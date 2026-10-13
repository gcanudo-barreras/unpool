# What a real campaign looks like

Not a toy. This is the output of the first campaign this tool ever ran:
**50 papers of `Nature Communications`, 35 of them shown here**, mined on
with the query `"tumor volume" OR "tumour volume"`.

| | |
|---|---|
| papers fetched | 35 |
| scanner acceptances | 23 |
| candidate sheets | 129 |
| verified so far | 4 -- **1 real, 3 false** |

`campaign_candidates.csv` is what `mine.py` writes: one row per accepted sheet,
with the DOI, the file, the sheet, the subject count, the fold change and the
header evidence.

`worklist.csv` is the same thing collapsed to one row per paper — the best
sheet, ordered best-first — with the two empty columns you fill in as you
verify: `verdict_human` and `notes`.

Four rows are filled. They are the honest shape of what this tool gives you:

```
PMC13373164   FALSE   DESeq2 table; 350 gene rows counted as animals
PMC13503664   FALSE   header says Time, values are a doubling concentration ladder
PMC13522462   FALSE   residue-residue contact matrix from molecular simulation
PMC13490386   TRUE    long format id|Time|P|M|log(tv+1), real per-animal series
```

Those four were chosen as the **most suspicious** of the 36, so 1-in-4 is not
the precision — it is what happens when you check the worst ones first, which
is what the ordering is for.

When you fill in the rest, `CONTRIBUTING.md` explains where to send them and
what it earns you.

---

# And what the whole path looks like, on one paper

The campaign above stops at a worklist. **`BUILD_REPORT.md` carries one paper
the rest of the way** — verify at the sheet, builder, both guards, CSV — with
the real output of every step, including the two places a guard refuses.

| | |
|---|---|
| source | `10.1038/s41467-026-76293-x`, sheet `Supplementary Fig. 8b.` |
| built | 41 mice, 5 arms, 9 time points, 369 rows |
| registered first | `docs/VALIDATION.md`, V6 |

```bash
python -c "from unpool import scan; print(scan.fetch('PMC13534483'))"   # 18 MB, once
python example/build_mdamb231_crispra_v1.py
#   -> example/corpus/mdamb231_crispra_v1.csv
```

**The CSV is not in this repository, and that is the point.** Its source is
CC BY-NC-ND: `ND` is *no derivatives*, and 369 restructured rows are a
derivative. So what ships is the builder, the report, and the guards' records —
which is what the top-level README means by *"not a dataset, a builder script
plus a build report"*. One command against the publisher's own bytes gives you
the rows; the `sha256` in the builder proves they are the same bytes this
report was written from.

`records/` holds what the guards wrote: `guard_*.json` and
`fingerprint_*.json`, each naming what it checked, over what, and — for the
reserved-unit screen nobody here configured — that it did **not** run.
