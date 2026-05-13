---
name: avm-check-metadata
description: 'Scrape Terraform metadata from an AVM module repo. Use when: checking provider versions, terraform version constraint, resources managed, module calls, what providers a module uses, what resources a module creates.'
argument-hint: 'Module name (e.g. "avm-res-network-virtualnetwork") or "all"'
---

# AVM Terraform Metadata Check

Fetches `.tf` files from an AVM module's GitHub repo and populates the
`analysis_terraform_metadata` block in the module's YAML file with:
- Terraform `required_version` constraint
- `required_providers` (source + version constraint)
- Resource types managed (`res`/`utl`) or module calls (`ptn`)

## When to Use

- Checking which Terraform or provider version a module requires
- Finding which Azure resource types a module manages
- Updating stale metadata after a module release
- Preparing for a dependency-health check (which depends on this dimension)

---

## Procedure

### Step 1 — Identify the module

Ask the user for the module name if not provided. Accepted formats:
- Short name: `avm-res-network-virtualnetwork`
- All modules: omit `--module` flag

Verify the module YAML exists: `data/modules/{res|ptn|utl}/{name}.yaml`

### Step 2 — Run the analyzer

```bash
python3 scripts/analyze_module.py --modules {name} --dimension terraform-metadata
```

Add `--force` to re-run even if recently checked. Add `--dry-run` to preview.

> **Requires the repo to be cloned.** Run `./avm.sh clone --modules {name}` first if the
> directory `terraform-azurerm-avm-*/{name}` does not exist locally.

### Step 3 — Read results

Read the updated YAML file and inspect the `analysis_terraform_metadata` block:

```
# BEGIN ANALYSIS:terraform-metadata
analysis_terraform_metadata:
  checked_at: "..."
  status: pass | partial | fail | unchecked
  errors: [...]
  terraform_constraints:
    required_version: "..."
    required_providers:
      azurerm: { source: "...", version_constraint: "..." }
  resources_managed:
    azurerm: [azurerm_virtual_network, ...]
# END ANALYSIS:terraform-metadata
```

### Step 4 — Assess and report

If `status: partial` or `status: fail`:
- Review `errors` for filesystem read failures (module not cloned, missing `.tf` files)
- Verify the module repo is cloned: `ls terraform-azurerm-avm-*/{name}/`
- Note any missing constraints or empty resource lists

Report a concise summary:
```
Module: avm-res-network-virtualnetwork
Terraform: >= 1.9, < 2.0
Providers: azurerm ~> 4.0, azapi ~> 2.4, modtm ~> 0.3, random ~> 3.5
Resources: azurerm (12 types), azapi (3 types)
Status: pass ✓
```

---

## Notes

- This is the `./avm.sh scrape` alias: `./avm.sh scrape --modules NAME`
- The `dependency-health` dimension depends on this data being present
- Analysis reads `.tf` files from the locally cloned repo — no network calls required
