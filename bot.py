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

# --- قاعدة البيانات ---
def get_db_connection():
    conn = sqlite3.connect('omega_v5.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prod_id INTEGER, status TEXT)')
    
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO products (name, price) VALUES (?, ?)', ("اشتراك دعم شهري", 30.0))
        cursor.execute('INSERT INTO products (name, price) VALUES (?, ?)', ("نظام أوميغا الكامل", 700.0))
    conn.commit()
    conn.close()

init_db()

# --- القوائم ---
def get_admin_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📊 التقارير', '✅ إدارة الطلبات', '📢 إعلان جماعي')
    return markup

def get_user_kb():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ تصفح المتجر', '📦 تتبع طلبي', '📞 الدعم الفني')
    return markup

# 1. مراقب أمر /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    conn = get_db_connection()
    conn.execute('INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)', (message.from_user.id, message.from_user.first_name))
    conn.commit()
    conn.close()
    
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 أهلاً بك يا قائد أوميغا. النظام جاهز للعمل.", reply_markup=get_admin_kb())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في أوميغا V5.0 🚀\nاختر من القائمة أدناه:", reply_markup=get_user_kb())

# 2. مراقب الرسائل النصية العام (هاد اللي بحل مشكلتك)
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text
    uid = message.from_user.id

    # خيارات المستخدم
    if text == '🛍️ تصفح المتجر':
        conn = get_db_connection()
        prods = conn.execute('SELECT * FROM products').fetchall()
        conn.close()
        markup = types.InlineKeyboardMarkup()
        for p in prods:
            markup.add(types.InlineKeyboardButton(f"{p[1]} - {p[2]}$", callback_data=f"buy_{p[0]}"))
        bot.send_message(message.chat.id, "قائمة الخدمات المتاحة:", reply_markup=markup)

    elif text == '📦 تتبع طلبي':
        bot.reply_to(message, "🔍 جاري البحث في قاعدة البيانات عن طلباتك...")

    elif text == '📞 الدعم الفني':
        bot.reply_to(message, "ارسل استفسارك الآن وسيتم الرد عليك قريباً.")

    # خيارات الأدمن
    elif uid == ADMIN_ID and text == '📊 التقارير':
        conn = get_db_connection()
        u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        conn.close()
        bot.reply_to(message, f"👤 إجمالي عدد المستخدمين: {u_count}")

    # إذا بعث أي شيء ثاني (مثل "هاي")
    else:
        if uid == ADMIN_ID:
            bot.reply_to(message, "أهلاً بك يا قائد، استخدم الأزرار للتحكم بالنظام.")
        else:
            bot.reply_to(message, "وصلت رسالتك لفريق أوميغا، شكراً لتواصلك!")

# --- معالجة الـ Webserver لـ Render ---
@app.route('/')
def home():
    return "Omega System is Live!"

def run_bot():
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
