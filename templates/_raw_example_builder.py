"""Build thsd7b-arms-v1.csv -- TWO gastric cancer cell lines (SNU-1,
MKN-45), NC vs si-THSD7B knockdown, from Quan, Cheng, Pu & Deng, PLOS ONE,
DOI 10.1371/journal.pone.0351545 ("THSD7B promotes tumor progression and is
associated with prognosis in gastric adenocarcinoma").
================================================================================

WHY THIS BUILD NEEDED TWO ROUNDS OF USER INPUT BEFORE IT COULD RUN AT ALL
------------------------------------------------------------------------------
The SI (`journal.pone.0351545.s001.xlsx`, copied here unmodified as
`pone0351545_thsd7b_gastric.xlsx`) is mostly IN VITRO assay data (CCK-8,
Transwell, PCR, Western blot, scratch test -- Figures 4, 5, 7, 8), unrelated
to tumour kinetics. The in vivo xenograft block (`Weight` / `Volume of
tumor` / `weight of tumor`, rows 119-155 of `Sheet1`) sits in the middle of
that, with two blocking gaps neither the SI nor the paper's own text
resolved:

  1. NO elapsed-day values anywhere for the four timepoints. Checked the
     Methods animal-experiments paragraph AND the full Figure 6 legend
     verbatim (two separate targeted checks) -- neither states a day, an
     interval, or a schedule ("monitored at regular intervals" is the most
     specific text in the paper). **Resolved by the user reading the
     published Figure 6C image directly** (not derivable from the SI or
     the paper's text at all): days **7, 14, 21, 28**, the same grid for
     both tumour volume and body weight. This is PROVENANCE FROM A FIGURE
     READING, not from a stated method -- recorded here because a future
     session should not re-derive or second-guess it against the paper's
     text, which will not corroborate it.
  2. NO way to tell which of the two parallel data blocks (rows 122-125 /
     137-140 vs rows 129-132 / 144-147) belongs to which cell line -- the
     SI carries no cell-line label on either block, and the Figure 6
     legend says panel 6C "contains both [SNU-1 and MKN-45]... combined"
     without disambiguating. **Resolved by the user reading the figure**:
     the UPPER growth curve is SNU-1, the LOWER is MKN-45 -- matching the
     paper's own consistent "SNU-1 and MKN-45" ordering everywhere else
     in the text, which corroborates but does not by itself prove the
     reading.

Both of these are exactly the "verify identity, never infer it from
structure or a name" discipline this corpus has followed throughout
(the "verify identity at the sheet" rule, protocol rule 4) -- applied
here to a source that could not be resolved from its own documents at all,
only from the human reading the published figure. **If the day grid or the
panel assignment above is ever found to be wrong, EVERY row this build
emits is wrong** -- there is no independent internal check possible on
either point (unlike the case-sensitivity bug or the AB-block dedup earlier
on this line, which were caught by a fingerprint cross-check against
another route). Flagged here, not glossed over.

MODEL, HOST AND METHOD, verified against the paper's own text
------------------------------------------------------------------------------
SNU-1 and MKN-45 are two DIFFERENT human gastric cancer cell lines --
treated as two different `model` values, never pooled, the same "a group is
not an arm" discipline applied to two cell lines sharing one figure rather
than to two drug studies of one model. Host: BALB/c NUDE mice (female,
4-6 weeks), n=5 per group, matching this data exactly (5 columns per arm).
Method, stated explicitly: "Tumor growth was monitored at regular intervals
using a caliper, and tumor volume was calculated as (length x width^2) / 2."
Attrition: "No animals were excluded from the final analysis... No
unexpected animal deaths occurred" -- and the data is clean of any gaps,
consistent with that statement (unlike the Chiang source, nothing here
needed reconciling against a stated protocol).

THE ANIMAL KEY: NO ORIGINAL IDENTIFIERS EXIST IN THIS SOURCE
------------------------------------------------------------------------------
Unlike every prior source on this line, the SI gives no per-animal id at
all -- five unlabelled columns per arm. Mouse index 1-5 here is a SYNTHETIC
positional id (left-to-right column order within the arm's block),
documented as such and never presented as an identifier the paper itself
assigned.

THE SCHEMA
----------
    animal_id;pair_id;model;study;arm_label;role;cohort;source;days;
    volumes;body_weight_g

No dose/route/schedule columns (both arms are a binary genetic
knockdown/negative-control pair, nothing to parse). `body_weight_g` carried
because the source has it, same policy as Chiang's source and the earlier
session decision to capture body weight opportunistically wherever a source
already supplies it, without yet building a cross-study welfare prior from
it. Terminal excised `weight of tumor` (rows 149-155) is NOT included in
this per-day schema -- it is a single endpoint value per animal with no
day, and this source gives no way to link its row order to the same
physical animals as the `Volume of tumor` table's column order, so linking
them would assert an identity this source does not support. It remains in
the raw xlsx, unused, the same policy `build_ebos_arms_v1.py` applies to
the columns it reads but does not need.

  model / study -- `SNU-1` or `MKN-45`.
  arm_label  -- `NC` (negative control) or `si-THSD7B` (knockdown),
                unmodified from the source.
  role       -- 'control' for `NC`, 'treated' for `si-THSD7B`. Explicit
                two-item mapping, not inferred from the label text.
  cohort     -- physical-mouse-set id by (days, volumes) fingerprint, same
                rule as every prior build on this line -- checked, not
                assumed, even though a collision is very unlikely with
                only two arms per model here.
  source     -- `Quan-PONE0351545` (first author + article id).

MIN_POINTS_PER_ANIMAL FLOOR: 4 (the profile's `min_points`). Every animal here
has exactly 4 points -- the floor binds on NONE of them, but ALSO leaves
NO slack: a single missing day for any animal would drop it entirely. None
are missing, checked explicitly below.

Run: ``python build_thsd7b_arms_v1.py``
"""

