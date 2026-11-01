"""장르별 유명곡 100곡의 줄 끝(어미)을 센다. GitHub Actions에서 돌린다(여기 컨테이너는 가사 사이트에 못 붙는다).

  python tools/endings_survey.py --probe          # 차트·가사 페이지 구조가 지금도 맞는지만 확인
  python tools/endings_survey.py [--limit 100] [--genres 발라드,힙합]

멜론 장르별 차트(없으면 벅스)에서 곡 100개를 뽑아 가사 페이지를 읽고, 줄마다 끝 어형을 분류해
assets/lyrics/_장르어미.json 과 _장르어미.md 에 통계만 남긴다. 가사 원문은 어디에도 저장하지 않는다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_JSON = ROOT / "assets" / "lyrics" / "_장르어미.json"
OUT_MD = ROOT / "assets" / "lyrics" / "_장르어미.md"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}

# 조사 묶음 → (멜론 장르 코드, 벅스 장르 경로, mufac 장르들)
GROUPS = {
    "발라드": ("GN0100", "ballad", ["발라드", "록발라드", "OST"]),
    "댄스·팝": ("GN0200", "dance", ["댄스", "팝", "일렉트로닉", "시티팝"]),
    "힙합": ("GN0300", "rap", ["힙합"]),
    "R&B": ("GN0400", "rnb", ["R&B"]),
    "인디": ("GN0500", "indie", ["인디밴드", "어쿠스틱"]),
    "록": ("GN0600", "rock", ["락", "밴드", "펑크", "메탈"]),
    "트로트": ("GN0700", "trot", ["트로트"]),
    "포크": ("GN0800", "folk", ["포크", "블루스"]),
    "OST": ("GN1500", "ost", ["OST"]),
}

SESSION = requests.Session()
SESSION.headers.update(UA)


def get(url: str, **kw) -> str:
    for i in range(3):
        try:
            r = SESSION.get(url, timeout=30, **kw)
            if r.status_code == 200:
                return r.text
            print(f"  {r.status_code} {url}", flush=True)
            if r.status_code in (403, 406, 429):
                time.sleep(3 * (i + 1))
        except requests.RequestException as e:
            print(f"  오류 {e} {url}", flush=True)
            time.sleep(2)
    return ""


# ---------------------------------------------------------------- 멜론

def melon_list(code: str, limit: int) -> list[str]:
    """장르별 차트(최근)와 스테디셀러 목록에서 곡 번호를 모은다."""
    ids: list[str] = []
    urls = [f"https://www.melon.com/chart/genre/index.htm?classCd={code}"]
    for start in range(1, 500, 50):
        urls.append(f"https://www.melon.com/genre/song_list.htm?gnrCode={code}&steadyYn=Y&startIndex={start}&pageSize=50")
    for u in urls:
        if len(ids) >= limit:
            break
        page = get(u)
        found = re.findall(r"data-song-no=\"(\d+)\"", page) or re.findall(r"goSongDetail\('(\d+)'\)", page)
        for f in found:
            if f not in ids:
                ids.append(f)
        time.sleep(0.6)
    return ids[:limit]


def melon_lyrics(song_id: str) -> tuple[str, list[str]]:
    page = get(f"https://www.melon.com/song/detail.htm?songId={song_id}")
    title = ""
    m = re.search(r"<div class=\"song_name\">(.*?)</div>", page, re.S)
    if m:
        title = re.sub(r"<[^>]+>", "", m.group(1)).replace("곡명", "").strip()
    m = re.search(r"<div class=\"lyric\"[^>]*>(.*?)</div>", page, re.S)
    if not m:
        return title, []
    body = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.S)
    body = re.sub(r"<br\s*/?>", "\n", body)  # 곡에 따라 <br> 대신 줄바꿈 글자만 있는 페이지가 있다
    lines = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in body.splitlines()]
    return title, [x for x in lines if x]


# ---------------------------------------------------------------- 벅스

def bugs_list(path: str, limit: int) -> list[str]:
    ids: list[str] = []
    for u in (f"https://music.bugs.co.kr/genre/chart/kpop/{path}/total/week",
              f"https://music.bugs.co.kr/genre/chart/{path}/total/week",
              f"https://music.bugs.co.kr/genre/kpop/{path}"):
        page = get(u)
        for f in re.findall(r"trackid=\"(\d+)\"", page) + re.findall(r"/track/(\d+)", page):
            if f not in ids:
                ids.append(f)
        if len(ids) >= limit:
            break
        time.sleep(0.6)
    return ids[:limit]


def bugs_lyrics(track_id: str) -> tuple[str, list[str]]:
    page = get(f"https://music.bugs.co.kr/track/{track_id}")
    title = ""
    m = re.search(r"<title>(.*?)</title>", page, re.S)
    if m:
        title = html.unescape(m.group(1)).split(" / ")[0].split("|")[0].strip()
    m = re.search(r"<xmp>(.*?)</xmp>", page, re.S)
    if not m:
        return title, []
    return title, [x.strip() for x in html.unescape(m.group(1)).splitlines() if x.strip()]


# ---------------------------------------------------------------- 분류

HANGUL = re.compile(r"[가-힣]")
EMOTION = re.compile(r"(슬프|슬퍼|외로|그리워|보고 싶|보고싶|사랑해|사랑하|좋아해|좋아|싫어|미워|아파|아프|행복|기뻐|무서|두려|설레|눈물|울어|울었|웃어)")
YOU = re.compile(r"(^|[\s,])(너|네|니|그대|당신|넌|널|네가|니가|너의|너를|너에게|너만|너도|그댈|그대여)")
CONCESSION = re.compile(r"(아도|어도|라도|ㄴ데도|는데도|여도|해도)$")
BRACKET = re.compile(r"^\(.*\)$|^\[.*\]$")


def ending(line: str) -> str:
    """줄 끝 어형 한 가지. 한국어 줄만(영어·숫자로 끝나면 '영어·기타')."""
    s = re.sub(r"[\s\.\,\!\?~…\-\"'’”)\]]+$", "", line)
    if not s:
        return "기타"
    last = s[-1]
    if not HANGUL.match(last):
        return "영어·기타"
    w = s.split()[-1] if s.split() else s
    if re.search(r"(요|죠|세요|네요|어요|아요|예요|에요|거죠|을까요|ㄹ까요)$", w):
        return "해요체"
    if re.search(r"(습니다|입니다|니다|소서|오)$", w):
        return "합쇼체"
    if re.search(r"(까|니|냐|나요|가요|을까|ㄹ까|는가|던가|련|오려나|려나)$", w) and not w.endswith("까지"):
        return "물음"
    if re.search(r"(었다|았다|였다|한다|된다|이다|다|더라|더군|구나|군)$", w) and not re.search(r"(보다|보다는|바다|사다리|다리|나다|어디다)$", w):
        return "-다/-더라"
    if re.search(r"(네|지|지만)$", w) and len(w) > 1 and not re.search(r"(까지|조차|마저|편지|가지|이미지|돼지|바지|거지|동네|언니|누나|아네|어제|이제)$", w):
        return "-네/-지"
    if re.search(r"(고|는데|ㄴ데|다가|면|면서|며|서|려고|라서|니까|듯이|처럼|같이|만큼|도록|기에)$", w) and len(w) > 1 and not re.search(r"(책상|참고|최고|사고|친구|의미)$", w):
        return "연결어미"
    if ((w.endswith("자") and len(w) > 1 and not re.search(r"(혼자|남자|여자|의자|모자|과자|상자|숫자|글자|제자|부자|환자|감자|사자|어제자)$", w))
            or w in ("마", "줘", "렴") or re.search(r"(해라|가라|어라|아라|봐라|와라|줄래|할래|해줘|해봐|려무나)$", w)):
        return "명령·청유"
    if re.search(r"(게|ㄹ게|을게|거야|거다|겠지|겠어|겠네|테야|텐데|려나|려 해|거예요)$", w):
        return "의지·추측"
    if re.search(r"(아|어|야|여|해|워|져|봐|와|라|데|래|잖아|잖니|는걸|인걸|인데|거든|걸|던|대|랴|려|지마|해도)$", w):
        return "해체"
    # 조사·명사·관형형으로 끝나는 줄
    return "명사·조사"


def syllables(line: str) -> int:
    return len(HANGUL.findall(line))


def analyze(songs: list[tuple[str, list[str]]]) -> dict:
    endings: Counter = Counter()
    lines_all: list[str] = []
    polite_songs = 0
    repeat_total = 0
    first_lines: Counter = Counter()
    for _, lines in songs:
        ko = [l for l in lines if HANGUL.search(l) and not BRACKET.match(l)]
        if len(ko) < 8:
            continue
        ends = [ending(l) for l in ko]
        endings.update(ends)
        lines_all += ko
        if ends.count("해요체") >= len(ko) * 0.3:
            polite_songs += 1
        c = Counter(ko)
        repeat_total += sum(n for n in c.values() if n > 1)
        first_lines[ends[0]] += 1
    n = len(lines_all) or 1
    syl = [syllables(l) for l in lines_all]
    return {
        "songs": sum(1 for _, l in songs if len([x for x in l if HANGUL.search(x)]) >= 8),
        "lines": len(lines_all),
        "endings_pct": {k: round(v * 100 / n, 1) for k, v in endings.most_common()},
        "syllables_median": statistics.median(syl) if syl else 0,
        "syllables_mean": round(statistics.mean(syl), 1) if syl else 0,
        "short_le4_pct": round(sum(1 for s in syl if s <= 4) * 100 / n, 1),
        "long_gt10_pct": round(sum(1 for s in syl if s > 10) * 100 / n, 1),
        "repeat_pct": round(repeat_total * 100 / n, 1),
        "you_pct": round(sum(1 for l in lines_all if YOU.search(l)) * 100 / n, 1),
        "emotion_pct": round(sum(1 for l in lines_all if EMOTION.search(l)) * 100 / n, 1),
        "concession_pct": round(sum(1 for l in lines_all if CONCESSION.search(re.sub(r"[\s\.\,\!\?~…]+$", "", l))) * 100 / n, 1),
        "polite_songs": polite_songs,
        "first_line_endings": dict(first_lines.most_common(4)),
    }


# ---------------------------------------------------------------- 실행

def probe() -> None:
    print("멜론 장르 차트 / 스테디 목록 / 가사 페이지 구조 확인", flush=True)
    for code in ("GN0100", "GN0600"):
        for u in (f"https://www.melon.com/chart/genre/index.htm?classCd={code}",
                  f"https://www.melon.com/genre/song_list.htm?gnrCode={code}&steadyYn=Y&startIndex=1&pageSize=50"):
            page = get(u)
            ids = re.findall(r"data-song-no=\"(\d+)\"", page) or re.findall(r"goSongDetail\('(\d+)'\)", page)
            print(f"{u}\n  글자 {len(page)}, 곡 번호 {len(ids)}개, 첫 번호 {ids[:3]}", flush=True)
            if ids:
                title, lines = melon_lyrics(ids[0])
                print(f"  가사 시험: {title!r} 줄 {len(lines)}, 첫 줄 끝 {ending(lines[0]) if lines else '-'}", flush=True)
    for path in ("ballad", "rock"):
        ids = bugs_list(path, 10)
        print(f"벅스 {path}: 곡 번호 {len(ids)}개", flush=True)
        if ids:
            title, lines = bugs_lyrics(ids[0])
            print(f"  가사 시험: {title!r} 줄 {len(lines)}", flush=True)


def survey(limit: int, genres: list[str]) -> None:
    result = json.loads(OUT_JSON.read_text(encoding="utf-8")) if OUT_JSON.exists() else {}
    for group, (code, bpath, members) in GROUPS.items():
        if genres and group not in genres:
            continue
        print(f"== {group}", flush=True)
        ids = melon_list(code, limit)
        src = "melon"
        if len(ids) < 20:
            ids, src = bugs_list(bpath, limit), "bugs"
        songs: list[tuple[str, list[str]]] = []
        titles = []
        for i, sid in enumerate(ids):
            title, lines = melon_lyrics(sid) if src == "melon" else bugs_lyrics(sid)
            if lines:
                songs.append((title, lines))
                titles.append(title)
            if (i + 1) % 20 == 0:
                print(f"  {i + 1}/{len(ids)}", flush=True)
            time.sleep(0.5)
        stats = analyze(songs)
        stats.update(source=src, members=members, titles=titles[:100])
        result[group] = stats
        print(f"  곡 {stats['songs']}, 줄 {stats['lines']}, 끝 분포 {stats['endings_pct']}", flush=True)
        OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    write_md(result)


def write_md(result: dict) -> None:
    keys = ["명사·조사", "해체", "연결어미", "-네/-지", "해요체", "-다/-더라", "물음", "의지·추측", "명령·청유", "합쇼체", "영어·기타"]
    rows = ["# 장르별 유명곡 줄 끝 실측", "",
            "멜론 장르별 차트·스테디셀러 상위 곡의 가사를 읽어 한국어 줄의 끝 어형을 센 것(통계만, 가사는 저장하지 않음). "
            "write.py가 요청 장르에 맞는 분포를 프롬프트에 붙인다. 갱신: Actions '줄 끝 조사'.", "",
            "| 묶음 | 곡 | 줄 | " + " | ".join(keys) + " | 음절 중앙 | ≤4음절 | >10음절 | 반복 | 2인칭 | 감정어 | 양보형 | 해요체 곡 |",
            "|" + "---|" * (len(keys) + 11)]
    for g, s in result.items():
        e = s["endings_pct"]
        rows.append(f"| {g} | {s['songs']} | {s['lines']} | " + " | ".join(f"{e.get(k, 0)}" for k in keys)
                    + f" | {s['syllables_median']} | {s['short_le4_pct']} | {s['long_gt10_pct']} | {s['repeat_pct']} | {s['you_pct']} | {s['emotion_pct']} | {s['concession_pct']} | {s['polite_songs']}/{s['songs']} |")
    rows += ["", "숫자는 줄의 백분율. 묶음이 맡는 mufac 장르: " + "; ".join(f"{g}→{', '.join(s['members'])}" for g, s in result.items()), ""]
    OUT_MD.write_text("\n".join(rows), encoding="utf-8")


def genre_text(genre: str) -> str:
    """write.py가 프롬프트에 붙일 장르 분포 문장. 장르가 없거나 자동이면 발라드·댄스·록·인디·힙합 요약."""
    if not OUT_JSON.exists():
        return ""
    result = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    groups = [g for g, s in result.items() if genre in s.get("members", [])]
    if not groups:
        groups = [g for g in ("발라드", "댄스·팝", "록", "인디", "힙합") if g in result]
    out = []
    for g in groups:
        s = result[g]
        e = s["endings_pct"]
        top = ", ".join(f"{k} {v}%" for k, v in list(e.items())[:6])
        out.append(f"- {g}(유명곡 {s['songs']}곡 {s['lines']}줄): {top}. 줄 음절 중앙값 {s['syllables_median']}, 4음절 이하 {s['short_le4_pct']}%, "
                   f"10음절 초과 {s['long_gt10_pct']}%, 같은 줄 반복 {s['repeat_pct']}%, 너·그대 든 줄 {s['you_pct']}%, 감정어 줄 {s['emotion_pct']}%, "
                   f"양보형 {s['concession_pct']}%, 전곡 해요체 {s['polite_songs']}/{s['songs']}곡.")
    return "\n".join(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--genres", default="")
    a = ap.parse_args()
    if a.probe:
        probe()
    else:
        survey(a.limit, [g for g in a.genres.split(",") if g])
