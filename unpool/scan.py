"""Supplementary-file triage: does this paper's supplementary hold PER-ANIMAL
longitudinal tumour volumes, or group means?

Decides on STRUCTURE, never on wording. A sheet titled "Tumor growth" that holds
`mean +/- SD` is rejected; a sheet with no title at all whose rows are animals
and whose columns are days is accepted. That asymmetry is the whole point --
One origin-project paper's supplement said "Tumor volume data" on page 2 and carried medians.

Usage:  unpool scan PMC6707218 PMC7320135 ...
Writes: si_scan_out.csv and si_cache/ into `UNPOOL_WORKDIR` if set,
        otherwise at the root of the clone (both gitignored).

PROVENANCE AND STATUS
------------------------------------------------------------------------------
Its gate is `tests/test_recall.py`, which runs offline against the cached
publisher fixtures in `fixtures/cache/`, with ground truth taken from the
builders' own `_VERIFIED_N` constants -- `fixtures/ground_truth.csv` carries
the citation on every row. Evidence that lives in a temporary directory
cannot be re-run, which is why the gate is a tracked file.

**MEASURED, AND BOTH NUMBERS BELONG TOGETHER.** Recall **15/15** on the
cached fixtures -- but that is the score on the TUNING SET, the scanner
having been re-tuned twice against them. Out of sample (`docs/VALIDATION.md`,
V1), 9 of a campaign's rejects were audited by hand and 1 was a false
negative: a day value living in header TEXT (`Day1`), which this scanner
reads as a number and cannot parse.

**AND THE PRECISION COST IS REAL AND THE GATE DOES NOT MEASURE IT.** On an
unbiased sample of 15 accepted papers, seed registered in advance, **9 were
false on verification** -- precision 6 of 15 (`docs/VALIDATION.md`, V2). The
four from the original hand-checked batch remain the clearest examples:
`PMC13408911` and `PMC13385831` were returned on a `4T1` mention while every
sheet it counted was B16F10 melanoma; `PMC13367972` is arm-level
`Average / SEM / Number of mice`, with statistic columns counted as animals;
`PMC13319373` is a differential gene-expression table read transposed, gene
symbols taken for animal IDs. **This scanner triages; it does not verify.**
No acceptance of its may enter a corpus until a builder has checked model
identity at the sheet, the control arm, and the animal count -- see
`docs/PROTOCOL.md`, rule 4.

Known structural gaps, none of them chased: `judge()`'s 6-8 row header window
misses sheets with long blank preambles; `IDCOL`'s `tumou?r` alternative can
take a model-name column for the per-animal ID column; tiled side-by-side
blocks whose ARM LABEL sits in a column rather than a header row are scored on
the wrong axis (this is what nearly lost `PMC13393277`, whose real 10-animal
control arm sits in such a block); `.docx` and `.pdf` supplements are not
opened at all, which an audit measured as costing nothing across 18 documents.
"""
import csv
import io
import os
import re
import sys
import time
import urllib.request
import zipfile

# One User-Agent for every request this project makes: it names the tool and
# where to reach it, as Europe PMC and the data repositories ask. The
# `Mozilla/5.0 (compatible; ...)` prefix is kept because some hosts refuse
# agents that do not start with it.
UA = {"User-Agent": "Mozilla/5.0 (compatible; unpool/0.1; "
                    "+https://github.com/gcanudo-barreras/unpool)"}
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/{}/supplementaryFiles"
# ponytail: paths are anchored to the CLONE, not the install -- the tool is
# used from a checkout (`pip install -e .`). Ship profiles as package data and
# write outputs to the CWD if a wheel install is ever wanted.
_WORKDIR = os.environ.get("UNPOOL_WORKDIR") or \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(_WORKDIR, "si_scan_out.csv")
CACHE = os.path.join(_WORKDIR, "si_cache")

# ---------------------------------------------------------------------------
# A MISSING PARSER IS NOT AN UNREADABLE FILE (protocol rule 10)
# ---------------------------------------------------------------------------
# `sheets_from` used to answer both with `except Exception: return`, so an
# environment without `openpyxl` reported every spreadsheet as "no per-animal
# table found" -- silently, and only ever in the direction of REJECTION. A live
# batch in such an environment returns a clean null result with no error and a
# plausible-looking report. Measured: the recall gate scores 4/21 instead of
# 21/21 on the same files, 17 false negatives, every one a spreadsheet.
#
# So the two are separated. An ImportError is recorded here and reported loudly
# by `preflight()`; a genuine parse failure still returns empty, as it should.
PARSER_FOR = {".xlsx": "openpyxl", ".xlsm": "openpyxl", ".xls": "xlrd"}
_MISSING = set()


def _parser(mod):
    """-> module, or None while recording that this format cannot be read."""
    try:
        return __import__(mod)
    except ImportError:
        _MISSING.add(mod)
        return None


