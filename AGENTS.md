# Agent instructions for this repository

**To USE the tool** (find and verify per-animal data for a user): follow
`skills/unpool/SKILL.md`. It is the operational manual, and it holds you to
the output contract below.

**The output contract, in one table** — use these words and only these:

| state | means | lives in |
|---|---|---|
| `candidate` | the scanner accepted the sheet's shape (precision ~40%) | `runs/*_candidates.csv`, `worklist.csv` |
| `screened` | an agent said TRUE/FALSE — including you | adjudication CSVs |
| `verified` | a named person read the sheet, or a builder re-derived it | `registry.csv`, `contributed/`, builders |

Nothing is called "data" until it is `verified`. Look in `registry.csv`
before mining. Report counts in all three states.

**To CHANGE the tool:** read `docs/PROTOCOL.md` first. The rules that bind a
code change here:

- `python tests/test_smoke.py` must pass (offline). If `fixtures/cache/` is
  filled (`python fixtures/fetch.py`), `python tests/test_recall.py` must too.
- **Never widen a pattern or move a floor to make the file in front of you
  pass** (rule 9). A change to what the scanner accepts is registered in
  `docs/VALIDATION.md` — with predictions and a falsifier — *before* it is
  written, and measured after.
- A number is quoted only beside its configuration and population
  (`docs/FIGURES.md`). Precision and recall travel together.
- Never commit publisher bytes; `si_cache/` and `fixtures/cache/` stay out.
- Never open `runs/v*_adjudications.csv` while a human is answering the same
  sample: an agent's verdict seen before a person answers voids the
  comparison.
