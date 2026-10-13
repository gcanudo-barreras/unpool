# V25 runbook — for the session that runs it

V25 is registered in `docs/VALIDATION.md` (last section). This file is the
procedure, step by step, so a fresh session can run it without this
repository's history in its head. **Read the V25 registration first; where this
file and the registration disagree, the registration wins.**

## Before anything: what the running session must NOT read

It is the adjudicator, and it has to arrive clean. Do not open:

- `runs/v*_adjudications.csv`, `runs/v*_r1_adjudications.csv`, `runs/v*_desk.json`
- `contributed/**` (the human verdicts of earlier studies)
- the Result sections of V10–V24 in `docs/VALIDATION.md`

Read: `AGENTS.md`, `skills/unpool/SKILL.md`, `docs/PROTOCOL.md`, the V25
registration, this file.

**Never narrate a verdict in the chat.** The raters can read the chat. Verdicts
go into files only, and the raters are asked not to open the tool calls that
write them (V23's breach, V24's precaution).

## 0. The timeline

Write every phase's wall-clock start and end, as it happens, to
`runs/v25_timeline.csv` — `phase,start_iso,end_iso,note`. P4 is read from it.

## 1. Mine (fixed at registration — do not change)

```bash
unpool mine "patient-derived xenograft" --journal "Nature Communications" \
    --budget 50 --tag v25 --workers 4
```

About 10 minutes uncached: run it in the background. Output
`runs/v25_candidates.csv`.

## 2. Exclude every paper that already carries a verdict, and freeze

```python
import csv, json, sys
sys.path.insert(0, "studies"); sys.path.insert(0, ".")
from precision_population import known_verdicts
known, notes = known_verdicts()
rows = [r for r in csv.DictReader(open("runs/v25_candidates.csv", encoding="utf-8"))
        if r["verdict"] == "CANDIDATE" and r["id"] not in known]
```

Write those rows (every accepted SHEET of every remaining paper, not one per
paper) to `runs/v25_pile_source.csv` with columns `pmcid,file,sheet,n,pts,
hdr,signature,verdict_human,notes` (`verdict_human` empty), and the same list
plus the exclusion notes to `runs/v25_sample.json`. **Commit the sample before
opening any sheet.**

## 3. Screen every sheet (the adjudicator)

For each sheet: `unpool sheet <PMCID> --sheet "<name>" --rows 0 --cols 30`,
and `unpool paper <PMCID> --sheet "<name>"` where the sheet leaves it open.
The question is V23's, verbatim in the V25 registration. Write
`runs/v25_adjudications.csv` — `pmcid,sheet,verdict,readout,rung,note`.

For every sheet you mark TRUE: `unpool extract <PMCID> --sheet "<name>"`
(summary mode, no `-o` into the repository), assign each block's arm from the
legend, and write one row per sheet to `runs/v25_extractions.csv` —
`pmcid,sheet,blocks,subjects,time_grid,arms,note`, where `arms` is
`b1=<arm>;b2=<arm>`. **A summary, never the values: those are publisher bytes.**

**Commit both files before any rater sees an item.** That commit is the seal.

## 4. The raters, blind and apart

```bash
unpool desk build runs/v25_pile_source.csv -o runs/v25_desk.json
unpool desk queue runs/v25_desk.json --adjudications runs/v25_adjudications.csv \
    --review --audit-rate 0.2 --seed 20260926 \
    --handle <rater> --tag v25 -o contributed/<rater>/v25.csv
```

Rater A (the author) and rater B each run it separately, on their own, without
seeing each other's file. Rater B needs a clone of the branch, `pip install -e .`,
and `runs/v25_desk.json` + `runs/v25_adjudications.csv` handed to them as
files. Each declares, in writing, that they opened none of the adjudicator's
tool calls.

## 5. The extraction check (P3)

After rater A has answered, for every sheet they confirmed TRUE, prefill
`runs/v25_extraction_check.csv` — `pmcid,sheet,subjects_ok,times_ok,arms_ok,note`
— from `runs/v25_extractions.csv`. Rater A compares each line against the sheet
(`unpool sheet`) and the legend and marks `yes`/`no` in the three columns.

```bash
unpool desk check runs/v25_desk.json runs/v25_extraction_check.csv     --timeline runs/v25_timeline.csv
```

walks the open rows with the sheet and legend beside the agent's line, saves
after every row (`q` stops, a re-run resumes) and writes each session's wall
clock to the timeline. `python studies/v25_p3.py` scores it, and refuses while
any row is open.

## 6. Score, then reconcile

Score round 1 against the registration — P1 delivered precision (agent-TRUE
confirmed by rater A), P2 rater-rater and agent-rater agreement, P3 from the
extraction check, P4 from the timeline — and write the Result section. Commit.

Only then: `unpool desk reconcile ...` for each rater, report any changes as
round 2 beside round 1, rebuild `registry.csv`
(`python studies/build_registry.py`), commit.
