"""MIDI 악보 파일에서 선율을 읽고 피아노로 렌더링한다.

- notes(path): 모든 음을 (시작초, 끝초, 미디음, 세기, 트랙)로.
- skyline(notes): 같은 순간 가장 높은 음만 남긴 선율선.
- phrases(skyline): 쉼이나 긴 음에서 끊은 프레이즈. 가사 음절 수 계획에 쓴다.
- render(path, out_dir, seconds): 전체 악보 피아노 연주 melody.mp3, 선율만 melody-solo.mp3.
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import mido
import numpy as np

from . import classical as cl

MAX_SECONDS = 150.0


def notes(path: Path) -> list[tuple[float, float, int, int, int]]:
    mid = mido.MidiFile(str(path))
    tpb = mid.ticks_per_beat or 480
    # 템포 변화표(틱 → 초)
    tempo_changes = [(0, 500000)]
    for track in mid.tracks:
        t = 0
        for msg in track:
            t += msg.time
            if msg.type == "set_tempo":
                tempo_changes.append((t, msg.tempo))
    tempo_changes.sort()
    marks = [(0, 0.0, tempo_changes[0][1])]  # (틱, 초, 그 뒤 템포)
    for tick, tempo in tempo_changes[1:]:
        ptick, psec, ptempo = marks[-1]
        marks.append((tick, psec + (tick - ptick) * ptempo / 1e6 / tpb, tempo))

    def sec(tick: int) -> float:
        lo, hi = 0, len(marks) - 1
        while lo < hi:
            mid_ = (lo + hi + 1) // 2
            if marks[mid_][0] <= tick:
                lo = mid_
            else:
                hi = mid_ - 1
        ptick, psec, tempo = marks[lo]
        return psec + (tick - ptick) * tempo / 1e6 / tpb

    out = []
    for ti, track in enumerate(mid.tracks):
        t = 0
        on: dict[tuple[int, int], tuple[int, int]] = {}
        for msg in track:
            t += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                if getattr(msg, "channel", 0) == 9:
                    continue
                on[(msg.channel, msg.note)] = (t, msg.velocity)
            elif msg.type in ("note_off", "note_on"):
                key = (getattr(msg, "channel", 0), msg.note)
                if key in on:
                    st, vel = on.pop(key)
                    if t > st:
                        out.append((sec(st), sec(t), msg.note, vel, ti))
    out.sort()
    return out


def skyline(ns, grace: float = 0.06) -> list[tuple[float, float, int]]:
    """같은 순간(60ms 안) 가장 높은 음 하나. 다음 음이 시작되면 끊는다."""
    out: list[tuple[float, float, int]] = []
    i = 0
    while i < len(ns):
        t0 = ns[i][0]
        group = []
        while i < len(ns) and ns[i][0] - t0 <= grace:
            group.append(ns[i])
            i += 1
        top = max(group, key=lambda n: n[2])
        out.append((t0, top[1], top[2]))
    # 겹침 정리와 꾸밈음 합치기
    fixed = []
    for k, (s, e, p) in enumerate(out):
        nxt = out[k + 1][0] if k + 1 < len(out) else e
        e = min(e, nxt)
        if e - s < 0.05 and fixed:
            continue
        fixed.append((s, e, p))
    return fixed


def phrases(sky, max_notes: int = 14) -> list[list[tuple[float, float, int]]]:
    out, cur = [], []
    for k, (s, e, p) in enumerate(sky):
        cur.append((s, e, p))
        gap = sky[k + 1][0] - e if k + 1 < len(sky) else 9
        long_note = (e - s) >= 1.6
        if gap >= 0.28 or long_note or len(cur) >= max_notes:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def lyric_plan(path: Path, name: str, seconds: float = MAX_SECONDS) -> str:
    sky = [n for n in skyline(notes(path)) if n[0] < seconds]
    phs = [p for p in phrases(sky) if len(p) >= 3][:24]
    if not phs:
        return f"멜로디 곡: {name}. 가사 줄 수와 음절 수는 자유롭게."
    counts = [len(p) for p in phs]
    half = max(1, len(counts) // 2)
    lines = [f"멜로디 곡: {name}. 가사는 멜로디 파일(melody.mp3)을 처음부터 그대로 따라 부른다.",
             f"- 멜로디 프레이즈 {len(counts)}개, 순서대로 음 수: {' / '.join(map(str, counts))}",
             f"- [Verse 1]은 프레이즈 1~{half}, [Chorus]는 프레이즈 {half + 1}~{len(counts)}에 얹는다. 줄 하나가 프레이즈 하나, 줄의 음절 수는 그 프레이즈의 음 수(±1).",
             "- [Verse 2]와 [Final Chorus]는 같은 프레이즈가 되풀이되므로 같은 줄 수와 음절 수로 쓴다. [Bridge]는 [Verse]의 앞 절반 길이로. [Pre-Chorus], [Intro], [Outro]는 쓰지 않는다.",
             "- 긴 음 자리에는 '아', '요', '오'처럼 열린 모음을 둔다."]
    return "\n".join(lines)


def render(path: Path, out_dir: Path, seconds: float = MAX_SECONDS) -> dict:
    ns = notes(path)
    if not ns:
        raise ValueError(f"음이 없는 MIDI: {path}")
    end = min(seconds, max(e for _, e, *_ in ns))
    ns = [n for n in ns if n[0] < end]
    sky = skyline(ns)
    full, solo = cl.Track(end), cl.Track(end)
    vmax = max(v for *_, v, _ in ns) or 100
    for s, e, p, v, _ in ns:
        full.note(p, s, min(e, end) - s, 0.35 + 0.6 * (v / vmax))
    for s, e, p in sky:
        solo.note(p, s, min(e, end) - s, 0.95)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for label, tr in (("melody", full), ("melody-solo", solo)):
        x = cl._reverb(tr.buf)[: int(end * cl.SR) + int(2.5 * cl.SR)]
        fo = int(min(3.0, end / 4) * cl.SR)
        x[-fo:] *= np.linspace(1, 0, fo)
        x = x / max(1e-9, np.abs(x).max()) * 0.89
        wav = out_dir / f"{label}.wav"
        with wave.open(str(wav), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(cl.SR)
            w.writeframes((x * 32767).astype("<i2").tobytes())
        mp3 = out_dir / f"{label}.mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(wav), "-codec:a", "libmp3lame", "-q:a", "2", str(mp3)], check=True)
        wav.unlink()
        files[label] = mp3
    phs = phrases([n for n in sky if n[0] < end])
    return {"seconds": round(end, 1), "notes": len(ns), "phrases": [len(p) for p in phs if len(p) >= 3][:24],
            "source": "midi"}
