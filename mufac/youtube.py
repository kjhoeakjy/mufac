"""유튜브 업로드. 키 세 개(YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)가 있어야 동작한다."""

from __future__ import annotations

import os
import datetime as _dt
from pathlib import Path

from .song import Song, artist_name

SCOPES = ["https://www.googleapis.com/auth/youtube"]


def ready() -> bool:
    return all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))


def _client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def whoami() -> str:
    r = _client().channels().list(part="snippet", mine=True).execute()
    items = r.get("items") or []
    return items[0]["snippet"]["title"] if items else ""


def main_title(fmt: str, title: str, artist: str, situation: str) -> str:
    """config의 youtube_title 형식으로 제목을 만든다. 빈 칸은 구분자째 지운다."""
    out = fmt.format(title=title, artist=artist, situation=situation)
    for sep in (" |  ", " | |", " -  |", "  "):
        out = out.replace(sep, " ")
    return out.strip(" -|")[:100]


def fit_tags(tags: list[str], limit: int = 480) -> list[str]:
    """중복을 지우고 유튜브 태그 500자 제한 안에 맞춘다(띄어쓰기 있는 태그는 따옴표 2자 추가)."""
    seen, out, total = set(), [], 0
    for t in tags:
        t = (t or "").strip().lstrip("#")
        if not t or t.lower() in seen or any(c in t for c in "<>,"):
            continue
        cost = len(t) + (2 if " " in t else 0) + (1 if out else 0)
        if total + cost > limit:
            break
        seen.add(t.lower())
        out.append(t)
        total += cost
    return out


# 늘 들어가는 해시태그. 노래·음악·인공지능은 사용자 지정(2026-11-01)으로 앞쪽 고정
FIXED_HASHTAGS = ["노래", "음악", "인공지능"]
GENERIC_HASHTAGS = ["AI음악", "감성", "신곡", "노래추천", "플레이리스트", "가사", "AI노래", "kpop", "music", "koreanmusic"]
GENERIC_TAGS = ["음악", "노래", "인공지능", "AI음악", "AI노래", "AI 작곡", "suno", "ai music", "감성", "신곡", "노래 추천",
                "플레이리스트", "가사", "kpop", "korean music", "k-pop", "korean song"]
SHORT_KINDS = ("도입", "후렴", "브릿지", "엔딩")

# 영어 곡은 제목·설명·해시태그·태그를 모두 영어로(사용자 지정, 2026-11-01)
FIXED_HASHTAGS_EN = ["song", "music", "AI"]
GENERIC_HASHTAGS_EN = ["AImusic", "newmusic", "englishsong", "popsong", "lyrics", "AIsong", "musicvideo", "playlist", "sadsongs", "lovesong"]
GENERIC_TAGS_EN = ["song", "music", "AI", "AI music", "AI song", "suno", "new music", "english song", "pop song", "lyrics",
                   "lyric video", "love song", "playlist", "chill music", "songs with lyrics"]
GENRE_EN = {"발라드": "ballad", "록발라드": "rockballad", "팝": "pop", "R&B": "rnb", "어쿠스틱": "acoustic", "포크": "folk",
            "밴드": "band", "인디밴드": "indie", "락": "rock", "펑크": "punk", "메탈": "metal", "힙합": "hiphop", "댄스": "dance",
            "일렉트로닉": "electronic", "시티팝": "citypop", "재즈": "jazz", "블루스": "blues", "레게": "reggae", "OST": "soundtrack",
            "트로트": "trot", "국악": "koreantraditional", "캐럴": "christmas", "동요": "kidssongs", "자장가": "lullaby",
            "무가사": "instrumental", "뉴에이지": "newage", "로파이": "lofi"}


def is_en(meta: dict) -> bool:
    return (meta.get("lang") or (meta.get("request") or {}).get("lang", "")) == "en"


def _genre_word(meta: dict) -> str:
    g = ((meta.get("request") or {}).get("genre") or "").strip()
    if g in ("", "자동"):
        return ""
    return GENRE_EN.get(g, "") if is_en(meta) else g


