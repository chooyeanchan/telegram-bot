_sessions: dict[int, dict] = {}


def get(chat_id: int) -> dict:
    return _sessions.get(chat_id, {})


def set_location(chat_id: int, lat: float, lng: float) -> None:
    _sessions.setdefault(chat_id, {})
    _sessions[chat_id]["lat"] = lat
    _sessions[chat_id]["lng"] = lng


def clear(chat_id: int) -> None:
    _sessions.pop(chat_id, None)
