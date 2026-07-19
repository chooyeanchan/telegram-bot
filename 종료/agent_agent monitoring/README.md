# 📡 모니터링 봇

텔레그램에서 다른 에이전트들의 실행 상태를 확인하고, 시작/중지하고, 로그를 조회할 수 있는 원격 제어 봇입니다.

## 주요 기능

- `/start`, `/status` — 등록된 에이전트들의 실행 상태(🟢/🔴) 목록 표시
- 버튼으로 각 에이전트 시작 / 중지
- 버튼으로 각 에이전트 최근 로그 조회
- `agent_manager.py`의 `AGENTS` 목록에 정의된 에이전트를 대상으로 동작

## 설치

```bash
cd "종료/agent_agent monitoring"
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 환경 변수 (`.env`)

`.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

| 변수 | 설명 | 발급처 |
|---|---|---|
| `TELEGRAM_TOKEN` | 텔레그램 봇 토큰 | [@BotFather](https://t.me/BotFather) |
| `ALLOWED_CHAT_ID` | 이 봇을 사용할 수 있는 유일한 텔레그램 chat ID | [@userinfobot](https://t.me/userinfobot) 등으로 확인 |

## 실행

```bash
python3 bot.py
```

## 보안

- ⚠️ `ALLOWED_CHAT_ID`를 설정하지 않으면(`0` 또는 미설정) **누구나 다른 에이전트를 원격으로 켜고 끌 수 있습니다.** 반드시 값을 채워주세요.
- 다른 에이전트를 시작/중지하는 강력한 권한을 가진 봇이므로 특히 신경 써서 접근을 제한해야 합니다.
- `.env`, `nohup.out`, `agent_pids.json`은 `.gitignore`에 포함되어 있습니다.
