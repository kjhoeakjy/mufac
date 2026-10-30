"""Claude로 후렴, 가사, Suno 스타일, 사진 검색어를 쓴다."""

from __future__ import annotations

import json
import os

import anthropic

MODEL = os.environ.get("MUFAC_MODEL", "claude-opus-5-5")

SYSTEM = """\
너는 한국 대중가요 작사가이자 프로듀서다. 음원 차트에 오래 머무는 발라드, 인디 팝, 밴드 곡을 쓴다.
결과물은 Suno(AI 음악 생성기)에 그대로 붙여넣어 노래로 만든다.

주제는 사랑, 어른, 아픔 중 하나다.
- 사랑: 이별 뒤, 오래된 연인, 짝사랑, 다시 연락하고 싶은 밤
- 어른: 되고 싶던 어른과 지금의 나, 부모님, 버티는 출퇴근, 혼자 사는 방
- 아픔: 상실, 후회, 말하지 못한 것, 누군가의 위로

좋은 후렴 문장의 조건
- 듣는 사람에게 건네는 질문이나 고백 한 문장. 들으면 자기 얘기 같아야 한다.
- 일상어로 짧게(띄어쓰기 포함 8~16자). 처음 들어도 따라 부를 수 있어야 한다.
- 이미 유명한 노래 제목과 겹치지 않는다. 예: "꿈꾸던 어른이 되었나요"는 이미 있는 곡이라 쓰지 않는다.

가사 규칙
- 벌스는 구체적인 장면으로 시작한다: 시간, 장소, 물건, 습관(막차, 편의점 불빛, 엄마의 부재중 전화, 반쯤 남은 칫솔).
- 별, 날개, 운명, 영원히, 눈물이 흘러 같은 닳은 표현은 쓰지 않는다. 과장된 감탄이나 오글거리는 고백도 쓰지 않는다.
- 감정은 설명하지 말고 장면으로 보여준다. 담담할수록 아프다.
- 후렴 첫 줄은 제목이자 후렴 문장. 후렴은 곡에서 최소 세 번 나온다. 마지막 후렴은 한두 줄을 바꿔 결론을 낸다.
- 브릿지에서 시점이나 시간을 한 번 바꾼다.
- 한 줄은 7~14음절. 구간마다 2~4줄. 전체 길이는 3분 안팎.
- 가사는 한국어만 쓴다. 숫자와 영어 단어는 한글 발음으로 적는다(예: 열두 시, 버스).
- 구간 태그는 Suno 형식으로 따로 한 줄에: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Bridge] [Final Chorus] [Outro]
- [Intro]와 [Outro]는 가사 없이 태그만 두거나 짧은 허밍 한 줄만.

Suno 스타일 규칙
- 영어로, 쉼표로 구분, 180자 이내.
- 장르, 분위기, 핵심 악기 2~3개, 보컬(성별, 음색), 빠르기(BPM), 곡 전개를 넣는다.
- 반드시 korean을 넣는다. 예: korean pop ballad, emotional piano, soft strings, warm male vocal, 72 bpm, builds to powerful final chorus
- exclude는 Suno의 제외 스타일 칸에 넣을 말. 예: rap, autotune, english lyrics

사진 검색어 규칙
- Pexels에서 찾을 영어 검색어 2~5단어.
- 곡의 장면을 담은 실제 풍경이나 사물. 사람 얼굴이 정면으로 나오지 않는 장면.
- 예: empty bus stop night rain, window light empty room, city lights from rooftop
- image_prompt는 AI 이미지 생성기에 줄 영어 장면 묘사 1~2문장. 실제 필름 사진처럼 보이게,
  곡의 한 장면을 구체적으로(시간대, 빛, 장소, 사물). 글자나 간판 문구, 정면 얼굴은 넣지 않는다.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "candidates": {
            "type": "array",
            "description": "후렴 문장 후보 5개. 서로 다른 상황과 주제.",
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
        "chosen": {"type": "integer", "description": "가사로 쓴 후보의 번호(0부터)"},
        "title": {"type": "string", "description": "곡 제목. 보통 후렴 문장 그대로."},
        "lyrics": {"type": "string", "description": "구간 태그를 포함한 전체 가사"},
        "style": {"type": "string"},
        "exclude": {"type": "string"},
        "photo_query": {"type": "string"},
        "image_prompt": {"type": "string"},
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "유튜브 태그 8~12개. 한국어 위주.",
        },
    },
    "required": ["candidates", "chosen", "title", "lyrics", "style", "exclude", "photo_query", "image_prompt", "tags"],
    "additionalProperties": False,
}


def write_song(*, hook: str = "", idea: str = "", theme: str = "", vocal: str = "",
               avoid: list[str] | None = None) -> dict:
    asks = []
    if hook:
        asks.append(f"후렴 문장은 이것으로 정했다: \"{hook}\". 후보 첫 번째에 넣고 그걸로 가사를 써라.")
    else:
        asks.append("후렴 후보 5개를 만들고, 그중 가장 많은 사람을 움직일 하나를 골라 가사를 써라.")
    if idea:
        asks.append(f"요즘 내 생각이나 상황: {idea}")
    if theme and theme != "자동":
        asks.append(f"주제는 {theme}.")
    if vocal and vocal != "자동":
        asks.append(f"보컬은 {vocal}.")
    if avoid:
        asks.append("이미 만든 곡의 후렴이다. 겹치지 않게 해라:\n" + "\n".join(f"- {a}" for a in avoid))

    client = anthropic.Anthropic()
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=SYSTEM,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": "\n\n".join(asks)}],
    ) as stream:
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 이 요청을 거절했습니다. 아이디어 문장을 바꿔서 다시 실행하세요.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("응답이 길이 제한에 걸려 잘렸습니다. 다시 실행하세요.")
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["chosen"] = max(0, min(int(data.get("chosen", 0)), len(data["candidates"]) - 1))
    return data
