import telebot
import os
from flask import Flask

API_TOKEN = '8641628383:AAFpiPkh4GKkicpLgJsTaK-efKUKLfZKP64'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "نظام أوميغا V300.0 جاهز للعمل. أهلاً بك يا محمد.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, "تم استلام رسالتك في نظام أوميغا.")

@app.route('/')
def index():
    return "Omega System is Running!"

if __name__ == "__main__":
    import threading
    threading.Thread(target=bot.infinity_polling).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
