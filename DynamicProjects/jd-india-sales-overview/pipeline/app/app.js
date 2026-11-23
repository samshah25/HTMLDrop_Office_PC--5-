/* ===== JD India sales overview: the page (needs core.js above) ===== */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const IN0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
  const IN1 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });
  const MINUS = '−';
  const fDeals = x => (Math.abs(x) < 100 ? IN1 : IN0).format(x);     // joint deals make halves; small numbers keep them
  function fRv(th) {                                                   // RV is carried in rupees thousand
    const cr = th / 1e4;
    if (Math.abs(cr) >= 1) return '₹' + (Math.abs(cr) >= 100 ? IN0 : IN1).format(cr) + ' cr';
    const l = th / 100;
    return '₹' + (Math.abs(l) >= 10 ? IN0 : IN1).format(l) + ' L';
  }
  const sgn = (x, f) => (x > 0 ? '+' : x < 0 ? MINUS : '') + f(Math.abs(x));
  const fPct = p => p === null || !isFinite(p) ? '—' : sgn(Math.round(p * 10) / 10, v => v.toFixed(1)) + '%';
  const fPts = x => sgn(Math.round(x * 10) / 10, v => v.toFixed(1)) + ' pts';
  // change colour follows the map's bands: within ±2% is neutral; red only for a real drop
  const clsP = p => p === null || p === undefined || !isFinite(p) ? 'mu' : p > 0 ? 'up' : p < 0 ? 'dn' : 'mu';
  const clsPts = x => x >= 1 ? 'up' : x <= -1 ? 'dn' : 'mu';
  const TRI = up => `<svg class="tri" viewBox="0 0 10 10" aria-hidden="true"><path d="${up ? 'M5 1.5L9.2 8.5H.8z' : 'M5 8.5L.8 1.5h8.4z'}"/></svg>`;
  const MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const FYM = ['Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar'];
  const dOf = o => dayDate(o);
  const fDate = (d, yr) => `${d.getUTCDate()} ${MON3[d.getUTCMonth()]}${yr ? ' ' + d.getUTCFullYear() : ''}`;
  function fRange(a, b) {
    const A = dOf(a), B = dOf(b);
    if (a === b) return fDate(A, true);
    if (A.getUTCMonth() === B.getUTCMonth() && A.getUTCFullYear() === B.getUTCFullYear()) return `${A.getUTCDate()}–${fDate(B, true)}`;
    return `${fDate(A, A.getUTCFullYear() !== B.getUTCFullYear())} – ${fDate(B, true)}`;
  }
  const iso = d => d.toISOString().slice(0, 10);
  const offOf = s => Math.round((new Date(s + 'T00:00:00Z') - FY0) / 864e5);
  const LY0 = new Date(META.lyFrom + 'T00:00:00Z');
  const lyRange = (a, b) => { const A = new Date(LY0.getTime() + a * 864e5), B = new Date(LY0.getTime() + b * 864e5); return `${fDate(A, A.getUTCFullYear() !== B.getUTCFullYear())} – ${fDate(B, true)}`; };

  // growth % is only shown where last year had enough deals to make it meaningful
  // growth % needs enough deals last year to mean anything: per half-year 500 (state), 200 (branch), 100 (district),
  // 20 (pincode), scaled to the dates picked, never below 30 / 20 / 10 / 5 on short periods
  const MIN = { india: 0, state: 500, branch: 200, district: 100, pin: 20 }, FLOOR = { india: 0, state: 30, branch: 20, district: 10, pin: 5 };
  const MIN0 = { ...MIN };
  const minFor = k => Math.min(MIN[k], Math.max(Math.min(FLOOR[k], MIN[k]), Math.round(MIN[k] * (V.to - V.from + 1) / 182)));
  const FEW_KEYS = [['state', 'State or UT'], ['branch', 'Branch'], ['district', 'District'], ['pin', 'Pincode']];
  const fewChanged = () => FEW_KEYS.some(([k]) => MIN[k] !== MIN0[k]);
  const KIND_OF = { states: 'state', branches: 'branch', districts: 'district', pincodes: 'pin' };
  const BAND = { l2: '#B8322A', l1: '#EBA196', g1: '#BFE3D3', g2: '#5FB596', g3: '#0E7A5E', small: '#FFFFFF' };
  const DOT = { l2: '#B8322A', l1: '#E3897D', g1: '#8FCDB4', g2: '#4FAA88', g3: '#0E7A5E', small: '#C9D1DC' };
  const BAND_LABEL = [['l2', 'below ' + MINUS + '10%'], ['l1', MINUS + '10 to 0%'], ['g1', '0 to +10%'], ['g2', '+10 to +25%'], ['g3', '+25% or more']];
  const BAND_DARK = { l2: 1, g3: 1 };          // white text on these
  const bandOf = (p, ok) => !ok || p === null ? 'small' : p >= 25 ? 'g3' : p >= 10 ? 'g2' : p >= 0 ? 'g1' : p >= -10 ? 'l1' : 'l2';
  // the legend: one continuous ramp with its cut points, then the two non-band states
  const rampLegend = smallCls => `<span class="lgt">${MLABEL[V.m]} vs last year</span><span class="ramp" role="img" aria-label="Change against last year: ${BAND_LABEL.map(x => x[1]).join(', ')}">` +
    `<span class="rsw">${BAND_LABEL.map(([k]) => `<i style="background:${BAND[k]}"></i>`).join('')}</span>` +
    `<span class="rtk"><em style="left:20%">${MINUS}10%</em><em style="left:40%">0</em><em style="left:60%">+10%</em><em style="left:80%">+25%</em></span></span>` +
    `<span><i class="${smallCls}"></i>too few to compare: under ${minFor(MAP_KIND())} deals last year <button type="button" class="lk" data-rules="few">Change</button></span><span><i class="hatch"></i>no deals in these dates</span>`;
  // what the map's shapes or dots are at this level: states on India, districts in a state, pincodes below
  const MAP_KIND = () => ({ india: 'state', state: 'district', branch: 'pin', district: 'pin' })[level()];
  const CHC = ['#1F5FAD', '#8B5CF6', '#B7791F', '#D9468C'];
  const CUR = MONTH_OF[META.days - 1];      // FY month index of the data's last day

  // ---------- groupings beyond core ----------
  const ROWS_BY_BR = BRANCHES.map(() => []);
  for (let p = 0; p < NP; p++) ROWS_BY_BR[COLS.br[p]].push(p);
  const BR_STATES = BRANCHES.map(() => new Set());
  for (let p = 0; p < NP; p++) BR_STATES[COLS.br[p]].add(COLS.st[p]);

  // ---------- map districts: each pincode's district on the district map (placed by its location at build time) ----------
  const DMAP = JSON.parse($('#districts').textContent);
  const DNAME = DMAP.n;
  const DM_STATE = DMAP.s.map(n => STATES.indexOf(n));
  const DIST_OF_STATE = STATES.map(() => []);
  DM_STATE.forEach((s, i) => { if (s >= 0) DIST_OF_STATE[s].push(i); });
  const ROWS_BY_DM = DNAME.map(() => []);
  for (let p = 0; p < NP; p++) if (COLS.dm[p] >= 0) ROWS_BY_DM[COLS.dm[p]].push(p);
  const NO_DIST = 'District not known';

  // ---------- view state ----------
  const V = { cap: 0, s: -1, b: -1, d: -1, kids: 'states', m: 'deals', from: 0, to: META.days - 1, preset: 'fytd', pin: -1, cols: false, sort: null, dir: -1 };
  const level = () => V.d >= 0 ? 'district' : V.b >= 0 ? 'branch' : V.s >= 0 ? 'state' : 'india';
  const KIDS = { india: ['states', 'districts', 'branches', 'pincodes'], state: ['districts', 'branches', 'pincodes'], branch: ['pincodes'], district: ['pincodes'] };
  const KID_NAME = { states: 'States & UTs', districts: 'Districts', branches: 'Branches', pincodes: 'Pincodes' };
  const KID_LOW = { states: 'states & UTs', districts: 'districts', branches: 'branches', pincodes: 'pincodes' };
  const KID_ONE = { states: 'state or UT', districts: 'district', branches: 'branch', pincodes: 'pincode' };
  function rowsOf(s, b, d = -1) {
    if (d >= 0) return ROWS_BY_DM[d];
    if (b >= 0) return s >= 0 ? (ROWS_BY_SB.get(s + '|' + b) || []) : ROWS_BY_BR[b];
    return s >= 0 ? ROWS_BY_STATE[s] : ALL_ROWS;
  }
  function areaName(s = V.s, b = V.b, d = V.d) { return d >= 0 ? DNAME[d] + ' district' : b >= 0 ? BRANCHES[b] : s >= 0 ? STATES[s] : 'India'; }

  // ---------- period sums (cached per period) ----------
  let SUMS = null, SUMKEY = '';
  function sums() { const k = V.from + '-' + V.to + '-' + CAP; if (k !== SUMKEY) { SUMS = sumPeriod({ a: V.from, b: V.to }); SUMKEY = k; } return SUMS; }
  const val = (o) => V.m === 'rv' ? o.tyRv : V.m === 'cust' ? (o.tyC || 0) : o.ty;
  const lval = (o) => V.m === 'rv' ? o.lyRv : V.m === 'cust' ? (o.lyC || 0) : o.ly;
  const fCust = x => IN0.format(Math.round(x));
  const fVal = x => V.m === 'rv' ? fRv(x) : V.m === 'cust' ? fCust(x) : fDeals(x);
  const fDelta = x => V.m === 'rv' ? sgn(x, fRv) : V.m === 'cust' ? sgn(x, fCust) : sgn(x, fDeals);
  const measureName = () => V.m === 'rv' ? 'RV 3yr' : V.m === 'cust' ? 'customers' : 'deals';
  const MLABEL = { deals: 'Deals', rv: 'RV 3yr', cust: 'Customers' };
  const P0 = () => ({ a: V.from, b: V.to });
  // unique customers per pincode for the period (cached with the period sums)
  function pinCust() { const S = sums(); if (!S.cust) S.cust = custCount(P0(), p => p, NP); return S.cust; }
  // area totals, plus the area's own distinct customer count when customers are shown
  function totals(S, rows) {
    const T = areaTotals(S, rows);
    if (V.m === 'cust') { const mask = maskOf(rows), c = custCount(P0(), p => mask[p] ? 0 : -1, 1); T.tyC = c.ty[0]; T.lyC = c.ly[0]; }
    return T;
  }

  function children(S, rows, kind) {
    if (kind === 'pincodes') {
      const out = [];
      for (const p of rows) if (S.ty[p] > 0 || S.ly[p] > 0) out.push({ kind: 'pin', id: p, name: COLS.pin[p], sub: COLS.place[p], ty: S.ty[p], ly: S.ly[p], tyRv: S.tyRv[p], lyRv: S.lyRv[p], rows: [p] });
      if (V.m === 'cust') { const pc = pinCust(); out.forEach(c => { c.tyC = pc.ty[c.id]; c.lyC = pc.ly[c.id]; }); }
      return out;
    }
    const isSt = kind === 'states', isDi = kind === 'districts', m = new Map();
    const keyOf = isSt ? p => COLS.st[p] : isDi ? p => COLS.dm[p] : p => COLS.br[p];
    const KIND = isSt ? 'state' : isDi ? 'district' : 'branch';
    const nameOf = k => isSt ? STATES[k] : isDi ? (k >= 0 ? DNAME[k] : NO_DIST) : BRANCHES[k];
    const blank = k => ({ kind: KIND, id: k, name: nameOf(k), sub: '', ty: 0, ly: 0, tyRv: 0, lyRv: 0, rows: [] });
    // every state on the India map and every district of an open state is listed, with or without deals
    if (isSt && rows === ALL_ROWS) STATES.forEach((n, k) => { if (n !== 'State not known') m.set(k, blank(k)); });
    if (isDi && V.s >= 0 && V.d < 0 && V.b < 0) DIST_OF_STATE[V.s].forEach(k => m.set(k, blank(k)));
    for (const p of rows) {
      const k = keyOf(p);
      let c = m.get(k);
      if (!c) m.set(k, c = blank(k));
      c.ty += S.ty[p]; c.ly += S.ly[p]; c.tyRv += S.tyRv[p]; c.lyRv += S.lyRv[p]; c.rows.push(p);
    }
    const out = [...m.values()].filter(c => c.kind === 'state' || (isDi && c.id >= 0 && V.s >= 0) || c.ty > 0 || c.ly > 0);
    if (KIND === 'branch') for (const c of out) { const st = [...BR_STATES[c.id]]; if (V.s < 0 && st.length) c.sub = st.length > 1 ? st.length + ' states' : STATES[st[0]]; }
    if (isDi && V.s < 0) for (const c of out) if (c.id >= 0) c.sub = STATES[DM_STATE[c.id]] || '';
    if (V.m === 'cust') {      // each state, district or branch counts its own distinct customers (a customer in two pincodes counts once)
      const ix = new Map(out.map((c, i) => [c.id, i])), mask = maskOf(rows);
      const cc = custCount(P0(), p => mask[p] ? (ix.get(keyOf(p)) ?? -1) : -1, out.length);
      out.forEach((c, i) => { c.tyC = cc.ty[i]; c.lyC = cc.ly[i]; });
    }
    return out;
  }
  function enrich(c, total) {
    c.v = val(c); c.lv = lval(c); c.d = c.v - c.lv;
    c.ok = c.ly >= minFor(c.kind) && c.lv > 0;
    c.p = c.ok ? (c.v / c.lv - 1) * 100 : null;
    c.share = total > 0 ? c.v / total * 100 : 0;
    c.band = c.kind !== 'pin' && c.ty === 0 && c.tyRv === 0 ? 'none' : bandOf(c.p, c.ok);
    return c;
  }
  // a district named alone is ambiguous across India (two Aurangabads): outside a state it carries its state's code
  const kidLabel = c => c.kind === 'pin' ? `${c.name}${c.sub ? ' ' + c.sub : ''}` : c.kind === 'district' && V.s < 0 && c.id >= 0 ? `${c.name} (${(TILE[STATES[DM_STATE[c.id]]] || [''])[0]})` : c.name;
  const UNPLACED = /^(State not known|Not mapped|District not known)$/;
  function mixFor(rows, S, which) {
    const K = new Float64Array(NK), src = which === 'ly' ? S.lyK : S.tyK;
    for (const p of rows) for (let k = 0; k < NK; k++) K[k] += src[p * NK + k];
    return mixOf(K);
  }

  // ---------- number tweening ----------
  function tweenText(el, to, fmt, first) {
    const from = el._v === undefined ? (first ? 0 : to) : el._v;
    el._v = to;
    if (RM || from === to) { el.textContent = fmt(to); return; }
    const t0 = performance.now(), dur = first ? 1100 : 650;
    cancelAnimationFrame(el._raf);
    const step = now => { const k = Math.max(0, Math.min(1, (now - t0) / dur)), e = 1 - Math.pow(2, -10 * k); el.textContent = fmt(from + (to - from) * (k >= 1 ? 1 : e)); if (k < 1) el._raf = requestAnimationFrame(step); };
    el._raf = requestAnimationFrame(step);
  }

  // ---------- tooltip ----------
  const TIP = $('#tip');
  function tip(html, ev) {
    TIP.innerHTML = html; TIP.hidden = false;
    const w = TIP.offsetWidth, h = TIP.offsetHeight;
    let x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + w > innerWidth - 8) x = ev.clientX - w - 14;
    if (y + h > innerHeight - 8) y = ev.clientY - h - 14;
    TIP.style.left = x + 'px'; TIP.style.top = y + 'px';
  }
  const untip = () => { TIP.hidden = true; };
  const tipFor = (c, extra = '') => `<b>${esc(kidLabel(c))}</b><br>${esc(fVal(c.v))} ${measureName()} <span class="m">(${esc(fVal(c.lv))} last year)</span><br>` +
    `<span class="${{ up: 'u', dn: 'd', mu: 'm' }[clsP(c.ok ? c.p : null)]}">${esc(fDelta(c.d))}${c.ok ? ' · ' + esc(fPct(c.p)) : ''}</span>` +
    (c.ok ? '' : `<br><span class="m">Change % not shown: under ${minFor(c.kind)} deals last year</span>`) + extra;

  /* =========================================================== band */
  function stub(name, s, b, current, d = -1) {
    const S = sums(), rows = rowsOf(s, b, d), T = totals(S, rows), v = val(T), lv = lval(T);
    const p = lv > 0 ? (v / lv - 1) * 100 : null;
    return `<button type="button" class="stub" data-s="${s}" data-b="${b}" data-d="${d}" ${current ? 'aria-current="page"' : ''}><b>${esc(name)}</b><small class="tn">${esc(fVal(v))} · ${esc(fPct(p))}</small></button>`;
  }
  const SEP = '<svg class="sep" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5L10.5 8 6 12.5"/></svg>';
  let FIRST = true;
  function renderBand(T, kids) {
    const L = level();
    let trail = stub('India', -1, -1, L === 'india');
    if (V.s >= 0) trail += SEP + stub(STATES[V.s], V.s, -1, L === 'state');
    if (V.b >= 0) trail += SEP + stub(BRANCHES[V.b], V.s, V.b, true);
    if (V.d >= 0) trail += SEP + stub(DNAME[V.d], V.s, -1, true, V.d);
    $('#trail').innerHTML = trail;

    const v = val(T), lv = lval(T), p = lv > 0 ? (v / lv - 1) * 100 : null;
    const oT = V.m === 'deals' ? T.tyRv : T.ty, oL = V.m === 'deals' ? T.lyRv : T.ly, op = oL > 0 ? (oT / oL - 1) * 100 : null;
    const mx = mixOf(T.tyK), ml = mixOf(T.lyK);
    const sh = (a, b) => a.all ? a[b] / a.all * 100 : 0;
    const fr = [sh(mx, 'fresh'), sh(ml, 'fresh')], ec = [sh(mx, 'ecs'), sh(ml, 'ecs')], js = [mx.all ? mx.ch[1] / mx.all * 100 : 0, ml.all ? ml.ch[1] / ml.all * 100 : 0];
    const chg = x => { const k = clsP(x); return `<span class="chg ${k === 'mu' ? 'flat' : k}">${x === null ? '' : k === 'mu' ? esc(fPct(x)) : TRI(k === 'up') + Math.abs(x).toFixed(1) + '%'}</span>`; };
    const H = $('#hero');
    if (!H.firstChild) H.innerHTML = `<div><div class="area" id="hArea"></div><div class="big"><span id="hBig"></span><span id="hLyC"></span></div></div>
      <div><div class="k" id="hLyK">Same dates last year</div><div class="mid"><span id="hLy"></span></div></div>
      <div><div class="k" id="hOK"></div><div class="mid"><span id="hO"></span><span id="hOC"></span></div></div>
      <div class="mix3" id="hMix" role="group" aria-label="Share of deals"></div>
      <p class="say" id="hSay"></p>`;
    $('#hArea').innerHTML = `<b>${esc(areaName())}</b> · ${MLABEL[V.m]}, ${esc(fRange(V.from, V.to))}` +
      (V.cap ? ` · <span class="capnote">deals above ${esc(fLakh(V.cap))} RV 3yr left out</span>` : '');
    tweenText($('#hBig'), v, fVal, FIRST);
    tweenText($('#hLy'), lv, fVal, FIRST);
    $('#hLyC').innerHTML = chg(p);
    $('#hOK').textContent = V.m === 'deals' ? 'RV 3yr' : 'Deals';
    tweenText($('#hO'), oT, V.m === 'deals' ? fRv : fDeals, FIRST);
    $('#hOC').innerHTML = chg(op);
    // three shares of deals, each with its change in points; neutral ink, since up or down is not good or bad by itself
    $('#hMix').innerHTML = [['Fresh share', fr, 'Fresh (new) deals as a share of all deals'], ['ECS share', ec, 'Deals on ECS (auto-debit) as a share of all deals'], ['JDS share', js, 'Deals closed by JDS (in-house) as a share of all deals; joint deals count half']]
      .map(([l, v, t]) => `<div title="${t}"><div class="k">${l}</div><div class="mid tn">${v[0].toFixed(0)}%</div><div class="pt tn">${fPts(v[0] - v[1])}<span class="vly"> vs last year</span></div></div>`).join('');
    // one factual sentence: direction, and the largest drop and gain among the areas below
    const dp = T.ly > 0 ? (T.ty / T.ly - 1) * 100 : null, rp = T.lyRv > 0 ? (T.tyRv / T.lyRv - 1) * 100 : null;
    const dir = dp === null ? 'has no deals on these dates last year' : Math.abs(dp) < 2 ? `is <b>flat on deals</b> (${fPct(dp)})` : dp > 0 ? `is <b>ahead on deals</b> by ${Math.abs(dp).toFixed(1)}%` : `is <b>behind on deals</b> by ${Math.abs(dp).toFixed(1)}%`;
    const rv = rp === null ? '' : `, RV 3yr ${rp >= 0 ? 'up' : 'down'} <b>${Math.abs(rp).toFixed(1)}%</b>`;
    const byD = kids.filter(c => c.d !== 0 && !UNPLACED.test(c.name)).sort((a, b) => a.d - b.d);
    const lo = byD[0], hi = byD[byD.length - 1];
    const ex = [lo && lo.d < 0 ? `Biggest drop: <b>${esc(kidLabel(lo))}</b> (${esc(fDelta(lo.d))})` : '', hi && hi.d > 0 ? `biggest gain: <b>${esc(kidLabel(hi))}</b> (${esc(fDelta(hi.d))})` : ''].filter(Boolean).join('; ');
    $('#hSay').innerHTML = `${esc(areaName())} ${dir}${rv} against the same dates last year.${ex ? ' ' + ex.charAt(0).toUpperCase() + ex.slice(1) + '.' : ''}`;

    // tally: this year's fill against last year's tick
    const scale = Math.max(v, lv) * 1.06 || 1;
    const tl = $('#tally');
    if (!tl.firstChild) tl.innerHTML = `<div class="bar"><div class="fill" id="tFill"></div><div class="lyw" id="tLy"><div class="ly"></div></div></div><div class="lab"><span id="tL"></span><span id="tR"></span></div>`;
    requestAnimationFrame(() => { $('#tFill').style.transform = `scaleX(${v / scale})`; $('#tLy').style.transform = `translateX(${lv / scale * 100}%)`; });
    $('#tL').innerHTML = `This year <b class="tn">${esc(fVal(v))}</b> · white mark = last year <b class="tn">${esc(fVal(lv))}</b>`;
    $('#tR').innerHTML = lv > 0 ? `<b class="tn">${(v / lv * 100).toFixed(1)}%</b> of last year's ${measureName()} on the same dates (<b class="tn">${esc(fDelta(v - lv))}</b>)` : '';

    document.querySelectorAll('#measure button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.m === V.m)));
    const pre = META.presets.find(x => x.k === V.preset);
    $('#periodLabel').innerHTML = (pre ? `<span class="pl-pre">${esc(pre.label.replace('Financial year', 'FY'))} · </span>` : '') + esc(fRange(V.from, V.to));
  }

  /* =========================================================== map */
  const BORDERS = JSON.parse($('#borders').textContent);
  const BORDER_TO_STATE = { 'Jammu & Kashmir': 'Jammu and Kashmir', 'Andaman & Nicobar': 'Andaman and Nicobar Islands' };
  let lo0 = 180, lo1 = -180, la0 = 90, la1 = -90;
  for (const rings of Object.values(BORDERS)) for (const r of rings) for (let j = 0; j < r.length; j += 2) { lo0 = Math.min(lo0, r[j]); lo1 = Math.max(lo1, r[j]); la0 = Math.min(la0, r[j + 1]); la1 = Math.max(la1, r[j + 1]); }
  const KX = Math.cos((la0 + la1) / 2 * Math.PI / 180), SC = 1000 / ((lo1 - lo0) * KX);
  const PX = lon => (lon - lo0) * KX * SC, PY = lat => (la1 - lat) * SC;
  const MAPH = (la1 - la0) * SC;
  const SHAPES = [];      // {s, d, box:[x0,y0,x1,y1], cx}
  for (const [name, rings] of Object.entries(BORDERS)) {
    const s = STATES.indexOf(BORDER_TO_STATE[name] || name);
    let d = '', x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const r of rings) {
      for (let j = 0; j < r.length; j += 2) { const x = PX(r[j]), y = PY(r[j + 1]); d += (j ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      d += 'Z';
    }
    SHAPES.push({ s, name, d, box: [x0, y0, x1, y1] });
  }
  const MAP = $('#map'), NS = 'http://www.w3.org/2000/svg';
  MAP.innerHTML = `<defs><pattern id="hatch" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)"><rect width="7" height="7" fill="#FBF3F2"/><line x1="0" y1="0" x2="0" y2="7" stroke="#C8372D" stroke-width="2" opacity=".6"/></pattern><pattern id="dots" patternUnits="userSpaceOnUse" width="5" height="5"><rect width="5" height="5" fill="#EDF0F4"/><circle cx="2.5" cy="2.5" r="1.15" fill="#7F8B9D"/></pattern></defs><g id="gOut">${SHAPES.map(sh => `<path d="${sh.d}"/>`).join('')}</g><g id="gSt">${SHAPES.map((sh, i) => `<path class="st" data-i="${i}" d="${sh.d}" style="--d:${Math.round(sh.box[0] / 1000 * 320)}ms"/>`).join('')}</g><g id="gCtx"></g><g id="gDist"></g><g id="gEdge"></g><g id="gBd"></g><g id="gSel"></g><g id="gDl"></g><g id="gDots"></g>`;
  // district shapes in the page's projection, built on first use
  const DSH = [];
  function dShape(i) {
    if (DSH[i]) return DSH[i];
    let d = '', x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    for (const r of DMAP.r[i]) {
      for (let j = 0; j < r.length; j += 2) { const x = PX(r[j]), y = PY(r[j + 1]); d += (j ? 'L' : 'M') + x.toFixed(1) + ' ' + y.toFixed(1); x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
      d += 'Z';
    }
    return (DSH[i] = { d, box: [x0, y0, x1, y1], lx: PX(DMAP.lp[i][0]), ly: PY(DMAP.lp[i][1]) });
  }
  // inside a state everything is drawn from the district file, so borders meet exactly: the other states' districts as
  // grey context, and state borders from the district edges that separate two states or face the sea
  const lineD = r => { let d = ''; for (let j = 0; j < r.length; j += 2) d += (j ? 'L' : 'M') + PX(r[j]).toFixed(1) + ' ' + PY(r[j + 1]).toFixed(1); return d; };
  const E_ST = DMAP.es.map(a => STATES.indexOf(DMAP.st[a]));      // the state of each line between two districts
  const BD_ST = DMAP.bs.map(([a, b]) => [STATES.indexOf(DMAP.st[a]), b >= 0 ? STATES.indexOf(DMAP.st[b]) : -2]);
  let ctxBuilt = false;
  function districtWorld() {
    if (ctxBuilt) return;
    ctxBuilt = true;
    $('#gCtx').innerHTML = DNAME.map((_, i) => `<path class="dc" data-s="${DM_STATE[i]}" d="${dShape(i).d}"/>`).join('');
    $('#gBd').innerHTML = `<path d="${DMAP.b.map(lineD).join('')}"/><path class="on" id="bdOn"/>`;
  }
  const ASPECT = 1080 / 1000;
  const FULL = fitBox([0, 0, 1000, MAPH], 0.02);
  function fitBox(b, pad, min = 40) {
    let [x0, y0, x1, y1] = b; let w = x1 - x0, h = y1 - y0;
    w = Math.max(w, min); h = Math.max(h, min);
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    w *= 1 + pad * 2; h *= 1 + pad * 2;
    if (h / w > ASPECT) w = h / ASPECT; else h = w * ASPECT;
    return [cx - w / 2, cy - h / 2, w, h];
  }
  let VB = FULL.slice(), vbRaf = 0;
  const applyVB = () => MAP.setAttribute('viewBox', VB.map(v => v.toFixed(2)).join(' '));
  applyVB();
  function goVB(t, animate) {
    cancelAnimationFrame(vbRaf);
    if (!animate || RM) { VB = t.slice(); applyVB(); return; }
    const f = VB.slice(), t0 = performance.now(), dur = 700;
    const step = now => { const k = Math.max(0, Math.min(1, (now - t0) / dur)), e = k >= 1 ? 1 : 1 - Math.pow(2, -10 * k); VB = f.map((v, i) => v + (t[i] - v) * e); applyVB(); if (k < 1) vbRaf = requestAnimationFrame(step); };
    vbRaf = requestAnimationFrame(step);
  }
  function pctl(a, q) { const s = [...a].sort((x, y) => x - y); return s[Math.min(s.length - 1, Math.max(0, Math.floor(q * (s.length - 1))))]; }
  function rowsBox(rows) {
    const xs = [], ys = [];
    for (const p of rows) if (COLS.lat[p] !== null && COLS.lon[p] !== null) { xs.push(PX(COLS.lon[p])); ys.push(PY(COLS.lat[p])); }
    if (xs.length < 2) return null;
    return [pctl(xs, .02), pctl(ys, .02), pctl(xs, .98), pctl(ys, .98)];
  }

  const TILE = {
    'Jammu and Kashmir': ['JK', 1, 0], 'Ladakh': ['LA', 2, 0],
    'Punjab': ['PB', 1, 1], 'Himachal Pradesh': ['HP', 2, 1],
    'Chandigarh': ['CH', 1, 2], 'Haryana': ['HR', 2, 2], 'Uttarakhand': ['UK', 3, 2], 'Sikkim': ['SK', 5, 2], 'Arunachal Pradesh': ['AR', 7, 2],
    'Rajasthan': ['RJ', 1, 3], 'Delhi': ['DL', 2, 3], 'Uttar Pradesh': ['UP', 3, 3], 'Bihar': ['BR', 4, 3], 'West Bengal': ['WB', 5, 3], 'Assam': ['AS', 6, 3], 'Nagaland': ['NL', 7, 3],
    'Gujarat': ['GJ', 0, 4], 'Madhya Pradesh': ['MP', 1, 4], 'Chhattisgarh': ['CG', 2, 4], 'Jharkhand': ['JH', 3, 4], 'Odisha': ['OD', 4, 4], 'Meghalaya': ['ML', 6, 4], 'Manipur': ['MN', 7, 4],
    'Dadra and Nagar Haveli and Daman and Diu': ['DD', 0, 5], 'Maharashtra': ['MH', 1, 5], 'Telangana': ['TG', 2, 5], 'Andhra Pradesh': ['AP', 3, 5], 'Tripura': ['TR', 6, 5], 'Mizoram': ['MZ', 7, 5],
    'Goa': ['GA', 0, 6], 'Karnataka': ['KA', 1, 6], 'Tamil Nadu': ['TN', 2, 6], 'Puducherry': ['PY', 3, 6], 'Andaman and Nicobar Islands': ['AN', 5, 6],
    'Lakshadweep': ['LD', 0, 7], 'Kerala': ['KL', 1, 7],
  };
  let MAP_MODE = 'map';
  try { MAP_MODE = localStorage.getItem('jdSalesMapMode') === 'tiles' ? 'tiles' : 'map'; } catch (e) { /* storage blocked: default map */ }
  function renderTiles() {
    const by = new Map(stateKids.map(c => [c.name, c]));
    $('#tiles').innerHTML = Object.entries(TILE).map(([name, [ab, x, y]]) => {
      const c = by.get(name);
      const band = !c ? 'none' : c.band;
      const val = !c || band === 'none' ? 'none' : c.ok ? sgn(Math.round(c.p), v => String(v)) + '%' : '—';   // whole % on the tile; exact in the tooltip
      const cls = band === 'none' ? 'hatch' : band === 'small' ? 'sm' : BAND_DARK[band] ? 'dk' : '';
      const bg = band === 'none' || band === 'small' ? '' : `background:${BAND[band]};`;
      return `<button type="button" class="tile ${cls}" style="grid-column:${x + 1};grid-row:${y + 1};${bg}" data-n="${esc(name)}" aria-label="${esc(name)}: ${esc(val)}${c ? ', ' + esc(fVal(c.v)) + ' ' + measureName() : ''}"><b>${ab}</b><span class="tv tn">${esc(val)}</span></button>`;
    }).join('');
  }
  $('#tiles').addEventListener('mousemove', ev => {
    const b = ev.target.closest('.tile'); if (!b) return untip();
    const c = stateKids.find(x => x.name === b.dataset.n);
    tip(c && c.band !== 'none' ? tipFor(c, `<br><span class="m">${c.share.toFixed(1)}% of India</span>`) : `<b>${esc(b.dataset.n)}</b><br><span class="d">No deals in these dates</span>`, ev);
  });
  $('#tiles').addEventListener('mouseleave', untip);
  $('#tiles').addEventListener('click', ev => { const b = ev.target.closest('.tile'); if (!b) return; const s0 = STATES.indexOf(b.dataset.n); if (s0 >= 0) go({ s: s0, b: -1 }); });
  $('#mapMode').addEventListener('click', ev => {
    const b = ev.target.closest('button'); if (!b || b.dataset.v === MAP_MODE) return;
    MAP_MODE = b.dataset.v;
    try { localStorage.setItem('jdSalesMapMode', MAP_MODE); } catch (e) { /* not remembered */ }
    renderMap(LAST.T, CUR_KIDS, false);
  });

  let stateKids = [];      // state-level figures for the India map, whatever the ranking shows
  function renderMap(T, kids, animate) {
    const L = level(), S = sums();
    const paths = MAP.querySelectorAll('.st'), gD = $('#gDots');
    const legend = rampLegend(level() === 'india' && MAP_MODE === 'tiles' ? 'smsw' : 'dots');
    $('#mapLegend').innerHTML = legend;
    if (L === 'india') {
      stateKids = children(S, ALL_ROWS, 'states').map(c => enrich(c, val(T)));
      const by = new Map(stateKids.map(c => [c.id, c]));
      paths.forEach(el => { const sh = SHAPES[+el.dataset.i], c = by.get(sh.s); el.setAttribute('class', 'st'); el.style.fill = !c || c.band === 'none' ? 'url(#hatch)' : c.band === 'small' ? 'url(#dots)' : BAND[c.band]; });
      gD.innerHTML = '';
      const tilesOn = MAP_MODE === 'tiles';
      $('#mapMode').hidden = false;
      document.querySelectorAll('#mapMode button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === MAP_MODE)));
      MAP.style.display = tilesOn ? 'none' : '';
      $('#tiles').hidden = !tilesOn;
      if (tilesOn) renderTiles();
      $('#mapH').textContent = `${MLABEL[V.m]} against the same dates last year, by state & UT`;
      $('#mapHint').textContent = 'Click a state or UT to open it.';
      $('#gDist').innerHTML = ''; $('#gDl').innerHTML = ''; $('#gEdge').innerHTML = ''; $('#gSel').innerHTML = ''; MAP.classList.remove('dzm');
      goVB(FULL, animate);
      return;
    }
    if (L === 'state' || L === 'district') return renderDistricts(T, kids, animate);
    $('#gDist').innerHTML = ''; $('#gDl').innerHTML = ''; $('#gEdge').innerHTML = ''; $('#gSel').innerHTML = ''; MAP.classList.remove('dzm');
    // inside a branch: the state outlines for context, pincodes as dots sized by the measure
    $('#mapMode').hidden = true; $('#tiles').hidden = true; MAP.style.display = '';
    paths.forEach(el => { const sh = SHAPES[+el.dataset.i]; el.setAttribute('class', 'st ' + (sh.s === V.s ? 'on' : 'ctx')); el.style.fill = ''; });
    const area = rowsOf(V.s, V.b, V.d);
    let target = null;
    if (L === 'state') { const sh = SHAPES.find(x => x.s === V.s); target = sh ? fitBox(sh.box, .06) : null; }
    if (!target) { const b = rowsBox(area); target = b ? fitBox(b, .12) : FULL; }
    if (L === 'branch' && V.s >= 0) { const b = rowsBox(area); if (b) target = fitBox(b, .14); }
    const pins = kids.length && kids[0].kind === 'pin' ? kids : children(S, area, 'pincodes').map(c => enrich(c, val(T)));
    const mx = Math.max(1, ...pins.map(c => c.v));
    const unit = target[2] / Math.max(300, MAP.clientWidth || 500);       // viewBox units per screen pixel at the target zoom
    const faint = L === 'branch' && V.s >= 0 ? ROWS_BY_STATE[V.s].filter(p => COLS.br[p] !== V.b && COLS.lat[p] !== null && (S.ty[p] > 0 || S.ly[p] > 0)) : [];
    let html = faint.map(p => `<circle class="faint" cx="${PX(COLS.lon[p]).toFixed(1)}" cy="${PY(COLS.lat[p]).toFixed(1)}" r="${(1.8 * unit).toFixed(2)}"/>`).join('');
    const sorted = pins.filter(c => COLS.lat[c.id] !== null).sort((a, b) => b.v - a.v);
    html += sorted.map(c => `<circle data-p="${c.id}" cx="${PX(COLS.lon[c.id]).toFixed(1)}" cy="${PY(COLS.lat[c.id]).toFixed(1)}" r="${((2.2 + 10 * Math.sqrt(Math.max(0, c.v) / mx)) * unit).toFixed(2)}" fill="${DOT[c.band]}"/>`).join('');
    gD.innerHTML = html;
    gD._pins = new Map(pins.map(c => [c.id, c]));
    const noLoc = pins.length - sorted.length;
    $('#mapH').textContent = `Pincodes in ${areaName()}, against the same dates last year`;
    $('#mapHint').textContent = `Dot size shows ${measureName()}; click a pincode for its details.` + (noLoc > 0 ? ` ${noLoc} pincode${noLoc > 1 ? 's have' : ' has'} no reliable location and ${noLoc > 1 ? 'are' : 'is'} not drawn.` : '');
    goVB(target, animate);
  }
  // a state: its districts filled by change, named where the name fits. A district: the state's districts for context
  // (click one to move to it), the open district in white with its pincodes as dots.
  function renderDistricts(T, kids, animate) {
    const L = level(), S = sums();
    $('#mapMode').hidden = true; $('#tiles').hidden = true; MAP.style.display = '';
    districtWorld();
    MAP.classList.add('dzm'); MAP.classList.toggle('dlev', L === 'district');
    $('#bdOn').setAttribute('d', DMAP.b.filter((_, k) => BD_ST[k][0] === V.s || BD_ST[k][1] === V.s).map(lineD).join(''));
    const ids = DIST_OF_STATE[V.s] || [];
    const sh = SHAPES.find(x => x.s === V.s);
    const target = L === 'district' ? fitBox(dShape(V.d).box, .12, 6) : sh ? fitBox(sh.box, .06) : FULL;
    // viewBox units per screen pixel: the map keeps its aspect, so the tighter of width and height sets the scale
    const unit = Math.max(target[2] / Math.max(300, MAP.clientWidth || 500), target[3] / Math.max(300, MAP.clientHeight || 540));
    const dk = L === 'state' && V.kids === 'districts' ? kids : children(S, rowsOf(V.s, -1), 'districts').map(c => enrich(c, val(T)));
    const by = new Map(dk.map(c => [c.id, c]));
    let html = '', lab = '';
    for (const i of ids) {
      const g = dShape(i), c = by.get(i);
      if (L === 'district') { html += `<path class="ds ${i === V.d ? 'on' : 'ctx'}" data-d="${i}" d="${g.d}"/>`; continue; }
      const fill = !c || c.band === 'none' ? 'url(#hatch)' : c.band === 'small' ? 'url(#dots)' : BAND[c.band];
      html += `<path class="ds" data-d="${i}" d="${g.d}" style="fill:${fill}"/>`;
    }
    // names, biggest districts first, only where the name fits inside its district and clears the names already placed
    if (L === 'state') {
      const placed = [], FS = 10.5, CW = 5.7;
      const big = [...ids].sort((a, b) => { const A = dShape(a).box, B = dShape(b).box; return (B[2] - B[0]) * (B[3] - B[1]) - (A[2] - A[0]) * (A[3] - A[1]); });
      for (const i of big) {
        const g = dShape(i), c = by.get(i), w = (g.box[2] - g.box[0]) / unit, h = (g.box[3] - g.box[1]) / unit, tw = DNAME[i].length * CW + 4;
        if (tw > w * .85 || h < 18) continue;
        const bx = [g.lx / unit - tw / 2, g.ly / unit - 7, g.lx / unit + tw / 2, g.ly / unit + 7];
        if (bx[0] < target[0] / unit || bx[2] > (target[0] + target[2]) / unit) continue;
        if (placed.some(o => bx[0] < o[2] && bx[2] > o[0] && bx[1] < o[3] && bx[3] > o[1])) continue;
        placed.push(bx);
        lab += `<text x="${g.lx.toFixed(1)}" y="${(g.ly + FS * .36 * unit).toFixed(1)}"${c && BAND_DARK[c.band] ? ' class="inv"' : ''}>${esc(DNAME[i])}</text>`;
      }
    }
    $('#gDist').innerHTML = html;
    $('#gDist')._d = by;
    // district borders as their own layer over the fills: a white line with a fine grey core reads on a colour band and on
    // the dotted "too few" fill alike; the open district's outline goes on top of everything in ink
    const ed = DMAP.e.filter((_, k) => E_ST[k] === V.s).map(lineD).join('');
    $('#gEdge').innerHTML = `<path class="eh" d="${ed}"/><path class="ec" d="${ed}"/>`;
    $('#gSel').innerHTML = L === 'district' ? `<path d="${dShape(V.d).d}"/>` : '';
    const gl = $('#gDl');
    gl.setAttribute('font-size', (10.5 * unit).toFixed(3)); gl.setAttribute('stroke-width', (2.2 * unit).toFixed(3));
    gl.innerHTML = lab;
    const gD = $('#gDots');
    if (L === 'district') {
      const pins = kids.length && kids[0].kind === 'pin' ? kids : children(S, rowsOf(V.s, -1, V.d), 'pincodes').map(c => enrich(c, val(T)));
      const mx = Math.max(1, ...pins.map(c => c.v));
      const sorted = pins.filter(c => COLS.lat[c.id] !== null).sort((a, b) => b.v - a.v);
      const rOf = c => (2.6 + 11 * Math.sqrt(Math.max(0, c.v) / mx)) * unit;
      gD.innerHTML = sorted.map(c => `<circle data-p="${c.id}" cx="${PX(COLS.lon[c.id]).toFixed(1)}" cy="${PY(COLS.lat[c.id]).toFixed(1)}" r="${rOf(c).toFixed(2)}" fill="${DOT[c.band]}"/>`).join('');
      // where you are: the biggest pincodes named beside their dots, then the neighbouring districts in grey, each only
      // where it clears what is already placed and stays inside the view
      const placed = [], inView = b => b[0] > target[0] / unit + 2 && b[2] < (target[0] + target[2]) / unit - 2 && b[1] > target[1] / unit + 2 && b[3] < (target[1] + target[3]) / unit - 2;
      const clear = b => inView(b) && !placed.some(o => b[0] < o[2] && b[2] > o[0] && b[1] < o[3] && b[3] > o[1]);
      for (const c of sorted.slice(0, 40)) {
        const x = PX(COLS.lon[c.id]) / unit, y = PY(COLS.lat[c.id]) / unit, r = rOf(c) / unit;
        placed.push([x - r, y - r, x + r, y + r]);
      }
      let n = 0;
      for (const c of sorted.slice(0, 12)) {
        if (n >= 6 || !(c.v > 0)) break;
        const name = (COLS.place[c.id] || COLS.pin[c.id]).replace(/\s+(B\.?O|S\.?O|H\.?O)\.?$/i, ''), t = name.length > 18 ? name.slice(0, 17) + '…' : name;
        const x = PX(COLS.lon[c.id]) / unit, y = PY(COLS.lat[c.id]) / unit, r = rOf(c) / unit, tw = t.length * 5.9 + 4;
        for (const [bx, anchor, tx] of [[[x + r + 3, y - 7, x + r + 3 + tw, y + 7], 'start', x + r + 4], [[x - r - 3 - tw, y - 7, x - r - 3, y + 7], 'end', x - r - 4]]) {
          if (!clear(bx)) continue;
          placed.push(bx); n++;
          lab += `<text class="pl" x="${(tx * unit).toFixed(1)}" y="${((y + 3.8) * unit).toFixed(1)}" style="text-anchor:${anchor}">${esc(t)}</text>`;
          break;
        }
      }
      for (const i of ids) {
        if (i === V.d) continue;
        const g = dShape(i), tw = DNAME[i].length * 5.7 + 4, bx = [g.lx / unit - tw / 2, g.ly / unit - 7, g.lx / unit + tw / 2, g.ly / unit + 7];
        if (!clear(bx)) continue;
        placed.push(bx);
        lab += `<text class="ctxn" x="${g.lx.toFixed(1)}" y="${(g.ly + 3.8 * unit).toFixed(1)}">${esc(DNAME[i])}</text>`;
      }
      gl.innerHTML = lab;
      gD._pins = new Map(pins.map(c => [c.id, c]));
      const noLoc = pins.length - sorted.length;
      $('#mapH').textContent = `Pincodes in ${areaName()}, against the same dates last year`;
      $('#mapHint').textContent = `Dot size shows ${measureName()}; click a pincode for its details, or another district to move to it.` + (noLoc > 0 ? ` ${noLoc} pincode${noLoc > 1 ? 's have' : ' has'} no reliable location and ${noLoc > 1 ? 'are' : 'is'} not drawn.` : '');
    } else {
      gD.innerHTML = '';
      const none = (by.get(-1) || {}).v || 0;
      $('#mapH').textContent = `${MLABEL[V.m]} against the same dates last year, by district`;
      const one = V.m === 'rv' ? false : Math.round(none) === 1 && none < 1.5;
      $('#mapHint').textContent = 'Click a district to open it.' + (none > 0 ? ` ${fVal(none)} ${one ? measureName().replace(/s$/, '') + ' is' : measureName() + ' are'} in pincodes with no known district and ${one ? 'is' : 'are'} not on the map.` : '');
    }
    goVB(target, animate);
  }
  MAP.addEventListener('mousemove', ev => {
    const t = ev.target;
    if (t.classList.contains('st')) {
      const sh = SHAPES[+t.dataset.i];
      if (level() === 'india') { const c = stateKids.find(x => x.id === sh.s); tip(c && c.band !== 'none' ? tipFor(c, `<br><span class="m">${c.share.toFixed(1)}% of India</span>`) : `<b>${esc(sh.name)}</b><br><span class="d">No deals in these dates</span>${c && c.lv > 0 ? `<br><span class="m">${esc(fVal(c.lv))} ${measureName()} on the same dates last year</span>` : ''}`, ev); }
      else if (sh.s !== V.s && sh.s >= 0) tip(`<b>${esc(STATES[sh.s])}</b><br><span class="m">Click to open</span>`, ev);
      else untip();
    } else if (t.classList.contains('dc')) {
      const s = +t.dataset.s;
      if (s >= 0 && s !== V.s) tip(`<b>${esc(STATES[s])}</b><br><span class="m">Click to open</span>`, ev); else untip();
    } else if (t.classList.contains('ds')) {
      const i = +t.dataset.d, c = $('#gDist')._d.get(i);
      if (level() === 'district' && i !== V.d) tip(`<b>${esc(DNAME[i])}</b><br><span class="m">Click to open</span>`, ev);
      else if (level() === 'state') tip(c && c.band !== 'none' ? tipFor(c, `<br><span class="m">${c.share.toFixed(1)}% of ${esc(STATES[V.s])}</span>`) : `<b>${esc(DNAME[i])}</b><br><span class="d">No deals in these dates</span>${c && c.lv > 0 ? `<br><span class="m">${esc(fVal(c.lv))} ${measureName()} on the same dates last year</span>` : ''}`, ev);
      else untip();
    } else if (t.tagName === 'circle' && t.dataset.p) {
      const c = $('#gDots')._pins.get(+t.dataset.p), dn = c ? DNAME[COLS.dm[c.id]] : '';
      if (c) tip(tipFor(c, `<br><span class="m">${dn ? esc(dn) + ' district · ' : ''}${esc(BRANCHES[COLS.br[c.id]])} branch</span>`), ev);
    } else untip();
  });
  MAP.addEventListener('mouseleave', untip);
  MAP.addEventListener('click', ev => {
    const t = ev.target;
    if (t.classList.contains('st')) { const sh = SHAPES[+t.dataset.i]; if (sh.s >= 0 && sh.s !== V.s) go({ s: sh.s, b: -1 }); }
    else if (t.classList.contains('ds')) { const i = +t.dataset.d; if (i !== V.d) go({ s: V.s, b: -1, d: i }); }
    else if (t.classList.contains('dc')) { const st = +t.dataset.s; if (st >= 0 && st !== V.s) go({ s: st, b: -1 }); }
    else if (t.tagName === 'circle' && t.dataset.p) openPin(+t.dataset.p);
  });

  /* =========================================================== bridge */
  function renderBridge(T, kids) {
    const el = $('#bridge');
    const moved = kids.filter(c => c.d !== 0).sort((a, b) => a.d - b.d);
    if (!moved.length) { el.innerHTML = `<p class="empty">No change against last year here.</p>`; return; }
    const losers = moved.filter(c => c.d < 0).slice(0, 5), gainers = moved.filter(c => c.d > 0).slice(-5).reverse();
    const shown = new Set([...losers, ...gainers]);
    const other = moved.filter(c => !shown.has(c)).reduce((s, c) => s + c.d, 0);
    const v = val(T), lv = lval(T);
    const steps = [{ l: 'Last year', v: lv, base: 1 }, ...losers.map(c => ({ l: kidLabel(c), v: c.d, c })), ...gainers.map(c => ({ l: kidLabel(c), v: c.d, c }))];
    if (Math.abs(other) > 1e-9) steps.push({ l: `Other ${KID_LOW[V.kids]}`, v: other });
    steps.push({ l: 'This year', v, base: 1 });
    let run = 0; const pos = [];
    for (const s of steps) { if (s.base) { run = s.v; pos.push([0, s.v]); } else { pos.push([run, run + s.v]); run += s.v; } }
    const ends = pos.flatMap(x => x).filter((x, i) => !steps[Math.floor(i / 2)].base || i % 2 === 1);
    let lo = Math.min(...ends), hi = Math.max(...ends); const pad = (hi - lo) * .18 || Math.abs(hi) * .05 || 1;
    lo = Math.max(0, lo - pad); hi += pad * .6;
    const W = Math.max(300, Math.round(el.clientWidth || 470)), L = W < 400 ? 128 : 150, R = 66, RH = 27, H = steps.length * RH + 6;
    const X = x => L + (x - lo) / (hi - lo) * (W - L - R);
    const maxC = Math.floor((L - 10) / 6.7), trunc = s => s.length > maxC ? s.slice(0, maxC - 1) + '…' : s;
    let svg = '';
    steps.forEach((s, i) => {
      const y = 4 + i * RH, [a, b] = pos[i];
      if (s.base) {
        svg += `<text class="lab base" x="0" y="${y + 17}">${esc(s.l)}</text><rect class="grow" x="${X(lo)}" y="${y + 5}" width="${Math.max(1, X(s.v) - X(lo))}" height="15" rx="2" fill="#14213D"/>` +
          `<text class="val" x="${X(s.v) + 6}" y="${y + 17}" fill="#14213D" font-weight="600">${esc(fVal(s.v))}</text>`;
      } else {
        const x0 = X(Math.min(a, b)), x1 = X(Math.max(a, b)), neg = s.v < 0;
        // the value sits outside the bar on its own side, unless it would run into the names or off the card
        const vw = fDelta(s.v).length * 6.6;
        let left = neg;
        if (left && x0 - 5 - vw < L - 2) left = false;
        if (!left && x1 + 5 + vw > W - 2) left = true;
        const vx = left ? x0 - 5 : x1 + 5, va = left ? 'end' : 'start';
        svg += `<line x1="${X(a)}" x2="${X(a)}" y1="${y - 6}" y2="${y + 22}" stroke="#D5DBE3" stroke-dasharray="2 2"/>` +
          `<text class="lab" x="0" y="${y + 17}">${esc(trunc(s.l))}</text><rect class="grow${neg ? ' rt' : ''}" style="animation-delay:${i * 30}ms" x="${x0}" y="${y + 7}" width="${Math.max(1.5, x1 - x0)}" height="11" rx="1.5" fill="${neg ? '#C8372D' : '#0E8A6A'}"/>` +
          `<text class="val" x="${vx}" y="${y + 16.5}" text-anchor="${va}" fill="${neg ? '#B23126' : '#0B7558'}">${esc(fDelta(s.v))}</text>` +
          (s.c ? `<rect class="hit" data-i="${i}" x="0" y="${y}" width="${W}" height="${RH}"/>` : '');
      }
    });
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Change against last year, by ${KID_ONE[V.kids]}">${svg}</svg>` +
      `<p class="hint">Same dates last year. The five biggest drops and gains among ${KID_LOW[V.kids]}; the two dark bars start at ${esc(fVal(lo))}, not zero, so the changes are visible.</p>`;
    el._steps = steps;
    // how the areas below are doing: a count per band (only those with enough deals last year)
    // every area below, in three groups: compared against last year (by band), too small to compare, no deals at all
    const real = kids.filter(c => !UNPLACED.test(c.name));   // a bucket of unlocated deals is not a state or branch
    const all = real.length, ok = real.filter(c => c.ok && c.band !== 'none'), none = real.filter(c => c.band === 'none'), small = all - ok.length - none.length;
    if (all >= 3 && kids[0].kind !== 'pin' || ok.length >= 3) {
      const cnt = BAND_LABEL.map(([k]) => ok.filter(c => c.band === k).length);
      const ahead = ok.filter(c => c.p > 0).length, nm = KID_LOW[V.kids], minK = minFor(KIND_OF[V.kids]);
      const extra = [small ? `${small} too small to compare (under ${minK} deals last year)` : '', none.length ? `<b class="dn">${none.length} with no deals</b> in these dates` : ''].filter(Boolean).join('; ');
      const seg = (n, cls, bg, t) => n ? `<span style="flex-grow:${n};${bg}" class="${cls}" title="${esc(t)}: ${n}">${n}</span>` : '';
      el.insertAdjacentHTML('beforeend', `<div class="spread"><div class="t"><b>${ahead} of the ${all}</b> ${nm} are ahead of last year${extra ? `<span class="mu">; ${extra}</span>` : ''}.</div>` +
        `<div class="sbar">${BAND_LABEL.map(([k, l], i) => seg(cnt[i], BAND_DARK[k] ? '' : 'lt', `background:${BAND[k]}`, l)).join('')}` +
        seg(small, 'lt sm', 'background:#EEF1F5', 'Too small to compare') + seg(none.length, 'lt hatch', '', 'No deals in these dates') + `</div>` +
        `<div class="sk"><span>below ${MINUS}10%</span><span>+25% or more${small ? ' · too small' : ''}${none.length ? ' · none' : ''}</span></div></div>`);
    }
  }
  $('#bridge').addEventListener('mousemove', ev => { const t = ev.target.closest('.hit'); if (!t) return untip(); const s = $('#bridge')._steps[+t.dataset.i]; if (s && s.c) tip(tipFor(s.c), ev); });
  $('#bridge').addEventListener('mouseleave', untip);
  $('#bridge').addEventListener('click', ev => { const t = ev.target.closest('.hit'); if (t) { const s = $('#bridge')._steps[+t.dataset.i]; if (s && s.c) openKid(s.c); } });

  /* =========================================================== ranking (virtual list) */
  let RANK = [];
  const RH = 36;
  function renderRank(kids) {
    $('#rankH').textContent = `${KID_NAME[V.kids]} ranked by ${measureName()}`;
    $('#kids').innerHTML = KIDS[level()].map(k => `<button type="button" data-k="${k}" aria-pressed="${k === V.kids}">${KID_NAME[k]}</button>`).join('');
    const q = $('#rankSearch').value.trim().toLowerCase();
    const all = [...kids].sort((a, b) => b.v - a.v);
    all.forEach((c, i) => { c.rank = i + 1; });
    RANK = q ? all.filter(c => kidLabel(c).toLowerCase().includes(q)) : all;
    RANK._max = Math.max(1e-9, ...all.map(c => c.v));
    const box = $('#rank');
    box.scrollTop = 0;
    box.innerHTML = RANK.length ? `<div style="height:${RANK.length * RH}px;position:relative" id="rankIn"></div>` : `<p class="empty">${q ? 'Nothing matches “' + esc(q) + '”.' : 'No deals here in these dates.'}</p>`;
    drawRank();
  }
  function drawRank() {
    const box = $('#rank'), inn = $('#rankIn'); if (!inn) return;
    const a = Math.max(0, Math.floor(box.scrollTop / RH) - 8), b = Math.min(RANK.length, a + Math.ceil((box.clientHeight || 520) / RH) + 16);
    let h = '';
    for (let i = a; i < b; i++) {
      const c = RANK[i];
      h += `<button type="button" class="rk" style="position:absolute;top:${i * RH}px" data-i="${i}"><span class="n tn">${c.rank}</span><span class="nm"><span>${esc(c.name)}${c.sub ? ` <small class="mu">${esc(c.sub)}</small>` : ''}</span><i style="width:${Math.max(.5, c.v / RANK._max * 100)}%"></i></span>` +
        `<span class="v tn">${esc(fVal(c.v))}</span><span class="c tn ${clsP(c.ok ? c.p : null)}">${esc(c.ok ? fPct(c.p) : '—')}</span></button>`;
    }
    inn.innerHTML = h;
  }
  $('#rank').addEventListener('scroll', () => requestAnimationFrame(drawRank), { passive: true });
  $('#rank').addEventListener('click', ev => { const t = ev.target.closest('.rk'); if (t) openKid(RANK[+t.dataset.i]); });
  $('#rank').addEventListener('mousemove', ev => { const t = ev.target.closest('.rk'); if (!t) return untip(); const c = RANK[+t.dataset.i]; tip(tipFor(c, `<br><span class="m">${c.share.toFixed(1)}% of ${esc(areaName())}</span>`), ev); });
  $('#rank').addEventListener('mouseleave', untip);
  $('#rankSearch').addEventListener('input', () => renderRank(CUR_KIDS));
  $('#kids').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b && b.dataset.k !== V.kids) { V.kids = b.dataset.k; V.sort = null; $('#rankSearch').value = ''; $('#tableSearch').value = ''; render(false, true); } });

  /* =========================================================== trend by month */
  function monthBars(M, opts = {}) {
    const W = opts.w || 520, H = opts.h || 230, padL = 46, padB = opts.short ? 24 : 36, top = 10;
    const C = M.cust, ty = V.m === 'rv' ? M.tyRv : V.m === 'cust' ? C.ty : M.ty, ly = V.m === 'rv' ? M.lyRv : V.m === 'cust' ? C.ly : M.ly, lyR = V.m === 'rv' ? M.lyRRv : V.m === 'cust' ? C.lyR : M.lyR;
    const lyFull = i => i < CUR ? ly[i] : i === CUR ? ly[i] : ly[i] + lyR[i];
    const mx = Math.max(1e-9, ...ty.slice(0, CUR + 1), ...Array.from({ length: 12 }, (_, i) => lyFull(i)));
    const gw = (W - padL - 6) / 12, bw = Math.min(16, gw * .34);
    const Y = v => H - padB - v / mx * (H - padB - top);
    const ticks = niceTicks(mx, 3);
    const inP = i => { const a = MONTH_OF[V.from], b = MONTH_OF[V.to]; return i >= a && i <= b; };
    const fT = x => V.m !== 'rv' ? (x >= 1000 ? IN0.format(x / 1000) + 'k' : IN0.format(x)) : fRv(x);
    let s = ticks.map(t => `<line class="grid" x1="${padL}" x2="${W}" y1="${Y(t)}" y2="${Y(t)}"/><text class="ax" x="${padL - 6}" y="${Y(t) + 4}" text-anchor="end">${esc(fT(t))}</text>`).join('');
    for (let i = 0; i < 12; i++) {
      const x = padL + i * gw + gw / 2, out = opts.noPeriod ? '' : (inP(i) ? '' : ' out');
      const lyv = lyFull(i);
      s += `<rect class="${i > CUR ? 'bar-lyr' : 'bar-ly'}${out}" x="${x - bw - 1}" y="${Y(lyv)}" width="${bw}" height="${Math.max(0, H - padB - Y(lyv))}" rx="2"/>`;
      if (i <= CUR) s += `<rect class="bar-ty${out}" x="${x + 1}" y="${Y(ty[i])}" width="${bw}" height="${Math.max(0, H - padB - Y(ty[i]))}" rx="2"/>`;
      const partial = i === CUR && META.end.slice(8) !== String(new Date(Date.UTC(+META.end.slice(0, 4), +META.end.slice(5, 7), 0)).getUTCDate());
      // month names stay short when the bars are close; a part month gets its days on a second line
      const mName = opts.short || gw < 32 ? FYM[i].slice(0, 1) : gw < 46 ? FYM[i].slice(0, 3) : FYM[i];
      s += `<text class="ax" x="${x}" y="${H - (opts.short ? 7 : 19)}" text-anchor="middle">${mName}${partial && !opts.short ? `<tspan x="${x}" dy="12">1–${+META.end.slice(8)}</tspan>` : ''}</text>`;
      s += `<rect class="mon-hit" data-m="${i}" x="${x - gw / 2}" y="${top}" width="${gw}" height="${H - padB - top}"/>`;
    }
    return { svg: `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg>`, ty, lyFull, fT };
  }
  function niceTicks(mx, n) { const raw = mx / n, p = Math.pow(10, Math.floor(Math.log10(raw))), st = [1, 2, 2.5, 5, 10].map(k => k * p).find(k => k >= raw) || raw; const out = []; for (let v = 0; v <= mx + 1e-9; v += st) out.push(v); return out; }
  let TREND = null;
  function renderTrend(rows) {
    const M = monthly(rows);
    if (V.m === 'cust') M.cust = custMonthly(maskOf(rows));
    const r = monthBars(M, { w: Math.max(300, Math.round($('#trend').clientWidth || 520)) });
    TREND = { M, r };
    const fy = META.fy.slice(2, 4), ny = String(+fy + 1).padStart(2, '0'), lfy = String(+fy - 1).padStart(2, '0');
    $('#trendH').textContent = `${MLABEL[V.m]} by month`;
    $('#trend').innerHTML = `<div class="keyline"><span><i style="background:var(--blue)"></i>FY ${fy}–${ny}</span><span><i style="background:var(--ly)"></i>FY ${lfy}–${fy}, same dates</span><span><i style="background:var(--ly-2)"></i>rest of last year</span></div>${r.svg}` +
      `<p class="hint">Months outside the dates you picked are faded. ${FYM[CUR]} compares the same days of both years.</p>`;
  }
  $('#trend').addEventListener('mousemove', ev => {
    const t = ev.target.closest('.mon-hit'); if (!t || !TREND) return untip();
    const i = +t.dataset.m, { r } = TREND, ty = r.ty[i], ly = r.lyFull(i);
    const y = i < 9 ? +META.fy.slice(0, 4) : +META.fy.slice(0, 4) + 1;
    const p = i <= CUR && ly > 0 ? (ty / ly - 1) * 100 : null;
    tip(i <= CUR ? `<b>${FYM[i]} ${y}</b>${i === CUR ? ' <span class="m">(to ' + esc(fDate(dOf(META.days - 1))) + ')</span>' : ''}<br>${esc(fVal(ty))} ${measureName()}<br><span class="m">${FYM[i]} ${y - 1}: ${esc(fVal(ly))}</span>${p !== null ? `<br><span class="${{ up: 'u', dn: 'd', mu: 'm' }[clsP(p)]}">${esc(fPct(p))}</span>` : ''}`
      : `<b>${FYM[i]} ${y - 1}</b><br>${esc(fVal(ly))} ${measureName()} last year<br><span class="m">This year's ${FYM[i]} has not happened yet</span>`, ev);
  });
  $('#trend').addEventListener('mouseleave', untip);

  /* =========================================================== mix */
  function mixBars(parts, keyLabels, colors) {
    return parts.map(([lab, vals]) => {
      const tot = vals.reduce((s, x) => s + x, 0) || 1;
      return `<div class="mixbar"><span>${lab}</span><span class="bars">${vals.map((x, i) => { const w = x / tot * 100; return `<span class="${colors[i] === '#C9D3E0' ? 'lt' : ''}" style="flex-grow:${w.toFixed(3)};flex-basis:0;background:${colors[i]}" title="${esc(keyLabels[i])}: ${w.toFixed(1)}%">${w >= 9 ? w.toFixed(0) + '%' : ''}</span>`; }).join('')}</span></div>`;
    }).join('');
  }
  function mixBlock(A, B) {
    const pct = (a, x) => a.all ? x / a.all * 100 : 0;
    const row = (title, now, then, keys, colors, partsA, partsB) => `<div class="mixrow"><div class="t"><b>${title}</b><span class="mu">${keys[0]} ${pct(A, now).toFixed(1)}% <span class="${clsPts(pct(A, now) - pct(B, then))}">(${fPts(pct(A, now) - pct(B, then))})</span></span></div>` +
      mixBars([['This year', partsA], ['Last year', partsB]], keys, colors) + `<div class="mixkey">${keys.map((k, i) => `<span><i style="background:${colors[i]}"></i>${k}</span>`).join('')}</div></div>`;
    return row('Fresh or renewal', A.fresh, B.fresh, ['Fresh', 'Renewal'], ['#1C6FB8', '#C9D3E0'], [A.fresh, A.all - A.fresh], [B.fresh, B.all - B.fresh]) +
      row('ECS (auto-debit) or not', A.ecs, B.ecs, ['ECS', 'Non-ECS'], ['#1C6FB8', '#C9D3E0'], [A.ecs, A.all - A.ecs], [B.ecs, B.all - B.ecs]) +
      row('Channel', A.ch[0], B.ch[0], CH, CHC, A.ch, B.ch);
  }
  function renderMix(T) {
    $('#mix').innerHTML = mixBlock(mixOf(T.tyK), mixOf(T.lyK)) + `<p class="hint">Shares of deals. Joint JDA + JDS deals count half to each.</p>`;
  }

  /* =========================================================== size against growth */
  let QPTS = [];
  function renderQuad(T, kids) {
    const el = $('#quad');
    const pts = kids.filter(c => c.ok && c.v > 0).sort((a, b) => b.v - a.v).slice(0, 400);
    $('#quadH').textContent = `Size against growth, by ${KID_ONE[V.kids]}`;
    if (pts.length < 3) { el.innerHTML = `<p class="empty">Not enough ${KID_LOW[V.kids]} with ${minFor(KIND_OF[V.kids])}+ deals last year to compare.</p>`; QPTS = []; return; }
    const W = Math.max(300, Math.round(el.clientWidth || 470)), H = W < 560 ? 360 : 320, L = 44, B = 26, Tp = 12, Rt = 12, LR = 40;
    const xs = pts.map(c => Math.log10(c.share)), x0 = Math.min(...xs), x1 = Math.max(...xs);
    const ps = pts.map(c => c.p).sort((a, b) => a - b);
    const yLo = Math.max(-60, Math.min(-5, ps[Math.floor(ps.length * .03)] - 3)), yHi = Math.min(80, Math.max(5, ps[Math.ceil(ps.length * .97) - 1] + 3));
    const X = c => L + (Math.log10(c.share) - x0) / ((x1 - x0) || 1) * (W - L - Rt - LR), Y = p => Tp + (yHi - Math.max(yLo, Math.min(yHi, p))) / (yHi - yLo) * (H - Tp - B);
    const avg = Math.log10(100 / pts.length), xa = L + (avg - x0) / ((x1 - x0) || 1) * (W - L - Rt - LR);
    const mx = Math.max(...pts.map(c => c.v));
    const area = lval(T) > 0 ? (val(T) / lval(T) - 1) * 100 : 0;
    let s = `<line class="grid" x1="${L}" x2="${W - Rt}" y1="${Y(0)}" y2="${Y(0)}" stroke="#B9C2CF"/>`;
    if (xa > L && xa < W - Rt) s += `<line x1="${xa}" x2="${xa}" y1="${Tp}" y2="${H - B}" stroke="#D5DBE3" stroke-dasharray="3 3"/>`;
    s += `<line x1="${L}" x2="${W - Rt}" y1="${Y(area)}" y2="${Y(area)}" stroke="#14213D" stroke-dasharray="4 3" opacity=".5"/><text class="qlab" x="${L + 4}" y="${Y(area) + (Y(area) > H / 2 ? -5 : 13)}" fill="#3D4860">${esc(areaName())} ${esc(fPct(area))}</text>`;
    s += `<text class="qlab" x="${W - Rt - 2}" y="${Tp + 10}" text-anchor="end">Large · growing</text><text class="qlab" x="${W - Rt - 2}" y="${H - B - 6}" text-anchor="end">Large · shrinking</text>` +
      `<text class="qlab" x="${L + 4}" y="${Tp + 10}">Small · growing</text><text class="qlab" x="${L + 4}" y="${H - B - 6}">Small · shrinking</text>`;
    [yLo, 0, yHi].forEach(v => { s += `<text class="ax" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v > 0 ? '+' : v < 0 ? MINUS : ''}${Math.abs(Math.round(v))}%</text>`; });
    s += `<text class="ax" x="${L}" y="${H - 6}">smaller share</text><text class="ax" x="${W - Rt}" y="${H - 6}" text-anchor="end">larger share of ${esc(areaName())} →</text>`;
    QPTS = pts;
    const order = [...pts].sort((a, b) => a.v - b.v);
    s += order.map(c => `<circle data-i="${pts.indexOf(c)}" cx="${X(c).toFixed(1)}" cy="${Y(c.p).toFixed(1)}" r="${(3 + 11 * Math.sqrt(c.v / mx)).toFixed(1)}" fill="${DOT[c.band] || '#C9D1DC'}" fill-opacity=".9"/>`).join('');
    // every bubble is labelled beside it: a state or UT by its two-letter code (the tile codes), others by a short name;
    // the label takes the first of eight clear spots around the bubble, else the least crowded one
    const yA = Y(area) + (Y(area) > H / 2 ? -5 : 13);   // the baseline's own label
    const taken = [[W - Rt - 100, Tp, W - Rt, Tp + 14], [W - Rt - 108, H - B - 18, W - Rt, H - B], [L, Tp, L + 104, Tp + 14], [L, H - B - 18, L + 104, H - B],
      [L, yA - 10, L + 6.4 * (areaName().length + 7) + 6, yA + 3]];
    const rOf = c => 3 + 11 * Math.sqrt(c.v / mx);
    const bub = pts.map(c => ({ c, b: [X(c) - rOf(c), Y(c.p) - rOf(c), X(c) + rOf(c), Y(c.p) + rOf(c)] }));
    const over = (a, b) => a[0] < b[2] && a[2] > b[0] && a[1] < b[3] && a[3] > b[1];
    const short = c => c.kind === 'state' ? ((TILE[c.name] || [])[0] || c.name.slice(0, 2).toUpperCase()) : c.kind === 'pin' ? c.name : (c.name.length > 10 ? c.name.slice(0, 9) + '…' : c.name);
    const byDelta = [...pts].sort((a, b) => a.d - b.d);
    const all = pts.length <= 60;      // label every bubble when the chart can carry it; otherwise the biggest and the movers
    const want = all ? [...pts].sort((a, b) => b.v - a.v) : [...new Set([...byDelta.slice(0, 3).filter(c => c.d < 0), ...byDelta.slice(-3).filter(c => c.d > 0), ...pts.slice(0, 20)])];
    for (const c of want) {
      const t = short(c), r = rOf(c), cx = X(c), cy = Y(c.p), w = t.length * 6.6 + 2;
      const d = r + 3, tries = [[cx + d, cy + 3.5, 'start'], [cx - d, cy + 3.5, 'end'], [cx, cy - d - 1, 'middle'], [cx, cy + d + 9, 'middle'],
        [cx + d * .75, cy - d * .75, 'start'], [cx + d * .75, cy + d * .75 + 8, 'start'], [cx - d * .75, cy - d * .75, 'end'], [cx - d * .75, cy + d * .75 + 8, 'end']];
      let best = null, bestScore = 1e9;
      for (const [x, y, a] of tries) {
        const x0 = a === 'start' ? x : a === 'end' ? x - w : x - w / 2, box = [x0, y - 9.5, x0 + w, y + 2.5];
        if (box[0] < 2 || box[2] > W - 2 || box[1] < 0 || box[3] > H - B) continue;
        const score = taken.filter(b => over(box, b)).length * 3 + bub.filter(o => o.c !== c && over(box, o.b)).length;
        if (score < bestScore) { bestScore = score; best = [x, y, a, box]; }
        if (score === 0) break;
      }
      if (!best || (!all && bestScore > 0)) continue;
      taken.push(best[3]);
      s += `<text class="qname${c.kind === 'state' ? ' qcode' : ''}" x="${best[0].toFixed(1)}" y="${best[1].toFixed(1)}" text-anchor="${best[2]}">${esc(t)}</text>`;
    }
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Share against change for each ${KID_ONE[V.kids]}">${s}</svg>` +
      `<p class="hint">Across: share of ${esc(areaName())}'s ${measureName()} (log scale; dashed line = an even share). Up: change against last year. ${pts.length < kids.length ? `Only the ${pts.length} with ${minFor(KIND_OF[V.kids])}+ deals last year.` : ''}</p>`;
  }
  $('#quad').addEventListener('mousemove', ev => { const t = ev.target.closest('circle'); if (!t) return untip(); const c = QPTS[+t.dataset.i]; tip(tipFor(c, `<br><span class="m">${c.share.toFixed(2)}% of ${esc(areaName())}</span>`), ev); });
  $('#quad').addEventListener('mouseleave', untip);
  $('#quad').addEventListener('click', ev => { const t = ev.target.closest('circle'); if (t) openKid(QPTS[+t.dataset.i]); });

  /* =========================================================== concentration: every pincode, with a slider */
  let CONC = null, CONC_F = 0.1;
  function renderConc(rows) {
    const S = sums(), vals = [];
    const pc = V.m === 'cust' ? pinCust() : null;
    for (const p of rows) { const v = V.m === 'rv' ? S.tyRv[p] : V.m === 'cust' ? pc.ty[p] : S.ty[p]; if (v > 0) vals.push(v); }
    vals.sort((a, b) => b - a);
    const n = vals.length, cum = new Float64Array(n);
    let t = 0; for (let i = 0; i < n; i++) { t += vals[i]; cum[i] = t; }
    CONC = { n, cum, tot: t };
    let half = 0; while (half < n && cum[half] < t / 2) half++;
    $('#concH').textContent = `How concentrated ${areaName()}'s ${measureName()} are`;
    $('#concSub').innerHTML = n ? `<b class="tn">${IN0.format(n)}</b> pincodes had ${measureName()} in these dates. Half of it came from just <b class="tn">${IN0.format(half + 1)}</b> of them (${((half + 1) / n * 100).toFixed(1)}%).` : 'No deals in these dates.';
    $('#concCtl').hidden = !n;
    drawConc();
  }
  function concAt(f) { const { n, cum, tot } = CONC; const k = Math.max(1, Math.min(n, Math.round(n * f))); return [k, cum[k - 1] / tot * 100]; }
  function drawConc() {
    const cv = $('#conc'), dpr = devicePixelRatio || 1, w = cv.clientWidth || 800, h = 170;
    cv.style.height = h + 'px';
    cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
    const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, w, h);
    if (!CONC || !CONC.n) return;
    const { n, cum, tot } = CONC;
    const L = 40, R = 12, T = 12, B = 22, X = f => L + f * (w - L - R), Y = f => T + (1 - f) * (h - T - B);
    g.font = '11.5px Inter, system-ui'; g.fillStyle = '#6B7484'; g.strokeStyle = '#EDF0F4'; g.lineWidth = 1;
    [0, .5, 1].forEach(f => { g.beginPath(); g.moveTo(L, Y(f)); g.lineTo(w - R, Y(f)); g.stroke(); g.textAlign = 'right'; g.fillText(Math.round(f * 100) + '%', L - 6, Y(f) + 4); });
    g.textAlign = 'left'; g.fillText('pincodes, largest first →', L, h - 5); g.textAlign = 'right'; g.fillText('all ' + IN0.format(n), w - R, h - 5);
    g.setLineDash([3, 3]); g.strokeStyle = '#B9C2CF'; g.beginPath(); g.moveTo(X(0), Y(0)); g.lineTo(X(1), Y(1)); g.stroke(); g.setLineDash([]);
    if (w >= 600) { g.textAlign = 'left'; g.fillStyle = '#8A93A3'; g.fillText('if every pincode were equal', X(.62), Y(.62) + 16); }
    const step = Math.max(1, Math.floor(n / (w * 2)));
    const curve = () => { g.moveTo(X(0), Y(0)); for (let i = 0; i < n; i++) if (i % step === 0 || i === n - 1) g.lineTo(X((i + 1) / n), Y(cum[i] / tot)); };
    g.beginPath(); curve(); g.lineTo(X(1), Y(0)); g.closePath(); g.fillStyle = 'rgba(28,111,184,.08)'; g.fill();
    // the share picked on the slider: its slice of the area darker, guides to both axes, the point on the curve
    const [k, sh] = concAt(CONC_F), x = X(k / n), y = Y(sh / 100);
    g.save(); g.beginPath(); g.rect(L, 0, x - L, h - B); g.clip();
    g.beginPath(); curve(); g.lineTo(X(1), Y(0)); g.closePath(); g.fillStyle = 'rgba(28,111,184,.22)'; g.fill(); g.restore();
    g.beginPath(); curve(); g.strokeStyle = '#1C6FB8'; g.lineWidth = 2; g.stroke();
    g.setLineDash([4, 3]); g.strokeStyle = '#14213D'; g.globalAlpha = .55; g.lineWidth = 1;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x, Y(0)); g.moveTo(L, y); g.lineTo(x, y); g.stroke(); g.setLineDash([]); g.globalAlpha = 1;
    g.fillStyle = '#fff'; g.beginPath(); g.arc(x, y, 7, 0, Math.PI * 2); g.fill();
    g.fillStyle = '#14213D'; g.beginPath(); g.arc(x, y, 4.5, 0, Math.PI * 2); g.fill();
    const lab = `top ${fShare(k / n * 100)} → ${sh.toFixed(0)}%`;
    g.font = '600 12.5px Inter, system-ui'; const lw = g.measureText(lab).width;
    const right = x + 12 + lw < w - R;
    g.textAlign = right ? 'left' : 'right'; g.fillStyle = '#14213D';
    g.fillText(lab, right ? x + 12 : x - 12, y + 20);
    // the readout and the slider's own fill
    const pctPins = k / n * 100;
    $('#concPct').textContent = fShare(pctPins);
    $('#concOut').innerHTML = `The top <b class="tn">${IN0.format(k)}</b> pincodes bring <b class="tn">${sh.toFixed(0)}%</b> of ${esc(areaName())}'s ${measureName()}; the other <span class="tn">${IN0.format(n - k)}</span> bring <b class="tn">${(100 - sh).toFixed(0)}%</b>.`;
    const r = $('#concR'); r.style.setProperty('--p', (+r.value - +r.min) / (+r.max - +r.min) * 100 + '%');
  }
  const fShare = p => (p < 10 && Math.round(p) !== p ? p.toFixed(1) : Math.round(p)) + '%';
  $('#concR').addEventListener('input', ev => { CONC_F = +ev.target.value / 100; drawConc(); });
  // click or drag on the chart moves the slider too
  function concFromPointer(ev) {
    const cv = $('#conc'), r = cv.getBoundingClientRect(), L = 40, R = 12;
    const f = Math.min(1, Math.max(.005, (ev.clientX - r.left - L) / (r.width - L - R)));
    const sl = $('#concR'); sl.value = Math.max(+sl.min, Math.round(f * 1000) / 10); CONC_F = +sl.value / 100; drawConc();
  }
  $('#conc').addEventListener('pointerdown', ev => { $('#conc').setPointerCapture(ev.pointerId); concFromPointer(ev); });
  $('#conc').addEventListener('pointermove', ev => { if (ev.buttons & 1) concFromPointer(ev); });

  /* =========================================================== table (virtual rows) */
  let TROWS = [], CUR_KIDS = [];
  const COLS_BASE = [['name', 'Name'], ['v', ''], ['p', 'Change %'], ['d', 'Change'], ['lv', 'Last year'], ['share', 'Share'], ['other', ''], ['op', '']];
  const COLS_MIX = [['fresh', 'Fresh'], ['ecs', 'ECS'], ['ch0', 'JDA'], ['ch1', 'JDS'], ['ch2', 'B2B'], ['ch3', 'Anon.']];
  function tableCols() {
    const label = { v: MLABEL[V.m], other: V.m === 'deals' ? 'RV 3yr' : 'Deals', op: (V.m === 'deals' ? 'RV' : 'Deals') + ' change %' };
    const c = COLS_BASE.map(([k, l]) => [k, label[k] || l]);
    return V.cols ? c.concat(COLS_MIX) : c;
  }
  function fillMix(c) {
    if (c.mix) return;
    const S = sums(), m = mixFor(c.rows, S, 'ty');
    const sh = x => m.all ? x / m.all * 100 : null;
    c.mix = { fresh: sh(m.fresh), ecs: sh(m.ecs), ch0: sh(m.ch[0]), ch1: sh(m.ch[1]), ch2: sh(m.ch[2]), ch3: sh(m.ch[3]) };
  }
  function cellVal(c, k) {
    if (k === 'name') return kidLabel(c);
    if (k === 'other') return V.m === 'deals' ? c.tyRv : c.ty;
    if (k === 'op') { const a = V.m === 'deals' ? c.tyRv : c.ty, b = V.m === 'deals' ? c.lyRv : c.ly; return c.ok && b > 0 ? (a / b - 1) * 100 : null; }
    if (k in (c.mix || {}) || k.startsWith('ch') || k === 'fresh' || k === 'ecs') { fillMix(c); return c.mix[k]; }
    return c[k];
  }
  function renderTable(T, kids) {
    const L = level();
    $('#tableH').textContent = `${KID_NAME[V.kids]} in ${areaName()}`;
    $('#moreCols').setAttribute('aria-pressed', String(V.cols));
    const q = $('#tableSearch').value.trim().toLowerCase();
    let rows = q ? kids.filter(c => kidLabel(c).toLowerCase().includes(q)) : kids.slice();
    const key = V.sort || 'v', dir = V.sort ? V.dir : -1;
    if (V.cols || ['fresh', 'ecs', 'ch0', 'ch1', 'ch2', 'ch3'].includes(key)) rows.forEach(fillMix);
    rows.sort((a, b) => {
      const x = cellVal(a, key), y = cellVal(b, key);
      if (key === 'name') return dir * String(x).localeCompare(String(y), 'en', { numeric: true });
      if (x === null && y === null) return 0; if (x === null) return 1; if (y === null) return -1;
      return dir * (x - y);
    });
    TROWS = rows;
    const cols = tableCols();
    const tot = { v: val(T), lv: lval(T) };
    $('#tbl').innerHTML = `<table><thead><tr>${cols.map(([k, l]) => `<th data-k="${k}" ${V.sort === k || (!V.sort && k === 'v') ? `aria-sort="${dir > 0 ? 'ascending' : 'descending'}"` : ''}>${esc(l)}${V.sort === k || (!V.sort && k === 'v') ? `<svg class="ar" viewBox="0 0 10 10" aria-hidden="true"><path d="${dir > 0 ? 'M2 6.5l3-3 3 3' : 'M2 3.5l3 3 3-3'}"/></svg>` : ''}</th>`).join('')}</tr></thead>` +
      `<tbody id="tb"></tbody><tfoot><tr>${cols.map(([k]) => {
        const tp = tot.lv > 0 ? (tot.v / tot.lv - 1) * 100 : null;
        if (k === 'name') return `<td>${esc(areaName())}${q ? ' (all, not just matches)' : ''}</td>`;
        if (k === 'v') return `<td>${esc(fVal(tot.v))}</td>`;
        if (k === 'lv') return `<td>${esc(fVal(tot.lv))}</td>`;
        if (k === 'd') return `<td class="${clsP(tp)}">${esc(fDelta(tot.v - tot.lv))}</td>`;
        if (k === 'p') return `<td class="${clsP(tp)}">${esc(fPct(tp))}</td>`;
        if (k === 'share') return '<td>100%</td>';
        return '<td></td>';
      }).join('')}</tr></tfoot></table>` +
      (rows.length ? '' : `<p class="empty">${q ? 'Nothing matches “' + esc(q) + '”.' : 'No deals here in these dates.'}</p>`);
    $('#tbl').scrollTop = 0;
    drawTable();
  }
  const TRH = 36;
  function drawTable() {
    const box = $('#tbl'), tb = $('#tb'); if (!tb) return;
    const cols = tableCols(), n = TROWS.length;
    const head = 38, a = Math.max(0, Math.floor((box.scrollTop - head) / TRH) - 10), b = Math.min(n, a + Math.ceil((box.clientHeight || 560) / TRH) + 20);
    const pctc = x => x === null || x === undefined ? '—' : x.toFixed(1) + '%';
    let h = a > 0 ? `<tr class="pad"><td colspan="${cols.length}" style="height:${a * TRH}px"></td></tr>` : '';
    for (let i = a; i < b; i++) {
      const c = TROWS[i];
      const cells = cols.map(([k]) => {
        if (k === 'name') return `<td class="nm" title="${esc(kidLabel(c))}">${esc(c.name)}${c.sub ? `<small>${esc(c.sub)}</small>` : ''}</td>`;
        const x = cellVal(c, k);
        if (k === 'v' || k === 'lv') return `<td>${esc(fVal(x))}</td>`;
        if (k === 'd') return `<td class="${clsP(c.ok ? c.p : null)}">${esc(fDelta(x))}</td>`;
        if (k === 'p' || k === 'op') return `<td class="${clsP(x)}">${esc(fPct(x))}</td>`;
        if (k === 'share') return `<td>${x.toFixed(x < 1 ? 2 : 1)}%</td>`;
        if (k === 'other') return `<td>${esc(V.m === 'deals' ? fRv(x) : fDeals(x))}</td>`;
        return `<td>${pctc(x)}</td>`;
      }).join('');
      h += `<tr class="go" data-i="${i}">${cells}</tr>`;
    }
    if (b < n) h += `<tr class="pad"><td colspan="${cols.length}" style="height:${(n - b) * TRH}px"></td></tr>`;
    tb.innerHTML = h;
  }
  $('#tbl').addEventListener('scroll', () => requestAnimationFrame(drawTable), { passive: true });
  $('#tbl').addEventListener('click', ev => {
    const th = ev.target.closest('th');
    if (th) { const k = th.dataset.k; if (V.sort === k) V.dir = -V.dir; else { V.sort = k; V.dir = k === 'name' ? 1 : -1; } renderTable(LAST.T, CUR_KIDS); return; }
    const tr = ev.target.closest('tr.go'); if (tr) openKid(TROWS[+tr.dataset.i]);
  });
  $('#tableSearch').addEventListener('input', () => renderTable(LAST.T, CUR_KIDS));
  $('#moreCols').addEventListener('click', () => { V.cols = !V.cols; renderTable(LAST.T, CUR_KIDS); });
  $('#csv').addEventListener('click', () => {
    const cols = tableCols().filter(([k]) => k !== 'name');
    TROWS.forEach(fillMix);
    const head = ['Name', 'Place', 'State', 'Branch', ...cols.map(([, l]) => l)];
    const lines = [head];
    for (const c of TROWS) {
      const p0 = c.rows[0];
      lines.push([c.name, c.kind === 'pin' ? COLS.place[p0] : '', c.kind === 'branch' && V.s < 0 ? (c.sub || '') : STATES[COLS.st[p0]], c.kind === 'state' || c.kind === 'district' ? '' : BRANCHES[COLS.br[p0]],
        ...cols.map(([k]) => { const x = cellVal(c, k); if (x === null || x === undefined) return ''; const rupees = k === 'other' ? V.m === 'deals' : (k === 'v' || k === 'lv' || k === 'd') && V.m === 'rv'; return rupees ? (x / 1e4).toFixed(4) : (+x).toFixed(2); })]);
    }
    const note = V.m === 'deals' ? 'RV columns in rupees crore' : 'RV columns in rupees crore';
    const csv = '﻿' + lines.map(r => r.map(x => /[",\n]/.test(String(x)) ? `"${String(x).replace(/"/g, '""')}"` : x).join(',')).join('\r\n') + `\r\n\r\n"${KID_NAME[V.kids]} in ${areaName()}, ${fRange(V.from, V.to)} vs ${lyRange(V.from, V.to)}; ${note}; data to ${META.end}"`;
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    a.download = `JD_sales_${areaName().replace(/\W+/g, '_')}_${V.kids}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`;
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  });

  /* =========================================================== notes */
  function renderNotes() {
    const ck = META.check, ty = ck.ty, ly = ck.ly;
    $('#notes').innerHTML = [
      `<p><b>Dates.</b> ${esc(fRange(V.from, V.to))}, compared with the same dates last year (${esc(lyRange(V.from, V.to))}). Data to ${esc(fDate(dOf(META.days - 1), true))}; refreshed ${esc(META.refreshed.replace('T', ' at '))}.</p>`,
      `<p><b>Deals</b> are the sum of <i>dc_genio</i> on every deal row in the daily deals table with dc_genio above 0, all teams. A joint JDA + JDS deal counts half to each. <b>RV 3yr</b> is the sum of <i>RV_3yr</i> on the same rows.</p>`,
      `<p><b>Customers</b> are unique businesses: the count of distinct docids on those same deal rows. A customer who signed several deals, or in several pincodes, counts once in any total here, so customer figures for areas or months do not add up to a bigger area or a longer period.</p>`,
      `<p><b>Fresh or renewal</b> comes from the deal's fresh flag; <b>ECS</b> from its original ECS flag. <b>Channel</b>: JDA, JDS (in-house), B2B and anonymous, from the deal's JDA flag.</p>`,
      `<p><b>Change %</b> is shown only where last year had enough deals on the same dates: for these dates at least ${minFor('state')} (state or UT), ${minFor('branch')} (branch), ${minFor('district')} (district) or ${minFor('pin')} (pincode). That is ${MIN.state} / ${MIN.branch} / ${MIN.district} / ${MIN.pin} per half-year${fewChanged() ? ' (changed in Rules; the defaults are 500 / 200 / 100 / 20)' : ''}, scaled down for shorter dates, never below 30 / 20 / 10 / 5. Smaller areas show the change in numbers only and are dotted on the map; areas with no deals at all are hatched red. Colours: five bands split at 0 (below −10%, −10 to 0%, 0 to +10%, +10 to +25%, +25% or more).</p>`,
      `<p><b>Big deals.</b> ${V.cap ? `Deals above ${esc(fLakh(V.cap))} of RV 3yr are left out of every figure on this page, this year and last year alike (a deal is one customer on one day; its size is the RV 3yr of all its rows). A customer whose only deals here were above it is left out of the customer counts too.` : `Every deal counts. Rules can leave out deals above an amount you pick (from ${esc(fLakh(META.bigFloor / 1e5))}), this year and last year alike.`}</p>`,
      `<p><b>Places.</b> State and place from GeoNames by pincode; branch from the pincode → branch list. <b>District</b>: the district on the map that the pincode's location falls in (within its own state); a pincode with no known location takes the district of the same name, else the usual district of its city. ${ty.noPincode || ly.noPincode ? `Deals with no usable pincode (${fDeals(ty.noPincode)} this year, ${fDeals(ly.noPincode)} last year) are left out of every figure here.` : ''} State borders: DataMeet India (CC BY 4.0). District borders: india-maps-data (udit-001, compiled from public sources).</p>`,
      `<p><b>Check.</b> On the last refresh the page's totals ${ty.ok && ly.ok ? 'matched' : 'did not match'} the deals table (${fDeals(ty.deals)} deals and ${fCust(ty.customers || 0)} customers this year, ${fDeals(ly.deals)} and ${fCust(ly.customers || 0)} last year, financial year to date).</p>`,
    ].join('');
  }

  /* =========================================================== pincode drawer */
  const DRAWER = $('#drawer');
  function openPin(p) {
    V.pin = p;
    const S = sums(), c = enrich({ kind: 'pin', id: p, name: COLS.pin[p], sub: COLS.place[p], ty: S.ty[p], ly: S.ly[p], tyRv: S.tyRv[p], lyRv: S.lyRv[p], rows: [p] }, 1);
    const A = mixFor([p], S, 'ty'), B = mixFor([p], S, 'ly');
    const where = [...new Set([COLS.place[p], COLS.dm[p] >= 0 ? DNAME[COLS.dm[p]] + ' district' : DISTRICTS[COLS.dist[p]], CITIES[COLS.ci[p]], STATES[COLS.st[p]]].filter(x => x && x !== 'Not mapped'))];
    const dp = c.ly > 0 && c.ly >= minFor('pin') ? (c.ty / c.ly - 1) * 100 : null, rp = c.lyRv > 0 && c.ly >= minFor('pin') ? (c.tyRv / c.lyRv - 1) * 100 : null;
    const pcu = pinCust(), cp = pcu.ly[p] > 0 && c.ly >= minFor('pin') ? (pcu.ty[p] / pcu.ly[p] - 1) * 100 : null;
    const Mp = monthly([p]);
    if (V.m === 'cust') Mp.cust = custMonthly(maskOf([p]));
    const r = monthBars(Mp, { w: 390, h: 170, short: true });
    $('#drawerBody').innerHTML = `<h2 id="drawerH">${esc(COLS.pin[p])}</h2><p class="where">${esc(where.join(' · '))}<br>${esc(BRANCHES[COLS.br[p]])} branch · ${esc(fRange(V.from, V.to))} vs the same dates last year</p>` +
      `<div class="kv"><div><div class="k">Deals</div><div class="v tn">${esc(fDeals(c.ty))}</div><div class="${clsP(dp)}">${esc(fPct(dp))} <span class="mu">vs ${esc(fDeals(c.ly))}</span></div></div>` +
      `<div><div class="k">RV 3yr</div><div class="v tn">${esc(fRv(c.tyRv))}</div><div class="${clsP(rp)}">${esc(fPct(rp))} <span class="mu">vs ${esc(fRv(c.lyRv))}</span></div></div>` +
      `<div><div class="k">Customers</div><div class="v tn">${esc(fCust(pcu.ty[p]))}</div><div class="${clsP(cp)}">${esc(fPct(cp))} <span class="mu">vs ${esc(fCust(pcu.ly[p]))}</span></div></div></div>` +
      (c.ly > 0 && c.ly < minFor('pin') ? `<p class="hint">Change % is not shown: under ${minFor('pin')} deals here last year.</p>` : '') +
      `<h3>${MLABEL[V.m]} by month</h3>${r.svg}` +
      (A.all ? `<h3>What kind of deals</h3>${mixBlock(A, B.all ? B : { fresh: 0, ecs: 0, ch: [0, 0, 0, 0], all: 0 })}` : '') +
      `<p style="margin-top:18px"><button type="button" class="btn" id="toBranch">Open the ${esc(BRANCHES[COLS.br[p]])} branch</button></p>`;
    DRAWER.classList.add('open'); DRAWER.setAttribute('aria-hidden', 'false'); $('#dim').hidden = false;
    $('#toBranch').onclick = () => { closePin(); go({ s: COLS.st[p], b: COLS.br[p], kids: 'pincodes' }); };
    DRAWER.focus({ preventScroll: true });
    writeHash(true);
  }
  function closePin() { if (V.pin < 0) return; V.pin = -1; DRAWER.classList.remove('open'); DRAWER.setAttribute('aria-hidden', 'true'); $('#dim').hidden = true; writeHash(true); }
  $('#drawerClose').addEventListener('click', closePin);
  $('#dim').addEventListener('click', closePin);

  /* =========================================================== period picker */
  const POP = $('#periodPop'), PBTN = $('#periodBtn');
  function openPop() {
    const minD = META.fy, maxD = META.end;
    POP.innerHTML = META.presets.map(p => `<button type="button" class="pre" data-k="${p.k}" aria-pressed="${V.preset === p.k}"><span>${esc(p.label)}</span><small>${esc(fRange(p.a, p.b))}</small></button>`).join('') +
      `<div class="custom"><label>From<input type="date" id="pFrom" min="${minD}" max="${maxD}" value="${iso(dOf(V.from))}"></label><label>To<input type="date" id="pTo" min="${minD}" max="${maxD}" value="${iso(dOf(V.to))}"></label><span class="err" id="pErr"></span><button type="button" class="btn" id="pApply">Show these dates</button></div>`;
    const r = PBTN.getBoundingClientRect();
    POP.hidden = false;
    POP.style.top = (r.bottom + 8) + 'px'; POP.style.left = Math.max(8, Math.min(innerWidth - POP.offsetWidth - 8, r.right - POP.offsetWidth)) + 'px';
    PBTN.setAttribute('aria-expanded', 'true');
    (POP.querySelector('[aria-pressed="true"]') || POP.querySelector('button')).focus();
  }
  function closePop() { if (POP.hidden) return; POP.hidden = true; PBTN.setAttribute('aria-expanded', 'false'); }
  PBTN.addEventListener('click', () => POP.hidden ? openPop() : closePop());
  POP.addEventListener('click', ev => {
    const b = ev.target.closest('button.pre');
    if (b) { const p = META.presets.find(x => x.k === b.dataset.k); Object.assign(V, { from: p.a, to: p.b, preset: p.k }); closePop(); render(false, true); return; }
    if (ev.target.id === 'pApply') {
      const a = offOf($('#pFrom').value), z = offOf($('#pTo').value);
      if (!isFinite(a) || !isFinite(z)) { $('#pErr').textContent = 'Pick both dates.'; return; }
      if (a > z) { $('#pErr').textContent = 'The start date is after the end date.'; return; }
      if (a < 0 || z > META.days - 1) { $('#pErr').textContent = `Pick dates from ${fDate(dOf(0), true)} to ${fDate(dOf(META.days - 1), true)}.`; return; }
      const p = META.presets.find(x => x.a === a && x.b === z);
      Object.assign(V, { from: a, to: z, preset: p ? p.k : null }); closePop(); render(false, true);
    }
  });
  document.addEventListener('mousedown', ev => { if (!POP.hidden && !POP.contains(ev.target) && !PBTN.contains(ev.target)) closePop(); });

  /* =========================================================== rules: big deals, too few to compare */
  const RPOP = $('#rulesPop'), RBTN = $('#rulesBtn');
  const fLakh = l => '₹' + (Math.round(l * 100) / 100).toLocaleString('en-IN') + ' L';
  function rulesLabel() {
    $('#rulesLabel').textContent = V.cap ? `Up to ${fLakh(V.cap)}` : 'All deals';
    RBTN.classList.toggle('on', !!V.cap || fewChanged());
  }
  // deals above x rupees in the dates picked, India-wide: count (dc_genio) and RV, this year and last year
  function bigIn(x) {
    const out = { ty: [0, 0], ly: [0, 0] };
    for (const [S, o] of [[BTY, out.ty], [BLY, out.ly]]) for (let i = 0; i < S.n; i++) { const d = S.d[i]; if (d >= V.from && d <= V.to && S.a[i] > x) { o[0] += S.deals[i] / 100; o[1] += S.rv[i]; } }
    return out;
  }
  function capNote() {
    const on = $('#capOn').checked, l = +$('#capL').value;
    $('#capL').disabled = !on;
    if (!on) { $('#capOut').textContent = 'Every deal counts.'; return; }
    if (!(l >= META.bigFloor / 1e5)) { $('#capOut').textContent = `Type an amount of at least ${fLakh(META.bigFloor / 1e5)}.`; return; }
    const b = bigIn(l * 1e5);
    $('#capOut').innerHTML = `In these dates, India-wide, this leaves out <b>${fDeals(b.ty[0])}</b> deals (${esc(fRv(b.ty[1]))} RV 3yr) this year and <b>${fDeals(b.ly[0])}</b> (${esc(fRv(b.ly[1]))}) on the same dates last year.`;
  }
  function fewNote() {
    FEW_KEYS.forEach(([k]) => {
      const v = Math.max(1, Math.round(+$('#few_' + k).value || MIN0[k])), saved = MIN[k];
      MIN[k] = v; $('#fewNow_' + k).textContent = `${IN0.format(minFor(k))} for these dates`; MIN[k] = saved;
    });
  }
  function openRules(focus) {
    const days = V.to - V.from + 1;
    RPOP.innerHTML = `<h3>Leave out big deals</h3>
      <p class="mu">A deal is one customer on one day; its size is its RV 3yr. Corporate-size deals can make an area look bigger than its everyday sales.</p>
      <label class="chk"><input type="checkbox" id="capOn"${V.cap ? ' checked' : ''}> Leave out deals above</label>
      <div class="amt"><span>₹</span><input type="number" id="capL" min="${META.bigFloor / 1e5}" step="0.5" value="${V.cap || 5}" aria-label="Amount in lakh"><span>lakh RV 3yr</span></div>
      <p class="cap-out" id="capOut" aria-live="polite"></p>
      <h3 id="fewH">Too few to compare</h3>
      <p class="mu">Change % is hidden where last year had fewer deals than this on the same dates, so a small base cannot show a big swing. Set per half-year and scaled to the ${days} days picked; those areas are dotted on the map.</p>
      <div class="few">${FEW_KEYS.map(([k, l]) => `<label for="few_${k}">${l}</label><input type="number" id="few_${k}" min="1" step="1" value="${MIN[k]}"><span class="mu" id="fewNow_${k}"></span>`).join('')}</div>
      <div class="acts"><button type="button" class="btn" id="rulesReset">Reset all</button><button type="button" class="btn pri" id="rulesApply">Apply</button></div>`;
    const r = RBTN.getBoundingClientRect();
    RPOP.hidden = false;
    RPOP.style.top = (r.bottom + 8) + 'px'; RPOP.style.left = Math.max(8, Math.min(innerWidth - RPOP.offsetWidth - 8, r.right - RPOP.offsetWidth)) + 'px';
    RPOP.style.maxHeight = (innerHeight - r.bottom - 20) + 'px';
    RBTN.setAttribute('aria-expanded', 'true');
    capNote(); fewNote();
    (focus === 'few' ? $('#few_' + MAP_KIND()) : $('#capOn')).focus();
    if (focus === 'few') $('#fewH').scrollIntoView({ block: 'nearest' });
  }
  function closeRules() { if (RPOP.hidden) return; RPOP.hidden = true; RBTN.setAttribute('aria-expanded', 'false'); }
  function applyRules(cap, mins) {
    V.cap = cap > 0 ? cap : 0;
    setCap(V.cap ? V.cap * 1e5 : Infinity);
    Object.assign(MIN, mins);
    rulesLabel();
  }
  RBTN.addEventListener('click', () => RPOP.hidden ? openRules() : closeRules());
  RPOP.addEventListener('input', ev => { if (ev.target.id.startsWith('few')) fewNote(); else capNote(); });
  RPOP.addEventListener('change', ev => { if (ev.target.id === 'capOn') capNote(); });
  RPOP.addEventListener('click', ev => {
    if (ev.target.id === 'rulesReset') { applyRules(0, MIN0); closeRules(); render(false, true); return; }
    if (ev.target.id !== 'rulesApply') return;
    const on = $('#capOn').checked, l = +$('#capL').value;
    if (on && !(l >= META.bigFloor / 1e5)) { $('#capL').focus(); return; }
    const mins = {}; FEW_KEYS.forEach(([k]) => { mins[k] = Math.max(1, Math.round(+$('#few_' + k).value || MIN0[k])); });
    applyRules(on ? Math.round(l * 100) / 100 : 0, mins);
    closeRules(); render(false, true);
  });
  RPOP.addEventListener('keydown', ev => { if (ev.key === 'Enter' && ev.target.tagName === 'INPUT') $('#rulesApply').click(); });
  document.addEventListener('mousedown', ev => { if (!RPOP.hidden && !RPOP.contains(ev.target) && !RBTN.contains(ev.target)) closeRules(); });
  // the legend's "Change" opens the panel at the cut-offs
  document.addEventListener('click', ev => { const b = ev.target.closest('[data-rules]'); if (b) { ev.stopPropagation(); openRules(b.dataset.rules); } });

  /* =========================================================== navigation */
  function openKid(c) {
    if (!c) return;
    if (c.kind === 'pin') return openPin(c.id);
    if (c.kind === 'state') return go({ s: c.id, b: -1 });
    if (c.kind === 'branch') return go({ s: V.s, b: c.id });
    if (c.kind === 'district' && c.id >= 0) return go({ s: DM_STATE[c.id], b: -1, d: c.id });
  }
  function go(o) {
    closePin();
    V.s = o.s; V.b = o.b; V.d = o.d >= 0 && o.b < 0 ? o.d : -1;
    const L = level();
    V.kids = o.kids && KIDS[L].includes(o.kids) ? o.kids : KIDS[L][0];
    V.sort = null; $('#rankSearch').value = ''; $('#tableSearch').value = '';
    render(true, true);
    window.scrollTo({ top: 0, behavior: RM ? 'auto' : 'smooth' });
  }
  $('#trail').addEventListener('click', ev => { const b = ev.target.closest('.stub'); if (b) go({ s: +b.dataset.s, b: +b.dataset.b, d: +b.dataset.d }); });
  $('#home').addEventListener('click', ev => { ev.preventDefault(); go({ s: -1, b: -1 }); });
  $('#measure').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b && b.dataset.m !== V.m) { V.m = b.dataset.m; render(false, true); } });
  function siblings() {
    const S = sums();
    if (V.d >= 0) { const list = children(S, rowsOf(V.s, -1), 'districts').filter(c => c.id >= 0).map(c => enrich(c, 1)).sort((a, b) => b.v - a.v); return { list, at: list.findIndex(c => c.id === V.d), to: c => ({ s: V.s, b: -1, d: c.id }) }; }
    if (V.b >= 0) { const list = children(S, rowsOf(V.s, -1), 'branches').map(c => enrich(c, 1)).sort((a, b) => b.v - a.v); return { list, at: list.findIndex(c => c.id === V.b), to: c => ({ s: V.s, b: c.id }) }; }
    if (V.s >= 0) { const list = children(S, ALL_ROWS, 'states').map(c => enrich(c, 1)).sort((a, b) => b.v - a.v); return { list, at: list.findIndex(c => c.id === V.s), to: c => ({ s: c.id, b: -1 }) }; }
    return null;
  }
  document.addEventListener('keydown', ev => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
    if (ev.key === 'Escape') { if (!RPOP.hidden) { closeRules(); RBTN.focus(); } else if (!POP.hidden) { closePop(); PBTN.focus(); } else if (V.pin >= 0) closePin(); else if (!typing && level() !== 'india') go((V.b >= 0 || V.d >= 0) && V.s >= 0 ? { s: V.s, b: -1 } : { s: -1, b: -1 }); return; }
    if (typing || ev.altKey || ev.ctrlKey || ev.metaKey) return;
    if (ev.key === '/') { ev.preventDefault(); $('#rankSearch').focus(); return; }
    if (ev.key === 'ArrowLeft' || ev.key === 'ArrowRight') {
      const sb = siblings(); if (!sb || sb.at < 0) return;
      const n = sb.list[sb.at + (ev.key === 'ArrowRight' ? 1 : -1)];
      if (n) { ev.preventDefault(); go(sb.to(n)); }
    }
  });

  /* =========================================================== link state */
  let writing = false;
  function writeHash(replace) {
    const h = new URLSearchParams();
    if (V.s >= 0) h.set('state', STATES[V.s]);
    if (V.b >= 0) h.set('branch', BRANCHES[V.b]);
    if (V.d >= 0) h.set('district', DNAME[V.d]);
    if (V.kids !== KIDS[level()][0]) h.set('by', V.kids);
    if (V.m !== 'deals') h.set('m', V.m);
    if (V.preset && V.preset !== 'fytd') h.set('period', V.preset);
    else if (!V.preset) { h.set('from', iso(dOf(V.from))); h.set('to', iso(dOf(V.to))); }
    if (V.cap) h.set('cap', String(V.cap));
    if (fewChanged()) h.set('few', FEW_KEYS.map(([k]) => MIN[k]).join('-'));
    if (V.pin >= 0) h.set('pin', COLS.pin[V.pin]);
    const s = h.toString(), want = s ? '#' + s : '';
    if (location.hash === want || (!want && !location.hash)) return;
    writing = true;
    if (replace) history.replaceState(null, '', want || location.pathname + location.search); else history.pushState(null, '', want || location.pathname + location.search);
    writing = false;
  }
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    const s = h.has('state') ? STATES.indexOf(h.get('state')) : -1;
    const b = h.has('branch') ? BRANCHES.indexOf(h.get('branch')) : -1;
    V.s = s; V.b = b;
    V.d = b < 0 && s >= 0 && h.has('district') ? DIST_OF_STATE[s].find(i => DNAME[i] === h.get('district')) ?? -1 : -1;
    const L = level();
    V.kids = KIDS[L].includes(h.get('by')) ? h.get('by') : KIDS[L][0];
    V.m = ['rv', 'cust'].includes(h.get('m')) ? h.get('m') : 'deals';
    const p = META.presets.find(x => x.k === h.get('period'));
    if (p) Object.assign(V, { from: p.a, to: p.b, preset: p.k });
    else if (h.has('from') && h.has('to')) {
      const a = offOf(h.get('from')), z = offOf(h.get('to'));
      if (isFinite(a) && isFinite(z) && a >= 0 && z <= META.days - 1 && a <= z) Object.assign(V, { from: a, to: z, preset: null });
    } else { const f = META.presets.find(x => x.k === 'fytd') || { a: 0, b: META.days - 1, k: 'fytd' }; Object.assign(V, { from: f.a, to: f.b, preset: f.k }); }
    const cap = +h.get('cap'), few = (h.get('few') || '').split('-').map(Number);
    const mins = { ...MIN0 };
    if (few.length === 4 && few.every(x => x >= 1)) FEW_KEYS.forEach(([k], i) => { mins[k] = Math.round(few[i]); });
    applyRules(cap >= META.bigFloor / 1e5 ? cap : 0, mins);
    return h.get('pin');
  }
  addEventListener('popstate', () => { if (writing) return; const pin = readHash(); render(true, false); syncPin(pin); });
  function syncPin(pin) { const p = pin ? COLS.pin.indexOf(pin) : -1; if (p >= 0) openPin(p); else if (V.pin >= 0) { V.pin = -1; DRAWER.classList.remove('open'); DRAWER.setAttribute('aria-hidden', 'true'); $('#dim').hidden = true; } }

  /* =========================================================== render */
  const LAST = { T: null };
  function render(animateMap, push) {
    untip();
    const S = sums(), rows = rowsOf(V.s, V.b, V.d), T = totals(S, rows);
    LAST.T = T;
    const kids = children(S, rows, V.kids).map(c => enrich(c, val(T)));
    CUR_KIDS = kids;
    renderBand(T, kids);
    renderMap(T, kids, animateMap);
    renderBridge(T, kids);
    renderRank(kids);
    renderTrend(rows);
    renderMix(T);
    renderQuad(T, kids);
    renderConc(rows);
    renderTable(T, kids);
    renderNotes();
    document.title = level() === 'india' ? 'JD India sales overview' : `${areaName()} · JD India sales overview`;
    if (push !== undefined) writeHash(!push);
    FIRST = false;
    requestAnimationFrame(pinBand);
  }
  // the band's top row (where you are, measure, dates) stays pinned; the big numbers scroll away under it
  const HEAD = $('#band'), TOPBAR = $('#topbar');
  function pinBand() { document.documentElement.style.setProperty('--bar', TOPBAR.offsetHeight + 'px'); }
  addEventListener('scroll', () => TOPBAR.classList.toggle('stuck', HEAD.getBoundingClientRect().bottom <= TOPBAR.offsetHeight + 1), { passive: true });
  let rz = 0;
  addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { pinBand(); const rows = rowsOf(V.s, V.b, V.d); drawConc(); drawRank(); renderBridge(LAST.T, CUR_KIDS); renderTrend(rows); renderQuad(LAST.T, CUR_KIDS); }, 150); });

  const pin0 = readHash();
  if (!RM) MAP.classList.add('map-in');
  render(false);
  setTimeout(() => MAP.classList.remove('map-in'), 1200);
  if (pin0) syncPin(pin0);
})();
