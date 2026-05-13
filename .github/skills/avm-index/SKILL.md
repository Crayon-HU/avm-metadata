---
name: avm-index
description: 'Build the resource-to-module index. Use when: build resource index, index resources, provider resource index, which modules use a resource, resource to module mapping, provider change intelligence phase 1, index terraform resources, datasources index, rebuild index, data/resources.'
argument-hint: '[--domains DOMAIN] [--types res|ptn|utl] [--dry-run]'
---

# AVM Index Skill

Builds a provider-grouped resource-to-module index from all `analysis_terraform_metadata` blocks in `data/modules/`. Collects all five Terraform symbol types and writes `data/resources/{provider}.yaml`.

This is **Phase 1 of the Provider Change Intelligence track** — the index it produces is the foundation for changelog diffing (Phase 2) and findings surfacing (Phase 4).

**Symbol types collected:**

| Symbol type | Terraform block | YAML key |
|---|---|---|
| resource | `resource "<type>" "<name>"` | `resources_managed` |
| datasource | `data "<type>" "<name>"` | `datasources_managed` |
| function | `provider::<ns>::<fn>()` | `functions_used` |
| ephemeral | `ephemeral "<type>" "<name>"` | `ephemeral_managed` |
| action | `actions "<type>" "<name>"` | `actions_managed` |

---

## When to Use

- After running `./avm.sh check` on a set of modules — rebuild the index to capture new analysis data
- Before running a provider changelog diff — the index is a prerequisite
- To answer "which modules use `azurerm_virtual_network`?"
- After adding or updating modules in the catalog

---

## Procedure

### Step 1 — Rebuild the index

```bash
./avm.sh index
```

For a subset:

```bash
./avm.sh index --domains networking --types res
./avm.sh index --dry-run   # preview without writing
```

### Step 2 — Report what was indexed

After the script completes, read its output and summarise:
- How many provider files were written (e.g., `data/resources/azurerm.yaml`)
- Total resource types indexed per provider
- Whether any modules were skipped (no analysis data yet)

### Step 3 — Surface useful insights (optional)

If the user asks follow-up questions like "which modules use `azurerm_virtual_network`?" or "how many modules depend on azapi?", read the relevant `data/resources/{provider}.yaml` and answer directly from the YAML data.

---

## Output location

`data/resources/{provider}.yaml` — committed to the repo as part of the catalog, never gitignored.

Example files written:
- `data/resources/azurerm.yaml`
- `data/resources/azapi.yaml`
- `data/resources/azuread.yaml`
