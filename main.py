import os
import re
import jdatetime
import pytz
import asyncio
import json
import base64
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl

# --- تنظیمات ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

# تنظیمات پینگ
ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
MAX_PING_WAIT = 4

source_channels = [
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

# ==================== توابع پینگ ====================

async def measure_tcp_latency(host, port, timeout=2):
    """اندازه‌گیری تاخیر TCP"""
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
    """بررسی وضعیت و برگرداندن ایموجی + پینگ"""
    
    if not host or not port:
        return None, None
    
    try:
        latency = await measure_tcp_latency(host, port, timeout)
        
        if latency is None:
            return "🔴 آفلاین", None
        
        if latency < 100:
            return "🟢 عالی", latency
        elif latency < 200:
            return "🟡 خوب", latency
        elif latency < 400:
            return "🟠 متوسط", latency
        else:
            return "🔴 ضعیف", latency
    
    except:
        return None, None


def extract_server_info(config):
    """استخراج IP و Port از کانفیگ"""
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
    """استخراج server و port از لینک پروکسی"""
    try:
        match = re.search(r"server=([\w\.-]+)&port=(\d+)", proxy_link)
        if match:
            return match.group(1), int(match.group(2))
        return None, None
    except:
        return None, None


async def safe_check_config(config, max_wait=4):
    """چک امن با timeout"""
    try:
        host, port = extract_server_info(config)
        if host and port:
            status, latency = await asyncio.wait_for(
                check_and_format_status(host, port, timeout=PING_TIMEOUT),
                timeout=max_wait
            )
            return status, latency
        return None, None
    except asyncio.TimeoutError:
        return "⏱️ Timeout", None
    except:
        return None, None


async def safe_check_proxy(proxy_link, max_wait=4):
    """چک امن پروکسی"""
    try:
        host, port = extract_proxy_info(proxy_link)
        if host and port:
            status, latency = await asyncio.wait_for(
                check_and_format_status(host, port, timeout=PING_TIMEOUT),
                timeout=max_wait
            )
            return status, latency
        return None, None
    except asyncio.TimeoutError:
        return "⏱️ Timeout", None
    except:
        return None, None


# ==================== توابع راهنما (مینیمال) ====================

def get_file_usage_guide(file_name):
    """راهنمای فایل خلاصه"""
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
    """راهنمای کانفیگ خلاصه"""
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
        'nm': 'NetMod',
        'nm-vless': 'NetMod',
        'nm-vmess': 'NetMod',
        'nm-xray-json': 'NetMod'
    }
    
    app_name = apps.get(protocol, 'v2rayNG • Hiddify')
    return f"\n📱 {app_name}\n"


def get_proxy_usage_guide():
    """راهنمای پروکسی خلاصه"""
    return "\n💡 روی لینک کلیک کنید، تلگرام خودکار متصل می‌شود\n"


