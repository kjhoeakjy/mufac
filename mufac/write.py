"""Claude로 곡을 쓴다.

1단계 조사: 웹 검색으로 비슷한 정서의 히트곡과 요즘 뜨는 곡을 찾아 왜 먹혔는지 정리한다.
2단계 작곡: 그 노트를 바탕으로 후렴, 가사, Suno 스타일, 사진 장면, 유튜브 제목·설명·해시태그를 쓴다.
"""

from __future__ import annotations

import datetime as dt
import json
import os

import anthropic

from . import classical

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
- 말투: 줄 끝이 어떻게 끝나는지(반말 -어/-지/-네, 명사로 끊김, 존댓말), 문장이 끊기는 방식, 한 줄의 길이
- 제목의 형태(단어 하나, 명사구, 반말 문장, 존댓말 문장)

3. 감성 레퍼런스({ref}): 아래에 [레퍼런스 작사 프로필]이 붙어 있으면 그것을 읽고, 이번 곡의 정서와 가장 가까운 팀 두셋을 골라
   그 팀의 최근 곡이나 이번 주제와 닿는 곡만 짧게 더 찾는다. 프로필이 없으면 대표곡 4~6곡의 말투, 낱말, 반복과 리듬을 조사해 원리를 정리한다.

4. 클래식 멜로디 위에 쓰는 곡이면 그 원곡의 배경도 검색한다: 작곡 시기와 상황, 헌정 대상, 작곡가가 그때 겪던 일, 초연과 그 뒤의 쓰임,
   사람들이 이 곡을 어떤 자리에서 듣는지. 노래 가사와 설명란에 쓸 수 있는 확인된 사실만 정리한다.

마지막에 "이번 곡에 가져갈 원칙" 6~8개와, 조사한 곡들의 제목 형태와 줄 끝 말투의 분포를 두세 줄로 쓴다. 구조와 원리만 가져오고 표현은 베끼지 않는다.
가사 전문이나 긴 구절은 인용하지 않는다. 한국어로 쓴다.
"""

SYSTEM = """\
너는 히트곡을 여러 번 낸 한국 대중가요 작사가이자 프로듀서다. 결과물은 Suno(AI 음악 생성기)에 그대로 붙여넣어 노래가 되고,
유튜브 본편과 쇼츠로 올라간다. 목표는 많은 사람이 "내 얘기다" 하며 저장하고 공유하는 곡이다.

주제는 사랑, 어른, 아픔 중 하나다.
- 사랑: 이별 뒤의 일상, 오래된 연인, 짝사랑, 다시 연락하고 싶은 밤, 처음 좋아하던 날
- 어른: 되고 싶던 어른과 지금의 나, 부모님, 버티는 출퇴근, 혼자 사는 방, 그래도 괜찮은 하루
- 아픔: 상실, 후회, 말하지 못한 것, 누군가의 위로, 다시 일어나는 아침

[누구나의 이야기]
- 특수한 사건이 아니라 거의 모든 사람이 이미 겪었거나 겪을 일을 쓴다. 입원, 사고, 장례처럼 드문 사건은 쓰지 않는다.
  쓰는 것은 이런 것: 엄마 전화를 귀찮아하다 끊은 저녁, 집에 가는 길, 나이를 먹었다고 처음 느낀 날, 오래 못 본 친구,
  첫사랑의 계절, 월급날, 일요일 밤, 어릴 때 살던 동네, 혼자 먹는 밥, 그래도 내일 또 출근하는 사람.
- 사물은 누구 집에나 있는 것으로. 서류나 전문 용어, 특정 직업만 아는 장면은 피한다.
- 꼭 슬플 필요 없다. 따뜻한 곡, 웃음이 나는 곡, 괜찮다고 등 두드리는 곡, 설레는 곡도 쓴다. 후보 5개 중 적어도 둘은 슬프지 않은 결로.
- 가장 많은 사람이 "내 얘기다" 할 하나를 고른다. 참신함보다 넓이가 먼저다.

