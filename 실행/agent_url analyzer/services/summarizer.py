import os
import time
import re
import google.generativeai as genai


def summarize(parsed: dict) -> dict:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = _build_prompt(parsed)

    for attempt in range(5):
        try:
            response = model.generate_content(prompt)
            return _parse_response(response.text, parsed)
        except Exception as e:
            wait = _parse_retry_delay(str(e))
            if wait and attempt < 4:
                time.sleep(wait + 2)
                continue
            raise

    raise RuntimeError("Gemini API 요청 실패: 재시도 횟수 초과")


def _parse_retry_delay(error_msg: str) -> int:
    # "Please retry in Xs" 패턴에서 대기 시간 추출
    match = re.search(r"retry in (\d+)", error_msg)
    return int(match.group(1)) if match else 0


def _build_prompt(parsed: dict) -> str:
    content_preview = parsed["content"][:8000]  # 토큰 절약
    return f"""다음 콘텐츠를 한국어로 분석하고 아래 형식으로 정확히 출력하세요.

콘텐츠 유형: {parsed['type']}
원본 URL: {parsed['url']}

---콘텐츠---
{content_preview}
---끝---

출력 형식 (각 섹션을 정확히 이 마커로 구분):
[TITLE]
콘텐츠의 실제 제목 또는 핵심 주제 (1줄)

[SUMMARY]
3~5문장의 핵심 요약

[POINTS]
- 핵심 포인트 1
- 핵심 포인트 2
- 핵심 포인트 3

[QUOTE]
원문에서 가장 중요한 문장 1개

[TAGS]
태그1, 태그2, 태그3
"""


def _parse_response(text: str, parsed: dict) -> dict:
    def extract(marker: str) -> str:
        start = text.find(f"[{marker}]")
        if start == -1:
            return ""
        start += len(f"[{marker}]")
        markers = ["[TITLE]", "[SUMMARY]", "[POINTS]", "[QUOTE]", "[TAGS]"]
        end = len(text)
        for m in markers:
            idx = text.find(m, start)
            if idx != -1 and idx < end:
                end = idx
        return text[start:end].strip()

    title = extract("TITLE") or parsed.get("title", "제목 없음")
    tags_raw = extract("TAGS")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    return {
        "title": title,
        "type": parsed["type"],
        "url": parsed["url"],
        "summary": extract("SUMMARY"),
        "points": extract("POINTS"),
        "quote": extract("QUOTE"),
        "tags": tags,
    }
