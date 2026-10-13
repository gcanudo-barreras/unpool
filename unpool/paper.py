"""THE ARTICLE LAYER: the paper's own words, next to the sheet they describe.

`mine.py` and `scan.py` read supplementary BYTES and article METADATA, and
never the article. Every question step 4 of the protocol asks -- which model,
which arm is the control, how many animals does the paper CLAIM, what method,
what units -- is answered in the article, and until now the operator had to go
and find it by hand.

WHY THIS IS A READER AND NOT A FILTER
------------------------------------------------------------------------------
`judge()` decides on structure and never on wording (protocol rule 1). That is
not an accident to be corrected: a sheet titled "Tumor volume data" holding
medians is still medians. So nothing here feeds back into the accept decision.
This module produces EVIDENCE FOR A PERSON, in the paper's own words, with the
sentence and its location, so that a verdict can be justified rather than felt.

Measured before it was written (`docs/VALIDATION.md`, V17), over the 20 papers
V10 verified by hand:

  * a legend for the sheet's own figure panel was located for 16 of 20
  * among sheets whose legend said "tumour volume/growth", precision was
    4 of 7 = 57%, against the scanner's 35% on the same sample
  * AND IT COST RECALL: 4 of 7 true positives kept. It is therefore not a gate
    at any threshold, and is not offered as one.

The sharpest result was not a rate. `PMC7138317` `fig.6C` carries no unit, no
animal label and no day label -- V10 read the sheet, could not resolve it, and
scored it FALSE. Figure 6's legend says "tumor volumes at the indicated time
points (C) ... injected to the nude mice". The verdict was wrong, the
spreadsheet could never have said so, and one sentence of the paper settled it.

WHAT IT DOES NOT DO
------------------------------------------------------------------------------
It does not decide. It does not rank. It does not write a verdict. A legend
that says "tumour growth" on a sheet of western blot densitometry is a legend
about a different panel of the same figure, and that happens -- V17 measured it.
Read the sheet too.

Run:
    unpool paper PMC13534483
    unpool paper PMC13534483 --sheet "Supplementary Fig. 8b."
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from unpool import scan

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.environ.get("UNPOOL_PAPER_CACHE") or os.path.join(_HERE, "si_cache")
SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
FULLTEXT = "https://www.ebi.ac.uk/europepmc/webservices/rest/{}/fullTextXML"

# The method sentence a builder's docstring has to quote. These are the words a
# measurement is described with, not the words a result is described with.
METHOD = re.compile(
    r"caliper|calliper|vernier|tumou?r volume was|volumes? were (?:measured|"
    r"assessed|calculated|monitored)|length\s*[x×*]\s*width|width\s*\^?2"
    r"|\bL\s*[x×*]\s*W\b|bioluminescen|IVIS|photon flux|body weights? were"
    r"|euthani[sz]ed|sacrificed|humane endpoint|tumou?r burden was", re.I)

# "n = 8 mice per group", "(n = 8-9 mice/group)", "seven animals per arm".
CLAIM_N = re.compile(
    r"\bn\s*=\s*\d+(?:\s*[-–]\s*\d+)?\s*(?:mice|animals|rats|mouse|"
    r"per group|/group|per arm|mice/group|animals/group)"
    r"|\b\d+\s+(?:mice|animals|rats)\s+per\s+(?:group|arm|cage)", re.I)

SPECIES = re.compile(r"\b(?:NSG|NOD[- ]?SCID|BALB/?c|C57BL/6[JN]?|nude mice|"
                     r"athymic|nu/nu|CD-?1|FVB|129S|Wistar|Sprague[- ]Dawley)\b",
                     re.I)


class PaperWall(Exception):
    """A wall, not a result (protocol rule 10). Say what blocked you."""


# ---------------------------------------------------------------- fetching
def _get(url, timeout=60):
    req = urllib.request.Request(url, headers=scan.UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def metadata(pmcid):
    """-> dict with doi, title, journal, licence, open_access."""
    q = "%s?query=%s&resultType=core&format=json&pageSize=1" % (
        SEARCH, urllib.parse.quote("PMCID:%s" % pmcid))
    try:
        res = json.loads(_get(q).decode("utf-8"))["resultList"]["result"]
    except Exception as exc:
        raise PaperWall("Europe PMC search failed for %s: %s -- this is a wall, "
                        "not an absent paper." % (pmcid, exc))
    if not res:
        raise PaperWall("Europe PMC returned no record for %s." % pmcid)
    r = res[0]
    return {"pmcid": pmcid, "doi": r.get("doi", ""),
            "title": (r.get("title") or "").strip(),
            "journal": (r.get("journalInfo") or {}).get("journal", {}).get("title", ""),
            "year": (r.get("journalInfo") or {}).get("yearOfPublication", ""),
            "licence": r.get("license", ""),
            "open_access": r.get("isOpenAccess", "")}


def fulltext(pmcid, use_cache=True):
    """-> the article's JATS XML. Cached beside the supplementary bundles."""
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, "%s.fulltext.xml" % pmcid)
    if use_cache and os.path.exists(p) and os.path.getsize(p) > 500:
        return open(p, encoding="utf-8").read()
    try:
        x = _get(FULLTEXT.format(pmcid)).decode("utf-8")
    except Exception as exc:
        raise PaperWall(
            "no full text for %s (%s). Europe PMC serves full text only for "
            "the open-access subset; the abstract may exist while the body "
            "does not. NOT a finding about the paper's content." % (pmcid, exc))
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(x)
    return x


