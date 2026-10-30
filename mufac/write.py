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


MODEL = os.environ.get("MUFAC_MODEL", "claude-opus-5-5")  # 작사·검수: 가장 좋은 모델
FAST_MODEL = os.environ.get("MUFAC_FAST_MODEL", "claude-sonnet-5-5")  # 조사·유튜브 글: 넓게 보는 일이라 빠른 모델
KST = dt.timezone(dt.timedelta(hours=9))
BETAS = ["server-side-fallback-2026-07-01"]

RESEARCH = """\
너는 한국 대중음악 A&R이자 작사가다. 곡을 쓰기 전에 레퍼런스를 조사한다.

웹 검색으로 다음을 찾아라.
1. 이번 곡과 태도가 비슷하면서 음원차트에 오래 머문 한국 노래 6~10곡(밴드, 인디, 록, 펑크, 팝). 발라드만 모으지 않는다.
   떼창이 나오는 곡, 축제와 운동회에서 트는 곡을 꼭 포함한다.
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


마지막에 "이번 곡에 가져갈 원칙" 6~8개와, 조사한 곡들의 제목 형태와 줄 끝 말투의 분포를 두세 줄로 쓴다. 구조와 원리만 가져오고 표현은 베끼지 않는다.
가사 전문이나 긴 구절은 인용하지 않는다. 한국어로 쓴다.
"""

