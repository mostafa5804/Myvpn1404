# 🔮 V2Ray Collector & Dashboard Hub

### ربات هوشمند جمع‌آوری، تست و انتشار کانفیگ‌های V2Ray و پروکسی  
**Powerful Python Automation with 24h Persistent History & Web Dashboard**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)
![Telethon](https://img.shields.io/badge/Telethon-Async-E34F26.svg?style=for-the-badge&logo=telegram)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF.svg?style=for-the-badge&logo=github-actions)
![HTML5](https://img.shields.io/badge/Dashboard-Responsive-E34F26.svg?style=for-the-badge&logo=html5)
![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)

🌐 **Demo:** https://mostafa5804.github.io/Myvpn1404  
🐞 **Issues:** https://github.com/mostafa5804/Myvpn1404/issues  
📢 **Telegram:** https://t.me/myvpn1404

---

## 📖 معرفی پروژه (Overview)

این پروژه یک **ربات تمام‌خودکار (Full-Stack Automation)** است که با استفاده از کتابخانه `Telethon` و قدرت `GitHub Actions`، جمع‌آوری، تست و انتشار کانفیگ‌های V2Ray و پروکسی را انجام می‌دهد.

برخلاف ربات‌های معمولی، این سیستم دارای **حافظه ۲۴ ساعته** است و علاوه بر انتشار در تلگرام، یک **وب‌سایت حرفه‌ای (Dashboard)** برای نمایش و مدیریت کانفیگ‌ها تولید می‌کند.

### 🌟 چرا این پروژه متمایز است؟
- **بدون نیاز به سرور:** اجرا کاملاً روی GitHub Actions  
- **پایداری داده:** ذخیره و پالایش اطلاعات تا ۲۴ ساعت در `data.json`  
- **خروجی دوگانه:** تلگرام + وب‌سایت ریسپانسیو  

---

## ✨ ویژگی‌های کلیدی (Key Features)

### 🤖 هسته ربات
- ⚡ تست پینگ واقعی (TCP Ping)
- 🔄 چرخه هوشمند ۸۰ دقیقه‌ای برای مدیریت منابع
- 💾 دیتابیس JSON با حذف خودکار داده‌های قدیمی
- 🛡️ تشخیص نت ملی (Intranet) و سرورهای فیلترشده

### 📢 تلگرام
- 🎨 استایل مینیمال و خوانا
- 📦 ارسال گروهی پروکسی‌ها برای جلوگیری از اسپم
- 📋 کپی سریع کانفیگ‌ها با فرمت Mono
- 🔗 اصلاح لینک کانال‌های منبع

### 🌐 وب‌سایت (Dashboard)
- 📱 طراحی Mobile-First
- 🌑 Dark Mode
- 🔍 جستجوی پیشرفته (کشور، پروتکل، کانال)
- 📷 تولید QR Code آنی
- 📑 تب‌بندی کانفیگ، پروکسی و فایل‌ها

---

## 📸 پیش‌نمایش (Screenshots)

| Web Dashboard | Telegram Style |
|--------------|----------------|
| <img src="web.jpg" width="250"> | <img src="telegram.jpg" width="250"> |

---

## 🛠 نصب و راه‌اندازی (Installation)

### پیش‌نیازها
- اکانت GitHub  
- `API_ID` و `API_HASH` از my.telegram.org  
- Session String تلگرام (Telethon)

### مراحل
1. مخزن را Fork کنید  
2. در مسیر  
   `Settings → Secrets and variables → Actions`  
   مقادیر زیر را اضافه کنید:
   - `API_ID`
   - `API_HASH`
   - `SESSION_STRING`
3. GitHub Pages را از مسیر  
   `Settings → Pages`  
   روی **GitHub Actions** فعال کنید
4. Workflow را اجرا کنید (یا منتظر اجرای زمان‌بندی بمانید)

---
🤝 مشارکت (Contributing)
اگر ایده‌ای برای بهبود ربات دارید یا باگی پیدا کردید:

مخزن را Fork کنید.

تغییرات خود را اعمال کنید.

یک Pull Request ارسال کنید.

<div align="center">

Developed with ❤️ by [Mostafa]


Don't forget to star ⭐ the repo if you like it!

</div>
---

## ⚙️ ساختار پروژه

```text
📂 Repo Root
├── main.py          # هسته ربات
├── data.json        # دیتابیس موقت
├── index.html       # داشبورد وب
├── web.jpg
├── telegram.jpg
└── .github/workflows
    └── bot.yml      # GitHub Actions