# ---------------------------------------------------------------- parsing
def _text(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()


def _sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", t) if s.strip()]


def figures(xml):
    """-> [(label, caption)] for every figure in the article."""
    out = []
    for m in re.finditer(r"<fig\b.*?</fig>", xml, re.S):
        blk = m.group(0)
        lab = re.search(r"<label>(.*?)</label>", blk, re.S)
        cap = re.search(r"<caption>(.*?)</caption>", blk, re.S)
        out.append((_text(lab.group(1)) if lab else "",
                    _text(cap.group(1)) if cap else ""))
    return out


def sheet_panel(sheet):
    """`Fig 4c` / `Extended Data Figure 3` / `Supplementary Fig. 8b.` -> key.

    -> (kind, number, panel) where kind is F / ED / S, or None when the sheet
    name carries no figure reference at all -- which is itself worth knowing,
    because a sheet called `Sheet1` cannot be cross-referenced this way.
    """
    s = (sheet or "").strip()
    if not s:
        return None
    ext = bool(re.search(r"extended|\bED\b|EDF", s, re.I))
    sup = bool(re.search(r"supp|\bS\d|Fig\.?\s*S", s, re.I))
    m = re.search(r"(\d+)\s*[._-]?\s*([a-z])?\b", s, re.I)
    if not m:
        return None
    return ("ED" if ext else "S" if sup else "F", m.group(1),
            (m.group(2) or "").lower())


def legend_for(xml, sheet):
    """-> (label, full_caption, panel_sentences) for the sheet's own figure.

    The WHOLE caption is returned, not a window around the panel letter. V17
    measured the cost of a window: every true positive that rule dropped was an
    extraction artifact rather than missing information, so this hands the
    reader everything and merely POINTS at the panel.
    """
    key = sheet_panel(sheet)
    if key is None:
        return None
    kind, num, panel = key
    for lab, cap in figures(xml):
        lm = re.search(r"(\d+)", lab or "")
        if not lm or lm.group(1) != num:
            continue
        is_ext = bool(re.search(r"extended|supplementary|^\s*S", lab or "", re.I))
        if (kind in ("ED", "S")) != is_ext:
            continue
        return (lab, cap, _panel_hits(cap, panel))
    return None


def _panel_hits(cap, panel):
    return [s for s in _sentences(cap) if panel and
            re.search(r"(?:^|[\s(,;])%s[\s),.:;]" % panel, s, re.I)]


# A caption, not a mention: `Supplementary Fig. 32.` / `Supplementary Figure 7:`
# at the start of a line of the SI PDF's text.
SI_CAPTION = re.compile(r"(?m)^[ \t]*Supplementary\s+Fig(?:ure|\.)?\s*S?(\d+)\s*[.:|]", re.I)
# Bundles also carry the referees' report, which quotes "Supplementary Figure
# 3" in comments, and the reporting summary: neither holds a legend (V28-P2).
NOT_SI = re.compile(r"Peer\s+Review\s+File|Reviewers?['’]?\s+comments|"
                    r"Reporting\s+Summary", re.I)


def si_text(pmcid):
    """-> the text of every PDF in the cached supplementary bundle (V28).
    Cached beside the bundle; publisher bytes, so never inside the repository."""
    cache = os.path.join(CACHE, "%s.si-v2.txt" % pmcid)   # v2: review files out
    if os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    try:
        from pypdf import PdfReader
    except ImportError:
        raise PaperWall("this legend is in the SI PDF, and reading it needs the "
                        "optional `pypdf` (`pip install -e .[pdf]`)")
    import io
    import logging
    logging.getLogger("pypdf").setLevel(logging.ERROR)   # malformed-xref chatter
    from unpool import sheet as sheet_mod
    try:
        zf = sheet_mod._zip(pmcid, fetch=False)
    except sheet_mod.SheetWall as w:
        raise PaperWall(str(w))
    parts = []
    for name in zf.namelist():
        if name.lower().endswith(".pdf"):
            try:
                pages = [p.extract_text() or "" for p in
                         PdfReader(io.BytesIO(zf.read(name))).pages]
            except Exception:           # one unreadable PDF is not the bundle
                continue
            if pages and NOT_SI.search(pages[0][:1500]):
                continue
            parts.append("\n".join(pages))
    # lone surrogates come out of some PDFs' fonts; atomic, so a failed write
    # never leaves a truncated cache that later reads as "no caption"
    text = "\n".join(parts).encode("utf-8", "replace").decode("utf-8")
    with open(cache + ".part", "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(cache + ".part", cache)
    return text


def si_legend(pmcid, sheet):
    """-> (label, caption, panel_sentences) from the SI PDF for a sheet naming a
    supplementary figure, or None. Of several captions with that number (a
    contents page lists them too) the longest is the legend."""
    key = sheet_panel(sheet)
    if not key or key[0] != "S" or os.environ.get("UNPOOL_NO_SI"):
        return None     # UNPOOL_NO_SI: the evidence as it was before V28 (V30)
    text = si_text(pmcid)
    caps = list(SI_CAPTION.finditer(text))
    best = None
    for i, m in enumerate(caps):
        if m.group(1) != key[1]:
            continue
        end = caps[i + 1].start() if i + 1 < len(caps) else m.start() + 3000
        cap = re.sub(r"\s+", " ", text[m.start():min(end, m.start() + 4000)]).strip()
        if best is None or len(cap) > len(best):
            best = cap
    if best is None:
        return None
    return ("Supplementary Fig. %s (from the SI PDF)" % key[1], best,
            _panel_hits(best, key[2]))


def legend_any(pmcid, xml, sheet):
    """The XML's legend, else the SI PDF's for a supplementary figure."""
    return legend_for(xml, sheet) or si_legend(pmcid, sheet)


def methods(xml, limit=6):
    """-> sentences describing HOW the measurement was made.

    `<front>` is dropped first, and that is not tidiness. JATS front matter is
    title, author list, affiliations, PMID, DOI and history dates, and it
    carries almost no full stops -- so `_sentences` cannot split it, the whole
    block comes back as ONE ~1,000-character "sentence", and it matches if any
    METHOD token appears anywhere inside it. On the V18 desk, PMC11839401's
    first method sentence was the author list. Noise at the top of the evidence
    someone is about to decide from is worse than no evidence: it is what they
    read first.
    """
    body = re.sub(r"<front\b.*?</front>", " ", xml, flags=re.S)
    body = re.sub(r"<fig\b.*?</fig>", " ", body, flags=re.S)
    return [s for s in _sentences(_text(body)) if METHOD.search(s)][:limit]


def claimed_n(xml, limit=8):
    """-> sentences in which the paper states a group size."""
    out, seen = [], set()
    for s in _sentences(_text(xml)):
        for m in CLAIM_N.finditer(s):
            k = m.group(0).lower()
            if k not in seen:
                seen.add(k)
                out.append((m.group(0), s))
            break
    return out[:limit]


# Inside a figure's OWN legend `n = 5` needs no "mice" after it: the legend is
# where group sizes are stated per panel, tersely. Paper-wide, CLAIM_N stays
# strict, because there a bare `n = 3` is as often an in-vitro replicate.
LEGEND_N = re.compile(r"\bn\s*=\s*\d+(?:\s*(?:[-–,/]|and|or|to)\s*\d+)*", re.I)


def legend_n(caption):
    """-> [(statement, sentence)]: every `n = ...` in a figure legend, with its
    sentence, so whoever compares counts can see WHICH panel and WHAT unit
    (mice, tumours, independent experiments) the n belongs to."""
    out = []
    for s in _sentences(caption or ""):
        for m in LEGEND_N.finditer(s):
            out.append((m.group(0), s))
    return out


def hosts(xml, limit=6):
    """-> the host strains the article names, in order of first appearance."""
    seen = []
    for m in SPECIES.finditer(_text(xml)):
        if m.group(0) not in seen:
            seen.append(m.group(0))
    return seen[:limit]


def bundle(pmcid, sheet=None):
    """-> the EVIDENCE BUNDLE an adjudicator sees, and nothing else.

    Deliberately carries no recommendation, no score and no reasoning. The
    agent that gathers evidence must not hand its conclusion to the agent that
    judges: V17's retraction happened because a reader formed "probably in
    vitro" from the sheet and never fetched the legend that said otherwise.
    A bundle is evidence; a verdict is somebody's job.

    `resolved_at` names the cheapest rung that could settle it, so the ladder
    can be measured and the rungs that carry nothing can be deleted.
    """
    out = {"pmcid": pmcid, "sheet": sheet, "legend": None,
           "legend_panel_sentences": [], "methods": [], "claimed_n": [],
           "claimed_n_sentences": [], "hosts": [],
           "resolved_at": None, "walls": []}
    try:
        meta = metadata(pmcid)
    except PaperWall as exc:
        out["walls"].append(str(exc))
        return out
    out.update({k: meta[k] for k in
                ("doi", "title", "journal", "year", "licence", "open_access")})
    if str(meta["open_access"]).upper() != "Y":
        out["walls"].append("not open access -- protocol rule 12 stop")
        return out
    try:
        xml = fulltext(pmcid)
    except PaperWall as exc:
        out["walls"].append(str(exc))
        return out

    leg = None
    if sheet:
        try:
            leg = legend_any(pmcid, xml, sheet)
        except PaperWall as exc:          # the SI PDF could not be read
            out["walls"].append(str(exc))
    if leg:
        out["legend"] = leg[1]
        out["legend_panel_sentences"] = leg[2]
        out["resolved_at"] = "L2"
    elif sheet:
        out["walls"].append(
            "no legend located for %r -- UNRESOLVED, not absent. Either the "
            "sheet name carries no figure reference, or the legend is in the "
            "SI PDF rather than the full text." % sheet)
    out["methods"] = methods(xml)
    cn = claimed_n(xml)
    out["claimed_n"] = [k for k, _ in cn]
    out["claimed_n_sentences"] = [t for _, t in cn]
    out["hosts"] = hosts(xml)
    if out["resolved_at"] is None and (out["methods"] or out["claimed_n"]):
        out["resolved_at"] = "L3"
    return out


# ---------------------------------------------------------------------- CLI
def report(pmcid, sheet=None, stream=sys.stdout):
    meta = metadata(pmcid)
    p = stream.write
    p("  %s  %s\n" % (pmcid, meta["doi"]))
    p("  %s\n" % meta["title"][:96])
    p("  %s %s | open access: %s | licence: %s\n"
      % (meta["journal"], meta["year"], meta["open_access"], meta["licence"]))
    if str(meta["open_access"]).upper() != "Y":
        p("\n  NOT OPEN ACCESS. Protocol rule 12 makes that a stop, not an\n"
          "  obstacle. No full text is fetched.\n")
        return meta
    xml = fulltext(pmcid)

    if sheet:
        p("\n  LEGEND for sheet %r\n" % sheet)
        try:
            leg = legend_any(pmcid, xml, sheet)
        except PaperWall as exc:
            p("    WALL -- %s\n" % exc)
            leg = None
        if leg is None:
            p("    NOT FOUND. Either the sheet name carries no figure reference\n"
              "    (e.g. `Sheet1`), or the figure is supplementary and its\n"
              "    legend lives in the SI PDF rather than the full text.\n"
              "    UNRESOLVED, not absent -- open the sheet and read it.\n")
        else:
            lab, cap, hits = leg
            p("    %s\n" % lab)
            for s in hits:
                p("    >> %s\n" % s)
            if not hits:
                p("    (panel letter not located inside the caption; the whole\n"
                  "     caption follows)\n")
            p("\n    %s\n" % cap[:1200])

    m = methods(xml)
    p("\n  METHOD, in the paper's own words (quote one of these in the builder):\n")
    for s in (m or []):
        p("    * %s\n" % s[:300])
    if not m:
        p("    none matched. The builder's METHOD line must then be resolved by\n"
          "    reading, and recorded as resolved by a human.\n")

    n = claimed_n(xml)
    p("\n  GROUP SIZES THE PAPER CLAIMS (compare against your COUNT):\n")
    for k, s in (n or []):
        p("    * %-28s %s\n" % (k, s[:200]))
    if not n:
        p("    none stated. Then the count is the only number there is, and the\n"
          "    builder says so.\n")

    h = hosts(xml)
    if h:
        p("\n  HOST STRAINS MENTIONED: %s\n" % ", ".join(h))
    p("\n  This is evidence, not a verdict. The scanner decides on structure;\n"
      "  you decide, and now you can quote the paper while doing it.\n")
    return meta


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pmcid", help="e.g. PMC13534483")
    ap.add_argument("--json", action="store_true",
                    help="emit the evidence bundle an adjudicator sees -- no "
                         "recommendation, no score, evidence only")
    ap.add_argument("--sheet", default=None,
                    help='the accepted sheet name, e.g. "Fig. 2i" -- used to '
                         "find that panel's legend")
    a = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    try:
        if a.json:
            import json as _j
            print(_j.dumps(bundle(a.pmcid, a.sheet), indent=1,
                           ensure_ascii=False))
        else:
            report(a.pmcid, a.sheet)
    except PaperWall as exc:
        print("WALL -- not a result:\n  %s" % exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
