"""V7 — the BLI census. Every cached paper, every member, every sheet.

Registered in `docs/VALIDATION.md` before this file was written. The BLI
vocabulary regex below is the one in that registration, character for
character; it is not adjusted after seeing a result (protocol rule 9).

Answers three of the four registered questions:

  P1  does removing `bli|flux|radiance` from `value` change what is accepted?
      (run twice, once with UNPOOL_PROFILE=tumor_volume and once with the
      knockout profile written beside it)
  P2  are BLI-vocab sheets accepted at a rate comparable to all sheets?
  P3  does a log10(flux) series fall below `fold_lo` and get rejected?
  P4  is answered by hand against V2's table, not here.

Run:  python studies/bli_census.py [--limit N]
Writes: studies/bli_census.csv  and  studies/bli_census.json
"""
import csv
import glob
import json
import os
import re
import sys
import time
import zipfile

# THE SAME POPULATION THE TOOL ITSELF READS, NOT A LARGER ONE.
# `scan_one` considers only tabular members and skips any over 40 MB. A census
# that read more than the tool reads would measure a population the tool never
# sees, and its accept RATE would not be the tool's accept rate.
# The skips are COUNTED, never silent -- V1 found four papers reported as "no
# per-animal table found" that had simply never been opened, and one of them
# held ten sheets the scanner accepts.
TABULAR = re.compile(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", re.I)
MAX_MEMBER = 40 * 1024 * 1024

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool import scan  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
CACHE = os.path.join(_ROOT, "si_cache")

# FIXED IN THE REGISTRATION, BEFORE THE SWEEP. Do not edit to chase a result.
BLI_VOCAB = re.compile(
    r"bioluminescen|luminescen|photon|p/s|radiance|total\s*flux|\bflux\b"
    r"|\bBLI\b|IVIS|luciferase|\bluc\b", re.I)

# A log-scale readout announces itself in the header, or sits in the narrow
# numeric band a log10 of a photon count occupies. Both declared in advance.
LOG_HDR = re.compile(r"log\s*10|log10|log\s*\(|\blog\b", re.I)
LOG_BAND = (2.0, 12.0)


def header_text(rows, window=8):
    """The first `window` rows, flattened. The region a header lives in."""
    out = []
    for r in rows[:window]:
        for c in r:
            if c is not None:
                out.append(str(c))
    return " | ".join(out)


def looks_log(rows, cols_window=40):
    """-> True if this sheet's numbers look like log10 of something big.

    Header says log, OR every numeric cell in the body sits inside LOG_BAND
    while the sheet also carries BLI vocabulary. The second arm is what catches
    a sheet whose header says only `Flux` and whose values are 5.8 .. 9.1.
    """
    if LOG_HDR.search(header_text(rows)):
        return True
    vals = []
    for r in rows[:60]:
        for c in r[:cols_window]:
            v = scan._num(c)
            if v is not None and v != 0:
                vals.append(abs(v))
    if len(vals) < 20:
        return False
    lo, hi = LOG_BAND
    return all(lo <= v <= hi for v in vals)


def sweep(limit=None, on_partial=None):
    zips = sorted(glob.glob(os.path.join(CACHE, "*.zip")))
    if limit:
        zips = zips[:limit]

    rowsout = []
    stats = {"papers": 0, "members": 0, "sheets": 0, "unreadable_members": 0,
             "size_skipped_members": 0, "bad_zips": 0,
             "accepted": 0, "bli_sheets": 0, "bli_accepted": 0,
             "log_bli_sheets": 0, "log_bli_accepted": 0}
    t0 = time.time()
    for n, z in enumerate(zips, 1):
        stats["papers"] += 1
        pmcid = os.path.splitext(os.path.basename(z))[0]
        try:
            zf = zipfile.ZipFile(z)
            infos = zf.infolist()
        except Exception:
            stats["bad_zips"] += 1
            continue
        for info in infos:
            member = info.filename
            if not TABULAR.search(member):
                continue
            if info.file_size > MAX_MEMBER:
                stats["size_skipped_members"] += 1
                continue
            try:
                blob = zf.read(member)
            except Exception:
                stats["unreadable_members"] += 1
                continue
            try:
                sheets = list(scan.sheets_from(member, blob))
            except Exception:
                stats["unreadable_members"] += 1
                continue
            if sheets:
                stats["members"] += 1
            for sname, rows in sheets:
                stats["sheets"] += 1
                htxt = header_text(rows)
                is_bli = bool(BLI_VOCAB.search(htxt))
                verdict = scan.judge_any(rows)
                ok = verdict is not None
                if ok:
                    stats["accepted"] += 1
                if not is_bli:
                    continue
                stats["bli_sheets"] += 1
                if ok:
                    stats["bli_accepted"] += 1
                lg = looks_log(rows)
                if lg:
                    stats["log_bli_sheets"] += 1
                    if ok:
                        stats["log_bli_accepted"] += 1
                rowsout.append({
                    "pmcid": pmcid, "member": member, "sheet": sname,
                    "accepted": int(ok),
                    "layout": verdict[0] if ok else "",
                    "n_animals": verdict[1] if ok else "",
                    "n_points": verdict[2] if ok else "",
                    "note": verdict[3] if ok else "",
                    "hdr": verdict[-1] if ok else "",
                    "log_scale": int(lg),
                    "header_snippet": htxt[:300].replace("\n", " "),
                })
        # PROGRESS MUST BE VISIBLE, AND IT MUST SURVIVE A KILL.
        # The first attempt at this sweep ran 48 minutes behind a `grep` that
        # block-buffered every flushed line, so it was indistinguishable from a
        # hang and was killed -- losing the whole run. Same defect class as the
        # one already fixed in mine.py, reintroduced one layer out. Progress is
        # frequent, and a partial result is written as it goes, so a kill costs
        # the remainder rather than everything.
        if n % 50 == 0:
            el = time.time() - t0
            print("  %d/%d papers  %d sheets  %d BLI  %.0fs  (eta %.0f min)"
                  % (n, len(zips), stats["sheets"], stats["bli_sheets"], el,
                     (el / n) * (len(zips) - n) / 60), flush=True)
        if n % 250 == 0 and on_partial:
            on_partial(rowsout, stats, partial=True)
    stats["elapsed_s"] = round(time.time() - t0, 1)
    return rowsout, stats


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    scan.preflight_banner()
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])

    profile = os.environ.get("UNPOOL_PROFILE", "tumor_volume")
    scan.load_profile(profile)
    print("profile: %s" % profile)

    tag = "" if profile == "tumor_volume" else "_" + os.path.basename(
        profile).replace(".toml", "")

    def write_out(rows, st, partial=False):
        """One writer for the final result and for every partial."""
        csv_p = os.path.join(_HERE, "bli_census%s.csv" % tag)
        with open(csv_p, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else
                               ["pmcid"], delimiter=",")
            w.writeheader()
            w.writerows(rows)
        rec = dict(st)
        rec["partial"] = partial
        rec["profile"] = profile
        sh = st.get("sheets") or 0
        rec["base_accept_rate"] = round(st["accepted"] / sh, 4) if sh else 0
        bs = st.get("bli_sheets") or 0
        rec["bli_accept_rate"] = round(st["bli_accepted"] / bs, 4) if bs else 0
        with open(os.path.join(_HERE, "bli_census%s.json" % tag), "w",
                  encoding="utf-8") as fh:
            json.dump(rec, fh, indent=1)
            fh.flush()
            os.fsync(fh.fileno())

    rowsout, stats = sweep(limit, on_partial=write_out)

    out_csv = os.path.join(_HERE, "bli_census%s.csv" % tag)
    write_out(rowsout, stats)

    base_rate = (stats["accepted"] / stats["sheets"]) if stats["sheets"] else 0
    bli_rate = ((stats["bli_accepted"] / stats["bli_sheets"])
                if stats["bli_sheets"] else 0)
    stats["base_accept_rate"] = round(base_rate, 4)
    stats["bli_accept_rate"] = round(bli_rate, 4)
    stats["profile"] = profile
    with open(os.path.join(_HERE, "bli_census%s.json" % tag), "w",
              encoding="utf-8") as fh:
        json.dump(stats, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())

    print("\n%-28s %d" % ("papers", stats["papers"]))
    print("%-28s %d" % ("sheets read", stats["sheets"]))
    print("%-28s %d" % ("unreadable members", stats["unreadable_members"]))
    print("%-28s %d  (%.1f%%)  <- the unit counted is SHEETS"
          % ("accepted, all sheets", stats["accepted"], 100 * base_rate))
    print("%-28s %d" % ("sheets with BLI vocabulary", stats["bli_sheets"]))
    print("%-28s %d  (%.1f%%)"
          % ("  of those, accepted", stats["bli_accepted"], 100 * bli_rate))
    print("%-28s %d" % ("  of those, log-scale", stats["log_bli_sheets"]))
    print("%-28s %d" % ("    of those, accepted", stats["log_bli_accepted"]))
    print("\nwrote %s (%d rows), %.0fs"
          % (out_csv, len(rowsout), stats["elapsed_s"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
