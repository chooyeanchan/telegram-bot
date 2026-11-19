"""'어떤 기록이 있어?' 같은 목록 질문은 LLM 없이 기록 폴더의 노트 목록으로 바로 답한다.

검색은 질문과 내용이 비슷한 노트 몇 개만 가져오므로 "일기 뭐 있어?"에 전체 목록을 줄 수 없고,
LLM은 노트 제목을 지어내거나 빠뜨린다. 목록은 폴더를 직접 읽는 편이 정확하다.
"""
import os
import re

import config

RECORD_DIR = "1.2_record"
# 폴더 → (이모지, 카테고리 이름, 질문에서 이 카테고리를 가리키는 말)
CATEGORIES = [
    ("1_journal", "📔", "일기", re.compile(r"(일기|저널|journal|회고|다이어리)", re.I)),
    ("2_sora letter", "💌", "소라에게 쓴 편지", re.compile(r"(편지|소라\s*레터|레터|letter)", re.I)),
    ("3_book review", "📖", "책 감상평", re.compile(r"(책|독서|감상|서평|독후감|book)", re.I)),
    ("4_posting", "✍️", "블로그 포스팅", re.compile(r"(포스팅|블로그|게시글|posting|sns)", re.I)),
]
RECORD_Q = re.compile(r"(기록|일기|저널|회고|편지|레터|감상|서평|독후감|독서|포스팅|블로그|게시글)")
# 내용이 아니라 목록을 묻는 말
LIST_Q = re.compile(
    r"(어떤\s*(기록|일기|편지|글|포스팅|게시글|감상|책|것|거)|무슨\s*(기록|일기|편지|글|포스팅|게시글|책)|"
    r"뭐\s*(있|썼|적었|남겼)|목록|리스트|몇\s*(개|편|건|번|통)|있는지|얼마나|전부|전체|모든|현황)"
)
SHOW = 25  # 카테고리 하나를 물었을 때 보여줄 최대 제목 수
PREVIEW = 3  # 전체 현황에서 카테고리마다 보여줄 최근 제목 수


def _eun(word):
    """받침에 따라 은/는"""
    ch = word[-1]
    return "은" if "가" <= ch <= "힣" and (ord(ch) - 0xAC00) % 28 else "는"


def _notes(folder):
    base = os.path.join(config.VAULT_PATH, RECORD_DIR, folder)
    out = []
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".md") and not f.startswith("."):
                rel = os.path.relpath(os.path.join(root, f), config.VAULT_PATH)
                out.append(rel)
    return out


def try_answer(query):
    if not (RECORD_Q.search(query) and LIST_Q.search(query)):
        return None
    from services.search import _sort_date, date_match, parse_date_query  # 순환 import 방지

    cond = parse_date_query(query)
    picked = [c for c in CATEGORIES if c[3].search(query)]
    cats = picked or CATEGORIES

    when = ""
    if cond:
        y = ", ".join(f"{v}년" for v in sorted(cond[0]))
        m = ", ".join(f"{v}월" for v in sorted(cond[1]))
        when = f"{y} {m}".strip() + " "

    def listed(folder):
        notes = _notes(folder)
        if cond:
            notes = [n for n in notes if date_match(n, cond)]
        return sorted(notes, key=lambda n: (_sort_date(n), n), reverse=True)

    if len(cats) == 1:
        folder, emoji, label, _ = cats[0]
        notes = listed(folder)
        if not notes:
            return f"{emoji} {when}**{label}** 기록은 아직 없어요.", []
        lines = [f"{emoji} {when}**{label}**{_eun(label)} {len(notes)}개 있어요", ""]
        year = None
        for n in notes[:SHOW]:
            y, title = _split(n)
            if y != year:  # 연도가 바뀔 때마다 연도 제목
                lines += ([""] if year is not None else []) + [f"🗂 **{y or '날짜 없음'}**"]
                year = y
            lines.append(f"  • {title}")
        if len(notes) > SHOW:
            lines += ["", f"… 외 {len(notes) - SHOW}개 · 💬 \"작년 3월 일기\"처럼 기간을 붙이면 좁혀 드려요"]
        return "\n".join(lines), []

    lines, total = [f"🗃 {when}**기록 현황**", ""], 0
    for folder, emoji, label, _ in cats:
        notes = listed(folder)
        total += len(notes)
        lines.append(f"{emoji} **{label}**  {len(notes)}개")
        for n in notes[:PREVIEW]:
            y, title = _split(n)
            lines.append(f"      ▸ {title}" + (f"  ({y})" if y else ""))
        lines.append("")
    if not total:
        return f"🗃 {when}기록이 없어요.", []
    lines.append("💬 \"소라 편지 뭐 있어?\"처럼 물으면 그 기록만 자세히 보여드려요.")
    return "\n".join(lines).strip(), []


def _split(rel):
    """'261031 우리에게' → ('2026', '10.31 우리에게')"""
    t = os.path.splitext(os.path.basename(rel))[0]
    m = re.match(r"(\d{2})(\d{2})(\d{2})\s*(.*)", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"20{m.group(1)}", f"{int(m.group(2))}.{int(m.group(3))}  {m.group(4) or t}"
    return "", t
