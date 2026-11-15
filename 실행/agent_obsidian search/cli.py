"""터미널 테스트용.
  python cli.py index          # 인덱스 생성/갱신
  python cli.py search "질문"  # 검색 결과만 보기
  python cli.py ask "질문"     # 검색 + 답변
"""
import sys
import time

from services.indexer import update_index
from services.search import answer, search


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd, q = sys.argv[1], " ".join(sys.argv[2:])
    t = time.time()
    if cmd == "index":
        new, upd, rem = update_index(
            progress=lambda i, n, p: print(f"\r[{i}/{n}] {p[:60]:<60}", end="", flush=True)
        )
        print(f"\n추가 {new}, 갱신 {upd}, 삭제 {rem}")
    elif cmd == "search":
        for h in search(q):
            print(f"{h['score']:.3f}  {h['path']}  # {h['heading']}")
    elif cmd == "ask":
        reply, hits = answer(q)
        print(reply)
        print("\n출처:", ", ".join(sorted({h["path"] for h in hits})))
    print(f"({time.time() - t:.1f}s)")


if __name__ == "__main__":
    main()
