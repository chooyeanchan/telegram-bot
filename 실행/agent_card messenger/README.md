# 💼 명함 메신저

텔레그램으로 명함 사진을 보내면 OCR로 정보를 추출하고, 인식된 이메일 주소로 내 명함을 자동 발송하는 봇입니다.

## 주요 기능

- 명함 사진 전송 → OCR로 이름/회사/직책/이메일/전화번호/주소 인식
- 인식 결과 확인 후 버튼(✅ 발송 / ❌ 취소)으로 발송 여부 결정
- Gmail 앱 비밀번호를 이용해 내 명함(이미지 + 소개 문구)을 이메일로 발송

## 설치

```bash
cd "실행/agent_card messenger"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

`.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `GEMINI_API_KEY` | 명함 OCR/파싱에 사용하는 Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `GMAIL_ADDRESS` | 발신용 Gmail 주소 | — |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (일반 로그인 비밀번호 아님) | [Google 계정 → 보안 → 앱 비밀번호](https://myaccount.google.com/apppasswords) |
| `MY_CARD_IMAGE_PATH` | 발송할 내 명함 이미지 경로 | 로컬 파일 경로 |
| `MY_EMAIL_INTRO` | 발송 이메일 본문에 들어갈 소개 문구 | — |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |

## 실행

```bash
python3 bot.py
```

## 보안

- `ALLOWED_CHAT_ID`와 일치하지 않는 사용자의 요청은 무시합니다.
- `GMAIL_APP_PASSWORD`는 일반 Gmail 비밀번호가 아니라 앱 전용 비밀번호를 사용하세요 (유출 시 앱 비밀번호만 재발급하면 됨).
- `.env`, `credentials.json`, `my_card.jpg`, `nohup.out`은 `.gitignore`에 포함되어 있습니다.
