---
paths:
  - "**/*.schema.json"
  - "**/schema/**"
  - "**/schemas/**"
  - "**/*.linkml.yaml"
  - "**/*.shacl.ttl"
---

# Schema / data layer

- The schema is the single source of truth. Change it first; code follows.
- Declare the dialect/version (`$schema` for JSON Schema). Give every schema an `$id` and `title`.
- Names align to a benchmark ontology term where one fits; otherwise note "no benchmark" in the description.
- Every property has a type and a description; mark `required` explicitly; set `additionalProperties` deliberately.
- Reuse via `$ref`/subschemas; no duplicated definitions.
- Version schemas; breaking changes bump the major version and are noted in the change description.
- Provide at least one valid and one invalid example per schema where tooling allows.
