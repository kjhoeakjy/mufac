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

    lines += ["## 1. Suno에 붙여넣기", "",
              "[Suno](https://suno.com/create)에서 Custom 모드를 켜고 아래를 칸마다 붙여넣는다. 곡 이미지는 cover.jpg.", ""]
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


def _work_dir():
    from pathlib import Path
    d = Path(os.environ.get("MUFAC_WORK", ".mufac-work"))
    d.mkdir(exist_ok=True)
    return d


def cmd_new(a) -> None:
    """--stage all(기본) | plan | write | finish.
    Actions에서는 세 단계를 따로 실행해 진행률을 보여 준다. 단계 사이 상태는 .mufac-work/에 JSON으로 둔다."""
    import json
    import time
    from concurrent.futures import ThreadPoolExecutor

    from .photo import fetch
    from .write import compose, prepare, safe_polish, took

    stage = a.stage or "all"
    wd = _work_dir()
    t_all = time.time()

    if stage in ("all", "plan"):
        done = songmod.all_songs()
        avoid = [x.meta.get("hook", "") for x in done][-40:]
        avoid_styles = [x.meta.get("style", "") for x in done][-12:]
        work = prepare(hook=a.hook, idea=a.idea, theme=a.theme, vocal=a.vocal, style=a.style,
                       avoid=avoid, avoid_styles=avoid_styles, title=a.title, content=a.content, genre=a.genre)
        work["request"] = {k: v for k, v in {"id": a.req, "title": a.title, "idea": a.idea, "content": a.content,
                                             "genre": a.genre, "style": a.style}.items() if v and v != "자동"}
        (wd / "plan.json").write_text(json.dumps(work, ensure_ascii=False), encoding="utf-8")
        if stage == "plan":
            return

    if stage in ("all", "write"):
        work = json.loads((wd / "plan.json").read_text(encoding="utf-8"))
        data = compose(work)
        data["request"] = work.get("request", {})
        (wd / "song.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        if stage == "write":
            return

    data = json.loads((wd / "song.json").read_text(encoding="utf-8"))
    s = Song(songmod.new_slug())
    pick = data["candidates"][data["chosen"]]
    s.meta = {
        "title": data["title"],
        "hook": pick["hook"],
        "theme": pick["theme"],
        "story": pick["story"],
        "created": dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "request": data.get("request", {}),
        "style": data["style"],
        "exclude": data["exclude"],
        "photo_query": data["photo_query"],
        "image_prompt": data["image_prompt"],
        "title_kind": data.get("title_kind", ""),
        "tempo": data.get("tempo", ""),
        "arc": data.get("arc", ""),
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
        "lyrics_draft": data.get("lyrics_draft", ""),
        "polish": data.get("polish", []),
    }
    s.save()
    if data.get("research"):
        (s.dir / "research.md").write_text(f"# 레퍼런스 조사\n\n{data['research']}\n", encoding="utf-8")

    # 가사 검수와 사진은 서로 상관없으니 동시에 한다 (원곡 음원은 만들지 않는다: Suno가 음원 지문 검사로 막는다)
    def photo() -> None:
        t0 = time.time()
        try:
            fetch(s)
            took("사진", t0)
        except Exception as e:  # 사진이 없어도 곡 폴더는 남긴다
            print(f"사진을 못 가져왔습니다: {e}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_polish = pool.submit(safe_polish, data, (data.get("request") or {}).get("title", ""))
        pool.submit(photo)
        data = f_polish.result()
    for k in ("title", "lyrics", "lyrics_draft", "polish", "share_line"):
        if k in data:
            s.meta[k] = data[k]
    s.meta["youtube_preview"] = _preview(s)
    s.save()
    write_readme(s)
    took("마무리" if stage == "finish" else "전체", t_all)
    print(s.slug)
    _output("slug", s.slug)
    _output("title", s.meta["title"])


def cmd_refresh(a) -> None:
    """사용자가 대시보드에서 제목·가사를 고친 뒤: 유튜브 글을 다시 쓰고 미리보기·README를 갱신한다.
    가사가 바뀌었으면 자막 타이밍(timing.lrc)을 지워 다음 영상 제작 때 다시 맞추게 한다."""
    from .write import refresh_meta

    s = Song(a.slug)
    m = s.meta
    try:
        new = refresh_meta(m)
        ym = m.setdefault("youtube_meta", {})
        for k_src, k_dst in (("situation", "situation"), ("shorts_title", "shorts_title"), ("yt_intro", "intro"),
                             ("comment_prompt", "comment_prompt"), ("hashtags", "hashtags")):
            ym[k_dst] = new[k_src]
        m["tags"], m["story"] = new["tags"], new["story"]
        if new["share_line"].strip() and new["share_line"].strip() in m.get("lyrics", ""):
            m["share_line"] = new["share_line"].strip()
    except Exception as e:  # 글을 못 받아도 제목·가사 반영은 한다
        print(f"유튜브 글을 다시 쓰지 못했습니다: {e}", file=sys.stderr)
    if a.lyrics_changed and s.timing_path.exists():
        s.timing_path.unlink()
        print("가사가 바뀌어 자막 타이밍을 지웠습니다. 영상은 다시 만들어야 합니다.", flush=True)
    m["youtube_preview"] = _preview(s)
    m["youtube_preview_edited"] = False  # 직접 고친 글이 있었어도 새 제목·가사 기준으로 다시 쓴다
    s.save()
    write_readme(s)
    print(s.slug)


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
    if s.meta.get("youtube_preview_edited") and s.meta.get("youtube_preview"):
        pv = s.meta["youtube_preview"]  # 대시보드에서 직접 고친 글을 그대로 쓴다
        pv.setdefault("playlists", youtube.playlist_names(cfg, s.meta))
        pv.setdefault("privacy", cfg.get("privacy", "private"))
    else:
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
    n.add_argument("--req", default="", help="대시보드가 붙이는 요청 번호")
    n.add_argument("--title", default="", help="제목을 직접 정하려면")
    n.add_argument("--content", default="", help="노래에 담을 내용")
    n.add_argument("--genre", default="", help="장르 (트로트, 인디밴드, 발라드, 락, OST, 팝 ...)")
    n.add_argument("--stage", default="all", choices=["all", "plan", "write", "finish"],
                   help="단계별 실행 (Actions가 진행률을 보여 주려고 셋으로 나눠 부른다)")
    n.set_defaults(func=cmd_new)

    rf = sub.add_parser("refresh", help="제목·가사를 고친 뒤 유튜브 글과 미리보기 다시 만들기")
    rf.add_argument("slug")
    rf.add_argument("--lyrics-changed", action="store_true", help="가사가 바뀌었으면 자막 타이밍을 지운다")
    rf.set_defaults(func=cmd_refresh)

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
