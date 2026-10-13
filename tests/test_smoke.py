"""The offline smoke test CI runs on every push: no network, no fixture cache,
no publisher bytes -- synthetic sheets built here, so nothing is redistributed.

It is NOT the gate. `test_recall.py` is, and it needs `fixtures/fetch.py`
first. This only catches the failures that need no real data to show: the
package does not import, a parser is missing (which makes every spreadsheet
"no table found", silently -- protocol rule 10), the wide path stops accepting
a plain per-animal grid, or AGG stops rejecting group means.

The negative is checked the only way that claim can be (V11): with AGG
neutered, the same sheet must be ACCEPTED, or the test is not testing AGG.

Usage: python tests/test_smoke.py      Exits 0 on pass.
"""
import io
import os
import random
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from unpool import scan as S  # noqa: E402
from unpool import __main__ as cli  # noqa: E402

DAYS = [0, 3, 7, 10, 14, 17]


def per_animal_csv():
    rnd = random.Random(1)
    out = "mouse," + ",".join("day %d" % d for d in DAYS) + "\n"
    for a in range(1, 9):
        v = 50 + rnd.random() * 20
        out += "M%d," % a + ",".join(
            "%.1f" % (v * (1.25 + rnd.random() * 0.1) ** i)
            for i in range(len(DAYS))) + "\n"
    return out


def group_means_csv():
    # markers in ROW LABELS, where AGG reads -- a header-row `Mean` column
    # never reaches AGG at all (V11)
    out = "group," + ",".join("day %d" % d for d in DAYS) + "\n"
    for arm, g in [("Control", 1.3), ("Treated", 1.15),
                   ("Combo", 1.1), ("Vehicle", 1.28)]:
        for stat, k in [("mean", 100), ("sem", 9)]:
            out += "%s %s," % (arm, stat) + ",".join(
                "%.1f" % (k * g ** i) for i in range(len(DAYS))) + "\n"
    return out


def verdicts(name, blob):
    return [S.judge_any(rows) for _, rows in S.sheets_from(name, blob)]


