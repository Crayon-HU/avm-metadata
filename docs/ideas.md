# Ideas

## Reporting & Visualization

- **Health dashboard** — generate a static HTML/markdown scorecard from all `analysis_*` blocks: per-domain pass/fail table, staleness indicator (`checked_at` age), overall quality score
- **Domain coverage heatmap** — which domains have analysis data, which are gaps
- **Owner map** — who owns what across all modules; highlight modules with no secondary owner

## Quality & Compliance

- **Stale analysis detector** — flag modules where any `analysis_*` block hasn't been refreshed in N days; add this as an `avm status` output column
- **Cross-module issue rollup** — aggregate all `enrichment.known_issues` with `status: open` into a single triage table, grouped by severity
- **Compliance scorecard** — rank all modules by how many of the 6 analysis dimensions pass; expose as a sorted table

## Enrichment Automation

- **Auto version-pin** — for each cloned repo, read the latest git tag and pre-fill `enrichment.version_pinned` where it's missing
- **GitHub issue import** — new script that fetches open issues from each module's GitHub repo and populates `enrichment.known_issues` automatically
- **Use-case tagging** — infer `use_cases` from `analysis_terraform_metadata.resources_managed` using a lookup table

## New Skills / Commands

- **`/avm-issues`** — surface open enrichment issues across a domain in one call
- **`avm report`** — new CLI command that dumps a markdown/HTML quality report for a domain or all modules

## Cross-repo Git Intelligence

- **Activity monitor** — `avm run git log --since="30 days ago" --oneline` across all repos; identify which modules are actively maintained vs stagnant
- **Multi-repo CHANGELOG** — aggregate recent commits across a domain into a digest

## Provider Change Intelligence

**Goal:** for every module that manages Azure resources, determine whether the provider version it requires is outdated relative to the latest release, and surface which of those gaps contain changes relevant to the resources the module actually uses.

### Phase 1 — Build a resource-to-module index

Collect `analysis_terraform_metadata.resources_managed` from all `data/modules/res/*.yaml` and `data/modules/utl/*.yaml` and build a flat dataset:

```
data/resources/
  azurerm.yaml    # all resource types managed via azurerm, grouped by resource type → [module list]
  azapi.yaml      # same for azapi
  azuread.yaml    # etc.
```

Each entry:

```yaml
- resource_type: "azurerm_virtual_network"
  provider: azurerm
  modules:
    - name: avm-res-network-virtualnetwork
      min_provider_version: "~> 4.0"   # from terraform_constraints.required_providers
      enrichment_version_pinned: "0.7.0"
```

Script: `scripts/build_resource_index.py` — reads all module YAMLs, merges `resources_managed` + `required_providers` version constraints, writes `data/resources/{provider}.yaml`.

---

### Phase 2 — Fetch provider changelog per resource type

For each provider, pull the changelog/release notes between the module's minimum required provider version and the latest published version. Three sources, used in order:

| Source | Method | Notes |
|---|---|---|
| **GitHub Releases** | GitHub API — `GET /repos/{owner}/{repo}/releases` | Structured; contains release body (markdown) |
| **GitHub CHANGELOG.md** | Fetch raw file from the provider repo | `hashicorp/terraform-provider-azurerm`, `Azure/terraform-provider-azapi` |
| **Terraform Registry** | MCP / Registry API | Provides latest version; use as version anchor |

Filter release notes to only entries that mention the specific resource type(s) a module manages (e.g., `azurerm_virtual_network`).

Script: `scripts/fetch_provider_changes.py --provider azurerm` — outputs `data/resources/azurerm_changes.yaml` with per-resource-type findings.

---

### Phase 3 — Assign criticality

Classify each matched changelog entry by scanning the release note text for signal words:

| Criticality | Signals |
|---|---|
| `critical` | `security`, `CVE`, `vulnerability`, `breaking change`, `data loss` |
| `high` | `bug fix`, `fix`, `regression`, `incorrect`, `panic`, `crash` |
| `medium` | `enhancement`, `improvement`, `deprecated`, `behavior change` |
| `low` | `new resource`, `new attribute`, `new argument`, `documentation` |

Store findings in `data/resources/azurerm_findings.yaml`:

```yaml
- resource_type: "azurerm_virtual_network"
  provider: azurerm
  provider_version_from: "4.0.0"
  provider_version_to: "4.21.0"   # latest at check time
  findings:
    - version: "4.15.0"
      criticality: high
      type: bug_fix
      summary: "azurerm_virtual_network: fixed incorrect subnet delegation order"
      url: "https://github.com/hashicorp/terraform-provider-azurerm/releases/tag/v4.15.0"
    - version: "4.18.0"
      criticality: medium
      type: enhancement
      summary: "azurerm_virtual_network: added private_endpoint_network_policies attribute"
      url: "..."
  modules_affected:
    - avm-res-network-virtualnetwork
  checked_at: "2026-05-13T..."
```

