const demoData = {
  configs: [
    { protocol: 'VLESS', config: 'vless://00000000-0000-4000-8000-000000000001@de.example.net:443?type=ws&security=tls#DE-01', latency: 142, channel: 'کانال نمونه آلمان', country: 'Germany', flag: '🇩🇪', ts: Date.now()/1000 - 240 },
    { protocol: 'VLESS', config: 'vless://00000000-0000-4000-8000-000000000002@nl.example.net:8443?type=grpc&security=tls#NL-02', latency: 186, channel: 'کانال نمونه هلند', country: 'Netherlands', flag: '🇳🇱', ts: Date.now()/1000 - 720 },
    { protocol: 'VMESS', config: 'vmess://eyJhZGQiOiJ1cy5leGFtcGxlLm5ldCIsInBvcnQiOiI0NDMiLCJpZCI6IjAwMDAwMDAwLTAwMDAtNDAwMC04MDAwLTAwMDAwMDAwMDAwMyIsImFpZCI6IjAiLCJuZXQiOiJ3cyIsInRscyI6InRscyIsInBhdGgiOiIvIn0=#US-03', latency: 248, channel: 'کانال نمونه آمریکا', country: 'United States', flag: '🇺🇸', ts: Date.now()/1000 - 1100 },
    { protocol: 'TROJAN', config: 'trojan://demo-password@fi.example.net:443?security=tls&type=tcp#FI-04', latency: 310, channel: 'کانال نمونه فنلاند', country: 'Finland', flag: '🇫🇮', ts: Date.now()/1000 - 3200 },
    { protocol: 'SS', config: 'ss://YWVzLTI1Ni1nY206ZGVtby1vbmx5@fr.example.net:8388#FR-05', latency: 376, channel: 'کانال نمونه فرانسه', country: 'France', flag: '🇫🇷', ts: Date.now()/1000 - 5200 },
    { protocol: 'VLESS', config: 'vless://00000000-0000-4000-8000-000000000006@se.example.net:443?type=ws&security=tls#SE-06', latency: 582, channel: 'کانال نمونه سوئد', country: 'Sweden', flag: '🇸🇪', ts: Date.now()/1000 - 7200 },
    { protocol: 'HY2', config: 'hy2://demo-password@tr.example.net:443?sni=example.net#TR-07', latency: null, channel: 'کانال نمونه ترکیه', country: 'Türkiye', flag: '🇹🇷', ts: Date.now()/1000 - 9800 },
  ],
  proxies: [
    { protocol: 'MTPROXY', link: 'tg://proxy?server=proxy-one.example.net&port=443&secret=demo-only', latency: 118, channel: 'کانال پروکسی نمونه', country: 'Germany', flag: '🇩🇪', ts: Date.now()/1000 - 300 },
  ],
  files: [
    { protocol: 'NPVT', name: 'mobile-profile.npvt', link: 'https://t.me/example/101', channel: 'کانال فایل نمونه', country: '', ts: Date.now()/1000 - 5200 },
  ]
};

const subscriptionUrl = 'https://raw.githubusercontent.com/mostafa5804/Myvpn1404/refs/heads/main/sub.txt';
let database = demoData;
let dataMode = 'demo';
let activeView = 'servers';
let protocolFilter = 'ALL';
let countryFilter = 'ALL';
let statusFilter = 'ALL';
let sortMode = 'fresh';
let query = '';
let selected = new Set();
let favorites = new Set(JSON.parse(localStorage.getItem('vpnHubFavorites') || '[]'));

const app = document.querySelector('#app');

