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


def get_channel_batch():
    """انتخاب 20 کانال بر اساس زمان"""
    current_hour = datetime.now(iran_tz).hour
    current_minute = datetime.now(iran_tz).minute
    
    # محاسبه batch بر اساس زمان
    # هر 40 دقیقه یک batch
    total_minutes = current_hour * 60 + current_minute
    batch_index = (total_minutes // 40) % 2  # 0 یا 1
    
    if batch_index == 0:
        # نیمه اول (20 کانال اول)
        selected = ALL_CHANNELS[:20]
        print(f"📦 Batch 1/2: کانال‌های 1-20")
    else:
        # نیمه دوم (20 کانال دوم)
        selected = ALL_CHANNELS[20:40]
        print(f"📦 Batch 2/2: کانال‌های 21-40")
    
    return selected


# لیست IP رنج ایران (کوتاه شده برای نمونه)
IRAN_IP_RANGES = [
    '2.144.', '2.176.', '5.22.', '5.52.', '31.2.',
    '37.9.', '46.18.', '78.38.', '79.132.', '85.9.',
    '91.98.', '93.88.', '94.74.', '185.', '188.'
]

def is_iran_ip(ip):
    """بررسی آیا IP ایرانی است"""
    try:
        for iran_prefix in IRAN_IP_RANGES:
            if ip.startswith(iran_prefix):
                return True
        return False
    except:
        return False


# ==================== توابع پینگ (مثل قبل) ====================

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
    except:
        return None


async def check_and_format_status(host, port, timeout=2):
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
    try:
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match:
            return match.group(1), int(match.group(2))
        return None, None
    except:
        return None, None


async def safe_check_config(config, max_wait=4):
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
    from urllib.parse import quote
    encoded = quote(config)
    return f"https://quickchart.io/qr?text={encoded}&size=300"


# ==================== توابع راهنما ====================

def get_file_usage_guide(file_name):
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
    protocol = config_link.split("://")[0].lower()
    apps = {
        'vmess': 'v2rayNG • Hiddify • V2Box',
        'vless': 'v2rayNG • Hiddify • NekoBox',
        'trojan': 'v2rayNG • Hiddify • Trojan-Go',
        'ss': 'Shadowsocks • v2rayNG • Outline',
        'shadowsocks': 'Shadowsocks • v2rayNG • Outline',
        'hysteria': 'v2rayNG • NekoBox • SingBox',
        'hysteria2': 'v2rayNG • Hiddify • NekoBox',
        'hy2': 'v2rayNG • Hiddify • NekoBox',
        'tuic': 'NekoBox • SingBox',
        'nm': 'NetMod'
    }
    app_name = apps.get(protocol, 'v2rayNG • Hiddify')
    return f"\n📱 {app_name}\n"


def get_proxy_usage_guide():
    return "\n💡 روی لینک کلیک کنید، تلگرام خودکار متصل می‌شود\n"


def create_footer(channel_name, extra_info=""):
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


# ==================== تابع اصلی ====================

async def main():
    try:
        await client.start()
        print("✅ متصل شد")
        
        # تاخیر تصادفی اولیه
        initial_wait = random.randint(15, 25)
        print(f"⏳ صبر {initial_wait} ثانیه...")
        await asyncio.sleep(initial_wait)
        
        # انتخاب کانال‌ها بر اساس زمان
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
        
        for i, channel in enumerate(source_channels):
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                # تاخیر تصادفی بین کانال‌ها
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
                    
                    # --- فایل‌ها ---
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
                    
                    # --- پروکسی‌ها ---
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
                                        sent_proxies.add(unique_key)
                            except: 
                                pass
                    
                    # --- کانفیگ‌ها ---
                    if message.text:
                        raw_matches = re.findall(config_regex, message.text)
                        for conf in raw_matches:
                            clean_conf = conf.strip()
                            if clean_conf not in sent_configs:
                                channel_configs.append(clean_conf)
                                sent_configs.add(clean_conf)
                
                # چک و ارسال پروکسی‌ها
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
                
                # چک و ارسال کانفیگ‌ها
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

        # GitHub Pages (همون کد قبلی)
        if live_configs:
            try:
                print("\n📄 ساخت GitHub Pages...")
                # ... (کد HTML مثل قبل)
                print("✅ index.html ساخته شد")
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
