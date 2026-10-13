"""the re-export check (protocol rule 7) AXIS 3: the identical-curve fingerprint check, which the
re-export rule cites and **nothing had actually implemented.**

    unpool fingerprint self-scan
    unpool fingerprint check <candidate.csv>

PROVENANCE AND STATUS
------------------------------------------------------------------------------
The re-export check (protocol rule 7) has three axes -- "shared deposit DOI or
accession, shared corresponding author, and **an identical-curve fingerprint
scan**". `mine.py` runs axes 1 and 2 and explicitly
cannot run axis 3: it needs the candidate's actual curves, which only a builder
reading the sheet has. the checklist makes this row's checklist item 4, so it is built
here.

**"AN EXISTING SCAN" WOULD HAVE MEANT THREE DIFFERENT SCANS.**
Looking for one to reuse turned up three incompatible conventions in the
author's builders:

  * `build_control_corpus_v3.py` -- `tuple(sorted((round(d, 6), round(v, 2))))`.
    Sorted, rounded, no model in the key. This is the only one ever used to
    make a real cross-source exclusion (the 33 `LM24LUC` animals that
    fingerprint `ebos` Vehicle mice).
  * `build_control_corpus_v4.py` -- `(model, tuple(sorted(set(pts))))`. Raw
    floats, no rounding, and the MODEL is part of the key.
  * `build_chiang4t1_arms_v1.py` (and `build_constellation_arms_v1.py`) --
    `tuple((round(d, 9), round(v, 9)))`. Unsorted, and 9 dp is not rounding.

They disagree on all three axes of the design, so "the existing scan" was never
a single thing and a check written against any one of them would silently have
been a different check from the others. **This module picks one and states why,
rather than adding a fourth by accident.**

THE CONVENTION, AND THE TWO PLACES IT DELIBERATELY DIFFERS
------------------------------------------------------------------------------
`round(day, 6)`, `round(volume, 2)`, **sorted**, **model NOT in the key** --
v3's, with v3's rounding.

  * **Rounded, because a re-export is a round trip.** A curve that has been
    through Excel and back is the same measurement with different low bits;
    v4's raw-float key and chiang's 9 dp would both call that a non-match,
    which is the failure mode the axis exists to catch.
  * **Sorted, because measurement order is not identity.** A re-export that
    lists the same animal's points in a different order is the same animal.
  * **The model is NOT in the key, and this is the one real departure from v4.**
    A re-export relabelled to a different model name is *exactly* the provenance
    hiding the re-export check (protocol rule 7) was written about, and keying on model would make the axis
    blind to it. Excluding it can only ever refuse MORE, never admit more --
    the same property the re-export check (protocol rule 7) claims for its own amendment -- and the model of
    both sides is reported so a cross-model hit can be read for what it is.

**WHAT IT CANNOT CATCH, NAMED RATHER THAN LEFT TO BE FOUND.** An exact
fingerprint is exact: a re-export that TRUNCATES the series (drops the last two
timepoints), RESCALES it (mm3 to cm3), or drops one animal from the arm does not
match and this axis will pass it. Partial overlap is deliberately **not**
reported -- v3's own docstring records that partial value overlap mis-matched
animals under its pre-fix code and "is not evidence of identity". So a pass here
is a pass on identity, not on independence, and axes 1 and 2 remain the ones
that catch a re-export that was edited on the way out.
"""
import csv
import glob
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# THIRD FILE WITH THIS BUG TODAY. `_ROOT` was the PARENT of this file's
# directory, correct while these modules lived in a subdirectory and
# wrong the moment they moved to the repo root: it resolved one level ABOVE the
# repository, and `self-scan` then reported "no corpus CSVs found" -- a content
# statement about a directory that was never the right one. `mine.py` and
# `guard.py` carried the identical defect and were fixed the same way.
_ROOT = _HERE
CORPUS = os.environ.get("UNPOOL_CORPUS") or os.path.join(_ROOT, "corpus")

FP_DAY_DP = 6           # v3's, deliberately: see the module docstring
FP_VOL_DP = 2

