# Every number this repository quotes, and what it was measured with

A figure without its configuration and its population is not a figure, and the
two get separated the moment somebody quotes one in a slide. This page is the
one place where they cannot be.

The rules it exists to enforce: **precision and recall travel together**
(rule 3), **say which unit you counted, beside the count** (rule 8), and **a
figure nobody but its author can reproduce is not a figure** (V15).

`STALE` below does not mean wrong. It means measured at a configuration this
repository no longer ships, and therefore quotable only with that configuration
attached.

---

## The headline pair — quote both or neither

### Recall — 15/15 = 100%
- **Configuration** `tumor_volume`, `min_subjects=4`, `min_points=4`
- **Population** the cached publisher fixtures the gate can reach: 17 of the 29
  files named in `fixtures/ground_truth.csv`. Eight more need a Dryad token;
  three are transcriptions rather than publisher bytes and are excluded by
  design.
- **Artifact** `tests/test_recall.py`, `fixtures/manifest.csv` (sha256-pinned),
  `fixtures/ground_truth.csv`
- **Status** CURRENT. Reproducible from a clean clone since V15 — before that,
  reproducible only by its author.
- **It is a TUNING-SET figure, not a score.** The instrument was re-tuned
  against those files twice. It says what the scanner does on the files that
  shaped it, which is a weaker claim than it looks.

### Precision — 8/20 = 40%, 95% interval 19–61%
- **Configuration** `tumor_volume`, `min_subjects=4`, `min_points=4`
- **Population** 450 eligible papers of the 480 the scanner then accepted across
  `si_cache/`; 20 drawn with `random.seed(20261018)` before any sheet was opened
- **Artifact** `runs/v10_sample.json`, `runs/v10_verdicts.csv`,
  `runs/v10_population.csv`
- **When** V10, corrected the same day by V17's retraction of
  `PMC7138317`
- **Status** CURRENT, and the weakest number here. Twenty items cannot separate
  a third from a half. `si_cache/` over-represents 27 journals and is not a
  random sample of the literature; the direction of that bias is unknown.

### Precision — 8/20 = 40%, 95% interval 22–61% (OUT OF SAMPLE)
- **Configuration** `tumor_volume`, `min_subjects=4`, `min_points=4`, the
  40 MB member cap, V12's `Day1` axis and V13's `AGG` repair
- **Population** 418 eligible papers of 484 accepted in `si_cache/`, every
  paper with a prior verdict excluded; 20 drawn with `random.seed(20260919)`
  before any sheet was opened
- **Artifact** `runs/v18_sample.json`, `runs/v18_population.csv`, verdicts in
  `contributed/gcanudo-barreras/v18.csv`
- **When** V18. **7/20 as first answered**; one verdict
  corrected by the human on documentary evidence (round 2, V23), as V17
  corrected V10
- **Status** CURRENT, and the first precision figure measured on papers no
  part of this repository had been tuned against. **Not pooled with 8/20**:
  different configuration, different draw.

### Delivered precision — 74/75 = 98.7%, 95% interval 92.8–99.8%
- **Unit** a sheet the agent (Claude Opus 5.5, reading sheet + legend +
  methods) returned TRUE, scored against one rater's blind round-1 verdict
- **Population** V25: `unpool mine "patient-derived xenograft" --journal
  "Nature Communications" --budget 50`, papers with any earlier verdict
  excluded; 173 accepted sheets in 26 papers screened, 75 kept; desk of every
  agent-TRUE plus a seeded 20% audit of agent-FALSE (95 sheets)
- **Artifact** `runs/v25_adjudications.csv`,
  `contributed/gcanudo-barreras/v25.csv`
