# Marketing Reach Builder

A self-serve page (title "Justdial Reach Builder") where a marketer picks business categories, sees how many real businesses
can be reached by phone, landline or email, and compares reach and cost across 5 outreach channels
(WhatsApp, SMS, Email, AI bot calling, human calling). The "launch campaign" part is a demo - nothing is sent.
Status: live on HTML Drop (data frozen at 19 Sep 2026)  ·  Owner: Priyal  ·  Last updated: 28 Oct 2026

## Where it runs
- Office link (HTML Drop, folder dashboard): `http://172.29.65.188:8150/s/marketing-reach-builder/` (slug `marketing-reach-builder`, "link only", not on the master dashboard).
- Sync: folder dashboard -> uploaded by `..\_htmldrop\htmldrop_sync.py` on Mondays (end of the weekly b2b run) or on request, only if a file here changed. Last upload 16 Oct 2026 (files unchanged since 19 Sep 2026).
- Main file to open: `self-serve-dashboard.html` (needs `reach-data.js` next to it). No scheduled task of its own.
- Old local option (not used since 22 Oct 2026): port 8090 via `..\_launcher`.

## How it works (the flow)
1. `reach-data.js` (frozen data file, 19 Sep 2026) -> 2. loaded by `self-serve-dashboard.html` in the browser -> 3. all counting and costs are done in the page (no server, no network calls except Google Fonts and the Justdial logo image).
Screens: **1 Build Audience** (keywords / sales groups + filters) -> **2 Channels** (reach + cost per channel) -> **3 Outreach Plan** (funnel, expected responses, cost; assumptions editable) -> "Create Campaign" / "My Campaigns" (demo).

## Data sources
| Source | Table / file | Read how | Refreshed |
|---|---|---|---|
| `reach-data.js` (21.5 MB) | `REACH_DATA.cats` = 280 category names (electronics / appliances / computers / mobiles etc.); `REACH_DATA.rows` = 377,459 businesses | static file in the page | Never - frozen 19 Sep 2026. **How it was built (query, source table, script) is Unknown - confirm with Priyal**; no build script exists on D: |

Each row = `[docid, rating, review count, contact flags, [category numbers], year]`.
Contact flags: 1 = has mobile phone, 2 = has landline, 4 = has email (added together).
Counts in the file (checked 28 Oct 2026): phone 357,932 · landline 64,086 · email 141,900 · phone or landline 376,055.
The last field is a year (1950-2026 on 178,378 rows, 0 on the other 199,081); the page does **not** use it - meaning Unknown - confirm with Priyal.
The file holds Justdial docids: keep it on internal hosts only (HTML Drop), never on a public site.

## Rules and definitions (as found in the code)
- **Category match**: a keyword matches every category whose name contains it (e.g. "tv" -> "tv dealers", "tv repair & services"). If a keyword matches nothing as a phrase, its single words are tried instead, ignoring generic trade words (dealer, distributor, manufacturer, wholesaler, retailer, supplier, service, repair, centre, shop, store, hire, agency, parts, and, on ...).
- **Sales group picker**: lists all categories except 17 non-electronics ones (cable TV operators, software developers, training institutes, horoscope, DTH recharge/broadcast, SIM/recharge/bill-payment, video game parlours, etc.). Picked groups are added to the keyword matches. On screen 2 each matched category can be clicked to exclude it.
- **Audience** = businesses with at least one included category AND rating >= minimum rating AND review count >= minimum reviews. Defaults: rating 4.0+, reviews 10+ (rating options: any / 3.0 / 3.5 / 4.0 / 4.5; reviews in steps of 5). With the defaults the file has 46,732 businesses before the category filter.
- Counts: Total = audience; Phone / Landline / Email = audience with that contact; **Callable** = phone or landline.
- **Location**: only New Delhi / Delhi NCR has real data. The state/city filter does not filter rows - if the chosen places exclude New Delhi (city) or Delhi NCR (state), the search returns nothing with a "only Delhi NCR is live" message; "All" or any choice that includes Delhi uses the whole file. Default = Delhi NCR / New Delhi.
- **Reachable per channel**: Email -> businesses with email; AI bot and human calling -> callable (phone or landline); WhatsApp and SMS -> phone.
- **Targeted** = reachable x "% of audience you want to reach" (default 40%, one slider for all, then per channel).
- **Cost and funnel (default rates and assumptions, editable on screen 3)**:

| Channel | Rate | Funnel defaults | Billed on | Response rate band |
|---|---|---|---|---|
| WhatsApp | Rs 5 per open | 90% delivered, 50% read | read (opened) | 4-6% of read |
| SMS | Rs 1 per delivered | 95% delivered | delivered | 1-3% of delivered |
| Email | Rs 1 per open | 75% inboxed, 20% opened | opened | 2-4% of opened |
| AI bot calling | Rs 3.5 per 30-sec pulse | 35% connected, 2 pulses per connected call | connected x pulses | 4-6% of connected |
| Human calling | Rs 7.5 per minute talked | 45% connected, 2 minutes per connected call | connected x minutes | 4-6% of connected |

- Responses are always shown as a low-high range (from the rate band), never one number. Money is rounded to whole rupees, Indian digit grouping.
- **Campaigns are a demo**: "Create Campaign" only stores the campaign in the open browser tab (lost on reload); "Simulate Approval" shows made-up "live" numbers (fixed per campaign name). Nothing is sent to anyone or saved anywhere.

## Files
| File | What it does |
|---|---|
| `self-serve-dashboard.html` | The whole app (layout, rules, costs, demo campaign screens), ~107 KB |
| `reach-data.js` | Frozen data: 280 categories + 377,459 businesses (21.5 MB) |

## How to run / rebuild from scratch
1. Open locally: double-click `D:\claude\01 Dashboards\marketing_reach_builder\self-serve-dashboard.html` (both files in the same folder).
2. Push a change to the office link: `"D:\claude\01 Dashboards\_python_env\Scripts\python.exe" "D:\claude\01 Dashboards\_htmldrop\htmldrop_sync.py" --only dynamic` (or `--force marketing-reach-builder`), or double-click `..\_htmldrop\SYNC FOLDER DASHBOARDS NOW.bat`.
3. Rebuild `reach-data.js` from the database: Unknown - confirm with Priyal (no script found). If it is redone, it should come from `01 Dashboards\b2b_master` (the single b2b source) and keep the row format above.
Credentials needed: none for the page. HTML Drop upload uses the login file named in `..\_htmldrop\README.md`.

## Checks
- Browser console shows `Reach Builder loaded 377459 businesses, 280 categories`.
- `..\_htmldrop\sync_state_dynamic.json` -> `marketing-reach-builder` has the latest upload time.

## Known issues / open questions
- Data source, pull date logic and the meaning of the year field are not documented - Unknown - confirm with Priyal.
- Delhi only; other cities return zero.
- Channel rates and funnel percentages are built-in defaults - who agreed them is Unknown - confirm with Priyal.

## Change log
- 28 Oct 2026 - README written from the code (Claude)
- 16 Oct 2026 - moved from "Marketing Reach Builder" folder into `01 Dashboards\marketing_reach_builder`; uploaded to HTML Drop (`marketing-reach-builder`); local port 8090 added to the launcher.
- 19 Sep 2026 - current page and data files saved (DASHBOARD LINKS lists the data as of 19 Sep 2026).
