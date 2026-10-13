"""The precision population, and the draw from it -- reproducible by a stranger.

    python studies/precision_population.py --tag v18 --seed 20260918 --n 20
    #  -> runs/v18_population.csv   one row per ACCEPTED PAPER, its best sheet
    #  -> runs/v18_sample.json      the draw, the seed, the exclusions, the
    #                               profile and the floors it ran under

WHY THIS IS A FILE AND NOT AN AFTERNOON'S SCRIPT
------------------------------------------------------------------------------
V10 built its population by hand and the code did not survive the day. The
artifacts did (`runs/v10_population.csv`, `runs/v10_sample.json`), which is more
than most projects keep -- but V15 is the lesson here: a headline figure nobody
except its author can reproduce is not a figure, and V15 found the recall gate
in exactly that state. A precision figure is the number this repository is most
often asked for. The thing that produces its sample belongs in the repository.

WHAT IT SWEEPS, AND WHY IT IS NOT A RANDOM SAMPLE OF ANYTHING
------------------------------------------------------------------------------
`si_cache/` -- every paper already fetched, which is the accumulation of past
campaigns and of `journal_yield.py`'s 100-paper sweeps across 27 journals. It
OVER-REPRESENTS those journals and the direction of the bias is unknown: a
Source Data policy may mean cleaner per-animal tables, or more of the discipline
matrices V2 found. This is written into the sample file as well as here, because
it is the kind of caveat that falls off a number in transit.

The population is the one the TOOL reads: tabular members only, nothing over
40 MB, judged by the shipped `judge_any`. Size skips are COUNTED, never silent
(rule 11) -- a paper whose only tabular member was skipped unread is NOT JUDGED
and is not in the denominator.

The best sheet per paper is the one `worklist.py` would put first -- header
evidence, then subjects, then points -- because that is the sheet a user opens.

WHAT IT EXCLUDES, AND WHY THE EXCLUSION IS NOT A DETAIL
------------------------------------------------------------------------------
Every paper that already carries a verdict anywhere in this repository. Drawing
a paper whose answer is known is not an out-of-sample measurement, and the
exclusion list is assembled from the artifacts themselves rather than typed from
memory -- V10's own exclusion was described in prose and could not be re-derived
today. Each source is reported by name and count, so a reader can see what was
held out and object to it.
"""
import argparse
import csv
import datetime
import glob
import json
import os
import random
import re
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool import scan  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
CACHE = os.path.join(_ROOT, "si_cache")
RUNS = os.path.join(_ROOT, "runs")

