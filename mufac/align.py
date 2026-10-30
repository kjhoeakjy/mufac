"""가사 한 줄 한 줄이 노래 어디서 나오는지 찾는다.

음성 인식(faster-whisper)으로 들리는 글자와 시간을 얻고, 원래 가사 글자와 순서대로 맞춰
각 줄의 시작·끝 시간을 정한다. 결과는 timing.lrc로 저장하고, 이 파일이 있으면 다시 인식하지 않는다.
틀린 줄은 timing.lrc를 직접 고쳐서 다시 돌리면 된다.
"""

from __future__ import annotations

import difflib
import re
import subprocess

import numpy as np

from .song import Song

KEEP = re.compile(r"[0-9A-Za-z가-힣]")
LRC_RE = re.compile(r"^\[(\d+):(\d+(?:\.\d+)?)\](.*)$")


def duration(path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(out.stdout.strip())


def load_mono(path, sr: int = 16000) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


# ---------------------------------------------------------------- 타이밍

def timings(song: Song, model_size: str = "medium") -> list[dict]:
    """[{section, text, start, end}] — 가사 줄마다 시간(초)."""
    lines = song.lyric_lines()
    if song.timing_path.exists():
        stamps = read_lrc(song.timing_path)
        if len(stamps) == len(lines):
            return _finish(lines, [s for s, _ in stamps], song)
    starts = _recognize_and_match(song, lines, model_size)
    result = _finish(lines, starts, song)
    write_lrc(song.timing_path, result)
    return result


def _recognize_and_match(song: Song, lines, model_size: str) -> list[float | None]:
    from faster_whisper import WhisperModel

    audio = song.audio_path()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    prompt = " ".join(t for _, t in lines)[:220]
    # 파일 대신 파형을 넘긴다(faster-whisper의 PyAV 디코더 버전 문제를 피함)
    segments, _ = model.transcribe(
        load_mono(audio, 16000), language="ko", word_timestamps=True, vad_filter=False,
        initial_prompt=prompt, condition_on_previous_text=False, beam_size=2,  # 줄 맞추기엔 충분하고 두 배 빠르다
    )
    # 인식된 글자마다 시간 하나
    t_chars, t_times = [], []
    for seg in segments:
        for w in seg.words or []:
            chars = [c for c in w.word if KEEP.match(c)]
            if not chars:
                continue
            step = (w.end - w.start) / len(chars)
            for i, c in enumerate(chars):
                t_chars.append(c)
                t_times.append(w.start + step * i)

    # 가사 글자마다 몇 번째 줄인지
    l_chars, l_line = [], []
    for idx, (_, text) in enumerate(lines):
        for c in text:
            if KEEP.match(c):
                l_chars.append(c)
                l_line.append(idx)

    matcher = difflib.SequenceMatcher(None, l_chars, t_chars, autojunk=False)
    hits: dict[int, list[float]] = {}
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            hits.setdefault(l_line[a + k], []).append(t_times[b + k])

    starts: list[float | None] = []
    for idx, (_, text) in enumerate(lines):
        n = sum(1 for c in text if KEEP.match(c))
        got = hits.get(idx, [])
        starts.append(min(got) if n and len(got) >= max(2, n * 0.3) else None)
    return starts


def _finish(lines, starts: list[float | None], song: Song) -> list[dict]:
    total = duration(song.audio_path())
    starts = list(starts)
    # 순서가 뒤집힌 값은 버린다
    last = -1.0
    for i, s in enumerate(starts):
        if s is not None and s <= last:
            starts[i] = None
        elif s is not None:
            last = s
    # 비어 있는 줄은 앞뒤 줄 사이를 글자 수 비율로 채운다
    known = [i for i, s in enumerate(starts) if s is not None]
    if not known:
        # 인식이 전부 실패하면 곡 10%~90% 구간에 고르게 놓는다
        span = np.linspace(total * 0.1, total * 0.9, len(lines) + 1)
        starts = list(span[:-1])
    else:
        lens = [max(1, len(t)) for _, t in lines]
        first, lastk = known[0], known[-1]
        # 앞뒤 끝은 한 글자 약 0.28초로 잡아 늘린다
        for i in range(first - 1, -1, -1):
            starts[i] = max(0.0, starts[i + 1] - lens[i] * 0.28 - 0.4)
        for i in range(lastk + 1, len(lines)):
            starts[i] = min(total - 1.0, starts[i - 1] + lens[i - 1] * 0.28 + 0.4)
        for a, b in zip(known, known[1:]):
            if b - a > 1:
                weights = np.cumsum([lens[i] for i in range(a, b)])
                for j, i in enumerate(range(a + 1, b)):
                    starts[i] = starts[a] + (starts[b] - starts[a]) * weights[j] / weights[-1]
    out = []
    for i, (section, text) in enumerate(lines):
        start = float(starts[i])
        nxt = float(starts[i + 1]) if i + 1 < len(lines) else total
        # 다음 줄까지 간주가 길면 줄 길이만큼만 보여준다
        end = min(nxt - 0.05, start + max(2.5, len(text) * 0.32 + 1.5))
        out.append({"section": section, "text": text, "start": round(start, 2), "end": round(max(end, start + 1.0), 2)})
    return out


# ---------------------------------------------------------------- LRC

def write_lrc(path, rows: list[dict]) -> None:
    body = []
    for r in rows:
        m, s = divmod(r["start"], 60)
        body.append(f"[{int(m):02d}:{s:05.2f}]{r['text']}")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def read_lrc(path) -> list[tuple[float, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = LRC_RE.match(line.strip())
        if m:
            rows.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return rows


# ---------------------------------------------------------------- 쇼츠 구간

def short_window(song: Song, rows: list[dict], seconds: float) -> tuple[float, float]:
    """쇼츠로 자를 구간. 첫 후렴을 우선, 없으면 가장 큰 소리 구간."""
    total = duration(song.audio_path())
    seconds = min(seconds, total)
    chorus = [r for r in rows if "chorus" in r["section"].lower()]
    if chorus:
        first = chorus[0]
        start = max(0.0, first["start"] - 2.0)
        return start, min(total, start + seconds)
    audio = load_mono(song.audio_path(), 8000)
    hop = 4000  # 0.5초
    rms = np.sqrt(np.add.reduceat(audio ** 2, np.arange(0, len(audio), hop)) / hop)
    win = int(seconds * 2)
    if len(rms) <= win:
        return 0.0, seconds
    score = np.convolve(rms, np.ones(win), "valid")
    start = float(np.argmax(score[: max(1, len(score) - 20)]) / 2)
    return start, start + seconds
