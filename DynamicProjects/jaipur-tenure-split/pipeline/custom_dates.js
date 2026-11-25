// ------------------------------------------------------------------ custom dates (24 Nov 2026, user: a calendar in the period selector)
// Works out any date range from the home branch's day-level building blocks (D.custom), with the same rules as the build's
// window_sums / metrics / leaders_for. Tested: the MTD dates picked as a custom range give the page's own MTD figures.
const CU = D.custom;
const CU0 = Date.UTC(+CU.d0.slice(0, 4), +CU.d0.slice(5, 7) - 1, +CU.d0.slice(8, 10));
const dayN = s => Math.round((Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) - CU0) / 864e5);
const isoOf = n => new Date(CU0 + n * 864e5).toISOString().slice(0, 10);
const ymOf = n => { const s = isoOf(n); return +s.slice(0, 4) * 100 + +s.slice(5, 7); };
const CU_END = dayN(CU.end), CU_MIN = 0;
const CSEGS = D.segs, CNOS = CSEGS.length, CAR = ["Main", "Remote"];
const TME_ROWS_ = new Set(M.hc_t.segs.filter(s => s !== "Branch"));
const PER_MD_ = new Set(["deals_pmd", "rv_pmd", "att_pmd", "made_pmd", "tt", "pres"]);
const UNK_NONE = new Set([...PER_MD_, "hc_t", "hc_b", "hc_j", "hc_m", "md_t", "md_b", "md_j", "md_m"]);
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
function fmtRange(a, b) {
  const A = isoOf(a), B = isoOf(b), f = s => `${+s.slice(8, 10)} ${MON[+s.slice(5, 7) - 1]}`;
  return A.slice(0, 4) === B.slice(0, 4) ? `${f(A)} – ${f(B)} ${B.slice(0, 4)}` : `${f(A)} ${A.slice(0, 4)} – ${f(B)} ${B.slice(0, 4)}`;
}
function cfracs(a, b, lo) {
  const days = CU.wd.filter(d => d >= a && d <= b && (lo == null || d >= lo)), f = {}, g = {}, cnt = {};
  for (const d of days) { const ym = ymOf(d); cnt[ym] = (cnt[ym] || 0) + 1; }
  for (const ym in cnt) { f[ym] = cnt[ym] / (CU.wdm[ym] || cnt[ym]); g[ym] = cnt[ym] / days.length; }
  return { f, g, n: days.length };
}
// segments a base row adds to (the page's derived rows: All Team JDA = JDA, All Team JDS = TME teams, Branch = all deals)
function dealSegs(si) {
  if (si === CNOS) return ["Branch"];
  const s = CSEGS[si];
  if (s === "JDA") return ["JDA", "All Team JDA", "Branch"];
  if (s === "B2B") return ["B2B", "Branch"];
  if (s === "BDE") return ["BDE"];
  return [s, "All Team JDS", "Branch"];
}
function csums(a, b) {
  const S = new Map(), add = (seg, ar, bk, col, v) => {
    const k = seg + "|" + ar + "|" + bk; let o = S.get(k); if (!o) { o = {}; S.set(k, o); } o[col] = (o[col] || 0) + v;
  };
  const cols = CU.x.cols;
  for (const r of CU.x.rows) {
    if (r[0] < a || r[0] > b) continue;
    const ar = CAR[r[2]], bk = BK[r[3]];
    for (const seg of dealSegs(r[1])) for (let i = 0; i < cols.length; i++) if (r[4 + i]) add(seg, ar, bk, cols[i], r[4 + i]);
  }
  const W = cfracs(a, b), WP = cfracs(a, b, CU.pres_from), WT = cfracs(a, b, CU.dial_from);
  for (const r of CU.f.rows) {                                     // person facts: only months with a working day in the range
    if (r[0] < a || r[0] > b || !(W.f[ymOf(r[0])] > 0)) continue;
    const [role, ts] = CU.rs[r[1]], s = CU.suf[role], ar = CAR[r[2]], bk = BK[r[3]];
    CU.rcols[role].forEach((c, i) => { if (r[4 + i]) for (const sg of CU.rolesegs[role]) add(sg === "tseg" ? ts : sg, ar, bk, c + "_" + s, r[4 + i]); });
  }
  for (const r of CU.h.rows) {                                     // HR month rows: mandays pro-rated by working days, headcount weighted
    const f = W.f[r[0]] || 0; if (!(f > 0)) continue;
    const [role, ts] = CU.rs[r[1]], s = CU.suf[role], ar = CAR[r[2]], bk = BK[r[3]];
    const vals = { ["md_" + s]: r[4] * f, ["hc_" + s]: r[5] * (W.g[r[0]] || 0) };
    if (role === "JDA") vals.md_jp = r[4] * (WP.f[r[0]] || 0);
    if ((role === "TME" || role === "B2B") && CU.has_dialer) vals["md_" + s + "t"] = r[4] * (WT.f[r[0]] || 0);
    for (const sg of CU.rolesegs[role]) for (const c in vals) add(sg === "tseg" ? ts : sg, ar, bk, c, vals[c]);
  }
  // area All, then tenure All (as window_sums)
  for (const [k, o] of [...S]) { const [seg, ar, bk] = k.split("|"); for (const c in o) add(seg, "All", bk, c, o[c]); }
  for (const [k, o] of [...S]) { const [seg, ar, bk] = k.split("|"); if (bk === "All") continue; for (const c in o) add(seg, ar, "All", c, o[c]); }
  return { S, wd: W.n };
}
const ratio_ = (x, y) => y > 0 ? x / y : null;
function cmetrics(r, rall, seg, bk) {
  const G = c => r[c] || 0;
  let pm;
  if (TME_ROWS_.has(seg)) pm = [G("cd_t"), G("crv_t"), G("md_t")];
  else if (seg === "B2B") pm = [G("cd_b"), G("crv_b"), G("md_b")];
  else if (seg === "JDA" || seg === "All Team JDA") pm = [G("cd_j"), G("crv_j"), G("md_j")];
  else if (seg === "BDE") pm = [G("cd_m"), G("crv_m"), G("md_m")];
  else pm = [G("cd_t") + G("cd_j") + G("cd_b"), G("crv_t") + G("crv_j") + G("crv_b"), G("md_t") + G("md_j") + G("md_b")];
  if (bk === "All") pm = [G("deals"), G("rv"), pm[2]];
  let att;
  if (TME_ROWS_.has(seg)) att = seg !== "All Team JDS" ? [G("att_t"), G("md_t")] : [G("att_m"), G("md_m")];
  else if (seg === "B2B") att = [G("att_b"), G("md_b")];
  else if (seg === "BDE") att = [G("att_m"), G("md_m")];
  else att = [G("attall_m"), G("md_m")];
  let made, tt;
  if (seg === "B2B") { made = [G("made_b"), G("md_b")]; tt = [G("trunk_b"), G("md_bt")]; }
  else if (seg === "Branch") { made = [G("made_t") + G("made_b"), G("md_t") + G("md_b")]; tt = [G("trunk_t") + G("trunk_b"), G("md_tt") + G("md_bt")]; }
  else { made = [G("made_t"), G("md_t")]; tt = [G("trunk_t"), G("md_tt")]; }
  const dl = G("deals"), rv = G("rv"), ed = G("ed"), er = G("er"), ra = c => rall[c] || 0;
  const v = {
    deals: [dl, dl], contrib_deals: [ratio_(dl, ra("deals")), ra("deals")], rv: [rv / 1e5, dl], contrib_rv: [ratio_(rv, ra("rv")), ra("deals")],
    deals_pmd: [ratio_(pm[0], pm[2]), pm[2]], rv_pmd: [ratio_(pm[1], pm[2]), pm[2]], rv_deal: [ratio_(rv, dl), dl], coll_deal: [ratio_(G("coll"), dl), dl],
    nonecs_rv: [ratio_(rv - er, dl - ed), dl - ed], ecs_rv: [ratio_(er, ed), ed], ecs_pct: [ratio_(ed, dl), dl], nonecs_pct: [ratio_(dl - ed, dl), dl],
    pk_pct: [ratio_(G("pk_d"), dl), dl], pd_pct: [ratio_(G("pd_d"), dl), dl], ot_pct: [ratio_(G("ot_d"), dl), dl],
    pk_rv: [ratio_(G("pk_r"), G("pk_d")), G("pk_d")], pd_rv: [ratio_(G("pd_r"), G("pd_d")), G("pd_d")], ot_rv: [ratio_(G("ot_r"), G("ot_d")), G("ot_d")],
    att_pmd: [ratio_(att[0], att[1]), att[1]], made_pmd: [ratio_(made[0], made[1]), made[1]], cog: [ratio_(G("cogd"), G("appt")), G("appt")],
    tt: [CU.has_dialer ? ratio_(tt[0] / 60, tt[1]) : null, tt[1]], pres: [ratio_(G("pres_j"), G("md_jp")), G("md_jp")], ecs_clear: [null, 0],
    hc_t: [G("hc_t"), G("hc_t")], hc_b: [G("hc_b"), G("hc_b")], hc_j: [G("hc_j"), G("hc_j")], hc_m: [G("hc_m"), G("hc_m")],
    md_t: [G("md_t"), G("md_t")], md_b: [G("md_b"), G("md_b")], md_j: [G("md_j"), G("md_j")], md_m: [G("md_m"), G("md_m")],
  };
  return D.metrics.map(m => {
    if (!m.segs.includes(seg)) return null;
    if (bk === "unknown" && UNK_NONE.has(m.id)) return null;
    const [val, base] = v[m.id];
    return [val == null ? null : Number(val.toPrecision(5)), Math.round(base * 10) / 10];
  });
}
function ccube(a, b) {
  const { S, wd } = csums(a, b), cube = {};
  for (const seg of CSEGS) {
    cube[seg] = {};
    for (const ar of D.areas) {
      const rall = S.get(seg + "|" + ar + "|All") || {};
      cube[seg][ar] = BK.map(bk => cmetrics(S.get(seg + "|" + ar + "|" + bk) || {}, rall, seg, bk));
    }
  }
  return { cube, wd };
}
function cleaders(a, b) {
  const L = CU.lead, W = cfracs(a, b), fs = new Map();
  for (const r of L.facts) if (r[0] >= a && r[0] <= b) { const o = fs.get(r[1]) || [0, 0]; o[0] += r[2]; o[1] += r[3]; fs.set(r[1], o); }
  const out = {}, rnd = (v, d) => Math.round(v * 10 ** d) / 10 ** d;
  L.rows.forEach((r, i) => {
    const f = W.f[r[0]] || 0; if (!(f > 0) || r[1] < 0) return;
    const seg = LEAD_SEGS[r[1]], md = r[4] * f, hc = r[3] ? (W.g[r[0]] || 0) : 0, x = r[3] ? (fs.get(i) || [0, 0]) : [0, 0];
    for (const ar of ["All", CAR[r[2]]]) {
      const A = ((out[seg] = out[seg] || {})[ar] = out[seg][ar] || new Map());
      const mk = r[6] + "|" + r[5], tk = r[8] + "|" + r[7], pk = r[10] + "|" + r[9];
      const m = A.get(mk) || { n: L.names[r[5]], id: r[6], s: [0, 0, 0, 0], t: new Map() }; A.set(mk, m);
      const t = m.t.get(tk) || { n: L.names[r[7]], id: r[8], s: [0, 0, 0, 0], p: new Map() }; m.t.set(tk, t);
      const p = t.p.get(pk) || { n: L.names[r[9]], id: r[10], s: [0, 0, 0, 0] }; t.p.set(pk, p);
      for (const o of [m.s, t.s, p.s]) { o[0] += hc; o[1] += md; o[2] += x[0]; o[3] += x[1]; }
    }
  });
  const res = {};
  for (const seg in out) {
    res[seg] = {};
    for (const ar in out[seg]) {
      res[seg][ar] = [...out[seg][ar].values()].map(m => {
        const tls = [...m.t.values()].sort((u, v) => v.s[2] - u.s[2]).map(t => [t.n, rnd(t.s[0], 1), rnd(t.s[1], 1), rnd(t.s[2], 1), Math.round(t.s[3]),
          [...t.p.values()].sort((u, v) => v.s[2] - u.s[2]).map(p => [p.n, rnd(p.s[0], 2), rnd(p.s[1], 1), rnd(p.s[2], 1), Math.round(p.s[3]), p.id]), t.id]);
        return [m.n, rnd(m.s[0], 1), rnd(m.s[1], 1), rnd(m.s[2], 1), Math.round(m.s[3]), tls, m.id];
      }).sort((u, v) => v[3] - u[3]);
    }
  }
  return res;
}
const lyShift = n => { const s = isoOf(n); const y = +s.slice(0, 4) - 1, md = s.slice(5) === "02-29" ? "02-28" : s.slice(5); return dayN(`${y}-${md}`); };
function setCustom(a, b) {                                         // a, b = day numbers; registers CUSTOM, CUSTOM_ly, CUSTOM_pv
  a = Math.max(CU_MIN, Math.min(a, CU_END)); b = Math.max(a, Math.min(b, CU_END));
  const n = b - a + 1, wins = { CUSTOM: [a, b], CUSTOM_ly: [lyShift(a), lyShift(b)], CUSTOM_pv: [a - n, a - 1] };
  for (const [k, [x, y]] of Object.entries(wins)) {
    if (y < CU_MIN) { delete D.cube[k]; delete D.wins[k]; continue; }
    const { cube, wd } = ccube(Math.max(x, CU_MIN), y);
    D.cube[k] = cube; D.wdays[k] = wd; D.wins[k] = [isoOf(x), isoOf(y), fmtRange(x, y)];
    if (k !== "CUSTOM_ly" && dayN(CU.lead.from) <= x) D.leaders[k] = cleaders(x, y); else delete D.leaders[k];
  }
  D.plabel.CUSTOM = "Custom"; D.pvname.CUSTOM = "Prev.";
  st.cfrom = isoOf(a); st.cto = isoOf(b);
}