def preflight():
    """-> sorted list of parser modules that are missing.

    Call before trusting ANY rejection. An empty list is the only state in
    which a 'no table found' verdict means what it says.
    """
    for mod in sorted(set(PARSER_FOR.values())):
        _parser(mod)
    return sorted(_MISSING)


def preflight_banner(stream=sys.stderr):
    """Print the refusal-to-be-trusted banner. -> True if anything is missing."""
    missing = preflight()
    if not missing:
        return False
    exts = sorted(e for e, m in PARSER_FOR.items() if m in missing)
    print(chr(10) + "!" * 78, file=stream)
    print("  CANNOT READ %s -- these formats will be reported as EMPTY, not as"
          % ", ".join(exts), file=stream)
    print("  errors, and every one of them will look like an honest rejection.",
          file=stream)
    print("", file=stream)
    print("  missing: %s" % ", ".join(missing), file=stream)
    print("  fix:     python -m pip install %s" % " ".join(missing), file=stream)
    print("", file=stream)
    print("  Do not quote a recall figure, a null result or an empty batch",
          file=stream)
    print("  produced in this state. See protocol rule 10.", file=stream)
    print("!" * 78 + chr(10), file=stream)
    return True


# WINDOWS CONSOLES ARE NOT UTF-8, AND BIOLOGY TITLES ARE.
# A paper called "PPAR<alpha> activation overcomes ..." crashed this script
# with UnicodeEncodeError on a cp1252 console. Greek letters are everywhere in
# this literature, so any run that printed a title was one paper away from
# dying -- invisible to anyone developing with PYTHONIOENCODING set, which is
# exactly how it survived until a fresh user hit it.
#
# Console output degrades; FILES are still written as utf-8 and keep the
# character.
try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass

MAX_ZIP = 120 * 1024 * 1024          # skip monsters; they are imaging, not tables
# ---------------------------------------------------------------------------
# WHAT STAYS HERE, AND WHY IT IS NOT IN THE PROFILE
# ---------------------------------------------------------------------------
# `AGG` is the aggregate-statistic blacklist, and it is the scanner's whole
# thesis: a sheet titled "Tumor growth" holding `mean +/- SD` is REJECTED, a
# sheet with no title at all whose rows are subjects and columns are times is
# ACCEPTED. That asymmetry does not vary by data type -- "mean", "sem" and
# "n =" mean the same thing on a tumour sheet, a plate reader export and a
# behavioural scoring table. Putting it in a profile would invite a user to
# relax the one rule that makes the instrument worth anything.
# V13: TWO MEASURED HOLES CLOSED, AND NOTHING ELSE ADDED.
# `NUMBER OF MICE` was not matched, so on PMC13367972 `Fig. S4A_DOSE_RESPONSE`
# those rows were counted as SUBJECTS and an arm-level means table was
# accepted as five animals. And the trailing boundary meant `n=5` matched
# while `n = 5` did not, because a boundary cannot close between `=` and a
# space.
#
# No plus/minus, IQR, range, 95% CI or p. Those were never measured as holes
# here, and widening a rejection rule past what was measured is V5's error.
AGG = re.compile(r"\b(mean|average|avg|sd|s\.d|sem|s\.e|stdev|std|median|"
                 r"error)\b|\bn\s*=|\bnumber\s+of\s+"
                 r"(?:mice|animals|rats|subjects)\b", re.I)

# ---------------------------------------------------------------------------
# WHAT THE PROFILE CARRIES
# ---------------------------------------------------------------------------
# Everything below is loaded from `profiles/<name>.toml` -- the column patterns
# and the two floors. `tomllib` is stdlib, so a profile costs no dependency,
# and TOML keeps comments, which matters more than it sounds: several of these
# regexes exist because of ONE file each and the profile names that file beside
# the clause. See `profiles/tumor_volume.toml`.
#
# They are module globals rather than an object passed around because `judge()`
# reads them directly and is NOT being rewritten as part of making them
# configurable. Changing how the instrument is configured and changing how it
# judges are two different edits and only one of them is happening here.
PROFILE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")
DEFAULT_PROFILE = os.environ.get("UNPOOL_PROFILE") or "tumor_volume"

PROFILE = None          # the loaded dict, for reports
IDCOL = IDCOL_STRICT = TCOL = VCOL = DAYIDX = None
MIN_ANIMALS = MIN_POINTS = None

