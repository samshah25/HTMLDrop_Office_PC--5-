/* ===== data core: decode the day records once, add up any period on demand ===== */
const RAW = JSON.parse(document.getElementById('data').textContent);
const META = RAW.meta, COLS = RAW.cols;
const NP = COLS.pin.length;
const STATES = RAW.states, BRANCHES = RAW.branches, CITIES = RAW.cities, DISTRICTS = RAW.districts;
const NK = 16;                        // record code = channel * 4 + fresh * 2 + ecs
const CH = META.channels;             // JDA, JDS, B2B, Anonymous

function b64(s, Type) {
  const bin = atob(s), u8 = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  return new Type(u8.buffer);
}
function stream(s, withCode) {
  return { n: s.n, r: b64(s.r, Uint16Array), d: withCode ? b64(s.d, Uint16Array) : b64(s.d, Uint8Array),
           k: withCode ? b64(s.k, Uint8Array) : null, deals: b64(s.deals, Uint32Array), rv: b64(s.rv, Uint32Array) };
}
const TYS = stream(RAW.ty, true), LYS = stream(RAW.ly, true), REST = stream(RAW.rest, false);
// big deals (RV 3yr of META.bigFloor or more), one row each with the deal's size in rupees (a). They are not in the
// streams above; every sum adds them back unless the deal is above CAP (the "leave out big deals" rule).
function bstream(s, withCode) { const o = stream(s, withCode); o.a = b64(s.a, Uint32Array); return o; }
const BTY = bstream(RAW.bigTy, true), BLY = bstream(RAW.bigLy, true), BRS = bstream(RAW.bigRest, false);
let CAP = Infinity;

// day offset -> financial-year month index (Apr = 0); the same for last year's offsets (same calendar dates a year back)
const FY0 = new Date(META.fy + 'T00:00:00Z');
const dayDate = o => new Date(FY0.getTime() + o * 864e5);
const MONTH_OF = new Uint8Array(META.days + 400);
for (let o = 0; o < MONTH_OF.length; o++) { const d = dayDate(o); MONTH_OF[o] = (d.getUTCMonth() + 9) % 12; }

// per pincode, by month (12 FY months): this year; last year on the same dates (ly); the rest of last year's months
// after the data's last day (lyR, for the trend's context only). Fixed: the trend ignores the period picked.
const MON = { ty: new Float64Array(NP * 12), ly: new Float64Array(NP * 12), tyRv: new Float64Array(NP * 12), lyRv: new Float64Array(NP * 12),
              lyR: new Float64Array(NP * 12), lyRRv: new Float64Array(NP * 12) };
function buildMON() {
  for (const k in MON) MON[k].fill(0);
  for (const [S, a, ar] of [[TYS, MON.ty, MON.tyRv], [LYS, MON.ly, MON.lyRv], [BTY, MON.ty, MON.tyRv], [BLY, MON.ly, MON.lyRv]]) {
    for (let i = 0; i < S.n; i++) { if (S.a && S.a[i] > CAP) continue; const j = S.r[i] * 12 + MONTH_OF[S.d[i]]; a[j] += S.deals[i] / 100; ar[j] += S.rv[i]; }
  }
  for (const S of [REST, BRS]) for (let i = 0; i < S.n; i++) { if (S.a && S.a[i] > CAP) continue; const j = S.r[i] * 12 + S.d[i]; MON.lyR[j] += S.deals[i] / 100; MON.lyRRv[j] += S.rv[i]; }
}
buildMON();
// leave out deals above x rupees of RV 3yr (Infinity = keep every deal); the monthly series follow at once
function setCap(x) { CAP = x > 0 ? x : Infinity; buildMON(); }

/* Period sums. P = {a, b} day offsets, inclusive. Per pincode: deals and RV (this year / last year), plus deals by code
   (this year and last year) so any area's mix is a sum over its pincodes. RV is in rupees thousand. */
function sumPeriod(P) {
  const out = { ty: new Float64Array(NP), ly: new Float64Array(NP), tyRv: new Float64Array(NP), lyRv: new Float64Array(NP),
                tyK: new Float64Array(NP * NK), lyK: new Float64Array(NP * NK), lyRvK: null };
  for (const [S, d, rv, kk] of [[TYS, out.ty, out.tyRv, out.tyK], [LYS, out.ly, out.lyRv, out.lyK], [BTY, out.ty, out.tyRv, out.tyK], [BLY, out.ly, out.lyRv, out.lyK]]) {
    const r = S.r, dd = S.d, k = S.k, n = S.deals, v = S.rv, am = S.a;
    for (let i = 0; i < S.n; i++) {
      const o = dd[i];
      if (o < P.a || o > P.b || (am && am[i] > CAP)) continue;
      const p = r[i], x = n[i] / 100;
      d[p] += x; rv[p] += v[i]; kk[p * NK + k[i]] += x;
    }
  }
  return out;
}

