# 資料來源連線探測

執行時間：2026-10-08 16:35（台灣時間）；測試的交易日：20261007；TDX：金鑰

| 類別 | 項目 | 結果 | 秒 | 說明 |
| --- | --- | --- | --- | --- |
| 台股 | 證交所 OpenAPI 說明檔（列出所有可用資料集） | 通 | 4.8 | paths 143 個（302 KB） |
| 台股 | 證交所 全部個股收盤行情 | 通 | 6.4 | (最外層)：1380 筆；欄位 ['Date', 'Code', 'Name', 'TradeVolume', 'TradeValue', 'OpeningPrice', 'HighestPrice', 'LowestPrice', 'ClosingPrice', 'Change', 'Transaction']（311 KB） |
| 台股 | 證交所 本益比、殖利率、股價淨值比 | 通 | 2.3 | (最外層)：1082 筆；欄位 ['Date', 'Code', 'Name', 'PEratio', 'DividendYield', 'PBratio']（113 KB） |
| 台股 | 證交所 融資融券餘額 | 通 | 12.5 | (最外層)：1298 筆；欄位 ['股票代號', '股票名稱', '融資買進', '融資賣出', '融資現金償還', '融資前日餘額', '融資今日餘額', '融資限額', '融券買進', '融券賣出', '融券現券償還', '融券前日餘額']（456 KB） |
| 台股 | 證交所 三大法人買賣超（日，網站 JSON） | 通 | 6.2 | dict；鍵 ['stat', 'date', 'title', 'hints', 'fields', 'data', 'selectType', 'notes', 'total']（186 KB）；stat=OK |
| 台股 | 櫃買中心 OpenAPI 說明檔 | 通 | 17.3 | paths 225 個（465 KB） |
| 台股 | 櫃買中心 上櫃收盤行情 | 連不上 | 32.3 | ChunkedEncodingError |
| 台股 | 櫃買中心 三大法人（路徑為推測） | 通 | 6.1 | (最外層)：892 筆；欄位 ['Date', 'SecuritiesCompanyCode', 'CompanyName', 'Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Buy', ' Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Sell', 'Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference', 'Foreign Dealers-Total Buy', 'Foreign Dealers-TotalSell', 'ForeignDealers-Difference', 'ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy', 'ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell', 'ForeignInvestorsInclude MainlandAreaInvestors-Difference']（824 KB） |
| 山區道路 | 氣象署 顯著有感地震報告 | 通 | 1.6 | result.fields：34 筆；欄位 ['id', 'type']（14 KB） |
| 山區道路 | 氣象署 小區域有感地震報告 | 通 | 1.7 | result.fields：36 筆；欄位 ['id', 'type']（89 KB） |
| 山區道路 | TDX 省道 事件／封路通報（News） | 通 | 1.2 | Newses：3 筆；欄位 ['NewsID', 'Language', 'Title', 'NewsCategory', 'Description', 'PublishTime', 'UpdateTime']（1 KB） |
| 山區道路 | TDX 省道 即時事件（Event，路徑為推測） | HTTP 404 | 0.9 | 31 bytes |
| 淹水 | 民生公共物聯網 水利署感測器（路徑為推測） | 連不上 | 0.5 | SSLError |
| 淹水 | 水利署 開放資料 即時水位（資料集代碼為推測） | HTTP 404 | 5.0 | 303905 bytes |
| 其他 | USGS 全球地震（近 24 小時） | 通 | 0.1 | features：219 筆；欄位 ['type', 'properties', 'geometry', 'id']（152 KB） |
| 其他 | TDX YouBike 台北車位 | 通 | 1.1 | (最外層)：3 筆；欄位 ['StationUID', 'StationID', 'ServiceStatus', 'ServiceType', 'AvailableRentBikes', 'AvailableReturnBikes', 'SrcUpdateTime', 'UpdateTime', 'AvailableRentBikesDetail']（0 KB） |
| 其他 | TDX 台鐵 即時到離站 | 通 | 1.2 | (最外層)：3 筆；欄位 ['StationID', 'StationName', 'TrainNo', 'Direction', 'TrainTypeID', 'TrainTypeCode', 'TrainTypeName', 'TripLine', 'EndingStationID', 'EndingStationName', 'ScheduledArrivalTime', 'ScheduledDepartureTime']（1 KB） |
| 其他 | 環境部 空氣品質（需免費金鑰 MOENV_API_KEY） | 略過 |  | 沒有設定 MOENV_API_KEY，這項沒測 |
| 其他 | 疾管署 開放資料（路徑為推測） | 連不上 | 10.2 | ConnectTimeout |
| 其他 | GDELT 新聞搜尋 | 連不上 | 10.2 | ReadTimeout |
| 其他 | 世界銀行 台灣 GDP | 通 | 3.6 | (最外層)：2 筆；欄位 ['page', 'pages', 'per_page', 'total', 'sourceid', 'lastupdated']（0 KB） |

## 證交所 OpenAPI 說明檔（列出所有可用資料集）：和法人、融資券、本益比有關的資料集
- /exchangeReport/BWIBBU_ALL 上市個股日本益比、殖利率及股價淨值比（依代碼查詢）
- /exchangeReport/MI_MARGN 集中市場融資融券餘額
- /exchangeReport/BWIBBU_d 上市個股日本益比、殖利率及股價淨值比（依日期查詢）
- /SBL/TWT96U 上市上櫃股票當日可借券賣出股數

## 櫃買中心 OpenAPI 說明檔：和法人、融資券、本益比有關的資料集
- /tpex_mainboard_peratio_analysis 上櫃股票個股本益比、殖利率、股價淨值比
- /tpex_mainboard_margin_balance 上櫃股票融資融券餘額
- /tpex_margin_sbl 上櫃股票融券借券賣出餘額
- /tpex_margin_trading_term 上櫃融資融券暫停融券賣出預告表
- /tpex_margin_trading_adjust 上櫃融資融券調整成數
- /tpex_margin_trading_lend 上櫃融資融券標借
- /tpex_margin_trading_marginspot 上櫃信用交易餘額概況表
- /tpex_margin_trading_margin_mark 上櫃平盤下得融(借)券賣出之證券名單
- /tpex_margin_trading_margin_used 上櫃融資融券使用率報表
- /tpex_margin_trading_short_sell 上櫃融資融券增減排行表
- /tpex_3insti_qfii 上櫃僑外資及陸資持股比例排行表
- /tpex_3insti_qfii_industry 上櫃各類股僑外資及陸資持股比例表
- /tpex_3insti_daily_trading 上櫃股票三大法人買賣明細資訊
- /tpex_3insti_dealer_trading 上櫃股票自營商買賣超彙總表
- /tpex_short_sell 上櫃當日融券賣出與借券賣出成交量值
- /tpex_intraday_fee 上櫃應付現股當日沖銷券差借券費率
- /tpex_pe_ratio_top10 上櫃歷史個股本益比排行
- /tpex_3insti_summary 上櫃股票三大法人買賣金額彙總表
- /tpex_3insti_trading 上櫃股票投信買賣超彙總表
- /tpex_3insti_qfii_trading 上櫃股票外資及陸資買賣超彙總表