def create_footer(channel_name, extra_info=""):
    """فوتر مینیمال"""
    
    now_iran = datetime.now(iran_tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = j_date.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    hashtag_map = {
        "vmess": "#vmess #v2ray",
        "vless": "#vless #v2ray",
        "trojan": "#trojan #v2ray",
        "ss": "#shadowsocks",
        "shadowsocks": "#shadowsocks",
        "hysteria": "#hysteria",
        "hysteria2": "#hysteria2",
        "hy2": "#hysteria2",
        "tuic": "#tuic",
        "proxy": "#MTProto",
        "npv4": "#netmod",
        "npv2": "#netmod",
        "npvt": "#netmod",
        "dark": "#darkproxy",
        "ehi": "#httpinjector",
        "nm": "#netmod"
    }
    
    hashtags = hashtag_map.get(extra_info.lower(), "#VPN")
    
    footer = f"\n{hashtags}\n"
    footer += f"🗓 {date_str} • 🕐 {time_str}\n"
    footer += f"📡 {channel_name}\n"
    footer += f"🔗 {destination_channel}"
    
    return footer


# ==================== تابع اصلی (میکس شده) ====================

async def main():
    """تابع اصلی با ارسال میکس"""
    
    try:
        await client.start()
        print("✅ متصل شد")
        
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        print("--- شروع ---")
        
        sent_files = set()
        sent_proxies = set()
        sent_configs = set()
        
        # بارگذاری تاریخچه
        try:
            print("بارگذاری تاریخچه...")
            async for msg in client.iter_messages(destination_channel, limit=200):
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
        
        except Exception as e:
            print(f"⚠️ خطا: {e}")

        sent_count = 0
        MAX_PER_RUN = 40
        
        # ========== حلقه اصلی (میکس شده) ==========
        
        for channel in source_channels:
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                print(f"🔍 {channel}...")
                
                # جمع‌آوری از این کانال
                channel_proxies = []
                channel_configs = []
                
                async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True, limit=50):
                    
                    if sent_count >= MAX_PER_RUN:
                        break
                    
                    ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                    
                    # --- 1. فایل‌ها (ارسال فوری) ---
                    if message.file:
                        file_name = message.file.name if message.file.name else ""
                        
                        if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                            if file_name not in sent_files:
                                try:
                                    caption = f"📂 **{file_name}**"
                                    caption += get_file_usage_guide(file_name)
                                    caption += create_footer(ch_title, file_name.lower().split('.')[-1])
                                    
                                    await client.send_file(destination_channel, message.media, caption=caption)
                                    print(f"✅ فایل: {file_name}")
                                    sent_files.add(file_name)
                                    sent_count += 1
                                    await asyncio.sleep(1)
                                except Exception as e:
                                    print(f"❌ خطا فایل: {e}")
                    
                    # --- 2. جمع‌آوری پروکسی‌ها ---
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
                    
                    # --- 3. جمع‌آوری کانفیگ‌ها ---
                    if message.text:
                        raw_matches = re.findall(config_regex, message.text)
                        
                        for conf in raw_matches:
                            clean_conf = conf.strip()
                            
                            if clean_conf not in sent_configs:
                                channel_configs.append(clean_conf)
                                sent_configs.add(clean_conf)
                
                # ========== چک و ارسال پروکسی‌ها این کانال ==========
                
                if channel_proxies and ENABLE_PING_CHECK:
                    print(f"   🔍 چک {len(channel_proxies)} پروکسی...")
                    
                    # چک همزمان
                    tasks = [safe_check_proxy(p, MAX_PING_WAIT) for p in channel_proxies]
                    results = await asyncio.gather(*tasks)
                    
                    # ارسال
                    proxy_text = "🔵 **پروکسی‌های جدید:**\n\n"
                    
                    for i, (proxy, (status, latency)) in enumerate(zip(channel_proxies, results), 1):
                        if status and latency:
                            proxy_text += f"{i}. [اتصال]({proxy}) • {status} ({latency}ms)\n"
                        elif status:
                            proxy_text += f"{i}. [اتصال]({proxy}) • {status}\n"
                        else:
                            proxy_text += f"{i}. [اتصال]({proxy})\n"
                    
                    proxy_text += get_proxy_usage_guide()
                    proxy_text += create_footer(ch_title, "proxy")
                    
                    try:
                        await client.send_message(destination_channel, proxy_text, link_preview=False)
                        print(f"   ✅ {len(channel_proxies)} پروکسی")
                        sent_count += 1
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"   ❌ خطا پروکسی: {e}")
                
                # ========== چک و ارسال کانفیگ‌ها این کانال ==========
                
                if channel_configs and ENABLE_PING_CHECK:
                    print(f"   🔍 چک {len(channel_configs)} کانفیگ...")
                    
                    # چک همزمان
                    tasks = [safe_check_config(c, MAX_PING_WAIT) for c in channel_configs]
                    results = await asyncio.gather(*tasks)
                    
                    # ارسال یکی یکی
                    for conf, (status, latency) in zip(channel_configs, results):
                        if sent_count >= MAX_PER_RUN:
                            break
                        
                        prot = conf.split("://")[0].upper()
                        if "NM-" in prot: 
                            prot = "NETMOD"
                        
                        final_txt = f"🔮 **کانفیگ {prot}**\n\n`{conf}`\n"
                        
                        # اضافه کردن وضعیت
                        if status and latency:
                            final_txt += f"\n📊 {status} • {latency}ms\n"
                        elif status:
                            final_txt += f"\n📊 {status}\n"
                        
                        final_txt += get_config_usage_guide(conf)
                        final_txt += create_footer(ch_title, prot.lower())
                        
                        try:
                            await client.send_message(destination_channel, final_txt, link_preview=False)
                            print(f"   ✅ {prot}")
                            sent_count += 1
                            await asyncio.sleep(1)
                        except Exception as e:
                            print(f"   ❌ خطا: {e}")

            except Exception as e:
                print(f"❌ خطا {channel}: {e}")
                continue

        print(f"\n✅ پایان ({sent_count} ارسال)")

    except Exception as e:
        print(f"❌ خطای حیاتی: {e}")
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
