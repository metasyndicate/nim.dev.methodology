"""Source adapters. Each search() yields candidate dicts conforming to $defs/candidate."""

from __future__ import annotations

import json
import re
import urllib.parse

from .util import Fetcher, as_list, first, norm, text_of

MATCH_WEIGHT = {"exact": 1.0, "label": 0.6, "text": 0.3}
MAX_EXTRA_WORDS = 2  # a 'label' match may add at most this many words to the keyword


def classify_match(keyword: str, label: str) -> str:
    """exact: same normalized words. label: keyword is a word-bounded part of a short label
    ('order' in 'Order Status'). Anything looser ('research group' inside a 9-word
    instrument name) is only 'text' evidence and never drives selection or entities."""
    k, lab = norm(keyword), norm(label)
    if k == lab:
        return "exact"
    if (
        re.search(rf"(^| ){re.escape(k)}( |$)", lab)
        and len(lab.split()) - len(k.split()) <= MAX_EXTRA_WORDS
    ):
        return "label"
    return "text"


def score(match: str, rank: int, prior: float) -> float:
    return round(MATCH_WEIGHT[match] * (1.0 / (1.0 + 0.1 * rank)) * prior, 4)


# -- OLS4 ---------------------------------------------------------------------


class OLS:
    FIELDS = "iri,label,ontology_name,type,description,is_defining_ontology,obo_id"

    def __init__(self, cfg: dict, fetch: Fetcher):
        self.cfg, self.fetch = cfg, fetch
        self._ont: dict[str, dict] = {}

    def search_in(self, keyword: str, ontology: str, prior) -> list[dict]:
        """Search restricted to one ontology (used for pinned ontologies)."""
        return self.search(keyword, prior, ontology=ontology)

    def search(self, keyword: str, prior, ontology: str | None = None) -> list[dict]:
        params = {
            "q": keyword,
            "rows": self.cfg["rows"],
            "fieldList": self.FIELDS,
            "type": "class,property",
        }
        if ontology:
            params["ontology"] = ontology
        q = urllib.parse.urlencode(params)
        data = self.fetch.json(f"{self.cfg['search']}?{q}", self.cfg["ttl_days"])
        out, rank = [], 0
        for d in data.get("response", {}).get("docs", []):
            ont = d.get("ontology_name") or ""
            if (
                ont in self.cfg["skip_ontologies"]
                or d.get("is_defining_ontology") is False
            ):
                continue
            label, iri = d.get("label") or "", d.get("iri") or ""
            if not label or ":" not in iri:
                continue
            kind = (
                d.get("type")
                if d.get("type") in ("class", "property", "individual")
                else "class"
            )
            m = classify_match(keyword, label)
            out.append(
                {
                    "source": "ols",
                    "ontology": ont,
                    "iri": iri,
                    "label": label,
                    "kind": kind,
                    "definition": first(d.get("description")),
                    "keyword": keyword,
                    "match": m,
                    "rank": rank,
                    "score": score(m, rank, prior(ont)),
                }
            )
            rank += 1
        return out

    def ontology(self, oid: str) -> dict:
        if oid not in self._ont:
            try:
                d = self.fetch.json(self.cfg["ontology"].format(id=oid), 30)
                c = d.get("config", {})
                self._ont[oid] = {
                    "title": c.get("title"),
                    "version": d.get("version") or c.get("version"),
                }
            except Exception:
                self._ont[oid] = {"title": None, "version": None}
        return self._ont[oid]

    def ancestors(self, oid: str, iri: str) -> list[dict]:
        iri2 = urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")
        url = self.cfg["ancestors"].format(id=oid, iri2=iri2) + "?size=100"
        try:
            d = self.fetch.json(url, self.cfg["ttl_days"])
        except Exception:
            return []
        return [
            {"iri": t["iri"], "label": t.get("label")}
            for t in d.get("_embedded", {}).get("terms", [])
        ]


# -- schema.org ---------------------------------------------------------------

XSD_LIKE = {
    "schema:Text": "string",
    "schema:URL": "uri",
    "schema:Number": "number",
    "schema:Integer": "integer",
    "schema:Float": "number",
    "schema:Boolean": "boolean",
    "schema:Date": "date",
    "schema:DateTime": "date-time",
    "schema:Time": "time",
    "schema:CssSelectorType": "string",
    "schema:XPathType": "string",
    "schema:PronounceableText": "string",
}
PREFIXES = {"schema": "https://schema.org/"}


