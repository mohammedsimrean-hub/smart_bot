import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading

# --- الإعدادات (تأكد من الأيدي والتوكن) ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- وظائف قاعدة البيانات ---
def get_db():
    conn = sqlite3.connect('omega_enterprise.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)')
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, status TEXT, price REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- القوائم ---
def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('📊 إحصائيات النظام', '📢 إعلان جماعي', '⚙️ الإعدادات')
    return markup

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ المنتجات', '🛒 تتبع طلبي', '💳 شحن رصيد', '📞 الدعم الفني')
    return markup

# --- الأوامر الرئيسية ---
@bot.message_handler(commands=['start'])
def start(message):
    conn = get_db()
    conn.execute('INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)', (message.from_user.id, message.from_user.first_name))
    conn.commit()
    conn.close()

    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 أهلاً بك يا قائد أوميغا. كل الأنظمة تحت سيطرتك الآن.", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في نظام أوميغا المتكامل 🚀", reply_markup=main_menu())

# --- معالجة الرسائل والكبسات (المنطق الفعلي) ---
@bot.message_handler(func=lambda m: True)
def handle_logic(message):
    uid = message.from_user.id
    text = message.text

    # 1. قسم الإدارة (فقط لك)
    if uid == ADMIN_ID:
        if text == '📊 إحصائيات النظام':
            conn = get_db()
            u_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
            o_count = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
            sales = conn.execute('SELECT SUM(price) FROM orders').fetchone()[0] or 0
            conn.close()
            msg = f"📈 **تقرير النظام الحلي:**\n\n👤 عدد المستخدمين: {u_count}\n📦 عدد الطلبات: {o_count}\n💰 إجمالي المبيعات: {sales}$"
            bot.reply_to(message, msg, parse_mode="Markdown")
        
        elif text == '📢 إعلان جماعي':
            bot.reply_to(message, "حاضر يا قائد، ارسل نص الإعلان الآن ليتم تعميمه:")
            bot.register_next_step_handler(message, process_broadcast)
            return

    # 2. قسم المستخدمين
    if text == '🛍️ المنتجات':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 اشتراك شهري - 30$", callback_data="buy_30"))
        markup.add(types.InlineKeyboardButton("🔥 نظام كامل - 700$", callback_data="buy_700"))
        bot.send_message(message.chat.id, "اختر الخدمة التي تود طلبها:", reply_markup=markup)

    elif text == '🛒 تتبع طلبي':
        conn = get_db()
        order = conn.execute('SELECT id, item, status FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1', (uid,)).fetchone()
        conn.close()
        if order:
            bot.reply_to(message, f"🔍 **آخر طلب لك:**\n\nرقم الطلب: #{order[0]}\nالخدمة: {order[1]}\nالحالة: {order[2]}")
        else:
            bot.reply_to(message, "لا توجد طلبات مسجلة باسمك حالياً.")

    elif text == '📞 الدعم الفني':
        bot.reply_to(message, "اكتب مشكلتك الآن، وسيتم تحويلها للمدير فوراً.")

    # تحويل أي كلام موجه للبوت كدعم فني للأدمن
    elif uid != ADMIN_ID:
        bot.send_message(ADMIN_ID, f"📩 **رسالة دعم جديدة:**\nمن: {message.from_user.first_name}\nالأيدي: `{uid}`\n\nالرسالة: {text}", parse_mode="Markdown")
        bot.reply_to(message, "✅ تم إرسال رسالتك للمدير.")

# --- وظائف مساعدة ---
def process_broadcast(message):
    conn = get_db()
    users = conn.execute('SELECT id FROM users').fetchall()
    conn.close()
    count = 0
    for u in users:
        try:
            bot.send_message(u[0], f"📢 **إعلان من الإدارة:**\n\n{message.text}", parse_mode="Markdown")
            count += 1
        except: pass
    bot.send_message(ADMIN_ID, f"✅ تم إرسال الإعلان بنجاح إلى {count} مستخدم.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def purchase_logic(call):
    price = 30.0 if "30" in call.data else 700.0
    item = "اشتراك شهري" if price == 30 else "نظام أوميغا الكامل"
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, item, status, price) VALUES (?, ?, ?, ?)', 
                   (call.from_user.id, item, 'بانتظار الدفع', price))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    bot.edit_message_text(f"✅ تم تسجيل طلبك بنجاح!\n\nرقم الطلب: #{order_id}\nالخدمة: {item}\nالسعر: {price}$\n\nسيقوم المدير بالتواصل معك الآن.", call.message.chat.id, call.message.message_id)
    bot.send_message(ADMIN_ID, f"🚨 **طلب شراء جديد!**\nالعميل: {call.from_user.first_name}\nالمنتج: {item}\nرقم الطلب: {order_id}")

# --- تشغيل السيرفر والبوت ---
@app.route('/')
def home(): return "Omega Enterprise System is Active 🚀"

if __name__ == "__main__":
    threading.Thread(target=lambda: bot.infinity_polling()).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
