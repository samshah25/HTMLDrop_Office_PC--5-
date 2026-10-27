// Rating & Review - browser engine for the static (HTML Drop) version (16 Oct 2026).
// Same SQL as server.py (build_where / stats / groups), run by DuckDB-WASM on rr_data.parquet, so every number matches the
// laptop dashboard. Only difference: each result column is cast to DOUBLE so JavaScript gets plain numbers.
import * as duckdb from './duckdb/duckdb-browser.js';

const BASE = new URL('./', import.meta.url).href;
const T = 'dash';   // rr_data.parquet already holds only the shown rows (in_tam AND sales_group <> 'Unmapped')
const SOURCES = { G: ['Google', 'g_rating', 'g_reviews', ['LG_Ratings', 'LG_Reviews']],
                  JD: ['Justdial', 'jd_rating', 'jd_reviews', ['JD_Ratings', 'JD_Reviews']],
                  OT: ['Others', 'ot_rating', 'ot_reviews', null] };
const SRC = Object.keys(SOURCES);
const FILTERS = ['data_city', 'paid_flag', 'mask', 'freeze', 'closedown_flag', 'state', 'sales_group', 'vertical', 'sub_vertical'];
const PRESENT = new Set(['data_city', 'state', 'sales_group', 'vertical', 'sub_vertical']);   // columns kept in rr_data.parquet
const PICKLIST = new Set(['data_city', 'state', 'sales_group', 'vertical', 'sub_vertical']);
const RATING_BANDS = [['none', '{x} = 0'], ['lt2', '{x} > 0 AND {x} < 2'], ['2', '{x} >= 2 AND {x} < 3'], ['3', '{x} >= 3 AND {x} < 3.5'],
                      ['35', '{x} >= 3.5 AND {x} < 4'], ['4', '{x} >= 4 AND {x} < 4.5'], ['45', '{x} >= 4.5 AND {x} <= 5'], ['gt5', '{x} > 5']];
const REVIEW_BANDS = [['0', '{x} = 0'], ['1', '{x} BETWEEN 1 AND 9'], ['10', '{x} BETWEEN 10 AND 49'], ['50', '{x} BETWEEN 50 AND 99'],
                      ['100', '{x} BETWEEN 100 AND 499'], ['500', '{x} BETWEEN 500 AND 999'], ['1000', '{x} >= 1000']];
const RB = Object.fromEntries(RATING_BANDS);
const fmt = (s, x) => s.split('{x}').join(x);
const GROUP_BY = new Set(['sales_group', 'vertical', 'sub_vertical']);

let conn = null;
export async function init(status = () => {}) {
  status('Starting the data engine...');
  const worker = new Worker(BASE + 'duckdb/duckdb-browser-eh.worker.js');
  const db = new duckdb.AsyncDuckDB(new duckdb.VoidLogger(), worker);
  await db.instantiate(BASE + 'duckdb/duckdb-eh.wasm');
  status('Downloading data (about 40 MB, once)...');
  const buf = new Uint8Array(await (await fetch(BASE + 'rr_data.parquet')).arrayBuffer());
  await db.registerFileBuffer('rr_data.parquet', buf);
  conn = await db.connect();
  status('Preparing data...');
  await conn.query(`CREATE TABLE ${T} AS SELECT * FROM read_parquet('rr_data.parquet')`);
  status('');
}

// run SQL with ? params; every column except `keepFirst` text column comes back as a JS number (or null)
async function q(sql, params = []) {
  const st = await conn.prepare(sql);
  try {
    const t = await st.query(...params);
    const cols = Array.from({ length: t.numCols }, (_, i) => t.getChildAt(i));
    return Array.from({ length: t.numRows }, (_, r) => cols.map(c => { const v = c.get(r); return typeof v === 'bigint' ? Number(v) : v; }));   // get() keeps NULLs
  } finally { await st.close(); }
}
const D = exprs => exprs.map((e, i) => `(${e})::DOUBLE AS c${i}`).join(', ');
const num = v => (v === null || v === undefined) ? null : Number(v);
const int = v => Math.trunc(num(v) || 0);
function round2(x) {   // Python round(x, 2) on the exact binary value: an exact tie (x = odd multiple of 1/8) goes to the even digit
  const k = x * 8;
  if (Number.isInteger(k) && k % 2 !== 0) { const f = Math.floor(x * 100); return (f % 2 === 0 ? f : f + 1) / 100; }
  return Number(x.toFixed(2));
}

function buildWhere(p) {
  const parts = [], params = [];
  for (const col of FILTERS) {
    const vals = p[col];
    if (vals === undefined || vals === null || (PICKLIST.has(col) && !vals.length)) continue;
    if (!PRESENT.has(col)) continue;   // never sent by the page
    if (!vals.length) { parts.push('FALSE'); continue; }
    parts.push(`"${col}" IN (` + vals.map(() => '?').join(',') + ')'); params.push(...vals);
  }
  const cities = (p.city_text || []).map(x => String(x).trim().toLowerCase()).filter(Boolean);
  if (cities.length) { parts.push('lower(rtrim(data_city)) IN (' + cities.map(() => '?').join(',') + ')'); params.push(...cities); }
  const conds = [];
  for (const c of (p.conds || [])) {
    const codes = c.source === '*' ? SRC : [c.source];
    const alts = [];
    for (const code of codes) {
      if (!SOURCES[code]) continue;
      const [, rat, rev] = SOURCES[code];
      const sub = [];
      const bands = (c.bands || []).filter(b => b in RB);
      if (!bands.length) sub.push('FALSE');
      else if (bands.length < RATING_BANDS.length) sub.push('(' + bands.map(b => fmt(RB[b], rat)).join(' OR ') + ')');
      for (const [key, op] of [['rmin', '>='], ['rmax', '<=']]) {
        const v = c[key];
        if (v !== undefined && v !== null && v !== '') { sub.push(`${rev} ${op} ?`); params.push(parseInt(v, 10)); }
      }
      if (!sub.length) sub.push(`(${rat} > 0 OR ${rev} > 0)`);
      alts.push('(' + sub.join(' AND ') + ')');
    }
    if (alts.length) conds.push((c.neg ? 'NOT ' : '') + '(' + alts.join(' OR ') + ')');
  }
  if (conds.length) parts.push('(' + conds.join(p.match === 'any' ? ' OR ' : ' AND ') + ')');
  return [parts.join(' AND ') || 'TRUE', params];
}

