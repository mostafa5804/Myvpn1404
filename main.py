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
# اضافه شدن ماژول برای خواندن لینک‌های مخفی
from telethon.tl.types import MessageEntityTextUrl

# ==========================================
# 1. Configuration
# ==========================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

PING_TIMEOUT = 1.5
DATA_FILE = 'data.json'
SUB_FILE = 'sub.txt'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
MAX_MESSAGE_AGE_MINUTES = 90
SUB_LINK_URL = "https://raw.githubusercontent.com/mostafa5804/Myvpn1404/refs/heads/main/sub.txt"

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

ALLOWED_EXTENSIONS = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')
IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

IP_CACHE = {}

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

        match = re.search(r'://.*?@([^:/]+):(\d+)', config_str)
        if match:
            return f"{match.group(1)}:{match.group(2)}"
        
        match_simple = re.search(r'://([^:/]+):(\d+)', config_str)
        if match_simple:
            return f"{match_simple.group(1)}:{match.group(2)}"

        return config_str
    except:
        return config_str

def get_host_port(link, type='config'):
    try:
        if type == 'proxy':
            m = re.search(r"server=([\w\.-]+)&port=(\d+)", link)
            if m: return m.group(1), int(m.group(2))
        else:
            if link.startswith('vmess://'):
                b64 = link.replace('vmess://', '')
                padded = b64 + '=' * (-len(b64) % 4)
                d = json.loads(base64.b64decode(padded).decode('utf-8'))
                return d['add'], int(d['port'])
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

