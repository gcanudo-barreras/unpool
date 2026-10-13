# Out-of-sample validation

Everything measured so far was measured in-sample. `15/15` is a recall figure on
the very files the instrument was re-tuned against, twice, and it has been
quoted in every run footer this tool has ever printed. **No out-of-sample recall
figure exists.** This document is the attempt to produce one, and it registers
what it expects before it looks.

Studies are numbered in the order they were registered. Each registration
was committed before its measurement in the development history, which the
author keeps; amendments and post hoc analyses are labelled where they occur.

---

## V1 — recall out of sample, from the campaign's own rejects

**Registered, before any reject was opened.**

### The test set, and why it is the right one

The first real campaign scanned 50 papers across two journals and **rejected 13
of them** with *"no per-animal table found"*. Those 13 are the only population
available that the scanner has judged negative and that nobody has checked.

This is what a recall test needs and what the tuning set can never be: to
measure recall you have to find per-subject data by some route other than the
scanner, and then ask whether the scanner finds it too. Auditing its own
rejects does exactly that, and the files are already on disk.

A 14th paper, `PMC13550616`, returned `ERR TimeoutError`. **It is UNMEASURED,
not rejected**, and it is excluded from the denominator. A fetch that failed is
not a judgement (protocol rule 10).

### The predictions

> **P1** — **1 or 2 of the 13 are false negatives.** The scanner's measured
> in-sample recall is at ceiling and its known gaps are structural rather than
> semantic, so most rejects should be genuine.
>
> **P2** — **the false negatives that do appear will be layout failures, not
> content failures**: side-by-side tiled day blocks, or a day value living in
> header *text* rather than in a data cell. Both are already named in the ground
> truth as known structural gaps.
>
> **FALSIFIER of P1**: **4 or more false negatives.** Then out-of-sample recall
> is materially below the in-sample figure, `15/15` is not representative of
> anything, and every run footer this tool has printed overstates it.
>
> **FALSIFIER of P2**: a false negative whose sheet is an ordinary long or wide
> per-animal table that the scanner simply missed. That would mean the gap is in
> the judgement rather than in the layout handling, which is a much worse defect
> than a known parser limitation.

### The stop

**No regex, floor or branch is edited in response to whatever this finds.**
Every false negative is written down with the header or layout that defeated the
scanner, and any fix is a later pass measured on the whole set. Tuning on the
files that exposed a gap, immediately after discovering the benchmark was
weaker than believed, is protocol rule 9 — and rule 9 exists because that is
exactly the moment the temptation arrives.

### Method

Every tabular supplement of each of the 13 is opened and every sheet examined —
not the first accepting sheet, every sheet. Stopping at the first verdict per
file is the error that made an earlier grading script miss a real per-animal
block two sheets past the one it stopped at.

### Result — BOTH PREDICTIONS CONFIRMED, AND THE AUDIT FOUND A BIGGER DEFECT THAN THE ONE IT WAS LOOKING FOR

**The denominator is 9, not 13.** Four of the thirteen "rejects" were never
judged at all: `scan_one` skipped a tabular member over 40 MB with a silent
`continue`, and the paper was then reported as *"no per-animal table found"* --
a statement about what a file contains, made without opening it.

| | |
|---|---|
| rejects reported by the campaign | 13 |
| never read (member over 40 MB, silently skipped) | **4** |
| fetch failed (timeout) | 1, already excluded |
| **genuinely judged** | **9** |

`PMC13486681` is the sharp case: its skipped 56.6 MB member holds **10 sheets
the scanner accepts**. The campaign reported that paper as containing no
per-animal data. All four size-skips ended as rejects; no accepted paper was
affected.

### The nine, audited sheet by sheet

| paper | contents | verdict |
|---|---|---|
| 4 papers | no tabular supplement at all | correct by construction |
| `PMC13572498` | DESeq2 table, `ensembl_gene_id` / `log2FoldChange` | correct |
| `PMC13408595` | gene table, `Gene` / `pvalue` | correct |
| `PMC13538470` | DNA sequences | correct |
| `PMC13350917` | 4 rows, below the floors | correct |
| **`PMC13538391`** | `Group/volume \| Day1 \| Day4 \| Day7 \| Day10 \| Day14`, rows are individual animals | **FALSE NEGATIVE** |

**P1 CONFIRMED**: 1 false negative, against a predicted 1-2.

**P2 CONFIRMED exactly as written**: it is a layout failure, and it is the
named one -- the day value lives in header TEXT (`Day1`) rather than in a data
cell. The scanner reads days as numbers and `Day1` is not one.

### What this is and is not

**1 false negative in 9 judged rejects.** That is the fact. Turning it into a
recall percentage needs the true-positive count, which only V2 produces, so no
percentage is quoted here.

And the decomposition matters more than any single figure:

* **scanner recall** — the judgement itself missed one paper of nine, on a
  known layout gap.
* **pipeline recall** — `mine.py` additionally lost `PMC13486681`, which the
  scanner would have accepted ten times over. That is not a judgement failure
  at all, and it would have been invisible without this audit.

A tool can have a good instrument and still lose data in the plumbing around
it. Nothing in the test suite could see this: the gate feeds files to `judge`
directly and never goes through `scan_one`.

### The stop held

No regex, floor or branch was edited. `Day1` remains unparsed and is written
down here instead. The 40 MB cap was NOT raised either -- it is a real
trade-off and changing it in the same breath as discovering it would be the
same error in a different costume. What changed is only that a size refusal
now REPORTS itself as one: *"this paper was never read, it was not rejected"*.

---

## Still to run

## V2 — precision, measured on an unbiased sample. **6 of 15.**

**Sample drawn before any sheet was opened**, with the seed written into the
artifact: `random.seed(20260917)`, 15 of the 36 accepted papers, excluding the
4 previously verified because those had been picked as the most suspicious and
pooling them would import that bias. `runs/v2_sample.json` holds the seed and
the draw.

Each paper's best sheet was opened and read.

| | |
|---|---|
| **TRUE** — per-animal longitudinal tumour measurements | **6** |
| FALSE | 9 |
| **precision** | **6/15 = 40%** |

**The nine false accepts, by what they actually were:**

| paper | what the sheet holds |
|---|---|
| `PMC13096527` | TCGA expression quantiles by cancer type |
| `PMC13402817` | per-mouse series, but ~1000x disparity between arms — bacterial load or flux, not volume |
| `PMC13408951` | western blot densitometry, ACLY/GAPDH |
| `PMC13470199` | endpoint tumour **weight**, one value per animal — the animal INDEX read as a time axis |
| `PMC13503815` | replicate measurements, no time axis |
| `PMC13507113` | panel labels only; the scanner assembled scattered blocks |
| `PMC13547291` | `mean_fraction / sd_fraction` — aggregate, in-vitro migration |
| `PMC13558603` | `% colocalization` imaging quantification |
| `PMC13562587` | survival, one row per mouse with days elapsed — time-to-event, not repeated measures |

### What this does to the headline number

The standing figure was **2 of 6 (33%)**, one batch, measured once, by hand.
This is **6 of 15 (40%)**, unbiased, seed registered in advance. **The old
figure survives contact with a larger sample**, which is not the usual outcome
when a small hand-measured number is retested.

Combined honestly: 8 of 21 across both batches, **but do not pool them** — the
first six and the four suspicious ones were not randomly drawn. 6/15 is the
number to quote, and its 95% interval is roughly 20-64%. Fifteen items is
enough to confirm "about a third" and not enough to distinguish a third from a
half.

### The pattern in the failures, which is new

Seven of the nine are **large numeric matrices from a different discipline** —
transcriptomics, proteomics, imaging quantification, in-vitro migration — that
fall into the `wide` path because they carry a monotonic ordinal axis. This is
not a set of edge cases. It is what a Source Data workbook contains *besides*
the growth curves, and the scanner cannot tell those apart from what it wants.

Two failures are subtler and worth naming separately: an endpoint **tumour
weight** table whose animal index (1, 2, 3, 4) was read as the time axis, and a
**survival** table whose days-elapsed column looked like a covariate. Both are
genuinely per-animal, genuinely about tumours, and neither is a growth series.

**V3 — the guards, run in anger.** `guard.py` and `fingerprint.py` have never
been executed on real input; their only exercise is the pair of corpora named
in their own docstrings. 36 new papers against an existing 29-source corpus is
where duplicate curves appear — a previous fingerprint scan found 30 inside a
corpus that had been assembled carefully, one source at a time.

**V4 — clean clone.** `git clone`, `pip install`, `fixtures/fetch.py`,
`tests/test_recall.py`, in an empty directory. It is the first thing anyone who
downloads this will do and it has never been tested. Three bugs surfaced today
the first time `mine.py` was run end to end; the front door carries the same
risk.

---

## V5 - discipline-signature rejection. REGISTERED, BEFORE ANY RULE IS WRITTEN

V2 found that **seven of nine false accepts are large numeric matrices from
another discipline** - TCGA quantiles, western densitometry, imaging
colocalisation, in-vitro migration with its own `sd` columns, a dose ladder.
They are not subtle. They carry literal signatures.

The hypothesis is that **explicit rejection rules beat a learned model here**,
because the thing to detect is a vocabulary rather than a pattern, and because
the labelled data a model would need does not exist (about 40 verified items).

### The rules, declared before they are measured

Reject a sheet when its header region carries any of:

1. **transcriptomics** - `ENSMUSG|ENSG|ENSRNO`, `log2 fold change`, `padj`,
   `baseMean`
2. **blot densitometry** - a housekeeping protein as a ROW label: GAPDH,
   ACTIN, TUBULIN, VINCULIN, or an `X/GAPDH` ratio label
3. **distribution columns** - `q1` and `q3` together, or `mean_`/`sd_` prefixed
   column names (not the same as `AGG`, which matches free text)
4. **survival** - `days elapsed`, `time to event`, `censor`, or `survival` as a
   column header
5. **imaging quantification** - `colocali`, `fluorescence intensity`,
   `mean gray`, with no covariate match anywhere
6. **geometric axis** - the candidate axis is a geometric sequence (successive
   ratios within 10% of a constant >= 1.8), which is a dilution series and not
   a calendar

### Predictions

> **P1** - the rules reject **at least 5 of the 9** V2 false accepts.
>
> **P2** - they cost **at most 1** of the 15 recall items in the fixture gate.
>
> **FALSIFIER of P1**: 4 or fewer caught. The signatures are less separable
> than V2 made them look and a rule-based approach is the wrong shape.
>
> **FALSIFIER of P2**: 2 or more true positives lost. The rules would then be
> trading recall for precision rather than removing a distinct population, and
> they do not ship at that price.

### The stop

**Measured on the whole labelled set - 15 V2 papers and the 28 fixtures - in
one pass, before any rule is adjusted.** If a rule misfires it is REPORTED and
the whole set re-measured after the change, never tightened against the item it
missed. Rule 9 applies to rejection rules exactly as to acceptance patterns,
and a rejection rule tuned to the false positives that inspired it is the same
error wearing the opposite sign.

### Result - P1 FALSIFIED. The rules do not ship as a gate.

| | | |
|---|---|---|
| **P1** | caught **4 of 9** false accepts | **FALSIFIED** - the falsifier was "4 or fewer" |
| **P2** | lost **1 of 15** fixture recall items, and 1 of 6 V2 true positives | held, at the limit |

Registered outcome honoured: at 4 of 9 they do not ship as a rejection.

**They would have improved precision from 6/15 (40%) to 5/10 (50%)** at a cost
of one true positive in six. That is not a bad trade and it is not the trade
that was registered, and the point of registering a bar before measuring is
that it still binds when the result lands just under it.

### What the five misses were, which is the useful part

| missed | why no signature fired |
|---|---|
| `PMC13402817` | per-mouse series with a ~1000x disparity between arms - bacterial load or flux. No vocabulary at all, only an implausible magnitude |
| `PMC13470199` | endpoint tumour **weight**; the animal INDEX (1,2,3,4) read as a time axis. Needs a different rule entirely: a covariate that is small consecutive integers starting at 1 |
| `PMC13503815` | replicate columns, no time axis. Nothing to match |
| `PMC13507113` | panel labels only; the scanner assembled scattered blocks |
| `PMC13558603` | **`% colocalization` - the imaging rule SHOULD have caught this.** It did not, because that rule carries an exception for sheets with a covariate match, and this sheet has a day-like cell somewhere. My own exception let it through |

The last row is the honest one: one of the five misses is a rule defeating
itself, not a missing signature.

### And the survival rule is actively bad

It fired on **three** sheets: one true false positive (`PMC13562587`, a
time-to-event table) and **two genuine positives** (`ebos_data_breast`,
`PMC13542117`) whose workbooks contain a survival block *beside* the growth
data. Sheet-level matching is too coarse for it - a workbook that reports
survival alongside tumour volume is normal, not suspicious.

That single rule accounts for both recall losses. Removing it would leave 3 of
9 caught at zero recall cost, which is a different and weaker proposition.

### What ships instead

The signatures are **reported, not enforced** - the same resolution as header
evidence, and for the same reason. A sheet carrying a discipline signature is
ranked last in the worklist rather than dropped, so the ordering reflects it
and no recall is spent. A revised rule set needs its own registration, a rule
for the consecutive-integer axis, a fix for the imaging exception, and the
survival rule either scoped below sheet level or abandoned.

### V5 addendum - the index-axis rule, measured after the fact

A sixth predicate, written after V5's result because the endpoint-weight miss
suggested it: **an axis of 1, 2, 3, ... is a row number, not a calendar.**

| | |
|---|---|
| positive fixtures carrying such an axis | **0 of 15** |
| V2 false accepts caught | **1 of 9** (`PMC13507113`) |
| V2 true positives lost | **0 of 6** |

A free catch, and **it does not ship as a gate either**, for a reason that has
nothing to do with the numbers: the rule was derived from looking at V2's
failures and then measured on V2. Zero cost on the set that inspired the rule
is not zero cost. It labels, like the others, and a real measurement of it
needs items it has never seen.

It also did not catch the case that suggested it - `PMC13470199`'s endpoint
weight table, whose axis on the sheet the scanner chose is not a clean 1..N.
The rule a miss suggests is not always the rule that catches it.

---

## V6 — the whole path, end to end. REGISTERED, BEFORE THE BUILDER IS WRITTEN

Three of six people who tried this repo asked for the same thing: nobody has
seen `mine -> verify -> builder -> guard -> CSV` run once, on one real paper,
all the way through. Phase 2 of the README is a promise, and a promise is not a
check that ran (rule 11).

Building it is not a documentation task. It is the first execution of a path
whose two halves were written months apart and never joined, so it is
registered as a measurement, with what it expects to break written down first.

### What is already known by READING, not by running

`templates/builder.py` emits `subject_id;model;study;source;covariate;value`.
`guard.py:check_file` requires `model,study,source,animal_id`.
`fingerprint.py:_load_candidate` requires `animal_id,days,volumes`.
`templates/_raw_example_builder.py` — the initial import, which predates
the template — emits `animal_id;...;days;volumes`, which both guards accept.

So the generic template and the guards disagree on the name of every column
that matters. That much is legible in the source. What happens when a builder
written from the template actually calls the guard is not, and that is the
prediction.

### The predictions

> **P1** — a builder written strictly from `templates/builder.py` is REFUSED by
> `guard.py` and by `fingerprint.py check`, on column names alone, before
> either guard looks at a single value.
>
> **P2** — the refusal inside the builder is NOT clean. `main()` calls
> `assert_buildable(rows)` directly, `single_source_violations` subscripts
> `r["animal_id"]`, and the template's handler catches only `BuildRefused` and
> `CorpusGuardRefused`. So the builder dies on an uncaught `KeyError:
> 'animal_id'` with a traceback, not on the readable refusal the template was
> written to produce.
>
> **P3** — the scanner's `n_animals=41` for `PMC13534483`, sheet
> `Supplementary Fig. 8b.`, is not 41 animals of one experiment. It is an
> assembled total across arms or panels laid out side by side, and the real
> per-arm counts are smaller.
>
> **FALSIFIER of P1**: either guard accepts the template's schema.
> **FALSIFIER of P2**: any clean exit — a `CorpusGuardRefused` with a readable
> message, or a non-zero exit without a traceback.
> **FALSIFIER of P3**: the sheet carries 41 subject columns belonging to one
> arm on one covariate grid, and the scanner's count is simply right.

### The stop

If P1 and P2 hold, **the guards' schema is the fact and the template is the
defect** — two shipped artifacts contradicting each other, which is not the
same thing as rule 9. Rule 9 forbids widening the instrument's JUDGEMENT to
admit the file in front of you; nothing here touches `scan.py`, no pattern, no
floor, no threshold. What may be edited is the template's column names, once,
to the names the guards have required all along, with this registration as the
reason.

What may NOT be edited either way: `_VERIFIED_N` or the covariate grid, to make
a build pass. If the count disagrees with the paper, the count wins and the
disagreement goes in the docstring (rule 5).

### Source selection, decided before the sheet was opened

`PMC13534483` is **CC BY-NC-ND**; `PMC13351075` and `PMC13408345` are **CC BY**.
The builder ships as a script and re-derives its CSV, but `example/` ships the
derived rows, and ND is a real question about a derivative rather than a
theoretical one. Recorded here before it could be settled by which sheet turned
out to be prettiest.

### Result — P1 and P2 CONFIRMED, P3 CONFIRMED WITH A CORRECTION WORTH MORE THAN THE PREDICTION

**P1 — both guards refuse the template's schema.** Measured by writing a
builder strictly to `templates/builder.py` and handing its output to each:

```
guard.py          …/p1p2_out.csv is missing column(s) ['animal_id']
fingerprint.py    expected a ';'-delimited corpus-schema CSV with at least
                  animal_id/days/volumes; got ['subject_id', 'model', 'study',
                  'source', 'covariate', 'value']
```

**P2 — the refusal is not clean, exactly as registered.**

```
  File "…/p1p2_template_shaped.py", line 52, in main
    assert_buildable(rows, label=OUT)
  File "C:\proyectos\unpool\guard.py", line 96, in single_source_violations
    per[key][str(r["source"]).strip()].add(str(r["animal_id"]).strip())
KeyError: 'animal_id'
```

An uncaught `KeyError` escaping the template's own
`except (BuildRefused, CorpusGuardRefused)`. So the failure mode for anyone
following the template was a traceback out of a library they did not write,
rather than the readable refusal the template was built to produce.

**P3 — confirmed, and the correction matters.** `n_animals=41` is **5 arms
side by side** — NTC 9, VPS45g1a 8, RBSNg2a 8, CMTR2g1a 8, NF2g1a 8 — sharing
one 9-point grid. But the count of ANIMALS is right: there really are 41.

What the scanner gets wrong is not the number, it is that **the number is not
about one experiment.** Nothing in a candidates row says "these 41 animals are
five groups, one of which is the control". That is invisible to triage and it
is the whole of what step 3 recovers — an arm label, a control arm, and the
fact that `Mouse #1` names five different mice.

A second, smaller gap from the same sheet: the scanner's grid is `31..56`, 8
points. The sheet carries 9, including a day-0 column of zeros. So a `fold`
quoted from triage and a fold computed from the built CSV are different
numbers, for a reason nothing printed.

### What was fixed, and what deliberately was not

`templates/builder.py` now emits `animal_id;model;study;source;days;volumes`,
which is the schema `guard.py` and `fingerprint.py` have required since the
initial import, and which `README.md` already documented correctly. The template
was the lone outlier. Nothing in `scan.py` was touched — no pattern, no floor,
no threshold — and the instrument's judgement is byte-identical.

**NOT fixed, and named here so it is not mistaken for an oversight:** `days`
and `volumes` are tumour vocabulary standing in for "covariate" and "response".
A rotarod builder must either put latency in a column called `volumes` or
rename it and lose axis 3. Generalising the guards is a real change to two
shipped refusals and it needs its own registration, not a paragraph at the end
of somebody else's pass.

### And the thing this exercise was not looking for

`fingerprint.py check` on a corpus holding only the file being checked refuses:

```
every corpus file was excluded: 1 present, 1 excluded. Nothing was compared --
this is NOT a pass.
```

That is correct and it is rule 11 working in the case that matters most — a
first-time user's corpus has exactly one file in it, so the very first time
anyone runs axis 3 for real, the honest answer is "nothing was compared". It
would have been easy for that path to print `AXIS 3 PASSES`.

Verified firing, on the same 41 curves relabelled to a different `source`:
**AXIS 3 HIT on 41 of 41 animals.** A guard that has never fired is a guard
nobody has tested.

### What V6 is not

One paper. It establishes that the path is connected and shows every step's
real output. It moves no recall or precision figure, and it says so where the
example lives.

---

## V7 — should the scope widen from tumour volume to BLI? REGISTERED, BEFORE THE SWEEP

The question asked: expand the longitudinal profile to other magnitudes, BLI
first — bioluminescence, reported as photon flux or radiance, the standard
readout for orthotopic and metastatic burden where a caliper cannot reach.

### What reading the code already settles, before any measurement

Three facts, all legible in the shipped files, and they reshape the question:

1. **`tumor_volume.toml` already carries BLI vocabulary.** Its `value` regex is
   `(volume|tumou?r\s*vol|tv\b|size|bli|flux|radiance|rtv|…)` and its own
   `description` reads *"per-subject longitudinal tumour volume (or BLI
   flux)"*. BLI was in scope from the start and nobody measured it.
2. **The response band does not exclude BLI.** `direction = "increase"`,
   `fold_lo = 1.5`, and `fold_hi = 0`, which is *no upper bound* — so BLI's
   four-to-six orders of magnitude are not what rejects it. The comment beside
   it says "a tumour can grow 50x"; flux can grow 10,000x and the band does not
   care.
3. **Column patterns decide 3 sheets of 115**, and all
   three were flat long-format text. A new profile's vocabulary is close to
   irrelevant for spreadsheets, which is most supplementary material.

So the honest prior is that a `bli_flux` profile buys nearly nothing in
acceptance, and that the real question is not detection at all.

### The predictions

Measured as a **CENSUS, not a sample** — every one of the 2,390 papers in
`si_cache/`, every member, every sheet. A timing probe put the full sweep at
about five minutes, so there is no reason to sample and no sampling bias to
argue about.

