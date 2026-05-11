import telebot
import os
from flask import Flask

# إعدادات البوت
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = '8212079374'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# أمر البداية
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "نظام أوميغا V300.0 جاهز للعمل. أهلاً بك يا محمد.")

# الرد على الرسائل
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "تم استلام رسالتك في نظام أوميغا.")

# نقطة اتصال عشان ريندر ما يطفي البوت (Web Service)
@app.route('/')
def index():
    return "Omega System is Running!"

if __name__ == "__main__":
    # تشغيل البوت
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    # تشغيل السيرفر على المنفذ المطلوب
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
