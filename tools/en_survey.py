"""유행했던 영어 노래 가사 실측. GitHub Actions에서 돌린다(여기 컨테이너는 바깥 사이트에 못 붙는다).

  python tools/en_survey.py [--years 1990-2025] [--top 100] [--probe]

1. 위키백과 'Billboard Year-End Hot 100 singles of <연도>'에서 해마다 상위 곡 목록을 받는다.
2. 곡마다 LRCLIB(공개 가사 API)에서 가사를, Deezer 앨범 정보에서 장르를 받는다.
3. 줄 길이, 각운, 축약, 인칭, 반복, 제목 반복, 추임새, 물음·명령, 자주 쓰는 낱말 등을 센다.
결과는 assets/lyrics/_영어실측.json·md 에 통계만 남긴다. 가사 원문은 어디에도 저장하지 않는다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "assets" / "lyrics" / "_영어실측.json"
OUT_MD = ROOT / "assets" / "lyrics" / "_영어실측.md"
UA = {"User-Agent": "mufac-lyrics-survey/1.0 (https://github.com/kjhoeakjy/mufac)"}

# Deezer 장르 → 조사 묶음, 묶음 → mufac 장르
GENRE_MAP = {
    "Pop": "팝", "Films/Games": "팝", "Singer & Songwriter": "포크·컨트리",
    "Rap/Hip Hop": "힙합",
    "R&B": "R&B", "Soul & Funk": "R&B", "Jazz": "R&B", "Blues": "R&B",
    "Rock": "록", "Alternative": "록", "Metal": "록", "Indie": "록",
    "Dance": "댄스·일렉트로닉", "Electro": "댄스·일렉트로닉",
    "Country": "포크·컨트리", "Folk": "포크·컨트리",
    "Reggae": "레게·라틴", "Latino": "레게·라틴", "Latin Music": "레게·라틴",
}
MEMBERS = {
    "팝": ["팝", "발라드", "록발라드", "OST", "시티팝"],
    "힙합": ["힙합"],
    "R&B": ["R&B", "재즈", "블루스"],
    "록": ["락", "밴드", "인디밴드", "펑크", "메탈"],
    "댄스·일렉트로닉": ["댄스", "일렉트로닉"],
    "포크·컨트리": ["포크", "어쿠스틱"],
    "레게·라틴": ["레게"],
}

S = requests.Session()
S.headers.update(UA)


def get_json(url: str, params: dict | None = None, tries: int = 4):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                j = r.json()
                if isinstance(j, dict) and (j.get("error") or {}).get("code") == 4:  # Deezer 요청 한도
                    time.sleep(5)
                    continue
                return j
            if r.status_code == 404:
                return None
            time.sleep(2 * (i + 1))
        except (requests.RequestException, ValueError):
            time.sleep(2 * (i + 1))
    return None


# ---------------------------------------------------------------- 곡 목록

def year_list(year: int, top: int) -> list[dict]:
    page = f"Billboard Year-End Hot 100 singles of {year}"
    j = get_json("https://en.wikipedia.org/w/api.php",
                 {"action": "parse", "page": page, "prop": "text", "format": "json", "formatversion": 2, "redirects": 1})
    if not j or "parse" not in j:
        print(f"  {year}: 목록 없음", flush=True)
        return []
    text = j["parse"]["text"]
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", text, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        if len(cells) < 3 or not re.fullmatch(r"\d{1,3}", cells[0]):
            continue
        title = re.sub(r"\[\w+\]", "", cells[1]).strip().strip('"“”').strip()
        artist = re.sub(r"\[\w+\]", "", cells[2]).strip()
        if title and artist:
            out.append({"year": year, "rank": int(cells[0]), "title": title, "artist": artist})
    return out[:top]


def main_artist(a: str) -> str:
    return re.split(r"\s+(?:featuring|feat\.|ft\.|and|&|with|x|vs\.?)\s+|,\s*", a, flags=re.I)[0].strip()


def clean_title(t: str) -> str:
    return re.split(r"\s*/\s*", re.sub(r"\s*\(.*?\)", "", t))[0].strip()


# ---------------------------------------------------------------- 가사·장르

def fetch_lyrics(title: str, artist: str) -> list[str]:
    t, a = clean_title(title), main_artist(artist)
    for params in ({"track_name": t, "artist_name": a}, {"q": f"{a} {t}"}):
        res = get_json("https://lrclib.net/api/search", params) or []
        for r in res:
            if r.get("instrumental") or not r.get("plainLyrics"):
                continue
            if t.lower()[:12] not in (r.get("trackName") or "").lower() and "q" not in params:
                continue
            return [l.strip() for l in r["plainLyrics"].splitlines()]
    return []


_album_cache: dict[int, str] = {}


def fetch_genre(title: str, artist: str) -> str:
    t, a = clean_title(title), main_artist(artist)
    j = get_json("https://api.deezer.com/search", {"q": f'artist:"{a}" track:"{t}"', "limit": 1})
    data = (j or {}).get("data") or []
    if not data:
        j = get_json("https://api.deezer.com/search", {"q": f"{a} {t}", "limit": 1})
        data = (j or {}).get("data") or []
    if not data:
        return ""
    aid = (data[0].get("album") or {}).get("id")
    if not aid:
        return ""
    if aid not in _album_cache:
        alb = get_json(f"https://api.deezer.com/album/{aid}") or {}
        names = [g.get("name", "") for g in ((alb.get("genres") or {}).get("data") or [])]
        _album_cache[aid] = names[0] if names else ""
        time.sleep(0.12)
    return _album_cache[aid]


# ---------------------------------------------------------------- 분석

WORD = re.compile(r"[A-Za-z']+")
SECTION = re.compile(r"^\s*[\[(].*[\])]\s*$")
CONTRACTION = re.compile(r"\b(\w+n't|\w+'(?:m|re|ll|ve|d)|gonna|wanna|gotta|'cause|cause|'til|ain't|y'all|lemme|gimme|kinda|outta|tryna|'em)\b", re.I)
FILLER = re.compile(r"\b(o+h+|o+o+h*|yeah+|yea|ya+|baby|babe|hey+|na+|la+|whoa+|uh+|woo+|mm+|da+)\b", re.I)
QUESTION_START = re.compile(r"^(do|does|did|is|are|was|were|can|could|will|would|why|what|how|where|when|who|should|have|has|ain't|don't|didn't|won't|wouldn't|isn't)\b", re.I)
IMPERATIVE_START = re.compile(r"^(don't|let|let's|come|take|give|tell|hold|say|go|stay|call|look|make|show|put|leave|listen|wait|kiss|turn|get|keep|bring|run|dance|forget|remember|never|baby,? don't|just)\b", re.I)
EMOTION = re.compile(r"\b(love|loved|loving|miss|missing|hate|hurt|hurts|cry|crying|cried|sad|happy|lonely|alone|afraid|scared|broken|heartbreak|heart|feel|feeling|feelings|want|need)\b", re.I)
ABSTRACT = re.compile(r"\b(love|heart|soul|time|forever|life|dream|dreams|world|mind|truth|pain|fate|destiny|hope|faith|memory|memories|eternity|freedom)\b", re.I)
AI_CLICHE = re.compile(r"\b(neon|whispers?|echo(es)?|shadows?|tapestry|symphony|shatter(ed)?|ignite[sd]?|embers?|ethereal|celestial|velvet|silhouettes?|labyrinth|kaleidoscope|abyss|serenade|melod(y|ies)|rhythm|endless|infinite|eternity|destiny|fate|stardust|starlight|moonlight|cascade|tides?)\b", re.I)
BIG_WORDS = re.compile(r"\b(forever|eternal|eternity|destiny|fate|soul|heaven|infinity|always)\b", re.I)
STOP = set("""i you me my your the a an and to it in of on is be that this for with we our us all no not but so just like
can can't don't i'm you're it's that's what when all oh yeah baby got get gonna wanna up down out at do know now one
been was were are am have has had will would could should if or as by from there they them their he she his her its
who how why where then than too say said go make made back way never ever let see wanna 'cause cause ooh na la hey""".split())
_VOWELS = re.compile(r"[aeiouy]+")


