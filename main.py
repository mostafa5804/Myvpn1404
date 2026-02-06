import os
import re
import jdatetime
import pytz
import asyncio
import json
import base64
import socket
import random
import time
import sys
import html
import hashlib
import aiohttp
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from telethon.errors.rpcerrorlist import FloodWaitError

# تلاش برای لود کردن ماژول GeoIP
try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except:
    GEOIP_AVAILABLE = False
    print("⚠️ GeoIP module not found.")

# =============================================================================
# 1. تنظیمات
# =============================================================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

ENABLE_REAL_TEST = True
REAL_TEST_TIMEOUT = 3
DATA_FILE = 'data.json'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
GITHUB_PAGES_DOMAIN = "mostafa5804.github.io/Myvpn1404"
MAX_MESSAGE_AGE_MINUTES = 90

ALL_CHANNELS = [
    '@KioV2ray', '@Npvtunnel_vip', '@planB_net', '@Free_Nettm', '@mypremium98',
    '@mitivpn', '@iSeqaro', '@configraygan', '@shankamil', '@xsfilternet',
    '@varvpn1', '@iP_CF', '@cooonfig', '@DeamNet', '@anty_filter',
    '@vpnboxiran', '@Merlin_ViP', '@BugFreeNet', '@cicdoVPN', '@Farda_Ai',
    '@Awlix_ir', '@proSSH', '@vpn_proxy_custom', '@Free_HTTPCustom',
    '@sinavm', '@Amir_Alternative_Official', '@StayconnectedVPN', '@BINNER_IRAN',
    '@IranianMinds', '@vpn11ir', '@NetAccount', '@mitiivpn2', '@isharewin',
    '@iroproxy', '@ProxyMTProto', '@darkproxy', '@configs_freeiran', '@v2rayvpnchannel'
]

allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')

# راه اندازی GeoIP
geoip_reader = None
if GEOIP_AVAILABLE and os.path.exists('GeoLite2-Country.mmdb'):
    try:
        geoip_reader = geoip2.database.Reader('GeoLite2-Country.mmdb')
        print("✅ GeoIP Loaded Successfully")
    except Exception as e:
        print(f"⚠️ GeoIP Error: {e}")

# =============================================================================
# 2. توابع کمکی
# =============================================================================

def generate_config_hash(config_str):
    try:
        clean_conf = config_str.strip()
        if clean_conf.startswith('vmess://'):
            decoded = json.loads(base64.b64decode(clean_conf.split('://')[1]))
            key = f"{decoded.get('add')}:{decoded.get('port')}:{decoded.get('id', '')}"
        elif '://' in clean_conf:
            match = re.search(r'://(.*?)@(.*):(\d+)', clean_conf)
            if match:
                key = f"{match.group(2)}:{match.group(3)}:{match.group(1)}"
            else:
                key = clean_conf
        else:
            key = clean_conf
        return hashlib.md5(key.encode()).hexdigest()
    except:
        return hashlib.md5(config_str.encode()).hexdigest()

def calculate_quality_score(latency, protocol='vmess'):
    if not latency or latency > 2000: return 0
    if latency < 200: base = 100
    elif latency < 500: base = 80
    elif latency < 1000: base = 60
    else: base = 40
    
    proto_bonus = 0
    p = protocol.lower()
    if 'reality' in p or 'vless' in p: proto_bonus = 10
    elif 'trojan' in p: proto_bonus = 5
    
    return min(100, base + proto_bonus)

def get_country_flag(ip_address):
    if not geoip_reader: return "🌐"
    try:
        response = geoip_reader.country(ip_address)
        iso_code = response.country.iso_code
        if iso_code:
            return ''.join(chr(127397 + ord(c)) for c in iso_code.upper())
        return "🚩"
    except: return "🌐"

