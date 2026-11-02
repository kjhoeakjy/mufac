"""영어 노래: 영어 작사 규칙, 영어 검수, 영어 유튜브 글, 자연스러운 한국어 번역.

한국어 규칙(write.SYSTEM)의 어미·해요체·부정 꼴 같은 한국어 전용 부분은 쓰지 않는다.
소리 설계, Suno 스타일, 가사 태그, 사진은 한국어 곡과 같은 절을 그대로 쓴다.
영어 히트곡 실측(assets/lyrics/_영어실측.json)과 작사법(assets/lyrics/_영어작사.md)이 있으면 프롬프트에 붙인다.
"""

from __future__ import annotations

import json
import time

import anthropic

from . import write as w

EN_STATS = w.LYRICS_DIR / "_영어실측.json"
EN_GUIDE = w.LYRICS_DIR / "_영어작사.md"

SYSTEM_EN_HEAD = """\
너는 영어권 팝 작사가이자 프로듀서다. 이번 곡은 영어 노래다. 가사는 전부 영어로, 원어민 작사가가 쓴 것처럼 쓴다. 결과물은 Suno에 그대로 붙여넣어 노래가 되고 유튜브에 올라간다.
아래 지시문은 한국어지만 가사·제목·후렴·유튜브 글은 모두 영어다(share_line, shorts_title 포함). 한국어를 영어로 옮긴 가사가 아니라 처음부터 영어로 생각한 가사다.

[요청 우선]
- 사용자가 적은 내용·장르·스타일·제목이 아래 모든 규칙보다 앞선다. 내용이 한국어로 와도 가사는 영어로 쓴다. 제목이 한국어로 오면 같은 뜻의 자연스러운 영어 제목으로 바꾼다(title_kind: 지정).
- 장르가 정해졌으면 소리와 가사의 호흡을 그 장르답게.

[추상, 의미] (강제, 사용자 취향)
- 상황 보고가 아니라 뜻이다. 장소 이름, 시각, 요일, 생활 소품(phone, text, car keys, coffee, Uber, Instagram), 동작의 차례로 장면을 세우지 않는다.
  사물은 곡에 둘까지, 뜻을 지는 큰 것(night, road, window, hands, sea, fire, rain, summer)만. 곡을 읽고 "어떤 마음"만 남아야 한다.
- 줄은 뜻 한 겹이다. 보편 명사와 기본 동사(love, time, leave, stay, fall, hold, run, know)로 누구의 상황에도 들어맞는 말을 쓴다.
- 큰말(forever, soul, heaven, fate)은 노래의 말이니 써도 된다. 영어 히트곡에서는 드문 말이라 곡에 하나, 가장 센 자리(후렴 마지막 줄이나 브릿지)에 둔다.
- 가사는 많을 필요 없다. 멜로디와 후렴이 먼저다. 훅이 곡의 뜻 전부를 지고, 절은 그 뜻의 다른 면 하나씩만 짧게 비춘다.

[길이와 구조]
- 구조: [Intro] [Verse 1] [Pre-Chorus] [Chorus] [Verse 2] [Pre-Chorus] [Chorus] [Instrumental] [Bridge] [Final Chorus] [Outro] [End]. 간주 하나는 늘 둔다.
- 줄 수: 절 4줄, 프리코러스 2줄, 후렴 4줄, 브릿지 2~4줄, 아웃트로 0~2줄. 전체 18~26줄(반복 후렴 포함). 길이는 간주와 마지막 후렴 반복으로 채운다.
- 마지막 후렴은 한두 줄만 바꿔 다른 뜻으로 들리게 한다.

[후렴과 훅]
- 후렴은 한 문장이다. 훅(2~6낱말)을 첫 줄이나 마지막 줄(둘 다면 더 좋다)에 두고 후렴 안에서 2~4번 되풀이한다. 제목은 훅 그 자체거나 훅 안의 말이다.
- 훅은 소리로 고른다. 길게 늘일 수 있는 열린 모음(-ay, -oh, -ee, -i)이나 n·m·l로 끝나는 말이 좋다. 세 번 불러도 어색하지 않아야 한다.
- 후렴의 다른 줄도 훅만큼 세야 한다. 훅을 꾸미기만 하는 줄은 넣지 않는다. 첫 후렴은 곡 시작 45초 안.
- 브릿지에는 훅을 쓰지 않는다. 브릿지는 처음 말하는 진심 하나.

[도입부의 임팩트] (강제)
- 1절 첫 두 줄과 후렴의 모든 줄은 선언·모순·고백·부탁·질문·뒤집기 중 하나다. 배경 설명, 날씨, 장소로 시작하지 않는다.
- 첫 줄이 "I"로 시작해도 된다. 그러나 "I remember / I was walking / In the city"처럼 회상·장면으로 열지 않는다.

[영어다운 말] (강제)
- 대화하듯 쓴다. 축약형(I'm, don't, can't, you're, gonna, wanna)을 자연스럽게 쓴다. 풀어 쓴 "I do not", "I am going to"는 강조할 때만.
- 영어 어순과 강세를 지킨다. 강세 있는 음절이 박자의 강한 자리에 오도록 줄을 짠다(prosody). 강세 없는 말(the, of, and)로 줄을 끝내지 않는다.
- 각운은 쓰되 억지로 맞추지 않는다. 히트곡의 운은 대부분 모음운이다(완전운 5.5%, 모음운 23%). 근사운(slant rhyme: time/mind, love/enough)을 기본으로 완전운을 섞는다. 운을 맞추려고 어순을 뒤집거나("love I need") 뜻 없는 낱말을 넣지 않는다.
  같은 낱말로 끝나는 줄(you/you)은 후렴의 반복에서만. 운 패턴은 절마다 AABB나 ABCB 하나로 일관되게.
- 대명사: 곡의 중심은 I와 you다. "you"에게 말하는 곡이 가장 많다. 화자와 상대는 곡 끝까지 같다.
- 번역투 금지: 한국어를 옮긴 듯한 말("my heart is hurting so much", "you are my everything that I have", "fighting", "skinship", "eye smile")을 쓰지 않는다. 콩글리시 금지.
- AI 영어 가사 상투어 금지: neon, whispers, echoes, shadows, tapestry, symphony, shattered, ignite, embers, ethereal, celestial, velvet, silhouette, labyrinth, kaleidoscope, abyss, serenade,
  "dance in the rain", "stars align", "heart of gold", "in this moment", "we were meant to be", "under the moonlight", "lost in the rhythm", "chasing dreams", "find my way". 히트곡에서 거의 안 나오는 말이다.
- 형용사·부사는 거의 쓰지 않는다. 명사와 동사로. "-ly" 부사는 곡에 하나까지.
- 감정은 한 곡에 두세 번 직접 말한다(I miss you, I'm not okay). 그중 하나는 후렴에.
- 추임새(oh, yeah, ooh)는 괄호 코러스나 후렴 끝에만, 곡에 두세 번까지. 줄을 채우려고 넣지 않는다.
- 한 줄은 아래 [영어 실측]의 낱말 수·음절 수를 따른다(실측이 없으면 5~8낱말, 7~10음절).

[제목]
- 영어 제목은 짧게: 훅 그대로(2~5낱말), 낱말 하나, 짧은 명사구 중 하나. 모든 낱말 첫 글자를 대문자로(Title Case). 따옴표·마침표 없이.

[화법]
- 너에게 말하기를 기본으로(열에 다섯), 혼잣말 셋, 우리 둘. arc 첫 줄에 "화법: ○○".

[Suno 스타일 언어]
- style에 "sung in English, english lyrics"를 반드시 넣는다. 한국어 곡 기준의 "sung in Korean" 문구는 쓰지 않는다. 보컬은 원어민 발음이 나오도록 "native English pronunciation"을 넣는다.
"""