from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict

import openpyxl

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
WORKBOOK = os.path.join(_ROOT, "data", "corpus", "raw", "pone0351545_thsd7b_gastric.xlsx")
OUT = os.path.join(_ROOT, "data", "corpus", "thsd7b-arms-v1.csv")

SOURCE = "Quan-PONE0351545"
MIN_POINTS_PER_ANIMAL = 4

# Day grid, confirmed by the user reading the published Figure 6C directly
# (not stated in the paper's own text -- see docstring). Same grid for
# weight and volume, both cell lines.
DAYS = [7.0, 14.0, 21.0, 28.0]

# Row layout, 0-indexed, verified by hand against the actual sheet dump.
# Each block: 4 consecutive rows (one per day in DAYS, in order), 10 data
# columns (0-4 = NC mice 1-5, 5-9 = si-THSD7B mice 1-5).
WEIGHT_ROWS = {"SNU-1": 122, "MKN-45": 129}     # first DAY-row of each block
VOLUME_ROWS = {"SNU-1": 137, "MKN-45": 144}
NC_COLS = range(0, 5)
SI_COLS = range(5, 10)

ROLE_OF_ARM = {"NC": "control", "si-THSD7B": "treated"}


class BuildRefused(SystemExit):
    """The workbook does not look like what this parser was written against."""


def _read_block(rows, first_row):
    """{arm_label: {mouse_idx: [volume_per_day]}} for one 4-row block."""
    out = {"NC": defaultdict(list), "si-THSD7B": defaultdict(list)}
    for i, day in enumerate(DAYS):
        r = rows[first_row + i]
        for j, col in enumerate(NC_COLS):
            v = r[col]
            if not isinstance(v, (int, float)):
                raise BuildRefused(f"row {first_row + i} col {col}: expected a "
                                    f"number for NC mouse {j + 1} at day {day}, got {v!r}")
            out["NC"][j + 1].append(float(v))
        for j, col in enumerate(SI_COLS):
            v = r[col]
            if not isinstance(v, (int, float)):
                raise BuildRefused(f"row {first_row + i} col {col}: expected a "
                                    f"number for si-THSD7B mouse {j + 1} at day {day}, got {v!r}")
            out["si-THSD7B"][j + 1].append(float(v))
    return out


