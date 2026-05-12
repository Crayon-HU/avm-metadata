# avm-metadata — Azure Verified Modules Workspace

This is the **metadata repository** for managing [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/) Terraform modules. It contains no Terraform code of its own — instead it ties together the upstream AVM module repositories into a single VSCode multi-root workspace, organized by domain.

Modules are sourced directly from the official [Azure GitHub organization](https://github.com/orgs/Azure/repositories?q=terraform-azurerm-avm) and include all three AVM module types: **resource** (`res`), **pattern** (`ptn`), and **utility** (`utl`).

---

## Prerequisites

- **git** — the only required tool for cloning

---

## Getting Started

### 1. Clone this metadata repo

```bash
git clone https://github.com/Crayon-HU/avm-metadata.git
cd avm-metadata
```

### 2. Generate the module inventory

Select the domains you want to work with. This merges the selected `.config/{domain}.yaml` files into `.config/modules.yaml`.

**macOS / Linux:**
```bash
./scripts/generate_modules.sh                        # interactive menu
./scripts/generate_modules.sh --domains all          # all domains
./scripts/generate_modules.sh --domains networking,compute,identity
```

**Windows (PowerShell):**
```powershell
.\scripts\generate_modules.ps1                       # interactive menu
.\scripts\generate_modules.ps1 -Domains all
.\scripts\generate_modules.ps1 -Domains networking,compute,identity
```

### 3. Clone the module repositories

```bash
./scripts/clone_repos.sh                  # clone everything in modules.yaml
./scripts/clone_repos.sh --domain networking   # one domain only
./scripts/clone_repos.sh --type ptn            # pattern modules only
./scripts/clone_repos.sh --full               # full history (default: --depth 1)
```

### 4. Open the workspace in VSCode

```bash
code avm-metadata.code-workspace          # all modules (root)
code avm-networking.code-workspace        # networking domain only
code avm-compute.code-workspace           # compute domain only
```

> Open the domain-specific workspace to load only the modules relevant to your current task.

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

---

## Repository Layout

```
.config/
  networking.yaml        ← domain module definitions (committed, source of truth)
  compute.yaml
  containers.yaml
  identity.yaml
  storage.yaml
  management.yaml
  recovery.yaml
  web.yaml
  data.yaml
  platform.yaml
  modules.yaml           ← GENERATED (gitignored) — re-run generate_modules.sh

scripts/
  generate_modules.sh    ← merges selected domains → .config/modules.yaml
  generate_modules.ps1   ← PowerShell variant
  clone_repos.sh         ← clones repos from modules.yaml
  clone_repos.ps1        ← PowerShell variant
  generate_workspaces.sh ← regenerates .code-workspace files from domain YAMLs

avm-metadata.code-workspace      ← root VSCode workspace (all modules via autodetect)
avm-networking.code-workspace    ← networking domain workspace
avm-compute.code-workspace       ← compute domain workspace
avm-containers.code-workspace    ← containers domain workspace
avm-identity.code-workspace      ← identity domain workspace
avm-storage.code-workspace       ← storage domain workspace
avm-management.code-workspace    ← management domain workspace
avm-recovery.code-workspace      ← recovery domain workspace
avm-web.code-workspace           ← web domain workspace
avm-data.code-workspace          ← data domain workspace
avm-platform.code-workspace      ← platform domain workspace
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

1. Find the module in the [AVM Terraform index](https://azure.github.io/Azure-Verified-Modules/indexes/terraform/)
2. Add an entry to the appropriate `.config/{domain}.yaml`
3. Re-run `scripts/generate_modules.sh` (select the affected domain)
4. Re-run `scripts/generate_workspaces.sh` to update `.code-workspace` files
5. Run `scripts/clone_repos.sh` to clone the new repo

The new module directory (`terraform-azurerm-avm-*`) is automatically gitignored by the `.gitignore` wildcard pattern.
