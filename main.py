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

# --- تنظیمات ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
MAX_PING_WAIT = 4

# لیست کامل کانال‌ها (40 تا)
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

def is_iran_ip(ip):
    try:
        for prefix in IRAN_IP_PREFIXES:
            if ip.startswith(prefix): return True
        return False
    except: return False

def get_channel_batch():
    now = datetime.now(iran_tz)
    # چرخه 80 دقیقه‌ای (دقیقه 0 دسته اول، دقیقه 40 دسته دوم)
    batch_index = ((now.hour * 60 + now.minute) // 40) % 2
    if batch_index == 0:
        return ALL_CHANNELS[:20], "اول (1-20)"
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
            return ("🔵 اینترانت", None, True) if is_intranet else ("🔴 آفلاین", None, False)
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
    return f"https://quickchart.io/qr?text={quote(config)}&size=300"

def get_file_usage_guide(file_name):
    ext = file_name.lower().split('.')[-1]
    apps = {'npv4': 'NapsternetV • v2rayNG', 'ehi': 'HTTP Injector', 'txt': 'Hiddify • NekoBox'}
    return f"\n📱 {apps.get(ext, 'v2rayNG • Hiddify')}\n"

def get_config_usage_guide(config_link):
    prot = config_link.split("://")[0].lower()
    apps = {'vmess': 'v2rayNG • V2Box', 'vless': 'Hiddify • NekoBox'}
    return f"\n📱 {apps.get(prot, 'v2rayNG • Hiddify')}\n"

def get_proxy_usage_guide():
    return "\n💡 روی لینک کلیک کنید، تلگرام خودکار متصل می‌شود\n"

def create_footer(channel_name, extra_info=""):
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    footer = f"\n#{extra_info or 'VPN'}\n🗓 {date_str} • 🕐 {time_str}\n📡 {channel_name}\n🔗 {destination_channel}"
    return footer

async def main():
    try:
        await client.start()
        print("✅ متصل شد")
        await asyncio.sleep(random.randint(5, 10))
        
        # اصلاح تداخل: تفکیک لیست از نام دسته
        source_channels, batch_name = get_channel_batch()
        print(f"--- شروع بررسی دسته {batch_name} ---")
        
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1.5)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        sent_files = set(); sent_proxies = set(); sent_configs = set()
        async for msg in client.iter_messages(destination_channel, limit=150):
            if msg.file and msg.file.name: sent_files.add(msg.file.name)
            if msg.text:
                [sent_configs.add(c.strip()) for c in re.findall(config_regex, msg.text)]
                [sent_proxies.add(f"{m[0]}:{m[1]}") for m in re.findall(r"server=([\w\.-]+)&port=(\d+)", msg.text)]

        sent_count = 0; MAX_PER_RUN = 40; live_configs = []; all_files_data = {}; all_proxies_data = {}
        
        # بررسی کانال‌به‌کانال (Channel-by-Channel)
        for i, channel in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN: break
            try:
                await asyncio.sleep(random.uniform(4, 7))
                print(f"🔍 کانال {i+1}/20: {channel}")
                
                ch_title = None
                items = {'files': [], 'proxies': [], 'configs': []}
                
                async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True, limit=40):
                    if not ch_title and hasattr(message.chat, 'title'): ch_title = message.chat.title
                    
                    if message.file and any(message.file.name.lower().endswith(ext) for ext in allowed_extensions if message.file.name):
                        if message.file.name not in sent_files:
                            items['files'].append({'name': message.file.name, 'media': message.media, 'id': message.id})
                    
                    p_links = re.findall(r"(?:tg|https)://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+", message.text or "")
                    for p in list(set(p_links)):
                        host, port = extract_proxy_info(p)
                        if host and f"{host}:{port}" not in sent_proxies:
                            items['proxies'].append({'link': p.replace("https://t.me/", "tg://"), 'key': f"{host}:{port}", 'id': message.id})
                    
                    configs = re.findall(config_regex, message.text or "")
                    for c in configs:
                        if c.strip() not in sent_configs:
                            items['configs'].append({'config': c.strip(), 'id': message.id})

                ch_title = ch_title or channel
                
                # ارسال فایل
                for f in items['files']:
                    if sent_count >= MAX_PER_RUN: break
                    cap = f"📂 **{f['name']}**" + get_file_usage_guide(f['name']) + create_footer(ch_title, f['name'].split('.')[-1])
                    await client.send_file(destination_channel, f['media'], caption=cap)
                    sent_files.add(f['name']); all_files_data[f['name']] = {'channel': ch_title, 'link': f"https://t.me/{channel[1:]}/{f['id']}"}
                    sent_count += 1; await asyncio.sleep(3)

                # ارسال پروکسی
                for p in items['proxies']:
                    if sent_count >= MAX_PER_RUN: break
                    status, lat, is_in = await safe_check_proxy(p['link'])
                    if status:
                        txt = f"🔵 **پروکسی جدید**\n\n[اتصال]({p['link']}) • {status}\n" + get_proxy_usage_guide() + create_footer(ch_title, "proxy")
                        await client.send_message(destination_channel, txt, link_preview=False)
                        sent_proxies.add(p['key']); all_proxies_data[p['key']] = {'link': p['link'], 'channel': ch_title, 't_link': f"https://t.me/{channel[1:]}/{p['id']}"}
                        sent_count += 1; await asyncio.sleep(3)

                # ارسال کانفیگ
                for c in items['configs']:
                    if sent_count >= MAX_PER_RUN: break
                    status, lat, is_in = await safe_check_config(c['config'])
                    if status:
                        prot = c['config'].split("://")[0].upper()
                        qr = generate_qr_url(c['config'])
                        txt = f"🔮 **کانفیگ {prot}**\n\n`{c['config']}`\n\n📊 {status}\n" + get_config_usage_guide(c['config']) + f"[​]({qr})" + create_footer(ch_title, prot.lower())
                        await client.send_message(destination_channel, txt, link_preview=True)
                        sent_configs.add(c['config']); live_configs.append({'protocol':prot, 'config':c['config'], 'latency':lat or 999, 'status':status, 'channel':ch_title, 't_link': f"https://t.me/{channel[1:]}/{c['id']}"})
                        sent_count += 1; await asyncio.sleep(3)
            except Exception as e: print(f"⚠️ Error {channel}: {e}")

        # --- ساخت GitHub Pages ---
        try:
            print("\n📄 ساخت صفحه وب...")
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Config Hub</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --primary: #38bdf8; --text: #f1f5f9; --border: #334155; }}
        * {{ margin:0; padding:0; box-sizing:border-box; font-family: 'Vazirmatn', sans-serif; }}
        body {{ background: var(--bg); color: var(--text); padding: 15px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        header {{ text-align: center; padding: 30px 0; border-bottom: 1px solid var(--border); }}
        .tabs {{ display: flex; gap: 10px; margin: 25px 0; overflow-x: auto; }}
        .tab {{ background: var(--card); border: 1px solid var(--border); color: #94a3b8; padding: 10px 20px; border-radius: 12px; cursor: pointer; white-space: nowrap; }}
        .tab.active {{ background: var(--primary); color: var(--bg); font-weight: bold; }}
        .section {{ display: none; }}
        .section.active {{ display: block; animation: fadeIn 0.4s; }}
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
        .card {{ background: var(--card); border-radius: 16px; padding: 20px; margin-bottom: 15px; border: 1px solid var(--border); }}
        .code-box {{ background: #000; color: #22d3ee; padding: 12px; border-radius: 10px; font-family: monospace; font-size: 0.8rem; overflow-x: auto; margin: 10px 0; direction: ltr; }}
        .btn {{ display: inline-block; padding: 10px 20px; border-radius: 10px; background: var(--primary); color: var(--bg); text-decoration: none; font-weight: bold; margin-left: 5px; cursor: pointer; border: none; }}
        .guide-box {{ line-height: 2; font-size: 0.95rem; }}
        .guide-box h3 {{ color: var(--primary); margin: 15px 0; }}
        footer {{ text-align: center; padding: 40px; color: #64748b; font-size: 0.8rem; }}
    </style>
</head>
<body>
<div class="container">
    <header><h1>🔮 VPN DASHBOARD</h1><p>بروزرسانی شده در: {now_str}</p></header>
    <div class="tabs">
        <div class="tab active" onclick="show(event, 'configs')">🚀 کانفیگ‌ها ({len(live_configs)})</div>
        <div class="tab" onclick="show(event, 'proxies')">🔵 پروکسی‌ها ({len(all_proxies_data)})</div>
        <div class="tab" onclick="show(event, 'files')">📂 فایل‌ها ({len(all_files_data)})</div>
        <div class="tab" onclick="show(event, 'guide')">📖 راهنمای پنل</div>
    </div>
    <div id="configs" class="section active">
        {"".join([f'<div class="card"><p style="font-size:0.8rem;color:var(--primary)">📡 {c["channel"]} | {c["status"]}</p><div class="code-box" id="c{i}">{c["config"]}</div><button class="btn" onclick="copy(\'c{i}\')">کپی هوشمند</button><a href="{c["config"]}" class="btn" style="background:transparent;border:1px solid var(--primary);color:var(--primary)">اتصال مستقیم</a></div>' for i, c in enumerate(live_configs)])}
    </div>
    <div id="proxies" class="section">
        {"".join([f'<div class="card"><p style="color:var(--primary)">🛡️ پروکسی MTProto</p><div class="code-box">Server: {k}</div><a href="{v["link"]}" class="btn">اتصال سریع</a></div>' for k, v in all_proxies_data.items()])}
    </div>
    <div id="files" class="section">
        {"".join([f'<div class="card"><h3>📂 {name}</h3><p style="margin:10px 0;font-size:0.8rem;color:#94a3b8">منبع: {data["channel"]}</p><a href="{data["link"]}" class="btn">مشاهده در تلگرام</a></div>' for name, data in all_files_data.items()])}
    </div>
    <div id="guide" class="section">
        <div class="card guide-box">
            <h3>۱. اطلاعات کلی و پینگ</h3>
            <p>تمام کانفیگ‌ها قبل از نمایش تست پینگ می‌شوند. وضعیت با رنگ‌های سبز (عالی) و قرمز (ضعیف) مشخص شده است.</p>
            <h3>۲. کپی هوشمند و اتصال</h3>
            <p>با دکمه کپی، متن کانفیگ کپی شده و با دکمه اتصال مستقیم، برنامه وی‌پی‌ان شما خودکار باز می‌شود.</p>
            <h3>۳. دسترسی به منبع و فایل‌ها</h3>
            <p>برای هر مطلب، لینک مستقیم به پست اصلی تلگرام قرار داده شده تا از امنیت فایل‌ها مطمئن شوید.</p>
        </div>
    </div>
    <footer>طراحی شده برای کانال {destination_channel}<br>آپدیت خودکار هر ۸۰ دقیقه</footer>
</div>
<script>
    function show(e, id) {{
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.getElementById(id).classList.add('active');
        e.target.classList.add('active');
    }}
    function copy(id) {{
        var t = document.getElementById(id).innerText;
        navigator.clipboard.writeText(t).then(() => {{ alert("کپی شد! ✅"); }});
    }}
</script>
</body>
</html>"""
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
        except Exception as e: print(f"❌ HTML Error: {e}")
        print(f"✅ پایان ({sent_count} ارسال)")
    except Exception as e: print(f"❌ Critical Error: {e}")
    finally: await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
