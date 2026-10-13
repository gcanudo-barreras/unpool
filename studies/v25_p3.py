"""V25 P3: extraction right on >= 80% of confirmed sheets (subjects, times
and arms all `yes`), read from rater A's runs/v25_extraction_check.csv.

    python studies/v25_p3.py [runs/v25_extraction_check.csv] [--answered]

Unit: confirmed sheet. The set is fixed at the file's rows (commit 2729107).
Refuses a verdict while any row is still open: a partial count is not P3.
"""
import csv
import math
import sys

COLS = ("subjects_ok", "times_ok", "arms_ok")


def wilson(k, n, z=1.96):
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def score(rows):
    """-> dict of counts; `open` > 0 means no verdict yet."""
    val = lambda r, c: (r.get(c) or "").strip().lower()
    out = {"n": len(rows),
           "open": sum(1 for r in rows if not all(val(r, c) for c in COLS)),
           "all": sum(1 for r in rows if all(val(r, c) == "yes" for c in COLS))}
    for c in COLS:
        out[c] = sum(1 for r in rows if val(r, c) == "yes")
    return out


def main(path="runs/v25_extraction_check.csv", answered=False):
    """`answered`: score the fully answered rows only -- the set V25 closed on
    (50 of 74, the rater stopped before any rate was computed)."""
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if answered:
        rows = [r for r in rows if all((r.get(c) or "").strip() for c in COLS)]
        print("  scoring the %d fully answered row(s)" % len(rows))
    s = score(rows)
    n = s["n"]
    for c in COLS + ("all",):
        lo, hi = wilson(s[c], n)
        print("  %-12s %3d/%d = %5.1f %%  (Wilson 95 %% %.1f-%.1f)"
              % (c, s[c], n, 100 * s[c] / n, 100 * lo, 100 * hi))
    if s["open"]:
        print("  P3 -- NOT SCORED: %d of %d row(s) still open" % (s["open"], n))
        return 1
    ok = s["all"] / n >= 0.80
    print("  P3 -- %s (threshold 80 %%, unit = confirmed sheet)"
          % ("PASSED" if ok else "FALSIFIED"))
    return 0


def _selftest():
    y, nn = {c: "yes" for c in COLS}, dict({c: "yes" for c in COLS}, arms_ok="no")
    s = score([y, y, y, y, nn])
    assert (s["all"], s["arms_ok"], s["open"]) == (4, 4, 0), s
    assert score([{"subjects_ok": "yes"}])["open"] == 1
    lo, hi = wilson(74, 75)
    assert abs(lo - 0.928) < 1e-3 and abs(hi - 0.998) < 1e-3, (lo, hi)


if __name__ == "__main__":
    _selftest()
    args = [a for a in sys.argv[1:] if a != "--answered"]
    sys.exit(main(*args, answered="--answered" in sys.argv))
