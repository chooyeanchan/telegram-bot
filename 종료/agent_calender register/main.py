import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from calendar_service import (
    create_event,
    delete_event,
    list_today_events,
    list_week_events,
)
from gemini_parser import parse_event

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])


def is_allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID


# ── 명령어 핸들러 ──────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    await update.message.reply_text(
        "안녕하세요! 캘린더 등록 봇입니다 📅\n\n"
        "일정을 자유롭게 말씀해 주세요.\n"
        "예) 내일 오후 3시 팀 미팅\n"
        "예) 6월 20일 10시 강남역 고객 미팅\n"
        "예) 매주 월요일 9시 스탠드업\n\n"
        "/today — 오늘 일정 조회\n"
        "/week — 이번 주 일정 조회"
    )


async def today_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        events = list_today_events()
    except FileNotFoundError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    if not events:
        await update.message.reply_text("오늘 예정된 일정이 없습니다.")
        return

    lines = ["📅 오늘 일정\n"]
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        time_str = datetime.fromisoformat(start).strftime("%H:%M") if "T" in start else "종일"
        lines.append(f"• {time_str}  {e['summary']}")

    await update.message.reply_text("\n".join(lines))


async def week_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    try:
        events = list_week_events()
    except FileNotFoundError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    if not events:
        await update.message.reply_text("이번 주 예정된 일정이 없습니다.")
        return

    lines = ["📅 이번 주 일정\n"]
    for e in events:
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        if "T" in start:
            dt = datetime.fromisoformat(start)
            day_kr = ["월", "화", "수", "목", "금", "토", "일"][dt.weekday()]
            date_str = f"{dt.strftime('%m/%d')}({day_kr}) {dt.strftime('%H:%M')}"
        else:
            date_str = start
        lines.append(f"• {date_str}  {e['summary']}")

    await update.message.reply_text("\n".join(lines))


# ── 메시지 핸들러 ──────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return
    text = update.message.text
    msg = await update.message.reply_text("⏳ 일정을 분석하는 중...")

    try:
        event_data = parse_event(text)
    except Exception as e:
        logger.error("파싱 오류: %s", e)
        await msg.edit_text(f"❌ 분석 오류: {e}")
        return

    if not event_data:
        await msg.edit_text(
            "일정을 찾을 수 없었어요.\n날짜·시간·제목을 포함해서 다시 입력해 주세요.\n예) 내일 오후 3시 팀 미팅"
        )
        return

    start_dt = datetime.fromisoformat(event_data["start_datetime"])
    end_dt = datetime.fromisoformat(event_data["end_datetime"])

    lines = [
        "📋 이렇게 등록할까요?\n",
        f"제목: {event_data['title']}",
        f"시작: {start_dt.strftime('%Y-%m-%d %H:%M')}",
        f"종료: {end_dt.strftime('%Y-%m-%d %H:%M')}",
    ]
    if event_data.get("location"):
        lines.append(f"장소: {event_data['location']}")
    if event_data.get("recurrence"):
        lines.append("반복: 설정됨")

    context.user_data["pending_event"] = event_data

    keyboard = [[
        InlineKeyboardButton("✅ 등록", callback_data="confirm"),
        InlineKeyboardButton("❌ 취소", callback_data="cancel"),
    ]]
    await msg.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_allowed(update):
        await query.answer()
        return
    await query.answer()

    if query.data == "confirm":
        event_data = context.user_data.get("pending_event")
        if not event_data:
            await query.edit_message_text("❌ 등록할 일정이 없습니다.")
            return

        try:
            result = create_event(event_data)
        except FileNotFoundError as e:
            await query.edit_message_text(f"❌ {e}")
            return
        except Exception as e:
            logger.error("캘린더 등록 오류: %s", e)
            await query.edit_message_text(f"❌ 등록 실패: {e}")
            return

        link = result.get("htmlLink", "")
        start_dt = datetime.fromisoformat(event_data["start_datetime"])
        await query.edit_message_text(
            f"✅ 등록 완료!\n\n"
            f"{event_data['title']}\n"
            f"{start_dt.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📎 {link}"
        )
        context.user_data.pop("pending_event", None)

    elif query.data == "cancel":
        context.user_data.pop("pending_event", None)
        await query.edit_message_text("취소했습니다.")


# ── 진입점 ────────────────────────────────────────────────

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(".env 파일에 TELEGRAM_BOT_TOKEN이 없습니다.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", today_events))
    app.add_handler(CommandHandler("week", week_events))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("봇 시작 (polling 모드)")
    app.run_polling()


if __name__ == "__main__":
    main()
