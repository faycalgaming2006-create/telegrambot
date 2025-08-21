# bot.py — نسخة فنية وفلسفية للبوت
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
        [InlineKeyboardButton("🎮 إبدأ اللعبة", callback_data="start_game")],
        [InlineKeyboardButton("☀️ اقتباس اليومي", callback_data="daily_quote")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "🌿 *مرحباً بك في عالم الحكمة والألعاب!* 🌿\n\n"
        "في هذا البوت ستجد متعة التفكير، واختبار معرفتك بالحكمة.\n"
        "اضغط على الأزرار أدناه للبدء باللعبة أو لاستلام اقتباس ملهم اليوم.\n"
        "_تذكر: كل اقتباس يحمل درسًا، وكل لعبة رحلة نحو المعرفة._"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="Markdown")

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in subscribers:
        subscribers.append(uid)
        save_subscribers(subscribers)
        await update.message.reply_text("✅ تم الاشتراك! ستصلك حكمة يومية لتضيء يومك.")
    else:
        await update.message.reply_text("أنت مشترك بالفعل. الحكمة قادمة إليك كل يوم 🌟")

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in subscribers:
        subscribers.remove(uid)
        save_subscribers(subscribers)
        await update.message.reply_text("❌ تم إلغاء الاشتراك. سنفتقد حكمتك اليومية 😔")
    else:
        await update.message.reply_text("أنت لست مشتركاً. ابدأ الاشتراك لتستمتع بالحكمة اليومية 🌿")

async def send_daily(app):
    if not subscribers:
        return
    author, quote = random.choice(all_quotes)
    text = f"☀️ *حكمة اليوم*\n\n_{quote}_\n\n— *{author}*"
    for uid in subscribers:
        try:
            await app.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
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
    await update.message.reply_text(
        f"🎲 *من قال هذا الاقتباس؟*\n\n«{quote}»",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def game_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, correct, chosen = q.data.split(":")
    uid = q.from_user.id
    username = q.from_user.username or q.from_user.first_name
    if correct == chosen:
        add_point(uid, username)
        await q.edit_message_text(f"✅ رائع! الإجابة الصحيحة: *{correct}*\n+1 نقطة 🌟", parse_mode="Markdown")
    else:
        await q.edit_message_text(f"❌ للأسف خطأ. الإجابة الصحيحة: *{correct}*", parse_mode="Markdown")

# === التعامل مع أزرار الترحيب ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_game":
        await game(update, context)
    elif query.data == "daily_quote":
        await send_daily(context.application)

# === التشغيل مع Polling لتجنب مشاكل Render ===
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CallbackQueryHandler(game_answer, pattern="^game:"))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(start_game|daily_quote)$"))

    # بدء المجدول
    asyncio.create_task(daily_scheduler(app))

    # تشغيل polling
    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # حل مشاكل event loop على Render
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
