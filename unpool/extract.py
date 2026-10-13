"""Turn a sheet into a tidy per-subject CSV: one row per (subject, time, value).

    unpool extract PMC13534483 --sheet "Supplementary Fig. 8b."          # summary only
    unpool extract PMC13534483 --sheet "Supplementary Fig. 8b." -o out.csv

WHAT IT DOES NOT DO, AND WHY THAT IS THE DESIGN
------------------------------------------------------------------------------
It does not VERIFY. Every output row carries `state`, read from registry.csv:
`verified` only if a person or a builder verified that exact sheet, otherwise
`candidate` -- extracting a sheet does not make it data (skills/unpool/SKILL.md,
the output contract).

It does not guess ARMS. Each block of subjects gets the raw text the sheet
writes above and beside it (`block_label`, `subject_label`), and the `arm`
column is left EMPTY for a person, or an agent from the legend, to fill.

It does not trust subject LABELS as identifiers. `Mouse #1` restarts inside
every arm of the worked example: keyed on the label, five mice fuse into one
and 41 animals become 9, silently, in a plausible CSV. So `subject` is
positional -- `b<block>:s<index>` -- and the sheet's own label is kept beside it.

It does not interpret VALUES. A row of zeros at day 0 is written as zeros; the
worked example's builder decided those are not measurements, and that is a
decision for whoever builds from this, recorded in their builder.

It reads the sheet in the ORIENTATION the scanner accepted it in (`wide`,
`wide-T`, `long`), and finds EVERY block, where the scanner stops at the first:
two arms side by side are two blocks here and one acceptance there. It never
changes what the scanner accepts.

It prints, and writes only where `-o` says. Publisher bytes stay out of this
repository: write the CSV outside it, or under a gitignored path.
"""
import argparse
import csv
import hashlib
import os
import re
import sys

from unpool import scan
from unpool import sheet as sheet_mod

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIELDS = ["pmcid", "file", "sheet", "sha256", "layout", "block", "block_label",
          "subject", "subject_label", "arm", "time", "value", "state"]


def _text(c):
    if c is None:
        return ""
    s = str(c).strip()
    return "" if scan._num(c) is not None else s


# Extraction reads sheets a person has already judged, so it may accept a
# `D7` header the scanner refuses (plate wells, V12) -- but only as a WHOLE
# cell, and only in extraction.
_D_TOKEN = re.compile(r"^\s*d\s*(\d+)\s*$", re.I)
_DAYS_AFTER = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(?:d|days?|wks?|weeks?)\s*$", re.I)
# Summary rows the scanner's AGG does not name, as whole labels only:
# `N | 6 | 6 | 6` and `AVE | 60.5 | 126.8` were extracted as two subjects.
_AGG_ROW = re.compile(r"^\s*(?:n|ave|av|avg|avrg|average|mean|sd|se|sem|std|stdev|count|"
                      r"total|median)\s*[:.]?\s*$", re.I)
# GraphPad exports put the analysis beside the data: significance markers and
# test headers, which a day axis above them makes look like subjects (V27).
_STATS_ROW = re.compile(r"^\s*(?:(?:ns|\*{1,4})\s*$|F\s*\(DFn|P\s*value|Adjusted\s*P|"
                        r"Two-stage|Summary\s*$|Significant\?|Mean\s*Diff)", re.I)


def _day_text(c):
    """-> the day in a header cell written as text (`Day 7`, `Week 2`, `D7`), or None."""
    if not isinstance(c, str):
        return None
    m = scan.HDR_DAY.match(c) or _D_TOKEN.match(c) or _DAYS_AFTER.match(c)
    return float(m.group(1)) if m else None


def _axis_runs(hdr):
    """-> [[(col, day), ...], ...]: the header's increasing day runs.

    The scanner's own sanity tests (span, start, not-one-jump), plus one it
    does not need and extraction does: every day is a WHOLE number or was
    written as day text. The scanner also demands that the rows below GROW,
    which is what keeps a row of tumour volumes (0, 49.39, 121.1, 298.7) from
    being read as an axis; extraction cannot demand growth of a verified
    sheet, so it demands a header-shaped header instead."""
    if len(hdr) > 260:
        return []
    days = []
    for j, c in enumerate(hdr):
        d, txt = scan._num(c), False
        if d is None:
            d, txt = _day_text(c), True
        if d is not None and 0 <= d <= 400 and (txt or float(d).is_integer()):
            days.append((j, d))
    if len(days) < scan.MIN_POINTS:
        return []
    runs, cur = [], [days[0]]
    for prev, nxt in zip(days, days[1:]):
        if nxt[1] > prev[1]:
            cur.append(nxt)
        else:
            runs.append(cur)
            cur = [nxt]
    runs.append(cur)
    good = []
    for run in runs:
        ds = [d for _, d in run]
        if len(run) < scan.MIN_POINTS or ds[0] > 60 or ds[-1] - ds[0] < 3:
            continue
        steps = [b - a for a, b in zip(ds, ds[1:])]
        if max(steps) > 0.85 * (ds[-1] - ds[0]):
            continue
        good.append(run)
    return good


