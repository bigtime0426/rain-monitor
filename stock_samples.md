# 台股資料集欄位與範例

執行時間：2026-10-08 16:44（台灣時間）；測試的交易日：20261007
成功 12 項，失敗 1 項。


## 說明檔裡和收盤、漲跌、家數、指數有關的資料集

### 證交所
- /exchangeReport/STOCK_DAY_AVG_ALL 上市個股日收盤價及月平均價
- /exchangeReport/STOCK_DAY_ALL 上市個股日成交資訊
- /exchangeReport/FMSRFK_ALL 上市個股月成交資訊
- /exchangeReport/FMNPTK_ALL 上市個股年成交資訊
- /exchangeReport/MI_INDEX 每日收盤行情-大盤統計資訊
- /exchangeReport/TWT88U 上市個股首五日無漲跌幅
- /exchangeReport/MI_INDEX4 每日上市上櫃跨市場成交資訊
- /indicesReport/FRMSA 寶島股價指數歷史資料
- /indicesReport/TAI50I 臺灣 50 指數歷史資料
- /exchangeReport/MI_5MINS 每 5 秒委託成交統計
- /exchangeReport/FMTQIK 集中市場每日市場成交資訊
- /exchangeReport/MI_INDEX20 集中市場每日成交量前二十名證券
- /exchangeReport/TWT53U 集中市場零股交易行情單
- /indicesReport/MI_5MINS_HIST 發行量加權股價指數歷史資料
- /block/BFIAUU_d 集中市場鉅額交易日成交量值統計
- /block/BFIAUU_m 集中市場鉅額交易月成交量值統計
- /block/BFIAUU_y 集中市場鉅額交易年成交量值統計
- /exchangeReport/STOCK_FIRST 每日第一上市外國股票成交量值
- /indicesReport/MFI94U 發行量加權股價報酬指數
- /opendata/twtazu_od 集中市場漲跌證券數統計表
- /opendata/t187ap42_L 上市認購(售)權證每日成交資料檔

### 櫃買中心
- 說明檔讀取失敗：JSONDecodeError、JSONDecodeError

## 證交所 上市收盤行情

`https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL`

通，4.9 秒，311 KB，1380 筆

欄位：
```
Date
Code
Name
TradeVolume
TradeValue
OpeningPrice
HighestPrice
LowestPrice
ClosingPrice
Change
Transaction
```

範例 1：
```
Date = 1151007
Code = 00400A
Name = 主動國泰動能高息
TradeVolume = 65642556
TradeValue = 1084672563
OpeningPrice = 16.57
HighestPrice = 16.68
LowestPrice = 16.43
ClosingPrice = 16.47
Change = -0.1400
Transaction = 17068
```

範例 2：
```
Date = 1151007
Code = 00401A
Name = 主動摩根台灣鑫收
TradeVolume = 5013388
TradeValue = 73495958
OpeningPrice = 14.70
HighestPrice = 14.74
LowestPrice = 14.62
ClosingPrice = 14.62
Change = -0.0500
Transaction = 1199
```

## 證交所 本益比、殖利率、股價淨值比

`https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL`

通，6.5 秒，113 KB，1082 筆

欄位：
```
Date
Code
Name
PEratio
DividendYield
PBratio
```

範例 1：
```
Date = 1151007
Code = 1101
Name = 台泥
PEratio = 
DividendYield = 3.14
PBratio = 0.83
```

範例 2：
```
Date = 1151007
Code = 1102
Name = 亞泥
PEratio = 9.92
DividendYield = 6.41
PBratio = 0.69
```

## 證交所 融資融券餘額

`https://openapi.twse.com.tw/v1/exchangeReport/MI_MARGN`

通，6.7 秒，456 KB，1298 筆

欄位：
```
股票代號
股票名稱
融資買進
融資賣出
融資現金償還
融資前日餘額
融資今日餘額
融資限額
融券買進
融券賣出
融券現券償還
融券前日餘額
融券今日餘額
融券限額
資券互抵
註記
```

範例 1：
```
股票代號 = 00400A
股票名稱 = 主動國泰動能高息
融資買進 = 3696
融資賣出 = 2132
融資現金償還 = 
融資前日餘額 = 10870
融資今日餘額 = 12434
融資限額 = 474035
融券買進 = 
融券賣出 = 
融券現券償還 = 
融券前日餘額 = 
融券今日餘額 = 
融券限額 = 474035
資券互抵 = 
註記 =  
```

