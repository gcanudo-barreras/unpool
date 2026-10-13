"""Collapse a campaign's candidate sheets into one row per paper, best first.

    unpool worklist runs/mycampaign_candidates.csv
    unpool worklist runs/*_candidates.csv -o runs/worklist.csv

WHY THIS EXISTS, AND WHY IT IS A SEPARATE SCRIPT
------------------------------------------------------------------------------
`mine.py` writes one row per accepted SHEET. A Source Data workbook holds a
sheet per figure, so one paper routinely contributes 40 rows and a 50-paper
campaign produces a file with a couple of hundred. That file is the record of
what the scanner saw; it is not a list of work.

A user testing this tool got 86 candidate rows, discovered by hand that they
were 10 papers, and reported that "collapsing to one row per paper has no
script anywhere -- it's described in prose only". That was true, and this is
the script.

WHAT IT DECIDES, AND WHAT IT REFUSES TO DECIDE
------------------------------------------------------------------------------
One row per paper, carrying that paper's single most promising sheet, ordered
so the most defensible candidates come first:

  1. header evidence -- `itv` beats `tv` beats nothing. A sheet whose own
     headers name a subject id, the covariate and the value is a better bet
     than one taken on numeric shape alone, and 48% of accepts are shape alone.
  2. subject count, then timepoints.

**The order is a convenience and nothing more.** It does not filter, it does
not score, and a paper at the bottom is not rejected -- gating on header
evidence was measured and costs 3 of 15 true positives without removing the
known false positive. The ordering exists so that a reader who stops halfway
has spent their time on the better half, because with precision at 6 of 15
the order is the only part of the verification cost this tool controls.

The two empty columns are the point of the file: `verdict_human` and `notes`,
filled in as you verify. See CONTRIBUTING.md for where to send them.
"""
import argparse
import csv
import glob
import os
import re
import sys


# WINDOWS CONSOLES ARE NOT UTF-8, AND BIOLOGY TITLES ARE.
# A paper called "PPAR<alpha> activation overcomes ..." crashed this script
# with UnicodeEncodeError on a cp1252 console. Greek letters are everywhere in
# this literature, so any run that printed a title was one paper away from
# dying -- invisible to anyone developing with PYTHONIOENCODING set, which is
# exactly how it survived until a fresh user hit it.
#
# Console output degrades; FILES are still written as utf-8 and keep the
# character.
try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

def fold_of(row):
    m = re.search(r"fold=([\d.]+)", row.get("reason") or "")
    return float(m.group(1)) if m else 0.0


