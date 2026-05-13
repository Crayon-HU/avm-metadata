# Copilot Instructions — avm-metadata Workspace

## What this repo is

This is a **metadata repository** for [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/). It contains no Terraform code of its own. Its purpose is to organize and bootstrap the upstream AVM module repositories into a VSCode multi-root workspace, grouped by domain.

Every directory whose name starts with `terraform-azurerm-avm-*` is a **cloned external repository** — it has its own `.git` history and its own Copilot instructions. Do not modify those repos through this metadata repo.

---

## Workspace layout

```
data/modules/                   Source of truth for the module catalog (committed)
  res/   avm-res-*.yaml         One YAML per resource module
  ptn/   avm-ptn-*.yaml         One YAML per pattern module
  utl/   avm-utl-*.yaml         One YAML per utility module
  catalog-manifest.yaml         Auto-generated summary

scripts/
  generate_config.py            Reads data/modules/ → writes .config/modules.yaml
  manage_repos.py               Multi-repo git ops: clone/update/fetch/status/branch/stash/reset/run/cleanup
  sync_catalog.py               Fetches upstream AVM CSVs → refreshes data/modules/ catalog sections
  analyze_module.py             Multi-dimensional analysis (7 dimensions) → populates analysis_* blocks in data/modules/
  report.py                     Read-only reports: compliance scores (weighted), issue rollup, provider-findings, JSON export
  activity.py                   Git commit activity monitor across cloned repos
  build_resource_index.py       Per-resource-type stub inventory builder → data/{resources,datasources,…}/
  fetch_provider_changes.py     Fetch provider GitHub Releases → write provider_updates findings to stubs
  harvest_module_issues.py      Fetch open GitHub issues from AVM module repos → write module_issues blocks
  tag_use_cases.py              Infer functional use-case tags → write analysis_use_cases blocks
  generate_site.py              Static HTML health dashboard generator → docs/site/index.html
                                  Panels: stats, domain×dimension heatmap, owner map, per-domain module tables

avm.sh                          Unified operator entry point — delegates to scripts/
.github/skills/                 Copilot skill procedures — also delegate to scripts/
avm.code-workspace              Root workspace — includes . + all modules

terraform-azurerm-avm-*/        Cloned module repos (gitignored — not part of this repo)
.config/modules.yaml            GENERATED (gitignored) — re-run: ./avm.sh setup
```

---

## Domain → module mapping

| Domain | Types | Key modules |
|---|---|---|
| `networking` | res, ptn, utl | VNet, NSG, Firewall, Bastion, Private Endpoint, DNS, LB, App GW, NAT GW, IPAM |
| `compute` | res, ptn | VM, VMSS, Disk, Disk Encryption Set, Gallery, Image Builder |
| `containers` | res, ptn | AKS, ACR, Container App, Managed Environment, ACA LZA |
| `identity` | res, ptn | Key Vault, User Assigned Identity, Role Assignment |
| `storage` | res, ptn | Storage Account, Function App Storage PE pattern |
| `monitoring` | res, ptn | Log Analytics, App Insights, DCR, AMBA ALZ, Alert Rules, Grafana |
| `management` | res, ptn, utl | Resource Group, Management Group, Policy, Budget, Automation Account |
| `recovery` | res, ptn | Recovery Services Vault, Backup Vault, Resource Guard, VM Replication |
| `web` | res | App Service Plan, Web/Function App, Static Web App, ASE, APIM |
| `data` | res, ptn | Databricks, PostgreSQL, MySQL, Cosmos DB, SQL Server, Data Factory, Event Hub, Service Bus, Oracle DB |
| `aiml` | res, ptn | Cognitive Services, OpenAI, ML Workspace, AI Foundry, AI Search |
| `platform` | res, ptn, utl | ALZ core, Sub Vending, CI/CD Agents, Regions, Naming, Managed DevOps Pools |
| `avd` | res, ptn | AVD Host Pool, Workspace, Application Group, LZA patterns |
| `hybrid` | res, ptn | Azure Stack HCI, Arc-enabled Servers, AKS Arc |
| `iot` | res | IoT Operations, Digital Twins, Device Registry |
| `devtools` | res, ptn | Dev Center, Dev Box, Dev Test Lab, Load Testing |

---

## Module type conventions

| Type | Prefix | Notes |
|---|---|---|
| `res` | `avm-res-*` | Deploys a single Azure resource type. Accepts standard AVM interface variables (tags, lock, RBAC, PE, diagnostic settings). |
| `ptn` | `avm-ptn-*` | Opinionated multi-resource pattern. Composes multiple `res` and other modules. |
| `utl` | `avm-utl-*` | Shared utility/data helper. No Azure resources deployed; provides data or schema utilities. |

---

## AVM coding conventions

