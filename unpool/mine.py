"""the freeze rule (protocol rule 2) acquisition path: search one tumour-model LINE on Europe PMC, triage
every paper's supplementary with `scan`, and apply the three screens the
brief inherits -- the animal floor, the freeze rule's CALENDAR screen, and the re-export check's
three-axis re-export check -- to whatever the scanner accepts.

    unpool mine LLC --budget 300

PROVENANCE AND STATUS
------------------------------------------------------------------------------
Mining hits live Europe PMC APIs against a paper budget and is not
reproducible. the freeze rule (protocol rule 2) records
that as a cost it does not pay for -- *"the acquisition path must be rebuilt
before it can run"* -- and this is that rebuild.

It is still not reproducible, and that is not fixed here: the Europe PMC index
grows, so the same query returns a different `hitCount` every month (`4T1` went
from 10,778 hits to 13,549 in a few months). What IS reproducible is the RECORD:
the scan order is frozen to disk before a single supplementary file is fetched,
and the run header carries the query, the sort, the budget and the counted unit.
Re-running this script does not reproduce a batch; reading its artifacts does.

THE THREE RULES the freeze rule (protocol rule 2) IMPOSES ON WHATEVER SUCCEEDS `mine.py`
------------------------------------------------------------------------------
1. **Precision and recall together or neither.** This script reports NEITHER of
   its own and says so in its own output. Recall is
   `tests/test_recall.py`'s 15/15 on the tuning set; precision on
   accepts is 6 of 15, on an unbiased sample whose seed was registered
   before any sheet was opened (`docs/VALIDATION.md`, V2). Both are printed
   in the footer of every run so no batch of this script's can be quoted
   without them.
2. **Freeze the scan order and the candidate list before any candidate is
   opened.** `_freeze_order()` writes the full ID list and the run header to
   `tests/` and `fsync`s them BEFORE the first `fetch()`. A candidate list
   assembled after the fact is a list chosen with its answer in view.
3. **Record which unit was counted in the same place as the count.** Every
   artifact this script writes carries `unit_counted=scanner_acceptances`.
   **That is NOT `STOP_AT_CELLS`'s unit.** the stop rule settled `STOP_AT_CELLS = 10`
   on *verified cells*, and this script cannot verify anything -- verification
   is a builder reading a sheet animal by animal. So this script's ONLY stop is
   the paper budget (rule 3 of the freeze rule's stop list), it never decrements a cell
   budget, and a reader who wants the cell count has to go to the builders.

THE SCREENS, IN THE ORDER THEY RUN
------------------------------------------------------------------------------
* **The animal floor** is `scan`'s own (`MIN_ANIMALS = 5` at
  `MIN_POINTS = 4`), which is the subject-floor rule's `MIN_ANIMALS_ESTIMATION` and
  `MIN_POINTS_PER_ANIMAL`. Nothing below it reaches the screens below.
* **The calendar screen is the freeze rule's, and no previous mining pass applied it.**
  A candidate is admissible only if the model's per-model window -- recomputed
  over the model's arms INCLUDING the candidate, per the per-model window rule, from day grids
  alone and before any `r_eff` -- is non-empty and leaves `>= 5` animals
  retained in every surviving arm. the one-arm drop rule's ONE-arm drop is applied when the
  window comes out empty, with `MIN_ARMS_PER_MODEL = 2` remaining and the drop
  chosen to maximise surviving window length, ties by source name ascending.
  A candidate that is itself the arm the drop rule removes is refused: it would
  buy nothing.
* **The re-export check is the three re-export axes (protocol rule 7).** Axis 1 (DOI /
  accession) and axis 2 (author over `A1 u A2`) run here, mechanically, against
  `corpus_source_registry.csv`. Axis 3 (the identical-curve fingerprint)
  does NOT run here and cannot: it needs the candidate's actual curves, which
  only a builder reading the sheet has. A hit on axis 1 or 2 is a `FLAGGED`
  verdict -- **a stop with a written reason, not a silent drop** -- and the re-export check's
  remedy is unchanged: it is explained in the builder's docstring or the
  ingestion does not happen.

WHAT THIS SCRIPT DOES NOT DO
------------------------------------------------------------------------------
It does not verify, it does not ingest, it does not write a builder, it does not
count cells, and a `CANDIDATE` verdict from it is worth exactly what the V2
sample's fifteen were worth: 6 of 15.
"""
import argparse
import concurrent.futures
import csv
import datetime
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile

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

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ROOT = _HERE          # the clone's root: runs/, si_cache/ and profiles/ live there
from unpool import scan as S  # the triage instrument, reused not rewritten

OUTDIR = os.environ.get("UNPOOL_OUT") or os.path.join(_ROOT, "runs")

