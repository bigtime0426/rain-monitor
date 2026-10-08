"""第三輪探測：驗證 TDX 金鑰，並印出路況、路段位置、氣象署特報／雷達的實際內容樣本。
結果寫到 probe_result.txt。不會印出任何金鑰或 token。"""
import os
import time
import requests

CWA = os.environ.get("CWA_API_KEY", "")
TID = os.environ.get("TDX_CLIENT_ID", "")
TSEC = os.environ.get("TDX_CLIENT_SECRET", "")
UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/"
secrets = [s for s in (CWA, TID, TSEC) if s]

lines = []


def clean(s):
    s = str(s)
    for k in secrets:
        s = s.replace(k, "***")
    return s


def log(*a):
    lines.append(clean(" ".join(str(x) for x in a)))


# 1. 取得 TDX token
token = None
try:
    r = requests.post(
        "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token",
        data={"grant_type": "client_credentials", "client_id": TID, "client_secret": TSEC},
        headers=UA, timeout=25)
    log("TDX token | 狀態", r.status_code, "| 有 secret:", bool(TSEC), "| 有 id:", bool(TID))
    if r.status_code == 200:
        token = r.json().get("access_token")
        log("TDX token | 取得成功，長度", len(token or ""))
    else:
        log("TDX token | 失敗內容:", r.text[:200])
except Exception as e:
    log("TDX token | 例外", e)

H = dict(UA)
if token:
    H["Authorization"] = "Bearer " + token


def get(name, url, headers, n=1200):
    try:
        r = requests.get(url, headers=headers, timeout=30)
        body = r.content[:n].decode("utf-8", "replace").replace("\n", " ")
        log("==", name, "|", r.status_code, "|", len(r.content), "B")
        log("   ", body)
    except Exception as e:
        log("==", name, "| 失敗", str(e)[:200])
    time.sleep(1.5)


# 2. TDX（帶金鑰）
get("省道即時路況(帶金鑰)", BASE + "Live/Highway?%24top=2&%24format=JSON", H, 1500)
get("國道即時路況(帶金鑰)", BASE + "Live/Freeway?%24top=2&%24format=JSON", H, 1500)
get("省道路段(Section)", BASE + "Section/Highway?%24top=1&%24format=JSON", H, 1500)
get("國道路段(Section)", BASE + "Section/Freeway?%24top=1&%24format=JSON", H, 1500)
get("省道路段(Link)", BASE + "Link/Highway?%24top=1&%24format=JSON", H, 1200)
get("省道鏡頭(帶金鑰)", BASE + "CCTV/Highway?%24top=1&%24format=JSON", H, 1500)
get("省道即時訊息 分類", BASE + "Live/News/Highway?%24top=5&%24select=Title,NewsCategory&%24format=JSON", H, 800)

# 3. 氣象署
get("CWA 天氣警特報", "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001?Authorization=" + CWA, UA, 2500)
get("CWA 雷達回波", "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0058-001?format=JSON&Authorization=" + CWA, UA, 1200)

with open("probe_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
