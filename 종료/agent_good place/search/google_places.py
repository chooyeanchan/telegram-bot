import httpx
import os


GOOGLE_API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")


async def search_restaurants(query: str, lat: float, lng: float, radius: int = 500) -> list[dict]:
    """Google Places API (New) Nearby Search"""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.currentOpeningHours,places.priceLevel,places.googleMapsUri,places.primaryType",
    }
    body = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius),
            }
        },
        "includedTypes": ["restaurant"],
        "maxResultCount": 10,
        "rankPreference": "DISTANCE",
    }
    # 쿼리 텍스트는 TextSearch를 써야 하지만 Nearby로 먼저 가져온 뒤 이름 필터링
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            return []
        data = resp.json()

    results = []
    for place in data.get("places", []):
        loc = place.get("location", {})
        results.append({
            "name": place.get("displayName", {}).get("text", ""),
            "address": place.get("formattedAddress", ""),
            "lat": loc.get("latitude", 0),
            "lng": loc.get("longitude", 0),
            "distance_m": None,
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "open_now": place.get("currentOpeningHours", {}).get("openNow"),
            "price_level": place.get("priceLevel"),
            "google_maps_url": place.get("googleMapsUri", ""),
            "source": "google",
        })
    return results