`BLI vocabulary` is fixed HERE, before the sweep, so it cannot be tuned to a
result:

    bioluminescen|luminescen|photon|p/s|radiance|total\s*flux|\bflux\b
    |\bBLI\b|IVIS|luciferase|\bluc\b

> **P1 — the vocabulary is decorative.** Removing `bli|flux|radiance` from
> `value` changes the set of accepted sheets by **at most 1** across the whole
> cache.
> *FALSIFIER: 2 or more sheets change* — then the patterns do real work for BLI
> that they do not do for anything else, and that is worth knowing.
>
> **P2 — BLI is already accepted, not missed.** Sheets carrying BLI vocabulary
> are accepted at a rate **not below half the base rate** for all sheets.
> *FALSIFIER: below half* — BLI is being systematically lost, and a profile
> would buy recall rather than a label.
>
> **P3 — the log-scale gap is real.** BLI is often published as log10(flux).
> Such a series rises from perhaps 6.0 to 8.0, a fold of **1.33**, which is
> below `fold_lo = 1.5` and is REJECTED — while the identical series in linear
> units is accepted easily. Predict **at least one** such sheet in the cache.
> *FALSIFIER: zero found* — the gap is theoretical and does not justify
> anything.
>
> **P4 — this is relabelling, not detection.** Exactly **1** of V2's 9 false
> accepts is a flux-like series (`PMC13402817`, which V2's own table calls
> "bacterial load or flux, not volume").
> *FALSIFIER: 0, or 2 or more.*

### The stop, and it is the whole point of this registration

No regex, floor, band or branch is edited in response to whatever this finds.

**And the trap, named before it can be walked into.** If the scope widens from
"tumour volume" to "tumour burden, volume or BLI", then `PMC13402817` stops
being a false accept and precision moves from **6/15 to 7/15** — *without a
single new observation*. That is not a measurement. It is the V5 error wearing
the opposite sign: there, a rejection rule was tuned against the false
positives that inspired it; here, the DEFINITION OF TRUE would be widened
against them.

Widening the scope means the precision figure is **void until re-measured on a
new unbiased sample under the new definition**, with its own seed registered in
advance. `6/15` was measured against the question "is this per-animal
longitudinal tumour volume". It cannot be carried across to a different
question and still be called the same number.

### Result — P1 and P2 CONFIRMED, P3 and P4 FALSIFIED, and the useful finding was in none of them

Census of the whole cache, one pass, no sampling: **2,390 papers, 20,330
sheets, 208 seconds.** The unit counted is SHEETS throughout.

| | | |
|---|---|---|
| **P1** | removing `bli\|flux\|radiance` moved **0 of 20,330** sheets | **CONFIRMED**, at the strongest possible value |
| **P2** | BLI-vocab sheets accepted **11.3%** (18/159) against a base rate of **12.2%** (2,487/20,330) | **CONFIRMED** — falsifier was below 6.1% |
| **P3** | genuine log10(flux) sheets found: **0** | **FALSIFIED** |
| **P4** | V2 false accepts that are BLI series: **0** | **FALSIFIED** |

**P1 is a set comparison, not a count comparison** — both verdicts were computed
for the same sheet in one pass, so two sheets swapping could not hide. Nothing
moved. The BLI vocabulary shipped in `tumor_volume.toml` since the initial import
is provably inert on every spreadsheet in the cache, which is the initial
null-profile finding holding at 177× the scale.

### P3 fell over on my own instrument, which is the more useful half

The two sheets flagged as log-scale are a Gene Ontology table and an Ingenuity
pathway table, both carrying `-log(p-value)`. They reached the BLI population at
all because the registered vocabulary contains `IVIS` **with no word boundary**,
and `IVIS` is a substring of **`division`**.

Four sheets in total matched only that way — `cell division`, `Mitochondrial
Division` — and all four were rejected anyway.

| | sheets | accepted | rate |
|---|---|---|---|
| as registered | 159 | 18 | 11.3% |
| `\bIVIS\b` corrected | 155 | 18 | 11.6% |

Both are reported. The correction cannot reach P2's falsifier (6.1%) from
either side, so the conclusion is unchanged and the defect is recorded rather
than quietly patched into the number.

**So the log-scale gap is theoretical.** It was derived correctly from the code
— a log10 series really would fold ~1.33 against `fold_lo = 1.5` — and it does
not occur. In this corpus BLI is published in linear photon flux.

### P4: it was bacterial load, and the trap I registered does not fire

V2's own table hedged: *"~1000x disparity between arms — bacterial load or
flux"*. Opened, it is bacterial load. `PMC13402817` is a microbiome/colorectal
paper, and sheet `SFig5 C` is Control ≈1.0–3.4 against `B.O` ≈1,500 over days
0/7/14 — a gnotobiotic *Bacteroides* colonisation time course.

So widening the scope to BLI would **not** reclassify a single V2 false accept,
and precision does not drift from 6/15 to 7/15. The warning registered before
the sweep stands for any future widening; it simply is not triggered by this
one. Registering it before knowing that is the only reason the statement is
worth anything.

### THE FINDING, WHICH NO PREDICTION ANTICIPATED

56 sheets carry unambiguous in-vivo BLI units (`photon`, `p/s`, `radiance`,
`total flux`, `bioluminescen`, `\bBLI\b`). **11 accepted, 45 rejected** — and
reading all 45, nearly every rejection is correct. They are endpoint
comparisons, ex-vivo organ panels, two- and three-timepoint tables, and
statistics blocks.

**BLI in this corpus is overwhelmingly an endpoint and metastasis readout, not
a dense longitudinal per-animal series.** That is a fact about how the assay is
used, not a failure of the scanner, and it is the real answer to whether the
profile should expand.

Two rejects were opened individually:

* `PMC11056319` `Fig.2d` — `Luciferase photons/sec`, days 14/25/35. **Three
  timepoints against a floor of four. A legitimate rejection** by a declared
  floor, not a defect.

* `PMC12545207` `4b-c` — **a real false negative, and a large one.** A
  402-row long-format table, `Mouse_ID | Measurement_day_post_CART_injection |
  Total_flux[photons/s]`: **51 mice, 21 timepoints.** The tool reports nothing.
  Two independent defects, both in the LONG branch, **neither BLI-specific**:

  | | |
  |---|---|
  | `IDCOL` matches 3 columns and takes the first | `Tumor_model` (col 0) instead of `Mouse_ID` (col 7) — the exact failure `subject_strict` was written for, in the one branch that does not use it |
  | `TCOL` is anchored `^` | it misses `Measurement_day_post_CART_injection` entirely and matches only `Day_tumor_relative_to_CART`, a design constant whose values are `{-5, NA}` |

  Both are the same shape: **the LONG branch commits to the first candidate
  triple and never reconsiders.** A column that matches but carries one
  distinct value is taken over a column that is the actual axis.

### What this recommends, and what it refuses to do

**Do not ship a `bli_flux` profile.** It would change nothing measurable: the
vocabulary is already there and is provably inert (P1 = 0), the response band
already admits BLI (`fold_hi = 0`, no upper bound), and BLI-vocab sheets are
already accepted at the base rate (P2). A profile is the wrong instrument for
this question, and shipping one would create the appearance of a capability
that the census says is already present.

What would buy recall is a `judge()` change — try the candidate `(id, t, v)`
triples rather than the first, and prefer a covariate column with more than one
distinct value. That is `scan.py`, it is **not** BLI-specific, it would affect
every long-format sheet in the corpus, and it needs its own registration and
its own measurement over the whole set before a line of it is written.

**Nothing was edited in response to any of this.** No regex, no floor, no band,
no branch. `PMC12545207`'s two defeating headers are written down here, which
is what rule 9 asks for and all it asks for. Gate unchanged: 15/15, negative
control intact.

### What V7 is not

The BLI population is defined by header vocabulary, which is a noisy proxy:
`luciferase`, `luminescen` and `\bluc\b` also match in-vitro reporter assays,
and `\bflux\b` matches metabolic flux. "159 BLI-vocab sheets" is not "159 in
vivo BLI datasets", and the 56-sheet hard-unit subset is the one to trust. No
sheet outside that subset was read by hand.

---

## V8 — the LONG branch takes the first candidate and never reconsiders. REGISTERED, BEFORE ANY CODE CHANGES

V7's census found a per-animal BLI dataset the tool cannot see: `PMC12545207`
sheet `4b-c`, 402 rows, **51 mice and 21 timepoints**, in clean long format:

```
Tumor_model | ... | Mouse_ID | Measurement_day_post_CART_injection | Total_flux[photons/s]
   col 0            col 7              col 8                              col 9
```

`judge()`'s LONG branch picks one column for each role with `next(...)` and
commits to it:

| role | matches | picks | should pick |
|---|---|---|---|
| `IDCOL` | cols 0, 3, 7 | **0** `Tumor_model` | 7 `Mouse_ID` |
| `TCOL` | col 4 only | **4** `Day_tumor_relative_to_CART`, values `{-5, NA}` | 8 |
| `VCOL` | col 9 | 9 `Total_flux[photons/s]` | 9 ✓ |

Two defects, one shape. The id pattern's `tumou?r` alternative grabs
`Tumor_model` — **the exact failure `subject_strict` exists for, in the one
branch that does not use it.** And the covariate is anchored *twice*, in the
code (`TCOL.match`) and in the profile (`^\s*`), so
`Measurement_day_post_CART_injection` cannot match at all; the only column that
does is a design constant.

This is not BLI-specific. It is every long-format sheet whose headers are
prefixed, and long format is the one place the profile was measured to matter.

### The two changes, declared before either is written

* **A — try the candidate triples.** Enumerate every column matching each role
  and accept the first `(id, t, v)` combination that clears the floors, instead
  of committing to the first match per role. Prefer `IDCOL_STRICT` for the
  subject.
* **B — let the covariate match anywhere in the header.** `TCOL.match` →
  `TCOL.search`, *and* drop `^\s*` from the profile's `covariate`. **Either
  edit alone is a no-op**: `.match()` anchors regardless of the pattern, and the
  `^` anchors regardless of the method.

### The predictions

> **P1 — neither change alone recovers the file; both together do.** A alone
> leaves the only `TCOL` candidate at col 4, a constant. B alone still takes the
> first match, which is col 4.
> *FALSIFIER: either change alone recovers `PMC12545207`* — then the mechanism
> is not what the table above says it is.
>
> **P2 — the gate holds 15/15 with A+B, negative control intact.**
> *FALSIFIER: any fixture lost.*
>
> **P3 — over the 20,330-sheet census, A+B raises accepted sheets by LESS THAN
> 10%** (fewer than ~249 new accepts).
> *FALSIFIER: 10% or more.* Then the change is admitting a new population
> rather than recovering missed series, and it does not ship at that price
> however many mice it recovers.
>
> **P4 — none of V2's 6 verified TRUE papers is lost.**
> *FALSIFIER: any of them lost.*

### The stop, and the part that is easy to skip

**An accept count is not a recall gain.** The census can only say the number
moved; only reading says whether the new sheets are real. So a sample of the
new accepts is opened by hand and reported as TRUE/FALSE before any claim about
recall is made — and if that sample is mostly false, the change does not ship
even if P3 passes on the count.

This is rule 9 being *used* rather than merely obeyed: the rule permits a fix,
in its own pass, measured on the whole set, stating what it costs elsewhere.
That is exactly this. Nothing else moves — no floor, no response band, no new
vocabulary, no value pattern.

### Result — all four predictions CONFIRMED. 3 papers, 11 sheets, 0 lost.

Measured over the same census as V7: 2,390 papers, 20,330 sheets. Unit counted
is SHEETS.

| | | |
|---|---|---|
| **P1** | base REJECTED, A alone REJECTED, B alone REJECTED, **A+B accepted** `('long', 42, 4)` | **CONFIRMED** |
| **P2** | 15/15 under base, A, B, A+B and the shipped build; control intact | **CONFIRMED** |
| **P3** | accepted 2,487 → **2,498**: 11 gained, **0.44%** | **CONFIRMED** (falsifier 10%) |
| **P4** | **0 sheets lost** anywhere in the census, so no V2 true positive could be | **CONFIRMED** |

**P1 held for `PMC12545207`, and the general version of it is false** — which is
worth more than the prediction. Each change independently recovers papers the
other cannot:

| recovered by | sheets | what defeated the shipped scanner |
|---|---|---|
| **A alone** | 3 (`PMC11663793`) | `Date Taken` matched the covariate before `Day` did, and it is a datetime `_num` cannot read. The sheet died on a column that matched |
| **B alone** | 1 (`PMC12527938`) | `cumDay` — the token is there, the anchor is in front of it |
| **both** | 7 (`PMC12545207`) | the CAR-T dataset: wrong id column *and* an unreachable covariate |

### The stop was honoured: all 11 were read

**An accept count is not a recall gain**, so every gained sheet was opened.
**11 of 11 are genuine per-animal longitudinal series.** Two examples:

* `PMC12527938` — `Mouse ID | Group | cumDay | Tumor Volume (cm3)`, 402 rows;
  mouse 21 at cumDay 0/3/5/7/10/12, 0.27 → 1.86 cm³.
* `PMC11663793` — a vivarium Study Director export: `ID | Grp Name | … | Vol |
  Date Taken | Day | Notes`, mouse 171 across days 0–15, 188 → 1424 mm³, with
  caliper dimensions, body weight and welfare notes recording ulceration.

`PMC12545207`'s `4b-c` admits **42 animals**, not the 51 on the sheet: nine mice
have fewer than `min_points = 4` distinct timepoints and the floor drops them.
The sheet holds 51; the tool claims 42; both numbers are printed because they
are different quantities (rule 8).

### What shipped, and one correction to the tested variant

The variant measured above dropped `^\s*` from the covariate pattern. **The
shipped version keeps `\s*` and removes only `^`**, because two other call
sites — `header_evidence` and `discipline_signature` — still use `TCOL.match()`,
where dropping `\s*` would stop matching a header with leading whitespace and
silently change the reported `hdr=` label and the worklist ordering. The census
measures acceptance and would never have seen it.

Verified equivalent on both axes before shipping: under `.match()` the kept-`\s*`
pattern is identical to shipped (`"  Day"`, `"\tDay 5"`, `" time (h)"` all still
match, and would not have under the tested variant); under `.search()` it is
identical to the tested one. The full census was then re-run against the actual
shipped build: **11 gained, 0 lost**, reproducing exactly.

The cost, stated because it is real: under `.search()` the covariate pattern
matches `Monday` and `Today`. It cost nothing across 20,330 sheets, but the
shape of the risk is a substring rather than a word.

### What V8 does NOT fix

