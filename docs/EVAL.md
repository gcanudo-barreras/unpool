# Opus 5 vs Sonnet 5 on the verification step

**Registered, before the run.** Predictions, decision rule and the
power limitation are all written here first, because a threshold chosen after
seeing the result is not a threshold.

## The question, narrowed

Not "which model is better". The pipeline's expensive judgement is one step:
**step 4, verify at the leaf.** The scanner is deterministic regexes and costs
no tokens; the guards are deterministic. The model is asked to do exactly one
thing that matters — look at a supplementary file the scanner accepted and say
whether it really holds per-subject longitudinal measurements, of how many
subjects, at which time points.

If Sonnet does that as well as Opus, use Sonnet.

**And the saving is smaller than it looks.** The scanner already reduces ~300
papers to ~6, so the model never sees the volume. The real token cost is
writing the builder docstring, not triage. This eval measures the judgement,
not the saving.

## The item set

21 files, each one with a known answer:

| | n | |
|---|---|---|
| **POS** | 15 | verified at the sheet by a builder that emitted real data |
| **NEG** | 6 | and five of these are the valuable ones |

The negatives are not synthetic. **Five are files the scanner accepts today and
is wrong about**, verified by hand:

- two are the **wrong model** — the paper mentions 4T1, every counted sheet is
  B16F10
- one is **arm-level** `Average / SEM / Number of mice`, statistic columns
  counted as animals
- one is a **differential gene-expression table read transposed**, gene symbols
  taken for animal IDs
- one is an **in-vitro IC50 dose-response plate**, the dose column read as a
  time axis

The sixth is a tiled side-by-side layout the parser cannot read correctly.

That is the population that matters: if a model only agrees with the scanner it
adds nothing, because the scanner is free.

## Blinding

The files are copied to a directory containing **nothing else** — no ground
truth, no builders, no protocol, no repository, no git history. Filenames are
kept because a real user has them.

This matters more than it sounds. Both models can read; if the builders are
reachable the eval measures search, not judgement.

## What each model is asked, per file

> Does any sheet in this file contain per-subject longitudinal measurements —
> one row or column per individual subject, repeated across time? If yes: which
> sheet, how many subjects in the largest single arm, and what are the time
> points. If no, answer NO and say what the file actually contains.

## Metrics, in priority order

1. **False-accept rate** on the 6 negatives. A false accept wastes the
   verification step the pipeline exists to protect and, uncaught, poisons a
   dataset. This is the metric.
2. **False-reject rate** on the 15 positives. Costs a paper.
3. **Exact subject count** where the truth is known (11 of 15 positives).

## Predictions

> **P1** — Both models reject at least 4 of the 6 negatives. The failures are
> legible in the file itself (a `Mean/SEM/N` header, gene symbols, a `Dose, uM`
> column), so this is a reading task, not a knowledge task.
>
> **P2** — The gap between the two false-accept rates is **smaller than 2 of 6
> items**, i.e. not resolvable by this eval.
>
> **FALSIFIER of P1**: either model accepts 3 or more negatives. That model
> cannot be used for step 4 unsupervised, whatever it costs.
>
> **FALSIFIER of P2**: a gap of 2 or more items appears. Then the eval has found
> something and a larger item set is worth building.

## The power limitation, stated before the result

**6 negatives cannot resolve a small difference.** One item is 17 percentage
points. This eval can detect a catastrophic gap and nothing finer. It is a
smoke test and it will be reported as one.

A real measurement needs 30+ verified negatives, which is acquisition work: run
`mine.py` on a query, take the scanner's accepts, verify each by hand. That is
the same loop the pipeline already runs, so the item set grows as the tool is
used.

Both models see all 21 items in one pass rather than one call each. Cheaper, and
it risks cross-item contamination — a model that spots the pattern may calibrate
across the set. Named, accepted, and it applies equally to both.

## Decision rule, fixed now

