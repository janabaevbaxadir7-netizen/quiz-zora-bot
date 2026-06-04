import logging
import os
import json
import random
import asyncio
import tempfile

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import database as db
from parser import parse_quiz_docx
from texts import t, get_grade

# ── Logging ──
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Config ──
BOT_TOKEN = os.environ["BOT_TOKEN"]
SUPER_ADMIN = int(os.environ["ADMIN_ID"])


# ══════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════

async def get_lang(user_id: int) -> str:
    user = await db.get_user(user_id)
    return user["language"] if user else "uz"


async def check_access(user_id: int) -> bool:
    if user_id == SUPER_ADMIN:
        return True
    if not await db.is_bot_active():
        return False
    return await db.is_subscribed(user_id)


def main_menu_kb(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("➕ " + t(lang, "new_quiz"), callback_data="new_quiz")],
        [InlineKeyboardButton("📋 " + t(lang, "my_quizzes"), callback_data="my_quizzes")],
        [InlineKeyboardButton("🌐 Til / Язык", callback_data="change_lang"),
         InlineKeyboardButton("❓ Yordam", callback_data="help")],
        [InlineKeyboardButton("📊 Status", callback_data="status")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇺🇿 O'zbek tili", callback_data="lang_uz")],
        [InlineKeyboardButton("🇷🇺 Русский язык", callback_data="lang_ru")],
    ])


def mode_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "mode_seq"), callback_data="mode_seq")],
        [InlineKeyboardButton(t(lang, "mode_shuffle_q"), callback_data="mode_shuffle_q")],
        [InlineKeyboardButton(t(lang, "mode_shuffle_a"), callback_data="mode_shuffle_a")],
        [InlineKeyboardButton(t(lang, "mode_shuffle_all"), callback_data="mode_shuffle_all")],
    ])


def option_kb(options: list, lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for opt in options:
        buttons.append([InlineKeyboardButton(
            f"{opt['letter']}) {opt['text']}",
            callback_data=f"answer_{opt['letter']}"
        )])
    buttons.append([InlineKeyboardButton(t(lang, "finish_early"), callback_data="finish_early")])
    return InlineKeyboardMarkup(buttons)


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="adm_users"),
         InlineKeyboardButton("💎 Obunalar", callback_data="adm_subs")],
        [InlineKeyboardButton("➕ Obuna qo'sh", callback_data="adm_add_sub"),
         InlineKeyboardButton("➖ Obuna ol", callback_data="adm_rm_sub")],
        [InlineKeyboardButton("✅ Hammaga obuna", callback_data="adm_add_all"),
         InlineKeyboardButton("❌ Hammadan ol", callback_data="adm_rm_all")],
        [InlineKeyboardButton("👑 Admin qo'sh", callback_data="adm_add_admin"),
         InlineKeyboardButton("🗑️ Admin o'chir", callback_data="adm_rm_admin")],
        [InlineKeyboardButton("👑 Adminlar", callback_data="adm_list_admins"),
         InlineKeyboardButton("📢 Xabar", callback_data="adm_broadcast")],
        [InlineKeyboardButton("📊 Statistika", callback_data="adm_stats"),
         InlineKeyboardButton("🔒 Bot holati", callback_data="adm_toggle")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")],
    ])


# ══════════════════════════════════════════
# COMMANDS
# ══════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.add_user(user.id, user.username, user.first_name)
    lang = await get_lang(user.id)
    is_adm = await db.is_admin(user.id, SUPER_ADMIN)

    if not await db.is_bot_active() and user.id != SUPER_ADMIN:
        await update.message.reply_text(t(lang, "bot_off"))
        return

    if not await check_access(user.id):
        await update.message.reply_text(t(lang, "no_sub"), parse_mode="HTML")
        return

    await update.message.reply_text(
        t(lang, "start", name=user.first_name),
        parse_mode="HTML",
        reply_markup=main_menu_kb(lang, is_adm)
    )


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(user.id)
    if await db.is_subscribed(user.id) or user.id == SUPER_ADMIN:
        await update.message.reply_text(t(lang, "status_active"), parse_mode="HTML")
    else:
        await update.message.reply_text(t(lang, "status_inactive"), parse_mode="HTML")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = await get_lang(update.effective_user.id)
    await update.message.reply_text(t(lang, "help"), parse_mode="HTML")