# --- اصلاح شده: فوتر جدید طبق درخواست ---
def create_footer(source_title, source_username):
    now = datetime.now(iran_tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    safe_title = re.sub(r'[\[\]\(\)\*`_]', '', str(source_title)).strip()
    
    clean_username = source_username.replace('@', '')
    
    return (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"🗓 {date_str} • 🕐 {time_str}\n"
        f"📡 source: [{safe_title}](https://t.me/{clean_username})\n"
        f"💬 {destination_channel}"
    )

async def check_connection(host, port):
    try:
        start_time = time.perf_counter()
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
    host, port = get_host_port(link, type)
    if not host or not port:
        return None, None, None, None

    latency = await check_connection(host, port)
    
    if latency is None:
        try:
            if any(host.startswith(p) for p in IRAN_IP_PREFIXES):
                return "🔵 اینترانت", None, "🇮🇷", "Iran"
        except: pass
        return None, None, None, None

    flag, country = get_ip_info(host)
    status = "🟢 عالی" if latency < 200 else "🟡 خوب" if latency < 500 else "🟠 متوسط"
    return status, latency, flag, country

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
        unique_fingerprints = set()
        
        for c in hist['configs']: 
            k = extract_unique_key(c['config'])
            unique_fingerprints.add(k)
        
        sent_hashes = set()
        for p in hist['proxies']: sent_hashes.add(p['link'])
        for f in hist['files']: sent_hashes.add(f['name'])

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

                for m in msgs:
                    if m.date < cutoff_time: continue
                    link = f"https://t.me/{channel_str[1:]}/{m.id}"

                    # --- Section 1: Text Processing ---
                    if m.text:
                        # 1.1 Configs (VLESS/VMess/etc)
                        configs = re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text)
                        for c in configs:
                            u_key = extract_unique_key(c)
                            if u_key not in unique_fingerprints:
                                stat, lat, flag, country = await process_item(c, 'config')
                                if stat:
                                    prot = c.split('://')[0].upper()
                                    clean_c = c.replace('`', '')
                                    caption = (
                                        f"{flag} **{prot}** | {country}\n"
                                        f"📶 Ping: {lat}ms\n\n"
                                        f"```{clean_c}```\n"
                                        f"{create_footer(title, channel_str)}"
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
                                    except: pass

                        # 1.2 Proxies (Advanced Extraction: Regex + Entities)
                        found_proxies = set()
                        
                        # A) Regex (متن ساده)
                        regex_matches = re.findall(r"https://t.me/proxy\?[^\s\n]+|tg://proxy\?[^\s\n]+", m.text)
                        for p in regex_matches:
                            # تبدیل همه به tg://proxy برای یکسان‌سازی
                            clean_p = p.replace('https://t.me/proxy', 'tg://proxy')
                            found_proxies.add(clean_p)
                        
                        # B) Entities (هایپرلینک‌های مخفی)
                        if m.entities:
                            for ent in m.entities:
                                if isinstance(ent, MessageEntityTextUrl):
                                    url = ent.url
                                    if 'proxy' in url and ('server=' in url or 'secret=' in url):
                                        clean_url = url.replace('https://t.me/proxy', 'tg://proxy')
                                        found_proxies.add(clean_url)

                        # پردازش لیست پیدا شده
                        for p in found_proxies:
                            if p not in sent_hashes:
                                stat, lat, flag, country = await process_item(p, 'proxy')
                                if stat:
                                    # استخراج مشخصات برای دیتابیس
                                    m_search = re.search(r"server=([\w\.-]+)&port=(\d+)", p)
                                    key_p = f"{m_search.group(1)}:{m_search.group(2)}" if m_search else str(time.time())
                                    
                                    channel_proxies.append({
                                        'link': p, 'flag': flag, 'stat': stat, 'lat': lat, 'key': key_p
                                    })
                                    sent_hashes.add(p)

                    # --- Section 2: File Processing ---
                    if m.file and m.file.name:
                        file_ext = "." + m.file.name.split('.')[-1].lower() if '.' in m.file.name else ""
                        
                        if any(m.file.name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                            if m.file.name not in sent_hashes:
                                try:
                                    print(f"📂 Found File: {m.file.name}")
                                    await client.send_file(destination_channel, m.media, caption=f"📂 **{m.file.name}**\n{create_footer(title, channel_str)}")
                                    new_file.append({
                                        'name': m.file.name, 'ext': file_ext.replace('.', '').upper(), 
                                        'channel': title, 'link': link, 'ts': time.time()
                                    })
                                    sent_hashes.add(m.file.name)
                                except Exception as e:
                                    print(f"❌ Error sending file {m.file.name}: {e}")

                # --- Send Batch Proxies ---
                if channel_proxies:
                    proxy_msg = "🔵 MTProxy‌های جدید\n\n"
                    for idx, p_data in enumerate(channel_proxies, 1):
                        proxy_msg += f"{idx}. {p_data['flag']} - [اتصال]({p_data['link']}) • {p_data['stat']} {p_data['lat']}ms\n"
                    
                    proxy_msg += "\n💡 برای اتصال روی لینک کلیک کنید"
                    proxy_msg += create_footer(title, channel_str)

                    try:
                        sent = await client.send_message(destination_channel, proxy_msg, link_preview=False)
                        for p_data in channel_proxies:
                            new_prox.append({
                                'key': p_data['key'], 'link': p_data['link'], 'channel': title, 
                                't_link': f"https://t.me/{destination_channel[1:]}/{sent.id}", 
                                'latency': p_data['lat'], 'flag': p_data['flag'], 
                                'ts': time.time()
                            })
                    except: pass

            except Exception as e: print(f"Error Loop: {e}")

        # Saving & Generation
        all_configs = hist['configs'] + new_conf
        all_configs.sort(key=lambda x: x['ts'], reverse=True)
        all_configs = all_configs[:300]

        all_proxies = hist['proxies'] + new_prox
        all_proxies.sort(key=lambda x: x['ts'], reverse=True)
        all_proxies = all_proxies[:100]
        
        all_files = hist['files'] + new_file
        all_files.sort(key=lambda x: x['ts'], reverse=True)
        all_files = all_files[:50]

        save_data({'configs': all_configs, 'proxies': all_proxies, 'files': all_files})
        
        # Subscription Link
        sub_content = ""
        for c in all_configs:
            if c['config'].startswith(('vmess', 'vless', 'trojan', 'ss', 'hy2', 'tuic')):
                sub_content += c['config'] + "\n"
        
        with open(SUB_FILE, 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(sub_content.encode('utf-8')).decode('utf-8'))

        # PWA Generation
        with open('manifest.json', 'w') as f:
            json.dump({
                "name": "VPN Hub Premium",
                "short_name": "VPN Hub",
                "start_url": "./index.html",
                "display": "standalone",
                "background_color": "#0f172a",
                "theme_color": "#0f172a",
                "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2099/2099192.png", "sizes": "192x192", "type": "image/png"}]
            }, f)

        with open('sw.js', 'w') as f:
            f.write("self.addEventListener('install',e=>e.waitUntil(caches.open('vpn-v1').then(c=>c.addAll(['index.html','manifest.json']))));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));")

        now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
        html_cards = ""

        # 1. Config Cards Generator
        for idx, cfg in enumerate(all_configs, 1):
            lat = cfg.get('latency', 999)
            try:
                lat = int(lat)
            except:
                lat = 999

            flag = cfg.get('flag', '🏳️')
            country = html.escape(cfg.get('country', 'Unknown'))

            raw_conf = cfg['config']
            safe_conf = html.escape(raw_conf)

            protocol = cfg['protocol'].upper()
    
    # تعیین رنگ پینگ
    if lat < 500: ping_color = "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
    elif lat < 1000: ping_color = "text-yellow-400 border-yellow-500/30 bg-yellow-500/10"
    else: ping_color = "text-rose-400 border-rose-500/30 bg-rose-500/10"
    
    html_cards += f"""
    <div class="card group relative bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/50 hover:border-sky-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-sky-500/10" data-type="{protocol.lower()}" data-search="{country.lower()} {protocol.lower()}">
        <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
                <span class="text-3xl filter drop-shadow-md">{flag}</span>
                <div>
                    <div class="flex items-center gap-2">
                        <span class="font-bold text-sky-400 text-sm tracking-wide">{protocol}</span>
                        <span class="text-[10px] text-slate-500 border border-slate-700 rounded px-1">{country}</span>
                    </div>
                    <div class="text-xs text-slate-400 mt-1 truncate max-w-[120px]">Server {idx}</div>
                </div>
            </div>
            <div class="text-xs font-mono font-bold {ping_color} border px-2 py-1 rounded-lg flex items-center gap-1">
                <i class="fas fa-signal text-[10px]"></i> {lat}ms
            </div>
        </div>
        
        <div class="grid grid-cols-2 gap-2 mt-2">
            <button data-clipboard="{safe_conf}" class="copy-btn col-span-1 bg-sky-600/90 hover:bg-sky-500 text-white py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95 flex justify-center items-center gap-2 shadow-lg shadow-sky-900/20">
                <i class="fas fa-copy"></i> <span>کپی</span>
            </button>
            <button onclick="showQR('{safe_conf}')" class="col-span-1 bg-slate-700/80 hover:bg-slate-600 text-slate-200 py-2.5 rounded-xl text-sm font-medium transition-all active:scale-95 flex justify-center items-center gap-2 border border-slate-600/50">
                <i class="fas fa-qrcode"></i> QR
            </button>
        </div>
    </div>"""

