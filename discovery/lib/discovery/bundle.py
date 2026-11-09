"""Bundle I/O: stage runner, digest (BUNDLE.md), manifest, check."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import keywords as kw
from .merge import merge, to_json_schema
from .select import select
from .sources import OLS, SchemaOrg, SchemaStore
from .util import (
    ROOT,
    VERSION,
    Fetcher,
    OfflineMiss,
    dump_json,
    load_json,
    now,
    sha256_file,
)
from .validate import validate

FILES = {  # path -> $defs name (None = not schema-governed)
    "request.json": "request",
    "candidates.jsonl": "candidate",
    "selection.json": "selection",
    "baseline.model.json": "baseline",
    "baseline.schema.json": None,
    "BUNDLE.md": None,
}


def config() -> dict:
    return load_json(ROOT / "etc" / "sources.json")


def priors_for(profile: str):
    p = config()["profiles"].get(profile)
    if p is None:
        raise SystemExit(f"unknown profile '{profile}' (see etc/sources.json)")
    table = {**p.get("penalize", {}), **p.get("priors", {})}
    return lambda o: table.get(o, 1.0)


class Bundle:
    def __init__(
        self, out: Path, offline: bool = False, refresh: bool = False, log=print
    ):
        self.out = Path(out)
        self.fetch = Fetcher(offline=offline, refresh=refresh)
        self.offline = offline
        self.log = log
        cfg = config()["sources"]
        self.adapters = {
            "ols": OLS(cfg["ols"], self.fetch),
            "schemaorg": SchemaOrg(cfg["schemaorg"], self.fetch),
            "schemastore": SchemaStore(cfg["schemastore"], self.fetch),
        }

    # -- stages ----------------------------------------------------------------
    def request(
        self,
        text: str,
        keywords: list[str],
        profile: str,
        rigor: str,
        pin: list[str],
        exclude: list[str],
        max_ontologies: int,
    ) -> dict:
        self._archive()
        self.out.mkdir(parents=True, exist_ok=True)
        explicit = kw.parse_explicit(keywords)
        req = {
            "text": text,
            "keywords": explicit or kw.extract(text),
            "extracted": not explicit,
            "profile": profile,
            "rigor": rigor,
            "pin": pin,
            "exclude": exclude,
            "max_ontologies": max_ontologies,
            "created": now(),
        }
        if not req["keywords"]:
            raise SystemExit("no keywords: pass -k or a more specific request")
        self._write("request.json", req)
        return req

    def search(self) -> list[dict]:
        req = self._read("request.json")
        prior = priors_for(req["profile"])
        cands: list[dict] = []
        sources = [("ols", None), ("schemaorg", None), ("schemastore", None)]
        sources += [
            ("ols", o)
            for o in req.get("pin", [])
            if o not in ("schemaorg", "schemastore")
        ]
        failures = []
        for k in req["keywords"]:
            for name, only in sources:
                try:
                    if name == "ols" and only:
                        hits = self.adapters["ols"].search_in(k, only, prior)
                    else:
                        hits = self.adapters[name].search(k, prior)
                except OfflineMiss as e:
                    failures.append(f"{name}: not cached ({e})")
                    continue
                except Exception as e:  # one source failing must not sink the run
                    failures.append(
                        f"{name}{'/' + only if only else ''} '{k}': {type(e).__name__}: {e}"
                    )
                    continue
                seen = {(c["iri"], c["keyword"]) for c in cands}
                cands += [h for h in hits if (h["iri"], h["keyword"]) not in seen]
        for f in sorted(set(failures)):
            self.log(f"warn: {f}")
        (self.out / "candidates.jsonl").write_text(
            "".join(json.dumps(c, ensure_ascii=False) + "\n" for c in cands),
            encoding="utf-8",
        )
        self.log(f"search: {len(cands)} candidates for {len(req['keywords'])} keywords")
        return cands

    def select(self) -> dict:
        req, cands = self._read("request.json"), self._candidates()
        sel = select(cands, req, priors_for(req["profile"]))
        for o in sel["ontologies"]:
            meta = self._ontology_meta(o["id"])
            o["title"], o["version"] = meta["title"], meta["version"]
        self._write("selection.json", sel)
        picked = [o["id"] for o in sel["ontologies"] if o["selected"]]
        self.log(
            f"select: {', '.join(picked) or '(none)'}; uncovered: {', '.join(sel['uncovered']) or '-'}"
        )
        return sel

    def merge(self) -> dict:
        req, cands, sel = (
            self._read("request.json"),
            self._candidates(),
            self._read("selection.json"),
        )
        model = merge(req, cands, sel, self.adapters, config()["upper"])
        self._write("baseline.model.json", model)
        dump_json(to_json_schema(model), self.out / "baseline.schema.json")
        self.log(
            f"merge: {len(model['entities'])} entities, {len(model['relations'])} relations, "
            f"{len(model['vocabulary'])} vocabulary terms, {len(model['unresolved'])} unresolved"
        )
        return model

    def finish(self) -> None:
        (self.out / "BUNDLE.md").write_text(digest(self.out), encoding="utf-8")
        self._manifest()

    def run(self, **req_args) -> None:
        self.request(**req_args)
        self.search()
        self.select()
        self.merge()
        self.finish()

    # -- helpers ---------------------------------------------------------------
    def _ontology_meta(self, oid: str) -> dict:
        if oid == "schemaorg":
            return {"title": "schema.org", "version": "latest"}
        try:
            return self.adapters["ols"].ontology(oid)
        except Exception:
            return {"title": None, "version": None}

    def _archive(self) -> None:
        if (self.out / "request.json").exists():
            dest = self.out / "history" / now().replace(":", "")
            dest.mkdir(parents=True, exist_ok=True)
            for f in [*FILES, "manifest.json"]:
                if (self.out / f).exists():
                    shutil.move(str(self.out / f), dest / f)
            self.log(f"archived previous bundle -> {dest}")

    def _read(self, name: str):
        p = self.out / name
        if not p.exists():
            raise SystemExit(f"missing {p}: run the earlier stage first")
        return load_json(p)

    def _candidates(self) -> list[dict]:
        p = self.out / "candidates.jsonl"
        if not p.exists():
            raise SystemExit(f"missing {p}: run search first")
        return [
            json.loads(line)
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _write(self, name: str, obj) -> None:
        errs = validate(obj, FILES[name])
        if errs:
            raise SystemExit(
                f"{name} violates schema $defs/{FILES[name]}:\n  "
                + "\n  ".join(errs[:20])
            )
        dump_json(obj, self.out / name)

    def _manifest(self) -> None:
        old = (
            load_json(self.out / "manifest.json")
            if (self.out / "manifest.json").exists()
            else {}
        )
        srcs = {s["url"]: s for s in old.get("sources", [])}
        srcs.update(self.fetch.log)
        man = {
            "bundle": "nim.discovery",
            "schema": "urn:nim:discovery:bundle:1",
            "tool": f"nim.discovery {VERSION}",
            "generatedAtTime": now(),
            "offline": self.offline,
            "files": [
                {"path": f, "sha256": sha256_file(self.out / f), "schema": FILES[f]}
                for f in FILES
                if (self.out / f).exists()
            ],
            "sources": sorted(srcs.values(), key=lambda s: s["url"]),
        }
        errs = validate(man, "manifest")
        if errs:
            raise SystemExit("manifest invalid:\n  " + "\n  ".join(errs))
        dump_json(man, self.out / "manifest.json")


def check(out: Path) -> list[str]:
    """Validate every bundle file against its schema and the manifest hashes."""
    out = Path(out)
    errs: list[str] = []
    if not (out / "manifest.json").exists():
        return [f"{out}/manifest.json missing"]
    man = load_json(out / "manifest.json")
    errs += [f"manifest.json {e}" for e in validate(man, "manifest")]
    for f in man.get("files", []):
        p = out / f["path"]
        if not p.exists():
            errs.append(f"{f['path']}: missing")
            continue
        if sha256_file(p) != f["sha256"]:
            errs.append(
                f"{f['path']}: modified since generation (sha256 differs; re-run a stage or `finish`)"
            )
        if f.get("schema") == "candidate":
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines()):
                errs += [
                    f"candidates.jsonl:{i + 1} {e}"
                    for e in validate(json.loads(line), "candidate")
                ]
        elif f.get("schema"):
            errs += [f"{f['path']} {e}" for e in validate(load_json(p), f["schema"])]
    return errs


# -- digest -------------------------------------------------------------------


def _cell(s, n=70) -> str:
    s = (s or "").replace("|", "/").replace("\n", " ").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def digest(out: Path) -> str:
    """Compact, agent-facing summary. Kept short: a SessionStart hook injects it."""
    req, sel, m = (
        load_json(Path(out) / f)
        for f in ("request.json", "selection.json", "baseline.model.json")
    )
    L = [
        f"# Discovery bundle: {_cell(req['text'], 90)}",
        "",
        f"Rigor `{req['rigor']}` · profile `{req['profile']}` · keywords ({'extracted' if req['extracted'] else 'explicit'}): "
        + ", ".join(f"`{k}`" for k in req["keywords"]),
        "",
        "Authority for data design. Cite entity IRIs in schema `description`/`x-iri`; record deviations as decisions.",
        "",
        "## Selected ontologies",
        "",
        "| id | title | version | covers | reason |",
        "|---|---|---|---|---|",
    ]
    for o in sel["ontologies"]:
        if o["selected"]:
            L.append(
                f"| `{o['id']}` | {_cell(o.get('title'), 40)} | {_cell(o.get('version'), 14)} | "
                f"{', '.join(o['covers']) or '-'} | {_cell(o['reason'], 60)} |"
            )
    runners = [o["id"] for o in sel["ontologies"] if not o["selected"]]
    if runners:
        L += [
            "",
            f"Runners-up (pin with `--pin`): {', '.join(f'`{r}`' for r in runners)}",
        ]
    L += [
        "",
        "## Entities",
        "",
        "| entity | term | upper | parents | key attributes |",
        "|---|---|---|---|---|",
    ]
    for e in m["entities"]:
        rel = [a["name"] for a in e["attributes"] if a.get("relevant")]
        attrs = (
            (", ".join(rel[:6]) + (" + " if rel else ""))
            + f"{len(e['attributes'])} total"
            if e["attributes"]
            else "-"
        )
        parents = (
            ", ".join(
                _cell(p.get("label") or p["iri"].rsplit("/", 1)[-1], 24)
                for p in e["parents"][:3]
            )
            or "-"
        )
        L.append(
            f"| **{e['name']}** | [{_cell(e['label'], 30)}]({e['iri']}) `{e['ontology']}` | {e.get('upper') or '?'} "
            f"| {parents} | {attrs} |"
        )
    if m["relations"]:
        L += ["", "## Relations", ""]
        L += [f"- {r['from']} —{r['name']}→ {r['to']}" for r in m["relations"][:25]]
    maps = [(e["name"], mp) for e in m["entities"] for mp in e["mappings"]]
    if maps:
        L += ["", "## Crosswalk (merger)", ""]
        L += [
            f"- {n} {mp['relation']} <{mp['iri']}> ({mp.get('basis')})"
            for n, mp in maps[:25]
        ]
    if m["vocabulary"]:
        L += ["", "## Vocabulary (properties / individuals)", ""]
        L += [
            f"- `{v['keyword']}` → [{v['label']}]({v['iri']}) `{v['ontology']}` {v['kind']}"
            for v in m["vocabulary"]
        ]
    if sel.get("schemas"):
        L += ["", "## Reference JSON Schemas (SchemaStore)", ""]
        L += [
            f"- [{s['label']}]({s['iri']}) — {_cell(s.get('definition'), 80)}"
            for s in sel["schemas"]
        ]
    if m["unresolved"]:
        L += [
            "",
            "## Unresolved (no benchmark; assumption required)",
            "",
            ", ".join(f"`{k}`" for k in m["unresolved"]),
        ]
    L += [
        "",
        "## Files",
        "",
        "`baseline.model.json` (entities, relations, crosswalk, decisions) · `baseline.schema.json` (JSON Schema 2020-12 seed for JSON↔DDL) · "
        "`selection.json` · `candidates.jsonl` (all hits) · `manifest.json` (provenance, sha256)",
        "",
    ]
    return "\n".join(L)
