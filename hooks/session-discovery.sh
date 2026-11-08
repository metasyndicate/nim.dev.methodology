#!/usr/bin/env bash
# SessionStart hook: make the discovery bundle part of every session's context.
#   bundle present  -> inject BUNDLE.md (bounded) as the data-design authority
#   skip file       -> inject the recorded reason
#   project, none   -> inject a directive to run the discovery skill first
#   not a project   -> nothing
# Reads the hook JSON from stdin (uses .cwd). Always exits 0: context, never a block.
set -uo pipefail

input="$(cat)"
cwd="$(printf '%s' "$input" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd",""))
except Exception: print("")' 2>/dev/null)"
[[ -n "$cwd" && -d "$cwd" ]] || cwd="$PWD"

root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$root" ]] || { [[ -f "$cwd/AGENTS.md" ]] && root="$cwd"; }
[[ -n "$root" ]] || exit 0

bundle="$root/.nim/discovery/BUNDLE.md"
skip="$root/.nim/discovery.skip"
max="${NIM_DISCOVERY_CONTEXT_BYTES:-8000}"

if [[ -r "$bundle" ]]; then
  ctx="Discovery bundle for this project (${bundle#"$root"/}). It is the authority for data design:
cite its entity IRIs, extend it rather than inventing parallel terms, and record deviations as decisions.

$(head -c "$max" "$bundle")"
elif [[ -r "$skip" ]]; then
  ctx="Discovery phase skipped for this project: $(head -c 400 "$skip")"
else
  ctx="No discovery bundle in this project (.nim/discovery/). Before modeling or editing schemas,
run the 'discovery' skill (phase 0): nim.discovery run \"<request>\" -k \"<keywords>\" -p <profile>.
If discovery does not apply, record why in .nim/discovery.skip."
fi

python3 -c 'import sys,json
print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":sys.argv[1]}}))' "$ctx"
exit 0