EN_YOUTUBE = """\
[유튜브] (영어 곡: 모두 영어로)
- situation: 제목 뒤에 붙일 듣는 상황 문구, 영어로 3~6낱말. 사람들이 검색하는 말: late night drive playlist, songs for a rainy day, chill pop for studying.
- shorts_title: 후렴 문장(hook)을 그대로 적는다. #shorts는 붙이지 않는다.
- 설명란은 가사, 만든 사람, 저작권, 해시태그뿐이고 모두 영어다. 소개 글이나 댓글 유도는 쓰지 않는다.
- hashtags: 12개, 영어, # 없이, 띄어쓰기 없이. 앞의 3개가 제목 위에 보이니 넓은 말부터(pop, sadsongs, latenightvibes). 시스템이 song, music, AI 같은 기본 태그를 붙이니 그 말들은 넣지 않는다.
- tags: 영어 검색 키워드 30~40개. 넓은 말(pop music, new music, love song, playlist)부터 좁은 말(곡의 기분, 상황)까지. 다른 가수 이름은 넣지 않는다.
"""

REVIEW_EN = """\
너는 영어 가사 편집자다. 작사가가 쓴 영어 가사에서 AI가 쓴 티, 번역투, 억지 각운, 상투어, 장면 서술, 설명을 걷어낸다. 원어민이 노래로 부를 말만 남긴다.
길이는 늘리지 않는다. 줄은 되도록 지우지 말고 고친다. 구간 태그와 순서, 태그 뒤 전개 지시, 후렴 줄 수, [Final Chorus]의 바뀐 줄은 지킨다.

차례대로 본다.
1. 추상과 뜻(강제): 장소·시각·생활 소품·동작 차례가 든 줄은 그 줄의 뜻만 남기고 사물을 지운다. 곡이 "어떤 하루"를 그리면 "어떤 마음"으로 바꾼다.
2. 도입과 후렴(강제): 1절 첫 두 줄과 후렴의 모든 줄이 선언·모순·고백·부탁·질문·뒤집기인지. 장면·배경으로 열면 가장 센 말을 첫 줄로 올린다.
3. 번역투와 콩글리시: 한국어를 옮긴 듯한 줄은 원어민 표현으로 바꾼다. 어색한 관사·전치사·시제를 고친다.
4. 각운: 운을 맞추려고 비튼 어순, 뜻 없는 낱말, 억지 운은 고친다. 절마다 운 패턴을 하나로 맞춘다. 완전운만 이어지면 근사운을 섞는다.
5. 강세: 줄 끝이 the/of/and/a 같은 약한 말이면 고친다. 훅의 마지막 낱말이 늘일 수 있는 소리인지 본다.
6. 상투어: neon, whispers, echoes, shadows, tapestry, symphony, shattered, ignite, embers, ethereal, velvet, silhouette, "dance in the rain", "stars align", "in this moment" 같은 말은 바꾼다.
7. 말투: 축약형이 없는 딱딱한 줄은 축약한다. 형용사·부사가 둘 넘는 줄은 줄인다. 추임새가 곡에 셋 넘으면 줄인다.
8. 감정어가 한 번도 없으면 후렴 한 줄을 직접 말하는 줄로 바꾼다.

JSON만 답한다: {"lyrics": "<고친 가사 전문>", "title": "<제목>", "share_line": "<가사 안에 그대로 있는 공유용 한 줄>", "changes": ["<바꾼 줄: 이유(한국어)>", ...]}
"""

