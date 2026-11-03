// Rating & Review - fast path of the HTML Drop version (30 Oct 2026).
// Answers the same /api/stats payloads as server.py from pre-computed numbers (rr_cells.bin.gz, build_cells.py):
// per source, (sales group x vertical x subvertical) x rating bin (0.1) x review bin -> docids, paid docids, review sum.
// canAnswer(p) is false for City / State / review limits that cut a review bin / anything the page never sends;
// hybrid.js then uses the full DuckDB-WASM engine (engine.js). Medians above 99 reviews are estimates (median_approx).
const SRC = [['G', 'Google'], ['JD', 'Justdial'], ['OT', 'Others']];
const RATING_BANDS = ['none', 'lt2', '2', '3', '35', '4', '45', 'gt5'];
const RB_N = 52;   // rating bins: 0 = none, 1..50 = 0.1..5.0, 51 = above 5
const rbBand = rb => rb === 0 ? 0 : rb < 20 ? 1 : rb < 30 ? 2 : rb < 35 ? 3 : rb < 40 ? 4 : rb < 45 ? 5 : rb <= 50 ? 6 : 7;
const RBB = Uint8Array.from({ length: RB_N }, (_, i) => rbBand(i));
// review bins come with the data (rr_cells.json): exact 0..99, then ranges of at most ~10%; review band = 0, 1-9, 10-49, 50-99,
// 100-499, 500-999, 1000+
const vbBand = lo => lo === 0 ? 0 : lo <= 9 ? 1 : lo <= 49 ? 2 : lo <= 99 ? 3 : lo <= 499 ? 4 : lo <= 999 ? 5 : 6;
const GROUP_KEYS = { sales_group: 'sg', vertical: 'v', sub_vertical: 'sv' };

let M = null, S = {}, C = {}, nCombo = 0, VB_LO = [], VB_HI = [], VB_N = 0, VBB = null, LO_SET = null, HI_SET = null;

