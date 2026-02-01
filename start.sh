#!/bin/bash

# ═══════════════════════════════════════════════════════════
# سكريبت تشغيل بوت بيع الأرقام الافتراضية
# Virtual Numbers Bot Launcher
# ═══════════════════════════════════════════════════════════

echo "════════════════════════════════════════════════════"
echo "🤖 بوت بيع الأرقام الافتراضية"
echo "Virtual Numbers Selling Bot"
echo "════════════════════════════════════════════════════"
echo ""

# التحقق من Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مثبت!"
    echo "قم بتثبيته أولاً: sudo apt install python3 python3-pip"
    exit 1
fi

echo "✅ Python 3 موجود"

# التحقق من pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 غير مثبت!"
    echo "قم بتثبيته: sudo apt install python3-pip"
    exit 1
fi

echo "✅ pip3 موجود"

# إنشاء مجلد البيانات
if [ ! -d "data" ]; then
    echo "📁 إنشاء مجلد البيانات..."
    mkdir -p data
fi

# التحقق من المكتبات
echo ""
echo "📦 التحقق من المكتبات المطلوبة..."

if ! python3 -c "import telegram" 2>/dev/null; then
    echo "📥 تثبيت المكتبات..."
    pip3 install -r requirements.txt
    echo "✅ تم تثبيت المكتبات بنجاح!"
else
    echo "✅ جميع المكتبات موجودة"
fi

# التحقق من ملف الإعدادات
if [ ! -f "config.py" ]; then
    echo ""
    echo "❌ ملف config.py غير موجود!"
    echo "قم بإنشائه أولاً"
    exit 1
fi

# التحقق من التوكن
if grep -q "ضع_توكن_البوت_هنا" config.py; then
    echo ""
    echo "⚠️  تحذير: لم تقم بتعديل التوكن في config.py!"
    echo "افتح الملف وضع توكن البوت الخاص بك"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════"
echo "🚀 تشغيل البوت..."
echo "════════════════════════════════════════════════════"
echo ""
echo "لإيقاف البوت: اضغط Ctrl + C"
echo ""

# تشغيل البوت
python3 bot.py

# في حالة توقف البوت
echo ""
echo "════════════════════════════════════════════════════"
echo "⚠️  البوت توقف عن العمل"
echo "════════════════════════════════════════════════════"
