"""ONE SOURCE, ONE BUILDER. Copy this file, do not import it.

Replace every <ANGLE BRACKET> and delete every instruction comment. What
survives must be true of YOUR source, not of this template.

WHY A SCRIPT AND NOT A SPREADSHEET
------------------------------------------------------------------------------
The CSV is the cheap part. The expensive part is everything a future reader
needs in order to trust it: which file, which sheet, which rows, which arm is
the control, what the paper claimed versus what the data actually holds, and
which questions a HUMAN had to answer because the documents did not.

None of that survives in a spreadsheet. It survives here, in the docstring,
and the script re-emits the CSV from the source so the claim can be re-checked
rather than believed.

================================================================================
<MODEL / CELL LINE / SUBJECT TYPE> -- <N> arms, from <FIRST AUTHOR> et al.
<YEAR>, <JOURNAL>, DOI <10.xxxx/xxxxx>.
================================================================================

THE SOURCE
------------------------------------------------------------------------------
File: `<exact filename as downloaded>`, sheet `<sheet name>`, rows <a>-<b>.
Obtained from: <deposit / supplementary bundle> on <YYYY-MM-DD>.
Licence: <CC-BY 4.0 / CC0 / ...>  -- travels with the data, into the report.

MODEL, HOST AND METHOD, verified against the paper's own text
------------------------------------------------------------------------------
Quote the paper. A column header is not evidence.

  * METHOD, stated explicitly: "<verbatim quote of the measurement method>"
  * MODEL: <what it is, and how you know it from the text -- not from the
    sheet's title>
  * GROUP SIZES: the paper states <n>; the data carries <n>. If these
    DISAGREE, say so here and trust the count, not the claim.
  * ATTRITION: <what the paper says about exclusions and deaths, and whether
    the data is consistent with it>

WHAT A HUMAN RESOLVED THAT THE PAPER DOES NOT STATE
------------------------------------------------------------------------------
**This section is the reason the file exists. Do not delete it when it is
empty -- write "nothing" and mean it.**

Anything you could not derive from the documents and had to settle another way
goes here, marked as what it is, with the consequence if it is wrong. For
example: a day grid read off a published figure image because the Methods say
only "monitored at regular intervals"; a panel-to-cell-line assignment taken
from the figure because the supplement carries no label.

  <e.g.> Days 7/14/21/28, resolved by the user reading Figure 6C directly --
  NOT derivable from the supplement or the paper's text, which says only
  "regular intervals". **If this grid is wrong, every row this build emits is
  wrong**, and there is no internal check that would catch it.

THE SUBJECT KEY
------------------------------------------------------------------------------
<Whether the source carries real per-subject identifiers, or whether the index
below is POSITIONAL and synthetic. Never present a positional index as an
identifier the authors assigned.>
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool.guard import assert_buildable, CorpusGuardRefused  # noqa: E402

SRC = "<path to the source file>"
OUT = "<path to the CSV this writes>"

# THE ROUND-TRIP GUARD. Counted BY READING THE FILE, not copied from the
# legend -- published group sizes and actual column counts disagree often
# enough that the legend is not a check. If a re-download disagrees with these,
# the build REFUSES. It does not adapt: a source that changed under you is a
# fact to investigate, not a number to follow.
_VERIFIED_N = 0            # subjects in the arm(s) this build emits
_VERIFIED_GRID = ()        # the covariate values, e.g. (7.0, 14.0, 21.0, 28.0)


class BuildRefused(Exception):
    """The source does not match what was verified. Stop."""


def read_source():
    """-> {animal_id: [(covariate, value), ...]}  Parse and nothing else."""
    raise NotImplementedError("<parse SRC here>")


def main():
    curves = read_source()

    if len(curves) != _VERIFIED_N:
        raise BuildRefused(
            "%d subjects, verified %d -- the source changed, or the parse did. "
            "Investigate before editing this constant."
            % (len(curves), _VERIFIED_N))

    grids = {tuple(c for c, _ in pts) for pts in curves.values()}
    if grids != {_VERIFIED_GRID}:
        raise BuildRefused("covariate grid %s, verified %s"
                           % (sorted(grids), [_VERIFIED_GRID]))

    # THESE COLUMN NAMES ARE NOT A SUGGESTION. `guard.py` keys on
    # `model, study, source, animal_id` and `fingerprint.py` on
    # `animal_id, model, source, days, volumes`; anything else is refused
    # before either guard looks at a value. This template said `subject_id`
    # and `covariate`/`value` until V6 ran the whole path for the first time
    # and found that a builder written from it dies on an uncaught
    # `KeyError: 'animal_id'` inside its own `assert_buildable` call.
    #
    # `days` and `volumes` are the corpus schema's fixed names, inherited from
    # tumour work. A NON-TUMOUR builder puts its covariate in `days` and its
    # response in `volumes` and says so in the docstring -- or renames them and
    # loses axis 3, which is a real cost and not a free choice. Generalising
    # the guards is its own pass with its own measurement.
    rows = [{"animal_id": aid, "model": "<model>", "study": "<study>",
             "source": "<Source-DOI-tag>", "days": c, "volumes": v}
            for aid, pts in sorted(curves.items()) for c, v in pts]

    # Refuse before writing, never after: a guard that runs on a file already
    # on disk is a report, not a gate.
    assert_buildable(rows, label=OUT)

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter=";")
        w.writeheader()
        w.writerows(rows)
    print("wrote %s: %d rows, %d subjects" % (OUT, len(rows), len(curves)))


if __name__ == "__main__":
    try:
        main()
    except (BuildRefused, CorpusGuardRefused) as exc:
        print("REFUSED\n%s" % exc)
        sys.exit(1)
