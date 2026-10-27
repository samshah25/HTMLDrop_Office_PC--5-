/* ===== JD ME team performance: appointment opportunity -> ME attendance -> deal ===== */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const IN0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
  const MINUS = '−';
  const n0 = x => IN0.format(Math.round(x));
  const pc = (a, b) => b > 0 ? a / b * 100 : null;
  const fP = p => p === null || !isFinite(p) ? '—' : p.toFixed(1) + '%';
  const sgn = (x, f) => (x > 0 ? '+' : x < 0 ? MINUS : '') + f(Math.abs(x));
  const fPts = x => x === null || !isFinite(x) ? '—' : sgn(Math.round(x * 10) / 10, v => v.toFixed(1)) + ' pts';
  const fChg = (a, b) => b > 0 ? sgn(Math.round((a / b - 1) * 1000) / 10, v => v.toFixed(1)) + '%' : '—';
  const cls = x => x === null || !isFinite(x) || x === 0 ? 'mu' : x > 0 ? 'up' : 'dn';
  const MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const MIN = 15;          // rates and checks only for an ME with at least this many appointments in the period
  const MINCELL = 5;       // heatmap rate cells need this many

  /* ---------- data ---------- */
  const RAW = JSON.parse($('#data').textContent), META = RAW.meta;
  const MES = RAW.mes, MGRS = RAW.mgrs, MGUP = RAW.mgUp, TMES = RAW.tmes, TEAMS = RAW.teams;
  const NME = MES.length, NT = TEAMS.length;
  function b64(s, T) { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new T(u.buffer); }
  const N = RAW.a.n, AD = b64(RAW.a.d, Uint16Array), AME = b64(RAW.a.me, Uint16Array), AMG = b64(RAW.a.mg, Uint16Array),
    ATM = b64(RAW.a.tme, Uint16Array), ATT = b64(RAW.a.tt, Uint8Array), AO = b64(RAW.a.o, Uint8Array), ARL = b64(RAW.a.rl, Uint8Array);
  const CO = RAW.co, PID = RAW.pid;
  // outcomes: 0 deal, 1 follow up, 2 not interested (attended); 3 customer not available, 4 pending, 5 not visited (not attended)
  const OUT = ['Deal', 'Follow up', 'Not interested', 'Customer not available', 'Pending update', 'Not visited by ME'];
  const OC = ['#12875F', '#1F5FAD', '#D9468C', '#C28A1E', '#8B5CF6', '#B8322A'];
  const FY0 = new Date(META.fy + 'T00:00:00Z');
  const dOf = o => new Date(FY0.getTime() + o * 864e5);
  const fDate = (d, yr) => `${d.getUTCDate()} ${MON3[d.getUTCMonth()]}${yr ? ' ' + d.getUTCFullYear() : ''}`;
  const fRange = (a, b) => { const A = dOf(a), B = dOf(b); if (a === b) return fDate(A, true); if (A.getUTCMonth() === B.getUTCMonth()) return `${A.getUTCDate()}–${fDate(B, true)}`; return `${fDate(A)} – ${fDate(B, true)}`; };
  const iso = d => d.toISOString().slice(0, 10);
  const offOf = s => Math.round((new Date(s + 'T00:00:00Z') - FY0) / 864e5);
  const LAST = META.days - 1;
  const shortName = n => { const p = String(n).split(' ').filter(Boolean); return p.length > 1 ? `${p[0]} ${p[p.length - 1][0]}.` : p[0] || n; };

  // ME Head = top of the reporting chain of the appointment's manager
  const HEAD = MGRS.map((_, m) => { let c = m, seen = new Set([m]); while (MGUP[c] >= 0 && !seen.has(MGUP[c])) { c = MGUP[c]; seen.add(c); } return c; });
  const HEADS = (() => {
    const mes = new Map();
    for (let i = 0; i < N; i++) { const h = HEAD[AMG[i]]; if (!mes.has(h)) mes.set(h, new Set()); mes.get(h).add(AME[i]); }
    return [...mes.entries()].map(([h, s]) => ({ h, name: MGRS[h][1], size: s.size })).sort((a, b) => b.size - a.size);
  })();
  // each ME's usual team leader (their most common manager)
  const ME_TL = (() => { const c = new Map(); for (let i = 0; i < N; i++) { const k = AME[i] * 65536 + AMG[i]; c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME).fill(-1), bn = new Int32Array(NME); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();

  /* ---------- periods ---------- */
  const endD = dOf(LAST);
  const monthStart = (y, m) => offOf(`${y}-${String(m + 1).padStart(2, '0')}-01`);
  const PRESETS = (() => {
    const y = endD.getUTCFullYear(), m = endD.getUTCMonth(), out = [];
    const thisA = Math.max(0, monthStart(y, m));
    const lm = m === 0 ? [y - 1, 11] : [y, m - 1], lmA = monthStart(lm[0], lm[1]), lmB = thisA - 1;
    const pm = lm[1] === 0 ? [lm[0] - 1, 11] : [lm[0], lm[1] - 1], pmA = monthStart(pm[0], pm[1]);
    if (lmA >= 0) out.push({ k: 'lm', label: 'Last month', a: lmA, b: lmB, pa: pmA >= 0 ? pmA : null, pb: lmA - 1, pl: MON3[pm[1]] });
    const span = LAST - thisA;
    out.push({ k: 'tm', label: 'This month', a: thisA, b: LAST, pa: lmA >= 0 ? lmA : null, pb: lmA >= 0 ? Math.min(lmB, lmA + span) : null, pl: `1–${1 + span} ${MON3[lm[1]]}` });
    out.push({ k: 'fy', label: 'Financial year to date', a: 0, b: LAST, pa: null, pb: null });
    return out;
  })();

  /* ---------- view state ---------- */
  const V = { head: -1, from: 0, to: LAST, pa: null, pb: null, pl: '', preset: 'lm', hm: 'conv', hmAll: false, sort: 'n', dir: -1 };
  function setPreset(k) { const p = PRESETS.find(x => x.k === k) || PRESETS[0]; Object.assign(V, { from: p.a, to: p.b, pa: p.pa, pb: p.pb, pl: p.pl || '', preset: p.k }); }
  setPreset('lm');
  const inScope = i => V.head < 0 || HEAD[AMG[i]] === V.head;
  const scopeName = () => V.head < 0 ? META.city : MGRS[V.head][1];

  /* ---------- aggregation ---------- */
  function agg(a, b) {
    const R = { n: 0, o: new Float64Array(6), meO: new Float64Array(NME * 6), meT: new Float64Array(NME * NT * 3), tO: new Float64Array(NT * 6),
      meRL: new Float64Array(NME * 2), rl: [0, 0], mes: new Set() };
    if (a === null) return R;
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < a || d > b || !inScope(i)) continue;
      const me = AME[i], o = AO[i], t = ATT[i];
      R.n++; R.o[o]++; R.meO[me * 6 + o]++; R.tO[t * 6 + o]++; R.mes.add(me);
      const k = (me * NT + t) * 3; R.meT[k]++; if (o <= 2) R.meT[k + 1]++; if (o === 0) R.meT[k + 2]++;
      const rl = ARL[i]; if (rl === 1 || rl === 2) { R.meRL[me * 2]++; R.rl[0]++; if (rl === 1) { R.meRL[me * 2 + 1]++; R.rl[1]++; } }
    }
    return R;
  }
  const att = o => o[0] + o[1] + o[2];
  function rowsOfMes(R) {
    // per-source team rates, used as each ME's lead-mix benchmark
    const tg = new Float64Array(NT), ta = new Float64Array(NT), td = new Float64Array(NT), tna = new Float64Array(NT);
    for (let t = 0; t < NT; t++) { const o = R.tO.subarray(t * 6, t * 6 + 6); tg[t] = o.reduce((s, x) => s + x, 0); ta[t] = att(o); td[t] = o[0]; tna[t] = o[3]; }
    const rlRate = R.rl[0] ? R.rl[1] / R.rl[0] : null;
    const out = [];
    for (const me of R.mes) {
      const o = R.meO.subarray(me * 6, me * 6 + 6), n = o.reduce((s, x) => s + x, 0), a = att(o);
      let eA = 0, eD = 0, eNA = 0;
      for (let t = 0; t < NT; t++) {
        const k = (me * NT + t) * 3, g = R.meT[k], at = R.meT[k + 1];
        if (tg[t]) { eA += g * ta[t] / tg[t]; eNA += g * tna[t] / tg[t]; }
        if (ta[t]) eD += at * td[t] / ta[t];
      }
      const enough = n >= MIN;
      const rlDone = R.meRL[me * 2], rlYes = R.meRL[me * 2 + 1];
      // flags are neutral prompts to look closer, raised only when the gap is large for the number of appointments
      const naHigh = enough && o[3] >= eNA + 5 && (o[3] - eNA) / Math.sqrt(Math.max(eNA, 1)) >= 2;
      const rlHigh = rlDone >= 10 && rlRate !== null && (rlYes / rlDone - rlRate) / Math.sqrt(rlRate * (1 - rlRate) / rlDone) >= 2;
      out.push({ me, name: MES[me][1], code: MES[me][0], tl: ME_TL[me] >= 0 ? MGRS[ME_TL[me]][1] : '', n, o: Array.from(o), att: a, deals: o[0],
        attP: pc(a, n), conv: pc(o[0], a), attVs: enough && n ? (a - eA) / n * 100 : null, convVs: enough && a ? (o[0] - eD) / a * 100 : null,
        na: o[3], naP: pc(o[3], n), naExp: eNA, naHigh, rlDone, rlYes, rlP: rlDone ? rlYes / rlDone * 100 : null, rlHigh, enough });
    }
    return out;
  }

  /* ---------- tooltip ---------- */
  const TIP = $('#tip');
  function tip(html, ev) { TIP.innerHTML = html; TIP.hidden = false; const w = TIP.offsetWidth, h = TIP.offsetHeight; let x = ev.clientX + 14, y = ev.clientY + 14; if (x + w > innerWidth - 8) x = ev.clientX - w - 14; if (y + h > innerHeight - 8) y = ev.clientY - h - 14; TIP.style.left = x + 'px'; TIP.style.top = y + 'px'; }
  const untip = () => { TIP.hidden = true; };

  /* ---------- band ---------- */
  let CUR = null, PREV = null, MEROWS = [];
  function renderBand() {
    const R = CUR, P = PREV, a = att(R.o), pa = att(P.o), hasP = V.pa !== null && P.n > 0;
    const attP = pc(a, R.n), convP = pc(R.o[0], a), pAtt = pc(pa, P.n), pConv = pc(P.o[0], pa);
    const vs = hasP ? `vs ${V.pl || fRange(V.pa, V.pb)}` : '';
    const chip = (txt, x) => `<span class="chg ${x === null ? 'flat' : x > 0 ? 'up' : x < 0 ? 'dn' : 'flat'}">${txt}</span>`;
    $('#hero').innerHTML =
      `<div class="fig"><div class="area"><b>${esc(scopeName())}</b> · appointments given to MEs, ${esc(fRange(V.from, V.to))}</div><div class="big tn">${n0(R.n)}${hasP ? chip(fChg(R.n, P.n), R.n - P.n) : ''}</div>` +
      `<div class="sub">${n0(R.mes.size)} MEs${hasP ? ` · ${vs}: <b>${n0(P.n)}</b>` : ''}</div></div>` +
      `<div class="fig"><div class="k">Attended</div><div class="mid tn">${fP(attP)}${hasP ? chip(fPts(attP - pAtt), attP - pAtt) : ''}</div><div class="sub"><b>${n0(a)}</b> appointments</div></div>` +
      `<div class="fig"><div class="k">Deals</div><div class="mid tn">${n0(R.o[0])}${hasP ? chip(fChg(R.o[0], P.o[0]), R.o[0] - P.o[0]) : ''}</div><div class="sub">${fP(pc(R.o[0], R.n))} of appointments</div></div>` +
      `<div class="fig"><div class="k">Conversion (deals ÷ attended)</div><div class="mid tn">${fP(convP)}${hasP ? chip(fPts(convP - pConv), convP - pConv) : ''}</div><div class="sub">${hasP ? `${vs}: <b>${fP(pConv)}</b>` : ''}</div></div>` +
      `<p class="say">${say(R, P, hasP)}</p>`;
    // trail
    let t = `<button type="button" class="stub" data-h="-1" ${V.head < 0 ? 'aria-current="page"' : ''}><b>${esc(META.city)}</b><small class="tn">${n0(R.n)} appts</small></button>`;
    if (V.head >= 0) t += `<svg class="sep" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3.5L10.5 8 6 12.5"/></svg><button type="button" class="stub" data-h="${V.head}" aria-current="page"><b>${esc(MGRS[V.head][1])}</b><small class="tn">${n0(R.mes.size)} MEs</small></button>`;
    $('#trail').innerHTML = t;
    $('#teamLabel').textContent = V.head < 0 ? `All ME Heads` : MGRS[V.head][1];
    const pre = PRESETS.find(x => x.k === V.preset);
    $('#periodLabel').innerHTML = (pre ? `<span class="pl-pre">${esc(pre.label.replace('Financial year', 'FY'))} · </span>` : '') + esc(fRange(V.from, V.to));
  }
  function say(R, P, hasP) {
    const a = att(R.o), miss = R.n - a;
    const big = [[R.o[3], 'customer not available'], [R.o[4], 'pending an update'], [R.o[5], 'not visited by the ME']].sort((x, y) => y[0] - x[0]);
    let s = `MEs attended <b>${fP(pc(a, R.n))}</b> of ${n0(R.n)} appointments and closed <b>${n0(R.o[0])}</b> deals. Of the ${n0(miss)} not attended, ${n0(big[0][0])} are ${big[0][1]}`;
    s += big[1][0] ? `, ${n0(big[1][0])} ${big[1][1]}` : '';
    s += big[2][0] ? ` and ${n0(big[2][0])} ${big[2][1]}.` : '.';
    const flagged = MEROWS.filter(r => r.naHigh || r.rlHigh).length;
    if (flagged) s += ` <b>${flagged}</b> ME${flagged > 1 ? 's have' : ' has'} a "customer not available" pattern worth a look.`;
    return s;
  }

  /* ---------- funnel ---------- */
  function renderFunnel() {
    const R = CUR, a = att(R.o), P = PREV, hasP = V.pa !== null && P.n > 0, pa = att(P.o);
    const w = x => (R.n ? x / R.n * 100 : 0).toFixed(2) + '%';
    const stage = (lab, sub, x, segs) => `<div class="fun-stage"><div class="lab">${lab}<small>${sub}</small></div><div class="bar">${segs}</div><div class="num">${n0(x)}</div></div>`;
    const seg = (o) => `<i style="width:${w(R.o[o])};background:${OC[o]}" title="${OUT[o]}: ${n0(R.o[o])}"></i>`;
    const leak = o => `<button type="button" class="leak" data-o="${o}"><i style="background:${OC[o]}"></i>${OUT[o]} <b>${n0(R.o[o])}</b></button>`;
    const pts = (x, y) => hasP ? ` <span class="${cls(x - y)}">${fPts(x - y)}</span>` : '';
    $('#funnel').innerHTML =
      stage('Given', 'appointments', R.n, [0, 1, 2, 3, 4, 5].map(seg).join('')) +
      `<div class="fun-arrow">Not attended: ${n0(R.n - a)} (${fP(pc(R.n - a, R.n))})</div><div class="fun-leak">${[3, 4, 5].map(leak).join('')}</div>` +
      stage('Attended', `${fP(pc(a, R.n))} of given${hasP ? '' : ''}`, a, [0, 1, 2].map(seg).join('')) +
      `<div class="fun-arrow">Attended, no deal: ${n0(a - R.o[0])}</div><div class="fun-leak">${[1, 2].map(leak).join('')}</div>` +
      stage('Deals', `${fP(pc(R.o[0], a))} of attended`, R.o[0], seg(0)) +
      `<p class="hint">Attendance ${fP(pc(a, R.n))}${pts(pc(a, R.n), pc(pa, P.n))}; conversion ${fP(pc(R.o[0], a))}${pts(pc(R.o[0], a), pc(P.o[0], pa))}${hasP ? ` vs ${esc(V.pl || fRange(V.pa, V.pb))}` : ''}. Click a reason to see those appointments. "Pending update" means no outcome was recorded.</p>`;
  }
  $('#funnel').addEventListener('click', ev => { const b = ev.target.closest('.leak'); if (b) openList({ o: +b.dataset.o }); });

  /* ---------- week by week (whole year, the picked dates highlighted) ---------- */
  function renderWeeks() {
    const el = $('#weeks'), W = Math.max(320, el.clientWidth || 500), H = 220, L = 40, B = 24, T = 10;
    const nW = Math.floor(LAST / 7) + 1, g = Array.from({ length: nW }, () => [0, 0, 0]);
    for (let i = 0; i < N; i++) { if (!inScope(i)) continue; const w = Math.floor(AD[i] / 7), o = AO[i]; g[w][o === 0 ? 0 : o <= 2 ? 1 : 2]++; }
    const mx = Math.max(1, ...g.map(x => x[0] + x[1] + x[2])), bw = (W - L - 6) / nW;
    const Y = v => H - B - v / mx * (H - B - T);
    let s = '';
    const st = [100, 200, 250, 500, 1000, 2000, 2500, 5000].find(x => x * 4 >= mx) || 10000;
    for (let v = 0; v <= mx; v += st) s += `<line class="grid" x1="${L}" x2="${W}" y1="${Y(v)}" y2="${Y(v)}"/><text class="ax" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v >= 1000 ? (v / 1000) + 'k' : n0(v)}</text>`;
    const col = ['#12875F', '#9DB7D6', '#E3C27D'];
    g.forEach((v, w) => {
      const x = L + w * bw + 1, a0 = w * 7, a1 = Math.min(LAST, a0 + 6), inP = a1 >= V.from && a0 <= V.to;
      let y = H - B;
      v.forEach((c, k) => { const h = c / mx * (H - B - T); y -= h; s += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="${col[k]}" opacity="${inP ? 1 : .35}"/>`; });
      s += `<rect class="mon-hit" data-w="${w}" x="${(L + w * bw).toFixed(1)}" y="${T}" width="${bw.toFixed(1)}" height="${H - B - T}"/>`;
      const d = dOf(a0); if (d.getUTCDate() <= 7) s += `<text class="ax" x="${(x + bw / 2).toFixed(1)}" y="${H - 6}" text-anchor="middle">${MON3[d.getUTCMonth()]}</text>`;
    });
    el.innerHTML = `<div class="keyline"><span><i style="background:${col[0]}"></i>Deal</span><span><i style="background:${col[1]}"></i>Attended, no deal</span><span><i style="background:${col[2]}"></i>Not attended</span></div><svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg><p class="hint">Weeks from 1 April; the dates you picked are in full colour.</p>`;
    el._g = g;
  }
  $('#weeks').addEventListener('mousemove', ev => { const t = ev.target.closest('.mon-hit'); if (!t) return untip(); const w = +t.dataset.w, v = $('#weeks')._g[w], n = v[0] + v[1] + v[2], a = v[0] + v[1]; tip(`<b>Week of ${esc(fDate(dOf(w * 7), true))}</b><br>${n0(n)} appointments · attended ${fP(pc(a, n))}<br>${n0(v[0])} deals · conversion ${fP(pc(v[0], a))}`, ev); });
  $('#weeks').addEventListener('mouseleave', untip);

  /* ---------- where appointments come from (TME teams) ---------- */
  function teamRows(R) { return TEAMS.map((name, t) => { const o = Array.from(R.tO.subarray(t * 6, t * 6 + 6)), n = o.reduce((s, x) => s + x, 0), a = att(o); return { t, name, o, n, a, attP: pc(a, n), conv: pc(o[0], a) }; }).filter(x => x.n > 0).sort((x, y) => y.n - x.n); }
  function renderSources() {
    const rows = teamRows(CUR), mx = Math.max(1, ...rows.map(r => r.n)), ta = att(CUR.o), tAtt = pc(ta, CUR.n), tConv = pc(CUR.o[0], ta);
    $('#sources').innerHTML = `<div class="src hd"><span>TME team</span><span>Appointments, by outcome</span><span class="r">Given</span><span class="r">Attended</span><span class="r">Conv.</span></div>` +
      rows.map(r => `<button type="button" class="src" data-t="${r.t}"><span class="nm">${esc(r.name)}</span><span class="bars" style="width:${Math.max(4, r.n / mx * 100)}%">${r.o.map((c, o) => c ? `<i style="flex:${c} 0 0;background:${OC[o]}"></i>` : '').join('')}</span>` +
        `<span class="r">${n0(r.n)}</span><span class="r ${r.n >= MIN ? cls(r.attP - tAtt) : 'mu'}">${r.n >= MIN ? fP(r.attP) : '—'}</span><span class="r ${r.a >= MIN ? cls(r.conv - tConv) : 'mu'}">${r.a >= MIN ? fP(r.conv) : '—'}</span></button>`).join('') +
      `<div class="okey">${OUT.map((l, o) => `<span><i style="background:${OC[o]}"></i>${l}</span>`).join('')}</div><p class="hint">Rates are green or red against the whole ${esc(scopeName())} figure (${fP(tAtt)} attended, ${fP(tConv)} conversion). Click a team to see which MEs took its appointments.</p>`;
    $('#sources')._rows = rows;
  }
  $('#sources').addEventListener('click', ev => { const b = ev.target.closest('.src[data-t]'); if (b) openTeam(+b.dataset.t); });

  /* ---------- attendance against conversion ---------- */
  let SC = [];
  function renderScatter() {
    const el = $('#scatter'), pts = MEROWS.filter(r => r.enough && r.att > 0), W = Math.max(320, el.clientWidth || 500), H = 300, L = 58, B = 34, T = 16, R0 = 14;
    if (pts.length < 3) { el.innerHTML = `<p class="empty">Too few MEs with ${MIN}+ appointments in these dates.</p>`; return; }
    const ta = att(CUR.o), tAtt = pc(ta, CUR.n), tConv = pc(CUR.o[0], ta);
    const xs = pts.map(r => r.attP), ys = pts.map(r => r.conv);
    const x0 = Math.max(0, Math.min(...xs) - 3), x1 = Math.min(100, Math.max(...xs) + 3), y0 = Math.max(0, Math.min(...ys) - 3), y1 = Math.min(100, Math.max(...ys) + 3);
    const X = v => L + (v - x0) / (x1 - x0 || 1) * (W - L - R0), Y = v => T + (y1 - v) / (y1 - y0 || 1) * (H - T - B);
    const mx = Math.max(...pts.map(r => r.n));
    let s = '';
    s += `<line x1="${X(tAtt)}" x2="${X(tAtt)}" y1="${T}" y2="${H - B}" stroke="#14213D" stroke-dasharray="4 3" opacity=".4"/><line x1="${L}" x2="${W - R0}" y1="${Y(tConv)}" y2="${Y(tConv)}" stroke="#14213D" stroke-dasharray="4 3" opacity=".4"/>`;
    s += `<text class="qlab" x="${X(tAtt) + 4}" y="${T + 9}">${esc(scopeName())} ${fP(tAtt)}</text><text class="qlab" x="${W - R0}" y="${Y(tConv) - 5}" text-anchor="end">${esc(scopeName())} ${fP(tConv)}</text>`;
    s += `<text class="ax" x="${(L + W) / 2}" y="${H - 4}" text-anchor="middle">Attended (% of appointments given) →</text><text class="ax" x="14" y="${(T + H - B) / 2}" transform="rotate(-90 14 ${(T + H - B) / 2})" text-anchor="middle">Conversion (deals ÷ attended) →</text>`;
    const tick = (lo, hi) => { const st = (hi - lo) > 50 ? 20 : 10, out = []; for (let v = Math.ceil(lo / st) * st; v <= hi; v += st) out.push(v); return out; };
    tick(x0, x1).forEach(v => { s += `<line class="grid" x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${H - B}"/><text class="ax" x="${X(v)}" y="${H - B + 14}" text-anchor="middle">${v}%</text>`; });
    tick(y0, y1).forEach(v => { s += `<line class="grid" x1="${L}" x2="${W - R0}" y1="${Y(v)}" y2="${Y(v)}"/><text class="ax" x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${v}%</text>`; });
    const order = [...pts].sort((a, b) => b.n - a.n);
    SC = order;
    s += order.map((r, i) => `<circle data-i="${i}" cx="${X(r.attP).toFixed(1)}" cy="${Y(r.conv).toFixed(1)}" r="${(3 + 9 * Math.sqrt(r.n / mx)).toFixed(1)}" fill="${r.naHigh || r.rlHigh ? '#C28A1E' : '#1F5FAD'}" fill-opacity="${r.naHigh || r.rlHigh ? .85 : .45}" stroke="#fff" stroke-width="1"/>`).join('');
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg><p class="hint">Each dot is an ME with ${MIN}+ appointments; size = appointments. Dashed lines = ${esc(scopeName())} overall (${fP(tAtt)}, ${fP(tConv)}). <span class="ochip"><i style="background:#C28A1E"></i>amber</span> = a "customer not available" pattern worth a look. Click a dot for the ME.</p>`;
  }
  $('#scatter').addEventListener('mousemove', ev => { const c = ev.target.closest('circle'); if (!c) return untip(); const r = SC[+c.dataset.i]; tip(`<b>${esc(r.name)}</b><br>${n0(r.n)} appointments · attended ${fP(r.attP)}<br>${n0(r.deals)} deals · conversion ${fP(r.conv)}${r.naHigh ? '<br><span class="d">Customer not available: higher than expected</span>' : ''}${r.rlHigh ? '<br><span class="d">"Not available" customers often reached later</span>' : ''}`, ev); });
  $('#scatter').addEventListener('mouseleave', untip);
  $('#scatter').addEventListener('click', ev => { const c = ev.target.closest('circle'); if (c) openMe(SC[+c.dataset.i].me); });

  /* ---------- spread ---------- */
  let SP = [];
  function renderSpread() {
    const el = $('#spread'), rows = [...MEROWS].sort((a, b) => b.n - a.n), n = rows.length;
    SP = rows;
    if (!n) { el.innerHTML = '<p class="empty">No appointments in these dates.</p>'; $('#sprSub').textContent = ''; return; }
    const W = Math.max(320, el.clientWidth || 900), H = 150, L = 40, B = 8, T = 8, bw = (W - L) / n, mx = rows[0].n;
    const tot = rows.reduce((s, r) => s + r.n, 0), totD = rows.reduce((s, r) => s + r.deals, 0), k = Math.max(1, Math.round(n * .2));
    const topN = rows.slice(0, k).reduce((s, r) => s + r.n, 0), topD = rows.slice(0, k).reduce((s, r) => s + r.deals, 0), avg = tot / n;
    const Y = v => T + (1 - v / mx) * (H - T - B);
    let s = `<line class="grid" x1="${L}" x2="${W}" y1="${Y(0)}" y2="${Y(0)}"/><text class="ax" x="${L - 6}" y="${Y(mx) + 4}" text-anchor="end">${n0(mx)}</text><text class="ax" x="${L - 6}" y="${Y(0)}" text-anchor="end">0</text>`;
    rows.forEach((r, i) => { s += `<rect data-i="${i}" x="${(L + i * bw).toFixed(2)}" y="${Y(r.n).toFixed(1)}" width="${Math.max(.6, bw - (bw > 3 ? 1 : 0)).toFixed(2)}" height="${(Y(0) - Y(r.n)).toFixed(1)}" fill="${i < k ? '#1F5FAD' : '#9DB7D6'}"/>`; });
    s += `<line x1="${L}" x2="${W}" y1="${Y(avg)}" y2="${Y(avg)}" stroke="#14213D" stroke-dasharray="4 3" opacity=".55"/><text class="qlab" x="${W - 4}" y="${Y(avg) - 5}" text-anchor="end">average ${n0(avg)} per ME</text>`;
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${s}</svg>`;
    $('#sprSub').innerHTML = `${n0(n)} MEs, most appointments first. The top 20% (<b class="tn">${n0(k)}</b>) got <b class="tn">${fP(pc(topN, tot))}</b> of appointments and closed <b class="tn">${fP(pc(topD, totD))}</b> of deals.`;
  }
  $('#spread').addEventListener('mousemove', ev => { const r0 = ev.target.closest('rect[data-i]'); if (!r0) return untip(); const r = SP[+r0.dataset.i]; tip(`<b>${esc(r.name)}</b><br>${n0(r.n)} appointments (${fP(pc(r.n, CUR.n))} of all)<br>attended ${fP(r.attP)} · ${n0(r.deals)} deals`, ev); });
  $('#spread').addEventListener('mouseleave', untip);
  $('#spread').addEventListener('click', ev => { const r0 = ev.target.closest('rect[data-i]'); if (r0) openMe(SP[+r0.dataset.i].me); });

  /* ---------- ME x TME team ---------- */
  // each TME team is two narrow columns: appointments (shade = share of the ME's own appointments) and, beside them,
  // conversion or attendance (green / red when 5+ points from that TME team's own rate; blank when too few to judge)
  function renderHeat() {
    const R = CUR, teams = teamRows(R), rows = [...MEROWS].sort((a, b) => b.n - a.n), show = V.hmAll ? rows : rows.slice(0, 25);
    document.querySelectorAll('#hmMode button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.hm)));
    const isAtt = V.hm === 'att', word = isAtt ? 'attendance' : 'conversion';
    const cell = (r, t) => { const k = (r.me * NT + t.t) * 3; return { g: R.meT[k], a: R.meT[k + 1], d: R.meT[k + 2] }; };
    const rate = c => isAtt ? pc(c.a, c.g) : pc(c.d, c.a), den = c => isAtt ? c.g : c.a;
    const tip = (r, t, c) => `${r.name} · ${t.name}: ${n0(c.g)} appointments (${fP(c.g / r.n * 100)} of theirs), ${n0(c.a)} attended, ${n0(c.d)} deals` +
      (den(c) >= MINCELL ? `; ${word} ${fP(rate(c))} against ${fP(isAtt ? t.attP : t.conv)} for ${t.name}` : `; too few to judge ${word}`);
    const body = show.map(r => `<tr><td class="rh" data-me="${r.me}" title="${esc(r.name)}">${esc(r.name)}<small>${esc(shortName(r.tl))}</small></td>` + teams.map(t => {
      const c = cell(r, t);
      if (!c.g) return `<td class="c nil">·</td><td class="c cv nil"></td>`;
      const sh = c.g / r.n, ti = esc(tip(r, t, c));
      let h = `<td class="c" data-me="${r.me}" data-t="${t.t}" style="background:rgba(31,95,173,${(.08 + .62 * sh).toFixed(3)});color:${sh > .55 ? '#fff' : 'inherit'}" title="${ti}">${n0(c.g)}</td>`;
      if (den(c) < MINCELL) return h + `<td class="c cv few" data-me="${r.me}" data-t="${t.t}" title="${ti}"></td>`;
      const v = rate(c), dlt = v - (isAtt ? t.attP : t.conv);
      return h + `<td class="c cv" data-me="${r.me}" data-t="${t.t}" style="background:${dlt >= 5 ? '#BFE3D3' : dlt <= -5 ? '#F3C6BF' : '#F3F5F8'}" title="${ti}">${Math.round(v)}%</td>`;
    }).join('') + `<td class="tot">${n0(r.n)}<small>${r.enough ? fP(isAtt ? r.attP : r.conv) : ''}</small></td></tr>`).join('');
    const sub = isAtt ? 'Att.' : 'Conv.';
    $('#heat').innerHTML = `<div class="hm"><table><thead><tr><th class="rh" rowspan="2">ME <span class="mu">(team leader)</span></th>${teams.map(t => `<th colspan="2" data-t="${t.t}" title="Open ${esc(t.name)}">${esc(t.name)}<br><span class="mu tn">${n0(t.n)} · ${fP(isAtt ? t.attP : t.conv)}</span></th>`).join('')}<th rowspan="2">All</th></tr>` +
      `<tr class="sub">${teams.map(() => `<th>Appts</th><th>${sub}</th>`).join('')}</tr></thead><tbody>${body}</tbody></table></div>` +
      `<p class="hint">Appointments: shade = share of that ME's own appointments. ${isAtt ? 'Attendance' : 'Conversion (deals ÷ attended)'}: green = 5+ points above that TME team's own, red = 5+ below, blank = under ${MINCELL} ${isAtt ? 'appointments' : 'attended'} to judge. Under each team: its appointments · its ${word}. Click a name for the ME, a team for the TME team, a cell for those appointments.</p>` +
      (rows.length > 25 ? `<button type="button" class="btn more" id="hmAll">${V.hmAll ? 'Show the top 25' : `Show all ${n0(rows.length)} MEs`}</button>` : '');
    const h1 = $('#heat thead tr').offsetHeight;
    document.querySelectorAll('#heat thead tr.sub th').forEach(th => { th.style.top = h1 + 'px'; });
  }
  $('#heat').addEventListener('click', ev => {
    if (ev.target.closest('#hmAll')) { V.hmAll = !V.hmAll; renderHeat(); return; }
    const c = ev.target.closest('td.c[data-t]'); if (c) return openList({ me: +c.dataset.me, t: +c.dataset.t });
    const r = ev.target.closest('td.rh[data-me]'); if (r) return openMe(+r.dataset.me);
    const h = ev.target.closest('th[data-t]'); if (h) openTeam(+h.dataset.t);
  });
  $('#hmMode').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) { V.hm = b.dataset.v; renderHeat(); } });

  /* ---------- table ---------- */
  const COLS = [['name', 'ME'], ['tl', 'Team leader'], ['n', 'Appointments'], ['share', 'Share'], ['attP', 'Attended'], ['attVs', 'vs lead mix'], ['naP', 'Customer not available'], ['rlP', 'Reached later'],
    ['o4', 'Pending'], ['o5', 'Not visited'], ['deals', 'Deals'], ['conv', 'Conversion'], ['convVs', 'vs lead mix']];
  const cv = (r, k) => k === 'share' ? pc(r.n, CUR.n) : k === 'o4' ? r.o[4] : k === 'o5' ? r.o[5] : r[k];
  function renderTable() {
    const q = $('#tableSearch').value.trim().toLowerCase();
    let rows = q ? MEROWS.filter(r => (r.name + ' ' + r.tl + ' ' + r.code).toLowerCase().includes(q)) : MEROWS.slice();
    const k = V.sort, d = V.dir;
    rows.sort((a, b) => { const x = cv(a, k), y = cv(b, k); if (k === 'name' || k === 'tl') return d * String(x).localeCompare(String(y)); if (x === null && y === null) return 0; if (x === null) return 1; if (y === null) return -1; return d * (x - y); });
    const arrow = c => V.sort === c ? `<svg class="ar" viewBox="0 0 10 10" aria-hidden="true"><path d="${V.dir > 0 ? 'M2 6.5l3-3 3 3' : 'M2 3.5l3 3 3-3'}"/></svg>` : '';
    const td = (r, c) => {
      if (c === 'name') return `<td class="nm" title="${esc(r.code)}">${esc(r.name)}${r.naHigh || r.rlHigh ? ` <span class="flag" title="${r.naHigh ? 'Customer not available higher than expected for this lead mix. ' : ''}${r.rlHigh ? 'Many “not available” customers were attended within 30 days.' : ''}">check</span>` : ''}</td>`;
      if (c === 'tl') return `<td style="text-align:left">${esc(r.tl)}</td>`;
      const x = cv(r, c), en = r.enough;
      if (c === 'n' || c === 'deals' || c === 'o4' || c === 'o5') return `<td>${n0(x)}</td>`;
      if (c === 'share') return `<td>${fP(x)}</td>`;
      if (c === 'attVs' || c === 'convVs') return `<td class="${en ? cls(x) : 'mu'}">${en ? fPts(x) : '—'}</td>`;
      if (c === 'naP') return `<td class="${r.naHigh ? 'dn' : ''}">${n0(r.na)} <span class="mu">(${en ? fP(x) : '—'})</span></td>`;
      if (c === 'rlP') return `<td class="${r.rlHigh ? 'dn' : ''}">${r.rlDone ? `${n0(r.rlYes)} of ${n0(r.rlDone)}` : '—'}</td>`;
      return `<td class="${en ? '' : 'mu'}">${en ? fP(x) : '—'}</td>`;
    };
    $('#tbl').innerHTML = `<table><thead><tr>${COLS.map(([c, l]) => `<th data-k="${c}" ${V.sort === c ? `aria-sort="${V.dir > 0 ? 'ascending' : 'descending'}"` : ''}>${l}${arrow(c)}</th>`).join('')}</tr></thead><tbody>` +
      rows.slice(0, 400).map(r => `<tr class="go" data-me="${r.me}">${COLS.map(([c]) => td(r, c)).join('')}</tr>`).join('') + `</tbody></table>` +
      (rows.length > 400 ? `<p class="hint">Showing 400 of ${n0(rows.length)}; search to find others.</p>` : '') + (rows.length ? '' : `<p class="empty">No ME matches.</p>`);
  }
  $('#tbl').addEventListener('click', ev => { const th = ev.target.closest('th'); if (th) { const k = th.dataset.k; if (V.sort === k) V.dir = -V.dir; else { V.sort = k; V.dir = k === 'name' || k === 'tl' ? 1 : -1; } return renderTable(); } const tr = ev.target.closest('tr.go'); if (tr) openMe(+tr.dataset.me); });
  $('#tableSearch').addEventListener('input', renderTable);
  $('#csv').addEventListener('click', () => {
    const head = ['ME code', 'ME', 'Team leader', 'Appointments', 'Attended', 'Attended %', 'Attended vs lead mix (pts)', 'Deals', 'Conversion %', 'Conversion vs lead mix (pts)', 'Customer not available', 'Expected for lead mix', 'Not available checked after 30 days', 'Of those, attended within 30 days', 'Pending', 'Not visited', 'Follow up', 'Not interested'];
    const f = x => x === null || x === undefined || !isFinite(x) ? '' : (+x).toFixed(2);
    const lines = [head, ...MEROWS.sort((a, b) => b.n - a.n).map(r => [r.code, r.name, r.tl, r.n, r.att, f(r.attP), f(r.attVs), r.deals, f(r.conv), f(r.convVs), r.na, f(r.naExp), r.rlDone, r.rlYes, r.o[4], r.o[5], r.o[1], r.o[2]])];
    const csv = '﻿' + lines.map(l => l.map(x => /[",\n]/.test(String(x)) ? `"${String(x).replace(/"/g, '""')}"` : x).join(',')).join('\r\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    a.download = `ME_team_${scopeName().replace(/\W+/g, '_')}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`; document.body.append(a); a.click(); a.remove();
  });

  /* ---------- drawer ---------- */
  const DR = $('#drawer');
  function openDrawer(html) { $('#drawerBody').innerHTML = html; DR.classList.add('open'); DR.setAttribute('aria-hidden', 'false'); $('#dim').hidden = false; DR.focus({ preventScroll: true }); }
  function closeDrawer() { DR.classList.remove('open'); DR.setAttribute('aria-hidden', 'true'); $('#dim').hidden = true; }
  $('#drawerClose').addEventListener('click', closeDrawer); $('#dim').addEventListener('click', closeDrawer);
  const strip = (o, n) => `<div class="ostrip">${o.map((c, k) => c ? `<span style="flex:${c} 0 0;background:${OC[k]}" title="${OUT[k]}: ${n0(c)}">${c / n >= .08 ? Math.round(c / n * 100) + '%' : ''}</span>` : '').join('')}</div>`;
  const outChip = o => `<span class="ochip"><i style="background:${OC[o]}"></i>${OUT[o]}</span>`;
  function apptRows(filter, limit) {
    const out = [];
    for (let i = N - 1; i >= 0; i--) { const d = AD[i]; if (d < V.from || d > V.to || !inScope(i) || !filter(i)) continue; out.push(i); }
    return out;
  }
  function apptTable(idx, cols, limit = 150) {
    return `<table class="dl"><thead><tr><th>Date</th><th>Business</th>${cols.includes('me') ? '<th>ME</th>' : ''}${cols.includes('tme') ? '<th>TME (team)</th>' : ''}<th>Outcome</th></tr></thead><tbody>` +
      idx.slice(0, limit).map(i => `<tr><td class="tn">${esc(fDate(dOf(AD[i])))}</td><td>${esc(CO[i] || PID[i])}</td>${cols.includes('me') ? `<td>${esc(MES[AME[i]][1])}</td>` : ''}${cols.includes('tme') ? `<td>${esc(TMES[ATM[i]][1])} <span class="mu">(${esc(TEAMS[ATT[i]])})</span></td>` : ''}<td>${outChip(AO[i])}</td></tr>`).join('') +
      `</tbody></table>${idx.length > limit ? `<p class="hint">Latest ${limit} of ${n0(idx.length)}.</p>` : ''}`;
  }
  function openMe(me) {
    const r = MEROWS.find(x => x.me === me); if (!r) return;
    const ta = att(CUR.o), tAtt = pc(ta, CUR.n), tConv = pc(CUR.o[0], ta);
    const teams = teamRows(CUR).map(t => { const k = (me * NT + t.t) * 3; return { ...t, g: CUR.meT[k], a: CUR.meT[k + 1], d: CUR.meT[k + 2] }; }).filter(t => t.g > 0);
    const wk = Array.from({ length: Math.floor(LAST / 7) + 1 }, () => [0, 0]);
    for (let i = 0; i < N; i++) if (AME[i] === me) { const w = Math.floor(AD[i] / 7); wk[w][0]++; if (AO[i] === 0) wk[w][1]++; }
    const mx = Math.max(1, ...wk.map(x => x[0])), Wd = 500, Hd = 90, bw = Wd / wk.length;
    const spark = `<svg width="100%" viewBox="0 0 ${Wd} ${Hd}" preserveAspectRatio="none" style="height:${Hd}px">${wk.map((v, w) => { const h = v[0] / mx * (Hd - 4), hd = v[1] / mx * (Hd - 4), inP = w * 7 + 6 >= V.from && w * 7 <= V.to; return `<rect x="${(w * bw).toFixed(1)}" y="${(Hd - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="#9DB7D6" opacity="${inP ? 1 : .4}"/><rect x="${(w * bw).toFixed(1)}" y="${(Hd - hd).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${hd.toFixed(1)}" fill="#12875F" opacity="${inP ? 1 : .4}"/>`; }).join('')}</svg>`;
    const checks = `<div class="check"><b>Customer not available:</b> ${n0(r.na)} of ${n0(r.n)} (${fP(r.naP)}). ${r.enough ? `For this ME's mix of TME teams, about <b>${n0(r.naExp)}</b> would be expected at ${esc(scopeName())}'s rates.${r.naHigh ? ' <span class="flag">higher than expected</span>' : ''}` : `Too few appointments to compare.`}</div>` +
      `<div class="check"><b>Reached later:</b> ${r.rlDone ? `of ${n0(r.rlDone)} "not available" appointments old enough to check, the same business had an <b>attended</b> appointment within 30 days in <b>${n0(r.rlYes)}</b> (${fP(r.rlP)}; ${esc(scopeName())} ${fP(CUR.rl[0] ? CUR.rl[1] / CUR.rl[0] * 100 : null)}).${r.rlHigh ? ' <span class="flag">well above the team</span>' : ''}` : 'no "not available" appointments old enough to check (30 days).'} These are prompts to look closer, not proof.</div>`;
    const list = apptRows(i => AME[i] === me);
    openDrawer(`<h2 id="drawerH" style="font-size:30px">${esc(r.name)}</h2><p class="where">${esc(r.code)} · team leader ${esc(r.tl)} · ME Head ${esc(MGRS[HEAD[ME_TL[me]]] ? MGRS[HEAD[ME_TL[me]]][1] : '')}<br>${esc(fRange(V.from, V.to))}</p>` +
      `<div class="kv"><div><div class="k">Appointments</div><div class="v tn">${n0(r.n)}</div><div class="cmp">${fP(pc(r.n, CUR.n))} of all</div></div>` +
      `<div><div class="k">Attended</div><div class="v tn">${fP(r.attP)}</div><div class="cmp">all ${fP(tAtt)} · vs lead mix <span class="${cls(r.attVs)}">${r.enough ? fPts(r.attVs) : '—'}</span></div></div>` +
      `<div><div class="k">Deals</div><div class="v tn">${n0(r.deals)}</div><div class="cmp">${fP(pc(r.deals, CUR.o[0]))} of all</div></div>` +
      `<div><div class="k">Conversion</div><div class="v tn">${fP(r.conv)}</div><div class="cmp">all ${fP(tConv)} · vs lead mix <span class="${cls(r.convVs)}">${r.enough ? fPts(r.convVs) : '—'}</span></div></div></div>` +
      `<h3>What happened to the appointments</h3>${strip(r.o, r.n)}<div class="okey">${OUT.map((l, o) => r.o[o] ? `<span><i style="background:${OC[o]}"></i>${l} ${n0(r.o[o])}</span>` : '').join('')}</div>` + checks +
      `<h3>By TME team</h3><table class="dl"><thead><tr><th>TME team</th><th class="n">Appts</th><th class="n">Attended</th><th class="n">Team</th><th class="n">Conv.</th><th class="n">Team</th></tr></thead><tbody>${teams.map(t => `<tr><td>${esc(t.name)}</td><td class="n">${n0(t.g)}</td><td class="n">${t.g >= MINCELL ? fP(pc(t.a, t.g)) : '—'}</td><td class="n mu">${fP(t.attP)}</td><td class="n">${t.a >= MINCELL ? fP(pc(t.d, t.a)) : '—'}</td><td class="n mu">${fP(t.conv)}</td></tr>`).join('')}</tbody></table>` +
      `<h3>Week by week, the whole year</h3>${spark}<div class="okey"><span><i style="background:#9DB7D6"></i>appointments</span><span><i style="background:#12875F"></i>deals</span></div>` +
      `<h3>Appointments</h3>${apptTable(list, ['tme'])}`);
  }
  function openTeam(t) {
    const tr = teamRows(CUR).find(x => x.t === t); if (!tr) return;
    const rows = MEROWS.map(r => { const k = (r.me * NT + t) * 3; return { r, g: CUR.meT[k], a: CUR.meT[k + 1], d: CUR.meT[k + 2] }; }).filter(x => x.g > 0).sort((a, b) => b.g - a.g);
    const k5 = rows.slice(0, 5).reduce((s, x) => s + x.g, 0);
    openDrawer(`<h2 id="drawerH" style="font-size:30px">${esc(tr.name)}</h2><p class="where">TME team · appointments given to ${esc(scopeName())} MEs, ${esc(fRange(V.from, V.to))}</p>` +
      `<div class="kv"><div><div class="k">Appointments</div><div class="v tn">${n0(tr.n)}</div><div class="cmp">${fP(pc(tr.n, CUR.n))} of all</div></div><div><div class="k">Attended</div><div class="v tn">${fP(tr.attP)}</div><div class="cmp">all ${fP(pc(att(CUR.o), CUR.n))}</div></div>` +
      `<div><div class="k">Deals</div><div class="v tn">${n0(tr.o[0])}</div><div class="cmp">${fP(pc(tr.o[0], CUR.o[0]))} of all</div></div><div><div class="k">Conversion</div><div class="v tn">${fP(tr.conv)}</div><div class="cmp">all ${fP(pc(CUR.o[0], att(CUR.o)))}</div></div></div>` +
      `<h3>What happened to them</h3>${strip(tr.o, tr.n)}<div class="okey">${OUT.map((l, o) => tr.o[o] ? `<span><i style="background:${OC[o]}"></i>${l} ${n0(tr.o[o])}</span>` : '').join('')}</div>` +
      `<h3>Which MEs took them</h3><p class="cmp">${n0(rows.length)} MEs; the top 5 took ${fP(pc(k5, tr.n))}.</p>` +
      `<table class="dl"><thead><tr><th>ME</th><th class="n">Appts</th><th class="n">Share</th><th class="n">Attended</th><th class="n">Deals</th><th class="n">Conv.</th></tr></thead><tbody>${rows.slice(0, 60).map(x => `<tr class="go" data-me="${x.r.me}"><td>${esc(x.r.name)}</td><td class="n">${n0(x.g)}</td><td class="n">${fP(pc(x.g, tr.n))}</td><td class="n">${x.g >= MINCELL ? fP(pc(x.a, x.g)) : '—'}</td><td class="n">${n0(x.d)}</td><td class="n">${x.a >= MINCELL ? fP(pc(x.d, x.a)) : '—'}</td></tr>`).join('')}</tbody></table>` +
      (rows.length > 60 ? `<p class="hint">Top 60 of ${n0(rows.length)} MEs.</p>` : ''));
  }
  function openList(f) {
    const filt = i => (f.o === undefined || AO[i] === f.o) && (f.me === undefined || AME[i] === f.me) && (f.t === undefined || ATT[i] === f.t);
    const idx = apptRows(filt);
    const title = [f.o !== undefined ? OUT[f.o] : 'Appointments', f.me !== undefined ? MES[f.me][1] : '', f.t !== undefined ? TEAMS[f.t] : ''].filter(Boolean).join(' · ');
    const byMe = new Map(); idx.forEach(i => byMe.set(AME[i], (byMe.get(AME[i]) || 0) + 1));
    const top = [...byMe.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
    openDrawer(`<h2 id="drawerH" style="font-size:26px">${esc(title)}</h2><p class="where">${n0(idx.length)} appointments · ${esc(scopeName())} · ${esc(fRange(V.from, V.to))}</p>` +
      (f.me === undefined && top.length > 1 ? `<h3>Most of these were with</h3><table class="dl"><tbody>${top.map(([me, c]) => `<tr class="go" data-me="${me}"><td>${esc(MES[me][1])}</td><td class="n">${n0(c)}</td><td class="n mu">${fP(pc(c, idx.length))}</td></tr>`).join('')}</tbody></table>` : '') +
      `<h3>The appointments</h3>${apptTable(idx, ['me', 'tme'])}`);
  }
  $('#drawerBody').addEventListener('click', ev => { const tr = ev.target.closest('tr.go[data-me]'); if (tr) openMe(+tr.dataset.me); });

  /* ---------- team and period pickers ---------- */
  const TP = $('#teamPop'), TB = $('#teamBtn'), PP = $('#periodPop'), PB = $('#periodBtn');
  function place(pop, btn) { const r = btn.getBoundingClientRect(); pop.hidden = false; pop.style.top = (r.bottom + 8) + 'px'; pop.style.left = Math.max(8, Math.min(innerWidth - pop.offsetWidth - 8, r.right - pop.offsetWidth)) + 'px'; btn.setAttribute('aria-expanded', 'true'); }
  function closePops() { [[TP, TB], [PP, PB]].forEach(([p, b]) => { p.hidden = true; b.setAttribute('aria-expanded', 'false'); }); }
  function teamList(q) {
    const list = HEADS.filter(h => h.size >= 2 && (!q || h.name.toLowerCase().includes(q)));
    return `<button type="button" class="pre" data-h="-1" aria-pressed="${V.head < 0}"><span>All ME Heads (${esc(META.city)})</span><small>${n0(HEADS.reduce((s, h) => s + h.size, 0))} MEs</small></button>` +
      list.map(h => `<button type="button" class="pre" data-h="${h.h}" aria-pressed="${V.head === h.h}"><span>${esc(h.name)}</span><small>${n0(h.size)} MEs</small></button>`).join('');
  }
  TB.addEventListener('click', () => {
    if (!TP.hidden) return closePops(); closePops();
    TP.innerHTML = `<label class="search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="tq" type="search" placeholder="Find an ME Head" autocomplete="off"></label><div class="teams" id="tlist">${teamList('')}</div>`;
    place(TP, TB); $('#tq').focus();
    $('#tq').addEventListener('input', e => { $('#tlist').innerHTML = teamList(e.target.value.trim().toLowerCase()); });
  });
  TP.addEventListener('click', ev => { const b = ev.target.closest('button.pre'); if (!b) return; V.head = +b.dataset.h; closePops(); render(true); });
  PB.addEventListener('click', () => {
    if (!PP.hidden) return closePops(); closePops();
    PP.innerHTML = PRESETS.map(p => `<button type="button" class="pre" data-k="${p.k}" aria-pressed="${V.preset === p.k}"><span>${esc(p.label)}</span><small>${esc(fRange(p.a, p.b))}${p.pa !== null ? ` · vs ${esc(p.pl || fRange(p.pa, p.pb))}` : ''}</small></button>`).join('') +
      `<div class="custom"><label>From<input type="date" id="pFrom" min="${META.fy}" max="${META.end}" value="${iso(dOf(V.from))}"></label><label>To<input type="date" id="pTo" min="${META.fy}" max="${META.end}" value="${iso(dOf(V.to))}"></label><span class="err" id="pErr"></span><button type="button" class="btn" id="pApply">Show these dates</button></div>`;
    place(PP, PB);
  });
  PP.addEventListener('click', ev => {
    const b = ev.target.closest('button.pre'); if (b) { setPreset(b.dataset.k); closePops(); return render(true); }
    if (ev.target.id === 'pApply') {
      const a = offOf($('#pFrom').value), z = offOf($('#pTo').value);
      if (!isFinite(a) || !isFinite(z)) return void ($('#pErr').textContent = 'Pick both dates.');
      if (a > z) return void ($('#pErr').textContent = 'The start date is after the end date.');
      if (a < 0 || z > LAST) return void ($('#pErr').textContent = `Pick dates from ${fDate(dOf(0), true)} to ${fDate(dOf(LAST), true)}.`);
      const len = z - a + 1, pa = a - len;
      Object.assign(V, { from: a, to: z, preset: null, pa: pa >= 0 ? pa : null, pb: pa >= 0 ? a - 1 : null, pl: '' });
      closePops(); render(true);
    }
  });
  document.addEventListener('mousedown', ev => { if (!TP.hidden && !TP.contains(ev.target) && !TB.contains(ev.target)) closePops(); if (!PP.hidden && !PP.contains(ev.target) && !PB.contains(ev.target)) closePops(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') { if (!TP.hidden || !PP.hidden) closePops(); else if (DR.classList.contains('open')) closeDrawer(); } });
  $('#trail').addEventListener('click', ev => { const b = ev.target.closest('.stub'); if (b) { V.head = +b.dataset.h; render(true); } });
  $('#home').addEventListener('click', ev => { ev.preventDefault(); V.head = -1; render(true); });

  /* ---------- link state ---------- */
  function writeHash() { const h = new URLSearchParams(); if (V.head >= 0) h.set('head', MGRS[V.head][0]); if (V.preset && V.preset !== 'lm') h.set('period', V.preset); else if (!V.preset) { h.set('from', iso(dOf(V.from))); h.set('to', iso(dOf(V.to))); } const s = h.toString(); history.replaceState(null, '', s ? '#' + s : location.pathname); }
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.has('head')) { const i = MGRS.findIndex(m => m[0] === h.get('head')); if (i >= 0) V.head = i; }
    if (h.has('period')) setPreset(h.get('period'));
    else if (h.has('from') && h.has('to')) { const a = offOf(h.get('from')), z = offOf(h.get('to')); if (a >= 0 && z <= LAST && a <= z) { const len = z - a + 1; Object.assign(V, { from: a, to: z, preset: null, pa: a - len >= 0 ? a - len : null, pb: a - len >= 0 ? a - 1 : null }); } }
  }

  /* ---------- notes ---------- */
  function renderNotes() {
    const c = META.check;
    $('#notes').innerHTML = [
      `<p><b>Appointments.</b> datagrowth.tbl_final_data_appt (server 240), ${esc(META.city)}: appointments given to MEs, counted as the Sales MIS counts them (jda_flag 0 and 3; every appointment with a real disposition, including those a BDE set, which the table marks given_count 0; MEs in team Corporate or section Sales (Training) are left out; a Sunday appointment counts on the Saturday before), 1 April to ${esc(fDate(dOf(LAST), true))}; refreshed ${esc(META.refreshed.replace('T', ' at '))}. The date is the appointment's to_date.</p>`,
      `<p><b>Attended</b> = the outcome is Deal, Follow up or Not interested. <b>Not attended</b> = Customer not available, Pending update (no outcome recorded) or Not visited by the ME. <b>Conversion</b> = deals ÷ attended.</p>`,
      META.dealSrc && META.dealSrc.dump !== undefined
        ? `<p><b>Deals</b> come from the deals table (db_paidcontracts.daily_deals_closed_dump, server 216): an appointment is a deal when its business (docid) has a deal that day. The deals table books Sunday deals on the Saturday before, so a Saturday deal also counts for an appointment the next day or two. A business's deal that day counts once, for one appointment. Against the appointment table's own Dealclosed (${n0(META.dealSrc.table)}): ${n0(META.dealSrc.toDeal)} appointments not marked Dealclosed there had a deal, and are counted as deals (so as attended); ${n0(META.dealSrc.fromDeal)} marked Dealclosed there had no deal of their own (mostly a second appointment of the same business that day) and are counted with Follow up.${META.dealSrc.recentTo ? ` Deals after ${esc(META.dealSrc.dumpTo)} (to ${esc(META.dealSrc.recentTo)}) come from the 30-day rolling deals table (db_paidcontracts.tbl_30_day_rolling_dealdump_data), which is refreshed earlier each morning than the deals table.` : ''}</p>`
        : `<p><b>Deals</b> are the appointment table's own Dealclosed (the deals table was not read on this refresh).</p>`,
      `<p><b>ME Head</b> = the top of each appointment's reporting chain (team leader, their manager, and so on). <b>Comparison</b>: last month against the month before; This month against the same days of last month; any dates against the same number of days just before.</p>`,
      `<p><b>vs lead mix</b> compares an ME with ${esc(scopeName())}'s own rates for the same TME teams, so an ME who gets harder or easier leads is judged fairly. Rates and checks need ${MIN}+ appointments; heatmap rates need ${MINCELL}+.</p>`,
      `<p><b>"Customer not available" checks</b> are prompts to look closer, not findings. <i>Higher than expected</i>: the ME's count is at least 5 above, and 2 standard errors above, what their TME-team mix predicts. <i>Reached later</i>: the same business (parentid) had an attended appointment with any ME within 30 days; only appointments at least 30 days old are checked; flagged when well above the team share.</p>`,
      `<p><b>Check.</b> ${n0(c.given)} appointments, ${n0(c.attended)} attended, ${n0(c.deals)} deals in the data${c.left_out ? `; ${n0(c.left_out)} left out (outcome not one of the six)` : ''}.</p>`,
    ].join('');
  }

  /* ---------- render ---------- */
  function render(push) {
    untip(); closePops();
    CUR = agg(V.from, V.to); PREV = agg(V.pa, V.pb);
    MEROWS = rowsOfMes(CUR);
    renderBand(); renderFunnel(); renderWeeks(); renderSources(); renderScatter(); renderSpread(); renderHeat(); renderTable(); renderNotes();
    document.title = `${scopeName()} · ME team performance`;
    if (push) writeHash();
  }
  let rz = 0;
  addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { renderWeeks(); renderScatter(); renderSpread(); }, 150); });
  readHash();
  render(false);
})();
