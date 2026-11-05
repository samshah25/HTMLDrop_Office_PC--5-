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
  // ME or TME mode (2026-10-29, the user: a switch between ME and TME, each with its own Table and Overview): the same
  // page with the TMEs as its people. In TME mode the person on each record is the TME and the other side is the ME; the
  // teams are the TME head's managers and team leaders (tme_tree.py: the team leader on each appointment, the lines above
  // from the SSO dump); the ME line setting still picks which records count. The switch reloads the page, link kept.
  const MODE_KEY = 'jd-me-review-mode';
  const TM = (() => {
    if (!RAW.tl) return false;
    const h = new URLSearchParams(location.hash.slice(1));
    if (h.get('mode')) return h.get('mode') === 'tme';
    if (h.get('view') === 'tme') return true;   // links to the TME view of 28 Oct
    try { return localStorage.getItem(MODE_KEY) === 'tme'; } catch (e) { return false; }
  })();
  // words for the page's people (s, p) and for the other side of each record (c, cp)
  const W = TM ? { s: 'TME', p: 'TMEs', c: 'ME', cp: 'MEs', aS: 'a TME', aC: 'an ME', doS: 'fixed', doC: 'took', toS: 'by', lines: 'SSO reporting line' }
    : { s: 'ME', p: 'MEs', c: 'TME', cp: 'TMEs', aS: 'an ME', aC: 'a TME', doS: 'took', doC: 'fixed', toS: 'to', lines: 'HR reporting line' };
  const ME_L = RAW.mes, TME_L = RAW.tmes, TEAMS = RAW.teams, NT = TEAMS.length;
  function b64(s, T) { const bin = atob(s), u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return new T(u.buffer); }
  // every record as loaded; the ME line setting (below, after the hierarchy) keeps the ones the page works with
  const N0 = RAW.a.n, AD0 = b64(RAW.a.d, Uint16Array), AME0 = b64(RAW.a.me, Uint16Array), AMG0 = b64(RAW.a.mg, Uint16Array),
    ATM0 = b64(RAW.a.tme, Uint16Array), ATT0 = b64(RAW.a.tt, Uint8Array), AO0 = b64(RAW.a.o, Uint8Array), ARL0 = b64(RAW.a.rl, Uint8Array),
    AF0 = b64(RAW.a.f, Uint8Array), ASL0 = b64(RAW.a.sl, Int32Array), ABK0 = b64(RAW.a.bk, Int32Array), AEN0 = b64(RAW.a.en, Int32Array), ADC0 = b64(RAW.a.dc, Int32Array);
  // deals closed, as the Sales MIS counts them (15 Oct 2026): one record per deal row of the deals dump (dc_genio as the
  // weight), with its ME, the ME's team leader that month (65535 = none) and its TME team; not tied to an appointment
  const DLN0 = RAW.dl.n, DLD0 = b64(RAW.dl.d, Uint16Array), DLME0 = b64(RAW.dl.me, Uint16Array), DLMG0 = b64(RAW.dl.mg, Uint16Array),
    DLT0 = b64(RAW.dl.tt, Uint8Array), DLW0 = Float64Array.from(b64(RAW.dl.w, Float32Array), v => Math.round(v * 100) / 100), DLPID0 = RAW.dl.pid || [];
  // the TME on each deal record (2026-10-28, for the TME view; 65535 = none there). Data built before then has none, so
  // every deal counts as 'no TME on the deal record'
  const DLTM0 = RAW.dl.tm ? b64(RAW.dl.tm, Uint16Array) : new Uint16Array(DLN0).fill(65535);
  // each deal's RV_3yr, credited as the deal is counted (x dc_genio); none in data built before 30 Oct 2026
  const DLRV0 = RAW.dl.rv ? Float64Array.from(b64(RAW.dl.rv, Float32Array)) : new Float64Array(DLN0);
  const NC = RAW.nc, NCN0 = NC.n, NCD0 = b64(NC.d, Uint16Array), NCME0 = b64(NC.me, Uint16Array), NCTM0 = b64(NC.tme, Uint16Array), NCK0 = b64(NC.k, Uint8Array);
  // HR records (days present per month, joining date, designation, home city): the MEs', or the TMEs' in TME mode
  const HRS = TM ? RAW.tl : RAW.hr;
  const MONTHS = META.months || [], NM = MONTHS.length, HRD = NM && HRS.days ? b64(HRS.days, Uint16Array) : new Uint16Array(0);
  // TME mode: each TME's team in HR's monthly record (team_type_name; 2026-10-31, the user), as an index into TEAMS per TME
  // and month (-1: no record, or a team with no appointments here such as Corporate)
  const HRT = (() => { const T = TM && HRS.team; if (!T || !NM || !T.ix) return null; const map = T.names.map(n => TEAMS.findIndex(x => x.toLowerCase() === String(n).toLowerCase()));
    return Array.from(b64(T.ix, Uint8Array), v => v === 255 ? -1 : map[v]); })();
  const HRJ = HRS.j || [], HRDES = HRS.des || [], HRCITY = HRS.city || [], HRGRADE = TM ? [] : RAW.hr.grade || [];
  // per ME and month: does the Sales MIS count the ME's deals in this city? 1 yes, 0 no (another city), 2 not known (MEs only)
  const HRMIS = !TM && NM && RAW.hr.mis ? b64(RAW.hr.mis, Uint8Array) : new Uint8Array(0);
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

  const ncode = s => String(s).trim().replace(/^0+/, '');
  /* ---------- the team hierarchy (2026-10-14): head > managers > team leaders > people ---------- */
  // MEs: from HR's reporting lines (each manager's own usual manager, records.py mg_up) until the official list arrives;
  // ROOT = the ME head at the top of most chains in the last 60 days (Kushal Sharma). TMEs (TME mode, 2026-10-29): the
  // team leader on each appointment and the SSO lines above it (tme_tree.py), the TME head given. An appointment sits in
  // the team of the person themselves when they lead a team (a team leader's own appointments count in their team), else
  // in its team leader's team. Teams below a team leader fold into that team leader's team (four levels, as the teams
  // work). Chains that do not reach the head go to one group, OUT.
  function makeTree(G, UP, PEOPLE, AP, AG, root) {
    const NG0 = G.length, OUT = NG0;
    const HEAD = G.map((_, m) => { let c = m, seen = new Set([m]); while (UP[c] >= 0 && !seen.has(UP[c])) { c = UP[c]; seen.add(c); } return c; });
    const R0 = root >= 0 ? root : (() => { const c = new Float64Array(NG0); for (let i = 0; i < N0; i++) if (AG[i] < NG0 && AD0[i] >= LAST - 60) c[HEAD[AG[i]]]++; let b = 0; for (let m = 1; m < NG0; m++) if (c[m] > c[b]) b = m; return b; })();
    const DEPTH = G.map((_, m) => { let d = 0, c = m; const seen = new Set(); while (c !== R0) { if (c < 0 || seen.has(c)) return -1; seen.add(c); c = UP[c]; d++; } return d; });
    const TEAMOF = G.map((_, m) => { if (DEPTH[m] < 0) return OUT; let c = m; while (DEPTH[c] > 2) c = UP[c]; return c; });
    const LEAD_OF = new Map(); G.forEach((x, m) => { if (DEPTH[m] >= 0 && x[0]) LEAD_OF.set(ncode(x[0]), m); });
    const lead = x => x[0] ? LEAD_OF.get(ncode(x[0])) : undefined;
    const OWN = PEOPLE.map(x => { const m = lead(x); return m === undefined ? -1 : TEAMOF[m]; });               // the team a person's own appointments sit in
    const LEAD = PEOPLE.map(x => { const m = lead(x); return m !== undefined && DEPTH[m] <= 2 ? m : -1; });   // the team a person leads (tag)
    const nodeA = i => { const o = OWN[AP[i]]; return o >= 0 ? o : AG[i] < NG0 ? TEAMOF[AG[i]] : OUT; };
    return { ROOT: R0, DEPTH, TEAMOF, OWN, LEAD, OUT, nodeA };
  }
  const MT = makeTree(RAW.mgrs, RAW.mgUp, ME_L, AME0, AMG0, -1), MEHEAD = RAW.mgrs[MT.ROOT][1];   // the ME tree and the ME head

  /* ---------- which MEs the page counts (2026-10-27, settings: the ME head's line only, or all MEs) ---------- */
  // The ME head's line only (the default; the user, 27 Oct): the appointments, deals closed and not-counted appointments of
  // MEs whose HR reporting line does not reach the ME head (OUT) are dropped here, before anything is counted, so no
  // figure, check, skewness day or 'Mumbai' comparison includes them. All MEs = every record, as the Sales MIS counts them.
  // The same rules as the teams below: an appointment sits in the ME's own team when the ME leads one, else in its
  // manager's; a deal in the ME's own team, else its team leader's that month, else the ME's usual team; a not-counted
  // appointment (no manager on it) in the ME's usual team. Changing the setting reloads the page; the link keeps the view.
  // It is always the ME tree, in TME mode too: TME mode shows the TMEs behind the same records.
  const LINE_KEY = 'jd-me-review-line';
  // 2026-11-02 (the user): every fresh open starts on the line only; 'All MEs' lasts for this browser tab's session only
  const LINE_ONLY = (() => { try { localStorage.removeItem(LINE_KEY); return sessionStorage.getItem(LINE_KEY) !== 'all'; } catch (e) { return true; } })();
  const NME0 = ME_L.length, NMG0 = RAW.mgrs.length;
  const nodeA0 = MT.nodeA;
  const ME_NODE0 = (() => { const c = new Map(); for (let i = 0; i < N0; i++) { const k = AME0[i] * 65536 + nodeA0(i); c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME0).fill(-1), bn = new Int32Array(NME0); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();
  const nodeD0 = j => { const me = DLME0[j], o = MT.OWN[me]; return o >= 0 ? o : DLMG0[j] < NMG0 ? MT.TEAMOF[DLMG0[j]] : ME_NODE0[me] >= 0 ? ME_NODE0[me] : MT.OUT; };
  const inLineNC = k => { const nd = ME_NODE0[NCME0[k]]; return nd >= 0 && nd !== MT.OUT; };
  // OUTSIDE: the records outside the line (whatever the setting), for the settings text and the note under the heading
  const KA = [], KD = [], KN = [], OUTSIDE = { ad: [], ame: [], dd: [], dw: [], dme: [], nd: [] };
  for (let i = 0; i < N0; i++) { const out = nodeA0(i) === MT.OUT; if (out) { OUTSIDE.ad.push(AD0[i]); OUTSIDE.ame.push(AME0[i]); } if (!LINE_ONLY || !out) KA.push(i); }
  for (let j = 0; j < DLN0; j++) { const out = nodeD0(j) === MT.OUT; if (out) { OUTSIDE.dd.push(DLD0[j]); OUTSIDE.dw.push(DLW0[j]); OUTSIDE.dme.push(DLME0[j]); } if (!LINE_ONLY || !out) KD.push(j); }
  for (let k = 0; k < NCN0; k++) { const out = !inLineNC(k); if (out) OUTSIDE.nd.push(NCD0[k]); if (!LINE_ONLY || !out) KN.push(k); }
  const keep = (src, idx) => { const o = new src.constructor(idx.length); for (let k = 0; k < idx.length; k++) o[k] = src[idx[k]]; return o; };

  /* ---------- the page's people and teams (2026-10-29): the MEs and the ME tree, or the TMEs and the TME tree ---------- */
  // NOTME: in TME mode, one more 'TME' for the deals closed with no TME on the deal record (at the top of the tree), so
  // the TMEs add up to the same totals as the MEs
  // SELFME (2026-11-04): one more line for the appointments an ME fixed themselves (below)
  const NOTME = TME_L.length, SELFME = NOTME + 1;
  const MES = TM ? [...TME_L, ['', 'No TME on the deal record'], ['', 'Fixed by the ME']] : ME_L, TMES = TM ? ME_L : TME_L;
  const notTme = me => TM && (me === NOTME || me === SELFME);   // TME mode: lines that are not a TME (the counts of TMEs leave them out)
  const MGRS = TM ? RAW.tl.nodes : RAW.mgrs, MGUP = TM ? RAW.tl.up : RAW.mgUp;
  const NME = MES.length, NTM = TMES.length, NMG = MGRS.length, OUTN = NMG;
  const ATL0 = TM ? b64(RAW.tl.a, Uint16Array) : null, DTL0 = TM ? b64(RAW.tl.d, Uint16Array) : null;
  // an appointment the ME fixed themselves (2026-11-04, the user: "why is Hemang Shah in TME mode, he's an ME"): its TME is
  // the ME who took it (TME team BDE, the ME's own manager as its team leader). TME mode shows these as one line, SELFME,
  // with no team leader, so they stay in the group outside the TME head's line where they sat, instead of the MEs as TMEs
  // and their managers as team leaders; the same for the deal records and the not-counted rows. ME mode is unchanged
  if (TM) {
    const meOf = new Map(ME_L.map((x, k) => [ncode(x[0]), k])), same = TME_L.map(x => x[0] && meOf.has(ncode(x[0])) ? meOf.get(ncode(x[0])) : -1);
    const self = (t, m) => t < TME_L.length && same[t] >= 0 && same[t] === m;
    for (let i = 0; i < N0; i++) if (self(ATM0[i], AME0[i])) { ATM0[i] = SELFME; ATL0[i] = 65535; }
    for (let j = 0; j < DLN0; j++) if (self(DLTM0[j], DLME0[j])) { DLTM0[j] = SELFME; DTL0[j] = 65535; }
    for (let k = 0; k < NCN0; k++) if (self(NCTM0[k], NCME0[k])) NCTM0[k] = SELFME;
  }
  const ST = TM ? makeTree(MGRS, MGUP, MES, ATM0, ATL0, RAW.tl.root) : MT;
  const ROOT = ST.ROOT, DEPTH = ST.DEPTH, TEAMOF = ST.TEAMOF, ME_OWN = ST.OWN, ME_LEAD = ST.LEAD;
  const UPN = m => m === OUTN ? ROOT : MGUP[m];   // a team's parent team
  // a manager's page (2026-11-02, Kushal via the user: each manager sees only their own line, behind a login): the page
  // holds only that manager's records and stays on their team; 'Mumbai' adds the rest of the ME head's line as anonymous
  // records under one placeholder ME at the head (manager_pages.py). -1 on the full page
  const MGRN = META.mgr && !TM ? META.mgr.node : -1;
  const inMgr = m => { for (let c = m, g = 0; c >= 0 && g < 8; g++) { if (c === MGRN) return true; if (c === ROOT) return false; c = UPN(c); } return false; };
  const NDEP = m => m === OUTN ? 1 : DEPTH[m];    // 0 the head, 1 a manager, 2 a team leader
  const HEADNAME = MGRS[ROOT][1];
  const OUT_NAME = `Not in ${HEADNAME}'s line`;
  const NNAME = m => m === OUTN ? OUT_NAME : MGRS[m][1];
  const N = KA.length, AD = keep(AD0, KA), AME = keep(TM ? ATM0 : AME0, KA), AMG = keep(TM ? ATL0 : AMG0, KA), ATM = keep(TM ? AME0 : ATM0, KA), ATT = keep(ATT0, KA), AO = keep(AO0, KA),
    ARL = keep(ARL0, KA), AF = keep(AF0, KA), ASL = keep(ASL0, KA), ABK = keep(ABK0, KA), AEN = keep(AEN0, KA), ADC = keep(ADC0, KA);
  const CO = KA.map(i => RAW.co[i]), PID = KA.map(i => RAW.pid[i]);
  const DLME_S = TM ? DLTM0.map(v => v < NOTME || v === SELFME ? v : NOTME) : DLME0;
  const DLN = KD.length, DLD = keep(DLD0, KD), DLME = keep(DLME_S, KD), DLMG = keep(TM ? DTL0 : DLMG0, KD), DLT = keep(DLT0, KD), DLW = keep(DLW0, KD),
    DLPID = DLPID0.length ? KD.map(j => DLPID0[j]) : [], DLTM = keep(TM ? DLME0 : DLTM0, KD);
  const NCN = KN.length, NCD = keep(NCD0, KN), NCME = keep(TM ? NCTM0 : NCME0, KN), NCTM = keep(TM ? NCME0 : NCTM0, KN), NCK = keep(NCK0, KN);
  // TME mode's calls (fetch_calls.py; the user's rules, 31 Oct 2026): per TME and day, the dialer calls whose agent is a
  // TME in HR that month, and the connected ones (trunk duration above 0 and one of his end types); a TME's calls count
  // where the TME is on a line
  // the not-counted rows' allocation and appointment times and TME team (2026-10-30; data built before has none): a
  // same-day 'customer not available' is filed as Not Counted/Cancelled (Not Available (Online)), not as Not Available
  const DLRV = keep(DLRV0, KD);
  const NCBK = RAW.nc.bk ? keep(b64(RAW.nc.bk, Int32Array), KN) : null, NCSL = RAW.nc.sl ? keep(b64(RAW.nc.sl, Int32Array), KN) : null, NCTT = RAW.nc.tt ? keep(b64(RAW.nc.tt, Uint8Array), KN) : null;
  const NA_ONLINE = (NC.kinds || []).indexOf('Not Available (Online)');
  const CL = TM && RAW.tl.calls ? RAW.tl.calls : null, CLN = CL ? CL.n : 0;
  const CLT = CLN ? b64(CL.tm, Uint16Array) : null, CLD = CLN ? b64(CL.d, Uint16Array) : null, CLC = CLN ? b64(CL.c, Uint16Array) : null, CLK = CLN ? b64(CL.k, Uint16Array) : null;
  // what lies outside the line in dates a..b (all of it is left out when LINE_ONLY)
  function outsideIn(a, b) {
    let n = 0, dl = 0, nc = 0; const mes = new Set();
    for (let k = 0; k < OUTSIDE.ad.length; k++) if (OUTSIDE.ad[k] >= a && OUTSIDE.ad[k] <= b) { n++; mes.add(OUTSIDE.ame[k]); }
    for (let k = 0; k < OUTSIDE.dd.length; k++) if (OUTSIDE.dd[k] >= a && OUTSIDE.dd[k] <= b) { dl += OUTSIDE.dw[k]; mes.add(OUTSIDE.dme[k]); }
    for (const d of OUTSIDE.nd) if (d >= a && d <= b) nc++;
    return { n, dl, nc, mes: mes.size };
  }

  // each ME's usual team leader (most common manager), each TME's usual team, each ME's usual ME Head
  const ME_TL = (() => { const c = new Map(); for (let i = 0; i < N; i++) { if (AMG[i] >= NMG) continue; const k = AME[i] * 65536 + AMG[i]; c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME).fill(-1), bn = new Int32Array(NME); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();
  const TME_TEAM = (() => { const c = new Float64Array(NTM * NT); for (let i = 0; i < N; i++) c[ATM[i] * NT + ATT[i]]++; const out = new Int16Array(NTM).fill(-1); for (let t = 0; t < NTM; t++) { let b = 0; for (let k = 0; k < NT; k++) if (c[t * NT + k] > b) { b = c[t * NT + k]; out[t] = k; } } return out; })();
  const ANODE = new Uint16Array(N);
  for (let i = 0; i < N; i++) { const o = ME_OWN[AME[i]]; ANODE[i] = o >= 0 ? o : AMG[i] < NMG ? TEAMOF[AMG[i]] : OUTN; }
  const KIDS = Array.from({ length: NMG + 1 }, () => []);
  for (let m = 0; m < NMG; m++) if (DEPTH[m] === 1 || DEPTH[m] === 2) KIDS[MGUP[m]].push(m);
  KIDS[ROOT].push(OUTN);
  // TME mode: someone straight under the TME head with no team below them leads TMEs: a team leader, not a manager
  const leafTL = m => TM && m >= 0 && m < NMG && DEPTH[m] === 1 && !KIDS[m].length;
  // each ME's usual team (for not-counted appointments, which carry no manager)
  const ME_NODE = (() => { const c = new Map(); for (let i = 0; i < N; i++) { const k = AME[i] * 65536 + ANODE[i]; c.set(k, (c.get(k) || 0) + 1); } const best = new Int32Array(NME).fill(-1), bn = new Int32Array(NME); for (const [k, v] of c) { const me = Math.floor(k / 65536); if (v > bn[me]) { bn[me] = v; best[me] = k % 65536; } } return best; })();
  // a deal sits where its ME's appointments sit: the ME's own team when they lead one, else their team leader's that month
  const DNODE = new Uint16Array(DLN);
  for (let j = 0; j < DLN; j++) { const me = DLME[j], o = ME_OWN[me]; DNODE[j] = TM && me === NOTME ? ROOT : o >= 0 ? o : DLMG[j] < NMG ? TEAMOF[DLMG[j]] : ME_NODE[me] >= 0 ? ME_NODE[me] : OUTN; }
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
  // the ME Head looks at one day; TME mode opens on this month (2026-10-30, the review: a TME fixes about half an appointment
  // a day, so a day is too few to compare anyone, and the dialer runs a day behind)
  const DEFAULT_P = (TM && PRESETS.find(p => p.k === 'tm')) || PRESETS.find(p => p.k === 'day') || PRESETS.find(p => p.k === 'lm') || PRESETS[0];

  /* ---------- view state ---------- */
  // scope: one team of the hierarchy (ROOT = all Mumbai); lvl: the table's Show (1 managers, 2 team leaders, 3 MEs)
  const V = { scope: MGRN >= 0 ? MGRN : ROOT, cb: 'att', from: 0, to: LAST, pa: null, pb: null, pl: '', preset: null, view: 'table', sortBy: 'n',
    qKind: 'all', qTeam: -1, qSev: 'all', qStat: 'open', qAll: false, lvl: 1, xOpen: new Set(), xShut: new Set(), ovOpen: new Set(), ovShut: new Set(), ovSort: 'n',
    // the TME view (2026-10-28): the TME team shown (kept as a team, so it follows the grouping settings; -1 = Hot Data),
    // By TME or By ME, its order, and the view to go back to
    tgT: -1, tTab: 'tme', tSort: 'n', tDir: 'desc', prevView: 'table',
    // TME mode's flows card (2026-10-30): its top row (TME teams or TME managers' teams) and the team picked on it
    flowBy: 'teams', flowSel: null,   // flowBy: always 'teams' since 31 Oct (the user removed the TME managers' teams switch)
    flowView: 'conv', flowMea: 'c', cvMea: 'c', tsec: 'teams',   // tsec opens on 'TME teams → ME managers' (2026-11-02, the user; was Summary)   // cvMea: ME mode's 'Who converts' measure (2026-11-02)   // flowView 'conv' = who converts which leads (2026-11-02, the first view); flowMea: c conversion | a attended %   // tsec: TME mode's section shown (2026-10-30)   // flowView: the lines or the grid (2026-10-30)
    // TME mode's ME managers' card (2026-10-30): the TME team its funnels show (-1 = all)
    mgrTeam: -1 };
  try { const l = +localStorage.getItem('jd-me-review-show'); if ([1, 2, 3].includes(l)) V.lvl = l; } catch (e) { /* default: managers */ }
  // the Overview's 'Your team' view: 'shares' (team-share ribbons) or 'bars' (Funnel: one bar per line), for every Show
  // level (2026-10-15). Remembered apart for 1-6 days and for 7 days or more, like the Table's two column sets; Funnel by
  // default
  const MS = {}, MS_KEY = () => V.to - V.from + 1 < 7 ? 'jd-me-review-mestyle-day' : 'jd-me-review-mestyle';
  const meStyle = () => { const k = MS_KEY(); if (MS[k]) return MS[k]; try { const v = localStorage.getItem(k); if (v === 'bars' || v === 'shares' || v === 'conv') return (MS[k] = v === 'bars' ? v : 'conv'); } catch (e) { /* default */ } return 'bars'; };
  // the second view is 'Who converts' (2026-11-02, the user: instead of Team shares; ME mode first, then TME mode too)
  { const sb = document.querySelector('#meStyle [data-v="shares"]'); if (sb) { sb.dataset.v = 'conv'; sb.textContent = 'Who converts'; sb.title = 'Each line\'s conversion on each TME team\'s appointments, against all Mumbai on the same TME team'; } }
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
    if (!NM || (me + 1) * NM > HRD.length) return null;
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
      dl: 0, meDl: new Float64Array(NME), tDl: new Float64Array(NT), gMes: new Set(), cl: [0, 0], meCl: new Float64Array(CLN ? NME * 2 : 0),
      rv: 0, meRv: new Float64Array(NME), tRv: new Float64Array(NT), meTim: new Float64Array(NME * 2) };   // rv: RV3yr; meTim: [with an allocation record, allocated the day before or earlier]   // gMes: MEs with appointments given   // dl: deals closed (Sales MIS rule), not Dealclosed appointments (o[0])
    if (a === null || a === undefined || b < a) return R;
    const nd = new Map(), lastNd = new Int32Array(NME).fill(-1);   // each ME's team in the dates: where most of their appointments sit
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < a || d > b || !inScope(i)) continue;
      const me = AME[i], o = AO[i], t = ATT[i], f = AF[i], tm = ATM[i];
      R.n++; R.o[o]++; R.meO[me * 6 + o]++; R.tO[t * 6 + o]++; R.mes.add(me); R.gMes.add(me); R.tmN[tm]++;
      const nk = me * 65536 + ANODE[i]; nd.set(nk, (nd.get(nk) || 0) + 1); lastNd[me] = ANODE[i];
      const k = (me * NT + t) * 3; R.meT[k]++; if (o <= 2) R.meT[k + 1]++;   // [k + 2] = deals closed, from the deal records below
      const tg0 = timingOf(i); if (tg0 < 3) { R.meTim[me * 2]++; if (tg0 > 0) R.meTim[me * 2 + 1]++; }
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
      R.rv += DLRV[j]; R.meRv[me] += DLRV[j]; R.tRv[t] += DLRV[j];
      if (R.meNode[me] < 0) R.meNode[me] = DNODE[j];
    }
    // TME mode: the calls of the TMEs on the lines (with appointments given or deals closed here), in these dates
    for (let k = 0; k < CLN; k++) { const d = CLD[k]; if (d < a || d > b) continue; const me = CLT[k]; if (!R.mes.has(me)) continue; R.meCl[me * 2] += CLC[k]; R.meCl[me * 2 + 1] += CLK[k]; R.cl[0] += CLC[k]; R.cl[1] += CLK[k]; }
    // not-counted appointments carry no manager: they belong to the scope when the ME's usual team does
    for (let i = 0; i < NCN; i++) { const d = NCD[i]; if (d < a || d > b) continue; if (scoped() && !(ME_NODE[NCME[i]] >= 0 && SMASK[ME_NODE[NCME[i]]])) continue; R.meNC[NCME[i]]++; R.nc++; }
    return R;
  }
  const att = o => o[0] + o[1] + o[2];
  // an ME's team leader and manager from their team in the dates; outside the ME head's line, the recorded manager
  const tlOf = m => m >= 0 && m !== OUTN && (DEPTH[m] === 2 || leafTL(m)) ? m : -1;
  const mgOf = m => m < 0 || m === OUTN ? -1 : DEPTH[m] === 2 ? MGUP[m] : DEPTH[m] === 1 && !leafTL(m) ? m : -1;
  // calls, connected, connected %, appointments given per 1,000 connected, calls per day present (TME mode)
  // appointments per 1,000 connected needs APC_MIN connected calls: some TMEs fix most appointments without a dialer call
  // (Super Cat; BDEs are not on the dialer), and a few connected calls would give hundreds per 100
  const APC_MIN = 30;
  // per 1,000 connected (2026-10-31): under the user's connected rule about 80% of calls connect, so per 100 reads 0.3-2
  const APC_PER = 1000;
  const callsOf = (calls, conn, n, pd) => ({ calls, conn, connP: pc(conn, calls), apc: conn >= APC_MIN ? n / conn * APC_PER : null, clPd: pd && calls ? calls / pd : null });
  // RV3yr in rupees: crore / lakh (2026-10-30)
  const fRv = v => !v ? '₹0' : v >= 1e7 ? `₹${(v / 1e7).toFixed(2)} cr` : v >= 1e5 ? `₹${(v / 1e5).toFixed(1)} L` : `₹${n0(v)}`;
  // time since joining (HR), in months and in bands (TME mode's Table, 2026-10-30)
  const tenureMonths = me => { const j = HRJ[me]; if (!j) return null; const d = new Date(j + 'T00:00:00Z'), e = dOf(LAST); const m = (e.getUTCFullYear() - d.getUTCFullYear()) * 12 + e.getUTCMonth() - d.getUTCMonth(); return m < 0 ? null : m; };
  const tenureBand = me => { const m = tenureMonths(me); return m === null ? '(not in HR)' : m < 3 ? '0–3 months' : m < 6 ? '3–6 months' : m < 12 ? '6–12 months' : m < 24 ? '1–2 years' : '2+ years'; };
  // a person's TME teams in the dates [given, attended, deals], and the team of most of their appointments
  const teamsOf = (R, me) => TEAMS.map((_, t) => { const k = (me * NT + t) * 3; return [R.meT[k], R.meT[k + 1], R.meT[k + 2]]; });
  // a TME's team in HR over the dates: the month with the most days in them (-1 when HR has none)
  function hrTeamOf(me, a = V.from, b = V.to) {
    if (!HRT || me < 0 || (me + 1) * NM > HRT.length) return -1;
    let best = -1, bw = 0;
    for (let k = 0; k < NM; k++) { const M = MONTH_SPAN[k], lo = Math.max(a, M.a), hi = Math.min(b, M.b); if (hi < lo) continue; const t = HRT[me * NM + k]; if (t >= 0 && hi - lo + 1 >= bw) { bw = hi - lo + 1; best = t; } }
    return best;
  }
  // a TME's own team: HR's (2026-10-31), else the TME team of most of their appointments in the dates
  const mainTeamOf = me => { const h = TM ? hrTeamOf(me) : -1; return h >= 0 ? h : apptTeamOf(me); };
  const apptTeamOf = me => { let b = -1, bn = 0; for (let t = 0; t < NT; t++) { const g = CUR.meT[(me * NT + t) * 3]; if (g > bn) { bn = g; b = t; } } return b; };
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
        des: HRDES[me] || '', city: HRCITY[me] || '', grade: HRGRADE[me] || '', ...callsOf(CLN ? R.meCl[me * 2] : 0, CLN ? R.meCl[me * 2 + 1] : 0, n, pd), rv: R.meRv[me], tim: [R.meTim[me * 2], R.meTim[me * 2 + 1]] });
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
    return `<p class="upd">${esc(t)}</p>` + lineNote();
  }
  // the ME head's line only: what the figures leave out in these dates (the user, 27 Oct: keep 'Mumbai', but say it is the
  // ME head's line so nobody takes it for all of Mumbai, and show the gap to the Sales MIS)
  function lineNote() {
    if (!LINE_ONLY) return '';
    if (MGRN >= 0) return '';   // a manager's page: no note (the user, 2 Nov: unnecessary; the top tag names the team)
    const h = outsideIn(V.from, V.to);
    const what = [h.n ? plural(h.n, 'appointment') + ' given' : '', h.dl ? `${n0(h.dl)} ${Math.round(h.dl) === 1 ? 'deal' : 'deals'} closed` : '', h.nc ? `${n0(h.nc)} not counted` : ''].filter(Boolean).join(', ');
    // 2026-11-02 (the user: the band reads text-heavy; polish only): one short line, the whole sentence on hover
    const full = `${META.city} = ${MEHEAD}'s line only. ${h.mes ? `Left out in these dates: ${plural(h.mes, 'ME')} outside the line (${what}), so the totals are below the Sales MIS by that much.` : 'No MEs outside the line in these dates.'}`;
    const brief = [h.n ? plural(h.n, 'appointment') + ' given' : '', h.dl ? `${n0(h.dl)} ${Math.round(h.dl) === 1 ? 'deal' : 'deals'} closed` : ''].filter(Boolean).join(', ');
    return `<p class="linenote" title="${esc(full)}"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/></svg>${h.mes ? `Left out: ${esc(plural(h.mes, 'ME'))} outside the line${brief ? ` (${esc(brief)})` : ''}` : 'No MEs outside the line in these dates'} · <button type="button" class="lnk on-navy" data-open-set="1">Change in settings</button></p>`;
  }
  const ARROW = `<div class="sarr" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M4 12h15M13 6l6 6-6 6"/></svg></div>`;
  // a team's chain from the top: [ROOT, manager, team leader]
  const chainOf = m => { const c = []; for (let g = 0; m >= 0 && g < 6; g++) { c.unshift(m); if (m === ROOT) break; m = UPN(m); } return c; };
  const ROLE = m => m === OUTN ? '' : DEPTH[m] === 1 ? (leafTL(m) ? 'team leader' : 'manager') : DEPTH[m] === 2 ? 'team leader' : '';
  // the way back up above the heading: All Mumbai > manager > (this team, named in the heading)
  function crumbs() {
    if (!scoped()) return '';
    const c0 = chainOf(V.scope), c = (MGRN >= 0 ? c0.slice(Math.max(0, c0.indexOf(MGRN))) : c0).slice(0, -1);
    if (!c.length) return '';
    return `<nav class="crumbs" aria-label="Teams above">${c.map(m => `<button type="button" class="lnk" data-scope="${m}" title="Show ${esc(m === ROOT ? `all of ${META.city}` : `${NNAME(m)}'s whole team`)}">${esc(m === ROOT ? `All ${META.city}` : NNAME(m))}</button><span aria-hidden="true">›</span>`).join('')}</nav>`;
  }
  const teamHead = () => scoped() ? `${esc(NNAME(V.scope))}${V.scope === OUTN ? '' : "'s team"} · ` : '';
  // one step of the band's funnel: bar (width = share of appointments given) and its words; `open` makes the bar a button
  // 2026-11-02 (the user: polish): the words sit right after the bar, the rate as a figure (its meaning on hover); the
  // bars keep their widths, against the band less room for the words (--flw)
  function fRow(w, cls, val, lab, sub, chg, open) {
    const out = w < 17, ww = `style="width:calc((100% - var(--flw)) * ${(Math.max(w, 1.5) / 100).toFixed(4)})"`;
    const bar = `<span class="fbar ${cls}">${out ? '' : `<span class="tn">${val}</span>`}</span>`;
    return `<div class="fr">${open ? `<button type="button" class="ftrack fgo" data-open="${open}" title="See the deals closed" ${ww}>${bar}</button>` : `<div class="ftrack" ${ww}>${bar}</div>`}${out ? `<span class="fout tn">${val}</span>` : ''}` +
      `<div class="flab"><span class="l1"><b>${lab}</b>${sub}</span>${chg ? `<span class="l2">${chg}</span>` : ''}</div></div>`;
  }
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
    const cityR = x => scoped() ? ` <span class="chg flat">${hasP ? '· ' : ''}${esc(META.city)} ${fP(x)}</span>` : '';   // no leading dot when there is no change before it (2026-11-02)
    // MEs with appointments; MEs who only closed a deal (no appointment in the dates) are named apart, so the count
    // matches the Table's 'N MEs' (both together)
    // TME mode: 'No TME on the deal record' is not a TME
    const xD = R.mes.size - R.gMes.size - (TM && R.mes.has(NOTME) && !R.gMes.has(NOTME) ? 1 : 0);
    const dOnly = xD > 0 ? `<span class="chg flat">${hasP ? ' · ' : ''}+${plural(xD, W.s)} with deals only</span>` : '';
    if (V.view === 'table' || TM) {
      // the Table view: one line of totals so the table starts high on the screen (the funnel stays on Overview); TME mode
      // uses it on the Overview too (2026-10-30, the user: too much scrolling), with the calls first
      const kp = TM   // TME mode (2026-10-31, the design pass): label, figure, context, change -- the same order in all five
        ? (v, lab, sub, c) => `<div class="kp kq"><div class="kh">${lab}</div><div class="kvr"><span class="kv tn">${v}</span>${sub ? `<span class="ks">${sub}</span>` : ''}</div>${c ? `<div class="kc">${c}</div>` : ''}</div>`
        : (v, lab, sub, c) => `<div class="kp"><div class="kt"><span class="kv tn">${v}</span><span class="kl"><b>${lab}</b>${sub ? ` · ${sub}` : ''}</span></div>${c ? `<div class="kc">${c}</div>` : ''}</div>`;
      const whyK = k => TM && R.o[k] ? `<button type="button" class="lnk on-navy" data-o="${k}" title="See these appointments">${n0(R.o[k])} ${OUT[k]}</button>` : `${n0(R.o[k])} ${OUT[k]}`;
      $('#hero').innerHTML = head + `<div class="kps${TM && CLN ? ' kps5' : ''}">` + (TM ? callKp(R, P, hasP, kp) : '') +
        kp(n0(R.n), 'appointments given', `${W.toS} ${plural(R.gMes.size, W.s)}`, chN + dOnly) +
        kp(n0(a), 'attended', fP(attP), chA + cityR(cA)) +
        kp(n0(R.dl), 'deals closed', `${fP(conv)} ${CVOF()}${TM && R.rv ? ` · ${fRv(R.rv)} RV3yr` : ''}`, chC + cityR(cC)) +
        kp(n0(R.n - a), 'not attended', fP(pc(R.n - a, R.n)), `<span class="chg flat">${whyK(3)} · ${whyK(4)} · ${whyK(5)}</span>`) +
        `</div>`;
      return;
    }
    // Overview: the funnel (bar width = share of appointments given), each step with its own change (2026-10-15: the
    // side panel that repeated the rates is gone); deals closed and each not-attended reason open their records
    const frow = fRow;
    // the not-attended reasons as small chips (2026-11-02, polish); each still opens its appointments
    const why = k => R.o[k] ? `<button type="button" class="mchip" data-o="${k}" title="See these appointments"><b class="tn">${n0(R.o[k])}</b>${OUT[k]}</button>` : `<span class="mchip off"><b class="tn">0</b>${OUT[k]}</span>`;
    const fpc = (v, tip, word) => `<span class="fpc tn" title="${esc(tip)}">${v}</span>${word ? `<span class="fsub">${word}</span>` : ''}`;
    $('#hero').innerHTML = `<div class="fx"><div class="fmain">${head}${callStrip(R, P, hasP)}<div class="fn">` +
      frow(100, 'g', n0(R.n), 'appointments given', `<span class="fsub">${W.toS} ${plural(R.gMes.size, W.s)}</span>`, chN + dOnly) +
      frow(attP || 0, 'a', n0(a), 'attended', fpc(fP(attP), `${fP(attP)} of appointments given`), chA + cityR(cA)) +
      frow(Math.min(100, pc(R.dl, R.n) || 0), 'd', n0(R.dl), 'deals closed', fpc(fP(conv), `${fP(conv)} ${CVOF()} (conversion)`, 'conversion') + (TM && R.rv ? `<span class="fsub">${fRv(R.rv)} RV3yr</span>` : ''), chC + cityR(cC), 'deals') +
      `</div><p class="miss"><span class="mlab"><b class="tn">${n0(R.n - a)}</b>not attended (${fP(pc(R.n - a, R.n))})</span>${why(3)}${why(4)}${why(5)}</p></div>` +
      `<div class="fside">${TM ? tmeSide() : ''}${movers()}${trend()}</div></div>`;
  }
  // TME mode's band (2026-10-30, the user: the TME funnel with the calls, as in the Hot Data TME report): the TMEs' calls,
  // the connected ones, and the appointments given per 1,000 connected, each with its change; above the funnel
  // appointments per 1,000 connected counts only TMEs with DIAL_MIN+ dialer calls in the dates (2026-10-30, the review: many
  // Super Cat TMEs fix appointments without a dialer call, which flattered the ratio); their appointments and connected
  const DIAL_MIN = 100;
  const dialOf = R => { let n = 0, k = 0, off = 0; for (const me of R.mes) { if (TM && me === NOTME) continue; const c = R.meCl[me * 2], g = R.meO.subarray(me * 6, me * 6 + 6).reduce((s, x) => s + x, 0); if (c >= DIAL_MIN) { n += g; k += R.meCl[me * 2 + 1]; } else off += g; } return { n, k, off, apc: k ? n / k * APC_PER : null }; };
  // TME mode's band: the calls as the first figure of the one line (2026-10-30)
  function callKp(R, P, hasP, kp) {
    if (!CLN) return '';
    if (!R.cl[0]) { const t0 = CL.to ? offOf(CL.to) : LAST; return kp('—', 'calls', V.from > t0 ? `the dialer data runs to ${esc(fDate(dOf(t0)))}` : 'none in these dates', ''); }
    const c = R.cl, p = P.cl, cp = pc(c[1], c[0]), pcp = pc(p[1], p[0]), dc = dialOf(R), dp = P.n ? dialOf(P) : { apc: null };
    const d = hasP && p[0] && cp !== null && pcp !== null ? Math.round((cp - pcp) * 10) / 10 : null;
    const chg = d === null ? '' : `<span class="chg ${d > 0 ? 'up' : d < 0 ? 'dn' : 'flat'}">${d > 0 ? '▲ ' : d < 0 ? '▼ ' : ''}connected ${d > 0 ? 'up' : d < 0 ? 'down' : 'same,'} ${Math.abs(d).toFixed(1)} pts (was ${fP(pcp)})</span>`;
    const ap = V.from === V.to || dc.apc === null ? '' : `<span class="chg flat" title="${esc(`Appointments given per 1,000 connected calls, for the TMEs with ${DIAL_MIN}+ dialer calls in these dates${dc.off ? `; ${n0(dc.off)} appointments by TMEs off the dialer left out` : ''}`)}">${dc.apc.toFixed(1)} appointments per 1,000 connected${hasP && dp.apc !== null ? ` (was ${dp.apc.toFixed(1)})` : ''}</span>`;
    const late = CL.to && V.to > offOf(CL.to) ? ` · to ${esc(fDate(dOf(offOf(CL.to))))}` : '';
    return kp(c[0] >= 1e5 ? (c[0] / 1e5).toFixed(1) + ' L' : n0(c[0]), 'calls dialed', `${fP(cp)} connected${late}`, [chg, ap].filter(Boolean).join('<br>'));
  }
  function callStrip(R, P, hasP) {
    if (!CLN) return '';
    if (!R.cl[0]) { const t0 = CL.to ? offOf(CL.to) : LAST; return V.from > t0 ? `<div class="cstrip"><span class="cnote">No calls for these dates yet: the dialer data runs to ${esc(fDate(dOf(t0), true))}.</span></div>` : ''; }
    const c = R.cl, p = P.cl, cp = pc(c[1], c[0]), pcp = pc(p[1], p[0]), dc = dialOf(R), dp = P.n ? dialOf(P) : { apc: null }, apc = dc.apc, papc = dp.apc, oneDay = V.from === V.to;
    const ch = (v, w, unit) => { if (!hasP || v === null || w === null || !p[0]) return ''; const d = Math.round((v - w) * 10) / 10; return `<span class="chg ${d > 0 ? 'up' : d < 0 ? 'dn' : 'flat'}">${d > 0 ? '▲ up' : d < 0 ? '▼ down' : 'same,'} ${Math.abs(d).toFixed(1)}${unit} (was ${w.toFixed(1)}${unit === ' pts' ? '%' : ''})</span>`; };
    const to = CL.to ? offOf(CL.to) : LAST, late = V.to > to ? `<p class="cnote">Calls run to ${esc(fDate(dOf(to), true))}.</p>` : '';
    const AR = '<span class="carr" aria-hidden="true">→</span>';
    const blk = (v, lab, chg) => `<div class="cst"><b class="tn">${v}</b><span class="cl">${lab}</span>${chg ? `<span class="cc">${chg}</span>` : ''}</div>`;
    return `<div class="cstrip">${blk(n0(c[0]), 'calls', hasP && p[0] ? `<span class="chg flat">was ${n0(p[0])}</span>` : '')}${AR}` +
      `${blk(n0(c[1]), `connected · ${fP(cp)}`, ch(cp, pcp, ' pts'))}${AR}` +
      (oneDay ? `<div class="cst"><span class="cl mu">Appointments per 1,000 connected shows for 2+ days:<br>most of a day's appointments were fixed earlier</span></div>`
        : `${blk(apc === null ? '—' : apc.toFixed(1), 'appointments given per 1,000 connected', ch(apc, papc, ''))}${dc.off ? `<div class="cst cnote2"><span class="cl mu" title="TMEs with fewer than ${DIAL_MIN} dialer calls in these dates fix their appointments mostly without the dialer (many in Super Cat), so they are left out of this ratio">TMEs with ${DIAL_MIN}+ calls; ${n0(dc.off)} appointments by<br>TMEs off the dialer left out</span></div>` : ''}`) + `</div>${late}`;
  }
  // a comparison is like for like only on usual days: name any low day (a holiday, a short day) in either set of dates
  function lowNote() {
    const list = (a, b) => { const o = []; if (a === null || a === undefined) return o; for (let d = a; d <= b; d++) if (isLow(d)) o.push(d); return o; };
    const cur = list(V.from, V.to), prv = list(V.pa, V.pb);
    if (!cur.length && !prv.length) return '';
    if (V.from !== V.to && cur.length === prv.length) return '';   // one in each: still like for like
    const say = ds => ds.map(d => `${dayName(d)} (${n0(DAYN[d])} appointments given in ${META.city})`).join(', ');
    const parts = [];
    if (cur.length) parts.push(V.from === V.to ? `${say(cur)} was a low day` : `These dates include ${say(cur)}`);
    if (prv.length) parts.push(`${prevName()} ${V.pa === V.pb ? 'was' : 'includes'} ${V.pa === V.pb ? `a low day (${n0(DAYN[V.pa])} appointments given)` : say(prv)}`);
    const full = `${parts.join('; ')}. A usual day has about ${n0(Math.round(USUAL / 10) * 10)}, so the changes are not like for like.`;
    // 2026-11-02 (the user: text-heavy; polish): one line naming the low days, the whole sentence on hover
    const brief = [cur.length ? (V.from === V.to ? `${dayName(cur[0])} was a low day` : `low ${cur.length === 1 ? 'day' : 'days'} ${cur.map(dayName).join(', ')}`) : '',
      prv.length ? `${prevName()}: ${V.pa === V.pb ? 'a low day' : prv.map(dayName).join(', ')}` : ''].filter(Boolean).join(' · ');
    return `<p class="lownote" title="${esc(full)}"><svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/></svg>Not like for like: ${esc(brief)}</p>`;
  }
  // the band's 'Across managers' lines: plain facts about the level below the team shown (managers, team leaders or MEs)
  // a TME's appointments given a day present against the usual of their own TME team (2026-10-31, the user: a TME's main
  // KPI is appointments given to MEs; deals closed are the added view). The usual = the median a day present of the team's
  // TMEs with PACE_PD+ days present in these dates (the TME's team in HR, else that of most of their appointments; PACE_N+ such TMEs), from
  // all Mumbai whatever team is picked; short = the usual pace x their days present - their appointments given
  const PACE_PD = 10, PACE_N = 5, PACE_LOW = .6;
  let PACE = null;
  function paceMap() {
    if (PACE) return PACE;
    PACE = new Map();
    const R = CITY, rows = scoped() ? rowsOfMes(CITY) : MEROWS, by = new Map();
    const team = me => { let b = hrTeamOf(me), bn = 0; if (b >= 0) return b; for (let t = 0; t < NT; t++) { const g = R.meT[(me * NT + t) * 3]; if (g > bn) { bn = g; b = t; } } return b; };
    for (const r of rows) { if (notTme(r.me) || r.pd === null || r.pd < PACE_PD || !r.n) continue; const t = team(r.me); if (t < 0) continue; if (!by.has(t)) by.set(t, []); by.get(t).push(r); }
    for (const [t, rs] of by) {
      if (rs.length < PACE_N) continue;
      const med = median(rs.map(r => r.perDay)); let cn = 0, ca = 0;
      for (const r of rs) if (r.calls >= DIAL_MIN) { cn += r.conn; ca += r.n; }   // the team's appointments per 1,000 connected
      const tapc = cn >= APC_MIN ? ca / cn * APC_PER : null;
      for (const r of rs) PACE.set(r.me, { t, med, k: rs.length, short: med * r.pd - r.n, ratio: med ? r.perDay / med : null, tapc });
    }
    return PACE;
  }
  const f1 = v => v === null || v === undefined || !isFinite(v) ? '—' : v.toFixed(1);
  const pd1 = v => n0(Math.round(v * 10) / 10);
  // TME mode's band, right (2026-10-30; first on the TME view of 28 Oct): the TMEs, how many sit past the usual swing
  // against the same MEs (a click orders the TME list by it), when the appointments were allocated, and a pointer to
  // longer dates when most appointments sit with TMEs who fixed too few to compare
  function tmeSide() {
    const R = CUR, rows = MEROWS.filter(r => !notTme(r.me) && r.n > 0), L = rows.map(lfOf).filter(Boolean);
    // where to look first (2026-10-30, the review): the TMEs past the usual swing below the same MEs on conversion, the
    // most deals short first (size and gap in one number), with how many of the last 3 months they were below
    const short = rows.map(r => ({ r, x: lfOf(r) })).filter(o => o.x && !tFew(o.x).c && o.x.zC <= -TZ).map(o => Object.assign(o, { s: o.x.ed - o.x.deals })).sort((a, b) => b.s - a.s);
    const wl = short.slice(0, 5).map(o => { const mb = monthsBelow(o.r.me), t = mainTeamOf(o.r.me); return `<div class="rk"><div class="rkb"><div class="rkt"><button type="button" class="lnk" data-me="${o.r.me}" title="Open ${esc(o.r.name)}'s window">${esc(o.r.name)}</button>${t >= 0 ? `<span class="rkx">${esc(TEAMS[t])}</span>` : ''}</div><div class="rkd"><b>${n0(o.x.deals)}</b> deals closed against <b>${n0(o.x.ed)}</b> at the same MEs' rate${mb.of ? ` · below in ${mb.below} of ${mb.of === 1 ? 'its 1 recent month' : `its last ${mb.of} months`} with ${TMIN}+ to compare` : ''}</div></div><div class="rkv" title="${esc(`${n0(o.s)} deals closed below what the same MEs' rate gives`)}"><b class="tn">${n0(o.s)}</b><small>deals short</small></div></div>`; }).join('');
    const look = short.length ? `<div class="mv tmv"><h3>Through deals <span class="h3s">· the added view</span></h3><p class="sumsub">TMEs past the usual swing below the same MEs on conversion, most deals short first</p>${wl}<p class="tmore"><button type="button" class="lnk on-navy" data-tord="short">${short.length > 5 ? `All ${n0(short.length)}, ` : ''}every TME, most deals short first</button></p></div>` : '';
    // where to look first, the main KPI (2026-10-31): appointments given a day present, against the TME's team's usual
    const pm = paceMap(), low = rows.map(r => ({ r, p: pm.get(r.me) })).filter(o => o.p && o.p.ratio !== null && o.p.ratio <= PACE_LOW && o.p.short >= 1).sort((a, b) => b.p.short - a.p.short);
    const wlA = low.slice(0, 5).map(({ r, p }) => { const tn = TEAMS[p.t];
      const ap = r.calls >= DIAL_MIN && r.apc !== null && p.tapc !== null ? ` · <b>${f1(r.apc)}</b> per 1,000 connected (${esc(tn)} ${f1(p.tapc)})` : r.calls < DIAL_MIN ? ' · off the dialer' : '';
      return `<div class="rk"><div class="rkb"><div class="rkt"><button type="button" class="lnk" data-me="${r.me}" title="Open ${esc(r.name)}'s window">${esc(r.name)}</button><span class="rkx">${esc(tn)}</span></div><div class="rkd"><b>${f1(r.perDay)}</b> a day present against ${esc(tn)}'s usual <b>${f1(p.med)}</b> · ${n0(r.n)} in ${pd1(r.pd)} days${ap}</div></div><div class="rkv" title="${esc(`${n0(Math.round(p.short))} appointments below ${tn}'s usual pace`)}"><b class="tn">${n0(Math.round(p.short))}</b><small>below pace</small></div></div>`; }).join('');
    const multi = V.to - V.from + 1 >= 7;
    const lookA = `<div class="mv tmv"><h3>Where to look first <span class="h3s">· appointments given</span></h3>` + (!multi
      ? `<p class="mu sumnone">Appointments a day present needs a week or more of dates (HR attendance is monthly): ${PRESETS.filter(q => q.k === 'tm' || q.k === 'lm').map(q => `<button type="button" class="lnk on-navy" data-tpre="${q.k}">${esc(q.label)}</button>`).join(' · ')}</p>`
      : low.length ? `<p class="sumsub" title="${esc(`The usual = the median a day present of the team's TMEs with ${PACE_PD}+ days present in these dates (HR attendance), all ${META.city}; the TME's team = their team in HR (monthly record), else the TME team of most of their appointments`)}">TMEs below ${Math.round(PACE_LOW * 100)}% of their TME team's usual appointments a day present, most appointments short first</p>${wlA}<p class="tmore"><button type="button" class="lnk on-navy" data-tord="pace">${low.length > 5 ? `All ${n0(low.length)}, ` : ''}every TME, most appointments short first</button></p>`
      : `<p class="mu sumnone">No TME with ${PACE_PD}+ days present is below ${Math.round(PACE_LOW * 100)}% of their TME team's usual appointments a day present in these dates.</p>`) + `</div>`;
    const usual = [...new Map([...pm.values()].map(p => [p.t, p])).values()].sort((a, b) => b.k - a.k);
    const big = rows.filter(r => r.n >= TMIN), bigShare = pc(big.reduce((s, r) => s + r.n, 0), R.n) || 0;
    const ok = L.filter(r => !tFew(r).c), okA = L.filter(r => !tFew(r).a);
    const cnt = (X, k, s) => X.filter(r => s < 0 ? r[k] <= -TZ : r[k] >= TZ).length;
    const cb = cnt(ok, 'zC', -1), ca = cnt(ok, 'zC', 1), ab = cnt(okA, 'zA', -1), aa = cnt(okA, 'zA', 1);
    // about 2.3% of the TMEs tested land past 2 standard errors each way by chance alone (2026-10-30, the review)
    const chance = n => `<small class="tch" title="${esc(`${n0(n)} TMEs have enough appointments to compare; at ${TZ} standard errors, chance alone puts about 2.3% of them past the usual swing each way`)}">about ${n0(Math.round(n * .0228))} each way by chance alone</small>`;
    const tmx = timingMix(() => true, () => true), tg = tmx.reduce((s, c) => s + c[0], 0), before = [tmx[1][0] + tmx[2][0], tmx[1][1] + tmx[2][1], tmx[1][2] + tmx[2][2]];
    const ord = (k, n, txt) => n ? `<button type="button" class="lnk on-navy" data-tord="${k}" title="List the TMEs in this order">${n0(n)} ${txt}</button>` : `0 ${txt}`;
    return { look, lookA, rest: `<div class="mv tmv"><h3>The TMEs</h3>` +
      `<p><span class="k">Fixed these</span><span><b>${n0(rows.length)}</b> TMEs · <b>${n0(big.length)}</b> with ${TMIN}+ given, ${Math.round(bigShare)}% of the appointments</span></p>` +
      (multi && usual.length ? `<p><span class="k">A day present</span><span>${ord('pace', low.length, `below ${Math.round(PACE_LOW * 100)}% of their team's usual`)} · usual: ${usual.slice(0, 4).map(p => `${esc(TEAMS[p.t])} <b>${f1(p.med)}</b>`).join(' · ')}${usual.length > 4 ? ` <small class="tch" title="${esc(usual.slice(4).map(p => `${TEAMS[p.t]} ${f1(p.med)}`).join(' · '))}">+${usual.length - 4} more</small>` : ''}</span></p>` : '') +
      `<p><span class="k">Conversion</span><span>${ord('zC', cb, 'below')} · ${ord('zCu', ca, 'above')} the same MEs, past the usual swing; ${chance(ok.length)}</span></p>` +
      `<p><span class="k">Attended %</span><span>${ord('zA', ab, 'below')} · ${ord('zAu', aa, 'above')} the same MEs (same allocation timing), past the usual swing; ${chance(okA.length)}</span></p></div>` +
      (tg ? `<div class="mv tmv"><h3>When they were allocated</h3><p><span class="k">Same day</span><span><b>${pct0(tmx[0][0], tg)}</b> of given · <b>${pct0(tmx[0][1], tmx[0][0] + tmx[0][2])}</b> attended${tmx[0][2] ? ` <small class="tch" title="A company not available for a same-day appointment is filed as Not Counted/Cancelled (Not Available (Online)), so it never shows in appointments given; counted back here as not attended">(${pct0(tmx[0][1], tmx[0][0])} leaving out ${n0(tmx[0][2])} same-day Not Available (Online))</small>` : ''}</span></p>` +
        `<p><span class="k">Day before or earlier</span><span><b>${pct0(before[0], tg)}</b> of given · <b>${pct0(before[1], before[0] + before[2])}</b> attended</span></p>` +
        (tmx[3][0] ? `<p><span class="k">No allocation record</span><span><b>${pct0(tmx[3][0], tg)}</b> of given <small class="tch">(appointment rows made at the deal)</small></span></p>` : '') + `</div>` : '') +
      (bigShare < 50 ? `<p class="tfew">Most of these appointments sit with TMEs who fixed fewer than ${TMIN} in these dates, so few gaps can pass the usual swing. Longer dates: ${PRESETS.filter(q => q.k === 'lq' || q.k === 'fytd').map(q => `<button type="button" class="lnk on-navy" data-tpre="${q.k}">${esc(q.label)}</button>`).join(' · ')}</p>` : '') };
  }
  // TME mode's sections (2026-10-30, the user: too much scrolling): one at a time, picked on a row of tabs that stays under
  // the top bar; the band's panels sit in the Summary tab. ME mode shows its cards as before
  // 2026-10-31 (the user): the TME teams, where their appointments went and the ME managers' teams share one tab, in that
  // order (his sketch: TME teams on top, the ME managers below)
  const SECS = { sum: ['#sumCard'], teams: ['.tmstrip', '#flowCard', '#mgrCard'], tmes: ['.tmcard'] };
  const secOn = s => !TM || V.tsec === s;
  function showSec() {
    const nav = $('#tSec'); if (!nav) return;
    nav.hidden = !TM; if (!TM) return;
    nav.querySelectorAll('[data-sec]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.sec === V.tsec)));
    for (const [k, sels] of Object.entries(SECS)) for (const sel of sels) { const e = $(sel); if (e) e.hidden = k !== V.tsec; }
  }
  function setSec(s) {
    if (!SECS[s] || s === V.tsec) return;
    V.tsec = s; showSec(); writeHash();
    if (s === 'teams') { renderTeams(); renderFlow(); renderMgrs(); }   // drawn to the width they now have
    const n = $('#tSec'), top = n.getBoundingClientRect().top + scrollY - $('#topbar').offsetHeight;
    if (scrollY > top) scrollTo(0, top);   // back to the top of the section when it was scrolled past
  }
  $('#tSec') && $('#tSec').addEventListener('click', ev => { const b = ev.target.closest('[data-sec]'); if (b) setSec(b.dataset.sec); });
  // the Summary tab: where to look first beside the TMEs' counts, allocation timing, across managers and the trend
  function renderSummary() {
    const card = $('#sumCard'); if (!card) return;
    if (!TM) { card.hidden = true; return; }
    const s = tmeSide();   // 2026-10-31: appointments given first (the main KPI), then the deals view
    $('#sumL').innerHTML = s.lookA + (s.look || `<div class="mv tmv"><h3>Through deals <span class="h3s">· the added view</span></h3><p class="mu sumnone">No TME is past the usual swing below the same MEs on conversion in these dates.${V.to - V.from < 27 ? ' Longer dates give more TMEs enough appointments to compare.' : ''}</p></div>`);
    $('#sumR').innerHTML = s.rest + movers() + trend();
    // the counts on the tabs
    const nP = MEROWS.filter(r => !notTme(r.me)).length;   // as the TMEs list: with appointments or deals closed
    const sm = (k, v) => { const e = $(`#tSec [data-sec="${k}"] small`); if (e) e.textContent = v ? n0(v) : ''; };
    sm('tmes', nP);
  }
  $('#sumCard') && $('#sumCard').addEventListener('click', ev => {
    const o = ev.target.closest('[data-tord]'); if (o) return orderZ(o.dataset.tord);
    const m = ev.target.closest('[data-me]'); if (m) return openMe(+m.dataset.me);
    const tp = ev.target.closest('[data-tpre]'); if (tp) { setPreset(tp.dataset.tpre); return render(true); }
  });
  // a count on TME mode's band orders the Overview's TME list by it: the TMEs, as funnels, furthest below (or above) the
  // same MEs first, allowing for size (the gap in standard errors); rates on too few appointments last
  function orderZ(k) {
    const upk = k.endsWith('u'); k = upk ? k.slice(0, -1) : k;
    if (meStyle() !== 'bars') MS[MS_KEY()] = 'bars';
    if (TM) { V.tsec = 'tmes'; showSec(); writeHash(); }   // the TMEs tab
    V.ovSort = k; V.ovDir = upk || k === 'short' || k === 'pace' ? 'desc' : 'asc';
    if (lvl() < 3) setLevel(3); else { OPG = 0; renderLadder(); renderList(); }
    $('.tmcard').scrollIntoView({ block: 'start' });
  }
  const zSay = () => TM && V.ovSort === 'pace' ? ` · <b>most appointments below their TME team's usual pace first</b> (TMEs with ${PACE_PD}+ days present); the rest after. <button type="button" class="lnk" data-ovreset="1">Most appointments first</button>`
    : TM && V.ovSort === 'short' ? ` · <b>most deals closed below what the same MEs' rate gives first</b> (TMEs with ${TMIN}+ in the base); the rest after. <button type="button" class="lnk" data-ovreset="1">Most appointments first</button>`
    : TM && (V.ovSort === 'zA' || V.ovSort === 'zC') ? ` · <b>${V.ovSort === 'zC' ? 'conversion' : 'attended %'} ${V.ovDir === 'asc' ? 'furthest below' : 'furthest above'} the same MEs first</b>, allowing for size: a gap on many appointments comes before the same gap on a few; rates on fewer than ${TMIN} last. <button type="button" class="lnk" data-ovreset="1">Most appointments first</button>` : '';
  function movers() {
    const { SUB } = teamIndex(MEROWS);
    const kids = (KIDS[V.scope] || []).filter(k => k !== OUTN && SUB.has(k));
    const lvlName = kids.length ? (NDEP(kids[0]) === 1 ? 'managers' : 'team leaders') : W.p;
    const units = kids.length ? kids.map(k => ({ name: NNAME(k), s: sumRows(SUB.get(k)) })) : MEROWS.filter(r => r.n > 0).map(r => ({ name: r.name, s: r }));
    const minN = kids.length ? Math.max(MINR, 10) : MINR, ok = units.filter(u => u.s.n >= minN), out = [];
    const span = (key, lab) => {
      const v = ok.filter(u => u.s[key] !== null && u.s[key] !== undefined && isFinite(u.s[key])).sort((x, y) => x.s[key] - y.s[key]);
      if (v.length < 2 || Math.round(v[0].s[key]) === Math.round(v[v.length - 1].s[key])) return;
      out.push(`<span class="k">${lab}</span>${cell(v[0].name, fPi(v[0].s[key]))}${cell(v[v.length - 1].name, fPi(v[v.length - 1].s[key]))}`);
    };
    // ME mode (2026-11-02, the user: text-heavy; polish): a grid, lowest | highest, names cut with ... (whole on hover)
    const cell = (nm, v, pre, post) => `<span class="mvc" title="${esc(`${pre ? pre + ': ' : ''}${nm} ${v}${post ? ' ' + post : ''}`)}">${pre ? `<span class="mvx">${pre}</span>` : ''}<span class="mvn">${esc(nm)}</span><b class="mvf tn">${v}</b>${post ? `<small>${post}</small>` : ''}</span>`;
    if (TM) {   // TME mode (2026-10-30, the review): raw rates would compare lead types (Super Cat converts far above the rest)
      const f = x => `${x > 0 ? '+' : x < 0 ? MINUS : ''}${Math.abs(Math.round(x))} pts`;
      const spanL = (k, lab) => { const v = ok.map(u => ({ u, x: lfPts(u.s, k) })).filter(o => o.x !== null).sort((a, b) => a.x - b.x); if (v.length < 2 || Math.round(v[0].x) === Math.round(v[v.length - 1].x)) return;
        out.push(`<p><span class="k">${lab}</span><span>lowest <b>${esc(v[0].u.name)}</b> ${f(v[0].x)} · highest <b>${esc(v[v.length - 1].u.name)}</b> ${f(v[v.length - 1].x)}</span></p>`); };
      spanL('a', 'Attended % vs same MEs'); spanL('c', 'Conversion vs same MEs');
    } else { span('attP', 'Attended %'); span('conv', 'Conversion'); }
    const na = units.filter(u => u.s.o[3] > 0).sort((x, y) => y.s.o[3] - x.s.o[3]);
    const nSpan = out.length;
    if (na.length > 1 && CUR.o[3] >= 5) out.push(TM ? `<p><span class="k">Not Available</span><span>most: <b>${esc(na[0].name)}</b>, ${n0(na[0].s.o[3])} of ${n0(CUR.o[3])}</span></p>`
      : `<span class="k">Not Available</span><span class="mvw">${cell(na[0].name, n0(na[0].s.o[3]), 'most', `of ${n0(CUR.o[3])}`)}</span>`);
    if (!out.length) return '';
    const h3 = `<h3>Across ${lvlName}${ok.length < units.length ? ` <small>with ${minN}+ appointments given</small>` : ''}</h3>`;
    return TM ? `<div class="mv tmv">${h3}${out.join('')}</div>` : `<div class="mv">${h3}<div class="mvg">${nSpan ? '<span></span><span class="mvh">Lowest</span><span class="mvh">Highest</span>' : ''}${out.join('')}</div></div>`;
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
    const W = 300, H = 52, x = b => 4 + b / Math.max(1, nb - 1) * (W - 8), y = v => H - 4 - Math.max(0, Math.min(100, v)) / 100 * (H - 8);
    const path = k => pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.b).toFixed(1)},${y(p[k]).toFixed(1)}`).join('');
    const dots = pts.filter(p => p.sel).map(p => `<path class="da" d="M${x(p.b).toFixed(1)},${y(p.a).toFixed(1)}h0"/><path class="dc" d="M${x(p.b).toFixed(1)},${y(p.c).toFixed(1)}h0"/>`).join('');
    const tips = pts.map(p => `<rect x="${(x(p.b) - W / nb / 2).toFixed(1)}" y="0" width="${(W / nb).toFixed(1)}" height="${H}" fill="transparent"><title>${esc(daily ? dayName(p.d0) : fRange(p.d0, p.d1))}: attended ${Math.round(p.a)}%, conversion ${Math.round(p.c)}%</title></rect>`).join('');
    // the last values beside the line ends (2026-11-02, polish), kept 14 px apart; the dashed line's 50% beside it
    const lp = pts[pts.length - 1]; let ya = y(lp.a), yc = y(lp.c);
    if (Math.abs(ya - yc) < 14) { const m = (ya + yc) / 2, up = ya <= yc ? -7 : 7; ya = m + up; yc = m - up; }
    const y5 = y(50), lab50 = Math.abs(y5 - ya) >= 13 && Math.abs(y5 - yc) >= 13 ? `<span class="t50" style="top:${(y5 - 7).toFixed(1)}px">50%</span>` : '';
    return `<div class="trd"><h3 title="${esc(`Dashed line = 50% · dots = the dates shown · point at a ${daily ? 'day' : 'week'} for its numbers`)}">${daily ? 'Last 4 weeks, each usual day' : 'Last 12 weeks, each week'}</h3>` +
      `<div class="trw"><svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Attended % and conversion, ${daily ? 'each day of the last 4 weeks' : 'each week of the last 12 weeks'}"><path class="g50" d="M0,${y(50).toFixed(1)}H${W}"/><path class="la" d="${path('a')}"/><path class="lc" d="${path('c')}"/>${dots}${tips}</svg>` +
      `<span class="te" style="top:${(ya - 8).toFixed(1)}px" title="Attended %, ${esc(daily ? dayName(lp.d0) : fRange(lp.d0, lp.d1))}">${Math.round(lp.a)}%</span><span class="te" style="top:${(yc - 8).toFixed(1)}px" title="Conversion, ${esc(daily ? dayName(lp.d0) : fRange(lp.d0, lp.d1))}">${Math.round(lp.c)}%</span>${lab50}</div>` +
      `<p class="tkey"><span><i class="a"></i>Attended %</span><span><i class="c"></i>Conversion</span></p></div>`;
  }
  $('#hero').addEventListener('click', ev => {
    const s = ev.target.closest('[data-scope]'); if (s) return setScope(+s.dataset.scope);
    const o = ev.target.closest('[data-o]'); if (o) return openList(o.dataset.g !== undefined ? { o: +o.dataset.o, g: +o.dataset.g } : { o: +o.dataset.o });
    if (ev.target.closest('[data-open="deals"]')) return openDeals();
    const dy = ev.target.closest('[data-day]'); if (dy) { const t = +dy.dataset.day, p = PRESETS.find(x => x.a === t && x.b === t); if (p) setPreset(p.k); else setRange(t, t); return render(true); }
    const g = ev.target.closest('[data-go="how"]'); if (g) return $('#how').scrollIntoView({ block: 'start' });
    const to = ev.target.closest('[data-tord]'); if (to) return orderZ(to.dataset.tord);   // TME mode: order the TMEs by a gap
    const tp = ev.target.closest('[data-tpre]'); if (tp) { setPreset(tp.dataset.tpre); return render(true); }
    const pm = ev.target.closest('[data-me]'); if (pm) return openMe(+pm.dataset.me);   // a TME named on the band
    const w = ev.target.closest('[data-view]'); if (w && w.dataset.view !== V.view) setView(w.dataset.view);
  });
  function showViews() {
    $('#vTeam').hidden = V.view !== 'team'; $('#vTable').hidden = V.view !== 'table'; $('#vChecks').hidden = V.view !== 'checks';
    $('#toChecks').closest('p').hidden = TM || V.view === 'checks';   // the record checks are about MEs
  }
  function setView(v) {
    v = ['checks', 'table'].includes(v) && !(TM && v === 'checks') ? v : 'team';
    V.view = v;
    closeCol(); showViews(); renderBand(); renderLadder(); renderList(); renderX(); writeHash(); scrollTo(0, 0);
  }
  // ME | TME (2026-10-29): the page reloads in the other mode with the same dates and view; a team picked is left behind
  // (the two modes have different teams)
  function setMode(tme) {
    if (tme === TM) return;
    try { localStorage.setItem(MODE_KEY, tme ? 'tme' : 'me'); } catch (e) { /* the link carries it */ }
    const h = new URLSearchParams(location.hash.slice(1)); h.delete('team'); h.delete('tl'); h.delete('tg'); h.delete('tby');
    if (h.get('view') === 'tme' || h.get('view') === 'checks') h.delete('view');
    if (tme) h.set('mode', 'tme'); else h.delete('mode');
    // the dates are a master filter: always carried to the other mode (2026-10-31, the user). The link leaves out a mode's
    // default dates, and the two defaults differ (ME the latest day, TME this month), so they are written in full here
    h.delete('period'); h.delete('from'); h.delete('to');
    if (V.preset) h.set('period', V.preset); else { h.set('from', iso(dOf(V.from))); h.set('to', iso(dOf(V.to))); }
    const s = h.toString(); history.replaceState(null, '', s ? '#' + s : location.pathname);
    document.body.classList.add('switching');
    location.reload();
  }
  document.body.classList.toggle('tmev', TM);   // TME mode's amber
  $('#modeSw').addEventListener('click', ev => { const b = ev.target.closest('[data-mode]'); if (b) setMode(b.dataset.mode === 'tme'); });


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

  /* ---------- Super Cat skewness (2026-10-19, for Kushal: is Super Cat still going to the same MEs?) ---------- */
  // The day's factor: how much Super Cat the MEs who got the day's Super Cat appointments usually do (their Super Cat share
  // of attended appts in the 12 working days before), against the same for the MEs who got the day's OTHER teams'
  // appointments (not all of them: that included the Super Cat ones and read lower on days with more Super Cat).
  // 1.0 = Super Cat goes to the same kind of MEs as the other teams' appointments. No cut-off list in the factor, so it moves only when where Super Cat goes
  // really changes (a list of 'heavy' MEs made it jump: 3.2x -> 2.5x on 16-17 Oct, partly because a holiday left the window).
  // The heavy MEs (8+ attended appts in the 12 working days, more than twice Mumbai's Super Cat share) are listed beside it.
  // Working day = a day with 100+ appointments. Always all Mumbai, whatever team the page shows.
  // Status against the 12 working days before uses a margin, so an ME hovering at the line does not flip: newly heavy =
  // clearly normal before (under 1.5x Mumbai's share; 3+ attended appts before are enough to tell), back to normal =
  // clearly normal now (8+ attended appts); in between = close to the line.
  const SK_K = 12, SK_MIN = 8, SK_DAYMIN = 100, SK_NEAR = 1.5, SK_SC = TEAMS.map(t => t === 'Super Cat');
  const skRatio = (mx, m, minV = SK_MIN) => { const v = mx.v.get(m); return v && v[0] >= minV && mx.sh ? (v[1] / v[0]) / mx.sh : null; };
  const SKD = (() => { const d = Array.from({ length: LAST + 1 }, () => []); for (let i = 0; i < N; i++) d[AD[i]].push(i); return d; })();
  const SK_WORK = []; for (let d = 0; d <= LAST; d++) if (SKD[d].length >= SK_DAYMIN) SK_WORK.push(d);
  // the 12 working days before day d (after skipping `skip` more working days back)
  const skBefore = (d, skip = 0) => { let i = SK_WORK.findIndex(x => x >= d); if (i < 0) i = SK_WORK.length; const e = Math.max(0, i - skip); return SK_WORK.slice(Math.max(0, e - SK_K), e); };
  const skRange = (a, b) => { const o = []; for (let d = Math.max(0, a); d <= b; d++) o.push(d); return o; };
  function skMix(days, minV) {   // attended appts on these days: Mumbai's Super Cat share, each ME's [attended appts, Super Cat ones], the heavy MEs
    const v = new Map(); let n = 0, s = 0;   // per ME: [attended appts, Super Cat ones, appointments given, Super Cat ones]
    for (const d of days) for (const i of SKD[d]) {
      const sc = SK_SC[ATT[i]] ? 1 : 0, x = v.get(AME[i]) || [0, 0, 0, 0]; x[2]++; x[3] += sc; v.set(AME[i], x);
      if (AO[i] > 2) continue;
      n++; s += sc; x[0]++; x[1] += sc;
    }
    const sh = n ? s / n : 0, heavy = new Set();
    for (const [m, x] of v) if (x[0] >= minV && x[0] && x[1] / x[0] >= 2 * sh) heavy.add(m);
    return { sh, v, heavy };
  }
  const SK_DAY = new Map();
  function skDay(d) {
    if (SK_DAY.has(d)) return SK_DAY.get(d);
    let r = null; const t = SKD[d], ds = skBefore(d);
    if (t && t.length >= SK_DAYMIN && ds.length === SK_K) {
      const M = skMix(ds, 1), u = m => { const x = M.v.get(m); return x && x[0] >= 4 ? x[1] / x[0] : M.sh; };
      let sc = 0, scU = 0, oU = 0;
      for (const i of t) { const v = u(AME[i]); if (SK_SC[ATT[i]]) { sc++; scU += v; } else oU += v; }
      const o = t.length - sc;
      if (sc && o) r = { d, sc, o, n: t.length, scU: scU / sc, oU: oU / o, f: (scU / sc) / (oU / o) };
    }
    SK_DAY.set(d, r); return r;
  }
  const skDays = (a, b) => { const o = []; for (let d = Math.max(0, a); d <= b; d++) { const r = skDay(d); if (r) o.push(r); } return o; };
  // several days together: each day's usual shares, weighted by its appointments
  const skSum = rs => { if (!rs.length) return null; const sc = rs.reduce((t, r) => t + r.sc, 0), o = rs.reduce((t, r) => t + r.o, 0), scU = rs.reduce((t, r) => t + r.sc * r.scU, 0) / sc, oU = rs.reduce((t, r) => t + r.o * r.oU, 0) / o; return { sc, o, n: sc + o, scU, oU, f: scU / oU }; };
  const skAvg = (d, k = 6) => { const o = []; for (let x = d; x >= 0 && o.length < k; x--) { const r = skDay(x); if (r) o.push(r.f); } return o.length ? o.reduce((s, v) => s + v, 0) / o.length : null; };
  const fWD = d => `${WD[dOf(d).getUTCDay()]} ${fDate(dOf(d))}`;
  const pc0 = v => Math.round(v * 100) + '%';
  let SK = null;   // what the card shows (for the list)
  // the card is hidden while the user works on it (31 Oct 2026): shown only with sk=1 in the page link, kept in the link
  const SK_ON = new URLSearchParams(location.hash.slice(1)).get('sk') === '1' && !META.mgr;
  function renderSkew() {
    const box = $('#skBody'); if (!box) return;
    if (TM || !SK_ON) { $('#skCard').hidden = true; SK = null; return; }   // about MEs; hidden unless sk=1 (the user, 31 Oct 2026: still working on it)
    $('#skCard').hidden = false;
    let D = V.to; while (D > 0 && !skDay(D)) D--;
    const one = V.from === V.to, x = one ? skDay(D) : skSum(skDays(V.from, V.to));
    if (!x) { $('#skSub').textContent = 'Not enough appointments in these dates'; box.innerHTML = '<p class="empty">Too few appointments to judge where Super Cat went.</p>'; SK = null; return; }
    const prev = one ? (() => { for (let d = D - 1; d > 0; d--) { const r = skDay(d); if (r) return r; } return null; })() : (V.pa !== null ? skSum(skDays(V.pa, V.pb)) : null);
    const avg = skAvg(D), avgWk = skAvg(D - 7);
    const all = skDays(0, D).map(r => r.f).sort((a, b) => a - b), band = all.length >= 8 ? [all[Math.floor(all.length / 4)], all[Math.floor(all.length * 3 / 4)]] : null;
    const when = one ? fWD(D) : fRange(V.from, V.to);
    const ch = (a, b, lab) => { if (a === null || b === null || b === undefined) return ''; const v = +(a - b).toFixed(1); return v ? `<b class="${v < 0 ? 'better' : 'worse'}">${v < 0 ? '▼' : '▲'} ${Math.abs(v).toFixed(1)}×</b> ${lab}` : `<b>no change</b> ${lab}`; };
    // the MEs: judged on the 12 working days before D, against the 12 working days before those
    const win = skBefore(D), win0 = skBefore(D, SK_K), now = skMix(win, SK_MIN), was = skMix(win0, SK_MIN);
    const L = [...now.heavy].map(m => { const rb = skRatio(was, m, 3); return { m, rb, st: rb !== null && rb >= SK_NEAR ? 'still' : 'new' }; });
    const back = [...was.heavy].filter(m => !now.heavy.has(m));
    const backOk = back.filter(m => { const r = skRatio(now, m); return r !== null && r < SK_NEAR; }), still = L.filter(r => r.st === 'still').length, nw = L.length - still;
    const mixOf = f => { let n = 0, s = 0; for (const [m, v] of now.v) if (v[0] >= SK_MIN && f(m)) { n += v[0]; s += v[1]; } return n ? Math.round(s / n * 100) : 0; };
    const leads = L.filter(r => ME_LEAD[r.m] >= 0).length, leadSc = mixOf(m => ME_LEAD[m] >= 0), othSc = mixOf(m => ME_LEAD[m] < 0);
    const wl = w => w.length ? `${fDate(dOf(w[0]))} – ${fDate(dOf(w[w.length - 1]))}` : '';
    SK = { D, now, was, L, back, backOk, win, win0, wl };
    $('#skSub').textContent = `${when} · where Super Cat went, all ${META.city} · 1.0× = no lean · lower is better`;
    // the chart: each day for about three months up to D, the 6-day average, the usual band, the fair line
    const T = skDays(Math.max(0, D - 95), D), Wd = 620, Hd = 200, L0 = 30, R0 = 8, T0 = 8, B0 = 20, y1 = Math.max(3, Math.ceil(Math.max(...T.map(r => r.f)) + .2));
    const X = i => L0 + (T.length > 1 ? i / (T.length - 1) : .5) * (Wd - L0 - R0), Y = v => T0 + (1 - v / y1) * (Hd - T0 - B0);
    let g = band ? `<rect class="skband" x="${L0}" width="${Wd - L0 - R0}" y="${Y(band[1])}" height="${Y(band[0]) - Y(band[1])}"/>` : '';
    for (let v = 0; v <= y1; v++) g += `<line class="skgl" x1="${L0}" x2="${Wd - R0}" y1="${Y(v)}" y2="${Y(v)}"/><text class="skax" x="${L0 - 5}" y="${Y(v) + 3.5}" text-anchor="end">${v}×</text>`;
    g += `<line class="skfair" x1="${L0}" x2="${Wd - R0}" y1="${Y(1)}" y2="${Y(1)}"/><text class="skfairt" x="${L0 + 4}" y="${Y(1) - 4}">no lean</text>`;
    T.forEach((r, i) => { if (i === 0 || dOf(T[i - 1].d).getUTCMonth() !== dOf(r.d).getUTCMonth()) g += `<text class="skax" x="${X(i)}" y="${Hd - 5}">${MON3[dOf(r.d).getUTCMonth()]}</text>`; });
    g += `<path class="skavg" d="${T.map((r, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)},${Y(skAvg(r.d)).toFixed(1)}`).join('')}"/>`;
    g += T.map((r, i) => `<circle class="skdt${r.d >= V.from && r.d <= V.to ? ' on' : ''}" cx="${X(i)}" cy="${Y(r.f)}" r="${r.d >= V.from && r.d <= V.to ? 4.5 : 3}"/>`).join('');
    box.innerHTML =
      `<div><div class="skbig">${x.f.toFixed(1)}<small>×</small></div><div class="sklab">Super Cat went to MEs who already do ${x.f.toFixed(1)} times as much Super Cat as those who got the other teams' appointments</div>` +
      `<div class="skex">${esc(when)}: the <b>${n0(x.sc)} Super Cat appointments</b> went to MEs whose attended appts are usually <b>${pc0(x.scU)}</b> Super Cat; the <b>${n0(x.o)} other teams' appointments</b> went to MEs whose attended appts are usually <b>${pc0(x.oU)}</b> Super Cat.</div>` +
      `<div class="skchg">${[ch(x.f, prev && prev.f, one && prev ? `from ${WD[dOf(prev.d).getUTCDay()]}` : 'from the period before'), avg !== null ? `6-day average <b>${avg.toFixed(1)}×</b>${avgWk !== null ? ` (${ch(avg, avgWk, 'in a week')})` : ''}` : ''].filter(Boolean).join(' · ')}</div></div>` +
      `<div><div class="skk">Each day${T.length ? ' since ' + fDate(dOf(T[0].d)) : ''}${band ? `<span>usual ${band[0].toFixed(1)}–${band[1].toFixed(1)}×</span>` : ''}</div>` +
      `<svg class="skc" viewBox="0 0 ${Wd} ${Hd}" role="img" aria-label="Skewness factor each day, with the 6-day average">${g}<line class="skcross" x1="0" x2="0" y1="${T0}" y2="${Hd - B0}" visibility="hidden"/><rect class="skhit" x="${L0}" y="0" width="${Wd - L0 - R0}" height="${Hd}"/></svg>` +
      `<div class="skkey"><span><i class="k1"></i>a day (click one to show it)</span><span><i class="k2"></i>6-day average</span>${band ? '<span><i class="k3"></i>usual range</span>' : ''}<span><i class="k4"></i>no lean (1.0×)</span></div></div>` +
      `<div><div class="skk">Super Cat-heavy MEs<span>${wl(win)}</span></div>` +
      `<div class="sknote" style="margin-top:0"><b>${L.length} MEs</b> do more than twice ${esc(META.city)}'s Super Cat share of attended appts (${Math.round(now.sh * 100)}%) in the last ${SK_K} working days. Against the ${SK_K} before:</div>` +
      `<div class="sktrio"><div title="Super Cat-heavy in the ${SK_K} working days before, clearly normal now (under ${SK_NEAR}× ${esc(META.city)}'s share)"><b class="better">${backOk.length}</b><span>back to normal</span></div>` +
      `<div title="Super Cat-heavy now, and heavy or close to it before"><b>${still}</b><span>still heavy</span></div>` +
      `<div title="Super Cat-heavy now, clearly normal before (under ${SK_NEAR}× ${esc(META.city)}'s share)"><b class="${nw ? 'worse' : ''}">${nw}</b><span>newly heavy</span></div></div>` +
      (L.length ? `<div class="sknote"><b>${leads} of the ${L.length}</b> lead a team: team leaders do <b>${leadSc}%</b> of their attended appts on Super Cat, other MEs <b>${othSc}%</b>.</div>` : '') +
      `<button type="button" class="btn skbtn" id="skOpen">See the ${L.length + backOk.length} MEs</button></div>`;
    const sv = box.querySelector('svg.skc');
    const at = ev => { const r = sv.getBoundingClientRect(), xv = (ev.clientX - r.left) / r.width * Wd; return Math.max(0, Math.min(T.length - 1, Math.round((xv - L0) / (Wd - L0 - R0) * (T.length - 1)))); };
    sv.addEventListener('mousemove', ev => {
      if (!T.length) return; const i = at(ev), r = T[i], c = sv.querySelector('.skcross'), a = skAvg(r.d);
      c.setAttribute('x1', X(i)); c.setAttribute('x2', X(i)); c.setAttribute('visibility', 'visible');
      tip(`<b>${fWD(r.d)}: ${r.f.toFixed(1)}×</b>${a !== null ? ` (6-day average ${a.toFixed(1)}×)` : ''}<br>${r.sc} Super Cat appointments went to MEs whose attended appts are usually ${pc0(r.scU)} Super Cat; the ${r.o} other teams' ones to MEs whose attended appts are usually ${pc0(r.oU)}`, ev);
    });
    sv.addEventListener('mouseleave', () => { untip(); sv.querySelector('.skcross').setAttribute('visibility', 'hidden'); });
    sv.addEventListener('click', ev => { if (!T.length) return; const t = T[at(ev)].d, p = PRESETS.find(z => z.a === t && z.b === t); if (p) setPreset(p.k); else setRange(t, t); render(true); });
  }
  // the list: in the side window
  function openSkew() {
    if (!SK) return;
    const { D, now, was, L, back, win, win0, wl } = SK, Mo = [];
    for (let m = new Date(Date.UTC(FY0.getUTCFullYear(), FY0.getUTCMonth(), 1)); m <= dOf(D - 1); m = new Date(Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1))) {
      const a = Math.max(0, Math.round((m - FY0) / 864e5)), b = Math.min(D - 1, Math.round((Date.UTC(m.getUTCFullYear(), m.getUTCMonth() + 1, 1) - FY0) / 864e5) - 1);
      Mo.push({ k: MON3[m.getUTCMonth()], x: skMix(skRange(a, b), 15) });
    }
    const day = new Map(); for (const i of SKD[D]) { const x = day.get(AME[i]) || [0, 0]; x[0]++; if (SK_SC[ATT[i]]) x[1]++; day.set(AME[i], x); }
    const who = m => {
      const l = ME_LEAD[m];
      if (l >= 0) return DEPTH[l] === 0 ? 'ME head' : DEPTH[l] === 1 ? 'Manager' : `Team leader · Manager ${esc(MGRS[MGUP[l]][1])}`;
      const mg = mgOf(ME_NODE[m]); return mg >= 0 ? 'Manager ' + esc(MGRS[mg][1]) : '';
    };
    const pcOf = (mx, m) => { const v = mx.v.get(m); return v && v[0] ? Math.round(v[1] / v[0] * 100) : null; };
    const gv = m => { const x = now.v.get(m); return x && x[2] ? Math.round(x[3] / x[2] * 100) : null; };
    const row = (m, st) => ({ m, st, sc: pcOf(now, m), g: gv(m), was: pcOf(was, m), n: (now.v.get(m) || [0])[0], dsc: (day.get(m) || [0, 0])[1], dn: (day.get(m) || [0, 0])[0] });
    const byAttd = r => r.st !== 'back' && r.g !== null && r.g < 2 * now.sh * 100 * .75;   // heavy through what they attend, not what they are given
    const rows = [...L.map(r => row(r.m, r.st)).sort((a, b) => b.dsc - a.dsc || b.sc - a.sc), ...SK.backOk.map(m => row(m, 'back')).sort((a, b) => b.was - a.was)];
    const notCounted = back.filter(m => !SK.backOk.includes(m));
    const stTxt = { still: 'still', new: 'new', back: 'back to normal' };
    const lvl = (mx, m) => { const r = skRatio(mx, m, 15); return r === null ? ['few', 'too few attended appts to judge'] : r >= 2 ? ['on', 'Super Cat-heavy'] : r >= SK_NEAR ? ['near', 'close to the line'] : ['', 'normal mix']; };
    const strip = m => `<span class="skstrip">${Mo.map(x => { const [c, t] = lvl(x.x, m); return `<i class="${c}" title="${x.k}: ${t}"></i>`; }).join('')}</span>`;
    openDrawer(`<h2 id="drawerH">Super Cat-heavy MEs</h2><p class="where">${rows.length} MEs: the ${L.length} doing more than twice ${esc(META.city)}'s Super Cat share of attended appts (${Math.round(now.sh * 100)}%), judged on the ${SK_K} working days ${wl(win)}. , and the ${SK.backOk.length} back to normal. Super Cat share: of their attended appts · of the appointments given to them. Before = the ${SK_K} working days before that: <b>still</b> = heavy or close to it then, <b>new</b> = clearly normal then, <b>back to normal</b> = heavy then, clearly normal now (under ${SK_NEAR}×). By month (15+ attended appts): dark = heavy, light = close to the line (${SK_NEAR}–2×), blank = normal, outlined = too few attended appts. Heavy MEs first, most Super Cat on ${fWD(D)} first; click an ME for their page.</p>` +
      (rows.length ? `<div class="dlw"><table class="dl sktbl"><thead><tr><th>ME</th><th>Attd appts</th><th>Super Cat share<br><span class="mu">attd · given</span></th><th>Before</th><th>${fDate(dOf(D))}<br><span class="mu">SC / all</span></th><th>By month<br><span class="skmo">${Mo.map(x => `<span>${x.k[0]}</span>`).join('')}</span></th><th></th></tr></thead><tbody>` +
        rows.map(r => `<tr><td><button type="button" class="lnk" data-me="${r.m}">${esc(MES[r.m][1])}</button><small class="pid">${who(r.m)}${byAttd(r) ? ` · <span class="skwhy" title="Given ${r.g}% Super Cat, close to normal, but ${r.sc}% of what they attend: they skip more of the other teams' appointments">heavy by what they attend</span>` : ''}</small></td><td class="tn">${r.n}</td><td class="tn">${r.sc}% · <span class="mu">${r.g === null ? '—' : r.g + '%'}</span></td><td class="tn">${r.was === null ? '—' : r.was + '%'}</td>` +
          `<td class="tn">${r.dn ? `${r.dsc} / ${r.dn}` : '—'}</td><td>${strip(r.m)}</td><td><span class="skst ${r.st}" title="${r.st === 'back' ? `Super Cat-heavy in the ${SK_K} working days before, clearly normal now` : r.st === 'new' ? `clearly normal (or fewer than 3 attended appts) in the ${SK_K} working days before` : `Super Cat-heavy or close to it in the ${SK_K} working days before`}">${stTxt[r.st]}</span></td></tr>`).join('') + `</tbody></table></div>` : '<p class="empty">No Super Cat-heavy MEs.</p>') +
      (notCounted.length ? `<p class="cmpn">Also Super Cat-heavy in the ${SK_K} working days before (${wl(win0)}) but not counted as back to normal yet: ${notCounted.map(m => { const n = (now.v.get(m) || [0])[0], r = skRatio(now, m); return `<button type="button" class="lnk" data-me="${m}">${esc(MES[m][1])}</button> (${n < SK_MIN ? 'too few attended appts now' : `${pcOf(now, m)}% now, close to the line`})`; }).join(' · ')}.</p>` : ''));
  }
  $('#skCard') && $('#skCard').addEventListener('click', ev => { if (ev.target.closest('#skOpen')) openSkew(); });

  /* ---------- where the appointments came from: three tiles ---------- */
  // TME mode (2026-10-30, the user: every TME team on its own, not under 'Other teams'): the teams in order, those with a
  // colour of their own first (Super Cat, Hot Data, Online, Revival (Expiry)), then the rest by appointments given; the
  // rest share one grey (the validated palette has no more distinct colours); the grouping settings stay for ME mode
  const OWN_COL = ['Super Cat', 'Hot Data', 'Online', EXP];
  const teamCol = t => OWN_COL.includes(TEAMS[t]) ? GDEF[TEAMS[t]].c : '#8C97A8';
  const teamOrder = (list, size) => list.slice().sort((a, b) => { const ia = OWN_COL.indexOf(TEAMS[a]), ib = OWN_COL.indexOf(TEAMS[b]); return (ia < 0 ? 9 : ia) - (ib < 0 ? 9 : ib) || size(b) - size(a); });
  const lvBar = (w, cls, txt) => `<span class="ml ${cls}"><i style="width:${Math.max(w, 1.5).toFixed(1)}%">${w >= 42 ? txt : ''}</i>${w < 42 ? `<em>${txt}</em>` : ''}</span>`;
  const miniFun = (g, a, d) => `<span class="mini">${lvBar(100, 'g', `${plural(g, 'appointment')} given`)}${lvBar(pc(a, g) || 0, 'a', `${n0(a)} attended`)}${lvBar(Math.min(100, pc(d, g) || 0), 'd', `${plural(d, 'deal')} closed`)}</span>`;
  // a box's bar (2026-10-31, the user liked the ME box: labels in the bars): the longest label that fits in the bar, else
  // beside it, else the short one; tw = the bar track's width in px. labs = [full, short]
  function fitBar(w, cls, labs, tw, title) {
    const W = Math.max(w, 1.5), px = W / 100 * tw, tx = s => s.length * 6.1 + 14;
    let inn = '', out = '';   // each label in turn: in the bar, else beside it; the shortest beside it when none fits
    for (const s of labs) { if (tx(s) <= px) { inn = s; break; } if (px + tx(s) - 6 <= tw) { out = s; break; } }
    if (!inn && !out) out = labs[labs.length - 1];
    return `<span class="ml ${cls}"${title ? ` title="${esc(title)}"` : ''}><i style="width:${W.toFixed(1)}%">${inn ? esc(inn) : ''}</i>${out ? `<em>${esc(out)}</em>` : ''}</span>`;
  }
  // given, attended, deals closed: widths against appointments given, as the ME box
  const apptBars = (g, a, d, tw) => fitBar(100, 'g', [`${n0(g)} appointments given`, `${n0(g)} given`], tw) +
    fitBar(pc(a, g) || 0, 'a', [`${n0(a)} attended`, n0(a)], tw) + fitBar(Math.min(100, pc(d, g) || 0), 'd', [`${n0(d)} ${d === 1 ? 'deal' : 'deals'} closed`, `${n0(d)} deals`, n0(d)], tw);
  const fL = v => v >= 1e5 ? (v / 1e5).toFixed(1) + ' L' : n0(v);
  
  const callLine = c => c && c[0] ? `<span class="tline tcl" title="${esc(`${n0(c[0])} calls, ${n0(c[1])} connected, ${n0(c[2])} appointments given`)}"><b>${c[0] >= 1e5 ? (c[0] / 1e5).toFixed(1) + ' lakh' : n0(c[0])}</b> calls · <b>${pct0(c[1], c[0])}</b> connected · <b>${c[1] >= APC_MIN ? (c[2] / c[1] * APC_PER).toFixed(1) : '—'}</b> appts / 1,000 connected</span>` : '';
  // a grid of n boxes at least minW wide, the rows as even as they can be (10 boxes: 5 + 5, not 6 + 4)
  function evenCols(el, n, minW) {
    const gap = 8, w = el.clientWidth || (($('#main') || document.body).clientWidth - 94);
    const mx = Math.max(1, Math.floor((w + gap) / (minW + gap))), rows = Math.ceil(Math.max(n, 1) / mx);
    const cols = Math.max(1, Math.ceil(n / rows));
    el.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    return (w - gap * (cols - 1)) / cols;   // a box's width in px
  }
  function renderTeamsTM() {
    const R = CUR, rows = teamRows(R), cr = new Map(teamRows(CITY).map(x => [x.t, x]));
    // each team's TMEs' calls: a TME counts in their team in HR, else the team of most of their appointments in the dates
    const tc = new Map(), off = new Map();
    if (CLN) for (const r of MEROWS) { if (TM && r.me === NOTME) continue; let b = hrTeamOf(r.me), bn = 0; if (b < 0) for (let t = 0; t < NT; t++) { const g = R.meT[(r.me * NT + t) * 3]; if (g > bn) { bn = g; b = t; } } if (b < 0) continue;
      if (r.calls >= DIAL_MIN) { const v = tc.get(b) || [0, 0, 0]; v[0] += r.calls; v[1] += r.conn; v[2] += r.n; tc.set(b, v); } else off.set(b, (off.get(b) || 0) + r.n); }
    const by = new Map(rows.map(x => [x.t, x])), list = teamOrder(rows.map(x => x.t), t => by.get(t).n);
    // the period before, and each team's not-counted appointments by kind (2026-10-30)
    const pr = V.pa !== null && PREV ? new Map(teamRows(PREV).map(x => [x.t, x])) : new Map(), nct = new Map();
    if (NCTT) for (let k = 0; k < NCN; k++) { const d = NCD[k]; if (d < V.from || d > V.to || !ncScope(k) || NCTT[k] >= NT) continue; let m = nct.get(NCTT[k]); if (!m) nct.set(NCTT[k], m = new Map()); m.set(NCK[k], (m.get(NCK[k]) || 0) + 1); }
    // the TME teams as one table (2026-11-02, the user picked mockup 2, 'Leaderboard table', of ten): one row per TME team,
    // the dialer (calls, connected %, appointments per 1,000 connected) and the appointments (given, attended, deals closed,
    // attended % and conversion with their change) in columns, a slim three-part bar for the funnel's shape (against the
    // biggest team), and an 'All TME teams' line that adds up. A row opens the team's window, as the boxes did
    const box = $('#teams'); box.classList.add('ttbl'); box.style.gridTemplateColumns = '';
    $('#tmSub').innerHTML = `By TME team · calls of its TMEs (team in HR) with ${DIAL_MIN}+ dialer calls${pr.size ? ` · ▲▼ = pts against ${esc(prevName())}` : ''} · click a team for its teams and its TMEs`;
    if (!list.length) { box.innerHTML = '<p class="empty">No appointments given or deals closed in these dates.</p>'; return; }
    const one = V.from === V.to, maxG = Math.max(1, ...list.map(t => by.get(t).n)), S = [0, 0, 0, 0, 0, 0], P = [0, 0, 0];
    const dl = (x, what, few) => x === null || few ? '' : `<small class="tdl${x > 0 ? ' up' : x < 0 ? ' dn' : ''}" title="${esc(`${what} against ${prevName()}: ${x > 0 ? '+' : x < 0 ? MINUS : '±'}${Math.abs(x)} pts`)}">${x > 0 ? '▲' : x < 0 ? '▼' : '±'}${Math.abs(x)}</small>`;
    const apcOf = c => one ? null : c[1] >= APC_MIN ? (c[2] / c[1] * APC_PER).toFixed(1) : null;
    const bars = (g, a, d) => `<td class="fbc" aria-hidden="true">${[[g, 'g'], [a, 'a'], [Math.min(d, g || d), 'd']].map(([v, k]) => `<i class="fb ${k}" style="width:${v ? Math.max(1.5, v / maxG * 100).toFixed(1) : 0}%"></i>`).join('')}</td>`;
    const rowsH = list.map(t => {
      const x = by.get(t), g = x.n, a = x.a, d = x.d, few = g < MINR, cx = cr.get(t), c = tc.get(t), offN = off.get(t) || 0, m = nct.get(t), nn = m ? [...m.values()].reduce((s, v) => s + v, 0) : 0;
      S[3] += g; S[4] += a; S[5] += d; if (c) { S[0] += c[0]; S[1] += c[1]; S[2] += c[2]; }
      const p = pr.get(t); if (p) { P[0] += p.n; P[1] += p.a; P[2] += p.d; }
      const why = c && c[0] ? `TMEs with ${DIAL_MIN}+ dialer calls: ${n0(c[0])} calls dialed, ${n0(c[1])} connected, ${n0(c[2])} appointments given${offN ? `; ${n0(offN)} appointments (${pct0(offN, g)}) by TMEs off the dialer are not in these calls` : ''}` : '';
      const sub = [g ? `${pct0(g, R.n)} of all` : 'deals only',
        m ? `<span title="${esc([...m.entries()].sort((a2, b2) => b2[1] - a2[1]).map(([k, c2]) => `${n0(c2)} ${NC.kinds[k]}`).join(' · '))}">not counted ${pct0(nn, g + nn)}</span>` : '',
        CLN && c && c[0] && offN >= g * .05 ? `<span title="${esc(why)}">${pct0(offN, g)} off the dialer</span>` : ''].filter(Boolean).join(' · ');
      const nm = `<td class="nm"><span class="tnm"><i class="cdot" style="background:${teamCol(t)}"></i>${esc(x.name)}</span><small>${sub}</small></td>`;
      const open = `data-t="${t}" tabindex="0" role="button" title="${esc(`Open ${x.name}: its teams and its TMEs`)}"`;
      if (!g) return `<tr ${open}>${nm}${CLN ? `<td class="sep mu l" colspan="3">no appointments in these dates</td>` : ''}<td class="sep">—</td><td>—</td><td>${n0(d)}</td><td>—</td><td>—</td>${bars(0, 0, d)}</tr>`;
      const dial = !CLN ? '' : c && c[0] ? `<td class="sep" title="${esc(why)}">${fL(c[0])}</td><td>${pct0(c[1], c[0])}</td><td title="${esc(one ? 'Shown for 2 days or more' : c[1] < APC_MIN ? `Under ${APC_MIN} connected calls` : why)}">${apcOf(c) ?? '—'}</td>` : `<td class="sep mu l" colspan="3">no TMEs with ${DIAL_MIN}+ dialer calls</td>`;
      const hp = !!p && p.n >= MINR && !few, cv1 = cvr(d, a, g), cv0 = hp ? cvr(p.d, p.a, p.n) : null;
      const dA = hp ? Math.round((pc(a, g) || 0) - (pc(p.a, p.n) || 0)) : null, dC = cv1 !== null && cv0 !== null ? Math.round(cv1 - cv0) : null;
      const fw = few ? ' class="few" title="Few appointments: these rates swing a lot"' : '';
      const city = (v) => scoped() && cx ? `<small class="ct">${esc(META.city)} ${v}</small>` : '';
      return `<tr ${open}>${nm}${dial}<td class="sep"><b>${n0(g)}</b></td><td>${n0(a)}</td><td>${n0(d)}</td>` +
        `<td${fw}><b>${pct0(a, g)}</b>${dl(dA, 'Attended %', few)}${city(cx ? pct0(cx.a, cx.n) : '')}</td><td${fw}><b>${pct0(d, CB() ? g : a)}</b>${dl(dC, 'Conversion', few)}${city(cx ? pct0(cx.d, CB() ? cx.n : cx.a) : '')}</td>${bars(g, a, d)}</tr>`;
    }).join('');
    // the line for all the TME teams: the sums of the lines above (appointments and deals = the band's)
    const tA = pc(S[4], S[3]), tC = cvr(S[5], S[4], S[3]), pA = pc(P[1], P[0]), pC = P[0] ? cvr(P[2], P[1], P[0]) : null;
    const tot = `<tr class="tot"><td class="nm"><span class="tnm">All TME teams</span><small>${plural(list.filter(t => by.get(t).n).length, 'TME team')}</small></td>` +
      (CLN ? `<td class="sep"${R.cl[0] && Math.abs(R.cl[0] - S[0]) >= 1 ? ` title="${esc(`The TMEs with ${DIAL_MIN}+ dialer calls in these dates; all the TMEs' calls: ${n0(R.cl[0])} (the band)`)}"` : ''}>${S[0] ? fL(S[0]) : '—'}</td><td>${S[0] ? pct0(S[1], S[0]) : '—'}</td><td>${S[1] ? apcOf(S) ?? '—' : '—'}</td>` : '') +
      `<td class="sep"><b>${n0(S[3])}</b></td><td>${n0(S[4])}</td><td>${n0(S[5])}</td><td><b>${pct0(S[4], S[3])}</b>${dl(pA === null || tA === null || !P[0] ? null : Math.round(tA - pA), 'Attended %', false)}</td><td><b>${fPi(tC)}</b>${dl(pC === null || tC === null ? null : Math.round(tC - pC), 'Conversion', false)}</td><td></td></tr>`;
    box.innerHTML = `<div class="ttw"><table class="tmt tn"><thead>` +
      `<tr class="gr"><th></th>${CLN ? `<th class="sep" colspan="3">Dialer</th>` : ''}<th class="sep" colspan="5">Appointments</th><th></th></tr>` +
      `<tr><th class="l">TME team</th>${CLN ? `<th class="sep">Calls</th><th>Connected</th><th title="Appointments given per 1,000 connected calls (TMEs with ${DIAL_MIN}+ dialer calls)">Per 1,000 conn.</th>` : ''}<th class="sep">Given</th><th>Attended</th><th>Deals closed</th><th>Attended %</th><th>Conversion</th><th class="fbh">Funnel</th></tr></thead>` +
      `<tbody>${rowsH}</tbody><tfoot>${tot}</tfoot></table></div>` +
      `<p class="hint ttk"><i class="fk g"></i>given <i class="fk a"></i>attended <i class="fk d"></i>deals closed · each bar against the biggest team · conversion = deals closed ${CVOF()}</p>`;
  }
  $('#teams').addEventListener('keydown', ev => { const t = ev.target.closest('tr[data-t]'); if (t && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); openTeamCard(+t.dataset.t); } });   // the table's rows (2026-11-02)
  // a team's card (TME mode): its window; a team inside a group of several gets a window of its own
  function openTeamCard(t) { const gi = GROUP_OF[t]; if (GROUP_OF.filter(g => g === gi).length === 1) openGroup(gi); else openGroup(gi, t); }
  function renderTeams() {
    // one card per TME team with its own small funnel, the view the ME Head knows (kept 2026-10-15, made shorter): three
    // labelled bars (bar width = share of the team's appointments given), then attended % and conversion; rates grey
    // under the page's minimum
    if (TM) return renderTeamsTM();
    $('#teams').classList.remove('ttbl');
    const R = CUR, city = cityGroups(R), cg = cityGroups(CITY);
    // TME mode: each team's calls, connected and appointments (of its TMEs: a TME counts in the team of most of their
    // appointments in the dates)
    const tc = GROUPS.map(() => [0, 0, 0]);
    if (CLN) for (const r of MEROWS) { if (!r.calls && !r.n) continue; const g = groupsOf(R, r.me); let b = -1; g.forEach((x, i) => { if (x[0] && (b < 0 || x[0] > g[b][0])) b = i; }); if (b < 0) continue; tc[b][0] += r.calls; tc[b][1] += r.conn; tc[b][2] += r.n; }
    $('#teams').style.gridTemplateColumns = `repeat(${NG}, minmax(0, 1fr))`;
    // 2026-11-02 (the user: polish): the bars' words in the bar when they fit, else beside it (as the TME-mode boxes), so
    // nothing is cut; attended % and conversion as figures, Mumbai's under them when a team is picked
    const gap = innerWidth <= 1100 ? 10 : 14, tw = Math.max(120, (($('#teams').clientWidth || (($('#main') || document.body).clientWidth - 94)) - gap * (NG - 1)) / NG - 30);
    const rt = (v, lab, cv) => `<span class="tr1"><b class="tn">${v}</b><span>${lab}</span>${cv ? `<small>${esc(META.city)} ${cv}</small>` : ''}</span>`;
    $('#teams').innerHTML = GROUPS.map((l, i) => {
      const [g, a, d] = city[i], few = g < MINR;
      return `<button type="button" class="tile tf" data-g="${i}"><span class="tt">${esc(l)}<small>${pct0(g, R.n)} of all</small></span>` +
        `<span class="mini">${apptBars(g, a, d, tw)}</span>` +
        `<span class="trates${few ? ' few' : ''}"${few ? ' title="Few appointments: these rates swing a lot"' : ''}>${rt(pct0(a, g), 'attended', scoped() ? pct0(cg[i][1], cg[i][0]) : '')}${rt(pct0(d, CB() ? g : a), 'conversion', scoped() ? pct0(cg[i][2], CB() ? cg[i][0] : cg[i][1]) : '')}</span>` +
        (CLN && tc[i][0] ? `<span class="tline tcl" title="${esc(`The calls of the TMEs who fixed most of their appointments for ${l}: ${n0(tc[i][0])} calls, ${n0(tc[i][1])} connected, ${n0(tc[i][2])} appointments given`)}"><b>${tc[i][0] >= 1e5 ? (tc[i][0] / 1e5).toFixed(1) + ' lakh' : n0(tc[i][0])}</b> calls · <b>${pct0(tc[i][1], tc[i][0])}</b> connected · <b>${tc[i][1] >= APC_MIN ? (tc[i][2] / tc[i][1] * APC_PER).toFixed(1) : '—'}</b> appts / 1,000 connected</span>` : CLN && city[i][0] ? `<span class="tline tcl">no dialer calls</span>` : '') +
        `</button>`;
    }).join('');
  }
  $('#teams').addEventListener('click', ev => { const t = ev.target.closest('[data-t]'); if (t) return openTeamCard(+t.dataset.t); const b = ev.target.closest('.tile[data-g]'); if (b) openGroup(+b.dataset.g); });   // the team's side window (back 29 Oct; the TME view had taken its place on 28 Oct)

  /* ---------- where the appointments went (2026-10-30, TME mode; the user's sketch: the TME teams on top, the ME
     managers' teams below, a line from each TME team to the teams its appointments went to) ----------
     A flow diagram: a line's width = appointments given. A click on a team, on either row, shows its lines alone and a
     table of them: appointments given, the share of the team's appointments, the other side's share of all appointments
     in the dates (its usual share), how many times its usual share that is, attended % and conversion on them. The top
     row is the TME teams (as the team cards) or the TME managers' teams under the TME head; the bottom row is the
     managers under the ME head (the ME tree, also in TME mode). Records follow the dates and the team picked. */
  let MM = null;   // each record's ME manager: [appointments, deals closed]; -1 = the ME head's own MEs, -2 = outside his line
  const meMgr = node => { if (node === MT.OUT) return -2; let c = node; for (let g = 0; c >= 0 && MT.DEPTH[c] > 1 && g < 8; g++) c = RAW.mgUp[c]; return c === MT.ROOT || c < 0 ? -1 : c; };
  const mmOf = () => MM || (MM = [Int32Array.from(KA, i => meMgr(nodeA0(i))), Int32Array.from(KD, j => meMgr(nodeD0(j)))]);
  // a TME team's manager under the TME head: -1 = the head's own, -2 = outside the head's line
  const tmMgr = node => { if (node === OUTN) return -2; let c = node; for (let g = 0; c >= 0 && DEPTH[c] > 1 && g < 8; g++) c = MGUP[c]; return c === ROOT || c < 0 ? -1 : c; };
  // the Lines view's box for the small teams (2026-10-31): key FSK, set on each draw (FSM = { keys, name, tip } or null)
  const FSK = -99, FLOW_MINW = 48;
  let FSM = null;
  const flTop = t => t === FSK && FSM ? FSM.name : V.flowBy === 'teams' ? TEAMS[t] : t === -1 ? `${HEADNAME} (own)` : t === -2 ? OUT_NAME : NNAME(t);
  const flBot = b => b === -1 ? `${MEHEAD}'s own MEs` : b === -2 ? `Not in ${MEHEAD}'s line` : RAW.mgrs[b][1];
  function flows() {
    const [AMM, DMM] = mmOf(), teams = V.flowBy === 'teams', F = new Map(), T = new Map(), B = new Map();
    const add = (M, k, j, w) => { let v = M.get(k); if (!v) M.set(k, v = [0, 0, 0]); v[j] += w; };
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < V.from || d > V.to || !inScope(i)) continue;
      const t = teams ? ATT[i] : tmMgr(ANODE[i]), b = AMM[i], k = t + '|' + b, at = AO[i] <= 2 ? 1 : 0;
      add(F, k, 0, 1); add(F, k, 1, at); add(T, t, 0, 1); add(T, t, 1, at); add(B, b, 0, 1); add(B, b, 1, at);
    }
    for (let j = 0; j < DLN; j++) {
      const d = DLD[j]; if (d < V.from || d > V.to || !SMASK[DNODE[j]]) continue;
      if (!teams && DLME[j] === NOTME) continue;   // no TME on the deal record: no TME manager
      const t = teams ? DLT[j] : tmMgr(DNODE[j]), b = DMM[j], w = DLW[j];
      add(F, t + '|' + b, 2, w); add(T, t, 2, w); add(B, b, 2, w);
    }
    return { F, T, B };
  }
  let FLW = [];   // the lines drawn (for the tooltips)
  // times the usual share (2026-10-30, the review): the share of X's appointments that went to a team, against that team's
  // share of everyone else's appointments (not of all appointments, which contain X itself and pull big teams such as Hot
  // Data towards 1.0); z = how many standard errors the count is from that usual share (bold past TZ)
  const liftOf = (x, n, own, tot) => { const us = tot - n > 0 ? (own - x) / (tot - n) : 0, sh = n ? x / n : 0; return { sh, us, lift: us > 0 ? sh / us : null, z: us > 0 && us < 1 && n ? (x - n * us) / Math.sqrt(n * us * (1 - us)) : 0 }; };
  const liftTxt = L => L.lift === null ? '—' : Math.abs(L.z) >= TZ ? `<b>${L.lift.toFixed(1)}×</b>` : `<span class="mu" title="Within the usual swing">${L.lift.toFixed(1)}×</span>`;
  const shp = v => v === null || !isFinite(v) ? '—' : v * 100 < 10 ? (v * 100).toFixed(1) + '%' : Math.round(v * 100) + '%';
  // the allocation grid (2026-10-30, the review): one row per TME team (or TME manager's team), one column per ME manager's
  // team; each cell = times the usual share, shaded amber (more) or blue (less) only past the usual swing, deeper for a
  // bigger gap; the small number = appointments given. A row or column name, or a cell, picks that team as the lines do
  function flowGrid(tops, bots, F, T, B, tot, sel, teams, colT) {
    const head = `<tr><th class="fgc">${teams ? 'TME team' : "TME manager's team"} → ME manager's team</th>${bots.map(b => `<th class="fgb${sel && sel.s === 'b' && sel.k === b ? ' on' : ''}" data-fs="b:${b}" tabindex="0" role="button" title="${esc(`${flBot(b)}: ${n0(B.get(b)[0])} appointments given`)}">${esc(b >= 0 ? shortName(flBot(b)) : flBot(b))}<small>${n0(B.get(b)[0])}</small></th>`).join('')}</tr>`;
    const body = tops.map(t => `<tr${sel && sel.s === 't' && sel.k === t ? ' class="on"' : ''}><th class="fgr" data-fs="t:${t}" tabindex="0" role="button"><i style="background:${colT(t)}"></i>${esc(flTop(t))}<small>${n0(T.get(t)[0])}</small></th>` + bots.map(b => {
      const v = F.get(t + '|' + b) || [0, 0, 0], L = liftOf(v[0], T.get(t)[0], B.get(b)[0], tot), sig = L.lift !== null && L.lift > 0 && Math.abs(L.z) >= TZ;
      const a = sig ? Math.min(.5, Math.abs(Math.log(L.lift)) / Math.log(3) * .45 + .08) : 0, bg = !sig ? '' : L.lift > 1 ? `rgba(201,138,18,${a.toFixed(2)})` : `rgba(61,111,176,${a.toFixed(2)})`;
      return `<td class="fgx${sig ? ' sig' : ''}" data-fs="t:${t}"${bg ? ` style="background:${bg}"` : ''} title="${esc(`${flTop(t)} → ${flBot(b)}: ${n0(v[0])} appointments given, ${shp(L.sh)} of ${flTop(t)}'s; usual share ${shp(L.us)} (of everyone else's); ${L.lift === null ? '—' : L.lift.toFixed(2) + '×'}, ${sig ? 'past' : 'within'} the usual swing`)}">${v[0] ? `<b>${L.lift === null ? '—' : L.lift.toFixed(1) + '×'}</b><small>${n0(v[0])}</small>` : '<span class="mu">—</span>'}</td>`;
    }).join('') + `</tr>`).join('');
    return `<div class="dlw fgw"><table class="fgrid">${head}${body}</table></div>` +
      `<p class="hint fgkey"><i class="ka"></i>more than its usual share <i class="kb"></i>less · shaded only past the usual swing (${TZ} standard errors), deeper for a bigger gap · the number = times the usual share (the ME manager's team's share of the other ${teams ? 'TME teams' : "TME managers' teams"}' appointments) · small = appointments given · click a row, a column or a cell for the numbers</p>`;
  }
  // who converts which leads (2026-11-02, the user picked mockup A of three: for each kind of lead -- TME team -- how each
  // ME manager's team did with it, against all the managers on the same leads). Rows = the ME managers' teams, columns =
  // the TME teams with 30+ appointments given; a cell = conversion (or attended %) with its counts. Green / red only past
  // the usual swing (TZ standard errors on that many appointments at the column's rate), fewer than TMIN in the base
  // greyed, 'best' = the column's highest cell past the swing. A cell opens that manager's team's window on that TME team
  function convGrid(tops, bots, F, T, B) {
    const ca = V.flowMea === 'a', base = v => ca || CB() ? v[0] : v[1], hit = v => ca ? v[1] : v[2];
    const baseW = ca || CB() ? 'given' : 'attended', hitW = ca ? 'attended' : 'deals', word = ca ? 'attended %' : 'conversion';
    const cols = tops.filter(t => T.get(t)[0] >= 30), left = tops.filter(t => !cols.includes(t));
    const rate = v => base(v) ? hit(v) / base(v) : null, pcR = p => p === null ? '—' : Math.round(p * 100) + '%';
    const col = new Map(cols.map(t => [t, { n: base(T.get(t)), p: rate(T.get(t)) }]));
    const cell = (b, t) => { const v = F.get(t + '|' + b) || [0, 0, 0], n = base(v), p = rate(v), p0 = col.get(t).p;
      if (!n || p0 === null) return { v, n, p, few: true };
      const se = Math.sqrt(Math.max(p0 * (1 - p0), 1e-9) / n), z = (p - p0) / se;
      return { v, n, p, gap: (p - p0) * 100, z, few: n < TMIN, sig: n >= TMIN && p0 > 0 && p0 < 1 && Math.abs(z) >= TZ }; };
    const best = new Map(cols.map(t => { let w = null, wp = -1; for (const b of bots) { const x = cell(b, t); if (x.sig && x.gap > 0 && x.p > wp) { w = b; wp = x.p; } } return [t, w]; }));
    const tint = x => { if (!x.sig) return ''; const a = Math.min(.55, .14 + Math.abs(x.gap) / 25 * .41); return x.gap > 0 ? `background:rgba(18,135,95,${a.toFixed(2)})` : `background:rgba(200,55,45,${(a * .8).toFixed(2)})`; };
    const sg = v => `${v > 0 ? '+' : v < 0 ? MINUS : '±'}${Math.abs(Math.round(v))}`;
    let all = [0, 0, 0]; for (const v of B.values()) { all[0] += v[0]; all[1] += v[1]; all[2] += v[2]; }
    const nSig = bots.reduce((s, b) => s + cols.filter(t => cell(b, t).sig).length, 0);
    $('#flowSub').innerHTML = `${ca ? 'Attended % (attended of appointments given)' : `Conversion (deals closed ${CVOF()})`} by ME manager's team and TME team (the kind of lead), each against all the managers on the same leads`;
    $('#flowSvg').innerHTML = `<div class="cvw"><table class="cvg tn"><thead><tr><th class="c0"></th>${cols.map(t => `<th data-ct="${t}" tabindex="0" role="button" title="${esc(`Open ${TEAMS[t]}: its teams and its TMEs`)}"><span class="cdot" style="background:${teamCol(t)}"></span>${esc(TEAMS[t])}<small>all ${pcR(col.get(t).p)} · ${n0(col.get(t).n)} ${baseW}</small></th>`).join('')}<th class="ct0">All lead types</th></tr></thead><tbody>` +
      bots.map(b => { const mv = B.get(b);
        return `<tr><th class="rh" data-cb="${b}" tabindex="0" role="button" title="${esc(`Open ${flBot(b)}`)}">${esc(flBot(b))}</th>` + cols.map(t => { const x = cell(b, t);
          return `<td class="${x.few ? 'few' : ''}${best.get(t) === b ? ' best' : ''}" style="${tint(x)}" data-cc="${b}|${t}" tabindex="0" role="button" title="${esc(`${flBot(b)} · ${TEAMS[t]}: ${n0(hit(x.v))} ${hitW} of ${n0(x.n)} ${baseW} = ${pcR(x.p)}; all managers ${pcR(col.get(t).p)}${x.n ? ` (${sg(x.gap)} pts${x.few ? `; fewer than ${TMIN}, too few to compare` : x.sig ? ', past the usual swing' : ', within the usual swing'})` : ''}. Click for this team's window on ${TEAMS[t]}`)}"><b>${pcR(x.p)}</b><small>${x.n ? `${n0(hit(x.v))} of ${n0(x.n)}` : '—'}</small></td>`; }).join('') +
          `<td class="tot"><b>${pcR(rate(mv))}</b><small>${n0(base(mv))} ${baseW}</small></td></tr>`; }).join('') +
      `<tr class="all"><th class="rh">All managers</th>${cols.map(t => `<td><b>${pcR(col.get(t).p)}</b><small>${n0(col.get(t).n)} ${baseW}</small></td>`).join('')}<td><b>${pcR(rate(all))}</b><small>${n0(base(all))} ${baseW}</small></td></tr></tbody></table></div>` +
      `<p class="cvk"><span><i class="g"></i>above all the managers on these leads</span><span><i class="r"></i>below</span><span><i class="n"></i>within the usual swing (${TZ} standard errors)</span><span><i class="f"></i>fewer than ${TMIN} ${baseW}</span><span>small = ${hitW} of ${baseW} · "best" = the column's top cell past the swing · click a cell for that team's window on that lead</span></p>` +
      (left.length ? `<p class="hint">Under 30 appointments given, not shown: ${left.map(t => esc(TEAMS[t])).join(', ')}.</p>` : '') +
      (V.to - V.from + 1 < 60 ? `<p class="hint">${nSig ? `${plural(nSig, 'cell')} past the usual swing in these dates.` : 'No cell is past the usual swing in these dates.'} A month gives few appointments per cell; longer dates give firmer answers: ${PRESETS.filter(q => q.k === 'fytd' || q.k === 'lq').map(q => `<button type="button" class="lnk" data-tpre="${q.k}">${esc(q.label)}</button>`).join(' · ')}</p>` : '');
    $('#flowDet').innerHTML = '';
  }
  function renderFlow() {
    const card = $('#flowCard'); if (!card) return;
    card.hidden = !TM || !secOn('teams'); if (!TM) return;
    document.querySelectorAll('#flowBy button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.flowBy)));
    document.querySelectorAll('#flowV button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.flowView)));
    card.classList.toggle('gridv', V.flowView !== 'lines');
    const conv = V.flowView === 'conv';
    $('#flowH').textContent = conv ? 'Who converts which leads' : 'Where the appointments went';
    $('#flowMw').hidden = !conv;
    document.querySelectorAll('#flowM button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.v === V.flowMea)));
    const { F, T, B } = flows(), tot = [...T.values()].reduce((s, v) => s + v[0], 0), teams = V.flowBy === 'teams';
    const box = $('#flowSvg');
    $('#flowFrom').textContent = teams ? 'From: TME teams' : "From: TME managers' teams";   // what the top row is (2026-10-31, the user)
    if (!tot) { box.innerHTML = '<p class="empty">No appointments given in these dates.</p>'; $('#flowDet').innerHTML = ''; $('#flowSub').textContent = ''; return; }
    const tops = [...T.keys()].filter(t => T.get(t)[0] > 0), bots = [...B.keys()].filter(b => B.get(b)[0] > 0);
    if (teams) tops.splice(0, tops.length, ...teamOrder(tops, t => T.get(t)[0])); else tops.sort((a, b) => (a < 0) - (b < 0) || T.get(b)[0] - T.get(a)[0]);
    bots.sort((a, b) => (a < 0) - (b < 0) || B.get(b)[0] - B.get(a)[0]);
    if (conv) { convGrid(tops, bots, F, T, B); return; }
    let sel = V.flowSel; if (sel && !(sel.s === 't' ? T.has(sel.k) || sel.k === FSK : B.has(sel.k))) sel = V.flowSel = null;
    // the small teams as one box in the Lines view (the user: "club this, this feels a little cluttered"): each under
    // too narrow for a label at this width (under FLOW_MINW px), when 2+; their lines add up into the box's, its numbers
    // are their sum
    FSM = null;
    const W0 = Math.max(640, Math.round(box.clientWidth) || 1200), avail0 = W0 - 4 - (tops.length > 9 ? 6 : 14) * (tops.length - 1);
    const small = V.flowView === 'grid' ? [] : tops.filter(t => T.get(t)[0] / tot * avail0 < FLOW_MINW);
    if (small.length >= 2) {
      const sv = [0, 0, 0], add = (M, k, v) => { const o = M.get(k) || [0, 0, 0]; M.set(k, [o[0] + v[0], o[1] + v[1], o[2] + v[2]]); };
      for (const t of small) { const v = T.get(t); sv[0] += v[0]; sv[1] += v[1]; sv[2] += v[2]; }
      for (const [k, v] of [...F]) { const [t, b] = k.split('|').map(Number); if (small.includes(t)) add(F, FSK + '|' + b, v); }
      T.set(FSK, sv);
      FSM = { keys: small, name: `${small.length} small teams`, tip: small.map(t => `${flTop(t)} ${n0(T.get(t)[0])}`).join(' · ') };
      tops.splice(0, tops.length, ...tops.filter(t => !small.includes(t)), FSK);
      if (sel && sel.s === 't' && small.includes(sel.k)) sel = { s: 't', k: FSK };   // a small team picked (the managers' chips): its box
    }
    if (sel && sel.k === FSK && !FSM) sel = V.flowSel = null;
    const W = Math.max(640, Math.round(box.clientWidth) || 1200), H = 300, PAD = 2, BH = 12, Y0 = 40, Y1 = H - 52;
    const lay = (keys, M, gap) => { const avail = W - PAD * 2 - gap * (keys.length - 1); let x = PAD; const o = new Map(); for (const k of keys) { const w = Math.max(3, M.get(k)[0] / tot * avail); o.set(k, { x, w }); x += w + gap; } return o; };
    const GT = tops.length > 9 ? 6 : 14, GB = 14, LT = lay(tops, T, GT), LB = lay(bots, B, GB);
    const fl = []; for (const [k, v] of F) { const [t, b] = k.split('|').map(Number); if (v[0] && LT.has(t) && LB.has(b)) fl.push({ t, b, v }); }
    for (const t of tops) { const L = LT.get(t), s = L.w / T.get(t)[0]; let x = L.x; fl.filter(f => f.t === t).sort((a, c) => LB.get(a.b).x - LB.get(c.b).x).forEach(f => { f.x0 = x; f.w0 = f.v[0] * s; x += f.w0; }); }
    for (const b of bots) { const L = LB.get(b), s = L.w / B.get(b)[0]; let x = L.x; fl.filter(f => f.b === b).sort((a, c) => LT.get(a.t).x - LT.get(c.t).x).forEach(f => { f.x1 = x; f.w1 = f.v[0] * s; x += f.w1; }); }
    FLW = fl; FLT = { T, B }; flowAll = tot;
    const ym = (Y0 + BH + Y1) / 2, on = f => !sel || (sel.s === 't' ? f.t === sel.k : f.b === sel.k);
    const linked = new Set(); if (sel) fl.filter(on).forEach(f => linked.add(sel.s === 't' ? 'b:' + f.b : 't:' + f.t));
    const colT = t => t === FSK ? '#9AA3B2' : teams ? teamCol(t) : '#C98A12';
    const paths = fl.map((f, i) => { const y0 = Y0 + BH, a = f.x0, a2 = f.x0 + f.w0, c = f.x1, c2 = f.x1 + f.w1;
      return `<path class="fl${sel ? (on(f) ? ' on' : ' off') : !teams && f.w0 < LT.get(f.t).w * .03 ? ' faint' : ''}" data-fi="${i}" style="fill:${colT(f.t)}" d="M${a.toFixed(1)},${y0}C${a.toFixed(1)},${ym} ${c.toFixed(1)},${ym} ${c.toFixed(1)},${Y1}L${c2.toFixed(1)},${Y1}C${c2.toFixed(1)},${ym} ${a2.toFixed(1)},${ym} ${a2.toFixed(1)},${y0}Z"/>`; }).join('');
    const fit = (s, room, cw = 7.6) => { const n = Math.floor(room / cw);   // cw: a character's width (bold 12.5px names; 2026-10-31: 6.9 let neighbours touch)
      return s.length <= n ? s : n < 5 ? '' : s.slice(0, n - 1) + '…'; };
    // with a team picked, the other row's numbers are its part of each (2026-10-31, the user: "even though I've clicked on
    // the Supercat the bottom numbers are static"): '254 of 1,064', else '254'
    const selNm = sel ? (sel.s === 't' ? flTop(sel.k) : flBot(sel.k)) : '';
    const part = (side, k) => !sel || sel.s === side ? null : F.get(side === 'b' ? `${sel.k}|${k}` : `${k}|${sel.k}`) || [0, 0, 0];
    const node = (side, k, L, gap, nm, v, y, fill) => {
      const id = side + ':' + k, s = !!sel && sel.s === side && sel.k === k, dim = !!sel && !s && !linked.has(id), room = L.w + gap - 4, pv = part(side, k);
      // the small teams' box is last: its label may use the room its left neighbour's label leaves
      const roomL = side === 't' && k === FSK && tops.length > 1 ? (() => { const pk = tops[tops.length - 2], P = LT.get(pk), pw = Math.min(flTop(pk).length * 7.6, P.w + GT - 4); return L.x + L.w - (P.x + P.w / 2 + pw / 2) - 6; })() : room;
      const t1 = side === 't' && k === FSK ? [nm, `+${FSM.keys.length} teams`, `+${FSM.keys.length}`].map(x => fit(x, roomL)).find(x => x && !x.includes('…')) || '' : fit(nm, room), t2 = pv ? (fit(`${n0(pv[0])} of ${n0(v[0])}`, roomL, 7).includes('…') ? fit(n0(pv[0]), roomL, 7) : fit(`${n0(pv[0])} of ${n0(v[0])}`, roomL, 7)) : fit(n0(v[0]), roomL, 6.6), cx = Math.min(W - 4, Math.max(4, L.x + L.w / 2)), anc = L.x + L.w / 2 < 40 ? 'start' : L.x + L.w / 2 > W - 40 || roomL > room ? 'end' : 'middle', tx = anc === 'start' ? L.x : anc === 'end' ? L.x + L.w : cx;
      const ly = side === 't' ? [Y0 - 20, Y0 - 6] : [Y1 + BH + 16, Y1 + BH + 31];
      return `<g class="fnd${s ? ' sel' : ''}${dim ? ' dim' : ''}" data-fs="${id}" tabindex="0" role="button" aria-pressed="${s}" aria-label="${esc(`${nm}: ${n0(v[0])} appointments given`)}"><title>${esc((side === 't' && k === FSK && FSM ? `${FSM.tip}\n` : '') + (pv ? `${nm}: ${n0(pv[0])} of its ${n0(v[0])} appointments given ${side === 'b' ? 'came from' : 'went to'} ${selNm} (${shp(v[0] ? pv[0] / v[0] : 0)}) · on them attended ${pct0(pv[1], pv[0])} · conversion ${fPi(cvr(pv[2], pv[1], pv[0]))}` : `${nm}: ${n0(v[0])} appointments given (${shp(v[0] / tot)} of all) · attended ${pct0(v[1], v[0])} · conversion ${fPi(cvr(v[2], v[1], v[0]))}`))}</title>` +
        `<rect x="${L.x.toFixed(1)}" y="${y}" width="${L.w.toFixed(1)}" height="${BH}" rx="2" style="fill:${fill}"/>` +
        (t1 ? `<text class="nm" x="${tx.toFixed(1)}" y="${ly[0]}" text-anchor="${anc}">${esc(t1)}</text>` : '') + (t1 && t2 ? `<text class="ct${pv ? ' pt' : ''}" x="${tx.toFixed(1)}" y="${ly[1]}" text-anchor="${anc}">${esc(t2)}</text>` : '') + `</g>`;
    };
    // the shares on the lines (2026-11-02, the user: "show % in these ribbons, without making it look too cluttered"): at
    // the top end, the line's share of its TME team's appointments; at the bottom end, its share of the ME manager's team's
    // appointments. Only where the line's end is wide enough for the figure and the share is 5% or more; with a team
    // picked, only its lines
    const pctLab = (x, w, v, y, cls) => { const t = `${Math.round(v * 100)}%`; return v >= .05 && w >= t.length * 6.2 + 10 ? `<text class="fp ${cls}" x="${x.toFixed(1)}" y="${y}" text-anchor="middle">${t}</text>` : ''; };
    const pcts = fl.filter(f => sel ? on(f) : !(!teams && f.w0 < LT.get(f.t).w * .03)).map(f =>
      pctLab(f.x0 + f.w0 / 2, f.w0, f.v[0] / T.get(f.t)[0], Y0 + BH + 12, 'pt') + pctLab(f.x1 + f.w1 / 2, f.w1, f.v[0] / B.get(f.b)[0], Y1 - 5, 'pb')).join('');
    if (V.flowView === 'grid') box.innerHTML = flowGrid(tops, bots, F, T, B, tot, sel, teams, colT);
    else box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Appointments given from each ${teams ? 'TME team' : "TME manager's team"} to each ME manager's team">${paths}<g class="fps${sel ? ' on' : ''}" aria-hidden="true">${pcts}</g>` +
      tops.map(t => node('t', t, LT.get(t), GT, flTop(t), T.get(t), Y0, colT(t))).join('') + bots.map(b => node('b', b, LB.get(b), GB, flBot(b), B.get(b), Y1, '#3D4860')).join('') + `</svg>`;
    $('#flowSub').innerHTML = `${n0(tot)} appointments given${scoped() ? ` in ${esc(teamName())}` : ''}, from ${plural(tops.length - (FSM ? 1 - FSM.keys.length : 0), teams ? 'TME team' : "TME manager's team", teams ? 'TME teams' : "TME managers' teams")} to ${plural(bots.length, "ME manager's team", "ME managers' teams")} · a line's width = appointments given`;
    // the table of the team picked
    let det = `<p class="hint">% at the top of a line = its share of that TME team's appointments; at the bottom = its share of that ME manager's team's (shown from 5%, where the line is wide enough). Click a team on either row for its lines alone and their numbers; point at a line for its numbers.</p>`;
    if (sel) {
      const isT = sel.s === 't', k = sel.k, own = (isT ? T : B).get(k), other = isT ? bots : tops, OM = isT ? B : T, nm = isT ? flTop(k) : flBot(k), oName = isT ? flBot : flTop;
      const rows = other.map(o => { const v = F.get(isT ? `${k}|${o}` : `${o}|${k}`) || [0, 0, 0]; return Object.assign({ o, v }, liftOf(v[0], own[0], OM.get(o)[0], tot)); }).filter(r => r.v[0] || r.v[2]).sort((a, b) => b.v[0] - a.v[0]);
      const lift = liftTxt;
      const rate = (a, b) => b >= MINR ? a : `<span class="mu">${a}</span>`;
      det = `<div class="flhd"><h3>${esc(nm)}: ${n0(own[0])} appointments given, ${isT ? 'where they went' : 'where they came from'}</h3><span>attended ${pct0(own[1], own[0])} · conversion ${fPi(cvr(own[2], own[1], own[0]))}</span><button type="button" class="lnk" data-fclear="1">Show all the lines</button></div>` +
        `<div class="dlw"><table class="dl fltbl"><thead><tr><th>${isT ? "ME manager's team" : teams ? 'TME team' : "TME manager's team"}</th><th class="n">Appointments given</th><th class="n">Share of these</th><th class="n">Usual share<br><span class="mu">of everyone else's</span></th><th class="n">Times the<br>usual share</th><th class="n">Attended %</th><th class="n">Conversion %</th></tr></thead><tbody>` +
        rows.map(r => `<tr><td>${esc(oName(r.o))}</td><td class="n">${n0(r.v[0])}</td><td class="n"><b>${shp(r.sh)}</b></td><td class="n">${shp(r.us)}</td><td class="n">${lift(r)}</td><td class="n">${rate(pct0(r.v[1], r.v[0]), r.v[0])}</td><td class="n">${rate(fPi(cvr(r.v[2], r.v[1], r.v[0])), r.v[0])}</td></tr>`).join('') + `</tbody></table></div>` +
        `<p class="hint">Share of these = the share of ${esc(nm)}'s appointments given. Usual share = that ${isT ? "ME manager's team's" : teams ? "TME team's" : "TME manager's team's"} share of ${isT ? `the appointments given outside ${esc(nm)}` : "the appointments given to the other ME managers' teams"} in these dates${scoped() ? ` (${esc(teamName())})` : ''}; times the usual share = the two divided (1.0× = as usual; bold when the gap is past the usual swing, ${TZ} standard errors; grey within it). Attended % and conversion (deals closed ${CVOF()}) on these appointments; grey under ${MINR} appointments.</p>`;
    }
    $('#flowDet').innerHTML = det;
  }
  $('#flowBy') && $('#flowBy').addEventListener('click', ev => { const b = ev.target.closest('[data-v]'); if (!b || b.dataset.v === V.flowBy) return; V.flowBy = b.dataset.v; V.flowSel = null; renderFlow(); });
  $('#flowV') && $('#flowV').addEventListener('click', ev => { const b = ev.target.closest('[data-v]'); if (!b || b.dataset.v === V.flowView) return; V.flowView = b.dataset.v; renderFlow(); });
  const flowPick = id => { const [s, k] = [id.slice(0, 1), +id.slice(2)]; V.flowSel = V.flowSel && V.flowSel.s === s && V.flowSel.k === k ? null : { s, k };
    if (V.flowBy === 'teams' && s === 't') { V.mgrTeam = V.flowSel && k >= 0 ? k : -1; renderMgrs(); }   // the ME managers' card follows a TME team picked
    renderFlow(); };
  const convPick = el => {
    if (el.dataset.cc) { const [b, t] = el.dataset.cc.split('|').map(Number); V.mgrTeam = t; renderMgrs(); return openMgrWin(b); }
    if (el.dataset.cb !== undefined) { V.mgrTeam = -1; renderMgrs(); return openMgrWin(+el.dataset.cb); }
    if (el.dataset.ct !== undefined) return openTeamCard(+el.dataset.ct);
  };
  $('#flowCard') && $('#flowCard').addEventListener('click', ev => {
    const cv = ev.target.closest('[data-cc], [data-cb], [data-ct]'); if (cv) return convPick(cv);
    const tp = ev.target.closest('[data-tpre]'); if (tp) { setPreset(tp.dataset.tpre); return render(true); }
    const fm = ev.target.closest('#flowM [data-v]'); if (fm) { if (fm.dataset.v !== V.flowMea) { V.flowMea = fm.dataset.v; renderFlow(); } return; }
    if (ev.target.closest('[data-fclear]')) { if (V.flowBy === 'teams' && V.flowSel && V.flowSel.s === 't') { V.mgrTeam = -1; renderMgrs(); } V.flowSel = null; return renderFlow(); }
    const g = ev.target.closest('[data-fs]'); if (g) return flowPick(g.dataset.fs);
    const p = ev.target.closest('path[data-fi]'); if (p) { const f = FLW[+p.dataset.fi]; if (f) flowPick('t:' + f.t); }
  });
  $('#flowCard') && $('#flowCard').addEventListener('keydown', ev => { const cv = ev.target.closest('[data-cc], [data-cb], [data-ct]'); if (cv && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); return convPick(cv); } const g = ev.target.closest('[data-fs]'); if (g && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); flowPick(g.dataset.fs); } });
  $('#flowSvg') && $('#flowSvg').addEventListener('mousemove', ev => {
    const p = ev.target.closest('path[data-fi]'); if (!p) return untip();
    const f = FLW[+p.dataset.fi]; if (!f) return;
    const { T, B } = flowTot(); const tt = T.get(f.t), bb = B.get(f.b), tot = flowAll, L = liftOf(f.v[0], tt[0], bb[0], tot);
    tip(`<b>${esc(flTop(f.t))} → ${esc(flBot(f.b))}</b><br>${n0(f.v[0])} appointments given: ${shp(L.sh)} of ${esc(flTop(f.t))}'s; this ME manager's team gets ${shp(L.us)} of everyone else's (${L.lift === null ? '—' : L.lift.toFixed(1) + '×'}${Math.abs(L.z) >= TZ ? ', past the usual swing' : ''})<br>attended ${pct0(f.v[1], f.v[0])} · conversion ${fPi(cvr(f.v[2], f.v[1], f.v[0]))}`, ev);
  });
  $('#flowSvg') && $('#flowSvg').addEventListener('mouseleave', untip);
  // the totals behind the tooltips: kept from the last draw
  let flowAll = 0, FLT = { T: new Map(), B: new Map() };
  const flowTot = () => FLT;

  /* ---------- the ME managers' teams as cards (2026-10-30, TME mode; the user: each manager's performance at a glance,
     for all TME teams or one) ----------
     One card per manager under the ME head (as the team cards: appointments given, attended, deals closed, attended %,
     conversion), for the TME team picked on the card's row or in the flow diagram. With one team picked, each card also
     says how many times its usual share of appointments the manager's team got of that team's. A card opens the
     manager's team's window: which TME teams and TMEs gave its appointments, and a link to the team in ME mode. */
  function mgrAgg(t0) {
    const [AMM, DMM] = mmOf(), inT = t => t0 < 0 || t === t0, M = new Map(), all = new Map(), tot = [0, 0, 0, 0];
    // per manager and TME team, and per TME team: [given, attended, deals], for the lead-mix expectation (2026-10-30)
    const BT = new Map(), TT = Array.from({ length: NT }, () => [0, 0, 0]);
    let totAll = 0;
    const add = (b, j, w) => { let v = M.get(b); if (!v) M.set(b, v = [0, 0, 0, 0]); v[j] += w; };
    const addT = (b, t, j, w) => { const k = b * NT + t; let v = BT.get(k); if (!v) BT.set(k, v = [0, 0, 0]); v[j] += w; TT[t][j] += w; };
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < V.from || d > V.to || !inScope(i)) continue;
      const b = AMM[i], at = AO[i] <= 2 ? 1 : 0; all.set(b, (all.get(b) || 0) + 1); totAll++; addT(b, ATT[i], 0, 1); addT(b, ATT[i], 1, at);
      if (!inT(ATT[i])) continue;
      add(b, 0, 1); add(b, 1, at); tot[0]++; tot[1] += at;
    }
    for (let j = 0; j < DLN; j++) { const d = DLD[j]; if (d < V.from || d > V.to || !SMASK[DNODE[j]]) continue; addT(DMM[j], DLT[j], 2, DLW[j]); if (!inT(DLT[j])) continue; add(DMM[j], 2, DLW[j]); tot[2] += DLW[j]; add(DMM[j], 3, DLRV[j]); tot[3] += DLRV[j]; }
    // what a manager's team would show at all the managers' rates of each TME team, for its own mix of TME teams
    const mix = b => { let eA = 0, eD = 0; for (let t = 0; t < NT; t++) { const v = BT.get(b * NT + t); if (!v || !inT(t)) continue; const T0 = TT[t], dn = CB() ? T0[0] : T0[1]; if (T0[0]) eA += v[0] * T0[1] / T0[0]; if (dn) eD += (CB() ? v[0] : v[1]) * T0[2] / dn; } return { eA, eD }; };
    return { M, all, tot, totAll, mix };
  }
  function renderMgrs() {
    const card = $('#mgrCard'); if (!card) return;
    card.hidden = !TM || !secOn('teams'); if (!TM) return;
    const teamsIn = teamRows(CUR).filter(x => x.n > 0), sizes = new Map(teamsIn.map(x => [x.t, x.n]));
    if (V.mgrTeam >= 0 && !sizes.has(V.mgrTeam)) V.mgrTeam = -1;
    const t0 = V.mgrTeam, { M, all, tot, totAll, mix } = mgrAgg(t0);
    $('#mgrT').innerHTML = `<button type="button" data-mt="-1" aria-pressed="${t0 < 0}">All TME teams</button>` +
      teamOrder([...sizes.keys()], t => sizes.get(t)).map(t => `<button type="button" data-mt="${t}" aria-pressed="${t0 === t}"><i class="cdot" style="background:${teamCol(t)}"></i>${esc(TEAMS[t])}</button>`).join('');
    const keys = [...M.keys()].filter(b => M.get(b)[0] || M.get(b)[2]).sort((a, b) => (a < 0) - (b < 0) || M.get(b)[0] - M.get(a)[0]);
    const tn = t0 < 0 ? 'all TME teams' : TEAMS[t0];
    $('#mgrSub').innerHTML = `${plural(keys.length, "ME manager's team", "ME managers' teams")} · ${t0 < 0 ? 'appointments of all TME teams' : `${esc(tn)} appointments only`}${scoped() ? ` · ${esc(teamName())}` : ''} · all of them together: <b>${pct0(tot[1], tot[0])}</b> attended · <b>${fPi(cvr(tot[2], tot[1], tot[0]))}</b> conversion`;
    if (!keys.length) { $('#mgrTiles').innerHTML = `<p class="empty">No ${esc(tn)} appointments in these dates.</p>`; return; }
    const tw = evenCols($('#mgrTiles'), keys.length, 220) - 22;   // wider: the managers' names are long (8 teams: 4 + 4 on a laptop and full HD)
    $('#mgrTiles').innerHTML = keys.map(b => {
      const [g, a, d] = M.get(b), few = g < MINR, L2 = liftOf(g, tot[0], all.get(b) || 0, totAll), cv = cvr(d, a, g);
      // one TME team: against all the managers on it; all TME teams: against what this team's own mix of TME teams gives
      // at all the managers' rates (2026-10-30, the review: a team with little Super Cat otherwise looks weak)
      const e = mix(b), dn = CB() ? g : a;
      const dA = t0 >= 0 ? Math.round((pc(a, g) || 0) - (pc(tot[1], tot[0]) || 0)) : g ? Math.round((a - e.eA) / g * 100) : null;
      const cvT = cvr(tot[2], tot[1], tot[0]), dC = t0 >= 0 ? (cv === null || cvT === null ? null : Math.round(cv - cvT)) : dn ? Math.round((d - e.eD) / dn * 100) : null;
      const pt = (x, lab) => x === null || few ? '' : `${x > 0 ? '+' : x < 0 ? MINUS : ''}${Math.abs(x)} pts ${lab}`;
      return `<button type="button" class="tile tf mgt" data-mb="${b}"><span class="tt"><span class="tnm" title="${esc(flBot(b))}">${esc(flBot(b))}</span><small>${pct0(g, tot[0])} of ${t0 < 0 ? 'all' : esc(tn)}</small></span>` + `<span class="mini">${apptBars(g, a, d, tw)}</span>` +
        `<span class="tline${few ? ' few' : ''}"${few ? ' title="Few appointments: these rates swing a lot"' : ''}><b>${pct0(a, g)}</b> attended · <b>${fPi(cv)}</b> conversion</span>` +
        (() => {   // the comparison, the share and the revenue in two short lines (2026-10-30: less scrolling)
          const L = [];
          if (!few) L.push(`<span title="${t0 >= 0 ? `Against all the managers' teams together on ${esc(tn)}` : "Against what all the managers' teams together do on the same TME teams, for this team's own mix of TME teams"}">${[pt(dA, 'attd'), pt(dC, 'conv')].filter(Boolean).map(x => `<span class="nw">${x}</span>`).join(' · ')} <span class="nw">${t0 >= 0 ? 'vs all' : 'vs its lead mix'}</span></span>`);
          const sh2 = t0 >= 0 && L2.lift !== null ? `<span title="${esc(`${shp(L2.sh)} of the ${tn} appointments, against ${shp(L2.us)} of the other TME teams' appointments`)}" class="nw">${liftTxt(L2)} its usual share</span>` : '';
          if (sh2) L.push(sh2);   // RV3yr off the boxes for now (2026-10-31, the user)
          return L.length ? `<span class="tmeta">${L.join('<br>')}</span>` : '';
        })() + `</button>`;
    }).join('');
  }
  $('#mgrT') && $('#mgrT').addEventListener('click', ev => {
    const b = ev.target.closest('[data-mt]'); if (!b) return;
    const t = +b.dataset.mt; if (t === V.mgrTeam) return;
    V.mgrTeam = t;
    if (V.flowBy === 'teams') V.flowSel = t >= 0 ? { s: 't', k: t } : null;   // the flow diagram shows the same team
    renderMgrs(); renderFlow();
  });
  $('#mgrTiles') && $('#mgrTiles').addEventListener('click', ev => { const b = ev.target.closest('[data-mb]'); if (b) openMgrWin(+b.dataset.mb); });
  // a manager's team's window (TME mode): its funnel for the TME team picked, which TME teams and which TMEs gave its
  // appointments, and the way to the team in ME mode
  function openMgrWin(b) {
    const [AMM, DMM] = mmOf(), t0 = V.mgrTeam, inT = t => t0 < 0 || t === t0, nm = flBot(b), tn = t0 < 0 ? 'all TME teams' : TEAMS[t0];
    const byT = new Map(), byP = new Map(), o = [0, 0, 0, 0, 0, 0], tot = [0, 0, 0];
    const add = (M, k, j, w) => { let v = M.get(k); if (!v) M.set(k, v = [0, 0, 0]); v[j] += w; };
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < V.from || d > V.to || !inScope(i) || AMM[i] !== b || !inT(ATT[i])) continue;
      const at = AO[i] <= 2 ? 1 : 0; o[AO[i]]++; tot[0]++; tot[1] += at; add(byT, ATT[i], 0, 1); add(byT, ATT[i], 1, at); add(byP, AME[i], 0, 1); add(byP, AME[i], 1, at);
    }
    for (let j = 0; j < DLN; j++) { const d = DLD[j]; if (d < V.from || d > V.to || !SMASK[DNODE[j]] || DMM[j] !== b || !inT(DLT[j])) continue; tot[2] += DLW[j]; add(byT, DLT[j], 2, DLW[j]); if (DLME[j] !== NOTME) add(byP, DLME[j], 2, DLW[j]); }
    const tl = teamOrder([...byT.keys()], t => byT.get(t)[0]), pl = [...byP.entries()].filter(([, v]) => v[0] || v[2]).sort((a, c) => c[1][0] - a[1][0] || c[1][2] - a[1][2]);
    const MA = mgrAgg(t0), code = b >= 0 ? RAW.mgrs[b][0] : '', TT = MA.tot, ca = pc(tot[1], tot[0]), cc = cvr(tot[2], tot[1], tot[0]), ex = MA.mix(b);
    const refA = t0 >= 0 ? `all managers ${fP(pc(TT[1], TT[0]))}` : `${fP(pc(ex.eA, tot[0]))} expected for its mix of TME teams`, refC = t0 >= 0 ? `all managers ${fP(cvr(TT[2], TT[1], TT[0]))}` : `${fP(pc(ex.eD, CB() ? tot[0] : tot[1]))} expected for its mix`;
    const st = (v, l, sub) => `<div class="mstep"><div class="mv tn">${v}</div><div class="ml2">${l}</div><div class="ms">${sub}</div></div>`;
    openDrawer(`<h2 id="drawerH">${esc(nm)}</h2><p class="where">${b >= 0 ? "ME manager's team" : ''}${b >= 0 ? ' · ' : ''}${esc(tn)} · ${esc(periodName())}</p>` +
      `<div class="mflow">${st(n0(tot[0]), 'appointments given', `${pct0(tot[0], TT[0])} of ${esc(tn)}`)}${ARROW}${st(n0(tot[1]), 'attended', `<b>${fP(ca)}</b> · ${refA}`)}${ARROW}${st(n0(tot[2]), 'deals closed', `<b>${fP(cc)}</b> ${CVOF()} · ${refC}`)}</div>` +
      (code ? `<div class="dact"><button type="button" class="btn" data-goMe="${esc(code)}">Open ${esc(shortName(nm))}'s team in ME mode</button></div>` : '') +
      (t0 < 0 && tl.length ? `<h3>From which TME teams</h3><div class="mlist">${MHEAD}${tl.map(t => mrow(esc(TEAMS[t]), byT.get(t))).join('')}</div>` : '') +
      `<h3>Dispositions</h3>${dispLines(o)}` +
      `<h3>Which TMEs fixed them</h3>` + (pl.length ? `<p class="cmpn">${plural(pl.length, 'TME')}. Click one for their page.</p><div class="mlist">${MHEAD.replace('TME team', 'TME')}${pl.slice(0, 40).map(([p, v]) => `<button type="button" class="srow" data-me="${p}">${mrow(esc(MES[p][1]), v)}</button>`).join('')}</div>${pl.length > 40 ? `<p class="hint">Top 40 of ${plural(pl.length, 'TME')}.</p>` : ''}` : '<p class="empty">None in these dates.</p>'));
  }
  // from TME mode to ME mode, on one manager's team (the page reloads)
  function goMe(code) {
    try { localStorage.setItem(MODE_KEY, 'me'); } catch (e) { /* the link carries it */ }
    const h = new URLSearchParams(location.hash.slice(1)); h.delete('mode'); h.set('team', code); h.set('view', 'team');
    history.replaceState(null, '', '#' + h.toString()); document.body.classList.add('switching'); location.reload();
  }

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
  $('.tmcard').addEventListener('click', ev => { if (ev.target.closest('[data-ovreset]')) { V.ovSort = 'n'; V.ovDir = 'desc'; OPG = 0; renderLadder(); } });
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
    const direct = m => { const d = DIR.get(m); if (d && d.length) out.push({ k: m, name: NNAME(m), rows: d, tag: `own & direct ${W.p}`, sub: `${m === ROOT ? W.s + ' head' : 'Manager'}: own and direct ${W.p} · ${plural(d.length, W.s)}` }); };
    const walk = m => {
      for (const k of kidsOf(m)) {
        if (NDEP(k) >= L) { const nT = kidsOf(k).length; out.push({ k, name: NNAME(k), rows: SUB.get(k), sub: `${ROLE(k) === 'manager' ? 'Manager' : `Team leader${UPN(k) === V.scope ? '' : ` · ${NNAME(UPN(k))}`}`}${nT ? ` · ${plural(nT, 'team leader')}` : ''} · ${plural(SUB.get(k).length, W.s)}` }); }
        else { walk(k); direct(k); }
      }
    };
    walk(V.scope); direct(V.scope);
    if (V.scope === ROOT && SUB.has(OUTN)) out.push({ k: OUTN, name: OUT_NAME, rows: SUB.get(OUTN), sub: `${plural(SUB.get(OUTN).length, W.s)} · their ${W.lines} ends elsewhere` });
    return out;
  }
  // ME mode's 'Who converts' (2026-11-02, the user: the same view as TME mode's 'Who converts which leads', instead of
  // Team shares): this card's lines (managers, team leaders or MEs, as Show says; the same order, search and pages) x the
  // TME teams; a cell = the line's conversion (or attended %) on that TME team's appointments, against all Mumbai on the
  // same TME team (the bottom line). Green / red only past the usual swing (TZ standard errors at Mumbai's rate), fewer
  // than TMIN in the base hatched, 'best' = the column's top line past the swing (over every page). A cell opens that ME's
  // window on that TME team; a team's cell shows that team on the whole dashboard with that TME team's window
  function convList(list, show, pg, city, teams, word, q, total) {
    const ca = V.cvMea === 'a', base = v => ca || CB() ? v[0] : v[1], hit = v => ca ? v[1] : v[2];
    const baseW = ca || CB() ? 'given' : 'attended', hitW = ca ? 'attended' : 'deals', what = ca ? 'attended %' : 'conversion';
    const pcR = p => p === null || p === undefined ? '—' : Math.round(p * 100) + '%', sg = v => `${v > 0 ? '+' : v < 0 ? MINUS : '±'}${Math.abs(Math.round(v))}`;
    const col = city.map(v => ({ n: base(v), p: base(v) ? hit(v) / base(v) : null }));
    const cell = (x, i) => { const v = x.g[i], n = base(v), p = n ? hit(v) / n : null, p0 = col[i].p;
      if (x.r.away && !ca) return { v, n: 0, p: null, few: true, away: true };
      if (!n || p0 === null) return { v, n, p, few: true };
      const se = Math.sqrt(Math.max(p0 * (1 - p0), 1e-9) / n), z = (p - p0) / se;
      return { v, n, p, gap: (p - p0) * 100, z, few: n < TMIN, sig: n >= TMIN && p0 > 0 && p0 < 1 && Math.abs(z) >= TZ }; };
    const best = GROUPS.map((_, i) => { let w = null, wp = -1; for (const x of list) { const c = cell(x, i); if (c.sig && c.gap > 0 && c.p > wp) { w = x; wp = c.p; } } return w; });
    const tint = c => { if (!c.sig) return ''; const a = Math.min(.55, .14 + Math.abs(c.gap) / 25 * .41); return c.gap > 0 ? `background:rgba(18,135,95,${a.toFixed(2)})` : `background:rgba(200,55,45,${(a * .8).toFixed(2)})`; };
    const lineB = r => ca || CB() ? r.n : r.att, lineH = r => ca ? r.att : r.deals, lineP = r => r.away && !ca ? null : lineB(r) ? lineH(r) / lineB(r) : null;
    const rowH = x => { const r = x.r, u = r.unit, sub = u ? u.sub : (r.tl ? `Team leader: ${r.tl}` : r.mgr ? `Manager: ${r.mgr}` : 'No team leader recorded');
      const open = u ? `data-cvu="${u.k}"` : `data-cvm="${r.me}"`, who = u ? u.name : r.name;
      return `<tr><th class="rh" ${open} tabindex="0" role="button" title="${esc(u ? `${u.name}: ${sub}. Click to show only this team on the whole dashboard` : `${r.name}: ${sub}. Click for the window`)}"><span class="rn">${u ? esc(u.name) + (u.tag ? `<span class="rtag">${esc(u.tag)}</span>` : '') : esc(r.name) + rtag(r)}</span><small>${esc(sub)}</small></th>` +
        GROUPS.map((l, i) => { const c = cell(x, i);
          return `<td class="${c.few ? 'few' : ''}${best[i] === x ? ' best' : ''}" style="${tint(c)}" ${open} data-cvg="${i}" tabindex="0" role="button" title="${esc(c.away ? `${who}: an ME of another city; the Sales MIS counts their deals closed there` : `${who} · ${l}: ${n0(hit(c.v))} ${hitW} of ${n0(c.n)} ${baseW} = ${pcR(c.p)}; ${META.city} ${pcR(col[i].p)}${c.n ? ` (${sg(c.gap)} pts${c.few ? `; fewer than ${TMIN}, too few to compare` : c.sig ? ', past the usual swing' : ', within the usual swing'})` : ''}. Click for ${u ? 'this team and ' + l : 'the window on ' + l}`)}"><b>${pcR(c.p)}</b><small>${c.n ? `${n0(hit(c.v))} of ${n0(c.n)}` : '—'}</small></td>`; }).join('') +
        `<td class="tot"><b>${pcR(lineP(r))}</b><small>${n0(lineB(r))} ${baseW}</small></td></tr>`; };
    const cityR = { n: CITY.n, att: att(CITY.o), deals: CITY.dl };
    $('#tcSub').innerHTML = (teams ? `One line per ${lvl() === 1 ? "manager's" : "team leader's"} team` : `${plural(total, W.s)} with appointments or deals closed`) + ` · ${what} by TME team, against all ${esc(META.city)} on the same TME team` + (q ? ` · ${n0(list.length)} matching "${esc(q)}"` : '');
    $('#meList').innerHTML = `<div class="cvbar"><span class="slab">Measure</span><div class="seg small" role="group" aria-label="Measure"><button type="button" data-cvmea="c" aria-pressed="${!ca}">Conversion</button><button type="button" data-cvmea="a" aria-pressed="${ca}">Attended %</button></div></div>` +
      (list.length ? `<div class="cvw"><table class="cvg tn"><thead><tr><th class="c0 rh0">${teams ? (lvl() === 1 ? 'Manager' : 'Team leader') : W.s}</th>${GROUPS.map((l, i) => `<th><span class="cdot" style="background:var(--t${i})"></span>${esc(l)}<small>${esc(META.city)} ${pcR(col[i].p)} · ${n0(col[i].n)} ${baseW}</small></th>`).join('')}<th class="ct0">All TME teams</th></tr></thead><tbody>` +
        show.map(rowH).join('') +
        `<tr class="all"><th class="rh">${esc(META.city)}, all ${W.p}</th>${GROUPS.map((_, i) => `<td><b>${pcR(col[i].p)}</b><small>${n0(col[i].n)} ${baseW}</small></td>`).join('')}<td><b>${pcR(lineB(cityR) ? lineH(cityR) / lineB(cityR) : null)}</b><small>${n0(lineB(cityR))} ${baseW}</small></td></tr></tbody></table></div>`
        : `<p class="empty">${q ? `Nothing matches "${esc(q)}".` : `No ${word}s in these dates.`}</p>`) +
      ovPager(list.length, pg.pages, `${word}s`) +
      `<div class="lfoot"><span class="gap"></span><button type="button" class="lnk" id="lCsv">Download this list (CSV)</button></div>` +
      `<p class="cvk"><span><i class="g"></i>above all ${esc(META.city)} on the same TME team</span><span><i class="r"></i>below</span><span><i class="n"></i>within the usual swing (${TZ} standard errors)</span><span><i class="f"></i>fewer than ${TMIN} ${baseW}</span><span>small = ${hitW} of ${baseW} · "best" = the column's top line past the swing · click a cell for ${teams ? 'that team and TME team' : `that ${W.s}'s window on that TME team`}</span></p>` +
      (V.to - V.from + 1 < 60 ? `<p class="hint">A month gives few appointments per cell${teams ? '' : `, fewer still per ${W.s}`}; longer dates give firmer answers: ${PRESETS.filter(k => k.k === 'fytd' || k.k === 'lq').map(k => `<button type="button" class="lnk" data-tpre="${k.k}">${esc(k.label)}</button>`).join(' · ')}</p>` : '');
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
    const pg = ovPage(list), show = pg.rows, cityShare = i => pct0(city[i][0], CITY.n), word = teams ? 'team' : W.s;
    if (meStyle() === 'conv') return convList(list, show, pg, city, teams, word, q, total);
    $('#tcSub').innerHTML = (teams ? `One line per ${lvl() === 1 ? "manager's" : "team leader's"} team, split by TME team`
      : `${plural(total, W.s)} with appointments or deals closed, split by TME team`) + (q ? ` · ${n0(list.length)} matching "${esc(q)}"` : '');
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
        `<span class="mc nm"><b>${ref ? `${esc(META.city)}, all ${W.p}` : u ? esc(u.name) + (u.tag ? `<span class="rtag">${esc(u.tag)}</span>` : '') : esc(r.name) + rtag(r)}</b><small class="sm">${sum(r)}</small>${ref ? '' : why(x)}</span>` +
        ribbon(x) + reading(x, ref) + `</${ref ? 'div' : 'button'}>`;
    };
    $('#meList').innerHTML = `<div class="mer mh" aria-hidden="true"><span class="mc nm">${teams ? (lvl() === 1 ? 'Manager' : 'Team leader') : W.s}</span><span class="mc gh">Team shares: appointments given → attended → deals closed<span class="key">${GROUPS.map((l, i) => `<span><i class="t${i}"></i>${esc(l)}</span>`).join('')}</span></span><span class="mc gh">Reading</span></div>` +
      row(cityX, true) + show.map(x => row(x)).join('') +
      (list.length ? '' : `<p class="empty">${q ? `Nothing matches "${esc(q)}".` : `No ${word}s in these dates.`}</p>`) +
      ovPager(list.length, pg.pages, `${word}s`) +
      `<div class="lfoot"><span class="gap"></span><button type="button" class="lnk" id="lCsv">Download this list (CSV)</button></div>` +
      `<p class="hint">Each bar is 100% of the ${word}'s appointments given, attended or deals closed, split by TME team. A band that widens on the way down is a TME team the ${word} converts better than its other TME teams; one that narrows, one it converts less. Some change is normal: compare with ${esc(META.city)}'s line on top. Point at a band for its numbers. ${teams ? 'Click a team to show only that team on the whole dashboard.' : `Click ${W.aS} for their page.`}${V.sortBy === 'uneven' ? ` "Uneven attended across teams" puts first the lines whose attendance differs most between two TME teams, beyond the usual difference in ${esc(META.city)} (e.g. Super Cat 94% vs Hot Data 30%, where ${esc(META.city)} is 88% vs 78%). A TME team needs ${G_GAP_MIN}+ appointments to count.` : ''}</p>`;
  }
  $('#sortBy').addEventListener('click', ev => { const b = ev.target.closest('button'); if (b) { V.sortBy = b.dataset.v; OPG = 0; renderList(); } });
  $('#meSearch').addEventListener('input', () => { OPG = 0; V.ovShut.clear(); renderLadder(); renderList(); });
  const cvOpen = el => {   // 'Who converts' (ME mode): a cell or a line
    const gi = el.dataset.cvg !== undefined ? +el.dataset.cvg : -1;
    if (el.dataset.cvm !== undefined) return gi >= 0 ? openMe(+el.dataset.cvm, gi) : openMe(+el.dataset.cvm);
    if (el.dataset.cvu !== undefined) { setScope(+el.dataset.cvu, true); if (gi >= 0) openGroup(gi); }
  };
  $('#meList').addEventListener('keydown', ev => { const c = ev.target.closest('[data-cvm], [data-cvu]'); if (c && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); cvOpen(c); } });
  $('#meList').addEventListener('click', ev => {
    const cv = ev.target.closest('[data-cvm], [data-cvu]'); if (cv) return cvOpen(cv);
    const cm = ev.target.closest('[data-cvmea]'); if (cm) { if ((cm.dataset.cvmea === 'a') !== (V.cvMea === 'a')) { V.cvMea = cm.dataset.cvmea; renderList(); } return; }
    const tp = ev.target.closest('[data-tpre]'); if (tp) { setPreset(tp.dataset.tpre); return render(true); }
    if (ev.target.closest('#lCsv')) return listCsv();
    const t = ev.target.closest('.mer[data-scope]'); if (t) return setScope(+t.dataset.scope, true);
    const b = ev.target.closest('.mer[data-me]'); if (b) openMe(+b.dataset.me);
  });
  function listCsv() {
    const f = x => x === null || x === undefined || !isFinite(x) ? '' : (+x).toFixed(1);
    if (LROWS.length && LROWS[0].r.unit) return download(`${W.s}_teams_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['Team', 'What it is', W.p, 'Appointments given', 'Attended', 'Attended %', 'Deals closed', `Conversion % (${CVOF()})`, 'Not Available', 'Pending', 'Not Visited',
        ...GROUPS.flatMap(l => [`${l} appointments given`, `${l} attended`, `${l} deals closed`])],
        ...LROWS.map(x => { const r = x.r; return [r.name, r.unit.sub, r.k, r.n, r.att, f(r.attP), r.away ? '' : r.deals, f(r.conv), r.o[3], r.o[4], r.o[5], ...x.g.flat()]; })]);
    download(`ME_team_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [[`${W.s} code`, W.s, 'Team leader', 'Manager', 'Designation', 'Grade', 'Home city', 'Days present', 'Appointments given', 'Attended', 'Attended %', 'Deals closed', `Conversion % (${CVOF()})`, 'Not Available', 'Pending', 'Not Visited', 'Not Counted/Cancelled',
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
    const s = { n: 0, att: 0, deals: 0, o: [0, 0, 0, 0, 0, 0], nc: 0, pd: 0, pdN: 0, nPd: 0, aPd: 0, away: 0, g: z3(), calls: 0, conn: 0, cPd: 0, rv: 0, tim: [0, 0], gt: null };
    const lf = TM ? { n: 0, att: 0, deals: 0, ea: 0, va: 0, ed: 0, vd: 0 } : null;
    for (const r of rows) {
      s.n += r.n; s.att += r.att; s.deals += r.deals; s.nc += r.nc; r.o.forEach((x, i) => { s.o[i] += x; }); if (r.away) s.away++;
      if (lf && r.lf) for (const k in lf) lf[k] += r.lf[k];
      if (r.pd !== null) { s.pd += r.pd; s.pdN++; s.nPd += r.n; s.aPd += r.att; s.cPd += r.calls || 0; }
      s.calls += r.calls || 0; s.conn += r.conn || 0; s.rv += r.rv || 0; if (r.tim) { s.tim[0] += r.tim[0]; s.tim[1] += r.tim[1]; }
      if (r.gt) { if (!s.gt) s.gt = TEAMS.map(() => [0, 0, 0]); r.gt.forEach((x, t) => { s.gt[t][0] += x[0]; s.gt[t][1] += x[1]; s.gt[t][2] += x[2]; }); }
      if (r.g) for (let i = 0; i < NG; i++) for (let j = 0; j < 3; j++) s.g[i][j] += r.g[i][j];
    }
    return { me: -1, name: '', code: '', tl: '', mgr: '', des: '', city: '', grade: '', k: rows.filter(r => !notTme(r.me)).length,   // TME mode: the lines that are not a TME are not counted as TMEs
      n: s.n, att: s.att, deals: s.deals, o: s.o, nc: s.nc, g: s.g, lf,
      attP: pc(s.att, s.n), conv: rows.length && s.away === rows.length ? null : cvr(s.deals, s.att, s.n), away: rows.length > 0 && s.away === rows.length, pd: s.pdN ? s.pd / s.pdN : null, perDay: s.pd ? s.nPd / s.pd : null, attPd: s.pd ? s.aPd / s.pd : null,
      ...callsOf(s.calls, s.conn, s.n, null), clPd: s.pd && s.cPd ? s.cPd / s.pd : null, rv: s.rv, tim: s.tim, gt: s.gt };
  }
  // the small tag after an ME's name: their own appointments as a team leader / manager, or an ME with no team leader
  const rtag = (r, m) => {
    if (r.lead >= 0 && r.lead === r.node) { const d = DEPTH[r.lead]; return d === 2 ? '<span class="rtag" title="Team leader: their own appointments">TL</span>' : d === 1 ? '<span class="rtag" title="Manager: their own appointments">Manager</span>' : '<span class="rtag">ME head</span>'; }
    return m !== undefined && m !== OUTN && NDEP(m) === 1 && !leafTL(m) ? '<span class="rtag" title="Reports to the manager directly (no team leader)">direct</span>' : '';
  };
  function setScope(m, stay) {
    if (MGRN >= 0 && !inMgr(m)) m = MGRN;
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
    if (V.scope === MGRN) { $('#tcH').innerHTML = `<span class="tct">${esc(NNAME(V.scope))}'s team</span>${ROLE(V.scope) ? `<span class="tctag">${ROLE(V.scope)}</span>` : ''}`; return; }
    const up = UPN(V.scope), upName = up === ROOT ? `All ${META.city}` : NNAME(up), role = ROLE(V.scope);
    $('#tcH').innerHTML = `<button type="button" class="tcback" data-scope="${up}" title="Back to ${esc(up === ROOT ? `all of ${META.city}` : `${upName}'s whole team`)}"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg>${esc(upName)}</button>` +
      `<span class="tct">${esc(V.scope === OUTN ? OUT_NAME : `${NNAME(V.scope)}'s team`)}</span>${role ? `<span class="tctag">${role}</span>` : ''}`;
  }
  $('#tcH').addEventListener('click', ev => { const b = ev.target.closest('[data-scope]'); if (b) setScope(+b.dataset.scope, true); });

  /* ---------- Overview, 'Your team': the teams ladder (managers / team leaders, each a small funnel, opening in place) or
     the ME list - one card, switched by Show (shared with the Table, 2026-10-14) ---------- */
  const fPi = v => v === null || v === undefined || !isFinite(v) ? '—' : Math.round(v) + '%';
  // each line's funnel (2026-10-16, option C picked from rendered previews): appointments given, attended and deals
  // closed as three centred bars joined by soft shading, width against the biggest line (max); thin until the line is
  // pointed at (or focused), then full height with the counts, as the Team shares bands. Also the TME view's lines
  const FUN_Y = [4.5, 19.5, 34.5];   // the middle of each bar: three 9 px rows, 6 px apart
  function funnelSvg(s, max) {
    const FY = FUN_Y;
    const W = [s.n, s.att, s.away ? 0 : Math.min(s.deals, s.n)].map(v => v > 0 ? Math.max(.8, v / max * 100) : 0), L = W.map(w => (100 - w) / 2);
    const lab = [`${n0(s.n)} given`, `${n0(s.att)} attended`, s.away ? AWAY_TXT : `${n0(s.deals)} ${s.deals === 1 ? 'deal' : 'deals'}`];
    const bar = (k, c) => W[k] ? `<span class="fq ${c}${W[k] < 18 ? ' out' : ''}" style="left:${L[k].toFixed(2)}%;width:${W[k].toFixed(2)}%"><b>${lab[k]}</b></span>` : '';
    const join = k => W[k] && W[k + 1] ? `<path class="${k ? 'pd' : 'pa'}" d="M${L[k].toFixed(2)},${FY[k]} L${(L[k] + W[k]).toFixed(2)},${FY[k]} L${(L[k + 1] + W[k + 1]).toFixed(2)},${FY[k + 1]} L${L[k + 1].toFixed(2)},${FY[k + 1]} Z"/>` : '';
    return `<span class="fun" title="${esc(`${n0(s.n)} appointments given · ${n0(s.att)} attended · ${s.away ? AWAY_TXT : `${n0(s.deals)} deals closed`}`)}"><svg viewBox="0 0 100 39" preserveAspectRatio="none" aria-hidden="true">${join(0)}${join(1)}</svg>` +
      `<span class="rl">Given</span><span class="ft">${bar(0, 'g')}</span><span class="rl">Attd</span><span class="ft">${bar(1, 'a')}</span><span class="rl">Deals</span><span class="ft">${bar(2, 'd')}</span></span>`;
  }
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
      if (k === 'pace') {   // TME mode: appointments below their TME team's usual pace, most first (from the Summary)
        const z = s => { const p = paceMap().get(s.me); return p ? p.short : null; };
        const x = z(a.s), y = z(b.s);
        if (x === null) return y === null ? b.s.n - a.s.n : 1;
        if (y === null) return -1;
        return (x - y) * up || b.s.n - a.s.n;
      }
      if (k === 'short') {   // TME mode: deals closed below what the same MEs' rate gives, most first (from the band)
        const z = s => { const r = lfOf(s); return !r || tFew(r).c ? null : r.ed - r.deals; };
        const x = z(a.s), y = z(b.s);
        if (x === null) return y === null ? b.s.n - a.s.n : 1;
        if (y === null) return -1;
        return (x - y) * up || b.s.n - a.s.n;
      }
      if (k === 'zA' || k === 'zC') {   // TME mode: the gap to the same MEs in standard errors (from the band's counts)
        const z = s => { const r = lfOf(s); if (!r) return null; const f = tFew(r); return k === 'zA' ? (f.a ? null : r.zA) : (f.c ? null : r.zC); };
        const x = z(a.s), y = z(b.s);
        if (x === null) return y === null ? b.s.n - a.s.n : 1;
        if (y === null) return -1;
        return (x - y) * up || b.s.n - a.s.n;
      }
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
    const fb = s => funnelSvg(s, max);
    const line = (cls, nm, s, p, bar = true) => {
      const f = few(s);
      const gA = TM ? (p ? lfGap(s, 'a') : '') : f || !p ? '' : pts(s.attP, p.attP), gC = TM ? (p ? lfGap(s, 'c') : '') : f || !p ? '' : pts(s.conv, p.conv);
      return `<div class="lr ${cls}">${nm}${bar ? fb(s) : '<span></span>'}<span class="v">${n0(s.n)}</span>` +
        `<span class="v${f ? ' few' : ''}">${fPi(s.attP)}${gA}</span><span class="v"${s.away ? ` title="${AWAY_TXT}"` : ''}>${s.away ? '—' : n0(s.deals)}</span>` +
        `<span class="v${f ? ' few' : ''}">${fPi(s.conv)}${gC}</span></div>`;
    };
    const refLine = line('ref', `<span class="nm"><span class="chev none"></span><span class="t"><b>${scoped() ? 'Whole team' : `All ${esc(META.city)}`}</b><small>the line to compare with</small></span></span>`, ref, null, false);
    const key = hint => `<span><i class="g"></i>appointments given</span><span><i class="a"></i>attended</span><span><i class="d"></i>deals closed</span>` +
      `<span>Each funnel narrows from appointments given to attended to deals closed; its width is against the biggest line. Point at a line for its numbers. ${TM ? `Under each rate: the gap to the same MEs on the other TMEs' appointments (same TME team, same dates), so a TME is not judged on which MEs took their appointments; green / red = past the usual swing for that many appointments, grey = within it, no gap under ${TMIN} appointments. Point at a gap for its numbers.` : `Green / red = ${GAP}+ points above / below the line above; smaller gaps stay grey (rates on fewer than ${MINR} appointments are grey too).`} Conversion = deals closed ${CVOF()}. Click a column name to order by it, again to turn the order round. ${hint}</span>`;
    if (OVMODE === 'me') {   // every ME in the team shown, one line each, against the team's line
      const all = MEROWS.filter(r => !q || hit(r)).map(r => ({ r, s: r })).sort(srt);
      max = Math.max(1, ...all.map(x => x.s.n));
      $('#tcSub').innerHTML = `${plural(MEROWS.filter(r => !notTme(r.me)).length, W.s)} with appointments or deals closed, each against ${vsName}` + (q ? ` · ${n0(all.length)} matching "${esc(q)}"` : '');
      $('#tcSub').insertAdjacentHTML('beforeend', zSay());
      $('#lad').innerHTML = [`<div class="lr hd">${ovTh('name', W.s, 'nmh')}<span></span>${ovHead()}</div>`, refLine,
        ...ovPage(all).rows.map(x => line('l0 me', `<span class="nm"><span class="chev none"></span><button type="button" class="go" data-me="${x.r.me}" title="Open ${esc(x.r.name)}'s page"><b>${esc(x.r.name)}${rtag(x.r, x.r.node)}</b><small>${scoped() && NDEP(V.scope) === 2 ? '' : x.r.tl ? `TL ${esc(x.r.tl)}` : x.r.mgr ? `Mgr ${esc(x.r.mgr)}` : ''}${x.r.away ? `${scoped() && NDEP(V.scope) === 2 ? '' : ' · '}${AWAY_TXT}` : ''}</small></button></span>`, x.s, ref)),
        all.length ? '' : `<p class="empty">${q ? `No ${W.s} matches "${esc(q)}".` : `No ${W.p} in these dates.`}</p>`,
        ovPager(all.length, ovPage(all).pages, TM ? 'lines' : W.p)].join('');
      $('#ladKey').innerHTML = key(`Click ${W.aS} for their page.`);
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
      if (x.rest) { lines.push(line(`l${x.d} me rest`, `<span class="nm"><span class="chev none"></span><span class="t"><span class="rname" title="${W.p} in this team that do not match the search, added up so the team's line adds up">${plural(x.rest.length, 'other ' + W.s)}, not matching</span></span></span>`, x.T, sumOf(x.m), false)); continue; }
      if (x.r) { lines.push(line(`l${x.d} me`, `<span class="nm"><span class="chev none"></span><button type="button" class="go" data-me="${x.r.me}" title="Open ${esc(x.r.name)}'s page"><b>${esc(x.r.name)}${rtag(x.r, x.m)}</b></button></span>`, x.r, sumOf(x.m))); continue; }
      if (x.k === OUTN) { lines.push(line(`l${x.d} out`, `<span class="nm">${chev(OUTN, x.open, OUT_NAME)}<span class="t"><b>${esc(OUT_NAME)}</b><small>${plural(x.T.k, W.s)} · their ${W.lines} ends elsewhere${x.T.away ? ` · ${AWAY_TXT}` : ''}</small></span></span>`, x.T, ref)); continue; }
      const nT = kidsOf(x.k).length, nm = NNAME(x.k);
      lines.push(line(`l${x.d}`, `<span class="nm">${chev(x.k, x.open, nm)}<button type="button" class="go" data-scope="${x.k}" title="Show only ${esc(nm)}'s team on the whole dashboard"><b>${esc(nm)}</b><small>${nT ? `${plural(nT, 'team leader')} · ` : ROLE(x.k) === 'team leader' ? 'team leader · ' : ''}${plural(x.T.k, W.s)}</small></button></span>`, x.T, x.d === 0 ? ref : sumOf(UPN(x.k))));
    }
    const pg = ovPage(lines);   // paged as the Table: a page of lines (teams and MEs as they open)
    // a page that starts inside a team names the teams it sits in, so the lines keep their place
    const at = OPS ? OPG * OPS : 0;
    if (at > 0 && T.L[at] && T.L[at].d > 0) {
      const up = []; for (let i = at - 1, d = T.L[at].d; i >= 0 && d > 0; i--) if (T.L[i].k !== undefined && T.L[i].d === d - 1) { up.unshift(NNAME(T.L[i].k)); d--; }
      if (up.length) rows.push(`<div class="lr cont"><span class="nm"><span class="chev none"></span><span class="t">${up.map(esc).join(' › ')} · continued</span></span></div>`);
    }
    rows.push(...pg.rows, ovPager(lines.length, pg.pages, 'lines'));
    if (q && !T.L.length) rows.push(`<p class="empty">No ${W.s}, team leader or manager matches "${esc(q)}".</p>`);
    const kT = kidsOf(V.scope).filter(leafTL).length, kM = kidsOf(V.scope).length - kT;
    $('#tcSub').innerHTML = `${scoped() ? '' : `${esc(HEADNAME)}'s `}${scoped() ? plural(kM + kT, 'team leader') : plural(kM, 'manager') + (kT ? ` and ${plural(kT, 'team leader')}` : '')}, each against ${vsName}` + (q ? ` · teams with an ME matching "${esc(q)}"` : '');
    $('#tcSub').insertAdjacentHTML('beforeend', zSay());
    $('#lad').innerHTML = rows.join('');
    $('#ladKey').innerHTML = key(`▸ opens a team; click a name to show only that team on the whole dashboard.${T.filt ? ` The search only picks which teams and ${W.p} are listed; the rest of an open team shows as one "other ${W.p}, not matching" line.` : ''}`);
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
    { k: 'name', h: W.s, sec: W.s, kind: 'text', v: r => r.name },
    // only: shown in the team views (Managers / Team leaders) or in the MEs view
    { k: 'mes', h: W.p, full: `${W.p} with appointments`, tip: `in these dates; ${W.aS} counts in the team where most of their appointments sit`, sec: W.s, kind: 'num', only: 'tree', v: r => r.me >= 0 ? null : r.k },
    { k: 'code', h: `${W.s} code`, sec: W.s, kind: 'text', v: r => r.code },
    { k: 'tl', h: 'TL', full: 'Team leader', sec: W.s, kind: 'list', only: 'flat', v: r => r.tl || '(no team leader)', d: r => r.tl || '—' },
    { k: 'mgr', h: 'Mgr', full: 'Manager', sec: W.s, kind: 'list', only: 'flat', v: r => r.mgr || '(none)', d: r => r.mgr || '—' },
    { k: 'des', h: 'Designation', sec: W.s, kind: 'list', v: r => r.des || '(not in HR)' },
    { k: 'grade', h: 'Grade', sec: W.s, kind: 'list', me: true, v: r => r.grade || '(not recorded)', sv: r => { const m = /(\d+)/.exec(r.grade || ''); return m ? +m[1] : null; } },
    { k: 'city', h: 'Home city', sec: W.s, kind: 'list', v: r => r.city || '(not in HR)' },
    { k: 'joined', h: 'Joined', sec: W.s, kind: 'list', v: r => yr(HRJ[r.me]) || '(not in HR)', sv: r => HRJ[r.me] || '', d: r => HRJ[r.me] ? `${MON3[+HRJ[r.me].slice(5, 7) - 1]} ${HRJ[r.me].slice(0, 4)}` : '—' },
    { k: 'pd', h: 'Days present', tip: 'days present in these dates, from HR attendance', sec: 'Attendance (HR)', kind: 'num', band: 'pd', v: r => r.pd, d: r => r.pd === null ? '—' : (Math.round(r.pd * 10) / 10).toString() },
    { k: 'perDay', h: 'Appts / day', full: 'Appointments given per day present', tip: 'appointments given ÷ days present (HR attendance)', sec: 'Attendance (HR)', kind: 'num', band: 'perDay', v: r => r.perDay, d: r => r.perDay === null ? '—' : r.perDay.toFixed(1) },
    { k: 'attPd', h: 'Attd / day', full: 'Appointments attended per day present', tip: 'appointments attended ÷ days present (HR attendance)', sec: 'Attendance (HR)', kind: 'num', v: r => r.attPd, d: r => r.attPd === null ? '—' : r.attPd.toFixed(1) },
    { k: 'pace', h: 'Pace vs team', full: "Appointments a day present against their TME team's usual", tip: `appointments given a day present as a % of the usual (median) of their TME team's TMEs with ${PACE_PD}+ days present in these dates, all ${META.city}; — under ${PACE_PD} days present`, sec: 'Attendance (HR)', kind: 'num', tm: true, v: r => { const p = r.me === undefined ? null : paceMap().get(r.me); return p && p.ratio !== null ? p.ratio * 100 : null; }, d: r => { const p = r.me === undefined ? null : paceMap().get(r.me); return p && p.ratio !== null ? Math.round(p.ratio * 100) + '%' : '—'; } },
    { k: 'clPd', h: 'Calls / day', full: 'Calls per day present', tip: 'dialer calls ÷ days present (HR attendance)', sec: 'Attendance (HR)', kind: 'num', tm: true, v: r => r.clPd, d: r => r.clPd === null ? '—' : n0(r.clPd) },
    // TME mode (2026-10-30): the TME's dialer calls before the appointments
    { k: 'calls', h: 'Calls', full: 'Dialer calls', tip: "every dialer call of the TME in these dates (the dialer's agent is the TME's employee code, a TME in HR that month)", sec: 'Calls (dialer)', kind: 'num', tm: true, v: r => r.calls },
    { k: 'conn', h: 'Connected', full: 'Connected calls', tip: 'a call whose line connected (trunk duration above 0) and that the TME closed with one of: client disconnected call, not contactable, call back, follow up, not interested, paid client, call to me, IVR call, discard call, do not disturb, not in business, company closed, wrong number, allocate appointment, appointment allocated to JDA, appointment refixed, invalid data, other city data, other TME data, non sales data, lead/call price high, freezed contract, error, testing, inbound call data not found', sec: 'Calls (dialer)', kind: 'num', tm: true, v: r => r.conn },
    { k: 'connP', h: 'Conn %', full: 'Connected % of calls', sec: 'Calls (dialer)', kind: 'pct', bar: 'a', tm: true, v: r => r.connP, few: r => r.calls < 100 },
    { k: 'apc', h: 'Appts / 1,000 conn', full: 'Appointments given per 1,000 connected calls', tip: `— under ${APC_MIN} connected calls`, sec: 'Calls (dialer)', kind: 'num', tm: true, v: r => r.apc, d: r => r.apc === null ? '—' : r.apc.toFixed(1) },
    { k: 'n', h: 'Appts given', full: 'Appointments given', sec: 'All teams', kind: 'num', band: 'n', v: r => r.n, strong: true },
    { k: 'att', h: 'Attd', full: 'Attended', sec: 'All teams', kind: 'num', v: r => r.att },
    { k: 'na', h: 'Not Available', sec: 'All teams', kind: 'num', v: r => r.o[3] },
    { k: 'pend', h: 'Pending', sec: 'All teams', kind: 'num', v: r => r.o[4] },
    { k: 'nv', h: 'Not Visited', sec: 'All teams', kind: 'num', v: r => r.o[5] },
    { k: 'deals', h: 'Deals closed', sec: 'All teams', kind: 'num', v: r => r.deals, d: r => r.away ? '—' : n0(r.deals) },
    { k: 'attP', h: 'Attd %', full: 'Attended %', sec: 'All teams', kind: 'pct', bar: 'a', v: r => r.attP, few: r => r.n < MINR },
    { k: 'conv', h: 'Conv %', full: 'Conversion %', sec: 'All teams', kind: 'pct', bar: 'd', v: r => r.conv, few: r => r.n < MINR },
    { k: 'nc', h: 'Not counted', sec: 'All teams', kind: 'num', v: r => r.nc },
    // TME mode (2026-10-29): the gaps to the same MEs, as under the rates on the Overview (green / red past the usual swing)
    { k: 'lfA', h: 'Attd % vs same MEs', full: 'Attended % against the same MEs', tip: "points: this line's attended % minus what the same MEs did on the other TMEs' appointments (same TME team, same dates)", sec: 'Against the same MEs', kind: 'num', tm: true, v: r => lfPts(r, 'a'), d: r => lfCell(r, 'a') },
    // TME mode (2026-10-30, the review): the TME's team, tenure, next-day share, deals against the same MEs, revenue,
    // the not-counted share
    { k: 'tteam', h: 'TME team', full: 'TME team (HR; else most of their appointments in these dates)', sec: W.s, kind: 'list', tm: true, v: r => { if (!r.gt) return ''; const h = r.me >= 0 ? hrTeamOf(r.me) : -1; if (h >= 0) return TEAMS[h]; let b = -1, bn = 0; r.gt.forEach((x, t) => { if (x[0] > bn) { bn = x[0]; b = t; } }); return b < 0 ? '(deals only)' : TEAMS[b]; } },
    { k: 'tenure', h: 'Tenure', full: 'Time since joining (HR)', sec: W.s, kind: 'list', tm: true, v: r => r.me >= 0 ? tenureBand(r.me) : '', sv: r => r.me >= 0 ? (tenureMonths(r.me) ?? 9999) : null },
    { k: 'nx', h: 'Next-day %', full: 'Allocated the day before or earlier, % of appointments', tip: 'of the appointments with an allocation record, the share allocated the day before the appointment day or earlier; those are attended far less (the attended % gap above allows for it)', sec: 'All teams', kind: 'pct', bar: 'a', tm: true, v: r => r.tim && r.tim[0] ? r.tim[1] / r.tim[0] * 100 : null, few: r => !r.tim || r.tim[0] < MINR },
    { k: 'dGap', h: 'Deals vs same MEs', full: "Deals closed against what the same MEs' rate gives", tip: "deals closed minus what the same MEs' conversion on the other TMEs' appointments gives for these appointments (negative = fewer); green / red past the usual swing", sec: 'Against the same MEs', kind: 'num', tm: true, v: r => { const x = lfOf(r); return !x || tFew(x).c ? null : Math.round((x.deals - x.ed) * 10) / 10; },
      d: r => { const x = lfOf(r); if (!x || tFew(x).c) return '—'; const v = Math.round((x.deals - x.ed) * 10) / 10; return `<span class="lfv ${x.zC >= TZ ? 'up' : x.zC <= -TZ ? 'dn' : ''}" title="${esc(lfTip(x, 'c'))}">${v > 0 ? '+' : v < 0 ? MINUS : ''}${Math.abs(v).toFixed(1)}</span>`; } },
    { k: 'rv', h: 'RV3yr (₹ L)', full: 'Revenue: RV3yr of the deals closed, ₹ lakh', sec: 'All teams', kind: 'num', tm: true, v: r => (r.rv || 0) / 1e5, d: r => r.rv ? (r.rv / 1e5).toFixed(1) : '—' },
    { k: 'ncP', h: 'Not counted %', full: 'Not Counted/Cancelled, % of appointments given and not counted', tip: 'TME Cancelled, Fake Appt, Details Incorrect, Appointment Refixed, Not Available (Online)…', sec: 'All teams', kind: 'pct', bar: 'a', tm: true, v: r => pc(r.nc, r.n + r.nc), few: r => r.n + r.nc < MINR },
    { k: 'lfC', h: 'Conv % vs same MEs', full: 'Conversion % against the same MEs', tip: "points: this line's conversion minus what the same MEs did on the other TMEs' appointments (same TME team, same dates)", sec: 'Against the same MEs', kind: 'num', tm: true, v: r => lfPts(r, 'c'), d: r => lfCell(r, 'c') },
  ];
  // one set of team columns per TME team group (the groups follow the settings; 2026-10-16); in TME mode one per TME team
  // with appointments in the data (2026-10-30: every team on its own, as the cards), the rest in one grey tint
  const TEAM_ANY = (() => { const c = new Float64Array(NT); for (let i = 0; i < N; i++) c[ATT[i]]++; return c; })();
  const TEAMSETS = () => TM ? teamOrder(TEAMS.map((_, t) => t).filter(t => TEAM_ANY[t] > 0), t => TEAM_ANY[t]).map(t => ({ id: 'tm' + t, name: TEAMS[t] === EXP ? 'Expiry' : TEAMS[t], idx: [GROUP_OF[t]], tt: t, t: GDEF[TEAMS[t]] && OWN_COL.includes(TEAMS[t]) ? GDEF[TEAMS[t]].tint : 6 }))
    : GROUPS.map((g, i) => ({ id: GDEF[g].id, name: GSHORT[i], idx: [i], t: GDEF[g].tint }));
  const sumG0 = (r, idx, j) => idx.reduce((t, i) => t + r.g[i][j], 0);
  const makeCols = () => [...BASE_COLS.filter(c => TM ? !c.me : !c.tm).sort((a, b) => !TM ? 0 : tmOrd(a.k) - tmOrd(b.k)), ...TEAMSETS().flatMap(T => { const sumG = (r, idx, j) => T.tt !== undefined ? (r.gt ? r.gt[T.tt][j] : 0) : sumG0(r, idx, j); return [
    { k: `${T.id}n`, h: 'G', full: 'Appointments given', grp: T.name, gi: T.idx[0], team: T.t, kind: 'num', v: r => sumG(r, T.idx, 0), first: true },
    { k: `${T.id}t`, h: 'A', full: 'Attended', grp: T.name, gi: T.idx[0], team: T.t, kind: 'num', v: r => sumG(r, T.idx, 1) },
    { k: `${T.id}a`, h: 'A%', full: 'Attended %', grp: T.name, gi: T.idx[0], team: T.t, kind: 'pct', bar: 'a', v: r => pc(sumG(r, T.idx, 1), sumG(r, T.idx, 0)), few: r => sumG(r, T.idx, 0) < G_MIN },
    { k: `${T.id}d`, h: 'D', full: 'Deals closed', grp: T.name, gi: T.idx[0], team: T.t, kind: 'num', v: r => sumG(r, T.idx, 2) },
    { k: `${T.id}c`, h: 'C%', full: 'Conversion %', grp: T.name, gi: T.idx[0], team: T.t, kind: 'pct', bar: 'd', v: r => cvr(sumG(r, T.idx, 2), sumG(r, T.idx, 1), sumG(r, T.idx, 0)), few: r => sumG(r, T.idx, 0) < G_MIN },
  ]; })];
  // TME mode's column order (2026-10-30, the review): who, how many, the like-for-like, then calls, then the rest
  // 2026-10-31 (the user: a TME's main KPI is appointments given): the appointment columns first, then attended, then the
  // deals view
  const TM_ORDER = ['name', 'tteam', 'mes', 'tl', 'mgr', 'tenure', 'n', 'perDay', 'pace', 'calls', 'connP', 'apc', 'clPd', 'attP', 'lfA', 'nx', 'ncP', 'conv', 'lfC', 'deals', 'dGap', 'rv', 'conn', 'pd', 'att', 'na', 'pend', 'nv', 'nc', 'attPd', 'des', 'city', 'joined', 'code'];
  const tmOrd = k => { const i = TM_ORDER.indexOf(k); return i < 0 ? 99 : i; };
  let XCOLS = makeCols();
  let XC = Object.fromEntries(XCOLS.map(c => [c.k, c]));
  // hidden columns and column widths, remembered in this browser; a few rarely used ones start hidden
  const XHIDE_KEY = TM ? 'jd-me-review-xhide-tme-v1' : 'jd-me-review-xhide-v1', XW_KEY = 'jd-me-review-xwidth-v1';   // TME mode keeps its own column choice
  // the per-team attended counts (A) start hidden too, also for browsers that saved a choice before they existed
  const TEAM_A = ['sct', 'hdt', 'ont', 'ott', 'hot', 'ext'];
  // two column choices, kept apart: 1 to 6 days (the ME Head's daily look) and 7 days or more
  const dayMode = () => V.to - V.from + 1 < 7;
  const XHIDE_DAY_KEY = TM ? 'jd-me-review-xhide-tme-day-v1' : 'jd-me-review-xhide-day-v2';
  const TM_A = TM ? TEAMS.map((_, t) => `tm${t}t`) : [];
  const LONG_HIDE = TM ? ['code', 'des', 'city', 'joined', 'conn', 'pd', 'att', 'na', 'pend', 'nv', 'nc', 'attPd', ...TM_A] : ['code', 'city', 'joined', 'na', 'pend', 'nv', 'nc', ...TEAM_A];
  const DAY_HIDE = TM ? ['code', 'des', 'city', 'joined', 'conn', 'pd', 'perDay', 'pace', 'clPd', 'att', 'na', 'pend', 'nv', 'nc', 'attPd', 'tenure', ...TM_A] : ['code', 'des', 'grade', 'city', 'joined', 'pd', 'perDay', 'attPd', 'nv', 'nc', ...TEAM_A];   // per TME team: G, A%, D, C% (as for longer periods)
  let XHL = new Set(LONG_HIDE), XHD = new Set(DAY_HIDE), XW = {};
  try {
    const h = JSON.parse(localStorage.getItem(XHIDE_KEY) || 'null'); if (Array.isArray(h)) XHL = new Set(h);
    if (!TM && !localStorage.getItem('jd-me-review-xhide-teamA')) { TEAM_A.forEach(k => XHL.add(k)); localStorage.setItem('jd-me-review-xhide-teamA', '1'); localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); }
    // the expiry team's attended count (A, 2026-10-16) starts hidden too, also in column choices saved before it
    if (!TM && !localStorage.getItem('jd-me-review-xhide-ext')) { XHL.add('ext'); localStorage.setItem('jd-me-review-xhide-ext', '1'); localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); }
    const hd = JSON.parse(localStorage.getItem(XHIDE_DAY_KEY) || 'null'); if (Array.isArray(hd)) XHD = new Set(hd);
    // 'Attended per day' (15 Oct 2026) is empty under 7 days: hidden in a day choice saved before it existed
    if (!TM && !localStorage.getItem('jd-me-review-xhide-attPd')) { XHD.add('attPd'); localStorage.setItem('jd-me-review-xhide-attPd', '1'); localStorage.setItem(XHIDE_DAY_KEY, JSON.stringify([...XHD])); }
    XW = JSON.parse(localStorage.getItem(XW_KEY) || '{}') || {};
  } catch (e) { /* defaults */ }
  let XHIDE = XHL;
  const pickHide = () => { XHIDE = dayMode() ? XHD : XHL; };
  const saveX = () => { try { localStorage.setItem(XHIDE_KEY, JSON.stringify([...XHL])); localStorage.setItem(XHIDE_DAY_KEY, JSON.stringify([...XHD])); localStorage.setItem(XW_KEY, JSON.stringify(XW)); } catch (e) { /* not remembered */ } };
  // inside one team, the manager (and in a team leader's team, the team leader) is the same on every line: left out
  const sameAll = k => (k === 'mgr' && sDepth() >= 1) || (k === 'tl' && sDepth() >= 2);
  const visCols = () => { const t = isTree() ? 'tree' : 'flat'; return XCOLS.filter(c => c.k === 'name' || (!XHIDE.has(c.k) && (!c.only || c.only === t) && !sameAll(c.k))); };
  const NARROW = matchMedia('(max-width: 860px)');
  const DEFW = { pace: 78, tteam: 96, tenure: 92, nx: 74, dGap: 84, rv: 78, ncP: 80, lfA: 92, lfC: 92, clPd: 76, calls: 84, conn: 84, connP: 70, apc: 96, name: 150, mes: 56, code: 84, tl: 122, mgr: 122, des: 140, grade: 58, city: 96, joined: 76, pd: 72, perDay: 84, attPd: 80, n: 92, att: 60, attP: 76, deals: 66, conv: 76, na: 76, pend: 66, nv: 68, nc: 74 };   // compact (2026-10-14)
  // the name column is wider in the team views (names are indented under their team); its width is kept apart
  const wKey = k => k === 'name' && isTree() ? 'tname' : k;
  const colW = c => XW[wKey(c.k)] || (c.k === 'name' && isTree() ? 230 : 0) || (c.k === 'name' && NARROW.matches ? 120 : 0) || DEFW[c.k] || (c.team !== undefined ? (c.kind === 'pct' ? 54 : 50) : 80);
  const colName = c => (c.grp ? `${c.grp} ${(c.full || c.h).toLowerCase()}` : c.full || c.h) + (/onversion/.test(c.full || c.h) ? ` (${CVOF()})` : '');
  // filters: { key: { q } | { vals: Set } | { min, max, bands: Set } }; the default shows MEs with MIN+ appointments, like the overview
  let XF = {};
  const XS = { k: 'n', dir: -1 };
  let XROWS = [], XALL = [];   // the MEs listed (search + filters) and every ME in the dates and team

  const xRows = () => MEROWS.map(r => Object.assign({}, r, { g: groupsOf(CUR, r.me), gt: TM ? teamsOf(CUR, r.me) : null }));
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
      const seg = b => cnt[b] ? `<button type="button" class="bseg b${b}${sel.has(b) ? ' on' : ''}" data-k="${k}" data-b="${b}" style="flex:${cnt[b]}" aria-pressed="${sel.has(b)}" title="${esc(`${bandName(k, b)}: ${plural(cnt[b], W.s)}. Click to show only these`)}"><span>${n0(cnt[b])}</span></button>` : '';
      const lab = b => `<button type="button" class="blab${sel.has(b) ? ' on' : ''}" data-k="${k}" data-b="${b}" aria-pressed="${sel.has(b)}"><i class="b${b}"></i>${esc(bandName(k, b))} <b>${n0(cnt[b])}</b></button>`;
      const step = BANDS[k].int ? 1 : 0.1, ec = ECUT(k);
      return `<div class="bcard"><div class="bt">${esc(BANDS[k].label)}</div>` +
        `<div class="bstack">${tot ? [0, 1, 2].map(seg).join('') : `<span class="mu">No ${W.p}</span>`}</div>` +
        `<div class="blabs">${[0, 1, 2].map(lab).join('')}</div>` +
        `<div class="bcuts"><label>Low band below <input type="number" inputmode="decimal" step="${step}" min="0" data-k="${k}" data-i="0" value="${ec[0]}" aria-label="${esc(BANDS[k].label)}: low band below"></label>` +
        `<label>high band from <input type="number" inputmode="decimal" step="${step}" min="0" data-k="${k}" data-i="1" value="${ec[1]}" aria-label="${esc(BANDS[k].label)}: high band from"></label></div>` +
        (miss ? `<p class="bmiss">${plural(miss, W.s)} with no HR record for these dates</p>` : '') + `</div>`;
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
    // an ME's TME team cells (2026-10-28): a click opens the ME's window on that team, at the TMEs behind the appointments
    const ga = c.gi !== undefined && !grp && r.g && r.g[c.gi][0] ? ` data-g="${c.gi}" title="${esc(`${GROUPS[c.gi]}: the TMEs behind ${r.name}'s appointments`)}"` : '';
    if (c.kind === 'text' || c.kind === 'list') {
      const d = c.d ? c.d(r) : v, tg = c.k === 'name' ? rtag(r) : '';
      return c.k === 'name' ? `<td class="nm">${tg ? '<span class="tcell">' : ''}<button type="button" class="lnk me" data-me="${r.me}" title="${esc(d)}">${esc(d)}</button>${tg ? tg + '</span>' : ''}</td>` : `<td class="tx" title="${esc(d)}">${esc(d)}</td>`;
    }
    if (c.k === 'mes' && !grp) return '<td></td>';
    if (c.band && !dayMode() && !grp) { const b = bandOf(c.band, v); if (b >= 0) cls.push('b' + b); }
    if (c.kind === 'pct') {
      if (v === null) return `<td${ga} class="${cls.join(' ')} mu">—</td>`;
      const few = c.few && c.few(r);
      if (dayMode()) return `<td${ga} class="${cls.join(' ')}${few ? ' few' : ''}"><span class="pv">${Math.round(v)}%</span></td>`;   // a day: plain rates, no size bars
      return `<td${ga} class="${cls.join(' ')}${few ? ' few' : ''}"><span class="db ${c.bar}" style="--w:${Math.max(0, Math.min(100, v)).toFixed(0)}%">${Math.round(v)}%</span></td>`;
    }
    const d = c.d ? c.d(r) : (v === null || v === undefined ? '—' : n0(v));
    return `<td${ga} class="${cls.join(' ')}${v === 0 ? ' z' : ''}">${d}</td>`;
  }
  const pplN = rows => rows.filter(r => !notTme(r.me)).length;   // TME mode: 'No TME on the deal record' is not a TME
  const totLabel = rows => isTree() ? `${scoped() ? esc(teamName()) : `All ${esc(META.city)}`}, ${plural(pplN(rows), W.s)}` : `Together, ${plural(pplN(rows), W.s)}`;
  function totalRow(rows, VIS) {
    const T = sumRows(rows);
    return `<tr class="tot"><td class="nm">${totLabel(rows)}</td>` + VIS.slice(1).map(c => {
      if (c.kind === 'text' || c.kind === 'list') return '<td></td>';
      if (c.k === 'pd') return `<td title="Average days present per ${W.s}">${T.pd === null ? '—' : (Math.round(T.pd * 10) / 10) + ' avg'}</td>`;
      if (c.k === 'perDay') return `<td>${T.perDay === null ? '—' : T.perDay.toFixed(1)}</td>`;
      if (c.k === 'attPd') return `<td>${T.attPd === null ? '—' : T.attPd.toFixed(1)}</td>`;
      if (c.tm && c.d) return `<td>${c.d(T)}</td>`;
      if (c.tm && (c.kind === 'list' || c.kind === 'text')) return '<td></td>';
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
    if (c.k === 'name' && x.rest) return `<td class="nm"><span class="tcell" style="padding-left:${x.d * 16 + 22}px"><span class="rname" title="${W.p} in ${esc(x.m === ROOT ? `all ${META.city}` : `${NNAME(x.m)}'s team`)} that do not match the search or filters, added up so the team's line adds up">${plural(x.rest.length, 'other ' + W.s)}, not matching</span></span></td>`;
    if (c.k === 'name') {
      const nm = esc(NNAME(x.k));
      return `<td class="nm"><span class="tcell" style="padding-left:${x.d * 16}px"><button type="button" class="tchev" data-t="${x.k}" aria-expanded="${x.open}" aria-label="${x.open ? 'Close' : 'Open'} ${nm}">${CHEVX}</button>` +
        (x.k === OUTN ? `<span class="gname" title="${nm}: their ${W.lines} ends elsewhere">${nm}</span>` : `<button type="button" class="lnk gname" data-scope="${x.k}" title="${nm}, ${ROLE(x.k)}: click to show only this team on the whole dashboard">${nm}</button>`) + `</span></td>`;
    }
    if (c.kind === 'text' || c.kind === 'list') return '<td></td>';
    if (c.k === 'pd') return `<td title="Average days present per ${W.s}">${T.pd === null ? '—' : (Math.round(T.pd * 10) / 10) + ' avg'}</td>`;
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
    $('#xH').textContent = rows.length === all.length ? plural(pplN(all), W.s) : `${n0(pplN(rows))} of ${plural(pplN(all), W.s)}`;
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
      return `<th class="${x.kind === 'text' || x.kind === 'list' ? 'tx' : ''}${x.first ? ' gs' : ''}${f ? ' fon' : ''}${x.team !== undefined ? ' tc' + x.team : ''}"${sorted ? ` aria-sort="${XS.dir < 0 ? 'descending' : 'ascending'}"` : ''}><button type="button" class="hbtn" data-k="${x.k}" aria-haspopup="dialog" title="${esc((x.k === 'name' && tree ? `Manager, team leader or ${W.s}` : colName(x)) + (x.tip ? `: ${x.tip}` : ''))}">${esc(h)}${sorted ? ARR(XS.dir) : ''}${FUN}</button><span class="rz" data-k="${x.k}" title="Drag to resize"></span></th>`;
    }).join('') + `</tr>`;
    const tw = VIS.reduce((t, c) => t + colW(c), 0);
    // one scroll box: the header rows and the totals row stick at its top, the ME column at its left; pages of XPS rows
    const cg = `<colgroup>${VIS.map(c => `<col data-k="${c.k}" style="width:${colW(c)}px">`).join('')}</colgroup>`;
    const qv = $('#xSearch').value.trim();
    const empty = qv || on.length
      ? `<p class="empty">No ${W.s}${qv ? `, team leader or manager matches "${esc(qv)}"` : ' matches these filters'}${qv && on.length ? ' with these filters' : ''}.</p><p class="empty-act">${qv ? '<button type="button" class="btn" id="xClrQ">Clear search</button>' : ''}${on.length ? '<button type="button" class="btn" id="xClrF">Clear filters</button>' : ''}</p>`
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
      const nOf = d => [...T.SUB.keys()].filter(k => k !== OUTN && (d === 1 ? NDEP(k) === 1 && !leafTL(k) : NDEP(k) === 2 || leafTL(k))).length;
      $('#xPager').innerHTML = `<span class="pgi">${[base < 1 ? plural(nOf(1), 'manager') : '', plural(nOf(2), 'team leader'), T.filt ? `${n0(pplN(rows))} of ${plural(pplN(all), W.s)}` : plural(pplN(rows), W.s)].filter(Boolean).join(' · ')}${T.filt ? ` match the ${qv && on.length ? 'search and filters' : qv ? 'search' : 'filters'}` : ''}</span>`;
    } else {
      const from = rows.length ? XPG * (XPS || rows.length) + 1 : 0, to = XPS ? Math.min(rows.length, (XPG + 1) * XPS) : rows.length;
      $('#xPager').innerHTML = rows.length ? `<span class="pgi">${n0(from)}–${n0(to)} of ${plural(rows.length, W.s)}</span>` +
        (pages > 1 ? `<span class="pgb"><button type="button" class="btn" data-pg="-1"${XPG ? '' : ' disabled'} aria-label="Previous page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg></button><span>Page ${XPG + 1} of ${pages}</span><button type="button" class="btn" data-pg="1"${XPG < pages - 1 ? '' : ' disabled'} aria-label="Next page"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg></button></span>` : '') +
        `<label class="pgs">Rows per page <select id="xPs">${[25, 50, 100, 0].map(n => `<option value="${n}"${n === XPS ? ' selected' : ''}>${n ? n : 'All'}</option>`).join('')}</select></label>` : '';
    }
    $('#xKey').innerHTML = (tree ? `Each team's line is the whole team: all its ${W.p} in these dates (${W.aS} counts in the team where most of their appointments sit).${T && T.filt ? ` The search / filters only choose which ${W.p} are listed; the rest of a team shows as one "other ${W.p}, not matching" line, so every team still adds up.` : ''} ▸ opens or closes a team; <b>Show</b> opens every team down to that level. Click a team's name to show only that team on the whole dashboard.<br>` : '') +
      `Team columns: <b>G</b> appointments given · <b>A%</b> attended % · <b>D</b> deals closed · <b>C%</b> conversion % (deals closed ${CVOF()}). Click ${W.aS}'s team cells for the ${W.cp} behind those appointments.${TM ? ` <b>vs same MEs</b>: points above / below what the same MEs did on the other TMEs' appointments; green / red past the usual swing.` : ''}<br>` +
      `A grey rate has too few appointments behind it to judge.${dayMode() ? '' : ' Shaded cells show the band (Columns > Band cutoffs).'} Click a column name to sort or filter it; click ${W.aS} for their page.`;
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
    const tr = ev.target.closest('tbody tr[data-me]'), tg = ev.target.closest('td[data-g]');   // the whole row opens the ME's page; a team's cells open it on that team
    if (tr) openMe(+tr.dataset.me, tg ? +tg.dataset.g : -1);
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
      const lev = k => k === OUTN ? 'Not in the line' : ROLE(k) === 'manager' ? 'Manager' : 'Team leader';
      const gval = (T, c) => c.kind === 'text' || c.kind === 'list' ? '' : c.k === 'pd' ? (T.pd === null ? '' : Math.round(T.pd * 10) / 10) : val(T, c);
      return download(`${W.s}_teams_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
        [['Level', 'Manager', 'Team leader', 'Name', ...dc.map(colName)],
          ['Total', '', '', scoped() ? teamName() : `All ${META.city}`, ...dc.map(c => gval(sumRows(XALL), c))],
          ...L.map(x => x.r ? [W.s, x.r.mgr, x.r.tl, x.r.name, ...dc.map(c => c.k === 'mes' ? '' : val(x.r, c))]
            : x.rest ? [`Other ${W.p} (not matching)`, x.m === ROOT || x.m === OUTN ? '' : up(x.m, 1), x.m === ROOT || x.m === OUTN ? '' : up(x.m, 2), plural(x.rest.length, 'other ' + W.s), ...dc.map(c => gval(x.T, c))]
            : [lev(x.k), x.k === OUTN ? '' : up(x.k, 1), x.k === OUTN ? '' : up(x.k, 2), NNAME(x.k), ...dc.map(c => gval(x.T, c))])]);
    }
    download(`${W.s}_table_${META.city}${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
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
  function openDrawer(html) { if (!DR.classList.contains('open')) lastFocus = document.activeElement; DR.classList.toggle('tmed', TM); $('#drawerBody').innerHTML = html; DR.classList.add('open'); DR.setAttribute('aria-hidden', 'false'); $('#dim').hidden = false; DR.scrollTop = 0; DR.focus({ preventScroll: true }); }
  function closeDrawer() { DR.classList.remove('open'); DR.setAttribute('aria-hidden', 'true'); $('#dim').hidden = true; if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); }
  $('#drawerClose').addEventListener('click', closeDrawer); $('#dim').addEventListener('click', closeDrawer);
  const strip = (o, n) => `<div class="ostrip">${o.map((c, k) => c ? `<span style="flex:${c} 0 0;background:${OC[k]}" title="${OUT[k]}: ${n0(c)}">${c / n >= .08 ? Math.round(c / n * 100) + '%' : ''}</span>` : '').join('')}</div>`;
  const outChip = o => `<span class="ochip"><i style="background:${OC[o]}"></i>${OUT[o]}</span>`;
  function apptRows(filter) { const out = []; for (let i = N - 1; i >= 0; i--) { const d = AD[i]; if (d < V.from || d > V.to || !inScope(i) || !filter(i)) continue; out.push(i); } return out; }
  const FLAG_TXT = [[F.naEarly, 'Not Available updated early'], [F.dealBeforeBooked, 'Dealclosed before allocation'], [F.noBooking, 'No allocation record'], [F.pending, 'Pending 2+ days'], [F.sameDay, 'Same parentid twice that day']];
  const COLDEF = {
    date: ['Date', i => `<span class="tn">${esc(fDate(dOf(AD[i])))}</span>`, i => iso(dOf(AD[i]))],
    biz: ['Company', i => `${esc(CO[i] || '—')}<small class="pid">${esc(PID[i])}</small>`, i => CO[i]],
    me: [W.s, i => `<button type="button" class="lnk" data-me="${AME[i]}">${esc(MES[AME[i]][1])}</button>`, i => MES[AME[i]][1]],
    tme: [`${W.c} (team)`, i => `${TM ? `<button type="button" class="lnk" data-tme="${ATM[i]}">${esc(TMES[ATM[i]][1])}</button>` : esc(TMES[ATM[i]][1])} <span class="mu">(${esc(TEAMS[ATT[i]])})</span>`, i => `${TMES[ATM[i]][1]} (${TEAMS[ATT[i]]})`],
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
    if (ev.target.closest('#dealsCsv') && DLIST) return download(`${W.s}_deals_closed${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`,
      [['Date', 'parentid', 'Company', `${W.s} code`, W.s, 'TME team', 'Deal (dc_genio)'], ...DLIST.map(j => [iso(dOf(DLD[j])), DLPID[j] || '', CO_OF.get(DLPID[j]) || '', MES[DLME[j]][0], MES[DLME[j]][1], TEAMS[DLT[j]], DLW[j]])]);
    if (ev.target.closest('#listCsv') && LIST) return download(`${W.s}_records${fileTag()}_${iso(dOf(V.from))}_${iso(dOf(V.to))}.csv`, [['parentid', ...LIST.cols.map(c => COLDEF[c][0])], ...LIST.idx.map(i => [PID[i], ...LIST.cols.map(c => COLDEF[c][2](i))])]);
    const it = ev.target.closest('[data-item]'); if (it) { const x = ITEMS.find(y => y.id === it.dataset.item); if (x) return openRecords(x); }
    const chk = ev.target.closest('[data-chk]'); if (chk) { const x = ITEMS.find(y => y.id === chk.dataset.chk); if (x) { if (MARKS[x.id]) delete MARKS[x.id]; else MARKS[x.id] = new Date().toISOString().slice(0, 10); saveMarks(); renderBand(); renderQueue(); renderList(); chk.setAttribute('aria-pressed', String(!!MARKS[x.id])); chk.innerHTML = MARKS[x.id] ? ICON.done + 'Checked' : 'Mark checked'; } return; }
    const tg = ev.target.closest('[data-tg]'); if (tg) return meTeam(+tg.dataset.tg);
    // a TME (2026-10-28): their own window; the TME view of a team
    const tb = ev.target.closest('[data-tme]'); if (tb) return openTme(+tb.dataset.tme, tb.dataset.g !== undefined ? +tb.dataset.g : -1);
    const tw = ev.target.closest('[data-tw]'); if (tw) return openTeamWin(+tw.dataset.tw);
    const gm = ev.target.closest('[data-gome]'); if (gm) return goMe(gm.dataset.gome);
    const tgw = ev.target.closest('[data-tgw]'); if (tgw) return openGroup(+tgw.dataset.tgw);
    const gt = ev.target.closest('[data-gt]'); if (gt && GRP >= 0 && $('#grpDet')) { $('#grpDet').innerHTML = grpDet(GRP, +gt.dataset.gt); return; }   // a team in the team's window
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
  // the TMEs behind one ME's appointments of a TME team (2026-10-28): the ME against the same TMEs' appointments to other
  // MEs, then each TME with their appointments to this ME and to the other MEs; a TME opens their own window
  function meTmes(me, gs) {
    const A = tAgg(), r = tRows(A, gs, 'me', me)[0], gname = GROUPS[gs];
    if (!r || !r.n) return '';
    const tl = new Map();
    for (const [k, v] of A.K) {
      if (!(v[3] || v[5])) continue;
      const s = kSplit(k); if (s.me !== me || GROUP_OF[s.t] !== gs) continue;
      let x = tl.get(s.tm); if (!x) tl.set(s.tm, x = { tm: s.tm, n: 0, att: 0, deals: 0, o: [0, 0, 0] });
      x.n += v[3]; x.att += v[4]; x.deals += v[5];
      if (s.tm !== NOTM) { const S = A.TT.get(s.tm * NT + s.t); x.o[0] += S[0] - v[0]; x.o[1] += S[1] - v[1]; x.o[2] += S[2] - v[2]; }
    }
    const L = [...tl.values()].filter(x => x.tm !== NOTM && x.n).sort((a, b) => b.n - a.n || b.deals - a.deals), lim = 12, one = L.filter(x => x.n <= 2).length;
    const noT = tl.get(NOTM), f = tFew(r), x = cityGroups(CUR)[gs];
    // TME mode: a TME whose appointments are all in this team already has the comparison at the top of the window
    const whole = TM && (() => { const rr = MEROWS.find(y => y.me === me); return !!rr && rr.n === r.n; })();
    // TME mode: the MEs who took the TME's appointments, the TME against the same MEs' other appointments
    const same = TM ? `The same MEs = these MEs on the other TMEs' ${gMulti(gs) ? 'appointments (same team)' : esc(gname) + ' appointments'} in these dates: it takes out which MEs took this TME's appointments.`
      : `The same TMEs = these TMEs' ${gMulti(gs) ? 'appointments (same team)' : esc(gname) + ' appointments'} to the other MEs in these dates: it takes out which TMEs' appointments this ME got.`;
    return `<h4 class="tmeh">${esc(gname)}: the ${W.cp} behind ${esc(MES[me][1])}'s appointments</h4>` +
      `<p class="cmpn">${plural(L.length, W.c)} ${W.doC} this ${W.s}'s ${plural(r.n, 'appointment')} from ${esc(gname)}${one ? `; ${n0(one)} of them ${W.doC} only 1 or 2, too few to compare one by one, so the lines below add them up` : ''}. ${same}</p>` +
      (whole ? '' : `<div class="tcmp"><div><p class="tcl">Attended %</p>${cmp3([[`This ${W.s}`, r.attP, 'me'], [`Same ${W.cp}`, r.bA], [`All ${gname}`, pc(x[1], x[0])]], fPi)}${tSay(r, 'a', `the same ${W.cp}`, f.a)}</div>` +
      `<div><p class="tcl">Conversion %</p>${cmp3([[`This ${W.s}`, r.conv, 'me'], [`Same ${W.cp}`, r.bC], [`All ${gname}`, cvr(x[2], x[1], x[0])]], fPi)}${tSay(r, 'c', `the same ${W.cp}`, f.c)}</div></div>`) +
      `<div class="dlw"><table class="dl"><thead><tr><th>${W.c}</th><th class="n">Given</th><th class="n">Attended</th><th class="n">Deals closed</th><th class="n">The ${W.c} with other ${W.p}<br><span class="mu">conversion · of</span></th></tr></thead><tbody>` +
      L.slice(0, lim).map(t => { const od = CB() ? t.o[0] : t.o[1]; return `<tr><td><button type="button" class="lnk" data-tme="${t.tm}" data-g="${gs}">${esc(TMES[t.tm][1])}</button></td><td class="n">${n0(t.n)}</td><td class="n">${n0(t.att)}</td><td class="n">${n0(t.deals)}</td><td class="n">${od >= TMIN ? fPi(pc(t.o[2], od)) : '<span class="mu">—</span>'} <span class="mu">${n0(od)}</span></td></tr>`; }).join('') +
      (L.length > lim ? (() => { const R2 = L.slice(lim), s2 = R2.reduce((t, m) => [t[0] + m.n, t[1] + m.att, t[2] + m.deals], [0, 0, 0]), mx2 = Math.max(...R2.map(m => m.n)); return `<tr class="rest"><td>${plural(R2.length, 'other ' + W.c)}, ${mx2 > 1 ? `1–${n0(mx2)}` : '1'} each</td><td class="n">${n0(s2[0])}</td><td class="n">${n0(s2[1])}</td><td class="n">${n0(s2[2])}</td><td></td></tr>`; })() : '') +
      `</tbody></table></div>` +
      (L.length > 1 && L[0].n >= 5 ? (() => { const top = L[0]; let og = 0, ag = 0; for (let t = 0; t < NT; t++) { if (GROUP_OF[t] !== gs) continue; const S = A.TT.get(top.tm * NT + t); if (S) og += S[0]; ag += A.T[t][0]; }
        return `<p class="dline">The most ${TM ? 'to' : 'from'} one ${W.c}: <b>${n0(top.n)} of ${n0(r.n)}</b> (${pct0(top.n, r.n)}) ${TM ? 'went to' : 'came from'} ${esc(TMES[top.tm][1])}, who ${TM ? 'takes' : 'fixes'} ${shp(ag ? og / ag : 0)} of ${esc(gname)}'s appointments in these dates.</p>`; })() : '') +
      `<p class="hint">${noT && noT.deals ? `Also ${plural(noT.deals, 'deal')} closed here with no TME on the deal record. ` : ''}Last column: — under ${TMIN}. Click ${W.aC} for their window.</p>`;
  }
  // TME mode's window (2026-10-30, the review): the funnel against the TME's own TME team (not all of Mumbai, which mixes
  // lead types), the like-for-like verdict for all their appointments, and the same month by month
  function tmeFlow(me, r) {
    const t = mainTeamOf(me), tr = t >= 0 ? teamRows(CUR).find(y => y.t === t) : null, tn = t >= 0 ? TEAMS[t] : '';
    const st = (v, l, s) => `<div class="mstep"><div class="mv tn">${v}</div><div class="ml2">${l}</div><div class="ms">${s}</div></div>`;
    return `<div class="mflow">${st(n0(r.n), 'appointments given', [r.pd !== null ? `${r.pd} days present` : '', tr ? `${pct0(r.n, tr.n)} of ${esc(tn)}` : ''].filter(Boolean).join(' · '))}${ARROW}` +
      `${st(n0(r.att), 'attended', `<b>${pct0(r.att, r.n)}</b>${tr ? ` · all ${esc(tn)} ${pct0(tr.a, tr.n)}` : ''}`)}${ARROW}` +
      `${st(n0(r.deals), 'deals closed', `<b>${fPi(r.conv)}</b> ${CVOF()}${tr ? ` · all ${esc(tn)} ${fPi(cvr(tr.d, tr.a, tr.n))}` : ''}${r.rv ? `<br>${fRv(r.rv)} RV3yr` : ''}`)}</div>`;
  }
  // the window's 'Appointments given' (2026-10-31): a TME's main KPI first -- a day present against their team's usual
  // pace, appointments per 1,000 connected against the team, and the calls
  function tmeAppts(me, r) {
    const p = paceMap().get(me), t = p ? p.t : mainTeamOf(me), tn = t >= 0 ? TEAMS[t] : '';
    const cityApc = CITY.cl[1] ? CITY.n / CITY.cl[1] * APC_PER : null;
    const pace = r.pd === null ? `<p class="cmpn tsay">Needs a week or more of dates (HR attendance is monthly).</p>` : r.pd < PACE_PD ? `<p class="cmpn tsay">${pd1(r.pd)} days present: under ${PACE_PD}, not compared.</p>` : !p ? `<p class="cmpn tsay">Fewer than ${PACE_N} ${esc(tn)} TMEs with ${PACE_PD}+ days present to set a usual.</p>`
      : cmp3([['This TME', r.perDay, 'me'], [`${esc(tn)} usual`, p.med]], f1) + `<p class="cmpn tsay">${n0(r.n)} given in ${pd1(r.pd)} days present: ${Math.round(p.ratio * 100)}% of the usual pace, ${p.short >= 0 ? `${n0(Math.round(p.short))} below` : `${n0(Math.round(-p.short))} above`} it (the median of ${n0(p.k)} ${esc(tn)} TMEs with ${PACE_PD}+ days present).</p>`;
    const apc = !CLN ? '' : r.calls < DIAL_MIN ? `<p class="cmpn tsay">${r.calls ? `${n0(r.calls)} dialer calls: under ${DIAL_MIN}, off the dialer for these dates.` : 'No dialer calls in these dates: off the dialer.'}</p>`
      : r.apc === null ? `<p class="cmpn tsay">Under ${APC_MIN} connected calls: too few to compare.</p>`
      : cmp3([['This TME', r.apc, 'me'], [`All ${esc(tn)}`, p ? p.tapc : null], [esc(META.city), cityApc]], f1);
    return `<h3>Appointments given <span class="h3s">· a TME's main measure</span></h3>` +
      `<div class="tcmp"><div><p class="tcl">A day present</p>${pace}</div><div><p class="tcl">Per 1,000 connected calls</p>${apc}</div></div>` +
      (CLN && r.calls ? `<p class="dline">Calls: <b>${n0(r.calls)}</b>${r.clPd ? ` (${n0(r.clPd)} a day present)` : ''} · connected <b>${n0(r.conn)}</b> (${fP(r.connP)}; ${esc(META.city)} ${fP(pc(CITY.cl[1], CITY.cl[0]))}) · ${r.apc === null ? `too few connected dialer calls (under ${APC_MIN}) for appointments per 1,000 connected` : `<b>${r.apc.toFixed(1)}</b> appointments given per 1,000 connected`} (${esc(META.city)} ${cityApc === null ? '—' : cityApc.toFixed(1)})</p>` : '');
  }
  function tmeTop(me, r) {
    const x = lfOf(r); if (!x || !x.n) return '';
    const f = tFew(x), t = mainTeamOf(me), tr = t >= 0 ? teamRows(CUR).find(y => y.t === t) : null, tn = t >= 0 ? `All ${TEAMS[t]}` : 'All';
    const mo = monthLF().filter(o => o.M.a <= V.to), rowsM = mo.map(o => { const y = o.R.get(me); if (!y || !y.n) return null; const z = tFin(Object.assign({}, y)), ff = tFew(z);
      return `<tr${o.M.b >= V.from && o.M.a <= V.to ? ' class="on"' : ''}><td>${esc(o.M.short)}</td><td class="n">${n0(z.n)}</td><td class="n">${ff.a ? `<span class="mu">${fPi(z.attP)}</span>` : fPi(z.attP)} ${tGap(z.attP, z.bA, z.zA, ff.a, lfTip(z, 'a'))}</td><td class="n">${n0(z.deals)}</td><td class="n">${ff.c ? `<span class="mu">${fPi(z.conv)}</span>` : fPi(z.conv)} ${tGap(z.conv, z.bC, z.zC, ff.c, lfTip(z, 'c'))}</td></tr>`; }).filter(Boolean);
    return `<h3>Against the same MEs <span class="h3s">· through deals, the added view</span></h3><p class="cmpn">All this TME's appointments in these dates. The same MEs = the MEs who took them, on the other TMEs' appointments of the same TME team in the same dates (for attended %, also allocated as long before the day). It takes out which MEs got them.</p>` +
      `<div class="tcmp"><div><p class="tcl">Attended %</p>${cmp3([['This TME', x.attP, 'me'], ['Same MEs', x.bA], [tn, tr ? pc(tr.a, tr.n) : null]], fPi)}${tSay(x, 'a', 'the same MEs', f.a)}</div>` +
      `<div><p class="tcl">Conversion %</p>${cmp3([['This TME', x.conv, 'me'], ['Same MEs', x.bC], [tn, tr ? cvr(tr.d, tr.a, tr.n) : null]], fPi)}${tSay(x, 'c', 'the same MEs', f.c)}</div></div>` +
      (!f.c ? `<p class="dline">Deals closed: <b>${n0(x.deals)}</b>, where the same MEs' rate gives about <b>${n0(x.ed)}</b>: ${x.deals >= x.ed ? `${n0(x.deals - x.ed)} more` : `${n0(x.ed - x.deals)} fewer`}${Math.abs(x.zC) >= TZ ? ', past the usual swing' : ', within the usual swing'}.</p>` : '') +
      (rowsM.length > 1 ? `<h3>Month by month since April</h3><p class="cmpn">Under each rate: the gap to the same MEs that month (green / red past the usual swing; none under ${TMIN}). The dates shown are marked.</p><div class="dlw"><table class="dl tmon"><thead><tr><th>Month</th><th class="n">Given</th><th class="n">Attended %</th><th class="n">Deals closed</th><th class="n">Conversion %</th></tr></thead><tbody>${rowsM.join('')}</tbody></table></div>` : '');
  }
  // a TME's not-counted share against their TME team's
  function ncVsTeam(me, r) {
    const t = mainTeamOf(me); if (t < 0 || !NCTT) return '';
    let nn = 0; for (let k = 0; k < NCN; k++) { const d = NCD[k]; if (d < V.from || d > V.to || !ncScope(k) || NCTT[k] !== t) continue; nn++; }
    const tr = teamRows(CUR).find(y => y.t === t);
    return ` (${pct0(r.nc, r.n + r.nc)} of this TME's appointments; all ${esc(TEAMS[t])} ${tr ? pct0(nn, tr.n + nn) : '—'})`;
  }
  function meDet(me, gs, open) {
    const list = apptRows(i => AME[i] === me && (gs < 0 || GROUP_OF[ATT[i]] === gs)), o = [0, 0, 0, 0, 0, 0];
    list.forEach(i => { o[AO[i]]++; });
    const tb = gs >= 0 ? meTmes(me, gs) : '';   // with the TMEs shown, the appointments stay folded
    return tb + `<details class="appts"${open && !tb ? ' open' : ''}><summary>See the ${n0(list.length)} ${gs < 0 ? '' : esc(GROUPS[gs]) + ' '}appointment${list.length === 1 ? '' : 's'}</summary>` +
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
    const asked = gsel >= 0;
    if (TM && gsel < 0) { const g0 = groupsOf(CUR, me); let b = -1; g0.forEach((x, i) => { if (x[0] && (b < 0 || x[0] > g0[b][0])) b = i; }); gsel = b; }   // a TME: their own TME team
    const R = CUR, city = cityGroups(R), g = groupsOf(R, me), pr = PREVROWS.get(me), mine = ITEMS.filter(it => it.me === me);
    const ncK = new Map(); for (let i = 0; i < NCN; i++) if (NCME[i] === me && NCD[i] >= V.from && NCD[i] <= V.to) ncK.set(NCK[i], (ncK.get(NCK[i]) || 0) + 1);
    const wk = Array.from({ length: Math.floor(LAST / 7) + 1 }, () => [0, 0, 0]);
    for (let i = 0; i < N; i++) if (AME[i] === me) { const w = Math.floor(AD[i] / 7); wk[w][0]++; if (AO[i] >= 3) wk[w][2]++; }
    for (let j = 0; j < DLN; j++) if (DLME[j] === me) wk[Math.floor(DLD[j] / 7)][1] += DLW[j];   // deals closed (Sales MIS rule)
    const mx = Math.max(1, ...wk.map(x => Math.max(x[0], x[1]))), Wd = 500, Hd = 90, bw = Wd / wk.length;
    const spark = `<svg width="100%" viewBox="0 0 ${Wd} ${Hd}" preserveAspectRatio="none" style="height:${Hd}px" role="img" aria-label="Appointments per week since April">${wk.map((v, w) => { const op = w * 7 + 6 >= V.from && w * 7 <= V.to ? 1 : .4; const h = v[0] / mx * (Hd - 4), hm = v[2] / mx * (Hd - 4), hd = v[1] / mx * (Hd - 4); return `<rect x="${(w * bw).toFixed(1)}" y="${(Hd - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" fill="#9DB7D6" opacity="${op}"/><rect x="${(w * bw).toFixed(1)}" y="${(Hd - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${hm.toFixed(1)}" fill="#E3C27D" opacity="${op}"/><rect x="${(w * bw).toFixed(1)}" y="${(Hd - hd).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${hd.toFixed(1)}" fill="#12875F" opacity="${op}"/>`; }).join('')}</svg>`;
    const items = mine.length ? `<ul class="mitems">${mine.map(it => { const done = isDone(it); return `<li class="${it.sev}${done ? ' done' : ''}"><span class="tag ${done ? 'ok' : it.sev}">${done ? ICON.done : ICON[it.sev]}${done ? 'Checked' : it.sev === 'rev' ? 'Review' : 'Info'}</span><div><b>${esc(CHECKS[it.kind].label)}</b><p>${it.why}</p></div><button type="button" class="btn" data-item="${esc(it.id)}">See ${plural(it.n, recWord(it).replace(/s$/, ''), recWord(it))}</button></li>`; }).join('')}</ul>` : `<p class="okline">${ICON.done} No check was raised for this ME in these dates.</p>`;
    const prevLine = pr && pr.n && r.n ? `<p class="dline mu">${esc(prevName())}: ${n0(pr.n)} appointments given, ${fP(pr.attP)} attended, ${plural(pr.deals, 'deal')} closed.</p>` : '';
    openDrawer(`<h2 id="drawerH">${esc(r.name)}</h2><p class="where">${r.code ? `${W.s} code ${esc(r.code)}` : 'Deals closed whose deal record has no TME'}${r.lead >= 0 && r.lead === r.node ? (DEPTH[r.lead] === 2 ? ` · Team leader, under manager ${esc(r.mgr)}` : DEPTH[r.lead] === 1 ? ` · Manager under ${esc(HEADNAME)}` : ` · ${W.s} head`)
        : `${r.tl ? ` · Team leader ${esc(r.tl)}` : ''}${r.mgr ? ` · ${r.node === OUTN ? esc(r.mgr) : `Manager ${esc(r.mgr)}`}` : ''}`}${r.des ? ` · ${esc(r.des)}` : ''}${r.city ? ` · based in ${esc(r.city)}` : ''}${HRJ[me] ? ` · ${esc(tenure(HRJ[me]))}` : ''}<br>${esc(periodName())}</p>` +
      (V.view === 'checks' ? `<h3>Checks for this ME</h3>${items}` : '') +
      (TM ? tmeFlow(me, r) + prevLine + tmeAppts(me, r) + tmeTop(me, r) : miniFlow(r.n, r.att, r.away ? null : r.deals, r.pd !== null ? `${r.pd} days present` : '') + prevLine) +
      (!TM && CLN && r.calls ? `<p class="dline">Calls: <b>${n0(r.calls)}</b>${r.clPd ? ` (${n0(r.clPd)} a day present)` : ''} · connected <b>${n0(r.conn)}</b> (${fP(r.connP)}; ${esc(META.city)} ${fP(pc(CITY.cl[1], CITY.cl[0]))}) · ${r.apc === null ? `too few connected dialer calls (under ${APC_MIN}) for appointments per 1,000 connected` : `<b>${r.apc.toFixed(1)}</b> appointments given per 1,000 connected`} (${esc(META.city)} ${CITY.cl[1] ? (CITY.n / CITY.cl[1] * APC_PER).toFixed(1) : '—'})</p>` : '') +
      (r.away ? `<p class="dline mu">An ME of another city: the Sales MIS counts their deals closed in that city, so none show here.</p>` : '') +
      (r.n >= MINR ? '' : `<p class="dline mu">Fewer than ${MINR} appointments in these dates: percentages swing a lot.</p>`) +
      `<h3>By TME team</h3><p class="cmpn">Click a team for the ${W.cp} behind it and its appointments, below.</p>` +
      `<div class="mlist" id="meTeams">${MHEAD}${GROUPS.map((l, i) => g[i][0]
        ? `<button type="button" class="srow tsel" data-tg="${i}" aria-pressed="${gsel === i}" title="List only the ${esc(l)} appointments">${mrow(esc(l), g[i])}</button>`
        : `<div class="srow">${mrow(esc(l), g[i])}</div>`).join('')}` +
      `<button type="button" class="srow tsel tall" data-tg="-1" aria-pressed="${gsel < 0}" title="List all the appointments">${mrow('All teams', g.reduce((s, x) => [s[0] + x[0], s[1] + x[1], s[2] + x[2]], [0, 0, 0]), 'tot')}</button></div>` +
      `<p class="hint">${esc(META.city)}, attended: ${GROUPS.map((l, i) => `${esc(l)} ${pct0(city[i][1], city[i][0])}`).join(' · ')}.</p>` +
      `<div id="meDet">${meDet(me, gsel, gsel >= 0)}</div>` +
      `<h3>Dispositions</h3>${dispLines(r.o)}` + (TM ? timingBlock(me) : '') +
      (r.nc ? `<p class="dline mu">Also ${n0(r.nc)} Not Counted/Cancelled${TM ? ncVsTeam(me, r) : ''}: ${[...ncK.entries()].sort((a, b) => b[1] - a[1]).map(([k, c]) => `${n0(c)} ${esc(NC.kinds[k])}`).join(' · ')}</p>` : '') +
      `<h3>Week by week since April</h3>${spark}<div class="okey"><span><i style="background:#12875F"></i>deals closed</span><span><i style="background:#9DB7D6"></i>attended, no deal closed</span><span><i style="background:#E3C27D"></i>not attended</span><span class="mu">faded = outside the dates</span></div>`);
    // opened on one team (a team's cells in the table, an ME in the TME view): straight to the TMEs behind them
    const th = asked && $('#meDet .tmeh'); if (th) DR.scrollTop = th.offsetTop - 18;
  }
  /* ---------- the TME view (2026-10-28, for Kushal): one TME team's appointments by the TMEs who fixed them and by the
     MEs who took them ----------
     His question: an ME does well on most teams' appointments but not on one team's - is it the appointments or the ME?
     A rate alone does not say, because MEs differ and each TME's appointments go to different MEs. So each rate here is
     set against the other side of the same appointments, in the same dates and the same TME team:
       a TME  -> the same MEs on the other TMEs' appointments (how the MEs usually do is taken out);
       an ME  -> the same TMEs' appointments to the other MEs (how those TMEs' appointments usually do is taken out).
     That rate is pulled towards the TME team's own by TK appointments, so a few appointments count for little, and a gap
     is green / red only past the usual swing for that many appointments (TZ standard errors, each appointment a yes / no
     at its own rate); smaller gaps stay grey, as on Your team. Deals closed are the page's own (Sales MIS rule), each with
     the TME on the deal record; deals with no TME there get a line of their own, so the lines add up to the team.
     Conversion follows the Attended / Given setting. The comparisons use all the line's MEs in the dates; the lines
     follow the team picked at the top. */
  const TK = 20, TZ = 2, NOTM = NTM;   // NOTM: deals with no TME on the deal record
  // rates and gaps need TMIN appointments whatever the dates: a TME fixes far fewer appointments than an ME takes, and
  // the page's own minimum for a day (3) would show gaps on a handful
  const TMIN = 15;
  const HD_T = TEAMS.indexOf('Hot Data');
  const tgOf = () => { const t = V.tgT >= 0 && V.tgT < NT ? V.tgT : HD_T >= 0 ? HD_T : 0; return GROUP_OF[t]; };
  // a group's biggest team (by appointments in the data), so the group survives a change of the grouping settings
  const TEAM_N = (() => { const c = new Float64Array(NT); for (let i = 0; i < N; i++) c[ATT[i]]++; return c; })();
  const repTeam = gi => { let b = -1; for (let t = 0; t < NT; t++) if (GROUP_OF[t] === gi && (b < 0 || TEAM_N[t] > TEAM_N[b])) b = t; return b; };
  // when the appointment was allocated, against its appointment day (actiontime; else the appointment date): 0 the same
  // day, 1 the day before, 2 two or more days before, 3 no allocation record (allocationtime empty: mostly deal rows
  // made at the deal)
  const TIMING = ['Same day', 'The day before', '2+ days before', 'No allocation record'];
  const timingOf = i => { if (ABK[i] < 0) return 3; const day = ASL[i] >= 0 ? Math.floor(ASL[i] / 1440) : AD[i], g = day - Math.floor(ABK[i] / 1440); return g <= 0 ? 0 : g === 1 ? 1 : 2; };
  const timingOfNC = k => { if (!NCBK || NCBK[k] < 0) return 3; const day = NCSL[k] >= 0 ? Math.floor(NCSL[k] / 1440) : NCD[k], g = day - Math.floor(NCBK[k] / 1440); return g <= 0 ? 0 : g === 1 ? 1 : 2; };
  const ncScope = k => !scoped() || (ME_NODE[NCME[k]] >= 0 && SMASK[ME_NODE[NCME[k]]] === 1);
  const ncTeamIn = (k, gi) => !!NCTT && NCTT[k] < NT && GROUP_OF[NCTT[k]] === gi;
  // [given, attended, same-day-style Not Available (Online)] per timing; fnc picks the not-counted rows (2026-10-30: added
  // back as not attended, so same-day attendance is not flattered)
  function timingMix(f, fnc) {
    const c = [[0, 0, 0], [0, 0, 0], [0, 0, 0], [0, 0, 0]];
    for (let i = 0; i < N; i++) { const d = AD[i]; if (d < V.from || d > V.to || !inScope(i) || !f(i)) continue; const k = timingOf(i); c[k][0]++; if (AO[i] <= 2) c[k][1]++; }
    if (fnc && NA_ONLINE >= 0) for (let k = 0; k < NCN; k++) { const d = NCD[k]; if (d < V.from || d > V.to || NCK[k] !== NA_ONLINE || !ncScope(k) || !fnc(k)) continue; c[timingOfNC(k)][2]++; }
    return c;
  }
  const TBK = [0, 1, 1, 2];   // timing buckets for the like-for-like: same day | the day before or earlier | no allocation record
  // per TME, team and ME in the dates: [given, attended, deals] for all the line's MEs, then the same for the team shown;
  // with the sums by ME and team (MT), by TME and team (TT) and by team (T), all MEs
  let TA = null;
  const tAgg = () => TA || (TA = tmeAgg(V.from, V.to));
  function tmeAgg(a, b) {
    const K = new Map(), get = k => { let v = K.get(k); if (!v) K.set(k, v = new Float64Array(6)); return v; };
    // attendance by allocation timing (2026-10-30, the review: next-day appointments are attended far less whoever fixed
    // or took them, and a TME's next-day share explained most of their attendance gap): per pair, team and timing bucket
    const KT = new Map(), MTT = new Map(), TTT = new Map(), TKT = new Float64Array(NT * 6);
    const gv = (M, k, n) => { let v = M.get(k); if (!v) M.set(k, v = new Float64Array(n)); return v; };
    for (let i = 0; i < N; i++) {
      const d = AD[i]; if (d < a || d > b) continue;
      const key = (ATM[i] * NT + ATT[i]) * NME + AME[i], v = get(key), at = AO[i] <= 2, tb = TBK[timingOf(i)], w = gv(KT, key * 3 + tb, 4);
      v[0]++; if (at) v[1]++; w[0]++; if (at) w[1]++;
      if (inScope(i)) { v[3]++; if (at) v[4]++; w[2]++; if (at) w[3]++; }
      const m = gv(MTT, (AME[i] * NT + ATT[i]) * 3 + tb, 2), t2 = gv(TTT, (ATM[i] * NT + ATT[i]) * 3 + tb, 2), q = (ATT[i] * 3 + tb) * 2;
      m[0]++; t2[0]++; TKT[q]++; if (at) { m[1]++; t2[1]++; TKT[q + 1]++; }
    }
    for (let j = 0; j < DLN; j++) {
      const d = DLD[j]; if (d < a || d > b) continue;
      const v = get(((DLTM[j] < NTM ? DLTM[j] : NOTM) * NT + DLT[j]) * NME + DLME[j]);
      v[2] += DLW[j]; if (SMASK[DNODE[j]]) v[5] += DLW[j];
    }
    const MT = new Map(), TT = new Map(), T = Array.from({ length: NT }, () => [0, 0, 0]);
    const add = (M, k, v) => { let s = M.get(k); if (!s) M.set(k, s = [0, 0, 0]); s[0] += v[0]; s[1] += v[1]; s[2] += v[2]; };
    for (const [k, v] of K) { const me = k % NME, q = (k - me) / NME, t = q % NT, tm = (q - t) / NT; add(MT, me * NT + t, v); add(TT, tm * NT + t, v); T[t][0] += v[0]; T[t][1] += v[1]; T[t][2] += v[2]; }
    return { K, MT, TT, T, KT, MTT, TTT, TKT };
  }
  const kSplit = k => { const me = k % NME, q = (k - me) / NME, t = q % NT; return { me, t, tm: (q - t) / NT }; };
  // one pair's like-for-like conversion: the other side's rate (o = [given, attended, deals], the pair itself taken out),
  // pulled towards the TME team's (c) by TK appointments; adds what it gives for this pair (dn = conversion base). The
  // attendance part is lflA, by allocation timing
  function lfl(r, g, dn, o, c) {
    const cd = CB() ? c[0] : c[1], pd = cd ? c[2] / cd : 0, od = Math.max(0, CB() ? o[0] : o[1]);
    const bd = Math.min(.98, (Math.max(0, o[2]) + TK * pd) / (od + TK));
    r.ed += dn * bd; r.vd += dn * bd * (1 - bd);
  }
  // one pair's like-for-like attendance, timing bucket by timing bucket: the other side's rate in that bucket (the pair
  // taken out), pulled towards the team's own rate in that bucket by TK appointments
  function lflA(r, A, key, me, t, tm, side) {
    for (let tb = 0; tb < 3; tb++) {
      const w = A.KT.get(key * 3 + tb); if (!w || !w[2]) continue;
      const S = side === 'tme' ? A.MTT.get((me * NT + t) * 3 + tb) : A.TTT.get((tm * NT + t) * 3 + tb);
      const cg = A.TKT[(t * 3 + tb) * 2], pa = cg ? A.TKT[(t * 3 + tb) * 2 + 1] / cg : 0;
      const ba = (Math.max(0, S[1] - w[1]) + TK * pa) / (Math.max(0, S[0] - w[0]) + TK);
      r.ea += w[2] * ba; r.va += w[2] * ba * (1 - ba);
    }
  }
  const tFin = r => {
    const dn = CB() ? r.n : r.att;
    return Object.assign(r, { attP: pc(r.att, r.n), conv: pc(r.deals, dn), dn, bA: r.n && r.ea ? r.ea / r.n * 100 : null, bC: dn && r.ed ? r.ed / dn * 100 : null,
      zA: r.va > 0 ? (r.att - r.ea) / Math.sqrt(r.va) : 0, zC: r.vd > 0 ? (r.deals - r.ed) / Math.sqrt(r.vd) : 0 });
  };
  // the lines of one TME team group: side 'tme' = one per TME (against the same MEs), 'me' = one per ME (against the
  // same TMEs); only (also = the one TME or ME wanted, for the side windows)
  function tRows(A, gi, side, only = -1) {
    const R = new Map();
    for (const [k, v] of A.K) {
      if (!(v[3] || v[5])) continue;
      const { me, t, tm } = kSplit(k);
      if (GROUP_OF[t] !== gi) continue;
      const id = side === 'tme' ? tm : me; if (only >= 0 && id !== only) continue;
      let r = R.get(id); if (!r) R.set(id, r = { id, n: 0, att: 0, deals: 0, other: new Set(), teams: new Map(), ea: 0, va: 0, ed: 0, vd: 0 });
      r.n += v[3]; r.att += v[4]; r.deals += v[5];
      if (v[3]) { r.other.add(side === 'tme' ? me : tm); r.teams.set(t, (r.teams.get(t) || 0) + v[3]); }
      if (tm === NOTM || !v[3]) continue;
      const S = side === 'tme' ? A.MT.get(me * NT + t) : A.TT.get(tm * NT + t);
      lfl(r, v[3], CB() ? v[3] : v[4], [S[0] - v[0], S[1] - v[1], S[2] - v[2]], A.T[t]);
      lflA(r, A, k, me, t, tm, side);
    }
    return [...R.values()].map(tFin);
  }
  const tSum = rows => { const s = { n: 0, att: 0, deals: 0 }; for (const r of rows) { s.n += r.n; s.att += r.att; s.deals += r.deals; } return Object.assign(s, { attP: pc(s.att, s.n), conv: cvr(s.deals, s.att, s.n) }); };
  // a gap under a rate: green / red only past the usual swing, grey otherwise; '' when too few to compare
  const tGap = (v, b, z, few, tt) => {
    if (few || v === null || b === null) return '';
    const d = Math.round(v - b);
    return `<em class="${z >= TZ ? 'up' : z <= -TZ ? 'dn' : ''}" title="${esc(tt)}">${d === 0 ? 'same' : `${d > 0 ? '+' : MINUS}${Math.abs(d)} pts`}</em>`;
  };
  const tFew = r => ({ a: r.n < TMIN, c: r.dn < TMIN });
  const SAME = side => side === 'tme' ? `the same ${W.p}` : `the same ${W.cp}`;
  // words for a group in sentences; a group of several teams (Others, Hot Data + Online) compares within each team
  const gMulti = gi => GROUP_OF.filter(g => g === gi).length > 1;
  const gApp = g => g === 'Other teams' ? "the other teams'" : g;   // before 'appointments'
  const tTitle = g => g === 'Other teams' ? "Other teams' TMEs" : `${g} TMEs`;
  // side 'tme' = a line of the other side (a TME in ME mode), 'me' = one of the page's people
  const sameLong = (side, gname, multi) => (side === 'tme') !== TM ? (multi ? "the same MEs on the other TMEs' appointments of the same team" : `the same MEs on the other ${gname} TMEs' appointments`) : (multi ? "the same TMEs' appointments (same team) to other MEs" : `the same TMEs' ${gname} appointments to other MEs`);

  // like for like across all the TME teams (TME mode, 2026-10-29): each person's lines added up over the teams, each
  // against the other side of the same appointments; deals of a pair with no appointment in the dates count, unweighed
  function lfAll(A0) {
    const A = A0 || tAgg(), R = new Map();
    for (const [k, v] of A.K) {
      if (!(v[3] || v[5])) continue;
      const { me, t, tm } = kSplit(k);
      let r = R.get(me); if (!r) R.set(me, r = { n: 0, att: 0, deals: 0, ea: 0, va: 0, ed: 0, vd: 0 });
      r.n += v[3]; r.att += v[4]; r.deals += v[5];
      if (tm === NOTM || !v[3]) continue;
      const S = A.TT.get(tm * NT + t);
      lfl(r, v[3], CB() ? v[3] : v[4], [S[0] - v[0], S[1] - v[1], S[2] - v[2]], A.T[t]);
      lflA(r, A, k, me, t, tm, 'me');
    }
    return R;
  }
  const lfOf = s => s && s.lf && s.lf.n ? tFin(Object.assign({}, s.lf)) : null;
  // each person's like-for-like month by month since April (2026-10-30, the review: is a gap a pattern or one month?), for
  // the team picked and the settings; worked out once per draw, when first needed
  let MLF = null;
  const monthLF = () => MLF || (MLF = MPRE.map(M => ({ M, _R: null, get R() { return this._R || (this._R = lfAll(tmeAgg(M.a, M.b))); } })));   // each month worked out only when asked
  // below the same MEs on conversion in how many of the last 3 months up to the dates' end (with TMIN+ in the base)
  function monthsBelow(me) {
    const L = monthLF().filter(o => o.M.a <= V.to).slice(-3); let below = 0, of = 0;
    for (const o of L) { const y = o.R.get(me); if (!y || !y.n) continue; const z = tFin(Object.assign({}, y)); if (tFew(z).c || z.bC === null) continue; of++; if (z.conv < z.bC) below++; }
    return { below, of };
  }
  // the gap's words when pointed at
  const lfTip = (r, kind) => { const b = kind === 'a' ? r.bA : r.bC, n = kind === 'a' ? r.n : r.dn, e = kind === 'a' ? r.ea : r.ed, v = kind === 'a' ? r.va : r.vd, got = kind === 'a' ? r.att : r.deals;
    return `The same MEs on the other TMEs' appointments${kind === 'a' ? ', allocated as long before the day' : ''}: ${fPi(b)}. At that rate ${plural(Math.round(n), kind === 'a' || CB() ? 'appointment' : 'attended appt')} give about ${n0(e)} ${kind === 'a' ? 'attended' : 'deals closed'} (usual swing ±${n0(TZ * Math.sqrt(v))}); here ${n0(got)}.`; };
  const lfGap = (s, kind) => { const r = lfOf(s); if (!r) return ''; const f = tFew(r); return kind === 'a' ? tGap(r.attP, r.bA, r.zA, f.a, lfTip(r, 'a')) : tGap(r.conv, r.bC, r.zC, f.c, lfTip(r, 'c')); };
  const lfPts = (s, kind) => { const r = lfOf(s); if (!r) return null; const f = tFew(r); return kind === 'a' ? (f.a || r.bA === null ? null : Math.round((r.attP - r.bA) * 10) / 10) : (f.c || r.bC === null ? null : Math.round((r.conv - r.bC) * 10) / 10); };
  const lfCell = (s, kind) => { const r = lfOf(s), v = lfPts(s, kind); if (v === null) return '—'; const z = kind === 'a' ? r.zA : r.zC, d = Math.round(v);
    return `<span class="lfv ${z >= TZ ? 'up' : z <= -TZ ? 'dn' : ''}" title="${esc(lfTip(r, kind))}">${d === 0 ? '0' : `${d > 0 ? '+' : MINUS}${Math.abs(d)}`}</span>`; };

  // when a TME's appointments were allocated, against their TME team (the TME's window in TME mode)
  function timingBlock(me) {
    const g0 = groupsOf(CUR, me); let gi = -1; g0.forEach((x, i) => { if (x[0] && (gi < 0 || x[0] > g0[gi][0])) gi = i; }); if (gi < 0) return '';
    const inG = i => GROUP_OF[ATT[i]] === gi, allG = `All ${GROUPS[gi]}`;
    const tmx = timingMix(i => AME[i] === me, k => NCME[k] === me), gmx = timingMix(inG, k => ncTeamIn(k, gi)), tN = tmx.reduce((s, c) => s + c[0], 0), gN = gmx.reduce((s, c) => s + c[0], 0);
    if (!tN) return '';
    return `<h3>When they were allocated</h3><p class="cmpn">Allocated against the appointment day. A company not available for a same-day appointment is filed as Not Counted/Cancelled (Not Available (Online)), not as Not Available; the attended % here counts those back in as not attended.</p>` +
      `<div class="dlw"><table class="dl ttim"><thead><tr><th>Allocated</th><th class="n">This TME<br><span class="mu">share of given</span></th><th class="n">${esc(allG)}<br><span class="mu">share of given</span></th><th class="n">This TME<br><span class="mu">attended %</span></th><th class="n">${esc(allG)}<br><span class="mu">attended %</span></th></tr></thead><tbody>` +
      TIMING.map((l, k) => tmx[k][0] || gmx[k][0] ? `<tr><td>${l}</td><td class="n"><b>${pct0(tmx[k][0], tN)}</b> <span class="mu">${n0(tmx[k][0])}</span></td><td class="n">${pct0(gmx[k][0], gN)}</td><td class="n">${tmx[k][0] ? (tmx[k][0] >= 5 ? pct0(tmx[k][1], tmx[k][0] + tmx[k][2]) : `<span class="mu">${n0(tmx[k][1])} of ${n0(tmx[k][0] + tmx[k][2])}</span>`) : '—'}</td><td class="n">${pct0(gmx[k][1], gmx[k][0] + gmx[k][2])}</td></tr>` : '').join('') + `</tbody></table></div>`;
  }

  // a team group's side window (a team card on the Overview; brought back 29 Oct, the user asked where it went): Super Cat
  // or Hot Data (one TME team each), or the teams of a group together; its funnel, the teams in it, the dispositions and
  // the people who took (ME mode) or fixed (TME mode) its appointments; at the foot, each of them against the other side
  function openGroup(gi, one = -1) {
    const R = CUR, teams = teamRows(R).filter(t => GROUP_OF[t.t] === gi), y = one >= 0 ? teams.find(t => t.t === one) : null, x = y ? [y.n, y.a, y.d] : cityGroups(R)[gi];
    GRP = gi;
    openDrawer(`<h2 id="drawerH">${esc(one >= 0 ? TEAMS[one] : GROUPS[gi])}</h2><p class="where">TME team${teams.length > 1 && one < 0 ? 's' : ''} · ${esc(periodName())}</p>` +
      miniFlow(x[0], x[1], x[2], `${pct0(x[0], R.n)} of all`) + `<div id="grpDet">${grpDet(gi, one, one >= 0)}</div>`);
  }
  // the window's lower part (30 Oct 2026, the user: make the teams in it interactive): the teams as rows to click, like
  // the ME window's TME teams; the dispositions and the people below follow the team picked (sel; -1 = the whole group)
  let GRP = -1;
  function grpDet(gi, sel, single) {
    const R = CUR, teams = teamRows(R).filter(t => GROUP_OF[t.t] === gi), inSel = t => sel < 0 ? GROUP_OF[t] === gi : t === sel;
    const o = [0, 0, 0, 0, 0, 0]; teams.forEach(t => { if (inSel(t.t)) t.o.forEach((v, k) => { o[k] += v; }); });
    const pick = me => { const g = [0, 0, 0]; for (let t = 0; t < NT; t++) if (inSel(t)) { const k = (me * NT + t) * 3; g[0] += R.meT[k]; g[1] += R.meT[k + 1]; g[2] += R.meT[k + 2]; } return g; };
    const rows = MEROWS.filter(r => !(TM && r.me === NOTME)).map(r => ({ r, g: pick(r.me) })).filter(y => y.g[0] > 0 || y.g[2] > 0).sort((a, b) => b.g[0] - a.g[0] || b.g[2] - a.g[2]);
    const noT = TM && MEROWS.some(r => r.me === NOTME) ? pick(NOTME)[2] : 0;   // TME mode: deals with no TME on the deal record
    const tot = teams.reduce((s, t) => [s[0] + t.n, s[1] + t.a, s[2] + t.d], [0, 0, 0]), name = sel < 0 ? GROUPS[gi] : TEAMS[sel], pk = sel >= 0 ? ` · ${esc(name)}` : '';
    const selT = sel >= 0 ? teams.find(t => t.t === sel) : null, dOnly = !!selT && !selT.n;   // a team with deals closed but no appointment in the dates (Cold call (no TME))
    const trow = t => `<button type="button" class="srow tsel" data-gt="${t.t}" aria-pressed="${sel === t.t}" title="${esc(`Only ${t.name}: its dispositions and ${W.p} below`)}">${mrow(t.n ? esc(t.name) : `<span title="Deals closed with no appointment behind them">${esc(t.name)}</span>`, [t.n, t.a, t.d])}</button>`;
    return (teams.length > 1 && !single ? `<h3>The teams in it</h3><p class="cmpn">Click a team for its dispositions and ${W.p} below.</p><div class="mlist" id="grpTeams">${MHEAD}${teams.map(trow).join('')}` +
        `<button type="button" class="srow tsel tall" data-gt="-1" aria-pressed="${sel < 0}" title="${esc(`All of ${GROUPS[gi]}`)}">${mrow(`All ${esc(GROUPS[gi])}`, tot, 'tot')}</button></div>` : '') +
      (dOnly ? `<p class="dline mu">No ${esc(name)} appointments in these dates: only deals closed, so no dispositions.</p>` : `<h3>Dispositions${pk}</h3>${dispLines(o)}`) +
      (TM && V.pa !== null && PREV ? (() => {   // 2026-10-30, the review: is a change broad, or a few TMEs?
        const dd = []; let cur = 0, prv = 0;
        for (let me = 0; me < NME; me++) { if (me === NOTME) continue; let c = 0, p = 0; for (let t = 0; t < NT; t++) if (inSel(t)) { c += R.meT[(me * NT + t) * 3 + 2]; p += PREV.meT[(me * NT + t) * 3 + 2]; } if (c || p) dd.push({ me, d: c - p }); cur += c; prv += p; }
        if (!cur && !prv) return '';
        const net = cur - prv, up = dd.filter(x => x.d >= .5).length, dn = dd.filter(x => x.d <= -.5).length, top = dd.slice().sort((a, b) => Math.abs(b.d) - Math.abs(a.d)).slice(0, 5).filter(x => Math.abs(x.d) >= .5), t5 = top.reduce((s, x) => s + x.d, 0);
        const sg = x => `${x > 0 ? '+' : x < 0 ? MINUS : ''}${n0(Math.abs(x))}`;
        return `<h3>Change since ${esc(prevName())}</h3><p class="dline">Deals closed: <b>${n0(cur)}</b> against ${n0(prv)} (<b>${sg(net)}</b>). ${plural(up, 'TME')} closed more, ${n0(dn)} fewer.${top.length ? ` The ${top.length} biggest changes add up to <b>${sg(t5)}</b>: ${top.map(x => `<button type="button" class="lnk" data-me="${x.me}">${esc(MES[x.me][1])}</button> ${sg(x.d)}`).join(' · ')}.` : ''}</p>`;
      })() : '') +
      `<h3>Which ${W.p} ${dOnly ? (TM ? 'are on these deals' : 'closed these deals') : `${W.doS} ${sel >= 0 ? `the ${esc(name)} appointments` : 'them'}`}</h3>` +
      (rows.length ? `<p class="cmpn">${plural(rows.length, W.s)}. Click one for their page.</p><div class="mlist">${MHEAD.replace('TME team', W.s)}${rows.slice(0, 40).map(y => `<button type="button" class="srow" data-me="${y.r.me}" data-g="${gi}">${mrow(esc(y.r.name), y.g)}</button>`).join('')}</div>`
        : `<p class="empty">${noT ? `No ${W.s}: ${plural(noT, 'deal')} closed${pk ? ' here' : ''} with no TME on the deal record.` : `No ${W.p} in these dates.`}</p>`) +
      (rows.length > 40 ? `<p class="hint">Top 40 of ${plural(rows.length, W.s)}.</p>` : '') +
      (noT && rows.length ? `<p class="hint">Also ${plural(noT, 'deal')} closed${pk ? ' here' : ''} with no TME on the deal record.</p>` : '') +
      (rows.length ? `<p class="hint"><button type="button" class="lnk" data-tw="${gi}">Each ${W.s} against the same ${W.cp}</button>: who is above or below the other side of the same appointments${sel >= 0 ? ` (all of ${esc(GROUPS[gi])})` : ''}.</p>` : '');
  }
  // a TME team's people against the other side (from the team's side window, 2026-10-29): the team's funnel, then each ME (or
  // TME) with their appointments of the team, each against the other side of the same appointments (as the person's
  // window); the biggest first, the rest added up
  function openTeamWin(gi) {
    const A = tAgg(), gname = GROUPS[gi], x = cityGroups(CUR)[gi], rows = tRows(A, gi, 'me').filter(r => r.n > 0 && !(TM && r.id === NOTME)).sort((a, b) => b.n - a.n || b.deals - a.deals);
    const others = new Set(); rows.forEach(r => r.other.forEach(o => others.add(o))); others.delete(NOTM);
    const lim = 40, show = rows.slice(0, lim), rest = rows.slice(lim), gA = pc(x[1], x[0]), gC = cvr(x[2], x[1], x[0]);
    const tip = (r, kind) => `${kind === 'a' ? 'Attended' : 'Conversion'}: ${fPi(kind === 'a' ? r.attP : r.conv)}; the same ${W.cp}: ${fPi(kind === 'a' ? r.bA : r.bC)}.`;
    const tr = r => { const f = tFew(r); return `<tr><td><button type="button" class="lnk" data-me="${r.id}" data-g="${gi}">${esc(MES[r.id][1])}</button></td><td class="n">${n0(r.n)}</td>` +
      `<td class="n">${f.a ? `<span class="mu">${fPi(r.attP)}</span>` : fPi(r.attP)} ${tGap(r.attP, r.bA, r.zA, f.a, tip(r, 'a'))}</td><td class="n">${n0(r.deals)}</td><td class="n">${f.c ? `<span class="mu">${fPi(r.conv)}</span>` : fPi(r.conv)} ${tGap(r.conv, r.bC, r.zC, f.c, tip(r, 'c'))}</td></tr>`; };
    const restRow = rest.length ? (() => { const s = tSum(rest); return `<tr class="rest"><td>${plural(rest.length, 'other ' + W.s)}, ${rest.length && rest[0].n > 1 ? `1–${n0(rest[0].n)}` : '1'} each</td><td class="n">${n0(s.n)}</td><td class="n">${fPi(s.attP)}</td><td class="n">${n0(s.deals)}</td><td class="n">${fPi(s.conv)}</td></tr>`; })() : '';
    openDrawer(`<p class="kicker"><button type="button" class="lnk" data-tgw="${gi}">← ${esc(gname)}</button></p><h2 id="drawerH" class="dt">${esc(gname)}: by ${W.s}</h2>` +
      `<p class="where">${plural(rows.length, W.s)} ${W.doS} ${esc(gApp(gname))} appointments ${TM ? 'for' : 'from'} ${plural(others.size, W.c)}${scoped() ? ` · ${esc(teamName())}` : ''}<br>${esc(periodName())}</p>` +
      `<div class="mflow">${[[n0(x[0]), 'appointments given', `${pct0(x[0], CUR.n)} of all`], [n0(x[1]), 'attended', `<b>${fPi(gA)}</b>`], [n0(x[2]), 'deals closed', `<b>${fPi(gC)}</b> ${CVOF()}`]].map(([v, l, s]) => `<div class="mstep"><div class="mv tn">${v}</div><div class="ml2">${l}</div><div class="ms">${s}</div></div>`).join(ARROW)}</div>` +
      `<p class="cmpn">Under each rate: the gap to ${sameLong('me', esc(gname), gMulti(gi))}${TM ? ', so a TME is not judged on which MEs took their appointments' : ", so an ME is not judged on which TMEs' appointments they got"}. Green / red = past the usual swing for that many appointments; grey = within it; no gap under ${TMIN}. Click ${W.aS} for their window on ${esc(gname)}.</p>` +
      (rows.length ? `<div class="dlw"><table class="dl"><thead><tr><th>${W.s}</th><th class="n">Given</th><th class="n">Attended %</th><th class="n">Deals closed</th><th class="n">Conversion %</th></tr></thead><tbody>${show.map(tr).join('')}${restRow}</tbody></table></div>` : `<p class="empty">No ${esc(gApp(gname))} appointments in these dates.</p>`));
  }
  /* one TME's side window: against the same MEs, the MEs who took the appointments, when they were allocated, month by
     month, the appointments */
  const cmp3 = (rows, fmt) => { const mx = Math.max(1, ...rows.map(r => r[1] || 0)) * 1.08; return `<div class="cmp2 cmp3">${rows.map(([l, v, cls]) => `<div class="r"><span class="l">${l}</span><span class="tr"><i class="${cls || ''}" style="width:${((v || 0) / mx * 100).toFixed(1)}%"></i></span>${cls === 'me' ? `<b class="tn">${fmt(v)}</b>` : `<span class="tn">${fmt(v)}</span>`}</div>`).join('')}</div>`; };
  // the sentence under a comparison: within the usual swing, or above / below it, with the counts behind it
  function tSay(r, kind, other, few) {
    const n = kind === 'a' ? r.n : r.dn, e = kind === 'a' ? r.ea : r.ed, v = kind === 'a' ? r.va : r.vd, got = kind === 'a' ? r.att : r.deals, z = kind === 'a' ? r.zA : r.zC;
    const unit = kind === 'a' ? 'attended' : 'deals closed', base = kind === 'a' ? 'appointments given' : CB() ? 'appointments given' : 'attended appts';
    if (few) return `<p class="cmpn tsay">Fewer than ${TMIN} ${base}: too few to compare.</p>`;
    const sw = `usual swing ±${n0(TZ * Math.sqrt(v))}`;
    return `<p class="cmpn tsay"><b class="${z >= TZ ? 'up' : z <= -TZ ? 'dn' : ''}">${z >= TZ ? 'Above' : z <= -TZ ? 'Below' : 'Within'} the usual swing</b>: ${n0(got)} ${unit} on ${n0(n)} ${base}, where ${other}' rate gives about ${n0(e)} (${sw}).</p>`;
  }
  function openTme(tm, gi) {
    if (gi === undefined || gi < 0) { const c = new Float64Array(NG); for (let i = 0; i < N; i++) if (ATM[i] === tm && AD[i] >= V.from && AD[i] <= V.to && inScope(i)) c[GROUP_OF[ATT[i]]]++; let b = -1; c.forEach((v, k) => { if (v && (b < 0 || v > c[b])) b = k; }); gi = b >= 0 ? b : tgOf(); }
    const A = tAgg(), r = tRows(A, gi, 'tme', tm)[0];
    if (!r) return;
    const gname = GROUPS[gi], inG = i => GROUP_OF[ATT[i]] === gi, x = cityGroups(CUR)[gi], gAttP = pc(x[1], x[0]), gConv = cvr(x[2], x[1], x[0]);
    const idx = apptRows(i => ATM[i] === tm && inG(i)), o = [0, 0, 0, 0, 0, 0]; idx.forEach(i => { o[AO[i]]++; });
    const fA = tFew(r).a, fC = tFew(r).c, allG = `All ${gname}`;
    // the MEs who took them: with each ME's own rate on the other TMEs' appointments of the team
    const byMe = new Map();
    for (const [k, v] of A.K) {
      if (!(v[3] || v[5])) continue;
      const s = kSplit(k); if (s.tm !== tm || GROUP_OF[s.t] !== gi) continue;
      let m = byMe.get(s.me); if (!m) byMe.set(s.me, m = { me: s.me, n: 0, att: 0, deals: 0, o: [0, 0, 0] });
      m.n += v[3]; m.att += v[4]; m.deals += v[5];
      const S = A.MT.get(s.me * NT + s.t); m.o[0] += S[0] - v[0]; m.o[1] += S[1] - v[1]; m.o[2] += S[2] - v[2];
    }
    const ml = [...byMe.values()].filter(m => m.n || m.deals).sort((a, b) => b.n - a.n || b.deals - a.deals), top = ml[0];
    const meTbl = ml.length ? `<div class="dlw"><table class="dl"><thead><tr><th>${W.s}</th><th class="n">Given</th><th class="n">Attended</th><th class="n">Deals closed</th><th class="n">The ${W.s} with other ${W.cp}<br><span class="mu">conversion · of</span></th></tr></thead><tbody>` +
      ml.slice(0, 15).map(m => { const od = CB() ? m.o[0] : m.o[1]; return `<tr><td><button type="button" class="lnk" data-me="${m.me}" data-g="${gi}">${esc(MES[m.me][1])}</button></td><td class="n">${n0(m.n)}</td><td class="n">${n0(m.att)}</td><td class="n">${n0(m.deals)}</td><td class="n">${od >= TMIN ? fPi(pc(m.o[2], od)) : '<span class="mu">—</span>'} <span class="mu">${n0(od)}</span></td></tr>`; }).join('') +
      (ml.length > 15 ? (() => { const R2 = ml.slice(15), s2 = R2.reduce((t, m) => [t[0] + m.n, t[1] + m.att, t[2] + m.deals], [0, 0, 0]), mx2 = Math.max(...R2.map(m => m.n)); return `<tr class="rest"><td>${plural(R2.length, 'other ' + W.s)}, ${mx2 > 1 ? `1–${n0(mx2)}` : '1'} each</td><td class="n">${n0(s2[0])}</td><td class="n">${n0(s2[1])}</td><td class="n">${n0(s2[2])}</td><td></td></tr>`; })() : '') +
      `</tbody></table></div>` : '<p class="empty">None in these dates.</p>';
    // when they were allocated, against the whole TME team
    const tmx = timingMix(i => ATM[i] === tm && inG(i), k => NCTM[k] === tm && ncTeamIn(k, gi)), gmx = timingMix(inG, k => ncTeamIn(k, gi)), tN = tmx.reduce((s, c) => s + c[0], 0), gN = gmx.reduce((s, c) => s + c[0], 0);
    const timTbl = tN ? `<div class="dlw"><table class="dl ttim"><thead><tr><th>Allocated</th><th class="n">This ${W.c}<br><span class="mu">share of given</span></th><th class="n">${esc(allG)}<br><span class="mu">share of given</span></th><th class="n">This ${W.c}<br><span class="mu">attended %</span></th><th class="n">${esc(allG)}<br><span class="mu">attended %</span></th></tr></thead><tbody>` +
      TIMING.map((l, k) => tmx[k][0] || gmx[k][0] ? `<tr><td>${l}</td><td class="n"><b>${pct0(tmx[k][0], tN)}</b> <span class="mu">${n0(tmx[k][0])}</span></td><td class="n">${pct0(gmx[k][0], gN)}</td><td class="n">${tmx[k][0] ? (tmx[k][0] >= 5 ? pct0(tmx[k][1], tmx[k][0] + tmx[k][2]) : `<span class="mu">${n0(tmx[k][1])} of ${n0(tmx[k][0] + tmx[k][2])}</span>`) : '—'}</td><td class="n">${pct0(gmx[k][1], gmx[k][0] + gmx[k][2])}</td></tr>` : '').join('') + `</tbody></table></div>` : '';
    // not counted / cancelled appointments of this TME (they carry no team: counted with the TME's usual team)
    const ncK = new Map(); let nc = 0, gnc = 0;
    for (let k2 = 0; k2 < NCN; k2++) {
      const d = NCD[k2]; if (d < V.from || d > V.to) continue;
      if (scoped() && !(ME_NODE[NCME[k2]] >= 0 && SMASK[ME_NODE[NCME[k2]]])) continue;
      const tt = TME_TEAM[NCTM[k2]]; if (tt >= 0 && GROUP_OF[tt] === gi) gnc++;
      if (NCTM[k2] === tm) { nc++; ncK.set(NCK[k2], (ncK.get(NCK[k2]) || 0) + 1); }
    }
    // month by month since April: this TME's lines on the team's appointments, with the whole team's rates
    const MON = MPRE.map(M => ({ M, t: [0, 0, 0], g: [0, 0, 0] })), mOf = d => { for (let k2 = MON.length - 1; k2 >= 0; k2--) if (d >= MON[k2].M.a) return MON[k2]; return null; };
    for (let i = 0; i < N; i++) { if (!inG(i) || !inScope(i)) continue; const m = mOf(AD[i]); if (!m) continue; m.g[0]++; if (AO[i] <= 2) m.g[1]++; if (ATM[i] === tm) { m.t[0]++; if (AO[i] <= 2) m.t[1]++; } }
    for (let j = 0; j < DLN; j++) { if (GROUP_OF[DLT[j]] !== gi || !SMASK[DNODE[j]]) continue; const m = mOf(DLD[j]); if (!m) continue; m.g[2] += DLW[j]; if (DLTM[j] === tm) m.t[2] += DLW[j]; }
    const mrows = MON.filter(m => m.t[0] || m.t[2]);
    const monTbl = mrows.length ? `<div class="dlw"><table class="dl tmon"><thead><tr><th>Month</th><th class="n">Given</th><th class="n">Attended %<br><span class="mu">${esc(allG)}</span></th><th class="n">Deals closed</th><th class="n">Conversion %<br><span class="mu">${esc(allG)}</span></th></tr></thead><tbody>` +
      mrows.map(m => { const on = m.M.b >= V.from && m.M.a <= V.to, few = m.t[0] < TMIN; return `<tr${on ? ' class="on"' : ''}><td>${esc(m.M.short)}</td><td class="n">${n0(m.t[0])}</td><td class="n">${few ? `<span class="mu">${pct0(m.t[1], m.t[0])}</span>` : pct0(m.t[1], m.t[0])} <span class="mu">${pct0(m.g[1], m.g[0])}</span></td><td class="n">${n0(m.t[2])}</td><td class="n">${few ? `<span class="mu">${fPi(cvr(m.t[2], m.t[1], m.t[0]))}</span>` : fPi(cvr(m.t[2], m.t[1], m.t[0]))} <span class="mu">${fPi(cvr(m.g[2], m.g[1], m.g[0]))}</span></td></tr>`; }).join('') +
      `</tbody></table></div>` : '';
    const teams = [...r.teams.entries()].sort((a, b) => b[1] - a[1]).map(([t]) => TEAMS[t]);
    openDrawer(`<p class="kicker"><span class="tmetag">${W.c} · ${esc(gname)}</span></p><h2 id="drawerH">${esc(TMES[tm][1])}</h2>` +
      `<p class="where">${W.c} code ${esc(TMES[tm][0])}${teams.length > 1 || teams[0] !== gname ? ` · ${esc(teams.join(', '))}` : ''} · ${W.doC} ${plural(r.n, 'appointment')} ${TM ? 'from' : 'for'} ${plural(r.other.size, W.s)}${scoped() ? ` in ${esc(teamName())}` : ''}<br>${esc(periodName())}</p>` +
      `<div class="mflow">${[[n0(r.n), 'appointments given', `${pct0(r.n, x[0])} of ${esc(gname)}`], [n0(r.att), 'attended', `<b>${pct0(r.att, r.n)}</b> · ${esc(allG)} ${fPi(gAttP)}`], [n0(r.deals), 'deals closed', `<b>${fPi(r.conv)}</b> ${CVOF()} · ${esc(allG)} ${fPi(gConv)}`]].map(([v, l, s]) => `<div class="mstep"><div class="mv tn">${v}</div><div class="ml2">${l}</div><div class="ms">${s}</div></div>`).join(ARROW)}</div>` +
      `<h3>Against the same ${W.p}</h3><p class="cmpn">${TM ? `The same TMEs = the ${plural(r.other.size, 'TME')} who fixed these appointments, with the other MEs${gMulti(gi) ? ' (same team)' : ` on ${esc(gname)}`} in these dates. It takes out which TMEs' appointments this ME got.` : `The same MEs = the ${plural(r.other.size, 'ME')} who took these appointments, on the other TMEs' appointments${gMulti(gi) ? ' of the same team' : ` of ${esc(gname)}`} in these dates. It takes out which MEs got them.`}</p>` +
      `<div class="tcmp"><div><p class="tcl">Attended %</p>${cmp3([[`This ${W.c}`, r.attP, 'me'], [`Same ${W.p}`, r.bA], [allG, gAttP]], fPi)}${tSay(r, 'a', `the same ${W.p}`, fA)}</div>` +
      `<div><p class="tcl">Conversion %</p>${cmp3([[`This ${W.c}`, r.conv, 'me'], [`Same ${W.p}`, r.bC], [allG, gConv]], fPi)}${tSay(r, 'c', `the same ${W.p}`, fC)}</div></div>` +
      `<h3>The ${W.p} who ${W.doS} them</h3><p class="cmpn">${ml.length > 1 ? `${plural(ml.length, W.s)}; the most ${TM ? 'from' : 'to'} one ${W.s}: ${n0(top.n)} of ${n0(r.n)} (${pct0(top.n, r.n)}). ` : ''}Last column: the ${W.s} ${TM ? "with the other MEs" : "on the other TMEs' appointments"}${gMulti(gi) ? ' of the same team' : ` of ${esc(gname)}`} (— under ${TMIN}). Click ${W.aS} for their window.</p>${meTbl}` +
      (tN ? `<h3>When they were allocated</h3><p class="cmpn">Allocated against the appointment day. A company not available for a same-day appointment is filed as Not Counted/Cancelled (Not Available (Online)), not as Not Available; the attended % here counts those back in as not attended.</p>${timTbl}` : '') +
      `<p class="dline">Not Counted/Cancelled: <b>${n0(nc)}</b>${nc ? ` (${pct0(nc, nc + r.n)} of this ${W.c}'s, ${esc(allG)} ${pct0(gnc, gnc + x[0])})${ncK.size ? ': ' + [...ncK.entries()].sort((a, b) => b[1] - a[1]).map(([k2, c]) => `${n0(c)} ${esc(NC.kinds[k2])}`).join(' · ') : ''}` : ''}</p>` +
      (monTbl ? `<h3>Month by month since April</h3><p class="cmpn">This ${W.c}'s appointments here; grey beside each rate: All ${esc(gname)}. Greyed rates: fewer than ${TMIN} given. The dates shown are marked.</p>${monTbl}` : '') +
      `<h3>Dispositions</h3>${dispLines(o)}` +
      `<details class="appts"><summary>See the ${plural(idx.length, 'appointment')}</summary>${apptTable(idx, ['date', 'biz', 'me', 'booked', 'slot', 'out'])}</details>`);
    DR.classList.add('tmed');
  }


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
      (idx.length ? `<div class="dlw"><table class="dl"><thead><tr><th>Date</th><th>Company</th><th>${W.s}</th><th>TME team</th>${part ? '<th>Deal</th>' : ''}</tr></thead><tbody>${idx.slice(0, lim).map(row).join('')}</tbody></table></div>` +
        (idx.length > lim ? `<p class="hint">Latest ${lim} of ${n0(idx.length)}; the CSV has them all.</p>` : '') +
        `<button type="button" class="btn" id="dealsCsv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV of these ${n0(idx.length)}</button>` : '<p class="empty">No deals closed in these dates.</p>'));
  }
  function openList(f) {
    const filt = i => (f.o === undefined || AO[i] === f.o) && (f.me === undefined || AME[i] === f.me) && (f.t === undefined || ATT[i] === f.t) && (f.g === undefined || GROUP_OF[ATT[i]] === f.g);
    const idx = apptRows(filt);
    const title = [f.o !== undefined ? OUT[f.o] : 'Appointments', f.me !== undefined ? MES[f.me][1] : '', f.t !== undefined ? TEAMS[f.t] : '', f.g !== undefined ? GROUPS[f.g] : ''].filter(Boolean).join(' · ');
    openDrawer(`<h2 id="drawerH" class="dt">${esc(title)}</h2><p class="where">${n0(idx.length)} appointments · ${esc(scopeName())} · ${esc(fRange(V.from, V.to))}</p>` +
      (f.me !== undefined ? `<div class="dact"><button type="button" class="btn" data-me="${f.me}">Open ${esc(shortName(MES[f.me][1]))}'s page</button></div>` : '') +
      `<h3>The appointments</h3>${apptTable(idx, ['date', 'biz', ...(f.me === undefined ? ['me'] : []), 'tme', ...(f.g !== undefined ? ['booked'] : []), 'slot', 'entered', 'out', ...(V.view === 'checks' ? ['flags'] : [])])}`);
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
    $('#tlClear').hidden = !scoped() || V.scope === MGRN;   // a manager's page has no way back to all teams
  }
  $('#tlClear').addEventListener('click', () => setScope(ROOT));
  // settings (gear): the conversion switch
  const SP = $('#setPop'), SBTN = $('#setBtn');
  const closeSet = () => { if (SP.hidden) return; SP.hidden = true; untip(); SBTN.setAttribute('aria-expanded', 'false'); };
  // each setting's explanation in the tooltip of the (i) beside its name: on hover, on focus, or on a click (2026-11-04, the
  // user: the panel read text-heavy); under the (i), above it when there is no room below
  const setHelp = b => {
    const h = $('#' + b.dataset.help); if (!h || !h.textContent) return;
    TIP.textContent = h.textContent; TIP.hidden = false;
    const r = b.getBoundingClientRect(), w = TIP.offsetWidth, ht = TIP.offsetHeight;
    TIP.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left - 12)) + 'px';
    TIP.style.top = (r.bottom + 6 + ht > innerHeight - 8 ? Math.max(8, r.top - ht - 6) : r.bottom + 6) + 'px';
  };
  SP.addEventListener('mouseover', ev => { const b = ev.target.closest('.sinfo'); if (b) setHelp(b); });
  SP.addEventListener('mouseout', ev => { const b = ev.target.closest('.sinfo'); if (b && !b.contains(ev.relatedTarget)) untip(); });
  SP.addEventListener('focusin', ev => { const b = ev.target.closest('.sinfo'); if (b) setHelp(b); });
  SP.addEventListener('focusout', ev => { if (ev.target.closest('.sinfo')) untip(); });
  SP.addEventListener('click', ev => { const b = ev.target.closest('.sinfo'); if (b) setHelp(b); });
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
      for (let c = ANODE[i], g = 0; c >= 0 && g < 6; g++) { n[c]++; let s = mes.get(c); if (!s) mes.set(c, s = new Set()); if (!notTme(AME[i])) s.add(AME[i]); if (c === ROOT) break; c = UPN(c); }
    }
    return { n, k: m => mes.has(m) ? mes.get(m).size : 0 };
  }
  function openTl() {
    closePops();
    const C = teamCounts(), show = m => RECENT[m] || C.n[m] || V.scope === m, byName = (a, b) => NNAME(a).localeCompare(NNAME(b));
    const item = (m, cls) => `<button type="button" class="pre ${cls}" data-tl="${m}" data-n="${esc(NNAME(m).toLowerCase())}" aria-pressed="${V.scope === m}"><span>${esc(NNAME(m))}</span><small${C.n[m] ? '' : ' class="none"'}>${ROLE(m)} · ${C.n[m] ? `${plural(C.k(m), W.s)} · ${n0(C.n[m])} appts` : 'no appointments'}</small></button>`;
    const L = MGRN >= 0 ? KIDS[MGRN].filter(m => m !== OUTN && show(m)).sort(byName).map(t => item(t, 'p2')).join('')
      : KIDS[ROOT].filter(m => m !== OUTN && show(m)).sort(byName).map(m => item(m, 'p1') + KIDS[m].filter(show).sort(byName).map(t => item(t, 'p2')).join('')).join('');
    TP.innerHTML = `<label class="search tls"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input type="search" id="tlFind" placeholder="Find a manager or team leader" autocomplete="off"></label>` +
      `<div class="tll">${MGRN >= 0 ? item(MGRN, 'p0') : `<button type="button" class="pre p0" data-tl="${ROOT}" aria-pressed="${!scoped()}"><span>All teams</span><small>${esc(HEADNAME)} · ${plural(C.k(ROOT), W.s)} · ${n0(C.n[ROOT])} appts</small></button>`}${L}</div>`;
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
  // settings: which MEs the page counts (a master filter: changing it reloads the page with the same link)
  (() => {
    const all = outsideIn(0, LAST), HEADNAME = MEHEAD, lineName = `${HEADNAME}'s line only`;
    $('#lnSw').innerHTML = `<button type="button" data-v="line" aria-pressed="${LINE_ONLY}" title="Leave out the MEs whose HR reporting line does not reach ${esc(HEADNAME)}">${esc(lineName)}</button><button type="button" data-v="all" aria-pressed="${!LINE_ONLY}" title="Every ME, as the Sales MIS counts them">All MEs</button>`;
    $('#lnHelp').textContent = `${lineName} leaves out the MEs whose HR reporting line does not reach ${HEADNAME}: since 1 April, ${plural(all.mes, 'ME')} with ${plural(all.n, 'appointment')} given and ${n0(all.dl)} deals closed. They are left out of every figure, and ${META.city} then means ${HEADNAME}'s line. All MEs matches the Sales MIS. The page reloads when this changes.`;
    const tag = $('#lineTag'); if (tag) { tag.hidden = !LINE_ONLY; tag.textContent = lineName; tag.title = `${META.city} figures cover ${HEADNAME}'s line only (settings)`; }
    if (MGRN >= 0) {
      const sw = $('#lnSw'); if (sw.previousElementSibling) sw.previousElementSibling.hidden = true; sw.hidden = true; $('#lnHelp').hidden = true;
      if (tag) { tag.hidden = false; tag.textContent = `${NNAME(MGRN)}'s team`; tag.title = `This page holds ${NNAME(MGRN)}'s team only; ${META.city} figures are ${HEADNAME}'s whole line, for comparison`; }
      return;
    }
    $('#lnSw').addEventListener('click', ev => {
      const b = ev.target.closest('[data-v]'); if (!b || (b.dataset.v === 'line') === LINE_ONLY) return;
      try { sessionStorage.setItem(LINE_KEY, b.dataset.v); } catch (e) { return; }
      location.reload();
    });
    document.addEventListener('click', ev => { if (ev.target.closest('[data-open-set]')) { ev.preventDefault(); if (SP.hidden) SBTN.click(); } });
  })();
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
    if (TM) h.set('mode', 'tme');
    if (SK_ON) h.set('sk', '1');
    if (TM && V.tsec !== 'teams') h.set('sec', V.tsec);
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
    if (['sum', 'teams', 'tmes'].includes(h.get('sec'))) V.tsec = h.get('sec');
    else if (['flow', 'mgrs'].includes(h.get('sec'))) V.tsec = 'teams';   // links from before 31 Oct
    if (h.get('view') === 'tme' || (TM && V.view === 'checks')) V.view = 'team';   // the TME view of 28 Oct is TME mode's Overview
    if (h.get('cb') === 'given') V.cb = 'given';
    const tc = h.get('team') || h.get('tl');   // tl: links from before the hierarchy (a team leader) open that team
    if (tc) { const m = MGRS.findIndex(x => String(x[0]) === tc); if (m >= 0 && DEPTH[m] >= 0 && (MGRN < 0 || inMgr(TEAMOF[m]))) V.scope = TEAMOF[m]; }
    if (h.has('period')) setPreset(h.get('period'));
    else if (h.has('from') && h.has('to')) { const a = offOf(h.get('from')), z = offOf(h.get('to')); if (a >= 0 && z <= LAST && a <= z) setRange(a, z); }
  }


  /* ---------- notes ---------- */
  function renderNotes() {
    const c = META.check, ds = META.dealSrc || {};
    $('#notes').innerHTML = [
      MGRN >= 0 ? `<p><b>This page.</b> ${esc(NNAME(MGRN))}'s team only: their team leaders, MEs, appointments and deals closed. ${esc(META.city)} figures (the comparison lines) are ${esc(MEHEAD)}'s whole line, every manager's team together; no other team's MEs, team leaders or businesses are in this page.</p>` : '',
      `<p><b>Appointments.</b> ${esc(META.city)}: appointments given to MEs, counted as the Sales MIS counts them (jda_flag 0 and 3; every appointment with a real disposition, including those a BDE set, which the table marks given_count 0; MEs in team Corporate or section Sales (Training) are left out; a Sunday appointment counts on the Saturday before), 1 April to ${esc(fDate(dOf(LAST), true))}; refreshed ${esc(META.refreshed.replace('T', ' at '))}. The date is the appointment's to_date. An appointment counts for the ME it was finally allocated to; the table keeps no earlier allocation.</p>`,
      `<p><b>Attended</b> = disposition Dealclosed, Follow Up or Not Interested. <b>Not attended</b> = Not Available, Pending (no disposition yet) or Not Visited. <b>Conversion</b> = deals closed ÷ ${CB() ? 'appointments given' : 'attended'} (switch at the top: Conversion on Attended / Given). <b>Not Counted/Cancelled</b> = appointments with that disposition (Not Available (Online), TME Cancelled, Fake Appt, Details Incorrect, Appointment Refixed…); they are shown per ME, not added to appointments.</p>`,
      ds.mis !== undefined
        ? `<p><b>Deals closed</b> are counted as the Sales MIS counts them (JDS-ME): every deal row in the deals data (one row per payment version, dc_genio) with jda_flag 0 or 3 and an ME, whose ME was a ${esc(META.city)} ME that month (HR's monthly record: city, emptype ME, team not Corporate / JDA; else the HR city), on the deal date (dealclosed_date; the table books Sunday deals on Saturday). A deal counts whether or not an appointment sits behind it: deals with no TME are under the TME team 'Cold call (no TME)', a top-up payment the next day is a deal that day. Each deal is with its ME and the ME's team leader that month, and with the deal's TME team (final_team_type_name).${ds.misTo && ds.misTo < iso(dOf(LAST)) ? ` The deals table runs to ${esc(fDate(new Date(ds.misTo + 'T00:00:00Z'), true))}; later days use the appointments with disposition Dealclosed until it has them.` : ''} So an ME can have deals closed on a day with no appointment, and conversion (deals closed ÷ ${CB() ? 'appointments given' : 'attended'}) can pass 100% on a few appointments.</p>` +
          `<p><b>Dealclosed</b> (in Dispositions and the appointment lists) is the appointment's own disposition, checked against the same deals table: an appointment is Dealclosed when its docid has a deal that day (a Saturday deal also counts for the next day or two); ${n0(ds.toDeal)} not marked Dealclosed in the appointment table had a deal, ${n0(ds.fromDeal)} marked Dealclosed there had no deal of their own and count with Follow Up.</p>`
        : `<p><b>Deals closed</b> are the appointments with disposition Dealclosed (the deals table was not read on this refresh).</p>`,
      `<p><b>Comparisons.</b> A single day is compared with the previous usual day. A low day (fewer than 40% of a usual day's appointments given in ${esc(META.city)}, about ${n0(Math.round(USUAL * 0.4))}; a holiday or a short day) is named under the heading when either set of dates has one, as the changes are then not like for like. <b>Green / red</b> in Your team: 10+ points from the line above for 1–6 days, 5+ points for 7 days or more; smaller gaps stay grey.</p>`,
      `<p><b>Across managers</b> (band, right): the lowest and highest attended % and conversion among the teams one level below the team shown (managers, team leaders, or MEs in a team leader's team), counting teams with 10+ appointments given (MEs: ${MINR}+), and who has the most Not Available. <b>The trend</b> under it: attended % and conversion each usual day of the last 4 weeks (or each week of the last 12 weeks, for 7 days or more), up to the last day shown, for the team shown; days with fewer than 5 appointments are left out.</p>`,
      TM ? '' : `<p><b>MEs of another city</b> (their HR city that month is not ${esc(META.city)}; most sit in "${esc(OUT_NAME)}") take ${esc(META.city)} appointments, which count here, but the Sales MIS counts their deals closed in their own city, so they show "—" for deals closed and conversion.</p>`,
      `<p><b>Times.</b> Allocated = allocationtime (when the appointment was allocated to the ME); appointment time = actiontime; disposition updated = attended_date; Dealclosed at = dealclosed_date. Deals with no allocation record have no allocationtime and an appointment time equal to the Dealclosed time.</p>`,
      `<p><b>Days present, designation, home city, joining date</b>: HR records${META.hrPulled ? `, read ${esc(META.hrPulled)}` : ''}. Part months count pro rata.</p>`,
      TM ? `<p><b>TME mode.</b> The same appointments and deals closed, with the TMEs as the people: each appointment is with the TME who fixed it (the appointment's TME) and each deal closed with the TME on the deal record (it matches the appointment's TME on 99.9% of deals; deals with no TME there are one line, "No TME on the deal record"), so the totals match the ME view. Appointments an ME fixed themselves (the appointment's TME is the ME who took it; TME team BDE) are one line too, "Fixed by the ME", in the group outside the TME head's line, not the MEs as TMEs. Which records count still follows the ME setting (${esc(MEHEAD)}'s line only or all MEs). <b>TME teams</b>: ${esc(HEADNAME)} (TME head) > managers > team leaders > TMEs. The team leader is the one on the appointment that day (TMEs move between team leaders); the people above come from the SSO dump${RAW.tl.src ? ` (${esc(RAW.tl.src)})` : ''}. A TME counts in the team where most of their appointments in the dates sit; a deal closed sits with its TME's team leader that month. "${esc(OUT_NAME)}" = team leaders whose line does not reach ${esc(HEADNAME)} (mostly BDEs). <b>Days present, joining date, designation, home city</b>: HR records (else the SSO dump). <b>Calls</b>: the TMEs' dialer calls${CL && CL.to ? ` (to ${esc(fDate(new Date(CL.to + 'T00:00:00Z'), true))})` : ''}, every call whose agent is a TME (the dialer's agent = the employee code; a TME in HR that month); <b>connected</b> = a call whose line connected (trunk duration above 0) and that the TME closed with one of: client disconnected call, not contactable, call back, follow up, not interested, paid client, call to me, IVR call, discard call, do not disturb, not in business, company closed, wrong number, allocate appointment, appointment allocated to JDA, appointment refixed, invalid data, other city data, other TME data, non sales data, lead/call price high, freezed contract, error, testing, inbound call data not found. A Sunday call counts on the Saturday before. A TME's calls count when the TME has appointments given or deals closed in the dates (the band's calls are those TMEs' calls). Calls are all the TME's calls, while the appointments follow the ME setting (${esc(MEHEAD)}'s line only leaves out appointments to MEs outside it), so appointments per 1,000 connected can read a little low. Connected % depends on the lead pool the TME calls, which is not in this page's data. Some TMEs fix most of their appointments without a dialer call (many Super Cat TMEs; BDEs are not on the dialer), so for them appointments per 1,000 connected reads high; it is shown from ${APC_MIN} connected calls. On the team cards, a TME's calls count in their team in HR (the monthly record), else the team of most of their appointments in the dates; a TME's team elsewhere (the pace, the window) is set the same way. <b>Against the same MEs</b> (under the rates and in the Table): for each appointment, how the ME who took it did on the other TMEs' appointments of the same TME team in the same dates, added up over the TME's appointments; that rate is pulled towards the team's own by ${TK} appointments, and a gap is green / red only past ${TZ} standard errors (each appointment a yes / no at its rate), with no gap under ${TMIN} appointments. A gap says where to look, not why: the leads (lead source, existing paid companies), when the appointments were allocated, or the people. Lead source is not in this page's data. <b>Since 30 Oct 2026</b>: attended % is compared within the same allocation timing (same day / the day before or earlier / no record: next-day appointments are attended far less whoever fixed or took them); the band's counts say how many would land past the usual swing by chance alone (about 2.3% of the TMEs tested, each way); <b>deals vs same MEs</b> = deals closed minus what the same MEs' rate gives (the Table's column, and "Where to look first", most short first, with how many of the last 3 months were below); attended % by allocation timing counts the same-day Not Available (Online), filed as Not Counted, back in as not attended; <b>times the usual share</b> = the share of a team's appointments that went to X, against X's share of everyone else's appointments (not of all, which contains the team itself), bold only past ${TZ} standard errors; the ME managers' cards for all TME teams compare with what each team's own mix of TME teams gives at all the managers' rates; appointments per 1,000 connected counts only TMEs with ${DIAL_MIN}+ dialer calls in the dates, and not on a single day; <b>RV3yr</b> = the deals' RV_3yr, credited as the deal is counted (dc_genio), ₹ (L = lakh, cr = crore), from the deals table (the newest days, before the deals table has them, have none).</p>` : '',
      TM ? '' : `<p><b>Teams.</b> ${esc(HEADNAME)} (ME head) > managers > team leaders > MEs, from HR's reporting lines: each person's usual manager on their appointments since 1 April, until the official list is in. A team leader's or manager's own appointments count in their own team (tagged TL / Manager); "direct" = an ME who reports to a manager with no team leader. Anyone further down a chain counts in their team leader's team. An ME counts in the team where most of their appointments in the dates sit. "${esc(OUT_NAME)}" = MEs whose HR reporting line does not reach ${esc(HEADNAME)} (mostly MEs of other cities taking a Mumbai appointment).</p>`,
      TM ? '' : `<p><b>Expected</b> (TME team mix) applies the rate of ${esc(scopeName())} for each TME team to the ME's appointments, so an ME fed harder or easier leads is judged fairly. Rates need ${MIN}+ appointments. On the Checks view, <b>checked</b> marks are saved in this browser only, for these exact dates.</p>`,
      TM ? '' : `<p><b>TMEs</b> (a team card on the Overview opens its people; TME mode at the top shows every TME): one TME team's appointments by the TME who fixed them (the appointment's TME) and by the ME who took them. Deals closed are the ones above, each with the TME on the deal record (it matches the appointment's TME on 99.9% of deals); deals with no TME there have a line of their own, and so do the TMEs (or MEs) with deals closed but no appointment of the team in the dates (a few deal records carry a TME code with no appointment here, shown by the code), so the lines add up to the team; each line's deals closed are rounded, so half deals can make the lines differ from the total by one or two. <b>Against the same MEs</b> (a TME): how the MEs who took the TME's appointments did on the other TMEs' appointments of the same team in the same dates, each ME weighted by the appointments they took from the TME. <b>Against the same TMEs</b> (an ME): how the TMEs who fixed the ME's appointments did with the other MEs. Each of those rates is pulled towards the team's own by ${TK} appointments, so a few appointments count for little. <b>Usual swing</b> = ${TZ} standard errors, counting each appointment as a yes / no at that rate; green / red only past it, and no gap on fewer than ${TMIN} appointments. A gap says where to look, not why: it can come from the leads (lead source, existing paid companies), when the appointments were allocated, or the people. A deal of a TME and ME with no appointment between them in the same dates counts in the deals closed but not in what the other side's rate gives. Lead source and TME tenure are not in this page's data.</p>`,
      `<p><b>Check.</b> ${n0(c.given)} appointments, ${n0(c.attended)} attended, ${n0(c.deals)} deals closed in the data${c.left_out ? `; ${n0(c.left_out)} left out (disposition not one of the six)` : ''}.</p>`,
    ].join('');
  }

  /* ---------- render ---------- */
  function render(push) {
    untip(); closePops(); ITEM_TEAMS.clear(); TA = null; MLF = null; PACE = null;
    MINR = minFor(V.to - V.from + 1);
    setMask();
    CUR = agg(V.from, V.to); PREV = agg(V.pa, V.pb);
    CITY = !scoped() ? CUR : (() => { const s = V.scope; V.scope = ROOT; setMask(); const r = agg(V.from, V.to); V.scope = s; setMask(); return r; })();
    BASE = V.from > 0 ? agg(Math.max(0, V.from - 90), V.from - 1) : null;
    MEROWS = rowsOfMes(CUR);
    if (TM) { const LF = lfAll(); for (const r of MEROWS) r.lf = LF.get(r.me) || null; }   // the gaps to the same MEs
    const prevRows = rowsOfMes(PREV);
    PREVROWS = new Map(prevRows.map(r => [r.me, r]));
    ITEMS = TM ? [] : computeItems(CUR, MEROWS, BASE);   // the record checks are about MEs
    PREV_IDS = new Set(!TM && V.pa !== null && PREV.n ? computeItems(PREV, prevRows, V.pa > 0 ? agg(Math.max(0, V.pa - 90), V.pa - 1) : null).map(it => it.kind + '|' + it.subj) : []);
    showViews(); closeCol();
    document.body.classList.toggle('nodata', !CUR.n && !CUR.dl);
    renderTl(); renderBand(); renderSkew(); renderLadder(); renderTeams(); renderFlow(); renderMgrs(); renderSummary(); showSec(); renderList(); renderX(); if (!TM) { renderQueue(); renderPairs(); renderHow(); } renderNotes();
    document.title = `${META.city} · ${W.s} team${MGRN >= 0 ? ' · ' + NNAME(MGRN) : ''}`;
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
  // the words in the page's frame (2026-10-29): ME or TME
  (() => {
    $('#brandWho').textContent = W.s; $('#home').setAttribute('aria-label', `${W.s} team, ${META.city}: back to the dashboard`);
    document.querySelectorAll('#modeSw [data-mode]').forEach(b => b.setAttribute('aria-pressed', String((b.dataset.mode === 'tme') === TM)));
    if (!RAW.tl) { $('#modeSw').hidden = true; $('#modeSw').style.display = 'none'; }   // no TME data (a manager's page): no ME | TME switch
    document.querySelectorAll('#ovLv [data-l="3"], #xLv [data-l="3"]').forEach(b => { b.textContent = W.p; });
    $('#meSearch').placeholder = `Find ${W.aS}, TL or manager`; $('#meSearch').setAttribute('aria-label', `Find ${W.aS}, team leader or manager`);
    $('#xSearch').placeholder = `Search ${W.s}, team leader or manager`; $('#xSearch').setAttribute('aria-label', `Search ${W.s}, team leader or manager`);
    $('#xH').textContent = W.p;
    $('#tmSub').textContent = `By TME team · click one for its teams and the ${W.p} who ${W.doS} its appointments`;
    if (TM) { $('#tlBtn').title = "Show one TME manager's or team leader's team"; }
  })();
  readHash();
  render(false);
  spaMark(document.body);
})();
