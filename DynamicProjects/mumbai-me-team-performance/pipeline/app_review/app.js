/* ===== JD ME team review: what needs checking in the ME team, why, and the records behind it ===== */
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
  const fN = x => sgn(Math.round(x), n0);
  const cls = x => x === null || !isFinite(x) || x === 0 ? 'mu' : x > 0 ? 'up' : 'dn';
  const plural = (k, one, many) => `${n0(k)} ${k === 1 ? one : (many || one + 's')}`;
  const MON3 = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const MIN = 15;          // pattern checks (Records to verify) only for an ME with at least this many appointments in the dates
  let MINR = 15;           // rates on screen are greyed below this many: 15 for a month or more, 5 for a week, 3 for fewer days
  const minFor = days => days >= 28 ? 15 : days >= 7 ? 5 : 3;
  const MINCELL = 5;       // grid rate cells need this many

  /* ---------- data ---------- */
  const RAW = JSON.parse($('#data').textContent), META = RAW.meta;
  const MES = RAW.mes, MGRS = RAW.mgrs, MGUP = RAW.mgUp, TMES = RAW.tmes, TEAMS = RAW.teams;
  const NME = MES.length, NT = TEAMS.length, NTM = TMES.length;
  function b64(s, T) { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new T(u.buffer); }
  const N = RAW.a.n, AD = b64(RAW.a.d, Uint16Array), AME = b64(RAW.a.me, Uint16Array), AMG = b64(RAW.a.mg, Uint16Array),
    ATM = b64(RAW.a.tme, Uint16Array), ATT = b64(RAW.a.tt, Uint8Array), AO = b64(RAW.a.o, Uint8Array), ARL = b64(RAW.a.rl, Uint8Array),
    AF = b64(RAW.a.f, Uint8Array), ASL = b64(RAW.a.sl, Int32Array), ABK = b64(RAW.a.bk, Int32Array), AEN = b64(RAW.a.en, Int32Array), ADC = b64(RAW.a.dc, Int32Array);
  const CO = RAW.co, PID = RAW.pid;
  // deals closed, as the Sales MIS counts them (15 Oct 2026): one record per deal row of the deals dump (dc_genio as the
  // weight), with its ME, the ME's team leader that month (65535 = none) and its TME team; not tied to an appointment
  const DLN = RAW.dl.n, DLD = b64(RAW.dl.d, Uint16Array), DLME = b64(RAW.dl.me, Uint16Array), DLMG = b64(RAW.dl.mg, Uint16Array),
    DLT = b64(RAW.dl.tt, Uint8Array), DLW = Float64Array.from(b64(RAW.dl.w, Float32Array), v => Math.round(v * 100) / 100), DLPID = RAW.dl.pid || [];
  const NC = RAW.nc, NCN = NC.n, NCD = b64(NC.d, Uint16Array), NCME = b64(NC.me, Uint16Array), NCTM = b64(NC.tme, Uint16Array), NCK = b64(NC.k, Uint8Array);
  const MONTHS = META.months || [], NM = MONTHS.length, HRD = NM ? b64(RAW.hr.days, Uint16Array) : new Uint16Array(0);
  const HRJ = RAW.hr.j, HRDES = RAW.hr.des, HRCITY = RAW.hr.city, HRGRADE = RAW.hr.grade || [];
  // per ME and month: does the Sales MIS count the ME's deals in this city? 1 yes, 0 no (another city), 2 not known
  const HRMIS = NM && RAW.hr.mis ? b64(RAW.hr.mis, Uint8Array) : new Uint8Array(0);
  // outcomes: 0 deal, 1 follow up, 2 not interested (attended); 3 customer not available, 4 pending, 5 not visited (not attended)
  const OUT = ['Dealclosed', 'Follow Up', 'Not Interested', 'Not Available', 'Pending', 'Not Visited'];   // the JD dispositions
  const OC = ['#12875F', '#1F5FAD', '#D9468C', '#C28A1E', '#8B5CF6', '#B8322A'];
  const F = { naEarly: 1, dealBeforeBooked: 2, noBooking: 4, pending: 8, sameDay: 16 };
  const FY0 = new Date(META.fy + 'T00:00:00Z');
  const dOf = o => new Date(FY0.getTime() + o * 864e5);
  const fDate = (d, yr) => `${d.getUTCDate()} ${MON3[d.getUTCMonth()]}${yr ? ' ' + d.getUTCFullYear() : ''}`;
  const fRange = (a, b) => { const A = dOf(a), B = dOf(b); if (a === b) return fDate(A, true); if (A.getUTCMonth() === B.getUTCMonth() && A.getUTCFullYear() === B.getUTCFullYear()) return `${A.getUTCDate()}–${fDate(B, true)}`; return `${fDate(A)} – ${fDate(B, true)}`; };
  const iso = d => d.toISOString().slice(0, 10);
  const offOf = s => Math.round((new Date(s + 'T00:00:00Z') - FY0) / 864e5);
  const LAST = META.days - 1;
  const shortName = n => { const p = String(n).split(' ').filter(Boolean); return p.length > 1 ? `${p[0]} ${p[p.length - 1][0]}.` : p[0] || n; };
  // a time stored as minutes from 1 April
  const fClock = m => { const h = Math.floor(m % 1440 / 60), mi = m % 60; return `${(h + 11) % 12 + 1}:${String(mi).padStart(2, '0')} ${h < 12 ? 'am' : 'pm'}`; };
  const fWhen = (m, day) => m < 0 ? '—' : (Math.floor(m / 1440) === day ? '' : fDate(dOf(Math.floor(m / 1440))) + ', ') + fClock(m);
  const fGap = mins => { const a = Math.abs(mins); if (a < 60) return `${Math.round(a)} min`; if (a < 1440) { const h = Math.floor(a / 60), m = Math.round(a % 60); return m ? `${h} h ${m} min` : `${h} h`; } const d = Math.round(a / 1440); return plural(d, 'day'); };
  const tenure = j => { if (!j) return ''; const d = new Date(j + 'T00:00:00Z'), e = dOf(LAST); let mo = (e.getUTCFullYear() - d.getUTCFullYear()) * 12 + e.getUTCMonth() - d.getUTCMonth(); if (mo < 0) return ''; return mo < 12 ? `joined ${MON3[d.getUTCMonth()]} ${d.getUTCFullYear()} (${plural(mo, 'month')})` : `joined ${MON3[d.getUTCMonth()]} ${d.getUTCFullYear()} (${plural(Math.floor(mo / 12), 'year')})`; };

  // ME Head = top of the reporting chain of the appointment's manager
  const HEAD = MGRS.map((_, m) => { let c = m, seen = new Set([m]); while (MGUP[c] >= 0 && !seen.has(MGUP[c])) { c = MGUP[c]; seen.add(c); } return c; });
  // each ME's usual team leader (most common manager), each TME's usual team, each ME's usual ME Head
  const ME_TL = (() => { const c = new Map(); for (let i = 0; i < N; i++) { const k = AME[i] * 65536 + AMG[i]; c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME).fill(-1), bn = new Int32Array(NME); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();
  const TME_TEAM = (() => { const c = new Float64Array(NTM * NT); for (let i = 0; i < N; i++) c[ATM[i] * NT + ATT[i]]++; const out = new Int16Array(NTM).fill(-1); for (let t = 0; t < NTM; t++) { let b = 0; for (let k = 0; k < NT; k++) if (c[t * NT + k] > b) { b = c[t * NT + k]; out[t] = k; } } return out; })();

  /* ---------- the team hierarchy (2026-10-14): ME head > managers > team leaders > MEs ---------- */
  // From HR's reporting lines (each manager's own usual manager, records.py mg_up) until the official list arrives.
  // ROOT = the ME head at the top of most chains in the last 60 days (Kushal Sharma). An appointment sits in the team of
  // the ME themselves when the ME leads a team (a team leader's own appointments count in their team), else in its
  // manager's team. Teams below a team leader fold into that team leader's team (four levels, as the ME team works).
  // Chains that do not reach the ME head go to one group, OUTN.
  const NMG = MGRS.length, OUTN = NMG;
  const ROOT = (() => { const c = new Float64Array(NMG); for (let i = 0; i < N; i++) if (AD[i] >= LAST - 60) c[HEAD[AMG[i]]]++; let b = 0; for (let m = 1; m < NMG; m++) if (c[m] > c[b]) b = m; return b; })();
  const DEPTH = MGRS.map((_, m) => { let d = 0, c = m; const seen = new Set(); while (c !== ROOT) { if (c < 0 || seen.has(c)) return -1; seen.add(c); c = MGUP[c]; d++; } return d; });
  const TEAMOF = MGRS.map((_, m) => { if (DEPTH[m] < 0) return OUTN; let c = m; while (DEPTH[c] > 2) c = MGUP[c]; return c; });
  const UPN = m => m === OUTN ? ROOT : MGUP[m];   // a team's parent team
  const NDEP = m => m === OUTN ? 1 : DEPTH[m];    // 0 the ME head, 1 a manager, 2 a team leader
  const HEADNAME = MGRS[ROOT][1];
  const OUT_NAME = `Not in ${HEADNAME}'s line`;
  const NNAME = m => m === OUTN ? OUT_NAME : MGRS[m][1];
  const ncode = s => String(s).trim().replace(/^0+/, '');
  const LEAD_OF = new Map(); MGRS.forEach((x, m) => { if (DEPTH[m] >= 0) LEAD_OF.set(ncode(x[0]), m); });
  const ME_OWN = MES.map(x => { const m = LEAD_OF.get(ncode(x[0])); return m === undefined ? -1 : TEAMOF[m]; });           // the team an ME's own appointments sit in
  const ME_LEAD = MES.map(x => { const m = LEAD_OF.get(ncode(x[0])); return m !== undefined && DEPTH[m] <= 2 ? m : -1; });  // the team an ME leads (tag)
  const ANODE = new Uint16Array(N);
  for (let i = 0; i < N; i++) { const o = ME_OWN[AME[i]]; ANODE[i] = o >= 0 ? o : TEAMOF[AMG[i]]; }
  const KIDS = Array.from({ length: NMG + 1 }, () => []);
  for (let m = 0; m < NMG; m++) if (DEPTH[m] === 1 || DEPTH[m] === 2) KIDS[MGUP[m]].push(m);
  KIDS[ROOT].push(OUTN);
  // each ME's usual team (for not-counted appointments, which carry no manager)
  const ME_NODE = (() => { const c = new Map(); for (let i = 0; i < N; i++) { const k = AME[i] * 65536 + ANODE[i]; c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME).fill(-1), bn = new Int32Array(NME); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();
  // a deal sits where its ME's appointments sit: the ME's own team when they lead one, else their team leader's that month
  const DNODE = new Uint16Array(DLN);
  for (let j = 0; j < DLN; j++) { const me = DLME[j], o = ME_OWN[me]; DNODE[j] = o >= 0 ? o : DLMG[j] < NMG ? TEAMOF[DLMG[j]] : ME_NODE[me] >= 0 ? ME_NODE[me] : OUTN; }
  // teams with appointments in the last 60 days (the team picker lists these, plus any with appointments in the dates)
  const RECENT = new Uint8Array(NMG + 1);
  for (let i = 0; i < N; i++) if (AD[i] >= LAST - 60) for (let c = ANODE[i], g = 0; c >= 0 && g < 6; g++) { RECENT[c] = 1; if (c === ROOT) break; c = UPN(c); }

  /* ---------- periods: a day (against the day before with data), a month, the financial year, or any dates ---------- */
  const DAYN = new Uint32Array(LAST + 1);
  for (let i = 0; i < N; i++) if (AD[i] <= LAST) DAYN[AD[i]]++;
  const prevDay = o => { for (let d = o - 1; d >= 0; d--) if (DAYN[d]) return d; return null; };
  // a low day (a holiday or a short day): under 40% of a usual day's appointments given in the city. A day is compared
  // with the previous usual day, and a comparison that takes in a low day says so (2026-10-15)
  const USUAL = (() => { const v = []; for (let d = 0; d <= LAST; d++) if (DAYN[d]) v.push(DAYN[d]); v.sort((x, y) => x - y); return v.length ? v[Math.floor(v.length / 2)] : 0; })();
  const isLow = d => d >= 0 && d <= LAST && DAYN[d] > 0 && DAYN[d] < USUAL * 0.4;
  const prevNormal = o => { for (let d = o - 1; d >= 0; d--) if (DAYN[d] && !isLow(d)) return d; return null; };
  const nextDay = o => { for (let d = o + 1; d <= LAST; d++) if (DAYN[d]) return d; return null; };
  const WD = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const dayName = o => `${WD[dOf(o).getUTCDay()]} ${fDate(dOf(o), true)}`;
  const isProv = o => false;   // days from the allocation API are shown like any other day (agreed with the ME Head, 2026-10-14)
  const dayPeriod = (o, k, label) => { const p = prevNormal(o); return { k, label, a: o, b: o, pa: p, pb: p, name: dayName(o) + (isProv(o) ? ' (provisional)' : ''), pl: p === null ? '' : dayName(p) }; };
  const MONTH_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const monthStart = (y, m) => offOf(`${y}-${String(m + 1).padStart(2, '0')}-01`);
  const MPRE = (() => {
    const out = [], e = dOf(LAST);
    let y = FY0.getUTCFullYear(), m = FY0.getUTCMonth();
    while (y < e.getUTCFullYear() || (y === e.getUTCFullYear() && m <= e.getUTCMonth())) {
      const a = monthStart(y, m), full = (m === 11 ? monthStart(y + 1, 0) : monthStart(y, m + 1)) - 1, b = Math.min(full, LAST), part = b < full;
      const py = m === 0 ? y - 1 : y, pm = m === 0 ? 11 : m - 1, pa = monthStart(py, pm), days = b - a + 1;
      out.push({ k: `${y}-${String(m + 1).padStart(2, '0')}`, part, a, b,
        short: part ? `${MON3[m]} 1–${days}` : MON3[m], long: part ? `${MONTH_LONG[m]} ${y}, 1–${days}` : `${MONTH_LONG[m]} ${y}`,
        pa: pa >= 0 ? pa : null, pb: pa >= 0 ? (part ? Math.min(a - 1, pa + days - 1) : a - 1) : null, pl: part ? `1–${days} ${MON3[pm]}` : MONTH_LONG[pm] });
      if (m === 11) { y++; m = 0; } else m++;
    }
    return out;
  })();
  // ready-made periods, as on the India sales overview (2026-10-12): FY to date, this / last month, this / last quarter
  // (FY quarters: Apr-Jun, Jul-Sep, Oct-Dec, Jan-Mar). A full one is compared with the whole one before it, a part one
  // with the same days of the one before; the FY has no comparison. Same dates twice = listed once.
  const PRESETS = (() => {
    const e = dOf(LAST), ey = e.getUTCFullYear(), em = e.getUTCMonth();
    const ym = (y, m, d) => { const t = y * 12 + m + d; return [Math.floor(t / 12), ((t % 12) + 12) % 12]; };
    const per = (k, label, y, m, n) => {
      const a = monthStart(y, m), [ny, nm] = ym(y, m, n), full = monthStart(ny, nm) - 1, b = Math.min(full, LAST), part = b < full, days = b - a + 1;
      const [py, pm] = ym(y, m, -n), pa0 = monthStart(py, pm), pa = pa0 >= 0 ? pa0 : null, pb = pa === null ? null : (part ? Math.min(a - 1, pa + days - 1) : a - 1);
      const [ly, lm] = ym(y, m, n - 1);
      const nm1 = n === 1 ? `${MONTH_LONG[m]} ${y}` : `${MON3[m]}–${MON3[lm]} ${ly}`;
      const pnm = n === 1 ? MONTH_LONG[pm] : `${MON3[pm]}–${MON3[ym(py, pm, n - 1)[1]]}`;
      return { k, label, a, b, pa, pb, name: part ? `${nm1}, to ${fDate(dOf(b))}` : nm1, pl: pa === null ? '' : part ? fRange(pa, pb) : pnm };
    };
    const q0 = em - (((em - 3) % 12 + 12) % 12) % 3;
    const [lmy, lmm] = ym(ey, em, -1), [lqy, lqm] = ym(ey, q0, -3);
    const LD = DAYN[LAST] ? LAST : prevDay(LAST), PD = LD === null ? null : prevDay(LD);
    const l7a = Math.max(0, LAST - 6), l7p = LAST - 13 >= 0;
    const days = [LD !== null && dayPeriod(LD, 'day', 'Latest day' + (isProv(LD) ? ' (provisional)' : '')), PD !== null && dayPeriod(PD, 'pday', 'Day before'),
      { k: 'l7', label: 'Last 7 days', a: l7a, b: LAST, pa: l7p ? LAST - 13 : null, pb: l7p ? LAST - 7 : null, name: `Last 7 days (${fRange(l7a, LAST)})`, pl: l7p ? fRange(LAST - 13, LAST - 7) : '' }].filter(Boolean);
    const all = [...days, { k: 'fytd', label: 'Financial year to date', a: 0, b: LAST, pa: null, pb: null, name: `Financial year to date (${fRange(0, LAST)})`, pl: '' },
      per('tm', 'This month', ey, em, 1), per('lm', 'Last month', lmy, lmm, 1), per('tq', 'This quarter', ey, q0, 3), per('lq', 'Last quarter', lqy, lqm, 3)];
    const seen = new Set();
    return all.filter(p => { const key = p.a + ':' + p.b; if (p.a < 0 || seen.has(key)) return false; seen.add(key); return true; });
  })();
  const DEFAULT_P = PRESETS.find(p => p.k === 'day') || PRESETS.find(p => p.k === 'lm') || PRESETS[0];   // the ME Head looks at one day

  /* ---------- view state ---------- */
  // scope: one team of the hierarchy (ROOT = all Mumbai); lvl: the table's Show (1 managers, 2 team leaders, 3 MEs)
  const V = { scope: ROOT, cb: 'att', from: 0, to: LAST, pa: null, pb: null, pl: '', preset: null, view: 'table', sortBy: 'n',
    qKind: 'all', qTeam: -1, qSev: 'all', qStat: 'open', qAll: false, lvl: 1, xOpen: new Set(), xShut: new Set(), ovOpen: new Set(), ovShut: new Set(), ovSort: 'n' };
  try { const l = +localStorage.getItem('jd-me-review-show'); if ([1, 2, 3].includes(l)) V.lvl = l; } catch (e) { /* default: managers */ }
  // the Overview's 'Your team' view: 'shares' (team-share ribbons) or 'bars' (Funnel: one bar per line), for every Show
  // level (2026-10-15). Remembered apart for 1-6 days and for 7 days or more, like the Table's two column sets; Funnel by
  // default
  const MS = {}, MS_KEY = () => V.to - V.from + 1 < 7 ? 'jd-me-review-mestyle-day' : 'jd-me-review-mestyle';
  const meStyle = () => { const k = MS_KEY(); if (MS[k]) return MS[k]; try { const v = localStorage.getItem(k); if (v === 'bars' || v === 'shares') return (MS[k] = v); } catch (e) { /* default */ } return 'bars'; };
  function setPreset(k) {
    if (k === 'fy') k = 'fytd';   // older links
    const p = PRESETS.find(x => x.k === k) || MPRE.find(x => x.k === k) || DEFAULT_P;   // a month key (YYYY-MM) from older links still works
    Object.assign(V, { from: p.a, to: p.b, pa: p.pa, pb: p.pb, pl: p.pl || '', preset: p.k });
  }
  setPreset(DEFAULT_P.k);
  // scope: a team and everyone below it (SMASK marks the teams inside it; set in render)
  // conversion: deals as a share of attended (default) or of given -- one switch for the whole page
  const CB = () => V.cb === 'given';
  const cvr = (d, a, g) => CB() ? pc(d, g) : pc(d, a);
  const CVOF = () => CB() ? 'of appointments given' : 'of attended';
  const scoped = () => V.scope !== ROOT;
  const inTeam = (m, s) => { if (s === ROOT) return true; for (let c = m, g = 0; c >= 0 && g < 8; g++) { if (c === s) return true; if (c === ROOT) return false; c = UPN(c); } return false; };
  const SMASK = new Uint8Array(NMG + 1).fill(1);
  const setMask = () => { for (let m = 0; m <= NMG; m++) SMASK[m] = inTeam(m, V.scope) ? 1 : 0; };
  const inScope = i => SMASK[ANODE[i]] === 1;
  const teamName = () => scoped() ? `${NNAME(V.scope)}'s team` : META.city;
  const scopeName = teamName;
  const sDepth = () => NDEP(V.scope);
  const lvl = () => Math.max(V.lvl, sDepth() + 1);   // a team leader's team has only MEs below it
  const isTree = () => lvl() < 3;
  const prevName = () => V.pa === null ? '' : (V.pl || fRange(V.pa, V.pb));
  const periodName = () => { const p = PRESETS.find(x => x.k === V.preset) || MPRE.find(x => x.k === V.preset); return p ? (p.name || p.long) : fRange(V.from, V.to); };


  /* ---------- days present (HR, per month) ---------- */
  const MONTH_SPAN = MONTHS.map((m, k) => {
    const a = offOf(m + '-01'), nx = k + 1 < NM ? offOf(MONTHS[k + 1] + '-01') : (() => { const d = new Date(m + '-01T00:00:00Z'); d.setUTCMonth(d.getUTCMonth() + 1); return offOf(iso(d)); })();
    const hrEnd = META.hrPulled ? offOf(META.hrPulled) : nx - 1;
    return { a, b: nx - 1, len: Math.max(1, Math.min(nx - 1, hrEnd) - a + 1) };
  });
  // days present in the dates, pro rata for part months; null when HR has no record for a month in the dates
  function presentDays(me, a, b) {
    if (!NM) return null;
    let s = 0;
    for (let k = 0; k < NM; k++) {
      const M = MONTH_SPAN[k], lo = Math.max(a, M.a), hi = Math.min(b, M.b);
      if (hi < lo) continue;
      const v = HRD[me * NM + k];
      if (v === 65535) return null;
      s += v / 10 * Math.min(1, (hi - lo + 1) / M.len);
    }
    return Math.round(s * 10) / 10;
  }

  // an ME whose deals the Sales MIS counts in another city in every month of the dates: deals follow the ME's own city,
  // appointments the TME's, so this ME can never show deals here (no deals or conversion shown, 2026-10-15)
  function awayMe(me, a, b) {
    if (!HRMIS.length) return false;
    let any = false;
    for (let k = 0; k < NM; k++) { const M = MONTH_SPAN[k]; if (Math.min(b, M.b) < Math.max(a, M.a)) continue; if (HRMIS[me * NM + k] !== 0) return false; any = true; }
    return any;
  }
  const AWAY_TXT = 'deals count in their own city';

  /* ---------- aggregation ---------- */
  function agg(a, b) {
    const R = { a, b, n: 0, o: new Float64Array(6), meO: new Float64Array(NME * 6), meT: new Float64Array(NME * NT * 3), tO: new Float64Array(NT * 6),
      meRL: new Float64Array(NME * 2), rl: [0, 0], mes: new Set(), meF: new Float64Array(NME * 5), F: new Float64Array(5),
      tmN: new Float64Array(NTM), pair: new Map(), meNC: new Float64Array(NME), nc: 0, meNode: new Int32Array(NME).fill(-1),
      dl: 0, meDl: new Float64Array(NME), tDl: new Float64Array(NT), gMes: new Set() };   // gMes: MEs with appointments given   // dl: deals closed (Sales MIS rule), not Dealclosed appointments (o[0])
    if (a === null || a === undefined || b < a) return R;
    const nd = new Map(), lastNd = new Int32Array(NME).fill(-1);   // each ME's team in the dates: where most of their appointments sit
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < a || d > b || !inScope(i)) continue;
      const me = AME[i], o = AO[i], t = ATT[i], f = AF[i], tm = ATM[i];
      R.n++; R.o[o]++; R.meO[me * 6 + o]++; R.tO[t * 6 + o]++; R.mes.add(me); R.gMes.add(me); R.tmN[tm]++;
      const nk = me * 65536 + ANODE[i]; nd.set(nk, (nd.get(nk) || 0) + 1); lastNd[me] = ANODE[i];
      const k = (me * NT + t) * 3; R.meT[k]++; if (o <= 2) R.meT[k + 1]++;   // [k + 2] = deals closed, from the deal records below
      const rl = ARL[i]; if (rl === 1 || rl === 2) { R.meRL[me * 2]++; R.rl[0]++; if (rl === 1) { R.meRL[me * 2 + 1]++; R.rl[1]++; } }
      if (f) for (let bit = 0; bit < 5; bit++) if (f & (1 << bit)) { R.meF[me * 5 + bit]++; R.F[bit]++; }
      const pk = tm * NME + me; let p = R.pair.get(pk); if (!p) { p = [0, 0, 0, 0]; R.pair.set(pk, p); } p[0]++; if (o <= 2) p[1]++; if (o === 0) p[2]++; if (f & F.noBooking) p[3]++;
    }
    const bn = new Float64Array(NME);   // ties go to the team of the ME's latest appointment
    for (const [k, v] of nd) { const me = Math.floor(k / 65536), m = k % 65536; if (v > bn[me] || (v === bn[me] && m === lastNd[me])) { bn[me] = v; R.meNode[me] = m; } }
    // deals closed in the dates; an ME with deals but no appointment given in them still gets a row (in their deals' team)
    for (let j = 0; j < DLN; j++) {
      const d = DLD[j]; if (d < a || d > b || !SMASK[DNODE[j]]) continue;
      const me = DLME[j], t = DLT[j], w = DLW[j];
      R.dl += w; R.meDl[me] += w; R.tDl[t] += w; R.meT[(me * NT + t) * 3 + 2] += w; R.mes.add(me);
      if (R.meNode[me] < 0) R.meNode[me] = DNODE[j];
    }
    // not-counted appointments carry no manager: they belong to the scope when the ME's usual team does
    for (let i = 0; i < NCN; i++) { const d = NCD[i]; if (d < a || d > b) continue; if (scoped() && !(ME_NODE[NCME[i]] >= 0 && SMASK[ME_NODE[NCME[i]]])) continue; R.meNC[NCME[i]]++; R.nc++; }
    return R;
  }
  const att = o => o[0] + o[1] + o[2];
  // an ME's team leader and manager from their team in the dates; outside the ME head's line, the recorded manager
  const tlOf = m => m >= 0 && m !== OUTN && DEPTH[m] === 2 ? m : -1;
  const mgOf = m => m < 0 || m === OUTN ? -1 : DEPTH[m] === 2 ? MGUP[m] : DEPTH[m] === 1 ? m : -1;
  function rowsOfMes(R) {
    const tg = new Float64Array(NT), ta = new Float64Array(NT), td = new Float64Array(NT), tna = new Float64Array(NT);
    for (let t = 0; t < NT; t++) { const o = R.tO.subarray(t * 6, t * 6 + 6); tg[t] = o.reduce((s, x) => s + x, 0); ta[t] = att(o); td[t] = R.tDl[t]; tna[t] = o[3]; }
    const rlRate = R.rl[0] ? R.rl[1] / R.rl[0] : null;
    const out = [];
    for (const me of R.mes) {
      const o = R.meO.subarray(me * 6, me * 6 + 6), n = o.reduce((s, x) => s + x, 0), a = att(o), dl = Math.round(R.meDl[me] * 100) / 100;
      let eA = 0, eD = 0, eNA = 0;
      for (let t = 0; t < NT; t++) {
        const k = (me * NT + t) * 3, g = R.meT[k], at = R.meT[k + 1];
        if (tg[t]) { eA += g * ta[t] / tg[t]; eNA += g * tna[t] / tg[t]; }
        if (ta[t]) eD += at * td[t] / ta[t];
      }
      const enough = n >= MIN, rlDone = R.meRL[me * 2], rlYes = R.meRL[me * 2 + 1];
      const naZ = (o[3] - eNA) / Math.sqrt(Math.max(eNA, 1));
      const rlZ = rlDone && rlRate ? (rlYes / rlDone - rlRate) / Math.sqrt(rlRate * (1 - rlRate) / rlDone) : 0;
      const pd = R.b - R.a + 1 < 7 ? null : presentDays(me, R.a, R.b);   // HR attendance is monthly: not shown under a week
      const away = awayMe(me, R.a, R.b);
      const node = R.meNode[me], tlN = tlOf(node), mgN = mgOf(node);
      out.push({ me, name: MES[me][1], code: MES[me][0], node, lead: ME_LEAD[me], n, o: Array.from(o), att: a, deals: dl, miss: n - a,
        tl: node === OUTN ? (ME_TL[me] >= 0 ? MGRS[ME_TL[me]][1] : '') : tlN >= 0 ? MGRS[tlN][1] : '',
        mgr: node === OUTN ? OUT_NAME : mgN >= 0 ? MGRS[mgN][1] : '',
        attP: pc(a, n), conv: away ? null : cvr(dl, a, n), attExp: eA, attVs: enough && n ? (a - eA) / n * 100 : null, convVs: !away && enough && a ? (dl - eD) / a * 100 : null, away,
        na: o[3], naP: pc(o[3], n), naExp: eNA, naZ, naHigh: enough && o[3] >= eNA + 5 && naZ >= 2,
        rlDone, rlYes, rlP: rlDone ? rlYes / rlDone * 100 : null, rlZ, rlHigh: rlDone >= 10 && rlRate !== null && rlZ >= 2,
        fl: Array.from(R.meF.subarray(me * 5, me * 5 + 5)), nc: R.meNC[me], pd, perDay: pd ? n / pd : null, attPd: pd ? a / pd : null, enough,
        des: HRDES[me] || '', city: HRCITY[me] || '', grade: HRGRADE[me] || '' });
    }
    return out;
  }

  /* ---------- the checks ---------- */
  // Order = how they are listed. sev: 'rev' = worth checking; 'info' = a pattern to know about, not a problem by itself.
  const CHECKS = {
    noBooking: { label: 'Many deals closed with no allocation record', short: 'Deals closed with no allocation record', level: 'Review',
      when: 'An ME (10+ deals) or a TME–ME pair has 8+ deals whose appointment has no allocation record (allocationtime empty; the appointment time equals the Dealclosed time), and that share is well above the whole scope\'s (3 standard errors).',
      vs: 'The share of all deals closed in the scope with no allocation record.', recs: 'Dealclosed appointments with an empty allocationtime.',
      limits: 'About 3 in 10 deals look like this, so it can be a normal way of recording a deal; what is unusual is one ME or pair far above that. The process behind these rows is not recorded.' },
    dealBeforeBooked: { label: 'Dealclosed before the appointment was allocated', short: 'Dealclosed before allocation', level: 'Review at 2+ per ME; single cases pooled as Information',
      when: 'The Dealclosed time is earlier than the time the appointment was allocated to the ME.', vs: 'Nothing: the order of the two times is the check.',
      recs: 'dealclosed_date against allocationtime.', limits: 'A re-allocated or corrected appointment can also do this. The deals table itself has no times.' },
    naEarly: { label: 'Not Available updated before the appointment time', short: 'Not Available updated early', level: 'Review at 2+ per ME; single cases pooled as Information',
      when: `An appointment with disposition Not Available was updated ${Math.round((META.naEarlyMin || 60) / 60)}+ hour before its appointment time (appointments on the same day only).`, vs: 'The appointment time (actiontime).',
      recs: 'attended_date (when the disposition was updated) against actiontime.', limits: 'An ME can learn early that the customer will not be there. Attended dispositions are often updated early too, because visits happen before the appointment time.' },
    naHigh: { label: 'More Not Available than expected', short: 'Not Available above expected', level: 'Review',
      when: 'The ME (15+ appointments) has at least 5 more Not Available, and 2 standard errors more, than their mix of TME teams predicts.',
      vs: 'The scope\'s own Not Available rate for each TME team, applied to the ME\'s appointments.', recs: 'Appointments with disposition Not Available.',
      limits: 'Territory, appointment times and lead quality beyond the TME team are not in the data.' },
    rlHigh: { label: 'Not Available, then attended within 30 days', short: 'Not Available, attended later', level: 'Review',
      when: 'Of the ME\'s Not Available appointments at least 30 days old (10+), the share whose parentid had an attended appointment (any ME) within 30 days is 2 standard errors above the scope\'s share.',
      vs: 'The same share across the scope.', recs: 'Same parentid, attended appointment within 30 days.', limits: 'A customer can genuinely be away and then available. Only appointments 30+ days old are checked.' },
    naUp: { label: 'Not attended went up against the ME\'s own past', short: 'Not attended up', level: 'Review',
      when: 'The ME\'s not-attended share is 10+ points, and 2.5 standard errors, above their own previous 90 days (15+ appointments now, 30+ before).',
      vs: 'The same ME in the 90 days before the dates.', recs: 'Appointments not attended: Not Available, Pending, Not Visited.',
      limits: 'Leave, a new territory or a change in the TME teams feeding the ME can explain a change.' },
    pending: { label: 'Dispositions not updated (Pending)', short: 'Pending', level: 'Review at 5+',
      when: `5+ appointments still Pending ${META.pendingDays || 2}+ days after the appointment date, as of the refresh.`, vs: 'Nothing: every appointment should have a disposition.',
      recs: 'Disposition Pending.', limits: 'Dispositions updated after the refresh show up on the next refresh.' },
    sameDay: { label: 'Same parentid given more than once on one day', short: 'Same parentid twice', level: 'Information (one item for the scope)',
      when: 'Any appointment was for a parentid with another appointment given that day.', vs: 'Nothing.',
      recs: 'Same parentid, same day, given_count 1.', limits: 'Often the TME fixing it twice; the deal counts once either way.' },
    pairing: { label: 'One TME sends most of their appointments to this ME', short: 'TME → ME pairing', level: 'Information',
      when: 'A TME with 20+ appointments sent 8+, and at least a quarter of them, to one ME: at least 3 times (and 3 standard errors) more than that ME\'s overall share would give.',
      vs: 'The ME\'s share of all appointments in the scope.', recs: 'Appointments of that TME and ME.',
      limits: 'How appointments are allocated (system, TME or team leader) is not recorded, so this is a pattern to verify, not unfair allocation.' },
    volume: { label: 'Appointments given per day present far from the usual', short: 'Appointments given per day present', level: 'Information',
      when: 'Among MEs based in the city (HR) with 15+ appointments and 10+ days present, twice the median per day present or more; or, with 15+ days present, less than 0.4 times the median.',
      vs: 'The median ME in the scope, per day present (HR days present, pro rata for part months).', recs: 'All the ME\'s appointments; HR monthly days present.',
      limits: 'Capacity, targets and territory size are not in the data.' },
  };
  const KINDS = Object.keys(CHECKS);
  const STORE = 'jd-me-review-checked-v1';
  let MARKS = {};
  try { MARKS = JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch (e) { MARKS = {}; }
  const saveMarks = () => { try { localStorage.setItem(STORE, JSON.stringify(MARKS)); } catch (e) { /* browser storage off: marks last for this visit */ } };

  const bin = (k, n, p) => n && p > 0 && p < 1 ? (k / n - p) / Math.sqrt(p * (1 - p) / n) : 0;
  function median(xs) { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b), m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
  function computeItems(R, rows, base) {
    const items = [], meName = me => MES[me][1], scope = scopeName();
    const add = (kind, sev, subj, fields) => items.push(Object.assign({ kind, sev, id: `${kind}|${subj}|${iso(dOf(R.a))}|${iso(dOf(R.b))}`, subj }, fields));
    const byMe = new Map(rows.map(r => [r.me, r]));
    const totDeals = R.o[0], nbShare = totDeals ? R.F[2] / totDeals : 0;
    // TME of most of an ME's flagged records (for the sentence)
    const topTme = (me, bit) => { let best = null; for (const [pk, p] of R.pair) { if (pk % NME !== me) continue; const v = bit === 'nb' ? p[3] : p[0]; if (!best || v > best[1]) best = [Math.floor(pk / NME), v]; } return best; };
    const flaggedNbMe = new Set(), single = { dealBeforeBooked: new Set(), naEarly: new Set(), sameDay: new Set() };
    for (const r of rows) {
      const who = { me: r.me };
      // deals with no allocation record
      const nb = r.fl[2], zNb = bin(nb, r.o[0], nbShare);
      if (r.o[0] >= 10 && nb >= 8 && zNb >= 3) {
        flaggedNbMe.add(r.me);
        const tt = topTme(r.me, 'nb');
        add('noBooking', 'rev', r.code, Object.assign({}, who, { strength: zNb, n: nb,
          why: `<b>${n0(nb)} of ${n0(r.o[0])}</b> deals (${fP(pc(nb, r.o[0]))}) have no allocation record: the appointment was created at the moment of the deal. Across ${esc(scope)}: ${fP(nbShare * 100)}.` +
            (tt && tt[1] >= nb * .5 ? ` ${tt[1] === nb ? 'All' : n0(tt[1])} of them came from TME <b>${esc(TMES[tt[0]][1])}</b>.` : ''),
          cmp: { a: pc(nb, r.o[0]), b: nbShare * 100, al: 'This ME', bl: scope } }));
      }
      // Dealclosed before the appointment was allocated
      if (r.fl[1] >= 2) add('dealBeforeBooked', 'rev', r.code, Object.assign({}, who, { strength: r.fl[1], n: r.fl[1],
        why: `<b>${plural(r.fl[1], 'deal')}</b> were closed before the appointment was allocated.` }));
      else if (r.fl[1] === 1) single.dealBeforeBooked.add(r.me);
      // Not Available updated before the appointment time
      if (r.fl[0] >= 2) add('naEarly', 'rev', r.code, Object.assign({}, who, { strength: r.fl[0], n: r.fl[0],
        why: `<b>${plural(r.fl[0], 'appointment')}</b> updated as Not Available at least 1 hour before the appointment time. Across ${esc(scope)}, ${fP(pc(R.F[0], R.o[3]))} of Not Available dispositions look like this.` }));
      else if (r.fl[0] === 1) single.naEarly.add(r.me);
      if (r.fl[4]) single.sameDay.add(r.me);
      // more not available than the lead mix predicts
      if (r.naHigh) add('naHigh', 'rev', r.code, Object.assign({}, who, { strength: r.naZ, n: r.na,
        why: `<b>${n0(r.na)} of ${n0(r.n)}</b> appointments (${fP(r.naP)}) are Not Available. For this ME's mix of TME teams about <b>${n0(r.naExp)}</b> were expected: <b>${n0(r.na - Math.round(r.naExp))} more</b>.`,
        cmp: { a: r.naP, b: pc(r.naExp, r.n), al: 'This ME', bl: 'Expected' } }));
      // reached later
      if (r.rlHigh) add('rlHigh', 'rev', r.code, Object.assign({}, who, { strength: r.rlZ, n: r.rlYes,
        why: `Of <b>${n0(r.rlDone)}</b> parentids this ME marked Not Available, <b>${n0(r.rlYes)}</b> (${fP(r.rlP)}) had an attended appointment within 30 days. Across ${esc(scope)}: ${fP(pc(R.rl[1], R.rl[0]))}.`,
        cmp: { a: r.rlP, b: pc(R.rl[1], R.rl[0]), al: 'This ME', bl: scope } }));
      // not attended up against own past
      if (base && r.n >= MIN) {
        const bo = base.meO.subarray(r.me * 6, r.me * 6 + 6), bn = bo.reduce((s, x) => s + x, 0), bm = bn - att(bo);
        if (bn >= 30) {
          const p = r.miss / r.n, q = bm / bn, pp = (r.miss + bm) / (r.n + bn), z = pp > 0 && pp < 1 ? (p - q) / Math.sqrt(pp * (1 - pp) * (1 / r.n + 1 / bn)) : 0;
          if (p - q >= .10 && z >= 2.5) add('naUp', 'rev', r.code, Object.assign({}, who, { strength: z, n: r.miss,
            why: `<b>${n0(r.miss)} of ${n0(r.n)}</b> appointments not attended (${fP(p * 100)}), against ${n0(bm)} of ${n0(bn)} (${fP(q * 100)}) in the 90 days before: <b>${fPts((p - q) * 100).replace(' pts', ' points')} more</b>.`,
            cmp: { a: p * 100, b: q * 100, al: 'These dates', bl: 'Before' } }));
        }
      }
      // pending
      if (r.fl[3] >= 5) add('pending', 'rev', r.code, Object.assign({}, who, { strength: r.fl[3], n: r.fl[3],
        why: `<b>${plural(r.fl[3], 'appointment')}</b> are still Pending ${META.pendingDays || 2}+ days after the appointment date (as of the refresh).` }));
    }
    // isolated record problems: one information item per check (its records list names each ME)
    if (single.dealBeforeBooked.size) add('dealBeforeBooked', 'info', 'one-each', { me: -1, mes: single.dealBeforeBooked, strength: 0, n: single.dealBeforeBooked.size,
      why: `<b>${plural(single.dealBeforeBooked.size, 'more ME')}</b> had one deal each closed before the appointment was allocated. Isolated cases, listed together.` });
    if (single.naEarly.size) add('naEarly', 'info', 'one-each', { me: -1, mes: single.naEarly, strength: 0, n: single.naEarly.size,
      why: `<b>${plural(single.naEarly.size, 'more ME')}</b> had one appointment each updated as Not Available 1+ hour before the appointment time. Isolated cases, listed together.` });
    if (single.sameDay.size) add('sameDay', 'info', 'all', { me: -1, mes: single.sameDay, strength: 0, n: R.F[4],
      why: `<b>${plural(R.F[4], 'appointment')}</b> (${plural(single.sameDay.size, 'ME')}) were for a parentid that had another appointment given the same day. Usually the TME fixing it twice; the deal counts once either way.` });
    // pairs: deals with no allocation record (when the ME as a whole is not already listed), and concentration
    const tot = R.n;
    for (const [pk, p] of R.pair) {
      const tm = Math.floor(pk / NME), me = pk % NME, r = byMe.get(me); if (!r) continue;
      if (!flaggedNbMe.has(me) && p[3] >= 8 && bin(p[3], p[2], nbShare) >= 3)
        add('noBooking', 'rev', `${TMES[tm][0]}>${r.code}`, { me, tme: tm, strength: bin(p[3], p[2], nbShare), n: p[3],
          why: `Of the <b>${n0(p[2])}</b> deals on appointments from TME <b>${esc(TMES[tm][1])}</b>, <b>${n0(p[3])}</b> (${fP(pc(p[3], p[2]))}) have no allocation record. Across ${esc(scope)}: ${fP(nbShare * 100)}.`,
          cmp: { a: pc(p[3], p[2]), b: nbShare * 100, al: 'This pair', bl: scope } });
      const T = R.tmN[tm], k = p[0], exp = T * r.n / tot;
      if (T >= 20 && k >= 8 && k / T >= .25 && k >= 3 * exp && (k - exp) / Math.sqrt(exp) >= 3)
        add('pairing', 'info', `${TMES[tm][0]}>${r.code}`, { me, tme: tm, strength: (k - exp) / Math.sqrt(exp), n: k,
          why: `TME <b>${esc(TMES[tm][1])}</b>${TME_TEAM[tm] >= 0 ? ` (${esc(TEAMS[TME_TEAM[tm]])})` : ''} sent <b>${n0(k)} of ${n0(T)}</b> appointments (${fP(pc(k, T))}) to this ME. From the ME's share of all appointments, ${exp < 1 ? 'less than 1' : `about ${n0(exp)}`} would be expected. ${n0(p[2])} of the ${n0(k)} became deals closed.`,
          cmp: { a: pc(k, T), b: pc(exp, T), al: 'To this ME', bl: 'Expected' } });
    }
    // volume per day present
    const local = r => r.city && r.city.toLowerCase() === String(META.city).toLowerCase();
    const cohort = rows.filter(r => r.enough && r.pd >= 10 && local(r)), med = median(cohort.map(r => r.perDay));
    if (med && cohort.length >= 10) {
      for (const r of rows) {
        if (r.pd === null || !local(r)) continue;
        const hi = r.enough && r.pd >= 10 && r.perDay >= 2 * med, lo = r.pd >= 15 && r.n >= 5 && r.perDay <= .4 * med;
        if (hi || lo) add('volume', 'info', r.code, { me: r.me, strength: hi ? r.perDay / med : med / Math.max(r.perDay, .01), n: r.n,
          why: `<b>${n0(r.n)}</b> appointments over <b>${r.pd}</b> days present: <b>${r.perDay.toFixed(1)} a day</b>, against ${med.toFixed(1)} for the median ME based in ${esc(META.city)} (${cohort.length} MEs with ${MIN}+ appointments). ${hi ? 'More' : 'Fewer'} than ${hi ? 'twice' : '0.4 times'} the usual.`,
          cmp: { a: r.perDay, b: med, al: 'This ME', bl: 'Median', unit: 'a day' } });
      }
    }
    const order = k => KINDS.indexOf(k);
    items.sort((a, b) => (a.sev === b.sev ? 0 : a.sev === 'rev' ? -1 : 1) || order(a.kind) - order(b.kind) || b.strength - a.strength);
    for (const it of items) { const r = byMe.get(it.me); it.name = it.me < 0 ? plural(it.mes.size, 'ME') : r ? r.name : MES[it.me][1]; it.tl = r ? r.tl : ''; }
    return items;
  }
  // the records behind an item, in the current dates and scope
  function recFilter(it) {
    const me = it.me, tm = it.tme;
    const base = me < 0 ? (i => it.mes.has(AME[i])) : (i => AME[i] === me && (tm === undefined || ATM[i] === tm));
    switch (it.kind) {
      case 'noBooking': return i => base(i) && (AF[i] & F.noBooking);
      case 'dealBeforeBooked': return i => base(i) && (AF[i] & F.dealBeforeBooked);
      case 'naEarly': return i => base(i) && (AF[i] & F.naEarly);
      case 'naHigh': return i => base(i) && AO[i] === 3;
      case 'rlHigh': return i => base(i) && ARL[i] === 1;
      case 'naUp': return i => base(i) && AO[i] >= 3;
      case 'pending': return i => base(i) && (AF[i] & F.pending);
      case 'sameDay': return i => base(i) && (AF[i] & F.sameDay);
      default: return base;
    }
  }
  const REC_COLS = { noBooking: ['date', 'biz', 'tme', 'dealt', 'out'], dealBeforeBooked: ['date', 'biz', 'tme', 'dealt', 'booked', 'gapBk'], naEarly: ['date', 'biz', 'tme', 'slot', 'entered', 'early'],
    naHigh: ['date', 'biz', 'tme', 'slot', 'entered'], rlHigh: ['date', 'biz', 'tme', 'entered'], naUp: ['date', 'biz', 'tme', 'out'], pending: ['date', 'biz', 'tme', 'slot', 'since'],
    sameDay: ['date', 'biz', 'tme', 'out'], pairing: ['date', 'biz', 'booked', 'slot', 'out'], volume: ['date', 'biz', 'tme', 'out'] };
  const recWord = it => ({ noBooking: 'deals', dealBeforeBooked: 'deals', naEarly: 'appointments', naHigh: 'appointments', rlHigh: 'appointments', naUp: 'appointments', pending: 'appointments', sameDay: 'appointments', pairing: 'appointments', volume: 'appointments' }[it.kind]);

  /* ---------- tooltip ---------- */
  const TIP = $('#tip');
  function tip(html, ev) { TIP.innerHTML = html; TIP.hidden = false; const w = TIP.offsetWidth, h = TIP.offsetHeight; let x = ev.clientX + 14, y = ev.clientY + 14; if (x + w > innerWidth - 8) x = ev.clientX - w - 14; if (y + h > innerHeight - 8) y = ev.clientY - h - 14; TIP.style.left = x + 'px'; TIP.style.top = y + 'px'; }
  const untip = () => { TIP.hidden = true; };

  /* ---------- band: the dates in three steps (team view), or the checks (records to verify) ---------- */
  let CUR = null, PREV = null, BASE = null, CITY = null, MEROWS = [], ITEMS = [], PREV_IDS = new Set();
  const isDone = it => !!MARKS[it.id];
  let PREVROWS = new Map();
  // when the data was read, and how far the appointments and deals go
  function updLine() {
    const r = META.refreshed || '', ds = META.dealSrc || {};
    // days from the allocation API carry the system's Dealclosed records (103), so deals are covered to those days too
    const dl = [ds.recentTo, ds.dumpTo, ...(META.provisional || [])].filter(Boolean).sort().pop();
    const d = r ? fDate(new Date(r.slice(0, 10) + 'T00:00:00Z'), true) + (r.length > 11 ? ', ' + r.slice(11, 16) : '') : '';
    const at = fDate(dOf(LAST), true), dt = dl ? fDate(new Date(dl + 'T00:00:00Z'), true) : '';
    const t = d ? `Data updated ${d}` : '';   // the 'up to' dates were dropped (2026-10-14): the date picker already shows the last day
    const u = $('#updTop'); if (u) { u.textContent = t; u.title = t; }   // shown under the dashboard name; the copy below is for phones and screen readers
    return `<p class="upd">${esc(t)}</p>`;
  }
  const ARROW = `<div class="sarr" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 12h15M13 6l6 6-6 6"/></svg></div>`;
  // a team's chain from the top: [ROOT, manager, team leader]
  const chainOf = m => { const c = []; for (let g = 0; m >= 0 && g < 6; g++) { c.unshift(m); if (m === ROOT) break; m = UPN(m); } return c; };
  const ROLE = m => m === OUTN ? '' : DEPTH[m] === 1 ? 'manager' : DEPTH[m] === 2 ? 'team leader' : '';
  // the way back up above the heading: All Mumbai > manager > (this team, named in the heading)
  function crumbs() {
    if (!scoped()) return '';
    const c = chainOf(V.scope).slice(0, -1);
    return `<nav class="crumbs" aria-label="Teams above">${c.map(m => `<button type="button" class="lnk" data-scope="${m}" title="Show ${esc(m === ROOT ? `all of ${META.city}` : `${NNAME(m)}'s whole team`)}">${esc(m === ROOT ? `All ${META.city}` : NNAME(m))}</button><span aria-hidden="true">›</span>`).join('')}</nav>`;
  }
  const teamHead = () => scoped() ? `${esc(NNAME(V.scope))}${V.scope === OUTN ? '' : "'s team"} · ` : '';
  function renderBand() {
    renderPills();
    const R = CUR, P = PREV, a = att(R.o), pa = att(P.o), hasP = V.pa !== null && P.n > 0, vs = esc(prevName());
    if (V.view === 'checks') {
      const open = ITEMS.filter(it => !isDone(it)), rev = open.filter(it => it.sev === 'rev'), info = open.filter(it => it.sev === 'info');
      const mesRev = new Set(rev.map(it => it.me)).size, done = ITEMS.length - open.length;
      const byKind = KINDS.map(k => [k, rev.filter(it => it.kind === k).length]).filter(x => x[1]).sort((x, y) => y[1] - x[1]);
      let say = '';
      if (!ITEMS.length) say = `None of the ${KINDS.length} checks was raised in these dates.`;
      else if (!rev.length) say = done ? `All items to review are marked checked.${info.length ? ` ${plural(info.length, 'pattern')} for information remain.` : ''}` : `Nothing to review; ${plural(info.length, 'pattern')} for information.`;
      else say = `Most common: ${byKind.slice(0, 3).map(([k, c]) => `<b>${esc(CHECKS[k].short)}</b> (${c})`).join(', ')}.`;
      $('#hero').innerHTML = `<div class="when"><h1>Records to verify</h1><span>${esc(periodName())}</span></div>` + updLine() +
        `<div class="ov"><div class="ov-l"><div class="q"><span class="big tn">${n0(rev.length)}</span><span class="ql">${rev.length === 1 ? 'item' : 'items'} to review<small>${rev.length ? `across ${plural(mesRev, 'ME')}` : 'nothing open'}${info.length ? ` · ${n0(info.length)} more for information` : ''}${done ? ` · ${n0(done)} marked checked` : ''}</small></span></div><p class="say">${say}</p></div>` +
        `<div class="ov-note"><b>Before acting on any of these</b><p>These checks run automatically on the appointment and deal records and have not been confirmed yet. Each one is a prompt to look at the records, not a finding about anyone: a normal reason can sit behind any of them. Open the records, decide, then mark the item checked.</p><p class="lnks"><button type="button" class="lnk" data-go="how">How each check works</button></p></div></div>`;
      return;
    }
    const attP = pc(a, R.n), conv = cvr(R.dl, a, R.n), pAttP = pc(pa, P.n), pConv = cvr(P.dl, pa, P.n);
    const cA = pc(att(CITY.o), CITY.n), cC = cvr(CITY.dl, att(CITY.o), CITY.n);
    const dN = R.n - P.n, dA = Math.round((attP - pAttP) * 10) / 10, dC = Math.round((conv - pConv) * 10) / 10;
    const head = crumbs() + `<div class="when"><h1>${teamHead()}${esc(periodName())}</h1>${hasP ? `<span>compared with ${vs}</span>` : ''}</div>` + updLine() + (hasP ? lowNote() : '');
    // nothing in these dates (a Sunday, or a team with nothing that day): say so instead of zeros and -100% (2026-10-15)
    if (!R.n && !R.dl) {
      const o = V.from, sat = V.from === V.to && dOf(o).getUTCDay() === 0 && o > 0 && DAYN[o - 1] ? o - 1 : null;
      $('#hero').innerHTML = head + `<p class="noband">${sat !== null ? `No appointments on a Sunday: as in the Sales MIS, a Sunday appointment counts on the Saturday before. <button type="button" class="lnk on-navy" data-day="${sat}">Show ${esc(dayName(sat))}</button>` : `No appointments given or deals closed${scoped() ? ` in ${esc(teamName())}` : ''} in these dates.`}</p>`;
      return;
    }
    const ch = (d, txt) => hasP ? `<span class="chg ${d > 0 ? 'up' : d < 0 ? 'dn' : 'flat'}">${d > 0 ? '▲ ' : d < 0 ? '▼ ' : ''}${txt}</span>` : '';
    const chN = ch(dN, `${dN >= 0 ? '+' : '−'}${n0(Math.abs(dN))} (was ${n0(P.n)})`);
    const chA = ch(dA, `${dA > 0 ? 'up' : dA < 0 ? 'down' : 'same,'} ${Math.abs(dA).toFixed(1)} pts (was ${fP(pAttP)})`);
    const chC = ch(dC, `${dC > 0 ? 'up' : dC < 0 ? 'down' : 'same,'} ${Math.abs(dC).toFixed(1)} pts (was ${fP(pConv)})`);
    const cityR = x => scoped() ? ` <span class="chg flat">· ${esc(META.city)} ${fP(x)}</span>` : '';
    // MEs with appointments; MEs who only closed a deal (no appointment in the dates) are named apart, so the count
    // matches the Table's 'N MEs' (both together)
    const meN = `to ${plural(R.gMes.size, 'ME')}${R.mes.size > R.gMes.size ? ` (+${n0(R.mes.size - R.gMes.size)} with deals only)` : ''}`;
    const dOnly = R.mes.size > R.gMes.size ? `<span class="chg flat">${hasP ? ' · ' : ''}+${plural(R.mes.size - R.gMes.size, 'ME')} with deals only</span>` : '';
    if (V.view === 'table') {
      // the Table view: one line of totals so the table starts high on the screen (the funnel stays on Overview)
      const kp = (v, lab, sub, c) => `<div class="kp"><div class="kt"><span class="kv tn">${v}</span><span class="kl"><b>${lab}</b>${sub ? ` · ${sub}` : ''}</span></div>${c ? `<div class="kc">${c}</div>` : ''}</div>`;
      $('#hero').innerHTML = head + `<div class="kps">` +
        kp(n0(R.n), 'appointments given', `to ${plural(R.gMes.size, 'ME')}`, chN + dOnly) +
        kp(n0(a), 'attended', fP(attP), chA + cityR(cA)) +
        kp(n0(R.dl), 'deals closed', `${fP(conv)} ${CVOF()}`, chC + cityR(cC)) +
        kp(n0(R.n - a), 'not attended', fP(pc(R.n - a, R.n)), `<span class="chg flat">${n0(R.o[3])} Not Available · ${n0(R.o[4])} Pending · ${n0(R.o[5])} Not Visited</span>`) +
        `</div>`;
      return;
    }
    // Overview: the funnel (bar width = share of appointments given), each step with its own change (2026-10-15: the
    // side panel that repeated the rates is gone); deals closed and each not-attended reason open their records
    const frow = (w, cls, val, lab, sub, chg, open) => {
      const out = w < 17, bar = `<span class="fbar ${cls}" style="width:${Math.max(w, 1.5).toFixed(1)}%">${out ? '' : `<span class="tn">${val}</span>`}</span>${out ? `<span class="fout tn">${val}</span>` : ''}`;
      return `<div class="fr">${open ? `<button type="button" class="ftrack fgo" data-open="${open}" title="See the deals closed">${bar}</button>` : `<div class="ftrack">${bar}</div>`}` +
        `<div class="flab"><span class="l1"><b>${lab}</b> · ${sub}</span>${chg ? `<span class="l2">${chg}</span>` : ''}</div></div>`;
    };
    const why = k => R.o[k] ? `<button type="button" class="lnk on-navy" data-o="${k}" title="See these appointments">${n0(R.o[k])} ${OUT[k]}</button>` : `${n0(R.o[k])} ${OUT[k]}`;
    $('#hero').innerHTML = `<div class="fx"><div class="fmain">${head}<div class="fn">` +
      frow(100, 'g', n0(R.n), 'appointments given', `to ${plural(R.gMes.size, 'ME')}`, chN + dOnly) +
      frow(attP || 0, 'a', n0(a), 'attended', `${fP(attP)} of appointments given`, chA + cityR(cA)) +
      frow(Math.min(100, pc(R.dl, R.n) || 0), 'd', n0(R.dl), 'deals closed', `${fP(conv)} ${CVOF()} (conversion)`, chC + cityR(cC), 'deals') +
      `</div><p class="miss">Not attended: <b>${n0(R.n - a)}</b> (${fP(pc(R.n - a, R.n))}) · ${why(3)} · ${why(4)} · ${why(5)}</p></div>` +
      `<div class="fside">${movers()}${trend()}</div></div>`;
  }
  // a comparison is like for like only on usual days: name any low day (a holiday, a short day) in either set of dates
  function lowNote() {
    const list = (a, b) => { const o = []; if (a === null || a === undefined) return o; for (let d = a; d <= b; d++) if (isLow(d)) o.push(d); return o; };
    const cur = list(V.from, V.to), prv = list(V.pa, V.pb);
    if (!cur.length && !prv.length) return '';
    if (V.from !== V.to && cur.length === prv.length) return '';   // one in each: still like for like
    const say = ds => ds.map(d => `${esc(dayName(d))} (${n0(DAYN[d])} appointments given in ${esc(META.city)})`).join(', ');
    const parts = [];
    if (cur.length) parts.push(V.from === V.to ? `${say(cur)} was a low day` : `These dates include ${say(cur)}`);
    if (prv.length) parts.push(`${esc(prevName())} ${V.pa === V.pb ? 'was' : 'includes'} ${V.pa === V.pb ? `a low day (${n0(DAYN[V.pa])} appointments given)` : say(prv)}`);
    return `<p class="lownote">${parts.join('; ')}. A usual day has about ${n0(Math.round(USUAL / 10) * 10)}, so the changes are not like for like.</p>`;
  }
  // the band's 'Across managers' lines: plain facts about the level below the team shown (managers, team leaders or MEs)
  function movers() {
    const { SUB } = teamIndex(MEROWS);
    const kids = (KIDS[V.scope] || []).filter(k => k !== OUTN && SUB.has(k));
    const lvlName = kids.length ? (NDEP(kids[0]) === 1 ? 'managers' : 'team leaders') : 'MEs';
    const units = kids.length ? kids.map(k => ({ name: NNAME(k), s: sumRows(SUB.get(k)) })) : MEROWS.filter(r => r.n > 0).map(r => ({ name: r.name, s: r }));
    const minN = kids.length ? Math.max(MINR, 10) : MINR, ok = units.filter(u => u.s.n >= minN), out = [];
    const span = (key, lab) => {
      const v = ok.filter(u => u.s[key] !== null && u.s[key] !== undefined && isFinite(u.s[key])).sort((x, y) => x.s[key] - y.s[key]);
      if (v.length < 2 || Math.round(v[0].s[key]) === Math.round(v[v.length - 1].s[key])) return;
      out.push(`<p><span class="k">${lab}</span>lowest <b>${esc(v[0].name)}</b> ${fPi(v[0].s[key])} · highest <b>${esc(v[v.length - 1].name)}</b> ${fPi(v[v.length - 1].s[key])}</p>`);
    };
    span('attP', 'Attended %'); span('conv', 'Conversion');
    const na = units.filter(u => u.s.o[3] > 0).sort((x, y) => y.s.o[3] - x.s.o[3]);
    if (na.length > 1 && CUR.o[3] >= 5) out.push(`<p><span class="k">Not Available</span>most: <b>${esc(na[0].name)}</b>, ${n0(na[0].s.o[3])} of ${n0(CUR.o[3])}</p>`);
    if (!out.length) return '';
    return `<div class="mv"><h3>Across ${lvlName}${ok.length < units.length ? ` <small>with ${minN}+ appointments given</small>` : ''}</h3>${out.join('')}</div>`;
  }
  // the band's small trend: attended % and conversion over the last 4 weeks (each usual day) or 12 weeks (each week),
  // ending on the last day shown, for the team shown; the dates shown are dotted
  function trend() {
    const daily = V.to - V.from + 1 < 7, end = V.to, start = Math.max(0, daily ? end - 27 : end - 83);
    const nb = daily ? end - start + 1 : Math.ceil((end - start + 1) / 7), bk = d => daily ? d - start : Math.floor((d - start) / 7);
    const G = new Float64Array(nb), A = new Float64Array(nb), D = new Float64Array(nb);
    for (let i = 0; i < N; i++) { const d = AD[i]; if (d < start || d > end || !inScope(i)) continue; const b = bk(d); G[b]++; if (AO[i] <= 2) A[b]++; }
    for (let j = 0; j < DLN; j++) { const d = DLD[j]; if (d < start || d > end || !SMASK[DNODE[j]]) continue; D[bk(d)] += DLW[j]; }
    const pts = [];
    for (let b = 0; b < nb; b++) {
      const d0 = daily ? start + b : start + b * 7, d1 = daily ? d0 : Math.min(end, d0 + 6);
      if ((daily && (!DAYN[d0] || isLow(d0))) || G[b] < 5) continue;
      pts.push({ b, d0, d1, a: A[b] / G[b] * 100, c: (CB() ? D[b] / G[b] : A[b] ? D[b] / A[b] : 0) * 100, sel: d1 >= V.from && d0 <= V.to });
    }
    if (pts.length < 3) return '';
    const W = 300, H = 46, x = b => 4 + b / Math.max(1, nb - 1) * (W - 8), y = v => H - 4 - Math.max(0, Math.min(100, v)) / 100 * (H - 8);
    const path = k => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.b).toFixed(1)},${y(p[k]).toFixed(1)}`).join('');
    const dots = pts.filter(p => p.sel).map(p => `<path class="da" d="M${x(p.b).toFixed(1)},${y(p.a).toFixed(1)}h0"/><path class="dc" d="M${x(p.b).toFixed(1)},${y(p.c).toFixed(1)}h0"/>`).join('');
    const tips = pts.map(p => `<rect x="${(x(p.b) - W / nb / 2).toFixed(1)}" y="0" width="${(W / nb).toFixed(1)}" height="${H}" fill="transparent"><title>${esc(daily ? dayName(p.d0) : fRange(p.d0, p.d1))}: attended ${Math.round(p.a)}%, conversion ${Math.round(p.c)}%</title></rect>`).join('');
    return `<div class="trd"><h3>${daily ? 'Last 4 weeks, each usual day' : 'Last 12 weeks, each week'}</h3>` +
      `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Attended % and conversion, ${daily ? 'each day of the last 4 weeks' : 'each week of the last 12 weeks'}"><path class="g50" d="M0,${y(50).toFixed(1)}H${W}"/><path class="la" d="${path('a')}"/><path class="lc" d="${path('c')}"/>${dots}${tips}</svg>` +
      `<p class="tkey"><span><i class="a"></i>Attended %</span><span><i class="c"></i>Conversion</span><span title="Point at a ${daily ? 'day' : 'week'} for its numbers">dashed = 50% · dots = the dates shown</span></p></div>`;
  }
  $('#hero').addEventListener('click', ev => {
    const s = ev.target.closest('[data-scope]'); if (s) return setScope(+s.dataset.scope);
    const o = ev.target.closest('[data-o]'); if (o) return openList({ o: +o.dataset.o });
    if (ev.target.closest('[data-open="deals"]')) return openDeals();
    const dy = ev.target.closest('[data-day]'); if (dy) { const t = +dy.dataset.day, p = PRESETS.find(x => x.a === t && x.b === t); if (p) setPreset(p.k); else setRange(t, t); return render(true); }
    const g = ev.target.closest('[data-go="how"]'); if (g) return $('#how').scrollIntoView({ block: 'start' });
    const w = ev.target.closest('[data-view]'); if (w && w.dataset.view !== V.view) setView(w.dataset.view);
  });
  function showViews() {
    $('#vTeam').hidden = V.view !== 'team'; $('#vTable').hidden = V.view !== 'table'; $('#vChecks').hidden = V.view !== 'checks';
    $('#toChecks').closest('p').hidden = V.view === 'checks';
  }
  function setView(v) {
    V.view = v === 'checks' || v === 'table' ? v : 'team';
    closeCol(); showViews(); renderBand(); renderLadder(); renderList(); renderX(); writeHash(); scrollTo(0, 0);
  }


  /* ---------- review queue ---------- */
  const ICON = {
    rev: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1.8l6.6 11.6H1.4z" fill="currentColor"/><path d="M8 6v3.6M8 11.3v.1" stroke="#FFF4DB" stroke-width="1.6" stroke-linecap="round"/></svg>',
    info: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.6" fill="currentColor"/><path d="M8 7.2v4M8 4.9v.1" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/></svg>',
    done: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3.2 8.4l3 3 6.6-6.8" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>',
  };
  const ITEM_TEAMS = new Map();
  function itemTeams(it) {
    if (ITEM_TEAMS.has(it.id)) return ITEM_TEAMS.get(it.id);
    const f = recFilter(it), s = new Set();
    for (let i = 0; i < N; i++) { const d = AD[i]; if (d < V.from || d > V.to || !inScope(i)) continue; if (f(i)) s.add(ATT[i]); }
    ITEM_TEAMS.set(it.id, s); return s;
  }
  function cmpBars(c) {
    if (!c || c.a === null || c.b === null || !isFinite(c.a) || !isFinite(c.b)) return '';
    const mx = Math.max(c.a, c.b) * 1.08 || 1, f = v => c.unit ? `${v.toFixed(1)} ${c.unit}` : fP(v);
    return `<div class="cmp2" role="img" aria-label="${esc(c.al)} ${f(c.a)}, ${esc(c.bl)} ${f(c.b)}"><div class="r"><span class="l">${esc(c.al)}</span><span class="tr"><i class="me" style="width:${(c.a / mx * 100).toFixed(1)}%"></i></span><b class="tn">${f(c.a)}</b></div>` +
      `<div class="r"><span class="l">${esc(c.bl)}</span><span class="tr"><i style="width:${(c.b / mx * 100).toFixed(1)}%"></i></span><span class="tn">${f(c.b)}</span></div></div>`;
  }
  const apptCount = it => { const f = recFilter(it); let c = 0; for (let i = 0; i < N; i++) { const d = AD[i]; if (d >= V.from && d <= V.to && inScope(i) && f(i)) c++; } return c; };
  function qFiltered() {
    const q = $('#qSearch').value.trim().toLowerCase();
    return ITEMS.filter(it => (V.qKind === 'all' || it.kind === V.qKind) && (V.qSev === 'all' || it.sev === V.qSev) &&
      (V.qStat === 'all' || (V.qStat === 'done') === isDone(it)) && (V.qTeam < 0 || itemTeams(it).has(V.qTeam)) &&
      (!q || (it.me < 0 ? [...it.mes].map(m => MES[m][1] + ' ' + MES[m][0]).join(' ') : it.name + ' ' + it.tl + ' ' + (it.tme !== undefined ? TMES[it.tme][1] : '') + ' ' + MES[it.me][0]).toLowerCase().includes(q)));
  }
  function renderQueue() {
    const kinds = KINDS.map(k => [k, ITEMS.filter(it => it.kind === k).length]);
    $('#qKind').innerHTML = `<option value="all">All checks (${n0(ITEMS.length)})</option>` + kinds.map(([k, c]) => `<option value="${k}" ${V.qKind === k ? 'selected' : ''}${c ? '' : ' disabled'}>${esc(CHECKS[k].label)} (${c})</option>`).join('');
    if (V.qKind !== 'all' && !kinds.find(x => x[0] === V.qKind && x[1])) { V.qKind = 'all'; $('#qKind').value = 'all'; }
    const teamsUsed = new Set(); for (let t = 0; t < NT; t++) if (CUR.tO.subarray(t * 6, t * 6 + 6).some(x => x)) teamsUsed.add(t);
    $('#qTeam').innerHTML = `<option value="-1">All TME teams</option>` + [...teamsUsed].map(t => `<option value="${t}" ${V.qTeam === t ? 'selected' : ''}>${esc(TEAMS[t])}</option>`).join('');
    document.querySelectorAll('#qSev button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.qSev)));
    document.querySelectorAll('#qStat button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.qStat)));
    const list = qFiltered(), show = V.qAll ? list : list.slice(0, 12);
    const filtered = V.qKind !== 'all' || V.qSev !== 'all' || V.qStat !== 'open' || V.qTeam >= 0 || $('#qSearch').value.trim();
    $('#qSum').innerHTML = ITEMS.length ? `${filtered ? `Showing <b>${n0(list.length)}</b> of ${n0(ITEMS.length)} items` : `<b>${n0(list.length)}</b> open ${list.length === 1 ? 'item' : 'items'}`}, ${esc(fRange(V.from, V.to))}. Review first, then information; strongest first within each check.${V.to - V.from > 45 ? ' The limits are set for about a month: longer dates add up more records, so more cross them.' : ''}` : '';
    if (!ITEMS.length) { $('#items').innerHTML = `<li class="empty">No check was raised for ${esc(scopeName())} in these dates. The ${KINDS.length} checks are explained below.</li>`; return; }
    if (!list.length) { $('#items').innerHTML = `<li class="empty">No items match these filters.${V.qStat === 'open' && ITEMS.some(isDone) ? ' Items you marked checked are under "Checked".' : ''}</li>`; return; }
    $('#items').innerHTML = show.map(it => {
      const done = isDone(it), r = MEROWS.find(x => x.me === it.me);
      const who = it.me < 0 ? `<span class="mu">${esc(it.name)}: ${[...it.mes].slice(0, 6).map(m => esc(MES[m][1])).join(', ')}${it.mes.size > 6 ? ` and ${n0(it.mes.size - 6)} more` : ''}</span>` : `<button type="button" class="lnk" data-me="${it.me}">${esc(it.name)}</button>${it.tme !== undefined ? ` <span class="mu">from TME</span> ${esc(TMES[it.tme][1])}` : ''}` +
        `<span class="mu">${it.tl ? ` · team leader ${esc(it.tl)}` : ''}${r && (r.des || r.city) ? ` · ${esc([r.des, r.city].filter(Boolean).join(', '))}` : ''}</span>`;
      const nRec = it.me < 0 ? apptCount(it) : it.n;
      const again = PREV_IDS.has(it.kind + '|' + it.subj) ? `<span class="again" title="The same check was raised for the same ${it.tme !== undefined ? 'pair' : 'ME'} in ${esc(prevName())}">Also raised in ${esc(prevName())}</span>` : '';
      return `<li class="item ${it.sev}${done ? ' done' : ''}" data-id="${esc(it.id)}">` +
        `<div class="sev"><span class="tag ${done ? 'ok' : it.sev}">${done ? ICON.done : ICON[it.sev]}${done ? 'Checked' : it.sev === 'rev' ? 'Review' : 'Information'}</span></div>` +
        `<div class="body"><h3>${esc(CHECKS[it.kind].label)}</h3><p class="who">${who}</p><p class="why">${it.why}</p>${again}</div>` +
        `<div class="viz">${cmpBars(it.cmp)}</div>` +
        `<div class="act"><button type="button" class="btn rec" data-act="rec">See ${plural(nRec, recWord(it).replace(/s$/, ''), recWord(it))}</button>` +
        `<button type="button" class="btn chk" data-act="chk" aria-pressed="${done}">${done ? ICON.done + 'Checked' : 'Mark checked'}</button>` +
        `<button type="button" class="howq" data-act="how" aria-label="How this check works">How is this raised?</button></div></li>`;
    }).join('') + (list.length > 12 ? `<li class="more"><button type="button" class="btn" id="qMore">${V.qAll ? 'Show the first 12' : `Show all ${n0(list.length)}`}</button></li>` : '');
  }
  $('#items').addEventListener('click', ev => {
    if (ev.target.closest('#qMore')) { V.qAll = !V.qAll; return renderQueue(); }
    const li = ev.target.closest('li.item'); if (!li) return;
    const it = ITEMS.find(x => x.id === li.dataset.id); if (!it) return;
    const me = ev.target.closest('.lnk[data-me]'); if (me) return openMe(+me.dataset.me);
    const b = ev.target.closest('[data-act]'); if (!b) return;
    if (b.dataset.act === 'rec') openRecords(it);
    else if (b.dataset.act === 'how') { const row = document.querySelector(`#howTbl tr[data-k="${it.kind}"]`); if (row) { row.scrollIntoView({ block: 'center' }); row.classList.add('hl'); setTimeout(() => row.classList.remove('hl'), 2500); } }
    else if (b.dataset.act === 'chk') { if (MARKS[it.id]) delete MARKS[it.id]; else MARKS[it.id] = new Date().toISOString().slice(0, 10); saveMarks(); renderBand(); renderQueue(); renderList(); }
  });
  $('#qKind').addEventListener('change', e => { V.qKind = e.target.value; V.qAll = false; renderQueue(); });
  $('#qTeam').addEventListener('change', e => { V.qTeam = +e.target.value; V.qAll = false; renderQueue(); });
  $('#qSev').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) { V.qSev = b.dataset.v; V.qAll = false; renderQueue(); } });
  $('#qStat').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) { V.qStat = b.dataset.v; V.qAll = false; renderQueue(); } });
  $('#qSearch').addEventListener('input', () => { V.qAll = false; renderQueue(); });
  $('#qCsv').addEventListener('click', () => {
    const strip = h => String(h).replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"');
    download(`ME_review_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['Level', 'Check', 'ME code', 'ME', 'Team leader', 'TME', 'What was seen', 'Records', 'Status'],
        ...qFiltered().map(it => [it.sev === 'rev' ? 'Review' : 'Information', CHECKS[it.kind].label, it.me < 0 ? '' : MES[it.me][0], it.me < 0 ? [...it.mes].map(m => MES[m][1]).join('; ') : it.name, it.tl, it.tme !== undefined ? TMES[it.tme][1] : '', strip(it.why), it.n, isDone(it) ? `Checked ${MARKS[it.id]}` : 'Open'])]);
  });
  // Excel-safe CSV: UTF-8 with BOM, CRLF rows; a code with leading zeros stays text (="000140"); text that Excel would
  // run as a formula (= + @ or a non-number starting with -) gets a leading apostrophe; quotes, commas and line breaks quoted
  function csvCell(x) {
    if (x === null || x === undefined) return '';
    if (typeof x === 'number') return isFinite(x) ? String(x) : '';
    let v = String(x);
    if (/^0\d+$/.test(v)) return `="${v}"`;
    if (/^[=+@]/.test(v) || (/^-/.test(v) && !/^-\d+(\.\d+)?$/.test(v))) v = "'" + v;
    return /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  }
  const fileTag = () => scoped() ? '_' + NNAME(V.scope).replace(/\W+/g, '_') : '';
  function download(name, lines) {
    const csv = '﻿' + lines.map(l => l.map(csvCell).join(',')).join('\r\n');
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    a.download = name; document.body.append(a); a.click(); a.remove();
  }

  /* ---------- TME teams in groups, set under the settings icon for the whole dashboard (2026-10-16) ----------
     Super Cat; Hot Data and Online apart or together ('Hot Data + Online'); Other teams; the expiry team
     (Revival (Expiry)) on its own (default, the ME Head asked for it) or inside Other teams. Other teams always last.
     Each group keeps its colour wherever it sits: the dataviz palette's slots (Expiry violet, Hot Data + Online
     magenta), checked with its validator in every order the settings make: no two neighbours too close, also for
     colour-blind readers */
  const EXP = 'Revival (Expiry)';
  const GDEF = {
    'Super Cat': { id: 'sc', c: '#2a78d6', ink: '#fff', tint: 0 }, 'Hot Data': { id: 'hd', c: '#eb6834', ink: '#fff', tint: 1 },
    'Online': { id: 'on', c: '#1baf7a', ink: '#14213D', tint: 2 }, 'Hot Data + Online': { id: 'ho', c: '#e87ba4', ink: '#14213D', tint: 4 },
    'Other teams': { id: 'ot', c: '#eda100', ink: '#14213D', tint: 3 }, [EXP]: { id: 'ex', c: '#4a3aa7', ink: '#fff', tint: 5 },
  };
  let XMERGE = false, XEXP = true;   // Hot Data and Online together; the expiry team on its own
  try { XMERGE = localStorage.getItem('jd-me-review-xmerge-v1') === '1'; const e = localStorage.getItem('jd-me-review-expiry-v1'); if (e !== null) XEXP = e === '1'; } catch (e) { /* defaults */ }
  let GROUPS, NG, GSHORT, GROUP_OF;
  function setGroups() {
    GROUPS = ['Super Cat', ...(XMERGE ? ['Hot Data + Online'] : ['Hot Data', 'Online']), ...(XEXP ? [EXP] : []), 'Other teams'];
    NG = GROUPS.length;
    GSHORT = GROUPS.map(l => l === 'Other teams' ? 'Others' : l === EXP ? 'Expiry' : l);
    const at = n => GROUPS.indexOf(n);
    GROUP_OF = TEAMS.map(t => t === 'Super Cat' ? 0 : t === 'Hot Data' || t === 'Online' ? at(XMERGE ? 'Hot Data + Online' : t) : t === EXP && XEXP ? at(EXP) : at('Other teams'));
    const st = document.documentElement.style;   // the page's group colours follow the groups: --t0.. and their text colour --t0i..
    GROUPS.forEach((g, i) => { st.setProperty(`--t${i}`, GDEF[g].c); st.setProperty(`--t${i}i`, GDEF[g].ink); });
  }
  setGroups();
  const G_MIN = 5, G_GAP_MIN = 10, FAV_MIN_DEALS = 10;   // 'Favours one team' needs this many deals: shares of a few deals swing   // shares shown from 5 given; a team counts towards 'uneven' from 10
  const z3 = () => GROUPS.map(() => [0, 0, 0]);   // given, attended, deals per group
  function groupsOf(R, me) { const g = z3(); for (let t = 0; t < NT; t++) { const k = (me * NT + t) * 3, x = g[GROUP_OF[t]]; x[0] += R.meT[k]; x[1] += R.meT[k + 1]; x[2] += R.meT[k + 2]; } return g; }
  function cityGroups(R) { const g = z3(); for (let t = 0; t < NT; t++) { const o = R.tO.subarray(t * 6, t * 6 + 6), x = g[GROUP_OF[t]]; x[0] += o.reduce((s2, v) => s2 + v, 0); x[1] += att(o); x[2] += R.tDl[t]; } return g; }
  // uneven: the ME's highest minus lowest attended share across the groups with G_GAP_MIN+ given, beyond Mumbai's for the same two
  function gapOf(g, city) {
    const ok = GROUPS.map((_, i) => i).filter(i => g[i][0] >= G_GAP_MIN); if (ok.length < 2) return null;
    const p = i => g[i][1] / g[i][0] * 100, c = i => city[i][0] ? city[i][1] / city[i][0] * 100 : 0;
    let hi = ok[0], lo = ok[0]; for (const i of ok) { if (p(i) > p(hi)) hi = i; if (p(i) < p(lo)) lo = i; }
    return { hi, lo, ph: p(hi), pl: p(lo), ch: c(hi), cl: c(lo), extra: (p(hi) - p(lo)) - (c(hi) - c(lo)) };
  }
  const pct0 = (k, n) => n ? Math.round(k / n * 100) + '%' : '—';
  function teamRows(R) { return TEAMS.map((name, t) => { const o = Array.from(R.tO.subarray(t * 6, t * 6 + 6)), n = o.reduce((s, x) => s + x, 0), a = att(o), d = R.tDl[t]; return { t, name, o, n, a, d, attP: pc(a, n), conv: cvr(d, a, n) }; }).filter(x => x.n > 0 || x.d > 0).sort((x, y) => y.n - x.n || y.d - x.d); }
  // the bar: full = given; blue = attended; green = deals (both as parts of given)
  const bar = x => x[0] ? `<span class="mbar" aria-hidden="true"><i class="a" style="width:${(x[1] / x[0] * 100).toFixed(1)}%"></i><i class="d" style="width:${(x[2] / x[0] * 100).toFixed(1)}%"></i></span>` : `<span class="mbar empty" aria-hidden="true"></span>`;
  // one row in a drawer: label | bar | Given | Attended n % | Deals n % (of attended)
  function mrow(label, x, cls2) {
    const [g, a, d] = x, few = g > 0 && g < G_MIN, p = (k, n) => n && !few ? ` <em>${pct0(k, n)}</em>` : '', dOnly = !g && d > 0;   // dOnly: deals with no appointment behind them
    return `<div class="mrow${few ? ' few' : ''}${g || dOnly ? '' : ' none'}${cls2 ? ' ' + cls2 : ''}"><span class="ml">${label}</span>${bar(x)}` +
      `<span class="mn">${g ? n0(g) : '—'}</span><span class="mn">${g ? n0(a) + p(a, g) : dOnly ? '—' : ''}</span><span class="mn">${g ? n0(d) + p(d, CB() ? g : a) : dOnly ? n0(d) : ''}</span></div>`;
  }
  const MHEAD = `<div class="mrow mh"><span class="ml">TME team</span><span></span><span class="mn"><span class="lg">Appointments given</span><span class="sh">Given</span></span><span class="mn">Attended</span><span class="mn">Deals closed</span></div>`;

  /* ---------- where the appointments came from: three tiles ---------- */
  function renderTeams() {
    // one card per TME team with its own small funnel, the view the ME Head knows (kept 2026-10-15, made shorter): three
    // labelled bars (bar width = share of the team's appointments given), then attended % and conversion; rates grey
    // under the page's minimum
    const R = CUR, city = cityGroups(R), cg = cityGroups(CITY);
    $('#teams').style.gridTemplateColumns = `repeat(${NG}, minmax(0, 1fr))`;
    const lv = (w, cls, txt) => `<span class="ml ${cls}"><i style="width:${Math.max(w, 1.5).toFixed(1)}%">${w >= 42 ? txt : ''}</i>${w < 42 ? `<em>${txt}</em>` : ''}</span>`;
    $('#teams').innerHTML = GROUPS.map((l, i) => {
      const [g, a, d] = city[i], few = g < MINR;
      return `<button type="button" class="tile tf" data-g="${i}"><span class="tt">${esc(l)}<small>${pct0(g, R.n)} of all</small></span>` +
        `<span class="mini">${lv(100, 'g', `${plural(g, 'appointment')} given`)}${lv(pc(a, g) || 0, 'a', `${n0(a)} attended`)}${lv(Math.min(100, pc(d, g) || 0), 'd', `${plural(d, 'deal')} closed`)}</span>` +
        `<span class="tline${few ? ' few' : ''}"${few ? ' title="Few appointments: these rates swing a lot"' : ''}><b>${pct0(a, g)}</b> attended · <b>${pct0(d, CB() ? g : a)}</b> conversion</span>` +
        (scoped() ? `<span class="tline tc">${esc(META.city)}: ${pct0(cg[i][1], cg[i][0])} attended · ${pct0(cg[i][2], CB() ? cg[i][0] : cg[i][1])} conversion</span>` : '') + `</button>`;
    }).join('');
  }
  $('#teams').addEventListener('click', ev => { const b = ev.target.closest('.tile[data-g]'); if (b) openGroup(+b.dataset.g); });

  /* ---------- 'Your team' paging (2026-10-16): the Table's pager - previous / next, 'Page 1 of 8', rows per page 25 / 50
     / 100 / All (remembered: jd-me-review-ovpagesize) - for the ladder, the ME funnel list and Team shares ---------- */
  let OPS = 25, OPG = 0;
  try { const v = localStorage.getItem('jd-me-review-ovpagesize'); if (v !== null && [0, 25, 50, 100].includes(+v)) OPS = +v; } catch (e) { /* default */ }
  function ovPage(list) {
    const pages = OPS ? Math.max(1, Math.ceil(list.length / OPS)) : 1;
    OPG = Math.max(0, Math.min(OPG, pages - 1));
    return { rows: OPS ? list.slice(OPG * OPS, OPG * OPS + OPS) : list, pages };
  }
  function ovPager(n, pages, what) {
    if (!n) return '';
    const from = OPG * (OPS || n) + 1, to = OPS ? Math.min(n, (OPG + 1) * OPS) : n;
    return `<div class="xpg ovpg"><span class="pgi">${n0(from)}–${n0(to)} of ${n0(n)} ${what}</span>` +
      (pages > 1 ? `<span class="pgb"><button type="button" class="btn" data-ovpg="-1"${OPG ? '' : ' disabled'} aria-label="Previous page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg></button><span>Page ${OPG + 1} of ${pages}</span><button type="button" class="btn" data-ovpg="1"${OPG < pages - 1 ? '' : ' disabled'} aria-label="Next page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg></button></span>` : '') +
      `<label class="pgs">Rows per page <select class="ovps">${[25, 50, 100, 0].map(k => `<option value="${k}"${k === OPS ? ' selected' : ''}>${k || 'All'}</option>`).join('')}</select></label></div>`;
  }
  const ovRedraw = () => { renderLadder(); renderList(); const c = $('.tmcard'); if (c.getBoundingClientRect().top < 0) c.scrollIntoView({ block: 'start' }); };
  $('.tmcard').addEventListener('click', ev => { const b = ev.target.closest('[data-ovpg]'); if (!b || b.disabled) return; OPG += +b.dataset.ovpg; ovRedraw(); });
  $('.tmcard').addEventListener('change', ev => {
    if (!ev.target.classList.contains('ovps')) return;
    OPS = +ev.target.value; OPG = 0; try { localStorage.setItem('jd-me-review-ovpagesize', String(OPS)); } catch (e) { /* not remembered */ }
    ovRedraw();
  });

  /* ---------- your MEs: one row each, one way to order them ---------- */
  const SORTS = {
    n: { label: 'Most appointments given', f: (a, b) => b.r.n - a.r.n },
    att: { label: 'Lowest attended %', f: (a, b) => (a.r.attP ?? 101) - (b.r.attP ?? 101) || b.r.n - a.r.n },
    deals: { label: 'Most deals closed', f: (a, b) => b.r.deals - a.r.deals || b.r.n - a.r.n },
    uneven: { label: 'Uneven attended across teams', f: (a, b) => (b.gap ? b.gap.extra : -1e9) - (a.gap ? a.gap.extra : -1e9) || b.r.n - a.r.n },
    one: { label: 'Appointments given mostly from one team', f: (a, b) => b.share - a.share || b.r.n - a.r.n },
  };
  let LROWS = [];
  function meLines(R, city, r, gIn) {
    const g = gIn || groupsOf(R, r.me); let top = 0; for (let i = 1; i < NG; i++) if (g[i][0] > g[top][0]) top = i;
    // favours: the team whose share rises most from the ME's appointments to their deals, beyond the same rise across
    // the city (a team needs G_GAP_MIN+ appointments); lift in share points
    const cn = city.reduce((t, x) => t + x[0], 0), cd = city.reduce((t, x) => t + x[2], 0);
    let fav = null;
    if (r.deals >= FAV_MIN_DEALS) for (let i = 0; i < NG; i++) {
      if (g[i][0] < G_GAP_MIN) continue;
      const s0 = g[i][0] / r.n * 100, s2 = g[i][2] / r.deals * 100, c0 = cn ? city[i][0] / cn * 100 : 0, c2 = cd ? city[i][2] / cd * 100 : 0;
      const lift = (s2 - s0) - (c2 - c0);
      if (!fav || lift > fav.lift) fav = { i, s0, s2, c0, c2, lift };
    }
    return { r, g, gap: gapOf(g, city), fav, top, share: r.n ? g[top][0] / r.n : 0 };
  }
  // Team shares at the Managers / Team leaders level (2026-10-15): the teams at that level under the team shown, each with
  // all its MEs; a manager's own and direct MEs (no team leader) and the MEs outside the ME head's line get lines of their
  // own, so the lines cover everyone
  function teamUnits() {
    const { SUB, DIR } = teamIndex(MEROWS), L = lvl(), out = [];
    const kidsOf = m => KIDS[m].filter(k => k !== OUTN && SUB.has(k));
    const direct = m => { const d = DIR.get(m); if (d && d.length) out.push({ k: m, name: NNAME(m), rows: d, tag: 'own & direct MEs', sub: `${m === ROOT ? 'ME head' : 'Manager'}: own and direct MEs · ${plural(d.length, 'ME')}` }); };
    const walk = m => {
      for (const k of kidsOf(m)) {
        if (NDEP(k) >= L) { const nT = kidsOf(k).length; out.push({ k, name: NNAME(k), rows: SUB.get(k), sub: `${ROLE(k) === 'manager' ? 'Manager' : `Team leader${UPN(k) === V.scope ? '' : ` · ${NNAME(UPN(k))}`}`}${nT ? ` · ${plural(nT, 'team leader')}` : ''} · ${plural(SUB.get(k).length, 'ME')}` }); }
        else { walk(k); direct(k); }
      }
    };
    walk(V.scope); direct(V.scope);
    if (V.scope === ROOT && SUB.has(OUTN)) out.push({ k: OUTN, name: OUT_NAME, rows: SUB.get(OUTN), sub: `${plural(SUB.get(OUTN).length, 'ME')} · their HR reporting line ends elsewhere` });
    return out;
  }
  function renderList() {
    if (meStyle() === 'bars') return;   // the Funnel view is drawn by renderLadder
    const R = CUR, city = cityGroups(CITY), q = $('#meSearch').value.trim().toLowerCase(), teams = OVMODE === 'lad';
    document.querySelectorAll('#sortBy button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.sortBy)));
    const hit = r => (r.name + ' ' + r.tl + ' ' + r.mgr + ' ' + r.code).toLowerCase().includes(q);
    let list, total;
    if (teams) {   // one line per team: its MEs added up, their TME-team shares too
      const GM = new Map(MEROWS.map(r => [r.me, groupsOf(R, r.me)])), units = teamUnits();
      total = units.length;
      list = units.filter(u => !q || u.name.toLowerCase().includes(q) || u.rows.some(hit)).map(u => {
        const r = Object.assign(sumRows(u.rows), { name: u.name, unit: u }), g = z3();
        for (const x of u.rows) GM.get(x.me).forEach((v, i) => { for (let j = 0; j < 3; j++) g[i][j] += v[j]; });
        return meLines(R, city, r, g);
      });
    } else {
      total = MEROWS.length;
      list = MEROWS.filter(r => !q || hit(r)).map(r => meLines(R, city, r));
    }
    list.sort(SORTS[V.sortBy].f);
    LROWS = list;
    const pg = ovPage(list), show = pg.rows, cityShare = i => pct0(city[i][0], CITY.n), word = teams ? 'team' : 'ME';
    $('#tcSub').innerHTML = (teams ? `One line per ${lvl() === 1 ? "manager's" : "team leader's"} team, split by TME team`
      : `${plural(total, 'ME')} with appointments or deals closed, split by TME team`) + (q ? ` · ${n0(list.length)} matching "${esc(q)}"` : '');
    const why = x => {
      if (V.sortBy === 'uneven' && x.gap) return `<span class="why">Attended <b>${esc(GROUPS[x.gap.hi])}</b> ${Math.round(x.gap.ph)}%, <b>${esc(GROUPS[x.gap.lo])}</b> ${Math.round(x.gap.pl)}% · ${esc(META.city)}: ${Math.round(x.gap.ch)}% and ${Math.round(x.gap.cl)}%</span>`;
      if (V.sortBy === 'one') return `<span class="why">${Math.round(x.share * 100)}% of their appointments from ${esc(GROUPS[x.top])} · ${esc(META.city)}: ${cityShare(x.top)}</span>`;
      return '';
    };
    // share ribbons (2026-10-12, option C2): three bars per line, each 100% -- the TME-team shares of its appointments, of
    // its attended and of its deals -- joined by ribbons. A band that widens on the way down is a TME team converted
    // better than the others; the reading line sets it against the same shares for the whole city.
    const LV = ['appointments given', 'attended', 'deals closed'];
    const shares = x => [x.r.n, x.r.att, x.r.deals].map((t, k) => x.g.map(v => t ? v[k] / t * 100 : 0));
    const ribbon = x => {
      const S = shares(x), tot = [x.r.n, x.r.att, x.r.deals];
      const lefts = S.map(row => { let l = 0; return row.map(w => { const o = l; l += w; return o; }); });
      // the bands are thin until the line is pointed at or focused, then full height with the numbers (2026-10-16)
      const bar = k => tot[k] ? x.g.map((v, i) => S[k][i] ? `<span class="sg t${i}" style="left:${lefts[k][i].toFixed(2)}%;width:${S[k][i].toFixed(2)}%" title="${esc(`${GROUPS[i]}: ${n0(v[k])} of ${n0(tot[k])} ${LV[k]} (${Math.round(S[k][i])}%)`)}">${S[k][i] >= 12 ? `<b>${Math.round(S[k][i])}%</b>` : ''}</span>` : '').join('') : `<span class="sg none">no ${LV[k]}</span>`;
      // ribbons: one shape behind the three bars joining their middles, so they stay attached whether the bars are thin or full
      const Y = [4.5, 19.5, 34.5];   // the middle of each bar: three 9 px rows, 6 px apart
      const band = k => tot[k] && tot[k + 1] ? x.g.map((v, i) => S[k][i] || S[k + 1][i] ?
        `<path class="t${i}" d="M${lefts[k][i]},${Y[k]} L${lefts[k][i] + S[k][i]},${Y[k]} L${lefts[k + 1][i] + S[k + 1][i]},${Y[k + 1]} L${lefts[k + 1][i]},${Y[k + 1]} Z"/>` : '').join('') : '';
      return `<span class="mc rib" aria-label="${esc(GROUPS.map((l, i) => `${l} ${Math.round(S[0][i])}% of appointments given, ${Math.round(S[2][i])}% of deals closed`).join('; '))}">` +
        `<svg class="rgx" viewBox="0 0 100 39" preserveAspectRatio="none" aria-hidden="true">${band(0)}${band(1)}</svg>` +
        `<span class="rl" title="Appointments given">Given</span><span class="rb">${bar(0)}</span>` +
        `<span class="rl" title="Attended">Attd</span><span class="rb">${bar(1)}</span>` +
        `<span class="rl" title="Deals closed">Deals</span><span class="rb">${bar(2)}</span></span>`;
    };
    const cityX = { r: { n: CITY.n, att: att(CITY.o), deals: CITY.dl }, g: city }, CS = shares(cityX);
    // the reading, one line: the TME team whose share rises most from appointments given to deals closed (beyond the
    // same rise in the city), else where most appointments came from
    const reading = (x, ref) => {
      const S = shares(x);
      if (ref) {
        const d = GROUPS.map((_, i) => S[2][i] - S[0][i]), up = d.indexOf(Math.max(...d));
        return `<span class="mc rd"><span><b>${esc(GROUPS[up])}</b> brings <b>${Math.round(S[2][up])}%</b> of deals</span><span class="mu">from ${Math.round(S[0][up])}% of given · the normal</span></span>`;
      }
      const fav = x.fav && x.fav.lift >= 2 ? x.fav.i : -1;   // the same team the 'Favours one team' order uses
      if (fav >= 0) return `<span class="mc rd" title="${esc(`${META.city}: ${GROUPS[fav]} ${Math.round(CS[0][fav])}% of given → ${Math.round(CS[2][fav])}% of deals`)}"><span>Leans to <b>${esc(GROUPS[fav])}</b></span><span class="mu">${Math.round(S[0][fav])}% of given → <b>${Math.round(S[2][fav])}%</b> of deals</span></span>`;
      // no lean: say why -- too few deals, a rise only in a TME team with too few appointments, or none
      const rise = GROUPS.some((_, i) => x.g[i][0] && (S[2][i] - S[0][i]) - (CS[2][i] - CS[0][i]) >= 2);
      const why = !x.r.deals ? 'no deals closed yet' : x.r.deals < FAV_MIN_DEALS ? 'too few deals to compare' : rise ? 'too few appointments per TME team' : 'deals split like the appointments';
      return `<span class="mc rd"><span>Most from <b>${esc(GROUPS[x.top])}</b> · ${Math.round(S[0][x.top])}% of given</span><span class="mu">${why.charAt(0).toUpperCase() + why.slice(1)}</span></span>`;
    };
    const sum = r => `${n0(r.n)} given · ${pct0(r.att, r.n)} attd · ${r.away ? 'deals in own city' : pct0(r.deals, CB() ? r.n : r.att) + ' conv'}`;
    const row = (x, ref) => {
      const r = x.r, u = r.unit;
      const sub = ref ? 'together, the normal' : u ? u.sub : (r.tl ? `Team leader: ${r.tl}` : r.mgr ? `Manager: ${r.mgr}` : 'No team leader recorded');
      const tag = ref ? `div title="${esc(sub)}"` : u ? `button type="button" data-scope="${u.k}" title="${esc(`${u.name}: ${sub}. Click to show only this team on the whole dashboard`)}"` : `button type="button" data-me="${r.me}" title="${esc(`${r.name}: ${sub}`)}"`;
      return `<${tag} class="mer${ref ? ' ref' : ''}">` +
        `<span class="mc nm"><b>${ref ? `${esc(META.city)}, all MEs` : u ? esc(u.name) + (u.tag ? `<span class="rtag">${esc(u.tag)}</span>` : '') : esc(r.name) + rtag(r)}</b><small class="sm">${sum(r)}</small>${ref ? '' : why(x)}</span>` +
        ribbon(x) + reading(x, ref) + `</${ref ? 'div' : 'button'}>`;
    };
    $('#meList').innerHTML = `<div class="mer mh" aria-hidden="true"><span class="mc nm">${teams ? (lvl() === 1 ? 'Manager' : 'Team leader') : 'ME'}</span><span class="mc gh">Team shares: appointments given → attended → deals closed<span class="key">${GROUPS.map((l, i) => `<span><i class="t${i}"></i>${esc(l)}</span>`).join('')}</span></span><span class="mc gh">Reading</span></div>` +
      row(cityX, true) + show.map(x => row(x)).join('') +
      (list.length ? '' : `<p class="empty">${q ? `Nothing matches "${esc(q)}".` : `No ${word}s in these dates.`}</p>`) +
      ovPager(list.length, pg.pages, `${word}s`) +
      `<div class="lfoot"><span class="gap"></span><button type="button" class="lnk" id="lCsv">Download this list (CSV)</button></div>` +
      `<p class="hint">Each bar is 100% of the ${word}'s appointments given, attended or deals closed, split by TME team. A band that widens on the way down is a TME team the ${word} converts better than its other TME teams; one that narrows, one it converts less. Some change is normal: compare with ${esc(META.city)}'s line on top. Point at a band for its numbers. ${teams ? 'Click a team to show only that team on the whole dashboard.' : 'Click an ME for their page.'}${V.sortBy === 'uneven' ? ` "Uneven attended across teams" puts first the lines whose attendance differs most between two TME teams, beyond the usual difference in ${esc(META.city)} (e.g. Super Cat 94% vs Hot Data 30%, where ${esc(META.city)} is 88% vs 78%). A TME team needs ${G_GAP_MIN}+ appointments to count.` : ''}</p>`;
  }
  $('#sortBy').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) { V.sortBy = b.dataset.v; OPG = 0; renderList(); } });
  $('#meSearch').addEventListener('input', () => { OPG = 0; V.ovShut.clear(); renderLadder(); renderList(); });
  $('#meList').addEventListener('click', ev => {
    if (ev.target.closest('#lCsv')) return listCsv();
    const t = ev.target.closest('.mer[data-scope]'); if (t) return setScope(+t.dataset.scope, true);
    const b = ev.target.closest('.mer[data-me]'); if (b) openMe(+b.dataset.me);
  });
  function listCsv() {
    const f = x => x === null || x === undefined || !isFinite(x) ? '' : (+x).toFixed(1);
    if (LROWS.length && LROWS[0].r.unit) return download(`ME_teams_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['Team', 'What it is', 'MEs', 'Appointments given', 'Attended', 'Attended %', 'Deals closed', `Conversion % (${CVOF()})`, 'Not Available', 'Pending', 'Not Visited',
        ...GROUPS.flatMap(l => [`${l} appointments given`, `${l} attended`, `${l} deals closed`])],
        ...LROWS.map(x => { const r = x.r; return [r.name, r.unit.sub, r.k, r.n, r.att, f(r.attP), r.away ? '' : r.deals, f(r.conv), r.o[3], r.o[4], r.o[5], ...x.g.flat()]; })]);
    download(`ME_team_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['ME code', 'ME', 'Team leader', 'Manager', 'Designation', 'Grade', 'Home city', 'Days present', 'Appointments given', 'Attended', 'Attended %', 'Deals closed', `Conversion % (${CVOF()})`, 'Not Available', 'Pending', 'Not Visited', 'Not Counted/Cancelled',
        ...GROUPS.flatMap(l => [`${l} appointments given`, `${l} attended`, `${l} deals closed`])],
        ...LROWS.map(x => { const r = x.r; return [r.code, r.name, r.tl, r.mgr, r.des, r.grade, r.city, r.pd ?? '', r.n, r.att, f(r.attP), r.deals, f(r.conv), r.na, r.o[4], r.o[5], r.nc, ...x.g.flat()]; })]);
  }


  /* ---------- teams: ME rows added up by the hierarchy (the Overview ladder and the Table share these) ---------- */
  // SUB: team -> every ME row inside it, at any depth up to the scope; DIR: team -> its own MEs (not in a team below it)
  function teamIndex(rows) {
    const SUB = new Map(), DIR = new Map();
    const push = (M, k, r) => { let a = M.get(k); if (!a) M.set(k, a = []); a.push(r); };
    for (const r of rows) {
      if (r.node < 0) continue;
      push(DIR, r.node, r);
      for (let c = r.node, g = 0; c >= 0 && g < 8; g++) { push(SUB, c, r); if (c === V.scope || c === ROOT) break; c = UPN(c); }
    }
    return { SUB, DIR };
  }
  // a team (or the table's totals) as one row: sums, rates on the sums, average days present
  function sumRows(rows) {
    const s = { n: 0, att: 0, deals: 0, o: [0, 0, 0, 0, 0, 0], nc: 0, pd: 0, pdN: 0, nPd: 0, aPd: 0, away: 0, g: z3() };
    for (const r of rows) {
      s.n += r.n; s.att += r.att; s.deals += r.deals; s.nc += r.nc; r.o.forEach((x, i) => { s.o[i] += x; }); if (r.away) s.away++;
      if (r.pd !== null) { s.pd += r.pd; s.pdN++; s.nPd += r.n; s.aPd += r.att; }
      if (r.g) for (let i = 0; i < NG; i++) for (let j = 0; j < 3; j++) s.g[i][j] += r.g[i][j];
    }
    return { me: -1, name: '', code: '', tl: '', mgr: '', des: '', city: '', grade: '', k: rows.length, n: s.n, att: s.att, deals: s.deals, o: s.o, nc: s.nc, g: s.g,
      attP: pc(s.att, s.n), conv: rows.length && s.away === rows.length ? null : cvr(s.deals, s.att, s.n), away: rows.length > 0 && s.away === rows.length, pd: s.pdN ? s.pd / s.pdN : null, perDay: s.pd ? s.nPd / s.pd : null, attPd: s.pd ? s.aPd / s.pd : null };
  }
  // the small tag after an ME's name: their own appointments as a team leader / manager, or an ME with no team leader
  const rtag = (r, m) => {
    if (r.lead >= 0 && r.lead === r.node) { const d = DEPTH[r.lead]; return d === 2 ? '<span class="rtag" title="Team leader: their own appointments">TL</span>' : d === 1 ? '<span class="rtag" title="Manager: their own appointments">Manager</span>' : '<span class="rtag">ME head</span>'; }
    return m !== undefined && m !== OUTN && NDEP(m) === 1 ? '<span class="rtag" title="Reports to the manager directly (no team leader)">direct</span>' : '';
  };
  function setScope(m, stay) {
    if (m === V.scope || !(m === ROOT || m === OUTN || DEPTH[m] >= 0)) return;
    V.scope = m; V.xOpen.clear(); V.xShut.clear(); V.ovOpen.clear(); V.ovShut.clear(); OPG = 0;
    closeTl(); render(true);
    if (stay && V.view === 'team') $('.tmcard').scrollIntoView({ block: 'start' }); else scrollTo(0, 0);
  }
  // 'Your team' card heading (2026-10-15): in a team, the way back up and whose team this is, so it is clear the card (and
  // the whole page) shows one team
  function renderTeamHead() {
    const card = $('.tmcard'), on = scoped();
    card.classList.toggle('scoped', on);
    if (!on) { $('#tcH').textContent = 'Your team'; return; }
    const up = UPN(V.scope), upName = up === ROOT ? `All ${META.city}` : NNAME(up), role = ROLE(V.scope);
    $('#tcH').innerHTML = `<button type="button" class="tcback" data-scope="${up}" title="Back to ${esc(up === ROOT ? `all of ${META.city}` : `${upName}'s whole team`)}"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg>${esc(upName)}</button>` +
      `<span class="tct">${esc(V.scope === OUTN ? OUT_NAME : `${NNAME(V.scope)}'s team`)}</span>${role ? `<span class="tctag">${role}</span>` : ''}`;
  }
  $('#tcH').addEventListener('click', ev => { const b = ev.target.closest('[data-scope]'); if (b) setScope(+b.dataset.scope, true); });

  /* ---------- Overview, 'Your team': the teams ladder (managers / team leaders, each a small funnel, opening in place) or
     the ME list - one card, switched by Show (shared with the Table, 2026-10-14) ---------- */
  const fPi = v => v === null || v === undefined || !isFinite(v) ? '—' : Math.round(v) + '%';
  let OVMODE = 'lad';   // which half of the card shows: 'lad' (teams) or 'me' (the ME list)
  function renderLadder() {
    renderTeamHead();
    const { SUB } = teamIndex(MEROWS);
    const kidsOf = m => KIDS[m].filter(k => k !== OUTN && SUB.has(k));
    // Show: only the levels below the team shown; a team leader's team (or one with no teams below) shows its MEs
    const base = sDepth();
    $('#ovLvW').hidden = base >= 2;
    document.querySelectorAll('#ovLv button').forEach(b => { b.hidden = +b.dataset.l <= base; b.setAttribute('aria-pressed', String(+b.dataset.l === lvl())); });
    // View: Team shares or Funnel, for every level (2026-10-15; was for MEs only)
    OVMODE = isTree() && kidsOf(V.scope).length ? 'lad' : 'me';
    const bars = meStyle() === 'bars';
    $('#ladPane').hidden = !bars; $('#mePane').hidden = bars;
    document.querySelectorAll('#meStyle button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === meStyle())));
    if (!bars) return;
    const q = $('#meSearch').value.trim().toLowerCase(), hit = r => (r.name + ' ' + r.tl + ' ' + r.mgr + ' ' + r.code).toLowerCase().includes(q);
    const few = s => s.n < MINR;
    const nameOf = x => x.k !== undefined ? NNAME(x.k) : (x.s.name || '');
    const srt = (a, b) => {   // the column and direction picked in the column names; rates on too few appointments last either way
      const k = V.ovSort, up = V.ovDir === 'asc' ? 1 : -1;
      if (k === 'name') return nameOf(a).localeCompare(nameOf(b)) * up;
      if (k === 'n' || k === 'deals') return (a.s[k] - b.s[k]) * up || b.s.n - a.s.n;
      const x = few(a.s) ? null : a.s[k], y = few(b.s) ? null : b.s[k];
      if (x === null || x === undefined) return y === null || y === undefined ? b.s.n - a.s.n : 1;
      if (y === null || y === undefined) return -1;
      return (x - y) * up || b.s.n - a.s.n;
    };
    const ref = sumRows(SUB.get(V.scope) || []), vsName = scoped() ? 'the whole team' : `all ${esc(META.city)}`;
    const GAP = V.to - V.from + 1 < 7 ? 10 : 5;   // green / red only past this many points; a day's few appointments swing more
    const pts = (v, p) => { if (v === null || p === null || v === undefined || p === undefined) return ''; const d = Math.round(v - p); return `<em class="${d >= GAP ? 'up' : d <= -GAP ? 'dn' : ''}">${d === 0 ? 'same' : `${d > 0 ? '+' : MINUS}${Math.abs(d)} pts`}</em>`; };
    let max = 1;
    // each line's funnel (2026-10-16, option C picked from rendered previews): appointments given, attended and deals
    // closed as three centred bars joined by soft shading, width against the biggest line; thin until the line is pointed
    // at (or focused), then full height with the counts, as the Team shares bands
    const FY = [4.5, 19.5, 34.5];   // the middle of each bar: three 9 px rows, 6 px apart
    const fb = s => {
      const W = [s.n, s.att, s.away ? 0 : Math.min(s.deals, s.n)].map(v => v > 0 ? Math.max(.8, v / max * 100) : 0), L = W.map(w => (100 - w) / 2);
      const lab = [`${n0(s.n)} given`, `${n0(s.att)} attended`, s.away ? AWAY_TXT : `${n0(s.deals)} ${s.deals === 1 ? 'deal' : 'deals'}`];
      const bar = (k, c) => W[k] ? `<span class="fq ${c}${W[k] < 18 ? ' out' : ''}" style="left:${L[k].toFixed(2)}%;width:${W[k].toFixed(2)}%"><b>${lab[k]}</b></span>` : '';
      const join = k => W[k] && W[k + 1] ? `<path class="${k ? 'pd' : 'pa'}" d="M${L[k].toFixed(2)},${FY[k]} L${(L[k] + W[k]).toFixed(2)},${FY[k]} L${(L[k + 1] + W[k + 1]).toFixed(2)},${FY[k + 1]} L${L[k + 1].toFixed(2)},${FY[k + 1]} Z"/>` : '';
      return `<span class="fun" title="${esc(`${n0(s.n)} appointments given · ${n0(s.att)} attended · ${s.away ? AWAY_TXT : `${n0(s.deals)} deals closed`}`)}"><svg viewBox="0 0 100 39" preserveAspectRatio="none" aria-hidden="true">${join(0)}${join(1)}</svg>` +
        `<span class="rl">Given</span><span class="ft">${bar(0, 'g')}</span><span class="rl">Attd</span><span class="ft">${bar(1, 'a')}</span><span class="rl">Deals</span><span class="ft">${bar(2, 'd')}</span></span>`;
    };
    const line = (cls, nm, s, p, bar = true) => {
      const f = few(s);
      return `<div class="lr ${cls}">${nm}${bar ? fb(s) : '<span></span>'}<span class="v">${n0(s.n)}</span>` +
        `<span class="v${f ? ' few' : ''}">${fPi(s.attP)}${f || !p ? '' : pts(s.attP, p.attP)}</span><span class="v"${s.away ? ` title="${AWAY_TXT}"` : ''}>${s.away ? '—' : n0(s.deals)}</span>` +
        `<span class="v${f ? ' few' : ''}">${fPi(s.conv)}${f || !p ? '' : pts(s.conv, p.conv)}</span></div>`;
    };
    const refLine = line('ref', `<span class="nm"><span class="chev none"></span><span class="t"><b>${scoped() ? 'Whole team' : `All ${esc(META.city)}`}</b><small>the line to compare with</small></span></span>`, ref, null, false);
    const key = hint => `<span><i class="g"></i>appointments given</span><span><i class="a"></i>attended</span><span><i class="d"></i>deals closed</span>` +
      `<span>Each funnel narrows from appointments given to attended to deals closed; its width is against the biggest line. Point at a line for its numbers. Green / red = ${GAP}+ points above / below the line above; smaller gaps stay grey (rates on fewer than ${MINR} appointments are grey too). Conversion = deals closed ${CVOF()}. Click a column name to order by it, again to turn the order round. ${hint}</span>`;
    if (OVMODE === 'me') {   // every ME in the team shown, one line each, against the team's line
      const all = MEROWS.filter(r => !q || hit(r)).map(r => ({ r, s: r })).sort(srt);
      max = Math.max(1, ...all.map(x => x.s.n));
      $('#tcSub').innerHTML = `${plural(MEROWS.length, 'ME')} with appointments or deals closed, each against ${vsName}` + (q ? ` · ${n0(all.length)} matching "${esc(q)}"` : '');
      $('#lad').innerHTML = [`<div class="lr hd">${ovTh('name', 'ME', 'nmh')}<span></span>${ovHead()}</div>`, refLine,
        ...ovPage(all).rows.map(x => line('l0 me', `<span class="nm"><span class="chev none"></span><button type="button" class="go" data-me="${x.r.me}" title="Open ${esc(x.r.name)}'s page"><b>${esc(x.r.name)}${rtag(x.r, x.r.node)}</b><small>${scoped() && NDEP(V.scope) === 2 ? '' : x.r.tl ? `TL ${esc(x.r.tl)}` : x.r.mgr ? `Mgr ${esc(x.r.mgr)}` : ''}${x.r.away ? `${scoped() && NDEP(V.scope) === 2 ? '' : ' · '}${AWAY_TXT}` : ''}</small></button></span>`, x.s, ref)),
        all.length ? '' : `<p class="empty">${q ? `No ME matches "${esc(q)}".` : 'No MEs in these dates.'}</p>`,
        ovPager(all.length, ovPage(all).pages, 'MEs')].join('');
      $('#ladKey').innerHTML = key('Click an ME for their page.');
      return;
    }
    // the teams ladder. A search works as in the Table's team views: it lists the teams with a matching ME (opened) and
    // the matching MEs; a team's line stays the whole team and the rest of an open team is one 'other MEs, not matching'
    // line, so every line still adds up
    const fRows = q ? MEROWS.filter(hit) : MEROWS;
    const T = fRows.length || !q ? treeLines(fRows, MEROWS, (a, b, ka, kb) => srt({ s: a, k: ka }, { s: b, k: kb }), null, { open: V.ovOpen, shut: V.ovShut }) : { L: [], filt: true };
    const sums = new Map([[V.scope, ref]]), sumOf = m => { if (!sums.has(m)) sums.set(m, sumRows(SUB.get(m) || [])); return sums.get(m); };
    max = Math.max(1, ...T.L.filter(x => x.d === 0 && !x.rest).map(x => (x.T || x.r).n));   // the 'not matching' lines have no bar
    const CHEV = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg>';
    const chev = (k, o, nm) => `<button type="button" class="chev" data-lo="${k}" aria-expanded="${o}" aria-label="${o ? 'Close' : 'Open'} ${esc(nm)}">${CHEV}</button>`;
    const rows = [`<div class="lr hd">${ovTh('name', scoped() ? 'Team leader' : 'Manager', 'nmh')}<span></span>${ovHead()}</div>`, refLine], lines = [];
    for (const x of T.L) {
      if (x.rest) { lines.push(line(`l${x.d} me rest`, `<span class="nm"><span class="chev none"></span><span class="t"><span class="rname" title="MEs in this team that do not match the search, added up so the team's line adds up">${plural(x.rest.length, 'other ME')}, not matching</span></span></span>`, x.T, sumOf(x.m), false)); continue; }
      if (x.r) { lines.push(line(`l${x.d} me`, `<span class="nm"><span class="chev none"></span><button type="button" class="go" data-me="${x.r.me}" title="Open ${esc(x.r.name)}'s page"><b>${esc(x.r.name)}${rtag(x.r, x.m)}</b></button></span>`, x.r, sumOf(x.m))); continue; }
      if (x.k === OUTN) { lines.push(line(`l${x.d} out`, `<span class="nm">${chev(OUTN, x.open, OUT_NAME)}<span class="t"><b>${esc(OUT_NAME)}</b><small>${plural(x.T.k, 'ME')} · their HR reporting line ends elsewhere${x.T.away ? ` · ${AWAY_TXT}` : ''}</small></span></span>`, x.T, ref)); continue; }
      const nT = kidsOf(x.k).length, nm = NNAME(x.k);
      lines.push(line(`l${x.d}`, `<span class="nm">${chev(x.k, x.open, nm)}<button type="button" class="go" data-scope="${x.k}" title="Show only ${esc(nm)}'s team on the whole dashboard"><b>${esc(nm)}</b><small>${nT ? `${plural(nT, 'team leader')} · ` : ROLE(x.k) === 'team leader' ? 'team leader · ' : ''}${plural(x.T.k, 'ME')}</small></button></span>`, x.T, x.d === 0 ? ref : sumOf(UPN(x.k))));
    }
    const pg = ovPage(lines);   // paged as the Table: a page of lines (teams and MEs as they open)
    // a page that starts inside a team names the teams it sits in, so the lines keep their place
    const at = OPS ? OPG * OPS : 0;
    if (at > 0 && T.L[at] && T.L[at].d > 0) {
      const up = []; for (let i = at - 1, d = T.L[at].d; i >= 0 && d > 0; i--) if (T.L[i].k !== undefined && T.L[i].d === d - 1) { up.unshift(NNAME(T.L[i].k)); d--; }
      if (up.length) rows.push(`<div class="lr cont"><span class="nm"><span class="chev none"></span><span class="t">${up.map(esc).join(' › ')} · continued</span></span></div>`);
    }
    rows.push(...pg.rows, ovPager(lines.length, pg.pages, 'lines'));
    if (q && !T.L.length) rows.push(`<p class="empty">No ME, team leader or manager matches "${esc(q)}".</p>`);
    $('#tcSub').innerHTML = `${scoped() ? '' : `${esc(HEADNAME)}'s `}${plural(kidsOf(V.scope).length, scoped() ? 'team leader' : 'manager')}, each against ${vsName}` + (q ? ` · teams with an ME matching "${esc(q)}"` : '');
    $('#lad').innerHTML = rows.join('');
    $('#ladKey').innerHTML = key(`▸ opens a team; click a name to show only that team on the whole dashboard.${T.filt ? ' The search only picks which teams and MEs are listed; the rest of an open team shows as one "other MEs, not matching" line.' : ''}`);
  }
  $('#lad').addEventListener('click', ev => {
    const c = ev.target.closest('[data-lo]');
    if (c) { const k = +c.dataset.lo; if (c.getAttribute('aria-expanded') === 'true') { V.ovOpen.delete(k); V.ovShut.add(k); } else { V.ovShut.delete(k); V.ovOpen.add(k); } return renderLadder(); }
    const s = ev.target.closest('[data-scope]'); if (s) return setScope(+s.dataset.scope, true);
    const m = ev.target.closest('[data-me]'); if (m) openMe(+m.dataset.me);
  });
  // the column names order the lines (the order chips before 2026-10-15); a second click on the same name turns the
  // order round. Counts start most first, rates lowest first, names A to Z. Every name shows it can be ordered (↕)
  const OV_SORTS = { name: ['asc', 'name'], n: ['desc', 'appointments given'], attP: ['asc', 'attended %'], deals: ['desc', 'deals closed'], conv: ['asc', 'conversion %'] };
  V.ovDir = OV_SORTS[V.ovSort][0];
  const ovSay = (k, d) => k === 'name' ? (d === 'asc' ? 'A to Z' : 'Z to A') : k === 'n' || k === 'deals' ? (d === 'desc' ? 'most first' : 'fewest first') : (d === 'desc' ? 'highest first' : 'lowest first');
  const ovTh = (k, label, cls) => {
    const on = V.ovSort === k, next = on ? (V.ovDir === 'asc' ? 'desc' : 'asc') : OV_SORTS[k][0];
    return `<button type="button" class="${cls} sh${on ? ' on' : ''}" data-s="${k}" aria-pressed="${on}" title="${on ? `Ordered by ${OV_SORTS[k][1]}, ${ovSay(k, V.ovDir)}. Click for ${ovSay(k, next)}` : `Order by ${OV_SORTS[k][1]}, ${ovSay(k, next)}`}">${label}<i aria-hidden="true">${on ? (V.ovDir === 'desc' ? '↓' : '↑') : '↕'}</i></button>`;
  };
  const ovHead = () => ovTh('n', 'Appointments given', 'v') + ovTh('attP', 'Attended %', 'v') + ovTh('deals', 'Deals closed', 'v') + ovTh('conv', 'Conversion %', 'v');
  $('#lad').addEventListener('click', ev => {
    const b = ev.target.closest('.lr.hd [data-s]'); if (!b) return;
    const k = b.dataset.s;
    if (V.ovSort === k) V.ovDir = V.ovDir === 'asc' ? 'desc' : 'asc'; else { V.ovSort = k; V.ovDir = OV_SORTS[k][0]; }
    OPG = 0; renderLadder();
  });
  // Show: Managers / Team leaders / MEs - one choice for the Overview and the Table, remembered in this browser
  function setLevel(l) {
    V.lvl = l; V.xOpen.clear(); V.xShut.clear(); V.ovOpen.clear(); V.ovShut.clear(); OPG = 0;
    try { localStorage.setItem('jd-me-review-show', String(V.lvl)); } catch (e) { /* not remembered */ }
    closeCol(); renderLadder(); renderList(); renderX();
  }
  $('#ovLv').addEventListener('click', ev => { const b = ev.target.closest('[data-l]'); if (b) setLevel(+b.dataset.l); });
  $('#meStyle').addEventListener('click', ev => {
    const b = ev.target.closest('[data-v]'); if (!b || b.dataset.v === meStyle()) return;
    MS[MS_KEY()] = b.dataset.v; OPG = 0; try { localStorage.setItem(MS_KEY(), b.dataset.v); } catch (e) { /* not remembered */ }
    renderLadder(); renderList();
  });


  /* ---------- table view: every ME in columns, Excel-style filters on each header, bands with cutoffs Kushal sets ---------- */
  const BAND_STORE = 'jd-me-review-bands-v1';
  const BANDS = {
    n: { label: 'Appointments given', def: [50, 80], int: true, scale: true },
    pd: { label: 'Days present', def: [20, 24], int: true, scale: true },
    perDay: { label: 'Appointments given per day present', def: [2, 3], int: false },
  };
  const BAND_KEYS = Object.keys(BANDS);
  let CUTS = {};
  try { CUTS = JSON.parse(localStorage.getItem(BAND_STORE) || '{}') || {}; } catch (e) { CUTS = {}; }
  for (const k of BAND_KEYS) if (!Array.isArray(CUTS[k]) || CUTS[k].length !== 2 || !(CUTS[k][0] < CUTS[k][1])) CUTS[k] = BANDS[k].def.slice();
  const saveCuts = () => { try { localStorage.setItem(BAND_STORE, JSON.stringify(CUTS)); } catch (e) { /* the cutoffs just aren't remembered */ } };
  const fCut = (k, x) => BANDS[k].int && Number.isInteger(x) ? n0(x) : (Math.round(x * 10) / 10).toString();
  // cutoffs are kept per month (WD_MONTH working days) and scaled to the working days in the dates shown
  const WD_MONTH = 26;
  const wdIn = (a, b) => { let n = 0; for (let d = a; d <= b; d++) if (DAYN[d]) n++; return n; };
  const scaleF = () => Math.max(1, wdIn(V.from, V.to)) / WD_MONTH;
  function ECUT(k) {
    if (!BANDS[k].scale) return CUTS[k];
    if (k === 'pd') {   // HR days present are spread over calendar days (pro rata), so these scale by calendar days
      const g = (V.to - V.from + 1) / 30.4; if (g >= 0.97) return CUTS[k];
      return [Math.round(CUTS[k][0] * g * 10) / 10, Math.max(Math.round(CUTS[k][0] * g * 10) / 10 + 0.1, Math.round(CUTS[k][1] * g * 10) / 10)];
    }
    const f = scaleF(); if (Math.abs(f - 1) < 0.02) return CUTS[k];
    const lo = Math.max(1, Math.round(CUTS[k][0] * f)), hi = Math.max(lo + 1, Math.round(CUTS[k][1] * f));
    return [lo, hi];
  }
  const bandOf = (k, v) => { if (v === null || v === undefined || !isFinite(v)) return -1; const c = ECUT(k); return v < c[0] ? 0 : v < c[1] ? 1 : 2; };
  function bandName(k, b) {
    const [lo, hi] = ECUT(k);
    if (b === 0) return `Under ${fCut(k, lo)}`;
    if (b === 2) return `${fCut(k, hi)} or more`;
    return BANDS[k].int && Number.isInteger(lo) && Number.isInteger(hi) ? (hi - 1 > lo ? `${fCut(k, lo)}–${fCut(k, hi - 1)}` : fCut(k, lo)) : `${fCut(k, lo)} to under ${fCut(k, hi)}`;
  }

  // the columns: key, header, group, kind (text | list | num | pct), value, display
  const yr = j => j ? j.slice(0, 4) : '';
  const BASE_COLS = [
    { k: 'name', h: 'ME', sec: 'ME', kind: 'text', v: r => r.name },
    // only: shown in the team views (Managers / Team leaders) or in the MEs view
    { k: 'mes', h: 'MEs', full: 'MEs with appointments', tip: 'in these dates; an ME counts in the team where most of their appointments sit', sec: 'ME', kind: 'num', only: 'tree', v: r => r.me >= 0 ? null : r.k },
    { k: 'code', h: 'ME code', sec: 'ME', kind: 'text', v: r => r.code },
    { k: 'tl', h: 'TL', full: 'Team leader', sec: 'ME', kind: 'list', only: 'flat', v: r => r.tl || '(no team leader)', d: r => r.tl || '—' },
    { k: 'mgr', h: 'Mgr', full: 'Manager', sec: 'ME', kind: 'list', only: 'flat', v: r => r.mgr || '(none)', d: r => r.mgr || '—' },
    { k: 'des', h: 'Designation', sec: 'ME', kind: 'list', v: r => r.des || '(not in HR)' },
    { k: 'grade', h: 'Grade', sec: 'ME', kind: 'list', v: r => r.grade || '(not recorded)', sv: r => { const m = /(\d+)/.exec(r.grade || ''); return m ? +m[1] : null; } },
    { k: 'city', h: 'Home city', sec: 'ME', kind: 'list', v: r => r.city || '(not in HR)' },
    { k: 'joined', h: 'Joined', sec: 'ME', kind: 'list', v: r => yr(HRJ[r.me]) || '(not in HR)', sv: r => HRJ[r.me] || '', d: r => HRJ[r.me] ? `${MON3[+HRJ[r.me].slice(5, 7) - 1]} ${HRJ[r.me].slice(0, 4)}` : '—' },
    { k: 'pd', h: 'Days present', tip: 'days present in these dates, from HR attendance', sec: 'Attendance (HR)', kind: 'num', band: 'pd', v: r => r.pd, d: r => r.pd === null ? '—' : (Math.round(r.pd * 10) / 10).toString() },
    { k: 'perDay', h: 'Appts / day', full: 'Appointments given per day present', tip: 'appointments given ÷ days present (HR attendance)', sec: 'Attendance (HR)', kind: 'num', band: 'perDay', v: r => r.perDay, d: r => r.perDay === null ? '—' : r.perDay.toFixed(1) },
    { k: 'attPd', h: 'Attd / day', full: 'Appointments attended per day present', tip: 'appointments attended ÷ days present (HR attendance)', sec: 'Attendance (HR)', kind: 'num', v: r => r.attPd, d: r => r.attPd === null ? '—' : r.attPd.toFixed(1) },
    { k: 'n', h: 'Appts given', full: 'Appointments given', sec: 'All teams', kind: 'num', band: 'n', v: r => r.n, strong: true },
    { k: 'att', h: 'Attd', full: 'Attended', sec: 'All teams', kind: 'num', v: r => r.att },
    { k: 'na', h: 'Not Available', sec: 'All teams', kind: 'num', v: r => r.o[3] },
    { k: 'pend', h: 'Pending', sec: 'All teams', kind: 'num', v: r => r.o[4] },
    { k: 'nv', h: 'Not Visited', sec: 'All teams', kind: 'num', v: r => r.o[5] },
    { k: 'deals', h: 'Deals closed', sec: 'All teams', kind: 'num', v: r => r.deals, d: r => r.away ? '—' : n0(r.deals) },
    { k: 'attP', h: 'Attd %', full: 'Attended %', sec: 'All teams', kind: 'pct', bar: 'a', v: r => r.attP, few: r => r.n < MINR },
    { k: 'conv', h: 'Conv %', full: 'Conversion %', sec: 'All teams', kind: 'pct', bar: 'd', v: r => r.conv, few: r => r.n < MINR },
    { k: 'nc', h: 'Not counted', sec: 'All teams', kind: 'num', v: r => r.nc },
  ];
  // one set of team columns per TME team group (the groups follow the settings; 2026-10-16)
  const TEAMSETS = () => GROUPS.map((g, i) => ({ id: GDEF[g].id, name: GSHORT[i], idx: [i], t: GDEF[g].tint }));
  const sumG = (r, idx, j) => idx.reduce((t, i) => t + r.g[i][j], 0);
  const makeCols = () => [...BASE_COLS, ...TEAMSETS().flatMap(T => [
    { k: `${T.id}n`, h: 'G', full: 'Appointments given', grp: T.name, team: T.t, kind: 'num', v: r => sumG(r, T.idx, 0), first: true },
    { k: `${T.id}t`, h: 'A', full: 'Attended', grp: T.name, team: T.t, kind: 'num', v: r => sumG(r, T.idx, 1) },
    { k: `${T.id}a`, h: 'A%', full: 'Attended %', grp: T.name, team: T.t, kind: 'pct', bar: 'a', v: r => pc(sumG(r, T.idx, 1), sumG(r, T.idx, 0)), few: r => sumG(r, T.idx, 0) < G_MIN },
    { k: `${T.id}d`, h: 'D', full: 'Deals closed', grp: T.name, team: T.t, kind: 'num', v: r => sumG(r, T.idx, 2) },
    { k: `${T.id}c`, h: 'C%', full: 'Conversion %', grp: T.name, team: T.t, kind: 'pct', bar: 'd', v: r => cvr(sumG(r, T.idx, 2), sumG(r, T.idx, 1), sumG(r, T.idx, 0)), few: r => sumG(r, T.idx, 0) < G_MIN },
  ])];
  let XCOLS = makeCols();
  let XC = Object.fromEntries(XCOLS.map(c => [c.k, c]));
  // hidden columns and column widths, remembered in this browser; a few rarely used ones start hidden
  const XHIDE_KEY = 'jd-me-review-xhide-v1', XW_KEY = 'jd-me-review-xwidth-v1';
  // the per-team attended counts (A) start hidden too, also for browsers that saved a choice before they existed
  const TEAM_A = ['sct', 'hdt', 'ont', 'ott', 'hot', 'ext'];
  // two column choices, kept apart: 1 to 6 days (the ME Head's daily look) and 7 days or more
  const dayMode = () => V.to - V.from + 1 < 7;
  const XHIDE_DAY_KEY = 'jd-me-review-xhide-day-v2';
  const LONG_HIDE = ['code', 'city', 'joined', 'na', 'pend', 'nv', 'nc', ...TEAM_A];
  const DAY_HIDE = ['code', 'des', 'grade', 'city', 'joined', 'pd', 'perDay', 'attPd', 'nv', 'nc', ...TEAM_A];   // per TME team: G, A%, D, C% (as for longer periods)
  let XHL = new Set(LONG_HIDE), XHD = new Set(DAY_HIDE), XW = {};
  try {
    const h = JSON.parse(localStorage.getItem(XHIDE_KEY) || 'null'); if (Array.isArray(h)) XHL = new Set(h);
    if (!localStorage.getItem('jd-me-review-xhide-teamA')) { TEAM_A.forEach(k => XHL.add(k)); localStorage.setItem('jd-me-review-xhide-teamA', '1'); localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); }
    // the expiry team's attended count (A, 2026-10-16) starts hidden too, also in column choices saved before it
    if (!localStorage.getItem('jd-me-review-xhide-ext')) { XHL.add('ext'); localStorage.setItem('jd-me-review-xhide-ext', '1'); localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); }
    const hd = JSON.parse(localStorage.getItem(XHIDE_DAY_KEY) || 'null'); if (Array.isArray(hd)) XHD = new Set(hd);
    // 'Attended per day' (15 Oct 2026) is empty under 7 days: hidden in a day choice saved before it existed
    if (!localStorage.getItem('jd-me-review-xhide-attPd')) { XHD.add('attPd'); localStorage.setItem('jd-me-review-xhide-attPd', '1'); localStorage.setItem(XHIDE_DAY_KEY, JSON.stringify([...XHD])); }
    XW = JSON.parse(localStorage.getItem(XW_KEY) || '{}') || {};
  } catch (e) { /* defaults */ }
  let XHIDE = XHL;
  const pickHide = () => { XHIDE = dayMode() ? XHD : XHL; };
  const saveX = () => { try { localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); localStorage.setItem(XHIDE_DAY_KEY, JSON.stringify([...XHD])); localStorage.setItem(XW_KEY, JSON.stringify(XW)); } catch (e) { /* not remembered */ } };
  // inside one team, the manager (and in a team leader's team, the team leader) is the same on every line: left out
  const sameAll = k => (k === 'mgr' && sDepth() >= 1) || (k === 'tl' && sDepth() >= 2);
  const visCols = () => { const t = isTree() ? 'tree' : 'flat'; return XCOLS.filter(c => c.k === 'name' || (!XHIDE.has(c.k) && (!c.only || c.only === t) && !sameAll(c.k))); };
  const NARROW = matchMedia('(max-width: 860px)');
  const DEFW = { name: 150, mes: 56, code: 84, tl: 122, mgr: 122, des: 140, grade: 58, city: 96, joined: 76, pd: 72, perDay: 84, attPd: 80, n: 92, att: 60, attP: 76, deals: 66, conv: 76, na: 76, pend: 66, nv: 68, nc: 74 };   // compact (2026-10-14)
  // the name column is wider in the team views (names are indented under their team); its width is kept apart
  const wKey = k => k === 'name' && isTree() ? 'tname' : k;
  const colW = c => XW[wKey(c.k)] || (c.k === 'name' && isTree() ? 230 : 0) || (c.k === 'name' && NARROW.matches ? 120 : 0) || DEFW[c.k] || (c.team !== undefined ? (c.kind === 'pct' ? 54 : 50) : 80);
  const colName = c => (c.grp ? `${c.grp} ${(c.full || c.h).toLowerCase()}` : c.full || c.h) + (/onversion/.test(c.full || c.h) ? ` (${CVOF()})` : '');
  // filters: { key: { q } | { vals: Set } | { min, max, bands: Set } }; the default shows MEs with MIN+ appointments, like the overview
  let XF = {};
  const XS = { k: 'n', dir: -1 };
  let XROWS = [], XALL = [];   // the MEs listed (search + filters) and every ME in the dates and team

  const xRows = () => MEROWS.map(r => Object.assign({}, r, { g: groupsOf(CUR, r.me) }));
  function passes(r, f, c) {
    const v = c.v(r);
    if (f.q) return String(v).toLowerCase().includes(f.q.toLowerCase());
    if (f.vals) return f.vals.has(String(v));
    if (f.min !== undefined && f.min !== null && !(v !== null && v >= f.min)) return false;
    if (f.max !== undefined && f.max !== null && !(v !== null && v <= f.max)) return false;
    if (f.bands && f.bands.size && !f.bands.has(bandOf(c.band, v))) return false;
    return true;
  }
  const isOn = f => !!f && (!!f.q || !!f.vals || (f.min !== undefined && f.min !== null) || (f.max !== undefined && f.max !== null) || !!(f.bands && f.bands.size));
  // except: leave out that column's filter; noBands: leave out only that column's band choice (the band cards count with it off)
  const filtered = (rows, except, noBands) => rows.filter(r => Object.entries(XF).every(([k, f]) => {
    if (k === except) return true;
    if (k === noBands) f = Object.assign({}, f, { bands: null });
    return !isOn(f) || passes(r, f, XC[k]);
  }));
  function fText(k, f) {
    const c = XC[k], nm = colName(c);
    if (f.q) return `${nm} contains "${f.q}"`;
    if (f.vals) return f.vals.size === 1 ? `${nm}: ${[...f.vals][0]}` : `${nm}: ${n0(f.vals.size)} chosen`;
    const p = [];
    if (f.bands && f.bands.size) p.push([...f.bands].sort().map(b => bandName(c.band, b)).join(' or '));
    const num = x => c.kind === 'pct' ? x + '%' : (Number.isInteger(x) ? n0(x) : x);
    if (f.min !== undefined && f.min !== null && f.max !== undefined && f.max !== null) p.push(`${num(f.min)} to ${num(f.max)}`);
    else if (f.min !== undefined && f.min !== null) p.push(`${num(f.min)} or more`);
    else if (f.max !== undefined && f.max !== null) p.push(`${num(f.max)} or less`);
    return `${nm}: ${p.join(', ')}`;
  }

  /* the bands card: one stacked bar of MEs per band for each banded number, cutoffs editable in place */
  const bandKeys = () => V.to - V.from + 1 < 7 ? BAND_KEYS.filter(k => k === 'n') : BAND_KEYS;
  function renderBands(all) {
    const f = scaleF(), wd = wdIn(V.from, V.to);
    $('#bdScale').innerHTML = Math.abs(f - 1) < 0.02 ? '' : `Cutoffs for appointments given and days present are set for a month (${WD_MONTH} working days) and scaled to these dates (${plural(wd, 'working day')}): appointments given ${CUTS.n.map(x => fCut('n', x)).join(' / ')} a month = ${ECUT('n').join(' / ')} here.`;
    $('#bands').innerHTML = bandKeys().map(k => {
      const rows = filtered(all, null, k), cnt = [0, 0, 0], miss = rows.filter(r => bandOf(k, XC[k].v(r)) < 0).length;
      for (const r of rows) { const b = bandOf(k, XC[k].v(r)); if (b >= 0) cnt[b]++; }
      const tot = cnt[0] + cnt[1] + cnt[2], sel = (XF[k] && XF[k].bands) || new Set();
      const seg = b => cnt[b] ? `<button type="button" class="bseg b${b}${sel.has(b) ? ' on' : ''}" data-k="${k}" data-b="${b}" style="flex:${cnt[b]}" aria-pressed="${sel.has(b)}" title="${esc(`${bandName(k, b)}: ${plural(cnt[b], 'ME')}. Click to show only these`)}"><span>${n0(cnt[b])}</span></button>` : '';
      const lab = b => `<button type="button" class="blab${sel.has(b) ? ' on' : ''}" data-k="${k}" data-b="${b}" aria-pressed="${sel.has(b)}"><i class="b${b}"></i>${esc(bandName(k, b))} <b>${n0(cnt[b])}</b></button>`;
      const step = BANDS[k].int ? 1 : 0.1, ec = ECUT(k);
      return `<div class="bcard"><div class="bt">${esc(BANDS[k].label)}</div>` +
        `<div class="bstack">${tot ? [0, 1, 2].map(seg).join('') : '<span class="mu">No MEs</span>'}</div>` +
        `<div class="blabs">${[0, 1, 2].map(lab).join('')}</div>` +
        `<div class="bcuts"><label>Low band below <input type="number" inputmode="decimal" step="${step}" min="0" data-k="${k}" data-i="0" value="${ec[0]}" aria-label="${esc(BANDS[k].label)}: low band below"></label>` +
        `<label>high band from <input type="number" inputmode="decimal" step="${step}" min="0" data-k="${k}" data-i="1" value="${ec[1]}" aria-label="${esc(BANDS[k].label)}: high band from"></label></div>` +
        (miss ? `<p class="bmiss">${plural(miss, 'ME')} with no HR record for these dates</p>` : '') + `</div>`;
    }).join('') + (bandKeys().length < BAND_KEYS.length ? `<div class="bcard bnote"><div class="bt">Days present</div><p class="mu">Comes from HR's monthly attendance, so days present and appointments given per day present show for 7 days or more.</p></div>` : '');
  }
  $('#bands').addEventListener('click', ev => {
    const b = ev.target.closest('[data-b]'); if (!b) return;
    const k = b.dataset.k, v = +b.dataset.b, f = XF[k] || (XF[k] = {});
    f.bands = f.bands || new Set(); f.bands.has(v) ? f.bands.delete(v) : f.bands.add(v);
    renderX();
  });
  $('#bands').addEventListener('change', ev => {
    const inp = ev.target.closest('input[data-k]'); if (!inp) return;
    const k = inp.dataset.k, i = +inp.dataset.i, x = parseFloat(inp.value), c = ECUT(k).slice();
    if (!isFinite(x) || x < 0) { inp.value = ECUT(k)[i]; return; }
    c[i] = BANDS[k].int && !(k === 'pd' && V.to - V.from + 1 < 30) ? Math.round(x) : Math.round(x * 10) / 10;
    if (!(c[0] < c[1])) { inp.value = ECUT(k)[i]; inp.setCustomValidity('The low cutoff must be below the high one'); inp.reportValidity(); setTimeout(() => inp.setCustomValidity(''), 0); return; }
    const f = !BANDS[k].scale ? 1 : k === 'pd' ? Math.min(1, (V.to - V.from + 1) / 30.4) : scaleF();   // typed for these dates: kept as the month's value
    CUTS[k] = Math.abs(f - 1) < 0.02 ? c : [Math.round(c[0] / f * 10) / 10, Math.round(c[1] / f * 10) / 10];
    saveCuts(); renderX();
  });
  // the Bands card is opened from Columns > Band cutoffs, and closed again with its own button
  const BD_OPEN = 'jd-me-review-bands-card';
  let bdOpen = false; try { bdOpen = localStorage.getItem(BD_OPEN) === '1'; } catch (e) { /* closed */ }
  const paintBd = () => { $('#bdCard').hidden = !bdOpen; };
  const setBd = v => { bdOpen = v; try { localStorage.setItem(BD_OPEN, v ? '1' : '0'); } catch (e) { /* not remembered */ } paintBd(); };
  $('#bdClose').addEventListener('click', () => setBd(false));
  paintBd();
  $('#bdReset').addEventListener('click', () => { for (const k of BAND_KEYS) CUTS[k] = BANDS[k].def.slice(); saveCuts(); renderX(); });

  /* the table */
  const ARR = d => `<svg class="ar" viewBox="0 0 10 10" aria-hidden="true"><path d="${d < 0 ? 'M2 3.5l3 3 3-3' : 'M2 6.5l3-3 3 3'}"/></svg>`;
  const FUN = `<svg class="fi" viewBox="0 0 12 12" aria-hidden="true"><path d="M1.5 2h9L7 6.2V10L5 9V6.2z"/></svg>`;
  // grp: a team's row (sums of its MEs): no band shading, no ME link
  function cellOf(r, c, grp) {
    const v = c.v(r), cls = [c.first ? 'gs' : '', c.strong ? 'st' : '', c.team !== undefined ? 'tc' + c.team : ''];
    if (c.kind === 'text' || c.kind === 'list') {
      const d = c.d ? c.d(r) : v, tg = c.k === 'name' ? rtag(r) : '';
      return c.k === 'name' ? `<td class="nm">${tg ? '<span class="tcell">' : ''}<button type="button" class="lnk me" data-me="${r.me}" title="${esc(d)}">${esc(d)}</button>${tg ? tg + '</span>' : ''}</td>` : `<td class="tx" title="${esc(d)}">${esc(d)}</td>`;
    }
    if (c.k === 'mes' && !grp) return '<td></td>';
    if (c.band && !dayMode() && !grp) { const b = bandOf(c.band, v); if (b >= 0) cls.push('b' + b); }
    if (c.kind === 'pct') {
      if (v === null) return `<td class="${cls.join(' ')} mu">—</td>`;
      const few = c.few && c.few(r);
      if (dayMode()) return `<td class="${cls.join(' ')}${few ? ' few' : ''}"><span class="pv">${Math.round(v)}%</span></td>`;   // a day: plain rates, no size bars
      return `<td class="${cls.join(' ')}${few ? ' few' : ''}"><span class="db ${c.bar}" style="--w:${Math.max(0, Math.min(100, v)).toFixed(0)}%">${Math.round(v)}%</span></td>`;
    }
    const d = c.d ? c.d(r) : (v === null || v === undefined ? '—' : n0(v));
    return `<td class="${cls.join(' ')}${v === 0 ? ' z' : ''}">${d}</td>`;
  }
  const totLabel = rows => isTree() ? `${scoped() ? esc(teamName()) : `All ${esc(META.city)}`}, ${plural(rows.length, 'ME')}` : `Together, ${plural(rows.length, 'ME')}`;
  function totalRow(rows, VIS) {
    const T = sumRows(rows);
    return `<tr class="tot"><td class="nm">${totLabel(rows)}</td>` + VIS.slice(1).map(c => {
      if (c.kind === 'text' || c.kind === 'list') return '<td></td>';
      if (c.k === 'pd') return `<td title="Average days present per ME">${T.pd === null ? '—' : (Math.round(T.pd * 10) / 10) + ' avg'}</td>`;
      if (c.k === 'perDay') return `<td>${T.perDay === null ? '—' : T.perDay.toFixed(1)}</td>`;
      if (c.k === 'attPd') return `<td>${T.attPd === null ? '—' : T.attPd.toFixed(1)}</td>`;
      const v = c.v(T); return `<td class="${c.first ? 'gs' : ''}${c.team !== undefined ? ' tc' + c.team : ''}">${v === null ? '—' : c.kind === 'pct' ? Math.round(v) + '%' : n0(v)}</td>`;
    }).join('') + `</tr>`;
  }
  // the team views: one line per team with the WHOLE team's numbers (all its MEs in the dates) and, when it is open,
  // its teams and MEs below it. A search or filter only picks what is listed (teams with a matching ME, the matching
  // MEs); what it leaves out of an open team becomes one 'other MEs, not matching' line, so every team still adds up
  // (2026-10-14: the team lines used to add up only the matching MEs - 'All Mumbai' showed 23 on a search).
  // A team is open down to the Show level, or when opened by hand; everything opens while a search or filter is on.
  function treeLines(rows, allRows, cmp, mode, S = { open: V.xOpen, shut: V.xShut }) {
    const F = teamIndex(rows), A = rows.length === allRows.length ? F : teamIndex(allRows), filt = A !== F, L = [];
    const isOpen = k => mode === 'csv' || (filt ? !S.shut.has(k) : (S.open.has(k) || (NDEP(k) < lvl() && k !== OUTN)) && !S.shut.has(k));
    const team = (k, d, covered) => {
      const o = isOpen(k), all = A.SUB.get(k);
      L.push({ k, T: sumRows(all), d, open: o }); all.forEach(r => covered.add(r));
      if (o) emit(k, d + 1);
    };
    const emit = (m, d) => {
      const covered = new Set();
      KIDS[m].filter(k => k !== OUTN && F.SUB.has(k)).map(k => ({ k, T: sumRows(A.SUB.get(k)) })).sort((a, b) => cmp(a.T, b.T, a.k, b.k)).forEach(x => team(x.k, d, covered));
      for (const r of (F.DIR.get(m) || []).slice().sort((a, b) => cmp(a, b))) { L.push({ r, d, m }); covered.add(r); }
      if (m === ROOT && F.SUB.has(OUTN)) team(OUTN, d, covered);   // the MEs outside the ME head's line, last
      const left = (A.SUB.get(m) || []).filter(r => !covered.has(r));
      if (left.length) L.push({ rest: left, T: sumRows(left), d, m });
    };
    emit(V.scope, 0);
    return { L, SUB: F.SUB, filt };
  }
  const CHEVX = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg>';
  function groupCell(x, c) {
    const T = x.T;
    if (c.k === 'name' && x.rest) return `<td class="nm"><span class="tcell" style="padding-left:${x.d * 16 + 22}px"><span class="rname" title="MEs in ${esc(x.m === ROOT ? `all ${META.city}` : `${NNAME(x.m)}'s team`)} that do not match the search or filters, added up so the team's line adds up">${plural(x.rest.length, 'other ME')}, not matching</span></span></td>`;
    if (c.k === 'name') {
      const nm = esc(NNAME(x.k));
      return `<td class="nm"><span class="tcell" style="padding-left:${x.d * 16}px"><button type="button" class="tchev" data-t="${x.k}" aria-expanded="${x.open}" aria-label="${x.open ? 'Close' : 'Open'} ${nm}">${CHEVX}</button>` +
        (x.k === OUTN ? `<span class="gname" title="${nm}: their HR reporting line ends elsewhere">${nm}</span>` : `<button type="button" class="lnk gname" data-scope="${x.k}" title="${nm}, ${ROLE(x.k)}: click to show only this team on the whole dashboard">${nm}</button>`) + `</span></td>`;
    }
    if (c.kind === 'text' || c.kind === 'list') return '<td></td>';
    if (c.k === 'pd') return `<td title="Average days present per ME">${T.pd === null ? '—' : (Math.round(T.pd * 10) / 10) + ' avg'}</td>`;
    if (c.k === 'perDay') return `<td>${T.perDay === null ? '—' : T.perDay.toFixed(1)}</td>`;
    if (c.k === 'attPd') return `<td>${T.attPd === null ? '—' : T.attPd.toFixed(1)}</td>`;
    return cellOf(T, c, true);
  }
  const meNameCell = x => `<td class="nm"><span class="tcell" style="padding-left:${x.d * 16 + 22}px"><button type="button" class="lnk me" data-me="${x.r.me}" title="${esc(x.r.name)}">${esc(x.r.name)}</button>${rtag(x.r, x.m)}</span></td>`;
  let XKEEP = false;   // keep the table's scroll position on the next draw (a team opened or closed)
  $('#xSearch').addEventListener('input', () => renderX());
  function renderX() {
    if (V.view !== 'table') return;
    pickHide();
    const all = xRows(), tree = isTree();
    for (const [k, f] of Object.entries(XF)) if (!isOn(f)) delete XF[k];
    renderBands(all);
    // Show: Managers / Team leaders / MEs (only the levels below the team shown)
    const base = sDepth();
    $('#xLvW').hidden = base >= 2;
    document.querySelectorAll('#xLv button').forEach(b => { b.hidden = +b.dataset.l <= base; b.setAttribute('aria-pressed', String(+b.dataset.l === lvl())); });
    // the search box: ME name, team leader, manager or ME code
    const q = $('#xSearch').value.trim().toLowerCase();
    const rows = filtered(all).filter(r => !q || `${r.name} ${r.tl} ${r.mgr} ${r.code}`.toLowerCase().includes(q)), c = XC[XS.k];
    const key = c.sv || c.v, dir = XS.dir;
    const empt = x => x === null || x === undefined || x === '';
    // a team sorts by its sums (by its name for the name column; text columns have no value for a team)
    const val = (o, k) => k === undefined ? key(o) : c.k === 'name' ? NNAME(k) : c.kind === 'text' || c.kind === 'list' ? null : key(o);
    const cmp = (a, b, ka, kb) => {
      const x = val(a, ka), y = val(b, kb);
      if (empt(x)) return empt(y) ? b.deals - a.deals || b.n - a.n : 1; if (empt(y)) return -1;
      return (typeof x === 'string' ? x.localeCompare(y) : x - y) * dir || b.deals - a.deals || b.n - a.n;
    };
    rows.sort((a, b) => cmp(a, b));
    XROWS = rows; XALL = all;
    $('#xH').textContent = rows.length === all.length ? plural(all.length, 'ME') : `${n0(rows.length)} of ${plural(all.length, 'ME')}`;
    const on = Object.entries(XF);
    $('#xChips').innerHTML = on.length ? on.map(([k, f]) => `<span class="fchip"><button type="button" class="fopen" data-k="${k}">${esc(fText(k, f))}</button><button type="button" class="fx" data-k="${k}" aria-label="Remove filter: ${esc(fText(k, f))}"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 6l8 8M14 6l-8 8"/></svg></button></span>`).join('') +
      (on.length > 1 ? `<button type="button" class="lnk" id="xClear">Clear all filters</button>` : '') : '';
    const VIS = visCols(), spans = [];
    for (const c of VIS) { const g = c.grp || ''; const last = spans[spans.length - 1]; if (last && last.g === g) last.n++; else spans.push({ g, n: 1, t: c.team }); }
    // the corner above the ME column is its own frozen cell, so team names scrolled sideways pass under it
    if (spans.length && !spans[0].g) { spans[0].n--; spans.unshift({ g: '', n: 1, corner: true }); if (!spans[1].n) spans.splice(1, 1); }
    const grpRow = `<tr class="gr">` + spans.map((x, i) => `<th colspan="${x.n}" class="${x.corner ? 'g0 xcorner' : i > 1 || (i === 1 && x.g) ? 'gs' : 'g0'}${x.g ? ' tc' + x.t : ''}">${esc(x.g)}</th>`).join('') + `</tr>`;
    const head = `<tr class="hr">` + VIS.map(x => {
      const sorted = XS.k === x.k, f = isOn(XF[x.k]);
      const h = x.k === 'name' && tree ? 'Name' : x.h;
      return `<th class="${x.kind === 'text' || x.kind === 'list' ? 'tx' : ''}${x.first ? ' gs' : ''}${f ? ' fon' : ''}${x.team !== undefined ? ' tc' + x.team : ''}"${sorted ? ` aria-sort="${XS.dir < 0 ? 'descending' : 'ascending'}"` : ''}><button type="button" class="hbtn" data-k="${x.k}" aria-haspopup="dialog" title="${esc((x.k === 'name' && tree ? 'Manager, team leader or ME' : colName(x)) + (x.tip ? `: ${x.tip}` : ''))}">${esc(h)}${sorted ? ARR(XS.dir) : ''}${FUN}</button><span class="rz" data-k="${x.k}" title="Drag to resize"></span></th>`;
    }).join('') + `</tr>`;
    const tw = VIS.reduce((t, c) => t + colW(c), 0);
    // one scroll box: the header rows and the totals row stick at its top, the ME column at its left; pages of XPS rows
    const cg = `<colgroup>${VIS.map(c => `<col data-k="${c.k}" style="width:${colW(c)}px">`).join('')}</colgroup>`;
    const qv = $('#xSearch').value.trim();
    const empty = qv || on.length
      ? `<p class="empty">No ME${qv ? `, team leader or manager matches "${esc(qv)}"` : ' matches these filters'}${qv && on.length ? ' with these filters' : ''}.</p><p class="empty-act">${qv ? '<button type="button" class="btn" id="xClrQ">Clear search</button>' : ''}${on.length ? '<button type="button" class="btn" id="xClrF">Clear filters</button>' : ''}</p>`
      : `<p class="empty">No appointments in these dates.</p>`;
    const sig = [qv, on.map(([k, f]) => fText(k, f)).join('|'), XS.k, XS.dir, V.from, V.to, V.scope, lvl(), XMERGE].join('~');
    if (sig !== XSIG) { XSIG = sig; XPG = 0; }
    // the team views show every line (no pages); the MEs view comes in pages
    const T = tree && rows.length ? treeLines(rows, all, cmp) : null;
    const pages = XPS && !tree ? Math.max(1, Math.ceil(rows.length / XPS)) : 1;
    XPG = Math.min(XPG, pages - 1);
    const shown = XPS && !tree ? rows.slice(XPG * XPS, XPG * XPS + XPS) : rows;
    document.documentElement.style.setProperty('--tbh', $('#topbar').offsetHeight + 'px');   // the box fits under the top bar
    const box = $('#xTbl'), keepX = box.scrollLeft, keepY = box.scrollTop;
    const body = !rows.length ? `<tr><td class="nm emp" colspan="${VIS.length}">${empty}</td></tr>`
      : T ? T.L.map(x => x.r ? `<tr data-me="${x.r.me}">${VIS.map(c2 => c2.k === 'name' ? meNameCell(x) : cellOf(x.r, c2)).join('')}</tr>`
        : x.rest ? `<tr class="trest">${VIS.map(c2 => groupCell(x, c2)).join('')}</tr>`
        : `<tr class="tg l${Math.min(2, x.d + 1)}${x.k === OUTN ? ' out' : ''}" data-node="${x.k}">${VIS.map(c2 => groupCell(x, c2)).join('')}</tr>`).join('')
      : shown.map(r => `<tr data-me="${r.me}">${VIS.map(x => cellOf(r, x)).join('')}</tr>`).join('');
    // the team views' top line is the whole scope (as each team line is the whole team); the MEs view adds up what is listed
    box.innerHTML = `<table style="width:${tw}px">${cg}<thead>${grpRow}${head}${rows.length ? totalRow(tree ? all : rows, VIS) : ''}</thead><tbody>${body}</tbody></table>`;
    // each sticky header row sits right under the one above it
    let top = 0;
    for (const tr of box.querySelectorAll('thead tr')) { for (const c of tr.children) c.style.top = top + 'px'; top += tr.offsetHeight; }
    box.scrollTop = XKEEP ? keepY : 0; box.scrollLeft = keepX; XKEEP = false;
    if (T) {
      const nOf = d => [...T.SUB.keys()].filter(k => k !== OUTN && NDEP(k) === d).length;
      $('#xPager').innerHTML = `<span class="pgi">${[base < 1 ? plural(nOf(1), 'manager') : '', plural(nOf(2), 'team leader'), T.filt ? `${n0(rows.length)} of ${plural(all.length, 'ME')}` : plural(rows.length, 'ME')].filter(Boolean).join(' · ')}${T.filt ? ` match the ${qv && on.length ? 'search and filters' : qv ? 'search' : 'filters'}` : ''}</span>`;
    } else {
      const from = rows.length ? XPG * (XPS || rows.length) + 1 : 0, to = XPS ? Math.min(rows.length, (XPG + 1) * XPS) : rows.length;
      $('#xPager').innerHTML = rows.length ? `<span class="pgi">${n0(from)}–${n0(to)} of ${plural(rows.length, 'ME')}</span>` +
        (pages > 1 ? `<span class="pgb"><button type="button" class="btn" data-pg="-1"${XPG ? '' : ' disabled'} aria-label="Previous page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg></button><span>Page ${XPG + 1} of ${pages}</span><button type="button" class="btn" data-pg="1"${XPG < pages - 1 ? '' : ' disabled'} aria-label="Next page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg></button></span>` : '') +
        `<label class="pgs">Rows per page <select id="xPs">${[25, 50, 100, 0].map(n => `<option value="${n}"${n === XPS ? ' selected' : ''}>${n ? n : 'All'}</option>`).join('')}</select></label>` : '';
    }
    $('#xKey').innerHTML = (tree ? `Each team's line is the whole team: all its MEs in these dates (an ME counts in the team where most of their appointments sit).${T && T.filt ? ' The search / filters only choose which MEs are listed; the rest of a team shows as one "other MEs, not matching" line, so every team still adds up.' : ''} ▸ opens or closes a team; <b>Show</b> opens every team down to that level. Click a team's name to show only that team on the whole dashboard.<br>` : '') +
      `Team columns: <b>G</b> appointments given · <b>A%</b> attended % · <b>D</b> deals closed · <b>C%</b> conversion % (deals closed ${CVOF()}).<br>` +
      `A grey rate has too few appointments behind it to judge.${dayMode() ? '' : ' Shaded cells show the band (Columns > Band cutoffs).'} Click a column name to sort or filter it; click an ME for their page.`;
  }
  // open or close one team in the table (by hand: overrides the Show level until Show, the team or the dates change)
  function toggleX(k) {
    const b = $(`#xTbl tr[data-node="${k}"] .tchev`), open = b && b.getAttribute('aria-expanded') === 'true';
    if (open) { V.xOpen.delete(k); V.xShut.add(k); } else { V.xShut.delete(k); V.xOpen.add(k); }
    XKEEP = true; renderX();
  }
  $('#xLv').addEventListener('click', ev => { const b = ev.target.closest('[data-l]'); if (b) setLevel(+b.dataset.l); });
  // pages: 25 / 50 / 100 rows or all, remembered in this browser; back to page 1 when the search, filters, sort or dates change
  let XPS = 50, XPG = 0, XSIG = '';
  try { const v = localStorage.getItem('jd-me-review-pagesize'); if (v !== null && [0, 25, 50, 100].includes(+v)) XPS = +v; } catch (e) { /* default */ }
  $('#xPager').addEventListener('click', ev => { const b = ev.target.closest('[data-pg]'); if (!b || b.disabled) return; XPG += +b.dataset.pg; renderX(); });
  $('#xPager').addEventListener('change', ev => {
    if (ev.target.id !== 'xPs') return;
    XPS = +ev.target.value; XPG = 0; try { localStorage.setItem('jd-me-review-pagesize', String(XPS)); } catch (e) { /* not remembered */ }
    renderX();
  });
  $('#xTbl').addEventListener('scroll', () => { if (!CP.hidden) closeCol(); });
  $('#xChips').addEventListener('click', ev => {
    if (ev.target.closest('#xClear')) { XF = {}; return renderX(); }
    const x = ev.target.closest('.fx'); if (x) { delete XF[x.dataset.k]; return renderX(); }
    const o = ev.target.closest('.fopen'); if (o) { const th = $(`#xTbl .hbtn[data-k="${o.dataset.k}"]`); if (th) openCol(o.dataset.k, th); }
  });
  $('#xTbl').addEventListener('click', ev => {
    const m = ev.target.closest('button.me'); if (m) return openMe(+m.dataset.me);
    const s = ev.target.closest('[data-scope]'); if (s) return setScope(+s.dataset.scope);
    const t = ev.target.closest('.tchev'); if (t) return toggleX(+t.dataset.t);
    const h = ev.target.closest('.hbtn'); if (h) return openCol(h.dataset.k, h);
    if (ev.target.closest('#xClrQ')) { $('#xSearch').value = ''; return renderX(); }
    if (ev.target.closest('#xClrF')) { XF = {}; return renderX(); }
    const g = ev.target.closest('tbody tr[data-node]'); if (g) return toggleX(+g.dataset.node);   // the rest of a team's line opens or closes it
    const tr = ev.target.closest('tbody tr[data-me]'); if (tr) openMe(+tr.dataset.me);   // the whole row opens the ME's page
  });

  /* the header popover: sort, then filter (tick values, a range, or bands) */
  const CP = $('#colPop');
  let CPK = null;
  function closeCol() { CP.hidden = true; CPK = null; }
  function openCol(k, btn) {
    const c = XC[k], f = XF[k] || {}, isTxt = c.kind === 'text' || c.kind === 'list';
    CPK = k;
    let body = '';
    if (c.kind === 'text') body = `<label class="cpf"><span>Contains</span><input type="search" id="cpQ" value="${esc(f.q || '')}" autocomplete="off" placeholder="Type part of it"></label>`;
    else if (c.kind === 'list') {
      const rows = filtered(xRows(), k), cnt = new Map();
      for (const r of rows) { const v = String(c.v(r)); cnt.set(v, (cnt.get(v) || 0) + 1); }
      const vals = [...cnt.keys()].sort((a, b) => k === 'joined' ? b.localeCompare(a) : a.localeCompare(b));
      const on = v => !f.vals || f.vals.has(v);
      body = `<label class="search cps"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input type="search" id="cpFind" placeholder="Find" autocomplete="off"></label>` +
        `<div class="cplist"><label class="cpall"><input type="checkbox" id="cpAll"${!f.vals ? ' checked' : ''}> (Select all)</label>` +
        vals.map(v => `<label data-v="${esc(v.toLowerCase())}"><input type="checkbox" value="${esc(v)}"${on(v) ? ' checked' : ''}> ${esc(v)} <span class="mu">${n0(cnt.get(v))}</span></label>`).join('') + `</div>`;
    } else {
      const unit = c.kind === 'pct' ? '%' : '';
      body = (c.band ? `<div class="cpb"><span class="cpl">Bands</span>${[0, 1, 2].map(b => `<label><input type="checkbox" data-b="${b}"${f.bands && f.bands.has(b) ? ' checked' : ''}><i class="sw b${b}"></i>${esc(bandName(c.band, b))}</label>`).join('')}</div>` : '') +
        `<div class="cpr"><span class="cpl">Range</span><label>From <input type="number" id="cpMin" step="any" value="${f.min ?? ''}">${unit}</label><label>to <input type="number" id="cpMax" step="any" value="${f.max ?? ''}">${unit}</label></div>`;
    }
    CP.innerHTML = `<div class="cph">${esc(colName(c))}</div>` +
      `<div class="cpsort"><button type="button" class="pre" data-dir="${isTxt ? 1 : -1}">${isTxt ? 'Sort A to Z' : 'Sort largest first'}</button><button type="button" class="pre" data-dir="${isTxt ? -1 : 1}">${isTxt ? 'Sort Z to A' : 'Sort smallest first'}</button></div>` +
      `<div class="cpbody">${body}</div>` +
      `<div class="cpf2"><button type="button" class="lnk" id="cpClear">Clear filter</button><button type="button" class="btn pri" id="cpApply">Apply</button></div>`;
    CP.hidden = false;
    const r = btn.getBoundingClientRect(), w = CP.offsetWidth;
    CP.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px';
    CP.style.top = Math.min(r.bottom + 6, Math.max(8, innerHeight - CP.offsetHeight - 8)) + 'px';
    const first = CP.querySelector('#cpQ, #cpFind, #cpMin, input[data-b]'); if (first) first.focus();
  }
  function applyCol() {
    const k = CPK, c = XC[k]; if (!c) return closeCol();
    if (c.kind === 'text') { const q = $('#cpQ').value.trim(); if (q) XF[k] = { q }; else delete XF[k]; }
    else if (c.kind === 'list') {
      const boxes = [...CP.querySelectorAll('.cplist label[data-v] input')];
      const keep = boxes.filter(b => b.checked).map(b => b.value);
      if (keep.length === boxes.length) delete XF[k]; else XF[k] = { vals: new Set(keep) };
    } else {
      const num = id => { const s = $(id).value.trim(); return s === '' ? null : parseFloat(s); };
      const bands = new Set([...CP.querySelectorAll('input[data-b]')].filter(b => b.checked).map(b => +b.dataset.b));
      XF[k] = { min: num('#cpMin'), max: num('#cpMax'), bands };
    }
    closeCol(); renderX();
  }
  CP.addEventListener('click', ev => {
    const s = ev.target.closest('[data-dir]'); if (s) { XS.k = CPK; XS.dir = +s.dataset.dir; closeCol(); return renderX(); }
    if (ev.target.closest('#cpApply')) return applyCol();
    if (ev.target.closest('#cpClear')) { delete XF[CPK]; closeCol(); return renderX(); }
  });
  CP.addEventListener('change', ev => {
    if (ev.target.id === 'cpAll') CP.querySelectorAll('.cplist label[data-v]:not([hidden]) input').forEach(b => { b.checked = ev.target.checked; });
    else if (ev.target.closest('.cplist')) { const all = [...CP.querySelectorAll('.cplist label[data-v] input')]; $('#cpAll').checked = all.every(b => b.checked); }
  });
  CP.addEventListener('input', ev => {
    if (ev.target.id !== 'cpFind') return;
    const q = ev.target.value.trim().toLowerCase();
    CP.querySelectorAll('.cplist label[data-v]').forEach(l => { l.hidden = !!q && !l.dataset.v.includes(q); });
  });
  CP.addEventListener('keydown', ev => { if (ev.key === 'Enter' && ev.target.tagName === 'INPUT' && ev.target.type !== 'checkbox') { ev.preventDefault(); applyCol(); } });
  document.addEventListener('mousedown', ev => { if (!CP.hidden && !CP.contains(ev.target) && !ev.target.closest('.hbtn, .fopen')) closeCol(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !CP.hidden) { closeCol(); ev.stopImmediatePropagation(); } }, true);

  function xCsv() {
    const cols = visCols(), bandCols = BAND_KEYS;
    const val = (r, c) => { const v = c.v(r); if (c.k === 'joined') return HRJ[r.me] || ''; if (v === null || v === undefined) return ''; return c.kind === 'pct' ? (+v).toFixed(1) : c.k === 'pd' || c.k === 'perDay' || c.k === 'attPd' ? (Math.round(v * 10) / 10) : v; };
    if (isTree()) {
      // the team views: every team and every ME (all opened), in the table's order, with their level, manager and team leader
      const dc = cols.filter(c => c.k !== 'name'), c0 = XC[XS.k], key = c0.sv || c0.v;
      const v2 = (o, k) => k === undefined ? key(o) : c0.k === 'name' ? NNAME(k) : c0.kind === 'text' || c0.kind === 'list' ? null : key(o);
      const empt = x => x === null || x === undefined || x === '';
      const cmp = (a, b, ka, kb) => { const x = v2(a, ka), y = v2(b, kb); if (empt(x)) return empt(y) ? b.n - a.n : 1; if (empt(y)) return -1; return (typeof x === 'string' ? x.localeCompare(y) : x - y) * XS.dir || b.deals - a.deals || b.n - a.n; };
      // teams are whole teams, as on screen: with a search or filter, the MEs left out of a team are one 'Other MEs' line
      const L = XROWS.length ? treeLines(XROWS, XALL, cmp, 'csv').L : [];
      const up = (k, d) => { const c = chainOf(k); return c.length > d ? NNAME(c[d]) : ''; };
      const lev = k => k === OUTN ? 'Not in the line' : DEPTH[k] === 1 ? 'Manager' : 'Team leader';
      const gval = (T, c) => c.kind === 'text' || c.kind === 'list' ? '' : c.k === 'pd' ? (T.pd === null ? '' : Math.round(T.pd * 10) / 10) : val(T, c);
      return download(`ME_teams_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
        [['Level', 'Manager', 'Team leader', 'Name', ...dc.map(colName)],
          ['Total', '', '', scoped() ? teamName() : `All ${META.city}`, ...dc.map(c => gval(sumRows(XALL), c))],
          ...L.map(x => x.r ? ['ME', x.r.mgr, x.r.tl, x.r.name, ...dc.map(c => c.k === 'mes' ? '' : val(x.r, c))]
            : x.rest ? ['Other MEs (not matching)', x.m === ROOT || x.m === OUTN ? '' : up(x.m, 1), x.m === ROOT || x.m === OUTN ? '' : up(x.m, 2), plural(x.rest.length, 'other ME'), ...dc.map(c => gval(x.T, c))]
            : [lev(x.k), x.k === OUTN ? '' : up(x.k, 1), x.k === OUTN ? '' : up(x.k, 2), NNAME(x.k), ...dc.map(c => gval(x.T, c))])]);
    }
    download(`ME_table_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [[...cols.map(colName), ...bandCols.map(k => `${BANDS[k].label} band`)],
        ...XROWS.map(r => [...cols.map(c => val(r, c)), ...bandCols.map(k => { const b = bandOf(k, XC[k].v(r)); return b < 0 ? '' : bandName(k, b); })])]);
  }
  $('#xCsv').addEventListener('click', xCsv);
  // the two group settings (under the settings icon): Hot Data and Online together; the expiry team on its own
  function setGrouping(merge, exp) {
    if (merge === XMERGE && exp === XEXP) return;
    XMERGE = merge; XEXP = exp;
    try { localStorage.setItem('jd-me-review-xmerge-v1', XMERGE ? '1' : '0'); localStorage.setItem('jd-me-review-expiry-v1', XEXP ? '1' : '0'); } catch (e) { /* not remembered */ }
    setGroups();
    XCOLS = makeCols(); XC = Object.fromEntries(XCOLS.map(c => [c.k, c]));
    for (const k of Object.keys(XF)) if (!XC[k]) delete XF[k];
    if (!XC[XS.k]) { XS.k = 'n'; XS.dir = -1; }
    render(true);
  }
  // Columns: tick to show, untick to hide (the ME name always shows)
  const KP = $('#colsPop'), KBTN = $('#xColsBtn');
  function openCols() {
    pickHide();
    const secs = [];
    for (const c of XCOLS) { const sname = c.grp || c.sec; let x = secs.find(z => z.n === sname); if (!x) secs.push(x = { n: sname, cols: [] }); x.cols.push(c); }
    KP.innerHTML = `<div class="kh"><b>Columns</b><span><button type="button" class="lnk" id="kDef">Default</button> · <button type="button" class="lnk" id="kAll">Show all</button></span></div>` +
      `<p class="kn">${dayMode() ? 'For 1 to 6 days. Weeks and months keep their own choice.' : 'For 7 days or more. Single days keep their own choice.'}</p><div class="kl">` +
      secs.map(x => `<div class="ks"><span class="kt">${esc(x.n)}</span>${x.cols.map(c => `<label><input type="checkbox" data-k="${c.k}"${c.k === 'name' ? ' checked disabled' : XHIDE.has(c.k) ? '' : ' checked'}> ${esc(c.full || c.h)}${c.grp ? ` <span class="mu">(${esc(c.h)})</span>` : ''}${c.only ? ` <span class="mu">(${c.only === 'tree' ? 'Managers and Team leaders views' : 'MEs view'})</span>` : ''}</label>`).join('')}</div>`).join('') + `</div>` +
      `<div class="kb"><button type="button" class="lnk" id="kBands">Band cutoffs…</button></div>`;
    const r = KBTN.getBoundingClientRect();
    KP.hidden = false; KP.style.top = (r.bottom + 6) + 'px';
    // the list scrolls inside the menu, which ends 12 px above the bottom of the window
    const kl = KP.querySelector('.kl'); kl.style.maxHeight = '';
    kl.style.maxHeight = Math.max(160, Math.min(420, innerHeight - r.bottom - 18 - (KP.offsetHeight - kl.offsetHeight))) + 'px';
    KP.style.left = Math.max(8, Math.min(innerWidth - KP.offsetWidth - 8, r.right - KP.offsetWidth)) + 'px';
    KBTN.setAttribute('aria-expanded', 'true');
  }
  function closeCols() { if (KP.hidden) return; KP.hidden = true; KBTN.setAttribute('aria-expanded', 'false'); }
  KBTN.addEventListener('click', () => KP.hidden ? openCols() : closeCols());
  KP.addEventListener('change', ev => {
    const k = ev.target.dataset.k; if (!k) return; ev.target.checked ? XHIDE.delete(k) : XHIDE.add(k); saveX(); renderX();
  });
  KP.addEventListener('click', ev => {
    const id = ev.target.id;
    if (id === 'kAll') { XHIDE.clear(); saveX(); renderX(); openCols(); }
    else if (id === 'kDef') { XHIDE.clear(); (dayMode() ? DAY_HIDE : LONG_HIDE).forEach(k => XHIDE.add(k)); saveX(); renderX(); openCols(); }
    else if (id === 'kBands') { closeCols(); setBd(true); const c = $('#bdCard'); scrollTo(0, c.getBoundingClientRect().top + scrollY - $('#topbar').offsetHeight - 12); }
  });
  document.addEventListener('mousedown', ev => { if (!KP.hidden && !KP.contains(ev.target) && !KBTN.contains(ev.target)) closeCols(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !KP.hidden) closeCols(); });
  // drag a header's right edge to resize that column
  $('#xTbl').addEventListener('mousedown', ev => {
    const h = ev.target.closest('.rz'); if (!h) return;
    ev.preventDefault(); ev.stopPropagation();
    const k = h.dataset.k, cols = [...document.querySelectorAll(`#xTbl col[data-k="${k}"]`)], tbls = [...document.querySelectorAll('#xTbl table')];
    const x0 = ev.clientX, w0 = cols[0].getBoundingClientRect().width || colW(XC[k]), t0 = tbls[0].getBoundingClientRect().width;
    h.classList.add('on'); document.body.classList.add('resizing');
    const move = e => { const w = Math.max(40, Math.round(w0 + e.clientX - x0)), t = (t0 - w0 + w) + 'px'; cols.forEach(c => { c.style.width = w + 'px'; }); tbls.forEach(x => { x.style.width = t; }); XW[wKey(k)] = w; };
    const up = () => { document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up); h.classList.remove('on'); document.body.classList.remove('resizing'); saveX(); };
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  });
  $('#xTbl').addEventListener('dblclick', ev => { const h = ev.target.closest('.rz'); if (!h) return; delete XW[wKey(h.dataset.k)]; saveX(); renderX(); });


  /* ---------- TME -> ME pairings ---------- */
  function renderPairs() {
    const R = CUR, tops = [];
    const best = new Map(); for (const [pk, p] of R.pair) { const tm = Math.floor(pk / NME); if (R.tmN[tm] >= 20) best.set(tm, Math.max(best.get(tm) || 0, p[0])); }
    for (const [tm, v] of best) tops.push(v / R.tmN[tm]);
    const med = median(tops), list = ITEMS.filter(it => it.kind === 'pairing');
    $('#pairSub').innerHTML = tops.length ? `Of ${n0(tops.length)} TMEs with 20+ appointments, the typical one sends <b>${fP(med * 100)}</b> of them to the ME they use most.` : 'Too few TMEs with 20+ appointments in these dates.';
    if (!list.length) { $('#pairs').innerHTML = `<p class="empty">No TME sends an unusual share of their appointments to one ME in these dates.</p>`; return; }
    $('#pairs').innerHTML = `<div class="pr hd"><span>TME (team)</span><span>ME</span><span class="r">Share</span><span class="r">Deals</span></div>` +
      list.map(it => { const p = CUR.pair.get(it.tme * NME + it.me); return `<button type="button" class="pr" data-id="${esc(it.id)}"><span class="nm">${esc(TMES[it.tme][1])}<small>${TME_TEAM[it.tme] >= 0 ? esc(TEAMS[TME_TEAM[it.tme]]) : ''}</small></span><span class="nm">${esc(it.name)}<small>${esc(it.tl)}</small></span>` +
        `<span class="r"><b>${n0(p[0])}</b> of ${n0(CUR.tmN[it.tme])}<small>${fP(pc(p[0], CUR.tmN[it.tme]))}</small></span><span class="r">${n0(p[2])}<small>${fP(CB() ? pc(p[2], p[0]) : pc(p[2], p[1]))} conv.</small></span></button>`; }).join('') +
      `<p class="hint">${esc(CHECKS.pairing.limits)} Click a pair for its appointments.</p>`;
  }
  $('#pairs').addEventListener('click', ev => { const b = ev.target.closest('.pr[data-id]'); if (!b) return; const it = ITEMS.find(x => x.id === b.dataset.id); if (it) openRecords(it); });

  /* ---------- how each check works ---------- */
  function renderHow() {
    $('#howTbl').innerHTML = `<table><thead><tr><th>Check</th><th>Level</th><th>Raised when</th><th>Compared with</th><th>Records used</th><th>What it cannot tell</th></tr></thead><tbody>` +
      KINDS.map(k => { const c = CHECKS[k]; return `<tr data-k="${k}"><td class="nm">${esc(c.label)}</td><td>${esc(c.level)}</td><td>${esc(c.when)}</td><td>${esc(c.vs)}</td><td>${esc(c.recs)}</td><td>${esc(c.limits)}</td></tr>`; }).join('') + `</tbody></table>`;
  }

  /* ---------- drawer ---------- */
  const DR = $('#drawer');
  let lastFocus = null;
  function openDrawer(html) { if (!DR.classList.contains('open')) lastFocus = document.activeElement; $('#drawerBody').innerHTML = html; DR.classList.add('open'); DR.setAttribute('aria-hidden', 'false'); $('#dim').hidden = false; DR.scrollTop = 0; DR.focus({ preventScroll: true }); }
  function closeDrawer() { DR.classList.remove('open'); DR.setAttribute('aria-hidden', 'true'); $('#dim').hidden = true; if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); }
  $('#drawerClose').addEventListener('click', closeDrawer); $('#dim').addEventListener('click', closeDrawer);
  const strip = (o, n) => `<div class="ostrip">${o.map((c, k) => c ? `<span style="flex:${c} 0 0;background:${OC[k]}" title="${OUT[k]}: ${n0(c)}">${c / n >= .08 ? Math.round(c / n * 100) + '%' : ''}</span>` : '').join('')}</div>`;
  const outChip = o => `<span class="ochip"><i style="background:${OC[o]}"></i>${OUT[o]}</span>`;
  function apptRows(filter) { const out = []; for (let i = N - 1; i >= 0; i--) { const d = AD[i]; if (d < V.from || d > V.to || !inScope(i) || !filter(i)) continue; out.push(i); } return out; }
  const FLAG_TXT = [[F.naEarly, 'Not Available updated early'], [F.dealBeforeBooked, 'Dealclosed before allocation'], [F.noBooking, 'No allocation record'], [F.pending, 'Pending 2+ days'], [F.sameDay, 'Same parentid twice that day']];
  const COLDEF = {
    date: ['Date', i => `<span class="tn">${esc(fDate(dOf(AD[i])))}</span>`, i => iso(dOf(AD[i]))],
    biz: ['Company', i => `${esc(CO[i] || '—')}<small class="pid">${esc(PID[i])}</small>`, i => CO[i]],
    me: ['ME', i => `<button type="button" class="lnk" data-me="${AME[i]}">${esc(MES[AME[i]][1])}</button>`, i => MES[AME[i]][1]],
    tme: ['TME (team)', i => `${esc(TMES[ATM[i]][1])} <span class="mu">(${esc(TEAMS[ATT[i]])})</span>`, i => `${TMES[ATM[i]][1]} (${TEAMS[ATT[i]]})`],
    out: ['Disposition', i => outChip(AO[i]), i => OUT[AO[i]]],
    booked: ['Allocated', i => fWhen(ABK[i], AD[i]), i => fWhen(ABK[i], -1)],
    slot: ['Appointment time', i => fWhen(ASL[i], AD[i]), i => fWhen(ASL[i], -1)],
    entered: ['Disposition updated', i => fWhen(AEN[i], AD[i]), i => fWhen(AEN[i], -1)],
    dealt: ['Dealclosed at', i => fWhen(ADC[i], AD[i]), i => fWhen(ADC[i], -1)],
    early: ['How early', i => ASL[i] >= 0 && AEN[i] >= 0 ? `<b>${fGap(ASL[i] - AEN[i])}</b>` : '—', i => ASL[i] >= 0 && AEN[i] >= 0 ? fGap(ASL[i] - AEN[i]) : ''],
    gapBk: ['Dealclosed before allocation by', i => ABK[i] >= 0 && ADC[i] >= 0 ? `<b>${fGap(ABK[i] - ADC[i])}</b>` : '—', i => ABK[i] >= 0 && ADC[i] >= 0 ? fGap(ABK[i] - ADC[i]) : ''],
    since: ['Days since', i => n0(LAST - AD[i]), i => LAST - AD[i]],
    flags: ['Checks', i => FLAG_TXT.filter(([b]) => AF[i] & b).map(([, t]) => `<span class="ftag">${t}</span>`).join(' ') || '<span class="mu">—</span>', i => FLAG_TXT.filter(([b]) => AF[i] & b).map(([, t]) => t).join('; ')],
  };
  let LIST = null;
  function apptTable(idx, cols, limit = 200) {
    LIST = { idx, cols };
    return `<div class="dlw"><table class="dl"><thead><tr>${cols.map(c => `<th>${COLDEF[c][0]}</th>`).join('')}</tr></thead><tbody>` +
      idx.slice(0, limit).map(i => `<tr>${cols.map(c => `<td>${COLDEF[c][1](i)}</td>`).join('')}</tr>`).join('') +
      `</tbody></table></div>${idx.length > limit ? `<p class="hint">Latest ${limit} of ${n0(idx.length)}; the CSV has them all.</p>` : ''}` +
      (idx.length ? `<button type="button" class="btn" id="listCsv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV of these ${n0(idx.length)}</button>` : '<p class="empty">No records in these dates.</p>');
  }
  $('#drawerBody').addEventListener('click', ev => {
    if (ev.target.closest('#dealsCsv') && DLIST) return download(`ME_deals_closed${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['Date', 'parentid', 'Company', 'ME code', 'ME', 'TME team', 'Deal (dc_genio)'], ...DLIST.map(j => [iso(dOf(DLD[j])), DLPID[j] || '', CO_OF.get(DLPID[j]) || '', MES[DLME[j]][0], MES[DLME[j]][1], TEAMS[DLT[j]], DLW[j]])]);
    if (ev.target.closest('#listCsv') && LIST) return download(`ME_records${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`, [['parentid', ...LIST.cols.map(c => COLDEF[c][0])], ...LIST.idx.map(i => [PID[i], ...LIST.cols.map(c => COLDEF[c][2](i))])]);
    const it = ev.target.closest('[data-item]'); if (it) { const x = ITEMS.find(y => y.id === it.dataset.item); if (x) return openRecords(x); }
    const chk = ev.target.closest('[data-chk]'); if (chk) { const x = ITEMS.find(y => y.id === chk.dataset.chk); if (x) { if (MARKS[x.id]) delete MARKS[x.id]; else MARKS[x.id] = new Date().toISOString().slice(0, 10); saveMarks(); renderBand(); renderQueue(); renderList(); chk.setAttribute('aria-pressed', String(!!MARKS[x.id])); chk.innerHTML = MARKS[x.id] ? ICON.done + 'Checked' : 'Mark checked'; } return; }
    const tg = ev.target.closest('[data-tg]'); if (tg) return meTeam(+tg.dataset.tg);
    // an ME picked inside a TME team's window opens on that team's appointments
    const tr = ev.target.closest('[data-me]'); if (tr) openMe(+tr.dataset.me, tr.dataset.g !== undefined ? +tr.dataset.g : -1);
  });
  function openRecords(it) {
    const idx = apptRows(recFilter(it)), r = MEROWS.find(x => x.me === it.me), done = isDone(it);
    openDrawer(`<p class="kicker"><span class="tag ${done ? 'ok' : it.sev}">${done ? ICON.done : ICON[it.sev]}${done ? 'Checked' : it.sev === 'rev' ? 'Review' : 'Information'}</span></p>` +
      `<h2 id="drawerH" class="dt">${esc(CHECKS[it.kind].label)}</h2>` +
      `<p class="where">${it.me < 0 ? esc(it.name) : `<button type="button" class="lnk" data-me="${it.me}">${esc(it.name)}</button>`}${it.tme !== undefined ? ` · from TME ${esc(TMES[it.tme][1])}` : ''}${it.tl ? ` · team leader ${esc(it.tl)}` : ''}<br>${esc(scopeName())} · ${esc(fRange(V.from, V.to))}</p>` +
      `<p class="whyd">${it.why}</p>${cmpBars(it.cmp)}` +
      `<div class="howbox"><b>Why it was raised.</b> ${esc(CHECKS[it.kind].when)} <b>Compared with:</b> ${esc(CHECKS[it.kind].vs)} <b>Keep in mind:</b> ${esc(CHECKS[it.kind].limits)}</div>` +
      `<div class="dact"><button type="button" class="btn chk" data-chk="${esc(it.id)}" aria-pressed="${done}">${done ? ICON.done + 'Checked' : 'Mark checked'}</button>${r && it.me >= 0 ? `<button type="button" class="btn" data-me="${it.me}">Open ${esc(shortName(it.name))}'s page</button>` : ''}</div>` +
      `<h3>The ${n0(idx.length)} ${recWord(it)}</h3><p class="cmpn">parentid under each company, to look it up${it.me < 0 ? '; click an ME for their page' : ''}.</p>${apptTable(idx, (REC_COLS[it.kind] || ['date', 'biz', 'tme', 'out']).flatMap(c => c === 'biz' && it.me < 0 ? ['biz', 'me'] : [c]))}`);
  }
  // three steps for one ME (or team) against the whole city (also when the dashboard shows one team)
  function miniFlow(n, a, d, sub) {
    const R = CITY, ta = att(R.o);
    const st = (v, l, s) => `<div class="mstep"><div class="mv tn">${v}</div><div class="ml2">${l}</div><div class="ms">${s}</div></div>`;
    return `<div class="mflow">${st(n0(n), 'appointments given', sub || '')}${ARROW}${st(n0(a), 'attended', `<b>${pct0(a, n)}</b> · ${esc(META.city)} ${pct0(ta, R.n)}`)}${ARROW}${d === null ? st('—', 'deals closed', AWAY_TXT) : st(n0(d), 'deals closed', `<b>${pct0(d, CB() ? n : a)}</b> ${CVOF()} · ${esc(META.city)} ${pct0(R.dl, CB() ? R.n : ta)}`)}</div>`;
  }
  const dispLines = o => `<p class="dline"><b>Attended ${n0(o[0] + o[1] + o[2])}:</b> ${n0(o[0])} Dealclosed · ${n0(o[1])} Follow Up · ${n0(o[2])} Not Interested</p>` +
    `<p class="dline"><b>Not attended ${n0(o[3] + o[4] + o[5])}:</b> ${n0(o[3])} Not Available · ${n0(o[4])} Pending · ${n0(o[5])} Not Visited</p>`;
  // the ME's appointments, all or one TME team's (picked in "By TME team"; preset when the ME was opened from that team)
  let ME_CUR = -1;
  function meDet(me, gs, open) {
    const list = apptRows(i => AME[i] === me && (gs < 0 || GROUP_OF[ATT[i]] === gs)), o = [0, 0, 0, 0, 0, 0];
    list.forEach(i => { o[AO[i]]++; });
    return `<details class="appts"${open ? ' open' : ''}><summary>See the ${n0(list.length)} ${gs < 0 ? '' : esc(GROUPS[gs]) + ' '}appointment${list.length === 1 ? '' : 's'}</summary>` +
      (gs >= 0 && list.length ? dispLines(o) : '') +
      (list.length || gs < 0 ? apptTable(list, ['date', 'biz', 'tme', 'slot', 'entered', 'out', ...(V.view === 'checks' ? ['flags'] : [])])
        : `<p class="empty">No ${esc(GROUPS[gs])} appointments in these dates.</p>`) + `</details>`;
  }
  function meTeam(gs) {
    document.querySelectorAll('#meTeams [data-tg]').forEach(b => b.setAttribute('aria-pressed', String(+b.dataset.tg === gs)));
    const d = $('#meDet'); if (d) d.innerHTML = meDet(ME_CUR, gs, true);
  }
  function openMe(me, gsel = -1) {
    const r = MEROWS.find(x => x.me === me); if (!r) return;
    ME_CUR = me;
    const R = CUR, city = cityGroups(R), g = groupsOf(R, me), pr = PREVROWS.get(me), mine = ITEMS.filter(it => it.me === me);
    const ncK = new Map(); for (let i = 0; i < NCN; i++) if (NCME[i] === me && NCD[i] >= V.from && NCD[i] <= V.to) ncK.set(NCK[i], (ncK.get(NCK[i]) || 0) + 1);
    const wk = Array.from({ length: Math.floor(LAST / 7) + 1 }, () => [0, 0, 0]);
    for (let i = 0; i < N; i++) if (AME[i] === me) { const w = Math.floor(AD[i] / 7); wk[w][0]++; if (AO[i] >= 3) wk[w][2]++; }
    for (let j = 0; j < DLN; j++) if (DLME[j] === me) wk[Math.floor(DLD[j] / 7)][1] += DLW[j];   // deals closed (Sales MIS rule)
    const mx = Math.max(1, ...wk.map(x => Math.max(x[0], x[1]))), Wd = 500, Hd = 90, bw = Wd / wk.length;
    const spark = `<svg width="100%" viewBox="0 0 ${Wd} ${Hd}" preserveAspectRatio="none" style="height:${Hd}px" role="img" aria-label="Appointments per week since April">${wk.map((v, w) => { const op = w * 7 + 6 >= V.from && w * 7 <= V.to ? 1 : .4; const h = v[0] / mx * (Hd - 4), hm = v[2] / mx * (Hd - 4), hd = v[1] / mx * (Hd - 4); return `<rect x="${(w * bw).toFixed(1)}" y="${(Hd - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="#9DB7D6" opacity="${op}"/><rect x="${(w * bw).toFixed(1)}" y="${(Hd - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${hm.toFixed(1)}" fill="#E3C27D" opacity="${op}"/><rect x="${(w * bw).toFixed(1)}" y="${(Hd - hd).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${hd.toFixed(1)}" fill="#12875F" opacity="${op}"/>`; }).join('')}</svg>`;
    const items = mine.length ? `<ul class="mitems">${mine.map(it => { const done = isDone(it); return `<li class="${it.sev}${done ? ' done' : ''}"><span class="tag ${done ? 'ok' : it.sev}">${done ? ICON.done : ICON[it.sev]}${done ? 'Checked' : it.sev === 'rev' ? 'Review' : 'Info'}</span><div><b>${esc(CHECKS[it.kind].label)}</b><p>${it.why}</p></div><button type="button" class="btn" data-item="${esc(it.id)}">See ${plural(it.n, recWord(it).replace(/s$/, ''), recWord(it))}</button></li>`; }).join('')}</ul>` : `<p class="okline">${ICON.done} No check was raised for this ME in these dates.</p>`;
    const prevLine = pr && pr.n && r.n ? `<p class="dline mu">${esc(prevName())}: ${n0(pr.n)} appointments given, ${fP(pr.attP)} attended, ${plural(pr.deals, 'deal')} closed.</p>` : '';
    openDrawer(`<h2 id="drawerH">${esc(r.name)}</h2><p class="where">ME code ${esc(r.code)}${r.lead >= 0 && r.lead === r.node ? (DEPTH[r.lead] === 2 ? ` · Team leader, under manager ${esc(r.mgr)}` : DEPTH[r.lead] === 1 ? ` · Manager under ${esc(HEADNAME)}` : ' · ME head')
        : `${r.tl ? ` · Team leader ${esc(r.tl)}` : ''}${r.mgr ? ` · ${r.node === OUTN ? esc(r.mgr) : `Manager ${esc(r.mgr)}`}` : ''}`}${r.des ? ` · ${esc(r.des)}` : ''}${r.city ? ` · based in ${esc(r.city)}` : ''}${HRJ[me] ? ` · ${esc(tenure(HRJ[me]))}` : ''}<br>${esc(periodName())}</p>` +
      (V.view === 'checks' ? `<h3>Checks for this ME</h3>${items}` : '') +
      miniFlow(r.n, r.att, r.away ? null : r.deals, r.pd !== null ? `${r.pd} days present` : '') + prevLine +
      (r.away ? `<p class="dline mu">An ME of another city: the Sales MIS counts their deals closed in that city, so none show here.</p>` : '') +
      (r.n >= MINR ? '' : `<p class="dline mu">Fewer than ${MINR} appointments in these dates: percentages swing a lot.</p>`) +
      `<h3>By TME team</h3><p class="cmpn">Click a team to list only its appointments below.</p>` +
      `<div class="mlist" id="meTeams">${MHEAD}${GROUPS.map((l, i) => g[i][0]
        ? `<button type="button" class="srow tsel" data-tg="${i}" aria-pressed="${gsel === i}" title="List only the ${esc(l)} appointments">${mrow(esc(l), g[i])}</button>`
        : `<div class="srow">${mrow(esc(l), g[i])}</div>`).join('')}` +
      `<button type="button" class="srow tsel tall" data-tg="-1" aria-pressed="${gsel < 0}" title="List all the appointments">${mrow('All teams', g.reduce((s, x) => [s[0] + x[0], s[1] + x[1], s[2] + x[2]], [0, 0, 0]), 'tot')}</button></div>` +
      `<p class="hint">${esc(META.city)}, attended: ${GROUPS.map((l, i) => `${esc(l)} ${pct0(city[i][1], city[i][0])}`).join(' · ')}.</p>` +
      `<div id="meDet">${meDet(me, gsel, gsel >= 0)}</div>` +
      `<h3>Dispositions</h3>${dispLines(r.o)}` +
      (r.nc ? `<p class="dline mu">Also ${n0(r.nc)} Not Counted/Cancelled: ${[...ncK.entries()].sort((a, b) => b[1] - a[1]).map(([k, c]) => `${n0(c)} ${esc(NC.kinds[k])}`).join(' · ')}</p>` : '') +
      `<h3>Week by week since April</h3>${spark}<div class="okey"><span><i style="background:#12875F"></i>deals closed</span><span><i style="background:#9DB7D6"></i>attended, no deal closed</span><span><i style="background:#E3C27D"></i>not attended</span><span class="mu">faded = outside the dates</span></div>`);
  }
  // a team group: Super Cat or Hot Data (one TME team each), or all the other teams together
  function openGroup(gi) {
    const R = CUR, teams = teamRows(R).filter(t => GROUP_OF[t.t] === gi), city = cityGroups(R), x = city[gi];
    const o = [0, 0, 0, 0, 0, 0]; teams.forEach(t => t.o.forEach((v, k) => { o[k] += v; }));
    const rows = MEROWS.map(r => ({ r, g: groupsOf(R, r.me)[gi] })).filter(y => y.g[0] > 0 || y.g[2] > 0).sort((a, b) => b.g[0] - a.g[0] || b.g[2] - a.g[2]);
    openDrawer(`<h2 id="drawerH">${esc(GROUPS[gi])}</h2><p class="where">TME team${teams.length > 1 ? 's' : ''} · ${esc(periodName())}</p>` +
      miniFlow(x[0], x[1], x[2], `${pct0(x[0], R.n)} of all`) +
      (teams.length > 1 ? `<h3>The teams in it</h3><div class="mlist">${MHEAD}${teams.map(t => mrow(t.n ? esc(t.name) : `<span title="Deals closed with no appointment behind them">${esc(t.name)}</span>`, [t.n, t.a, t.d])).join('')}</div>` : '') +
      `<h3>Dispositions</h3>${dispLines(o)}` +
      `<h3>Which MEs took them</h3><p class="cmpn">${plural(rows.length, 'ME')}. Click one for their page.</p><div class="mlist">${MHEAD.replace('TME team', 'ME')}${rows.slice(0, 40).map(y => `<button type="button" class="srow" data-me="${y.r.me}" data-g="${gi}">${mrow(esc(y.r.name), y.g)}</button>`).join('')}</div>` +
      (rows.length > 40 ? `<p class="hint">Top 40 of ${n0(rows.length)} MEs.</p>` : ''));
  }
  const openTeam = t => openGroup(GROUP_OF[t]);


  // the deals closed in the dates (the deal records, Sales MIS rule), opened from the band's deals bar (2026-10-15)
  const CO_OF = new Map(); for (let i = 0; i < N; i++) if (CO[i] && !CO_OF.has(PID[i])) CO_OF.set(PID[i], CO[i]);
  let DLIST = null;
  function openDeals() {
    const idx = []; for (let j = DLN - 1; j >= 0; j--) { const d = DLD[j]; if (d >= V.from && d <= V.to && SMASK[DNODE[j]]) idx.push(j); }
    const tot = idx.reduce((t, j) => t + DLW[j], 0), part = idx.some(j => DLW[j] !== 1), lim = 300;
    DLIST = idx;
    const row = j => `<tr><td><span class="tn">${esc(fDate(dOf(DLD[j])))}</span></td><td>${esc(CO_OF.get(DLPID[j]) || '—')}<small class="pid">${esc(DLPID[j] || '')}</small></td>` +
      `<td><button type="button" class="lnk" data-me="${DLME[j]}">${esc(MES[DLME[j]][1])}</button></td><td>${esc(TEAMS[DLT[j]])}</td>${part ? `<td class="tn">${DLW[j]}</td>` : ''}</tr>`;
    openDrawer(`<h2 id="drawerH" class="dt">Deals closed</h2><p class="where">${n0(tot)} deals closed · ${esc(scopeName())} · ${esc(fRange(V.from, V.to))}</p>` +
      `<p class="dline mu">As the Sales MIS counts them: each deal in the deals table (one per payment version) by a ${esc(META.city)} ME, with or without an appointment behind it.${part ? ' Deal = dc_genio (a half deal is 0.5).' : ''}</p>` +
      (idx.length ? `<div class="dlw"><table class="dl"><thead><tr><th>Date</th><th>Company</th><th>ME</th><th>TME team</th>${part ? '<th>Deal</th>' : ''}</tr></thead><tbody>${idx.slice(0, lim).map(row).join('')}</tbody></table></div>` +
        (idx.length > lim ? `<p class="hint">Latest ${lim} of ${n0(idx.length)}; the CSV has them all.</p>` : '') +
        `<button type="button" class="btn" id="dealsCsv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV of these ${n0(idx.length)}</button>` : '<p class="empty">No deals closed in these dates.</p>'));
  }
  function openList(f) {
    const filt = i => (f.o === undefined || AO[i] === f.o) && (f.me === undefined || AME[i] === f.me) && (f.t === undefined || ATT[i] === f.t);
    const idx = apptRows(filt);
    const title = [f.o !== undefined ? OUT[f.o] : 'Appointments', f.me !== undefined ? MES[f.me][1] : '', f.t !== undefined ? TEAMS[f.t] : ''].filter(Boolean).join(' · ');
    openDrawer(`<h2 id="drawerH" class="dt">${esc(title)}</h2><p class="where">${n0(idx.length)} appointments · ${esc(scopeName())} · ${esc(fRange(V.from, V.to))}</p>` +
      (f.me !== undefined ? `<div class="dact"><button type="button" class="btn" data-me="${f.me}">Open ${esc(shortName(MES[f.me][1]))}'s page</button></div>` : '') +
      `<h3>The appointments</h3>${apptTable(idx, ['date', 'biz', ...(f.me === undefined ? ['me'] : []), 'tme', 'slot', 'entered', 'out', ...(V.view === 'checks' ? ['flags'] : [])])}`);
  }

  /* ---------- period: one button with ready-made periods + any dates (as on the India sales overview) ---------- */
  const PP = $('#periodPop'), PBTN = $('#periodBtn');
  function closePops() { if (PP.hidden) return; PP.hidden = true; PBTN.setAttribute('aria-expanded', 'false'); }
  function renderPills() {
    const pre = PRESETS.find(x => x.k === V.preset);
    const one = V.from === V.to;
    $('#periodLabel').innerHTML = (pre && !one ? `<span class="pl-pre">${esc(pre.label.replace('Financial year', 'FY').replace(' (provisional)', ''))} · </span>` : '') + esc(one ? dayName(V.from) : fRange(V.from, V.to)) + (one && isProv(V.from) ? ' <span class="pl-prov">provisional</span>' : '');
    $('#dayPrev').hidden = $('#dayNext').hidden = !one;
    $('#dayPrev').disabled = prevDay(V.from) === null; $('#dayNext').disabled = nextDay(V.from) === null;
    document.querySelectorAll('#viewSw button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.view === V.view)));
    document.querySelectorAll('#cbSw button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.cb === V.cb)));
    document.querySelectorAll('#hoSw button').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.v === '1') === XMERGE)));
    document.querySelectorAll('#exSw button').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.v === '1') === XEXP)));
  }
  function openPop() {
    PP.innerHTML = PRESETS.map(p => `<button type="button" class="pre" data-k="${p.k}" aria-pressed="${V.preset === p.k}"><span>${esc(p.label)}</span><small>${esc(fRange(p.a, p.b))}</small></button>`).join('') +
      `<div class="custom"><label>From<input type="date" id="pFrom" min="${META.fy}" max="${META.end}" value="${iso(dOf(V.from))}"></label><label>To<input type="date" id="pTo" min="${META.fy}" max="${META.end}" value="${iso(dOf(V.to))}"></label><span class="err" id="pErr"></span><button type="button" class="btn" id="pApply">Show these dates</button></div>`;
    const r = PBTN.getBoundingClientRect();
    PP.hidden = false;
    PP.style.top = (r.bottom + 8) + 'px'; PP.style.left = Math.max(8, Math.min(innerWidth - PP.offsetWidth - 8, r.right - PP.offsetWidth)) + 'px';
    PBTN.setAttribute('aria-expanded', 'true');
    (PP.querySelector('[aria-pressed="true"]') || PP.querySelector('button')).focus();
  }
  PBTN.addEventListener('click', () => PP.hidden ? openPop() : closePops());
  PP.addEventListener('click', ev => {
    const b = ev.target.closest('button.pre'); if (b) { setPreset(b.dataset.k); closePops(); return render(true); }
    if (ev.target.id === 'pApply') {
      const a = offOf($('#pFrom').value), z = offOf($('#pTo').value);
      if (!isFinite(a) || !isFinite(z)) return void ($('#pErr').textContent = 'Pick both dates.');
      if (a > z) return void ($('#pErr').textContent = 'The start date is after the end date.');
      if (a < 0 || z > LAST) return void ($('#pErr').textContent = `Pick dates from ${fDate(dOf(0), true)} to ${fDate(dOf(LAST), true)}.`);
      const p = PRESETS.find(x => x.a === a && x.b === z);
      if (p) setPreset(p.k);
      else setRange(a, z);
      closePops(); render(true);
    }
  });
  document.addEventListener('mousedown', ev => { if (!PP.hidden && !PP.contains(ev.target) && !PBTN.contains(ev.target)) closePops(); });
  const TP = $('#tlPop'), TBTN = $('#tlBtn');
  function renderTl() {
    const t = scoped() ? NNAME(V.scope) : 'All teams';
    $('#tlLabel').textContent = t;
    TBTN.title = scoped() ? `${t} (${ROLE(V.scope)}): the whole dashboard shows only this team` : 'Show one manager\'s or team leader\'s team';
    TBTN.setAttribute('aria-label', 'Team: ' + t); TBTN.classList.toggle('on', scoped());
    $('#tlClear').hidden = !scoped();
  }
  $('#tlClear').addEventListener('click', () => setScope(ROOT));
  // settings (gear): the conversion switch
  const SP = $('#setPop'), SBTN = $('#setBtn');
  const closeSet = () => { if (SP.hidden) return; SP.hidden = true; SBTN.setAttribute('aria-expanded', 'false'); };
  SBTN.addEventListener('click', () => {
    if (!SP.hidden) return closeSet();
    SP.hidden = false; const r = SBTN.getBoundingClientRect();
    SP.style.top = (r.bottom + 8) + 'px'; SP.style.left = Math.max(8, Math.min(innerWidth - SP.offsetWidth - 8, r.right - SP.offsetWidth)) + 'px';
    SBTN.setAttribute('aria-expanded', 'true'); (SP.querySelector('[aria-pressed="true"]') || SP.querySelector('button')).focus();
  });
  document.addEventListener('mousedown', ev => { if (!SP.hidden && !SP.contains(ev.target) && !SBTN.contains(ev.target)) closeSet(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !SP.hidden) { closeSet(); SBTN.focus(); } });
  function closeTl() { if (TP.hidden) return; TP.hidden = true; TBTN.setAttribute('aria-expanded', 'false'); }
  // the team picker: every manager under the ME head with their team leaders below them, with the appointments and MEs of
  // each team in the dates (a team includes everyone below it). Teams with no appointment in the last 60 days are left out.
  function teamCounts() {
    const n = new Float64Array(NMG + 1), mes = new Map();
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < V.from || d > V.to) continue;
      for (let c = ANODE[i], g = 0; c >= 0 && g < 6; g++) { n[c]++; let s = mes.get(c); if (!s) mes.set(c, s = new Set()); s.add(AME[i]); if (c === ROOT) break; c = UPN(c); }
    }
    return { n, k: m => mes.has(m) ? mes.get(m).size : 0 };
  }
  function openTl() {
    closePops();
    const C = teamCounts(), show = m => RECENT[m] || C.n[m] || V.scope === m, byName = (a, b) => NNAME(a).localeCompare(NNAME(b));
    const item = (m, cls) => `<button type="button" class="pre ${cls}" data-tl="${m}" data-n="${esc(NNAME(m).toLowerCase())}" aria-pressed="${V.scope === m}"><span>${esc(NNAME(m))}</span><small${C.n[m] ? '' : ' class="none"'}>${ROLE(m)} · ${C.n[m] ? `${plural(C.k(m), 'ME')} · ${n0(C.n[m])} appts` : 'no appointments'}</small></button>`;
    const L = KIDS[ROOT].filter(m => m !== OUTN && show(m)).sort(byName).map(m => item(m, 'p1') + KIDS[m].filter(show).sort(byName).map(t => item(t, 'p2')).join('')).join('');
    TP.innerHTML = `<label class="search tls"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input type="search" id="tlFind" placeholder="Find a manager or team leader" autocomplete="off"></label>` +
      `<div class="tll"><button type="button" class="pre p0" data-tl="${ROOT}" aria-pressed="${!scoped()}"><span>All teams</span><small>${esc(HEADNAME)} · ${plural(C.k(ROOT), 'ME')} · ${n0(C.n[ROOT])} appts</small></button>${L}</div>`;
    const r = TBTN.getBoundingClientRect();
    TP.hidden = false;
    TP.style.top = (r.bottom + 8) + 'px'; TP.style.left = Math.max(8, Math.min(innerWidth - TP.offsetWidth - 8, r.right - TP.offsetWidth)) + 'px';
    TBTN.setAttribute('aria-expanded', 'true');
    $('#tlFind').focus();
  }
  TBTN.addEventListener('click', () => TP.hidden ? openTl() : closeTl());
  TP.addEventListener('input', ev => { if (ev.target.id !== 'tlFind') return; const q = ev.target.value.trim().toLowerCase(); TP.querySelectorAll('[data-n]').forEach(b => { b.hidden = !!q && !b.dataset.n.includes(q); }); });
  TP.addEventListener('click', ev => { const b = ev.target.closest('[data-tl]'); if (!b) return; closeTl(); setScope(+b.dataset.tl); });
  document.addEventListener('mousedown', ev => { if (!TP.hidden && !TP.contains(ev.target) && !TBTN.contains(ev.target)) closeTl(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && !TP.hidden) closeTl(); });
  $('#cbSw').addEventListener('click', ev => { const b = ev.target.closest('[data-cb]'); if (b && b.dataset.cb !== V.cb) { V.cb = b.dataset.cb; render(true); } });
  $('#hoSw').addEventListener('click', ev => { const b = ev.target.closest('[data-v]'); if (b) setGrouping(b.dataset.v === '1', XEXP); });
  $('#exSw').addEventListener('click', ev => { const b = ev.target.closest('[data-v]'); if (b) setGrouping(XMERGE, b.dataset.v === '1'); });
  $('#viewSw').addEventListener('click', ev => { const b = ev.target.closest('[data-view]'); if (b && b.dataset.view !== V.view) setView(b.dataset.view); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape') { if (!PP.hidden) closePops(); else if (DR.classList.contains('open')) closeDrawer(); } });
  $('#home').addEventListener('click', ev => { ev.preventDefault(); setView('team'); });
  $('#toChecks').addEventListener('click', () => setView('checks'));
  $('#backBtn').addEventListener('click', () => setView('team'));

  /* ---------- link state ---------- */
  function writeHash() {
    const h = new URLSearchParams();
    if (V.view !== 'table') h.set('view', V.view);   // the Table page is the default (the ME Head works there)
    if (scoped() && V.scope !== OUTN) h.set('team', MGRS[V.scope][0]);
    if (V.cb === 'given') h.set('cb', 'given');
    if (V.preset && V.preset !== DEFAULT_P.k) h.set('period', V.preset); else if (!V.preset) { h.set('from', iso(dOf(V.from))); h.set('to', iso(dOf(V.to))); }
    const s = h.toString(); history.replaceState(null, '', s ? '#' + s : location.pathname);
  }
  function setRange(a, z) {
    if (a === z) { const p = prevNormal(a); Object.assign(V, { from: a, to: z, preset: null, pa: p, pb: p, pl: p === null ? '' : dayName(p) }); return; }
    const len = z - a + 1, pa = a - len;
    Object.assign(V, { from: a, to: z, preset: null, pa: pa >= 0 ? pa : null, pb: pa >= 0 ? a - 1 : null, pl: '' });
  }
  function stepDay(dir) {
    const t = dir < 0 ? prevDay(V.from) : nextDay(V.from); if (t === null) return;
    const p = PRESETS.find(x => x.a === t && x.b === t);
    if (p) setPreset(p.k); else setRange(t, t);
    render(true);
  }
  $('#dayPrev').addEventListener('click', () => stepDay(-1));
  $('#dayNext').addEventListener('click', () => stepDay(1));
  function readHash() {
    const h = new URLSearchParams(location.hash.slice(1));
    if (['checks', 'table', 'team'].includes(h.get('view'))) V.view = h.get('view');
    if (h.get('cb') === 'given') V.cb = 'given';
    const tc = h.get('team') || h.get('tl');   // tl: links from before the hierarchy (a team leader) open that team
    if (tc) { const m = MGRS.findIndex(x => String(x[0]) === tc); if (m >= 0 && DEPTH[m] >= 0) V.scope = TEAMOF[m]; }
    if (h.has('period')) setPreset(h.get('period'));
    else if (h.has('from') && h.has('to')) { const a = offOf(h.get('from')), z = offOf(h.get('to')); if (a >= 0 && z <= LAST && a <= z) setRange(a, z); }
  }


  /* ---------- notes ---------- */
  function renderNotes() {
    const c = META.check, ds = META.dealSrc || {};
    $('#notes').innerHTML = [
      `<p><b>Appointments.</b> datagrowth.tbl_final_data_appt (server 240), ${esc(META.city)}: appointments given to MEs, counted as the Sales MIS counts them (jda_flag 0 and 3; every appointment with a real disposition, including those a BDE set, which the table marks given_count 0; MEs in team Corporate or section Sales (Training) are left out; a Sunday appointment counts on the Saturday before), 1 April to ${esc(fDate(dOf(LAST), true))}; refreshed ${esc(META.refreshed.replace('T', ' at '))}. The date is the appointment's to_date. An appointment counts for the ME it was finally allocated to; the table keeps no earlier allocation.</p>`,
      `<p><b>Attended</b> = disposition Dealclosed, Follow Up or Not Interested. <b>Not attended</b> = Not Available, Pending (no disposition yet) or Not Visited. <b>Conversion</b> = deals closed ÷ ${CB() ? 'appointments given' : 'attended'} (switch at the top: Conversion on Attended / Given). <b>Not Counted/Cancelled</b> = appointments with that disposition (Not Available (Online), TME Cancelled, Fake Appt, Details Incorrect, Appointment Refixed…); they are shown per ME, not added to appointments.</p>`,
      ds.mis !== undefined
        ? `<p><b>Deals closed</b> are counted as the Sales MIS counts them (JDS-ME): every deal row in the deals table (db_paidcontracts.daily_deals_closed_dump, server 216; one row per payment version, dc_genio) with jda_flag 0 or 3 and an ME, whose ME was a ${esc(META.city)} ME that month (tbl_working_days_final_data: city, emptype ME, team not Corporate / JDA; else the HR city), on the deal date (dealclosed_date; the table books Sunday deals on Saturday). A deal counts whether or not an appointment sits behind it: deals with no TME are under the TME team 'Cold call (no TME)', a top-up payment the next day is a deal that day. Each deal is with its ME and the ME's team leader that month, and with the deal's TME team (final_team_type_name).${ds.misTo && ds.misTo < iso(dOf(LAST)) ? ` The deals table runs to ${esc(fDate(new Date(ds.misTo + 'T00:00:00Z'), true))}; later days use the appointments with disposition Dealclosed until it has them.` : ''} So an ME can have deals closed on a day with no appointment, and conversion (deals closed ÷ ${CB() ? 'appointments given' : 'attended'}) can pass 100% on a few appointments.</p>` +
          `<p><b>Dealclosed</b> (in Dispositions and the appointment lists) is the appointment's own disposition, checked against the same deals table: an appointment is Dealclosed when its docid has a deal that day (a Saturday deal also counts for the next day or two); ${n0(ds.toDeal)} not marked Dealclosed in the appointment table had a deal, ${n0(ds.fromDeal)} marked Dealclosed there had no deal of their own and count with Follow Up.</p>`
        : `<p><b>Deals closed</b> are the appointments with disposition Dealclosed (the deals table was not read on this refresh).</p>`,
      `<p><b>Comparisons.</b> A single day is compared with the previous usual day. A low day (fewer than 40% of a usual day's appointments given in ${esc(META.city)}, about ${n0(Math.round(USUAL * 0.4))}; a holiday or a short day) is named under the heading when either set of dates has one, as the changes are then not like for like. <b>Green / red</b> in Your team: 10+ points from the line above for 1–6 days, 5+ points for 7 days or more; smaller gaps stay grey.</p>`,
      `<p><b>Across managers</b> (band, right): the lowest and highest attended % and conversion among the teams one level below the team shown (managers, team leaders, or MEs in a team leader's team), counting teams with 10+ appointments given (MEs: ${MINR}+), and who has the most Not Available. <b>The trend</b> under it: attended % and conversion each usual day of the last 4 weeks (or each week of the last 12 weeks, for 7 days or more), up to the last day shown, for the team shown; days with fewer than 5 appointments are left out.</p>`,
      `<p><b>MEs of another city</b> (their HR city that month is not ${esc(META.city)}; most sit in "${esc(OUT_NAME)}") take ${esc(META.city)} appointments, which count here, but the Sales MIS counts their deals closed in their own city, so they show "—" for deals closed and conversion.</p>`,
      `<p><b>Times.</b> Allocated = allocationtime (when the appointment was allocated to the ME); appointment time = actiontime; disposition updated = attended_date; Dealclosed at = dealclosed_date. Deals with no allocation record have no allocationtime and an appointment time equal to the Dealclosed time.</p>`,
      `<p><b>Days present, designation, home city, joining date</b>: HR (db_paidcontracts.tbl_working_days_final_data and hr_all_daily_copy_ganesh, server 216)${META.hrPulled ? `, read ${esc(META.hrPulled)}` : ''}. Part months count pro rata.</p>`,
      `<p><b>Teams.</b> ${esc(HEADNAME)} (ME head) > managers > team leaders > MEs, from HR's reporting lines: each person's usual manager on their appointments since 1 April, until the official list is in. A team leader's or manager's own appointments count in their own team (tagged TL / Manager); "direct" = an ME who reports to a manager with no team leader. Anyone further down a chain counts in their team leader's team. An ME counts in the team where most of their appointments in the dates sit. "${esc(OUT_NAME)}" = MEs whose HR reporting line does not reach ${esc(HEADNAME)} (mostly MEs of other cities taking a Mumbai appointment).</p>`,
      `<p><b>Expected</b> (TME team mix) applies the rate of ${esc(scopeName())} for each TME team to the ME's appointments, so an ME fed harder or easier leads is judged fairly. Rates need ${MIN}+ appointments. On the Checks view, <b>checked</b> marks are saved in this browser only, for these exact dates.</p>`,
      `<p><b>Check.</b> ${n0(c.given)} appointments, ${n0(c.attended)} attended, ${n0(c.deals)} deals closed in the data${c.left_out ? `; ${n0(c.left_out)} left out (disposition not one of the six)` : ''}.</p>`,
    ].join('');
  }

  /* ---------- render ---------- */
  function render(push) {
    untip(); closePops(); ITEM_TEAMS.clear();
    MINR = minFor(V.to - V.from + 1);
    setMask();
    CUR = agg(V.from, V.to); PREV = agg(V.pa, V.pb);
    CITY = !scoped() ? CUR : (() => { const s = V.scope; V.scope = ROOT; setMask(); const r = agg(V.from, V.to); V.scope = s; setMask(); return r; })();
    BASE = V.from > 0 ? agg(Math.max(0, V.from - 90), V.from - 1) : null;
    MEROWS = rowsOfMes(CUR);
    const prevRows = rowsOfMes(PREV);
    PREVROWS = new Map(prevRows.map(r => [r.me, r]));
    ITEMS = computeItems(CUR, MEROWS, BASE);
    PREV_IDS = new Set(V.pa !== null && PREV.n ? computeItems(PREV, prevRows, V.pa > 0 ? agg(Math.max(0, V.pa - 90), V.pa - 1) : null).map(it => it.kind + '|' + it.subj) : []);
    showViews(); closeCol();
    document.body.classList.toggle('nodata', !CUR.n && !CUR.dl);
    renderTl(); renderBand(); renderLadder(); renderTeams(); renderList(); renderX(); renderQueue(); renderPairs(); renderHow(); renderNotes();
    document.title = `${META.city} · ME team`;
    if (push) writeHash();
  }
  /* ---------- a small inside joke (requested 2026-10-12): a subtle, monochrome spa mark after one ME's name ---------- */
  const SPA_RE = /karan krishna gaikwad/i;
  const SPA_SVG = '<svg class="spa" viewBox="0 0 16 16" aria-hidden="true"><path d="M8 3.2c1.3 1.4 1.9 2.9 1.9 4.5S9.3 10.7 8 12c-1.3-1.3-1.9-2.7-1.9-4.3S6.7 4.6 8 3.2z"/><path d="M8 12c-1.7-.1-3.6-1-4.7-3 1.6-.3 3 .1 4.2 1.1M8 12c1.7-.1 3.6-1 4.7-3-1.6-.3-3 .1-4.2 1.1"/><path d="M4 13.6h8"/></svg>';
  function spaMark(root) {
    if (!root || !root.ownerDocument && root !== document) return;
    const skip = el => el && el.closest('.spa-done, script, style, textarea, option, input');
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: n => SPA_RE.test(n.nodeValue) && !skip(n.parentElement) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
    const hits = []; while (w.nextNode()) hits.push(w.currentNode);
    for (const t of hits) {
      const m = SPA_RE.exec(t.nodeValue); if (!m) continue;
      const rest = t.splitText(m.index); rest.splitText(m[0].length);
      const span = document.createElement('span'); span.className = 'spa-done'; span.textContent = rest.nodeValue; span.insertAdjacentHTML('beforeend', SPA_SVG);
      rest.replaceWith(span);
    }
  }
  new MutationObserver(muts => { for (const mu of muts) for (const n of mu.addedNodes) spaMark(n.nodeType === 1 ? n : n.parentElement); })
    .observe(document.body, { childList: true, subtree: true, characterData: false });
  readHash();
  render(false);
  spaMark(document.body);
})();
