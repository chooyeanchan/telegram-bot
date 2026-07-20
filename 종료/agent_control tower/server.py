#!/usr/bin/env python3
"""
Agent Control Tower - Local API Server
Run: python3 server.py
Then open index.html in your browser.
"""

import os
import json
import signal
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import threading

BASE_DIR = Path(__file__).parent
AGENTS_CONFIG = BASE_DIR / "agents.json"
PIDS_FILE = BASE_DIR / "pids.json"
LOG_LINES = 50
PORT = 8765


# ── Config helpers ──────────────────────────────────────────────────────────

def load_config() -> dict:
    return json.loads(AGENTS_CONFIG.read_text(encoding="utf-8"))

def save_config(cfg: dict):
    AGENTS_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def load_pids() -> dict:
    if PIDS_FILE.exists():
        try:
            return json.loads(PIDS_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_pids(pids: dict):
    PIDS_FILE.write_text(json.dumps(pids, indent=2))


# ── Process helpers ─────────────────────────────────────────────────────────

def is_running(pid: int) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False

def resolve_dir(agent: dict) -> Path:
    d = agent["dir"]
    if d.startswith("..") or d.startswith("."):
        return (BASE_DIR / d).resolve()
    return Path(d).resolve()


# ── Agent status ────────────────────────────────────────────────────────────

def get_agent_status(agent: dict) -> dict:
    pids = load_pids()
    agent_id = agent["id"]
    pid = pids.get(agent_id)
    running = is_running(pid)

    if not running and pid:
        pids.pop(agent_id, None)
        save_pids(pids)
        pid = None

    agent_dir = resolve_dir(agent)
    script = agent_dir / agent["script"]

    # Last run: check nohup.out mtime
    log_file = agent_dir / "nohup.out"
    last_run = None
    if log_file.exists():
        mtime = log_file.stat().st_mtime
        last_run = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "id": agent_id,
        "name": agent["name"],
        "emoji": agent.get("emoji", "🤖"),
        "description": agent.get("description", ""),
        "category": agent.get("category", "general"),
        "tags": agent.get("tags", []),
        "group": agent.get("group", "active"),
        "running": running,
        "pid": pid,
        "last_run": last_run,
        "script_exists": script.exists(),
        "dir": str(agent_dir),
    }

def get_all_status() -> list:
    cfg = load_config()
    return [get_agent_status(a) for a in cfg["agents"]]


# ── Start / Stop ────────────────────────────────────────────────────────────

