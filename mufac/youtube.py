"""유튜브 업로드. 키 세 개(YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN)가 있어야 동작한다."""

from __future__ import annotations

import os
from pathlib import Path

from .song import Song

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


def hashtags(meta: dict, artist: str) -> list[str]:
    """설명란 해시태그. 유튜브는 15개를 넘으면 전부 무시하므로 15개까지만."""
    raw = list((meta.get("youtube_meta") or {}).get("hashtags") or [])
    raw += [meta.get("title", ""), artist, "노래추천", "신곡"]
    out = []
    for t in raw:
        t = "".join(ch for ch in (t or "") if ch.isalnum() or ch == "_")
        if t and t not in out:
            out.append(t)
    return out[:15]


def description(song: Song, artist: str, *, main_id: str | None = None, short: bool = False) -> str:
    m = song.meta
    ym = m.get("youtube_meta") or {}
    parts = [ym.get("intro") or m.get("hook", "")]
    if main_id:
        parts.append(f"전체 노래 ▶ https://youtu.be/{main_id}")
    if not short:
        parts.append(f"{m.get('title', '')}\n\n{song.plain_lyrics()}")
    if ym.get("comment_prompt"):
        parts.append(ym["comment_prompt"])
    credit = []
    if artist:
        credit.append(f"작사·기획 {artist}")
    credit.append("음악 생성 Suno")
    photo = m.get("photo") or {}
    if photo.get("source") == "pexels":
        credit.append(f"사진 {photo.get('photographer')} (Pexels)")
    elif photo.get("source") == "openai":
        credit.append("이미지 AI 생성")
    credit.append("이 곡은 AI 음악 생성 도구로 만들었습니다.")
    parts.append("\n".join(credit))
    parts.append(" ".join("#" + t for t in hashtags(m, artist)))
    return "\n\n".join(p for p in parts if p).strip()[:4900]


def preview(song: Song, cfg: dict) -> dict:
    """업로드 전에 보여 줄 유튜브 메타데이터. 업로드도 같은 값을 쓴다."""
    artist = cfg.get("artist", "")
    m, ym = song.meta, song.meta.get("youtube_meta") or {}
    return {
        "title": main_title(cfg["youtube_title"], m["title"], artist, ym.get("situation", "")),
        "shorts_title": f"{(ym.get('shorts_title') or m['title']).strip()} #shorts"[:100],
        "description": description(song, artist),
        "tags": fit_tags([m["title"], artist, *(m.get("tags") or [])]),
        "hashtags": hashtags(m, artist),
        "playlists": playlist_names(cfg, m),
        "privacy": cfg.get("privacy", "private"),
    }


def playlist_names(cfg: dict, meta: dict) -> list[str]:
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
           thumb: Path | None = None) -> str:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    yt = _client()
    body = {
        "snippet": {
            "title": title[:100],
            "description": desc,
            "tags": tags[:30],
            "categoryId": "10",  # Music
            "defaultLanguage": "ko",
            "defaultAudioLanguage": "ko",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": True,  # 유튜브의 AI 생성 콘텐츠 표시
        },
    }
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
