# bot.py
import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import nest_asyncio

nest_asyncio.apply()

# ======= التوكن =======
BOT_TOKEN = "8343481325:AAGk1Mro9_LgeSZoq4m_WnfGNfYzg6j8OeM"

# ======= ملفات التخزين =======
SUBSCRIBERS_FILE = "subscribers.json"
SCORES_FILE = "scores.json"
QUOTES_FILE = "quotes.json"

# ======= تحميل الاقتباسات =======
with open(QUOTES_FILE, "r", encoding="utf-8") as f:
    quotes_data = json.load(f)
all_quotes = [(author, q) for author, quotes in quotes_data.items() for q in quotes]

# ======= وظائف التخزين =======
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f)

subscribers = load_json(SUBSCRIBERS_FILE).get("subs", [])
scores = load_json(SCORES_FILE)

def add_point(user_id, username):
    uid = str(user_id)
    if uid not in scores:
        scores[uid] = {"username": username, "points": 0}
    scores[uid]["points"] += 1
    save_json(SCORES_FILE, scores)

# ======= أوامر البوت =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎮 لعبة الاقتباسات", callback_data="game")],
        [InlineKeyboardButton("☀️ تفعيل الاقتباس اليومي", callback_data="daily_on"),
         InlineKeyboardButton("❌ إيقاف الاقتباس اليومي", callback_data="daily_off")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(
            "👋 مرحباً بك في بوت الحكمة واللعبة!\nاختر خيارك من الأزرار أدناه.",
            reply_markup=markup
        )

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in subscribers:
        subscribers.append(uid)
        save_json(SUBSCRIBERS_FILE, {"subs": subscribers})
        await update.callback_query.answer("✅ تم الاشتراك في الاقتباس اليومي.")
    else:
        await update.callback_query.answer("أنت مشترك بالفعل.")

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in subscribers:
        subscribers.remove(uid)
        save_json(SUBSCRIBERS_FILE, {"subs": subscribers})
        await update.callback_query.answer("❌ تم إلغاء الاشتراك.")
    else:
        await update.callback_query.answer("أنت لست مشتركاً.")

async def send_daily(app):
    if not subscribers:
        return
    author, quote = random.choice(all_quotes)
    text = f"☀️ اقتباس اليوم:\n\n«{quote}»\n— {author}"
    for uid in subscribers:
        try:
            await app.bot.send_message(chat_id=uid, text=text)
        except:
            pass

async def daily_scheduler(app):
    await asyncio.sleep(10)  # تأخير أولي
    while True:
        await send_daily(app)
        await asyncio.sleep(24*60*60)  # كل 24 ساعة

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    author, quote = random.choice(all_quotes)
    wrong = list(quotes_data.keys())
    if author in wrong:
        wrong.remove(author)
    options = random.sample(wrong, min(3, len(wrong))) + [author]
    random.shuffle(options)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"answer:{author}:{opt}")] for opt in options]

    if update.message:
        await update.message.reply_text(f"🎮 من قال هذا الاقتباس؟\n\n«{quote}»", reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.edit_message_text(f"🎮 من قال هذا الاقتباس؟\n\n«{quote}»", reply_markup=InlineKeyboardMarkup(keyboard))

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"حدث خطأ: {context.error}")

# ======= Main =======
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(game, pattern="^game$"))
    app.add_handler(CallbackQueryHandler(daily_on, pattern="^daily_on$"))
    app.add_handler(CallbackQueryHandler(daily_off, pattern="^daily_off$"))
    app.add_handler(CallbackQueryHandler(answer, pattern="^answer:"))
    app.add_error_handler(error_handler)

    # Scheduler
    asyncio.create_task(daily_scheduler(app))

    # Webhook للـ Render
    PORT = int(os.environ.get("PORT", "5000"))
    HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME", None)

    if not HOST:
        print("تشغيل polling محلي (للتطوير فقط)")
        await app.run_polling()
        return

    WEBHOOK_URL = f"https://{HOST}/{BOT_TOKEN}"
    await app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    asyncio.run(main())
