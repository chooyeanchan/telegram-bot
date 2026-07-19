import json
import os
import google.generativeai as genai


genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))

EXTRACT_TOOL = genai.protos.Tool(
    function_declarations=[
        genai.protos.FunctionDeclaration(
            name="extract_restaurant_intent",
            description="사용자의 자연어 입력에서 맛집 검색 조건과 지역 정보를 추출한다.",
            parameters=genai.protos.Schema(
                type=genai.protos.Type.OBJECT,
                properties={
                    "location_text": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="텍스트에서 추출한 지역/장소명 (예: '강남역', '홍대'). 위치 메시지가 있거나 언급 없으면 빈 문자열.",
                    ),
                    "cuisine_type": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="원하는 음식 종류 키워드 (예: '라멘', '파스타', '고기'). 없으면 '맛집'.",
                    ),
                    "atmosphere": genai.protos.Schema(
                        type=genai.protos.Type.STRING,
                        description="원하는 분위기나 목적 (예: '혼밥', '데이트', '조용한', '회식'). 없으면 빈 문자열.",
                    ),
                    "party_size": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="인원 수. 언급 없으면 1.",
                    ),
                    "budget_per_person": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="1인당 예산 (원). 언급 없으면 0.",
                    ),
                    "max_distance_m": genai.protos.Schema(
                        type=genai.protos.Type.INTEGER,
                        description="최대 거리 (미터). 언급 없으면 500.",
                    ),
                    "open_now": genai.protos.Schema(
                        type=genai.protos.Type.BOOLEAN,
                        description="현재 영업중인 곳만 볼지 여부. 기본 True.",
                    ),
                },
                required=["cuisine_type", "max_distance_m", "open_now"],
            ),
        )
    ]
)


async def parse(user_text: str) -> dict:
    """자연어 텍스트 → intent_slots dict"""
    response = model.generate_content(
        contents=[{"role": "user", "parts": [user_text]}],
        tools=[EXTRACT_TOOL],
        tool_config={"function_calling_config": {"mode": "ANY"}},
    )

    for part in response.candidates[0].content.parts:
        if part.function_call:
            args = dict(part.function_call.args)
            return {
                "location_text": args.get("location_text", ""),
                "cuisine_type": args.get("cuisine_type", "맛집"),
                "atmosphere": args.get("atmosphere", ""),
                "party_size": int(args.get("party_size", 1)),
                "budget_per_person": int(args.get("budget_per_person", 0)),
                "max_distance_m": int(args.get("max_distance_m", 500)),
                "open_now": bool(args.get("open_now", True)),
            }

    # Function call 없을 때 기본값
    return {
        "location_text": "",
        "cuisine_type": "맛집",
        "atmosphere": "",
        "party_size": 1,
        "budget_per_person": 0,
        "max_distance_m": 500,
        "open_now": True,
    }
