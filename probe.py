"""資料來源連線探測：從 GitHub 的機器實際打一次各候選資料來源，看連不連得到、資料長什麼樣。
只做讀取，不寫入任何服務。金鑰只從環境變數讀，不會出現在報告或日誌裡。
結果寫進 probe_report.md。
"""
import concurrent.futures as cf
import datetime as dt
import json
import os
import time

import requests

try:
    import traffic      # 沿用雨在哪裡的 TDX 登入
except Exception as _e:  # noqa: BLE001
    traffic = None
    print("traffic 模組載入失敗（TDX 項目會用匿名）：", type(_e).__name__)

TZ = dt.timezone(dt.timedelta(hours=8))
REPORT = "probe_report.md"
TDX = "https://tdx.transportdata.tw/api/basic/"
KEYWORDS = ("法人", "融資", "融券", "借券", "本益比", "三大", "margin", "insti")


def last_trading_guess():
    """最近一個可能有資料的平日（17 點前用前一天；週末往前推）。假日不會抓到資料，報告會註明。"""
    d = dt.datetime.now(TZ)
    if d.hour < 17:
        d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


DAY = last_trading_guess()

TESTS = [
    # ---- 台股 ----
    dict(g="台股", name="證交所 OpenAPI 說明檔（列出所有可用資料集）", url="https://openapi.twse.com.tw/v1/swagger.json", swagger=True),
    dict(g="台股", name="證交所 全部個股收盤行情", url="https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"),
    dict(g="台股", name="證交所 本益比、殖利率、股價淨值比", url="https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"),
    dict(g="台股", name="證交所 融資融券餘額", url="https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN"),
    dict(g="台股", name="證交所 三大法人買賣超（日，網站 JSON）", url="https://www.twse.com.tw/rwd/zh/fund/T86",
         params={"date": DAY, "selectType": "ALLBUT0999", "response": "json"}),
    dict(g="台股", name="櫃買中心 OpenAPI 說明檔", url="https://www.tpex.org.tw/openapi/swagger.json", swagger=True),
    dict(g="台股", name="櫃買中心 上櫃收盤行情", url="https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes"),
    dict(g="台股", name="櫃買中心 三大法人（路徑為推測）", url="https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"),
    # ---- 山區道路 ----
    dict(g="山區道路", name="氣象署 顯著有感地震報告", url="https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0016-001",
         env="CWA_API_KEY", keyparam="Authorization", params={"format": "JSON", "limit": 3}),
    dict(g="山區道路", name="氣象署 小區域有感地震報告", url="https://opendata.cwa.gov.tw/api/v1/rest/datastore/E-A0015-001",
         env="CWA_API_KEY", keyparam="Authorization", params={"format": "JSON", "limit": 3}),
    dict(g="山區道路", name="TDX 省道 事件／封路通報（News）", url=TDX + "v2/Road/Traffic/Live/News/Highway", tdx=True),
    dict(g="山區道路", name="TDX 省道 即時事件（Event，路徑為推測）", url=TDX + "v2/Road/Traffic/Live/Event/Highway", tdx=True),
    # ---- 淹水 ----
    dict(g="淹水", name="民生公共物聯網 水利署感測器（路徑為推測）", url="https://sta.ci.taiwan.gov.tw/STA_WaterResource_v2/v1.0/Things",
         params={"$top": 3}),
    dict(g="淹水", name="水利署 開放資料 即時水位（資料集代碼為推測）",
         url="https://opendata.wra.gov.tw/Service/OpenData.aspx",
         params={"format": "json", "id": "1602CA19-B224-4CC3-AA31-11B1B124530F"}),
    # ---- 其他 ----
    dict(g="其他", name="USGS 全球地震（近 24 小時）", url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"),
    dict(g="其他", name="TDX YouBike 台北車位", url=TDX + "v2/Bike/Availability/City/Taipei", tdx=True),
    dict(g="其他", name="TDX 台鐵 即時到離站", url=TDX + "v2/Rail/TRA/LiveBoard", tdx=True),
    dict(g="其他", name="環境部 空氣品質（需免費金鑰 MOENV_API_KEY）", url="https://data.moenv.gov.tw/api/v2/aqx_p_432",
         env="MOENV_API_KEY", keyparam="api_key", params={"limit": 3, "format": "json"}),
    dict(g="其他", name="疾管署 開放資料（路徑為推測）", url="https://od.cdc.gov.tw/eic/Weekly_Confirmed_Disease_Number.json"),
    dict(g="其他", name="GDELT 新聞搜尋", url="https://api.gdeltproject.org/api/v2/doc/doc",
         params={"query": "taiwan", "mode": "artlist", "format": "json", "maxrecords": 3}),
    dict(g="其他", name="世界銀行 台灣 GDP", url="https://api.worldbank.org/v2/country/TW/indicator/NY.GDP.MKTP.CD",
         params={"format": "json", "per_page": 3}),
]


def find_list(obj, path="", depth=0):
    """找第一個『裝著物件的清單』，回傳 (路徑, 清單)。"""
    if isinstance(obj, list):
        if obj and isinstance(obj[0], dict):
            return path or "(最外層)", obj
        return None
    if isinstance(obj, dict) and depth < 4:
        for k, v in obj.items():
            r = find_list(v, (path + "." + k).strip("."), depth + 1)
            if r:
                return r
    return None


def describe(obj):
    """一句話描述資料長相：幾筆、有哪些欄位。"""
    if isinstance(obj, dict) and "paths" in obj:
        return "paths %d 個" % len(obj["paths"])
    f = find_list(obj)
    if f:
        path, lst = f
        return "%s：%d 筆；欄位 %s" % (path, len(lst), list(lst[0].keys())[:12])
    if isinstance(obj, list):
        return "list %d 筆" % len(obj)
    if isinstance(obj, dict):
        return "dict；鍵 %s" % list(obj.keys())[:10]
    return type(obj).__name__


def has_data(obj):
    f = find_list(obj)
    if f:
        return len(f[1]) > 0
    if isinstance(obj, dict) and "stat" in obj and str(obj["stat"]).upper() != "OK":
        return False
    if isinstance(obj, dict) and "paths" in obj:
        return len(obj["paths"]) > 0
    return bool(obj)


def swagger_hits(obj):
    out = []
    for path, ops in (obj.get("paths") or {}).items():
        text = path
        if isinstance(ops, dict):
            for op in ops.values():
                if isinstance(op, dict):
                    text += " " + str(op.get("summary") or "") + " " + str(op.get("description") or "")
        if any(k in text for k in KEYWORDS):
            summ = ""
            for op in (ops.values() if isinstance(ops, dict) else []):
                if isinstance(op, dict) and op.get("summary"):
                    summ = op["summary"]
                    break
            out.append("%s %s" % (path, summ))
    return out


def run(t, token):
    res = {"g": t["g"], "name": t["name"], "url": t["url"], "verdict": "", "detail": "", "secs": None, "extra": []}
    headers = {"User-Agent": "Mozilla/5.0 data-probe"}
    params = dict(t.get("params") or {})
    key = ""
    if t.get("env"):
        key = (os.environ.get(t["env"]) or "").strip()
        if not key:
            res.update(verdict="略過", detail="沒有設定 %s，這項沒測" % t["env"])
            return res
        params[t["keyparam"]] = key
    if t.get("tdx"):
        params.update({"$format": "JSON", "$top": 3})
        if token:
            headers["Authorization"] = "Bearer " + token
    t0 = time.time()
    try:
        r = requests.get(t["url"], params=params, headers=headers, timeout=(10, 30))
    except Exception as e:  # noqa: BLE001
        res.update(verdict="連不上", detail=type(e).__name__, secs=round(time.time() - t0, 1))
        return res
    res["secs"] = round(time.time() - t0, 1)
    size = len(r.content)
    if r.status_code != 200:
        res.update(verdict="HTTP %s" % r.status_code, detail="%d bytes" % size)
        return res
    try:
        obj = r.json()
    except ValueError:
        snippet = r.text[:80].replace("\n", " ")
        res.update(verdict="通但不是 JSON", detail="%d bytes：%s" % (size, snippet))
        return res
    res["detail"] = "%s（%d KB）" % (describe(obj), size // 1024)
    if isinstance(obj, dict) and "stat" in obj:
        res["detail"] += "；stat=%s" % str(obj["stat"])[:40]
    res["verdict"] = "通" if has_data(obj) else "通但沒資料"
    if t.get("swagger") and isinstance(obj, dict):
        res["extra"] = swagger_hits(obj)
    return res


def main():
    token = None
    if traffic:
        try:
            token = traffic.get_token()
        except Exception as e:  # noqa: BLE001
            print("TDX token 失敗：", type(e).__name__)
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda t: run(t, token), TESTS))

    now = dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    lines = ["# 資料來源連線探測", "", "執行時間：%s（台灣時間）；測試的交易日：%s；TDX：%s" % (now, DAY, "金鑰" if token else "匿名"), "",
             "| 類別 | 項目 | 結果 | 秒 | 說明 |", "| --- | --- | --- | --- | --- |"]
    for r in results:
        lines.append("| %s | %s | %s | %s | %s |" % (r["g"], r["name"], r["verdict"], "" if r["secs"] is None else r["secs"],
                                                    r["detail"].replace("|", "／")))
    for r in results:
        if r["extra"]:
            lines += ["", "## %s：和法人、融資券、本益比有關的資料集" % r["name"]] + ["- " + x for x in r["extra"][:40]]
    text = "\n".join(lines) + "\n"
    open(REPORT, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
