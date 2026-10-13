# Build report — `MDA-MB-231-CRISPRa-MFP`, 41 mice, 5 arms

The whole path, on one paper, with the output of every step. Mine → verify →
builder → guards → CSV. Before this existed, phase 2 of the README was a
promise, and a promise is not a check that ran (protocol rule 11).

Registered before it was built: `docs/VALIDATION.md`, V6.

---

## The source

| | |
|---|---|
| paper | Galal S, Chaltel Lima L, Wang N, Moury C, Yan G, Dai M, Ali S, Lebrun JJ. *In vivo CRISPR screening identifies metastasis suppressors in triple-negative breast cancer.* Nature Communications, 2026-08-04 |
| DOI | `10.1038/s41467-026-76293-x` — PMC13534483 |
| licence | **CC BY-NC-ND 4.0** |
| file | `41467_2026_76293_MOESM6_ESM.xlsx`, the article's Source Data file |
| sheet | `Supplementary Fig. 8b.` — the trailing period is part of the name |
| cells | header rows 3–4, data rows 5–13, columns C..AQ |
| workbook sha256 | `13fbff4ba57d7de064911c288f0002757754dbfe26f45eea8bffc94b8d4ebae7` |

The workbook has **41 sheets**; this is one of them. The scanner accepted three
(`Fig. 2i`, `Fig. 3p`, `Supplementary Fig. 8b.`). Addressing the source by sheet
rather than by file is not pedantry — a file-level claim about this workbook
would be a claim about 41 different things.

---

## Step 1 — mine. The paper was on the list before anyone opened it

`PMC13534483` is **line 17 of 35** in the frozen scan order, written and
`fsync`ed at `(timestamp)`, *before* the first supplementary file of
that campaign was fetched (protocol rule 2).

```
runs/tumor_volume_or_tumour_volume_scan_order.csv:17
  "tumor volume" OR "tumour volume",pmc,PMC13534483,10.1038/s41467-026-76293-x,2026,
  (timestamp),scanner_acceptances
```

Query, verbatim from the run record:

```
JOURNAL:"Nature Communications" AND ("tumor volume" OR "tumour volume")
  AND HAS_FT:Y AND HAS_SUPPL:Y
sort   P_PDATE_D desc      budget 35      hit_count 2561
```

*(That freeze file is named after the query rather than the `--tag`, because
this arm was already running when the tag bug was found mid-campaign. The
record is the record; it is not renamed after the fact.)*

## Step 2 — what the scanner said, which is a triage verdict and not a fact

```
file   41467_2026_76293_MOESM6_ESM.xlsx
sheet  Supplementary Fig. 8b.
       layout=wide-T   n_animals=41   n_points=9   fold=2.7   hdr=itv
```

`hdr=itv` means the header matched all three profile patterns — subject id,
covariate and value. That is the strongest evidence class this tool reports,
and **it is still only evidence about headers.** 48% of accepted sheets carry
no header evidence at all.

## Step 3 — verify at the sheet. What a human read, and what it changed

| | scanner | verified by reading |
|---|---|---|
| animals | 41 | **41** — and they are **5 arms**, which the scanner cannot see |
| arms | *not reported* | NTC **9**, VPS45g1a 8, RBSNg2a 8, CMTR2g1a 8, NF2g1a 8 |
| covariate grid | `31, 34, 38, 41, 44, 48, 51, 56` (8) | `0, 31, 34, 38, 41, 44, 48, 51, 56` (**9**) |
| model | *inferred from the query* | **MDA-MB-231**, from the paper's Methods |
| control arm | *not reported* | **NTC**, expanded from the paper, not from the sheet |

The count was right. **The structure was invisible**, and the structure is what
decides whether the rows are usable: an arm label, a control, and the fact that
`Mouse #1` means five different animals.

The scanner also drops the day-0 column, so its `fold=2.7` is day 31 → day 56.
Nothing is wrong with that — but a fold quoted from triage and a fold computed
from the built CSV are two different numbers, and this is why.

### The paper's claim against the actual count

> "MDA-MB-231 cells transduced with the endogenously activated targets of CRISPR
> lentiSAMv2 cloned constructs (1 sgRNA/gene) … 2 × 10⁶ cells/mouse were
> inoculated into the MFP of NSG female mice (**n = 8-9 mice/group**). Primary
> tumor volumes were assessed regularly using the formula:
> [4/3 × π × (length/2) × (width/2)²]. The injected mice were euthanized on
> **day 56** of inoculation."

Counted by hand: **9 + 8 + 8 + 8 + 8 = 41**. The paper's range is correct, and
the data settles what the range leaves open — NTC is the group of 9. The grid
ends at day 56, as the Methods say. No disagreement to report, which is itself
worth reporting: that is only legible because both numbers are printed.

### What a human resolved that the paper does not state

Four items, in the builder's docstring, where they belong. The load-bearing one:

> **`Mouse #1` is not an identifier.** The column labels restart at `Mouse #1`
> inside every arm. Key on the sheet's own label and five mice fuse into one —
> the build emits 9 animals instead of 41, silently, with a plausible CSV.

## Step 4 — the builder

`example/build_mdamb231_crispra_v1.py`, from `templates/builder.py`.

**From a fresh clone this needs the supplementary bundle first**, because
`si_cache/` is gitignored and 18 MB of publisher bytes are not this repo's to
redistribute:

```bash
python -c "from unpool import scan; print(scan.fetch('PMC13534483'))"
#   -> si_cache/PMC13534483.zip
python example/build_mdamb231_crispra_v1.py
```