RESEARCH_EN = """\
너는 영어권 팝 A&R이자 작사가다. 영어 곡을 쓰기 전에 레퍼런스를 조사한다.

웹 검색으로 다음을 찾아라.
1. 요청한 장르와 정서에 맞으면서 오래 사랑받은 영어 노래 6~10곡(빌보드·영국 차트 히트, 스트리밍 스테디셀러). 장르 요청이 없으면 팝·팝발라드·R&B·인디팝·록을 고루 본다.
2. 최근 몇 달 사이 스트리밍 차트와 쇼츠·틱톡에서 뜬 영어 곡 3~5곡.

곡마다 짧게: 제목 / 가수 / 연도, 훅이 무엇인지(다섯 낱말 이내로만 인용), 먹힌 이유(화자, 후렴 시점, 반복, 템포, 편곡 크기, 보컬 톤), 소리(드럼·베이스, 화성 악기, 후렴 멜로디 모양, 구간별 악기), 기승전결, 말투(축약·각운 패턴·한 줄 길이), 제목 형태.

마지막에 "이번 곡에 가져갈 원칙" 6~8개를 쓴다. 구조와 원리만 가져오고 표현은 베끼지 않는다. 가사 전문이나 긴 구절은 인용하지 않는다. 한국어로 쓴다.
"""

TRANSLATE_VERSION = 2  # 번역 규칙을 바꾸면 올린다. 영상을 다시 만들 때 옛 번역은 새로 옮긴다.

