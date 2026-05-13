# Ideas

> **Status legend:** ✅ Done · ⏳ Planned · 💡 Idea

---

## Issues & Changelog Data Architecture

Four distinct tracking keys — each has a unique location, source, and automation command:

| # | Key | File location | Source | Direction | Command |
|---|---|---|---|---|---|
| 1 | `enrichment.known_issues` | `data/modules/*.yaml` | **Hand-typed** by operator | n/a (read by `report --issues`, `/avm-issues`) | ✅ Done |
| 2 | `module_issues` | `data/modules/*.yaml` | GitHub issues on AVM module repos (`Azure/terraform-azurerm-avm-*`) | ⬇ pull | `avm harvest` 💡 |
| 3 | `provider_issues` | `data/{resources,datasources,…}/*.yaml` | GitHub issues on Terraform provider repos (`hashicorp/terraform-provider-azurerm`, `Azure/terraform-provider-azapi`) | ⬇ pull | `avm providers --mode issues` ✅ |
| 4 | `provider_updates` | `data/{resources,datasources,…}/*.yaml` | GitHub Releases / CHANGELOG of Terraform provider | ⬇ pull | `avm providers` ✅ |

**`/avm-issues` shows 0 on a fresh repo** — correct. It reads `enrichment.known_issues` only. No operator has typed entries yet.

---

## Reporting & Visualization

- ✅ **Health dashboard** — `./avm.sh site` generates a single-file static HTML scorecard from all `analysis_*` blocks: per-domain collapsible tables, colour-coded scores, dimension badges, staleness indicators, version pin column. _Implemented in `scripts/generate_site.py`. Output: `docs/site/index.html`._
- ✅ **`/avm-index`** — Copilot skill for building/rebuilding the resource-to-module index. _Implemented in `.github/skills/avm-index/SKILL.md`._
- 💡 **Domain coverage heatmap** — which domains have analysis data, which are gaps
- 💡 **Owner map** — who owns what across all modules; highlight modules with no secondary owner

## Quality & Compliance

- ✅ **Stale analysis detector** — `avm status` now annotates modules with `[stale Nd]` when oldest `analysis_*` block exceeds threshold (default 14d); `--stale-threshold DAYS` flag added. _Implemented in `scripts/manage_repos.py`._
- ✅ **Cross-module issue rollup** — `./avm.sh report --issues` aggregates all `enrichment.known_issues[status: open]` into a severity-sorted triage table. _Implemented in `scripts/report.py`._
- ✅ **Compliance scorecard** — `./avm.sh report --scores` ranks all modules by a weighted 0–100% score across all 6 analysis dimensions (security=4, compliance/deps=3, tests/docs=2, metadata=1). _Implemented in `scripts/report.py`. Severity weights defined in `scripts/analyze_module.py`._

## Enrichment Automation

- ✅ **Auto version-pin** — when `./avm.sh check --dimension terraform-metadata` runs, it reads the latest git tag and auto-fills `enrichment.version_pinned` if currently empty. _Implemented as a side-effect in `scripts/analyze_module.py`._
- 💡 **GitHub issue import** — new script that fetches open issues from each module's GitHub repo and populates `enrichment.known_issues` automatically
- 💡 **Use-case tagging** — infer `use_cases` from `analysis_terraform_metadata.resources_managed` using a lookup table

## New Skills / Commands

