---
paths:
  - "**/*.py"
---

# Python

- Target current stable Python; stdlib first; justify each third-party dependency.
- Type hints on all public functions. `pathlib` over `os.path`. No mutable globals.
- All external input (files, env, CLI, network) is validated against its schema at the boundary.
- Data definitions live in the schema/data layer, not hard-coded in modules.
- CLI via `argparse` (or the project's chosen framework); stable exit codes; `logging`, not `print`, for diagnostics.
- Cross-platform: no hard-coded separators or shell-isms; guard platform-specific code.
- Format and lint with `ruff` when available (the validate hook runs it).
- Match the surrounding module's comment density and naming.
