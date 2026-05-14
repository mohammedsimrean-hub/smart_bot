import os
import time
import asyncio
import logging
import hashlib
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps

import telebot
import psycopg2
import redis
from flask import Flask
from playwright.async_api import async_playwright

# ===================== LOGGING ========================
log_handler = RotatingFileHandler("omega.log", maxBytes=5 * 1024 * 1024, backupCount=2)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[log_handler, logging.StreamHandler()]
)
logger = logging.getLogger("OmegaSystem")

# ===================== CONFIG (YOUR DATA) =============
# بياناتك الخاصة التي طلبت إضافتها
BOT_TOKEN = "8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64"
ADMIN_ID = 8212079374
ZAIN_CASH = "0782237627"
CRYPTO_WALLET = "TYvU7hY8pS6k9... (ضع عنوان محفظتك الكامل هنا)" # تأكد من وضع عنوان USDT الخاص بك

# روابط قواعد البيانات من Render (يفضل وضعها في ENV)
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

# ===================== DATABASE =======================
class Database:
    def connect(self):
        return psycopg2.connect(DATABASE_URL)

    def init_db(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY,
                        username TEXT,
                        subscription_type TEXT DEFAULT 'FREE',
                        expire_ts BIGINT DEFAULT 0,
                        total_spent NUMERIC DEFAULT 0,
                        join_date TIMESTAMP DEFAULT NOW()
                    )
                ''')
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS transactions (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        amount NUMERIC,
                        plan TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                conn.commit()
        logger.info("Database initialized successfully")

db = Database()

# ===================== HELPERS & SECURITY =============
def safe_execute(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        for _ in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                time.sleep(1)
        return None
    return wrapper

def register_user(user):
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
                (user.id, user.username)
            )
            conn.commit()

# ===================== MENUS ==========================
def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('🚗 السيارات', '📊 الإحصائيات')
    markup.add('💳 الاشتراك', '🛡️ الدعم')
    return markup

# ===================== HANDLERS =======================
@bot.message_handler(commands=['start'])
@safe_execute
def start(message):
    register_user(message.from_user)
    bot.send_message(
        message.chat.id, 
        "🚀 **أهلاً بك في منصة أوميغا للاستخبارات التجارية**\n\nنظامك جاهز لرصد الفرص في الأردن والخليج.", 
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == '💳 الاشتراك')
@safe_execute
def subscribe(message):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🗓️ شهري - 30$", callback_data="buy_monthly_30"))
    markup.add(telebot.types.InlineKeyboardButton("🏆 سنوي - 299$", callback_data="buy_yearly_299"))
    bot.send_message(message.chat.id, "💎 **اختر خطة الاشتراك المناسبة لك:**", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def buy_callback(c):
    _, plan, price = c.data.split('_')
    text = f"""
💳 **تفاصيل إتمام الدفع**

🔹 الخطة: `{plan}`
💰 المبلغ: `${price}`

📍 **داخل الأردن (Zain Cash):**
`{ZAIN_CASH}`

🌍 **دولي (USDT TRC20):**
`{CRYPTO_WALLET}`

📸 **يرجى إرسال صورة (Screenshot) للوصل هنا للتفعيل.**
    """
    bot.send_message(c.message.chat.id, text)

# ===================== ADMIN METRICS ==================
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    with db.connect() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            total = cur.fetchone()[0]
            cur.execute("SELECT COALESCE(SUM(total_spent), 0) FROM users")
            rev = cur.fetchone()[0]
    
    report = f"📊 **تقرير الإدارة**\n\n👥 الأعضاء: {total}\n💰 الأرباح: ${rev}"
    bot.send_message(message.chat.id, report)

# ===================== SYSTEM START ===================
if __name__ == '__main__':
    import threading
    from flask import Flask
    
    # تشغيل Flask لـ Render Health Check
    server = Flask(__name__)
    @server.route('/')
    def index(): return "Omega Online"
    
    threading.Thread(target=lambda: server.run(host='0.0.0.0', port=os.getenv('PORT', 5000))).start()
    
    logger.info("Omega System is LIVE...")
    db.init_db()
    bot.infinity_polling()