def _widen(run, rows, hi):
    """A header split over two rows (`Day 4 .. Day 21` above, `Day 0` below it
    in the next column to the left): day TEXT in the row above or below joins
    the axis if it keeps the order. Numbers never do -- that is a data row."""
    run = list(run)
    for ri in (hi - 1, hi + 1):
        if 0 <= ri < len(rows):
            for j, c in enumerate(rows[ri] or []):
                d = _day_text(c)
                if d is None or any(j == k for k, _ in run):
                    continue
                if j < run[0][0] and d < run[0][1]:
                    run.insert(0, (j, d))
                elif j > run[-1][0] and d > run[-1][1]:
                    run.append((j, d))
    return run


def _texts(rows, lo, hi, c0, c1):
    return [t for ri in range(max(0, lo), hi)
            for t in (_text(c) for c in (rows[ri] or [])[max(0, c0):c1 + 1]) if t]


def wide_blocks(rows):
    """-> list of blocks: {"label", "axis": [days], "subjects": [(label, [(t, v)])]}.

    A header row with a day axis opens a group. Below it, subjects run until a
    row with no number under the axis; up to two such rows are skipped before
    the first subject (a split header, a units line), and after a blank
    separator the next run of subjects is a NEW block on the SAME axis -- arms
    laid side by side, one day column shared. A row that is itself a header
    ends the group. A row taken as a subject is never re-read as a header."""
    used, blocks = set(), []
    for hi, hdr in enumerate(rows):
        if hi in used or not hdr:
            continue
        for run in _axis_runs(hdr):
            run = _widen(run, rows, hi)
            cols = [j for j, _ in run]
            first = cols[0]
            cur, blank, gap_start = None, 0, hi + 1
            group = []
            for ri in range(hi + 1, len(rows)):
                r = rows[ri] or []
                pairs = [(d, scan._num(r[j])) for (j, d) in run if j < len(r)]
                pairs = [(d, v) for d, v in pairs if v is not None]
                if not pairs:
                    if cur is not None:
                        group.append(cur)
                        cur = None
                        gap_start = ri
                    blank += 1
                    # a header may sit a few empty rows above its data; after
                    # the first subject, two empty rows end the table
                    if blank > (2 if (group or cur) else 4):
                        break
                    continue
                if cur is None and ri > hi + 1 and _axis_runs(r):
                    break                          # the next table's header
                blank = 0
                labels = [_text(c) for c in r[:first]]
                said = [t for t in labels if t]
                if scan.AGG.search(" ".join(labels)) or any(
                        _AGG_ROW.match(t) for t in said) or (
                        said and all(_STATS_ROW.match(t) for t in said)):
                    # Mean / SEM / n rows are not subjects; a statistics row is
                    # skipped only when statistics are ALL it says -- a mouse
                    # beside a GraphPad `P value` cell is still a mouse (V29)
                    continue
                # GROUP NAMES IN MERGED CELLS (V27): GraphPad lays arms side by
                # side with no blank between them, the arm's name written once
                # over its span. Read transposed, that is a label column that
                # is blank under each name until the next one. A NEW name in a
                # column that went blank inside this block starts a new block;
                # a column filled on every row (`Mouse #1, #2`) never splits.
                # Only a column that NAMED this block at its first subject can
                # name the next one: a banner merged across the table lands
                # mid-block in some other column (the worked example's
                # `MDA-MB-231 ...` beside its second mouse) and is not a group.
                if cur is not None and cur["subjects"] and any(
                        t and cur["blank"].get(k) and k in cur["named"]
                        for k, t in enumerate(labels)):
                    group.append(cur)
                    cur = {"label": " | ".join(t for t in labels if t),
                           "axis": [d for _, d in run], "subjects": [],
                           "carry": {}, "rows": [], "blank": {}, "split": True}
                if cur is None:
                    lab = _texts(rows, gap_start if group else hi - 3, ri,
                                 first - 1, cols[-1])
                    if not group:
                        lab += [_text(c) for c in hdr[:first] if _text(c)]
                    cur = {"label": " | ".join(lab), "axis": [d for _, d in run],
                           "subjects": [], "carry": {}, "rows": [], "blank": {}}
                # merged cells: an arm name written once, over its first
                # subject only, is carried down to the subjects under it.
                # Each level is carried on its own and never cleared: a sheet
                # banner merged across the whole table lands in some OTHER
                # subject's row, and clearing "deeper" levels whenever a
                # shallower one changed erased the arm of 8 of the worked
                # example's 9 NTC mice.
                for k, t in enumerate(labels):
                    if t:
                        cur["carry"][k] = t
                if len(pairs) >= 2:
                    lab = " | ".join(cur["carry"][k] for k in sorted(cur["carry"]))
                    if not cur["subjects"]:
                        cur["named"] = {k for k, t in enumerate(labels) if t}
                    cur["subjects"].append((lab, pairs))
                    cur["rows"].append(ri)
                    for k, t in enumerate(labels):
                        cur["blank"][k] = not t
            if cur is not None:
                group.append(cur)
            for b in group:
                # an arm of one animal, cut off by a group name, is still an
                # arm; an unsplit run of one is noise, as before
                if len(b["subjects"]) >= (1 if b.get("split") else 2):
                    used.update(b["rows"])
                    blocks.append({k: b[k] for k in ("label", "axis", "subjects")})
    return blocks


