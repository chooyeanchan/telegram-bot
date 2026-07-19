"""
최초 1회만 실행하세요.
Google 로그인 창이 뜨면 허용하면 token.json이 생성됩니다.
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")

if not os.path.exists(CREDENTIALS_FILE):
    print("❌ credentials.json 파일이 없습니다.")
    print("Google Cloud Console에서 OAuth 클라이언트 ID를 다운로드해 이 폴더에 넣어주세요.")
    print("자세한 방법은 README.md를 참고하세요.")
    exit(1)

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
creds = flow.run_local_server(port=0)

token_path = os.path.join(os.path.dirname(__file__), "token.json")
with open(token_path, "w") as f:
    f.write(creds.to_json())

print("✅ 인증 완료! token.json이 생성되었습니다.")
print("이제 'python main.py'로 봇을 실행하세요.")
