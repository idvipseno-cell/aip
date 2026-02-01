# -*- coding: utf-8 -*-
"""
معالج لوحة تحكم المطور المتقدمة
Advanced Admin Panel Handler
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
import json
from datetime import datetime

# حالات المحادثة للمطور
(
    ADMIN_WAITING_USER_ID,
    ADMIN_WAITING_POINTS,
    ADMIN_WAITING_WELCOME,
    ADMIN_WAITING_CHANNEL,
    ADMIN_WAITING_BROADCAST,
    ADMIN_WAITING_DEDUCT_USER,
    ADMIN_WAITING_DEDUCT_POINTS
) = range(7)

class AdminHandler:
    def __init__(self, db, admin_ids):
        self.db = db
        self.admin_ids = admin_ids
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض لوحة تحكم المطور"""
        query = update.callback_query
        user_id = query.from_user.id
        
        if user_id not in self.admin_ids:
            await query.answer("⚠️ غير مصرح لك!", show_alert=True)
            return
        
        keyboard = [
            [
                InlineKeyboardButton("➕ إضافة نقاط", callback_data="admin_add_points"),
                InlineKeyboardButton("➖ خصم نقاط", callback_data="admin_deduct_points")
            ],
            [
                InlineKeyboardButton("✏️ تغيير الترحيب", callback_data="admin_welcome"),
                InlineKeyboardButton("📢 تغيير القناة", callback_data="admin_channel")
            ],
            [
                InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
                InlineKeyboardButton("📣 إرسال رسالة جماعية", callback_data="admin_broadcast")
            ],
            [
                InlineKeyboardButton("👥 قائمة المستخدمين", callback_data="admin_users_list"),
                InlineKeyboardButton("💰 أعلى الأرصدة", callback_data="admin_top_balance")
            ],
            [
                InlineKeyboardButton("🛍 آخر المشتريات", callback_data="admin_recent_purchases"),
                InlineKeyboardButton("📈 تقرير اليوم", callback_data="admin_today_report")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        
        await query.edit_message_text(
            "⚙️ <b>لوحة تحكم المطور</b>\n\n"
            "اختر الإجراء الذي تريده:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def add_points_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية إضافة نقاط"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📝 <b>إضافة نقاط للمستخدم</b>\n\n"
            "أرسل معرف المستخدم (User ID) أو اليوزرنيم (@username)\n\n"
            "مثال:\n"
            "• <code>123456789</code>\n"
            "• <code>@username</code>\n\n"
            "أو أرسل /cancel للإلغاء",
            parse_mode=ParseMode.HTML
        )
        
        return ADMIN_WAITING_USER_ID
    
    async def add_points_user_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال معرف المستخدم"""
        user_input = update.message.text.strip()
        
        # محاولة الحصول على معرف المستخدم
        if user_input.startswith('@'):
            # البحث في قاعدة البيانات عن اليوزرنيم
            target_user = None
            with open('data/users.json', 'r', encoding='utf-8') as f:
                users = json.load(f)
                for uid, data in users.items():
                    if data.get('username', '').lower() == user_input[1:].lower():
                        target_user = uid
                        break
            
            if not target_user:
                await update.message.reply_text(
                    "❌ لم أجد هذا المستخدم!\n\n"
                    "تأكد من اليوزرنيم أو استخدم الآيدي الرقمي.\n"
                    "أرسل /cancel للإلغاء"
                )
                return ADMIN_WAITING_USER_ID
            
            context.user_data['target_user_id'] = int(target_user)
        else:
            try:
                target_user_id = int(user_input)
                
                # التحقق من وجود المستخدم
                user_data = self.db.get_user(target_user_id)
                if not user_data:
                    await update.message.reply_text(
                        "❌ هذا المستخدم غير موجود في النظام!\n\n"
                        "تأكد من الآيدي أو أرسل /cancel للإلغاء"
                    )
                    return ADMIN_WAITING_USER_ID
                
                context.user_data['target_user_id'] = target_user_id
            except ValueError:
                await update.message.reply_text(
                    "❌ معرف غير صحيح!\n\n"
                    "أرسل آيدي رقمي أو يوزرنيم (@username)\n"
                    "أو أرسل /cancel للإلغاء"
                )
                return ADMIN_WAITING_USER_ID
        
        # الحصول على بيانات المستخدم
        user_data = self.db.get_user(context.user_data['target_user_id'])
        
        await update.message.reply_text(
            f"✅ <b>تم العثور على المستخدم</b>\n\n"
            f"👤 الاسم: {user_data['first_name']}\n"
            f"🆔 الآيدي: <code>{user_data['user_id']}</code>\n"
            f"💰 الرصيد الحالي: {user_data['points']} نقطة\n\n"
            f"📝 الآن أرسل عدد النقاط التي تريد إضافتها:\n"
            f"أو أرسل /cancel للإلغاء",
            parse_mode=ParseMode.HTML
        )
        
        return ADMIN_WAITING_POINTS
    
    async def add_points_amount_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """استقبال عدد النقاط"""
        try:
            points = int(update.message.text.strip())
            
            if points <= 0:
                await update.message.reply_text(
                    "❌ يجب أن يكون العدد موجباً!\n"
                    "أرسل عدد النقاط أو /cancel للإلغاء"
                )
                return ADMIN_WAITING_POINTS
            
            target_user_id = context.user_data['target_user_id']
            user_data = self.db.get_user(target_user_id)
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ نعم، أضف النقاط", callback_data=f"confirm_add_{target_user_id}_{points}"),
                ],
                [
                    InlineKeyboardButton("❌ لا، إلغاء", callback_data="admin_panel")
                ]
            ]
            
            await update.message.reply_text(
                f"⚠️ <b>تأكيد إضافة النقاط</b>\n\n"
                f"👤 المستخدم: {user_data['first_name']}\n"
                f"🆔 الآيدي: <code>{target_user_id}</code>\n\n"
                f"💰 الرصيد الحالي: {user_data['points']} نقطة\n"
                f"➕ النقاط المضافة: {points} نقطة\n"
                f"💵 الرصيد بعد الإضافة: {user_data['points'] + points} نقطة\n\n"
                f"هل أنت متأكد من إضافة <b>{points}</b> نقطة لحساب هذا المستخدم؟",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.HTML
            )
            
            return ConversationHandler.END
            
        except ValueError:
            await update.message.reply_text(
                "❌ أرسل رقماً صحيحاً!\n"
                "أو أرسل /cancel للإلغاء"
            )
            return ADMIN_WAITING_POINTS
    
    async def confirm_add_points(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد إضافة النقاط"""
        query = update.callback_query
        await query.answer()
        
        # استخراج البيانات
        parts = query.data.split('_')
        target_user_id = int(parts[2])
        points = int(parts[3])
        
        # إضافة النقاط
        if self.db.add_points(target_user_id, points):
            user_data = self.db.get_user(target_user_id)
            
            # إرسال إشعار للمستخدم
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"🎉 <b>تم إضافة نقاط لحسابك!</b>\n\n"
                         f"➕ النقاط المضافة: {points}\n"
                         f"💰 رصيدك الحالي: {user_data['points']} نقطة\n\n"
                         f"شكراً لاستخدامك البوت! ❤️",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
            
            await query.edit_message_text(
                f"✅ <b>تمت العملية بنجاح!</b>\n\n"
                f"تم إضافة {points} نقطة للمستخدم #{target_user_id}\n"
                f"💰 رصيده الحالي: {user_data['points']} نقطة",
                parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text("❌ حدث خطأ! حاول مرة أخرى")
    
    async def deduct_points_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بدء عملية خصم نقاط"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📝 <b>خصم نقاط من المستخدم</b>\n\n"
            "أرسل معرف المستخدم (User ID) أو اليوزرنيم (@username)\n\n"
            "مثال:\n"
            "• <code>123456789</code>\n"
            "• <code>@username</code>\n\n"
            "أو أرسل /cancel للإلغاء",
            parse_mode=ParseMode.HTML
        )
        
        return ADMIN_WAITING_DEDUCT_USER
    
    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات مفصلة"""
        query = update.callback_query
        await query.answer()
        
        # قراءة البيانات
        with open('data/users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        with open('data/purchases.json', 'r', encoding='utf-8') as f:
            purchases = json.load(f)
        
        # حساب الإحصائيات
        total_users = len(users)
        total_purchases = sum(len(v) for v in purchases.values())
        total_points = sum(u.get('points', 0) for u in users.values())
        
        # المستخدمين النشطين (لديهم مشتريات)
        active_users = len([u for u in users.values() if u.get('purchases', 0) > 0])
        
        # إجمالي النقاط المستخدمة
        total_spent = sum(
            purchase.get('price', 0)
            for user_purchases in purchases.values()
            for purchase in user_purchases
        )
        
        text = (
            f"📊 <b>إحصائيات البوت الشاملة</b>\n\n"
            f"👥 <b>المستخدمين:</b>\n"
            f"  • إجمالي المستخدمين: {total_users}\n"
            f"  • المستخدمين النشطين: {active_users}\n"
            f"  • نسبة النشاط: {(active_users/total_users*100) if total_users > 0 else 0:.1f}%\n\n"
            f"🛍 <b>المشتريات:</b>\n"
            f"  • إجمالي المشتريات: {total_purchases}\n"
            f"  • متوسط المشتريات للمستخدم: {(total_purchases/active_users) if active_users > 0 else 0:.1f}\n\n"
            f"💰 <b>النقاط:</b>\n"
            f"  • إجمالي النقاط المتاحة: {total_points:,}\n"
            f"  • إجمالي النقاط المستخدمة: {total_spent:,}\n"
            f"  • إجمالي النقاط الكلي: {(total_points + total_spent):,}\n\n"
            f"📅 التحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def users_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض قائمة المستخدمين"""
        query = update.callback_query
        await query.answer()
        
        with open('data/users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # ترتيب حسب تاريخ الانضمام
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get('join_date', ''),
            reverse=True
        )[:10]  # أحدث 10 مستخدمين
        
        text = "👥 <b>آخر 10 مستخدمين:</b>\n\n"
        
        for i, (uid, data) in enumerate(sorted_users, 1):
            text += (
                f"{i}. {data['first_name']}\n"
                f"   🆔 <code>{uid}</code>\n"
                f"   💰 {data.get('points', 0)} نقطة | "
                f"🛍 {data.get('purchases', 0)} مشترية\n\n"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def top_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض أعلى الأرصدة"""
        query = update.callback_query
        await query.answer()
        
        with open('data/users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        # ترتيب حسب النقاط
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get('points', 0),
            reverse=True
        )[:10]
        
        text = "💰 <b>أعلى 10 أرصدة:</b>\n\n"
        
        medals = ["🥇", "🥈", "🥉"] + ["👤"] * 7
        
        for i, (uid, data) in enumerate(sorted_users):
            text += (
                f"{medals[i]} {data['first_name']}\n"
                f"   💵 {data.get('points', 0):,} نقطة\n"
                f"   🛍 {data.get('purchases', 0)} مشترية\n\n"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def recent_purchases(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض آخر المشتريات"""
        query = update.callback_query
        await query.answer()
        
        with open('data/purchases.json', 'r', encoding='utf-8') as f:
            all_purchases = json.load(f)
        
        # جمع وترتيب جميع المشتريات
        purchases_list = []
        for uid, user_purchases in all_purchases.items():
            for purchase in user_purchases:
                purchase['user_id'] = uid
                purchases_list.append(purchase)
        
        # ترتيب حسب التاريخ
        sorted_purchases = sorted(
            purchases_list,
            key=lambda x: x.get('date', ''),
            reverse=True
        )[:5]
        
        text = "🛍 <b>آخر 5 مشتريات:</b>\n\n"
        
        for purchase in sorted_purchases:
            text += (
                f"📱 {purchase.get('service', 'N/A').title()}\n"
                f"🌍 {purchase.get('country', 'N/A').title()}\n"
                f"👤 المشتري: #{purchase.get('user_id')}\n"
                f"💰 {purchase.get('price', 0)} نقطة\n"
                f"📅 {purchase.get('date', 'N/A')[:16]}\n\n"
            )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )
    
    async def cancel_admin_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء العملية الإدارية"""
        await update.message.reply_text(
            "❌ تم الإلغاء!\n\n"
            "استخدم /start للعودة للقائمة الرئيسية"
        )
        return ConversationHandler.END

# دالة لإنشاء معالج المحادثة للمطور
def create_admin_conversation_handler(admin_handler):
    """إنشاء معالج محادثة لوحة المطور"""
    
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_handler.add_points_start, pattern='^admin_add_points$'),
            CallbackQueryHandler(admin_handler.deduct_points_start, pattern='^admin_deduct_points$'),
        ],
        states={
            ADMIN_WAITING_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler.add_points_user_received)
            ],
            ADMIN_WAITING_POINTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler.add_points_amount_received)
            ],
            ADMIN_WAITING_DEDUCT_USER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler.add_points_user_received)
            ],
            ADMIN_WAITING_DEDUCT_POINTS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handler.add_points_amount_received)
            ],
        },
        fallbacks=[
            CommandHandler('cancel', admin_handler.cancel_admin_action)
        ],
        name="admin_conversation",
        persistent=False
    )
