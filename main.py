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
PING_TIMEOUT = 2  # ثانیه
MAX_PING_WAIT = 4  # ثانیه
CONCURRENT_CHECKS = 15  # تعداد چک همزمان
SKIP_PING_EXTENSIONS = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}  # فایل‌ها چک نمیشن

# لیست کامل کانال‌ها
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
        latency = int((time.time() - start) * 1000)  # میلی‌ثانیه
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
        
        # رنگ‌بندی بر اساس پینگ
        if latency < 100:
            emoji = "🟢"
            status = "عالی"
        elif latency < 200:
            emoji = "🟡"
            status = "خوب"
        elif latency < 400:
            emoji = "🟠"
            status = "متوسط"
        else:
            emoji = "🔴"
            status = "ضعیف"
        
        return f"{emoji} {status}", latency
    
    except:
        return None, None


def extract_server_info(config):
    """استخراج IP و Port از کانفیگ"""
    try:
        protocol = config.split("://")[0].lower()
        
        if protocol == "vmess":
            # دیکد کردن vmess
            encoded = config.split("://")[1]
            decoded = json.loads(base64.b64decode(encoded))
            return decoded.get("add"), int(decoded.get("port", 443))
        
        elif protocol in ["vless", "trojan", "ss", "shadowsocks", "hysteria", "hysteria2", "hy2", "tuic"]:
            # پارس کردن با regex
            match = re.search(r"@([\w\.-]+):(\d+)", config)
            if match:
                return match.group(1), int(match.group(2))
        
        return None, None
    
    except Exception as e:
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


async def batch_check_items(items, check_func, max_concurrent=15):
    """چک کردن batch با محدودیت همزمانی"""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def check_one(item):
        async with semaphore:
            return item, await check_func(item, max_wait=MAX_PING_WAIT)
    
    tasks = [check_one(item) for item in items]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # ساخت دیکشنری نتایج
    result_dict = {}
    for result in results:
        if not isinstance(result, Exception) and result:
            item, (status, latency) = result
            result_dict[item] = (status, latency)
    
    return result_dict


# ==================== توابع راهنما (مثل قبل) ====================

def get_file_usage_guide(file_name):
    """راهنمای استفاده بر اساس پسوند فایل"""
    
    ext = file_name.lower().split('.')[-1]
    
    guides = {
        'npv4': {
            'apps': ['NapsternetV', 'v2rayNG'],
            'emoji': '📱',
            'note': 'فایل قابل ایمپورت مستقیم'
        },
        'npv2': {
            'apps': ['NapsternetV'],
            'emoji': '📱',
            'note': 'نسخه قدیمی‌تر NapsternetV'
        },
        'npvt': {
            'apps': ['NapsternetV'],
            'emoji': '📱',
            'note': 'فرمت تونل NapsternetV'
        },
        'dark': {
            'apps': ['DarkProxy'],
            'emoji': '🌑',
            'note': 'فقط در DarkProxy قابل استفاده'
        },
        'ehi': {
            'apps': ['HTTP Injector', 'HTTP Custom'],
            'emoji': '📶',
            'note': 'نیاز به تنظیمات دستی دارد'
        },
        'txt': {
            'apps': ['v2rayNG', 'v2rayN', 'Nekobox', 'Hiddify'],
            'emoji': '📄',
            'note': 'فایل لیست کانفیگ - قابل ایمپورت'
        },
        'conf': {
            'apps': ['Shadowrocket', 'Quantumult', 'Surge'],
            'emoji': '⚙️',
            'note': 'فایل پیکربندی'
        },
        'json': {
            'apps': ['v2rayN', 'v2rayNG', 'Nekoray'],
            'emoji': '📋',
            'note': 'فایل JSON خام - نیاز به ایمپورت دستی'
        }
    }
    
    info = guides.get(ext, {
        'apps': ['سایر نرم‌افزارها'],
        'emoji': '📂',
        'note': 'نوع فایل شناخته نشده'
    })
    
    apps_text = " • ".join(info['apps'])
    
    usage = f"\n{info['emoji']} **قابل استفاده در:**\n"
    usage += f"   ├ {apps_text}\n"
    usage += f"   └ {info['note']}\n"
    
    return usage


