"""
명함 스캔 챗봇 - 텔레그램 봇 메인
"""
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from dotenv import load_dotenv

from ocr import extract_card_info
from email_sender import send_my_card

load_dotenv()
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])

# 사용자별 임시 명함 데이터 저장 (메모리)
pending_cards: dict[int, dict] = {}


def is_allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "안녕하세요! 명함 스캔 봇입니다.\n\n"
        "명함 사진을 전송해 주시면:\n"
        "1️⃣ 명함 정보를 자동으로 인식합니다\n"
        "2️⃣ 명함에 적힌 이메일로 제 명함을 발송합니다\n\n"
        "📷 명함 사진을 보내주세요!"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    user_id = update.effective_user.id
    await update.message.reply_text("📷 명함을 분석 중입니다... 잠시만 기다려주세요.")

    # 텔레그램에서 이미지 다운로드
    photo = update.message.photo[-1]  # 가장 고해상도
    file = await context.bot.get_file(photo.file_id)
    image_path = f"/tmp/card_{user_id}.jpg"
    await file.download_to_drive(image_path)

    # OCR로 명함 정보 추출
    try:
        card_info = extract_card_info(image_path)
    except Exception as e:
        logger.error(f"OCR 오류: {e}")
        await update.message.reply_text("❌ 명함 인식에 실패했습니다. 다시 시도해 주세요.")
        return

    if not card_info.get("email"):
        await update.message.reply_text(
            "⚠️ 이메일 주소를 인식하지 못했습니다.\n"
            "선명한 사진으로 다시 시도해 주세요."
        )
        return

    # 임시 저장
    pending_cards[user_id] = card_info

    # 사용자에게 확인 요청
    text = (
        "📋 인식된 명함 정보:\n\n"
        f"👤 이름: {card_info.get('name', '-')}\n"
        f"🏢 회사: {card_info.get('company', '-')}\n"
        f"💼 직책: {card_info.get('title', '-')}\n"
        f"📧 이메일: {card_info.get('email', '-')}\n"
        f"📞 전화번호: {card_info.get('phone', '-')}\n"
        f"📍 주소: {card_info.get('address', '-')}\n\n"
        "위 정보로 이메일을 발송할까요?"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ 확인 후 발송", callback_data="confirm"),
            InlineKeyboardButton("❌ 취소", callback_data="cancel"),
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_allowed(update):
        await query.answer()
        return
    await query.answer()
    user_id = query.from_user.id

    if query.data == "cancel":
        pending_cards.pop(user_id, None)
        await query.edit_message_text("❌ 취소되었습니다.")
        return

    if query.data != "confirm":
        return

    card_info = pending_cards.pop(user_id, None)
    if not card_info:
        await query.edit_message_text("⚠️ 세션이 만료되었습니다. 다시 사진을 보내주세요.")
        return

    await query.edit_message_text("⏳ 이메일 발송 및 저장 처리 중...")

    # 이메일 발송
    email_sent = False
    try:
        send_my_card(card_info["email"], card_info.get("name", ""))
        email_sent = True
        msg_text = "✅ 처리 완료!\n📧 이메일 발송: 성공"
    except Exception as e:
        logger.error(f"이메일 발송 오류: {e}")
        msg_text = "❌ 이메일 발송에 실패했습니다. Gmail 설정을 확인해 주세요."

    await context.bot.send_message(user_id, msg_text)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인해 주세요.")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("봇이 시작되었습니다.")
    app.run_polling()


if __name__ == "__main__":
    main()
