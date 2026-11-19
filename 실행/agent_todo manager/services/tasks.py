"""옵시디언 to do list 노트 하나만 다루는 할 일 관리.

- 오늘의 할 일: 아직 체크하지 않은 항목에 번호를 붙여 보여준다
- 추가: "○○ 추가해줘" → '___' 구분선 위에 "- [ ] ○○"
- 완료: "3 완료", "대장약 완료" → "- [x]"로 바꾸고 구분선 아래 완료 목록 맨 위로 옮긴다
- 되돌리기: "취소" → 방금 완료한 항목을 다시 할 일로

노트 파일을 직접 읽고 쓰므로 옵시디언에서 고친 내용도 바로 반영된다.
"""
import os
import re
from datetime import date

import config

NOTE = os.path.join("1.1_tasks", "1_to do list.md")

ITEM = re.compile(r"^(\s*)[-*+]\s+(?:\[( |x|X)\]\s*)?(.*)$")
SEP = re.compile(r"\s*(___+|---+|\*\*\*+)\s*")
WEEKDAY = "월화수목금토일"

# "○○ 추가해줘", "할일에 ○○ 넣어줘"
LIST_WORD = (
    r"(오늘\s*|매일\s*)?(할\s*일|투\s*두|to\s*-?\s*do(\s*list)?|체크\s*리스트|리스트)"
    r"(\s*(목록|리스트))?\s*(에다가|에다|에|으로|로)?"
)
ADD_CMD = re.compile(r"\s*(을|를)?\s*(추가|넣어|등록|적어)\s*(해)?\s*(줘|줄래|주세요|줘요|요|해)?\s*[.!?~]*\s*$")
# "3 완료", "대장약 다 했어", "○○ 체크해줘", "○○ 끝"
DONE_CMD = re.compile(
    r"\s*(을|를|은|는)?\s*(다\s*)?(완료|끝|체크|했어|했음|했다|했어요|해치웠어)\s*"
    r"(했어|했음|했어요|해줘|해\s*줘|처리|처리해줘|처리\s*해\s*줘|함|요|!)?\s*[.!?~]*\s*$"
)
UNDO_CMD = re.compile(r"^\s*(취소|되돌려|되돌리기|실행\s*취소|undo)(\s*(해\s*줘|해줘|해))?\s*[.!?~]*\s*$", re.I)
# 완료 목록을 보여 달라는 질문 ("완료한 거 보여줘", "끝낸 일 뭐 있어")
DONE_LIST_Q = re.compile(r"(완료|끝낸|끝난|체크한|체크된|한)\s*(일|것|거|항목|목록)")

_last_done = {"text": None}  # 되돌리기용: 마지막으로 완료한 항목


def _path():
    return os.path.join(config.VAULT_PATH, NOTE)


def _load():
    with open(_path(), encoding="utf-8") as f:
        return f.read().split("\n")


def _save(lines):
    path = _path()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    os.replace(tmp, path)  # 한 번에 바꿔치기: 쓰는 도중 iCloud가 반쪽짜리 파일을 올리지 않게


def _sep(lines):
    return next((i for i, l in enumerate(lines) if SEP.fullmatch(l)), None)


def parse(lines):
    """목록을 트리로. 각 항목 = {text, state('open'|'done'|None), line, indent, children}.
    state None은 체크박스 없는 묶음 제목(예: 💻 side project)."""
    root = {"text": "", "state": None, "children": [], "indent": -1, "line": -1}
    stack = [root]
    for i, line in enumerate(lines):
        m = ITEM.match(line.replace("\t", "    "))
        if not m:
            continue
        indent, box, body = len(m.group(1)), m.group(2), m.group(3).strip()
        body = body.replace("**", "").strip()
        if not body:
            continue
        state = None if box is None else ("open" if box == " " else "done")
        node = {"text": body, "state": state, "children": [], "indent": indent, "line": i}
        while stack[-1]["indent"] >= indent:
            stack.pop()
        node["parent"] = stack[-1]["text"] if stack[-1]["line"] >= 0 else None
        stack[-1]["children"].append(node)
        stack.append(node)
    return root