async def check_connection(host, port):
    try:
        start = time.time()
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=REAL_TEST_TIMEOUT)
        latency = int((time.time() - start) * 1000)
        writer.close()
        try: await writer.wait_closed()
        except: pass
        return latency, True
    except:
        return None, False

def extract_server_info(config_str):
    try:
        if config_str.startswith('vmess://'):
            d = json.loads(base64.b64decode(config_str.split('://')[1]))
            return d.get('add'), int(d.get('port'))
        match = re.search(r'@([\w\.-]+):(\d+)', config_str)
        if match: return match.group(1), int(match.group(2))
    except: pass
    return None, None

async def check_config_health(config):
    host, port = extract_server_info(config)
    if not host or not port: return None, None, 0, False, "🌐"
    
    lat, success = await check_connection(host, port)
    flag = get_country_flag(host)
    
    if not success: return "🔴 آفلاین", None, 0, False, flag
    
    prot = config.split('://')[0]
    score = calculate_quality_score(lat, prot)
    status = "🟢 عالی" if lat < 300 else "🟡 خوب" if lat < 800 else "🟠 متوسط"
    return status, lat, score, True, flag

def generate_subscription(configs):
    valid_configs = [c['config'] for c in configs if c.get('quality', 0) > 0]
    if not valid_configs: return None
    
    full_text = '\n'.join(valid_configs)
    encoded = base64.b64encode(full_text.encode()).decode()
    
    with open('subscription.txt', 'w', encoding='utf-8') as f:
        f.write(encoded)
        
    return f"https://{GITHUB_PAGES_DOMAIN}/subscription.txt"