def build(paths):
    rows = []
    for pat in paths:
        for path in sorted(glob.glob(pat)) or [pat]:
            if not os.path.exists(path):
                print("skipped, not found: %s" % path, file=sys.stderr)
                continue
            with open(path, newline="", encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    if (r.get("verdict") or "").strip().upper() == "CANDIDATE":
                        r["_src"] = os.path.basename(path)
                        rows.append(r)
    by = {}
    for r in rows:
        by.setdefault(r["id"], []).append(r)

    out = []
    for pid, rs in by.items():
        best = max(rs, key=lambda r: (len(r.get("header_evidence") or ""),
                                      int(r.get("n_animals") or 0),
                                      int(r.get("n_points") or 0)))
        out.append({
            "pmcid": pid,
            "doi": best.get("doi", ""),
            "journal": (best.get("journal") or "")[:40],
            "sheets": len(rs),
            "file": best.get("file", ""),
            "sheet": best.get("sheet", ""),
            "hdr": best.get("header_evidence") or "",
            "signature": best.get("signature") or "",
            "n": int(best.get("n_animals") or 0),
            "pts": int(best.get("n_points") or 0),
            # Subjects on the sheet that `min_points` dropped, and the floors
            # that dropped them. A verdict is not readable without the rule
            # that produced it, and the person filling in `verdict_human` is
            # exactly who needs to know that the sheet held more animals than
            # the count beside it.
            "below_floor": int(best.get("n_below_floor") or 0),
            "profile": best.get("profile", ""),
            "min_subjects": best.get("min_subjects", ""),
            "min_points": best.get("min_points", ""),
            "fold": fold_of(best),
            "title": (best.get("title") or "")[:70],
            "source_run": best.get("_src", ""),
            "verdict_human": "",
            "notes": "",
        })
    out.sort(key=lambda w: (bool(w["signature"]), -len(w["hdr"]),
                            -w["n"], -w["pts"]))
    return out


def _human_verdicts(path):
    """-> how many rows of an existing worklist carry a filled `verdict_human`.

    0 for a file that does not exist, is unreadable, or has no such column: the
    caller must not refuse on a file it could not read, only on one it could
    read and found verdicts in.
    """
    if not os.path.exists(path):
        return 0
    try:
        with open(path, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            if not rd.fieldnames or "verdict_human" not in rd.fieldnames:
                return 0
            return sum(1 for r in rd if (r.get("verdict_human") or "").strip())
    except OSError:
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("candidates", nargs="+",
                    help="one or more *_candidates.csv written by mine.py")
    ap.add_argument("-o", "--out", default=None,
                    help="default: <first input's directory>/worklist.csv")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a worklist that already carries human "
                         "verdicts. Without it, such a file is never touched.")
    a = ap.parse_args(argv)

    work = build(a.candidates)
    if not work:
        print("no CANDIDATE rows found. Did mine.py accept anything?")
        return 1
    out = a.out or os.path.join(os.path.dirname(a.candidates[0]) or ".",
                                "worklist.csv")

    # NEVER OVERWRITE SOMEONE'S VERDICTS.
    # The default output path is derived from the INPUT's directory, so re-running
    # the same command lands on the same file -- and that file is where a human
    # has been typing `verdict_human` for hours. Those verdicts are the one
    # measurement this toolchain cannot make about itself (CONTRIBUTING.md), they
    # exist nowhere else, and they were silently destroyed by a second run.
    # Found by doing it: a verification pass overwrote the four verdicts shipped
    # in `example/worklist.csv`, and only `git` got them back. A user's copy is
    # not in git.
    filled = _human_verdicts(out)
    if filled and not a.force:
        print("REFUSING to overwrite %s" % out)
        print("  it already carries %d human verdict(s) -- the scarcest thing "
              "in this workflow." % filled)
        print("  Write elsewhere with -o, or pass --force if you mean it.")
        return 1

    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(work[0]))
        w.writeheader()
        w.writerows(work)

    # "every row is shape-only" and "this file predates the hdr column" look
    # identical from here, and only one of them is a statement about the data.
    has_col = any(w_["hdr"] for w_ in work)
    shape = sum(1 for w_ in work if not w_["hdr"])
    print("  %d papers from %d candidate sheet(s) -> %s"
          % (len(work), sum(w_["sheets"] for w_ in work), out))
    print("  ordered best-first by header evidence, then subjects, then points")
    if has_col:
        print("  %d of %d rest on numeric SHAPE ALONE (hdr empty) -- verify "
              "those last, and expect more of them to be false"
              % (shape, len(work)))
    else:
        print("  NO header-evidence column in this input -- it predates that "
              "field, so the ordering below is by subjects and points only. "
              "This is NOT a finding that every sheet is shape-only.")
    print()
    print("  %-13s %-5s %-4s %-4s %-8s %s"
          % ("pmcid", "hdr", "n", "pts", "fold", "title"))
    for w_ in work[:12]:
        print("  %-13s %-5s %-4d %-4d %-8.1f %s"
              % (w_["pmcid"], w_["hdr"] or "---", w_["n"], w_["pts"],
                 w_["fold"], w_["title"][:44]))
    if len(work) > 12:
        print("  ... and %d more in the file" % (len(work) - 12))
    print()
    print("  STATE: %d candidate, 0 verified. Only a TRUE written by a person "
          "is `verified`;" % len(work))
    print("  an agent's TRUE is `screened` (skills/unpool/SKILL.md, the output contract).")
    print("  NEXT: open each paper's sheet and fill in `verdict_human` and")
    print("  `notes`. Nothing here is data until you have. Precision is "
          "8 of 20 at the shipped floors (docs/VALIDATION.md, V10/V17).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
