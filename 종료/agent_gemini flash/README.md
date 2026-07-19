# ⚡ 제미나이 플래시

Gemini 기반 범용 AI 챗봇입니다. 텍스트 대화와 이미지 설명을 지원합니다.

## 주요 기능

- `/start` — 새 대화 세션 시작
- `/new` — 대화 히스토리 초기화
- `/model <모델명>` — 사용할 Gemini 모델 전환 (예: `gemini-2.5-pro`)
- 일반 텍스트 메시지 → Gemini와 대화
- 이미지 전송(+캡션) → 이미지 설명/분석

## 설치

```bash
cd "종료/agent_gemini flash"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

| 변수 | 설명 | 발급처 |
|---|---|---|
| `BOT_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `GEMINI_API_KEY` | Gemini API 키 | [Google AI Studio](https://aistudio.google.com) |
| `ALLOWED_USER_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 사용자 ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |
| `GEMINI_MODEL` | 기본 모델 (선택, 기본값 `gemini-2.0-flash`) | — |

## 실행

```bash
python3 main.py
```

## 보안

- `ALLOWED_USER_ID`와 일치하지 않는 사용자의 요청은 모든 핸들러에서 무시합니다.
- `.env`, `nohup.out`은 `.gitignore`에 포함되어 있습니다.
- ⚠️ `.claude/settings.local.json`도 함께 gitignore 처리했습니다 — 과거 이 파일에 봇 토큰이 curl 명령 승인 기록으로 평문 저장된 적이 있습니다. 커밋 전이라 실제 유출은 아니지만, 걱정되면 BotFather에서 `/revoke` 후 토큰을 재발급하는 걸 권장합니다.
