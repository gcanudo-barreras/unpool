---
name: unpool
description: "Find and verify individual-level data that is published only as a pooled summary: per-subject LONGITUDINAL series from open-access supplementary tables -- tumour volume and body weight, measured repeatedly over days. Use when someone wants raw per-subject numbers from the literature instead of a figure's mean +/- SEM. NOT for dose-response or IC50 curves (a concentration axis is not a time axis and the scanner mis-parses them), not for figure digitisation, and not for human patient data."
---

# unpool

**Supports:** per-subject longitudinal series -- tumour volume, body weight --
from open-access supplementary spreadsheets and flat text.

**Does NOT support:** dose-response / IC50 (see step 1), figure digitisation,
`.pdf` or `.docx` supplements, paywalled sources, human patient data.


Most preclinical papers publish `mean ± SEM`. The per-subject numbers usually
exist — in a supplementary spreadsheet nobody reads. This skill finds them,
refuses most of what it finds, and turns the survivors into a record that can
be re-run and audited.

**What you produce is a re-runnable record, never a bare dataset.** For a
campaign, that is your extraction CSV plus `unpool export`, which re-derives
the per-animal CSV from the sheets and states each animal's state; for one
source someone will build on, a builder script plus a build report. Anyone can
re-run either and get the same rows, or read why a candidate was refused. A
CSV typed by hand is not an output of this skill.

## Before anything

**The tool runs from a clone the user owns, never from where this skill is
installed.** Everything it writes — `runs/`, `si_cache/`, and above all the
user's verdicts in `contributed/` — lands inside that clone. A plugin or
skills directory is replaced by the harness on update, and verdicts written
there would be lost.

If `unpool --help` fails, it is not installed. **Ask the user where to keep
the clone** (suggest `~/unpool`), then:

```bash
git clone https://github.com/gcanudo-barreras/unpool <dir>
cd <dir> && pip install -e .     # Python >= 3.11; gives you `unpool`
```

Run every command below from that directory. Then, every session:

```bash
python -c "from unpool import scan; scan.preflight_banner()"
```

If it prints a banner, **stop and tell the user which package is missing.** Do
not create a virtualenv, do not switch code paths, and above all do not report
the resulting empty output as a result. Without the parsers the scanner reports
every spreadsheet as "no table found" — silently, and only ever toward
rejection. Measured: the same gate scores 21/21 with them and 4/21 without,
with a clean report both times.

The same rule covers a missing credential, a rate limit, or a fetch that 401s.
**A wall you could not get past is never a negative result.** Say so.

## The output contract — three words, and you may not blur them

Everything this tool touches is in exactly one of three states. **Use these
words, and only these, when you report to the user.**

| state | what it means | where it lives |
|---|---|---|
| **candidate** | the scanner accepted the sheet's *shape*. Measured precision is 8 of 20 (V10) and 8 of 20 out of sample (V18): most candidates are not data | `runs/*_candidates.csv`, `worklist.csv` rows with an empty `verdict_human` |
| **screened** | an agent — you, or an adjudicator — read the evidence and said TRUE or FALSE. Its error rate against a person is what V18/V23 measure | an adjudications CSV, or your own notes |
| **verified** | a **named person** read the sheet and wrote TRUE, or a builder re-derived it and asserted the subject count | `registry.csv`, `contributed/`, a builder |

Hard rules:

- **Never call anything "data", "the dataset" or "the results" unless it is
  verified.** "I found 12 candidate sheets in 9 papers; none is verified yet"
  is the correct sentence. "I found data for 9 papers" is a false statement,
  however likely it looks.
- **Your own TRUE is `screened`, not `verified`**, however sure you are. You
  do not promote it; the user does, by reading the sheet.
- **Report counts in all three states, every time:** *"N candidates, M
  screened (k TRUE), V verified."* A zero is reported, not omitted.
- **When the user asks you to get data, look in `registry.csv` first.** It
  holds the verified entries, with the file, sheet and licence for each. Mine
  only for what it does not have, and say which is which.