// average rating as two exact integers (sum of rating*10, count); JS divides them -> same double as AVG() on the laptop
const avgParts = rat => [`SUM(CASE WHEN ${rat} > 0 AND ${rat} <= 5 THEN (${rat} * 10)::BIGINT END)`, `COUNT(CASE WHEN ${rat} > 0 AND ${rat} <= 5 THEN 1 END)`];
const avgOf = (s10, n) => (n ? s10 / (10 * n) : null);
const medReviews = rev => `MEDIAN(CASE WHEN ${rev} > 0 THEN ${rev} END)`;
const medRating = rat => `MEDIAN(CASE WHEN ${rat} > 0 AND ${rat} <= 5 THEN ${rat} END)`;

export async function stats(p) {
  const [w, params] = buildWhere(p);
  const focus = (p.focus in SOURCES || p.focus === 'ALL') ? p.focus : 'ALL';
  const fp = focus === 'ALL' ? 'TRUE' : `(${SOURCES[focus][1]} > 0 OR ${SOURCES[focus][2]} > 0)`;
  const agg = [`COUNT(*) FILTER (WHERE ${fp})`, `SUM(paid_b2b::INT) FILTER (WHERE ${fp})`];
  for (const code of SRC) {
    const [, rat, rev] = SOURCES[code];
    agg.push(`SUM((${rat} > 0 OR ${rev} > 0)::INT)`, `SUM((${rat} > 0)::INT)`, `SUM((${rev} > 0)::INT)`, `SUM(${rev})::BIGINT`,
             ...avgParts(rat), medReviews(rev), medRating(rat));
  }
  const distSrc = focus === 'ALL' ? SRC : [focus];
  for (const code of distSrc) {
    const [, frat, frev] = SOURCES[code];
    for (const [, s] of RATING_BANDS) agg.push(`SUM((${fmt(s, frat)} AND ${fp})::INT)`);
    for (const [, s] of REVIEW_BANDS) agg.push(`SUM((${fmt(s, frev)} AND ${fp})::INT)`);
  }
  let r = (await q(`SELECT ${D(agg)} FROM ${T} WHERE ${w}`, params))[0];
  const paid = int(r[1]); r = [r[0], ...r.slice(2)];
  const srcs = []; let i = 1;
  for (const code of SRC) {
    const a = avgOf(r[i + 4], r[i + 5]);
    srcs.push({ code, label: SOURCES[code][0], docids: int(r[i]), rated: int(r[i + 1]), reviewed: int(r[i + 2]), reviews: int(r[i + 3]),
                avg: a === null ? null : round2(a), median: num(r[i + 6]), median_rating: num(r[i + 7]) });
    i += 8;
  }
  const nr = RATING_BANDS.length, nv = REVIEW_BANDS.length, rating_dist = {}, review_dist = {};
  for (const code of distSrc) {
    rating_dist[code] = r.slice(i, i + nr).map(int); review_dist[code] = r.slice(i + nr, i + nr + nv).map(int); i += nr + nv;
  }
  return { matched: int(r[0]), paid, sources: srcs, focus, rating_dist, review_dist,
           groups: await groups(p, `(${w}) AND ${fp}`, params, focus), sql: null };
}

async function groups(p, w, params, focus) {
  const col = GROUP_BY.has(p.group_by) ? p.group_by : 'sales_group';
  if (focus === 'ALL') {
    const agg = ['COUNT(*)', 'SUM(paid_b2b::INT)'];
    for (const code of SRC) { const [, rat, rev] = SOURCES[code]; agg.push(`SUM((${rat} > 0)::INT)`, `SUM((${rev} > 0)::INT)`, `SUM(${rev})::BIGINT`); }
    const rows = await q(`SELECT "${col}", ${D(agg)} FROM ${T} WHERE ${w} GROUP BY 1 ORDER BY 2 DESC`, params);
    return { by: col, all: true, sources: SRC, rows: rows.map(([g, ...x]) => [g, ...x.map(int)]) };
  }
  const [, rat, rev] = SOURCES[focus];
  const agg = ['COUNT(*)', `SUM((${rat} > 0)::INT)`, `SUM((${rev} > 0)::INT)`, ...avgParts(rat), `SUM(${rev})::BIGINT`];
  for (const [, s] of RATING_BANDS) agg.push(`SUM((${fmt(s, rat)})::INT)`);
  for (const [, s] of REVIEW_BANDS) agg.push(`SUM((${fmt(s, rev)})::INT)`);
  agg.push('SUM(paid_b2b::INT)', medReviews(rev), medRating(rat));
  const rows = await q(`SELECT "${col}", ${D(agg)} FROM ${T} WHERE ${w} GROUP BY 1 ORDER BY 2 DESC`, params);
  return { by: col, rows: rows.map(([g, ...x]) => { const a = avgOf(x[3], x[4]);
    return [g, ...x.slice(0, 3).map(int), a === null ? null : round2(a), ...x.slice(5, -2).map(int), num(x[x.length - 2]), num(x[x.length - 1])]; }) };
}
