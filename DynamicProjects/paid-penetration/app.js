// Data + components for the Paid Penetration dashboard.
// Needs portal_data.js loaded first (C, S, P, BM, BN, CP, CPS, fmt, aggr).

const $ = s => document.querySelector(s);
const SEGK = ['T', 'C', 'N', 'p1', 'p2', 'm', 'c1p0', 'c0p1'];
const BIZ = [['b2b', 'B2B'], ['b2c', 'B2C'], ['both', 'Hybrid']];
const OFF = [['prod', 'Products'], ['serv', 'Services'], ['mix', 'Both']];
const COL = { b2b: 'var(--b2b)', b2c: 'var(--b2c)', both: 'var(--both)' };

// ---------- filter state ----------
const ST = { loc: { t: 'all' }, biz: 'total', ps: 'all', vfl: false };
const subs = [];
const onChange = f => subs.push(f);
const emit = () => subs.forEach(f => f());
function setST(patch) { Object.assign(ST, patch); emit(); }

// ---------- data ----------
function mergeG(rows) {
  const g = {};
  rows.forEach(r => {
    for (const k in r.g || {}) {
      const v = g[k] || (g[k] = SEGK.map(() => 0));
      r.g[k].forEach((x, i) => v[i] += x);
    }
  });
  return g;
}
const STATES = S.map(s => {
  const cs = C.filter(c => c.s === s.id);
  return { id: s.id, n: s.n, r: s.r, cs, a: { ...aggr(cs), g: mergeG(cs) } };
}).filter(s => s.a.T > 0);
const SN = Object.fromEntries(STATES.map(s => [s.id, s]));
PA.g = mergeG(C);
BM.forEach(b => b.a.g = mergeG(b.cs.map(j => C[j])));

function keyMatch(key, biz, ps) {
  const [b, p, v] = key.split('|');
  if (v === 'V' && !ST.vfl) return false;
  return (biz === 'total' || b === biz.toUpperCase()) && (ps === 'all' || p === ps.toUpperCase());
}
// Metrics for a raw scope, limited to business / offering (defaults: current filters)
function met(raw, biz = ST.biz, ps = ST.ps) {
  const o = { ...raw };
  if (biz === 'total' && ps === 'all' && !ST.vfl) return o;
  SEGK.forEach(k => o[k] = 0);
  for (const k in raw.g || {}) if (keyMatch(k, biz, ps)) raw.g[k].forEach((v, i) => o[SEGK[i]] += v);
  return o;
}
const pen = o => o.m ? o.p1 / o.m * 100 : 0;
const cities = n => n + (n === 1 ? ' city' : ' cities');
const pct = (a, b, d = 1) => b ? (a / b * 100).toFixed(d) + '%' : '0%';

// A branch split into its main (hub) city or its remote cities: { t: 'part', id: branchKey, part: 'main' | 'remote' }
const PARTS = {};
function partRaw(id, part) {
  const k = id + '|' + part;
  if (!PARTS[k]) {
    const cs = BN[id].cs.map(j => C[j]).filter(c => part === 'main' ? !!c.h : !c.h);
    PARTS[k] = { ...aggr(cs), g: mergeG(cs), n: cs.length, hub: cs.find(c => c.h) };
  }
  return PARTS[k];
}
// Which cities belong to a location (a city counts as its whole branch, for map dots and the Cities table)
const inLoc = (loc = ST.loc) => loc.t === 'branch' ? (c => c.b === loc.id)
  : loc.t === 'part' ? (c => c.b === loc.id && (loc.part === 'main' ? !!c.h : !c.h))
  : loc.t === 'state' ? (c => c.s === loc.id)
  : loc.t === 'city' ? (c => c.b === C[loc.id].b) : (() => true);

function locRaw(loc = ST.loc) {
  if (loc.t === 'part') return partRaw(loc.id, loc.part);
  if (loc.t === 'city') return C[loc.id];
  if (loc.t === 'branch') return BN[loc.id].a;
  if (loc.t === 'state') return SN[loc.id].a;
  return PA;
}
function locName(loc = ST.loc) {
  if (loc.t === 'part') return BN[loc.id].n + (loc.part === 'main' ? ' · Main' : ' · Remote');
  if (loc.t === 'city') return C[loc.id].n;
  if (loc.t === 'branch') return BN[loc.id].n;
  if (loc.t === 'state') return SN[loc.id].n;
  return 'Pan India';
}
function locSub(loc = ST.loc) {
  if (loc.t === 'part') {
    const pr = partRaw(loc.id, loc.part);
    return loc.part === 'main' ? 'Main city of the ' + BN[loc.id].n + ' branch' : cities(pr.n) + ' outside the main city · ' + BN[loc.id].n + ' branch';
  }
  if (loc.t === 'city') { const c = C[loc.id]; return (c.h ? 'Main city' : 'Remote city') + ' · ' + BN[c.b].n + ' branch · ' + (SN[c.s] ? SN[c.s].n : c.s); }
  if (loc.t === 'branch') return BN[loc.id].r + ' region · ' + cities(BN[loc.id].cs.length);
  if (loc.t === 'state') return SN[loc.id].r + ' region · ' + cities(SN[loc.id].cs.length);
  return BM.length + ' branches · ' + C.length + ' cities';
}

