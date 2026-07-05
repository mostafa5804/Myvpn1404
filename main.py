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
import requests
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from telethon.tl.custom import Button  # اضافه شدن ماژول دکمه‌های شیشه‌ای

# ==========================================
# 1. Configuration
# ==========================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

PING_TIMEOUT = 5
DATA_FILE = 'data.json'
SUB_FILE = 'sub.txt'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
MAX_MESSAGE_AGE_MINUTES = 90
SUB_LINK_URL = "https://raw.githubusercontent.com/mostafa5804/Myvpn1404/refs/heads/main/sub.txt"
DASHBOARD_URL = "https://mostafa5804.github.io/Myvpn1404/"

ALL_CHANNELS = [
    '@net_melli1', '@xixv2ray', '@filtershekan_channel', '@ghalagyann', '@Proxymelimon',
    '@isor1n', '@Lizard_Vpn', '@KalbodTeam', '@TirexNet',
    '@Npvtunnel_vip', '@planB_net', '@Free_Nettm', '@mitivpn', '@configraygan', 
    '@xsfilternet', '@varvpn1', '@iP_CF', '@cooonfig', '@anty_filter',
    '@vpnboxiran', '@Merlin_ViP', '@BugFreeNet', '@cicdoVPN', '@Farda_Ai',
    '@Awlix_ir', '@proSSH', '@vpn_proxy_custom', '@Free_HTTPCustom', '@sinavm', 
    '@Amir_Alternative_Official', '@IranianMinds', '@NetAccount', '@isharewin', 
    '@iroproxy', '@ProxyMTProto', '@darkproxy', '@v2rayvpnchannel'
]
ALLOWED_EXTENSIONS = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')
IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

IP_CACHE = {}

# کامپایل عبارات منظم برای افزایش سرعت پردازش
REGEX_CONFIGS = re.compile(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|slipnet-enc):\/\/[^\s\n]+")
REGEX_PROXY = re.compile(r"https://t.me/proxy\?[^\s\n]+|tg://proxy\?[^\s\n]+")
REGEX_PROXY_PARAMS = re.compile(r"server=([\w\.-]+)&port=(\d+)")

# ==========================================
# 2. Helper Functions
# ==========================================

def get_ip_info(host):
    if not host or any(host.startswith(p) for p in IRAN_IP_PREFIXES):
        return "🇮🇷", "Iran"
    
    target_ip = host
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
        try:
            target_ip = socket.gethostbyname(host)
        except:
            return "🏳️", "Unknown"

    if target_ip in IP_CACHE:
        return IP_CACHE[target_ip]

    try:
        response = requests.get(f'http://ip-api.com/json/{target_ip}?fields=countryCode,country', timeout=2)
        if response.status_code == 200:
            data = response.json()
            code = data.get('countryCode', '')
            country = data.get('country', 'Unknown')
            flag_offset = 127397
            flag = ''.join([chr(ord(c) + flag_offset) for c in code.upper()]) if code else "🏳️"
            IP_CACHE[target_ip] = (flag, country)
            return flag, country
    except:
        pass
    
    return "🏳️", "Unknown"

def extract_unique_key(config_str):
    try:
        if config_str.startswith('vmess://'):
            b64 = config_str.replace('vmess://', '')
            try:
                padded = b64 + '=' * (-len(b64) % 4)
                decoded = base64.b64decode(padded).decode('utf-8')
                data = json.loads(decoded)
                return f"{data.get('add')}:{data.get('port')}"
            except:
                return config_str
        elif config_str.startswith('slipnet-enc://'):
            return config_str[:50]

        match = re.search(r'://.*?@([^:/]+):(\d+)', config_str)
        if match: return f"{match.group(1)}:{match.group(2)}"
        
        match_simple = re.search(r'://([^:/]+):(\d+)', config_str)
        if match_simple: return f"{match_simple.group(1)}:{match.group(2)}"

        return config_str
    except:
        return config_str

def get_host_port(link, type='config'):
    try:
        if type == 'proxy':
            m = REGEX_PROXY_PARAMS.search(link)
            if m: return m.group(1), int(m.group(2))
        else:
            if link.startswith('vmess://'):
                b64 = link.replace('vmess://', '')
                padded = b64 + '=' * (-len(b64) % 4)
                d = json.loads(base64.b64decode(padded).decode('utf-8'))
                return d['add'], int(d['port'])
            elif link.startswith('slipnet-enc://'):
                return 'slipnet', 0 
            else:
                m = re.search(r"@([\w\.-]+):(\d+)", link)
                if m: return m.group(1), int(m.group(2))
                m2 = re.search(r"://(?:[^@]+@)?([\w\.-]+):(\d+)", link)
                if m2: return m2.group(1), int(m2.group(2))
    except:
        pass
    return None, None

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
        return ALL_CHANNELS[:20], "First Batch", target_session
    else:
        return ALL_CHANNELS[20:], "Second Batch", target_session

