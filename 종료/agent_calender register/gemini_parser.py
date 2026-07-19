import json
import os
import re
from datetime import datetime
from typing import Optional

import google.generativeai as genai


def parse_event(text: str) -> Optional[dict]:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")

    prompt = f"""오늘 날짜와 시간: {now} (한국 시간, KST)

다음 텍스트에서 일정 정보를 추출해 JSON으로만 반환하세요.
일정이 없으면 null만 반환하세요. 설명은 절대 붙이지 마세요.

텍스트: "{text}"

반환 형식:
{{
  "title": "이벤트 제목",
  "start_datetime": "YYYY-MM-DDTHH:MM:SS",
  "end_datetime": "YYYY-MM-DDTHH:MM:SS",
  "location": "장소 또는 null",
  "description": "설명 또는 null",
  "recurrence": "RRULE:FREQ=WEEKLY;BYDAY=MO 형식 또는 null"
}}

규칙:
- 종료 시간이 없으면 시작 시간 + 1시간
- 시간이 없으면 오전 9시로 설정
- 날짜 표현은 오늘 날짜 기준으로 계산
- 일정이 아닌 일반 대화면 null 반환"""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # 코드블록 제거
    raw = re.sub(r"```json|```", "", raw).strip()

    if raw.lower() == "null":
        return None

    return json.loads(raw)