V1's false negative is **unchanged and still rejected** — and re-checking it
found it is **four sheets, not one**: `PMC13538391`'s `Group/volume (mm3) |
Day1 | Day4 | …` layout appears in Figures 6b, 6f, S9m and S9o. That is a WIDE
branch failure — the header cells must parse as numbers and `Day1` does not —
and V8 touches only the LONG branch's column selection. Writing it down again
rather than reaching for it (rule 9).

### The honest size of this

11 sheets in 20,330 is 0.44%, and the population it helps is long-format
supplementary tables, which this corpus says are rare. The change is worth
shipping because the sheets are real, nothing was lost, and the largest of them
is a 51-mouse CAR-T dataset that no amount of profile editing could ever have
reached — not because the number is large.

---

## V9 — the floors are a bias nobody was told about, and `min_subjects` drops to 4. REGISTERED, BEFORE THE MEASUREMENT

Asked by the owner, about a user who is not us: **are the default floors a bias,
and should they be reported or chosen?** They are three different biases,
"configurable" is not "informed", and the owner has decided to lower
`min_subjects` from 5 to 4.

### The three biases, which are not the same thing

1. **Coverage.** `min_subjects = 5` excludes small-n studies structurally, and
   n=3-4 per arm is ordinary preclinical practice — more so under 3Rs reduction
   pressure. Those are exactly the studies whose published means are least
   trustworthy and whose individual data is worth most.
2. **The floor's unit is the SHEET, and the scientific unit is the ARM.** On
   `PMC12545207` `4b-c` the sheet clears the floor on 51 pooled animals and then
   contributes experiments of **2 and 3 animals** (`CART0064`, `CART0060`) to
   the accepted total. The floor does not protect against small experiments at
   all there, while it does exclude whole sheets whose pooled total is under 5.
   Same defect shape as V6's "41 animals is really 5 arms".
3. **`min_points` drops animals inside an accepted sheet** — 9 of 51 there.
   **The obvious reading of this is wrong and was checked.** Dropped animals'
   last observed day is median 8 against 36 for admitted, which looks exactly
   like survivorship: the floor eating the animals that hit humane endpoint
   first. Split by `Experiment_ID` it is not. Whole SHORT experiments are
   excluded — `CART0073/0077/0079`, every animal dropped — while `CART0085`
   keeps all 37. The survivorship mechanism remains real in principle, since an
   animal euthanised early inside a long experiment is dropped the same way, but
   it is **not what happens here**, and stopping at the first measurement would
   have published a confident wrong reading.

### Nothing tells the user any of this

The frozen run record carries `query, sort, budget, hit_count, unit_counted,
stop_rule, scanner_recall, scanner_precision` — and **neither the profile nor
the floors**. Nor do `candidates.csv` or `worklist.csv`. `load_profile`'s own
docstring says *"Every artifact this tool writes must name the profile it ran
under"*: the rule is written down and not implemented.

And the headline figures are floor-conditional. **15/15 and 6/15 were measured
at `min_subjects = 5, min_points = 4`.** A user who changes them holds numbers
that no longer describe their run.

### The change

`min_subjects` 5 → 4 in `tumor_volume` and `body_weight`.
**`profiles/contributed/rotarod_latency.toml` is NOT touched** — it ships
exactly as its author wrote it, and editing a contributed profile would erase
the one thing it demonstrates.

Lowering a floor can only ADD acceptances, never remove one, so recall cannot
fall. What it can do is admit false positives, and that is what is measured.

> **P1 — the gate holds 15/15 and the negative control stays intact.**
> *FALSIFIER: the control fires* — a 4-subject aggregate block would then be
> reachable, and the floor was load-bearing for the one rule everything rests on.
>
> **P2 — over the 20,330-sheet census, accepted sheets rise by LESS THAN 20%.**
> *FALSIFIER: 20% or more* — the floor was doing most of the filtering rather
> than trimming an edge, and the owner should see that number before it ships.
>
> **P3 — the new accepts are enriched for false positives: a hand-read sample
> of 10 yields FEWER THAN 5 genuine per-animal longitudinal series.**
> *FALSIFIER: 5 or more genuine* — then the floor was costing real data, and the
> change is a straight recall win rather than a trade.

P3 is the one that matters and the one that cannot be automated. An accept count
is not a recall gain (V8).

### What ships regardless of the result

The owner decided the default. The measurement does not gate it — it **prices**
it, and the price travels with the number wherever the number is quoted. If P2
or P3 lands badly that is a finding to publish, not a reason to quietly revert a
decision made deliberately.

### Two plain defects fixed in the same pass, neither a measurement

* **`scan.py`'s own CLI has been dead since the initial import.** `scan()` unpacks
  `judge_any`'s tuple into four names; a later commit appended `hdr` as a sixth
  element and stated "no positional unpacking downstream moves". It moved this
  one. `python scan.py <PMCID>` raises `ValueError: too many values to unpack
  (expected 4, got 6)` on the first accepted sheet. `mine.py` has its own loop
  and the gate calls `judge_any` directly, so nothing caught it — the tests
  check the instrument and the demo checks the tool, again.
* **The artifacts now name what produced them:** profile, `min_subjects` and
  `min_points` in the run record, `candidates.csv` and `worklist.csv`, plus a
  per-sheet `n_below_floor` — the animals present on the sheet that the points
  floor dropped — so the exclusion is visible where the decision is made rather
  than buried in a TOML.

### Result — all three predictions CONFIRMED. The floor change is a real trade, and it makes the precision figure stale.

| | | |
|---|---|---|
| **P1** | gate 15/15, negative control intact | **CONFIRMED** |
| **P2** | accepted 2,498 → **2,696**: 198 gained, **7.93%**, 0 lost | **CONFIRMED** (falsifier 20%) |
| **P3** | hand-read sample of 10: **2 genuine** | **CONFIRMED** (falsifier 5) |

Sample drawn with `random.seed(20260918)` from the 198 new accepts and written
to `runs/v9_sample.json` **before any sheet was opened**.

| verdict | papers |
|---|---|
| **TRUE** — per-animal longitudinal tumour series | `PMC12779575` (4 mice, days 1–14, 0 → 1684 mm³), `PMC13522462` (HL-60 xenograft, n=4, day 0/7/14, body weight + width + length + volume) |
| FALSE | IHC staining intensity, GO-term values, antibody-array spots, flow-cytometry counts, DLS particle-size distribution, RNA expression by condition |

**2 of 10 = 20% on the newly admitted population**, against the established
6 of 15 = 40%. Lowering the floor roughly halves precision *on what it adds*.
That is the price, it is what the registration asked for, and it is not a reason
to revert a decision taken deliberately.

**Two of the eight false accepts are genuinely per-subject longitudinal series
of the wrong readout**, which is the scanner doing its structural job under the
wrong label: `PMC11357990` is `Animal\Timepoint (hr)` blood glucose, and
`PMC13490413` is ΔCT across `Volunteer1..4` at 0/3/7/14 days.

### An unregistered finding: the human-data exclusion is documented and not enforced

`PMC13490413` is human volunteers. `SKILL.md` and `docs/PROTOCOL.md` rule 12
both put individual human data out of scope — and nothing in the tool enforces
it. The scanner accepted it on structure, as it is designed to. The exclusion
lives entirely in prose that a person has to read and apply. Written down, not
fixed here: enforcing it means detecting "human" from a sheet, which is the
identity problem step 4 exists for, and it needs its own registration.

### THE CONSEQUENCE THAT MATTERS MOST

**`6 of 15` was measured at `min_subjects = 5`. It no longer describes the
shipped configuration.** The number is not wrong — it is about a scanner that is
no longer the default one. It cannot be repaired by arithmetic on the two
samples: blending 40% over 2,498 with 20% over 198 gives roughly 38%, and that
is a calculation, not a measurement, over two intervals wide enough to swallow
the difference.

So the honest state is: **precision is unmeasured at the shipped floors**, the
last measurement was 6 of 15 at `min_subjects = 5`, and the figure that replaces
it needs a fresh unbiased sample drawn at the new default. Every place the
number is quoted now says which floor it was taken at.

That is the cost of the change that nobody would have noticed: not the 198
sheets, but the fact that the repository's second headline number quietly
stopped describing the tool.

---

## V10 — precision at the shipped floors. REGISTERED, BEFORE THE DRAW

V9 lowered `min_subjects` to 4 and left the repository with no precision figure
that describes its own scanner: `6 of 15` was measured at `min_subjects = 5`.
This produces the replacement.

### The population, defined before it is built

Every paper in `si_cache/` (2,390) is swept with the **shipped** configuration.
A paper enters the population if the scanner accepts at least one of its sheets.
For each such paper the **best sheet** is taken — the one `worklist.py` would
put first: header evidence, then subject count, then points — because that is
the sheet a user actually opens.

**Papers already carrying a verdict are excluded**: V2's 15, V8's 3, V9's 10,
and the 4 in `example/worklist.csv`. Re-drawing a paper whose answer is already
known is not an out-of-sample measurement, and V2 excluded its 4 previously
verified papers for the same reason.

**The honest limit on the population, stated before the result:** `si_cache/` is
the accumulation of previous campaigns and of `journal_yield.py`'s 100-paper
sweeps across 27 journals. It over-represents the journals that were studied and
is **not** a random sample of the literature. This is a precision figure over
*that* population, and the direction of any bias is unknown — high-yield
journals may carry cleaner Source Data, or more of the discipline matrices that
V2 found. Said now because it cannot be said honestly afterwards.

### Sample and power

**`random.seed(20261018)`, n = 20**, drawn and written to
`runs/v10_sample.json` before any sheet is opened.

**n = 20 cannot distinguish a third from a half.** At p ≈ 0.4 the 95% interval
is roughly ±21 points, barely narrower than V2's 15. Separating a third from a
half needs of order 100 hand-read items, which is acquisition work and not an
afternoon. This is a figure that DESCRIBES THE SHIPPED SCANNER, which is what
does not currently exist — not a more precise one. It will be reported as such
whichever way it falls.

### The predictions

> **P1 — the new figure is LOWER than 6 of 15 (40%).** V9 added 198 sheets
> measured at 2 of 10, so the blended population should sit below the old one.
> *FALSIFIER: equal or higher* — then the floor change is not what dominates
> this number, and the cache population differs from V2's single campaign in a
> way that matters more than the floors do.
>
> **P2 — the false accepts are dominated by the population V2 named**: large
> numeric matrices from another discipline. At least half of them.
> *FALSIFIER: fewer than half* — the failure mode has moved since V2, and what
> replaced it is a new finding.

### The stop

**Nothing is tuned in response to this, whichever way it falls** (rule 9). No
floor, no pattern, no band. The figure replaces `6 of 15` wherever precision is
quoted, and it travels with the floors it was measured at and the population it
was drawn from — which is the defect V9 exposed and this exists to close.

### Result — precision at the shipped floors is **7 of 20 = 35%**. P1 confirmed on the point estimate and worth almost nothing; P2 FALSIFIED.

Population: 480 of 2,390 cached papers accepted by the shipped scanner, minus
30 already carrying a verdict, leaving **450 eligible**. Twenty drawn with
`random.seed(20261018)` into `runs/v10_sample.json` before any sheet was opened;
verdicts in `runs/v10_verdicts.csv`.

| | |
|---|---|
| **TRUE** — per-animal longitudinal tumour series | **7** |
| FALSE | 13 |
| **precision at `min_subjects=4, min_points=4`** | **7/20 = 35%**, 95% interval roughly **14–56%** |

The seven: `PMC12075843` (weekly burden, TAT-CRE vs AD-CRE), `PMC12589595`
(4T1, mice 1–6, days 0–21), `PMC13179327` (days 0/9/13/16, Aged RAGE+/+),
`PMC11560846` (`Animal ID | D0..D13`, BALB/c nude n=18), `PMC9970872` (raw
tumours' volume mm³ at 1/4/7/10/14 days), `PMC13396614` (HepG2 vehicle arms),
`PMC13372664` (Vehicle vs dHuR-2, mm³ by day).

**P1 — CONFIRMED, and the confirmation is worth almost nothing.** 35% against
V2's 40% is not a distinguishable difference: the intervals are 14–56% and
20–64%. Worse, it turned on a **single judgement call**. `PMC7138317` `fig.6C`
carries no unit, no animal label and no day label — only `DMSO / Dox / ATMi-1 /
Dox+ATMi-1`, six replicates and `Average`/`SD` rows. Unresolvable from the
documents, scored FALSE because the burden of proof is on the accept. Scored
TRUE it would be 8/20 = 40%, exactly equal, and P1 would be falsified. **One
unresolvable sheet decides the direction of this prediction**, which is the
honest size of a 20-item measurement.

**P2 — FALSIFIED. The failure mode has moved since V2.**

| what the false accepts are | n |
|---|---|
| **in vitro assay read as a time or index course** | **5** |
| numeric matrix from another discipline (V2's population) | 4 |
| group-level aggregate | 2 |
| human data | 2 |

V2 found 7 of 9 false accepts were discipline matrices. Here that class is 4 of
13, and the largest is **in vitro assays** — cell proliferation over days, drug
panels with a replicate index read as a calendar, a `Time (minutes)` kinetic
run. Two causes, and this measurement cannot separate them: the population is
the whole cache rather than one campaign, and V9's floor of 4 admits small
replicate sets that a floor of 5 excluded.

### Two findings the sample produced on its own

**`AGG` has a layout hole, and `AGG` is the thesis.** `PMC12397317` `Fig 4c` is
`Day | Mean | SD | Mean | SD` per arm — group-level aggregate, exactly what the
scanner exists to reject. `AGG` matches **row labels**; here `Mean` and `SD` are
**column headers**, so it never fires. This is the one rule that deliberately
does not live in a profile ("a profile field is an invitation to relax the one
rule worth having") and it has a blind spot nobody had measured.

**Human data is excluded in prose only, and now there is a number.** `2 of 20`
accepted papers are human: `PMC13278948` (clinicopathological cohort table) and
`PMC12352675` (patient records with name, sex, age, diagnosis and brachytherapy
dosimetry). `docs/PROTOCOL.md` rule 12 and `SKILL.md` both exclude individual
human data; nothing in the tool enforces it. V9 saw one instance and called it
unregistered; at 2 of 20 it is a rate, not an anecdote.

### What this figure is, and what it is not

It is **the first precision figure that describes the scanner this repository
actually ships.** It does not supersede `6 of 15` as a better measurement of the
same thing — they measure different configurations over different populations,
and they must not be pooled.

Both say "about a third", and neither can distinguish a third from a half.

**The population caveat, repeated because it survives the result:** `si_cache/`
is the accumulation of past campaigns and of `journal_yield.py`'s sweeps across
27 journals. It over-represents those journals and is not a random sample of the
literature. A user mining a different journal set should expect a different
number, and the only honest way to get theirs is to verify their own worklist.

---

## V11 — the negative control does not test `AGG`. REGISTERED, BEFORE THE MEASUREMENT

V10 found `PMC12397317` `Fig 4c` accepted: `Day | Mean | SD | Mean | SD` per
arm, group-level aggregate, exactly what this scanner exists to reject. `AGG`
matches **row labels**; there `Mean` and `SD` are **column headers**.

Chasing that produced something worse, and it is a fact rather than a
prediction — established by reading and confirmed by experiment before this was
written:

### The gate's negative control is a vacuous pass for `AGG`

`PMC13367972` sheet `Fig. 7C_Tumor_growth` is the control acquired
specifically to test `AGG`. Its aggregate markers — `Average tumor
growth (%)`, `SEM`, `Number of mice` — all sit in **row 5, a column-header
row**. The WIDE path's label for that row is the word `variables`. `AGG` fires
on **no row label in the file**.

Neutering `AGG` to a pattern that can never match:

```
with AGG as shipped     -> None
with AGG NEUTERED       -> None
```

**Identical.** The control is rejected because its time axis is the text
`Week 1` and no numeric axis exists — the same layout that caused V1's false
negative — and not because it holds means. So `negative control: intact` in
every gate run this repository has ever printed is a statement about a check
that never exercised the rule it was acquired for.

This is `D104` again, one level deeper. D104 found `AGG` was being scored
against headers this project had transcribed itself; the repair acquired real
publisher bytes; and the acquired file does not reach `AGG` either. Rule 11
applied to the negative control itself, twice.

### What is measured

Over the 20,330-sheet census, with the shipped configuration.

> **P1 — `AGG` does material work.** Neutering it raises accepted sheets by at
> least **1%** (27 or more), because rows labelled `Mean`/`SD`/`Average` would
> then be counted as subjects and push sheets over the subject floor.
> *FALSIFIER: fewer than 27* — `AGG`, the one rule deliberately kept out of the
> profiles, is close to decorative in practice, and that is a finding about the
> thesis of the whole scanner.
>
> **P2 — the column-header hole is material.** At least **5** currently
> accepted sheets carry aggregate markers in their header region rather than in
> a row label.
> *FALSIFIER: fewer than 5* — `PMC12397317` is an edge case, not a class.
>
> **P3 — a real control exists in the cache.** At least one sheet is rejected
> **by `AGG` specifically** (accepted when `AGG` is neutered) and holds genuine
> group-level longitudinal means — a candidate negative control that actually
> exercises the rule.
> *FALSIFIER: none found* — then `AGG` has no demonstrable positive anywhere in
> 2,390 papers, and the gate cannot be repaired from what is already on disk.

### The stop

**No pattern is widened to make `PMC12397317` fail.** Any change to `AGG` is
measured over the whole set and states what it costs the 15 fixture positives
first; a rejection rule tuned against the false positive that inspired it is
V5's error wearing the opposite sign, and V5 already refused to ship at that
price.

And the gate is **not** repaired by editing the check. It is repaired by naming
a control that exercises the rule — which is what P3 looks for and why it is
registered rather than assumed.

### Result — all three predictions CONFIRMED, and the gate now actually tests `AGG`

Census, 20,330 sheets, shipped configuration.

| | | |
|---|---|---|
| **P1** | accepted 2,696 → 2,732 with `AGG` neutered: **36 sheets rejected by `AGG` alone**, 1.34% | **CONFIRMED** (falsifier: under 27) |
| **P2** | **304** accepted sheets carry aggregate vocabulary in their header region, 11% of all accepts | **CONFIRMED** (falsifier: under 5) |
| **P3** | 37 candidates found; the best is a textbook control | **CONFIRMED** |

*(37 sheets gain acceptance when `AGG` is neutered but the net is +36 — one
sheet is **lost**, because aggregate rows counted as subjects shift the median
fold and the consistency fraction enough to fail the response band.)*

### The new negative control, and the proof it works

`PMC12611756` (Nature, `10.1038/s41586-025-09655-y`, OA) sheet `2a`:

```
Days | UT        |      | PD1     |      | RNA-LNP |      | RNA-LNP+PD-1
Days | Mean      | SEM  | Mean    | SEM  | Mean    | SEM  | Mean   | SEM
13   |  112.371  | 4.24 | 118.2   | 8.06 | 120.612 | 19.2 | 88.35  | 4.96
19   | 1572.96   | 171  | 862.95  | 164  | 580.029 | 79.9 | 315.657| 34.9
```

Longitudinal tumour volumes as group means with SEM per arm, written by the
paper's own authors. It has a **numeric** day axis, so unlike the old control it
reaches the structural test and is rejected on the rule rather than on a parse
failure.

**The proof, which is the whole point:**

| | shipped | `AGG` neutered |
|---|---|---|
| old control `Fig. 7C_Tumor_growth` | `None` | `None` — **`AGG` irrelevant** |
| new control `2a` | `None` | **ACCEPTED** |

Running the gate with `AGG` neutered now prints `negative control: FIRED` and
exits **FAIL**. Break the rule and the gate goes red. That was never true
before, and it is the only form of evidence that a control tests what it claims.

The old file stays in the fixture set as an ordinary `NEG` row. It is still a
true negative; it was simply never a test of `AGG`.

### The column-header hole: REPORTED, NOT ENFORCED

A header-aware `AGG` costs the fixture gate **nothing** — 15/15, control intact.
Over the census it would reject **304 of 2,696** accepts. A seeded sample of 8
of those:

| | |
|---|---|
| correctly caught | **7** — patient radiomics, blot densitometry (`Area/Mean/IntDen`), two genuine `Day \| Mean \| SEM \| N` tumour-growth aggregates, in-vitro viability and confluency |
| **wrongly caught** | **1** — `PMC13102701` `11E`: `Days \| Control \| JHU-083`, one column per animal, 1 → 35.9. A real per-animal series |

Seven in eight is a good rule and it still costs real recall, so it **does not
ship as a gate** — the same resolution V5 reached for the discipline
signatures, on the same evidence and for the same reason. It ships as a
`discipline_signature` label, which sinks the sheet to the bottom of the
worklist and spends no recall. `PMC12397317` `Fig 4c`, the sheet that started
this, is now labelled *aggregate vocabulary in the header region*.

### A by-product: two papers publishing identical data

`PMC12932840` and `PMC12992596` are different papers with different files and
different `sha256`, whose sheets `3E1, 3E2, 8A1, 8A2, S4B1, S4B2` are
**identical in every numeric value** (108, 108, 216, 216, 72, 72 values
respectively). This is exactly what `fingerprint.py`'s axis 3 exists to catch,
found here as a side-effect of asking a different question — and it is the
first duplicate this repository has observed in the wild rather than inside its
own corpus.

---

## V12 — the `Day1` axis. REGISTERED, BEFORE ANY CODE CHANGES

V1 found this false negative and wrote it down rather than fixing it. V8
re-checked it and found it is **four sheets, not one**: `PMC13538391`
(`41467_2026_76239_MOESM10_ESM.xlsx`) Figures `6b`, `6f`, `S9m`, `S9o`, all
laid out

```
Group/volume (mm3) | Day1 | Day4 | Day7 | Day10 | Day14
Control            | 39.868 | 125.585 | 387.195 | 420.332 | 846.506
                   | 127.32 | 281.786 | 1193.15 | 1554.71 | 1997.92
```

Rows are individual animals, the arm named once per block. The WIDE branch
builds its axis with `_num()` on the header row, and `_num('Day1')` is `None`,
so no axis exists and the sheet is invisible. Rule 9 permits the fix in its own
pass, measured on the whole set, stating what it costs elsewhere. This is it.

### The change

A header cell may yield a covariate when the **whole cell** is a day-like token
followed by a number:

```
^\s*(?:day|week|wk)\s*[-_ ]?(\d+(?:\.\d+)?)\s*$
```

**What is deliberately excluded, and why.** No bare `t`, `d`, `w` or `tp`: `T1
T2 T3` and `D1 D2 D3` are as often plate wells, timepoint labels with no
calendar, or sample codes. No partial matches: requiring the whole cell keeps
`Figure 1`, `Sample 2`, `Group 3` and `Mouse #1` out — and `Mouse #1 | Mouse #2
| …` becoming an axis of 1,2,3 is precisely the index-axis failure V5 named.

`week` and `wk` are admitted knowing they change the UNIT: a sheet headed
`Week 1..Week 6` yields an axis in weeks, not days. The scanner's axis is an
ordinal covariate and always was; the unit belongs in the builder's docstring,
where the protocol already requires it.

### The predictions

> **P1 — the gate holds 15/15 and the new `AGG` control stays intact.**
> *FALSIFIER: either moves.*
>
> **P2 — all four `PMC13538391` sheets are recovered.**
> *FALSIFIER: fewer than four* — the mechanism is not what two validations have
> now claimed it is.
>
> **P3 — over the 20,330-sheet census, accepted sheets rise by LESS THAN 5%**
> (fewer than ~135).
> *FALSIFIER: 5% or more* — the rule is admitting a population rather than
> recovering a layout.
>
> **P4 — a seeded sample of 10 new accepts is MAJORITY genuine: 5 or more.**
> This is the risky one. V9's floor change managed 2 of 10; the claim here is
> that a lexically anchored rule does better than a numeric threshold, because
> it recovers a known layout instead of lowering a bar.
> *FALSIFIER: 4 or fewer* — then it ships as a label and not as a parse, the
> resolution V5 and V11 both reached.

### The stop

The pattern above is fixed before measuring and is not widened afterwards to
admit anything the census turns up. If P4 fails the rule does not ship as a
parse, whatever P2 and P3 say.

### Result — all four predictions CONFIRMED, and the change created one false accept of the worst class

| | | |
|---|---|---|
| **P1** | gate 15/15, `AGG` control intact | **CONFIRMED** |
| **P2** | all **4 of 4** `PMC13538391` sheets recovered | **CONFIRMED** |
| **P3** | accepted 2,696 → 2,754: **58 gained, 2.15%**, 0 lost | **CONFIRMED** (falsifier 5%) |
| **P4** | seeded sample of 10: **6 genuine** | **CONFIRMED** (falsifier 4 or fewer) |

Sample drawn with `random.seed(20261218)` into `runs/v12_sample.json` before any
sheet was opened. The six: `PMC13538391` `Figure S9m` (the target layout),
`PMC9701141` ×4 (`day 0 | day 12 | day 14 …`, tumour volume, one row per
animal, including bilateral irradiated/non-irradiated blocks), and `PMC9068207`
`tumori` (per-mouse tumour measurements with a `Mouse ID` column).

**A caveat the sample itself produced:** this draw is over SHEETS, not papers,
and four of the six true positives are the same paper. V2 and V10 drew papers
for this reason. Six true sheets means **three distinct papers**, and the
weaker number is the honest one.

### The cost, and it is the sharpest thing here

`PMC13367972` `Fig. S4A_DOSE_RESPONSE` is **newly accepted, and it is
group-level means** — the exact class the negative control exists to reject, in
the very file that used to BE the negative control:

```
WEEKS OF TREATMENT | WEEK 0 | WEEK 1 | WEEK 2 | ...
AVERAGE GROWTH (%) |    100 | 89.109 | 89.559 | ...
SEM                |      0 | 11.342 |  9.055 | ...
NUMBER OF MICE     |      5 |      5 |      5 | ...
```

**This change created that accept.** Before it, `WEEK 0` was unparseable and the
sheet had no axis; the rejection was an accident of layout rather than a
judgement. Traced to the row:

| row | `AGG`? |
|---|---|
| `AVERAGE GROWTH (%)` | rejected, correctly |
| `SEM` | rejected, correctly |
| **`NUMBER OF MICE`** | **not matched** — counted as a subject |
| `B20-4.1.1 1X vs. 0.5X` (a p-value row) | not matched — counted as a subject |

The "5 animals" are two `NUMBER OF MICE` rows and three statistical-comparison
rows. **`AGG` has vocabulary holes**, and a second one fell out of checking:
`n = 5` with spaces does not match either, because `\bn\s*=\b` cannot close its
boundary before a space (`n=5` matches; `n = 5` does not).

### What ships, and what deliberately does not

The rule ships **as registered**, `day|week|wk`, whole-cell match. Narrowing it
to `day` alone now — after seeing which sheet the `week` half admitted — would
be tuning on the very sample that exposed it, which is V5's error and this
registration's explicit stop.

So the cost is reported rather than engineered away, and the repair is queued as
its own pass: **V13 closes `AGG`'s vocabulary holes** (`number of mice`, spaced
`n = `), which is the root cause — that sheet *should* be rejected by the rule
and is not — and measures day-only against day+week over the whole set. Fixing
`AGG` is not tuning: it makes the rule match the thing it already claims to
match.

---

## V13 — closing `AGG`'s vocabulary holes, and letting that decide whether `week` stays. REGISTERED

V12 shipped the `Day1` axis as registered and created one false accept:
`PMC13367972` `Fig. S4A_DOSE_RESPONSE`, group-level `AVERAGE GROWTH (%)` /
`SEM` / `NUMBER OF MICE` across `WEEK 0..WEEK 7`. Tracing it found the cause is
not the week axis but **`AGG`'s vocabulary**, measured on the row:

| row label | matched by `AGG`? |
|---|---|
| `AVERAGE GROWTH (%)`, `SEM` | yes |
| **`NUMBER OF MICE`** | **no** — counted as a subject |
| `n = 5` (spaced) | **no** — `\bn\s*=\b` cannot close its boundary before a space; `n=5` matches |

That sheet *should* be rejected by the rule and is not. Repairing the rule so it
matches what it already claims to match is a root-cause fix, not tuning.

### The change

```
number\s+of\s+(?:mice|animals|rats|subjects)      added
\bn\s*=                                           trailing \b dropped, so
                                                  `n = 5` matches as `n=5` does
