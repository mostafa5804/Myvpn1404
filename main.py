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
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntityTextUrl
from telethon.errors.rpcerrorlist import FloodWaitError

# -----------------------------------------------------------------------------
# 1. تنظیمات و پیکربندی
# -----------------------------------------------------------------------------
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

# دریافت سشن‌ها
session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
DATA_FILE = 'data.json'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'

ALL_CHANNELS = [
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

allowed_extensions = {'.npv4', '.npv2', '.npvt', '.dark', '.ehi', '.txt', '.conf', '.json'}
iran_tz = pytz.timezone('Asia/Tehran')
IRAN_IP_PREFIXES = ['2.144.', '5.22.', '31.2.', '37.9.', '46.18.', '78.38.', '85.9.', '91.98.', '93.88.', '185.']

# -----------------------------------------------------------------------------
# 2. توابع کمکی
# -----------------------------------------------------------------------------
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
    res.sort(key=lambda x: x.get('ts', 0), reverse=True)
    return res

def get_batch_info():
    minute = datetime.now(iran_tz).minute
    # استراتژی: همیشه اولویت با سشن 2 (سالم) است
    target_session = session_2 if session_2 else session_1
    
    if minute < 30:
        print("👤 نوبت نیمه اول (کانال 1-20)")
        return ALL_CHANNELS[:20], "اول", target_session
    else:
        print("👤 نوبت نیمه دوم (کانال 21-40)")
        return ALL_CHANNELS[20:], "دوم", target_session

def is_iran_ip(ip):
    return any(ip.startswith(p) for p in IRAN_IP_PREFIXES)

def clean_title(t): return re.sub(r'[\[\]\(\)\*`_]', '', str(t)).strip() if t else "Channel"

def get_hashtags(name, type='file'):
    if type == 'config': return f"#{name.split('://')[0].lower()} #v2rayNG"
    ext = name.lower().split('.')[-1]
    return {'npv4': '#napsternetv', 'ehi': '#httpinjector', 'txt': '#v2rayng'}.get(ext, '#vpn')

def create_footer(title, link):
    now = datetime.now(iran_tz)
    return f"\n━━━━━━━━━━━━━━━━\n🗓 {now.strftime('%Y/%m/%d')} • 🕐 {now.strftime('%H:%M')}\n📡 منبع: [{clean_title(title)}]({link})\n🔗 {destination_channel}"

async def check_ping(host, port):
    try:
        st = time.time()
        _, w = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=PING_TIMEOUT)
        w.close()
        return int((time.time() - st) * 1000)
    except: return None

async def check_status(link, type='config'):
    try:
        if type == 'proxy':
            m = re.search(r"server=([\w\.-]+)&port=(\d+)", link)
            host, port = m.group(1), int(m.group(2))
        else:
            if link.startswith('vmess'):
                d = json.loads(base64.b64decode(link.split('://')[1]))
                host, port = d['add'], int(d['port'])
            else:
                m = re.search(r"@([\w\.-]+):(\d+)", link)
                host, port = m.group(1), int(m.group(2))
        
        lat = await check_ping(host, port)
        if lat is None:
            try:
                if is_iran_ip(socket.gethostbyname(host)): return "🔵 اینترانت", None, True
            except: pass
            return "🔴 آفلاین", None, False
        if lat < 100: return "🟢 عالی", lat, False
        if lat < 200: return "🟡 خوب", lat, False
        return "🟠 متوسط", lat, False
    except: return None, None, False

def extract_proxy_key(link):
    m = re.search(r"server=([\w\.-]+)&port=(\d+)", link)
    if m: return f"{m.group(1)}:{m.group(2)}"
    return str(time.time())

