"""一次性探測：從 GitHub 機器實測各官方交通／雨災資料源連不連得到。
結果寫到 probe_result.txt（只記狀態碼、大小、前 300 字，不含金鑰）。"""
import os
import time
import requests

KEY = os.environ.get("CWA_API_KEY", "")
UA = {"User-Agent": "Mozilla/5.0"}

TARGETS = [
    # 國道（高公局）
    ("國道 5分鐘路段等級", "https://tisvcloud.freeway.gov.tw/roadlevel_value5.xml.gz"),
    ("國道 VD 5分鐘", "https://tisvcloud.freeway.gov.tw/vd_value5.xml.gz"),
    ("國道 CMS 看板", "https://tisvcloud.freeway.gov.tw/cms_value.xml.gz"),
    ("國道 首頁", "https://tisvcloud.freeway.gov.tw/"),
    ("1968 路況頁", "https://1968.freeway.gov.tw/roadcctv"),
    # TDX（只測連線：沒帶帳號，回 400/401/405 都代表連得到）
    ("TDX token", "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"),
    ("TDX API 根", "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/News/Highway?%24top=1&%24format=JSON"),
    # 縣市 eTag 即時路況（NCHC 文件）
    ("eTag 文件", "https://adsapi.stois.nchc.tw/docs.json"),
    # 民生公共物聯網（水利署淹水感測等）
    ("SensorThings 水資源", "https://sta.ci.taiwan.gov.tw/STA_WaterResource_v2/v1.0/Things?%24top=1"),
    # 台北
    ("台北 ITS", "https://its.taipei.gov.tw/"),
    ("台北 ITS CCTV API", "https://its.taipei.gov.tw/api/CCTVByLBS"),
    # 公路局
    ("公路局鏡頭", "https://cctv-ss07.thb.gov.tw/T15-0K+500/snapshot"),
    ("公路局 首頁", "https://www.thb.gov.tw/"),
    # 氣象署（用既有 CWA_API_KEY）
    ("CWA 天氣警特報", "https://opendata.cwa.gov.tw/api/v1/rest/datastore/W-C0033-001?Authorization=" + KEY),
    ("CWA 雷達回波", "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/O-A0058-001?format=JSON&Authorization=" + KEY),
]

lines = []
for name, url in TARGETS:
    safe = url.replace(KEY, "***") if KEY else url
    try:
        r = requests.get(url, headers=UA, timeout=20)
        body = r.content[:300]
        try:
            snippet = body.decode("utf-8", "replace")
        except Exception:
            snippet = repr(body)
        snippet = snippet.replace("\n", " ").replace(KEY, "***") if KEY else snippet.replace("\n", " ")
        lines.append("%s | %s | %s | %sB | %s | %s" % (
            name, safe, r.status_code, len(r.content), r.headers.get("content-type", ""), snippet[:200]))
    except Exception as e:
        lines.append("%s | %s | 失敗 | %s" % (name, safe, str(e).replace(KEY, "***")[:200] if KEY else str(e)[:200]))
    time.sleep(1)

with open("probe_result.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("\n".join(lines))