```

Nothing else enters the vocabulary. `±`, `IQR`, `range`, `95% CI` and `p` are
**not** added: they were not measured as holes here, and widening a rejection
rule beyond what was measured is the error V5 named.

### The predictions, and the decision rule fixed in advance

> **P1 — with the holes closed, `PMC13367972` `Fig. S4A_DOSE_RESPONSE` is
> REJECTED.**
> *FALSIFIER: still accepted* — the repair does not reach the sheet it was
> derived from, and `week` must then be judged on its own.
>
> **P2 — the repair costs the gate nothing: 15/15, `AGG` control intact.**
> *FALSIFIER: either moves.*
>
> **P3 — over the census the repair removes FEWER THAN 2% of accepts**
> (under ~55 sheets).
> *FALSIFIER: 2% or more* — it is removing a population rather than closing a
> hole, and each removal then needs reading before it ships.
>
> **P4 — `week`/`wk` accounts for FEWER THAN HALF of V12's 58 gained sheets**,
> i.e. most of that gain is plain `day`.
> *FALSIFIER: half or more* — `week` is carrying the change rather than riding
> it, and deserves its own registration.

**THE DECISION RULE, FIXED NOW SO IT CANNOT BE CHOSEN AFTERWARDS:** `week|wk`
**stays** if P1 holds — the harm it caused is then removed at its actual source.
If P1 fails, `week|wk` is **removed** from `HDR_DAY` and re-registered as its
own change with its own measurement.

### The stop

The repair is measured over the whole set before it ships, and whatever the
census turns up is **not** used to widen `AGG` further in this pass.

### Result — all four predictions CONFIRMED. `week` stays, by the rule fixed in advance.

| | | |
|---|---|---|
| **P1** | `PMC13367972` `Fig. S4A_DOSE_RESPONSE` → **REJECTED** (was `wide, n=5, fold=2.0`) | **CONFIRMED** |
| **P2** | gate 15/15, `AGG` control intact | **CONFIRMED** |
| **P3** | census 2,754 → 2,753: **exactly 1 sheet removed**, 0.04% | **CONFIRMED** (falsifier 2%) |
| **P4** | of V12's 58 gained sheets, **54 come from `day` alone**; only **4 (7%)** need `week`/`wk` | **CONFIRMED** (falsifier 50%) |

**P1 held, so `week|wk` stays** — that was the decision rule, written before the
measurement, and the harm it caused is now removed at its actual source rather
than by withdrawing the feature that exposed it.

**P3 is the sharpest number here and it cuts both ways.** The repair removes
exactly one sheet from 20,330 — *the* sheet it was derived from — and touches
nothing else in 2,390 papers. That is as surgical as a rejection rule gets, and
it also means the hole was narrow: `NUMBER OF MICE` is rare as a row label, and
the spaced `n = ` half changed no verdict at all. The value of this change is
that `AGG` now matches what it has always claimed to match, not that it removed
a population.

**P4 reframes V12 in hindsight.** `day` does 54 of 58; `week`/`wk` does 4. The
half of the pattern that caused the only false accept was carrying 7% of the
benefit. Registering the decision rule in advance is what made that a
measurement rather than an argument — with the rule fixed beforehand, the answer
was forced by P1 and could not be chosen to suit the result.

### A methodological failure worth recording, because it nearly shipped a lie

Two attempts to build this variant produced an `AGG` that **matched nothing at
all** — not `Mean`, not `SEM`, nothing. Passing `\b` through a shell heredoc
delivered a single backslash to Python, which turned it into a **backspace
character** (`\x08`) inside the pattern. The regex compiled without error and
silently rejected nothing.

Had that variant been measured instead of inspected, the census would have
reported a large, clean, entirely false result — an `AGG` that "costs nothing"
because it does nothing. It was caught only because the vocabulary check ran
first and `Mean` came back `False`.

The build step now writes the patcher to a file the shell never touches,
re-compiles the written pattern, and **refuses if the compiled pattern contains
any character below `0x20`**. This is protocol rule 10's shape one level down:
the tooling met a wall, produced something that looked like an answer, and the
only defence was checking a value known in advance.

---

## V14 — human data is excluded in prose only. REGISTERED

`docs/PROTOCOL.md` rule 12 and `SKILL.md` both put individual human data out of
scope. Nothing in the tool enforces it, and V10 measured the consequence on an
unbiased sample: **2 of 20 accepted papers are human** — `PMC13278948`
(clinicopathological cohort table, `GENDER==female`) and `PMC12352675` (patient
records: 姓名 / 性别 / 年龄 — name, sex, age — with brachytherapy dosimetry).
V9 saw a third, `PMC13490413` (ΔCT across `Volunteer1..4`).

For a tool about to be published, an exclusion that exists only in a sentence
someone has to read is not an exclusion.

### Why this LABELS rather than rejects

`patient` cannot be a rejection token. **Patient-derived xenograft is the single
most common phrase in this literature**, and a PDX study is animal data. Bare
`donor` is out for the same reason: CAR-T papers name human donors for cells
grown in mice. A rule that rejected on either would delete a large part of the
tool's actual target.

So the vocabulary is deliberately narrow, requires the marker to be
unambiguous, and the result is a `discipline_signature` label that sinks the
sheet in the worklist — the resolution V5 and V11 both reached, for the same
reason.

```
volunteer | participant | patient[_ ]?id | clinicopathologic
TCGA | gender | age at diagnosis | informed consent
姓名 | 性别 | 年龄 | 患者            (name / sex / age / patient)
```

The CJK terms are in because one of the three known cases is a Chinese-language
sheet, and an English-only rule would miss it while appearing to work.

### The predictions

> **P1 — all three known human sheets are labelled**, including the
> Chinese-language one.
> *FALSIFIER: fewer than three.* If the Chinese sheet is the miss, an
> English-only vocabulary is insufficient and the gap is linguistic, which is
> worth knowing before anyone quotes a rate.
>
> **P2 — fewer than 3% of accepted sheets are labelled** across the census.
> *FALSIFIER: 3% or more* — the vocabulary is catching xenograft language and
> is unusable as written.
>
> **P3 — a seeded sample of 10 labelled sheets is majority genuinely human:
> 6 or more.**
> *FALSIFIER: 5 or fewer* — the label is noise and does not ship.

### The stop

The label does not gate, whatever the numbers say. And the vocabulary above is
fixed before measuring: nothing is added afterwards to catch what the census
turns up.

### Result — all three predictions CONFIRMED, and one token is weak

| | | |
|---|---|---|
| **P1** | all **3 of 3** known human sheets labelled, the Chinese-language one included | **CONFIRMED** |
| **P2** | **44 of 2,753** accepted sheets labelled = **1.60%** | **CONFIRMED** (falsifier 3%) |
| **P3** | seeded sample of 10: **9 genuinely human** | **CONFIRMED** (falsifier 5 or fewer) |

The nine are unambiguous: `Anonymized patient ID | Age | Gender | Smoking status
| Pack Years | BMI | Recurrence | Deceased`; a FUSCC clinical table with
`TNM_stage` and `Furhman` grade; TCGA-KIRC drug-sensitivity predictions; a
`Patient ID | Age | Sex | Race/Ethnicity | Survival, days` glioma cohort; and a
Chinese-language lymphoma cohort carrying `gender | age | heart_rate | sbp |
spo2 | hematocrit | creatinine` — ICU-grade clinical variables, in a
supplementary spreadsheet, reachable by a tool built to find mouse tumours.

**The tenth is a false positive and names the weak token.** `PMC13428747`
`Tabelle1` is *Measurements of tumour size, Day 2..Day 13, Recipient mouse,
B16F10* — mouse melanoma. What matched was **`gender`**, a column recording the
**mouse's** sex. Animals have a recorded sex too, and `gender` is not a human
marker.

`gender` is **not removed**. The registration fixed the vocabulary before
measuring and said nothing would be changed afterwards to suit what the census
turned up; narrowing on the single item that exposed it is the same error as
widening. It is written down here, and the cost is bounded by design: the label
orders the worklist and does not reject, so a mislabelled mouse sheet sinks a
few rows and is still there to be read.

### What this does and does not establish

**1.60% of accepted sheets** carry the label. V10 found **2 of 20 accepted
papers** were human. Those are different units over different draws and **must
not be compared** — sheets are not papers, and the label certainly misses cases
the vocabulary does not name.

What can be said: individual human data, including named clinical variables, is
reachable by this tool today; the exclusion that was written in prose is now
visible in the artifacts; and it still is not enforced, because enforcing it on
`patient` would delete patient-derived xenografts, which are the tool's actual
target.

---

## V15 — the clean clone, run for the first time since V4

Four validations and twenty-five commits after V4 last did this, on a fresh copy
with nothing carried over.

| step | result |
|---|---|
| `git clone` | 2.9 MB, **no publisher bytes** — the manifest design holds |
| `pip install -e .` | builds clean; V4's flat-layout failure stays fixed |
| `preflight_banner()` | silent |
| gate, **before** fetching | **FAIL** — `negative control: NOT RUN -- the file is not in the cache`. Correct: no vacuous pass on an empty cache |
| `fixtures/fetch.py` | cached **5**, MANUAL 8 (Dryad), not_oa 1 |
| gate, after fetching | **PASS — RECALL 4/4** |

**`RECALL 4/4`, and the README claimed 15/15.** The denominator was honest, so
nothing lied — but the headline recall figure **was not reproducible by anyone
except its author**, because `fixtures/manifest.csv` held 14 rows while
`fixtures/ground_truth.csv` names 29.

Fifteen files the gate scores against were in no manifest at all, including
`pone0288380_4t1luc2.xlsx` — the known false positive the gate **prints by name
on every single run**. Phase 1's own words: *"a fixture set you cannot prove is
the one the recall figure was measured on is not a fixture set."* This manifest
could not prove half of its own.

### After the repair

12 of the 15 are cached and are now pinned, every DOI **resolved and verified**
against Europe PMC or doi.org rather than constructed from a filename. The
resolver writes `route=unresolved` with a reason instead of guessing; nothing
needed it.

Re-run on a second fresh clone:

```
cached 17 ... the gate's denominator is the 17 cached files, and it says so.
RECALL: 15/15 = 100.0%
PASS -- negative control: intact (sheet '2a' rejected)
```

**The headline figure is now reproducible by a stranger.** That is the single
most important thing this repository can offer, and it was false until today.

### Three files remain unpinnable, and two of them should be

`pone0262378_mcf7.csv` and `rsob_240210_group_means.txt` are the transcriptions
Phase 1 identified as **not publisher bytes** and excluded from the headline for
exactly that reason; they are correctly absent from a manifest of publisher
bytes. `jmc5c01298_pkmyt1_sourcedata.xlsx` was never cached here at all — a
genuine gap, now visible as one rather than silently missing.

### What the clean clone still cannot do

Eight Dryad files need a manual download or a token. That is Dryad's policy, the
tool reports it every run and never counts them as absent, and a user who skips
them gets a gate over 17 files that says 17.

---

## What is NOT done, and what each one would actually take

Written here so it cannot be mistaken for an oversight, and so a reader can
price it.

### `body_weight` has no measured recall, and cannot have one yet

Re-verified that the mechanism still works after V8, V12 and V13, on
the three files where a weight block is known to exist:

| file | `tumor_volume` | `body_weight` |
|---|---|---|
| thsd7b | `n=9 fold=8.0` | `n=7 fold=1.2` |
| 4t1luc2 | `n=12 fold=1.6` | `n=13 fold=1.2` |
| aldh1a1 | `n=51 fold=25.8` | `n=47 fold=0.8` |

Different blocks, weight-like folds. **That is a regression check and not a
recall figure**, and calling it one would be exactly the tuning-set-as-score
error rule 9 exists to prevent: three files, all of which informed the profile.

A real figure needs ground truth — a set of sheets verified BY READING to
contain per-animal body weight, assembled by some route other than this
scanner, or the measurement is circular. Nobody has assembled one. Until then
the profile prints `NOT MEASURED. There is no figure for it, none.` on every
run, which is the correct thing for it to say.

**And the sharper gap the 3Rs reviewer found stands unrepaired** — restated
precisely, because the wording it had was wrong in a way that
mattered.

The band `0.6 .. 1.6` is applied by `judge()` to **`med_fold`, the MEDIAN fold
across the subjects on the sheet** (`scan.py`, the `wide` branch), never to a
subject. So:

- **No individual animal is ever excluded by the band.** A mouse that falls to
  fold 0.55 inside an otherwise stable cohort is counted and its series is
  recovered. The previous wording here said the band "excludes an animal losing
  more than 40%". It does not, and that is better news than this section gave.
- **What the band rejects is a whole SHEET whose median animal moved outside
  it** — a cohort that ran to severe loss, or a growth study whose animals
  gained more than 60%. A toxicity arm, in other words, or juveniles. And it is
  rejected silently, as an ordinary non-match.
- `min_consistent = 0.0` for this profile, so the direction test never binds:
  the band is the only thing deciding.

That changes what the repair is. A per-subject counter would report zero
forever, because no subject is dropped there. The honest instrumentation is a
**rejection reason** — a sheet refused by the band should be able to say
*"median fold 0.42, outside 0.6 .. 1.6"* instead of vanishing into "no
per-animal table found". `judge()` returns `None` on rejection and has no
channel for that, so it is a real change with its own registration, not a
counter and not a config edit.

Fixing the band ITSELF still needs sheets known to contain endpoint-triggering
loss, and nobody has assembled them. Swapping one guess for another is not
progress.

### Precision needs ~100 hand-read verdicts, and has 20

`7 of 20` has a 95% interval of 14–56%. Separating a third from a half needs of
order a hundred items. That is acquisition work — reading sheets — not
engineering, and `CONTRIBUTING.md` exists to collect it. **No amount of code
changes this number.**

### The floor's unit is the sheet, and should be the arm

`PMC12545207` clears `min_subjects` on 51 pooled animals while contributing
experiments of 2 and 3. Making the floor arm-aware means teaching `judge` what
an arm is, which is a structural change to the accept decision with its own
registration and its own precision measurement. It is not a config edit.

### One worked builder, not two

`example/` carries a single source end to end. The contribution channel for
more exists and is empty. A second builder is worth more from someone else's
hands than from the author's — it is the one thing in this repository that
tests whether the protocol transfers.

### `gender` is a weak token in the human-data label

It matches the mouse's recorded sex (V14 found one B16F10 sheet mislabelled).
Not removed, because narrowing on the single item that exposed it is the same
error as widening. The label orders and does not reject, so the cost is bounded.

---

## V17 — can the ARTICLE filter what the spreadsheet cannot? REGISTERED

The tool reads supplementary bytes and article **metadata**, and never the
article. Two endpoints, `/search` and `/{pmcid}/supplementaryFiles`. `SKILL.md`
step 4 requires "the paper's own words" and gives no way to obtain them.

Most Source Data sheets are named by figure panel — `Fig 4c`, `Extended Data
Figure 3`, `Supplementary Fig. 8b`. **The legend for that panel states what the
panel shows.** If a sheet's legend can be retrieved and read, a large part of
step 4 becomes mechanical.

### What is measured, against V10's existing verdicts

V10 hand-read 20 accepted papers: 7 TRUE, 13 FALSE. Those verdicts are the
ground truth here.

> **P1 — RETRIEVABILITY. For 12 or more of the 20, the article's full text is
> fetchable AND a legend matching the sheet name can be located.**
> *FALSIFIER: fewer than 12* — sheet names do not map to legends often enough
> for this to be a general mechanism, whatever it does on the ones that match.
>
> **P2 — SEPARATION. Among the sheets whose legend IS located, a vocabulary
> fixed below separates TRUE from FALSE better than the scanner alone**, which
> on this sample is 7/20 = 35% precision. Concretely: precision among
> legend-positive sheets is **50% or better**.
> *FALSIFIER: below 50%* — the legend does not carry the signal, and reading
> the article is not the cheap win it looks like.

The vocabulary, fixed now so it cannot be chosen afterwards. A legend is
**positive** when it contains a growth-series phrase —

```
tumou?r (volume|growth|burden|size) | growth curve | tumou?r-?bearing
```

— and **negative** when it contains an in-vitro or aggregate phrase and no
growth phrase —

```
western|blot|immunoblot|qPCR|RT-PCR|flow cytometr|viability|proliferation assay
|migration|invasion|colocali|densitometr|mass spectrometr|proteomic
|transcriptomic|RNA-seq|survival curve|Kaplan
```

### The trap, named before the result

**V10's 20 papers are a TUNING SET for this rule**, not a score. The vocabulary
was written by someone who has read these twenty sheets. Whatever separation
appears here is in-sample and must be re-measured on papers this rule has never
seen before it is quoted as a precision figure. That is rule 9, and it applies
to a filter exactly as to a detector.

### The stop

Nothing in `scan.py` changes. If P1 and P2 hold, what ships is a **step in the
skill and a fetch helper** — the article as evidence a human or an agent reads,
never as an automatic gate. The tool triages on structure; the article informs
the person. Making the article decide would be the "decide on wording" error
protocol rule 1 exists to forbid.

### Result — both predictions CONFIRMED, and the article overturned one of V10's verdicts

| | | |
|---|---|---|
| **P1** | legend located for **16 of 20** | **CONFIRMED** (falsifier under 12) |
| **P2** | precision among legend-positive **4/7 = 57%** against the scanner's 35% | **CONFIRMED** (falsifier under 50%) |

**And it costs recall: 4 of 7 true positives retained.** As a gate that is a bad
trade — 22 points of precision for 43% of the recall — which is why the
registration said it ships as a step, not a gate. That holds.

### THE RETRACTION, WHICH IS WORTH MORE THAN THE PREDICTIONS

V10 scored `PMC7138317` `fig.6C` **FALSE**, noting it was *"unresolvable from
the documents"* — the sheet carries no unit, no animal label and no day label,
only `DMSO / Dox / ATMi-1`, six replicates and `Average`/`SD` rows, which read
as an in-vitro drug panel. V10 recorded that this was the single judgement call
in the sample and that scoring it TRUE would change the headline.

The article resolves it in one sentence. Figure 6's legend:

> "…(A-C) Tumor images (A) and tumor weight at day 28 (B), as well as **tumor
> volumes at the indicated time points (C)** … were **injected to the nude
> mice**…"

In vivo, per-animal, over days. **The verdict was wrong**, and the spreadsheet
could never have said so.

| | before | after |
|---|---|---|
| V10 precision | 7/20 = 35% | **8/20 = 40%**, 95% interval 19–61% |
| V10's **P1** ("lower than 6/15 = 40%") | reported CONFIRMED | **FALSIFIED** — it lands exactly equal |

V10 named this exact risk in advance: *"Scored TRUE it would be 8/20 = 40%,
exactly equal, and P1 would be falsified. One unresolvable sheet decides the
direction of this prediction."* It did. Corrected in `runs/v10_verdicts.csv`,
and in every place the figure is quoted.

### Why the three legend misses are the encouraging part

The three true positives the rule dropped were not cases where the legend lacked
the signal. `PMC12075843` and `PMC9970872` had the legend **located but the
wrong panel sliced out** by a crude regex; `PMC13396614`'s supplementary figure
legend is not in the full-text XML at all. So the ceiling here is set by naive
panel extraction, not by the article.

**That is the direct answer to whether a reader beats a regex: on this sample,
every miss was an extraction artifact.** An agent that fetches the legend and
reads it — rather than pattern-matching a 400-character slice — should recover
all three, and it resolved the retraction above by reading one sentence.

### What ships

A `--legend` fetch helper and a step in `SKILL.md` between triage and
verification: *fetch the article, find the legend for the sheet's panel, read it
before opening the workbook.* **Never a gate.** The tool decides on structure
(rule 1); the article is evidence for the person deciding, and V17 is exactly
why — it changed a human verdict, not a scanner verdict.

---

## V18 — agent-assisted precision on a sample nothing here has seen. REGISTERED, BEFORE ANY SHEET IS OPENED

Two things are now true at once and they do not fit together.

**The tool has a desk.** `desk.py` climbs the ladder for every candidate, hands
the evidence bundle to an adjudicator that sees nothing else, and puts what is
still open in front of a person with the reading already done. Nothing has
measured whether a verdict produced that way is worth anything.

**And the only precision figure this repository owns is spent.** V10's 20
papers were hand-read; V17 then wrote a legend vocabulary *while looking at
those twenty sheets* and reported 4 of 7 = 57% among legend-positive ones.
**That 57% is in-sample and is not quoted as a figure anywhere**, by V17's own
registration. The twenty are a tuning set now. They cannot score the thing that
was tuned on them.

So this measures the scanner and the agent at once, on papers neither has seen.

### The population, and the exclusion, both mechanical

`studies/precision_population.py`, new and committed with this registration,
because V10's population was built by an afternoon's script that did not
survive the day — and V15 is what that costs. It sweeps `si_cache/` with the
**shipped** configuration, takes the sheet `worklist.py` would put first for
each accepted paper, and excludes every paper carrying a verdict anywhere in
this repository, assembling that list from the artifacts rather than from
memory: V2's sample, V8's three, V9's ten, V10's twenty, V12's and V14's draws,
`example/worklist.csv`, `runs/worklist.csv`, and anything in `contributed/`.

V12's and V14's papers are excluded although neither study asked *this*
question — V12 read the sheets its change gained, V14 read ten for human versus
mouse. Someone has had those sheets open. Excluding them costs eligible papers
and biases nothing, which is the right direction to be wrong in.

Papers whose only tabular member was skipped for size are **NOT JUDGED** and
are not in the denominator (rule 11). Size skips are counted and reported.

**`random.seed(20260919)`, n = 20**, drawn into `runs/v18_sample.json` with the
population in `runs/v18_population.csv`, both written before any sheet is
opened and both committed here.

**What the sweep found, before anything was read:** 2,390 cached papers, 20,330
sheets, **2,753 accepted sheets across 484 papers**. Sixty-six of those papers
already carry a verdict somewhere in this repository, leaving **418 eligible**.
Twenty-two tabular members over 40 MB were skipped unread, and **8 papers had
no other tabular member: NOT JUDGED, and out of the denominator** rather than
counted as rejections.

V10 swept the same cache and found 480 accepted papers; this finds 484. That is
the expected size of V12's `Day1` axis (+11 sheets in 20,330) net of V13's `AGG`
repair (−1), recorded as a cross-check and not as a finding — and it is also the
concrete reason P1 must not be pooled with V10's `8 of 20`.

**ADDED, before a single verdict was answered: this population was
swept AT THE 40 MB CAP.** The 8 papers whose only tabular member is oversized
were `NOT JUDGED` and sit outside the denominator. V20 then opened those files
and found **6 of the 8 hold sheets the scanner accepts**. V18's figure therefore
describes the scanner *with the cap in force*, which is what ships today and
what the sample was drawn against. The draw is not re-rolled; V21 registers what
raising the cap is predicted to do instead. The configuration travels with the
number, as it must.

**The population caveat survives the result and is repeated because it does:**
`si_cache/` is the accumulation of past campaigns and of `journal_yield.py`'s
sweeps across 27 journals. It over-represents those journals, it is not a random
sample of the literature, and the direction of that bias is unknown.

### How a verdict is produced, fixed now so it cannot be arranged afterwards

1. `desk.py build` gathers L0/L1 from the row and L2/L3 from one `paper.py`
   fetch. It writes the bundles file: evidence only, sorted by PMCID, no
   ordering, no recommendation, no count.
2. An adjudicator instance sees **only that file** and writes
   `runs/v18_adjudications.csv` — `pmcid,sheet,verdict[,note]`, verdict TRUE /
   FALSE / UNRESOLVED. It is not told how many are needed, how many remain, or
   what the scout thought. **This file is sealed before the human sees
   anything.**
3. The human works the whole desk — all twenty, not only the unresolved pile.
   That is a departure from normal use and it is deliberate: it makes the
   agent-versus-human comparison twenty items instead of the two an audit quota
   would yield. `desk.py` never prints `agent_verdict`, and its selftest asserts
   that.
4. Answers land in `contributed/<handle>/<date>-v18.csv`, which is also the
   first batch in `contributed/`.

### The predictions

> **P1 — PRECISION REPLICATES. The human verdicts give between 4 and 12 TRUE
> of 20**, i.e. inside V10's 95% interval of 19–61%.
> *FALSIFIER: 3 or fewer, or 13 or more.* Then either the cache population has
> moved, or V11–V14 changed the accept decision more than their sheet counts
> implied, and `8 of 20` does not describe the scanner that ships today.
>
> **P2 — THE AGENT IS CLOSE BUT NOT A SUBSTITUTE. The bundle-only adjudicator
> agrees with the human on 16 or more of the items it settled.**
> *FALSIFIER: 15 or fewer.* Then an agent-assisted verdict cannot stand in for
> a hand read at all, 2-in-20 auditing is far too sparse to notice, and the
> desk must route everything to a person.
> **Denominator fixed in advance:** items the adjudicator returned TRUE or
> FALSE on. UNRESOLVED is not a disagreement and is counted separately. **If
> it settles fewer than 10 of 20, P2 is UNDERPOWERED and is reported as that,
> not as a rate.**
> This is a real bet and not `docs/EVAL.md`'s 20-of-21. That was two models
> agreeing with each other; agreement is not accuracy, and on the count — where
> truth was known — the same two agreed 12 of 18 and were wrong.
>
> **P3 — THE LEGEND IS RETRIEVABLE OUT OF SAMPLE. A legend for the sheet's own
> panel is located for 12 or more of the 20.**
> *FALSIFIER: fewer than 12.* V17's 16 of 20 was measured on the papers the
> matching rule was written against; this is the first time it meets sheet
> names it has never seen. Under 12 and `paper.py`'s claim on the tin is wrong.
>
> **P4 — L3 EARNS ITS RUNG. At least one item is settled on methods or claimed
> group size with no legend located.**
> *FALSIFIER: zero.* Then on this sample L3 carried nothing L2 had not already
> carried, and the honest response is to say so — a rung that settles nothing
> gets deleted rather than defended. **n = 20 can detect "never", not a rate.**

### The stop

**Nothing in `scan.py` changes in response, whichever way any of this falls**
(rule 9). No floor, no pattern, no band, no legend vocabulary.

**The sample is not extended because the answer is uncomfortable.** Twenty is
twenty: at p ≈ 0.4 the interval is about ±21 points, and separating a third
from a half still needs of order a hundred items.

**Where the agent and the human disagree, the human is the record**, and the
disagreement is written down rather than argued back. One exception, declared
now because V17 is exactly it: if *documentary* evidence settles the item — a
legend, a methods sentence — the verdict is corrected in place with a note and
the correction is reported as one. An agent's confidence is not documentary
evidence.

**A wall is not a result** (rule 10). No full text, not open access, a failed
fetch: the item stays in P1's denominator, because the human can still open the
sheet, and leaves P2's and P3's, because nothing was retrieved to judge.

**And the two figures never travel apart** (rule 3), nor without their floors
and their population. **P1's result must not be pooled with V10's `8 of 20`**:
V12 added the `Day1` axis and V13 closed `AGG`'s vocabulary holes, so these are
two configurations as well as two draws. Close numbers over different
configurations are two measurements, not forty items.

### Result — measured. P1, P3, P4 CONFIRMED; P2 FALSIFIED

Twenty human verdicts in `contributed/gcanudo-barreras/v18.csv`,
answered at `--audit-rate 1.0` through the desk, which never printed an agent
verdict. The human declared, before seeing any result, that they had not read
the V23 adjudicator's verdicts in the session chat (see V23).

| | registered | measured | |
|---|---|---|---|
| **P1** precision | 4–12 TRUE of 20 | **7 of 20 = 35%**, 95% interval ~18–57% | **CONFIRMED** |
| **P2** bundle-only agent vs human | ≥16 of the items it settled | **12 of 14** settled (6 UNRESOLVED) | **FALSIFIED** |
| **P3** legend located | ≥12 of 20 | **12 of 20** | **CONFIRMED**, on the line |
| **P4** L3 settles an item with no legend | ≥1 | **2** (`PMC13006418`, `PMC11452177`: counted series against the claimed group size) | **CONFIRMED** |

**P1 at the shipped configuration, out of sample: 7 of 20.** Not pooled with
V10's 8 of 20 (different configuration, different draw); the two say the same
thing, "about a third to two fifths", and neither separates those.

**P2 fails, and HOW it fails matters more than the rate.** Both of the
bundle-only adjudicator's errors are missed TRUEs (`PMC11078746`,
`PMC12909920`) and it returned no false TRUE at all; it also left 6 of 20
UNRESOLVED. Denied the sheet, it is cautious rather than wrong: it filters
nothing out that it should keep, but it misses real data and hands back a
third of the pile. By the registered consequence, a bundle-only agent cannot
stand in for a hand read. V23 asks what changes when it reads the sheet.

P3 lands exactly on its threshold, so it is not a margin; P4 holds on two
items, and L3 earns its rung.

**Why P2 failed, read afterwards from the adjudicator's own notes.**
In all three of its disagreements with the person, the bundle-only
adjudicator's reasoning rests on a legend that describes a DIFFERENT panel --
a FACS panel, an in-vitro CCK8 figure, an aggregate header -- which
`paper.py`'s sheet-to-legend matching had attached. Denied the sheet, it had
no way to see the mismatch. The sheet-reading adjudicator of V23 made none of
these errors. The legend rung is useful and fallible, and the sheet overrules
it.

---

## V19 — is the journal ranking a POLICY or a readout? REGISTERED, BEFORE THE SAMPLE IS DRAWN

`studies/journal_yield.csv` is the finding this project's paper rests on: 76% of
Communications Biology papers and 71% of Nature Communications papers carry a
sheet the scanner accepts, against 10% for Nature Medicine and 0% for the
general population. The stated mechanism is a **Source Data policy** rather than
prestige — Nature Medicine and Nature Cancer share a publisher and a field and
differ by a factor of five.

If that mechanism is real, it is **about publishing practice and not about
tumours**, and the ranking should survive a change of readout. Nobody has
checked. Every figure in that file was measured with `tumor_volume`.

### Two defects in the existing figure, found and fixed before this runs

**The floors are missing from the file.** It was measured at `min_subjects=5`;
V9 lowered the floor to 4 the following day. Lowering a floor can only ADD
acceptances, so those percentages are a **lower bound** at the shipped
configuration. The CSV recorded `profile` and `unit` and not the floors, so the
file could not say this about itself. It now writes `min_subjects`,
`min_points`, `sampled_on` and the id file.

**The sample was never written down.** `sample()` returned 100 PMCIDs per
journal, the run used them and discarded them, and the sort is `P_PDATE_D desc`
over an index that grows. So the earlier figures **cannot be re-derived on
their own population by anyone, including their author** — protocol rule 2
inverted. `freeze_ids()` now writes them, fsynced, before the first fetch, and
`--from-ids` re-scans a frozen list so two configurations can be compared on the
same papers.

**Consequence for this registration, stated before the result:** because the old
ids are gone, V19 draws a NEW sample. It therefore **cannot isolate the floor
change** from population drift between the two runs. What it can do is
compare two profiles over *the same frozen papers*, which is the question it
exists to ask.

### What is measured

Four journals, chosen now because they carry the contrast the paper rests on:
**Communications Biology (76%), Nature Communications (71%), Nature Cancer
(49%), Nature Medicine (10%)**. `--per-journal 100`. The drawn PMCIDs are frozen
to `studies/journal_yield_ids.csv` before anything is fetched, and BOTH passes
run over that same frozen list:

1. `tumor_volume`, `min_subjects=4`, `min_points=4` — the refreshed baseline
2. `body_weight`, same floors — the same papers, a different readout

Per-paper acceptance is written for both, so the overlap can be measured instead
of asserted.

### The predictions

> **P1 — THE REFRESHED BASELINE IS NOT LOWER. The `tumor_volume` yield is at or
> above the earlier figure in at least 3 of the 4 journals.**
> *FALSIFIER: 2 or fewer.* Then the floor drop is not what dominates this
> number, and either population drift or V12/V13's changes to `judge()` matter
> more than the floors do. **Confounded by construction** — this is a new sample
> — which is why the falsifier is a count of journals rather than a threshold on
> any single percentage.
>
> **P2 — THE RANKING SURVIVES THE READOUT. Under `body_weight`, Communications
> Biology and Nature Communications each exceed Nature Medicine by at least 20
> percentage points**, as they do under `tumor_volume`.
> *FALSIFIER: either of them does not.* Then the ranking is a property of the
> readout and not of the journal's data policy, and the paper's mechanism
> sentence is wrong as written. **This is the prediction that matters**: it is
> the difference between "these journals publish per-subject source data" and
> "these journals publish tumour curves".
>
> **P3 — THE PROFILES OVERLAP, AND BY HOW MUCH IS MEASURED RATHER THAN ASSUMED.
> At least 50% of the papers accepted under `body_weight` are also accepted
> under `tumor_volume`.**
> *FALSIFIER: under 50%.* `profiles/body_weight.toml` states that a treated
> tumour arm that barely grew falls inside the stable band, so heavy overlap is
> expected. **If it is heavy, P2 is weak evidence**: a ranking that survives
> because `body_weight` re-accepts the same tumour sheets says nothing about
> weight tables. P3 is what tells a reader how much P2 is worth, and it is
> registered here so that reading cannot be arranged afterwards.

### The stop

**Nothing is tuned in response** (rule 9): not the band, not the floors, not the
patterns, whatever any of this shows. `body_weight` has no measured recall and
V19 does not give it one — **an acceptance under that profile is not evidence
that a weight table was found**, only that the scanner accepted something under
it. That sentence travels with every number this produces.

If P2 fails, what changes is a sentence in the paper, not a line of code.


### Result — all three predictions CONFIRMED, P2 is worth nothing, and the useful finding was in none of them

400 papers, frozen to `studies/journal_yield_ids.csv` before the
first fetch; both passes over that same list. Artifacts:
`studies/v19_tumor_volume.csv`, `studies/v19_body_weight.csv`,
`studies/v19_papers_tumor_volume.csv`, `studies/v19_papers_body_weight.csv`.

**P1 — CONFIRMED, 4 of 4** (falsifier was 2 or fewer):

| journal | earlier run, `min_subjects=5` | V19 run, `min_subjects=4` |
|---|---|---|
| Communications Biology | 76% | **78%** |
| Nature Communications | 71% | **72%** |
| Nature Cancer | 49% | **51%** |
| Nature Medicine | 10% | **10%** |

One to two points, and nothing moved down. Consistent with a floor that can only
add — and **it does not isolate the floor**, because the earlier ids were
never written down and this is a new sample. That was declared before the run
and it stays declared. From today it is isolable: the ids are on disk.

**P2 — CONFIRMED, AND IT IS WORTH NOTHING.** Under `body_weight`,
Communications Biology (63%) and Nature Communications (64%) each beat Nature
Medicine (9%) by more than 50 points, far past the 20 the prediction asked for.

**P3 — CONFIRMED at 97%**, against a threshold of 50%:

| journal | TV accepted | BW accepted | both | BW only |
|---|---|---|---|---|
| Communications Biology | 78 | 63 | 59 | 4 |
| Nature Communications | 72 | 64 | 64 | 0 |
| Nature Cancer | 51 | 49 | 47 | 2 |
| Nature Medicine | 10 | 9 | 9 | 0 |
| **total** | **211** | **185** | **179** | **6** |

**179 of the 185 `body_weight` acceptances are papers `tumor_volume` had already
accepted. Six papers in four hundred are new.** The ranking survives the change
of readout because there was barely a change of readout: on this population the
two profiles are very nearly one instrument. P3 was registered precisely so this
reading could not be arranged afterwards, and it is the reading — **P2 confirms
nothing about weight tables.**

`body_weight` also accepts FEWER papers than `tumor_volume` in every journal. It
is close to a subset, not a different view.

### THE FINDING NO PREDICTION ANTICIPATED, and it is larger than all three

```
BASE = '("tumor volume" OR "tumour volume") AND HAS_FT:Y AND HAS_SUPPL:Y'
```

**Every paper in every journal's hundred already mentions tumour volume.** The
sampling frame is readout-constrained upstream of any profile, so this design
cannot answer the policy question with `body_weight`, with a new profile, or
with any profile at all. Swapping the instrument downstream of a filtered
population measures the instrument, not the population.

What the journal figures mean, stated exactly: *among papers that discuss tumour
volume and carry a supplement, journal X publishes a sheet this scanner accepts
N% of the time.* That is still the finding the paper rests on and it is still
worth publishing. It is **not** "journal X publishes per-subject source data N%
of the time", and V19 is the reason that sentence must not be written.

Testing the policy claim needs a different SAMPLING FRAME — a query that does not
name the readout, or a per-journal sample drawn with no readout term at all —
not a different profile. That is a new study with its own registration, and this
one has priced it.

### What ships

Nothing is tuned (rule 9). The band stays, the floors stay, the patterns stay.
What changes is `docs/FIGURES.md`, and any sentence that reads the journal
ranking as a statement about per-subject data in general.

---

## V20 — what the 40 MB cap costs, measured by opening the files it refuses. REGISTERED, BEFORE ANY OF THEM IS OPENED

V16 measured how often the size refusal fires: **22 tabular members over 40 MB,
across 19 of 2,390 papers, and in 8 of those the skipped member was the paper's
ONLY tabular file.** It then said, in the same breath, that it was not opening
them — *"parsing those is a real time and memory cost"* — and left the cap where
it was.

So the frequency is measured and **the cost in data is not**. For those 8 papers
the tool reports `NOT JUDGED`, honestly, about a file nobody has read.

The entire evidence base for what is inside such files is V1: four of them, from
one campaign, and **one held ten sheets the scanner accepts**. That is one
observation being asked to justify a rule that fires on 0.8% of the corpus.

### What is measured

`studies/big_member_cost.py`, new and committed with this registration. Every
tabular member over 40 MB in `si_cache/` is read **with no cap at all** and every
sheet in it goes through the shipped `judge_any`. Recorded per member: size,
whether it parsed, **wall-clock seconds**, sheets seen, sheets accepted, and the
best sheet's subject and timepoint counts.

Time is recorded because time is the argument FOR the cap, and it has never been
measured either. A member that parses in nine seconds and holds four accepted
sheets is a different fact from one that takes four minutes and holds none.

A member that cannot be parsed — MemoryError, a reader that refuses the format —
is a **WALL with its exception text**, not an empty file and not evidence that
the file holds nothing (rule 10).

### The predictions

> **P1 — THE CAP COSTS REAL DATA. At least one of the 8 papers whose only
> tabular member is oversized flips from NOT JUDGED to accepted.**
> *FALSIFIER: zero.* Then on this corpus the cap costs no data at all, those 8
> `NOT JUDGED` are honest and empty, and V1's single finding was a sampling
> accident rather than a rate.
>
> **P2 — TIME IS NOT THE BLOCKER IT IS ASSUMED TO BE. At least 11 of the 22
> members parse in under 60 seconds each.**
> *FALSIFIER: fewer than 11.* Then parsing cost is the binding constraint, the
> cap is well placed, and the argument for it stops being an assumption and
> becomes a measurement.

### The decision rule, fixed now so that the result cannot choose it

**The cap is raised only if ALL THREE hold:** at least 3 papers flip, the median
parse time is under 60 seconds, and no member fails for memory. Anything else
and **the cap stays at 40 MB** — what ships is the number, not a new threshold.

And whatever happens, `scan.py` is not edited in this study. The cap is a
constant in shipped code; moving it is a separate change with its own
measurement over the whole fixture set (`CONTRIBUTING.md`).


### Result — both predictions CONFIRMED, and the registered decision rule says the cap must move

Run over all 22 oversized members. Artifacts:
`studies/big_member_cost.csv`, `studies/big_member_cost.json`.

| | |
|---|---|
| members read with no cap | **22 of 22 parsed. 0 walls.** |
| members holding at least one accepted sheet | **15 of 22** |
| accepted sheets recovered | **84** |
| papers flipping NOT JUDGED to accepted | **6 of 8** |
| parse time | **median 0.4 s**, max 147.1 s |

**P1 — CONFIRMED, and not marginally.** Six of the eight papers whose only
tabular member was oversized hold sheets the scanner accepts: `PMC11735388`,
`PMC12518634`, `PMC13249897`, `PMC13392262`, `PMC13482816`, `PMC13550523`. Two
do not — `PMC11623927`, `PMC13036090` — and for those the `NOT JUDGED` was
honest and empty.

**P2 — CONFIRMED, 21 of 22 under 60 seconds** against a bar of 11. The full
distribution, in seconds:

```
0.1 0.1 0.2 0.2 0.2 0.2 0.2 0.3 0.3 0.4 0.4 0.4 0.4 0.6 0.9 1.1 1.1 1.2 1.3
3.4 3.6 147.1
```

Nineteen of the twenty-two parse in **under one and a half seconds**.

### The finding that outlives both predictions: bytes predict nothing

| member | size | time | accepted sheets |
|---|---|---|---|
| the largest in the set | **262.9 MB** | **3.4 s** | — |
| `PMC13392262` | 105.6 MB | 0.3 s | **13**, best sheet 395 subjects |
| `PMC13470634` supplement-7.csv | 108.0 MB | **147.1 s** | 0 |

**The 40 MB cap refuses on compressed size, and compressed size predicts
neither parse cost nor content.** A quarter-gigabyte workbook opens in three
seconds; the one slow member in the corpus is a flat CSV holding a single table
and nothing the scanner wants. The rule was protecting against a cost it never
measured, and paying for it in data it never counted.

That is the shape of rule 10's original defect: a refusal that could only
manufacture absence, in the direction the tool is expected to report anyway.

### The decision rule, applied

Registered in advance: raise the cap only if **at least 3 papers flip AND median
parse time is under 60 s AND nothing fails for memory.**

- 6 papers flip — **passes** (bar: 3)
- median 0.4 s — **passes** (bar: 60 s)
- 0 memory failures, 22 of 22 parsed — **passes**

**All three hold. By the rule fixed before the measurement, the cap moves.**

### What ships, and what deliberately does not ship yet

**Not the cap.** V20 registered that `scan.py` is not edited in this study, and
it is not. Moving `MAX_MEMBER` changes the shipped accept decision on 0.8% of
the corpus and needs its own registration and its own measurement over the whole
fixture set (`CONTRIBUTING.md`), including what it costs in wall clock on a full
campaign — 22 members is not 2,390 papers. That is V21, and it is queued behind
V18, because `scan.py` must not move while a precision sample is being answered
against it.

**And 84 acceptances are not 84 datasets** (rule 8). These are scanner
acceptances inside large Source Data workbooks — exactly the population V2 and
V10 found their false accepts in — and one of the best sheets here reports 395
subjects, a shape a gene matrix has more often than a mouse study does. The
number that travels is *84 accepted sheets across 15 members*, with precision
applying on top.

---

## V21 — raising the 40 MB cap. REGISTERED, BEFORE THE CHANGE IS WRITTEN AND BEFORE V18 HAS A SINGLE HUMAN ANSWER

V20's decision rule, fixed in advance and met on all three counts, says the cap
moves: 6 papers flip, median parse time 0.4 s, no memory failure in 22 of 22.
This is the change that does it, and it is registered now for a reason that
expires: **V18's twenty verdicts do not exist yet**. Once they do, any
prediction about what the cap does to precision is a prediction made by someone
who already knows the answer to the neighbouring question.

### The change, declared before it is written

`MAX_MEMBER` in `scan.py` and `mine.py` goes from 40 MB to **512 MB** — above
the largest member in the corpus (262.9 MB), so the cap stops binding on
anything currently cached rather than moving to a new arbitrary line that will
need moving again. The size refusal itself STAYS: a member over 512 MB is still
reported as `NOT JUDGED`, never as "no per-animal table found" (rule 11, V16).

### The predictions

> **P1 — PRECISION FALLS, and this is the whole reason to register before V18
> is answered.** The papers the cap admits are large multi-sheet Source Data
> workbooks — precisely the population V2 (7 of 9 false accepts) and V10 (4 of
> 13) found their discipline matrices in — and V20 already saw one of the best
> new sheets reporting **395 subjects**, a shape a gene matrix has far more
> often than a mouse study. So a precision sample drawn AFTER this change should
> sit **below** one drawn before it.
> *FALSIFIER: equal or higher.* Then large workbooks are no worse than the rest
> and the failure population has moved again, which is itself a finding.
> **V18 cannot score this** — V18 is drawn at the shipped cap. It needs its own
> draw afterwards, and that is the point: the prediction is on record before
> either number exists.
>
> **P2 — RECALL DOES NOT MOVE. 15/15 on the fixture set, negative control
> intact.** No fixture is anywhere near 40 MB, so the change must be inert
> there.
> *FALSIFIER: any movement at all* — then `MAX_MEMBER` is doing something other
> than what its name says.
>
> **P3 — A FULL CAMPAIGN DOES NOT GET MEASURABLY SLOWER.** Wall clock for a
> `precision_population.py` sweep of all 2,390 cached papers rises by **less
> than 10%** against V20's run of that same sweep.
> *FALSIFIER: 10% or more.* Twenty-two members are not 2,390 papers, and a
> median of 0.4 s over 22 files guarantees nothing about the tail. If the sweep
> gets materially slower the cap had a cost after all — just not the one it was
> justified with.

### The stop

The change ships only if **P2 holds exactly**: recall 15/15, control intact. P1
and P3 are measurements that travel with it, not gates — a precision drop is the
expected price of admitting more papers and it must be REPORTED, never used to
quietly revert a change the decision rule already approved.

Nothing else moves in the same commit: not the floors, not the patterns, not the
band.

### Not before V18

`scan.py` does not change while a precision sample is being answered against it.
V18 was drawn at the 40 MB cap and its figure will say so.

### Result

NOT YET MEASURED. Registered while `contributed/` was still empty, which is the
only moment this prediction is worth anything.

---

## V22 — does the label layer already sort the pile? REGISTERED, BEFORE V18 HAS A SINGLE HUMAN ANSWER

A diagnostic on V10's twenty (IN-SAMPLE, V10 is a tuning set, not quoted as a
figure): the existing labels flag 4 of the 12 false accepts and 1 of the 8 true
ones, and the eight they miss are in-vitro (5) and omics (3) sheets that
structure cannot separate from a mouse growth curve. One split looked large:
**tier A = `hdr` contains `t` AND `signature` is empty** held 5 of 7 true,
the rest 3 of 13.

That split was found by looking, so it is worth nothing until it meets sheets
it has not seen. V18's twenty are exactly that, and their human verdicts do not
exist yet.

> **P1 — TIER A IS AT LEAST 20 POINTS MORE PRECISE THAN THE REST** on V18's
> human verdicts. Tiers are computed mechanically from `hdr` and `signature` in
> `runs/v18_sample.json`, which were written before any sheet was opened.
> *FALSIFIER: a gap under 20 points, or reversed.* Then the label layer orders
> nothing and `worklist.py`'s sort key is decoration.
> **If either tier holds fewer than 5 items, P1 is UNDERPOWERED** and is
> reported as that, not as a gap.

Nothing in `scan.py` or `worklist.py` changes on this result alone (rule 9).

### Result — measured on V18's human verdicts. P1 CONFIRMED, and weak

| tier | items | human TRUE | precision |
|---|---|---|---|
| **A** (`hdr` has `t`, no signature) | 8 | 4 | **50%** |
| B (the rest) | 12 | 3 | 25% |

A gap of **25 points against a registered 20**: CONFIRMED, and both tiers
hold 5 or more items, so it is not formally underpowered. It is weak all the
same: one verdict moved the other way turns it into a 12.5-point gap, and the
contested item in V23 sits in tier A. What it licenses is what it was
registered to test -- the worklist's existing sort key orders something --
and nothing more. No tier label is shown to users on this result.

## V23 — a high-reasoning model with ALL the evidence, against the same twenty. REGISTERED, BEFORE ANY V18 SHEET IS OPENED BY IT

V18 measures an adjudicator (Claude Opus 5) that saw the evidence bundle alone:
legend, method sentences, claimed group sizes. It never saw the sheet. The
question worth asking before recommending any model to users is the one a user
would actually run: **the model reads the sheet, the bundle, and the full
article, as a person would.**

**The adjudicator is Claude Opus 5.5** (`claude-opus-5-5`), run in an
interactive session. Declared contamination, because it cannot be removed: in
that session it had read `runs/v10_verdicts.csv` (twenty papers disjoint from
V18 by construction) and this repository's documented failure modes. It has
NOT read `runs/v18_adjudications.csv`, `runs/v18_r1_adjudications.csv` or
`runs/v18_desk.json`, and does not until its own file is committed.

### The question, fixed now

**TRUE** — the sheet holds, for at least one arm, one value per individual
animal at four or more time points, of an in-vivo tumour-growth readout
(volume, diameters, area, or bioluminescent tumour burden). **FALSE** —
anything else: group means, in vitro, omics, human data, per-animal body
weight, survival, a single endpoint. **UNRESOLVED** — the evidence reachable
from open sources does not settle it.

Each verdict records the **readout** it saw, so that a disagreement over
definition (bioluminescence is the likely one) can be separated from a
disagreement over fact.

### Evidence, fixed now

For each item: the V18 bundle; the sheet itself (`desk.sheet_excerpt` and, if
that is not enough, the parsed rows); and, only when those leave it open, the
full-text XML from Europe PMC. Each verdict names the highest rung it used.

The verdicts go to `runs/v23_adjudications.csv` —
`pmcid,sheet,verdict,readout,rung,note` — **committed before the human answers
anything**. The human answers through the V18 desk as registered there, which
never prints an agent verdict; they must not open `runs/v23_*` until done.

### The predictions

> **P1 — IT SETTLES ALMOST EVERYTHING. UNRESOLVED on 2 or fewer of 20.**
> *FALSIFIER: 3 or more.* Then reading the sheet and the article does not
> close what the bundle left open, and L4 is not worth its cost.
>
> **P2 — IT AGREES WITH THE HUMAN on 18 or more of the items it settled.**
> *FALSIFIER: 17 or fewer.*
>
> **P3 — THE EXPENSIVE ERROR IS RARE. At most ONE item where it says TRUE and
> the human says FALSE.** This is the error a user pays for: a sheet presented
> as data that is not.
> *FALSIFIER: two or more.*
>
> **P4 — MORE EVIDENCE BEATS LESS.** Items settled AND agreeing with the human:
> V23 ≥ V18's bundle-only adjudicator, on the same human answers.
> *FALSIFIER: fewer.*

### The decision rule, fixed now

`SKILL.md` may recommend **"a high-reasoning model reading the sheet, legend
and methods as the adjudicator, with the desk's human audit quota kept"** if
and only if **P2 and P3 both hold**. It names the model that was measured and
no other: a model family is not a measurement, and any other model is
recommended by running this same protocol on it, not by analogy. If P2 or P3
fails, the recommendation stays what it is: a person reads every sheet.

n = 20. At 18 of 20 the 95% interval on agreement is roughly 68–99%. This can
rule out "an agent is useless" and "an agent is a coin"; it cannot certify an
agent as a substitute for a person, and nothing written from it may say so.

### Result — measured. All four predictions CONFIRMED; the decision rule is met

**The human declared, in writing and before seeing any result: they had NOT
read the adjudicator's verdicts in the chat.** The design stands as
registered.

| | registered | measured | |
|---|---|---|---|
| **P1** UNRESOLVED | ≤2 of 20 | **0** | **CONFIRMED** |
| **P2** agreement with the human | ≥18 of the items settled | **19 of 20** (95% interval ~76–99%) | **CONFIRMED** |
| **P3** agent TRUE / human FALSE | ≤1 | **1** (`PMC9767871`) | **CONFIRMED**, on the line |
| **P4** settled-and-agreeing vs V18's bundle-only agent | V23 ≥ V18 | **19 vs 12** | **CONFIRMED** |

Against the same twenty human answers:

| adjudicator | evidence | unresolved | agrees | agent TRUE / human FALSE | agent FALSE / human TRUE |
|---|---|---|---|---|---|
| Claude Opus 5 (V18) | legend, methods, claimed n | 6 | 12 of 14 | 0 | 2 |
| **Claude Opus 5.5 (V23)** | **+ the sheet itself** | **0** | **19 of 20** | **1** | **0** |

The difference is the evidence as much as the model, and this design cannot
separate the two: V18's adjudicator was denied the sheet by construction.

**The one disagreement.** `PMC9767871` `Ext.Fig. 6f`: adjudicator TRUE, human
FALSE with the note *"Parece una serie longitudinal, pero de sgNT IgG"*. The
sheet's own title reads **`Tumor growth (Panc02)`**, over `Day after
injection` and four column groups `sgNT IgG`, `sgNT αCD8`, `sgSlc4a4`,
`sgSlc4a4 αCD8` -- arm names (non-targeting or Slc4a4-targeting sgRNA, with
isotype or anti-CD8 antibody), not a readout. That is documentary evidence of
exactly the kind this registration's stop allows to correct a verdict in
place. **It is not applied here.** The human is the record; the evidence has
been put to them, and any change is reported as a second round beside this
one, as V17 and V18's adjudications were. The figures above are round 1.

**The decision rule, applied.** P2 and P3 both hold. `skills/unpool/SKILL.md`
may now recommend: *Claude Opus 5.5 (`claude-opus-5-5`), reading the sheet,
the legend and the methods, as the adjudicator -- with the desk's human audit
quota kept*. It names that model and no other; any other model is recommended
by running this protocol on it. n = 20: this rules out "an agent is useless"
and "an agent is a coin", and it certifies nothing as a substitute for a
person.

### Round 2 — the human corrects one verdict on documentary evidence

Shown the sheet's title (`Tumor growth (Panc02)`) and its column groups, the
human re-read `PMC9767871` `Ext.Fig. 6f` and changed FALSE to TRUE: *"la había
malinterpretado yo"* -- `sgNT IgG` had been read as the readout, and it is an
arm. Corrected in place in the human's file, round 1's verdict and note kept
inside the new note, exactly as V17 corrected V10.

| | round 1 (independent) | round 2 (after the correction) |
|---|---|---|
| V18 P1 precision | 7 of 20 = 35% | **8 of 20 = 40%** (~22–61%) |
| V18 P2 Opus 5, bundle only | 12 of 14 | 11 of 14 |
| V22 tier A vs B | 4/8 vs 3/12 (25 pts) | 5/8 vs 3/12 (37.5 pts) |
| V23 Opus 5.5 agreement | **19 of 20** | 20 of 20 |
| V23 agent TRUE / human FALSE | 1 | 0 |

**What each round is good for, and they are not interchangeable.** Round 2
is the better estimate of what the sheets HOLD, so precision is quoted as 8
of 20. It is NOT a measurement of agent-versus-person agreement: the one
changed verdict changed because the person read the agent's argument, which
is precisely the dependence this study was built to exclude. **The agreement
figure that may be quoted is round 1's 19 of 20.** Round 2 adds one
qualitative finding instead: the single disagreement was a person's misread
that the agent's evidence corrected, not an agent's false TRUE -- on this
sample, the expensive error did not occur at all.

And the error ran the other way. The person had discarded a legitimate
per-subject series that the agent kept -- 34 per-subject columns in 4 arms,
days 7-22, as `unpool extract` counts them; no builder has counted the mice.
Without the agent it would have been lost from the registry. That is one
item -- an observation, not a rate -- but it says the agent is worth more as
a SECOND READER whose disagreements go back to the person than as a filter
in front of them. The desk hides agent verdicts, correctly, while a sample is
being measured; outside a measurement, the disagreements are exactly what a
person should see again.

**ADDED, when the verdicts were sealed and before the human has
answered anything — a breach of this registration's own firewall, recorded
rather than hidden.** The adjudicator worked in an interactive session and
narrated its verdicts in the chat as it reached them, item by item, in a
window the human answering V18 can read. Whether the human had read them
before answering is the only thing that decides what this study is worth, so
the human declares it, in writing, beside the answers:

- **not read** — the design stands as registered;
- **read** — P2, P3 and P4 are not measured, and neither is V18's P2, whose
  human would have seen an agent's opinion (not V18's, but correlated with
  it). V18's P1 is reported with the same caveat. The clean repair is a
  second person who has seen neither.

The sheet itself was sufficient on all 20 items; no full-text read (L4) was
needed. The rung each verdict used is in the file.

---

## V24 — how many ACCEPTED PAPERS hold real per-subject data, not just their first sheet. REGISTERED, BEFORE ANY OF THE 26 SHEETS IS OPENED

V18 measures one sheet per paper -- the one `worklist.py` puts first -- and
finds 8 of 20 real (round 2). A user does not care which sheet; they care
whether the paper the tool proposed has the data. Of V18's 12 FALSE papers, 5
have no other sheet the scanner accepts, and 7 have **26** that nobody has
read (`runs/v24_sample.json`, enumerated mechanically before any was opened).
So paper-level precision is somewhere between 8/20 and 15/20, unmeasured.

### Procedure, fixed now

1. **Claude Opus 5.5 screens all 26**, reading each sheet (`unpool sheet`)
   and, where the sheet leaves it open, the legend and methods (`unpool
   paper`). Same question as V23: one value per individual animal at four or
   more time points, of an in-vivo tumour-growth readout (volume, diameters,
   area, bioluminescent burden). Verdicts go to `runs/v24_adjudications.csv`
   and are **committed before the human sees any item**. They are not
   narrated in the session chat this time (V23's breach).
2. The human then answers, blind to every agent verdict, through the desk: a
   pile of **every agent-TRUE sheet plus an audit of 5 agent-FALSE sheets**
   (all of them if fewer), drawn with `random.seed(20260925)` and shuffled
   together. The human knows the pile is mostly agent-TRUE; that is declared,
   because it is how the second-reader workflow would run for real.
3. A paper counts TRUE if **any** of its sheets is TRUE by the human. An
   agent-FALSE sheet outside the audit stays `screened`, and the paper-level
   figure is reported with those sheets named.

Declared contamination: the adjudicator read these seven papers' V18 bundles
(legend, methods, claimed n) during V23. It has not opened any of the 26.

### The predictions

> **P1 — 2 TO 4 OF THE 7 PAPERS TURN OUT TO HOLD A REAL SERIES**, so
> paper-level precision is 10-12 of 20, against 8 for the first sheet.
> *FALSIFIER: 0-1, or 5-7.* Low: the first sheet was a good proxy for the
> paper and the ranking lost almost nothing. High: the ranking routinely puts
> the wrong sheet first, and the worklist's order is costing real data.
>
> **P2 — THE SECOND READER HOLDS.** The human confirms every agent-TRUE sheet
> but at most one, and finds none of the audited agent-FALSE sheets TRUE.
> *FALSIFIER: two or more agent-TRUEs rejected, or any audited FALSE found
> TRUE.* Then V23's 19/20 did not carry to a pile the agent screened alone.

### The stop

Nothing in `scan.py` or `worklist.py` changes on this result (rule 9). If P1's
high side comes true, the ranking gets its own registered study; it is not
retuned here. Paper-level precision is quoted beside V18's sheet-level figure,
never instead of it, with its unit named.

### Result — measured. P1 FALSIFIED on the low side; P2 CONFIRMED

The human answered the blind pile of 6 (`contributed/gcanudo-barreras/v24.csv`,
pile in `runs/v24_pile.csv`) and declared, before any result, that they had
opened none of the adjudicator's tool calls, which carried its verdicts.

| | registered | measured | |
|---|---|---|---|
| **P1** papers that flip | 2-4 of 7 | **1 of 7** (`PMC9498964`, a `Tumor Volume` block in `S5_Data. Tumors (Fig 1)`) | **FALSIFIED**, low |
| **P2** second reader | every agent-TRUE but ≤1 confirmed; no audited FALSE found TRUE | **1 of 1 confirmed; 0 of 5 audited FALSE found TRUE** | **CONFIRMED** |

**Paper-level precision: 9 of 20 = 45%** (95% interval ~26-66%), against 8 of
20 for the first sheet alone. The unit is the PAPER: a paper counts if any
sheet the scanner accepts in it holds a real per-subject series. 20 of the 26
sheets are agent-FALSE and were not audited; they stay `screened`, and the
figure rests on them.

**What the falsification says.** The registered reading of the low side: the
first sheet was a good proxy for the paper, and the worklist's order cost
almost nothing -- one paper in seven had its data behind a FALSE first sheet.
The upper bound of 15/20 was never close: the FALSE papers are, sheet after
sheet, in-vitro, omics and release-kinetics papers. No ranking study follows
from this.

Agent and human agreed on 6 of 6, and together with V23's round 1 that is 25
of 26 across both studies. The human's note on one item -- *"hay un estudio
longitudinal, pero no encuentro los datos"* -- is the paper whose data sat in
another file of its supplement, which is the case this study exists for.

One observation outside the question: `PMC12501270`'s methods describe caliper
volumes in mice, and none of its accepted sheets holds them. Either they were
not published as data or they sit in a sheet the scanner rejects -- a recall
question, not measured here.


---

## V25 — the system end to end, with a second reader. REGISTERED, BEFORE THE CAMPAIGN IS MINED

V23 and V24 say the agent's kept sheets were real 9 of 9 and that it matched a
person 25 times in 26. Three things stop that from being the claim "the
system finds the data and hands it to you": n is 9; the only person is the
tool's own author; and "hands it to you" includes an extraction nobody has
scored on unseen sheets.

### Procedure, fixed now

1. **A fresh campaign, fixed here:** `unpool mine "patient-derived xenograft"
   --journal "Nature Communications" --budget 50 --tag v25`, every paper
   carrying a verdict anywhere in this repository excluded
   (`studies/precision_population.known_verdicts`). Step by step in
   `docs/V25_RUNBOOK.md`.
2. **The agent screens every sheet the scanner accepts** in every accepted
   paper (Claude Opus 5.5, `unpool sheet` + `unpool paper`), and for each sheet
   it keeps it runs `unpool extract` and fills `arm` from the legend. Verdicts
   and a SUMMARY of each extraction (blocks, subjects, time grid, arms -- never
   the values, which are publisher bytes) are committed before any person
   sees an item. The adjudicator is a fresh session that has not read the
   verdicts of any earlier study.
3. **Two people answer blind and apart** through `desk queue --review`:
   rater A (the author) and **rater B, someone outside this project**. Each
   sees every agent-TRUE plus a seeded 20% audit of agent-FALSE
   (`random.seed(20260926)`), never the agent's verdict nor the other rater's.
4. For every sheet a rater confirms, they also check the extraction: subject
   count, time grid, and arm assignment against the sheet and the legend.
5. Each phase's wall-clock start and end is written down as it happens.

### The predictions

> **P1 — DELIVERED PRECISION ≥ 85%**: of the sheets the agent keeps, rater A
> confirms 85% or more. *FALSIFIER: under 85%.* **Underpowered, and reported
> as that, if the agent keeps fewer than 15 sheets.**
>
> **P2 — THE PEOPLE AGREE WITH EACH OTHER ≥ 90%** on the pile, and the agent
> agrees with each of them no worse than they agree with each other.
> *FALSIFIER: either fails.* Without rater B, P2 is NOT RUN -- not passed.
>
> **P3 — EXTRACTION IS RIGHT ON ≥ 80% OF CONFIRMED SHEETS**: subject count,
> time grid and arms all correct as rater A reads them.
> *FALSIFIER: under 80%.* Then "hands you the data" means "hands you a
> sheet", and the README says so.
>
> **P4 — DESCRIPTIVE, NO PREDICTION**: person-minutes per verified dataset,
> and agent wall-clock per paper. No speed claim is made from this alone:
> "faster" needs a baseline, and none is measured here.

### The stop

Nothing in `scan.py`, `extract.py` or the agent's instructions changes
between the campaign and the answers (rule 9). The README's delivered-precision
sentence is replaced by V25's figure, whichever way it falls, with its
interval and both raters' agreement beside it.

### Result

**Round 1 MEASURED for P1, P2, P4; P3 measured, below.** Written and
committed before any reconciliation; the P3 set is fixed at the 74 rows of
`runs/v25_extraction_check.csv`.

Campaign: 50 papers mined, 224 candidate sheets in 35 papers, 9 papers
excluded as already adjudicated, **173 accepted sheets in 26 papers** screened
by the agent. Desk (`--review --audit-rate 0.2 --seed 20260926`): every
agent-TRUE plus a seeded audit of agent-FALSE, **95 sheets**, all answered by
rater A, none skipped.

| | agent TRUE | agent FALSE (audit) |
|---|---|---|
| rater A TRUE | 74 | 1 |
| rater A FALSE | 1 | 19 |

> **P1 -- PASSED.** Delivered precision **74/75 = 98.7 %** (Wilson 95 %
> 92.8-99.8), unit = accepted sheet, the agent reading sheet + legend +
> methods. n = 75 >= 15: powered as registered.
>
> **P2 -- NOT RUN** (no rater B, decided before answering, see below). For
> the record only, not a P2 result: agent-rater A agreement 93/95 (92.6-99.4);
> on the audit, 19/20.
>
> **P3 -- FALSIFIED** (measured, see "P3, measured" below):
> extraction right on **31 of 50** checked sheets, **62 %** (Wilson 95 %
> 48-74), against a threshold of 80 %.
>
> **P4 -- DESCRIPTIVE.** Rater A: 90 person-minutes for 95 sheets (self-reported
> total over several sessions, per-session times not recorded), about 57 s per
> sheet. Agent wall-clock (`runs/v25_timeline.csv`): mine 7 min, screen ~16
> min for 173 sheets, extract + arm assignment ~7 min, desk build 1.5 min.
> No speed claim: there is no baseline.

The two disagreements go to reconciliation, reported as round 2 beside this:
`PMC13490547 / Figure 6 (Nov 2025)` (agent TRUE, rater FALSE) and
`PMC13562552 / Figure 5e` (agent FALSE, rater TRUE).

**Round 2 (reconciliation), beside round 1, not replacing it.**
Rater A saw the agent's verdict and note on the two disagreements only:
`PMC13490547 / Figure 6 (Nov 2025)` changed FALSE -> TRUE ("the growth is
shown as photographs of animals in the figure, not a curve; the per-mouse
series is on the sheet"); `PMC13562552 / Figure 5e` changed TRUE -> FALSE on a
second pass ("the tumour volume is in Figure 5f, not 5e"; first kept TRUE,
then corrected by the rater, who had mixed up which side held which verdict).
Round 2: agent-TRUE confirmed **75/75**; audit 20/20; overall 95/95. Round 1 is the registered figure; round 2 is what `registry.csv` holds.

**P3, measured.** Rater A checked the first **50 of the 74**
rows of `runs/v25_extraction_check.csv`, in file order (15 of the 21 papers),
with `unpool desk check`, one logged session of 79 minutes
(`runs/v25_timeline.csv`). Row by row: is the subject count right, is the
time grid right, is each block's arm right, as rater A reads the sheet and
the legend.

*The stop at 50, and why it is not optional stopping.* Rater A stopped at 50
rows, a time decision stated before any P3 rate had been computed: the only
figures produced up to then were progress counts (rows answered). The
registered set was 74; the 24 unchecked rows cannot change the verdict --
were every one of them right on all three, P3 would read 55/74 = 74 %, still
under 80 %. The first 7 rows were answered before the rater had settled the
method (the attempt is kept in the development history) and are counted as
answered; without them P3 reads 29/43 = 67 % (53-80), the same verdict. The
rule for blocks the agent marked MIXED was never fixed; it is immaterial,
since 2 of the 50 rows carry one.

| column | right | % | Wilson 95 % |
|---|---|---|---|
| subjects | 33/50 | 66 % | 52-78 |
| time grid | 39/50 | 78 % | 65-87 |
| arms | 42/50 | 84 % | 71-92 |
| **all three (P3)** | **31/50** | **62 %** | **48-74** |

Reproduced by `python studies/v25_p3.py --answered`.

*Why the subject count fails* -- the 17 rows marked `subjects_ok = no`, read
from the agent's summary and the rater's notes, after scoring:
- **8: a block the agent itself had set aside still counted.** The agent
  marked a block `NOT TUMOUR` (body weights, an in-vitro plate) or `NOT A
  READOUT` (a survival table), and wrote `subjects` as `extract`'s total over
  every block. The rater's notes give the corrected count in several
  ("removing b5 the count is right", "it is 32"). This one is the agent's
  procedure, not `extract`: the count was never re-derived after the arms
  were assigned (rater A's diagnosis).
- **6: `extract` returned nothing** (`blocks 0`) from a sheet that holds a
  series -- these fail all three columns.
- **3: a block cut wrong** -- an arm left out, a day column read as a subject,
  panels pooled.

*Sensitivity, post hoc, NOT a P3 figure:* in 7 of the 8 set-aside rows the
times and arms were right, so had the set-aside blocks been subtracted, P3
would have read **at most 38/50 = 76 %** -- still under 80 %. The fix is
registered and measured on a fresh campaign (V26, amendment 2), never on
these rows.

*What the registration says follows:* "hands you the data" means "hands you a
sheet", and the README says so. The system finds the right sheet (P1, 98.7 %);
its extraction is a starting point a person checks, not the data.

**P3, round 2, beside round 1, not replacing it.** Counting
subjects over the kept blocks only (V26 part C) changes the total on 16 of
the 50 rows. On 5 the rater's round-1 note already gave the count; the other
11 the rater recounted from the sheet without seeing either total
(`runs/v25_round2_counts.csv`), then saw the
agent's per-block reading and reconciled:
- **8 sheets, rater's error:** the rater had counted the rows of a body-weight
  or IHC block as further animals; they are the same mice. Only sheets that
  carry such a block are affected, all among the last rows checked (rater A:
  "an error in these last ones"), so the unrecounted rows are not presumed to
  share it. On 7 of them the
  rater had said `subjects_ok = yes` to a total that double-counted.
- **PMC13493945 Figure S5:** recount 24 against a total of 30 the rater had
  accepted in round 1 -- also a round-1 `yes` that the recount reverses.
- **PMC13490547 Figure 7 (Nov 2025):** recount 74, neither total right (a
  block cut wrong); already `no` in round 1.

| | subjects right | all three right |
|---|---|---|
| round 1, as registered | 33/50 = 66 % (52-78) | **31/50 = 62 % (48-74)** |
| round 2, the agent's V25 totals | 25/50 = 50 % (37-63) | 23/50 = 46 % (33-60) |
| round 2, totals over kept blocks (part C, **post hoc**) | 39/50 = 78 % (65-87) | 36/50 = 72 % (58-83) |

Round 1 is the registered figure and P3 stays FALSIFIED. Round 2 says the
extraction as delivered in V25 was worse than round 1 read it, and that the
part-C counting would have recovered most of the subject errors -- but that
last row is measured on the very rows that suggested the fix, and on the 34
unchanged rows no recount was made. It is a reason to expect C-P1 to hold,
not a measurement; V26 is.

**P4, the extraction check:** 79 person-minutes for 50 rows, about 95 s a row
(logged per session this time, by `desk check`).

**Rater B: none.** After the seal and BEFORE rater A
answered any item, the author decided to run V25 without a second reader.
Consequences, fixed now rather than after the answers: **P2 is NOT RUN -- not
passed**; P1, P3 and P4 rest on rater A, the tool's own author, which is the
objection V25 was registered to remove and which therefore still stands; the
README's delivered-precision sentence carries V25's figure with its interval
and says that no second reader was used. The procedure is not otherwise amended.


## V26 — the desk reads the blocks, and extraction follows the figure's panels. REGISTERED, BEFORE V25's P3 HAS A SINGLE ANSWER AND BEFORE ANY OF THIS IS WRITTEN

Written while `runs/v25_extraction_check.csv` holds 0 of 74 answers
(`python studies/v25_p3.py`: NOT SCORED, 74 open). Nothing here may be
adjusted after those answers are read: they are V26's test set.

Two changes, two parts, measured apart. Part A changes what the PERSON sees;
part B changes what `extract` returns. Neither changes what the scanner
accepts.

### Part A — the desk shows the mechanical blocks before the answer, and the agent's arms only after it

**The campaign, fixed now:** `unpool mine '"MC38" OR "CT26"' --journal
"Nature Communications" --budget 50 --tag v26 --workers 4`, every paper
carrying a verdict anywhere in this repository excluded, as in V25. The two
commonest syngeneic immunotherapy models: the query a researcher would type,
a model class V25 did not cover, and V25's journal, so the journal is not a
second change.

**The change.** (1) At seal time the adjudicator runs `unpool extract` on
EVERY sheet it screens, TRUE and FALSE alike, so the existence of an
extraction says nothing about the verdict. (2) Each desk item is drawn, with
the desk's seed, into one of two halves: in the SHOWN half `desk queue`
prints, before the answer, `extract`'s own summary -- blocks, subjects per
block, time grid, raw block labels -- and nothing the agent wrote; in the
HIDDEN half it prints what V25's desk printed. (3) After a human TRUE, and
only after that verdict is written, it prints the agent's arm assignment and
asks `subjects_ok`, `times_ok`, `arms_ok` (step 5 of V25 folded into the
desk). (4) Every answer is written with its `answered_at` timestamp. (5) The
audit of agent-FALSE sheets is a FIXED seeded draw of 20, not a rate, split
10 and 10 by the same draw.

> **A-P1 — BLINDNESS HOLDS MECHANICALLY.** The desk selftest feeds an item
> whose agent fields carry a sentinel string and asserts the sentinel is not
> written to stdout before the verdict is appended to the answers file.
> *FALSIFIER: the sentinel appears before the answer.* A failure stops part A.
>
> **A-P2 — THE BLOCKS DO NOT PULL THE PERSON TOWARD TRUE.** On the 20 audit
> sheets rater A says TRUE on at most 2 (V25 round 1: 1 of 20).
> *FALSIFIER: 3 or more of 20.* Power, stated now: at V25's 5 % this
> falsifies by chance 7.5 % of the time; a real rise to 20 % goes undetected
> 21 % of the time, so only a gross anchoring (the rate tripling) is
> detectable. SHOWN and HIDDEN audit halves are reported side by side,
> 10 each, as description only.
>
> **A-P3 — THE CHANGE SAVES TIME, MEASURED WITHIN THE CAMPAIGN.** Median
> seconds per item (from consecutive `answered_at`, the first item of each
> session dropped), SHOWN half against HIDDEN half, extraction check
> included. Predicted lower in SHOWN. *FALSIFIER: SHOWN median ≥ HIDDEN
> median.* V25's 90 person-minutes are not a baseline: a different campaign,
> self-reported, before the rater had practised.
>
> **A-P4 — DESCRIPTIVE, NO PREDICTION.** Delivered precision, with its
> interval, beside V25's. It is not a safeguard here: anchoring would RAISE
> it, which is why A-P2, not this, is the test of anchoring.

### Part B — `extract` splits blocks at the figure's panels

V25's adjudicator wrote, on the first extraction row, that blocks "pool
several arms and panels, so an arm per block cannot be assigned". That is one
sheet, and rule 9 forbids fixing it. The registration is therefore of a
PROCEDURE, and the mechanism is decided on other sheets.

**Development set, fixed now:** the sheets of `registry.csv` and the sheets
of V18 and V24 whose human verdict is TRUE. **No sheet of V25 is opened while
part B is written**, and no row of `runs/v25_extraction_check.csv` is read
except through `studies/v25_p3.py`'s counts. The session that writes part B
first lists, on the development set only, every block that carries more than
one arm or panel, and commits that list before writing code.

**Stops, fixed now:**
- the target set is the V25 sheets with `arms_ok = no` AND at least one
  block the sealed extraction marks `MIXED` (`runs/v25_extractions.csv`,
  written before any rater answered). A `no` on a sheet with no MIXED block
  is a misread legend, which splitting blocks does not touch. If the target
  set holds fewer than 5 sheets, part B is not written: there is no measured
  failure to fix;
- if the development set holds no pooled block, part B is not written: the
  only example would be the file in front of us.

**Test set:** V25's 74 checked sheets. A fresh session reruns `extract` with
the change and reassigns arms from the legend, without reading rater A's
check. Rater A re-checks, via `desk check`, the rows whose extraction summary
changed MIXED with an equal-sized seeded draw of unchanged rows, all
unlabelled and in seeded order, so the rater cannot tell which version is
the new one. The unchanged rows also give rater A's test-retest agreement
with their own P3 answers, reported beside B-P1.

> **B-P1 — POOLED BLOCKS GET FIXED.** Of the target set, at least half become
> `arms_ok = yes`. *FALSIFIER: fewer than half.* Underpowered, and reported
> as that, below 8 sheets: at 5, a fix that truly works 70 % of the time
> fails this 16 % of the time.
>
> **B-P2 — NOTHING THAT WORKED BREAKS.** Of the sheets marked
> `subjects_ok = times_ok = arms_ok = yes`, at most 1 becomes `no` in any
> column. A sheet whose extraction summary is byte-identical carries its
> answers over unchanged. *FALSIFIER: 2 or more.*
>
> **B-P3 — THE RECORDS STILL REPRODUCE.** The worked example's 369 values and
> every builder in `builders/` come out of `extract` unchanged, and
> `tests/test_smoke.py` and `tests/test_recall.py` pass. *FALSIFIER: any
> difference.*

### Amended the same day, before any answer to V25's P3 or any V26 sheet

A review of this registration's own thresholds, before data: A-P4 tested the
wrong direction (anchoring raises precision) and became descriptive; A-P3
compared two campaigns and a practised rater against an unpractised one, so
it would confirm itself, and became a within-campaign SHOWN/HIDDEN split
timed per item; A-P2 read "more than 15 % or 3 or more of 20", which
disagree, and the audit became a fixed 20; B-P1's denominator now counts only
pooled blocks; the B re-check is mixed with unchanged rows so the rater
cannot tell the new version; the campaign is fixed. P3 still read 0 of 74.
The first wording is in the commit before this one.

### Amendment 2 -- after V25's P3, before any V26 sheet is mined

**Part B is STOPPED by its own registered rule.** Its target set -- V25 rows
with `arms_ok = no` and a block the sealed extraction marks MIXED -- holds
**1** sheet in the 50 checked (2 rows carry MIXED at all), against a minimum
of 5. Nothing in `extract.py` is written for it.

**Part C -- the agent counts subjects over the blocks it keeps.** V25's P3
found the subject count wrong on 17 of 50 sheets, 8 of them because a block
the agent had itself set aside (`NOT TUMOUR`, `NOT A READOUT`) was still in
the total. This change was conceived after reading V25's answers, so it is
measured on V26's fresh campaign only, never on V25's rows (rule 9).

The change, to the agent's procedure and to the summary format:
`runs/v26_extractions.csv` writes `subjects` PER BLOCK (`b1:8;b2:0;b3:8`),
marks a set-aside block in `arms` as `bN=DROP: <reason>`, and the desk prints
the total of the blocks NOT dropped, computed by code, not typed by the agent.

> **C-P1 -- THE SUBJECT COUNT IS RIGHT ON ≥ 75 % OF CONFIRMED SHEETS** in
> V26's extraction check (V25: 66 %, 52-78). *FALSIFIER: under 75 %.* The
> threshold sits below the 82 % that removing V25's 8 set-aside failures
> would give, because `extract`'s empty and mis-cut blocks (9 of V25's 17)
> are untouched by this change.
>
> **C-P2 -- DESCRIPTIVE:** all three columns right, beside V25's 62 %. No
> prediction: the empty-extraction failure, untouched here, is most of what
> remains.

### Amendment 3 -- before any V26 sheet is mined

**Part C also compares every count with the legend.** Rater A: "normally,
what the legends say is the ground truth". The agent runs `unpool extract
--legend`, which prints every `n = ...` in the sheet's own legend with its
sentence, and writes a `legend` column: `match`, `mismatch: <why>` or `none
stated`. A mismatch sends it back to the cut and the DROP blocks; a count
that still differs stays the sheet's count, with the reason. The desk shows
the column to the rater after a TRUE, beside the rest of the extraction.

> **C-P1 is unchanged** (subject count right on >= 75 %): the threshold was
> set before this amendment and is not raised to credit it.
>
> **C-P3 -- DESCRIPTIVE.** `subjects_ok` on the rows the agent marked
> `match` against the rows it marked `mismatch` or `none stated`: whether the
> legend check tells the agent when its own count is wrong.

### Amendment 4 -- before any V26 sheet is opened (the mine is running)

**Part A is withdrawn; V26 becomes legend-anchored triage.** After V25's
round 2 showed the person checking every row making more errors than the
agent, rater A moved the person to the rows the legend flags.
So the person no longer answers every agent-TRUE; the legend does the first
pass mechanically and the person reads only what it flags, plus an audit.
Part A's predictions (A-P1..A-P4) are NOT RUN. Part C stands.

**Procedure, fixed now.**
1. Mine as registered (running; `runs/v26_timeline.csv`).
2. Exclude known papers and freeze, as V25; commit before opening a sheet.
3. **Fresh subagents** (Claude Opus 5.5, none of which has seen V25 or any
   earlier verdict) screen and extract every accepted sheet, a batch of
   papers each, following `docs/V26_RUNBOOK.md` step 3 and amendments 2-3.
   For each TRUE the `legend` column states the expected count as
   `n=<k> x <arms> [+ n=<k> x <arms> ...] = <total>`, using only `n` values
   the legend prints, or `none stated`. Merged files committed = the seal.
4. **The comparison is code, not the agent** (`studies/v26_legend.py`). For
   every agent-TRUE sheet it re-runs `extract` (cache only), sums the blocks
   the agent did not mark DROP, and flags the row ANOMALOUS when any of:
   (a) that sum differs from the stated expected total; (b) an `n` the agent
   cites is not among the `n = ...` the legend prints (`paper.legend_n`);
   (c) the legend states no n, or the agent wrote `none stated`; (d) `extract`
   finds no block; (e) any block is marked MIXED. Otherwise CONCORDANT.
5. **Review:** every ANOMALOUS row plus a seeded draw of 10 CONCORDANT rows
   (`random.Random(20261005)`; all of them if fewer than 10), merged in seeded
   order, unlabelled, WITHOUT the `legend` column, into
   `runs/v26_review.csv`. Rater A checks each with `unpool desk check`
   (subjects, times, arms against sheet and legend) and, where something is
   wrong, says in the note whether the agent erred or the legend is the
   problem (no n, a wrong n, a panel it does not describe).

**The predictions.**

> **L-P1 -- THE CONCORDANT ROWS ARE RIGHT.** Of the audited CONCORDANT rows,
> rater A finds subjects, times and arms all right on at least 9 of 10.
> *FALSIFIER: 8 or fewer.* This is what lets a person skip them.
>
> **L-P2 -- DESCRIPTIVE.** The share of agent-TRUE sheets the legend clears
> as CONCORDANT, with its interval: how much reading the legend saves.
>
> **L-P3 -- DESCRIPTIVE.** Among ANOMALOUS rows, the split rater A reports:
> agent error, legend problem, both right (a false alarm).
>
> **C-P1 is re-read on the reviewed rows only** (ANOMALOUS + audit), which
> are not a random sample of the agent-TRUE: reported, not tested.

The agent's TRUE/FALSE screening is not re-measured here (V25 P1: 74/75).

### Amendment 5 -- after the mechanical triage ran, before rater A answers anything

The comparison (`studies/v26_legend.py`, on the sealed files)
flagged 98 of 110 agent-TRUE sheets ANOMALOUS. By first reason: (d) `extract`
finds no block 43; (e) a block MIXED 25; (c) the legend states no n 25 (47
sheets in all lack a reachable legend, nearly all supplementary figures whose
legend is in the SI PDF); (a) the count disagrees with the legend 5;
CONCORDANT 12. For c, d and e the question step 5 asks -- did the agent err
or is the legend the problem -- is already answered by the reason itself
(the extraction failed, or no legend is reachable). So rater A reviews only
the **5 comparable anomalies plus the 10-row audit** (unchanged draw), 15
rows, unlabelled, and **without the agent's `note`** as well as `legend`,
since notes state whether the count matched. Decided on the reason counts
alone: no row's content or correctness was looked at. L-P1 is unaffected;
L-P3 is reported mechanically for c/d/e and by rater A for a.

### The stop

Part A and part B are measured on different campaigns (A on V26's own fresh
campaign, B on V25's checked sheets), so neither result can be credited to
the other. (Amendment 2: B stopped; C is measured on V26's campaign together
with A -- A changes what the person sees before answering, C what the agent
writes after, and A-P2/A-P3 compare SHOWN with HIDDEN inside the campaign, so
C cannot move them.) Nothing in `scan.py` changes. `extract.py` does not change while
V25's P3 is open. Rater B is still absent: all of A rests on rater A, the
tool's author, as in V25.

### Result -- measured. L-P1 PASSED; part A NOT RUN; C-P1 reported, not tested

Campaign: 50 papers mined, 320 candidate sheets in 35 papers, 7 known papers
excluded, **267 sheets in 28 papers** screened by 6 fresh subagents
(Claude Opus 5.5; verdicts sealed before scoring): 110 TRUE, 157 FALSE, 0 UNRESOLVED.
Rater A answered the 15-row review pile (amendment 5) blind to which row was
which (`runs/v26_review.csv`).

> **L-P1 -- PASSED.** The 10 audited CONCORDANT rows: subjects, times and
> arms all right on **10 of 10** (threshold 9). Where the code finds the
> agent's kept blocks equal to the legend's arms x n, rater A found nothing
> wrong.
>
> **L-P2 -- DESCRIPTIVE.** The legend cleared **12 of 110** agent-TRUE sheets
> (11 %, 95 % 6-18). It is not a filter yet: `extract` found no block on 43
> (39 %) and pooled arms on 25 (23 %), and 47 sheets had no reachable legend
> (supplementary figures, legend in the SI PDF). V27 is the fix for the
> first two.
>
> **L-P3 -- the 5 comparable anomalies, by rater A:** agent or `extract`
> wrong, legend right: **2** (a count of 39 against the legend's and rater's
> 37; every block of a 27-animal panel set aside, 0 kept); extraction right,
> legend number differs: **2** (36 animals against a legend 35; 52 against a
> legend 65 -- rater A confirmed the sheet's count both times); false alarm,
> extraction right but the agent wrote no expected total: **1**. Reasons c,
> d, e (93 rows) are classified mechanically above.
>
> **C-P1 -- reported on the 15 reviewed rows, not tested** (not a random
> sample): subject count right on 13 of 15.

The legend is a strong check where it can be applied -- every row it
cleared was right -- and a weak reference on its own: in 2 of the 4 real
disagreements the sheet, not the legend, was right. A mismatch is a reason
to look, never a reason to overwrite the sheet's count.

**Time:** the logged desk-check session was left open overnight: not a person-minutes
figure. Agent wall-clock: mine 13 min; screening and extraction of 267
sheets by 6 parallel subagents, 13 min (longest batch).


## V27 — `extract` reads GraphPad-style sheets: orientation fallback and a split at merged group names. REGISTERED, BEFORE THE CHANGE IS WRITTEN

V26's triage (amendment 5) found `extract` failing on 68 of 110 agent-TRUE
sheets: 43 with no block, 25 with a block pooling arms. A mechanical
diagnosis of those 68 (they are the DEVELOPMENT SET; no other sheet is opened
while the change is written) found: 42 of the 43 empty ones yield blocks when
read in the orientation opposite to the scanner's (days in rows, animals in
columns, the GraphPad layout); 63 of the 68 carry a row of group names, each
over its own span of columns (merged cells), with no blank column between
groups -- rater A's observation; 5 carry no group label at all.

### The change, declared before it is written

1. **Orientation fallback.** When the scanner's orientation yields no block,
   `extract` tries the opposite one (`wide` <-> `wide-T`). A sheet that
   yields blocks today is read exactly as today.
2. **Split at group names.** Inside a block, a label column that is blank on
   some subject rows (a merged cell carried down) and takes a NEW non-empty
   value starts a new block. A label column with no blanks (`Mouse #1, #2`)
   never splits: it identifies animals, not groups.

