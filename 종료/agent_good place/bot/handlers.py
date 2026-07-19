import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot import session
from bot.formatter import (
    build_result_message,
    build_no_result_message,
    build_location_request_message,
)
from agent.orchestrator import recommend

ALLOWED_CHAT_ID = int(os.environ["ALLOWED_CHAT_ID"])


def is_allowed(update: Update) -> bool:
    return update.effective_chat.id == ALLOWED_CHAT_ID


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    text = (
        "👋 안녕하세요! 맛집 추천 에이전트예요.\n\n"
        "*사용법*\n"
        "• 위치 전송 + 원하는 음식: _📍위치_ + '혼밥하기 좋은 일식집'\n"
        "• 텍스트만: '강남역 근처 파스타 맛집 알려줘'\n\n"
        "*커맨드*\n"
        "/location — 저장된 위치 확인\n"
        "/clear — 세션 초기화\n"
        "/help — 도움말"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await handle_start(update, context)


async def handle_location_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    data = session.get(chat_id)
    if data.get("lat"):
        await update.message.reply_text(
            f"📍 저장된 위치: {data['lat']:.5f}, {data['lng']:.5f}"
        )
    else:
        await update.message.reply_text("저장된 위치가 없어요. 위치를 전송하거나 지역명을 포함해 검색해보세요.")


async def handle_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        return
    session.clear(update.effective_chat.id)
    await update.message.reply_text("🗑 세션을 초기화했어요.")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """텔레그램 위치 메시지 수신"""
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    loc = update.message.location
    session.set_location(chat_id, loc.latitude, loc.longitude)
    await update.message.reply_text(
        "📍 위치 저장됐어요! 이제 원하는 음식을 말해주세요.\n예: '혼밥하기 좋은 일식집'"
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """일반 텍스트 메시지 처리 → 맛집 추천"""
    if not is_allowed(update):
        return
    chat_id = update.effective_chat.id
    user_text = update.message.text.strip()

    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    # 세션에서 이전 위치 가져오기
    data = session.get(chat_id)
    lat = data.get("lat")
    lng = data.get("lng")

    ranked, intent = await recommend(user_text, lat, lng)

    # 위치 결정 후 세션 업데이트
    if ranked and intent.get("location_text") and not lat:
        pass  # orchestrator 내부에서 geocoding한 좌표는 별도로 저장하지 않음 (다음 검색 때 재사용 원하면 추가 가능)

    if not ranked:
        # 위치 정보 자체가 없는 경우
        if not lat and not intent.get("location_text"):
            await update.message.reply_text(
                build_location_request_message(), parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(build_no_result_message())
        return

    # 위치 레이블
    location_label = intent.get("location_text") or f"{lat:.4f}, {lng:.4f}"

    msg = build_result_message(ranked, intent, location_label)
    await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
