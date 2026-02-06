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

try:
    import geoip2.database
    GEOIP_AVAILABLE = True
except:
    GEOIP_AVAILABLE = False
    print("⚠️ GeoIP غیرفعال (فایل mmdb موجود نیست)")

# =============================================================================
# 1. تنظیمات و پیکربندی
# =============================================================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']
session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

ENABLE_REAL_TEST = True
REAL_TEST_TIMEOUT = 5
REAL_TEST_URL = "https://www.gstatic.com/generate_204"

DATA_FILE = 'data.json'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
# آدرس گیت‌هاب پیج شما برای لینک اشتراک
GITHUB_PAGE_URL = "mostafa5804.github.io/Myvpn1404" 
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

# GeoIP Reader
geoip_reader = None
if GEOIP_AVAILABLE and os.path.exists('GeoLite2-Country.mmdb'):
    try:
        geoip_reader = geoip2.database.Reader('GeoLite2-Country.mmdb')
        print("✅ GeoIP فعال شد")
    except: pass

# =============================================================================
# 2. توابع کمکی
# =============================================================================

def generate_config_hash(config_str):
    try:
        if config_str.startswith('vmess://'):
            decoded = json.loads(base64.b64decode(config_str.split('://')[1]))
            key = f"{decoded.get('add')}:{decoded.get('port')}:{decoded.get('id', '')[:8]}"
        elif config_str.startswith('vless://') or config_str.startswith('trojan://'):
            match = re.search(r'@([\w\.-]+):(\d+)', config_str)
            uuid_match = re.search(r'://([\w-]+)@', config_str)
            if match and uuid_match:
                key = f"{match.group(1)}:{match.group(2)}:{uuid_match.group(1)[:8]}"
            else:
                key = config_str[:50]
        else:
            key = config_str[:50]
        return hashlib.md5(key.encode()).hexdigest()[:12]
    except:
        return hashlib.md5(config_str.encode()).hexdigest()[:12]

def calculate_quality_score(latency, success_rate=100, protocol='vmess'):
    if not latency or latency > 500: return 0
    if latency < 50: ping_score = 100
    elif latency < 100: ping_score = 90
    elif latency < 150: ping_score = 75
    elif latency < 200: ping_score = 60
    else: ping_score = max(0, 60 - (latency - 200) / 10)
    protocol_bonus = {'vless': 10, 'reality': 15, 'trojan': 5}.get(protocol.lower(), 0)
    return int(min(100, ping_score + protocol_bonus))

def get_country_flag(ip_address):
    if not geoip_reader: return "🌐"
    try:
        response = geoip_reader.country(ip_address)
        country_code = response.country.iso_code
        if country_code: return ''.join(chr(127397 + ord(c)) for c in country_code.upper())
        return "🌐"
    except: return "🌐"

async def real_connection_test(host, port, protocol='tcp'):
    try:
        start = time.time()
        if protocol in ['http', 'https']:
            async with aiohttp.ClientSession() as session:
                async with session.get(REAL_TEST_URL, timeout=aiohttp.ClientTimeout(total=REAL_TEST_TIMEOUT)) as resp:
                    await resp.read()
                    return int((time.time() - start) * 1000), True
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=REAL_TEST_TIMEOUT)
        writer.close()
        await writer.wait_closed()
        return int((time.time() - start) * 1000), True
    except: return None, False

def extract_server_info(config_str):
    try:
        if config_str.startswith('vmess://'):
            decoded = json.loads(base64.b64decode(config_str.split('://')[1]))
            return decoded.get('add'), int(decoded.get('port', 443))
        elif config_str.startswith(('vless://', 'trojan://', 'ss://')):
            match = re.search(r'@([\w\.-]+):(\d+)', config_str)
            if match: return match.group(1), int(match.group(2))
        return None, None
    except: return None, None

async def check_status_advanced(link, type='config'):
    try:
        host, port = extract_server_info(link)
        if not host or not port: return None, None, None, False, "🌐"
        
        if ENABLE_REAL_TEST:
            latency, success = await real_connection_test(host, port)
        else:
            try:
                start = time.time()
                _, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=2)
                w.close()
                latency = int((time.time() - start) * 1000)
                success = True
            except: latency, success = None, False
        
        flag = get_country_flag(host)
        if not success or latency is None: return "🔴 آفلاین", None, 0, False, flag
        
        protocol = link.split('://')[0]
        quality = calculate_quality_score(latency, 100, protocol)
        status = "🟢 عالی" if latency < 100 else "🟡 خوب" if latency < 200 else "🟠 متوسط"
        return status, latency, quality, True, flag
    except: return None, None, 0, False, "🌐"