def load_data():
    if not os.path.exists(DATA_FILE): return {'configs': []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # حذف کانفیگ‌های خیلی قدیمی
            limit = time.time() - (KEEP_HISTORY_HOURS * 3600)
            return {'configs': [c for c in data.get('configs', []) if c.get('ts', 0) > limit]}
    except: return {'configs': []}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def merge_data(history, new_items):
    # ترکیب بر اساس هش برای حذف تکراری‌ها
    # نکته: در تابع main لیست history اصلاح شده و حتما هش دارد
    combined = {c['hash']: c for c in history if 'hash' in c}
    for item in new_items:
        combined[item['hash']] = item
    
    final_list = list(combined.values())
    final_list.sort(key=lambda x: x.get('quality', 0), reverse=True)
    return final_list

def get_batch():
    m = datetime.now(iran_tz).minute
    session = session_2 if session_2 else session_1
    return (ALL_CHANNELS[:20], "پارت ۱") if m < 30 else (ALL_CHANNELS[20:], "پارت ۲"), session

def get_hashtags(conf):
    return f"#{conf.split('://')[0].lower()} #v2rayNG"

# =============================================================================
# 3. بدنه اصلی
# =============================================================================
(target_channels, batch_name), active_session = get_batch()

if not active_session:
    print("❌ سشن یافت نشد")
    sys.exit(1)

client = TelegramClient(StringSession(active_session), api_id, api_hash)

async def main():
    try:
        await client.start()
        print(f"✅ ربات استارت شد: {batch_name}")
        
        hist = load_data()
        
        # ===== FIX: اصلاح دیتابیس قدیمی که هش ندارد =====
        cleaned_history = []
        seen_hashes = set()
        
        for c in hist['configs']:
            # اگر هش ندارد، برایش بساز
            if 'hash' not in c:
                c['hash'] = generate_config_hash(c['config'])
            
            # اگر کیفیت ندارد، صفر بذار
            if 'quality' not in c:
                c['quality'] = 0
                
            # جلوگیری از تکراری در خود دیتابیس
            if c['hash'] not in seen_hashes:
                seen_hashes.add(c['hash'])
                cleaned_history.append(c)
        
        # آپدیت لیست history با داده‌های اصلاح شده
        hist['configs'] = cleaned_history
        # =================================================
        
        new_items = []
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)
        
        for i, channel in enumerate(target_channels):
            try:
                print(f"📡 در حال بررسی: {channel}")
                try: entity = await client.get_entity(channel)
                except: continue
                
                msgs = await client.get_messages(entity, limit=15)
                channel_title = getattr(entity, 'title', channel)
                
                for m in msgs:
                    if m.date < cutoff or not m.text: continue
                    configs = re.findall(r'(vmess|vless|trojan|ss|hy2|tuic)://[a-zA-Z0-9\-\_\=\@\:\.\?\&\%\#]+', m.text)
                    
                    for conf in configs:
                        conf = conf.strip()
                        if '...' in conf: continue
                        
                        conf_hash = generate_config_hash(conf)
                        if conf_hash in seen_hashes: continue
                        
                        status, lat, score, online, flag = await check_config_health(conf)
                        
                        if online and score > 30:
                            proto = conf.split('://')[0].upper()
                            msg_link = f"https://t.me/{channel.replace('@', '')}/{m.id}"
                            
                            caption = (
                                f"🔮 **{proto}** {flag}\n\n"
                                f"```\n{conf}\n```\n"
                                f"📊 وضعیت: {status}\n"
                                f"⚡️ پینگ: {lat}ms | ⭐ امتیاز: {score}/100\n\n"
                                f"{get_hashtags(conf)}\n"
                                f"━━━━━━━━━━━━━━━━\n"
                                f"📅 {jdatetime.datetime.now().strftime('%Y/%m/%d %H:%M')}\n"
                                f"📢 منبع: [{channel_title}]({msg_link})\n"
                                f"🆔 {destination_channel}"
                            )
                            
                            try:
                                sent = await client.send_message(destination_channel, caption, link_preview=False)
                                my_link = f"https://t.me/{destination_channel.replace('@', '')}/{sent.id}"
                                
                                new_items.append({
                                    'protocol': proto,
                                    'config': conf,
                                    'hash': conf_hash,
                                    'latency': lat,
                                    'quality': score,
                                    'country': flag,
                                    'channel': channel_title,
                                    'ts': time.time(),
                                    't_link': my_link
                                })
                                seen_hashes.add(conf_hash)
                                await asyncio.sleep(2)
                            except Exception as e:
                                print(f"❌ خطا در ارسال: {e}")

            except Exception as e:
                print(f"❌ خطا در کانال {channel}: {e}")

        print("💾 بروزرسانی دیتابیس...")
        final_configs = merge_data(hist['configs'], new_items)
        save_data({'configs': final_configs})
        
        sub_url = generate_subscription(final_configs)
        
        print("🌐 ساخت سایت PWA...")
        await generate_site(final_configs, sub_url)
        
    except Exception as e:
        print(f"🔥 خطای کلی: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

async def generate_site(configs, sub_link):
    total = len(configs)
    high_quality = len([c for c in configs if c.get('quality', 0) >= 80])
    avg_ping = int(sum(c.get('latency', 0) for c in configs)/total) if total else 0
    update_time = jdatetime.datetime.now().strftime('%Y/%m/%d - %H:%M')
    
    cards_html = ""
    for idx, c in enumerate(configs[:60]):
        safe_conf = c['config'].replace("'", "\\'").replace('"', '\\"')
        q_class = "high" if c.get('quality', 0) >= 80 else "mid" if c.get('quality', 0) >= 50 else "low"
        
        cards_html += f"""
        <div class="card">
            <div class="card-head">
                <span class="badge proto">{c['protocol']}</span>
                <span class="flag">{c.get('country', '🌐')}</span>
                <span class="badge score {q_class}">{c.get('quality', 0)}</span>
            </div>
            <div class="card-body">
                <div class="info">
                    <span>📡 {c['channel']}</span>
                    <span>⚡ {c.get('latency', 0)}ms</span>
                </div>
                <div class="code-box" onclick="selectText(this)">{c['config'][:50]}...</div>
            </div>
            <div class="actions">
                <button class="btn copy" onclick="copyTxt('{safe_conf}')">📋 کپی</button>
                <button class="btn qr" onclick="showQR('{safe_conf}')">📱 QR</button>
                <a href="{c.get('t_link', '#')}" target="_blank" class="btn link">🔗 تلگرام</a>
            </div>
        </div>
        """

    sub_box_html = ""
    if sub_link:
        # ساخت بخش اشتراک بدون استفاده از f-string پیچیده برای جلوگیری از ارور
        sub_box_html = (
            '<div class="sub-box">'
            '<h3>🚀 لینک اشتراک هوشمند</h3>'
            '<p>لینک زیر را در V2RayNG یا Streisand وارد کنید تا لیست آپدیت شود.</p>'
            f'<a href="{sub_link}" class="sub-btn" onclick="copyTxt(\'{sub_link}\'); return false;">کپی لینک اشتراک</a>'
            '</div>'
        )

    html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Hub Pro</title>
    <link rel="manifest" href="manifest.json">
    <meta name="theme-color" content="#1e293b">
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --text: #f8fafc; --accent: #38bdf8; --green: #22c55e; --yellow: #eab308; --red: #ef4444; }}
        * {{ box-sizing: border-box; font-family: 'Vazirmatn', sans-serif; margin: 0; padding: 0; }}
        body {{ background: var(--bg); color: var(--text); padding-bottom: 80px; }}
        header {{ background: rgba(30,41,59,0.9); backdrop-filter: blur(10px); padding: 15px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid #334155; display: flex; justify-content: space-between; align-items: center; }}
        h2 {{ font-size: 1.2rem; background: linear-gradient(45deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .stats {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; padding: 15px; max-width: 800px; margin: 0 auto; }}
        .stat-box {{ background: var(--card); padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #334155; }}
        .stat-num {{ display: block; font-size: 1.5rem; font-weight: bold; color: var(--accent); }}
        .stat-label {{ font-size: 0.8rem; color: #94a3b8; }}
        .sub-box {{ background: linear-gradient(135deg, #4f46e5, #ec4899); margin: 15px; padding: 20px; border-radius: 15px; text-align: center; color: white; max-width: 800px; margin: 15px auto; }}
        .sub-btn {{ display: inline-block; background: white; color: #4f46e5; padding: 10px 20px; border-radius: 8px; text-decoration: none; font-weight: bold; margin-top: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); cursor: pointer; }}
        .list {{ display: grid; gap: 15px; padding: 15px; max-width: 800px; margin: 0 auto; }}
        .card {{ background: var(--card); border-radius: 15px; padding: 15px; border: 1px solid #334155; transition: transform 0.2s; }}
        .card:active {{ transform: scale(0.98); }}
        .card-head {{ display: flex; justify-content: space-between; margin-bottom: 10px; align-items: center; }}
        .badge {{ padding: 4px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: bold; }}
        .proto {{ background: #334155; color: #cbd5e1; }}
        .score.high {{ background: rgba(34,197,94,0.2); color: var(--green); }}
        .score.mid {{ background: rgba(234,179,8,0.2); color: var(--yellow); }}
        .score.low {{ background: rgba(239,68,68,0.2); color: var(--red); }}
        .flag {{ font-size: 1.2rem; }}
        .info {{ display: flex; justify-content: space-between; font-size: 0.8rem; color: #94a3b8; margin-bottom: 8px; }}
        .code-box {{ background: #0b1120; padding: 10px; border-radius: 8px; font-family: monospace; color: #a5b4fc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; cursor: pointer; direction: ltr; }}
        .actions {{ display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 8px; margin-top: 12px; }}
        .btn {{ border: none; padding: 10px; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; }}
        .copy {{ background: var(--accent); }}
        .qr {{ background: #6366f1; }}
        .link {{ background: #334155; text-decoration: none; text-align: center; font-size: 0.9rem; display: flex; align-items: center; justify-content: center; }}
        .toast {{ position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); background: var(--green); color: white; padding: 10px 20px; border-radius: 50px; opacity: 0; transition: 0.3s; pointer-events: none; z-index: 200; }}
        .toast.show {{ opacity: 1; bottom: 40px; }}
        .modal {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 300; justify-content: center; align-items: center; }}
        .modal-content {{ background: var(--card); padding: 20px; border-radius: 20px; text-align: center; max-width: 90%; }}
        #qrcode {{ margin: 20px auto; background: white; padding: 10px; border-radius: 10px; }}
        .close-btn {{ background: var(--red); margin-top: 10px; width: 100%; }}
        #installBtn {{ display: none; position: fixed; bottom: 20px; right: 20px; background: var(--accent); color: #0f172a; border: none; padding: 12px 20px; border-radius: 50px; font-weight: bold; box-shadow: 0 4px 15px rgba(56,189,248,0.4); cursor: pointer; z-index: 90; }}
    </style>
</head>
<body>
    <header>
        <h2>💎 VPN Hub Pro</h2>
        <small>{update_time}</small>
    </header>
    
    <div class="stats">
        <div class="stat-box"><span class="stat-num">{total}</span><span class="stat-label">کل کانفیگ</span></div>
        <div class="stat-box"><span class="stat-num">{high_quality}</span><span class="stat-label">کیفیت عالی</span></div>
        <div class="stat-box"><span class="stat-num">{avg_ping}</span><span class="stat-label">پینگ میانگین</span></div>
    </div>
    
    {sub_box_html}
    
    <div class="list">
        {cards_html}
    </div>
    
    <button id="installBtn">📲 نصب اپلیکیشن</button>
    <div id="toast" class="toast">کپی شد!</div>
    
    <div id="qrModal" class="modal">
        <div class="modal-content">
            <h3>اسکن کنید</h3>
            <div id="qrcode"></div>
            <button class="btn close-btn" onclick="document.getElementById('qrModal').style.display='none'">بستن</button>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <script>
        function copyTxt(txt) {{
            navigator.clipboard.writeText(txt).then(() => {{
                const t = document.getElementById('toast');
                t.innerText = 'کپی شد!';
                t.classList.add('show');
                setTimeout(() => t.classList.remove('show'), 2000);
            }});
        }}
        
        function selectText(el) {{
            const range = document.createRange();
            range.selectNodeContents(el);
            const sel = window.getSelection();
            sel.removeAllRanges();
            sel.addRange(range);
        }}
        
        function showQR(txt) {{
            const m = document.getElementById('qrModal');
            const q = document.getElementById('qrcode');
            q.innerHTML = '';
            new QRCode(q, {{text: txt, width: 200, height: 200}});
            m.style.display = 'flex';
        }}
        
        let deferredPrompt;
        window.addEventListener('beforeinstallprompt', (e) => {{
            e.preventDefault();
            deferredPrompt = e;
            const btn = document.getElementById('installBtn');
            btn.style.display = 'block';
            btn.addEventListener('click', () => {{
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choice) => {{
                    if(choice.outcome === 'accepted') btn.style.display = 'none';
                    deferredPrompt = null;
                }});
            }});
        }});
        
        if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
    </script>
</body>
</html>"""

    with open('index.html', 'w', encoding='utf-8') as f: f.write(html_content)
    
    manifest = {
        "name": "VPN Hub Pro",
        "short_name": "VPNHub",
        "start_url": ".",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#38bdf8",
        "icons": [{"src": "https://img.icons8.com/3d-fluency/94/rocket.png", "sizes": "94x94", "type": "image/png"}]
    }
    with open('manifest.json', 'w') as f: json.dump(manifest, f)
    
    with open('sw.js', 'w') as f: f.write("self.addEventListener('install',e=>e.waitUntil(caches.open('v1').then(c=>c.addAll(['./']))));self.addEventListener('fetch',e=>e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request))));")

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
