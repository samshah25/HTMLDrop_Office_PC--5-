<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JD ME team</title>
<link rel="icon" href="/*LOGO*/">
<style>/*FONTS*/
/*CSS*/</style>
</head>
<body>
<a class="skip" href="#main">Skip to the dashboard</a>
<div class="topbar" id="topbar">
  <div class="band-top">
    <a class="brand" href="#" id="home" aria-label="ME team, Mumbai: back to the dashboard"><span class="logo"><img src="/*LOGO*/" alt="Justdial"></span><span class="brand-txt"><span class="brand-name"><span id="brandWho">ME</span> team <span class="city">Mumbai</span><span class="linetag" id="lineTag" hidden></span></span><span class="upd-top" id="updTop"></span></span></a>
    <div class="controls">
      <div class="seg views mode" id="modeSw" role="group" aria-label="People"><button type="button" data-mode="me" title="MEs: the people who took the appointments">ME</button><button type="button" data-mode="tme" class="vtme" title="TMEs: the people who fixed the appointments (the page reloads)">TME</button></div>
      <div class="seg views" id="viewSw" role="group" aria-label="Show"><button type="button" data-view="table">Table</button><button type="button" data-view="team">Overview</button></div>
    </div>
    <div class="right">
      <div class="pgrp">
      <button type="button" class="dstep" id="dayPrev" aria-label="Previous day" title="Previous day" hidden><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M12 5l-5 5 5 5"/></svg></button>
      <button type="button" class="period" id="periodBtn" aria-haspopup="dialog" aria-expanded="false">
        <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="4.5" width="14" height="12.5" rx="2"/><path d="M3 8.5h14M7 3v3M13 3v3"/></svg>
        <span id="periodLabel"></span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
      <button type="button" class="dstep" id="dayNext" aria-label="Next day" title="Next day" hidden><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M8 5l5 5-5 5"/></svg></button>
      </div>
      <button type="button" class="period tlbtn" id="tlBtn" aria-haspopup="dialog" aria-expanded="false" title="Show one manager's or team leader's team" aria-label="Team: all teams">
        <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="7.5" cy="7" r="2.8"/><path d="M2.5 16c.6-2.8 2.6-4.3 5-4.3s4.4 1.5 5 4.3"/><circle cx="14" cy="7.8" r="2.2"/><path d="M13.6 11.7c2 .1 3.4 1.4 3.9 3.6"/></svg>
        <span id="tlLabel">All teams</span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
      <button type="button" class="period icon-only tlclear" id="tlClear" title="Show all teams" aria-label="Show all teams" hidden><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5.5 5.5l9 9M14.5 5.5l-9 9"/></svg></button>
      <button type="button" class="period icon-only" id="setBtn" aria-haspopup="dialog" aria-expanded="false" title="Settings" aria-label="Settings">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      </button>
    </div>
  </div>
</div>
<header class="band" id="band">
  <div class="hero2" id="hero" aria-live="polite"></div>
</header>

