# 설정

키는 저장소 **Settings → Secrets and variables → Actions → New repository secret**에 넣는다. 채팅이나 파일에 적지 않는다.

| 이름 | 용도 | 필수 |
|---|---|---|
| `ANTHROPIC_API_KEY` | 후렴, 가사, Suno 스타일 | 필수 |
| `OPENAI_API_KEY` | 곡 분위기 사진 생성 | 사진용 (없으면 Pexels나 단색 배경) |
| `PEXELS_API_KEY` | 실제 사진 검색 (`config.yaml`의 `photo_source: pexels`) | 선택 |
| `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN` | 유튜브 업로드 | 업로드용 |

## 유튜브 키 받기

1. [Google Cloud 콘솔](https://console.cloud.google.com)에서 새 프로젝트(mufac)를 만든다.
2. "YouTube Data API v3"를 검색해 **사용**.
3. "OAuth 동의 화면" → 시작하기. 앱 이름 mufac, 본인 이메일, 대상 **외부**.
4. **브랜딩**: 앱 이름, 사용자 지원 이메일, 개발자 연락처 이메일. 게시 버튼이 꺼져 있으면 아래도 채운다.
   - 앱 홈페이지: `https://kjhoeakjy.github.io/mufac/`
   - 개인정보처리방침: `https://kjhoeakjy.github.io/mufac/privacy.html`
   - 승인된 도메인: `kjhoeakjy.github.io`
5. **대상** → 앱 게시(프로덕션). 게시 전 테스트 상태에서는 테스트 사용자에 본인을 넣어야 하고, 토큰이 7일마다 만료된다.
6. **클라이언트** → 클라이언트 만들기 → 웹 애플리케이션. 승인된 리디렉션 URI `https://developers.google.com/oauthplayground`. 클라이언트 ID와 보안 비밀번호를 복사.
7. [OAuth Playground](https://developers.google.com/oauthplayground) → 톱니바퀴 → Use your own OAuth credentials 체크, ID와 비밀번호 입력.
8. 왼쪽 입력칸에 `https://www.googleapis.com/auth/youtube` → Authorize APIs → 채널 계정으로 로그인 → "확인되지 않은 앱"이면 고급 → 이동 → 허용.
9. Exchange authorization code for tokens → **Refresh token** 복사.
10. Secrets에 `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`으로 저장.

알아둘 것

- 구글 심사를 받지 않은 앱으로 올린 영상은 공개로 보내도 **비공개로 잠긴다**. Studio에서 공개로 바꾼다.
- 하루 업로드 한도는 대략 6개(API 할당량 10,000 중 업로드 1회 1,600).
- 썸네일 지정은 채널 전화번호 인증([youtube.com/verify](https://www.youtube.com/verify))이 있어야 된다. 없으면 건너뛴다.
- 업로드할 때 "AI로 변경되거나 합성된 콘텐츠" 표시를 자동으로 켠다.
