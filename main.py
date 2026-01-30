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

# لیست کامل کانال‌ها
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

# IP های ایران (نمونه کوچک)
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
    """انتخاب 20 کانال بر اساس زمان"""
    current_hour = datetime.now(iran_tz).hour
    current_minute = datetime.now(iran_tz).minute
    total_minutes = current_hour * 60 + current_minute
    batch_index = (total_minutes // 40) % 2
    
    if batch_index == 0:
        selected = ALL_CHANNELS[:20]
        print(f"📦 Batch 1/2: کانال‌های 1-20")
    else:
        selected = ALL_CHANNELS[20:40]
        print(f"📦 Batch 2/2: کانال‌های 21-40")
    
    return selected

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
        
        initial_wait = random.randint(15, 25)
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
        all_proxies_data = {}
        
        for i, channel in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                if i > 0:
                    delay = random.uniform(4, 8)
                    await asyncio.sleep(delay)
                
                print(f"🔍 {channel}...")
                
                channel_proxies = []
                channel_configs = []
                
                async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True, limit=50):
                    if sent_count >= MAX_PER_RUN:
                        break
                    
                    ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                    
                    # فایل‌ها
                    if message.file:
                        file_name = message.file.name if message.file.name else ""
                        if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                            if file_name not in sent_files:
                                try:
                                    caption = f"📂 **{file_name}**"
                                    caption += get_file_usage_guide(file_name)
                                    caption += create_footer(ch_title, file_name.lower().split('.')[-1])
                                    
                                    await client.send_file(destination_channel, message.media, caption=caption)
                                    print(f"  ✅ فایل: {file_name}")
                                    sent_files.add(file_name)
                                    sent_count += 1
                                    await asyncio.sleep(random.uniform(1.5, 2.5))
                                except FloodWaitError as e:
                                    print(f"  ⚠️ Flood: {e.seconds}s")
                                    await asyncio.sleep(e.seconds + 5)
                                except Exception as e:
                                    print(f"  ❌ خطا: {e}")
                    
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
                                        final_link = p.replace("https://t.me/", "tg://")
                                        channel_proxies.append(final_link)
                                        all_proxies_data[unique_key] = final_link
                                        sent_proxies.add(unique_key)
                            except: 
                                pass
                    
                    # کانفیگ‌ها
                    if message.text:
                        raw_matches = re.findall(config_regex, message.text)
                        for conf in raw_matches:
                            clean_conf = conf.strip()
                            if clean_conf not in sent_configs:
                                channel_configs.append(clean_conf)
                                sent_configs.add(clean_conf)
                
                # چک پروکسی‌ها
                if channel_proxies and ENABLE_PING_CHECK:
                    print(f"  🔍 چک {len(channel_proxies)} پروکسی...")
                    tasks = [safe_check_proxy(p, MAX_PING_WAIT) for p in channel_proxies]
                    results = await asyncio.gather(*tasks)
                    
                    proxy_text = "🔵 **پروکسی‌های جدید:**\n\n"
                    for i, (proxy, (status, latency, is_intranet)) in enumerate(zip(channel_proxies, results), 1):
                        if is_intranet:
                            proxy_text += f"{i}. [اتصال]({proxy}) • {status} 🇮🇷\n"
                        elif status and latency:
                            proxy_text += f"{i}. [اتصال]({proxy}) • {status} ({latency}ms)\n"
                        elif status:
                            proxy_text += f"{i}. [اتصال]({proxy}) • {status}\n"
                        else:
                            proxy_text += f"{i}. [اتصال]({proxy})\n"
                    
                    proxy_text += get_proxy_usage_guide()
                    proxy_text += create_footer(ch_title, "proxy")
                    
                    try:
                        await client.send_message(destination_channel, proxy_text, link_preview=False)
                        print(f"  ✅ {len(channel_proxies)} پروکسی")
                        sent_count += 1
                        await asyncio.sleep(random.uniform(1.5, 2.5))
                    except FloodWaitError as e:
                        print(f"  ⚠️ Flood: {e.seconds}s")
                        await asyncio.sleep(e.seconds + 5)
                    except Exception as e:
                        print(f"  ❌ خطا: {e}")
                
                # چک کانفیگ‌ها
                if channel_configs and ENABLE_PING_CHECK:
                    print(f"  🔍 چک {len(channel_configs)} کانفیگ...")
                    tasks = [safe_check_config(c, MAX_PING_WAIT) for c in channel_configs]
                    results = await asyncio.gather(*tasks)
                    
                    for conf, (status, latency, is_intranet) in zip(channel_configs, results):
                        if sent_count >= MAX_PER_RUN:
                            break
                        
                        prot = conf.split("://")[0].upper()
                        if "NM-" in prot: 
                            prot = "NETMOD"
                        
                        qr_url = generate_qr_url(conf)
                        final_txt = f"🔮 **کانفیگ {prot}**\n\n`{conf}`\n"
                        
                        if is_intranet:
                            final_txt += f"\n📊 {status} 🇮🇷 (مخصوص نت ملی/نیم‌بها)\n"
                        elif status and latency:
                            final_txt += f"\n📊 {status} • {latency}ms\n"
                            live_configs.append({
                                'protocol': prot,
                                'config': conf,
                                'latency': latency,
                                'status': status,
                                'channel': ch_title
                            })
                        elif status:
                            final_txt += f"\n📊 {status}\n"
                        
                        final_txt += get_config_usage_guide(conf)
                        final_txt += f"\n[​]({qr_url})"
                        final_txt += create_footer(ch_title, "intranet" if is_intranet else prot.lower())
                        
                        try:
                            await client.send_message(destination_channel, final_txt, link_preview=True)
                            print(f"  ✅ {prot}")
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
            print("\n📄 ساخت GitHub Pages...")
            
            now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
            all_files = list(sent_files)
            all_proxies = list(sent_proxies)
            
            html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>VPN Config Hub</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:Tahoma,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;padding:20px;direction:rtl}}
