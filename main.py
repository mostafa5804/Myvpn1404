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
    """بررسی IP ایرانی"""
    try:
        for prefix in IRAN_IP_PREFIXES:
            if ip.startswith(prefix):
                return True
        return False
    except:
        return False


def get_channel_batch():
    now = datetime.now(iran_tz)
    batch_index = ((now.hour * 60 + now.minute) // 40) % 2
    if batch_index == 0:
        return ALL_CHANNELS[:20], "اول (1-20)"
    return ALL_CHANNELS[20:40], "دوم (21-40)"


async def measure_tcp_latency(host, port, timeout=2):
    """اندازه‌گیری پینگ"""
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
    """چک وضعیت"""
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
        
        if latency < 100:
            return "🟢 عالی", latency, False
        elif latency < 200:
            return "🟡 خوب", latency, False
        elif latency < 400:
            return "🟠 متوسط", latency, False
        else:
            return "🔴 ضعیف", latency, False
    except:
        return None, None, False


def extract_server_info(config):
    """استخراج IP و Port"""
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
    """استخراج اطلاعات پروکسی"""
    try:
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match:
            return match.group(1), int(match.group(2))
        return None, None
    except:
        return None, None


async def safe_check_config(config, max_wait=4):
    """چک امن کانفیگ"""
    try:
        host, port = extract_server_info(config)
        if host and port:
            status, latency, is_intranet = await asyncio.wait_for(
                check_and_format_status(host, port, timeout=PING_TIMEOUT),
                timeout=max_wait
            )
            return status, latency, is_intranet
        return None, None, False
    except asyncio.TimeoutError:
        return "⏱️ Timeout", None, False
    except:
        return None, None, False


async def safe_check_proxy(proxy_link, max_wait=4):
    """چک امن پروکسی"""
    try:
        host, port = extract_proxy_info(proxy_link)
        if host and port:
            status, latency, is_intranet = await asyncio.wait_for(
                check_and_format_status(host, port, timeout=PING_TIMEOUT),
                timeout=max_wait
            )
            return status, latency, is_intranet
        return None, None, False
    except asyncio.TimeoutError:
        return "⏱️ Timeout", None, False
    except:
        return None, None, False


def generate_qr_url(config):
    """تولید QR Code URL"""
    from urllib.parse import quote
    encoded = quote(config)
    return f"https://quickchart.io/qr?text={encoded}&size=300"


def get_file_usage_guide(file_name):
    """راهنمای فایل"""
    ext = file_name.lower().split('.')[-1]
    apps = {
        'npv4': 'NapsternetV • v2rayNG',
        'npv2': 'NapsternetV',
        'npvt': 'NapsternetV',
        'dark': 'DarkProxy',
        'ehi': 'HTTP Injector • HTTP Custom',
        'txt': 'v2rayNG • Hiddify • NekoBox',
        'conf': 'Shadowrocket • Quantumult',
        'json': 'v2rayNG • NekoBox'
    }
    app_name = apps.get(ext, 'v2rayNG')
    return f"\n📱 {app_name}\n"


def get_config_usage_guide(config_link):
    """راهنمای کانفیگ"""
    protocol = config_link.split("://")[0].lower()
    apps = {
        'vmess': 'v2rayNG • Hiddify • V2Box',
        'vless': 'v2rayNG • Hiddify • NekoBox',
        'trojan': 'v2rayNG • Hiddify • Trojan-Go',
        'ss': 'Shadowsocks • v2rayNG • Outline',
        'shadowsocks': 'Shadowsocks • v2rayNG',
        'hysteria': 'v2rayNG • NekoBox',
        'hysteria2': 'v2rayNG • Hiddify',
        'hy2': 'v2rayNG • Hiddify',
        'tuic': 'NekoBox • SingBox',
        'nm': 'NetMod'
    }
    app_name = apps.get(protocol, 'v2rayNG • Hiddify')
    return f"\n📱 {app_name}\n"


def get_proxy_usage_guide():
    """راهنمای پروکسی"""
    return "\n💡 روی لینک کلیک کنید، تلگرام خودکار متصل می‌شود\n"


def create_footer(channel_name, extra_info=""):
    """فوتر پیام"""
    now_iran = datetime.now(iran_tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = j_date.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    hashtag_map = {
        "vmess": "#vmess #v2ray",
        "vless": "#vless #v2ray",
        "trojan": "#trojan #v2ray",
        "ss": "#shadowsocks",
        "proxy": "#MTProto",
        "npv4": "#netmod",
        "npvt": "#netmod",
        "dark": "#darkproxy",
        "ehi": "#httpinjector",
        "nm": "#netmod",
        "intranet": "#اینترانت #نیم_بها"
    }
    
    hashtags = hashtag_map.get(extra_info.lower(), "#VPN")
    
    footer = f"\n{hashtags}\n"
    footer += f"🗓 {date_str} • 🕐 {time_str}\n"
    footer += f"📡 {channel_name}\n"
    footer += f"🔗 {destination_channel}"
    
    return footer


async def main():
    """تابع اصلی"""
    
    try:
        await client.start()
        print("✅ متصل شد")
        
        initial_wait = random.randint(10, 20)
        print(f"⏳ صبر {initial_wait} ثانیه...")
        await asyncio.sleep(initial_wait)
        
        source_channels = get_channel_batch()
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        print("--- شروع ---")
        
        sent_files = set()
        sent_proxies = set()
        sent_configs = set()
        
        # بارگذاری تاریخچه
        try:
            print("بارگذاری تاریخچه...")
            async for msg in client.iter_messages(destination_channel, limit=150):
                if msg.file and msg.file.name: 
                    sent_files.add(msg.file.name)
                if msg.text:
                    matches = re.findall(config_regex, msg.text)
                    for c in matches: 
                        sent_configs.add(c.strip())
                    proxy_matches = re.findall(r"server=([\w\.-]+)&port=(\d+)", msg.text)
                    for server, port in proxy_matches:
                        sent_proxies.add(f"{server}:{port}")
            print(f"✅ تاریخچه بارگذاری شد")
        except FloodWaitError as e:
            print(f"⚠️ Flood Wait: {e.seconds}s")
            return
        except Exception as e:
            print(f"⚠️ خطا: {e}")

        sent_count = 0
        MAX_PER_RUN = 40
        live_configs = []
        all_files_data = {}
        all_proxies_data = {}
        
        # حلقه اصلی: هر کانال به ترتیب
        for i, channel in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                if i > 0:
                    delay = random.uniform(5, 10)
                    print(f"⏸️ صبر {delay:.1f} ثانیه...")
                    await asyncio.sleep(delay)
                
                print(f"\n{'='*50}")
                print(f"🔍 کانال {i+1}/20: {channel}")
                print(f"{'='*50}")
                
                ch_title = None
                
                # جمع‌آوری محتوا از کانال
                channel_items = {
                    'files': [],
                    'proxies': [],
                    'configs': []
                }
                
                async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True, limit=50):
                    if not ch_title and hasattr(message.chat, 'title'):
                        ch_title = message.chat.title
                    
                    # فایل‌ها
                    if message.file:
                        file_name = message.file.name if message.file.name else ""
                        if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                            if file_name not in sent_files:
                                channel_items['files'].append({
                                    'name': file_name,
                                    'media': message.media,
                                    'message_id': message.id
                                })
                    
                    # پروکسی‌ها
                    if message.entities or message.text:
                        extracted_proxies = []
                        if message.entities:
                            for ent in message.entities:
                                if isinstance(ent, MessageEntityTextUrl) and "proxy?server=" in ent.url:
                                    extracted_proxies.append(ent.url)
                        if message.text:
                            extracted_proxies.extend(
                                re.findall(
                                    r"(tg://proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+)", 
                                    message.text
                                )
                            )
                        for p in list(set(extracted_proxies)):
                            try:
                                match = re.search(r"server=([\w\.-]+)&port=(\d+)", p)
                                if match:
                                    unique_key = f"{match.group(1)}:{match.group(2)}"
                                    if unique_key not in sent_proxies:
                                        channel_items['proxies'].append({
                                            'link': p.replace("https://t.me/", "tg://"),
                                            'key': unique_key,
                                            'message_id': message.id
                                        })
                            except: 
                                pass
                    
                    # کانفیگ‌ها
                    if message.text:
                        raw_matches = re.findall(config_regex, message.text)
                        for conf in raw_matches:
                            clean_conf = conf.strip()
                            if clean_conf not in sent_configs:
                                channel_items['configs'].append({
                                    'config': clean_conf,
                                    'message_id': message.id
                                })
                
                if not ch_title:
                    ch_title = channel
                
                print(f"📊 یافت شد: {len(channel_items['files'])} فایل، {len(channel_items['proxies'])} پروکسی، {len(channel_items['configs'])} کانفیگ")
                
                # ارسال به ترتیب: فایل → پروکسی → کانفیگ
                
                # 1. فایل‌ها (بدون تست)
                for item in channel_items['files']:
                    if sent_count >= MAX_PER_RUN:
                        break
                    try:
                        caption = f"📂 **{item['name']}**"
                        caption += get_file_usage_guide(item['name'])
                        caption += create_footer(ch_title, item['name'].lower().split('.')[-1])
                        
                        await client.send_file(destination_channel, item['media'], caption=caption)
                        print(f"  ✅ فایل: {item['name']}")
                        sent_files.add(item['name'])
                        all_files_data[item['name']] = {
                            'channel': ch_title,
                            'link': f"https://t.me/{channel[1:]}/{item['message_id']}"
                        }
                        sent_count += 1
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                    except FloodWaitError as e:
                        print(f"  ⚠️ Flood: {e.seconds}s")
                        await asyncio.sleep(e.seconds + 5)
                    except Exception as e:
                        print(f"  ❌ خطا: {e}")
                
                # 2. پروکسی‌ها (با تست)
                if channel_items['proxies'] and ENABLE_PING_CHECK:
                    print(f"  🔍 تست {len(channel_items['proxies'])} پروکسی...")
                    tasks = [safe_check_proxy(item['link'], MAX_PING_WAIT) for item in channel_items['proxies']]
                    results = await asyncio.gather(*tasks)
                    
                    proxy_text = "🔵 **پروکسی‌های جدید:**\n\n"
                    for idx, (item, (status, latency, is_intranet)) in enumerate(zip(channel_items['proxies'], results), 1):
                        if is_intranet:
                            proxy_text += f"{idx}. [اتصال]({item['link']}) • {status} 🇮🇷\n"
                        elif status and latency:
                            proxy_text += f"{idx}. [اتصال]({item['link']}) • {status} ({latency}ms)\n"
                        elif status:
                            proxy_text += f"{idx}. [اتصال]({item['link']}) • {status}\n"
                        else:
                            proxy_text += f"{idx}. [اتصال]({item['link']})\n"
                        
                        sent_proxies.add(item['key'])
                        all_proxies_data[item['key']] = {
                            'link': item['link'],
                            'channel': ch_title,
                            'telegram_link': f"https://t.me/{channel[1:]}/{item['message_id']}"
                        }
                    
                    proxy_text += get_proxy_usage_guide()
                    proxy_text += create_footer(ch_title, "proxy")
                    
                    try:
                        await client.send_message(destination_channel, proxy_text, link_preview=False)
                        print(f"  ✅ {len(channel_items['proxies'])} پروکسی")
                        sent_count += 1
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                    except FloodWaitError as e:
                        print(f"  ⚠️ Flood: {e.seconds}s")
                        await asyncio.sleep(e.seconds + 5)
                    except Exception as e:
                        print(f"  ❌ خطا: {e}")
                
                # 3. کانفیگ‌ها (با تست)
                if channel_items['configs'] and ENABLE_PING_CHECK:
                    print(f"  🔍 تست {len(channel_items['configs'])} کانفیگ...")
                    tasks = [safe_check_config(item['config'], MAX_PING_WAIT) for item in channel_items['configs']]
                    results = await asyncio.gather(*tasks)
                    
                    for item, (status, latency, is_intranet) in zip(channel_items['configs'], results):
                        if sent_count >= MAX_PER_RUN:
                            break
                        
                        prot = item['config'].split("://")[0].upper()
                        if "NM-" in prot: 
                            prot = "NETMOD"
                        
                        qr_url = generate_qr_url(item['config'])
                        final_txt = f"🔮 **کانفیگ {prot}**\n\n`{item['config']}`\n"
                        
                        if is_intranet:
                            final_txt += f"\n📊 {status} 🇮🇷 (نت ملی/نیم‌بها)\n"
                        elif status and latency:
                            final_txt += f"\n📊 {status} • {latency}ms\n"
                            live_configs.append({
                                'protocol': prot,
                                'config': item['config'],
                                'latency': latency,
                                'status': status,
                                'channel': ch_title,
                                'telegram_link': f"https://t.me/{channel[1:]}/{item['message_id']}"
                            })
                        elif status:
                            final_txt += f"\n📊 {status}\n"
                        
                        final_txt += get_config_usage_guide(item['config'])
                        final_txt += f"\n[​]({qr_url})"
                        final_txt += create_footer(ch_title, "intranet" if is_intranet else prot.lower())
                        
                        try:
                            await client.send_message(destination_channel, final_txt, link_preview=True)
                            print(f"  ✅ {prot} ({latency}ms)" if latency else f"  ✅ {prot}")
                            sent_configs.add(item['config'])
                            sent_count += 1
                            await asyncio.sleep(random.uniform(1.5, 2.5))
                        except FloodWaitError as e:
                            print(f"  ⚠️ Flood: {e.seconds}s")
                            await asyncio.sleep(e.seconds + 5)
                        except Exception as e:
                            print(f"  ❌ خطا: {e}")

            except FloodWaitError as e:
                print(f"❌ Flood {channel}: {e.seconds}s")
                continue
            except Exception as e:
                print(f"❌ خطا {channel}: {e}")
                continue

        # ساخت GitHub Pages
        try:
            print("\n📄 ساخت صفحه وب...")
            
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VPN Config Hub - {destination_channel}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Tahoma,Arial,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}}
.header{{text-align:center;color:#fff;margin-bottom:30px}}
.header h1{{font-size:2.5em;margin-bottom:10px;text-shadow:2px 2px 4px rgba(0,0,0,0.3)}}
.header .subtitle{{font-size:1.1em;opacity:0.9;margin-bottom:5px}}
.update{{font-size:0.9em;opacity:0.8}}
.container{{max-width:1400px;margin:0 auto}}
.info-box{{background:rgba(255,255,255,0.95);border-radius:15px;padding:25px;margin-bottom:20px;box-shadow:0 10px 30px rgba(0,0,0,0.2)}}
.info-box h3{{color:#667eea;margin-bottom:15px;font-size:1.3em}}
.info-box p{{line-height:1.8;color:#333;margin-bottom:10px}}
.info-box ul{{margin-right:25px;margin-top:10px}}
.info-box li{{margin-bottom:8px;line-height:1.6}}
.tabs{{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}}
.tab{{background:rgba(255,255,255,0.2);color:#fff;border:2px solid rgba(255,255,255,0.3);padding:12px 30px;border-radius:10px;cursor:pointer;transition:all 0.3s;font-weight:500}}
.tab:hover{{background:rgba(255,255,255,0.3);transform:translateY(-2px)}}
.tab.active{{background:#fff;color:#667eea;border-color:#fff}}
.content{{background:#fff;border-radius:15px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:30px}}
.stat-card{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:25px;border-radius:12px;text-align:center;transition:transform 0.3s}}
.stat-card:hover{{transform:translateY(-5px)}}
.stat-card h3{{font-size:2.5em;margin-bottom:8px}}
.stat-card p{{font-size:0.95em}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{padding:15px;text-align:right;border-bottom:1px solid #eee}}
th{{background:#f8f9fa;font-weight:600;color:#333;position:sticky;top:0}}
tr:hover{{background:#f8f9fa}}
.protocol-badge{{display:inline-block;padding:5px 10px;border-radius:6px;font-size:0.85em;font-weight:600;color:#fff;margin-left:5px}}
.vmess{{background:#667eea}}
.vless{{background:#764ba2}}
.trojan{{background:#f093fb}}
.ss{{background:#4facfe}}
code{{background:#f8f9fa;padding:3px 8px;border-radius:4px;font-size:0.9em;word-break:break-all;font-family:monospace}}
.copy-btn{{background:#667eea;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:0.85em;transition:all 0.3s;margin-left:5px}}
.copy-btn:hover{{background:#764ba2;transform:scale(1.05)}}
.link-btn{{background:#28a745;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:0.85em;text-decoration:none;display:inline-block}}
.link-btn:hover{{background:#218838}}
.empty-state{{text-align:center;padding:60px 20px;color:#999}}
.empty-state h3{{font-size:1.5em;margin-bottom:10px;color:#666}}
.footer{{text-align:center;margin-top:40px;padding:30px;color:#fff}}
.footer a{{color:#fff;text-decoration:none;font-weight:500;border-bottom:2px solid rgba(255,255,255,0.5)}}
.footer a:hover{{border-bottom-color:#fff}}
.channel-list{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;margin-top:20px}}
.channel-item{{background:#f8f9fa;padding:15px;border-radius:10px;border-right:4px solid #667eea;transition:all 0.3s}}
.channel-item:hover{{background:#e9ecef;transform:translateX(-5px)}}
.channel-item a{{color:#667eea;text-decoration:none;font-weight:500}}
@media (max-width:768px){{
.header h1{{font-size:1.8em}}
.stats{{grid-template-columns:1fr}}
table{{font-size:0.85em}}
th,td{{padding:10px}}
}}
</style>
</head>
<body>
<div class="header">
<h1>🔮 VPN Config Hub</h1>
<div class="subtitle">مرکز جامع کانفیگ‌های رایگان و تست‌شده</div>
<div class="update">📅 آخرین بروزرسانی: {now_str} | 🔄 هر کانال هر 80 دقیقه بررسی می‌شود</div>
</div>

<div class="container">

<div class="info-box">
<h3>ℹ️ درباره این سرویس</h3>
<p><strong>🎯 پینگ و تست خودکار:</strong> تمام کانفیگ‌ها و پروکسی‌ها قبل از نمایش توسط سرورهای ما تست می‌شوند. وضعیت سلامت با رنگ‌های 🟢 سبز (عالی)، 🟡 زرد (خوب) و 🔴 قرمز (ضعیف) مشخص شده است.</p>
<p><strong>📋 کپی هوشمند:</strong> با کلیک روی دکمه "کپی"، کانفیگ مستقیماً در کلیپ‌بورد شما ذخیره می‌شود. نیازی به انتخاب دستی متن نیست!</p>
<p><strong>🔗 لینک به منبع:</strong> با کلیک روی "مشاهده در تلگرام"، مستقیماً به پست اصلی در کانال منبع هدایت می‌شوید.</p>
<p><strong>⏰ بروزرسانی منظم:</strong> هر کانال هر 80 دقیقه یکبار بررسی می‌شود و محتوای جدید به صورت خودکار اضافه می‌گردد.</p>
<p><strong>📱 طراحی ریسپانسیو:</strong> این صفحه روی تمام دستگاه‌ها (موبایل، تبلت، دسکتاپ) به خوبی کار می‌کند.</p>
</div>

<div class="tabs">
<button class="tab active" onclick="showTab('configs')">🔮 کانفیگ ({len(live_configs)})</button>
<button class="tab" onclick="showTab('proxies')">🔵 پروکسی ({len(all_proxies_data)})</button>
<button class="tab" onclick="showTab('files')">📂 فایل ({len(all_files_data)})</button>
<button class="tab" onclick="showTab('channels')">📡 کانال ({len(ALL_CHANNELS)})</button>
</div>

<div class="content">
<div id="configs" class="tab-content active">
<div class="stats">
<div class="stat-card"><h3>{len(live_configs)}</h3><p>کانفیگ آنلاین</p></div>
"""
            
            if live_configs:
                avg = int(sum(c['latency'] for c in live_configs) / len(live_configs))
                fast = len([c for c in live_configs if c['latency'] < 100])
                html += f"""
<div class="stat-card"><h3>{avg}ms</h3><p>میانگین پینگ</p></div>
<div class="stat-card"><h3>{len(set(c['protocol'] for c in live_configs))}</h3><p>نوع پروتکل</p></div>
<div class="stat-card"><h3>{fast}</h3><p>سرعت عالی</p></div>
</div>
<table>
<thead><tr><th>ردیف</th><th>پروتکل</th><th>وضعیت</th><th>پینگ</th><th>منبع</th><th>کانفیگ</th><th>عملیات</th></tr></thead>
<tbody>
"""
                
                for i, c in enumerate(sorted(live_configs, key=lambda x: x['latency']), 1):
                    if c['latency'] < 100:
                        badge = '<span style="color:#28a745;font-weight:bold">🟢 عالی</span>'
                    elif c['latency'] < 200:
                        badge = '<span style="color:#ffc107;font-weight:bold">🟡 خوب</span>'
                    else:
                        badge = '<span style="color:#dc3545;font-weight:bold">🟠 متوسط</span>'
                    
                    config_id = f"cfg{i}"
                    safe_config = c['config'].replace("'", "\\'").replace('"', '\\"')
                    
                    html += f"""
<tr>
<td>{i}</td>
<td><span class="protocol-badge {c['protocol'].lower()}">{c['protocol']}</span></td>
<td>{badge}</td>
<td><strong>{c['latency']}ms</strong></td>
<td>{c['channel']}</td>
<td><code id="{config_id}">{c['config'][:50]}...</code></td>
<td>
<button class="copy-btn" onclick='copyText("{safe_config}")'>📋 کپی</button>
<a href="{c['telegram_link']}" target="_blank" class="link-btn">📱 منبع</a>
</td>
</tr>
"""
                
                html += "</tbody></table>"
            else:
                html += """
<div class="stat-card"><h3>-</h3><p>میانگین</p></div>
<div class="stat-card"><h3>-</h3><p>پروتکل</p></div>
<div class="stat-card"><h3>-</h3><p>سرعت</p></div>
</div>
<div class="empty-state"><h3>هیچ کانفیگ زنده‌ای موجود نیست</h3><p>لطفاً بعداً بررسی کنید</p></div>
"""
            
            html += "</div>"
            
            # پروکسی
            html += f"""
<div id="proxies" class="tab-content">
<div class="stats">
<div class="stat-card"><h3>{len(all_proxies_data)}</h3><p>پروکسی فعال</p></div>
<div class="stat-card"><h3>MTProto</h3><p>نوع پروتکل</p></div>
<div class="stat-card"><h3>رایگان</h3><p>100%</p></div>
</div>
"""
            
            if all_proxies_data:
                html += """
<div style="background:#e7f3ff;padding:20px;border-radius:10px;margin-bottom:20px;border-right:4px solid #667eea">
<h3 style="color:#667eea;margin-bottom:10px">💡 نحوه استفاده:</h3>
<ol style="margin-right:20px;line-height:1.8">
<li>روی دکمه "اتصال" کلیک کنید</li>
<li>تلگرام خودکار باز می‌شود</li>
<li>روی "اتصال" در تلگرام کلیک کنید</li>
<li>✅ متصل شدید!</li>
</ol>
</div>
<table>
<thead><tr><th>ردیف</th><th>سرور:پورت</th><th>منبع</th><th>عملیات</th></tr></thead>
<tbody>
"""
                
                for i, (key, data) in enumerate(all_proxies_data.items(), 1):
                    html += f"""
<tr>
<td>{i}</td>
<td><code>{key}</code></td>
<td>{data['channel']}</td>
<td>
<a href="{data['link']}" target="_blank"><button class="copy-btn">🔗 اتصال</button></a>
<a href="{data['telegram_link']}" target="_blank" class="link-btn">📱 منبع</a>
</td>
</tr>
"""
                
                html += "</tbody></table>"
            else:
                html += '<div class="empty-state"><h3>پروکسی موجود نیست</h3></div>'
            
            html += "</div>"
            
            # فایل
            html += f"""
<div id="files" class="tab-content">
<div class="stats">
<div class="stat-card"><h3>{len(all_files_data)}</h3><p>فایل موجود</p></div>
<div class="stat-card"><h3>{len(set([f.split('.')[-1] for f in all_files_data.keys()]))}</h3><p>نوع فایل</p></div>
<div class="stat-card"><h3>رایگان</h3><p>100%</p></div>
</div>
"""
            
            if all_files_data:
                html += """
<table>
<thead><tr><th>ردیف</th><th>نام فایل</th><th>نوع</th><th>منبع</th><th>عملیات</th></tr></thead>
<tbody>
"""
                
                for i, (fname, data) in enumerate(all_files_data.items(), 1):
                    ext = fname.split('.')[-1].upper()
                    html += f"""
<tr>
<td>{i}</td>
<td><code>{fname}</code></td>
<td><strong>{ext}</strong></td>
<td>{data['channel']}</td>
<td><a href="{data['link']}" target="_blank" class="link-btn">📥 دانلود</a></td>
</tr>
"""
                
                html += "</tbody></table>"
            else:
                html += '<div class="empty-state"><h3>فایل موجود نیست</h3></div>'
            
            html += "</div>"
            
            # کانال‌ها
            html += f"""
<div id="channels" class="tab-content">
<div class="stats">
<div class="stat-card"><h3>{len(ALL_CHANNELS)}</h3><p>کانال منبع</p></div>
<div class="stat-card"><h3>80 دقیقه</h3><p>فاصله بررسی</p></div>
<div class="stat-card"><h3>خودکار</h3><p>بروزرسانی</p></div>
</div>
<h3 style="margin-bottom:15px;color:#667eea">📡 لیست کامل کانال‌های منبع:</h3>
<div class="channel-list">
"""
            
            for ch in ALL_CHANNELS:
                ch_clean = ch[1:] if ch.startswith('@') else ch
                html += f'<div class="channel-item"><a href="https://t.me/{ch_clean}" target="_blank">📢 {ch}</a></div>'
            
            html += f"""
</div>
</div>
</div>
</div>

<div class="footer">
<p style="font-size:1.2em;margin-bottom:15px">🔗 کانال اصلی: <a href="https://t.me/{destination_channel[1:]}">{destination_channel}</a></p>
<p>ساخته شده با ❤️ • بروزرسانی خودکار هر 40 دقیقه • رایگان برای همیشه</p>
<p style="margin-top:10px;font-size:0.9em">آخرین بروزرسانی: {now_str}</p>
</div>

<script>
function showTab(n){{
document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
document.getElementById(n).classList.add('active');
event.target.classList.add('active');
}}
function copyText(txt){{
navigator.clipboard.writeText(txt).then(()=>{{
const btn=event.target;
const old=btn.innerText;
btn.innerText='✅ کپی شد';
btn.style.background='#28a745';
setTimeout(()=>{{btn.innerText=old;btn.style.background='#667eea'}},2000);
}});
}}
setTimeout(()=>location.reload(),40*60*1000);
</script>
</body>
</html>
"""
            
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            print("✅ صفحه وب ساخته شد")
            print(f"   📊 {len(live_configs)} کانفیگ، {len(all_proxies_data)} پروکسی، {len(all_files_data)} فایل")
            
        except Exception as e:
            print(f"❌ خطا HTML: {e}")
            import traceback
            traceback.print_exc()

        print(f"\n✅ پایان ({sent_count} ارسال شد)")

    except Exception as e:
        print(f"❌ خطای حیاتی: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
