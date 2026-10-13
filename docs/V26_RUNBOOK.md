# V26 runbook — for the session that runs part A

V26 is registered in `docs/VALIDATION.md` (last section, with its amendment).
This file is the procedure for **part A**. Part B has its own stops and does
not start until V25's P3 is scored. **Where this file and the registration
disagree, the registration wins.**

**Do not start before V25 is closed** (P3 scored, Result written): rater A
answers one study at a time.

## Before anything: what the running session must NOT read

It is the adjudicator, and it has to arrive clean. Do not open:

- `runs/v*_adjudications.csv`, `runs/v*_r1_adjudications.csv`, `runs/v*_desk.json`
- `contributed/**`
- `runs/v25_extraction_check.csv`, `runs/v25_extractions.csv`
- the Result sections of V10–V25 in `docs/VALIDATION.md`

Read: `AGENTS.md`, `skills/unpool/SKILL.md`, `docs/PROTOCOL.md`, the V26
registration, this file.

**Never narrate a verdict in the chat.** Verdicts go into files only, and the
rater is asked not to open the tool calls that write them.

## 0. The timeline

Every phase's wall-clock start and end, as it happens, to
`runs/v26_timeline.csv` — `phase,start_iso,end_iso,note`.

## 1. Mine (fixed at registration — do not change)

```bash
python -m unpool mine '"MC38" OR "CT26"' --journal "Nature Communications" \
    --budget 50 --tag v26 --workers 4
```

About 10 minutes uncached: run it in the background. Output
`runs/v26_candidates.csv`.

## 2. Exclude every paper that already carries a verdict, and freeze

As V25 step 2 (`docs/V25_RUNBOOK.md`), with `v26` for `v25`:
`runs/v26_pile_source.csv` and `runs/v26_sample.json`. **Commit the sample
before opening any sheet.**

## 3. Screen every sheet, and extract EVERY sheet

For each sheet: `unpool sheet` and `unpool paper` as in V25, the question
verbatim from the V25 registration. Write `runs/v26_adjudications.csv` —
`pmcid,sheet,verdict,readout,rung,note`.

**Unlike V25, for EVERY sheet — TRUE and FALSE alike** (registration, part A
change 1): `unpool extract <PMCID> --sheet "<name>"` (summary mode), assign
each block's arm from the legend where the sheet is a series, and write one
row per sheet to `runs/v26_extractions.csv` —
`pmcid,sheet,blocks,subjects,time_grid,arms,note`. A sheet with no block gets
`blocks=0`. **A summary, never the values.**

Part C (amendment 2): `subjects` is written **per block**, as `extract`
reports it — `b1:8;b2:5;b3:8` — never as a total. A block that is not the
readout (body weights, survival, an in-vitro plate, a summary table) is
written in `arms` as `bN=DROP: <reason>` (`b4-b5=DROP: ...` and
`b2,b4=DROP: ...` work). The desk sums the blocks not dropped; do not type a
total anywhere.

Amendment 3: run `unpool extract <PMCID> --sheet "<name>" --legend` and
compare the kept blocks with the group sizes the legend states — **the legend
is the reference**. Write the outcome in a `legend` column (after `arms`):
`match: 4 arms x n=5 = 20`, `mismatch: <why>` or `none stated`. On a
mismatch, re-check the cut and the DROP blocks first; if the sheet still
differs (deaths, exclusions), keep the sheet's count and say why. Never type
the legend's n as the count. Columns:
`pmcid,sheet,blocks,subjects,time_grid,arms,legend,note`.

**Commit both files before the rater sees an item.** That commit is the seal.
Record its hash and `git rev-parse HEAD:unpool/extract.py` in the timeline:
part A is measured with `extract` as it stood at the seal.

## 4. The rater, blind

```bash
python -m unpool desk build runs/v26_pile_source.csv -o runs/v26_desk.json
python -m unpool desk queue runs/v26_desk.json \
    --adjudications runs/v26_adjudications.csv \
    --review --audit-n 20 --split --seed 20261003 \
    --extractions runs/v26_extractions.csv \
    --handle gcanudo-barreras --tag v26 \
    -o contributed/gcanudo-barreras/<date>-v26.csv
```

- `--split`: half the items, seeded, show `extract`'s blocks before the answer
  (the `shown` column records which).
- after every TRUE the agent's arms appear and the extraction check is asked
  in place, into `contributed/gcanudo-barreras/<date>-v26.check.csv`.
- every answer carries `answered_at`, which A-P3 is read from: answer in
  sittings, and do not leave the desk open across a break mid-item.
- the rater declares in writing that they opened none of the adjudicator's
  tool calls.

An extraction check left half-done (`q`) is finished with
`python -m unpool desk check runs/v26_desk.json <the .check.csv>`.

## 5. Score, then reconcile

Round 1 against the registration: A-P1 (`python -m unpool desk selftest`,
the sentinel), A-P2 (agent-FALSE audit, rater TRUE count of 20, SHOWN and
HIDDEN halves side by side), A-P3 (median seconds between consecutive
`answered_at`, first item of each sitting dropped, SHOWN vs HIDDEN), A-P4
(delivered precision with its interval, descriptive). Write the Result.
Commit. Only then `desk reconcile`, round 2 beside round 1, rebuild
`registry.csv`, commit.
