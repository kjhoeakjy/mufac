"""사진 + 노래 + 가사 자막으로 영상을 만든다.

- main.mp4  1920x1080, 곡 전체. 사진이 아주 천천히 확대·축소되고 가사가 한 줄씩 뜬다.
- short.mp4 1080x1920, 후렴 구간. 위에 제목, 가운데 아래 가사.
- thumb.jpg 1280x720 유튜브 썸네일.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .align import duration
from .song import FONTS, Song

SERIF = FONTS / "GowunBatang-Bold.ttf"
SANS = FONTS / "NotoSansKR-Medium.ttf"
FPS = 30
ZOOM_PERIOD = 48  # 초. 확대됐다가 돌아오는 한 주기


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


def prepare(song: Song) -> dict[str, Path]:
    song.out.mkdir(parents=True, exist_ok=True)
    photo = Image.open(song.photo_path).convert("RGB")
    paths = {
        "land": song.out / "src_land.jpg",
        "port": song.out / "src_port.jpg",
        "land_shade": song.out / "shade_land.png",
        "port_shade": song.out / "shade_port.png",
    }
    # 확대·축소가 부드럽도록 출력의 2배 크기로 준비
    _cover(photo, 3840, 2160).save(paths["land"], quality=92)
    vertical = Image.open(song.photo_v_path).convert("RGB") if song.photo_v_path.exists() else photo
    _cover(vertical, 2160, 3840).save(paths["port"], quality=92)
    _shade(1920, 1080, bottom=0.72, top=0.0, vignette=0.45).save(paths["land_shade"])
    _shade(1080, 1920, bottom=0.55, top=0.55, vignette=0.4).save(paths["port_shade"])
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


def _style(name, font, size, align, margin_v, *, bold=-1, shadow=2, margin_lr=120, color="&H00FFFFFF", spacing=1):
    return (f"Style: {name},{font},{size},{color},&H00FFFFFF,&H00000000,&H96000000,"
            f"{bold},0,0,0,100,100,{spacing},0,1,0,{shadow},{align},{margin_lr},{margin_lr},{margin_v},1")


def write_ass_main(song: Song, rows: list[dict], path: Path, artist: str) -> None:
    title = song.meta.get("title", "")
    cl = song.meta.get("classic") or {}
    origin = f"원곡 {cl['name']} · {cl['composer']}" if cl else ""
    lines = [_ass_header(1920, 1080, [
        _style("Lyric", "Gowun Batang", 64, 2, 110),
        _style("Title", "Gowun Batang", 96, 5, 0, spacing=2),
        _style("Artist", "Noto Sans KR Medium", 38, 5, 0, bold=0, color="&H00D8D8D8", spacing=3),
    ])]
    first = rows[0]["start"] if rows else 8.0
    card_end = max(4.0, min(8.0, first - 0.3))
    lines.append(f"Dialogue: 0,{_ts(0.6)},{_ts(card_end)},Title,,0,0,0,,{{\\fad(900,700)\\pos(960,500)}}{_esc(title)}")
    if artist:
        lines.append(f"Dialogue: 0,{_ts(1.0)},{_ts(card_end)},Artist,,0,0,0,,{{\\fad(900,700)\\pos(960,600)}}{_esc(artist)}")
    if origin:
        lines.append(f"Dialogue: 0,{_ts(1.4)},{_ts(card_end)},Artist,,0,0,0,,{{\\fad(900,700)\\pos(960,660)\\fs30}}{_esc(origin)}")
    for r in rows:
        lines.append(f"Dialogue: 0,{_ts(r['start'] - 0.15)},{_ts(r['end'])},Lyric,,0,0,0,,"
                     f"{{\\fad(220,320)}}{_esc(r['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_ass_short(song: Song, rows: list[dict], path: Path, artist: str, start: float, end: float) -> None:
    title = song.meta.get("title", "")
    lines = [_ass_header(1080, 1920, [
        _style("Lyric", "Gowun Batang", 76, 5, 0, margin_lr=90),
        _style("Title", "Gowun Batang", 70, 8, 250, margin_lr=90, spacing=2),
        _style("Artist", "Noto Sans KR Medium", 34, 8, 350, bold=0, color="&H00D8D8D8", spacing=3),
    ])]
    span = end - start
    lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Title,,0,0,0,,{{\\fad(600,0)}}{_esc(title)}")
    if artist:
        lines.append(f"Dialogue: 0,{_ts(0)},{_ts(span)},Artist,,0,0,0,,{{\\fad(600,0)}}{_esc(artist)}")
    for r in rows:
        a, b = r["start"] - start, r["end"] - start
        if b <= 0 or a >= span:
            continue
        lines.append(f"Dialogue: 0,{_ts(a - 0.15)},{_ts(min(b, span))},Lyric,,0,0,0,,"
                     f"{{\\fad(220,320)\\pos(540,1380)}}{_esc(r['text'])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- ffmpeg

def _zoom(size: str, frames_offset: int = 0) -> str:
    # 1.0배에서 시작해 1.06배까지 아주 천천히 다가갔다가 돌아온다
    on = f"(on+{frames_offset})"
    return (f"zoompan=z='1.03-0.03*cos(2*PI*{on}/({FPS}*{ZOOM_PERIOD}))'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={size}:fps={FPS}")


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
    graph = (f"[0:v]{_zoom('1920x1080')},format=rgba[bg];"
             f"[bg][1:v]overlay=0:0,{_subs(ass)},"
             f"fade=t=in:st=0:d=1.5,fade=t=out:st={max(0, total - 2.5):.2f}:d=2.5,format=yuv420p[v]")
    _run([
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-loop", "1", "-framerate", str(FPS), "-i", str(src["land"]),
        "-loop", "1", "-framerate", str(FPS), "-i", str(src["land_shade"]),
        "-i", str(audio),
        "-filter_complex", graph, "-map", "[v]", "-map", "2:a",
        "-t", f"{total:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "film",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000",
        "-movflags", "+faststart", str(out),
    ])
    return out


def render_short(song: Song, src: dict[str, Path], ass: Path, start: float, end: float) -> Path:
    audio = song.audio_path()
    span = end - start
    out = song.out / "short.mp4"
    graph = (f"[0:v]{_zoom('1080x1920', int(start * FPS))},format=rgba[bg];"
             f"[bg][1:v]overlay=0:0,{_subs(ass)},"
             f"fade=t=in:st=0:d=0.6,fade=t=out:st={max(0, span - 1.5):.2f}:d=1.5,format=yuv420p[v];"
             f"[2:a]afade=t=in:st=0:d=0.8,afade=t=out:st={max(0, span - 2):.2f}:d=2[a]")
    _run([
        "ffmpeg", "-y", "-v", "warning", "-stats",
        "-loop", "1", "-framerate", str(FPS), "-i", str(src["port"]),
        "-loop", "1", "-framerate", str(FPS), "-i", str(src["port_shade"]),
        "-ss", f"{start:.2f}", "-t", f"{span:.2f}", "-i", str(audio),
        "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
        "-t", f"{span:.2f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-tune", "film",
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
    img = _cover(Image.open(song.photo_path).convert("RGB"), 1280, 720)
    img = Image.alpha_composite(img.convert("RGBA"), _shade(1280, 720, bottom=0.85, top=0.0, vignette=0.5))
    draw = ImageDraw.Draw(img)
    title = song.meta.get("title", "")
    font = _fit_font(draw, title, SERIF, 1280 - 160, 104)
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    y = 720 - 90 - font.size - (56 if artist else 0)
    sd.text((82, y + 4), title, font=font, fill=(0, 0, 0, 170))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(8)))
    draw = ImageDraw.Draw(img)
    draw.text((80, y), title, font=font, fill=(255, 255, 255, 255))
    if artist:
        draw.text((84, y + font.size + 26), artist, font=ImageFont.truetype(str(SANS), 34), fill=(225, 225, 225, 255))
    out = song.out / "thumb.jpg"
    img.convert("RGB").save(out, quality=92)
    return out
