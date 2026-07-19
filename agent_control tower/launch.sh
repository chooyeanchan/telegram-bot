#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"

# 서버가 꺼져있으면 시작
if ! curl -s http://127.0.0.1:8765/api/ping > /dev/null 2>&1; then
    cd "$DIR"
    nohup python3 server.py >> /tmp/control_tower.log 2>&1 &
    sleep 1
fi

# Chrome으로 HTML 열기
open -a "Google Chrome" "$DIR/index.html"