def create_footer(source_title, source_username):
    now = datetime.now(iran_tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    safe_title = re.sub(r'[\[\]\(\)\*`_]', '', str(source_title)).strip()
    clean_username = source_username.replace('@', '')
    return (
        f"━━━━━━━━━━━━━━━━\n"
        f"🗓 {date_str} • 🕐 {time_str}\n"
        f"📡 منبع: [{safe_title}](https://t.me/{clean_username})\n"
        f"💬 {destination_channel}"
    )

def extract_password_from_text(text):
    if not text: return ""
    text = str(text)
    keywords = ['رمز', 'پسورد', 'password', 'pass']
    lines = [line.strip() for line in text.split('\n')]
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in keywords):
            clean_line = line_lower
            for kw in keywords: clean_line = clean_line.replace(kw, '')
            clean_line = clean_line.replace(':', '').replace('=', '').replace('-', '').strip()
            
            if clean_line: return f"🔑 {line}"
            else:
                for j in range(i + 1, len(lines)):
                    if lines[j]: return f"🔑 {line} {lines[j]}"
    
    match = re.search(r'@\w+', text)
    if match and len(text) < 150: return f"🔑 آیدی/رمز احتمالی: {match.group(0)}"
    return ""

async def check_connection(host, port):
    if host == 'slipnet': return 50
    try:
        start_time = time.perf_counter()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=PING_TIMEOUT)
        end_time = time.perf_counter()
        writer.close()
        try: await writer.wait_closed()
        except: pass
        return int((end_time - start_time) * 1000)
    except: return None

async def process_item(link, type='config'):
    host, port = get_host_port(link, type)
    if not host or port is None: return link, None, None, None, None

    latency = await check_connection(host, port)
    if latency is None:
        try:
            if any(host.startswith(p) for p in IRAN_IP_PREFIXES):
                return link, "🔵 اینترانت", None, "🇮🇷", "Iran"
        except: pass
        return link, None, None, None, None

    if host == 'slipnet': return link, "🟢 عالی", latency, "🏴‍☠️", "SlipNet"

    flag, country = get_ip_info(host)
    status = "🟢 عالی" if latency < 200 else "🟡 خوب" if latency < 500 else "🟠 متوسط"
    return link, status, latency, flag, country

# ==========================================
# 3. Main Execution
# ==========================================
target_channels, batch_name, active_session = get_batch_info()
if not active_session: sys.exit(1)

client = TelegramClient(StringSession(active_session), api_id, api_hash)