def hashtags(meta: dict, artist: str) -> list[str]:
    """설명란 해시태그 15개. 유튜브는 15개를 넘으면 전부 무시하므로 딱 15개까지.
    곡별 태그 → 장르 → 제목·채널 → 넓은 기본 태그(음악, 노래, 감성) 순으로 채운다. 앞의 3개가 제목 위에 보인다."""
    own = list((meta.get("youtube_meta") or {}).get("hashtags") or [])
    # 앞 3개는 곡이 고른 넓은 말(제목 위에 보인다), 그다음 장르와 고정 태그(노래·음악·인공지능), 나머지 곡 태그, 제목·채널, 기본 태그
    fixed, generic = (FIXED_HASHTAGS_EN, GENERIC_HASHTAGS_EN) if is_en(meta) else (FIXED_HASHTAGS, GENERIC_HASHTAGS)
    raw = own[:3] + [_genre_word(meta)] + fixed + own[3:] + [meta.get("title", ""), artist] + generic
    out = []
    for t in raw:
        t = "".join(ch for ch in (t or "") if ch.isalnum() or ch == "_")
        if t and t not in out:
            out.append(t)
    return out[:15]


def description(song: Song, artist: str, *, main_id: str | None = None, short: bool = False) -> str:
    """설명란. 가사, 만든 사람, 저작권, 해시태그만 적는다."""
    m = song.meta
    if is_en(m):
        return _description_en(song, artist, main_id=main_id, short=short)
    parts = []
    if main_id:
        parts.append(f"전체 노래 https://youtu.be/{main_id}")
    if short:
        # 쇼츠 설명 첫 줄은 가사 한 줄(검색어가 되고, 설명을 열었을 때 바로 보인다)
        line = (m.get("share_line") or m.get("hook") or "").strip()
        if line:
            parts.append(line)
    elif song.plain_lyrics():
        parts.append(song.plain_lyrics())
    credit = []
    if artist:
        credit.append(f"{'음악' if m.get('instrumental') else '노래·가사'} {artist}")
    photo = m.get("photo") or {}
    if photo.get("source") == "pexels":
        credit.append(f"음악 생성 Suno, 사진 {photo.get('photographer')} (Pexels)")
    else:
        credit.append("음악·이미지 AI 생성 (Suno)")
    year = str(m.get("created", ""))[:4] or _dt.date.today().strftime("%Y")
    credit.append(f"© {year} {artist or '채널 운영자'}. 무단 복제·재업로드 금지.")
    parts.append("\n".join(credit))
    tags = hashtags(m, artist)
    if short and "shorts" not in tags:
        tags = ["shorts", *tags][:15]
    parts.append(" ".join("#" + t for t in tags))
    return "\n\n".join(p for p in parts if p).strip()[:4900]


def _description_en(song: Song, artist: str, *, main_id: str | None = None, short: bool = False) -> str:
    """영어 곡 설명란. 전부 영어: 가사, 만든 사람(Yon Ju Kim과 채널 이름), 저작권, 해시태그."""
    from .song import config
    m = song.meta
    parts = []
    if main_id:
        parts.append(f"Full song: https://youtu.be/{main_id}")
    if short:
        line = (m.get("share_line") or m.get("hook") or "").strip()
        if line:
            parts.append(line)
    elif song.plain_lyrics():
        parts.append(song.plain_lyrics())
    channel = config().get("artist", "")
    who = f"{artist} ({channel})" if channel and channel != artist else artist
    credit = [f"{'Music' if m.get('instrumental') else 'Words & music'} by {who}" if who else ""]
    photo = m.get("photo") or {}
    if photo.get("source") == "pexels":
        credit.append(f"Music generated with Suno. Photo by {photo.get('photographer')} (Pexels)")
    else:
        credit.append("Music and artwork generated with AI (Suno)")
    year = str(m.get("created", ""))[:4] or _dt.date.today().strftime("%Y")
    credit.append(f"© {year} {artist or 'the channel owner'}. All rights reserved. Please do not re-upload.")
    parts.append("\n".join(c for c in credit if c))
    tags = hashtags(m, artist)
    if short and "shorts" not in tags:
        tags = ["shorts", *tags][:15]
    parts.append(" ".join("#" + t for t in tags))
    return "\n\n".join(p for p in parts if p).strip()[:4900]


