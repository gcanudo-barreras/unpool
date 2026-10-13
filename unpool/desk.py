"""THE VERIFICATION DESK: the unresolved pile, best-first, reading already done.

    unpool desk build runs/worklist.csv --budget 40
    #   -> runs/worklist_desk.json           the desk, evidence attached
    #   -> runs/worklist_desk.bundles.json   what the ADJUDICATOR sees, and
    #                                        nothing else

    unpool desk queue runs/worklist_desk.json \
        --adjudications runs/adjudications.csv --handle you --tag natcomm \
        --seed 20260918
    #   -> contributed/you/natcomm.csv   one row per answer

WHY IT EXISTS
------------------------------------------------------------------------------
Moment 3 of the interaction contract (`skills/unpool/SKILL.md`). A campaign produces a pile of
candidates; a person can answer TRUE / FALSE / SKIP on any of them in seconds
IF THE READING IS ALREADY DONE. So the ladder is climbed first -- L0 structure
and L1 labels are already in the worklist row, L2 the figure legend and L3 the
methods and the claimed group size come from one `paper.py` fetch -- and only
what is still open reaches a human.

Every answer is a contributed verdict (`CONTRIBUTING.md`). The ~100-verdict
sample this project most needs accumulates as exhaust from normal use instead of
as a chore nobody volunteers for.

THE FIREWALL, WHICH IS THE ONLY LOAD-BEARING PART
------------------------------------------------------------------------------
Three parties, and each is denied what would anchor it:

  Scout        (`build`) gathers. May form any opinion it likes; the opinion
               goes nowhere, because `*.bundles.json` carries evidence only.
  Adjudicator  sees the bundle. NOT the scout's reasoning, NOT the running
               count, NOT how many verdicts the run still needs. A quota is an
               instruction to grade the last ones generously -- rule 9 wearing
               an agent costume.
  The human    sees the same evidence and never the agent's verdict, which is
               why `_present()` prints from the bundle and `agent_verdict` is
               written to the CSV only after the answer is in.

THE AUDIT QUOTA
------------------------------------------------------------------------------
About 2 desk items in 20 are cases the ADJUDICATOR ALREADY SETTLED, mixed into
the pile unlabelled. Without them this repository would only ever learn the
agent's opinion of itself: `docs/EVAL.md` measured two models agreeing 20 times
out of 21 on the binary question and being wrong together where the truth was
known. Agreement is not accuracy, and only a human answer on an item the agent
was sure about can tell the two apart.

The draw is seeded and the seed is written into the desk file, so the audit set
is fixed before any answer is typed rather than chosen afterwards (rule 2).

WHAT IT REFUSES TO DO
------------------------------------------------------------------------------
It renders no verdict. It does not rank by promise beyond the order
`worklist.py` already computed. It never loops until a target count is reached:
`--budget` bounds the run and the tally is reported (`skills/unpool/SKILL.md`). A wall -- no
full text, not open access, a failed fetch -- is carried to the desk and printed
as a wall, never as an absent legend (rule 10).
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import random
import re
import sys


from unpool import paper
from unpool import scan
from unpool import sheet as sheet_mod

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 2 in 20. Fixed here rather than passed in, because a rate chosen per run is a
# rate chosen with a result in view; `--audit-rate` exists for a caller who
# means to change it and says so in the record.
AUDIT_RATE = 0.10

ANSWERS = {"T": "TRUE", "TRUE": "TRUE", "Y": "TRUE",
           "F": "FALSE", "FALSE": "FALSE", "N": "FALSE",
           "S": "SKIP", "SKIP": "SKIP", "": "SKIP"}

# A LEGEND IS WHAT THE PERSON IS ABOUT TO DECIDE ON, so it must not be mangled
# on the way to them. A cp1252 console turns `RAGE-/-` vs `RAGE+/+` (written
# with real minus signs) into `RAGE?/?` and `n = 9-12` into `n = 9?12`, which is
# exactly the arm distinction the answer turns on. utf-8 first, `replace` only
# as the fallback that keeps a Greek letter from killing the run.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):  # pragma: no cover - console dependent
    try:
        sys.stdout.reconfigure(errors="replace")
        sys.stderr.reconfigure(errors="replace")
    except Exception:
        pass


# ------------------------------------------------------------------ build
def _rows(path):
    # A registered study's frozen draw is a `*_sample.json`, and re-typing its
    # twenty rows into a CSV to feed this would put a hand-made file between the
    # draw and the desk -- exactly where a row could quietly change.
    if path.lower().endswith(".json"):
        with open(path, encoding="utf-8") as fh:
            blob = json.load(fh)
        if not isinstance(blob, dict):
            return blob
        # The floors and the profile are properties of the DRAW, recorded once
        # at the top of the sample file rather than on every row. The desk was
        # looking for them per row, finding nothing, and printing `floors=?/?`
        # at the person -- evidence the record holds, withheld from the only
        # reader who needs it.
        head = {k: blob[k] for k in ("min_subjects", "min_points", "profile")
                if k in blob}
        return [dict(head, **row) for row in blob["drawn"]]
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def deepest_rung(bundle, row):
    """-> the cheapest rung that could settle this candidate, L0..L3.

    Evidence GATHERED, not a verdict. Which rung actually settled it is known
    only once an adjudication arrives, and `queue` records that separately: a
    rung that settles nothing should be deleted rather than defended.
    """
    if bundle.get("legend"):
        return "L2"
    if bundle.get("methods") or bundle.get("claimed_n"):
        return "L3"
    if (row.get("hdr") or row.get("signature") or "").strip():
        return "L1"
    return "L0"


def build(worklist, out=None, budget=None, sheet_key="sheet"):
    rows = [r for r in _rows(worklist)
            if not (r.get("verdict_human") or "").strip()]
    if budget:
        rows = rows[:budget]
    items, tally, walls = [], {}, {}
    for i, r in enumerate(rows, 1):
        pmcid = (r.get("pmcid") or r.get("id") or "").strip()
        sheet = (r.get(sheet_key) or "").strip()
        print("  [%d/%d] %s %s" % (i, len(rows), pmcid, sheet[:40]),
              file=sys.stderr)
        try:
            b = paper.bundle(pmcid, sheet)
        except paper.PaperWall as exc:      # rule 10: carried, never absorbed
            b = {"pmcid": pmcid, "sheet": sheet, "walls": [str(exc)],
                 "legend": None, "legend_panel_sentences": [], "methods": [],
                 "claimed_n": [], "claimed_n_sentences": [], "hosts": []}
        rung = deepest_rung(b, r)
        tally[rung] = tally.get(rung, 0) + 1
        for w in b.get("walls") or []:
            # NAME THE WALL, DO NOT GUESS ITS CAUSE. This line first said
            # "no full text, not open access, fetch failed" about every wall it
            # counted; the first real run's eight walls were all "no legend
            # located" on papers whose full text had been fetched and read.
            # A message that asserts a cause it never checked is the thing this
            # repository exists to refuse.
            walls.setdefault(w.split(" -- ")[0].split(" for ")[0].strip(),
                             []).append(pmcid)
        items.append({"pmcid": pmcid, "sheet": sheet, "row": r,
                      "bundle": b, "evidence_at": rung})

    out = out or os.path.splitext(worklist)[0] + "_desk.json"
    desk = {"worklist": os.path.basename(worklist),
            "built": datetime.date.today().isoformat(),
            "budget": budget, "n": len(items),
            "audit_rate": AUDIT_RATE, "audit_seed": None,
            "evidence_tally": tally, "items": items}
    _write_json(out, desk)

    # THE ADJUDICATOR'S INPUT. Sorted by PMCID, not by promise: the worklist's
    # order is the scout's opinion about which is the better bet, and an
    # opinion is exactly what must not cross this line.
    bpath = out + ".bundles.json"
    _write_json(bpath, sorted(
        [dict(it["bundle"], row_evidence=dict(
            {k: it["row"].get(k, "") for k in
             ("sheet", "hdr", "signature", "n", "pts", "below_floor", "fold",
              "layout", "file", "min_subjects", "min_points", "profile",
              "note")},
            # Both parties judge the same evidence or the comparison is not
            # one. `fold` lives in a column on a worklist row and inside `note`
            # on a study's sample row, and the desk resolves that for the
            # person -- so the bundle must resolve it for the adjudicator too,
            # rather than handing it an empty string.
            fold=_fold(it["row"]),
            # THE SAME SHEET STRING THE DESK KEYS ON, not the raw cell. One
            # sheet in V18's draw is named "... (Fig 4F) " with a trailing
            # space: the desk stored it stripped and the bundle handed the
            # adjudicator the raw one, so the two files disagreed about the key
            # and only `read_adjudications`' own strip() was holding the join
            # together. Two spellings of one key is where a silent mismatch
            # lives.
            sheet=it["sheet"]))
         for it in items], key=lambda b: b.get("pmcid") or ""))

    print("\n  %d candidate(s) -> %s" % (len(items), out))
    print("  evidence gathered at: %s"
          % ", ".join("%s %d" % kv for kv in sorted(tally.items())))
    for kind, ids in sorted(walls.items(), key=lambda kv: -len(kv[1])):
        print("  WALL x%d: %s  (%s%s) -- carried to the desk, not a result"
              % (len(ids), kind, ", ".join(ids[:3]),
                 ", ..." if len(ids) > 3 else ""))
    print("  adjudicator input (evidence only, no ordering): %s" % bpath)
    print("  budget was %s and it is not a target: this reports what it "
          "found." % (budget if budget else "unbounded"))
    return desk


def _write_json(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False)


# ------------------------------------------------------------------ queue
def read_adjudications(path):
    """-> {(pmcid, sheet): (VERDICT, note)}; VERDICT in TRUE/FALSE/UNRESOLVED."""
    got = {}
    if not path:
        return got
    for r in _rows(path):
        v = (r.get("verdict") or "").strip().upper()
        if v not in ("TRUE", "FALSE", "UNRESOLVED"):
            raise SystemExit(
                "adjudication for %s is %r -- must be TRUE, FALSE or "
                "UNRESOLVED" % (r.get("pmcid"), v))
        got[((r.get("pmcid") or "").strip(),
             (r.get("sheet") or "").strip())] = (v, r.get("note") or "")
    return got


def plan(desk, adjudications, seed, rate=AUDIT_RATE, review=False,
         audit_n=None, split=False):
    """-> the ordered desk pile, audit items seeded into it.

    Unresolved keeps the worklist's order (best-first, computed upstream).
    Audit items -- ones the adjudicator settled -- are drawn with `seed` and
    inserted at seeded positions, so neither their identity nor their place is
    chosen once answers start arriving.

    REVIEW MODE (`review=True`) is the second-reader workflow V23/V24 measured:
    every agent-TRUE goes to the person, because a person reading it is the
    only way `screened` becomes `verified`; the agent-FALSE are audited at
    `rate` OF THE FALSE, at least one. The person still sees no verdict.

    `audit_n` fixes the audit at that many items instead of a rate (V26:
    a rate makes the audit's size, and so its power, depend on the campaign).
    `split` marks each item `shown` True/False -- whether `extract`'s blocks
    are printed before the answer -- balanced within the audit and within the
    rest, from its own seeded stream so the audit draw is the one a desk
    without `split` would make.
    """
    pile, settled = [], []
    for it in desk["items"]:
        v, note = adjudications.get((it["pmcid"], it["sheet"]), ("", ""))
        it = dict(it, agent_verdict=v or "NONE", agent_note=note)
        if review and v == "TRUE":
            pile.append(it)
        else:
            (settled if v in ("TRUE", "FALSE") else pile).append(it)

    rnd = random.Random(seed)
    # `--audit-rate 1.0` asks EVERY settled item as well, which is what a
    # measurement run needs: V18 compares the adjudicator against a person over
    # the whole draw, and 2-in-20 would compare it over two. It is not the
    # normal mode -- normal use asks the person only what is still open.
    base = len(settled) if review else len(pile)
    k = (len(settled) if rate >= 1.0
         else min(len(settled), max(1 if settled else 0,
                                    round(base * rate))))
    if audit_n is not None:
        k = min(len(settled), audit_n)
    audit = rnd.sample(settled, k) if k else []
    for a in audit:
        pile.insert(rnd.randrange(len(pile) + 1), dict(a, audit=True))
    pile = [dict(p, audit=p.get("audit", False)) for p in pile]
    if split:
        rs = random.Random("%s:shown" % seed)
        for group in ([p for p in pile if p["audit"]],
                      [p for p in pile if not p["audit"]]):
            order = list(range(len(group)))
            rs.shuffle(order)
            for rank, j in enumerate(order):
                group[j]["shown"] = rank < (len(group) + 1) // 2
    return pile


def sheet_excerpt(pmcid, member, sheet, max_rows=9, max_cols=7, width=15):
    """-> ([lines], wall) for the actual sheet, read from the local cache.

    PRINTED, NEVER STORED. It does not go into the desk file and above all not
    into `*.bundles.json`: those are publisher bytes, this repository
    redistributes none, and the adjudicator is meant to judge the DOCUMENTS.
    The asymmetry is deliberate and it is what V18's P2 asks about -- protocol
    rule 4 says no acceptance becomes data until a person has opened the sheet,
    so the person gets the sheet and the agent does not.
    """
    if not (pmcid and member):
        return [], "no cached file recorded for this row"
    try:                                          # cache only: the desk never fetches
        _, rows = sheet_mod.load(pmcid, sheet, member, fetch=False)
    except sheet_mod.SheetWall as w:              # a wall, never an empty sheet
        return [], str(w)

    out = []
    for r in rows[:max_rows]:
        cells = []
        for c in r[:max_cols]:
            t = "" if c is None else str(c)
            cells.append(t.ljust(width) if len(t) <= width
                         else t[:width - 1] + "~")
        out.append(" | ".join(cells).rstrip())
    if len(rows) > max_rows:
        out.append("... %d more row(s)" % (len(rows) - max_rows))
    return out, ""


def _fold(row):
    """First-to-last ratio. A worklist has it as a column; a study's sample has
    it inside `note` (`fold=1.9`), which is where `worklist.py` reads it from
    too. Printing `?` for a number the row is carrying is not a small thing on
    a screen someone is deciding from."""
    if (row.get("fold") or "").strip() not in ("", "?"):
        return row["fold"]
    m = re.search(r"fold=([\d.]+)", row.get("note") or "")
    return m.group(1) if m else "?"


def _present_blocks(pmcid, sheet, member, p):
    """`extract`'s own reading of the sheet, MECHANICAL ONLY (V26 part A):
    blocks, subjects, day grid, the labels the sheet writes. Nothing an agent
    wrote, so it says nothing about the agent's verdict."""
    from unpool import extract as extract_mod
    try:                                          # cache only: never fetches
        _, _, layout, blocks = extract_mod.extract(pmcid, sheet.strip(), member,
                                                   fetch=False)
    except sheet_mod.SheetWall as w:
        p("\n  BLOCKS: WALL -- %s\n" % w)
        return
    p("\n  BLOCKS, as `unpool extract` reads the sheet (layout %s)\n" % layout)
    if not blocks:
        p("    none found -- not evidence either way\n")
    for i, blk in enumerate(blocks, 1):
        p("    b%d  %2d subjects  t=%s\n       label: %s\n"
          % (i, len(blk["subjects"]), ",".join("%g" % t for t in blk["axis"]),
             blk["label"][:100] or "(none written on the sheet)"))


def _present(it, i, total, p=None):
    """Print the evidence. NEVER the agent's verdict, and never whether this
    item is an audit item -- both would decide the answer being asked for."""
    p = p or sys.stdout.write
    r, b = it["row"], it["bundle"]
    p("\n" + "=" * 74 + "\n")
    # The bundle carries the article's own metadata, so a desk built straight
    # from a population sweep -- which has no `doi`/`title` column, only
    # `member` -- reads exactly like one built from a worklist.
    p("  [%d of %d]  %s   %s\n"
      % (i, total, it["pmcid"], b.get("doi") or r.get("doi", "")))
    p("  %s\n" % (b.get("title") or r.get("title") or "")[:70])
    p("  sheet: %s   (%s)\n"
      % (it["sheet"], r.get("file") or r.get("member", "")))
    p("  L0/L1  n=%s pts=%s below_floor=%s fold=%s hdr=%s sig=%s "
      "floors=%s/%s\n"
      % (r.get("n", "?"), r.get("pts", "?"), r.get("below_floor", "?"),
         _fold(r), r.get("hdr") or "---", r.get("signature") or "---",
         r.get("min_subjects", "?"), r.get("min_points", "?")))
    lines, wall = sheet_excerpt(it["pmcid"], r.get("file") or r.get("member"),
                                it["sheet"])
    p("\n  THE SHEET ITSELF (rule 4: nothing is data until you have read it)\n")
    for ln in lines:
        p("    %s\n" % ln)
    if wall:
        p("    WALL -- not an empty sheet: %s\n" % wall)
    if it.get("shown"):
        _present_blocks(it["pmcid"], it["sheet"],
                        r.get("file") or r.get("member"), p)
    if b.get("legend"):
        p("\n  L2 LEGEND\n")
        for s in b.get("legend_panel_sentences") or []:
            p("    >> %s\n" % s[:300])
        p("    %s\n" % b["legend"][:900])
    else:
        p("\n  L2 LEGEND: not located -- UNRESOLVED, not absent. The sheet name"
          "\n     may carry no figure reference, or the legend lives in the SI"
          "\n     PDF rather than the full text.\n")
    if b.get("methods"):
        p("\n  L3 METHOD, the paper's own words\n")
        for s in b["methods"][:3]:
            p("    * %s\n" % s[:240])
    if b.get("claimed_n"):
        p("\n  L3 GROUP SIZES CLAIMED: %s   (against n=%s counted)\n"
          % (", ".join(b["claimed_n"][:6]), r.get("n", "?")))
    if b.get("hosts"):
        p("  HOSTS: %s\n" % ", ".join(b["hosts"]))
    for w in b.get("walls") or []:
        p("\n  WALL -- not a result: %s\n" % w)
    p("\n  TRUE = per-subject longitudinal series, this model, one arm.\n")


FIELDS = ["pmcid", "doi", "journal", "file", "sheet", "n", "pts", "hdr",
          "signature", "below_floor", "fold", "min_subjects", "min_points",
          "profile", "title", "verdict_human", "notes",
          "evidence_at", "settled_at", "agent_verdict", "audit",
          "shown", "answered_at"]


def _answered(path):
    if not os.path.exists(path):
        return set()
    return {(r.get("pmcid", ""), r.get("sheet", "")) for r in _rows(path)
            if (r.get("verdict_human") or "").strip()}


def queue(desk, adjudications, handle, tag, seed, rate=AUDIT_RATE,
          out=None, stdin=None, stdout=None, review=False,
          audit_n=None, split=False, extractions=None):
    stream = stdout or sys.stdout

    def p(s):
        # FLUSHED. `verdict [T/F/S]: ` and `note (ENTER for none): ` end with
        # no newline, and a console only shows a line once it ends: in the
        # first V18 session the note prompt never appeared, and the desk
        # looked frozen while it was waiting for an answer.
        stream.write(s)
        stream.flush()
    stdin = stdin or sys.stdin
    items = plan(desk, adjudications, seed, rate, review, audit_n, split)
    extractions = extractions or {}
    out = out or os.path.join(
        _HERE, "contributed", handle,
        "%s.csv" % tag)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    done = _answered(out)
    items = [it for it in items if (it["pmcid"], it["sheet"]) not in done]

    n_audit = sum(1 for it in items if it["audit"])
    p("  %d item(s) on the desk, best-first%s\n"
      % (len(items), " (%d already answered in %s)"
         % (len(done), os.path.basename(out)) if done else ""))
    p("  the reading is done: answer TRUE / FALSE / SKIP, ENTER skips.\n")
    p("  %d of them %s and you are not told which -- that is the only way\n"
      "  this project ever learns the agent's error rate rather than its\n"
      "  opinion of itself.\n"
      % (n_audit, "is an audit item" if n_audit == 1 else "are audit items"))

    new, counts = [], {"TRUE": 0, "FALSE": 0, "SKIP": 0}
    for i, it in enumerate(items, 1):
        _present(it, i, len(items), p)
        p("  verdict [T/F/S]: ")
        line = stdin.readline()
        if not line:                       # EOF: stop, do not invent answers
            p("\n  input ended -- %d answered, the rest stay on the desk.\n"
              % len(new))
            break
        v = ANSWERS.get(line.strip().upper())
        while v is None:
            p("  T, F or S: ")
            line = stdin.readline()
            if not line:
                v = "SKIP"
                break
            v = ANSWERS.get(line.strip().upper())
        p("  note (ENTER for none): ")
        note = (stdin.readline() or "").strip()
        counts[v] += 1
        if v != "SKIP":
            rec = _record(it, v, note)
            # WRITTEN NOW, NOT AT THE END. These accumulated in a list and were
            # appended after the loop, so Ctrl-C -- the obvious way to stop a
            # twenty-item desk -- destroyed every answer typed. The same class
            # of defect as `worklist.py` silently overwriting four verdicts:
            # the scarcest thing in this workflow, held in memory for no reason.
            _append(out, [rec])
            new.append(rec)
            # ONLY NOW, with the verdict on disk: the agent's arms, and the
            # extraction check folded into the desk (V26 part A).
            ex = extractions.get((it["pmcid"].strip(), it["sheet"].strip()))
            if v == "TRUE" and ex:
                ck = {k: ex.get(k, "") for k in CHECK_FIELDS}
                _print_extraction(p, ck)
                _ask_check(ck, stdin, p)
                _append_check(os.path.splitext(out)[0] + ".check.csv", ck)
    p("\n  %d TRUE, %d FALSE, %d skipped -> %s\n"
      % (counts["TRUE"], counts["FALSE"], counts["SKIP"], out))
    audited = [r for r in new if r["audit"] == "yes"]
    if audited:
        ok = sum(1 for r in audited if r["verdict_human"] == r["agent_verdict"])
        p("  audit: %d of %d agreed with the adjudicator. %d item(s) is a "
          "start,\n  not a rate -- it accumulates across desks.\n"
          % (ok, len(audited), len(audited)))
    p("  These are contributed verdicts. CONTRIBUTING.md: FALSE is the "
      "scarcer\n  half. To contribute them: guillermo@canudo.org or an issue.\n")
    return out, new


def _record(it, verdict, note):
    r, b = it["row"], it["bundle"]
    rec = {k: r.get(k, "") for k in FIELDS}
    rec.update({
        "pmcid": it["pmcid"], "sheet": it["sheet"],
        "doi": r.get("doi") or b.get("doi", ""),
        "journal": r.get("journal") or b.get("journal", ""),
        "title": r.get("title") or b.get("title", ""),
        "file": r.get("file") or r.get("member", ""),
        "verdict_human": verdict, "notes": note,
        "evidence_at": it["evidence_at"],
        # The rung that SETTLED it: the human, unless the adjudicator had
        # already settled it and this was an audit item.
        "settled_at": it["evidence_at"] if it["audit"] else "L5",
        "agent_verdict": it["agent_verdict"],
        "audit": "yes" if it["audit"] else "no",
        "shown": {True: "yes", False: "no"}.get(it.get("shown"), ""),
        "answered_at": _utc()})
    return rec


def _utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def correct(rows, key, verdict, reason, today=None):
    """Round 2, in place: the verdict changes, round 1 survives in the note.

    Exactly how V17 corrected V10 and V23 corrected V18 -- never a silent
    overwrite, because the round-1 answer is the independent measurement and
    the round-2 answer is the better truth, and a reader needs both."""
    today = today or datetime.date.today().isoformat()
    hit = [r for r in rows
           if (r.get("pmcid", "").strip(), r.get("sheet", "").strip()) == key]
    if len(hit) != 1:
        raise SystemExit("reconcile: %d rows for %s -- expected exactly one"
                         % (len(hit), key))
    r = hit[0]
    r["notes"] = ("CORRECTED %s (round 2): %s. Round 1 was %s: %s"
                  % (today, reason, r["verdict_human"], r.get("notes") or ""))
    r["verdict_human"] = verdict
    return rows


def disagreements(rows):
    """-> answered rows where a settled agent verdict and the person differ."""
    return [r for r in rows
            if (r.get("agent_verdict") or "") in ("TRUE", "FALSE")
            and (r.get("verdict_human") or "") in ("TRUE", "FALSE")
            and r["agent_verdict"] != r["verdict_human"]]


def reconcile(desk, adjudications, answers, stdin=None, stdout=None):
    """After the answers are in, show the person ONLY the disagreements, now
    with the agent's verdict and note, and let them keep or change theirs.

    Never during a measurement: a person who sees the agent before answering
    is no longer an independent reader (V18/V23). Afterwards it is the whole
    point -- on V18 it recovered a real series the person had discarded."""
    stream, stdin = stdout or sys.stdout, stdin or sys.stdin

    def p(s):
        stream.write(s)
        stream.flush()

    with open(answers, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        fields, rows = rd.fieldnames, list(rd)
    by_key = {(it["pmcid"], it["sheet"]): it for it in desk["items"]}
    todo = disagreements(rows)
    p("  %d disagreement(s) between you and the adjudicator in %s\n"
      % (len(todo), os.path.basename(answers)))
    changed = 0
    for i, r in enumerate(todo, 1):
        key = (r["pmcid"].strip(), r["sheet"].strip())
        it = by_key.get(key)
        if it:
            _present(dict(it, audit=False), i, len(todo), p)
        v, note = adjudications.get(key, (r["agent_verdict"], ""))
        p("\n  YOU SAID: %s   %s\n" % (r["verdict_human"], r.get("notes") or ""))
        p("  THE ADJUDICATOR SAID: %s   %s\n" % (v, note))
        p("  keep yours or change it? [K/C]: ")
        ans = (stdin.readline() or "K").strip().upper()
        if ans.startswith("C"):
            p("  why, in one line (it goes in the record): ")
            why = (stdin.readline() or "").strip() or "changed on re-reading"
            correct(rows, key, "FALSE" if r["verdict_human"] == "TRUE" else "TRUE", why)
            changed += 1
    if changed:
        tmp = answers + ".part"
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, answers)
    p("\n  %d changed, %d kept. Round 1 stays in each changed note.\n"
      % (changed, len(todo) - changed))
    return changed


CHECK_COLS = ("subjects_ok", "times_ok", "arms_ok")
YES_NO = {"Y": "yes", "YES": "yes", "SI": "yes",
          "N": "no", "NO": "no", "": ""}


def _block_ids(key):
    """`b3` / `b3,b5` / `b6-b8` -> {3} / {3, 5} / {6, 7, 8}."""
    out = set()
    for part in key.split(","):
        m = re.match(r"\s*b(\d+)\s*(?:-\s*b?(\d+))?\s*$", part)
        if m:
            lo = int(m.group(1))
            out.update(range(lo, int(m.group(2) or lo) + 1))
    return out


def kept_subjects(subjects, arms):
    """-> (total over blocks NOT marked `DROP`, [dropped ids]), or None when
    `subjects` is a bare total (V25's format).

    V25 P3: on 8 of 50 sheets the agent set a block aside (weights, survival)
    and still typed a total that counted it. So the agent writes subjects PER
    BLOCK (`b1:8;b2:0`) and marks `bN=DROP: reason`; the sum is done here."""
    per = {}
    for part in (subjects or "").split(";"):
        m = re.match(r"\s*b(\d+)\s*:\s*(\d+)\s*$", part)
        if m:
            per[int(m.group(1))] = int(m.group(2))
    if not per:
        return None
    dropped = set()
    for part in (arms or "").split(";"):
        key, _, arm = part.partition("=")
        if arm.strip().upper().startswith("DROP"):
            dropped |= _block_ids(key)
    return (sum(n for b, n in per.items() if b not in dropped),
            sorted(dropped & set(per)))


def _print_extraction(p, r):
    p("\n  THE AGENT'S EXTRACTION\n")
    p("    blocks:    %s\n    subjects:  %s\n" % (r["blocks"], r["subjects"]))
    kept = kept_subjects(r.get("subjects"), r.get("arms"))
    if kept:
        p("    -> %d subject(s) in the blocks kept%s\n"
          % (kept[0], " (dropped: %s)" % ", ".join("b%d" % b for b in kept[1])
             if kept[1] else ""))
    for g in (r.get("time_grid") or "").split(";"):
        p("    times:     %s\n" % g)
    for a in (r.get("arms") or "").split(";"):
        p("    arm:       %s\n" % a)
    for f in ("model", "host", "role", "readout"):
        if r.get(f):
            p("    %-10s %s\n" % (f + ":", r[f]))
    if r.get("legend"):
        p("    legend:    %s\n" % r["legend"])
    if r.get("note"):
        p("    note:      %s\n" % r["note"])
    p("\n")


def _ask_check(r, stdin, p):
    """Fill r's open CHECK_COLS and append a rater note. -> False on q/EOF."""
    for c in CHECK_COLS:
        if (r.get(c) or "").strip():
            continue
        while True:
            p("  %s [y/n]: " % c)
            line = stdin.readline()
            if not line or line.strip().lower() == "q":
                return False
            v = YES_NO.get(line.strip().upper())
            if v is not None:
                break
            p("  y, n, ENTER to leave blank, q to stop\n")
        r[c] = v
    p("  note (ENTER for none): ")
    extra = (stdin.readline() or "").strip()
    if extra:
        r["note"] = ("%s | rater: %s" % (r["note"], extra)
                     if r.get("note") else "rater: " + extra)
    return True


CHECK_FIELDS = ["pmcid", "sheet", "blocks", "subjects", "time_grid", "arms",
                "legend", "subjects_ok", "times_ok", "arms_ok", "note"]


def _append_check(path, row):
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CHECK_FIELDS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def read_extractions(path):
    """-> {(pmcid, sheet): row} from pmcid,sheet,blocks,subjects,time_grid,arms,note."""
    return {((r.get("pmcid") or "").strip(), (r.get("sheet") or "").strip()): r
            for r in _rows(path)} if path else {}


def check(desk, path, timeline=None, max_rows=60, max_cols=30,
          stdin=None, stdout=None, now=None):
    """The extraction check (V25 step 5): walk every row of `path` that is
    not fully answered, show the agent's summary beside the sheet and the
    legend, and ask yes/no for subjects, times and arms.

    The agent's summary IS shown: this is not a blind verdict but a check of
    a written claim against the sheet. The file is rewritten after every row,
    so Ctrl-C or `q` loses nothing, and a re-run resumes where it stopped.
    With `timeline`, the session's wall clock is appended to it (P4)."""
    stream, stdin = stdout or sys.stdout, stdin or sys.stdin
    now = now or (lambda: datetime.datetime.now(datetime.timezone.utc)
                  .strftime("%Y-%m-%dT%H:%M:%SZ"))

    def p(s):
        stream.write(s)
        stream.flush()

    def is_open(r):
        return not all((r.get(c) or "").strip() for c in CHECK_COLS)

    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        fields, rows = rd.fieldnames, list(rd)
    by_key = {(it["pmcid"].strip(), it["sheet"].strip()): it
              for it in desk["items"]}
    todo = [r for r in rows if is_open(r)]
    p("  %d of %d row(s) still to check in %s. y / n per column, ENTER leaves"
      " it blank,\n  q stops (everything answered so far is saved).\n"
      % (len(todo), len(rows), os.path.basename(path)))
    start, done = now(), 0
    for i, r in enumerate(todo, 1):
        it = by_key.get((r["pmcid"].strip(), r["sheet"].strip()))
        b = it["bundle"] if it else {}
        p("\n" + "=" * 74 + "\n")
        p("  [%d of %d]  %s   %s\n" % (i, len(todo), r["pmcid"], r["sheet"]))
        if it:
            member = it["row"].get("file") or it["row"].get("member")
            try:                                  # cache only, like the desk
                _, sh = sheet_mod.load(r["pmcid"], r["sheet"].strip(), member,
                                       fetch=False)
                for ln in sheet_mod.render(sh, max_rows, max_cols):
                    p("  %s\n" % ln)
            except sheet_mod.SheetWall as w:
                p("  WALL -- not an empty sheet: %s\n" % w)
        else:
            p("  (not on the desk: `unpool sheet %s --sheet ...` to read it)\n"
              % r["pmcid"])
        if b.get("legend"):
            p("\n  LEGEND\n    %s\n" % b["legend"][:1500])
        else:
            p("\n  LEGEND: not located -- `unpool paper %s --sheet \"%s\"`\n"
              % (r["pmcid"], r["sheet"].strip()))
        _print_extraction(p, r)
        stop = not _ask_check(r, stdin, p)
        tmp = path + ".part"            # rewritten now: Ctrl-C loses nothing
        with open(tmp, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)
        if stop:
            break
        done += 1
    p("\n  %d row(s) checked this session, %d still open -> %s\n"
      % (done, sum(map(is_open, rows)), path))
    if timeline and done:
        new = not os.path.exists(timeline) or os.path.getsize(timeline) == 0
        with open(timeline, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if new:
                w.writerow(["phase", "start_iso", "end_iso", "note"])
            w.writerow(["extraction_check", start, now(),
                        "rater session, %d row(s), desk check" % done])
    return done


def _append(path, rows):
    exists = os.path.exists(path) and os.path.getsize(path) > 0
    fields = FIELDS
    if exists:                  # resume a file in ITS columns, never shifted
        with open(path, newline="", encoding="utf-8-sig") as fh:
            fields = next(csv.reader(fh))
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        if not exists:
            w.writeheader()
        w.writerows(rows)


# --------------------------------------------------------------- selftest
def selftest():
    """The three things that break silently if this file is edited wrong."""
    import io
    import tempfile

    desk = {"items": [
        {"pmcid": "PMC1", "sheet": "Fig 1a", "evidence_at": "L2",
         "row": {"pmcid": "PMC1", "sheet": "Fig 1a", "n": "6", "title": "t1"},
         "bundle": {"legend": "tumour volumes per mouse", "methods": [],
                    "claimed_n": [], "walls": []}},
        {"pmcid": "PMC2", "sheet": "Fig 2b", "evidence_at": "L1",
         "row": {"pmcid": "PMC2", "sheet": "Fig 2b", "n": "9", "title": "t2"},
         "bundle": {"legend": None, "methods": [], "claimed_n": [],
                    "walls": ["no full text for PMC2"]}},
    ] + [{"pmcid": "PMC%d" % i, "sheet": "s", "evidence_at": "L0",
          "row": {"pmcid": "PMC%d" % i, "sheet": "s", "n": "4", "title": ""},
          "bundle": {"legend": None, "methods": [], "claimed_n": [],
                     "walls": []}} for i in range(3, 23)]}
    adj = {("PMC1", "Fig 1a"): ("TRUE", ""), ("PMC2", "Fig 2b"): ("FALSE", "")}

    # 1. the settled ones leave the pile, and the audit quota puts some back
    pile = plan(desk, adj, seed=7)
    assert len(pile) == 22, len(pile)                  # 20 open + 2 audit
    assert sum(1 for it in pile if it["audit"]) == 2   # round(20 * 0.10)
    assert [it["pmcid"] for it in plan(desk, adj, seed=7)] == \
           [it["pmcid"] for it in pile], "the audit draw is not reproducible"

    # rate 1.0 is the measurement mode: every settled item is asked as well
    full = plan(desk, adj, seed=7, rate=1.0)
    assert sum(1 for it in full if it["audit"]) == len(adj), full
    assert len(full) == len(desk["items"]), len(full)

    # 2. THE FIREWALL: the agent's verdict never reaches the person answering
    buf = io.StringIO()
    for i, it in enumerate(pile, 1):
        _present(it, i, len(pile), buf.write)
    shown = buf.getvalue()
    assert "agent" not in shown.lower(), "the adjudicator's verdict leaked"
    assert "audit" not in shown.lower(), "audit membership leaked"
    assert "WALL -- not a result" in shown, "a wall was absorbed"

    # 3. answers land, SKIP writes nothing, and a second pass resumes
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "x.csv")
        answers = io.StringIO("T\n\nF\nbad sheet\n" + "S\n\n" * 40)
        _, new = queue(desk, adj, "h", "t", seed=7, out=out,
                       stdin=answers, stdout=io.StringIO())
        assert len(new) == 2, len(new)
        assert new[0]["verdict_human"] == "TRUE"
        assert new[1]["verdict_human"] == "FALSE" and new[1]["notes"] == "bad sheet"
        assert {r["settled_at"] for r in new} <= {"L5", "L0", "L1", "L2", "L3"}
        again = _answered(out)
        assert len(again) == 2, again
        _, second = queue(desk, adj, "h", "t", seed=7, out=out,
                          stdin=io.StringIO("T\n\n"), stdout=io.StringIO())
        assert (second[0]["pmcid"], second[0]["sheet"]) not in again

    # 4. V26: a fixed audit, and a split that leaves the audit draw untouched
    assert sum(1 for it in plan(desk, adj, 7, audit_n=1) if it["audit"]) == 1
    sp = plan(desk, adj, seed=7, split=True)
    assert [it["pmcid"] for it in sp] == [it["pmcid"] for it in pile]
    rest = [it for it in sp if not it["audit"]]
    assert sum(it["shown"] for it in rest) == (len(rest) + 1) // 2

    # 5. V26 A-P1, THE SENTINEL: nothing the agent wrote reaches stdout before
    # the verdict is on disk -- and afterwards it does, so the test is not vacuous
    two = {"items": desk["items"][:2]}
    adj2 = {("PMC1", "Fig 1a"): ("TRUE", "SENTINEL"),
            ("PMC2", "Fig 2b"): ("FALSE", "SENTINEL")}
    ex = {("PMC1", "Fig 1a"): {"pmcid": "PMC1", "sheet": "Fig 1a", "blocks": "1",
                               "subjects": "6", "time_grid": "b1:0,3",
                               "arms": "b1=SENTINEL", "note": "SENTINEL"}}
    for verdict in ("T", "F"):
        with tempfile.TemporaryDirectory() as d:
            out, buf = os.path.join(d, "a.csv"), io.StringIO()

            class Snap(io.StringIO):
                before = None

                def readline(self):
                    if Snap.before is None:
                        Snap.before = buf.getvalue()
                        assert not os.path.exists(out), "answer written early"
                    return super().readline()
            _, new = queue(two, adj2, "h", "t", seed=7, out=out, review=True,
                           audit_n=0, split=True, extractions=ex, stdout=buf,
                           stdin=Snap(verdict + "\n\ny\ny\nn\n\n"))
            assert "SENTINEL" not in Snap.before, "agent text before the answer"
            ckp = os.path.join(d, "a.check.csv")
            assert new[0]["shown"] in ("yes", "no") and new[0]["answered_at"]
            if verdict == "T":
                assert "SENTINEL" in buf.getvalue(), "the check never ran"
                got = list(_rows(ckp))[0]
                assert [got[c] for c in CHECK_COLS] == ["yes", "yes", "no"], got
            else:
                assert "SENTINEL" not in buf.getvalue()
                assert not os.path.exists(ckp)

    # 6. V26 part C: the subject total skips DROP blocks, ranges and lists too
    assert kept_subjects("b1:8;b2:5;b3:8;b4:3;b5:3",
                         "b1=PBS;b2=DROP: weights;b3=aPD-1;b4-b5=DROP: in vitro") \
        == (16, [2, 4, 5])
    assert kept_subjects("b1:4;b3:4", "b1,b3=DROP: survival") == (0, [1, 3])
    assert kept_subjects("62", "b1=x") is None          # V25's bare total

    # check: answers land in the file, a note is appended, q stops and keeps
    with tempfile.TemporaryDirectory() as d:
        ck, tl = os.path.join(d, "c.csv"), os.path.join(d, "t.csv")
        with open(ck, "w", newline="", encoding="utf-8") as fh:
            fh.write("pmcid,sheet,blocks,subjects,time_grid,arms,"
                     "subjects_ok,times_ok,arms_ok,note\n"
                     "P1,s,1,8,b1:0,b1=x,,,,agent\nP2,t,1,6,b1:0,b1=y,,,,\n")
        n = check({"items": []}, ck, tl, stdin=io.StringIO("y\nn\nsi\nok\nq\n"),
                  stdout=io.StringIO(), now=lambda: "T")
        got = list(_rows(ck))
        assert n == 1, n
        assert [got[0][c] for c in CHECK_COLS] == ["yes", "no", "yes"], got[0]
        assert got[0]["note"] == "agent | rater: ok", got[0]["note"]
        assert not got[1]["subjects_ok"], got[1]
        assert list(_rows(tl))[0]["phase"] == "extraction_check"

    print("selftest OK")


# -------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="climb the ladder over a worklist")
    b.add_argument("worklist")
    b.add_argument("-o", "--out", default=None)
    b.add_argument("--budget", type=int, default=None,
                   help="how many candidates to work, NOT a target to reach")

    q = sub.add_parser("queue", help="work the desk and write the verdicts")
    q.add_argument("desk")
    q.add_argument("--adjudications", default=None,
                   help="csv: pmcid,sheet,verdict[,note] from the adjudicator")
    q.add_argument("--handle", required=True)
    q.add_argument("--tag", required=True)
    q.add_argument("--seed", type=int, required=True,
                   help="fixes the audit draw BEFORE any answer is typed")
    q.add_argument("--audit-rate", type=float, default=AUDIT_RATE)
    q.add_argument("-o", "--out", default=None)
    q.add_argument("--review", action="store_true",
                   help="second-reader mode: every agent-TRUE comes to you, "
                        "plus an audit of the agent-FALSE at --audit-rate")
    q.add_argument("--audit-n", type=int, default=None,
                   help="a FIXED number of audit items instead of a rate")
    q.add_argument("--split", action="store_true",
                   help="V26: half the items, seeded, show extract's blocks "
                        "before the answer")
    q.add_argument("--extractions", default=None,
                   help="csv: the agent's extraction summaries; after a TRUE "
                        "they are shown and checked -> <out>.check.csv")

    rc = sub.add_parser("reconcile", help="after answering: re-decide only "
                        "where you and the adjudicator disagreed")
    rc.add_argument("desk")
    rc.add_argument("--adjudications", required=True)
    rc.add_argument("answers", help="the csv queue wrote your answers to")

    ck = sub.add_parser("check", help="the extraction check: yes/no on the "
                        "agent's subjects, times and arms, sheet beside it")
    ck.add_argument("desk")
    ck.add_argument("check_csv", help="pmcid,sheet,...,subjects_ok,times_ok,arms_ok,note")
    ck.add_argument("--timeline", default=None,
                    help="append this session's wall clock here (P4)")
    ck.add_argument("--rows", type=int, default=60, help="sheet rows, 0 = all")
    ck.add_argument("--cols", type=int, default=30, help="sheet columns, 0 = all")

    sub.add_parser("selftest", help="run the assertions and exit")
    a = ap.parse_args(argv)

    if a.cmd == "selftest":
        selftest()
        return 0
    if a.cmd == "check":
        with open(a.desk, encoding="utf-8") as fh:
            check(json.load(fh), a.check_csv, a.timeline, a.rows, a.cols)
        return 0
    if a.cmd == "build":
        build(a.worklist, a.out, a.budget)
        return 0

    with open(a.desk, encoding="utf-8") as fh:
        desk = json.load(fh)
    if a.cmd == "reconcile":
        reconcile(desk, read_adjudications(a.adjudications), a.answers)
        return 0
    desk["audit_seed"] = a.seed
    _write_json(a.desk, desk)
    queue(desk, read_adjudications(a.adjudications), a.handle, a.tag,
          a.seed, a.audit_rate, a.out, review=a.review, audit_n=a.audit_n,
          split=a.split, extractions=read_extractions(a.extractions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
