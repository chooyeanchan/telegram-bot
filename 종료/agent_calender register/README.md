# 텔레그램 캘린더 등록 봇 — 설정 가이드

---

## 필요한 것 3가지

| 항목 | 발급처 |
|------|--------|
| Telegram Bot Token | 텔레그램 BotFather |
| Gemini API Key | Google AI Studio |
| Google OAuth credentials.json | Google Cloud Console |

---

## STEP 1 — Telegram Bot Token 발급

1. 텔레그램 앱에서 **@BotFather** 검색 후 대화 시작
2. `/newbot` 입력
3. 봇 이름 입력 (예: `내 캘린더봇`)
4. 봇 아이디 입력 — 반드시 `bot`으로 끝나야 함 (예: `my_calendar_bot`)
5. 완료되면 이런 메시지가 옴:

```
Done! Congratulations on your new bot...
Token: 7412345678:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

6. `Token:` 뒤의 값을 복사해 `.env` 파일에 붙여넣기

---

## STEP 2 — Gemini API Key 발급

1. https://aistudio.google.com 접속 (Google 계정 로그인)
2. 왼쪽 메뉴에서 **"Get API key"** 클릭
3. **"Create API key"** 클릭
4. 생성된 키 복사해 `.env` 파일에 붙여넣기

> 무료 플랜으로 충분합니다 (분당 15회 요청 무료)

---

## STEP 3 — Google Calendar 연동 (credentials.json 발급)

### 3-1. Google Cloud Console 프로젝트 생성

1. https://console.cloud.google.com 접속
2. 상단 프로젝트 선택 → **"새 프로젝트"**
3. 프로젝트 이름 입력 (예: `calendar-bot`) → **만들기**

### 3-2. Google Calendar API 활성화

1. 왼쪽 메뉴 → **"API 및 서비스"** → **"라이브러리"**
2. 검색창에 `Google Calendar API` 입력
3. **"사용 설정"** 클릭

### 3-3. OAuth 동의 화면 설정

1. **"API 및 서비스"** → **"OAuth 동의 화면"**
2. **"외부"** 선택 → **"만들기"**
3. 앱 이름 (아무거나), 지원 이메일 (내 이메일) 입력
4. **"저장 후 계속"** 3번 눌러서 완료
5. **"테스트 사용자"** 탭 → **"사용자 추가"** → 내 구글 이메일 추가

### 3-4. OAuth 클라이언트 ID 생성

1. **"API 및 서비스"** → **"사용자 인증 정보"**
2. **"사용자 인증 정보 만들기"** → **"OAuth 클라이언트 ID"**
3. 애플리케이션 유형: **"데스크톱 앱"** 선택
4. 이름 입력 → **"만들기"**
5. **"JSON 다운로드"** 클릭
6. 다운로드된 파일을 이 프로젝트 폴더에 `credentials.json` 이름으로 저장

---

## STEP 4 — 환경 설정

### .env 파일 생성

```bash
cp .env.example .env
```

`.env` 파일을 열어 값 입력:

```
TELEGRAM_BOT_TOKEN=7412345678:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALLOWED_CHAT_ID=본인_텔레그램_chat_id
```

`ALLOWED_CHAT_ID`를 설정하지 않으면 봇이 시작되지 않습니다(필수값). 본인 chat ID는 [@userinfobot](https://t.me/userinfobot) 등으로 확인할 수 있습니다. 이 값과 일치하지 않는 사용자의 요청은 무시되어, 봇 링크를 아는 다른 사람이 내 캘린더를 등록/조회/삭제하지 못하게 막아줍니다.

---

## STEP 5 — 패키지 설치

```bash
pip install -r requirements.txt
```

---

## STEP 6 — Google 인증 (최초 1회)

```bash
python google_auth.py
```

- 브라우저가 자동으로 열리면 **내 구글 계정으로 로그인**
- **"허용"** 클릭
- 터미널에 `✅ 인증 완료!` 메시지가 뜨면 성공
- `token.json` 파일이 생성됨

---

## STEP 7 — 봇 실행

```bash
python main.py
```

텔레그램에서 내 봇을 찾아 `/start`를 입력하면 시작됩니다.

---

## 사용법

| 입력 | 결과 |
|------|------|
| `내일 오후 3시 팀 미팅` | 파싱 후 확인 → 등록 |
| `6월 20일 강남역 고객 미팅` | 파싱 후 확인 → 등록 |
| `매주 월요일 9시 스탠드업` | 반복 일정 등록 |
| `/오늘` | 오늘 일정 조회 |
| `/이번주` | 이번 주 일정 조회 |

---

## 파일 구조

```
├── main.py              # 봇 메인
├── gemini_parser.py     # Gemini 자연어 파싱
├── calendar_service.py  # Google Calendar 연동
├── google_auth.py       # 최초 인증 스크립트
├── requirements.txt     # 패키지 목록
├── .env                 # API 키 (git에 올리지 마세요)
├── credentials.json     # Google OAuth (git에 올리지 마세요)
└── token.json           # 자동 생성 (git에 올리지 마세요)
```

---

## 문제 해결

| 오류 | 해결 |
|------|------|
| `token.json이 없습니다` | `python google_auth.py` 실행 |
| `TELEGRAM_BOT_TOKEN이 없습니다` | `.env` 파일 확인 |
| `credentials.json이 없습니다` | Google Cloud에서 다운로드 후 프로젝트 폴더에 저장 |
| 파싱이 엉뚱하게 됨 | 날짜·시간을 더 명확하게 입력 |

---

## 보안

- `credentials.json`, `token.json`은 내 구글 캘린더에 접근 가능한 실제 인증 정보입니다. `.gitignore`에 등록되어 있으니 GitHub에 올리기 전 `git status`로 두 파일이 추적되지 않는지 반드시 확인하세요.
- `ALLOWED_CHAT_ID`가 설정되지 않으면 누구나 이 봇으로 내 캘린더를 조작할 수 있습니다.
