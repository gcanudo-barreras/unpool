"""Build `registry.csv`: every sheet or file in this repository that a PERSON or
a BUILDER has verified to hold per-subject longitudinal tumour data.

It is the only place the word `verified` is allowed to live. A scanner
acceptance is a `candidate`; an agent's verdict is `screened`; neither ever
enters this file, whatever it says (skills/unpool/SKILL.md, "The output contract").

Sources, each read from its committed artifact and never from memory:

  built      example/build_*.py      a builder re-derives the bytes and
                                     asserts the subject count (_VERIFIED_N)
  built      fixtures/ground_truth.csv  POS rows, verified by the origin
                                     project's builders (named in `record`);
                                     file-level, and only files the manifest
                                     can re-fetch -- transcriptions excluded
  verified   runs/v*_verdicts.csv    hand-read precision samples
  verified   example/worklist.csv    hand-read campaign verdicts
  verified   contributed/*/*.csv     contributed verdicts (CONTRIBUTING.md)

Only TRUE verdicts enter. Metadata (DOI, journal, licence) comes from one
Europe PMC query per row; a failed query is written as a wall, not dropped.

Usage:  python studies/build_registry.py        -> registry.csv
"""
import csv
import glob
import json
import os
import re
import sys
import urllib.parse

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
from unpool import paper  # noqa: E402

OUT = os.path.join(_ROOT, "registry.csv")
FIELDS = ["level", "pmcid", "doi", "journal", "year", "licence", "file",
          "sheet", "verified_n", "scanner_n", "scanner_pts", "record", "note"]
# verified_n: subjects a BUILDER asserted. scanner_n / scanner_pts: what the
# scanner counted on that sheet -- a count of rows or columns, NOT of animals
# (one V10 sheet reads 322 for 18 mice). Rule 8: the unit travels with the count.


def rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def rel(path):
    return os.path.relpath(path, _ROOT).replace(os.sep, "/")


def collect():
    out = []
    for path in sorted(glob.glob(os.path.join(_ROOT, "example", "build_*.py"))):
        src = open(path, encoding="utf-8").read()
        pmc = re.search(r'si_cache", "(PMC\d+)\.zip"', src)
        sheet = re.search(r'^SHEET = "(.*)"', src, re.M)
        n = re.search(r"^_VERIFIED_N = (\d+)", src, re.M)
        if pmc and sheet and n:
            out.append({"level": "built", "pmcid": pmc.group(1),
                        "sheet": sheet.group(1), "verified_n": n.group(1),
                        "record": rel(path)})
    manifest = {r["file"]: r for r in rows(os.path.join(_ROOT, "fixtures", "manifest.csv"))}
    gt = os.path.join(_ROOT, "fixtures", "ground_truth.csv")
    for r in rows(gt):
        if r["verdict"] == "POS" and r["file"] in manifest:
            m = re.search(r"PMC\d+", r["file"])
            out.append({"level": "built", "pmcid": m.group(0) if m else "",
                        "doi": manifest[r["file"]]["doi"], "file": r["file"],
                        "record": "%s (%s)" % (rel(gt), list(r.values())[2].strip())})
    human = sorted(glob.glob(os.path.join(_ROOT, "runs", "v*_verdicts.csv")))
    human += [os.path.join(_ROOT, "example", "worklist.csv")]
    human += sorted(glob.glob(os.path.join(_ROOT, "contributed", "*", "*.csv")))
    for path in human:
        for r in rows(path):
            if (r.get("verdict_human") or "").strip().upper() == "TRUE":
                out.append({"level": "verified", "pmcid": r.get("pmcid", ""),
                            "doi": r.get("doi", ""),
                            "file": r.get("file") or r.get("member", ""),
                            "sheet": r.get("sheet", ""), "scanner_n": r.get("n", ""),
                            "scanner_pts": r.get("pts", ""), "record": rel(path),
                            "note": (r.get("notes") or "")[:200]})
    # a verdicts file names the sheet but not the member; its draw's population does
    members = {}
    for pop in glob.glob(os.path.join(_ROOT, "runs", "v*_population.csv")):
        for r in rows(pop):
            members[(r["pmcid"], r["sheet"].strip())] = r["member"]
    for r in out:
        if not r.get("file"):
            r["file"] = members.get((r["pmcid"], r.get("sheet", "").strip()), "")
    return out


def meta(row):
    q = "PMCID:%s" % row["pmcid"] if row.get("pmcid") else "DOI:%s" % row["doi"]
    url = "%s?query=%s&resultType=core&format=json&pageSize=1" % (
        paper.SEARCH, urllib.parse.quote(q))
    try:
        res = json.loads(paper._get(url).decode("utf-8"))["resultList"]["result"]
    except Exception as exc:
        return {"licence": "WALL: metadata query failed (%s)" % type(exc).__name__}
    if not res:
        return {"licence": "not indexed by Europe PMC"}
    r = res[0]
    return {"pmcid": row.get("pmcid") or r.get("pmcid", ""),
            "doi": row.get("doi") or r.get("doi", ""),
            "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title", ""),
            "year": (r.get("journalInfo") or {}).get("yearOfPublication", ""),
            "licence": r.get("license", "")}


def main():
    reg = collect()
    for row in reg:
        row.update({k: v for k, v in meta(row).items() if v})
    reg.sort(key=lambda r: (r["level"], r.get("pmcid") or r.get("doi", ""), r.get("sheet", "")))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(reg)
    by = {}
    for r in reg:
        by[r["level"]] = by.get(r["level"], 0) + 1
    print("registry.csv: %d entries  %s" % (len(reg), by))
    return 0


if __name__ == "__main__":
    sys.exit(main())