- ✅ **`/avm-issues`** — surfaces open enrichment issues across a domain; wraps `report.py --issues`. _Implemented in `.github/skills/avm-issues/SKILL.md`._
- ✅ **`/avm-index`** — Copilot skill for building/rebuilding the resource-to-module index; wraps `build_resource_index.py`. _Implemented in `.github/skills/avm-index/SKILL.md`._
- ✅ **`avm report`** — new CLI command: `--scores`, `--issues`, `--json` subcommands with `--domains`, `--types`, `--severity`, `--min-score`, `--output` filters. _Implemented in `avm.sh` + `scripts/report.py`._
- ✅ **`avm activity`** — git commit activity monitor across all cloned repos with `--since`, `--stagnant-only`, `--no-stagnant`, `--top`, `--domains` flags. _Implemented in `avm.sh` + `scripts/activity.py`._
- ✅ **`avm index`** — build per-resource-type stub inventory (`data/{resources,datasources,functions,ephemerals,actions}/{type}.yaml`); stubs never overwritten; `--dry-run`, `--domains`, `--types` flags. _Implemented in `avm.sh` + `scripts/build_resource_index.py`._
- ✅ **`avm providers`** — fetch Terraform provider changelog (releases) and/or open GitHub issues → write `provider_updates.findings` / `provider_issues.items` into each stub. Modes: `changes` (default), `issues`, `all`. Flags: `--provider`, `--mode`, `--since`, `--max-releases`, `--max-issues`, `--dry-run`, `--force`. _Implemented in `avm.sh` + `scripts/fetch_provider_changes.py`._



> **Export to JSON** (was an inline idea) — ✅ `./avm.sh report --json` exports the full catalog to `data/catalog.json`. _Implemented in `scripts/report.py`._

## Cross-repo Git Intelligence

- ✅ **Activity monitor** — `./avm.sh activity` reads `.config/modules.yaml`, runs `git log --since` per cloned repo, outputs a sorted commit-count table with `[stagnant]` labels. _Implemented in `scripts/activity.py`._
- 💡 **Multi-repo CHANGELOG** — aggregate recent commits across a domain into a digest

## Provider Change Intelligence

**Goal:** for every module that manages Azure resources, determine whether the provider version it requires is outdated relative to the latest release, and surface which of those gaps contain changes relevant to the resources the module actually uses.

### Phase 1 — Build a per-resource-type stub inventory ✅

Collect all five terraform symbol types (`resources_managed`, `datasources_managed`, `functions_used`, `ephemeral_managed`, `actions_managed`) from all `data/modules/{res,ptn,utl}/*.yaml` and create a stub YAML file for each unique symbol encountered:

```
data/
  resources/    azurerm_virtual_network.yaml
                azapi_resource.yaml
  datasources/  azurerm_subnet.yaml      ← separate folder avoids name collision
                azurerm_public_ip.yaml
  functions/    assert_cidrv4.yaml
  ephemerals/   azapi_resource_action.yaml
  actions/      ...
```

Each stub is small, resource-centric, and **never overwritten** — it is the future home for provider changelog findings and provider issues. The module↔resource relationship is a runtime lookup at check time, not stored in the stub.

```yaml
resource:
  type: azurerm_virtual_network
  provider: azurerm
  symbol_type: resource
  registry_url: "https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/virtual_network"

provider_updates:          # populated by Phase 2 (fetch_provider_changes.py)
  last_checked: null
  findings: []
  # finding shape:
  #   - version: "4.15.0"
  #     criticality: high   # critical | high | medium | low
  #     type: bug_fix       # bug_fix | security | enhancement | breaking_change | new_feature | deprecated
  #     summary: "..."
  #     url: "..."

provider_issues:           # populated by Phase 3
  last_checked: null
  items: []
  # item shape:
  #   - number: 1234
  #     title: "..."
  #     labels: [bug]
  #     url: "..."
  #     created_at: "2026-01-01"

enrichment:
  notes: []         # hand-maintained
```

Script: `scripts/build_resource_index.py` — reads all module YAMLs, collects all 5 symbol types, creates stubs only for new resource types. _Implemented. Run `./avm.sh index`._

---

### Phase 2 — Fetch provider changelog per resource type ✅

For each provider, fetch GitHub Releases and parse the markdown release body to extract entries that mention specific resource types. Findings are written directly into each resource stub's `provider_updates.findings` block — no intermediate file.