範例 2：
```
股票代號 = 00401A
股票名稱 = 主動摩根台灣鑫收
融資買進 = 59
融資賣出 = 113
融資現金償還 = 
融資前日餘額 = 1902
融資今日餘額 = 1848
融資限額 = 64848
融券買進 = 
融券賣出 = 
融券現券償還 = 
融券前日餘額 = 2
融券今日餘額 = 2
融券限額 = 64848
資券互抵 = 
註記 = X 
```

## 證交所 三大法人買賣超（網站 JSON）

`https://www.twse.com.tw/rwd/zh/fund/T86`　參數：{'date': '20261007', 'selectType': 'ALLBUT0999', 'response': 'json'}

通，1.7 秒，186 KB，1339 筆；stat=OK，date=20261007，title=115年10月07日 三大法人買賣超日報

欄位：
```
證券代號
證券名稱
外陸資買進股數(不含外資自營商)
外陸資賣出股數(不含外資自營商)
外陸資買賣超股數(不含外資自營商)
外資自營商買進股數
外資自營商賣出股數
外資自營商買賣超股數
投信買進股數
投信賣出股數
投信買賣超股數
自營商買賣超股數
自營商買進股數(自行買賣)
自營商賣出股數(自行買賣)
自營商買賣超股數(自行買賣)
自營商買進股數(避險)
自營商賣出股數(避險)
自營商買賣超股數(避險)
三大法人買賣超股數
```

範例 1：
```
證券代號 = 1301
證券名稱 = 台塑            
外陸資買進股數(不含外資自營商) = 50,263,875
外陸資賣出股數(不含外資自營商) = 14,595,540
外陸資買賣超股數(不含外資自營商) = 35,668,335
外資自營商買進股數 = 0
外資自營商賣出股數 = 0
外資自營商買賣超股數 = 0
投信買進股數 = 10,282,000
投信賣出股數 = 0
投信買賣超股數 = 10,282,000
自營商買賣超股數 = 1,952,676
自營商買進股數(自行買賣) = 788,561
自營商賣出股數(自行買賣) = 228,000
自營商買賣超股數(自行買賣) = 560,561
自營商買進股數(避險) = 1,637,235
自營商賣出股數(避險) = 245,120
自營商買賣超股數(避險) = 1,392,115
三大法人買賣超股數 = 47,903,011
```

範例 2：
```
證券代號 = 00403A
證券名稱 = 主動統一升級50  
外陸資買進股數(不含外資自營商) = 37,904,345
外陸資賣出股數(不含外資自營商) = 23,246,256
外陸資買賣超股數(不含外資自營商) = 14,658,089
外資自營商買進股數 = 0
外資自營商賣出股數 = 0
外資自營商買賣超股數 = 0
投信買進股數 = 0
投信賣出股數 = 0
投信買賣超股數 = 0
自營商買賣超股數 = 21,571,222
自營商買進股數(自行買賣) = 0
自營商賣出股數(自行買賣) = 0
自營商買賣超股數(自行買賣) = 0
自營商買進股數(避險) = 41,165,561
自營商賣出股數(避險) = 19,594,339
自營商買賣超股數(避險) = 21,571,222
三大法人買賣超股數 = 36,229,311
```

## 櫃買 上櫃本益比、殖利率、股價淨值比

`https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis`

通，1.0 秒，152 KB，886 筆

欄位：
```
Date
SecuritiesCompanyCode
CompanyName
PriceEarningRatio
DividendPerShare
YieldRatio
PriceBookRatio
```

範例 1：
```
Date = 1151007
SecuritiesCompanyCode = 1240
CompanyName = 茂生農經
PriceEarningRatio = 10.02
DividendPerShare = 0.50000000
YieldRatio = 0.93
PriceBookRatio = 1.59
```

範例 2：
```
Date = 1151007
SecuritiesCompanyCode = 1259
CompanyName = 安心
PriceEarningRatio = 18.50
DividendPerShare = 1.20000000
YieldRatio = 1.83
PriceBookRatio = 0.76
```

## 櫃買 上櫃融資融券餘額

`https://www.tpex.org.tw/openapi/v1/tpex_mainboard_margin_balance`

通，5.9 秒，537 KB，919 筆

