import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL


def summarize_todos(items_by_file: dict[str, list[dict]]) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API 키가 설정되지 않았습니다."

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    lines = []
    for label, items in items_by_file.items():
        if items:
            lines.append(f"[{label}]")
            for item in items:
                if item["parent"]:
                    lines.append(f"- {item['parent']} > {item['text']}")
                else:
                    lines.append(f"- {item['text']}")

    if not lines:
        return "미완료 항목이 없습니다. 모두 완료했어요! 🎉"

    todo_text = "\n".join(lines)
    prompt = (
        "다음은 나의 미완료 할 일 목록입니다.\n\n"
        f"{todo_text}\n\n"
        "오늘 처리하면 좋을 것 같은 항목 3개를 추천해주세요. "
        "각 항목마다 짧은 이유도 함께 알려주세요. 한국어로 답해주세요."
    )

    response = model.generate_content(prompt)
    return response.text
