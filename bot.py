import os import time import asyncio import logging import hashlib from logging.handlers import RotatingFileHandler from datetime import datetime from functools import wraps

import telebot import psycopg2 import redis from flask import Flask from playwright.async_api import async_playwright

======================================================

OMEGA ENTERPRISE - RENDER READY VERSION

======================================================

Required ENV Variables on Render:

BOT_TOKEN

ADMIN_ID

DATABASE_URL

REDIS_URL

======================================================

===================== LOGGING ========================

log_handler = RotatingFileHandler( "omega.log", maxBytes=5 * 1024 * 1024, backupCount=2 )

logging.basicConfig( level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", handlers=[log_handler, logging.StreamHandler()] )

logger = logging.getLogger("OmegaSystem")

===================== CONFIG =========================

BOT_TOKEN = os.getenv("BOT_TOKEN") ADMIN_ID = int(os.getenv("ADMIN_ID", "0")) DATABASE_URL = os.getenv("DATABASE_URL") REDIS_URL = os.getenv("REDIS_URL")

if not BOT_TOKEN: raise Exception("BOT_TOKEN missing")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")

===================== FLASK ==========================

app = Flask(name)

@app.route('/') def home(): return 'Omega SaaS System Running'

===================== REDIS ==========================

redis_client = redis.from_url(REDIS_URL, decode_responses=True)

===================== DATABASE =======================

class Database: def init(self): self.init_db()

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
            CREATE TABLE IF NOT EXISTS listings (
                id SERIAL PRIMARY KEY,
                external_id TEXT UNIQUE,
                title TEXT,
                price NUMERIC,
                url TEXT,
                score INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
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

    logger.info("Database initialized")

db = Database()

===================== HELPERS ========================

def safe_execute(func): @wraps(func) def wrapper(*args, **kwargs): for attempt in range(3): try: return func(*args, **kwargs) except Exception as e: logger.error(f"{func.name} failed: {e}") time.sleep(1) return None return wrapper

def rate_limit(seconds=2): def decorator(func): @wraps(func) def wrapper(message, *args, **kwargs): uid = message.from_user.id key = f"rate:{uid}"

last = redis_client.get(key)
        now = time.time()

        if last and now - float(last) < seconds:
            return

        redis_client.set(key, now, ex=seconds)
        return func(message, *args, **kwargs)
    return wrapper
return decorator

def register_user(user): with db.connect() as conn: with conn.cursor() as cur: cur.execute( ''' INSERT INTO users (id, username) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING ''', (user.id, user.username) ) conn.commit()

def has_active_subscription(uid): with db.connect() as conn: with conn.cursor() as cur: cur.execute( "SELECT subscription_type, expire_ts FROM users WHERE id=%s", (uid,) ) user = cur.fetchone()

if not user:
    return False

sub_type, expire_ts = user

return sub_type != 'FREE' and expire_ts > int(time.time())

===================== MENUS ==========================

def main_menu(): markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True) markup.add('🚗 السيارات', '📊 الإحصائيات') markup.add('💳 الاشتراك', '🛡️ الدعم') return markup

===================== START ==========================

@bot.message_handler(commands=['start']) @rate_limit(1) @safe_execute def start(message): register_user(message.from_user)

bot.send_message(
    message.chat.id,
    "🚀 مرحباً بك في Omega Intelligence Platform",
    reply_markup=main_menu()
)

===================== SUBSCRIPTION ===================

@bot.message_handler(func=lambda m: m.text == '💳 الاشتراك') @rate_limit(1) @safe_execute def subscribe(message): markup = telebot.types.InlineKeyboardMarkup()

markup.add(
    telebot.types.InlineKeyboardButton(
        "اشتراك شهري - 30$",
        callback_data="buy_monthly_30"
    )
)

markup.add(
    telebot.types.InlineKeyboardButton(
        "اشتراك سنوي - 299$",
        callback_data="buy_yearly_299"
    )
)

bot.send_message(
    message.chat.id,
    "💎 اختر الباقة المناسبة:",
    reply_markup=markup
)

===================== BUY ============================

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_')) @safe_execute def buy_callback(c): uid = c.from_user.id

plan_data = c.data.split('_')
plan = plan_data[1]
price = plan_data[2]

text = f'''

💳 إتمام الاشتراك

الخطة: {plan} السعر: ${price}

📱 زين كاش: 0782237627

🌍 Binance USDT: YOUR_WALLET

📸 أرسل صورة التحويل وسيتم التفعيل. '''

redis_client.set(f"waiting:{uid}", f"{plan}:{price}", ex=3600)

bot.send_message(c.message.chat.id, text)

===================== RECEIPT ========================

@bot.message_handler(content_types=['photo']) @safe_execute def receipt_handler(message): uid = message.from_user.id

data = redis_client.get(f"waiting:{uid}")

if not data:
    return

photo_id = message.photo[-1].file_id

markup = telebot.types.InlineKeyboardMarkup()

markup.add(
    telebot.types.InlineKeyboardButton(
        "✅ تفعيل",
        callback_data=f"adm_ok_{uid}_{data}"
    )
)

bot.send_photo(
    ADMIN_ID,
    photo_id,
    caption=f"طلب جديد من {uid}\nالخطة: {data}",
    reply_markup=markup
)

bot.reply_to(message, "⏳ تم إرسال الطلب للمراجعة")

===================== ADMIN ==========================

@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_ok_')) @safe_execute def activate_user(c): if c.from_user.id != ADMIN_ID: return

_, _, uid, plan, price = c.data.split('_')

uid = int(uid)
price = float(price)

days = 365 if plan == 'yearly' else 30

expire_ts = int(time.time()) + (days * 86400)

with db.connect() as conn:
    with conn.cursor() as cur:
        cur.execute(
            '''
            UPDATE users
            SET subscription_type=%s,
                expire_ts=%s,
                total_spent=total_spent + %s
            WHERE id=%s
            ''',
            (plan, expire_ts, price, uid)
        )

        cur.execute(
            '''
            INSERT INTO transactions (user_id, amount, plan)
            VALUES (%s, %s, %s)
            ''',
            (uid, price, plan)
        )

        conn.commit()

bot.send_message(uid, "✅ تم تفعيل اشتراكك بنجاح")
bot.answer_callback_query(c.id, "تم التفعيل")

logger.info(f"Activated {uid} plan={plan}")

===================== METRICS ========================

@bot.message_handler(commands=['admin']) @safe_execute def admin_panel(message): if message.from_user.id != ADMIN_ID: return

with db.connect() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]

        cur.execute(
            "SELECT COUNT(*) FROM users WHERE expire_ts > %s",
            (int(time.time()),)
        )
        active = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(total_spent), 0) FROM users")
        revenue = cur.fetchone()[0]