class SchemaOrg:
    """Local index over the schema.org JSON-LD release: classes, properties, domains, ranges,
    and the owl:equivalent* links schema.org now publishes to other vocabularies."""

    def __init__(self, cfg: dict, fetch: Fetcher):
        self.cfg, self.fetch = cfg, fetch
        self.loaded = False

    def _load(self) -> None:
        if self.loaded:
            return
        doc = json.loads(
            self.fetch.get(self.cfg["url"], self.cfg["ttl_days"]).decode("utf-8")
        )
        ctx = doc.get("@context", {})
        self.ctx = {k: v for k, v in ctx.items() if isinstance(v, str)}
        self.nodes = {
            n["@id"]: n for n in doc["@graph"] if isinstance(n.get("@id"), str)
        }
        self.classes, self.props = {}, {}
        self.by_domain: dict[str, list[str]] = {}
        for nid, n in self.nodes.items():
            if not nid.startswith("schema:"):
                continue
            types = as_list(n.get("@type"))
            if "rdfs:Class" in types:
                self.classes[nid] = n
            elif "rdf:Property" in types:
                self.props[nid] = n
                for dom in as_list(n.get("schema:domainIncludes")):
                    self.by_domain.setdefault(dom["@id"], []).append(nid)
        self.loaded = True

    def expand(self, curie: str) -> str:
        pre, _, local = curie.partition(":")
        base = self.ctx.get(pre)
        return f"{base}{local}" if base and not curie.startswith("http") else curie

    def search(self, keyword: str, prior) -> list[dict]:
        self._load()
        hits = []
        for nid, n in {**self.classes, **self.props}.items():
            label = text_of(n.get("rdfs:label")) or nid.split(":", 1)[1]
            m = classify_match(keyword, label)
            if m == "text":
                continue
            lab = norm(label)
            kind = "class" if nid in self.classes else "property"
            hits.append(
                (
                    0 if m == "exact" else 1,
                    0 if kind == "class" else 1,
                    len(lab),
                    nid,
                    label,
                    m,
                    kind,
                    n,
                )
            )
        hits.sort(key=lambda h: h[:3])
        out = []
        for rank, (_, _, _, nid, label, m, kind, n) in enumerate(hits[:15]):
            out.append(
                {
                    "source": "schemaorg",
                    "ontology": "schemaorg",
                    "iri": self.expand(nid),
                    "label": label,
                    "kind": kind,
                    "definition": text_of(n.get("rdfs:comment")),
                    "keyword": keyword,
                    "match": m,
                    "rank": rank,
                    "score": score(m, rank, prior("schemaorg")),
                }
            )
        return out

    def _curie(self, iri: str) -> str:
        return (
            "schema:" + iri.rsplit("/", 1)[-1]
            if iri.startswith("https://schema.org/")
            else iri
        )

    def parents(self, iri: str) -> list[dict]:
        self._load()
        n = self.nodes.get(self._curie(iri), {})
        out = []
        for p in as_list(n.get("rdfs:subClassOf")):
            pid = p["@id"]
            out.append(
                {
                    "iri": self.expand(pid),
                    "label": text_of(self.nodes.get(pid, {}).get("rdfs:label")),
                }
            )
        return out

    def equivalents(self, iri: str) -> list[dict]:
        self._load()
        n = self.nodes.get(self._curie(iri), {})
        out = []
        for key in ("owl:equivalentClass", "owl:equivalentProperty"):
            for e in as_list(n.get(key)):
                eid = e["@id"] if isinstance(e, dict) else e
                out.append(
                    {
                        "iri": self.expand(eid),
                        "ontology": eid.split(":", 1)[0],
                        "label": None,
                        "relation": "skos:exactMatch",
                        "basis": f"{key} in schema.org",
                    }
                )
        return out

    def attributes(self, iri: str) -> list[dict]:
        """Direct properties whose domainIncludes this class: (prop, ranges)."""
        self._load()
        cid = self._curie(iri)
        out = []
        for pid in sorted(self.by_domain.get(cid, [])):
            p = self.props[pid]
            ranges = [r["@id"] for r in as_list(p.get("schema:rangeIncludes"))]
            out.append(
                {
                    "id": pid,
                    "iri": self.expand(pid),
                    "name": pid.split(":", 1)[1],
                    "definition": text_of(p.get("rdfs:comment")),
                    "ranges": ranges,
                    "superseded": bool(p.get("schema:supersededBy")),
                }
            )
        return out


# -- SchemaStore --------------------------------------------------------------


class SchemaStore:
    def __init__(self, cfg: dict, fetch: Fetcher):
        self.cfg, self.fetch = cfg, fetch
        self._cat = None

    def search(self, keyword: str, prior) -> list[dict]:
        if self._cat is None:
            self._cat = self.fetch.json(self.cfg["url"], self.cfg["ttl_days"]).get(
                "schemas", []
            )
        k = norm(keyword)
        hits = []
        for s in self._cat:
            name, desc = s.get("name") or "", s.get("description") or ""
            url = s.get("url") or ""
            n = norm(name)
            # Catalog names are product names, so single words ("store") collide constantly:
            # single-word keywords must match a whole name; multi-word ones may match within one.
            if n == k:
                m = "exact"
            elif " " in k and re.search(rf"(^| ){re.escape(k)}( |$)", n):
                m = "label"
            else:
                continue
            if ":" in url:
                hits.append((m, name, desc, url))
        order = {"exact": 0, "label": 1, "text": 2}
        hits.sort(key=lambda h: (order[h[0]], len(h[1])))
        return [
            {
                "source": "schemastore",
                "ontology": "schemastore",
                "iri": url,
                "label": name,
                "kind": "schema",
                "definition": desc or None,
                "keyword": keyword,
                "match": m,
                "rank": i,
                "score": score(m, i, prior("schemastore")),
            }
            for i, (m, name, desc, url) in enumerate(hits[: self.cfg["max"]])
        ]
