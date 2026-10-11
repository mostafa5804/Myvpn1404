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
from telethon.tl.types import MessageEntityTextUrl

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

ALL_CHANNELS = [
    # --- کانال‌های جدید اضافه شده ---
    '@net_melli1', '@xixv2ray', '@filtershekan_channel', '@ghalagyann', '@Proxymelimon',
    '@isor1n', '@Lizard_Vpn', '@KalbodTeam', '@TirexNet',
    
    # --- کانال‌های فعال و قدیمی (سبز و زرد) ---
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
    # Deduplicate only identical full config text. Host/port alone collides
    # for valid configs with different credentials or parameters.
    return str(config_str)

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
            elif link.startswith('slipnet-enc://'):
                # SlipNet قابل استخراج IP/Port برای پینگ نیست
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

def telegram_text_units(text):
    """Telegram counts UTF-16 code units, not Python Unicode code points."""
    return len(str(text).encode('utf-16-le')) // 2


def split_text_lossless(text, max_units=3300):
    """Split plain text on character boundaries; joining chunks restores it exactly."""
    text = str(text or "")
    chunks, current, units = [], [], 0
    for char in text:
        char_units = 2 if ord(char) > 0xFFFF else 1
        if current and units + char_units > max_units:
            chunks.append(''.join(current))
            current, units = [], 0
        current.append(char)
        units += char_units
    if current or not chunks:
        chunks.append(''.join(current))
    return chunks


def create_footer(source_title, source_username):
    now = datetime.now(iran_tz)
    date_str = now.strftime('%Y/%m/%d')
    time_str = now.strftime('%H:%M')
    safe_title = re.sub(r'[\[\]\(\)\*`_]', '', str(source_title)).strip()
    clean_username = source_username.replace('@', '')
    return (
        f"\n━━━━━━━━━━━━━━━━\n"
        f"🗓 {date_str} • 🕐 {time_str}\n"
        f"📡 source: {safe_title} https://t.me/{clean_username}\n"
        f"💬 {destination_channel}\n"
        
    )

async def check_connection(host, port):
    if host == 'slipnet':
        # برای slipnet چون رمز شده است، پینگ نمی‌گیریم و فرض می‌کنیم سالم است
        return 50 # یک پینگ فرضی می‌دهیم تا به عنوان کانفیگ عالی دسته‌بندی شود

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
    if not host or port is None:
        return None, None, None, None

    latency = await check_connection(host, port)
    
    if latency is None:
        try:
            if any(host.startswith(p) for p in IRAN_IP_PREFIXES):
                return "🔵 اینترانت", None, "🇮🇷", "Iran"
        except: pass
        return None, None, None, None

    if host == 'slipnet':
        return "🟢 عالی", latency, "🏴‍☠️", "SlipNet"

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
        for f in hist['files']: sent_hashes.add(f.get('link', f.get('name')))

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
                        # 1.1 Configs (VLESS/VMess/SlipNet/etc)
                        # اضافه شدن slipnet-enc به لیست
                        configs = re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|slipnet-enc):\/\/[^\s\n]+", m.text)
                        for c in configs:
                            u_key = extract_unique_key(c)
                            if u_key not in unique_fingerprints:
                                stat, lat, flag, country = await process_item(c, 'config')
                                if stat:
                                    prot = c.split('://')[0].upper().replace('-', '_')
                                    # Split only when necessary; concatenating part bodies reproduces c exactly.
                                    chunks = split_text_lossless(c)
                                    first_sent = None
                                    try:
                                        for part_index, chunk in enumerate(chunks, 1):
                                            part_label = f" • بخش {part_index}/{len(chunks)}" if len(chunks) > 1 else ""
                                            message = (
                                                f"{flag} {prot} | {country}{part_label}\n"
                                                f"📶 اتصال TCP: {lat}ms\n"
                                                f"منبع: {link}\n\n{chunk}"
                                            )
                                            sent = await client.send_message(
                                                destination_channel, message,
                                                link_preview=False, parse_mode=None
                                            )
                                            if first_sent is None:
                                                first_sent = sent
                                        t_link = f"https://t.me/{destination_channel[1:]}/{first_sent.id}"
                                        new_conf.append({
                                            'protocol': prot, 'config': c, 'latency': lat,
                                            'channel': title, 't_link': t_link,
                                            'flag': flag, 'country': country,
                                            'ts': time.time()
                                        })
                                        unique_fingerprints.add(u_key)
                                    except Exception as e:
                                        print(f"❌ Error sending full config: {e}")

                        # 1.2 Proxies
                        found_proxies = set()
                        regex_matches = re.findall(r"https://t.me/proxy\?[^\s\n]+|tg://proxy\?[^\s\n]+", m.text)
                        for p in regex_matches:
                            clean_p = p.replace('https://t.me/proxy', 'tg://proxy')
                            found_proxies.add(clean_p)
                        
                        if m.entities:
                            for ent in m.entities:
                                if isinstance(ent, MessageEntityTextUrl):
                                    url = ent.url
                                    if 'proxy' in url and ('server=' in url or 'secret=' in url):
                                        clean_url = url.replace('https://t.me/proxy', 'tg://proxy')
                                        found_proxies.add(clean_url)

                        for p in found_proxies:
                            if p not in sent_hashes:
                                stat, lat, flag, country = await process_item(p, 'proxy')
                                if stat:
                                    m_search = re.search(r"server=([\w\.-]+)&port=(\d+)", p)
                                    key_p = f"{m_search.group(1)}:{m_search.group(2)}" if m_search else str(time.time())
                                    channel_proxies.append({
                                        'link': p, 'flag': flag, 'stat': stat, 'lat': lat, 'key': key_p
                                    })
                                    sent_hashes.add(p)

                    # --- Section 2: File Processing (preserve original file and caption) ---
                    if m.file and m.file.name:
                        file_ext = "." + m.file.name.split('.')[-1].lower() if '.' in m.file.name else ""
                        
                        if any(m.file.name.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
                            if link not in sent_hashes:
                                try:
                                    print(f"📂 Found File: {m.file.name}")
                                    
                                    # Keep the original file binary, name and caption intact.
                                    original_caption = m.message or ""
                                    source_line = f"منبع اصلی: {link}"
                                    if telegram_text_units(original_caption) <= 650:
                                        preserved_caption = (
                                            original_caption
                                            + ("\n\n" if original_caption else "")
                                            + source_line
                                            + create_footer(title, channel_str)
                                        )
                                    else:
                                        preserved_caption = (
                                            f"📂 {m.file.name}\n{source_line}\n"
                                            "کپشن کامل مبدأ در پیام‌های بلافاصله بعد آمده است."
                                        )
                                    sent_file = await client.send_file(
                                        destination_channel, m.media,
                                        caption=preserved_caption, parse_mode=None
                                    )
                                    if telegram_text_units(original_caption) > 650:
                                        caption_parts = split_text_lossless(original_caption)
                                        for part_index, chunk in enumerate(caption_parts, 1):
                                            await client.send_message(
                                                destination_channel,
                                                f"📎 کپشن اصلی {m.file.name} • بخش {part_index}/{len(caption_parts)}\n\n{chunk}",
                                                link_preview=False, parse_mode=None
                                            )
                                    new_file.append({
                                        'name': m.file.name,
                                        'ext': file_ext.replace('.', '').upper(),
                                        'channel': title,
                                        'link': link,
                                        't_link': f"https://t.me/{destination_channel[1:]}/{sent_file.id}",
                                        'original_caption': original_caption,
                                        'ts': time.time()
                                    })
                                    sent_hashes.add(link)
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
        all_configs = all_configs[:100]

        all_proxies = hist['proxies'] + new_prox
        all_proxies.sort(key=lambda x: x['ts'], reverse=True)
        all_proxies = all_proxies[:100]
        
        all_files = hist['files'] + new_file
        all_files.sort(key=lambda x: x['ts'], reverse=True)
        all_files = all_files[:50]

        save_data({'configs': all_configs, 'proxies': all_proxies, 'files': all_files})
        
        # Subscription Link (اضافه شدن slipnet به ساب لینک)
        sub_content = ""
        for c in all_configs:
            if c['config'].startswith(('vmess', 'vless', 'trojan', 'ss', 'hy2', 'tuic', 'slipnet-enc')):
                sub_content += c['config'] + "\n"
        
        with open(SUB_FILE, 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(sub_content.encode('utf-8')).decode('utf-8'))

        # index.html is a static frontend and is no longer regenerated by the scraper.
        with open('manifest.json', 'w', encoding='utf-8') as f:
            json.dump({
                "name": "VPN Hub",
                "short_name": "VPN Hub",
                "start_url": "./index.html",
                "display": "standalone",
                "background_color": "#f5f7fa",
                "theme_color": "#087e8b"
            }, f, ensure_ascii=False, indent=2)

        with open('sw.js', 'w', encoding='utf-8') as f:
            f.write("self.addEventListener('install',e=>e.waitUntil(caches.open('vpn-v2').then(c=>c.addAll(['./','./index.html','./src/style.css','./src/main.js','./manifest.json']))));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));")

    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally: await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
