"""台股資料集欄位探測：把每個要用的資料集「真實欄位＋前兩筆範例」存成 stock_samples.md，
並從證交所、櫃買的說明檔找出和收盤行情、漲跌家數、指數有關的資料集路徑。
不需要任何金鑰。只做讀取。
"""
import datetime as dt
import time

import requests

TZ = dt.timezone(dt.timedelta(hours=8))
REPORT = "stock_samples.md"
UA = {"User-Agent": "Mozilla/5.0 data-probe"}
TWSE = "https://openapi.twse.com.tw/v1"
TPEX = "https://www.tpex.org.tw/openapi/v1"
KEYS = ("收盤", "行情", "漲跌", "家數", "指數", "成交")
MAX_CAND = 6


def last_day_guess():
    d = dt.datetime.now(TZ)
    if d.hour < 17:
        d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d.strftime("%Y%m%d")


DAY = last_day_guess()


def get_json(url, params=None):
    """第一次用一般方式；失敗再用 Accept-Encoding: identity（避開壓縮傳輸中斷）重試。回 (資料, 秒, 位元組, 錯誤清單)。"""
    errs = []
    for extra, read in (({}, 60), ({"Accept-Encoding": "identity"}, 90)):
        headers = dict(UA)
        headers.update(extra)
        t0 = time.time()
        try:
            r = requests.get(url, params=params, headers=headers, timeout=(10, read))
            if r.status_code != 200:
                errs.append("HTTP %s" % r.status_code)
                if r.status_code in (403, 404):
                    break
                continue
            return r.json(), round(time.time() - t0, 1), len(r.content), errs
        except Exception as e:  # noqa: BLE001
            errs.append(type(e).__name__)
    return None, None, 0, errs


def clip(v, n=40):
    s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def swagger_matches(base):
    data, _s, _n, errs = get_json(base + "/swagger.json")
    if not isinstance(data, dict):
        return [], errs
    out = []
    for path, ops in (data.get("paths") or {}).items():
        summ = ""
        for op in (ops.values() if isinstance(ops, dict) else []):
            if isinstance(op, dict) and op.get("summary"):
                summ = op["summary"]
                break
        if any(k in path or k in summ for k in KEYS):
            out.append((path, summ))
    return out, errs


def sample_of(obj):
    """回 (欄位清單, 筆數, 前兩筆 dict)。"""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return list(obj[0].keys()), len(obj), obj[:2]
    if isinstance(obj, dict) and isinstance(obj.get("fields"), list) and isinstance(obj.get("data"), list):
        f = obj["fields"]
        rows = [dict(zip(f, r)) for r in obj["data"][:2] if isinstance(r, list)]
        return f, len(obj["data"]), rows
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return list(v[0].keys()), len(v), v[:2]
        return list(obj.keys()), 0, []
    return [], 0, []


def section(title, url, params=None):
    lines = ["## " + title, "", "`%s`%s" % (url, "　參數：%s" % params if params else "")]
    data, secs, size, errs = get_json(url, params)
    if data is None:
        lines += ["", "**失敗**：%s" % "、".join(errs or ["未知"]), ""]
        return lines, False
    fields, n, rows = sample_of(data)
    meta = ""
    if isinstance(data, dict):
        meta = "；" + "，".join("%s=%s" % (k, clip(data[k], 30)) for k in ("stat", "date", "title") if k in data)
    lines += ["", "通，%s 秒，%d KB，%d 筆%s%s" % (secs, size // 1024, n, meta, "（重試後才成功：%s）" % "、".join(errs) if errs else ""), ""]
    lines += ["欄位：", "```", "\n".join(fields) or "(看不出欄位)", "```", ""]
    for i, row in enumerate(rows, 1):
        lines += ["範例 %d：" % i, "```", "\n".join("%s = %s" % (k, clip(v)) for k, v in row.items()), "```", ""]
    return lines, True


def main():
    now = dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    out = ["# 台股資料集欄位與範例", "", "執行時間：%s（台灣時間）；測試的交易日：%s" % (now, DAY), ""]

    tw_hits, tw_err = swagger_matches(TWSE)
    tp_hits, tp_err = swagger_matches(TPEX)
    out += ["## 說明檔裡和收盤、漲跌、家數、指數有關的資料集", "", "### 證交所"]
    out += ["- %s %s" % h for h in tw_hits] or ["- 說明檔讀取失敗：%s" % "、".join(tw_err)]
    out += ["", "### 櫃買中心"]
    out += ["- %s %s" % h for h in tp_hits] or ["- 說明檔讀取失敗：%s" % "、".join(tp_err)]
    out.append("")

    ok = fail = 0
    targets = [
        ("證交所 上市收盤行情", TWSE + "/exchangeReport/STOCK_DAY_ALL", None),
        ("證交所 本益比、殖利率、股價淨值比", TWSE + "/exchangeReport/BWIBBU_ALL", None),
        ("證交所 融資融券餘額", TWSE + "/exchangeReport/MI_MARGN", None),
        ("證交所 三大法人買賣超（網站 JSON）", "https://www.twse.com.tw/rwd/zh/fund/T86",
         {"date": DAY, "selectType": "ALLBUT0999", "response": "json"}),
        ("櫃買 上櫃本益比、殖利率、股價淨值比", TPEX + "/tpex_mainboard_peratio_analysis", None),
        ("櫃買 上櫃融資融券餘額", TPEX + "/tpex_mainboard_margin_balance", None),
        ("櫃買 上櫃三大法人買賣明細", TPEX + "/tpex_3insti_daily_trading", None),
    ]
    # 上櫃收盤行情：原本猜的路徑，加上說明檔裡名稱像收盤行情的候選
    cand = ["/tpex_mainboard_daily_close_quotes"]
    for path, summ in tp_hits:
        if path not in cand and ("收盤" in summ or "收盤" in path) and "上櫃" in summ:
            cand.append(path)
    for path in cand[:MAX_CAND]:
        targets.append(("櫃買 上櫃收盤行情候選 " + path, TPEX + path, None))
    # 證交所：漲跌家數、指數這類候選（只取名稱最像的，避免打太多）
    for path, summ in tw_hits:
        if ("家數" in summ or "漲跌" in summ or "MI_INDEX" in path) and len(targets) < 20:
            targets.append(("證交所 候選 " + path, TWSE + path, None))

    for title, url, params in targets:
        lines, good = section(title, url, params)
        out += lines
        ok += good
        fail += (not good)
        time.sleep(1)       # 對政府網站客氣一點
    out[3:3] = ["成功 %d 項，失敗 %d 項。" % (ok, fail), ""]
    text = "\n".join(out) + "\n"
    open(REPORT, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
