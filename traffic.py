"""雨在哪裡：路況與特報模組（給 monitor.py 呼叫）

資料來源（都是官方開放資料，免費）：
- TDX 省道／國道即時路況（車速、壅塞等級、路段位置 OpenLR）
- 氣象署天氣警特報（豪雨、大雨、颱風等）
金鑰只從環境變數讀（TDX_CLIENT_ID／TDX_CLIENT_SECRET／CWA_API_KEY），不寫進任何檔案或紀錄。
任何一步失敗都只記錄，不會讓主程式中斷。
"""
import base64
import datetime as dt
import json
import math
import os
import time

import requests

BASE = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/"
TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
WARN_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001"
RADIUS_KM = 5
MAX_ROADS = 4
RAIN_WORDS = ("雨", "颱風")      # 特報名稱含這些字才算和下雨有關
UA = {"User-Agent": "Mozilla/5.0 rain-monitor"}


def km(lat1, lon1, lat2, lon2):
    r, p = 6371, math.pi / 180
    a = (math.sin((lat2 - lat1) * p / 2) ** 2
         + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2)
    return 2 * r * math.asin(math.sqrt(a))


# ---------- TDX 登入 ----------
def get_token():
    """取得 TDX token。失敗回 None（改用匿名，呼叫限制較嚴但仍可用）。不印出任何金鑰。"""
    cid = (os.environ.get("TDX_CLIENT_ID") or "").strip()
    sec = (os.environ.get("TDX_CLIENT_SECRET") or "").strip()
    if not cid or not sec:
        print("TDX：未設定金鑰，改用匿名")
        return None
    for a, b, label in ((cid, sec, ""), (sec, cid, "（ID 與 Secret 對調後）")):
        try:
            r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials",
                                               "client_id": a, "client_secret": b},
                              headers=UA, timeout=30)
        except requests.RequestException as e:
            print("TDX token 連線失敗：", str(e)[:80])
            return None
        if r.status_code == 200:
            print("TDX token：成功" + label)
            return r.json().get("access_token")
        print("TDX token 失敗%s：HTTP %s（ID 長度 %d、Secret 長度 %d）" % (label, r.status_code, len(a), len(b)))
        if r.status_code not in (400, 401):
            break
    print("TDX：金鑰無效，改用匿名")
    return None


def fetch(path, token, params=None):
    headers = dict(UA)
    if token:
        headers["Authorization"] = "Bearer " + token
    q = {"$format": "JSON"}
    q.update(params or {})
    for i in range(3):
        try:
            r = requests.get(BASE + path, params=q, headers=headers, timeout=60)
            if r.status_code == 200:
                return r.json()
            print("TDX %s：HTTP %s" % (path, r.status_code))
            if r.status_code in (400, 401, 403, 404):
                return None
        except (requests.RequestException, ValueError) as e:
            print("TDX %s：%s" % (path, str(e)[:80]))
        time.sleep(2 * (i + 1))
    return None


# ---------- OpenLR 位置解碼 ----------
def decode_openlr(s):
    """OpenLR 二進位（base64）的第一個點 → (緯度, 經度)。看不懂回 None。"""
    try:
        b = base64.b64decode(s)
        if len(b) < 7:
            return None

        def c(x):
            v = int.from_bytes(x, "big", signed=True)
            sgn = (v > 0) - (v < 0)
            return (v - sgn * 0.5) * 360 / 2 ** 24
        lat, lon = c(b[4:7]), c(b[1:4])
        if 20 <= lat <= 27 and 118 <= lon <= 123:   # 只收台灣範圍內的點
            return round(lat, 5), round(lon, 5)
    except Exception:  # noqa: BLE001
        pass
    return None


def points_of(item):
    pts = []
    for lr in item.get("OpenLRs") or []:
        p = decode_openlr(lr.get("OpenLR")) if isinstance(lr, dict) else None
        if p:
            pts.append(p)
    return pts


# ---------- 路況 ----------
def load_live(token):
    """省道＋國道即時路況 → [{kind,id,speed,level,pts}, ...]；另回傳統計。"""
    items, stats = [], {}
    for kind, label in (("Freeway", "國道"), ("Highway", "省道")):
        data = fetch("Live/" + kind, token)
        total = with_loc = 0
        for it in (data or {}).get("LiveTraffics") or []:
            total += 1
            pts = points_of(it)
            if pts:
                with_loc += 1
            items.append({"kind": label, "id": it.get("SectionID"),
                          "speed": it.get("TravelSpeed"), "level": it.get("CongestionLevel"),
                          "pts": pts})
        stats[label] = {"總筆數": total, "有位置": with_loc}
        print("路況 %s：%d 筆，其中 %d 筆有位置" % (label, total, with_loc))
    return items, stats


