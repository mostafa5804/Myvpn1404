import os
import re
import jdatetime
import pytz
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl

# --- تنظیمات ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

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

def create_footer(channel_name, extra_info=""):
    now_iran = datetime.now(iran_tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = j_date.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    # ساخت هشتگ ساده
    hashtags = "#V2Ray #VPN"
    if "vmess" in extra_info: hashtags = "#vmess #v2ray"
    elif "vless" in extra_info: hashtags = "#vless #v2ray"
    elif "trojan" in extra_info: hashtags = "#trojan"
    elif "netmod" in extra_info: hashtags = "#netmod #nm"
    
    return (
        f"\n\n━━━━━━━━━━━━━━\n"
        f"{hashtags}\n"
        f"📅 {date_str} | ⏰ {time_str}\n"
        f"📢 Source: {channel_name}\n"
        f"🆔 {destination_channel}"
    )

async def main():
    # بررسی ۲۴ ساعت گذشته برای اطمینان
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # regex کامل
    config_regex = r"(?:vmess|vless|trojan|ss|tuic|hysteria|nm|nm-xray-json|nm-vless|nm-vmess)://[^\s\n]+"
    
    print("--- Started (Repaired Old Version) ---")
    
    sent_files = set()
    sent_proxies = set()
    sent_configs = set()
    
    # خواندن تاریخچه
    try:
        async for msg in client.iter_messages(destination_channel, limit=150):
            if msg.file and msg.file.name: sent_files.add(msg.file.name)
            if msg.text:
                matches = re.findall(config_regex, msg.text)
                for c in matches: sent_configs.add(c.strip())
                # استخراج آی‌پی پروکسی‌های قبلی
                links = re.findall(r"server=([\w\.-]+)", msg.text)
                for l in links: sent_proxies.add(l)
    except Exception as e:
        print(f"Warning: History check failed: {e}")

    print(f"Loaded history items.")

    for channel in source_channels:
        try:
            print(f"Checking {channel}...")
            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                # --- 1. پردازش پروکسی‌ها ---
                extracted_proxies = []
                if message.entities:
                    for ent in message.entities:
                        if isinstance(ent, MessageEntityTextUrl) and "proxy?server=" in ent.url:
                            extracted_proxies.append(ent.url)
                if message.text:
                    extracted_proxies.extend(re.findall(r"(tg://proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+)", message.text))
                
                new_proxies = []
                for p in list(set(extracted_proxies)):
                    try:
                        server_val = p.split("server=")[1].split("&")[0]
                        if server_val not in sent_proxies:
                            final_link = p.replace("https://t.me/", "tg://")
                            new_proxies.append(final_link)
                            sent_proxies.add(server_val)
                    except: pass

                if new_proxies:
                    proxy_text = "🔵 **لیست پروکسی‌های جدید:**\n\n"
                    for i, proxy in enumerate(new_proxies, 1):
                        proxy_text += f"{i}. [اتصال سریع]({proxy})\n"
                    
                    try:
                        # گرفتن نام کانال
                        ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                        await client.send_message(destination_channel, proxy_text + create_footer(ch_title, "proxy"), link_preview=False)
                        print(f"Sent {len(new_proxies)} proxies")
                    except: pass

                # --- 2. پردازش فایل‌ها ---
                if message.file:
                    file_name = message.file.name if message.file.name else ""
                    if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                        if file_name not in sent_files:
                            try:
                                ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                                caption = f"📂 **File: {file_name}**" + create_footer(ch_title, file_name.lower())
                                await client.send_file(destination_channel, message.media, caption=caption)
                                print(f"Sent file: {file_name}")
                                sent_files.add(file_name)
                            except: pass

                # --- 3. پردازش کانفیگ‌های متنی (تعمیر شده) ---
                if message.text:
                    raw_matches = re.findall(config_regex, message.text)
                    for conf in raw_matches:
                        clean_conf = conf.strip()
                        if clean_conf not in sent_configs:
                            
                            prot = clean_conf.split("://")[0].upper()
                            if "NM-" in prot or "XRAY" in prot: prot = "NETMOD"

                            final_txt = f"🔮 **کانفیگ {prot}**\n\n`{clean_conf}`"
                            
                            try:
                                ch_title = message.chat.title if hasattr(message.chat, 'title') else channel
                                await client.send_message(destination_channel, final_txt + create_footer(ch_title, prot.lower()), link_preview=False)
                                sent_configs.add(clean_conf)
                                print(f"Sent config: {prot}")
                            except: pass

        except Exception as e:
            print(f"Error checking {channel}: {e}")

    print("--- End ---")

with client:
    client.loop.run_until_complete(main())