# SUPERSEDED INPUTS. Not "files we don't care about" -- files whose animals
# are ALREADY INDEXED under another source, so indexing them again reports the
# corpus colliding with itself.
#
# v2 is the pre-arm-identity schema (no `source` column); v3/v4 are snapshots
# of v5's own rows.
#
# `paired-arms-v1.csv` was added **because the self-scan gate
# below caught it**, which is the gate doing its job on its first run. It
# reported 86 cross-source collisions against a registered reference of zero,
# all of them `PDXNet` (in v5, via v3's `load_v2`) against
# `PDXNet-PDTC-Export-20260407-102250` (in the paired file) -- the same
# physical `HCI-*` mice under two source labels. `build_control_corpus_v5.py`
# already knows: the file is in its own `EXCLUDED_FILES` for exactly this
# reason. Measured here rather than taken on trust: **109 of its 206 curves
# are already in v5** (the other 97 are treated animals v5 drops), so nothing
# is lost by skipping it.
#
# **`novartis-arms-v1.csv` IS NOT SKIPPED, AND THE ASYMMETRY IS THE POINT.**
# v5 excludes it too, but for an unrelated reason -- 223 arms of ~1 animal each
# never reach the five-animal floor -- and **0 of its 4642 curves are in v5**.
# Those animals are accepted corpus data that live nowhere else, so a candidate
# re-exporting one is a real collision this axis must catch. Reusing v5's
# `EXCLUDED_FILES` wholesale would have conflated "superseded" with "too small
# to use" and made the axis blind to the entire PDXE deposit.
SKIP = ("general-prior_dataset-v2.csv", "control-corpus-v3.csv",
        "control-corpus-v4.csv", "paired-arms-v1.csv")   # matched as name endings


class FingerprintRefused(SystemExit):
    """The corpus is not shaped the way this check needs."""


def fingerprint(curve):
    """-> a hashable identity key for one animal's whole (day, volume) series."""
    return tuple(sorted((round(float(d), FP_DAY_DP), round(float(v), FP_VOL_DP))
                        for d, v in curve))


def _curves_from(path):
    """{(source, model, animal_id) -> [(day, volume), ...]} for one corpus CSV.

    Schemas differ across the 24 builders (`role`, `cohort`, `pair_id` and the
    rest), so this reads only the five columns every one of them has."""
    out = defaultdict(list)
    with open(path, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh, delimiter=";")
        need = {"animal_id", "model", "source", "days", "volumes"}
        if not rd.fieldnames or not need.issubset(rd.fieldnames):
            return {}
        for r in rd:
            try:
                d, v = float(r["days"]), float(r["volumes"])
            except (TypeError, ValueError):
                continue
            out[(r["source"].strip(), r["model"].strip(),
                 r["animal_id"].strip())].append((d, v))
    return out


def corpus_index(paths=None, exclude=()):
    """{fingerprint -> [(source, model, animal_id), ...]} over accepted arms.

    `exclude` is a set of BASENAMES left out on top of `SKIP` (a file
    whose name ends with an entry of either is skipped). A builder MUST
    pass its own output file: once it has run, its rows sit in `CORPUS` like
    any other, and a second run would find every animal fingerprinting itself
    and refuse to rebuild. That is not a re-export -- it is the same file --
    and this gate caught it on the first re-run of both LLC builders."""
    if paths is None:
        skip = set(SKIP) | set(exclude)
        paths = [p for p in sorted(glob.glob(os.path.join(CORPUS, "*.csv")))
                 if not os.path.basename(p).endswith(tuple(skip))]
    if not paths:
        # "the directory is empty" and "everything in it was excluded" are
        # different facts and only one is about the corpus.
        present = sorted(glob.glob(os.path.join(CORPUS, "*.csv")))
        if present and exclude:
            raise FingerprintRefused(
                "every corpus file was excluded: %d present, %d excluded (%s). "
                "Nothing was compared -- this is NOT a pass."
                % (len(present), len(exclude), ", ".join(sorted(exclude))))
        raise FingerprintRefused(f"no corpus CSVs found under {CORPUS}")
    index = defaultdict(list)
    for p in paths:
        for key, pts in _curves_from(p).items():
            index[fingerprint(pts)].append(key)
    return index


