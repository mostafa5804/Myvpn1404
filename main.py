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
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from telethon.errors.rpcerrorlist import FloodWaitError

# -----------------------------------------------------------------------------
# 1. تنظیمات و متغیرهای اصلی
# -----------------------------------------------------------------------------
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
MAX_PING_WAIT = 4
DATA_FILE = 'data.json'  # نام فایل دیتابیس
KEEP_HISTORY_HOURS = 24  # مدت زمان نگهداری اطلاعات (ساعت)

# لیست کانال‌ها
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
# 2. مدیریت دیتابیس و حافظه (Data Management)
# -----------------------------------------------------------------------------
def load_data():
    """لود کردن اطلاعات از فایل جیسون و حذف قدیمی‌ها"""
    if not os.path.exists(DATA_FILE):
        return {'configs': [], 'proxies': [], 'files': []}
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # پاکسازی داده‌های قدیمی (بیشتر از 24 ساعت)
        now_ts = time.time()
        limit_ts = now_ts - (KEEP_HISTORY_HOURS * 3600)
        
        new_data = {
            'configs': [c for c in data.get('configs', []) if c.get('ts', 0) > limit_ts],
            'proxies': [p for p in data.get('proxies', []) if p.get('ts', 0) > limit_ts],
            'files': [f for f in data.get('files', []) if f.get('ts', 0) > limit_ts]
        }
        return new_data
    except Exception as e:
        print(f"⚠️ خطای لود دیتابیس: {e}")
        return {'configs': [], 'proxies': [], 'files': []}

