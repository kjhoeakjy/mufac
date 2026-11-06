"""Probe 3: trend paging, industry, basic full dump, throughput."""
import json, time, urllib.request, urllib.parse, concurrent.futures as cf
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36", "Referer": "https://m.stock.naver.com/"}
def get(u, n=3000, data=None, hdr=None):
    try:
        h = dict(UA); h.update(hdr or {})
        r = urllib.request.urlopen(urllib.request.Request(u, headers=h, data=data), timeout=30); b = r.read()
        try: t = b.decode("utf-8")
        except: t = b.decode("euc-kr", "replace")
        print(f"=== {r.status} len={len(b)} {u}\n{t[:n]}\n"); return t
    except Exception as e:
        print(f"=== ERR {u}: {e}\n")
get("https://m.stock.naver.com/api/stock/005930/basic", 9000)
for ps, pg in [(20,1),(20,2),(20,30),(20,100),(30,1),(50,1),(60,1),(99,1),(100,1),(10,200)]:
    t = get(f"https://m.stock.naver.com/api/stock/005930/trend?pageSize={ps}&page={pg}", 200)
    if t:
        try: j=json.loads(t); print("   rows", len(j), j[0]["bizdate"], j[-1]["bizdate"])
        except Exception as e: print("   parse", e)
get("https://m.stock.naver.com/api/stock/005930/trend?pageSize=20&page=1&bizdate=20240105", 200)
get("https://m.stock.naver.com/api/stocks/industry?page=1&pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/industry", 1500)
get("https://m.stock.naver.com/api/industries/KOSPI", 1500)
get("https://m.stock.naver.com/api/stocks/industry/KOSPI/1", 800)
get("https://finance.naver.com/sise/sise_group.naver?type=upjong", 300)
get("https://finance.naver.com/item/main.naver?code=005930", 300)
get("https://m.stock.naver.com/api/stock/005930/news/title?pageSize=1", 300)
get("https://m.stock.naver.com/api/stock/005930/disclosure?pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/analyst?pageSize=3", 800)
get("https://m.stock.naver.com/api/stocks/theme?page=1&pageSize=3", 1500)
get("https://m.stock.naver.com/api/stock/005930/consensus", 800)
get("https://m.stock.naver.com/api/stock/005930/company", 800)
get("https://m.stock.naver.com/api/stock/005930/realtime", 300)
get("https://m.stock.naver.com/api/stock/005930/integration/overview", 300)
# KIND POST
d = urllib.parse.urlencode({"method":"searchInvestAttentWarnRiskySub","currentPageSize":"15","pageIndex":"1","searchCorpName":"","repIsuSrtCd":"","forward":"investattentwarnrisky_sub","startDate":"2026-10-01","endDate":"2026-11-06","marketType":"","investattentwarnriskyType":"0"}).encode()
get("https://kind.krx.co.kr/investwarn/investattentwarnrisky.do", 3000, data=d, hdr={"Content-Type":"application/x-www-form-urlencoded","Referer":"https://kind.krx.co.kr/investwarn/investattentwarnrisky.do?method=investattentwarnriskyMain"})
# DART recent list
get("https://dart.fss.or.kr/dsac001/mainAll.do?selectDate=20261105&sort=&series=&mdayCnt=0", 300)
d = urllib.parse.urlencode({"currentPage":"1","mdayCnt":"0","selectDate":"20261105","textCrpCik":"","textCrpNm":"","pageGrouping":"","maxResults":"100"}).encode()
t = get("https://dart.fss.or.kr/dsac001/search.ax", 200, data=d, hdr={"Content-Type":"application/x-www-form-urlencoded","Referer":"https://dart.fss.or.kr/dsac001/mainAll.do"})
if t:
    import re; print("   DART rows:", len(re.findall(r'<tr', t)), "|", re.sub(r'\s+',' ', t)[2000:3500])
# throughput: universe page + 60 siseJson
codes = []
for pg in (1,2):
    j = json.loads(get(f"https://m.stock.naver.com/api/stocks/marketValue/KOSDAQ?page={pg}&pageSize=100", 0))
    codes += [s["itemCode"] for s in j["stocks"] if s["stockEndType"]=="stock"]
codes = codes[:80]
def one(c):
    t0=time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"https://api.finance.naver.com/siseJson.naver?symbol={c}&requestType=1&startTime=20190101&endTime=20261231&timeframe=day", headers=UA), timeout=30)
        return (r.status, len(r.read()), time.time()-t0)
    except Exception as e: return (str(e), 0, time.time()-t0)
t0=time.time()
with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(one, codes))
print("siseJson x80 @16 threads:", round(time.time()-t0,1), "s; statuses", {r[0] for r in res}, "bytes", sum(r[1] for r in res))
def two(c):
    t0=time.time()
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"https://m.stock.naver.com/api/stock/{c}/trend?pageSize=20&page=1", headers=UA), timeout=30)
        return (r.status, len(r.read()), time.time()-t0)
    except Exception as e: return (str(e), 0, time.time()-t0)
t0=time.time()
with cf.ThreadPoolExecutor(16) as ex: res = list(ex.map(two, codes))
print("trend x80 @16 threads:", round(time.time()-t0,1), "s; statuses", {r[0] for r in res})