def _select(node, want):
    """want 상태의 항목만 남긴 트리 (묶음 제목은 아래 남는 항목이 있을 때만)."""
    if want == "open" and node["state"] == "done":
        return None
    kids = [k for k in (_select(c, want) for c in node["children"]) if k]
    if node["state"] == want or kids:
        return {**node, "children": kids}
    return None


def _leaves(node):
    """맨 아래 항목들 (번호를 붙이는 대상)"""
    if not node["children"]:
        return [node] if node["line"] >= 0 else []
    return [x for c in node["children"] for x in _leaves(c)]


def open_items(lines=None):
    tree = _select(parse(lines or _load()), "open")
    return tree, (_leaves(tree) if tree else [])


def _done_count(lines):
    tree = _select(parse(lines), "done")
    return len(_leaves(tree)) if tree else 0


def _numbered(tree):
    """번호 붙인 목록. 묶음 제목은 📌 굵게, 그 아래 항목은 들여쓰기."""
    out, n = [], 0

    def walk(node, depth):
        nonlocal n
        for c in node["children"]:
            pad = "      " * depth
            if c["children"]:
                out.append(f"{pad}{'📌' if depth == 0 else '▸'} **{c['text']}**")
                walk(c, depth + 1)
            else:
                n += 1
                out.append(f"{pad}{n}. {c['text']}")

    walk(tree, 0)
    return out


def today_message(greeting=True):
    lines = _load()
    tree, items = open_items(lines)
    d = date.today()
    if greeting is None:  # 다른 답변 아래에 붙이는 목록: 시작 문구 없이
        head = "📅 **지금 남은 할 일**"
    elif greeting:
        head = f"✅ 정리 완료!\n\n☀️ **{d.month}월 {d.day}일 {WEEKDAY[d.weekday()]}요일, 오늘의 할 일**"
    else:
        head = "✅ 조회 완료!\n\n📅 **할 일 목록**"
    status = f"☐ 남은 일 {len(items)}개 · ✔️ 완료 {_done_count(lines)}개"
    if not items:
        return f"{head}\n{status}\n\n남은 할 일이 없어요. 전부 끝냈어요 👏"
    tip = '💬 "3 완료"나 "대장약 완료"로 체크하고, "○○ 추가해줘"로 할 일을 넣어요.'
    return f"{head}\n{status}\n\n" + "\n".join(_numbered(tree)) + f"\n\n{tip}"


def done_message(limit=20):
    lines = _load()
    tree = _select(parse(lines), "done")
    items = _leaves(tree) if tree else []
    if not items:
        return "✅ 조회 완료!\n\n아직 완료한 항목이 없어요."
    shown = "\n".join(f"✔️ {x['text']}" for x in items[:limit])
    more = f"\n… 외 {len(items) - limit}개" if len(items) > limit else ""
    return f"✅ 조회 완료!\n\n✔️ **완료한 일** {len(items)}개 (최근 순)\n\n{shown}{more}"


# ---------- 추가 ----------

def _parse_add(q):
    m = ADD_CMD.search(q)
    if not m:
        return None
    item = re.sub(rf"^\s*{LIST_WORD}\s*", "", q[: m.start()], flags=re.I)
    item = re.sub(rf"\s*{LIST_WORD}\s*$", "", item, flags=re.I)
    return re.sub(r"\s*(을|를)$", "", item.strip()).strip(" \"'“”‘’")


def add(item):
    lines = _load()
    _, items = open_items(lines)
    if any(x["text"] == item for x in items):
        return f"✅ 확인 완료!\n\n이미 할 일에 있어서 추가하지 않았어요.\n☐ {item}"
    new = f"- [ ] {item}"
    sep = _sep(lines)
    if sep is not None:
        lines.insert(sep, new)
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += [new, ""]
    _save(lines)
    _, items = open_items(lines)
    return f"✅ 추가 완료!\n\n☐ {item}\n\n남은 일 {len(items)}개"


