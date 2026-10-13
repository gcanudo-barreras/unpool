# Measurements

Moved verbatim from the README, which had grown to 439 lines. Nothing here was
re-measured when it moved. `docs/FIGURES.md` is the authority on any number:
it carries each one beside the configuration and population it was taken at.

## How the gate got to green

Verified from a clean clone, which is the first thing anyone does
and had not been done since V4: `git clone`, `pip install -e .`,
`fixtures/fetch.py`, `tests/test_recall.py` → **17 files fetched automatically,
RECALL 15/15, negative control intact**. Before that run the manifest named 14
files while the ground truth named 29, so the headline recall figure was **not
reproducible by anyone but its author** (`docs/VALIDATION.md`, V15).

The gate is green, and it took acquiring a real negative control to get there.
The old one was a file transcribed by hand into this project's own column
names, so the rule it was meant to test was only ever tested against headers we
had written ourselves. Its publisher serves no data file at all, so it could
not simply be swapped.

The replacement is publisher bytes: `10.1172/jci174092`, sheet
`Fig. 7C_Tumor_growth`, which is `Weeks of treatment` × `Average tumor volume /
SEM / Number of mice` per arm — longitudinal group means written by its own
authors, which the scanner must reject and does.

It is addressed **by sheet**, because that workbook has 103 of them and the
scanner accepts 6. A file-level control there would answer a different question
by accident.

## Profiles, and how little they do

A profile declares four column patterns and two floors, in TOML, with the
evidence for each clause written beside it.

**Measured, because the claim was worth checking: swapping the profile barely
changes what the scanner accepts.** Over the 22 cached fixtures, 368 sheets:

| | sheets accepted |
|---|---|
| `tumor_volume` | 115 |
| a NULL profile, every pattern impossible | **112** |

The column patterns decide **3 sheets out of 115**. The other 97% is decided by
structure alone — a numeric grid with a regular ordinal axis — which no profile
field touches.

And the three are not arbitrary. They are exactly the **flat long-format text
files** (`ID,Time,Vol` and `ID Time Observation`). So:

- **Long format (CSV/TSV): the profile is everything.** Without it all three are
  missed.
- **Spreadsheets (wide or transposed): the profile is nothing.** 112 sheets,
  identical either way.

### The part that DOES adapt the tool, and it had to be built

The column patterns are not where a data type lives. The **response shape** is,
and it used to be hardcoded inside the structural test where no profile could
reach it: *at least 60% of subjects must rise, median fold at least 1.5*.

Those are tumour-growth assumptions. Body weight does not rise 1.5×, so
`body_weight` could not match a weight block at all — it returned the **tumour**
block of whatever workbook it was pointed at, the same sheet and the same
`fold=8.0`, under a body-weight label. It was not a weak profile. It was
returning the wrong data type.

A profile now declares its own response:

```toml
[response]
direction = "stable"      # increase | stable | decrease
fold_lo = 0.6
fold_hi = 1.6
min_consistent = 0.0
```

Measured after the change, on three files where a weight block is known to
exist:

| file | `tumor_volume` | `body_weight` |
|---|---|---|
| thsd7b | `n=9 fold=8.0` | `n=7 fold=1.2` |
| 4t1luc2 | `n=7 fold=1.5` | `n=13 fold=1.3` |
| aldh1a1 | `fold=9.9 / 25.8 / 6.8` | `fold=1.1 / 0.8 / 1.1` |

Different blocks, weight-like folds, where before the two profiles returned
byte-identical verdicts. `tumor_volume` is unchanged throughout: the same 115
sheets, gate still 15/15.

So the honest split is: **column patterns adapt almost nothing (3 sheets of
115), response shape adapts a great deal** (`body_weight` accepts 95 sheets, 25
of which `tumor_volume` never sees).

It also explains the IC50 false accept in `docs/EVAL.md`: not an edge case, the
dominant mode. The scanner takes numeric matrices with ordinal structure and
mostly ignores the headers — on that plate it took a row of measurements as the
time axis.

Shipped profiles:

- `tumor_volume` — the only one with a measured recall figure
- `profiles/contributed/rotarod_latency.toml` — **a non-oncology profile
  built by an outside user in under an hour**, which found a real per-animal
  rotarod dataset on its first live run. It also shows the limit: 75% of its
  candidates carried no header evidence at all, against 48% for
  `tumor_volume`. A new profile mostly rides the same structural detector.
- `body_weight` — **the mechanism was broken and is now fixed**, see below. No
  measured recall, and roughly three quarters of what it accepts is also
  accepted by `tumor_volume`, because a treated tumour arm that barely grew
  falls inside its stable band.