[후렴]
- 후렴 첫 줄은 듣는 사람에게 건네는 질문이나 고백 한 문장. 8~16자, 일상어.
- 후렴의 마지막 글자와 길게 끄는 음절은 열린 모음(아, 어, 오, 야)으로 끝나게 해서 부르기 쉽게 한다. 그렇다고 줄마다 "-요"로 끝내지 않는다.
- 후렴은 곡에서 세 번 이상, 첫 후렴은 30초 안에 나오게 한다(스트리밍은 초반에 넘긴다).
- 이미 유명한 곡의 제목이나 후렴과 겹치지 않는다.

[제목]
곡마다 가장 세게 박히는 형태를 고른다. 세 가지 중 하나다.
- 후렴 문장 그대로: 질문이나 고백이 곧 이야기일 때. 반말이나 끊긴 문장이 기본. 예: 잘 지내, 너는 읽기 쉬운 사람
- 단어 하나: 부르는 순간 각자의 기억이 떠오르는 말. 예: 아빠, 막차, 반찬통, 자취방
- 짧은 명사구: 장면 하나를 찍는 말. 예: 열한 시 반, 엄마의 부재중 전화, 그해 여름
사람이 지은 제목처럼 보여야 한다. "-해요/-거예요/-했어요"로 끝나는 제목은 쓰지 않는다. 조사한 히트곡들의 제목 형태 분포를 따른다.
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
- 감성 레퍼런스: {ref}. 밴드 음악의 노랫말이다. 쉬운 말, 입말, 유머와 자조, 능청, 갑자기 진심이 되는 순간, 청춘의 쓸쓸함, 낱말의 리듬.
  아래 [레퍼런스 작사 프로필]의 원리를 가져오되 표현과 특정 낱말은 절대 베끼지 않는다. 곡마다 가장 맞는 팀의 결을 고르고, 여섯 팀을 섞어 뭉개지 않는다.
- 레퍼런스가 밴드이므로 곡 스타일도 밴드 사운드(기타, 베이스, 드럼)가 어울리면 그쪽으로 간다. 발라드만 고집하지 않는다.

[말투]
- 진짜 사람이 쓴 가사처럼 읽혀야 한다. 조사에서 모은 실제 가사의 말투 분포를 따른다.
- 줄 끝을 "-요/-해요/-거예요/-했어요"로 맞추지 않는다. 이런 존댓말 서술이 이어지면 AI가 쓴 티가 난다.
  기본은 반말(-어, -아, -지, -네, -야, -데)과 명사나 부사로 끊기는 줄이다. 존댓말은 곡 전체에서 꼭 필요한 한두 줄만.
- 한 구간 안에서 줄 끝이 모두 같은 어미로 끝나지 않게 한다. 문장을 끝까지 말하지 않고 끊는 줄을 섞는다.
- 설명하는 문장, 요약하는 문장, 교훈을 말하는 문장은 쓰지 않는다. 장면과 말 한마디만 남긴다.
- 매끈하게 정리된 문장보다 사람이 중얼거리듯 흘린 말이 낫다. "그냥", "뭐", "있잖아", "근데" 같은 입말을 한두 번 쓴다.
- 같은 틀의 문장을 세 번 이상 늘어놓지 않는다(나열, 대구의 남용). 되풀이는 후렴에서만.
- 감탄사, 느낌표, 과장된 고백, "소중한", "행복", "영원", "빛나는" 같은 닳은 낱말은 쓰지 않는다.