# ---------- 완료 ----------

def _norm(t):
    return re.sub(r"[\s\W_]+", "", t).lower()


def _bigrams(t):
    t = _norm(t)
    return {t[i : i + 2] for i in range(len(t) - 1)} or {t}


def find(ref, items):
    """'3', '3번', '2, 5' → 번호로, 그 밖에는 글자로 찾는다. 후보 목록을 돌려준다."""
    nums = re.findall(r"\d+", ref)
    if nums and re.fullmatch(r"[\d\s,번과와및and]+", ref.strip()):
        picked = [items[int(n) - 1] for n in nums if 1 <= int(n) <= len(items)]
        return picked, True
    r = _norm(ref)
    if not r:
        return [], False
    exact = [x for x in items if _norm(x["text"]) == r]
    if exact:
        return exact[:1], False
    inside = [x for x in items if r in _norm(x["text"])]
    if inside:
        return inside, False
    # 글자가 조금 달라도("대장 약" ↔ "대장약 먹기") 2글자 조각이 많이 겹치면 후보로
    rb = _bigrams(ref)
    scored = sorted(((len(rb & _bigrams(x["text"])) / len(rb), x) for x in items), key=lambda s: -s[0])
    return [x for s, x in scored if s >= 0.5][:5], "fuzzy"


def _block_end(lines, start, indent):
    """start 줄 아래로 들여쓰기가 더 깊은 줄(세부 항목)이 끝나는 위치"""
    end = start + 1
    while end < len(lines):
        m = ITEM.match(lines[end].replace("\t", "    "))
        if not lines[end].strip() or (m and len(m.group(1)) > indent):
            end += 1
            continue
        break
    return end


def _lead(line):
    return line[: len(line) - len(line.lstrip())]


def _complete_line(lines, item):
    """한 항목을 완료로: 세부 항목째 [x]로 바꿔 구분선 아래 완료 목록 맨 위로 옮긴다.
    묶음(예: 💻 side project) 안의 항목은 맨 바깥 항목으로 내어 옮긴다. 되돌릴 때 쓰려고 묶음 이름을 돌려준다."""
    i, indent = item["line"], item["indent"]
    sep = _sep(lines)
    if sep is None or i > sep:
        lines[i] = lines[i].replace("[ ]", "[x]", 1)
        return None
    end = _block_end(lines, i, indent)
    lead = _lead(lines[i])
    block = [(l[len(lead):] if l.startswith(lead) else l.lstrip()).replace("[ ]", "[x]", 1) for l in lines[i:end]]
    del lines[i:end]
    sep -= end - i
    lines[sep + 1 : sep + 1] = block
    return item.get("parent") if indent > 0 else None


def _do_complete(lines, found):
    # 아래 줄부터 처리해야 앞 줄 번호가 밀리지 않는다
    done = []
    for x in sorted(found, key=lambda x: -x["line"]):
        done.append((x["text"], _complete_line(lines, x)))
    _save(lines)
    _last_done["text"] = done
    _, left = open_items(lines)
    shown = "\n".join(f"✔️ ~~{x['text']}~~" for x in found)
    return f"✅ 체크 완료!\n\n{shown}\n\n☐ 남은 일 {len(left)}개 · 잘못 눌렀으면 \"취소\" 🎉"


