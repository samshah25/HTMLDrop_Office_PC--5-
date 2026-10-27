"""
Mumbai sales-head view (v4, Sarvesh 2026-09-28): the MAIN Mumbai dashboard, simplified for a JDA head, as a separate page.

History: v1 (own 5-page design) too complicated; v2 (one page of lists) not useful; v3 (main dashboard + a summary and a
"where to send" list on top) "just more scrolls -- a JDA head identifies pincodes from the table". So v4 puts the effort
into the pincode table itself and adds nothing above it:
  * a plain-words Status column on every row, and the table opens sorted "needs action first, most JDS deals first",
    so the table IS the where-to-go list;
  * plain column names, fewer default columns, pincode + place stay put while scrolling sideways, a taller table;
  * analyst controls hidden (colours, band settings, column picker, per-column filter arrows, PDF, colour strip,
    advanced column); plain category names; long notes folded; opens on this month (month to date).
The main dashboard file is only READ. Output: Mumbai\\JDA_Mumbai_Sales_Head_Dashboard.html
Run after the daily refresh (run_daily.bat does it):   python tools\\build_sales_head.py
(Earlier builders / templates are kept alongside as *_v1_full / *_v2_simple.)
"""
import os
import re

TOOLS = os.path.dirname(os.path.abspath(__file__))
MUMBAI = os.path.dirname(TOOLS)
SRC_PAGE = os.path.join(MUMBAI, "JDA_JDS_Mumbai_Pincode_Dashboard_Lite_SubVertical.page")
OUT = os.path.join(MUMBAI, "JDA_Mumbai_Sales_Head_Dashboard.html")

