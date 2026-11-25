"""Deals left out of every figure built from the deal records (user decisions). Apply right after loading deals.pkl:
    from exclusions import drop_excluded;  d = drop_excluded(d)
Figures taken from the branch reviews themselves cannot be adjusted and still include these deals."""
EXCLUDE = [
    # parentid, version, why
    ("PXX33.XX33.110510133958.G8B7", "193",
     "Kolkata, 9 Oct 2026, Multiple team, contract value Rs 10.9 lakh (RV 3-yr Rs 9.7 lakh); one deal was 17% of a whole table row. "
     "User, 13 Nov 2026: 'exclude this 10.9 lakh deal'."),
]
KEYS = {(p, v) for p, v, _ in EXCLUDE}

def is_excluded(pid, ver):
    return (str(pid).strip(), str(ver).strip().split(".")[0]) in KEYS

def drop_excluded(df, pid_col="parentid", ver_col="version"):
    """Return df without the excluded deals (rows matched on parentid + version)."""
    if df is None or len(df) == 0 or pid_col not in df or ver_col not in df:
        return df
    keep = [not is_excluded(p, v) for p, v in zip(df[pid_col], df[ver_col])]
    return df[keep]
