import os
import re
import jdatetime
import pytz
import asyncio
import json
import base64
import socket
import random
import time
import sys
import html
import requests
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import FloodWaitError

# =============================================================================
# 1. تنظیمات و پیکربندی
# =============================================================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

PING_TIMEOUT = 1.5  # کاهش تایم‌اوت برای سرعت بیشتر
DATA_FILE = 'data.json'
SUB_FILE = 'sub.txt'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
MAX_MESSAGE_AGE_MINUTES = 90

ALL_CHANNELS = [
    '@KioV2ray', '@Npvtunnel_vip', '@planB_net', '@Free_Nettm', '@mypremium98',
    '@mitivpn', '@iSeqaro', '@configraygan', '@shankamil', '@xsfilternet',
    '@varvpn1', '@iP_CF', '@cooonfig', '@DeamNet', '@anty_filter',
    '@vpnboxiran', '@Merlin_ViP', '@BugFreeNet', '@cicdoVPN', '@Farda_Ai',
    '@Awlix_ir', '@proSSH', '@vpn_proxy_custom', '@Free_HTTPCustom',
    '@sinavm', '@Amir_Alternative_Official', '@StayconnectedVPN', '@BINNER_IRAN',
    '@IranianMinds', '@vpn11ir', '@NetAccount', '@mitiivpn2', '@isharewin',
    '@v2rays_ha', '@iroproxy', '@ProxyMTProto',
    '@darkproxy', '@configs_freeiran', '@v2rayvpnchannel'
]

allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')
IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

# کش برای جلوگیری از درخواست‌های تکراری به API پرچم
IP_CACHE = {}

# =============================================================================
# 2. توابع هوشمند (Unique Key, GeoIP, Parsing)
# =============================================================================

def get_ip_info(host):
    """دریافت پرچم کشور بر اساس IP"""
    if not host or host in IRAN_IP_PREFIXES:
        return "🇮🇷", "Iran"
    
    # اگر هاست یک دامنه است، سعی کنیم IP آن را بگیریم (با خطا هندلینگ)
    target_ip = host
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
        try:
            target_ip = socket.gethostbyname(host)
        except:
            return "🏳️", "Unknown"

    if target_ip in IP_CACHE:
        return IP_CACHE[target_ip]

    try:
        # استفاده از API رایگان (محدودیت ۴۵ درخواست در دقیقه دارد)
        response = requests.get(f'http://ip-api.com/json/{target_ip}?fields=countryCode,country', timeout=2)
        if response.status_code == 200:
            data = response.json()
            code = data.get('countryCode', '')
            country = data.get('country', 'Unknown')
            
            # تبدیل کد کشور به ایموجی پرچم
            flag_offset = 127397
            flag = ''.join([chr(ord(c) + flag_offset) for c in code.upper()]) if code else "🏳️"
            
            IP_CACHE[target_ip] = (flag, country)
            return flag, country
    except:
        pass
    
    return "🏳️", "Unknown"

def extract_unique_key(config_str):
    """
    استخراج یک شناسه یکتا برای کانفیگ جهت حذف تکراری‌های هوشمند.
    شناسه شامل: IP + Port + Protocol
    """
    try:
        # 1. VMess (JSON inside Base64)
        if config_str.startswith('vmess://'):
            b64 = config_str.replace('vmess://', '')
            try:
                # اصلاح پدینگ base64
                padded = b64 + '=' * (-len(b64) % 4)
                decoded = base64.b64decode(padded).decode('utf-8')
                data = json.loads(decoded)
                return f"{data.get('add')}:{data.get('port')}"
            except:
                return config_str # اگر دیکد نشد، کل رشته را برگردان

        # 2. VLESS / Trojan / SS (URI Scheme)
        # الگوی کلی: protocol://user@host:port...
        match = re.search(r'://.*?@([^:/]+):(\d+)', config_str)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
        
        # fallback for simple patterns
        match_simple = re.search(r'://([^:/]+):(\d+)', config_str)
        if match_simple:
            return f"{match_simple.group(1)}:{match_simple.group(2)}"

        return config_str
    except:
        return config_str