- **The starter dataset needs no mining.** If the user wants per-animal data
  ready to use, or asks to rebuild the starter / example / author's dataset,
  run `unpool export data/verified_extractions.csv -o <path outside the
  clone>`: 1,311 animals, 39 sheets, 13 papers, re-derived from the
  publishers' files (about 70 MB, 5-20 minutes). Then tell them what the
  README's "What is checked and what is not" says: counts, days and arms were
  verified blind; model, host, role, readout and time axis were checked by
  the author, not blind, and `described_by` names any field left open.
- **Respect the licence column.** `cc by-nc-nd` data can be used and cited; it
  cannot be redistributed in modified form. Say so when it applies.

## The workflow

### 1. Pick the profile, or make one

```bash
ls profiles/ profiles/contributed/   # tumor_volume, body_weight,
                                     # contributed/rotarod_latency
export UNPOOL_PROFILE=tumor_volume
```

The profile declares four column patterns and two floors. If the user's data
type is not there, copy the closest `.toml`, change `covariate` and `value`,
and **say plainly that the new profile has no measured recall** — only
`tumor_volume` does, and that figure does not transfer.

**And tell the user what a profile can and cannot buy them, because it is
measured and it is small.** Swapping the profile changes 3 of 115 accepted
sheets; the other 97% is decided by structure that no profile field touches.
Measured again at scale: deleting `bli|flux|radiance` from the shipped
`value` pattern moved **0 of 20,330 sheets** across 2,390 papers
(`docs/VALIDATION.md`, V7). Vocabulary is not where a data type lives.
Those 3 are all flat long-format text files. So a new profile genuinely works
for a long-format export (`ID,Time,Value`) and does **almost nothing** for a
wide spreadsheet. If the user's data is in spreadsheets and the scanner misses
it, a profile will not fix that — say so rather than letting them edit TOML for
an afternoon.

Run one profile per pass. The two shipped profiles overlap: a treated tumour arm
that barely grew falls inside `body_weight`'s stable band, so about three
quarters of what `body_weight` accepts is also accepted by `tumor_volume`. Read
the `fold=` and the `hdr=` before trusting either.

**There is no dose-response profile, and that is deliberate.** One was written
and deleted the same day: the scanner mis-parses IC50 plates at the structural
level -- on the one plate we could check it took a row of measurements as the
time axis -- and no profile field repairs a bad parse.

### 2. Freeze the search before you open anything

```bash
unpool mine "<model or query>" --journal "Nature Communications" --budget 300
#   -> runs/<tag>_candidates.csv     one row per accepted SHEET
```

**It is slow, and your harness has a command timeout.** Measured:
about 10 s per uncached paper at the default `--workers 4` (20 s at 1), so a
50-paper campaign takes minutes and a 300-paper one most of an hour. Run it in
the background and read the log as it grows. **An interrupted run is not
lost:** the same command again reuses every supplement already in `si_cache/`
(16 papers: 322 s cold, 31 s re-run), and the artifact is identical whatever
`--workers` is.

**`--journal` is the highest-yield thing in this tool and it costs nothing.**
Share of papers with an accepted sheet, on 100 papers per journal that
mention tumour volume and carry a supplement (V19, `studies/v19_tumor_volume.csv`):

| Communications Biology | Nature Communications | Nature Cancer | Nature Medicine | general population † |
|---|---|---|---|---|
| 78% | 72% | 51% | 10% | **0%** |

These are candidates, not data. † the general-population figure is n=50 from
an earlier screening pass and has not been re-measured. Say so if you quote
the contrast.

The mechanism is a **Source Data policy**, not prestige — `Nature Medicine`
and `Nature Cancer` share a publisher and a field and differ by a factor of
five. Omit `--journal` and you are searching the population measured at 0%.
`mine.py` prints that warning and names journals worth trying; do not scroll
past it.

A second campaign on the same query returns the **same papers** — the sort is
deterministic. Use `--offset` to take a different slice of the frozen order,
and `--tag` so the second run's artifacts do not overwrite the first's.

The scan order and the full candidate list go to disk, `fsync`ed, **before the
first supplementary file is fetched**. This is not bookkeeping. A candidate list
assembled after the fact is a list chosen with its answer already in view, and
nothing downstream can detect that it was.

