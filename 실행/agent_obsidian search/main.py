import asyncio
import html
import logging
import os
import re
import time
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from services.indexer import update_index
from services.search import answer

log_dir = os.path.join(config.BASE_DIR, "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(log_dir, datetime.now().strftime("%Y-%m-%d") + ".log"),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)  # 로그에 토큰 URL이 찍히지 않도록
logger = logging.getLogger(__name__)

# LLM 작업은 한 번에 하나씩만 (메모리 보호)
llm_lock = asyncio.Lock()


def allowed(update: Update) -> bool:
    if update.effective_chat.id != config.ALLOWED_CHAT_ID:
        logger.warning(f"허용되지 않은 chat_id 접근: {update.effective_chat.id}")
        return False
    return True


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text(
        "옵시디언 검색봇이에요 🔎\n"
        "질문을 보내면 노트에서 찾아 답해 드려요.\n\n"
        "/reindex  노트 다시 인덱싱"
    )


async def cmd_reindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    await update.message.reply_text("인덱싱 중... ⏳")
    async with llm_lock:
        new, upd, rem = await asyncio.to_thread(update_index)
    await update.message.reply_text(f"✅ 완료: 추가 {new}, 갱신 {upd}, 삭제 {rem}")


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    q = (update.message.text or "").strip()
    if not q:
        return
    msg = await update.message.reply_text("🔎 노트 찾는 중...")
    t0 = time.time()
    try:
        async with llm_lock:
            reply, hits = await asyncio.to_thread(answer, q)
        logger.info(
            f"질문 처리 {time.time() - t0:.0f}초 | {q} → "
            + ", ".join(os.path.basename(h["path"]) for h in hits)
        )
        try:
            await msg.edit_text(render(reply, hits), parse_mode=ParseMode.HTML)
        except BadRequest:  # HTML 해석이 실패하면 장식 없이라도 보낸다
            await msg.edit_text(reply[:4000])
    except Exception as e:
        logger.exception("답변 실패")
        await msg.edit_text(f"❌ 오류가 났어요: {e}")


def _folder_name(path):
    """'1.2_record/2_sora letter/정리/2025/x.md' → 'sora letter' 처럼 사람이 읽는 폴더 이름."""
    parts = [p for p in os.path.dirname(path).split("/") if p]
    parts = [p for p in parts if p != "정리" and not re.fullmatch(r"\d{4}", p)]
    return re.sub(r"^[\d.]+_", "", parts[-1]) if parts else ""


# 폴더별 이모지: 노트가 어떤 종류(일기·편지·리서치…)인지 한눈에 보이게
FOLDER_EMOJI = [
    ("1.0_llm wiki", "📚"),
    ("1.1_tasks", "✅"),
    ("1.2_record/1_journal", "📔"),
    ("1.2_record/2_sora letter", "💌"),
    ("1.2_record/3_book review", "📖"),
    ("1.2_record/4_posting", "✍️"),
    ("1.3_writing", "🖋"),
    ("1.4_habit tracker", "📈"),
    ("1.5_yearly goals", "🎯"),
    ("1.9_storage/letter by sora", "💝"),
    ("1.9_storage/log", "🛠"),
    ("1.9_storage/materials/memo", "📝"),
    ("1.9_storage/materials/whisky note", "🥃"),
    ("1.9_storage/materials/에이전트 지식", "🤖"),
    ("1.9_storage/materials/커리어", "💼"),
]


def _emoji(path):
    best = ("", "📄")
    for key, e in FOLDER_EMOJI:
        if path.startswith(key + "/") and len(key) > len(best[0]):
            best = (key, e)
    return best[1]


def _title_of(path):
    return os.path.splitext(os.path.basename(path))[0]


def render(reply, hits):
    """답변을 텔레그램 HTML로: **굵게**·노트 제목은 굵게, 근거 노트는 폴더 이모지로, 끝에 참고 노트."""
    body = "\n".join(line.rstrip() for line in reply.splitlines())
    body = re.sub(r"^[ \t]*[-*•][ \t]+(?!\*)", "• ", body, flags=re.M)
    if hits:  # LLM 답변: 첫 문단과 목록 사이 한 줄 띄우기 (규칙 답변은 이미 모양을 갖춰 옴)
        body = re.sub(r"([^\n])\n(• )", r"\1\n\n\2", body, count=1)
    body = re.sub(r"\n{3,}", "\n\n", body)
    listed = set(re.findall(r"^• \[\[(.+?)\]\]", body, flags=re.M))
    by_title = {_title_of(h["path"]): h["path"] for h in hits}
    body = html.escape(body)
    body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
    # 근거 노트 목록은 • 대신 그 노트 폴더의 이모지로 (💌 편지, 📔 일기 …)
    body = re.sub(
        r"^• \[\[(.+?)\]\]",
        lambda m: f"{_emoji(by_title.get(html.unescape(m.group(1)), ''))} [[{m.group(1)}]]",
        body,
        flags=re.M,
    )
    body = re.sub(r"\[\[(.+?)\]\]", r"<b>\1</b>", body)
    if len(body) > 3300:
        body = body[:3300].rsplit("\n", 1)[0] + "\n…"
    if not hits:
        return body
    # 본문 목록에 이미 나온 노트는 다시 쓰지 않고, 노트가 있는 폴더만 한 줄로 보여준다
    extra = []
    for h in hits[:5]:
        title = _title_of(h["path"])
        if title not in listed:
            folder = _folder_name(h["path"])
            extra.append(f"{_emoji(h['path'])} {html.escape(title)}" + (f"  <i>{html.escape(folder)}</i>" if folder else ""))
    folders = list(dict.fromkeys(
        f"{_emoji(h['path'])} {_folder_name(h['path'])}" for h in hits[:5] if _folder_name(h["path"])
    ))
    if extra:
        return f"{body}\n\n📎 <b>참고한 노트</b>\n" + "\n".join(extra)
    return f"{body}\n\n📂 <i>{html.escape(' · '.join(folders))}</i>" if folders else body


async def periodic_reindex(app):
    while True:
        await asyncio.sleep(config.REINDEX_MINUTES * 60)
        try:
            async with llm_lock:
                new, upd, rem = await asyncio.to_thread(update_index)
            if new or upd or rem:
                logger.info(f"자동 인덱싱: 추가 {new}, 갱신 {upd}, 삭제 {rem}")
        except Exception:
            logger.exception("자동 인덱싱 실패")


async def post_init(app):
    try:
        new, upd, rem = await asyncio.to_thread(update_index)
        logger.info(f"시작 인덱싱: 추가 {new}, 갱신 {upd}, 삭제 {rem}")
    except Exception:
        logger.exception("시작 인덱싱 실패")
    app.create_task(periodic_reindex(app))


def main():
    if not config.TELEGRAM_TOKEN or not config.ALLOWED_CHAT_ID:
        raise SystemExit(".env에 TELEGRAM_TOKEN과 ALLOWED_CHAT_ID를 넣어 주세요.")
    app = (
        ApplicationBuilder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("reindex", cmd_reindex))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))
    logger.info("옵시디언 검색봇 시작")
    app.run_polling()


if __name__ == "__main__":
    main()