def complete(ref):
    """규칙으로 완료 처리. 어떤 항목인지 글자로 못 찾으면 None (→ AI가 해석)."""
    lines = _load()
    _, items = open_items(lines)
    found, by_number = find(ref, items)
    if by_number == "fuzzy":
        return None  # 글자가 딱 맞지 않으면 바로 고치지 않고 AI 해석 + 확인 버튼으로
    if not found:
        if by_number:
            return f"✅ 확인 완료!\n\n{ref}번 할 일은 없어요.\n\n" + today_message(greeting=None)
        return None
    if len(found) > 1 and not by_number:
        cands = "\n".join(f"{items.index(x) + 1}. {x['text']}" for x in found)
        return f"✅ 확인 완료!\n\n비슷한 할 일이 여러 개예요. 번호로 알려 주세요 (예: \"{items.index(found[0]) + 1} 완료\")\n\n{cands}"
    return _do_complete(lines, found)


def complete_texts(texts):
    """확인받은 항목(글자 그대로)을 완료. 확인하는 사이 노트가 바뀌어도 맞는 줄을 고치도록 번호가 아니라 글자로 찾는다."""
    lines = _load()
    _, items = open_items(lines)
    found = [x for t in texts for x in items if x["text"] == t][: len(texts)]
    if not found:
        return "✅ 확인 완료!\n\n그사이 노트가 바뀌었는지 그 할 일을 찾지 못했어요.\n\n" + today_message(greeting=None)
    return _do_complete(lines, found)


def undo():
    """방금 완료한 항목을 할 일로 되돌린다. 묶음 안에 있던 항목은 그 묶음 끝으로 돌려놓는다."""
    done = _last_done["text"]
    if not done:
        return "✅ 확인 완료!\n\n되돌릴 완료 기록이 없어요. (봇을 다시 켜면 기록이 지워져요)"
    lines = _load()
    restored = []
    for t, parent in done:
        sep = _sep(lines)
        for i, l in enumerate(lines):
            m = ITEM.match(l.replace("\t", "    "))
            if not (m and m.group(2) in ("x", "X") and m.group(3).replace("**", "").strip() == t):
                continue
            indent = len(m.group(1))
            if sep is None or i < sep:
                lines[i] = re.sub(r"\[[xX]\]", "[ ]", l, count=1)
            else:
                end = _block_end(lines, i, indent)
                block = [re.sub(r"\[[xX]\]", "[ ]", x, count=1) for x in lines[i:end]]
                del lines[i:end]
                sep = _sep(lines)
                at, lead = sep, ""  # 기본: 구분선 바로 위(할 일 맨 끝)
                if parent:
                    tree = parse(lines)
                    par = next((n for n in _walk(tree) if n["text"] == parent and n["line"] < sep), None)
                    if par:
                        at = _block_end(lines, par["line"], par["indent"])
                        lead = _lead(lines[par["line"]]) + "\t"
                lines[at:at] = [lead + x for x in block]
            restored.append(t)
            break
    _save(lines)
    _last_done["text"] = None
    if not restored:
        return "✅ 확인 완료!\n\n방금 완료한 항목을 노트에서 찾지 못했어요."
    return "✅ 되돌리기 완료!\n\n↩️ 다시 할 일로 돌렸어요.\n" + "\n".join(f"☐ {t}" for t in restored)


def _walk(node):
    for c in node["children"]:
        yield c
        yield from _walk(c)


# ---------- 메시지 처리 ----------

HELP = (
    "✅ 안내 완료!\n\n📅 **todo manager 사용법**\n\n"
    "• 매일 아침 8시에 오늘의 할 일을 보내 드려요\n"
    "• \"할일\" → 지금 남은 할 일\n"
    "• \"대장약 먹기 추가해줘\" → 할 일 추가\n"
    "• \"3 완료\" / \"대장약 완료\" → 완료 처리\n"
    "• \"취소\" → 방금 완료한 것 되돌리기\n"
    "• \"완료한 거\" → 완료 목록\n\n"
    "🤖 \"내일 병원 가는 거 넣어둬\", \"보험 건 처리했어\", \"뭐부터 할까?\"처럼 편하게 말해도 "
    "AI가 알아듣고, 노트를 고치기 전에 한 번 확인해요."
)


