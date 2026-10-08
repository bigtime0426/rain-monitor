"""台股第二輪探測：
1. 櫃買「上櫃收盤行情」一直傳輸中斷，這裡改成分段讀取，記錄斷在哪裡、回應是壓縮還是一般，並列出櫃買說明檔的全部路徑找正確的資料集。
2. 測試能不能抓「過去某一天」的全市場收盤資料（證交所與櫃買的網站 JSON），用來回補歷史、讓 20 日均線第一天就算得出來。
不需要金鑰，只做讀取。結果存成 stock_samples2.md。
"""
import datetime as dt
import json
import time

import requests

TZ = dt.timezone(dt.timedelta(hours=8))
REPORT = "stock_samples2.md"
UA = {"User-Agent": "Mozilla/5.0 data-probe"}
TPEX = "https://www.tpex.org.tw/openapi/v1"
TPEX_SWAGGER = "https://www.tpex.org.tw/openapi/swagger.json"     # 注意：說明檔在 /openapi/，不在 /openapi/v1/
MAX_CAND = 8


def workday(back=0):
    """最近一個可能有資料的平日再往前推 back 個平日（假日會抓不到，報告會呈現）。"""
    d = dt.datetime.now(TZ)
    if d.hour < 17:
        d -= dt.timedelta(days=1)
    n = -1
    while True:
        if d.weekday() < 5:
            n += 1
            if n >= back:
                return d
        d -= dt.timedelta(days=1)


def clip(v, n=40):
    s = str(v)
    return s if len(s) <= n else s[:n] + "…"