欄位：
```
Date
SecuritiesCompanyCode
CompanyName
MarginPurchaseBalancePreviousDay
MarginPurchase
MarginSales
CashRedemption
MarginPurchaseBalance
MarginPurchaseBalanceBelongSecuritiesFinanceEnterprise
MarginPurchaseUtilizationRate
MarginPurchaseQuota
ShortSaleBalancePreviousDay
ShortSale
ShortConvering
StockRedemption
ShortSaleBalance
ShortSaleBalanceBelongSecuritiesFinanceEnterprise
ShortSaleUtilizationRate
ShortSaleQuota
Offsetting
Note
```

範例 1：
```
Date = 1151007
SecuritiesCompanyCode = 00411A
CompanyName = 主動統一前沿科技
MarginPurchaseBalancePreviousDay = 9619
MarginPurchase = 1481
MarginSales = 438
CashRedemption = 0
MarginPurchaseBalance = 10662
MarginPurchaseBalanceBelongSecuritiesFinanceEnterprise = 3
MarginPurchaseUtilizationRate = 10.16
MarginPurchaseQuota = 104894
ShortSaleBalancePreviousDay = 12
ShortSale = 0
ShortConvering = 0
StockRedemption = 0
ShortSaleBalance = 12
ShortSaleBalanceBelongSecuritiesFinanceEnterprise = 0
ShortSaleUtilizationRate = 0.01
ShortSaleQuota = 104894
Offsetting = 85
Note = 
```

範例 2：
```
Date = 1151007
SecuritiesCompanyCode = 00679B
CompanyName = 元大美債20年
MarginPurchaseBalancePreviousDay = 4625
MarginPurchase = 37
MarginSales = 44
CashRedemption = 0
MarginPurchaseBalance = 4618
MarginPurchaseBalanceBelongSecuritiesFinanceEnterprise = 137
MarginPurchaseUtilizationRate = 0.29
MarginPurchaseQuota = 1558548
ShortSaleBalancePreviousDay = 4
ShortSale = 1
ShortConvering = 0
StockRedemption = 0
ShortSaleBalance = 5
ShortSaleBalanceBelongSecuritiesFinanceEnterprise = 0
ShortSaleUtilizationRate = 0.0
ShortSaleQuota = 1558548
Offsetting = 0
Note = 
```

## 櫃買 上櫃三大法人買賣明細

`https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading`

通，2.2 秒，824 KB，892 筆

欄位：
```
Date
SecuritiesCompanyCode
CompanyName
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Buy
 Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Sell
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference
Foreign Dealers-Total Buy
Foreign Dealers-TotalSell
ForeignDealers-Difference
ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy
ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell
ForeignInvestorsInclude MainlandAreaInvestors-Difference
SecuritiesInvestmentTrustCompanies-TotalBuy
SecuritiesInvestmentTrustCompanies-TotalSell
SecuritiesInvestmentTrustCompanies-Difference
Dealers-TotalBuy
Dealers-TotalSell
Dealers-Difference
Dealers -TotalSell
TotalDifference
```

範例 1：
```
Date = 1151008
SecuritiesCompanyCode = 00411A
CompanyName = 主動統一前沿科技
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Buy = 1304000
 Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Sell = 1619500
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference = -315500
Foreign Dealers-Total Buy = 0
Foreign Dealers-TotalSell = 0
ForeignDealers-Difference = 0
ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy = 1304000
ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell = 1619500
ForeignInvestorsInclude MainlandAreaInvestors-Difference = -315500
SecuritiesInvestmentTrustCompanies-TotalBuy = 0
SecuritiesInvestmentTrustCompanies-TotalSell = 0
SecuritiesInvestmentTrustCompanies-Difference = 0
Dealers-TotalBuy = 2851583
Dealers-TotalSell = 6046351
Dealers-Difference = -3194768
Dealers -TotalSell = 6046351
TotalDifference = -3510268
```

範例 2：
```
Date = 1151008
SecuritiesCompanyCode = 00679B
CompanyName = 元大美債20年
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Buy = 4603133
 Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Total Sell = 347000
Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference = 4256133
Foreign Dealers-Total Buy = 0
Foreign Dealers-TotalSell = 0
ForeignDealers-Difference = 0
ForeignInvestorsIncludeMainlandAreaInvestors-TotalBuy = 4603133
ForeignInvestorsIncludeMainlandAreaInvestors-TotalSell = 347000
ForeignInvestorsInclude MainlandAreaInvestors-Difference = 4256133
SecuritiesInvestmentTrustCompanies-TotalBuy = 0
SecuritiesInvestmentTrustCompanies-TotalSell = 0
SecuritiesInvestmentTrustCompanies-Difference = 0
Dealers-TotalBuy = 3624000
Dealers-TotalSell = 6598243
Dealers-Difference = -2974243
Dealers -TotalSell = 6598243
TotalDifference = 1281890
```

