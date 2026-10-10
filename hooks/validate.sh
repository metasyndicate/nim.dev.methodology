#!/usr/bin/env bash
# PostToolUse hook (Edit|Write|MultiEdit): format/lint/validate the edited file.
# Reads the hook JSON from stdin. Skips silently when a tool is absent.
# Exit 2 + stderr feeds failures back to the agent; exit 0 otherwise.
set -uo pipefail

input="$(cat)"
file="$(printf '%s' "$input" | python3 -c 'import sys,json
try:
    d=json.load(sys.stdin); print(d.get("tool_input",{}).get("file_path",""))
except Exception:
    print("")' 2>/dev/null)"

[[ -n "$file" && -f "$file" ]] || exit 0

fail=0
run() { # run <label> <cmd...>; capture output, report on failure
  local label="$1"; shift
  local out
  if ! out="$("$@" 2>&1)"; then
    printf '[validate:%s] %s\n%s\n' "$label" "$file" "$out" >&2
    fail=1
  fi
}
have() { command -v "$1" >/dev/null 2>&1; }

case "$file" in
  *.py)
    if have ruff; then run ruff-format ruff format "$file"; run ruff-check ruff check "$file"; fi
    ;;
  *.sh|*.bash)
    if have shellcheck; then run shellcheck shellcheck "$file"; fi
    run bash-syntax bash -n "$file"
    ;;
  *.json)
    run json-syntax python3 -m json.tool "$file" /dev/null
    ;;
  *.yaml|*.yml)
    python3 -c 'import yaml' 2>/dev/null && run yaml-syntax python3 -c 'import sys,yaml; yaml.safe_load(open(sys.argv[1]))' "$file"
    ;;
esac

# Schema validation hook point: if "<name>.schema.json" sits beside a "<name>.json", validate it.
if [[ "$file" == *.json && "$file" != *.schema.json ]]; then
  schema="${file%.json}.schema.json"
  if [[ -f "$schema" ]] && python3 -c 'import jsonschema' 2>/dev/null; then
    run json-schema python3 -c 'import sys,json,jsonschema
jsonschema.validate(json.load(open(sys.argv[1])), json.load(open(sys.argv[2])))' "$file" "$schema"
  fi
fi

[[ $fail -eq 0 ]] || exit 2
exit 0
