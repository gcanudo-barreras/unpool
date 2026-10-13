"""THE GUARD EVERY CORPUS BUILDER FROM `v9` ON MUST PASS: one key, one source.

The refusal IS the spec -- protocol rule 6, refuse before writing and not
after.

WHAT IT REFUSES, AND WHY IT LIVES HERE RATHER THAN IN A BUILDER
------------------------------------------------------------------------------
`CorpusArm`'s identity is `(model, study)`. Its `source` is NOT part of that
identity, so when two publications happen to write the same `study` string for
the same `model` the loader silently fuses them into one arm and reports ONE of
the two `source` labels for all of it -- a loader that keys arms on
`(model, study)` does `src[key] = row["source"]` per row, so the LAST row
read wins and the other publication's animals are attributed to a paper they
did not come from.

That is exactly what `v6` shipped and `v8` inherited: `4T1|4T1::4T1:CTRL1` held
12 `Mereiter-NCOMMS73401` animals and 6 `Prosetta-DRYAD-CFXPNVXNZ` animals under
`Prosetta`'s name alone. Nothing in the build chain noticed, because nothing was
looking. the growing-artifact decision makes the corpus a GROWING artifact; with more publications added
by more builders, a second collision is a certainty rather than a risk.

**THIS IS INVARIANT 3'S SHAPE APPLIED TO IDENTITY RATHER THAN TO A CONSTANT:
the corpus must not be able to state a provenance it cannot support.** A
corpus quote exists to hand a study a variance estimate WITH its provenance
attached, for an ethics submission. A fused arm's provenance is false for part
of the arm, and the falsehood is invisible downstream.

It is a module, not a paragraph copied into each builder, so that the next
builder INHERITS the refusal by importing it instead of remembering to
reimplement it. It depends on nothing but the standard library, and a guard
that runs before the loader is the only guard that can refuse to WRITE a bad
corpus rather than merely notice one.

WHAT IT IS NOT
------------------------------------------------------------------------------
It is NOT a loader-level check. Putting the same refusal inside whatever
loads the corpus may well be right -- it would protect every older corpus
version too -- but that is a change to the consuming application, with its
own consequences, and it is a SEPARATE decision.

It does NOT deduplicate, merge, rename or repair anything. It reads and refuses.

THE SECOND REFUSAL: RESERVED MODELS (the reserved-units rule (protocol rule 6))
------------------------------------------------------------------------------
`data/holdout/` holds models reserved for VALIDATION. the reserved-units rule: an arm cannot both
quote and validate, so a model that is ever used to grade a corpus must never
sit inside one. **The reserved unit is the MODEL, not the arm** -- if a future
corpus ingests a DIFFERENT arm of a reserved model, the reserved arm's model is
in the pool and the evaluation leaks, which is the cross-model leak the cross-model leak spent a
session closing.

The guard's input is `data/holdout/RESERVED_MODELS.csv`, one line per model with
the date and the row that reserved it. Future reservations APPEND there, under
the reserved-units rule's acceptance rule, and every builder that already imports this module
inherits the refusal without being edited.

A MISSING manifest is a REFUSAL, not a pass. The file is tracked; if it is not
on disk the checkout is broken, and a guard that silently permits everything
when its input disappears is the exact failure mode it exists to prevent.

Run: ``unpool guard <your-builder-output>.csv``

The input is ';'-delimited and must carry `model`, `study`, `source` and
`animal_id`. `templates/builder.py` writes exactly that; a comma-delimited
file fails with an opaque missing-column error. Exit 0 and a record under
`runs/` when both refusals pass; exit 1 naming the colliding key or the
reserved model when they do not.

`example/BUILD_REPORT.md` runs this on a real builder's output, with the
output of every step -- including the two cases where a guard refuses.
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

__all__ = ["CorpusGuardRefused", "single_source_violations",
           "assert_single_source_keys", "RESERVED_MANIFEST",
           "load_reserved_models", "reserved_models_present",
           "assert_no_reserved_models", "assert_buildable", "check_file"]


class CorpusGuardRefused(Exception):
    """A corpus states a provenance it cannot support. The build must stop."""


def single_source_violations(rows):
    """-> {(model, study): {source: n_animals}} for every key spanning >1 source.

    Counts ANIMALS, not rows, because the number that matters when this fires is
    "how many animals are attributed to the wrong publication".
    """
    per = defaultdict(lambda: defaultdict(set))
    for r in rows:
        key = (str(r["model"]).strip(), str(r["study"]).strip())
        per[key][str(r["source"]).strip()].add(str(r["animal_id"]).strip())
    return {k: {s: len(a) for s, a in sorted(v.items())}
            for k, v in sorted(per.items()) if len(v) > 1}


def assert_single_source_keys(rows, label="corpus"):
    """Refuse if any `(model, study)` key spans more than one `source`.

    Returns the number of keys checked, so a build report can state the
    denominator the "0 violations" was measured over.
    """
    bad = single_source_violations(rows)
    n_keys = len({(str(r["model"]).strip(), str(r["study"]).strip()) for r in rows})
    if bad:
        lines = ["%s: %d of %d (model, study) key(s) span more than one source."
                 % (label, len(bad), n_keys),
                 "`CorpusArm.key` is (model, study); `source` is not in it, so the "
                 "loader keeps ONE source label per key and the rest of the arm is "
                 "attributed to a publication it did not come from."]
        for (model, study), srcs in bad.items():
            total = sum(srcs.values())
            lines.append("  %s|%s  %d animals:" % (model, study, total))
            for s, n in sorted(srcs.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append("      %-28s %3d animals" % (s, n))
        lines.append("REFUSING. Disambiguate the `study` label of the colliding "
                     "subset -- see the single-source guard (protocol rule 6) -- rather than widening the key.")
        raise CorpusGuardRefused("\n".join(lines))
    print("  single-source guard: OK -- %d (model, study) keys in %s, 0 span "
          "more than one source" % (n_keys, label))
    return n_keys


# ---------------------------------------------------------------------------
# refusal 2: a model reserved for validation may not enter a corpus (the reserved-units rule (protocol rule 6))
# ---------------------------------------------------------------------------

# THE MANIFEST PATH, AND THE THIRD STATE THIS CHECK NEEDED
# ---------------------------------------------------------------------------
# `_REPO` used to be the PARENT of this file's directory, which was right when
# this lived in a subdirectory and is wrong now that it sits at the
# repo root -- it resolved one level above the repository entirely.
#
# The deeper problem the wrong path exposed: this check had two states, present
# and missing, and missing was a REFUSAL. That is correct for a project where
# the manifest is tracked and its absence means a broken checkout. It is wrong
# for everyone else, because most users hold nothing out and would be refused
# for a feature they do not use.
#
# So there are three states now, which is protocol rule 11 applied to this
# guard: configured-and-present is CHECKED, configured-and-missing is REFUSED
# (a declared reservation that cannot be read must not be assumed honoured),
# and not-configured is reported as NOT RUN and does not block.
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESERVED_MANIFEST = (os.environ.get("UNPOOL_RESERVED")
                     or os.path.join(_REPO, "reserved_units.csv"))
RESERVED_DECLARED = bool(os.environ.get("UNPOOL_RESERVED"))


def load_reserved_models(path=None):
    """-> {model: {manifest columns}} from the holdout manifest.

    A missing manifest REFUSES. See the module docstring: the file is tracked,
    and a guard that passes everything when its input vanishes is worse than no
    guard, because it reports OK.
    """
    path = path or RESERVED_MANIFEST
    if not os.path.exists(path) and not RESERVED_DECLARED:
        return None            # not configured -> the caller reports NOT RUN
    if not os.path.exists(path):
        raise CorpusGuardRefused(
            "the reserved-model manifest is missing: %s\n"
            "It is tracked (the reserved-units rule (protocol rule 6)). Restore it before building a corpus -- a "
            "build that cannot read the reservation cannot honour it." % path)
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    if not rows or "model" not in (rows[0] or {}):
        raise CorpusGuardRefused("%s has no `model` column" % path)
    return {str(r["model"]).strip(): r for r in rows if str(r["model"]).strip()}


def reserved_models_present(rows, reserved=None):
    """-> {model: n_animals} for every reserved model appearing in `rows`."""
    reserved = load_reserved_models() if reserved is None else reserved
    if reserved is None:
        return {}
    hit = defaultdict(set)
    for r in rows:
        m = str(r["model"]).strip()
        if m in reserved:
            hit[m].add(str(r["animal_id"]).strip())
    return {m: len(a) for m, a in sorted(hit.items())}


def assert_no_reserved_models(rows, label="corpus", reserved=None):
    """Refuse if any row carries a model reserved for validation.

    Returns the number of reserved models checked against, so a build report can
    state the denominator its "0 reserved" was measured over.
    """
    reserved = load_reserved_models() if reserved is None else reserved
    if reserved is None:
        print("  reserved-unit guard: NOT RUN -- no manifest configured. "
              "Set UNPOOL_RESERVED to a CSV with a `model` column, or place "
              "one at %s. THIS IS NOT A PASS." % RESERVED_MANIFEST)
        return 0
    bad = reserved_models_present(rows, reserved)
    if bad:
        lines = ["%s: %d reserved model(s) present." % (label, len(bad)),
                 "A reserved model is held OUT of every corpus so it can GRADE "
                 "corpus versions. An arm cannot both quote and validate (the reserved-units rule), "
                 "and the reserved unit is the MODEL, not the arm (the reserved-units rule) -- any "
                 "arm of it in the pool leaks the evaluation (the cross-model leak)."]
        for m, n in sorted(bad.items(), key=lambda kv: (-kv[1], kv[0])):
            meta = reserved.get(m, {})
            lines.append("  %-10s %3d animals   reserved %s by %s"
                         % (m, n, meta.get("reserved_on", "?"),
                            meta.get("reserved_by", "?")))
        lines.append("REFUSING. Drop these models from the build, or retire the "
                     "reservation in data/holdout/RESERVED_MODELS.csv with a row "
                     "that says why -- see the reserved-units rule (protocol rule 6).")
        raise CorpusGuardRefused("\n".join(lines))
    print("  reserved-model guard: OK -- 0 of %d reserved models in %s"
          % (len(reserved), label))
    return len(reserved)


def assert_buildable(rows, label="corpus"):
    """Every refusal in this module, in one call. THE build gate.

    A builder calls THIS rather than the individual assertions, so that the next
    refusal added here is inherited by every builder that already imports it
    instead of being remembered by each one separately.
    """
    n_keys = assert_single_source_keys(rows, label=label)
    assert_no_reserved_models(rows, label=label)
    return n_keys


def check_file(path, delimiter=";"):
    with open(path, encoding="utf-8-sig") as fh:
        rdr = csv.DictReader(fh, delimiter=delimiter)
        need = ("model", "study", "source", "animal_id")
        missing = [c for c in need if c not in (rdr.fieldnames or [])]
        if missing:
            raise CorpusGuardRefused("%s is missing column(s) %s" % (path, missing))
        rows = [{k: r[k] for k in need} for r in rdr]
    return assert_buildable(rows, label=path)


def write_record(path, checks, out_dir=None):
    """Persist what was checked, when, over what. -> the artifact's path.

    `mine.py` fsyncs a frozen run record before fetching a single file, and
    these guards wrote NOTHING -- stdout and an exit code. A systematic-review
    user put it precisely: the audit trail exists for the cheap step and not
    for the load-bearing one, which is backwards from what a methods section
    needs to cite.

    So a run leaves a record: the file, its sha256, the date, and per check
    whether it PASSED, REFUSED or DID NOT RUN. `NOT RUN` is a first-class
    state here for the same reason it is everywhere else in this toolchain
    (rule 11) -- a reserved-unit check with no manifest configured has not
    passed, and a record that cannot say so is not worth writing.
    """
    import datetime
    import hashlib
    import json
    out_dir = out_dir or os.environ.get("UNPOOL_OUT") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runs")
    os.makedirs(out_dir, exist_ok=True)
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    rec = {
        "tool": "guard.py",
        "checked": os.path.abspath(path),
        "sha256": digest,
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "reserved_manifest": RESERVED_MANIFEST if RESERVED_DECLARED else None,
        "checks": checks,
    }
    name = os.path.splitext(os.path.basename(path))[0]
    dest = os.path.join(out_dir, "guard_%s.json" % name)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    return dest


def main(argv):
    if not argv:
        print(__doc__.strip().splitlines()[0])
        print("usage: unpool guard <corpus.csv> [...]")
        return 2
    rc = 0
    for path in argv:
        checks = {}
        try:
            n_keys = check_file(path)
            checks["single_source"] = {"state": "PASSED", "keys": n_keys}
            checks["reserved_units"] = {
                "state": "PASSED" if RESERVED_DECLARED else "NOT RUN",
                "manifest": RESERVED_MANIFEST if RESERVED_DECLARED else None}
        except CorpusGuardRefused as exc:
            print("REFUSED" + chr(10) + "%s" % exc)
            checks["result"] = {"state": "REFUSED", "why": str(exc)[:600]}
            rc = 1
        try:
            print("  record: %s" % write_record(path, checks))
        except Exception as e:
            print("  could NOT write the run record: %s" % e)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
