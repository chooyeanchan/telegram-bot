import trafilatura
import requests
from urllib.parse import urlparse


def parse_webpage(url: str) -> dict:
    content = _fetch_with_trafilatura(url)

    if not content or len(content.strip()) < 100:
        raise ValueError("본문 콘텐츠를 추출할 수 없습니다. 페이월이나 로그인이 필요한 페이지일 수 있습니다.")

    title = _extract_title(url, content)

    return {
        "type": _detect_type(url),
        "title": title,
        "content": content,
        "url": url,
    }


def _fetch_with_trafilatura(url: str):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        downloaded = response.text
    except Exception as e:
        # trafilatura 자체 다운로드로 폴백
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise ValueError(f"페이지 다운로드 실패: {e}")

    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    return result


def _extract_title(url: str, content: str) -> str:
    # 본문 첫 줄을 제목으로 사용
    first_line = content.strip().split("\n")[0][:80]
    return first_line if first_line else urlparse(url).netloc


def _detect_type(url: str) -> str:
    news_domains = [
        "naver.com/news", "daum.net/news", "chosun.com", "joongang.co.kr",
        "hani.co.kr", "donga.com", "bbc.com", "cnn.com", "reuters.com",
        "yonhapnews.co.kr", "yna.co.kr", "khan.co.kr",
    ]
    for domain in news_domains:
        if domain in url:
            return "news"
    return "blog"
