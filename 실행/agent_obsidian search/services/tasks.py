"""할 일(체크박스) 질문은 LLM 없이 노트 원문에서 바로 답하고, "○○ 할일 추가해줘"는 노트에 직접 적는다.

8B 모델은 "- [x]"(완료)와 "- [ ]"(미완료)를 구분하지 못해 끝낸 일까지 할 일로 늘어놓는다.
체크 여부는 글자 그대로 정해진 사실이므로, 규칙으로 읽어 오는 편이 빠르고 정확하다.
검색 인덱스가 아니라 볼트의 노트 파일을 직접 읽으니 방금 체크한 것도 바로 반영된다.
"""
import os
import re

import config

TASK_DIR = "1.1_tasks"
DEFAULT_NOTE = "1_to do list.md"

# 체크리스트 카테고리 (사용자가 설명한 용도) → (이모지, 이름)
CATEGORIES = {
    "1_to do list.md": ("📅", "매일 할 일"),
    "2_monthly check.md": ("🗓️", "월간 점검"),
    "3_deep clean.md": ("🧹", "분기 대청소"),
    "4_life rules&plan.md": ("🌱", "생활 규칙·계획"),
}

# 할 일을 묻는 질문인지 ("할 일", "투두", "해야 할 것", "남은 일" ...)
TODO_Q = re.compile(
    r"(할\s*일|할\s*것|할\s*거|투\s*두|to\s*-?\s*do|해야\s*(할|하는|될|되는|돼|되)|남은\s*(일|것|거|항목)|남았|"
    r"체크\s*리스트|미완료|안\s*한\s*(일|것|거)|못\s*한\s*(일|것|거))",
    re.I,
)
# 끝낸 일을 묻는 질문인지 ("완료한 일", "끝낸 것", "한 일")
DONE_Q = re.compile(r"(완료|끝낸|끝난|마친|체크된|체크한|(?<![안못할])\s한\s*(일|것|거)|^한\s*(일|것|거)|했던\s*(일|것|거))")
DONE_ITEMS = re.compile(r"(완료|끝낸|끝난|마친|체크한|체크된)\s*(한\s*)?(일|것|거|항목|목록)")
NOT_DONE = re.compile(r"(미완료|안\s*한|못\s*한|남은)")
# 특정 리스트가 아니라 체크리스트 전체 현황을 묻는 질문
OVERVIEW_Q = re.compile(
    r"(현황|전체|모든|모두|카테고리|종류|어떤\s*(리스트|체크|목록)|무슨\s*(리스트|체크|목록)|리스트\s*뭐|체크\s*리스트\s*뭐)"
)

# 질문 단어 → 어느 할 일 노트를 볼지 (없으면 기본 to do list)
NOTE_HINTS = [
    (re.compile(r"(매일|오늘|데일리|daily)", re.I), "1_to do list.md"),
    (re.compile(r"(월간|매달|이번\s*달\s*점검|점검|monthly)", re.I), "2_monthly check.md"),
    (re.compile(r"(대청소|청소|deep\s*clean)", re.I), "3_deep clean.md"),
    (re.compile(r"(버킷|위시|네거티브|인생\s*계획|생활\s*규칙)", re.I), "4_life rules&plan.md"),
]

# "○○ 할일 추가해줘", "할일에 ○○ 넣어줘"
LIST_WORD = (
    r"(오늘\s*|매일\s*)?(할\s*일|투\s*두|to\s*-?\s*do(\s*list)?|체크\s*리스트|리스트|월간\s*점검|대청소|버킷\s*리스트)"
    r"(\s*(목록|리스트))?\s*(에다가|에다|에|으로|로)?"
)
ADD_CMD = re.compile(r"\s*(을|를)?\s*(추가|넣어|등록|적어)\s*(해)?\s*(줘|줄래|주세요|줘요|요|해)?\s*[.!?~]*\s*$")
ADD_Q = re.compile(LIST_WORD, re.I)

ITEM = re.compile(r"^(\s*)[-*+]\s+(?:\[( |x|X)\]\s*)?(.*)$")