# The same population the tool itself reads -- `mine.py` and `scan.py` both use
# these two constants, and a census over a wider set would report an accept rate
# that is not the tool's accept rate.
TABULAR = re.compile(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", re.I)
MAX_MEMBER = 40 * 1024 * 1024

# V8's three papers carry verdicts that live in prose (docs/VALIDATION.md, V8:
# "all 11 were read ... 11 of 11 are genuine per-animal longitudinal series")
# and in no CSV. Named here rather than left out of the exclusion, because a
# verdict is a verdict wherever it is written down.
V8_VERIFIED = ["PMC11663793", "PMC12527938", "PMC12545207"]


def known_verdicts():
    """-> ({pmcid: [source, ...]}, notes) for every paper already adjudicated."""
    got, notes = {}, []

    def add(pmcid, src):
        pmcid = (pmcid or "").strip()
        if pmcid.startswith("PMC"):
            got.setdefault(pmcid, []).append(src)

    for p in V8_VERIFIED:
        add(p, "V8 (docs/VALIDATION.md)")
    notes.append("V8 (docs/VALIDATION.md): %d" % len(V8_VERIFIED))

    for name in ("v2_sample.json", "v9_sample.json", "v12_sample.json",
                 "v14_sample.json"):
        path = os.path.join(RUNS, name)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
        ids = []
        for key in ("sample", "excluded_biased"):
            ids += [i for i in blob.get(key, []) if isinstance(i, str)]
        ids += [d.get("pmcid", "") for d in blob.get("drawn", [])
                if isinstance(d, dict)]
        for i in ids:
            add(i, name)
        notes.append("%s: %d" % (name, len(set(ids))))

    # Anything with a FILLED verdict column, wherever it lives. A contributed
    # batch is a verdict this project did not make and must still not re-draw.
    for path in ([os.path.join(RUNS, "v10_verdicts.csv"),
                  os.path.join(_ROOT, "example", "worklist.csv"),
                  os.path.join(RUNS, "worklist.csv")]
                 + sorted(glob.glob(os.path.join(_ROOT, "contributed",
                                                 "*", "*.csv")))):
        if not os.path.exists(path):
            continue
        rel = os.path.relpath(path, _ROOT).replace("\\", "/")
        n = 0
        with open(path, encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                if (r.get("verdict_human") or r.get("verdict") or "").strip():
                    add(r.get("pmcid") or r.get("id") or "", rel)
                    n += 1
        notes.append("%s: %d" % (rel, n))
    return got, notes


def best_sheet(accepts):
    """The sheet `worklist.py` would put first: hdr evidence, subjects, points."""
    return max(accepts, key=lambda a: (len(a["hdr"]), a["n"], a["pts"]))


def sweep(limit=None, progress=250):
    zips = sorted(glob.glob(os.path.join(CACHE, "*.zip")))[:limit or None]
    papers, stats = [], {"papers": 0, "bad_zips": 0, "sheets": 0,
                         "unreadable_members": 0, "size_skipped_members": 0,
                         "papers_only_size_skipped": 0, "accepted_sheets": 0}
    t0 = time.time()
    for i, z in enumerate(zips, 1):
        stats["papers"] += 1
        pmcid = os.path.splitext(os.path.basename(z))[0]
        try:
            zf = zipfile.ZipFile(z)
            infos = zf.infolist()
        except Exception:
            stats["bad_zips"] += 1
            continue
        accepts, read_any, skipped = [], False, 0
        for info in infos:
            if not TABULAR.search(info.filename):
                continue
            if info.file_size > MAX_MEMBER:
                stats["size_skipped_members"] += 1
                skipped += 1
                continue
            try:
                blob = zf.read(info)
            except Exception:
                stats["unreadable_members"] += 1
                continue
            read_any = True
            try:
                sheets = list(scan.sheets_from(info.filename, blob))
            except Exception:
                stats["unreadable_members"] += 1
                continue
            for sheet, rows in sheets:
                stats["sheets"] += 1
                try:
                    v = scan.judge_any(rows)
                except Exception:
                    continue
                if not v:
                    continue
                layout, n_an, n_pt, note, _grids, below, ev = v
                stats["accepted_sheets"] += 1
                accepts.append({
                    "pmcid": pmcid, "member": os.path.basename(info.filename),
                    "sheet": sheet, "layout": layout, "n": n_an, "pts": n_pt,
                    "note": note, "below_floor": below, "hdr": ev or "",
                    "signature": scan.discipline_signature(rows) or ""})
        if skipped and not read_any:
            # NOT JUDGED, and therefore not in the denominator (rule 11).
            stats["papers_only_size_skipped"] += 1
            continue
        if accepts:
            papers.append(best_sheet(accepts))
        if progress and i % progress == 0:
            print("  %d/%d papers, %d accepted, %.0fs"
                  % (i, len(zips), len(papers), time.time() - t0),
                  file=sys.stderr)
    return papers, stats


COLS = ["pmcid", "member", "sheet", "layout", "n", "pts", "note",
        "below_floor", "hdr", "signature"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tag", required=True, help="e.g. v18")
    ap.add_argument("--seed", type=int, required=True,
                    help="registered BEFORE the draw; it goes in the artifact")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--limit", type=int, default=None,
                    help="sweep only the first N cached papers (development)")
    a = ap.parse_args(argv)

    print("  profile %s   floors min_subjects=%d min_points=%d"
          % (os.environ.get("UNPOOL_PROFILE", "tumor_volume"),
             scan.MIN_ANIMALS, scan.MIN_POINTS))
    papers, stats = sweep(a.limit)
    excl, notes = known_verdicts()

    eligible = [p for p in papers if p["pmcid"] not in excl]
    if len(eligible) < a.n:
        raise SystemExit("only %d eligible papers, cannot draw %d"
                         % (len(eligible), a.n))

    os.makedirs(RUNS, exist_ok=True)
    pop = os.path.join(RUNS, "%s_population.csv" % a.tag)
    with open(pop, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows({k: p[k] for k in COLS} for p in eligible)

    rnd = random.Random(a.seed)
    drawn = rnd.sample(eligible, a.n)
    smp = os.path.join(RUNS, "%s_sample.json" % a.tag)
    with open(smp, "w", encoding="utf-8") as fh:
        json.dump({
            "seed": a.seed, "n": a.n,
            "swept": datetime.date.today().isoformat(),
            "profile": os.environ.get("UNPOOL_PROFILE", "tumor_volume"),
            "min_subjects": scan.MIN_ANIMALS, "min_points": scan.MIN_POINTS,
            "accepted_papers_total": len(papers),
            "excluded_known_verdict": len(papers) - len(eligible),
            "population": len(eligible),
            "exclusion_sources": notes,
            "excluded_pmcids": {k: sorted(set(v))
                                for k, v in sorted(excl.items())
                                if any(p["pmcid"] == k for p in papers)},
            "sweep_stats": stats,
            "population_caveat":
                "si_cache/ is the accumulation of past campaigns and of "
                "journal_yield.py's 100-paper sweeps across 27 journals. It "
                "over-represents those journals and is NOT a random sample of "
                "the literature. The direction of the bias is unknown.",
            "drawn": drawn,
        }, fh, indent=1, ensure_ascii=False)

    print("\n  swept %d papers, %d sheets, %d accepted sheets"
          % (stats["papers"], stats["sheets"], stats["accepted_sheets"]))
    print("  %d bad zip(s), %d unreadable member(s), %d member(s) over 40 MB "
          "skipped unread" % (stats["bad_zips"], stats["unreadable_members"],
                              stats["size_skipped_members"]))
    print("  %d paper(s) had ONLY size-skipped members: NOT JUDGED, and not in "
          "the denominator" % stats["papers_only_size_skipped"])
    print("  %d accepted paper(s), %d already carry a verdict -> %d eligible"
          % (len(papers), len(papers) - len(eligible), len(eligible)))
    for n in notes:
        print("      excluded from %s" % n)
    print("  %s" % pop)
    print("  drew %d with seed %d -> %s" % (a.n, a.seed, smp))
    print("\n  Nothing has been opened yet. That is the point: the draw is "
          "frozen\n  before the first sheet is read (protocol rule 2).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
