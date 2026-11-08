"""Offline tests: keywords, matching, selection, merge, schema conformance. Run:
python3 -m unittest discover -s tests
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))

from discovery import keywords as kw
from discovery.merge import merge, to_json_schema
from discovery.select import select
from discovery.sources import classify_match
from discovery.validate import validate

REQ = {
    "text": "org hierarchy",
    "keywords": ["organization", "tree", "widget"],
    "extracted": False,
    "profile": "default",
    "rigor": "standard",
    "pin": [],
    "exclude": [],
    "max_ontologies": 5,
    "created": "2026-11-07T00:00:00+00:00",
}


def cand(ont, iri, label, k, match="exact", kind="class", score=1.0):
    return {
        "source": "schemaorg" if ont == "schemaorg" else "ols",
        "ontology": ont,
        "iri": iri,
        "label": label,
        "kind": kind,
        "definition": None,
        "keyword": k,
        "match": match,
        "rank": 0,
        "score": score,
    }


class FakeSO:
    def expand(self, c):
        return "https://schema.org/" + c.split(":", 1)[1]

    def parents(self, iri):
        return [{"iri": "https://schema.org/Thing", "label": "Thing"}]

    def equivalents(self, iri):
        return [
            {
                "iri": "http://www.w3.org/ns/org#Organization",
                "ontology": "org",
                "label": None,
                "relation": "skos:exactMatch",
                "basis": "owl:equivalentClass in schema.org",
            }
        ]

    def attributes(self, iri):
        return [
            {
                "id": "schema:parentOrganization",
                "iri": "https://schema.org/parentOrganization",
                "name": "parentOrganization",
                "definition": "parent",
                "ranges": ["schema:Organization"],
                "superseded": False,
            },
            {
                "id": "schema:foundingDate",
                "iri": "https://schema.org/foundingDate",
                "name": "foundingDate",
                "definition": "date",
                "ranges": ["schema:Date"],
                "superseded": False,
            },
        ]


class FakeOLS:
    def ancestors(self, ont, iri):
        return [
            {
                "iri": "http://purl.obolibrary.org/obo/BFO_0000002",
                "label": "continuant",
            },
            {"iri": "http://purl.obolibrary.org/obo/CDAO_0000006", "label": "Network"},
        ]


CANDS = [
    cand(
        "schemaorg", "https://schema.org/Organization", "Organization", "organization"
    ),
    cand(
        "sio",
        "http://semanticscience.org/resource/SIO_000012",
        "organization",
        "organization",
        score=0.9,
    ),
    cand("cdao", "http://purl.obolibrary.org/obo/CDAO_0000110", "Tree", "tree"),
    cand(
        "noise",
        "http://example.org/x",
        "Widget recall notice",
        "widget",
        match="text",
        score=0.3,
    ),
]


class Keywords(unittest.TestCase):
    def test_bigrams_do_not_cross_punctuation(self):
        k = kw.extract("track customer orders, invoices and payments")
        self.assertIn("customer order", k)
        self.assertNotIn("order invoice", k)
        self.assertIn("invoice", k)

    def test_generic_qualifier_leads_bigram(self):
        self.assertIn("data lineage", kw.extract("data lineage for pipelines"))

    def test_explicit(self):
        self.assertEqual(
            kw.parse_explicit(["Orders, Research Groups", "tree"]),
            ["order", "research group", "tree"],
        )


class Matching(unittest.TestCase):
    def test_match_classes(self):
        self.assertEqual(classify_match("customer order", "CustomerOrders"), "exact")
        self.assertEqual(classify_match("order", "Order Status"), "label")
        self.assertEqual(
            classify_match(
                "research group",
                "Cancer and Aging Research Group Chemo Toxicity Calculator",
            ),
            "text",
        )


class Selection(unittest.TestCase):
    def test_greedy_cover_ignores_text_hits(self):
        sel = select(CANDS, REQ, lambda o: 1.0)
        picked = [o["id"] for o in sel["ontologies"] if o["selected"]]
        self.assertEqual(
            set(picked), {"schemaorg", "cdao"}
        )  # sio adds no gain; noise is text-only
        self.assertEqual(sel["uncovered"], ["widget"])
        self.assertEqual(validate(sel, "selection"), [])

    def test_pin_and_exclude(self):
        sel = select(
            CANDS, {**REQ, "pin": ["sio"], "exclude": ["schemaorg"]}, lambda o: 1.0
        )
        picked = [o["id"] for o in sel["ontologies"] if o["selected"]]
        self.assertEqual(picked[0], "sio")
        self.assertNotIn("schemaorg", picked)


class Merge(unittest.TestCase):
    def setUp(self):
        sel = select(CANDS, REQ, lambda o: 1.0)
        self.model = merge(
            REQ,
            CANDS,
            sel,
            {"schemaorg": FakeSO(), "ols": FakeOLS()},
            {
                "continuant": ["http://purl.obolibrary.org/obo/BFO_0000002"],
                "occurrent": [],
            },
        )

    def test_model_valid(self):
        self.assertEqual(validate(self.model, "baseline"), [])

    def test_entities_mappings_upper(self):
        e = {x["name"]: x for x in self.model["entities"]}
        self.assertEqual(set(e), {"Organization", "Tree"})
        self.assertEqual(e["Tree"]["upper"], "continuant")
        rels = {m["relation"] for m in e["Organization"]["mappings"]}
        self.assertEqual(rels, {"skos:exactMatch"})  # sio not selected -> no closeMatch
        self.assertEqual(self.model["unresolved"], ["widget"])

    def test_self_relation_and_json_schema(self):
        self.assertIn(
            ("Organization", "parentOrganization", "Organization"),
            {(r["from"], r["name"], r["to"]) for r in self.model["relations"]},
        )
        js = to_json_schema(self.model)
        props = js["$defs"]["Organization"]["properties"]
        self.assertEqual(props["parentOrganization"]["$ref"], "#/$defs/Organization")
        self.assertEqual(
            props["foundingDate"],
            {
                "type": "string",
                "description": "date",
                "x-iri": "https://schema.org/foundingDate",
                "format": "date",
            },
        )


class Validator(unittest.TestCase):
    def test_rejects_bad_candidate(self):
        bad = cand("x", "not an iri", "X", "Bad Keyword", match="fuzzy")
        errs = validate(bad, "candidate")
        self.assertTrue(any("iri" in e for e in errs))
        self.assertTrue(any("keyword" in e for e in errs))
        self.assertTrue(any("match" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
