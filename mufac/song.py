"""곡 폴더(songs/<slug>/)와 설정 파일 읽기·쓰기."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SONGS = ROOT / "songs"
FONTS = ROOT / "assets" / "fonts"
AUDIO_EXT = (".mp3", ".wav", ".m4a", ".flac")
SECTION_RE = re.compile(r"^\s*\[(.+?)\]\s*$")


def config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8")) or {}
    cfg.setdefault("artist", "")
    cfg.setdefault("youtube_title", "{title} - {artist}")
    cfg.setdefault("privacy", "private")
    cfg.setdefault("photo_source", "pexels")
    cfg.setdefault("whisper_model", "medium")
    cfg.setdefault("short_seconds", 40)
    return cfg


class _Literal(str):
    pass


def _literal_repr(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_Literal, _literal_repr, Dumper=yaml.SafeDumper)


class Song:
    def __init__(self, slug: str):
        self.slug = slug
        self.dir = SONGS / slug
        self.out = self.dir / "out"
        self.meta_path = self.dir / "song.yaml"
        self.meta: dict = {}
        if self.meta_path.exists():
            self.meta = yaml.safe_load(self.meta_path.read_text(encoding="utf-8")) or {}

    # ---- 파일 위치
    @property
    def photo_path(self) -> Path:
        return self.dir / "photo.jpg"

    @property
    def photo_v_path(self) -> Path:
        return self.dir / "photo_v.jpg"

    @property
    def timing_path(self) -> Path:
        return self.dir / "timing.lrc"

    def audio_path(self) -> Path | None:
        files = sorted(p for p in self.dir.iterdir() if p.suffix.lower() in AUDIO_EXT)
        return files[0] if files else None

    # ---- 저장
    def save(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        data = dict(self.meta)
        if "lyrics" in data:
            data["lyrics"] = _Literal(data["lyrics"].strip() + "\n")
        self.meta_path.write_text(
            yaml.dump(data, Dumper=yaml.SafeDumper, allow_unicode=True, sort_keys=False, width=1000),
            encoding="utf-8",
        )

    # ---- 가사
    def lyric_lines(self) -> list[tuple[str, str]]:
        """(구간 이름, 가사 한 줄) 목록. 구간 태그와 빈 줄은 뺀다."""
        section = ""
        lines = []
        for raw in self.meta.get("lyrics", "").splitlines():
            m = SECTION_RE.match(raw)
            if m:
                section = m.group(1).strip()
                continue
            text = raw.strip()
            if text and not text.startswith("("):
                lines.append((section, text))
        return lines

    def plain_lyrics(self) -> str:
        """설명란용 가사: 구간 태그를 빼고 구간 사이에 빈 줄."""
        blocks, cur = [], []
        for raw in self.meta.get("lyrics", "").splitlines():
            if SECTION_RE.match(raw) or not raw.strip():
                if cur:
                    blocks.append("\n".join(cur))
                    cur = []
                continue
            cur.append(raw.strip())
        if cur:
            blocks.append("\n".join(cur))
        return "\n\n".join(blocks)


def new_slug() -> str:
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%y%m%d")
    n = 1
    while (SONGS / f"{today}-{n}").exists():
        n += 1
    return f"{today}-{n}"


def all_songs() -> list[Song]:
    if not SONGS.exists():
        return []
    return [Song(p.name) for p in sorted(SONGS.iterdir()) if (p / "song.yaml").exists()]
