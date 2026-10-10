#!/usr/bin/env bash
# Symlink methodology rules/skills/agents into ~/.claude. Dry run by default.
# Never overwrites an existing path; reports conflicts instead.
set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dst="${CLAUDE_HOME:-$HOME/.claude}"
apply=0
[[ "${1:-}" == "--apply" ]] && apply=1

link() { # link <source> <target>
  local s="$1" t="$2"
  if [[ -L "$t" && "$(readlink "$t")" == "$s" ]]; then echo "ok        $t"; return; fi
  if [[ -e "$t" || -L "$t" ]]; then echo "CONFLICT  $t (exists; skipped)"; return; fi
  echo "link      $t -> $s"
  if (( apply )); then mkdir -p "$(dirname "$t")"; ln -s "$s" "$t"; fi
}

for f in "$src"/rules/*.md;        do link "$f" "$dst/rules/nim-$(basename "$f")"; done
for d in "$src"/skills/*/;         do d="${d%/}"; link "$d" "$dst/skills/$(basename "$d")"; done
for f in "$src"/agents/*.md;       do link "$f" "$dst/agents/$(basename "$f")"; done

echo
echo "Manual steps:"
echo "  1. Add to $dst/CLAUDE.md:   @$src/constitution.md"
echo "  2. Merge $src/settings.fragment.json into $dst/settings.json"
(( apply )) || echo "(dry run; re-run with --apply)"