def get_host_port(link, type='config'):
    """استخراج هاست و پورت برای پینگ"""
    try:
        if type == 'proxy':
            m = re.search(r"server=([\w\.-]+)&port=(\d+)", link)
            if m: return m.group(1), int(m.group(2))
        else:
            if link.startswith('vmess://'):
                # دیکد vmess برای گرفتن هاست
                b64 = link.replace('vmess://', '')
                padded = b64 + '=' * (-len(b64) % 4)
                d = json.loads(base64.b64decode(padded).decode('utf-8'))
                return d['add'], int(d['port'])
            else:
                # سایر پروتکل‌ها
                m = re.search(r"@([\w\.-]+):(\d+)", link)
                if m: return m.group(1), int(m.group(2))
                # حالت‌هایی که @ ندارند (مثل بعضی ss ها)
                m2 = re.search(r"://(?:[^@]+@)?([\w\.-]+):(\d+)", link)
                if m2: return m2.group(1), int(m2.group(2))
    except:
        pass
    return None, None

# =============================================================================
# 3. توابع اصلی ربات
# =============================================================================
def load_data():
    if not os.path.exists(DATA_FILE): return {'configs': [], 'proxies': [], 'files': []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        limit = time.time() - (KEEP_HISTORY_HOURS * 3600)
        return {
            'configs': [c for c in data.get('configs', []) if c.get('ts', 0) > limit],
            'proxies': [p for p in data.get('proxies', []) if p.get('ts', 0) > limit],
            'files': [f for f in data.get('files', []) if f.get('ts', 0) > limit]
        }
    except: return {'configs': [], 'proxies': [], 'files': []}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def get_batch_info():
    minute = datetime.now(iran_tz).minute
    target_session = session_2 if session_2 else session_1
    if minute < 30:
        return ALL_CHANNELS[:20], "اول", target_session
    else:
        return ALL_CHANNELS[20:], "دوم", target_session

def clean_title(t):
    if not t: return "Channel"
    return re.sub(r'[\[\]\(\)\*`_]', '', str(t)).strip()

async def check_connection(host, port):
    """تست اتصال دقیق با زمان‌سنجی بالا"""
    try:
        start_time = time.perf_counter() # دقت میکروثانیه
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), 
            timeout=PING_TIMEOUT
        )
        end_time = time.perf_counter()
        writer.close()
        try:
            await writer.wait_closed()
        except: pass
        
        latency = int((end_time - start_time) * 1000)
        return latency
    except:
        return None

async def process_item(link, type='config'):
    """بررسی وضعیت، پینگ و کشور"""
    host, port = get_host_port(link, type)
    if not host or not port:
        return None, None, None, None

    latency = await check_connection(host, port)
    
    if latency is None:
        # چک کردن اینترانت
        try:
            if any(host.startswith(p) for p in IRAN_IP_PREFIXES):
                return "🔵 اینترانت", None, "🇮🇷", "Iran"
        except: pass
        return None, None, None, None # آفلاین

    flag, country = get_ip_info(host)
    
    status = "🟢 عالی" if latency < 200 else "🟡 خوب" if latency < 500 else "🟠 متوسط"
    return status, latency, flag, country

# =============================================================================
# 4. بدنه اجرایی (Main)
# =============================================================================
target_channels, batch_name, active_session = get_batch_info()
if not active_session: sys.exit(1)

client = TelegramClient(StringSession(active_session), api_id, api_hash)

