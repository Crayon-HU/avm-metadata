# Copilot Instructions — avm-metadata Workspace

## What this repo is

This is a **metadata repository** for [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/). It contains no Terraform code of its own. Its purpose is to organize and bootstrap the upstream AVM module repositories into a VSCode multi-root workspace, grouped by domain.

Every directory whose name starts with `terraform-azurerm-avm-*` is a **cloned external repository** — it has its own `.git` history and its own Copilot instructions. Do not modify those repos through this metadata repo.

---

## Workspace layout

```
.config/                        Source-of-truth domain YAML files (committed)
  {domain}.yaml                 One file per domain — module inventory
  modules.yaml                  GENERATED (gitignored) — merged from selected domains

scripts/
  generate_config.py            Reads data/modules/ → writes .config/modules.yaml (called by avm.sh setup)
  clone_repos.sh/.ps1           Clones repos from modules.yaml (called by avm.sh clone)
  update_repos.sh/.ps1          Pulls latest changes in cloned repos (called by avm.sh update)
  sync_catalog.py               Fetches upstream AVM CSVs → refreshes data/modules/ catalog sections
  analyze_module.py             Multi-dimensional analysis → populates analysis_* blocks in data/modules/

avm.sh                          Unified operator entry point — delegates to scripts/
.github/skills/                 Copilot skill procedures — also delegate to scripts/
avm.code-workspace              Root workspace — includes . + all modules

terraform-azurerm-avm-*/        Cloned module repos (gitignored — not part of this repo)
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

`generate_config.py` reads `catalog.repo_url`, `catalog.domain`, `catalog.type`, `catalog.display_name` from `data/modules/{type}/*.yaml` catalog blocks. Modules with `status: Deprecated` are excluded by default (`--include-deprecated` to override).

---

## Entry point

`avm.sh` is the single unified wrapper for all automation. Prefer it over calling `scripts/` directly (skills are the exception — they call `scripts/` directly).

```bash
./avm.sh help                                       # show all commands and options
./avm.sh setup --domains all                        # generate .config/modules.yaml
./avm.sh setup --domains networking,compute --types res
./avm.sh clone                                      # clone all modules from modules.yaml
./avm.sh clone --domain networking --type res       # filtered clone
./avm.sh update                                     # git pull --ff-only in all cloned repos
./avm.sh sync                                       # fetch upstream CSVs → refresh data/modules/{res,ptn,utl}/*.yaml catalog section
./avm.sh sync --dry-run                             # preview changes without writing
./avm.sh scrape                                     # alias: check --dimension terraform-metadata (scrape all modules)
./avm.sh scrape --module avm-res-network-virtualnetwork  # scrape one module
./avm.sh check --module avm-res-network-virtualnetwork   # full analysis (all 6 dimensions)
./avm.sh check --dimension avm-interface-compliance      # one dimension, all modules
./avm.sh check --dry-run                                 # preview analysis changes
```

**Syntax validation** (run before committing any script change):
```bash
bash -n avm.sh scripts/*.sh
```

---

## Workflow for this repo

1. Edit `.config/{domain}.yaml` — add entries or **comment them out** (non-core modules use `# - name:` blocks; do not delete them)
2. Run `./avm.sh setup --domains <changed-domain>` to regenerate `.config/modules.yaml`
3. Run `./avm.sh clone` (or `--domain`/`--type` filtered) to clone newly added repos
4. Run `./avm.sh sync` to refresh the catalog from upstream AVM CSVs
5. Commit only the `.config/{domain}.yaml` and `data/modules/*.yaml` changes — never commit generated or cloned files

---

## Line endings

Per `.gitattributes`: `.sh`, `.yaml`, `.yml`, `.json`, `.tf`, `.tfvars` → LF. `.ps1` → CRLF.

---

## Module inventory (`data/modules/`)

**225 module files** across three subdirectories, one YAML per module:

```
data/modules/
  res/   avm-res-*.yaml   (152 resource modules)
  ptn/   avm-ptn-*.yaml   (59 pattern modules)
  utl/   avm-utl-*.yaml   (14 utility modules)
  catalog-manifest.yaml   auto-generated summary
```

- **`catalog:`** — auto-generated, refreshed by `./avm.sh sync`. Never hand-edit this section.
- **`enrichment:`** — hand-maintained, **never overwritten by sync**. Add your notes here.

```yaml
enrichment:
  version_pinned: "0.7.0"
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