<main id="main">
  <div id="vTeam">
    <!-- TME mode (2026-10-30): one section at a time, picked here; the row stays under the top bar -->
    <nav class="tsec" id="tSec" aria-label="Sections" hidden><button type="button" data-sec="teams">TME teams → ME managers</button><button type="button" data-sec="tmes">TMEs <small></small></button><button type="button" data-sec="sum">Summary</button></nav>
    <section class="card sumcard" id="sumCard" aria-label="Summary" hidden><div class="sumg"><div id="sumL"></div><div id="sumR"></div></div></section>


    <section class="card tmstrip" aria-labelledby="tmH">
      <div class="card-h"><div><h2 id="tmH">Where the appointments came from</h2><p class="sub" id="tmSub">By TME team</p></div></div>
      <div class="tiles3" id="teams"></div>
    </section>

    <!-- TME mode (2026-10-30): where the appointments went, from the TME teams to the ME managers' teams -->
    <section class="card flowcard" id="flowCard" aria-labelledby="flowH" hidden>
      <div class="card-h">
        <div><h2 id="flowH">Where the appointments went</h2><p class="sub" id="flowSub"></p></div>
        <div class="tctools"><!-- the From: TME teams | TME managers' teams switch was removed on 31 Oct 2026 (the user: not needed, cluttered) --><div class="xlv" id="flowMw"><span class="slab" id="flowMLab">Measure</span><div class="seg small" id="flowM" role="group" aria-labelledby="flowMLab"><button type="button" data-v="c">Conversion</button><button type="button" data-v="a">Attended %</button></div></div><div class="xlv"><span class="slab" id="flowVLab">Show</span><div class="seg small" id="flowV" role="group" aria-labelledby="flowVLab"><button type="button" data-v="conv">Who converts</button><button type="button" data-v="lines">Lines</button><button type="button" data-v="grid">Share grid</button></div></div></div>
      </div>
      <p class="flcap" id="flowFrom">From: TME teams</p>
      <div class="flsvg" id="flowSvg"></div>
      <p class="flcap">To: ME managers' teams</p>
      <div id="flowDet"></div>
    </section>

    <!-- TME mode (2026-10-30): the ME managers' teams as cards, for all TME teams or one -->
    <section class="card mgrcard" id="mgrCard" aria-labelledby="mgrH" hidden>
      <div class="card-h"><div><h2 id="mgrH">The ME managers' teams</h2><p class="sub" id="mgrSub"></p></div></div>
      <div class="sortrow"><span class="slab" id="mgrTLab">TME team</span><div class="chips" id="mgrT" role="group" aria-labelledby="mgrTLab"></div></div>
      <div class="tiles3 mgrtiles" id="mgrTiles"></div>
    </section>

    <!-- one card for the team: managers / team leaders (the ladder) or MEs (the list); Show is shared with the Table -->
    <section class="card tmcard" aria-labelledby="tcH">
      <div class="card-h">
        <div><h2 id="tcH">Your team</h2><p class="sub" id="tcSub"></p></div>
        <div class="tctools">
          <div class="xlv" id="ovLvW"><span class="slab" id="ovLvLab">Show</span><div class="seg small" id="ovLv" role="group" aria-labelledby="ovLvLab"><button type="button" data-l="1">Managers</button><button type="button" data-l="2">Team leaders</button><button type="button" data-l="3">MEs</button></div></div>
          <div class="xlv" id="meStyleW"><span class="slab" id="meStyleLab">View</span><div class="seg small" id="meStyle" role="group" aria-labelledby="meStyleLab"><button type="button" data-v="bars" title="One bar per line: appointments given, attended, deals closed, with attended % and conversion">Funnel</button><button type="button" data-v="shares" title="Appointments given, attended and deals closed of each line, split by TME team">Team shares</button></div></div>
          <label class="search mesearch" id="meSearchW"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="meSearch" type="search" placeholder="Find an ME, TL or manager" autocomplete="off" aria-label="Find an ME, team leader or manager"></label>
        </div>
      </div>
      <div id="ladPane">
        <div class="lad" id="lad"></div>
        <div class="lkey" id="ladKey"></div>
      </div>
      <div id="mePane" hidden>
        <div class="sortrow"><span class="slab" id="sortLab">Order by</span>
          <div class="chips" id="sortBy" role="group" aria-labelledby="sortLab"><button type="button" data-v="n">Most appointments given</button><button type="button" data-v="att">Lowest attended %</button><button type="button" data-v="deals">Most deals closed</button><button type="button" data-v="uneven">Uneven attended across teams</button><button type="button" data-v="one">Appointments given mostly from one team</button></div>
        </div>
        <div id="meList"></div>
      </div>
    </section>
    <!-- Super Cat skewness (2026-10-19): moved to the end and hidden on 31 Oct 2026 (the user is still working on it);
         it shows only with sk=1 in the page link -->
    <section class="card skcard" id="skCard" aria-labelledby="skH" hidden>
      <div class="card-h"><div><h2 id="skH">Skewness factor · Super Cat</h2><p class="sub" id="skSub"></p></div></div>
      <div class="skb" id="skBody"></div>
    </section>
  </div>
  <div id="vTable" hidden>
    <section class="card" id="bdCard" aria-labelledby="bdH" hidden>
      <div class="card-h"><div><h2 id="bdH">Bands</h2><p class="sub">How many MEs fall in each band, for the MEs in the table below. Set the cutoffs to suit; click a band to show only those MEs.</p></div><div class="xbtns"><button type="button" class="lnk" id="bdReset">Reset the cutoffs</button><button type="button" class="btn" id="bdClose">Close</button></div></div>
      <p class="sub bdscale" id="bdScale"></p>
      <div class="bands3" id="bands"></div>
    </section>
    <section class="card xcard" aria-labelledby="xH">
      <div class="card-h">
        <div class="xhl"><h2 id="xH">MEs</h2>
          <div class="xlv" id="xLvW"><span class="slab" id="xLvLab">Show</span><div class="seg small" id="xLv" role="group" aria-labelledby="xLvLab"><button type="button" data-l="1">Managers</button><button type="button" data-l="2">Team leaders</button><button type="button" data-l="3">MEs</button></div></div></div>
        <div class="xact">
          <div class="xbtns"><label class="xsearch"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input type="search" id="xSearch" placeholder="Search ME, team leader or manager" aria-label="Search ME, team leader or manager" autocomplete="off"></label><button type="button" class="btn" id="xColsBtn" aria-haspopup="dialog" aria-expanded="false"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 4.5h4v11h-4zM8 4.5h4v11H8zM12.5 4.5h4v11h-4z"/></svg>Columns</button><button type="button" class="btn" id="xCsv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>Download for Excel</button></div>
        </div>
      </div>
      <div class="xchips" id="xChips" aria-live="polite"></div>
      <div class="tbl xtbl" id="xTbl"></div>
      <div class="xpg" id="xPager"></div>
      <p class="hint" id="xKey"></p>
    </section>
  </div>
  <div id="vChecks" hidden>
    <p class="back"><button type="button" class="lnk" id="backBtn">← Back to the dashboard</button></p>
    <section class="card queue-card" aria-labelledby="qH" id="queue">
      <div class="card-h">
        <div><h2 id="qH">What to check</h2><p class="sub">Unusual patterns and record problems in these dates. Each one is a prompt to verify, not a finding.</p></div>
        <button type="button" class="btn" id="qCsv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV</button>
      </div>
      <div class="qtools" id="qTools">
        <label class="sel"><span>Check</span><select id="qKind"></select></label>
        <label class="sel"><span>TME team</span><select id="qTeam"></select></label>
        <div class="seg small" id="qSev" role="group" aria-label="Show"><button type="button" data-v="all">All</button><button type="button" data-v="rev">Review</button><button type="button" data-v="info">Information</button></div>
        <div class="seg small" id="qStat" role="group" aria-label="Status"><button type="button" data-v="open">Open</button><button type="button" data-v="done">Checked</button><button type="button" data-v="all">All</button></div>
        <label class="search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="qSearch" type="search" placeholder="Find an ME or TME" autocomplete="off"></label>
      </div>
      <p class="qsum" id="qSum" aria-live="polite"></p>
      <ol class="items" id="items"></ol>
    </section>

    <section class="card" aria-labelledby="pairH">
      <div class="card-h"><div><h2 id="pairH">TME → ME pairings</h2><p class="sub" id="pairSub"></p></div></div>
      <div id="pairs"></div>
    </section>

    <section class="card" aria-labelledby="howH" id="how">
      <div class="card-h"><div><h2 id="howH">How each check works</h2><p class="sub">What raises it, what it is compared with, and what it cannot tell. The limits are fixed for now.</p></div></div>
      <div class="tbl how" id="howTbl"></div>
    </section>
  </div>
  <footer class="foot">
    <details class="notes-box"><summary>How these numbers are counted</summary><div class="notes" id="notes"></div></details>
    <p class="quiet"><button type="button" class="lnk" id="toChecks">Records to verify</button><span class="mu"> · automatic checks on the records, not yet confirmed</span></p>
  </footer>
