---
name: discovery
description: Preliminary discovery phase (phase 0). Turns a stated idea or work request into an ontology/standards-grounded referential bundle (.nim/discovery/) before any modeling. Use at the start of every project or data-design task, when no bundle exists, or when the request's concepts change.
---

# discovery

Runs before `model-first`. Output is the authority that model-first step 2 cites.
Engine: `/usr/local/nim/discovery/bin/nim.discovery` (stdlib python; see its README).

1. **Frame.** Restate the request in one sentence. Pick rigor (`loose`/`standard`/`rigorous`)
   and profile (`default`, `nim` for infra/software/bio/org work, `bio`).
2. **Keywords.** Write 5-12 domain nouns and noun phrases yourself: entities and processes,
   singular, no verbs or filler ("sample", "assay run", "research group"). Prefer this over
   extraction; preview extraction with `nim.discovery keywords "<request>"` if unsure.
3. **Run.**
   `nim.discovery run "<request>" -k "<k1, k2, ...>" -p <profile> -r <rigor>`
4. **Review selection** (`.nim/discovery/BUNDLE.md`). For each selected ontology ask: is it a
   real authority for this domain, or did it win on coverage alone? Adjust and re-run:
   `--pin <id>` / `--exclude <id>` (or edit `request.json`, then `nim.discovery search`).
   Unresolved keywords: rephrase/widen once; otherwise they stay "no benchmark; assumption".
5. **Gate.** Show the user: selected ontologies, entity table, unresolved keywords.
   Confirm before modeling when rigor is `rigorous` or the model is shared.
6. **Hand off.** `nim.discovery check` must print `ok`. Then follow `model-first`, citing
   entity IRIs from `baseline.model.json`; seed JSON/DDL design from `baseline.schema.json`.
   Record accepted/rejected entries as decisions in the project's ADRs or charter.

Skip only with a reason: write it to `.nim/discovery.skip` (one line), e.g. "pure refactor,
no data shape change". The schema-edit hook accepts that file instead of a bundle.
