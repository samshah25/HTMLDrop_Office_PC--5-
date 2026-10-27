r"""
Saved copy of the presentation feed: one file per day, pres_store\YYYY-MM-DD.tsv.gz, next to this script.

The feed keeps only about 6 months (on 14 Oct 2026 its first day was 14 Apr 2026), so this saved copy is the only
record of older days. NEVER DELETE THE pres_store FOLDER: days the feed has dropped cannot be fetched again.

Rules:
- days in the last RECHECK_DAYS are fetched again on every run (late entries and corrections land there);
- older days come from the saved copy and are not fetched again;
- an empty answer never replaces a saved day that has rows (the feed drops old days, and it can hiccup);
- a day is saved only when the feed had rows that day (for anywhere in India), so a feed outage is not saved as
  "no presentations".

Each file holds the feed's header and, unchanged, the feed's rows for this city's pincodes (all employee types,
all points). The counting rules (JDA/Both, Points or Revenue > 0) stay in the refresh script.
Days restored from an earlier dashboard page, after the feed had dropped them, are listed in pres_store\RECOVERED.txt.
"""
import datetime
import gzip
import os
import time
import urllib.request

FEED = "http://192.168.1.199:81/cron/presentation/cron/downloadPresentationData.php?date={}"
RECHECK_DAYS = 14


class PresStore:
    def __init__(self, folder, keep_pincode, log=print):
        self.folder, self.keep_pincode, self.log = folder, keep_pincode, log
        self.stats = {"saved": 0, "fetched": 0, "kept over empty answer": 0, "not in feed": 0, "failed": 0}
        os.makedirs(folder, exist_ok=True)

    def path(self, day):
        return os.path.join(self.folder, day.isoformat() + ".tsv.gz")

    def read(self, day):
        p = self.path(day)
        if not os.path.exists(p):
            return None
        with gzip.open(p, "rt", encoding="utf-8", newline="") as f:
            return f.read()

    def write(self, day, text):
        p = self.path(day)
        tmp = p + ".tmp"
        with gzip.open(tmp, "wt", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp, p)

    def city_rows(self, text):
        """(header + this city's rows as one text, number of city rows, number of feed rows)."""
        lines = [l.rstrip("\r") for l in text.strip("\n").split("\n")]
        if not lines or not lines[0].strip():
            return "", 0, 0
        header = lines[0].split("\t")
        if "Pincode" not in header:
            return "", 0, 0
        ix, keep, total = header.index("Pincode"), [], 0
        for line in lines[1:]:
            if not line.strip():
                continue
            total += 1
            parts = line.split("\t")
            if len(parts) == len(header) and self.keep_pincode(parts[ix].strip()):
                keep.append(line)
        return "\n".join([lines[0]] + keep), len(keep), total

    @staticmethod
    def n_rows(text):
        return sum(1 for l in text.strip("\n").split("\n")[1:] if l.strip()) if text else 0

    def fetch(self, day):
        for attempt in range(5):
            try:
                with urllib.request.urlopen(FEED.format(day.isoformat()), timeout=60) as resp:
                    return resp.read().decode("utf-8", errors="replace")
            except Exception as e:
                if attempt == 4:
                    self.log(f"  presentation feed failed for {day}: {e}")
                    return None
                time.sleep(3 * (attempt + 1))

    def day_text(self, day, last_day):
        """The day's rows for this city as feed text, or None when the day can't be had (no saved copy, fetch failed)."""
        saved = self.read(day)
        if saved is not None and (last_day - day).days >= RECHECK_DAYS:
            self.stats["saved"] += 1
            return saved
        raw = self.fetch(day)
        time.sleep(0.3)   # go easy on the feed server
        if raw is None:
            self.stats["failed"] += 1
            return saved
        text, n_city, n_feed = self.city_rows(raw)
        if n_feed == 0:   # nothing anywhere: dropped from the feed, not loaded yet, or an outage
            if saved is not None:
                self.stats["kept over empty answer"] += 1
                if self.n_rows(saved):
                    self.log(f"  {day}: the feed sent nothing; kept the saved copy ({self.n_rows(saved)} rows)")
                return saved
            self.stats["not in feed"] += 1
            return raw   # empty, as before: the day counts as no presentations
        self.stats["fetched"] += 1
        if text != saved:
            self.write(day, text)
        return text

    def summary(self):
        return ", ".join(f"{k} {v}" for k, v in self.stats.items() if v)
