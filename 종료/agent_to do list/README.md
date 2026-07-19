# ✅ 할 일 목록

마크다운 파일 기반으로 할 일을 관리하는 텔레그램 봇입니다. 여러 개의 체크리스트(할 일/건강/청소 등)를 조회하고 번호로 완료 처리할 수 있습니다.

## 주요 기능

- `/todo`, `/health`, `/clean` — 각 카테고리 미완료 항목 조회
- `/all` — 전체 미완료 항목 조회
- `/status` — 파일별 완료율 요약
- `/summary` — Gemini가 우선순위를 분석해 추천
- 조회 후 번호 입력(예: `1 3 5`)으로 해당 항목 완료 처리

## 설치

```bash
cd "종료/agent_to do list"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |
| `TASKS_DIR` | 할 일 마크다운 파일들이 있는 로컬 디렉토리 경로 | — |
| `GEMINI_API_KEY` | `/summary`에 사용하는 Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `GEMINI_MODEL` | 사용할 Gemini 모델 | — |

## 실행

```bash
python3 bot.py
```

## 보안

- `ALLOWED_CHAT_ID`와 일치하지 않는 사용자에게는 "접근 권한이 없습니다"라고만 응답하고 아무 데이터도 노출하지 않습니다.
- `TASKS_DIR`이 가리키는 실제 할 일 마크다운 파일에는 사생활 정보가 담길 수 있으니, 그 폴더 자체를 레포에 포함하지 않도록 주의하세요.
- `.env`, `nohup.out`은 `.gitignore`에 포함되어 있습니다.
