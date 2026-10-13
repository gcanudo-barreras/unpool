"""V20: what the 40 MB cap actually COSTS, by opening the files it refuses.

    python studies/big_member_cost.py            # every oversized member
    python studies/big_member_cost.py --limit 3  # a dry run

Writes: studies/big_member_cost.csv and studies/big_member_cost.json

WHY THIS IS NOT V16 AGAIN
------------------------------------------------------------------------------
V16 measured how OFTEN the refusal fires -- 22 members across 19 of 2,390
papers, 8 of them the paper's only tabular file -- and said in the same breath
that it was not opening them: "parsing those is a real time and memory cost".
So the frequency is known and the COST IN DATA is not. Nobody has asked what is
inside them.

V1 asked it once, on four files from a single campaign, and one held ten sheets
the scanner accepts. That is the entire evidence base for a cap that silently
turns papers into "no per-animal table found".

WHAT IT DOES, AND WHAT IT DELIBERATELY DOES NOT
------------------------------------------------------------------------------
It reads each oversized member with no cap at all and runs the shipped
`judge_any` over every sheet. It does not change `scan.py`, it does not change
`MAX_MEMBER`, and it ships no new behaviour: the cap stays exactly where it is
until a registered decision rule says otherwise.

Time is recorded per member because time is the argument FOR the cap. A member
that parses in nine seconds and holds four accepted sheets is a different fact
from one that takes four minutes and holds none, and the two have been argued
about without either being measured.

A file that cannot be parsed at all -- MemoryError, a format the reader
refuses -- is recorded as a WALL with its exception text. It is not an empty
result and it is not evidence that the file holds nothing (rule 10).
"""
import argparse
import csv
import glob
import json
import os
import re
import sys
import time
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool import scan as S  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(os.path.dirname(_HERE), "si_cache")
TABULAR = re.compile(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", re.I)
CAP = 40 * 1024 * 1024        # the shipped cap: used to FIND them, not to obey

COLS = ["pmcid", "member", "mb", "only_tabular", "parsed", "seconds",
        "sheets", "accepted_sheets", "best_n", "best_pts", "best_sheet", "wall"]


def oversized(limit=None):
    """-> [(pmcid, member, size, only_tabular)] for every capped member."""
    out = []
    for z in sorted(glob.glob(os.path.join(CACHE, "*.zip"))):
        pmcid = os.path.splitext(os.path.basename(z))[0]
        try:
            infos = zipfile.ZipFile(z).infolist()
        except Exception:
            continue
        tabs = [i for i in infos if TABULAR.search(i.filename)]
        big = [i for i in tabs if i.file_size > CAP]
        if not big:
            continue
        only = len(big) == len(tabs)
        for i in big:
            out.append((pmcid, i.filename, i.file_size, only))
        if limit and len(out) >= limit:
            break
    return out[:limit] if limit else out


def open_one(pmcid, member, only):
    """Read one capped member with NO cap and judge every sheet it holds."""
    row = {"pmcid": pmcid, "member": os.path.basename(member), "mb": 0,
           "only_tabular": int(only), "parsed": 0, "sheets": 0,
           "accepted_sheets": 0, "best_n": 0, "best_pts": 0,
           "best_sheet": "", "wall": ""}
    path = os.path.join(CACHE, "%s.zip" % pmcid)
    t0 = time.time()
    try:
        zf = zipfile.ZipFile(path)
        info = next(i for i in zf.infolist() if i.filename == member)
        row["mb"] = round(info.file_size / 1048576.0, 1)
        blob = zf.read(info)
        for sheet, rows in S.sheets_from(member, blob):
            row["sheets"] += 1
            v = S.judge_any(rows)
            if v:
                row["accepted_sheets"] += 1
                n_an, n_pt = v[1], v[2]
                if n_an > row["best_n"]:
                    row.update({"best_n": n_an, "best_pts": n_pt,
                                "best_sheet": str(sheet)[:60]})
        row["parsed"] = 1
    except MemoryError:
        row["wall"] = ("MemoryError -- the file did not fit, which is a fact "
                       "about this machine, not about the file's contents")
    except Exception as exc:
        row["wall"] = "%s: %s" % (type(exc).__name__,
                                  str(exc).replace("\n", " ")[:160])
    row["seconds"] = round(time.time() - t0, 1)
    return row


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(argv)
    if S.preflight_banner():
        return 1

    targets = oversized(a.limit)
    print("  %d oversized tabular member(s) over %d MB, in %d paper(s)"
          % (len(targets), CAP // 1048576, len({t[0] for t in targets})))
    print("  %d of them are their paper's ONLY tabular member\n"
          % sum(1 for t in targets if t[3]))

    rows = []
    for i, (pmcid, member, size, only) in enumerate(targets, 1):
        print("  [%d/%d] %s %s (%.0f MB)%s"
              % (i, len(targets), pmcid, os.path.basename(member)[:40],
                 size / 1048576.0, "  ONLY TABULAR" if only else ""),
              file=sys.stderr)
        r = open_one(pmcid, member, only)
        rows.append(r)
        print("        %s  %ss  sheets=%d accepted=%d%s"
              % ("parsed" if r["parsed"] else "WALL", r["seconds"],
                 r["sheets"], r["accepted_sheets"],
                 "  <- " + r["wall"][:60] if r["wall"] else ""),
              file=sys.stderr)

    out = os.path.join(_HERE, "big_member_cost.csv")
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    parsed = [r for r in rows if r["parsed"]]
    walls = [r for r in rows if not r["parsed"]]
    gained = [r for r in parsed if r["accepted_sheets"]]
    only_gained = [r for r in gained if r["only_tabular"]]
    secs = sorted(r["seconds"] for r in parsed)
    summary = {
        "members": len(rows), "papers": len({r["pmcid"] for r in rows}),
        "parsed": len(parsed), "walls": len(walls),
        "members_with_accepted_sheets": len(gained),
        "papers_that_would_flip": len({r["pmcid"] for r in only_gained}),
        "accepted_sheets_total": sum(r["accepted_sheets"] for r in parsed),
        "seconds_median": secs[len(secs) // 2] if secs else None,
        "seconds_max": secs[-1] if secs else None,
        "unit": "tabular MEMBERS over the cap, and the papers holding them",
        "cap_mb": CAP // 1048576,
        "note": "The cap is NOT changed by this study. A member that could not "
                "be parsed is a wall, not an empty file.",
    }
    with open(os.path.join(_HERE, "big_member_cost.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)

    print("\n  parsed %d of %d; %d wall(s)" % (len(parsed), len(rows),
                                               len(walls)))
    print("  %d member(s) hold at least one sheet the scanner accepts, %d "
          "sheet(s) in total" % (len(gained), summary["accepted_sheets_total"]))
    print("  %d paper(s) would flip from NOT JUDGED to accepted"
          % summary["papers_that_would_flip"])
    print("  parse time: median %ss, max %ss"
          % (summary["seconds_median"], summary["seconds_max"]))
    print("  -> %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