**There is no `dose_response` profile.** One shipped for a day and was deleted
rather than published: the scanner mis-parses IC50 plates at the structural
level. On the one plate we could check it took a row of measurements as the
time axis, reporting `fold=932.1`. A profile field cannot repair a bad parse,
and shipping a profile that fails the only file we can verify it against is the
thing this repository exists not to do.

### What was done about it

Every accept now carries `hdr=`, naming which profile patterns its headers
actually supported — `i` subject id, `t` covariate, `v` value, or
`NONE-shape only`:

```
LLC_sc_CCSB.txt         long    n=20  hdr=itv
ncomms71144_aldh1a1     wide    n=51  hdr=NONE-shape only
pone0288380_4t1luc2     wide-T  n=12  hdr=tv           <- known false positive
```

**48% of accepted sheets are `NONE-shape only`.** The accept decision is
unchanged — same 115 sheets before and after — but an accept made on shape
alone is now visibly an accept made on shape alone, which is what a reader
needs before trusting it.

### Why the evidence is reported and not enforced

Making it a gate was measured before being rejected:

| rule | recall | gate |
|---|---|---|
| report only (shipped) | 15/15 | PASS |
| require any evidence | 12/15 | PASS, *exactly* on the 0.80 threshold |
| require `t` **and** `v` | 5/15 | FAIL |
| require all three | 4/15 | FAIL |

Requiring evidence costs 3 of 15 positives, lands precisely on the threshold —
a rule that scrapes its own gate is a coin, not a rule — and **does not remove
the known false positive**, which carries `hdr=tv`. It buys nothing it was
supposed to buy.

Nothing was tuned in response to any of this. Widening a pattern to fix what a
measurement just exposed, on the fixtures that exposed it, is how a tuning set
becomes a score (`docs/PROTOCOL.md`, rule 9).

## Scope, and the ceiling that sets it

Tables, not figures — no curve digitisation. Open access only; the fetcher
returns `not_open_access` and that is a stop. Attribution travels with the data.
Individual patient data from clinical trials is out of scope.

**`.pdf` and `.docx` supplements are not opened, and that is a measured decision
rather than a gap.** Over 206 supplementary documents already in the fixture
cache, parsed with `pdfplumber` and with a stdlib reader for Word:

| | documents | with tables | tables | substantial | mostly numeric | per-subject |
|---|---|---|---|---|---|---|
| `.docx` | 117 | 66 | 239 | 82 | 36 | **0** |
| `.pdf` | 89 | 50 | 454 | 22 | 4 | **0** |

693 tables, none of them per-subject longitudinal data. The one acceptance was
a false positive — a cell-culture medium composition table, amino acids against
concentrations, scored `n=26 fold=22.2`.

What these documents actually hold: primer sequences, antibody catalogues,
bacterial strains, microbiome abundances, gene lists, statistical parameter
tables, patient characteristics. Real tables, correctly extracted, and none of
them a growth series.

### WHERE YOU LOOK MATTERS MORE THAN ANYTHING ELSE IN THIS REPOSITORY

> **Earlier measurement.** The table below is the first screening pass, n=50 per row. The README's journal table (`studies/journal_yield.py`, n=100) supersedes it for every journal row; the *general population* row has not been re-measured and is still this one.


The 10% figure above is a population average, and treating it as a ceiling was
wrong. Measured on unselected samples of 50 papers each, same query, same
scanner:

| | hits | tabular supplement | scanner accepts |
|---|---|---|---|
| **Nature Communications** | 2,561 | **90%** | **80%** |
| Nature portfolio, wider | 4,433 | 66% | 34% |
| PLOS ONE | 2,410 | 28% | 12% |
| general population | 87,933 | 10% | **0%** |

**80% against 0%.** Mining the general literature is close to worthless; mining
a journal with a Source Data policy is productive. Nature portfolio titles have
required Source Data files since around 2016 and they are spreadsheets by
convention, which is the whole mechanism.

So target the journal. `unpool mine --journal "Nature Communications"` costs nothing
and is the single highest-yield thing in this tool.

Two honest caveats. "Accepts" means scanner acceptances, not verified cells —
apply the measured precision (6 of 15) and the 71% becomes roughly **28%** of
papers yielding something real, or 14–45% across that figure's 95% interval. And this measures where per-animal data is
*recoverable*, not where it *exists*: the general population may hold as much of
it, unreadably, in figures.

The caveat that keeps this honest: `extract_tables()` finds tables with
detectable structure. A table rendered as an image would be missed. The claim is
"no per-subject table is recoverable from these documents by table extraction",
not "no such table exists in any PDF anywhere."
