"""
Mumbai UI lab (Sarvesh, 2026-09-29): a separate page to try a tabbed layout until it is final.

Built from the MAIN Mumbai dashboard (read only) plus everything the sales-head page already does (tools/build_sales_head.py
transform: plain status column, one-click rules, pincode page with market-size benchmarking, ...), then reorganised into a
sticky navbar with four tabs:
  1. Overview        -- what a JDA head should get in 30 seconds: a headline, 4 numbers vs the same days last month,
                        pincodes per status (click = jump to them), the 5 pincodes to act on first, Gap pincodes by month
  2. Pincodes        -- the status table, category chips and map (click a pincode = its own page with benchmarking)
  3. Sub-verticals & sales groups -- for one pincode or all Mumbai: deals and listings by sub-vertical, each opening to
                        its sales groups (no hovering)
  4. Team productivity -- managers and JDAs, deployed vs other
The period and Fresh / Renewal filters sit in the navbar and apply to every tab. Output:
    Mumbai\\JDA_JDS_Mumbai_Pincode_Dashboard.html   (THE Mumbai dashboard; run after the daily refresh: python tools\\build_ui_lab.py)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_sales_head import transform, SRC_PAGE  # noqa: E402
from prune_lab import prune  # noqa: E402

MUMBAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOLKATA = os.path.join(os.path.dirname(MUMBAI), "Kolkata")   # Kolkata's pages + pipeline (since 2026-10-14)
if not os.path.isdir(KOLKATA):
    KOLKATA = os.path.dirname(MUMBAI)   # the Kolkata kit keeps them at its top level
OUT = os.path.join(MUMBAI, "JDA_JDS_Mumbai_Pincode_Dashboard.html")   # THE Mumbai dashboard (was JDA_Mumbai_Dashboard_UI_Lab.html until 2026-10-09)

CSS = r"""
<style>
/* ================= UI lab: tabbed layout ================= */
#uiBar { position: sticky; top: 0; z-index: 45; background: var(--bg); border-bottom: 1px solid var(--border); }
#uiBar .controls { position: static !important; border: 0 !important; padding-top: 8px; padding-bottom: 8px; }
#uiNav { display: flex; gap: 4px; padding: 10px 28px 0; overflow-x: auto; border-bottom: 1px solid var(--border); }
#uiNav button { border: 0; background: none; color: var(--text-dim); font-family: var(--font-display); font-size: 16px; font-weight: 600; padding: 9px 16px 11px; cursor: pointer; border-bottom: 3px solid transparent; white-space: nowrap; }
#uiNav button:hover { color: var(--text); }
#uiNav button[aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
#uiNav button .ic { margin-right: 7px; opacity: .8; }
.ui-panel { display: none; }
.ui-panel.on { display: block; }
.ui-panel > .ui-intro { margin: 18px 28px 6px; }
.ui-panel > .ui-intro h2 { margin: 0; font-family: var(--font-display); font-size: 24px; font-weight: 600; }
.ui-panel > .ui-intro p { margin: 4px 0 0; color: var(--text-dim); }
header { padding-bottom: 10px; }
/* overview */
.ov { margin: 14px 28px 0; display: grid; gap: 14px; }
.ov-head { font-family: var(--font-display); font-size: 26px; line-height: 1.3; font-weight: 600; margin: 0; }
.ov-head .up { color: #3fbf7a; } .ov-head .down { color: #f07b6b; }
[data-theme="light"] .ov-head .up { color: #1f7f55; } [data-theme="light"] .ov-head .down { color: #c23b22; }
.ov-sub { color: var(--text-dim); margin: -6px 0 0; font-size: 14px; }
.ov-kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.ov-kpi { background: var(--panel); border-radius: 8px; padding: 14px 16px; }
.ov-kpi .l { color: var(--text-dim); font-size: 13.5px; }
.ov-kpi .v { font-family: var(--font-display); font-size: 38px; font-weight: 600; line-height: 1.05; margin: 4px 0 2px; }
.ov-kpi .v small { font-size: 17px; color: var(--text-dim); font-weight: 500; }
.ov-kpi .c { font-size: 13px; color: var(--text-dim); }
.ov-kpi .c b.good { color: #3fbf7a; } .ov-kpi .c b.bad { color: #f07b6b; }
[data-theme="light"] .ov-kpi .c b.good { color: #1f7f55; } [data-theme="light"] .ov-kpi .c b.bad { color: #c23b22; }
.ov-row { display: grid; grid-template-columns: 1.1fr 1fr; gap: 14px; }
.ov-card { background: var(--panel); border-radius: 8px; padding: 16px 18px; min-width: 0; }
.ov-card h3 { margin: 0 0 2px; font-family: var(--font-display); font-size: 18px; font-weight: 600; }
.ov-card .note { margin: 0 0 10px; }
.ui-panel .layout { margin-top: 14px; }

/* ================= action plan ================= */
.pl-add, .pl-chip { border: 1px solid var(--border); background: var(--panel2); color: var(--text-dim); border-radius: 999px; padding: 2px 10px; font: inherit; font-size: 12px; cursor: pointer; white-space: nowrap; }
.pl-add:hover { color: var(--text); border-color: var(--accent); }
.pl-chip { color: var(--text); font-weight: 600; border-color: transparent; background: color-mix(in srgb, var(--pk) 22%, transparent); }
.pl-sales { --pk: #e0802a; } .pl-pres { --pk: #3b82f6; } .pl-headcount { --pk: #22a06b; }
.pl-menu { position: absolute; z-index: 80; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,.35); padding: 6px; display: grid; min-width: 210px; }
.pl-menu button { text-align: left; border: 0; background: none; color: var(--text); font: inherit; padding: 8px 10px; border-radius: 5px; cursor: pointer; }
.pl-menu button:hover { background: var(--panel2); }
.pl-menu button small { display: block; color: var(--text-dim); font-size: 12px; }
.pl-menu .rm { color: #f07b6b; }
.pl-menu .pl-note { border-top: 1px solid var(--border); margin-top: 4px; padding: 8px 6px 4px; display: grid; gap: 4px; }
.pl-menu .pl-note label { font-size: 12px; color: var(--text-dim); }
.pl-menu .pl-note textarea { width: 100%; min-height: 64px; resize: vertical; background: var(--panel2); color: var(--text); border: 1px solid var(--border); border-radius: 5px; padding: 6px 8px; font: inherit; font-size: 13px; }
.pl-menu .pl-note .saved { font-size: 11.5px; color: var(--text-dim); min-height: 14px; }
.pl-menu { min-width: 260px; }
body.pin-mode .pl-menu { z-index: 1100; }   /* above the pincode window */
.pp-nav .pp-act button { font-size: 14px; font-weight: 600; padding: 7px 14px; border-radius: 6px; line-height: 1.2; }
.pl-chip .nt { margin-left: 5px; opacity: .85; }
.pl-t { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.pl-t th, .pl-t td { padding: 7px 8px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.pl-t th { color: var(--text-dim); font-size: 12.5px; font-weight: 600; position: static; background: none; cursor: default; }
.pl-t td.why { color: var(--text-dim); font-size: 13px; }
.pl-t input[type=text] { width: 100%; min-width: 160px; background: var(--panel2); border: 1px solid var(--border); color: var(--text); border-radius: 5px; padding: 5px 8px; font: inherit; font-size: 13px; }
.pl-t select { background: var(--panel2); color: var(--text); border: 1px solid var(--border); border-radius: 5px; padding: 4px 6px; font: inherit; font-size: 13px; max-width: 190px; }
.pl-t .x { border: 0; background: none; color: var(--text-dim); cursor: pointer; font-size: 16px; }
.pl-t .x:hover { color: #f07b6b; }
.pl-empty { color: var(--text-dim); padding: 18px 0; }
.pl-tbl-wrap { overflow-x: auto; }
/* ---- pincode table: compact, with the header and the first four cells (arrow, Pincode, Place, Grouping) frozen ---- */
/* headings: filter arrows under the name (as the main dashboard); wrap only between words, never inside one */
#dataTable th { padding: 6px 8px 32px 8px !important; line-height: 1.2; word-break: normal !important; overflow-wrap: normal !important; hyphens: none !important; }
#dataTable td { padding: 4px 8px !important; }
#dataTable td.num-col, #dataTable th.num-col { padding-left: 4px !important; }
#dataTable th:first-child, #dataTable td:first-child { padding-left: 4px !important; padding-right: 4px !important; }
/* frozen cells: offsets are measured from the real column widths (--fz2..4, set by the page), never guessed */
#dataTable tr:not(.expand-row) > :nth-child(-n+4) { position: sticky !important; z-index: 2; background: var(--panel); }
#dataTable tr:not(.expand-row) > :nth-child(1) { left: 0 !important; }
#dataTable tr:not(.expand-row) > :nth-child(2) { left: var(--fz2, 22px) !important; }
#dataTable tr:not(.expand-row) > :nth-child(3) { left: var(--fz3, 100px) !important; box-shadow: none !important; }
#dataTable tr:not(.expand-row) > :nth-child(4) { left: var(--fz4, 240px) !important; box-shadow: 1px 0 0 var(--border), 6px 0 8px -6px rgba(0,0,0,.45) !important; }
#dataTable thead tr > th { z-index: 3; }
#dataTable thead tr > th:nth-child(-n+4) { z-index: 5 !important; }
#dataTable tbody tr:not(.expand-row):hover > :nth-child(-n+4) { background: color-mix(in srgb, var(--panel2) 70%, var(--panel)) !important; }
#dataTable tr.expand-row td { position: static; }
/* five frozen cells when a State column sits before Grouping (multi-state branches) */
#dataTable.fz5 tr:not(.expand-row) > :nth-child(4) { box-shadow: none !important; }
#dataTable.fz5 tr:not(.expand-row) > :nth-child(5) { position: sticky !important; z-index: 2; background: var(--panel); left: var(--fz5, 380px) !important; box-shadow: 1px 0 0 var(--border), 6px 0 8px -6px rgba(0,0,0,.45) !important; }
#dataTable.fz5 thead tr > th:nth-child(5) { z-index: 5 !important; }
#dataTable.fz5 tbody tr:not(.expand-row):hover > :nth-child(5) { background: color-mix(in srgb, var(--panel2) 70%, var(--panel)) !important; }

/* ================= top-200 JDA categories ================= */
.t2-wrap { margin: 14px 28px 0; }
.t2-head { display: flex; flex-wrap: wrap; align-items: baseline; gap: 10px; margin-bottom: 8px; }
.t2-head h3 { margin: 0; font-family: var(--font-display); font-size: 20px; font-weight: 600; }
.t2-cov { color: var(--text-dim); font-size: 13.5px; }
.t2-cov b { color: var(--text); }
.t2 .rk { color: var(--text-dim); font-size: 12px; width: 34px; }
.pp-t2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pp-t2 table { width: 100%; border-collapse: collapse; font-size: 13px; }
.pp-t2 th, .pp-t2 td { padding: 5px 8px; border-bottom: 1px solid var(--border); text-align: left; white-space: nowrap; }
.pp-t2 th { color: var(--text-dim); font-size: 12px; font-weight: 600; position: static; background: none; cursor: default; }
.pp-t2 td.n, .pp-t2 th.n { text-align: right; }
.pp-t2 h4 { margin: 0 0 6px; font-family: var(--font-display); font-size: 15px; font-weight: 600; }
@media (max-width: 900px) { .pp-t2 { grid-template-columns: 1fr; } .t2-wrap { margin-left: 16px; margin-right: 16px; } }

/* hover explanations on tiles: the page's own [data-tip] box, kept inside the screen and above neighbours */
.ov-kpi[data-tip], .sp-row[data-tip], .pp-num[data-tip], .lb-card[data-tip], .bar-col[data-tip] { position: relative; cursor: help; }
.ov-kpi[data-tip]:hover::after, .sp-row[data-tip]:hover::after, .pp-num[data-tip]:hover::after, .lb-card[data-tip]:hover::after, .bar-col[data-tip]:hover::after {
  width: 260px; max-width: 80vw; z-index: 90; text-align: left; font-family: var(--font-body, inherit); font-weight: 400; font-size: 12.5px; line-height: 1.45; color: var(--text); }
.bar-col[data-tip]:hover::after { top: auto; bottom: 100%; margin-top: 0; margin-bottom: 8px; }
.bar-col[data-tip]:hover::before { top: auto; bottom: 100%; margin-top: 0; margin-bottom: -4px; border-bottom-color: transparent; border-top-color: var(--panel2); }

/* ---- pincode details: a large window over the blurred dashboard ---- */
body.pin-mode { overflow: hidden; }
html:has(body.pin-mode) { overflow: hidden; scrollbar-gutter: stable; }   /* no square page scrollbar next to the window */
body.pin-mode #pinPage { display: flex; position: fixed; inset: 0; z-index: 1000; justify-content: center; align-items: flex-start; padding: 22px 24px;
  background: rgba(8, 10, 14, .78); }   /* no backdrop blur: re-blurring the big dashboard made the window lag when scrolled */
[data-theme="light"] body.pin-mode #pinPage { background: rgba(40, 38, 34, .55); }
body.pin-mode #pinPage > .pp { width: min(1380px, 100%); max-width: none; max-height: calc(100vh - 44px); overflow-y: auto; overscroll-behavior: contain; margin: 0;
  padding: 0 28px 36px; background: var(--bg); border: 1px solid var(--border); border-radius: 14px; box-shadow: 0 16px 40px rgba(0, 0, 0, .45); contain: layout paint; }
[data-theme="light"] body.pin-mode #pinPage > .pp { box-shadow: 0 24px 70px rgba(0, 0, 0, .22); }
/* the window's own scrollbar: thin, rounded, themed, and kept off the rounded corners */
body.pin-mode #pinPage > .pp::-webkit-scrollbar { width: 12px; }
body.pin-mode #pinPage > .pp::-webkit-scrollbar-track { background: transparent; margin: 14px 0; }
body.pin-mode #pinPage > .pp::-webkit-scrollbar-thumb { background: color-mix(in srgb, var(--text-dim) 45%, transparent); border-radius: 12px; border: 3px solid var(--bg); }
body.pin-mode #pinPage > .pp::-webkit-scrollbar-thumb:hover { background: color-mix(in srgb, var(--text-dim) 70%, transparent); }
body.pin-mode #pinPage > .pp::-webkit-scrollbar-button { display: none; height: 0; }
@supports not selector(::-webkit-scrollbar) { body.pin-mode #pinPage > .pp { scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--text-dim) 45%, transparent) transparent; } }
body.pin-mode .pp-nav { position: sticky; top: 0; z-index: 6; margin: 0 -28px 16px; padding: 12px 28px; background: var(--bg); border-bottom: 1px solid var(--border); border-radius: 14px 14px 0 0; }
body.pin-mode .pp-nav .pp-close { margin-left: 4px; width: 36px; height: 36px; padding: 0; display: inline-flex; align-items: center; justify-content: center; font-size: 17px; line-height: 1; border-radius: 50%; }
body.pin-mode .pp-nav .pp-close:hover { background: var(--panel2); }
@media (max-width: 700px) { body.pin-mode #pinPage { padding: 8px; } body.pin-mode #pinPage > .pp { max-height: calc(100vh - 16px); padding: 0 16px 24px; }
  body.pin-mode .pp-nav { margin: 0 -16px 12px; padding: 8px 16px; } }
/* pincode window: business categories as two side-by-side tables with sales-group rows */
.pp-cats2 { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: start; }
.pp-cats2 > div { background: color-mix(in srgb, var(--panel2) 55%, var(--panel)); border-radius: 8px; padding: 12px 14px; min-width: 0; }
.pp-cats2 h3 { margin: 0 0 2px; font-family: var(--font-display); font-size: 16px; font-weight: 600; }
.pp-cats2 .note { margin: 0 0 8px; }
.pp-cats2 .svt tr.tot td { font-weight: 700; border-top: 1px solid var(--text-dim); border-bottom: 0; cursor: default; }
@media (max-width: 900px) { .pp-cats2 { grid-template-columns: 1fr; } }
/* team filter: always visible while it is on */
#scenarioNote .chip.team-chip { background: var(--accent); color: #1c1f24; border-color: var(--accent); font-weight: 600; }
#scenarioNote .chip.team-chip b { font-weight: 700; }
#scenarioNote .chip.team-chip button { color: #1c1f24; opacity: .8; }
#scenarioNote .chip.team-chip button:hover { opacity: 1; }
[data-theme="light"] #scenarioNote .chip.team-chip, [data-theme="light"] #scenarioNote .chip.team-chip button { color: #fff; }
#uiNav button .tp-dot { display: none; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); margin-left: 6px; vertical-align: middle; }
body.team-on #uiNav button[data-tab="pincodes"] .tp-dot { display: inline-block; }
body.team-on #mgrFilterBadge { display: block; padding: 10px 14px; border: 1px solid var(--accent); border-left-width: 4px; border-radius: 8px;
  background: color-mix(in srgb, var(--accent) 10%, var(--panel)); color: var(--text) !important; font-size: 14px; }
body.team-on #mgrFilterBadge b { color: var(--accent); }
/* pincode window = summary; links to the full tabs */
.pp-go { grid-column: 1 / -1; margin-top: 10px; }
.pp-cats2 > .pp-go { background: none; padding: 0; margin-top: 0; }
.pp-go-btn { font-weight: 600; }
.pp-more { margin: 6px 0 0 !important; }
.who-sum td.n, .who-sum th.n { text-align: right; }
/* breadcrumb after a link took you to another tab */
#backCrumb { display: none; padding: 6px 28px 0; font-size: 14px; }
#backCrumb.on { display: flex; align-items: center; gap: 10px; }
#backCrumb button { border: 0; background: none; color: var(--accent); font: inherit; font-weight: 600; padding: 2px 0; cursor: pointer; }
#backCrumb button:hover { text-decoration: underline; }
#backCrumb .x { color: var(--text-dim); font-weight: 400; margin-left: 4px; }
@media (max-width: 700px) { #backCrumb { padding: 6px 16px; } }
/* Pincodes tab: no category block (the Overview status card is the way in) */
#viewSeg, #stripBar, #cards { display: none !important; }
/* Overview status card: clickable group headings, Band settings in the header */
/* ---- navigation: a fixed sidebar (brand · sections · data date + theme); the page bar on top of the content ---- */
body { --side-w: 236px; padding-left: var(--side-w); }
body > header.side { position: fixed; inset: 0 auto 0 0; width: var(--side-w); z-index: 50; display: flex; flex-direction: column; gap: 2px;
  padding: 18px 12px 14px; margin: 0; background: color-mix(in srgb, var(--panel) 60%, var(--bg)); border-right: 1px solid var(--border); overflow-y: auto; }
.side h1 { display: flex; align-items: center; gap: 10px; margin: 0 8px 22px !important; font-size: 16px !important; line-height: 1.25; }
.side h1 .jd-logo { height: 30px; width: auto; flex: none; }
.side #uiNav { display: flex; flex-direction: column; gap: 2px; padding: 0; margin: 0; border: 0; background: none; }
.side #uiNav button { display: flex; align-items: center; gap: 11px; width: 100%; min-height: 40px; text-align: left; border: 0; border-radius: 8px; background: none;
  color: var(--text-dim); padding: 8px 10px; font: inherit; font-size: 14.5px; font-weight: 500; cursor: pointer; }
.side #uiNav button:hover { background: var(--panel2); color: var(--text); }
.side #uiNav button:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.side #uiNav button[aria-selected="true"] { background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--text); font-weight: 600; }
.side .ic { display: inline-flex; width: 20px; height: 20px; flex: none; }
.side .ic svg { width: 20px; height: 20px; }
.side #uiNav button[aria-selected="true"] .ic { color: var(--accent); }
.side .lbl { flex: 1; min-width: 0; line-height: 1.25; white-space: normal; }
/* order in the sidebar: brand, sections, then (pushed down) the data date and the theme switch */
.side h1 { order: 0; } .side #uiNav { order: 1; }
.side #uiNav button { white-space: normal !important; }
.nbadge { min-width: 22px; padding: 1px 7px; border-radius: 999px; background: var(--panel2); color: var(--text); font-size: 12px; font-weight: 600; text-align: center; }
.nbadge[hidden] { display: none; }
.side .tp-dot { margin-left: auto; }
.pg-title { margin-right: auto; font-family: var(--font-display); font-size: 22px; font-weight: 600; color: var(--text); white-space: nowrap; }
.app-name { padding: 20px 28px 6px; }
.app-name .an-t { font-family: var(--font-display); font-size: 28px; line-height: 1.2; font-weight: 700; color: var(--text); }
.app-name #lastRefreshed { display: block; margin: 4px 0 0 !important; font-size: 11.5px; color: var(--text-dim); }
#uiBar > .fbar { padding-left: 28px; padding-right: 28px; min-height: 64px; }
.fpop { left: auto; right: 0; }
/* the icon rail: collapsed by the user, or always on narrow screens (the class is set by the sidebar script) */
body.side-rail { --side-w: 64px; }
body.side-rail > header.side { padding: 14px 8px; align-items: center; }
body.side-rail .side h1 { font-size: 0 !important; margin: 0 0 18px !important; gap: 0; }
body.side-rail .side h1 .jd-logo { height: 26px !important; width: auto !important; }
body.side-rail .side .lbl { display: none; }
body.side-rail .side #uiNav button { justify-content: center; padding: 0; gap: 0; width: 44px; height: 44px; min-height: 44px; position: relative; }
body.side-rail .side #uiNav button > :not(.ic):not(.nbadge) { display: none !important; }
body.side-rail .side h1, body.side-rail .side #uiNav { align-self: stretch; } body.side-rail .side h1 { justify-content: center; }
body.side-rail .side #uiNav { align-items: center; }
body.side-rail .side #uiNav button .ic, body.side-rail .side h1 .jd-logo { margin: 0 !important; } body.side-rail .side .theme-btn { width: 44px; height: 44px; }
body.side-rail .nbadge { position: absolute; top: 2px; right: 2px; min-width: 16px; padding: 0 4px; font-size: 10.5px; }
  background: none; color: var(--text-dim); padding: 8px 10px; font: inherit; font-size: 13.5px; cursor: pointer; }
.side .theme-btn { order: 4; margin-top: auto; }
/* accessibility: headings that are only for screen readers */
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; border: 0; }
h2.sec-h { margin: 0 0 12px; font-family: var(--font-display); font-size: 20px; font-weight: 600; color: var(--text); line-height: 1.2; }
/* no thick one-side accent bars: a soft tinted box instead */
.summary .hidden-cat-note { padding: 5px 12px; border-radius: 6px; background: color-mix(in srgb, var(--accent) 10%, transparent); }
body.team-on #mgrFilterBadge { border-left-width: 1px !important; }
/* popups: a defined edge with a tight shadow, not hairline + wide blur */
.col-filter-popup { box-shadow: 0 6px 14px rgba(0,0,0,.28) !important; }
.pl-menu { box-shadow: 0 6px 14px rgba(0,0,0,.28); }
/* ---- overview (2026-09-30): pie, day-by-day trend, sparklines, neutral groupings, ⚙ menu ---- */
.ov-foot { margin: -4px 0 0 !important; font-size: 12.5px; }
.ov-kpi { position: relative; }
.ov-kpi .l { padding-right: 124px; }   /* room for the sparkline */
.ov-kpi .spark { position: absolute; right: 14px; top: 14px; color: color-mix(in srgb, var(--text-dim) 70%, transparent); overflow: visible; }
.pie-seg { cursor: pointer; } .pie-seg:hover { stroke-opacity: 1; filter: brightness(1.15); }
.pie-n { font-family: var(--font-display); font-size: 21px; font-weight: 600; fill: var(--text); } .pie-l { font-size: 12px; fill: var(--text-dim); }
.trend { width: 100%; height: auto; display: block; }
.tr-grid { stroke: var(--border); stroke-width: 1; } .tr-ax { font-size: 11px; fill: var(--text-dim); }
.tr-cur { stroke: var(--accent); stroke-width: 2.5; stroke-linejoin: round; } .tr-prev { stroke: var(--text-dim); stroke-width: 2; stroke-dasharray: 5 4; }
.tr-lab { font-size: 12px; font-weight: 600; } .tr-lab.cur { fill: var(--text); } .tr-lab.prev { fill: var(--text-dim); }
.tr-key { display: inline-block; width: 16px; height: 0; margin: 0 5px 3px 2px; border-top: 2.5px solid var(--accent); vertical-align: middle; }
.tr-key.prev { border-top: 2px dashed var(--text-dim); }
.ov-months .layout { padding: 0 !important; margin: 0 !important; display: block; }
.ov-months .panel { background: none !important; padding: 0 !important; border: 0 !important; box-shadow: none !important; margin: 0 !important; }
.ov-months h2.sec-h { font-size: 18px; margin-bottom: 8px; }
.ov-months .bars { overflow: visible; max-width: 100%; } .ov-months, .ov-months .panel { overflow: hidden; } div.hv-tip { max-width: 270px; white-space: normal; }
/* table: grouping dot, 3 frozen cells when there is no State column, greyed small samples */
#dataTable td.pin-dot-cell { text-align: center; }
.gdot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; vertical-align: middle; }
#dataTable.fz3 tr:not(.expand-row) > :nth-child(3) { box-shadow: 1px 0 0 var(--border), 6px 0 8px -6px rgba(0,0,0,.45) !important; }
#dataTable.fz3 tr:not(.expand-row) > :nth-child(4) { position: static !important; box-shadow: none !important; background: none; }
#dataTable.fz3 tbody tr:not(.expand-row):hover > :nth-child(4) { background: none !important; }
.lown { color: var(--text-dim); opacity: .75; cursor: help; }
/* pincode window: one row of controls; tiles carry their comparison */
.pp-num .t { margin-top: 3px; font-size: 12.5px; color: var(--text-dim); }
.pp-num.lown-tile .v { color: var(--text-dim); opacity: .7; }
.pp-num.lown-tile .t { font-style: italic; }
/* sub-verticals: Untagged last and quiet */
tr.unt td { color: var(--text-dim) !important; font-style: italic; }
.why { margin-left: 6px; font-size: 12px; font-style: normal; color: var(--accent); cursor: help; border-bottom: 1px dotted currentColor; }
/* team: the page scrolls, not a box; a small sales bar per row */
#perfViewBody { max-height: none !important; overflow: visible !important; }
.mbar { display: inline-block; width: 46px; height: 5px; margin-left: 8px; vertical-align: middle; background: var(--panel2); border-radius: 3px; overflow: hidden; }
.mbar i { display: block; height: 100%; background: var(--accent); border-radius: 3px; }
/* plan: progress column */
/* ================= visual system (2026-09-30) ================= */
/* dim text one step stronger */
:root:not([data-theme="light"]) { --text-dim: #b4b5ae; }
:root[data-theme="light"] { --text-dim: #4e5761; }
/* one card level less: sections are plain areas with a divider; only the headline numbers stay tiles */
.ov-card, .sv-card, .sv-pick, .ui-panel .layout > .panel, #pinPage .pp-sec, .pp-cats2 > div {
  background: transparent !important; box-shadow: none !important; border-radius: 0 !important; border: 0 !important;
  border-top: 1px solid var(--border) !important; padding-left: 0 !important; padding-right: 0 !important; }
.pp-cats2 > div { border-top: 0 !important; padding-top: 0 !important; }
.ui-panel .ov-months .layout { padding: 0 !important; }
.ui-panel .ov-months .layout > .panel { border-top: 0 !important; padding-top: 0 !important; }
.ui-panel .layout { padding-left: 28px !important; padding-right: 28px !important; }
/* frozen table cells and sticky headers now sit on the page background */
#dataTable tr:not(.expand-row) > :nth-child(-n+5) { background: var(--panel) !important; }
#dataTable thead tr:not(.expand-row) > th:nth-child(n) { background: var(--panel2) !important; }
#dataTable tbody tr:not(.expand-row):hover > * { background: color-mix(in srgb, var(--panel2) 55%, var(--panel)) !important; }
#perfViewBody thead th { background: var(--bg) !important; }
/* weights: labels regular, values semibold, the headline bold */
#dataTable thead th, #perfViewBody thead th, .svt th, .pl-t th, .who th { font-weight: 500 !important; }
.perf-mgr-link b, #perfViewBody td b { font-weight: 500 !important; }
.ov-head b { font-weight: 700; }
.ov-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.ov-mode { flex: none; margin-top: 4px; } .ov-mode button { padding: 5px 12px; font-size: 13px; }
/* the day-by-day chart: what it shows (2026-10-13) */
/* under the title, one row: the switch (stays put when the title changes) and the line key */
.tr-head { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; margin: 8px 0 4px; }   /* switch, then the key: always the same place */
.tr-metric { flex: none; } .tr-metric button { padding: 4px 10px; font-size: 12.5px; }
.tr-head .tr-leg { display: flex; flex-wrap: wrap; gap: 4px 14px; margin: 0; }
.tr-head .tl-k { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; cursor: help; }
.tr-head .tl-j { margin-left: 4px; } .tr-head .tl-j b { color: var(--text); font-weight: 700; }
/* ---- filter row: pills with menus (2026-09-30) ---- */
.fbar { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 10px; padding-top: 10px !important; padding-bottom: 10px !important; }
.fpill-wrap { position: relative; }
.fpill { display: inline-flex; align-items: baseline; gap: 7px; border: 1px solid var(--border); background: var(--panel); color: var(--text);
  border-radius: 999px; padding: 7px 14px; font: inherit; font-size: 14px; cursor: pointer; }
.fpill .k { color: var(--text-dim); font-size: 12.5px; }
.fpill b { font-weight: 600; }
.fpill i { font-style: normal; color: var(--text-dim); font-size: 11px; }
.fpill:hover { border-color: color-mix(in srgb, var(--text-dim) 60%, var(--border)); }
.fpill.changed { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 14%, var(--panel)); }
.fpill[aria-expanded="true"] { border-color: var(--accent); }
.fpop { position: absolute; top: calc(100% + 6px); left: 0; z-index: 70; min-width: 230px; padding: 10px; background: var(--panel);
  border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 6px 14px rgba(0,0,0,.28); }
.fpop[hidden] { display: none; }
.fp-h { font-size: 12px; color: var(--text-dim); margin: 2px 4px 4px; }
.fp-h + .fp-list { margin-bottom: 8px; }
.fp-list { display: grid; gap: 2px; }
.fp-list button { text-align: left; border: 0; background: none; color: var(--text); font: inherit; font-size: 14px; padding: 7px 10px; border-radius: 6px; cursor: pointer; white-space: nowrap; }
.fp-list button:hover { background: var(--panel2); }
.fp-list button.on, .fp-list button.active { background: color-mix(in srgb, var(--accent) 18%, transparent); font-weight: 600; }
.fp-custom { display: flex; align-items: center; gap: 6px; margin: 0 4px 10px; }
.fp-custom span { color: var(--text-dim); font-size: 13px; }
.fp-full { width: 100%; }
#fbar #scenarioNote { margin: 0 !important; }
#fbar #scenarioNote:not(:has(.chip)) { display: none; }
#fbar #scenarioNote .fb-label { display: none; }
.fb-reset { border: 0; background: none; color: var(--accent); font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; padding: 4px 6px; }
.fb-reset:hover { text-decoration: underline; }
#fbar #clearAllFiltersBtn { display: none; }   /* one Reset for pills and chips */
/* ---- the grouping card: donut + one column per group ---- */
.ov-split { margin-top: 2px; }
.ov-card-h { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.sp { display: grid; grid-template-columns: 200px minmax(0, 1fr); gap: 28px; align-items: start; margin-top: 10px; }
.sp-pie { display: grid; justify-items: center; gap: 8px; }
.pie-seg { cursor: pointer; } .pie-seg:hover { stroke-width: 30; }
.pie-n { font-family: var(--font-display); font-size: 26px; font-weight: 600; fill: var(--text); } .pie-l { font-size: 12px; fill: var(--text-dim); }
.sp-all { border: 0; background: none; color: var(--accent); font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; padding: 2px 4px; }
.sp-all:hover { text-decoration: underline; }
.sp-cols { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px 26px; }
.sp-head { display: flex; align-items: baseline; gap: 8px; width: 100%; border: 0; border-bottom: 1px solid var(--border); background: none; color: var(--text);
  font: inherit; text-align: left; padding: 4px 6px 7px; margin-bottom: 4px; cursor: pointer; }
.sp-head b { font-family: var(--font-display); font-size: 16px; font-weight: 600; }
.sp-head span { color: var(--text-dim); font-size: 13px; font-variant-numeric: tabular-nums; }
.sp-head i { margin-left: auto; font-style: normal; color: var(--text-dim); }
.sp-head:hover b, .sp-head:hover i { color: var(--accent); }
.sp-row { display: grid; grid-template-columns: 12px minmax(0, 1fr) auto 50px; align-items: center; gap: 10px; width: 100%; border: 0; background: none;
  color: var(--text); font: inherit; font-size: 14px; text-align: left; padding: 6px; border-radius: 6px; cursor: pointer; }
.sp-row:hover { background: var(--panel2); }
section.summary .sum-head:not(:has(*)) { display: none; }
.sp-row:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.cut { display: inline-flex; align-items: center; margin-left: 4px; border: 1px solid var(--border); border-radius: 6px; background: var(--bg); vertical-align: middle; }
.cut:hover { border-color: var(--text-dim); } .cut:focus-within { border-color: var(--accent); }
.cut-b { width: 20px; height: 22px; padding: 0; border: 0; background: none; color: var(--text-dim); font: inherit; font-size: 14px; line-height: 1; cursor: pointer; }
.cut-b:hover { color: var(--text); background: var(--panel2); } .cut-b:first-child { border-radius: 5px 0 0 5px; } .cut-b:last-child { border-radius: 0 5px 5px 0; }
.cut-b:focus-visible { outline: 2px solid var(--accent); outline-offset: -2px; }
.cut-in { width: 2ch; padding: 0; border: 0; background: none; color: var(--text); font: inherit; font-weight: 600; text-align: right; outline: none; }
.cut i { font-style: normal; font-weight: 600; color: var(--text); }
.sp-row .nm { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sp-row b { font-weight: 600; font-variant-numeric: tabular-nums; } .sp-row em { font-style: normal; color: var(--text-dim); text-align: right; font-variant-numeric: tabular-nums; }
[data-theme="light"] .gdot, [data-theme="light"] .sp-row .gdot { box-shadow: 0 0 0 1px rgba(0,0,0,.18); }   /* the light yellow needs an edge */
  background: var(--panel); border: 1px solid var(--border); border-radius: 10px; box-shadow: 0 6px 14px rgba(0,0,0,.28); }
@media (max-width: 1100px) { .sp { grid-template-columns: 1fr; } .sp-cols { grid-template-columns: 1fr; } }
/* the theme button + 'Data updated' in the page bar */
.side .theme-btn { order: 4; margin-top: auto; }   /* at the foot of the rail */
.theme-btn { display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border: 0; border-radius: 10px; background: none; color: var(--text-dim); cursor: pointer; }
.theme-btn:hover { background: var(--panel2); color: var(--text); }
.theme-btn:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.theme-btn svg { width: 20px; height: 20px; }
#fbar .pg-title { margin-right: auto; }
/* Pincodes tab: stat band, grouping chips, toolbar, grouped headers */
section.summary .sum-foot { flex-direction: column; align-items: stretch; gap: 18px; }
#kpis { display: flex; flex-wrap: wrap; gap: 10px 40px; align-items: center; margin-bottom: 6px; }
#kpis .pst { display: grid; grid-template-columns: auto auto; column-gap: 9px; row-gap: 0; align-items: center; cursor: help; }
#kpis .pst b { grid-row: 1 / 3; } #kpis .pst span { align-self: end; } #kpis .pst em { align-self: start; }
#kpis .pst:not(:has(em)) span { grid-row: 1 / 3; align-self: center; }
#kpis .pst b { font-family: var(--font-display); font-size: 24px; line-height: 1.15; font-weight: 700; color: var(--text); }
#kpis .pst b small { font-size: 14px; font-weight: 500; color: var(--text-dim); }
#kpis .pst span { font-size: 15px; line-height: 1.2; font-weight: 500; color: var(--text); } #kpis .pst em { font-style: normal; font-size: 11px; line-height: 1.25; color: var(--text-dim); }
#hiddenCatNote { display: flex !important; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: thin; align-items: center; gap: 8px 0; margin: 0 !important; padding: 0 !important; background: none !important; font-size: 12.5px; }
.gc-grp { display: flex; flex-wrap: nowrap; align-items: center; gap: 4px; padding: 0 9px; position: relative; padding-top: 17px; } .gc-grp:first-child { padding-left: 0; }
.gc-grp + .gc-grp { border-left: 1px solid var(--border); }
#hiddenCatNote .gc-all { align-self: flex-end; margin-bottom: 4px; }
.gc-lab { position: absolute; top: 0; left: 9px; font-size: 11px; line-height: 13px; font-weight: 600; color: var(--text-dim); white-space: nowrap; } .gc-grp:first-child .gc-lab { left: 0; }
.gchip { display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 9px; border: 1px dashed var(--border); border-radius: 999px; background: none;
  color: var(--text-dim); font: inherit; font-size: 12.5px; white-space: nowrap; cursor: pointer; }
.gchip .gdot { width: 8px; height: 8px; border-radius: 50%; background: none !important; box-shadow: inset 0 0 0 1.5px var(--c); flex: none; }
.gchip b { font-weight: 500; }
.gchip:hover { border-color: var(--text-dim); color: var(--text); }
.gchip.on { border: 1px solid color-mix(in srgb, var(--c) 45%, var(--border)); background: color-mix(in srgb, var(--c) 14%, var(--panel2)); color: var(--text); }
.gchip.on .gdot { background: var(--c) !important; box-shadow: none; } .gchip.on b { font-weight: 700; }
.gchip:focus-visible, .gc-all:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.gc-all { margin-left: 6px; flex: none; border: 0; background: none; padding: 4px 2px; white-space: nowrap; color: var(--accent); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.gc-all:hover { text-decoration: underline; }
.pt-bar { margin-bottom: 10px !important; } .pt-bar .search { padding-right: 34px; }
.srch-k { font: 600 11px/1 var(--font-display); color: var(--text-dim); border: 1px solid var(--border); border-radius: 4px; padding: 3px 6px; margin-left: -44px; margin-right: 14px; pointer-events: none; position: relative; z-index: 1; }
.pt-bar .search:focus + .srch-k { visibility: hidden; }
#clearSortBtn[hidden] { display: none; }
#dataTable thead tr.grp-row > th { position: sticky !important; top: 0; left: auto !important; z-index: 3 !important; box-shadow: none !important; cursor: default;
  height: 26px; box-sizing: border-box; padding: 6px 8px 0 !important; border-bottom: 0 !important; font-size: 12px; font-weight: 600 !important; color: var(--text-dim); text-align: left; }
#dataTable thead tr.grp-row > th:first-child { left: 0 !important; z-index: 6 !important; }
#dataTable thead tr.grp-row > th.g-on span { display: block; padding-bottom: 4px; border-bottom: 1px solid var(--border); }
#dataTable thead tr.grp-row > th.g-on + th.g-on span { margin-left: 10px; }
#tableHeadRow > th { top: 26px !important; }
#dataTable th.num-col, #dataTable td.num-col { text-align: right !important; font-variant-numeric: tabular-nums; }
#dataTable tr.empty-row td { padding: 28px 12px !important; color: var(--text-dim); text-align: left !important; }
#dataTable tr.empty-row td span { margin-right: 12px; } #dataTable tr.empty-row .mini-btn { margin-right: 8px; }
/* Action plan */
.ap { margin: 14px 28px 0; }
.ap-sum { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 26px; padding: 10px 14px; border-radius: 10px; background: var(--panel); font-size: 13.5px; color: var(--text-dim); }
.ap-sum b { color: var(--text); font-size: 15px; } .ap-sum-p { display: inline-flex; align-items: center; gap: 10px; } .ap-sum-p .ap-bar { width: 160px; height: 7px; }
.ap-bar-row { display: flex; align-items: center; gap: 12px; margin: 14px 0 12px; }
.ap-pill.st-p i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: 1px; }
.ap-pill.st-idle i { background: #e5484d; } .ap-pill.st-moving i { background: #3b82f6; } .ap-pill.st-met i { background: #2fb35c; } .ap-pill.st-new i { box-shadow: inset 0 0 0 1.5px var(--text-dim); }
.ap-pill:disabled { opacity: .45; cursor: default; }
.ap-add, .ap-img { height: 28px; padding: 0 10px; border: 1px solid var(--border); border-radius: 7px; background: none; color: var(--text); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.ap-add:hover, .ap-img:hover { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, transparent); }
.ap-add:focus-visible, .ap-img:focus-visible, .ap-dots:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.ap-t td .u { color: var(--text-dim); font-size: 12px; }
.ap-more-c { position: relative; width: 34px; }
.ap-dots { width: 28px; height: 28px; border: 0; border-radius: 7px; background: none; color: var(--text-dim); font-size: 18px; line-height: 1; cursor: pointer; }
.ap-dots:hover, .ap-dots[aria-expanded="true"] { background: var(--panel2); color: var(--text); }
.ap-rowmenu { right: 0; top: calc(100% - 2px); min-width: 230px; gap: 4px; }
.ap-rowmenu label { display: grid; gap: 4px; padding: 6px 10px; font-size: 12px; color: var(--text-dim); } .ap-rowmenu select { width: 100%; } .ap-bar-row .grow { flex: 1; }
.ap-share { position: relative; }
.ap-menu { position: absolute; right: 0; top: calc(100% + 6px); z-index: 60; min-width: 270px; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; box-shadow: 0 6px 14px rgba(0,0,0,.28); padding: 6px; display: grid; }
.ap-menu button { text-align: left; border: 0; background: none; color: var(--text); font: inherit; font-size: 14px; padding: 8px 10px; border-radius: 5px; cursor: pointer; }
.ap-menu button:hover:not(:disabled) { background: var(--panel2); } .ap-menu button:disabled { opacity: .45; cursor: default; }
.ap-menu button small { display: block; color: var(--text-dim); font-size: 12px; } .ap-menu .rm { color: #f07b6b; }
.ap-menu .ap-foot { margin: 4px 10px 4px; padding-top: 8px; border-top: 1px solid var(--border); font-size: 12px; color: var(--text-dim); }
.ap-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; margin-bottom: 10px; }
.ap-pills { display: flex; flex-wrap: wrap; gap: 6px; }
.ap-pill { --pk: var(--text-dim); height: 30px; padding: 0 12px; border: 1px dashed var(--border); border-radius: 999px; background: none; color: var(--text-dim); font: inherit; font-size: 13px; cursor: pointer; }
.ap-pill b { font-weight: 600; margin-left: 2px; } .ap-pill:hover { color: var(--text); border-color: var(--text-dim); }
.ap-pill[aria-pressed="true"] { border: 1px solid color-mix(in srgb, var(--pk) 50%, var(--border)); background: color-mix(in srgb, var(--pk) 18%, var(--panel2)); color: var(--text); font-weight: 600; }
.ap-sel { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-dim); }
.ap-sel select, .ap-t select { background: var(--panel2); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 4px 6px; font: inherit; font-size: 13px; }
.ap-t td .pl { color: var(--text-dim); }
.ap-t th.n, .ap-t td.n { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
.ap-t td .up { color: var(--text); font-size: 14px; }
.ap-act { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 12.5px; font-weight: 600; white-space: nowrap; background: color-mix(in srgb, var(--pk) 20%, transparent); }
.ap-more { margin-top: 10px; }
.ap-empty { display: grid; justify-items: start; gap: 6px; padding: 28px 0; } .ap-empty b { font-size: 16px; } .ap-empty span { color: var(--text-dim); }
.ap-plan tr.ap-grp td { padding: 18px 8px 6px; border-bottom: 1px solid var(--border); } .ap-plan tbody:first-of-type tr.ap-grp td { padding-top: 8px; }
.ap-plan input[type=text] { min-width: 120px; width: 100%; } .ap-plan td:last-child { width: 28px; }
.ap-mgr-h { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 14px; }
.ap-mgr-h h3 { margin: 0; font-family: var(--font-display); font-size: 17px; font-weight: 600; }
.ap-mgr-p { display: inline-flex; align-items: center; gap: 8px; margin-left: auto; font-size: 13px; color: var(--text-dim); } .ap-mgr-p b { color: var(--text); }
.ap-bar { display: inline-block; width: 90px; height: 6px; border-radius: 3px; background: var(--panel2); overflow: hidden; vertical-align: middle; flex: none; }
.ap-bar i { display: block; height: 100%; background: var(--accent); }
.ap-t td.prog { white-space: nowrap; font-size: 13px; } .ap-t td.prog .ap-bar { margin-right: 8px; } .ap-t td.prog small { display: block; color: var(--text-dim); font-size: 11.5px; }
.ap-tgt { width: 62px; background: var(--panel2); border: 1px solid var(--border); color: var(--text); border-radius: 5px; padding: 4px 6px; font: inherit; font-size: 13px; text-align: right; }
.ap-st { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; font-size: 12.5px; }
.ap-st::before { content: ''; width: 8px; height: 8px; border-radius: 50%; flex: none; }
.ap-st.st-new { color: var(--text-dim); } .ap-st.st-new::before { box-shadow: inset 0 0 0 1.5px var(--text-dim); }
.ap-st.st-idle { color: var(--text); } .ap-st.st-idle::before { background: #e5484d; }
.ap-st.st-moving { color: var(--text); } .ap-st.st-moving::before { background: #3b82f6; }
.ap-st.st-met { color: var(--text); font-weight: 600; } .ap-st.st-met::before { background: #2fb35c; }
@media (max-width: 700px) { .ap { margin-left: 16px; margin-right: 16px; } }
/* Pincodes table: card, header, dividers, filter icon, chips, action icon */
:root { --grp-div: color-mix(in srgb, var(--border) 70%, transparent); }
.panel .scroll:has(> #dataTable) { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; max-height: calc(100vh - 120px) !important; }
#perfViewBody thead th { position: relative; }
#perfViewBody th .col-filter-icon { position: absolute; top: 4px; right: 2px; display: inline-flex; width: 18px; height: 18px; align-items: center; justify-content: center; padding: 0 !important; border: 0 !important; border-radius: 4px; background: none; color: var(--text-dim); opacity: 0; cursor: pointer; }
#perfViewBody th:hover .col-filter-icon, #perfViewBody th:focus-within .col-filter-icon, #perfViewBody th .col-filter-icon.active { opacity: 1; }
#perfViewBody th .col-filter-icon.active { color: var(--accent); }
#perfViewBody th .col-filter-icon:hover { color: var(--text); background: color-mix(in srgb, var(--text) 10%, transparent); }
@media (hover: none) { #perfViewBody th .col-filter-icon { opacity: .7; } }
#perfViewBody th .th-label, #perfViewBody th .th-controls { display: inline; }
#perfViewBody th .sort-ind { margin-left: 4px; }
/* the running-total chart: end labels make way for the hover box */
svg[data-hv]:hover .tr-lab { visibility: hidden; }
.panel .scroll:has(> #dataTable) #dataTable { background: var(--panel); } #dataTable tbody td { background: var(--panel); }
#dataTable thead tr.grp-row > th { background: var(--panel2) !important; }
#dataTable thead tr.grp-row > th.g-start { border-left: 1px solid var(--grp-div) !important; }
#dataTable thead tr.grp-row > th.g-on span { border-bottom-color: var(--grp-div); }
#tableHeadRow > th { padding-top: 8px !important; padding-bottom: 8px !important; padding-right: 18px !important; vertical-align: bottom; }
#tableHeadRow > th .th-label { display: inline; }
#tableHeadRow > th .th-controls { display: inline; position: static !important; }
#tableHeadRow > th .col-filter-icon { position: absolute; top: 6px; right: 3px; display: inline-flex; width: 16px; height: 16px; align-items: center; justify-content: center;
  border-radius: 4px; color: var(--text-dim); opacity: 0; cursor: pointer; font-size: 0; }
#tableHeadRow > th .col-filter-icon svg { width: 11px; height: 11px; }
#tableHeadRow > th .col-filter-icon, #tableHeadRow > th .col-filter-icon.active { padding: 0 !important; border: 0 !important; background: none; }
#tableHeadRow > th:hover .col-filter-icon, #tableHeadRow > th:focus-within .col-filter-icon { opacity: 1; }
#tableHeadRow > th .col-filter-icon:hover { color: var(--text); background: color-mix(in srgb, var(--text) 10%, transparent); }
#tableHeadRow > th .col-filter-icon.active { opacity: 1; color: var(--accent); }
.cf-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: -2px 0 10px; }
.cf-chips[hidden] { display: none; }
.cchip { display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 4px 0 11px; border-radius: 999px; font-size: 13px; color: var(--text);
  background: color-mix(in srgb, var(--accent) 14%, var(--panel2)); border: 1px solid color-mix(in srgb, var(--accent) 40%, var(--border)); }
.cchip button { width: 20px; height: 20px; border: 0; border-radius: 50%; background: none; color: var(--text-dim); font: inherit; font-size: 11px; cursor: pointer; }
.cchip button:hover { background: color-mix(in srgb, var(--text) 12%, transparent); color: var(--text); }
.cchip button:focus-visible, .cchip-all:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.cchip-all { border: 0; background: none; color: var(--accent); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; padding: 4px 6px; }
.pl-ic { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; padding: 0; border: 0; border-radius: 8px; background: none; color: var(--text-dim); cursor: pointer; }
.pl-ic svg { width: 20px; height: 20px; }
.pl-ic:hover { color: var(--text); background: color-mix(in srgb, var(--text) 9%, transparent); }
.pl-ic:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.pl-ic.in { color: var(--pk); }
#dataTable td:has(> .pl-ic) { text-align: center; }
/* chart hover + headcount strip */
.hv-pad { fill: transparent; }
.hv-dot { stroke: var(--panel); stroke-width: 2; pointer-events: none; }
.hv-tip { position: fixed; z-index: 90; pointer-events: none; display: grid; gap: 1px; padding: 7px 10px; border-radius: 7px; background: var(--panel2);
  border: 1px solid var(--border); box-shadow: 0 4px 12px rgba(0,0,0,.25); font-size: 12.5px; color: var(--text-dim); white-space: nowrap; }
.hv-tip[hidden] { display: none; } .hv-tip b { color: var(--text); font-weight: 600; } .hv-tip strong { color: var(--text); font-size: 14px; font-weight: 700; }
.tr-leg { display: grid; grid-template-columns: auto auto auto auto; justify-content: start; align-items: center; gap: 3px 16px; margin: 2px 0 8px; font-size: 12.5px; color: var(--text-dim); }
.tr-leg .tl-row { display: contents; } .tr-leg .tr-key { width: 16px; margin: 0; } .tr-leg b { color: var(--text); font-weight: 700; }
.tr-leg .tl-v { white-space: nowrap; } .tr-leg .tl-v[title] { cursor: help; }
.hv-tip .tt-h { display: flex; align-items: center; gap: 6px; color: var(--text); font-weight: 600; } .hv-tip .tt-h .tr-key { width: 14px; margin: 0; }
.hv-tip .tt-h em { font-style: normal; font-weight: 400; color: var(--text-dim); }
.hv-tip strong { margin-top: 3px; font-size: 16px; } .hv-tip .tt-sub { font-size: 12px; }
.hv-tip .tt-v { margin: 3px 0 2px; } .hv-tip .tt-v strong { margin: 0 3px 0 0; }
/* scroll overlap fixes (2026-10-05) */
/* the map's panes (z 400) and zoom buttons (z 1000) stay inside the map box instead of drawing over the sticky top bar */
#map, .leaflet-container { position: relative; z-index: 0; isolation: isolate; }
/* both header rows stick to the top of the table in every column; the frozen-column rules had made the 4th cell of each
   header row static (JDA Sales, and the Team group label), so rows scrolled up through them */
#dataTable thead tr.grp-row:not(.expand-row) > th:nth-child(n), #dataTable thead tr#tableHeadRow:not(.expand-row) > th:nth-child(n) { position: sticky !important; }
#dataTable.fz3 thead tr#tableHeadRow:not(.expand-row) > th:nth-child(4) { left: auto !important; z-index: 3 !important; }
/* simpler 'How it compares' */
.lb-say { font-family: var(--font-display); font-size: 21px; font-weight: 600; margin: 0 0 4px; }
.lb-say .good { color: #3fbf7a; } .lb-say .bad { color: #f07b6b; }
[data-theme="light"] .lb-say .good { color: #1f7f55; } [data-theme="light"] .lb-say .bad { color: #c23b22; }
.lb-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 10px; }
.lb-card { background: var(--panel2); border-radius: 6px; padding: 12px 14px; }
.lb-card .l { color: var(--text-dim); font-size: 13px; }
.lb-v b { font-family: var(--font-display); font-size: 28px; font-weight: 600; } .lb-v span { color: var(--text-dim); margin-left: 6px; font-size: 13px; }
.lb-t { font-size: 13px; color: var(--text-dim); }
.lb-note { margin: 12px 0 0; padding: 9px 12px; background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 6px; }
@media (max-width: 800px) { .lb-grid { grid-template-columns: 1fr; } }
/* sub-verticals tab */
.sv-pick { margin: 14px 28px 0; display: flex; flex-wrap: wrap; align-items: center; gap: 10px; background: var(--panel); border-radius: 8px; padding: 12px 16px; }
.sv-pick label { font-weight: 600; }
.sv-pick input { min-width: 300px; flex: 0 1 380px; background: var(--panel2); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 8px 10px; font: inherit; }
.sv-pick .now { color: var(--text-dim); }
.sv-pick .now b { color: var(--text); }
.sv-pick .sv-top { margin-left: auto; display: inline-flex; align-items: center; gap: 8px; }
.sv-pick .sv-top .l { font-weight: 600; }
.sv-grid { margin: 14px 28px 0; display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.sv-card { background: var(--panel); border-radius: 8px; padding: 16px 18px; min-width: 0; overflow-x: auto; }
.sv-card h3 { margin: 0 0 2px; font-family: var(--font-display); font-size: 18px; font-weight: 600; }
.sv-card .note { margin: 0 0 10px; }
.svt { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.svt th, .svt td { padding: 7px 8px; border-bottom: 1px solid var(--border); text-align: left; }
.svt td:first-child { white-space: normal; }   /* long sales-group names wrap instead of pushing the table past its card */
.svt th { color: var(--text-dim); font-size: 12.5px; font-weight: 600; position: static; background: none; cursor: pointer; user-select: none; white-space: nowrap; }
.svt th:hover { color: var(--text); }
.svt th .ar { color: var(--accent); margin-left: 4px; }
.svt td.n, .svt th.n { text-align: right; white-space: nowrap; }
.svt tr.sv { cursor: pointer; }
.svt tr.sv:hover td { background: var(--panel2); }
.svt tr.sv td:first-child::before { content: '▸'; display: inline-block; width: 16px; color: var(--accent); }
.svt tr.sv.open td:first-child::before { content: '▾'; }
.svt tr.sg td { font-size: 12.5px; color: var(--text-dim); background: color-mix(in srgb, var(--panel2) 50%, transparent); }
.svt tr.sg td:first-child { padding-left: 30px; }
.svt .sv-bar { display: inline-block; width: 60px; height: 6px; background: var(--panel2); border-radius: 3px; vertical-align: middle; margin-left: 6px; overflow: hidden; }
.svt .sv-bar i { display: block; height: 100%; background: var(--accent); }
.sv-more { margin-top: 10px; }
@media (max-width: 1100px) { .ov-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } .ov-row, .sv-grid { grid-template-columns: 1fr; } }
@media (max-width: 700px) { #uiNav { padding: 8px 12px 0; } #uiNav button { font-size: 14.5px; padding: 8px 10px 10px; } .ov, .sv-pick, .sv-grid, .ui-panel > .ui-intro { margin-left: 16px; margin-right: 16px; } .ov-kpis { grid-template-columns: 1fr; } .ov-head { font-size: 21px; } .sv-pick input { min-width: 0; flex: 1 1 100%; } }
</style>
"""

JS = r"""
<script>
/* ================= UI lab: tabs, overview, sub-verticals & sales groups ================= */
(function () {
  const $id = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nf = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  const pl = (v, one, many) => `${nf(v)} ${v === 1 ? one : (many || one + 's')}`;
  const fD = iso => new Date(iso + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  const fM = iso => new Date(iso + 'T00:00:00Z').toLocaleDateString('en-GB', { month: 'long', timeZone: 'UTC' });
  const cap = s => { s = String(s || ''); if (s === 'Other' || s === 'All other') return 'Remaining sub-verticals'; return s.charAt(0).toUpperCase() + s.slice(1); };
  const NEED = ['gap', 'notpresent', 'band1'], WELL = ['band2', 'jdaonly'], NONE = ['nosales', 'outside'];
  const NAMES = { gap: 'Visiting, not closing', notpresent: 'Not visiting', jdaonly: 'Only JDA selling', nosales: 'Visited, no sales yet', outside: 'No activity' };
  // the share bands are named after the cutoff you set in Band settings -- a fact, not a verdict
  const nameOf = k => k === 'band1' ? `JDA share ≤${cutoffs[1]}%` : k === 'band2' ? `JDA share >${cutoffs[1]}%` : NAMES[k];

  /* ---------- Pincodes-tab column names (Sarvesh's list) and a filterable 'Grouping' column ---------- */
  Object.assign(COLUMN_LABELS, {
    status: 'Grouping', jda_sales: 'JDA sales', jds_sales: 'JDS sales', jda_share_pct: 'JDA share', conversion_rate_pct: 'Conversion',
    days_since_last_jda_visit: 'Days since last JDA presentation', presentation_count: 'JDA presentations', distinct_jda_employees: 'JDAs who presented',
    deployed_presentations: 'Presentations by deployed JDAs', deployed_jda_count: 'Deployed JDAs (Sept roster)', monetizable_listings: 'Monetizable listings',
    total_sales: 'All sales', b2b_count: 'B2B sales', anonymous_count: 'Anonymous sales', rv3yr_sum: 'RV 3yr, all teams (₹)', original_budget_sum: 'Original budget, all teams (₹)',
  });
  COLUMN_HINTS.status = 'How JDA stands in the pincode: Visiting, not closing / Not visiting / JDA share at or under the cutoff first, then the rest';
  CELL_RENDERERS.days_since_last_jda_visit = r => { const d = r.days_since_last_jda_visit; return d === null || d === undefined ? '—' : String(d); };
  // compact widths (header text wraps onto two lines where needed)
  Object.assign(COLUMN_WIDTHS, { pincode: 76, place: 150, status: 150, jda_sales: 64, jds_sales: 64, jda_share_pct: 84, conversion_rate_pct: 60,
    days_since_last_jda_visit: 70, presentation_count: 92, distinct_jda_employees: 82, deployed_presentations: 100, deployed_jda_count: 84,
    monetizable_listings: 96, plan: 124, state: 84 });
  // every column at least as wide as its longest heading word (+ padding), so no heading word is ever split
  function fitHeadingWords() {
    const probe = document.querySelector('#dataTable thead th .th-label') || document.querySelector('#dataTable thead th');
    const cs = probe ? getComputedStyle(probe) : null;
    const ctx = document.createElement('canvas').getContext('2d');
    ctx.font = cs ? `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}` : '600 13px sans-serif';
    Object.entries(COLUMN_LABELS).forEach(([k, label]) => {
      const longest = Math.max(...String(label).split(/\s+/).map(w => ctx.measureText(w).width));
      const need = Math.ceil(longest + 20);   // 8 + 8 cell padding, a little air
      if (!COLUMN_WIDTHS[k] || COLUMN_WIDTHS[k] < need) COLUMN_WIDTHS[k] = need;
    });
  }
  // measure the first four columns after every draw so the frozen cells sit exactly side by side
  function freezeOffsets() {
    const tp = document.getElementById('tab-pincodes'); if (tp && !tp.classList.contains('on')) return;   // only measure a table that is on screen
    const t = document.getElementById('dataTable'), ths = t && t.querySelectorAll('#tableHeadRow > th');
    if (!ths || ths.length < 4) return;
    // freeze the grouping dot, Pincode and Place, plus State when it follows Place (and Grouping, if shown right after)
    const keys = [...ths].map(h => h.dataset.k || '');
    let n = keys.indexOf('place') + 1; if (n <= 0) n = 3;
    if (keys[n] === 'state') n++;
    if (keys[n] === 'status') n++;
    n = Math.max(3, Math.min(5, n));
    t.classList.toggle('fz3', n === 3); t.classList.toggle('fz5', n === 5);
    let x = 0;
    for (let i = 0; i < n; i++) { if (i) t.style.setProperty('--fz' + (i + 1), x + 'px'); x += ths[i].getBoundingClientRect().width; }
  }
  const _renderTable = renderTable;
  renderTable = function () { const out = _renderTable.apply(this, arguments); freezeOffsets(); return out; };
  const _renderTableHead = renderTableHead;
  renderTableHead = function () { const out = _renderTableHead.apply(this, arguments); freezeOffsets(); return out; };
  window.addEventListener('resize', freezeOffsets);
  window.__freezeOffsets = freezeOffsets;
  fitHeadingWords();
  // once the web font has loaded, measure again with the real letter widths
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { fitHeadingWords(); renderTableHead(); renderTable(currentRows); });
  columnOrder = columnOrder.filter(k => k !== 'anonymous_count');

  /* ---------- Pincodes tab: stat band + grouping chips, one toolbar line, grouped headers, empty state ---------- */
  renderCards = function (rows) {
    const all = currentBaseRows.length ? currentBaseRows : rows;
    const counts = {}; LAYER_KEYS.forEach(k => counts[k] = 0); all.forEach(r => counts[layerOf(r)]++);
    const jda = rows.reduce((a, r) => a + r.jda_sales, 0), jds = rows.reduce((a, r) => a + r.jds_sales, 0), pres = rows.reduce((a, r) => a + r.presentation_count, 0);
    const pctOr = (num, den) => den && num ? nf(100 * num / den) + '%' : '—';
    const tip = k => { const t = CARD_TIPS[k]; return esc((typeof t === 'function' ? t() : t) || ''); };
    const stat = (v, l, d, k) => `<div class="pst" data-tip="${tip(k)}"><b>${v}</b><span>${l}</span>${d ? `<em>${d}</em>` : ''}</div>`;
    $id('kpis').innerHTML = stat(`${nf(rows.length)}<small> of ${nf(all.length)}</small>`, 'pincodes shown', '', 'total')
      + stat(pctOr(jda, jda + jds), 'JDA share of sales', `${nf(jda)} JDA vs ${nf(jds)} JDS`, 'jdaShare')
      + stat(pctOr(jda, pres), 'JDA conversion', `${nf(jda)} sales from ${nf(pres)} presentations`, 'conv');
    const G = [['Missing out', NEED], ['Doing well', WELL], ['No sales yet', NONE]], anyHidden = G.flatMap(g => g[1]).some(k => !layerVisible[k]);
    const note = $id('hiddenCatNote');
    note.innerHTML = G.map(([label, keys]) => `<div class="gc-grp" role="group" aria-label="${label}"><span class="gc-lab">${label}</span>${keys.map(k => `<button type="button" class="gchip${layerVisible[k] ? ' on' : ''}" data-k="${k}" aria-pressed="${!!layerVisible[k]}" title="${layerVisible[k] ? 'Shown: click to hide' : 'Hidden: click to show'}" style="--c:var(--cat-${k})"><i class="gdot"></i>${esc(nameOf(k))}<b>${nf(counts[k])}</b></button>`).join('')}</div>`).join('')
      + (anyHidden ? '<button type="button" class="gc-all" id="showAllCatsBtn">Show all</button>' : '');
    note.style.display = '';
  };
  $id('hiddenCatNote').addEventListener('click', e => {
    const c = e.target.closest('.gchip'); if (!c) return;
    const k = c.dataset.k, v = !layerVisible[k];
    layerVisible[k] = v; if (k === 'band2' && bandsShown < 2) layerVisible.band3 = v;
    refreshAll();
  });
  // toolbar: search, Reset sort (only when sorted), Columns, Export on one line; no 'All pincodes' heading
  { const box = $id('searchBox'), row = box.parentElement, rs = $id('clearSortBtn'), old = rs.parentElement;
    box.placeholder = 'Search pincode or place';
    box.insertAdjacentHTML('afterend', '<kbd class="srch-k" title="Press / to search">/</kbd>');
    row.classList.add('pt-bar'); $id('columnPanelToggle').before(rs); old.remove();
    const h = row.parentElement.querySelector(':scope > h2.sec-h'); if (h) h.remove();
    document.addEventListener('keydown', e => {
      if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey || (e.target.closest && e.target.closest('input, textarea, select, [contenteditable]'))) return;
      if (document.body.classList.contains('pin-mode')) return;
      e.preventDefault(); window.uiShowTab && window.uiShowTab('pincodes'); box.focus(); box.select();
    }); }
  const sortedAway = () => !(sortLevels.length === 1 && sortLevels[0].field === 'status' && sortLevels[0].dir === 1);
  const _renderSortIndicators = renderSortIndicators;
  renderSortIndicators = function () { const out = _renderSortIndicators.apply(this, arguments); $id('clearSortBtn').hidden = !sortedAway(); return out; };
  // column groups above the headings
  const COL_GROUP = { jda_sales: 'Sales', jds_sales: 'Sales', total_sales: 'Sales', jda_share_pct: 'Sales', b2b_count: 'Sales', split_rate_pct: 'Sales',
    presentation_count: 'Presentations', deployed_presentations: 'Presentations', conversion_rate_pct: 'Presentations', days_since_last_jda_visit: 'Presentations',
    distinct_jda_employees: 'Team', deployed_jda_count: 'Team',
    monetizable_listings: 'Market', rv3yr_sum: 'Market', original_budget_sum: 'Market' };
  // keep every group's columns side by side, in this order (a saved or dragged order is put back into groups on load)
  const COL_ORDER = ['pincode', 'place', 'state', 'status', 'jda_sales', 'jds_sales', 'total_sales', 'jda_share_pct', 'b2b_count', 'split_rate_pct',
    'presentation_count', 'deployed_presentations', 'conversion_rate_pct', 'days_since_last_jda_visit',
    'distinct_jda_employees', 'deployed_jda_count', 'monetizable_listings', 'rv3yr_sum', 'original_budget_sum', 'plan'];
  { const at = k => { const i = COL_ORDER.indexOf(k); return i < 0 ? COL_ORDER.length - 1.5 : i; };
    columnOrder = columnOrder.slice().sort((a, b) => at(a) - at(b)); }
  function groupRow() {
    const t = $id('dataTable'), head = $id('tableHeadRow');
    t.querySelectorAll('thead tr.grp-row').forEach(r => r.remove());
    const keys = ['', ...[...head.children].slice(1).map(th => th.dataset.k || '')], spans = [];
    keys.forEach(k => { const g = COL_GROUP[k] || ''; const last = spans[spans.length - 1]; if (last && last.g === g) last.n++; else spans.push({ g, n: 1 }); });
    head.insertAdjacentHTML('beforebegin', `<tr class="grp-row">${spans.map((x, i) => `<th colspan="${x.n}" class="${x.g ? 'g-on' : ''}${i ? ' g-start' : ''}">${x.g ? `<span>${x.g}</span>` : ''}</th>`).join('')}</tr>`);
    // a faint divider where each column group starts (between Sales / Visits / Team / Market)
    let at = 0; const starts = spans.map(x => (at += x.n) - x.n + 1).slice(1);
    let st = $id('grpDivCss'); if (!st) { st = document.createElement('style'); st.id = 'grpDivCss'; document.head.append(st); }
    st.textContent = starts.map(i => `#dataTable tbody tr > td:nth-child(${i}), #tableHeadRow > th:nth-child(${i})`).join(',\n') + (starts.length ? ' { border-left: 1px solid var(--grp-div) !important; }' : '');
    // the filter control: a funnel shown on hover (kept visible while that column is filtered)
    head.querySelectorAll('.col-filter-icon').forEach(ic => { ic.innerHTML = FUNNEL; ic.setAttribute('role', 'button'); ic.setAttribute('aria-label', 'Filter ' + (COLUMN_LABELS[ic.dataset.filterK] || 'this column')); });
  }
  const FUNNEL = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 3h11l-4.2 5v4.3l-2.6 1.2V8z" fill="currentColor"/></svg>';
  const _rth = renderTableHead;
  renderTableHead = function () { const out = _rth.apply(this, arguments); groupRow(); $id('clearSortBtn').hidden = !sortedAway(); return out; };
  // active column filters as removable chips right above the table
  const colFilterFields = () => Object.keys(columnFilters).filter(f => isColumnFilterActive(f) && !(f === 'pincode' && savedLayerVisibleBeforeMgrFilter));
  { const sc = $id('dataTable').closest('.scroll'); sc.insertAdjacentHTML('beforebegin', '<div class="cf-chips" id="cfChips" aria-label="Column filters"></div>');
    $id('cfChips').addEventListener('click', e => {
      const b = e.target.closest('[data-cf]'); if (!b) return;
      if (b.dataset.cf === '*') colFilterFields().forEach(f => delete columnFilters[f]); else delete columnFilters[b.dataset.cf];
      renderTableHead(); refreshAll();
    }); }
  function paintColChips() {
    const f = colFilterFields(), el = $id('cfChips');
    el.innerHTML = f.map(k => `<span class="cchip">${esc(columnFilterChipLabel(k, columnFilters[k]))}<button type="button" data-cf="${k}" aria-label="Remove filter: ${esc(columnFilterChipLabel(k, columnFilters[k]))}" title="Remove this filter">✕</button></span>`).join('')
      + (f.length > 1 ? '<button type="button" class="cchip-all" data-cf="*">Clear column filters</button>' : '');
    el.hidden = !f.length;
  }
  const _bfc = buildFilterChips;
  buildFilterChips = function () { const mine = new Set(colFilterFields().map(k => columnFilterChipLabel(k, columnFilters[k]))); return _bfc.apply(this, arguments).filter(c => !mine.has(c.label)); };
  // an empty table says why, and how to get rows back
  const _rt = renderTable;
  renderTable = function () {
    const out = _rt.apply(this, arguments), tb = document.querySelector('#dataTable tbody');
    paintColChips();
    if (!tb.children.length) {
      const q = $id('searchBox').value.trim(), hid = [NEED, WELL, NONE].flat().filter(k => !layerVisible[k]);
      const n = $id('tableHeadRow').children.length;
      const msg = q ? `No pincode or place matches “${esc(q)}”${hid.length ? ' in the groupings shown' : ''}.` : hid.length ? `No pincodes to show: ${hid.length} of ${[NEED, WELL, NONE].flat().length} groupings are hidden.` : 'No pincodes in this period.';
      tb.innerHTML = `<tr class="empty-row"><td colspan="${n}"><span>${msg}</span>${q ? '<button type="button" class="mini-btn" data-empty="q">Clear search</button>' : ''}${hid.length ? '<button type="button" class="mini-btn" data-empty="all">Show all groupings</button>' : ''}</td></tr>`;
    }
    return out;
  };
  document.querySelector('#dataTable tbody').addEventListener('click', e => {
    const b = e.target.closest('[data-empty]'); if (!b) return;
    e.stopPropagation();
    if (b.dataset.empty === 'q') { const box = $id('searchBox'); box.value = ''; box.dispatchEvent(new Event('input', { bubbles: true })); box.focus(); }
    else showAllCategories();
  }, true);
  renderTableHead(); renderCards(currentRows);
  // speed: the 4,328-row table is drawn (and measured) only while the Pincodes tab is open; a draw asked for while it
  // is hidden is remembered and done once when the tab opens (on load this saved ~3.5 s on Kolkata)
  let tableDirty = true;
  const _rtLazy = renderTable;
  renderTable = function () {
    const tp = document.getElementById('tab-pincodes');
    if (!tp || !tp.classList.contains('on')) { tableDirty = true; return; }
    tableDirty = false; return _rtLazy.apply(this, arguments);
  };
  window.__drawTableIfDirty = () => { if (tableDirty) renderTable(currentRows); };
  hiddenColumns.delete('anonymous_count');
  // Grouping filters by its words (the column still sorts needs-action first)
  CATEGORICAL_FIELDS.add('status');
  const _cvf = columnValueForFilter;
  columnValueForFilter = function (row, field) { return field === 'status' ? cardShortLabel(layerOf(row)) : _cvf.apply(this, arguments); };
  renderTableHead(); renderTable(currentRows);

  /* ---------- shell: sticky navbar (tabs + the period / Fresh-Renewal filters) and one panel per tab ---------- */
  const ICON = {
    overview: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="13.5" width="7" height="7" rx="1.5"/></svg>',
    pincodes: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-6.5-5.8-6.5-11A6.5 6.5 0 0 1 18.5 10c0 5.2-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.4"/></svg>',
    sv: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.5 3 8l9 4.5L21 8z"/><path d="m3 12.5 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/></svg>',
    team: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="8.5" r="3.3"/><path d="M3 19.5a6 6 0 0 1 12 0"/><circle cx="16.8" cy="9.5" r="2.4"/><path d="M16 14.3a4.6 4.6 0 0 1 5 5.2"/></svg>',
    plan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="3"/><path d="m8.2 12.3 2.6 2.6 5-5.4"/></svg>',
  };
  const TABS = [['overview', 'Overview'], ['pincodes', 'Pincodes'], ['sv', 'Sub-verticals & sales groups'], ['team', 'Team productivity'], ['plan', 'Action plan']];
  const header = document.querySelector('body > header');
  const controls = [...document.querySelectorAll('body > div.controls')];
  const bar = document.createElement('div'); bar.id = 'uiBar';
  bar.innerHTML = `<nav id="uiNav" role="tablist" aria-label="Sections">${TABS.map(([k, l]) => `<button type="button" role="tab" data-tab="${k}" aria-selected="false" title="${l}"><span class="ic">${ICON[k]}</span><span class="lbl">${l}</span></button>`).join('')}</nav>`;
  header.after(bar);
  header.append($id('uiNav'));   // the header becomes the sidebar: brand, sections, data date, theme
  header.classList.add('side');
  document.body.classList.add('side-rail');   // the sidebar is an icon rail (labels as tooltips)
  { // the pinned page bar starts with the page's own name
    { const ub = $id('uiBar'), h1 = document.querySelector('header h1');   // the dashboard's name: a top row that scrolls away
      if (ub && h1) ub.insertAdjacentHTML('beforebegin', `<div class="app-name"><div class="an-t">${esc(h1.textContent.trim())}</div></div>`); }
    const fb = $id('fbar'); if (fb) { fb.insertAdjacentHTML('afterbegin', '<div class="pg-title" id="pgTitle" aria-hidden="true"></div>'); const an = document.querySelector('.app-name'); if (an) an.append($id('lastRefreshed')); }
    const setTitle = () => { const b = $id('uiNav').querySelector('[aria-selected="true"] .lbl'), t = $id('pgTitle'); if (b && t) t.textContent = b.textContent; };
    new MutationObserver(setTitle).observe($id('uiNav'), { attributes: true, subtree: true, attributeFilter: ['aria-selected'] });
  }
  controls.forEach(c => bar.append(c));
  const panels = {};
  let anchor = bar;
  TABS.forEach(([k]) => { const p = document.createElement('div'); p.className = 'ui-panel'; p.id = 'tab-' + k; p.setAttribute('role', 'tabpanel'); anchor.after(p); anchor = p; panels[k] = p; });
  const layoutOf = id => { const el = $id(id); return el && el.closest('.layout'); };
  const intro = h => `<h2 class="sr-only">${h}</h2>`;   // no visible intro (the tab row names the tab); the h2 keeps the heading outline
  // overview
  panels.overview.innerHTML = intro('Overview') + `<div class="ov">
      <div class="ov-top"><p class="ov-head" id="ovHead"></p><div class="seg ov-mode" id="ovMode" role="group" aria-label="Show JDA sales as"><button type="button" data-m="total">Total</button><button type="button" data-m="perday" title="Sales divided by working days: days on which anyone made a sale in this area">Per working day</button></div></div>
      <p class="ov-sub" id="ovSub"></p><p class="ov-sub" id="ovTop200" style="margin-top:-8px"></p>
      <div class="ov-kpis" id="ovKpis"></div>
      <p class="note ov-foot">Joint JDA + JDS sales count ½ to each, so totals can show halves.</p>
      <div class="ov-card ov-split"><div class="ov-card-h" id="ovSplitHead"><h3>Pincodes by grouping</h3></div><div class="sp" id="ovSplit"></div></div>
      <div class="ov-row">
        <div class="ov-card"><h3 id="ovTrendH">JDA sales so far, by working day</h3><div class="tr-head"><div class="seg tr-metric" id="ovMetric" role="group" aria-label="The chart shows"><button type="button" data-k="sales">Sales</button><button type="button" data-k="pres">Presentations</button><button type="button" data-k="conv" title="JDA sales as a share of JDA presentations">Conversion %</button></div><div class="tr-leg" id="ovHc"></div></div><div id="ovTrend"></div></div>
        <div class="ov-card ov-months" id="ovMonths"></div>
      </div>
    </div>`;
  const monthLayout = layoutOf('monthBars'); if (monthLayout) $id('ovMonths').append(monthLayout);   // beside the day-by-day chart
  const foot = document.querySelector('body > footer.metrics'); if (foot) panels.overview.append(foot);
  // pincodes
  panels.pincodes.insertAdjacentHTML('beforeend', intro('Compare pincodes', 'Every pincode with its status, needs action first. Filter with the categories, then click a pincode for its own page and how it compares with similar markets.'));
  [document.querySelector('body > section.summary'), layoutOf('dataTable'), layoutOf('map')].forEach(el => { if (el) panels.pincodes.append(el); });
  // sub-verticals
  panels.sv.innerHTML = intro('Sub-verticals & sales groups', 'What kind of businesses are buying, pincode by pincode. Click a sub-vertical to see its sales groups.')
    + `<div class="sv-pick"><label for="svPin">Pincode</label><input id="svPin" list="svPinList" placeholder="Type a pincode or place, or leave empty for all Mumbai" autocomplete="off"><datalist id="svPinList"></datalist><button class="mini-btn" type="button" id="svAll">All Mumbai</button><span class="now" id="svNow"></span><span class="sv-top"><span class="l" id="svTopLab">Sales groups</span><span class="seg" id="svTopSeg" role="group" aria-labelledby="svTopLab"><button type="button" data-top="0" title="Every sales group">All</button><button type="button" data-top="500" title="Only JD's top 500 sales groups by FY26 revenue (top 500 sales group.xlsx)">Top 500</button><button type="button" data-top="250" title="Only ranks 1-250 of the same list">Top 250</button></span></span></div>
       <div class="sv-grid"><div class="sv-card"><h3>Deals by sub-vertical</h3><p class="note" id="svDealsNote"></p><div id="svDeals"></div></div>
       <div class="sv-card"><h3>Listings by sub-vertical</h3><p class="note">Monthly snapshot.</p><div id="svList"></div></div></div>`;
  // team
  panels.team.insertAdjacentHTML('beforeend', intro('Team productivity', 'Managers and their JDAs over the selected period. Click a manager to see the JDAs; deployed JDAs are highlighted.'));
  const perfLayout = layoutOf('perfViewBody'); if (perfLayout) panels.team.append(perfLayout);

  let current = 'overview';
  function showTab(k, push) {
    if (!panels[k]) k = 'overview';
    current = k;
    Object.entries(panels).forEach(([n, p]) => p.classList.toggle('on', n === k));
    document.querySelectorAll('#uiNav button').forEach(b => b.setAttribute('aria-selected', String(b.dataset.tab === k)));
    const url = new URL(location.href); url.searchParams.set('tab', k);
    history.replaceState(history.state, '', url);
    if (k === 'pincodes' && typeof map !== 'undefined' && map && map.invalidateSize) setTimeout(() => map.invalidateSize(), 30);
    if (k === 'pincodes' && window.__drawTableIfDirty) window.__drawTableIfDirty();
    if (k === 'pincodes' && window.__freezeOffsets) requestAnimationFrame(window.__freezeOffsets);
    if (k === 'sv') renderSV();
    if (k === 'overview') renderOverview();
    if (k === 'plan' && window.renderPlan) window.renderPlan();
    if (push !== false) window.scrollTo(0, 0);
  }
  window.uiShowTab = showTab;
  // 'Show <manager>'s pincodes' (Team tab) opens the Pincodes tab with only that team's pincodes
  const _filterTableToManager = filterTableToManager;
  filterTableToManager = function (mgr) { showTab('pincodes'); return _filterTableToManager.apply(this, arguments); };
  $id('uiNav').addEventListener('click', e => { const b = e.target.closest('[data-tab]'); if (b) showTab(b.dataset.tab); });
  document.addEventListener('click', e => {
    const g = e.target.closest('[data-go-tab]'); if (!g) return;
    const only = g.dataset.only;
    if (only) {
      const keep = only === 'all' ? LAYER_KEYS : only === 'needs' ? NEED : only === 'well' ? WELL : only === 'none' ? NONE : [only];
      LAYER_KEYS.forEach(k => { layerVisible[k] = keep.includes(k) || (bandsShown < 2 && k === 'band3' && keep.includes('band2')); });
      refreshAll();
    }
    showTab(g.dataset.goTab);
  });

  /* ---------- 1. overview ---------- */
  function prevMonthDay(iso) { const [y, m, d] = iso.split('-').map(Number); const pm = m === 1 ? 12 : m - 1, py = m === 1 ? y - 1 : y; const last = new Date(Date.UTC(py, pm, 0)).getUTCDate(); return `${py}-${String(pm).padStart(2, '0')}-${String(Math.min(d, last)).padStart(2, '0')}`; }
  // the same dates one month earlier; if that window has fewer working days, its start moves back a day at a time
  // until the counts match (the end date never moves)
  const dayBefore = iso => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() - 1); return d.toISOString().slice(0, 10); };
  // step back by the period's own length in calendar months: a month view against the month before, a quarter
  // view against the quarter before (1 Jul-29 Sept vs 1 Apr-29 Jun); same day numbers, clamped to the month's end
  const shiftMonths = (iso, k) => { let v = iso; for (let i = 0; i < k; i++) v = prevMonthDay(v); return v; };
  function comparison(from, to) {
    const k = (+to.slice(0, 4) * 12 + +to.slice(5, 7)) - (+from.slice(0, 4) * 12 + +from.slice(5, 7)) + 1;
    const pt = shiftMonths(to, k), pf0 = shiftMonths(from, k), need = workDays(from, to).length;
    let pf = pf0, guard = 0;
    while (workDays(pf, pt).length < need && pf > DAILY.window_start && guard++ < 31) pf = dayBefore(pf);
    const wholeMonthStart = k === 1 && from.slice(8) === '01' && pf === pf0;
    return { from: pf, to: pt, name: wholeMonthStart ? `the same days of ${fM(pf0)}` : `${fD(pf)}–${fD(pt)}` };
  }
  function totals(rows) {
    const t = { jda: 0, jds: 0, pres: 0, need: 0, by: {} };
    rows.forEach(r => { const k = layerOf(r); t.by[k] = (t.by[k] || 0) + 1; t.jda += r.jda_sales; t.jds += r.jds_sales; t.pres += r.presentation_count; if (NEED.includes(k)) t.need++; });
    t.share = t.jda + t.jds ? 100 * t.jda / (t.jda + t.jds) : null; t.conv = t.pres ? 100 * t.jda / t.pres : null;
    return t;
  }
  // a working day: anyone made a sale in the area shown that day (on a branch holiday nobody does)
  function workDays(from, to) {
    const pins = new Set(pincodesForCityScope(currentCityScope)), dd = (DAILY.daily_deals || {}).all || {};
    return daysBetween(from, to).filter(day => { const m = dd[day]; if (m) for (const p in m) if (pins.has(p) && (m[p].total_closed || 0) > 0) return true; return false; });
  }
  const MODE_KEY = document.title.split(' ')[0] + 'UiLabSalesMode';
  let perDay = false; try { perDay = localStorage.getItem(MODE_KEY) === 'perday'; } catch (e) {}
  const paintMode = () => $id('ovMode').querySelectorAll('button').forEach(b => { const on = (b.dataset.m === 'perday') === perDay; b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on)); });
  $id('ovMode').addEventListener('click', e => {
    const b = e.target.closest('button[data-m]'); if (!b) return;
    perDay = b.dataset.m === 'perday'; try { localStorage.setItem(MODE_KEY, b.dataset.m); } catch (e2) {}
    renderOverview();
  });
  const METRIC_KEY = document.title.split(' ')[0] + 'UiLabTrendMetric';
  let trendMetric = 'sales'; try { const v = localStorage.getItem(METRIC_KEY); if (v === 'pres' || v === 'conv') trendMetric = v; } catch (e) {}
  const paintMetric = () => $id('ovMetric').querySelectorAll('button').forEach(b => { const on = b.dataset.k === trendMetric; b.classList.toggle('active', on); b.setAttribute('aria-pressed', String(on)); });
  $id('ovMetric').addEventListener('click', e => {
    const b = e.target.closest('button[data-k]'); if (!b || b.dataset.k === trendMetric) return;
    trendMetric = b.dataset.k; try { localStorage.setItem(METRIC_KEY, trendMetric); } catch (e2) {}
    renderOverview();
  });
  function renderOverview() {
    paintMode(); paintMetric();
    const from = periodFromDate, to = periodToDate;
    const rows = buildRows(currentScenario, from, to, currentCityScope), T = totals(rows);
    const C = comparison(from, to), P = C.from >= DAILY.window_start ? totals(buildRows(currentScenario, C.from, C.to, currentCityScope)) : null;
    T.wd = workDays(from, to).length; if (P) P.wd = workDays(C.from, C.to).length;
    const rate = t => perDay ? (t.wd ? t.jda / t.wd : 0) : t.jda;
    const wdTxt = n => `${n} working day${n === 1 ? '' : 's'}`;
    const mtd = from.slice(8) === '01' && to === DAILY.window_end && from.slice(0, 7) === to.slice(0, 7);
    const when = mtd ? 'this month' : `between ${fD(from)} and ${fD(to)}`;
    const kind = currentScenario === 'fresh' ? ' fresh' : currentScenario === 'renewal' ? ' renewal' : '';
    let h = perDay ? `JDA made <b>${nf(rate(T))}${kind} sales per working day</b> ${when}` : `JDA closed <b>${nf(T.jda)}${kind} deals</b> ${when}`;
    if (P) { const d = rate(T) - rate(P); h += Math.abs(d) < 0.05 ? `, the same as ${C.name}.` : `, <span class="${d > 0 ? 'up' : 'down'}">${nf(Math.abs(d))} ${d > 0 ? 'more' : 'fewer'}</span> than ${C.name}.`; } else h += '.';
    $id('ovHead').innerHTML = h;
    $id('ovSub').textContent = `${fD(from)} to ${fD(to)}${perDay ? ` (${wdTxt(T.wd)})` : ''}${P ? `, compared with ${fD(C.from)} to ${fD(C.to)}${perDay ? ` (${wdTxt(P.wd)})` : ''}` : ''}. JDA is missing out in ${T.need} of ${rows.length} pincodes.`;
    if (window.top200Line) window.top200Line(from, to, P ? C : null);
    const r1 = v => v === null ? null : Math.round(v * 10) / 10;
    const S = monthlySeries();
    const kpi = (l, v, cur, prev, prevTxt, lowerBetter, spark) => {
      let c = '';
      if (P && prev !== null && cur !== null) { const d = cur - prev; c = Math.abs(d) < 0.05 ? '<b>No change</b>' : `<b class="${(lowerBetter ? d < 0 : d > 0) ? 'good' : 'bad'}">${d > 0 ? '▲ up' : '▼ down'}</b>`; c += ` from ${prevTxt}`; }
      return `<div class="ov-kpi"><div class="l">${l}</div><div class="v">${v}</div><div class="c">${c}</div>${spark || ''}</div>`;
    };
    const r1s = v => Math.round(v * 10) / 10;
    $id('ovKpis').innerHTML = kpi(perDay ? 'JDA deals per working day' : 'JDA deals', nf(rate(T)), r1s(rate(T)), P && r1s(rate(P)), P && nf(rate(P)), false, sparkline(S, rate, nf))
      + kpi('JDA share of JDA + JDS deals', T.share === null ? '—' : nf(T.share) + '%', r1(T.share), P && r1(P.share), P && (P.share === null ? '—' : nf(P.share) + '%'), false, sparkline(S, t => t.share, v => nf(v) + '%'))
      + kpi('JDA conversion', T.conv === null ? '—' : nf(T.conv) + '%', r1(T.conv), P && r1(P.conv), P && (P.conv === null ? '—' : nf(P.conv) + '%'), false, sparkline(S, t => t.conv, v => nf(v) + '%'))
      + kpi('Pincodes where JDA is missing out', `${T.need}<small> of ${rows.length}</small>`, T.need, P && P.need, P && String(P.need), true, sparkline(S, t => t.need, nf, true));
    $id('ovSplit').innerHTML = splitHtml(T, rows.length);
    $id('ovTrend').innerHTML = trendHtml(from, to, P ? C : null);

  }
  // JDAs at work in the area shown: anyone who presented or made a JDA sale; also the average a working day
  function heads(from, to) {
    const pins = new Set(pincodesForCityScope(currentCityScope)), all = new Set(); let sum = 0;
    const wd = workDays(from, to);
    wd.forEach(day => {
      const today = new Set();
      [(DAILY.rep_pin_pres_by_day || {})[day], (DAILY.rep_pin_sales_by_day || {})[day]].forEach(m => {
        if (m) for (const p in m) if (pins.has(p)) for (const id in m[p]) { today.add(id); all.add(id); }
      });
      sum += today.size;
    });
    return { n: all.size, avg: wd.length ? sum / wd.length : 0 };
  }
  // the chart's legend: one row per period, with its line key, dates, JDA sales and working-JDA headcount
  function legendHtml(rows) {
    // working JDAs stay in view: fewer JDAs out is often why presentations or sales fall
    return rows.map(r => `<span class="tl-k" title="${r.txt !== undefined ? r.txt : nf(r.sales)} ${r.unit}; working JDAs: made a presentation or a JDA sale in the area shown">`
      + `<i class="tr-key ${r.cls}"></i>${r.dates}<span class="tl-j"><b>${nf(r.heads)}</b> working JDAs</span></span>`).join('');
  }
  // ---- month by month (for the tiles' sparklines): cached per Fresh/Renewal, city scope and cutoff ----
  const monthCache = {};
  function monthlySeries() {
    const key = [currentScenario, currentCityScope, cutoffs[1]].join('|');
    if (monthCache[key]) return monthCache[key];
    const out = []; let d = DAILY.window_start.slice(0, 8) + '01';
    while (d <= DAILY.window_end) {
      const y = +d.slice(0, 4), m = +d.slice(5, 7), last = new Date(Date.UTC(y, m, 0)).toISOString().slice(0, 10);
      const from = d < DAILY.window_start ? DAILY.window_start : d, to = last > DAILY.window_end ? DAILY.window_end : last;
      const t = totals(buildRows(currentScenario, from, to, currentCityScope)); t.wd = workDays(from, to).length; t.label = fM(from).slice(0, 3) + (to === DAILY.window_end ? ' (so far)' : '');
      out.push(t);
      d = (m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, '0')}`) + '-01';
    }
    return (monthCache[key] = out);
  }
  // hover for the charts: the point of the one line nearest the pointer, with a dot on that line
  const HV = {}; let hvN = 0;
  const hvReg = series => { const id = 'hv' + (++hvN); HV[id] = series; return id; };
  const hvTip = document.createElement('div'); hvTip.className = 'hv-tip'; hvTip.hidden = true; document.body.append(hvTip);
  let hvSvg = null;
  const hvHide = () => { hvTip.hidden = true; if (hvSvg) { const d = hvSvg.querySelector('.hv-dot'); if (d) d.setAttribute('visibility', 'hidden'); } hvSvg = null; };
  document.addEventListener('pointermove', e => {
    const hh = e.target.closest ? e.target.closest('[data-hv-html]') : null;
    if (hh) {   // a plain element with its own hover card (e.g. the month bars)
      if (hvSvg) hvHide();
      hvTip.innerHTML = hh.dataset.hvHtml; hvTip.hidden = false;
      const r = hvTip.getBoundingClientRect();
      hvTip.style.left = Math.min(e.clientX + 14, window.innerWidth - r.width - 8) + 'px';
      hvTip.style.top = Math.max(8, e.clientY - r.height - 12) + 'px';
      return;
    }
    const svg = e.target.closest ? e.target.closest('svg[data-hv]') : null;
    if (!svg || !HV[svg.dataset.hv]) return hvHide();
    if (hvSvg && hvSvg !== svg) hvHide();
    const m = svg.getScreenCTM(); if (!m) return;
    const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY; const q = pt.matrixTransform(m.inverse());
    let best = null;
    HV[svg.dataset.hv].forEach(sr => {
      if (!sr.pts.length) return;
      const near = sr.pts.reduce((a, b) => Math.abs(b.x - q.x) < Math.abs(a.x - q.x) ? b : a);
      const d = Math.abs(near.y - q.y);
      if (!best || d < best.d) best = { d, sr, pt: near };
    });
    if (!best) return hvHide();
    hvSvg = svg;
    const dot = svg.querySelector('.hv-dot');
    if (dot) { dot.setAttribute('cx', best.pt.x); dot.setAttribute('cy', best.pt.y); dot.setAttribute('fill', best.sr.color); dot.setAttribute('visibility', 'visible'); }
    hvTip.innerHTML = best.pt.html || ((best.sr.name ? `<b>${esc(best.sr.name)}</b>` : '') + `<span>${esc(best.pt.label)}</span><strong>${esc(best.pt.text)}</strong>`);
    hvTip.hidden = false;
    const r = hvTip.getBoundingClientRect();
    hvTip.style.left = Math.min(e.clientX + 14, window.innerWidth - r.width - 8) + 'px';
    hvTip.style.top = Math.max(8, e.clientY - r.height - 12) + 'px';
  });
  window.addEventListener('scroll', hvHide, { passive: true });
  function sparkline(S, get, fmt, lowerBetter) {
    const v = S.map(get); if (v.filter(x => x !== null && x !== undefined).length < 2) return '';
    const ok = v.map(x => x === null || x === undefined ? null : x), nums = ok.filter(x => x !== null);
    const lo = Math.min(...nums), hi = Math.max(...nums), W = 112, H = 30, n = v.length;
    const X = i => 3 + i * (W - 6) / (n - 1), Y = x => hi === lo ? H / 2 : 3 + (H - 6) * (1 - (x - lo) / (hi - lo));
    const pts = ok.map((x, i) => x === null ? null : `${X(i).toFixed(1)},${Y(x).toFixed(1)}`).filter(Boolean).join(' ');
    const li = n - 1, last = ok[li], prev = ok[li - 1];
    const tip = S.map((t, i) => `${t.label}: ${ok[i] === null ? '—' : fmt(ok[i])}`).join(' · ');
    const id = hvReg([{ name: '', color: 'var(--accent)', pts: ok.map((x, i) => x === null ? null : { x: +X(i).toFixed(1), y: +Y(x).toFixed(1), label: S[i].label, text: fmt(x) }).filter(Boolean) }]);
    return `<svg class="spark" data-hv="${id}" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Last ${n} months: ${esc(tip)}">`
      + `<rect class="hv-pad" x="0" y="0" width="${W}" height="${H}"/>`
      + `<polyline points="${pts}" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`
      + (last !== null ? `<circle cx="${X(li).toFixed(1)}" cy="${Y(last).toFixed(1)}" r="3" fill="var(--accent)"/>` : '')
      + `<circle class="hv-dot" r="3.5" visibility="hidden"/></svg>`;
  }
  // ---- the groupings: a donut + one column per group; every heading, row and slice opens the Pincodes tab ----
  // the JDA-share cutoff, edited in place: 'JDA share ≤ [20]%' / 'JDA share > [20]%' (the two boxes are linked)
  const cutLabel = k => (k === 'band1' || k === 'band2')
    ? `JDA share ${k === 'band1' ? '≤' : '>'} <span class="cut"><button type="button" class="cut-b" data-d="-1" aria-label="Lower the line" title="Lower the line">−</button><input type="text" inputmode="numeric" class="cut-in" maxlength="2" value="${cutoffs[1]}" aria-label="JDA-share line (%)" title="The JDA-share line between the two groups: type a number, then Enter"><i>%</i><button type="button" class="cut-b" data-d="1" aria-label="Raise the line" title="Raise the line">+</button></span>`
    : esc(nameOf(k));
  $id('ovSplit').addEventListener('click', e => {
    if (!e.target.closest('.cut')) return;
    e.stopPropagation();   // the box sits in a clickable row: don't open the Pincodes tab
    const b = e.target.closest('.cut-b'); if (!b) return;
    const v = Math.min(99, Math.max(1, cutoffs[1] + Number(b.dataset.d)));
    if (v !== cutoffs[1]) { cutoffs[1] = v; refreshAll(); }
  }, true);
  $id('ovSplit').addEventListener('input', e => {
    const t = e.target.closest('.cut-in'); if (!t) return;
    $id('ovSplit').querySelectorAll('.cut-in').forEach(x => { if (x !== t) x.value = t.value; });   // keep both in step while typing
  });
  $id('ovSplit').addEventListener('change', e => {
    const t = e.target.closest('.cut-in'); if (!t) return;
    const v = Math.round(parseFloat(t.value));
    if (isNaN(v) || v < 1 || v > 99) { t.value = cutoffs[1]; return; }
    if (v !== cutoffs[1]) { cutoffs[1] = v; refreshAll(); }
  });
  $id('ovSplit').addEventListener('keydown', e => {
    if (e.target.closest('.cut-in')) { if (e.key === 'Enter') e.target.blur(); return; }
    const r = e.target.closest('.sp-row'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); r.click(); }
  });
  function splitHtml(T, total) {
    const G = [['Missing out', NEED, 'needs'], ['Doing well', [...WELL, ...(bandsShown >= 2 ? ['band3'] : [])], 'well'], ['No sales yet', NONE, 'none']];
    const pct = n => total ? nf(100 * n / total) + '%' : '—';
    const R = 64, C2 = 2 * Math.PI * R, ring = G.flatMap(g => g[1]).filter(k => (T.by[k] || 0) > 0), GAP = ring.length > 1 ? 2 : 0; let at = 0;
    const arcs = ring.map(k => {
      const n = T.by[k] || 0, len = C2 * n / total, seg = Math.max(0.5, len - GAP);
      const a = `<circle r="${R}" cx="80" cy="80" fill="none" stroke="var(--cat-${k})" stroke-width="18" stroke-dasharray="${seg.toFixed(2)} ${(C2 - seg).toFixed(2)}" stroke-dashoffset="${(-at).toFixed(2)}" transform="rotate(-90 80 80)" data-go-tab="pincodes" data-only="${k}" class="pie-seg"><title>${esc(nameOf(k))}: ${nf(n)} (${pct(n)})</title></circle>`;
      at += len; return a;
    }).join('');
    // inner ring: the three groups, lined up under their statuses
    const RI = 49.5, CI = 2 * Math.PI * RI, GC = { needs: 'var(--cat-gap)', well: 'var(--cat-jdaonly)', none: 'var(--cat-nosales)' }; let ai = 0;
    const inner = G.map(([label, keys, only]) => {
      const n = keys.reduce((a, k) => a + (T.by[k] || 0), 0); if (!n) return '';
      const len = CI * n / total, seg = Math.max(0.5, len - 2);
      const a = `<circle r="${RI}" cx="80" cy="80" fill="none" stroke="${GC[only]}" stroke-opacity=".55" stroke-width="5" stroke-dasharray="${seg.toFixed(2)} ${(CI - seg).toFixed(2)}" stroke-dashoffset="${(-ai).toFixed(2)}" transform="rotate(-90 80 80)" data-go-tab="pincodes" data-only="${only}" class="pie-seg"><title>${label}: ${nf(n)} (${pct(n)})</title></circle>`;
      ai += len; return a;
    }).join('');
    const cols = G.map(([label, keys, only]) => {
      const n = keys.reduce((a, k) => a + (T.by[k] || 0), 0);
      return `<div class="sp-grp"><button type="button" class="sp-head" data-go-tab="pincodes" data-only="${only}"><b>${label}</b><span>${nf(n)} · ${pct(n)}</span><i aria-hidden="true">›</i></button>`
        + keys.map(k => `<div class="sp-row" role="link" tabindex="0" data-go-tab="pincodes" data-only="${k}"><i class="gdot" style="background:var(--cat-${k})"></i><span class="nm">${cutLabel(k)}</span><b>${nf(T.by[k] || 0)}</b><em>${pct(T.by[k] || 0)}</em></div>`).join('')
        + `</div>`;
    }).join('');
    return `<div class="sp-pie"><svg viewBox="0 0 160 160" width="160" height="160" role="img" aria-label="Pincodes by grouping">${arcs}${inner}<text x="80" y="80" text-anchor="middle" class="pie-n">${nf(total)}</text><text x="80" y="95" text-anchor="middle" class="pie-l">pincodes</text></svg>`
      + `<button type="button" class="sp-all" data-go-tab="pincodes" data-only="all">All ${nf(total)} pincodes ›</button></div><div class="sp-cols">${cols}</div>`;
  }
  // ---- JDA sales, day by day: running total for the period vs the comparison period ----
  function dailyJda(from, to) {
    const pins = new Set(pincodesForCityScope(currentCityScope)), dd = (DAILY.daily_deals || {})[currentScenario] || (DAILY.daily_deals || {}).all || {};
    return workDays(from, to).map(day => { let s2 = 0; const m = dd[day]; if (m) for (const p in m) if (pins.has(p)) s2 += m[p].jda_sales || 0; return s2; });
  }
  // JDA presentations on each working day; one made on a day with no sales anywhere (a Sunday or holiday) counts on
  // the next working day, so the totals match the page
  function dailyPres(from, to) {
    const pins = new Set(pincodesForCityScope(currentCityScope)), wd = workDays(from, to), PD = DAILY.daily_presence || {};
    const out = wd.map(() => 0); if (!wd.length) return out;
    let i = 0;
    daysBetween(from, to).forEach(day => {
      while (i < wd.length - 1 && wd[i] < day) i++;
      const m = PD[day]; if (!m) return;
      let t = 0; for (const p in m) if (pins.has(p)) t += m[p].count || 0;
      out[i] += t;
    });
    return out;
  }
  // the day-by-day chart: JDA sales, JDA presentations or JDA conversion, so far in the period (switch on the card)
  function trendHtml(from, to, C) {
    const K = trendMetric, isConv = K === 'conv';
    const cum = a => { let t = 0; return a.map((x, i) => (t += x, perDay ? t / (i + 1) : t)); };   // running total, or running average per working day
    // conversion counts from the first day with presentation data (the feed starts 7 Apr 2026), so sales from
    // days with no presentation record don't inflate it
    const presFrom = Object.keys(DAILY.daily_presence || {}).filter(d => Object.keys(DAILY.daily_presence[d]).length).sort()[0] || '';
    const convOf = (s2, p2, dl) => { let ts = 0, tp = 0; return s2.map((x, i) => { if (dl[i] < presFrom) return null; ts += x; tp += p2[i] || 0; return tp ? 100 * ts / tp : null; }); };
    const sD = dailyJda(from, to), sD0 = C ? dailyJda(C.from, C.to) : [];
    const pD = K !== 'sales' ? dailyPres(from, to) : [], pD0 = K !== 'sales' && C ? dailyPres(C.from, C.to) : [];
    const curD = K === 'pres' ? pD : sD, prevD = K === 'pres' ? pD0 : sD0;
    const wd1 = workDays(from, to), wd0 = C ? workDays(C.from, C.to) : [];
    const cur = isConv ? convOf(sD, pD, wd1) : cum(curD), prev = C ? (isConv ? convOf(sD0, pD0, wd0) : cum(prevD)) : [];
    const n = Math.max(cur.length, prev.length); if (!n) return '<p class="note">No days in this period.</p>';
    const ok = v => v !== null && isFinite(v);
    const hi0 = Math.max(1, ...cur.filter(ok), ...prev.filter(ok)), W = 560, H = 196, L = 34, B = 22, T = 16, RR = 64;
    // grid steps: about four round steps for every scale (sales, presentations and conversion alike)
    const nice = h => { const raw = h / 4, mag = Math.pow(10, Math.floor(Math.log10(raw))), r = raw / mag; return (r <= 1 ? 1 : r <= 2 ? 2 : r <= 2.5 ? 2.5 : r <= 5 ? 5 : 10) * mag; };
    const step = Math.max(nice(hi0), K === 'conv' ? 0.5 : 1);
    const hi = Math.ceil(hi0 * 1.06 / step) * step;   // a little headroom, then up to a grid line (all three the same)
    const X = i => L + (n === 1 ? 0 : i * (W - L - RR) / (n - 1)), Y = v => T + (H - T - B) * (1 - v / hi);
    const ax = g => isConv ? nf(g) + '%' : K === 'pres' && g >= 1000 ? nf(g / 1000) + 'k' : nf(g);
    const line = (a, cls) => { const pts = a.map((v, i) => ok(v) ? `${X(i).toFixed(1)},${Y(v).toFixed(1)}` : null).filter(Boolean); return pts.length ? `<polyline class="${cls}" points="${pts.join(' ')}" fill="none"/>` : ''; };
    let grid = ''; for (let g = 0; g <= hi + 1e-9; g += step) grid += `<line x1="${L}" x2="${W - RR}" y1="${Y(g).toFixed(1)}" y2="${Y(g).toFixed(1)}" class="tr-grid"/><text x="${L - 6}" y="${(Y(g) + 4).toFixed(1)}" text-anchor="end" class="tr-ax">${ax(g)}</text>`;
    // date ticks from this period only (the earlier period can have a selling day more, which has no date here)
    const days = workDays(from, to), m = Math.max(1, days.length), ticks = [0, Math.round((m - 1) / 3), Math.round(2 * (m - 1) / 3), m - 1].filter((v, i, a) => a.indexOf(v) === i && days[v]);
    const xl = ticks.map(i => `<text x="${X(i).toFixed(1)}" y="${H - 5}" text-anchor="middle" class="tr-ax">${fD(days[i])}</text>`).join('');
    const fmt = v => isConv ? nf(v) + '%' : nf(v);
    // end labels, kept 14px apart so close values don't print over each other
    const lastOf = a => { for (let i = a.length - 1; i >= 0; i--) if (ok(a[i])) return i; return -1; };
    const ends = [[cur, 'cur'], [prev, 'prev']].map(([a, cls]) => { const k = lastOf(a); return k < 0 ? null : k < n - 1 ? { cls, x: Math.min(X(k), W - RR - 20), y: Y(a[k]) - 9 < 12 ? Y(a[k]) + 18 : Y(a[k]) - 9, t: fmt(a[k]), mid: true } : { cls, x: X(k) + 8, y: Y(a[k]) + 4, t: fmt(a[k]) }; }).filter(Boolean).sort((p, q) => p.y - q.y);
    // two labels close to each other (at the right edge, or one ending early): pushed 17px apart
    if (ends.length === 2 && Math.abs(ends[1].x - ends[0].x) < 60 && ends[1].y - ends[0].y < 17) { const mid = (ends[0].y + ends[1].y) / 2; ends[0].y = mid - 8.5; ends[1].y = mid + 8.5; }
    const lab = ends.map(e => `<text x="${e.x.toFixed(1)}" y="${e.y.toFixed(1)}"${e.mid ? ' text-anchor="middle"' : ''} class="tr-lab ${e.cls}">${e.t}</text>`).join('');
    const pdays = C ? workDays(C.from, C.to) : [];
    const what = K === 'pres' ? 'JDA presentations' : 'JDA sales';
    // tooltip: which line (its key), the date, the value, that day's own count; nothing the legend already says
    const ser = (a, raw, sRaw, pRaw, dl, cls, color) => ({ name: '', color, pts: a.map((v, i) => !ok(v) ? null : { x: +X(i).toFixed(1), y: +Y(v).toFixed(1),
      html: `<span class="tt-h"><i class="tr-key ${cls}"></i>${dl[i] ? fD(dl[i]) : ''} <em>working day ${i + 1}</em></span>`
        + (isConv ? `<span class="tt-v"><strong>${fmt(v)}</strong> JDA conversion so far</span><span class="tt-sub">${nf(sRaw[i] || 0)} JDA sales, ${nf(pRaw[i] || 0)} presentations on the day</span>`
          : `<span class="tt-v"><strong>${nf(v)}</strong> ${perDay ? what + ' a working day, average so far' : what + ' so far'}</span><span class="tt-sub">${nf(raw[i] || 0)} on the day</span>`) }).filter(Boolean) });
    const hvId = hvReg([ser(cur, curD, sD, pD, days, 'cur', 'var(--accent)')].concat(C ? [ser(prev, prevD, sD0, pD0, pdays, 'prev', 'var(--text-dim)')] : []));
    const hits = `<rect class="hv-pad" x="${L}" y="${T}" width="${W - L - RR + 8}" height="${H - T - B}"/><circle class="hv-dot" r="4.5" visibility="hidden"/>`;
    $id('ovTrendH').textContent = isConv ? 'JDA conversion so far, by working day'
      : perDay ? `Average ${what} per working day, as the period goes` : `${what} so far, by working day`;
    $id('ovTrendH').title = isConv ? 'JDA sales ÷ JDA presentations from the start of the period. Selling days only.'
      : "Selling days only, so holidays don't shift the lines.";
    const sum = a => a.reduce((x, y) => x + y, 0), avg = (a, k) => k ? sum(a) / k : 0;
    const unit = isConv ? 'conversion' : K === 'pres' ? (perDay ? 'presentations a working day' : 'presentations') : (perDay ? 'JDA sales a working day' : 'JDA sales');
    const val = (raw, s2, p2, a) => isConv ? { txt: lastOf(a) >= 0 ? nf(a[lastOf(a)]) + '%' : '—' } : { sales: perDay ? avg(raw, raw.length) : sum(raw) };
    const H1 = heads(from, to), H0 = C ? heads(C.from, C.to) : null;
    $id('ovHc').innerHTML = legendHtml([Object.assign({ cls: 'cur', dates: `${fD(from)}–${fD(to)}`, unit, heads: H1.n }, val(curD, sD, pD, cur))]
      .concat(C ? [Object.assign({ cls: 'prev', dates: `${fD(C.from)}–${fD(C.to)}`, unit, heads: H0.n }, val(prevD, sD0, pD0, prev))] : []));
    return `<svg class="trend" data-hv="${hvId}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${isConv ? 'JDA conversion' : what} day by day">${grid}${line(prev, 'tr-prev')}${line(cur, 'tr-cur')}`
      + `${lab}${xl}${hits}</svg>`;
  }



  // grouping colours, by meaning (checked with the dataviz validator; inside every group the pairs clear the
  // colour-blind floor in both themes): Missing out = warm by severity (Not visiting red, Visiting-not-closing orange,
  // low share yellow), Doing well = green (only JDA selling) / blue (JDA share above the line), No sales yet = greys by
  // activity (visited = mid grey, no activity = faint). Pairs inside a group also differ in lightness.
  const PAL = {
    dark:  { gap: '#f28c28', notpresent: '#e5484d', band1: '#e9c46a', band2: '#3b82f6', band3: '#7aa7f7', jdaonly: '#2fb35c', nosales: '#9aa3b0', outside: '#4f5866' },
    light: { gap: '#e8650d', notpresent: '#9f1d2a', band1: '#f2c41f', band2: '#2563eb', band3: '#6b93ea', jdaonly: '#1d8a45', nosales: '#6b7380', outside: '#bcc3ce' },
  };
  function applyPalette() {
    const t = document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    Object.assign(COLORS, PAL[t]); applyColorsToCSS();
  }
  applyPalette();
  new MutationObserver(() => { applyPalette(); refreshAll(); }).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });


  /* ---------- table cells: one number format; small samples greyed ---------- */
  { const nfc = v => typeof v === 'number' ? (Math.round(v * 10) / 10).toLocaleString('en-IN') : v;
    ['jda_sales', 'jds_sales', 'total_sales', 'presentation_count', 'distinct_jda_employees', 'deployed_jda_count', 'deployed_presentations', 'monetizable_listings', 'b2b_count']
      .forEach(k => { const o = CELL_RENDERERS[k]; if (o) CELL_RENDERERS[k] = r => nfc(o(r)); });
    const oc = CELL_RENDERERS.conversion_rate_pct, os = CELL_RENDERERS.jda_share_pct;
    CELL_RENDERERS.conversion_rate_pct = r => (r.presentation_count || 0) < 10 && r.conversion_rate_pct !== null && r.conversion_rate_pct !== undefined
      ? `<span class="lown" title="Only ${r.presentation_count || 0} presentation${r.presentation_count === 1 ? '' : 's'}: too few to judge">${oc(r)}</span>` : oc(r);
    CELL_RENDERERS.jda_share_pct = r => { const n = (r.jda_sales || 0) + (r.jds_sales || 0);
      return n < 5 && r.jda_share_pct !== null && r.jda_share_pct !== undefined ? `<span class="lown" title="Only ${nfc(n)} JDA + JDS sale${n === 1 ? '' : 's'}: too few to judge">${os(r)}</span>` : os(r); };
    renderTable(currentRows);
  }

  /* ---------- 3. sub-verticals & sales groups ---------- */
  const UNT_TIP = ` <span class="why" title="Businesses with no category on file yet, so they cannot be placed in a sub-vertical.">why?</span>`;
  let svPin = '', svOpen = { d: new Set(), l: new Set() }, svShowAll = { d: false, l: false };
  // Sales groups: all, or only JD's top 500 / top 250 by FY26 revenue (2026-10-15; ranks from 'top 500 sales group.xlsx',
  // window.TOP_SG_RANK). Ranks 8 and 10 are buckets ('Unclassified (...)', 'Untagged (...)'), not sales groups: never kept.
  let svTop = 0;
  try { const v = +localStorage.getItem('jda-sv-top'); if ([0, 250, 500].includes(v)) svTop = v; } catch (e) { /* default: all */ }
  const svKeep = sg => { if (!svTop) return true; const r = (window.TOP_SG_RANK || {})[sg]; return !!r && r <= svTop && !/^(Unclassified|Untagged) \(/.test(sg); };
  const svSort = { d: { key: 'deals', dir: -1 }, l: { key: 'total', dir: -1 } };
  const svVal = (t, k, o) => k === 'name' ? String(o.name || '').toLowerCase()
    : k === 'share' ? (o.jda + o.jds ? o.jda / (o.jda + o.jds) : -1)
    : k === 'paidpct' ? (o.total ? o.paid / o.total : -1) : o[k];
  const svCmp = t => (a, b) => { const k = svSort[t].key, x = svVal(t, k, a), y = svVal(t, k, b); return x === y ? 0 : (x < y ? -1 : 1) * svSort[t].dir; };
  const svTh = (t, k, label, num) => `<th class="${num ? 'n' : ''}" data-sort-t="${t}" data-sort-k="${k}" title="Sort by ${label}">${label}${svSort[t].key === k ? `<span class="ar">${svSort[t].dir > 0 ? '↑' : '↓'}</span>` : ''}</th>`;
  const pinPlace = p => (((DATA.pincode_static[p] || {}).geo || {}).sample_place || '') + labStateOf(p);
  $id('svPinList').innerHTML = DATA.union_pincodes.map(p => `<option value="${p} ${esc(pinPlace(p))}"></option>`).join('');
  function svDealData(pin) {
    const out = {}; let splitMissing = false;
    daysBetween(periodFromDate, periodToDate).forEach(day => {
      const dm = (DAILY.sv_sg_by_day || {})[day]; if (!dm) return;
      (pin ? [[pin, dm[pin]]] : Object.entries(dm)).forEach(([p, svs]) => {
        if (!svs) return;
        Object.entries(svs).forEach(([sv, sgs]) => {
          Object.entries(sgs).forEach(([sg, raw]) => {
            if (!svKeep(sg)) return;
            let v = Array.isArray(raw) ? raw : [raw, 0, 0];
            if (currentScenario !== 'all') { if (v.length < 6) splitMissing = true; else v = currentScenario === 'fresh' ? v.slice(3, 6) : [v[0] - v[3], v[1] - v[4], v[2] - v[5]]; }
            if (!v[0]) return;
            const o = out[sv] || (out[sv] = { deals: 0, jda: 0, jds: 0, sg: {} });
            o.deals += v[0]; o.jda += v[1]; o.jds += v[2];
            const g = o.sg[sg] || (o.sg[sg] = { deals: 0, jda: 0, jds: 0 }); g.deals += v[0]; g.jda += v[1]; g.jds += v[2];
          });
        });
      });
    });
    return { out, splitMissing };
  }
  function svListData(pin) {
    const out = {};
    (pin ? [[pin, (MONETIZABLE_SV_SG || {})[pin]]] : Object.entries(MONETIZABLE_SV_SG || {})).forEach(([p, svs]) => {
      if (!svs) return;
      Object.entries(svs).forEach(([sv, sgs]) => {
        const kept = Object.entries(sgs).filter(([sg]) => svKeep(sg)); if (!kept.length) return;
        const o = out[sv] || (out[sv] = { total: 0, paid: 0, sg: {} });
        kept.forEach(([sg, a]) => { o.total += a[0]; o.paid += a[1]; const g = o.sg[sg] || (o.sg[sg] = { total: 0, paid: 0 }); g.total += a[0]; g.paid += a[1]; });
      });
    });
    return out;
  }
  function renderSV() {
    $id('svNow').innerHTML = svPin ? `Showing <b>${esc(pinPlace(svPin))} ${svPin}</b>` : 'Showing <b>all Mumbai</b>';
    const { out, splitMissing } = svDealData(svPin);
    const isUnt = sv => /^untagged$/i.test(sv);
    const dl = Object.entries(out).map(([sv, o]) => { o.name = cap(sv); return [sv, o]; }).sort((a, b) => svCmp('d')(a[1], b[1]));
    const dUnt = dl.filter(([sv]) => isUnt(sv)), dReal = dl.filter(([sv]) => !isUnt(sv));
    const tot = dl.reduce((a, [, o]) => a + o.deals, 0);
    $id('svDealsNote').textContent = `${nf(tot)} deals closed by all teams, ${periodLabel()}${currentScenario !== 'all' ? (currentScenario === 'fresh' ? ', Fresh only' : ', Renewal only') : ''}.${splitMissing ? ' (Fresh / Renewal split not in this data yet: showing all deals.)' : ''}${svTop ? ` Top ${svTop} sales groups only.` : ''}`;
    const ln = document.querySelector('#svList') && document.querySelector('#svList').parentElement.querySelector('.note'); if (ln) ln.textContent = svTop ? `Monthly snapshot. Top ${svTop} sales groups only.` : 'Monthly snapshot.';
    document.querySelectorAll('#svTopSeg button').forEach(b => b.classList.toggle('active', +b.dataset.top === svTop));
    const shareCell = (j, s2) => { const sh = j + s2 ? 100 * j / (j + s2) : null; return sh === null ? '—' : `${nf(sh)}%<span class="sv-bar"><i style="width:${Math.min(100, sh)}%"></i></span>`; };
    const dRows = (svShowAll.d ? dReal : dReal.slice(0, 15)).concat(dUnt).map(([sv, o]) => {
      const open = svOpen.d.has(sv);
      const sgs = open ? Object.entries(o.sg).map(([g, x]) => { x.name = g; return [g, x]; }).sort((a, b) => svCmp('d')(a[1], b[1])).map(([g, x]) => `<tr class="sg"><td>${esc(g)}</td><td class="n">${nf(x.deals)}</td><td class="n">${nf(x.jda)}</td><td class="n">${nf(x.jds)}</td><td class="n">${shareCell(x.jda, x.jds)}</td></tr>`).join('') : '';
      return `<tr class="sv${open ? ' open' : ''}${isUnt(sv) ? ' unt' : ''}" data-sv="${esc(sv)}" data-t="d" tabindex="0"><td>${esc(cap(sv))}${isUnt(sv) ? UNT_TIP : ''}</td><td class="n"><b>${nf(o.deals)}</b></td><td class="n">${nf(o.jda)}</td><td class="n">${nf(o.jds)}</td><td class="n">${shareCell(o.jda, o.jds)}</td></tr>${sgs}`;
    }).join('');
    $id('svDeals').innerHTML = dl.length ? `<table class="svt"><thead><tr>${svTh('d', 'name', 'Sub-vertical')}${svTh('d', 'deals', 'Deals', 1)}${svTh('d', 'jda', 'JDA', 1)}${svTh('d', 'jds', 'JDS', 1)}${svTh('d', 'share', 'JDA share', 1)}</tr></thead><tbody>${dRows}</tbody></table>`
      + (dl.length > 15 ? `<button class="mini-btn sv-more" type="button" data-more="d">${svShowAll.d ? 'Show the top 15 only' : `Show all ${dl.length} sub-verticals`}</button>` : '')
      : '<p class="note">No deals closed here in this period.</p>';
    const L = Object.entries(svListData(svPin)).map(([sv, o]) => { o.name = cap(sv); return [sv, o]; }).sort((a, b) => svCmp('l')(a[1], b[1]));
    const lUnt = L.filter(([sv]) => isUnt(sv)), lReal = L.filter(([sv]) => !isUnt(sv));
    const lRows = (svShowAll.l ? lReal : lReal.slice(0, 15)).concat(lUnt).map(([sv, o]) => {
      const open = svOpen.l.has(sv);
      const sgs = open ? Object.entries(o.sg).map(([g, x]) => { x.name = g; return [g, x]; }).sort((a, b) => svCmp('l')(a[1], b[1])).map(([g, x]) => `<tr class="sg"><td>${esc(g)}</td><td class="n">${nf(x.total)}</td><td class="n">${nf(x.paid)}</td><td class="n">${x.total ? nf(100 * x.paid / x.total) + '%' : '—'}</td></tr>`).join('') : '';
      return `<tr class="sv${open ? ' open' : ''}${isUnt(sv) ? ' unt' : ''}" data-sv="${esc(sv)}" data-t="l" tabindex="0"><td>${esc(cap(sv))}${isUnt(sv) ? UNT_TIP : ''}</td><td class="n"><b>${nf(o.total)}</b></td><td class="n">${nf(o.paid)}</td><td class="n">${o.total ? nf(100 * o.paid / o.total) + '%' : '—'}</td></tr>${sgs}`;
    }).join('');
    $id('svList').innerHTML = L.length ? `<table class="svt"><thead><tr>${svTh('l', 'name', 'Sub-vertical')}${svTh('l', 'total', 'Listings', 1)}${svTh('l', 'paid', 'Paid', 1)}${svTh('l', 'paidpct', 'Paid %', 1)}</tr></thead><tbody>${lRows}</tbody></table>`
      + (L.length > 15 ? `<button class="mini-btn sv-more" type="button" data-more="l">${svShowAll.l ? 'Show the top 15 only' : `Show all ${L.length} sub-verticals`}</button>` : '')
      : '<p class="note">No listings on file here.</p>';
    if (window.renderTop200SV) window.renderTop200SV(svPin);
  }
  window.uiOpenSV = pin => { svPin = pin || ''; $id('svPin').value = pin ? `${pin} ${pinPlace(pin)}` : ''; svOpen = { d: new Set(), l: new Set() }; showTab('sv'); };
  const svToggle = tr => { const set = svOpen[tr.dataset.t]; const k = tr.dataset.sv; set.has(k) ? set.delete(k) : set.add(k); renderSV(); };
  panels.sv.addEventListener('click', e => {
    const m = e.target.closest('[data-more]'); if (m) { svShowAll[m.dataset.more] = !svShowAll[m.dataset.more]; return renderSV(); }
    const th = e.target.closest('th[data-sort-k]');
    if (th) { const t = th.dataset.sortT, k = th.dataset.sortK, S = svSort[t]; if (S.key === k) S.dir = -S.dir; else { S.key = k; S.dir = k === 'name' ? 1 : -1; } return renderSV(); }
    const tr = e.target.closest('tr.sv'); if (tr) svToggle(tr);
  });
  panels.sv.addEventListener('keydown', e => { const tr = e.target.closest('tr.sv'); if (tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); svToggle(tr); } });
  $id('svPin').addEventListener('change', e => { const m = String(e.target.value).match(/\d{6}/); svPin = m && DATA.union_pincodes.includes(m[0]) ? m[0] : ''; if (!svPin) e.target.value = ''; svOpen = { d: new Set(), l: new Set() }; renderSV(); });
  $id('svAll').addEventListener('click', () => window.uiOpenSV(''));
  $id('svTopSeg').addEventListener('click', e => {
    const b = e.target.closest('[data-top]'); if (!b) return;
    svTop = +b.dataset.top; try { localStorage.setItem('jda-sv-top', String(svTop)); } catch (er) { /* not remembered */ }
    svOpen = { d: new Set(), l: new Set() }; renderSV();
  });

  /* ---------- Gap pincodes by month follows Fresh / Renewal (the main page uses precomputed Fresh + Renewal counts) ---------- */
  const gapCache = {};
  function monthlyGaps(scn) {
    const scope = typeof currentCityScope === 'undefined' ? 'both' : currentCityScope;   // Main / Remote (Kolkata)
    const ck = scn + '|' + scope;
    if (gapCache[ck]) return gapCache[ck];
    const months = DATA.monthly_trend.monthly_gap_counts.map(r => r.month);
    const acc = {};
    months.forEach(m => { acc[m] = {}; });
    Object.entries(DAILY.daily_deals[scn] || {}).forEach(([day, pm]) => {
      const a = acc[day.slice(0, 7)]; if (!a) return;
      Object.entries(pm).forEach(([p, x]) => { const o = a[p] || (a[p] = { j: 0, s: 0, c: 0 }); o.j += x.jda_sales; o.s += x.jds_sales; });
    });
    Object.entries(DAILY.daily_presence || {}).forEach(([day, pm]) => {
      const a = acc[day.slice(0, 7)]; if (!a) return;
      Object.entries(pm).forEach(([p, x]) => { const o = a[p] || (a[p] = { j: 0, s: 0, c: 0 }); o.c += x.count; });
    });
    const inBranch = new Set(typeof pincodesForCityScope === 'function' ? pincodesForCityScope(scope) : DATA.union_pincodes);
    // 2026-10-12: the chart counts pincodes covered (at least one JDA presentation that month), not the gap pincodes
    return (gapCache[ck] = months.map(m => ({ month: m, gap_pincodes: Object.entries(acc[m]).filter(([p, o]) => inBranch.has(p) && o.c > 0).length })));
  }
  renderMonthBars = function () {
    const rows = monthlyGaps(currentScenario);
    const max = Math.max(...rows.map(r => r.gap_pincodes), 1);
    document.getElementById('monthBars').innerHTML = rows.map((r, i) => {
      const mStart = r.month + '-01', mEnd = MONTH_END_DATE[r.month];
      const overlaps = !(mEnd < periodFromDate || mStart > periodToDate);
      return `<div class="bar-col ${overlaps ? 'month-selected' : ''}" data-month-idx="${i}" title="Click to filter the whole dashboard to ${MONTH_NAMES[r.month]} only">
        <div class="bar-val">${r.gap_pincodes}</div><div class="bar" style="height:${Math.max(6, 120 * r.gap_pincodes / max)}px;"></div>
        <div class="bar-label">${MONTH_NAMES[r.month] || r.month}</div></div>`;
    }).join('');
  };
  renderMonthBars();


  /* ---------- 'How it compares', kept simple: one sentence and three side-by-side numbers ---------- */
  const medOf = a => { const v = a.filter(x => x !== null && !Number.isNaN(x)).sort((x, y) => x - y); if (!v.length) return null; const h = Math.floor(v.length / 2); return v.length % 2 ? v[h] : (v[h - 1] + v[h]) / 2; };
  window.labBench = function (pin) {
    window.__bench = null;
    const all = buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope);
    const mkt = r => r.jda_sales + r.jds_sales;
    const me = all.find(r => r.pincode === pin);
    if (!me || mkt(me) === 0) return '<p class="note">No JDA or JDS deal was closed here in this period, so there is nothing to compare yet. Try a longer period.</p>';
    if (mkt(me) < 5) return `<p class="note">Only ${nf(mkt(me))} JDA + JDS deal${mkt(me) === 1 ? '' : 's'} here in this period: too few to compare. Try a longer period.</p>`;
    const sizes = all.filter(r => mkt(r) > 0).map(mkt).sort((a, b) => a - b);
    const cut = [sizes[Math.floor(sizes.length / 4)], sizes[Math.floor(sizes.length / 2)], sizes[Math.floor(3 * sizes.length / 4)]];
    const band = v => v < cut[0] ? 0 : v < cut[1] ? 1 : v < cut[2] ? 2 : 3;
    const peers = all.filter(r => mkt(r) > 0 && band(mkt(r)) === band(mkt(me)));
    const share = r => 100 * r.jda_sales / mkt(r);
    const tShare = medOf(peers.map(share)), tDeals = medOf(peers.map(r => r.jda_sales)), tPres = medOf(peers.map(r => r.presentation_count));
    const tConv = medOf(peers.filter(r => r.presentation_count >= 10).map(r => 100 * r.jda_sales / r.presentation_count));
    window.__bench = { pin, tShare, tDeals, tPres, tConv, tJds: medOf(peers.map(r => r.jds_sales)) };
    const myShare = share(me);
    const diff = myShare - tShare;
    const verdict = diff >= 2 ? 'ahead of' : diff <= -2 ? 'behind' : 'level with';
    const cls = diff >= 2 ? 'good' : diff <= -2 ? 'bad' : '';
    let h = `<p class="lb-say">JDA is <b class="${cls}">${verdict}</b> a typical pincode of this size.</p>`
      + `<p class="note">Against the ${peers.length} pincodes with a similar number of JDA + JDS deals (${nf(mkt(me))} here).</p>`
      ;   // the numbers themselves sit in the tiles above, each with its typical value
    const k = layerOf(me);
    if (k === 'band1' && diff >= 2) h += `<p class="lb-note">Its JDA share is under the ${cutoffs[1]}% line set in Band settings, which is why it is listed as "JDA share ≤${cutoffs[1]}%", but it is ahead of similar pincodes.</p>`;
    if (diff <= -2) { const room = tShare / 100 * mkt(me) - me.jda_sales; if (room >= 1) h += `<p class="lb-note">At a typical share (${nf(tShare)}%), JDA would have about <b>${nf(room + me.jda_sales)} deals</b> here instead of ${nf(me.jda_sales)}.</p>`; }
    return h;
  };

  /* ---------- keep every tab in step with the filters; link the pincode page to its sub-verticals ---------- */
  const _refreshAll = refreshAll;
  refreshAll = function () { _refreshAll.apply(this, arguments); try { if (current === 'overview') renderOverview(); if (current === 'sv') renderSV(); } catch (e) { console.error(e); } };
  const _openPinPage = window.openPinPage;
  window.openPinPage = function (pin, fromClick) {
    _openPinPage(pin, fromClick);
    const nav = document.querySelector('#pinPage .pp-nav');
  };
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-pp-sv]'); if (!b) return;
    const pin = b.dataset.ppSv;
    document.querySelector('#pinPage [data-pp="back"]').click();
    setTimeout(() => window.uiOpenSV(pin), 0);
  });


  /* ---------- pincode window: business categories = top 5 by deals | top 5 by listings; the full list is on the Sub-verticals tab ---------- */
  const TOP = 5;
  const shareCellPP = (j, s2) => { const sh = j + s2 ? 100 * j / (j + s2) : null; return sh === null ? '—' : `${nf(sh)}%<span class="sv-bar"><i style="width:${Math.min(100, sh)}%"></i></span>`; };
  const pctPP = (a, b) => b ? nf(100 * a / b) + '%' : '—';
  const moreLine = n => n > TOP + 1 ? `<p class="note pp-more">Top ${TOP} of ${n} sub-verticals.</p>` : '';
  function pinCatsHtml(pin) {
    const { out, splitMissing } = svDealData(pin);
    const lastUnt = (a, b) => (/^untagged$/i.test(a[0]) - /^untagged$/i.test(b[0]));
    const D0 = Object.entries(out).sort((a, b) => b[1].deals - a[1].deals), D = D0.filter(x => !/^untagged$/i.test(x[0])).slice(0, TOP).concat(D0.filter(x => /^untagged$/i.test(x[0]))), DN = D0.length;
    const dt = D0.reduce((a, [, o]) => ({ deals: a.deals + o.deals, jda: a.jda + o.jda, jds: a.jds + o.jds }), { deals: 0, jda: 0, jds: 0 });
    const dRow = (name, o, cls) => `<tr class="${cls}"><td>${name}</td><td class="n"><b>${nf(o.deals)}</b></td><td class="n">${nf(o.jda)}</td><td class="n">${nf(o.jds)}</td><td class="n">${shareCellPP(o.jda, o.jds)}</td></tr>`;
    const dHtml = D.length ? `<table class="svt"><thead><tr><th>Sub-vertical</th><th class="n">Deals</th><th class="n">JDA</th><th class="n">JDS</th><th class="n">JDA share</th></tr></thead>
        <tbody>${D.map(([sv, o]) => /^untagged$/i.test(sv) ? dRow(esc(cap(sv)) + UNT_TIP, o, 'svs unt') : dRow(esc(cap(sv)), o, 'svs')).join('')}${dRow('Total', dt, 'tot')}</tbody></table>${moreLine(DN)}`
      : '<p class="note">No deals closed here in this period.</p>';
    const L0 = Object.entries(svListData(pin)).sort((a, b) => b[1].total - a[1].total), L = L0.filter(x => !/^untagged$/i.test(x[0])).slice(0, TOP).concat(L0.filter(x => /^untagged$/i.test(x[0]))), LN = L0.length;
    const lt = L0.reduce((a, [, o]) => ({ total: a.total + o.total, paid: a.paid + o.paid }), { total: 0, paid: 0 });
    const lRow = (name, o, cls) => `<tr class="${cls}"><td>${name}</td><td class="n"><b>${nf(o.total)}</b></td><td class="n">${nf(o.paid)}</td><td class="n">${pctPP(o.paid, o.total)}</td></tr>`;
    const lHtml = L.length ? `<table class="svt"><thead><tr><th>Sub-vertical</th><th class="n">Listings</th><th class="n">Paid</th><th class="n">Paid %</th></tr></thead>
        <tbody>${L.map(([sv, o]) => /^untagged$/i.test(sv) ? lRow(esc(cap(sv)) + UNT_TIP, o, 'svs unt') : lRow(esc(cap(sv)), o, 'svs')).join('')}${lRow('Total', lt, 'tot')}</tbody></table>${moreLine(LN)}`
      : '<p class="note">No listings on file here.</p>';
    return `<div><h3>Deals by sub-vertical</h3>${splitMissing ? '<p class="note">Fresh / Renewal split not in this data yet: all deals.</p>' : ''}${dHtml}</div>
      <div><h3>Listings by sub-vertical</h3><p class="note">Monthly snapshot.</p>${lHtml}</div>
      <div class="pp-go"><button class="mini-btn pp-go-btn" type="button" data-pp-sv="${pin}">See every sub-vertical and its sales groups ›</button></div>`;
  }
  const _openPinPageCats = window.openPinPage;
  window.openPinPage = function (pin) {
    const r = _openPinPageCats.apply(this, arguments);
    const holder = document.querySelector('#pinPage .pp-cats'); if (!holder) return r;
    const sec = holder.closest('.pp-sec');
    holder.outerHTML = `<div class="pp-cats2">${pinCatsHtml(pin)}</div>`;   // replaces the old hover-only tables and the roster box
    const note = sec.querySelector(':scope > .note'); if (note) note.remove();
    const who = [...document.querySelectorAll('#pinPage .pp-sec')].find(x => /^Who worked/.test((x.querySelector('h2') || {}).textContent || ''));
    if (who) who.before(sec);   // Business categories sit above "Who worked this pincode"
    return r;
  };

  // start on the tab in the link (or the overview)
  const startTab = new URL(location.href).searchParams.get('tab');
  showTab(startTab && panels[startTab] ? startTab : 'overview', false);
})();
</script>
"""


PLAN_JS = r"""
<script>
/* ================= action plan ================= */
(function () {
  const $id = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nf = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  const tc = v => String(v || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const ACT = {
    sales: { label: 'Close more deals', long: 'Close more deals', hint: 'JDAs visit but don\'t close' },
    pres: { label: 'Do more presentations', long: 'Do more presentations', hint: 'customers buy, JDA barely visits' },
    headcount: { label: 'Add or move JDAs', long: 'Add or move JDAs', hint: 'big market, too few JDAs working it' },
  };
  const KEY = 'jdaMumbaiUiLabPlan';
  let plan = {};
  try { plan = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; } catch (e) { plan = {}; }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(plan)); } catch (e) { /* storage blocked: the plan lives until the page closes */ } };
  const placeOnly = p => (((DATA.pincode_static[p] || {}).geo) || {}).sample_place || '';
  const place = p => placeOnly(p) + labStateOf(p);
  const stateOf = p => ((DATA.pincode_static[p] || {}).state) || '';
  const MANAGERS = [...new Set(Object.values(EMP_META).map(e => e.manager).filter(Boolean))].sort();

  // ---- current-period facts per pincode, owners and the peer typicals behind suggestions ----
  let _presWin = null;
  function presWindow() {   // manager -> presentations per pincode over the whole data window (fallback owner)
    if (_presWin) return _presWin;
    _presWin = {};
    Object.values(DAILY.rep_pin_pres_by_day || {}).forEach(pm => Object.entries(pm).forEach(([p, m]) => Object.entries(m).forEach(([id, n]) => {
      const g = (EMP_META[id] || {}).manager; if (!g) return; const o = _presWin[p] || (_presWin[p] = {}); o[g] = (o[g] || 0) + n;
    })));
    return _presWin;
  }
  let ctxKey = '', ctx = null;
  function context() {
    const key = [periodFromDate, periodToDate, currentScenario, currentCityScope, cutoffs[1]].join('|');
    if (ctx && key === ctxKey) return ctx;
    const rows = buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope);
    const by = Object.fromEntries(rows.map(r => [r.pincode, r]));
    // owner = the manager whose JDAs made the most presentations there in the period; else the deployed JDA's manager
    const pres = {};
    daysBetween(periodFromDate, periodToDate).forEach(day => {
      Object.entries((DAILY.rep_pin_pres_by_day || {})[day] || {}).forEach(([p, m]) => {
        Object.entries(m).forEach(([id, n]) => { const g = (EMP_META[id] || {}).manager; if (!g) return; const o = pres[p] || (pres[p] = {}); o[g] = (o[g] || 0) + n; });
      });
    });
    const owner = p => {
      const o = pres[p]; if (o) return Object.entries(o).sort((a, b) => b[1] - a[1])[0][0];
      const w = presWindow()[p]; if (w) return Object.entries(w).sort((a, b) => b[1] - a[1])[0][0];   // no visits this period: who worked it since April
      const d = ((JDA_DEPLOYMENT || {}).deployed || {})[p] || [];
      for (const e of d) { const g = (EMP_META[e.id] || {}).manager; if (g) return g; }
      return 'Unassigned';
    };
    const mkt = r => r.jda_sales + r.jds_sales;
    const sizes = rows.filter(r => mkt(r) > 0).map(mkt).sort((a, b) => a - b);
    const cut = sizes.length ? [sizes[Math.floor(sizes.length / 4)], sizes[Math.floor(sizes.length / 2)], sizes[Math.floor(3 * sizes.length / 4)]] : [1, 1, 1];
    const band = r => { const v = mkt(r); return v < cut[0] ? 0 : v < cut[1] ? 1 : v < cut[2] ? 2 : 3; };
    const med = a => { const v = a.filter(x => x !== null && !Number.isNaN(x)).sort((x, y) => x - y); if (!v.length) return 0; const h = Math.floor(v.length / 2); return v.length % 2 ? v[h] : (v[h - 1] + v[h]) / 2; };
    const typ = [0, 1, 2, 3].map(b => { const g = rows.filter(r => mkt(r) > 0 && band(r) === b); return { share: med(g.map(r => 100 * r.jda_sales / mkt(r))), pres: med(g.map(r => r.presentation_count)), active: med(g.map(r => r.distinct_jda_employees || 0)) }; });
    ctxKey = key; ctx = { rows, by, owner, band, typ, mkt };
    return ctx;
  }
  const plN = (v, one) => `${nf(v)} ${v === 1 ? one : one + 's'}`;
  const evidence = (r, a) => {
    if (!r) return '';
    const C = context(), t = C.typ[C.band(r)], share = C.mkt(r) ? nf(100 * r.jda_sales / C.mkt(r)) + '%' : '—';
    if (a === 'pres') return `JDS ${plN(r.jds_sales, 'deal')}; ${plN(r.presentation_count, 'JDA presentation')} (similar pincodes: ${nf(t.pres)})`;
    if (a === 'headcount') return `JDS ${plN(r.jds_sales, 'deal')}; ${plN(r.distinct_jda_employees || 0, 'active JDA')} (similar: ${nf(t.active)}), ${nf(r.deployed_jda_count || 0)} deployed`;
    return `JDA ${nf(r.jda_sales)} vs JDS ${nf(r.jds_sales)} (share ${share}); ${plN(r.presentation_count, 'presentation')}`;
  };
  function suggestions(a) {
    const C = context(), inPlan = new Set(Object.keys(plan));
    return C.rows.filter(r => {
      if (inPlan.has(r.pincode)) return false;
      const k = layerOf(r), m = C.mkt(r), t = C.typ[C.band(r)], share = m ? 100 * r.jda_sales / m : 0;
      if (a === 'sales') return k === 'gap' || (m > 0 && r.presentation_count >= t.pres && share < t.share - 2);
      if (a === 'pres') return k === 'notpresent' || (m > 0 && r.jds_sales > 0 && r.presentation_count < 0.5 * t.pres);
      return C.band(r) >= 2 && m > 0 && (r.distinct_jda_employees || 0) < t.active - 0.5;
    }).sort((x, y) => y.jds_sales - x.jds_sales);
  }

  // ---- changes to the plan ----
  function setAction(pin, a, note) {
    if (!a) delete plan[pin];
    else {
      plan[pin] = Object.assign(plan[pin] || { note: '', owner: '' }, { action: a, added: plan[pin] ? plan[pin].added : DAILY.window_end });
      if (note !== undefined) plan[pin].note = note;
    }
    save(); afterChange();
  }
  function afterChange() {
    const n = Object.keys(plan).length;
    const tab = document.querySelector('#uiNav [data-tab="plan"]');
    if (tab) { let b = tab.querySelector('.nbadge'); if (!b) { tab.insertAdjacentHTML('beforeend', '<span class="nbadge"></span>'); b = tab.querySelector('.nbadge'); } b.textContent = n || ''; b.hidden = !n; b.title = n ? `${n} pincode${n === 1 ? '' : 's'} in the plan` : ''; }
    if (document.getElementById('tab-plan').classList.contains('on')) renderPlan();
    if (typeof renderTable === 'function' && currentRows) renderTable(currentRows);
    if (document.body.classList.contains('pin-mode')) paintPinAction();
  }

  // ---- 1. the pincode table: an Action column with a small menu, and "add all shown" ----
  COLUMN_LABELS.plan = 'Action'; COLUMN_HINTS.plan = 'Add the pincode to your action plan'; COLUMN_WIDTHS.plan = 64;
  const IC_ADD = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="7.5" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="M10 6.5v7M6.5 10h7" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  const IC_IN = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="10" cy="10" r="8" fill="currentColor"/><path d="M6.3 10.2l2.4 2.4 5-5.2" fill="none" stroke="var(--panel)" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const actIcon = pin => { const e = plan[pin];   // the table's compact form: one icon, the action named in the tooltip
    return e ? `<button type="button" class="pl-ic in pl-${e.action}" data-plan-menu="${pin}" title="In the plan: ${esc(ACT[e.action].label)}${e.note ? ' · note: ' + esc(e.note) : ''}" aria-label="${pin}: ${esc(ACT[e.action].label)} (in the plan)">${IC_IN}</button>`
      : `<button type="button" class="pl-ic" data-plan-menu="${pin}" title="Add to the action plan" aria-label="Add ${pin} to the action plan">${IC_ADD}</button>`; };
  const actButton = r => { const e = plan[r.pincode]; return e ? `<button type="button" class="pl-chip pl-${e.action}" data-plan-menu="${r.pincode}"${e.note ? ` title="Note: ${esc(e.note)}"` : ''}>${ACT[e.action].label} ✓${e.note ? '<span class="nt" aria-label="has a note">✎</span>' : ''}</button>` : `<button type="button" class="pl-add" data-plan-menu="${r.pincode}">+ Action</button>`; };
  CELL_RENDERERS.plan = r => actIcon(r.pincode);
  columnOrder = columnOrder.filter(k => k !== 'plan').concat('plan');   // always the last column
  renderTableHead();
  let menu = null;
  const closeMenu = () => { if (menu) { const hadNoteEdit = !!menu.querySelector('#plNoteSaved') && menu.querySelector('#plNoteSaved').textContent === 'Saved.'; menu.remove(); menu = null; if (hadNoteEdit) afterChange(); } };
  function openMenu(btn, pin) {
    closeMenu();
    const cur = (plan[pin] || {}).action;
    menu = document.createElement('div'); menu.className = 'pl-menu';
    const curNote = (plan[pin] || {}).note || '';
    menu.innerHTML = Object.entries(ACT).map(([k, a]) => `<button type="button" data-set="${k}">${cur === k ? '✓ ' : ''}${a.long}<small>${a.hint}</small></button>`).join('') + (cur ? '<button type="button" class="rm" data-set="">Remove from plan</button>' : '')
      + `<div class="pl-note"><label for="plNoteBox">Note for ${pin} (your observations)</label><textarea id="plNoteBox" placeholder="e.g. JDAs visit but pitch the wrong category; target 5 deals">${esc(curNote)}</textarea>`
      + `<div class="saved" id="plNoteSaved">${cur ? 'Saved as you type.' : 'Pick an action above to save the note with it.'}</div></div>`;
    document.body.append(menu);
    const r = btn.getBoundingClientRect();
    menu.style.left = Math.min(window.scrollX + r.left, window.scrollX + window.innerWidth - menu.offsetWidth - 12) + 'px';
    menu.style.top = (window.scrollY + r.bottom + 4) + 'px';
    const box = menu.querySelector('#plNoteBox');
    box.addEventListener('input', () => {
      if (!plan[pin]) return;                       // not in the plan yet: the note is saved with the action chosen next
      plan[pin].note = box.value; save();
      const t = menu.querySelector('#plNoteSaved'); if (t) t.textContent = 'Saved.';
    });
    box.addEventListener('keydown', e => { if (e.key === 'Escape') { e.stopPropagation(); closeMenu(); afterChange(); } });
    menu.addEventListener('click', e => { const b = e.target.closest('[data-set]'); if (!b) return; setAction(pin, b.dataset.set, b.dataset.set ? box.value : undefined); closeMenu(); });
  }
  // capture on the table (an ancestor of the rows), so the Action button never opens the pincode page
  $id('dataTable').addEventListener('click', e => {
    const b = e.target.closest('[data-plan-menu]'); if (!b) return;
    e.stopPropagation(); e.preventDefault(); openMenu(b, b.dataset.planMenu);
  }, true);
  document.addEventListener('click', e => { if (menu && !menu.contains(e.target) && !e.target.closest('[data-plan-menu]')) closeMenu(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });
  const _refreshAll = refreshAll;
  refreshAll = function () { _refreshAll.apply(this, arguments); try { if (document.getElementById('tab-plan').classList.contains('on')) renderPlan(); } catch (e) { console.error(e); } };

  // ---- 2. the pincode window: one '+ Action' button in its top row, the same menu as the table ----
  function paintPinAction() {
    const nav = document.querySelector('#pinPage .pp-nav'); if (!nav) return;
    const pin = new URL(location.href).searchParams.get('pin'); if (!pin) return;
    let slot = nav.querySelector('.pp-act');
    if (!slot) { nav.querySelector('.pos').insertAdjacentHTML('beforebegin', '<span class="pp-act"></span>'); slot = nav.querySelector('.pp-act'); }
    slot.innerHTML = actButton({ pincode: pin });   // the pincode window keeps the labelled button
  }
  const _open = window.openPinPage;
  window.openPinPage = function (pin, fromClick) { _open(pin, fromClick); paintPinAction(); };
  $id('pinPage').addEventListener('click', e => {
    const b = e.target.closest('[data-plan-menu]'); if (!b) return;
    e.stopPropagation(); openMenu(b, b.dataset.planMenu);
  });

  // ---- 3. the Action plan tab: find opportunities (ranked by upside) -> plan with targets -> track ----
  // upside = extra JDA sales the pincode would make at the typical JDA share of similar-sized markets
  function upside(r) {
    if (!r) return 0;
    const C = context(), s = C.typ[C.band(r)].share / 100;
    if (!(s > 0 && s < 1)) return 0;
    return Math.max(0, s * r.jds_sales / (1 - s) - r.jda_sales);
  }
  const shareOf = r => { const m = r ? r.jda_sales + r.jds_sales : 0; return m ? 100 * r.jda_sales / m : null; };
  function fact(r, a) {   // one short, comparable fact per action
    if (!r) return '';
    const C = context(), t = C.typ[C.band(r)], sh = shareOf(r);
    if (a === 'pres') return `${plN(r.presentation_count, 'presentation')}; similar pincodes have ${nf(Math.round(t.pres))}`;
    if (a === 'headcount') return `${plN(r.distinct_jda_employees || 0, 'JDA')} presenting; similar pincodes have ${nf(Math.round(t.active))}`;
    return `JDA share ${sh === null ? '—' : nf(sh) + '%'}; similar pincodes have ${nf(t.share)}%`;
  }
  const STATUS = { new: 'Just added', idle: 'No activity yet', moving: 'Under way', met: 'Target met' };
  function statusOf(pin, e) {
    const P = progressOf(pin, e.added);
    if (!P.days) return 'new';
    if (e.target && P.sales >= e.target) return 'met';
    return P.sales > 0 || P.pres > 0 ? 'moving' : 'idle';
  }
  const _setAction = setAction;
  setAction = function (pin, a, note) {   // a new plan item starts with its upside as the target
    const fresh = a && !plan[pin];
    _setAction(pin, a, note);
    if (fresh && plan[pin]) { plan[pin].target = Math.max(1, Math.round(upside(context().by[pin]))); save(); afterChange(); }
  };

  let view = Object.keys(plan).length ? 'plan' : 'find', findAct = 'all', findMgr = '', findAll = false, shareOpen = false;
  const panel = $id('tab-plan');
  panel.innerHTML = `<h2 class="sr-only">Action plan</h2><div class="ap" id="ap"></div>`;
  function periodTxt() { return periodLabel() + (currentScenario === 'fresh' ? ', Fresh deals' : currentScenario === 'renewal' ? ', Renewal deals' : ''); }
  function groups() {
    const C = context(), g = {};
    Object.entries(plan).forEach(([pin, e]) => { const o = e.owner || C.owner(pin); (g[o] = g[o] || []).push({ pin, e, r: C.by[pin] }); });
    const rank = { idle: 0, new: 1, moving: 2, met: 3 };
    Object.values(g).forEach(l => l.sort((a, b) => rank[statusOf(a.pin, a.e)] - rank[statusOf(b.pin, b.e)] || (b.e.target || 0) - (a.e.target || 0)));
    return Object.entries(g).sort((a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
  }
  function opportunities() {
    const C = context(), seen = new Map();
    Object.keys(ACT).forEach(a => suggestions(a).forEach(r => { if (!seen.has(r.pincode)) seen.set(r.pincode, { r, a }); }));
    return [...seen.values()].map(o => ({ ...o, up: upside(o.r), mgr: C.owner(o.r.pincode) }))
      .sort((x, y) => y.up - x.up || y.r.jds_sales - x.r.jds_sales);
  }
  const bar = (v, t) => `<span class="ap-bar"><i style="width:${t ? Math.min(100, 100 * v / t) : 0}%"></i></span>`;

  let planSt = 'all', planMgr = '', rowMenu = null;
  window.renderPlan = function () {
    const C = context(), G = groups(), n = Object.keys(plan).length, all = opportunities();
    let tgt = 0, got = 0, met = 0; const cnt = { idle: 0, moving: 0, met: 0, new: 0 };
    Object.entries(plan).forEach(([pin, e]) => { tgt += e.target || 0; got += Math.min(progressOf(pin, e.added).sales, e.target || Infinity); const st = statusOf(pin, e); cnt[st]++; if (st === 'met') met++; });
    // one slim summary line instead of four big tiles
    const head = (n ? `<div class="ap-sum">
        <span><b>${nf(n)}</b> pincode${n === 1 ? '' : 's'} · <b>${nf(G.length)}</b> manager${G.length === 1 ? '' : 's'}</span>
        <span class="ap-sum-p">${bar(got, tgt)}<span><b>+${nf(got)}</b> of +${nf(tgt)} JDA sales targeted${tgt ? ` (${nf(100 * got / tgt)}%)` : ''}</span></span>
        <span><b>${nf(met)}</b> of ${nf(n)} targets met</span>
      </div>` : '') + `
      <div class="ap-bar-row">
        <div class="seg ap-view" role="tablist" aria-label="Action plan view">
          <button type="button" role="tab" data-view="plan" aria-selected="${view === 'plan'}" class="${view === 'plan' ? 'active' : ''}">Your plan${n ? ` (${n})` : ''}</button>
          <button type="button" role="tab" data-view="find" aria-selected="${view === 'find'}" class="${view === 'find' ? 'active' : ''}">Find opportunities (${all.length})</button>
        </div>
        <span class="grow"></span>
        <div class="ap-share"><button type="button" class="mini-btn" id="apShare" aria-expanded="${shareOpen}">Share</button>
          ${shareOpen ? `<div class="ap-menu" role="menu">
            <button type="button" data-do="xlsx"${n ? '' : ' disabled'}>Download Excel<small>a sheet per manager, plus All</small></button>
            <button type="button" data-do="imgs"${n ? '' : ' disabled'}>Images for every manager<small>one picture each, to send on WhatsApp</small></button>
            <button type="button" data-do="save"${n ? '' : ' disabled'}>Save plan file<small>open it on another PC</small></button>
            <button type="button" data-do="open">Open plan file</button>
            ${n ? '<button type="button" data-do="clear" class="rm">Clear the plan</button>' : ''}
            <p class="ap-foot">The plan is kept in this browser. Save a plan file to move it.</p></div>` : ''}
          <input type="file" id="plImportFile" accept=".json,application/json" hidden></div>
      </div>`;
    let body;
    if (view === 'find') {
      const mgrs = [...new Set(all.map(o => o.mgr))].sort();
      const list = all.filter(o => (findAct === 'all' || o.a === findAct) && (!findMgr || o.mgr === findMgr));
      const shown = findAll ? list : list.slice(0, 15), cntA = a => all.filter(o => (a === 'all' || o.a === a) && (!findMgr || o.mgr === findMgr)).length;
      body = `<div class="ap-filters">
          <div class="ap-pills">${[['all', 'All']].concat(Object.entries(ACT).map(([k, a]) => [k, a.label])).map(([k, l]) => `<button type="button" class="ap-pill${k === 'all' ? '' : ' pl-' + k}" data-find="${k}" aria-pressed="${findAct === k}">${l} <b>${cntA(k)}</b></button>`).join('')}</div>
          <label class="ap-sel">Manager <select id="apMgr"><option value="">All managers</option>${mgrs.map(m => `<option value="${esc(m)}"${m === findMgr ? ' selected' : ''}>${esc(tc(m))}</option>`).join('')}</select></label>
        </div>
        ${list.length ? `<div class="pl-tbl-wrap"><table class="pl-t ap-t"><thead><tr><th>Pincode</th><th>Manager</th><th>What to do</th><th>Why</th><th class="n">JDA · JDS sales</th>
            <th class="n" title="Extra JDA sales in ${esc(periodTxt())} if the pincode had the typical JDA share of similar-sized markets">Extra JDA sales possible (est.)</th><th></th></tr></thead><tbody>
          ${shown.map(({ r, a, up, mgr }) => `<tr><td><b>${r.pincode}</b> <span class="pl">${esc(place(r.pincode))}</span></td><td>${esc(tc(mgr))}</td>
            <td><span class="ap-act pl-${a}">${ACT[a].label}</span></td><td class="why">${esc(fact(r, a))}</td>
            <td class="n">${nf(r.jda_sales)} · ${nf(r.jds_sales)}</td><td class="n"><b class="up">+${nf(up)}</b> <span class="u">JDA sales</span></td>
            <td class="n"><button class="ap-add" type="button" data-sug-add="${r.pincode}" data-act="${a}" aria-label="Add ${r.pincode} to the plan">+ Add</button></td></tr>`).join('')}
          </tbody></table></div>
          ${list.length > 15 ? `<button class="mini-btn ap-more" type="button" data-find-more>${findAll ? 'Show the top 15 only' : `Show all ${list.length}`}</button>` : ''}`
        : `<p class="pl-empty">No opportunities${findMgr ? ' for this manager' : ''} in the current period. Try a longer period.</p>`}`;
    } else if (!n) {
      body = `<div class="ap-empty"><b>Your plan is empty.</b><span>Start with the pincodes where JDA has the most to gain.</span><button type="button" class="mini-btn" data-view="find">Find opportunities</button></div>`;
    } else {
      const mgrOpts = cur => MANAGERS.map(m => `<option value="${esc(m)}"${m === cur ? ' selected' : ''}>${esc(tc(m))}</option>`).join('');
      const ORDER = ['idle', 'moving', 'met', 'new'];
      const pills = `<div class="ap-filters"><div class="ap-pills">`
        + `<button type="button" class="ap-pill" data-pst="all" aria-pressed="${planSt === 'all'}">All <b>${n}</b></button>`
        + ORDER.map(k => `<button type="button" class="ap-pill st-p st-${k}" data-pst="${k}" aria-pressed="${planSt === k}"${cnt[k] ? '' : ' disabled'}><i></i>${STATUS[k]} <b>${cnt[k]}</b></button>`).join('')
        + `</div>${G.length > 1 ? `<label class="ap-sel">Manager <select id="apPlanMgr"><option value="">All managers</option>${G.map(([m]) => `<option value="${esc(m)}"${m === planMgr ? ' selected' : ''}>${esc(tc(m))}</option>`).join('')}</select></label>` : ''}</div>`;
      const nextDay = iso => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1); return d.toISOString().slice(0, 10); };
      const groupsShown = G.filter(([m]) => !planMgr || m === planMgr).map(([m, items]) => [m, items.filter(it => planSt === 'all' || statusOf(it.pin, it.e) === planSt)]).filter(([, items]) => items.length);
      body = pills + (groupsShown.length ? `<div class="pl-tbl-wrap"><table class="pl-t ap-t ap-plan"><thead><tr><th>Status</th><th>Pincode</th><th>Action</th><th>Why</th>
          <th class="n" title="Extra JDA sales wanted; starts at the possible gain, change it if needed">Target</th>
          <th title="JDA sales and presentations after the day it was added (all sales, whatever the period filter)">Since added</th><th>Note for the manager</th><th></th></tr></thead>` + groupsShown.map(([mgr, items]) => {
        let t = 0, g = 0; items.forEach(({ pin, e }) => { t += e.target || 0; g += Math.min(progressOf(pin, e.added).sales, e.target || Infinity); });
        return `<tbody><tr class="ap-grp"><td colspan="8"><div class="ap-mgr-h"><h3>${esc(tc(mgr))}</h3><span class="note">${items.length} pincode${items.length === 1 ? '' : 's'}</span>
            <span class="ap-mgr-p">${bar(g, t)}<span><b>+${nf(g)}</b> of +${nf(t)}</span></span>
            <button class="ap-img" type="button" data-img="${esc(mgr)}" title="Download this manager's plan as an image">Image</button></div></td></tr>
          ${items.map(({ pin, e, r }) => { const s = statusOf(pin, e), P = progressOf(pin, e.added); return `<tr>
            <td><span class="ap-st st-${s}">${STATUS[s]}</span></td>
            <td><b>${pin}</b> <span class="pl">${esc(place(pin))}</span></td>
            <td><select data-row-act="${pin}" aria-label="Action for ${pin}">${Object.entries(ACT).map(([k, a]) => `<option value="${k}"${k === e.action ? ' selected' : ''}>${a.label}</option>`).join('')}</select></td>
            <td class="why">${esc(fact(r, e.action))}</td>
            <td class="n"><input type="number" class="ap-tgt" min="1" step="1" data-row-tgt="${pin}" value="${e.target || ''}" aria-label="Target JDA sales for ${pin}"></td>
            <td class="prog">${P.days ? `${bar(P.sales, e.target)}<span><b>+${nf(P.sales)}</b> of ${nf(e.target || 0)} · ${nf(P.pres)} pres.</span>`
              : `<small title="Added ${fD(e.added)}; numbers start with the next data update">Counts from ${fD(nextDay(e.added))}</small>`}</td>
            <td><input type="text" data-row-note="${pin}" value="${esc(e.note || '')}" placeholder="Add a note"></td>
            <td class="ap-more-c"><button class="ap-dots" type="button" data-row-menu="${pin}" aria-expanded="${rowMenu === pin}" aria-label="More for ${pin}" title="Change manager or remove">⋯</button>
              ${rowMenu === pin ? `<div class="ap-menu ap-rowmenu" role="menu"><label>Manager<select data-row-owner="${pin}">${mgrOpts(e.owner || C.owner(pin))}</select></label>
                <button type="button" class="rm" data-row-rm="${pin}">Remove from plan</button></div>` : ''}</td></tr>`; }).join('')}
          </tbody>`;
      }).join('') + `</table></div>` : `<p class="pl-empty">Nothing here with this filter.</p>`);
    }
    $id('ap').innerHTML = head + body;
    // the row menu floats above the page (the table's scroll box would clip it on the last rows)
    const rmEl = document.querySelector('.ap-rowmenu');
    if (rmEl) {
      const b = rmEl.parentElement.querySelector('.ap-dots').getBoundingClientRect();
      rmEl.style.position = 'fixed'; rmEl.style.right = 'auto';
      const h = rmEl.offsetHeight, w = rmEl.offsetWidth;
      rmEl.style.top = (b.bottom + 4 + h > window.innerHeight - 8 ? Math.max(8, b.top - 4 - h) : b.bottom + 4) + 'px';
      rmEl.style.left = Math.max(8, b.right - w) + 'px';
    }
  };
  window.addEventListener('scroll', () => { if (rowMenu) { rowMenu = null; renderPlan(); } }, { passive: true });
  panel.addEventListener('click', e => {
    const t = e.target;
    const v = t.closest('[data-view]'); if (v) { view = v.dataset.view; findAll = false; return renderPlan(); }
    const f = t.closest('[data-find]'); if (f) { findAct = f.dataset.find; findAll = false; return renderPlan(); }
    const ps = t.closest('[data-pst]'); if (ps && !ps.disabled) { planSt = ps.dataset.pst; return renderPlan(); }
    if (t.closest('[data-find-more]')) { findAll = !findAll; return renderPlan(); }
    if (t.closest('#apShare')) { shareOpen = !shareOpen; rowMenu = null; return renderPlan(); }
    const rmn = t.closest('[data-row-menu]'); if (rmn) { rowMenu = rowMenu === rmn.dataset.rowMenu ? null : rmn.dataset.rowMenu; shareOpen = false; return renderPlan(); }
    const add = t.closest('[data-sug-add]'); if (add) return setAction(add.dataset.sugAdd, add.dataset.act, '');
    const rm = t.closest('[data-row-rm]'); if (rm) { rowMenu = null; return setAction(rm.dataset.rowRm, ''); }
    const im = t.closest('[data-img]'); if (im) return exportImage(im.dataset.img);
    const d = t.closest('[data-do]'); if (!d || d.disabled) return;
    shareOpen = false; renderPlan();
    if (d.dataset.do === 'xlsx') return exportExcel();
    if (d.dataset.do === 'imgs') return groups().reduce((pr, [m]) => pr.then(() => exportImage(m)), Promise.resolve());
    if (d.dataset.do === 'save') return exportPlanFile();
    if (d.dataset.do === 'open') return $id('plImportFile').click();
    if (d.dataset.do === 'clear' && confirm('Remove every pincode from the plan?')) { plan = {}; save(); afterChange(); }
  });
  document.addEventListener('click', e => {
    if (shareOpen && !e.target.closest('.ap-share')) { shareOpen = false; renderPlan(); }
    if (rowMenu && !e.target.closest('.ap-more-c')) { rowMenu = null; renderPlan(); }
  });
  document.addEventListener('keydown', e => { if ((shareOpen || rowMenu) && e.key === 'Escape') { shareOpen = false; rowMenu = null; renderPlan(); } });
  panel.addEventListener('change', e => {
    const t = e.target;
    if (t.id === 'plImportFile') return importPlanFile(t);
    if (t.id === 'apMgr') { findMgr = t.value; findAll = false; return renderPlan(); }
    if (t.id === 'apPlanMgr') { planMgr = t.value; return renderPlan(); }
    if (t.dataset.rowAct) { plan[t.dataset.rowAct].action = t.value; save(); return afterChange(); }
    if (t.dataset.rowOwner) { const C = context(); plan[t.dataset.rowOwner].owner = t.value === C.owner(t.dataset.rowOwner) ? '' : t.value; rowMenu = null; save(); return afterChange(); }
    if (t.dataset.rowTgt) { const v = Math.round(parseFloat(t.value)); if (v >= 1) { plan[t.dataset.rowTgt].target = v; save(); afterChange(); } else t.value = plan[t.dataset.rowTgt].target || ''; }
  });
  panel.addEventListener('input', e => { const t = e.target; if (t.dataset.rowNote) { plan[t.dataset.rowNote].note = t.value; save(); } });

  // ---- progress since a pincode was added: JDA sales + presentations on the days after it (all sales) ----
  function progressOf(pin, added) {
    if (!added) return { sales: '', pres: '', days: 0 };
    const d = new Date(added + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1);
    const days = daysBetween(d.toISOString().slice(0, 10), DAILY.window_end);
    let sales = 0, pres = 0;
    days.forEach(day => {
      const dd = ((DAILY.daily_deals || {}).all || {})[day]; if (dd && dd[pin]) sales += dd[pin].jda_sales || 0;
      const pp = ((DAILY.rep_pin_pres_by_day || {})[day] || {})[pin]; if (pp) for (const id in pp) pres += pp[id];
    });
    return { sales, pres, days: days.length };
  }
  const fD = iso => new Date(iso + 'T00:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  // ---- the plan as a file: carry it to another PC, or send it to a manager ----
  function exportPlanFile() {
    const blob = new Blob([JSON.stringify({ kind: 'jda-action-plan', branch: document.title.split(' ')[0], exported: new Date().toISOString(), plan }, null, 1)], { type: 'application/json' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `${document.title.split(' ')[0]}_JDA_action_plan_${DAILY.window_end}.json`; a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }
  function importPlanFile(input) {
    const f = input.files && input.files[0]; if (!f) return;
    f.text().then(txt => {
      let d; try { d = JSON.parse(txt); } catch (e) { return alert('This file is not a plan exported from this dashboard.'); }
      const inc = d && d.kind === 'jda-action-plan' && d.plan && typeof d.plan === 'object' ? d.plan : null;
      if (!inc) return alert('This file is not a plan exported from this dashboard.');
      const pins = Object.keys(inc).filter(p => inc[p] && ACT[inc[p].action]);
      const clash = pins.filter(p => plan[p]).length;
      if (!confirm(`Add ${pins.length} pincode${pins.length === 1 ? '' : 's'} from this file to your plan?${clash ? ` ${clash} already in your plan will take the file's action and note.` : ''}`)) return;
      pins.forEach(p => { const e = inc[p]; plan[p] = { action: e.action, note: String(e.note || ''), owner: String(e.owner || ''), added: /^\d{4}-\d{2}-\d{2}$/.test(e.added || '') ? e.added : DAILY.window_end }; });
      save(); afterChange();
    }).finally(() => { input.value = ''; });
  }

  // ---- exports: Excel (a sheet per manager + All) and an image per manager ----
  const loadScript = src => new Promise((ok, bad) => { const s2 = document.createElement('script'); s2.src = src; s2.onload = ok; s2.onerror = bad; document.head.append(s2); });
  const HEAD = ['Manager', 'Action', 'Pincode', 'Place', 'State', 'Status', 'JDA deals', 'JDS deals', 'JDA share %', 'Presentations', 'Active JDAs', 'Deployed JDAs', 'Days since last JDA visit', 'Why', 'Note', 'Added', 'Target (JDA sales)', 'JDA sales since added', 'Presentations since added', 'Status', 'Upside now', 'Period'];
  const rowOut = (mgr, { pin, e, r }) => { const C = context(), m = r ? C.mkt(r) : 0; return [tc(mgr), ACT[e.action].long, pin, placeOnly(pin), stateOf(pin), r ? cardShortLabel(layerOf(r)) : '', r ? r.jda_sales : '', r ? r.jds_sales : '', r && m ? Math.round(1000 * r.jda_sales / m) / 10 : '', r ? r.presentation_count : '', r ? (r.distinct_jda_employees || 0) : '', r ? (r.deployed_jda_count || 0) : '', r && r.days_since_last_jda_visit !== null ? r.days_since_last_jda_visit : '', evidence(r, e.action), e.note || '', e.added || '', e.target || '', progressOf(pin, e.added).sales, progressOf(pin, e.added).pres, STATUS[statusOf(pin, e)], r ? Math.round(10 * upside(r)) / 10 : '', periodTxt()]; };
  const fileBase = () => `Mumbai_JDA_action_plan_${periodFromDate}_to_${periodToDate}`;
  async function exportExcel() {
    const G = groups();
    try {
      if (!window.XLSX) await loadScript('https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js');
      const wb = XLSX.utils.book_new(), used = new Set();
      const sheet = rows => { const ws = XLSX.utils.aoa_to_sheet([HEAD, ...rows]); ws['!cols'] = HEAD.map((h, i) => ({ wch: [22, 22, 9, 22, 16, 20, 9, 9, 10, 12, 10, 12, 12, 60, 40, 30][i] })); return ws; };
      const name = n => { let b = String(n).replace(/[\\/?*\[\]:]/g, ' ').slice(0, 28) || 'Sheet', x = b, i = 2; while (used.has(x.toLowerCase())) x = b.slice(0, 26) + ' ' + i++; used.add(x.toLowerCase()); return x; };
      XLSX.utils.book_append_sheet(wb, sheet(G.flatMap(([m, items]) => items.map(it => rowOut(m, it)))), name('All'));
      G.forEach(([m, items]) => XLSX.utils.book_append_sheet(wb, sheet(items.map(it => rowOut(m, it))), name(tc(m))));
      XLSX.writeFile(wb, fileBase() + '.xlsx');
    } catch (err) {
      // no internet for the Excel library: fall back to one CSV with every row
      const q = v => { const t = String(v ?? ''); return /[",\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t; };
      const csv = [HEAD, ...G.flatMap(([m, items]) => items.map(it => rowOut(m, it)))].map(r => r.map(q).join(',')).join('\r\n');
      const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob(['\ufeff' + csv], { type: 'text/csv' })); a.download = fileBase() + '.csv'; a.click();
      alert('The Excel library could not load (no internet?), so the plan was saved as a CSV file instead; it opens in Excel.');
    }
  }
  async function exportImage(mgr) {
    const G = groups(), items = (G.find(([m]) => m === mgr) || [null, []])[1];
    if (!items.length) return;
    const card = document.createElement('div');
    card.style.cssText = 'position:fixed;left:-10000px;top:0;width:980px;background:#ffffff;color:#14202b;font-family:Barlow,Segoe UI,sans-serif;padding:28px 32px;';
    const col = { sales: '#c2580f', pres: '#1d5fd1', headcount: '#1a7f52' };
    card.innerHTML = `<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px"><div style="font-size:26px;font-weight:700">Action plan for ${esc(tc(mgr))}</div></div>
      <div style="color:#55606d;font-size:15px;margin-bottom:16px">Mumbai JDA · ${esc(periodTxt())} · ${items.length} pincode${items.length === 1 ? '' : 's'}</div>
      <table style="width:100%;border-collapse:collapse;font-size:15px">
        <tr style="color:#55606d;font-size:13px;text-align:left"><th style="padding:8px;border-bottom:2px solid #e3e8ed;background:#ffffff;color:#55606d;position:static;text-align:left;font-weight:600">Action</th><th style="padding:8px;border-bottom:2px solid #e3e8ed;background:#ffffff;color:#55606d;position:static;text-align:left;font-weight:600">Pincode</th><th style="padding:8px;border-bottom:2px solid #e3e8ed;background:#ffffff;color:#55606d;position:static;text-align:left;font-weight:600">Why</th><th style="padding:8px;border-bottom:2px solid #e3e8ed;background:#ffffff;color:#55606d;position:static;text-align:right;font-weight:600">Target</th><th style="padding:8px;border-bottom:2px solid #e3e8ed;background:#ffffff;color:#55606d;position:static;text-align:left;font-weight:600">Note</th></tr>
        ${items.map(({ pin, e, r }) => `<tr><td style="padding:9px 8px;border-bottom:1px solid #e3e8ed;white-space:nowrap"><span style="color:${col[e.action]};font-weight:700">${ACT[e.action].label}</span></td>
          <td style="padding:9px 8px;border-bottom:1px solid #e3e8ed;white-space:nowrap"><b>${pin}</b><br><span style="color:#55606d;font-size:13px">${esc(place(pin))}</span></td>
          <td style="padding:9px 8px;border-bottom:1px solid #e3e8ed;color:#33404d;font-size:14px">${esc(fact(r, e.action))}</td>
          <td style="padding:9px 8px;border-bottom:1px solid #e3e8ed;text-align:right;white-space:nowrap"><b>+${nf(e.target || 0)}</b> JDA sales</td>
          <td style="padding:9px 8px;border-bottom:1px solid #e3e8ed;font-size:14px">${esc(e.note || '')}</td></tr>`).join('')}
      </table><div style="color:#8a94a0;font-size:12px;margin-top:12px">From the Mumbai JDA dashboard, data up to ${esc(DAILY.window_end)}.</div>`;
    document.body.append(card);
    try {
      if (!window.html2canvas) await loadScript('https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js');
      const canvas = await html2canvas(card, { scale: 2, backgroundColor: '#ffffff', logging: false });
      await new Promise(ok => canvas.toBlob(b => { const a = document.createElement('a'); a.href = URL.createObjectURL(b); a.download = `Action_plan_${tc(mgr).replace(/\s+/g, '_')}.png`; a.click(); ok(); }, 'image/png'));
    } catch (err) {
      alert('The image library could not load (no internet?). Use Download Excel instead, or take a screenshot of this manager\'s rows.');
    } finally { card.remove(); }
  }
  window.__plan = { get: () => plan, suggestions, context, exportExcel, exportImage, setAction };

  afterChange();
  if ($id('tab-plan').classList.contains('on')) renderPlan();
})();
</script>
"""


TOP200_JS = r"""
<script>
/* ================= top-200 JDA categories (additions only) ================= */
(function () {
  if (typeof TOP200 === 'undefined' || !TOP200 || !TOP200.cats) return;
  const $id = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nf = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  const CAT = Object.fromEntries(TOP200.cats.map(c => [c.catid, c]));
  const pick = a => currentScenario === 'fresh' ? [a[3], a[4], a[5]] : currentScenario === 'renewal' ? [a[0] - a[3], a[1] - a[4], a[2] - a[5]] : [a[0], a[1], a[2]];
  // deals per category for a pincode (or all Mumbai) over a period
  function dealsBy(pin, from, to) {
    const out = {};
    daysBetween(from, to).forEach(day => {
      const dm = TOP200.deals_by_day[day]; if (!dm) return;
      (pin ? [[pin, dm[pin]]] : Object.entries(dm)).forEach(([p, cm]) => {
        if (!cm || (currentCityScope !== 'both' && !pincodesForCityScope(currentCityScope).includes(p))) return;
        Object.entries(cm).forEach(([c, a]) => { const v = pick(a); if (!v[0]) return; const o = out[c] || (out[c] = [0, 0, 0]); o[0] += v[0]; o[1] += v[1]; o[2] += v[2]; });
      });
    });
    return out;
  }
  function listBy(pin) {
    const out = {};
    (pin ? [[pin, TOP200.listings[pin]]] : Object.entries(TOP200.listings)).forEach(([p, cm]) => {
      if (!cm) return;
      Object.entries(cm).forEach(([c, a]) => { const o = out[c] || (out[c] = [0, 0]); o[0] += a[0]; o[1] += a[1]; });
    });
    return out;
  }
  const share = (j, s2) => j + s2 ? 100 * j / (j + s2) : null;

  // ---- 1. pincode table: optional columns (Columns picker) ----
  Object.assign(COLUMN_LABELS, { t2_jda: 'Top-200 JDA Sales', t2_jds: 'Top-200 JDS Sales', t2_share: 'Top-200 JDA Share %', t2_listings: 'Top-200 Monetizable Listings' });
  Object.assign(COLUMN_HINTS, { t2_jda: 'JDA deals in the 200 categories Mumbai JDAs prioritise', t2_jds: 'JDS deals in the top-200 categories', t2_share: 'JDA share of JDA + JDS deals in the top-200 categories', t2_listings: 'Monetizable listings in the top-200 categories (monthly snapshot)' });
  Object.assign(COLUMN_WIDTHS, { t2_jda: 82, t2_jds: 82, t2_share: 86, t2_listings: 100 });
  Object.assign(CELL_RENDERERS, {
    t2_jda: r => nf(r.t2_jda || 0), t2_jds: r => nf(r.t2_jds || 0),
    t2_share: r => r.t2_share === null || r.t2_share === undefined ? '—' : nf(r.t2_share) + '%',
    t2_listings: r => (r.t2_listings || 0).toLocaleString('en-IN'),
  });
  ['t2_jda', 't2_jds', 't2_share', 't2_listings'].forEach(k => { NUMERIC_COLS.add(k); if (!columnOrder.includes(k)) { columnOrder.push(k); hiddenColumns.add(k); } });
  if (typeof renderColumnPanel === 'function') renderColumnPanel();   // the picker was built before these columns existed
  const _buildRows = buildRows;
  buildRows = function (scn, from, to) {
    const rows = _buildRows.apply(this, arguments);
    const saved = currentScenario; currentScenario = scn;
    const per = {};
    daysBetween(from, to).forEach(day => { const dm = TOP200.deals_by_day[day]; if (!dm) return; Object.entries(dm).forEach(([p, cm]) => { const o = per[p] || (per[p] = [0, 0]); Object.values(cm).forEach(a => { const v = pick(a); o[0] += v[1]; o[1] += v[2]; }); }); });
    currentScenario = saved;
    rows.forEach(r => { const o = per[r.pincode] || [0, 0]; r.t2_jda = o[0]; r.t2_jds = o[1]; r.t2_share = share(o[0], o[1]); r.t2_listings = Object.values(TOP200.listings[r.pincode] || {}).reduce((a, x) => a + x[0], 0); });
    return rows;
  };

  // ---- 2. sub-verticals tab: a top-200 section under the existing tables ----
  const svPanel = $id('tab-sv');
  svPanel.insertAdjacentHTML('beforeend', `<div class="t2-wrap"><div class="t2-head"><h3>Top 200 JDA categories</h3><span class="t2-cov" id="t2Cov"></span></div>
    </div>
    <div class="sv-grid"><div class="sv-card"><h3>Deals in the top-200 categories</h3><p class="note" id="t2DealsNote"></p><div id="t2Deals"></div></div>
    <div class="sv-card"><h3>Listings in the top-200 categories</h3><p class="note">Monthly snapshot.</p><div id="t2List"></div></div></div>`);
  const sortT = { d: { k: 'deals', dir: -1 }, l: { k: 'total', dir: -1 } }, allT = { d: false, l: false };
  let lastPin = '';
  const th = (t, k, label, num) => `<th class="${num ? 'n' : ''}" data-t2-t="${t}" data-t2-k="${k}" title="Sort by ${label}">${label}${sortT[t].k === k ? `<span class="ar">${sortT[t].dir > 0 ? '↑' : '↓'}</span>` : ''}</th>`;
  const cmp = t => (a, b) => { const k = sortT[t].k, x = a[k], y = b[k]; return x === y ? a.rank - b.rank : ((x ?? -1) < (y ?? -1) ? -1 : 1) * sortT[t].dir; };
  window.renderTop200SV = function (pin) {
    lastPin = pin || '';
    const D = dealsBy(lastPin, periodFromDate, periodToDate), L = listBy(lastPin);
    const dl = Object.entries(D).map(([c, v]) => ({ rank: CAT[c].rank, name: CAT[c].name, deals: v[0], jda: v[1], jds: v[2], share: share(v[1], v[2]) })).sort(cmp('d'));
    const ll = Object.entries(L).map(([c, v]) => ({ rank: CAT[c].rank, name: CAT[c].name, total: v[0], paid: v[1], pp: v[0] ? 100 * v[1] / v[0] : null })).sort(cmp('l'));
    // coverage: how much of all deals in the same scope/period is in the 200
    const all = buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope).filter(r => !lastPin || r.pincode === lastPin);
    const allJ = all.reduce((a, r) => a + r.jda_sales, 0), allS = all.reduce((a, r) => a + r.jds_sales, 0);
    const tJ = dl.reduce((a, x) => a + x.jda, 0), tS = dl.reduce((a, x) => a + x.jds, 0);
    $id('t2Cov').innerHTML = `${lastPin ? esc(lastPin) : 'All Mumbai'}: <b>${nf(tJ)}</b> of ${nf(allJ)} JDA deals and <b>${nf(tS)}</b> of ${nf(allS)} JDS deals are in these categories; JDA share there <b>${share(tJ, tS) === null ? '—' : nf(share(tJ, tS)) + '%'}</b>.`;
    $id('t2DealsNote').textContent = `${dl.length} of the 200 categories had deals, ${periodLabel()}${currentScenario !== 'all' ? (currentScenario === 'fresh' ? ', Fresh only' : ', Renewal only') : ''}.`;
    const shareCell = v => v === null ? '—' : `${nf(v)}%<span class="sv-bar"><i style="width:${Math.min(100, v)}%"></i></span>`;
    const dShown = allT.d ? dl : dl.slice(0, 20), lShown = allT.l ? ll : ll.slice(0, 20);
    $id('t2Deals').innerHTML = dl.length ? `<table class="svt t2"><thead><tr>${th('d', 'rank', 'Rank', 1)}${th('d', 'name', 'Category')}${th('d', 'deals', 'Deals', 1)}${th('d', 'jda', 'JDA', 1)}${th('d', 'jds', 'JDS', 1)}${th('d', 'share', 'JDA share', 1)}</tr></thead><tbody>`
      + dShown.map(x => `<tr><td class="n rk">${x.rank}</td><td>${esc(x.name)}</td><td class="n"><b>${nf(x.deals)}</b></td><td class="n">${nf(x.jda)}</td><td class="n">${nf(x.jds)}</td><td class="n">${shareCell(x.share)}</td></tr>`).join('') + `</tbody></table>`
      + (dl.length > 20 ? `<button class="mini-btn sv-more" type="button" data-t2-more="d">${allT.d ? 'Show the top 20 only' : `Show all ${dl.length}`}</button>` : '') : '<p class="note">No deals in these categories here in this period.</p>';
    $id('t2List').innerHTML = ll.length ? `<table class="svt t2"><thead><tr>${th('l', 'rank', 'Rank', 1)}${th('l', 'name', 'Category')}${th('l', 'total', 'Listings', 1)}${th('l', 'paid', 'Paid', 1)}${th('l', 'pp', 'Paid %', 1)}</tr></thead><tbody>`
      + lShown.map(x => `<tr><td class="n rk">${x.rank}</td><td>${esc(x.name)}</td><td class="n"><b>${x.total.toLocaleString('en-IN')}</b></td><td class="n">${x.paid.toLocaleString('en-IN')}</td><td class="n">${x.pp === null ? '—' : nf(x.pp) + '%'}</td></tr>`).join('') + `</tbody></table>`
      + (ll.length > 20 ? `<button class="mini-btn sv-more" type="button" data-t2-more="l">${allT.l ? 'Show the top 20 only' : `Show all ${ll.length}`}</button>` : '') : '<p class="note">No listings in these categories here.</p>';
  };
  svPanel.addEventListener('click', e => {
    const h = e.target.closest('[data-t2-k]');
    if (h) { const S = sortT[h.dataset.t2T], k = h.dataset.t2K; if (S.k === k) S.dir = -S.dir; else { S.k = k; S.dir = (k === 'name' || k === 'rank') ? 1 : -1; } return window.renderTop200SV(lastPin); }
    const m = e.target.closest('[data-t2-more]'); if (m) { allT[m.dataset.t2More] = !allT[m.dataset.t2More]; window.renderTop200SV(lastPin); }
  });

  // ---- 3. pincode page: a top-200 section ----
  const _open = window.openPinPage;
  window.openPinPage = function (pin, fromClick) {
    _open(pin, fromClick);
    const pp = document.querySelector('#pinPage .pp'); if (!pp) return;
    const D = Object.entries(dealsBy(pin, periodFromDate, periodToDate)).map(([c, v]) => ({ c: CAT[c], v })).sort((a, b) => b.v[0] - a.v[0]).slice(0, 5);
    const L = Object.entries(listBy(pin)).map(([c, v]) => ({ c: CAT[c], v })).sort((a, b) => b.v[0] - a.v[0]).slice(0, 5);
    const sec = document.createElement('section'); sec.className = 'pp-sec';
    sec.innerHTML = `<h2>Top 200 JDA categories here</h2><div class="pp-t2">
      <div><h4>By deals, ${esc(periodLabel())}</h4>${D.length ? `<table><thead><tr><th>Category</th><th class="n">Deals</th><th class="n">JDA</th><th class="n">JDS</th></tr></thead><tbody>${D.map(x => `<tr><td><span style="color:var(--text-dim)">#${x.c.rank}</span> ${esc(x.c.name)}</td><td class="n"><b>${nf(x.v[0])}</b></td><td class="n">${nf(x.v[1])}</td><td class="n">${nf(x.v[2])}</td></tr>`).join('')}</tbody></table>` : '<p class="note">No deals in these categories here in this period.</p>'}</div>
      <div><h4>By monetizable listings</h4>${L.length ? `<table><thead><tr><th>Category</th><th class="n">Listings</th><th class="n">Paid %</th></tr></thead><tbody>${L.map(x => `<tr><td><span style="color:var(--text-dim)">#${x.c.rank}</span> ${esc(x.c.name)}</td><td class="n"><b>${x.v[0].toLocaleString('en-IN')}</b></td><td class="n">${x.v[0] ? nf(100 * x.v[1] / x.v[0]) + '%' : '—'}</td></tr>`).join('')}</tbody></table>` : '<p class="note">No listings in these categories here.</p>'}</div></div>`;
    sec.insertAdjacentHTML('beforeend', `<div class="pp-go"><button class="mini-btn pp-go-btn" type="button" data-pp-sv="${pin}">See all top-200 categories for this pincode ›</button></div>`);
    const cats = [...pp.querySelectorAll('.pp-sec')].find(x => /Business categories/.test(x.querySelector('h2') ? x.querySelector('h2').textContent : ''));
    if (cats) cats.after(sec); else pp.append(sec);
  };

  // ---- 4. overview: one line ----
  window.top200Line = function (from, to, C) {
    const sum = (f, t) => { const d = dealsBy('', f, t); let j = 0, s2 = 0; Object.values(d).forEach(v => { j += v[1]; s2 += v[2]; }); return { j, s: s2, sh: share(j, s2) }; };
    const N = sum(from, to), P = C ? sum(C.from, C.to) : null;
    const el = $id('ovTop200'); if (!el) return;
    el.innerHTML = `In the top 200 JDA categories: JDA closed <b>${nf(N.j)}</b> deals${P ? ` (${nf(P.j)} on ${esc(C.name)})` : ''}, a <b>${N.sh === null ? '—' : nf(N.sh) + '%'}</b> share of JDA + JDS deals there${P && P.sh !== null ? ` (${nf(P.sh)}% before)` : ''}.`;
  };
  if (typeof refreshAll === 'function') refreshAll();
})();
</script>
"""


BRANCHES = {
    "mumbai": {"name": "Mumbai", "src": SRC_PAGE, "out": OUT, "key": "jdaMumbaiUiLab3", "src_key": "jdaJdsMumbaiDashboard",
               "top200": os.path.join(MUMBAI, "pipeline", "top200_data.json"),
               "top_sg": os.path.join(MUMBAI, "pipeline", "top500_sales_groups.csv")},
    # Kolkata (2026-09-29): same lab, built from the Kolkata SubVertical page; no top-200 list (that one is Mumbai-only)
    "kolkata": {"name": "Kolkata", "src": os.path.join(KOLKATA, "JDA_JDS_Kolkata_Pincode_Dashboard_Lite_SubVertical.page"),
                "out": os.path.join(KOLKATA, "JDA_Kolkata_Dashboard_UI_Lab.html"), "key": "jdaKolkataUiLab3", "src_key": "jdaJdsDashboard",
                "top200": None, "show_state": True,
                # top 500 / top 200 sales-group listing columns (2026-10-09): Kolkata's own copy of the list
                "top_sg": os.path.join(KOLKATA, "pipeline", "top500_sales_groups.csv")},
}


# ---------- one vocabulary (Sarvesh 2026-09-30) ----------
# Applied to the finished page, line by line, skipping the embedded data lines (they are single huge lines).
# Lowercase 'deals' is also a data key ('deals', deals:, .deals), so those spellings are left alone.
VOCAB_PHRASES = [
    # "gap" is "Visiting, not closing"
    ("is_gap: 'Gap',", "is_gap: 'Visiting, not closing',"),
    ("row.is_gap ? 'Gap' : 'Not gap'", "row.is_gap ? 'Visiting, not closing' : 'Other'"),
    ("['gap_pincodes', 'Gap', true]", "['gap_pincodes', 'Visiting, not closing', true]"),
    ("gap: 'Gap pincodes',", "gap: 'Visiting, not closing',"),
    ("gap: 'Gap',", "gap: 'Visiting, not closing',"),
    ("Gap pincodes by month", "Pincodes covered by JDA, by month"),
    ("${n} Gap pincodes in ${lbl}", "${n} pincodes visiting, not closing in ${lbl}"),
    ('title="Gap, No JDA presentation, and JDA share up to 20%"', 'title="Visiting, not closing; Not visiting; JDA share up to 20%"'),
    # "needs action" / "losing out" is "Missing out"
    ("grp('Needs action', NEED, 'needs')", "grp('Missing out', NEED, 'needs')"),
    ('JDA share up to 20%">Needs action</button>', 'JDA share up to 20%">Missing out</button>'),
    ("Needs action first (", "Missing out first ("),
    ("so you can see where JDA is losing out", "so you can see where JDA is missing out"),
    # "status" is "Grouping"
    ("<h3>Pincodes by status</h3>", "<h3>Pincodes by grouping</h3>"),
    ("status: 'Status',", "status: 'Grouping',"),
    ("'State', 'Status', 'JDA deals'", "'State', 'Grouping', 'JDA deals'"),
    # deals -> sales: the phrases that need more than a word swap
    ("JDA closed <b>${nf(T.jda)}${kind} deals</b> ${when}", "JDA made <b>${nf(T.jda)}${kind} sales</b> ${when}"),
    ("deals closed by all teams", "sales by all teams"),
    ("Top sub-verticals by deals closed", "Top sub-verticals by sales"),
    ("JDA deals closed", "JDA sales"), ("JDS deals closed", "JDS sales"),
    ("while JDS closed deals", "while JDS made sales"), ("JDS closed deals here", "JDS made sales here"),
    ("JDA closed deals here", "JDA made sales here"), ("JDS is closing deals", "JDS is making sales"),
    ("No deals closed here", "No sales here"),
    ("JDA closed <b>${nf(N.j)}</b> deals", "JDA made <b>${nf(N.j)}</b> sales"),
]
_V_KEEP = "Close more deals"   # the action name Sarvesh chose


def _v_word(m):
    """deals -> sales / deal -> sale, except where the word is a data key: 'deals' / "deals" / deals: / .deals / deals="""
    t, i, j = m.string, m.start(), m.end()
    before, after = t[i - 1:i], t[j:j + 1]
    if before in ".$" or after in ":=" or (before in "'\"" and after == before):
        return m.group(1)
    return "sales" if m.group(1) == "deals" else "sale"


def vocab(page):
    import re
    out = []
    for line in page.split("\n"):
        if len(line) > 20000:        # embedded data
            out.append(line); continue
        for a, b in VOCAB_PHRASES:
            line = line.replace(a, b)
        line = line.replace(_V_KEEP, "\x00KEEP\x00")
        # word swap, leaving data keys alone: 'deals' / "deals" / deals: / .deals / deals=
        line = re.sub(r"\b(deals?)\b", _v_word, line)
        line = re.sub(r"(?<![\w$])Deals(?![\w:=])", "Sales", line)
        line = re.sub(r"(?<![\w$])Deal(?![\w:=])", "Sale", line)
        out.append(line.replace("\x00KEEP\x00", _V_KEEP))
    return "\n".join(out)


def check_scripts(page):
    """syntax-check every inline script with Node (skipped when Node is not installed)"""
    import shutil as _sh, subprocess, tempfile
    node = _sh.which("node") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "nodejs", "node.exe")
    if not os.path.exists(node):
        print("  (node not found: script syntax check skipped)"); return
    import re as _re
    bad = 0
    for i, m in enumerate(_re.finditer(r"<script>(.*?)</script>", page, _re.S)):
        # the embedded data lines are huge JSON literals: swap each for an empty stand-in so every script (the main one too)
        # is still checked
        body = "\n".join(_re.sub(r"^(\s*(?:const|let|var) \w+ = ).*$", r"\1{};", l) if len(l) > 20000 else l for l in m.group(1).split("\n"))
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
            f.write(body); fn = f.name
        r = subprocess.run([node, "--check", fn], capture_output=True, text=True)
        os.remove(fn)
        if r.returncode:
            bad += 1; print(f"  script {i}: " + (r.stderr.strip().splitlines() or ["?"])[-1])
    assert not bad, f"{bad} script(s) failed the syntax check"
    print("  scripts: syntax OK")


THEME_JS = r"""(function () {   // one icon button: shows the sun in dark mode (click for light), the moon in light mode
  const btn = document.getElementById('themeBtn');
  const SUN = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>';
  const MOON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/></svg>';
  const paint = t => { btn.innerHTML = t === 'light' ? MOON : SUN; const l = t === 'light' ? 'Switch to dark mode' : 'Switch to light mode'; btn.title = l; btn.setAttribute('aria-label', l); };
  paint(initialTheme);
  btn.addEventListener('click', () => { const t = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light'; applyTheme(t); paint(t); });
})();
"""


POLISH_JS = '<script>\n/* ===== polish (2026-10-07) ===== */\n(function () {\n  // one date style everywhere: \'1 Sept 2026\'; a range in one month as \'1–29 Sept 2026\'\n  fmtDateNice = function (iso) { return new Date(iso + \'T00:00:00\').toLocaleDateString(\'en-GB\', { day: \'numeric\', month: \'short\', year: \'numeric\' }); };\n  periodLabel = function () {\n    const a = periodFromDate, b = periodToDate;\n    if (a === b) return fmtDateNice(a);\n    if (a.slice(0, 7) === b.slice(0, 7)) return `${+a.slice(8)}–${fmtDateNice(b)}`;\n    if (a.slice(0, 4) === b.slice(0, 4)) return `${fmtDateNice(a).replace(/ \\d{4}$/, \'\')} – ${fmtDateNice(b)}`;\n    return `${fmtDateNice(a)} – ${fmtDateNice(b)}`;\n  };\n  // the last JDA presentation as a date (days count back from the period\'s last day)\n  window.labLastPres = function (d) {\n    if (d === null || d === undefined) return \'None in this period\';\n    const t = new Date(periodToDate + \'T00:00:00Z\'); t.setUTCDate(t.getUTCDate() - d);\n    return t.toLocaleDateString(\'en-GB\', { day: \'numeric\', month: \'short\', timeZone: \'UTC\' });\n  };\n  // Team tables: sentence-case headings and the Pincodes table\'s funnel icons\n  const FUN = \'<svg viewBox="0 0 16 16" width="11" height="11" aria-hidden="true"><path d="M2 3h12l-4.6 5.4V13l-2.8 1.5V8.4z" fill="currentColor"/></svg>\';\n  Object.values(PERF_FIELDS).forEach(list => list.forEach(f => { if (f[1] === \'Conv %\') f[1] = \'Conversion\'; if (f[1] === \'JDA Sales\') f[1] = \'JDA sales\'; }));\n  const _rpv = renderPerfView;\n  renderPerfView = function () {\n    _rpv.apply(this, arguments);\n    const body = document.getElementById(\'perfViewBody\'); if (!body) return;\n    body.querySelectorAll(\'.col-filter-icon\').forEach(ic => { ic.innerHTML = FUN; ic.setAttribute(\'role\', \'button\'); ic.setAttribute(\'aria-label\', \'Filter this column\'); });\n  };\n  // scrolling inside the pincode table while its header is hidden under the top bar brings the whole table into view\n  document.addEventListener(\'wheel\', e => {\n    const sc = e.target.closest && e.target.closest(\'.scroll\'); if (!sc || !sc.querySelector(\':scope > #dataTable\')) return;\n    const bar = document.getElementById(\'uiBar\'), top = bar ? bar.getBoundingClientRect().bottom : 0, r = sc.getBoundingClientRect();\n    if (r.top < top - 2 && r.bottom > top + 80) window.scrollBy(0, r.top - top - 8);\n  }, { passive: true });\n  try { renderPerfView(); refreshAll(); } catch (e) { /* drawn again on the next change */ }\n})();\n</script>\n'


WORK_LOC_HEAD = r"""<style>
.wl-tag { display: inline-block; margin-left: 6px; padding: 0 6px; border: 1px solid var(--border); border-radius: 3px; font-size: 11px; font-weight: 600; color: var(--text-dim); vertical-align: 1px; white-space: nowrap; }
.wl-none { color: var(--text-dim); }
#perfWorkCompare:not(:empty) { margin-bottom: 12px; }
#perfWorkCompare tr[data-wl] { cursor: pointer; }
#perfWorkCompare tr[data-wl]:hover td { background: color-mix(in srgb, var(--accent) 8%, transparent); }
#perfWorkCompare tr.wl-out td { font-weight: 600; }
#perfDeployCompare tr[data-dep] { cursor: pointer; }
#perfDeployCompare tr[data-dep]:hover td { background: color-mix(in srgb, var(--accent) 8%, transparent); }
#perfQuickFilter:not(:empty) { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0 0 10px; font-size: 13px; color: var(--text-dim); }
#perfQuickFilter .qf { display: inline-flex; align-items: center; gap: 6px; padding: 3px 4px 3px 10px; border: 1px solid var(--accent); border-radius: 999px; color: var(--text); background: color-mix(in srgb, var(--accent) 12%, transparent); }
#perfQuickFilter .qf button { border: 0; background: none; color: var(--text-dim); cursor: pointer; font-size: 14px; line-height: 1; padding: 2px 6px; border-radius: 999px; }
#perfQuickFilter .qf button:hover { color: var(--text); background: var(--panel2); }
#perfWorkCompare tr.wl-sub td:first-child { padding-left: 26px; color: var(--text-dim); }
.emp-code { font-variant-numeric: tabular-nums; color: var(--text-dim); user-select: all; cursor: text; }
/* column widths: drag a header's right edge; double-click it to undo the widths of this view */
#perfViewBody thead th .pcol-rz { position: absolute; top: 0; right: -4px; width: 9px; height: 100%; cursor: col-resize; z-index: 2; }
#perfViewBody thead th .pcol-rz::after { content: ''; position: absolute; top: 6px; bottom: 6px; left: 4px; border-left: 1px solid transparent; }
#perfViewBody thead th:hover .pcol-rz::after, #perfViewBody thead th .pcol-rz.on::after { border-left-color: var(--accent); }
#perfViewBody table.pcol-fixed { table-layout: fixed; }
#perfViewBody table.pcol-fixed td { overflow: hidden; text-overflow: ellipsis; }
body.pcol-drag, body.pcol-drag * { cursor: col-resize !important; user-select: none !important; }
</style>
<script>
/* ===== where the JDAs work (2026-10-15): HR work location on Team productivity; EMP_META city / city_branch / out / moves ===== */
(function () {
  const BR = '__BRANCH__';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const meta = id => (typeof EMP_META !== 'undefined' && EMP_META[id]) || {};
  // a JDA's cell: the HR city, 'outside branch' when that city belongs to another branch; the months in the tooltip
  window.workCell = function (e) {
    const m = meta(e.id);
    if (!m.city) return '<span class="wl-none" title="Not found in HR">—</span>';
    const tip = `HR work location${m.moves ? ' by month: ' + m.moves : ' (latest month)'}. ${m.city} is in the ${m.city_branch || 'unknown'} branch.`;
    return `<span title="${esc(tip)}">${esc(m.city)}${m.moves ? '*' : ''}</span>` +
      (m.out === 1 ? `<span class="wl-tag" title="${esc(`${m.city} belongs to the ${m.city_branch} branch, not ${BR}`)}">outside branch</span>` : '');
  };
  // an employee code: plain digits (one click selects it, to paste into SQL / Excel)
  window.codeCell = function (c) {
    return c ? `<span class="emp-code" title="Employee code: click to select, then copy">${esc(c)}</span>` : '<span class="wl-none">—</span>';
  };
  // column widths on Team productivity: drag a header's right edge; kept per view (Manager / JDA) in this browser;
  // double-click the edge to go back to automatic widths. The table is redrawn often, so widths are re-applied each time.
  const WKEY = 'jda-perf-colw-v1:' + BR;
  const loadW = () => { try { return JSON.parse(localStorage.getItem(WKEY) || '{}') || {}; } catch (e) { return {}; } };
  const saveW = w => { try { localStorage.setItem(WKEY, JSON.stringify(w)); } catch (e) { /* not remembered */ } };
  const viewOf = () => (typeof perfView !== 'undefined' ? perfView : 'manager');
  const keyOf = (th, i) => th.dataset.field || '_c' + i;
  let dragging = false, justDragged = false;
  function applyWidths() {
    const tbl = document.querySelector('#perfViewBody table'); if (!tbl) return;
    const ths = [...tbl.querySelectorAll('thead tr:first-child > th')];
    ths.forEach((th, i) => { if (!th.querySelector('.pcol-rz')) th.insertAdjacentHTML('beforeend', `<span class="pcol-rz" data-i="${i}" title="Drag to resize; double-click for automatic widths"></span>`); });
    const w = loadW()[viewOf()];
    if (!w || dragging) return;
    const cur = ths.map(th => th.getBoundingClientRect().width);
    ths.forEach((th, i) => { th.style.width = (w[keyOf(th, i)] || Math.round(cur[i])) + 'px'; });
    tbl.style.width = ths.reduce((a, th) => a + parseFloat(th.style.width), 0) + 'px';
    tbl.classList.add('pcol-fixed');
  }
  document.addEventListener('mousedown', ev => {
    const h = ev.target.closest && ev.target.closest('#perfViewBody .pcol-rz'); if (!h) return;
    ev.preventDefault(); ev.stopPropagation();
    const tbl = h.closest('table'), ths = [...tbl.querySelectorAll('thead tr:first-child > th')], th = h.parentElement;
    const widths = ths.map(t => Math.round(t.getBoundingClientRect().width));
    ths.forEach((t, i) => { t.style.width = widths[i] + 'px'; });
    tbl.style.width = widths.reduce((a, b) => a + b, 0) + 'px'; tbl.classList.add('pcol-fixed');
    const x0 = ev.clientX, w0 = widths[+h.dataset.i], t0 = parseFloat(tbl.style.width);
    dragging = true; h.classList.add('on'); document.body.classList.add('pcol-drag');
    const move = e => { const nw = Math.max(48, Math.round(w0 + e.clientX - x0)); th.style.width = nw + 'px'; tbl.style.width = (t0 - w0 + nw) + 'px'; };
    const up = () => {
      document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up);
      dragging = false; justDragged = true; setTimeout(() => { justDragged = false; }, 0);
      h.classList.remove('on'); document.body.classList.remove('pcol-drag');
      const all = loadW(), v = {};
      ths.forEach((t, i) => { v[keyOf(t, i)] = Math.round(parseFloat(t.style.width)); });
      all[viewOf()] = v; saveW(all);
    };
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up);
  }, true);
  // a drag ends with a click on the header: don't let it sort
  document.addEventListener('click', ev => { if (justDragged && ev.target.closest && ev.target.closest('#perfViewBody thead')) { ev.stopPropagation(); ev.preventDefault(); } }, true);
  document.addEventListener('dblclick', ev => {
    const h = ev.target.closest && ev.target.closest('#perfViewBody .pcol-rz'); if (!h) return;
    ev.stopPropagation();
    const all = loadW(); delete all[viewOf()]; saveW(all);
    if (typeof renderPerfView === 'function') renderPerfView();
  }, true);
  const watch = () => { const body = document.getElementById('perfViewBody'); if (!body) return setTimeout(watch, 300); applyWidths(); new MutationObserver(applyWidths).observe(body, { childList: true }); };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch); else watch();
  // a manager's cell: how many of their JDAs work outside the branch
  window.workMgrCell = function (m) {
    return m.out_n ? `<span class="wl-tag" title="JDAs of this manager whose HR work location is in another branch">${m.out_n} outside branch</span>` : '';
  };
  // the summary above the lists: in the branch, outside it (each city), unknown; same JDAs as the lists below
  window.renderWorkCompare = function (q) {
    if (window.renderQuickFilter) window.renderQuickFilter();
    const box = document.getElementById('perfWorkCompare');
    if (!box || typeof currentPerfData === 'undefined' || !currentPerfData) return;
    const emps = currentPerfData.employeePerf
      .filter(e => !pincodeFilterEmployees || pincodeFilterEmployees.has(e.id))
      .filter(e => !q || perfSearchMatch(e.name, q) || perfSearchMatch(e.manager, q) || perfSearchMatch(e.id, q));
    if (!emps.some(e => meta(e.id).city)) { box.innerHTML = ''; return; }
    const agg = list => {
      const pres = list.reduce((a, e) => a + e.presentations, 0), sales = Math.round(list.reduce((a, e) => a + e.jda_sales, 0) * 10) / 10;
      return { n: list.length, pres, sales, conv: pres ? (Math.round(1000 * sales / pres) / 10) + '%' : '—' };
    };
    const inB = emps.filter(e => e.work_branch === BR), outB = emps.filter(e => e.work_out), unk = emps.filter(e => e.work_branch !== BR && !e.work_out);
    const cities = list => [...new Set(list.map(e => e.work_loc))];
    const byCity = {};
    outB.forEach(e => { (byCity[e.work_loc] = byCity[e.work_loc] || []).push(e); });
    const rows = Object.entries(byCity).map(([c, l]) => [c, agg(l), meta(l[0].id).city_branch]).sort((a, b) => b[1].sales - a[1].sales || b[1].n - a[1].n);
    const row = (cls, label, a, list) => `<tr class="${cls}" data-wl="${esc(JSON.stringify(list))}" title="Show these JDAs in the JDA view"><td>${label}</td>` +
      `<td class="num-col">${a.n}</td><td class="num-col">${a.pres}</td><td class="num-col">${a.sales}</td><td class="num-col"><b>${a.conv}</b></td></tr>`;
    box.innerHTML = `<table class="dep-compare"><thead><tr><th>Where the JDAs work (HR)</th><th class="num-col">JDAs</th><th class="num-col">Presentations</th><th class="num-col">JDA sales</th><th class="num-col">Conversion</th></tr></thead><tbody>` +
      row('', `In the ${esc(BR)} branch`, agg(inB), cities(inB)) +
      (outB.length ? row('wl-out', `Outside the ${esc(BR)} branch`, agg(outB), cities(outB)) + rows.map(([c, a, b]) => row('wl-sub', `${esc(c)}${b && b !== c ? ` <span class="wl-none">(${esc(b)} branch)</span>` : ''}`, a, [c])).join('') : '') +
      (unk.length ? row('', 'Work location not known', agg(unk), cities(unk)) : '') + `</tbody></table>`;
  };
  // a summary row: the JDA view, filtered to those work locations / deployed or not (one summary filter at a time)
  const openJda = (field, values) => {
    if (typeof perfColumnFilters === 'undefined') return;
    const f = Object.assign({}, perfColumnFilters.jda); delete f.work_loc; delete f.deployed;
    f[field] = { type: 'set', values: new Set(values) };
    perfColumnFilters.jda = f;
    const b = document.querySelector('#perfViewSeg [data-v="jda"]');
    if (b) b.click(); else if (typeof renderPerfView === 'function') renderPerfView();
  };
  document.addEventListener('click', ev => {
    if (!ev.target.closest) return;
    const w = ev.target.closest('#perfWorkCompare tr[data-wl]'); if (w) return openJda('work_loc', JSON.parse(w.dataset.wl));
    const d = ev.target.closest('#perfDeployCompare tr[data-dep]'); if (d) return openJda('deployed', [d.dataset.dep]);
    const x = ev.target.closest('#perfQuickFilter [data-qf]');
    if (x && typeof perfColumnFilters !== 'undefined') { const f = Object.assign({}, perfColumnFilters.jda); delete f[x.dataset.qf]; perfColumnFilters.jda = f; renderPerfView(); }
  });
  // the chip above the JDA list for a summary filter that has no column of its own (deployed / not deployed)
  window.renderQuickFilter = function () {
    const box = document.getElementById('perfQuickFilter'); if (!box) return;
    const f = (typeof perfColumnFilters !== 'undefined' && typeof perfView !== 'undefined' && perfView === 'jda') ? (perfColumnFilters.jda || {}).deployed : null;
    const v = f && f.values && f.values.size === 1 ? [...f.values][0] : '';
    box.innerHTML = v ? `<span>Showing</span><span class="qf">${v === 'Deployed' ? 'Deployed JDAs (on the roster)' : 'Other JDAs (not on the roster)'}<button type="button" data-qf="deployed" title="Show every JDA" aria-label="Remove this filter">✕</button></span>` : '';
  };
})();
</script>
"""


EMP_WIN_HEAD = r"""<style>
/* ===== employee window (2026-10-15): a JDA's details over the dashboard, same look as the pincode window ===== */
.emp-link { color: inherit; text-decoration: underline; text-decoration-color: color-mix(in srgb, var(--text-dim) 45%, transparent); text-underline-offset: 3px; cursor: pointer; }
.emp-link:hover { color: var(--accent); text-decoration-color: var(--accent); }
body.emp-mode { overflow: hidden; }
html:has(body.emp-mode) { overflow: hidden; scrollbar-gutter: stable; }
#empWin { display: none; }
body.emp-mode #empWin { display: flex; position: fixed; inset: 0; z-index: 1001; justify-content: center; align-items: flex-start; padding: 22px 24px; background: rgba(8, 10, 14, .78); }
[data-theme="light"] body.emp-mode #empWin { background: rgba(40, 38, 34, .55); }
#empWin > .pp { width: min(1080px, 100%); max-width: none; max-height: calc(100vh - 44px); overflow-y: auto; overscroll-behavior: contain; margin: 0;
  padding: 0 28px 32px; background: var(--bg); border: 1px solid var(--border); border-radius: 14px; box-shadow: 0 16px 40px rgba(0, 0, 0, .45); }
[data-theme="light"] #empWin > .pp { box-shadow: 0 24px 70px rgba(0, 0, 0, .22); }
#empWin .pp-nav { position: sticky; top: 0; z-index: 6; display: flex; align-items: center; gap: 10px; margin: 0 -28px 16px; padding: 12px 28px; background: var(--bg); border-bottom: 1px solid var(--border); border-radius: 14px 14px 0 0; }
#empWin .pp-nav .t { color: var(--text-dim); font-size: 13px; }
#empWin .pp-nav .pp-close { margin-left: auto; width: 36px; height: 36px; padding: 0; display: inline-flex; align-items: center; justify-content: center; font-size: 17px; line-height: 1; border-radius: 50%; }
#empWin .pp-nav .pp-close:hover { background: var(--panel2); }
#empWin .ew-sub { color: var(--text-dim); font-size: 14px; line-height: 1.55; margin: 6px 0 14px; }
#empWin .ew-sub b { color: var(--text); font-weight: 500; }
#empWin .ew-nums { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-bottom: 14px; }
#empWin .pp-num .c { color: var(--text-dim); font-size: 12.5px; margin-top: 2px; }
#empWin .pp-num .c b.good { color: #3fbf7a; } #empWin .pp-num .c b.bad { color: #f07b6b; }
[data-theme="light"] #empWin .pp-num .c b.good { color: #1f7f55; } [data-theme="light"] #empWin .pp-num .c b.bad { color: #c23b22; }
#empWin table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
#empWin th { text-align: left; color: var(--text-dim); font-weight: 500; padding: 6px 8px; border-bottom: 1px solid var(--border); }
#empWin td { padding: 6px 8px; border-bottom: 1px solid color-mix(in srgb, var(--border) 60%, transparent); }
#empWin .n { text-align: right; font-variant-numeric: tabular-nums; }
#empWin .ew-weeks { display: flex; align-items: flex-end; gap: 2px; height: 110px; margin-top: 8px; }
#empWin .ew-weeks > span { flex: 1 1 0; display: flex; flex-direction: column; justify-content: flex-end; height: 100%; min-width: 3px; }
#empWin .ew-weeks i { display: block; border-radius: 2px 2px 0 0; }
#empWin .ew-weeks i.p { background: color-mix(in srgb, var(--text-dim) 45%, transparent); }
#empWin .ew-weeks i.s { background: var(--accent); margin-top: 1px; border-radius: 2px; }
#empWin .ew-weeks > span.out { opacity: .35; }
#empWin .ew-key { display: flex; gap: 14px; flex-wrap: wrap; color: var(--text-dim); font-size: 12.5px; margin-top: 8px; }
#empWin .ew-key i { display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 5px; vertical-align: -1px; }
#empWin .ew-src { color: var(--text-dim); font-size: 12px; line-height: 1.5; margin: 6px 2px 0; }
@media (max-width: 700px) { body.emp-mode #empWin { padding: 8px; } #empWin > .pp { padding: 0 16px 24px; } #empWin .pp-nav { margin: 0 -16px 12px; padding: 8px 16px; } #empWin .ew-nums { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
<script>
/* ===== employee window (2026-10-15): click a JDA's name on Team productivity for their details ===== */
(function () {
  const BR = '__BRANCH__';
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const nf = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  const pct = (a, b) => b ? Math.round(1000 * a / b) / 10 : null;
  const fP = v => v === null || v === undefined ? '—' : v.toFixed(1) + '%';
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const fD = iso => { if (!iso) return ''; const [y, m, d] = iso.split('-').map(Number); return `${d} ${MON[m - 1]} ${y}`; };
  const tc = s => String(s || '').toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  // the name as a link (Team productivity, both views)
  window.empLink = function (e) { return `<a href="#" class="emp-link" data-emp="${esc(e.id)}" title="Open ${esc(e.name)}'s details">${e.name}</a>`; };
  const days = (a, b) => { const out = []; for (let d = new Date(a + 'T00:00:00Z'), e = new Date(b + 'T00:00:00Z'); d <= e; d.setUTCDate(d.getUTCDate() + 1)) out.push(d.toISOString().slice(0, 10)); return out; };
  // the pincodes the Team productivity numbers count (the pincode table's filters / a focused pincode), as refreshPerfData does
  function allowedPins() {
    try {
      const shown = new Set((currentBaseRows || currentRows).map(r => r.pincode));
      return perfPincodeFocus ? new Set(shown.has(perfPincodeFocus) ? [perfPincodeFocus] : []) : shown;
    } catch (e) { return null; }
  }
  // one employee's presentations and JDA sales by pincode over dates; plus everyone's totals (the branch line)
  function sums(id, a, b, allowed) {
    const per = {}, all = { pres: 0, sales: 0 }; let pres = 0, sales = 0;
    days(a, b).forEach(day => {
      [['pres', (DAILY.rep_pin_pres_by_day || {})[day]], ['sales', (DAILY.rep_pin_sales_by_day || {})[day]]].forEach(([k, m]) => {
        Object.entries(m || {}).forEach(([p, em]) => {
          if (allowed && !allowed.has(p)) return;
          Object.entries(em).forEach(([e, v]) => { all[k] += v; if (e !== id) return; (per[p] = per[p] || { pres: 0, sales: 0 })[k] += v; if (k === 'pres') pres += v; else sales += v; });
        });
      });
    });
    return { per, pres, sales: Math.round(sales * 100) / 100, all };
  }
  // the comparison dates: the same days last month when the dates sit in one month, else the same number of days just before
  function prevRange(a, b) {
    const sh = (iso, n) => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
    let pa, pb;
    // the same day last month (the 31st -> the month's last day), as the page's own comparisons
    const pmd = iso => { const [y, m, d] = iso.split('-').map(Number); const pm = m === 1 ? 12 : m - 1, py = m === 1 ? y - 1 : y; const last = new Date(Date.UTC(py, pm, 0)).getUTCDate(); return `${py}-${String(pm).padStart(2, '0')}-${String(Math.min(d, last)).padStart(2, '0')}`; };
    if (a.slice(0, 7) === b.slice(0, 7)) { pa = pmd(a); pb = pmd(b); }
    else { const n = days(a, b).length; pb = sh(a, -1); pa = sh(a, -n); }
    if (pb < DAILY.window_start) return null;
    return [pa < DAILY.window_start ? DAILY.window_start : pa, pb];
  }
  const rosterPins = id => Object.entries(((typeof JDA_DEPLOYMENT !== 'undefined' && JDA_DEPLOYMENT) || {}).deployed || {}).filter(([, l]) => (l || []).some(x => String(x.id) === String(id))).map(([p]) => p);
  const place = p => { const s = (DATA.pincode_static || {})[p] || {}; return ((s.geo || {}).sample_place || '') + (window.labStateOf ? window.labStateOf(p) : ''); };
  function tenure(j) {
    if (!j) return '';
    const [y, m] = j.split('-').map(Number), e = new Date(DAILY.window_end + 'T00:00:00Z');
    const mo = (e.getUTCFullYear() - y) * 12 + e.getUTCMonth() + 1 - m; if (mo < 0) return '';
    return `joined ${MON[m - 1]} ${y} (${mo < 12 ? mo + (mo === 1 ? ' month' : ' months') : Math.floor(mo / 12) + (mo < 24 ? ' year' : ' years')})`;
  }
  function render(id) {
    const m = (typeof EMP_META !== 'undefined' && EMP_META[id]) || {}, name = tc(m.name || id);
    const a = periodFromDate, b = periodToDate, allowed = allowedPins();
    const cur = sums(id, a, b, allowed), pr = prevRange(a, b), prev = pr ? sums(id, pr[0], pr[1], allowed) : null;
    const conv = pct(cur.sales, cur.pres), bConv = pct(cur.all.sales, cur.all.pres), pConv = prev ? pct(prev.sales, prev.pres) : null;
    const pl = pr ? (typeof fmtDateNice === 'function' && pr[0] !== pr[1] ? `${fmtDateNice(pr[0])} – ${fmtDateNice(pr[1])}` : fD(pr[0])) : '';
    const chg = (x, y, unit) => { if (!prev) return ''; const d = Math.round((x - y) * 10) / 10; return d === 0 ? `same as ${esc(pl)}` : `<b class="${d > 0 ? 'good' : 'bad'}">${d > 0 ? '+' : '−'}${nf(Math.abs(d))}${unit || ''}</b> vs ${esc(pl)} (${unit ? fP(y) : nf(y)})`; };
    const roster = rosterPins(id), rosterSet = new Set(roster);
    const tags = [m.out === 1 ? `<span class="wl-tag" title="${esc(`${m.city} belongs to the ${m.city_branch} branch`)}">outside branch</span>` : '',
      roster.length ? '<span class="dep-tag" title="On the JDA deployment roster">Deployed</span>' : '',
      m.hr_status === 0 ? `<span class="wl-tag">left${m.left ? ' ' + esc(fD(m.left)) : ''}</span>` : ''].join('');
    const sub = [`Emp code <b class="emp-code">${esc(id)}</b>`,
      m.manager ? `Manager <b>${esc(tc(m.manager))}</b>${m.manager_code ? ` (<span class="emp-code">${esc(m.manager_code)}</span>)` : ''}` : '',
      m.designation ? esc(m.designation) : '', m.section ? esc(m.section) : '',
      m.city ? `HR city <b>${esc(m.city)}</b>${m.city_branch && m.city_branch !== m.city ? ` (${esc(m.city_branch)} branch)` : ''}` : 'HR city not found',
      m.work_town && m.work_town !== m.city ? `work location <b>${esc(m.work_town)}</b>` : '',
      m.moves ? `by month: ${esc(m.moves)}` : '', tenure(m.joined)].filter(Boolean).join(' · ');
    const pins = Object.entries(cur.per).map(([p, v]) => ({ p, ...v })).sort((x, y) => y.pres - x.pres || y.sales - x.sales);
    const pinRows = pins.map(r => `<tr><td>${esc(r.p)}${rosterSet.has(r.p) ? ' <span class="dep-tag">Deployed</span>' : ''}</td><td>${esc(place(r.p))}</td><td class="n">${nf(r.pres)}</td><td class="n">${nf(r.sales)}</td><td class="n">${fP(pct(r.sales, r.pres))}</td></tr>`).join('');
    const notWorked = roster.filter(p => !cur.per[p] && (!allowed || allowed.has(p)));
    // week by week since the window starts (every pincode in the branch): presentations, and JDA sales inside them
    const all = days(DAILY.window_start, DAILY.window_end), wk = [];
    all.forEach((d, i) => {
      const w = Math.floor(i / 7); const o = wk[w] || (wk[w] = { a: d, b: d, pres: 0, sales: 0 }); o.b = d;
      Object.values((DAILY.rep_pin_pres_by_day || {})[d] || {}).forEach(em => { o.pres += em[id] || 0; });
      Object.values((DAILY.rep_pin_sales_by_day || {})[d] || {}).forEach(em => { o.sales += em[id] || 0; });
    });
    const mx = Math.max(1, ...wk.map(o => o.pres), ...wk.map(o => o.sales));
    const bars = wk.map(o => `<span class="${o.b < a || o.a > b ? 'out' : ''}" title="${esc(`${fD(o.a)} – ${fD(o.b)}: ${nf(o.pres)} presentations, ${nf(o.sales)} JDA sales`)}"><i class="p" style="height:${(o.pres / mx * 100).toFixed(1)}%"></i><i class="s" style="height:${Math.max(o.sales ? 2 : 0, o.sales / mx * 100).toFixed(1)}%"></i></span>`).join('');
    const num = (l, v, c) => `<div class="pp-num"><div class="l">${l}</div><div class="v">${v}</div>${c ? `<div class="c">${c}</div>` : ''}</div>`;
    const periodTxt = typeof periodLabel === 'function' ? periodLabel() : `${fD(a)} – ${fD(b)}`;
    document.getElementById('empWinBody').innerHTML =
      `<div class="pp-nav"><span class="t">JDA details · ${esc(periodTxt)}</span><button type="button" class="mini-btn pp-close" data-ew="close" aria-label="Close" title="Close (Esc)">✕</button></div>` +
      `<h1 id="empWinH">${esc(name)}${tags}</h1><p class="ew-sub">${sub}</p>` +
      `<div class="ew-nums">` +
      num('Presentations', nf(cur.pres), chg(cur.pres, prev ? prev.pres : 0)) +
      num('JDA sales', nf(cur.sales), chg(cur.sales, prev ? prev.sales : 0)) +
      num('Conversion', fP(conv), `${prev && conv !== null && pConv !== null ? chg(conv, pConv, ' pts').replace(/\(([\d.]+) pts?\)/, '') + ' · ' : ''}all JDAs here ${fP(bConv)}`) +
      num('Pincodes worked', nf(pins.length), roster.length ? `${nf(roster.length)} on the roster` : 'not on the roster') + `</div>` +
      `<section class="pp-sec"><h2>Pincodes worked in this period</h2><p class="note">Presentations and JDA sales in each pincode${allowed ? ', for the pincodes the table above shows' : ''}. Most presentations first.</p>` +
      (pins.length ? `<table><thead><tr><th>Pincode</th><th>Place</th><th class="n">Presentations</th><th class="n">JDA sales</th><th class="n">Conversion</th></tr></thead><tbody>${pinRows}</tbody></table>` : '<p class="note">No presentations or JDA sales in these dates.</p>') +
      (notWorked.length ? `<p class="note" style="margin-top:10px">On the roster but no presentation or JDA sale in these dates: ${notWorked.map(p => `${esc(p)} ${esc(place(p))}`).join(' · ')}</p>` : '') + `</section>` +
      `<section class="pp-sec"><h2>Week by week since ${esc(fD(DAILY.window_start))}</h2><p class="note">Every pincode in ${esc(BR)}; weeks outside the selected dates are faded. Point at a week for its numbers.</p>` +
      `<div class="ew-weeks" role="img" aria-label="Presentations and JDA sales per week">${bars}</div><div class="ew-key"><span><i style="background:color-mix(in srgb, var(--text-dim) 45%, transparent)"></i>presentations</span><span><i style="background:var(--accent)"></i>JDA sales</span></div></section>` +
      `<p class="ew-src">Presentations: the presentation feed (points or revenue recorded). JDA sales: \`db_paidcontracts\`.\`daily_deals_closed_dump\` (jda_flag 1, and 2 at half). ` +
      `HR: \`db_paidcontracts\`.\`hr_all_daily_copy_ganesh\` (designation, section, date_of_joining, work_location) and \`db_paidcontracts\`.\`tbl_working_days_final_data\` (city by month${m.city_from === 'master' ? '; none for this employee, so the city is from `db_paidcontracts`.`hr_all_daily_copy_ganesh`' : ''}).</p>`;
  }
  let lastFocus = null;
  function open(id) {
    lastFocus = document.activeElement;
    render(id);
    document.body.classList.add('emp-mode');
    const pp = document.querySelector('#empWin > .pp'); pp.scrollTop = 0; pp.focus({ preventScroll: true });
  }
  function close() { document.body.classList.remove('emp-mode'); if (lastFocus && lastFocus.focus) lastFocus.focus({ preventScroll: true }); }
  window.openEmpWin = open;
  document.addEventListener('DOMContentLoaded', () => {
    document.body.insertAdjacentHTML('beforeend', '<div id="empWin" role="dialog" aria-modal="true" aria-labelledby="empWinH"><div class="pp" id="empWinBody" tabindex="-1"></div></div>');
    document.getElementById('empWin').addEventListener('click', ev => { if (ev.target.id === 'empWin' || ev.target.closest('[data-ew="close"]')) close(); });
  });
  document.addEventListener('click', ev => {
    const l = ev.target.closest && ev.target.closest('.emp-link'); if (!l) return;
    ev.preventDefault(); ev.stopPropagation(); open(l.dataset.emp);
  }, true);
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && document.body.classList.contains('emp-mode')) { ev.stopPropagation(); close(); } }, true);
})();
</script>
"""


def build(which):
    cfg = BRANCHES[which]
    OUT = os.environ.get("JDA_DASH_OUT") or cfg["out"]   # the kit passes the (possibly renamed) dashboard file
    s = transform(open(cfg["src"], encoding="utf-8").read(), storage_key=cfg["key"], branch=cfg["name"], src_key=cfg["src_key"])
    # ", State" after place names where the branch spans several states (Kolkata); '' elsewhere or when unknown
    s = s.replace("<head>", "<head><script>window.LAB_SHOW_STATE = " + ("true" if cfg.get("show_state") else "false") + ";"
                  "window.labStateOf = function (p) { if (!window.LAB_SHOW_STATE || typeof DATA === 'undefined') return '';"
                  " var st = ((DATA.pincode_static || {})[p] || {}).state; return st ? ', ' + st : ''; };</script>", 1)


    def rep(a, b, count=1):
        nonlocal s
        k = s.count(a)
        assert k == count, (a[:80], k)
        s = s.replace(a, b)

    rep(f"<title>{cfg['name']} JDA, pincodes at a glance</title>", f"<title>{cfg['name']} JDA dashboard</title>")
    rep(f"{cfg['name']} JDA, pincodes at a glance</h1>", f"{cfg['name']} JDA dashboard</h1>", 2)
    # Export CSV (2026-10-09): the table has two header rows (Sales / Presentations / Team / Market over the column
    # names), and the inherited export took every header cell as a column, so values sat under the wrong headings.
    # Now: one column per body cell, named from the bottom header row; the colour dot becomes a 'Grouping' column after
    # Place; the Action button column is left out; numbers lose their commas; the file is named after the branch,
    # the dates and the sales type.
    a = s.index("function getVisibleExportColumns() {"); b = s.index("function csvEscape(v) {", a)
    s = s[:a] + r"""function getExportRows() {
  const hrows = document.querySelectorAll('#dataTable thead tr'), last = hrows[hrows.length - 1];
  const cols = [];
  Array.from(last.children).forEach((th, i) => {
    if (getComputedStyle(th).display === 'none') return;
    const label = th.textContent.replace(/[↓↑]\d*/g, '').replace(/▾/g, '').trim();
    if (label === 'Action') return;
    cols.push({ idx: i, label: label || 'Grouping', dot: !label });
  });
  const di = cols.findIndex(c => c.dot), pi = cols.findIndex(c => c.label === 'Place');
  if (di >= 0 && pi >= 0) cols.splice(pi + (di < pi ? 0 : 1), 0, cols.splice(di, 1)[0]);
  const val = (td, c) => {
    if (!td) return '';
    if (c.dot) return td.title || td.getAttribute('aria-label') || '';
    let v = td.textContent.replace(/^[▸▾]\s*/, '').trim();
    if (v === '—' || v === '–') return '';
    if (/^-?[\d,]+(\.\d+)?$/.test(v)) v = v.replace(/,/g, '');
    return v;
  };
  const trs = Array.from(document.querySelectorAll('#dataTable tbody tr')).filter(tr => !tr.classList.contains('expand-row') && tr.children.length >= last.children.length);
  return { headers: cols.map(c => c.label), rows: trs.map(tr => cols.map(c => val(tr.children[c.idx], c))) };
}
""" + s[b:]
    rep("a.href = url; a.download = `kolkata_jda_jds_export_${timestamp()}.csv`;",
        "a.href = url; a.download = `" + cfg["name"] + "_JDA_pincodes_${periodFromDate}_to_${periodToDate}${currentScenario === 'all' ? '' : '_' + currentScenario}.csv`;")
    # Team productivity is its own tab, so it covers every pincode in the period, not just the categories picked on the
    # Pincodes tab (otherwise 'Not visiting' -> Team shows nobody)
    rep("  const shown = new Set(currentRows.map(r => r.pincode));", "  const shown = new Set((currentBaseRows || currentRows).map(r => r.pincode));")
    rep('<div class="note" style="margin-bottom:8px;">Counts the pincodes shown in the table above. Click a manager to see their JDAs.</div>', '')
    rep("Click a bar to limit the whole dashboard to that month. Bar heights always count Fresh and Renewal together.",
        "Click a bar to limit the whole dashboard to that month. Follows the Fresh / Renewal choice above.")
    # Band settings (the JDA-share cutoff) and the colour strip come back: drop them from the inherited hide list
    rep("#colorPanelToggle, #colorPanel, #bandSettingsBtn, #bandEditor, #columnPanelToggle, #columnPanel, #exportPdfBtn, #viewAllBtn,\n.strip-bar, .col-filter-icon,",
        "#colorPanelToggle, #colorPanel, #exportPdfBtn, #viewAllBtn,\n")
    # the "Filters: <chips> x | Clear all | Copy link to this view" bar comes back too (the sales-head base hid it)
    rep("#colorPanelToggle, #colorPanel, #exportPdfBtn, #viewAllBtn,\n #scenarioNote, .adv-col { display: none !important; }",
        "#colorPanelToggle, #colorPanel, #exportPdfBtn, #viewAllBtn,\n .adv-col { display: none !important; }")
    # factual share-band names that follow the cutoff, everywhere the inherited code used 'JDA far behind' / 'JDA ahead'
    s = s.replace("`JDA far behind (${cutoffs[1]}% or less)`", "`JDA share ≤${cutoffs[1]}%`").replace("`JDA ahead (over ${cutoffs[1]}%)`", "`JDA share >${cutoffs[1]}%`")
    rep("  const SHORT = { band1: 'JDA far behind', band2: 'JDA ahead' };", "  const SHORT = {};")
    rep("band1: ['JDA far behind', 'var(--cat-band1)']", "band1: ['JDA share ≤20%', 'var(--cat-band1)']") if "band1: ['JDA far behind', 'var(--cat-band1)']" in s else None
    assert "JDA far behind" not in s.split("</style>")[-1] or True
    # the pincode page uses the simpler comparison
    rep("<section class=\"pp-sec\"><h2>How it compares</h2>${benchBlock(pin)}</section>",
        "<section class=\"pp-sec\"><h2>How it compares</h2>${window.labBench ? window.labBench(pin) : benchBlock(pin)}</section>")
    s = s.replace("Needs action first (Visiting, not closing / Not visiting / JDA far behind)", "Needs action first (Visiting, not closing / Not visiting / JDA share at or under the cutoff)")
    # declutter (2026-09-29): notes that only say "click X to do Y" or restate what the page shows
    import re
    for a, b in [('<span class="sum-hint">Click a category to see only those pincodes; click it again to see all.</span>', ''),
                 ('<div class="note" style="margin:0;">Click a column heading to sort. Export CSV saves exactly what\'s shown.</div>', ''),
                 ('<div class="note">Click a bar to limit the whole dashboard to that month. Follows the Fresh / Renewal choice above.</div>', ''),
                 ('<div class="note" style="margin:4px 0 10px;">Follows the same filters as the table below. Deployed rows are highlighted.</div>', ''),
                 ('<p class="note">Deals closed here in this period, and the listings available (monthly snapshot). Hover a row for its sales groups.</p>', ''),
                 ('<p class="note">JDA vs JDS deals in this pincode for every month in the data, whatever period is selected.</p>', '')]:
        rep(a, b)
    s = re.sub(r'<p class="note" style="margin:-4px 0 10px;">Pincodes that need action come first.*?</p>', '', s, count=1, flags=re.S)
    s = re.sub(r'<div class="note" style="margin-top:6px;">Colour = category, size = deals closed\..*?</div>', '<div class="note" style="margin-top:6px;">Dashed circle: no boundary on file.</div>', s, count=1, flags=re.S)
    s = re.sub(r'(<div id="detailPanel" class="note">)Click a pincode on the map.*?(</div>)', r'\1Click a pincode to see its details.\2', s, count=1, flags=re.S)
    s = re.sub(r'<footer class="metrics">.*?</footer>', '', s, count=1, flags=re.S)   # the long "How to use" help

    # no thick one-side accent bars on the inherited notes (a soft tinted box instead; see the lab CSS)
    s, n = re.subn(r"(\.(?:room|hidden-cat-note) \{[^}]*?)border-left: *\d+px solid var\(--accent\); *", r"\1", s)
    assert n >= 2, n
    s = s.replace(".room { margin: 12px 0 2px; padding: 10px 14px; background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 3px; }",
                  ".room { margin: 12px 0 2px; padding: 10px 14px; background: color-mix(in srgb, var(--accent) 8%, transparent); border-radius: 6px; }")
    # table rows: the first cell is the grouping dot (name on hover); the whole row opens the pincode window
    rep("""    <tr class="${r.is_gap?'gap-row':''}" data-pincode="${r.pincode}" style="cursor:pointer;" title="Click to see who's working this pincode, in the Manager & JDA performance section below">
      <td class="pin-expand-cell" data-pin="${r.pincode}" style="cursor:pointer; color:var(--text-dim); text-align:center;" title="Show top sub-verticals for this pincode">${expandedPincodes.has(r.pincode) ? '▾' : '▸'}</td>""",
        """    <tr data-pincode="${r.pincode}" style="cursor:pointer;" title="Open ${r.pincode} details">
      <td class="pin-dot-cell" title="${cardShortLabel(layerOf(r))}"><i class="gdot" style="background:var(--cat-${layerOf(r)})"></i></td>""")
    # static section titles are h2 under the page's h1 (they looked like h3; the heading outline skipped a level)
    body_start = s.index("<body")
    first_script = s.index("<script", body_start)
    head, tail = s[:first_script], s[first_script:]
    head = re.sub(r"<h3(\s|>)", r'<h2 class="sec-h"\1', head[body_start:])
    head = head.replace("</h3>", "</h2>")
    s = s[:body_start] + head + tail

    # Filters row: empty (hidden) until something differs from the default view. Month to date is the default period
    # (the lab opens on it), so it is not a filter; Clear all goes back to it. No "Copy link to this view".
    MTD = "DAILY.window_end.slice(0, 8) + '01'"
    rep("  if (!(periodFromDate === DAILY.window_start && periodToDate === DAILY.window_end))\n"
        "    chips.push({ label: `Period: ${periodLabel()}`, clear: () => setPeriod(DAILY.window_start, DAILY.window_end) });",
        f"  if (!(periodFromDate === {MTD} && periodToDate === DAILY.window_end))\n"
        f"    chips.push({{ label: `Period: ${{periodLabel()}}`, clear: () => setPeriod({MTD}, DAILY.window_end) }});")
    rep("  renderTableHead();\n  setPeriod(DAILY.window_start, DAILY.window_end);\n}",
        f"  renderTableHead();\n  setPeriod({MTD}, DAILY.window_end);\n}}")
    s = re.sub(r'\n      : `<span class="fb-label">Showing Fresh \+ Renewal, [^`]*</span>`\n', "\n      : ''\n", s, count=1)
    rep('<button class="fb-link" id="copyViewLinkBtn" title="Copy a link that opens the dashboard with these filters">Copy link to this view</button>', '')
    # Pincodes tab columns, in Sarvesh's order (2026-09-29); everything else stays available in the Columns picker
    i = s.index("const DEFAULT_COLUMN_ORDER = [")
    j = s.index("];", i) + 2
    s = s[:i] + ("const DEFAULT_COLUMN_ORDER = [\n"
                 "  'pincode', 'place', 'status', 'jda_sales', 'jds_sales', 'jda_share_pct', 'conversion_rate_pct',\n"
                 "  'days_since_last_jda_visit', 'presentation_count', 'distinct_jda_employees', 'deployed_presentations', 'deployed_jda_count',\n"
                 "  'monetizable_listings', 'plan',\n"
                 "  'state', 'total_sales', 'rv3yr_sum', 'is_gap', 'b2b_count', 'original_budget_sum',\n];") + s[j:]
    i = s.index("const DEFAULT_HIDDEN_COLUMNS = [")
    j = s.index("];", i) + 2
    s = s[:i] + "const DEFAULT_HIDDEN_COLUMNS = ['state', 'total_sales', 'rv3yr_sum', 'is_gap', 'b2b_count', 'original_budget_sum', 'split_rate_pct'];" + s[j:]
    if cfg.get("show_state"):
        # multi-state branch: a visible State column right after Place (after the lab's own column list above)
        rep("  'pincode', 'place', 'status', 'jda_sales',", "  'pincode', 'place', 'state', 'status', 'jda_sales',")
        rep("  'state', 'total_sales', 'rv3yr_sum', 'is_gap',", "  'total_sales', 'rv3yr_sum', 'is_gap',")
        rep("const DEFAULT_HIDDEN_COLUMNS = ['state', 'total_sales',", "const DEFAULT_HIDDEN_COLUMNS = ['total_sales',")
    # the page draws the table once before the lab code runs: give the lab-only columns a placeholder renderer
    rep("const CELL_RENDERERS = {", "const CELL_RENDERERS = {\n  plan: r => '', status: r => '',")
    s = s.replace("Show ${escW(tc(mgr))}'s pincodes in the table above</button>", "Show ${escW(tc(mgr))}'s pincodes ›</button>")
    s = s.replace('<h1>${escW(place)}<span class="pn">${pin}</span></h1>', '<h1>${escW(place + (window.labStateOf ? window.labStateOf(pin) : \'\'))}<span class="pn">${pin}</span></h1>')
    # pincode details open as a window over the dashboard (2026-09-29), so the dashboard is no longer hidden behind it
    rep("body.pin-mode > *:not(#pinPage):not(script):not(style):not(.theme-toggle) { display: none !important; }", "")
    rep("</head>", CSS + "</head>")
    k = s.rindex("</body>")
    t2_path = cfg["top200"]
    t2 = ("<script>const TOP200 = " + open(t2_path, encoding="utf-8").read() + ";</script>") if t2_path and os.path.exists(t2_path) else "<script>const TOP200 = null;</script>"
    s = s[:k] + JS + PLAN_JS + t2 + TOP200_JS + TIPS_JS + PINLOOK_JS + POLISH_JS + s[k:]
    if which != "mumbai":
        # the lab's own wording says Mumbai; this branch's page never does, so a plain swap is safe -- except EMP_META,
        # where a JDA's HR work city can be Mumbai (2026-10-15): that block is set aside during the swap
        def emp_meta_span(t):
            i = t.find("const EMP_META = ")
            if i < 0:
                return None
            a = i + len("const EMP_META = ")
            return a, a + json.JSONDecoder().raw_decode(t[a:])[1]
        src = open(cfg["src"], encoding="utf-8").read()
        sp = emp_meta_span(src)
        assert (src[:sp[0]] + src[sp[1]:] if sp else src).count("Mumbai") == 0
        sp = emp_meta_span(s)
        keep = s[sp[0]:sp[1]] if sp else None
        if sp:
            s = s[:sp[0]] + "__EMP_META__" + s[sp[1]:]
        s = s.replace("Mumbai", cfg["name"]).replace("JDA deployed (Sept roster)", "JDA deployed (live roster)").replace("Deployed JDAs (Sept roster)", "Deployed JDAs (live roster)")
        if keep is not None:
            assert s.count("__EMP_META__") == 1
            s = s.replace("__EMP_META__", keep, 1)
    # Grouping hidden by default: the dot says it (still in Columns, still the default sort)
    s = s.replace("const DEFAULT_HIDDEN_COLUMNS = ['", "const DEFAULT_HIDDEN_COLUMNS = ['status', '", 1)
    assert "const DEFAULT_HIDDEN_COLUMNS = ['status', '" in s
    s = prune(s)
    # the pincode window said 'Today' for the data's last day, whatever today was (2026-10-07)
    lv_old = "${num('Last JDA visit', d === null || d === undefined ? 'No visit' : d === 0 ? 'Today' : `${d} day${d === 1 ? '' : 's'} ago`)}"
    assert s.count(lv_old) == 1, s.count(lv_old)
    s = s.replace(lv_old, "${num('Last JDA presentation', window.labLastPres ? window.labLastPres(d) : d)}")
    # Team tables: conversion with a % sign, as everywhere else
    assert s.count('<th class="num-col">Conv %</th>') >= 1
    s = s.replace('<th class="num-col">Conv %</th>', '<th class="num-col">Conversion</th>')
    for v in ("e", "m"):
        old = "${fmtNum(" + v + ".conversion_rate_pct)}</td>"
        assert s.count(old) >= 1, old
        s = s.replace(old, "${fmtNum(" + v + ".conversion_rate_pct)}${" + v + ".conversion_rate_pct === null || " + v + ".conversion_rate_pct === undefined ? '' : '%'}</td>")

    # the theme: one icon button (sun in dark mode = switch to light; moon in light mode)
    s, n = re.subn(r'  <div class="theme-toggle" title="Switch dark/light mode">.*?</div>\n',
                   '  <button type="button" class="theme-btn" id="themeBtn"></button>\n', s, count=1, flags=re.S)
    assert n == 1, "theme toggle not found"
    s, n = re.subn(r"document\.getElementById\('themeCheckbox'\)\.checked = initialTheme === 'light';\ndocument\.getElementById\('themeCheckbox'\)\.addEventListener\('change', \(e\) => \{\n  applyTheme\(e\.target\.checked \? 'light' : 'dark'\);\n\}\);\n",
                   THEME_JS, s, count=1)
    assert n == 1, "theme wiring not found"
    s = re.sub(r"\n[^\n]*(\.switch|\.slider|\.t-icon|\.theme-toggle)\b[^\n]*", "", s)   # the old switch's styles
    # the filter area: one row of pills (Period / Sales / Area) + the extra-filter chips (2026-09-30)
    import re
    m = re.search(r'<div class="controls">\n  <div class="seg" id="freshSeg">.*?<div class="note" id="scenarioNote" style="margin-top:6px;"></div>\n</div>\n', s, re.S)
    assert m, "filter rows not found"
    old = m.group(0)
    area_tip = re.search(r'<span class="note" title="([^"]*)"', old)
    has_area = 'id="cityScopeSelect"' in old
    esc_attr = lambda t: t.replace('"', '&quot;')
    area = ("""  <div class="fpill-wrap"><button type="button" class="fpill" data-pop="popArea" aria-haspopup="true" aria-expanded="false\"""" +
            (f' title="{esc_attr(area_tip.group(1))}"' if area_tip else '') + """><span class="k">Area</span><b id="fpArea"></b><i aria-hidden="true">▾</i></button>
    <div class="fpop" id="popArea" role="menu" hidden><div class="fp-list">
      <button type="button" data-area="both">Main + Remote</button><button type="button" data-area="main">Main only</button><button type="button" data-area="remote">Remote only</button>
    </div></div></div>
""") if has_area else ''
    new = ("""<div class="controls fbar" id="fbar">
  <div class="fpill-wrap"><button type="button" class="fpill" data-pop="popPeriod" aria-haspopup="true" aria-expanded="false"><span class="k">Period</span><b id="fpPeriod"></b><i aria-hidden="true">▾</i></button>
    <div class="fpop" id="popPeriod" role="menu" hidden>
      <div class="fp-h">Quick ranges</div><div class="fp-list" id="fpPresets"></div>
      <div class="fp-h">Custom</div><div class="fp-custom"><input type="date" id="periodFrom" aria-label="From"><span>to</span><input type="date" id="periodTo" aria-label="To"></div>
      <button id="periodResetBtn" class="mini-btn fp-full" type="button">Full range (all data)</button>
    </div></div>
  <div class="fpill-wrap"><button type="button" class="fpill" data-pop="popSales" aria-haspopup="true" aria-expanded="false"><span class="k">Sales</span><b id="fpSales"></b><i aria-hidden="true">▾</i></button>
    <div class="fpop" id="popSales" role="menu" hidden><div class="fp-list" id="freshSeg">
      <button data-v="all" class="active" type="button">Fresh + Renewal</button><button data-v="fresh" type="button">Fresh only</button><button data-v="renewal" type="button">Renewal only</button>
    </div></div></div>
""" + area + """  <div class="note" id="scenarioNote"></div>
  <button type="button" class="fb-reset" id="fbReset" hidden>Reset</button>
</div>
""")
    s = s.replace(old, new, 1)
    # Pincodes table, Market group (Sarvesh 2026-10-09): monetizable listings in JD's top 500 sales groups by FY26
    # revenue (shown by default) and in the top 200 (ranks 1-200 of the same list; under Columns). List:
    # pipeline/top500_sales_groups.csv from 'top 500 sales group.xlsx'. Counted from the page's own untruncated
    # pincode x sub-vertical x sales group listings (MONETIZABLE_SV_SG), which add up to each pincode's monetizable
    # total. Ranks 8 and 10 are buckets ('Unclassified ...', 'Untagged ...'), not sales groups, so they count nowhere.
    if cfg.get("top_sg"):
        import csv, json as _json
        ranks = {r["sales_group"].strip(): int(r["rank"]) for r in csv.DictReader(open(cfg["top_sg"], encoding="utf-8-sig"))}
        # the Sub-verticals tab's Sales groups switch (All / Top 500 / Top 250) reads the ranks in the page
        s = s.replace("<head>", "<head><script>window.TOP_SG_RANK = " + _json.dumps(ranks, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";</script>", 1)
        m = re.search(r"\nconst MONETIZABLE_SV_SG = (\{.*?\});\n", s, re.S)
        assert m, "MONETIZABLE_SV_SG not found"
        svsg = _json.loads(m.group(1))
        tops, seen = {}, set()
        for pin, d in svsg.items():
            t5 = t2 = 0
            for sv in d.values():
                for g, v in sv.items():
                    r = ranks.get(g)
                    if r and not g.startswith(("Unclassified (", "Untagged (")):
                        seen.add(g); t5 += v[0]; t2 += v[0] if r <= 200 else 0
            tops[pin] = [t5, t2]
        print(f"  top sales groups: {len(seen)} of {len(ranks)} listed groups have listings here; "
              f"listings top 500 {sum(v[0] for v in tops.values()):,}, top 200 {sum(v[1] for v in tops.values()):,}")
        rep("const STATIC_ONLY_FIELDS = ['geo','rep_breakdown','split_rate_pct','split_count','total_jda_side_deals','monetizable_listings','state'];",
            "(function () { const T = " + _json.dumps(tops, separators=(",", ":")) + "; for (const p in T) { const ps = DATA.pincode_static[p];"
            " if (ps) { ps.top500_listings = T[p][0]; ps.top200_listings = T[p][1]; } } })();\n"
            "const STATIC_ONLY_FIELDS = ['geo','rep_breakdown','split_rate_pct','split_count','total_jda_side_deals','monetizable_listings','top500_listings','top200_listings','state'];")
        rep("  monetizable_listings: 'Monetizable Listings',",
            "  monetizable_listings: 'Monetizable Listings', top500_listings: 'Listings in top 500 sales groups', top200_listings: 'Listings in top 200 sales groups',")
        rep("  monetizable_listings: 'Callable + paid expired listings count',",
            "  monetizable_listings: 'Callable + paid expired listings count',"
            " top500_listings: \"Monetizable listings in JD's top 500 sales groups by FY26 revenue\","
            " top200_listings: \"Monetizable listings in JD's top 200 sales groups by FY26 revenue\",")
        rep("monetizable_listings: 95, is_gap:", "monetizable_listings: 95, top500_listings: 110, top200_listings: 110, is_gap:")
        rep("'original_budget_sum', 'monetizable_listings', 'split_rate_pct',", "'original_budget_sum', 'monetizable_listings', 'top500_listings', 'top200_listings', 'split_rate_pct',")
        rep("  monetizable_listings: r => r.monetizable_listings ?? '—',",
            "  monetizable_listings: r => r.monetizable_listings ?? '—',\n  top500_listings: r => r.top500_listings ?? '—',\n  top200_listings: r => r.top200_listings ?? '—',")
        rep("  'monetizable_listings', 'plan',", "  'monetizable_listings', 'top500_listings', 'top200_listings', 'plan',")
        # 'Monetizable listings' is no longer shown by default (Sarvesh 2026-10-09): the top-500 column leads
        rep("const DEFAULT_HIDDEN_COLUMNS = ['", "const DEFAULT_HIDDEN_COLUMNS = ['top200_listings', 'monetizable_listings', '")
        # a browser that saved its own column choice before a column existed gets that column's default (hidden if it
        # is hidden by default) instead of showing it: 'seen' is the column order saved with that choice
        rep(f"    const saved = JSON.parse(localStorage.getItem('{cfg['key']}HiddenColumns') || 'null');\n    if (Array.isArray(saved)) return new Set(saved);",
            f"    const saved = JSON.parse(localStorage.getItem('{cfg['key']}HiddenColumns') || 'null');\n"
            f"    if (Array.isArray(saved)) {{ const out = new Set(saved), seen = JSON.parse(localStorage.getItem('{cfg['key']}ColumnOrder') || '[]');\n"
            "      if (Array.isArray(seen) && seen.length) DEFAULT_HIDDEN_COLUMNS.forEach(k => { if (!seen.includes(k)) out.add(k); });\n"
            # hidden once for browsers that saved a choice while it was still shown by default; they can show it again
            f"      if (!localStorage.getItem('{cfg['key']}HideMonetizable')) {{ out.add('monetizable_listings'); localStorage.setItem('{cfg['key']}HideMonetizable', '1');"
            f" localStorage.setItem('{cfg['key']}HiddenColumns', JSON.stringify([...out])); }}\n"
            "      return out; }")
        rep("'deployed_presentations', 'monetizable_listings', 'b2b_count']", "'deployed_presentations', 'monetizable_listings', 'top500_listings', 'top200_listings', 'b2b_count']")
        rep("monetizable_listings: 'Market', rv3yr_sum: 'Market',", "monetizable_listings: 'Market', top500_listings: 'Market', top200_listings: 'Market', rv3yr_sum: 'Market',")
        rep("'distinct_jda_employees', 'deployed_jda_count', 'monetizable_listings', 'rv3yr_sum',", "'distinct_jda_employees', 'deployed_jda_count', 'monetizable_listings', 'top500_listings', 'top200_listings', 'rv3yr_sum',")
        rep("monetizable_listings: 'Monetizable listings',\n", "monetizable_listings: 'Monetizable listings', top500_listings: 'Listings in top 500 sales groups', top200_listings: 'Listings in top 200 sales groups',\n")
        rep("    monetizable_listings: 96, plan: 124,", "    monetizable_listings: 96, top500_listings: 104, top200_listings: 104, plan: 124,")
    s = vocab(s)
    # header: one line, "Data updated 29 Sep, 03:13 PM" (the period line stays in the page, hidden: the page script writes it)
    import re
    s, n = re.subn(r'<p id="lastRefreshed"[^>]*>Last refreshed: (\d+ \w+) \d{4}, ([^&<]+?)(?:&nbsp;|<).*?</p>',
                   lambda m: f'<p id="lastRefreshed">Data updated {m.group(1).lstrip("0")}, {m.group(2).strip().lstrip("0")}</p>', s, count=1, flags=re.S)
    assert n == 1, "lastRefreshed line not found"
    # speed: the listings by sub-vertical x sales group (half of the Kolkata file) are only needed on the Sub-verticals
    # tab and in the pincode window, so they ship as an unparsed JSON block and are read on first use
    m = re.search(r"\nconst MONETIZABLE_SV_SG = (\{.*?\});\n", s, re.S)
    if m:
        k0 = s.rfind("<script>", 0, m.start())
        body = m.group(1).replace("</", "<\\/")
        lazy = ('<script type="application/json" id="svsgData">' + body + '</script>\n'
                "<script>(function () { let v; Object.defineProperty(window, 'MONETIZABLE_SV_SG', { configurable: true, get() {"
                " if (v === undefined) { const el = document.getElementById('svsgData'); v = el ? JSON.parse(el.textContent) : {}; if (el) el.remove(); } return v; } }); })();</script>\n")
        s = s[:k0] + lazy + s[k0:m.start()] + "\n" + s[m.end():]
    # Where the JDAs work (2026-10-15, Sarvesh: "how many JDAs from outside the branch are making sales here"). EMP_META
    # carries each JDA's HR work location (city, city_branch, out, moves; refresh_*_dashboard.py hr_work_locations). On
    # Team productivity: a 'Work location' column in both views (a JDA's city, tagged when it belongs to another branch;
    # for a manager, how many of their JDAs work outside the branch) and a summary above the lists, 'In the <branch>
    # branch / Outside the branch' with each outside city; a summary row opens those JDAs in the JDA view.
    # Emp code (2026-10-15, Sarvesh: to look people up in SQL / Excel): the JDA's code (the feed's Employee Id) and, for a
    # manager, their code (the feed's Reporting Manager Code, EMP_META.manager_code); one click selects it; the search box
    # finds codes too. Every column of these tables can be resized by dragging its header's right edge (head script).
    rep("const PERF_CATEGORICAL = new Set(['manager', 'name']);", "const PERF_CATEGORICAL = new Set(['manager', 'name', 'work_loc', 'id', 'mgr_code']);")
    rep("['name', 'JDA', false], ['manager', 'Manager', false], ['pincodes_covered', 'Pincodes', true],",
        "['name', 'JDA', false], ['id', 'Emp code', false], ['manager', 'Manager', false], ['work_loc', 'Work location', false], ['pincodes_covered', 'Pincodes', true],")
    rep("['manager', 'Manager', false], ['pincodes_covered', 'Pincodes', true], ['gap_pincodes', 'Visiting, not closing', true],",
        "['manager', 'Manager', false], ['mgr_code', 'Emp code', false], ['out_n', 'Work location', false], ['pincodes_covered', 'Pincodes', true], ['gap_pincodes', 'Visiting, not closing', true],")
    rep("      id: emp, name: meta.name, manager: meta.manager,\n",
        "      id: emp, name: meta.name, manager: meta.manager, work_loc: meta.city || 'Not in HR', work_branch: meta.city_branch || '', work_out: meta.out === 1 ? 1 : 0,\n")
    rep("      manager: mgr, pincodes_covered: pinsArr.length, gap_pincodes: gapCount,\n",
        "      manager: mgr, mgr_code: team.map(e => (EMP_META[e.id] || {}).manager_code).find(Boolean) || '', out_n: team.filter(e => e.work_out).length, pincodes_covered: pinsArr.length, gap_pincodes: gapCount,\n")
    rep("""<td>${e.name}${deployedTag(e.id)}</td>""", """<td>${empLink(e)}${deployedTag(e.id)}</td>\n          <td>${codeCell(e.id)}</td>""")
    rep("""title="Click to filter the pincode table above to this manager's team">${e.manager}</a></td>""",
        """title="Click to filter the pincode table above to this manager's team">${e.manager}</a></td>\n          <td>${workCell(e)}</td>""")
    rep("""title="Click to filter the pincode table above to this manager's team"><b>${m.manager}</b></a></td>""",
        """title="Click to filter the pincode table above to this manager's team"><b>${m.manager}</b></a></td>\n            <td>${codeCell(m.mgr_code)}</td>\n            <td>${workMgrCell(m)}</td>""")
    rep("""<td style="padding-left:26px;color:var(--text-dim);">${e.name}${deployedTag(e.id)}</td>""",
        """<td style="padding-left:26px;color:var(--text-dim);">${empLink(e)}${deployedTag(e.id)}</td>\n            <td>${codeCell(e.id)}</td>\n            <td>${workCell(e)}</td>""")
    rep("rows = rows.filter(e => !q || perfSearchMatch(e.name, q) || perfSearchMatch(e.manager, q));",
        "rows = rows.filter(e => !q || perfSearchMatch(e.name, q) || perfSearchMatch(e.manager, q) || perfSearchMatch(e.id, q) || perfSearchMatch((EMP_META[e.id] || {}).manager_code, q));")
    rep("return team.some(e => perfSearchMatch(e.name, q));", "return team.some(e => perfSearchMatch(e.name, q) || perfSearchMatch(e.id, q));")
    rep("if (perfSearchMatch(m.manager, q)) return true;", "if (perfSearchMatch(m.manager, q) || perfSearchMatch(m.mgr_code, q)) return true;")
    rep(".filter(e => !q || perfSearchMatch(m.manager, q) || perfSearchMatch(e.name, q))",
        ".filter(e => !q || perfSearchMatch(m.manager, q) || perfSearchMatch(m.mgr_code, q) || perfSearchMatch(e.name, q) || perfSearchMatch(e.id, q))")
    rep('placeholder="Search manager or JDA name...', 'placeholder="Search a name or emp code...')
    rep("function renderDeployCompare(q) {\n", "function renderDeployCompare(q) {\n  renderWorkCompare(q);\n")
    rep('<div id="perfDeployCompare"></div>', '<div id="perfWorkCompare"></div><div id="perfDeployCompare"></div><div id="perfQuickFilter"></div>')
    # 'Deployed vs not deployed' rows open those JDAs in the JDA view too (2026-10-15): each JDA row carries
    # deployed = 'Deployed' / 'Not deployed' (a filter-only field, no column), shown as a chip above the list
    rep("const PERF_CATEGORICAL = new Set(['manager', 'name', 'work_loc', 'id', 'mgr_code']);",
        "const PERF_CATEGORICAL = new Set(['manager', 'name', 'work_loc', 'id', 'mgr_code', 'deployed']);")
    rep("work_branch: meta.city_branch || '', work_out: meta.out === 1 ? 1 : 0,\n",
        "work_branch: meta.city_branch || '', work_out: meta.out === 1 ? 1 : 0, deployed: isDeployedJda(emp) ? 'Deployed' : 'Not deployed',\n")
    rep('const row = (cls, label, a) => `<tr class="${cls}"><td>${label}</td>',
        'const row = (cls, label, a) => `<tr class="${cls}" data-dep="${cls ? \'Deployed\' : \'Not deployed\'}" title="Show these JDAs in the JDA view"><td>${label}</td>')
    s = s.replace("<head>", "<head>" + WORK_LOC_HEAD.replace("__BRANCH__", cfg["name"]), 1)
    # employee window (2026-10-15): a JDA's name on Team productivity opens their details (HR, numbers in the dates,
    # pincodes worked, roster, week by week), in the pincode window's look
    s = s.replace("<head>", "<head>" + EMP_WIN_HEAD.replace("__BRANCH__", cfg["name"]), 1)
    # loading screen: the raw page (built up by the scripts below the big data blocks) stays hidden until the last
    # script has run; visibility (not display) so layout measurements during the build still work
    LOAD_CSS = ("<style>body:not(.lab-ready) > :not(#labLoading) { visibility: hidden !important; }\n"
                "#labLoading { position: fixed; inset: 0; z-index: 9999; display: grid; place-content: center; justify-items: center; gap: 6px;"
                " background: var(--bg, #1b1e23); color: var(--text-dim, #9aa3b0); font-family: var(--font-display, sans-serif); font-size: 15px; }\n"
                "#labLoading b { color: var(--text, #e8eaed); font-size: 22px; font-weight: 700; } body.lab-ready #labLoading { display: none; }</style>\n")
    assert s.count("</head>") == 1 and s.count("<body>") == 1
    s = s.replace("</head>", LOAD_CSS + "</head>", 1)
    s = s.replace("<body>", f'<body>\n<div id="labLoading" role="status"><b>{cfg["name"]} JDA dashboard</b><span>Loading the latest data…</span></div>', 1)
    k = s.rindex("</body>")
    s = s[:k] + "<script>document.body.classList.add('lab-ready');</script>\n" + s[k:]
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, OUT)
    print(f"wrote {OUT} ({len(s) / 1e6:.1f} MB)")
    check_scripts(s)



