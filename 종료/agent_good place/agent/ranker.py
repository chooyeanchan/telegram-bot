import json
import os
import google.generativeai as genai


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))


async def rank(restaurants: list[dict], intent: dict) -> list[dict]:
    """Gemini로 상위 3개 선정 + 추천 이유 생성"""
    if not restaurants:
        return []

    simplified = [
        {
            "index": i,
            "name": r["name"],
            "distance_m": r.get("distance_m"),
            "rating": r.get("rating"),
            "review_count": r.get("review_count"),
            "category": r.get("category", ""),
            "open_now": r.get("open_now"),
            "description": r.get("description", ""),
        }
        for i, r in enumerate(restaurants)
    ]

    conditions = []
    if intent.get("cuisine_type"):
        conditions.append(f"음식: {intent['cuisine_type']}")
    if intent.get("atmosphere"):
        conditions.append(f"분위기/목적: {intent['atmosphere']}")
    if intent.get("party_size", 1) > 1:
        conditions.append(f"인원: {intent['party_size']}명")
    if intent.get("budget_per_person"):
        conditions.append(f"예산: 1인 {intent['budget_per_person']:,}원")

    prompt = f"""당신은 친근한 맛집 큐레이터입니다.
아래 사용자 조건과 후보 식당 목록을 보고 가장 적합한 상위 3개를 골라주세요.

[사용자 조건]
{chr(10).join(conditions) if conditions else "특별한 조건 없음"}

[후보 식당]
{json.dumps(simplified, ensure_ascii=False, indent=2)}

JSON 배열로만 응답하세요 (다른 텍스트 없이):
[
  {{"index": 숫자, "reason": "추천 이유 1~2문장, 친근한 말투로"}},
  {{"index": 숫자, "reason": "..."}},
  {{"index": 숫자, "reason": "..."}}
]"""

    response = model.generate_content(prompt)
    text = response.text.strip()

    # 코드블록 제거
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    try:
        ranked = json.loads(text)
    except Exception:
        # 파싱 실패 시 거리순 상위 3개 반환
        return [{"restaurant": r, "reason": "거리가 가까운 곳이에요."} for r in restaurants[:3]]

    result = []
    for item in ranked[:3]:
        idx = item.get("index", 0)
        if 0 <= idx < len(restaurants):
            result.append({
                "restaurant": restaurants[idx],
                "reason": item.get("reason", ""),
            })
    return result
