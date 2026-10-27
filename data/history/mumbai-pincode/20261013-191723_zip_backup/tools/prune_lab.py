"""Remove what the UI lab never shows (Sarvesh 2026-09-30: "what user sees shall only remain").

The lab is built from the main dashboard + the sales-head transform, which carry features the lab has since hidden or
replaced. prune(s) deletes their markup, code and styles from the finished page, asserting every edit, and then checks
that none of the removed names is still referenced anywhere (a leftover call would be a runtime error).

Removed: colour customiser, PDF export, 'Show every pincode', quick-view buttons + colour strip + category cards,
'How this is counted', the hidden period line, the hidden split-rate column, the unused manager table, the map panel's
hidden 'advanced' block, the old ▸ row-expand panels (and their hover tooltips), the old sales-head comparison table,
the hidden 'Back to all pincodes' button. Also fixes the refresh path: a ?pin= link now opens the current window.
"""
import re


class _S:
    def __init__(self, s):
        self.s = s

    def rep(self, a, b="", n=1):
        k = self.s.count(a)
        assert k == n, ("prune: expected %d, found %d: %r" % (n, k, a[:90]))
        self.s = self.s.replace(a, b)

    def sub(self, pat, b="", n=1, flags=re.S):
        self.s, k = re.subn(pat, b, self.s, flags=flags)
        assert k == n, ("prune: pattern matched %d times (want %d): %r" % (k, n, pat[:90]))

    def lines(self, pat, min_n=1):
        """drop whole lines matching a regex (CSS rules for removed elements)"""
        out, k = [], 0
        for line in self.s.split("\n"):
            if len(line) < 400 and re.match(pat, line):
                k += 1; continue
            out.append(line)
        assert k >= min_n, ("prune: no line matched %r" % pat)
        self.s = "\n".join(out)

    def block(self, start, n=1, optional=False):
        """drop a statement / function that starts with `start`: through the brace that closes its first '{',
        then the rest of that line (e.g. `});`). Strings, template literals and comments are skipped."""
        for _ in range(n):
            i = self.s.find(start)
            if i < 0 and optional:
                return
            assert i >= 0, ("prune: block not found: %r" % start[:90])
            j = _close(self.s, self.s.index("{", i))
            e = self.s.find("\n", j)
            ls = self.s.rfind("\n", 0, i) + 1
            if self.s[ls:i].strip() == "":
                i = ls
            self.s = self.s[:i] + self.s[e + 1:]
        assert self.s.find(start) < 0 or n > 1, ("prune: block still present: %r" % start[:90])


def _close(s, i):
    """index of the '}' matching the '{' at s[i]; skips '..', "..", `..${..}..`, // and /* */"""
    depth, k, stack = 0, i, []
    while k < len(s):
        c = s[k]
        if stack and stack[-1] == "`":
            if c == "\\": k += 2; continue
            if c == "`": stack.pop()
            elif c == "$" and s[k + 1:k + 2] == "{": stack.append("${"); depth += 1; k += 1
            k += 1; continue
        if c in "'\"":
            q = c; k += 1
            while s[k] != q:
                k += 2 if s[k] == "\\" else 1
            k += 1; continue
        if c == "`": stack.append("`"); k += 1; continue
        if s.startswith("//", k): k = s.index("\n", k); continue
        if s.startswith("/*", k): k = s.index("*/", k) + 2; continue
        if c == "/":   # a regex literal when it follows an operator / opening bracket / keyword, e.g. .replace(/"/g, ...)
            p = k - 1
            while p >= 0 and s[p] in " \t": p -= 1
            prev = s[p] if p >= 0 else ""
            if prev in "(,=:[!&|?{};+-*%<>~^\n" or s[max(0, p - 5):p + 1].endswith("return"):
                k += 1; cls = False
                while k < len(s) and (cls or s[k] != "/"):
                    if s[k] == "\\": k += 1
                    elif s[k] == "[": cls = True
                    elif s[k] == "]": cls = False
                    elif s[k] == "\n": break
                    k += 1
                k += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if stack and stack[-1] == "${": stack.pop()
            elif depth == 0: return k
        k += 1
    raise AssertionError("prune: unbalanced braces")