// Deal financials (Total / Package / PDG / Others / Multi) for the location, honouring filters.
function deals(loc = ST.loc) {
  const z = () => ({ deals: 0, coll: 0, rv: 0, ecs: 0, ob: 0, ctr: 0 });
  const out = { Total: z(), Package: z(), PDG: z(), Others: z(), Multi: z(), hasEcs: false };
  const key = loc.t === 'branch' || loc.t === 'part' ? loc.id : loc.t === 'city' ? C[loc.id].b : 'all';
  for (const [k, blk] of Object.entries(CPS[key] || {})) {
    if (!keyMatch(k, ST.biz, ST.ps)) continue;
    for (const [name, v] of Object.entries(blk)) {
      const o = out[name];
      if (o) { o.deals += v[0]; o.coll += v[1]; o.rv += v[2]; o.ecs += v[3] || 0; o.ob += v[4] || 0; o.ctr += v[5] || 0; }
      if (v.length > 3) out.hasEcs = true;
    }
  }
  if (loc.t === 'state' || loc.t === 'city' || loc.t === 'part') {
    // No state/city-level deal table: scale Pan India (state) or the branch (city, main/remote) by share of paid listings
    const bA = loc.t === 'city' ? BN[C[loc.id].b].a : loc.t === 'part' ? BN[loc.id].a : PA;
    const r = met(locRaw(loc)).p1 / (met(bA).p1 || 1);
    for (const o of Object.values(out)) if (typeof o === 'object') { o.deals *= r; o.coll *= r; o.rv *= r; o.ecs *= r; o.ob *= r; o.ctr *= r; }
  }
  return out;
}

// ---------- tooltip ----------
const tipEl = document.createElement('div');
tipEl.className = 'tip';
document.addEventListener('DOMContentLoaded', () => document.body.appendChild(tipEl));
document.addEventListener('mousemove', e => {
  const t = e.target.closest && e.target.closest('[data-tip]');
  if (!t) { tipEl.classList.remove('o'); return; }
  tipEl.innerHTML = t.dataset.tip;
  tipEl.classList.add('o');
  const w = tipEl.offsetWidth, h = tipEl.offsetHeight;
  tipEl.style.left = Math.min(e.clientX + 14, innerWidth - w - 8) + 'px';
  tipEl.style.top = (e.clientY + 16 + h > innerHeight ? e.clientY - h - 12 : e.clientY + 16) + 'px';
});

// ---------- location picker ----------
// Branches -> (All | Main | Remote | a city), States, Cities. Names only.
const esc = t => String(t).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const CITY_LIST = C.map((c, i) => ({ i, c })).filter(o => o.c.T > 0).sort((a, b) => b.c.T - a.c.T);
const STATE_LIST = STATES.slice().sort((a, b) => a.n.localeCompare(b.n));
const PK = { open: false, tab: 'branch', q: '', drill: null, act: 0 };

