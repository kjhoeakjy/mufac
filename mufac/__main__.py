"""mufac 명령.

  python -m mufac new [--hook 문장] [--idea 생각] [--theme 사랑|어른|아픔] [--vocal 여성|남성|듀엣]
  python -m mufac photo <slug> [--pick N]
  python -m mufac produce <slug> [--no-short]
  python -m mufac publish <slug>
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
    if m.get("why"):
        lines += ["## 이렇게 쓴 이유", "", m["why"], ""]
    refs = m.get("references") or []
    if refs:
        lines += ["참고한 곡", ""] + [f"- {r['title']} / {r['artist']}: {r['takeaway']}" for r in refs]
        lines += ["", "조사 전체는 [research.md](research.md).", ""]

    yt = m.get("youtube") or {}
    if yt:
        lines += ["## 유튜브", ""]
        if yt.get("main"):
            lines.append(f"- 본편 https://youtu.be/{yt['main']}")
        if yt.get("short"):
            lines.append(f"- 쇼츠 https://youtube.com/shorts/{yt['short']}")
        lines += ["- 비공개로 올라갑니다. [YouTube Studio](https://studio.youtube.com)에서 공개로 바꾸세요.", ""]

    cl = m.get("classic") or {}
    if cl:
        lines += [
            f"## 원곡: {cl['name']}", "",
            f"{cl['composer']}, {cl['year']}. {cl.get('reason', '')}", "",
            f"- [melody.mp3](melody.mp3) 노래 형태 전체: 전주·후렴·간주에 원곡 주제 ({cl.get('seconds', 0)}초)",
            f"- [theme.mp3](theme.mp3) 원곡 주제만 ({cl.get('theme_seconds', 0)}초)",
            "- [cover.jpg](cover.jpg) Suno 곡 이미지", "",
            "## 1. Suno에 멜로디 올리고 붙여넣기", "",
            "1. [Suno](https://suno.com/create)에서 **Upload Audio**로 melody.mp3를 올립니다.",
            "2. 올라간 곡의 메뉴에서 **Cover**를 고릅니다.",
            "3. 아래 Style, Exclude, Title, Lyrics를 칸마다 붙여넣고 만듭니다.", "",
        ]
    else:
        lines += ["## 1. Suno에 붙여넣기", "",
                  "[Suno 열기](https://suno.com/create)에서 Custom 모드를 켜고 아래를 칸마다 붙여넣으세요.", ""]
    lines += [
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


def _preview(s: Song) -> dict:
    from . import youtube
    return youtube.preview(s, songmod.config())


def cmd_new(a) -> None:
    from .photo import fetch
    from .write import write_song

    avoid = [x.meta.get("hook", "") for x in songmod.all_songs()][-40:]
    data = write_song(hook=a.hook, idea=a.idea, theme=a.theme, vocal=a.vocal, style=a.style,
                      classic=a.classic, avoid=avoid)
    s = Song(songmod.new_slug())
    pick = data["candidates"][data["chosen"]]
    s.meta = {
        "title": data["title"],
        "hook": pick["hook"],
        "theme": pick["theme"],
        "story": pick["story"],
        "created": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "request": {k: v for k, v in {"id": a.req, "idea": a.idea, "style": a.style, "classic": a.classic}.items() if v},
        "style": data["style"],
        "exclude": data["exclude"],
        "photo_query": data["photo_query"],
        "image_prompt": data["image_prompt"],
        "title_kind": data.get("title_kind", ""),
        "why": data.get("why", ""),
        "share_line": data.get("share_line", ""),
        "youtube_meta": {
            "situation": data.get("situation", ""),
            "shorts_title": data.get("shorts_title", ""),
            "intro": data.get("yt_intro", ""),
            "comment_prompt": data.get("comment_prompt", ""),
            "hashtags": data.get("hashtags", []),
        },
        "tags": data["tags"],
        "references": data.get("references", []),
        "candidates": data["candidates"],
        "chosen": data["chosen"],
        "lyrics": data["lyrics"],
    }
    if data.get("classic"):
        s.meta["classic"] = data["classic"]
    s.save()
    if data.get("classic"):
        from .classical import render as render_melody
        try:
            info = render_melody(data["classic"]["id"], s.dir)
            s.meta["classic"].update({k: info[k] for k in ("seconds", "theme_seconds", "bpm", "key", "chorus_syllables", "plan")})
        except Exception as e:  # 멜로디 파일이 없어도 가사는 남긴다
            print(f"원곡 멜로디를 만들지 못했습니다: {e}", file=sys.stderr)
    if data.get("research"):
        (s.dir / "research.md").write_text(f"# 레퍼런스 조사\n\n{data['research']}\n", encoding="utf-8")
    try:
        fetch(s)
    except Exception as e:  # 사진이 없어도 곡 폴더는 남긴다
        print(f"사진을 못 가져왔습니다: {e}", file=sys.stderr)
    s.meta["youtube_preview"] = _preview(s)
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
    thumbnail(s, artist)

    ass = s.out / "main.ass"
    write_ass_main(s, rows, ass, artist)
    print("본편 영상 만드는 중", flush=True)
    render_main(s, src, ass)

    if not a.no_short:
        start, end = short_window(s, rows, float(cfg.get("short_seconds", 40)))
        ass_s = s.out / "short.ass"
        write_ass_short(s, rows, ass_s, artist, start, end)
        print(f"쇼츠 만드는 중 ({start:.1f}s~{end:.1f}s)", flush=True)
        render_short(s, src, ass_s, start, end)
        s.meta["short_window"] = [round(start, 2), round(end, 2)]

    s.meta["produced"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    s.meta["youtube_preview"] = _preview(s)
    s.save()
    write_readme(s)
    print("완료", s.out, flush=True)


def cmd_publish(a) -> None:
    """out/에 있는 영상(main.mp4, short.mp4, thumb.jpg)을 유튜브에 올린다."""
    from . import youtube

    cfg = songmod.config()
    artist = cfg.get("artist", "")
    s = Song(a.slug)
    main, short, thumb = s.out / "main.mp4", s.out / "short.mp4", s.out / "thumb.jpg"
    if not main.exists():
        sys.exit(f"{s.slug}: 영상이 없습니다. 먼저 영상을 만들어 주세요.")
    if not youtube.ready():
        sys.exit("유튜브 키가 없습니다. SETUP.md를 보세요.")
    yt = s.meta.setdefault("youtube", {})
    pv = youtube.preview(s, cfg)
    s.meta["youtube_preview"] = pv
    title, tags = pv["title"], pv["tags"]
    if not yt.get("main"):
        print("유튜브 본편 업로드:", title, flush=True)
        yt["main"] = youtube.upload(main, title=title, desc=pv["description"],
                                    tags=tags, privacy=cfg["privacy"], thumb=thumb)
        s.save()
        for name in youtube.playlist_names(cfg, s.meta):
            try:
                youtube.add_to_playlist(yt["main"], name, cfg["privacy"])
            except Exception as e:  # 재생목록은 실패해도 업로드는 유지
                print(f"  재생목록 '{name}' 추가 실패: {e}", flush=True)
    if short.exists() and not yt.get("short"):
        print("유튜브 쇼츠 업로드:", pv["shorts_title"], flush=True)
        yt["short"] = youtube.upload(short, title=pv["shorts_title"],
                                     desc=youtube.description(s, artist, main_id=yt.get("main"), short=True),
                                     tags=tags, privacy=cfg["privacy"])
    s.meta["uploaded"] = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M")
    s.save()
    write_readme(s)
    print("완료", yt, flush=True)


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


def cmd_learn(a) -> None:
    from .learn import learn_all
    paths = learn_all(a.names or None, force=a.force)
    _output("count", str(len(paths)))


def main() -> None:
    p = argparse.ArgumentParser(prog="mufac")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new", help="새 곡 가사와 Suno 문구 만들기")
    n.add_argument("--hook", default="")
    n.add_argument("--idea", default="")
    n.add_argument("--theme", default="")
    n.add_argument("--vocal", default="")
    n.add_argument("--style", default="")
    n.add_argument("--classic", default="auto", help="auto, none, 또는 클래식 곡 id")
    n.add_argument("--req", default="", help="대시보드가 붙이는 요청 번호")
    n.set_defaults(func=cmd_new)

    ph = sub.add_parser("photo", help="사진 다시 만들기")
    ph.add_argument("slug")
    ph.add_argument("--pick", type=int, default=None)
    ph.add_argument("--prompt", default="")
    ph.set_defaults(func=cmd_photo)

    pr = sub.add_parser("produce", help="자막 영상과 썸네일 만들기")
    pr.add_argument("slug")
    pr.add_argument("--no-short", action="store_true")
    pr.set_defaults(func=cmd_produce)

    pu = sub.add_parser("publish", help="만든 영상을 유튜브에 올리기")
    pu.add_argument("slug")
    pu.set_defaults(func=cmd_publish)

    c = sub.add_parser("check", help="유튜브 연결 확인")
    c.set_defaults(func=cmd_check)

    l = sub.add_parser("learn", help="레퍼런스 아티스트의 노랫말 프로필 만들기")
    l.add_argument("names", nargs="*", help="비우면 config.yaml의 lyric_reference 전부")
    l.add_argument("--force", action="store_true", help="이미 있는 프로필도 다시 쓴다")
    l.set_defaults(func=cmd_learn)

    a = p.parse_args()
    a.func(a)


if __name__ == "__main__":
    main()
