# bot.py — نسخة جاهزة للعمل على Render Worker
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

# === ملفات تخزين بسيطة ===
SUBSCRIBERS_FILE = "subscribers.json"
SCORES_FILE = "scores.json"

def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

subscribers = load_json(SUBSCRIBERS_FILE, [])
scores = load_json(SCORES_FILE, {})

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 أهلاً بك في بوت الاقتباسات الحكيمة والفلسفية!\nاختر أحد الخيارات بالأسفل:",
        reply_markup=reply_markup
    )

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in subscribers:
        subscribers.append(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        await update.message.reply_text("✅ تم الاشتراك في الاقتباس اليومي. ستصلك اقتباسات حكيمة كل يوم!")
    else:
        await update.message.reply_text("أنت مشترك بالفعل بالاقتباس اليومي.")

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in subscribers:
        subscribers.remove(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        await update.message.reply_text("❌ تم إلغاء الاشتراك بالاقتباس اليومي.")
    else:
        await update.message.reply_text("أنت لست مشتركاً.")

async def send_daily(app):
    if not subscribers:
        return
    author, quote = random.choice(all_quotes)
    text = f"☀️ اقتباس اليوم:\n\n«{quote}»\n\n— {author}"
    for uid in subscribers:
        try:
            await app.bot.send_message(chat_id=uid, text=text)
        except Exception as e:
            print("Send error:", e)

async def daily_scheduler(app):
    await asyncio.sleep(10)  # أول إرسال بعد 10 ثواني
    while True:
        await send_daily(app)
        await asyncio.sleep(24 * 60 * 60)  # كل 24 ساعة

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # تأكد من وجود message
    if update.message is None:
        return
    author, quote = random.choice(all_quotes)
    wrong = list(quotes_data.keys())
    if author in wrong:
        wrong.remove(author)
    options = random.sample(wrong, min(3, len(wrong))) + [author]
    random.shuffle(options)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"game:{author}:{opt}")] for opt in options]
    await update.message.reply_text(f"🎮 لعبة الاقتباس:\n\n«{quote}»\nمن قال هذا؟", reply_markup=InlineKeyboardMarkup(keyboard))

async def game_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data.startswith("game:"):
        _, correct, chosen = q.data.split(":")
        uid = q.from_user.id
        username = q.from_user.username or q.from_user.first_name
        if correct == chosen:
            add_point(uid, username)
            await q.edit_message_text(f"✅ صحيح! {correct}\n+1 نقطة")
        else:
            await q.edit_message_text(f"❌ خطأ. الإجابة الصحيحة: {correct}")

# === تشغيل البوت ===
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CallbackQueryHandler(game_answer, pattern="^game:"))

    # ابدأ المجدول كـ background task
    asyncio.create_task(daily_scheduler(app))

    # تشغيل البوت على Polling
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # لتجنب مشاكل event loop على Render
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