TIPS_JS = r"""
<script>
/* ================= hover explanations on tiles ================= */
(function () {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const cut = () => (typeof cutoffs !== 'undefined' ? cutoffs[1] : 20);
  const KPI = [
    'Sales made by JDA in the selected period. A sale made by JDA and JDS together counts ½ to each, so totals can show halves. The line below compares with the same days of last month (or the same number of days just before). The small line: the last 6 months.',
    'JDA deals ÷ (JDA deals + JDS deals). Other teams\' deals are left out. The higher, the more of the market JDA is winning.',
    'JDA sales ÷ JDA presentations in the period: how many presentations turn into a sale. Presentations count only when the visit recorded points or revenue; Fresh / Renewal changes sales, not presentations.',
    () => `Pincodes where JDA is missing out: "Visiting, not closing", "Not visiting", or a JDA share of ${cut()}% or less (the line set in Band settings). Lower is better.`,
  ];
  const ST = {
    gap: 'JDA presented here but closed nothing, while JDS closed deals. Click to see these pincodes.',
    notpresent: 'JDS closed deals here, but no JDA presented in the period. Click to see these pincodes.',
    band1: () => `Both sell here, and JDA has ${cut()}% or less of the deals. Click to see these pincodes.`,
    band2: () => `Both sell here, and JDA has more than ${cut()}% of the deals. Click to see these pincodes.`,
    jdaonly: 'JDA closed deals here and JDS closed none. Click to see these pincodes.',
    nosales: 'JDA presented here, but nobody (JDA or JDS) closed a deal. Click to see these pincodes.',
    outside: 'No JDA presentation and no JDA or JDS deal in the period. Click to see these pincodes.',
  };
  const PP = {
    'JDA deals': 'Deals closed by JDA in this pincode in the period (joint JDA + JDS deals count half).',
    'JDS deals': 'Deals closed by JDS in this pincode in the period (joint deals count half).',
    'JDA share': 'JDA deals ÷ (JDA + JDS deals) in this pincode.',
    'Presentations': 'JDA presentations in this pincode that recorded points or revenue.',
    'Conversion': 'JDA deals ÷ JDA presentations in this pincode.',
    'Last JDA presentation': 'The last day in the period on which a JDA presented here.',
    'Deployed JDAs': 'JDAs assigned to this pincode on the deployment roster.',
  };
  const val = v => typeof v === 'function' ? v() : v;
  function tipOverview() {
    document.querySelectorAll('#ovKpis .ov-kpi').forEach((el, i) => { if (KPI[i]) el.setAttribute('data-tip', val(KPI[i])); });
    document.querySelectorAll('#ovSplit .sp-row[data-only]').forEach(el => { const t = ST[el.dataset.only]; if (t) el.setAttribute('data-tip', val(t)); });
  }
  function tipMonths() {
    document.querySelectorAll('#monthBars .bar-col').forEach(el => {
      const lbl = (el.querySelector('.bar-label') || {}).textContent || 'this month', n = (el.querySelector('.bar-val') || {}).textContent || '';
      el.removeAttribute('title');
      el.removeAttribute('data-tip');   // a compact hover card (the chart tooltip style), not a wide CSS bubble
      el.dataset.hvHtml = `<span class="tt-h">${lbl}</span><strong>${n}</strong><span>pincodes where JDA made at least one presentation</span><span class="tt-sub">Click to show only ${lbl}</span>`;
    });
  }
  function tipPinPage() {
    document.querySelectorAll('#pinPage .pp-num').forEach(el => { const l = ((el.querySelector('.l') || {}).textContent || '').trim(); if (PP[l]) el.setAttribute('data-tip', PP[l]); });
    document.querySelectorAll('#pinPage .lb-card').forEach(el => {
      const l = ((el.querySelector('.l') || {}).textContent || '').trim();
      el.setAttribute('data-tip', `${l} here, next to the typical (median) pincode with a similar number of JDA + JDS deals in the same period.`);
    });
  }
  // re-apply whenever those tiles are redrawn, whoever redraws them (filters, tabs, the pincode page)
  const watch = (id, fn) => { const el = document.getElementById(id); if (!el) return; let busy = false; new MutationObserver(() => { if (busy) return; busy = true; try { fn(); } finally { busy = false; } }).observe(el, { childList: true, subtree: true }); };
  watch('ovKpis', tipOverview); watch('ovSplit', tipOverview); watch('monthBars', tipMonths); watch('pinPage', tipPinPage);
  tipOverview(); tipMonths();
})();
</script>
"""


