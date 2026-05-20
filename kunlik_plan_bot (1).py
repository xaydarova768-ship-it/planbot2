#!/usr/bin/env python3
import logging
import os
import random
from datetime import datetime
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler,
    MessageHandler, Filters, ConversationHandler
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TIMEZONE = pytz.timezone("Asia/Tashkent")

CHOOSING, ADDING_TASK, ADDING_TIME, ADDING_CAT = range(4)

CATS = {
    "💼": "Ish", "📚": "O'qish", "🏃": "Sport",
    "🏠": "Uy", "👤": "Shaxsiy", "🎯": "Boshqa"
}

MOTIVLAR = [
    "💪 Har bir qadam maqsad sari!",
    "🔥 Bugun kuchli kun!",
    "⭐ Kichik qadamlar katta yutuq!",
    "🚀 Muvaffaqiyat mehnatdan boshlanadi!",
    "🌟 Siz qila olasiz!",
]

MASLAHATLAR = [
    "📌 Eng muhim 3 vazifadan boshlang!",
    "⏰ Har vazifaga vaqt belgilang.",
    "🧠 Muhim ishlarni ertalab bajaring.",
    "💧 Har soatda suv iching.",
    "📝 Kechqurun ertangi rejaingizni tuzing.",
]

logging.basicConfig(level=logging.INFO)
user_plans = {}

def today():
    return datetime.now(TIMEZONE).strftime("%Y-%m-%d")

def get_tasks(uid):
    return user_plans.get(uid, {}).get(today(), [])

def add_task(uid, task):
    if uid not in user_plans:
        user_plans[uid] = {}
    if today() not in user_plans[uid]:
        user_plans[uid][today()] = []
    user_plans[uid][today()].append(task)

def toggle(uid, i):
    tasks = get_tasks(uid)
    if 0 <= i < len(tasks):
        tasks[i]["done"] = not tasks[i].get("done", False)

def delete(uid, i):
    tasks = get_tasks(uid)
    if 0 <= i < len(tasks):
        tasks.pop(i)

def pbar(done, total):
    if not total:
        return "⬜" * 10 + " 0%"
    p = int(done / total * 100)
    return "🟩" * (p // 10) + "⬜" * (10 - p // 10) + f" {p}%"

def menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Vazifa qo'shish", callback_data="add"),
         InlineKeyboardButton("📋 Reja", callback_data="view")],
        [InlineKeyboardButton("✅ Bajarildi", callback_data="done"),
         InlineKeyboardButton("🗑 O'chirish", callback_data="del")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stat"),
         InlineKeyboardButton("💡 Maslahat", callback_data="tip")],
    ])

def start(update, context):
    text = (
        f"Salom, {update.effective_user.first_name}! 👋\n\n"
        f"🗓 Kunlik Reja Botiga xush kelibsiz!\n\n"
        f"{random.choice(MOTIVLAR)}\n\nBoshlaylik! 👇"
    )
    update.message.reply_text(text, reply_markup=menu())
    return CHOOSING

def view(update, context):
    q = update.callback_query
    q.answer()
    uid = q.from_user.id
    tasks = get_tasks(uid)
    today_str = datetime.now(TIMEZONE).strftime("%d.%m.%Y")

    if not tasks:
        text = f"📅 {today_str}\n\n📭 Hali vazifa yo'q!\n\n{random.choice(MOTIVLAR)}"
    else:
        done = sum(1 for t in tasks if t.get("done"))
        text = f"📅 {today_str}\n{pbar(done, len(tasks))}\n✅ {done}/{len(tasks)}\n\n"
        for i, t in enumerate(tasks):
            s = "✅" if t.get("done") else "⬜"
            tm = f" 🕐{t['time']}" if t.get("time") else ""
            text += f"{s} {i+1}. {t['name']}{tm}\n"

    q.edit_message_text(text, reply_markup=menu())
    return CHOOSING

def add_start(update, context):
    q = update.callback_query
    q.answer()
    q.edit_message_text("➕ Vazifa nomini yozing:")
    return ADDING_TASK

def get_name(update, context):
    context.user_data["task"] = {"name": update.message.text.strip()}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("⏭ O'tkazish", callback_data="skip")]])
    update.message.reply_text("🕐 Vaqtini yozing (09:00):", reply_markup=kb)
    return ADDING_TIME

def get_time(update, context):
    context.user_data["task"]["time"] = update.message.text.strip()
    return ask_cat(update, context)

def skip_time(update, context):
    q = update.callback_query
    q.answer()
    context.user_data["task"]["time"] = None
    return ask_cat(update, context, True)

