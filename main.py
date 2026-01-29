import os
import re
import json
import base64
import socket
import requests
import jdatetime
import pytz
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl

# --- تنظیمات ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

# لیست نهایی و آپدیت شده کانال‌ها
source_channels = [
    '@KioV2ray', '@Npvtunnel_vip', '@planB_net', '@Free_Nettm', '@mypremium98',
    '@mitivpn', '@iSeqaro', '@configraygan', '@shankamil', '@xsfilternet',
    '@varvpn1', '@iP_CF', '@cooonfig', '@DeamNet', '@anty_filter',
    '@vpnboxiran', '@Merlin_ViP', '@BugFreeNet', '@cicdoVPN', '@Farda_Ai',
    '@Awlix_ir', '@proSSH', '@vpn_proxy_custom', '@Free_HTTPCustom',
    '@sinavm', '@Amir_Alternative_Official', '@StayconnectedVPN', '@BINNER_IRAN',
    '@IranianMinds', '@vpn11ir', '@NetAccount', '@mitiivpn2', '@isharewin',
    '@v2rays_ha', '@iroproxy', '@ProxyMTProto',
    
    # موارد جدید اضافه شده
    '@darkproxy', '@configs_freeiran', '@v2rayvpnchannel'
]

destination_channel = '@myvpn1404'
allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')

client = TelegramClient(StringSession(session_string), api_id, api_hash)

# --- توابع کمکی (پینگ و پرچم) ---

def get_flag_emoji(country_code):
    """تبدیل کد کشور به ایموجی"""
    if not country_code: return "🏳️"
    return chr(127397 + ord(country_code[0])) + chr(127397 + ord(country_code[1]))

def get_ip_info(ip):
    """گرفتن اطلاعات کشور"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode,country", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return data.get("countryCode", "UN"), data.get("country", "Unknown")
    except:
        pass
    return None, None

def tcp_ping(host, port, timeout=2):
    """تست اتصال (Ping)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start_time = datetime.now()
        result = sock.connect_ex((host, int(port)))
        end_time = datetime.now()
        sock.close()
        
        if result == 0:
            duration = (end_time - start_time).microseconds / 1000
            return int(duration)
        return False
    except:
        return False

def parse_config(config_str):
    """استخراج IP و Port از کانفیگ"""
    try:
        if config_str.startswith("vmess://"):
            b64 = config_str.replace("vmess://", "")
            missing_padding = len(b64) % 4
            if missing_padding: b64 += '=' * (4 - missing_padding)
            decoded = base64.b64decode(b64).decode('utf-8')
            data = json.loads(decoded)
            return data.get("add"), data.get("port")
        
        elif config_str.startswith("vless://") or config_str.startswith("trojan://") or config_str.startswith("ss://"):
            match = re.search(r"@([\w\.-]+):(\d+)", config_str)
            if match: return match.group(1), match.group(2)
    except: pass
    return None, None

def parse_proxy(proxy_link):
    """استخراج IP و Port از لینک پروکسی"""
    try:
        # جستجوی server=...&port=...
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match:
            return match.group(1), match.group(2)
    except: pass
    return None, None

# --- ساخت کپشن ---
def create_caption(content_type, extra_info, source_name, ping_time=None, country_name=None):
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    status_line = ""
    if ping_time:
        status_line = f"\n⚡️ Ping: {ping_time}ms | {country_name}"
    
    caption = (
        f"{content_type}\n"
        f"➖➖➖➖➖➖➖\n"
        f"🏷 {extra_info}"
        f"{status_line}\n"
        f"➖➖➖➖➖➖➖\n"
        f"📅 {date_str} | ⏰ {time_str}\n"
        f"📢 Source: {source_name}\n"
        f"🆔 {destination_channel}"
    )
    return caption

