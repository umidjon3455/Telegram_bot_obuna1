"""
Advanced admin panel with:
- Inline admin panel menu
- /addvideo FSM flow
- /stats with chart
- Broadcast (with confirm step)
- Ban / Unban
- Video list & delete
- Top referrers
"""
import asyncio
import logging
from typing import Dict

from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, BufferedInputFile

import database as db
from config import config
from keyboards.inline import (
    admin_panel_keyboard, ban_menu_keyboard, back_to_panel,
    confirm_broadcast_keyboard, reaction_keyboard
)
from services.broadcast import broadcast
from services.charts import generate_stats_chart
from services.cache import invalidate_ban, invalidate_video

logger = logging.getLogger(__name__)
router = Router(name="admin")


# ─── States ──────────────────────────────────────────────────────────────────

class AddVideo(StatesGroup):
    code  = State()
    title = State()
    file  = State()


class BanFlow(StatesGroup):
    waiting_id = State()


class UnbanFlow(StatesGroup):
    waiting_id = State()


class BroadcastFlow(StatesGroup):
    waiting_message = State()
    confirm         = State()


class DeleteVideo(StatesGroup):
    waiting_code = State()


# ─── Guard ───────────────────────────────────────────────────────────────────

async def admin_guard(event) -> bool:
    uid = event.from_user.id if hasattr(event, "from_user") else None
    if uid not in config.ADMIN_IDS:
        if isinstance(event, Message):
            await event.answer("🚫 Admin huquqi yo'q.")
        elif isinstance(event, CallbackQuery):
            await event.answer("🚫 Admin huquqi yo'q.", show_alert=True)
        return False
    return True


# ─── /admin ──────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not await admin_guard(message):
        return
    await message.answer(
        "🛠 <b>Admin Panel</b>\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=admin_panel_keyboard()
    )


# ─── Panel callback router ───────────────────────────────────────────────────

@router.callback_query(F.data == "admin:panel")
async def cb_panel(callback: CallbackQuery, state: FSMContext):
    if not await admin_guard(callback):
        return
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "🛠 <b>Admin Panel</b>\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=admin_panel_keyboard()
    )


# ─── STATS ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def cb_stats(callback: CallbackQuery):
    if not await admin_guard(callback):
        return
    await callback.answer()
    s = await db.get_full_stats()
    await callback.message.edit_text(
        f"📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{s['users_total']}</b>\n"
        f"✅ Faol: <b>{s['users_active']}</b>\n"
        f"🚫 Banned: <b>{s['users_banned']}</b>\n"
        f"🆕 Bugun yangi: <b>{s['new_today']}</b>\n\n"
        f"🎬 Videolar: <b>{s['videos_total']}</b>\n"
        f"👁 Jami ko'rishlar: <b>{s['total_views']}</b>\n"
        f"👍 Jami likelar: <b>{s['total_likes']}</b>\n"
        f"👎 Jami dislikelar: <b>{s['total_dislikes']}</b>",
        reply_markup=back_to_panel()
    )


# ─── CHART ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:chart")
async def cb_chart(callback: CallbackQuery, bot: Bot):
    if not await admin_guard(callback):
        return
    await callback.answer("📈 Grafik tayyorlanmoqda...")
    daily = await db.get_daily_stats(7)

    if not daily:
        await callback.message.answer("📭 Statistika ma'lumotlari yo'q.")
        return

    try:
        buf = await generate_stats_chart(daily)
        photo = BufferedInputFile(buf.read(), filename="stats.png")
        await callback.message.answer_photo(photo, caption="📈 <b>7 kunlik statistika</b>")
    except ImportError:
        await callback.message.answer("⚠️ Grafik uchun matplotlib kerak:\npip install matplotlib")


# ─── ADD VIDEO ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:addvideo")
async def cb_addvideo(callback: CallbackQuery, state: FSMContext):
    if not await admin_guard(callback):
        return
    await callback.answer()
    await state.set_state(AddVideo.code)
    await callback.message.edit_text(
        "📹 <b>Video qo'shish</b>\n\n"
        "1️⃣ Video kodini kiriting (masalan: <code>42</code>):"
    )


@router.message(AddVideo.code, F.text)
async def av_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if not code.isdigit():
        await message.answer("❌ Faqat raqam kiriting.")
        return
    if await db.get_video(code):
        await message.answer(f"⚠️ <b>{code}</b> kodli video mavjud. Boshqa kod kiriting:")
        return
    await state.update_data(code=code)
    await state.set_state(AddVideo.title)
    await message.answer("2️⃣ Video sarlavhasini kiriting (o'tkazib yuborish: <code>-</code>):")


@router.message(AddVideo.title, F.text)
async def av_title(message: Message, state: FSMContext):
    title = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AddVideo.file)
    await message.answer("3️⃣ Videoni yuboring:")


@router.message(AddVideo.file, F.video)
async def av_file(message: Message, state: FSMContext):
    data = await state.get_data()
    ok = await db.add_video(data["code"], message.video.file_id, data.get("title"), message.from_user.id)
    await state.clear()
    if ok:
        await message.answer(
            f"✅ <b>Video qo'shildi!</b>\n\n"
            f"🔢 Kod: <code>{data['code']}</code>\n"
            f"🎬 Sarlavha: {data.get('title') or '—'}",
            reply_markup=back_to_panel()
        )
    else:
        await message.answer("❌ Xatolik yuz berdi.", reply_markup=back_to_panel())


@router.message(AddVideo.file)
async def av_wrong(message: Message):
    await message.answer("❌ Faqat video yuboring.")


