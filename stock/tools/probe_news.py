import json, time, urllib.request
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36","Referer":"https://m.stock.naver.com/"}
def get(u,n=1500):
    try:
        r=urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=30);t=r.read().decode("utf-8","replace")
        print(f"=== {r.status} len={len(t)} {u}\n{t[:n]}\n");return t
    except Exception as e: print(f"=== ERR {u}: {e}\n")
for code in ("005930","196170","462980"):
    for ps,pg in ((100,1),(100,3),(100,10),(20,30)):
        t=get(f"https://m.stock.naver.com/api/news/stock/{code}?pageSize={ps}&page={pg}",300)
        if t:
            try:
                j=json.loads(t); items=[it for g in j for it in g.get("items",[])]
                print("   groups",len(j),"items",len(items),"dates",items[0]["datetime"] if items else None, items[-1]["datetime"] if items else None)
            except Exception as e: print("   parse",e)
    for ps,pg in ((100,1),(100,2),(500,1)):
        t=get(f"https://m.stock.naver.com/api/stock/{code}/disclosure?pageSize={ps}&page={pg}",200)
        if t:
            try: j=json.loads(t); print("   n",len(j),j[0]["datetime"],j[-1]["datetime"])
            except Exception as e: print("   parse",e)
get("https://m.stock.naver.com/api/news/stock/005930?pageSize=5&page=1&fromDate=20251001&toDate=20251003",600)
get("https://m.stock.naver.com/api/news/flash?pageSize=5&page=1",800)
get("https://m.stock.naver.com/api/news/mainnews?pageSize=5&page=1",800)
get("https://m.stock.naver.com/api/news/category/mainnews?pageSize=5",800)
get("https://m.stock.naver.com/api/news/list?pageSize=5&category=mainnews",800)
get("https://finance.naver.com/news/news_list.naver?mode=LSS2D&section_id=101&section_id2=258&date=20261105&page=1",400)
get("https://news.google.com/rss/search?q=%EC%83%81%ED%95%9C%EA%B0%80&hl=ko&gl=KR&ceid=KR:ko",600)
get("https://search.naver.com/search.naver?where=news&query=%EC%83%81%ED%95%9C%EA%B0%80&sort=1",300)
get("https://m.stock.naver.com/api/stock/005930/news/title?pageSize=1",200)
