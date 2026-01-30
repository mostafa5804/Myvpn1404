import os
import re
import jdatetime
import pytz
import asyncio
import json
import base64
import socket
import random
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from telethon.errors.rpcerrorlist import FloodWaitError

# -----------------------------------------------------------------------------
# تنظیمات و متغیرهای اصلی
# -----------------------------------------------------------------------------
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
MAX_PING_WAIT = 4

# لیست کامل کانال‌ها (40 عدد)
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

destination_channel = '@myvpn1404'
allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')

client = TelegramClient(StringSession(session_string), api_id, api_hash)

IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

# -----------------------------------------------------------------------------
# توابع کمکی (Helper Functions)
# -----------------------------------------------------------------------------

def is_iran_ip(ip):
    try:
        for prefix in IRAN_IP_PREFIXES:
            if ip.startswith(prefix): return True
        return False
    except: return False

def get_channel_batch():
    """چرخه ۸۰ دقیقه‌ای دقیق: دقیقه ۰ تا ۴۰ (دسته ۱)، ۴۰ تا ۸۰ (دسته ۲)"""
    now = datetime.now(iran_tz)
    batch_index = ((now.hour * 60 + now.minute) // 40) % 2
    if batch_index == 0:
        return ALL_CHANNELS[:20], "اول (1-20)"
    else:
        return ALL_CHANNELS[20:40], "دوم (21-40)"

async def measure_tcp_latency(host, port, timeout=2):
    import time
    try:
        start = time.time()
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        latency = int((time.time() - start) * 1000)
        writer.close()
        await writer.wait_closed()
        return latency
    except: return None

async def check_and_format_status(host, port, timeout=2):
    if not host or not port: return None, None, False
    try:
        latency = await measure_tcp_latency(host, port, timeout)
        is_intranet = False
        try:
            ip_address = socket.gethostbyname(host)
            if is_iran_ip(ip_address) and latency is None: is_intranet = True
        except: pass
        
        if latency is None:
            if is_intranet: return "🔵 اینترانت", None, True
            return "🔴 آفلاین", None, False
        
        if latency < 100: return "🟢 عالی", latency, False
        elif latency < 200: return "🟡 خوب", latency, False
        elif latency < 400: return "🟠 متوسط", latency, False
        else: return "🔴 ضعیف", latency, False
    except: return None, None, False

def extract_server_info(config):
    try:
        protocol = config.split("://")[0].lower()
        if protocol == "vmess":
            encoded = config.split("://")[1]
            decoded = json.loads(base64.b64decode(encoded))
            return decoded.get("add"), int(decoded.get("port", 443))
        elif protocol in ["vless", "trojan", "ss", "shadowsocks", "hysteria", "hysteria2", "hy2", "tuic"]:
            match = re.search(r"@([\w\.-]+):(\d+)", config)
            if match: return match.group(1), int(match.group(2))
        return None, None
    except: return None, None

def extract_proxy_info(proxy_link):
    try:
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match: return match.group(1), int(match.group(2))
        return None, None
    except: return None, None

async def safe_check_config(config, max_wait=4):
    try:
        host, port = extract_server_info(config)
        if host and port:
            return await asyncio.wait_for(check_and_format_status(host, port, timeout=PING_TIMEOUT), timeout=max_wait)
        return None, None, False
    except: return "⏱️ Timeout", None, False

async def safe_check_proxy(proxy_link, max_wait=4):
    try:
        host, port = extract_proxy_info(proxy_link)
        if host and port:
            return await asyncio.wait_for(check_and_format_status(host, port, timeout=PING_TIMEOUT), timeout=max_wait)
        return None, None, False
    except: return "⏱️ Timeout", None, False

def generate_qr_url(config):
    from urllib.parse import quote
    encoded = quote(config)
    return f"[https://quickchart.io/qr?text=](https://quickchart.io/qr?text=){encoded}&size=300"

def get_file_usage_guide(file_name):
    ext = file_name.lower().split('.')[-1]
    apps = {'npv4': 'NapsternetV', 'ehi': 'HTTP Injector', 'txt': 'v2rayNG', 'conf': 'Shadowrocket', 'json': 'v2rayNG'}
    return f"📱 {apps.get(ext, 'v2rayNG')}"

def get_config_usage_guide(config_link):
    protocol = config_link.split("://")[0].lower()
    apps = {'vmess': 'v2rayNG', 'vless': 'v2rayNG', 'trojan': 'v2rayNG', 'ss': 'Shadowsocks', 'hysteria': 'NekoBox', 'tuic': 'SingBox'}
    return f"📱 {apps.get(protocol, 'v2rayNG • Hiddify')}"

def get_proxy_usage_guide():
    return "💡 برای اتصال روی لینک کلیک کنید"

# --- فوتر مینیمال و ساده ---
def create_minimal_footer(channel_title, message_link):
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    # خط جداکننده ساده و شیک + منبع لینک دار + آیدی کانال شما
    footer = f"\n━━━━━━━━━━━━━━━━\n"
    footer += f"🗓 {date_str} • 🕐 {time_str}\n"
    footer += f"📡 منبع: [{channel_title}]({message_link})\n"
    footer += f"🔗 {destination_channel}"
    return footer

# -----------------------------------------------------------------------------
# تابع اصلی برنامه
# -----------------------------------------------------------------------------
async def main():
    try:
        await client.start()
        print("✅ ربات متصل شد")
        
        initial_wait = random.randint(10, 20)
        print(f"⏳ صبر {initial_wait} ثانیه...")
        await asyncio.sleep(initial_wait)
        
        source_channels, batch_name = get_channel_batch()
        print(f"--- شروع بررسی دسته {batch_name} ---")
        
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1.5)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        sent_files = set(); sent_proxies = set(); sent_configs = set()
        
        # بارگذاری تاریخچه
        try:
            print("بارگذاری تاریخچه...")
            async for msg in client.iter_messages(destination_channel, limit=150):
                if msg.file and msg.file.name: sent_files.add(msg.file.name)
                if msg.text:
                    [sent_configs.add(c.strip()) for c in re.findall(config_regex, msg.text)]
                    [sent_proxies.add(f"{m[0]}:{m[1]}") for m in re.findall(r"server=([\w\.-]+)&port=(\d+)", msg.text)]
            print("✅ تاریخچه لود شد")
        except: pass

        sent_count = 0; MAX_PER_RUN = 40; live_configs = []; all_files_data = {}; all_proxies_data = {}
        
        # حلقه اصلی روی کانال‌ها
        for i, channel_username in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN: break
            
            try:
                if i > 0: await asyncio.sleep(random.uniform(5, 8))
                print(f"\n🔍 کانال {i+1}/20: {channel_username}")
                
                try:
                    entity = await client.get_entity(channel_username)
                    ch_title = entity.title if hasattr(entity, 'title') else channel_username
                except: ch_title = channel_username
                
                # مخازن موقت برای این کانال
                temp_files = []
                temp_proxies = []
                temp_configs = []
                
                async for message in client.iter_messages(entity, offset_date=time_threshold, reverse=True, limit=40):
                    orig_link = f"[https://t.me/](https://t.me/){channel_username[1:]}/{message.id}"
                    
                    # 1. جمع‌آوری فایل
                    if message.file:
                        fname = message.file.name if message.file.name else ""
                        if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                            if fname not in sent_files:
                                temp_files.append({'name': fname, 'media': message.media, 'link': orig_link})
                    
                    # 2. جمع‌آوری پروکسی
                    if message.text or message.entities:
                        p_links = re.findall(r"(?:tg|https)://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+", message.text or "")
                        for p in list(set(p_links)):
                            host, port = extract_proxy_info(p)
                            if host:
                                key = f"{host}:{port}"
                                if key not in sent_proxies:
                                    temp_proxies.append({'link': p.replace("[https://t.me/](https://t.me/)", "tg://"), 'key': key, 'orig_link': orig_link})

                    # 3. جمع‌آوری کانفیگ
                    if message.text:
                        confs = re.findall(config_regex, message.text)
                        for c in confs:
                            clean = c.strip()
                            if clean not in sent_configs:
                                temp_configs.append({'config': clean, 'orig_link': orig_link})

                print(f"📊 یافت شد: {len(temp_files)} فایل، {len(temp_proxies)} پروکسی، {len(temp_configs)} کانفیگ")

                # --- ارسال فایل‌ها (تکی) ---
                for item in temp_files:
                    if sent_count >= MAX_PER_RUN: break
                    try:
                        caption = f"📂 **{item['name']}**\n"
                        caption += f"{get_file_usage_guide(item['name'])}\n"
                        caption += create_minimal_footer(ch_title, item['link'])
                        
                        sent_msg = await client.send_file(destination_channel, item['media'], caption=caption)
                        
                        my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent_msg.id}"
                        all_files_data[item['name']] = {'channel': ch_title, 'link': my_link}
                        sent_files.add(item['name']); sent_count += 1
                        await asyncio.sleep(3)
                    except Exception as e: print(f"❌ فایل: {e}")

                # --- ارسال پروکسی‌ها (گروهی/Grouped) ---
                # تغییر مهم: همه پروکسی‌های این کانال را تست کن و در یک پیام بفرست
                valid_proxies_in_channel = []
                if temp_proxies:
                    print(f"  🔍 تست {len(temp_proxies)} پروکسی...")
                    for item in temp_proxies:
                        if sent_count >= MAX_PER_RUN: break
                        status, lat, is_in = await safe_check_proxy(item['link'])
                        if status:
                            flag = "🇮🇷" if is_in else "🌍"
                            ping_str = f"{lat}ms" if lat else ""
                            valid_proxies_in_channel.append({
                                'link': item['link'], 'ping': ping_str, 'status': status, 'flag': flag, 
                                'key': item['key'], 'orig_link': item['orig_link']
                            })
                            sent_proxies.add(item['key'])
                            
                            # برای صفحه وب ذخیره میکنیم (لینک تلگرام رو بعدا آپدیت میکنیم یا اولین لینک رو میذاریم)
                            all_proxies_data[item['key']] = {'link': item['link'], 'channel': ch_title, 't_link': '#'}
                
                # اگر پروکسی سالمی پیدا شد، همه را در یک پیام بفرست
                if valid_proxies_in_channel:
                    try:
                        msg_body = "🔵 **پروکسی‌های جدید**\n\n"
                        for i, p in enumerate(valid_proxies_in_channel, 1):
                            msg_body += f"{i}. [اتصال]({p['link']}) • {p['flag']} {p['status']} {p['ping']}\n"
                        
                        msg_body += get_proxy_usage_guide()
                        # لینک منبع رو از اولین پروکسی لیست برمیداریم
                        msg_body += create_minimal_footer(ch_title, valid_proxies_in_channel[0]['orig_link'])
                        
                        sent_msg = await client.send_message(destination_channel, msg_body, link_preview=False)
                        print(f"  ✅ لیست پروکسی ارسال شد ({len(valid_proxies_in_channel)} عدد)")
                        
                        # آپدیت لینک وب برای همه این پروکسی‌ها
                        my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent_msg.id}"
                        for p in valid_proxies_in_channel:
                            all_proxies_data[p['key']]['t_link'] = my_link
                            
                        sent_count += 1
                        await asyncio.sleep(3)
                    except Exception as e: print(f"❌ ارسال گروهی پروکسی: {e}")

                # --- ارسال کانفیگ‌ها (تکی با Copy Code) ---
                for item in temp_configs:
                    if sent_count >= MAX_PER_RUN: break
                    try:
                        status, lat, is_in = await safe_check_config(item['config'])
                        if status:
                            prot = item['config'].split("://")[0].upper()
                            ping_txt = f"{lat}ms" if lat else ""
                            
                            # استایل مینیمال با دکمه کپی
                            txt = f"🔮 **{prot}**\n\n"
                            txt += f"```{item['config']}```\n" # دکمه کپی
                            txt += f"📊 وضعیت: {status} • {ping_txt}\n"
                            txt += f"{get_config_usage_guide(item['config'])}\n"
                            txt += create_minimal_footer(ch_title, item['orig_link'])
                            
                            # نکته مهم: link_preview=False برای جلوگیری از دوتایی شدن و نمایش پایین پیام
                            sent_msg = await client.send_message(destination_channel, txt, link_preview=False)
                            
                            my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent_msg.id}"
                            live_configs.append({
                                'protocol': prot, 'config': item['config'],
                                'latency': lat or 999, 'status': status,
                                'channel': ch_title, 't_link': my_link
                            })
                            sent_configs.add(item['config'])
                            sent_count += 1
                            print(f"  ✅ کانفیگ ارسال شد: {prot}")
                            await asyncio.sleep(3)
                    except Exception as e: print(f"❌ کانفیگ: {e}")

            except Exception as e:
                print(f"⚠️ خطا در کانال {channel_username}: {e}")
                continue

        # -----------------------------------------------------------------------------
        # ساخت صفحه وب (GitHub Pages) - موبایل فرندلی، دارک مود، کارت ویو
        # -----------------------------------------------------------------------------
        try:
            print("\n📄 ساخت صفحه وب...")
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub - {destination_channel}</title>
    <link href="[https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css](https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css)" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0f172a; --card-bg: #1e293b; --primary: #38bdf8;
            --text-main: #f1f5f9; --text-sub: #94a3b8; --border: #334155;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Vazirmatn', sans-serif; -webkit-tap-highlight-color: transparent; }}
        body {{ background-color: var(--bg-color); color: var(--text-main); padding-bottom: 80px; }}
        .header {{ text-align: center; padding: 20px 15px; border-bottom: 1px solid var(--border); background: rgba(15, 23, 42, 0.95); position: sticky; top: 0; z-index: 50; backdrop-filter: blur(10px); }}
        .header h1 {{ font-size: 1.4rem; color: var(--primary); margin-bottom: 5px; }}
        .header p {{ font-size: 0.8rem; color: var(--text-sub); }}
        .help-btn {{ position: absolute; left: 15px; top: 50%; transform: translateY(-50%); background: none; border: none; font-size: 1.2rem; cursor: pointer; color: var(--primary); }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 15px; }}
        .card {{ background: var(--card-bg); border-radius: 16px; padding: 16px; margin-bottom: 16px; border: 1px solid var(--border); box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); animation: fadeIn 0.4s ease; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .protocol-tag {{ background: #334155; padding: 4px 10px; border-radius: 8px; font-size: 0.75rem; font-weight: bold; color: #e2e8f0; }}
        .ping-tag {{ font-size: 0.8rem; font-weight: bold; display: flex; align-items: center; gap: 4px; }}
        .channel-info {{ font-size: 0.75rem; color: var(--text-sub); margin-bottom: 10px; display: flex; align-items: center; gap: 5px; }}
        .code-block {{ background: #0b1120; border: 1px dashed var(--border); border-radius: 10px; padding: 12px; font-family: monospace; font-size: 0.75rem; color: #22d3ee; overflow-x: auto; white-space: nowrap; margin-bottom: 12px; direction: ltr; }}
        .action-btns {{ display: flex; gap: 10px; }}
        .btn {{ flex: 1; padding: 12px; border-radius: 10px; border: none; font-size: 0.9rem; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; text-decoration: none; transition: 0.2s; }}
        .btn-copy {{ background: var(--primary); color: #0f172a; }}
        .btn-connect {{ background: transparent; border: 1px solid var(--primary); color: var(--primary); }}
        .btn-source {{ width: 100%; margin-top: 10px; background: #334155; color: #cbd5e1; font-size: 0.8rem; padding: 8px; }}
        .bottom-nav {{ position: fixed; bottom: 0; left: 0; right: 0; background: rgba(30, 41, 59, 0.95); backdrop-filter: blur(10px); border-top: 1px solid var(--border); display: flex; justify-content: space-around; padding: 10px 0; z-index: 100; padding-bottom: max(10px, env(safe-area-inset-bottom)); }}
        .nav-item {{ display: flex; flex-direction: column; align-items: center; gap: 4px; color: var(--text-sub); font-size: 0.75rem; cursor: pointer; flex: 1; }}
        .nav-item.active {{ color: var(--primary); font-weight: bold; }}
        .nav-icon {{ font-size: 1.2rem; margin-bottom: 2px; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 200; align-items: center; justify-content: center; padding: 20px; }}
        .modal-content {{ background: var(--card-bg); width: 100%; max-width: 400px; border-radius: 20px; padding: 25px; position: relative; border: 1px solid var(--border); }}
        .close-modal {{ position: absolute; left: 20px; top: 20px; font-size: 1.5rem; color: #ef4444; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="header">
        <button class="help-btn" onclick="openModal()">ℹ️</button>
        <h1>VPN Hub</h1>
        <p>{now_str}</p>
    </div>

    <div class="container">
        <div id="tab-configs" class="tab-content active">
            {"".join([f'''
            <div class="card">
                <div class="card-header">
                    <span class="protocol-tag">{c['protocol']}</span>
                    <span class="ping-tag" style="color:{'#4ade80' if c['latency']<200 else '#facc15'}">⚡ {c['latency']}ms</span>
                </div>
                <div class="channel-info">📡 منبع: {c['channel']}</div>
                <div class="code-block" id="conf-{i}">{c['config']}</div>
                <div class="action-btns">
                    <button class="btn btn-copy" onclick="copyText('conf-{i}')">کپی</button>
                    <a href="{c['config']}" class="btn btn-connect">اتصال</a>
                </div>
                <a href="{c['t_link']}" class="btn btn-source">🔗 مشاهده در کانال ما</a>
            </div>
            ''' for i, c in enumerate(live_configs)])}
            {f'<div style="text-align:center;color:#64748b;padding:20px">کانفیگی یافت نشد...</div>' if not live_configs else ''}
        </div>

        <div id="tab-proxies" class="tab-content">
            {"".join([f'''
            <div class="card">
                <div class="card-header"><span class="protocol-tag">MTProto</span><span class="ping-tag" style="color:#facc15">Proxy</span></div>
                <div class="channel-info">📡 منبع: {v['channel']}</div>
                <div class="code-block">Server: {k.split(':')[0]}</div>
                <div class="action-btns">
                    <a href="{v['link']}" class="btn btn-copy">اتصال سریع</a>
                </div>
                <a href="{v['t_link']}" class="btn btn-source">🔗 مشاهده در کانال ما</a>
            </div>
            ''' for k, v in all_proxies_data.items()])}
        </div>
        
        <div id="tab-files" class="tab-content">
            {"".join([f'''
            <div class="card">
                <div class="card-header"><span class="protocol-tag">FILE</span><span class="protocol-tag" style="background:#475569">{name.split('.')[-1]}</span></div>
                <div style="margin:15px 0;font-weight:bold;font-size:0.9rem">{name}</div>
                <div class="channel-info">📡 منبع: {v['channel']}</div>
                <a href="{v['link']}" class="btn btn-connect" style="width:100%">📥 دانلود از کانال ما</a>
            </div>
            ''' for name, v in all_files_data.items()])}
        </div>
    </div>

    <div class="bottom-nav">
        <div class="nav-item active" onclick="switchTab('tab-configs', this)"><span class="nav-icon">🚀</span><span>کانفیگ</span></div>
        <div class="nav-item" onclick="switchTab('tab-proxies', this)"><span class="nav-icon">🛡️</span><span>پروکسی</span></div>
        <div class="nav-item" onclick="switchTab('tab-files', this)"><span class="nav-icon">📂</span><span>فایل</span></div>
    </div>

    <div id="helpModal" class="modal">
        <div class="modal-content">
            <span class="close-modal" onclick="closeModal()">&times;</span>
            <h3 style="color:var(--primary);margin-bottom:15px">راهنما</h3>
            <p style="font-size:0.9rem;line-height:1.8;color:#cbd5e1">
            1. <b>کپی هوشمند:</b> دکمه کپی را بزنید، کد خودکار کپی می‌شود.<br>
            2. <b>اتصال مستقیم:</b> دکمه اتصال، برنامه v2rayNG را باز می‌کند.<br>
            3. <b>منبع:</b> تمام لینک‌ها برای امنیت به کانال {destination_channel} ارجاع داده می‌شوند.
            </p>
        </div>
    </div>

    <script>
        function switchTab(tabId, element) {{
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            element.classList.add('active');
            window.scrollTo(0, 0);
        }}
        function copyText(elementId) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => alert('✅ کپی شد!'));
        }}
        function openModal() {{ document.getElementById('helpModal').style.display = 'flex'; }}
        function closeModal() {{ document.getElementById('helpModal').style.display = 'none'; }}
        window.onclick = function(event) {{
            if (event.target == document.getElementById('helpModal')) closeModal();
        }}
    </script>
</body>
</html>"""
            
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            print("✅ صفحه وب ساخته شد")
            
        except Exception as e: print(f"❌ خطا HTML: {e}")

        print(f"\n✅ پایان عملیات ({sent_count} مورد)")

    except Exception as e: print(f"❌ خطای حیاتی: {e}")
    finally: await client.disconnect()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