Script: `scripts/fetch_provider_changes.py` — reads `data/{resources,datasources,functions,ephemerals}/` stubs, fetches GitHub Releases API, parses markdown headings to assign criticality and type, writes findings in-place. _Implemented. Run `./avm.sh providers`._

```
./avm.sh providers                                    # all stubs, last 100 releases, azurerm+azapi
./avm.sh providers --since 4.0.0                      # limit to releases >= 4.0.0
./avm.sh providers --provider azurerm --dry-run       # preview without writing
./avm.sh providers --force                            # re-fetch even if checked within 24 h
```

Criticality classification is done inline by matching release section headings against a precedence table (Breaking Changes → critical, Security/CVE → critical, Bug Fixes → high, Enhancements → medium, New Resources → low). Results are stored per-resource, per-version:

```yaml
provider_updates:
  last_checked: "2026-05-13T06:16:10Z"
  findings:
  - version: "4.15.0"
    criticality: high
    type: bug_fix
    summary: "`azurerm_virtual_network` - fixed incorrect subnet delegation order"
    url: "https://github.com/hashicorp/terraform-provider-azurerm/releases/tag/v4.15.0"
```

> **Note:** Phase 3 (criticality classification) is merged into Phase 2 — it is performed inline during the same fetch pass.

---

### Phase 3 — Fetch provider issues per resource type ✅

Bulk-fetches all open GitHub Issues from provider repos, cross-matches issue titles and bodies against known resource types (backtick-quoted), and writes matched issues into each stub's `provider_issues.items` block.

```
./avm.sh providers --mode issues                      # open issues only (azurerm+azapi)
./avm.sh providers --mode all                         # changelog + issues in one pass
./avm.sh providers --mode issues --max-issues 500
./avm.sh providers --mode issues --dry-run
```

**Strategy:** Bulk-fetch all open issues in ~10 API calls (100/page), then cross-match — far more efficient than per-resource-type search queries (~223 calls). Issue title + first 3 000 chars of body are scanned for backtick-quoted resource type names.

```yaml
provider_issues:
  last_checked: "2026-05-13T08:00:00Z"
  items:
  - number: 12345
    title: "azurerm_storage_account: Support for Geo Priority Replication"
    labels: ["enhancement", "service/storage"]
    url: "https://github.com/hashicorp/terraform-provider-azurerm/issues/12345"
    created_at: "2026-04-09"
```

### Phase 4 — Surface findings

- **`avm check --dimension provider-currency`** — new analysis dimension; writes summary back to `analysis_provider_currency:` block in each module YAML
- **`/avm-check-provider`** — new Copilot skill; wraps the above for a single module
- **`avm report --provider-findings`** — rolls up all `critical` and `high` findings across modules into a triage table sorted by criticality
- **Health dashboard integration** — add a "Provider Currency" column to the dashboard showing worst-criticality finding per module

---

> **Implementation order:** Phase 1 ✅ → Phase 2 ✅ → Phase 3 ✅ → Phase 4 💡 (surface findings in `analysis_provider_currency:` blocks and dashboard).

### Other Terraform symbol types (datasources, functions, ephemeral/actions) ✅

All five symbol types are already scraped by `scripts/analyze_module.py` (terraform-metadata dimension) and written as sibling keys in `analysis_terraform_metadata`:

| Symbol type | Terraform block | YAML key |
|---|---|---|
| **Resources** | `resource "<provider>_<type>"` | `resources_managed` |
| **Data sources** | `data "<provider>_<type>"` | `datasources_managed` |
| **Provider functions** | `provider::<ns>::<fn>()` | `functions_used` |
| **Ephemeral resources** | `ephemeral "<provider>_<type>"` | `ephemeral_managed` |
| **Actions** | `actions "<provider>_<type>"` | `actions_managed` |

_All five parsers (`parse_resources`, `parse_datasources`, `parse_functions_used`, `parse_ephemeral_managed`, `parse_actions_managed`) are implemented in `scripts/analyze_module.py`. The resource index builder (Phase 1) uses all five._



