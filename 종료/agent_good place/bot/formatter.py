MEDALS = ["🥇", "🥈", "🥉"]


def _open_emoji(open_now) -> str:
    if open_now is True:
        return "🟢 영업중"
    if open_now is False:
        return "🔴 영업종료"
    return "⚪ 영업정보 없음"


def _map_links(r: dict) -> str:
    links = []
    if r.get("kakao_url"):
        links.append(f'[카카오맵]({r["kakao_url"]})')
    if r.get("google_maps_url"):
        links.append(f'[구글맵]({r["google_maps_url"]})')
    return " · ".join(links) if links else ""


def build_result_message(ranked: list[dict], intent: dict, location_label: str) -> str:
    cuisine = intent.get("cuisine_type", "맛집")
    radius = intent.get("max_distance_m", 500)

    lines = [f"📍 *{location_label}* 기준 · {cuisine} · 반경 {radius}m\n{'━' * 22}"]

    for i, item in enumerate(ranked):
        r = item["restaurant"]
        reason = item["reason"]
        medal = MEDALS[i] if i < len(MEDALS) else f"{i+1}."

        dist = f"({r['distance_m']}m)" if r.get("distance_m") else ""
        rating = f"⭐ {r['rating']}" if r.get("rating") else ""
        reviews = f"({r['review_count']}개)" if r.get("review_count") else ""
        open_status = _open_emoji(r.get("open_now"))
        maps = _map_links(r)

        block = [
            f"{medal} *{r['name']}* {dist}",
            " · ".join(filter(None, [rating + reviews, open_status])),
            f'💬 {reason}',
        ]
        if maps:
            block.append(f"🗺 {maps}")

        lines.append("\n".join(block))

    lines.append("━" * 22)
    return "\n\n".join(lines)


def build_no_result_message() -> str:
    return "😅 조건에 맞는 맛집을 찾지 못했어요. 검색 범위를 넓히거나 다른 키워드로 시도해보세요!"


def build_location_request_message() -> str:
    return (
        "📍 위치를 알 수 없어요!\n\n"
        "아래 중 하나로 알려주세요:\n"
        "1️⃣ 텔레그램 📎 → 위치 → *현재 위치 전송*\n"
        "2️⃣ 텍스트에 지역 포함: _'강남역 근처 파스타'_"
    )
