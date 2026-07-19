# 명함 챗봇 설치 및 실행 가이드

## 1단계: 파이썬 패키지 설치

```bash
cd "/Users/chooyeanchan/클로드코드/agent_card messenger"
pip install -r requirements.txt
```

## 2단계: .env 파일 만들기

```bash
cp .env.example .env
```

`.env` 파일을 열어서 아래 값들을 채워주세요:

| 항목 | 준비 방법 |
|------|-----------|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 @BotFather → /newbot |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `GMAIL_ADDRESS` | 본인 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | Google 계정 → 보안 → 앱 비밀번호 (2단계 인증 필요) |
| `GOOGLE_SHEET_ID` | 스프레드시트 URL 중간의 긴 ID |
| `GOOGLE_CREDENTIALS_FILE` | 서비스 계정 JSON 파일명 |
| `MY_CARD_IMAGE_PATH` | 본인 명함 이미지 파일명 |
| `MY_EMAIL_INTRO` | 이메일 소개 문구 |

## 3단계: 파일 배치

이 폴더에 다음 파일들을 넣어주세요:
- `credentials.json` — Google Cloud 서비스 계정 키 파일
- `my_card.jpg` — 본인 명함 이미지

## 4단계: Google Sheets 헤더 초기 설정 (최초 1회)

```bash
python sheets.py
```

## 5단계: 봇 실행

```bash
python bot.py
```

## Google Sheets 서비스 계정 설정 상세

1. https://console.cloud.google.com 접속
2. 새 프로젝트 만들기 (예: `card-bot`)
3. `API 및 서비스` → `라이브러리` → `Google Sheets API` 검색 → 활성화
4. `사용자 인증 정보` → `사용자 인증 정보 만들기` → `서비스 계정`
5. 서비스 계정 이름 입력 → `만들고 계속하기` → `완료`
6. 생성된 서비스 계정 클릭 → `키` 탭 → `키 추가` → `새 키 만들기` → `JSON`
7. 다운로드된 파일 이름을 `credentials.json`으로 바꿔서 이 폴더에 넣기
8. 서비스 계정 이메일(예: `card-bot@card-bot-xxxxx.iam.gserviceaccount.com`)을
   Google 스프레드시트에서 `공유` → 편집자로 추가
