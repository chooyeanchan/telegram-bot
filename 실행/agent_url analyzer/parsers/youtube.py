import re


def parse_youtube(url: str) -> dict:
    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError("유튜브 영상 ID를 추출할 수 없습니다.")

    transcript_text, title = _get_transcript(video_id)

    return {
        "type": "youtube",
        "title": title or f"YouTube: {video_id}",
        "content": transcript_text,
        "url": url,
    }


def _extract_video_id(url: str):
    match = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return match.group(1) if match else None


def _get_transcript(video_id: str) -> tuple:
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

    api = YouTubeTranscriptApi()

    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled:
        raise ValueError("자막이 비활성화된 영상입니다.")

    # ko → en 순서로 시도 (수동 자막 우선, 자동 자막 포함)
    for lang in ["ko", "ko-KR", "en", "en-US"]:
        try:
            transcript = transcript_list.find_transcript([lang])
            snippets = transcript.fetch()
            text = " ".join(s.text.strip() for s in snippets if s.text.strip())
            if text:
                title = _get_title(video_id)
                return text, title
        except NoTranscriptFound:
            continue

    # 자동 생성 자막이라도 가져오기
    try:
        transcript = transcript_list.find_generated_transcript(["ko", "en"])
        snippets = transcript.fetch()
        text = " ".join(s.text.strip() for s in snippets if s.text.strip())
        if text:
            title = _get_title(video_id)
            return text, title
    except Exception:
        pass

    raise ValueError("자막이 없는 영상은 요약을 지원하지 않습니다.")


def _get_title(video_id: str) -> str:
    try:
        import requests
        resp = requests.get(
            f"https://www.youtube.com/oembed?url=https://youtu.be/{video_id}&format=json",
            timeout=5,
        )
        if resp.ok:
            return resp.json().get("title", "")
    except Exception:
        pass
    return ""
