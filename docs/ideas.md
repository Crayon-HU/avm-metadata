# Ideas

> **Status legend:** ✅ Done · ⏳ Planned · 💡 Idea

---

## Architecture Reference

### Issues & Changelog Data

Four distinct tracking keys — each has a unique location, source, and command:

| # | Key | Location | Source | Command | Status |
|---|---|---|---|---|---|
| 1 | `enrichment.known_issues` | `data/modules/*.yaml` | Hand-typed by operator | `avm report --issues` / `/avm-issues` | ✅ |
| 2 | `module_issues` | `data/modules/*.yaml` | AVM module GitHub issues | `avm harvest` | ✅ |
| 3 | `provider_issues` | `data/{resources,datasources,…}/*.yaml` | Terraform provider GitHub issues | `avm providers --mode issues` | ✅ |
| 4 | `provider_updates` | `data/{resources,datasources,…}/*.yaml` | Terraform provider GitHub Releases | `avm providers` | ✅ |

> `/avm-issues` reads `enrichment.known_issues` only (hand-curated). Shows 0 on a fresh repo — correct.

### Analysis Dimensions (7)

| Shorthand | Dimension | YAML block | Status |
|---|---|---|---|
| `metadata` | `terraform-metadata` | `analysis_terraform_metadata` | ✅ |
| `compliance` | `avm-interface-compliance` | `analysis_avm_interface_compliance` | ✅ |
| `security` | `security-hardening` | `analysis_security_hardening` | ✅ |
| `tests` | `test-coverage` | `analysis_test_coverage` | ✅ |
| `docs` | `doc-quality` | `analysis_doc_quality` | ✅ |
| `deps` | `dependency-health` | `analysis_dependency_health` | ✅ |
| `currency` | `provider-currency` | `analysis_provider_currency` | ✅ |

---

## Open Ideas

### Visualization

- 💡 **Domain coverage heatmap** — show which domains have fresh analysis data and which are gaps; expose as a dashboard panel in `generate_site.py`
- 💡 **Owner map** — who owns what across all modules; highlight modules with no secondary owner

### Enrichment Automation

- 💡 **Use-case tagging** — infer `enrichment.use_cases` from `analysis_terraform_metadata.resources_managed` using a lookup table (e.g. `azurerm_key_vault` → `"security"`, `azurerm_virtual_network` → `"networking"`)
- 💡 **Multi-repo CHANGELOG** — aggregate recent commits across a domain into a weekly digest (feed from `avm activity`)

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