# ══════════════════════════════════════════
# DOCUMENT HANDLER
# ══════════════════════════════════════════

async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = await get_lang(user.id)

    if not await check_access(user.id):
        await update.message.reply_text(t(lang, "no_sub"), parse_mode="HTML")
        return

    doc = update.message.document
    if not doc.file_name.endswith(".docx"):
        await update.message.reply_text("❌ Faqat .docx fayl qabul qilinadi!")
        return

    msg = await update.message.reply_text("⏳ Fayl o'qilmoqda...")

    try:
        file = await ctx.bot.get_file(doc.file_id)
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            await file.download_to_drive(tmp.name)
            title, questions = parse_quiz_docx(tmp.name)
        os.unlink(tmp.name)
    except Exception as e:
        logger.error(f"File parse error: {e}")
        await msg.edit_text(t(lang, "file_error"))
        return

    if not questions:
        await msg.edit_text(t(lang, "no_questions"))
        return

    # Save quiz to DB
    quiz_id = await db.save_quiz(user.id, title, json.dumps(questions, ensure_ascii=False))

    ctx.user_data["pending_quiz_id"] = quiz_id
    ctx.user_data["pending_title"] = title
    ctx.user_data["pending_questions"] = questions

    await msg.edit_text(
        t(lang, "quiz_found", title=title, count=len(questions)),
        parse_mode="HTML",
        reply_markup=mode_kb(lang)
    )


# ══════════════════════════════════════════
# QUIZ LOGIC
# ══════════════════════════════════════════

def prepare_questions(questions: list, mode: str) -> list:
    qs = [q.copy() for q in questions]
    if mode in ("mode_shuffle_q", "mode_shuffle_all"):
        random.shuffle(qs)
    if mode in ("mode_shuffle_a", "mode_shuffle_all"):
        for q in qs:
            opts = q["options"].copy()
            correct_text = next(o["text"] for o in opts if o["letter"] == q["answer"])
            random.shuffle(opts)
            for i, opt in enumerate(opts):
                opt["letter"] = chr(65 + i)
                if opt["text"] == correct_text:
                    q["answer"] = opt["letter"]
            q["options"] = opts
    return qs


