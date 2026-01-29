mport os
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

# لیست کانال‌های مبدأ
source_channels = [
    '@KioV2ray', '@Npvtunnel_vip', '@planB_net', '@Free_Nettm', '@mypremium98',
    '@mitivpn', '@iSeqaro', '@configraygan', '@shankamil', '@xsfilternet',
    '@varvpn1', '@iP_CF', '@cooonfig', '@DeamNet', '@anty_filter',
    '@vpnboxiran', '@Merlin_ViP', '@BugFreeNet', '@cicdoVPN', '@Farda_Ai',
    '@Awlix_ir', '@proSSH', '@vpn_proxy_custom', '@Free_HTTPCustom',
    '@sinavm', '@Amir_Alternative_Official', '@StayconnectedVPN', '@BINNER_IRAN',
    '@IranianMinds', '@vpn11ir', '@NetAccount', '@mitiivpn2', '@isharewin',
    '@v2rays_ha', '@iroproxy', '@ProxyMTProto'
]

destination_channel = '@myvpn1404'
allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')

client = TelegramClient(StringSession(session_string), api_id, api_hash)

def create_footer(channel_name):
    now_iran = datetime.now(iran_tz)
    j_date = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = j_date.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    return (
        f"\n\n━━━━━━━━━━━━━━\n"
        f"📅 {date_str} | ⏰ {time_str}\n"
        f"📢 منبع: {channel_name}\n"
        f"🆔 {destination_channel}"
    )

async def main():
    # 1. افزایش زمان اسکن به 2 ساعت برای پوشش دادن تاخیرهای گیت‌هاب
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=2)
    
    # الگوها
    v2ray_pattern = r"(vmess://|vless://|trojan://|ss://|tuic://|hysteria://|ine://|nm://)"
    
    print("--- 1. Learning Sent History (Anti-Duplicate) ---")
    
    # **حافظه موقت:** لیست چیزهایی که قبلا فرستادیم
    sent_files = set()
    sent_proxies = set()
    
    # خواندن ۱۰۰ پیام آخر کانال خودت برای جلوگیری از تکرار
    try:
        async for msg in client.iter_messages(destination_channel, limit=100):
            if msg.file and msg.file.name:
                sent_files.add(msg.file.name)
            
            if msg.text:
                # استخراج لینک‌های داخل متن‌های قبلی خودمان
                links = re.findall(r"(tg://proxy\?server=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+)", msg.text)
                for l in links:
                    # فقط قسمت سرور را نگه میداریم برای مقایسه راحت‌تر
                    if "server=" in l:
                        server_val = l.split("server=")[1].split("&")[0]
                        sent_proxies.add(server_val)
                        
    except Exception as e:
        print(f"Warning: Could not check history: {e}")

    print(f"Loaded {len(sent_files)} files and {len(sent_proxies)} proxies from history.")
    print("--- 2. Start Checking Sources ---")

    for channel in source_channels:
        try:
            print(f"Checking {channel}...")
            try:
                entity = await client.get_entity(channel)
                channel_title = entity.title if entity.title else channel
            except:
                continue

            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                # --- پردازش پروکسی‌ها ---
                extracted_proxies = []
                if message.entities:
                    for ent in message.entities:
                        if isinstance(ent, MessageEntityTextUrl) and "proxy?server=" in ent.url:
                            extracted_proxies.append(ent.url)
                if message.text:
                    extracted_proxies.extend(re.findall(r"(tg://proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+|https://t\.me/proxy\?server=[\w\.-]+&port=\d+&secret=[\w\.-]+)", message.text))
                
                # فیلتر کردن پروکسی‌های تکراری
                new_proxies = []
                for p in list(set(extracted_proxies)):
                    # چک میکنیم آیا سرور این پروکسی قبلا ثبت شده؟
                    try:
                        server_val = p.split("server=")[1].split("&")[0]
                        if server_val not in sent_proxies:
                            new_proxies.append(p)
                            sent_proxies.add(server_val) # به لیست اضافه کن که در همین اجرا هم تکراری نفرسته
                    except:
                        pass

                if new_proxies:
                    print(f"Found {len(new_proxies)} NEW proxies")
                    proxy_text = "🔵 **لیست پروکسی‌های جدید:**\n\n"
                    for i, proxy in enumerate(new_proxies, 1):
                        proxy = proxy.replace("https://t.me/", "tg://")
                        proxy_text += f"{i}. [اتصال سریع]({proxy})\n"
                    
                    await client.send_message(destination_channel, proxy_text + create_footer(channel_title), link_preview=False)

                # --- پردازش فایل‌ها ---
                elif message.file:
                    file_name = message.file.name if message.file.name else ""
                    # شرط مهم: بررسی تکراری نبودن اسم فایل
                    if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                        if file_name not in sent_files:
                            caption = (message.text or "") + create_footer(channel_title)
                            if len(caption) > 1000: caption = caption[:950] + "..."
                            
                            await client.send_file(destination_channel, message.media, caption=caption)
                            print(f"Sent NEW file: {file_name}")
                            sent_files.add(file_name) # اضافه به حافظه
                        else:
                            print(f"Skipped duplicate file: {file_name}")

                # --- پردازش متن V2Ray ---
                elif message.text and re.search(v2ray_pattern, message.text, re.IGNORECASE):
                    # برای متن‌های طولانی v2ray تشخیص تکرار سخت است،
                    # اما می‌توانیم چک کنیم اگر دقیقاً همان متن در ۱۰۰ پیام آخر بوده نفرستیم
                    # فعلا برای سادگی فرض میکنیم اگر ۲ ساعت گذشته باشد جدید است
                    # (چون تشخیص تکرار متن v2ray با هدرهای مختلف پیچیده است)
                     pass 
                     # اینجا را فعلا غیرفعال کردم تا اسپم نشود یا میتوانید فعال کنید
                     # معمولا کانال‌ها فایل میگذارند.

        except Exception as e:
            print(f"Error checking {channel}: {e}")

    print("--- End ---")

with client:
    client.loop.run_until_complete(main())