def is_task_question(q):
    if TODO_Q.search(q) or DONE_ITEMS.search(q):
        return True
    # "대청소 체크한 거", "월간 점검 완료" 처럼 할 일 노트 이름 + 체크/완료
    return _pick_note(q) != DEFAULT_NOTE and bool(re.search(r"(체크|완료|끝)", q))


def _pick_note(q):
    for pat, name in NOTE_HINTS:
        if pat.search(q):
            return name
    return DEFAULT_NOTE


def _path(name):
    return os.path.join(config.VAULT_PATH, TASK_DIR, name)


def parse(text):
    """목록을 트리로: 각 항목 = {text, state('open'|'done'|None), children}. None은 체크박스 없는 묶음 제목."""
    root = {"text": "", "state": None, "children": [], "indent": -1}
    stack = [root]
    for line in text.splitlines():
        m = ITEM.match(line.replace("\t", "    "))
        if not m:
            continue
        indent, box, body = len(m.group(1)), m.group(2), m.group(3).strip()
        body = re.sub(r"\*\*", "", body).strip()
        if not body:
            continue
        state = None if box is None else ("open" if box == " " else "done")
        node = {"text": body, "state": state, "children": [], "indent": indent}
        while stack[-1]["indent"] >= indent:
            stack.pop()
        stack[-1]["children"].append(node)
        stack.append(node)
    return root


def _select(node, want):
    """want 상태의 항목만 남긴 트리. 묶음 제목은 아래에 남는 항목이 있을 때만 남긴다.
    미완료를 볼 때 완료된 항목은 그 아래까지 통째로 뺀다(끝난 일의 세부 단계는 볼 필요 없음)."""
    if want == "open" and node["state"] == "done":
        return None
    kids = [k for k in (_select(c, want) for c in node["children"]) if k]
    if node["state"] == want or kids:
        return {**node, "children": kids}
    return None


def _count(node, want):
    """세부 항목이 있는 상위 항목(예: '26년 4분기')은 묶음이므로 맨 아래 항목만 센다."""
    if not node["children"]:
        return int(node["state"] == want)
    return sum(_count(c, want) for c in node["children"])


def _status(tree):
    """(미체크, 체크) 개수"""
    sel = _select(tree, "open")
    return (_count(sel, "open") if sel else 0), _count(tree, "done")


def _lines(node, want, depth=0):
    """보기 좋은 목록: 묶음 제목은 굵게, 항목은 ☐/✅, 깊이마다 들여쓰기."""
    out = []
    mark = "✅" if want == "done" else "☐"
    for c in node["children"]:
        pad = "      " * depth
        if c["children"]:  # 아래 항목이 있으면 묶음 제목
            out.append(f"{pad}{'▸' if depth else '📌'} **{c['text']}**")
        else:
            out.append(f"{pad}{mark} {c['text']}")
        out += _lines(c, want, depth + 1)
    return out


def _read(name):
    try:
        with open(_path(name), encoding="utf-8") as f:
            return parse(f.read())
    except OSError:
        return None


def _overview():
    lines = ["📋 **체크리스트 현황**", ""]
    for name, (emoji, label) in CATEGORIES.items():
        tree = _read(name)
        if tree is None:
            continue
        o, d = _status(tree)
        lines.append(f"{emoji} **{label}**  ☐ {o}개 · ✅ {d}개")
        # 지금 진행 중인 묶음(예: 26년 4분기, 26년 10월)을 같이 보여준다
        sel = _select(tree, "open")
        groups = [c["text"] for c in (sel["children"] if sel else []) if c["children"]][:3]
        if groups:
            lines.append("      ▸ " + " · ".join(groups))
    lines += ["", "💬 \"대청소 뭐 남았어?\"처럼 물으면 그 리스트만 자세히 보여드려요."]
    return "\n".join(lines), []


# ---------- 할 일 추가 ----------

