import logging
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

import database as db
from config import config
from keyboards.inline import reaction_keyboard, subscription_keyboard
from services.subscription import check_user_subscriptions
from services.cache import invalidate_subscription

logger = logging.getLogger(__name__)
router = Router(name="user")


# ─── Subscription gate ────────────────────────────────────────────────────────

async def subscription_gate(event, bot: Bot) -> bool:
    """Returns True if user passed subscription check."""
    uid = event.from_user.id
    missing = await check_user_subscriptions(bot, uid)
    if not missing:
        return True

    text = (
        "⚠️ <b>Botdan foydalanish uchun</b> quyidagi kanallarga obuna bo'ling:\n\n"
        + "\n".join(f"  • {ch}" for ch in missing)
        + "\n\n✅ Obuna bo'lgach, <b>Tekshirish</b> tugmasini bosing."
    )
    kb = subscription_keyboard(config.REQUIRED_CHANNELS)

    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        try:
            await event.message.edit_text(text, reply_markup=kb)
        except Exception:
            await event.message.answer(text, reply_markup=kb)
    return False


# ─── /start ──────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, bot: Bot):
    # Referral: /start ref_123456789
    args = message.text.split(maxsplit=1)
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            rid = int(args[1][4:])
            if rid != message.from_user.id:
                referrer_id = rid
        except ValueError:
            pass

    # Register with referral
    is_new = await db.upsert_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referrer_id=referrer_id
    )

    if is_new and referrer_id:
        try:
            await bot.send_message(
                referrer_id,
                f"🎉 Yangi foydalanuvchi sizning havolangiz orqali qo'shildi!\n"
                f"👤 {message.from_user.full_name}"
            )
        except Exception:
            pass

    if not await subscription_gate(message, bot):
        return

    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref_{message.from_user.id}"

    await message.answer(
        f"👋 Salom, <b>{message.from_user.full_name}</b>!\n\n"
        f"🎬 Video kodini yozing (masalan: <code>1</code>)\n"
        f"Bot sizga shu videoni yuboradi.\n\n"
        f"🔗 <b>Sizning referral havolangiz:</b>\n"
        f"<code>{ref_link}</code>",
    )


# ─── Check subscription ───────────────────────────────────────────────────────

@router.callback_query(F.data == "check_sub")
async def cb_check_sub(callback: CallbackQuery, bot: Bot):
    await callback.answer()
    await invalidate_subscription(callback.from_user.id)  # force recheck
    missing = await check_user_subscriptions(bot, callback.from_user.id)

    if missing:
        await callback.message.edit_text(
            "❌ Hali obuna bo'lmagan kanallar bor:\n\n"
            + "\n".join(f"  • {ch}" for ch in missing),
            reply_markup=subscription_keyboard(config.REQUIRED_CHANNELS),
        )
    else:
        me = await bot.get_me()
        ref_link = f"https://t.me/{me.username}?start=ref_{callback.from_user.id}"
        await callback.message.edit_text(
            "✅ <b>Barcha kanallarga obuna bo'ldingiz!</b>\n\n"
            f"🎬 Video kodini yozing (masalan: <code>1</code>)\n\n"
            f"🔗 <b>Referral havolangiz:</b>\n<code>{ref_link}</code>",
        )


# ─── Video code ───────────────────────────────────────────────────────────────

@router.message(F.text.regexp(r"^\d+$"))
async def handle_video_code(message: Message, bot: Bot):
    if not await subscription_gate(message, bot):
        return

    code = message.text.strip()
    video = await db.get_video(code)

    if not video:
        await message.answer(
            f"❌ <b>{code}</b> kodli video topilmadi.\n"
            "Boshqa kod kiriting."
        )
        return

    kb = reaction_keyboard(video["id"], video["like_count"], video["dislike_count"])
    cap = (
        f"🎬 <b>{video['title'] or f'Video #{code}'}</b>\n\n"
        f"👁 {video['view_count']} ta ko'rilgan  "
        f"👍 {video['like_count']}  👎 {video['dislike_count']}"
    )
    await message.answer_video(video=video["file_id"], caption=cap, reply_markup=kb)


# ─── Reactions ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("react:"))
async def cb_reaction(callback: CallbackQuery, bot: Bot):
    await callback.answer()

    if not await subscription_gate(callback, bot):
        return

    _, reaction, vid_str = callback.data.split(":")
    video_id = int(vid_str)

    existing = await db.get_user_reaction(callback.from_user.id, video_id)
    if existing == reaction:
        emoji = "👍" if reaction == "like" else "👎"
        await callback.answer(f"Siz allaqachon {emoji} qo'ygansiz.", show_alert=False)
        return

    result = await db.set_reaction(callback.from_user.id, video_id, reaction)
    kb = reaction_keyboard(video_id, result["like_count"], result["dislike_count"])
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

    emoji = "👍" if reaction == "like" else "👎"
    await callback.answer(f"{emoji} Reaksiya qabul qilindi!", show_alert=False)