</main>

<div class="dim" id="dim" hidden></div>
<aside class="drawer" id="drawer" aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="drawerH" tabindex="-1">
  <button type="button" class="close" id="drawerClose" aria-label="Close"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg></button>
  <div id="drawerBody"></div>
</aside>
<div class="pop tlpop" id="tlPop" role="dialog" aria-label="Choose a team leader" hidden></div>
<div class="pop" id="periodPop" role="dialog" aria-label="Choose dates" hidden></div>
<div class="pop setpop" id="setPop" role="dialog" aria-label="Settings" hidden>
  <p class="setl">MEs counted</p>
      <div class="seg cbsw" id="lnSw" role="group" aria-label="MEs counted"></div>
  <p class="seth" id="lnHelp"></p>
  <p class="setl setg">Conversion on</p>
      <div class="seg cbsw" id="cbSw" role="group" aria-label="Conversion on"><button type="button" data-cb="att" title="Deals closed as a share of attended">Attended</button><button type="button" data-cb="given" title="Deals closed as a share of appointments given">Given</button></div>
  <p class="seth">Deals closed as a share of attended, or of appointments given. Applies to the whole dashboard.</p>
  <p class="setl setg">Hot Data and Online</p>
      <div class="seg cbsw" id="hoSw" role="group" aria-label="Hot Data and Online"><button type="button" data-v="0" title="Hot Data and Online as two TME team groups">Separate</button><button type="button" data-v="1" title="Hot Data and Online as one group, Hot Data + Online">Together</button></div>
  <p class="setl setg">Expiry team (Revival)</p>
      <div class="seg cbsw" id="exSw" role="group" aria-label="Expiry team"><button type="button" data-v="1" title="Revival (Expiry) as its own TME team group">Separate</button><button type="button" data-v="0" title="Revival (Expiry) inside Other teams">In other teams</button></div>
  <p class="seth">The TME team groups everywhere: the team cards, Who converts, the ME page and the Table's team columns.</p>
</div>
<div class="pop colspop" id="colsPop" role="dialog" aria-label="Show or hide columns" hidden></div>
<div class="pop colpop" id="colPop" role="dialog" aria-label="Sort and filter this column" hidden></div>
<div class="tip" id="tip" role="tooltip" hidden></div>

<script type="application/json" id="data">/*DATA*/</script>
<script>/*JS*/</script>
</body>
</html>