TRANSLATE = """\
너는 영어 노래를 한국어로 옮기는 작사가다. 결과는 유튜브 영상에서 영어 가사 바로 아래에 한 줄씩 뜨는 자막이다.
번역문이 아니라 한국 작사가가 이 곡의 뜻으로 처음부터 쓴 한국어 노랫말처럼 읽혀야 한다. 영어를 가리고 한국어만 읽어도 한 편의 가사여야 한다.

먼저 곡 전체를 읽고 정한다: 누가 누구에게 하는 말인가, 곡의 기분은 무엇인가, 말투(반말 평서가 기본, 존대 곡만 해요체) 하나.
그다음 줄마다 "이 줄이 결국 하는 말"을 한국어로 가장 짧고 자연스럽게 쓴다.

줄 맞춤
- 영어 한 줄에 한국어 한 줄, 순서와 줄 수는 그대로. 같은 영어 줄은 늘 같은 한국어다(후렴 반복).
- 영어 두 줄이 한 문장이면 한국어도 두 줄에 걸쳐 한 문장으로 이어 써도 된다. 줄마다 문장을 닫지 않는다.
- 한 줄 16자 안팎, 길어도 20자. 영어보다 짧게. 한눈에 읽혀야 한다.

AI 번역 티를 없애는 규칙 (가장 중요)
1. 줄 머리 접속사를 옮기지 않는다. And, So, But, 'Cause, Then, Or, Now를 "그리고, 그래서, 그러니, 그런데, 근데, 아니면, 이제"로 옮기면 번역투다. 거의 다 빼고, 꼭 필요할 때만 어미(-는데, -니까, -고)로 녹인다.
2. 주어를 쓰지 않는다. 나는, 난, 너는, 넌, 내가, 네가는 뜻이 헷갈릴 때만. "나는 돌을 내려놨어"는 "이제 내려놓을게"처럼.
3. 줄 끝을 섞는다. 모든 줄이 -어/-해/-야로 끝나면 번역 자막이다. 명사로 끊기, -는데, -지, -까, -고, -네, -던, -ㄹ게, 말줄임을 섞고, 같은 끝맺음은 세 줄 넘게 잇지 않는다.
4. 영어 비유를 낱말째 옮기지 않는다. 한국어에서 그 그림이 안 서면 뜻으로 바꾼다. "tell my hands"를 "손에게 말해", "I need the ground"를 "디딜 땅이 필요해", "almost mine"을 "거의 내 사람"으로 옮기지 않는다.
5. 사전 낱말 대신 노래 낱말. 감당하다, 알아차리다, 밀려오다, 필요하다, 존재, 순간, 감정 같은 설명하는 말보다 기본 동사와 쉬운 말(알다, 보다, 남다, 놓다, 버티다, 그립다).
6. 영어 문장 구조를 따르지 않는다. "~뿐일까", "~할 수만 있다면", "~하는 법을 배웠을 뿐", "~것만으로", "~가 다였는데", "~하기엔 충분했어" 같은 영어 구문의 직역 틀을 피한다.
7. 번역투 낱말: 나의·너의(→내·네), 그것은, 당신(존대 곡이 아니면), ~에 대해, ~를 통해, ~하는 것, 수동태, "~하는 중이야", "~할 수 있어" 남발.
8. 어색한 구어체(사용자 금지): 니/니가, "~부터 ~까지" 틀, 그냥·뭔가·진짜·되게·근데·완전·막, "~거든", "~잖아" 반복, "야" 부르기, "~한 거 있지".
9. 닳은 감성어: 소중한, 빛나는, 너라는, 그날의 우리. 음차(러브, 하트, 베이비) 금지.
10. 짧은 부정이 어색하면 긴 부정("~지 않아")으로.

후렴과 훅
- 제목 훅은 한국어로도 짧고 입에 붙게, 곡 내내 같은 말로. 훅이 반복되면 한국어도 반복한다.
- 추임새만 있는 줄(oh, yeah, ooh, baby)은 빈 문자열. baby·darling 부름은 빼거나 "너"로.

보기 (우리 곡의 줄, 나쁜 번역 → 좋은 번역)
- So I tell my hands what I can't say: "그래서 말 못 할 걸 손에게 말해" → "못 한 말은 손에 쥐고"
- I don't need the answer, I need the ground: "답은 필요 없어, 디딜 땅이 필요해" → "답 말고 발 디딜 곳이면 돼"
- Then one look and you were almost mine: "한 번 마주친 순간 넌 거의 내 사람" → "눈 한 번 마주쳤을 뿐인데"
- Or am I just a face you used to see?: "아니면 예전에 보던 얼굴일 뿐일까" → "그저 낯익은 얼굴이었을까"
- And I'd believe me too, if I could: "믿을 수만 있다면 나라도 믿겠지" → "나도 그 말을 믿고 싶어"
- I've been living like the ending's here: "끝이 벌써 온 것처럼 살아왔어" → "다 끝난 사람처럼 살았어"
- I just learned to live with half my soul: "반쪽 마음으로 사는 법을 배웠을 뿐" → "반만 남은 채로 버텼을 뿐"

JSON만 답한다: {"lines": ["<1번 줄>", "<2번 줄>", ...]} 줄 수는 받은 영어 줄 수와 정확히 같다.
"""

