"""Merge: selected ontologies' best terms -> one baseline model, with crosswalks.

Per keyword, the best exact/label hit from a selected ontology wins (classes become
entities; properties/individuals become vocabulary). Same-label hits in the other selected
ontologies become skos:closeMatch mappings; schema.org's owl:equivalent* links become
skos:exactMatch. Hierarchy (parents, BFO upper category) comes from the source itself.
"""

from __future__ import annotations

from .sources import XSD_LIKE
from .util import camel, norm, now, pascal, slug

ORDER = {"exact": 0, "label": 1, "text": 2}


def _best(cands: list[dict]) -> dict | None:
    good = [c for c in cands if c["match"] in ("exact", "label")]
    if not good:
        return None
    return sorted(
        good, key=lambda c: (ORDER[c["match"]], c["kind"] != "class", -c["score"])
    )[0]


def merge(
    request: dict,
    candidates: list[dict],
    selection: dict,
    adapters: dict,
    upper_cfg: dict,
) -> dict:
    selected = [o["id"] for o in selection["ontologies"] if o["selected"]]
    pool = [
        c for c in candidates if c["ontology"] in selected and c["kind"] != "schema"
    ]
    by_kw: dict[str, list[dict]] = {}
    for c in pool:
        by_kw.setdefault(c["keyword"], []).append(c)

    entities: dict[str, dict] = {}  # iri -> entity
    vocabulary, unresolved, decisions = [], [], []
    for k in request["keywords"]:
        b = _best(by_kw.get(k, []))
        if b is None:
            unresolved.append(k)
            decisions.append(
                {
                    "subject": k,
                    "decision": "no benchmark term in selected ontologies; model as a project-local concept or widen search",
                    "authority": "no benchmark; assumption",
                    "status": "proposed",
                }
            )
            continue
        if b["kind"] != "class":
            if b["iri"] not in {v["iri"] for v in vocabulary}:
                vocabulary.append(b)
            continue
        if b["iri"] in entities:
            continue
        entities[b["iri"]] = {
            "name": pascal(b["label"]),
            "iri": b["iri"],
            "ontology": b["ontology"],
            "label": b["label"],
            "definition": b.get("definition"),
            "keyword": k,
            "upper": None,
            "parents": [],
            "mappings": [],
            "attributes": [],
        }

    _dedupe_names(entities)
    ent_by_iri = {e["iri"]: e for e in entities.values()}
    relations: list[dict] = []
    so, ols = adapters.get("schemaorg"), adapters.get("ols")
    kw_norm = {norm(k) for k in request["keywords"]}
    upper_iris = {iri: cat for cat, iris in upper_cfg.items() for iri in iris}

    for e in entities.values():
        # crosswalk: same normalized label elsewhere in the selection
        for c in pool:
            if (
                c["iri"] != e["iri"]
                and c["kind"] == "class"
                and norm(c["label"]) == norm(e["label"])
            ):
                if c["iri"] not in {m["iri"] for m in e["mappings"]}:
                    e["mappings"].append(
                        {
                            "iri": c["iri"],
                            "ontology": c["ontology"],
                            "label": c["label"],
                            "relation": "skos:closeMatch",
                            "basis": "same normalized label",
                        }
                    )
        if e["ontology"] == "schemaorg" and so:
            e["parents"] = so.parents(e["iri"])
            e["mappings"] += so.equivalents(e["iri"])
            for a in so.attributes(e["iri"]):
                if a["superseded"]:
                    continue
                targets = [so.expand(r) for r in a["ranges"]]
                # self-references stay: parentOrganization/subOrganization are how hierarchies are modeled
                ents = [ent_by_iri[t] for t in targets if t in ent_by_iri]
                for t in ents:
                    relations.append(
                        {
                            "name": a["name"],
                            "iri": a["iri"],
                            "from": e["name"],
                            "to": t["name"],
                            "definition": a["definition"],
                            "cardinality": None,
                        }
                    )
                dtypes = [XSD_LIKE[r] for r in a["ranges"] if r in XSD_LIKE]
                e["attributes"].append(
                    {
                        "name": a["name"],
                        "iri": a["iri"],
                        "type": dtypes[0] if dtypes else "object",
                        "range": targets,
                        "definition": a["definition"],
                        "relevant": norm(a["name"]) in kw_norm
                        or any(w in kw_norm for w in norm(a["name"]).split()),
                    }
                )
        elif ols:
            anc = ols.ancestors(e["ontology"], e["iri"])
            for t in anc:
                if t["iri"] in upper_iris:
                    e["upper"] = upper_iris[t["iri"]]
            e["parents"] = [t for t in anc if t["iri"] not in upper_iris][:8]
        for p in e["parents"]:
            if p["iri"] in ent_by_iri:
                relations.append(
                    {
                        "name": "subClassOf",
                        "iri": "http://www.w3.org/2000/01/rdf-schema#subClassOf",
                        "from": e["name"],
                        "to": ent_by_iri[p["iri"]]["name"],
                        "definition": "taxonomic parent (from source)",
                        "cardinality": None,
                    }
                )
        decisions.append(
            {
                "subject": e["name"],
                "decision": f"adopt '{e['label']}' ({e['ontology']}) as entity for keyword '{e['keyword']}'",
                "authority": e["iri"],
                "status": "proposed",
            }
        )

    return {
        "id": f"urn:nim:discovery:{slug(request['text'])}:baseline",
        "title": f"Baseline model: {request['text'][:80]}",
        "generated": now(),
        "rigor": request["rigor"],
        "keywords": request["keywords"],
        "ontologies": selected,
        "entities": list(entities.values()),
        "relations": relations,
        "vocabulary": vocabulary,
        "unresolved": unresolved,
        "decisions": decisions,
    }


