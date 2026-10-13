"""A campaign's extractions as ONE per-animal CSV: every animal, its study and arm.

    unpool export runs/mc38_extractions.csv -o mc38_animals.csv

The input is the agent's extraction CSV (skills/unpool/SKILL.md): one row per
sheet with `pmcid`, `sheet`, `subjects` per block (`b1:8;b2:5`) and `arms`
(`b1=Vehicle;b2=Drug;b3-b4=DROP: body weight`), and what a modeller needs
to pool arms across papers: `model` (`MC38 subcutaneous`), `host`
(`C57BL/6`), `role` (`control` / `treated`) and `readout` (`volume (mm3)`),
each one value for the sheet or per block (`b1=control;b2-b3=treated`).
Each sheet is re-read with `extract`; each block gets its arm and the rest;
`DROP`, `MIXED` and `UNRESOLVED` blocks are left out.

WHAT IT DOES NOT DO
------------------------------------------------------------------------------
It does not READ anything new. Arms come from the agent's column, the cut
from `extract`; this is bookkeeping, and it says what it left out and why.

It does not RELABEL a sheet that is now cut differently. The arms name
blocks by number: if `extract` no longer returns the per-block counts the
agent wrote, `b2` may be another group, so the sheet is refused (V31).

It does not promote. `state` is `verified` only when the sheet is in
registry.csv AND a person checked this extraction (`subjects_ok`,
`times_ok`, `arms_ok` all yes, as `desk check` writes them); else `screened`.

Publisher bytes stay out of this repository: write the CSV outside it.
"""
import argparse
import csv
import json
import os
import re
import sys

from unpool import extract as ex
from unpool import paper
from unpool import sheet as sheet_mod
from unpool.desk import _block_ids

FIELDS = ["doi", "pmcid", "journal", "year", "licence", "file", "sheet", "sha256",
          "block", "arm", "model", "host", "role", "readout", "time_axis",
          "zero_at_start", "described_by", "animal", "subject_label", "time", "value", "state",
          "verified_by"]


def verifier(r, record):
    """Who a verified sheet is credited to: the extraction row's `checked_by`,
    else the handle of the registry record (`contributed/<handle>/...`)."""
    if (r.get("checked_by") or "").strip():
        return r["checked_by"].strip()
    parts = (record or "").replace("\\", "/").split("/")
    return parts[1] if len(parts) > 2 and parts[0] == "contributed" else ""


def per_block(subjects):
    """`b1:8;b2:5` -> {1: 8, 2: 5}; {} for a bare total."""
    out = {}
    for part in (subjects or "").split(";"):
        m = re.match(r"\s*b(\d+)\s*:\s*(\d+)\s*$", part)
        if m:
            out[int(m.group(1))] = int(m.group(2))
    return out


def arm_map(arms):
    """`b1=Veh;b2-b3=DROP: bw;b4=MIXED: ...` -> {1: 'Veh', 2: None, ...}.
    None means left out (DROP or MIXED); a block absent from the map has no arm."""
    out = {}
    for part in (arms or "").split(";"):
        key, eq, name = part.partition("=")
        if not eq:
            continue
        name = name.strip()
        for b in _block_ids(key):
            out[b] = None if name.upper().startswith(LEFT_OUT) else name
    return out


LEFT_OUT = ("DROP", "MIXED", "UNRESOLVED")


DESCRIBE = ("model", "host", "role", "readout", "time_axis", "zero_at_start")
_PER_BLOCK = re.compile(r"\s*b\d+(?:\s*[-,]\s*b?\d+)*\s*=")


def block_map(text):
    """`volume (mm3)` for the whole sheet, or `b1-b4=volume (mm3);b5=bli`
    per block -> {block: value}, with key 0 for the sheet-wide value."""
    text = (text or "").strip()
    if not _PER_BLOCK.match(text):          # "D/T = dabrafenib" is one value
        return {0: text}
    out = {}
    for part in text.split(";"):
        key, _, name = part.partition("=")
        for b in _block_ids(key):
            out[b] = name.strip()
    return out


