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
    def cover_path(self) -> Path:
        return self.dir / "cover.jpg"

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


# ---- 이전 곡들에서 버릇을 읽는다 (새 곡 요청에 붙여 되풀이를 막는다)
_STOP = set("""그 이 저 내 네 나 너 우리 것 거 건 게 수 때 말 더 다 안 못 잘 좀 또 왜 뭐 누가 누구 어디 언제 어떻게 하고 있는 없는 같은 그런 이런 저런
오늘 내일 어제 지금 이제 다시 보고 두고 놓고 가고 나와 나도 너도 너는 네가 내가 아는 싶어 자리 사이 전에 오늘은 그래도 하루 처음 마지막
밤 길 손 창 비 집 꿈 날 눈 몸 맘 마음 사람 사랑 시간 하늘 바람 봄 여름 가을 겨울 아침 저녁 새벽""".split())
_ALWAYS = ["하나(세는 말)", "사실은", "-는 척", "아무도"]


def _words(song: Song) -> set[str]:
    return {w for _, line in song.lyric_lines() for w in re.findall(r"[가-힣]{2,}", line)}


def habit_words(done: list[Song], min_songs: int = 3, recent: int = 20) -> list[str]:
    """최근 곡 셋 이상에 나온 낱말(조사 붙은 어절 그대로). 흔한 기능어·기본 명사는 뺀다."""
    from collections import Counter
    c: Counter = Counter()
    for s in done[-recent:]:
        c.update(_words(s))
    found = [w for w, n in c.most_common() if n >= min_songs and w not in _STOP and not w.endswith(("요", "죠"))]
    return _ALWAYS + found[:40]


def speech_styles(done: list[Song]) -> list[str]:
    """arc 첫 줄에 적힌 화법(혼잣말·너에게·관찰·우리)을 곡 순서대로."""
    out = []
    for s in done:
        head = (s.meta.get("arc") or "")[:60]
        for k in ("너에게", "혼잣말", "관찰", "우리"):
            if k in head:
                out.append(k)
                break
    return out


def polite_turn(done: list[Song], genre: str = "", window: int = 5) -> bool:
    """지난 다섯 곡에 해요체 곡이 없고 장르가 맞으면 이번 곡은 해요체 차례."""
    if genre not in ("", "자동", "발라드", "포크", "어쿠스틱", "OST", "록발라드"):
        return False
    for s in done[-window:]:
        lines = [t for _, t in s.lyric_lines()]
        if lines and sum(t.endswith(("요", "죠")) for t in lines) >= len(lines) * 0.3:
            return False
    return len(done) >= window