def _dedupe_names(entities: dict[str, dict]) -> None:
    seen: dict[str, int] = {}
    for e in entities.values():
        n = e["name"] or "Entity"
        if n in seen:
            seen[n] += 1
            e["name"] = f"{n}{pascal(e['ontology'])}"
        else:
            seen[n] = 1


FORMATS = {
    "date": ("string", "date"),
    "date-time": ("string", "date-time"),
    "time": ("string", "time"),
    "uri": ("string", "uri"),
}


def to_json_schema(model: dict) -> dict:
    """Baseline model -> JSON Schema 2020-12 ($defs per entity), annotated with source IRIs.
    Deliberately permissive (no `required`, additionalProperties true): it is a starting point for
    data design, not the design. Relations become $ref; cardinality is left to design."""
    defs = {}
    rels: dict[str, list[dict]] = {}
    for r in model["relations"]:
        if r["name"] != "subClassOf":
            rels.setdefault(r["from"], []).append(r)
    for e in model["entities"]:
        props = {}
        for a in e["attributes"]:
            if a["name"] in {r["name"] for r in rels.get(e["name"], [])}:
                continue
            t, fmt = FORMATS.get(a["type"], (a["type"], None))
            p = {
                "type": t,
                "description": a.get("definition") or "",
                "x-iri": a.get("iri"),
            }
            if fmt:
                p["format"] = fmt
            if t == "object":
                p = {
                    "description": (a.get("definition") or "")
                    + f" Range: {', '.join(a.get('range', []))}",
                    "x-iri": a.get("iri"),
                }
            props[camel(a["name"])] = p
        for r in rels.get(e["name"], []):
            props[camel(r["name"])] = {
                "$ref": f"#/$defs/{r['to']}",
                "description": r.get("definition") or "",
                "x-iri": r.get("iri"),
                "x-cardinality": r.get("cardinality"),
            }
        d = {
            "type": "object",
            "title": e["label"],
            "description": e.get("definition") or "",
            "x-iri": e["iri"],
            "x-ontology": e["ontology"],
            "x-upper": e.get("upper"),
            "x-mappings": [m["iri"] for m in e["mappings"]],
            "properties": props,
            "additionalProperties": True,
        }
        parents = [
            r["to"]
            for r in model["relations"]
            if r["name"] == "subClassOf" and r["from"] == e["name"]
        ]
        if parents:
            d["allOf"] = [{"$ref": f"#/$defs/{p}"} for p in parents]
        defs[e["name"]] = d
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": model["id"].replace(":baseline", ":baseline.schema"),
        "title": model["title"],
        "description": "Generated by nim.discovery from the baseline model. Permissive by design: add required, keys, cardinality, and constraints during data design.",
        "$defs": defs,
    }
