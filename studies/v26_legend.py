"""V26 amendment 4: legend-anchored triage. The comparison is CODE, not the
agent, so CONCORDANT / ANOMALOUS does not rest on the agent's judgement.

    python studies/v26_legend.py            # -> runs/v26_legend.csv, runs/v26_review.csv

For every agent-TRUE sheet: re-run `extract` (cache only, default layout),
sum the blocks the agent did not mark DROP, and flag ANOMALOUS when
  (a) the sum differs from the expected total the agent wrote in `legend`
      (`n=5 x 4 + n=6 x 2 = 32`), or the terms do not add up to it;
  (b) an n the agent cites is not among the `n = ...` the legend prints;
  (c) the legend prints no n, or the agent wrote `none stated`;
  (d) `extract` finds no block;
  (e) a block is marked MIXED.
Review pile: every ANOMALOUS row + 10 seeded CONCORDANT rows, unlabelled,
WITHOUT the `legend` column, in seeded order.
"""
import csv
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unpool import extract, paper, sheet as sheet_mod  # noqa: E402
from unpool.desk import CHECK_FIELDS, kept_subjects     # noqa: E402

SEED, AUDIT = 20261005, 10
TERM = re.compile(r"n\s*=\s*(\d+)\s*[x×*]\s*(\d+)", re.I)


def parse_expected(text):
    """`n=5 x 4 + n=6 x 2 = 32` -> ([(5, 4), (6, 2)], 32); None if unparseable."""
    t = (text or "").strip()
    m = re.search(r"=\s*(\d+)\s*$", t)
    terms = [(int(a), int(b)) for a, b in TERM.findall(t)]
    if not m or not terms:
        return None
    return terms, int(m.group(1))


def legend_ns(caption):
    """Every integer inside the legend's `n = ...` statements: `n = 8-9` -> {8, 9}."""
    return {int(x) for k, _ in paper.legend_n(caption) for x in re.findall(r"\d+", k)}


def judge(row, blocks, caption):
    """-> (status, [reasons], kept_total, expected_total)."""
    why = []
    per = ";".join("b%d:%d" % (i, len(b["subjects"])) for i, b in enumerate(blocks, 1))
    kept = kept_subjects(per, row.get("arms")) if blocks else None
    kept_n = kept[0] if kept else 0
    if not blocks:
        why.append("d: extract finds no block")
    if "MIXED" in (row.get("arms") or "").upper():
        why.append("e: a block is MIXED")
    ns = legend_ns(caption)
    exp = parse_expected(row.get("legend"))
    expected = None
    if not ns or "none stated" in (row.get("legend") or "").lower():
        why.append("c: the legend states no n")
    elif exp is None:
        why.append("a: no expected total written")
    else:
        terms, expected = exp
        if sum(k * a for k, a in terms) != expected:
            why.append("a: the terms do not add up to %d" % expected)
        if kept_n != expected:
            why.append("a: kept blocks hold %d, legend expects %d" % (kept_n, expected))
        bad = sorted({k for k, _ in terms} - ns)
        if bad:
            why.append("b: n=%s not in the legend" % ",".join(map(str, bad)))
    return ("ANOMALOUS" if why else "CONCORDANT"), why, kept_n, expected


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main():
    key = lambda r: (r["pmcid"].strip(), r["sheet"].strip())
    true = {key(r) for r in _rows("runs/v26_adjudications.csv")
            if r["verdict"].strip().upper() == "TRUE"}
    member = {key(r): r.get("file") or r.get("member") for r in _rows("runs/v26_pile_source.csv")}
    ext = [r for r in _rows("runs/v26_extractions.csv") if key(r) in true]
    out = []
    for r in ext:
        pm, sh = key(r)
        try:
            _, _, _, blocks = extract.extract(pm, sh, member.get((pm, sh)), fetch=False)
        except sheet_mod.SheetWall:
            blocks = []
        try:
            leg = paper.legend_for(paper.fulltext(pm), sh)
        except paper.PaperWall:
            leg = None
        status, why, kept, expected = judge(r, blocks, leg[1] if leg else "")
        out.append(dict(r, status=status, reasons=" | ".join(why),
                        kept_total=kept, expected_total=expected if expected is not None else ""))
    fields = ["pmcid", "sheet", "status", "reasons", "kept_total", "expected_total",
              "blocks", "subjects", "arms", "legend"]
    with open("runs/v26_legend.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)
    anom = [r for r in out if r["status"] == "ANOMALOUS"]
    conc = [r for r in out if r["status"] == "CONCORDANT"]
    rnd = random.Random(SEED)
    # Amendment 5: only the comparable anomalies (reason a/b, none of c/d/e)
    # need a person; c, d and e already name their cause mechanically.
    comparable = [r for r in anom if not re.search(r"(?:^| )[cde]:", r["reasons"])]
    pile = comparable + rnd.sample(conc, min(AUDIT, len(conc)))
    rnd.shuffle(pile)
    with open("runs/v26_review.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CHECK_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in pile:          # no legend, no note, no status: the audit stays blind
            w.writerow({k: ("" if k in ("legend", "note") else r.get(k, ""))
                        for k in CHECK_FIELDS})
    n = len(out)
    print("  agent-TRUE sheets: %d   CONCORDANT %d   ANOMALOUS %d" % (n, len(conc), len(anom)))
    for tag in "abcde":
        print("    %s: %d" % (tag, sum(1 for r in anom if (" " + r["reasons"]).count(" %s:" % tag))))
    print("  review pile: %d (%d comparable anomalous + %d audit) -> runs/v26_review.csv"
          % (len(pile), len(comparable), len(pile) - len(comparable)))


def _selftest():
    assert parse_expected("n=5 x 4 + n=6 x 2 = 32") == ([(5, 4), (6, 2)], 32)
    assert parse_expected("none stated") is None
    blk = lambda k: {"subjects": [("", [])] * k}
    cap = "b, Tumour volume (n = 5 mice per group). c, Body weight, n = 5."
    row = {"arms": "b1=PBS, aPD-1, combo, x;b2=DROP: weight", "legend": "n=5 x 4 = 20"}
    assert judge(row, [blk(20), blk(20)], cap)[:2] == ("CONCORDANT", [])
    st, why, kept, _ = judge(dict(row, arms="b1=PBS;b2=vehicle"), [blk(20), blk(20)], cap)
    assert st == "ANOMALOUS" and kept == 40 and why[0].startswith("a:"), why
    assert judge(dict(row, legend="n=6 x 4 = 24"), [blk(24)], cap)[1] == \
        ["b: n=6 not in the legend"]
    assert judge(row, [], cap)[1][0].startswith("d:")
    assert judge(row, [blk(20)], "no group sizes here.")[1] == ["c: the legend states no n"]


if __name__ == "__main__":
    _selftest()
    if sys.argv[1:] != ["selftest"]:
        main()
