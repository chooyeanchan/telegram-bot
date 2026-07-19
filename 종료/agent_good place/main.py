import os
from dotenv import load_dotenv

load_dotenv()

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.handlers import (
    handle_start,
    handle_help,
    handle_location_cmd,
    handle_clear,
    handle_location,
    handle_text,
)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or token == "여기에_텔레그램_봇_토큰_입력":
        print("❌ .env 파일에 TELEGRAM_BOT_TOKEN을 설정해주세요.")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("help", handle_help))
    app.add_handler(CommandHandler("location", handle_location_cmd))
    app.add_handler(CommandHandler("clear", handle_clear))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🍽 맛집 추천 봇 시작! (Ctrl+C로 종료)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
