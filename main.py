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

# --- اصلاح شده: فوتر با لینک به کانال منبع ---
def create_footer(source_title, source_username):
    now = datetime.now(iran_tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    safe_title = re.sub(r'[\[\]\(\)\*`_]', '', str(source_title)).strip()
    
    # حذف @ از یوزرنیم برای ساخت لینک
    clean_username = source_username.replace('@', '')
    
    return (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"🗓 {date_str} • 🕐 {time_str}\n"
        f"📡 منبع: [{safe_title}](https://t.me/{clean_username})\n"
        f"🔗 {destination_channel} | [لینک اشتراک کانفینگ]({SUB_LINK_URL})"
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

                    # --- Section 1: Text Processing (Configs & Proxies) ---
                    if m.text:
                        # 1.1 Configs
                        configs = re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text)
                        for c in configs:
                            u_key = extract_unique_key(c)
                            if u_key not in unique_fingerprints:
                                stat, lat, flag, country = await process_item(c, 'config')
                                if stat:
                                    prot = c.split('://')[0].upper()
                                    clean_c = c.replace('`', '')
                                    # پاس دادن channel_str برای لینک‌دهی
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

                        # 1.2 Proxies
                        proxies = re.findall(r"https://t.me/proxy\?[^\s\n]+", m.text)
                        for p in proxies:
                            clean_p = p.replace('https://t.me/proxy', 'tg://proxy')
                            if clean_p not in sent_hashes:
                                stat, lat, flag, country = await process_item(clean_p, 'proxy')
                                if stat:
                                    m_search = re.search(r"server=([\w\.-]+)&port=(\d+)", clean_p)
                                    key_p = f"{m_search.group(1)}:{m_search.group(2)}" if m_search else str(time.time())
                                    channel_proxies.append({
                                        'link': clean_p, 'flag': flag, 'stat': stat, 'lat': lat, 'key': key_p
                                    })
                                    sent_hashes.add(clean_p)

                    # --- Section 2: File Processing ---
                    if m.file and m.file.name:
                        file_ext = "." + m.file.name.split('.')[-1].lower() if '.' in m.file.name else ""
                        
                        if any(m.file.name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                            if m.file.name not in sent_hashes:
                                try:
                                    print(f"📂 Found File: {m.file.name}")
                                    # استفاده از m.media برای ارسال مستقیم
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
        
        # 1. Config Cards
        for idx, cfg in enumerate(all_configs, 1):
            lat = cfg.get('latency')
            if lat is None: lat = 999
            else: lat = int(lat)

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
                    <div class="text-xs font-mono {ping_color} bg-slate-900 px-2 py-1 rounded">{lat}ms</div>
                </div>
                <div class="text-xs text-slate-400 mb-3 truncate">📡 {cfg['channel']} • {country}</div>
                <div class="grid grid-cols-2 gap-2">
                    <button onclick="copyToClipboard('{safe_conf}')" class="bg-sky-600 hover:bg-sky-500 text-white py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center gap-2"><i class="fas fa-copy"></i> Copy</button>
                    <a href="{cfg.get('t_link', '#')}" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center"><i class="fab fa-telegram"></i> Channel</a>
                </div>
            </div>"""

        # 2. Proxy Cards (اضافه شد)
        for idx, prox in enumerate(all_proxies, 1):
            lat = prox.get('latency')
            if lat is None: lat = 999
            else: lat = int(lat)
            
            flag = prox.get('flag', '🏳️')
            ping_color = "text-green-400" if lat < 200 else "text-yellow-400" if lat < 500 else "text-red-400"
            
            html_cards += f"""
            <div class="card bg-slate-800 rounded-xl p-4 border border-slate-700 hover:border-emerald-500 transition-all duration-300">
                <div class="flex justify-between items-center mb-3">
                    <div class="flex items-center gap-2">
                        <span class="text-2xl">{flag}</span>
                        <span class="font-bold text-emerald-400 uppercase text-sm bg-emerald-900/30 px-2 py-1 rounded">MTProxy</span>
                    </div>
                    <div class="text-xs font-mono {ping_color} bg-slate-900 px-2 py-1 rounded">{lat}ms</div>
                </div>
                <div class="text-xs text-slate-400 mb-3 truncate">📡 {prox['channel']}</div>
                <div class="grid grid-cols-2 gap-2">
                    <a href="{prox['link']}" class="bg-emerald-600 hover:bg-emerald-500 text-white py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center gap-2"><i class="fas fa-link"></i> Connect</a>
                    <a href="{prox.get('t_link', '#')}" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-slate-200 py-2 rounded-lg text-sm font-medium transition-colors flex justify-center items-center"><i class="fab fa-telegram"></i> Channel</a>
                </div>
            </div>"""

        full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium</title>
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#0f172a">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {{ font-family: 'Vazirmatn', sans-serif; background-color: #0f172a; color: #f1f5f9; padding-bottom: 80px; -webkit-tap-highlight-color: transparent; }}
        .card {{ animation: fadeIn 0.5s ease-out; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    </style>
</head>
<body>
    <header class="fixed top-0 w-full bg-slate-900/90 backdrop-blur-md border-b border-slate-700 z-50">
        <div class="max-w-md mx-auto px-4 h-16 flex justify-between items-center">
            <div><h1 class="text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-sky-400 to-purple-500">VPN Hub</h1><p class="text-[10px] text-slate-400">{now_str}</p></div>
            <a href="{SUB_LINK_URL}" class="bg-emerald-600/20 text-emerald-400 border border-emerald-600/50 px-3 py-1 rounded-full text-xs font-bold animate-pulse"><i class="fas fa-rss"></i> لینک اشتراک کانفینگ</a>
        </div>
    </header>
    <main class="max-w-md mx-auto pt-20 px-4">
        <div class="flex gap-2 mb-4 overflow-x-auto pb-2">
            <button onclick="filter('all')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">All</button>
            <button onclick="filter('vless')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">VLESS</button>
            <button onclick="filter('vmess')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">VMess</button>
            <button onclick="filter('mtproxy')" class="flex-shrink-0 bg-slate-800 text-slate-300 px-4 py-2 rounded-full text-sm border border-slate-700">MTProxy</button>
        </div>
        <div id="grid" class="grid gap-3">{html_cards}</div>
    </main>
    <nav class="fixed bottom-0 w-full bg-slate-900/95 backdrop-blur border-t border-slate-800 pb-safe z-50">
        <div class="max-w-md mx-auto grid grid-cols-3 h-16">
            <button onclick="window.scrollTo(0,0)" class="flex flex-col items-center justify-center text-sky-400"><i class="fas fa-bolt text-xl mb-1"></i><span class="text-[10px]">Config</span></button>
            <a href="{destination_channel.replace('@', 'https://t.me/')}" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400"><i class="fab fa-telegram text-xl mb-1"></i><span class="text-[10px]">Channel</span></a>
            <button onclick="location.reload()" class="flex flex-col items-center justify-center text-slate-400 hover:text-sky-400"><i class="fas fa-sync text-xl mb-1"></i><span class="text-[10px]">Update</span></button>
        </div>
    </nav>
    <div id="toast" class="fixed bottom-20 left-1/2 transform -translate-x-1/2 bg-emerald-600 text-white px-4 py-2 rounded-lg shadow-xl text-sm font-bold opacity-0 transition-opacity duration-300 pointer-events-none z-50">Copied! ✅</div>
    <script>
        if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
        function copyToClipboard(text) {{ navigator.clipboard.writeText(text).then(() => {{ const t = document.getElementById('toast'); t.classList.remove('opacity-0'); setTimeout(() => t.classList.add('opacity-0'), 2000); }}); }}
        function filter(type) {{ document.querySelectorAll('.card').forEach(c => {{ c.style.display = (type === 'all' || c.querySelector('.uppercase').innerText.toLowerCase().includes(type)) ? 'block' : 'none'; }}); }}
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
