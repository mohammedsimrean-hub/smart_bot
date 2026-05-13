import telebot
from telebot import types
import sqlite3
import os
from flask import Flask
import threading

# --- الإعدادات الأساسية ---
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = 8212079374 

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- إعداد قواعد البيانات (Database) ---
def init_db():
    conn = sqlite3.connect('omega_enterprise.db', check_same_thread=False)
    cursor = conn.cursor()
    # جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)''')
    # جدول الطلبات (مع تتبع الحالة)
    cursor.execute('''CREATE TABLE IF NOT EXISTS orders 
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, item TEXT, status TEXT, price REAL)''')
    conn.commit()
    conn.close()

init_db()

# --- واجهة الويب (Web Dashboard) للإحصائيات ---
@app.route('/')
def dashboard():
    conn = sqlite3.connect('omega_enterprise.db')
    users_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    orders_count = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
    total_sales = conn.execute('SELECT SUM(price) FROM orders WHERE status="تم التفعيل"').fetchone()[0] or 0
    conn.close()
    
    return f"""
    <html>
        <head><title>Omega Dashboard</title></head>
        <body style="font-family: Arial; text-align: center; background: #1a1a1a; color: white;">
            <h1>🔱 لوحة تحكم أوميغا V400.0 🔱</h1>
            <div style="display: flex; justify-content: space-around; margin-top: 50px;">
                <div><h3>المستخدمين</h3><p style="font-size: 24px;">{users_count}</p></div>
                <div><h3>إجمالي الطلبات</h3><p style="font-size: 24px;">{orders_count}</p></div>
                <div><h3>المبيعات المؤكدة</h3><p style="font-size: 24px;">{total_sales} $</p></div>
            </div>
            <hr>
            <p>النظام متصل ويعمل بالسحابة 24/7</p>
        </body>
    </html>
    """

# --- لوحات الأزرار (Keyboards) ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add('🛍️ المنتجات', '🛒 تتبع طلبي', '💳 شحن رصيد', '📞 الدعم الفني')
    return markup

def admin_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('📊 إحصائيات النظام', '📢 إعلان جماعي', '⚙️ الإعدادات')
    return markup

# --- معالجة الأوامر ---
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect('omega_enterprise.db')
    conn.execute('INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)', (message.from_user.id, message.from_user.first_name))
    conn.commit()
    conn.close()

    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "🔱 أهلاً بك يا قائد أوميغا. لوحة الإدارة جاهزة.", reply_markup=admin_menu())
    else:
        bot.send_message(message.chat.id, "مرحباً بك في نظام أوميغا المتكامل 🚀\nاختر من القائمة أدناه للبدء:", reply_markup=main_menu())

# --- نظام المنتجات والشراء ---
@bot.message_handler(func=lambda m: m.text == '🛍️ المنتجات')
def show_products(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📦 اشتراك دعم شهري - 30$", callback_data="buy_sub_30"))
    markup.add(types.InlineKeyboardButton("🔥 تركيب نظام كامل - 700$", callback_data="buy_full_700"))
    bot.send_message(message.chat.id, "اختر المنتج أو الخدمة المطلوبة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    item = "اشتراك شهري" if "sub" in call.data else "نظام كامل"
    price = 30.0 if "30" in call.data else 700.0
    
    conn = sqlite3.connect('omega_enterprise.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO orders (user_id, item, status, price) VALUES (?, ?, ?, ?)', 
                   (call.from_user.id, item, 'انتظار الدفع', price))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    bot.send_message(call.message.chat.id, f"✅ تم تسجيل طلبك رقم: #{order_id}\nالحالة: انتظار الدفع.\nيرجى التواصل مع @[يوزرك_هنا] لتفعيل الدفع الإلكتروني.")
    bot.send_message(ADMIN_ID, f"🚨 طلب شراء جديد!\nالعميل: {call.from_user.first_name}\nالمنتج: {item}\nرقم الطلب: {order_id}")

# --- نظام تتبع الطلبات ---
@bot.message_handler(func=lambda m: m.text == '🛒 تتبع طلبي')
def track_order(message):
    conn = sqlite3.connect('omega_enterprise.db')
    order = conn.execute('SELECT id, item, status FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 1', (message.from_user.id,)).fetchone()
    conn.close()
    
    if order:
        bot.reply_to(message, f"📦 تفاصيل آخر طلب:\nالرقم: #{order[0]}\nالمنتج: {order[1]}\nالحالة الحالية: {order[2]}")
    else:
        bot.reply_to(message, "ليس لديك طلبات سابقة حالياً.")

# --- تشغيل البوت والسيرفر ---
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    t = threading.Thread(target=run_bot)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
