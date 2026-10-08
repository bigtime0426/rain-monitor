"""第二輪探測：TDX 公路／國道路況端點、氣象署特報與雷達。
結果寫到 probe_result.txt（不含金鑰）。"""
import json
import os
import time
import requests

KEY = os.environ.get("CWA_API_KEY", "")
UA = {"User-Agent": "Mozilla/5.0"}
TDX = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/"

TARGETS = [
    # TDX：公路即時訊息（前一輪確認連得到），完整看內容
    ("TDX 公路即時訊息", TDX + "Live/News/Highway?%24top=30&%24format=JSON"),
    # TDX：其他路徑（有些是猜的，404 代表路徑不對）
    ("TDX 國道即時訊息", TDX + "Live/News/Freeway?%24top=10&%24format=JSON"),
    ("TDX 國道即時路況", TDX + "Live/Freeway?%24top=3&%24format=JSON"),
    ("TDX 公路即時路況", TDX + "Live/Highway?%24top=3&%24format=JSON"),
    ("TDX 國道路段", TDX + "Live/Section/Freeway?%24top=3&%24format=JSON"),
    ("TDX 公路鏡頭", TDX + "CCTV/Highway?%24top=3&%24format=JSON"),
    ("TDX 國道鏡頭", TDX + "CCTV/Freeway?%24top=3&%24format=JSON"),
    ("TDX 公路 VD", TDX + "Live/VD/Highway?%24top=3&%24format=JSON"),
    ("TDX 國道 VD", TDX + "Live/VD/Freeway?%24top=3&%24format=JSON"),
    # 氣象署
    ("CWA 天氣警特報", "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001?Authorization=" + KEY),
    ("CWA 雷達回波", "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0058-001?format=JSON&Authorization=" + KEY),
]


def clean(s):
    return s.replace(KEY, "***") if KEY else s


def describe(r, name):
    """JSON 的話列出結構重點，其他就印前 300 字。"""
    try:
        data = r.json()
    except Exception:
        return clean(r.content[:300].decode("utf-8", "replace").replace("\n", " "))
    out = []
    if isinstance(data, dict):
        out.append("keys=" + ",".join(list(data.keys())[:12]))
        for k, v in data.items():
            if isinstance(v, list):
                out.append("%s: %d 筆" % (k, len(v)))
                for it in v[:12]:
                    if isinstance(it, dict):
                        t = it.get("Title") or it.get("title") or ""
                        d = (it.get("Description") or it.get("Content") or "")
                        out.append("   - 欄位=%s" % ",".join(list(it.keys())[:14]))
                        if t or d:
                            out.append("     標題=%s | 內容=%s" % (str(t)[:60], str(d)[:100]))
                        break
                # 列出所有標題
                titles = [str(it.get("Title", ""))[:50] for it in v if isinstance(it, dict) and it.get("Title")]
                if titles:
                    out.append("   全部標題: " + " / ".join(titles[:30]))
    elif isinstance(data, list):
        out.append("list %d 筆" % len(data))
        if data and isinstance(data[0], dict):
            out.append("欄位=" + ",".join(list(data[0].keys())[:14]))
    return clean(" ; ".join(out))[:2500]


lines = []
for name, url in TARGETS:
    safe = clean(url)
    try:
        r = requests.get(url, headers=UA, timeout=25)
        lines.append("%s | %s | %s | %sB | %s" % (name, safe, r.status_code, len(r.content), describe(r, name)))
    except Exception as e:
        lines.append("%s | %s | 失敗 | %s" % (name, safe, clean(str(e))[:200]))
    time.sleep(1.5)

with open("probe_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
