import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading
import time

# --- 1. الإعدادات الأساسية ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 
bot = telebot.TeleBot(API_TOKEN, parse_mode='Markdown')
app = Flask(__name__)

# --- 2. قاعدة البيانات ---
class Database:
    def __init__(self):
        self.db_path = 'omega_final.db'
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, name TEXT, state TEXT, sub_type TEXT DEFAULT 'FREE'
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, plan TEXT, photo TEXT
            )""")
            conn.commit()

db = Database()

# --- 3. لوحات التحكم والقوائم ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🚗 السيارات', '🏠 العقارات', '📦 أمازون')
    markup.add('💳 اشتراكاتي', '🛡️ الدعم الفني')
    return markup

def countries_menu(service):
    markup = types.InlineKeyboardMarkup(row_width=2)
    countries = [
        ("🇯🇴 الأردن", "jo"), ("🇸🇦 السعودية", "sa"), 
        ("🇦🇪 الإمارات", "ae"), ("🇧🇭 البحرين", "bh"), 
        ("🇶🇦 قطر", "qa"), ("🇴🇲 عمان", "om"), ("🇰🇼 الكويت", "kw")
    ]
    btns = [types.InlineKeyboardButton(n, callback_data=f"sel_{service}_{c}") for n, c in countries]
    markup.add(*btns)
    return markup

# --- 4. معالجة الرسائل ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    with db.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, name, state) VALUES (?, ?, 'IDLE')", (uid, message.from_user.first_name))
    bot.send_message(message.chat.id, "🔱 **مرحباً بك في نظام أوميغا للاستخبارات التجارية**\nاختر القسم المطلوب:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def router(message):
    if message.text == '🚗 السيارات':
        bot.send_message(message.chat.id, "اختر الدولة لمراقبة السيارات:", reply_markup=countries_menu("cars"))
    elif message.text == '🏠 العقارات':
        bot.send_message(message.chat.id, "اختر الدولة لمراقبة العقارات:", reply_markup=countries_menu("re"))
    elif message.text == '📦 أمازون':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🗓️ شهري (70$)", callback_data="buy_m_amz"),
                   types.InlineKeyboardButton("🏆 سنوي (740$)", callback_data="buy_y_amz"))
        bot.send_message(message.chat.id, "📦 اشتراك أمازون (أفضل 100 منتج مبيعاً):", reply_markup=markup)

# --- 5. منطق الأسعار والدفع ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('sel_'))
def select_plan(c):
    _, service, country = c.data.split('_')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🗓️ اشتراك شهري", callback_data=f"buy_m_{service}_{country}"),
               types.InlineKeyboardButton("🏆 اشتراك سنوي (عرض)", callback_data=f"buy_y_{service}_{country}"))
    bot.edit_message_text(f"اختر مدة الاشتراك لـ {service} في {country}:", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def pay_msg(c):
    uid = c.from_user.id
    plan = c.data
    # ميكانيكية الأسعار حسب طلبك
    prices = {
        "m_cars_jo": "13$", "y_cars_jo": "100$",
        "m_cars_sa": "19.99$", "y_cars_sa": "200$",
        "m_re_jo": "30$", "y_re_jo": "220$",
        "m_re_sa": "50$", "y_re_sa": "499$",
        "m_amz": "70$", "y_amz": "740$"
    }
    # (باقي دول الخليج نضع لها سعر السعودية كافتراضي)
    price = prices.get(plan.replace('buy_', ''), "اتصل بالدعم")
    
    with db.connect() as conn:
        conn.execute("UPDATE users SET state='WAIT_PHOTO', name=? WHERE id=?", (plan, uid))
    
    msg = (
        f"💳 **فاتورة اشتراك: {price}**\n\n"
        "للدفع من الأردن (زين كاش):\n`0782237627` ✅\n\n"
        "للدفع دولياً (Binance - USDT TRC20):\n`عنوان_محفظتك_هنا` 🌍\n\n"
        "📸 أرسل صورة الوصل هنا لتفعيل الحساب."
    )
    bot.edit_message_text(msg, c.message.chat.id, c.message.message_id)

@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    uid = message.from_user.id
    with db.connect() as conn:
        user = conn.execute("SELECT state, name FROM users WHERE id=?", (uid,)).fetchone()
    if user and user[0] == 'WAIT_PHOTO':
        photo_id = message.photo[-1].file_id
        bot.reply_to(message, "⏳ جاري مراجعة طلبك من قبل محمد...")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"adm_ok_{uid}_{user[1]}"),
                   types.InlineKeyboardButton("❌ رفض", callback_data=f"adm_no_{uid}"))
        bot.send_photo(ADMIN_ID, photo_id, caption=f"طلب جديد من {uid}\nالباقة: {user[1]}", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('adm_'))
def admin_action(c):
    _, act, uid, *plan = c.data.split('_')
    if act == 'ok':
        with db.connect() as conn:
            conn.execute("UPDATE users SET sub_type=?, state='IDLE' WHERE id=?", (plan[0], uid))
        bot.send_message(uid, "🎉 تم تفعيل اشتراكك بنجاح! استمتع بالبيانات.")
    else:
        bot.send_message(uid, "❌ نعتذر، تم رفض الوصل. تأكد من التحويل.")
    bot.answer_callback_query(c.id, "تم الإجراء")

# --- 6. تشغيل السيرفر ---
@app.route('/')
def h(): return "Omega Active"

def r():
    while True:
        try: bot.infinity_polling()
        except: time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=r, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
