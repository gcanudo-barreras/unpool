"""Fetch the recall gate's fixture files from their public sources.

    python fixtures/fetch.py            # fill the cache, report what is missing
    python fixtures/fetch.py --check    # verify the cache, fetch nothing

WHY THE FILES ARE NOT IN THE REPO
------------------------------------------------------------------------------
They are publisher supplementary material. Most are CC-BY or CC0 and could be
redistributed with attribution, but a manifest costs nothing, carries no
licence risk for ANY of them, and pins the exact bytes by `sha256` -- which
re-distribution alone would not do. A fixture set you cannot prove is the one
the recall figure was measured on is not a fixture set.

The renaming on import means a member cannot be found by NAME: this repo calls
one file `ncomms71144_aldh1a1_sourcedata.xlsx` and the publisher calls it
`41467_2026_71144_MOESM5_ESM.xlsx`. **So members are matched by `sha256`**,
which finds the file and verifies it in one step, and survives a publisher
renaming their ESM attachments.

ALL THREE ROUTES ARE THE SAME OPERATION -- fetch one archive, walk its members,
keep the one whose hash matches -- so there is one function and not three.

  epmc            Europe PMC OA supplementary bundle, via the tool's own
                  `scan.fetch()`. No second fetcher to keep working.
  zenodo:<id>     Zenodo's whole-record archive.
  dryad           Dryad's whole-dataset archive.
  manual:<host>   NOT FETCHED AUTOMATICALLY. Dryad answers 401 to an
                  unauthenticated download of both the dataset archive and the
                  per-file link; only its metadata is public. So this route
                  prints the dataset's real file names -- read from that public
                  metadata -- and the operator fetches them once by hand into
                  the cache, where the manifest sha256 verifies them exactly as
                  if they had come down automatically.

  transcribed     NOT FETCHED, and it is a REAL GAP. These files are not
                  publisher bytes at all -- they were transcribed or
                  re-schematised by hand into this project's own column names.
                  A scanner scored on a file whose headers the scorer wrote is
                  scored on its own reflection: the POS is easier to accept and
                  the NEGATIVE CONTROL is easier to reject than any file the
                  instrument will meet in the wild. They are excluded from the
                  headline figure and reported on their own line.

  not_oa          NOT FETCHED, and not a gap. The shipping scanner gets
                  `not_open_access` on these, so a gate that scored them would
                  be scoring files the instrument can never be handed. Their
                  rows stay in the manifest so the exclusion is visible and
                  reasoned rather than absent.

A file that will not come down is reported and the gate scores without it,
over a denominator it states. It is never silently dropped.
"""
import csv
import hashlib
import io
import os
import sys
import urllib.parse
import urllib.request
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
from unpool import scan as S  # noqa: E402 -- the epmc route IS the tool's own fetcher

MANIFEST = os.path.join(_HERE, "manifest.csv")
DRYAD_TOKEN_ENV = "DRYAD_TOKEN"

