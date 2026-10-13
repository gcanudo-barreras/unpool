"""The acceptance gate for `scan.py`: recall against the cached publisher
fixtures, whose ground truth (POS/POS*/NEG) is read from the builder that
established it (`_VERIFIED_N` or docstring), never from this script's own
inspection of the raw file -- see `fixtures/ground_truth.csv` for the citation
on every row.

**THIS GATE MEASURES RECALL AND HALF OF PRECISION, AND THE HALF IT MISSES HAS
SINCE FAILED.** It scores false negatives (POS files the scanner missed) and
false positives *within the known fixtures* -- but the scanner's real precision
cost is on papers it ACCEPTS out in the wild, which no local file can exhibit.
Measured on an unbiased sample of 15 accepted papers, seed registered before
any sheet was opened: **9 of 15 were false** -- seven of them large numeric
matrices from another discipline (`docs/VALIDATION.md`, V2).

The standing rule is that precision and recall are reported together or
neither is; this file reports recall, and **the precision figure that belongs
beside it is 6 of 15.** Do not quote this gate's PASS as evidence that an
acceptance is real.

POS*  = structurally identical to an accepted positive but rejected by its
        builder only on provenance/prose grounds the scanner cannot see
        (e.g. CT-26 figure4b/figureS1 are phosphorescence, not volume).
        Counts toward recall's numerator like any POS: the scanner's job is
        structural triage, not the paper's prose.
NEG   = must stay a miss. rsob_240210_group_means.txt is the negative
        control and is graded on its own line: any hit there is reported as
        a HARD FAILURE regardless of the recall percentage.

Usage: python test_recall.py
Exits 0 if recall >= 0.80 AND the negative control is a miss, else 1.
"""
import csv
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _ROOT)
from unpool import scan as S  # noqa: E402

RAW = os.path.join(_ROOT, "fixtures", "cache")
GT = os.path.join(_ROOT, "fixtures", "ground_truth.csv")
RECALL_TARGET = 0.80
# THE NEGATIVE CONTROL IS A SHEET, NOT A FILE.
#
# The previous one was a file we had transcribed ourselves, so AGG was only
# ever tested against headers we wrote (protocol rule 11). Its publisher did not serve any
# data file at all, so it could not simply be swapped (protocol rule 10).
#
# This one is publisher bytes: `Weeks of treatment` x `Average tumor volume /
# SEM / Number of mice` per arm, longitudinal group means written by its own
# authors. AGG must reject it.
#
# It is addressed BY SHEET because the same workbook has 103 sheets and the
# scanner accepts 6 of them. A file-level control here would be asking a
# different question and answering it by accident -- which is exactly how the
# grading script in protocol rule 10 missed `Figure 1D` by stopping at the first hit.
# V11: THE PREVIOUS CONTROL NEVER REACHED `AGG`.
# `PMC13367972` `Fig. 7C_Tumor_growth` was acquired to test the mean/SEM rule,
# and its markers sit in a COLUMN-HEADER row -- so `AGG`, which only ever reads
# ROW LABELS, fired on nothing in the file. Neutering `AGG` entirely left the
# verdict unchanged at `None`: it is rejected because its axis is the text
# `Week 1`, the same layout as V1's false negative. `negative control: intact`
# was therefore a vacuous pass for the one rule everything else rests on.
#
# This one is rejected BY `AGG`, verified the only way that claim can be: with
# `AGG` neutered, the scanner ACCEPTS it.
NEG_CONTROL = "PMC12611756_41586_2025_9655_MOESM3_ESM.xlsx"
NEG_CONTROL_SHEET = "2a"