Neither changes what the scanner accepts. `scan.py` does not change.

**Amendment 1, from the development set only, before the test
set is touched.** 3. **GraphPad statistics are not subjects.** A row whose
label is a significance marker (`ns`, `*`, `**`, ...) or a GraphPad test
header (`F (DFn, DFd)`, `P value`, `Two-stage ...`, `Adjusted P`, `Summary`)
is skipped, like the Mean / SEM / n rows already are. On PMC13415869 these
analysis tables were read as blocks of animals. The rule for change 2 was
also narrowed while developing: only a label column that named the block at
its first subject can split it (a banner merged across the table, as in the
worked example, lands mid-block in another column and split one mouse off).

### Test set, fixed now

V25's 50 checked rows (`runs/v25_extraction_check.csv`, P3 round 1, with the
round-2 recounts), never used to develop anything. Truth per row: round 2
where it exists, round 1 elsewhere.

> **V27-P1 -- EMPTY EXTRACTIONS RECOVER.** Of the 6 V25 rows where `extract`
> found no block, at least 4 yield a block. Mechanical. *FALSIFIER: 3 or
> fewer.*
>
> **V27-P2 -- WRONG ROWS GET FIXED.** For every V25 row whose per-block
> extraction changes, a fresh subagent that has not seen rater A's answers
> reassigns arms, DROP and the legend's expected count. Rater A re-checks
> the changed rows mixed with an equal-sized seeded draw of unchanged rows
> (`random.Random(20261006)`), unlabelled, without the agent's note. Of the
> changed rows that were wrong in subjects or arms, at least half become
> right in both. *FALSIFIER: fewer than half.* Underpowered below 8 rows.
>
> **V27-P3 -- NOTHING THAT WORKED BREAKS.** Of the changed rows that were
> right in all three columns, at most 1 is no longer. *FALSIFIER: 2 or
> more.*
>
> **V27-P4 -- THE RECORDS STILL REPRODUCE.** The worked example's 369 values
> and every hand-verified sheet's day grid come out unchanged;
> `tests/test_smoke.py` and `tests/test_recall.py` pass. *FALSIFIER: any
> difference.*
>
> **V27-P5 -- DESCRIPTIVE, DEVELOPMENT SET ONLY.** V26's triage re-run with
> the new `extract` (CONCORDANT count, reasons d and e). A training figure,
> never quoted as a measurement.

