"""공개 악보 저장소에서 카탈로그 곡의 MIDI를 모은다. GitHub Actions에서 돌린다.

출처
- Mutopia Project (mutopiaproject.org): 저작권이 끝난 악보를 자원봉사자가 LilyPond로 옮긴 것. 곡마다 MIDI가 함께 있다.
  카탈로그의 mutopia: 값은 저장소 안 곡 폴더(ftp/작곡가/작품/곡)이고, 그 폴더의 <곡>.mid 를 받는다.
  (검색으로 찾으면 다른 곡이 잡히는 일이 많아서 폴더를 직접 적는다. 폴더 목록은 github.com/MutopiaProject/MutopiaProject 의 ftp/ 참고.)

실행: python tools/collect_midi.py [id ...]   (인자가 없으면 아직 없는 곡 전부, 인자가 있으면 그 곡은 다시 받는다)
결과: assets/classical/midi/<id>.mid, 표준출력과 step summary에 보고.
"""

from __future__ import annotations

import html
import os
import re
import sys
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from mufac import classical  # noqa: E402

MIDI_DIR = classical.MIDI_DIR
UA = {"User-Agent": "mufac-collector/1.0 (public-domain score collector)"}
SITE = "https://www.mutopiaproject.org/"


def valid_midi(data: bytes) -> bool:
    return data[:4] == b"MThd" and len(data) > 200


def get(url: str) -> bytes | None:
    try:
        r = requests.get(url, headers=UA, timeout=120)
    except Exception:
        return None
    return r.content if r.status_code == 200 else None


def candidates(folder: str) -> list[str]:
    """곡 폴더에서 받을 .mid 주소. 폴더 이름과 같은 파일을 먼저, 없으면 폴더 목록에서 찾는다."""
    folder = folder.strip("/")
    base = folder.rsplit("/", 1)[-1]
    out = [f"{SITE}{folder}/{base}.mid"]
    page = get(f"{SITE}{folder}/")
    if page:
        text = html.unescape(page.decode("utf-8", "ignore"))
        for link in re.findall(r'href="([^"]+\.mid)"', text, flags=re.I):
            full = urllib.parse.urljoin(f"{SITE}{folder}/", link)
            if full not in out:
                out.append(full)
    return out


def fetch(piece: dict) -> tuple[bool, str]:
    folder = piece.get("mutopia")
    if not folder:
        return False, "악보 출처 없음"
    for url in candidates(folder)[:6]:
        data = get(url)
        if data and valid_midi(data):
            (MIDI_DIR / f"{piece['id']}.mid").write_bytes(data)
            return True, url
    return False, f"MIDI 없음 ({SITE}{folder}/)"


def main() -> None:
    MIDI_DIR.mkdir(parents=True, exist_ok=True)
    wanted = set(sys.argv[1:])
    pieces = classical.catalog(available_only=False)
    rows = []
    for p in pieces:
        if wanted and p["id"] not in wanted:
            continue
        if p["midi"] and not wanted:
            continue
        if not p.get("mutopia"):
            continue
        ok, info = fetch(p)
        rows.append((p["id"], p["name"], ok, info))
        print(("OK   " if ok else "MISS ") + f"{p['id']:22} {p['name']:20} {info}", flush=True)
    have = len([p for p in pieces if (MIDI_DIR / f"{p['id']}.mid").exists()])
    print(f"\n모인 MIDI: {have} / {len(pieces)}")
    summary = Path(os.environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    with summary.open("a", encoding="utf-8") as f:
        f.write(f"### MIDI {have} / {len(pieces)}\n\n| 곡 | 결과 |\n|---|---|\n")
        for pid, name, ok, info in rows:
            f.write(f"| {name} | {'✅ ' if ok else '❌ '}{info} |\n")


if __name__ == "__main__":
    main()