HEAD = r"""
<script>window.__headInitialHash = location.hash;  /* read before the page rewrites the link */</script>
<style>
/* ---- sales-head view ---- */
#colorPanelToggle, #colorPanel, #bandSettingsBtn, #bandEditor, #columnPanelToggle, #columnPanel, #exportPdfBtn, #viewAllBtn,
.strip-bar, .col-filter-icon, #scenarioNote, .adv-col { display: none !important; }
/* the table is the page: taller, no room reserved for the hidden filter arrows, pincode + place stay put sideways */
.panel .scroll:has(> #dataTable) { max-height: 72vh; }
#dataTable th { padding-bottom: 10px; }
#dataTable tr:not(.expand-row) > :nth-child(1) { position: sticky; left: 0; z-index: 1; background: var(--panel); }
#dataTable tr:not(.expand-row) > :nth-child(2) { position: sticky; left: 22px; z-index: 1; background: var(--panel); }
#dataTable tr:not(.expand-row) > :nth-child(3) { position: sticky; left: 102px; z-index: 1; background: var(--panel); box-shadow: 1px 0 0 var(--border); }
#dataTable thead tr > th:nth-child(-n+3) { z-index: 3; }
/* the Status column says it in words, so no purple tint on Visiting-not-closing rows; fixed cells follow the hover shade */
#dataTable tr.gap-row { background: none; }
#dataTable tbody tr:not(.expand-row):hover > :nth-child(-n+3) { background: color-mix(in srgb, var(--panel2) 70%, var(--panel)); }
.st-pill { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.st-pill::before { content: ""; width: 9px; height: 9px; border-radius: 50%; background: var(--k); flex-shrink: 0; }
.st-pill.act { color: var(--text); }
.st-pill.calm { color: var(--text-dim); font-weight: 500; }
/* one click = details in place: whole rows are the click target; manager names are plain text (the row opens) */
#dataTable tbody tr[data-pincode] { cursor: pointer; }
.perf-mgr-link { color: inherit !important; cursor: pointer; }
.who { display: inline-block; max-width: 100%; margin: 10px 0 2px; padding: 12px 14px; background: var(--panel); border: 1px solid var(--border); border-radius: 4px; }
.who h4 { margin: 0 0 8px; font-family: var(--font-display); font-size: 14px; font-weight: 600; }
.who table { width: auto; min-width: 520px; font-size: 12.5px; border-collapse: collapse; }
.who td, .who th { padding: 4px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; text-align: left; }
.who th { color: var(--text-dim); font-weight: 600; position: static; background: none; cursor: default; }
.who td.n, .who th.n { text-align: right; }
.who .mgr td { color: var(--text-dim); font-weight: 600; padding-top: 8px; }
.who .miss { margin-top: 8px; color: var(--text-dim); font-size: 12.5px; }
.team-go td { padding: 6px 12px 12px 26px !important; background: var(--panel2); }
/* ---- pincode page: a full view inside the same file; the dashboard is hidden while it shows ---- */
body.pin-mode > *:not(#pinPage):not(script):not(style):not(.theme-toggle) { display: none !important; }
#pinPage { display: none; }
body.pin-mode #pinPage { display: block; }
.pp { max-width: 1240px; margin: 0 auto; padding: 18px 28px 48px; }
.pp-nav { position: sticky; top: 0; z-index: 5; background: var(--bg); display: flex; align-items: center; gap: 10px; flex-wrap: wrap; padding: 10px 0; border-bottom: 1px solid var(--border); margin-bottom: 18px; }
.pp-nav .pos { color: var(--text-dim); font-size: 13px; margin-left: auto; }
.pp-nav .mini-btn { font-size: 14px; padding: 7px 13px; }
.pp-nav .mini-btn[disabled] { opacity: .4; cursor: default; }
.pp h1 { margin: 0; font-family: var(--font-display); font-size: 32px; font-weight: 600; line-height: 1.15; }
.pp h1 .pn { color: var(--text-dim); font-weight: 500; font-size: 24px; margin-left: 10px; }
.pp .pp-sub { color: var(--text-dim); margin: 6px 0 18px; }
.pp .pp-sub .st-pill { font-size: 14px; margin-right: 10px; }
.pp-nums { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 10px; margin-bottom: 22px; }
.pp-num { background: var(--panel); border-radius: 6px; padding: 12px 14px; }
.pp-num .l { color: var(--text-dim); font-size: 12.5px; }
.pp-num .v { font-family: var(--font-display); font-size: 26px; font-weight: 600; line-height: 1.15; margin-top: 2px; }
.pp-sec { background: var(--panel); border-radius: 6px; padding: 16px 18px; margin-bottom: 14px; }
.pp-sec > h2 { margin: 0 0 4px; font-family: var(--font-display); font-size: 19px; font-weight: 600; }
.pp-sec > .note { margin: 0 0 10px; }
.pp-sec .who { display: block; margin: 0; padding: 0; border: 0; background: none; }
.pp-sec .who h4 { display: none; }
.pp-cats { display: flex; flex-wrap: wrap; gap: 10px; }
.pp-months { display: grid; max-width: 900px; grid-template-columns: 110px minmax(0, 1fr) 230px; gap: 6px 12px; align-items: center; font-size: 13px; }
.pp-months .pp-bar { display: flex; height: 14px; border-radius: 3px; overflow: hidden; background: var(--panel2); }
.pp-months .pp-bar i { display: block; height: 100%; }
.pp-months .n { text-align: right; color: var(--text-dim); white-space: nowrap; }
.pp-key { display: flex; gap: 16px; font-size: 12.5px; color: var(--text-dim); margin-top: 10px; }
.pp-key i { display: inline-block; width: 11px; height: 11px; border-radius: 2px; vertical-align: -1px; margin-right: 6px; }
#dataTable tbody td.pin-expand-cell { color: var(--accent) !important; }
@media (max-width: 1100px) { .pp-nums { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (max-width: 700px) { .pp { padding: 12px 16px 40px; } .pp-nums { grid-template-columns: repeat(2, minmax(0, 1fr)); } .pp h1 { font-size: 25px; } .pp-months { grid-template-columns: 70px minmax(0, 1fr); } .pp-months .n { grid-column: 2; text-align: left; } }
.bench { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.bench th, .bench td { padding: 8px 10px; border-bottom: 1px solid var(--border); text-align: left; white-space: nowrap; }
.bench th { color: var(--text-dim); font-weight: 600; font-size: 12.5px; position: static; background: none; cursor: default; }
.bench td.n, .bench th.n { text-align: right; }
.bench td.me { font-family: var(--font-display); font-size: 17px; font-weight: 600; }
.bench .vd { font-weight: 600; }
.bench .vd.good { color: #3fbf7a; } .bench .vd.bad { color: #f07b6b; } .bench .vd.mid { color: var(--text-dim); }
[data-theme="light"] .bench .vd.good { color: #1f7f55; } [data-theme="light"] .bench .vd.bad { color: #c23b22; }
.bench svg { display: block; }
.room { margin: 12px 0 2px; padding: 10px 14px; border-left: 3px solid var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 3px; }
.bench-wrap { overflow-x: auto; }
details.fold { margin-top: 4px; }
details.fold > summary { cursor: pointer; font-family: var(--font-display); font-size: 17px; font-weight: 600; color: var(--text); padding: 4px 0; }
</style>
"""