function locPicker(root) {
  const cur = ST.loc;
  const label = cur.t === 'all' ? 'Pan India' : cur.t === 'part' ? BN[cur.id].n : locName(cur);
  const crumb = cur.t === 'all' ? '' : cur.t === 'branch' ? 'Branch' : cur.t === 'state' ? 'State'
    : cur.t === 'part' ? (cur.part === 'main' ? 'Main' : 'Remote') : BN[C[cur.id].b].n;
  root.innerHTML = `
    <button class="lt" aria-haspopup="listbox" aria-expanded="${PK.open}">
      <svg viewBox="0 0 24 24" class="pin"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
      <span class="ltx"><b>${esc(label)}</b>${crumb ? `<small>${esc(crumb)}</small>` : ''}</span>
      <svg viewBox="0 0 24 24" class="chev"><path d="m6 9 6 6 6-6"/></svg>
    </button>
    ${cur.t !== 'all' ? '<button class="lclr" title="Back to Pan India" aria-label="Back to Pan India">&times;</button>' : ''}
    <div class="lp" ${PK.open ? '' : 'hidden'}>
      <div class="lps"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input type="text" placeholder="Search branch, state or city" value="${esc(PK.q)}" aria-label="Search locations"></div>
      <div class="lpt">${[['branch', 'Branches'], ['state', 'States'], ['city', 'Cities']].map(([k, l]) =>
        `<button data-tab="${k}" aria-pressed="${PK.tab === k}">${l}</button>`).join('')}</div>
      <div class="lpl" role="listbox"></div>
    </div>`;

  const panel = root.querySelector('.lp'), list = root.querySelector('.lpl'), inp = root.querySelector('.lp input');
  let rows = [];
  const same = loc => cur.t === loc.t && cur.id === loc.id && cur.part === loc.part;
  const hl = n => {
    const q = PK.q.trim();
    return q ? esc(n).replace(new RegExp('(' + q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'ig'), '<mark>$1</mark>') : esc(n);
  };
  // act: { loc } selects a location, { drill } opens a branch
  const row = (name, act, aside = '') => {
    rows.push(act);
    const on = act.loc && same(act.loc);
    return `<div class="lr ${on ? 'on' : ''}" role="option" aria-selected="${!!on}" data-r="${rows.length - 1}">
      <span class="lnm">${hl(name)}</span>${aside ? `<span class="las">${aside}</span>` : ''}${act.drill ? '<span class="lgo">›</span>' : ''}</div>`;
  };
  const head = t => `<div class="lh">${t}</div>`;
  const india = () => row('Pan India', { loc: { t: 'all' } }, 'All branches').replace('class="lr ', 'class="lr all ');
  const branchRows = bs => bs.map(b => row(b.n, { drill: b.k })).join('');
  const stateRows = ss => ss.map(s => row(s.n, { loc: { t: 'state', id: s.id } })).join('');
  const cityRows = cs => cs.map(o => row(o.c.n, { loc: { t: 'city', id: o.i } }, esc(SN[o.c.s] ? SN[o.c.s].n : o.c.s))).join('');

  const drawList = () => {
    rows = [];
    const q = PK.q.trim().toLowerCase();
    let h = '';
    if (PK.drill && !q) {
      const b = BN[PK.drill], main = partRaw(b.k, 'main'), rem = partRaw(b.k, 'remote');
      const cs = CITY_LIST.filter(o => o.c.b === b.k).sort((x, y) => (y.c.h || 0) - (x.c.h || 0));
      const chip = (loc, t) => `<button class="lch ${same(loc) ? 'on' : ''}" data-loc='${JSON.stringify(loc)}'>${t}</button>`;
      h = `<button class="lback">‹ Branches</button><div class="lbt">${esc(b.n)}</div>
        <div class="lchs">${chip({ t: 'branch', id: b.k }, 'All')}
          ${main.n ? chip({ t: 'part', id: b.k, part: 'main' }, 'Main') : ''}
          ${rem.n ? chip({ t: 'part', id: b.k, part: 'remote' }, 'Remote') : ''}</div>
        ${head('Or pick a city')}` +
        cs.map(o => row(o.c.n, { loc: { t: 'city', id: o.i } }, o.c.h ? '<i class="hub">Main</i>' : '')).join('');
    } else if (q) {
      const has = n => n.toLowerCase().includes(q);
      const first = (a, b) => b.n.toLowerCase().startsWith(q) - a.n.toLowerCase().startsWith(q);
      const bs = BM.filter(b => has(b.n));
      const ss = STATE_LIST.filter(s => has(s.n)).sort(first);
      const cs = CITY_LIST.filter(o => has(o.c.n)).sort((a, b) => b.c.n.toLowerCase().startsWith(q) - a.c.n.toLowerCase().startsWith(q));
      // the current tab's matches first, then the other kinds
      const blocks = { branch: bs.length ? head('Branches') + branchRows(bs) : '', state: ss.length ? head('States') + stateRows(ss.slice(0, 15)) : '',
        city: cs.length ? head('Cities') + cityRows(cs.slice(0, 40)) + (cs.length > 40 ? `<div class="lmore">Keep typing to narrow ${cs.length} cities</div>` : '') : '' };
      h = [PK.tab, ...['branch', 'state', 'city'].filter(t => t !== PK.tab)].map(t => blocks[t]).join('')
        || `<div class="lnone">Nothing matches “${esc(PK.q)}”</div>`;
    } else if (PK.tab === 'branch') {
      h = india() + branchRows(BM);
    } else if (PK.tab === 'state') {
      h = india() + stateRows(STATE_LIST);
    } else {
      h = india() + cityRows(CITY_LIST.slice(0, 60)) + `<div class="lmore">Showing the 60 largest · type to find any of ${CITY_LIST.length} cities</div>`;
    }
    list.innerHTML = h;
    PK.act = Math.max(0, Math.min(PK.act, rows.length - 1));
    mark();
    list.querySelectorAll('.lr').forEach(r => {
      r.onclick = () => run(rows[+r.dataset.r]);
      r.onmousemove = () => { if (PK.act !== +r.dataset.r) { PK.act = +r.dataset.r; mark(false); } };
    });
    list.querySelectorAll('.lch').forEach(c => c.onclick = () => run({ loc: JSON.parse(c.dataset.loc) }));
    const bk = list.querySelector('.lback');
    if (bk) bk.onclick = () => { PK.drill = null; PK.act = 0; drawList(); inp.focus(); };
  };
  const mark = (scroll = true) => list.querySelectorAll('.lr').forEach(r => {
    const a = +r.dataset.r === PK.act;
    r.classList.toggle('act', a);
    if (a && scroll) r.scrollIntoView({ block: 'nearest' });
  });
  const run = act => {
    if (act.drill) { PK.drill = act.drill; PK.q = ''; inp.value = ''; PK.act = 0; drawList(); inp.focus(); return; }
    PK.open = false; PK.q = ''; PK.drill = null; PK.act = 0;
    setST({ loc: act.loc });
  };
  const place = () => {
    const r = root.querySelector('.lt').getBoundingClientRect();
    panel.style.left = Math.max(12, Math.min(r.left, innerWidth - panel.offsetWidth - 12)) + 'px';
    panel.style.top = r.bottom + 8 + 'px';
  };
  const setOpen = v => {
    PK.open = v;
    panel.hidden = !v;
    if (v) place();
    root.querySelector('.lt').setAttribute('aria-expanded', v);
    if (v) {
      // reopen where the current selection lives
      if (!PK.q) {
        if (cur.t === 'city') { PK.tab = 'branch'; PK.drill = C[cur.id].b; }
        else if (cur.t === 'branch' || cur.t === 'part') { PK.tab = 'branch'; PK.drill = cur.id; }
        else if (cur.t === 'state') { PK.tab = 'state'; PK.drill = null; }
        root.querySelectorAll('.lpt button').forEach(x => x.setAttribute('aria-pressed', x.dataset.tab === PK.tab));
      }
      drawList();
      inp.focus();
    }
  };

  root.querySelector('.lt').onclick = e => { e.stopPropagation(); setOpen(!PK.open); };
  const clr = root.querySelector('.lclr');
  if (clr) clr.onclick = e => { e.stopPropagation(); PK.open = false; PK.drill = null; setST({ loc: { t: 'all' } }); };
  root.querySelectorAll('.lpt button').forEach(b => b.onclick = () => {
    PK.tab = b.dataset.tab; PK.drill = null; PK.act = 0;
    root.querySelectorAll('.lpt button').forEach(x => x.setAttribute('aria-pressed', x === b));
    drawList(); inp.focus();
  });
  inp.oninput = () => { PK.q = inp.value; PK.drill = null; PK.act = 0; drawList(); };
  inp.onkeydown = e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); PK.act = Math.min(rows.length - 1, PK.act + 1); mark(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); PK.act = Math.max(0, PK.act - 1); mark(); }
    else if (e.key === 'Enter') { e.preventDefault(); if (rows[PK.act]) run(rows[PK.act]); }
    else if (e.key === 'Escape') { setOpen(false); root.querySelector('.lt').focus(); }
    else if (e.key === 'ArrowLeft' && PK.drill && !PK.q) { e.preventDefault(); PK.drill = null; PK.act = 0; drawList(); }
  };
  panel.onclick = e => e.stopPropagation();
  if (PK.open) setOpen(true);
}
// keep the open panel under its button while the page or filter bar scrolls
['scroll', 'resize'].forEach(ev => addEventListener(ev, () => {
  const lp = document.querySelector('.lp'), lt = document.querySelector('.lt');
  if (!PK.open || !lp || !lt) return;
  const r = lt.getBoundingClientRect();
  lp.style.left = Math.max(12, Math.min(r.left, innerWidth - lp.offsetWidth - 12)) + 'px';
  lp.style.top = r.bottom + 8 + 'px';
}, { passive: true, capture: true }));
document.addEventListener('click', () => {
  const lp = document.querySelector('.lp');
  if (PK.open && lp) { PK.open = false; lp.hidden = true; document.querySelector('.lt').setAttribute('aria-expanded', false); }
});

