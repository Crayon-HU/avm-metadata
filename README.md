# avm-metadata — Azure Verified Modules Workspace

This is the **metadata repository** for managing [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/) Terraform modules. It contains no Terraform code of its own — instead it ties together the upstream AVM module repositories into a single VSCode multi-root workspace, organized by domain.

Modules are sourced directly from the official [Azure GitHub organization](https://github.com/orgs/Azure/repositories?q=terraform-azurerm-avm) and include all three AVM module types: **resource** (`res`), **pattern** (`ptn`), and **utility** (`utl`).

---

## Prerequisites

- **git** — for cloning module repos
- **Python 3.9+** — for all automation scripts (`avm.sh` delegates to them)

---

## Getting Started

### 1. Clone this metadata repo

```bash
git clone https://github.com/Crayon-HU/avm-metadata.git
cd avm-metadata
```

### 2. Sync the module catalog from upstream AVM CSVs

Fetches the official AVM index CSVs and creates/updates one YAML file per module under `data/modules/`. Only `Available` modules are synced by default.

```bash
./avm.sh sync              # fetch upstream AVM CSVs → data/modules/
./avm.sh sync --dry-run    # preview changes without writing
```

### 3. Generate the module inventory

Reads `data/modules/` and writes `.config/modules.yaml` — the list of repos to clone. Only `Available` modules are included by default.

```bash
./avm.sh setup --domains all                          # all domains
./avm.sh setup --domains networking,compute           # specific domains
./avm.sh setup --domains networking --types res,ptn   # filtered by type
./avm.sh setup --dry-run                              # preview
```

> **Interactive mode:** omit `--domains`/`--types` for a menu-driven selection.

### 4. Clone the module repositories

```bash
./avm.sh clone                                          # clone all from modules.yaml
./avm.sh clone --domains networking --types res         # filtered clone
./avm.sh clone --modules avm-res-network-virtualnetwork # single module
```

Git identity is prompted interactively on first clone (set per-repo, never in global config).

### 5. Open the workspace in VSCode

```bash
code avm.code-workspace    # all modules
```

---

## Key Commands

```bash
# Catalog
./avm.sh sync                                       # refresh catalog from upstream AVM CSVs
./avm.sh sync --force                               # force-rewrite all module files
./avm.sh sync --include-proposed                    # also include Proposed-status modules
./avm.sh setup --domains all                        # generate .config/modules.yaml

# Repo management
./avm.sh clone                                      # clone repos in modules.yaml
./avm.sh update --parallel 10                       # pull latest (parallel)
./avm.sh fetch --parallel 30                        # fetch remotes without merging
./avm.sh status                                     # show dirty / behind repos + staleness
./avm.sh cleanup                                    # remove repos not in modules.yaml
./avm.sh cleanup --dry-run                          # preview cleanup
./avm.sh cleanup --force                            # remove even dirty repos

# Branch management
./avm.sh branch create feature/my-fix              # create branch in all repos
./avm.sh branch checkout feature/my-fix --fallback # checkout (stay put if missing)
./avm.sh branch delete feature/my-fix              # delete branch

# Stash / reset
./avm.sh stash                                     # stash all changes
./avm.sh stash pop
./avm.sh reset --hard                              # hard reset all repos to HEAD

# Arbitrary command
./avm.sh run git log --oneline -3

# Analysis
./avm.sh check --module avm-res-network-virtualnetwork   # full analysis (all 6 dims)
./avm.sh check --dimension test-coverage                  # one dim, all modules
./avm.sh check --domains networking --dimension doc-quality
./avm.sh scrape --module avm-res-network-virtualnetwork   # terraform-metadata alias

# Reporting (read-only)
./avm.sh report --scores                                  # weighted compliance scorecard
./avm.sh report --scores --domains networking --min-score 80  # show modules scoring < 80
./avm.sh report --issues                                  # cross-module open issue rollup
./avm.sh report --issues --severity critical,high         # filter by severity
./avm.sh report --json                                    # export catalog → data/catalog.json
```

Run `./avm.sh help` or `./avm.sh <command> --help` for full flag reference.

---

## Domain Overview

| Domain | res | ptn | utl | Description |
|---|---|---|---|---|
| `networking` | 26 | 4 | 3 | VNets, firewalls, DNS, load balancing, private endpoints, connectivity |
| `compute` | 9 | — | 3 | Virtual machines, scale sets, disks, compute infrastructure |
| `containers` | 6 | 3 | — | AKS, ACR, Container Apps, Container Instances |
| `identity` | 3 | 1 | — | Key Vault, managed identity, role assignment |
| `storage` | 1 | 1 | — | Storage accounts and storage-adjacent patterns |
| `management` | 7 | 4 | 1 | Resource management, observability, monitoring, policy |
| `recovery` | 3 | — | — | Backup vaults, Recovery Services, data protection |
| `web` | 5 | — | — | App Service, Web/Function Apps, Static Web Apps |
| `data` | 8 | — | — | Databricks, PostgreSQL, MySQL, Cosmos DB, SQL Server, Data Factory |
| `platform` | — | 3 | 4 | Cross-cutting: ALZ foundations, regions, interfaces, SKU finder |

> Counts reflect `Available`-status modules. `Proposed` and `Deprecated` modules exist in upstream but are excluded by default.

---

## Repository Layout

```
data/modules/                  ← one YAML per module (source of truth for catalog)
  res/   avm-res-*.yaml        ← resource modules
  ptn/   avm-ptn-*.yaml        ← pattern modules
  utl/   avm-utl-*.yaml        ← utility modules
  catalog-manifest.yaml        ← auto-generated summary

scripts/
  generate_config.py           ← data/modules/ → .config/modules.yaml
  manage_repos.py              ← multi-repo git ops (clone/update/fetch/…)
  sync_catalog.py              ← upstream AVM CSVs → data/modules/ catalog sections
  analyze_module.py            ← multi-dimensional analysis → analysis_* blocks
  report.py                    ← read-only reports: scores, issues, JSON export

avm.sh                         ← unified operator entry point
.github/skills/                ← Copilot skill procedures
avm.code-workspace             ← VSCode multi-root workspace

terraform-azurerm-avm-*/       ← cloned module repos (gitignored)
```

---

## Module Types

| Type | Prefix | Description |
|---|---|---|
| `res` | `terraform-azurerm-avm-res-*` | Resource modules — deploy a single Azure resource type |
| `ptn` | `terraform-azurerm-avm-ptn-*` | Pattern modules — opinionated multi-resource compositions |
| `utl` | `terraform-azurerm-avm-utl-*` | Utility modules — shared helpers (regions, interfaces, SKUs) |

---

## Adding a New Module

New modules appear automatically when upstream AVM publishes them and `sync` is re-run:

```bash
./avm.sh sync          # picks up new Available modules from upstream CSVs
./avm.sh setup --domains <domain>   # regenerate modules.yaml for that domain
./avm.sh clone         # clone newly added repos
```

To remove repos that are no longer in your config:

```bash
./avm.sh cleanup --dry-run   # preview
./avm.sh cleanup             # remove clean orphaned repos
```
