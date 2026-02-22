from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List


def reaction_keyboard(video_id: int, like_count: int, dislike_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=f"👍 {like_count}", callback_data=f"react:like:{video_id}"),
        InlineKeyboardButton(text=f"👎 {dislike_count}", callback_data=f"react:dislike:{video_id}"),
    )
    return builder.as_markup()


def subscription_keyboard(channels: List[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        builder.row(InlineKeyboardButton(
            text=f"📢 {ch}",
            url=f"https://t.me/{ch.lstrip('@')}"
        ))
    builder.row(InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"))
    return builder.as_markup()


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📹 Video qo'sh", callback_data="admin:addvideo"),
        InlineKeyboardButton(text="📊 Statistika",  callback_data="admin:stats"),
    )
    builder.row(
        InlineKeyboardButton(text="📋 Video ro'yxat", callback_data="admin:videolist"),
        InlineKeyboardButton(text="📈 Grafik",         callback_data="admin:chart"),
    )
    builder.row(
        InlineKeyboardButton(text="📨 Broadcast",      callback_data="admin:broadcast"),
        InlineKeyboardButton(text="🚫 Ban boshqaruv",  callback_data="admin:banmenu"),
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Top referrallar", callback_data="admin:toprefs"),
    )
    return builder.as_markup()


def ban_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚫 Foydalanuvchini ban", callback_data="admin:ban"),
        InlineKeyboardButton(text="✅ Banni ochish",         callback_data="admin:unban"),
    )
    builder.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:panel"))
    return builder.as_markup()


def back_to_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin:panel"))
    return builder.as_markup()


def confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Ha, yuborish", callback_data="broadcast:confirm"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="broadcast:cancel"),
    )
    return builder.as_markup()