// ---------- filter bar ----------
function filterBar(el) {
  const tg = (name, val, opts) => `<div class="tg" data-f="${name}">` +
    opts.map(([v, l]) => `<button data-v="${v}" aria-pressed="${v === val}">${l}</button>`).join('') + '</div>';
  const draw = () => {
    el.innerHTML = `
      <div class="ff"><span class="ffl def" ${tip('Location')}>Location</span><div class="loc"></div></div>
      <div class="ff"><span class="ffl def" ${tip('Customer type')}>Customer type</span>${tg('biz', ST.biz, [['total', 'All'], ...BIZ])}</div>
      <div class="ff"><span class="ffl def" ${tip('Offering type')}>Offering type</span>${tg('ps', ST.ps, [['all', 'All'], ...OFF])}</div>
      <div class="ff"><span class="ffl def" ${tip('VFL')}>VFL</span>${tg('vfl', ST.vfl ? '1' : '0', [['0', 'Exclude'], ['1', 'Include']])}</div>`;
    locPicker(el.querySelector('.loc'));
    el.querySelectorAll('.tg').forEach(g => g.querySelectorAll('button').forEach(b => b.onclick = () => {
      const f = g.dataset.f, v = b.dataset.v;
      setST({ [f]: f === 'vfl' ? v === '1' : v });
    }));
  };
  draw();
  onChange(draw);
}

// ---------- components ----------
const RATE = o => o.m ? o.p1 / o.m * 100 : 0;   // penetration rate: paying / monetisable

// Definitions shown on hover. tip('Callable base') -> data-tip attribute; lab('Callable base') -> label with dotted underline
const DEF = {
  'Addressable base': 'Every live listing in the directory (not frozen, masked or closed down).',
  'Callable base': 'Listings with a working phone number that sales can call (callable_flag = 1).',
  'Monetisable base': 'Listings we can sell to: callable, or has paid at some point (callable or paid ≠ 0). Penetration is measured against this.',
  'Paying customers': 'Listings on a paid plan today (paid = 1).',
  'Penetration rate': 'Share of the monetisable base that is paying today. Paying customers ÷ monetisable base.',
  'Lapsed customers': 'Paid before but not paying now (paid = 2). The win-back pool.',
  'Fresh pipeline': 'Callable listings that have never bought (callable, paid = 0). The new-sales pool.',
  'Gap to India': 'This area’s penetration rate minus India’s, in percentage points. Green = ahead, red = behind.',
  'Customers to win': 'Extra paying customers this area would have if it reached India’s penetration rate. Monetisable base × India rate − paying customers.',
  'Average deal value': 'Original budget ÷ number of active contracts. Each contract (docid + version) counted once.',
  'RV_3yr': 'Revenue value of active contracts over three years: sum of RV_3yr on deals with dc_genio > 0 for the active versions in the paid contracts dump. For a state or city it is estimated from its share of its branch’s paying customers.',
  'Product mix': 'Share of active deals that include each product. A deal with several products counts under each, so shares add up to more than 100%.',
  'Customer type': 'From business_flag. B2B = serves businesses, B2C = serves consumers, Hybrid = serves both. Unflagged listings appear only under All.',
  'Offering type': 'From prod_service_flag. Products, Services, or Both.',
  'VFL': 'Listings tagged vfl_tag = 1. Exclude leaves them out; Include adds them in.',
  'Location': 'Pan India, a branch (All / Main city / Remote cities), a state or a city.',

};
const tip = (k, extra = '') => `data-tip="<b>${k}</b><br>${esc(DEF[k])}${extra ? '<br>' + extra : ''}"`;
const lab = (k, text = k) => `<span class="def" ${tip(k)}>${text}</span>`;
const inrCr = v => '₹' + (v >= 100 ? Math.round(v).toLocaleString('en-IN') : v.toFixed(v >= 10 ? 1 : 2)) + ' Cr';
const pts = d => `<span class="gap ${d >= 0 ? 'up' : 'dn'}">${d >= 0 ? '+' : '−'}${Math.abs(d).toFixed(2)} pts</span>`;

