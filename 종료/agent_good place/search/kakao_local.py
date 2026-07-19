import httpx
import os


KAKAO_API_KEY = os.getenv("KAKAO_REST_API_KEY")
HEADERS = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}


async def search_restaurants(query: str, lat: float, lng: float, radius: int = 500) -> list[dict]:
    """Kakao 로컬 API로 음식점 검색 (좌표 기반)"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {
        "query": query,
        "x": str(lng),
        "y": str(lat),
        "radius": radius,
        "category_group_code": "FD6",
        "size": 10,
        "sort": "distance",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("documents", []):
        results.append({
            "name": item["place_name"],
            "address": item.get("road_address_name") or item.get("address_name", ""),
            "lat": float(item["y"]),
            "lng": float(item["x"]),
            "distance_m": int(item.get("distance", 0)),
            "phone": item.get("phone", ""),
            "kakao_url": item.get("place_url", ""),
            "category": item.get("category_name", ""),
            "source": "kakao",
        })
    return results


async def geocode(address: str):
    """주소 또는 지역명 → (lat, lng) 변환"""
    url = "https://dapi.kakao.com/v2/local/search/keyword.json"
    params = {"query": address, "size": 1}
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=HEADERS, params=params)
        resp.raise_for_status()
        data = resp.json()

    docs = data.get("documents", [])
    if not docs:
        return None
    return float(docs[0]["y"]), float(docs[0]["x"])