LIST_Q = re.compile(
    r"^\s*(오늘\s*|지금\s*|남은\s*)?(할\s*일|투\s*두|to\s*-?\s*do|목록|리스트|남은\s*(일|거|것))"
    r"(\s*(뭐|뭐야|뭐\s*있어|뭐\s*남았어|있어|알려\s*줘|보여\s*줘|목록|리스트|좀))*\s*[?!.~]*\s*$",
    re.I,
)


def handle_rules(text):
    """규칙으로 알아들으면 답장, 못 알아들으면 None (→ AI가 해석)."""
    q = text.strip()
    if UNDO_CMD.match(q):
        return undo()
    m = ADD_CMD.search(q)
    if m:
        item = _parse_add(q)
        if not item or len(item) < 2:
            return "✅ 확인 완료!\n\n어떤 할 일을 추가할까요?\n예) \"대장내시경 약 먹기 추가해줘\""
        return add(item)
    m = DONE_CMD.search(q)
    if DONE_LIST_Q.search(q) and not (m and not q.endswith("?")):
        return done_message()
    # "오늘 뭐 했어?"처럼 묻는 말은 완료 명령이 아니다
    if m and q[: m.start()].strip() and not q.endswith("?"):
        r = complete(q[: m.start()].strip())
        if r:
            return r
        return None
    if LIST_Q.match(q):
        return today_message(greeting=False)
    if re.fullmatch(r"\s*(도움말|help|사용법|\?)\s*", q, re.I):
        return HELP
    return None


# ---------- AI 해석 (규칙이 못 알아들은 말만) ----------
# AI는 '무엇을 원하는지'만 고른다. 노트를 고치는 일은 사용자가 확인 버튼을 누른 뒤 규칙 코드가 한다.

AI_PROMPT = """너는 사용자의 할 일 목록(옵시디언 to do list)을 관리하는 비서다. 오늘은 {today}이다.
사용자 메시지가 무엇을 원하는지 분석해 JSON으로만 답하라.

[현재 남은 할 일]
{items}

[메시지]
{message}

[출력 형식]
{{"action": "add, complete, list, advice, unknown 중 하나",
 "item": "action이 add일 때 추가할 할 일. '병원 가기'처럼 짧은 명사형",
 "keyword": "action이 complete일 때, 끝낸 일을 가리키는 핵심 단어 1~2개. 위 목록 항목에 실제로 들어 있는 글자로 (예: 보험, 에어컨, 차 파손)",
 "reply": "action이 advice일 때 사용자에게 줄 답. 존댓말(~요)로, 이유 한 줄 + '▸ 항목 이름' 줄 2~4개. 번호는 쓰지 말고 위 목록의 항목 이름 그대로"}}

[판단 기준]
- add: 새로 할 일을 기억하거나 넣어 달라는 말 (예: "내일 병원 가는 거 잊지 않게 넣어둬")
- complete: 목록에 있는 일을 했거나 끝냈다는 말
- list: 할 일 목록을 보여 달라는 말
- advice: 무엇부터 할지, 추천, 묶어서 정리 등 조언을 묻는 말
- unknown: 할 일과 관계없는 말"""

_pending = {}  # 확인 대기 중인 AI 제안 {"op": "add"|"complete", "item"/"texts": ..., "at": 시각}
PENDING_SECONDS = 600


