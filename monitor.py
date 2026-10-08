"""雨在哪裡：每 15 分鐘自動盯雨（GitHub Actions 版）

流程：讀氣象署雨量站 → 每支鏡頭找最近雨量站 → 10 分鐘雨量 > 0 才抓畫面
→ 交給 Gemini 判斷 → 結果寫進 log.csv（有雨時另存畫面到 frames/）。
金鑰只從環境變數讀（GitHub Secrets），不會寫進任何檔案或紀錄。
"""
import base64
import concurrent.futures as cf
import csv
import datetime as dt
import json
import math
import os
import subprocess
import tempfile
import time

import requests

try:
    import traffic          # 路況與特報；缺檔或出錯都不影響主流程
except Exception as _e:     # noqa: BLE001
    traffic = None
    print("路況模組載入失敗：", str(_e)[:80])

TZ = dt.timezone(dt.timedelta(hours=8))
MAX_KM = 5            # 鏡頭和雨量站超過這個距離，就不當作同一場雨
RAIN_MIN_M10 = 0      # 最近 10 分鐘雨量大於這個值才抓畫面
CWA_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.5-flash-lite"]
PROMPT = "\n".join([
    "這是台灣路邊攝影機的即時畫面。請判斷目前是否正在下雨。",
    "只看畫面證據：雨絲、路面是否濕亮或反光、鏡頭水珠、車輛尾燈或水花。",
    "請只回傳一行 JSON，格式：",
    '{"raining":"yes|no|unclear","road_wet":true|false,"confidence":0到1的數字,"reason":"一句話理由"}',
])
HEADER = ["抓取時間", "地區", "鏡頭", "最近雨量站", "距離(km)", "站觀測時間", "資料落後(分)",
          "10分鐘(mm)", "1小時(mm)", "判斷下雨", "路面濕", "信心", "理由", "型號", "畫面", "狀態"]


def km(lat1, lon1, lat2, lon2):
    r, p = 6371, math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v < 0 else v


def fetch_stations():
    key = os.environ["CWA_API_KEY"]
    res = requests.get(CWA_URL, params={"Authorization": key, "format": "JSON"}, timeout=60)
    res.raise_for_status()
    out = []
    for s in res.json()["records"]["Station"]:
        geo = s.get("GeoInfo") or {}
        coords = geo.get("Coordinates") or []
        c = next((x for x in coords if "WGS" in (x.get("CoordinateName") or "")), coords[0] if coords else {})
        try:
            lat, lon = float(c["StationLatitude"]), float(c["StationLongitude"])
        except (KeyError, TypeError, ValueError):
            continue
        re_ = s.get("RainfallElement") or {}
        g = lambda k: num((re_.get(k) or {}).get("Precipitation"))
        out.append({
            "name": s.get("StationName", ""), "county": geo.get("CountyName", ""),
            "town": geo.get("TownName", ""), "lat": lat, "lon": lon,
            "time": (s.get("ObsTime") or {}).get("DateTime", ""),
            "m10": g("Past10Min"), "h1": g("Past1hr"),
        })
    return out


def nearest(cam, stations):
    best = min(stations, key=lambda s: km(cam["lat"], cam["lon"], s["lat"], s["lon"]))
    return best, km(cam["lat"], cam["lon"], best["lat"], best["lon"])


def grab_frame(url):
    """用 ffmpeg 從 HLS 或 MJPEG 串流截一張畫面，回傳 JPEG 位元組"""
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "f.jpg")
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-rw_timeout", "10000000",
               "-i", url, "-frames:v", "1", "-q:v", "2", out]
        p = subprocess.run(cmd, capture_output=True, timeout=45)
        if p.returncode != 0 or not os.path.exists(out):
            raise RuntimeError("ffmpeg 失敗：" + p.stderr.decode("utf-8", "ignore")[-200:].strip())
        data = open(out, "rb").read()
        if len(data) < 2000:
            raise RuntimeError("畫面太小，可能是空白")
        return data


def call_gemini(img):
    key = os.environ["GEMINI_API_KEY"]
    b64 = base64.b64encode(img).decode()
    last = (None, 0, "")
    for model in GEMINI_MODELS:
        for attempt in (1, 2):
            try:
                r = requests.post(GEMINI_URL, headers={"x-goog-api-key": key}, timeout=45, json={
                    "model": model,
                    "input": [{"type": "text", "text": PROMPT},
                              {"type": "image", "data": b64, "mime_type": "image/jpeg"}],
                })
            except requests.RequestException as e:   # 逾時或連線中斷：等一下再試，不行就換型號
                last = (model, 0, str(e)[:120])
                time.sleep(attempt * 3)
                continue
            last = (model, r.status_code, r.text)
            if r.status_code == 200:
                return last
            if r.status_code in (503, 429):
                time.sleep(attempt * 4)
                continue
            break
    return last


