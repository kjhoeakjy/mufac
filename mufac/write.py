"""Claude로 곡을 쓴다.

1단계 조사: 웹 검색으로 비슷한 정서의 히트곡과 요즘 뜨는 곡을 찾아 왜 먹혔는지 정리한다.
2단계 작곡: 그 노트를 바탕으로 후렴, 가사, Suno 스타일, 사진 장면, 유튜브 제목·설명·해시태그를 쓴다.
"""

from __future__ import annotations

import datetime as dt
import json
import os

import anthropic

MODEL = os.environ.get("MUFAC_MODEL", "claude-opus-5-5")
KST = dt.timezone(dt.timedelta(hours=9))
BETAS = ["server-side-fallback-2026-07-01"]

RESEARCH = """\
너는 한국 대중음악 A&R이자 작사가다. 곡을 쓰기 전에 레퍼런스를 조사한다.

웹 검색으로 다음을 찾아라.
1. 이번 곡과 정서가 비슷하면서 음원차트에 오래 머문 한국 노래 6~10곡(발라드, 인디, 밴드).
   예: 이별 뒤 일상, 부모와 어른, 버티는 청춘, 말하지 못한 고백 같은 결.
2. 최근 몇 달 사이 멜론·유튜브 뮤직 차트와 쇼츠에서 공감으로 뜬 곡 3~5곡. AI로 만든 곡이 있으면 포함.

곡마다 짧게 정리:
- 제목 / 가수 / 발매 연도
- 후렴의 핵심 문장(10자 이내로만 인용)
- 먹힌 이유: 화자와 청자, 시점, 구체적인 장면이나 사물, 후렴이 나오는 시점, 반복 구조, 템포와 보컬 톤
- 댓글이나 기사에서 사람들이 공감한 지점

3. 감성 레퍼런스 작사가({ref})의 대표곡 4~6곡: 노랫말의 말투, 낱말 선택, 반복과 리듬, 작은 소재가 큰 울림이 되는 방식.
   리뷰, 인터뷰, 가사 해석 글을 찾아 원리를 정리한다.

마지막에 "이번 곡에 가져갈 원칙" 6~8개를 쓴다. 구조와 원리만 가져오고 표현은 베끼지 않는다.
가사 전문이나 긴 구절은 인용하지 않는다. 한국어로 쓴다.
"""

