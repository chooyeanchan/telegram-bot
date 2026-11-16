"""질문과 의미가 가까운 청크를 찾고, 그 내용을 근거로 답변한다.

의미 검색(임베딩)만으로는 날짜("작년 이맘때")와 정확한 제목("2026")을 잘 못 찾기 때문에
1) 질문에서 날짜 조건을 뽑아 해당 기간 노트로 좁히고
2) 제목/폴더에 질문 단어가 들어 있으면 가산점을 준다.
"""
import os
import re
from datetime import date

import numpy as np

import config
from services.indexer import connect
from services.ollama_client import chat, embed

SYSTEM_PROMPT = """너는 사용자의 옵시디언 노트를 검색해 주는 비서다.
오늘 날짜는 {today}이다.
- 반드시 아래 [노트] 내용만 근거로 한국어로 답한다.
- 질문에 맞는 노트가 여러 개면 날짜와 질문 조건(연도, 시기)에 가장 맞는 노트를 우선한다.
- 노트에 답이 없으면 "노트에서 찾지 못했어요"라고 말하고 추측하지 않는다.
- 근거가 된 노트는 === 사이에 적힌 실제 제목 그대로 [[제목]] 형식으로 언급한다. "노트 1" 같은 번호로 부르지 않는다.
- 답변에 === 표시나 폴더 경로는 쓰지 않는다. 노트를 나열할 때는 "- [[제목]]: 한 줄 요약" 형식으로 쓴다."""

# 검색 품질을 떨어뜨리는 말투/요청 표현 (임베딩·키워드 매칭에서 제거)
FILLER = re.compile(
    r"(찾아\s*줘|찾아\s*줄래|찾아|알려\s*줘|보여\s*줘|정리해\s*줘|뭐였지|뭐였어|뭐야|뭐지|"
    r"있어|있나|좀|관련해서|관련된|관련|대해서|대한|노트|[?？!.,])"
)
DATE_WORDS = re.compile(
    r"(재작년|작년|지난해|올해|금년|이번\s*해|내년|이맘때\s*쯤?|요즘|최근|"
    r"(19|20)\d{2}\s*년?|\d{2}\s*년|\d{1,2}\s*월|지난\s*달|이번\s*달|저번\s*달)"
)


# ---------- 날짜 ----------

def note_date(path):
    """노트 경로에서 (연, 월) 추출. 월을 모르면 None."""
    name = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r"(\d{2})(\d{2})(\d{2})(?:\D|$)", name)
    if m and 1 <= int(m.group(2)) <= 12:
        return 2000 + int(m.group(1)), int(m.group(2))
    m = re.fullmatch(r"(20\d{2})", name.strip())  # 예: 2026.md
    if m:
        return int(m.group(1)), None
    m = re.search(r"(?:^|/)(20\d{2})(?:/|$)", os.path.dirname(path))  # 예: 정리/2025/
    if m:
        return int(m.group(1)), None
    return None


def parse_date_query(q, today=None):
    """질문에서 (연도 집합, 월 집합)을 뽑는다. 조건이 없으면 None."""
    today = today or date.today()
    years, months = set(), set()

    if "재작년" in q:
        years.add(today.year - 2)
    elif "작년" in q or "지난해" in q:
        years.add(today.year - 1)
    if any(w in q for w in ("올해", "금년", "이번 해", "이번해")):
        years.add(today.year)
    if "내년" in q:
        years.add(today.year + 1)
    for y in re.findall(r"((?:19|20)\d{2})", q):
        years.add(int(y))
    for y in re.findall(r"(?<!\d)(\d{2})\s*년", q):
        years.add(2000 + int(y))

    if "이맘때" in q:
        months |= {(today.month + d - 1) % 12 + 1 for d in (-1, 0, 1)}
        if not years:
            years.add(today.year)
    for mo in re.findall(r"(?<!\d)(\d{1,2})\s*월", q):
        if 1 <= int(mo) <= 12:
            months.add(int(mo))
    if re.search(r"(이번|요번)\s*달", q):
        years.add(today.year)
        months.add(today.month)
    if re.search(r"(지난|저번)\s*달", q):
        y, mo = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
        years.add(y)
        months.add(mo)

    if not years and not months:
        return None
    return years, months


def _sort_date(path):
    d = note_date(path)
    return (d[0], d[1] or 0) if d else (0, 0)


def date_match(path, cond):
    d = note_date(path)
    if not d:
        return False
    years, months = cond
    y, mo = d
    if years and y not in years:
        return False
    if months and mo is not None and mo not in months:
        return False
    return True


# ---------- 질문 의도 (LLM) ----------

