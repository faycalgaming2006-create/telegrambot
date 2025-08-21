import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# =============================
# التوكن واسم الخدمة
# =============================
TOKEN = "8343481325:AAGk1Mro9_LgeSZoq4m_WnfGNfYzg6j8OeM"
SERVICE_NAME = "myquotesbot123"  # اسم الخدمة على Render

# =============================
# تحميل الاقتباسات
# =============================
with open("quotes.json", "r", encoding="utf-8") as f:
    quotes_data = json.load(f)

all_quotes = [(author, q) for author, quotes in quotes_data.items() for q in quotes]

# =============================
# تخزين المشتركين
# =============================
SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f)

subscribers = load_subscribers()

# =============================
# تخزين النقاط
# =============================
SCORES_FILE = "scores.json"

def load_scores():
    if os.path.exists(SCORES_FILE):
        with open(SCORES_FILE, "r") as f:
            return json.load(f)
    return {}

def save_scores(scores):
    with open(SCORES_FILE, "w") as f:
        json.dump(scores, f)

scores = load_scores()

def add_point(user_id, username):
    if str(user_id) not in scores:
        scores[str(user_id)] = {"username": username, "points": 0}
    scores[str(user_id)]["points"] += 1
    save_scores(scores)

# =============================
# أوامر أساسية
# =============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 مرحبًا بك في بوت الاقتباسات!\n\n"
        "📝 الأوامر:\n"
        "/daily_on - اشترك في اقتباس يومي\n"
        "/daily_off - أوقف الاشتراك\n"
        "/game - ابدأ لعبة 'من قال هذا الاقتباس؟'\n"
        "/score - اعرض نقاطك\n"
        "/leaderboard - اعرض أفضل 10 لاعبين\n"
    )

async def daily_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in subscribers:
        subscribers.append(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text("✅ تم تفعيل اقتباس يومي لك!")
    else:
        await update.message.reply_text("📌 أنت مشترك بالفعل في اقتباس يومي.")

async def daily_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers(subscribers)
        await update.message.reply_text("❌ تم إلغاء الاشتراك من اقتباس اليوم.")
    else:
        await update.message.reply_text("⚠️ لم تكن مشتركًا.")

# =============================
# إرسال اقتباس يومي
# =============================
async def send_daily(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers:
        return
    author, quote = random.choice(all_quotes)
    text = f"☀️ اقتباس اليوم:\n\n{quote}\n\n— {author}"
    for user_id in subscribers:
        try:
            await context.bot.send_message(chat_id=user_id, text=text)
        except Exception as e:
            print(f"خطأ عند الإرسال لـ {user_id}: {e}")

# =============================
# اللعبة
# =============================
async def game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    author, quote = random.choice(all_quotes)
    wrong_authors = list(quotes_data.keys())
    wrong_authors.remove(author)
    options = random.sample(wrong_authors, 3) + [author]
    random.shuffle(options)
    keyboard = [[InlineKeyboardButton(opt, callback_data=f"game:{author}:{opt}")] for opt in options]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎮 لعبة: من قال هذا الاقتباس؟\n\n"
        f"«{quote}»\n",
        reply_markup=reply_markup
    )

async def game_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, correct, chosen = query.data.split(":")
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    if correct == chosen:
        add_point(user_id, username)
        text = f"✅ صحيح! هذا اقتباس لـ *{correct}*.\n\n+1 نقطة 🎉"
    else:
        text = f"❌ خطأ. الإجابة الصحيحة: *{correct}*."
    await query.edit_message_text(text=text, parse_mode="Markdown")

# =============================
# عرض النقاط والترتيب
# =============================
async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in scores:
        points = scores[user_id]["points"]
        await update.message.reply_text(f"📊 نقاطك: {points}")
    else:
        await update.message.reply_text("⚠️ ليس لديك نقاط بعد، ابدأ بـ /game")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not scores:
        await update.message.reply_text("⚠️ لا يوجد لاعبون بعد.")
        return
    sorted_scores = sorted(scores.items(), key=lambda x: x[1]["points"], reverse=True)
    top10 = sorted_scores[:10]
    text = "🏆 أفضل 10 لاعبين:\n\n"
    for i, (uid, data) in enumerate(top10, start=1):
        text += f"{i}. {data['username']} — {data['points']} نقطة\n"
    await update.message.reply_text(text)

# =============================
# تشغيل البوت مع Webhook على Render
# =============================
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("daily_on", daily_on))
    app.add_handler(CommandHandler("daily_off", daily_off))
    app.add_handler(CommandHandler("game", game))
    app.add_handler(CallbackQueryHandler(game_answer, pattern="^game:"))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(CommandHandler("leaderboard", leaderboard))

    # جدولة الاقتباس اليومي
    app.job_queue.run_repeating(send_daily, interval=86400, first=10)  # كل 24 ساعة، أول تنفيذ بعد 10 ثواني للاختبار

    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = f"https://{SERVICE_NAME}.onrender.com/{TOKEN}"

    await app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 5000)),
    url_path=TOKEN,
    webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TOKEN}"
    )

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    import asyncio
    asyncio.get_event_loop().run_until_complete(main())

