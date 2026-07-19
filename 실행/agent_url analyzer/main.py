import os
import re
import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from parsers import parse_youtube, parse_webpage, parse_pdf
from services import summarize, save_markdown

load_dotenv(override=True)  # 시스템 환경변수보다 .env 우선

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])
ICLOUD_PATH = os.environ["ICLOUD_PATH"]

# 로깅 설정
log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, datetime.now().strftime("%Y-%m-%d") + ".log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(r"https?://[^\s]+")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if chat_id != ALLOWED_CHAT_ID:
        logger.warning(f"허용되지 않은 chat_id 접근: {chat_id}")
        return

    text = update.message.text or ""
    urls = URL_PATTERN.findall(text)

    if not urls:
        await update.message.reply_text("URL을 포함한 메시지를 보내주세요.")
        return

    url = urls[0]
    await update.message.reply_text("처리 중... ⏳")
    logger.info(f"URL 처리 시작: {url}")

    for attempt in range(3):
        try:
            parsed = _parse_url(url)
            result = summarize(parsed)
            filepath = save_markdown(result, ICLOUD_PATH)

            filename = os.path.basename(filepath)
            preview = result["summary"][:300]

            reply = (
                f"✅ 저장 완료!\n\n"
                f"📄 *{result['title']}*\n\n"
                f"{preview}\n\n"
                f"📁 `{filename}`"
            )
            await update.message.reply_text(reply, parse_mode="Markdown")
            logger.info(f"완료: {filename}")
            return

        except ValueError as e:
            # 파싱 실패 등 재시도해도 의미 없는 오류
            await update.message.reply_text(f"❌ {e}")
            logger.error(f"처리 실패: {e}")
            return

        except Exception as e:
            logger.error(f"오류 (시도 {attempt+1}/3): {e}")
            if attempt == 2:
                await update.message.reply_text(
                    "❌ 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                )
            else:
                await asyncio.sleep(5)


def _parse_url(url: str) -> dict:
    if _is_youtube(url):
        return parse_youtube(url)
    elif url.lower().endswith(".pdf") or "/pdf/" in url.lower():
        return parse_pdf(url)
    else:
        return parse_webpage(url)


def _is_youtube(url: str) -> bool:
    return any(domain in url for domain in ["youtube.com", "youtu.be"])


PID_FILE = os.path.join(os.path.dirname(__file__), "bot.pid")


def _check_single_instance():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, "r") as f:
            old_pid = int(f.read().strip())
        try:
            os.kill(old_pid, 0)  # 프로세스 존재 확인
            logger.error(f"봇이 이미 실행 중입니다 (PID: {old_pid}). 먼저 종료해주세요.")
            raise SystemExit(1)
        except ProcessLookupError:
            pass  # 이전 프로세스가 없으면 계속 진행

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))


def _remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def main():
    _check_single_instance()
    try:
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("봇 시작됨")
        app.run_polling()
    finally:
        _remove_pid()


if __name__ == "__main__":
    main()
