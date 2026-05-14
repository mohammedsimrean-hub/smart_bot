import telebot
from telebot import types
import sqlite3
import os
import logging
from flask import Flask
import threading
import time

# --- 1. الإعدادات والتعريفات (يجب أن تكون في البداية) ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 
bot = telebot.TeleBot(API_TOKEN, parse_mode='Markdown')
app = Flask(__name__)

# --- 2. إدارة قاعدة البيانات ---
class Database:
    def __init__(self):
        self.db_path = 'omega_business.db'
        self.init_db()

    def connect(self):
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def init_db(self):
        with self.connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY, 
                name TEXT, 
                state TEXT, 
                sub_type TEXT DEFAULT 'FREE', 
                is_banned INTEGER DEFAULT 0
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS sub_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                user_id INTEGER, 
                sub_plan TEXT, 
                receipt_photo TEXT, 
                status TEXT DEFAULT 'PENDING'
            )""")
            conn.commit()

db = Database()

# --- 3. لوحات المفاتيح (القوائم) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🚗 السيارات', '🏠 العقارات', '📦 أمازون')
    markup.add('💳 اشتراكاتي', '🛡️ الدعم الفني')
    return markup

def car_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    # تحديث الأسعار حسب طلبك (الأردن 13$ والسعودية 19.99$)
    markup.add(
        types.InlineKeyboardButton("🇯🇴 الأردن: شهر (13$) | سنة (100$🔥)", callback_data="plan_cars_jo"),
        types.InlineKeyboardButton("🇸🇦 السعودية: شهر (19.99$) | سنة (200$🔥)", callback_data="plan_cars_sa")
    )
    return markup

def re_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    # تحديث الأسعار (الأردن 30$ والسعودية 50$)
    markup.add(
        types.InlineKeyboardButton("🇯🇴 الأردن: شهر (30$) | سنة (220$🔥)", callback_data="plan_re_jo"),
        types.InlineKeyboardButton("🇸🇦 السعودية: شهر (50$) | سنة (499$🔥)", callback_data="plan_re_sa")
    )
    return markup

# --- 4. معالجة الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    with db.connect() as conn:
        conn.execute("INSERT OR IGNORE INTO users (id, name, state) VALUES (?, ?, 'IDLE')", (uid, message.from_user.first_name))
    
    welcome = (
        "🔱 **مرحباً بك في نظام أوميغا V.1**\n"
        "للحصول على أفضل صفقات السيارات، العقارات، وأمازون.\n\n"
        "اختر القسم المطلوب للاشتراك:"
    )
    bot.send_message(message.chat.id, welcome, reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def router(message):
    uid = message.from_user.id
    text = message.text

    if text == '🚗 السيارات':
        bot.send_message(message.chat.id, "اختر السوق المستهدف لمراقبة السيارات:", reply_markup=car_menu())
    elif text == '🏠 العقارات':
        bot.send_message(message.chat.id, "اختر السوق المستهدف لمراقبة العقارات:", reply_markup=re_menu())
    elif text == '📦 أمازون':
        markup = types.InlineKeyboardMarkup()
        # اشتراك أمازون 70$ شهري و 740$ سنوي
        markup.add(types.InlineKeyboardButton("🔥 اشتراك أمازون (70$ شهري / 740$ سنوي)", callback_data="plan_amazon"))
        bot.send_message(message.chat.id, "تحليل مبيعات أمازون وأفضل 100 منتج مبيعاً.", reply_markup=markup)
    elif text == '💳 اشتراكاتي':
        with db.connect() as conn:
            user = conn.execute("SELECT sub_type FROM users WHERE id=?", (uid,)).fetchone()
            bot.reply_to(message, f"نوع اشتراكك الحالي: `{user[0]}`")

# --- 5. نظام اختيار المدة والدفع ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('plan_'))
def select_duration(c):
    category = c.data # مثلا plan_cars_jo
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗓️ اشتراك شهري", callback_data=f"buy_m_{category}"),
        types.InlineKeyboardButton("🏆 اشتراك سنوي (العرض الخاص)", callback_data=f"buy_y_{category}")
    )
    bot.edit_message_text("اختر مدة الاشتراك المطلوبة للاستفادة من العروض السنوية:", c.message.chat.id, c.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def payment_process(c):
    uid = c.from_user.id
    # قائمة الأسعار النهائية حسب طلبك
    price_list = {
        "buy_m_plan_cars_jo": "13$", "buy_y_plan_cars_jo": "100$",
        "buy_m_plan_cars_sa": "19.99$", "buy_y_plan_cars_sa": "200$",
        "buy_m_plan_re_jo": "30$", "buy_y_plan_re_jo": "220$",
        "buy_m_plan_re_sa": "50$", "buy_y_plan_re_sa": "499$",
        "buy_m_plan_amazon": "70$", "buy_y_plan_amazon": "740$"
    }
    
    plan_code = c.data
    price = price_list.get(plan_code, "غير محدد")
    
    with db.connect() as conn:
        conn.execute("UPDATE users SET state='WAITING_PHOTO', name=? WHERE id=?", (plan_code, uid))
    
    pay_msg = (
        f"💳 **تفاصيل الاشتراك:**\n"
        f"الخدمة: `{plan_code}`\n"
        f"المبلغ: **{price}**\n\n"
        "لإتمام التحويل:\n"
        "📍 الأردن (زين كاش/CliQ): `07XXXXXXXX` (ضع رقمك)\n"
        "🌍 دولياً (USDT - TRC20):\n`عنوان_محفظتك_هنا`\n\n"
        "📸 أرسل صورة الوصل (Screenshot) هنا للتفعيل."
    )
    bot.edit_message_text(pay_msg, c.message.chat.id, c.message.message_id)

# --- 6. استقبال صور الوصل وتفعيل الأدمن ---
@bot.message_handler(content_types=['photo'])
def handle_receipt(message):
    uid = message.from_user.id
    with db.connect() as conn:
        user = conn.execute("SELECT state, name FROM users WHERE id=?", (uid,)).fetchone()
    
    if user and user[0] == 'WAITING_PHOTO':
        photo_id = message.photo[-1].file_id
        plan = user[1]
        
        with db.connect() as conn:
            conn.execute("INSERT INTO sub_requests (user_id, sub_plan, receipt_photo) VALUES (?, ?, ?)", 
                         (uid, plan, photo_id))
            conn.execute("UPDATE users SET state='IDLE' WHERE id=?", (uid,))
        
        bot.reply_to(message, "✅ تم استلام صورة الوصل. جاري مراجعة الدفع من قبل الإدارة.")
        
        # تنبيه للأدمن (أنت)
        admin_markup = types.InlineKeyboardMarkup()
        admin_markup.add(types.InlineKeyboardButton("✅ تفعيل", callback_data=f"admin_approve_{uid}_{plan}"),
                         types.InlineKeyboardButton("❌ رفض", callback_data=f"admin_reject_{uid}"))
        
        bot.send_photo(ADMIN_ID, photo_id, caption=f"🚨 طلب جديد!\nالمستخدم: `{uid}`\nالباقة: `{plan}`", reply_markup=admin_markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('admin_'))
def admin_action(c):
    data = c.data.split('_')
    action = data[1]
    target_uid = data[2]
    
    if action == 'approve':
        plan = data[3]
        with db.connect() as conn:
            conn.execute("UPDATE users SET sub_type=? WHERE id=?", (plan, target_uid))
        bot.send_message(target_uid, f"🎉 تم تفعيل اشتراكك في باقة `{plan}` بنجاح!")
        bot.answer_callback_query(c.id, "تم التفعيل")
    else:
        bot.send_message(target_uid, "❌ عذراً، تم رفض طلبك. تأكد من صحة الوصل.")
        bot.answer_callback_query(c.id, "تم الرفض")

# --- 7. تشغيل Flask للبقاء حياً على Render ---
@app.route('/')
def home(): return "Omega Server Online"

def run_bot():
    while True:
        try:
            bot.infinity_polling(timeout=90)
        except Exception:
            time.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
