# bot.py — نسخة جاهزة للعمل على Render باستخدام Polling
import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === عيّن توكن البوت هنا ===
BOT_TOKEN = "8343481325:AAGk1Mro9_LgeSZoq4m_WnfGNfYzg6j8OeM"

# === تحميل الاقتباسات ===
with open("quotes.json", "r", encoding="utf-8") as f:
    quotes_data = json.load(f)
all_quotes = [(author, q) for author, quotes in quotes_data.items() for q in quotes]

# === ملفات تخزين بسيطة ===
SUBSCRIBERS_FILE = "subscribers.json"
SCORES_FILE = "scores.json"

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_subscribers(s):
    with open(SUBSCRIBERS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f)

def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_scores(s):
    with open(SCORES_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f)

subscribers = load_subscribers()
scores = load_scores()

def add_point(user_id, username):
    uid = str(user_id)
    if uid not in scores:
        scores[uid] = {"username": username, "points": 0}
    scores[uid]["points"] += 1
    save_scores(scores)

# === أوامر البوت ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 اللعبة", callback_data="game_start")],
        [InlineKeyboardButton("☀️ الاقتباس اليومي", callback_data="daily_toggle")]
    ]
    if update.message:
        await update.message.reply_text(
            "👋 مرحبا بك في بوت الحكمة واللعب!\nاختر أحد الخيارات أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "👋 مرحبا بك في بوت الحكمة واللعب!\nاختر أحد الخيارات أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def daily_on(uid):
    if uid not in subscribers:
        subscribers.append(uid)
        save_subscribers(subscribers)
        return "✅ تم الاشتراك في الاقتباس اليومي."
    else:
        return "أنت مشترك بالفعل."

async def daily_off(uid):
    if uid in subscribers:
        subscribers.remove(uid)
        save_subscribers(subscribers)
        return "❌ تم إلغاء الاشتراك."
    else:
        return "أنت لست مشتركاً."

async def send_daily(app):
    if not subscribers:
        return
    author, quote = random.choice(all_quotes)
    text = f"☀️ اقتباس اليوم:\n\n«{quote}»\n— {author}"
    for uid in subscribers:
        try:
            await app.bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            print("Send error:", e)

async def daily_scheduler(app):
    await asyncio.sleep(10)  # أول تنفيذ بعد 10 ثواني
    while True:
        await send_daily(app)
        await asyncio.sleep(24 * 60 * 60)  # كل 24 ساعة

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    author, quote = random.choice(all_quotes)
    wrong = list(quotes_data.keys())
    if author in wrong:
        wrong.remove(author)
    options = random.sample(wrong, min(3, len(wrong))) + [author]
    random.shuffle(options)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"game:{author}:{opt}")] for opt in options]

    # التعامل مع message أو callback_query
    if update.message:
        await update.message.reply_text(
            f"🎮 من قال هذا الاقتباس؟\n\n«{quote}»",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            f"🎮 من قال هذا الاقتباس؟\n\n«{quote}»",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def game_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, correct, chosen = q.data.split(":")
    uid = q.from_user.id
    username = q.from_user.username or q.from_user.first_name
    if correct == chosen:
        add_point(uid, username)
        await q.edit_message_text(f"✅ صحيح! {correct}\n+1 نقطة")
    else:
        await q.edit_message_text(f"❌ خطأ. الإجابة الصحيحة: {correct}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    if q.data == "game_start":
        await game(update, context)
    elif q.data == "daily_toggle":
        msg = await daily_on(uid) if uid not in subscribers else await daily_off(uid)
        await q.edit_message_text(msg)

# === التشغيل ===
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(game_start|daily_toggle|game:)"))

    # جدولة الاقتباسات اليومية
    asyncio.create_task(daily_scheduler(app))

    # تشغيل البوت بالـ polling لتجنب مشاكل Render مع Webhook
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # لحل مشاكل event loop
    import asyncio
    asyncio.run(main())
