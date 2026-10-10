# Layers, Tiers, Languages

## Model layers

| Layer | Scope | Intent | Benchmark | Output |
|---|---|---|---|---|
| `CONCEPTUAL` | Ontology, models, published specs | Semantic benchmark | BFO, SEON, EDAM (see `map.md`) | ERD, OSI, hierarchical prose |
| `SCHEMA` | Entities, relations, flows | Integrity, validation | SHACL / OWL / JSON Schema | schema / metaschema / subschema |
| `SPEC` | API | Interface components and flows | process, procedural, UI, data flow | OpenAPI or equivalent |
| `FACADE` | Generated interfaces, classes, forms | Prototype interfaces | generators from schema | classes, DTOs, forms |

Bridging idea: author the model once in a language-agnostic form (candidate: LinkML, or
JSON Schema at `loose`/`standard`), then generate per-language facades. Tool choice is open;
record it as an ADR when decided.

## Interface tiers

| Tier | Description | Language |
|---|---|---|
| `PROGRAMMATIC` | Raw modules/methods; singular data access and CRUD flow | python |
| `API` | Schematized interface for remote interop and automation | json, http(s), html |
| `COMMAND` | CLI scripts, functions, automation | python, bash, powershell, perl |
| `WEB` | Portable graphical interface, web host/middleware | php, html, css, javascript |
| `DESKTOP` | Local GUI on macOS/Linux/Windows | c++, swift, c#, python |
| `MOBILE` | Distributed apps for small devices | swift |

Rule: build lower tiers before higher ones.

## Language allocation by target

| Target | Order of preference |
|---|---|
| Systems automation, ops, admin CLI/utilities/libraries | python, bash, powershell |
| Scientific computing | c++ |
| Mobile applications | swift |
| Web applications | php, html, css, javascript |

Operational scripts may favor bash, but portability wins: python is the default unless the
project says otherwise.

## Facade generation by target (candidates, not decisions)

| Target | loose | rigorous | facade |
|---|---|---|---|
| Systems ops | YAML / JSON Schema | LinkML or SHACL | pydantic/dataclasses; jq or native cmdlets for bash/ps |
| Scientific (c++) | structs | Protocol Buffers | protoc-generated classes |
| Mobile (swift) | JSON / plists | SwiftData models from ERD | Codable structs from schema |
| Web | JSON | relational DDL / OpenAPI | DTOs (php), TypeScript/Zod (js) |
