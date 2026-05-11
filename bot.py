import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading

# الإعدادات الأساسية
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 # الأيدي الخاص بك كمدير

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- إنشاء قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('omega_business.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, username TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- لوحة الأزرار الرئيسية ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ المتجر', '🛒 سلة المشتريات', '📦 طلباتي', '📞 الدعم الفني')
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    # تسجيل المستخدم في القاعدة
    conn = sqlite3.connect('omega_business.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, name, username) VALUES (?, ?, ?)', 
                   (message.from_user.id, message.from_user.first_name, message.from_user.username))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, f"أهلاً بك في منصة أوميغا الذكية.\nنحن نوفر لك أفضل المنتجات بأتمتة كاملة.", reply_markup=main_menu())
    bot.send_message(ADMIN_ID, f"🔔 مستخدم جديد دخل النظام: {message.from_user.first_name}")

@bot.message_handler(func=lambda m: True)
def handle_business_logic(message):
    if message.text == '🛍️ المتجر':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("منتج 1 - 50$ 💰", callback_data="buy_item1"))
        markup.add(types.InlineKeyboardButton("منتج 2 - 100$ 💰", callback_data="buy_item2"))
        bot.send_message(message.chat.id, "اختر المنتج الذي ترغب بشرائه:", reply_markup=markup)

    elif message.text == '📞 الدعم الفني':
        bot.reply_to(message, "ارسل استفسارك الآن وسيرد عليك أحد الموظفين قريباً.")

# --- معالجة عمليات الشراء ---
@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def process_purchase(call):
    item_name = "منتج متميز" if call.data == "buy_item1" else "باقة احترافية"
    
    # تسجيل الطلب في القاعدة
    conn = sqlite3.connect('omega_business.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, item, status) VALUES (?, ?, ?)', (call.from_user.id, item_name, 'قيد الانتظار'))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "تم تسجيل طلبك بنجاح!")
    bot.send_message(call.message.chat.id, f"✅ تم طلب {item_name}. سيتم التواصل معك لإتمام الدفع.")
    
    # إشعار فوري لك (الأدمن) مع تفاصيل العميل
    bot.send_message(ADMIN_ID, f"🚨 طلب شراء جديد!\nالعميل: {call.from_user.first_name}\nالمنتج: {item_name}")

# --- تشغيل السيرفر (Render) ---
@app.route('/')
def home(): return "Omega Enterprise System is Active"

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling()).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