When generating Terraform code that consumes AVM modules:

1. **Pin versions**: Always use `version = "x.y.z"` — never a floating constraint.
2. **Registry source**: `source = "Azure/avm-{type}-{provider}-{resource}/azurerm"`
   - Example: `source = "Azure/avm-res-network-virtualnetwork/azurerm"`
3. **Telemetry**: Pass through `enable_telemetry = var.enable_telemetry` from root.
4. **Standard interfaces**: All `res` modules accept `tags`, `lock`, `role_assignments`, `private_endpoints`, `diagnostic_settings`, `managed_identities` via the AVM interface spec.
5. **Terraform version**: AVM modules require `>= 1.9, < 2.0`.
6. **Provider version**: `azurerm >= 3.117`.

---

## modules.yaml schema

`.config/modules.yaml` is **auto-generated** by `generate_config.py` from `data/modules/` catalog data. Do not edit it manually. Each entry:

```yaml
modules:
  - name: terraform-azurerm-avm-res-network-virtualnetwork   # GitHub repo name = clone dir
    domain: networking     # derived from catalog.domain
    type: res              # res | ptn | utl
    url: https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork.git
    branch: main
    description: Virtual Network
```

`generate_config.py` reads `catalog.repo_url`, `catalog.domain`, `catalog.type`, `catalog.display_name` from `data/modules/{type}/*.yaml` catalog blocks.

**Status filtering (both `setup` and `sync`):**
- Default: only `Available` modules are included/synced
- `--include-deprecated` — also include/sync `Deprecated` modules
- `--include-proposed` — also include/sync `Proposed` modules

---

## Entry point

`avm.sh` is the single unified wrapper for all automation. Prefer it over calling `scripts/` directly (skills are the exception — they call `scripts/` directly).

```bash
./avm.sh help                                            # show all commands and options

# Catalog
./avm.sh sync                                            # fetch upstream CSVs → refresh data/modules/
./avm.sh sync --dry-run                                  # preview changes without writing
./avm.sh sync --force                                    # force-rewrite all module files
./avm.sh sync --include-proposed                         # also sync Proposed-status modules
./avm.sh sync --include-deprecated                       # also sync Deprecated-status modules

# Setup
./avm.sh setup --domains all                             # generate .config/modules.yaml
./avm.sh setup --domains networking,compute --types res
./avm.sh setup --include-proposed                        # include Proposed modules in config

# Clone / update
./avm.sh clone                                           # clone all modules from modules.yaml
./avm.sh clone --domains networking --types res          # filtered clone
./avm.sh clone --modules avm-res-network-virtualnetwork  # single module
./avm.sh update --parallel 10                            # git pull --ff-only (parallel)
./avm.sh fetch --parallel 30                             # fetch remotes without merging

# Status / cleanup
./avm.sh status                                          # show dirty/behind repos + staleness
./avm.sh status --domains networking                     # filtered status
./avm.sh status --stale-threshold 30                     # flag modules not checked for 30+ days
./avm.sh cleanup                                         # remove repos not in modules.yaml
./avm.sh cleanup --dry-run                               # preview cleanup
./avm.sh cleanup --force                                 # remove even dirty repos

# Branch management
./avm.sh branch create feature/my-fix                   # create branch in all repos
./avm.sh branch create feature/my-fix --domains networking  # filtered
./avm.sh branch checkout feature/my-fix --fallback       # checkout (stay put if missing)
./avm.sh stash --domains networking                      # stash changes in networking repos
./avm.sh reset --hard                                    # hard reset all repos to HEAD
./avm.sh run git log --oneline -3                        # arbitrary command in each repo

# Analysis
./avm.sh scrape --domains networking --types res         # terraform-metadata for filtered repos
./avm.sh scrape --modules avm-res-network-virtualnetwork # scrape one module
./avm.sh check --modules avm-res-network-virtualnetwork  # full analysis (all 7 dimensions)
./avm.sh check --domains networking --dimension avm-interface-compliance  # filtered
./avm.sh check --domains networking --dimension provider-currency         # no clone needed
./avm.sh check --dry-run                                 # preview analysis changes

# Reporting (read-only, no files modified)
./avm.sh report --scores                                 # weighted compliance scorecard
./avm.sh report --scores --domains networking --min-score 80  # filter low scorers
./avm.sh report --issues                                 # cross-module open issue rollup
./avm.sh report --issues --severity critical,high        # filter by severity
./avm.sh report --provider-findings                      # modules with critical/high provider release findings
./avm.sh report --provider-findings --severity critical  # critical only
./avm.sh report --json                                   # export catalog → data/catalog.json
./avm.sh report --json --output docs/catalog.json        # custom output path

# Activity (read-only, needs cloned repos)
./avm.sh activity                                        # commit activity for all modules (last 30d)
./avm.sh activity --since 7d --no-stagnant               # active modules only, last 7 days
./avm.sh activity --stagnant-only                        # repos with no commits in window
./avm.sh activity --domains networking --top 10          # top 10 most active in networking

# Resource index (reads data/modules/, writes data/{resources,datasources,functions,ephemerals,actions}/)
./avm.sh index                                           # create stubs for all symbol types (no overwrite)
./avm.sh index --dry-run                                 # preview without writing
./avm.sh index --domains networking --types res          # filtered index

# Provider change intelligence (reads stubs from data/resources/ etc., calls GitHub API)
./avm.sh providers                                       # fetch all releases, azurerm+azapi (default)
./avm.sh providers --since 4.0.0                         # only releases >= 4.0.0
./avm.sh providers --provider azurerm --max-releases 10  # limit release count
./avm.sh providers --mode issues                         # open GitHub Issues → provider_issues.items
./avm.sh providers --mode all                            # releases + issues in one pass
./avm.sh providers --dry-run                             # preview without writing
./avm.sh providers --force                               # re-fetch even if checked within 24 h

# Module issue harvesting (fetches GitHub Issues from AVM module repos)
./avm.sh harvest                                         # harvest all modules (default labels)
./avm.sh harvest --domains networking --types res        # filtered harvest
./avm.sh harvest --modules avm-res-network-virtualnetwork  # single module
./avm.sh harvest --since 7d                              # skip if harvested within 7 days
./avm.sh harvest --force --dry-run                       # preview forced re-harvest

# Use-case tagging (infers functional tags from catalog metadata + resources_managed)
./avm.sh tag                                             # tag all untagged modules
./avm.sh tag --domains networking --types res            # filtered
./avm.sh tag --dry-run                                   # preview all inferred tags
./avm.sh tag --force                                     # re-classify all modules
./avm.sh tag --promote                                   # also seed enrichment.use_cases when empty

# Health dashboard (reads data/modules/, writes docs/site/index.html)
./avm.sh site                                            # generate static HTML dashboard
./avm.sh site --domains networking,compute               # dashboard for specific domains
./avm.sh site --output /tmp/avm-health.html --open       # custom path + open in browser
```

