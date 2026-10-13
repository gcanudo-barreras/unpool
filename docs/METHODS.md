# Methods and Supporting Information

How each figure in the README was measured. Each section gives the question,
the population, the procedure, the result and what limits it, and points to
the study that holds the full record in `docs/VALIDATION.md`, where every
study is written down before it is run. `docs/FIGURES.md` lists every number
beside its configuration.

**Common to all.** Studies are pre-registered: the predictions and the test
for failure are committed before any data is looked at, and the agent's
verdicts are sealed by a commit before a person sees an item. The human rater
throughout is one person, the tool's author ("rater A"). Intervals are Wilson
95 %. "Post hoc" marks any figure measured on the sheets that suggested the
change being measured; such a figure is always quoted beside an independent
one.

---

## S1. The pipeline

1. **Mine.** `unpool mine` queries Europe PMC, downloads each paper's
   supplementary bundle and keeps the sheets whose *structure* looks like
   per-subject series: a subject axis, a time axis, values that grow (the
   scanner decides on structure, never on wording).
2. **Screen.** An agent reads every accepted sheet with its figure legend and
   methods (`unpool sheet`, `unpool paper`) and answers one fixed question:
   does the sheet hold, for at least one arm, one value per animal at four or
   more time points of an in-vivo tumour-growth readout?
3. **Extract.** `unpool extract` cuts the sheet into blocks of subjects; the
   agent assigns each block an arm from the legend, sets aside (`DROP`) blocks
   that are not the readout, and compares the kept count with the group sizes
   the legend states (`--legend`).
4. **Verify.** A person checks the result in the desk (`unpool desk`), blind
   to the agent's verdict until they have answered. Only then is a sheet
   `verified`, and only then does it enter `registry.csv`.
5. **Export.** `unpool export` writes the campaign as one per-animal CSV
   from the extractions, with each animal's state (S8).

## S2. Scanner (step 1) -- V10, V17, V18, V24

The first pass is deliberately broad. **Precision 8 of 20 (40 %, 22-61)** on a
seeded random draw of accepted sheets from papers nothing was tuned on (V18);
by paper, 9 of 20 (V24). **Recall 15/15** on the cached publisher fixtures --
a tuning-set figure, not a score: the scanner was re-tuned on those files.
Most false accepts are large numeric matrices from other disciplines that
happen to carry a monotonic axis. Precision and recall are quoted together or
not at all.

## S3. Finding the right sheet (step 2) -- V23, V25

**Question.** Of the sheets the agent keeps, how many hold real per-animal
series? **Population.** A fresh campaign (`"patient-derived xenograft"`,
*Nature Communications*, 50 papers): 173 accepted sheets in 26 papers, none
seen before. **Procedure.** Claude Opus 5.5 screened all 173; rater A answered
every agent-TRUE plus a seeded 20 % audit of agent-FALSE, blind. **Result.**
**74 of 75 agent-TRUE confirmed (98.7 %, 92.8-99.8)**; audit 19 of 20. On
re-reading the two disagreements with the agent's reasoning, both went the
agent's way (75/75, 20/20). **Limits.** One rater, who wrote the tool; the
second rater planned for this study was not run.

## S4. Extracting the data (step 3) -- V25 P3, V27, V29

**Question.** On a confirmed sheet, are the subject count, the day grid and
each block's arm all right? **Population.** 50 of V25's confirmed sheets.

| `extract` | all three right | how measured |
|---|---|---|
| original | 31/50 (62 %, 48-74); 23/50 after a recount found the rater double-counting mice repeated in body-weight blocks | V25 P3, blind |
| GraphPad-aware (V27) | **41/50 (82 %, 69-90)** | V27: developed on 68 *other* sheets, tested here; changed rows re-assigned by fresh agents and re-checked blind, mixed with unchanged ones |
| shipped (V27 + V29) | **44/50 (88 %, 76-94)**, post hoc | V29 fixed the two faults V27's test exposed |

What changed: GraphPad exports put days down the rows and animals across the
columns, with each arm's name written once above its columns (a merged cell)
and no blank column between arms. The original `extract` read 39 % of such
sheets as empty and pooled arms on 23 %. It now tries the other orientation
when the first yields nothing, starts a block where a merged group name
changes, and does not count statistics or `Avrg` columns as animals -- a
statistics row is not a mouse, however hard it tries to look like one.

**Records.** On all 93 hand-verified sheets in `registry.csv` and the worked
example, the shipped `extract` loses no animal: 78 come out identical, 16 that
read nothing before now read. V27 alone failed this check (one mouse whose row
carried a `P value` cell); V29 is that fix.

## S5. Using the legend -- V26, V28

**Legend as a check (V26).** A fresh campaign (`"MC38" OR "CT26"`, *Nature
Communications*, 267 sheets in 28 papers) was screened and extracted by six
independent Opus 5.5 agents; code then compared each kept count with the
legend's arms x n. Where they matched, rater A found **10 of 10** sampled rows
right: a match can be trusted. Where they did not, the legend was wrong about
as often as the extraction (2 and 2 of 4) -- a mismatch means *look*, not
*overwrite*. Only 12 of 110 sheets could be cleared this way then, mostly
because of the extraction faults S4 fixed and missing legends (below).