def ask_cat(update, context, cb=False):
    cats = list(CATS.items())
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in cats[:3]],
        [InlineKeyboardButton(f"{e} {n}", callback_data=f"cat_{e}") for e, n in cats[3:]],
    ])
    if cb:
        update.callback_query.edit_message_text("📁 Kategoriya:", reply_markup=kb)
    else:
        update.message.reply_text("📁 Kategoriya:", reply_markup=kb)
    return ADDING_CAT

def get_cat(update, context):
    q = update.callback_query
    q.answer()
    emoji = q.data.replace("cat_", "")
    task = context.user_data.get("task", {})
    task["category"] = emoji
    task["done"] = False
    add_task(q.from_user.id, task)
    tm = f" 🕐{task['time']}" if task.get("time") else ""
    q.edit_message_text(
        f"✅ Qo'shildi!\n{emoji} {task['name']}{tm}\n\n{random.choice(MOTIVLAR)}",
        reply_markup=menu()
    )
    return CHOOSING

def done_start(update, context):
    q = update.callback_query
    q.answer()
    tasks = get_tasks(q.from_user.id)
    if not tasks:
        q.answer("❌ Vazifa yo'q!", show_alert=True)
        return CHOOSING
    kb = [[InlineKeyboardButton(
        f"{'✅' if t.get('done') else '⬜'} {i+1}. {t['name']}",
        callback_data=f"tog_{i}"
    )] for i, t in enumerate(tasks)]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="view")])
    q.edit_message_text("✅ Belgilash:", reply_markup=InlineKeyboardMarkup(kb))
    return CHOOSING

def toggle_handler(update, context):
    q = update.callback_query
    q.answer()
    toggle(q.from_user.id, int(q.data.replace("tog_", "")))
    return done_start(update, context)

def del_start(update, context):
    q = update.callback_query
    q.answer()
    tasks = get_tasks(q.from_user.id)
    if not tasks:
        q.answer("❌ Vazifa yo'q!", show_alert=True)
        return CHOOSING
    kb = [[InlineKeyboardButton(f"🗑 {i+1}. {t['name']}", callback_data=f"delc_{i}")] for i, t in enumerate(tasks)]
    kb.append([InlineKeyboardButton("🔙 Orqaga", callback_data="view")])
    q.edit_message_text("🗑 O'chirish:", reply_markup=InlineKeyboardMarkup(kb))
    return CHOOSING

def del_confirm(update, context):
    q = update.callback_query
    q.answer("O'chirildi!")
    delete(q.from_user.id, int(q.data.replace("delc_", "")))
    return view(update, context)

def stat(update, context):
    q = update.callback_query
    q.answer()
    tasks = get_tasks(q.from_user.id)
    total = len(tasks)
    done = sum(1 for t in tasks if t.get("done"))
    p = int(done / total * 100) if total else 0
    text = (
        f"📊 Bugungi statistika\n\n"
        f"{pbar(done, total)}\n"
        f"✅ Bajarildi: {done}\n"
        f"⬜ Qoldi: {total-done}\n"
        f"📌 Jami: {total}\n"
        f"🏆 {p}%\n\n"
    )
    if p == 100 and total:
        text += "🎉 Hammasi bajarildi!"
    elif p >= 50:
        text += "💪 Yaxshi ketayapti!"
    else:
        text += "🔥 Davom eting!"
    q.edit_message_text(text, reply_markup=menu())
    return CHOOSING

def tip(update, context):
    q = update.callback_query
    q.answer()
    q.edit_message_text(
        f"💡 Maslahat\n\n{random.choice(MASLAHATLAR)}\n\n{random.choice(MOTIVLAR)}",
        reply_markup=menu()
    )
    return CHOOSING

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(add_start, pattern="^add$"),
                CallbackQueryHandler(view, pattern="^view$"),
                CallbackQueryHandler(done_start, pattern="^done$"),
                CallbackQueryHandler(del_start, pattern="^del$"),
                CallbackQueryHandler(stat, pattern="^stat$"),
                CallbackQueryHandler(tip, pattern="^tip$"),
                CallbackQueryHandler(toggle_handler, pattern="^tog_"),
                CallbackQueryHandler(del_confirm, pattern="^delc_"),
            ],
            ADDING_TASK: [MessageHandler(Filters.text & ~Filters.command, get_name)],
            ADDING_TIME: [
                MessageHandler(Filters.text & ~Filters.command, get_time),
                CallbackQueryHandler(skip_time, pattern="^skip$"),
            ],
            ADDING_CAT: [CallbackQueryHandler(get_cat, pattern="^cat_")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    dp.add_handler(conv)
    print("Bot ishga tushdi!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
