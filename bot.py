import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading

# --- الإعدادات ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- خدمة قاعدة البيانات (المنطق المطور) ---
class OmegaDB:
    def __init__(self):
        self.db_name = 'omega_final.db'
        self.init_db()

    def execute(self, sql, params=(), commit=False, fetch=False):
        with sqlite3.connect(self.db_name, check_same_thread=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            if commit: conn.commit()
            if fetch: return cursor.fetchall()
            return cursor.lastrowid

    def init_db(self):
        self.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)", commit=True)
        self.execute("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)", commit=True)
        self.execute("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prod_id INTEGER, status TEXT)", commit=True)
        
        # بذر البيانات الأولية
        if not self.execute("SELECT * FROM products", fetch=True):
            self.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("اشتراك دعم شهري", 30.0), commit=True)
            self.execute("INSERT INTO products (name, price) VALUES (?, ?)", ("نظام أوميغا الكامل", 700.0), commit=True)

db = OmegaDB()

# --- لوحات المفاتيح ---
def admin_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📊 إحصائيات حية', '📦 إدارة الطلبات', '📢 تعميم إعلان')
    return markup

def user_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ تصفح المتجر', '📑 طلباتي', '📞 الدعم الفني')
    return markup

# --- معالجة الأوامر ---
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = message.from_user.id
    db.execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (uid, message.from_user.first_name), commit=True)
    
    if uid == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 نظام أوميغا V6.0 جاهز. لوحة القيادة مفعلة.", reply_markup=admin_keyboard())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في أوميغا V6.0 🚀\nنظام الأتمتة المطور.", reply_markup=user_keyboard())

# --- معالجة النصوص العامة (حل مشكلة الردود) ---
@bot.message_handler(func=lambda m: True)
def message_router(message):
    uid = message.from_user.id
    text = message.text

    # منطق الأدمن
    if uid == ADMIN_ID:
        if text == '📊 إحصائيات حية':
            u_count = len(db.execute("SELECT id FROM users", fetch=True))
            o_count = len(db.execute("SELECT id FROM orders", fetch=True))
            bot.reply_to(message, f"📈 **تقرير النظام:**\n- المستخدمين: {u_count}\n- إجمالي الطلبات: {o_count}")
        elif text == '📦 إدارة الطلبات':
            pending = db.execute("SELECT id, user_id FROM orders WHERE status='بانتظار الدفع' LIMIT 5", fetch=True)
            if not pending: bot.reply_to(message, "لا يوجد طلبات معلقة حالياً.")
            for order in pending:
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(f"تأكيد الدفع #{order[0]}", callback_data=f"confirm_{order[0]}"))
                bot.send_message(ADMIN_ID, f"طلب معلق رقم #{order[0]} من العميل {order[1]}", reply_markup=markup)

    # منطق المستخدم
    if text == '🛍️ تصفح المتجر':
        prods = db.execute("SELECT * FROM products", fetch=True)
        markup = types.InlineKeyboardMarkup()
        for p in prods:
            markup.add(types.InlineKeyboardButton(f"{p[1]} - {p[2]}$", callback_data=f"buy_{p[0]}"))
        bot.send_message(message.chat.id, "اختر الخدمة المطلوبة:", reply_markup=markup)
    
    elif text == '📑 طلباتي':
        orders = db.execute("SELECT id, status FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1", (uid,), fetch=True)
        if orders:
            bot.reply_to(message, f"📦 **آخر طلب لك:**\nرقم: #{orders[0][0]}\nالحالة: {orders[0][1]}")
        else:
            bot.reply_to(message, "ليس لديك طلبات سابقة.")

    # الرد التفاعلي (حل مشكلة "هاي")
    elif text.lower() in ['هاي', 'hi', 'سلام']:
        bot.reply_to(message, f"أهلاً {message.from_user.first_name}! كيف يمكن لنظام أوميغا مساعدتك اليوم؟")

# --- معالجة الـ Callbacks (الشراء والتأكيد) ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.data.startswith('buy_'):
        pid = call.data.split('_')[1]
        oid = db.execute("INSERT INTO orders (user_id, prod_id, status) VALUES (?, ?, ?)", (call.from_user.id, pid, 'بانتظار الدفع'), commit=True)
        bot.edit_message_text(f"✅ تم تسجيل طلبك رقم #{oid}.\nسيتم التواصل معك لتأكيد الدفع.", call.message.chat.id, call.message.message_id)
        bot.send_message(ADMIN_ID, f"🚨 طلب شراء جديد! رقم #{oid}")

    elif call.data.startswith('confirm_'):
        oid = call.data.split('_')[1]
        db.execute("UPDATE orders SET status='تم التأكيد' WHERE id=?", (oid,), commit=True)
        bot.answer_callback_query(call.id, "تم تأكيد الطلب بنجاح!")
        bot.edit_message_text(f"الطلب #{oid} مكتمل الآن ✅", call.message.chat.id, call.message.message_id)

# --- تشغيل السيرفر لـ Render ---
@app.route('/')
def health_check():
    return "Omega V6.0 Enterprise is Online"

def run_polling():
    bot.remove_webhook()
    bot.infinity_polling(timeout=15, long_polling_timeout=5)

if __name__ == "__main__":
    threading.Thread(target=run_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