async def send_question(update: Update, ctx: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = update.effective_user.id
    lang = await get_lang(user_id)
    session = ctx.user_data.get("quiz_session")
    if not session:
        return

    idx = session["current"]
    total = len(session["questions"])
    q = session["questions"][idx]

    text = t(lang, "question", num=idx + 1, total=total, question=q["question"])
    kb = option_kb(q["options"], lang)

    if edit and update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await ctx.bot.send_message(user_id, text, parse_mode="HTML", reply_markup=kb)
    else:
        target = update.message or update.callback_query.message
        await target.reply_text(text, parse_mode="HTML", reply_markup=kb)


async def finish_quiz(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await get_lang(user_id)
    session = ctx.user_data.get("quiz_session")
    if not session:
        return

    score = session["score"]
    total = len(session["questions"])
    percent = round(score / total * 100) if total else 0
    grade = get_grade(percent, lang)
    mode = session["mode"]
    quiz_id = session.get("quiz_id", 0)

    await db.save_result(user_id, quiz_id, score, total, mode)

    is_adm = await db.is_admin(user_id, SUPER_ADMIN)
    result_text = t(lang, "result", score=score, total=total, percent=percent, grade=grade)

    ctx.user_data.pop("quiz_session", None)

    if update.callback_query:
        await update.callback_query.edit_message_text(
            result_text, parse_mode="HTML",
            reply_markup=main_menu_kb(lang, is_adm)
        )
    else:
        await update.message.reply_text(
            result_text, parse_mode="HTML",
            reply_markup=main_menu_kb(lang, is_adm)
        )


# ══════════════════════════════════════════
# CALLBACK HANDLER
# ══════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    lang = await get_lang(user_id)
    is_adm = await db.is_admin(user_id, SUPER_ADMIN)

    # ── Language ──
    if data == "change_lang":
        await query.edit_message_text(t(lang, "choose_lang"), reply_markup=lang_kb())
        return

    if data in ("lang_uz", "lang_ru"):
        new_lang = data.split("_")[1]
        await db.set_language(user_id, new_lang)
        await query.edit_message_text(
            t(new_lang, "lang_set"),
            reply_markup=main_menu_kb(new_lang, is_adm)
        )
        return

    # ── Main menu ──
    if data == "main_menu":
        await query.edit_message_text(
            t(lang, "start", name=query.from_user.first_name),
            parse_mode="HTML",
            reply_markup=main_menu_kb(lang, is_adm)
        )
        return

    if data == "help":
        await query.edit_message_text(
            t(lang, "help"),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")
            ]])
        )
        return

    if data == "status":
        subbed = await db.is_subscribed(user_id) or user_id == SUPER_ADMIN
        txt = t(lang, "status_active") if subbed else t(lang, "status_inactive")
        await query.edit_message_text(
            txt,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")
            ]])
        )
        return

    if data == "new_quiz":
        if not await check_access(user_id):
            await query.edit_message_text(t(lang, "no_sub"), parse_mode="HTML")
            return
        await query.edit_message_text(t(lang, "send_file"), parse_mode="HTML")
        return

    if data == "my_quizzes":
        quizzes = await db.get_user_quizzes(user_id)
        if not quizzes:
            await query.edit_message_text(
                t(lang, "no_quizzes"),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")
                ]])
            )
            return
        text = "📋 <b>Mening quizlarim:</b>\n\n"
        buttons = []
        for q in quizzes:
            text_short = q["title"][:30]
            buttons.append([InlineKeyboardButton(
                f"📝 {text_short}", callback_data=f"load_quiz_{q['id']}"
            )])
        buttons.append([InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")])
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("load_quiz_"):
        quiz_id = int(data.split("_")[2])
        quiz = await db.get_quiz(quiz_id)
        if not quiz:
            await query.answer("Quiz topilmadi!", show_alert=True)
            return
        questions = json.loads(quiz["questions"])
        ctx.user_data["pending_quiz_id"] = quiz_id
        ctx.user_data["pending_title"] = quiz["title"]
        ctx.user_data["pending_questions"] = questions
        await query.edit_message_text(
            t(lang, "quiz_found", title=quiz["title"], count=len(questions)),
            parse_mode="HTML",
            reply_markup=mode_kb(lang)
        )
        return

    # ── Quiz mode ──
    if data in ("mode_seq", "mode_shuffle_q", "mode_shuffle_a", "mode_shuffle_all"):
        questions = ctx.user_data.get("pending_questions")
        quiz_id = ctx.user_data.get("pending_quiz_id", 0)
        if not questions:
            await query.edit_message_text("❌ Quiz topilmadi. Qaytadan fayl yuboring.")
            return
        prepared = prepare_questions(questions, data)
        ctx.user_data["quiz_session"] = {
            "questions": prepared,
            "current": 0,
            "score": 0,
            "mode": data,
            "quiz_id": quiz_id,
        }
        ctx.user_data.pop("pending_questions", None)
        await send_question(update, ctx, edit=True)
        return

    # ── Answer ──
    if data.startswith("answer_"):
        session = ctx.user_data.get("quiz_session")
        if not session:
            await query.answer("Quiz sessiyasi topilmadi!", show_alert=True)
            return

        chosen = data.split("_")[1]
        q = session["questions"][session["current"]]
        correct = q["answer"]

        if chosen == correct:
            session["score"] += 1
            feedback = t(lang, "correct")
        else:
            correct_text = next(
                (o["text"] for o in q["options"] if o["letter"] == correct), correct
            )
            feedback = t(lang, "wrong", answer=f"{correct}) {correct_text}")

        session["current"] += 1

        if session["current"] >= len(session["questions"]):
            # Quiz done
            await query.edit_message_text(feedback, parse_mode="HTML")
            await asyncio.sleep(1)
            await finish_quiz(update, ctx)
        else:
            await query.edit_message_text(feedback, parse_mode="HTML")
            await asyncio.sleep(1)
            await send_question(update, ctx, edit=False)
        return

    if data == "finish_early":
        await finish_quiz(update, ctx)
        return

    # ══════════════════════════════════════
    # ADMIN PANEL
    # ══════════════════════════════════════

    if data == "admin_panel":
        if not is_adm:
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        stats = await db.get_stats()
        text = (
            "⚙️ <b>Admin Panel</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"💎 Faol obunalar: <b>{stats['active_subs']}</b>\n"
            f"📝 Jami quizlar: <b>{stats['total_quizzes']}</b>\n"
            f"📊 Natijalari: <b>{stats['total_results']}</b>\n"
            f"🆕 Bugun: <b>{stats['today_users']}</b>\n"
            f"🔒 Bot: <b>{'Ochiq ✅' if await db.is_bot_active() else 'Yopiq 🔒'}</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_kb())
        return

    if data == "adm_stats":
        if not is_adm:
            return
        stats = await db.get_stats()
        text = (
            "📊 <b>Statistika</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"💎 Faol obunalar: <b>{stats['active_subs']}</b>\n"
            f"📝 Jami quizlar: <b>{stats['total_quizzes']}</b>\n"
            f"🏆 Natijalar: <b>{stats['total_results']}</b>\n"
            f"🆕 Bugungi yangi: <b>{stats['today_users']}</b>"
        )
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_users":
        if not is_adm:
            return
        users = await db.get_all_users()
        text = f"👥 <b>Foydalanuvchilar ({len(users)} ta):</b>\n\n"
        for u in users[:30]:
            uname = f"@{u['username']}" if u['username'] else "—"
            text += f"• {u['first_name']} | {uname} | <code>{u['user_id']}</code>\n"
        if len(users) > 30:
            text += f"\n... va yana {len(users)-30} ta"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_subs":
        if not is_adm:
            return
        subs = await db.get_all_subscriptions()
        text = f"💎 <b>Faol obunalar ({len(subs)} ta):</b>\n\n"
        for s in subs[:30]:
            uname = f"@{s['username']}" if s['username'] else "—"
            text += f"• {s['first_name']} | {uname} | <code>{s['user_id']}</code>\n"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_add_sub":
        if not is_adm:
            return
        ctx.user_data["admin_action"] = "add_sub"
        await query.edit_message_text(
            "💎 Obuna qo'shish\n\nFoydalanuvchi ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_rm_sub":
        if not is_adm:
            return
        ctx.user_data["admin_action"] = "rm_sub"
        await query.edit_message_text(
            "➖ Obunani olib tashlash\n\nFoydalanuvchi ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_add_all":
        if not is_adm:
            return
        count = await db.add_all_subscriptions(user_id)
        await query.answer(f"✅ {count} ta foydalanuvchiga obuna qo'shildi!", show_alert=True)
        await query.edit_message_text(
            f"✅ Barcha {count} ta foydalanuvchiga obuna qo'shildi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_rm_all":
        if not is_adm:
            return
        await db.remove_all_subscriptions()
        await query.answer("✅ Hammadan obuna olib tashlandi!", show_alert=True)
        await query.edit_message_text(
            "✅ Barcha foydalanuvchilardan obuna olib tashlandi!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_add_admin":
        if user_id != SUPER_ADMIN:
            await query.answer("❌ Faqat super admin!", show_alert=True)
            return
        ctx.user_data["admin_action"] = "add_admin"
        await query.edit_message_text(
            "👑 Admin qo'shish\n\nYangi admin ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_rm_admin":
        if user_id != SUPER_ADMIN:
            await query.answer("❌ Faqat super admin!", show_alert=True)
            return
        ctx.user_data["admin_action"] = "rm_admin"
        await query.edit_message_text(
            "🗑️ Admin o'chirish\n\nAdmin ID sini yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_list_admins":
        if not is_adm:
            return
        admins = await db.get_all_admins()
        text = f"👑 <b>Adminlar ({len(admins)} ta):</b>\n\n"
        text += f"🌟 Super Admin: <code>{SUPER_ADMIN}</code>\n\n"
        for a in admins:
            text += f"• <code>{a['user_id']}</code> | {a['role']}\n"
        await query.edit_message_text(
            text, parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_broadcast":
        if not is_adm:
            return
        ctx.user_data["admin_action"] = "broadcast"
        await query.edit_message_text(
            "📢 Hammaga xabar\n\nXabar matnini yozing:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("❌ Bekor", callback_data="admin_panel")
            ]])
        )
        return

    if data == "adm_toggle":
        if not is_adm:
            return
        new_state = await db.toggle_bot()
        state_txt = "Ochiq ✅" if new_state else "Yopiq 🔒"
        await query.answer(f"Bot holati: {state_txt}", show_alert=True)
        stats = await db.get_stats()
        text = (
            "⚙️ <b>Admin Panel</b>\n\n"
            f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"💎 Faol obunalar: <b>{stats['active_subs']}</b>\n"
            f"🔒 Bot: <b>{state_txt}</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=admin_kb())
        return


# ══════════════════════════════════════════
# TEXT MESSAGE HANDLER (admin actions)
# ══════════════════════════════════════════

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = await get_lang(user_id)
    text = update.message.text.strip()
    action = ctx.user_data.get("admin_action")
    is_adm = await db.is_admin(user_id, SUPER_ADMIN)

    if not is_adm or not action:
        # Normal user — check access
        if not await check_access(user_id):
            await update.message.reply_text(t(lang, "no_sub"), parse_mode="HTML")
            return
        await update.message.reply_text(
            t(lang, "send_file"),
            reply_markup=main_menu_kb(lang, is_adm)
        )
        return

    ctx.user_data.pop("admin_action", None)

    if action == "add_sub":
        try:
            uid = int(text)
            await db.add_subscription(uid, user_id)
            await update.message.reply_text(
                f"✅ <code>{uid}</code> ga obuna qo'shildi!",
                parse_mode="HTML", reply_markup=admin_kb()
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!", reply_markup=admin_kb())

    elif action == "rm_sub":
        try:
            uid = int(text)
            await db.remove_subscription(uid)
            await update.message.reply_text(
                f"✅ <code>{uid}</code> dan obuna olib tashlandi!",
                parse_mode="HTML", reply_markup=admin_kb()
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!", reply_markup=admin_kb())

    elif action == "add_admin":
        try:
            uid = int(text)
            await db.add_admin(uid, user_id)
            await update.message.reply_text(
                f"✅ <code>{uid}</code> admin qilindi!",
                parse_mode="HTML", reply_markup=admin_kb()
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!", reply_markup=admin_kb())

    elif action == "rm_admin":
        try:
            uid = int(text)
            if uid == SUPER_ADMIN:
                await update.message.reply_text("❌ Super adminni o'chirib bo'lmaydi!")
                return
            await db.remove_admin(uid)
            await update.message.reply_text(
                f"✅ <code>{uid}</code> admin ro'yxatidan o'chirildi!",
                parse_mode="HTML", reply_markup=admin_kb()
            )
        except ValueError:
            await update.message.reply_text("❌ Noto'g'ri ID!", reply_markup=admin_kb())

    elif action == "broadcast":
        users = await db.get_all_users()
        success = 0
        failed = 0
        for u in users:
            try:
                await ctx.bot.send_message(u["user_id"], text, parse_mode="HTML")
                success += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"📢 Xabar yuborildi!\n✅ Muvaffaqiyatli: {success}\n❌ Yuborilmadi: {failed}",
            reply_markup=admin_kb()
        )


# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════

def main():
    import asyncio

    async def post_init(app):
        await db.init_db()
        logger.info("✅ DB initialized")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("🚀 Bot ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
