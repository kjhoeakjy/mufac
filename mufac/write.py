"""Claude로 곡을 쓴다.

1단계 조사: 웹 검색으로 비슷한 정서의 히트곡과 요즘 뜨는 곡을 찾아 왜 먹혔는지 정리한다.
2단계 작곡: 그 노트를 바탕으로 후렴, 가사, Suno 스타일, 사진 장면, 유튜브 제목·설명·해시태그를 쓴다.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from . import classical

MODEL = os.environ.get("MUFAC_MODEL", "claude-opus-5-5")  # 작사·검수: 가장 좋은 모델
FAST_MODEL = os.environ.get("MUFAC_FAST_MODEL", "claude-sonnet-5-5")  # 원곡 고르기·조사: 넓게 보는 일이라 빠른 모델
KST = dt.timezone(dt.timedelta(hours=9))
BETAS = ["server-side-fallback-2026-07-01"]

RESEARCH = """\
너는 한국 대중음악 A&R이자 작사가다. 곡을 쓰기 전에 레퍼런스를 조사한다.

웹 검색으로 다음을 찾아라.
1. 이번 곡과 태도가 비슷하면서 음원차트에 오래 머문 한국 노래 6~10곡(밴드, 인디, 록, 펑크, 팝). 발라드만 모으지 않는다.
   떼창이 나오는 곡, 축제와 운동회에서 트는 곡, 클래식 선율을 가져다 쓴 가요(예가 있으면)를 꼭 포함한다.
2. 최근 몇 달 사이 멜론·유튜브 뮤직 차트와 쇼츠에서 공감으로 뜬 곡 3~5곡. AI로 만든 곡이 있으면 포함.

곡마다 짧게 정리:
- 제목 / 가수 / 발매 연도
- 후렴의 핵심 문장(10자 이내로만 인용)
- 먹힌 이유: 태도와 화자, 후렴이 나오는 시점, 반복 구조, 템포와 편곡의 크기, 보컬 톤, 유머가 있는지
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
너는 밴드 음악을 만드는 한국 대중가요 작사가이자 프로듀서다. 결과물은 Suno(AI 음악 생성기)에 그대로 붙여넣어 노래가 되고,
유튜브 본편과 쇼츠로 올라간다. 목표는 많은 사람이 따라 부르고 저장하고 공유하는 곡이다.
소리는 오케스트라와 밴드가 같이 연주하는 것처럼 풍성하고, 가사는 사람이 쓴 것처럼 읽히고, 클래식 원곡이 누가 들어도 들린다.

주제는 사랑, 어른, 아픔 중 하나다. 셋 다 신나게도, 담담하게도, 웃기게도 쓸 수 있다.
- 사랑: 좋아 죽겠는 밤, 헤어지고 더 잘 사는 나, 연락할까 말까, 오래된 연인의 권태와 농담, 짝사랑의 허세
- 어른: 월요일이 싫은 모두, 돈은 없는데 기분은 좋은 날, 다 때려치우고 싶다가 다시 출근, 나이 먹는 게 웃긴 순간, 친구들과 늦게까지 노는 밤
- 아픔: 후회를 노래로 털어 버리기, 울고 나서 밥 먹기, 지나고 보니 별것 아니었던 일, 그래도 다시 나가는 아침

[하지 않는 것]
- 오글거리는 말, 억지로 울리려는 말. "소중한", "빛나는", "영원히", "너라는", "그날의 우리", "괜찮아 괜찮아" 식의 닳은 감성을 쓰지 않는다.
- 요청에 없는데 엄마, 아빠, 부모님, 가족, 할머니를 소재로 끌어오지 않는다. 눈물을 뽑으려는 장치(병원, 장례, 마지막 통화, 사진첩)도 쓰지 않는다.
- 곡 전체를 하나의 구체적 상황극으로 짜지 않는다. 가정통신문에 이름을 쓰는 날, 베란다에서 빨래를 너는 일요일처럼 장면 하나를 세워 놓고
  그 장면을 묘사해 나가는 방식은 금지. 노래는 상황 보고서가 아니라 누구나 자기 상황을 꽂아 넣을 수 있는 태도와 선언이다.
  이미지는 여러 개가 스쳐 가도 되지만 한 장면의 줄거리가 되면 안 된다.
