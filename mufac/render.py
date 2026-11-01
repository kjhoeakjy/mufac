"""배경 그림 한 장 + 노래 + 가사 자막으로 영상을 만든다.

- main.mp4  1920x1080, 곡 전체. 배경은 움직이지 않고, 처음에 제목이 가운데 떴다가 가사가 한 줄씩 바뀐다.
- short1~4.mp4 1080x1920, 도입·후렴·브릿지·엔딩 네 구간. 구간마다 다른 세로 그림, 제목은 위에 작게 내내, 가사는 처음부터.
- thumb.jpg 1280x720 유튜브 썸네일. 같은 배경 가운데에 제목.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .align import duration
from .song import FONTS, Song

# 글꼴은 Pretendard(SIL OFL). 자막(ASS)에서는 글꼴 이름으로, 썸네일(PIL)에서는 파일로 쓴다
TITLE_FONT, TITLE_FILE = "Pretendard", FONTS / "Pretendard-Bold.otf"
LYRIC_FONT = "Pretendard SemiBold"
SMALL_FONT, SMALL_FILE = "Pretendard Medium", FONTS / "Pretendard-Medium.otf"
FPS = 30


# ---------------------------------------------------------------- 이미지 준비

def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _shade(w: int, h: int, *, bottom: float, top: float, vignette: float) -> Image.Image:
    """글자가 잘 읽히도록 위아래를 어둡게, 가장자리를 살짝 어둡게 하는 덮개."""
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(-1, 1, w)[None, :]
    yy = np.linspace(-1, 1, h)[:, None]
    a = np.clip((y - 0.55) / 0.45, 0, 1) ** 1.6 * bottom
    a = np.maximum(a, np.clip((0.25 - y) / 0.25, 0, 1) ** 1.6 * top)
    a = np.maximum(a, np.clip((x ** 2 + yy ** 2) ** 0.5 - 0.75, 0, 1) * vignette)
    alpha = (np.clip(a, 0, 1) * 255).astype("uint8")
    rgba = np.zeros((h, w, 4), dtype="uint8")
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def prepare(song: Song) -> dict:
    """본편 배경 한 장과 쇼츠 배경 네 장. 세로 그림이 없는 자리는 바로 앞 그림(없으면 가로 그림)을 쓴다."""
    song.out.mkdir(parents=True, exist_ok=True)
    photo = Image.open(song.photo_path).convert("RGB")
    paths = {"land": song.out / "src_land.png", "ports": []}
    # 배경은 움직이지 않으므로 출력 크기 그대로, 글자용 그늘까지 미리 합쳐 둔다(ffmpeg에서 겹치면 매 프레임 비용)
    land = Image.alpha_composite(_cover(photo, 1920, 1080).convert("RGBA"), _shade(1920, 1080, bottom=0.55, top=0.0, vignette=0.3))
    land.convert("RGB").save(paths["land"])
    prev = photo
    for i, vp in enumerate(song.photo_v_paths(), 1):
        vertical = Image.open(vp).convert("RGB") if vp.exists() else prev
        prev = vertical
        port = Image.alpha_composite(_cover(vertical, 1080, 1920).convert("RGBA"), _shade(1080, 1920, bottom=0.45, top=0.22, vignette=0.3))
        out = song.out / f"src_port{i}.png"
        port.convert("RGB").save(out)
        paths["ports"].append(out)
    paths["port"] = paths["ports"][0]
    return paths


# ---------------------------------------------------------------- 자막(ASS)

def _ts(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def _esc(text: str) -> str:
    return text.replace("\\", "＼").replace("{", "｛").replace("}", "｝")


def _ass_header(w: int, h: int, styles: list[str]) -> str:
    return "\n".join([
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        *styles, "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])


def _style(name, font, size, align, margin_v, *, bold=0, shadow=1, margin_lr=120, color="&H00FFFFFF", spacing=0):
    # 외곽선 없이 옅은 그림자만. 두꺼운 테두리가 촌스러움의 주범이다
    return (f"Style: {name},{font},{size},{color},&H00FFFFFF,&H00000000,&H78000000,"
            f"{bold},0,0,0,100,100,{spacing},0,1,0,{shadow},{align},{margin_lr},{margin_lr},{margin_v},1")


def write_ass_main(song: Song, rows: list[dict], path: Path, artist: str) -> None:
    title = song.meta.get("title", "")
    lines = [_ass_header(1920, 1080, [
        _style("Lyric", LYRIC_FONT, 62, 2, 110),
        _style("Title", TITLE_FONT, 84, 5, 0, bold=-1, spacing=1),
        _style("Artist", SMALL_FONT, 36, 5, 0, color="&H00E6E6E6", spacing=2),
    ])]
    if rows:
        card_end = max(4.0, min(8.0, rows[0]["start"] - 0.3))
    else:  # 연주곡: 제목을 끝까지 둔다
        from .align import duration
        card_end = duration(song.audio_path())
    # 제목은 같은 배경 한가운데
    lines.append(f"Dialogue: 0,{_ts(0.6)},{_ts(card_end)},Title,,0,0,0,,{{\\fad(900,700)\\pos(960,{520 if artist else 540})}}{_esc(title)}")
    if artist:
        lines.append(f"Dialogue: 0,{_ts(1.0)},{_ts(card_end)},Artist,,0,0,0,,{{\\fad(900,700)\\pos(960,620)}}{_esc(artist)}")
    for r in rows:
        lines.append(f"Dialogue: 0,{_ts(r['start'] - 0.15)},{_ts(r['end'])},Lyric,,0,0,0,,"
                     f"{{\\fad(220,320)}}{_esc(r['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ass_short(song: Song, rows: list[dict], path: Path, artist: str, start: float, end: float) -> None:
    title = song.meta.get("title", "")
    lines = [_ass_header(1080, 1920, [
        _style("Lyric", LYRIC_FONT, 54, 5, 0, margin_lr=100),
        _style("Title", TITLE_FONT, 72, 5, 0, bold=-1, margin_lr=90, spacing=1),
        _style("Top", TITLE_FONT, 50, 8, 0, bold=-1, margin_lr=90, spacing=1),
        _style("Artist", SMALL_FONT, 34, 5, 0, color="&H00E6E6E6", spacing=2),
    ])]
    span = end - start
    if rows:
        # 첫 1초가 승부라 제목 카드로 시간을 쓰지 않는다. 제목은 위쪽(상태 표시줄 아래)에 작게 내내 둔다
        lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Top,,0,0,0,,{{\\fad(300,300)\\pos(540,200)}}{_esc(title)}")
        if artist:
            lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Artist,,0,0,0,,{{\\fad(300,300)\\pos(540,262)}}{_esc(artist)}")
        # 구간 앞에 가사 없는 전주가 길면 그동안 후렴 한 줄을 띄운다(첫 1~2초에 글이 있어야 넘기지 않는다)
        first = next((r["start"] - start for r in rows if r["end"] > start), span)
        hook = (song.meta.get("hook") or "").strip()
        if hook and first > 2.5:
            lines.append(f"Dialogue: 0,{_ts(0.2)},{_ts(first - 0.4)},Lyric,,0,0,0,,{{\\fad(300,400)\\pos(540,1380)}}{_esc(hook)}")
    else:  # 연주곡은 제목을 가운데에 끝까지
        lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Title,,0,0,0,,{{\\fad(400,500)\\pos(540,{880 if artist else 900})}}{_esc(title)}")
        if artist:
            lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Artist,,0,0,0,,{{\\fad(400,500)\\pos(540,960)}}{_esc(artist)}")
    for r in rows:
        a, b = r["start"] - start, r["end"] - start
        if b <= 0 or a >= span:
            continue
        lines.append(f"Dialogue: 0,{_ts(a - 0.15)},{_ts(min(b, span))},Lyric,,0,0,0,,"
                     f"{{\\fad(220,320)\\pos(540,1380)}}{_esc(r['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- ffmpeg

def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd[:6]), "...", flush=True)
    subprocess.run(cmd, check=True)


def _subs(path: Path) -> str:
    # subtitles 필터 인자는 ':'와 '\'를 이스케이프해야 한다
    esc = lambda p: str(p).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")
    return f"subtitles='{esc(path)}':fontsdir='{esc(FONTS)}'"


def render_main(song: Song, src: dict[str, Path], ass: Path) -> Path:
    audio = song.audio_path()
    total = duration(audio)
    out = song.out / "main.mp4"
    graph = (f"[0:v]{_subs(ass)},"
             f"fade=t=in:st=0:d=1.5,fade=t=out:st={max(0, total - 2.5):.2f}:d=2.5,format=yuv420p[v]")
    _run([
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-loop", "1", "-framerate", str(FPS), "-i", str(src["land"]),
        "-i", str(audio),
        "-filter_complex", graph, "-map", "[v]", "-map", "1:a",
        "-t", f"{total:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ])
    return out


def render_short(song: Song, src: dict, ass: Path, start: float, end: float, out: Path | None = None, port: Path | None = None) -> Path:
    audio = song.audio_path()
    span = end - start
    out = out or song.out / "short.mp4"
    port = port or src["port"]
    # 쇼츠는 끝나자마자 처음으로 돌아가며 재생되므로 페이드를 짧게 둔다(끊김 없이 이어지는 느낌)
    graph = (f"[0:v]{_subs(ass)},"
             f"fade=t=in:st=0:d=0.3,fade=t=out:st={max(0, span - 0.6):.2f}:d=0.6,format=yuv420p[v];"
             f"[1:a]afade=t=in:st=0:d=0.3,afade=t=out:st={max(0, span - 1.2):.2f}:d=1.2[a]")
    _run([
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-loop", "1", "-framerate", str(FPS), "-i", str(port),
        "-ss", f"{start:.2f}", "-t", f"{span:.2f}", "-i", str(audio),
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-t", f"{span:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ])
    return out


# ---------------------------------------------------------------- 썸네일

def _fit_font(draw, text, path, max_w, start):
    size = start
    while size > 40:
        font = ImageFont.truetype(str(path), size)
        if draw.textlength(text, font=font) <= max_w:
            return font
        size -= 4
    return ImageFont.truetype(str(path), size)


def thumbnail(song: Song, artist: str) -> Path:
    """영상 첫 화면과 같은 구성: 배경 그림 가운데에 제목."""
    img = _cover(Image.open(song.photo_path).convert("RGB"), 1280, 720)
    img = Image.alpha_composite(img.convert("RGBA"), _shade(1280, 720, bottom=0.35, top=0.0, vignette=0.55))
    draw = ImageDraw.Draw(img)
    title = song.meta.get("title", "")
    font = _fit_font(draw, title, TITLE_FILE, 1280 - 400, 60)
    small = ImageFont.truetype(str(SMALL_FILE), 22)
    tw = draw.textlength(title, font=font)
    x, y = (1280 - tw) / 2, 360 - font.size * 0.62 - (16 if artist else 0)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.text((x + 1, y + 3), title, font=font, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(6)))
    draw = ImageDraw.Draw(img)
    draw.text((x, y), title, font=font, fill=(255, 255, 255, 255))
    if artist:
        aw = draw.textlength(artist, font=small)
        draw.text(((1280 - aw) / 2, y + font.size + 22), artist, font=small, fill=(232, 232, 232, 255))
    out = song.out / "thumb.jpg"
    img.convert("RGB").save(out, quality=92)
    return out