**Syntax validation** (run before committing any script change):
```bash
bash -n avm.sh
```

---

## Workflow for this repo

1. Run `./avm.sh sync` to refresh the catalog from upstream AVM CSVs
2. Run `./avm.sh setup --domains <domain(s)>` to regenerate `.config/modules.yaml`
3. Run `./avm.sh clone` (or filtered) to clone newly added repos
4. Run `./avm.sh cleanup` to remove repos that are no longer in your config
5. Commit only `data/modules/*.yaml` changes — never commit generated or cloned files

---

## Line endings

Per `.gitattributes`: `.sh`, `.yaml`, `.yml`, `.json`, `.tf`, `.tfvars` → LF. `.ps1` → CRLF.

---

## Module inventory (`data/modules/`)

**~148 Available module files** (out of 225 total upstream) across three subdirectories, one YAML per module:

```
data/modules/
  res/   avm-res-*.yaml   (resource modules)
  ptn/   avm-ptn-*.yaml   (pattern modules)
  utl/   avm-utl-*.yaml   (utility modules)
  catalog-manifest.yaml   auto-generated summary
```

Each module file has three sections:
- **`catalog:`** — auto-generated, refreshed by `./avm.sh sync`. Never hand-edit. Includes `last_synced` timestamp.
- **`analysis_*:`** — written by `./avm.sh check`. One block per dimension, never overwritten by sync.
- **`enrichment:`** — hand-maintained, **never overwritten by any tool**. Add your notes here.

```yaml
enrichment:
  version_pinned: "0.7.0"   # auto-filled by ./avm.sh check (terraform-metadata dim) from git tags
  terraform_version: "1.9.0"
  provider_version: "3.117.0"
  use_cases: ["alz", "hub-spoke"]
  known_issues:
    - title: "PE broken with azapi 2.x"
      status: open            # open | resolved | wontfix
      severity: medium        # low | medium | high
      workaround: "Pin azapi ~> 1.15"
      url: ""
  notes:
    - date: "2026-05-12"
      author: "your-github-handle"
      content: "Tested with private endpoints on v0.7.0 — works"
```

`data/catalog-manifest.yaml` — auto-generated summary (total, by_type, by_status).

Since each contributor works on a different module file, there are **never merge conflicts** in `data/modules/`.

---

- Do not create Terraform (`.tf`) files here — use the cloned module repos
- Do not commit `.config/modules.yaml` (gitignored by design)
- Do not commit `terraform-azurerm-avm-*/` directories
- Do not modify files inside cloned module dirs through this repo's git