## 櫃買 上櫃收盤行情候選 /tpex_mainboard_daily_close_quotes

`https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes`

**失敗**：ChunkedEncodingError、ChunkedEncodingError

## 證交所 候選 /exchangeReport/MI_INDEX

`https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX`

通，2.6 秒，44 KB，265 筆

欄位：
```
日期
指數
收盤指數
漲跌
漲跌點數
漲跌百分比
特殊處理註記
```

範例 1：
```
日期 = 1151007
指數 = 寶島股價指數
收盤指數 = 55225.47
漲跌 = -
漲跌點數 = 20.23
漲跌百分比 = -0.04
特殊處理註記 = 
```

範例 2：
```
日期 = 1151007
指數 = 發行量加權股價指數
收盤指數 = 49806.37
漲跌 = -
漲跌點數 = 16.18
漲跌百分比 = -0.03
特殊處理註記 = 
```

## 證交所 候選 /exchangeReport/TWT88U

`https://openapi.twse.com.tw/v1/exchangeReport/TWT88U`

通，1.9 秒，0 KB，1 筆

欄位：
```
SecurCode
SecurName
1stTradingDate
5thTradingDate
PriceUnderwritten
OverAllotmentShares
Code
Name
BuySell
TradingPrice
TradingVolume
AccTradingVolume
```

範例 1：
```
SecurCode = 7689
SecurName = 大鵬科CLMX
1stTradingDate = 1150728
5thTradingDate = 1150803
PriceUnderwritten = 180.53
OverAllotmentShares = 680
Code = 11
Name = 富邦
BuySell = B
TradingPrice = 176.0000
TradingVolume = 30
AccTradingVolume = 30
```

## 證交所 候選 /exchangeReport/MI_INDEX4

`https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX4`

通，0.6 秒，0 KB，5 筆

欄位：
```
Date
TradeValue
FormosaIndex
Change
```

範例 1：
```
Date = 1151001
TradeValue = 1138866899385
FormosaIndex = 53622.96
Change = 442.31
```

範例 2：
```
Date = 1151002
TradeValue = 1220992750811
FormosaIndex = 53820.56
Change = 197.60
```

## 證交所 候選 /exchangeReport/MI_INDEX20

`https://openapi.twse.com.tw/v1/exchangeReport/MI_INDEX20`

通，1.6 秒，5 KB，20 筆

欄位：
```
Date
Rank
Code
Name
TradeVolume
Transaction
OpeningPrice
HighestPrice
LowestPrice
ClosingPrice
Dir
Change
LastBestBidPrice
LastBestAskPrice
```

範例 1：
```
Date = 20261007
Rank = 1
Code = 2409
Name = 友達
TradeVolume = 349688890
Transaction = 129730
OpeningPrice = 37.50
HighestPrice = 38.15
LowestPrice = 37.00
ClosingPrice = 37.95
Dir = +
Change = 0.50
LastBestBidPrice = 37.90
LastBestAskPrice = 37.95
```

範例 2：
```
Date = 20261007
Rank = 2
Code = 00406A
Name = 主動中信台灣收益
TradeVolume = 276458470
Transaction = 53756
OpeningPrice = 10.30
HighestPrice = 10.35
LowestPrice = 10.22
ClosingPrice = 10.24
Dir = -
Change = 0.09
LastBestBidPrice = 10.23
LastBestAskPrice = 10.24
```

## 證交所 候選 /opendata/twtazu_od

`https://openapi.twse.com.tw/v1/opendata/twtazu_od`

通，2.4 秒，0 KB，2 筆

欄位：
```
出表日期
類型
上漲
漲停
下跌
跌停
持平
未成交
無比價
```

範例 1：
```
出表日期 = 1150605
類型 = 整體市場
上漲 = 3144
漲停 = 43
下跌 = 9578
跌停 = 355
持平 = 459
未成交 = 15058
無比價 = 2520
```

範例 2：
```
出表日期 = 1150605
類型 = 股票
上漲 = 342
漲停 = 19
下跌 = 671
跌停 = 10
持平 = 59
未成交 = 2
無比價 = 4
```