def get_config_usage_guide(config_link):
    """راهنمای استفاده بر اساس نوع کانفیگ"""
    
    protocol = config_link.split("://")[0].lower()
    
    guides = {
        'vmess': {
            'apps': ['v2rayNG', 'v2rayN', 'Nekobox', 'Hiddify'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'پروتکل VMess - پشتیبانی گسترده'
        },
        'vless': {
            'apps': ['v2rayNG', 'Nekoray', 'Hiddify', 'v2rayN'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'پروتکل VLESS - سبک‌تر از VMess'
        },
        'trojan': {
            'apps': ['v2rayNG', 'Trojan-Go', 'Hiddify'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'پروتکل Trojan - امنیت بالا'
        },
        'ss': {
            'apps': ['Shadowsocks', 'v2rayNG', 'Outline'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'Shadowsocks کلاسیک'
        },
        'shadowsocks': {
            'apps': ['Shadowsocks', 'v2rayNG', 'Outline'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'Shadowsocks - سرعت بالا'
        },
        'hysteria': {
            'apps': ['v2rayNG', 'NekoBox', 'SingBox'],
            'platforms': '🤖 Android • 🪟 Windows',
            'note': 'Hysteria - اتصالات پرسرعت'
        },
        'hysteria2': {
            'apps': ['v2rayNG', 'NekoBox', 'Hiddify'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'Hysteria2 - نسخه بهبود یافته'
        },
        'hy2': {
            'apps': ['v2rayNG', 'NekoBox', 'Hiddify'],
            'platforms': '🤖 Android • 🪟 Windows • 🍎 iOS',
            'note': 'Hysteria2 - نسخه بهبود یافته'
        },
        'tuic': {
            'apps': ['NekoBox', 'SingBox', 'v2rayNG'],
            'platforms': '🤖 Android • 🪟 Windows',
            'note': 'TUIC - بر پایه QUIC'
        },
        'nm': {
            'apps': ['NetMod'],
            'platforms': '🤖 Android فقط',
            'note': 'اختصاصی NetMod'
        },
        'nm-vless': {
            'apps': ['NetMod'],
            'platforms': '🤖 Android فقط',
            'note': 'NetMod با VLESS'
        },
        'nm-vmess': {
            'apps': ['NetMod'],
            'platforms': '🤖 Android فقط',
            'note': 'NetMod با VMess'
        }
    }
    
    info = guides.get(protocol, {
        'apps': ['کلاینت‌های v2ray'],
        'platforms': '🤖 Android • 🪟 Windows',
        'note': 'پروتکل قابل استفاده'
    })
    
    usage = f"\n📲 **نرم‌افزارهای پشتیبانی‌شده:**\n"
    usage += f"   {' • '.join(info['apps'][:3])}"
    
    if len(info['apps']) > 3:
        usage += f" • +{len(info['apps'])-3} مورد دیگر"
    
    usage += f"\n\n{info['platforms']}\n"
    usage += f"💡 {info['note']}\n"
    
    return usage


def get_proxy_usage_guide():
    """راهنمای استفاده پروکسی MTProto"""
    
    usage = "\n🔐 **پروکسی MTProto تلگرام**\n"
    usage += "   ├ روی لینک کلیک کنید\n"
    usage += "   ├ تلگرام خودکار باز می‌شود\n"
    usage += "   └ روی «اتصال» بزنید\n\n"
    usage += "⚡ بدون نیاز به نرم‌افزار جانبی\n"
    
    return usage


def create_footer(channel_name, extra_info=""):
    """فوتر زیباتر"""
    
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
        "hysteria": "#hysteria #v2ray",
        "hysteria2": "#hysteria2 #v2ray",
        "hy2": "#hysteria2 #v2ray",
        "tuic": "#tuic #v2ray",
        "proxy": "#MTProto #Proxy",
        "npv4": "#netmod #npv",
        "npv2": "#netmod #npv",
        "npvt": "#netmod #npvt",
        "dark": "#darkproxy",
        "ehi": "#httpinjector",
        "nm": "#netmod"
    }
    
    hashtags = hashtag_map.get(extra_info.lower(), "#V2Ray #VPN")
    
    footer = "\n" + "─" * 25 + "\n"
    footer += f"{hashtags}\n"
    footer += f"🗓 {date_str} • 🕐 {time_str}\n"
    footer += f"📡 منبع: {channel_name}\n"
    footer += f"🔗 {destination_channel}"
    
    return footer


# ==================== تابع اصلی ====================

async def main():
    """تابع اصلی با پینگ چک"""
    
    try:
        await client.start()
        print("✅ متصل شد")
        
        # بررسی 1 ساعت گذشته
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=1)
        
        config_regex = r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic|hysteria2?|nm(?:-[\w-]+)?)://[^\s\n]+"
        
        print("--- شروع ---")
        
        sent_files = set()
        sent_proxies = set()
        sent_configs = set()
        
        # خواندن تاریخچه
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
            print(f"⚠️ خطا در تاریخچه: {e}")

        sent_count = 0
        MAX_PER_RUN = 40
        
        # جمع‌آوری آیتم‌های جدید برای چک
        new_proxies_to_check = []
        new_configs_to_check = []
        
        for channel in source_channels:
            if sent_count >= MAX_PER_RUN:
                break
            
            try:
                print(f"🔍 {channel}...")
                
                async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True, limit=50):
                    
                    if sent_count >= MAX_PER_RUN:
                        break
                    
                    ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                    
                    # جمع‌آوری پروکسی‌ها
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
                                    new_proxies_to_check.append((final_link, ch_title))
                                    sent_proxies.add(unique_key)
                        except: 
                            pass
                    
                    # جمع‌آوری فایل‌ها (بدون چک)
                    if message.file:
                        file_name = message.file.name if message.file.name else ""
                        
                        if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                            if file_name not in sent_files:
                                try:
                                    caption = f"📂 **فایل: {file_name}**\n"
                                    caption += get_file_usage_guide(file_name)
                                    caption += create_footer(ch_title, file_name.lower().split('.')[-1])
                                    
                                    await client.send_file(destination_channel, message.media, caption=caption)
                                    print(f"✅ فایل: {file_name}")
                                    sent_files.add(file_name)
                                    sent_count += 1
                                    await asyncio.sleep(1)
                                except Exception as e:
                                    print(f"❌ خطا فایل: {e}")
                    
                    # جمع‌آوری کانفیگ‌ها
                    if message.text:
                        raw_matches = re.findall(config_regex, message.text)
                        
                        for conf in raw_matches:
                            clean_conf = conf.strip()
                            
                            if clean_conf not in sent_configs:
                                new_configs_to_check.append((clean_conf, ch_title))
                                sent_configs.add(clean_conf)

            except Exception as e:
                print(f"❌ خطا {channel}: {e}")
                continue
        
        # ========== چک کردن Batch ==========
        
        print(f"\n🔍 شروع چک پینگ...")
        print(f"   پروکسی‌ها: {len(new_proxies_to_check)}")
        print(f"   کانفیگ‌ها: {len(new_configs_to_check)}")
        
        # چک پروکسی‌ها
        proxy_results = {}
        if ENABLE_PING_CHECK and new_proxies_to_check:
            proxy_links = [p[0] for p in new_proxies_to_check]
            proxy_results = await batch_check_items(proxy_links, safe_check_proxy, CONCURRENT_CHECKS)
            print(f"✅ پروکسی‌ها چک شد")
        
        # چک کانفیگ‌ها
        config_results = {}
        if ENABLE_PING_CHECK and new_configs_to_check:
            config_links = [c[0] for c in new_configs_to_check]
            config_results = await batch_check_items(config_links, safe_check_config, CONCURRENT_CHECKS)
            print(f"✅ کانفیگ‌ها چک شد")
        
        # ========== ارسال با نتایج ==========
        
        # ارسال پروکسی‌ها
        if new_proxies_to_check:
            proxies_with_status = []
            for proxy_link, ch_title in new_proxies_to_check:
                status, latency = proxy_results.get(proxy_link, (None, None))
                proxies_with_status.append((proxy_link, status, latency))
            
            if proxies_with_status:
                proxy_text = "🔵 **لیست پروکسی‌های جدید:**\n\n"
                
                for i, (proxy, status, latency) in enumerate(proxies_with_status, 1):
                    if status and latency:
                        proxy_text += f"{i}. [اتصال سریع]({proxy}) • {status} ({latency}ms)\n"
                    elif status:
                        proxy_text += f"{i}. [اتصال سریع]({proxy}) • {status}\n"
                    else:
                        proxy_text += f"{i}. [اتصال سریع]({proxy})\n"
                
                proxy_text += get_proxy_usage_guide()
                proxy_text += create_footer(new_proxies_to_check[0][1], "proxy")
                
                try:
                    await client.send_message(destination_channel, proxy_text, link_preview=False)
                    print(f"✅ {len(proxies_with_status)} پروکسی ارسال شد")
                    sent_count += 1
                    await asyncio.sleep(1)
                except Exception as e:
                    print(f"❌ خطا ارسال پروکسی: {e}")
        
        # ارسال کانفیگ‌ها
        for conf, ch_title in new_configs_to_check:
            if sent_count >= MAX_PER_RUN:
                break
            
            prot = conf.split("://")[0].upper()
            if "NM-" in prot: 
                prot = "NETMOD"
            
            status, latency = config_results.get(conf, (None, None))
            
            final_txt = f"🔮 **کانفیگ {prot}**\n\n"
            final_txt += f"`{conf}`\n"
            
            # اضافه کردن وضعیت
            if status and latency:
                final_txt += f"\n📊 **وضعیت:** {status} • **پینگ:** {latency}ms\n"
            elif status:
                final_txt += f"\n📊 **وضعیت:** {status}\n"
            
            final_txt += get_config_usage_guide(conf)
            final_txt += create_footer(ch_title, prot.lower())
            
            try:
                await client.send_message(destination_channel, final_txt, link_preview=False)
                print(f"✅ کانفیگ {prot}")
                sent_count += 1
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ خطا کانفیگ: {e}")

        print(f"\n✅ پایان ({sent_count} ارسال شد)")

    except Exception as e:
        print(f"❌ خطای حیاتی: {e}")
    
    finally:
        await client.disconnect()


if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
