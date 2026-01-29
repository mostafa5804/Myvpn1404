import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
import jdatetime
import pytz

# --- تنظیمات ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

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

# --- تابع ساخت متن شیک (بدون پینگ/پرچم) ---
def create_caption(content_type, extra_info, source_name):
    now_iran = datetime.now(iran_tz)
    date_str = jdatetime.datetime.fromgregorian(datetime=now_iran).strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    # هشتگ‌گذاری هوشمند بر اساس نوع محتوا
    hashtags = "#V2Ray #VPN"
    lower_info = extra_info.lower()
    
    if "vmess" in lower_info: hashtags += " #vmess #v2rayng"
    elif "vless" in lower_info: hashtags += " #vless #v2rayng"
    elif "trojan" in lower_info: hashtags += " #trojan"
    elif "reality" in lower_info: hashtags += " #reality"
    elif "netmod" in lower_info or "nm-" in lower_info: hashtags += " #NetMod #nm"
    elif "napster" in lower_info or "npv" in lower_info: hashtags += " #NapsternetV #npv4"
    elif "proxy" in lower_info: hashtags = "#Proxy #MTProto #Telegram"

    caption = (
        f"{content_type}\n"
        f"➖➖➖➖➖➖➖\n"
        f"🏷 {extra_info}\n"
        f"{hashtags}\n"
        f"➖➖➖➖➖➖➖\n"
        f"📅 {date_str} | ⏰ {time_str}\n"
        f"📢 Source: {source_name}\n"
        f"🆔 {destination_channel}"
    )
    return caption

async def main():
    print("--- 🤖 Bot Started (Stable Clean Version) ---")
    
    # بازه زمانی مطمئن (۲۴ ساعت) که چیزی جا نیفتد
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # الگوی کامل شناسایی (شامل نت‌مود جدید)
    config_regex = r"(?:vmess|vless|trojan|ss|tuic|hysteria|nm|nm-xray-json|nm-vless|nm-vmess)://[^\s\n]+"
    
    sent_hashes = set()
    
    # 1. یادگیری از تاریخچه کانال خودمان (جلوگیری از تکرار)
    try:
        async for msg in client.iter_messages(destination_channel, limit=200):
            if msg.file and msg.file.name: sent_hashes.add(msg.file.name)
            if msg.text:
                matches = re.findall(config_regex, msg.text)
                for c in matches: sent_hashes.add(c.strip())
                proxies = re.findall(r"server=([\w\.-]+)", msg.text)
                for p in proxies: sent_hashes.add(p)
    except Exception as e:
        print(f"⚠️ History Error: {e}")

    print(f"ℹ️ History loaded: {len(sent_hashes)} items")

    # 2. اسکن کانال‌های منبع
    for channel in source_channels:
        try:
            print(f"🔍 Scanning {channel}...")
            try:
                entity = await client.get_entity(channel)
                title = entity.title if entity.title else channel
            except: 
                print(f"❌ Cannot access {channel}")
                continue

            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                # --- A. پردازش فایل‌ها ---
                if message.file:
                    fname = message.file.name if message.file.name else "Config"
                    if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                        if fname not in sent_hashes:
                            file_type = fname.split('.')[-1].upper()
                            
                            header = f"📂 **فایل کانفیگ جدید**"
                            cap = create_caption(header, f"File: {file_type}", title)
                            
                            try:
                                await client.send_file(destination_channel, message.media, caption=cap)
                                sent_hashes.add(fname)
                                print(f"✅ Sent File: {fname}")
                            except Exception as e:
                                print(f"Error sending file: {e}")

                # --- B. پردازش کانفیگ‌های متنی ---
                if message.text:
                    raw_matches = re.findall(config_regex, message.text)
                    for conf in raw_matches:
                        clean_conf = conf.strip()
                        if clean_conf not in sent_hashes:
                            
                            # تشخیص نوع پروتکل برای تیتر
                            prot = clean_conf.split("://")[0].upper()
                            if "NM-" in prot or "XRAY" in prot: prot = "NETMOD"
                            
                            # متن اصلی پیام
                            final_txt = f"🔮 **کانفیگ {prot}**\n\n`{clean_conf}`"
                            
                            # ساخت کپشن با هشتگ
                            cap = create_caption(final_txt, f"Protocol: {prot}", title)
                            
                            try:
                                await client.send_message(destination_channel, cap, link_preview=False)
                                sent_hashes.add(clean_conf)
                                print(f"✅ Sent Config: {prot}")
                            except Exception as e:
                                print(f"Error sending config: {e}")

                # --- C. پردازش پروکسی‌ها (لیست زیبا) ---
                extracted_proxies = []
                if message.entities:
                    for ent in message.entities:
                        if isinstance(ent, MessageEntityTextUrl) and "proxy?server=" in ent.url:
                            extracted_proxies.append(ent.url)
                if message.text:
                    extracted_proxies.extend(re.findall(r"(tg://proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+)", message.text))
                
                # فیلتر تکراری‌ها در همین پیام
                unique_proxies = list(set(extracted_proxies))
                valid_proxies = []
                
                for p in unique_proxies:
                    try:
                        # استخراج سرور برای چک کردن تکراری بودن
                        match = re.search(r"server=([\w\.-]+)", p)
                        if match:
                            server_val = match.group(1)
                            if server_val not in sent_hashes:
                                final_link = p.replace("https://t.me/", "tg://")
                                valid_proxies.append(final_link)
                                sent_hashes.add(server_val)
                    except: pass

                if valid_proxies:
                    # ساخت لیست شماره‌گذاری شده
                    proxy_body = "🔵 **لیست پروکسی‌های جدید**\n\n"
                    for i, link in enumerate(valid_proxies, 1):
                        proxy_body += f"{i}. [اتصال سریع (Proxy {i})]({link})\n"
                    
                    cap = create_caption(proxy_body, f"New Proxies ({len(valid_proxies)}x)", title)
                    
                    try:
                        await client.send_message(destination_channel, cap, link_preview=False)
                        print(f"✅ Sent {len(valid_proxies)} Proxies")
                    except: pass

        except Exception as e:
            print(f"Error on {channel}: {e}")

    print("--- End ---")

with client:
    client.loop.run_until_complete(main())
