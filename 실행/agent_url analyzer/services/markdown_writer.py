import os
import re
from datetime import datetime


def save_markdown(summary: dict, icloud_path: str) -> str:
    os.makedirs(icloud_path, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    file_prefix = now.strftime("%y%m%d")  # YYMMDD
    slug = _slugify(summary["title"])
    filename = f"{file_prefix} {slug}.md"
    filepath = os.path.join(icloud_path, filename)

    content = f"""---
url: {summary['url']}
type: {summary['type']}
date: {date_str}
---

## 요약

{summary['summary']}

## 핵심 포인트

{summary['points']}
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath


def _slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s가-힣]", "", text)
    text = re.sub(r"[\s_]+", " ", text)
    return text[:50]
