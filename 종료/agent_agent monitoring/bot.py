import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from dotenv import load_dotenv
from agent_manager import get_all_status, get_status, start_agent, stop_agent, get_recent_logs, AGENTS

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ.get("ALLOWED_CHAT_ID", "0"))


def _check_auth(update: Update) -> bool:
    if ALLOWED_CHAT_ID == 0:
        return True
    return update.effective_chat.id == ALLOWED_CHAT_ID


def _status_text(s: dict) -> str:
    icon = "🟢" if s["running"] else "🔴"
    pid_info = f" `(PID: {s['pid']})`" if s["running"] else ""
    return f"{icon} {s['emoji']} {s['name']}{pid_info}"


def _build_status_keyboard(statuses: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for s in statuses:
        if s.get("self"):
            buttons.append([InlineKeyboardButton(f"📡 {s['name']} (이 봇)", callback_data="noop")])
        else:
            action = "stop" if s["running"] else "start"
            label = f"⏹ {s['name']} 중지" if s["running"] else f"▶️ {s['name']} 시작"
            buttons.append([InlineKeyboardButton(label, callback_data=f"{action}:{s['id']}")])
        buttons.append([InlineKeyboardButton(f"📋 {s['name']} 로그", callback_data=f"log:{s['id']}")])
    buttons.append([InlineKeyboardButton("🔄 새로고침", callback_data="refresh")])
    return InlineKeyboardMarkup(buttons)


def _build_status_message(statuses: list[dict]) -> str:
    lines = ["*🤖 에이전트 모니터링*\n"]
    for s in statuses:
        lines.append(_status_text(s))
    return "\n".join(lines)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return
    statuses = get_all_status()
    text = _build_status_message(statuses)
    keyboard = _build_status_keyboard(statuses)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _check_auth(update):
        return
    statuses = get_all_status()
    text = _build_status_message(statuses)
    keyboard = _build_status_keyboard(statuses)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not _check_auth(update):
        return

    data = query.data

    if data == "noop":
        await query.answer("이 봇은 직접 제어할 수 없어요", show_alert=False)
        return

    if data == "refresh":
        statuses = get_all_status()
        text = _build_status_message(statuses)
        keyboard = _build_status_keyboard(statuses)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
        return

    action, agent_id = data.split(":", 1)

    if action == "start":
        ok, msg = start_agent(agent_id)
        await query.answer(msg, show_alert=True)
    elif action == "stop":
        ok, msg = stop_agent(agent_id)
        await query.answer(msg, show_alert=True)
    elif action == "log":
        logs = get_recent_logs(agent_id)
        agent_name = AGENTS[agent_id]["name"]
        log_text = f"*📋 {agent_name} 최근 로그*\n\n```\n{logs[-3000:]}\n```"
        await query.message.reply_text(log_text, parse_mode="Markdown")
        return

    statuses = get_all_status()
    text = _build_status_message(statuses)
    keyboard = _build_status_keyboard(statuses)
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CallbackQueryHandler(handle_callback))
    logger.info("모니터링 봇 시작")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
