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


def description(song: Song, artist: str, *, main_id: str | None = None) -> str:
    m = song.meta
    parts = [m.get("hook", "")]
    if main_id:
        parts.append(f"전체 듣기 https://youtu.be/{main_id}")
    parts.append(song.plain_lyrics())
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
    tags = m.get("tags") or []
    if tags:
        parts.append(" ".join("#" + t.replace(" ", "") for t in tags[:5]))
    return "\n\n".join(p for p in parts if p).strip()[:4900]


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