# THE RESPONSE SHAPE, AND WHY IT HAD TO LEAVE `judge`
# ---------------------------------------------------------------------------
# `judge`'s wide path used to hardcode "at least 60% of subjects rise" and
# "median fold >= 1.5". Those are TUMOUR GROWTH assumptions, and they were
# sitting inside the structural test where no profile could reach them.
#
# Measured consequence: `body_weight` returned the tumour block of every file
# it was pointed at -- the same sheet, the same `fold=8.0` -- because body
# weight cannot rise 1.5x and the only thing in those workbooks that could was
# the tumour. It never once found a body-weight block. `dose_response` was
# worse: a dose axis DECLINES, and a separate clause rejected fractional axes
# outright on the grounds that they are "a dose-response axis, not a time
# course" -- correct for a time profile, fatal for a dose one.
#
# So two profiles did not work badly. They returned the WRONG DATA TYPE under
# the requested label, which is worse than returning nothing.
RESPONSE = None


def load_profile(name=DEFAULT_PROFILE):
    """Set the module's column patterns and floors from a profile. -> dict.

    Every artifact this tool writes must name the profile it ran under: a
    verdict is only meaningful against the patterns that produced it, and two
    profiles over one corpus give two different answers about the same sheet.
    """
    import tomllib
    global PROFILE, IDCOL, IDCOL_STRICT, TCOL, VCOL, DAYIDX
    global MIN_ANIMALS, MIN_POINTS, RESPONSE
    is_path = os.path.sep in name or name.endswith(".toml")
    path = name if is_path else os.path.join(PROFILE_DIR, name + ".toml")
    if not os.path.exists(path):
        have = sorted(f[:-5] for f in os.listdir(PROFILE_DIR)
                      if f.endswith(".toml"))
        raise SystemExit("no such profile: %s -- available: %s"
                         % (name, ", ".join(have)))
    with open(path, "rb") as fh:
        prof = tomllib.load(fh)
    col, fl = prof["columns"], prof["floors"]
    IDCOL = re.compile(col["subject"], re.I)
    IDCOL_STRICT = re.compile(col["subject_strict"], re.I)
    TCOL = re.compile(col["covariate"], re.I)
    VCOL = re.compile(col["value"], re.I)
    DAYIDX = re.compile(col["ordinal_suffix"], re.I)
    MIN_ANIMALS = int(fl["min_subjects"])
    MIN_POINTS = int(fl["min_points"])
    rp = prof.get("response") or {}
    RESPONSE = {
        "direction": rp.get("direction", "increase"),
        "fold_lo": float(rp.get("fold_lo", 1.5)),
        "fold_hi": float(rp.get("fold_hi", 0.0)),      # 0 = no upper bound
        "min_consistent": float(rp.get("min_consistent", 0.60)),
        "allow_fractional_axis": bool(rp.get("allow_fractional_axis", False)),
    }
    PROFILE = prof
    return prof


load_profile()          # the default, so importing this module is enough



