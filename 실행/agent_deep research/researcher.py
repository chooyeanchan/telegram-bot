import os
import re
import asyncio
from datetime import datetime
from google import genai
from google.genai import types

SAVE_PATH = "/Users/chooyeanchan/Library/Mobile Documents/iCloud~md~obsidian/Documents/chooyeanchan_icloud/1.0_llm wiki/inbox"

RESEARCH_PROMPT = """
당신은 전문 리서처입니다. 아래 주제를 한국어로 상세히 조사하여 마크다운 문서를 작성해주세요.

주제: {topic}
조사 깊이: {depth}
특히 집중할 부분: {focus}

다음 구조로 작성해주세요 (마크다운 형식 엄수):

# {topic}
> 조사일: {date}

## 요약

## 배경 및 개요

## 핵심 내용

## 주요 사례/데이터

## 시사점 및 전망

## 참고 출처

규칙:
- 반드시 한국어로 작성
- 간략 모드: 각 섹션 2~3문장 / 심층 모드: 각 섹션 5문장 이상
- 참고 출처는 실제 URL 또는 출처명 포함
- 표, 목록 등 마크다운 요소 적극 활용
- 표 작성 시 구분선은 대시 3개(---|---) 수준으로 간결하게 작성하고, 대시(-) 또는 <br> 태그를 비정상적으로 길게 반복하여 출력하지 마십시오.
"""


def sanitize_filename(topic: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", topic).strip()


def build_filepath(topic: str) -> str:
    date_str = datetime.now().strftime("%y%m%d")
    safe_topic = sanitize_filename(topic)
    base = f"{date_str} {safe_topic}"

    path = os.path.join(SAVE_PATH, f"{base}.md")
    if not os.path.exists(path):
        return path

    counter = 2
    while os.path.exists(os.path.join(SAVE_PATH, f"{base} {counter}.md")):
        counter += 1
    return os.path.join(SAVE_PATH, f"{base} {counter}.md")


def clean_markdown(content: str) -> str:
    if not content:
        return ""
    # 1. Clean up excessive dashes in markdown tables (more than 10 consecutive dashes)
    content = re.sub(r'-{10,}', '---', content)
    # 2. Clean up repeating <br> tags (more than 2 consecutive br tags)
    content = re.sub(r'(<br\s*/?>\s*){2,}', '<br>', content)
    # 3. Clean up excessive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    return content


async def run_research(topic: str, depth: str, focus: str, progress_callback=None) -> dict:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    prompt = RESEARCH_PROMPT.format(
        topic=topic,
        depth=depth,
        focus=focus if focus else "없음 (전반적으로 조사)",
        date=datetime.now().strftime("%Y-%m-%d"),
    )

    if progress_callback:
        await progress_callback("🔍 Google Search로 최신 정보 검색 중...")

    try:
        print("[DEBUG] Gemini API 호출 시작", flush=True)
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.models.generate_content(
                model="gemini-2.5-pro",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.3,
                ),
            ),
        )

        print("[DEBUG] Gemini API 응답 수신", flush=True)
        markdown_content = clean_markdown(response.text)

        if progress_callback:
            await progress_callback("📝 문서 작성 완료, 파일 저장 중...")

        os.makedirs(SAVE_PATH, exist_ok=True)
        file_path = build_filepath(topic)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        summary = _extract_summary(markdown_content)
        return {"success": True, "file_path": file_path, "summary": summary}

    except Exception as e:
        return {"success": False, "error": str(e)}


def _extract_summary(content: str) -> str:
    match = re.search(r"## 요약\n+([\s\S]+?)(?=\n##|\Z)", content)
    if match:
        lines = [l for l in match.group(1).strip().splitlines() if l.strip()]
        return "\n".join(lines[:3])
    return content[:200].strip()