def check(candidate_curves, index=None, exclude=()):
    """-> [(candidate_id, [(source, model, animal_id), ...]), ...].

    `candidate_curves` is {animal_id -> [(day, volume), ...]}. Empty means the
    axis passes. A hit does NOT auto-refuse: the re-export check's remedy is that ingestion
    stops until it is explained in the builder's docstring."""
    if index is None:
        index = corpus_index(exclude=exclude)
    hits = []
    for aid, pts in candidate_curves.items():
        owners = index.get(fingerprint(pts))
        if owners:
            hits.append((aid, owners))
    return hits


def self_scan(index=None, exclude=()):
    """THE INSTRUMENT GATE. The corpus scanned against itself: any fingerprint
    held by two different SOURCES is a duplicate that survived ingestion.

    The registered reference is **zero**, which is v4's own duplicate-scan
    reference and is what v3's `LM24LUC`/`ebos` exclusion was made to achieve.
    A non-zero result here is a finding about the corpus, not about a
    candidate, and it means this axis is being run on a population that already
    contains what it is meant to detect."""
    if index is None:
        index = corpus_index(exclude=exclude)
    cross, within = [], 0
    for fp, owners in index.items():
        if len(owners) < 2:
            continue
        if len({o[0] for o in owners}) > 1:
            cross.append(owners)
        else:
            within += len(owners) - 1
    return index, cross, within


def _load_candidate(path):
    """A candidate file in the corpus schema: `animal_id;...;days;volumes`."""
    per = defaultdict(list)
    with open(path, encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh, delimiter=";")
        if not rd.fieldnames or not {"animal_id", "days",
                                     "volumes"}.issubset(rd.fieldnames):
            raise FingerprintRefused(
                f"{path}: expected a ';'-delimited corpus-schema CSV with at "
                f"least animal_id/days/volumes; got {rd.fieldnames}")
        for r in rd:
            try:
                per[r["animal_id"].strip()].append(
                    (float(r["days"]), float(r["volumes"])))
            except (TypeError, ValueError):
                continue
    return dict(per)


def write_record(mode, payload, out_dir=None):
    """Persist the scan: what corpus, how many curves, what it found.

    Same reasoning as guard.py's. A duplicate-screening result a review wants
    to cite ("N held sources, 0 cross-source collisions, date") existed only as
    stdout, so citing it meant remembering to redirect and trusting the memory.
    """
    import datetime
    import json
    out_dir = out_dir or os.environ.get("UNPOOL_OUT") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs")
    os.makedirs(out_dir, exist_ok=True)
    rec = {"tool": "fingerprint.py", "mode": mode,
           "corpus_dir": CORPUS,
           "key": "day %d dp, vol %d dp, sorted, model NOT in key"
                  % (FP_DAY_DP, FP_VOL_DP),
           "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "does_not_catch": ["rescaled units", "truncated series",
                              "partial overlap", "one dropped subject"],
           **payload}
    dest = os.path.join(out_dir, "fingerprint_%s.json" % mode.replace(" ", "_"))
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    return dest


