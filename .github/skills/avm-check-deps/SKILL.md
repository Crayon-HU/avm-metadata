---
name: avm-check-deps
description: 'Dependency health check for an AVM module. Use when: checking version constraints, provider versions pinned, terraform version has upper bound, open-ended >= constraint, dependency hygiene.'
argument-hint: 'Module name (e.g. "avm-res-network-virtualnetwork") or "all"'
---

# AVM Dependency Health Check

Analyses version constraint quality in an AVM module using the `terraform-metadata` block
(no extra GitHub API calls if terraform-metadata is already present).

**Checks:**

1. **`terraform_version_upper_bound`** — `required_version` should have an upper bound
   (`< 2.0` or a `~>` pessimistic constraint) to prevent compatibility surprises.

2. **`provider_constraint_style`** — All `required_providers` should use `~>` (pessimistic)
   or pinned `= x.y.z` constraints, NOT open-ended `>=` without an upper bound.

## When to Use

- Checking whether a module's version constraints follow AVM best practices
- Identifying modules with open-ended provider constraints that may break on upgrades
- Pre-release dependency audit

---

## Procedure

### Step 1 — Identify the module

Ask the user for the module name if not provided.

### Step 2 — Run the analyzer

```bash
python3 scripts/analyze_module.py --module {name} --dimension dependency-health
```

The script automatically runs `terraform-metadata` first if the module's block is
absent or stale, then derives dependency health without extra API calls.

Set `GITHUB_TOKEN` for rate limits (needed if terraform-metadata is also being refreshed).

### Step 3 — Read results

Inspect the `analysis_dependency_health` block:

```
analysis_dependency_health:
  checked_at: "..."
  status: pass | partial | fail
  checks:
    terraform_version_upper_bound: { status: pass, evidence: 'required_version = ">= 1.9, < 2.0"' }
    provider_constraint_style:     { status: fail, finding: "Open-ended >= constraint: azurerm: \">= 3.0\"" }
```

### Step 4 — Assess and report

**LLM assessment for non-`pass` checks:**

`terraform_version_upper_bound` partial/missing:
- Explain that without an upper bound, future Terraform major versions may break the module
- Suggest: `required_version = ">= 1.9, < 2.0"` or `>= 1.9, < 3.0` for forward compatibility

`provider_constraint_style` fail:
- Open-ended `>=` means the module will accept any future breaking provider version
- AVM convention: use `~>` to allow patch/minor updates but restrict majors
  e.g. `version_constraint: "~> 4.0"` for azurerm 4.x

Report:
```
Module: avm-res-network-virtualnetwork
Dependency Health:

  ✓ terraform_version_upper_bound   ">= 1.9, < 2.0"
  ✗ provider_constraint_style       Open-ended >=: azurerm: ">= 3.116, < 5.0"... wait, this has upper bound

Status: pass ✓
```

---

## Notes

- This check reads from `analysis_terraform_metadata` — run `avm-check-metadata` first or use
  `avm-audit` which runs all dimensions in dependency order
- `unchecked` status means terraform-metadata was unavailable; resolve that first
- The `~>` constraint allows the rightmost version component to increase (e.g. `~> 4.0` allows 4.x)