def long_blocks(rows):
    """The scanner's LONG layout, all subjects kept: id | time | value."""
    for hi in range(min(6, len(rows))):
        hdr = [str(c) if c is not None else "" for c in rows[hi]]
        ids = ([j for j, h in enumerate(hdr) if scan.IDCOL_STRICT.match(h)]
               + [j for j, h in enumerate(hdr)
                  if scan.IDCOL.match(h) and not scan.IDCOL_STRICT.match(h)])
        ts = [j for j, h in enumerate(hdr) if scan._tcol_hit(h)]
        vs = [j for j, h in enumerate(hdr) if scan.VCOL.search(h)]
        for i_id in ids:
            for i_t in ts:
                for i_v in vs:
                    if i_t == i_v or i_id in (i_t, i_v):
                        continue
                    per = {}
                    for r in rows[hi + 1:]:
                        if len(r) <= max(i_id, i_t, i_v):
                            continue
                        lab = str(r[i_id])
                        t, v = scan._num(r[i_t]), scan._num(r[i_v])
                        if scan.AGG.search(lab) or t is None or v is None:
                            continue
                        per.setdefault(lab, []).append((t, v))
                    good = {k: sorted(p) for k, p in per.items() if len(p) >= 2}
                    if len(good) >= 2:
                        return [{"label": "%s | %s | %s" % (hdr[i_id], hdr[i_t], hdr[i_v]),
                                 "axis": sorted({t for p in good.values() for t, _ in p}),
                                 "subjects": list(good.items())}]
    return []


def verified_sheets():
    """{(pmcid, sheet): record} for every registry row; `record` says who
    verified it (`contributed/<handle>/...`) or which builder re-derived it."""
    path = os.path.join(_ROOT, "registry.csv")
    if not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as fh:
        return {(r["pmcid"], r["sheet"].strip().lower()): r.get("record", "")
                for r in csv.DictReader(fh) if r.get("sheet")}


def extract(pmcid, sheet, member=None, layout=None, fetch=True):
    """-> (file, sha256, layout, blocks). Raises sheet.SheetWall."""
    name, rows = sheet_mod.load(pmcid, sheet, member, fetch)
    zf = sheet_mod._zip(pmcid, fetch=False)
    digest = hashlib.sha256(zf.read(name)).hexdigest()
    auto = layout is None
    if layout is None:
        v = scan.judge_any(rows)
        if not v:
            raise sheet_mod.SheetWall(
                "the scanner does not accept this sheet, so there is no layout "
                "to read it by -- pass --layout wide, wide-T or long if you have "
                "read it and know")
        layout = v[0]
    if layout.startswith("wide-idx"):
        raise sheet_mod.SheetWall(
            "wide-idx: the header carries a day INDEX, not days, so no time "
            "value exists on the sheet to extract. Write a builder.")
    blocks = _read(rows, layout)
    # ORIENTATION FALLBACK (V27): the scanner's orientation is a guess good
    # enough to ACCEPT a sheet; on 42 of 43 empty extractions in V26 the
    # opposite one held every block. Only when asked to choose, only when the
    # first reading is empty: a sheet that reads today reads the same.
    flip = {"wide": "wide-T", "wide-T": "wide"}
    if auto and not blocks and layout in flip:
        other = _read(rows, flip[layout])
        if other:
            layout, blocks = flip[layout], other
    return os.path.basename(name), digest, layout, blocks


def _read(rows, layout):
    grid = scan._transpose(rows) if layout.endswith("-T") else rows
    return long_blocks(grid) if layout.startswith("long") else wide_blocks(grid)