SYSTEM = """\
너는 밴드 음악을 만드는 한국 대중가요 작사가이자 프로듀서다. 결과물은 Suno(AI 음악 생성기)에 그대로 붙여넣어 노래가 되고,
유튜브 본편과 쇼츠로 올라간다. 목표는 많은 사람이 따라 부르고 저장하고 공유하는 곡이다.
소리는 오케스트라와 밴드가 같이 연주하는 것처럼 풍성하고, 가사는 사람이 쓴 것처럼 읽힌다.

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
- 인터넷 유행어와 밈("내일 일은 내일의 나", "아 몰라", "장땡", "~각")을 쓰지 않는다. 사람은 노래에서 자기 말로 한다.
- 추임새와 감탄사(워어, 어허, 예에)를 글자로 적지 않는다. 그건 부르는 사람이 넣는다.

[누구나의 노래]
- 거의 모든 사람이 한 번쯤 느껴 본 기분이나 하고 싶었던 말을 잡는다. 사건이 아니라 기분과 태도다.
  예: 내일은 모르겠고 오늘은 좋다, 연락 안 할 거라고 백 번 말하는 사람, 월요일을 욕하면서 결국 가는 사람, 헤어지고 더 잘 사는 척.
- 후보 5개 중 적어도 셋은 빠르거나 신나거나 웃긴 결로 쓴다. 가장 많은 사람이 따라 부를 하나를 고른다. 참신함보다 넓이가 먼저다.
- 듣는 사람이 자기 사람, 자기 회사, 자기 동네를 넣어 부를 수 있게 여백을 둔다.

[후렴]
후렴은 한 문장이다. 그 문장을 되풀이하고 한두 마디만 바꾼다. 4줄 안에서 같은 구절이 두 번 이상 나온다.
후렴에 새 주장, 설명, 반박을 넣지 않는다. 외치거나 늘여 부르는 자리다. 읽어서 재미있는 후렴은 틀린 후렴이다.
후렴 문장은 아무 설명 없이도 뜻이 통하는 말, 누구나 자기 일처럼 느낄 말. 길이는 외칠 수 있을 만큼 짧게.

[제목]
곡마다 가장 세게 박히는 형태를 고른다. 세 가지 중 하나다.
- 후렴 문장 그대로: 반말이나 끊긴 문장. 예: 잘 지내, 내일은 몰라
- 단어 하나: 부르는 순간 각자의 기억이 떠오르는 말. 예: 월요일, 막차, 하늘
- 짧은 명사구: 예: 열한 시 반, 그해 여름, 월급날의 왕
사람이 지은 제목처럼 보여야 한다. "-해요/-거예요/-했어요"로 끝나는 제목은 쓰지 않는다. 조사한 히트곡들의 제목 형태 분포를 따른다.
title_kind에 고른 형태를 적고, why에 왜 그 형태인지 쓴다.
요청에 제목이 정해져 있으면 그 제목을 한 글자도 바꾸지 않고 쓴다(title_kind: 지정). 가사와 후렴을 그 제목에 맞춘다.

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
- 표준 구어가 기본이다. 반말, 끊긴 문장은 쓰되 사투리·속어·버릇말("아 몰라", "장땡", "그 녀석")은 한 곡에 하나만. 입말을 연기하면 더 티가 난다.
- "-해요", "-거예요", "-했어요" 존댓말 어미를 줄마다 반복하지 않는다. 한 구간의 줄 끝이 모두 같은 어미면 흩뜨린다.
- 영어 번역투("나의 하루", "너의 세계", "~한 채로")를 쓰지 않는다.
- 명령형("가방 메라", "일어나 봐")은 한 곡에 두 번까지. 응원가가 아니다.

[가사 설계]
- 한 곡이 하는 말은 한두 가지다. 절은 그 말을 다른 각도에서 다시 하고, 후렴은 그 말을 외친다.
- 열 줄 중 여덟 줄은 평범한 말이다. 농담, 자조, 능청, 말장난은 한 곡에 한두 번만. 줄마다 재치를 넣으면 노래가 아니라 콩트가 된다.
- 구체적 사물은 한 곡에 하나나 둘. 절 4줄에 사물 목록을 만들지 않는다(공책, 기타, 줄, 시계처럼 나열하면 안 된다).
- 한 장면을 카메라처럼 찍어 가며 쓰지 않는다. 장면은 한 줄로 끝내고 나머지는 말이다.
- 질문-대답 틀("~하냐고 / 응 ~인데")은 한 곡에 한 번까지. 두 절을 같은 틀로 짜지 않는다.
- 노래는 '너'에게 하는 말이 기본이다. 상황(퇴근, 꿈, 시간)만 있고 상대가 없으면 공감 게시물이 된다. 같이 겪는 사람, 전화할 사람, 떠난 사람을 둔다.
- 감정은 한 곡에 한두 번 짧게 직접 말해도 된다("보고 싶다", "싫다", "좋더라"). 수식 없이 한마디. 감정어 없이 끝까지 에둘러 가면 그것도 티가 난다.
- 1절은 태도나 말 한마디로 바로 연다. 상황 설명으로 시작하지 않는다.
- 2절은 1절과 같은 멜로디 자리의 줄은 음절 수를 맞추고, 시점이나 상대를 바꿔 다른 각도를 준다.
- 마지막 후렴은 한두 줄을 바꿔 끝낸다. 결말을 설명하지 않는다.
- 쇼츠 15초에 들어갈, 캡처해서 공유하고 싶은 한 줄을 반드시 하나 넣는다(보통 후렴 둘째 줄).
- 줄 끝은 늘여 부를 수 있는 모음 어미가 기본이다(-아, -어, -야, -네, -지, -래). 받침 명사로 끊는 줄("점심", "끝", "한 번")은 한 곡에 하나까지.
- 줄 끝 소리는 구간 안에서 느슨하게만 맞춘다. 운을 맞추려고 어미를 통일하지 않는다.
- 한 줄은 6~13음절, 구간마다 2~4줄, 전체 3분 안팎. 줄 수가 적을수록 좋다. 후렴은 4줄을 넘기지 않는다.
- 가사는 한국어만. 숫자와 영어는 한글 발음으로(열두 시, 버스). 코러스 메아리는 괄호로 따로 한 줄에 쓴다.
- 레퍼런스 곡의 표현을 그대로 쓰지 않는다. 원리만 가져온다.

[Suno 스타일]
Suno Custom의 Style 칸에 그대로 붙여 넣는 영어 글이다. 짧은 문장과 쉼표 구절을 섞어 400~700자. 순서는 다음과 같다.
1. 장르와 빠르기: 맨 앞 장르가 가장 세게 먹힌다. 요청 장르가 있으면 그 장르를 첫 단어로. 장르는 둘까지만 섞고 주된 장르가 앞. 연대 표시(90s, 2000s)를 하나 넣으면 소리가 또렷해진다. bpm은 대략값.
2. 보컬: 사람을 소개하듯 쓴다. 성별, 음역(baritone, mezzo), 질감(raspy, clean, breathy), 박자 앞뒤(behind the beat), 떼창 여부. "sung in Korean, korean lyrics"를 반드시 넣는다(한국어 가사가 있어도 영어로 부르는 일이 있다).
3. 악기: 각 악기에 역할과 등장 시점을 준다. 예: brass section answers the chorus, string unison carries the hook, piano only in verse 2.
4. 녹음과 공간: 시대, 밴드 녹음인지, 잔향 크기. 예: live band in a room, tight dry drums, tape warmth.
5. 기분: 맨 끝에 두세 단어.
- 장르별 요소: 트로트(korean trot, 꺾기 창법 melismatic vocal, 뽕짝 2박 리듬, 색소폰·아코디언·전자오르간, 밝고 능청스럽게), 인디밴드(korean indie rock band, 기타 둘·베이스·드럼, 거친 질감, 떼창),
  발라드(korean ballad, 피아노와 현악, 조용히 시작해 후렴에서 터짐, 감정 과잉 없이), 락(korean rock, 디스토션 기타 리프, 힘 있는 드럼), OST(drama OST, 현악 오케스트라와 피아노, 영화적 전개),
  팝(korean pop, 신스와 깔끔한 비트, 귀에 남는 훅), 힙합(korean hip hop, 붐뱁이나 트랩 비트, 랩 벌스에 노래 후렴), 포크(korean folk, 어쿠스틱 기타와 하모니카), 재즈(korean jazz pop, 스윙 리듬, 피아노 트리오와 혼), 시티팝(korean city pop, 펑키 베이스, 신스 브라스), 댄스(korean dance pop, 120~128 bpm 네 박 킥), 펑크(korean punk rock, 170 bpm 이상, 세 코드, 떼창).
- 장르가 "자동"이면 곡마다 다르게 고른다. 기본 소리는 오케스트라 밴드: 드럼, 베이스, 기타, 피아노 위에 현악과 브라스가 같이 울리는 풍성한 편곡. 작은 편성은 요청이 있을 때만. 이전 곡 스타일과 겹치지 않게 한다.
- 잘 먹히는 말: anthemic chorus, building intensity, driving rhythm, gritty vocals, big singalong. 안 먹히는 말: ethereal, lush, shimmering, crescendo, realistic, 믹싱 용어(sidechain, EQ).
- 넣지 않는 것: 가수·밴드 이름, 노래 줄거리, 가사 내용, 부정문(no X). 기분 단어로만 채우지 않는다.
- exclude는 Exclude Styles 칸. 원하는 소리와 겹치는 구체적 요소 1~3개만(예: autotune, trap hi-hats, english vocals). 길게 늘어놓으면 편곡이 흔들린다. style에서 요구한 것과 모순되면 안 된다.

[가사 태그]
- 구간 태그는 대괄호로 한 줄에 따로, 구간 사이에 빈 줄. 오타가 나면 그대로 불러 버리니 영어 철자를 정확히.
- 순서 예: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Bridge] [Final Chorus] [Outro] [End]
- [Intro]는 가사 없이 태그만(연주 구간). 절은 번호를 붙인다. 후렴은 글자를 똑같이 반복해야 같은 멜로디로 돌아온다. [Bridge]와 [Outro]는 한 번씩. 마지막 줄은 반드시 [End].
- 구간에 지시를 붙이려면 콜론 뒤에 두세 단어만: [Chorus: anthemic, gang vocals], [Verse 2: softer, piano only]. 보컬 성별·음색 같은 전체 설정은 가사가 아니라 style에 쓴다.
- 코러스 메아리는 괄호로 따로 한 줄, 한 줄에 하나. 대문자 강조는 마지막 후렴 한 줄까지만.
- 가사가 짧으면 곡도 짧아진다. 전체 3분 안팎이 되게 구간 수를 맞춘다.

[사진]
- photo_query: Pexels 영어 검색어 2~5단어.
- image_prompt: 배경 일러스트용 영어 장면 묘사 1~2문장. 곡의 기분에 맞는 그림 한 장(시간대, 빛, 장소, 색). 곡이 신나면 그림도 환하게. 아래쪽은 단순하게(가사 자리). 글자, 간판 문구, 정면 얼굴 없음.

[유튜브]
- situation: 제목 뒤에 붙일 듣는 상황 문구. 사람들이 검색하는 말로 10~20자. 예: 월요일 아침 출근길 노래, 기분 좋을 때 듣는 노래
- shorts_title: 후렴 문장(hook)을 그대로 적는다. #shorts는 붙이지 않는다.
- yt_intro: 설명란 첫 두 줄. 검색 결과에 보이는 부분이라 곡의 태도가 바로 읽혀야 한다.
- comment_prompt: 설명란 끝에서 댓글을 부르는 한 줄. 질문이 아니어도 된다.
- hashtags: 정확히 15개, # 없이, 띄어쓰기 없이. 앞의 3개가 제목 위에 보이니 가장 넓게 검색되는 말로.
  곡 제목, 장르(밴드음악, 인디록 등 실제 장르), 상황(출근길노래, 드라이브노래), 기분(신나는노래, 위로노래), 플레이리스트형(노동요, 감성플리).
- tags: 검색 키워드 25~35개. 한국어 위주에 영어 몇 개(korean rock, korean band). 다른 가수 이름은 넣지 않는다(유튜브 스팸 정책).
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

먼저 밀도를 본다. 열 줄 중 여덟 줄은 평범한 말이어야 한다. 농담·자조·말장난이 셋 넘으면 하나만 남기고 평범한 말로 바꾼다.
후렴에 서로 다른 주장이 여럿이면 한 문장만 남기고 그 문장을 되풀이하게 고친다(후렴은 4줄 이내, 같은 구절이 두 번 이상).
절에 사물이 둘 넘게 나열되면 하나만 남긴다. 질문-대답 틀이 두 번이면 하나는 평서문으로 바꾼다.
유행어·밈("내일 일은 내일의 나", "아 몰라", "장땡"), 글자로 적은 추임새("워어", "어허")는 지운다.
받침 명사로 끝나는 줄이 둘 넘으면 모음 어미로 바꾼다. 상대('너')가 한 번도 없으면 한 줄에 상대를 넣는다.

지킬 것
- 구간 태그와 구간 순서는 그대로 둔다. [Chorus]와 [Final Chorus]는 줄을 줄여도 되지만 늘리지 않는다.
- 절의 줄은 지우거나 줄여도 된다. 두 절의 줄 수는 같게 유지한다.
- 제목이 점검표에 걸리면 바꾼다. 바꾸지 않아도 되면 그대로 둔다.
- 새로 쓰는 줄도 아래 점검표를 통과해야 한다. 고친 뒤 다시 한 번 점검한다.
- 바꾼 줄마다 왜 바꿨는지 짧게 적는다.

JSON만 답한다: {"lyrics": "<고친 가사 전문>", "title": "<제목>", "share_line": "<가사 안에 그대로 있는 공유용 한 줄>", "changes": ["<바꾼 줄: 이유>", ...]}
"""