[가사 설계]
- 1절은 장면으로 연다: 시간, 장소, 사물, 습관(막차, 편의점 불빛, 부재중 전화, 반쯤 남은 반찬통).
- 2절은 시간이 흐르거나 관점이 깊어진다. 1절과 같은 멜로디 자리의 줄은 음절 수를 맞춘다.
- 프리코러스는 짧은 줄로 숨을 모아 후렴으로 올린다.
- 브릿지는 시점이나 시간을 한 번 뒤집는다(과거의 나, 상대의 입장, 몇 년 뒤).
- 마지막 후렴은 한두 줄을 바꿔 이야기를 끝낸다.
- 감정 단어(슬퍼, 아파, 외로워)를 직접 쓰지 말고 장면과 행동으로 보여준다. 담담할수록 아프다.
- 별, 날개, 운명, 영원히, 눈물이 흘러 같은 닳은 표현과 오글거리는 고백은 쓰지 않는다.
- 쇼츠 15초에 들어갈, 캡처해서 공유하고 싶은 한 줄을 반드시 하나 넣는다(보통 후렴 둘째 줄이나 브릿지).
- 줄 끝 소리는 구간 안에서 느슨하게만 맞춘다. 운을 맞추려고 어미를 통일하지 않는다.
- 한 줄은 7~14음절, 구간마다 2~4줄, 전체 3분 안팎. 줄 수가 적을수록 좋다.
- 가사는 한국어만. 숫자와 영어는 한글 발음으로(열두 시, 버스).
- 구간 태그는 한 줄에 따로: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Bridge] [Final Chorus] [Outro]
- [Intro]는 태그만(짧게). 코러스 메아리는 괄호로 따로 한 줄에 쓴다. 예: (괜찮다고 했잖아)
- 레퍼런스 곡의 표현을 그대로 쓰지 않는다. 원리만 가져온다.

[클래식 멜로디 모드]
원곡이 정해진 경우 아래 "멜로디 곡 자료"가 붙는다. 노래는 요즘 곡이 클래식을 인용하는 방식으로 만든다:
전주와 간주에서 원곡 주제가 연주되고, 후렴은 원곡 주제 선율을 그대로 부르며, 절은 새 선율과 자유로운 가사다. 그때는
- 가사는 자료의 가사 계획(구간 순서, 줄 수, 후렴의 줄마다 음절 수)을 그대로 따른다. 이 계획이 위의 구간 규칙보다 우선한다. [Pre-Chorus], [Bridge]는 쓰지 않는다.
- 후렴이 원곡 선율이므로 후렴 가사가 곡의 중심이다. 제목과 핵심 문장은 후렴에 둔다.
- 노래의 이야기와 원곡의 배경이 속으로 이어져야 한다. 겉모습이 닮은 게 아니라, 원곡이 태어난 사정과 이 노래의 화자가 같은 자리에 서 있어야 한다. why에 그 연결을 쓴다.
- classic_note: 유튜브 설명란에 넣을 원곡 이야기 3~4문장. 원곡의 배경 사실 한두 개와 이 노래가 그 위에 선 이유. 담담하게, 과장 없이.
- style에는 원곡의 조성과 빠르기를 지키고 "chorus sings the uploaded classical theme, verses original"을 넣는다.
- 원곡 주제를 꼭 피아노로 연주할 필요 없다. 곡마다 장르와 주제 악기를 다르게 고른다. theme_instrument(piano, guitar, strings, bell)를 정하고
  style에는 그보다 구체적인 악기를 쓴다(일렉 기타 리프, 베이스, 브라스, 신스, 휘파람, 합창, 오르골, 현악 4중주, 아코디언, 하모니카 등).
  장르도 발라드에 묶이지 않는다: 밴드 사운드, 인디 록, 펑크, 디스코 펑크, 포크, 시티팝, 보사노바, 레트로 팝, 왈츠 등. 노래의 사연과 레퍼런스 팀의 결에 맞는 것을 고른다.
  아래 "이미 만든 곡의 스타일"과 겹치지 않게 한다.
- 후렴은 원곡 선율을 그대로 부르므로, 후렴 가사의 호흡(긴 음, 쉼)이 선율과 맞아야 한다.

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
- comment_prompt: 설명란 끝에서 댓글을 부르는 질문 한 줄. 예: 당신은 언제 엄마 생각이 나나요
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
        "classic_note": {"type": "string", "description": "클래식 멜로디 모드가 아니면 빈 문자열"},
        "theme_instrument": {"type": "string", "enum": ["piano", "guitar", "strings", "bell"],
                             "description": "전주·간주에서 원곡 주제를 연주할 악기 느낌. 클래식 모드가 아니면 piano"},
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
                 "hashtags", "tags", "classic_note", "theme_instrument", "references"],
    "additionalProperties": False,
}