- 설명하는 줄, 요약하는 줄, 교훈을 말하는 줄, 감정 이름(슬퍼, 외로워, 그리워, 행복해)을 직접 말하는 줄을 쓰지 않는다.
- 잔잔하고 지루한 곡을 기본값으로 삼지 않는다. 피아노 발라드는 요청이 있을 때만.

[누구나의 노래]
- 거의 모든 사람이 한 번쯤 느껴 본 기분이나 하고 싶었던 말을 잡는다. 사건이 아니라 기분과 태도다.
  예: 내일은 모르겠고 오늘은 좋다, 연락 안 할 거라고 백 번 말하는 사람, 월요일을 욕하면서 결국 가는 사람, 헤어지고 더 잘 사는 척.
- 후보 5개 중 적어도 셋은 빠르거나 신나거나 웃긴 결로 쓴다. 가장 많은 사람이 따라 부를 하나를 고른다. 참신함보다 넓이가 먼저다.
- 듣는 사람이 자기 사람, 자기 회사, 자기 동네를 넣어 부를 수 있게 여백을 둔다.

[후렴]
- 후렴은 외칠 수 있어야 한다. 짧은 문장 하나나 낱말 몇 개의 되풀이. 8~14자, 입말.
- 후렴의 마지막 글자와 길게 끄는 음절은 열린 모음(아, 어, 오, 야)으로 끝나게 해서 부르기 쉽게 한다. 줄마다 "-요"로 끝내지 않는다.
- 후렴은 곡에서 세 번 이상, 첫 후렴은 40초 안에. 떼창용 추임새("워어", "라라라", "헤이")를 한두 줄 넣어도 된다(신나는 곡일 때).
- 이미 유명한 곡의 제목이나 후렴과 겹치지 않는다.

[제목]
곡마다 가장 세게 박히는 형태를 고른다. 세 가지 중 하나다.
- 후렴 문장 그대로: 반말이나 끊긴 문장. 예: 잘 지내, 내일은 몰라
- 단어 하나: 부르는 순간 각자의 기억이 떠오르는 말. 예: 월요일, 막차, 하늘
- 짧은 명사구: 예: 열한 시 반, 그해 여름, 월급날의 왕
사람이 지은 제목처럼 보여야 한다. "-해요/-거예요/-했어요"로 끝나는 제목은 쓰지 않는다. 조사한 히트곡들의 제목 형태 분포를 따른다.
title_kind에 고른 형태를 적고, why에 왜 그 형태인지 쓴다.

[가사의 결]
- 감성 레퍼런스: {ref}. 밴드 음악의 노랫말이다. 쉬운 말, 입말, 유머와 자조, 능청, 허세, 갑자기 진심이 되는 한 줄, 낱말의 리듬.
  아래 [레퍼런스 작사 프로필]의 원리를 가져오되 표현과 특정 낱말은 절대 베끼지 않는다. 곡마다 가장 맞는 팀의 결을 고르고, 일곱 팀을 섞어 뭉개지 않는다.
- 많이 말하지 않는다. 곡 하나에 태도 하나, 외칠 말 하나. 나머지는 리듬과 농담으로 채운다.
- 비유는 곡 전체에 한두 개만, 일상의 것에서. 시처럼 다듬은 문장보다 사람이 중얼거리거나 소리치는 말이 낫다.
- 진심은 한 줄이면 된다. 그 한 줄 앞뒤는 가볍게 둔다. 그래야 그 줄이 산다.

[담백]
- 담백해야 한다. 꾸미는 말(형용사, 부사)을 거의 쓰지 않는다. 명사와 동사로 쓴다. 한 줄에 한 가지만.
- 서술하지 않는다. 장면을 시간 순서로 옮기는 줄거리, 상황 묘사, 설명은 가사가 아니다. 말 한마디를 남기고 나머지는 지운다.
- 억지로 감동시키려는 장치, 낯간지러운 고백, 시 흉내는 한 줄도 쓰지 않는다. 의심되면 지운다.
- 쓰고 나서 아래 [AI 티 점검표]로 줄마다 점검하고, 걸리는 줄은 고치거나 지운다. 줄이 줄어드는 것은 좋은 일이다.