// Customers to win are measured against India's penetration rate (under the current filters)
const indiaRate = () => RATE(met(PA));
// Average deal value: original budget ÷ active contracts (falls back to collections ÷ deals on older data)
const dealValue = d => d.ctr ? d.ob * 1e7 / d.ctr : d.deals ? d.coll * 1e7 / d.deals : 0;
function headroom(g) {
  const cust = Math.max(0, g.m * indiaRate() / 100 - g.p1);
  return { cust };
}

// Headline: Addressable -> Callable -> Monetisable -> Paying, the penetration rate, then the three customer pools
function headline(el) {
  const g = met(locRaw());
  const steps = [
    ['Addressable base', g.T, 'Every live listing', 1],
    ['Callable base', g.C, `<em>${pct(g.C, g.T)}</em> of addressable`, g.C / g.T],
    ['Monetisable base', g.m, `<em>${pct(g.m, g.T)}</em> of addressable`, g.m / g.T],
    ['Paying customers', g.p1, `<em>${pct(g.p1, g.m, 2)}</em> of monetisable`, g.p1 / g.T]
  ];
  const pools = [
    ['Paying customers', g.p1, 'On a paid plan today', 'var(--acc)'],
    ['Lapsed customers', g.p2, 'Paid before, not now · win-back pool', '#f2a33a'],
    ['Fresh pipeline', g.c1p0, 'Callable, never bought · new-sales pool', '#8d8b83']
  ];
  const pmax = Math.max(...pools.map(p => p[1]));
  el.innerHTML = `
    <div class="ch"><div><h2>Market to customers · ${esc(locName())}</h2><p class="hint">How much of the market is callable, monetisable and paying · hover any figure for its meaning</p></div></div>
    <div class="hl">
      <div class="fun">${steps.map((s, i) => `
        <div class="fs ${i === 3 ? 'hero' : ''}" ${tip(s[0])}>
          <small class="def">${s[0]}</small><b class="num">${fmt(s[1])}</b>
          <div class="cv">${s[2]}</div>
          <div class="fbarv"><i style="width:${Math.max(s[3] * 100, 0.8)}%"></i></div>
        </div>`).join('')}</div>
      <div class="rates">
        <div class="rt hero" ${tip('Penetration rate', fmt(g.p1) + ' ÷ ' + fmt(g.m))}>
          <small class="def">Penetration rate</small><b class="num">${RATE(g).toFixed(2)}%</b><span>${ST.loc.t === 'all' ? 'paying ÷ monetisable' : pts(RATE(g) - indiaRate()) + ' vs India'}</span></div>
      </div>
    </div>
    <div class="pools">${pools.map(p => `
      <div class="pl" ${tip(p[0], fmt(p[1]) + ' · ' + pct(p[1], g.m, 1) + ' of monetisable')}>
        <div class="plh"><i style="background:${p[3]}"></i><span class="def">${p[0]}</span></div>
        <b class="num">${fmt(p[1])}</b><small>${p[2]}</small>
        <div class="fbarv"><i style="width:${Math.max(p[1] / (pmax || 1) * 100, 1)}%;background:${p[3]}"></i></div>
      </div>`).join('')}</div>`;
}

// Sequential ramp for penetration (single hue, light -> dark)
const RAMP = ['--h0', '--h1', '--h2', '--h3', '--h4', '--h5'];
function heat(v, max) {
  const i = Math.min(RAMP.length - 1, Math.floor((v / (max || 1)) * (RAMP.length - 0.01)));
  return { bg: `var(${RAMP[i]})`, fg: i >= 3 ? '#fff' : 'var(--tx)' };
}