# -----------------------------------------------------------------------------
# 3. تولید کننده HTML
# -----------------------------------------------------------------------------
def generate_html_parts(configs, proxies, files):
    # کانفیگ
    c_html = ""
    for i, c in enumerate(configs):
        ping_color = '#10b981' if c['latency'] < 200 else '#f59e0b'
        c_html += f'''
        <div class="card search-item" data-filter="{c['protocol']} {c['channel']}">
            <div class="card-header">
                <span class="badge badge-proto">{c['protocol']}</span>
                <span class="badge badge-ping" style="color:{ping_color}"><i class="fas fa-bolt"></i> {c['latency']}ms</span>
            </div>
            <div class="meta-info"><i class="fas fa-broadcast-tower"></i> {c['channel']}</div>
            <div class="code-block" onclick="copyText('c{i}', this)">{c['config']}</div>
            <div class="actions">
                <button class="btn btn-copy" onclick="copyText('c{i}', this)"><i class="far fa-copy"></i> کپی</button>
                <a href="{c['t_link']}" class="btn btn-link"><i class="fab fa-telegram-plane"></i> تلگرام</a>
                <button class="btn btn-link btn-qr" onclick="showQRFrom('c{i}')"><i class="fas fa-qrcode"></i></button>
            </div>
            <div id="c{i}" style="display:none">{c['config']}</div>
        </div>'''
    if not configs: c_html = '<div class="empty"><i class="fas fa-box-open"></i><p>لیست خالی است</p></div>'

    # پروکسی
    p_html = ""
    for v in proxies:
        p_html += f'''
        <div class="card search-item" data-filter="proxy mtproto {v['channel']}">
            <div class="card-header">
                <span class="badge badge-proto">MTProto</span>
                <span class="badge badge-ping" style="color:#f59e0b">Proxy</span>
            </div>
            <div class="meta-info"><i class="fas fa-broadcast-tower"></i> {v['channel']}</div>
            <div class="actions" style="grid-template-columns: 1fr;">
                <a href="{v['link']}" class="btn btn-copy"><i class="fas fa-power-off"></i> اتصال سریع</a>
            </div>
        </div>'''
    if not proxies: p_html = '<div class="empty"><i class="fas fa-shield-virus"></i><p>پروکسی موجود نیست</p></div>'

    # فایل
    f_html = ""
    for v in files:
        f_html += f'''
        <div class="card search-item" data-filter="{v['ext']} {v['name']} {v['channel']}">
            <div class="card-header">
                <span class="badge badge-proto">{v['ext'].upper()}</span>
                <span class="badge badge-ping">FILE</span>
            </div>
            <div style="font-weight:bold;margin-bottom:5px;text-align:right;direction:ltr">{v['name']}</div>
            <div class="meta-info"><i class="fas fa-broadcast-tower"></i> {v['channel']}</div>
            <div class="actions" style="grid-template-columns: 1fr;">
                <a href="{v['link']}" class="btn btn-link" style="border-color:#38bdf8;color:#38bdf8"><i class="fas fa-download"></i> دانلود</a>
            </div>
        </div>'''
    if not files: f_html = '<div class="empty"><i class="fas fa-folder-open"></i><p>فایلی موجود نیست</p></div>'
    
    return c_html, p_html, f_html

