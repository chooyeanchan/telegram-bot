"""볼트의 .md 노트를 청크로 나누고 임베딩해서 SQLite에 저장한다.
수정 시간이 바뀐 노트만 다시 처리한다(증분 인덱싱)."""
import logging
import os
import re
import sqlite3
import unicodedata

import numpy as np

import config
from services.ollama_client import embed

logger = logging.getLogger(__name__)

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.M)

# 청크 규칙이 바뀌면 올린다 → 다음 인덱싱 때 전체를 다시 만든다
INDEX_VERSION = "3"
MIN_CHUNK_CHARS = 200  # 이보다 짧은 섹션은 다음 섹션과 합친다

# 검색에 쓸모없는 섹션(출처 목록 등): 긴 URL 덩어리라 아무 질문에나 걸리는 잡음이 된다
SKIP_HEADING = re.compile(r"^(참고\s*(출처|자료|문헌|링크)|출처|레퍼런스|references?|sources?|links?)\b", re.I)


def clean_text(text):
    """URL·이미지·링크 문법을 걷어내고 사람이 읽는 글자만 남긴다."""
    text = re.sub(r"!\[\[[^\]]*\]\]", " ", text)                  # ![[이미지]]
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)              # ![alt](url)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)            # [글자](url) → 글자
    text = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", text)     # [[노트|별칭]] → 별칭
    text = re.sub(r"https?://\S+", " ", text)                       # 맨 URL
    text = re.sub(r"<[^>]+>", " ", text)                             # html 태그
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def connect():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    db = sqlite3.connect(config.DB_PATH)
    db.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, mtime REAL)")
    db.execute(
        "CREATE TABLE IF NOT EXISTS chunks ("
        " id INTEGER PRIMARY KEY, path TEXT, heading TEXT, text TEXT, vec BLOB)"
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)")
    db.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")
    return db


def _excluded(rel):
    parts = rel.split(os.sep)
    for ex in config.EXCLUDE_DIRS:
        ex_parts = ex.strip("/").split("/")
        if parts[: len(ex_parts)] == ex_parts:
            return True
    return any(p.startswith(".") for p in parts)


def list_notes():
    notes = {}
    # 권한이 없으면 os.walk는 오류 없이 빈 결과를 내므로 먼저 직접 열어 확인한다
    # (예: launchd로 띄운 프로세스가 iCloud 볼트에 접근 권한이 없을 때)
    os.listdir(config.VAULT_PATH)

    def _onerror(e):
        raise e

    for root, dirs, files in os.walk(config.VAULT_PATH, onerror=_onerror):
        rel_root = os.path.relpath(root, config.VAULT_PATH)
        rel_root = "" if rel_root == "." else rel_root
        dirs[:] = [d for d in dirs if not _excluded(os.path.join(rel_root, d))]
        for f in files:
            if not f.endswith(".md"):
                continue
            rel = os.path.join(rel_root, f)
            if _excluded(rel):
                continue
            full = os.path.join(root, f)
            # macOS 파일명은 NFD(자모 분리)일 수 있어 NFC로 통일해 저장한다
            notes[unicodedata.normalize("NFC", rel)] = (os.path.getmtime(full), full)
    return notes