// Customer type x offering type grid: cell = penetration rate, click = apply as filters
function segGrid(el) {
  const raw = locRaw();
  const cells = BIZ.map(([b]) => OFF.map(([p]) => met(raw, b, p)));
  const max = Math.max(...cells.flat().map(RATE));
  const rowT = BIZ.map(([b]) => met(raw, b, 'all')), colT = OFF.map(([p]) => met(raw, 'total', p));
  const all = met(raw, 'total', 'all');
  const isOn = (b, p) => (ST.biz === b || ST.biz === 'total') && (ST.ps === p || ST.ps === 'all');
  const lbl = (b, p) => (b === 'total' ? 'All customer types' : BIZ.find(x => x[0] === b)[1]) + ' · ' + (p === 'all' ? 'All offering types' : OFF.find(x => x[0] === p)[1]);
  const cell = (o, b, p, tot) => {
    const h = tot ? { bg: '', fg: '' } : heat(RATE(o), max);
    const dim = !tot && (ST.biz !== 'total' || ST.ps !== 'all') && !isOn(b, p);
    return `<button class="cell ${tot ? 'tot' : ''} ${dim ? 'dim' : ''} ${!tot && ST.biz === b && ST.ps === p ? 'on' : ''}"
      style="background:${h.bg};color:${h.fg}" data-b="${b}" data-p="${p}"
      data-tip="<b>${lbl(b, p)}</b><br>Penetration rate ${RATE(o).toFixed(2)}%<br>${fmt(o.p1)} paying of ${fmt(o.m)} monetisable<br>${fmt(o.T)} addressable">
      <b class="num">${RATE(o).toFixed(2)}%</b><small class="num">${fmt(o.p1)} paying · ${fmt(o.m)} monetisable</small></button>`;
  };
  el.innerHTML = `
    <div class="ch"><div><h2>Penetration rate by customer type and offering · ${esc(locName())}</h2>
      <p class="hint">Darker = higher penetration rate. Click a cell to filter the page.</p></div>
      <div class="hleg">Low<span class="ramp">${RAMP.map(r => `<i style="background:var(${r})"></i>`).join('')}</span>High</div></div>
    <div class="sg">
      <div></div>${OFF.map(([, l]) => `<div class="hd">${l}</div>`).join('')}<div class="hd tc">All offering types</div>
      ${BIZ.map(([b, l], i) => `<div class="rh"><i style="background:${COL[b]}"></i>${l}</div>
        ${OFF.map(([p], j) => cell(cells[i][j], b, p)).join('')}<div class="tc">${cell(rowT[i], b, 'all', true)}</div>`).join('')}
      <div class="rh" style="color:var(--mu)">All types</div>${OFF.map(([p], j) => cell(colT[j], 'total', p, true)).join('')}<div class="tc">${cell(all, 'total', 'all', true)}</div>
    </div>`;
  el.querySelectorAll('.cell').forEach(c => c.onclick = () => {
    const b = c.dataset.b, p = c.dataset.p;
    const same = ST.biz === b && ST.ps === p;
    setST(same ? { biz: 'total', ps: 'all' } : { biz: b, ps: p });
  });
}

