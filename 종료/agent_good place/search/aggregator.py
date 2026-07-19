import math


def _distance(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return int(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def _normalize_name(name: str) -> str:
    return name.replace(" ", "").lower()


def merge(all_results: list[list[dict]], user_lat: float, user_lng: float) -> list[dict]:
    """여러 소스 결과를 통합하고 중복 제거 후 거리순 정렬"""
    seen: dict[str, dict] = {}

    for results in all_results:
        for item in results:
            key = _normalize_name(item["name"])
            if key not in seen:
                if item.get("distance_m") is None and item.get("lat") and item.get("lng"):
                    item["distance_m"] = _distance(user_lat, user_lng, item["lat"], item["lng"])
                seen[key] = item
            else:
                # 이미 있으면 평점/리뷰 등 보강
                existing = seen[key]
                if not existing.get("rating") and item.get("rating"):
                    existing["rating"] = item["rating"]
                if not existing.get("review_count") and item.get("review_count"):
                    existing["review_count"] = item["review_count"]
                if not existing.get("open_now") and item.get("open_now") is not None:
                    existing["open_now"] = item["open_now"]
                if not existing.get("google_maps_url") and item.get("google_maps_url"):
                    existing["google_maps_url"] = item["google_maps_url"]
                if not existing.get("kakao_url") and item.get("kakao_url"):
                    existing["kakao_url"] = item["kakao_url"]

    merged = list(seen.values())
    merged.sort(key=lambda x: x.get("distance_m") or 9999)
    return merged[:10]
