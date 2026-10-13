# Adapting this to your data type

A behavioural neuroscientist did this in under an hour, from a clean clone,
with no prior knowledge of the tool, and found a real per-animal rotarod
dataset on the first live run. Her profile ships at
`profiles/contributed/rotarod_latency.toml` exactly as she wrote it. This is
what she actually had to work out, in the order she hit it.

**Read the last section first if you are deciding whether this is worth your
time.** A profile buys less than it looks like it does, and the honest amount
is measured.

---

## 1. Copy the closest shipped profile

```bash
cp profiles/body_weight.toml profiles/my_measure.toml
```

`body_weight` is usually a better starting point than `tumor_volume`, because
its `[response]` block is already written for something that does not grow
without limit.

## 2. Change the three column patterns

```toml
[columns]
subject   = '^\s*(mouse|mice|rat|rats|animal|id|subject|sample|no\.?|#)'
covariate = '^\s*(day|days|time|timepoint|date|week|age|session|trial)'
value     = '(latency|rotarod|fall|rpm|duration|distance|time\s*on)'
```

Two things she had to discover by reading the regexes, because nothing said so:

- **The shipped `subject` pattern named the mouse and not the rat.** An
  oncology assumption nobody had examined. It is fixed now — partly because she
  reported it — but the lesson stands: read the pattern, do not assume it knows
  your field's vocabulary.
- **`covariate` matched only calendar time.** Behavioural cores stage by
  **trial** or **session** as often as by day, so she added those. They belong
  in her profile and were deliberately *not* added to the tumour one.

`value` is where your domain vocabulary goes. List the words your field puts in
a column header, not the words it puts in a paper.

## 3. Declare the response shape — this is the part that matters

```toml
[response]
direction      = "decrease"   # increase | stable | decrease
fold_lo        = 0.0
fold_hi        = 0.8          # must fall to under 80% of its start
min_consistent = 0.6          # fraction of subjects moving that way
allow_fractional_axis = false
```

**This block does far more work than the column patterns.** A tumour grows, a
body weight stays flat, a rotarod latency in a disease-progression model
declines. Get the direction wrong and you will silently match the wrong block
of the same workbook — which is exactly what `body_weight` used to do before
this block existed: it returned the *tumour* curve, at `fold=8.0`, under a
body-weight label.

She picked `decrease` / `0.8` / `0.6` by analogy to `body_weight`'s stated
guess, wrote in her file that it was a guess, and said which disease model she
had in mind. **Do that.** A documented guess can be argued with; an undocumented
one gets quoted as a measurement.

`allow_fractional_axis` only matters if your covariate is a concentration.

## 4. Run it

```bash
./.venv/Scripts/python.exe mine.py "rotarod" --journal "Nature Communications" \
    --budget 10 --profile my_measure --tag mytest
./.venv/Scripts/python.exe worklist.py runs/mytest_candidates.csv
```

`mine.py` needs no changes for a new field. Any query it does not recognise is
passed through as a raw search and frozen the same way — it prints
`RAW QUERY` and carries on.

**One trap, and the docs were right about it:** `UNPOOL_PROFILE` is read when
`scan.py` is *imported*. Setting it inside an already-running interpreter does
nothing, silently. Use `--profile`, which exists precisely because she reported
that `mine.py --help` never mentioned profiles at all.

## 5. Verify, because nothing above is data

Open the sheets. Precision on the profile that *has* been measured is **6 of
15**. Yours has none.

---

## What a profile actually buys you, measured

This is the part to read before deciding.

| | shape-only accepts |
|---|---|
| `tumor_volume` (measured, tuned over months) | 48% |
| `rotarod_latency` (new, first run) | **75%** |

"Shape-only" means the sheet matched **none** of your column patterns and was
accepted purely because it is a numeric grid on a monotonic ordinal axis.

And the harder number: swapping `tumor_volume`'s column patterns for ones that
can never match changes **3 accepted sheets out of 115**. The patterns decide
about 3% of the outcome on spreadsheets. On flat long-format text files
(`ID,Time,Value`) they decide everything.

So, honestly:

- **A new profile works** — she got a real dataset first try, in a field this
  tool was never built for.
- **It mostly rides the oncology structural detector**, inheriting its blind
  spots unmeasured. It cannot tell a rotarod decline from any other falling
  series in the same workbook.
- **Expect a worse precision than 6 of 15**, not better, and no way to know how
  much worse until you verify enough sheets to measure it.

If you do measure it, `CONTRIBUTING.md` says where to send the numbers and what
it earns you.