async def main():
    try:
        await client.start()
        print(f"Bot Started ({batch_name})")
        
        hist = load_data()
        unique_fingerprints = {extract_unique_key(c['config']) for c in hist['configs']}
        sent_hashes = {p['link'] for p in hist['proxies']} | {f['name'] for f in hist['files']}

        new_conf, new_prox, new_file = [], [], []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)

        for channel_str in target_channels:
            try:
                await asyncio.sleep(random.randint(5, 10))
                try:
                    entity = await client.get_entity(channel_str)
                    msgs = await client.get_messages(entity, limit=15)
                except: continue

                title = getattr(entity, 'title', channel_str)
                channel_proxies = []
                configs_to_process = []
                proxies_to_process = []

                for m in msgs:
                    if m.date < cutoff_time: continue
                    link = f"https://t.me/{channel_str[1:]}/{m.id}"

                    if m.text:
                        configs = REGEX_CONFIGS.findall(m.text)
                        for c in configs:
                            if extract_unique_key(c) not in unique_fingerprints:
                                configs_to_process.append((c, title, channel_str, m.id))
                        
                        found_proxies = set(p.replace('https://t.me/proxy', 'tg://proxy') for p in REGEX_PROXY.findall(m.text))
                        if m.entities:
                            for ent in m.entities:
                                if isinstance(ent, MessageEntityTextUrl) and 'proxy' in ent.url and ('server=' in ent.url or 'secret=' in ent.url):
                                    found_proxies.add(ent.url.replace('https://t.me/proxy', 'tg://proxy'))

                        for p in found_proxies:
                            if p not in sent_hashes:
                                proxies_to_process.append((p, title, channel_str))

                    if m.file and m.file.name:
                        file_ext = "." + m.file.name.split('.')[-1].lower() if '.' in m.file.name else ""
                        if any(m.file.name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS) and m.file.name not in sent_hashes:
                            pwd_text = extract_password_from_text(m.text)
                            
                            file_caption = f"📂 **{m.file.name}**\n\n"
                            if pwd_text:
                                file_caption += f"**پسورد فایل:**\n`{pwd_text.replace('🔑', '').strip()}`\n\n"
                            file_caption += create_footer(title, channel_str)

                            btn = [[Button.url("🌐 داشبورد اختصاصی ابزار", DASHBOARD_URL)]]

                            try:
                                await client.send_file(destination_channel, m.media, caption=file_caption, buttons=btn)
                                new_file.append({
                                    'name': m.file.name, 'ext': file_ext.replace('.', '').upper(), 
                                    'channel': title, 'link': link, 'ts': time.time()
                                })
                                sent_hashes.add(m.file.name)
                            except Exception as e:
                                print(f"❌ Error sending file: {e}")

                # پردازش موازی کانفیگ‌ها
                if configs_to_process:
                    tasks = [process_item(c[0], 'config') for c in configs_to_process]
                    results = await asyncio.gather(*tasks)
                    
                    for idx, res in enumerate(results):
                        c, stat, lat, flag, country = res
                        orig_data = configs_to_process[idx]
                        if stat:
                            prot = c.split('://')[0].upper().replace('-', '_')
                            safe_country = country.replace(' ', '_')
                            clean_c = c.replace('`', '')
                            u_key = extract_unique_key(c)
                            
                            caption = (
                                f"🌐 **پروتکل:** #{prot}\n"
                                f"🏳️ **لوکیشن:** {flag} #{safe_country}\n"
                                f"⚡ **وضعیت:** {stat} ({lat}ms)\n\n"
                                f"```{clean_c}```\n\n"
                                f"{create_footer(orig_data[1], orig_data[2])}"
                            )
                            
                            keyboard = [
                                [Button.url("🌐 مشاهده در داشبورد زنده", DASHBOARD_URL)],
                                [Button.url("🔗 لینک اشتراک سابسکریپشن", SUB_LINK_URL)]
                            ]
                            
                            try:
                                sent = await client.send_message(destination_channel, caption, link_preview=False, buttons=keyboard)
                                t_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                                new_conf.append({
                                    'protocol': prot, 'config': c, 'latency': lat, 
                                    'channel': orig_data[1], 't_link': t_link, 
                                    'flag': flag, 'country': country, 'ts': time.time()
                                })
                                unique_fingerprints.add(u_key)
                            except: pass

                # پردازش موازی پروکسی‌ها
                if proxies_to_process:
                    tasks = [process_item(p[0], 'proxy') for p in proxies_to_process]
                    results = await asyncio.gather(*tasks)
                    
                    proxy_buttons = []
                    for idx, res in enumerate(results):
                        p, stat, lat, flag, country = res
                        if stat:
                            m_search = REGEX_PROXY_PARAMS.search(p)
                            key_p = f"{m_search.group(1)}:{m_search.group(2)}" if m_search else str(time.time())
                            channel_proxies.append({'link': p, 'flag': flag, 'stat': stat, 'lat': lat, 'key': key_p})
                            sent_hashes.add(p)
                            btn_text = f"اتصال {flag} ({lat}ms)"
                            proxy_buttons.append([Button.url(btn_text, p)])
                    
                    if proxy_buttons:
                        proxy_msg = "🛡 **پروکسی‌های جدید و پرسرعت (MTProxy)**\n\n💡 برای اتصال سریع، روی دکمه‌های زیر کلیک کنید:\n\n"
                        proxy_msg += create_footer(proxies_to_process[0][1], proxies_to_process[0][2])
                        proxy_buttons.append([Button.url("🌐 داشبورد پیشرفته", DASHBOARD_URL)])
                        
                        try:
                            sent = await client.send_message(destination_channel, proxy_msg, link_preview=False, buttons=proxy_buttons)
                            t_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                            for p_data in channel_proxies:
                                new_prox.append({
                                    'key': p_data['key'], 'link': p_data['link'], 'channel': proxies_to_process[0][1], 
                                    't_link': t_link, 'latency': p_data['lat'], 'flag': p_data['flag'], 'ts': time.time()
                                })
                        except: pass

            except Exception as e: print(f"Error Loop: {e}")

        # ذخیره اطلاعات
        all_configs = sorted(hist['configs'] + new_conf, key=lambda x: x['ts'], reverse=True)[:100]
        all_proxies = sorted(hist['proxies'] + new_prox, key=lambda x: x['ts'], reverse=True)[:100]
        all_files = sorted(hist['files'] + new_file, key=lambda x: x['ts'], reverse=True)[:50]

        save_data({'configs': all_configs, 'proxies': all_proxies, 'files': all_files})
        
        # تولید فایل سابسکریپشن
        sub_content = "".join(c['config'] + "\n" for c in all_configs if c['config'].startswith(('vmess', 'vless', 'trojan', 'ss', 'hy2', 'tuic', 'slipnet-enc')))
        with open(SUB_FILE, 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(sub_content.encode('utf-8')).decode('utf-8'))

        # PWA Generation
        with open('manifest.json', 'w') as f:
            json.dump({
                "name": "VPN Hub Premium", "short_name": "VPN Hub", "start_url": "./index.html", "display": "standalone",
                "background_color": "#020617", "theme_color": "#020617",
                "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2099/2099192.png", "sizes": "192x192", "type": "image/png"}]
            }, f)

        with open('sw.js', 'w') as f:
            f.write("self.addEventListener('install',e=>e.waitUntil(caches.open('vpn-v1').then(c=>c.addAll(['index.html','manifest.json']))));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));")

        # بازنویسی کامل index.html با ساختار داینامیک و پرسرعت (رشته HTML استاتیک)
        full_html = """<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium</title>
    <meta name="theme-color" content="#0f172a">
    
    <!-- PWA Metadata -->
    <link rel="manifest" href="manifest.json">
    <link rel="apple-touch-icon" href="https://cdn-icons-png.flaticon.com/512/2099/2099192.png">
    
    <!-- TailWind & Fonts & Icons -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: { sans: ['Vazirmatn', 'sans-serif'] }
                }
            }
        }
    </script>
    
    <style>
        body { font-family: 'Vazirmatn', sans-serif; background-color: #020617; color: #f8fafc; -webkit-tap-highlight-color: transparent; }
        .pb-safe { padding-bottom: env(safe-area-inset-bottom); }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 10px; }
        .filter-btn.active { background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%); color: #020617; font-weight: 800; border-color: #38bdf8; box-shadow: 0 0 15px rgba(56,189,248,0.4); }
        .sort-btn.active { background-color: #1e293b; color: #38bdf8; border-color: #38bdf8/50; }
        @keyframes pulse-glow { 0%, 100% { opacity: 0.6; } 50% { opacity: 1; transform: scale(1.05); } }
        .live-dot { animation: pulse-glow 2s infinite; }
    </style>
</head>
<body class="min-h-screen flex flex-col pb-24 selection:bg-sky-500/30 selection:text-sky-200">
    
    <!-- Top Header Bar -->
    <header class="fixed top-0 w-full bg-slate-950/75 backdrop-blur-xl border-b border-slate-800/60 z-40 transition-all duration-300">
        <div class="max-w-xl mx-auto px-4 h-16 flex justify-between items-center">
            <div class="flex flex-col">
                <h1 class="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-indigo-400 to-emerald-400 tracking-tight">VPN Hub <span class="text-xs font-bold bg-sky-500/10 text-sky-400 px-2 py-0.5 rounded-full border border-sky-500/20">PRO</span></h1>
                <div class="flex items-center gap-1.5 text-[10px] text-slate-400 font-mono mt-0.5">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 live-dot"></span>
                    <span id="updateTime">در حال بروزرسانی...</span>
                </div>
            </div>
            <div class="flex gap-2">
                <button onclick="showSubQR()" class="bg-slate-800 hover:bg-slate-700 text-slate-300 w-9 h-9 rounded-full flex items-center justify-center border border-slate-700 transition-all active:scale-95" title="کد QR اشتراک">
                    <i class="fas fa-qrcode text-sm"></i>
                </button>
                <a href="https://raw.githubusercontent.com/mostafa5804/Myvpn1404/refs/heads/main/sub.txt" class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white px-4 py-2 rounded-full text-xs font-bold shadow-lg shadow-emerald-950/40 transition-all active:scale-95 flex items-center gap-2 border border-emerald-500/20">
                    <i class="fas fa-rss animate-pulse"></i> لینک اشتراک
                </a>
            </div>
        </div>
    </header>

    <!-- Main Content Grid Container -->
    <main class="max-w-xl mx-auto w-full pt-20 px-4 flex-grow">
        
        <!-- Controls & Filter Toolbar Sticky -->
        <div class="sticky top-16 bg-slate-950/90 backdrop-blur-md z-30 py-4 -mx-4 px-4 border-b border-slate-900 mb-4 space-y-3.5">
            <!-- Search field -->
            <div class="relative group">
                <i class="fas fa-search absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-sky-400 transition-colors"></i>
                <input type="text" id="searchInput" oninput="filterGrid()" placeholder="جستجو بر اساس کشور، پروتکل یا کانال..." class="w-full bg-slate-900 text-white text-sm rounded-xl pl-4 pr-11 py-3.5 border border-slate-800 focus:border-sky-500/50 focus:ring-2 focus:ring-sky-950 outline-none transition-all placeholder-slate-500 shadow-inner">
            </div>
            
            <!-- Protocol Filter Tabs -->
            <div class="flex gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
                <button onclick="filterType('all', this)" class="filter-btn active flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">همه سرورها</button>
                <button onclick="filterType('VLESS', this)" class="filter-btn flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">VLESS</button>
                <button onclick="filterType('VMESS', this)" class="filter-btn flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">VMess</button>
                <button onclick="filterType('TROJAN', this)" class="filter-btn flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">Trojan</button>
                <button onclick="filterType('MTPROXY', this)" class="filter-btn flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">MTProxy</button>
                <button onclick="filterType('FILES', this)" class="filter-btn flex-shrink-0 bg-slate-900 text-slate-400 px-5 py-2 rounded-full text-xs border border-slate-800 transition-all">فایل‌ها (NPVT)</button>
            </div>

            <!-- Advanced Sorting Toolbar & Copy All Action -->
            <div class="flex items-center justify-between pt-1 gap-4">
                <div class="flex gap-1.5 bg-slate-900/60 p-0.5 rounded-lg border border-slate-800/80">
                    <button onclick="changeSort('date', this)" class="sort-btn active px-3 py-1.5 rounded-md text-[11px] font-medium text-slate-400 border border-transparent transition-all">
                        <i class="fas fa-clock pl-1"></i>جدیدترین
                    </button>
                    <button onclick="changeSort('ping', this)" class="sort-btn px-3 py-1.5 rounded-md text-[11px] font-medium text-slate-400 border border-transparent transition-all">
                        <i class="fas fa-bolt pl-1"></i>کمترین پینگ
                    </button>
                </div>
                
                <button onclick="copyAllVisible()" id="copyAllBtn" class="bg-sky-950/40 hover:bg-sky-900/60 text-sky-400 border border-sky-900/50 px-3 py-1.5 rounded-lg text-[11px] font-bold transition-all flex items-center gap-1.5 shadow-sm">
                    <i class="fas fa-copy"></i> کپی همه فیلتر شده‌ها
                </button>
            </div>
        </div>

        <!-- Cards Display Dynamic Grid -->
        <div id="grid" class="grid gap-4">
            <!-- Skeleton Loaders Shimmer Effect -->
            <div class="skeleton-card bg-slate-900/40 border border-slate-900 rounded-2xl p-4 space-y-4 animate-pulse">
                <div class="flex justify-between items-center">
                    <div class="flex items-center gap-3"><div class="w-10 h-10 bg-slate-800 rounded-xl"></div><div class="space-y-2"><div class="w-20 h-4 bg-slate-800 rounded"></div><div class="w-12 h-3 bg-slate-800 rounded"></div></div></div>
                    <div class="w-16 h-6 bg-slate-800 rounded-lg"></div>
                </div>
                <div class="grid grid-cols-2 gap-2"><div class="h-10 bg-slate-800 rounded-xl"></div><div class="h-10 bg-slate-800 rounded-xl"></div></div>
            </div>
        </div>
        
        <!-- Premium UI Empty State Template -->
        <div id="emptyState" class="hidden flex-col items-center justify-center py-20 text-slate-500 text-center animate-fade-in">
            <div class="relative mb-4">
                <div class="absolute inset-0 bg-sky-500/10 blur-2xl rounded-full"></div>
                <i class="fas fa-ghost text-5xl relative z-10 text-slate-600 drop-shadow-md"></i>
            </div>
            <h3 class="text-base font-bold text-slate-300 mb-1">سروری یافت نشد!</h3>
            <p class="text-xs text-slate-500 max-w-xs mb-5 leading-relaxed">کانفیگی با فیلتر یا عبارت مورد نظر شما در دیتابیس پیدا نشد.</p>
            <button onclick="resetFilters()" class="bg-slate-900 hover:bg-slate-800 text-sky-400 px-5 py-2 rounded-xl text-xs font-semibold border border-slate-800 transition-all active:scale-95 flex items-center gap-1.5">
                <i class="fas fa-arrow-rotate-left text-[10px]"></i> ریست کردن فیلترها
            </button>
        </div>
    </main>

    <!-- Bottom Navigation Bar -->
    <nav class="fixed bottom-0 w-full bg-slate-950/80 backdrop-blur-xl border-t border-slate-900 pb-safe z-50">
        <div class="max-w-xl mx-auto grid grid-cols-3 h-16 relative">
            <div class="absolute -top-14 left-4">
                 <button onclick="window.scrollTo({top: 0, behavior: 'smooth'})" class="bg-slate-900/60 hover:bg-sky-600 border border-slate-800 text-white w-10 h-10 rounded-full backdrop-blur flex items-center justify-center shadow-xl transition-all active:scale-90">
                    <i class="fas fa-arrow-up text-xs"></i>
                 </button>
            </div>
            
            <button onclick="fetchData()" class="group flex flex-col items-center justify-center text-slate-400 hover:text-sky-400 transition-colors">
                <i class="fas fa-arrows-rotate text-lg mb-1 group-active:rotate-180 transition-transform duration-500"></i>
                <span class="text-[10px] font-medium">بروزرسانی لایو</span>
            </button>
            
            <a href="https://t.me/myvpn1404" target="_blank" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400 transition-colors">
                <div class="bg-sky-500/10 p-2.5 rounded-xl mb-0.5 shadow-inner">
                     <i class="fab fa-telegram text-lg text-sky-400"></i>
                </div>
            </a>

           <a href="https://github.com/mostafa5804" target="_blank" class="flex flex-col items-center justify-center text-slate-400 hover:text-white transition-colors">
               <i class="fab fa-github text-lg mb-1"></i>
               <span class="text-[10px] font-medium">مخزن گیت‌هاب</span>
          </a>
        </div>
    </nav>

    <!-- Modal Layout Architecture for QRCodes -->
    <div id="qrModal" class="fixed inset-0 z-[60] bg-black/80 backdrop-blur-md hidden flex items-center justify-center opacity-0 transition-opacity duration-300">
        <div class="bg-slate-900 p-6 rounded-2xl max-w-xs w-full mx-4 transform scale-95 transition-transform duration-300 shadow-2xl border border-slate-800">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-white font-bold text-sm" id="qrModalTitle">اسکن کد QR</h3>
                <button onclick="closeQR()" class="text-slate-400 hover:text-white w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center transition-colors"><i class="fas fa-times text-xs"></i></button>
            </div>
            <div class="bg-white p-3 rounded-xl flex justify-center overflow-hidden shadow-inner">
                <div id="qrcode"></div>
            </div>
            <p class="text-center text-slate-400 text-[11px] mt-4 leading-relaxed" id="qrModalDesc">برای اتصال سریع، بارکد فوق را داخل نرم‌افزار اسکن کنید.</p>
        </div>
    </div>

    <!-- Feedback Toast Notification System -->
    <div id="toast" class="fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-slate-900 border border-slate-800 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 translate-y-10 opacity-0 transition-all duration-300 z-[60]">
        <div class="bg-emerald-500/20 text-emerald-400 rounded-full w-6 h-6 flex items-center justify-center text-xs"><i class="fas fa-check"></i></div>
        <span class="text-xs font-semibold" id="toastText">با موفقیت کپی شد!</span>
    </div>

    <!-- JavaScript Application Logic Core Engine -->
    <script>
        let rawDatabase = { configs: [], proxies: [], files: [] };
        let activeFilterType = 'all';
        let activeSortType = 'date';
        const subscriptionLink = "https://raw.githubusercontent.com/mostafa5804/Myvpn1404/refs/heads/main/sub.txt";

        document.addEventListener("DOMContentLoaded", () => { fetchData(); });

        async function fetchData() {
            showSkeletons();
            try {
                const res = await fetch(`./data.json?t=${new Date().getTime()}`);
                if (!res.ok) throw new Error("Network status invalid");
                rawDatabase = await res.json();
                
                if (rawDatabase.configs && rawDatabase.configs.length > 0) {
                    const sampleTs = rawDatabase.configs[0].ts * 1000;
                    const dateObj = new Date(sampleTs);
                    document.getElementById('updateTime').innerText = dateObj.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' }) + " - " + dateObj.toLocaleDateString('fa-IR');
                } else {
                    document.getElementById('updateTime').innerText = "بروزرسانی زنده فعال";
                }
                renderGrid();
            } catch (err) {
                console.error("Critical fetching issue:", err);
                document.getElementById('grid').innerHTML = `<p class="text-center text-rose-400 py-6 text-xs font-bold"><i class="fas fa-triangle-exclamation pl-1"></i>خطا در بارگذاری پایگاه داده زنده</p>`;
            }
        }

        function showSkeletons() {
            const grid = document.getElementById('grid');
            document.getElementById('emptyState').classList.add('hidden');
            grid.innerHTML = Array(3).fill(`
                <div class="bg-slate-900/40 border border-slate-900 rounded-2xl p-4 space-y-4 animate-pulse">
                    <div class="flex justify-between items-center">
                        <div class="flex items-center gap-3"><div class="w-10 h-10 bg-slate-800 rounded-xl"></div><div class="space-y-2"><div class="w-24 h-4 bg-slate-800 rounded"></div><div class="w-16 h-3 bg-slate-800 rounded"></div></div></div>
                        <div class="w-16 h-6 bg-slate-800 rounded-lg"></div>
                    </div>
                    <div class="grid grid-cols-2 gap-2"><div class="h-10 bg-slate-800 rounded-xl"></div><div class="h-10 bg-slate-800 rounded-xl"></div></div>
                </div>
            `).join('');
        }

        function filterType(type, element) {
            document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            activeFilterType = type;
            renderGrid();
        }

        function changeSort(method, element) {
            document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
            element.classList.add('active');
            activeSortType = method;
            renderGrid();
        }

        function resetFilters() {
            document.getElementById('searchInput').value = '';
            filterType('all', document.querySelector('.filter-btn'));
        }

        function generateSignalBars(latency) {
            let colorClass = "bg-rose-500";
            let activeBars = 1;
            
            if (latency < 180) { colorClass = "bg-emerald-400"; activeBars = 3; } 
            else if (latency < 450) { colorClass = "bg-yellow-400"; activeBars = 2; }
            
            return `
                <div class="flex items-end gap-[2px] h-3.5 pb-0.5" title="پینگ: ${latency}ms">
                    <div class="w-1 h-1.5 ${activeBars >= 1 ? colorClass : 'bg-slate-700'} rounded-sm"></div>
                    <div class="w-1 h-2.5 ${activeBars >= 2 ? colorClass : 'bg-slate-700'} rounded-sm"></div>
                    <div class="w-1 h-3.5 ${activeBars >= 3 ? colorClass : 'bg-slate-700'} rounded-sm"></div>
                </div>
            `;
        }

        function renderGrid() {
            const grid = document.getElementById('grid');
            const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
            let compiledItems = [];

            if (activeFilterType === 'all' || ['VLESS', 'VMESS', 'TROJAN'].includes(activeFilterType)) {
                let confs = (rawDatabase.configs || []).map(item => ({ ...item, masterType: 'config' }));
                if (activeFilterType !== 'all') confs = confs.filter(c => c.protocol.toUpperCase() === activeFilterType);
                compiledItems = compiledItems.concat(confs);
            }

            if (activeFilterType === 'all' || activeFilterType === 'MTPROXY') {
                let proxies = (rawDatabase.proxies || []).map(item => ({ ...item, masterType: 'proxy', protocol: 'MTPROXY' }));
                compiledItems = compiledItems.concat(proxies);
            }

            if (activeFilterType === 'FILES') {
                let files = (rawDatabase.files || []).map(item => ({ ...item, masterType: 'file', protocol: item.ext }));
                compiledItems = compiledItems.concat(files);
            }

            if (searchTerm) {
                compiledItems = compiledItems.filter(item => {
                    const country = (item.country || '').toLowerCase();
                    const protocol = (item.protocol || '').toLowerCase();
                    const channel = (item.channel || '').toLowerCase();
                    const name = (item.name || '').toLowerCase();
                    return country.includes(searchTerm) || protocol.includes(searchTerm) || channel.includes(searchTerm) || name.includes(searchTerm);
                });
            }

            if (activeSortType === 'date') compiledItems.sort((a, b) => b.ts - a.ts);
            else if (activeSortType === 'ping') {
                compiledItems.sort((a, b) => {
                    const pA = a.masterType === 'file' ? 9999 : parseInt(a.latency || 9999);
                    const pB = b.masterType === 'file' ? 9999 : parseInt(b.latency || 9999);
                    return pA - pB;
                });
            }

            if (compiledItems.length === 0) {
                grid.innerHTML = '';
                document.getElementById('emptyState').classList.remove('hidden');
                return;
            }
            document.getElementById('emptyState').classList.add('hidden');

            grid.innerHTML = compiledItems.map((item, index) => {
                if (item.masterType === 'config') {
                    const lat = parseInt(item.latency || 999);
                    const pingColor = lat < 180 ? "text-emerald-400 bg-emerald-500/5 border-emerald-500/20" : lat < 450 ? "text-yellow-400 bg-yellow-500/5 border-yellow-500/20" : "text-rose-400 bg-rose-500/5 border-rose-500/20";
                    
                    return `
                        <div class="card group relative bg-gradient-to-b from-slate-900/90 to-slate-950/90 backdrop-blur-md rounded-2xl p-4 border border-slate-800/80 hover:border-sky-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_25px_-6px_rgba(56,189,248,0.15)] overflow-hidden">
                            <div class="flex justify-between items-start mb-3.5">
                                <div class="flex items-center gap-3">
                                    <span class="text-3xl filter drop-shadow-md select-none">${item.flag || '🏳️'}</span>
                                    <div>
                                        <div class="flex items-center gap-2">
                                            <span class="font-extrabold text-sky-400 text-xs tracking-wider">${item.protocol.toUpperCase()}</span>
                                            <span class="text-[9px] text-slate-400 border border-slate-800 rounded bg-slate-900 px-1 py-0.5 font-medium">${item.country || 'Global'}</span>
                                        </div>
                                        <div class="text-[10px] text-slate-500 mt-1 truncate max-w-[150px] font-medium"><i class="far fa-paper-plane pl-1 text-[9px]"></i>${item.channel}</div>
                                    </div>
                                </div>
                                <div class="text-[11px] font-mono font-bold ${pingColor} border px-2 py-1 rounded-lg flex items-center gap-1.5 shadow-inner">
                                    ${generateSignalBars(lat)}
                                    <span>${lat}ms</span>
                                </div>
                            </div>
                            <div class="grid grid-cols-2 gap-2">
                                <button onclick="copyToClipboard('${escapeHtml(item.config)}')" class="col-span-1 bg-sky-600/90 hover:bg-sky-500 text-slate-950 py-2.5 rounded-xl text-xs font-bold transition-all flex justify-center items-center gap-1.5 shadow-md shadow-sky-950/20">
                                    <i class="fas fa-copy"></i> کپی کانفیگ
                                </button>
                                <button onclick="showIndividualQR('${escapeHtml(item.config)}', '${item.protocol}')" class="col-span-1 bg-slate-900 hover:bg-slate-850 text-slate-300 py-2.5 rounded-xl text-xs font-semibold transition-all flex justify-center items-center gap-1.5 border border-slate-800">
                                    <i class="fas fa-qrcode text-slate-400"></i> بارکد QR
                                </button>
                            </div>
                        </div>`;
                } else if (item.masterType === 'proxy') {
                    const lat = parseInt(item.latency || 999);
                    const pingColor = lat < 180 ? "text-emerald-400 bg-emerald-500/5 border-emerald-500/20" : lat < 450 ? "text-yellow-400 bg-yellow-500/5 border-yellow-500/20" : "text-rose-400 bg-rose-500/5 border-rose-500/20";
                    
                    return `
                        <div class="card group relative bg-gradient-to-b from-slate-900/90 to-slate-950/90 backdrop-blur-md rounded-2xl p-4 border border-slate-800/80 hover:border-emerald-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_25px_-6px_rgba(52,211,153,0.15)] overflow-hidden">
                            <div class="flex justify-between items-start mb-3.5">
                                <div class="flex items-center gap-3">
                                    <span class="text-3xl filter drop-shadow-md select-none">${item.flag || '🏳️'}</span>
                                    <div>
                                        <div class="flex items-center gap-1.5">
                                            <span class="font-extrabold text-emerald-400 text-xs tracking-wider bg-emerald-950/30 border border-emerald-900/40 px-1.5 py-0.5 rounded">MTProxy</span>
                                        </div>
                                        <div class="text-[10px] text-slate-500 mt-1 truncate max-w-[150px] font-medium"><i class="far fa-paper-plane pl-1 text-[9px]"></i>${item.channel}</div>
                                    </div>
                                </div>
                                <div class="text-[11px] font-mono font-bold ${pingColor} border px-2 py-1 rounded-lg flex items-center gap-1.5 shadow-inner">
                                    ${generateSignalBars(lat)}
                                    <span>${lat}ms</span>
                                </div>
                            </div>
                            <div class="grid grid-cols-1">
                                <a href="${item.link}" class="w-full bg-emerald-600/90 hover:bg-emerald-500 text-slate-950 py-2.5 rounded-xl text-xs font-bold transition-all flex justify-center items-center gap-1.5 shadow-md shadow-emerald-950/20">
                                    <i class="fas fa-paper-plane"></i> اتصال مستقیم به پروکسی تلگرام
                                </a>
                            </div>
                        </div>`;
                } else if (item.masterType === 'file') {
                    return `
                        <div class="card group relative bg-gradient-to-b from-slate-900/90 to-slate-950/90 backdrop-blur-md rounded-2xl p-4 border border-slate-800/80 hover:border-indigo-500/40 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_8px_25px_-6px_rgba(129,140,248,0.15)] overflow-hidden">
                            <div class="flex justify-between items-start mb-3.5">
                                <div class="flex items-center gap-3">
                                    <div class="w-10 h-10 rounded-xl bg-indigo-950/40 border border-indigo-900/40 flex items-center justify-center text-indigo-400 text-lg shadow-inner"><i class="fas fa-file-code"></i></div>
                                    <div>
                                        <h4 class="text-xs font-bold text-slate-200 line-clamp-1 max-w-[180px]">${item.name}</h4>
                                        <div class="text-[10px] text-slate-500 mt-1 truncate max-w-[150px] font-medium"><i class="far fa-paper-plane pl-1 text-[9px]"></i>${item.channel}</div>
                                    </div>
                                </div>
                                <span class="text-[9px] font-extrabold text-indigo-400 border border-indigo-900/40 bg-indigo-950/30 px-2 py-0.5 rounded">${item.protocol}</span>
                            </div>
                            <div class="grid grid-cols-1">
                                <a href="${item.link}" target="_blank" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white py-2.5 rounded-xl text-xs font-bold transition-all flex justify-center items-center gap-1.5 shadow-md shadow-indigo-950/20">
                                    <i class="fas fa-download"></i> دانلود فایل از منبع اصلی تلگرام
                                </a>
                            </div>
                        </div>`;
                }
            }).join('');
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => { showToast("کانفیگ با موفقیت کپی شد."); }).catch(err => { console.error("Copy failed", err); });
        }

        function copyAllVisible() {
            const searchInput = document.getElementById('searchInput').value.toLowerCase().trim();
            let filtered = (rawDatabase.configs || []);
            if (activeFilterType !== 'all' && ['VLESS', 'VMESS', 'TROJAN'].includes(activeFilterType)) {
                filtered = filtered.filter(c => c.protocol.toUpperCase() === activeFilterType);
            } else if (['MTPROXY', 'FILES'].includes(activeFilterType)) {
                filtered = [];
            }
            if (searchInput) {
                filtered = filtered.filter(item => (item.country || '').toLowerCase().includes(searchInput) || (item.protocol || '').toLowerCase().includes(searchInput) || (item.channel || '').toLowerCase().includes(searchInput));
            }
            if (filtered.length === 0) { showToast("کانفیگ معتبری برای کپی یافت نشد", true); return; }
            const payload = filtered.map(c => c.config).join('\\n');
            navigator.clipboard.writeText(payload).then(() => { showToast(`${filtered.length} کانفیگ کپی شدند.`); });
        }

        function showToast(text, isWarning = false) {
            const t = document.getElementById('toast');
            document.getElementById('toastText').innerText = text;
            t.classList.remove('translate-y-10', 'opacity-0');
            setTimeout(() => t.classList.add('translate-y-10', 'opacity-0'), 2500);
        }

        const modal = document.getElementById('qrModal');
        const modalContent = modal.querySelector('div');
        
        function openModalCore(title, desc, textToQr) {
            document.getElementById('qrModalTitle').innerText = title;
            document.getElementById('qrModalDesc').innerText = desc;
            document.getElementById('qrcode').innerHTML = "";
            new QRCode(document.getElementById("qrcode"), { text: textToQr, width: 200, height: 200, colorDark : "#020617", colorLight : "#ffffff", correctLevel : QRCode.CorrectLevel.M });
            modal.classList.remove('hidden');
            setTimeout(() => { modal.classList.remove('opacity-0'); modalContent.classList.remove('scale-95'); modalContent.classList.add('scale-100'); }, 20);
        }

        function showIndividualQR(configStr, protocol) { openModalCore(`بارکد اتصال ${protocol}`, "برای اتصال مستقیم گوشی، بارکد فوق را داخل کلاینت خود اسکن کنید.", configStr); }
        function showSubQR() { openModalCore("بارکد کل لینک اشتراک", "آدرس سابسکریپشن کامل شما؛ بارکد فوق را اسکن کنید تا کل پایگاه داده به نرم‌افزار ایمپورت شود.", subscriptionLink); }
        function closeQR() {
            modal.classList.add('opacity-0'); modalContent.classList.remove('scale-100'); modalContent.classList.add('scale-95');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }
        modal.addEventListener('click', (e) => { if (e.target === modal) closeQR(); });
        function escapeHtml(str) { return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;"); }
    </script>
</body>
</html>"""

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(full_html)
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
