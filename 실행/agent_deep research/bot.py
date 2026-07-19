import os
import asyncio
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from researcher import run_research, SAVE_PATH

load_dotenv()

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])

# 대화 상태
WAITING_TOPIC, WAITING_DEPTH, WAITING_FOCUS, RESEARCHING = range(4)

DEPTH_OPTIONS = [["심층 분석", "간략 개요"]]


def is_allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID


# ── 명령어 핸들러 ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    context.user_data.clear()
    await update.message.reply_text(
        "안녕하세요! 딥리서치 봇입니다 🔍\n\n"
        "조사하고 싶은 주제를 입력하거나 /research 를 사용하세요.\n"
        "결과는 Obsidian inbox에 md 파일로 저장됩니다.\n\n"
        "명령어:\n"
        "/research - 리서치 시작\n"
        "/list - 최근 저장 파일 목록\n"
        "/cancel - 현재 조사 취소\n"
        "/help - 도움말",
        reply_markup=ReplyKeyboardRemove(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "📖 사용 방법\n\n"
        "1. 주제를 자유롭게 입력하거나 /research 입력\n"
        "2. 조사 깊이 선택 (심층 / 간략)\n"
        "3. 집중할 세부 분야 입력 (없으면 '없음' 입력)\n"
        "4. 조사 완료 후 Obsidian inbox에 파일 저장\n\n"
        "바로 조사: 주제 입력 후 '바로 조사' 선택\n"
        "저장 경로: " + SAVE_PATH
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        files = sorted(
            [f for f in os.listdir(SAVE_PATH) if f.endswith(".md")],
            reverse=True
        )[:5]
        if not files:
            await update.message.reply_text("저장된 파일이 없습니다.")
        else:
            text = "📂 최근 저장 파일:\n\n" + "\n".join(f"• {f}" for f in files)
            await update.message.reply_text(text)
    except Exception as e:
        await update.message.reply_text(f"파일 목록 조회 실패: {e}")


# ── 대화 흐름 ──────────────────────────────────────────────

async def research_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """리서치 시작 - 주제 입력 요청"""
    if not is_allowed(update):
        return ConversationHandler.END
    await update.message.reply_text(
        "조사할 주제를 입력해주세요.\n예) 양자 컴퓨터 최신 동향",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_TOPIC


async def receive_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """주제 수신 → 조사 깊이 선택"""
    topic = update.message.text.strip()
    context.user_data["topic"] = topic

    keyboard = ReplyKeyboardMarkup(
        [["심층 분석", "간략 개요"], ["바로 조사"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        f"주제: *{topic}*\n\n조사 깊이를 선택해주세요.\n'바로 조사'를 누르면 기본값(심층)으로 즉시 시작합니다.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return WAITING_DEPTH


async def receive_depth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """깊이 수신 → 세부 분야 질문 (또는 바로 조사)"""
    text = update.message.text.strip()

    if text == "바로 조사":
        context.user_data["depth"] = "심층 분석"
        context.user_data["focus"] = ""
        return await start_research(update, context)

    context.user_data["depth"] = text
    await update.message.reply_text(
        "특히 집중할 세부 분야가 있나요?\n예) 하드웨어, 투자 동향, 국내 현황\n없으면 '없음' 입력",
        reply_markup=ReplyKeyboardRemove(),
    )
    return WAITING_FOCUS


async def receive_focus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """세부 분야 수신 → 조사 시작"""
    focus = update.message.text.strip()
    context.user_data["focus"] = "" if focus in ("없음", "없어", "-") else focus
    return await start_research(update, context)


async def start_research(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """실제 리서치 실행"""
    topic = context.user_data["topic"]
    depth = context.user_data["depth"]
    focus = context.user_data.get("focus", "")

    await update.message.reply_text(
        f"🔍 조사를 시작합니다!\n\n"
        f"주제: {topic}\n깊이: {depth}\n집중 분야: {focus or '전반적'}\n\n잠시 기다려주세요...",
        reply_markup=ReplyKeyboardRemove(),
    )

    async def progress(msg: str):
        await update.message.reply_text(msg)

    # 조사하는 동안 "타이핑 중..." 표시를 10초마다 갱신
    async def keep_typing():
        while True:
            try:
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.TYPING,
                )
                await asyncio.sleep(8)
            except asyncio.CancelledError:
                break

    typing_task = asyncio.create_task(keep_typing())
    result = await run_research(topic, depth, focus, progress)
    typing_task.cancel()

    if result["success"]:
        filename = os.path.basename(result["file_path"])
        await update.message.reply_text(
            f"✅ 조사 완료!\n\n"
            f"📄 파일: `{filename}`\n\n"
            f"📝 요약:\n{result['summary']}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"❌ 조사 중 오류가 발생했습니다.\n{result['error']}"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("조사를 취소했습니다.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ── 일반 텍스트 입력 → 주제로 처리 ─────────────────────────

async def text_as_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """대화 흐름 밖에서 텍스트 입력 시 주제로 자동 인식"""
    if not is_allowed(update):
        return ConversationHandler.END
    context.user_data["topic"] = update.message.text.strip()
    keyboard = ReplyKeyboardMarkup(
        [["심층 분석", "간략 개요"], ["바로 조사"]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )
    await update.message.reply_text(
        f"주제: *{context.user_data['topic']}*\n\n조사 깊이를 선택해주세요.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )
    return WAITING_DEPTH


# ── 앱 설정 및 실행 ────────────────────────────────────────

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(".env 파일에 TELEGRAM_BOT_TOKEN이 없습니다.")

    app = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("research", research_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, text_as_topic),
        ],
        states={
            WAITING_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_topic)],
            WAITING_DEPTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_depth)],
            WAITING_FOCUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_focus)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("start", start),
        ],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(conv_handler)

    print("봇 시작... (종료: Ctrl+C)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
