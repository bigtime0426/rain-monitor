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


def parse_answer(text):
    try:
        data = json.loads(text)
        for st in data.get("steps", []):
            if st.get("type") == "model_output" and st.get("content"):
                t = st["content"][0].get("text", "")
                t = t.replace("```json", "").replace("```", "").strip()
                return json.loads(t)
    except Exception:
        return None
    return None


def judge(cam):
    img = grab_frame(cam["url"])
    model, status, text = call_gemini(img)
    if status != 200:
        raise RuntimeError("Gemini HTTP %s %s" % (status, text[:100] if status == 0 else ""))
    ans = parse_answer(text)
    if not ans:
        raise RuntimeError("看不懂 Gemini 回應")
    return img, model, ans


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


if __name__ == "__main__":
    main()