def fetch(pmcid):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{pmcid}.zip")
    if os.path.exists(p) and os.path.getsize(p) > 200:
        return p
    try:
        req = urllib.request.Request(EPMC.format(pmcid), headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read(MAX_ZIP + 1)
    except Exception as e:
        return f"ERR {type(e).__name__}"
    if len(data) > MAX_ZIP:
        return "ERR too_large"
    if data[:2] != b"PK":
        return "ERR not_open_access"
    # Written aside and renamed: a download cut short (Ctrl-C, a killed
    # worker) used to leave a truncated zip at the cached path, which every
    # later run then trusted as the paper's supplement.
    with open(p + ".part", "wb") as fh:
        fh.write(data)
    os.replace(p + ".part", p)
    return p


def _num(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "")
    if not s or s in {"-", "NA", "N/A", "nan", "ND"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def sheets_from(name, blob):
    """Yield (sheet_name, rows) for whatever tabular thing this is."""
    low = name.lower()
    if low.endswith(".csv") or low.endswith(".txt") or low.endswith(".tsv"):
        try:
            txt = blob.decode("utf-8-sig", "replace")
        except Exception:
            return
        sep = "\t" if "\t" in txt.split("\n")[0] else ","
        rows = [r for r in csv.reader(io.StringIO(txt), delimiter=sep)]
        yield "(flat)", rows[:400]
        return
    if low.endswith(".xlsx") or low.endswith(".xlsm"):
        openpyxl = _parser("openpyxl")
        if openpyxl is None:
            return                      # recorded in _MISSING, not silent
        try:
            wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True,
                                        data_only=True)
        except Exception:
            return
        for ws in wb.worksheets:
            rows = []
            for i, r in enumerate(ws.iter_rows(values_only=True)):
                rows.append(list(r))
                if i > 400:
                    break
            yield ws.title, rows
        return
    if low.endswith(".xls"):
        xlrd = _parser("xlrd")
        if xlrd is None:
            return                      # recorded in _MISSING, not silent
        try:
            wb = xlrd.open_workbook(file_contents=blob)
        except Exception:
            return
        for ws in wb.sheets():
            rows = [ws.row_values(i) for i in range(min(ws.nrows, 400))]
            yield ws.name, rows


def _tcol_hit(h):
    """V8 CHANGE B: the covariate may match ANYWHERE in the header.

    Shipped, this was `TCOL.match(h)`, and the profile pattern also began with
    an anchor -- anchored twice, so `Measurement_day_post_CART_injection` could
    not match on either count. Removing one anchor changes nothing; this is the
    code half and the profile carries the other.
    """
    return TCOL.search(h)


# V12: A DAY WRITTEN INTO THE HEADER TEXT.
# `_num('Day1')` is None, so a sheet headed `Day1 | Day4 | Day7` has no axis and
# is invisible -- V1's false negative, and V8 found it is four sheets of
# PMC13538391, not one. The WHOLE CELL must be a day-like token plus a number:
# no bare `t`/`d`/`w` (plate wells and sample codes), and no partial match, so
# `Figure 1`, `Sample 2` and `Mouse #1` stay out. `Mouse #1 | Mouse #2 | ...`
# becoming an axis of 1,2,3 is the index-axis failure V5 named.
# `week`/`wk` change the UNIT, not the shape: the axis is an ordinal covariate
# and the unit belongs in the builder's docstring.
HDR_DAY = re.compile(r"^\s*(?:day|week|wk)\s*[-_ ]?(\d+(?:\.\d+)?)\s*$", re.I)


def _hdr_num(c):
    """`_num`, falling back to a day written into the header text."""
    v = _num(c)
    if v is not None:
        return v
    if isinstance(c, str):
        m = HDR_DAY.match(c)
        if m:
            return float(m.group(1))
    return None


def judge(rows):
    """-> (layout, n_animals, n_points, note, grids, n_below_floor) or None.

    `n_below_floor` counts subjects PRESENT on the sheet that `min_points`
    dropped. It is appended rather than inserted, and `judge_any` still puts
    the header evidence LAST, so `v[4]` is still the grids and `v[-1]` is still
    the evidence for every existing caller.

    `grids` is the per-accepted-animal list of DAY VALUES, added for
    the freeze rule's calendar screen, which needs the candidate's day grid and not just
    its two counts. It is `None` on the `wide-idx` branch, where the header
    carries a day INDEX and the real day numbers are nowhere in the sheet --
    a caller that needs a calendar must treat that as unknown, not as empty.
    Callers that only index [0:3] (`tests/test_recall.py`) are unaffected."""
    if not rows or len(rows) < MIN_ANIMALS:
        return None
    # ---- LONG: an id column, a time column, a value column
    for hi in range(min(6, len(rows))):
        hdr = [str(c) if c is not None else "" for c in rows[hi]]
        # V8 CHANGE A: TRY THE CANDIDATES, DO NOT COMMIT TO THE FIRST.
        # `next(...)` took the first column matching each role and never
        # reconsidered, so one bad match sank the sheet. On PMC12545207 the id
        # pattern's `tumou?r` alternative grabbed `Tumor_model` (col 0) instead
        # of `Mouse_ID` (col 7) -- the exact failure `subject_strict` exists
        # for, in the one branch that never used it -- and 51 mice over 21
        # timepoints were reported as nothing. Strict ids are tried first;
        # `IDCOL`-only matches remain reachable, so nothing that used to pass
        # can stop passing on the id axis.
        id_cands = ([j for j, h in enumerate(hdr) if IDCOL_STRICT.match(h)]
                    + [j for j, h in enumerate(hdr)
                       if IDCOL.match(h) and not IDCOL_STRICT.match(h)])
        t_cands = [j for j, h in enumerate(hdr) if _tcol_hit(h)]
        v_cands = [j for j, h in enumerate(hdr) if VCOL.search(h)]
        for i_id in id_cands:
            for i_t in t_cands:
                for i_v in v_cands:
                    if i_t == i_v or i_id in (i_t, i_v):
                        continue
                    per = {}
                    for r in rows[hi + 1:]:
                        if len(r) <= max(i_id, i_t, i_v):
                            continue
                        lab = str(r[i_id])
                        if AGG.search(lab):
                            continue
                        t, v = _num(r[i_t]), _num(r[i_v])
                        if t is None or v is None:
                            continue
                        per.setdefault(lab, set()).add(t)
                    good = [k for k, v in per.items() if len(v) >= MIN_POINTS]
                    if len(good) >= MIN_ANIMALS:
                        # Subjects PRESENT on the sheet that the points floor
                        # dropped. Reported, never silently discarded: on
                        # PMC12545207 this is 9 of 51, and which 9 is a fact
                        # about the data (there, three short experiments) that
                        # a reader cannot recover from the accepted count.
                        return ("long", len(good),
                                min(len(per[k]) for k in good), "",
                                [sorted(per[k]) for k in good],
                                len(per) - len(good))
    # ---- WIDE: a header row of days, rows of animals
    #
    # PRECISION PASS. The first version of this function accepted any sheet with
    # >= 4 numeric header cells and >= 5 numeric rows, and called 11 of 12 papers
    # a hit -- which is not a triage, it is a pass-through. A Source Data
    # workbook is one sheet per FIGURE, and most figures are not growth curves.
    # Two further tests, both structural rather than lexical:
    #
    #   (i)  a day axis is ORDERED. Strictly increasing, starting at or near
    #        zero, with a sane span. A row of unordered numbers is a set of
    #        conditions, not a time course.
    #   (ii) an untreated tumour GROWS. Most rows must end higher than they
    #        start, and the typical row must gain real ground. This does not
    #        identify what is being measured -- the CT-26 phosphorescence file
    #        taught that no check on the values can -- but it does separate a
    #        time course from a matrix of unrelated measurements.
    #
    # BLOCK-STACKED SHEETS. A day axis that RESETS partway across the row
    # (9,12,15,18,21, blank, 9,12,15,18,21, ...) is not one broken axis, it
    # is several arm-blocks sharing one header row -- the CT-26 Dryad `.xls`
    # layout, one 5-day block per arm, blank cell as separator. Requiring the
    # WHOLE row to be monotonic threw the arm away instead of the separator.
    # Splitting on every non-increasing step and grading each run on its own
    # recovers exactly the run the reset produced, with no change for a sheet
    # that was never split (one run, identical to the old single check).
    for hi in range(min(8, len(rows))):
        hdr = rows[hi]
        # WIDTH CAP. A transposed sheet with hundreds of ORIGINAL rows (e.g.
        # an RNAseq matrix, one row per gene) produces a header candidate
        # hundreds of columns wide -- and a run of 4 coincidentally-increasing
        # real numbers is common, not rare, somewhere in hundreds of cells.
        # No genuine day axis in this corpus runs anywhere near that wide.
        if len(hdr) > 260:
            continue
        days_all = [(j, _hdr_num(c)) for j, c in enumerate(hdr)]
        days_all = [(j, d) for j, d in days_all if d is not None and 0 <= d <= 400]
        if len(days_all) < MIN_POINTS:
            continue
        runs, cur = [], [days_all[0]]
        for prev, nxt in zip(days_all, days_all[1:]):
            if nxt[1] > prev[1]:
                cur.append(nxt)
            else:
                runs.append(cur)
                cur = [nxt]
        runs.append(cur)

        for days in runs:
            if len(days) < MIN_POINTS:
                continue
            ds = [d for _, d in days]
            if ds[0] > 60 or ds[-1] - ds[0] < 3:             # (i) sane span
                continue
            # NOT-ONE-JUMP. A real day axis, even an irregular one (dense
            # early measurements, sparse follow-up), spreads its growth
            # across more than one step. `id, length, width, volume` read as
            # one row is also, by construction, a short increasing run (id a
            # small int, volume the largest number) -- but essentially ALL of
            # its span sits in the single last step, because those are four
            # unrelated quantities, not four measurements of the same one.
            # Splitting a row into runs made this collision reachable where a
            # whole-row check never was; a plain step-ratio bound rejected it
            # but also rejected `thsd7b`'s genuine dense-then-sparse axis, so
            # this checks jump CONCENTRATION instead of jump SIZE.
            steps = [b - a for a, b in zip(ds, ds[1:])]
            if max(steps) > 0.85 * (ds[-1] - ds[0]):
                continue
            if (not RESPONSE["allow_fractional_axis"]
                    and sum(1 for d in ds if 0 < d < 1) > 1):
                # More than one fractional step means a concentration axis read
                # as a time course -- fatal for a time profile, and exactly what
                # a dose profile is looking for. The profile decides.
                continue
            cols = [j for j, _ in days]
            n_an, consistent, folds, grids = 0, 0, [], []
            below = 0          # rows with SOME data but under the points floor
            for r in rows[hi + 1:]:
                lab = " ".join(str(c) for c in r[:2] if c is not None)
                if AGG.search(lab):
                    continue
                # Day kept beside its value, so a row with holes in it yields
                # ITS OWN grid rather than the header's -- same filtering and
                # same order as the previous `vals`-only form.
                pairs = [(ds[k], _num(r[j])) for k, j in enumerate(cols)
                         if j < len(r)]
                pairs = [(d, v) for d, v in pairs if v is not None and v > 0]
                vals = [v for _, v in pairs]
                if len(vals) < MIN_POINTS:
                    # A row with no numeric cell at all is not a subject; a row
                    # with one to three is a subject the floor dropped, and only
                    # the second is worth reporting.
                    below += 1 if vals else 0
                    continue
                n_an += 1
                grids.append([d for d, _ in pairs])
                if RESPONSE["direction"] == "increase":
                    consistent += vals[-1] > vals[0]
                elif RESPONSE["direction"] == "decrease":
                    consistent += vals[-1] < vals[0]
                else:                       # stable: no direction required
                    consistent += 1
                folds.append(vals[-1] / vals[0] if vals[0] > 0 else 0.0)
            if n_an < MIN_ANIMALS:
                continue
            folds.sort()
            med_fold = folds[len(folds) // 2] if folds else 0.0
            if consistent / float(n_an) < RESPONSE["min_consistent"]:
                continue                    # not moving the declared way
            if med_fold < RESPONSE["fold_lo"]:
                continue                    # too small a change to be real
            if RESPONSE["fold_hi"] and med_fold > RESPONSE["fold_hi"]:
                continue                    # too big for the declared response
            return ("wide", n_an, len(days), f"fold={med_fold:.1f}", grids,
                    below)

    # ---- WIDE-IDX: an ID column plus a run of VOLUME-like columns whose
    # headers carry a day INDEX suffix (`t_0`, `t_1`, ...) rather than a raw
    # day number -- the PDXNet "%dVol t_N" export convention. The real day
    # number is nowhere in the header; only the column's rank in the series
    # orders it, so this cannot reuse the numeric-header-cell path above.
    # `%DeltaVol` values can fall (a responder) or start at 0 by definition,
    # so growth check (ii) does not apply here -- the admissibility
    # rule already treats %change as a valid scale-invariant readout.
    for hi in range(min(6, len(rows))):
        hdr = [str(c) if c is not None else "" for c in rows[hi]]
        i_id = next((j for j, h in enumerate(hdr) if IDCOL_STRICT.match(h)),
                    None)
        idx_cols = [j for j, h in enumerate(hdr)
                    if VCOL.search(h) and DAYIDX.search(h)]
        if i_id is None or len(idx_cols) < MIN_POINTS:
            continue
        good, below = 0, 0
        for r in rows[hi + 1:]:
            if i_id >= len(r):
                continue
            lab = str(r[i_id])
            if AGG.search(lab):
                continue
            n_pts = sum(1 for j in idx_cols if j < len(r) and _num(r[j]) is not None)
            if n_pts >= MIN_POINTS:
                good += 1
            elif n_pts:
                below += 1
        if good >= MIN_ANIMALS:
            return ("wide-idx", good, len(idx_cols), "", None, below)
    return None


def _transpose(rows):
    if not rows:
        return []
    w = max(len(r) for r in rows)
    padded = [list(r) + [None] * (w - len(r)) for r in rows]
    return [list(c) for c in zip(*padded)]


# ---------------------------------------------------------------------------
# DISCIPLINE SIGNATURES: what a Source Data workbook holds BESIDES the curves
# ---------------------------------------------------------------------------
# Measured (V2): seven of nine false accepts were large numeric matrices from
# another discipline that fall into the `wide` path because they carry a
# monotonic ordinal axis. They are not edge cases and they are not subtle --
# they carry literal vocabulary. Declared in docs/VALIDATION.md BEFORE being
# written, with the predictions and the price they were allowed to cost.
#
# These REJECT. They are the mirror of AGG and carry the same danger: a
# rejection rule tuned against the false positives that inspired it is rule 9
# wearing the opposite sign. Any change here is re-measured over the whole
# labelled set, never against the item it missed.
SIGNATURES = [
    ("transcriptomics", re.compile(
        r"ENSMUSG|ENSG0|ENSRNO|log2\s*fold\s*change|\bpadj\b|basemean", re.I)),
    ("blot densitometry", re.compile(
        r"\b(gapdh|beta[- ]?actin|alpha[- ]?tubulin|vinculin)\b|/\s*gapdh", re.I)),
    ("distribution columns", re.compile(
        r"\bq1\b.*\bq3\b|\bq3\b.*\bq1\b|\b(mean|sd|sem)_[a-z]|[a-z]_(sd|sem)\b", re.I)),
    ("survival", re.compile(
        r"days\s*elapsed|time\s*to\s*event|\bcensor|\bsurvival\b", re.I)),
    ("imaging quantification", re.compile(
        r"colocali|fluorescence\s*intensity|mean\s*gray", re.I)),
]


def geometric_axis(ds, tol=0.10, min_ratio=1.8):
    """-> True if `ds` is a dilution series rather than a calendar.
    
    Successive ratios within `tol` of one constant >= `min_ratio`. A doubling
    or ten-fold dilution ladder is geometric; a day grid is not, and the one
    IC50 plate this scanner is known to false-accept reads 2, 1, 0.5, 0.25.
    """
    vals = [d for d in ds if d and d > 0]
    if len(vals) < 4:
        return False
    vals = sorted(vals)
    ratios = [b / a for a, b in zip(vals, vals[1:]) if a > 0]
    if not ratios or min(ratios) < min_ratio:
        return False
    mid = sorted(ratios)[len(ratios) // 2]
    return all(abs(r - mid) <= tol * mid for r in ratios)


def index_axis(ds):
    """-> True if `ds` is 1, 2, 3, ... -- a row number, not a calendar.

    An endpoint table with one measurement per animal transposes into what
    looks like a time series whose axis is the animal INDEX. Measured: 0 of 15
    positive fixtures carry such an axis, and it catches 1 of the 9 V2 false
    accepts.

    THAT ZERO IS NOT AS STRONG AS IT LOOKS. The rule was derived from looking
    at V2's failures and then measured on V2, which is the set that inspired
    it. A free catch on the items that suggested the rule is not evidence that
    it is free anywhere else, which is why this labels rather than rejects.
    """
    ds = [d for d in ds if d is not None]
    if len(ds) < 3:
        return False
    return (abs(ds[0] - 1.0) < 1e-9
            and all(abs((b - a) - 1.0) < 1e-9 for a, b in zip(ds, ds[1:])))


# V14. Fixed before measuring; see docs/VALIDATION.md. Deliberately NOT here:
# bare `patient` (patient-derived xenograft) and bare `donor` (CAR-T donors).
HUMAN = re.compile(
    r"\bvolunteer|\bparticipant|\bpatient[_ ]?id\b|clinicopathologic"
    r"|\bTCGA\b|\bgender\b|age at diagnosis|informed consent"
    r"|\u59d3\u540d|\u6027\u522b|\u5e74\u9f84|\u60a3\u8005", re.I)


def discipline_signature(rows, window=8):
    """-> the name of the signature this sheet carries, or None."""
    cells = [str(c) for r in rows[:window] if r for c in r if c is not None]
    if not cells:
        return None
    txt = " ".join(cells)
    v = judge_any(rows)
    if v and v[4] and index_axis([x for x in v[4][0] if x is not None]):
        return "index axis (1,2,3... is a row number, not a calendar)"
    # AGG IN THE HEADER REGION, REPORTED AND NOT ENFORCED (V11).
    # `AGG` is applied to ROW LABELS only, so a sheet whose `Mean`/`SEM`
    # columns are NAMED IN A HEADER ROW -- which is how group-level data is
    # normally laid out -- never reaches the one rule this scanner rests on.
    # 304 of 2,696 accepted sheets carry the vocabulary up here.
    #
    # It does NOT reject, for V5's reason and with V5's evidence: a sample of
    # the 304 found 7 of 8 correctly caught and ONE GENUINE per-animal series
    # (`PMC13102701` `11E`, one column per animal, 1 -> 35.9 over days). A rule
    # that is right seven times in eight still costs real recall, so it sinks
    # the sheet in the worklist instead of dropping it -- the same resolution
    # V5 reached for the discipline signatures, for the same reason.
    if AGG.search(txt):
        return "aggregate vocabulary in the header region (mean/SEM/n=)"
    # INDIVIDUAL HUMAN DATA, REPORTED AND NOT ENFORCED (V14).
    # Protocol rule 12 puts it out of scope and nothing enforced that: V10
    # measured 2 of 20 accepted papers as human -- a clinicopathological cohort
    # table and a set of patient records carrying name, sex, age and
    # brachytherapy dosimetry.
    #
    # It LABELS rather than rejects because `patient` cannot be a rejection
    # token: patient-derived xenograft is the commonest phrase in this
    # literature and a PDX study is animal data. Bare `donor` is out for the
    # same reason -- CAR-T papers name human donors for cells grown in mice.
    # So the vocabulary demands an unambiguous marker, and the CJK terms are
    # present because one known case is a Chinese-language sheet and an
    # English-only rule would miss it while appearing to work.
    if HUMAN.search(txt):
        return "individual human data (out of scope, protocol rule 12)"
    for name, pat in SIGNATURES:
        if pat.search(txt):
            if name == "imaging quantification" and any(
                    TCOL.match(c) for c in cells):
                continue          # a real timecourse of an imaging readout
            return name
    return None


def header_evidence(rows, window=8):
    """-> a string naming which profile patterns the sheet's headers support.
    
    `judge`'s `wide` path decides on STRUCTURE alone -- an ascending numeric
    axis, a growth fraction, a fold change -- and never consults the profile.
    Measured: swapping the profile changes 3 accepted sheets out of 115, and
    all 3 are flat long-format text, where the `long` path DOES consult it.
    
    So on a spreadsheet the profile was buying nothing and the README was
    promising otherwise. This does not change that decision -- it RECORDS what
    the headers actually supported, so an accept made on structure alone is
    visibly an accept made on structure alone.
    
    Letters: i = a subject-id column, t = the ordered covariate, v = the value.
    An empty string means the sheet matched NO profile pattern and was taken on
    shape alone. That is not a rejection; it is the thing a reader needs to see
    before trusting it, and it is what the IC50 false accept looks like.
    """
    cells = [str(c) for r in rows[:window] if r
             for c in r if c is not None]
    ev = ""
    if any(IDCOL_STRICT.match(c) for c in cells):
        ev += "i"
    if any(TCOL.match(c) for c in cells):
        ev += "t"
    if any(VCOL.search(c) for c in cells):
        ev += "v"
    return ev


def judge_any(rows):
    """`judge` on the sheet AND on its transpose, because the time axis is as
    often a column as a header row."""
    ev = header_evidence(rows)
    v = judge(rows)
    if v:
        return v + (ev,)
    v = judge(_transpose(rows))
    if v:
        return (v[0] + "-T",) + v[1:] + (ev,)
    return None


def scan(pmcid):
    p = fetch(pmcid)
    if p.startswith("ERR"):
        return [(pmcid, "", "", "", 0, 0, p)]
    out = []
    size_skipped = []
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        return [(pmcid, "", "", "", 0, 0, f"ERR badzip {e}")]
    for info in z.infolist():
        nm = info.filename
        if not re.search(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", nm, re.I):
            continue
        if info.file_size > 40 * 1024 * 1024:
            # UNMEASURED IS NOT NEGATIVE (V16, and V1 before it).
            # This was a bare `continue`, so a paper whose only tabular member
            # was oversized came back "no per-animal table found" -- a claim
            # about a file nobody opened. `mine.py` already reported its skips;
            # this CLI did not. Measured over 2,390 cached papers: 19 carry a
            # size-skipped member and in 8 it was the ONLY tabular one.
            size_skipped.append((os.path.basename(nm), info.file_size))
            continue
        try:
            blob = z.read(info)
        except Exception:
            continue
        for sheet, rows in sheets_from(nm, blob):
            v = judge_any(rows)
            if v:
                # SLICE, DO NOT UNPACK. This read `layout, na, npt, note = v`
                # and had been raising ValueError on every accepted sheet since
                # `hdr` was appended -- the commit that added it
                # said "no positional unpacking downstream moves", and moved
                # this one. `mine.py` has its own loop and the gate calls
                # `judge_any` directly, so nothing exercised this path.
                layout, na, npt, note = v[:4]
                out.append((pmcid, os.path.basename(nm), sheet, layout,
                            na, npt, "CANDIDATE"))
    if not out:
        if size_skipped:
            # Never say "no table" about bytes that were never read.
            out = [(pmcid, "", "", "", 0, 0,
                    "NOT JUDGED: %d tabular member(s) over 40 MB were skipped "
                    "unread (%s). This paper was NOT rejected -- it was never "
                    "read." % (len(size_skipped),
                               ", ".join("%s %.0f MB" % (n, s / 1e6)
                                         for n, s in size_skipped)))]
        else:
            out = [(pmcid, "", "", "", 0, 0, "no per-animal table found")]
    elif size_skipped:
        out.append((pmcid, "", "", "", 0, 0,
                    "PARTIAL: %d member(s) over 40 MB skipped unread (%s); the "
                    "rows above are what the readable members held"
                    % (len(size_skipped),
                       ", ".join("%s %.0f MB" % (n, s / 1e6)
                                 for n, s in size_skipped))))
    return out


def main(ids=None):
    ids = sys.argv[1:] if ids is None else ids
    if not ids:
        print("usage: unpool scan PMCID [PMCID ...]")
        return 2
    rows = []
    for i, pid in enumerate(ids, 1):
        r = scan(pid)
        rows.extend(r)
        best = max((x[4] for x in r), default=0)
        tag = "HIT" if any(x[6] == "CANDIDATE" for x in r) else "--"
        print(f"  [{i:>2}/{len(ids)}] {pid:11s} {tag:3s} "
              f"best n_animals={best:<4} {r[0][6] if tag == '--' else ''}")
        sys.stdout.flush()
        time.sleep(0.3)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["pmcid", "file", "sheet", "layout", "n_animals",
                    "n_timepoints", "verdict"])
        w.writerows(rows)
    hits = sorted({r[0] for r in rows if r[6] == "CANDIDATE"})
    print(f"\n  {len(hits)} of {len(ids)} papers carry a per-animal table")
    print(f"  artifact: {OUT}")
    for h in hits:
        for r in rows:
            if r[0] == h and r[6] == "CANDIDATE":
                print(f"    {r[0]:11s} {r[4]:>4} animals x {r[5]:>3} pts  "
                      f"[{r[3]}]  {r[1][:44]} :: {str(r[2])[:26]}")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