report = f'''

📊 OMEGA METRICS

👥 Users: {total_users} 💎 Active Subs: {active} 💰 Revenue: ${revenue} '''

bot.send_message(message.chat.id, report)

===================== PROTECTED FEATURE ==============

@bot.message_handler(func=lambda m: m.text == '🚗 السيارات') @rate_limit(1) @safe_execute def cars_feature(message): if not has_active_subscription(message.from_user.id): bot.reply_to(message, "⚠️ هذا القسم للمشتركين فقط") return

bot.reply_to(message, "🔍 جاري جلب أحدث اللقطات...")

===================== SCRAPER ========================

class CarScraper: def init(self): self.base_url = "https://haraj.com.sa/tags/سيارات"

self.market_averages = {
        "كامري": 115000,
        "إلنترا": 75000,
        "سوناتا": 95000,
    }

async def get_listings(self):
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0"
        })

        try:
            logger.info("Scanning Haraj...")

            await page.goto(self.base_url, timeout=60000)

            await page.wait_for_selector('[data-testid="post-item"]')

            posts = await page.query_selector_all('[data-testid="post-item"]')

            for post in posts[:20]:
                title_el = await post.query_selector('h3')
                price_el = await post.query_selector('[data-testid="post-price"]')
                link_el = await post.query_selector('a')

                title = await title_el.inner_text() if title_el else 'Unknown'
                price_text = await price_el.inner_text() if price_el else '0'
                link = await link_el.get_attribute('href') if link_el else ''

                digits = ''.join(filter(str.isdigit, price_text))
                price = int(digits) if digits else 0

                score = 0

                for model, avg in self.market_averages.items():
                    if model in title:
                        ratio = price / avg if avg else 1

                        if ratio <= 0.80:
                            score += 80
                        elif ratio <= 0.90:
                            score += 60
                        elif ratio <= 0.95:
                            score += 40

                full_link = f"https://haraj.com.sa{link}"

                fingerprint = hashlib.md5(full_link.encode()).hexdigest()

                if redis_client.get(f"seen:{fingerprint}"):
                    continue

                redis_client.set(f"seen:{fingerprint}", 1, ex=86400)

                results.append({
                    'title': title,
                    'price': price,
                    'link': full_link,
                    'score': score
                })

        except Exception as e:
            logger.error(f"Scraping error: {e}")

        await browser.close()

    return results

===================== ENGINE =========================

async def market_engine(): scraper = CarScraper()

while True:
    try:
        logger.info("Starting scan cycle")

        listings = await scraper.get_listings()

        for item in listings:
            if item['score'] >= 60:
                text = f'''

🚨 فرصة جديدة

🚗 {item['title']} 💰 {item['price']} ريال 🔥 Score: {item['score']}/100

🔗 {item['link']} '''

bot.send_message(ADMIN_ID, text)

        await asyncio.sleep(600)

    except Exception as e:
        logger.error(f"Engine failed: {e}")
        await asyncio.sleep(30)

===================== THREADS ========================

def start_async_engine(): loop = asyncio.new_event_loop() asyncio.set_event_loop(loop) loop.run_until_complete(market_engine())

===================== START SYSTEM ===================

if name == 'main': import threading

logger.info("Omega Enterprise Starting...")

threading.Thread(target=start_async_engine, daemon=True).start()

bot.infinity_polling(timeout=10, long_polling_timeout=5)