def as_xlsx(text):
    import openpyxl
    wb = openpyxl.Workbook()
    for line in text.strip().splitlines():
        wb.active.append([float(c) if re.fullmatch(r"[\d.]+", c) else c
                          for c in line.split(",")])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main():
    assert not S.preflight(), "spreadsheet parsers missing: %s" % S.preflight()

    v = verdicts("pos.csv", per_animal_csv().encode())
    assert v and v[0] and v[0][:3] == ("wide", 8, 6), v
    v = verdicts("pos.xlsx", as_xlsx(per_animal_csv()))
    assert v and v[0] and v[0][:3] == ("wide", 8, 6), "xlsx path: %r" % (v,)

    neg = group_means_csv().encode()
    assert verdicts("neg.csv", neg) == [None], "AGG let group means through"
    real_agg, S.AGG = S.AGG, re.compile(r"(?!x)x")
    try:
        assert verdicts("neg.csv", neg)[0], \
            "negative is rejected without AGG -- it no longer tests AGG"
    finally:
        S.AGG = real_agg

    assert cli.main([]) == 2

    # mine's re-export registry must never resolve to the verified-data
    # registry.csv: same default name once, and every real campaign crashed
    from unpool import mine
    rows = mine.load_registry()
    assert not rows or "a2_enumerated" in rows[0], mine.REGISTRY

    # V28: a supplementary legend from the SI PDF's text -- the caption, not the
    # contents-page line or a mention, and its group sizes
    from unpool import paper
    si = ("Contents\nSupplementary Fig. 3. Tumour growth .... 4\n"
          "As shown in Supplementary Fig. 3, mice responded.\n"
          "Supplementary Fig. 3. Tumour growth of MC38 under aPD-1 (n = 6 mice per group).\n"
          "b, Body weight.\nSupplementary Figure 4: Survival.\n")
    paper.si_text, real_si = (lambda pmcid: si), paper.si_text
    leg = paper.si_legend("PMC0", "Supplementary Fig. 3b")
    paper.si_text = real_si
    assert leg and "n = 6" in leg[1] and "Survival" not in leg[1], leg
    assert paper.si_legend("PMC0", "Fig. 3b") is None   # main figures stay XML-only

    # V27: GraphPad statistics are not subjects; an arm called NSG still is
    from unpool.extract import _STATS_ROW
    assert all(_STATS_ROW.match(t) for t in ("ns", "**", "F (DFn, DFd)", "P value"))
    assert not any(_STATS_ROW.match(t) for t in ("NSG mice", "Summary of tumours", "PBS"))

    # the legend's group sizes, terse as legends write them, with their sentence
    from unpool import paper
    got = paper.legend_n("b, Tumour volume (n = 5 mice per group). "
                         "c, Body weight; n = 8-9. d, In vitro, n=3 experiments.")
    assert [k for k, _ in got] == ["n = 5", "n = 8-9", "n=3"], got
    assert got[1][1].startswith("c, Body weight"), got

    # `unpool extract`: two arms on one shared day axis, a label that repeats
    # inside every arm, a summary row, a blank separator -- and data rows of
    # rising volumes that must NOT be read as an axis
    from unpool import extract
    rows = [["arm", "mouse", "Day 0", "Day 4", "Day 7", "Day 11"],
            ["Vehicle", "Mouse #1", 50.5, 121.3, 298.7, 394.4],
            [None, "Mouse #2", 48.1, 110.0, 250.2, 380.9],
            [None, "Mouse #3", 52.0, 130.4, 260.8, 399.1],
            ["N", None, 3, 3, 3, 3],
            [None] * 6,
            ["Drug", "Mouse #1", 49.0, 80.2, 120.5, 160.3],
            [None, "Mouse #2", 51.3, 85.0, 118.9, 170.2]]
    blocks = extract.wide_blocks(rows)
    assert [len(b["subjects"]) for b in blocks] == [3, 2], blocks
    assert all(b["axis"] == [0, 4, 7, 11] for b in blocks), blocks
    labs = [lab for b in blocks for lab, _ in b["subjects"]]
    assert labs[1] == "Vehicle | Mouse #2" and labs[3] == "Drug | Mouse #1", labs
    # a header split over two rows: `Day 0` sits one row below the rest
    split = [["", "Day 4", "Day 7", "Day 11", "Day 14"],
             ["Day 0", None, None, None, None],
             [10.5, 20.5, 30.5, 40.5, 50.5],
             [11.5, 21.5, 31.5, 41.5, 51.5]]
    blocks = extract.wide_blocks(split)
    assert len(blocks) == 1 and blocks[0]["axis"] == [0, 4, 7, 11, 14], blocks
    assert len(blocks[0]["subjects"]) == 2, blocks
    # V27/V29: GraphPad -- arms side by side with no blank between them, the
    # arm named once (merged cell); an `Avrg` row and a pure statistics row are
    # not animals, but a mouse beside a `P value` cell still is
    gp = [["arm", "x", "Day 0", "Day 3", "Day 7", "Day 10"],
          ["PBS", None, 50, 90, 150, 220],
          [None, None, 52, 95, 160, 240],
          [None, "Avrg", 51.0, 92.5, 155.0, 230.5],
          ["aPD-1", None, 49, 70, 90, 110],
          ["aPD-1", "P value", 48, 72, 95, 120],   # its own group name too
          ["ns", None, 1, 1, 1, 1]]
    blocks = extract.wide_blocks(gp)
    assert [len(b["subjects"]) for b in blocks] == [2, 2], blocks

    # desk review mode: every agent-TRUE reaches the person, the agent-FALSE
    # are audited at the rate OF THE FALSE; reconcile keeps round 1
    from unpool import desk
    items = [{"pmcid": "P%d" % i, "sheet": "s"} for i in range(9)]
    adj = {("P0", "s"): ("TRUE", ""), ("P1", "s"): ("TRUE", ""), ("P2", "s"): ("TRUE", ""),
           ("P3", "s"): ("FALSE", ""), ("P4", "s"): ("FALSE", ""), ("P5", "s"): ("FALSE", ""),
           ("P6", "s"): ("FALSE", ""), ("P7", "s"): ("UNRESOLVED", "")}
    pile = desk.plan({"items": items}, adj, 1, 0.25, review=True)
    got = {x["pmcid"] for x in pile}
    assert {"P0", "P1", "P2", "P7", "P8"} <= got and len(got) == 6, got
    assert sum(x["audit"] for x in pile) == 1, pile
    normal = {x["pmcid"] for x in desk.plan({"items": items}, adj, 1, 0.25)}
    assert len(normal & {"P0", "P1", "P2"}) <= 1, normal   # normal mode: agent-TRUE stay screened
    rows = [{"pmcid": "P9", "sheet": "s", "verdict_human": "FALSE",
             "notes": "an arm read as the readout", "agent_verdict": "TRUE"}]
    assert len(desk.disagreements(rows)) == 1
    desk.correct(rows, ("P9", "s"), "TRUE", "the sheet title", today="2000-01-01")
    assert rows[0]["verdict_human"] == "TRUE", rows
    assert rows[0]["notes"].endswith("Round 1 was FALSE: an arm read as the readout"), rows
    assert desk.disagreements(rows) == []

    # `unpool sheet` announces every cut instead of silently truncating
    from unpool import sheet
    grid = [[r * 10 + c for c in range(5)] for r in range(4)]
    out = sheet.render(grid, max_rows=2, max_cols=3)
    assert len(out) == 4 and "2 more row" in out[2] and "2 more column" in out[3], out
    assert len(sheet.render(grid, 0, 0)) == 4

    # `unpool export`: arms by block, DROP/MIXED left out, and a sheet that
    # extract now cuts differently is refused, never relabelled (V31)
    from unpool import export as xp
    assert xp.arm_map("b1=Veh;b2-b3=DROP: bw;b4=MIXED: pooled;b5,b6=Drug") == {
        1: "Veh", 2: None, 3: None, 4: None, 5: "Drug", 6: "Drug"}
    assert xp.arm_map("b1=UNRESOLVED: no label") == {1: None}
    assert xp.block_map("volume (mm3)") == {0: "volume (mm3)"}
    assert xp.block_map("YUMM5.2, D/T = dabrafenib") == {0: "YUMM5.2, D/T = dabrafenib"}
    assert xp.block_map("b1-b2=volume;b3=bli") == {1: "volume", 2: "volume", 3: "bli"}
    assert xp.per_block("b1:2;b2:1") == {1: 2, 2: 1} and xp.per_block("12") == {}
    blocks = [{"subjects": [("m1", [(0, 1.0), (7, 2.0)]), ("m2", [(0, 1.5)])]},
              {"subjects": [("w1", [(0, 20.0)])]}]
    real = xp.ex.extract
    xp.ex.extract = lambda *a, **k: ("f.xlsx", "sha", "wide", blocks)
    try:
        row = {"pmcid": "P1", "sheet": "Fig 1", "subjects": "b1:2;b2:1",
               "arms": "b1=Vehicle;b2=DROP: body weight", "readout": "volume (mm3)",
               "role": "b1=control;b2=treated", "model": "MC38"}
        out, why = xp.rows_for(row, set(), meta=lambda p: {"doi": "10.1/x"})
        assert why is None and len(out) == 3, (why, out)
        assert {r["arm"] for r in out} == {"Vehicle"} and out[0]["doi"] == "10.1/x"
        assert {(r["state"], r["verified_by"]) for r in out} == {("screened", "")}
        ok = dict(row, subjects_ok="yes", times_ok="yes", arms_ok="yes")
        out, _ = xp.rows_for(ok, {("P1", "fig 1"): "contributed/ana/v40.csv"},
                             meta=lambda p: {})
        assert {(r["state"], r["verified_by"]) for r in out} == {("verified", "ana")}
        out, _ = xp.rows_for(dict(ok, checked_by="Ana (blind)"),
                             {("P1", "fig 1"): "contributed/ana/v40.csv"}, meta=lambda p: {})
        assert {r["verified_by"] for r in out} == {"Ana (blind)"}
        assert {(r["readout"], r["role"], r["model"], r["host"]) for r in out} == {
            ("volume (mm3)", "control", "MC38", "")}
        row["subjects"] = "b1:3;b2:1"
        out, why = xp.rows_for(row, set(), meta=lambda p: {})
        assert out == [] and "now cuts" in why, why
    finally:
        xp.ex.extract = real

    # The skill's frontmatter once failed to parse (an unquoted `: ` in the
    # description) and every harness loaded it with no name or description.
    skill = os.path.join(os.path.dirname(__file__), "..", "skills", "unpool", "SKILL.md")
    head = open(skill, encoding="utf-8").read().split("\n---\n", 1)[0].splitlines()
    fm = dict(l.split(": ", 1) for l in head[1:] if ": " in l)
    assert head[0] == "---" and fm.get("name") == "unpool", head[:2]
    d = fm.get("description", "")
    assert d.startswith('"') or ": " not in d, "unquoted ': ' in the skill description"
    print("smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