def model_text(text):
    """從 Gemini 回應取出模型說的那段文字；找不到回傳空字串"""
    try:
        data = json.loads(text)
        for st in data.get("steps", []):
            if st.get("type") == "model_output" and st.get("content"):
                return st["content"][0].get("text", "") or ""
    except Exception:
        pass
    return ""


def parse_answer(text):
    """容錯解析：去掉 ``` 圍欄，再取第一個 { 到最後一個 } 之間的內容"""
    t = model_text(text).replace("```json", "").replace("```", "").strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(t[i:j + 1])
    except Exception:
        return None


def judge(cam):
    img = grab_frame(cam["url"])
    model, status, text = call_gemini(img)
    if status != 200:
        raise RuntimeError("Gemini HTTP %s %s" % (status, text[:100] if status == 0 else ""))
    ans = parse_answer(text)
    if not ans:
        raise RuntimeError("看不懂 Gemini 回應：" + (model_text(text) or text)[:150].replace("\n", " "))
    return img, model, ans

NOTIFY_M10 = 1.0          # 雨量站 10 分鐘雨量達這個值（mm）就算「有雨」要通知
NOTIFY_COOLDOWN_MIN = 60  # 同一地區，這段時間內只通知一次


def send_mail(subject, body):
    """透過你自己的 Apps Script 寄信給你自己。失敗只記錄，不影響主流程。"""
    url, token = os.environ.get("MAIL_URL"), os.environ.get("MAIL_TOKEN")
    if not url or not token:
        print("未設定 MAIL_URL / MAIL_TOKEN，略過通知")
        return False
    try:
        r = requests.post(url, json={"token": token, "subject": subject, "body": body}, timeout=60)
        ok = r.status_code == 200 and bool(r.json().get("ok"))
        print("通知寄送：成功" if ok else "通知寄送：失敗 %s %s" % (r.status_code, r.text[:80].replace("\n", " ")))
        return ok
    except Exception as e:  # noqa: BLE001
        print("通知寄送：失敗", str(e)[:100])
        return False


