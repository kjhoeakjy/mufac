"""Probe free Korean market data endpoints from the Actions runner."""
import json, sys, urllib.request, ssl
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
      "Referer": "https://finance.naver.com/"}
URLS = [
 "https://m.stock.naver.com/api/stocks/up/KOSPI?page=1&pageSize=2",
 "https://m.stock.naver.com/api/stocks/upper/KOSDAQ?page=1&pageSize=2",
 "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page=1&pageSize=2",
 "https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page=1&pageSize=100",
 "https://polling.finance.naver.com/api/realtime/domestic/stock/005930,000660",
 "https://fchart.stock.naver.com/sise.nhn?symbol=005930&timeframe=day&count=3&requestType=0",
 "https://api.finance.naver.com/siseJson.naver?symbol=005930&requestType=1&startTime=20251001&endTime=20251003&timeframe=day",
 "https://m.stock.naver.com/api/stock/005930/basic",
 "https://m.stock.naver.com/api/stock/005930/integration",
 "https://m.stock.naver.com/api/stock/005930/trend?pageSize=3",
 "https://m.stock.naver.com/api/news/stock/005930?pageSize=2&page=1",
 "https://finance.naver.com/item/frgn.naver?code=005930",
 "https://finance.naver.com/sise/sise_upper.naver",
 "https://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
 "https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=investattentwarnriskyMain",
 "https://dart.fss.or.kr/dsac001/mainAll.do",
 "https://opendart.fss.or.kr/api/list.json",
 "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?range=5d&interval=1d",
 "https://query1.finance.yahoo.com/v8/finance/chart/KRW%3DX?range=5d&interval=1d",
 "https://stooq.com/q/d/l/?s=^ndx&i=d",
 "https://www.nextrade.co.kr/",
 "https://m.stock.naver.com/api/index/KOSPI/basic",
 "https://openapi.koreainvestment.com:9443",
 "https://apis.data.go.kr/1160100/service/GetStockSecuritiesInfoService/getStockPriceInfo",
]
for u in URLS:
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20)
        b = r.read()
        try: t = b.decode("utf-8")
        except: t = b.decode("euc-kr", "replace")
        print(f"=== {r.status} {u}\n{t[:1200]}\n")
    except Exception as e:
        print(f"=== ERR {u}: {e}\n")