// Opportunity table as CSV: every row (not just the top 25), current filters, sort order kept
function downloadCsv(rows, cols) {
  const head = { n: { b: 'Branch', s: 'State / UT', c: 'City' }[tblMode], rate: 'Penetration rate (%)', rv: 'RV_3yr (Rs Cr)' };
  const val = (r, k) => k === 'rate' ? r.rate.toFixed(2) : k === 'rv' ? r.rv.toFixed(2) : k === 'cust' ? Math.round(r.cust) : k === 'n' ? r.n : Math.round(r[k]);
  const q = v => /[",\n]/.test(v = String(v)) ? '"' + v.replace(/"/g, '""') + '"' : v;
  const lines = [[...cols.map(c => head[c[0]] || c[1]), 'Detail'].map(q).join(',')]
    .concat(rows.map(r => [...cols.map(c => val(r, c[0])), r.sub].map(q).join(',')));
  const bizL = { total: 'All', ...Object.fromEntries(BIZ) }[ST.biz], psL = { all: 'All', ...Object.fromEntries(OFF) }[ST.ps];
  const name = ['paid-penetration', { b: 'branches', s: 'states', c: 'cities' }[tblMode], locName(), 'customer-' + bizL, 'offering-' + psL,
    ST.vfl ? 'with-VFL' : 'no-VFL', new Date().toISOString().slice(0, 10)].join('_').replace(/[^\w.-]+/g, '-');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' }));
  a.download = name + '.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// Opportunity table: branches / states / cities with headroom vs India
let tblMode = 'b', tblSort = 'cust', tblDir = -1, cityAll = false;
function rankTable(el) {
  const ind = indiaRate();
  const cityScope = inLoc();
  const base = tblMode === 'b' ? BM.map(b => ({ t: 'branch', id: b.k, n: b.n, sub: b.r + ' · ' + cities(b.cs.length), raw: b.a }))
    : tblMode === 's' ? STATES.map(s => ({ t: 'state', id: s.id, n: s.n, sub: s.r + ' · ' + cities(s.cs.length), raw: s.a }))
    : C.map((c, i) => ({ t: 'city', id: i, n: c.n, sub: (c.h ? 'Main · ' : '') + BN[c.b].n + ' · ' + (SN[c.s] ? SN[c.s].n : c.s), raw: c }))
        .filter(r => cityScope(r.raw) && r.raw.T > 0);
  const rows = base.map(r => {
    const g = met(r.raw), h = headroom(g);
    return { ...r, g, T: g.T, m: g.m, p1: g.p1, rate: RATE(g), gap: RATE(g) - ind, cust: h.cust, rv: deals({ t: r.t, id: r.id }).Total.rv };
  });
  rows.sort((a, b) => (a[tblSort] > b[tblSort] ? 1 : -1) * tblDir);
  const lim = tblMode === 'c' && !cityAll ? 25 : 0, shown = lim ? rows.slice(0, lim) : rows;
  const rmax = Math.max(...rows.map(r => r.rate));
  const cols = [['n', { b: 'Branch', s: 'State / UT', c: 'City' }[tblMode]], ['T', 'Addressable base'], ['m', 'Monetisable base'], ['p1', 'Paying customers'], ['rate', 'Penetration rate'],
    ['cust', 'Customers to win'], ['rv', 'RV_3yr']];
  const td = (r, k) => k === 'n' ? `<td class="nm"><b>${esc(r.n)}</b><small>${esc(r.sub)}</small></td>`
    : k === 'rate' ? `<td><div class="ib"><u><i style="width:${r.rate / (rmax || 1) * 100}%"></i></u><b>${r.rate.toFixed(2)}%</b></div></td>`
    : k === 'cust' ? `<td>${r.cust >= 1 ? '+' + fmt(r.cust) : '<span class="ahead">At target</span>'}</td>`
    : k === 'rv' ? `<td>${inrCr(r.rv)}</td>` : `<td>${fmt(r[k])}</td>`;
  el.innerHTML = `
    <div class="ch"><div><h2>Where the opportunity is</h2>
      <p class="hint">Customers to win = extra paying customers at India’s penetration rate of ${ind.toFixed(2)}%. Click a row to focus.</p></div>
      <div class="tctl">
        <div class="seg2"><button data-m="b" aria-pressed="${tblMode === 'b'}">Branches</button><button data-m="s" aria-pressed="${tblMode === 's'}">States &amp; UTs</button><button data-m="c" aria-pressed="${tblMode === 'c'}">Cities${tblMode === 'c' && ST.loc.t !== 'all' ? ' · ' + esc(ST.loc.t === 'city' ? BN[C[ST.loc.id].b].n : locName()) : ''}</button></div>
      </div></div>
    <div class="tw"><table><thead><tr>${cols.map(c => `<th data-k="${c[0]}" class="${c[0] === tblSort ? 's' : ''}" ${DEF[c[1]] ? tip(c[1], 'Click to sort') : ''}>${DEF[c[1]] ? `<span class="def">${c[1]}</span>` : c[1]}${c[0] === tblSort ? (tblDir < 0 ? ' ↓' : ' ↑') : ''}</th>`).join('')}</tr></thead>
    <tbody>${shown.map(r => `<tr data-t="${r.t}" data-id="${r.id}" class="${ST.loc.t === r.t && ST.loc.id === r.id ? 'on' : ''}">
      ${cols.map(c => td(r, c[0])).join('')}</tr>`).join('')}</tbody></table></div>
    <div class="tfoot">${tblMode === 'c' && rows.length > 25 ? `<button class="xall">${cityAll ? 'Show top 25' : 'Show all ' + rows.length + ' cities'}</button>` : ''}
      <button class="csv" data-tip="All ${rows.length} rows of this table with the current filters">Download CSV</button></div>`;
  el.querySelector('.csv').onclick = () => downloadCsv(rows, cols);
  el.querySelectorAll('[data-m]').forEach(b => b.onclick = () => { tblMode = b.dataset.m; cityAll = false; rankTable(el); });
  el.querySelectorAll('th').forEach(h => h.onclick = () => {
    const k = h.dataset.k;
    if (k === tblSort) tblDir *= -1; else { tblSort = k; tblDir = k === 'n' ? 1 : -1; }
    rankTable(el);
  });
  const xa = el.querySelector('.xall');
  if (xa) xa.onclick = () => { cityAll = !cityAll; rankTable(el); };
  el.querySelectorAll('tbody tr').forEach(tr => tr.onclick = () => {
    const t = tr.dataset.t, id = t === 'city' ? +tr.dataset.id : tr.dataset.id;
    const same = ST.loc.t === t && ST.loc.id === id;
    setST({ loc: same ? (t === 'city' ? { t: 'branch', id: C[id].b } : { t: 'all' }) : { t, id } });
  });
}

// Choropleth: states and city dots shaded by penetration rate; click a state or city to focus
function mapView(el) {
  const sp = Object.fromEntries(STATES.map(s => [s.id, met(s.a)]));
  const max = Math.max(...Object.values(sp).filter(g => g.m > 50000).map(RATE));
  const selStates = ST.loc.t === 'all' ? null : ST.loc.t === 'state' ? [ST.loc.id] : ST.loc.t === 'city' ? [C[ST.loc.id].s]
    : [...new Set(C.filter(inLoc()).map(c => c.s))];
  const inArea = inLoc();
  const cmax = Math.max(...C.filter(c => c.m > 20000).map(c => RATE(met(c))));
  const dots = C.map((c, i) => ({ c, i, g: met(c) })).filter(o => inArea(o.c) && o.g.T > 0).sort((a, b) => a.g.T - b.g.T).map(o => {
    const on = ST.loc.t === 'city' && ST.loc.id === o.i;
    const r = ST.loc.t === 'all' ? 2.6 : Math.max(3, Math.min(9, Math.sqrt(o.g.T) / 90));
    return `<circle class="cd" cx="${o.c.x}" cy="${o.c.y}" r="${on ? r + 4 : r}" data-i="${o.i}" style="fill:${heat(Math.min(RATE(o.g), cmax), cmax).bg}" stroke="var(--ink)" stroke-width="${on ? 2.5 : 0.6}"
      data-tip="<b>${esc(o.c.n)}</b> · ${esc(BN[o.c.b].n)} branch<br>Penetration rate ${RATE(o.g).toFixed(2)}%<br>${fmt(o.g.p1)} paying · ${fmt(o.g.m)} monetisable"></circle>`;
  }).join('');
  const paths = P.map(p => {
    const g = sp[p.id];
    const h = g ? heat(Math.min(RATE(g), max), max) : { bg: '#e7e6e0' };
    const cls = selStates ? (selStates.includes(p.id) ? 'sel' : 'dim') : '';
    const nm = SN[p.id] ? SN[p.id].n : p.id;
    return `<path d="${p.d}" class="${cls}" style="fill:${h.bg}" data-s="${p.id}"
      data-tip="<b>${esc(nm)}</b><br>${g ? `Penetration rate ${RATE(g).toFixed(2)}%<br>${fmt(g.p1)} paying · ${fmt(g.m)} monetisable` : 'No listings'}"></path>`;
  }).join('');
  const hubs = C.filter(c => c.h).map(c => `<circle cx="${c.x}" cy="${c.y}" r="5" fill="var(--ink)" stroke="#fff" stroke-width="2"/><text x="${c.x + 8}" y="${c.y + 4}">${esc(c.n)}</text>`).join('');
  el.innerHTML = `
    <div class="ch"><div><h2>Penetration rate by state and city</h2><p class="hint">Darker = higher · labelled dots are each branch’s main city · click a state or city to focus</p></div></div>
    <div class="mapw"><svg viewBox="0 0 1000 1000" role="img" aria-label="India map shaded by penetration rate">${paths}${dots}${hubs}</svg>
      <div class="mapleg hleg">0%<span class="ramp">${RAMP.map(r => `<i style="background:var(${r})"></i>`).join('')}</span>${max.toFixed(1)}%+</div></div>`;
  el.querySelectorAll('circle.cd').forEach(d => d.onclick = () => {
    const i = +d.dataset.i, same = ST.loc.t === 'city' && ST.loc.id === i;
    setST({ loc: same ? { t: 'branch', id: C[i].b } : { t: 'city', id: i } });
  });
  el.querySelectorAll('path[data-s]').forEach(p => p.onclick = () => {
    if (!SN[p.dataset.s]) return;
    const same = ST.loc.t === 'state' && ST.loc.id === p.dataset.s;
    setST({ loc: same ? { t: 'all' } : { t: 'state', id: p.dataset.s } });
  });
}

// Selected-area panel: rates, opportunity, customer-type split, revenue quality, product mix
function selPanel(el) {
  const raw = locRaw(), g = met(raw), d = deals(), T = d.Total;
  const segs = BIZ.map(([b, l]) => ({ b, l, g: met(raw, b) }));
  const smax = Math.max(...segs.map(s => RATE(s.g)));
  const q = [
    ['Average deal value', dealValue(T) ? rs(dealValue(T)) : '—', ''],
    ['RV_3yr', inrCr(T.rv), '']
  ];
  const mix = ['Package', 'PDG', 'Others'].map(k => [k === 'Others' ? 'Other' : k, d[k].deals]);
  el.innerHTML = `
    <div class="sp">
      <div class="eb">${{ all: 'All branches', branch: 'Branch', part: 'Branch · ' + (ST.loc.part === 'main' ? 'main' : 'remote'), state: 'State / UT', city: 'City' }[ST.loc.t]}</div>
      <h3>${esc(locName())}</h3><div class="sub">${esc(locSub())}</div>
      <div class="pen" ${tip('Penetration rate')}><small class="def">Penetration rate</small><strong class="num">${RATE(g).toFixed(2)}%</strong>
        <div class="r"><span>${fmt(g.p1)} paying of ${fmt(g.m)} monetisable</span></div></div>
      <h4>${lab('Penetration rate', 'Penetration rate')} by ${lab('Customer type', 'customer type')}</h4>
      <div class="mini3">${segs.map(s => `<div class="m3" data-tip="<b>${s.l}</b><br>${fmt(s.g.p1)} paying of ${fmt(s.g.m)} monetisable">
        <span>${s.l}</span><u><i style="width:${RATE(s.g) / (smax || 1) * 100}%;background:${COL[s.b]}"></i></u><b>${RATE(s.g).toFixed(2)}%</b></div>`).join('')}</div>
      <h4>Deal value</h4>
      <div class="rq">${q.map(x => `<div ${tip(x[0])}><small class="def">${x[0]}</small><b class="num">${x[1]}</b></div>`).join('')}</div>
      <h4>${lab('Product mix')} · share of ${fmt(T.deals)} deals</h4>
      <div class="dl">${mix.map(([k, v]) => `<div class="dlr" data-tip="<b>${k}</b><br>${fmt(v)} deals include ${k}">
        <span>${k}</span><u><i style="width:${T.deals ? v / T.deals * 100 : 0}%;background:var(--ink)"></i></u><b class="num">${pct(v, T.deals)}</b></div>`).join('')}</div>
      <p class="hint" style="margin-top:8px">A deal with several products counts under each, so shares add up to more than 100%.${ST.loc.t === 'state' || ST.loc.t === 'city' || ST.loc.t === 'part' ? ' Deal figures here are estimated from this area’s share of its branch’s paying customers.' : ''}</p>
    </div>`;
}

function header() {
  return `<div class="top"><div class="brand"><div class="logo"><i></i></div><div><b>Paid Penetration Command Center</b><small>Pan India · live data</small></div></div></div>`;
}
