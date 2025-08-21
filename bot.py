# bot.py — جاهز للعمل على Render مع Webhook
import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === التوكن الخاص بك ===
BOT_TOKEN = "8343481325:AAGk1Mro9_LgeSZoq4m_WnfGNfYzg6j8OeM"

# === تحميل الاقتباسات ===
with open("quotes.json", "r", encoding="utf-8") as f:
    quotes_data = json.load(f)
all_quotes = [(author, q) for author, quotes in quotes_data.items() for q in quotes]

# === ملفات التخزين ===
SUBSCRIBERS_FILE = "subscribers.json"
SCORES_FILE = "scores.json"

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
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
    text = "🌟 أهلاً بك في بوت الحكمة والفلسفة!\n\nاكتشف اقتباسات يومية وألعاب ذهنية.\n\nللبدء، استخدم /daily_on للاشتراك بالاقتباس اليومي، و /game للعبة المعرفة."
    keyboard = [[InlineKeyboardButton("🎮 العب الآن", callback_data="start_game")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in subscribers:
        subscribers.append(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        await update.message.reply_text("✅ تم الاشتراك في الاقتباس اليومي. استمتع بالحكمة!")
    else:
        await update.message.reply_text("⚠️ أنت مشترك بالفعل.")

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in subscribers:
        subscribers.remove(uid)
        save_json(SUBSCRIBERS_FILE, subscribers)
        await update.message.reply_text("❌ تم إلغاء الاشتراك.")
    else:
        await update.message.reply_text("⚠️ لم تكن مشتركًا من قبل.")

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
    await asyncio.sleep(10)
    while True:
        await send_daily(app)
        await asyncio.sleep(24 * 60 * 60)

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    author, quote = random.choice(all_quotes)
    wrong = list(quotes_data.keys())
    if author in wrong:
        wrong.remove(author)
    options = random.sample(wrong, min(3, len(wrong))) + [author]
    random.shuffle(options)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"game:{author}:{opt}")] for opt in options]
    await update.message.reply_text(f"🎲 من قال هذا الاقتباس؟\n\n«{quote}»", reply_markup=InlineKeyboardMarkup(keyboard))

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

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CallbackQueryHandler(game_answer, pattern="^game:"))
    app.add_handler(CallbackQueryHandler(lambda u, c: asyncio.create_task(game(u,c)), pattern="start_game"))

    # مجدول الاقتباسات اليومية
    asyncio.create_task(daily_scheduler(app))

    # إعداد Webhook لـ Render
    PORT = int(os.environ.get("PORT", "5000"))
    HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
    if not HOST:
        print("تشغيل محلي (Polling)")
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
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
