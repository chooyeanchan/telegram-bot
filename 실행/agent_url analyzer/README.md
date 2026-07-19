# 🔗 URL 분석기

텔레그램으로 URL(유튜브 / 웹페이지 / PDF)을 보내면 내용을 분석·요약해서 마크다운 파일로 저장하는 봇입니다.

## 주요 기능

- 유튜브 링크 → 자막/설명 기반 요약
- 웹페이지 링크 → 본문 추출 후 요약 (trafilatura)
- PDF 링크 → 텍스트 추출 후 요약
- 결과를 iCloud 경로에 마크다운(.md)으로 저장

## 설치

```bash
cd "실행/agent_url analyzer"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

`.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |
| `GEMINI_API_KEY` | Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `ICLOUD_PATH` | 요약 결과(.md)를 저장할 로컬 경로 | 본인 iCloud Drive 경로 |

## 실행

```bash
python3 main.py
```

## 보안

- `ALLOWED_CHAT_ID`와 일치하지 않는 사용자의 메시지는 무시합니다. 본인 chat ID를 반드시 설정하세요.
- `.env`, `logs/`, `nohup.out`은 `.gitignore`에 포함되어 있습니다 (`nohup.out`에는 텔레그램 API 요청 로그가 남는데, 여기에 봇 토큰이 평문으로 찍힐 수 있으니 절대 커밋하지 마세요).
