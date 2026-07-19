# 🔬 딥 리서치

텔레그램에서 주제를 입력하면 심층 리서치를 수행하고, 결과를 Obsidian inbox에 마크다운 파일로 저장해주는 봇입니다.

자세한 기획 배경은 [PRD.md](PRD.md) 참고.

## 주요 기능

- `/research` 또는 자유 텍스트로 주제 입력 → 조사 깊이(심층/간략) 선택 → 세부 분야 지정
- 조사 진행 중 "타이핑 중..." 상태 유지
- 완료 후 요약 메시지 + 마크다운 파일 저장
- `/list` — 최근 저장 파일 목록 조회

## 설치

```bash
cd "실행/agent_deep research"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

`.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `GEMINI_API_KEY` | Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |

## 실행

```bash
python3 bot.py
```

## 보안

- `ALLOWED_CHAT_ID`와 일치하지 않는 사용자의 요청은 무시합니다.
- `.env`, `nohup.out`은 `.gitignore`에 포함되어 있습니다 (`nohup.out`에는 텔레그램 API 요청 로그가 남을 수 있어 커밋하면 안 됩니다).
