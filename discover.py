"""自動找鏡頭：從 TDX 官方鏡頭清單，依 scope.json 的範圍挑出鏡頭，
再從 GitHub 這台機器實際測試抓不抓得到畫面，只留抓得到的，存成 cameras_auto.json。
每 7 天重做一次（或設環境變數 FORCE_DISCOVER=1 強制重做）。失敗不會影響盯雨。
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import time

import requests

import traffic

OUT = "cameras_auto.json"
REPORT = "discover_report.txt"
MAX_AGE_DAYS = 7
TEST_WORKERS = 16
BUDGET_SEC = 420          # 測試連線最多花這麼久，超過就停


def fresh():
    if os.environ.get("FORCE_DISCOVER") == "1" or not os.path.exists(OUT):
        return False
    try:
        d = json.load(open(OUT, encoding="utf-8"))
        age = (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(d["updated"])).days
        return age < MAX_AGE_DAYS
    except Exception:  # noqa: BLE001
        return False


def in_bbox(lat, lon, box):
    return box[0] <= lat <= box[1] and box[2] <= lon <= box[3]


def reachable(url, connect=5, read=6):
    """抓前幾 KB，看是不是圖片或 MJPEG 串流。回 (是否成功, 說明)。"""
    try:
        r = requests.get(url, stream=True, timeout=(connect, read), headers={"User-Agent": "Mozilla/5.0"})
        ctype = r.headers.get("content-type", "")
        if r.status_code != 200:
            r.close()
            return False, "HTTP %s" % r.status_code
        head = b""
        for chunk in r.iter_content(2048):
            head += chunk
            if len(head) >= 2048:
                break
        r.close()
        ok = head[:2] == b"\xff\xd8" or "image" in ctype or "multipart" in ctype
        return ok, ctype[:30] or "?"
    except Exception as e:  # noqa: BLE001
        return False, type(e).__name__


def main():
    if fresh():
        print("鏡頭清單還新，略過重新探測")
        return
    scope = json.load(open("scope.json", encoding="utf-8"))
    roads, boxes = scope["roads"], scope["bboxes"]
    token = traffic.get_token()

    cands, seen = [], set()
    listed = {}
    for kind, label in (("Freeway", "國道"), ("Highway", "省道")):
        data = traffic.fetch("CCTV/" + kind, token)
        items = (data or {}).get("CCTVs") or []
        listed[label] = len(items)
        for it in items:
            lat, lon = it.get("PositionLat"), it.get("PositionLon")
            url = it.get("VideoImageURL") or it.get("VideoStreamURL")
            if lat is None or lon is None or not url or url in seen:
                continue
            road = it.get("RoadName") or ""
            on_road = any(road.startswith(r) for r in roads)
            in_area = any(in_bbox(lat, lon, b) for b in boxes.values())
            if not (on_road or in_area):
                continue
            seen.add(url)
            desc = it.get("SurveillanceDescription") or ""
            cands.append({
                "id": it.get("CCTVID"), "road": road, "kind": label,
                "name": ("%s %s %s" % (road, it.get("LocationMile") or "", desc)).strip()[:60],
                "lat": lat, "lon": lon, "url": url,
            })
    print("清單：%s；符合範圍 %d 支，開始測試連線" % (listed, len(cands)))

    good, fail_reasons, failed = [], {}, []
    start = time.time()
    with cf.ThreadPoolExecutor(max_workers=TEST_WORKERS) as ex:
        futs = {ex.submit(reachable, c["url"]): c for c in cands}
        for f in cf.as_completed(futs):
            c = futs[f]
            try:
                ok, why = f.result()
            except Exception as e:  # noqa: BLE001
                ok, why = False, type(e).__name__
            if ok:
                good.append(c)
            else:
                host = c["url"].split("/")[2]
                key = "%s %s" % (host, why)
                fail_reasons[key] = fail_reasons.get(key, 0) + 1
                failed.append(c)
            if time.time() - start > BUDGET_SEC:
                print("超過時間預算，停止測試")
                break


    # 整台主機連不上時，換個方式再測（判斷是被擋還是只是慢）
    variant = []
    by_host = {}
    for c in failed:
        by_host.setdefault(c["url"].split("/")[2], []).append(c)
    for host, cs in by_host.items():
        if len(cs) < 20:
            continue
        for c in cs[:3]:
            u = c["url"]
            http_u = u.replace("https://", "http://", 1)
            a = reachable(u, connect=15, read=10)
            b = reachable(http_u, connect=15, read=10)
            variant.append("%s | https長等待=%s | http=%s" % (host, a, b))

    tally = {}
    try:
        import monitor
        stations = monitor.fetch_stations()
        counties = [monitor.norm(x) for x in scope.get("counties", [])]
        ex_towns = set(scope.get("excludeTowns", []))
        for c in good:
            st, d = monitor.nearest(c, stations)
            if d > monitor.MAX_KM or st["town"] in ex_towns:
                continue
            county = monitor.norm(st["county"])
            on_road = any(c["road"].startswith(r) for r in roads)
            if county in counties:
                tally[county] = tally.get(county, 0) + 1
            elif on_road:
                tally["國道1/3號·其他縣市"] = tally.get("國道1/3號·其他縣市", 0) + 1
    except Exception as e:  # noqa: BLE001
        tally = {"統計失敗": str(e)[:80]}

    good.sort(key=lambda c: (c["road"], c["lat"]))
    json.dump({"updated": dt.datetime.now(dt.timezone.utc).isoformat(), "cameras": good},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    by_road = {}
    for c in good:
        by_road[c["road"]] = by_road.get(c["road"], 0) + 1
    lines = ["清單筆數：%s" % listed, "符合範圍：%d 支" % len(cands), "抓得到畫面：%d 支" % len(good),
             "抓得到（依道路）：%s" % json.dumps(by_road, ensure_ascii=False),
             "失敗原因：%s" % json.dumps(fail_reasons, ensure_ascii=False),
             "範圍內可用鏡頭（依縣市）：%s" % json.dumps(tally, ensure_ascii=False),
             "連不上主機的變體測試：", *(variant or ["（無）"])]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print("找鏡頭失敗（不影響盯雨）：", str(e)[:150])
