import httpx
import os
import math


NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")


def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    """두 좌표 간 거리(m) 계산"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


async def search_restaurants(query: str, lat: float, lng: float, radius: int = 500) -> list[dict]:
    """네이버 지역 검색 API (좌표 미지원 → 거리 후처리)"""
    from search.kakao_local import geocode

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": query, "display": 10, "sort": "comment"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        if resp.status_code != 200:
            return []
        data = resp.json()

    results = []
    for item in data.get("items", []):
        road_addr = item.get("roadAddress", "") or item.get("address", "")
        # 좌표 변환 후 반경 필터
        coords = await geocode(road_addr)
        if coords is None:
            continue
        dist = _haversine(lat, lng, coords[0], coords[1])
        if dist > radius:
            continue

        name = item.get("title", "").replace("<b>", "").replace("</b>", "")
        results.append({
            "name": name,
            "address": road_addr,
            "lat": coords[0],
            "lng": coords[1],
            "distance_m": dist,
            "category": item.get("category", ""),
            "description": item.get("description", ""),
            "naver_url": item.get("link", ""),
            "source": "naver",
        })
    return results