JS = r"""
<script>
/* ---- sales-head view: Status column + "needs action first" order (same rules as the rest of this page) ---- */
(function () {
  const ORDER = ['gap', 'notpresent', 'band1', 'band2', 'band3', 'jdaonly', 'nosales', 'outside'];
  const PLAIN = { gap: 'Visiting, not closing', notpresent: 'Not visiting', nosales: 'Visited, no sales yet', jdaonly: 'Only JDA selling', outside: 'No activity' };
  const plain = k => PLAIN[k] || (k === 'band1' ? `JDA far behind (${cutoffs[1]}% or less)` : k === 'band2' ? `JDA ahead (over ${cutoffs[1]}%)` : k);
  const NEED = new Set(['gap', 'notpresent', 'band1']);
  // plain names on the chips and colour strip too
  cardShortLabel = plain;
  stripLabel = plain;
  // every row carries a sortable status rank: all "needs action" pincodes rank together (0), then doing well (1), then
  // no sales yet (2); the second sort key (JDS deals) then puts the biggest missed markets first across the whole group
  const GROUP = { gap: 0, notpresent: 0, band1: 0, band2: 1, band3: 1, jdaonly: 1, nosales: 2, outside: 2 };
  const _buildRows = buildRows;
  buildRows = function () { return _buildRows.apply(this, arguments).map(r => { r.status = GROUP[layerOf(r)] * 1e6 - r.jds_sales; return r; }); };
  Object.assign(COLUMN_LABELS, {
    status: 'Status', jda_sales: 'JDA deals', jds_sales: 'JDS deals', total_sales: 'All deals', jda_share_pct: 'JDA share',
    conversion_rate_pct: 'Conversion', days_since_last_jda_visit: 'Last JDA visit', presentation_count: 'Presentations',
    deployed_jda_count: 'Deployed JDAs',
  });
  Object.assign(COLUMN_HINTS, {
    status: 'Needs action first (Visiting, not closing / Not visiting / JDA far behind), then Doing well, then No sales yet',
    days_since_last_jda_visit: 'Days since a JDA last presented here',
  });
  COLUMN_WIDTHS.status = 160;
  CELL_RENDERERS.days_since_last_jda_visit = r => { const d = r.days_since_last_jda_visit; return d === null || d === undefined ? '<span style="color:var(--text-dim)">No visit</span>' : d === 0 ? 'Today' : `${d} day${d === 1 ? '' : 's'} ago`; };
  const SHORT = { band1: 'JDA far behind', band2: 'JDA ahead' };
  CELL_RENDERERS.status = r => { const k = layerOf(r); return `<span class="st-pill ${NEED.has(k) ? 'act' : 'calm'}" style="--k:var(--cat-${k})" title="${plain(k)}">${SHORT[k] || plain(k)}</span>`; };
  COLUMN_WIDTHS.conversion_rate_pct = 88;
  renderTableHead();

  // (1) ONE click on a pincode row = open that pincode's own page (capture phase: the page's own row handlers -- expand
  //     in place, and quietly filtering the managers section -- never run)
  document.querySelector('#dataTable tbody').addEventListener('click', e => {
    const row = e.target.closest('tr[data-pincode]');
    if (!row) return;
    e.stopPropagation();
    openPinPage(row.dataset.pincode, true);
  }, true);
  const escW = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const tc = v => String(v || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const nW = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  function whoWorked(pin) {
    const reps = {};
    daysBetween(periodFromDate, periodToDate).forEach(day => {
      Object.entries(((DAILY.rep_pin_pres_by_day || {})[day] || {})[pin] || {}).forEach(([id, k]) => { (reps[id] = reps[id] || { id, pres: 0, deals: 0 }).pres += k; });
      Object.entries(((DAILY.rep_pin_sales_by_day || {})[day] || {})[pin] || {}).forEach(([id, k]) => { (reps[id] = reps[id] || { id, pres: 0, deals: 0 }).deals += k; });
    });
    const roster = ((JDA_DEPLOYMENT || {}).deployed || {})[pin] || [];
    const onRoster = new Set(roster.map(e => String(e.id)));
    const byMgr = {};
    Object.values(reps).forEach(r => { const m = (EMP_META[r.id] || {}).manager || 'Unassigned'; (byMgr[m] = byMgr[m] || []).push(r); });
    const mgrs = Object.entries(byMgr).map(([m, l]) => ({ m, l: l.sort((a, b) => b.pres - a.pres || b.deals - a.deals), pres: l.reduce((a, r) => a + r.pres, 0), deals: l.reduce((a, r) => a + r.deals, 0) }))
      .sort((a, b) => b.pres - a.pres || b.deals - a.deals);
    const notSeen = roster.filter(e => !reps[e.id]);
    let h = `<div class="who"><h4>Who worked ${pin}, ${escW(periodLabel())}</h4>`;
    if (!mgrs.length) h += `<div class="note">No JDA presented or closed a deal here in this period.</div>`;
    else h += `<table><thead><tr><th>Manager / JDA</th><th class="n">Presentations</th><th class="n">JDA deals</th></tr></thead><tbody>`
      + mgrs.map(g => `<tr class="mgr"><td>${escW(tc(g.m))}</td><td class="n">${nW(g.pres)}</td><td class="n">${nW(g.deals)}</td></tr>`
        + g.l.map(r => `<tr><td style="padding-left:22px">${escW(tc((EMP_META[r.id] || {}).name || r.id))}${onRoster.has(String(r.id)) ? ' <span class="dep-tag">Deployed here</span>' : ''}</td><td class="n">${nW(r.pres)}</td><td class="n">${nW(r.deals)}</td></tr>`).join('')).join('')
      + `</tbody></table>`;
    if (notSeen.length) h += `<div class="miss">Deployed here but not seen in this period: ${notSeen.map(e => escW(tc(e.name))).join(', ')}.</div>`;
    return h + `</div>`;
  }
  const _expandRowHtml = expandRowHtml;
  expandRowHtml = function (r, colspan) {
    let html = _expandRowHtml(r, colspan);
    const tpl = document.createElement('template'); tpl.innerHTML = html;
    tpl.content.querySelectorAll('.expand-title').forEach(t => { if (/^JDA deployed here/.test(t.textContent.trim())) t.parentElement.remove(); });
    html = tpl.innerHTML;
    const k = html.lastIndexOf('</td></tr>');
    return k < 0 ? html : html.slice(0, k) + `<div style="padding:0 10px 10px">${whoWorked(r.pincode)}</div>` + html.slice(k);
  };

  // ---- the pincode page ----
  document.body.insertAdjacentHTML('afterbegin', '<div id="pinPage" aria-live="polite"></div>');
  let savedScroll = 0, pushed = false;
  try { history.scrollRestoration = 'manual'; } catch (e) { /* older browsers */ }
  function tableOrder() {   // the pincodes in exactly the order the table shows them (filters, search and sort)
    const q = (document.getElementById('searchBox').value || '').trim().toLowerCase();
    return currentRows.filter(r => !q || r.pincode.includes(q) || ((r.geo && r.geo.sample_place) || '').toLowerCase().includes(q)).slice().sort(multiCompare).map(r => r.pincode);
  }
  function monthsBlock(pin) {
    const out = [];
    const m0 = DAILY.window_start.slice(0, 7);
    for (let d = m0 + '-01'; d <= DAILY.window_end; ) {
      const m = d.slice(0, 7); let j = 0, s2 = 0, pr = 0;
      Object.entries(DAILY.daily_deals[currentScenario] || {}).forEach(([day, pm]) => { if (day.slice(0, 7) === m && pm[pin]) { j += pm[pin].jda_sales; s2 += pm[pin].jds_sales; } });
      Object.entries(DAILY.daily_presence || {}).forEach(([day, pm]) => { if (day.slice(0, 7) === m && pm[pin]) pr += pm[pin].count; });
      out.push({ m, j, s: s2, pr });
      const nd = new Date(m + '-01T00:00:00Z'); nd.setUTCMonth(nd.getUTCMonth() + 1); d = nd.toISOString().slice(0, 10);
    }
    const max = Math.max(1, ...out.map(x => x.j + x.s));
    const lbl = m => new Date(m + '-01T00:00:00Z').toLocaleDateString('en-GB', { month: 'short', year: 'numeric', timeZone: 'UTC' });
    return `<div class="pp-months">` + out.map(x => `<span>${lbl(x.m)}${x.m === DAILY.window_end.slice(0, 7) ? ' (so far)' : ''}</span>`
      + `<span class="pp-bar" title="JDA ${nW(x.j)}, JDS ${nW(x.s)}"><i style="width:${100 * x.j / max}%;background:var(--accent)"></i><i style="width:${100 * x.s / max}%;background:var(--text-dim)"></i></span>`
      + `<span class="n">JDA ${nW(x.j)} vs JDS ${nW(x.s)}, ${nW(x.pr)} pres.</span>`).join('') + `</div>`
      + `<div class="pp-key"><span><i style="background:var(--accent)"></i>JDA deals</span><span><i style="background:var(--text-dim)"></i>JDS deals</span></div>`;
  }
  // ---- benchmarking against pincodes with a similar MARKET (JDA + JDS deals in the same period); listings only as context ----
  const LIST = {}, PAID = {};
  Object.entries(MONETIZABLE_SUB_VERTICALS || {}).forEach(([p2, m]) => { let t = 0, pd = 0; Object.values(m).forEach(v => { t += v.total || 0; pd += v.paid || 0; }); LIST[p2] = t; PAID[p2] = pd; });
  const med = a => { const v = a.filter(x => x !== null && !Number.isNaN(x)).sort((x, y) => x - y); if (!v.length) return null; const h = Math.floor(v.length / 2); return v.length % 2 ? v[h] : (v[h - 1] + v[h]) / 2; };
  // rates under 1 get two decimals, so 0.15 per 1,000 doesn't read as 0.2 next to an estimate built from 0.15
  const fmtN = (v, pct) => v === null || v === undefined ? '—' : (Math.abs(v) < 1 && v !== 0 && !pct ? v.toFixed(2) : (Math.round(v * 10) / 10).toLocaleString('en-IN')) + (pct ? '%' : '');
  function benchBlock(pin) {
    const all = buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope);
    const mkt = r => r.jda_sales + r.jds_sales;
    const me = all.find(r => r.pincode === pin);
    if (!me) return '<p class="note">No data for this pincode in the period.</p>';
    if (mkt(me) === 0) return '<p class="note">No JDA or JDS deal was closed here in this period, so there is no market to compare it on yet. Pick a longer period to compare.</p>';
    const withMkt = all.filter(r => mkt(r) > 0);
    const sizes = withMkt.map(mkt).sort((a, b) => a - b);
    const cut = [sizes[Math.floor(sizes.length / 4)], sizes[Math.floor(sizes.length / 2)], sizes[Math.floor(3 * sizes.length / 4)]];
    const band = v => v < cut[0] ? 0 : v < cut[1] ? 1 : v < cut[2] ? 2 : 3;
    const myBand = band(mkt(me));
    const peers = withMkt.filter(r => band(mkt(r)) === myBand);
    const f = v => fmtN(v);
    const bandTxt = [`fewer than ${f(cut[0])}`, `${f(cut[0])} to ${f(cut[1])}`, `${f(cut[1])} to ${f(cut[2])}`, `${f(cut[2])} or more`][myBand];
    const M = [
      { l: 'JDA share of JDA + JDS deals', f: r => 100 * r.jda_sales / mkt(r), dir: 1, pct: true },
      { l: 'JDA conversion', f: r => r.presentation_count ? 100 * r.jda_sales / r.presentation_count : null, dir: 1, pct: true, note: 'JDA deals ÷ presentations' },
      { l: 'JDA deals', f: r => r.jda_sales, dir: 1 },
      { l: 'JDA presentations', f: r => r.presentation_count, dir: 1, note: 'the effort going in' },
      { l: 'Days since the last JDA visit', f: r => r.days_since_last_jda_visit ?? null, dir: -1, note: 'fewer is better' },
      { l: 'Paid % of listings', f: r => LIST[r.pincode] ? 100 * (PAID[r.pincode] || 0) / LIST[r.pincode] : null, dir: 1, pct: true, note: 'context only: monthly listings snapshot' },
    ];
    const strip = (vals, mine, pm) => {   // every similar-market pincode as a dot, the median as a tick, this pincode highlighted
      const v = vals.filter(x => x !== null && !Number.isNaN(x));
      if (mine === null || !v.length) return '';
      const lo = Math.min(...v, mine), hi = Math.max(...v, mine), W = 170, x = t => hi === lo ? W / 2 : 4 + (W - 8) * (t - lo) / (hi - lo);
      return `<svg width="${W}" height="18" aria-hidden="true"><line x1="4" x2="${W - 4}" y1="9" y2="9" stroke="var(--border)"/>`
        + v.map(t => `<circle cx="${x(t).toFixed(1)}" cy="9" r="2.6" fill="var(--text-dim)" opacity=".45"/>`).join('')
        + (pm !== null ? `<line x1="${x(pm).toFixed(1)}" x2="${x(pm).toFixed(1)}" y1="2" y2="16" stroke="var(--text)" stroke-width="1.5"/>` : '')
        + `<circle cx="${x(mine).toFixed(1)}" cy="9" r="5.5" fill="var(--accent)" stroke="var(--panel)" stroke-width="1.5"/></svg>`;
    };
    const rowsHtml = M.map(m => {
      const mine = m.f(me), pv = peers.map(m.f), pm = med(pv), bm = med(withMkt.map(m.f));
      let verdict = '<span class="vd mid">—</span>';
      if (mine !== null) {
        const v = pv.filter(x => x !== null), below = v.filter(x => x < mine).length, same = v.filter(x => x === mine).length;
        // mid-rank: ties sit in the middle of their run, so 'equal to the typical value' reads as Middle, not Bottom
        const pctl = v.length > 1 ? 100 * (below + (same - 1) / 2) / (v.length - 1) : 50;
        const good = m.dir === 1 ? pctl >= 75 : pctl <= 25, bad = m.dir === 1 ? pctl <= 25 : pctl >= 75;
        const pos = pctl >= 75 ? (m.dir === -1 ? 'Highest quarter' : 'Top quarter') : pctl <= 25 ? (m.dir === -1 ? 'Lowest quarter' : 'Bottom quarter') : 'Middle';
        verdict = `<span class="vd ${good ? 'good' : bad ? 'bad' : 'mid'}">${pos}</span> <span class="note">of similar markets</span>`;
      }
      return `<tr><td>${m.l}${m.note ? `<br><span class="note">${m.note}</span>` : ''}</td><td class="n me">${fmtN(mine, m.pct)}</td><td class="n">${fmtN(pm, m.pct)}</td><td class="n">${fmtN(bm, m.pct)}</td><td>${strip(pv, mine, pm)}</td><td>${verdict}</td></tr>`;
    }).join('');
    const peerShare = med(peers.map(r => 100 * r.jda_sales / mkt(r)));
    const expected = peerShare === null ? null : peerShare / 100 * mkt(me);
    let room = '';
    if (expected !== null && expected - me.jda_sales >= 1) room = `<div class="room"><b>Room to grow:</b> if JDA took a typical similar-market share (${fmtN(peerShare, true)}) of the ${fmtN(mkt(me))} JDA + JDS deals closed here, that would be about <b>${fmtN(expected)} JDA deals</b> instead of ${fmtN(me.jda_sales)}.</div>`;
    else if (expected !== null) room = `<div class="room">JDA's share here is at or above a typical similar-market pincode (${fmtN(peerShare, true)}).</div>`;
    const few = peers.length < 8 ? ` Only ${peers.length} similar pincodes in this period, so read the comparison with care.` : '';
    return `<p class="note">Compared with pincodes of a similar market size: the <b>${peers.length} Mumbai pincodes where ${bandTxt} JDA + JDS deals</b> were closed in the same period (${fmtN(mkt(me))} here).${few}</p>`
      + `<div class="bench-wrap"><table class="bench"><thead><tr><th>Measure</th><th class="n">This pincode</th><th class="n">Similar markets (typical)</th><th class="n">All Mumbai (typical)</th><th>Among similar markets</th><th></th></tr></thead><tbody>${rowsHtml}</tbody></table></div>`
      + room + `<p class="note" style="margin-top:8px">Typical = the median. In the dots, each grey dot is a similar-market pincode, the line is the typical value and the highlighted dot is this pincode. All Mumbai counts pincodes with at least one JDA or JDS deal in the period.</p>`;
  }
  window.openPinPage = function (pin, fromClick) {
    const r = currentRows.find(x => x.pincode === pin) || buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope).find(x => x.pincode === pin);
    if (!r) return;
    if (!document.body.classList.contains('pin-mode')) savedScroll = window.scrollY;
    const order = tableOrder(), idx = order.indexOf(pin);
    const k = layerOf(r);
    const place = (r.geo && r.geo.sample_place) || ((DATA.pincode_static[pin] || {}).geo || {}).sample_place || 'Pincode';
    const tpl = document.createElement('template'); tpl.innerHTML = expandRowHtml(r, 1);
    const td = tpl.content.querySelector('td'); const blocks = td ? td.innerHTML : '';
    const holder = document.createElement('template'); holder.innerHTML = blocks;
    const who = holder.content.querySelector('.who'); const whoHtml = who ? who.outerHTML : '';
    if (who) who.parentElement.remove();
    const catsHtml = holder.innerHTML;
    const num = (l, v) => `<div class="pp-num"><div class="l">${l}</div><div class="v">${v}</div></div>`;
    const d = r.days_since_last_jda_visit;
    document.getElementById('pinPage').innerHTML = `<div class="pp">
      <div class="pp-nav">
        <button class="mini-btn" type="button" data-pp="back">← Back to all pincodes</button>
        <button class="mini-btn" type="button" data-pp="prev" ${idx > 0 ? '' : 'disabled'}>‹ Previous</button>
        <button class="mini-btn" type="button" data-pp="next" ${idx >= 0 && idx < order.length - 1 ? '' : 'disabled'}>Next ›</button>
        <span class="pos">${idx >= 0 ? `${idx + 1} of ${order.length} in the table's order` : ''}</span>
      </div>
      <h1>${escW(place)}<span class="pn">${pin}</span></h1>
      <p class="pp-sub"><span class="st-pill ${NEED.has(k) ? 'act' : 'calm'}" style="--k:var(--cat-${k})">${plain(k)}</span>${escW(periodLabel())}${currentScenario !== 'all' ? (currentScenario === 'fresh' ? ', Fresh deals only' : ', Renewal deals only') : ''}</p>
      <div class="pp-nums">
        ${num('JDA deals', nW(r.jda_sales))}${num('JDS deals', nW(r.jds_sales))}${num('JDA share', r.jda_share_pct === null || r.jda_share_pct === undefined ? '—' : nW(r.jda_share_pct) + '%')}
        ${num('Presentations', nW(r.presentation_count))}${num('Conversion', r.conversion_rate_pct === null || r.conversion_rate_pct === undefined ? '—' : nW(r.conversion_rate_pct) + '%')}
        ${num('Last JDA visit', d === null || d === undefined ? 'No visit' : d === 0 ? 'Today' : `${d} day${d === 1 ? '' : 's'} ago`)}${num('Deployed JDAs', nW(r.deployed_jda_count || 0))}
      </div>
      <section class="pp-sec"><h2>How it compares</h2>${benchBlock(pin)}</section>
      <section class="pp-sec"><h2>Who worked this pincode</h2><p class="note">Managers and their JDAs, from their own presentations and deals in this period.</p>${whoHtml}</section>
      <section class="pp-sec"><h2>Business categories</h2><p class="note">Deals closed here in this period, and the listings available (monthly snapshot). Hover a row for its sales groups.</p><div class="pp-cats">${catsHtml}</div></section>
      <section class="pp-sec"><h2>Month by month</h2><p class="note">JDA vs JDS deals in this pincode for every month in the data, whatever period is selected.</p>${monthsBlock(pin)}</section>
    </div>`;
    document.body.classList.add('pin-mode');
    window.scrollTo(0, 0);
    const url = new URL(location.href); url.searchParams.set('pin', pin);
    if (fromClick && !pushed) { history.pushState({ pinPage: pin }, '', url); pushed = true; }
    else history.replaceState({ pinPage: pin }, '', url);
    document.querySelector('#pinPage [data-pp="back"]').focus();
  };
  function closePinPage(viaHistory) {
    if (!document.body.classList.contains('pin-mode')) return;
    document.body.classList.remove('pin-mode');
    document.getElementById('pinPage').innerHTML = '';
    if (!viaHistory) {
      if (pushed) { pushed = false; history.back(); }
      else { const url = new URL(location.href); url.searchParams.delete('pin'); history.replaceState(null, '', url); }
    } else pushed = false;
    const y = savedScroll;
    window.scrollTo(0, y);
    requestAnimationFrame(() => window.scrollTo(0, y));   // after the dashboard is laid out again
  }
  document.getElementById('pinPage').addEventListener('click', e => {
    const b = e.target.closest('[data-pp]'); if (!b || b.disabled) return;
    if (b.dataset.pp === 'back') return closePinPage(false);
    const order = tableOrder(), idx = order.indexOf(new URL(location.href).searchParams.get('pin'));
    const next = order[idx + (b.dataset.pp === 'next' ? 1 : -1)];
    if (next) openPinPage(next, false);
  });
  window.addEventListener('popstate', () => { if (!new URL(location.href).searchParams.get('pin')) closePinPage(true); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && document.body.classList.contains('pin-mode')) closePinPage(false); });

  // (2) category chips: a click shows ONLY that category; clicking it again shows every category (it used to hide it)
  const onlyOrAll = k => {
    const keys = renderedLayerKeys();
    const alone = keys.every(x => layerVisible[x] === (x === k));
    keys.forEach(x => { layerVisible[x] = alone ? true : x === k; });
    refreshAll();
  };
  const cards = document.getElementById('cards');
  cards.addEventListener('click', e => { const c = e.target.closest('.card.layer-card'); if (!c) return; e.stopPropagation(); onlyOrAll(c.dataset.layer); }, true);
  cards.addEventListener('keydown', e => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const c = e.target.closest('.card.layer-card'); if (!c) return;
    e.preventDefault(); e.stopPropagation();
    const k = c.dataset.layer; onlyOrAll(k);
    const again = document.querySelector(`.card.layer-card[data-layer="${k}"]`); if (again) again.focus();
  }, true);

  // (3) manager rows: ONE click opens the JDAs (the name no longer jumps you up to a filtered table). Changing the
  //     pincode table is an explicit, labelled button inside the opened manager.
  const _renderPerfView = renderPerfView;
  renderPerfView = function () {
    _renderPerfView.apply(this, arguments);
    if (perfView !== 'manager') return;
    document.querySelectorAll('#perfViewBody tr.perf-mgr-row').forEach(tr => {
      const mgr = tr.dataset.mgr;
      if (!expandedManagers.has(mgr)) return;
      let last = tr;
      while (last.nextElementSibling && last.nextElementSibling.classList.contains('perf-subrow')) last = last.nextElementSibling;
      last.insertAdjacentHTML('afterend', `<tr class="team-go"><td colspan="${tr.children.length}"><button type="button" class="mini-btn" data-team-pins="${escW(mgr)}">Show ${escW(tc(mgr))}'s pincodes in the table above</button></td></tr>`);
    });
  };
  document.getElementById('perfViewBody').addEventListener('click', e => {
    const b = e.target.closest('[data-team-pins]');
    if (b) { e.stopPropagation(); filterTableToManager(b.dataset.teamPins); return; }
    const link = e.target.closest('.perf-mgr-link');           // the name opens the manager like the rest of the row
    if (!link) return;
    e.preventDefault(); e.stopPropagation();
    if (perfView !== 'manager') return;
    const mgr = link.dataset.mgr;
    if (expandedManagers.has(mgr)) expandedManagers.delete(mgr); else expandedManagers.add(mgr);
    renderPerfView();
  }, true);

  // open on this month (month to date) unless the link carries its own view; every category shown
  if (!/(^|[#&])show=/.test(window.__headInitialHash || '')) {
    LAYER_KEYS.forEach(k => { layerVisible[k] = true; });
    setPeriod(DAILY.window_end.slice(0, 8) + '01', DAILY.window_end);
  } else refreshAll();
  const linkPin = new URL(location.href).searchParams.get('pin');
  if (linkPin) openPinPage(linkPin, false);
})();
</script>
"""


