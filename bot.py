import telebot
import os
from flask import Flask
import threading

# الإعدادات الخاصة بك
API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'
ADMIN_ID = '8212079374'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "نظام أوميغا V300.0 جاهز للعمل. أهلاً بك يا محمد.")
    # إشعار لك إن في حدا شغل البوت
    bot.send_message(ADMIN_ID, f"تم تشغيل البوت من قبل: {message.from_user.first_name}")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "تم استلام رسالتك في نظام أوميغا.")
    # إرسال نسخة من الرسالة لحسابك الشخصي
    bot.send_message(ADMIN_ID, f"رسالة جديدة من {message.from_user.first_name}:\n{message.text}")

@app.route('/')
def index():
    return "Omega System is Running!"

def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # تشغيل البوت في خلفية السيرفر
    t = threading.Thread(target=run_bot)
    t.start()
    # تشغيل ويب سيرفر عشان ريندر ما يطفي
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
