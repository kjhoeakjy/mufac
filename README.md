# mufac

Suno로 만든 노래를 유튜브 영상까지 만드는 개인용 공장.
사람은 Suno에서 곡을 듣고 고르기만 하고, 나머지는 GitHub Actions가 한다.

## 하루 흐름

1. **새 곡** — [Actions → 새 곡](../../actions/workflows/new-song.yml) → Run workflow.
   생각이나 상황을 한 줄 적어도 되고 비워도 된다. 매일 아침 8시에도 한 곡씩 자동으로 준비된다.
   Claude가 후렴 후보 5개를 뽑고 하나로 가사, Suno 스타일, 사진까지 만들어 `songs/<날짜-번호>/`에 저장한다.
2. **Suno** — 그 폴더의 README에서 Style, Exclude, Title, Lyrics를 복사해 [Suno](https://suno.com/create) Custom 모드에 붙여넣는다.
3. **고르기** — 나온 곡 중 하나를 MP3로 받아 같은 폴더에 올린다(폴더 README의 "이 폴더에 올리세요" 링크).
4. **자동** — 올리면 [영상 만들기](../../actions/workflows/produce.yml)가 시작된다.
   가사 위치를 음성 인식으로 찾고, 본편(16:9)과 쇼츠(9:16, 첫 후렴), 썸네일을 만들어 유튜브에 비공개로 올린다.
5. **공개** — [YouTube Studio](https://studio.youtube.com)에서 확인하고 공개로 바꾼다.

영상 파일은 각 실행 결과 페이지 아래 `videos`에서 받을 수 있다(30일 보관).

## 고치고 싶을 때

| 하고 싶은 것 | 방법 |
|---|---|
| 자막 타이밍 수정 | 곡 폴더의 `timing.lrc`에서 시간을 고치고 영상 만들기를 곡 이름으로 다시 실행 |
| 사진 바꾸기 | `photo.jpg`(가로), `photo_v.jpg`(세로)를 원하는 사진으로 덮어쓰고 다시 실행 |
| 가사 수정 | `song.yaml`의 `lyrics`를 고치고 `timing.lrc`를 지운 뒤 다시 실행 |
| 활동명, 제목 형식, 공개 범위 | 맨 위 `config.yaml` |

## 설정

키 넣는 법은 [SETUP.md](SETUP.md).

## 폴더

```
config.yaml          활동명, 공개 범위, 사진 방식
songs/<slug>/        곡 하나: song.yaml, README.md, photo.jpg, photo_v.jpg, 노래 파일, timing.lrc
mufac/               코드 (write: 가사, photo: 사진, align: 자막 타이밍, render: 영상, youtube: 업로드)
assets/fonts/        자막 글꼴 (고운바탕, Noto Sans KR, SIL Open Font License)
```
