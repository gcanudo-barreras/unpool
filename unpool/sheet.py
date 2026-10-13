"""Read a supplementary sheet, for the person or the agent verifying it.

    unpool sheet PMC13534483                          # every sheet, with the scanner's verdict
    unpool sheet PMC13534483 --sheet "Fig. 2A"        # that sheet, 60 rows x 20 cols
    unpool sheet PMC13534483 --sheet "Fig. 2A" --rows 0 --cols 0   # all of it

Verifying IS reading the sheet (protocol rule 4), and until this existed an
agent had to write its own zip-and-parse script to do it -- the V23 adjudicator
did exactly that for twenty items.

It PRINTS and never stores: these are publisher bytes, and this repository
redistributes none. Whatever an agent concludes from reading one is
`screened`, not `verified` (skills/unpool/SKILL.md, the output contract).

A sheet it cannot read is a WALL, printed as one and exiting 1 -- never an
empty sheet (rule 10).
"""
import argparse
import os
import re
import sys
import zipfile

from unpool import scan

TABULAR = re.compile(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", re.I)


class SheetWall(Exception):
    """The sheet could not be reached. Not an empty sheet."""


_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _zip(pmcid, fetch):
    path = os.path.join(scan.CACHE, "%s.zip" % pmcid)
    if not os.path.exists(path):              # UNPOOL_WORKDIR may point elsewhere
        path = os.path.join(_ROOT, "si_cache", "%s.zip" % pmcid)
    if not os.path.exists(path) and fetch:
        got = scan.fetch(pmcid)
        if got.startswith("ERR"):
            raise SheetWall("%s: %s" % (pmcid, got))
        path = got
    if not os.path.exists(path):
        raise SheetWall("%s is not in the local cache -- open the supplement "
                        "yourself. A wall, not an empty sheet." % pmcid)
    return zipfile.ZipFile(path)


def sheets(pmcid, member=None, fetch=True):
    """-> iterator of (member, sheet, rows) over the paper's tabular files."""
    zf = _zip(pmcid, fetch)
    base = os.path.basename(member) if member else None
    names = [i.filename for i in zf.infolist() if TABULAR.search(i.filename)
             and (base is None or os.path.basename(i.filename) == base)]
    if base and not names:
        raise SheetWall("%s is not inside %s.zip" % (base, pmcid))
    for name in names:
        for s, rows in scan.sheets_from(name, zf.read(name)):
            yield name, s, rows


def load(pmcid, sheet, member=None, fetch=True):
    """-> (member, rows) for one sheet, matched case- and space-insensitively."""
    want = (sheet or "").strip().lower()
    try:
        for name, s, rows in sheets(pmcid, member, fetch):
            if (s or "").strip().lower() == want:
                return name, rows
    except SheetWall:
        raise
    except Exception as exc:
        raise SheetWall("could not read %s: %s" % (member or pmcid, exc))
    raise SheetWall("sheet %r not found in %s%s" % (
        sheet, pmcid, " / " + os.path.basename(member) if member else ""))


def render(rows, max_rows=60, max_cols=20, width=14):
    """-> lines. 0 means no limit. A cut is always announced, never silent."""
    shown = rows if not max_rows else rows[:max_rows]
    ncols = max((len(r) for r in rows if r), default=0)
    out = []
    for i, r in enumerate(shown):
        cells = list(r or [])[:max_cols or None]
        txt = []
        for c in cells:
            t = "" if c is None else str(c).replace("\n", " ")
            txt.append(t if len(t) <= width else t[:width - 1] + "~")
        out.append("%4d | %s" % (i, " | ".join(txt).rstrip()))
    if max_rows and len(rows) > max_rows:
        out.append("     ... %d more row(s): --rows 0 shows all" % (len(rows) - max_rows))
    if max_cols and ncols > max_cols:
        out.append("     ... %d more column(s): --cols 0 shows all" % (ncols - max_cols))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pmcid")
    ap.add_argument("--sheet", help="omit to list every sheet with the scanner's verdict")
    ap.add_argument("--member", help="the file inside the supplement, if the sheet name is ambiguous")
    ap.add_argument("--rows", type=int, default=60, help="0 = all")
    ap.add_argument("--cols", type=int, default=20, help="0 = all")
    ap.add_argument("--width", type=int, default=14, help="characters per cell")
    ap.add_argument("--no-fetch", action="store_true", help="read the local cache only")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    try:
        if not a.sheet:
            n = 0
            for name, s, rows in sheets(a.pmcid, a.member, not a.no_fetch):
                v = scan.judge_any(rows)
                verdict = ("CANDIDATE %s n=%d pts=%d" % v[:3]) if v else "--"
                print("  %-40s %-30s %4d rows  %s" % (os.path.basename(name)[:40],
                                                     str(s)[:30], len(rows), verdict))
                n += 1
            if not n:
                print("  no tabular file in %s's supplement" % a.pmcid)
            return 0
        name, rows = load(a.pmcid, a.sheet, a.member, not a.no_fetch)
    except SheetWall as w:
        print("  WALL -- not an empty sheet: %s" % w)
        return 1
    v = scan.judge_any(rows)
    print("  %s / %s / %s   scanner: %s" % (a.pmcid, os.path.basename(name), a.sheet,
          ("CANDIDATE %s n=%d pts=%d hdr=%s" % (v[0], v[1], v[2], v[-1] or "---")) if v else "not accepted"))
    for line in render(rows, a.rows, a.cols, a.width):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