// ---------------- the calendar (a pop-up under the Custom button: quick picks, two months, from / to boxes)
const cal = { open: false, a: null, b: null, hover: null, month: null };
function calQuick() {
  const e = CU_END, s = isoOf(e), ym = [+s.slice(0, 4), +s.slice(5, 7)];
  const mStart = dayN(`${ym[0]}-${String(ym[1]).padStart(2, "0")}-01`);
  const pmY = ym[1] === 1 ? ym[0] - 1 : ym[0], pmM = ym[1] === 1 ? 12 : ym[1] - 1, pmStart = dayN(`${pmY}-${String(pmM).padStart(2, "0")}-01`);
  const fyY = ym[1] >= 4 ? ym[0] : ym[0] - 1, q = Math.floor(((ym[1] - 4 + 12) % 12) / 3), qm = (3 + q * 3) % 12 + 1, qy = qm < 4 ? fyY + 1 : fyY;
  const qStart = dayN(`${qy}-${String(qm).padStart(2, "0")}-01`), pqm = ((qm - 4 + 12) % 12) + 1, pqy = pqm > qm ? qy - 1 : qy;
  const pqStart = dayN(`${pqy}-${String(pqm).padStart(2, "0")}-01`);
  return [[`Latest day (${fmtRange(e, e).replace(/ – .*/, "")})`, e, e], ["Last 7 days", e - 6, e], ["Last 30 days", e - 29, e], ["This month", mStart, e],
          ["Last month", pmStart, mStart - 1], ["This quarter", qStart, e], ["Last quarter", pqStart, qStart - 1],
          ["This financial year", dayN(`${fyY}-04-01`), e], ["Last financial year", dayN(`${fyY - 1}-04-01`), dayN(`${fyY}-03-31`)]]
    .map(([l, x, y]) => [l, Math.max(CU_MIN, x), Math.min(CU_END, y)]).filter(([, x, y]) => x <= y);
}
function monthGrid(y, m) {                                         // y, m (1-12) -> html for one month
  const first = dayN(`${y}-${String(m).padStart(2, "0")}-01`), dim = new Date(Date.UTC(y, m, 0)).getUTCDate();
  const lead = (new Date(Date.UTC(y, m - 1, 1)).getUTCDay() + 6) % 7;      // weeks start on Monday
  const a = cal.a, b = cal.b != null ? cal.b : (cal.a != null && cal.hover != null && cal.hover >= cal.a ? cal.hover : null);
  let h = `<div class="cm"><div class="cmh">${MON[m - 1]} ${y}</div><div class="cwk">${["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map(d => `<span>${d}</span>`).join("")}</div><div class="cdays">`;
  for (let i = 0; i < lead; i++) h += `<span></span>`;
  for (let d = 0; d < dim; d++) {
    const n = first + d, off = n < CU_MIN || n > CU_END, inR = a != null && b != null && n >= a && n <= b;
    const cls = ["cd", off ? "off" : "", inR ? "in" : "", n === a ? "st" : "", n === b ? "en" : "", n === CU_END ? "today" : ""].filter(Boolean).join(" ");
    h += off ? `<span class="${cls}">${d + 1}</span>` : `<button type="button" class="${cls}" data-n="${n}" aria-label="${isoOf(n)}">${d + 1}</button>`;
  }
  return h + `</div></div>`;
}
function calHtml() {
  const [y, m] = cal.month, n2 = m === 12 ? [y + 1, 1] : [y, m + 1], p1 = m === 1 ? [y - 1, 12] : [y, m - 1];
  const minM = isoOf(CU_MIN).slice(0, 7), maxM = isoOf(CU_END).slice(0, 7), cur = `${y}-${String(m).padStart(2, "0")}`, nxt = `${n2[0]}-${String(n2[1]).padStart(2, "0")}`;
  const sel = cal.a != null ? (cal.b != null ? fmtRange(cal.a, cal.b) : `${fmtRange(cal.a, cal.a).replace(/ – .*/, "")} – pick the last day`) : "Pick the first day";
  return `<div class="cq">${calQuick().map(([l, x, yy]) => `<button type="button" data-q="${x},${yy}">${l}</button>`).join("")}</div>
    <div class="cr"><div class="cnav"><button type="button" class="cprev" ${cur <= minM ? "disabled" : ""} aria-label="Earlier months">‹</button>
      <span class="csel">${sel}</span><button type="button" class="cnext" ${nxt >= maxM ? "disabled" : ""} aria-label="Later months">›</button></div>
      <div class="cms">${monthGrid(y, m)}${monthGrid(n2[0], n2[1])}</div>
      <div class="cft"><label>From <input type="date" id="cfrom" min="${isoOf(CU_MIN)}" max="${isoOf(CU_END)}" value="${cal.a != null ? isoOf(cal.a) : ""}"></label>
        <label>To <input type="date" id="cto" min="${isoOf(CU_MIN)}" max="${isoOf(CU_END)}" value="${cal.b != null ? isoOf(cal.b) : ""}"></label>
        <span class="cnote">Data from ${fmtRange(CU_MIN, CU_MIN).replace(/ – .*/, "")} ${isoOf(CU_MIN).slice(0, 4)} to ${fmtRange(CU_END, CU_END).replace(/ – .*/, "")} ${isoOf(CU_END).slice(0, 4)}</span>
        <button type="button" class="cbtn ghost" data-act="cancel">Cancel</button><button type="button" class="cbtn" data-act="apply" ${cal.a != null && cal.b != null ? "" : "disabled"}>Apply</button></div></div>`;
}
function calDraw() {
  let pop = document.getElementById("calpop");
  if (!cal.open) { if (pop) pop.hidden = true; return; }
  if (!pop) { pop = document.createElement("div"); pop.id = "calpop"; pop.setAttribute("role", "dialog"); pop.setAttribute("aria-label", "Pick dates"); document.body.appendChild(pop); }
  pop.innerHTML = calHtml(); pop.hidden = false;
  const btn = document.getElementById("custbtn"), r = btn ? btn.getBoundingClientRect() : { left: 20, bottom: 120 };
  pop.style.top = (r.bottom + 6) + "px"; pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pop.offsetWidth - 8)) + "px";
}
function calOpen() {
  cal.open = true;
  cal.a = st.per === "CUSTOM" && st.cfrom ? dayN(st.cfrom) : null; cal.b = st.per === "CUSTOM" && st.cto ? dayN(st.cto) : null; cal.hover = null;
  const s = isoOf(cal.b != null ? cal.b : CU_END); let y = +s.slice(0, 4), m = +s.slice(5, 7) - 1; if (m === 0) { m = 12; y--; }
  cal.month = [y, m]; calDraw();
}
function calApply(a, b) {
  cal.open = false; calDraw();
  setCustom(a, b); st.per = "CUSTOM"; if (st.cmp === "best") st.cmp = "lp"; ov.clear(); render();
}
document.addEventListener("click", e => {
  const pop = document.getElementById("calpop");
  if (e.target.closest("#custbtn")) { cal.open ? (cal.open = false, calDraw()) : calOpen(); return; }
  if (!cal.open || !pop) return;
  if (!e.target.closest("#calpop")) { cal.open = false; calDraw(); return; }
  const q = e.target.closest("[data-q]"), d = e.target.closest("button.cd"), act = e.target.closest("[data-act]");
  if (q) { const [a, b] = q.dataset.q.split(",").map(Number); calApply(a, b); return; }
  if (d) { const n = +d.dataset.n; if (cal.a == null || cal.b != null || n < cal.a) { cal.a = n; cal.b = null; } else cal.b = n; calDraw(); return; }
  if (e.target.closest(".cprev")) { let [y, m] = cal.month; m--; if (!m) { m = 12; y--; } cal.month = [y, m]; calDraw(); return; }
  if (e.target.closest(".cnext")) { let [y, m] = cal.month; m++; if (m > 12) { m = 1; y++; } cal.month = [y, m]; calDraw(); return; }
  if (act && act.dataset.act === "cancel") { cal.open = false; calDraw(); return; }
  if (act && act.dataset.act === "apply" && cal.a != null && cal.b != null) calApply(cal.a, cal.b);
});
document.addEventListener("mouseover", e => {
  if (!cal.open || cal.a == null || cal.b != null) return;
  const d = e.target.closest("#calpop button.cd"); const n = d ? +d.dataset.n : null;
  if (n !== cal.hover) { cal.hover = n; calDraw(); }
});
document.addEventListener("change", e => {
  if (!e.target.matches("#cfrom, #cto")) return;
  const fv = document.getElementById("cfrom").value, tv = document.getElementById("cto").value;
  if (fv) cal.a = Math.max(CU_MIN, Math.min(CU_END, dayN(fv)));
  if (tv) cal.b = Math.max(CU_MIN, Math.min(CU_END, dayN(tv)));
  if (cal.a != null && cal.b != null && cal.b < cal.a) [cal.a, cal.b] = [cal.b, cal.a];
  if (cal.a != null) { const s = isoOf(cal.a); cal.month = [+s.slice(0, 4), +s.slice(5, 7)]; }
  calDraw();
});
document.addEventListener("keydown", e => { if (e.key === "Escape" && cal.open) { cal.open = false; calDraw(); document.getElementById("custbtn")?.focus(); } });
addEventListener("resize", () => { if (cal.open) calDraw(); });
function periodBtns() {                                            // the presets + the Custom button (shows the picked range)
  segBtns("per", D.main.map(p => [p, D.plabel[p]]), st.per === "CUSTOM" ? null : st.per, v => { st.per = v; render(); });
  const el = document.getElementById("per"), b = document.createElement("button");
  b.type = "button"; b.id = "custbtn"; b.className = "cust"; b.setAttribute("aria-pressed", String(st.per === "CUSTOM")); b.setAttribute("aria-haspopup", "dialog");
  b.title = "Pick any dates (a calendar)";
  b.innerHTML = `<svg class="ic" viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/></svg>${st.per === "CUSTOM" ? D.wins.CUSTOM[2] : "Custom dates"}`;
  el.appendChild(b);
}
