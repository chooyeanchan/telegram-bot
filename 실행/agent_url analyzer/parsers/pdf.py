import io
import requests
import pdfplumber


def parse_pdf(url: str) -> dict:
    pdf_bytes = _download_pdf(url)
    text = _extract_text(pdf_bytes)

    if not text or len(text.strip()) < 50:
        raise ValueError("PDF에서 텍스트를 추출할 수 없습니다. 스캔된 이미지 PDF일 수 있습니다.")

    return {
        "type": "pdf",
        "title": _title_from_url(url),
        "content": text,
        "url": url,
    }


def _download_pdf(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        raise ValueError(f"PDF 다운로드 실패: {e}")


def _extract_text(pdf_bytes: bytes) -> str:
    text_parts = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _title_from_url(url: str) -> str:
    filename = url.rstrip("/").split("/")[-1]
    return filename.replace(".pdf", "").replace("-", " ").replace("_", " ")