def legend_check(pmcid, sheet, fetch=True, p=print):
    """The legend is the reference for group sizes (V25 P3: 17 of 50 subject
    counts wrong, 8 from blocks that were not the readout). Prints every
    `n = ...` the sheet's own legend states; the comparison is the reader's,
    because only the reader can say which block is which panel and arm."""
    from unpool import paper
    cache = os.path.join(paper.CACHE, "%s.fulltext.xml" % pmcid)
    try:
        if not fetch and not os.path.exists(cache):
            raise paper.PaperWall("full text not in the local cache")
        leg = paper.legend_any(pmcid, paper.fulltext(pmcid), sheet)
    except paper.PaperWall as w:
        p("  LEGEND: WALL -- %s. Compare against `unpool paper` by hand." % w)
        return
    if leg is None:
        p("  LEGEND: not located (no figure reference in the sheet name, or it is"
          " in the SI PDF).\n  Compare the blocks against the legend by hand.")
        return
    ns = paper.legend_n(leg[1])
    p("\n  LEGEND %s -- group sizes it states (the reference for the counts above):" % leg[0])
    for k, s in ns:
        p("    * %-14s %s" % (k, s[:220]))
    if not ns:
        p("    none stated in the legend; try `unpool paper` for the methods' n.")
    p("  Each kept block should hold arms x n of its panel. Where it does not,\n"
      "  re-check the cut and which blocks are not the readout (DROP) first;\n"
      "  if the sheet still differs (deaths, exclusions), keep the SHEET's\n"
      "  count and say why in the note. Never type the legend's n as the count.")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pmcid")
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--member", help="the file inside the supplement, if ambiguous")
    ap.add_argument("--layout", choices=["wide", "wide-T", "long", "long-T"],
                    help="override the scanner's orientation")
    ap.add_argument("-o", "--out", help="write the tidy CSV here (outside the repository)")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--legend", action="store_true",
                    help="print the group sizes the sheet's own figure legend "
                         "states, to compare with the blocks")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    try:
        fname, digest, layout, blocks = extract(a.pmcid, a.sheet, a.member,
                                                a.layout, not a.no_fetch)
    except sheet_mod.SheetWall as w:
        print("  WALL -- nothing extracted: %s" % w)
        return 1
    state = ("verified" if (a.pmcid, a.sheet.strip().lower()) in verified_sheets()
             else "candidate")
    n_sub = sum(len(b["subjects"]) for b in blocks)
    print("  %s / %s / %s   layout=%s   state=%s" % (a.pmcid, fname, a.sheet, layout, state))
    print("  %d block(s), %d subject(s)" % (len(blocks), n_sub))
    for i, b in enumerate(blocks, 1):
        vals = [v for _, p in b["subjects"] for _, v in p]
        zeros = sum(1 for _, p in b["subjects"] if p and p[0][1] == 0)
        print("   b%d  %2d subjects  t=%s  values %.4g..%.4g%s" % (
            i, len(b["subjects"]), ",".join("%g" % t for t in b["axis"]),
            min(vals), max(vals),
            "  (%d start at 0 -- a measurement or a placeholder? say which in your builder)" % zeros
            if zeros else ""))
        print("       label: %s" % (b["label"][:100] or "(none written on the sheet)"))
        labs = [lab for lab, _ in b["subjects"] if lab]
        if labs and len(set(labs)) < len(labs):
            print("       subject labels REPEAT (%d distinct of %d): they are not "
                  "identifiers; `subject` is positional" % (len(set(labs)), len(labs)))
    if not blocks:
        print("  no block found in the %s orientation -- try --layout, or write a builder" % layout)
        if a.legend:                   # most useful here: how many there should be
            legend_check(a.pmcid, a.sheet, not a.no_fetch)
        return 1
    if state != "verified":
        print("  STATE: candidate. These rows are what the sheet says, not verified data;")
        print("  read the sheet (`unpool sheet`) and the legend before using them.")
    print("  arm is EMPTY in every row: fill it from the legend, not from the labels.")
    if a.legend:
        legend_check(a.pmcid, a.sheet, not a.no_fetch)
    if not a.out:
        print("  (summary only -- pass -o FILE to write the rows)")
        return 0
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for i, b in enumerate(blocks, 1):
            for k, (lab, pairs) in enumerate(b["subjects"], 1):
                for t, v in pairs:
                    w.writerow({"pmcid": a.pmcid, "file": fname, "sheet": a.sheet,
                                "sha256": digest, "layout": layout, "block": "b%d" % i,
                                "block_label": b["label"], "subject": "b%d:s%d" % (i, k),
                                "subject_label": lab, "arm": "", "time": "%g" % t,
                                "value": repr(v), "state": state})
    print("  wrote %s" % a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