.header{{text-align:center;color:#fff;margin-bottom:30px}}
.header h1{{font-size:2.5em;margin-bottom:10px}}
.container{{max-width:1400px;margin:0 auto}}
.tabs{{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;justify-content:center}}
.tab{{background:rgba(255,255,255,0.2);color:#fff;border:2px solid rgba(255,255,255,0.3);padding:12px 30px;border-radius:10px;cursor:pointer;transition:all 0.3s}}
.tab:hover{{background:rgba(255,255,255,0.3)}}
.tab.active{{background:#fff;color:#667eea}}
.content{{background:#fff;border-radius:15px;padding:30px;box-shadow:0 20px 60px rgba(0,0,0,0.3)}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px;margin-bottom:30px}}
.stat-card{{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:#fff;padding:25px;border-radius:12px;text-align:center}}
.stat-card h3{{font-size:2.5em;margin-bottom:8px}}
table{{width:100%;border-collapse:collapse;margin-top:20px}}
th,td{{padding:15px;text-align:right;border-bottom:1px solid #eee}}
th{{background:#f8f9fa;font-weight:600}}
tr:hover{{background:#f8f9fa}}
.protocol-badge{{display:inline-block;padding:5px 10px;border-radius:6px;font-size:0.85em;font-weight:600;color:#fff}}
.vmess{{background:#667eea}}
.vless{{background:#764ba2}}
.trojan{{background:#f093fb}}
code{{background:#f8f9fa;padding:3px 8px;border-radius:4px;font-size:0.9em;word-break:break-all}}
.copy-btn{{background:#667eea;color:#fff;border:none;padding:6px 12px;border-radius:6px;cursor:pointer}}
.empty-state{{text-align:center;padding:60px 20px;color:#999}}
.footer{{text-align:center;margin-top:40px;padding:30px;color:#fff}}
.channel-list{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:15px;margin-top:20px}}
.channel-item{{background:#f8f9fa;padding:15px;border-radius:10px;border-right:4px solid #667eea}}
.channel-item a{{color:#667eea;text-decoration:none;font-weight:500}}
</style>
</head>
<body>
<div class="header">
<h1>🔮 VPN Config Hub</h1>
<div>📅 {now_str}</div>
</div>
<div class="container">
<div class="tabs">
<button class="tab active" onclick="showTab('configs')">🔮 کانفیگ ({len(live_configs)})</button>
<button class="tab" onclick="showTab('proxies')">🔵 پروکسی ({len(all_proxies)})</button>
<button class="tab" onclick="showTab('files')">📂 فایل ({len(all_files)})</button>
<button class="tab" onclick="showTab('channels')">📡 کانال ({len(ALL_CHANNELS)})</button>
</div>
<div class="content">
<div id="configs" class="tab-content active">
<div class="stats">
<div class="stat-card"><h3>{len(live_configs)}</h3><p>کانفیگ آنلاین</p></div>
"""
            
            if live_configs:
                avg = int(sum(c['latency'] for c in live_configs) / len(live_configs))
                html += f"<div class='stat-card'><h3>{avg}ms</h3><p>میانگین پینگ</p></div>"
                html += "<div class='stat-card'><h3>" + str(len(set(c['protocol'] for c in live_configs))) + "</h3><p>نوع پروتکل</p></div>"
                html += "</div><table><thead><tr><th>ردیف</th><th>پروتکل</th><th>پینگ</th><th>منبع</th><th>کانفیگ</th></tr></thead><tbody>"
                
                for i, c in enumerate(sorted(live_configs, key=lambda x: x['latency']), 1):
                    html += f"<tr><td>{i}</td><td><span class='protocol-badge {c['protocol'].lower()}'>{c['protocol']}</span></td>"
                    html += f"<td>{c['latency']}ms</td><td>{c['channel']}</td>"
                    html += f"<td><code>{c['config'][:60]}...</code></td></tr>"
                
                html += "</tbody></table>"
            else:
                html += "<div class='stat-card'><h3>-</h3><p>میانگین</p></div>"
                html += "<div class='stat-card'><h3>-</h3><p>پروتکل</p></div></div>"
                html += "<div class='empty-state'><h3>هیچ کانفیگ زنده‌ای موجود نیست</h3></div>"
            
            html += "</div>"
            
            # پروکسی
            html += "<div id='proxies' class='tab-content'>"
            html += f"<div class='stats'><div class='stat-card'><h3>{len(all_proxies)}</h3><p>پروکسی</p></div></div>"
            
            if all_proxies:
                html += "<table><thead><tr><th>ردیف</th><th>سرور:پورت</th></tr></thead><tbody>"
                for i, p in enumerate(all_proxies, 1):
                    html += f"<tr><td>{i}</td><td><code>{p}</code></td></tr>"
                html += "</tbody></table>"
            else:
                html += "<div class='empty-state'><h3>پروکسی موجود نیست</h3></div>"
            
            html += "</div>"
            
            # فایل
            html += "<div id='files' class='tab-content'>"
            html += f"<div class='stats'><div class='stat-card'><h3>{len(all_files)}</h3><p>فایل</p></div></div>"
            
            if all_files:
                html += "<table><thead><tr><th>ردیف</th><th>نام فایل</th></tr></thead><tbody>"
                for i, f in enumerate(all_files, 1):
                    html += f"<tr><td>{i}</td><td><code>{f}</code></td></tr>"
                html += "</tbody></table>"
            else:
                html += "<div class='empty-state'><h3>فایل موجود نیست</h3></div>"
            
            html += "</div>"
            
            # کانال‌ها
            html += "<div id='channels' class='tab-content'>"
            html += f"<div class='stats'><div class='stat-card'><h3>{len(ALL_CHANNELS)}</h3><p>کانال منبع</p></div></div>"
            html += "<div class='channel-list'>"
            
            for ch in ALL_CHANNELS:
                ch_clean = ch[1:] if ch.startswith('@') else ch
                html += f"<div class='channel-item'><a href='https://t.me/{ch_clean}' target='_blank'>📢 {ch}</a></div>"
            
            html += "</div></div>"
            
            html += f"""
</div></div>
<div class="footer">
<p>🔗 <a href="https://t.me/{destination_channel[1:]}">{destination_channel}</a></p>
<p>آپدیت هر 40 دقیقه • {now_str}</p>
</div>
<script>
function showTab(n){{
document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
document.getElementById(n).classList.add('active');
event.target.classList.add('active');
}}
</script>
</body>
</html>
"""
            
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(html)
            
            print("✅ فایل index.html ساخته شد")
            
        except Exception as e:
            print(f"❌ خطا HTML: {e}")

        print(f"\n✅ پایان ({sent_count} ارسال)")

    except Exception as e:
        print(f"❌ خطای حیاتی: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
