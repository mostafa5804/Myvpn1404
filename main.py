import os
import re
import jdatetime
import pytz
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات اولیه ---
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']

# لیست کانال‌های مبدأ
source_channels = [
    '@KioV2ray',
    '@Npvtunnel_vip',
    '@planB_net',
    '@Free_Nettm',
    '@mypremium98',
    '@mitivpn',
    '@iSeqaro',
    '@configraygan',
    '@shankamil',
    '@xsfilternet'
]

# کانال مقصد شما
destination_channel = '@myvpn1404'

# پسوندهای مجاز
allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}

# تنظیم منطقه زمانی ایران
iran_tz = pytz.timezone('Asia/Tehran')

client = TelegramClient(StringSession(session_string), api_id, api_hash)

def create_footer(channel_name):
    """ساخت متن زیرنویس (فوتر) شامل تاریخ شمسی و ساعت"""
    now_iran = datetime.now(iran_tz)
    # تبدیل به شمسی
    j_date = jdatetime.datetime.fromgregorian(datetime=now_iran)
    date_str = j_date.strftime("%Y/%m/%d")
    time_str = now_iran.strftime("%H:%M")
    
    footer = (
        f"\n\n━━━━━━━━━━━━━━\n"
        f"📅 {date_str} | ⏰ {time_str}\n"
        f"📢 منبع: {channel_name}\n"
        f"🆔 {destination_channel}"
    )
    return footer

async def main():
    # محاسبه زمان ۱۵ دقیقه پیش برای فیلتر کردن پیام‌ها
    # چون سرور گیت‌هاب UTC است، زمان مبنا را UTC می‌گیریم
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=15)
    
    # الگوهای متنی
    pattern_regex = r"(vmess://|vless://|trojan://|ss://|tuic://|hysteria://|ine://|nm://)"

    print("--- شروع بررسی کانال‌ها ---")

    for channel in source_channels:
        try:
            print(f"Checking {channel}...")
            # گرفتن اطلاعات کانال برای نمایش نام در کپشن
            entity = await client.get_entity(channel)
            channel_title = entity.title if entity.title else channel

            async for message in client.iter_messages(channel, offset_date=time_threshold, reverse=True):
                
                should_send = False
                msg_caption = message.text or "" # متن اصلی پیام
                
                # شرط ۱: بررسی فایل
                if message.file:
                    file_name = message.file.name if message.file.name else ""
                    if any(file_name.lower().endswith(ext) for ext in allowed_extensions):
                        should_send = True
                        print(f"Found file: {file_name}")

                # شرط ۲: بررسی متن کانفیگ (اگر فایل نبود)
                elif msg_caption and re.search(pattern_regex, msg_caption, re.IGNORECASE):
                    should_send = True
                    print("Found text config")

                if should_send:
                    try:
                        # ساخت کپشن جدید (متن اصلی + فوتر شیک)
                        new_caption = msg_caption + create_footer(channel_title)
                        
                        # اگر طول متن زیاد شد، برش می‌زنیم تا ارور ندهد (محدودیت تلگرام)
                        if len(new_caption) > 1024:
                            new_caption = new_caption[:1000] + "..." + create_footer(channel_title)

                        # ارسال به کانال شما (Send به جای Forward برای اعمال تغییرات)
                        if message.file:
                            await client.send_file(destination_channel, message.media, caption=new_caption)
                        else:
                            await client.send_message(destination_channel, new_caption, link_preview=False)
                            
                    except Exception as send_error:
                        print(f"Failed to send: {send_error}")
                    
        except Exception as e:
            print(f"Error checking {channel}: {e}")

    print("--- پایان عملیات ---")

with client:
    client.loop.run_until_complete(main())

