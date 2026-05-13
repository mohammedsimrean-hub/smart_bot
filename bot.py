import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading

# --- الإعدادات (يفضل استخدام Environment Variables لاحقاً) ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- إدارة قاعدة البيانات (SQL Service) ---
class DBService:
    def __init__(self):
        self.db_path = 'omega_v5.db'
        self.init_db()

    def query(self, sql, params=(), commit=False, fetch=False):
        # اتصال آمن لكل طلب لتجنب مشاكل الـ Threading
        with sqlite3.connect(self.db_path, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if commit: conn.commit()
            if fetch: return cursor.fetchall()
            return cursor.lastrowid

    def init_db(self):
        # جدول المستخدمين
        self.query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)", commit=True)
        # جدول المنتجات (الديناميكي)
        self.query("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)", commit=True)
        # جدول الطلبات
        self.query("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prod_id INTEGER, status TEXT)", commit=True)
        
        # إضافة منتجات افتراضية إذا كانت القائمة فارغة
        if not self.query("SELECT * FROM products", fetch=True):
            self.query("INSERT INTO products (name, price) VALUES (?, ?)", ("اشتراك دعم شهري", 30.0), commit=True)
            self.query("INSERT INTO products (name, price) VALUES (?, ?)", ("نظام أوميغا الكامل", 700.0), commit=True)

db = DBService()

# --- لوحات التحكم ---
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ تصفح المتجر', '📦 تتبع طلباتي', '📞 الدعم الفني')
    return markup

def get_admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📊 التقارير', '📢 إعلان جماعي', '🆕 إضافة منتج', '✅ إدارة الطلبات')
    return markup

# --- المنطق البرمجي للبوت ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    db.query("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (message.from_user.id, message.from_user.first_name), commit=True)
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 نظام أوميغا: وضع القائد مفعل.", reply_markup=get_admin_menu())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في أوميغا V5.0 🚀\nنظام التجارة المؤتمت الأول.", reply_markup=get_main_menu())

@bot.message_handler(func=lambda m: True)
def router(message):
    uid = message.from_user.id
    text = message.text

    # مسار الأدمن
    if uid == ADMIN_ID:
        if text == '📊 التقارير':
            u_count = len(db.query("SELECT id FROM users", fetch=True))
            o_count = len(db.query("SELECT id FROM orders", fetch=True))
            bot.reply_to(message, f"📈 إحصائيات حية:\n- مستخدمين: {u_count}\n- طلبات: {o_count}")
        elif text == '✅ إدارة الطلبات':
            pending = db.query("SELECT id, user_id FROM orders WHERE status='بانتظار الدفع' LIMIT 5", fetch=True)
            for order in pending:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"تأكيد دفع #{order[0]}", callback_data=f"confirm_{order[0]}"))
                bot.send_message(ADMIN_ID, f"طلب معلق رقم #{order[0]} من {order[1]}", reply_markup=markup)

    # مسار المستخدم
    if text == '🛍️ تصفح المتجر':
        prods = db.query("SELECT * FROM products", fetch=True)
        markup = types.InlineKeyboardMarkup()
        for p in prods:
            markup.add(types.InlineKeyboardButton(f"{p[1]} - {p[2]}$", callback_data=f"buy_{p[0]}"))
        bot.send_message(message.chat.id, "قائمة المنتجات المتوفرة حالياً:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    if call.data.startswith('buy_'):
        pid = call.data.split('_')[1]
        order_id = db.query("INSERT INTO orders (user_id, prod_id, status) VALUES (?, ?, ?)", (call.from_user.id, pid, 'بانتظار الدفع'), commit=True)
        bot.answer_callback_query(call.id, "تم تسجيل الطلب!")
        bot.edit_message_text(f"✅ تم إنشاء الطلب رقم #{order_id}.\nتواصل مع الإدارة للدفع.", call.message.chat.id, call.message.message_id)
        bot.send_message(ADMIN_ID, f"🚨 طلب جديد رقم #{order_id}")
    
    elif call.data.startswith('confirm_'):
        oid = call.data.split('_')[1]
        db.query("UPDATE orders SET status='تم الدفع' WHERE id=?", (oid,), commit=True)
        bot.answer_callback_query(call.id, "تم تأكيد الدفع ✅")
        bot.edit_message_text(f"الطلب #{oid} صار جاهز ومكتمل!", call.message.chat.id, call.message.message_id)

# --- تشغيل النظام ---
def run_bot():
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
