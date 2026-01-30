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

# =============================================================================
# 1. تنظیمات و پیکربندی (Configuration)
# =============================================================================

# دریافت متغیرهای محیطی از گیت‌هاب
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

# تنظیمات پینگ و تست
ENABLE_PING_CHECK = True  # آیا کانفیگ‌ها تست شوند؟
PING_TIMEOUT = 2          # زمان انتظار برای پاسخ پینگ (ثانیه)
MAX_PING_WAIT = 4         # حداکثر زمان کلی برای تست

# تنظیمات دیتابیس و حافظه
DATA_FILE = 'data.json'   # نام فایل ذخیره اطلاعات
KEEP_HISTORY_HOURS = 24   # مدت زمان نگهداری اطلاعات (ساعت)

# کانال مقصد (کانال خودت)
destination_channel = '@myvpn1404'

# لیست کامل کانال‌های منبع (40 عدد)
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

# پسوندهای مجاز فایل
allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}

# منطقه زمانی ایران
iran_tz = pytz.timezone('Asia/Tehran')

# رنج آی‌پی‌های ایران (برای تشخیص اینترانت)
IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

# راه‌اندازی کلاینت تلگرام
client = TelegramClient(StringSession(session_string), api_id, api_hash)


# =============================================================================
# 2. توابع مدیریت دیتابیس (Database Management)
# =============================================================================

def load_data():
    """
    اطلاعات قبلی را از فایل data.json می‌خواند و قدیمی‌ها را حذف می‌کند.
    """
    if not os.path.exists(DATA_FILE):
        return {'configs': [], 'proxies': [], 'files': []}
    
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # محاسبه زمان انقضا (24 ساعت پیش)
        now_ts = time.time()
        limit_ts = now_ts - (KEEP_HISTORY_HOURS * 3600)
        
        # فیلتر کردن داده‌های قدیمی
        new_data = {
            'configs': [c for c in data.get('configs', []) if c.get('ts', 0) > limit_ts],
            'proxies': [p for p in data.get('proxies', []) if p.get('ts', 0) > limit_ts],
            'files': [f for f in data.get('files', []) if f.get('ts', 0) > limit_ts]
        }
        return new_data
    except Exception as e:
        print(f"⚠️ خطا در لود دیتابیس: {e}")
        return {'configs': [], 'proxies': [], 'files': []}

def save_data(data):
    """
    اطلاعات جدید را در فایل data.json ذخیره می‌کند.
    """
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ خطا در ذخیره دیتابیس: {e}")

def merge_data(history, new_items, key_field):
    """
    داده‌های جدید را با تاریخچه ادغام می‌کند (حذف تکراری‌ها).
    """
    existing = {item[key_field]: item for item in history}
    
    for item in new_items:
        # اگر آیتم جدید است یا وجود ندارد، اضافه/آپدیت کن
        if item[key_field] not in existing:
             existing[item[key_field]] = item
    
    # تبدیل به لیست و مرتب‌سازی زمانی (جدیدترین اول)
    merged_list = list(existing.values())
    merged_list.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return merged_list


# =============================================================================
# 3. توابع کمکی و پردازش (Helper Functions)
# =============================================================================

def is_iran_ip(ip):
    """بررسی می‌کند آیا IP متعلق به ایران است؟"""
    try:
        for prefix in IRAN_IP_PREFIXES:
            if ip.startswith(prefix):
                return True
        return False
    except:
        return False

