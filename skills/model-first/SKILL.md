---
name: model-first
description: Model-driven build procedure (model -> schema -> spec -> facade -> code). Use when starting a new component, feature, interface, or data structure, or when a request touches data shape, API, or CLI surface.
---

# model-first

Follow in order. Do not skip ahead; stop and report at each gate.

1. **Scope and rigor.** Restate the request. Identify the highest-level interface involved. State the rigor level (`loose` / `standard` / `rigorous`; default `standard`).
2. **Conceptual.** Name the entities, relations, flows. Look up benchmark terms (use the `ontology-lookup` skill). Record each mapping or "no benchmark; assumption: X".
3. **Schema.** Draft the schema/subschema (entities, relations, constraints). Show it. Gate: confirm before proceeding if rigor is `rigorous` or the schema is shared.
4. **Spec.** Define the interface over the schema: parameters, commands, API paths, flows.
5. **Facade.** Generate or hand-write the typed interfaces/classes from the schema; no divergent definitions.
6. **Implement bottom-up.** Lower tiers first (see `~/Developer/methodology/ontology/layers.md`), then the target interface.
7. **Verify.** Run the project's checks; validate sample data against the schema (valid and invalid cases).
8. **Record.** Summarize decisions with their authorities and list open assumptions.

Output at each step: the artifact plus one line stating which gate you are at.