**Supplementary legends (V28).** Supplementary-figure legends live in the SI
PDF, not in the article text. `unpool` now reads the PDFs in the cached bundle
(optional `pip install -e .[pdf]`). On 57 test sheets: found for 26 (46 %) as
registered; after a fix for lower-case captions and for the referees' report
being read as SI, **43 of 57 (75 %, 63-85)**, post hoc. Right legend: 7 of 10
as registered, **10 of 10** after the fix (the three misses were one article
whose Peer Review File quotes its figures).

## S6. Which model -- V30

The figures above are Claude Opus 5.5. V30 repeated the screening (115 sheets
with a human verdict, 83 of them real series) and the extraction (44 rows with
a confirmed subject count) with Sonnet 5.5 and Haiku 5.5, each given exactly
the evidence Opus had, as fresh agents that saw no verdict.

| | screening precision | screening recall | extraction kept total |
|---|---|---|---|
| Sonnet 5.5 | 80/80 (100 %) | 80/83 (96 %) | 43/44 (98 %) |
| Haiku 5.5 | 82/82 (100 %) | 82/83 (99 %) | 39/44 (89 %) |

Opus scores 100 % on screening, but that is inflated: the reference verdicts
were reconciled with its reasoning, and part of the set was drawn through its
own verdicts. By the rule registered beforehand (precision >= 95 %, recall >=
90 %; extraction >= 40 of 44), Sonnet 5.5 can do the whole agentic phase and
Haiku 5.5 the screening. None of the three ever kept a sheet that was not a
series. The smaller models also showed some character: one Sonnet batch
scripted its way through and guessed a few arms (still 24 of 25 right), and
two Haiku batches managed to write into each other's file.

## S7. Where the data is -- journal yield

On 100 papers per journal that mention tumour volume and carry a supplement,
the share with a sheet the scanner accepts, re-measured at the shipped
settings on a new sample frozen before fetching (V19): *Communications
Biology* 78 %, *Nature Communications* 72 %, *Nature Cancer* 51 %, *Nature
Medicine* 10 % (211 of 400 pooled). The first sweep, at an older floor and
across 27 journals (`studies/journal_yield.py`), is a lower bound and agrees
in order: *Nature* 62 %, and an earlier 50-paper sample of the general
literature 0 %. These are scanner acceptances -- candidates -- not verified
data (S2). What predicts them is not prestige but whether the journal
requires a Source Data file per figure. 693 tables from 206 PDF and Word supplements held no per-subject
series, which is why data is only read from spreadsheets.

## S8. The per-animal CSV -- V31

**Question.** `unpool export` re-reads each sheet with `extract`, names each
block from the agent's arms and attaches the paper's DOI and licence. Is the
result what a careful person builds by hand? **Population.** The ten builder
scripts the author had written by hand, one per paper, whose source is a Europe
PMC paper (1,247 animals; 223 out as derived -- % of baseline, length x
width), plus the 50 V25 rows for the bookkeeping. **Procedure.** Each builder
animal is looked for among every curve `extract` reads in the paper's
supplement, by its exact sequence of values. **Result.** Where `extract` reads
an animal, it is right: **472 of 472** with the builder's days, **94 of 100**
blocks hold a single arm, and the bookkeeping is exact on 47 of 50 sheets, the
other 3 refused because `extract` now cuts them differently. But it reads
**472 of 1,024 (46 %, 43-49)** of the builders' animals, against a registered
90 %: stacked multi-panel sheets are read in part, and sheets the scanner
rejects not at all. **Limits.** These are the sheets someone once wrote a
builder for because they were hard; on the V25 campaign `extract` is fully
right on 41 of 50 sheets (S4). The error is omission, not corruption -- which
is what the legend check (S5) catches.

**On a normal campaign.** `export` adds no error of its own, so its CSV is
right exactly where the extraction is. On the 47 V25 sheets it exports (cut
identically by the V27 `extract`, which the rater checked blind on sheets it
was not built on): **fully right on 41 of 47 (87 %, 75-94)**, holding 1,363 of
1,518 animals (90 %). The six that are not right all fail on the subject
count. The CSV also carries a `readout` column written by the agent (`volume
(mm3)`, `bli`, ...), not yet measured -- a photon flux of 49,100,000 is
unremarkable; a tumour of that size is not.

## S9. The starter dataset -- `data/verified_extractions.csv`

**What it is.** The 41 V25/V27 sheets whose subject count, day grid and arms
rater A confirmed blind, less two where one block pools several arms: **39
sheets, 13 papers, 1,311 animals** (852 tumour volume, 459 bioluminescence).
`unpool export` re-derives them from the publishers' files; the repository
holds the extraction record, not the values.

**Metadata.** What pooling arms across papers needs -- tumour model, host,
control or treated, readout and unit, time axis and its origin, zeros at the
first time point -- was written per block by a Sonnet 5.5 agent from the
legend and methods, with the quote it relied on. Rater A then checked every
field against the paper on a phone, **not blind** (the agent's values were in
view), and looked up in the methods and SI PDF every field the quote did not
settle. **Result.** All six fields confirmed on **37 of 39 sheets**; on the
other two the papers do not state the host, the control arm, the model or the
unit, and `described_by` says which. Host was filled in from the methods on
12 sheets where the agent had left it unstated; on one of them the rater's
first correction (BALB/c) was itself wrong, and the methods settled it (B16F10
melanoma, in C57 mice).
`zero_at_start` was checked against the values, not by reading: it agrees on
39 of 39 sheets, and 125 animals in 5 sheets start at 0, which the papers do
not explain. Median time per sheet on the phone: 26 s. **Limits.** One rater,
not blind; a reviewer of agent-written metadata tends to accept it.