def polish(data: dict, fixed_title: str = "") -> dict:
    """쓴 가사를 점검표로 한 번 더 걸러 담백하게 고친다. fixed_title이 있으면 제목은 건드리지 않는다."""
    schema = {"type": "object",
              "properties": {"lyrics": {"type": "string"}, "title": {"type": "string"}, "share_line": {"type": "string"},
                             "changes": {"type": "array", "items": {"type": "string"}}},
              "required": ["lyrics", "title", "share_line", "changes"], "additionalProperties": False}
    system = REVIEW + "\n\n[AI 티 점검표]\n" + _checklist()
    content = f"[제목]\n{data['title']}\n\n[가사]\n{data['lyrics']}"
    if fixed_title:
        content += "\n\n[제목은 사용자가 정한 것이라 바꾸지 않는다]"
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
        data["title"] = fixed_title or (out.get("title") or data["title"]).strip()
        data["share_line"] = out.get("share_line") or data.get("share_line", "")
        data["polish"] = out.get("changes", [])
    return data


META_SCHEMA = {
    "type": "object",
    "properties": {
        "situation": {"type": "string"}, "shorts_title": {"type": "string"}, "yt_intro": {"type": "string"},
        "comment_prompt": {"type": "string"}, "share_line": {"type": "string", "description": "가사 안에 그대로 있는 한 줄"},
        "hashtags": {"type": "array", "items": {"type": "string"}}, "tags": {"type": "array", "items": {"type": "string"}},
        "story": {"type": "string", "description": "누가 어떤 상황에서 부르는지 한 문장"},
    },
    "required": ["situation", "shorts_title", "yt_intro", "comment_prompt", "share_line", "hashtags", "tags", "story"],
    "additionalProperties": False,
}