def fetch(url, params=None, tries=2):
    """分段讀取。回 (資料, 秒, 位元組, 備註清單, 內容型態)；失敗時資料為 None，備註說明原因。"""
    notes = []
    for i in range(tries):
        headers = dict(UA)
        if i == 1:
            headers["Accept-Encoding"] = "identity"
        t0, got, buf, stop = time.time(), 0, [], False
        try:
            r = requests.get(url, params=params, headers=headers, timeout=(10, 90), stream=True)
            ctype = (r.headers.get("content-type") or "")[:40]
            enc = r.headers.get("content-encoding") or "無"
            try:
                for chunk in r.iter_content(65536):
                    buf.append(chunk)
                    got += len(chunk)
            except Exception as e:  # noqa: BLE001
                notes.append("第%d次：傳輸中斷於 %d KB（%s；壓縮=%s）" % (i + 1, got // 1024, type(e).__name__, enc))
                continue
            body = b"".join(buf)
            if r.status_code != 200:
                notes.append("第%d次：HTTP %s（%s）%s" % (i + 1, r.status_code, ctype, body[:100].decode("utf-8", "ignore").replace("\n", " ")))
                if r.status_code in (403, 404):
                    stop = True
            else:
                try:
                    return json.loads(body.decode("utf-8-sig")), round(time.time() - t0, 1), got, notes, ctype
                except ValueError:
                    notes.append("第%d次：不是 JSON（%s，%d bytes）：%s" % (i + 1, ctype, got, body[:150].decode("utf-8", "ignore").replace("\n", " ")))
        except Exception as e:  # noqa: BLE001
            notes.append("第%d次：%s" % (i + 1, type(e).__name__))
        if stop:
            break
    return None, None, 0, notes, ""


def rows_of(obj):
    """回 (欄位, 筆數, 前兩筆 dict)。"""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return list(obj[0].keys()), len(obj), obj[:2]
    if isinstance(obj, dict) and isinstance(obj.get("fields"), list) and isinstance(obj.get("data"), list):
        f = obj["fields"]
        return f, len(obj["data"]), [dict(zip(f, r)) for r in obj["data"][:2] if isinstance(r, list)]
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return list(v[0].keys()), len(v), v[:2]
        return list(obj.keys()), 0, []
    return [], 0, []


def dump(title, url, params=None, guess=False):
    lines = ["## " + title + ("（路徑是猜的）" if guess else ""), "", "`%s`%s" % (url, "　參數：%s" % params if params else "")]
    data, secs, size, notes, ctype = fetch(url, params)
    if data is None:
        return lines + ["", "**失敗**", ""] + ["- " + n for n in notes] + [""], False
    lines += ["", "通，%s 秒，%d KB，%s%s" % (secs, size // 1024, ctype, "；先前嘗試：" + "；".join(notes) if notes else ""), ""]
    if isinstance(data, dict) and isinstance(data.get("tables"), list):      # 證交所網站格式：一次回多張表
        lines += ["頂層鍵：%s；stat=%s" % (list(data.keys())[:12], clip(data.get("stat", ""), 30)), ""]
        for t in data["tables"][:12]:
            if not isinstance(t, dict):
                continue
            f, n, rows = rows_of(t)
            lines += ["### 表格：%s（%d 筆）" % (clip(t.get("title", ""), 60), n), "```", "\n".join(map(str, f)) or "(無欄位)", "```"]
            if rows:
                lines += ["範例：", "```", "\n".join("%s = %s" % (k, clip(v)) for k, v in rows[0].items()), "```"]
            lines.append("")
        return lines, True
    f, n, rows = rows_of(data)
    meta = "，".join("%s=%s" % (k, clip(data[k], 30)) for k in ("stat", "date", "title", "reportDate") if isinstance(data, dict) and k in data)
    lines += ["%d 筆%s" % (n, "；" + meta if meta else ""), "", "欄位：", "```", "\n".join(map(str, f)) or "(看不出欄位)", "```", ""]
    for i, row in enumerate(rows, 1):
        lines += ["範例 %d：" % i, "```", "\n".join("%s = %s" % (k, clip(v)) for k, v in row.items()), "```", ""]
    return lines, True


def swagger_all():
    notes, data = [], None
    for i in range(3):
        data, _s, _n, nt, _c = fetch(TPEX_SWAGGER, tries=1)
        notes += ["第%d輪 %s" % (i + 1, x) for x in nt]
        if isinstance(data, dict) and data.get("paths"):
            break
        data = None
        time.sleep(5)
    paths = []
    if data:
        for path, ops in data["paths"].items():
            summ = ""
            for op in (ops.values() if isinstance(ops, dict) else []):
                if isinstance(op, dict) and op.get("summary"):
                    summ = op["summary"]
                    break
            paths.append((path, summ))
    return paths, notes


def main():
    day, past = workday(0), workday(5)
    now = dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
    out = ["# 台股第二輪探測", "", "執行時間：%s（台灣時間）；最近交易日：%s；回補測試日：%s" % (now, day.strftime("%Y%m%d"), past.strftime("%Y%m%d")), ""]

    paths, notes = swagger_all()
    out += ["## 櫃買說明檔：全部資料集路徑（%d 個）" % len(paths), ""]
    out += ["- %s %s" % p for p in paths] if paths else ["說明檔三輪都讀取失敗：", ""] + ["- " + n for n in notes]
    out.append("")

    tested = {"/tpex_mainboard_daily_close_quotes"}
    targets = [("櫃買 上櫃收盤行情（上次失敗的路徑）", TPEX + "/tpex_mainboard_daily_close_quotes", None, False)]
    for path, summ in paths:
        low = path.lower()
        if path not in tested and any(k in low for k in ("quote", "close", "daily")) and len(tested) <= MAX_CAND:
            tested.add(path)
            targets.append(("櫃買 候選 " + path + "　" + summ, TPEX + path, None, False))
    roc = "%d/%02d/%02d" % (past.year - 1911, past.month, past.day)
    targets += [
        ("櫃買 舊版網站 JSON（回補測試日）", "https://www.tpex.org.tw/web/stock/aftertrading/daily_close_quotes/stk_quote_result.php",
         {"l": "zh-tw", "d": roc, "o": "json"}, True),
        ("櫃買 新版網站 JSON（回補測試日）", "https://www.tpex.org.tw/www/zh-tw/afterTrading/otc",
         {"date": past.strftime("%Y/%m/%d"), "type": "EW", "response": "json"}, True),
        ("證交所 全市場收盤行情（回補測試日）", "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
         {"date": past.strftime("%Y%m%d"), "type": "ALLBUT0999", "response": "json"}, True),
        ("證交所 全市場收盤行情（最近交易日，看當天是否已更新）", "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX",
         {"date": day.strftime("%Y%m%d"), "type": "ALLBUT0999", "response": "json"}, True),
    ]
    ok = fail = 0
    for title, url, params, guess in targets:
        lines, good = dump(title, url, params, guess)
        out += lines
        ok += good
        fail += (not good)
        time.sleep(1.5)
    out[3:3] = ["成功 %d 項，失敗 %d 項。" % (ok, fail), ""]
    text = "\n".join(out) + "\n"
    open(REPORT, "w", encoding="utf-8").write(text)
    print(text)


if __name__ == "__main__":
    main()
