# Contributing

The useful contribution to this project is **not code**. It is measurement.

Every figure in the README was measured by one rater, the author. A second,
independent rater is the study this project needs most. Beyond that, every
person who runs a campaign has to verify candidates at the sheet in order to
use the data at all, and that verification is exactly the measurement the tool
cannot make about itself. Sharing it costs a pull request.

---

## What to send, in order of value

### 0. Be the second rater on V25 — the one this project needs most

V25 is the campaign behind the headline figure (74 of 75). Its registration
planned two raters; only one ran (`docs/METHODS.md`, S3). A second rater
answers the same 95 sheets, blind, with the same seed:

```bash
git clone https://github.com/gcanudo-barreras/unpool && cd unpool
pip install -e ".[pdf]"
unpool desk build runs/v25_pile_source.csv -o runs/v25_desk.json   # fetches the evidence
unpool desk queue runs/v25_desk.json --adjudications runs/v25_adjudications.csv \
    --review --audit-rate 0.2 --seed 20260926 \
    --handle <you> --tag v25 -o contributed/<you>/v25.csv
```

The desk shows each sheet with its legend and methods and never the agent's
verdict; it saves after every answer, so it can be done over several
sittings. **Blind means blind:** do not open `runs/v25_adjudications.csv`,
`runs/v25_extraction_check.csv` or anything under `contributed/` before you
have answered every item, and say so in writing in the pull request.
Rater-rater agreement is then scored against the registration
(`docs/VALIDATION.md`, V25 P2).

**If you are considering it, get in touch first** — write to
guillermo@canudo.org or open an issue titled *Second rater* — so the details
can be agreed before you start.

### 1. A builder

A builder script is a verified cell *plus* its provenance: the DOI, the exact
file and sheet, the quoted method, the subject count you actually counted, and
the section no other format has — **what a human resolved that the paper does
not state**.

Start from `templates/builder.py`. Put yours in
`builders/<your-handle>/build_<source>.py`.

### 2. Verified verdicts

`mine.py` writes a candidates CSV; a worklist built from it has empty
`verdict_human` and `notes` columns. Fill them in as you verify, and send the
file:

```
contributed/<your-handle>/<tag>.csv
```

`desk.py` writes exactly that file for you, and stages the evidence first — the
figure legend, the method sentence, the group size the paper claims — so each
answer costs seconds instead of a fetch and a read:

```bash
unpool desk build runs/worklist.csv --budget 40
unpool desk queue runs/worklist_desk.json --handle <you> --tag <campaign> \
    --seed <fixed before you answer anything>
```

It carries four columns a hand-filled worklist does not: `evidence_at` and
`settled_at` (which rung of the ladder did the work), `agent_verdict`, and
`audit`. **`audit=yes` marks an item an agent had already settled and that you
were asked anyway, without being told which** — about one desk item in ten.
Those rows are the only measurement of whether an agent-assisted verdict can be
trusted at all, so do not drop them from a batch, least of all the ones where
you disagreed.

`TRUE` and `FALSE` are both valuable and **`FALSE` is the scarcer one**. False
positives are what the precision figure is made of, and a batch where you
rejected nine of twelve is a better contribution than one where you accepted
all twelve.

### 3. A false positive or false negative report

Use the issue templates. Give the DOI, the sheet name, and one sentence on what
the sheet actually contains. A single well-described false negative is worth
more than a general observation that the tool missed something.

---

## What happens to it

**Contributed data goes into a separate tier and is never silently merged into
ours.**

```
fixtures/ground_truth.csv    verified by this project, each verdict citing the
                             builder that established it
contributed/                 verified by others, cited, NOT re-verified here
```

Recall and precision are reported **separately over each**. This is not
distrust; it is this project's own rule 8 — say which unit you counted, beside
the count. A figure over 30 contributed verdicts is a real figure and it is a
different figure from one over 30 we checked ourselves, and pooling them would
hide which is which.

If your verdict turns out to be wrong, it is corrected in place with a note.
Nothing is deleted. The record of a corrected verdict is more useful than a
clean one.

---

## What you get

**Credit that travels with the data.** What you verify carries your name:
your batch lives in `contributed/<handle>/`, `registry.csv` points to it, and
every animal exported from a sheet you verified names you in its
`verified_by` column. Contributors are listed in `studies/CONTRIBUTORS.md` as
their work lands.

**To contribute or collaborate**, write to guillermo@canudo.org or open an
issue. It is easier to agree the details before you start.

---

## Before you send

- **Say what you did not check.** A verdict of `TRUE` on subject count but not
  on model identity is useful if it says so, and misleading if it does not.
- **Do not re-tune the profile to make your file pass.** If a real sheet is
  missed, report it with the header that defeated the scanner. Widening a
  pattern against the file that exposed it is how a tuning set turns into a
  score (`docs/PROTOCOL.md`, rule 9).
- **Open access only.** Do not send data from behind a paywall, and do not send
  supplementary files at all — send the DOI, the file name and your verdict.
  This repository redistributes no publisher bytes and that is deliberate.
- **No human subject data.** Individual patient data from clinical trials is out
  of scope for consent and re-identification reasons.

## Code

Bug reports and fixes are welcome, with one standing request: a change to
`scan.py`'s judgement — the regexes, the floors, the layout branches — must come
with a measurement over the whole fixture set showing what it costs elsewhere.
Not because contributions are doubted, but because the first eight defects
found in this tool were all of one kind: something changed, nothing measured it,
and the tool reported a confident result anyway.