/* An area = a list of pincode rows. Totals and mix for it. */
function areaTotals(sums, rows) {
  const t = { ty: 0, ly: 0, tyRv: 0, lyRv: 0, tyK: new Float64Array(NK), lyK: new Float64Array(NK), pins: 0 };
  for (const p of rows) {
    t.ty += sums.ty[p]; t.ly += sums.ly[p]; t.tyRv += sums.tyRv[p]; t.lyRv += sums.lyRv[p];
    if (sums.ty[p] > 0) t.pins++;
    for (let k = 0; k < NK; k++) { t.tyK[k] += sums.tyK[p * NK + k]; t.lyK[k] += sums.lyK[p * NK + k]; }
  }
  return t;
}
// mix shares from a code vector: by channel, fresh share, ECS share
function mixOf(K) {
  const ch = [0, 0, 0, 0]; let fresh = 0, ecs = 0, all = 0;
  for (let k = 0; k < NK; k++) { const x = K[k]; ch[k >> 2] += x; if (k & 2) fresh += x; if (k & 1) ecs += x; all += x; }
  return { ch, fresh, ecs, all };
}

// rows of every pincode, grouped: by state, and by state + branch
const ROWS_BY_STATE = STATES.map(() => []);
const ROWS_BY_SB = new Map();           // 'state|branch' -> rows
for (let p = 0; p < NP; p++) {
  ROWS_BY_STATE[COLS.st[p]].push(p);
  const key = COLS.st[p] + '|' + COLS.br[p];
  if (!ROWS_BY_SB.has(key)) ROWS_BY_SB.set(key, []);
  ROWS_BY_SB.get(key).push(p);
}
const ALL_ROWS = Array.from({ length: NP }, (_, i) => i);

// monthly series for an area: {ty, ly (same dates), lyR (rest of last year), and the RV versions}, 12 FY months each
function monthly(rows) {
  const s = {}; for (const k in MON) s[k] = new Float64Array(12);
  for (const p of rows) for (let m = 0; m < 12; m++) { const j = p * 12 + m; for (const k in MON) s[k][m] += MON[k][j]; }
  return s;
}

/* ===== unique customers = COUNT(DISTINCT docid). Distinct counts do not add up across days or places, so they are
   counted here from (pincode, day, customer) rows for exactly the dates and area asked for. ===== */
function cstream(s) {
  const o = { n: s.n, r: b64(s.r, Uint16Array), d: b64(s.d, Uint16Array), c: b64(s.c, Uint32Array), a: new Uint32Array(s.n) };
  const ix = b64(s.ai, Uint32Array), av = b64(s.av, Uint32Array);      // sizes ship only for customers of big deals
  for (let i = 0; i < ix.length; i++) o.a[ix[i]] = av[i];
  return o;
}
const CTY = cstream(RAW.custTy), CLY = cstream(RAW.custLy), CRS = cstream(RAW.custRest);
const NCUST = META.nCust;
// distinct customers per key in the period P; keyOf(row) gives the key (0..n-1), or -1 to leave the row out
function custCount(P, keyOf, n) {
  const out = { ty: new Float64Array(n), ly: new Float64Array(n) };
  for (const [S, arr] of [[CTY, out.ty], [CLY, out.ly]]) {
    const seen = new Set();
    for (let i = 0; i < S.n; i++) {
      const o = S.d[i];
      if (o < P.a || o > P.b || S.a[i] > CAP) continue;
      const k = keyOf(S.r[i]);
      if (k < 0) continue;
      const id = k * NCUST + S.c[i];
      if (!seen.has(id)) { seen.add(id); arr[k]++; }
    }
  }
  return out;
}
// distinct customers by FY month for an area (mask over pincode rows): this year, last year same dates, rest of last year
function custMonthly(mask) {
  const r = { ty: new Float64Array(12), ly: new Float64Array(12), lyR: new Float64Array(12) };
  for (const [S, arr, rest] of [[CTY, r.ty, false], [CLY, r.ly, false], [CRS, r.lyR, true]]) {
    const seen = new Set();
    for (let i = 0; i < S.n; i++) {
      if (!mask[S.r[i]] || S.a[i] > CAP) continue;
      const m = rest ? S.d[i] : MONTH_OF[S.d[i]], id = m * NCUST + S.c[i];
      if (!seen.has(id)) { seen.add(id); arr[m]++; }
    }
  }
  return r;
}
function maskOf(rows) { const m = new Uint8Array(NP); for (const p of rows) m[p] = 1; return m; }
