# --- واجهات الأقسام الفرعية (تعديل الأسعار والخطط) ---
def car_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🇯🇴 الأردن: شهر (13$) | سنة (100$🔥)", callback_data="plan_cars_jo"),
        types.InlineKeyboardButton("🇸🇦 السعودية: شهر (19.99$) | سنة (200$🔥)", callback_data="plan_cars_sa")
    )
    return markup

def re_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🇯🇴 الأردن: شهر (30$) | سنة (220$🔥)", callback_data="plan_re_jo"),
        types.InlineKeyboardButton("🇸🇦 السعودية: شهر (50$) | سنة (499$🔥)", callback_data="plan_re_sa")
    )
    return markup

# --- اختيار المدة (شهري أو سنوي) ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('plan_'))
def select_duration(c):
    category = c.data # مثلا plan_cars_jo
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🗓️ اشتراك شهري", callback_data=f"buy_m_{category}"),
        types.InlineKeyboardButton("🏆 اشتراك سنوي (العرض الخاص)", callback_data=f"buy_y_{category}")
    )
    bot.edit_message_text("اختر مدة الاشتراك المطلوبة للاستفادة من العروض:", c.message.chat.id, c.message.message_id, reply_markup=markup)

# --- معالجة الدفع بناءً على الأسعار الجديدة ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('buy_'))
def payment_process(c):
    uid = c.from_user.id
    # تفاصيل الأسعار حسب الخطة
    price_list = {
        "buy_m_plan_cars_jo": "13$", "buy_y_plan_cars_jo": "100$",
        "buy_m_plan_cars_sa": "19.99$", "buy_y_plan_cars_sa": "200$",
        "buy_m_plan_re_jo": "30$", "buy_y_plan_re_jo": "220$",
        "buy_m_plan_re_sa": "50$", "buy_y_plan_re_sa": "499$",
        "buy_m_plan_amazon": "70$", "buy_y_plan_amazon": "740$"
    }
    
    plan_code = c.data
    price = price_list.get(plan_code, "اتصل بالدعم")
    
    # تحديث حالة المستخدم في الداتابيز
    with db.connect() as conn:
        conn.execute("UPDATE users SET state='WAITING_PHOTO', name=? WHERE id=?", (plan_code, uid))
    
    pay_msg = (
        f"💳 **تفاصيل الفاتورة:**\n"
        f"الخدمة: `{plan_code.split('_')[-1]}`\n"
        f"المبلغ المطلوب: **{price}**\n\n"
        "⚠️ **العرض السنوي يوفر عليك الكثير!**\n\n"
        "لإتمام الدفع:\n"
        "📍 داخل الأردن (زين كاش/كليك): `[ضع رقمك]`\n"
        "🌍 دولياً (USDT - TRC20):\n`[ضع عنوان محفظتك]`\n\n"
        "📸 أرسل صورة الوصل هنا فوراً لتفعيل اشتراكك."
    )
    bot.edit_message_text(pay_msg, c.message.chat.id, c.message.message_id)
