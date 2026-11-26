"""Where the refresh keeps its files (6 Nov 2026).

In the shared kit (main.py at the kit's top level) the kit folder may be the one HTML Drop shows to everyone, so everything
private lives OUTSIDE it, in PRIVATE = C:\\ProgramData\\ME_dashboard_private (or the folder named by ME_PRIVATE_DIR):
the database logins (environment.py, db_*.env), the cached data (cache\\), the unlocked pages (Mumbai ME Team
Performance.html, manager_pages\\), vault_keys.json and the refresh log. The kit folder keeps the code, the design files and
the sign-in page, "Mumbai ME Team Performance.html" (the same name and place as before; every page inside it is encrypted).

On the analysis PC (pipeline\\main.py with no main.py above it) nothing changes: cache in pipeline\\cache, the pages in the
folder above, the sign-in page in upload\\.
"""
import os
import sys

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
# the branch (2026-11-23, Ahmedabad added): pipeline\city.txt holds the city key (e.g. "ahmedabad"); without it, Mumbai
_ct = os.path.join(PIPE, "city.txt")
CITY = (open(_ct, encoding="utf-8").read().strip().lower() if os.path.isfile(_ct) else "") or "mumbai"
CITY_NAME = CITY.title()
PAGE_NAME = f"{CITY_NAME} ME Team Performance.html"
SHARED_KIT = os.path.isfile(os.path.join(KIT, "main.py"))
PRIVATE = os.environ.get("ME_PRIVATE_DIR") or (
    os.path.join(os.environ.get("ProgramData") or r"C:\ProgramData", "ME_dashboard_private" + ("" if CITY == "mumbai" else "_" + CITY)) if SHARED_KIT else "")
if PRIVATE:
    CACHE = os.path.join(PRIVATE, "cache")
    FULL = os.path.join(PRIVATE, PAGE_NAME)            # the unlocked full page (private)
    KEYS = os.path.join(PRIVATE, "vault_keys.json")
    SIGNIN = os.path.join(KIT, PAGE_NAME)              # the sign-in page HTML Drop shows
    LOGDIR = PRIVATE
    if PRIVATE not in sys.path:
        sys.path.insert(0, PRIVATE)                    # environment.py lives here
else:
    CACHE = os.path.join(PIPE, "cache")
    FULL = os.path.join(KIT, PAGE_NAME)
    KEYS = os.path.join(KIT, "vault_keys.json")
    SIGNIN = os.path.join(KIT, "upload", PAGE_NAME)
    LOGDIR = PIPE
FULL = os.environ.get("ME_REVIEW_OUT") or FULL
MGR = os.path.join(os.path.dirname(FULL), "manager_pages")
# no sign-in (26 Nov 2026, Ahmedabad; the user: "there's no login on ahmedabad page, everyone can see it"): the full page itself,
# with the skewness card, is the page HTML Drop shows at the kit's top level; no sign-in page, no separate Sounak page. The
# manager pages and every other private file stay in PRIVATE.
OPEN_PAGE = CITY == "ahmedabad"
if OPEN_PAGE and PRIVATE and not os.environ.get("ME_REVIEW_OUT"):
    FULL = SIGNIN
# the full page WITH the skewness card, opened only by the sounak.biswas login (25 Nov 2026; Mumbai), beside the full page;
# every other page has the card cut out (build_review.strip_skew). Ahmedabad too (26 Nov 2026, the user: "add similar skewness
# indicator to the Ahmedabad ME dashboard"), and there the card is on the open full page itself (OPEN_PAGE)
SKEW_PAGE = CITY in ("mumbai", "ahmedabad")
# the card compares city by city (26 Nov 2026, Ahmedabad: the branch covers all of Gujarat, 95% of its MEs work in one city and
# Super Cat's share differs by city, Surat 19% to Rajkot 30%; the user chose "within the same city"). Mumbai is one city.
SKEW_BY_CITY = CITY == "ahmedabad"
FULL_SK = FULL[:-5] + " - Sounak.html"
