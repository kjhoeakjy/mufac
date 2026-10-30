"""클래식 주제를 노래 형태로 편곡한다.

원곡 전체를 그대로 부르는 대신, 요즘 노래가 클래식을 인용하는 방식으로 만든다.
- 전주: 원곡 주제를 피아노가 연주
- 절(Verse): 원곡 조성의 흔한 진행 위에 반주만. 가사와 선율은 자유
- 후렴(Chorus): 원곡 주제 선율을 그대로 부른다
- 간주: 원곡 주제를 한 옥타브 위에서 연주
- 마지막 후렴, 후주

결과 melody.mp3(노래 형태 전체)를 Suno에 Upload Audio → Cover로 넣으면 절은 새로 만들고 후렴은 원곡 선율을 따른다.
theme.mp3는 주제만 따로(전주용 Extend에 쓸 수 있다).
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

from . import classical as cl

Note = tuple[float, float, int]  # (시작초, 끝초, 미디음)

THEME_MIN, THEME_MAX = 15.0, 28.0
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


# ---------------------------------------------------------------- 주제 뽑기

def theme_from_midi(path: Path) -> tuple[list[list[Note]], float]:
    """MIDI 첫머리에서 10~26초 분량의 프레이즈 묶음과 박 길이를 돌려준다."""
    from . import midi
    sky = midi.skyline(midi.notes(path))
    phs = [p for p in midi.phrases(sky) if len(p) >= 3]
    if not phs:
        raise ValueError(f"프레이즈를 찾지 못함: {path}")
    picked: list[list[Note]] = []
    for p in phs:
        end = p[-1][1] - phs[0][0][0]
        if picked and end > THEME_MAX:
            break
        picked.append(p)
        if end >= THEME_MIN and len(picked) >= 2:
            break
    t0 = picked[0][0][0]
    picked = [[(s - t0, e - t0, m) for s, e, m in p] for p in picked]
    onsets = sorted(s for p in picked for s, _, _ in p)
    ioi = np.diff(onsets)
    ioi = ioi[ioi > 0.08]
    beat = float(np.median(ioi)) if len(ioi) else 0.5
    while beat < 0.3:
        beat *= 2
    while beat > 0.9:
        beat /= 2
    return picked, beat


def theme_from_hand(piece: dict) -> tuple[list[list[Note]], float]:
    spb = 60.0 / piece["bpm"]
    sec = piece["sections"][piece["map"]["chorus"]]
    out, t = [], 0.0
    for ph in sec["phrases"]:
        notes = []
        for m, beats in cl.parse_phrase(ph):
            if m is not None:
                notes.append((t, t + beats * spb * 0.95, m))
            t += beats * spb
        out.append(notes)
    return out, spb


# ---------------------------------------------------------------- 조성과 코드

def key_of(notes: list[Note]) -> tuple[int, str]:
    hist = np.zeros(12)
    for s, e, m in notes:
        hist[m % 12] += max(0.05, e - s)
    best = (-9, 0, "major")
    for tonic in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            r = np.corrcoef(np.roll(prof, tonic), hist)[0, 1]
            if r > best[0]:
                best = (r, tonic, mode)
    return best[1], best[2]


def diatonic(tonic: int, mode: str) -> list[tuple[int, str]]:
    """조의 3화음 (근음 pc, 성질)."""
    if mode == "major":
        degs, quals = [0, 2, 4, 5, 7, 9, 11], ["", "m", "m", "", "", "m", "dim"]
    else:
        degs, quals = [0, 2, 3, 5, 7, 8, 10], ["m", "dim", "", "m", "m", "", ""]
    return [((tonic + d) % 12, q) for d, q in zip(degs, quals)]


def chord_name(pc: int, qual: str) -> str:
    return NAMES[pc % 12] + qual


def verse_progression(tonic: int, mode: str) -> list[str]:
    d = diatonic(tonic, mode)
    if mode == "major":
        seq = [d[0], d[4], d[5], d[3]]            # I V vi IV
    else:
        seq = [d[0], d[5], d[2], d[6]]            # i VI III VII
    return [chord_name(*c) for c in seq]


def chords_under(theme: list[Note], tonic: int, mode: str, bar: float, total: float) -> list[tuple[float, str]]:
    """주제 마디마다 가장 잘 맞는 조성 안 3화음을 고른다."""
    cands = diatonic(tonic, mode)
    out = []
    t = 0.0
    prev = None
    while t < total - 1e-6:
        hist = np.zeros(12)
        for s, e, m in theme:
            ov = min(e, t + bar) - max(s, t)
            if ov > 0:
                hist[m % 12] += ov
        best, score = None, -1.0
        for pc, q in cands:
            tones = [(pc + i) % 12 for i in cl.QUALITY[q]]
            sc = sum(hist[x] for x in tones) + (0.15 * hist.sum() if (pc, q) == cands[0] else 0)
            if (pc, q) == prev:
                sc += 0.05 * hist.sum()
            if sc > score:
                best, score = (pc, q), sc
        if hist.sum() == 0:
            best = prev or cands[0]
        prev = best
        out.append((t, chord_name(*best)))
        t += bar
    return out


# ---------------------------------------------------------------- 렌더

def _play_chords(track: cl.Track, chords: list[tuple[float, str]], t0: float, bar: float, beat: float, vel: float, arp: bool) -> None:
    for start, sym in chords:
        bass, notes = cl.parse_chord(sym)
        at = t0 + start
        track.note(bass, at, bar * 0.95, vel * 0.9)
        if arp:
            seq = [notes[0], notes[-1], notes[1] + 12 if len(notes) > 1 else notes[0] + 12, notes[-1]]
            k = 0
            while k * beat < bar - 1e-6:
                track.note(seq[k % 4], at + k * beat, beat * 0.9, vel * (0.7 if k == 0 else 0.5))
                k += 1
        else:
            for n in notes:
                track.note(n, at, bar * 0.95, vel * 0.65)


def _play_theme(track: cl.Track, phrases: list[list[Note]], t0: float, vel: float, octave: int = 0, timbre: str = "piano") -> None:
    for p in phrases:
        for s, e, m in p:
            dur = max(0.12, e - s)
            if timbre == "strings":
                dur = max(dur, 0.35)
            track.note(m + 12 * octave, t0 + s, dur, vel, timbre)


def _bar(beat: float) -> float:
    """마디 길이. 1.6~3.4초 사이로 맞춘다(아주 빠르거나 느린 박은 묶거나 나눈다)."""
    bar = beat * 4
    while bar < 1.6:
        bar *= 2
    while bar > 3.4:
        bar /= 2
    return bar


def _verse_bars(bar: float) -> int:
    """절 길이가 16초 안팎이 되도록 4마디 단위로."""
    return max(8, int(round(16 / bar / 4)) * 4)


def render(piece: dict, out_dir: Path, timbre: str = "piano") -> dict:
    """timbre: 주제 선율의 음색 piano | guitar | strings | bell. 반주는 피아노."""
    timbre = timbre if timbre in cl.TIMBRES else "piano"
    if piece.get("midi"):
        phrases, beat = theme_from_midi(piece["midi"])
    else:
        phrases, beat = theme_from_hand(cl.BY_ID[piece["hand"]])
    theme = [n for p in phrases for n in p]
    theme_len = max(e for _, e, _ in theme)
    bar = _bar(beat)
    # 주제 길이를 마디 단위로 올림
    theme_bars = int(np.ceil(theme_len / bar - 1e-6))
    theme_span = theme_bars * bar
    tonic, mode = key_of(theme)
    under = chords_under(theme, tonic, mode, bar, theme_span)
    verse = verse_progression(tonic, mode)
    verse_bars = _verse_bars(bar)
    verse_chords = [(i * bar, verse[i % 4]) for i in range(verse_bars)]
    verse_span = verse_bars * bar

    form = [("전주", "intro", theme_span), ("1절", "verse", verse_span), ("후렴", "chorus", theme_span),
            ("2절", "verse", verse_span), ("후렴", "chorus", theme_span), ("간주", "interlude", theme_span),
            ("마지막 후렴", "chorus", theme_span), ("후주", "outro", bar * 2)]
    total = sum(d for _, _, d in form)
    full, solo = cl.Track(total), cl.Track(theme_span)
    t = 0.0
    plan = []
    for label, kind, dur in form:
        if kind in ("intro", "chorus", "interlude"):
            _play_chords(full, under, t, bar, beat, 0.45 if kind != "chorus" else 0.5, arp=(kind != "intro"))
            _play_theme(full, phrases, t, 0.95 if kind == "chorus" else 0.8, octave=1 if kind == "interlude" else 0, timbre=timbre)
        elif kind == "verse":
            _play_chords(full, verse_chords, t, bar, beat, 0.42, arp=True)
        else:
            bass, notes = cl.parse_chord(chord_name(tonic, "" if mode == "major" else "m"))
            full.note(bass, t, dur, 0.8)
            for n in notes:
                full.note(n, t, dur, 0.55)
        plan.append({"part": label, "start": round(t, 1), "seconds": round(dur, 1)})
        t += dur
    _play_chords(solo, under, 0.0, bar, beat, 0.45, arp=True)
    _play_theme(solo, phrases, 0.0, 0.95, timbre=timbre)

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {}
    for label, tr, secs in (("melody", full, total), ("theme", solo, theme_span)):
        x = cl._reverb(tr.buf)[: int(secs * cl.SR) + int(2.5 * cl.SR)]
        fo = int(min(2.5, secs / 4) * cl.SR)
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
    for old in ("melody-solo.mp3",):
        (out_dir / old).unlink(missing_ok=True)
    return {
        "seconds": round(total, 1), "theme_seconds": round(theme_span, 1), "bpm": round(60 / beat),
        "key": chord_name(tonic, "" if mode == "major" else "m"),
        "chorus_syllables": [len(p) for p in phrases], "verse_bars": verse_bars, "instrument": timbre,
        "plan": plan, "source": "midi" if piece.get("midi") else "hand",
    }


# ---------------------------------------------------------------- 가사 계획

def lyric_plan(piece: dict) -> str:
    if piece.get("midi"):
        phrases, beat = theme_from_midi(piece["midi"])
    else:
        phrases, beat = theme_from_hand(cl.BY_ID[piece["hand"]])
    counts = [len(p) for p in phrases]
    theme_len = max(e for p in phrases for _, e, _ in p)
    bar = _bar(beat)
    verse_sec = _verse_bars(bar) * bar
    return "\n".join([
        f"멜로디 곡: {piece['name']} ({piece['composer']}). 노래 형태는 melody.mp3와 같다: 전주(원곡 주제 연주 {theme_len:.0f}초) → 1절 → 후렴 → 2절 → 후렴 → 간주(원곡 주제) → 마지막 후렴 → 후주.",
        f"- [Chorus]와 [Final Chorus]는 원곡 주제 선율을 그대로 부른다. 줄 {len(counts)}개, 줄마다 음절 수 {' / '.join(map(str, counts))} (±1).",
        f"- [Verse 1], [Verse 2]는 반주만 있는 {verse_sec:.0f}초 구간이라 선율과 가사가 자유다. 4줄, 한 줄 7~11음절. 두 절의 줄 수와 음절 수를 맞춘다.",
        "- [Intro]와 [Interlude]는 태그만 쓴다(원곡 주제가 연주되는 자리). [Pre-Chorus], [Bridge]는 쓰지 않는다. [Outro]는 태그만.",
        "- 구간 순서: [Intro] [Verse 1] [Chorus] [Verse 2] [Chorus] [Interlude] [Final Chorus] [Outro]. [Final Chorus]는 [Chorus]와 같은 줄 수·음절 수로 한두 줄만 바꾼다.",
        "- 긴 음 자리에는 열린 모음(아, 어, 오)을 둔다.",
    ])
