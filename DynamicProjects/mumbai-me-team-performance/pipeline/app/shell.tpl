<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>JD ME team performance</title>
<link rel="icon" href="/*LOGO*/">
<style>/*FONTS*/
/*CSS*/</style>
</head>
<body>
<a class="skip" href="#main">Skip to the dashboard</a>
<div class="topbar" id="topbar">
  <div class="band-top">
    <a class="brand" href="#" id="home" aria-label="ME team performance, back to the whole city"><span class="logo"><img src="/*LOGO*/" alt="Justdial"></span><span class="brand-name">ME team performance</span></a>
    <nav class="trail" id="trail" aria-label="Where you are"></nav>
    <div class="controls">
      <button type="button" class="period" id="teamBtn" aria-haspopup="dialog" aria-expanded="false">
        <svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="7.5" cy="7" r="2.6"/><circle cx="13.5" cy="8" r="2.1"/><path d="M2.8 15.5c.6-2.6 2.5-4 4.7-4s4.1 1.4 4.7 4M12 12.2c2.2-.3 4.2.9 5 3.3"/></svg>
        <span id="teamLabel"></span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
      <button type="button" class="period" id="periodBtn" aria-haspopup="dialog" aria-expanded="false">
        <svg viewBox="0 0 20 20" aria-hidden="true"><rect x="3" y="4.5" width="14" height="12.5" rx="2"/><path d="M3 8.5h14M7 3v3M13 3v3"/></svg>
        <span id="periodLabel"></span>
        <svg class="chev" viewBox="0 0 20 20" aria-hidden="true"><path d="M6 8l4 4 4-4"/></svg>
      </button>
    </div>
  </div>
</div>
<header class="band" id="band">
  <div class="hero" id="hero" aria-live="polite"></div>
</header>

<main id="main">
  <div class="row r1">
    <section class="card" aria-labelledby="funH">
      <div class="card-h"><h2 id="funH">Where the appointments went</h2></div>
      <div id="funnel"></div>
    </section>
    <section class="card" aria-labelledby="wkH">
      <div class="card-h"><h2 id="wkH">Week by week</h2></div>
      <div id="weeks"></div>
    </section>
  </div>
  <div class="row r2">
    <section class="card" aria-labelledby="srcH">
      <div class="card-h"><h2 id="srcH">Where appointments come from</h2><p class="sub">TME teams</p></div>
      <div id="sources"></div>
    </section>
    <section class="card" aria-labelledby="mapH">
      <div class="card-h"><h2 id="mapH">Attendance against conversion, by ME</h2></div>
      <div id="scatter"></div>
    </section>
  </div>
  <section class="card" aria-labelledby="sprH">
    <div class="card-h"><h2 id="sprH">How appointments are spread across MEs</h2><p class="sub" id="sprSub"></p></div>
    <div id="spread"></div>
  </section>
  <section class="card" aria-labelledby="hmH">
    <div class="card-h"><h2 id="hmH">Each ME's appointments by TME team</h2>
      <div class="seg small" id="hmMode" role="group" aria-label="Beside appointments, show"><button type="button" data-v="conv">Conversion</button><button type="button" data-v="att">Attendance</button></div></div>
    <div id="heat"></div>
  </section>
  <section class="card table-card" aria-labelledby="tableH">
    <div class="card-h"><h2 id="tableH">Every ME</h2>
      <div class="table-tools">
        <label class="search"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="9" r="5.5"/><path d="M13.2 13.2L17 17"/></svg><input id="tableSearch" type="search" placeholder="Find an ME" autocomplete="off"></label>
        <button type="button" class="btn" id="csv"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3v10M6 9l4 4 4-4M4 16h12"/></svg>CSV</button>
      </div>
    </div>
    <p class="hint swipe">Swipe the table sideways for more columns.</p>
    <div class="tbl" id="tbl"></div>
  </section>
  <footer class="notes" id="notes"></footer>
</main>

<div class="dim" id="dim" hidden></div>
<aside class="drawer" id="drawer" aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="drawerH" tabindex="-1">
  <button type="button" class="close" id="drawerClose" aria-label="Close"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 5l10 10M15 5L5 15"/></svg></button>
  <div id="drawerBody"></div>
</aside>
<div class="pop" id="periodPop" role="dialog" aria-label="Choose dates" hidden></div>
<div class="pop" id="teamPop" role="dialog" aria-label="Choose a team" hidden></div>
<div class="tip" id="tip" role="tooltip" hidden></div>

<script type="application/json" id="data">/*DATA*/</script>
<script>/*JS*/</script>
</body>
</html>
