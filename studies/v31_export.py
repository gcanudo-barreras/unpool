"""V31: `unpool export` measured (docs/VALIDATION.md, registered before the code).

    python studies/v31_export.py --builders "<builders folder>"

X-P4 on the 50 V25 rows (runs/v27_review.csv); X-P1..P3 against the builders'
per-animal CSVs, which live outside this repository with the publisher files.
Writes runs/v31_builders.csv: one row per builder animal, no values.
"""
import argparse
import collections
import csv
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from unpool import export as xp          # noqa: E402
from unpool import extract as ex         # noqa: E402
from unpool import sheet as sheet_mod    # noqa: E402


def r6(v):
    return float("%.6g" % v)


def nonzero(pairs):
    return [(t, r6(v)) for t, v in pairs if v == v and v != 0]


# ---------------------------------------------------------------- X-P4
def p4():
    with open(os.path.join(ROOT, "runs", "v27_review.csv"), newline="", encoding="utf-8") as fh:
        todo = list(csv.DictReader(fh))
    verified, bad, refused, done = ex.verified_sheets(), [], [], 0
    for r in todo:
        rows, why = xp.rows_for(r, verified, fetch=False, meta=lambda p: {})
        if why:
            refused.append((r["pmcid"], r["sheet"], why))
            continue
        done += 1
        want, arms = xp.per_block(r["subjects"]), xp.arm_map(r["arms"])
        per = collections.defaultdict(set)
        for x in rows:
            per[int(x["block"][1:])].add(x["animal"])
        for b, n in want.items():
            exp = n if arms.get(b) else 0          # kept block: all; DROP/MIXED/unnamed: none
            if len(per.get(b, ())) != exp:
                bad.append((r["pmcid"], r["sheet"], "b%d: %d animals, expected %d"
                            % (b, len(per.get(b, ())), exp)))
    print("X-P4  exported %d of %d sheets; %d discrepancies" % (done, len(todo), len(bad)))
    for x in bad:
        print("   BAD", *x)
    for x in refused:
        print("   refused %s / %s: %s" % x)
    return not bad


# ---------------------------------------------------------------- X-P1..P3
def builder_map():
    out = {}
    with open(os.path.join(ROOT, "registry.csv"), newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            m = re.search(r"build_(\w+?)_arms_v1\.py", r["record"])
            if r["level"] == "built" and r["pmcid"] and m:
                out[m.group(1)] = r["pmcid"]
    return out


def read_builder(path):
    """-> {animal_id: (arm_id, [(day, value)])} from a builder's `;` CSV."""
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh, delimiter=";"):
            try:
                t, v = float(r["days"]), float(r["volumes"])
            except (TypeError, ValueError):
                continue
            arm = (r.get("panel") or r.get("study") or "", r.get("arm_label", ""))
            out.setdefault(r["animal_id"], (arm, []))[1].append((t, v))
    return {k: (a, sorted(p)) for k, (a, p) in out.items()}


def extracted(pmcid):
    """-> (subjects [(sheet, block, [(t, v)])], every numeric cell rounded)."""
    subs, cells = [], set()
    for member, s, rows in sheet_mod.sheets(pmcid, fetch=False):
        for row in rows:
            for c in row:
                try:
                    cells.add(r6(float(c)))
                except (TypeError, ValueError):
                    pass
        try:
            _, _, _, blocks = ex.extract(pmcid, s, member, fetch=False)
        except sheet_mod.SheetWall:
            continue
        for i, b in enumerate(blocks, 1):
            for _, pairs in b["subjects"]:
                subs.append(("%s|%s" % (os.path.basename(member), s), i, nonzero(pairs)))
    return subs, cells


def contains(big, small):
    n = len(small)
    return any(big[i:i + n] == small for i in range(len(big) - n + 1))