def syllables(word: str) -> int:
    w = word.lower().strip("'")
    if not w:
        return 0
    n = len(_VOWELS.findall(w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and n > 1:
        n -= 1
    return max(1, n)


def rhyme_key(word: str) -> tuple[str, str]:
    w = re.sub(r"[^a-z]", "", word.lower())
    w = re.sub(r"in$", "ing", w) if w.endswith("in'") else w
    m = list(re.finditer(r"[aeiouy]+", w))
    if not m:
        return w, w
    last = m[-1]
    return w[last.start():], last.group()  # (각운 꼬리, 모음만)


def song_lines(lines: list[str]) -> list[str]:
    return [l for l in lines if l and not SECTION.match(l) and WORD.search(l)]


def analyze_song(title: str, lines: list[str]) -> dict | None:
    ls = song_lines(lines)
    if len(ls) < 10:
        return None
    words = [WORD.findall(l) for l in ls]
    lasts = [w[-1].lower() if w else "" for w in words]
    keys = [rhyme_key(x) for x in lasts]
    rhyme = assonance = same_word = 0
    for i in range(1, len(ls)):
        prev = range(max(0, i - 3), i)
        if any(lasts[j] == lasts[i] for j in prev):
            same_word += 1
        elif any(keys[j][0] == keys[i][0] and len(keys[i][0]) >= 2 for j in prev):
            rhyme += 1
        elif any(keys[j][1] == keys[i][1] for j in prev):
            assonance += 1
    c = Counter(l.lower() for l in ls)
    tnorm = re.sub(r"[^a-z' ]", "", clean_title(title).lower()).strip()
    body = " ".join(ls).lower()
    first = words[0][0].lower() if words[0] else ""
    return {
        "n": len(ls), "unique": len(c),
        "words": [len(w) for w in words],
        "syl": [sum(syllables(x) for x in w) for w in words],
        "rhyme": rhyme, "assonance": assonance, "same_word": same_word,
        "repeat": sum(n for n in c.values() if n > 1),
        "top_repeat": c.most_common(1)[0][1],
        "title_hits": body.count(tnorm) if len(tnorm) >= 3 else 0,
        "contraction": sum(1 for l in ls if CONTRACTION.search(l)),
        "filler": sum(1 for l in ls if FILLER.search(l)),
        "you": sum(1 for l in ls if re.search(r"\b(you|your|you're|you'll|you've|yours)\b", l, re.I)),
        "i": sum(1 for l in ls if re.search(r"\b(i|i'm|i'll|i've|i'd|me|my|mine)\b", l, re.I)),
        "we": sum(1 for l in ls if re.search(r"\b(we|we're|us|our)\b", l, re.I)),
        "question": sum(1 for l in ls if l.rstrip().endswith("?") or QUESTION_START.match(l)),
        "imperative": sum(1 for l in ls if IMPERATIVE_START.match(l)),
        "emotion": sum(1 for l in ls if EMOTION.search(l)),
        "abstract": sum(1 for l in ls if ABSTRACT.search(l)),
        "cliche": sum(1 for l in ls if AI_CLICHE.search(l)),
        "big": sum(1 for l in ls if BIG_WORDS.search(l)),
        "first_word": first,
        "ends": Counter(lasts),
        "starts": Counter(w[0].lower() for w in words if w),
        "content": Counter(x.lower() for w in words for x in w if x.lower() not in STOP and len(x) > 2),
    }


def aggregate(items: list[dict]) -> dict:
    if not items:
        return {}
    N = sum(x["n"] for x in items)
    allw = [v for x in items for v in x["words"]]
    alls = [v for x in items for v in x["syl"]]
    pct = lambda k: round(sum(x[k] for x in items) * 100 / N, 1)
    ends, starts, content = Counter(), Counter(), Counter()
    for x in items:
        ends.update(x["ends"]); starts.update(x["starts"]); content.update(x["content"])
    firsts = Counter(x["first_word"] for x in items)
    return {
        "songs": len(items), "lines": N,
        "lines_per_song_median": statistics.median(x["n"] for x in items),
        "unique_lines_median": statistics.median(x["unique"] for x in items),
        "words_median": statistics.median(allw), "words_mean": round(statistics.mean(allw), 1),
        "syllables_median": statistics.median(alls), "syllables_mean": round(statistics.mean(alls), 1),
        "short_le3w_pct": round(sum(1 for v in allw if v <= 3) * 100 / N, 1),
        "long_gt10w_pct": round(sum(1 for v in allw if v > 10) * 100 / N, 1),
        "rhyme_pct": pct("rhyme"), "assonance_pct": pct("assonance"), "same_end_word_pct": pct("same_word"),
        "repeat_pct": pct("repeat"), "top_line_repeat_median": statistics.median(x["top_repeat"] for x in items),
        "title_in_lyrics_pct": round(sum(1 for x in items if x["title_hits"] > 0) * 100 / len(items), 1),
        "title_hits_median": statistics.median(x["title_hits"] for x in items),
        "contraction_pct": pct("contraction"), "filler_pct": pct("filler"),
        "you_pct": pct("you"), "i_pct": pct("i"), "we_pct": pct("we"),
        "question_pct": pct("question"), "imperative_pct": pct("imperative"),
        "emotion_pct": pct("emotion"), "abstract_pct": pct("abstract"), "big_word_pct": pct("big"),
        "ai_cliche_per_1000": round(sum(x["cliche"] for x in items) * 1000 / N, 1),
        "first_word_top": dict(firsts.most_common(8)),
        "line_end_top": dict(ends.most_common(25)),
        "line_start_top": dict(starts.most_common(15)),
        "content_top": dict(content.most_common(40)),
    }


# ---------------------------------------------------------------- 실행

def survey(years: range, top: int, workers: int) -> dict:
    songs = []
    for y in years:
        songs += year_list(y, top)
        time.sleep(0.3)
    print(f"곡 목록 {len(songs)}곡", flush=True)

    def one(s: dict) -> dict:
        lines = fetch_lyrics(s["title"], s["artist"])
        genre = fetch_genre(s["title"], s["artist"]) if lines else ""
        r = analyze_song(s["title"], lines) if lines else None
        return {**s, "genre": genre, "stats": r}

    done = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for i, r in enumerate(pool.map(one, songs), 1):
            done.append(r)
            if i % 100 == 0:
                print(f"  {i}/{len(songs)} (가사 {sum(1 for x in done if x['stats'])})", flush=True)

    ok = [x for x in done if x["stats"]]
    by_group, by_decade = defaultdict(list), defaultdict(list)
    for x in ok:
        by_group[GENRE_MAP.get(x["genre"], "기타")].append(x["stats"])
        by_decade[f"{x['year'] // 10 * 10}년대"].append(x["stats"])
    result = {
        "source": f"Billboard Year-End Hot 100 {years.start}-{years.stop - 1} 상위 {top}곡, 가사 LRCLIB, 장르 Deezer",
        "total": aggregate([x["stats"] for x in ok]),
        "groups": {g: {**aggregate(v), "members": MEMBERS.get(g, [])} for g, v in sorted(by_group.items(), key=lambda kv: -len(kv[1]))},
        "decades": {d: aggregate(v) for d, v in sorted(by_decade.items())},
        "listed": len(songs), "with_lyrics": len(ok),
        "genres_raw": dict(Counter(x["genre"] or "-" for x in ok).most_common()),
    }
    return result


def write_md(r: dict) -> None:
    cols = [("곡", "songs"), ("줄", "lines"), ("곡당 줄", "lines_per_song_median"), ("서로 다른 줄", "unique_lines_median"),
            ("낱말 중앙", "words_median"), ("음절 중앙", "syllables_median"), ("≤3낱말%", "short_le3w_pct"), (">10낱말%", "long_gt10w_pct"),
            ("각운%", "rhyme_pct"), ("모음운%", "assonance_pct"), ("같은 끝낱말%", "same_end_word_pct"), ("반복%", "repeat_pct"),
            ("최다 반복 줄", "top_line_repeat_median"), ("제목 든 곡%", "title_in_lyrics_pct"), ("제목 횟수", "title_hits_median"),
            ("축약%", "contraction_pct"), ("추임새%", "filler_pct"), ("you%", "you_pct"), ("I%", "i_pct"), ("we%", "we_pct"),
            ("물음%", "question_pct"), ("명령%", "imperative_pct"), ("감정어%", "emotion_pct"), ("추상명사%", "abstract_pct"),
            ("큰말%", "big_word_pct"), ("AI상투어/1000줄", "ai_cliche_per_1000")]

    def table(rows: dict) -> list[str]:
        out = ["| 묶음 | " + " | ".join(c for c, _ in cols) + " |", "|---|" + "---|" * len(cols)]
        for name, s in rows.items():
            if s:
                out.append(f"| {name} | " + " | ".join(str(s.get(k, "")) for _, k in cols) + " |")
        return out

    t = r["total"]
    lines = ["# 영어 히트곡 가사 실측", "", f"출처: {r['source']}. 목록 {r['listed']}곡 중 가사를 찾은 {r['with_lyrics']}곡. 통계만 저장(가사 원문 없음). 갱신: Actions '영어 가사 조사'.", "",
             "## 전체와 장르", ""] + table({"전체": t, **r["groups"]}) + ["", "## 연대", ""] + table(r["decades"]) + [
             "", "## 자주 쓰는 말(전체)", "",
             "- 첫 곡 첫 낱말: " + ", ".join(f"{k} {v}" for k, v in t["first_word_top"].items()),
             "- 줄 첫 낱말: " + ", ".join(f"{k} {v}" for k, v in t["line_start_top"].items()),
             "- 줄 끝 낱말: " + ", ".join(f"{k} {v}" for k, v in t["line_end_top"].items()),
             "- 내용어: " + ", ".join(f"{k} {v}" for k, v in t["content_top"].items()),
             "", "Deezer 장르 원본 분포: " + ", ".join(f"{k} {v}" for k, v in r["genres_raw"].items()),
             "", "묶음이 맡는 mufac 장르: " + "; ".join(f"{g}→{', '.join(s.get('members') or [])}" for g, s in r["groups"].items() if s.get("members")), ""]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def probe() -> None:
    y = year_list(2015, 5)
    print("위키백과 2015:", y[:3], flush=True)
    for s in y[:3]:
        lines = fetch_lyrics(s["title"], s["artist"])
        print(f"  {s['title']}: 가사 {len(lines)}줄, 장르 {fetch_genre(s['title'], s['artist'])!r}", flush=True)
    y = year_list(1995, 3)
    print("위키백과 1995:", y[:3], flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="1990-2025")
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--probe", action="store_true")
    a = ap.parse_args()
    if a.probe:
        probe()
    else:
        y0, y1 = (int(x) for x in a.years.split("-"))
        res = survey(range(y0, y1 + 1), a.top, a.workers)
        OUT_JSON.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        write_md(res)
        print(json.dumps(res["total"], ensure_ascii=False)[:1500], flush=True)
