import asyncio
import logging
import os
from datetime import datetime

from telegram import Update
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
    msg = await update.message.reply_text("노트 찾는 중... 🔎")
    try:
        async with llm_lock:
            reply, hits = await asyncio.to_thread(answer, q)
        sources = "\n".join(
            f"• {os.path.splitext(p)[0]}" for p in dict.fromkeys(h["path"] for h in hits)
        )
        text = f"✅ {reply}\n\n📎 출처\n{sources}" if sources else f"✅ {reply}"
        await msg.edit_text(text[:4000])
    except Exception as e:
        logger.exception("답변 실패")
        await msg.edit_text(f"❌ 오류가 났어요: {e}")


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
    new, upd, rem = await asyncio.to_thread(update_index)
    logger.info(f"시작 인덱싱: 추가 {new}, 갱신 {upd}, 삭제 {rem}")
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