Re-running does not reproduce a batch — the index grows. Reading its artifacts
does. Every artifact names the query, the sort, the budget and the unit counted.

### 3. Read the triage for what it is

The scanner decides on **structure, never on wording**. A sheet titled
"Tumor growth" holding `mean ± SD` is rejected. An untitled sheet whose rows are
subjects and columns are times is accepted. That asymmetry is the whole design.

Collapse the candidate sheets to one row per paper, best first:

```bash
unpool worklist runs/<tag>_candidates.csv
#   -> runs/worklist.csv   one row per PAPER, ordered best-first, with
#                          empty `verdict_human` and `notes` to fill in
```

This is the file the user works through, and the one their verdicts live in.
Re-running onto a worklist that already carries verdicts **refuses** rather
than overwriting it — use `-o` to write elsewhere, or `--force` if they mean
it. Those verdicts exist nowhere else.

**A rejection is not always a judgement.** A supplementary member over 40 MB
is skipped unread, and the paper is then reported as "no per-animal table
found". An audit found 4 of 13 such rejects had never been opened, one of
them holding ten sheets the scanner accepts. Unmeasured is not negative.

**Its acceptances are not findings.** On an unbiased sample of 20 accepted
sheets, seed registered before any sheet was opened, precision at the shipped
floors is **8 of 20 = 40%**, 95% interval roughly 19–61% (`docs/VALIDATION.md`,
V10, corrected by V17). V2's earlier `6 of 15` was measured at
`min_subjects = 5`; both say *about a third*. **Say which floors a precision
figure was taken at, or do not quote it**, and never pool two that were not.

The largest class of false accept is an **in vitro assay read as a time
course** — a replicate index taken for a calendar, a drug panel, a `Time
(minutes)` kinetic run — 5 of V10's 13, which is what step 4 exists to catch.
Next, 4 of 13, are large numeric matrices from another discipline — TCGA
quantiles, blot densitometry, imaging colocalisation — which is what a Source
Data workbook holds *besides* the growth curves.

Recall is **15/15** on the cached publisher fixtures, and that is a
**tuning-set figure**, not a score. Quote the two together or quote
neither.

### 3b. Read the paper before you open the workbook

```bash
unpool paper <PMCID> --sheet "<the accepted sheet name>"
```

**Do this for every candidate you are about to open.** Source Data sheets are
usually named after a figure panel, and the legend for that panel says what the
panel is. `paper.py` returns, in the paper's own words:

- the **legend** for that sheet's figure, with the panel's own sentences marked
- the **method** sentences — the formula, the calipers, the imaging system
- every **group size the paper claims**, to set against your own count
- the host strains, the licence, and whether it is open access at all

This is measured, not assumed (`docs/VALIDATION.md`, V17): a legend was located
for 16 of 20 accepted sheets, and among sheets whose legend said "tumour
volume/growth" precision was 4 of 7 against the scanner's 35% on the same
sample.

**It also costs recall — 4 of 7 true positives kept — so it is never a filter.**
Do not drop a candidate because its legend looks wrong. A figure has many
panels and the legend you matched may belong to another one; V17 measured that
happening.

**Why it is worth the minute it takes.** On `PMC7138317` the sheet carries no
unit, no animal label and no day label — only `DMSO / Dox / ATMi-1`, six
replicates and `Average`/`SD` rows. A careful reader scored it FALSE as
unresolvable. The legend says *"tumor volumes at the indicated time points (C)
… injected to the nude mice"*, and the Methods say *"measured every week and
calculated as length × width² × 0.5"*. The verdict was wrong, and the
spreadsheet could never have said so.

When the legend is not found — a sheet called `Sheet1`, or a supplementary
figure whose legend lives in the SI PDF — that is **UNRESOLVED, not absent**.
Open the sheet.

### 4. Verify at the leaf — this is the step that cannot be skipped

For each acceptance, open the sheet and confirm **by reading**, not by trusting
a column name:

```bash
unpool sheet <PMCID>                     # every sheet in the paper, with the scanner's verdict
unpool sheet <PMCID> --sheet "<name>"    # the sheet itself; --rows 0 --cols 0 for all of it
```