def start_agent(agent_id: str) -> dict:
    cfg = load_config()
    agent = next((a for a in cfg["agents"] if a["id"] == agent_id), None)
    if not agent:
        return {"ok": False, "message": f"에이전트 '{agent_id}' 없음"}

    status = get_agent_status(agent)
    if status["running"]:
        return {"ok": False, "message": f"이미 실행 중 (PID: {status['pid']})"}

    agent_dir = resolve_dir(agent)
    script = agent_dir / agent["script"]
    if not script.exists():
        return {"ok": False, "message": f"스크립트 없음: {script}"}

    log_file = agent_dir / "nohup.out"
    try:
        proc = subprocess.Popen(
            ["python3", agent["script"]],
            cwd=str(agent_dir),
            stdout=open(log_file, "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        pids = load_pids()
        pids[agent_id] = proc.pid
        save_pids(pids)
        return {"ok": True, "message": f"시작됨 (PID: {proc.pid})", "pid": proc.pid}
    except Exception as e:
        return {"ok": False, "message": f"시작 실패: {e}"}

def stop_agent(agent_id: str) -> dict:
    cfg = load_config()
    agent = next((a for a in cfg["agents"] if a["id"] == agent_id), None)
    if not agent:
        return {"ok": False, "message": f"에이전트 '{agent_id}' 없음"}

    pids = load_pids()
    pid = pids.get(agent_id)
    if not pid or not is_running(pid):
        pids.pop(agent_id, None)
        save_pids(pids)
        return {"ok": False, "message": "실행 중이 아님"}

    try:
        # 프로세스 그룹 전체 종료 (start_new_session=True로 생성된 그룹)
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except Exception:
            os.kill(pid, signal.SIGTERM)

        import time as _time
        _time.sleep(0.8)

        # 아직 살아있으면 SIGKILL로 강제 종료
        if is_running(pid):
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except Exception:
                os.kill(pid, signal.SIGKILL)

        pids.pop(agent_id, None)
        save_pids(pids)
        return {"ok": True, "message": f"종료됨 (PID: {pid})"}
    except Exception as e:
        return {"ok": False, "message": f"종료 실패: {e}"}


# ── Logs ────────────────────────────────────────────────────────────────────

def get_logs(agent_id: str) -> str:
    cfg = load_config()
    agent = next((a for a in cfg["agents"] if a["id"] == agent_id), None)
    if not agent:
        return "에이전트 없음"

    agent_dir = resolve_dir(agent)
    log_file = agent_dir / "nohup.out"
    if not log_file.exists():
        return "로그 파일 없음"
    try:
        result = subprocess.run(
            ["tail", f"-{LOG_LINES}", str(log_file)],
            capture_output=True, text=True
        )
        return result.stdout or "로그 없음"
    except Exception as e:
        return f"로그 읽기 실패: {e}"


# ── HTTP Handler ─────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default access log

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/agents":
            self.send_json(get_all_status())

        elif path.startswith("/api/agents/") and path.endswith("/logs"):
            agent_id = path[len("/api/agents/"):-len("/logs")]
            self.send_text(get_logs(agent_id))

        elif path == "/api/ping":
            self.send_json({"ok": True, "time": datetime.now().isoformat()})

        elif path == "/api/shutdown":
            # 응답 먼저 보내고, 별도 스레드에서 에이전트 종료 후 서버 프로세스 종료
            self.send_json({"ok": True, "message": "전체 종료 시작"})
            def _shutdown():
                import time as _t
                _t.sleep(0.3)
                cfg = load_config()
                for agent in cfg["agents"]:
                    stop_agent(agent["id"])
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()

        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b"{}"

        if path.startswith("/api/agents/") and path.endswith("/start"):
            agent_id = path[len("/api/agents/"):-len("/start")]
            self.send_json(start_agent(agent_id))

        elif path.startswith("/api/agents/") and path.endswith("/stop"):
            agent_id = path[len("/api/agents/"):-len("/stop")]
            self.send_json(stop_agent(agent_id))

        elif path == "/api/agents":
            try:
                data = json.loads(body)
                required = ["id", "name", "dir", "script"]
                if not all(k in data for k in required):
                    self.send_json({"ok": False, "message": f"필수 필드 누락: {required}"}, 400)
                    return
                cfg = load_config()
                if any(a["id"] == data["id"] for a in cfg["agents"]):
                    self.send_json({"ok": False, "message": "이미 존재하는 ID"}, 400)
                    return
                new_agent = {
                    "id": data["id"],
                    "name": data["name"],
                    "emoji": data.get("emoji", "🤖"),
                    "description": data.get("description", ""),
                    "dir": data["dir"],
                    "script": data["script"],
                    "category": data.get("category", "general"),
                    "tags": data.get("tags", []),
                    "group": data.get("group", "active"),
                }
                cfg["agents"].append(new_agent)
                save_config(cfg)
                self.send_json({"ok": True, "message": "에이전트 추가됨", "agent": new_agent})
            except Exception as e:
                self.send_json({"ok": False, "message": str(e)}, 400)

        else:
            self.send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/agents/"):
            agent_id = path[len("/api/agents/"):]
            cfg = load_config()
            before = len(cfg["agents"])
            cfg["agents"] = [a for a in cfg["agents"] if a["id"] != agent_id]
            if len(cfg["agents"]) == before:
                self.send_json({"ok": False, "message": "에이전트 없음"}, 404)
                return
            save_config(cfg)
            # Also stop if running
            stop_agent(agent_id)
            self.send_json({"ok": True, "message": "삭제됨"})
        else:
            self.send_json({"error": "not found"}, 404)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    global server_instance
    server_instance = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"✅ Agent Control Tower API 서버 시작")
    print(f"   http://127.0.0.1:{PORT}")
    print(f"   index.html을 브라우저에서 여세요")
    print(f"   종료: Ctrl+C\n")
    try:
        server_instance.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료")

server_instance = None

if __name__ == "__main__":
    main()
