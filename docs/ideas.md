# Ideas

> **Status legend:** ✅ Done · ⏳ Planned · 💡 Idea
---
## Open Ideas

### GitHub Pages — AVM Intelligence Portal

Full interactive portal auto-published on every `sync`/`check` run via GitHub Actions.

| Page | Content |
|---|---|
| Home | Catalog stats: modules by type/domain, catalog growth trend |
| Module Catalog | Searchable, filterable table with analysis scores and provider currency |
| Quality Scoreboard | Per-module pass/fail heatmap across all 7 dimensions; leaderboard |
| Provider Currency | Findings by provider/criticality; critical/high findings with module links |
| Resource Explorer | Treemap of resource types by provider, sized by module usage |
| Known Issues | `enrichment.known_issues` + `module_issues` aggregated; kanban by severity |
| Activity Feed | Commit heatmap per module over last 90 days |

**Tech:** `generate_site.py` extended (currently generates a single `docs/site/index.html`); future multi-page output with [Observable Plot](https://observablehq.com/plot/) charts, [Pagefind](https://pagefind.app/) search, GitHub Actions deploy to `gh-pages`.

### GitHub Projects Integration

Sync findings to GitHub Issues + a Project board so they become trackable, assignable work items.

- `scripts/sync_issues.py` — reads `enrichment.known_issues` (open), `analysis_*` failures, and `provider_updates` critical/high findings → creates/updates GitHub Issues with labels (`domain:networking`, `criticality:high`, `module:avm-res-network-virtualnetwork`, etc.)
- Issues added to a Project board: **Triage → Operator: Bulk Fix → Assistant: Agent Fix → Blocked → Done**
- Closing an issue marks the corresponding YAML entry resolved on next sync
- CLI: `./avm.sh issues sync` / `./avm.sh issues close --domain networking --criticality low`

### Schema Refactoring — Shared Definitions

The three module schemas (`avm-module-{res,ptn,utl}.schema.json`) duplicate ~10 `$defs` (analysis dimensions, enrichment blocks, known_issue, note, owners, terraform_constraints, etc.). Any shared def change must be applied to all three files.

**Recommended approach (Option B):** Code-generate all three from `scripts/generate_schemas.py` with a shared definitions dict + per-type overrides. Schemas remain committed and self-contained; consumers (VS Code, CI) need no changes.

> Priority: low — worth doing once the schema fully stabilises.
