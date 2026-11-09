"""nim.discovery CLI: request -> search -> select -> merge -> finish (BUNDLE.md + manifest)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import keywords as kw
from .bundle import Bundle, check, config
from .util import VERSION

DEFAULT_OUT = ".nim/discovery"


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="nim.discovery", description=__doc__)
    ap.add_argument("--version", action="version", version=f"nim.discovery {VERSION}")
    ap.add_argument(
        "-o",
        "--out",
        default=DEFAULT_OUT,
        help=f"bundle directory (default: {DEFAULT_OUT})",
    )
    ap.add_argument(
        "--offline", action="store_true", help="cache only; never touch the network"
    )
    ap.add_argument(
        "--refresh", action="store_true", help="ignore cache freshness; refetch"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="full pipeline from a stated idea / work request")
    r.add_argument("text", help="the request, verbatim (quote it)")
    r.add_argument(
        "-k",
        "--keywords",
        action="append",
        default=[],
        help="explicit keywords, comma-separated (repeatable)",
    )
    r.add_argument(
        "-p", "--profile", default="default", help="prior profile in etc/sources.json"
    )
    r.add_argument(
        "-r", "--rigor", default="standard", choices=["loose", "standard", "rigorous"]
    )
    r.add_argument(
        "--pin",
        action="append",
        default=[],
        help="ontology id to always select (repeatable)",
    )
    r.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="ontology id to never select (repeatable)",
    )
    r.add_argument("-n", "--max-ontologies", type=int, default=5)

    sub.add_parser(
        "search", help="re-run search from request.json (after editing keywords/pins)"
    )
    sub.add_parser("select", help="re-run ontology selection from candidates.jsonl")
    sub.add_parser("merge", help="re-run merge + digest from selection.json")
    sub.add_parser("show", help="print BUNDLE.md")
    sub.add_parser(
        "check", help="validate bundle files against schema and manifest hashes"
    )
    sub.add_parser("profiles", help="list prior profiles")
    k = sub.add_parser("keywords", help="show keywords extracted from text")
    k.add_argument("text")

    a = ap.parse_args(argv)
    out = Path(a.out)

    if a.cmd == "keywords":
        print("\n".join(kw.extract(a.text)))
        return 0
    if a.cmd == "profiles":
        for name, p in config()["profiles"].items():
            print(f"{name:10} {p['description']}")
        return 0
    if a.cmd == "show":
        p = out / "BUNDLE.md"
        if not p.exists():
            _err(f"no bundle at {out}")
            return 1
        print(p.read_text(encoding="utf-8"))
        return 0
    if a.cmd == "check":
        errs = check(out)
        for e in errs:
            _err(e)
        print("ok" if not errs else f"{len(errs)} problem(s)")
        return 0 if not errs else 1

    b = Bundle(out, offline=a.offline, refresh=a.refresh, log=_err)
    if a.cmd == "run":
        b.run(
            text=a.text,
            keywords=a.keywords,
            profile=a.profile,
            rigor=a.rigor,
            pin=a.pin,
            exclude=a.exclude,
            max_ontologies=a.max_ontologies,
        )
    elif a.cmd == "search":
        b.search()
        b.select()
        b.merge()
        b.finish()
    elif a.cmd == "select":
        b.select()
        b.merge()
        b.finish()
    elif a.cmd == "merge":
        b.merge()
        b.finish()
    _err(f"bundle: {out}/BUNDLE.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