- ✅ **Export to JSON** — ~~dump `data/modules/` into a single `catalog.json` for consumption by external tools (Grafana, Power BI, a web UI)~~ `./avm.sh report --json` → `data/catalog.json`. _Implemented in `scripts/report.py`._

## GitHub Pages — AVM Intelligence Portal 💡

Not just a table. A full interactive intelligence portal auto-published on every `sync` or `check` run via GitHub Actions.

### Pages / views

| Page | Content | Visualizations |
|---|---|---|
| **Home / Overview** | Catalog summary stats | Donut: modules by type (res/ptn/utl); Bar: modules by domain; Trend line: catalog growth over time (from `first_published`) |
| **Module Catalog** | Searchable, filterable table of all modules | Filters: domain, type, status, owner; Columns: name, domain, type, status, analysis score, provider currency, last synced |
| **Quality Scoreboard** | Per-module pass/fail across all 6 analysis dimensions | Heatmap: module × dimension; Sorted leaderboard by overall score; Radar chart per module |
| **Provider Currency** | Findings from `data/resources/` | Grouped bar: findings by provider and criticality; Timeline: critical findings over provider versions; Table: open critical/high findings with module links |
| **Domain Deep-dive** | Per-domain page (one per domain slug) | Module list; Resource type cloud; Owner breakdown; Compliance heatmap for that domain |
| **Resource Explorer** | All resource types from `data/resources/` | Treemap: resource types by provider, sized by number of modules using them; Click-through to per-resource finding timeline |
| **Owner Map** | Primary + secondary owners across all modules | Force-directed graph: owner nodes → module nodes; Highlight: modules with no secondary owner |
| **Known Issues** | Aggregated `enrichment.known_issues` across all modules | Kanban-style board (open / resolved / wontfix) grouped by severity; Bar chart: open issues by domain |
| **Activity Feed** | Recent git activity across cloned repos | Timeline: commits per module per day (last 90 days); Heatmap: activity by day of week × module |
| **Changelog** | `data/resources/*_findings.yaml` findings | Filterable timeline of provider changes with criticality colour coding |

### Tech stack (static, no server)