INTENT_PROMPT = """사용자가 자기 옵시디언 노트에 검색 질문을 했다. 질문 의도를 분석해 JSON으로만 답하라.

[폴더 목록: 폴더 | 이 폴더 노트의 목적]
{folders}

[출력 형식]
{{"folders": ["질문이 찾는 노트가 있을 폴더 1~2개, 위 목록의 폴더 경로 그대로. 확실하지 않으면 빈 배열"],
 "query": "날짜 표현과 요청 말투(찾아줘, 뭐야 등)를 뺀 검색용 핵심 문장",
 "latest": "질문이 가장 최근/마지막 노트를 원하면 true, 아니면 false"}}

[질문]
{question}"""


def interpret(question):
    """LLM으로 질문이 찾는 폴더와 핵심 검색어를 뽑는다. 실패하면 빈 결과."""
    import json

    if not config.FOLDERS:
        return {"folders": [], "query": "", "latest": False}
    folders = "\n".join(f"- {k} | {v}" for k, v in config.FOLDERS.items())
    try:
        raw = chat(
            [{"role": "user", "content": INTENT_PROMPT.format(folders=folders, question=question)}],
            json_mode=True,
            temperature=0,
        )
        data = json.loads(raw)
    except Exception:
        return {"folders": [], "query": "", "latest": False}
    picked = [f for f in data.get("folders", []) if f in config.FOLDERS][:2]
    latest = data.get("latest") in (True, "true", "True")
    return {"folders": picked, "query": str(data.get("query", "")).strip(), "latest": latest}


# ---------- 검색 ----------

def _keywords(q):
    q = DATE_WORDS.sub(" ", q)
    q = FILLER.sub(" ", q)
    return [w for w in q.split() if len(w) >= 2]


# ---------- 키워드 검색 (BM25) ----------
# 임베딩은 '맥켈란', 'AZ-900', '홈플러스' 같은 고유명사를 잘 못 잡는다.
# 한국어는 조사가 붙으므로(제주도에서, 제주도의) 단어를 2글자씩 쪼갠 bigram으로 맞춘다.

W_LEX = 0.25     # 키워드 점수(0~1) 가중치
W_TITLE = 0.15   # 제목에 질문 단어가 들어 있을 때 가중치
W_FOLDER = 0.05  # LLM이 고른 폴더의 노트 가산점 (LLM이 자주 틀리므로 너무 크면 안 된다)
LATEST_WORDS = re.compile(r"(최근|최신|마지막|요즘|가장\s*늦|제일\s*늦|latest)")


def _tokens(text):
    out = []
    for w in re.findall(r"[0-9a-z]+(?:-[0-9a-z]+)*|[가-힣]+", text.lower()):
        if re.match(r"[가-힣]", w):
            out += [w[i : i + 2] for i in range(len(w) - 1)] if len(w) >= 2 else []
        elif len(w) >= 2:
            out.append(w)
    return out


class _Index:
    def __init__(self, rows):
        from collections import Counter, defaultdict

        self.rows = rows
        mat = np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows])
        self.mat = mat / (np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9)
        self.post = defaultdict(list)
        lens = []
        for i, r in enumerate(rows):
            tf = Counter(_tokens(r[2]))
            lens.append(sum(tf.values()))
            for t, c in tf.items():
                self.post[t].append((i, c))
        self.lens = np.asarray(lens, dtype=np.float32)
        self.avg = float(self.lens.mean()) or 1.0
        self.titles = [set(_tokens(os.path.splitext(os.path.basename(r[0]))[0])) for r in rows]

    def bm25(self, qtokens, k1=1.2, b=0.75):
        n = len(self.rows)
        s = np.zeros(n, dtype=np.float32)
        for t in set(qtokens):
            plist = self.post.get(t)
            if not plist:
                continue
            idf = np.log(1 + (n - len(plist) + 0.5) / (len(plist) + 0.5))
            ids = np.fromiter((i for i, _ in plist), dtype=np.int64)
            tf = np.fromiter((c for _, c in plist), dtype=np.float32)
            s[ids] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * self.lens[ids] / self.avg))
        return s / s.max() if s.max() > 0 else s

    def idf(self, t):
        n, df = len(self.rows), len(self.post.get(t, ()))
        return float(np.log(1 + (n - df + 0.5) / (df + 0.5)))

    def title_match(self, qtokens):
        """제목에 들어 있는 질문 단어의 비율. 흔한 단어(생각, 공부)보다 드문 단어(ITIL)에 무게를 둔다."""
        w = {t: self.idf(t) for t in set(qtokens)}
        total = sum(w.values())
        if not total:
            return np.zeros(len(self.rows), dtype=np.float32)
        return np.asarray([sum(v for t, v in w.items() if t in tt) / total for tt in self.titles], dtype=np.float32)