# THE TWO OPTIONAL INPUTS, AND WHY THEY ARE OPTIONAL RATHER THAN REMOVED
# ---------------------------------------------------------------------------
# Both screens below were written against one project's own corpus and source
# registry. Neither generalises as a PATH, but both generalise as a QUESTION,
# so the logic stays and the coupling goes:
#
#   PRIOR_ARMS  -- files of already-held arms, for the calendar screen: does
#                  this candidate leave a non-empty measurement window with
#                  enough subjects retained in every surviving arm? Nobody
#                  else has our corpus; everybody who has mined twice has a
#                  set of prior arms.
#   REGISTRY    -- known sources with their DOIs, for the re-export check's
#                  axes 1 and 2 (shared deposit, shared author).
#
# Supplied, the screen runs. Absent, the screen is REPORTED AS NOT RUN in
# every artifact rather than quietly skipped -- a candidate that passed no
# calendar screen must not read as one that passed it.
PRIOR_ARMS = [p for p in (os.environ.get("UNPOOL_PRIOR_ARMS") or "").split(os.pathsep) if p]
# NOT `registry.csv`: that name is the verified-data registry
# (studies/build_registry.py), a different schema. Sharing the default made
# every real `mine` run die on KeyError: a2_enumerated.
REGISTRY = os.environ.get("UNPOOL_REGISTRY") or os.path.join(_ROOT, "source_registry.csv")

SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
SORT = "P_PDATE_D desc"          # newest first

# Not one of these is a new number. See the module docstring for whose they are.
MIN_ANIMALS_PER_ARM = 5          # the subject floor MIN_ANIMALS_ESTIMATION
MIN_POINTS_PER_ANIMAL = 4        # the subject floor's points
MIN_ARMS_PER_MODEL = 2           # the one-arm drop rule
UNIT_COUNTED = "scanner_acceptances"   # NOT verified cells -- see rule 3

# The measured figures that must travel with any batch this script produces.
RECALL_NOTE = ("15/15 on the cached publisher fixtures (tests/test_recall.py) -- "
               "a TUNING-SET figure, re-tuned against those files twice, not a score")
# The floors are part of this figure, not context for it: the sample was drawn
# under `min_subjects=5` and the default is now 4 (V9). Every run record states
# the floors it ran under beside this note, so the two can never drift apart
# again without it being visible in the artifact.
PRECISION_NOTE = ("8 of 20 accepts verified TRUE at min_subjects=4/min_points=4 "
                  "-- unbiased sample, seed registered before any sheet was "
                  "opened (docs/VALIDATION.md V10, corrected by V17), 95% interval "
                  "roughly 19-61%. An earlier 6 of 15 was measured at min_subjects=5 "
                  "over a different population; do not pool them. The floors "
                  "this run used are in the `floors` key of this record")

# The line queries. A line's query is the MODEL'S NAMES and nothing else: the
# one filter this line ever added quietly (`SRC:PMC`) cut 22,267 hits to 350
# and turned a broken search into a null result, so a narrowing clause whose
# recall nobody measured does not go in here. `LLC` is the exception that
# proves the rule -- bare `"LLC"` returns 259,750 hits because it is also
# "limited liability company", so the line is searched under the model's
# actual names instead. That is a DISAMBIGUATION, not a narrowing, and it is
# written down here rather than left in a shell history.
LINE_QUERIES = {
    "4T1": '"4T1"',
    "LLC": '("Lewis lung carcinoma" OR "LLC1" OR "LL/2")',
    "HCC1569": '"HCC1569"',
    "YUMM1.7": '("YUMM1.7" OR "YUMM 1.7")',
    "A549": '"A549"',
}
BASE_CLAUSES = "HAS_FT:Y AND HAS_SUPPL:Y"

# WHERE YOU LOOK BEATS EVERYTHING ELSE THIS SCRIPT DOES.
# Measured on unselected 50-paper samples, same query, same scanner:
#
#     Nature Communications   90% have a tabular supplement, 80% accepted
#     Nature portfolio wider  66%                            34%
#     PLOS ONE                28%                            12%
#     general population      10%                             0%
#
# Journals with a Source Data policy publish spreadsheets; the rest publish
# PDFs. No improvement to the scanner closes a gap that size, so the cheapest
# real gain available here is `--journal`.
# The per-member size cap. Files above it are NAMED as skipped, never silently
# turned into a content verdict. Raising it costs memory and time on workbooks
# that are mostly embedded images; lowering it loses data. It is a real
# trade-off and it belongs where a reader can see it.
MAX_MEMBER = 40 * 1024 * 1024