def section_names(kind_en, ids, token):
    """用路段編號查路名。查不到就回空字典。"""
    ids = [i for i in ids if i]
    if not ids:
        return {}
    flt = " or ".join("SectionID eq '%s'" % i for i in ids[:20])
    data = fetch("Section/" + kind_en, token, {"$filter": flt})
    out = {}
    for s in (data or {}).get("Sections") or []:
        out[s.get("SectionID")] = s.get("SectionName") or s.get("RoadName") or ""
    return out


def nearby(items, lat, lon, radius=RADIUS_KM, limit=MAX_ROADS):
    found = []
    for it in items:
        if not it["pts"] or it["speed"] is None:
            continue
        d = min(km(lat, lon, p[0], p[1]) for p in it["pts"])
        if d <= radius:
            found.append((d, it))
    found.sort(key=lambda x: x[0])
    return [dict(it, km=round(d, 1)) for d, it in found[:limit]]


# ---------- 氣象署特報 ----------
def load_warnings(cwa_key):
    """回傳 {縣市: ['豪雨特報', ...]}，只留和下雨有關的。"""
    out = {}
    if not cwa_key:
        return out
    try:
        r = requests.get(WARN_URL, params={"Authorization": cwa_key, "format": "JSON"}, timeout=40)
        r.raise_for_status()
        for loc in r.json()["records"]["location"]:
            names = []
            for h in (loc.get("hazardConditions") or {}).get("hazards") or []:
                info = h.get("info") or {}
                ph = info.get("phenomena") or ""
                if any(w in ph for w in RAIN_WORDS):
                    names.append(ph + (info.get("significance") or ""))
            if names:
                out[loc.get("locationName", "")] = names
    except Exception as e:  # noqa: BLE001
        print("特報讀取失敗：", str(e)[:80])
    return out


def level_text(lv):
    return "壅塞等級 %s（1 最順暢，數字越大越塞）" % lv if lv not in (None, "") else "壅塞等級不明"


# ---------- 整合：每個監看地區的路況＋特報 ----------
def build_context(areas, cwa_key, now):
    """areas: {地區: (緯度, 經度, 縣市)}。回傳 ctx，並寫出 traffic.json（體積很小）。"""
    ctx = {"updated": now.isoformat(), "stats": {}, "areas": {}}
    token = get_token()
    items, stats = load_live(token)
    ctx["stats"] = stats
    warnings = load_warnings(cwa_key)
    for area, (lat, lon, county) in areas.items():
        roads = nearby(items, lat, lon)
        for kind_en, label in (("Freeway", "國道"), ("Highway", "省道")):
            ids = [r["id"] for r in roads if r["kind"] == label]
            names = section_names(kind_en, ids, token) if ids else {}
            for r in roads:
                if r["kind"] == label:
                    r["name"] = names.get(r["id"]) or ""
        county_key = (county or "").replace("台", "臺")
        ctx["areas"][area] = {
            "county": county,
            "warnings": warnings.get(county_key, []),
            "roads": [{"kind": r["kind"], "name": r.get("name", ""), "id": r["id"],
                       "speed": r["speed"], "level": r["level"], "km": r["km"]} for r in roads],
        }
    with open("traffic.json", "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=1)
    return ctx


def lines_for(ctx, area):
    """給下雨通知信用的幾行文字。"""
    a = (ctx or {}).get("areas", {}).get(area)
    if a is None:
        return []
    out = ["路況（%d km 內）：" % RADIUS_KM]
    if a["roads"]:
        for r in a["roads"]:
            label = r["name"] or "%s路段 %s" % (r["kind"], r["id"])
            out.append("• %s：%s km/h，%s，距 %s km" % (label, r["speed"], level_text(r["level"]), r["km"]))
    else:
        out.append("• 這個範圍沒有取得路況資料")
    if a["warnings"]:
        out.append("氣象署特報（%s）：%s" % (a["county"], "、".join(a["warnings"])))
    return out + [""]