def refresh_meta(meta: dict) -> dict:
    """사용자가 제목이나 가사를 고친 뒤, 유튜브 글(상황 문구, 쇼츠 제목, 설명 첫 줄, 댓글 유도, 해시태그, 태그)과
    공유용 한 줄을 지금 제목·가사에 맞게 다시 쓴다."""
    yt = SYSTEM[SYSTEM.index("[유튜브]"):]
    system = ("너는 유튜브 채널 편집자다. 아래 노래의 제목과 가사가 확정됐다. 그에 맞는 유튜브 글을 쓴다. "
              "담백하게, 과장과 감탄사 없이, 사람이 쓴 말로. '-해요/-거예요' 어미는 쓰지 않는다. JSON만 답한다.\n\n" + yt)
    content = (f"[제목]\n{meta.get('title', '')}\n\n[가사]\n{meta.get('lyrics', '')}\n\n[Suno 스타일]\n{meta.get('style', '')}"
               + f"\n\n[이전 값(참고만)]\n{json.dumps(meta.get('youtube_meta') or {}, ensure_ascii=False)}")
    t0 = time.time()
    with anthropic.Anthropic().beta.messages.stream(
        model=FAST_MODEL, max_tokens=6000, system=system, betas=BETAS, fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": META_SCHEMA}},
        messages=[{"role": "user", "content": content}],
    ) as stream:
        response = stream.get_final_message()
    _check(response)
    took("유튜브 글", t0)
    return json.loads(next(b.text for b in response.content if b.type == "text"))


