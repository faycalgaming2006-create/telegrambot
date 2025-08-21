# bot.py — نسخة جاهزة للعمل على Render
import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === توكن البوت ===
BOT_TOKEN = "8343481325:AAGk1Mro9_LgeSZoq4m_WnfGNfYzg6j8OeM"

# === تحميل الاقتباسات ===
with open("quotes.json", "r", encoding="utf-8") as f:
    quotes_data = json.load(f)
all_quotes = [(author, q) for author, quotes in quotes_data.items() for q in quotes]

# === ملفات التخزين ===
SUBSCRIBERS_FILE = "subscribers.json"
SCORES_FILE = "scores.json"

def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return [] if file in [SUBSCRIBERS_FILE] else {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)

subscribers = load_json(SUBSCRIBERS_FILE)
scores = load_json(SCORES_FILE)

def add_point(user_id, username):
    uid = str(user_id)
    if uid not in scores:
        scores[uid] = {"username": username, "points": 0}
    scores[uid]["points"] += 1
    save_json(SCORES_FILE, scores)

# === أوامر البوت ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 لعبة الاقتباس", callback_data="game")],
        [InlineKeyboardButton("☀️ الاشتراك بالاقتباس اليومي", callback_data="daily_on")]
    ]
    await update.message.reply_text(
        "👋 مرحبًا بك! استمتع بالحكمة واللعب.\nاختر أحد الخيارات أدناه:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # استخدم callback_query إذا جاء من زر
    q = update.callback_query
    if q:
        await q.answer()
        user_id = q.from_user.id
    else:
        user_id = update.effective_user.id

    author, quote = random.choice(all_quotes)
    wrong = list(quotes_data.keys())
    if author in wrong:
        wrong.remove(author)
    options = random.sample(wrong, min(3, len(wrong))) + [author]
    random.shuffle(options)

    keyboard = [[InlineKeyboardButton(opt, callback_data=f"game:{author}:{opt}")] for opt in options]

    text = f"🎮 من قال هذا الاقتباس؟\n\n«{quote}»"
    if q:
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id if q else update.effective_user.id
    if uid not in subscribers:
        subscribers.append(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        msg = "✅ تم الاشتراك في الاقتباس اليومي."
    else:
        msg = "أنت مشترك بالفعل."
    if q:
        await q.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = q.from_user.id if q else update.effective_user.id
    if uid in subscribers:
        subscribers.remove(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        msg = "❌ تم إلغاء الاشتراك."
    else:
        msg = "أنت لست مشتركاً."
    if q:
        await q.edit_message_text(msg)
    else:
        await update.message.reply_text(msg)

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
    await asyncio.sleep(10)
    while True:
        await send_daily(app)
        await asyncio.sleep(24*60*60)

# === main ===
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(game_answer, pattern="^game:"))
    app.add_handler(CallbackQueryHandler(game, pattern="^game$"))
    app.add_handler(CallbackQueryHandler(daily_on, pattern="^daily_on$"))
    app.add_handler(CallbackQueryHandler(daily_off, pattern="^daily_off$"))

    # scheduler
    asyncio.create_task(daily_scheduler(app))

    # تشغيل البوت باستخدام polling (لتجنب مشاكل Webhook و Render)
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