def save_data(data):
    """ذخیره اطلاعات در فایل جیسون"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتابیس: {e}")

def merge_data(history, new_items, key_field):
    """ادغام داده‌های جدید با قدیمی (بدون تکراری)"""
    # تبدیل لیست قدیمی به دیکشنری برای جستجوی سریع
    existing = {item[key_field]: item for item in history}
    
    # افزودن/آپدیت آیتم‌های جدید
    for item in new_items:
        # اگر آیتم جدید است یا آیتم قبلی قدیمی‌تر است، آپدیت کن
        if item[key_field] not in existing:
             existing[item[key_field]] = item
    
    # تبدیل دوباره به لیست و مرتب‌سازی بر اساس زمان (جدیدترین اول)
    merged_list = list(existing.values())
    merged_list.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return merged_list

# -----------------------------------------------------------------------------
# 3. توابع کمکی (Helper Functions)
# -----------------------------------------------------------------------------

def is_iran_ip(ip):
    try:
        for prefix in IRAN_IP_PREFIXES:
            if ip.startswith(prefix): return True
        return False
    except: return False

def get_channel_batch():
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

def clean_title(title):
    if not title: return "Channel"
    return re.sub(r'[\[\]\(\)\*`_]', '', str(title)).strip()

def get_file_hashtags(file_name):
    ext = file_name.lower().split('.')[-1]
    tags = {
        'npv4': '#NapsternetV #npv4', 'npv2': '#NapsternetV #npv2', 'npvt': '#NapsternetV #npvt',
        'ehi': '#HTTPInjector #ehi', 'txt': '#v2rayNG #Hiddify',
        'conf': '#Shadowrocket #conf', 'json': '#v2rayNG #json', 'dark': '#DarkProxy'
    }
    return tags.get(ext, '#VPN')

def get_config_hashtags(config_link):
    protocol = config_link.split("://")[0].lower()
    return f"#{protocol} #v2rayNG"

def get_proxy_usage_guide():
    return "💡 برای اتصال روی لینک کلیک کنید"

def create_minimal_footer(channel_title, message_link):
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    safe_title = clean_title(channel_title)
    return f"\n━━━━━━━━━━━━━━━━\n🗓 {date_str} • 🕐 {time_str}\n📡 منبع: [{safe_title}]({message_link})\n🔗 {destination_channel}"

# -----------------------------------------------------------------------------
# 4. تابع اصلی برنامه
# -----------------------------------------------------------------------------
async def main():
    try:
        await client.start()
        print("✅ ربات متصل شد")
        
        # لود کردن اطلاعات قبلی (حافظه)
        history_data = load_data()
        print(f"📂 حافظه لود شد: {len(history_data['configs'])} کانفیگ، {len(history_data['proxies'])} پروکسی")

        initial_wait = random.randint(10, 20)
        await asyncio.sleep(initial_wait)
        
        source_channels, batch_name = get_channel_batch()
        print(f"--- شروع بررسی دسته {batch_name} ---")
        
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1.5)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        # فقط برای جلوگیری از ارسال تکراری در همین اجرا (تلگرام)
        sent_files = set(); sent_proxies = set(); sent_configs = set()
        
        # مخازن موقت جدید برای این اجرا (New Items)
        new_live_configs = []
        new_proxies_data = []
        new_files_data = []

        try:
            async for msg in client.iter_messages(destination_channel, limit=100):
                if msg.text:
                    matches = re.findall(config_regex, msg.text)
                    for c in matches: sent_configs.add(c.strip())
                    proxy_matches = re.findall(r"server=([\w\.-]+)&port=(\d+)", msg.text)
                    for server, port in proxy_matches: sent_proxies.add(f"{server}:{port}")
        except: pass

        sent_count = 0; MAX_PER_RUN = 40
        
        for i, channel_username in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN: break
            try:
                if i > 0: await asyncio.sleep(random.uniform(5, 8))
                print(f"\n🔍 کانال {i+1}/20: {channel_username}")
                
                try:
                    entity = await client.get_entity(channel_username)
                    ch_title = entity.title if hasattr(entity, 'title') else channel_username
                except: ch_title = channel_username
                
                temp_files = []; temp_proxies = []; temp_configs = []
                
                async for message in client.iter_messages(entity, offset_date=time_threshold, reverse=True, limit=40):
                    orig_link = f"https://t.me/{channel_username[1:]}/{message.id}"
                    
                    if message.file:
                        fname = message.file.name if message.file.name else ""
                        if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                            if fname not in sent_files:
                                temp_files.append({'name': fname, 'media': message.media, 'link': orig_link})
                    
                    if message.text or message.entities:
                        p_links = re.findall(r"(?:tg|https)://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+", message.text or "")
                        for p in list(set(p_links)):
                            host, port = extract_proxy_info(p)
                            if host:
                                key = f"{host}:{port}"
                                if key not in sent_proxies:
                                    temp_proxies.append({'link': p.replace("https://t.me/", "tg://"), 'key': key, 'orig_link': orig_link})

                    if message.text:
                        confs = re.findall(config_regex, message.text)
                        for c in confs:
                            clean = c.strip()
                            if clean not in sent_configs:
                                temp_configs.append({'config': clean, 'orig_link': orig_link})

                # 1. فایل‌ها
                for item in temp_files:
                    if sent_count >= MAX_PER_RUN: break
                    try:
                        caption = f"📂 **{item['name']}**\n\n"
                        caption += f"{get_file_hashtags(item['name'])}\n"
                        caption += create_minimal_footer(ch_title, item['link'])
                        
                        sent_msg = await client.send_file(destination_channel, item['media'], caption=caption)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent_msg.id}"
                        
                        # افزودن به لیست جدید برای ذخیره
                        new_files_data.append({
                            'name': item['name'], 'channel': ch_title, 'link': my_link, 
                            'ext': item['name'].split('.')[-1], 'ts': time.time()
                        })
                        
                        sent_files.add(item['name']); sent_count += 1
                        await asyncio.sleep(3)
                    except Exception as e: print(f"❌ فایل: {e}")

                # 2. پروکسی‌ها
                valid_proxies = []
                if temp_proxies:
                    for item in temp_proxies:
                        if sent_count >= MAX_PER_RUN: break
                        status, lat, is_in = await safe_check_proxy(item['link'])
                        if status:
                            flag = "🇮🇷" if is_in else "🌍"
                            ping_str = f"{lat}ms" if lat else ""
                            valid_proxies.append({
                                'link': item['link'], 'ping': ping_str, 'status': status, 'flag': flag, 
                                'key': item['key'], 'orig_link': item['orig_link']
                            })
                            sent_proxies.add(item['key'])
                
                if valid_proxies:
                    try:
                        msg_body = "🔵 **پروکسی‌های جدید**\n\n"
                        for idx, p in enumerate(valid_proxies, 1):
                            msg_body += f"{idx}. [اتصال]({p['link']}) • {p['flag']} {p['status']} {p['ping']}\n"
                        msg_body += get_proxy_usage_guide()
                        msg_body += create_minimal_footer(ch_title, valid_proxies[0]['orig_link'])
                        
                        sent_msg = await client.send_message(destination_channel, msg_body, link_preview=False)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent_msg.id}"
                        
                        # افزودن به لیست جدید
                        for p in valid_proxies:
                            new_proxies_data.append({
                                'key': p['key'], 'link': p['link'], 'channel': ch_title, 
                                't_link': my_link, 'ts': time.time()
                            })
                            
                        sent_count += 1; await asyncio.sleep(3)
                    except Exception as e: print(f"❌ پروکسی: {e}")

                # 3. کانفیگ‌ها
                for item in temp_configs:
                    if sent_count >= MAX_PER_RUN: break
                    try:
                        status, lat, is_in = await safe_check_config(item['config'])
                        if status:
                            prot = item['config'].split("://")[0].upper()
                            ping_txt = f"{lat}ms" if lat else ""
                            
                            txt = f"🔮 **{prot}**\n\n"
                            txt += f"```{item['config']}```\n"
                            txt += f"📊 وضعیت: {status} • {ping_txt}\n"
                            txt += f"{get_config_hashtags(item['config'])}\n"
                            txt += create_minimal_footer(ch_title, item['orig_link'])
                            
                            sent_msg = await client.send_message(destination_channel, txt, link_preview=False)
                            my_link = f"https://t.me/{destination_channel[1:]}/{sent_msg.id}"
                            
                            # افزودن به لیست جدید
                            new_live_configs.append({
                                'protocol': prot, 'config': item['config'], 'latency': lat or 999, 
                                'channel': ch_title, 't_link': my_link, 'ts': time.time()
                            })
                            
                            sent_configs.add(item['config']); sent_count += 1
                            await asyncio.sleep(3)
                    except Exception as e: print(f"❌ کانفیگ: {e}")

            except Exception as e: print(f"⚠️ خطا در کانال: {e}"); continue

        # --- پایان حلقه ---
        
        # 4. ادغام داده‌ها و ذخیره در دیتابیس
        print("\n💾 در حال آپدیت حافظه 24 ساعته...")
        final_configs = merge_data(history_data['configs'], new_live_configs, 'config')
        final_proxies = merge_data(history_data['proxies'], new_proxies_data, 'key')
        final_files = merge_data(history_data['files'], new_files_data, 'name')
        
        save_data({
            'configs': final_configs,
            'proxies': final_proxies,
            'files': final_files
        })
        
        print(f"📊 آمار نهایی برای سایت: {len(final_configs)} کانفیگ، {len(final_proxies)} پروکسی، {len(final_files)} فایل")

        # 5. ساخت صفحه وب (با استفاده از داده‌های ۲۴ ساعته)
        try:
            print("📄 ساخت صفحه وب...")
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Hub</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --primary: #38bdf8; --text: #f1f5f9; --sub: #94a3b8; --border: #334155; }}
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        body {{ background:var(--bg); color:var(--text); padding-bottom:80px; }}
        .header {{ text-align:center; padding:20px; border-bottom:1px solid var(--border); position:sticky; top:0; background:rgba(15,23,42,0.95); z-index:50; backdrop-filter:blur(10); }}
        .container {{ max-width:600px; margin:0 auto; padding:15px; }}
        .card {{ background:var(--card); border-radius:16px; padding:16px; margin-bottom:16px; border:1px solid var(--border); }}
        .tag {{ background:#334155; padding:4px 10px; border-radius:8px; font-size:0.75rem; }}
        .code {{ background:#0b1120; padding:12px; border-radius:10px; color:#22d3ee; overflow-x:auto; font-family:monospace; margin:10px 0; }}
        .btns {{ display:flex; gap:10px; }}
        .btn {{ flex:1; padding:10px; border-radius:10px; border:none; cursor:pointer; font-weight:bold; text-align:center; text-decoration:none; }}
        .copy {{ background:var(--primary); color:#0f172a; }}
        .link {{ border:1px solid var(--primary); color:var(--primary); }}
        .nav {{ position:fixed; bottom:0; left:0; right:0; background:rgba(30,41,59,0.95); display:flex; padding:10px; border-top:1px solid var(--border); }}
        .nav-item {{ flex:1; text-align:center; color:var(--sub); cursor:pointer; }}
        .nav-item.active {{ color:var(--primary); font-weight:bold; }}
        .tab {{ display:none; }} .tab.active {{ display:block; }}
    </style>
</head>
<body>
    <div class="header"><h1>VPN Hub</h1><p>{now_str}</p></div>
    <div class="container">
        <div id="t1" class="tab active">
            {"".join([f'<div class="card"><div><span class="tag">{c["protocol"]}</span> <span style="float:left">⚡ {c["latency"]}ms</span></div><div style="font-size:0.8rem;color:#94a3b8;margin:10px 0">📡 {c["channel"]}</div><div class="code" id="c{i}">{c["config"]}</div><div class="btns"><button class="btn copy" onclick="cp(\'c{i}\')">کپی</button><a href="{c["t_link"]}" class="btn link">اتصال</a></div></div>' for i, c in enumerate(final_configs)])}
            {f'<div style="text-align:center;padding:20px;color:#64748b">لیست خالی است</div>' if not final_configs else ''}
        </div>
        <div id="t2" class="tab">
            {"".join([f'<div class="card"><div><span class="tag">Proxy</span></div><div style="font-size:0.8rem;color:#94a3b8;margin:5px 0">📡 {v["channel"]}</div><div class="code">{v["key"].split(":")[0]}</div><div class="btns"><a href="{v["link"]}" class="btn copy">اتصال</a></div></div>' for i, v in enumerate(final_proxies)])}
        </div>
        <div id="t3" class="tab">
            {"".join([f'<div class="card"><div><span class="tag">FILE</span> <span class="tag">{v["ext"]}</span></div><div style="margin:10px 0">{v["name"]}</div><div style="font-size:0.8rem;color:#94a3b8;margin:5px 0">📡 {v["channel"]}</div><a href="{v["link"]}" class="btn link" style="display:block">دانلود</a></div>' for i, v in enumerate(final_files)])}
        </div>
    </div>
    <div class="nav">
        <div class="nav-item active" onclick="sw('t1',this)">🚀 کانفیگ</div>
        <div class="nav-item" onclick="sw('t2',this)">🛡️ پروکسی</div>
        <div class="nav-item" onclick="sw('t3',this)">📂 فایل</div>
    </div>
    <script>
        function sw(id,el){{ document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active')); document.getElementById(id).classList.add('active'); document.querySelectorAll('.nav-item').forEach(e=>e.classList.remove('active')); el.classList.add('active'); window.scrollTo(0,0); }}
        function cp(id){{ navigator.clipboard.writeText(document.getElementById(id).innerText).then(()=>alert('کپی شد!')); }}
    </script>
</body>
</html>"""
            with open('index.html', 'w', encoding='utf-8') as f: f.write(html)
            print("✅ صفحه وب ساخته شد")
        except Exception as e: print(f"❌ خطا HTML: {e}")

        print(f"\n✅ پایان عملیات ({sent_count} ارسال شد)")
    except Exception as e: print(f"❌ خطای حیاتی: {e}")
    finally: await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
