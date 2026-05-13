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
def init_db():
    conn = sqlite3.connect('omega_v5.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, price REAL)')
    cursor.execute('CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, prod_id INTEGER, status TEXT)')
    # إضافة منتجات لو الجدول فاضي
    cursor.execute('SELECT COUNT(*) FROM products')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO products (name, price) VALUES (?, ?)', ("اشتراك دعم شهري", 30.0))
        cursor.execute('INSERT INTO products (name, price) VALUES (?, ?)', ("نظام أوميغا الكامل", 700.0))
    conn.commit()
    conn.close()

init_db()

# --- أوامر البوت ---
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('omega_v5.db', check_same_thread=False)
    conn.execute('INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)', (message.from_user.id, message.from_user.first_name))
    conn.commit()
    conn.close()
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if message.from_user.id == ADMIN_ID:
        markup.add('📊 التقارير', '✅ إدارة الطلبات')
        bot.send_message(message.chat.id, "🔱 وضع القائد مفعل.", reply_markup=markup)
    else:
        markup.add('🛍️ تصفح المتجر', '📦 تتبع طلباتي')
        bot.send_message(message.chat.id, "مرحباً بك في أوميغا V5.0 🚀", reply_markup=markup)

# --- تشغيل الويب والبوت معاً ---
@app.route('/')
def home():
    return "Omega System is Online!"

def run_bot():
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == "__main__":
    # تشغيل البوت في الخلفية
    threading.Thread(target=run_bot, daemon=True).start()
    # تشغيل الويب (إجباري لـ Render)
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