def _fingerprint(vols_per_day):
    return tuple((round(d, 9), round(v, 9)) for d, v in zip(DAYS, vols_per_day))


def assign_cohorts(model, weight_block, volume_block):
    """One id per PHYSICAL set of mice, from the VOLUME curves (weight is a
    second measurement on the same animals, not an independent identity
    check here -- five unlabelled columns give nothing else to fingerprint
    against)."""
    sig_to_cohort, cohort_of_arm = {}, {}
    counters = defaultdict(int)
    for arm in ("NC", "si-THSD7B"):
        sig = frozenset(_fingerprint(v) for v in volume_block[arm].values())
        if sig in sig_to_cohort:
            cohort_of_arm[arm] = sig_to_cohort[sig]
            continue
        tag = "CTRL" if arm == "NC" else "TRT"
        counters[tag] += 1
        cid = f"{model}:{tag}{counters[tag]}"
        sig_to_cohort[sig] = cid
        cohort_of_arm[arm] = cid
    return cohort_of_arm


def build_model(rows, model):
    weight_block = _read_block(rows, WEIGHT_ROWS[model])
    volume_block = _read_block(rows, VOLUME_ROWS[model])
    cohort_of_arm = assign_cohorts(model, weight_block, volume_block)

    out_rows = []
    for arm in ("NC", "si-THSD7B"):
        role = ROLE_OF_ARM[arm]
        cohort = cohort_of_arm[arm]
        vol_by_mouse = volume_block[arm]
        bw_by_mouse = weight_block[arm]
        if set(vol_by_mouse) != set(range(1, 6)) or set(bw_by_mouse) != set(range(1, 6)):
            raise BuildRefused(f"{model}/{arm}: expected mice 1-5 in both "
                                "volume and weight blocks")
        for mouse in range(1, 6):
            vols = vol_by_mouse[mouse]
            bws = bw_by_mouse[mouse]
            if len(vols) < MIN_POINTS_PER_ANIMAL:
                continue
            aid = f"{model}:{arm}:{mouse}"
            for day, v, bw in zip(DAYS, vols, bws):
                out_rows.append({
                    "animal_id": aid, "pair_id": model, "model": model,
                    "study": model, "arm_label": arm, "role": role,
                    "cohort": cohort, "source": SOURCE,
                    "days": f"{day:g}", "volumes": f"{v:g}",
                    "body_weight_g": f"{bw:g}",
                })
    return out_rows


def main():
    print("building thsd7b-arms dataset v1 (SNU-1 + MKN-45, PONE.0351545)")
    if not os.path.exists(WORKBOOK):
        raise BuildRefused(f"workbook not found: {WORKBOOK}")
    wb = openpyxl.load_workbook(WORKBOOK, read_only=True, data_only=True)
    if "Sheet1" not in wb.sheetnames:
        raise BuildRefused(f"expected 'Sheet1', have {wb.sheetnames}")
    rows = [list(r) for r in wb["Sheet1"].iter_rows(values_only=True)]

    out_rows = []
    for model in ("SNU-1", "MKN-45"):
        out_rows += build_model(rows, model)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, delimiter=";",
                            fieldnames=["animal_id", "pair_id", "model", "study",
                                        "arm_label", "role", "cohort", "source",
                                        "days", "volumes", "body_weight_g"])
        w.writeheader()
        w.writerows(out_rows)

    animals = {r["animal_id"] for r in out_rows}
    by_arm = defaultdict(set)
    for r in out_rows:
        by_arm[(r["model"], r["arm_label"])].add(r["animal_id"])

    print(f"\nwrote {OUT}")
    print(f"  rows={len(out_rows)}  animals={len(animals)}  arms={len(by_arm)}")
    for (model, arm), a in sorted(by_arm.items()):
        print(f"    {model:8s} {arm:10s} n={len(a)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
