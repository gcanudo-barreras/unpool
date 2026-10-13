"""usage: unpool <command> [args]

  scan         triage the supplementary files of given PMCIDs
  mine         search Europe PMC and scan a whole query  -> runs/*_candidates.csv
  worklist     collapse candidates to one row per paper  -> runs/worklist.csv
  paper        a paper's figure legend, methods and group sizes
  sheet        print a supplementary sheet, or list every sheet in a paper
  extract      a sheet as a tidy per-subject CSV (subject, time, value)
  export       a campaign's extractions as one per-animal CSV (DOI, arm, values)
  desk         fetch evidence for a whole worklist, then queue it for answering
  guard        validate a builder's per-subject CSV
  fingerprint  screen a corpus for identical-curve re-exports

`unpool <command> --help` for each; `unpool mine demo` and
`unpool fingerprint demo` run offline self-checks.
"""
import importlib
import os
import sys

COMMANDS = ("scan", "mine", "worklist", "paper", "sheet", "extract", "export", "desk", "guard",
            "fingerprint")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in COMMANDS:
        print(__doc__.strip())
        return 0 if argv[:1] in (["-h"], ["--help"]) else 2
    cmd, rest = argv[0], argv[1:]
    # The tool runs from a clone: profiles/, runs/ and si_cache/ live beside
    # the package. A plain `pip install .` copies the package alone, and every
    # command then died on an opaque FileNotFoundError.
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(root, "profiles")):
        print("unpool runs from a clone of its repository, not from a plain "
              "install:\n  git clone <repository> && cd unpool && pip install -e .\n"
              "(no profiles/ next to the package, in %s)" % root, file=sys.stderr)
        return 2
    mod = importlib.import_module("unpool." + cmd)
    if rest == ["demo"] and hasattr(mod, "demo"):
        return mod.demo()
    sys.argv = ["unpool " + cmd] + rest     # so --help names the real command
    return mod.main(rest)


if __name__ == "__main__":
    sys.exit(main())
