#!/bin/bash

# ═══════════════════════════════════════════════════════════
# سكريبت التنصيب التلقائي
# Automatic Installation Script
# ═══════════════════════════════════════════════════════════

clear
echo "════════════════════════════════════════════════════"
echo "🤖 مرحباً بك في معالج تنصيب بوت الأرقام الافتراضية"
echo "Welcome to Virtual Numbers Bot Installer"
echo "════════════════════════════════════════════════════"
echo ""

# دالة للسؤال
ask_question() {
    echo ""
    echo "❓ $1"
    read -p "➜ " answer
    echo "$answer"
}

# التحقق من الصلاحيات
if [[ $EUID -ne 0 ]] && [[ "$1" != "--user" ]]; then
   echo "⚠️  هذا السكريبت يحتاج صلاحيات root لتثبيت المتطلبات"
   echo "استخدم: sudo ./install.sh"
   echo "أو: ./install.sh --user (للتثبيت بدون صلاحيات root)"
   exit 1
fi

echo "الخطوة 1/5: تحديث النظام..."
apt-get update -qq

echo "الخطوة 2/5: تثبيت Python 3 و pip..."
apt-get install -y python3 python3-pip git screen -qq

echo "الخطوة 3/5: تثبيت المكتبات المطلوبة..."
pip3 install -r requirements.txt

echo "الخطوة 4/5: إنشاء مجلدات المشروع..."
mkdir -p data logs

echo "الخطوة 5/5: إعداد الإعدادات..."

# طلب البيانات من المستخدم
echo ""
echo "════════════════════════════════════════════════════"
echo "📝 الآن سنقوم بإعداد البوت"
echo "════════════════════════════════════════════════════"

BOT_TOKEN=$(ask_question "أدخل توكن البوت من @BotFather:")
BOT_USERNAME=$(ask_question "أدخل يوزرنيم البوت (مع @):")
ADMIN_ID=$(ask_question "أدخل آيدي التليجرام الخاص بك:")
CHANNEL=$(ask_question "أدخل يوزر قناة الاشتراك الإجباري (مع @):")
PURCHASES_CHANNEL=$(ask_question "أدخل يوزر قناة المشتريات (مع @):")
SUPPORT=$(ask_question "أدخل يوزر الدعم (مع @):")

# تعديل ملف config.py
echo ""
echo "⚙️  تطبيق الإعدادات..."

# نسخة احتياطية
cp config.py config.py.backup

# تعديل القيم
sed -i "s/BOT_TOKEN = \".*\"/BOT_TOKEN = \"$BOT_TOKEN\"/" config.py
sed -i "s/BOT_USERNAME = \".*\"/BOT_USERNAME = \"$BOT_USERNAME\"/" config.py
sed -i "s/ADMIN_IDS = \[.*\]/ADMIN_IDS = [$ADMIN_ID]/" config.py
sed -i "s/CHANNEL_USERNAME = \".*\"/CHANNEL_USERNAME = \"$CHANNEL\"/" config.py
sed -i "s/PURCHASES_CHANNEL = \".*\"/PURCHASES_CHANNEL = \"$PURCHASES_CHANNEL\"/" config.py
sed -i "s/SUPPORT_USERNAME = \".*\"/SUPPORT_USERNAME = \"$SUPPORT\"/" config.py

# جعل السكريبتات قابلة للتنفيذ
chmod +x start.sh

echo ""
echo "════════════════════════════════════════════════════"
echo "✅ تم التنصيب بنجاح!"
echo "════════════════════════════════════════════════════"
echo ""
echo "📋 ملخص الإعدادات:"
echo "   🤖 توكن البوت: ${BOT_TOKEN:0:20}..."
echo "   👤 يوزرنيم البوت: $BOT_USERNAME"
echo "   👑 آيدي المطور: $ADMIN_ID"
echo "   📢 قناة الاشتراك: $CHANNEL"
echo "   🛍 قناة المشتريات: $PURCHASES_CHANNEL"
echo "   💬 الدعم: $SUPPORT"
echo ""
echo "════════════════════════════════════════════════════"
echo "🚀 لتشغيل البوت استخدم:"
echo "   ./start.sh"
echo ""
echo "أو للتشغيل في الخلفية:"
echo "   screen -S telegram-bot"
echo "   ./start.sh"
echo "   (اضغط Ctrl+A ثم D للخروج)"
echo "════════════════════════════════════════════════════"
echo ""
echo "📚 للمزيد من المعلومات، راجع ملف README.md"
echo ""