**Use Sonnet for step 4 unless its false-accept rate exceeds Opus's by 2 or more
of the 6 negatives.** If both fail P1, neither is used unsupervised and the
protocol's existing requirement — a human reads the sheet — stands unchanged.

## Result

### First, the key was wrong, and the eval caught it

**Four of the six "negatives" were mislabelled, and both models were right about
all four.** The label conflated three different things under one word:

| file | what the scanner got wrong | correct answer to the question ASKED |
|---|---|---|
| `PMC13385831`, `PMC13408911` | **model identity** — paper says 4T1, sheets are B16F10 | **YES**, they do hold per-mouse series |
| `pone0288380` | **the parser** cannot read a tiled layout | **YES**, the data is genuinely per-animal |
| `PMC8967035` | accepted the IC50 sheet `Figure 1A` | **YES** — sheet `Figure 1D` holds a real 8-mouse series |

The prompt asked "does any sheet contain per-subject longitudinal
measurements". It did not ask "was the scanner right". Only two of the six
negatives were negative for the question posed.

That last row also **retracted a finding**: the run behind it had concluded no
tabular supplement of `PMC8967035` carried the per-animal MCF7 data. It does —
two sheets past the one the grading script stopped at.

### Scores, on the corrected key (19 POS, 2 NEG)

| | Opus 5 | Sonnet 5 |
|---|---|---|
| false accepts, of 2 | **0** | **0** |
| false rejects, of 19 | **0** | **1** |
| total errors of 21 | **0** | **1** |

Sonnet's one error: `jci197192_krastopo2_sourcedata.xlsx`, answered NO with
*"no day/mouse/tumor-volume field anywhere in the file"*, on a 21-sheet workbook
whose `Fig S7` has columns literally headed `Vehicle-1` … `Vehicle-6`, with
`Fig 9`, `Fig S6` and `Fig S11` carrying Vehicle/AMG510 per-mouse blocks too.
It reported checking 19 sheets of 21. Verified by hand before scoring.

### Predictions, graded

**P1 — ungradable as written.** It asked whether both models reject 4 of 6
negatives; there were never 6. On its intent — neither model false-accepts —
both pass, 2 of 2.

**P2 — confirmed, and worthless.** The false-accept gap is 0. With two
negatives it could not have been anything else. Registering the power limit in
advance is the only reason this does not read as a result.

### The decision rule says Sonnet. Do not act on that yet.

Applied literally: Sonnet's false-accept rate does not exceed Opus's, so the
rule selects Sonnet. **But the rule was written against a metric this eval could
not measure**, and the difference that did appear is somewhere else.

### The finding that matters, which nobody registered

The two models agree on the **binary verdict** for 20 of 21 files. They agree on
**the subject count** for 12 of the 18 positives both accepted — about
two thirds. They name a **different sheet** on 8 of 19.

| file | Opus | Sonnet | truth |
|---|---|---|---|
| `ncomms67865_blu222` | 10 | 8 | **8** |
| `41467_2026_70001` | 12 | 8 | ~10/arm (208 across 20) |
| `jci178446_nr2f1` | 10 | 5 | 13–16/arm |
| `PMC8967035` | `Figure 1D`, 8 | `Figure 1B`, 8 | 8 |

**The binary question is easy and the count is not.** Step 4 of the protocol
needs the count and the day grid, not the verdict — the scanner already gives
the verdict for free. Neither model is reliable at the number on a multi-sheet
workbook, because "the largest single arm" is ambiguous across sheets holding
several experiments, and both answer confidently anyway.

So the protocol's standing requirement is unchanged and now has evidence behind
it: **a person reads the sheet.** A model is useful for narrowing which sheet to
read and worthless as the last word on how many subjects are in it.

### What to do instead

Use either model for the narrowing pass; they are equivalent there and Sonnet is
cheaper. Do not let either fill in `_VERIFIED_N`.

The next eval is not a bigger version of this one. It should score **the count
and the grid against builder-verified truth**, per sheet rather than per file,
which is the question that discriminates. This one scored the question that
does not.
