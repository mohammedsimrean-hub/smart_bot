import os, time, asyncio, logging, hashlib, threading, telebot, psycopg2, redis
from logging.handlers import RotatingFileHandler
from datetime import datetime
from functools import wraps
from flask import Flask
from playwright.async_api import async_playwright

# --- CONFIG ---
BOT_TOKEN = "8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64"
ADMIN_ID = 8212079374
ZAIN_CASH = "0782237627"
CRYPTO_WALLET = "YOUR_USDT_TRC20_ADDRESS"
DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# --- DATABASE ---
class Database:
    def connect(self): return psycopg2.connect(DATABASE_URL)
    def init_db(self):
        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id BIGINT PRIMARY KEY, 
                        username TEXT, 
                        sub_type TEXT DEFAULT 'FREE', 
                        expire_ts BIGINT DEFAULT 0,
                        total_spent NUMERIC DEFAULT 0
                    )""")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_prefs (
                        user_id BIGINT PRIMARY KEY,
                        fav_model TEXT,
                        max_price NUMERIC DEFAULT 1000000,
                        is_active BOOLEAN DEFAULT TRUE
                    )""")
                conn.commit()
db = Database()

# --- SECURITY & CHECKING ---
def has_active_sub(uid):
    """التحقق المنطقي الكامل من الاشتراك (الحل للمشكلة المنطقية)"""
    try:
        with db.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT sub_type, expire_ts FROM users WHERE id=%s", (uid,))
                res = cur.fetchone()
                # التحقق: السجل موجود + ليس FREE + الوقت لم ينتهِ
                return res and res[0] != 'FREE' and res[1] > int(time.time())
    except Exception as e:
        return False

# --- DATA ENGINE (SCRAPER V5.1) ---
async def fetch_market_data():
    market_url = "https://haraj.com.sa/tags/سيارات"
    market_avgs = {"كامري": 115000, "إلنترا": 75000, "سوناتا": 90000}
    results = []

    async with async_playwright() as p:
        # حل Memory Leak بفتح وإغلاق المتصفح في كل دورة
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(market_url, timeout=60000)
            await page.wait_for_selector('[data-testid="post-item"]', timeout=15000)
            posts = await page.query_selector_all('[data-testid="post-item"]')

            for post in posts[:15]:
                try:
                    # تحسين Error Handling لمنع الـ Crash في حال غياب أي عنصر
                    title_el = await post.query_selector('h3')
                    price_el = await post.query_selector('[data-testid="post-price"]')
                    link_el = await post.query_selector('a')
                    
                    if not title_el or not price_el or not link_el: continue
                    
                    title = await title_el.inner_text()
                    price_t = await price_el.inner_text()
                    link = await link_el.get_attribute('href')
                    
                    price = int(''.join(filter(str.isdigit, price_t)))
                    fid = hashlib.md5(link.encode()).hexdigest()
                    
                    if not redis_client.get(f"seen:{fid}"):
                        redis_client.set(f"seen:{fid}", 1, ex=86400)
                        
                        score = 0
                        model_hit = None
                        for model, avg in market_avgs.items():
                            if model in title:
                                model_hit = model
                                ratio = price / avg
                                if ratio <= 0.85: score = 95
                                elif ratio <= 0.95: score = 65
                        
                        results.append({
                            "title": title, "price": price, 
                            "link": f"https://haraj.com.sa{link}", 
                            "score": score, "model": model_hit
                        })
                except: continue
        finally:
            await browser.close()
    return results

async def dispatcher_loop():
    while True:
        try:
            listings = await fetch_market_data()
            for item in listings:
                # 1. إرسال للأدمن (للرقابة الشاملة)
                if item['score'] >= 65:
                    bot.send_message(ADMIN_ID, f"📢 **فرصة ذكية ({item['score']}/100)**\n🚗 {item['title']}\n💰 {item['price']}\n🔗 {item['link']}")

                # 2. إرسال للمستخدمين (التحقق من الفلتر والاشتراك)
                if item['model']:
                    with db.connect() as conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                SELECT p.user_id, p.max_price FROM user_prefs p 
                                JOIN users u ON p.user_id = u.id 
                                WHERE p.fav_model = %s AND u.sub_type != 'FREE' 
                                AND u.expire_ts > %s AND p.is_active = TRUE
                            """, (item['model'], int(time.time())))
                            
                            for uid, max_p in cur.fetchall():
                                if item['price'] <= max_p:
                                    bot.send_message(uid, f"🌟 **لقطة تطابق طلبك!**\n🚗 {item['title']}\n💰 {item['price']}\n🔗 {item['link']}")
            await asyncio.sleep(600)
        except: await asyncio.sleep(60)

# --- START SYSTEM ---
if __name__ == "__main__":
    db.init_db()
    threading.Thread(target=lambda: asyncio.run(dispatcher_loop()), daemon=True).start()
    bot.infinity_polling()