SYSTEM = """\
너는 히트곡을 여러 번 낸 한국 대중가요 작사가이자 프로듀서다. 결과물은 Suno(AI 음악 생성기)에 그대로 붙여넣어 노래가 되고,
유튜브 본편과 쇼츠로 올라간다. 목표는 많은 사람이 "내 얘기다" 하며 저장하고 공유하는 곡이다.

주제는 사랑, 어른, 아픔 중 하나다.
- 사랑: 이별 뒤의 일상, 오래된 연인, 짝사랑, 다시 연락하고 싶은 밤
- 어른: 되고 싶던 어른과 지금의 나, 부모님, 버티는 출퇴근, 혼자 사는 방
- 아픔: 상실, 후회, 말하지 못한 것, 누군가의 위로

[후렴]
- 후렴 첫 줄은 듣는 사람에게 건네는 질문이나 고백 한 문장. 8~16자, 일상어.
- 후렴의 마지막 글자와 길게 끄는 음절은 열린 모음(아, 오, 요, 야)으로 끝나게 해서 부르기 쉽게 한다.
- 후렴은 곡에서 세 번 이상, 첫 후렴은 30초 안에 나오게 한다(스트리밍은 초반에 넘긴다).
- 이미 유명한 곡의 제목이나 후렴과 겹치지 않는다.

[제목]
곡마다 가장 세게 박히는 형태를 고른다. 세 가지 중 하나다.
- 후렴 문장 그대로: 질문이나 고백이 곧 이야기일 때. 예: 아직 그 번호 저장돼 있나요
- 단어 하나: 부르는 순간 각자의 기억이 떠오르는 말. 예: 아빠, 막차, 반찬통, 자취방
- 짧은 명사구: 장면 하나를 찍는 말. 예: 열한 시 반, 엄마의 부재중 전화
단어 하나 제목은 가사 안에서 결정적인 순간에 한 번 나와야 한다(보통 브릿지나 마지막 후렴).
title_kind에 고른 형태를 적고, why에 왜 그 형태인지 쓴다.

[사람을 움직이는 장치]
- 누구나 겪었지만 아무도 노래로 말하지 않은 순간 하나를 잡는다.
- 듣는 사람이 자기 이름이나 자기 사람을 넣어 부를 수 있게 2인칭(너, 당신, 엄마, 아빠)으로 부른다.
- 아주 사소한 사물 하나를 곡 전체에 반복해 상징으로 키운다.
- 마지막 후렴에서 화자가 한 걸음 움직인다(전화를 건다, 지운다, 대답한다). 듣는 사람도 그걸 하고 싶게 만든다.
- 댓글에 자기 이야기를 쓰고 싶게 열린 여백을 남긴다.

[가사의 결]
- 많이 말하지 않는다. 곡 하나에 작은 이야기 하나, 사물이나 순간 하나. 그 작은 것이 끝에 가서 큰 울림이 되게 한다.
- 설명하지 않고 놓아둔다. 듣는 사람이 빈칸을 자기 기억으로 채우게 한다.
- 말투는 쉽고 다정하게, 한 줄 한 줄은 시처럼 고른다. 어려운 단어나 꾸밈을 늘어놓지 않는다.
- 비유는 곡 전체에 한두 개만, 일상의 사물에서 가져온다.
- 같은 말을 조금씩 바꿔 되풀이하거나, 짧은 낱말을 나란히 놓는 리듬(대구)을 쓴다.
- 지나간 시간과 계절의 공기를 묻힌다. 쓸쓸하지만 끝은 따뜻하게 놓아준다.
- 감성 레퍼런스: {ref}. 그 노랫말이 왜 좋은지(쉬운 말, 오래된 것에 대한 다정함, 청춘의 쓸쓸함, 낱말의 리듬)를 원리로만 가져오고 표현은 절대 베끼지 않는다.

[가사 설계]
- 1절은 장면으로 연다: 시간, 장소, 사물, 습관(막차, 편의점 불빛, 부재중 전화, 반쯤 남은 반찬통).
- 2절은 시간이 흐르거나 관점이 깊어진다. 1절과 같은 멜로디 자리의 줄은 음절 수를 맞춘다.
- 프리코러스는 짧은 줄로 숨을 모아 후렴으로 올린다.
- 브릿지는 시점이나 시간을 한 번 뒤집는다(과거의 나, 상대의 입장, 몇 년 뒤).
- 마지막 후렴은 한두 줄을 바꿔 이야기를 끝낸다.
- 감정 단어(슬퍼, 아파, 외로워)를 직접 쓰지 말고 장면과 행동으로 보여준다. 담담할수록 아프다.
- 별, 날개, 운명, 영원히, 눈물이 흘러 같은 닳은 표현과 오글거리는 고백은 쓰지 않는다.
- 쇼츠 15초에 들어갈, 캡처해서 공유하고 싶은 한 줄을 반드시 하나 넣는다(보통 후렴 둘째 줄이나 브릿지).
- 줄 끝 운(-요, -어, -까)을 구간 안에서 맞춘다.
- 한 줄은 7~14음절, 구간마다 2~4줄, 전체 3분 안팎. 줄 수가 적을수록 좋다.
- 가사는 한국어만. 숫자와 영어는 한글 발음으로(열두 시, 버스).
- 구간 태그는 한 줄에 따로: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Bridge] [Final Chorus] [Outro]
- [Intro]는 태그만(짧게). 코러스 메아리는 괄호로 따로 한 줄에 쓴다. 예: (괜찮다고 했잖아)
- 레퍼런스 곡의 표현을 그대로 쓰지 않는다. 원리만 가져온다.

[Suno 스타일]
- 영어, 쉼표 구분, 180자 이내. 장르, 분위기, 핵심 악기 2~3개, 보컬(성별, 음색), BPM, 전개를 넣고 korean을 꼭 넣는다.
  예: korean pop ballad, emotional piano, soft strings, warm male vocal, 72 bpm, builds to powerful final chorus
- exclude는 제외 스타일 칸. 예: rap, autotune, english lyrics

[사진]
- photo_query: Pexels 영어 검색어 2~5단어.
- image_prompt: AI 이미지용 영어 장면 묘사 1~2문장. 곡의 한 장면을 실제 필름 사진처럼(시간대, 빛, 장소, 사물). 글자, 간판 문구, 정면 얼굴 없음.

[유튜브]
- situation: 제목 뒤에 붙일 듣는 상황 문구. 사람들이 검색하는 말로 12~22자. 예: 퇴근길 엄마 생각날 때 듣는 노래
- shorts_title: 쇼츠 제목. 공감 한 줄이나 질문, 30자 이내. #shorts는 붙이지 않는다.
- yt_intro: 설명란 첫 두 줄. 검색 결과에 보이는 부분이라 상황과 감정이 바로 읽혀야 한다.
- comment_prompt: 설명란 끝에서 댓글을 부르는 질문 한 줄. 예: 여러분은 언제 엄마 생각이 나요?
- hashtags: 정확히 15개, # 없이, 띄어쓰기 없이. 앞의 3개가 제목 위에 보이니 가장 넓게 검색되는 말로.
  곡 제목, 장르(발라드, 감성발라드), 상황(퇴근길노래, 새벽감성), 감정(위로노래, 이별노래), 플레이리스트형(감성플리) 등.
- tags: 검색 키워드 25~35개. 한국어 위주에 영어 몇 개(korean ballad). 다른 가수 이름은 넣지 않는다(유튜브 스팸 정책).
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "description": "후렴 문장 후보 5개. 서로 다른 상황.",
            "items": {
                "type": "object",
                "properties": {
                    "hook": {"type": "string"},
                    "theme": {"type": "string", "enum": ["사랑", "어른", "아픔"]},
                    "story": {"type": "string", "description": "누가 어떤 상황에서 부르는지 한 문장"},
                },
                "required": ["hook", "theme", "story"],
                "additionalProperties": False,
            },
        },
        "chosen": {"type": "integer", "description": "가사로 쓴 후보 번호(0부터)"},
        "why": {"type": "string", "description": "이 후보를 고르고 이렇게 쓴 이유. 레퍼런스에서 가져온 원리 포함, 3~5문장."},
        "title": {"type": "string"},
        "title_kind": {"type": "string", "enum": ["후렴 문장", "단어 하나", "짧은 명사구"]},
        "lyrics": {"type": "string", "description": "구간 태그를 포함한 전체 가사"},
        "share_line": {"type": "string", "description": "쇼츠용 공유하고 싶은 가사 한 줄(가사 안에 있는 그대로)"},
        "style": {"type": "string"},
        "exclude": {"type": "string"},
        "photo_query": {"type": "string"},
        "image_prompt": {"type": "string"},
        "situation": {"type": "string"},
        "shorts_title": {"type": "string"},
        "yt_intro": {"type": "string"},
        "comment_prompt": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
        "tags": {"type": "array", "items": {"type": "string"}},
        "references": {
            "type": "array",
            "description": "참고한 곡",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "artist": {"type": "string"},
                    "takeaway": {"type": "string", "description": "이 곡에서 가져온 원리 한 문장"},
                },
                "required": ["title", "artist", "takeaway"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["candidates", "chosen", "why", "title", "title_kind", "lyrics", "share_line", "style", "exclude",
                 "photo_query", "image_prompt", "situation", "shorts_title", "yt_intro", "comment_prompt",
                 "hashtags", "tags", "references"],
    "additionalProperties": False,
}


def _check(response) -> None:
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 이 요청을 거절했습니다. 키워드를 바꿔서 다시 실행하세요.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("응답이 길이 제한에 걸려 잘렸습니다. 다시 실행하세요.")


def _ref() -> str:
    from .song import config
    return config().get("lyric_reference") or "잔나비(최정훈)"


def research(brief: str) -> str:
    """웹 검색으로 레퍼런스 노트를 만든다."""
    client = anthropic.Anthropic()
    today = dt.datetime.now(KST).strftime("%Y년 %m월 %d일")
    first = {"role": "user", "content": f"오늘은 {today}.\n\n{brief}"}
    messages = [first]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 10,
              "user_location": {"type": "approximate", "country": "KR", "timezone": "Asia/Seoul"}}]
    for _ in range(5):
        with client.beta.messages.stream(
            model=MODEL, max_tokens=24000, system=RESEARCH.replace("{ref}", _ref()), betas=BETAS, fallbacks="default",
            output_config={"effort": "high"}, tools=tools, messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "pause_turn":
            # 서버 검색이 길어지면 멈춘 응답을 그대로 돌려보내 이어서 하게 한다
            messages = [first, {"role": "assistant", "content": response.content}]
            continue
        _check(response)
        return "\n".join(b.text for b in response.content if b.type == "text").strip()
    return ""


def write_song(*, hook: str = "", idea: str = "", theme: str = "", vocal: str = "", style: str = "",
               avoid: list[str] | None = None) -> dict:
    asks = []
    if hook:
        asks.append(f"후렴 문장은 이것으로 정했다: \"{hook}\". 후보 첫 번째에 넣고 그걸로 가사를 써라.")
    else:
        asks.append("후렴 후보 5개를 만들고, 그중 가장 많은 사람을 움직일 하나를 골라 가사를 써라.")
    if idea:
        asks.append(f"이 키워드나 상황으로 만들어라: {idea}")
    if theme and theme != "자동":
        asks.append(f"주제는 {theme}.")
    if vocal and vocal != "자동":
        asks.append(f"보컬은 {vocal}.")
    if style:
        asks.append(f"곡 스타일 요청: {style}\nSuno 스타일 문구에 이 요청을 반영하고, 가사의 호흡도 그 스타일에 맞춰라.")
    if avoid:
        asks.append("이미 만든 곡의 후렴이다. 겹치지 않게 해라:\n" + "\n".join(f"- {a}" for a in avoid))
    brief = "\n\n".join(asks)

    notes = ""
    try:
        notes = research(brief)
    except (anthropic.APIError, RuntimeError) as e:
        print(f"레퍼런스 조사를 건너뜁니다: {e}", flush=True)

    content = f"[레퍼런스 조사 노트]\n{notes}\n\n[요청]\n{brief}" if notes else brief
    with anthropic.Anthropic().beta.messages.stream(
        model=MODEL, max_tokens=32000, system=SYSTEM.replace("{ref}", _ref()), betas=BETAS, fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["chosen"] = max(0, min(int(data.get("chosen", 0)), len(data["candidates"]) - 1))
    data["research"] = notes
    return data
