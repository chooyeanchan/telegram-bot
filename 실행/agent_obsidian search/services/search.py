"""질문과 의미가 가까운 청크를 찾고, 그 내용을 근거로 답변한다."""
import os

import numpy as np

import config
from services.indexer import connect
from services.ollama_client import chat, embed

SYSTEM_PROMPT = """너는 사용자의 옵시디언 노트를 검색해 주는 비서다.
- 반드시 아래 [노트] 내용만 근거로 한국어로 간결하게 답한다.
- 노트에 답이 없으면 "노트에서 찾지 못했어요"라고 말하고 추측하지 않는다.
- 근거가 된 노트는 === 사이에 적힌 실제 제목 그대로 [[제목]] 형식으로 언급한다. "노트 1" 같은 번호로 부르지 않는다."""


def _load():
    db = connect()
    rows = db.execute("SELECT path, heading, text, vec FROM chunks").fetchall()
    db.close()
    if not rows:
        return [], None
    mat = np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows])
    mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
    return rows, mat


def search(query, k=config.TOP_K):
    rows, mat = _load()
    if not rows:
        return []
    q = np.asarray(embed([query])[0], dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-9
    scores = mat @ q

    # 같은 노트가 결과를 독점하지 않도록 노트당 최대 2개
    results, per_note = [], {}
    for i in np.argsort(-scores):
        path = rows[i][0]
        if per_note.get(path, 0) >= 2:
            continue
        per_note[path] = per_note.get(path, 0) + 1
        results.append(
            {"path": path, "heading": rows[i][1], "text": rows[i][2], "score": float(scores[i])}
        )
        if len(results) >= k:
            break
    return results


def answer(query):
    hits = search(query)
    if not hits:
        return "인덱스가 비어 있어요. 먼저 인덱싱을 실행해 주세요.", []
    context = "\n\n".join(
        f"=== [[{os.path.splitext(os.path.basename(h['path']))[0]}]] ===\n{h['text']}"
        for h in hits
    )
    reply = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"[노트]\n{context}\n\n[질문]\n{query}"},
        ]
    )
    return reply.strip(), hits
