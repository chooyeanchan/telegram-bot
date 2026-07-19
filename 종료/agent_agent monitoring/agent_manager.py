import os
import signal
import subprocess
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
SELF_DIR = Path(__file__).parent

AGENTS = {
    "monitoring": {
        "name": "모니터링 봇",
        "emoji": "📡",
        "dir": SELF_DIR,
        "script": "bot.py",
        "self": True,
    },
    "card_messenger": {
        "name": "명함 메신저",
        "emoji": "💼",
        "dir": BASE_DIR / "agent_card messenger",
        "script": "bot.py",
    },
    "url_analyzer": {
        "name": "URL 분석기",
        "emoji": "🔗",
        "dir": BASE_DIR / "agent_url analyzer",
        "script": "main.py",
    },
    "deep_research": {
        "name": "딥 리서치",
        "emoji": "🔬",
        "dir": BASE_DIR / "agent_deep research",
        "script": "bot.py",
    },
    "calendar": {
        "name": "캘린더 등록",
        "emoji": "📅",
        "dir": BASE_DIR / "agent_calender register",
        "script": "main.py",
    },
    "gemini_flash": {
        "name": "제미나이 플래시",
        "emoji": "⚡",
        "dir": BASE_DIR / "agent_gemini flash",
        "script": "main.py",
    },
    "good_place": {
        "name": "맛집 추천",
        "emoji": "🍽️",
        "dir": BASE_DIR / "agent_good place",
        "script": "main.py",
    },
}

PID_FILE = Path(__file__).parent / "agent_pids.json"


def _load_pids() -> dict:
    if PID_FILE.exists():
        try:
            return json.loads(PID_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_pids(pids: dict):
    PID_FILE.write_text(json.dumps(pids, indent=2))


def _is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def get_status(agent_id: str) -> dict:
    agent = AGENTS[agent_id]
    is_self = agent.get("self", False)

    if is_self:
        pid = os.getpid()
        return {
            "id": agent_id,
            "name": agent["name"],
            "emoji": agent["emoji"],
            "running": True,
            "pid": pid,
            "self": True,
        }

    pids = _load_pids()
    pid = pids.get(agent_id)

    running = False
    if pid and _is_pid_running(pid):
        running = True
    else:
        if agent_id in pids:
            del pids[agent_id]
            _save_pids(pids)

    return {
        "id": agent_id,
        "name": agent["name"],
        "emoji": agent["emoji"],
        "running": running,
        "pid": pid if running else None,
        "self": False,
    }


def get_all_status() -> list[dict]:
    return [get_status(aid) for aid in AGENTS]


def start_agent(agent_id: str) -> tuple[bool, str]:
    agent = AGENTS[agent_id]
    status = get_status(agent_id)
    if status["running"]:
        return False, f"{agent['name']}은(는) 이미 실행 중입니다 (PID: {status['pid']})"

    script_path = agent["dir"] / agent["script"]
    if not script_path.exists():
        return False, f"스크립트를 찾을 수 없습니다: {script_path}"

    log_file = agent["dir"] / "nohup.out"
    try:
        proc = subprocess.Popen(
            ["python3", agent["script"]],
            cwd=str(agent["dir"]),
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pids = _load_pids()
        pids[agent_id] = proc.pid
        _save_pids(pids)
        return True, f"{agent['name']} 시작됨 (PID: {proc.pid})"
    except Exception as e:
        return False, f"시작 실패: {e}"


def stop_agent(agent_id: str) -> tuple[bool, str]:
    agent = AGENTS[agent_id]
    status = get_status(agent_id)
    if not status["running"]:
        return False, f"{agent['name']}은(는) 실행 중이 아닙니다"

    pid = status["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
        pids = _load_pids()
        pids.pop(agent_id, None)
        _save_pids(pids)
        return True, f"{agent['name']} 종료됨 (PID: {pid})"
    except Exception as e:
        return False, f"종료 실패: {e}"


def get_recent_logs(agent_id: str, lines: int = 20) -> str:
    agent = AGENTS[agent_id]
    log_file = agent["dir"] / "nohup.out"
    if not log_file.exists():
        return "로그 파일 없음"
    try:
        result = subprocess.run(
            ["tail", f"-{lines}", str(log_file)],
            capture_output=True, text=True
        )
        return result.stdout.strip() or "로그 없음"
    except Exception as e:
        return f"로그 읽기 실패: {e}"
