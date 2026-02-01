#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import json
import os
import asyncio
from datetime import datetime
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
import aiohttp
from config import *

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
WAITING_USER_ID, WAITING_POINTS, WAITING_COUNTRY, WAITING_SERVICE = range(4)

# قاعدة البيانات البسيطة (JSON)
class Database:
    def __init__(self):
        self.users_file = 'data/users.json'
        self.reservations_file = 'data/reservations.json'
        self.purchases_file = 'data/purchases.json'
        self.settings_file = 'data/settings.json'
        self._ensure_files()
    
    def _ensure_files(self):
        os.makedirs('data', exist_ok=True)
        for file in [self.users_file, self.reservations_file, self.purchases_file, self.settings_file]:
            if not os.path.exists(file):
                with open(file, 'w', encoding='utf-8') as f:
                    if file == self.settings_file:
                        json.dump({
                            'welcome_message': WELCOME_MESSAGE,
                            'force_channel': CHANNEL_USERNAME,
                            'enabled': True
                        }, f, ensure_ascii=False, indent=2)
                    else:
                        json.dump({}, f)
    
    def get_user(self, user_id):
        with open(self.users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        return users.get(str(user_id))
    
    def save_user(self, user_id, data):
        with open(self.users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
        users[str(user_id)] = data
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def add_points(self, user_id, points):
        user = self.get_user(user_id)
        if user:
            user['points'] += points
            self.save_user(user_id, user)
            return True
        return False
    
    def deduct_points(self, user_id, points):
        user = self.get_user(user_id)
        if user and user['points'] >= points:
            user['points'] -= points
            self.save_user(user_id, user)
            return True
        return False
    
    def add_purchase(self, user_id, purchase_data):
        with open(self.purchases_file, 'r', encoding='utf-8') as f:
            purchases = json.load(f)
        
        if str(user_id) not in purchases:
            purchases[str(user_id)] = []
        
        purchases[str(user_id)].append(purchase_data)
        
        with open(self.purchases_file, 'w', encoding='utf-8') as f:
            json.dump(purchases, f, ensure_ascii=False, indent=2)
    
    def get_settings(self):
        with open(self.settings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def update_settings(self, key, value):
        settings = self.get_settings()
        settings[key] = value
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

db = Database()

# دالة التحقق من الاشتراك
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    settings = db.get_settings()
    if not settings.get('enabled', True):
        return True
    
    channel = settings.get('force_channel', CHANNEL_USERNAME)
    if not channel:
        return True
    
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

# الأوامر الرئيسية
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # التحقق من الاشتراك
    if not await check_subscription(update, context):
        settings = db.get_settings()
        channel = settings.get('force_channel', CHANNEL_USERNAME)
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")],
            [InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "⚠️ عذراً، يجب عليك الاشتراك في القناة أولاً:\n\n"
            f"📢 {channel}\n\n"
            "بعد الاشتراك، اضغط على الزر أدناه:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # إنشاء حساب جديد للمستخدم
    user_data = db.get_user(user_id)
    if not user_data:
        user_data = {
            'user_id': user_id,
            'username': user.username or 'بدون يوزر',
            'first_name': user.first_name,
            'points': 0,
            'join_date': datetime.now().isoformat(),
            'purchases': 0
        }
        db.save_user(user_id, user_data)
    
    settings = db.get_settings()
    welcome = settings.get('welcome_message', WELCOME_MESSAGE)
    
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy_number")],
        [InlineKeyboardButton("📱 التليجرام", callback_data="service_telegram"),
         InlineKeyboardButton("💬 الواتساب", callback_data="service_whatsapp")],
        [InlineKeyboardButton("📊 حسابي", callback_data="my_account"),
         InlineKeyboardButton("🔄 حجز تلقائي", callback_data="auto_reserve")],
        [InlineKeyboardButton("💰 شحن نقاط", url=f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=recharge")],
        [InlineKeyboardButton("📞 الدعم", url=SUPPORT_USERNAME)]
    ]
    
    # إضافة لوحة المطور
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة المطور", callback_data="admin_panel")])
    
    await update.message.reply_text(
        welcome.format(name=user.first_name),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# معالجة الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # التحقق من الاشتراك
    if query.data == "check_sub":
        if await check_subscription(update, context):
            await query.edit_message_text("✅ تم التحقق! مرحباً بك\n\nاستخدم /start للبدء")
        else:
            await query.answer("⚠️ لم تشترك بعد في القناة!", show_alert=True)
        return
    
    if not await check_subscription(update, context):
        settings = db.get_settings()
        channel = settings.get('force_channel', CHANNEL_USERNAME)
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")],
            [InlineKeyboardButton("✅ تحققت من الاشتراك", callback_data="check_sub")]
        ]
        await query.edit_message_text(
            "⚠️ عذراً، يجب عليك الاشتراك في القناة أولاً!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # حسابي
    if query.data == "my_account":
        user_data = db.get_user(user_id)
        text = (
            f"👤 <b>معلومات حسابك</b>\n\n"
            f"🆔 الآيدي: <code>{user_id}</code>\n"
            f"👤 الاسم: {user_data['first_name']}\n"
            f"💰 النقاط: <b>{user_data['points']}</b>\n"
            f"🛍 المشتريات: {user_data['purchases']}\n"
            f"📅 تاريخ الانضمام: {user_data['join_date'][:10]}"
        )
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    # شراء رقم
    elif query.data == "buy_number":
        keyboard = [
            [InlineKeyboardButton("🇮🇶 العراق", callback_data="country_iraq"),
             InlineKeyboardButton("🇸🇦 السعودية", callback_data="country_saudi")],
            [InlineKeyboardButton("🇦🇪 الإمارات", callback_data="country_uae"),
             InlineKeyboardButton("🇪🇬 مصر", callback_data="country_egypt")],
            [InlineKeyboardButton("🇯🇴 الأردن", callback_data="country_jordan"),
             InlineKeyboardButton("🇰🇼 الكويت", callback_data="country_kuwait")],
            [InlineKeyboardButton("🇾🇪 اليمن", callback_data="country_yemen"),
             InlineKeyboardButton("🇸🇾 سوريا", callback_data="country_syria")],
            [InlineKeyboardButton("🇱🇧 لبنان", callback_data="country_lebanon"),
             InlineKeyboardButton("🇵🇸 فلسطين", callback_data="country_palestine")],
            [InlineKeyboardButton("🌍 دول أخرى", callback_data="country_more")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "🌍 <b>اختر الدولة:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # الخدمات
    elif query.data.startswith("service_"):
        service = query.data.replace("service_", "")
        service_names = {
            "telegram": "📱 تليجرام",
            "whatsapp": "💬 واتساب",
            "facebook": "📘 فيسبوك",
            "instagram": "📷 انستجرام",
            "tiktok": "🎵 تيك توك",
            "twitter": "🐦 تويتر"
        }
        
        keyboard = [
            [InlineKeyboardButton("🇮🇶 العراق - 50 نقطة", callback_data=f"buy_{service}_iraq")],
            [InlineKeyboardButton("🇸🇦 السعودية - 70 نقطة", callback_data=f"buy_{service}_saudi")],
            [InlineKeyboardButton("🇦🇪 الإمارات - 80 نقطة", callback_data=f"buy_{service}_uae")],
            [InlineKeyboardButton("🇪🇬 مصر - 60 نقطة", callback_data=f"buy_{service}_egypt")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="buy_number")]
        ]
        
        await query.edit_message_text(
            f"{service_names.get(service, service)} - اختر الدولة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # شراء رقم
    elif query.data.startswith("buy_"):
        parts = query.data.split("_")
        service = parts[1]
        country = parts[2]
        
        user_data = db.get_user(user_id)
        price = PRICES.get(country, 50)
        
        if user_data['points'] < price:
            await query.answer(f"⚠️ رصيدك غير كافٍ! تحتاج {price} نقطة", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الشراء", callback_data=f"confirm_{service}_{country}_{price}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="buy_number")]
        ]
        
        country_names = {
            "iraq": "العراق 🇮🇶",
            "saudi": "السعودية 🇸🇦",
            "uae": "الإمارات 🇦🇪",
            "egypt": "مصر 🇪🇬"
        }
        
        service_names = {
            "telegram": "تليجرام",
            "whatsapp": "واتساب"
        }
        
        await query.edit_message_text(
            f"📱 <b>تأكيد الشراء</b>\n\n"
            f"🌍 الدولة: {country_names.get(country, country)}\n"
            f"📲 الخدمة: {service_names.get(service, service)}\n"
            f"💰 السعر: {price} نقطة\n\n"
            f"💵 رصيدك الحالي: {user_data['points']} نقطة\n"
            f"💵 رصيدك بعد الشراء: {user_data['points'] - price} نقطة",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # تأكيد الشراء
    elif query.data.startswith("confirm_"):
        parts = query.data.split("_")
        service = parts[1]
        country = parts[2]
        price = int(parts[3])
        
        # خصم النقاط
        if db.deduct_points(user_id, price):
            # محاكاة شراء رقم من API
            number = f"+964{7700000000 + user_id % 100000000}"  # رقم وهمي للتوضيح
            code_channel = f"CODE_{user_id}_{datetime.now().timestamp()}"
            
            # حفظ عملية الشراء
            purchase_data = {
                'number': number,
                'service': service,
                'country': country,
                'price': price,
                'date': datetime.now().isoformat(),
                'code_channel': code_channel
            }
            db.add_purchase(user_id, purchase_data)
            
            # تحديث عدد المشتريات
            user_data = db.get_user(user_id)
            user_data['purchases'] += 1
            db.save_user(user_id, user_data)
            
            # إرسال إشعار لقناة المشتريات
            country_names = {
                "iraq": "العراق 🇮🇶",
                "saudi": "السعودية 🇸🇦",
                "uae": "الإمارات 🇦🇪",
                "egypt": "مصر 🇪🇬"
            }
            
            service_names = {
                "telegram": "تليجرام 📱",
                "whatsapp": "واتساب 💬"
            }
            
            purchase_msg = (
                f"🎉 <b>عملية شراء جديدة</b>\n\n"
                f"👤 المشتري: #{user_id}\n"
                f"📱 الخدمة: {service_names.get(service, service)}\n"
                f"🌍 الدولة: {country_names.get(country, country)}\n"
                f"📞 الرقم: <code>{number}</code>\n"
                f"🔑 الكود: <code>{code_channel}</code>\n"
                f"💰 السعر: {price} نقطة\n"
                f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            try:
                await context.bot.send_message(
                    chat_id=PURCHASES_CHANNEL,
                    text=purchase_msg,
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            # رسالة للمشتري
            keyboard = [[InlineKeyboardButton("🔙 العودة للقائمة", callback_data="back_main")]]
            
            await query.edit_message_text(
                f"✅ <b>تم الشراء بنجاح!</b>\n\n"
                f"📞 الرقم: <code>{number}</code>\n"
                f"🔑 كود التفعيل: <code>{code_channel}</code>\n"
                f"📱 الخدمة: {service_names.get(service, service)}\n"
                f"🌍 الدولة: {country_names.get(country, country)}\n\n"
                f"💵 رصيدك الحالي: {user_data['points']} نقطة\n\n"
                f"⏱ انتظر وصول الكود... سيصلك خلال دقائق",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
        else:
            await query.answer("⚠️ حدث خطأ! رصيدك غير كافٍ", show_alert=True)
    
    # لوحة المطور
    elif query.data == "admin_panel":
        if user_id not in ADMIN_IDS:
            await query.answer("⚠️ غير مصرح لك!", show_alert=True)
            return
        
        keyboard = [
            [InlineKeyboardButton("➕ إضافة نقاط", callback_data="admin_add_points"),
             InlineKeyboardButton("➖ خصم نقاط", callback_data="admin_deduct_points")],
            [InlineKeyboardButton("✏️ تغيير الترحيب", callback_data="admin_welcome"),
             InlineKeyboardButton("📢 تغيير القناة", callback_data="admin_channel")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>لوحة تحكم المطور</b>\n\nاختر الإجراء:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    # العودة للقائمة الرئيسية
    elif query.data == "back_main":
        user = query.from_user
        user_data = db.get_user(user_id)
        settings = db.get_settings()
        welcome = settings.get('welcome_message', WELCOME_MESSAGE)
        
        keyboard = [
            [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy_number")],
            [InlineKeyboardButton("📱 التليجرام", callback_data="service_telegram"),
             InlineKeyboardButton("💬 الواتساب", callback_data="service_whatsapp")],
            [InlineKeyboardButton("📊 حسابي", callback_data="my_account"),
             InlineKeyboardButton("🔄 حجز تلقائي", callback_data="auto_reserve")],
            [InlineKeyboardButton("💰 شحن نقاط", url=f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=recharge")],
            [InlineKeyboardButton("📞 الدعم", url=SUPPORT_USERNAME)]
        ]
        
        if user_id in ADMIN_IDS:
            keyboard.append([InlineKeyboardButton("⚙️ لوحة المطور", callback_data="admin_panel")])
        
        await query.edit_message_text(
            welcome.format(name=user.first_name),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

# نظام إضافة النقاط من المطور
async def admin_add_points_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("⚠️ غير مصرح لك!", show_alert=True)
        return ConversationHandler.END
    
    await query.edit_message_text(
        "📝 <b>إضافة نقاط</b>\n\n"
        "أرسل معرف المستخدم (User ID) أو اليوزرنيم (@username):",
        parse_mode=ParseMode.HTML
    )
    
    return WAITING_USER_ID

# الإحصائيات
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("⚠️ غير مصرح لك!", show_alert=True)
        return
    
    # قراءة البيانات
    with open('data/users.json', 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    with open('data/purchases.json', 'r', encoding='utf-8') as f:
        purchases = json.load(f)
    
    total_users = len(users)
    total_purchases = sum(len(v) for v in purchases.values())
    total_points = sum(u.get('points', 0) for u in users.values())
    
    text = (
        f"📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 عدد المستخدمين: {total_users}\n"
        f"🛍 إجمالي المشتريات: {total_purchases}\n"
        f"💰 إجمالي النقاط: {total_points}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

def main():
    """تشغيل البوت"""
    application = Application.builder().token(BOT_TOKEN).build()
    
    # المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # تشغيل البوت
    logger.info("🚀 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