export async function init(base) {
  const [meta, buf] = await Promise.all([
    fetch(base + 'rr_cells.json').then(r => r.json()),
    fetch(base + 'rr_cells.bin.gz').then(r => r.arrayBuffer()).then(gunzip)]);
  M = meta; nCombo = meta.combos.sg.length;
  VB_LO = meta.vb_lo; VB_HI = meta.vb_hi.map(h => h === null ? Infinity : h); VB_N = VB_LO.length;
  VBB = Uint8Array.from(VB_LO, vbBand); LO_SET = new Set(VB_LO); HI_SET = new Set(VB_HI);
  C = { sg: Uint16Array.from(meta.combos.sg), v: Uint16Array.from(meta.combos.v), sv: Uint16Array.from(meta.combos.sv) };
  for (const [code] of SRC) {
    const L = meta.layout[code];
    S[code] = { n: L.n, combo: new Uint16Array(buf, L.combo, L.n), rb: new Uint8Array(buf, L.rb, L.n), vb: new Uint8Array(buf, L.vb, L.n),
                cnt: new Uint32Array(buf, L.cnt, L.n), paid: new Uint32Array(buf, L.paid, L.n), srev: new Uint32Array(buf, L.srev, L.n) };
  }
}
async function gunzip(ab) {   // the host may already have un-gzipped it (Content-Encoding): check the gzip magic bytes
  const b = new Uint8Array(ab, 0, 2);
  if (b[0] !== 0x1f || b[1] !== 0x8b) return ab;
  return new Response(new Blob([ab]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
}

const intOrNull = v => (v === undefined || v === null || v === '') ? null : parseInt(v, 10);
// review limits are exact here only when they fall on review-bin edges (any value up to 100, then e.g. 150, 200, 250, 500, 1000)
const minOK = v => v === null || (v >= 0 && LO_SET.has(v));
const maxOK = v => v === null || (v >= 0 && HI_SET.has(v));

export function canAnswer(p) {
  if (!M) return false;
  if ((p.state || []).length || (p.city_text || []).length) return false;
  for (const k of ['data_city', 'paid_flag', 'mask', 'freeze', 'closedown_flag']) if (p[k] !== undefined && p[k] !== null) return false;
  const focus = SRC.some(s => s[0] === p.focus) ? p.focus : 'ALL';
  const conds = p.conds || [];
  if (!conds.length) return true;
  if (focus === 'ALL' || conds.length > 1) return false;
  const c = conds[0];
  if (c.source !== focus || c.neg) return false;
  const lo = intOrNull(c.rmin), hi = intOrNull(c.rmax);
  if (Number.isNaN(lo) || Number.isNaN(hi)) return false;
  return minOK(lo) && maxOK(hi);
}

// DuckDB MEDIAN = quantile_cont(0.5): average of the two middle values. Bins with one value are exact;
// wider review bins are spread evenly (estimate) and flagged.
function median(hist, from, to, lo, hi) {
  let N = 0; for (let b = from; b <= to; b++) N += hist[b];
  if (!N) return [null, false];
  const pos = 0.5 * (N - 1), k1 = Math.floor(pos), k2 = Math.ceil(pos);
  let approx = false;
  const at = k => {
    let start = 0;
    for (let b = from; b <= to; b++) {
      const c = hist[b];
      if (k < start + c) {
        if (lo[b] === hi[b]) return lo[b];
        approx = true;
        if (!isFinite(hi[b])) return lo[b];
        return lo[b] + (hi[b] - lo[b]) * ((k - start) + 0.5) / c;
      }
      start += c;
    }
    return lo[to];
  };
  const v1 = at(k1), v2 = at(k2);
  return [v1 + (v2 - v1) * (pos - k1), approx];
}
const R_LO = Array.from({ length: RB_N }, (_, i) => i / 10);
// ratings are DECIMAL(3,1): DuckDB's MEDIAN keeps 1 decimal by cutting off (4.25 -> 4.2), so do the same
const medRating = h => { const m = median(h, 1, 50, R_LO, R_LO)[0]; return m == null ? null : Math.floor(m * 10 + 1e-6) / 10; };
const medReviews = h => median(h, 1, VB_N - 1, VB_LO, VB_HI);
function round2(x) {   // Python round(x, 2), same as engine.js
  const k = x * 8;
  if (Number.isInteger(k) && k % 2 !== 0) { const f = Math.floor(x * 100); return (f % 2 === 0 ? f : f + 1) / 100; }
  return Number(x.toFixed(2));
}
const avgOf = (s10, n) => (n ? round2(s10 / (10 * n)) : null);   // same division as engine.js -> same rounding

function comboMask(p) {
  const mask = new Uint8Array(nCombo).fill(1);
  for (const [key, ck] of Object.entries(GROUP_KEYS)) {
    const vals = p[key];
    if (!vals || !vals.length) continue;
    const want = new Set(vals), ok = M.names[key].map(n => want.has(n)), col = C[ck];
    for (let i = 0; i < nCombo; i++) if (!ok[col[i]]) mask[i] = 0;
  }
  return mask;
}

function newAcc() {
  return { docids: 0, rated: 0, reviewed: 0, reviews: 0, an: 0, ad: 0, paid: 0, present: 0,
           rh: new Float64Array(RB_N), vh: new Float64Array(VB_N), rd: new Float64Array(8), vd: new Float64Array(7) };
}
function add(a, rb, vb, cnt, paid, srev) {
  a.docids += cnt; a.paid += paid; a.reviews += srev;
  if (rb > 0) a.rated += cnt;
  if (vb > 0) a.reviewed += cnt;
  if (rb > 0 || vb > 0) a.present += cnt;
  if (rb >= 1 && rb <= 50) { a.an += rb * cnt; a.ad += cnt; }
  a.rh[rb] += cnt; a.vh[vb] += cnt; a.rd[RBB[rb]] += cnt; a.vd[VBB[vb]] += cnt;
}
function srcSummary(code, label, a) {
  const [med, medApprox] = medReviews(a.vh);
  return { code, label, docids: a.present, rated: a.rated, reviewed: a.reviewed, reviews: a.reviews,
           avg: avgOf(a.an, a.ad), median: med, median_approx: medApprox, median_rating: medRating(a.rh) };
}

export function stats(p) {
  const mask = comboMask(p);
  const focus = SRC.some(s => s[0] === p.focus) ? p.focus : 'ALL';
  const by = p.group_by in GROUP_KEYS ? p.group_by : 'sales_group';
  const gcol = C[GROUP_KEYS[by]], gnames = M.names[by];
  const cond = (p.conds || [])[0];
  const rbOK = new Uint8Array(8).fill(1), vbOK = new Uint8Array(VB_N).fill(1);
  if (cond) {
    const bands = (cond.bands || []).filter(b => RATING_BANDS.includes(b));
    rbOK.fill(0); bands.forEach(b => { rbOK[RATING_BANDS.indexOf(b)] = 1; });
    const lo = intOrNull(cond.rmin), hi = intOrNull(cond.rmax);
    for (let b = 0; b < VB_N; b++) if ((lo !== null && VB_LO[b] < lo) || (hi !== null && VB_HI[b] > hi)) vbOK[b] = 0;
  }
  const out = { focus, sources: [], rating_dist: {}, review_dist: {}, sql: null, fast: true };

  if (focus === 'ALL') {
    const groups = new Map();
    const g = gid => { let x = groups.get(gid); if (!x) { x = { docids: 0, paid: 0, s: {} }; groups.set(gid, x); } return x; };
    for (const [code, label] of SRC) {
      const d = S[code], a = newAcc();
      for (let i = 0; i < d.n; i++) {
        const c = d.combo[i]; if (!mask[c]) continue;
        add(a, d.rb[i], d.vb[i], d.cnt[i], d.paid[i], d.srev[i]);
        const gr = g(gcol[c]), gs = gr.s[code] || (gr.s[code] = [0, 0, 0]);
        if (d.rb[i] > 0) gs[0] += d.cnt[i];
        if (d.vb[i] > 0) gs[1] += d.cnt[i];
        gs[2] += d.srev[i];
        if (code === 'JD') { gr.docids += d.cnt[i]; gr.paid += d.paid[i]; }
      }
      out.sources.push(srcSummary(code, label, a));
      out.rating_dist[code] = Array.from(a.rd); out.review_dist[code] = Array.from(a.vd);
      if (code === 'JD') { out.matched = a.docids; out.paid = a.paid; }
    }
    const order = SRC.map(s => s[0]);
    out.groups = { by, all: true, sources: order,
      rows: [...groups].map(([gid, x]) => [gnames[gid], x.docids, x.paid, ...order.flatMap(code => x.s[code] || [0, 0, 0])])
                       .sort((a, b) => b[1] - a[1]) };
    return out;
  }

  // one source: only docids with a rating or reviews in it; rating band / review limit filters apply to it
  const d = S[focus], a = newAcc(), groups = new Map();
  for (let i = 0; i < d.n; i++) {
    const c = d.combo[i]; if (!mask[c]) continue;
    const rb = d.rb[i], vb = d.vb[i];
    if (rb === 0 && vb === 0) continue;
    if (!rbOK[RBB[rb]] || !vbOK[vb]) continue;
    add(a, rb, vb, d.cnt[i], d.paid[i], d.srev[i]);
    let ga = groups.get(gcol[c]); if (!ga) { ga = newAcc(); groups.set(gcol[c], ga); }
    add(ga, rb, vb, d.cnt[i], d.paid[i], d.srev[i]);
  }
  out.matched = a.docids; out.paid = a.paid;
  for (const [code, label] of SRC) {
    if (code === focus) { out.sources.push(srcSummary(code, label, a)); continue; }
    if (cond) { out.sources.push({ code, label, unavailable: true }); continue; }   // needs the docid-level data (full engine)
    const o = S[code], oa = newAcc();          // no rating/review filter: other sources over the same docids
    for (let i = 0; i < o.n; i++) if (mask[o.combo[i]]) add(oa, o.rb[i], o.vb[i], o.cnt[i], o.paid[i], o.srev[i]);
    out.sources.push(srcSummary(code, label, oa));
  }
  out.rating_dist[focus] = Array.from(a.rd); out.review_dist[focus] = Array.from(a.vd);
  // [name, docids, rated, reviewed, avg rating, total reviews, ...8 rating bands, ...7 review bands, paid, median reviews,
  //  median rating, (avg reviews filled by the page), median-reviews-is-estimate]
  out.groups = { by, rows: [...groups].map(([gid, x]) => {
    const [mr, mrApprox] = medReviews(x.vh);
    return [gnames[gid], x.docids, x.rated, x.reviewed, avgOf(x.an, x.ad), x.reviews,
            ...Array.from(x.rd), ...Array.from(x.vd), x.paid, mr, medRating(x.rh), null, mrApprox];
  }).sort((p1, p2) => p2[1] - p1[1]) };
  return out;
}