### The stop

No V25 sheet is opened, and no V25 row's answers read, while the change is
written. If V27-P4 fails, the change does not ship, whatever P1-P3 say.

### Result -- measured. P1, P2, P3 CONFIRMED; P4 FALSIFIED, so by the stop the change does not ship as written

Fresh subagents re-assigned the 39 changed rows (sealed before the
re-check); rater A re-checked all 50 rows blind to which had changed
(`runs/v27_review.csv`).

> **V27-P1 -- CONFIRMED.** The 6 V25 rows with no block: **6 of 6** now
> yield blocks (threshold 4).
>
> **V27-P2 -- CONFIRMED.** Of the 22 changed rows that were wrong in subjects
> or arms, **15** are now right in both (threshold 11). The 7 still wrong:
> GraphPad Mean/SD/SEM columns counted as animals (2), a panel's arms left
> out or stacked panels mis-cut (3), a block of a different readout kept (1),
> one animal lost (1, see P4).
>
> **V27-P3 -- CONFIRMED.** Of the 16 changed rows that were right in all
> three, **0** broke (threshold: at most 1).
>
> **V27-P4 -- FALSIFIED.** Over all 93 hand-verified sheets of
> `registry.csv` (old `extract` against new): 76 identical in subjects and
> day grids, **16 that read nothing before now read** (a difference, a gain),
> and **1 that loses an animal**: PMC13578219 Fig.10, 62 -> 61. The lost row
> is a real mouse whose row carries a GraphPad `P value` cell beside its
> label, so change 3 (amendment 1) skipped it. Under any reading of P4 that
> is a record that no longer reproduces.

