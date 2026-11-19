#!/bin/zsh
# todo manager 봇 시작 스크립트 (로그인 항목으로 등록해 재부팅 후 자동 실행)
#
# launchd 대신 터미널로 띄우는 이유: launchd가 직접 띄운 프로세스는 macOS 보안(TCC) 때문에
# iCloud에 있는 옵시디언 볼트를 읽지 못한다. 터미널에서 띄우면 터미널의 접근 권한을 물려받는다.

cd "/Users/chooyeanchan/telegram-bot/실행/agent_todo manager" || exit 1

# 이미 돌고 있으면 또 띄우지 않는다 (같은 토큰으로 두 개가 돌면 텔레그램 충돌)
if [ -f bot.pid ] && kill -0 "$(cat bot.pid)" 2>/dev/null; then
  echo "todo manager가 이미 실행 중이에요 (PID $(cat bot.pid))"
  exit 0
fi

nohup venv/bin/python3 -W ignore main.py >> logs/nohup.out 2>&1 &
echo $! > bot.pid
disown
echo "todo manager를 시작했어요 (PID $(cat bot.pid)). 이 창은 닫아도 돼요."