DRYAD_HELP = """
  Dryad refuses unauthenticated downloads (401 on both the dataset archive and
  the per-file link; only its metadata is public). You have three ways out and
  none of them blocks the rest of the run:

  (1) FETCH BY HAND -- no account needed, takes a minute.
      Open the dataset page printed below, download the files it lists, and
      drop them into
          %s
      under the names given. The manifest sha256 verifies each one, so a wrong
      or truncated download is caught rather than trusted.

  (2) USE A TOKEN -- if you already have a Dryad account.
      Dryad issues OAuth credentials from your account page; exchange them for
      a bearer token and export it:
          export %s=<your bearer token>          (PowerShell: $env:%s="...")
      Re-run and these files come down automatically. Docs:
          https://datadryad.org/api.html

  (3) SKIP DRYAD ENTIRELY -- if you do not care about these sources.
          python fixtures/fetch.py --skip dryad
      The run proceeds, the gate scores over what it has, and the denominator
      says so. Nothing is silently dropped: skipped rows are listed every time.
""".strip()
CACHE = os.path.join(_HERE, "cache")
UA = S.UA
EPMC_SEARCH = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def rows():
    with open(MANIFEST, encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def pmcid_for(doi):
    """-> 'PMC…' or None. One search, DOI is exact, so hitCount is 0 or 1."""
    import json
    q = urllib.parse.urlencode({"query": 'DOI:"%s"' % doi,
                                "format": "json", "pageSize": "1"})
    try:
        req = urllib.request.Request(EPMC_SEARCH + "?" + q, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.load(r)
    except Exception as e:
        return None, "search failed: %s" % type(e).__name__
    hits = (res.get("resultList") or {}).get("result") or []
    if not hits:
        return None, "no Europe PMC record for this DOI"
    pmcid = hits[0].get("pmcid")
    return (pmcid, None) if pmcid else (None, "record has no PMCID (not in OA subset)")


def _auth():
    tok = dryad_token()
    h = dict(UA)
    if tok:
        h["Authorization"] = "Bearer " + tok
    return h


def dryad_blobs(doi):
    """-> [bytes] for every file in the dataset's latest version.

    Dryad's whole-dataset `/download` endpoint answers 401 without a token, so
    this walks `versions -> files -> stash:download`, which is public. Hashing
    every file is cheap here (the CT-26 set is 7 files of ~18 KB) and it means
    a member is still found by content when Dryad renames a path.
    """
    import json
    base = "https://datadryad.org"
    def get(u):
        return json.load(urllib.request.urlopen(
            urllib.request.Request(base + u, headers=_auth()), timeout=120))
    ds = get("/api/v2/datasets/%s" % urllib.parse.quote("doi:" + doi, safe=""))
    ver = ds["_links"]["stash:version"]["href"]
    out = []
    for f in get(ver + "/files").get("_embedded", {}).get("stash:files", []):
        href = (f.get("_links", {}).get("stash:download") or {}).get("href")
        if not href:
            continue
        with urllib.request.urlopen(
                urllib.request.Request(base + href, headers=_auth()),
                timeout=300) as r:
            out.append(r.read())
    return out


def archive_url(route, doi):
    if route.startswith("zenodo:"):
        return "https://zenodo.org/api/records/%s/files-archive" % route.split(":", 1)[1]
    if route == "dryad":
        return "https://datadryad.org/api/v2/datasets/%s/download" % \
            urllib.parse.quote("doi:" + doi, safe="")
    return None


def dryad_paths(doi):
    """-> [str] the dataset's real file names. Metadata is public; files are not."""
    import json
    base = "https://datadryad.org"
    def get(u):
        return json.load(urllib.request.urlopen(
            urllib.request.Request(base + u, headers=UA), timeout=120))
    ds = get("/api/v2/datasets/%s" % urllib.parse.quote("doi:" + doi, safe=""))
    ver = ds["_links"]["stash:version"]["href"]
    return [f.get("path") for f in
            get(ver + "/files").get("_embedded", {}).get("stash:files", [])]


def get_blobs(route, doi):
    """-> ([bytes], None) | (None, reason). Candidate blobs to search by hash."""
    if route.startswith("manual"):
        return None, "manual route"
    if route == "dryad":
        try:
            return dryad_blobs(doi), None
        except Exception as e:
            return None, "%s: %s" % (type(e).__name__, e)
    if route == "epmc":
        pmcid, why = pmcid_for(doi)
        if not pmcid:
            return None, why
        p = S.fetch(pmcid)
        if isinstance(p, str) and p.startswith("ERR"):
            return None, "%s (%s)" % (p, pmcid)
        with open(p, "rb") as fh:
            return [fh.read()], None
    url = archive_url(route, doi)
    if url is None:
        return None, "unknown route %r" % route
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=300) as r:
            return [r.read()], None
    except Exception as e:
        return None, "%s: %s" % (type(e).__name__, e)


def extract(blob, want_hash):
    """Walk the archive's members; return the one whose sha256 matches."""
    if sha256(blob) == want_hash:          # the archive IS the file
        return blob
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except zipfile.BadZipFile:
        return None
    for name in zf.namelist():
        try:
            data = zf.read(name)
        except Exception:
            continue
        if sha256(data) == want_hash:
            return data
        if data[:2] == b"PK":              # nested archive, one level
            inner = extract(data, want_hash)
            if inner is not None:
                return inner
    return None


def cached_ok(row):
    p = os.path.join(CACHE, row["file"])
    if not os.path.exists(p):
        return False
    with open(p, "rb") as fh:
        return sha256(fh.read()) == row["sha256"]


def dryad_token():
    return os.environ.get(DRYAD_TOKEN_ENV, "").strip() or None


def parse_skips(argv):
    """-> set of route prefixes the operator asked to skip (--skip dryad ...)."""
    out = set()
    for i, a in enumerate(argv):
        if a == "--skip" and i + 1 < len(argv):
            out.update(s.strip().lower() for s in argv[i + 1].split(","))
        elif a.startswith("--skip="):
            out.update(s.strip().lower() for s in a.split("=", 1)[1].split(","))
    return out


def main(argv):
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        print(DRYAD_HELP % (CACHE, DRYAD_TOKEN_ENV, DRYAD_TOKEN_ENV))
        return 0
    check_only = "--check" in argv
    skips = parse_skips(argv)
    S.preflight_banner()
    os.makedirs(CACHE, exist_ok=True)
    have, skipped, transcribed, manual, failed = [], [], [], [], []
    by_doi = {}
    for row in rows():
        name, route = row["file"], row["route"]
        if route == "not_oa":
            skipped.append((name, row.get("note") or "not open access"))
            continue
        if route.startswith("manual"):
            host = route.split(":", 1)[1] if ":" in route else "manual"
            if host in skips or "manual" in skips:
                skipped.append((name, "skipped by request (--skip %s)" % host))
                continue
            if host == "dryad" and dryad_token():
                blobs, why = get_blobs("dryad", row["doi"])
                data = None if blobs is None else next(
                    (d for d in (extract(b, row["sha256"]) for b in blobs)
                     if d is not None), None)
                if data is not None:
                    with open(os.path.join(CACHE, name), "wb") as fh:
                        fh.write(data)
                    have.append(name)
                    continue
                failed.append((name, "token set but fetch failed: %s"
                               % (why or "no hash match")))
                continue
            manual.append((name, row["doi"]))
            continue
        if route == "transcribed":
            transcribed.append((name, row.get("note") or "not a publisher file"))
            continue
        if cached_ok(row):
            have.append(name)
            continue
        if check_only:
            failed.append((name, "not in cache"))
            continue
        key = (route, row["doi"])
        if key not in by_doi:
            by_doi[key] = get_blobs(route, row["doi"])
        blobs, why = by_doi[key]
        if blobs is None:
            failed.append((name, why))
            continue
        data = next((d for d in (extract(b, row["sha256"]) for b in blobs)
                     if d is not None), None)
        if data is None:
            failed.append((name, "nothing at this source matches the manifest sha256"))
            continue
        with open(os.path.join(CACHE, name), "wb") as fh:
            fh.write(data)
        have.append(name)

    print("\n  cached  %d" % len(have))
    print("  skipped %d (not open access -- the scanner could never see them)"
          % len(skipped))
    for n, why in skipped:
        print("      %-44s %s" % (n, (why or "")[:70]))
    print("  EXCLUDED, transcribed %d -- NOT publisher bytes, see the manifest notes"
          % len(transcribed))
    for n, why in transcribed:
        print("      %-44s %s" % (n, (why or "")[:70]))
    if manual:
        print("  MANUAL   %d -- the source refuses unauthenticated download" % len(manual))
        print(DRYAD_HELP % (CACHE, DRYAD_TOKEN_ENV, DRYAD_TOKEN_ENV))
        print("")
        for doi in sorted({d for _, d in manual}):
            names = sorted(n for n, dd in manual if dd == doi)
            print("      %s  -> https://datadryad.org/dataset/doi:%s" % (doi, doi))
            try:
                for path in dryad_paths(doi):
                    print("           %s" % path)
            except Exception as e:
                print("           (file list unavailable: %s)" % type(e).__name__)
            print("           save into fixtures/cache/ under these names:")
            for n in names:
                print("           %s" % n)
    if failed:
        print("  FAILED  %d" % len(failed))
        for n, why in failed:
            print("      %-44s %s" % (n, why))
    print("\n  the gate's denominator is the %d cached files, and it says so.\n"
          % len(have))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
