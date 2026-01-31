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

# =============================================================================
# 1. تنظیمات و پیکربندی
# =============================================================================
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

# دریافت سشن‌ها (اولویت با سشن 2 اگر سشن 1 بن شده باشد)
session_1 = os.environ.get('SESSION_STRING')
session_2 = os.environ.get('SESSION_STRING_2')

ENABLE_PING_CHECK = True
PING_TIMEOUT = 2
DATA_FILE = 'data.json'
KEEP_HISTORY_HOURS = 24
destination_channel = '@myvpn1404'
MAX_MESSAGE_AGE_MINUTES = 90  # فقط پیام‌های 90 دقیقه اخیر

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

# =============================================================================
# 2. توابع کمکی دیتابیس و شبکه
# =============================================================================
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
    """تعیین نوبت کانال‌ها و انتخاب سشن سالم"""
    minute = datetime.now(iran_tz).minute
    
    # استراتژی: همیشه اولویت با سشن 2 است (چون سشن 1 احتمالا لیمیت است)
    # اگر سشن 2 ست نشده باشد، مجبوریم از سشن 1 استفاده کنیم
    target_session = session_2 if session_2 else session_1
    
    if minute < 30:
        print(f"👤 نوبت نیمه اول (کانال 1-20) - استفاده از سشن {'دوم' if target_session == session_2 else 'اول'}")
        return ALL_CHANNELS[:20], "اول", target_session
    else:
        print(f"👤 نوبت نیمه دوم (کانال 21-40) - استفاده از سشن {'دوم' if target_session == session_2 else 'اول'}")
        return ALL_CHANNELS[20:], "دوم", target_session

def is_iran_ip(ip):
    return any(ip.startswith(p) for p in IRAN_IP_PREFIXES)

def clean_title(t):
    # حذف تمام کاراکترهای خراب‌کننده مارک‌داون
    if not t: return "Channel"
    # حذف براکت، پرانتز، ستاره، بک‌تیک و آندرلاین از اسم کانال
    return re.sub(r'[\[\]\(\)\*`_]', '', str(t)).strip()
    
def get_hashtags(name, type='file'):
    if type == 'config': return f"#{name.split('://')[0].lower()} #v2rayNG"
    ext = name.lower().split('.')[-1]
    return {'npv4': '#napsternetv', 'ehi': '#httpinjector', 'txt': '#v2rayng'}.get(ext, '#vpn')

def create_footer(title, link):
    now = datetime.now(iran_tz)
    safe_title = clean_title(title)
    # اصلاح فرمت: افزودن کاراکتر کنترل جهت متن برای جلوگیری از بهم‌ریختگی لینک
    return f"\n━━━━━━━━━━━━━━━━\n🗓 {now.strftime('%Y/%m/%d')} • 🕐 {now.strftime('%H:%M')}\n📡 منبع: [{safe_title}]({link})\n🔗 {destination_channel}"
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

# =============================================================================
# 3. تولید کننده HTML (سایت)
# =============================================================================
def generate_html_parts(configs, proxies, files):
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

# =============================================================================
# 4. بدنه اصلی (Main Loop)
# =============================================================================
target_channels, batch_name, active_session = get_batch_info()

if not active_session:
    print("❌ خطای حیاتی: سشن یافت نشد! لطفا Secrets را چک کنید.")
    sys.exit(1)

client = TelegramClient(StringSession(active_session), api_id, api_hash)

