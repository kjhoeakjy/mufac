"""레퍼런스 작사가·밴드의 노랫말을 공부해 프로필로 남긴다.

config.yaml의 lyric_reference에 적힌 이름마다 웹 검색으로 대표곡, 말투, 소재, 구조를 조사하고
assets/lyrics/<이름>.md 에 "가져갈 원리" 중심으로 정리한다. 가사 전문은 담지 않는다(원리만, 표현은 베끼지 않는다).
write.py가 곡을 쓸 때 이 파일들을 프롬프트에 붙인다.
"""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import anthropic

from .song import config
from .write import BETAS, KST, MODEL, _check

LYRICS_DIR = Path(__file__).resolve().parent.parent / "assets" / "lyrics"

PROFILE = """\
너는 한국 대중음악 평론가이자 작사가다. 한 아티스트의 노랫말을 공부해서, 다른 작사가가 그 "결"을 원리로 배울 수 있는 프로필을 쓴다.

웹 검색으로 대표곡 8~12곡의 가사, 가사 해석 글, 인터뷰, 리뷰, 댓글 반응을 찾아 읽는다.
그다음 아래 항목으로 마크다운 프로필을 쓴다. 각 항목은 구체적으로, 그러나 짧게.

# <아티스트 이름>
## 한 줄 요약
이 팀 노랫말의 결을 한 문장으로.
## 대표곡과 제목
- 곡 제목 (연도): 제목의 형태(단어 하나/명사구/반말 문장/존댓말 문장/영어 등)와 제목이 가사 어디서 나오는지
## 말투
- 종결어미의 분포(반말 -어/-아/-지/-네/-야, 명사로 끊김, 존댓말, 영어 섞임)와 실제 예시 어미
- 문장 길이, 끊어 말하기, 입말('그냥', '뭐', '있잖아' 같은)의 쓰임
- 화자가 누구에게 말하는지(너, 나 자신, 불특정 다수)
## 소재와 시선
- 자주 쓰는 소재(사물, 장소, 시간대, 계절)와 그것을 보는 태도(다정함, 자조, 냉소, 능청, 분노, 유머)
- 감정을 직접 말하는지, 장면으로 보여주는지
## 구조와 리듬
- 후렴의 길이와 반복 방식, 훅이 만들어지는 방법, 절과 후렴의 관계
- 운, 리듬, 낱말을 나란히 놓는 버릇
## 왜 사람 같은가
- 이 노랫말이 AI가 쓴 글과 다르게 읽히는 이유 5가지. 어색함, 비문, 과장, 사투리, 유머, 갑작스러운 전환 같은 것들.
## 가져갈 원리 10가지
- 다른 곡에 적용할 수 있는 구체적 규칙. "~한다" 꼴로.
## 피할 것
- 이 팀을 흉내 낼 때 생기는 실패(표현 베끼기, 특정 단어 남용 등).

규칙: 가사는 한 줄에 10자 이내로만 인용한다. 가사 전문이나 긴 구절은 절대 옮기지 않는다. 사실(연도, 곡명)은 검색으로 확인한 것만 쓴다.
한국어로 쓴다. 전체 1200자 안팎.
"""


def references() -> list[str]:
    ref = config().get("lyric_reference") or "잔나비"
    if isinstance(ref, str):
        ref = re.split(r"[,\n]", ref)
    return [r.strip() for r in ref if r and r.strip()]


def slug(name: str) -> str:
    return re.sub(r"[^\w가-힣]+", "_", name).strip("_")


def profile_path(name: str) -> Path:
    return LYRICS_DIR / f"{slug(name)}.md"


def learn(name: str) -> str:
    client = anthropic.Anthropic()
    today = dt.datetime.now(KST).strftime("%Y년 %m월 %d일")
    first = {"role": "user", "content": f"오늘은 {today}.\n\n아티스트: {name}\n이 팀(또는 작사가)의 노랫말 프로필을 써라."}
    messages = [first]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 14,
              "user_location": {"type": "approximate", "country": "KR", "timezone": "Asia/Seoul"}}]
    for _ in range(6):
        with client.beta.messages.stream(
            model=MODEL, max_tokens=20000, system=PROFILE, betas=BETAS, fallbacks="default",
            output_config={"effort": "high"}, tools=tools, messages=messages,
        ) as stream:
            response = stream.get_final_message()
        if response.stop_reason == "pause_turn":
            messages = [first, {"role": "assistant", "content": response.content}]
            continue
        _check(response)
        text = "\n".join(b.text for b in response.content if b.type == "text").strip()
        if text:
            return text
    raise RuntimeError(f"{name} 프로필을 만들지 못했습니다.")


def learn_all(names: list[str] | None = None, *, force: bool = False) -> list[Path]:
    LYRICS_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for name in names or references():
        path = profile_path(name)
        if path.exists() and not force:
            print(f"있음  {name}")
            continue
        text = learn(name)
        path.write_text(text + f"\n\n(정리: {dt.datetime.now(KST):%Y-%m-%d})\n", encoding="utf-8")
        print(f"작성  {name} → {path.relative_to(LYRICS_DIR.parent.parent)}")
        out.append(path)
    return out


def profiles_text(limit_chars: int = 24000) -> str:
    """곡을 쓸 때 프롬프트에 붙일 프로필 묶음. 레퍼런스 순서대로, 너무 길면 뒤를 자른다."""
    parts = []
    for name in references():
        p = profile_path(name)
        if p.exists():
            parts.append(p.read_text(encoding="utf-8").strip())
    text = "\n\n---\n\n".join(parts)
    return text[:limit_chars]
