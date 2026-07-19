import logging
from functools import wraps
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

from config import TELEGRAM_BOT_TOKEN, ALLOWED_CHAT_ID, FILES
import parser as md_parser
import gemini

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Per-user session: stores last queried items for number input
user_sessions: dict[int, list[dict]] = {}


def restricted(func):
    @wraps(func)
    async def wrapper(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ALLOWED_CHAT_ID:
            await update.message.reply_text("접근 권한이 없습니다.")
            return
        return await func(update, ctx)
    return wrapper


async def _send_items(update: Update, key: str):
    filepath, label = FILES[key]
    try:
        items = md_parser.parse_incomplete(filepath)
    except FileNotFoundError:
        await update.message.reply_text(f"파일을 찾을 수 없습니다: {filepath}")
        return

    chat_id = update.effective_user.id
    user_sessions[chat_id] = {"key": key, "items": items}

    if not items:
        await update.message.reply_text(f"{label} — 미완료 항목이 없습니다 🎉")
        return

    text = f"{label} — 미완료 {len(items)}건\n\n"
    text += md_parser.format_items(items)
    text += "\n\n번호를 입력하면 완료 처리할게요."
    await update.message.reply_text(text)


@restricted
async def cmd_todo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_items(update, "todo")


@restricted
async def cmd_health(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_items(update, "health")


@restricted
async def cmd_clean(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await _send_items(update, "clean")


@restricted
async def cmd_all(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    parts = []
    all_items: list[dict] = []
    for key, (filepath, label) in FILES.items():
        try:
            items = md_parser.parse_incomplete(filepath)
        except FileNotFoundError:
            parts.append(f"{label} — 파일 없음")
            continue
        if items:
            parts.append(f"{label} — {len(items)}건\n" + md_parser.format_items(items))
            all_items.extend(items)

    chat_id = update.effective_user.id
    user_sessions[chat_id] = {"key": "all", "items": all_items}

    if not parts:
        await update.message.reply_text("모든 항목이 완료됐어요! 🎉")
        return

    text = "\n\n".join(parts)
    text += "\n\n번호를 입력하면 완료 처리할게요."
    await update.message.reply_text(text)


@restricted
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lines = []
    for key, (filepath, label) in FILES.items():
        try:
            done, total = md_parser.get_stats(filepath)
        except FileNotFoundError:
            lines.append(f"{label}: 파일 없음")
            continue
        pct = int(done / total * 100) if total else 0
        lines.append(f"{label}: {done}/{total} ({pct}%)")
    await update.message.reply_text("\n".join(lines))


@restricted
async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Gemini가 분석 중입니다...")
    items_by_file = {}
    for key, (filepath, label) in FILES.items():
        try:
            items_by_file[label] = md_parser.parse_incomplete(filepath)
        except FileNotFoundError:
            items_by_file[label] = []

    result = gemini.summarize_todos(items_by_file)
    await update.message.reply_text(result)


@restricted
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "사용 가능한 명령어:\n"
        "/todo — 할 일 목록 조회\n"
        "/health — 건강 체크리스트 조회\n"
        "/clean — 대청소 체크리스트 조회\n"
        "/all — 전체 미완료 항목 조회\n"
        "/status — 파일별 진행률 요약\n"
        "/summary — AI 우선순위 추천\n"
        "/help — 도움말\n\n"
        "조회 후 번호를 입력하면 완료 처리됩니다. (예: 1 3 5)"
    )
    await update.message.reply_text(text)


@restricted
async def handle_number(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_user.id
    session = user_sessions.get(chat_id)
    if not session:
        await update.message.reply_text("먼저 /todo, /health, /clean, /all 명령어로 목록을 조회해주세요.")
        return

    items = session["items"]
    text = update.message.text.strip()
    try:
        numbers = [int(n) for n in text.split()]
    except ValueError:
        await update.message.reply_text("숫자를 입력해주세요. (예: 1 3 5)")
        return

    invalid = [n for n in numbers if n < 1 or n > len(items)]
    if invalid:
        await update.message.reply_text(f"잘못된 번호입니다: {', '.join(map(str, invalid))} (1~{len(items)} 범위)")
        return

    done_texts = []
    for n in numbers:
        item = items[n - 1]
        completed_text = md_parser.mark_complete(item["filepath"], item["line_no"])
        done_texts.append(completed_text)

    # Refresh session items
    key = session["key"]
    if key == "all":
        all_items = []
        for _, (filepath, _) in FILES.items():
            try:
                all_items.extend(md_parser.parse_incomplete(filepath))
            except FileNotFoundError:
                pass
        user_sessions[chat_id]["items"] = all_items
    else:
        filepath, _ = FILES[key]
        user_sessions[chat_id]["items"] = md_parser.parse_incomplete(filepath)

    if len(done_texts) == 1:
        await update.message.reply_text(f"✅ 완료 처리됐어요: {done_texts[0]}")
    else:
        lines = "\n".join(f"✅ {t}" for t in done_texts)
        await update.message.reply_text(f"{lines}\n{len(done_texts)}건 완료 처리됐어요.")


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("todo", cmd_todo))
    app.add_handler(CommandHandler("health", cmd_health))
    app.add_handler(CommandHandler("clean", cmd_clean))
    app.add_handler(CommandHandler("all", cmd_all))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    logging.info("Bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
