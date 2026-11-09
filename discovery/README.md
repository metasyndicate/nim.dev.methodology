# nim.discovery

Preliminary discovery for data design. A stated idea or work request becomes a
**referential bundle**: the standards and ontologies that cover its concepts, the
ones selected, and a merged, ontology-grounded **baseline model** that data design
(JSON ↔ DDL) starts from and cites.

```
request ─▶ keywords ─▶ search ─▶ select ─▶ merge ─▶ <project>/.nim/discovery/
 (text)   (-k or       (OLS4,     (greedy     (entities, relations,   BUNDLE.md
           extracted)   schema.org, weighted   crosswalk, BFO upper,  baseline.model.json
                        SchemaStore) set cover) JSON Schema seed)     baseline.schema.json
                                                                       selection.json
                                                                       candidates.jsonl
                                                                       manifest.json
```

Standalone subsystem: python3 stdlib engine (`lib/discovery`), a metashell module
(`discovery.sh`, registered via `nim.mod.register`), and a command (`bin/nim.discovery`).
No third-party dependencies; `jsonschema` is used for validation only if installed.

## Use

```bash
nim.discovery run "lab sample tracking with assays and instruments" \
    -k "sample, specimen, assay, instrument, laboratory" -p bio
nim.discovery show            # BUNDLE.md digest
nim.discovery check           # schema + sha256 integrity
```

Iterate without re-querying everything: edit `.nim/discovery/request.json`
(`keywords`, `pin`, `exclude`, `max_ontologies`) and run `nim.discovery search`, or edit
nothing and `nim.discovery select` / `merge`. A new `run` archives the previous bundle
under `.nim/discovery/history/`.

Global flags go before the command: `-o DIR`, `--offline` (cache only), `--refresh`.
Cache: `${NIM_DISCOVERY_CACHE:-~/.cache/nim/discovery}` (search 7 days, releases 30 days).

From a metashell session:

```bash
nim.mod.register /usr/local/nim/discovery
nim.fn.help nim.discovery.run
nim.discovery.run "<request>" -k "a, b, c" -p nim
```

## How it decides

| Stage | Rule | Authority |
|---|---|---|
| Keywords | Explicit `-k` wins. Extraction: stopword-filtered unigrams + bigrams that never span punctuation. | no benchmark; assumption: agent supplies better keywords than extraction |
| Match | `exact` = same normalized words (case, camel, plural); `label` = keyword inside a label ≤ 2 words longer; else `text` (kept as evidence, never drives decisions). | — |
| Score | match weight (1.0 / 0.6 / 0.3) × rank decay `1/(1+0.1·rank)` × profile prior (`etc/sources.json`). | — |
| Select | Greedy weighted set cover: add the ontology with the largest improvement over current best per keyword; pins first; stop at `-n` or gain < 0.5. Runners-up are listed. | set-cover approximation |
| Merge | Per keyword, best exact/label hit among selected ontologies; classes → entities, properties → vocabulary. Same-label terms in other selected ontologies → `skos:closeMatch`; schema.org `owl:equivalent*` → `skos:exactMatch`. | SKOS mapping properties |
| Upper | `continuant`/`occurrent` when the source's own ancestry reaches BFO; otherwise `?` for design to decide. | BFO |
| Attributes / relations | schema.org `domainIncludes`/`rangeIncludes`; ranges that are selected entities become relations (self-references kept for hierarchies). | schema.org |

## Sources

| Source | Coverage | Endpoint |
|---|---|---|
| OLS4 (EMBL-EBI) | ~270 ontologies incl. BFO, IAO, RO, SWO, EDAM, CDAO, OBI, SIO, NCIT | `ebi.ac.uk/ols4/api` |
| schema.org | current release, local index; equivalence links to DCAT, PROV, ORG, FIBO, GS1, UNECE | `schema.org/version/latest/...jsonld` |
| SchemaStore | published JSON Schemas for config/data formats | `schemastore.org/api/json/catalog.json` |

Not yet: LOV (its API returned HTML on 2026-11-07), BioPortal (needs an API key),
SEON (not in OLS). Add an adapter in `lib/discovery/sources.py` and a block in `etc/sources.json`.

## Layout

```
schema/bundle.schema.json   source of truth for every bundle file ($defs per file)
etc/sources.json            sources, BFO upper IRIs, prior profiles
lib/discovery/              util, validate, keywords, sources, select, merge, bundle, cli
discovery.sh, .nim/         metashell subsystem module + manifest
bin/nim.discovery           command
tests/                      offline unit tests: python3 -m unittest discover -s tests
```

## Install

```bash
ln -s ~/Developer/NIM/nim.discovery /usr/local/nim/discovery
ln -s /usr/local/nim/discovery/bin/nim.discovery ~/.local/bin/nim.discovery   # or anywhere on PATH
```