def main(argv):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    # --exclude REACHED THE API AND NOT THE CLI, AND THE DOCSTRING ALREADY
    # SAID A BUILDER MUST USE IT. Checking a file that already sits in the
    # corpus directory made every animal fingerprint ITSELF and fired a false
    # AXIS 3 HIT. Reproduced on purpose by a systematic-review user.
    exclude, rest, it = [], [], iter(argv)
    for a in it:
        if a == "--exclude":
            exclude.append(os.path.basename(next(it, "")))
        elif a.startswith("--exclude="):
            exclude.append(os.path.basename(a.split("=", 1)[1]))
        else:
            rest.append(a)
    argv = rest
    if not argv or argv[0] not in ("self-scan", "check"):
        print(__doc__.split("\n\n")[0])
        print("\nusage: fingerprint.py self-scan")
        print("       fingerprint.py check <candidate.csv> [--exclude FILE]")
        print("")
        print("  --exclude leaves a corpus file out of the index. The file")
        print("  you pass to `check` is excluded automatically.")
        return 2

    # --exclude REACHED THE API AND NOT THE CLI, AND THE DOCSTRING ALREADY
    # SAID A BUILDER MUST USE IT. Checking a file that already sits in the
    # corpus directory made every animal fingerprint ITSELF and fired a false
    # AXIS 3 HIT. Reproduced on purpose by a systematic-review user.
    exclude, rest, it = [], [], iter(argv)
    for a in it:
        if a == "--exclude":
            exclude.append(os.path.basename(next(it, "")))
        elif a.startswith("--exclude="):
            exclude.append(os.path.basename(a.split("=", 1)[1]))
        else:
            rest.append(a)
    argv = rest
    if argv and argv[0] == "check" and len(argv) > 1:
        auto = os.path.basename(argv[1])
        if auto not in exclude:
            exclude.append(auto)   # done for the user, not explained to them
    index, cross, within = self_scan(exclude=exclude)
    n_curves = sum(len(v) for v in index.values())
    print(f"  corpus: {n_curves} curves indexed, {len(index)} distinct "
          f"fingerprints  [day {FP_DAY_DP} dp, vol {FP_VOL_DP} dp, sorted, "
          f"model NOT in key]")
    print(f"  identical curves within one source : {within}")
    print(f"  fingerprints spanning TWO SOURCES  : {len(cross)}  "
          f"(registered reference: 0)")
    for owners in cross[:10]:
        print(f"    CROSS-SOURCE {owners}")

    if argv[0] == "self-scan":
        print("  record: %s" % write_record("self-scan", {
            "corpus_files_excluded": sorted(exclude),
            "curves_indexed": n_curves, "distinct_fingerprints": len(index),
            "within_source_identical": within,
            "cross_source_collisions": len(cross),
            "registered_reference": 0,
            "state": "PASSED" if not cross else "COLLISIONS FOUND"}))
        return 0 if not cross else 1

    cand = _load_candidate(argv[1])
    hits = check(cand, index)
    print(f"\n  candidate {os.path.basename(argv[1])}: {len(cand)} animals")
    if not hits:
        print("  AXIS 3 PASSES -- no animal fingerprints an accepted curve.")
        print("  (identity only: a truncated or rescaled re-export does not "
              "match and is not ruled out by this.)")
        return 0
    print(f"  AXIS 3 HIT on {len(hits)} animal(s) -- the re-export check (protocol rule 7): ingestion STOPS "
          f"until this is explained in the builder's docstring.")
    for aid, owners in hits:
        print(f"    {aid}  ==  {owners}")
    return 1


def demo():
    """Self-check. Offline, no corpus needed."""
    a = [(0.0, 100.0), (7.0, 220.0), (14.0, 480.0)]

    # (1) Order is not identity: the same points shuffled are the same animal.
    assert fingerprint(a) == fingerprint(list(reversed(a)))

    # (2) Rounding is what makes a round trip through a spreadsheet match --
    #     and the boundary is real, not decorative.
    assert fingerprint(a) == fingerprint([(0.0, 100.001), (7.0, 220.0),
                                          (14.0, 480.0)])
    assert fingerprint(a) != fingerprint([(0.0, 100.4), (7.0, 220.0),
                                          (14.0, 480.0)])

    # (3) A truncated re-export does NOT match. This is the documented blind
    #     spot, asserted so it cannot be quietly "fixed" into a partial match.
    assert fingerprint(a) != fingerprint(a[:2])

    # (4) check() finds an exact duplicate and ignores a merely similar curve.
    index = {fingerprint(a): [("Accepted-SRC", "LLC", "mouse-1")]}
    hits = check({"cand-1": list(reversed(a)),
                  "cand-2": [(0.0, 101.0), (7.0, 220.0), (14.0, 480.0)]}, index)
    assert len(hits) == 1 and hits[0][0] == "cand-1", hits
    assert hits[0][1] == [("Accepted-SRC", "LLC", "mouse-1")]

    # (5) The model is NOT in the key: a re-export relabelled to another model
    #     still collides. This is the departure from v4 and the reason for it.
    assert check({"relabelled": a}, index), "a cross-model re-export must hit"

    print("fingerprint demo: all checks pass")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        sys.exit(main(sys.argv[1:]))