SUGGESTED_JOURNALS = ["Nature Communications", "Cell Death and Disease",
                      "Signal Transduction and Targeted Therapy", "PLoS One"]


class MineRefused(SystemExit):
    """The line, the corpus or the registry is not what the freeze rule (protocol rule 2) registered."""


# =============================================================================
# EUROPE PMC
# =============================================================================

def _get(url):
    req = urllib.request.Request(url, headers=S.UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def search(query, budget, offset=0):
    """-> (hit_count, [record, ...]) -- `offset` skipped, then `budget` taken.

    THE OFFSET IS PART OF THE FROZEN RECORD, not a convenience. A second
    campaign on the same query and sort returns the same papers as the first:
    without an offset a budget of 50 re-mines what has already been mined and
    reports it as new. The offset says which slice of the frozen order this run
    took, so two runs can be read together instead of silently overlapping.
    """
    out, cursor, total = [], "*", None
    while len(out) < budget + offset:
        url = (f"{SEARCH}?query={urllib.parse.quote(query)}&format=json"
               f"&pageSize=100&cursorMark={urllib.parse.quote(cursor)}"
               f"&sort={urllib.parse.quote(SORT)}&resultType=core")
        page = _get(url)
        total = page.get("hitCount") if total is None else total
        results = page.get("resultList", {}).get("result", [])
        if not results:
            break
        for r in results:
            pmcid = r.get("pmcid")
            if not pmcid:
                continue
            out.append({
                "id": pmcid,
                "doi": r.get("doi", "") or "",
                "authorString": r.get("authorString", "") or "",
                "title": (r.get("title", "") or "").replace("\n", " "),
                "journal": (r.get("journalInfo", {}) or {})
                           .get("journal", {}).get("title", "") or "",
                "year": r.get("pubYear", "") or "",
            })
            if len(out) >= budget + offset:
                break
        nxt = page.get("nextCursorMark")
        if not nxt or nxt == cursor:
            break
        cursor = nxt
        time.sleep(0.2)
    return total or 0, out[offset:offset + budget]


def authors_for_doi(doi, cache):
    """A1/A2 author tokens for one DOI, via Europe PMC. `None` when the DOI is
    a deposit (Zenodo/Dryad) that the literature index does not hold -- which
    is NOT the same as an empty author set and must not be compared as one."""
    if doi in cache:
        return cache[doi]
    try:
        page = _get(f"{SEARCH}?query=DOI:%22{urllib.parse.quote(doi)}%22"
                    f"&format=json&pageSize=1&resultType=core")
        res = page.get("resultList", {}).get("result", [])
        cache[doi] = author_tokens(res[0].get("authorString", "")) if res else None
    except Exception:
        cache[doi] = None
    time.sleep(0.2)
    return cache[doi]


def author_tokens(author_string):
    """'Huang Y, Zhao Y, Su Y.' -> {'huang y', 'zhao y', 'su y'}.

    Surname plus first initial, which is the matching the check already uses.
    An author with no initial keeps the bare surname, so it still collides."""
    toks = set()
    for part in re.split(r"[,;]", author_string or ""):
        part = part.strip().rstrip(".")
        if not part:
            continue
        bits = part.split()
        if not bits:
            continue
        surname = bits[0].lower()
        initial = bits[1][0].lower() if len(bits) > 1 and bits[1][:1].isalpha() else ""
        toks.add(f"{surname} {initial}".strip())
    return toks


# =============================================================================
# THE HELD CORPUS -- DAY GRIDS ONLY, NO `r_eff` ANYWHERE ABOVE THIS
# =============================================================================

def held_arms(model, paths=None):
    """{source -> [per-animal day list, ...]} for one model, from the same two
    files `tests/study_sigma_dispersion.py` combines, at the same
    `(model, source)` study unit, under the same two floors."""
    per = {}
    paths = PRIOR_ARMS if paths is None else paths
    if not paths:
        return per          # -> calendar_screen reports NOT RUN, not "passed"
    for path in paths:
        if not os.path.exists(path):
            raise MineRefused(f"prior-arms file not found: {path}")
        with open(path, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh, delimiter=";"):
                if row.get("model") != model:
                    continue
                key = (row["source"], row["animal_id"])
                try:
                    per.setdefault(key, []).append(float(row["days"]))
                except (TypeError, ValueError):
                    continue
    arms = {}
    for (source, _aid), days in per.items():
        if len(days) >= MIN_POINTS_PER_ANIMAL:
            arms.setdefault(source, []).append(sorted(days))
    return {s: g for s, g in arms.items() if len(g) >= MIN_ANIMALS_PER_ARM}


# =============================================================================
# THE CALENDAR SCREEN -- the freeze rule (protocol rule 2), WITH the one-arm drop rule's ONE-ARM DROP
# =============================================================================

def model_window(arms):
    """the per-model window rule: `[max first day, min last day]` over a model's arms, or None."""
    if not arms:
        return None
    firsts = [min(min(g) for g in grids) for grids in arms.values()]
    lasts = [max(max(g) for g in grids) for grids in arms.values()]
    lo, hi = max(firsts), min(lasts)
    return None if hi <= lo else (lo, hi)


def retained(grids, win):
    """Animals of one arm still carrying `MIN_POINTS_PER_ANIMAL` inside `win`."""
    return sum(1 for g in grids
               if sum(1 for d in g if win[0] <= d <= win[1])
               >= MIN_POINTS_PER_ANIMAL)


def calendar_screen(held, cand_name, cand_grids):
    """-> (admitted: bool, reason: str, window, dropped_arm or None).

    The window is recomputed over the model's arms INCLUDING the candidate --
    not against the window as it stands today, which is the clause the freeze rule (protocol rule 2)
    spells out because the other reading is the one that looks natural."""
    if not held:
        return (True, "calendar screen NOT RUN: no prior arms supplied "
                      "(set UNPOOL_PRIOR_ARMS). This candidate has NOT been "
                      "screened for window compatibility.", None, None)
    if cand_grids is None:
        return (False, "calendar unknown: wide-idx sheet carries a day INDEX, "
                       "not day numbers", None, None)
    arms = dict(held)
    arms[cand_name] = cand_grids
    win, dropped = model_window(arms), None

    if win is None and len(arms) - 1 >= MIN_ARMS_PER_MODEL:
        best = None
        for name in sorted(arms):           # ties broken by source name asc
            trial = {k: v for k, v in arms.items() if k != name}
            w = model_window(trial)
            if w is not None and (best is None or (w[1] - w[0]) > best[1]):
                best = (name, w[1] - w[0], w)
        if best is not None:
            dropped, win = best[0], best[2]

    if win is None:
        return (False, "window empty and one drop does not suffice "
                       "(the one-arm drop rule); the model would leave the population",
                None, None)
    if dropped == cand_name:
        return (False, "the candidate IS the arm the one-arm drop rule's drop removes -- "
                       "admitting it buys nothing", win, dropped)
    for name, grids in arms.items():
        if name == dropped:
            continue
        n = retained(grids, win)
        if n < MIN_ANIMALS_PER_ARM:
            return (False, f"arm {name!r} retains {n} animals inside "
                           f"[{win[0]:g}, {win[1]:g}], below "
                           f"{MIN_ANIMALS_PER_ARM}", win, dropped)
    return (True, "", win, dropped)


# =============================================================================
# THE RE-EXPORT CHECK -- the re-export check (protocol rule 7) AXES 1 AND 2. AXIS 3 IS THE BUILDER'S.
# =============================================================================

def load_registry():
    """-> rows, or [] when no registry is supplied.

    An empty registry means axes 1 and 2 of the re-export check CANNOT RUN.
    That is reported by the caller, never rendered as a clean pass."""
    if not os.path.exists(REGISTRY):
        return []
    with open(REGISTRY, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def reexport_check(cand, registry, cache):
    """-> list of human-readable collision strings; empty means no hit."""
    hits = []
    cand_doi = (cand["doi"] or "").lower()
    cand_auth = author_tokens(cand["authorString"])
    for row in registry:
        dois = [d.strip() for d in (row["dois"] or "").split("|") if d.strip()]
        if cand_doi and any(cand_doi == d.lower() for d in dois):
            hits.append(f"AXIS1 doi == {row['source']}")
            continue
        known = set()
        for d in dois:
            got = authors_for_doi(d, cache)
            if got:
                known |= got
        shared = cand_auth & known
        if shared:
            hits.append(f"AXIS2 authors {sorted(shared)} shared with "
                        f"{row['source']}")
    return hits


# =============================================================================
# THE FROZEN RECORD -- WRITTEN BEFORE THE FIRST `fetch()`
# =============================================================================

def _ensure_outdir():
    os.makedirs(OUTDIR, exist_ok=True)
    return OUTDIR


def _slug(text, fallback="run"):
    """A filesystem-safe tag. A raw query is not a filename."""
    out = "".join(c if (c.isalnum() or c in "-_") else "_" for c in text.lower())
    out = "_".join(x for x in out.split("_") if x)[:40]
    return out or fallback


def _freeze_order(line, query, budget, hit_count, records):
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tag = _slug(line)
    _ensure_outdir()
    head = os.path.join(OUTDIR, f"{tag}_run.json")
    order = os.path.join(OUTDIR, f"{tag}_scan_order.csv")
    with open(head, "w", encoding="utf-8") as fh:
        json.dump({
            "line": line, "query": query, "base_clauses": BASE_CLAUSES,
            "sort": SORT, "paper_budget": budget, "hit_count": hit_count,
            "frozen_at": now, "unit_counted": UNIT_COUNTED,
            "stop_rule": "paper budget only; STOP_AT_CELLS=10 counts VERIFIED "
                         "cells (the stop rule) and is not this script's to spend",
            "scanner_recall": RECALL_NOTE, "scanner_precision": PRECISION_NOTE,
            # THE VERDICTS ARE ONLY MEANINGFUL AGAINST THESE.
            # `load_profile`'s docstring has always said every artifact must
            # name the profile it ran under, and no artifact did. The floors
            # matter for the same reason and more sharply: BOTH headline
            # figures above were measured at the floors in force when they were
            # taken, so a record that omits them cannot say whether they apply.
            "profile": S.PROFILE["name"],
            "floors": {"min_subjects": S.MIN_ANIMALS,
                       "min_points": S.MIN_POINTS},
        }, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())
    with open(order, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["line", "source", "id", "doi", "year", "frozen_at",
                    "unit_counted"])
        for r in records:
            w.writerow([line, "pmc", r["id"], r["doi"], r["year"], now,
                        UNIT_COUNTED])
        fh.flush()
        os.fsync(fh.fileno())
    return head, order


def scan_one(pmcid):
    """si_scan's own parsing, kept whole, with the day GRIDS retained."""
    p = S.fetch(pmcid)
    if p.startswith("ERR"):
        return [], p
    try:
        z = zipfile.ZipFile(p)
    except Exception as e:
        return [], f"ERR badzip {e}"
    accepts, skipped = [], []
    for info in z.infolist():
        if not re.search(r"\.(xlsx|xlsm|xls|csv|tsv|txt)$", info.filename, re.I):
            continue
        if info.file_size > MAX_MEMBER:
            # A SIZE REFUSAL IS NOT A CONTENT VERDICT (protocol rule 10).
            # This used to `continue` in silence, and the paper was then
            # reported as "no per-animal table found" -- a statement about what
            # the file contains, made without opening it. Measured on the first
            # campaign: 4 of 50 papers, and ALL FOUR were rejected on that
            # basis. One of them holds 10 accepting sheets inside the file that
            # was never read.
            skipped.append((os.path.basename(info.filename),
                            info.file_size / 1048576.0))
            continue
        try:
            blob = z.read(info)
        except Exception:
            continue
        for sheet, rows in S.sheets_from(info.filename, blob):
            v = S.judge_any(rows)
            if v:
                layout, n_an, n_pt, note, grids, below, ev = v
                sig = S.discipline_signature(rows) or ""
                accepts.append({
                    "file": os.path.basename(info.filename), "sheet": sheet,
                    "layout": layout, "n_animals": n_an, "n_points": n_pt,
                    "header_evidence": ev,
                    "n_below_floor": below,
                    "signature": sig,
                    "note": note, "grids": grids,
                })
    if skipped:
        note = "SKIPPED %d file(s) over %d MB, NOT JUDGED: %s" % (
            len(skipped), MAX_MEMBER // 1048576,
            ", ".join("%s (%.0f MB)" % t for t in skipped))
        if accepts:
            return accepts, note
        return [], note + " -- this paper was never read, it was not rejected"
    return accepts, "" if accepts else "no per-animal table found"


def main(argv=None):
    # A paper title is not ASCII and this script prints titles. The LLC batch
    # scanned all 300 papers, wrote its artifact, and THEN died printing a
    # U+2011 non-breaking hyphen to a cp1252 console -- a crash after the
    # evidence was safe, but one that would look like a failed batch to anyone
    # reading the exit code. The artifact is written before the summary for
    # exactly that reason; this keeps the summary from dying too.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("line")
    ap.add_argument("--profile", default=None,
                    help="data profile; see ls profiles/. Overrides "
                         "UNPOOL_PROFILE. Default tumor_volume, the only one "
                         "with a measured recall figure.")
    ap.add_argument("--offset", type=int, default=0,
                    help="skip this many results of the frozen order before "
                         "taking the budget. A second campaign on the same "
                         "query MUST use one or it re-mines the first.")
    ap.add_argument("--tag", default=None,
                    help="short name for this run's artifacts")
    ap.add_argument("--journal", default=None,
                    help='restrict to one journal, e.g. "Nature Communications". '
                         'Measured on 100 unselected papers per journal: 71%% '
                         'of that journal is accepted against 0%% of the '
                         'general population (studies/journal_yield.csv).')
    ap.add_argument("--budget", type=int, required=True,
                    help="papers fetched, declared before the run (the freeze rule (protocol rule 2) "
                         "stop 3).")
    ap.add_argument("--workers", type=int, default=4,
                    help="papers fetched and parsed at once (default 4). The "
                         "frozen order is kept in the output whatever this is; "
                         "1 reproduces the old one-at-a-time run.")
    ap.add_argument("--window", default="",
                    help="'lo..hi', the window a new arm must overlap. "
                         "Checked against the corpus's own; a mismatch is "
                         "refused rather than silently preferred.")
    a = ap.parse_args(argv)

    # A REGISTERED LINE, OR A RAW QUERY. Both are frozen identically before any
    # candidate is opened, which is the only property that matters -- the
    # registered names are a convenience, not a gate. A campaign that spans
    # models needs a query that is not one model's name.
    if a.profile:
        S.load_profile(a.profile)
    if a.line in LINE_QUERIES:
        query = f"{LINE_QUERIES[a.line]} AND {BASE_CLAUSES}"
    else:
        query = f"({a.line}) AND {BASE_CLAUSES}"
        print(f"  RAW QUERY (not a registered line): {a.line}")
    if a.journal:
        query = f'JOURNAL:"{a.journal}" AND {query}'
    else:
        print("  NO --journal GIVEN. Measured on 100 unselected papers per")
        print("  journal (studies/journal_yield.csv): 0% of the general")
        print("  population is accepted, against 71% of Nature Communications.")
        print("  Consider:")
        print("    %s" % ", ".join('--journal "%s"' % j for j in SUGGESTED_JOURNALS[:2]))
    held = held_arms(a.line)
    # NO PRIOR ARMS IS A FIRST RUN, NOT A REFUSAL.
    #
    # This used to raise. That was right when the tool only ever ran against
    # one project's existing corpus, and wrong for everyone else: the very
    # first pass on a new model has nothing held by definition, and refusing
    # it makes the tool unusable exactly once -- at the start.
    #
    # The screen is skipped and SAID TO BE SKIPPED, in the banner and in every
    # artifact. A candidate that was never screened for window compatibility
    # must not read like one that passed (protocol rule 11).
    win_today = model_window(held) if held else None
    if not held:
        print(f"  line {a.line}: NO PRIOR ARMS SUPPLIED.")
        print(f"  the calendar screen will NOT RUN -- every candidate below is")
        print(f"  unscreened for window compatibility, and its row says so.")
        print(f"  supply prior arms with UNPOOL_PRIOR_ARMS to enable it.")
    else:
        print(f"  line {a.line}: {len(held)} held arm(s) "
              f"{ {s: len(g) for s, g in held.items()} }")
        print(f"  window as it stands today: "
              f"{'EMPTY' if win_today is None else f'{win_today[0]:g}..{win_today[1]:g}'}")
    if a.window:
        lo, hi = (float(x) for x in a.window.split(".."))
        if win_today is None or abs(lo - win_today[0]) > 1e-9 or \
                abs(hi - win_today[1]) > 1e-9:
            raise MineRefused(
                f"declared window {a.window} does not match the corpus's own "
                f"{win_today}; one of the two is wrong and this run is not it")

    registry = load_registry()
    print(f"  registry: {len(registry)} accepted sources, "
          f"{sum(1 for r in registry if r['a2_enumerated'] == 'no')} whose A2 "
          f"is NOT enumerated (the re-export check (protocol rule 7): not refused, not cleared)")
    print(f"  query:  {query}\n  sort:   {SORT}\n  budget: {a.budget} papers "
          f"(unit counted below: {UNIT_COUNTED})")

    hit_count, records = search(query, a.budget, a.offset)
    head, order = _freeze_order(a.tag or a.line, query, a.budget,
                                hit_count, records)
    print(f"  {hit_count} hits; {len(records)} frozen to {order}")
    print(f"  run header: {head}\n")

    cache, rows, n_accept = {}, [], 0
    # Fetching is the slow part, so papers are fetched and parsed in parallel,
    # each worker pausing between requests as the sequential loop did. `map`
    # yields in the FROZEN order (rule 2), so the artifact, the printed log and
    # the re-export check below are identical to a one-at-a-time run.
    def _paced(pmcid):
        try:
            return scan_one(pmcid)
        finally:
            time.sleep(0.3)

    pool = concurrent.futures.ThreadPoolExecutor(max(1, a.workers))
    results = pool.map(_paced, [rec["id"] for rec in records])
    try:
        for i, (rec, (accepts, err)) in enumerate(zip(records, results), 1):
            if not accepts:
                rows.append({**rec, "file": "", "sheet": "", "layout": "",
                             "n_animals": 0, "n_points": 0, "header_evidence": "", "window": "",
                             "dropped_arm": "", "verdict": err or "no hit",
                             "reason": ""})
                print(f"  [{i:>3}/{len(records)}] {rec['id']:11s} --  {err}",
                      flush=True)
                sys.stdout.flush()
                continue
            n_accept += 1
            collisions = reexport_check(rec, registry, cache)
            for acc in accepts:
                ok, why, win, dropped = calendar_screen(
                    held, f"CANDIDATE:{rec['id']}", acc["grids"])
                if collisions:
                    verdict, reason = "FLAGGED", "; ".join(collisions)
                elif ok:
                    verdict, reason = "CANDIDATE", acc["note"]
                else:
                    verdict, reason = "REFUSED_CALENDAR", why
                rows.append({
                    **rec, "file": acc["file"], "sheet": acc["sheet"],
                    "layout": acc["layout"], "n_animals": acc["n_animals"],
                    "header_evidence": acc.get("header_evidence", ""),
                    "n_points": acc["n_points"],
                    "window": "" if win is None else f"{win[0]:g}..{win[1]:g}",
                    "dropped_arm": dropped or "", "verdict": verdict,
                    "reason": reason,
                })
            any_cand = any(r["verdict"] == "CANDIDATE" for r in rows[-len(accepts):])
            print(f"  [{i:>3}/{len(records)}] {rec['id']:11s} "
                  f"{'HIT' if any_cand else 'hit':3s} "
                  f"{len(accepts)} sheet(s), best n="
                  f"{max(x['n_animals'] for x in accepts)}"
                  f"{'  FLAGGED' if collisions else ''}", flush=True)
            sys.stdout.flush()
    finally:
        # map() queued the whole budget; an interrupted run must not sit
        # downloading the rest of it before it lets go
        pool.shutdown(cancel_futures=True)

    tag = _slug(a.tag or a.line)
    out = os.path.join(OUTDIR, f"{tag}_candidates.csv")
    cols = ["id", "doi", "year", "journal", "authorString", "title", "file",
            "sheet", "layout", "n_animals", "n_points", "n_below_floor",
            "header_evidence", "signature",
            "window", "dropped_arm", "verdict", "reason"]
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["line", "unit_counted", "profile",
                                           "min_subjects", "min_points"] + cols,
                           extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({"line": a.line, "unit_counted": UNIT_COUNTED,
                        "profile": S.PROFILE["name"],
                        "min_subjects": S.MIN_ANIMALS,
                        "min_points": S.MIN_POINTS, **r})

    cand = [r for r in rows if r["verdict"] == "CANDIDATE"]
    refused = [r for r in rows if r["verdict"] == "REFUSED_CALENDAR"]
    flagged = [r for r in rows if r["verdict"] == "FLAGGED"]
    print(f"\n  {len(records)} papers fetched of a {a.budget} budget")
    print(f"  {n_accept} scanner acceptances -- UNIT COUNTED: {UNIT_COUNTED}, "
          f"NOT verified cells")
    # ORDERED BEST-FIRST, BECAUSE THE USER'S COST IS TIME, NOT ACCEPTANCES.
    #
    # Precision is 6 of 15, so a researcher opens about two and a half sheets
    # per usable one, and the order they open them in is the only part of that
    # this tool controls. `header_evidence` says whether the sheet's own
    # headers name a subject id, the covariate and the value, or whether it was
    # taken on numeric shape alone -- and 48% of accepts are shape alone.
    #
    # This does NOT filter. Gating on evidence was measured and rejected: it
    # costs 3 of 15 positives and does not remove the known false positive.
    # Ordering costs nothing and lets a reader stop when they have enough.
    def _rank(r):
        ev = r.get("header_evidence") or ""
        # A discipline signature sinks a row rather than dropping it: measured
        # at 4 of 9 false accepts caught, below the bar registered for a gate,
        # but real signal that costs nothing when it only reorders.
        return (bool(r.get("signature")), -len(ev), -int(r.get("n_animals") or 0),
                -int(r.get("n_points") or 0))
    cand = sorted(cand, key=_rank)
    print(f"  {len(cand)} CANDIDATE sheet(s), {len(refused)} refused by the "
          f"calendar screen, {len(flagged)} FLAGGED by the re-export check")
    for r in cand:
        print(f"    {r['id']:11s} [{(r.get('header_evidence') or '---'):>3s}] "
              f"{r['n_animals']:>4} animals x "
              f"{r['n_points']:>3} pts  [{r['layout']}]  win {r['window']}"
              f"{'  drop=' + r['dropped_arm'] if r['dropped_arm'] else ''}")
        print(f"                {r['title'][:88]}")
    print(f"\n  artifact: {out}")
    prof = S.PROFILE["name"]
    if prof == "tumor_volume":
        print(f"  SCANNER RECALL {RECALL_NOTE}")
        print(f"  SCANNER PRECISION {PRECISION_NOTE}")
    else:
        # THE BANNER PRINTED tumor_volume's NUMBERS WHATEVER PROFILE RAN.
        # A 3Rs user pointed out that the run-time output never disclosed that
        # they do not apply to the profile just used -- the one place this
        # tool's honesty had a gap was the place a reader actually looks.
        print(f"  SCANNER RECALL and PRECISION for profile '{prof}': NOT "
              f"MEASURED. There is no figure for it, none.")
        print(f"  The numbers quoted elsewhere are for `tumor_volume` ONLY "
              f"and DO NOT TRANSFER.")
        print(f"  Treat every acceptance above as unscored.")
    print("  Every CANDIDATE above is a scanner acceptance and nothing more. "
          "None is a cell until a builder verifies it at the sheet.")
    print("  STATE: %d candidate, 0 verified. Verified entries live in "
          "registry.csv, and nowhere else (skills/unpool/SKILL.md, the output contract)."
          % len(cand))
    return 0


def demo():
    """The calendar screen's self-check. Runs offline, no corpus, no network."""
    # (1) An overlapping candidate is admitted, and the window is the
    #     intersection -- not the arm's own range. `CCSB` is the real LLC
    #     arm's shape: a daily grid 4..22, so the intersection still leaves it
    #     well above both floors.
    held = {"CCSB": [list(range(4, 23))] * 20}
    ok, why, win, drop = calendar_screen(held, "C", [[6, 10, 14, 18]] * 6)
    assert ok and win == (6, 18) and drop is None, (ok, why, win, drop)

    # (2) A disjoint candidate on a ONE-ARM model is refused, and the drop
    #     rule never even fires: dropping either arm leaves one, below
    #     MIN_ARMS_PER_MODEL. **This is exactly LLC's position today** -- with
    #     a single held arm, no calendar outlier can be rescued by the one-arm drop rule, so
    #     an LLC candidate either overlaps 4..22 or it is out.
    ok, why, win, drop = calendar_screen(held, "C", [[30, 34, 38, 42]] * 6)
    assert not ok and drop is None and "one drop does not suffice" in why, why

    # (2b) With TWO held arms the drop rule does fire on a disjoint candidate
    #      -- and the arm it picks is the candidate, which buys nothing.
    two_held = {"A": [list(range(4, 23))] * 6, "B": [list(range(6, 21))] * 6}
    ok, why, win, drop = calendar_screen(two_held, "C", [[30, 34, 38, 42]] * 6)
    assert not ok and drop == "C" and "candidate IS the arm" in why, (why, drop)

    # (3) MDA-MB-231 is NOT revived -- the one-arm drop rule's own worked example. Two arms,
    #     21..70 and 0..18, disjoint; dropping one leaves one, below
    #     MIN_ARMS_PER_MODEL, so no drop is attempted at all.
    two = {"A": [[21, 40, 55, 70]] * 6, "B": [[0, 6, 12, 18]] * 6}
    assert model_window(two) is None
    ok, why, win, drop = calendar_screen({"A": two["A"]}, "B", two["B"])
    assert not ok and drop is None and "one drop does not suffice" in why, why

    # (4) The one-arm drop fires when a THIRD arm is the calendar outlier, and
    #     the arm dropped is the outlier rather than the candidate.
    three = {"CCSB": [list(range(4, 23))] * 6, "OUT": [[60, 70, 80, 90]] * 6}
    ok, why, win, drop = calendar_screen(three, "C", [[6, 10, 14, 18]] * 6)
    assert ok and drop == "OUT" and win == (6, 18), (ok, why, win, drop)

    # (5) The animal floor is checked INSIDE the window, not on the raw arm:
    #     20 animals whose grids leave fewer than 4 points inside it fail.
    thin = {"CCSB": [[4, 5, 6, 7]] * 20}
    ok, why, win, drop = calendar_screen(thin, "C", [[6, 10, 14, 18]] * 6)
    assert not ok and "retains" in why, why

    # (6) A wide-idx sheet has no calendar and must not be treated as empty.
    ok, why, win, drop = calendar_screen(held, "C", None)
    assert not ok and "calendar unknown" in why, why

    # (7) Author tokens are surname + first initial, and a bare surname stays.
    assert author_tokens("Huang Y, Zhao Y, Su Y.") == {"huang y", "zhao y",
                                                       "su y"}
    assert author_tokens("Benzekry") == {"benzekry"}
    print("mine_line demo: all screen checks pass")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        sys.exit(main())