def notify(rows, now, ctx=None):
    try:
        state = json.load(open("state.json", encoding="utf-8"))
    except Exception:  # noqa: BLE001
        state = {}
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    by_area = {}
    for info, ans, _model, frame, _x, status in rows:
        if status.startswith("略過"):
            continue
        st = info["st"]
        rainy = (st["m10"] or 0) >= NOTIFY_M10 or bool(ans and ans.get("raining") == "yes")
        by_area.setdefault(info["cam"]["area"], []).append((info, ans, frame, status, rainy))

    changed = False
    for area, items in by_area.items():
        if not any(x[4] for x in items):
            continue
        last = state.get(area)
        if last:
            try:
                if (now - dt.datetime.fromisoformat(last)).total_seconds() / 60 < NOTIFY_COOLDOWN_MIN:
                    continue
            except Exception:  # noqa: BLE001
                pass
        st0 = items[0][0]["st"]
        lines = ["%s 目前有雨" % area, "雨量站：%s%s %s" % (st0["county"], st0["town"], st0["name"]),
                 "10 分鐘 %s mm，1 小時 %s mm（觀測時間 %s）" % (
                     "-" if st0["m10"] is None else st0["m10"], "-" if st0["h1"] is None else st0["h1"], st0["time"]),
                 ""]
        for info, ans, frame, status, _rainy in items:
            if ans:
                res = "鏡頭判斷：%s（信心 %s）%s" % (ans.get("raining"), ans.get("confidence"), ans.get("reason", ""))
            else:
                res = "鏡頭未能判斷：" + status[:60].replace("\n", " ")
            lines.append("• " + info["cam"]["name"])
            lines.append("  " + res)
            if frame and repo:
                lines.append("  畫面：https://github.com/%s/blob/main/%s" % (repo, frame))
        if traffic and ctx:
            try:
                lines += [""] + traffic.lines_for(ctx, area)[:-1]
            except Exception as e:  # noqa: BLE001
                print("路況文字產生失敗：", str(e)[:80])
        lines += ["", "注意：雨量站資料通常比現在晚 10～15 分鐘。"]
        top10 = max((x[0]["st"]["m10"] or 0) for x in items)
        top1h = max((x[0]["st"]["h1"] or 0) for x in items)
        cam_yes = any(x[1] and x[1].get("raining") == "yes" for x in items)
        tag = "鏡頭判斷有雨" if cam_yes else "雨量站有雨"
        if send_mail("【下雨】%s：10分鐘 %s mm／1小時 %s mm（%s）" % (area, top10, top1h, tag), "\n".join(lines)):
            state[area] = now.isoformat()
            changed = True
    if changed:
        json.dump(state, open("state.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def main():
    force = os.environ.get("FORCE") == "1"
    now = dt.datetime.now(TZ)
    cams = json.load(open("cameras.json", encoding="utf-8"))
    stations = fetch_stations()
    print("雨量站 %d 站" % len(stations))

    rows, jobs = [], []
    for cam in cams:
        if cam.get("disabled"):      # 已知連不上的鏡頭先停用，不浪費執行時間
            continue
        if cam.get("station"):       # 沒有精確座標的鏡頭：直接指定要配對的雨量站名稱，距離記為 0（不準）
            st = next((s for s in stations if s["name"] == cam["station"]), None)
            if st is None:
                print("找不到雨量站：", cam["station"])
                continue
            d = 0.0
        else:
            st, d = nearest(cam, stations)
        info = {"cam": cam, "st": st, "km": d}
        if d > MAX_KM:
            rows.append((info, None, "", None, "", "略過：%d km 內沒有雨量站" % MAX_KM))
            continue
        rainy = st["m10"] is not None and st["m10"] > RAIN_MIN_M10
        # 對照鏡頭（alwaysCheck）每小時只在整點後 15 分鐘內那一輪檢查，節省 Gemini 額度
        control = cam.get("alwaysCheck") and now.minute < 15
        if rainy or control or force:
            jobs.append(info)

    os.makedirs("frames", exist_ok=True)
    results = {}
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        futs = {ex.submit(judge, j["cam"]): i for i, j in enumerate(jobs)}
        for f in cf.as_completed(futs):
            i = futs[f]
            try:
                results[i] = ("ok",) + f.result()
            except Exception as e:  # noqa: BLE001
                results[i] = ("err", str(e)[:200])

    stamp = now.strftime("%Y%m%d-%H%M")
    for i, j in enumerate(jobs):
        r = results[i]
        if r[0] == "ok":
            _, img, model, ans = r
            frame = ""
            if (j["st"]["m10"] or 0) > 0 or ans.get("raining") == "yes":
                frame = "frames/%s_%d.jpg" % (stamp, i)
                open(frame, "wb").write(img)
            rows.append((j, ans, model, frame, "", "OK"))
        else:
            rows.append((j, None, "", "", "", r[1]))

    new_file = not os.path.exists("log.csv")
    with open("log.csv", "a", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        if new_file:
            w.writerow(HEADER)
        for info, ans, model, frame, _x, status in rows:
            st = info["st"]
            lag = ""
            try:
                lag = round((now - dt.datetime.fromisoformat(st["time"])).total_seconds() / 60)
            except Exception:  # noqa: BLE001
                pass
            w.writerow([
                now.strftime("%Y-%m-%d %H:%M:%S"), info["cam"]["area"], info["cam"]["name"],
                st["county"] + st["town"] + " " + st["name"], round(info["km"], 1),
                st["time"], lag,
                "" if st["m10"] is None else st["m10"], "" if st["h1"] is None else st["h1"],
                ans.get("raining", "") if ans else "", ans.get("road_wet", "") if ans else "",
                ans.get("confidence", "") if ans else "", ans.get("reason", "") if ans else "",
                model, frame or "", status,
            ])
    print("完成：檢查 %d 支鏡頭，寫入 %d 列" % (len(jobs), len(rows)))
    if os.environ.get("TEST_MAIL") == "1":
        send_mail("【雨在哪裡】測試通知", "如果你收到這封信，表示下雨通知的整條路線是通的。\n時間：" + now.strftime("%Y-%m-%d %H:%M"))
    ctx = None
    if traffic:
        try:
            areas = {}
            for info, *_rest in rows:
                cam = info["cam"]
                if cam.get("lat") is not None and cam.get("lon") is not None and cam["area"] not in areas:
                    areas[cam["area"]] = (cam["lat"], cam["lon"], info["st"]["county"])
            ctx = traffic.build_context(areas, os.environ.get("CWA_API_KEY"), now)
        except Exception as e:  # noqa: BLE001
            print("路況整合失敗（不影響盯雨）：", str(e)[:120])
    notify(rows, now, ctx)


if __name__ == "__main__":
    main()
