# mufac

Suno로 만든 노래를 유튜브 영상까지 만드는 개인용 공장.
사람은 Suno에서 곡을 듣고 고르기만 하고, 나머지는 GitHub Actions가 한다.

대시보드: https://kjhoeakjy.github.io/mufac/studio/

## 하루 흐름

1. **새 곡** — 대시보드에서 제목, 키워드, 원하는 내용, 장르, 곡 스타일을 적거나 고르고 만들기. 비운 칸은 알아서 채운다. 매일 아침 8시에도 한 곡씩 준비된다.
   Claude가 비슷한 정서의 히트곡을 조사한 뒤 가사, Suno 스타일, 배경 그림을 만들어 `songs/<날짜-번호>/`에 저장한다.
2. **Suno** — [Suno](https://suno.com/create)에서 Custom 모드를 켜고 대시보드의 Style, Exclude, Title, Lyrics를 붙여넣는다. 곡 이미지는 `cover.jpg`.
   모델은 v5 이상, Weirdness는 낮게, Style Influence는 높게, 프롬프트 보정(Enhance)은 끈다. 한 번에 두 곡이 나오니 서너 번 돌려 고른다.
   유료 플랜(Pro 이상)에서 만든 곡만 소유권과 상업적 이용 권리가 생긴다. 무료 플랜 곡은 유튜브 수익화가 안 된다.
3. **고르기** — 나온 곡 중 하나를 MP3로 받아 대시보드의 곡 칸에 놓는다.
4. **자동** — 영상 만들기가 시작된다. 가사 위치를 음성 인식으로 찾고 본편(16:9), 쇼츠(9:16), 썸네일을 만든다.
   배경 그림 한 장은 움직이지 않고, 처음에 제목이 가운데 떴다가 가사만 바뀐다.
5. **유튜브** — 대시보드의 업로드 버튼. 제목, 설명, 해시태그, 태그, 재생목록이 채워져 비공개로 올라간다.
   [YouTube Studio](https://studio.youtube.com)에서 확인하고 공개로 바꾼다.
   설명란에는 제작자 크레딧, © 연도 채널명, 무단 복제 금지 문구가 들어가고, 유튜브의 AI 생성 콘텐츠 표시(변경·합성 콘텐츠)도 자동으로 켜진다.
   공개 전 48시간 안에 Studio의 저작권 탭에 소유권 주장(Content ID 매치)이 없는지 한 번 본다.

## 가사의 결

- 주제는 사랑, 어른, 아픔. 누구나 겪는 일만 쓴다. 꼭 슬플 필요는 없다.
- 레퍼런스: `config.yaml`의 `lyric_reference`에 적힌 밴드들.
  [레퍼런스 학습](../../actions/workflows/learn.yml)을 실행하면 팀마다 노랫말 프로필이 `assets/lyrics/`에 만들어지고,
  새 곡을 쓸 때 그 원리를 읽는다. 표현은 베끼지 않는다.
- 존댓말 어미("-해요", "-거예요")를 줄마다 반복하지 않는다. 반말, 끊긴 문장, 입말이 기본.

## 고치고 싶을 때

| 하고 싶은 것 | 방법 |
|---|---|
| 자막 타이밍 수정 | 곡 폴더의 `timing.lrc`에서 시간을 고치고 영상 만들기를 곡 이름으로 다시 실행 |
| 배경 그림 바꾸기 | `photo.jpg`(가로), `photo_v.jpg`(세로), `cover.jpg`(정사각)를 덮어쓰고 영상 다시 제작 |
| 가사 수정 | `song.yaml`의 `lyrics`를 고치고 `timing.lrc`를 지운 뒤 다시 실행 |
| 제목·가사 바꾸기 | 대시보드 곡 상단의 제목·가사 수정 (유튜브 글이 다시 만들어짐) |
| 유튜브 글 바꾸기 | 대시보드 유튜브 칸의 글 수정 (업로드에 그대로 쓰임) |
| 레퍼런스 밴드 바꾸기 | `config.yaml`의 `lyric_reference`를 고치고 레퍼런스 학습 실행 |
| 활동명, 제목 형식, 공개 범위 | `config.yaml` |

## 설정

키 넣는 법은 [SETUP.md](SETUP.md).

## 폴더

```
config.yaml              활동명, 공개 범위, 레퍼런스, 사진 방식
songs/<slug>/            곡 하나: song.yaml, README.md, research.md, photo*.jpg, cover.jpg, 노래 파일, timing.lrc
assets/lyrics/           레퍼런스 밴드별 노랫말 프로필
assets/fonts/            자막 글꼴 (Pretendard, SIL Open Font License)
mufac/                   코드 (write: 가사, learn: 레퍼런스, photo: 사진, align: 자막, render: 영상, youtube: 업로드)
docs/studio/             대시보드 (GitHub Pages)
```

## 유튜브 토큰이 끊길 때

업로드가 `invalid_grant: Token has been expired or revoked`로 실패하면 refresh token이 만료된 것이다.
Google Cloud 콘솔의 OAuth 동의 화면 게시 상태가 "테스트"면 토큰이 7일마다 끊기므로 "프로덕션"으로 바꾼다.
그다음 내 컴퓨터에서 `python tools/yt_token.py`를 실행해 새 토큰을 받고, 저장소 Secrets의 `YT_REFRESH_TOKEN`을 바꾼다.
