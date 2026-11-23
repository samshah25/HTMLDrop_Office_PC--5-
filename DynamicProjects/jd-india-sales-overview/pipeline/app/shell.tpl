<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JD India sales overview</title>
<link rel="icon" href="/*LOGO*/">
<style>/*FONTS*/
/*CSS*/</style>
</head>
<body>
<a class="skip" href="#main">Skip to the dashboard</a>
<div class="topbar" id="topbar">
  <div class="band-top">
    <a class="brand" href="#" id="home" aria-label="JD India sales overview, back to India"><span class="logo"><img src="/*LOGO*/" alt="Justdial"></span><span class="brand-name">India sales overview</span></a>
    <nav class="trail" id="trail" aria-label="Where you are"></nav>
    <div class="controls">
      <div class="seg" id="measure" role="group" aria-label="Measure">
        <button type="button" data-m="deals">Deals</button><button type="button" data-m="rv">RV 3yr</button><button type="button" data-m="cust" title="Unique customers: distinct businesses (docids) with a deal">Customers</button>
      </div>
      <button type="button" class="period" id="periodBtn" aria-haspopup="dialog" aria-expanded="false">
        <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="4.5" width="14" height="12.5" rx="2"/><path d="M3 8.5h14M7 3v3M13 3v3"/></svg>
        <span id="periodLabel"></span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
      <button type="button" class="period rules" id="rulesBtn" aria-haspopup="dialog" aria-expanded="false" title="Rules: leave out big deals; what counts as too few to compare">
        <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M3.5 6.5h8M15.5 6.5h1M3.5 13.5h2M9.5 13.5h7"/><circle cx="13.5" cy="6.5" r="2"/><circle cx="7.5" cy="13.5" r="2"/></svg>
        <span id="rulesLabel">All deals</span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
    </div>
  </div>
</div>
<header class="band" id="band">
  <div class="hero" id="hero" aria-live="polite"></div>
  <div class="tally" id="tally"></div>
</header>

<main id="main">
  <div class="row r1">
    <section class="card map-card" aria-labelledby="mapH">
      <div class="card-h"><h2 id="mapH"></h2><div class="seg small" id="mapMode" role="group" aria-label="Map style"><button type="button" data-v="map">Map</button><button type="button" data-v="tiles">Tiles</button></div></div>
      <div class="map-wrap" id="mapWrap"><svg id="map" role="img" aria-labelledby="mapH"></svg><div class="tiles" id="tiles" role="group" aria-labelledby="mapH" hidden></div></div>
      <div class="legend map-foot" id="mapLegend"></div>
      <p class="hint" id="mapHint"></p>
    </section>
    <section class="card" aria-labelledby="bridgeH">
      <div class="card-h"><h2 id="bridgeH">Where the change came from</h2></div>
      <div id="bridge"></div>
    </section>
    <section class="card rank-card" aria-labelledby="rankH">
      <div class="card-h"><h2 id="rankH"></h2><div class="seg small" id="kids" role="group" aria-label="Rank by"></div></div>
      <label class="search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="rankSearch" type="search" placeholder="Find" autocomplete="off"></label>
      <div class="rank" id="rank" tabindex="-1"></div>
    </section>
  </div>
  <div class="row r2">
    <section class="card" aria-labelledby="trendH">
      <div class="card-h"><h2 id="trendH"></h2></div>
      <div id="trend"></div>
    </section>
    <section class="card" aria-labelledby="mixH">
      <div class="card-h"><h2 id="mixH">What kind of deals</h2></div>
      <div id="mix"></div>
    </section>
    <section class="card" aria-labelledby="quadH">
      <div class="card-h"><h2 id="quadH"></h2></div>
      <div id="quad"></div>
    </section>
  </div>
  <section class="card conc" aria-labelledby="concH">
    <div class="card-h"><h2 id="concH">How concentrated the deals are</h2><p class="sub" id="concSub"></p></div>
    <canvas id="conc" aria-labelledby="concSub"></canvas>
    <div class="conc-ctl" id="concCtl">
      <label for="concR">Top <b id="concPct" class="tn">10%</b> of pincodes</label>
      <input type="range" id="concR" min="0.5" max="100" step="0.5" value="10">
      <p id="concOut" aria-live="polite"></p>
    </div>
  </section>
  <section class="card table-card" aria-labelledby="tableH">
    <div class="card-h"><h2 id="tableH"></h2>
      <div class="table-tools">
        <label class="search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="tableSearch" type="search" placeholder="Find" autocomplete="off"></label>
        <button type="button" class="btn" id="moreCols" aria-pressed="false">Mix columns</button>
        <button type="button" class="btn" id="csv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV</button>
      </div>
    </div>
    <p class="hint swipe">Swipe the table sideways for more columns.</p>
    <div class="tbl" id="tbl"></div>
  </section>
  <footer class="notes" id="notes"></footer>
</main>

<div class="dim" id="dim" hidden></div>
<aside class="drawer" id="drawer" aria-hidden="true" aria-labelledby="drawerH" tabindex="-1">
  <button type="button" class="close" id="drawerClose" aria-label="Close"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg></button>
  <div id="drawerBody"></div>
</aside>
<div class="pop" id="periodPop" role="dialog" aria-label="Choose dates" hidden></div>
<div class="pop rules-pop" id="rulesPop" role="dialog" aria-label="Rules" hidden></div>
<div class="tip" id="tip" role="tooltip" hidden></div>

<script type="application/json" id="borders">/*BORDERS*/</script>
<script type="application/json" id="districts">/*DISTRICTS*/</script>
<script type="application/json" id="data">/*DATA*/</script>
<script>/*JS*/</script>
</body>
</html>