def _check(response) -> None:
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 이 요청을 거절했습니다. 키워드를 바꿔서 다시 실행하세요.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("응답이 길이 제한에 걸려 잘렸습니다. 다시 실행하세요.")


def _ref() -> str:
    from .learn import references
    return ", ".join(references())


def _system(base: str) -> str:
    """시스템 프롬프트에 레퍼런스 이름과, 있으면 작사 프로필을 붙인다."""
    from .learn import profiles_text
    text = base.replace("{ref}", _ref())
    profiles = profiles_text()
    if profiles:
        text += "\n\n[레퍼런스 작사 프로필]\n" + profiles
    return text


CHOOSE = """\
너는 음악학자이자 프로듀서다. 새로 쓸 노래의 사연에 가장 깊이 이어지는 클래식 원곡을 하나 고른다.
겉으로 분위기가 비슷한 곡이 아니라, 원곡이 태어난 사정(누구를 위해, 어떤 시기에, 무엇을 잃거나 바라며 썼는지)과
이 노래의 화자가 같은 자리에 서는 곡을 고른다. 모두 저작권이 끝난 곡이다.
JSON만 답한다: {"id": "<곡 id>", "reason": "<왜 이 곡인지 4~6문장, 원곡 배경의 구체적 사실을 들어서>"}
"""


def choose_classic(brief: str) -> dict:
    client = anthropic.Anthropic()
    schema = {"type": "object", "properties": {"id": {"type": "string", "enum": [p["id"] for p in classical.catalog()]},
                                                 "reason": {"type": "string"}},
              "required": ["id", "reason"], "additionalProperties": False}
    with client.beta.messages.stream(
        model=MODEL, max_tokens=8000, system=CHOOSE, betas=BETAS, fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": f"[노래 사연]\n{brief}\n\n[고를 수 있는 원곡]\n{classical.catalogue()}"}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    return json.loads(next(b.text for b in response.content if b.type == "text"))


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
            model=MODEL, max_tokens=24000, system=_system(RESEARCH), betas=BETAS, fallbacks="default",
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
               classic: str = "", avoid: list[str] | None = None, avoid_styles: list[str] | None = None) -> dict:
    """classic: '' 없음, 'auto' 의미로 고르기, 또는 classical.LIBRARY의 id."""
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
    if avoid_styles:
        asks.append("이미 만든 곡의 스타일이다. 장르와 악기가 겹치지 않게 해라:\n" + "\n".join(f"- {a}" for a in avoid_styles))
    brief = "\n\n".join(asks)

    piece, reason = None, ""
    if classic == "auto":
        pick = choose_classic(brief)
        piece, reason = classical.get(pick["id"]), pick["reason"]
    elif classic and classic != "none":
        piece = classical.get(classic)
        reason = "직접 고른 원곡"
    if piece:
        brief += (f"\n\n[멜로디 곡]\n이 노래는 {piece['name']}({piece['composer']}, {piece['year']}) 선율 위에 쓴다. "
                  f"고른 이유: {reason}")

    notes = ""
    try:
        notes = research(brief)
    except (anthropic.APIError, RuntimeError) as e:
        print(f"레퍼런스 조사를 건너뜁니다: {e}", flush=True)

    parts = []
    if notes:
        parts.append(f"[레퍼런스 조사 노트]\n{notes}")
    if piece:
        parts.append(f"[멜로디 곡 자료]\n{piece['story'].strip()}\n\n{classical.lyric_plan(piece['id'])}")
    parts.append(f"[요청]\n{brief}")
    content = "\n\n".join(parts)
    with anthropic.Anthropic().beta.messages.stream(
        model=MODEL, max_tokens=32000, system=_system(SYSTEM), betas=BETAS, fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["chosen"] = max(0, min(int(data.get("chosen", 0)), len(data["candidates"]) - 1))
    data["research"] = notes
    if piece:
        data["classic"] = {"id": piece["id"], "name": piece["name"], "composer": piece["composer"],
                           "year": piece["year"], "reason": reason, "note": data.get("classic_note", ""),
                           "instrument": data.get("theme_instrument", "piano")}
    return data