def compare(name, pmcid, path, w):
    animals = read_builder(path)
    subs, cells = extracted(pmcid)
    used, blocks = set(), collections.defaultdict(set)
    tally = collections.Counter()
    for aid, (arm, pairs) in animals.items():
        seq = nonzero(pairs)
        vals = [v for _, v in seq]
        row = {"builder": name, "pmcid": pmcid, "animal_id": aid, "arm": " / ".join(arm),
               "points": len(vals), "derived": "", "found": "", "sheet": "", "block": "",
               "days_ok": ""}
        if not vals or sum(v in cells for v in vals) < len(vals) / 2:
            row["derived"] = "yes"
            tally["derived"] += 1
            w.writerow(row)
            continue
        hit = None
        for k, (sh, b, sp) in enumerate(subs):
            if k in used:
                continue
            sv = [v for _, v in sp]
            if sv == vals:
                hit = (k, "exact")
                break
            if hit is None and len(vals) >= 3 and contains(sv, vals):
                hit = (k, "run")
        if hit is None:
            row["found"] = "no"
            tally["missed"] += 1
        else:
            k, how = hit
            used.add(k)
            sh, b, sp = subs[k]
            days = [t for t, _ in seq]
            got = [t for t, v in sp]
            if how == "run":
                start = next(i for i in range(len(sp)) if [v for _, v in sp[i:i + len(vals)]] == vals)
                got = got[start:start + len(vals)]
            ok = got == days
            row.update(found=how, sheet=sh, block="b%d" % b, days_ok="yes" if ok else "no")
            blocks[(sh, b)].add(arm)
            tally["found"] += 1
            tally["run"] += how == "run"
            tally["days_ok"] += ok
        w.writerow(row)
    tally["blocks"] = len(blocks)
    tally["pure"] = sum(len(a) == 1 for a in blocks.values())
    return tally


def pct(a, b):
    return "%d/%d (%.0f%%)" % (a, b, 100.0 * a / b) if b else "0/0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--builders", required=True, help="folder with the <name>-arms-v1.csv builder outputs")
    ap.add_argument("--example", default=os.path.join(ROOT, "example", "corpus",
                                                      "mdamb231_crispra_v1.csv"))
    a = ap.parse_args()
    ok4 = p4()
    out = os.path.join(ROOT, "runs", "v31_builders.csv")
    total = collections.Counter()
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["builder", "pmcid", "animal_id", "arm", "points",
                                           "derived", "found", "sheet", "block", "days_ok"])
        w.writeheader()
        print("\n%-14s %-12s %8s %-16s %-12s %-12s" % (
            "builder", "pmcid", "derived", "found (P1)", "pure (P2)", "days (P3)"))
        jobs = sorted(builder_map().items())
        jobs.append(("EXAMPLE", "PMC13534483"))
        for name, pmcid in jobs:
            path = a.example if name == "EXAMPLE" else next(iter(sorted(glob.glob(
                os.path.join(a.builders, "*%s-arms-v1.csv" % name)))), "")
            if not os.path.exists(path):
                print("%-14s %-12s builder CSV not found" % (name, pmcid))
                continue
            t = compare(name, pmcid, path, w)
            base = t["found"] + t["missed"]
            print("%-14s %-12s %8d %-16s %-12s %-12s%s" % (
                name, pmcid, t["derived"], pct(t["found"], base), pct(t["pure"], t["blocks"]),
                pct(t["days_ok"], t["found"]),
                "  (%d as a run)" % t["run"] if t["run"] else ""))
            if name != "EXAMPLE":
                total.update(t)
    base = total["found"] + total["missed"]
    print("\nPOOLED (10 builders, example apart): derived %d" % total["derived"])
    print("X-P1 animals found   %s  (>= 90%%)" % pct(total["found"], base))
    print("X-P2 blocks one arm  %s  (>= 90%%)" % pct(total["pure"], total["blocks"]))
    print("X-P3 days right      %s  (>= 90%%)" % pct(total["days_ok"], total["found"]))
    print("X-P4 bookkeeping     %s" % ("pass" if ok4 else "FAIL"))
    print("wrote %s" % out)


if __name__ == "__main__":
    main()