async def main():
    try:
        await client.start()
        print(f"✅ ربات متصل شد ({batch_name})")
        
        hist = load_data()
        
        # ساخت دیکشنری هوشمند برای جلوگیری از تکراری‌ها
        # کلید: Unique Key, مقدار: True
        unique_fingerprints = set()
        
        for c in hist['configs']: 
            k = extract_unique_key(c['config'])
            unique_fingerprints.add(k)
        
        # برای فایل و پروکسی همچنان از رشته کامل استفاده می‌کنیم چون پارس کردنشان سخت است
        sent_hashes = set()
        for p in hist['proxies']: sent_hashes.add(p['link'])
        for f in hist['files']: sent_hashes.add(f['name'])

        print(f"🔄 {len(unique_fingerprints)} کانفیگ یکتا در حافظه.")
        
        new_conf = []
        new_prox = []
        new_file = []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)

        for channel_str in target_channels:
            try:
                await asyncio.sleep(random.randint(5, 10)) # تاخیر کمتر برای سرعت
                try:
                    entity = await client.get_entity(channel_str)
                    msgs = await client.get_messages(entity, limit=15)
                except: continue

                title = getattr(entity, 'title', channel_str)
                
                for m in msgs:
                    if m.date < cutoff_time: continue
                    link = f"https://t.me/{channel_str[1:]}/{m.id}"

                    if m.text:
                        # 1. Configs
                        configs = re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text)
                        for c in configs:
                            u_key = extract_unique_key(c)
                            if u_key not in unique_fingerprints:
                                stat, lat, flag, country = await process_item(c, 'config')
                                if stat:
                                    prot = c.split('://')[0].upper()
                                    # ارسال به کانال (به فرمت ساده)
                                    clean_c = c.replace('`', '')
                                    caption = (
                                        f"{flag} **{prot}** | {country}\n"
                                        f"📶 Ping: {lat}ms\n\n"
                                        f"```{clean_c}```\n"
                                        f"🔗 [Source]({link})"
                                    )
                                    try:
                                        sent = await client.send_message(destination_channel, caption, link_preview=False)
                                        t_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                                        
                                        new_conf.append({
                                            'protocol': prot, 'config': c, 'latency': lat, 
                                            'channel': title, 't_link': t_link, 
                                            'flag': flag, 'country': country,
                                            'ts': time.time()
                                        })
                                        unique_fingerprints.add(u_key)
                                    except Exception as e: print(f"Error sending config: {e}")

                        # 2. Proxies
                        proxies = re.findall(r"https://t.me/proxy\?[^\s\n]+", m.text)
                        for p in proxies:
                            clean_p = p.replace('https://t.me/proxy', 'tg://proxy')
                            if clean_p not in sent_hashes:
                                stat, lat, flag, country = await process_item(clean_p, 'proxy')
                                if stat:
                                    # پروکسی‌ها معمولا به صورت دسته‌ای ارسال می‌شوند، اینجا یکی یکی هندل می‌کنیم
                                    # برای دیتابیس
                                    m_search = re.search(r"server=([\w\.-]+)&port=(\d+)", clean_p)
                                    key_p = f"{m_search.group(1)}:{m_search.group(2)}" if m_search else str(time.time())
                                    
                                    new_prox.append({
                                        'key': key_p, 'link': clean_p, 'channel': title, 
                                        't_link': '#', 'latency': lat, 'flag': flag, 
                                        'ts': time.time()
                                    })
                                    sent_hashes.add(clean_p)

                    # 3. Files
                    if m.file and any(m.file.name.endswith(x) for x in allowed_extensions if m.file.name):
                        if m.file.name not in sent_hashes:
                            try:
                                await client.send_file(destination_channel, m.file, caption=f"📂 {m.file.name}\n🔗 [Source]({link})")
                                new_file.append({
                                    'name': m.file.name, 'ext': m.file.name.split('.')[-1], 
                                    'channel': title, 'link': link, 'ts': time.time()
                                })
                                sent_hashes.add(m.file.name)
                            except: pass

            except Exception as e:
                print(f"Error in loop {channel_str}: {e}")

        # =====================================================================
        # 5. ادغام داده‌ها و تولید خروجی
        # =====================================================================
        
        # ادغام کانفیگ‌ها
        all_configs = hist['configs'] + new_conf
        # مرتب‌سازی بر اساس زمان (جدیدترین اول) و حذف قدیمی‌ها در لود انجام شده اما اینجا سورت نهایی
        all_configs.sort(key=lambda x: x['ts'], reverse=True)
        # نگه داشتن فقط 300 تای آخر برای فایل جیسون
        all_configs = all_configs[:300]

        # ادغام پروکسی‌ها
        all_proxies = hist['proxies'] + new_prox
        all_proxies.sort(key=lambda x: x['ts'], reverse=True)
        all_proxies = all_proxies[:100]
        
        # ادغام فایل‌ها
        all_files = hist['files'] + new_file
        all_files.sort(key=lambda x: x['ts'], reverse=True)
        all_files = all_files[:50]

        save_data({'configs': all_configs, 'proxies': all_proxies, 'files': all_files})
        
        # --- تولید لینک اشتراک (Subscription) ---
        print("🔥 Generating Subscription Link...")
        sub_content = ""
        for c in all_configs:
            # فقط کانفیگ‌های متنی وارد اشتراک شوند
            if c['config'].startswith(('vmess', 'vless', 'trojan', 'ss', 'hy2', 'tuic')):
                # افزودن نام کانال به عنوان نام کانفیگ (Remark)
                # این کار پیچیده است چون باید جیسون یا رشته تغییر کند. 
                # برای سادگی و جلوگیری از خرابی کانفیگ، خود کانفیگ خام را اضافه میکنیم.
                sub_content += c['config'] + "\n"
        
        # انکود Base64 برای لینک اشتراک
        sub_b64 = base64.b64encode(sub_content.encode('utf-8')).decode('utf-8')
        with open(SUB_FILE, 'w', encoding='utf-8') as f:
            f.write(sub_b64)

        # --- تولید فایل‌های PWA ---
        print("📱 Generating PWA Files...")
        
        manifest_content = {
            "name": "VPN Hub Premium",
            "short_name": "VPN Hub",
            "start_url": "./index.html",
            "display": "standalone",
            "background_color": "#0f172a",
            "theme_color": "#0f172a",
            "description": "Best Free VPN Collection",
            "icons": [
                {"src": "https://cdn-icons-png.flaticon.com/512/2099/2099192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "https://cdn-icons-png.flaticon.com/512/2099/2099192.png", "sizes": "512x512", "type": "image/png"}
            ]
        }
        with open('manifest.json', 'w') as f:
            json.dump(manifest_content, f)

        sw_content = """
        const CACHE_NAME = 'vpn-hub-v1';
        const urlsToCache = ['index.html', 'manifest.json'];
        self.addEventListener('install', event => {
            event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
        });
        self.addEventListener('fetch', event => {
            event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
        });
        """
        with open('sw.js', 'w') as f:
            f.write(sw_content)

        # --- تولید HTML نهایی ---
        print("📄 Generating HTML...")
        
        # تولید کارت‌های کانفیگ
        html_cards = ""
        for idx, cfg in enumerate(all_configs, 1):
            lat = cfg.get('latency', 999)
            flag = cfg.get('flag', '🏳️')
            country = cfg.get('country', 'Unknown')
            safe_conf = cfg['config'].replace("'", "\\'").replace('"', '\\"').replace('\n', '')
            
            ping_color = "text-green-400" if lat < 200 else "text-yellow-400" if lat < 500 else "text-red-400"
            
            html_cards += f"""
            <div class="card bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-sky-500 transition-all duration-300" data-ping="{lat}">
                <div class="flex justify-between items-center mb-3">
                    <div class="flex items-center gap-2">
                        <span class="text-2xl">{flag}</span>
                        <span class="font-bold text-sky-400 uppercase text-sm bg-sky-900/30 px-2 py-1 rounded">{cfg['protocol']}</span>
                    </div>
                    <div class="text-xs font-mono {ping_color} bg-slate-900 px-2 py-1 rounded">
                        {lat}ms
                    </div>
                </div>
                <div class="text-xs text-slate-400 mb-3 truncate">
                    📡 {cfg['channel']} • {country}
                </div>
                <div class="grid grid-cols-2 gap-2">
                    <button onclick="copyToClipboard('{safe_conf}')" class="bg-sky-600 hover:bg-sky-500 text-white py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center gap-2">
                        <i class="fas fa-copy"></i> کپی
                    </button>
                    <a href="{cfg.get('t_link', '#')}" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center">
                        <i class="fab fa-telegram"></i> کانال
                    </a>
                </div>
            </div>
            """

        # HTML اصلی با اضافه شدن PWA و Tailwind CDN (برای زیبایی و سبکی)
        now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
        full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium</title>
    
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#0f172a">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2099/2099192.png">

    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    
    <style>
        body {{ font-family: 'Vazirmatn', sans-serif; background-color: #0f172a; color: #f1f5f9; padding-bottom: 80px; -webkit-tap-highlight-color: transparent; }}
        .card {{ animation: fadeIn 0.5s ease-out; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        /* Scrollbar Hide */
        ::-webkit-scrollbar {{ width: 0px; background: transparent; }}
    </style>
</head>
<body>
    <header class="fixed top-0 w-full bg-slate-900/90 backdrop-blur-md border-b border-slate-700 z-50">
        <div class="max-w-md mx-auto px-4 h-16 flex justify-between items-center">
            <div>
                <h1 class="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-purple-500">VPN Hub</h1>
                <p class="text-[10px] text-slate-400">{now_str}</p>
            </div>
            <a href="sub.txt" class="bg-emerald-600/20 text-emerald-400 border border-emerald-600/50 px-3 py-1 rounded-full text-xs font-bold animate-pulse">
                <i class="fas fa-rss"></i> لینک اشتراک
            </a>
        </div>
    </header>

    <main class="max-w-md mx-auto pt-20 px-4">
        
        <div class="flex gap-2 mb-4 overflow-x-auto pb-2">
            <button onclick="filter('all')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700 active:bg-sky-600 active:text-white transition">همه</button>
            <button onclick="filter('vless')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">VLESS</button>
            <button onclick="filter('vmess')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">VMess</button>
            <button onclick="filter('trojan')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">Trojan</button>
        </div>

        <div id="grid" class="grid gap-3">
            {html_cards}
        </div>

        <div id="empty" class="hidden text-center py-10 text-slate-500">
            <i class="fas fa-search text-4xl mb-2"></i>
            <p>موردی یافت نشد</p>
        </div>
    </main>

    <nav class="fixed bottom-0 w-full bg-slate-900/95 backdrop-blur border-t border-slate-800 pb-safe z-50">
        <div class="max-w-md mx-auto grid grid-cols-3 h-16">
            <button onclick="window.scrollTo(0,0)" class="flex flex-col items-center justify-center text-sky-400">
                <i class="fas fa-bolt text-xl mb-1"></i>
                <span class="text-[10px]">کانفیگ</span>
            </button>
            <a href="{destination_channel.replace('@', 'https://t.me/')}" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400">
                <i class="fab fa-telegram text-xl mb-1"></i>
                <span class="text-[10px]">کانال</span>
            </a>
            <button onclick="location.reload()" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400">
                <i class="fas fa-sync text-xl mb-1"></i>
                <span class="text-[10px]">آپدیت</span>
            </button>
        </div>
    </nav>

    <div id="toast" class="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-emerald-600 text-white px-4 py-2 rounded-lg shadow-xl text-sm font-bold opacity-0 transition-opacity duration-300 pointer-events-none z-50">
        کپی شد! ✅
    </div>

    <script>
        // PWA Registration
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('sw.js');
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                const toast = document.getElementById('toast');
                toast.classList.remove('opacity-0');
                setTimeout(() => toast.classList.add('opacity-0'), 2000);
            }});
        }}

        function filter(type) {{
            const cards = document.querySelectorAll('.card');
            let hasItem = false;
            cards.forEach(card => {{
                const proto = card.querySelector('.uppercase').innerText.toLowerCase();
                if (type === 'all' || proto.includes(type)) {{
                    card.style.display = 'block';
                    hasItem = true;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            document.getElementById('empty').classList.toggle('hidden', hasItem);
        }}
    </script>
</body>
</html>
"""
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print("✅ عملیات با موفقیت به پایان رسید.")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())