def load_ground_truth():
    rows = []
    with open(GT, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.append(r)
    return rows


def scan_file(fname):
    """-> (hit: bool, best) using scan.py's own sheets_from/judge_any,
    directly on the local corpus file -- no network, no PMC fetch."""
    path = os.path.join(RAW, fname)
    with open(path, "rb") as fh:
        blob = fh.read()
    best = None
    for sheet, rows in S.sheets_from(fname, blob):
        v = S.judge_any(rows)
        if v and (best is None or v[1] > best[2]):
            best = (sheet, v[0], v[1], v[2], v[-1])
    return best is not None, best


def check_negative_control():
    """-> (present, fired). `fired` means AGG failed to reject a group-means sheet."""
    path = os.path.join(RAW, NEG_CONTROL)
    if not os.path.exists(path):
        return False, False
    with open(path, "rb") as fh:
        blob = fh.read()
    for sheet, rows in S.sheets_from(NEG_CONTROL, blob):
        if sheet == NEG_CONTROL_SHEET:
            return True, bool(S.judge_any(rows))
    return False, False


def main():
    gt = load_ground_truth()
    pos_total = pos_hit = 0
    neg_fail = []
    detail = []

    absent = [r["file"] for r in gt
              if not os.path.exists(os.path.join(RAW, r["file"]))]
    gt = [r for r in gt if r["file"] not in absent]
    control_present, control_fired_sheet = check_negative_control()

    for row in gt:
        fname, verdict = row["file"], row["verdict"]
        is_pos = verdict in ("POS", "POS*")
        hit, best = scan_file(fname)

        if is_pos:
            pos_total += 1
            if hit:
                pos_hit += 1
        else:
            if hit:
                neg_fail.append((fname, best))

        tag = "HIT " if hit else "MISS"
        want = "expect POS" if is_pos else "expect NEG"
        detail.append((fname, verdict, tag, want, best, row["note"]))

    if S.preflight_banner():
        print("REFUSING TO SCORE: see the banner above.")
        return 1
    if not control_present:
        print()
        print("THE NEGATIVE CONTROL WAS NOT SCORED: %s is not in the cache."
              % NEG_CONTROL)
        print("Run `python fixtures/fetch.py`. Without it, AGG -- the rule this")
        print("whole scanner rests on -- is not exercised by anything here, and")
        print("THE GATE CANNOT PASS.")
    if absent:
        print()
        print("NOT SCORED -- %d of %d ground-truth files are not in the cache."
              % (len(absent), len(absent) + len(gt)))
        print("Run `python fixtures/fetch.py` first. Every figure below is over")
        print("the %d files that ARE present, and over nothing else:" % len(gt))
        for f in absent:
            print("    %s" % f)
        print()
    print("profile: %s" % S.PROFILE["name"])
    print(f"{'file':45s} {'truth':5s} {'result':5s}")
    print("-" * 100)
    for fname, verdict, tag, want, best, note in detail:
        ok = (tag == "HIT " and verdict in ("POS", "POS*")) or \
             (tag == "MISS" and verdict == "NEG")
        mark = "OK " if ok else "!! "
        extra = (f"  ({best[1]} n={best[2]} pts={best[3]} sheet={best[0]!r}"
                 f" hdr={best[-1] or 'NONE-shape only'})") if best else ""
        print(f"{mark}{fname:43s} {verdict:5s} {tag:5s}{extra}")
        if not ok:
            print(f"       -> {note}")

    recall = pos_hit / pos_total if pos_total else 0.0
    print("-" * 100)
    print(f"RECALL: {pos_hit}/{pos_total} = {recall:.1%}  "
          f"(target >= {RECALL_TARGET:.0%})")
    if neg_fail:
        print(f"NEGATIVE-CONTROL / NEG FAILURES ({len(neg_fail)}):")
        for fname, best in neg_fail:
            flag = " <-- NEGATIVE CONTROL" if fname == NEG_CONTROL else ""
            print(f"    {fname}  ->  {best}{flag}")
    else:
        print("All NEG files (including the negative control) stayed misses.")

    named_misses = [f for f, v, t, w, b, n in detail
                    if v in ("POS", "POS*") and t == "MISS"]
    if named_misses:
        print(f"REMAINING FALSE NEGATIVES ({len(named_misses)}), named per the name-it-do-not-hide-it rule:")
        for f in named_misses:
            note = next(n for ff, vv, tt, ww, bb, n in detail if ff == f)
            print(f"    {f}: {note}")

    # Hard gate, exactly as registered: recall >= 80% and the negative
    # control stays a miss. Any OTHER false positive is reported and named
    # above, not silently passed -- but it is a precision cost to weigh, not
    # a reason to keep withholding a scanner that clears the actual bar.
    # A NEGATIVE CONTROL THAT WAS NOT RUN IS NOT AN INTACT NEGATIVE CONTROL.
    # The old expression asked only whether the control appeared in `neg_fail`.
    # When the file is absent it cannot appear there, so the gate reported
    # "intact: True" for a check it had never performed -- a vacuous pass, and
    # the one place in this tool where a vacuous pass is least affordable.
    control_fired = control_fired_sheet
    control_ok = control_present and not control_fired
    control_state = ("intact (sheet %r rejected)" % NEG_CONTROL_SHEET if control_ok
                     else "FIRED" if control_present
                     else "NOT RUN -- the file is not in the cache")
    passed = recall >= RECALL_TARGET and control_ok
    print()
    print("PASS" if passed else "FAIL",
          "-- recall>=80%:", recall >= RECALL_TARGET,
          " negative control:", control_state,
          " other NEG false-positives (reported, non-blocking):", len(neg_fail) - (1 if control_fired else 0))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
