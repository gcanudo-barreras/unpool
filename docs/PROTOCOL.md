# The protocol

Every rule here was bought. Most were bought by getting something wrong first,
and the wrong version is written down beside the rule, because a rule whose
cost is invisible gets relaxed by the next person who finds it inconvenient.

This document is the reasoning. `skills/unpool/SKILL.md` is the operational version.

---

## 1. Decide on structure, never on wording

A sheet titled **"Tumor volume data"** that holds medians is not per-subject
data. A sheet with no title at all, whose rows are subjects and whose columns
are days, is. The scanner therefore never reads titles, only shapes.

This asymmetry looks pedantic until it costs you a week. The specific paper
that produced it announced "Tumor volume data" on page 2 of its supplement and
carried medians.

The consequence is deliberate: the scanner will reject sheets a human would
accept on sight, and it will accept sheets no human would look at twice. The
first kind is a false negative you can find by widening; the second kind is why
step 4 exists.

## 2. Freeze the candidate list before opening the first candidate

The scan order and the full ID list are written to disk and `fsync`ed before
any supplementary file is fetched.

This is not bookkeeping. **A candidate list assembled after the fact is a list
chosen with its answer in view**, and no downstream check can detect that it
was. You will not remember, three weeks later, whether you added that query
term before or after you saw what it returned. The file remembers.

Corollary: re-running a mining pass does not reproduce it, because the
literature index grows. A query that returned 10,778 hits returns 13,549 a few
months later. What reproduces is the *record*, so every artifact carries the
query, the sort order, the budget and the date.

## 3. Precision and recall together, or neither

The triage instrument's recall is high on the files it was tuned against. Its
precision, measured once by hand on a real batch, was **2 of 6**. That is the
number this rule was bought with. The current figure is **6 of 15 (40%)**,
from an unbiased sample with its seed registered in advance — the old one
survived the larger test, which is not the usual outcome.

Of the four false accepts: two were the wrong tumour model entirely, the
scanner having matched a model name mentioned in the paper while every sheet it
counted was a different line; one was arm-level `Average / SEM / Number of
mice`, with the statistic columns counted as subjects; one was a differential
gene-expression table read transposed, gene symbols taken for subject IDs.

Publishing the recall alone would have been a lie of omission. Both numbers
travel together in every report this toolchain writes.

**And the recall number is a tuning-set figure, not a score.** The instrument
was re-tuned against those files twice. That is stated wherever it appears.

## 4. The scanner triages. It does not verify.

No acceptance becomes data until someone has opened the sheet and checked, by
reading:

- **model identity at the sheet**, not in the title and not in the abstract
- **which arm is the control**, and that it is one arm rather than two pooled
- **the subject count**, counted, and compared against the paper's own claim
- **the covariate grid**, meaning the real days or doses
- **units and method**, from the paper's own words

When the documents cannot settle one of these, **ask a human**. A day grid read
off a published figure, and recorded as a figure reading, is legitimate
provenance. The same grid inferred from "monitored at regular intervals" is not.

## 5. The builder is the record

One script per source. The CSV is regenerable; the docstring is not.

It carries the DOI, the exact file and sheet, the quoted method, what the paper
claimed versus what the data holds, and, the section that matters most,
**what a human resolved that the paper does not state**, marked as such, with
the consequence spelled out if it turns out to be wrong.

`_VERIFIED_N` and the covariate grid are constants, and the build **refuses**
when a re-download disagrees. It does not adapt. A source that changed under
you is a fact to investigate, not a number to update.

## 6. Refuse before writing, not after

A guard that runs on a file already on disk is a report. Two refusals run
before any row is emitted.

**One key, one source.** When two publications produce the same identity for
the same model, a loader fuses them and reports one source label for all of it,
so part of the data is attributed to a paper it did not come from and the
falsehood is invisible downstream. This happened, to twelve subjects, and
nothing noticed because nothing was looking.

**Reserved units stay out.** Anything held back to evaluate the dataset must
never be inside it, and the reserved unit is the *model*, not the arm: a
different arm of a reserved model puts that model back in the pool and the
evaluation leaks.

A missing manifest is a refusal, not a pass. A guard that permits everything
when its input disappears is worse than no guard, because it reports OK.

## 7. The same data gets republished under different names

Three axes, and they are not interchangeable:

1. **shared deposit DOI or accession**, mechanical, cheap, runs at triage
2. **shared corresponding author**, mechanical, noisy, flags rather than drops
3. **identical-curve fingerprint**, which needs the actual numbers, so it only
   runs once a builder has read the sheet

Axis 3 found **30 duplicate curves inside a corpus that had been assembled
carefully, one source at a time, by people paying attention.** Run it against
everything already held, not only against new candidates.

An exact fingerprint is exact: a re-export that truncates the series, rescales
the units, or drops one subject will not match. A pass on axis 3 is a pass on
identity, not on independence.

## 8. Say which unit you counted, beside the count

*Scanner acceptances*, *verified cells* and *admitted subjects* are three
different numbers. A batch that reports "6" without saying which one it means
is unreadable, and six acceptances have historically meant two cells.

## 9. Never widen a pattern to make the file in front of you pass

When a real file is missed, write down the header that defeated the scanner and
leave the pattern alone. Any fix is measured on the whole set, in its own pass,
and it states what it costs elsewhere.

Tuning on the example that exposed the gap is how a tuning set becomes a score,
and the moment you most want to do it, just after discovering your benchmark is
weaker than you thought, is the moment it does the most damage.

## 10. A wall is not a result

A missing library, an absent credential, a rate limit, a paywall: none of these
is a negative finding. Say what blocked you.

This one is recent and it is the sharpest. A spreadsheet parser was missing
from an interpreter, and the code answered "cannot import" and "this file is
corrupt" with the same empty return. Every spreadsheet became "no per-subject
table found", silently, and only ever toward rejection. The same gate scored
21/21 in one interpreter and 4/21 in another, printing a clean, plausible,
honest-looking report both times.

The failure was directional, which is what made it dangerous: it could only
manufacture *absence*, and absence is exactly what a mining tool is expected to
report most of the time.

## 11. A check that did not run is not a check that passed

The recall gate computed its negative-control verdict as "the control is not in
the failure list". When the control file was absent it could not be in that
list, so the gate reported **intact** for a check it had never performed.

Every screen in this toolchain now reports `NOT RUN` as a distinct state, and
`NOT RUN` cannot pass. If a candidate was never screened for window
compatibility, its record says so rather than reading like one that passed.

## 12. Open access only, and attribution travels with the data

The fetcher returns `not_open_access` and that is a stop. Licences and DOIs go
into the build report per source, not into a footnote.

Individual patient data from clinical trials is out of scope. The consent and
re-identification questions there are real and this toolchain does not address
them.
