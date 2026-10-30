"""mufac 명령.

  python -m mufac new [--hook 문장] [--idea 생각] [--theme 사랑|어른|아픔] [--vocal 여성|남성|듀엣]
  python -m mufac photo <slug> [--pick N]
  python -m mufac produce <slug> [--upload] [--no-short]
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

from . import song as songmod
from .song import Song

REPO = os.environ.get("GITHUB_REPOSITORY", "kjhoeakjy/mufac")
KST = dt.timezone(dt.timedelta(hours=9))


def _output(key: str, value: str) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")


def write_readme(s: Song) -> None:
    m = s.meta
    fence = "```"
    lines = [f"# {m.get('title', s.slug)}", ""]
    if s.photo_path.exists():
        lines += ["![](photo.jpg)", ""]
    lines += [f"> {m.get('hook', '')}", "", f"{m.get('theme', '')} · {m.get('story', '')}", ""]

    yt = m.get("youtube") or {}
    if yt:
        lines += ["## 유튜브", ""]
        if yt.get("main"):
            lines.append(f"- 본편 https://youtu.be/{yt['main']}")
        if yt.get("short"):
            lines.append(f"- 쇼츠 https://youtube.com/shorts/{yt['short']}")
        lines += ["- 비공개로 올라갑니다. [YouTube Studio](https://studio.youtube.com)에서 공개로 바꾸세요.", ""]

    lines += [
        "## 1. Suno에 붙여넣기", "",
        "[Suno 열기](https://suno.com/create)에서 Custom 모드를 켜고 아래를 칸마다 붙여넣으세요.", "",
        "**Style**", f"{fence}text", m.get("style", ""), fence, "",
        "**Exclude styles**", f"{fence}text", m.get("exclude", ""), fence, "",
        "**Title**", f"{fence}text", m.get("title", ""), fence, "",
        "**Lyrics**", f"{fence}text", m.get("lyrics", "").strip(), fence, "",
        "## 2. 곡 올리기", "",
        f"두 곡 중 마음에 드는 하나를 MP3로 받아 [이 폴더에 올리세요](https://github.com/{REPO}/upload/main/songs/{s.slug}).",
        "올리면 영상 만들기가 자동으로 시작됩니다. 진행은 [Actions](https://github.com/" + REPO + "/actions)에서 봅니다.", "",
        "가사 자막 위치가 틀리면 `timing.lrc`의 시간을 고치고 Actions에서 '영상 만들기'를 다시 실행하세요.", "",
    ]
    others = [c for i, c in enumerate(m.get("candidates") or []) if i != m.get("chosen", 0)]
    if others:
        lines += ["## 다른 후렴 후보", ""]
        lines += [f"- {c['hook']} ({c['theme']}, {c['story']})" for c in others]
        lines += ["", "이 중 하나로 쓰려면 '새 곡' 실행할 때 후렴 칸에 붙여넣으세요.", ""]
    (s.dir / "README.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_new(a) -> None:
    from .photo import fetch
    from .write import write_song

    avoid = [x.meta.get("hook", "") for x in songmod.all_songs()][-40:]
    data = write_song(hook=a.hook, idea=a.idea, theme=a.theme, vocal=a.vocal, avoid=avoid)
    s = Song(songmod.new_slug())
    pick = data["candidates"][data["chosen"]]
    s.meta = {
        "title": data["title"],
        "hook": pick["hook"],
        "theme": pick["theme"],
        "story": pick["story"],
        "created": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "style": data["style"],
        "exclude": data["exclude"],
        "photo_query": data["photo_query"],
        "image_prompt": data["image_prompt"],
        "tags": data["tags"],
        "candidates": data["candidates"],
        "chosen": data["chosen"],
        "lyrics": data["lyrics"],
    }
    s.save()
    try:
        fetch(s)
    except Exception as e:  # 사진이 없어도 곡 폴더는 남긴다
        print(f"사진을 못 가져왔습니다: {e}", file=sys.stderr)
    s.save()
    write_readme(s)
    print(s.slug)
    _output("slug", s.slug)
    _output("title", s.meta["title"])


def cmd_photo(a) -> None:
    from .photo import fetch

    s = Song(a.slug)
    if a.prompt:
        s.meta["image_prompt"] = a.prompt
    fetch(s, pick=a.pick)
    s.save()
    write_readme(s)


def cmd_produce(a) -> None:
    from . import youtube
    from .align import short_window, timings
    from .render import prepare, render_main, render_short, thumbnail, write_ass_main, write_ass_short

    cfg = songmod.config()
    artist = cfg.get("artist", "")
    s = Song(a.slug)
    if not s.audio_path():
        sys.exit(f"{s.slug}: 노래 파일이 없습니다. mp3를 폴더에 올려주세요.")
    if not s.photo_path.exists():
        from .photo import _gradient, fetch
        try:
            fetch(s)
        except Exception as e:  # 사진 키가 막혀도 영상은 만든다
            print(f"사진을 못 가져와 단색 배경으로 만듭니다: {e}", flush=True)
            s.meta["photo"] = _gradient(s)
        s.save()

    print("가사 위치 찾는 중", flush=True)
    rows = timings(s, cfg.get("whisper_model", "medium"))
    src = prepare(s)
    thumb = thumbnail(s, artist)

    ass = s.out / "main.ass"
    write_ass_main(s, rows, ass, artist)
    print("본편 영상 만드는 중", flush=True)
    main = render_main(s, src, ass)

    short = None
    if not a.no_short:
        start, end = short_window(s, rows, float(cfg.get("short_seconds", 40)))
        ass_s = s.out / "short.ass"
        write_ass_short(s, rows, ass_s, artist, start, end)
        print(f"쇼츠 만드는 중 ({start:.1f}s~{end:.1f}s)", flush=True)
        short = render_short(s, src, ass_s, start, end)
        s.meta["short_window"] = [round(start, 2), round(end, 2)]

    if a.upload:
        if not youtube.ready():
            print("유튜브 키가 없어 업로드는 건너뜁니다.", flush=True)
        else:
            yt = s.meta.setdefault("youtube", {})
            title = cfg["youtube_title"].format(title=s.meta["title"], artist=artist).strip(" -")
            tags = s.meta.get("tags") or []
            if not yt.get("main"):
                print("유튜브 본편 업로드", flush=True)
                yt["main"] = youtube.upload(main, title=title, desc=youtube.description(s, artist),
                                            tags=tags, privacy=cfg["privacy"], thumb=thumb)
                s.save()
            if short and not yt.get("short"):
                print("유튜브 쇼츠 업로드", flush=True)
                yt["short"] = youtube.upload(short, title=f"{s.meta['title']} #shorts",
                                             desc=youtube.description(s, artist, main_id=yt.get("main")),
                                             tags=tags, privacy=cfg["privacy"])
    s.meta["produced"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    s.save()
    write_readme(s)
    print("완료", s.out, flush=True)


def cmd_check(a) -> None:
    from . import youtube

    if not youtube.ready():
        sys.exit("유튜브 키 세 개 중 빠진 것이 있습니다.")
    name = youtube.whoami()
    if not name:
        sys.exit("연결은 됐지만 이 구글 계정에 유튜브 채널이 없습니다.")
    print(f"연결된 채널: {name}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(f"### 연결된 채널: {name}\n")


def main() -> None:
    p = argparse.ArgumentParser(prog="mufac")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="새 곡 가사와 Suno 문구 만들기")
    n.add_argument("--hook", default="")
    n.add_argument("--idea", default="")
    n.add_argument("--theme", default="")
    n.add_argument("--vocal", default="")
    n.set_defaults(func=cmd_new)

    ph = sub.add_parser("photo", help="사진 다시 만들기")
    ph.add_argument("slug")
    ph.add_argument("--pick", type=int, default=None)
    ph.add_argument("--prompt", default="")
    ph.set_defaults(func=cmd_photo)

    pr = sub.add_parser("produce", help="영상 만들고 업로드")
    pr.add_argument("slug")
    pr.add_argument("--upload", action="store_true")
    pr.add_argument("--no-short", action="store_true")
    pr.set_defaults(func=cmd_produce)

    c = sub.add_parser("check", help="유튜브 연결 확인")
    c.set_defaults(func=cmd_check)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
