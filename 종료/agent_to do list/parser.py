import os
import re
import tempfile
from typing import Optional


def _get_indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def parse_incomplete(filepath: str) -> list[dict]:
    """Return list of incomplete items with index, text, parent, and line_no."""
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    items = []
    # Track the most recent non-empty non-checkbox line at each indent level as potential parent
    parent_stack: list[tuple[int, str]] = []  # (indent, text)

    for line_no, line in enumerate(lines):
        stripped = line.rstrip("\n")
        indent = _get_indent(stripped)
        content = stripped.lstrip()

        # Update parent stack
        while parent_stack and parent_stack[-1][0] >= indent:
            parent_stack.pop()

        if re.match(r"- \[ \] ", content):
            text = content[6:]
            parent = parent_stack[-1][1] if parent_stack else None
            items.append({
                "text": text,
                "parent": parent,
                "line_no": line_no,
                "filepath": filepath,
            })
        elif re.match(r"- \[x\] ", content, re.IGNORECASE):
            pass  # completed, skip
        elif content and not content.startswith("- "):
            # heading or plain text — use as potential parent label
            label = content.lstrip("#").strip()
            parent_stack.append((indent, label))
        elif re.match(r"- ", content):
            label = content[2:]
            parent_stack.append((indent, label))

    return items


def format_items(items: list[dict]) -> str:
    lines = []
    for i, item in enumerate(items, 1):
        if item["parent"]:
            lines.append(f"{i}. {item['parent']} > {item['text']}")
        else:
            lines.append(f"{i}. {item['text']}")
    return "\n".join(lines)


def mark_complete(filepath: str, line_no: int) -> str:
    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    line = lines[line_no]
    new_line = re.sub(r"- \[ \] ", "- [x] ", line, count=1)
    lines[line_no] = new_line

    # Atomic write
    dir_ = os.path.dirname(filepath)
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, encoding="utf-8", suffix=".tmp") as tmp:
        tmp.writelines(lines)
        tmp_path = tmp.name
    os.replace(tmp_path, filepath)

    # Return the item text
    return re.sub(r"- \[x\] ", "", new_line.strip(), count=1)


def get_stats(filepath: str) -> tuple[int, int]:
    """Return (completed, total) checkbox counts."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    total = len(re.findall(r"- \[[ x]\] ", content, re.IGNORECASE))
    completed = len(re.findall(r"- \[x\] ", content, re.IGNORECASE))
    return completed, total