[말투]
- 진짜 사람이 쓴 가사처럼 읽혀야 한다. 조사에서 모은 실제 가사의 말투 분포를 따른다.
- 줄 끝을 "-요/-해요/-거예요/-했어요"로 맞추지 않는다. 기본은 반말(-어, -아, -지, -네, -야, -데, -자, -까)과 명사나 부사로 끊기는 줄이다.
- 한 구간 안에서 줄 끝이 모두 같은 어미로 끝나지 않게 한다. 문장을 끝까지 말하지 않고 끊는 줄을 섞는다.
- "그냥", "뭐", "있잖아", "근데", "아 몰라" 같은 입말을 쓴다. 비문 하나쯤 괜찮다.
- 같은 틀의 문장을 세 번 이상 늘어놓지 않는다(나열, 대구의 남용). 되풀이는 후렴에서만.
- 느낌표는 쓰지 않는다(소리는 가사가 아니라 멜로디가 낸다). 과장된 고백, 닳은 낱말은 쓰지 않는다.

[가사 설계]
- 1절은 태도나 말 한마디로 바로 연다. 상황 설명으로 시작하지 않는다.
- 2절은 1절과 같은 멜로디 자리의 줄은 음절 수를 맞추고, 시점이나 상대를 바꿔 다른 각도를 준다.
- 마지막 후렴은 한두 줄을 바꿔 끝낸다. 결말을 설명하지 않는다.
- 쇼츠 15초에 들어갈, 캡처해서 공유하고 싶은 한 줄을 반드시 하나 넣는다(보통 후렴 둘째 줄).
- 줄 끝 소리는 구간 안에서 느슨하게만 맞춘다. 운을 맞추려고 어미를 통일하지 않는다.
- 한 줄은 6~13음절, 구간마다 2~4줄, 전체 3분 안팎. 줄 수가 적을수록 좋다.
- 가사는 한국어만. 숫자와 영어는 한글 발음으로(열두 시, 버스). 추임새는 괜찮다.
- 구간 태그는 한 줄에 따로. 코러스 메아리는 괄호로 따로 한 줄에 쓴다. 예: (아 몰라)
- 레퍼런스 곡의 표현을 그대로 쓰지 않는다. 원리만 가져온다.

[클래식 멜로디 모드]
원곡이 정해진 경우 아래 "멜로디 곡 자료"가 붙는다. 클래식은 숨기지 않고 티 나게 쓴다:
전주에서 원곡 주제가 크게 연주되고, 후렴은 원곡 주제 선율을 그대로 부르며, 간주에서 다시 원곡 주제가 나온다. 절은 새 선율과 자유로운 가사다.
- 가사는 자료의 가사 계획(구간 순서, 줄 수, 후렴의 줄마다 음절 수)을 그대로 따른다. 이 계획이 위의 구간 규칙보다 우선한다. [Pre-Chorus], [Bridge]는 쓰지 않는다.
- 후렴이 원곡 선율이므로 후렴 가사가 곡의 중심이다. 제목과 외칠 말은 후렴에 둔다. 후렴 가사의 호흡(긴 음, 쉼)이 선율과 맞아야 한다.
- 노래의 태도와 원곡의 배경이 속으로 이어져야 한다. why에 그 연결을 한두 문장으로 쓴다. 억지로 슬픈 사연을 끌어오지 않는다. 원곡이 밝으면 밝게 쓴다.
- classic_note: 유튜브 설명란에 넣을 원곡 이야기 3~4문장. 원곡의 배경 사실 한두 개와 이 노래가 그 위에 선 이유. 담담하게, 과장 없이.
- theme_instrument(piano, guitar, strings, bell)는 Suno에 넣을 멜로디 파일에서 주제를 연주할 음색이다. 곡마다 다르게 고른다.

[Suno 스타일]
- 영어, 쉼표 구분, 200자 이내. korean을 꼭 넣는다.
- 기본 소리는 오케스트라 밴드: 드럼, 베이스, 기타, 피아노 위에 현악과 브라스가 같이 울리는 풍성한 편곡. 작은 편성은 요청이 있을 때만.
  예: korean orchestral rock, full band with string section and brass, driving drums, electric guitar riff quoting the classical theme, big singalong chorus, 128 bpm, male vocal