def _meta(pmcid):
    """paper.metadata, cached beside the supplement (one request per paper)."""
    path = os.path.join(paper.CACHE, "%s.meta.json" % pmcid)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        pass
    try:
        m = paper.metadata(pmcid)
    except paper.PaperWall:
        return {}
    os.makedirs(paper.CACHE, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(m, fh)
    return m


def rows_for(r, verified, fetch=True, meta=_meta):
    """-> (rows, None) or ([], reason) for one extraction row."""
    pmcid, sheet = r["pmcid"].strip(), r["sheet"]
    want, arms = per_block(r.get("subjects")), arm_map(r.get("arms"))
    desc = {f: block_map(r.get(f)) for f in DESCRIBE}
    if not want or not arms:
        return [], "no per-block subjects or no arms written"
    try:
        fname, digest, _, blocks = ex.extract(pmcid, sheet, fetch=fetch)
    except sheet_mod.SheetWall as w:
        return [], "WALL: %s" % w
    got = {i: len(b["subjects"]) for i, b in enumerate(blocks, 1)}
    if got != want:
        return [], ("extract now cuts it %s, the arms were written for %s"
                    % (_fmt(got), _fmt(want)))
    ok = all((r.get(k) or "").strip().lower() == "yes"
             for k in ("subjects_ok", "times_ok", "arms_ok"))
    key = (pmcid, sheet.strip().lower())
    state = "verified" if ok and key in verified else "screened"
    by = verifier(r, verified.get(key) if isinstance(verified, dict) else "") \
        if state == "verified" else ""
    m = meta(pmcid)
    out = []
    for i, b in enumerate(blocks, 1):
        arm = arms.get(i)
        if not arm:
            continue
        for k, (lab, pairs) in enumerate(b["subjects"], 1):
            for t, v in pairs:
                out.append({"doi": m.get("doi", ""), "pmcid": pmcid,
                            "journal": m.get("journal", ""), "year": m.get("year", ""),
                            "licence": m.get("licence", ""), "file": fname,
                            "sheet": sheet, "sha256": digest, "block": "b%d" % i,
                            "arm": arm, "animal": "%s:%s:b%d:s%d" % (pmcid, sheet, i, k),
                            "subject_label": (lab or "")[:60], "time": "%g" % t,
                            "value": repr(v), "state": state, "verified_by": by,
                            "described_by": r.get("metadata_by") or "agent",
                            **{f: d.get(i, d.get(0, "")) for f, d in desc.items()}})
    return out, None


def _fmt(d):
    return ";".join("b%d:%d" % kv for kv in sorted(d.items())) or "(nothing)"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("extractions", help="the agent's extraction CSV (pmcid, sheet, subjects, arms)")
    ap.add_argument("-o", "--out", required=True, help="the per-animal CSV (outside the repository)")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    with open(a.extractions, newline="", encoding="utf-8") as fh:
        todo = list(csv.DictReader(fh))
    verified = ex.verified_sheets()
    n_rows, papers, left, states = 0, set(), [], {}
    tmp = a.out + ".part"           # a half-written CSV must never look finished
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for n, r in enumerate(todo, 1):
            print("  [%d/%d] %s / %s%s" % (n, len(todo), r["pmcid"], r["sheet"],
                  "" if a.no_fetch else "  (downloads the supplement once)"),
                  file=sys.stderr, flush=True)
            rows, why = rows_for(r, verified, not a.no_fetch)
            if why:
                left.append((r["pmcid"], r["sheet"], why))
                continue
            out = {}
            for part in (r.get("arms") or "").split(";"):
                key, _, name = part.partition("=")
                tag = name.strip().split(":")[0].upper()
                if tag in LEFT_OUT:
                    out.setdefault(tag, set()).update(_block_ids(key))
            if out:
                left.append((r["pmcid"], r["sheet"], "; ".join(
                    "%s %s" % (t, ",".join("b%d" % b for b in sorted(ids)))
                    for t, ids in sorted(out.items()))))
            w.writerows(rows)
            n_rows += len(rows)
            if rows:
                papers.add(r["pmcid"])
                st = rows[0]["state"]
                states[st] = states.get(st, 0) + len({x["animal"] for x in rows})
    os.replace(tmp, a.out)
    print("  %d animals, %d values, %d papers -> %s"
          % (sum(states.values()), n_rows, len(papers), a.out))
    print("  state: %s" % (", ".join("%d %s" % (n, s) for s, n in sorted(states.items()))
                           or "nothing exported"))
    if left:
        print("  left out, by sheet (%d):" % len(left))
        for p, s, why in left:
            print("    %s / %s: %s" % (p, s, why))
    if states.get("screened"):
        print("  `screened` animals carry an agent's reading: check them (`unpool desk check`)\n"
              "  before calling them data.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
