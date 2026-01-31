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
import html  # این ماژول برای درست کردن لینک‌ها حیاتی است
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

# دریافت سشن‌ها (اولویت با سشن 2)
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
# 2. توابع کمکی
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
    minute = datetime.now(iran_tz).minute
    target_session = session_2 if session_2 else session_1
    
    if minute < 30:
        print(f"👤 نوبت نیمه اول (کانال 1-20)")
        return ALL_CHANNELS[:20], "اول", target_session
    else:
        print(f"👤 نوبت نیمه دوم (کانال 21-40)")
        return ALL_CHANNELS[20:], "دوم", target_session

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
                if any(host.startswith(p) for p in IRAN_IP_PREFIXES): return "🔵 اینترانت", None, True
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
# 3. بدنه اصلی ربات
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
        
        # لیست هش‌ها برای جلوگیری از تکرار
        sent_hashes = set()
        for c in hist['configs']: sent_hashes.add(c['config'])
        for p in hist['proxies']: sent_hashes.add(p['link'])
        for f in hist['files']: sent_hashes.add(f['name'])
        
        print(f"🔄 {len(sent_hashes)} آیتم در حافظه موقت.")
        await asyncio.sleep(random.randint(5, 10))
        
        new_conf, new_prox, new_file = [], [], []
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=MAX_MESSAGE_AGE_MINUTES)

        # شروع پیمایش کانال‌ها
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
                    print("⚠️ کانال در دسترس نیست")
                    continue

                msgs = await client.get_messages(entity, limit=20)
                temp_c, temp_p, temp_f = [], [], []
                title = getattr(entity, 'title', channel_str)
                
                for m in msgs:
                    # نادیده گرفتن پیام‌های قدیمی
                    if m.date < cutoff_time: continue
                    
                    link = f"https://t.me/{channel_str[1:]}/{m.id}"
                    
                    if m.text:
                        # استخراج کانفیگ
                        for c in re.findall(r"(?:vmess|vless|trojan|ss|shadowsocks|hy2|tuic)://[^\s\n]+", m.text):
                            if c not in sent_hashes:
                                temp_c.append({'c': c, 'link': link})
                                sent_hashes.add(c)
                        
                                                # استخراج پروکسی
                        for p in re.findall(r"https://t.me/proxy\?[^\s\n]+", m.text):
                            # اصلاح فرمت لینک به tg://proxy برای کارکرد صحیح دکمه‌های اتصال
                            clean_p = p.replace('https://t.me/proxy', 'tg://proxy')
                            
                            if clean_p not in sent_hashes:
                                temp_p.append({'p': clean_p, 'link': link, 'src': link})
                                sent_hashes.add(clean_p)


                    # استخراج فایل
                    if m.file and any(m.file.name.endswith(x) for x in allowed_extensions if m.file.name):
                        if m.file.name not in sent_hashes:
                            temp_f.append({'n': m.file.name, 'm': m, 'link': link})
                            sent_hashes.add(m.file.name)

                # ارسال کانفیگ‌ها
                for item in temp_c:
                    stat, lat, _ = await check_status(item['c'])
                    if stat:
                        prot = item['c'].split('://')[0].upper()
                        # ارسال به صورت کد بلاک برای کپی راحت
                        txt = f"🔮 **{prot}**\n\n```\n{item['c']}\n```\n📊 {stat} • {lat}ms\n{get_hashtags(item['c'], 'config')}{create_footer(title, item['link'])}"
                        try:
                            sent = await client.send_message(destination_channel, txt, link_preview=False)
                            my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                            new_conf.append({'protocol': prot, 'config': item['c'], 'latency': lat, 'channel': title, 't_link': my_link, 'ts': time.time()})
                            await asyncio.sleep(3)
                        except Exception as e: print(f"ارسال ناموفق کانفیگ: {e}")