# 2. Proxy Cards Generator
for idx, prox in enumerate(all_proxies, 1):
    lat = prox.get('latency', 999)
    try: lat = int(lat)
    except: lat = 999
    
    flag = prox.get('flag', '🏳️')
    safe_link = html.escape(prox['link'])
    
    if lat < 500: ping_color = "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
    elif lat < 1000: ping_color = "text-yellow-400 border-yellow-500/30 bg-yellow-500/10"
    else: ping_color = "text-rose-400 border-rose-500/30 bg-rose-500/10"
    
    html_cards += f"""
    <div class="card group bg-slate-800/50 backdrop-blur-sm rounded-2xl p-4 border border-slate-700/50 hover:border-emerald-500/50 transition-all duration-300" data-type="mtproxy" data-search="mtproxy telegram">
        <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
                <span class="text-3xl filter drop-shadow-md">{flag}</span>
                <div>
                    <span class="font-bold text-emerald-400 text-sm tracking-wide bg-emerald-900/20 px-2 py-0.5 rounded">MTProxy</span>
                    <div class="text-xs text-slate-400 mt-1">Telegram Proxy</div>
                </div>
            </div>
            <div class="text-xs font-mono font-bold {ping_color} border px-2 py-1 rounded-lg flex items-center gap-1">
                <i class="fas fa-bolt text-[10px]"></i> {lat}ms
            </div>
        </div>
        
        <div class="grid grid-cols-1 gap-2 mt-2">
            <a href="{safe_link}" class="bg-emerald-600/90 hover:bg-emerald-500 text-white py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95 flex justify-center items-center gap-2 shadow-lg shadow-emerald-900/20">
                <i class="fas fa-paper-plane"></i> <span>اتصال سریع</span>
            </a>
        </div>
    </div>"""

