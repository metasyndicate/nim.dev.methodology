---
name: ontology-lookup
description: Choose benchmark ontologies/standards for a single concept or data model detail. Use when naming entities, designing a schema, or justifying a modeling decision that the project's discovery bundle does not already cover.
---

# ontology-lookup

1. Check `.nim/discovery/BUNDLE.md` first; if the concept is there, use that term.
2. Otherwise search mechanically, not from memory:
   `nim.discovery -o /tmp/lookup run "<concept>" -k "<concept>, <synonym>"` and read its
   candidates/selection, or browse `/usr/local/nim/dev/ontology/map.md` for curated tags.
3. Pick the top-level (BFO) classification first (continuant vs occurrent), then the domain term.
4. Fetch exact class/relation names and IRIs from the source; never rely on memory for them.
5. Report: `concept | benchmark term | IRI | source | fit (exact/partial/none) | decision`.
6. For `none`, state "no benchmark; assumption: X" and proceed. If the concept is
   project-wide, add it to the bundle (`request.json` keywords, then `nim.discovery search`).
