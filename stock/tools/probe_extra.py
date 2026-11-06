import json, urllib.request, urllib.parse
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36","Referer":"https://m.stock.naver.com/"}
def get(u,n=900,hdr=None,data=None):
    try:
        h=dict(UA); h.update(hdr or {})
        r=urllib.request.urlopen(urllib.request.Request(u,headers=h,data=data),timeout=30);t=r.read().decode("utf-8","replace")
        print(f"=== {r.status} len={len(t)} {u}\n{t[:n]}\n");return t
    except Exception as e: print(f"=== ERR {u}: {e}\n")
PC={"Referer":"https://stock.naver.com/"}
for at in ("01","02","03"):
    get(f"https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=ALL&orderType=marketAlertType&alertType={at}&startIdx=0&pageSize=100",700,PC)
get("https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=ALL&orderType=tradeStopYn&startIdx=0&pageSize=100",700,PC)
get("https://stock.naver.com/api/domestic/market/stock/default?tradeType=KRX&marketType=ALL&orderType=statusTag&startIdx=0&pageSize=100",700,PC)
get("https://finance.naver.com/sise/item_overheating_1.naver",300)
get("https://finance.naver.com/sise/investment_alert.naver?type=warning",300)
codes=["005930","000660","196170","086520","035720","068270","207940","373220","005380","000270"]
q="|".join(f"SERVICE_ITEM:{c}" for c in codes)
get(f"https://polling.finance.naver.com/api/realtime?query={q}",2500)
get("https://stock.naver.com/api/polling/domestic/NXT/stock?itemCodes="+",".join(codes),1500,PC)
get("https://stock.naver.com/api/polling/domestic/stock?itemCodes="+",".join(codes),1500,PC)
get("https://m.stock.naver.com/front-api/stock/domestic/basic?code=005930&endType=stock",1500)
T={"Referer":"https://tossinvest.com/","Origin":"https://tossinvest.com","Accept":"application/json"}
get("https://wts-info-api.tossinvest.com/api/v1/mds/info/margin-loan?stockCode=A005930&number=1&size=5",1200,T)
get("https://wts-info-api.tossinvest.com/api/v1/mds/info/margin-loan?stockCode=A005930&number=30&size=50",400,T)
get("https://wts-info-api.tossinvest.com/api/v1/mds/info/lending-trading?stockCode=A005930&number=1&size=3",900,T)
get("https://wts-info-api.tossinvest.com/api/v1/mds/info/short-selling-trend?stockCode=A005930&number=1&size=3",900,T)
get("https://wts-info-api.tossinvest.com/api/v1/stock-prices/after?codes="+",".join("A"+c for c in codes),1500,T)
get("https://wts-info-api.tossinvest.com/api/v1/rankings/realtime/stock?size=5",1200,T)
get("https://wts-cert-api.tossinvest.com/api/v1/stock-infos/A005930/red-flags",800,T)
get("https://wts-cert-api.tossinvest.com/api/v3/trading/order/A005930/trading-status",800,T)
get("https://wts-cert-api.tossinvest.com/api/v4/comments?subjectType=STOCK&subjectId=KR7005930003&commentSortType=RECENT",600,T)
get("https://stock.naver.com/api/community/discussion/stats/by-items?startDate=2026-10-01&domesticCodes=005930,000660,196170",1500,PC)
get("https://stock.naver.com/api/community/discussion/posts/by-item?itemCode=005930&discussionType=domesticStock&pageSize=3&isHolderOnly=false&excludesItemNews=false&isItemNewsOnly=false",800,PC)
get("https://stock.naver.com/api/domestic/market/searchTop?nationType=KOR&startIdx=0&pageSize=5",800,PC)
get("https://stock.naver.com/api/domestic/market/ipo/progress?IpoProgressType=LISTING&startIdx=0&pageSize=5",1200,PC)
get("https://stock.naver.com/api/stockSecurity/researches/v2/company/goal-price-changed?direction=up&size=3",800,PC)
get("https://stock.naver.com/api/myasset/resources/invest/stock-investor-rank?item_code=005930",600,PC)
get("https://stock.naver.com/api/stockSecurity/market-status/current?exchanges=krx&exchanges=nxt",600,PC)
get("https://m.stock.naver.com/api/stock/005930/integration",0) and print("integration ok")
t=get("https://m.stock.naver.com/api/stock/005930/integration",0)
if t:
    j=json.loads(t); print("integration keys:", list(j.keys())); print("irScheduleInfo:", json.dumps(j.get("irScheduleInfo"),ensure_ascii=False)[:500]); print("industryCompareInfo:", json.dumps(j.get("industryCompareInfo"),ensure_ascii=False)[:600])
get("https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getRestDeInfo?solYear=2026&solMonth=11&_type=json",300)