def get_channel_batch():
    """
    انتخاب کانال‌ها بر اساس چرخه 80 دقیقه‌ای:
    - دقیقه 0 تا 40: دسته اول
    - دقیقه 40 تا 80: دسته دوم
    """
    now = datetime.now(iran_tz)
    batch_index = ((now.hour * 60 + now.minute) // 40) % 2
    
    if batch_index == 0:
        return ALL_CHANNELS[:20], "اول (1-20)"
    else:
        return ALL_CHANNELS[20:40], "دوم (21-40)"

def clean_title(title):
    """پاکسازی نام کانال از کاراکترهای مزاحم برای لینک‌دهی"""
    if not title: return "Channel"
    return re.sub(r'[\[\]\(\)\*`_]', '', str(title)).strip()

def get_file_hashtags(file_name):
    """تولید هشتگ مناسب برای فایل‌ها"""
    ext = file_name.lower().split('.')[-1]
    tags = {
        'npv4': '#NapsternetV #npv4',
        'npv2': '#NapsternetV #npv2',
        'npvt': '#NapsternetV #npvt',
        'ehi': '#HTTPInjector #ehi',
        'txt': '#v2rayNG #Hiddify',
        'conf': '#Shadowrocket #conf',
        'json': '#v2rayNG #json',
        'dark': '#DarkProxy'
    }
    return tags.get(ext, '#VPN')

def get_config_hashtags(config_link):
    """تولید هشتگ مناسب برای کانفیگ‌ها"""
    protocol = config_link.split("://")[0].lower()
    return f"#{protocol} #v2rayNG"

def create_minimal_footer(channel_title, message_link):
    """ساخت فوتر پیام تلگرام"""
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    safe_title = clean_title(channel_title)
    
    footer = f"\n━━━━━━━━━━━━━━━━\n"
    footer += f"🗓 {date_str} • 🕐 {time_str}\n"
    footer += f"📡 منبع: [{safe_title}]({message_link})\n"
    footer += f"🔗 {destination_channel}"
    return footer

def get_proxy_usage_guide():
    return "💡 برای اتصال روی لینک کلیک کنید"


# =============================================================================
# 4. توابع تست و استخراج (Testing & Extraction)
# =============================================================================

async def measure_tcp_latency(host, port, timeout=2):
    """اندازه‌گیری پینگ TCP"""
    import time
    try:
        start = time.time()
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        latency = int((time.time() - start) * 1000)
        writer.close()
        await writer.wait_closed()
        return latency
    except:
        return None

async def check_and_format_status(host, port, timeout=2):
    """بررسی وضعیت سرور"""
    if not host or not port:
        return None, None, False
    
    try:
        latency = await measure_tcp_latency(host, port, timeout)
        is_intranet = False
        
        try:
            ip_address = socket.gethostbyname(host)
            if is_iran_ip(ip_address) and latency is None:
                is_intranet = True
        except:
            pass
        
        if latency is None:
            if is_intranet:
                return "🔵 اینترانت", None, True
            return "🔴 آفلاین", None, False
        
        if latency < 100: return "🟢 عالی", latency, False
        elif latency < 200: return "🟡 خوب", latency, False
        elif latency < 400: return "🟠 متوسط", latency, False
        else: return "🔴 ضعیف", latency, False
    except:
        return None, None, False

def extract_server_info(config):
    """استخراج آدرس و پورت از کانفیگ"""
    try:
        protocol = config.split("://")[0].lower()
        if protocol == "vmess":
            encoded = config.split("://")[1]
            decoded = json.loads(base64.b64decode(encoded))
            return decoded.get("add"), int(decoded.get("port", 443))
        elif protocol in ["vless", "trojan", "ss", "shadowsocks", "hysteria", "hysteria2", "hy2", "tuic"]:
            match = re.search(r"@([\w\.-]+):(\d+)", config)
            if match:
                return match.group(1), int(match.group(2))
        return None, None
    except:
        return None, None

def extract_proxy_info(proxy_link):
    """استخراج آدرس و پورت از لینک پروکسی"""
    try:
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match:
            return match.group(1), int(match.group(2))
        return None, None
    except:
        return None, None

async def safe_check_config(config, max_wait=4):
    """تست امن کانفیگ"""
    try:
        host, port = extract_server_info(config)
        if host and port:
            return await asyncio.wait_for(check_and_format_status(host, port, timeout=PING_TIMEOUT), timeout=max_wait)
        return None, None, False
    except:
        return "⏱️ Timeout", None, False

async def safe_check_proxy(proxy_link, max_wait=4):
    """تست امن پروکسی"""
    try:
        host, port = extract_proxy_info(proxy_link)
        if host and port:
            return await asyncio.wait_for(check_and_format_status(host, port, timeout=PING_TIMEOUT), timeout=max_wait)
        return None, None, False
    except:
        return "⏱️ Timeout", None, False


# =============================================================================
# 5. بدنه اصلی برنامه (Main Loop)
# =============================================================================

async def main():
    try:
        # اتصال به تلگرام
        await client.start()
        print("✅ ربات متصل شد")
        
        # لود کردن حافظه 24 ساعته
        history_data = load_data()
        print(f"📂 حافظه لود شد: {len(history_data['configs'])} کانفیگ، {len(history_data['proxies'])} پروکسی")

        # تاخیر اولیه تصادفی (برای امنیت)
        initial_wait = random.randint(10, 20)
        print(f"⏳ صبر اولیه: {initial_wait} ثانیه...")
        await asyncio.sleep(initial_wait)
        
        # دریافت دسته کانال‌های این نوبت
        source_channels, batch_name = get_channel_batch()
        print(f"--- شروع بررسی دسته {batch_name} ---")
        
        # بازه زمانی جستجو (1.5 ساعت اخیر)
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1.5)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        # لیست‌های جلوگیری از تکرار در ارسال تلگرام
        sent_files = set()
        sent_proxies = set()
        sent_configs = set()
        
        # لود کردن آخرین پیام‌های کانال خودت (برای جلوگیری از تکرار)
        try:
            print("بارگذاری تاریخچه کانال مقصد...")
            async for msg in client.iter_messages(destination_channel, limit=100):
                if msg.text:
                    matches = re.findall(config_regex, msg.text)
                    for c in matches: sent_configs.add(c.strip())
                    proxy_matches = re.findall(r"server=([\w\.-]+)&port=(\d+)", msg.text)
                    for server, port in proxy_matches: sent_proxies.add(f"{server}:{port}")
        except Exception as e:
            print(f"⚠️ هشدار تاریخچه: {e}")

        # متغیرهای آماری و ذخیره‌سازی جدید
        sent_count = 0
        MAX_PER_RUN = 40
        new_live_configs = []
        new_proxies_data = []
        new_files_data = []

        # ---------------------------------------------------------------------
        # شروع حلقه پردازش کانال‌ها
        # ---------------------------------------------------------------------
        for i, channel_username in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                # تاخیر بین کانال‌ها
                if i > 0:
                    await asyncio.sleep(random.uniform(5, 8))
                
                print(f"\n🔍 کانال {i+1}/20: {channel_username}")
                
                # تلاش برای دریافت اطلاعات کانال (با هندلینگ خطا)
                try:
                    entity = await client.get_entity(channel_username)
                    ch_title = entity.title if hasattr(entity, 'title') else channel_username
                except Exception as e:
                    print(f"⚠️ خطا در دسترسی به کانال {channel_username}: {e}")
                    continue  # پرش به کانال بعدی

                # لیست‌های موقت برای این کانال
                temp_files = []
                temp_proxies = []
                temp_configs = []
                
                # پیمایش پیام‌های اخیر کانال
                async for message in client.iter_messages(entity, offset_date=time_threshold, reverse=True, limit=40):
                    orig_link = f"https://t.me/{channel_username[1:]}/{message.id}"
                    
                    # الف) استخراج فایل
                    if message.file:
                        fname = message.file.name if message.file.name else ""
                        if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                            if fname not in sent_files:
                                temp_files.append({'name': fname, 'media': message.media, 'link': orig_link})
                    
                    # ب) استخراج پروکسی
                    if message.text or message.entities:
                        p_links = re.findall(r"(?:tg|https)://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+", message.text or "")
                        for p in list(set(p_links)):
                            host, port = extract_proxy_info(p)
                            if host:
                                key = f"{host}:{port}"
                                if key not in sent_proxies:
                                    temp_proxies.append({'link': p.replace("https://t.me/", "tg://"), 'key': key, 'orig_link': orig_link})

                    # ج) استخراج کانفیگ
                    if message.text:
                        confs = re.findall(config_regex, message.text)
                        for c in confs:
                            clean = c.strip()
                            if clean not in sent_configs:
                                temp_configs.append({'config': clean, 'orig_link': orig_link})

                # -------------------------------------------------------------
                # ارسال موارد یافت شده به کانال خودت
                # -------------------------------------------------------------

                # 1. ارسال فایل‌ها
                for item in temp_files:
                    if sent_count >= MAX_PER_RUN: break
                    try:
                        caption = f"📂 **{item['name']}**\n\n"
                        caption += f"{get_file_hashtags(item['name'])}\n"
                        caption += create_minimal_footer(ch_title, item['link'])
                        
                        sent_msg = await client.send_file(destination_channel, item['media'], caption=caption)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent_msg.id}"
                        
                        new_files_data.append({
                            'name': item['name'], 'channel': ch_title, 'link': my_link,
                            'ext': item['name'].split('.')[-1], 'ts': time.time()
                        })
                        sent_files.add(item['name'])
                        sent_count += 1
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"❌ خطا در ارسال فایل: {e}")

                # 2. ارسال پروکسی‌ها (گروهی)
                valid_proxies = []
                if temp_proxies:
                    print(f"  🔍 تست {len(temp_proxies)} پروکسی...")
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
                        
                        for p in valid_proxies:
                            new_proxies_data.append({
                                'key': p['key'], 'link': p['link'], 'channel': ch_title,
                                't_link': my_link, 'ts': time.time()
                            })
                            
                        sent_count += 1
                        print(f"  ✅ لیست پروکسی ارسال شد ({len(valid_proxies)} عدد)")
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"❌ خطا در ارسال پروکسی: {e}")

                # 3. ارسال کانفیگ‌ها
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
                            
                            new_live_configs.append({
                                'protocol': prot, 'config': item['config'], 'latency': lat or 999,
                                'channel': ch_title, 't_link': my_link, 'ts': time.time()
                            })
                            
                            sent_configs.add(item['config'])
                            sent_count += 1
                            print(f"  ✅ کانفیگ ارسال شد: {prot}")
                            await asyncio.sleep(3)
                    except Exception as e:
                        print(f"❌ خطا در ارسال کانفیگ: {e}")

            except Exception as e:
                print(f"⚠️ خطای کلی در کانال {channel_username}: {e}")
                continue

        # ---------------------------------------------------------------------
        # پایان حلقه - ذخیره‌سازی داده‌ها
        # ---------------------------------------------------------------------
        
        print("\n💾 در حال ادغام و ذخیره دیتابیس 24 ساعته...")
        final_configs = merge_data(history_data['configs'], new_live_configs, 'config')
        final_proxies = merge_data(history_data['proxies'], new_proxies_data, 'key')
        final_files = merge_data(history_data['files'], new_files_data, 'name')
        
        save_data({
            'configs': final_configs,
            'proxies': final_proxies,
            'files': final_files
        })
        
        print(f"📊 آمار نهایی برای وب‌سایت: {len(final_configs)} کانفیگ، {len(final_proxies)} پروکسی، {len(final_files)} فایل")


        # ---------------------------------------------------------------------
        # تولید فایل HTML داشبورد (Full Professional)
        # ---------------------------------------------------------------------
        try:
            print("📄 در حال ساخت صفحه وب...")
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            
            # نکته: در اینجا از {{ و }} استفاده شده تا با f-string تداخل نکند
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub | {destination_channel}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg-body: #0f172a;
            --bg-card: #1e293b;
            --primary: #38bdf8;
            --secondary: #64748b;
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #334155;
            --success: #10b981;
            --accent: #6366f1;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', sans-serif; -webkit-tap-highlight-color: transparent; }}
        
        body {{ background-color: var(--bg-body); color: var(--text-main); padding-bottom: 90px; overflow-x: hidden; }}

        /* --- Header --- */
        header {{
            background: rgba(30, 41, 59, 0.95);
            backdrop-filter: blur(12px);
            padding: 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            border-bottom: 1px solid var(--border);
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }}

        header h1 {{ font-size: 1.5rem; background: linear-gradient(45deg, var(--primary), var(--accent)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 5px; }}
        header p {{ color: var(--text-muted); font-size: 0.85rem; }}

        /* --- Search Bar --- */
        .search-box {{
            max-width: 600px;
            margin: 15px auto 0;
            position: relative;
        }}
        .search-box input {{
            width: 100%;
            background: var(--bg-body);
            border: 1px solid var(--border);
            padding: 12px 45px 12px 15px;
            border-radius: 12px;
            color: var(--text-main);
            font-size: 0.95rem;
            transition: all 0.3s;
        }}
        .search-box input:focus {{ outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.2); }}
        .search-box i {{ position: absolute; right: 15px; top: 50%; transform: translateY(-50%); color: var(--text-muted); }}

        /* --- Container --- */
        .container {{ max-width: 600px; margin: 20px auto; padding: 0 15px; }}

        /* --- Cards --- */
        .card {{
            background: var(--bg-card);
            border-radius: 16px;
            padding: 16px;
            margin-bottom: 16px;
            border: 1px solid var(--border);
            position: relative;
            overflow: hidden;
            transition: transform 0.2s;
            animation: fadeIn 0.4s ease-out;
        }}
        
        @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}

        .card::before {{
            content: ''; position: absolute; top: 0; left: 0; width: 4px; height: 100%;
            background: var(--primary);
        }}

        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        
        .badge {{
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .badge-proto {{ background: rgba(56, 189, 248, 0.1); color: var(--primary); }}
        .badge-ping {{ display: flex; align-items: center; gap: 5px; }}

        .meta-info {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 12px; }}
        .meta-info i {{ color: var(--secondary); }}

        .code-block {{
            background: #0b1120;
            padding: 12px;
            border-radius: 10px;
            border: 1px dashed var(--border);
            font-family: 'Courier New', monospace;
            font-size: 0.8rem;
            color: #a5b4fc;
            overflow: hidden;
            white-space: nowrap;
            text-overflow: ellipsis;
            margin-bottom: 12px;
            direction: ltr;
            text-align: left;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .code-block:hover {{ background: #111827; }}

        /* --- Buttons --- */
        .actions {{ display: grid; grid-template-columns: 1fr 1fr auto; gap: 10px; }}
        
        .btn {{
            display: flex; align-items: center; justify-content: center; gap: 8px;
            padding: 10px; border-radius: 10px; border: none; cursor: pointer;
            font-weight: 600; font-size: 0.9rem; text-decoration: none; transition: 0.2s;
        }}
        
        .btn-copy {{ background: var(--primary); color: #0f172a; }}
        .btn-copy:active {{ transform: scale(0.96); }}
        
        .btn-link {{ background: transparent; border: 1px solid var(--border); color: var(--text-main); }}
        .btn-link:hover {{ border-color: var(--text-muted); background: rgba(255,255,255,0.05); }}

        .btn-qr {{ width: 42px; background: rgba(255,255,255,0.1); color: var(--text-main); }}

        /* --- Bottom Nav --- */
        .bottom-nav {{
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(30, 41, 59, 0.95);
            backdrop-filter: blur(15px);
            border-top: 1px solid var(--border);
            display: flex; justify-content: space-around;
            padding: 10px 0 25px; /* Extra padding for iOS */
            z-index: 999;
        }}
        
        .nav-item {{
            display: flex; flex-direction: column; align-items: center; gap: 4px;
            color: var(--text-muted); font-size: 0.75rem; cursor: pointer;
            flex: 1; padding: 5px; transition: 0.3s;
        }}
        
        .nav-item i {{ font-size: 1.2rem; margin-bottom: 2px; transition: 0.3s; }}
        .nav-item.active {{ color: var(--primary); }}
        .nav-item.active i {{ transform: translateY(-3px); text-shadow: 0 0 10px var(--primary); }}

        /* --- Sections --- */
        .tab-section {{ display: none; }}
        .tab-section.active {{ display: block; }}

        /* --- Empty State --- */
        .empty {{ text-align: center; padding: 40px 20px; color: var(--text-muted); }}
        .empty i {{ font-size: 3rem; margin-bottom: 15px; opacity: 0.3; }}

        /* --- Modal QR --- */
        .modal {{
            display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.85); z-index: 2000; align-items: center; justify-content: center;
            backdrop-filter: blur(5px);
        }}
        .modal-content {{
            background: var(--bg-card); padding: 25px; border-radius: 20px;
            text-align: center; position: relative; width: 90%; max-width: 350px;
            border: 1px solid var(--border); animation: zoomIn 0.3s;
        }}
        @keyframes zoomIn {{ from {{ transform: scale(0.8); opacity: 0; }} to {{ transform: scale(1); opacity: 1; }} }}
        
        .modal img {{ width: 100%; border-radius: 10px; margin-bottom: 15px; border: 4px solid #fff; }}
        .close-modal {{
            position: absolute; top: 10px; right: 15px; font-size: 1.5rem;
            color: var(--text-muted); cursor: pointer;
        }}

    </style>
</head>
<body>

    <header>
        <h1>VPN Config Hub</h1>
        <p>آخرین بروزرسانی: <span dir="ltr">{now_str}</span></p>
        
        <div class="search-box">
            <i class="fas fa-search"></i>
            <input type="text" id="searchInput" placeholder="جستجو (مثلاً: vless, آلمان, همراه...)" onkeyup="filterContent()">
        </div>
    </header>

    <div class="container">
        <div id="tab-configs" class="tab-section active">
            {"".join([f'''
            <div class="card search-item" data-filter="{c['protocol']} {c['channel']}">
                <div class="card-header">
                    <span class="badge badge-proto">{c['protocol']}</span>
                    <span class="badge badge-ping" style="color:{'#10b981' if c['latency']<200 else '#f59e0b'}">
                        <i class="fas fa-bolt"></i> {c['latency']}ms
                    </span>
                </div>
                <div class="meta-info">
                    <i class="fas fa-broadcast-tower"></i> {c['channel']}
                    <span style="margin:0 5px">•</span>
                    <i class="far fa-clock"></i> 24h
                </div>
                <div class="code-block" onclick="copyText('conf-{i}', this)">{c['config']}</div>
                <div class="actions">
                    <button class="btn btn-copy" onclick="copyText('conf-{i}', this)">
                        <i class="far fa-copy"></i> کپی
                    </button>
                    <a href="{c['t_link']}" class="btn btn-link">
                        <i class="fab fa-telegram-plane"></i> اتصال
                    </a>
                    <button class="btn btn-link btn-qr" onclick="showQR('{c['config']}')">
                        <i class="fas fa-qrcode"></i>
                    </button>
                </div>
                <div id="conf-{i}" style="display:none">{c['config']}</div>
            </div>
            ''' for i, c in enumerate(final_configs)])}
            
            {f'<div class="empty"><i class="fas fa-box-open"></i><p>هنوز کانفیگی ثبت نشده است</p></div>' if not final_configs else ''}
        </div>

        <div id="tab-proxies" class="tab-section">
            {"".join([f'''
            <div class="card search-item" data-filter="proxy mtproto {v['channel']}">
                <div class="card-header">
                    <span class="badge badge-proto">MTProto</span>
                    <span class="badge badge-ping" style="color:#f59e0b"><i class="fas fa-shield-alt"></i> Proxy</span>
                </div>
                <div class="meta-info"><i class="fas fa-broadcast-tower"></i> {v['channel']}</div>
                <div class="code-block" style="color:var(--text-muted)">{v['key'].split(':')[0]}</div>
                <div class="actions" style="grid-template-columns: 1fr;">
                    <a href="{v['link']}" class="btn btn-copy">
                        <i class="fas fa-power-off"></i> اتصال سریع
                    </a>
                </div>
            </div>
            ''' for i, v in enumerate(final_proxies)])}
            {f'<div class="empty"><i class="fas fa-shield-virus"></i><p>پروکسی موجود نیست</p></div>' if not final_proxies else ''}
        </div>

        <div id="tab-files" class="tab-section">
            {"".join([f'''
            <div class="card search-item" data-filter="{v['ext']} {v['name']} {v['channel']}">
                <div class="card-header">
                    <span class="badge badge-proto">{v['ext'].upper()}</span>
                    <span class="badge badge-ping"><i class="fas fa-file-download"></i> File</span>
                </div>
                <div style="font-weight:bold; margin-bottom:5px; direction:ltr; text-align:right">{v['name']}</div>
                <div class="meta-info"><i class="fas fa-broadcast-tower"></i> {v['channel']}</div>
                <div class="actions" style="grid-template-columns: 1fr;">
                    <a href="{v['link']}" class="btn btn-link" style="border-color:var(--primary); color:var(--primary)">
                        <i class="fas fa-download"></i> دانلود مستقیم
                    </a>
                </div>
            </div>
            ''' for i, v in enumerate(final_files)])}
            {f'<div class="empty"><i class="fas fa-folder-open"></i><p>فایلی موجود نیست</p></div>' if not final_files else ''}
        </div>
    </div>

    <nav class="bottom-nav">
        <div class="nav-item active" onclick="switchTab('tab-configs', this)">
            <i class="fas fa-rocket"></i>
            <span>کانفیگ</span>
        </div>
        <div class="nav-item" onclick="switchTab('tab-proxies', this)">
            <i class="fas fa-shield-alt"></i>
            <span>پروکسی</span>
        </div>
        <div class="nav-item" onclick="switchTab('tab-files', this)">
            <i class="fas fa-folder"></i>
            <span>فایل</span>
        </div>
    </nav>

    <div id="qrModal" class="modal" onclick="closeQR(event)">
        <div class="modal-content">
            <span class="close-modal" onclick="document.getElementById('qrModal').style.display='none'">&times;</span>
            <h3 style="margin-bottom:15px; color:var(--text-main)">اسکن برای اتصال</h3>
            <img id="qrImage" src="" alt="QR Code">
            <p style="font-size:0.8rem; color:var(--text-muted)">با دوربین گوشی اسکن کنید</p>
        </div>
    </div>

    <script>
        // Tab Switching
        function switchTab(id, el) {{
            document.querySelectorAll('.tab-section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            
            document.getElementById(id).classList.add('active');
            el.classList.add('active');
            window.scrollTo(0, 0);
        }}

        // Copy Function
        function copyText(elementId, btn) {{
            const text = document.getElementById(elementId).innerText;
            navigator.clipboard.writeText(text).then(() => {{
                const originalHTML = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> کپی شد';
                btn.style.background = '#10b981';
                btn.style.color = '#fff';
                
                setTimeout(() => {{
                    btn.innerHTML = originalHTML;
                    btn.style.background = ''; // reset to css
                    btn.style.color = '';
                }}, 2000);
            }});
        }}

        // Search Filter
        function filterContent() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            document.querySelectorAll('.search-item').forEach(card => {{
                const text = card.getAttribute('data-filter').toLowerCase();
                card.style.display = text.includes(query) ? 'block' : 'none';
            }});
        }}

        // QR Code Logic
        function showQR(config) {{
            const url = `https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=${{encodeURIComponent(config)}}`;
            document.getElementById('qrImage').src = url;
            document.getElementById('qrModal').style.display = 'flex';
        }}

        function closeQR(e) {{
            if (e.target.id === 'qrModal') {{
                document.getElementById('qrModal').style.display = 'none';
            }}
        }}
    </script>
</body>
</html>"""
            
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            print("✅ صفحه وب ساخته شد (Professional Full)")
            
        except Exception as e:
            print(f"❌ خطا HTML: {e}")

        print(f"\n✅ پایان عملیات ({sent_count} ارسال شد)")

    except Exception as e:
        print(f"❌ خطای حیاتی: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
