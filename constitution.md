# Development Constitution

Applies to all work unless a project `AGENTS.md` narrows it. Imperative, short, by design.

## Principles

1. Follow established patterns and conventions. Match the surrounding code before inventing.
2. Work step by step. State the step, do it, verify it.
3. Assume nothing. Every design decision maps to an authority: an ontology, standard,
   specification, published model, or best-in-class pattern. If none applies, say
   "no benchmark; assumption: X" explicitly. Never present an assumption as a fact.
4. Single source of truth. Define a thing once (schema/data layer); derive everything else.
5. Least privilege. Minimal permissions, minimal scope, minimal surface.
6. Referential and data integrity. Validate at boundaries; no orphan references.
7. Design for generality, extensibility, portability. Python is the portable default.
8. Decompose into layers; keep boundaries clean; group like with like.

## Build order (bottom-up)

Do not build a layer before the ones beneath it exist.

`model -> schema -> spec -> facade -> mux -> modules -> methods -> parameters -> interface -> commands -> forms -> configuration`

For any request: (1) identify the highest-level interface involved, (2) build every lower
interface first, (3) map each programmatic unit to a schema, subschema, or data-layer construct.

## Rigor dial

State the level at the start of a project or task; default is `standard`.

| Level | Schema authority | Typical use |
|---|---|---|
| `loose` | Inline JSON/YAML, light validation | Scripts, spikes, personal tooling |
| `standard` | JSON Schema (or equivalent) is authoritative; code validates against it | Most work |
| `rigorous` | Conceptual/logical/physical models, ontology-aligned, SHACL/OWL where fitting | Shared infrastructure, scientific, enterprise |

## Reference material (load on demand, do not inline)

- Layers, tiers, language allocation: `~/Developer/methodology/ontology/layers.md`
- Ontology map: `~/Developer/methodology/ontology/map.md`

## Definition of done

- The schema/model change (if any) precedes and matches the code.
- Checks pass (format, lint, validation, tests as the project defines them).
- Decisions made are recorded with their authority or flagged as assumptions.
- No unrelated changes; no new dependencies without stating why.

## Conduct

- Prefer the smallest change that satisfies the request.
- Surface conflicts between this constitution and a project charter; the project wins on
  project specifics, this wins on principles. Ask when they truly collide.
- Confirm before irreversible or outward-facing actions.
