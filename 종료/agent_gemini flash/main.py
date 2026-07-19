import os
import logging
from dotenv import load_dotenv
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ["BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

genai.configure(api_key=GEMINI_API_KEY)

# 대화 히스토리 (인메모리)
chat_session: "genai.ChatSession | None" = None


def new_chat() -> genai.ChatSession:
    model = genai.GenerativeModel(GEMINI_MODEL)
    return model.start_chat(history=[])


def is_allowed(update: Update) -> bool:
    return update.effective_user.id == ALLOWED_USER_ID


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_session
    if not is_allowed(update):
        return
    chat_session = new_chat()
    await update.message.reply_text(
        f"안녕하세요! Gemini({GEMINI_MODEL})와 대화를 시작합니다.\n"
        "/new — 대화 초기화\n"
        "/model — 모델 전환"
    )


async def cmd_new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_session
    if not is_allowed(update):
        return
    chat_session = new_chat()
    await update.message.reply_text("대화를 초기화했습니다. 새로운 주제로 시작하세요!")


async def cmd_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_session, GEMINI_MODEL
    if not is_allowed(update):
        return

    args = context.args
    if not args:
        await update.message.reply_text(
            f"현재 모델: `{GEMINI_MODEL}`\n\n"
            "사용법: `/model gemini-2.0-flash` 또는 `/model gemini-2.5-pro`",
            parse_mode="Markdown",
        )
        return

    GEMINI_MODEL = args[0]
    chat_session = new_chat()
    await update.message.reply_text(f"모델을 `{GEMINI_MODEL}`로 변경했습니다. 대화도 초기화됐어요.", parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global chat_session
    if not is_allowed(update):
        return

    if chat_session is None:
        chat_session = new_chat()

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response = await chat_session.send_message_async(update.message.text)
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error("Gemini error: %s", e)
        await update.message.reply_text(f"오류가 발생했습니다: {e}")


async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    photo = update.message.photo[-1]  # 가장 큰 해상도
    file = await photo.get_file()
    file_bytes = await file.download_as_bytearray()

    caption = update.message.caption or "이 이미지를 설명해줘"

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        image_part = {"mime_type": "image/jpeg", "data": bytes(file_bytes)}
        response = await model.generate_content_async([caption, image_part])
        await update.message.reply_text(response.text)
    except Exception as e:
        logger.error("Gemini image error: %s", e)
        await update.message.reply_text(f"이미지 처리 중 오류가 발생했습니다: {e}")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("new", cmd_new))
    app.add_handler(CommandHandler("model", cmd_model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))

    logger.info("봇 시작 (모델: %s)", GEMINI_MODEL)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
