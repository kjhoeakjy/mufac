"""Probe 2: field names and paging limits."""
import json, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36", "Referer": "https://m.stock.naver.com/"}
def get(u, n=6000):
    try:
        r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30); b = r.read()
        try: t = b.decode("utf-8")
        except: t = b.decode("euc-kr", "replace")
        print(f"=== {r.status} len={len(b)} {u}\n{t[:n]}\n")
        return t
    except Exception as e:
        print(f"=== ERR {u}: {e}\n")
get("https://m.stock.naver.com/api/stock/005930/integration", 20000)
get("https://m.stock.naver.com/api/stock/005930/trend?pageSize=100&page=2", 800)
get("https://m.stock.naver.com/api/stock/005930/trend?pageSize=500&page=1", 300)
t = get("https://api.finance.naver.com/siseJson.naver?symbol=005930&requestType=1&startTime=20190101&endTime=20261106&timeframe=day", 300)
print("siseJson rows ~", t.count("\n") if t else None)
get("https://fchart.stock.naver.com/sise.nhn?symbol=KOSPI&timeframe=day&count=3&requestType=0", 600)
get("https://fchart.stock.naver.com/sise.nhn?symbol=KOSDAQ&timeframe=day&count=3&requestType=0", 600)
get("https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page=1&pageSize=2", 3000)
get("https://m.stock.naver.com/api/stock/005930/finance/annual", 1500)
get("https://m.stock.naver.com/api/stock/005930/overview", 2000)
get("https://m.stock.naver.com/api/stock/005930/sameIndustry", 2000)
get("https://m.stock.naver.com/api/stocks/industry/KOSPI?page=1&pageSize=3", 2000)
get("https://m.stock.naver.com/api/stock/005930/sise/day?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/shortSelling?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/creditLoan?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/investorTrend?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/investor/daily?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/exchange/KOSPI/marketmeasure", 1500)
get("https://m.stock.naver.com/api/stocks/rising/KOSDAQ?page=1&pageSize=2", 800)
get("https://m.stock.naver.com/api/stocks/upperLimit/KOSDAQ?page=1&pageSize=2", 800)
get("https://m.stock.naver.com/api/stocks/mostSearched/KOSDAQ?page=1&pageSize=2", 800)
get("https://m.stock.naver.com/api/stocks/searchTop/KOSDAQ?page=1&pageSize=2", 800)
get("https://m.stock.naver.com/api/stock/005930/market/finance", 800)
get("https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=searchInvestAttentWarnRiskySub&currentPageSize=15&pageIndex=1&searchCorpName=&repIsuSrtCd=&forward=investattentwarnrisky_sub&startDate=2026-10-01&endDate=2026-11-06&marketType=&investattentwarnriskyType=0", 3000)
get("https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?range=1mo&interval=1d", 500)
get("https://query1.finance.yahoo.com/v8/finance/chart/%5ESOX?range=1mo&interval=1d", 500)
get("https://finance.naver.com/sise/sise_market_sum.naver?sosok=1&page=1", 400)
