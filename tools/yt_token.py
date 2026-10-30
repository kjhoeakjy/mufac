"""유튜브 refresh token 발급. 내 컴퓨터에서 한 번 실행한다.

    pip install google-auth-oauthlib
    python tools/yt_token.py

브라우저가 열리면 업로드할 채널의 구글 계정으로 로그인한다. 끝나면 refresh token이 출력된다.
그 값을 GitHub 저장소 Settings → Secrets → YT_REFRESH_TOKEN 에 넣는다. 채팅이나 파일에 적지 않는다.

redirect_uri_mismatch가 나오면 Google Cloud → 클라이언트 → 해당 클라이언트의 승인된 리디렉션 URI에
http://localhost:8765/ 를 추가하고 저장한다(데스크톱 앱 유형이면 필요 없다).

토큰이 일주일마다 끊기면 Google Cloud 콘솔 → OAuth 동의 화면 → 게시 상태가 "테스트"인 것이다.
"프로덕션"으로 바꾼 뒤 이 스크립트로 다시 발급하면 만료되지 않는다.
"""

import os
import sys


def main() -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("pip install google-auth-oauthlib 후 다시 실행")
    cid = os.environ.get("YT_CLIENT_ID") or input("client id: ").strip()
    secret = os.environ.get("YT_CLIENT_SECRET") or input("client secret: ").strip()
    flow = InstalledAppFlow.from_client_config(
        {"installed": {"client_id": cid, "client_secret": secret,
                       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                       "token_uri": "https://oauth2.googleapis.com/token",
                       "redirect_uris": ["http://localhost:8765/"]}},
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    # 웹 애플리케이션 유형 클라이언트면 승인된 리디렉션 URI에 http://localhost:8765/ 를 넣어야 한다.
    creds = flow.run_local_server(port=8765, access_type="offline", prompt="consent")
    print("\nYT_REFRESH_TOKEN =", creds.refresh_token)


if __name__ == "__main__":
    main()