_cache = {"key": None, "index": None}


def _load():
    """인덱스를 메모리에 올려 둔다. DB가 바뀌었을 때만 다시 읽는다."""
    key = os.path.getmtime(config.DB_PATH) if os.path.exists(config.DB_PATH) else None
    if _cache["key"] != key or _cache["index"] is None:
        db = connect()
        rows = db.execute("SELECT path, heading, text, vec FROM chunks").fetchall()
        db.close()
        _cache["index"] = _Index(rows) if rows else None
        _cache["key"] = key
    return _cache["index"]


def search(query, k=config.TOP_K, today=None, intent=None):
    index = _load()
    if index is None:
        return []
    rows = index.rows

    cond = parse_date_query(query, today)            # 날짜: 규칙으로 정확하게
    intent = intent if intent is not None else interpret(query)  # 의도: LLM
    keywords = _keywords(query)

    # 의미 검색은 LLM이 정리한 핵심 문장 + 의도 폴더의 목적 설명으로
    core = intent["query"] or " ".join(keywords) or query
    purpose = " ".join(config.FOLDERS[f] for f in intent["folders"])
    q = np.asarray(embed([f"{purpose} {core}".strip()])[0], dtype=np.float32)
    q /= np.linalg.norm(q) + 1e-9
    scores = index.mat @ q

    # 키워드 점수: 사용자가 쓴 단어 그대로 + LLM이 정리한 핵심어
    user_tok = _tokens(" ".join(keywords))
    scores += W_LEX * index.bm25(user_tok + _tokens(" ".join(_keywords(intent["query"]))))
    scores += W_TITLE * index.title_match(user_tok)

    for i, r in enumerate(rows):
        # 질문 의도에 맞는 폴더의 노트
        if any(r[0].startswith(f + "/") for f in intent["folders"]):
            scores[i] += W_FOLDER

    idx = list(np.argsort(-scores))
    # 날짜 조건이 있으면 해당 기간 노트로 좁힌다 (하나도 없으면 전체에서)
    if cond:
        filtered = [i for i in idx if date_match(rows[i][0], cond)]
        if filtered:
            idx = filtered
    # "최근/마지막" 질문이면 관련 있는 노트(1등 점수와 가까운 것)만 남기고 최신순으로
    # '최근/마지막'은 LLM 판단이 자주 틀려서, 질문에 그런 말이 직접 있을 때만 쓴다
    if intent["latest"] and LATEST_WORDS.search(query) and not cond:
        best = scores[idx[0]]
        top = [i for i in idx[:30] if scores[i] >= best - 0.12]
        idx = sorted(top, key=lambda i: _sort_date(rows[i][0]), reverse=True)

    results, per_note = [], {}
    for i in idx:
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


def _label(path):
    title = os.path.splitext(os.path.basename(path))[0]
    d = note_date(path)
    when = (f"{d[0]}년 {d[1]}월" if d[1] else f"{d[0]}년") if d else "날짜 모름"
    return f"=== [[{title}]] ({when}, {os.path.dirname(path)}) ==="


def answer(query):
    hits = search(query)
    if not hits:
        return "인덱스가 비어 있어요. 먼저 인덱싱을 실행해 주세요.", []
    # 1등과 점수 차이가 큰 노트는 관련 없는 것으로 보고 뺀다 (출처 목록도 깔끔하게)
    hits = [h for h in hits if h["score"] >= hits[0]["score"] - 0.2]
    context = "\n\n".join(f"{_label(h['path'])}\n{h['text']}" for h in hits)
    cond = parse_date_query(query)
    if cond:
        y = ", ".join(f"{v}년" for v in sorted(cond[0]))
        m = ", ".join(f"{v}월" for v in sorted(cond[1]))
        context = f"(질문의 날짜 조건: {y} {m}. 이 기간 노트를 모두 고려할 것)\n\n" + context
    reply = chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT.format(today=date.today().isoformat())},
            {"role": "user", "content": f"[노트]\n{context}\n\n[질문]\n{query}"},
        ]
    )
    # 내부용 라벨(=== [[제목]] (날짜, 폴더) ===)이 답변에 새어 나오면 지운다
    reply = re.sub(r"^\s*===.*?===\s*$", "", reply, flags=re.M).strip()
    # 출처는 답변이 실제로 [[제목]]으로 언급한 노트만 보여준다 (언급이 없으면 상위 노트만)
    cited = [h for h in hits if f"[[{os.path.splitext(os.path.basename(h['path']))[0]}]]" in reply]
    if cited:
        hits = cited
    elif "찾지 못했" in reply:
        hits = []
    else:
        hits = [h for h in hits if h["path"] == hits[0]["path"]]
    return reply, hits
