---
paths:
  - "**/*.sh"
  - "**/*.bash"
---

# Shell (bash)

- Start with `set -euo pipefail` in executable scripts; libraries meant to be sourced must not change shell options.
- Quote every expansion. Prefer `[[ ]]`, `$(...)`, and arrays. No parsing of `ls`.
- Portability: avoid bash 4+ features unless the project states a floor (macOS ships bash 3.2).
- Read structured data with `jq` from the shared data layer rather than duplicating constants.
- Functions are namespaced by module; no leaking of globals.
- Must pass `shellcheck` when available (the validate hook runs it).
- If a python counterpart exists, behavior must match; the schema/data layer is authoritative.