async def main():
    try:
        await client.start()
        print(f"✅ ربات متصل شد ({batch_name})")
        
        # لود دیتابیس برای جلوگیری از تکرار
        hist = load_data()
        
        # ساخت لیست هش‌ها برای چک کردن تکراری‌ها
        sent_hashes = set()
        for c in hist['configs']: sent_hashes.add(c['config'])
        for p in hist['proxies']: sent_hashes.add(p['link'])
        for f in hist['files']: sent_hashes.add(f['name'])
        
        print(f"🔄 {len(sent_hashes)} آیتم در حافظه برای جلوگیری از تکرار.")
        
        await asyncio.sleep(random.randint(5, 10))
        
        new_conf, new_prox, new_file = [], [], []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)

        for i, channel_str in enumerate(target_channels):
            try:
                wait_time = random.randint(15, 20)
                print(f"⏳ ({i+1}/{len(target_channels)}) {channel_str} - صبر: {wait_time}s")
                await asyncio.sleep(wait_time)
                
                try:
                    entity = await client.get_entity(channel_str)
                except FloodWaitError as e:
                    print(f"❌ لیمیت تلگرام برای {channel_str}: {e.seconds} ثانیه. عبور.")
                    continue
                except:
                    print("⚠️ کانال در دسترس نیست.")
                    continue

                msgs = await client.get_messages(entity, limit=20)
                temp_c, temp_p, temp_f = [], [], []
                title = getattr(entity, 'title', channel_str)
                
                for m in msgs:
                    # نادیده گرفتن پیام‌های قدیمی
                    if m.date < cutoff_time: continue

                    link = f"[https://t.me/](https://t.me/){channel_str[1:]}/{m.id}"
                    
                    # استخراج کانفیگ
                    if m.text:
                        for c in re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text):
                            if c not in sent_hashes:
                                temp_c.append({'c': c, 'link': link})
                                sent_hashes.add(c)
                        
                        # استخراج پروکسی
                        for p in re.findall(r"[https://t.me/proxy](https://t.me/proxy)\?[^\s\n]+", m.text):
                            clean_p = p.replace('https', 'tg')
                            if clean_p not in sent_hashes:
                                temp_p.append({'p': clean_p, 'link': link})
                                sent_hashes.add(clean_p)

                    # استخراج فایل
                    if m.file and any(m.file.name.endswith(x) for x in allowed_extensions if m.file.name):
                        if m.file.name not in sent_hashes:
                            temp_f.append({'n': m.file.name, 'm': m, 'link': link})
                            sent_hashes.add(m.file.name)

                # ارسال کانفیگ (Code Block Style)
                for item in temp_c:
                    stat, lat, _ = await check_status(item['c'])
                    if stat:
                        prot = item['c'].split('://')[0].upper()
                        # این فرمت باعث کپی شدن کد می‌شود
                        txt = f"🔮 **{prot}**\n\n```\n{item['c']}\n```\n📊 {stat} • {lat}ms\n{get_hashtags(item['c'], 'config')}{create_footer(title, item['link'])}"
                        try:
                            sent = await client.send_message(destination_channel, txt, link_preview=False)
                            my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent.id}"
                            new_conf.append({'protocol': prot, 'config': item['c'], 'latency': lat, 'channel': title, 't_link': my_link, 'ts': time.time()})
                            await asyncio.sleep(3)
                        except Exception as e: print(f"ارسال ناموفق: {e}")

                # ارسال پروکسی (Link Style)
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
                        body += f"{idx}. [اتصال]({p['l']}) • {p['s']} {p['pi']}\n"
                    body += "\n💡 برای اتصال روی لینک کلیک کنید" + create_footer(title, valid_proxies[0]['src'])
                    try:
                        sent = await client.send_message(destination_channel, body, link_preview=False)
                        my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent.id}"
                        for p in new_prox: 
                            if p['channel'] == title: p['t_link'] = my_link
                        await asyncio.sleep(3)
                    except: pass

                # ارسال فایل
                for item in temp_f:
                    cap = f"📂 **{item['n']}**\n\n{get_hashtags(item['n'])}{create_footer(title, item['link'])}"
                    try:
                        sent = await client.send_file(destination_channel, item['m'], caption=cap)
                        my_link = f"[https://t.me/](https://t.me/){destination_channel[1:]}/{sent.id}"
                        new_file.append({'name': item['n'], 'ext': item['n'].split('.')[-1], 'channel': title, 'link': my_link, 'ts': time.time()})
                        await asyncio.sleep(3)
                    except: pass

            except Exception as e: 
                print(f"Err {channel_str}: {e}")
                continue

        # ذخیره و ساخت سایت
        # ========== ساخت GitHub Pages (Premium Version) ==========
    print("\n📄 ساخت صفحه Premium...")
    
    now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
    j_now = jdatetime.datetime.fromgregorian(datetime=datetime.now(iran_tz))
    j_date_str = j_now.strftime('%Y/%m/%d')
    
    # آماده‌سازی HTML برای کانفیگ‌ها
    html_configs = ""
    if live_configs:
        for idx, cfg in enumerate(sorted(live_configs, key=lambda x: x['latency']), 1):
            status_class = "excellent" if cfg['latency'] < 100 else "good" if cfg['latency'] < 200 else "medium"
            safe_config = cfg['config'].replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
            
            html_configs += f"""
<div class="card" data-protocol="{cfg['protocol'].lower()}" data-ping="{cfg['latency']}">
    <div class="card-header">
        <span class="protocol-badge {cfg['protocol'].lower()}">{cfg['protocol']}</span>
        <span class="status-badge {status_class}">
            {'🟢' if cfg['latency'] < 100 else '🟡' if cfg['latency'] < 200 else '🟠'} {cfg['latency']}ms
        </span>
    </div>
    <div class="card-body">
        <div class="source">📡 {cfg['channel']}</div>
        <div class="code-block" id="cfg{idx}" onclick="selectCode(this)">{cfg['config'][:80]}...</div>
    </div>
    <div class="actions">
        <button class="btn btn-copy" onclick='copyFull("{safe_config}", this)'>
            <i class="far fa-copy"></i> کپی
        </button>
        <button class="btn btn-qr" onclick='showQR("{safe_config}")'>
            <i class="fas fa-qrcode"></i> QR
        </button>
        <a href="{cfg.get('telegram_link', '#')}" target="_blank" class="btn btn-link">
            <i class="fab fa-telegram"></i>
        </a>
        <button class="btn btn-download" onclick='downloadConfig("{safe_config}", "config_{idx}.txt")'>
            <i class="fas fa-download"></i>
        </button>
    </div>
</div>
"""
    else:
        html_configs = '<div class="empty"><i class="fas fa-inbox"></i><p>هیچ کانفیگ زنده‌ای موجود نیست</p></div>'
    
    # آماده‌سازی HTML برای پروکسی‌ها
    html_proxies = ""
    if all_proxies_data:
        for idx, (key, data) in enumerate(all_proxies_data.items(), 1):
            html_proxies += f"""
<div class="card">
    <div class="card-header">
        <span class="protocol-badge proxy">MTProto</span>
    </div>
    <div class="card-body">
        <div class="source">📡 {data['channel']}</div>
        <div class="code-block">{key}</div>
    </div>
    <div class="actions">
        <a href="{data['link']}" class="btn btn-copy" style="flex:2">
            <i class="fas fa-link"></i> اتصال مستقیم
        </a>
        <a href="{data.get('telegram_link', '#')}" target="_blank" class="btn btn-link">
            <i class="fab fa-telegram"></i>
        </a>
    </div>
</div>
"""
    else:
        html_proxies = '<div class="empty"><i class="fas fa-shield-alt"></i><p>پروکسی موجود نیست</p></div>'
    
    # آماده‌سازی HTML برای فایل‌ها
    html_files = ""
    if all_files_data:
        for idx, (fname, data) in enumerate(all_files_data.items(), 1):
            ext = fname.split('.')[-1].upper()
            html_files += f"""
<div class="card">
    <div class="card-header">
        <span class="protocol-badge file">{ext}</span>
    </div>
    <div class="card-body">
        <div class="source">📡 {data['channel']}</div>
        <div style="font-weight:bold;margin:10px 0">{fname}</div>
    </div>
    <div class="actions">
        <a href="{data.get('link', '#')}" target="_blank" class="btn btn-copy" style="flex:1">
            <i class="fas fa-download"></i> دانلود
        </a>
    </div>
</div>
"""
    else:
        html_files = '<div class="empty"><i class="fas fa-folder-open"></i><p>فایل موجود نیست</p></div>'
    
    # محاسبه آمار
    total_configs = len(live_configs)
    avg_ping = int(sum(c['latency'] for c in live_configs) / len(live_configs)) if live_configs else 0
    excellent_count = len([c for c in live_configs if c['latency'] < 100])
    
    # HTML کامل
    full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium | {destination_channel}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{
            --bg: #0f172a;
            --card: #1e293b;
            --primary: #38bdf8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --text: #f1f5f9;
            --sub: #94a3b8;
            --border: #334155;
            --purple: #a78bfa;
            --green: #34d399;
        }}
        
        [data-theme="light"] {{
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #0f172a;
            --sub: #64748b;
            --border: #e2e8f0;
        }}
        
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        
        body {{ 
            background:var(--bg); 
            color:var(--text); 
            padding-bottom:80px;
            transition:background 0.3s, color 0.3s;
        }}
        
        /* Header */
        header {{ 
            background:rgba(30,41,59,0.95); 
            padding:15px; 
            position:sticky; 
            top:0; 
            z-index:50; 
            border-bottom:1px solid var(--border);
            backdrop-filter:blur(10px);
        }}
        
        .header-content {{
            max-width:600px;
            margin:0 auto;
            display:flex;
            justify-content:space-between;
            align-items:center;
        }}
        
        .header-left {{ flex:1; }}
        .header-left h2 {{ font-size:1.5rem; margin-bottom:3px; }}
        .header-left small {{ color:var(--sub); font-size:0.75rem; }}
        
        .header-right {{
            display:flex;
            gap:10px;
        }}
        
        .icon-btn {{
            width:40px;
            height:40px;
            border-radius:10px;
            border:1px solid var(--border);
            background:var(--card);
            color:var(--text);
            display:flex;
            align-items:center;
            justify-content:center;
            cursor:pointer;
            transition:all 0.3s;
        }}
        
        .icon-btn:hover {{
            background:var(--primary);
            color:var(--bg);
            transform:scale(1.1);
        }}
        
        /* Stats Bar */
        .stats-bar {{
            background:var(--card);
            padding:15px;
            margin:15px auto;
            max-width:600px;
            border-radius:12px;
            display:grid;
            grid-template-columns:repeat(3,1fr);
            gap:15px;
            border:1px solid var(--border);
        }}
        
        .stat-item {{
            text-align:center;
        }}
        
        .stat-value {{
            font-size:1.5rem;
            font-weight:bold;
            color:var(--primary);
        }}
        
        .stat-label {{
            font-size:0.75rem;
            color:var(--sub);
            margin-top:5px;
        }}
        
        /* Search & Filter */
        .toolbar {{
            max-width:600px;
            margin:15px auto;
            padding:0 15px;
            display:flex;
            gap:10px;
        }}
        
        .search-box {{
            flex:1;
            position:relative;
        }}
        
        .search-box input {{
            width:100%;
            padding:12px 40px 12px 15px;
            border-radius:12px;
            border:1px solid var(--border);
            background:var(--card);
            color:var(--text);
            font-size:0.9rem;
        }}
        
        .search-box i {{
            position:absolute;
            right:15px;
            top:50%;
            transform:translateY(-50%);
            color:var(--sub);
        }}
        
        .filter-btn {{
            padding:12px 20px;
            border-radius:12px;
            border:1px solid var(--border);
            background:var(--card);
            color:var(--text);
            cursor:pointer;
            display:flex;
            align-items:center;
            gap:8px;
            transition:all 0.3s;
        }}
        
        .filter-btn:hover {{
            background:var(--primary);
            color:var(--bg);
        }}
        
        .filter-btn.active {{
            background:var(--primary);
            color:var(--bg);
        }}
        
        /* Container */
        .container {{ 
            max-width:600px; 
            margin:0 auto; 
            padding:0 15px; 
        }}
        
        /* Card */
        .card {{ 
            background:var(--card); 
            border-radius:16px; 
            padding:16px; 
            margin-bottom:16px; 
            border:1px solid var(--border);
            animation:slideIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
            transition:transform 0.3s, box-shadow 0.3s;
        }}
        
        .card:hover {{
            transform:translateY(-5px);
            box-shadow:0 10px 30px rgba(56,189,248,0.2);
        }}
        
        @keyframes slideIn {{
            from {{ opacity:0; transform:translateY(20px) scale(0.95); }}
            to {{ opacity:1; transform:translateY(0) scale(1); }}
        }}
        
        .card-header {{
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom:12px;
        }}
        
        .protocol-badge {{
            padding:6px 12px;
            border-radius:8px;
            font-size:0.75rem;
            font-weight:bold;
            text-transform:uppercase;
        }}
        
        .vmess {{ background:linear-gradient(135deg,#667eea,#764ba2); color:white; }}
        .vless {{ background:linear-gradient(135deg,#f093fb,#f5576c); color:white; }}
        .trojan {{ background:linear-gradient(135deg,#4facfe,#00f2fe); color:white; }}
        .ss {{ background:linear-gradient(135deg,#43e97b,#38f9d7); color:white; }}
        .proxy {{ background:linear-gradient(135deg,#fa709a,#fee140); color:white; }}
        .file {{ background:linear-gradient(135deg,#30cfd0,#330867); color:white; }}
        
        .status-badge {{
            padding:6px 12px;
            border-radius:8px;
            font-size:0.75rem;
            font-weight:bold;
        }}
        
        .excellent {{ background:rgba(16,185,129,0.2); color:var(--success); }}
        .good {{ background:rgba(245,158,11,0.2); color:var(--warning); }}
        .medium {{ background:rgba(239,68,68,0.2); color:var(--danger); }}
        
        .card-body {{
            margin-bottom:12px;
        }}
        
        .source {{
            font-size:0.8rem;
            color:var(--sub);
            margin-bottom:8px;
        }}
        
        .code-block {{ 
            background:#0b1120; 
            padding:12px; 
            border-radius:10px; 
            color:#a5b4fc; 
            overflow:hidden;
            white-space:nowrap; 
            text-overflow:ellipsis;
            cursor:pointer;
            font-family:monospace;
            font-size:0.85rem;
            direction:ltr;
            transition:all 0.3s;
        }}
        
        .code-block:hover {{
            background:#1a1f3a;
        }}
        
        .code-block.selected {{
            background:var(--primary);
            color:var(--bg);
        }}
        
        .actions {{ 
            display:grid;
            grid-template-columns:1fr 1fr auto auto;
            gap:8px;
        }}
        
        .btn {{ 
            padding:10px;
            border-radius:10px;
            border:none;
            cursor:pointer;
            font-weight:bold;
            display:flex;
            align-items:center;
            justify-content:center;
            gap:5px;
            text-decoration:none;
            transition:all 0.3s;
            font-size:0.85rem;
        }}
        
        .btn:active {{
            transform:scale(0.95);
        }}
        
        .btn-copy {{ 
            background:var(--primary); 
            color:var(--bg);
        }}
        
        .btn-copy:hover {{
            background:#0ea5e9;
            box-shadow:0 5px 15px rgba(56,189,248,0.4);
        }}
        
        .btn-qr {{
            background:var(--purple);
            color:white;
        }}
        
        .btn-qr:hover {{
            background:#9333ea;
        }}
        
        .btn-link {{ 
            background:transparent;
            border:1px solid var(--border);
            color:var(--text);
        }}
        
        .btn-link:hover {{
            background:var(--border);
        }}
        
        .btn-download {{
            background:var(--success);
            color:white;
        }}
        
        .btn-download:hover {{
            background:#059669;
        }}
        
        /* Bottom Navigation */
        .nav {{ 
            position:fixed;
            bottom:0;
            left:0;
            right:0;
            background:rgba(30,41,59,0.95);
            display:flex;
            padding:8px;
            border-top:1px solid var(--border);
            z-index:99;
            backdrop-filter:blur(10px);
        }}
        
        .nav-item {{ 
            flex:1;
            text-align:center;
            color:var(--sub);
            cursor:pointer;
            font-size:0.7rem;
            padding:8px;
            border-radius:10px;
            transition:all 0.3s;
        }}
        
        .nav-item:active {{
            transform:scale(0.95);
        }}
        
        .nav-item.active {{ 
            color:var(--primary);
            background:rgba(56,189,248,0.1);
        }}
        
        .nav-item i {{ 
            display:block;
            font-size:1.3rem;
            margin-bottom:4px;
        }}
        
        /* Tabs */
        .tab {{ display:none; }}
        .tab.active {{ display:block; }}
        
        /* Empty State */
        .empty {{ 
            text-align:center;
            padding:60px 20px;
            color:var(--sub);
        }}
        
        .empty i {{ 
            font-size:4rem;
            margin-bottom:20px;
            opacity:0.3;
        }}
        
        .empty p {{
            font-size:1.1rem;
        }}
        
        /* QR Modal */
        #qrModal {{ 
            display:none;
            position:fixed;
            top:0;
            left:0;
            width:100%;
            height:100%;
            background:rgba(0,0,0,0.9);
            z-index:2000;
            align-items:center;
            justify-content:center;
        }}
        
        .modal-content {{ 
            background:var(--card);
            padding:25px;
            border-radius:20px;
            max-width:350px;
            width:90%;
            text-align:center;
            animation:modalPop 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }}
        
        @keyframes modalPop {{
            from {{ opacity:0; transform:scale(0.8); }}
            to {{ opacity:1; transform:scale(1); }}
        }}
        
        .modal-content h3 {{
            margin-bottom:20px;
            color:var(--text);
        }}
        
        #qrCanvas {{
            width:100%;
            max-width:300px;
            height:auto;
            border-radius:15px;
            background:white;
            padding:15px;
        }}
        
        .modal-close {{
            margin-top:20px;
            padding:12px 30px;
            background:var(--danger);
            color:white;
            border:none;
            border-radius:10px;
            cursor:pointer;
            font-weight:bold;
        }}
        
        /* Filter Panel */
        #filterPanel {{
            display:none;
            position:fixed;
            bottom:80px;
            right:15px;
            background:var(--card);
            border:1px solid var(--border);
            border-radius:15px;
            padding:15px;
            box-shadow:0 10px 30px rgba(0,0,0,0.3);
            z-index:100;
            animation:slideUp 0.3s;
        }}
        
        @keyframes slideUp {{
            from {{ opacity:0; transform:translateY(20px); }}
            to {{ opacity:1; transform:translateY(0); }}
        }}
        
        .filter-option {{
            padding:10px;
            margin:5px 0;
            border-radius:8px;
            cursor:pointer;
            transition:all 0.3s;
        }}
        
        .filter-option:hover {{
            background:rgba(56,189,248,0.1);
        }}
        
        .filter-option.active {{
            background:var(--primary);
            color:var(--bg);
        }}
        
        /* Toast Notification */
        #toast {{
            position:fixed;
            bottom:100px;
            left:50%;
            transform:translateX(-50%) translateY(100px);
            background:var(--success);
            color:white;
            padding:15px 25px;
            border-radius:10px;
            font-weight:bold;
            z-index:1000;
            opacity:0;
            transition:all 0.3s;
        }}
        
        #toast.show {{
            opacity:1;
            transform:translateX(-50%) translateY(0);
        }}
        
        /* Loading */
        .loading {{
            text-align:center;
            padding:40px;
            color:var(--sub);
        }}
        
        .spinner {{
            border:3px solid var(--border);
            border-top:3px solid var(--primary);
            border-radius:50%;
            width:40px;
            height:40px;
            animation:spin 1s linear infinite;
            margin:0 auto 15px;
        }}
        
        @keyframes spin {{
            0% {{ transform:rotate(0deg); }}
            100% {{ transform:rotate(360deg); }}
        }}
        
        /* Responsive */
        @media (max-width:400px) {{
            .stats-bar {{ grid-template-columns:1fr; }}
            .actions {{ grid-template-columns:1fr 1fr; }}
            .btn {{ font-size:0.75rem; padding:8px; }}
        }}
        
        /* Pull to Refresh */
        .refresh-indicator {{
            position:fixed;
            top:70px;
            left:50%;
            transform:translateX(-50%) translateY(-100px);
            background:var(--card);
            padding:15px 30px;
            border-radius:50px;
            box-shadow:0 5px 20px rgba(0,0,0,0.3);
            display:flex;
            align-items:center;
            gap:10px;
            transition:transform 0.3s;
            z-index:1000;
        }}
        
        .refresh-indicator.show {{
            transform:translateX(-50%) translateY(0);
        }}
    </style>
</head>
<body>
    <!-- Header -->
    <header>
        <div class="header-content">
            <div class="header-left">
                <h2>🔮 VPN Hub</h2>
                <small>بروزرسانی: {now_str}</small>
            </div>
            <div class="header-right">
                <div class="icon-btn" onclick="toggleTheme()" title="تغییر تم">
                    <i class="fas fa-moon" id="themeIcon"></i>
                </div>
                <div class="icon-btn" onclick="location.reload()" title="بروزرسانی">
                    <i class="fas fa-sync-alt"></i>
                </div>
            </div>
        </div>
    </header>
    
    <!-- Stats Bar -->
    <div class="stats-bar">
        <div class="stat-item">
            <div class="stat-value">{total_configs}</div>
            <div class="stat-label">کانفیگ آنلاین</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{avg_ping}ms</div>
            <div class="stat-label">میانگین پینگ</div>
        </div>
        <div class="stat-item">
            <div class="stat-value">{excellent_count}</div>
            <div class="stat-label">سرعت عالی</div>
        </div>
    </div>
    
    <!-- Toolbar -->
    <div class="toolbar">
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="جستجو..." onkeyup="searchItems()">
            <i class="fas fa-search"></i>
        </div>
        <div class="filter-btn" onclick="toggleFilter()">
            <i class="fas fa-filter"></i>
            <span>فیلتر</span>
        </div>
    </div>
    
    <!-- Filter Panel -->
    <div id="filterPanel">
        <div class="filter-option active" onclick="sortBy('default')">
            <i class="fas fa-sort"></i> پیش‌فرض
        </div>
        <div class="filter-option" onclick="sortBy('ping')">
            <i class="fas fa-tachometer-alt"></i> سریع‌ترین
        </div>
        <div class="filter-option" onclick="sortBy('newest')">
            <i class="fas fa-clock"></i> جدیدترین
        </div>
        <div class="filter-option" onclick="filterProtocol('vmess')">
            <i class="fas fa-filter"></i> فقط VMess
        </div>
        <div class="filter-option" onclick="filterProtocol('vless')">
            <i class="fas fa-filter"></i> فقط VLess
        </div>
    </div>
    
    <!-- Container -->
    <div class="container">
        <div id="t1" class="tab active">{html_configs}</div>
        <div id="t2" class="tab">{html_proxies}</div>
        <div id="t3" class="tab">{html_files}</div>
    </div>
    
    <!-- Bottom Navigation -->
    <nav class="nav">
        <div class="nav-item active" onclick="switchTab('t1',this)">
            <i class="fas fa-rocket"></i>
            کانفیگ
        </div>
        <div class="nav-item" onclick="switchTab('t2',this)">
            <i class="fas fa-shield-alt"></i>
            پروکسی
        </div>
        <div class="nav-item" onclick="switchTab('t3',this)">
            <i class="fas fa-folder"></i>
            فایل
        </div>
    </nav>
    
    <!-- QR Modal -->
    <div id="qrModal" onclick="closeQR()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3>اسکن QR Code</h3>
            <canvas id="qrCanvas"></canvas>
            <button class="modal-close" onclick="closeQR()">بستن</button>
        </div>
    </div>
    
    <!-- Toast -->
    <div id="toast"></div>
    
    <!-- Refresh Indicator -->
    <div class="refresh-indicator" id="refreshIndicator">
        <div class="spinner"></div>
        <span>در حال بروزرسانی...</span>
    </div>
    
    <!-- QRCode.js Library -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    
    <script>
        // Tab Switching
        function switchTab(id, el) {{
            document.querySelectorAll('.tab').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active'));
            document.getElementById(id).classList.add('active');
            el.classList.add('active');
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
            
            // Haptic feedback
            if ('vibrate' in navigator) navigator.vibrate(10);
        }}
        
        // Copy Full Text
        function copyFull(text, btn) {{
            navigator.clipboard.writeText(text).then(() => {{
                const original = btn.innerHTML;
                btn.innerHTML = '<i class="fas fa-check"></i> کپی شد';
                btn.style.background = 'var(--success)';
                showToast('✅ کانفیگ کپی شد!');
                
                setTimeout(() => {{
                    btn.innerHTML = original;
                    btn.style.background = 'var(--primary)';
                }}, 2000);
            }});
        }}
        
        // Show QR Code
        let currentQR = null;
        function showQR(text) {{
            const modal = document.getElementById('qrModal');
            const canvas = document.getElementById('qrCanvas');
            
            // پاک کردن QR قبلی
            canvas.innerHTML = '';
            
            // ساخت QR جدید
            currentQR = new QRCode(canvas, {{
                text: text,
                width: 280,
                height: 280,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.H
            }});
            
            modal.style.display = 'flex';
            
            // Haptic
            if ('vibrate' in navigator) navigator.vibrate([10, 50, 10]);
        }}
        
        function closeQR() {{
            document.getElementById('qrModal').style.display = 'none';
        }}
        
        // Download Config
        function downloadConfig(text, filename) {{
            const blob = new Blob([text], {{ type: 'text/plain' }});
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            a.click();
            URL.revokeObjectURL(url);
            showToast('📥 فایل دانلود شد!');
        }}
        
        // Select Code Block
        function selectCode(el) {{
            document.querySelectorAll('.code-block').forEach(e => e.classList.remove('selected'));
            el.classList.add('selected');
        }}
        
        // Toast Notification
        function showToast(msg) {{
            const toast = document.getElementById('toast');
            toast.innerText = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3000);
        }}
        
        // Theme Toggle
        function toggleTheme() {{
            const html = document.documentElement;
            const icon = document.getElementById('themeIcon');
            
            if (html.getAttribute('data-theme') === 'light') {{
                html.removeAttribute('data-theme');
                icon.className = 'fas fa-moon';
                localStorage.setItem('theme', 'dark');
            }} else {{
                html.setAttribute('data-theme', 'light');
                icon.className = 'fas fa-sun';
                localStorage.setItem('theme', 'light');
            }}
        }}
        
        // Load Theme
        window.addEventListener('load', () => {{
            const theme = localStorage.getItem('theme');
            if (theme === 'light') {{
                document.documentElement.setAttribute('data-theme', 'light');
                document.getElementById('themeIcon').className = 'fas fa-sun';
            }}
        }});
        
        // Search
        function searchItems() {{
            const query = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.querySelectorAll('.card');
            
            cards.forEach(card => {{
                const text = card.innerText.toLowerCase();
                card.style.display = text.includes(query) ? 'block' : 'none';
            }});
        }}
        
        // Filter Panel Toggle
        function toggleFilter() {{
            const panel = document.getElementById('filterPanel');
            panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
        }}
        
        // Sort By
        function sortBy(type) {{
            const container = document.querySelector('.tab.active');
            const cards = Array.from(container.querySelectorAll('.card'));
            
            if (type === 'ping') {{
                cards.sort((a, b) => {{
                    const pingA = parseInt(a.getAttribute('data-ping')) || 9999;
                    const pingB = parseInt(b.getAttribute('data-ping')) || 9999;
                    return pingA - pingB;
                }});
            }} else if (type === 'newest') {{
                cards.reverse();
            }}
            
            cards.forEach(card => container.appendChild(card));
            
            // Update active filter
            document.querySelectorAll('.filter-option').forEach(opt => opt.classList.remove('active'));
            event.target.classList.add('active');
            
            showToast('🔄 مرتب‌سازی انجام شد');
        }}
        
        // Filter by Protocol
        function filterProtocol(protocol) {{
            const cards = document.querySelectorAll('.card');
            
            cards.forEach(card => {{
                const cardProtocol = card.getAttribute('data-protocol');
                card.style.display = cardProtocol === protocol ? 'block' : 'none';
            }});
            
            showToast(`فیلتر: ${{protocol.toUpperCase()}}`);
        }}
        
        // Pull to Refresh
        let startY = 0;
        let pulling = false;
        
        document.addEventListener('touchstart', e => {{
            if (window.scrollY === 0) {{
                startY = e.touches[0].pageY;
            }}
        }});
        
        document.addEventListener('touchmove', e => {{
            if (window.scrollY === 0) {{
                const currentY = e.touches[0].pageY;
                const diff = currentY - startY;
                
                if (diff > 80) {{
                    document.getElementById('refreshIndicator').classList.add('show');
                    pulling = true;
                }}
            }}
        }});
        
        document.addEventListener('touchend', () => {{
            if (pulling) {{
                setTimeout(() => location.reload(), 500);
            }}
            pulling = false;
        }});
        
        // Auto Refresh (40 minutes)
        setTimeout(() => {{
            showToast('🔄 بروزرسانی خودکار...');
            setTimeout(() => location.reload(), 2000);
        }}, 40 * 60 * 1000);
        
        // Keyboard Shortcuts
        document.addEventListener('keydown', e => {{
            if (e.ctrlKey && e.key === 'f') {{
                e.preventDefault();
                document.getElementById('searchInput').focus();
            }}
            if (e.key === 'Escape') {{
                closeQR();
                document.getElementById('filterPanel').style.display = 'none';
            }}
        }});
        
        // Service Worker (Progressive Web App)
        if ('serviceWorker' in navigator) {{
            navigator.serviceWorker.register('/sw.js').catch(() => {{}});
        }}
    </script>
</body>
</html>"""
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print("✅ صفحه Premium ساخته شد")
    print(f"   💎 تمام امکانات فعال است")
    
except Exception as e:
    print(f"❌ خطا: {e}")
    import traceback
    traceback.print_exc()
