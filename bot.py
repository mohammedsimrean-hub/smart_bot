from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os

TOKEN = "8641628383:AAHLmCry4lLS2MicMqfP5gC5QslyG1xWrPk"
DATA_FILE = "database.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك\nارسل طلبك أو رسالتك وسيتم تسجيلها"
    )

async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"📊 عدد الطلبات: {len(data)}")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user = update.effective_user

    data.append({
        "user_id": user.id,
        "name": user.first_name,
        "message": msg
    })

    save_data(data)

    await update.message.reply_text("✅ تم تسجيل طلبك")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("show", show))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("Bot is running...")
app.run_polling()