- Round 1 (blind): 74/75, audit 19/20. Round 2 (rater
  shown the agent's note on the 2 disagreements): 75/75, audit 20/20 -- both
  resolved in the agent's favour. **Quote round 1** as the figure
- **Status** CURRENT. Supersedes the 9/9 below

### Smaller models (V30) — Sonnet 5.5 and Haiku 5.5
- **Unit** screening: a sheet with a human final verdict (115; 83 TRUE);
  extraction: a row with a confirmed subject count (44), right when the kept
  total equals it
- Sonnet 5.5: precision 80/80, recall 80/83, extraction
  43/44. Haiku 5.5: precision 82/82, recall 82/83, extraction 39/44
- **Status** CURRENT. Opus 5.5's 100% on the same set is inflated (truth
  reconciled with its reasoning) and is not quoted as a comparison

### Per-animal CSV on a normal campaign (V31 amendment) — 41/47 sheets = 87%, 95% interval 75–94%
- **Unit** a V25 sheet `export` writes (47 of 50; 3 refused as re-cut); right
  when rater A's blind V27 check said subjects, days and arms all right.
  Animals: 1,363 of 1,518 (90%) on right sheets, no interval (clustered)
- Written after V31's result, descriptive
- **Status** CURRENT. The headline for the CSV; quote beside the builders' 46%

### Starter dataset metadata (S9) — all six fields confirmed on 37/39 sheets
- **Unit** a sheet of `data/verified_extractions.csv` (39 sheets, 13 papers,
  1,311 animals); confirmed when rater A accepted or corrected model, host,
  role, readout, time axis and zeros at start against the paper