def generate_subscription_link(configs, domain):
    """تولید فایل و لینک اشتراک"""
    if not configs: return None
    valid_configs = [c['config'] for c in configs if c.get('quality', 0) > 40]
    if not valid_configs: return None
    
    encoded = base64.b64encode('\n'.join(valid_configs).encode()).decode()
    
    # 🔴 اصلاح مسیر: ذخیره در مسیر جاری
    with open('subscription.txt', 'w', encoding='utf-8') as f:
        f.write(encoded)
    
    return f"https://{domain}/subscription.txt"

def load_data():
    if not os.path.exists(DATA_FILE): return {'configs': [], 'proxies': [], 'files': []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: data = json.load(f)
        limit = time.time() - (KEEP_HISTORY_HOURS * 3600)
        return {
            'configs': [c for c in data.get('configs', []) if c.get('ts', 0) > limit],
            'proxies': [p for p in data.get('proxies', []) if p.get('ts', 0) > limit],
            'files': [f for f in data.get('files', []) if f.get('ts', 0) > limit]
        }
    except: return {'configs': [], 'proxies': [], 'files': []}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def merge_data(history, new_items, key):
    exist = {i[key]: i for i in history}
    for i in new_items: exist[i[key]] = i
    res = list(exist.values())
    res.sort(key=lambda x: x.get('quality', 0), reverse=True)
    return res

def get_batch_info():
    minute = datetime.now(iran_tz).minute
    target_session = session_2 if session_2 else session_1
    if minute < 30: return ALL_CHANNELS[:20], "اول", target_session
    else: return ALL_CHANNELS[20:], "دوم", target_session

def clean_title(t):
    if not t: return "Channel"
    return re.sub(r'[\[\]\(\)\*`_]', '', str(t)).strip()

def get_hashtags(name, type='file'):
    if type == 'config': return f"#{name.split('://')[0].lower()} #v2rayNG"
    ext = name.lower().split('.')[-1]
    return {'npv4': '#napsternetv', 'ehi': '#httpinjector', 'txt': '#v2rayng'}.get(ext, '#vpn')

def create_footer(title, link):
    now = datetime.now(iran_tz)
    safe_title = clean_title(title)
    return f"\n━━━━━━━━━━━━━━━━\n🗓 {now.strftime('%Y/%m/%d')} • 🕐 {now.strftime('%H:%M')}\n📡 منبع: [{safe_title}]({link})\n🔗 {destination_channel}"

def extract_proxy_key(link):
    m = re.search(r"server=([\w\.-]+)&port=(\d+)", link)
    if m: return f"{m.group(1)}:{m.group(2)}"
    return str(time.time())

# =============================================================================
# 3. بدنه اصلی
# =============================================================================
target_channels, batch_name, active_session = get_batch_info()

if not active_session:
    print("❌ خطای حیاتی: سشن یافت نشد!")
    sys.exit(1)

client = TelegramClient(StringSession(active_session), api_id, api_hash)

async def main():
    try:
        await client.start()
        print(f"✅ ربات متصل شد ({batch_name})")
        
        hist = load_data()
        sent_hashes = set()
        for c in hist['configs']: sent_hashes.add(generate_config_hash(c['config']))
        
        print(f"🔄 {len(sent_hashes)} کانفیگ یکتا در حافظه")
        await asyncio.sleep(random.randint(5, 10))
        
        new_conf, new_prox, new_file = [], [], []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)

        for i, channel_str in enumerate(target_channels):
            try:
                wait_time = random.randint(15, 20)
                print(f"⏳ ({i+1}/{len(target_channels)}) {channel_str} - صبر: {wait_time}s")
                await asyncio.sleep(wait_time)
                
                try: entity = await client.get_entity(channel_str)
                except: continue

                msgs = await client.get_messages(entity, limit=20)
                temp_c = []
                title = getattr(entity, 'title', channel_str)
                
                for m in msgs:
                    if m.date < cutoff_time: continue
                    link = f"https://t.me/{channel_str[1:]}/{m.id}"
                    
                    if m.text:
                        for c in re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text):
                            config_hash = generate_config_hash(c)
                            if config_hash not in sent_hashes:
                                temp_c.append({'c': c, 'link': link, 'hash': config_hash})
                                sent_hashes.add(config_hash)

                for item in temp_c:
                    stat, lat, quality, is_online, flag = await check_status_advanced(item['c'])
                    
                    if stat and is_online:
                        prot = item['c'].split('://')[0].upper()
                        txt = (f"🔮 **{prot}** {flag}\n\n```\n{item['c']}\n```\n"
                               f"📊 {stat} • {lat}ms • کیفیت: {quality}/100\n"
                               f"{get_hashtags(item['c'], 'config')}{create_footer(title, item['link'])}")
                        try:
                            sent = await client.send_message(destination_channel, txt, link_preview=False)
                            my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                            new_conf.append({
                                'protocol': prot, 'config': item['c'], 'hash': item['hash'],
                                'latency': lat, 'quality': quality, 'country': flag,
                                'channel': title, 't_link': my_link, 'ts': time.time()
                            })
                            await asyncio.sleep(3)
                        except: pass

            except Exception as e:
                print(f"Err {channel_str}: {e}")
                continue

        print("💾 ذخیره دیتابیس...")
        f_c = merge_data(hist['configs'], new_conf, 'hash')
        save_data({'configs': f_c, 'proxies': [], 'files': []})
        
        # تولید لینک اشتراک با دامنه صحیح
        sub_link = generate_subscription_link(f_c, GITHUB_PAGE_URL)
        
        print("\n📄 ساخت صفحه Premium PWA...")
        await generate_advanced_website(f_c, sub_link)

    except Exception as e:
        print(f"❌ خطا: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

async def generate_advanced_website(configs, subscription_link):
    now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
    total = len(configs)
    excellent = len([c for c in configs if c.get('quality', 0) > 80])
    avg_ping = int(sum([c.get('latency', 999) for c in configs if c.get('latency')]) / total) if total > 0 else 0
    
    html_configs = ""
    for idx, cfg in enumerate(configs[:50], 1):
        quality = cfg.get('quality', 0)
        badge_class = "excellent" if quality > 80 else "good" if quality > 60 else "medium"
        safe_config = cfg['config'].replace("'", "\\'").replace('"', '\\"')
        
        html_configs += f"""
        <div class="card" data-quality="{quality}">
            <div class="card-header">
                <span class="protocol-badge">{cfg['protocol']}</span>
                <span class="country-flag">{cfg.get('country', '🌐')}</span>
                <span class="quality-badge {badge_class}">{quality}/100</span>
            </div>
            <div class="card-body">
                <div class="source">📡 {cfg['channel']}</div>
                <div class="stats"><span>📶 {cfg.get('latency', 'N/A')}ms</span></div>
                <div class="code-block" onclick="selectCode(this)">{cfg['config'][:60]}...</div>
            </div>
            <div class="actions">
                <button class="btn btn-copy" onclick='copyConfig("{safe_config}")'><i class="far fa-copy"></i> کپی</button>
                <button class="btn btn-qr" onclick='showQR("{safe_config}")'><i class="fas fa-qrcode"></i></button>
                <a href="{cfg.get('t_link', '#')}" class="btn btn-link" target="_blank"><i class="fab fa-telegram"></i></a>
            </div>
        </div>"""
    
    full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0f172a">
    <link rel="manifest" href="manifest.json">
    <title>VPN Hub Pro | {destination_channel}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg:#0f172a; --card:#1e293b; --primary:#38bdf8; --success:#10b981; --warning:#f59e0b; --danger:#ef4444; --text:#f1f5f9; --sub:#94a3b8; --border:#334155; }}
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        body {{ background:var(--bg); color:var(--text); padding-bottom:80px; }}
        header {{ background:rgba(30,41,59,0.95); padding:15px; position:sticky; top:0; z-index:50; backdrop-filter:blur(10px); border-bottom:1px solid var(--border); }}
        .header-content {{ max-width:600px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; }}
        .stats-bar {{ background:var(--card); padding:20px; margin:15px auto; max-width:600px; border-radius:15px; display:grid; grid-template-columns:repeat(3,1fr); gap:15px; }}
        .stat-item {{ text-align:center; }} .stat-value {{ font-size:1.8rem; font-weight:bold; color:var(--primary); }} .stat-label {{ font-size:0.75rem; color:var(--sub); margin-top:5px; }}
        .subscription-box {{ max-width:600px; margin:15px auto; padding:20px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius:15px; text-align:center; }}
        .sub-link {{ background:white; color:#667eea; padding:12px 25px; border-radius:10px; text-decoration:none; display:inline-block; font-weight:bold; margin-top:10px; }}
        .container {{ max-width:600px; margin:0 auto; padding:0 15px; }}
        .card {{ background:var(--card); border-radius:16px; padding:16px; margin-bottom:16px; border:1px solid var(--border); animation:slideIn 0.5s; }}
        @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
        .protocol-badge {{ padding:6px 12px; border-radius:8px; background:linear-gradient(135deg,#38bdf8,#3b82f6); color:white; font-size:0.75rem; font-weight:bold; }}
        .quality-badge {{ padding:6px 12px; border-radius:8px; font-size:0.75rem; font-weight:bold; }}
        .excellent {{ background:rgba(16,185,129,0.2); color:var(--success); }} .good {{ background:rgba(245,158,11,0.2); color:var(--warning); }} .medium {{ background:rgba(239,68,68,0.2); color:var(--danger); }}
        .source {{ font-size:0.8rem; color:var(--sub); margin-bottom:8px; }}
        .code-block {{ background:#0b1120; padding:12px; border-radius:10px; color:#a5b4fc; font-family:monospace; cursor:pointer; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
        .actions {{ display:grid; grid-template-columns:2fr 1fr 1fr; gap:8px; margin-top:12px; }}
        .btn {{ padding:10px; border-radius:10px; border:none; cursor:pointer; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:5px; text-decoration:none; transition:all 0.3s; }}
        .btn-copy {{ background:var(--primary); color:var(--bg); }} .btn-qr {{ background:#a78bfa; color:white; }} .btn-link {{ background:transparent; border:1px solid var(--border); color:var(--text); }}
        #toast {{ position:fixed; bottom:100px; left:50%; transform:translateX(-50%); background:var(--success); color:white; padding:15px 25px; border-radius:10px; font-weight:bold; z-index:1000; opacity:0; transition:opacity 0.3s; }}
        #toast.show {{ opacity:1; }}
        #installBtn {{ position:fixed; bottom:90px; right:20px; background:var(--primary); color:white; padding:15px 20px; border-radius:50px; border:none; cursor:pointer; box-shadow:0 4px 15px rgba(56,189,248,0.4); display:none; z-index:100; }}
    </style>
</head>
<body>
    <header><div class="header-content"><div><h2>🚀 VPN Hub Pro</h2><small>بروزرسانی: {now_str}</small></div><button class="btn" onclick="location.reload()"><i class="fas fa-sync-alt"></i></button></div></header>
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-value">{total}</div><div class="stat-label">کانفیگ آنلاین</div></div>
        <div class="stat-item"><div class="stat-value">{avg_ping}ms</div><div class="stat-label">میانگین تاخیر</div></div>
        <div class="stat-item"><div class="stat-value">{excellent}</div><div class="stat-label">کیفیت عالی</div></div>
    </div>
    {f'<div class="subscription-box"><h3>🔗 لینک اشتراک (Subscription)</h3><p style="color:rgba(255,255,255,0.9);font-size:0.85rem;">لینک زیر را در برنامه V2Ray/Clash کپی کنید:</p><a href="{subscription_link}" class="sub-link" onclick="copyText(\\'{subscription_link}\\')"><i class="fas fa-download"></i> کپی لینک اشتراک</a></div>' if subscription_link else ''}
    <div class="container">{html_configs}</div>
    <button id="installBtn" onclick="installPWA()"><i class="fas fa-download"></i> نصب اپلیکیشن</button>
    <div id="toast"></div>
    <script>
        function copyConfig(text) {{ navigator.clipboard.writeText(text).then(() => showToast('✅ کانفیگ کپی شد!')); }}
        function copyText(text) {{ navigator.clipboard.writeText(text); showToast('✅ لینک کپی شد!'); return false; }}
        function showToast(msg) {{ const t = document.getElementById('toast'); t.innerText = msg; t.classList.add('show'); setTimeout(() => t.classList.remove('show'), 3000); }}
        function selectCode(el) {{ const r = document.createRange(); r.selectNodeContents(el); const s = window.getSelection(); s.removeAllRanges(); s.addRange(r); }}
        let deferredPrompt; window.addEventListener('beforeinstallprompt', (e) => {{ e.preventDefault(); deferredPrompt = e; document.getElementById('installBtn').style.display = 'block'; }});
        function installPWA() {{ if(deferredPrompt) {{ deferredPrompt.prompt(); deferredPrompt = null; document.getElementById('installBtn').style.display = 'none'; }} }}
        if ('serviceWorker' in navigator) {{ navigator.serviceWorker.register('sw.js'); }}
    </script>
</body>
</html>"""
    
    # 🔴 اصلاح مسیرها: ذخیره در مسیر جاری
    with open('index.html', 'w', encoding='utf-8') as f: f.write(full_html)
    
    manifest = {
        "name": "VPN Hub Pro", "short_name": "VPNHub", "description": "VPN Configs",
        "start_url": "/", "display": "standalone", "background_color": "#0f172a", "theme_color": "#38bdf8",
        "icons": [{"src": "https://cdn-icons-png.flaticon.com/512/2099/2099192.png", "sizes": "512x512", "type": "image/png"}]
    }
    with open('manifest.json', 'w') as f: json.dump(manifest, f)
    
    sw_content = "self.addEventListener('install',e=>{e.waitUntil(caches.open('v1').then(c=>c.addAll(['/'])))})"
    with open('sw.js', 'w') as f: f.write(sw_content)
    
    print("✅ سایت PWA ساخته شد!")

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