- **Generator:** Python script (`scripts/generate_site.py`) — reads all `data/` YAMLs, emits `docs/site/` as static HTML + JSON data files
- **Charts:** [Observable Plot](https://observablehq.com/plot/) or [Apache ECharts](https://echarts.apache.org/) (CDN, zero build step)
- **Diagrams:** Mermaid.js (rendered client-side) for architecture diagrams embedded in module pages
- **Search:** [Pagefind](https://pagefind.app/) — static full-text search, zero backend
- **Theme:** Minimal, dark-mode-first, AVM brand colours
- **Deploy:** GitHub Actions → `gh-pages` branch on every push to `main` that touches `data/`

### Per-module detail page

Each module gets its own generated page at `/modules/{name}/`:

- Catalog metadata (owner, status, registry link, GitHub link)
- Analysis dimension scorecard (pass/fail badges with details)
- Provider currency findings (criticality timeline)
- Known issues board
- Resource types managed (with links to Resource Explorer)
- Enrichment notes and version pin history
- Embedded Mermaid dependency graph (which resource types it composes)

### Automation

```yaml
# .github/workflows/pages.yml
on:
  push:
    paths: ['data/**']
  schedule:
    - cron: '0 6 * * 1'   # weekly refresh
```

`generate_site.py` is idempotent — safe to run on every push. Output goes to `docs/site/` (gitignored locally, published via Actions).

---

## GitHub Projects Integration — Issue Triage & Bulk Remediation 💡

Use the GitHub Projects API (v2) and Issues as the operational surface for everything discovered by the analysis pipeline. Instead of findings living only in YAML files, they become trackable, assignable, closable work items.

### How it works

- **`scripts/sync_issues.py`** — reads all `enrichment.known_issues` (open), all `analysis_*` failures, and all `data/resources/*_findings.yaml` critical/high entries, then creates or updates GitHub Issues on the `avm-metadata` repo (or a dedicated triage repo)
- Each issue is tagged with labels: `domain:networking`, `type:bug-fix`, `criticality:high`, `module:avm-res-network-virtualnetwork`, `dimension:security-hardening`, etc.
- Issues are added to a **GitHub Project board** with columns: `Triage` → `In Progress` → `Done`
- Closing an issue via PR or manually marks the corresponding YAML entry as resolved on next sync

### Board columns

| Column | Contains |
|---|---|
| **Triage** | Newly detected findings not yet assigned |
| **Operator: Bulk Fix** | Issues suitable for `avm run` or `avm check --fix` — one person can resolve many at once |
| **Assistant: Agent Fix** | Issues flagged as automatable by a Copilot agent (e.g., version pin update, README gap) |
| **Blocked** | Needs upstream provider/module fix; waiting |
| **Done** | Resolved and verified |

### Operator workflow

```bash
# Sync all findings → GitHub Issues + Project board
./avm.sh issues sync

# Bulk-close all 'low' issues in a domain after fixing
./avm.sh issues close --domain networking --criticality low
```

### Assistant workflow

- **`/avm-issues sync`** — trigger `sync_issues.py` and report how many issues were created/updated/closed
- **`/avm-issues triage`** — list open issues by criticality and suggest which ones can be auto-fixed

### Key benefit

Both Operators (terminal) and Assistants (Copilot agent on a PR) can query the board, pick up a batch of issues, fix them across repos using `avm run`, and close them — all in one workflow loop without leaving the GitHub ecosystem.

---

## Module Issue Harvesting — `module_issues` (via GitHub MCP) 💡

Query open issues directly from each AVM module's GitHub repository using the GitHub MCP server, and write a structured snapshot into a dedicated `module_issues:` block in each `data/modules/*.yaml` file.

### Why this matters

The `enrichment.known_issues` block is hand-maintained — it captures what _we_ know. But the upstream repos (`Azure/terraform-azurerm-avm-res-*`) accumulate community-reported bugs, enhancement requests, and PRs we may never see unless we go looking. This harvests that signal automatically.

### How it works

- **`scripts/harvest_module_issues.py`** — for each module in `data/modules/`, calls the GitHub MCP tool to fetch open issues from `catalog.repo_url`
- Filters by useful labels: `bug`, `enhancement`, `breaking-change`, `help wanted`, `good first issue`
- Writes a new `module_issues:` block in the module YAML (never merges with `enrichment.known_issues` — kept strictly separate)
- Tracks `last_harvested` timestamp; skips modules where it is fresh (default: 24 h)

### YAML schema (`data/modules/*.yaml`)

```yaml
module_issues:
  last_harvested: "2026-05-13T10:00:00Z"
  open_count: 7
  issues:
    - number: 312
      title: "azurerm_virtual_network: subnet delegation order not respected"
      labels: [bug, help wanted]
      url: "https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork/issues/312"
      created_at: "2026-03-21"
      comments: 4
    - number: 318
      title: "Support for encryption_at_host"
      labels: [enhancement]
      url: "..."
      created_at: "2026-04-10"
      comments: 1
```

### Integration points

- **GitHub Pages** — "Known Issues" page gains a second tab: _Module Issues_ alongside _Enrichment Issues_; shows open count badge per module in the catalog table
- **GitHub Projects Integration** — high-signal module issues (labelled `bug` or `breaking-change`) can be fed into the triage board as linked items; see the _GitHub Projects Integration_ section for the board mechanics
- **Copilot skill** — **`/avm-harvest [module]`** — harvests on demand and summarises findings; useful when starting work on a module

### CLI

```bash
./avm.sh harvest                                    # harvest all modules
./avm.sh harvest --domains networking --types res   # filtered
./avm.sh harvest --modules avm-res-network-virtualnetwork  # single module
./avm.sh harvest --since 7d                         # only refresh if older than 7 days
```

> **Note:** Requires a GitHub token with `public_repo` read scope. Results are committed to `data/modules/` like any other sync output — they are the source of truth snapshot, not live data.

---

## Schema Refactoring — Shared Definitions 💡

The three module schemas (`avm-module-res.schema.json`, `avm-module-ptn.schema.json`, `avm-module-utl.schema.json`) share a large amount of duplicated `$defs`. Every time a shared definition is added or changed (as happened with `upstream_issues_block`, `upstream_issue`, `upstream_issues_block` etc.) it must be applied identically to all three files. This is error-prone and already caused drift during this session.

### What is duplicated today

| `$def` | Duplicated across |
|---|---|
| `analysis_dimension` | res, ptn, utl |
| `analysis_check_result` | res, ptn, utl |
| `upstream_issues_block` | res, ptn, utl |
| `upstream_issue` | res, ptn, utl |
| `resources_map` | res, ptn, utl |
| `terraform_constraints` | res, ptn, utl |
| `provider_requirement` | res, ptn, utl |
| `owners` / `owner` | res, ptn, utl |
| `known_issue` | res, ptn, utl |
| `note` | res, ptn, utl |
| `domain` / `provider` enums | res, ptn, utl |

Only `analysis_terraform_metadata` differs meaningfully between schemas (res/utl have `resources_managed`; ptn has `modules_called`). The `catalog` block differs in `name` pattern and `type` const. Everything else is identical.

### Refactoring options

**Option A — Shared definitions file (JSON Schema `$ref` to external URI)**

Extract all shared `$defs` into `schemas/avm-module-shared.schema.json`. Each per-type schema uses `"$ref": "./avm-module-shared.schema.json#/$defs/analysis_dimension"` for shared defs, keeping only type-specific properties inline.

- Pros: single source of truth; add once, applies everywhere
- Cons: requires JSON Schema draft 2020-12 `$ref` resolution; VS Code YAML extension and most validators handle it, but tooling must be tested

**Option B — Code-generate the schemas from a Python template**

Add `scripts/generate_schemas.py` that reads a shared definitions dict and per-type overrides, then writes all three `.schema.json` files. Run as `./avm.sh generate-schemas` or as a pre-commit hook.

- Pros: full control, no validator compatibility concerns; schemas remain self-contained
- Cons: schemas are no longer hand-editable; requires discipline to run after any shared def change

**Option C — JSON Schema `$defs` + `allOf` composition**

Keep three files but make each `allOf` a base schema (`avm-module-base.schema.json`) that contains all shared properties and defs, then each type schema extends it with only the type-specific overrides.

- Pros: validators that support `allOf` composition work out of the box (draft 2020-12 standard)
- Cons: `additionalProperties: false` interacts badly with `allOf` in some validators; needs careful testing

### Recommendation

**Option B** (code-generation) is the safest path given the existing Python toolchain. The generator can be invoked automatically in CI whenever `scripts/generate_schemas.py` is modified. The output `.schema.json` files remain committed and self-contained, so schema consumers (VS Code, CI validators) need no changes.

Priority: low — only worth doing once the schema stabilises (i.e., after `analysis_provider_currency` is added).

---

> ~~**Highest-ROI starting points:** health dashboard (all analysis data is already there, just needs rendering) and stale analysis detector (trivial to add to `avm status`, immediately useful).~~
> ✅ **Done (2026-05-13):** stale analysis detector, compliance scorecard (weighted), cross-module issue rollup, JSON export, `avm report` command, `/avm-issues` skill, auto version-pin, and `DIMENSION_SEVERITY`/`CHECK_SEVERITY` weight constants. Health dashboard (HTML/static site) is the next highest-ROI item.