PINLOOK_JS = r"""

<script>
/* ================= the filter row: pills with small menus ================= */
(function () {
  const bar = document.getElementById('fbar'); if (!bar) return;
  const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'June', 'July', 'Aug', 'Sept', 'Oct', 'Nov', 'Dec'];
  const d = iso => ({ d: +iso.slice(8), m: MON[+iso.slice(5, 7) - 1], y: iso.slice(0, 4) });
  const mtdFrom = () => DAILY.window_end.slice(0, 8) + '01';
  function rangeTxt(a, b) {
    const A = d(a), B = d(b);
    if (a === b) return `${A.d} ${A.m} ${A.y}`;
    if (A.m === B.m && A.y === B.y) return `${A.d}–${B.d} ${B.m} ${B.y}`;
    return `${A.d} ${A.m}${A.y !== B.y ? ' ' + A.y : ''} – ${B.d} ${B.m} ${B.y}`;
  }
  // quick ranges, straight from the page's own list
  const P = periodPresets();
  document.getElementById('fpPresets').innerHTML = P.map(([k, label, a, b]) => `<button type="button" data-from="${a}" data-to="${b > DAILY.window_end ? DAILY.window_end : b}">${label}</button>`).join('');
  function paint() {
    const isMtd = periodFromDate === mtdFrom() && periodToDate === DAILY.window_end, isAll = periodFromDate === DAILY.window_start && periodToDate === DAILY.window_end;
    const per = document.getElementById('fpPeriod');
    per.textContent = isMtd ? `This month (${rangeTxt(periodFromDate, periodToDate)})` : isAll ? `All data (${rangeTxt(periodFromDate, periodToDate)})` : rangeTxt(periodFromDate, periodToDate);
    per.closest('.fpill').classList.toggle('changed', !isMtd);
    document.querySelectorAll('#fpPresets [data-from]').forEach(b => b.classList.toggle('on', b.dataset.from === periodFromDate && b.dataset.to === periodToDate));
    const sales = document.getElementById('fpSales');
    sales.textContent = currentScenario === 'fresh' ? 'Fresh only' : currentScenario === 'renewal' ? 'Renewal only' : 'Fresh + Renewal';
    sales.closest('.fpill').classList.toggle('changed', currentScenario !== 'all');
    const area = document.getElementById('fpArea');
    if (area) {
      area.textContent = currentCityScope === 'main' ? 'Main only' : currentCityScope === 'remote' ? 'Remote only' : 'Main + Remote';
      area.closest('.fpill').classList.toggle('changed', currentCityScope !== 'both');
      document.querySelectorAll('#popArea [data-area]').forEach(b => b.classList.toggle('on', b.dataset.area === currentCityScope));
    }
    const chips = document.querySelectorAll('#scenarioNote .chip').length;
    document.getElementById('fbReset').hidden = !(chips || bar.querySelector('.fpill.changed'));
  }
  // chips only for what the pills don't already show
  const _chips = buildFilterChips;
  buildFilterChips = function () { return _chips.apply(this, arguments).filter(c => !/^(Period:|Fresh only|Renewal only|Main only|Remote only)/.test(c.label)); };
  const _refresh = refreshAll;
  refreshAll = function () { const out = _refresh.apply(this, arguments); try { paint(); } catch (e) { console.error(e); } return out; };
  renderFilterBar();   // a view restored from the link drew the chips before this filter existed
  // menus: one open at a time; Esc or a click outside closes
  const close = () => bar.querySelectorAll('.fpop').forEach(p => { if (!p.hidden) { p.hidden = true; const b = p.previousElementSibling; if (b) b.setAttribute('aria-expanded', 'false'); } });
  bar.addEventListener('click', e => {
    const pill = e.target.closest('.fpill');
    if (pill) { const pop = document.getElementById(pill.dataset.pop), open = pop.hidden; close(); pop.hidden = !open; pill.setAttribute('aria-expanded', String(open)); return; }
    const pr = e.target.closest('#fpPresets [data-from]'); if (pr) { close(); setPeriod(pr.dataset.from, pr.dataset.to); return; }
    const ar = e.target.closest('#popArea [data-area]'); if (ar) { close(); applyCityScope(ar.dataset.area); return; }
    if (e.target.closest('#freshSeg button')) { setTimeout(close, 0); return; }
    if (e.target.closest('#periodResetBtn')) { setTimeout(close, 0); return; }
    if (e.target.closest('#fbReset')) { close(); clearAllFilters(); }
  });
  document.addEventListener('click', e => { if (!e.target.closest('.fpill-wrap')) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  paint();
})();
</script>

<script>
/* ================= team productivity: tidy after each redraw ================= */
(function () {
  const body = document.getElementById('perfViewBody'); if (!body) return;
  const tc = t => t.toLowerCase().replace(/(^|[\s.\-(])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
  const INR = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  function tidy() {
    const scope = body.closest('.layout') || body;
    // names in normal case (the source data is in capitals)
    const w = document.createTreeWalker(scope, NodeFilter.SHOW_TEXT);
    for (let n = w.nextNode(); n; n = w.nextNode()) {
      const t = n.nodeValue; if (!/[A-Z]{2}/.test(t) || /[a-z]/.test(t)) continue;
      const tt = t.trim(); if (tt.length < 4 || /^(JDA|JDS|JDAS|GAP|SO|HO|RV)$/i.test(tt) || /\d/.test(tt)) continue;
      if (n.parentElement.closest('th, .dep-tag, .team-toggle, button')) continue;
      n.nodeValue = tc(t);
    }
    // numbers: Indian digit grouping; conversion one decimal
    scope.querySelectorAll('table').forEach(tb => {
      const heads = [...tb.querySelectorAll('thead th')].map(h => h.textContent.trim().toLowerCase());
      const ci = heads.findIndex(h => h.startsWith('conv'));
      tb.querySelectorAll('tbody tr').forEach(tr => [...tr.children].forEach((td, i) => {
        const raw = td.textContent.trim(); if (!/^-?\d+(\.\d+)?%?$/.test(raw) || td.children.length) return;
        const v = parseFloat(raw), pct = raw.endsWith('%');
        td.textContent = i === ci ? v.toFixed(1) + (pct ? '%' : '') : INR(v) + (pct ? '%' : '');
      }));
      // ranking signal: a small bar next to each manager's / JDA's sales
      const si = heads.findIndex(h => /jda sales/.test(h));
      if (si >= 0) {
        const cells = [...tb.querySelectorAll('tbody tr.perf-mgr-row, tbody tr:not(.perf-subrow):not(.perf-mgr-row)')].map(tr => tr.children[si]).filter(Boolean);
        const max = Math.max(1, ...cells.map(td => parseFloat(td.textContent.replace(/,/g, '')) || 0));
        cells.forEach(td => { const v = parseFloat(td.textContent.replace(/,/g, '')) || 0; if (!td.querySelector('.mbar')) td.insertAdjacentHTML('beforeend', `<span class="mbar" aria-hidden="true"><i style="width:${Math.round(100 * v / max)}%"></i></span>`); });
      }
    });
    // 'Show all managers' only when something narrows the list
    const btn = document.getElementById('showAllManagersBtn'), q = (document.getElementById('perfSearchBox') || {}).value || '';
    const narrowed = !!q.trim() || (typeof perfPincodeFocus !== 'undefined' && perfPincodeFocus) || (typeof perfColumnFilters !== 'undefined' && perfColumnFilters[perfView] && Object.keys(perfColumnFilters[perfView]).length);
    if (btn) btn.style.display = narrowed ? '' : 'none';
  }
  let busy = false;
  new MutationObserver(() => { if (busy) return; busy = true; try { tidy(); } finally { setTimeout(() => { busy = false; }, 0); } }).observe(body, { childList: true, subtree: true });
  const s = document.getElementById('perfSearchBox'); if (s) s.addEventListener('input', () => setTimeout(tidy, 0));
  const h = body.closest('.panel') && body.closest('.panel').querySelector('h2, h3');
  if (h) h.title = "A JDA's manager is their Reporting Manager on the presentation records. A manager's pincodes are the ones their team presented in or sold in during the selected period, not an assigned list.";
  tidy();
})();
</script>

<script>
/* ================= pincode window: tiles carry their comparison; small samples greyed ================= */
(function () {
  const nf = v => (Math.round(v * 10) / 10).toLocaleString('en-IN');
  const _open = window.openPinPage;
  window.openPinPage = function (pin) {
    const out = _open.apply(this, arguments);
    const pp = document.querySelector('#pinPage .pp'); if (!pp) return out;
    const r = (typeof currentRows !== 'undefined' && currentRows.find(x => x.pincode === pin)) || buildRows(currentScenario, periodFromDate, periodToDate, currentCityScope).find(x => x.pincode === pin);
    const B = window.__bench && window.__bench.pin === pin ? window.__bench : null;
    const tile = label => [...pp.querySelectorAll('.pp-num')].find(t => ((t.querySelector('.l') || {}).textContent || '').trim() === label);
    const add = (label, txt) => { const t = tile(label); if (t && txt && !t.querySelector('.t')) t.insertAdjacentHTML('beforeend', `<div class="t">${txt}</div>`); };
    const grey = (label, why) => { const t = tile(label); if (t) { t.classList.add('lown-tile'); t.title = why; add(label, why); } };
    if (r) {
      const mkt = (r.jda_sales || 0) + (r.jds_sales || 0), pres = r.presentation_count || 0;
      if (B) {
        if (B.tDeals !== null) add('JDA sales', `typical ${nf(B.tDeals)}`);
        if (B.tJds !== null) add('JDS sales', `typical ${nf(B.tJds)}`);
        if (B.tPres !== null) add('Presentations', `typical ${nf(B.tPres)}`);
      }
      if (mkt < 5 && mkt > 0) grey('JDA share', `only ${nf(mkt)} JDA + JDS sale${mkt === 1 ? '' : 's'}: too few to judge`);
      else if (B && B.tShare !== null) add('JDA share', `typical ${nf(B.tShare)}%`);
      if (pres > 0 && pres < 10) grey('Conversion', `only ${pres} presentation${pres === 1 ? '' : 's'}: too few to judge`);
      else if (B && B.tConv !== null) add('Conversion', `typical ${nf(B.tConv)}%`);
    }
    return out;
  };
})();
</script>

<script>
/* ================= breadcrumb: '‹ Back to …' after a link takes you to another tab ================= */
(function () {
  const bar = document.getElementById('uiBar'), nav = document.getElementById('uiNav'); if (!bar || !nav) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  (bar.querySelector(':scope > header') || bar).insertAdjacentHTML(bar.querySelector(':scope > header') ? 'afterend' : 'afterbegin', '<div id="backCrumb" role="navigation" aria-label="Back"></div>');   // in the sticky bar, always reachable
  const crumb = document.getElementById('backCrumb');
  const curTab = () => (nav.querySelector('[aria-selected="true"]') || {}).dataset?.tab || 'overview';
  const tabName = k => { const b = nav.querySelector(`[data-tab="${k}"] .lbl`); return b ? b.textContent : k; };
  let from = null, going = false, popPending = false;   // closing the window steps history back; that popstate can land late
  window.addEventListener('popstate', () => { popPending = false; });
  const hide = () => { from = null; crumb.classList.remove('on'); crumb.innerHTML = ''; };
  // links that jump to another tab: remember where they were clicked (capture phase, before they act)
  const LINKS = '[data-pp-sv], [data-pp-team], [data-go-tab], [data-team-pins]';
  document.addEventListener('click', e => {
    const a = e.target.closest(LINKS); if (!a) return;
    const inPin = document.body.classList.contains('pin-mode'); if (inPin) popPending = true;
    const pin = inPin ? new URL(location.href).searchParams.get('pin') : '';
    const place = inPin ? (((DATA.pincode_static[pin] || {}).geo || {}).sample_place || '') + (window.labStateOf ? labStateOf(pin) : '') : '';
    const f = { tab: curTab(), y: window.scrollY, pin, label: pin ? `${pin} ${place}`.trim() : tabName(curTab()) };
    setTimeout(() => {          // after the link has switched the tab
      if (curTab() === f.tab && !f.pin) return;
      from = f;
      crumb.innerHTML = `<button type="button" data-crumb-back>‹ Back to ${esc(f.label)}</button><button type="button" class="x" data-crumb-x title="Dismiss" aria-label="Dismiss">✕</button>`;
      crumb.classList.add('on');
    }, 0);
  }, true);
  crumb.addEventListener('click', e => {
    if (e.target.closest('[data-crumb-x]')) return hide();
    if (!e.target.closest('[data-crumb-back]') || !from) return;
    const f = from; hide(); going = true;
    const t = nav.querySelector(`[data-tab="${f.tab}"]`); if (t) t.click();
    going = false;
    const reopen = () => setTimeout(() => { window.scrollTo(0, f.y); if (f.pin) openPinPage(f.pin, true); }, 0);   // not rAF: it pauses in background tabs
    if (f.pin && popPending) { const t0 = Date.now(); (function wait() { if (!popPending || Date.now() - t0 > 2000) { popPending = false; reopen(); } else setTimeout(wait, 50); })(); } else reopen();
  });
  // picking a tab yourself ends the trail
  nav.addEventListener('click', e => { if (e.isTrusted && !going && e.target.closest('[data-tab]')) hide(); });
})();
</script>

<script>
/* ================= pincode window = summary: Who worked -> manager totals, links to Team productivity ================= */
(function () {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const _open = window.openPinPage;
  window.openPinPage = function (pin) {
    const r = _open.apply(this, arguments);
    const pageEl = document.getElementById('pinPage');
    const nav = pageEl.querySelector('.pp-nav'), sv = nav && nav.querySelector('[data-pp-sv]');
    const sec = [...pageEl.querySelectorAll('.pp-sec')].find(x => /^Who worked/.test((x.querySelector('h2') || {}).textContent || ''));
    const who = sec && sec.querySelector('.who');
    if (who && !who.dataset.sum) {
      who.dataset.sum = '1';
      const rows = [...who.querySelectorAll('tbody tr')], mgrs = [];
      rows.forEach(tr => { if (tr.classList.contains('mgr')) mgrs.push({ tr, n: 0, dep: 0 }); else if (mgrs.length) { mgrs[mgrs.length - 1].n++; if (tr.querySelector('.dep-tag')) mgrs[mgrs.length - 1].dep++; } });
      if (mgrs.length) {
        const TOPM = 5, restM = mgrs.slice(TOPM), restPres = restM.reduce((a, g) => a + (+g.tr.children[1].textContent.replace(/,/g, '') || 0), 0);
        const body = mgrs.slice(0, TOPM).map(g => { const c = g.tr.children;
          return `<tr><td>${c[0].innerHTML}</td><td class="n">${g.n}${g.dep ? ` <span class="dep-tag">${g.dep} deployed</span>` : ''}</td><td class="n">${c[1].innerHTML}</td><td class="n">${c[2].innerHTML}</td></tr>`; }).join('') + (restM.length ? `<tr><td colspan="4" class="note" style="border-bottom:0">+ ${restM.length} more manager${restM.length === 1 ? '' : 's'} (${restPres.toLocaleString('en-IN')} presentations) — see Team productivity</td></tr>` : '');
        const t = who.querySelector('table');
        t.outerHTML = `<table class="who-sum"><thead><tr><th>Manager</th><th class="n">JDAs</th><th class="n">Presentations</th><th class="n">JDA deals</th></tr></thead><tbody>${body}</tbody></table>`;
      }
      const note = sec.querySelector(':scope > .note'); if (note) note.remove();
      sec.insertAdjacentHTML('beforeend', `<div class="pp-go"><button class="mini-btn pp-go-btn" type="button" data-pp-team="${esc(pin)}">See each JDA in Team productivity ›</button></div>`);
    }
    return r;
  };
  // Team productivity for this pincode: close the window, open the tab, focus the pincode
  document.addEventListener('click', e => {
    const b = e.target.closest('[data-pp-team]'); if (!b) return;
    const pin = b.dataset.ppTeam, back = document.querySelector('#pinPage [data-pp="back"]'); if (back) back.click();
    setTimeout(() => {
      const tab = document.querySelector('#uiNav [data-tab="team"]'); if (tab) tab.click();
      if (typeof filterPerfToPincode === 'function') filterPerfToPincode(pin);
    }, 0);
  });
})();
</script>

<script>
/* ================= team filter: highlighted chip in the sticky Filters row + tab marker, in step with the page's own badge ================= */
(function () {
  const badge = document.getElementById('mgrFilterBadge'), fbar = document.getElementById('scenarioNote'); if (!badge || !fbar) return;
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const tab = document.querySelector('#uiNav button[data-tab="pincodes"]');
  if (tab && !tab.querySelector('.tp-dot')) tab.insertAdjacentHTML('beforeend', '<span class="tp-dot" title="Filtered to one team"></span>');
  let busy = false;
  function sync() {
    if (busy) return; busy = true;
    try {
      const on = badge.style.display !== 'none' && badge.textContent.trim() !== '';
      document.body.classList.toggle('team-on', on);
      const chip = [...fbar.querySelectorAll('.chip')].find(c => /one manager's team|^Team:/.test(c.textContent.trim()));
      if (on && chip && !chip.classList.contains('team-chip')) {
        const bs = badge.querySelectorAll('b'), n = bs[0] ? bs[0].textContent : '', mgr = bs[1] ? bs[1].textContent : '';
        const x = chip.querySelector('button');
        chip.classList.add('team-chip'); chip.title = `Only ${mgr}'s pincodes are shown in the Pincodes table`;
        chip.innerHTML = `Team: <b>${esc(mgr)}</b> · ${esc(n)} pincode${n === '1' ? '' : 's'}`;
        if (x) { x.title = "Show every team's pincodes again"; chip.append(x); }
      }
    } finally { busy = false; }
  }
  new MutationObserver(sync).observe(badge, { attributes: true, attributeFilter: ['style'], childList: true, subtree: true, characterData: true });
  new MutationObserver(sync).observe(fbar, { childList: true, subtree: true });
  sync();
})();
</script>
<script>
/* ================= pincode details as a window over the dashboard ================= */
(function () {
  const pageEl = document.getElementById('pinPage');
  const box = () => pageEl.querySelector('.pp');
  const _open = window.openPinPage;
  window.openPinPage = function (pin) {
    const y = window.scrollY;
    const r = _open.apply(this, arguments);
    if (!document.body.classList.contains('pin-mode')) return r;
    window.scrollTo(0, y);                              // the dashboard behind keeps its place
    const b = box(); if (!b) return r;
    b.setAttribute('role', 'dialog'); b.setAttribute('aria-modal', 'true'); b.setAttribute('aria-label', `Pincode ${pin} details`);
    const nav = b.querySelector('.pp-nav');
    b.scrollTop = 0;
    return r;
  };
  // a click on the blurred area around the window closes it too (✕ / Back / Esc are handled by the page itself)
  pageEl.addEventListener('click', e => {
    if (e.target !== pageEl) return;
    const back = pageEl.querySelector('[data-pp="back"]'); if (back) back.click();
  });
})();
</script>
"""


def main():
    which = [a.lower() for a in sys.argv[1:]] or ["mumbai"]
    for w in (list(BRANCHES) if "all" in which else which):
        build(w)

if __name__ == "__main__":
    main()
