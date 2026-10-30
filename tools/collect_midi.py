"""공개 악보 저장소에서 카탈로그 곡의 MIDI를 모은다. GitHub Actions에서 돌린다.

출처
- Mutopia Project (mutopiaproject.org): 저작권이 끝난 악보를 자원봉사자가 LilyPond로 옮긴 것. 각 곡에 MIDI가 함께 있다.
  검색 결과 페이지에서 .mid 링크를 찾아 받는다.

실행: python tools/collect_midi.py [id ...]   (인자가 없으면 아직 없는 곡 전부)
결과: assets/classical/midi/<id>.mid, 표준출력에 보고.
"""

from __future__ import annotations

import html
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
SEARCH = "https://www.mutopiaproject.org/cgibin/make-table.cgi?searchingfor={q}"


def mutopia_candidates(query: str) -> list[str]:
    url = SEARCH.format(q=urllib.parse.quote_plus(query))
    r = requests.get(url, headers=UA, timeout=60)
    r.raise_for_status()
    page = html.unescape(r.text)
    links = re.findall(r'href="([^"]+\.mid)"', page, flags=re.I)
    out = []
    for link in links:
        full = urllib.parse.urljoin(url, link)
        if full not in out:
            out.append(full)
    return out


def valid_midi(data: bytes) -> bool:
    return data[:4] == b"MThd" and len(data) > 200


def fetch(piece: dict) -> tuple[bool, str]:
    q = piece.get("mutopia")
    if not q:
        return False, "검색어 없음"
    try:
        cands = mutopia_candidates(q)
    except Exception as e:  # 네트워크 오류는 보고만
        return False, f"검색 실패: {e}"
    if not cands:
        words = q.split()
        if len(words) > 2:
            try:
                cands = mutopia_candidates(" ".join(words[:2]))
            except Exception:
                cands = []
    if not cands:
        return False, "검색 결과 없음"
    # 여러 악장이 있으면 파일 이름에 곡 id 힌트가 있는 것을 우선, 아니면 첫 번째
    hints = [w.lower() for w in re.split(r"[\s_]+", piece["id"]) if len(w) > 2]
    cands.sort(key=lambda u: (not any(h in u.lower() for h in hints), len(u)))
    for url in cands[:5]:
        try:
            data = requests.get(url, headers=UA, timeout=120).content
        except Exception:
            continue
        if valid_midi(data):
            (MIDI_DIR / f"{piece['id']}.mid").write_bytes(data)
            return True, url
    return False, f"받은 파일이 MIDI가 아님 ({cands[0]})"


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
        ok, info = fetch(p)
        rows.append((p["id"], p["name"], ok, info))
        print(("OK   " if ok else "MISS ") + f"{p['id']:22} {p['name']:20} {info}", flush=True)
    have = len([p for p in classical.catalog(available_only=False) if (MIDI_DIR / f"{p['id']}.mid").exists()])
    print(f"\n모인 MIDI: {have} / {len(pieces)}")
    summary = Path(__import__('os').environ.get("GITHUB_STEP_SUMMARY", "/dev/null"))
    with summary.open("a", encoding="utf-8") as f:
        f.write(f"### MIDI {have} / {len(pieces)}\n\n| 곡 | 결과 |\n|---|---|\n")
        for pid, name, ok, info in rows:
            f.write(f"| {name} | {'✅ ' if ok else '❌ '}{info} |\n")


if __name__ == "__main__":
    main()