A whole-paper workbook often holds the per-animal block far below the panel
the scanner happened to score: read past the first screen before you decide.
What you conclude is `screened`; the user makes it `verified`.

- **Model identity at the sheet.** Not in the title, not in the abstract. Which
  line or model is *this block*? Two of the false accepts failed here.
- **Which arm is the control**, and that it is one arm and not two pooled.
- **Subject count**, counted. `paper.py` prints every group size the paper
  CLAIMS; compare them against your count, and when they disagree say so
  and trust the count.
- **The covariate grid** — the actual days or doses. If the paper never states
  them, they are not derivable. Ask the user; a figure reading is legitimate
  provenance as long as it is recorded as one.
- **Units and method**, from the paper's own words — `unpool paper`
  prints the candidate sentences; quote one verbatim in the builder.
  `volume_mm3` as a header is not evidence of anything.

If any of these cannot be settled from the documents, **ask the user rather
than inferring**. A resolved-by-the-user answer recorded in the docstring is
worth more than a confident guess.

### 5. Write the builder

**Start from `unpool extract`**, which reads every block of a sheet into one
row per (subject, time, value) and prints what it found:

```bash
unpool extract <PMCID> --sheet "<name>"                  # blocks, subjects, day grid
unpool extract <PMCID> --sheet "<name>" -o ../out.csv    # the rows -- OUTSIDE the repo
```

Read its summary against the sheet before using a row. It gives every
subject a **positional** id (`b1:s3`) because labels like `Mouse #1` repeat
inside every arm; it leaves **`arm` empty**, for you to fill from the legend,
never from the labels; it counts subjects over **every** block, including
blocks that are not the readout (body weights, survival tables, in-vitro
plates parsed as time courses) -- set those aside and count the animals over
the blocks you keep (V25: the commonest extraction error, 8 of 50 sheets),
and check that count against the group sizes the figure legend states --
`unpool extract ... --legend` prints them; the legend is the reference, and
a count that disagrees is re-checked before it is written down;
it copies **zeros at day 0** as written and asks
whether they are measurements; and its `state` column says `candidate` unless
`registry.csv` holds that sheet. Its output is a starting point for the
builder, not a replacement for it: the builder is still the record.

**The whole campaign as one CSV.** Once your extraction CSV holds, for each
kept sheet, `subjects` per block, `arms` (`b1=Vehicle;b2=Drug;b3=DROP:
body weight`) and `readout` -- what the kept blocks measure, from the legend
or methods, with the unit when stated: `volume (mm3)`, or per block
`b1-b4=volume (mm3);b5=bli (photons/s)`. A modeller pooling arms needs the
rest too, each in the same syntax: `model` (cell line or PDX, implant site),
`host` (strain, immune status), `role` (`control` / `treated`), `time_axis`
(unit and origin: `days after tumour inoculation`; `days (origin not
stated)` if the documents do not say) and `zero_at_start` (if blocks start
at 0: `placeholder (not palpable)`, `baseline-normalised`, `measured 0`,
`not stated`; else `no`). Write `not stated` rather than guess:

```bash
unpool export runs/<campaign>_extractions.csv -o ../<campaign>_animals.csv
```