# -----------------------------------------------------------------------------
# 4. بدنه اصلی
# -----------------------------------------------------------------------------
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
        
        await asyncio.sleep(random.randint(5, 10))
        
        new_conf, new_prox, new_file = [], [], []
        sent_hashes = set()

        for i, channel_str in enumerate(target_channels):
            try:
                wait_time = random.randint(15, 20)
                print(f"⏳ ({i+1}/{len(target_channels)}) {channel_str} - صبر: {wait_time}s")
                await asyncio.sleep(wait_time)
                
                try:
                    entity = await client.get_entity(channel_str)
                except FloodWaitError as e:
                    print(f"❌ لیمیت تلگرام: {e.seconds}s")
                    continue
                except:
                    print("⚠️ کانال یافت نشد")
                    continue

                msgs = await client.get_messages(entity, limit=30)
                temp_c, temp_p, temp_f = [], [], []
                title = getattr(entity, 'title', channel_str)
                
                for m in msgs:
                    link = f"[https://t.me/](https://t.me/){channel_str[1:]}/{m.id}"
                    if m.text:
                        for c in re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text):
                            if c not in sent_hashes:
                                temp_c.append({'c': c, 'link': link})
                                sent_hashes.add(c)
                        for p in re.findall(r"[https://t.me/proxy](https://t.me/proxy)\?[^\s\n]+", m.text):
                            temp_p.append({'p': p.replace('https', 'tg'), 'link': link})
                    if m.file and any(m.file.name.endswith(x) for x in allowed_extensions if m.file.name):
                        temp_f.append({'n': m.file.name, 'm': m, 'link': link})

                # ارسال کانفیگ با فرمت کد بلاک (درست شد)
                for item in temp_c:
                    stat, lat, _ = await check_status(item['c'])
                    if stat:
                        prot = item['c'].split('://')[0].upper()
                        # اینجا تغییر دادم: استفاده از ``` برای کپی راحت
                        txt = f"🔮 **{prot}**\n\n```\n{item['c']}\n```\n📊 {stat} • {lat}ms\n{get_hashtags(item['c'], 'config')}{create_footer(title, item['link'])}"
                        try:
                            sent = await client.send_message(destination_channel, txt, link_preview=False)
                            my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                            new_conf.append({'protocol': prot, 'config': item['c'], 'latency': lat, 'channel': title, 't_link': my_link, 'ts': time.time()})
                            await asyncio.sleep(3)
                        except Exception as e:
                            print(f"ارسال ناموفق: {e}")

                # ارسال پروکسی با لینک قابل کلیک (درست شد)
                valid_proxies = []
                for item in temp_p:
                    stat, lat, _ = await check_status(item['p'], 'proxy')
                    if stat:
                        ping = f"{lat}ms" if lat else ""
                        valid_proxies.append({'l': item['p'], 's': stat, 'pi': ping, 'src': item['link']})
                        k = extract_proxy_key(item['p'])
                        new_prox.append({'key': k, 'link': item['p'], 'channel': title, 't_link': '#', 'ts': time.time()})
                
                if valid_proxies:
                    body = "🔵 **پروکسی‌های جدید**\n\n"
                    for idx, p in enumerate(valid_proxies, 1):
                        # فرمت لینک دار: [اتصال](لینک)
                        body += f"{idx}. [اتصال]({p['l']}) • {p['s']} {p['pi']}\n"
                    body += "\n💡 برای اتصال روی لینک کلیک کنید" + create_footer(title, valid_proxies[0]['src'])
                    try:
                        sent = await client.send_message(destination_channel, body, link_preview=False)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                        for p in new_prox: 
                            if p['channel'] == title: p['t_link'] = my_link
                        await asyncio.sleep(3)
                    except Exception as e:
                         print(f"ارسال ناموفق پروکسی: {e}")

                # فایل (تغییری نکرد چون اوکی بود)
                for item in temp_f:
                    cap = f"📂 **{item['n']}**\n\n{get_hashtags(item['n'])}{create_footer(title, item['link'])}"
                    try:
                        sent = await client.send_file(destination_channel, item['m'], caption=cap)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                        new_file.append({'name': item['n'], 'ext': item['n'].split('.')[-1], 'channel': title, 'link': my_link, 'ts': time.time()})
                        await asyncio.sleep(3)
                    except Exception as e:
                         print(f"ارسال ناموفق فایل: {e}")

            except Exception as e: 
                print(f"Err {channel_str}: {e}")
                continue

        print("💾 ذخیره دیتابیس...")
        f_c = merge_data(hist['configs'], new_conf, 'config')
        f_p = merge_data(hist['proxies'], new_prox, 'key')
        f_f = merge_data(hist['files'], new_file, 'name')
        save_data({'configs': f_c, 'proxies': f_p, 'files': f_f})

        print(f"📊 آمار نهایی: {len(f_c)} کانفیگ، {len(f_p)} پروکسی")

        # ساخت HTML (بعد از پر شدن لیست‌ها)
        html_c, html_p, html_f = generate_html_parts(f_c, f_p, f_f)
        now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
        
        full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN Hub | {destination_channel}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --primary: #38bdf8; --text: #f1f5f9; --sub: #94a3b8; --border: #334155; }}
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        body {{ background:var(--bg); color:var(--text); padding-bottom:90px; }}
        header {{ background:rgba(30,41,59,0.95); padding:20px; position:sticky; top:0; z-index:50; border-bottom:1px solid var(--border); text-align:center; backdrop-filter:blur(10px); }}
        .container {{ max-width:600px; margin:20px auto; padding:0 15px; }}
        .card {{ background:var(--card); border-radius:16px; padding:16px; margin-bottom:16px; border:1px solid var(--border); animation:fadeIn 0.5s; }}
        @keyframes fadeIn {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .badge {{ background:rgba(56,189,248,0.1); color:var(--primary); padding:4px 8px; border-radius:6px; font-size:0.75rem; font-weight:bold; }}
        .code-block {{ background:#0b1120; padding:12px; border-radius:10px; color:#a5b4fc; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; margin:12px 0; direction:ltr; cursor:pointer; font-family:monospace; }}
        .actions {{ display:grid; grid-template-columns:1fr 1fr auto; gap:10px; }}
        .btn {{ padding:10px; border-radius:10px; border:none; cursor:pointer; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:5px; text-decoration:none; }}
        .btn-copy {{ background:var(--primary); color:#0f172a; }}
        .btn-link {{ border:1px solid var(--border); color:var(--text); background:transparent; }}
        .nav {{ position:fixed; bottom:0; left:0; right:0; background:rgba(30,41,59,0.95); display:flex; padding:10px; border-top:1px solid var(--border); z-index:99; backdrop-filter:blur(10px); }}
        .nav-item {{ flex:1; text-align:center; color:var(--sub); cursor:pointer; font-size:0.75rem; }}
        .nav-item.active {{ color:var(--primary); }}
        .nav-item i {{ display:block; font-size:1.4rem; margin-bottom:4px; }}
        .tab {{ display:none; }} .tab.active {{ display:block; }}
        .empty {{ text-align:center; padding:40px; color:var(--sub); }}
        .empty i {{ font-size:3rem; margin-bottom:15px; opacity:0.3; }}
        #qrModal {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:2000; align-items:center; justify-content:center; }}
        .modal-content {{ background:var(--card); padding:20px; border-radius:20px; width:300px; text-align:center; }}
    </style>
</head>
<body>
    <header>
        <h2>VPN Hub</h2>
        <p style="font-size:0.8rem;color:var(--sub)">بروزرسانی: <span dir="ltr">{now_str}</span></p>
    </header>

    <div class="container">
        <div id="t1" class="tab active">{html_c}</div>
        <div id="t2" class="tab">{html_p}</div>
        <div id="t3" class="tab">{html_f}</div>
    </div>

    <nav class="nav">
        <div class="nav-item active" onclick="sw('t1',this)"><i class="fas fa-rocket"></i>کانفیگ</div>
        <div class="nav-item" onclick="sw('t2',this)"><i class="fas fa-shield-alt"></i>پروکسی</div>
        <div class="nav-item" onclick="sw('t3',this)"><i class="fas fa-folder"></i>فایل</div>
    </nav>

    <div id="qrModal" onclick="this.style.display='none'">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3 style="margin-bottom:15px">اسکن کنید</h3>
            <img id="qrImg" src="" style="width:100%;border-radius:10px">
        </div>
    </div>

    <script>
        function sw(id, el) {{
            document.querySelectorAll('.tab').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            el.classList.add('active');
            window.scrollTo(0, 0);
        }}
        function copyText(id, btn) {{
            navigator.clipboard.writeText(document.getElementById(id).innerText).then(() => {{
                btn.innerHTML = '<i class="fas fa-check"></i> کپی شد';
                setTimeout(() => btn.innerHTML = '<i class="far fa-copy"></i> کپی', 1500);
            }});
        }}
        function showQRFrom(id) {{
            const txt = document.getElementById(id).innerText;
            document.getElementById('qrImg').src = 'https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=' + encodeURIComponent(txt);
            document.getElementById('qrModal').style.display = 'flex';
        }}
    </script>
</body>
</html>"""
        
        with open('index.html', 'w', encoding='utf-8') as f: f.write(full_html)
        print("✅ پایان موفقیت‌آمیز")

    except Exception as e: print(f"CRITICAL: {e}")
    finally: await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
