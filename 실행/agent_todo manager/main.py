"""todo manager: 옵시디언 1.1_tasks/1_to do list.md 하나만 다룬다.

- 매일 아침 8시(DAILY_TIME)에 오늘의 할 일을 보낸다
- 할 일 추가, 완료 처리, 되돌리기 (services/tasks.py)
- 규칙이 못 알아들은 말만 로컬 AI(Ollama qwen3)가 해석하고, 노트를 고치기 전에 확인 버튼을 띄운다

예전 옵시디언 전체 검색(services/search.py, indexer.py)은 더 이상 쓰지 않는다.
"""
import asyncio
import html
import logging
import os
import re
import time
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import config
from services import tasks

DAILY_TIME = os.environ.get("DAILY_TIME", "08:00")  # 매일 할 일을 보내는 시각 (HH:MM)

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

# 노트 파일을 동시에 고치지 않도록 한 번에 하나씩
note_lock = asyncio.Lock()


def allowed(update: Update) -> bool:
    if update.effective_chat.id != config.ALLOWED_CHAT_ID:
        logger.warning(f"허용되지 않은 chat_id 접근: {update.effective_chat.id}")
        return False
    return True


def render(text):
    """**굵게** → <b>, ~~취소선~~ → <s> (나머지는 HTML 이스케이프)"""
    body = html.escape(text)
    body = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", body)
    body = re.sub(r"~~(.+?)~~", r"<s>\1</s>", body)
    if len(body) > 3900:
        body = body[:3900].rsplit("\n", 1)[0] + "\n…"
    return body


CONFIRM_BUTTONS = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✅ 네", callback_data="yes"), InlineKeyboardButton("❌ 아니요", callback_data="no")]]
)


async def send(target, text, **kw):
    """HTML로 보내고, 해석이 실패하면 장식 없이 보낸다."""
    try:
        return await target(render(text), parse_mode=ParseMode.HTML, **kw)
    except BadRequest:
        return await target(text[:4000], **kw)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed(update):
        await send(update.message.reply_text, tasks.HELP)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if allowed(update):
        async with note_lock:
            msg = await asyncio.to_thread(tasks.today_message)
        await send(update.message.reply_text, msg)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    q = (update.message.text or "").strip()
    if not q:
        return
    try:
        # 1) 규칙으로 바로 알아들으면 즉시 처리
        async with note_lock:
            reply = await asyncio.to_thread(tasks.handle_quick, q)
        if reply is not None:
            logger.info(f"규칙 처리 | {q}")
            await send(update.message.reply_text, reply)
            return
        # 2) 못 알아들으면 AI가 해석 (노트를 고칠 땐 확인 버튼)
        msg = await update.message.reply_text("🤖 무슨 뜻인지 생각해 볼게요…")
        t0 = time.time()
        async with note_lock:
            reply, ask = await asyncio.to_thread(tasks.handle_ai, q)
        logger.info(f"AI 처리 {time.time() - t0:.0f}초 | {q} → {'확인 요청' if ask else '답변'}")
        await send(msg.edit_text, reply, reply_markup=CONFIRM_BUTTONS if ask else None)
    except Exception as e:
        logger.exception("처리 실패")
        await update.message.reply_text(f"❌ 오류가 났어요: {e}")


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI 제안 확인 버튼 (✅ 네 / ❌ 아니요)"""
    query = update.callback_query
    if query.message.chat.id != config.ALLOWED_CHAT_ID:
        return
    await query.answer()
    async with note_lock:
        reply = await asyncio.to_thread(tasks.confirm, query.data == "yes")
    await send(query.edit_message_text, reply or "⌛ 이미 처리했거나 지난 요청이에요.")
    logger.info(f"확인 버튼 | {query.data}")


def _next_run(now):
    h, m = map(int, DAILY_TIME.split(":"))
    run = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return run if run > now else run + timedelta(days=1)


async def daily_todo(app):
    """매일 DAILY_TIME에 오늘의 할 일을 보낸다."""
    while True:
        run = _next_run(datetime.now())
        logger.info(f"다음 할 일 알림: {run:%Y-%m-%d %H:%M}")
        await asyncio.sleep((run - datetime.now()).total_seconds())
        try:
            async with note_lock:
                msg = await asyncio.to_thread(tasks.today_message)
            await send(lambda t, **kw: app.bot.send_message(config.ALLOWED_CHAT_ID, t, **kw), msg)
            logger.info("오늘의 할 일 알림 보냄")
        except Exception:
            logger.exception("할 일 알림 실패")
        await asyncio.sleep(60)  # 같은 분에 두 번 보내지 않도록


async def post_init(app):
    app.create_task(daily_todo(app))


def main():
    if not config.TELEGRAM_TOKEN or not config.ALLOWED_CHAT_ID:
        raise SystemExit(".env에 TELEGRAM_TOKEN과 ALLOWED_CHAT_ID를 넣어 주세요.")
    app = ApplicationBuilder().token(config.TELEGRAM_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler(["today", "todo"], cmd_today))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))
    logger.info("todo manager 시작")
    app.run_polling()


if __name__ == "__main__":
    main()
