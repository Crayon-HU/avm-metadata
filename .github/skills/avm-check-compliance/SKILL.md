---
name: avm-check-compliance
description: 'Check AVM interface variable compliance for a module. Use when: verifying a module has lock, role_assignments, private_endpoints, diagnostic_settings, managed_identities, tags, enable_telemetry variables, AVM interface compliance, required AVM variables missing.'
argument-hint: 'Module name (e.g. "avm-res-network-virtualnetwork") or "all"'
---

# AVM Interface Compliance Check

Verifies that an AVM module declares the required interface variables as specified by the
[AVM Interface Requirements](https://azure.github.io/Azure-Verified-Modules/specs/tf/).

**Required variables for `res` modules (all 7):**
- `lock`
- `role_assignments`
- `private_endpoints`
- `diagnostic_settings`
- `managed_identities`
- `tags`
- `enable_telemetry`

**Required variables for `ptn`/`utl` modules (reduced set):**
- `tags`
- `enable_telemetry`

## When to Use

- Verifying a module meets AVM interface requirements before contributing
- Finding which required variables are missing in a module
- Bulk compliance audit across all modules

---

## Procedure

### Step 1 — Identify the module

Ask the user for the module name if not provided.

Verify the module YAML exists: `data/modules/{res|ptn|utl}/{name}.yaml`

### Step 2 — Run the analyzer

```bash
python3 scripts/analyze_module.py --module {name} --dimension avm-interface-compliance
```

Add `--force` to re-run even if recently checked. Set `GITHUB_TOKEN` for higher rate limits.

### Step 3 — Read results

Inspect the `analysis_avm_interface_compliance` block in the YAML:

```
analysis_avm_interface_compliance:
  checked_at: "..."
  status: pass | partial | fail | unchecked
  checks:
    lock:              { status: pass, evidence: "variables.tf:47" }
    role_assignments:  { status: pass, evidence: "variables.tf:89" }
    private_endpoints: { status: missing, finding: "No variable found" }
    ...
```

### Step 4 — Assess and report

For each check:
- `pass` — variable found; show file:line evidence
- `missing` — variable not declared; this is a compliance gap
- `unchecked` — .tf files could not be fetched (API issue)

**LLM assessment for `status: partial`:**
- Explain which required variables are missing and their purpose
- Note if missing variables are commonly omitted (e.g. `private_endpoints` for non-network modules)
- Suggest the standard variable declaration pattern from AVM specs

Report:
```
Module: avm-res-network-virtualnetwork (res)
Compliance: 6/7 required interface variables present

  ✓ lock                  variables.tf:47
  ✓ role_assignments       variables.tf:89
  ✗ private_endpoints      MISSING
  ✓ diagnostic_settings   variables.tf:123
  ✓ managed_identities    variables.tf:98
  ✓ tags                  variables.tf:11
  ✓ enable_telemetry      variables.tf:22

Status: partial ⚠
Assessment: private_endpoints is required for all AVM res modules. Add:
  variable "private_endpoints" { ... }
```

---

## Notes

- Module type determines the required variable set (res=7, ptn/utl=2)
- The check looks only at root-level .tf files, not submodules
- A `partial` status always requires LLM assessment in this step
