# 🚀 VPN Hub Premium Bot

ربات پیشرفته جمع‌آوری و توزیع خودکار کانفیگ‌های VPN با ویژگی‌های حرفه‌ای

## ✨ ویژگی‌های نسخه جدید

### 🧠 هوش مصنوعی
- ✅ **شناسایی تکراری هوشمند**: جلوگیری از ارسال کانفیگ‌های تکراری با فرمت متفاوت
- ✅ **سیستم امتیازدهی**: رتبه‌بندی کانفیگ‌ها بر اساس کیفیت (0-100)
- ✅ **تست واقعی سرعت**: اندازه‌گیری دقیق latency واقعی (نه فقط ping)

### 🌍 جغرافیا
- ✅ **نمایش پرچم کشورها**: تشخیص خودکار موقعیت سرور (🇺🇸 🇳🇱 🇩🇪)
- ✅ **GeoIP Database**: پشتیبانی از دیتابیس GeoLite2

### 🔗 اشتراک
- ✅ **لینک Subscription**: تولید لینک اشتراک استاندارد برای V2Ray/Clash
- ✅ **فرمت Base64**: سازگار با تمام کلاینت‌ها

### 📱 Progressive Web App (PWA)
- ✅ **نصب به‌عنوان اپ**: قابلیت نصب روی موبایل/دسکتاپ
- ✅ **کار آفلاین**: دسترسی بدون اینترنت با Service Worker
- ✅ **طراحی مدرن**: UI/UX حرفه‌ای و ریسپانسیو

---

## 📋 پیش‌نیازها

1. **حساب GitHub** با مخزن فعال
2. **API تلگرام** از [my.telegram.org](https://my.telegram.org)
3. **Session String** (دو تا برای عملکرد بهتر)

---

## 🛠️ نصب و راه‌اندازی

### مرحله 1: کلون مخزن
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### مرحله 2: تنظیم GitHub Secrets
به `Settings` → `Secrets and variables` → `Actions` برو و این مقادیر رو اضافه کن:

| نام Secret | توضیحات | مثال |
|-----------|---------|------|
| `API_ID` | شناسه API از my.telegram.org | `12345678` |
| `API_HASH` | هش API از my.telegram.org | `abcdef123456...` |
| `SESSION_STRING` | سشن اول (نیمه اول ساعت) | `1BVt...` |
| `SESSION_STRING_2` | سشن دوم (نیمه دوم ساعت) - اختیاری | `1BVt...` |

### مرحله 3: آپلود فایل‌ها
```bash
# کپی فایل‌های ربات
cp bot_premium_v2.py main.py

# کپی فایل workflow
mkdir -p .github/workflows
cp bot.yml .github/workflows/

# Push به GitHub
git add .
git commit -m "🎉 Setup Premium VPN Bot"
git push origin main
```

### مرحله 4: فعال‌سازی GitHub Actions
1. برو به تب **Actions** در مخزن
2. اگر غیرفعال است، روی **Enable workflows** کلیک کن
3. اولین اجرا: **Run workflow** → **Run workflow**

---

## ⚙️ تنظیمات پیشرفته

### تغییر کانال مقصد
در فایل `main.py`:
```python
destination_channel = '@YOUR_CHANNEL'
```

### تنظیم زمان‌بندی
در `bot.yml`:
```yaml
schedule:
  - cron: '0 * * * *'   # هر ساعت
  - cron: '30 * * * *'  # نیمه هر ساعت
```

### غیرفعال کردن GeoIP
اگر نمی‌خوای پرچم کشورها نمایش داده بشه:
```python
GEOIP_AVAILABLE = False
```

### تنظیم تست سرعت
```python
ENABLE_REAL_TEST = True      # فعال/غیرفعال
REAL_TEST_TIMEOUT = 5        # تایم‌اوت (ثانیه)
```

---

## 📊 ساختار فایل‌های خروجی

```
📁 Repository Root
├── 📄 index.html          # صفحه اصلی PWA
├── 📄 manifest.json       # تنظیمات PWA
├── 📄 sw.js              # Service Worker
├── 📄 subscription.txt    # لینک اشتراک Base64
├── 📄 data.json          # دیتابیس کانفیگ‌ها
└── 📄 main.py            # کد اصلی ربات
```

---

## 🌐 نمایش سایت

### روش 1: GitHub Pages
1. `Settings` → `Pages`
2. Source: `Deploy from a branch`
3. Branch: `main` → `/root`
4. Save

سایت در `https://YOUR_USERNAME.github.io/YOUR_REPO` فعال می‌شه.

### روش 2: Netlify/Vercel
```bash
# Netlify
netlify deploy --dir=. --prod

# Vercel
vercel --prod
```

---

## 📱 استفاده از لینک اشتراک

### در V2Ray/V2RayNG
1. باز کردن اپ
2. `+` → `Import from URL`
3. آدرس: `https://YOUR_DOMAIN/subscription.txt`

### در Clash
```yaml
proxy-providers:
  premium:
    type: http
    url: https://YOUR_DOMAIN/subscription.txt
    interval: 3600
```

---

## 🐛 عیب‌یابی

### ربات اجرا نمی‌شه
```bash
# بررسی Logs در Actions
1. تب Actions
2. کلیک روی آخرین Run
3. بررسی خطاها در هر Step
```

### GeoIP کار نمی‌کنه
```bash
# دانلود دستی دیتابیس
wget https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-Country.mmdb

# آپلود به ریپو
git add GeoLite2-Country.mmdb
git commit -m "Add GeoIP database"
git push
```

### سایت نمایش داده نمی‌شه
1. بررسی GitHub Pages فعال باشه
2. چک کنید `index.html` در root باشه
3. منتظر 5 دقیقه برای deploy اولیه

---

## 📈 مثال خروجی

### پیام تلگرام
```
🔮 VLESS 🇳🇱

vless://uuid@server.nl:443?...

📊 🟢 عالی • 45ms • کیفیت: 95/100
#vless #v2rayNG
━━━━━━━━━━━━━━━━
🗓 2026/02/06 • 🕐 14:30
📡 منبع: [Free VPN](...)
🔗 @myvpn1404
```

### صفحه وب
![Preview](https://via.placeholder.com/800x600/0f172a/38bdf8?text=VPN+Hub+Premium)

---

## 🔒 امنیت

- ✅ Session String‌ها در GitHub Secrets
- ✅ دسترسی محدود به مخزن خصوصی
- ✅ بدون ذخیره اطلاعات حساس در کد

---

## 📝 لایسنس

MIT License - استفاده آزاد با ذکر منبع

---

## 🤝 مشارکت

1. Fork کن
2. Feature branch بساز (`git checkout -b feature/amazing`)
3. Commit کن (`git commit -m 'Add amazing feature'`)
4. Push کن (`git push origin feature/amazing`)
5. Pull Request باز کن

---

## 💬 پشتیبانی

- 🐛 گزارش باگ: [Issues](https://github.com/YOUR_USERNAME/YOUR_REPO/issues)
- 💡 پیشنهادات: [Discussions](https://github.com/YOUR_USERNAME/YOUR_REPO/discussions)
- 📧 ایمیل: your-email@example.com

---

## 🌟 ستاره بدید!

اگر این پروژه به دردتون خورد، یه ⭐ بهش بدید!

---

**ساخته شده با ❤️ توسط [Your Name](https://github.com/YOUR_USERNAME)**