def transform(s, storage_key="jdaMumbaiHeadView", branch="Mumbai", src_key="jdaJdsMumbaiDashboard"):
    """All the sales-head changes applied to the main page's HTML (also reused by build_ui_lab.py)."""

    def rep(a, b, count=1):
        nonlocal s
        k = s.count(a)
        assert k == count, (a[:80], k)
        s = s.replace(a, b)

    # no 'anonymous' wording on the pages: those deals are counted as JDS by the refresh (2026-09-29)
    s = s.replace("B2B: ${row.b2b_count} &nbsp; Anonymous: ${row.anonymous_count}<br>", "B2B: ${row.b2b_count}<br>")
    s = re.sub(r"\(all teams [^)]*Anonymous\)", "(all teams)", s)
    s = s.replace("'b2b_count', 'anonymous_count', 'original_budget_sum',\n];", "'b2b_count', 'original_budget_sum',\n];")
    # identity: own title / heading, own browser storage (its settings never touch the main dashboard's)
    rep(f"<title>JDA vs JDS pincode coverage, {branch}</title>", f"<title>{branch} JDA, pincodes at a glance</title>")
    rep(f"JDA vs JDS pincode coverage, {branch} branch</h1>", f"{branch} JDA, pincodes at a glance</h1>", 2)
    s = s.replace(src_key, storage_key)
    # plain category names (hover tips / legend)
    i = s.index("const LAYER_LABELS = () => ({")
    j = s.index("});", i) + 3
    s = s[:i] + """const LAYER_LABELS = () => ({
  gap: 'Visiting, not closing',
  notpresent: 'Not visiting',
  nosales: 'Visited, no sales yet',
  jdaonly: 'Only JDA selling',
  band1: `JDA far behind (${cutoffs[1]}% or less)`,
  band2: `JDA ahead (over ${cutoffs[1]}%)`,
  band3: `JDA-share Band 3: > ${cutoffs[2]}%`,
  outside: 'No activity',
});""" + s[j:]
    rep('>JDA losing out</button>', '>Needs action</button>')
    rep('>JDA doing well</button>', '>Doing well</button>')
    # the table: Status column right after the place, fewer columns, "needs action first, most JDS deals" order
    rep("'pincode', 'place', 'state', 'jda_sales',", "'pincode', 'place', 'status', 'state', 'jda_sales',")
    rep("const DEFAULT_HIDDEN_COLUMNS = ['b2b_count', 'anonymous_count', 'original_budget_sum'];",
        "const DEFAULT_HIDDEN_COLUMNS = ['b2b_count', 'anonymous_count', 'original_budget_sum', 'state', 'total_sales', 'distinct_jda_employees', "
        "'deployed_presentations', 'monetizable_listings', 'rv3yr_sum', 'is_gap', 'split_rate_pct'];")
    rep("sortLevels = [{ field: 'jds_sales', dir: -1 }]", "sortLevels = [{ field: 'status', dir: 1 }]", 2)
    rep("<h3>All pincodes</h3>", "<h3>All pincodes</h3>\n    <p class=\"note\" style=\"margin:-4px 0 10px;\">Pincodes that need action come first, the ones where JDS sells the most at the top. Click a pincode to open its own page: who worked it, business categories and month by month. Back returns you here.</p>")
    rep("<h3>Manager &amp; JDA performance</h3>", "<h3>Your managers and JDAs</h3>")
    rep("Click a category to show or hide it.", "Click a category to see only those pincodes; click it again to see all.")
    rep("Click a column to sort. Click a row to see who worked that pincode. Exports match what's shown.", "Click a column heading to sort. Export CSV saves exactly what's shown.")
    rep("Counts only the pincodes shown in the table above, so it follows every filter. Click a pincode row above to split its figures by manager and JDA.",
        "Counts the pincodes shown in the table above. Click a manager to see their JDAs.")
    rep('title="Click ▸ on a row to see its top sub-verticals"', 'title="Click a pincode to open its page"')
    # long notes folded away
    rep("    <h3>Data quality notes</h3>\n    <div class=\"note\" id=\"dqNotes\"></div>",
        "    <details class=\"fold\"><summary>How this is counted</summary><div class=\"note\" id=\"dqNotes\"></div></details>")
    rep('<footer class="metrics">\n  <h3 style="padding-left:0;">How to use the filters and tools</h3>',
        '<footer class="metrics">\n  <details class="fold"><summary>How to use the filters and tools</summary>')
    rep("</footer>", "</details>\n</footer>")
    rep("</head>", HEAD + "</head>")
    k = s.rindex("</body>")
    return s[:k] + JS + s[k:]


def main():
    s = transform(open(SRC_PAGE, encoding="utf-8").read())
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, OUT)
    print(f"wrote {OUT} ({len(s) / 1e6:.1f} MB) from {os.path.basename(SRC_PAGE)}")


if __name__ == "__main__":
    main()
