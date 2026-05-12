---
name: avm-check-security
description: 'Security hardening check for an AVM module. Use when: checking for hardcoded locations, missing validation blocks, sensitive outputs without sensitive=true, security review of terraform module.'
argument-hint: 'Module name (e.g. "avm-res-network-virtualnetwork") or "all"'
---

# AVM Security Hardening Check

Scans an AVM module's `.tf` files for common security anti-patterns:

1. **Hardcoded locations** — Azure region strings (e.g. `"eastus"`, `"westeurope"`) hard-coded in
   resource or variable definitions instead of being passed as parameters.

2. **Validation blocks** — Whether any `variable` block includes a `validation {}` block to
   restrict accepted values. At least one validation block is expected in well-hardened modules.

3. **Sensitive outputs** — Output blocks whose names contain `key`, `secret`, `password`,
   `token`, `credential`, or `cert` but do not declare `sensitive = true`.

## When to Use

- Security review before contributing or consuming a module
- Identifying modules with hardcoded infrastructure assumptions
- Finding outputs that leak secrets without sensitivity protection

---

## Procedure

### Step 1 — Identify the module

Ask the user for the module name if not provided.

### Step 2 — Run the analyzer

```bash
python3 scripts/analyze_module.py --module {name} --dimension security-hardening
```

Set `GITHUB_TOKEN` for higher rate limits. Add `--force` to bypass the staleness cache.

### Step 3 — Read results

Inspect the `analysis_security_hardening` block:

```
analysis_security_hardening:
  checked_at: "..."
  status: pass | partial | fail
  checks:
    hardcoded_locations: { status: pass, evidence: "No hardcoded locations found" }
    validation_blocks:   { status: partial, finding: "No validation {} blocks found" }
    sensitive_outputs:   { status: fail, finding: "Output 'admin_key' lacks sensitive = true" }
```

### Step 4 — Assess and report

**LLM assessment for non-`pass` checks:**

`hardcoded_locations` failing:
- Explain why hardcoded regions are problematic (multi-region deployments, geo-compliance)
- Suggest: `variable "location" {}` or using `azurerm_resource_group.this.location`

`validation_blocks` partial:
- Note this is a heuristic (not every variable needs validation)
- Check if critical variables like `location`, `sku`, `kind` have validation blocks
- Suggest common validation patterns

`sensitive_outputs` failing:
- This is a security finding — the output name suggests sensitive data
- Suggest adding `sensitive = true` to the output block

Report summary:
```
Module: avm-res-network-virtualnetwork
Security Hardening:

  ✓ hardcoded_locations   No hardcoded locations found
  ⚠ validation_blocks     No validation {} blocks found (informational)
  ✗ sensitive_outputs     Output "admin_key" lacks sensitive = true

Status: fail ✗
Assessment: ...
```

---

## Notes

- Hardcoded location check ignores example/test files (root-level only)
- Validation block check is heuristic: absence = warning, not a hard failure
- Sensitive output check is based on output name pattern matching
