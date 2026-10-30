# mufac

클래식 멜로디 위에 쓴 요즘 노래. Suno로 만든 곡을 유튜브 영상까지 만드는 개인용 공장.
사람은 Suno에서 곡을 듣고 고르기만 하고, 나머지는 GitHub Actions가 한다.

대시보드: https://kjhoeakjy.github.io/mufac/studio/

## 하루 흐름

1. **새 곡** — 대시보드에서 키워드를 적고 만들기, 또는 자동 생성. 매일 아침 8시에도 한 곡씩 준비된다.
   Claude가 비슷한 정서의 히트곡을 조사하고, 노래의 사연에 가장 깊이 이어지는 클래식 원곡을 고른 뒤,
   그 선율의 호흡에 맞춰 가사, Suno 스타일, 사진을 만들어 `songs/<날짜-번호>/`에 저장한다.
   원곡 멜로디는 `melody.mp3`(반주 포함), `melody-solo.mp3`(선율만)로 같이 만들어진다.
2. **Suno** — [Suno](https://suno.com/create)에서 Upload Audio로 `melody.mp3`를 올리고 Cover를 고른 뒤
   대시보드의 Style, Exclude, Title, Lyrics를 붙여넣는다. 곡 이미지는 `cover.jpg`.
3. **고르기** — 나온 곡 중 하나를 MP3로 받아 대시보드의 곡 칸에 놓는다.
4. **자동** — 영상 만들기가 시작된다. 가사 위치를 음성 인식으로 찾고 본편(16:9), 쇼츠(9:16), 썸네일을 만든다.
5. **유튜브** — 대시보드의 업로드 버튼. 제목, 설명, 해시태그, 태그, 재생목록이 채워져 비공개로 올라간다.
   [YouTube Studio](https://studio.youtube.com)에서 확인하고 공개로 바꾼다.

## 가사의 결

- 주제는 사랑, 어른, 아픔. 누구나 겪는 일만 쓴다. 꼭 슬플 필요는 없다.
- 레퍼런스: `config.yaml`의 `lyric_reference`에 적힌 밴드들.
  [레퍼런스 학습](../../actions/workflows/learn.yml)을 실행하면 팀마다 노랫말 프로필이 `assets/lyrics/`에 만들어지고,
  새 곡을 쓸 때 그 원리를 읽는다. 표현은 베끼지 않는다.
- 존댓말 어미("-해요", "-거예요")를 줄마다 반복하지 않는다. 반말, 끊긴 문장, 입말이 기본.

## 클래식 원곡

- `assets/classical/catalog.yaml`에 작곡가 사망 1955년 이전, 작곡 1930년 이전인 곡만 둔다(규칙은 `mufac/classical.py`).
  둘 중 하나라도 어긋나면 자동으로 빠진다.
- 선율은 공개 악보 저장소 [Mutopia](https://www.mutopiaproject.org)의 MIDI에서 만든다.
  [클래식 악보 수집](../../actions/workflows/collect.yml)이 카탈로그의 곡 폴더에서 받아 `assets/classical/midi/`에 둔다.
- 악보가 없는 곡은 목록에만 있고 고를 수 없다. 곡을 더 넣으려면 카탈로그에 배경 이야기와 Mutopia 폴더를 적고 수집을 실행한다.

## 고치고 싶을 때

| 하고 싶은 것 | 방법 |
|---|---|
| 자막 타이밍 수정 | 곡 폴더의 `timing.lrc`에서 시간을 고치고 영상 만들기를 곡 이름으로 다시 실행 |
| 사진 바꾸기 | `photo.jpg`(가로), `photo_v.jpg`(세로), `cover.jpg`(정사각)를 덮어쓰고 다시 실행 |
| 가사 수정 | `song.yaml`의 `lyrics`를 고치고 `timing.lrc`를 지운 뒤 다시 실행 |
| 원곡 직접 고르기 | 대시보드의 클래식 선택, 또는 새 곡 실행의 `classic`에 곡 id |
| 레퍼런스 밴드 바꾸기 | `config.yaml`의 `lyric_reference`를 고치고 레퍼런스 학습 실행 |
| 활동명, 제목 형식, 공개 범위 | `config.yaml` |

## 설정

키 넣는 법은 [SETUP.md](SETUP.md).

## 폴더

```
config.yaml              활동명, 공개 범위, 레퍼런스, 사진 방식
songs/<slug>/            곡 하나: song.yaml, README.md, research.md, photo*.jpg, cover.jpg, melody*.mp3, 노래 파일, timing.lrc
assets/classical/        catalog.yaml(원곡 목록과 배경), midi/(수집한 악보)
assets/lyrics/           레퍼런스 밴드별 노랫말 프로필
assets/fonts/            자막 글꼴 (고운바탕, Noto Sans KR, SIL Open Font License)
mufac/                   코드 (write: 가사, learn: 레퍼런스, classical·midi: 원곡, photo: 사진, align: 자막, render: 영상, youtube: 업로드)
tools/                   악보 수집 스크립트
docs/studio/             대시보드 (GitHub Pages)
```