def chunk_note(rel, text):
    """제목(heading) 단위로 나누고, 긴 섹션은 문단 기준으로 다시 자른다."""
    text = clean_text(FRONTMATTER.sub("", text))
    title = os.path.splitext(os.path.basename(rel))[0]
    sections, last, heading = [], 0, ""
    for m in HEADING.finditer(text):
        sections.append((heading, text[last : m.start()]))
        heading, last = m.group(2).strip(), m.start()
    sections.append((heading, text[last:]))

    # 제목만 있거나 한두 줄짜리 섹션은 따로 두면 내용 없는 벡터가 되어 아무 질문에나 걸린다
    # → 다음 섹션 앞에 붙여 하나로 만든다
    merged, carry = [], ""
    for heading, body in sections:
        body = body.strip()
        if not body or SKIP_HEADING.match(heading):
            continue
        body = f"{carry}\n\n{body}".strip() if carry else body
        if len(body) < MIN_CHUNK_CHARS:
            carry = body
            continue
        carry = ""
        merged.append((heading, body))
    if carry:
        if merged:
            merged[-1] = (merged[-1][0], f"{merged[-1][1]}\n\n{carry}")
        else:
            merged.append(("", carry))

    chunks = []
    for heading, body in merged:
        buf = ""
        for para in re.split(r"\n\s*\n", body):
            if len(buf) >= MIN_CHUNK_CHARS and len(buf) + len(para) > config.CHUNK_CHARS:
                chunks.append((heading, buf))
                buf = ""
            buf = f"{buf}\n\n{para}" if buf else para
            while len(buf) > config.CHUNK_CHARS * 1.5:
                chunks.append((heading, buf[: config.CHUNK_CHARS]))
                buf = buf[config.CHUNK_CHARS :]
        if buf.strip():
            chunks.append((heading, buf))
    # 임베딩 문맥을 위해 폴더 경로(예: yearly goals, sora letter)와 제목을 앞에 붙인다
    folder = " / ".join(
        re.sub(r"^[\d.]+_", "", p) for p in os.path.dirname(rel).split(os.sep) if p
    )
    _, purpose = config.folder_of(rel)
    prefix = f"[{folder} / {title}]" if folder else f"[{title}]"
    if purpose:
        prefix = f"[분류: {purpose}] {prefix}"
    out = [(h, f"{prefix} {h}\n{c}".strip()) for h, c in chunks if len(c.strip()) > 20]
    if not out:
        # 이미지만 있는 노트(손편지 사진 등)는 본문이 비어 검색에서 아예 사라진다
        # → 제목과 폴더만이라도 담은 청크를 만들어 제목으로는 찾을 수 있게 한다
        out = [("", f"{prefix}\n{title} (이 노트는 이미지나 첨부만 있고 본문 글은 없음)")]
    return out


def update_index(progress=None):
    """변경된 노트만 다시 인덱싱. (추가, 갱신, 삭제) 개수를 돌려준다."""
    db = connect()
    current = list_notes()
    known = dict(db.execute("SELECT path, mtime FROM files"))

    if known and not current:
        raise RuntimeError("볼트에서 노트를 하나도 찾지 못해 인덱스 삭제를 건너뜀 (볼트 경로·접근 권한 확인 필요)")
    removed = [p for p in known if p not in current]
    ver = db.execute("SELECT value FROM meta WHERE key='version'").fetchone()
    if not ver or ver[0] != INDEX_VERSION:
        # 청크 규칙이 바뀌었으니 모든 노트를 다시 만든다 (기존 청크는 노트별로 교체되어 중간에 끊겨도 안전)
        changed = list(current)
    else:
        changed = [p for p, (mt, _) in current.items() if known.get(p) != mt]
        # 청크가 하나도 없는 노트(예전 규칙에서 빈 노트로 처리된 것)도 다시 만든다
        empty = {
            p for (p,) in db.execute(
                "SELECT path FROM files f WHERE NOT EXISTS (SELECT 1 FROM chunks c WHERE c.path=f.path)"
            )
        }
        changed += [p for p in current if p in empty and p not in changed]
    for p in removed:
        db.execute("DELETE FROM chunks WHERE path=?", (p,))
        db.execute("DELETE FROM files WHERE path=?", (p,))
    db.commit()

    for i, rel in enumerate(changed, 1):
        try:
            with open(current[rel][1], encoding="utf-8") as f:
                text = unicodedata.normalize("NFC", f.read())
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"읽기 실패 {rel}: {e}")
            continue
        chunks = chunk_note(rel, text)
        vecs = []
        for b in range(0, len(chunks), 16):
            vecs += embed([c for _, c in chunks[b : b + 16]])
        db.execute("DELETE FROM chunks WHERE path=?", (rel,))
        db.executemany(
            "INSERT INTO chunks (path, heading, text, vec) VALUES (?,?,?,?)",
            [
                (rel, h, c, np.asarray(v, dtype=np.float32).tobytes())
                for (h, c), v in zip(chunks, vecs)
            ],
        )
        db.execute("INSERT OR REPLACE INTO files VALUES (?,?)", (rel, current[rel][0]))
        db.commit()
        if progress:
            progress(i, len(changed), rel)

    if not ver or ver[0] != INDEX_VERSION:
        db.execute("INSERT OR REPLACE INTO meta VALUES ('version', ?)", (INDEX_VERSION,))
        db.commit()
    new = sum(1 for p in changed if p not in known)
    db.close()
    return new, len(changed) - new, len(removed)