- 장르는 곡마다 다르게: 오케스트라 록, 브라스 팝, 디스코 펑크, 인디 록, 펑크, 시티팝, 스윙, 레트로 팝, 왈츠 록, 포크 록 등. 이전 곡 스타일과 겹치지 않게 한다.
- 원곡 주제를 맡을 구체적 악기를 적는다(일렉 기타 리프, 브라스 섹션, 현악 유니즌, 신스 리드, 합창, 휘파람, 아코디언 등).
- 클래식 모드면 원곡의 조성과 빠르기를 존중하되 BPM은 편곡에 맞게 올려도 되고, "intro and chorus quote the uploaded classical theme prominently, verses original"을 넣는다.
- 빠르기, 전개(조용히 시작해 터지는지, 처음부터 달리는지), 보컬(성별, 음색, 떼창 여부)을 적는다.
- exclude는 제외 스타일 칸. 예: lo-fi, solo piano ballad, rap, autotune, english lyrics

[사진]
- photo_query: Pexels 영어 검색어 2~5단어.
- image_prompt: AI 이미지용 영어 장면 묘사 1~2문장. 곡의 기분에 맞는 사진 한 장(시간대, 빛, 장소, 색). 곡이 신나면 사진도 환하게. 글자, 간판 문구, 정면 얼굴 없음.

[유튜브]
- situation: 제목 뒤에 붙일 듣는 상황 문구. 사람들이 검색하는 말로 10~20자. 예: 월요일 아침 출근길 노래, 기분 좋을 때 듣는 노래
- shorts_title: 쇼츠 제목. 한 줄, 30자 이내. #shorts는 붙이지 않는다.
- yt_intro: 설명란 첫 두 줄. 검색 결과에 보이는 부분이라 곡의 태도와 원곡 이름이 바로 읽혀야 한다.
- comment_prompt: 설명란 끝에서 댓글을 부르는 한 줄. 질문이 아니어도 된다.
- hashtags: 정확히 15개, # 없이, 띄어쓰기 없이. 앞의 3개가 제목 위에 보이니 가장 넓게 검색되는 말로.
  곡 제목, 장르(밴드음악, 인디록 등 실제 장르), 상황(출근길노래, 드라이브노래), 기분(신나는노래, 위로노래), 플레이리스트형(노동요, 감성플리), 원곡 이름, 클래식리메이크.
- tags: 검색 키워드 25~35개. 한국어 위주에 영어 몇 개(korean rock, classical crossover). 다른 가수 이름은 넣지 않는다(유튜브 스팸 정책).
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


def took(label: str, t0: float) -> None:
    print(f"[{label}] {time.time() - t0:.0f}초", flush=True)


def _check(response) -> None:
    if response.stop_reason == "refusal":
        raise RuntimeError("Claude가 이 요청을 거절했습니다. 키워드를 바꿔서 다시 실행하세요.")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("응답이 길이 제한에 걸려 잘렸습니다. 다시 실행하세요.")


def _ref() -> str:
    from .learn import references
    return ", ".join(references())


CHECKLIST = Path(__file__).resolve().parent.parent / "assets" / "lyrics" / "_점검표.md"


def _checklist() -> str:
    return CHECKLIST.read_text(encoding="utf-8").strip() if CHECKLIST.exists() else ""


def _system(base: str) -> str:
    """시스템 프롬프트에 레퍼런스 이름, 작사 프로필, AI 티 점검표를 붙인다."""
    from .learn import profiles_text
    text = base.replace("{ref}", _ref())
    profiles = profiles_text()
    if profiles:
        text += "\n\n[레퍼런스 작사 프로필]\n" + profiles
    check = _checklist()
    if check:
        text += "\n\n[AI 티 점검표]\n" + check
    return text


REVIEW = """\
너는 가사를 고치는 편집자다. 작사가가 쓴 가사를 받아 AI가 쓴 티, 억지 감성, 오글거림, 서술식 줄거리, 설명하는 줄을 걷어낸다.
담백하게. 더 짧게, 더 쉽게, 덜 설명하게. 사람이 중얼거리거나 외치는 말만 남긴다.

지킬 것
- 구간 태그와 구간 순서는 그대로 둔다. [Chorus]와 [Final Chorus]의 줄 수와 줄마다 음절 수는 바꾸지 않는다(원곡 선율에 얹히는 자리다). 음절 수를 지키면서 낱말만 바꾼다.
- 절의 줄은 지우거나 줄여도 된다. 두 절의 줄 수는 같게 유지한다.
- 제목이 점검표에 걸리면 바꾼다. 바꾸지 않아도 되면 그대로 둔다.
- 새로 쓰는 줄도 아래 점검표를 통과해야 한다. 고친 뒤 다시 한 번 점검한다.
- 바꾼 줄마다 왜 바꿨는지 짧게 적는다.

JSON만 답한다: {"lyrics": "<고친 가사 전문>", "title": "<제목>", "share_line": "<가사 안에 그대로 있는 공유용 한 줄>", "changes": ["<바꾼 줄: 이유>", ...]}
"""


