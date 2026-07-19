import asyncio
from agent.intent_parser import parse
from agent.ranker import rank
from search import kakao_local, google_places
from search.aggregator import merge


async def recommend(user_text: str, lat, lng):
    """
    메인 오케스트레이터.
    반환: (ranked_list, intent)
    """
    # 1. 의도 분석
    intent = await parse(user_text)

    # 2. 위치 결정
    if lat is None or lng is None:
        location_text = intent.get("location_text", "")
        if not location_text:
            return [], intent
        coords = await kakao_local.geocode(location_text)
        if coords is None:
            return [], intent
        lat, lng = coords

    radius = intent.get("max_distance_m", 500)
    query = intent.get("cuisine_type", "맛집")
    if intent.get("atmosphere"):
        query = f"{intent['atmosphere']} {query}"

    # 3. 병렬 API 호출 (Kakao + Google)
    kakao_results, google_results = await asyncio.gather(
        kakao_local.search_restaurants(query, lat, lng, radius),
        google_places.search_restaurants(query, lat, lng, radius),
        return_exceptions=True,
    )

    all_results = []
    for r in [kakao_results, google_results]:
        if isinstance(r, list):
            all_results.append(r)

    # 4. 통합 + 중복 제거
    merged = merge(all_results, lat, lng)

    # 5. Gemini 랭킹
    ranked = await rank(merged, intent)

    return ranked, intent