def parse_add(q):
    """'대장내시경 약 먹기 할일 추가해줘' → (노트 파일명, '대장내시경 약 먹기'). 추가 명령이 아니면 None."""
    q = q.strip()
    m = ADD_CMD.search(q)
    if not m or not ADD_Q.search(q[: m.start()] + " "):
        return None
    body = q[: m.start()]
    name = _pick_note(body)
    # 맨 앞이나 맨 뒤의 '할일에', '투두 리스트에' 같은 말을 걷어내면 남는 게 할 일 내용
    item = re.sub(rf"^\s*{LIST_WORD}\s*", "", body, flags=re.I)
    item = re.sub(rf"\s*{LIST_WORD}\s*$", "", item, flags=re.I)
    item = re.sub(r"\s*(을|를)$", "", item.strip()).strip(" \"'“”‘’")
    if len(item) < 2:
        return None
    return name, item


def add_task(name, item):
    """체크리스트에 '- [ ] item'을 넣는다.
    to do list는 '___' 구분선 위(미완료 묶음 끝)에, 다른 리스트는 맨 끝에 넣는다."""
    path = _path(name)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    open_items = [c["text"] for c in (_select(parse(text), "open") or {"children": []})["children"]]
    if item in open_items:
        return False
    lines = text.split("\n")
    new = f"- [ ] {item}"
    sep = next((i for i, l in enumerate(lines) if re.fullmatch(r"\s*(___+|---+|\*\*\*+)\s*", l)), None)
    if sep is not None:
        lines.insert(sep, new)
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append(new)
        lines.append("")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    os.replace(tmp, path)  # 한 번에 바꿔치기: 쓰는 도중 iCloud가 반쪽짜리 파일을 올리지 않게
    return True


def try_add(query):
    parsed = parse_add(query)
    if not parsed:
        m = ADD_CMD.search(query.strip())
        if m and re.fullmatch(rf"\s*{LIST_WORD}\s*", query.strip()[: m.start()], flags=re.I):
            return "✍️ 어떤 할 일을 추가할까요?\n\n예) \"대장내시경 약 먹기 할일 추가해줘\"", []
        return None
    name, item = parsed
    emoji, label = CATEGORIES.get(name, ("📋", "체크리스트"))
    try:
        added = add_task(name, item)
    except OSError as e:
        return f"⚠️ {label}에 추가하지 못했어요: {e}", []
    o, d = _status(_read(name))
    if not added:
        return f"💡 이미 {emoji} **{label}**에 있어요.\n\n☐ {item}", []
    return f"✍️ {emoji} **{label}**에 추가했어요.\n\n☐ {item}\n\n지금 남은 할 일 ☐ {o}개 · 체크 ✅ {d}개", []


# ---------- 할 일 조회 ----------

def try_answer(query):
    """할 일 추가/조회 질문이면 (답변, 출처) 반환, 아니면 None."""
    added = try_add(query)
    if added:
        return added
    if not is_task_question(query):
        return None
    name = _pick_note(query)
    if name == DEFAULT_NOTE and OVERVIEW_Q.search(query):
        return _overview()
    root = _read(name)
    if root is None:
        return None
    want = "done" if DONE_Q.search(query) and not NOT_DONE.search(query) else "open"
    n_open, n_done = _status(root)
    emoji, label = CATEGORIES.get(name, ("📋", "체크리스트"))
    status = f"{emoji} **{label}**\n☐ 남은 일 {n_open}개 · ✅ 체크 {n_done}개"
    n = n_done if want == "done" else n_open
    if not n:
        msg = "체크한 항목이 아직 없어요." if want == "done" else "남은 할 일이 없어요. 전부 체크했어요 👏"
        return f"{status}\n\n{msg}", []
    head = "✅ 체크한 항목" if want == "done" else "📝 아직 남은 일"
    lines = _lines(_select(root, want), want)
    if len(lines) > 45:  # 텔레그램 한 메시지에 들어가도록 (완료 목록은 수십 개라 위쪽 최근 것만)
        lines = lines[:45] + [f"… 외 {len(lines) - 45}줄은 노트에서 확인해 주세요"]
    return f"{status}\n\n{head}\n" + "\n".join(lines), []