function escapeHTML(value = '') {
  return String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function allItems() {
  return [
    ...(database.configs || []).map((x, i) => ({...x, kind:'config', id:`c-${i}`, fullText:x.config, sourceLink:x.source_link || ''})),
    ...(database.proxies || []).map((x, i) => ({...x, protocol:'MTPROXY', kind:'proxy', id:`p-${i}`, fullText:x.link, sourceLink:x.source_link || ''})),
    ...(database.files || []).map((x, i) => ({...x, protocol:(x.ext || x.protocol || 'FILE').toUpperCase(), kind:'file', id:`f-${i}`, sourceLink:x.link || '', outputLink:x.t_link || ''})),
  ];
}
function safeLatency(item) { return Number.isFinite(Number(item.latency)) && item.latency !== null ? Number(item.latency) : null; }
function freshness(ts) {
  const minutes = Math.max(0, Math.floor((Date.now()/1000 - Number(ts || 0))/60));
  if (minutes < 2) return 'تازه بررسی‌شده';
  if (minutes < 60) return `${minutes} دقیقه پیش`;
  const hours = Math.floor(minutes/60);
  return hours < 24 ? `${hours} ساعت پیش` : 'قدیمی';
}
function connectionLabel(item) {
  const latency = safeLatency(item);
  if (latency === null) return {text:'بدون تست اتصال', cls:'muted'};
  if (item.kind === 'file') return {text:'فایل اصلی', cls:'muted'};
  if (latency < 200) return {text:`${latency} ms اتصال TCP`, cls:'good'};
  if (latency < 500) return {text:`${latency} ms اتصال TCP`, cls:'mid'};
  return {text:`${latency} ms اتصال TCP`, cls:'slow'};
}
function isFresh(ts) { return Date.now()/1000 - Number(ts || 0) < 3600; }
function getFiltered() {
  let list = allItems().filter(item => {
    const haystack = [item.protocol,item.country,item.channel,item.name,item.original_caption].join(' ').toLowerCase();
    const matchesQuery = !query || haystack.includes(query.toLowerCase());
    const matchesProtocol = protocolFilter === 'ALL' || (protocolFilter === 'MORE' ? !['VLESS','VMESS','TROJAN','MTPROXY'].includes(item.protocol) && item.kind !== 'file' : protocolFilter === 'FILE' ? item.kind === 'file' : item.protocol === protocolFilter);
    const matchesCountry = countryFilter === 'ALL' || (item.country || '') === countryFilter;
    const status = connectionLabel(item).cls;
    const matchesStatus = statusFilter === 'ALL' || (statusFilter === 'TESTED' ? item.kind !== 'file' && safeLatency(item) !== null : statusFilter === 'FRESH' ? isFresh(item.ts) : statusFilter === 'FAVORITES' ? favorites.has(item.id) : status === statusFilter);
    return matchesQuery && matchesProtocol && matchesCountry && matchesStatus;
  });
  if (sortMode === 'fresh') list.sort((a,b)=>(b.ts||0)-(a.ts||0));
  if (sortMode === 'latency') list.sort((a,b)=>(safeLatency(a) ?? 1e9)-(safeLatency(b) ?? 1e9));
  if (sortMode === 'country') list.sort((a,b)=>(a.country||'').localeCompare(b.country||''));
  return list;
}
function tally() {
  const items = allItems();
  return {total:items.length, tested:items.filter(x=>x.kind!=='file'&&safeLatency(x)!==null).length, fresh:items.filter(x=>isFresh(x.ts)).length};
}
function render() {
  const stats = tally();
  app.innerHTML = `
    <header class="topbar">
      <div class="top-inner">
        <a class="brand" href="#" aria-label="VPN Hub، صفحه اصلی"><span class="brand-mark">VPN</span><span><strong>VPN HUB</strong><small>فهرست اتصال‌های عمومی</small></span></a>
        <div class="top-actions"><span class="data-state ${dataMode==='live'?'live':''}"><i></i>${dataMode==='live'?'داده زنده':'پیش‌نمایش با داده نمونه'}</span><a class="subscription-link" href="${subscriptionUrl}" target="_blank" rel="noreferrer">دریافت اشتراک</a></div>
      </div>
    </header>
    <main class="page-wrap">
      <section class="intro">
        <div><div class="eyebrow">جست‌وجو و دریافت کانفیگ</div><h1>اتصال مناسب‌ات را پیدا کن.</h1><p>اطلاعات کامل کانفیگ و فایل اصلی حفظ می‌شود؛ خلاصه‌ها فقط برای مرور سریع‌اند.</p></div>
        <div class="intro-stats"><div><strong>${stats.total}</strong><span>مورد فهرست‌شده</span></div><div><strong>${stats.tested}</strong><span>دارای زمان اتصال</span></div><div><strong>${stats.fresh}</strong><span>بررسی اخیر</span></div></div>
      </section>
      <nav class="view-switch" aria-label="بخش‌های سایت">
        <button class="view-tab ${activeView==='servers'?'active':''}" data-view="servers">سرورها <span>${stats.total}</span></button>
        <button class="view-tab ${activeView==='telegram'?'active':''}" data-view="telegram">پیش‌نمایش تلگرام</button>
        <a class="channel-link" href="https://t.me/myvpn1404" target="_blank" rel="noreferrer">کانال اصلی ↗</a>
      </nav>
      ${activeView === 'servers' ? renderServers() : renderTelegram()}
      <footer class="footer"><span>زمان اتصال TCP، نتیجه اتصال کامل VPN نیست.</span><a href="https://github.com/mostafa5804/Myvpn1404" target="_blank" rel="noreferrer">مشاهده پروژه در GitHub</a></footer>
    </main>
    <div id="toast" class="toast" role="status" aria-live="polite"></div>
  `;
  bindEvents();
}
function renderServers() {
  const items = getFiltered();
  const countries = [...new Set(allItems().map(x=>x.country).filter(Boolean))].sort();
  const selectedCount = selected.size;
  return `
    <section class="workspace" aria-label="جست‌وجوی سرورها">
      <aside class="filters">
        <div class="filter-title"><h2>فیلترها</h2><button id="resetFilters" class="text-button">پاک‌کردن</button></div>
        <label class="field-label" for="countrySelect">کشور</label><select id="countrySelect" class="native-select"><option value="ALL">همه کشورها</option>${countries.map(c=>`<option value="${escapeHTML(c)}" ${countryFilter===c?'selected':''}>${escapeHTML(c)}</option>`).join('')}</select>
        <label class="field-label" for="statusSelect">وضعیت بررسی</label><select id="statusSelect" class="native-select"><option value="ALL">همه وضعیت‌ها</option><option value="TESTED" ${statusFilter==='TESTED'?'selected':''}>دارای زمان اتصال</option><option value="FRESH" ${statusFilter==='FRESH'?'selected':''}>بررسی‌شده در ساعت اخیر</option><option value="FAVORITES" ${statusFilter==='FAVORITES'?'selected':''}>علاقه‌مندی‌ها</option></select>
        <div class="filter-note"><p>زمان ثبت‌شده، اتصال TCP است؛ تضمین کارکرد در برنامه مقصد نیست.</p></div>
      </aside>
      <section class="results">
        <div class="search-row">
          <label class="sr-only" for="searchBox">جست‌وجو بر اساس کشور، پروتکل یا کانال</label>
          <input id="searchBox" class="search-field" type="search" placeholder="کشور، پروتکل یا نام کانال را جست‌وجو کن" value="${escapeHTML(query)}" autocomplete="off">
          <label class="sr-only" for="sortSelect">ترتیب نمایش</label><select id="sortSelect" class="native-select sort-select"><option value="fresh" ${sortMode==='fresh'?'selected':''}>تازه‌ترین</option><option value="latency" ${sortMode==='latency'?'selected':''}>کمترین زمان اتصال</option><option value="country" ${sortMode==='country'?'selected':''}>کشور</option></select>
        </div>
        <div class="protocol-row" role="group" aria-label="فیلتر پروتکل">
          ${[['ALL','همه'],['VLESS','VLESS'],['VMESS','VMess'],['TROJAN','Trojan'],['MTPROXY','MTProxy'],['MORE','سایر پروتکل‌ها'],['FILE','فایل‌ها']].map(([v,l])=>`<button class="protocol-chip ${protocolFilter===v?'active':''}" data-protocol="${v}">${l}</button>`).join('')}
        </div>
        <div class="list-toolbar"><p><strong>${items.length}</strong> نتیجه <span>· انتخاب‌شده: ${selectedCount}</span></p><div class="bulk-actions"><button id="selectVisible" class="text-button">انتخاب نتایج</button><button id="copySelected" class="secondary-action" ${selectedCount?'':'disabled'}>کپی کامل ${selectedCount||''}</button></div></div>
        ${items.length ? `<div class="server-grid">${items.map(renderCard).join('')}</div>` : `<div class="empty-state"><h2>نتیجه‌ای پیدا نشد</h2><p>عبارت یا فیلترها را تغییر بده.</p><button id="emptyReset">پاک‌کردن فیلترها</button></div>`}
      </section>
    </section>`;
}
function renderCard(item) {
  const latency = connectionLabel(item);
  const selectedState = selected.has(item.id);
  const isFav = favorites.has(item.id);
  const deliveryLink = item.kind === 'file' ? (item.outputLink || item.t_link || item.link) : item.t_link;
  return `<article class="server-card">
    <div class="card-top"><label class="select-control"><input type="checkbox" data-select="${item.id}" ${selectedState?'checked':''}><span>انتخاب برای بسته تلگرام</span></label><button class="icon-action ${isFav?'favorited':''}" aria-label="${isFav?'حذف از':'افزودن به'} علاقه‌مندی‌ها" data-favorite="${item.id}">${isFav?'★':'☆'}</button></div>
    <div class="server-heading"><span class="country-flag" aria-hidden="true">${escapeHTML(item.flag||'🌐')}</span><div class="server-name"><h3>${escapeHTML(item.country || item.name || 'فایل کانفیگ')}</h3><p>${escapeHTML(item.channel || 'منبع ثبت نشده')}</p></div><span class="badge">${escapeHTML(item.protocol)}</span></div>
    <div class="meta-line"><span class="latency ${latency.cls}"><i></i>${escapeHTML(latency.text)}</span><span class="freshness">${escapeHTML(freshness(item.ts))}</span></div>
    ${item.kind==='file' ? `<div class="file-preserve"><span>${escapeHTML(item.name)}<small>فایل اصلی — بدون تبدیل یا خلاصه</small></span></div>` : `<details class="full-config"><summary>نمایش متن کامل کانفیگ</summary><code dir="ltr">${escapeHTML(item.fullText)}</code></details>`}
    <div class="card-actions">${item.kind==='file' ? `<a class="primary-action" href="${escapeHTML(deliveryLink||'#')}" target="_blank" rel="noreferrer">بازکردن پیام فایل</a>` : `<button class="primary-action" data-copy="${item.id}">کپی کامل</button><button class="secondary-action" data-add="${item.id}">${selectedState?'حذف از بسته':'افزودن به بسته'}</button>`}</div>
    ${item.sourceLink?`<a class="source-link" href="${escapeHTML(item.sourceLink)}" target="_blank" rel="noreferrer">مشاهده پیام منبع ↗</a>`:''}
  </article>`;
}
function selectedItems() { return allItems().filter(x=>selected.has(x.id)); }
function summaryText(items) {
  const countBy = {};
  items.forEach(i=>countBy[i.protocol]=(countBy[i.protocol]||0)+1);
  const list = Object.entries(countBy).map(([name,n])=>`• ${name}: ${n} مورد`).join('\n');
  return `📡 فهرست اتصال‌های بررسی‌شده\n\n${items.length} مورد در این بسته قرار دارد.\n${list}\n\nمتن کامل هر کانفیگ و فایل اصلی در پیام‌های بعدی همین بسته حفظ شده است.\nفهرست زنده و جست‌وجو: ${location.origin}${location.pathname}\nاشتراک کامل: ${subscriptionUrl}`;
}
function formatPostDate(ts) {
  if (!ts) return 'زمان ثبت نشده';
  return new Intl.DateTimeFormat('fa-IR', {dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Tehran'}).format(new Date(Number(ts)*1000));
}
function protocolIcon(item) {
  if (item.kind === 'file') return '📎';
  if (item.kind === 'proxy') return '🔵';
  return ({VLESS:'🔮', VMESS:'🔷', TROJAN:'🛡️', SS:'🔐', HY2:'⚡', TUIC:'🚀'}[item.protocol] || '🔐');
}
function renderTelegramPost(item, index) {
  const status = connectionLabel(item);
  const outputLink = item.outputLink || item.t_link || '';
  const sourceLink = item.sourceLink || '';
  const title = item.kind === 'file' ? item.name : (item.country || 'Global');
  const content = item.kind === 'file'
    ? `<div class="telegram-file-card"><span class="file-icon">${escapeHTML((item.ext || 'FILE').slice(0,4))}</span><span class="file-title"><strong>${escapeHTML(item.name || 'فایل اصلی')}</strong><small>پیوست اصلی · نام فایل حفظ شده</small></span><span class="file-size">${escapeHTML(item.ext || 'FILE')}</span></div>${item.original_caption ? `<pre class="telegram-caption" dir="auto">${escapeHTML(item.original_caption)}</pre><button class="telegram-copy caption-copy" data-copy-caption="${item.id}">▢ کپی کپشن کامل</button>` : `<p class="telegram-no-caption">این فایل در پیام مبدأ کپشن نداشت.</p>`}`
    : `<div class="telegram-code-shell"><pre dir="ltr"><code>${escapeHTML(item.fullText)}</code></pre><button class="telegram-copy" data-copy="${item.id}"><span aria-hidden="true">▢</span> کپی متن کامل</button></div>${item.kind === 'proxy' ? `<a class="telegram-connect" href="${escapeHTML(item.fullText)}" target="_blank" rel="noreferrer">اتصال به MTProxy <span aria-hidden="true">↗</span></a>` : ''}`;
  return `<article class="telegram-post" id="tg-post-${item.id}">
    <div class="post-author"><span class="post-avatar">VPN</span><span class="post-author-name"><strong>VPN | کانفیگ ملی‌شکن</strong><small>${escapeHTML(formatPostDate(item.ts))}</small></span><span class="post-sequence">${String(index+1).padStart(2,'0')}</span></div>
    <div class="tg-bubble">
      <div class="post-title"><span>${protocolIcon(item)}</span><strong>${escapeHTML(item.kind === 'file' ? 'فایل کانفیگ' : item.protocol)}</strong><span class="post-country">${escapeHTML(title)}</span></div>
      ${content}
      <div class="post-meta"><span class="latency ${status.cls}"><i></i>${escapeHTML(status.text)}</span><span class="freshness">${escapeHTML(freshness(item.ts))}</span></div>
      ${item.kind !== 'file' ? `<div class="post-tags"><span>#${escapeHTML(item.protocol.toLowerCase())}</span><span>#vpn</span></div>` : ''}
      <div class="post-divider"></div>
      <div class="post-links">${sourceLink ? `<a href="${escapeHTML(sourceLink)}" target="_blank" rel="noreferrer">📡 منبع: ${escapeHTML(item.channel || 'پیام اصلی')} ↗</a>` : `<span>📡 منبع: ${escapeHTML(item.channel || 'ثبت‌نشده')}</span>`}${outputLink ? `<a href="${escapeHTML(outputLink)}" target="_blank" rel="noreferrer">🔗 پیام در کانال ↗</a>` : ''}</div>
      ${item.kind !== 'file' ? `<div class="post-timestamp">${item.kind === 'proxy' ? 'لینک کامل و مستقیم اتصال در کادر بالا حفظ شده است.' : 'متن کامل داخل کادر آمده؛ پیام خلاصه‌ای جایگزین کانفیگ نشده است.'}</div>` : ''}
    </div>
  </article>`;
}
function renderTelegram() {
  const items = selectedItems();
  const configs = items.filter(x=>x.kind!=='file');
  return `<section class="telegram-workspace">
    <div class="telegram-intro"><div class="telegram-icon" aria-hidden="true">TG</div><div><div class="eyebrow">پیش‌نمایش کانال</div><h2>هر مورد، یک پیام کامل و مرتب</h2><p>کادر کانفیگ، لینک منبع، زمان اتصال و فایل اصلی را همان‌طور که در کانال دیده می‌شوند بررسی کن.</p></div></div>
    ${items.length ? `<div class="telegram-layout">
      <aside class="message-index"><div class="index-heading"><strong>پیام‌های انتخاب‌شده</strong><span>${items.length}</span></div><div class="index-list">${items.map((item,i)=>`<button class="index-item" data-jump="${item.id}"><span class="index-number">${String(i+1).padStart(2,'0')}</span><span class="index-copy"><strong>${escapeHTML(item.kind==='file'?item.name:`${item.flag||''} ${item.protocol}`)}</strong><small>${escapeHTML(item.country || item.channel || 'Global')}</small></span><span class="index-kind">${item.kind==='file'?'فایل':'پیام'}</span></button>`).join('')}</div><div class="index-actions"><button id="copyAllFull" class="secondary-action" ${configs.length?'':'disabled'}>کپی متن کامل کانفیگ‌ها</button><button id="downloadPackage" class="text-button">دانلود متن و کپشن‌ها ↓</button></div></aside>
      <div class="telegram-window"><header class="telegram-window-head"><span class="channel-avatar">V</span><span class="channel-name"><strong>VPN | کانفیگ ملی‌شکن</strong><small>پیش‌نمایش ${items.length} پیام انتخاب‌شده</small></span><a href="https://t.me/myvpn1404" target="_blank" rel="noreferrer">بازکردن کانال ↗</a></header><div class="telegram-feed"><div class="feed-date">پیام‌های کامل · ${items.length} مورد</div>${items.map(renderTelegramPost).join('')}</div></div>
    </div>` : `<div class="telegram-empty"><div class="empty-icon">↗</div><h3>هنوز پیامی انتخاب نشده</h3><p>از فهرست سرورها موردها را انتخاب کن. بعد اینجا هر پیام را با قالب واقعی کانال می‌بینی؛ کانفیگ کامل در کادر کپی‌پذیر می‌ماند.</p><button id="loadDemoSelection" class="primary-action">دیدن پیش‌نمایش نمونه</button></div>`}
    <aside class="preservation-rule"><span>🔒</span><p><strong>قانون انتشار:</strong> متن کامل کانفیگ در کادر خودش می‌آید؛ فایل با پیوست و نام اصلی می‌ماند. خلاصه جای پیام کامل را نمی‌گیرد.</p></aside>
    <button class="text-button back-to-results" data-view="servers">بازگشت به انتخاب سرورها</button>
  </section>`;
}
function notify(message) {
  const toast = document.querySelector('#toast');
  if (!toast) return;
  toast.textContent = message; toast.classList.add('visible');
  setTimeout(()=>toast.classList.remove('visible'),2400);
}
async function copyText(text, done='کپی شد') {
  try { await navigator.clipboard.writeText(text); notify(done); }
  catch { const el=document.createElement('textarea');el.value=text;document.body.append(el);el.select();document.execCommand('copy');el.remove();notify(done); }
}
function exportPackage(items) {
  const parts = [summaryText(items), '\n\n━━━━━━━━━━ متن کامل کانفیگ‌ها ━━━━━━━━━━\n'];
  let n=0;
  for (const item of items) {
    n++;
    if (item.kind==='file') parts.push(`\n[فایل اصلی ${n}] ${item.name}\nلینک پیام اصلی: ${item.link}\nکپشن اصلی:\n${item.original_caption || '(بدون کپشن)'}\nفایل باینری در پیام جداگانه کانال ارسال می‌شود.\n`);
    else parts.push(`\n[کانفیگ کامل ${n}] ${item.country||item.protocol} / ${item.protocol}\n${item.fullText}\nمنبع: ${item.channel||'ثبت نشده'}\n`);
  }
  const blob = new Blob([parts.join('')], {type:'text/plain;charset=utf-8'});
  const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`vpn-hub-full-${new Date().toISOString().slice(0,10)}.txt`;a.click();URL.revokeObjectURL(url);
}
function bindEvents() {
  document.querySelectorAll('[data-view]').forEach(el=>el.addEventListener('click',()=>{activeView=el.dataset.view;render();}));
  document.querySelectorAll('[data-protocol]').forEach(el=>el.addEventListener('click',()=>{protocolFilter=el.dataset.protocol;render();}));
  document.querySelector('#searchBox')?.addEventListener('input',e=>{const caret=e.target.selectionStart;query=e.target.value||'';render();const field=document.querySelector('#searchBox');field?.focus();field?.setSelectionRange(caret,caret);});
  document.querySelector('#countrySelect')?.addEventListener('change',e=>{countryFilter=e.target.value;render();});
  document.querySelector('#statusSelect')?.addEventListener('change',e=>{statusFilter=e.target.value;render();});
  document.querySelector('#sortSelect')?.addEventListener('change',e=>{sortMode=e.target.value;render();});
  document.querySelector('#resetFilters')?.addEventListener('click',()=>{protocolFilter='ALL';countryFilter='ALL';statusFilter='ALL';sortMode='fresh';query='';render();});
  document.querySelector('#emptyReset')?.addEventListener('click',()=>{protocolFilter='ALL';countryFilter='ALL';statusFilter='ALL';query='';render();});
  document.querySelector('#selectVisible')?.addEventListener('click',()=>{getFiltered().forEach(x=>selected.add(x.id));render();});
  document.querySelectorAll('[data-select]').forEach(el=>el.addEventListener('change',()=>{el.checked?selected.add(el.dataset.select):selected.delete(el.dataset.select);render();}));
  document.querySelectorAll('[data-favorite]').forEach(el=>el.addEventListener('click',()=>{const id=el.dataset.favorite;favorites.has(id)?favorites.delete(id):favorites.add(id);localStorage.setItem('vpnHubFavorites',JSON.stringify([...favorites]));render();}));
  document.querySelectorAll('[data-copy]').forEach(el=>el.addEventListener('click',()=>{const item=allItems().find(x=>x.id===el.dataset.copy);if(item)copyText(item.fullText,'متن کامل کپی شد');}));
  document.querySelectorAll('[data-copy-caption]').forEach(el=>el.addEventListener('click',()=>{const item=allItems().find(x=>x.id===el.dataset.copyCaption);if(item)copyText(item.original_caption||'','کپشن اصلی کپی شد');}));
  document.querySelectorAll('[data-add]').forEach(el=>el.addEventListener('click',()=>{selected.has(el.dataset.add)?selected.delete(el.dataset.add):selected.add(el.dataset.add);render();}));
  document.querySelectorAll('[data-jump]').forEach(el=>el.addEventListener('click',()=>document.querySelector(`#tg-post-${CSS.escape(el.dataset.jump)}`)?.scrollIntoView({behavior:'smooth',block:'center'})));
  document.querySelector('#copySelected')?.addEventListener('click',()=>copyText(selectedItems().filter(x=>x.kind!=='file').map(x=>x.fullText).join('\n'),'متن کامل موارد انتخاب‌شده کپی شد'));
  document.querySelector('#copyAllFull')?.addEventListener('click',()=>copyText(selectedItems().filter(x=>x.kind!=='file').map(x=>x.fullText).join('\n'),'تمام متن‌های کامل کپی شدند'));
  document.querySelector('#downloadPackage')?.addEventListener('click',()=>exportPackage(selectedItems()));
  document.querySelector('#loadDemoSelection')?.addEventListener('click',()=>{const demo=allItems();[...demo.filter(x=>x.kind==='config').slice(0,2),...demo.filter(x=>x.kind==='proxy').slice(0,1),...demo.filter(x=>x.kind==='file').slice(0,1)].forEach(x=>selected.add(x.id));activeView='telegram';render();});
  document.querySelector('#searchBox')?.addEventListener('keydown',e=>{if(e.key==='Escape'){query='';render();}});
}

async function loadData() {
  try {
    const response = await fetch('./data.json', {cache:'no-store'});
    if (!response.ok) throw new Error('data.json is unavailable');
    const incoming = await response.json();
    if (Array.isArray(incoming.configs) || Array.isArray(incoming.proxies) || Array.isArray(incoming.files)) {
      database = incoming; dataMode='live';
    }
  } catch { /* Standalone preview keeps a clearly labeled sample dataset. */ }
  render();
}
loadData();