- Not blind (the agent's values were in view), not registered: a check, not a
  measurement of the agent. `zero_at_start` checked against the values, 39/39.
  Median 26 s per sheet on a phone, first pass
- **Status** CURRENT. Quote as "checked by the author", never as the agent's
  accuracy

### Per-animal CSV against hand-written builders (V31) — read 472/1,024 = 46% (43–49); right where read 472/472
- **Unit** an animal of the ten Europe PMC builders (1,247; 223 derived, out);
  found when some curve `extract` reads has exactly its values
- Registered before the code. X-P1 (>= 90% found)
  FAILED; X-P2 blocks one arm 94/100 (88–97); X-P3 days 472/472; X-P4
  bookkeeping exact on 47/50 V25 rows, 3 refused as re-cut
- **Status** CURRENT. A floor on hard sheets (builders were written for
  them), not a campaign rate; quote beside the V27 41/50

### Extraction right (shipped extract, V27+V29) — 44/50 = 88%, 95% interval 76–94%
- **Unit / population** as below, the same 50 V25 sheets
- **Status** CURRENT, and OPTIMISTIC: V29's two fixes came from these sheets.
  Always quote it beside the held-out 41/50 below

### Supplementary legend found (shipped) — 43/57 = 75%, 95% interval 63–85%
- **Unit** a V25 supplementary-figure sheet with no legend in the article XML
- After the post-hoc fix (case-insensitive captions,
  Peer Review Files skipped). Registered V28-P1 on the same sheets: 26/57;
  captions right 7/10 before the fix (V28-P2)
- **Status** CURRENT, OPTIMISTIC for the same reason

### Extraction right (V27 extract, held out) — 41/50 = 82%, 95% interval 69–90%
- **Unit** a confirmed sheet, right only if subject count, day grid AND arms
  are all right as rater A reads sheet and legend
- **Population** V25's 50 checked sheets, held out from the development of
  V27 (developed on V26's 68 failures); 39 re-assigned by fresh subagents, 11
  unchanged, all re-checked blind to which
- **Artifact** `runs/v27_review.csv`, `runs/v27_extractions.csv`
- Subjects 41/50, days 48/50, arms 48/50. The rater had
  seen these sheets in P3 (test-retest on the unchanged 11: 9/11)
- **Status** CURRENT. V29 then fixed the two faults V27 exposed; on the same
  rows that gives 44/50 -- post hoc, never quoted

### Extraction right (previous extract) — 31/50 = 62%, 95% interval 48–74%
- **Unit** an agent-kept sheet confirmed by the rater, counted right only if
  the subject count, the day grid AND each block's arm are all right as the
  rater reads sheet and legend
- **Population** V25: the first 50 of the 74 confirmed sheets, in file order
  (15 of 21 papers); the rater stopped at 50 before any rate was computed
- **Artifact** `runs/v25_extraction_check.csv`, `studies/v25_p3.py`
- Per column: subjects 33/50 (66%), days 39/50 (78%),
  arms 42/50 (84%). The 24 unchecked rows cannot lift it to 80% (55/74 = 74%)
- **Status** CURRENT. P3 FALSIFIED (threshold 80%). Quote it beside the
  delivered precision: the agent finds the sheet; the extraction is checked.
  Round 2 (blind recount of 11 sheets, then reconciliation): 23/50 = 46%
  (33-60) for the totals as delivered; 36/50 = 72% (58-83) counting only
  kept blocks -- **post hoc, never quoted as a measurement**. Quote round 1

### Delivered precision (earlier) — 9/9, 95% interval ~70–100%
- **Unit** a sheet the agent (Claude Opus 5.5, reading the sheet) returned
  TRUE, scored against a person's final verdict
- **Population** V23 (8 agent-TRUE of V18's twenty) + V24 (1 agent-TRUE of 26)
- 8 of 9 confirmed independently; the ninth on the
  person's second reading of the sheet's own title (V23 round 2). Of the
  person's real series, the agent missed none (V23: 8 of 8; V24: 0 of 5
  audited agent-FALSE were real)
- **Status** SUPERSEDED by V25 (74/75); kept as the record of V23 + V24

### Paper-level precision — 9/20 = 45%, 95% interval 26–66%
- **Unit** the PAPER: counted if ANY sheet the scanner accepts in it holds a
  real per-subject series. The sheet-level figure above is 8/20
- **Population and artifact** V18's twenty papers; the 26 other accepted
  sheets of its 7 FALSE papers screened by Claude Opus 5.5
  (`runs/v24_adjudications.csv`), every agent-TRUE plus a seeded audit of 5
  read blind by the human (`contributed/gcanudo-barreras/v24.csv`)
- **When** V24. **Status** CURRENT; 20 agent-FALSE sheets were not
  audited and stay `screened`

### Agent adjudication against a person — 19/20 (Opus 5.5, sheet read) vs 12/14 settled (Opus 5, bundle only)
- **Population** V18's twenty, the human's verdicts as truth
- **Artifact** `runs/v23_adjudications.csv`, `runs/v18_adjudications.csv`
- **When** V18 P2, V23
- **Status** CURRENT. **Quote 19/20, round 1**, the independent figure (95%
  interval ~76–99%). The one disagreement was the human's misread, corrected
  in round 2 after reading the agent's evidence -- which makes round 2's 20/20
  a better truth, not a measurement of agreement.

### Precision — 6/15 = 40% (SUPERSEDED CONFIGURATION)
- **Configuration** `min_subjects=5` — a floor this repository no longer ships
- **Population** a single campaign, seed `20260917`
- **Artifact** `runs/v2_sample.json`. The verdicts themselves exist only as
  prose in V2.
- **Status** HISTORICAL. **Must not be pooled with 8/20**: different floors,
  different population. Both say "about a third"; that is a coincidence of
  wording, not 35 items.

---

## The finding the paper is built on

### Journal yield — 76% / 71% / 49% / 10%, against 0% for the general population
- **Configuration** `tumor_volume`, **`min_subjects=5`**
- **Population** 100 unselected papers per journal, 27 journals. The 0% is n=50
  from an earlier screening pass and has never been re-measured.
- **Artifact** `studies/journal_yield.csv`, `studies/journal_yield.py`
- **Status** ⚠ **STALE FLOORS.** V9 lowered `min_subjects` to 4,
  after this ran. Lowering a floor can only ADD acceptances, so these are a
  **LOWER BOUND** at the shipped configuration and the gap is unmeasured. The
  CSV records `profile` and `unit` but **not the floors**, so the file cannot
  say this about itself — which is the defect. The staleness is just its
  consequence.
- **Re-measured for the four journals that carry the contrast** (V19,
  `min_subjects=4`, a NEW 100-paper sample per journal, ids frozen to
  `studies/journal_yield_ids.csv`): Communications Biology **78%**, Nature
  Communications **72%**, Nature Cancer **51%**, Nature Medicine **10%**.
  Artifact `studies/v19_tumor_volume.csv`. The other 23 journals in
  `journal_yield.csv` remain at `min_subjects=5` and unrefreshed.
- **And what these percentages are ABOUT was narrower than it read** (V19): the
  sampling query is `("tumor volume" OR "tumour volume") AND HAS_FT:Y AND
  HAS_SUPPL:Y`, so every paper counted already mentions tumour volume. The
  figure means *among papers that discuss tumour volume and carry a supplement*,
  journal X publishes an accepted sheet N% of the time. It does **not** mean
  "journal X publishes per-subject source data N% of the time". Testing that
  needs a different sampling frame, not a different profile.
- **And it is a yield of SCANNER ACCEPTANCES, not of verified data** — the CSV
  says so in its own `unit` column. Multiply by precision for usable data.

---

## Census and scope

### 2,390 papers · 20,330 sheets · 2,753 accepted sheets · 484 accepted papers
- **Configuration** `tumor_volume`, `min_subjects=4`, `min_points=4`
- **Artifact** `runs/v18_population.csv`, `runs/v18_sample.json` (`sweep_stats`),
  re-derivable with `studies/precision_population.py`
- CURRENT.
- 22 tabular members over 40 MB were skipped unread, and **8 papers had no other
  tabular member: NOT JUDGED, not rejected** (rule 11).
- V10 swept the same cache and found 480 accepted papers. The
  difference of 4 is V12's `Day1` axis net of V13's `AGG` repair.

### Vocabulary is not where a data type lives — 0 of 20,330 sheets
Deleting `bli|flux|radiance` from the shipped `value` pattern moved **no sheet
at all** across 2,390 papers (V7). **Artifact** `studies/bli_census.csv`.

### A profile decides 3 sheets in 115
22 fixtures / 368 sheets. All three are flat long-format text. A
profile is decisive for an `ID,Time,Value` export and close to irrelevant for a
wide spreadsheet.

---

## The article layer

### Legend located for 16 of 20 · precision among legend-positive 4/7 = 57%
- **Artifact** `runs/v17_legends.csv`. **When** V17.
- **Status** ⚠ **IN-SAMPLE. NOT QUOTED AS A FIGURE ANYWHERE.** The legend
  vocabulary was written while looking at those twenty sheets. V18 is the
  out-of-sample test: registered, not yet measured.
- It also costs recall — 4 of 7 true positives kept — which is why the article
  ORDERS and never filters.

---

## What has no figure at all

### `body_weight` recall — NOT MEASURED. None.
The profile prints exactly that on every run. A real figure needs sheets
verified BY READING to hold per-animal weight, assembled by some route other
than this scanner, or the measurement is circular. Nobody has assembled one.

### The agent's error rate against a person — V18, registered, unmeasured
`docs/EVAL.md` measured two models agreeing with EACH OTHER 20 times in 21, and
agreeing on the count 12 of 18 while both were wrong where truth was known.
Agreement is not accuracy. V18 is the first measurement against a human.

---

## Where the verdicts live, which is not where the samples live

Every DRAW is now a committed artifact under `runs/`. Several VERDICT SETS are
not: they exist as prose inside `docs/VALIDATION.md`.

| study | sample | verdicts |
|---|---|---|
| V1 (9 audited) | — | prose only |
| V2 (6/15) | `runs/v2_sample.json` | prose only |
| V8 (11 sheets read) | — | prose only |
| V9 (2 of 10) | `runs/v9_sample.json` | prose only |
| V10 (8/20) | `runs/v10_sample.json` | `runs/v10_verdicts.csv` |
| V17 | — | `runs/v17_legends.csv` |
| V18 | `runs/v18_sample.json` | `runs/v18_adjudications.csv` (agent), `contributed/` (human) |

Prose is readable and it is not diffable. Anyone re-deriving V2's or V9's
numbers has to transcribe them out of a narrative first.