# ─── VIDEO LIST ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:videolist")
async def cb_videolist(callback: CallbackQuery):
    if not await admin_guard(callback):
        return
    await callback.answer()
    videos = await db.list_all_video_codes()
    if not videos:
        await callback.message.edit_text("📭 Videolar yo'q.", reply_markup=back_to_panel())
        return

    lines = []
    for v in videos[:30]:
        title = v["title"] or "—"
        lines.append(
            f"• <code>{v['code']}</code> | {title} | "
            f"👁{v['view_count']} 👍{v['like_count']} 👎{v['dislike_count']}"
        )

    text = f"🎬 <b>Video ro'yxati ({len(videos)} ta)</b>\n\n" + "\n".join(lines)
    if len(videos) > 30:
        text += f"\n\n...va yana {len(videos)-30} ta"

    await callback.message.edit_text(text, reply_markup=back_to_panel())


# ─── BAN / UNBAN ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:banmenu")
async def cb_banmenu(callback: CallbackQuery):
    if not await admin_guard(callback):
        return
    await callback.answer()
    await callback.message.edit_text("🚫 <b>Ban boshqaruvi</b>", reply_markup=ban_menu_keyboard())


@router.callback_query(F.data == "admin:ban")
async def cb_ban_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_guard(callback):
        return
    await callback.answer()
    await state.set_state(BanFlow.waiting_id)
    await callback.message.edit_text("🚫 Bloklash uchun foydalanuvchi ID sini kiriting:")


@router.message(BanFlow.waiting_id, F.text)
async def ban_process(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    await state.clear()
    if uid in config.ADMIN_IDS:
        await message.answer("⛔ Adminni ban qilib bo'lmaydi!")
        return
    ok = await db.ban_user(uid)
    await invalidate_ban(uid)
    if ok:
        await message.answer(f"✅ Foydalanuvchi <code>{uid}</code> bloklandi.", reply_markup=back_to_panel())
    else:
        await message.answer(f"⚠️ <code>{uid}</code> topilmadi yoki allaqachon bloklangan.", reply_markup=back_to_panel())


@router.callback_query(F.data == "admin:unban")
async def cb_unban_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_guard(callback):
        return
    await callback.answer()
    await state.set_state(UnbanFlow.waiting_id)
    await callback.message.edit_text("✅ Banni ochish uchun foydalanuvchi ID sini kiriting:")


@router.message(UnbanFlow.waiting_id, F.text)
async def unban_process(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri ID.")
        return
    await state.clear()
    ok = await db.unban_user(uid)
    await invalidate_ban(uid)
    if ok:
        await message.answer(f"✅ <code>{uid}</code> ning bani ochildi.", reply_markup=back_to_panel())
    else:
        await message.answer(f"⚠️ <code>{uid}</code> topilmadi yoki ban qilinmagan.", reply_markup=back_to_panel())


# ─── BROADCAST ───────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:broadcast")
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not await admin_guard(callback):
        return
    await callback.answer()
    await state.set_state(BroadcastFlow.waiting_message)
    await callback.message.edit_text(
        "📨 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga yuborish uchun xabar yuboring\n"
        "(matn, rasm, video — istalgan format):"
    )


@router.message(BroadcastFlow.waiting_message)
async def broadcast_preview(message: Message, state: FSMContext):
    await state.update_data(message_id=message.message_id, chat_id=message.chat.id)
    await state.set_state(BroadcastFlow.confirm)
    count = await db.get_user_count()
    await message.answer(
        f"👆 Yuqoridagi xabar <b>{count}</b> ta foydalanuvchiga yuboriladi.\n\n"
        "Tasdiqlaysizmi?",
        reply_markup=confirm_broadcast_keyboard()
    )


@router.callback_query(F.data == "broadcast:confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if not await admin_guard(callback):
        return
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    src_msg = await bot.forward_message(
        chat_id=callback.from_user.id,
        from_chat_id=data["chat_id"],
        message_id=data["message_id"]
    )
    # Use a status message to show live progress
    status = await callback.message.edit_text("⏳ Broadcast boshlandi...")

    result = await broadcast(bot, src_msg, status)

    await status.edit_text(
        f"✅ <b>Broadcast tugadi!</b>\n\n"
        f"📤 Yuborildi: <b>{result['sent']}</b>\n"
        f"❌ Xatolik: <b>{result['failed']}</b>\n"
        f"📊 Jami: <b>{result['total']}</b>",
        reply_markup=back_to_panel()
    )


@router.callback_query(F.data == "broadcast:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Bekor qilindi.")
    await callback.message.edit_text("❌ Broadcast bekor qilindi.", reply_markup=back_to_panel())


# ─── TOP REFERRERS ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:toprefs")
async def cb_toprefs(callback: CallbackQuery):
    if not await admin_guard(callback):
        return
    await callback.answer()
    refs = await db.get_top_referrers(10)
    if not refs:
        await callback.message.edit_text("📭 Referral ma'lumotlari yo'q.", reply_markup=back_to_panel())
        return

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = []
    for i, r in enumerate(refs):
        name = f"@{r['username']}" if r["username"] else r["full_name"]
        lines.append(f"{medals[i]} {name} — <b>{r['ref_count']}</b> ta taklif")

    await callback.message.edit_text(
        "🏆 <b>Top referrallar</b>\n\n" + "\n".join(lines),
        reply_markup=back_to_panel()
    )


# ─── /cancel ─────────────────────────────────────────────────────────────────

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("❌ Amal bekor qilindi.", reply_markup=back_to_panel())
    else:
        await message.answer("Bekor qilish uchun hech narsa yo'q.")
