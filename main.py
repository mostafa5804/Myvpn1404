import os
from telethon import TelegramClient
from telethon.sessions import StringSession

# دریافت متغیرها
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_string = os.environ['SESSION_STRING']
destination_channel = '@myvpn1404'

print("--- 1. Starting Connection ---")

try:
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    async def main():
        # تست 1: بررسی اطلاعات اکانت
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name} (ID: {me.id})")

        # تست 2: ارسال پیام به پیام‌های ذخیره شده (Saved Messages)
        await client.send_message('me', '🤖 Bot connected successfully from GitHub!')
        print("✅ Sent message to Saved Messages")

        # تست 3: ارسال پیام به کانال
        print(f"Attempting to send to {destination_channel}...")
        try:
            await client.send_message(destination_channel, '🛠 **تست اتصال ربات**\n\nاگر این پیام را می‌بینید، ربات سالم است.')
            print("✅ SUCCES: Message sent to channel!")
        except Exception as e:
            print(f"❌ ERROR sending to channel: {e}")
            print("راه حل: مطمئن شوید اکانت ربات در کانال ادمین است.")

    with client:
        client.loop.run_until_complete(main())

except Exception as e:
    print(f"❌ CRITICAL LOGIN ERROR: {e}")
    print("راه حل: کد SESSION_STRING شما نامعتبر یا منقضی شده است. باید دوباره آن را بسازید.")
