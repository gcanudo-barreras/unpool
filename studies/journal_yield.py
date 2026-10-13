"""How much per-subject preclinical data is machine-recoverable, and from where.

    python studies/journal_yield.py [--per-journal 100]

WHY THIS IS THE CHEAP MEASUREMENT AND THE PUBLISHABLE ONE
------------------------------------------------------------------------------
Two claims this toolchain can make, and they cost wildly different amounts:

  "journal X's supplements are N% machine-recoverable"   fully automatic
  "the scanner's precision is P"                         human, hours per batch

Only the second needs anyone to open a sheet. The first is a property of
publishing practice, it scales to thousands of papers overnight, and nobody has
published it.

WHAT IT MEASURES, PER JOURNAL
------------------------------------------------------------------------------
  pool      how many papers match the query at all
  bundle    how many have any supplementary bundle in the Europe PMC OA subset
  tabular   how many have at least one spreadsheet or flat text file
  accepted  how many hold at least one sheet the scanner accepts
  skipped   how many had a tabular member too large to open (NOT judged)

`accepted` is an upper bound on recoverable data, not a count of it: the
scanner's own precision applies on top, and it is measured elsewhere at
6 of 15.
Every artifact this writes says so.

Results are appended per journal as they complete, so a run that is interrupted
still leaves everything it finished.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool import scan as S  # noqa: E402

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
TAB = re.compile(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", re.I)
BASE = '("tumor volume" OR "tumour volume") AND HAS_FT:Y AND HAS_SUPPL:Y'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "journal_yield.csv")

# Chosen to span the POLICY spectrum rather than the prestige one: titles that
# require a Source Data file per figure, titles with a general data-availability
# statement and no file requirement, and titles with neither. Prestige is the
# confound this set exists to break -- Scientific Reports and Nature
# Communications share a publisher and nothing else that matters here.
JOURNALS = [
    "Nature Communications", "Communications Biology", "Nature",
    "Nature Cancer", "Nature Medicine", "Nature Metabolism",
    "Cell Death Dis", "Cell Death and Differentiation", "Oncogene",
    "Signal Transduction and Targeted Therapy", "British Journal of Cancer",
    "npj Precision Oncology", "npj Breast Cancer", "Scientific Reports",
    "eLife", "EMBO Molecular Medicine", "The EMBO Journal",
    "Cell Reports", "Cell Reports Medicine", "Molecular Cancer",
    "Journal for ImmunoTherapy of Cancer", "Cancer Cell International",
    "Journal of Experimental and Clinical Cancer Research",
    "Theranostics", "PLoS One", "PLoS Biology", "Cancers (Basel)",
    "Frontiers in Oncology", "International Journal of Molecular Sciences",
    "Cancer Research Communications",
]


def get(url):
    req = urllib.request.Request(url, headers=S.UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def sample(journal, n):
    """-> (pool, [pmcid, ...]) newest first."""
    q = 'JOURNAL:"%s" AND %s' % (journal, BASE)
    out, cursor, pool = [], "*", None
    while len(out) < n:
        url = ("%s?query=%s&format=json&pageSize=100&cursorMark=%s"
               "&sort=%s&resultType=core"
               % (SEARCH, urllib.parse.quote(q), urllib.parse.quote(cursor),
                  urllib.parse.quote("P_PDATE_D desc")))
        page = get(url)
        pool = page.get("hitCount") if pool is None else pool
        res = page.get("resultList", {}).get("result", [])
        if not res:
            break
        for r in res:
            if r.get("pmcid"):
                out.append(r["pmcid"])
                if len(out) >= n:
                    break
        nxt = page.get("nextCursorMark")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
    return pool or 0, out[:n]


def judge_paper(pmcid):
    """-> (has_bundle, has_tabular, accepted, skipped_big)."""
    import zipfile
    p = S.fetch(pmcid)
    if p.startswith("ERR"):
        return False, False, False, False
    try:
        zf = zipfile.ZipFile(p)
    except Exception:
        return False, False, False, False
    tabs = [i for i in zf.infolist() if TAB.search(i.filename)]
    if not tabs:
        return True, False, False, False
    skipped = any(i.file_size > 40 * 1024 * 1024 for i in tabs)
    for i in tabs:
        if i.file_size > 40 * 1024 * 1024:
            continue
        try:
            blob = zf.read(i)
        except Exception:
            continue
        for _, rows in S.sheets_from(i.filename, blob):
            if S.judge_any(rows):
                return True, True, True, skipped
    return True, True, False, skipped


IDS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "journal_yield_ids.csv")


def freeze_ids(journal, ids, path=IDS):
    """Write the sampled PMCIDs to disk, fsynced, BEFORE anything is fetched.

    THE DEFECT THIS CLOSES, found while writing docs/FIGURES.md:
    the first run of this study used `ids` and threw them away. The CSV kept
    aggregates only, so the 100 papers behind `Nature Communications 71%` were
    recorded nowhere -- and the sort is `P_PDATE_D desc`, newest first, over an
    index that grows, so re-running samples DIFFERENT papers. The published
    figure could not be re-derived on its own population by anyone, its author
    included. That is protocol rule 2 inverted: the file is supposed to
    remember what you will not.
    """
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["journal", "rank", "pmcid", "sampled_on"])
        today = datetime.date.today().isoformat()
        for i, pid in enumerate(ids, 1):
            w.writerow([journal, i, pid, today])
        fh.flush()
        os.fsync(fh.fileno())


def ids_from(path, journal):
    """-> the frozen PMCIDs for one journal, so a re-measurement at other
    floors runs on the SAME papers instead of on a fresh draw."""
    if not os.path.exists(path):
        raise SystemExit("no frozen id file at %s -- run without --from-ids "
                         "first" % path)
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["journal"] == journal]
    rows.sort(key=lambda r: int(r["rank"]))
    return [r["pmcid"] for r in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--per-journal", type=int, default=100)
    ap.add_argument("--journals", default=None,
                    help="comma-separated subset; default is all of JOURNALS")
    ap.add_argument("--from-ids", default=None, metavar="CSV",
                    help="re-scan the PMCIDs frozen by an earlier run instead "
                         "of drawing a new sample -- the only way to compare "
                         "two configurations on the same papers")
    ap.add_argument("--out", default=None)
    ap.add_argument("--per-paper", default=None, metavar="CSV",
                    help="also write one row per PAPER, so two profiles run "
                         "over the same frozen ids can be JOINED. Without it "
                         "only journal totals survive, and an overlap between "
                         "profiles cannot be measured -- only asserted.")
    a = ap.parse_args(argv)
    if S.preflight_banner():
        return 1

    journals = ([s.strip() for s in a.journals.split(",") if s.strip()]
                if a.journals else JOURNALS)
    unknown = [j for j in journals if j not in JOURNALS]
    if unknown:
        print("not in JOURNALS (measuring them anyway, named here so the "
              "scope of this run is visible): %s" % ", ".join(unknown))
    OUT_ = a.out or OUT

    done = set()
    if os.path.exists(OUT_):
        with open(OUT_, encoding="utf-8") as fh:
            done = {r["journal"] for r in csv.DictReader(fh)}
        print("resuming: %d journal(s) already done" % len(done))

    new = not os.path.exists(OUT_)
    fh = open(OUT_, "a", newline="", encoding="utf-8")
    w = csv.writer(fh)
    if new:
        w.writerow(["journal", "pool", "sampled", "bundle", "tabular",
                    "accepted", "skipped_big", "pct_tabular", "pct_accepted",
                    "unit", "profile",
                    # THE FLOORS TRAVEL WITH THE FIGURE OR THE FIGURE IS
                    # UNREADABLE (rule 8). The first run of this study recorded
                    # `profile` and not these, so its 76/71/49/10% could not say
                    # it was taken at min_subjects=5 -- and V9 lowered that to 4
                    # the next day.
                    "min_subjects", "min_points", "sampled_on", "ids_file"])
        fh.flush()

    pp = ppfh = None
    if a.per_paper:
        fresh = not os.path.exists(a.per_paper)
        ppfh = open(a.per_paper, "a", newline="", encoding="utf-8")
        pp = csv.writer(ppfh)
        if fresh:
            pp.writerow(["journal", "pmcid", "profile", "min_subjects",
                         "min_points", "accepted", "tabular", "skipped_big"])
            ppfh.flush()

    for j in journals:
        if j in done:
            continue
        try:
            if a.from_ids:
                ids = ids_from(a.from_ids, j)
                pool = "from_ids"
                if not ids:
                    print("%-46s no frozen ids" % j[:46])
                    continue
            else:
                pool, ids = sample(j, a.per_journal)
                freeze_ids(j, ids)      # rule 2: on disk before the first fetch
        except Exception as e:
            print("%-46s SEARCH FAILED %s" % (j[:46], type(e).__name__))
            continue
        if not ids:
            print("%-46s pool=%-7s no PMCIDs" % (j[:46], pool))
            continue
        b = t = acc = sk = 0
        for pid in ids:
            hb, ht, ha, hs = judge_paper(pid)
            b += hb
            t += ht
            acc += ha
            sk += hs
            if pp is not None:
                pp.writerow([j, pid, S.PROFILE["name"], S.MIN_ANIMALS,
                             S.MIN_POINTS, int(bool(ha)), int(bool(ht)),
                             int(bool(hs))])
                ppfh.flush()
        n = len(ids)
        w.writerow([j, pool, n, b, t, acc, sk,
                    round(100.0 * t / n, 1), round(100.0 * acc / n, 1),
                    "scanner_acceptances_NOT_verified_cells",
                    S.PROFILE["name"], S.MIN_ANIMALS, S.MIN_POINTS,
                    datetime.date.today().isoformat(),
                    os.path.basename(a.from_ids or IDS)])
        fh.flush()
        print("%-46s pool=%-7s n=%-4d tabular=%3d (%4.1f%%)  accepted=%3d (%4.1f%%)"
              % (j[:46], pool, n, t, 100.0 * t / n, acc, 100.0 * acc / n))
    fh.close()
    print("\nwrote %s" % OUT_)
    print("UNIT: scanner acceptances, NOT verified cells. Precision applies on "
          "top and is measured separately at 6 of 15.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
