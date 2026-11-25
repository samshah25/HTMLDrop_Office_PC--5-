"""Where the shared kit keeps its files (as the Mumbai ME kit's kitpaths.py).
HTML Drop shows everything in the kit folder, so everything private lives OUTSIDE it, in
PRIVATE = C:\ProgramData\Jaipur_tenure_grid_private (or the folder named by JAIPUR_TENURE_PRIVATE_DIR):
environment.py (database logins), data\ (pulls, history, snapshots), run_changes\ (run-to-run change reports), refresh_log.txt.
The kit folder keeps the code, the template and the page."""
import os
import sys

PIPE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(PIPE)
PRIVATE = os.environ.get("JAIPUR_TENURE_PRIVATE_DIR") or os.path.join(os.environ.get("ProgramData") or r"C:\ProgramData", "Jaipur_tenure_grid_private")
DATA = os.path.join(PRIVATE, "data")
CHANGES = os.path.join(PRIVATE, "run_changes")
PAGE = os.path.join(KIT, "jaipur-tenure-split.html")
LOG = os.path.join(PRIVATE, "refresh_log.txt")
if PRIVATE not in sys.path:
    sys.path.insert(0, PRIVATE)            # environment.py lives here after the first run
