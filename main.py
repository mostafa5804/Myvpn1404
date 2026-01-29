import os
import re
import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
import jdatetime
import pytz

# --- Configs ---
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

async def main():
    print("--- Started (Simple Mode) ---")
    # بررسی 24 ساعت گذشته
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=24)
    config_regex = r"(?:vmess|vless|trojan|ss|tuic|hysteria|nm|nm-xray-json|nm-vless|nm-vmess)://[^\s\n]+"

    sent_hashes = set()
    
    # 1. خواندن تاریخچه (برای جلوگیری از تکرار)
    try:
        async for msg in client.iter_messages(destination_channel, limit=100):
            if msg.file and msg.file.name: sent_hashes.add(msg.file.name)
            if msg.text:
                matches = re.findall(config_regex, msg.text)
                for c in matches: sent_hashes.add(c.strip())
    except Exception as e:
        print(f"History Error: {e}")

    # 2. بررسی کانال‌ها
    for channel in source_channels:
        try:
            print(f"Checking {channel}...")
            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                # --- FILES ---
                if message.file:
                    fname = message.file.name if message.file.name else "Config"
                    if any(fname.lower().endswith(ext) for ext in allowed_extensions):
                        if fname not in sent_hashes:
                            now_iran = datetime.now(iran_tz)
                            time_str = now_iran.strftime("%H:%M")
                            caption = f"📂 **File: {fname}**\n\n📢 {channel}\n⏰ {time_str}\n🆔 {destination_channel}"
                            await client.send_file(destination_channel, message.media, caption=caption)
                            sent_hashes.add(fname)
                            print(f"Sent File: {fname}")

                # --- CONFIGS ---
                if message.text:
                    configs = re.findall(config_regex, message.text)
                    for conf in configs:
                        clean_conf = conf.strip()
                        if clean_conf not in sent_hashes:
                            # ساده‌ترین فرمت ارسال (بدون پرچم و پینگ)
                            now_iran = datetime.now(iran_tz)
                            time_str = now_iran.strftime("%H:%M")
                            
                            prot = clean_conf.split("://")[0].upper()
                            caption = f"🔮 **{prot} Config**\n\n`{clean_conf}`\n\n📢 {channel}\n⏰ {time_str}\n🆔 {destination_channel}"
                            
                            try:
                                await client.send_message(destination_channel, caption, link_preview=False)
                                sent_hashes.add(clean_conf)
                                print(f"Sent Config: {prot}")
                            except: pass

        except Exception as e:
            print(f"Error on {channel}: {e}")

    print("--- Finished ---")

with client:
    client.loop.run_until_complete(main())