GONE = ["renderColorPanel", "colorPanelToggle", "loadColors", "saveColors", "exportPdf", "printExportArea", "exporting-print",
        "viewAllBtn", "viewAllActive", "savedViewState", "viewSeg", "syncViewSeg", "applyView", "stripBar", "layer-card",
        "dqNotes", "renderDQ", "deployNote", "periodHeaderText", "adv-col", "show-advanced", "adv-section", "renderManagerTable",
        "mgrTable", "expandRowHtml", "expandedPincodes", "pin-expand-cell", "computeSalesGroupsForPincode",
        "computeMonetizableSalesGroupsForPincode", "penetrationForSalesGroup", "constituentSalesGroupsFor", "subvertTooltip",
        "subvert-bar-row", "rawMonetizablePenetration", "displayLabel", "benchBlock", "bench-wrap", "onlyOrAll",
        "Back to all pincodes", "__labMonthlyGaps", "LIST[", "PAID[", "bandSettingsBtn", "bandEditor", "updateBandUI",
        "addBandBtn", "resetBandBtn", "cutoff1", "cutoff2"]


def prune(s):
    P = _S(s)
    # ---- Band settings (button + editor): the cutoff is edited in the grouping rows (the lab); two-band mode was off ----
    P.sub(r'\n\s*<button class="mini-btn" id="bandSettingsBtn"[^\n]*')
    P.sub(r'<div class="controls band-editor" id="bandEditor".*?\n</div>\n')
    P.block("document.getElementById('bandSettingsBtn').addEventListener(")
    P.block("['cutoff1','cutoff2'].forEach((id, i) => {")
    P.block("function updateBandUI() {")
    P.block("document.getElementById('addBandBtn').addEventListener(")
    P.block("document.getElementById('resetBandBtn').addEventListener(")
    P.rep("\nupdateBandUI();\n", "\n")
    P.rep("\n    updateBandUI();\n", "\n")
    P.rep("cutoffs[1] = c1; document.getElementById('cutoff1').value = c1;", "cutoffs[1] = c1;")
    P.rep("cutoffs[2] = c2; document.getElementById('cutoff2').value = c2;", "cutoffs[2] = c2;")
    P.lines(r"\s*(\.sum-head #bandSettingsBtn|\.band-editor|\.band-swatch)", min_n=1)
    # ---- the source's `html, body { overflow-x: hidden }`: nothing overflows sideways (checked on every tab at 1280 and
    #      1500px), and it made body a scroll box, which silently broke every position: sticky ----
    P.rep("  html, body { max-width: 100%; overflow-x: hidden; }\n")
    # ---- colour customiser ----
    P.rep('  <button id="colorPanelToggle" class="mini-btn" style="margin-left:auto;">Customize colors</button>\n')
    P.rep('<div class="controls" style="padding-top:0;">\n  <div id="colorPanel" class="color-panel"></div>\n</div>\n')
    P.block("function renderColorPanel() {")
    P.block("document.getElementById('colorPanelToggle').addEventListener(")
    P.rep("\nrenderColorPanel();\n", "\n")
    P.rep("let COLORS = loadColors();", "let COLORS = Object.assign({}, DEFAULT_COLORS);   // the lab sets its own palette (no customiser)")
    P.block("function loadColors() {")
    P.sub(r"function saveColors\(\) \{[^\n]*\}\n")
    P.lines(r"\s*\.color-(panel|row)\b")
    # ---- PDF export ----
    P.rep('      <button class="mini-btn export-btn" id="exportPdfBtn">Export PDF</button>\n')
    P.rep('<div id="printExportArea" style="display:none;"></div>\n')
    P.sub(r"  @media print \{\n(?:[^\n]*\n)*?  \}\n")
    P.lines(r"\s*(#printExportArea|body\.exporting-print)")
    P.block("function exportPdf() {")
    P.block("window.addEventListener('afterprint',")
    P.rep("document.getElementById('exportPdfBtn').addEventListener('click', exportPdf);\n")
    # ---- 'Show every pincode' ----
    P.sub(r'      <button class="mini-btn" id="viewAllBtn"[^\n]*</button>\n')
    P.rep("let viewAllActive = false;\nlet savedViewState = null;\n")
    P.block("document.getElementById('viewAllBtn').addEventListener(")
    P.rep("#colorPanelToggle, #colorPanel, #exportPdfBtn, #viewAllBtn,\n .adv-col { display: none !important; }\n")
    # ---- quick views, colour strip, category cards (the summary line and 'N hidden' note stay) ----
    P.sub(r'    <div class="seg" id="viewSeg".*?</div>\n')
    P.rep('  <div class="strip-bar" id="stripBar" aria-hidden="true"></div>\n  <div class="cards strip" id="cards"></div>\n')
    P.sub(r"  const layerCard = \(k\) => [^\n]*\n")
    P.sub(r"  document\.getElementById\('cards'\)\.innerHTML = [^\n]*\n")
    P.sub(r"  document\.getElementById\('stripBar'\)\.innerHTML = [^\n]*\n")
    P.rep("  syncViewSeg();\n")
    P.block("function syncViewSeg() {")
    P.block("function applyView(v) {")
    P.block("document.getElementById('cards').addEventListener('click'")
    P.block("document.getElementById('cards').addEventListener('keydown'")
    P.sub(r"document\.getElementById\('stripBar'\)\.addEventListener[^\n]*\n")
    P.sub(r"document\.getElementById\('viewSeg'\)\.addEventListener[^\n]*\n")
    P.block("  // (2) category chips: a click shows ONLY that category")
    P.sub(r"  const cards = document\.getElementById\('cards'\);\n")
    P.block("  cards.addEventListener('click'")
    P.block("  cards.addEventListener('keydown'")
    P.lines(r"\s*\.(cards|strip-bar)\b")
    P.lines(r"\s*\.card(\.layer|\.layer-off|\[data-tip\]| \.| \{|\.layer-card)")
    P.rep("#viewSeg, #stripBar, #cards { display: none !important; }\n")
    P.lines(r"\s*\.strip \.card")
    P.sub(r" \.cards\.strip \{[^}]*\} \.strip \.card\.layer-card \{[^}]*\}", "")        # inside the phone-width rule
    P.lines(r".*td\.pin-expand-cell")
    # ---- 'How this is counted' (now in tooltips) ----
    P.rep('<div class="layout" style="grid-template-columns: 1fr;">\n  <div class="panel">\n    <details class="fold"><summary>How this is counted</summary><div class="note" id="dqNotes"></div></details>\n  </div>\n</div>\n')
    P.block("function renderDQ() {")
    P.sub(r"\n[ \t]*renderDQ\(\);[^\n]*", "", n=1)
    P.block("function deployNote() {", optional=True)   # Kolkata page only
    P.lines(r"\s*#dqNotes")
    # ---- hidden period line ----
    P.sub(r'  <p id="periodHeaderText"[^>]*>[^\n]*</p>\n')
    P.sub(r"document\.getElementById\('periodHeaderText'\)\.textContent = [^\n]*\n")
    # ---- hidden split-rate column ----
    P.rep(" +\n    `<col class=\"adv-col\" style=\"width:${COLUMN_WIDTHS.split_rate_pct}px;\">`;", ";")
    P.sub(r" \+\n    headerCellHtml\('split_rate_pct', 'Split-(?:deal|sale) Rate %', 'adv-col'\);", ";")
    P.sub(r'\n      <td class="adv-col num-col">\$\{fmtPct\(r\.split_rate_pct\)\}</td>', "")
    P.lines(r"\s*(#dataTable col\.adv-col|body\.show-advanced|\.adv-col|\.adv-section)")
    # ---- unused manager table ----
    P.block("function renderManagerTable() {")
    P.sub(r"\n[ \t]*renderManagerTable\(\);", "")
    # ---- map detail panel: its hidden 'advanced' block ----
    P.sub(r"\n    <div class=\"adv-section\">.*?\n    </div>", "")
    P.sub(r"  const repRows = \(row\.rep_breakdown \|\| \[\]\).*?\.join\(''\);\n")   # a chained statement, not a block
    # ---- the old ▸ row-expand panels (the pincode window replaced them) ----
    P.rep("    ${expandedPincodes.has(r.pincode) ? expandRowHtml(r, colspan) : ''}\n")
    P.block("  const expandCell = e.target.closest('.pin-expand-cell');\n  if (expandCell) {")
    P.sub(r"let expandedPincodes = new Set\(\);[^\n]*\n")
    P.block("  const _expandRowHtml = expandRowHtml;\n  expandRowHtml = function (r, colspan) {")
    P.sub(r"    const tpl = document\.createElement\('template'\); tpl\.innerHTML = expandRowHtml\(r, 1\);\n.*?    const catsHtml = holder\.innerHTML;\n",
          "    const whoHtml = whoWorked(pin), catsHtml = '';   // the categories are drawn by the lab (pinCatsHtml)\n")
    for f in ["function expandRowHtml(r, colspan) {", "function computeSalesGroupsForPincode(", "function computeMonetizableSalesGroupsForPincode(",
              "function penetrationForSalesGroup(", "function constituentSalesGroupsForDeals(", "function constituentSalesGroupsForMonetizable(",
              "function subvertTooltip() {", "function rawMonetizablePenetration(", "function displayLabel("]:
        P.block(f)
    P.block("document.addEventListener('mouseover', (e) => {\n  const row = e.target.closest('.subvert-bar-row');")
    P.block("document.addEventListener('mouseout', (e) => {\n  const row = e.target.closest('.subvert-bar-row');")
    P.lines(r"\s*(#subvertTooltip|\.expand-(panel|title|table|row))")
    # ---- the old sales-head comparison table (dot plots); the lab's labBench draws 'How it compares' ----
    P.sub(r"  // ---- benchmarking against pincodes with a similar MARKET[^\n]*\n  const LIST = \{\}, PAID = \{\};\n  Object\.entries\(MONETIZABLE_SUB_VERTICALS \|\| \{\}\)\.forEach\([^\n]*\n")
    P.sub(r"  const med = a => \{[^\n]*\n  // rates under 1 get two decimals[^\n]*\n  const fmtN = [^\n]*\n")
    P.block("  function benchBlock(pin) {")
    P.rep("${window.labBench ? window.labBench(pin) : benchBlock(pin)}", "${window.labBench(pin)}")
    P.lines(r"\.bench(\b|-wrap)")
    # ---- the hidden 'Back to all pincodes' button: the ✕ is part of the window's top row from the start ----
    P.rep('        <button class="mini-btn" type="button" data-pp="back">← Back to all pincodes</button>\n')
    P.sub(r"(        <span class=\"pos\">\$\{idx >= 0 \? `\$\{idx \+ 1\} of \$\{order\.length\} in the table's order` : ''\}</span>\n)",
          r'\1        <button class="mini-btn pp-close" type="button" data-pp="back" title="Close (Esc)" aria-label="Close">✕</button>\n')
    # ---- refresh: a ?pin= link opens the window once every layer is in place (was: the old window, too early) ----
    P.rep("  const linkPin = new URL(location.href).searchParams.get('pin');\n  if (linkPin) openPinPage(linkPin, false);\n")
    k = P.s.rindex("</body>")
    P.s = P.s[:k] + "<script>/* a ?pin= link (e.g. after a refresh) opens that pincode's window */\n(function () { const p = new URL(location.href).searchParams.get('pin'); if (p) openPinPage(p, false); })();\n</script>\n" + P.s[k:]

    # nothing removed may still be referenced (outside the embedded data)
    code = "\n".join(l for l in P.s.split("\n") if len(l) < 20000)
    left = [g for g in GONE if g in code]
    if left:
        ctx = []
        for g in left:
            for line in code.split("\n"):
                if g in line: ctx.append(g + " :: " + line.strip()[:160])
        raise AssertionError("prune: still referenced:\n  " + "\n  ".join(ctx))
    return P.s
