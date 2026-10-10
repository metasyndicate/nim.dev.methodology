---
name: ontology-lookup
description: Choose benchmark ontologies/standards for a concept or data model. Use when naming entities, designing a schema, or justifying a modeling decision.
---

# ontology-lookup

1. Read `~/Developer/methodology/ontology/map.md`.
2. Match the concept to tags by scope and keywords. Pick the top-level (BFO) classification first (continuant vs occurrent), then the domain ontology.
3. Fetch the relevant class/relation names from the source if needed; do not rely on memory for exact terms or IRIs.
4. Report a table: `concept | benchmark term | source | fit (exact/partial/none) | decision`.
5. For `none`, state "no benchmark; assumption: X" and proceed.