def polish(data: dict, plan: str = "") -> dict:
    """쓴 가사를 점검표로 한 번 더 걸러 담백하게 고친다."""
    schema = {"type": "object",
              "properties": {"lyrics": {"type": "string"}, "title": {"type": "string"}, "share_line": {"type": "string"},
                             "changes": {"type": "array", "items": {"type": "string"}}},
              "required": ["lyrics", "title", "share_line", "changes"], "additionalProperties": False}
    system = REVIEW + "\n\n[AI 티 점검표]\n" + _checklist()
    content = f"[제목]\n{data['title']}\n\n[가사]\n{data['lyrics']}"
    if plan:
        content += f"\n\n[후렴 음절 계획]\n{plan}"
    t0 = time.time()
    with anthropic.Anthropic().beta.messages.stream(
        model=MODEL, max_tokens=12000, system=system, betas=BETAS, fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    took("가사 검수", t0)
    out = json.loads(next(b.text for b in response.content if b.type == "text"))
    if out.get("lyrics", "").count("[") >= 3:
        data["lyrics_draft"] = data["lyrics"]
        data["lyrics"] = out["lyrics"].strip()
        data["title"] = (out.get("title") or data["title"]).strip()
        data["share_line"] = out.get("share_line") or data.get("share_line", "")
        data["polish"] = out.get("changes", [])
    return data


def safe_polish(data: dict, piece_id: str = "") -> dict:
    """검수가 실패해도 초고는 남긴다."""
    try:
        return polish(data, classical.lyric_plan(piece_id) if piece_id else "")
    except (anthropic.APIError, RuntimeError) as e:
        print(f"가사 검수를 건너뜁니다: {e}", flush=True)
        return data


CHOOSE = """\
너는 음악학자이자 프로듀서다. 새로 쓸 노래에 가장 잘 맞는 클래식 원곡을 하나 고른다. 모두 저작권이 끝난 곡이다.
기준은 둘이다. 첫째, 원곡의 배경(누구를 위해, 어떤 시기에, 무엇을 바라며 썼는지)과 이 노래의 태도가 속으로 이어질 것.
둘째, 첫 소절에 많은 사람이 "아, 이 곡" 하고 알아들을 것. 후렴에서 그 선율을 그대로 부르므로 알아듣는 힘이 곧 곡의 힘이다.
슬픈 사연을 억지로 끌어오지 않는다. 노래가 신나면 밝고 힘 있는 원곡을 고른다. 같은 원곡을 자꾸 고르지 않는다.
JSON만 답한다: {"id": "<곡 id>", "reason": "<왜 이 곡인지 4~6문장, 원곡 배경의 구체적 사실을 들어서>"}
"""


def choose_classic(brief: str, used: list[str] | None = None) -> dict:
    """used: 최근 곡들이 쓴 원곡 id. 겹치지 않게 한다."""
    client = anthropic.Anthropic()
    if used:
        names = [p["name"] for p in classical.catalog() if p["id"] in used]
        brief += "\n\n[최근에 이미 쓴 원곡 — 이번에는 고르지 않는다]\n" + ", ".join(names)
    schema = {"type": "object", "properties": {"id": {"type": "string", "enum": [p["id"] for p in classical.catalog()]},
                                                 "reason": {"type": "string"}},
              "required": ["id", "reason"], "additionalProperties": False}
    t0 = time.time()
    with client.beta.messages.stream(
        model=FAST_MODEL, max_tokens=8000, system=CHOOSE, betas=BETAS, fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": f"[노래 사연]\n{brief}\n\n[고를 수 있는 원곡]\n{classical.catalogue()}"}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    took("원곡 고르기", t0)
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def research(brief: str) -> str:
    """웹 검색으로 레퍼런스 노트를 만든다."""
    client = anthropic.Anthropic()
    today = dt.datetime.now(KST).strftime("%Y년 %m월 %d일")
    first = {"role": "user", "content": f"오늘은 {today}.\n\n{brief}"}
    messages = [first]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 6,
              "user_location": {"type": "approximate", "country": "KR", "timezone": "Asia/Seoul"}}]
    t0 = time.time()
    for _ in range(5):
        with client.beta.messages.stream(
            model=FAST_MODEL, max_tokens=16000, system=_system(RESEARCH), betas=BETAS, fallbacks="default",
            output_config={"effort": "medium"}, tools=tools, messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "pause_turn":
            # 서버 검색이 길어지면 멈춘 응답을 그대로 돌려보내 이어서 하게 한다
            messages = [first, {"role": "assistant", "content": response.content}]
            continue
        _check(response)
        took("레퍼런스 조사", t0)
        return "\n".join(b.text for b in response.content if b.type == "text").strip()
    return ""


def prepare(*, hook: str = "", idea: str = "", theme: str = "", vocal: str = "", style: str = "",
            classic: str = "", avoid: list[str] | None = None, avoid_styles: list[str] | None = None,
            used_classics: list[str] | None = None) -> dict:
    """1단계: 요청문을 만들고, 원곡 고르기와 레퍼런스 조사를 동시에 한다.
    classic: '' 없음, 'auto' 의미로 고르기, 또는 카탈로그의 곡 id. 결과는 JSON으로 저장할 수 있는 dict."""
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

    # 원곡 고르기와 레퍼런스 조사는 서로 기다릴 필요가 없어 동시에 한다
    piece, reason = None, ""
    if classic and classic not in ("auto", "none"):
        piece, reason = classical.get(classic), "직접 고른 원곡"
    research_brief = brief + ("\n\n[멜로디 곡]\n이 노래는 저작권이 끝난 클래식 선율을 전주·후렴·간주에 그대로 쓴다."
                              if classic and classic != "none" else "")
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_notes = pool.submit(research, research_brief)
        f_pick = pool.submit(choose_classic, brief, used_classics) if classic == "auto" else None
        if f_pick:
            pick = f_pick.result()
            piece, reason = classical.get(pick["id"]), pick["reason"]
        notes = ""
        try:
            notes = f_notes.result()
        except (anthropic.APIError, RuntimeError) as e:
            print(f"레퍼런스 조사를 건너뜁니다: {e}", flush=True)
    if piece:
        brief += (f"\n\n[멜로디 곡]\n이 노래는 {piece['name']}({piece['composer']}, {piece['year']}) 선율 위에 쓴다. "
                  f"고른 이유: {reason}")
    return {"brief": brief, "piece_id": piece["id"] if piece else "", "reason": reason, "notes": notes}


def compose(work: dict) -> dict:
    """2단계: 가사·스타일·유튜브 글을 쓴다(가장 깊은 생각). 검수는 하지 않는다."""
    piece = classical.get(work["piece_id"]) if work.get("piece_id") else None
    notes = work.get("notes", "")
    parts = []
    if notes:
        parts.append(f"[레퍼런스 조사 노트]\n{notes}")
    if piece:
        parts.append(f"[멜로디 곡 자료]\n{piece['story'].strip()}\n\n{classical.lyric_plan(piece['id'])}")
    parts.append(f"[요청]\n{work['brief']}")
    content = "\n\n".join(parts)
    t0 = time.time()
    with anthropic.Anthropic().beta.messages.stream(
        model=MODEL, max_tokens=32000, system=_system(SYSTEM), betas=BETAS, fallbacks="default",
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    took("작사", t0)
    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    data["chosen"] = max(0, min(int(data.get("chosen", 0)), len(data["candidates"]) - 1))
    data["research"] = notes
    if piece:
        data["classic"] = {"id": piece["id"], "name": piece["name"], "composer": piece["composer"],
                           "year": piece["year"], "reason": work.get("reason", ""), "note": data.get("classic_note", ""),
                           "instrument": data.get("theme_instrument", "piano")}
    return data


def write_song(*, do_polish: bool = True, **kw) -> dict:
    """prepare → compose (→ polish) 를 한 번에."""
    work = prepare(**kw)
    data = compose(work)
    if do_polish:
        data = safe_polish(data, work["piece_id"])
    return data
