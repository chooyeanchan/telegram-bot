# 🗼 Agent Control Tower

로컬에서 돌아가는 여러 텔레그램 봇 에이전트를 한 화면에서 켜고 끄고, 로그를 보고, 상태를 모니터링하는 대시보드입니다.

- `server.py` — 로컬 API 서버 (포트 `8765`). `agents.json`에 등록된 에이전트를 시작/중지하고 PID·로그를 관리합니다.
- `index.html` — 대시보드 UI. `server.py`가 켜져 있어야 동작합니다.
- `agents.json` — 관리 대상 에이전트 목록(이름, 경로, 실행 스크립트, 카테고리 등).

## 실행 방법

```bash
cd "agent_control tower"
python3 server.py
```

그 다음 `index.html`을 브라우저로 열면 됩니다. (`launch.sh` 또는 `launch.command`로 한 번에 실행 가능)

## 에이전트 등록 구조

`agents.json`의 각 항목:

```json
{
  "id": "agent_id",
  "name": "표시 이름",
  "emoji": "🤖",
  "description": "설명",
  "dir": "../실행/agent_xxx",
  "script": "main.py",
  "category": "utility",
  "tags": ["telegram"],
  "group": "active"
}
```

- `group`이 `active`면 대시보드 메인 화면에, `archived`면 하단 "종료된 에이전트" 접이식 섹션에 표시됩니다.
- 대시보드의 "새 에이전트 추가" 버튼으로도 등록할 수 있습니다.

## 요구 사항

- Python 3.9+ (표준 라이브러리만 사용, 별도 의존성 없음)

## 주의

- `pids.json`은 실행 중인 프로세스 PID를 저장하는 런타임 파일이라 커밋하지 않습니다.
- 이 앱 자체는 API 키를 다루지 않지만, 관리 대상 에이전트들의 `.env`를 대신 노출하지 않도록 각 에이전트 폴더에서 `.gitignore`를 확인하세요.