One row per (animal, day, value) with DOI, journal, licence, sheet, arm,
readout and `state`. `DROP` and `MIXED` blocks are left out and listed; a sheet that
`extract` now cuts differently from your recorded counts is refused, never
relabelled; `UNRESOLVED` blocks are left out like `MIXED`. **A block that
holds several arms side by side is `MIXED`, never named with a list**
(`b1=Ctrl (5), Drug (5)`): every animal in it would carry that whole list as
its arm. Animals are `screened` until a person confirms the extraction
(`unpool desk check`), and `verified` only then. V31: where `extract` reads
an animal, its values, days and arm grouping are right (472/472; 94 of 100
blocks one arm), and on a normal campaign the CSV is fully right on 41 of 47
sheets; but on hard multi-panel sheets it leaves animals out (46% of the
builders' animals found) -- so **compare each sheet's kept count with the
legend's arms x n before you report it**, and say which sheets fall short.

Copy `templates/builder.py`. **`example/BUILD_REPORT.md` is one paper carried
the whole way — mine, verify, build, guard, CSV — with the real output of
every step. Read it before writing the first one.**

The CSV it writes is the guards' schema, not a choice:

```
animal_id;model;study;source;days;volumes
```

Semicolon-delimited. `guard.py` requires `model, study, source, animal_id`;
`fingerprint.py` requires `animal_id, days, volumes`. A comma-delimited file,
or a `subject_id` column, is refused before either guard looks at a value —
and a builder that calls the guard itself dies on an uncaught `KeyError`
instead. For a non-tumour readout, put the covariate in `days` and the
response in `volumes` and say so in the docstring; renaming them loses the
re-export check.

The docstring is the provenance act, and it carries what nothing else will:

- the DOI and the exact source file
- **what a human resolved that the paper does not state**, marked as such, with
  the consequence if it is wrong
- what was cross-checked and what could not be
- `_VERIFIED_N` and the covariate grid as constants — the builder **refuses**
  when a re-download disagrees, rather than adapting to it

A builder that silently accepts a changed source is worse than no builder.

### 6. Refuse

```bash
unpool guard <builder-output>.csv              # one key one source; reserved units
unpool fingerprint check <builder-output>.csv  # identical-curve re-export
```

**Read what they print, not just the exit code.** Each screen has three
states and only one of them is a failure:

- **PASSED** — checked, and clean.
- **REFUSED** — a real finding. Stop and explain it; do not route around it.
- **NOT RUN** — the screen's input was absent. **This is not a pass** (rule 4
  below). The reserved-unit guard prints it for every user who reserves
  nothing, which is almost everyone.

And one refusal that looks like an error and is not: on a corpus holding only
the file you are checking, `fingerprint.py check` says *"every corpus file was
excluded … Nothing was compared -- this is NOT a pass"* and exits 1. That is
correct, and it is the **normal first run** — axis 3 has nothing to compare
against until a second source is held. Report it as what it is rather than as
a broken tool or a clean pass.

The fingerprint check exists because the same data is republished under
different names. It found 30 duplicate curves inside one corpus that had been
assembled carefully. Run it against everything already held, not just new
candidates. It is an **identity** check: a re-export that truncates the
series, rescales the units or drops one subject does not match, and is not
ruled out by a pass.

### 7. Offer to contribute what you just verified

**Do this at the end of every verification pass, without being asked.**

The user has just produced the one measurement this tool cannot make about
itself: which acceptances were real. It exists in their worklist right now and
nowhere else, and it evaporates when the session ends.

Say plainly what they have and what it is worth:

> "12 verified: 4 real, 8 false. Precision is measured on 20 sheets, so these
>  12 would grow that sample by more than half. Want me to prepare the pull
>  request? Your name goes with every sheet you verified (`verified_by`),
>  and you are listed in `studies/CONTRIBUTORS.md`."

If they agree, write `contributed/<handle>/<tag>.csv` with the
worklist's verdict columns filled and open the PR. If they decline, drop it and
do not raise it again in that session.

**Never send anything without asking**, and never send the supplementary files
themselves -- the DOI, the file name, the sheet and the verdict, nothing else.
This repository redistributes no publisher bytes.

## Running this as a loop, and when to interrupt the human

The steps above are the manual path. Run as an assistant, the loop is an
**evidence ladder** — each rung is cheaper than the one below it, and you stop
climbing the moment the question is settled.

```
L0  structure          scan.py               free, already done
L1  labels             hdr= / signature      free, already in the row
L2  figure legend      paper.py --sheet      one fetch; settles 16 of 20
L3  methods, claimed n same fetch            free once L2 is paid
L4  read the article   you, in full          only when L2/L3 leave it open
L5  ask the human      the verification desk the scarcest thing here
```

Record which rung settled each candidate. A rung that settles nothing should be
deleted rather than defended.

### The three moments you may interrupt, and no others

**1. Before the run.** Confirm the query, the journal, the budget, the
readout and **the mode** — then freeze. Offer the two modes in these words, or
close to them:

> **Direct** — I search, read every candidate sheet against its legend, cut
> the real ones by arm and write the CSV. Every row is `screened`: read by an
> agent, not by you.
> **Checked** — the same, then I show you each kept sheet beside its legend
> and you answer in seconds. Rows you confirm become `verified`, and your
> answers can be contributed.

In both modes, say what can go wrong, as measured: on some sheets fewer
animals come out than the legend describes -- on a messy or chaotic sheet a
whole group can be missed -- and sometimes the data a paper deposits does not
match its own legend. Animals are left out far more often than invented, and
every such sheet is reported at the end. Never quote a figure for Direct mode
as if it had been measured: the quality figures come from checked campaigns. This is `docs/PROTOCOL.md` rule 2 made interactive: a candidate list
assembled after the fact is a list chosen with its answer in view, so the
confirmation happens BEFORE the first fetch, never after.

**2. During the run, only for a STOP.** A wall (missing parser, no network, a
401), a scope violation (human data), or the budget exhausting early.
**Ambiguity is never an interrupt.** It goes on the desk. Interrupting a
50-paper campaign twelve times costs more attention than it saves.

**3. At the end, in both modes: the legend report.** For every kept sheet,
compare the animals you kept with the legend's arms x n (`unpool extract
--legend`) and list each sheet where they differ, or where the legend states
no n, by name: *"PMC… Fig. 3: 18 kept, legend says 4 x 6 = 24 -- one group may
be missing."* A mismatch means look, not overwrite (V26: the legend was wrong
about as often as the extraction). In Direct mode, deliver the CSV with this
list and stop.

**Then, in Checked mode: the verification desk.** Present the unresolved pile one at a
time, best-first, with the evidence already gathered — sheet excerpt, legend,
method sentence, claimed group size, labels. The person answers TRUE / FALSE /
SKIP in seconds **because the reading was already done**. That is the whole
point: you fetch, they decide, and deciding is cheap because nothing has to be
looked up.

```bash
unpool desk build runs/worklist.csv --budget 40
#   -> runs/worklist_desk.json                 the desk, one fetch per candidate
#   -> runs/worklist_desk.json.bundles.json    the ADJUDICATOR's input: evidence
#                                              only, sorted by PMCID, carrying
#                                              none of your ordering

# the adjudicator -- a separate instance, bundle only -- writes
#   pmcid,sheet,verdict[,note]     verdict = TRUE / FALSE / UNRESOLVED

unpool desk queue runs/worklist_desk.json \
    --adjudications runs/adjudications.csv --handle <them> --tag <campaign> \
    --seed <fixed before the first answer>
