"""
Google Gemini Vision API를 사용한 명함 OCR
"""
import json
import os
from google import genai
from google.genai import types
from PIL import Image


def extract_card_info(image_path: str) -> dict:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    image = Image.open(image_path)

    prompt = (
        "이 명함 이미지에서 다음 정보를 추출해 주세요.\n"
        "반드시 아래 JSON 형식으로만 응답하고, 다른 텍스트는 포함하지 마세요.\n\n"
        "{\n"
        '  "name": "이름",\n'
        '  "company": "회사명",\n'
        '  "title": "직책",\n'
        '  "email": "이메일주소",\n'
        '  "phone": "전화번호",\n'
        '  "address": "주소"\n'
        "}\n\n"
        "정보가 없으면 해당 필드를 빈 문자열(\"\")로 채워주세요."
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=[prompt, image],
    )

    raw = response.text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())