**Descriptive, test set.** With the new `extract` wherever it changed the
row, all three columns right on **41 of 50** (82 %, Wilson 95 % 69-90);
subjects 41/50, times 48/50, arms 48/50 -- against 23/50 (46 %) for the
same sheets as delivered in V25 (round 2). Rater A had seen these sheets
before (P3); on the 11 unchanged rows the re-check repeated the earlier
all-three verdict on 9 (test-retest 82 %).

**The stop applies: the change does not ship as written.** The fix is
narrow (skip a row as statistics only when the statistics marker is its
ONLY label) and is a new change: it needs its own registration and a test
set nobody has used -- V25's rows are spent.

**Time:** rater sessions logged 14 min (12 rows), 22 min (15 rows) and one
left open across a working day (23 rows): about 70 s a row where usable.


## V28 — legends of supplementary figures, read from the SI PDF. REGISTERED, BEFORE THE CHANGE IS WRITTEN

V26 found no reachable legend for 47 of 110 agent-TRUE sheets, nearly all
supplementary figures: Nature-family articles carry those legends only in
the Supplementary Information PDF, which is inside the supplementary bundle
`unpool` already caches. A feasibility probe on 3 V26 sheets (development
set) found the caption ("Supplementary Fig. 32. ...", "Supplementary Figure
7. ... (n=6)") in the PDF's text each time, under a second per PDF.

### The change, declared before it is written

When a sheet names a supplementary figure and the article's XML holds no
legend for it, `paper` reads the PDFs in the cached bundle (optional
dependency `pypdf`, `pip install -e .[pdf]`; without it, a wall that says
so), finds the caption that starts a line with `Supplementary Fig[ure|.] N`
for the sheet's figure number, and returns its text up to the next such
caption. The extracted PDF text is cached beside the bundle. `extract
--legend`, `unpool paper` and the desk use it, labelled as coming from the SI
PDF. Nothing the scanner accepts changes.

Development set: V26's sheets only. Test set, fixed now: the V25 desk's
supplementary-figure sheets for which no legend was located
(`runs/v25_desk.json`, bundle legend empty, sheet name of kind S).

> **V28-P1 -- THE CAPTION IS FOUND.** On the test set, a caption is returned
> for at least 70 % of the sheets. Mechanical. *FALSIFIER: under 70 %.*
>
> **V28-P2 -- IT IS THE RIGHT CAPTION.** On a seeded sample of 10 test-set
> sheets where one was returned (`random.Random(20261007)`), rater A,
> reading the sheet and the returned text, says it is the legend of that
> sheet's figure on at least 9. *FALSIFIER: 8 or fewer.*
>
> **V28-P3 -- DESCRIPTIVE, DEVELOPMENT SET.** Of V26's 47 sheets without a
> reachable legend, how many gain one, and how many of those state an n.

### Result -- P1 and P3 measured; P2 pending rater A

The code (+ an atomic, surrogate-safe cache write found while
measuring), written on V26 sheets only.

> **V28-P1 -- FALSIFIED.** On the test set (57 supplementary-figure sheets
> of the V25 desk with no legend located, 18 papers) a caption is returned
> for **26 of 57, 46 %** (Wilson 95 % 33-58), against 70 %.
>
> **V28-P2 -- FALSIFIED.** Rater A: the returned caption is the
> legend of the sheet's figure on **7 of 10** (threshold 9). All three
> misses are one article (PMC13562681): the caption came from its **Peer
> Review File**, which quotes "Supplementary Figure 3" in referee comments.
> Read after scoring: that bundle's SI PDF writes `Supplementary figure 1.`
> in lower case, which the registered caption pattern did not accept, so the
> only match left was in the review file.
>
> **V28-P3 -- DESCRIPTIVE, DEVELOPMENT SET.** Of V26's 48 agent-TRUE sheets
> with no XML legend, 38 gain one from the SI PDF (79 %, 66-88), 36 of
> them stating an n. The gap between 79 % and 46 % is what a development
> figure is worth.

**Why the 31 test misses, read after scoring and not used to change the
code:** 11 PDFs caption their figures `Figure S12` / `Fig. S3` without the
word "Supplementary", which the registered pattern requires; in 9 the
caption is there but the PDF's text layer does not start it on a line of
its own; in 11 the figure number does not occur in any PDF of the bundle
(the legend is elsewhere, or the sheet's number is not the figure's).
A pattern widened for the first two would be fitted to this test set: it
needs its own registration and a fresh one (rule 9).

**Fix after P2, post hoc and labelled so** (the author's choice:
checked on data already used, not a fresh test). The caption pattern no
longer depends on case (`Supplementary figure 1.`), and a PDF whose first
page is a Peer Review File, reviewers' comments or a Reporting Summary is not
read. On the P2 sample the three misses now take their caption from the SI
PDF and the other seven start with the same caption as before; on the test
set the caption is found for **43 of 57 (75 %, 95 % 63-85) -- post hoc,
on the sheets whose misses suggested the fix**. Rater A then re-read the three
corrected captions and confirmed all three: on the P2 sample,
**10 of 10 after the fix, post hoc**. The registered figures stay P1 26/57
and P2 7/10.

What ships: the SI-PDF legend as an optional extra, quoted at the test
figure, 46 %: where it answers, the legend is the PDF's own; where it does
not, the wall is unchanged.


## V29 — V27 with the two faults its measurement exposed fixed. WRITTEN AND MEASURED ON DATA ALREADY USED, BY THE AUTHOR'S DECISION

**Not a pre-registered test, and labelled so.** V27-P4 failed: one
hand-verified sheet lost a mouse. Rater A decided to fix it and measure the
fix against the records already validated rather than on a fresh campaign,
trading independence for rater time. So this entry was written after the
change, and every figure below is a CONSISTENCY CHECK against existing human
answers on sheets that suggested the fix -- not an estimate of performance on
unseen sheets. That estimate is V27's 41/50 on a held-out set; V29 can only
be shown not to have broken anything and to have fixed what it set out to.

### The change

1. A row is skipped as GraphPad statistics only when statistics markers are
   ALL its labels say (PMC13578219 Fig.10: a mouse whose row also carries a
   `P value` cell from a neighbouring table was dropped by V27).
2. `Avrg`, `Average` and `Mean` as a whole label are summary rows, like
   `Ave` / `SD` / `SEM` already were (PMC13530216 Fig 7a/7e: each arm's
   average column was counted as an animal, V27-P2's two GraphPad failures).

### Results

> **Records (V27-P4 re-run).** All 93 hand-verified sheets of `registry.csv`
> plus the worked example, against `extract` before V27: **78 identical** in
> animals and day grids, **16 that read nothing before now read**, **0 lose
> or change an animal**. The worked example's 369 values are unchanged.
>
> **The faults it targets** (rater A's V27 answers and notes): Fig.10 kept
> total 39 -> **40** (rater: 40; legend 40); Fig 7a 26 -> **23** (rater:
> 23; legend 23); Fig 7e 20 -> **18** (rater: the Vehicle average was counted).
> No other V25 row's extraction changes between V27 and V29.
>
> **V26's reviewed rows:** the same animals and values on **15 of 15**
> (12 are cut into different blocks than when V26 sealed them -- per arm
> instead of per panel -- with nothing lost or added).

On the 50 V25 rows, with V27's answers where nothing changed and these three
now matching the rater's own counts, all three columns would be right on
**44 of 50 (88 %, 95 % 76-94) -- post hoc, on the rows that inspired the fix;
never quoted as a measurement.** The measured figure for the new `extract`
stays V27's 41/50 (82 %, 69-90) on a held-out set.

**Ships:** V27 + V29 is the `extract` of v0.1.0. `tests/test_smoke.py` passes;
`scan.py` is unchanged, so the recall gate is unaffected.


## V30 — the same work with Sonnet 5.5 and Haiku 4.5. REGISTERED, BEFORE EITHER MODEL SEES A SHEET

Every agent figure so far is Claude Opus 5.5. Rater A asked whether the
smaller models are reliable on the same data. (This registration first said
"Haiku 4.5"; every Haiku subagent reported itself as Haiku 5.5,
`claude-haiku-5-5`, which is what was measured.)

### Tasks and truth, fixed now

1. **Screening** (TRUE / FALSE / UNRESOLVED, V23's question verbatim, the
   evidence of `unpool sheet` + `unpool paper`) on **115 sheets with a human
   final verdict**: V18's 20 (a seeded random draw of scanner accepts) and
   V25's 95 desk sheets (every Opus-TRUE plus a 20 % audit of Opus-FALSE --
   so this set was drawn through Opus's verdicts, which favours Opus; the
   V18 twenty are the unbiased part, and are reported apart).
2. **Extraction** (per-block subjects, DROP, arms, the legend's expected
   count; `docs/V26_RUNBOOK.md`) on V25's 50 checked rows. Truth: the **44
   rows whose subject count rater A confirmed** (V27 + V29), the confirmed
   total being the kept total of the current `extract` under the confirmed
   DROP marks. A model is right on a row when its kept total equals it.

Both models get Opus's evidence and nothing more: `UNPOOL_NO_SI=1` switches
off the SI-PDF legends Opus did not have. Each runs as fresh subagents in
batches, never shown any verdict.

> **B-P1 -- DESCRIPTIVE, the numbers this exists for.** Per model: screening
> precision, recall and accuracy against the human verdicts (V18 and V25
> apart), and extraction kept-total accuracy on the 44 rows; Opus beside
> them from its sealed V23/V25 verdicts (on the extraction, Opus matches by
> construction and is not scored).
>
> **B-P2 -- THE DECISION RULE, fixed now.** `skills/unpool/SKILL.md` names a
> smaller model as usable for screening only if, on the 115, its precision
> is at least 95 % AND its recall at least 90 %; for extraction, only if its
> kept total is right on at least 40 of 44. Otherwise the skill says Opus.

### Result -- measured. Both models pass for screening; Sonnet 5.5 passes for extraction, Haiku 5.5 does not

Every subagent reported its model: Sonnet 5.5 (`claude-sonnet-5-5`), Haiku
5.5 (`claude-haiku-5-5`). Outputs `runs/v30_parts/`.

**Screening, 115 sheets (83 TRUE by the human verdict).**

| | precision | recall | accuracy | V18 (unbiased 20) |
|---|---|---|---|---|
| Opus 5.5 | 83/83 | 83/83 | 115/115 | 20/20 |
| Sonnet 5.5 | **80/80 (100 %, 95-100)** | **80/83 (96 %, 90-99)** | 112/115 | 20/20 |
| Haiku 5.5 | **82/82 (100 %, 96-100)** | **82/83 (99 %, 93-100)** | 114/115 (1 UNRESOLVED) | 19/20 |

Opus's perfect row is inflated twice over: the V25 set was drawn through its
verdicts, and the human verdict used as truth is the one reached after
re-reading the disagreements with Opus's reasoning (V23 and V25 round 2).
Against that truth no model can beat Opus, so the smaller models' figures are
the cleaner ones. None of the three ever called a non-series TRUE.

**Extraction, 44 rows with a confirmed subject count.**

| | kept total right | rows marked MIXED |
|---|---|---|
| Sonnet 5.5 | **43/44 (98 %, 88-100)** | 7 |
| Haiku 5.5 | **39/44 (89 %, 76-95)** | 14 |

Every row's per-block counts were copied from `extract` correctly by both;
the misses are DROP and arm decisions. Sonnet's one miss is PMC13578219
Fig.10 (kept 60 against 40). Haiku's five are DROP choices on multi-panel
sheets.

> **B-P2 applied.** Screening: Sonnet 5.5 (100 / 96) and Haiku 5.5 (100 / 99)
> both clear 95 / 90. Extraction: Sonnet 5.5 clears 40 of 44 with 43; Haiku
> 5.5 misses it with 39. `skills/unpool/SKILL.md` now says so.

**How they worked, not only what they got.** One Sonnet extraction batch ran
all 25 sheets through a script and assigned some arms without reading the
paper (its notes say which); it still matched 24 of its rows. Two Haiku
extraction batches wrote into the same file and one rewrote it, losing a row
of the other's, which that batch then restored; two Sonnet batches collided on
a helper script name. Nothing lost reached the scored files (every work list
is complete, once), but parallel agents need separate scratch space.


## V31 — `unpool export`: the campaign as one per-animal CSV. REGISTERED, BEFORE THE COMMAND IS WRITTEN AND BEFORE `extract` IS RUN ON ANY BUILDER'S FILE

Rater A asked for the last step without code: from a campaign's agent
extractions to one CSV with every animal, its study (DOI), arm and values.
`export` adds no reading of its own: it re-runs `extract` on each sheet,
names each block from the agent's `arms` column (`bN=name`), leaves out
`DROP` and `MIXED` blocks, and attaches the paper's DOI, journal and licence.
So what it can get wrong is (a) `extract`'s cut against a careful human
reading and (b) the bookkeeping. The agent's arm NAMES are not new here:
they are measured by V25 P3 / V27 (`arms_ok`).

### Design fixed now

- One row per (animal, day, value): `doi, pmcid, journal, year, licence,
  file, sheet, sha256, block, arm, animal, subject_label, time, value,
  state`. `animal` is `<PMCID>:<sheet>:b<k>:s<i>`, unique in the campaign.
- `state` is `verified` only when the sheet is in `registry.csv` AND the row
  carries `subjects_ok`, `times_ok`, `arms_ok` all `yes` (a person checked
  this extraction, not only the sheet); otherwise `screened`.
- **Stale guard.** The agent's arms refer to block numbers. If `extract`
  now cuts the sheet differently from the per-block counts the agent wrote
  (`b1:8;b2:5`), the sheet is refused with that reason, never relabelled by
  position.
- `MIXED` blocks and refused sheets are listed on screen, with the reason.

### Population

**Builders.** The hand-written builders of the earlier project whose source
is a Europe PMC paper with its supplement cached: 10 papers, 1,247 animals
(pdxnet5lab, nr2f1melanoma, tazteadA375, rmspi3k, blu222, krastopo2, atrcu,
aldh1a1, thsd7b, elmo2), plus the worked example (41) reported apart, since
`extract` was built on it. The builders were never used as a test of
`extract`; some of their layouts (arm named once over its columns) were
known when V27 was designed. Their CSVs and the publisher files stay out of
the repository; the per-animal result of the comparison is committed.

**Bookkeeping.** The 50 V25 rows as rater A last checked them
(`runs/v27_review.csv`).

### Procedure, fixed now

For each builder paper, `extract` runs (fallback on, no `--layout`) on every
sheet of the builder's file. A builder animal's curve is its non-zero values
in day order, rounded to 6 significant digits; it is **found** if some
extracted subject has exactly that sequence of non-zero values, or holds it
as a contiguous run (the builder truncated days; counted and reported).
Matching is one-to-one, greedy in file order.

A builder animal is **derived**, and out of every denominator, if fewer than
half of its values occur anywhere in the file as a cell value (rounded the
same way): the builder computed them (from length x width, as % of baseline),
and no reading of the sheet can return them. The count is reported.

### Predictions

- **X-P1 (animals).** Of the non-derived builder animals, `extract` finds
  >= 90 %. Falsifier: < 90 %.
- **X-P2 (arms not pooled).** Of the extracted blocks holding >= 1 found
  animal, >= 90 % hold animals of ONE builder arm (`panel` + `arm_label`). An
  arm split over two blocks is not a failure (the agent names both); two arms
  in one block is. Falsifier: < 90 %.
- **X-P3 (days).** For the found animals, the extracted days of the matched
  values equal the builder's days on >= 90 %. Falsifier: < 90 %.
- **X-P4 (bookkeeping).** On the 50 rows: every sheet `extract` still cuts as
  the agent recorded is exported, each kept arm with exactly its recorded
  block counts, no `DROP` or `MIXED` animal in the CSV, and every changed
  sheet refused, not relabelled. Falsifier: any exception -- a bug, fixed
  before release.

X-P1 to X-P3 are reported per paper as well as pooled: one large paper must
not hide a failing one.

### Result -- measured. The CSV is right where `extract` reads; `extract` reads half of the builders' animals. X-P1 fails

`python studies/v31_export.py --builders <builders folder>`; per animal in
`runs/v31_builders.csv` (identifiers, no values).

| builder | derived (out) | found (X-P1) | blocks one arm (X-P2) | days right (X-P3) |
|---|---|---|---|---|
| aldh1a1 | 0 | 188/188 | 29/29 | 188/188 |
| atrcu | 0 | 60/208 | 5/5 | 60/60 |
| blu222 | 1 | 31/287 | 0/1 | 31/31 |
| elmo2 | 0 | 72/73 | 6/11 | 72/72 |
| krastopo2 | 0 | 40/112 | 4/4 | 40/40 |
| nr2f1melanoma | 0 | 81/123 | 50/50 | 81/81 |
| pdxnet5lab | 174 | -- | -- | -- |
| rmspi3k | 48 | -- | -- | -- |
| tazteadA375 | 0 | 0/13 | -- | -- |
| thsd7b | 0 | 0/20 | -- | -- |
| *worked example* | 0 | *41/41* | *5/5* | *41/41* |

> **X-P1 FAILS: 472 of 1,024 non-derived animals found (46 %, 95 % 43-49),
> against >= 90 %.** **X-P2 passes: 94 of 100 blocks (94 %, 88-97)** hold one
> builder arm (elmo2's 2x2 sheet pools arms in 5 blocks; blu222 1). **X-P3
> passes: 472/472 (100 %)** of found animals carry the builder's days.
> **X-P4 passes:** 47 of 50 sheets exported, every kept block with exactly its
> recorded count and no DROP or MIXED animal; the 3 refused are exactly the
> sheets V29 re-cut (Fig 7a, Fig 7e, Fig.10), not relabelled.
> 223 animals are derived (pdxnet5lab as % of baseline, rmspi3k from
> length x width): no reading of the sheet returns them.

**Why, post hoc (not part of the test).** Of the 552 missed, 517 are never
read and 35 are read with other days (tazteadA375's 13: the pre-treatment days
-9 to -3 are not in the block; blu222 22). The unread fall in three groups:
stacked multi-panel sheets read only in part (blu222 Fig. 5-6, atrcu Fig. 1,
krastopo2 Fig. 9, nr2f1 Fig. 3C); sheets the scanner does not accept, so no
layout exists (blu222 Fig. 7, nr2f1 Fig. 5D, atrcu Fig. 5); and the wrong
orientation (thsd7b, krastopo2 Fig. 4).

**What it means.** The population is the sheets someone once wrote a builder
for *because* they were hard, so 46 % is a floor on hard sheets, not the rate on
a campaign (V27: 41 of 50 V25 sheets right). The failure mode matters more
than the rate: `extract` does not pool or garble animals it reads (X-P2, X-P3
with values matched exactly); it leaves animals out. `export` therefore ships
with the rule that the kept count is compared with the legend's arms x n
(V26: a match was right 10 of 10), and a sheet that falls short is a sheet to
read, not a complete one. Stacked panels and scanner-rejected sheets are the
next `extract` study; these builders are now its development set and can no
longer test it.

**Amendment, written after the result: the figure on a normal campaign.**
Rater A asked for the CSV's figure where users will meet it. X-P4 shows
`export` adds no error of its own, so the CSV is right exactly where the
extraction is. On the 47 V25 sheets it exports, the shipped `extract` cuts
every sheet as the V27 `extract` did (V29: no other row changes), and rater
A's V27 answers on them were given blind, on sheets V27 was not built on.
So, descriptive and not registered: **the CSV is fully right -- subjects,
days and arms -- on 41 of 47 exported sheets (87 %, 95 % 75-94), and
1,363 of its 1,518 animals (90 %) sit on those sheets.** (By animal, no
interval: animals on one sheet are not independent.) The 6 sheets that are
not right carry 155 animals; all 6 fail on subjects, which is what the
legend check is for.

**`readout`, added with this amendment, not measured.** The extraction CSV
takes a `readout` column -- what was measured, one value for the sheet
(`volume (mm3)`) or per block (`b1-b4=volume;b5=bli`) -- and `export` carries
it into every row; `desk check` shows it beside the arms. A sheet of
bioluminescence confirmed in V25 made the need plain: a value of 49,100,000
is a fine photon flux and an alarming tumour. The agent writes it; no study
has checked it yet.
