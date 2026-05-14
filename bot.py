import telebot
from telebot import types
import sqlite3
import os
import logging
from flask import Flask
import threading
import time
import json

# --- 1. التكوين والأمن ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Omega_V124")

API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN, parse_mode='Markdown')
app = Flask(__name__)

# --- 2. المحرك السيادي (Core Engine) ---
class OmegaCore:
    def __init__(self):
        self.db_path = 'omega_v124_enterprise.db'
        self.migrate()

    def connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def migrate(self):
        with self.connect() as conn:
            # المستخدمين: إضافة حقل المحفظة والحظر
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT, state TEXT, 
                temp_data TEXT, balance REAL DEFAULT 0.0, is_banned INTEGER DEFAULT 0
            )""")
            # المنتجات: إضافة المخزون والوصف التفصيلي
            conn.execute("""CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, 
                price REAL, stock INTEGER DEFAULT 0, description TEXT
            )""")
            # الطلبات: إضافة حقل صورة الدفع
            conn.execute("""CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, 
                product_id INTEGER, status TEXT, receipt_photo TEXT, 
                details TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            conn.commit()

db = OmegaCore()

# --- 3. أدوات الواجهة (High-End Interfaces) ---
def main_menu(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if uid == ADMIN_ID:
        markup.add('🏢 غرفة القيادة', '📦 إدارة المخزون', '🔔 الطلبات الواردة')
    else:
        markup.add('🛍️ المتجر السيادي', '📜 سجل مشترياتي', '🛡️ الدعم الفني')
    return markup

# --- 4. منطق العمليات (Operations Logic) ---
@bot.message_handler(commands=['start'])
def boot_v124(message):
    uid = message.from_user.id
    with db.connect() as conn:
        user = conn.execute("SELECT is_banned FROM users WHERE id=?", (uid,)).fetchone()
        if user and user[0] == 1: return # تجاهل المحظورين
        conn.execute("INSERT OR IGNORE INTO users (id, name, state) VALUES (?, ?, 'IDLE')", (uid, message.from_user.first_name))
        conn.execute("UPDATE users SET state='IDLE' WHERE id=?", (uid,))
        conn.commit()
    
    bot.send_message(message.chat.id, "🔱 **نظام أوميغا V.124 مفعل.**\nأهلاً بك في بيئة الأعمال الأكثر أماناً.", reply_markup=main_menu(uid))

# --- 5. نظام الـ Checkout المتقدم (الدفع بالصور) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def start_checkout(c):
    pid = c.data.split('_')[1]
    uid = c.from_user.id
    with db.connect() as conn:
        conn.execute("UPDATE users SET state='WAIT_PAYMENT_PHOTO', temp_data=? WHERE id=?", (pid, uid))
        conn.commit()
    bot.edit_message_text("💳 **إتمام العملية:**\nيرجى تحويل المبلغ ثم إرسال **صورة (Screenshot)** لوصل التحويل هنا لتوثيق الطلب.", c.message.chat.id, c.message.message_id)

@bot.message_handler(content_types=['photo'])
def handle_payment_photo(message):
    uid = message.from_user.id
    with db.connect() as conn:
        user = conn.execute("SELECT state, temp_data FROM users WHERE id=?", (uid,)).fetchone()
    
    if user and user[0] == 'WAIT_PAYMENT_PHOTO':
        photo_id = message.photo[-1].file_id
        pid = user[1]
        with db.connect() as conn:
            oid = conn.execute("INSERT INTO orders (user_id, product_id, status, receipt_photo) VALUES (?, ?, ?, ?)", 
                               (uid, pid, 'بانتظار مراجعة الإدارة', photo_id)).lastrowid
            conn.execute("UPDATE users SET state='IDLE', temp_data=NULL WHERE id=?", (uid,))
            conn.commit()
        
        bot.reply_to(message, f"✅ **تم استلام الوصل بنجاح.**\nرقم طلبك هو `#{oid}`. سيتم تفعيله بعد مراجعة الإدارة.")
        bot.send_photo(ADMIN_ID, photo_id, caption=f"🚨 **طلب جديد رقم #{oid}**\nيرجى مراجعة الدفع.")

# --- 6. الإدارة الديناميكية (Dynamic Admin) ---
@bot.message_handler(func=lambda m: m.text == '📦 إدارة المخزون' and m.from_user.id == ADMIN_ID)
def inventory_manager(message):
    with db.connect() as conn:
        prods = conn.execute("SELECT id, name, stock FROM products").fetchall()
    if not prods: return bot.reply_to(message, "لا يوجد منتجات حالياً.")
    
    for p in prods:
        mk = types.InlineKeyboardMarkup()
        mk.add(types.InlineKeyboardButton("➕ زيادة", callback_data=f"stock_add_{p[0]}"),
               types.InlineKeyboardButton("➖ تقليل", callback_data=f"stock_rem_{p[0]}"))
        bot.send_message(ADMIN_ID, f"📦 المنتج: `{p[1]}`\nالكمية الحالية: `{p[2]}`", reply_markup=mk)

# --- 7. استمرارية العمل (Anti-Freeze) ---
@app.route('/')
def health_check(): return "Omega V.124 Sovereign OS: Stable"

def run_v124():
    while True:
        try:
            bot.remove_webhook()
            logger.info("Sovereign Polling Online...")
            bot.infinity_polling(skip_pending_updates=True, timeout=90)
        except Exception as e:
            logger.error(f"System Glitch: {e}")
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_v124, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
