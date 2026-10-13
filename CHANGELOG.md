# Changelog

## 0.1.0 — 2026-10-13

First public release. Every figure below was measured in a study registered
before it ran; populations and intervals are in `docs/METHODS.md`, every
number beside its configuration in `docs/FIGURES.md`.

**The workflow, as commands** (`unpool <command>`, from a clone):

- `mine` — query Europe PMC, download each open-access supplement, freeze the
  scan order to disk before the first file, keep the sheets whose structure
  looks like per-subject series. Parallel downloads (`--workers`), atomic
  cache writes, a resumable run.
- `worklist`, `sheet`, `paper` — one row per paper; any sheet printed or
  listed with the scanner's verdict; the figure legend, methods and group
  sizes, including supplementary legends read from the SI PDF
  (`pip install -e ".[pdf]"`).
- `extract` — a sheet cut into one block per arm as a tidy CSV, GraphPad
  exports included (days down, animals across, the arm named once in a merged
  cell); `--legend` prints the legend's group sizes beside the blocks.
- `desk` — a person verifies, blind to the agent's verdict until they have
  answered: screening with an audit of agent-FALSE, reconciliation as a
  second round that keeps the first, and `desk check` for subjects, days and
  arms, resumable.
- `export` — the campaign as one per-animal CSV: DOI, journal, licence,
  sheet, arm, tumour model, host, control/treated, readout, time axis, value,
  state and who verified it (`verified_by`) per row; `DROP`, `MIXED` and `UNRESOLVED` blocks left out and
  listed; a sheet `extract` now cuts differently is refused, not relabelled.
  Progress per sheet, written atomically.
- `scan`, `guard`, `fingerprint` — the scanner on its own; checks for builder
  scripts, including identical curves re-exported under another source.

**Data that needs no agent.** `data/verified_extractions.csv`: `unpool export
data/verified_extractions.csv -o animals.csv` re-derives 1,311 animals from
39 sheets in 13 papers (852 tumour volume, 459 bioluminescence). Counts, days
and arms checked blind by a person; model, host, role, readout and time axis
written by an agent and checked by the author against the paper, not blind
(all fields confirmed on 37 of 39 sheets). `registry.csv`: 111 verified
entries in 56 papers.

**For agents.** `skills/unpool/SKILL.md` runs the workflow and holds the
agent to the output contract — `candidate` (scanner), `screened` (agent),
`verified` (a person or a builder); nothing is called data until verified.
Claude Code plugin and marketplace, install notes for Codex and OpenCode,
`AGENTS.md` for agents changing the code.

**Measured state** (Claude Opus 5.5 as the agent, one rater):

- Sheets the agent keeps that really hold per-animal series: 74 of 75
  (98.7%, 92.8–99.8) on a fresh 50-paper campaign (V25).
- Subject count, day grid and arms all right: 44 of 50 (88%), post hoc; 41
  of 50 (82%) on sheets the change was not developed on (V27, V29).
- Supplementary legend found: 43 of 57 (75%), right on 10 of 10, post hoc;
  26 of 57 as registered (V28). Where the kept count equals the legend's arms
  x n, 10 of 10 rows right (V26).
- Per-animal CSV fully right on 41 of 47 sheets (87%), 90% of their animals;
  on ten hand-built hard sheets it reads 46% of the animals and every one it
  reads is right (V31).
- Scanner alone: precision 8 of 20 (40%), recall 15/15 on tuning fixtures.
- Sonnet 5.5 does the whole agentic phase about as well (screening 100% /
  96%, extraction 43 of 44); Haiku 5.5 the screening (V30).