That round trip was run for this report, not assumed: the bundle was moved
aside, the builder correctly refused with the wall named, the fetch above
re-downloaded it from Europe PMC, and the member's `sha256` came back
**identical to the pin** — after which the build produced a CSV with the same
`sha256` as before. The provenance chain closes against the publisher today.

```
$ python example/build_mdamb231_crispra_v1.py
  single-source guard: OK -- 1 (model, study) keys in …mdamb231_crispra_v1.csv,
                       0 span more than one source
  reserved-unit guard: NOT RUN -- no manifest configured. … THIS IS NOT A PASS.
wrote …/example/corpus/mdamb231_crispra_v1.csv: 369 rows, 41 subjects, 1 (model, study) key(s)
    CMTR2g1a   n=8
    NF2g1a     n=8
    NTC        n=9   CONTROL
    RBSNg2a    n=8
    VPS45g1a   n=8
```

It **refuses** rather than adapts. `_VERIFIED_N = 41`, the 9-point grid, the
per-arm sizes and the workbook's sha256 are constants; a re-download that
disagrees with any of them stops the build. The guard runs *before* the file is
written, so a bad corpus is never on disk to be reported on.

Schema, which is the guards' schema and not a choice:

```
animal_id;model;study;arm_label;role;source;days;volumes
MDA-MB-231:NTC:1;MDA-MB-231;MDA-MB-231-CRISPRa-MFP;NTC;control;Galal-NCOMMS76293;31;167.42
```

### Those constants were verified to refuse, not assumed to

A `_VERIFIED_N` that has never rejected anything is decoration. Each constant
was corrupted in a throwaway copy and the build re-run:

| corrupted | result |
|---|---|
| `_VERIFIED_N` 41 → 40 | `REFUSED  41 subjects, verified 40` |
| workbook `sha256` | `REFUSED  … the publisher's file changed under this build` |
| `_VERIFIED_ARMS` NTC 9 → 8 | `REFUSED  arm sizes [… ('NTC', 9) …], verified [… ('NTC', 8) …]` |
| `_VERIFIED_GRID` day 31 → 30 | `REFUSED  covariate grid …, verified …` |

Four for four, exit 1, each naming what disagreed. And the build is
byte-reproducible: two runs from a deleted output give the same CSV,
`sha256 3b34c22d520cdf5a6071dc6e2b76c5e987a7e6275f69987324bc5b5279527b14`.

*(The first attempt at this table measured nothing: the throwaway copies
resolved `SRC` relative to themselves, so all four "refusals" were the
missing-input wall rather than the constant under test — a wall is not a
result, protocol rule 10. The table above is the re-run with the path pinned.)*

## Step 5 — the guards, on that output

```
$ UNPOOL_CORPUS=example/corpus UNPOOL_OUT=example/records \
  unpool guard example/corpus/mdamb231_crispra_v1.csv
  single-source guard: OK -- 1 (model, study) keys, 0 span more than one source
  reserved-unit guard: NOT RUN -- no manifest configured. … THIS IS NOT A PASS.
  record: example/records/guard_mdamb231_crispra_v1.json          exit 0

$ … unpool fingerprint self-scan
  corpus: 41 curves indexed, 41 distinct fingerprints
  identical curves within one source : 0
  fingerprints spanning TWO SOURCES  : 0  (registered reference: 0)
  record: example/records/fingerprint_self-scan.json              exit 0

$ … unpool fingerprint check example/corpus/mdamb231_crispra_v1.csv
  every corpus file was excluded: 1 present, 1 excluded
  (mdamb231_crispra_v1.csv). Nothing was compared -- this is NOT a pass.
                                                                 exit 1
```

**Read that third one carefully, because it is the most useful line in this
report.** The corpus holds one file; `check` excludes the file you hand it
(otherwise every animal fingerprints itself); nothing is left to compare
against. It could have printed `AXIS 3 PASSES`. It refuses instead, because a
comparison against an empty set is not a pass (protocol rule 11).

The two records that *were* written say what they checked and what they did
not. `reserved_units` is `"state": "NOT RUN", "manifest": null` — a first-class
state, not an omission. Nothing here is reserved, so nothing was screened, and
the record says so rather than staying silent and reading like a pass.

### And a positive control, because a guard that never fires proves nothing

The same 41 curves, relabelled to a different `source`, handed back to axis 3:

```
$ unpool fingerprint check reexport.csv        # source column rewritten
  AXIS 3 HIT on 41 animal(s) -- ingestion STOPS until this is explained
    MDA-MB-231:CMTR2g1a:1 == [('Galal-NCOMMS76293', 'MDA-MB-231', 'MDA-MB-231:CMTR2g1a:1')]
    …                                                            exit 1
```

41 of 41. The check works, and now that is a statement with a run behind it.

---

## What this example does NOT establish

* **It is one paper.** It shows the path is connected and every step's real
  output. It measures nothing about recall or precision — those are `15/15`
  (tuning set) and `6/15` (V2, unbiased), and this example does not move either.
* **It is the clean case.** The sheet has explicit arm banners, explicit mouse
  columns, an explicit day row, a complete rectangle and no attrition. It was
  chosen for that. A messier sheet costs more at step 3, which is where all the
  human time in this pipeline actually goes.
* **Axis 3 is an identity check.** The self-scan passed over a corpus of one
  file. A re-export that truncates the series, rescales the units or drops one
  subject does not match and is not ruled out — the record carries that list
  inline under `does_not_catch`.
* **The reserved-unit screen did not run.** See above. It is not a pass.