def handle_ai(text):
    """(답장, 확인 버튼 필요 여부)"""
    import json
    import time

    from services.ollama_client import chat

    lines = _load()
    _, items = open_items(lines)
    numbered = "\n".join(f"{i}. {x['text']}" for i, x in enumerate(items, 1)) or "(없음)"
    d = date.today()
    try:
        raw = chat(
            [{"role": "user", "content": AI_PROMPT.format(
                today=f"{d.year}년 {d.month}월 {d.day}일 {WEEKDAY[d.weekday()]}요일",
                items=numbered, message=text.strip())}],
            json_mode=True,
            temperature=0,
        )
        data = json.loads(raw)
    except Exception:
        return "✅ 확인 완료!\n\nAI가 지금 응답하지 않아요. 아래처럼 말해 주시면 바로 처리해요.\n\n" + HELP.split("\n\n", 1)[1], False

    action = str(data.get("action", "")).strip()
    if action == "add":
        item = str(data.get("item", "")).strip().strip("\"'")
        if len(item) >= 2:
            _pending.clear()
            _pending.update(op="add", item=item, at=time.time())
            return f"✅ 해석 완료!\n\n🤖 할 일 추가로 이해했어요\n☐ {item}\n\n이대로 추가할까요?", True
    elif action == "complete":
        # AI는 번호를 자주 헷갈리므로 핵심 단어만 받고, 항목 찾기는 규칙(find)으로 한다
        kw = str(data.get("keyword", "")).strip()
        found = find(kw, items)[0] if kw else []
        if len(found) > 1:
            cands = "\n".join(f"{items.index(x) + 1}. {x['text']}" for x in found)
            return f"✅ 해석 완료!\n\n비슷한 할 일이 여러 개예요. 번호로 알려 주세요 (예: \"{items.index(found[0]) + 1} 완료\")\n\n{cands}", False
        if found:
            _pending.clear()
            _pending.update(op="complete", texts=[found[0]["text"]], at=time.time())
            return f"✅ 해석 완료!\n\n🤖 이 할 일을 끝내신 걸로 이해했어요\n✔️ {found[0]['text']}\n\n이대로 체크할까요?", True
        return "✅ 해석 완료!\n\n어떤 할 일을 끝내신 건지 모르겠어요. 번호로 알려 주세요 (예: \"3 완료\")\n\n" + today_message(greeting=None), False
    elif action == "list":
        return today_message(greeting=False), False
    elif action == "advice":
        reply = str(data.get("reply", "")).strip()
        if reply:
            reply = re.sub(r"\s*▸\s*", "\n▸ ", reply).strip()
            reply = re.sub(r"\n(▸)", r"\n\n\1", reply, count=1)
            return f"✅ 분석 완료!\n\n🤖 {reply}", False
    return "✅ 확인 완료!\n\n할 일과 관련된 말인지 잘 모르겠어요.\n\n" + HELP.split("\n\n", 1)[1], False


def confirm(yes):
    """확인 버튼(또는 '네/아니요')에 대한 처리. 대기 중인 제안이 없으면 None."""
    import time

    if not _pending:
        return None
    p = dict(_pending)
    _pending.clear()
    if time.time() - p["at"] > PENDING_SECONDS:
        return "✅ 취소 완료!\n\n⌛ 확인 시간(10분)이 지나서 취소했어요. 다시 말씀해 주세요."
    if not yes:
        return "✅ 취소 완료!\n\n노트는 바꾸지 않았어요."
    if p["op"] == "add":
        return add(p["item"])
    return complete_texts(p["texts"])


YES = re.compile(r"^\s*(네|넹|넵|예|응|ㅇㅇ|ㅇ|그래|좋아|맞아|오케이|ok|okay|yes|y)\s*[.!~]*\s*$", re.I)
NO = re.compile(r"^\s*(아니|아니요|아뇨|ㄴㄴ|ㄴ|싫어|됐어|no|n)\s*[.!~]*\s*$", re.I)


def handle_quick(text):
    """확인 답('네/아니요')과 규칙으로 바로 처리. 못 알아들으면 None (→ handle_ai)."""
    if _pending and (YES.match(text) or NO.match(text)):
        r = confirm(bool(YES.match(text)))
        if r:
            return r
    return handle_rules(text)


def handle(text):
    """규칙 → AI 순서로 처리. (답장, 확인 버튼 필요 여부)"""
    r = handle_quick(text)
    if r is not None:
        return r, False
    return handle_ai(text)
