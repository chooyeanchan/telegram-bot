# User Rules

- **Trigger word "시작"**: When the user says "시작" (or any variation indicating to start/begin), check and list all running agent processes in the workspace root (`/Users/chooyeanchan/에이전트 프로젝트`) with their PID and status. If no agents are running, explicitly state so.
- **Trigger word "종료"**: When the user says "종료" (or any variation indicating to stop/end), find and terminate all running agent processes (python/node processes running from directories named `agent_*` in the workspace root `/Users/chooyeanchan/에이전트 프로젝트`). Report the PID and status of the terminated processes.