async def main():
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
    config_regex = r"(?:vmess|vless|trojan|ss|tuic|hysteria|nm|nm-xray-json|nm-vless|nm-vmess)://[^\s\n]+"
    
    print("--- 1. Syncing History ---")
    sent_hashes = set()
    try:
        async for msg in client.iter_messages(destination_channel, limit=200):
            if msg.file and msg.file.name: sent_hashes.add(msg.file.name)
            if msg.text:
                matches = re.findall(config_regex, msg.text)
                for c in matches: sent_hashes.add(c.strip())
                proxies = re.findall(r"server=([\w\.-]+)", msg.text)
                for p in proxies: sent_hashes.add(p)
    except: pass

    print("--- 2. Checking Sources ---")

    for channel in source_channels:
        try:
            print(f"Checking {channel}...")
            try:
                entity = await client.get_entity(channel)
                title = entity.title if entity.title else channel
            except: continue

            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                # --- A. بخش کانفیگ‌های متنی ---
                if message.text:
                    raw_matches = re.findall(config_regex, message.text)
                    for conf in raw_matches:
                        clean_conf = conf.strip()
                        if clean_conf not in sent_hashes:
                            ip, port = parse_config(clean_conf)
                            ping_val = None; country_txt = ""
                            
                            if ip and port:
                                ping_val = tcp_ping(ip, port)
                                if ping_val:
                                    cc, c_name = get_ip_info(ip)
                                    flag = get_flag_emoji(cc)
                                    country_txt = f"{flag} {c_name}"
                                    
                                    prot = clean_conf.split("://")[0].upper()
                                    final_txt = f"🔮 **{prot} Config** {flag}\n\n`{clean_conf}`"
                                    cap = create_caption(final_txt, f"Protocol: {prot}", title, ping_val, country_txt)
                                    
                                    try:
                                        await client.send_message(destination_channel, cap, link_preview=False)
                                        sent_hashes.add(clean_conf)
                                    except: pass
                                else:
                                    sent_hashes.add(clean_conf) # Skip dead config
                            elif "nm-" in clean_conf:
                                cap = create_caption(f"📱 **NetMod Config**\n\n{clean_conf}", "App: NetMod", title)
                                await client.send_message(destination_channel, cap)
                                sent_hashes.add(clean_conf)

                # --- B. بخش پروکسی‌ها (بهبود یافته) ---
                extracted_proxies = []
                if message.entities:
                    for ent in message.entities:
                        if isinstance(ent, MessageEntityTextUrl) and "proxy?server=" in ent.url:
                            extracted_proxies.append(ent.url)
                if message.text:
                    extracted_proxies.extend(re.findall(r"(tg://proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+)", message.text))
                
                valid_proxies = []
                
                # پردازش و تست پروکسی‌ها
                unique_proxies = list(set(extracted_proxies))
                if unique_proxies:
                    print(f"Testing {len(unique_proxies)} proxies...")
                    
                    for p in unique_proxies:
                        try:
                            # 1. استخراج سرور و پورت
                            p_ip, p_port = parse_proxy(p)
                            if p_ip and p_port and p_ip not in sent_hashes:
                                # 2. تست پینگ
                                ping = tcp_ping(p_ip, p_port, timeout=1)
                                if ping:
                                    # 3. گرفتن پرچم
                                    cc, _ = get_ip_info(p_ip)
                                    flag = get_flag_emoji(cc)
                                    
                                    # استانداردسازی لینک
                                    final_link = p.replace("https://t.me/", "tg://")
                                    
                                    # اضافه کردن به لیست با فرمت جدید
                                    # فرمت: پرچم - دکمه اتصال - پینگ
                                    link_text = f"{flag} اتصال (Ping: {ping}ms)"
                                    valid_proxies.append(f"[{link_text}]({final_link})")
                                    
                                    sent_hashes.add(p_ip)
                        except: pass

                # ارسال لیست پروکسی‌های سالم
                if valid_proxies:
                    proxy_body = "🔵 **MTProto Proxy List**\n\n"
                    for i, link_md in enumerate(valid_proxies, 1):
                        proxy_body += f"{i}. {link_md}\n"
                    
                    # محاسبه میانگین پینگ برای کپشن
                    cap = create_caption(proxy_body, f"New Proxies ({len(valid_proxies)}x)", title)
                    await client.send_message(destination_channel, cap, link_preview=False)
                    print(f"Sent {len(valid_proxies)} verified proxies")

                # --- C. بخش فایل‌ها ---
                if message.file:
                    fname = message.file.name if message.file.name else "Config"
                    if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                        if fname not in sent_hashes:
                            file_type = fname.split('.')[-1].upper()
                            cap = create_caption(f"📂 **File: {file_type}**", fname, title)
                            await client.send_file(destination_channel, message.media, caption=cap)
                            sent_hashes.add(fname)

        except Exception as e:
            print(f"Error on {channel}: {e}")

    print("--- End ---")

with client:
    client.loop.run_until_complete(main())