---

### Phase 4 — Surface findings

- **`avm check --dimension provider-currency`** — new analysis dimension; writes summary back to `analysis_provider_currency:` block in each module YAML
- **`/avm-check-provider`** — new Copilot skill; wraps the above for a single module
- **`avm report --provider-findings`** — rolls up all `critical` and `high` findings across modules into a triage table sorted by criticality
- **Health dashboard integration** — add a "Provider Currency" column to the dashboard showing worst-criticality finding per module

---

> **Implementation order:** Phase 1 (pure YAML → YAML transform, no network) → Phase 4 dashboard column (immediate value) → Phase 2+3 (network-dependent, needs GitHub token and Registry MCP).

### Other Terraform symbol types (datasources, functions, ephemeral/actions)

Currently `analyze_module.py` only collects `resources_managed` under `analysis_terraform_metadata`. To support full coverage in the resource index, it needs to be extended to also scrape and record:

| Symbol type | Terraform block | Example | Action |
|---|---|---|---|
| **Data sources** | `data "<provider>_<type>"` | `data "azurerm_subnet"` | Add `datasources_managed` key alongside `resources_managed` |
| **Provider functions** | `provider::<ns>::<fn>()` | `provider::azurerm::normalize_resource_id()` | Add `functions_used` key |
| **Ephemeral resources / actions** | `ephemeral "<provider>_<type>"` | `ephemeral "azurerm_key_vault_secret"` | Add `ephemeral_managed` key |

**Required change:** `scripts/analyze_module.py` — in the `terraform-metadata` dimension scraper, extend the `.tf` file walker to also collect these three block types and write them as separate sibling keys in the `analysis_terraform_metadata` block. The changelog fetch pipeline (Phase 2) can then filter on all four keys, not just `resources_managed`.



- **Export to JSON** — dump `data/modules/` into a single `catalog.json` for consumption by external tools (Grafana, Power BI, a web UI)

## GitHub Pages — AVM Intelligence Portal

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

## GitHub Projects Integration — Issue Triage & Bulk Remediation

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

## Upstream Module Issue Harvesting (via GitHub MCP)

Query open issues directly from each upstream module's GitHub repository using the GitHub MCP server, and write a structured snapshot into a dedicated `upstream_issues:` block in each `data/modules/*.yaml` file.

### Why this matters

The `enrichment.known_issues` block is hand-maintained — it captures what _we_ know. But the upstream repos (`Azure/terraform-azurerm-avm-res-*`) accumulate community-reported bugs, enhancement requests, and PRs we may never see unless we go looking. This harvests that signal automatically.

### How it works

- **`scripts/harvest_upstream_issues.py`** — for each module in `data/modules/`, calls the GitHub MCP tool (`github-pull-request_doSearch` or equivalent) to fetch open issues from `catalog.repo_url`
- Filters by useful labels: `bug`, `enhancement`, `breaking-change`, `help wanted`, `good first issue`
- Writes a new `upstream_issues:` block in the module YAML (never merges with `enrichment.known_issues` — kept strictly separate)
- Tracks `last_harvested` timestamp; skips modules where it is fresh (default: 24 h)

### YAML schema

```yaml
upstream_issues:
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

- **GitHub Pages** — "Known Issues" page gains a second tab: _Upstream Issues_ alongside _Enrichment Issues_; shows open count badge per module in the catalog table
- **GitHub Projects sync** — `sync_issues.py` can optionally mirror high-signal upstream issues (labelled `bug` or `breaking-change`) into the local triage board as linked items
- **Copilot skill** — **`/avm-upstream-issues [module]`** — harvests on demand and summarises findings; useful when starting work on a module

### CLI

```bash
./avm.sh harvest                                    # harvest all modules
./avm.sh harvest --domains networking --types res   # filtered
./avm.sh harvest --modules avm-res-network-virtualnetwork  # single module
./avm.sh harvest --since 7d                         # only refresh if older than 7 days
```

> **Note:** Requires a GitHub token with `public_repo` read scope. Results are committed to `data/modules/` like any other sync output — they are the source of truth snapshot, not live data.

---

> **Highest-ROI starting points:** health dashboard (all analysis data is already there, just needs rendering) and stale analysis detector (trivial to add to `avm status`, immediately useful).