def shorts_titles(song: Song) -> list[str]:
    """쇼츠 넷의 제목. 도입은 1절 첫 줄, 후렴은 후렴 문장(사용자 지정), 브릿지는 브릿지 첫 줄, 엔딩은 공유 한 줄(없으면 끝부분의 다른 줄).
    넷이 다른 말이어야 검색과 추천에서 서로 다른 입구가 된다."""
    m = song.meta
    hook = (m.get("hook") or (m.get("youtube_meta") or {}).get("shorts_title") or m["title"]).strip()
    lines = song.lyric_lines()
    texts = [t for _, t in lines]
    first = next((t for sec, t in lines if "verse" in sec.lower()), texts[0] if texts else hook)
    bridge = next((t for sec, t in lines if "bridge" in sec.lower()), "")
    share = (m.get("share_line") or "").strip()
    tail = [t for t in reversed(texts) if t != hook and not t.startswith("(")]  # 끝에서부터, 훅이 아닌 줄
    wants = [[first, hook], [hook], [bridge, share, *tail], [share, *tail, hook]]
    out = []
    for cands in wants:
        pick = next((c for c in cands if c and c.strip() and c.strip() not in out), None) or hook
        out.append(pick.strip())
    return [f"{p} #shorts"[:100] for p in out]


def preview(song: Song, cfg: dict) -> dict:
    """업로드 전에 보여 줄 유튜브 메타데이터. 업로드도 같은 값을 쓴다."""
    artist = artist_name(cfg, song.meta)
    m, ym = song.meta, song.meta.get("youtube_meta") or {}
    titles = shorts_titles(song)
    generic = GENERIC_TAGS_EN if is_en(m) else GENERIC_TAGS
    return {
        "title": main_title(cfg["youtube_title"], m["title"], artist, ym.get("situation", "")),
        "shorts_title": titles[1],  # 예전 호환: 후렴 쇼츠 제목
        "shorts_titles": titles,
        "description": description(song, artist),
        "tags": fit_tags([m["title"], artist, *generic[:3], _genre_word(m), *(m.get("tags") or []), *generic[3:]]),
        "hashtags": hashtags(m, artist),
        "playlists": playlist_names(cfg, m),
        "privacy": cfg.get("privacy", "private"),
    }


def publish_at(cfg: dict, index: int) -> str:
    """쇼츠 예약 공개 시각(RFC 3339). 첫 편은 다음 publish_hour(KST), 그다음은 shorts_gap_days 간격."""
    kst = _dt.timezone(_dt.timedelta(hours=9))
    hour = int(cfg.get("publish_hour", 18))
    gap = max(0, int(cfg.get("shorts_gap_days", 1)))
    now = _dt.datetime.now(kst)
    first = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if first <= now + _dt.timedelta(minutes=30):
        first += _dt.timedelta(days=1)
    return (first + _dt.timedelta(days=gap * index)).isoformat()


def playlist_names(cfg: dict, meta: dict) -> list[str]:
    if is_en(meta):
        return list(cfg.get("playlists_en") or [])
    names = list(cfg.get("playlists") or [])
    theme = meta.get("theme")
    themed = (cfg.get("theme_playlists") or {}).get(theme)
    if themed:
        names.append(themed)
    return names


def add_to_playlist(video_id: str, name: str, privacy: str) -> None:
    yt = _client()
    pid = None
    req = yt.playlists().list(part="snippet", mine=True, maxResults=50)
    while req is not None and pid is None:
        resp = req.execute()
        for p in resp.get("items", []):
            if p["snippet"]["title"] == name:
                pid = p["id"]
                break
        req = yt.playlists().list_next(req, resp)
    if pid is None:
        pid = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": name, "defaultLanguage": "ko"},
            "status": {"privacyStatus": "public" if privacy == "public" else privacy},
        }).execute()["id"]
    yt.playlistItems().insert(part="snippet", body={
        "snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": video_id}},
    }).execute()


def upload(path: Path, *, title: str, desc: str, tags: list[str], privacy: str,
           thumb: Path | None = None, publish_at: str | None = None, lang: str = "ko") -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = _client()
    body = {
        "snippet": {
            "title": title[:100],
            "description": desc,
            "tags": tags[:30],
            "categoryId": "10",  # Music
            "defaultLanguage": lang,
            "defaultAudioLanguage": lang,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # 유튜브의 AI 생성 콘텐츠 표시
        },
    }
    if publish_at:  # 예약 공개: 올릴 때는 비공개, 그 시각에 유튜브가 공개로 바꾼다
        body["status"].update(privacyStatus="private", publishAt=publish_at)
    req = yt.videos().insert(
        part="snippet,status", body=body,
        media_body=MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True),
    )
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  업로드 {int(status.progress() * 100)}%", flush=True)
    vid = resp["id"]
    if thumb and thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
        except HttpError as e:
            print(f"  썸네일 지정 실패(채널 전화번호 인증이 필요할 수 있음): {e.status_code}", flush=True)
    return vid