POLISH_KO = """\
너는 한국 노랫말 편집자다. 아래는 영어 노래 자막으로 쓸 한국어 가사 초안이다. 영어 원문은 뜻 확인용으로만 본다.
한국어 줄만 위에서 아래로 소리 내어 읽고, 한국 가요의 가사로 들리지 않는 줄을 고친다.

고칠 줄
- 번역문처럼 들리는 줄: 줄 머리 접속사(그리고·그래서·그러니·그런데·아니면), 주어(나는·난·너는·넌), 영어 구문 직역("~뿐일까", "~할 수만 있다면", "~것만으로", "~하기엔 충분했어", "~가 다였는데"), 낱말째 옮긴 비유, 사전 낱말.
- 줄 끝이 -어/-해/-야로 세 줄 넘게 이어지는 곳: 명사로 끊기, -는데, -지, -까, -고, -ㄹ게로 바꿔 숨을 고른다.
- 20자를 넘는 줄, 한눈에 안 읽히는 줄.
- 어색한 구어체(니/니가, ~부터 ~까지, 그냥·뭔가·진짜·되게·근데·완전·막, ~거든, ~잖아 반복).
- 앞뒤 줄과 말투가 다른 줄.

지킬 것
- 줄 수와 순서는 그대로. 같은 영어 줄은 같은 한국어. 빈 줄은 빈 줄로.
- 이미 자연스러운 줄은 그대로 둔다. 뜻을 새로 보태지 않는다.

JSON만 답한다: {"lines": [...]} 줄 수는 받은 줄 수와 정확히 같다.
"""


def is_english(meta_or_lang) -> bool:
    if isinstance(meta_or_lang, dict):
        lang = meta_or_lang.get("lang") or (meta_or_lang.get("request") or {}).get("lang", "")
    else:
        lang = meta_or_lang or ""
    return str(lang).lower() in ("en", "english", "영어")


def stats_text(genre: str = "") -> str:
    """영어 히트곡 실측을 프롬프트 문장으로. 요청 장르 묶음과 전체."""
    if not EN_STATS.exists():
        return ""
    try:
        r = json.loads(EN_STATS.read_text(encoding="utf-8"))
    except ValueError:
        return ""
    picks = [("전체", r.get("total") or {})]
    for g, s in (r.get("groups") or {}).items():
        if genre and genre in (s.get("members") or []):
            picks.append((g, s))
    recent = (r.get("decades") or {}).get("2020년대")
    if recent:
        picks.append(("2020년대", recent))
    lines = []
    for name, s in picks:
        if not s:
            continue
        lines.append(
            f"- {name}(히트곡 {s['songs']}곡 {s['lines']}줄): 곡당 줄 {s['lines_per_song_median']}(서로 다른 줄 {s['unique_lines_median']}), "
            f"줄당 낱말 중앙값 {s['words_median']}·음절 {s['syllables_median']}, 3낱말 이하 {s['short_le3w_pct']}%, 10낱말 초과 {s['long_gt10w_pct']}%, "
            f"앞 세 줄과 각운 {s['rhyme_pct']}%·모음운 {s['assonance_pct']}%·같은 끝낱말 {s['same_end_word_pct']}%, 반복 줄 {s['repeat_pct']}%, "
            f"제목이 가사에 든 곡 {s['title_in_lyrics_pct']}%(곡당 {s['title_hits_median']}번), 축약 든 줄 {s['contraction_pct']}%, 추임새 {s['filler_pct']}%, "
            f"you {s['you_pct']}%·I {s['i_pct']}%·we {s['we_pct']}%, 물음 {s['question_pct']}%, 명령 {s['imperative_pct']}%, 감정어 {s['emotion_pct']}%, "
            f"AI 상투어 1000줄당 {s['ai_cliche_per_1000']}.")
    if not lines:
        return ""
    head = "유행한 영어 노래들의 실측이다. 이 곡의 줄 길이·각운·반복·축약·인칭·감정어 비율을 요청 장르 묶음(없으면 전체)에 맞춘다. 2020년대 값은 요즘 곡의 방향이다. 곡당 줄 수는 반복 후렴을 모두 적은 길이라 따르지 않는다(이 곡의 길이는 [길이와 구조]대로)."
    return "\n\n[영어 실측]\n" + head + "\n" + "\n".join(lines)