# ارسال پروکسی (اصلاح شده)
                valid_proxies = []
                for item in temp_p:
                    stat, lat, _ = await check_status(item['p'], 'proxy')
                    if stat:
                        ping = f"{lat}ms" if lat else ""
                        valid_proxies.append({
                            'l': item['p'], 
                            's': stat, 
                            'pi': ping, 
                            'src': item['link']
                        })
                        k = extract_proxy_key(item['p'])
                        new_prox.append({
                            'key': k, 
                            'link': item['p'], 
                            'channel': title, 
                            't_link': '#', 
                            'ts': time.time()
                        })
                
                # -----------------------------------------------------------------
                # بخش پردازش و ارسال پروکسی (با پشتیبانی از فرمت‌های مختلف + HTML)
                # -----------------------------------------------------------------
                
                # تابع داخلی برای استانداردسازی لینک پروکسی
                def build_mtproxy_link(raw):
                    raw = raw.strip()
                    # اگر خودش لینک کامل بود، همون رو برگردون
                    if raw.startswith(("tg://proxy", "https://t.me/proxy")):
                        return raw
                    # اگر فرمت ip:port:secret بود، تبدیلش کن
                    try:
                        if ":" in raw:
                            parts = raw.split(":")
                            if len(parts) == 3:
                                server, port, secret = parts
                                return f"https://t.me/proxy?server={server}&port={port}&secret={secret}"
                    except: pass
                    return None

                valid_proxies = []
                # پردازش لیست پروکسی‌های پیدا شده
                for item in temp_p:
                    # بررسی سلامت پروکسی
                    stat, lat, _ = await check_status(item['p'], 'proxy')
                    if not stat:
                        continue

                    # ساخت لینک استاندارد
                    mt_link = build_mtproxy_link(item['p'])
                    if not mt_link:
                        continue

                    ping = f"{lat}ms" if lat else ""

                    valid_proxies.append({
                        'l': mt_link,        # لینک استاندارد برای کلیک
                        's': stat,
                        'pi': ping,
                        'src': item['link']  # لینک منبع
                    })

                    # ذخیره در لیست برای دیتابیس
                    k = extract_proxy_key(item['p'])
                    new_prox.append({
                        'key': k,
                        'link': item['p'],
                        'channel': title,
                        't_link': '#',
                        'ts': time.time()
                    })

                # ارسال پیام اگر پروکسی سالمی پیدا شد
                if valid_proxies:
                    # هدر پیام (HTML)
                    body = "🔵 <b>MTProxy‌های جدید</b>\n\n"

                    for idx, p in enumerate(valid_proxies, 1):
                        # استفاده از تگ <a> برای لینک‌دهی مطمئن
                        safe_link = html.escape(p['l'])
                        body += f"{idx}. <a href='{safe_link}'>🔗 اتصال</a> • {p['s']} {p['pi']}\n"

                    # فوتر پیام (HTML)
                    now = datetime.now(iran_tz)
                    safe_title = html.escape(clean_title(title)) # ایمن‌سازی اسم کانال
                    src_link = html.escape(valid_proxies[0]['src'])
                    
                    footer_html = (
                        "\n━━━━━━━━━━━━━━━━\n"
                        f"🗓 {now.strftime('%Y/%m/%d')} • 🕐 {now.strftime('%H:%M')}\n"
                        f"📡 منبع: <a href='{src_link}'>{safe_title}</a>\n"
                        f"🔗 {destination_channel}"
                    )

                    body += "\n💡 برای اتصال روی لینک کلیک کنید" + footer_html

                    try:
                        # ارسال با متد HTML (کلید موفقیت)
                        sent = await client.send_message(
                            destination_channel,
                            body,
                            parse_mode="html",
                            link_preview=False
                        )

                        # آپدیت لینک پیام در دیتابیس
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                        for p in new_prox:
                            if p['channel'] == title:
                                p['t_link'] = my_link

                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"ارسال ناموفق پروکسی: {e}")
                # ارسال فایل‌ها
                for item in temp_f:
                    cap = f"📂 **{item['n']}**\n\n{get_hashtags(item['n'])}{create_footer(title, item['link'])}"
                    try:
                        sent = await client.send_file(destination_channel, item['m'], caption=cap)
                        my_link = f"https://t.me/{destination_channel[1:]}/{sent.id}"
                        new_file.append({'name': item['n'], 'ext': item['n'].split('.')[-1], 'channel': title, 'link': my_link, 'ts': time.time()})
                        await asyncio.sleep(3)
                    except: pass

            except Exception as e:
                print(f"Err {channel_str}: {e}")
                continue

        # =============================================================================
        # 4. ذخیره دیتابیس و ساخت سایت (بخش Premium)
        # =============================================================================
        print("💾 ذخیره دیتابیس...")
        f_c = merge_data(hist['configs'], new_conf, 'config')
        f_p = merge_data(hist['proxies'], new_prox, 'key')
        f_f = merge_data(hist['files'], new_file, 'name')
        save_data({'configs': f_c, 'proxies': f_p, 'files': f_f})
        
        # متغیرهای مورد نیاز برای سایت
        live_configs = f_c
        all_proxies_data = {p['key']: p for p in f_p} if f_p else {}
        all_files_data = {f['name']: f for f in f_f} if f_f else {}

        print("\n📄 ساخت صفحه Premium...")
        
        now_str = datetime.now(iran_tz).strftime('%Y/%m/%d - %H:%M')
        
        # تولید HTML کانفیگ‌ها
        html_configs = ""
        if live_configs:
            for idx, cfg in enumerate(sorted(live_configs, key=lambda x: x.get('latency', 9999)), 1):
                lat = cfg.get('latency', 9999)
                status_class = "excellent" if lat < 100 else "good" if lat < 200 else "medium"
                safe_config = cfg['config'].replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n')
                t_link = cfg.get('t_link', '#')
                
                html_configs += f"""
        <div class="card" data-protocol="{cfg['protocol'].lower()}" data-ping="{lat}">
            <div class="card-header">
                <span class="protocol-badge {cfg['protocol'].lower()}">{cfg['protocol']}</span>
                <span class="status-badge {status_class}">
                    {'🟢' if lat < 100 else '🟡' if lat < 200 else '🟠'} {lat}ms
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
                <a href="{t_link}" target="_blank" class="btn btn-link">
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
        
        # تولید HTML پروکسی‌ها
        html_proxies = ""
        if all_proxies_data:
            for idx, (key, data) in enumerate(all_proxies_data.items(), 1):
                t_link = data.get('t_link', '#')
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
                <a href="{t_link}" target="_blank" class="btn btn-link">
                    <i class="fab fa-telegram"></i>
                </a>
            </div>
        </div>
        """
        else:
            html_proxies = '<div class="empty"><i class="fas fa-shield-alt"></i><p>پروکسی موجود نیست</p></div>'
        
        # تولید HTML فایل‌ها
        html_files = ""
        if all_files_data:
            for idx, (fname, data) in enumerate(all_files_data.items(), 1):
                ext = fname.split('.')[-1].upper() if '.' in fname else 'FILE'
                t_link = data.get('link', '#')
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
                <a href="{t_link}" target="_blank" class="btn btn-copy" style="flex:1">
                    <i class="fas fa-download"></i> دانلود
                </a>
            </div>
        </div>
        """
        else:
            html_files = '<div class="empty"><i class="fas fa-folder-open"></i><p>فایل موجود نیست</p></div>'
        
        # محاسبه آمار
        total_configs = len(live_configs)
        valid_pings = [c.get('latency', 999) for c in live_configs if isinstance(c.get('latency'), int)]
        avg_ping = int(sum(valid_pings) / len(valid_pings)) if valid_pings else 0
        excellent_count = len([p for p in valid_pings if p < 100])
        
        # ساخت فایل HTML نهایی
        full_html = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>VPN Hub Premium | {destination_channel}</title>
    <link href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {{ --bg: #0f172a; --card: #1e293b; --primary: #38bdf8; --success: #10b981; --warning: #f59e0b; --danger: #ef4444; --text: #f1f5f9; --sub: #94a3b8; --border: #334155; --purple: #a78bfa; }}
        [data-theme="light"] {{ --bg: #f8fafc; --card: #ffffff; --text: #0f172a; --sub: #64748b; --border: #e2e8f0; }}
        * {{ margin:0; padding:0; box-sizing:border-box; font-family:'Vazirmatn',sans-serif; }}
        body {{ background:var(--bg); color:var(--text); padding-bottom:80px; transition:background 0.3s, color 0.3s; }}
        header {{ background:rgba(30,41,59,0.95); padding:15px; position:sticky; top:0; z-index:50; border-bottom:1px solid var(--border); backdrop-filter:blur(10px); }}
        .header-content {{ max-width:600px; margin:0 auto; display:flex; justify-content:space-between; align-items:center; }}
        .header-left h2 {{ font-size:1.5rem; margin-bottom:3px; }}
        .header-left small {{ color:var(--sub); font-size:0.75rem; }}
        .header-right {{ display:flex; gap:10px; }}
        .icon-btn {{ width:40px; height:40px; border-radius:10px; border:1px solid var(--border); background:var(--card); color:var(--text); display:flex; align-items:center; justify-content:center; cursor:pointer; transition:all 0.3s; }}
        .icon-btn:hover {{ background:var(--primary); color:var(--bg); transform:scale(1.1); }}
        .stats-bar {{ background:var(--card); padding:15px; margin:15px auto; max-width:600px; border-radius:12px; display:grid; grid-template-columns:repeat(3,1fr); gap:15px; border:1px solid var(--border); }}
        .stat-item {{ text-align:center; }} .stat-value {{ font-size:1.5rem; font-weight:bold; color:var(--primary); }} .stat-label {{ font-size:0.75rem; color:var(--sub); margin-top:5px; }}
        .toolbar {{ max-width:600px; margin:15px auto; padding:0 15px; display:flex; gap:10px; }}
        .search-box {{ flex:1; position:relative; }} .search-box input {{ width:100%; padding:12px 40px 12px 15px; border-radius:12px; border:1px solid var(--border); background:var(--card); color:var(--text); font-size:0.9rem; }}
        .search-box i {{ position:absolute; right:15px; top:50%; transform:translateY(-50%); color:var(--sub); }}
        .filter-btn {{ padding:12px 20px; border-radius:12px; border:1px solid var(--border); background:var(--card); color:var(--text); cursor:pointer; display:flex; align-items:center; gap:8px; transition:all 0.3s; }}
        .container {{ max-width:600px; margin:0 auto; padding:0 15px; }}
        .card {{ background:var(--card); border-radius:16px; padding:16px; margin-bottom:16px; border:1px solid var(--border); animation:slideIn 0.5s; transition:transform 0.3s; }}
        @keyframes slideIn {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
        .card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
        .protocol-badge {{ padding:6px 12px; border-radius:8px; font-size:0.75rem; font-weight:bold; text-transform:uppercase; background:linear-gradient(135deg,#38bdf8,#3b82f6); color:white; }}
        .status-badge {{ padding:6px 12px; border-radius:8px; font-size:0.75rem; font-weight:bold; }}
        .excellent {{ background:rgba(16,185,129,0.2); color:var(--success); }} .good {{ background:rgba(245,158,11,0.2); color:var(--warning); }} .medium {{ background:rgba(239,68,68,0.2); color:var(--danger); }}
        .source {{ font-size:0.8rem; color:var(--sub); margin-bottom:8px; }}
        .code-block {{ background:#0b1120; padding:12px; border-radius:10px; color:#a5b4fc; overflow:hidden; white-space:nowrap; text-overflow:ellipsis; cursor:pointer; font-family:monospace; font-size:0.85rem; direction:ltr; transition:all 0.3s; }}
        .actions {{ display:grid; grid-template-columns:1fr 1fr auto auto; gap:8px; }}
        .btn {{ padding:10px; border-radius:10px; border:none; cursor:pointer; font-weight:bold; display:flex; align-items:center; justify-content:center; gap:5px; text-decoration:none; transition:all 0.3s; font-size:0.85rem; }}
        .btn-copy {{ background:var(--primary); color:var(--bg); }} .btn-qr {{ background:var(--purple); color:white; }} .btn-link {{ background:transparent; border:1px solid var(--border); color:var(--text); }} .btn-download {{ background:var(--success); color:white; }}
        .nav {{ position:fixed; bottom:0; left:0; right:0; background:rgba(30,41,59,0.95); display:flex; padding:8px; border-top:1px solid var(--border); z-index:99; backdrop-filter:blur(10px); }}
        .nav-item {{ flex:1; text-align:center; color:var(--sub); cursor:pointer; font-size:0.7rem; padding:8px; border-radius:10px; transition:all 0.3s; }}
        .nav-item.active {{ color:var(--primary); background:rgba(56,189,248,0.1); }}
        .nav-item i {{ display:block; font-size:1.3rem; margin-bottom:4px; }}
        .tab {{ display:none; }} .tab.active {{ display:block; }}
        .empty {{ text-align:center; padding:60px 20px; color:var(--sub); }} .empty i {{ font-size:4rem; margin-bottom:20px; opacity:0.3; }}
        #qrModal {{ display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.9); z-index:2000; align-items:center; justify-content:center; }}
        .modal-content {{ background:var(--card); padding:25px; border-radius:20px; max-width:350px; width:90%; text-align:center; }}
        #qrCanvas {{ width:100%; max-width:300px; height:auto; border-radius:15px; background:white; padding:15px; }}
        .modal-close {{ margin-top:20px; padding:12px 30px; background:var(--danger); color:white; border:none; border-radius:10px; cursor:pointer; font-weight:bold; }}
        #toast {{ position:fixed; bottom:100px; left:50%; transform:translateX(-50%) translateY(100px); background:var(--success); color:white; padding:15px 25px; border-radius:10px; font-weight:bold; z-index:1000; opacity:0; transition:all 0.3s; }}
        #toast.show {{ opacity:1; transform:translateX(-50%) translateY(0); }}
        #filterPanel {{ display:none; position:fixed; bottom:80px; right:15px; background:var(--card); border:1px solid var(--border); border-radius:15px; padding:15px; box-shadow:0 10px 30px rgba(0,0,0,0.3); z-index:100; }}
        .filter-option {{ padding:10px; margin:5px 0; border-radius:8px; cursor:pointer; transition:all 0.3s; }}
        .filter-option:hover {{ background:rgba(56,189,248,0.1); }}
        .filter-option.active {{ background:var(--primary); color:var(--bg); }}
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <div class="header-left"><h2>🔮 VPN Hub</h2><small>بروزرسانی: {now_str}</small></div>
            <div class="header-right">
                <div class="icon-btn" onclick="toggleTheme()"><i class="fas fa-moon" id="themeIcon"></i></div>
                <div class="icon-btn" onclick="location.reload()"><i class="fas fa-sync-alt"></i></div>
            </div>
        </div>
    </header>
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-value">{total_configs}</div><div class="stat-label">کانفیگ آنلاین</div></div>
        <div class="stat-item"><div class="stat-value">{avg_ping}ms</div><div class="stat-label">میانگین پینگ</div></div>
        <div class="stat-item"><div class="stat-value">{excellent_count}</div><div class="stat-label">سرعت عالی</div></div>
    </div>
    <div class="toolbar">
        <div class="search-box"><input type="text" id="searchInput" placeholder="جستجو..." onkeyup="searchItems()"><i class="fas fa-search"></i></div>
        <div class="filter-btn" onclick="toggleFilter()"><i class="fas fa-filter"></i><span>فیلتر</span></div>
    </div>
    <div id="filterPanel">
        <div class="filter-option" onclick="sortBy('ping')"><i class="fas fa-tachometer-alt"></i> سریع‌ترین</div>
        <div class="filter-option" onclick="sortBy('newest')"><i class="fas fa-clock"></i> جدیدترین</div>
    </div>
    <div class="container">
        <div id="t1" class="tab active">{html_configs}</div>
        <div id="t2" class="tab">{html_proxies}</div>
        <div id="t3" class="tab">{html_files}</div>
    </div>
    <nav class="nav">
        <div class="nav-item active" onclick="switchTab('t1',this)"><i class="fas fa-rocket"></i>کانفیگ</div>
        <div class="nav-item" onclick="switchTab('t2',this)"><i class="fas fa-shield-alt"></i>پروکسی</div>
        <div class="nav-item" onclick="switchTab('t3',this)"><i class="fas fa-folder"></i>فایل</div>
    </nav>
    <div id="qrModal" onclick="closeQR()">
        <div class="modal-content" onclick="event.stopPropagation()">
            <h3>اسکن QR Code</h3>
            <div id="qrCanvas"></div>
            <button class="modal-close" onclick="closeQR()">بستن</button>
        </div>
    </div>
    <div id="toast"></div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <script>
        function switchTab(id, el) {{ document.querySelectorAll('.tab').forEach(e => e.classList.remove('active')); document.querySelectorAll('.nav-item').forEach(e => e.classList.remove('active')); document.getElementById(id).classList.add('active'); el.classList.add('active'); window.scrollTo(0,0); }}
        function copyFull(text, btn) {{ navigator.clipboard.writeText(text).then(() => {{ showToast('✅ کانفیگ کپی شد!'); }}); }}
        function showQR(text) {{ const modal = document.getElementById('qrModal'); document.getElementById('qrCanvas').innerHTML = ''; new QRCode(document.getElementById('qrCanvas'), {{ text: text, width: 250, height: 250, correctLevel: QRCode.CorrectLevel.L }}); modal.style.display = 'flex'; }}
        function closeQR() {{ document.getElementById('qrModal').style.display = 'none'; }}
        function downloadConfig(text, filename) {{ const blob = new Blob([text], {{ type: 'text/plain' }}); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); }}
        function showToast(msg) {{ const toast = document.getElementById('toast'); toast.innerText = msg; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 3000); }}
        function toggleTheme() {{ const html = document.documentElement; if (html.getAttribute('data-theme') === 'light') {{ html.removeAttribute('data-theme'); localStorage.setItem('theme', 'dark'); }} else {{ html.setAttribute('data-theme', 'light'); localStorage.setItem('theme', 'light'); }} }}
        window.addEventListener('load', () => {{ if (localStorage.getItem('theme') === 'light') document.documentElement.setAttribute('data-theme', 'light'); }});
        function searchItems() {{ const query = document.getElementById('searchInput').value.toLowerCase(); document.querySelectorAll('.card').forEach(card => {{ card.style.display = card.innerText.toLowerCase().includes(query) ? 'block' : 'none'; }}); }}
        function toggleFilter() {{ const panel = document.getElementById('filterPanel'); panel.style.display = panel.style.display === 'block' ? 'none' : 'block'; }}
        function sortBy(type) {{ const container = document.querySelector('.tab.active'); const cards = Array.from(container.querySelectorAll('.card')); if (type === 'ping') {{ cards.sort((a, b) => (parseInt(a.getAttribute('data-ping'))||999) - (parseInt(b.getAttribute('data-ping'))||999)); }} else if (type === 'newest') {{ cards.reverse(); }} cards.forEach(card => container.appendChild(card)); document.getElementById('filterPanel').style.display = 'none'; }}
        function selectCode(el) {{ document.querySelectorAll('.code-block').forEach(e => e.classList.remove('selected')); el.classList.add('selected'); }}
    </script>
</body>
</html>"""
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(full_html)
        
        print("✅ صفحه وب ساخته شد (Premium Full)")

    except Exception as e:
        print(f"❌ خطا در اجرای اصلی: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await client.disconnect()

if __name__ == "__main__":
    with client: client.loop.run_until_complete(main())
