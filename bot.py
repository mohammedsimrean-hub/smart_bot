import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading
import time

# --- الإعدادات ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- قاعدة البيانات المتقدمة ---
class OmegaSystem:
    def __init__(self):
        self.db_path = 'omega_v7.db'
        self.setup()

    def connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def setup(self):
        with self.connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
            conn.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prod_id INTEGER, status TEXT)")
            
            # بذر المنتجات
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            if cursor.fetchone()[0] == 0:
                conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("اشتراك دعم شهري", 30.0))
                conn.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("نظام أوميغا الكامل", 700.0))
            conn.commit()

omega = OmegaSystem()

# --- لوحات التحكم ---
def get_admin_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('📊 إحصائيات حية', '📦 إدارة الطلبات', '📢 إرسال تعميم')
    return kb

def get_user_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add('🛍️ تصفح المتجر', '📑 طلباتي الأخيرة', '📞 الدعم الفني')
    return kb

# --- معالجة الأوامر ---
@bot.message_handler(commands=['start'])
def welcome(message):
    uid = message.from_user.id
    with omega.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (uid, message.from_user.first_name))
        conn.commit()
    
    if uid == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 أوميغا V7.0 | وضع التحكم الكامل", reply_markup=get_admin_kb())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في أوميغا V7.0 🚀\nنظام مبيعاتك المؤتمت.", reply_markup=get_user_kb())

# --- معالجة الردود (مش منظر، فعل حقيقي) ---
@bot.message_handler(func=lambda m: True)
def main_router(message):
    uid = message.from_user.id
    text = message.text

    # منطق الأدمن
    if uid == ADMIN_ID:
        if text == '📊 إحصائيات حية':
            with omega.connect() as conn:
                u = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                o = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
            bot.reply_to(message, f"📈 **تقرير أوميغا:**\n\n👤 المستخدمين: {u}\n📦 الطلبات: {o}")
        
        elif text == '📦 إدارة الطلبات':
            with omega.connect() as conn:
                pending = conn.execute("SELECT id, user_id FROM orders WHERE status='معلق' LIMIT 5").fetchall()
            if not pending: 
                bot.reply_to(message, "لا يوجد طلبات بانتظار الدفع حالياً.")
            for order in pending:
                mk = types.InlineKeyboardMarkup()
                mk.add(types.InlineKeyboardButton(f"تأكيد دفع #{order[0]}", callback_data=f"done_{order[0]}"))
                bot.send_message(ADMIN_ID, f"طلب معلق #{order[0]} من العميل {order[1]}", reply_markup=mk)

    # منطق المستخدم
    if text == '🛍️ تصفح المتجر':
        with omega.connect() as conn:
            prods = conn.execute("SELECT * FROM products").fetchall()
        mk = types.InlineKeyboardMarkup()
        for p in prods:
            mk.add(types.InlineKeyboardButton(f"{p[1]} - {p[2]}$", callback_data=f"order_{p[0]}"))
        bot.send_message(message.chat.id, "قائمة الخدمات المتاحة:", reply_markup=mk)
    
    elif text.lower() in ['هاي', 'hi', 'هلا']:
        bot.reply_to(message, f"أهلاً {message.from_user.first_name}! كيف حالك اليوم؟")

# --- معالجة الـ Callbacks ---
@bot.callback_query_handler(func=lambda c: True)
def calls(c):
    if c.data.startswith('order_'):
        pid = c.data.split('_')[1]
        with omega.connect() as conn:
            oid = conn.execute("INSERT INTO orders (user_id, prod_id, status) VALUES (?, ?, ?)", (c.from_user.id, pid, 'معلق')).lastrowid
            conn.commit()
        bot.edit_message_text(f"✅ تم تسجيل طلبك رقم #{oid}.\nتواصل مع @[يوزرك] للدفع.", c.message.chat.id, c.message.message_id)
        bot.send_message(ADMIN_ID, f"🚨 طلب شراء جديد! رقم #{oid}")

    elif c.data.startswith('done_'):
        oid = c.data.split('_')[1]
        with omega.connect() as conn:
            conn.execute("UPDATE orders SET status='مكتمل' WHERE id=?", (oid,))
            conn.commit()
        bot.answer_callback_query(c.id, "تم التأكيد ✅")
        bot.edit_message_text(f"الطلب #{oid} تم تأكيده بنجاح!", c.message.chat.id, c.message.message_id)

# --- تشغيل السيرفر (بشكل يمنع الـ Conflict) ---
@app.route('/')
def home():
    return "Omega V7 is Live and Stable"

def start_polling():
    while True:
        try:
            bot.remove_webhook()
            print("Starting Bot Polling...")
            bot.infinity_polling(skip_pending_updates=True, timeout=20)
        except Exception as e:
            print(f"Error: {e}. Restarting in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=start_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