def guide_text() -> str:
    g = w._read(EN_GUIDE)
    return "\n\n[영어 작사법]\n" + g if g else ""


def system(genre: str = "") -> str:
    """영어 곡 작사 시스템 프롬프트: 영어 규칙 + 한국어 곡과 같은 소리·스타일·태그·사진 절 + 영어 유튜브 절."""
    base = w.SYSTEM
    shared = base[base.index("[소리 설계]"):base.index("[유튜브]")]
    text = SYSTEM_EN_HEAD + guide_text() + stats_text(genre) + "\n\n" + shared + "\n" + EN_YOUTUBE
    hooks = w._read(w.HOOKS)
    if hooks:
        text += "\n\n[후렴과 반복(한국어 곡 조사지만 구조 원리는 같다)]\n" + hooks
    if w.is_instrumental(genre):
        text += "\n\n" + w.MODE_INSTRUMENTAL
    elif genre in w.KIDS_GENRES:
        text += "\n\n" + w.MODE_KIDS + "\n(영어 곡이니 가사는 영어 동요·자장가·캐럴의 말로 쓴다.)"
    text += w._sound(genre)
    return text


def review_system(genre: str = "") -> str:
    return REVIEW_EN + guide_text() + stats_text(genre)


def research_system() -> str:
    return RESEARCH_EN


def youtube_system() -> str:
    return ("너는 유튜브 채널 편집자다. 아래 영어 노래의 제목과 가사가 확정됐다. 그에 맞는 유튜브 글을 영어로 쓴다. "
            "담백하게, 과장과 감탄사 없이. JSON만 답한다. story만 한국어 한 문장.\n\n" + EN_YOUTUBE)


def _lines_call(system: str, content: str, n: int, label: str, effort: str) -> list[str]:
    schema = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "string"}}},
              "required": ["lines"], "additionalProperties": False}
    for attempt in range(2):
        t0 = time.time()
        with anthropic.Anthropic().beta.messages.stream(
            model=w.MODEL, max_tokens=16000, system=system, betas=w.BETAS, fallbacks="default",
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": content}],
        ) as stream:
            response = stream.get_final_message()
        w._check(response)
        w.took(label, t0)
        out = [x.strip() for x in json.loads(next(b.text for b in response.content if b.type == "text"))["lines"]]
        if len(out) == n:
            return out
        content += f"\n\n앞 답은 {len(out)}줄이었다. 정확히 {n}줄이어야 한다."
    raise RuntimeError("번역 줄 수가 가사 줄 수와 맞지 않습니다")


def _same_for_same(lyric_lines: list[str], out: list[str]) -> list[str]:
    """같은 영어 줄은 같은 번역으로 맞춘다(후렴이 매번 다르게 뜨지 않게)."""
    first: dict[str, str] = {}
    for i, en in enumerate(lyric_lines):
        key = en.strip().lower()
        if key in first and first[key]:
            out[i] = first[key]
        else:
            first[key] = out[i]
    return out


def translate(title: str, lyric_lines: list[str]) -> list[str]:
    """영어 가사 줄(구간 태그·괄호 코러스 제외)을 자연스러운 한국어 자막 줄로. 옮긴 뒤 한국어만 읽고 한 번 더 다듬는다."""
    if not lyric_lines:
        return []
    n = len(lyric_lines)
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(lyric_lines))
    draft = _lines_call(TRANSLATE, f"[제목]\n{title}\n\n[영어 가사 {n}줄]\n{numbered}\n\n번호는 빼고 같은 순서로 {n}줄을 돌려준다.",
                        n, "번역", "high")
    draft = _same_for_same(lyric_lines, draft)
    pairs = "\n".join(f"{i + 1}. {ko}    ← {en}" for i, (en, ko) in enumerate(zip(lyric_lines, draft)))
    try:
        final = _lines_call(POLISH_KO, f"[제목]\n{title}\n\n[한국어 초안 ← 영어 원문, {n}줄]\n{pairs}\n\n번호와 영어는 빼고 한국어 {n}줄을 돌려준다.",
                            n, "번역 다듬기", "high")
    except Exception as e:  # 다듬기가 실패해도 초안은 쓴다
        print(f"번역 다듬기 실패, 초안 사용: {e}")
        return draft
    return _same_for_same(lyric_lines, final)