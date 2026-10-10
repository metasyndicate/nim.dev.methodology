# methodology

Project-agnostic, model-driven development conventions for assisted (agent) development.
Applies to any `nim.*` project, or any dev work by default. **Contains no project specifics**;
those belong in each project's own `AGENTS.md` (see `templates/AGENTS.project.md`).

## Layers (most to least deterministic)

| Layer | File(s) | Applied |
|---|---|---|
| Hooks | `hooks/`, `settings.fragment.json` | Deterministically, by the harness |
| Constitution | `constitution.md` | Always (imported from `~/.claude/CLAUDE.md`) |
| Rules | `rules/*.md` (`paths:` globs) | Implicitly, when matching files are touched |
| Skills | `skills/*/SKILL.md` | On demand, as procedures |
| Subagents | `agents/*.md` | Delegated, read-only personas |
| Reference | `ontology/` | Looked up per task, never preloaded |

## Install (symlinks, nothing copied, one source of truth)

```
./install.sh            # dry run: prints what it would link
./install.sh --apply    # links rules/skills/agents into ~/.claude, never overwrites
```

Then add one line to `~/.claude/CLAUDE.md`:

```
@~/Developer/methodology/constitution.md
```

And merge `settings.fragment.json` into `~/.claude/settings.json` (hooks).

## Layout

```
constitution.md          principles, build order, layers, tiers, rigor dial
ontology/map.md          working ontology map (lookup per task)
ontology/layers.md       layer + tier + language-allocation tables
rules/                   python.md  shell.md  schema.md
skills/model-first/      model -> schema -> spec -> facade procedure
skills/ontology-lookup/  pick a benchmark ontology for a concept
agents/                  architect.md  reviewer.md
hooks/validate.sh        post-edit format/lint/schema check (skips absent tools)
templates/               AGENTS.project.md  (per-project charter)
```

## Roadmap (not yet stubbed)

- Rules: powershell, c++, swift, web (php/html/css/js)
- Skills: spec-review, adr, new-component
- Agents: schema-steward
- Schema tooling decision (LinkML vs JSON Schema vs SHACL) recorded as an ADR