full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium</title>
    <meta name="theme-color" content="#0f172a">
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Fonts & Icons -->
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <!-- QR Code Library -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    
    <style>
        body {{ font-family: 'Vazirmatn', sans-serif; background-color: #0f172a; color: #f1f5f9; -webkit-tap-highlight-color: transparent; }}
        .pb-safe {{ padding-bottom: env(safe-area-inset-bottom); }}
        
        /* Custom Scrollbar */
        ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
        ::-webkit-scrollbar-track {{ background: #1e293b; }}
        ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
        
        /* Animation */
        .card-enter {{ animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }}
        @keyframes slideUp {{ from {{ opacity: 0; transform: translateY(20px) scale(0.96); }} to {{ opacity: 1; transform: translateY(0) scale(1); }} }}
        
        .filter-btn.active {{ background-color: #38bdf8; color: #0f172a; border-color: #38bdf8; font-weight: 700; }}
    </style>
</head>
<body class="min-h-screen flex flex-col pb-24">
    
    <!-- Header -->
    <header class="fixed top-0 w-full bg-slate-900/80 backdrop-blur-lg border-b border-slate-700/50 z-40 transition-all duration-300" id="header">
        <div class="max-w-xl mx-auto px-4 h-16 flex justify-between items-center">
            <div>
                <h1 class="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 via-purple-400 to-emerald-400 tracking-tighter">VPN Hub</h1>
                <div class="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                    <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    {now_str}
                </div>
            </div>
            <a href="{SUB_LINK_URL}" class="bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white px-4 py-2 rounded-full text-xs font-bold shadow-lg shadow-emerald-900/30 transition-all active:scale-95 flex items-center gap-2">
                <i class="fas fa-rss"></i> اشتراک
            </a>
        </div>
    </header>

    <!-- Main Content -->
    <main class="max-w-xl mx-auto w-full pt-24 px-4 flex-grow">
        
        <!-- Search & Filter Container -->
        <div class="sticky top-16 bg-slate-900/90 backdrop-blur-md z-30 py-4 -mx-4 px-4 border-b border-slate-800/50 mb-4 space-y-3">
            <!-- Search -->
            <div class="relative">
                <i class="fas fa-search absolute right-3 top-1/2 -translate-y-1/2 text-slate-500"></i>
                <input type="text" id="searchInput" placeholder="جستجو (کشور، پروتکل...)" class="w-full bg-slate-800 text-white text-sm rounded-xl pl-4 pr-10 py-3 border border-slate-700 focus:border-sky-500 focus:ring-1 focus:ring-sky-500 outline-none transition-all placeholder-slate-500">
            </div>
            
            <!-- Filters -->
            <div class="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                <button onclick="filterItems('all', this)" class="filter-btn active flex-shrink-0 bg-slate-800 text-slate-400 px-5 py-2 rounded-full text-sm border border-slate-700 transition-all">همه</button>
                <button onclick="filterItems('vless', this)" class="filter-btn flex-shrink-0 bg-slate-800 text-slate-400 px-5 py-2 rounded-full text-sm border border-slate-700 transition-all">VLESS</button>
                <button onclick="filterItems('vmess', this)" class="filter-btn flex-shrink-0 bg-slate-800 text-slate-400 px-5 py-2 rounded-full text-sm border border-slate-700 transition-all">VMess</button>
                <button onclick="filterItems('mtproxy', this)" class="filter-btn flex-shrink-0 bg-slate-800 text-slate-400 px-5 py-2 rounded-full text-sm border border-slate-700 transition-all">MTProxy</button>
            </div>
        </div>

        <!-- Grid -->
        <div id="grid" class="grid gap-4 card-enter">
            {html_cards}
        </div>
        
        <!-- Empty State -->
        <div id="emptyState" class="hidden flex-col items-center justify-center py-12 text-slate-500">
            <i class="fas fa-ghost text-4xl mb-3 opacity-50"></i>
            <p class="text-sm">موردی یافت نشد</p>
        </div>
    </main>

    <!-- Bottom Nav -->
    <nav class="fixed bottom-0 w-full bg-slate-900/80 backdrop-blur-xl border-t border-slate-700/50 pb-safe z-50">
        <div class="max-w-xl mx-auto grid grid-cols-3 h-16 relative">
            <div class="absolute -top-12 right-4">
                 <button onclick="window.scrollTo({{top: 0, behavior: 'smooth'}})" class="bg-slate-700/50 hover:bg-sky-500 text-white w-10 h-10 rounded-full backdrop-blur flex items-center justify-center shadow-lg transition-all">
                    <i class="fas fa-arrow-up"></i>
                 </button>
            </div>
            
            <button onclick="location.reload()" class="group flex flex-col items-center justify-center text-slate-400 hover:text-sky-400 transition-colors">
                <i class="fas fa-sync text-xl mb-1 group-active:rotate-180 transition-transform duration-500"></i>
                <span class="text-[10px] font-medium">بروزرسانی</span>
            </button>
            
            <a href="{destination_channel.replace('@', 'https://t.me/')}" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400 transition-colors">
                <div class="bg-sky-500/10 p-2 rounded-xl mb-0.5">
                     <i class="fab fa-telegram text-xl text-sky-500"></i>
                </div>
            </a>

            <a href="https://github.com/YourRepo" class="flex flex-col items-center justify-center text-slate-400 hover:text-white transition-colors">
                <i class="fab fa-github text-xl mb-1"></i>
                <span class="text-[10px] font-medium">سورس</span>
            </a>
        </div>
    </nav>

    <!-- QR Modal -->
    <div id="qrModal" class="fixed inset-0 z-[60] bg-black/80 backdrop-blur-sm hidden flex items-center justify-center opacity-0 transition-opacity duration-300">
        <div class="bg-slate-800 p-6 rounded-2xl max-w-xs w-full mx-4 transform scale-95 transition-transform duration-300 shadow-2xl border border-slate-700">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-white font-bold">اسکن کد QR</h3>
                <button onclick="closeQR()" class="text-slate-400 hover:text-white"><i class="fas fa-times text-xl"></i></button>
            </div>
            <div id="qrcode" class="bg-white p-3 rounded-xl flex justify-center overflow-hidden"></div>
            <p class="text-center text-slate-400 text-xs mt-4">برای اتصال در برنامه اسکن کنید</p>
        </div>
    </div>

    <!-- Toast Notification -->
    <div id="toast" class="fixed bottom-24 left-1/2 transform -translate-x-1/2 bg-slate-800 border border-slate-700 text-white px-4 py-3 rounded-xl shadow-2xl flex items-center gap-3 translate-y-10 opacity-0 transition-all duration-300 z-[60]">
        <div class="bg-emerald-500/20 text-emerald-400 rounded-full p-1"><i class="fas fa-check-circle"></i></div>
        <span class="text-sm font-medium">کپی شد!</span>
    </div>

    <script>
        // Copy Logic
        document.querySelectorAll('.copy-btn').forEach(btn => {{
            btn.addEventListener('click', function() {{
                const text = this.getAttribute('data-clipboard');
                navigator.clipboard.writeText(text).then(() => showToast());
                
                // Visual Feedback
                const originalContent = this.innerHTML;
                this.classList.replace('bg-sky-600/90', 'bg-emerald-600');
                this.innerHTML = '<i class="fas fa-check"></i> <span>OK</span>';
                setTimeout(() => {{
                    this.classList.replace('bg-emerald-600', 'bg-sky-600/90');
                    this.innerHTML = originalContent;
                }}, 1500);
            }});
        }});

        function showToast() {{
            const t = document.getElementById('toast');
            t.classList.remove('translate-y-10', 'opacity-0');
            setTimeout(() => t.classList.add('translate-y-10', 'opacity-0'), 2000);
        }}

        // Filter Logic
        function filterItems(type, btn) {{
            // Active Button State
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            filterGrid();
        }}

        // Search Logic
        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', filterGrid);

        function filterGrid() {{
            const type = document.querySelector('.filter-btn.active').getAttribute('onclick').match(/'([^']+)'/)[1];
            const term = searchInput.value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            let hasVisible = false;

            cards.forEach(card => {{
                const cardType = card.getAttribute('data-type');
                const cardSearch = card.getAttribute('data-search');
                
                const typeMatch = type === 'all' || cardType.includes(type);
                const searchMatch = cardSearch.includes(term);

                if (typeMatch && searchMatch) {{
                    card.style.display = 'block';
                    // Re-trigger animation
                    card.style.animation = 'none';
                    card.offsetHeight; /* trigger reflow */
                    card.style.animation = null; 
                    hasVisible = true;
                }} else {{
                    card.style.display = 'none';
                }}
            }});
            
            document.getElementById('emptyState').classList.toggle('hidden', hasVisible);
        }}

        // QR Code Logic
        const modal = document.getElementById('qrModal');
        const modalContent = modal.querySelector('div');
        
        function showQR(text) {{
            document.getElementById('qrcode').innerHTML = "";
            new QRCode(document.getElementById("qrcode"), {{
                text: text,
                width: 200,
                height: 200,
                colorDark : "#000000",
                colorLight : "#ffffff",
                correctLevel : QRCode.CorrectLevel.M
            }});
            
            modal.classList.remove('hidden');
            // Small delay for transition
            setTimeout(() => {{
                modal.classList.remove('opacity-0');
                modalContent.classList.remove('scale-95');
                modalContent.classList.add('scale-100');
            }}, 10);
        }}

        function closeQR() {{
            modal.classList.add('opacity-0');
            modalContent.classList.remove('scale-100');
            modalContent.classList.add('scale-95');
            setTimeout(() => modal.classList.add('hidden'), 300);
        }}
        
        // Close modal on outside click
        modal.addEventListener('click', (e) => {{
            if (e.target === modal) closeQR();
        }});
    </script>
</body>
</html>"""
    

        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(full_html)
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally: await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