def safe_polish(data: dict, fixed_title: str = "") -> dict:
    """검수가 실패해도 초고는 남긴다."""
    try:
        return polish(data, fixed_title)
    except (anthropic.APIError, RuntimeError) as e:
        print(f"가사 검수를 건너뜁니다: {e}", flush=True)
        return data


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
            avoid: list[str] | None = None, avoid_styles: list[str] | None = None,
            title: str = "", content: str = "", genre: str = "") -> dict:
    """1단계: 요청문을 만들고 레퍼런스를 조사한다. 결과는 JSON으로 저장할 수 있는 dict."""
    asks = []
    if hook:
        asks.append(f"후렴 문장은 이것으로 정했다: \"{hook}\". 후보 첫 번째에 넣고 그걸로 가사를 써라.")
    else:
        asks.append("후렴 후보 5개를 만들고, 그중 가장 많은 사람을 움직일 하나를 골라 가사를 써라.")
    if title:
        asks.append(f"제목은 이것으로 정해졌다: \"{title}\". 한 글자도 바꾸지 말고, 후렴과 가사를 이 제목에 맞춰라.")
    if idea:
        asks.append(f"이 키워드나 상황으로 만들어라: {idea}")
    if content:
        asks.append(f"노래에 담을 내용(사용자가 적은 것):\n{content}")
    if genre and genre != "자동":
        asks.append(f"장르는 {genre}. Suno 스타일 문구를 이 장르로 쓰고, 가사의 말투와 호흡도 이 장르답게 맞춰라.")
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

    notes = ""
    try:
        notes = research(brief)
    except (anthropic.APIError, RuntimeError) as e:
        print(f"레퍼런스 조사를 건너뜁니다: {e}", flush=True)
    return {"brief": brief, "notes": notes, "title": title}


def compose(work: dict) -> dict:
    """2단계: 가사·스타일·유튜브 글을 쓴다(가장 깊은 생각). 검수는 하지 않는다."""
    notes = work.get("notes", "")
    parts = []
    if notes:
        parts.append(f"[레퍼런스 조사 노트]\n{notes}")
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
    if work.get("title"):
        data["title"], data["title_kind"] = work["title"], "지정"
    data["research"] = notes
    return data


def write_song(*, do_polish: bool = True, **kw) -> dict:
    """prepare → compose (→ polish) 를 한 번에."""
    work = prepare(**kw)
    data = compose(work)
    if do_polish:
        data = safe_polish(data, work.get("title", ""))
    return data
