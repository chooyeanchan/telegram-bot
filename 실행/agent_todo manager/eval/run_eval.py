"""검색 품질 평가: python eval/run_eval.py  (노트 단위 hit@1, hit@5, MRR)"""
import json
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.search import interpret, search  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = date(2026, 11, 17)


def main(quiet=False):
    path = os.path.join(HERE, "queries.json")
    if not os.path.exists(path):
        path = os.path.join(HERE, "queries.example.json")
    qs = json.load(open(path, encoding="utf-8"))
    # LLM 의도 해석은 느리고 매번 같으므로 캐시해서 검색 로직만 비교한다
    cache_path = os.path.join(HERE, "intent_cache.json")
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    for q, _ in qs:
        if q not in cache:
            cache[q] = interpret(q)
    json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    h1 = h5 = mrr = 0
    t0 = time.time()
    for q, gold in qs:
        hits = search(q, k=8, today=TODAY, intent=cache[q])
        notes = list(dict.fromkeys(os.path.splitext(os.path.basename(h["path"]))[0] for h in hits))[:5]
        rank = next((i + 1 for i, n in enumerate(notes) if n in gold), None)
        h1 += rank == 1
        h5 += rank is not None
        mrr += 1 / rank if rank else 0
        mark = "✅" if rank == 1 else ("🟡" if rank else "❌")
        quiet or print(f"{mark} {rank or '-'}  {q}  →  {notes[:3]}")
    n = len(qs)
    quiet or print(f"\nhit@1 {h1}/{n}  hit@5 {h5}/{n}  MRR {mrr / n:.3f}  ({(time.time() - t0) / n:.1f}s/q)")
    return h1, h5, mrr / n


if __name__ == "__main__":
    main()