#   -> contributed/<handle>/<campaign>.csv
```

Answering can stop and resume: rows already answered in that file are not asked
again.

**About 2 desk items in 20 are ones the adjudicator already settled, mixed in
unlabelled, and you do not say which.** If the person only ever sees what the
agent could not resolve, the record holds the agent's opinion of itself and
never its error rate — `docs/EVAL.md` measured two models agreeing 20 times in
21 while both were wrong where the truth was known. The draw is seeded and the
seed is written into the desk file before the first answer.

Every answer is a contributed verdict (step 7). The sample this tool most needs
accumulates as a by-product of being used.

### Judge on evidence, never on your own summary

When you gather evidence and then judge it, you will anchor on the impression
you formed while gathering. That is not hypothetical: `PMC7138317` was scored
FALSE by a careful reader who formed "probably in vitro" from the sheet and
never fetched the legend that said "tumor volumes at the indicated time points
… injected to the nude mice" (`docs/VALIDATION.md`, V17).

So when you adjudicate, work from `unpool paper <PMCID> --sheet "<sheet>"
--json` — the bundle carries evidence and deliberately carries no
recommendation. If a second agent adjudicates, give it the bundle and **not**
your reasoning.

### Never tell the adjudicating step how many are still needed

If a run is looking for ten and has eight, the ninth and tenth get graded
generously. **Verdict inputs are evidence only** — not the quota, not the
running count, not how long the search has taken.

And the loop is **budget-bounded, count-reported**: run a declared budget and
say what it found. Never loop until a target count is reached. A target on
verdicts is an incentive to lower the bar, which is `docs/PROTOCOL.md` rule 9
(rule 3 below) wearing an agent costume.

### Which model may adjudicate — measured, not assumed

V23 put twenty V18 sheets to two adjudicators and scored both against a
person. **Claude Opus 5.5, reading the sheet itself plus the legend and
methods, agreed on 19 of 20, left none unresolved, and its one "TRUE where
the person said FALSE" turned out to be the person's misread** — the person
corrected it on the sheet's own title. Claude Opus 5, given the legend and methods
but not the sheet, agreed on 12 of the 14 it settled and left 6 unresolved.

So, as the registered decision rule allows: use **Claude Opus 5.5 reading the
sheet (`unpool sheet`), the legend and the methods** as the adjudicator, and
**keep the desk's human audit quota**. Its TRUE is still `screened`, never
`verified`. That recommendation names the model that was measured and no
other — a different model is recommended by running V23's protocol on it,
not by analogy — and n = 20 certifies nothing as a substitute for a person.

**V30 measured the smaller models on the same data** (115 sheets with a human
verdict; 44 extraction rows with a confirmed count), by its registered rule:

| | screening precision / recall | extraction kept total | use it for |
|---|---|---|---|
| Opus 5.5 | 100% / 100% (inflated: the truth was reconciled with its reasoning) | the reference | everything |
| Sonnet 5.5 | 100% / 96% | 43 of 44 | screening and extraction |
| Haiku 5.5 | 100% / 99% | 39 of 44 (rule: 40) | screening only |

Whichever model screens, the desk's human audit stays.

### The second-reader workflow, as commands

```bash
# 1. you screen: read each candidate sheet, write one row per sheet
#    runs/<tag>_adjudications.csv   pmcid,sheet,verdict,note   (TRUE/FALSE/UNRESOLVED)
unpool desk build runs/worklist.csv -o runs/<tag>_desk.json
# 2. the person verifies what you kept, blind, plus an audit of what you dropped
unpool desk queue runs/<tag>_desk.json --adjudications runs/<tag>_adjudications.csv \
    --review --audit-rate 0.2 --handle <them> --tag <tag> --seed <fixed now>
# 3. then, and only then, they see where you disagreed, and may change their answer
unpool desk reconcile runs/<tag>_desk.json --adjudications runs/<tag>_adjudications.csv \
    contributed/<them>/<date>-<tag>.csv
```

Step 3 exists because on V18 it recovered a real series the person had
discarded. A changed answer keeps round 1 in its note. Rebuild
`registry.csv` afterwards (`python studies/build_registry.py`): the person's
TRUEs are now `verified`.

### What you never delegate

The **subject count**. Two models were evaluated on it (`docs/EVAL.md`): they
agreed on the binary question 20 times out of 21, and on the count they agreed
on 12 of 18 and were wrong against known truth where it was known. `_VERIFIED_N`
comes from the parse; your job is confirming the parse targeted the right block.

## Rules you do not get to relax

1. **Open access only.** The fetcher returns `not_open_access` and that is a
   stop, not an obstacle. Do not work around a paywall.
2. **Attribution travels with the data.** Emit the DOI and licence per source
   in the build report.
3. **Never widen a pattern to make the file in front of you pass.** That is how
   a tuning set turns into a score. If a real file is missed, write down the
   header that defeated the scanner and measure any fix on the whole set.
4. **A check that did not run is not a check that passed.** Report `NOT RUN`,
   never a clean verdict, for any screen whose input was absent. A paper
   whose supplement was skipped for size was never opened — it is
   unmeasured, not rejected, and saying "no table found" about it is a
   claim about a file nobody read.
5. **Say which unit you counted, beside the count.** Scanner acceptances,
   verified cells and admitted subjects are three different numbers and they
   are not interchangeable.
6. **Human data is out of scope.** Individual patient data from clinical trials
   raises consent and re-identification questions this skill does not address.

## What this does not do

It does not read figures or digitise curves — it reads tables. It does not open
`.pdf` or `.docx` supplements. It does not verify anything: every acceptance is
a candidate until a person or an agent has read the sheet. It does not decide
whether two datasets should be pooled, only whether they could be.
