---
name: avm-check
description: 'All-in-one AVM module analysis. Use when: check module, any single dimension, full audit, comprehensive review, pre-publish checklist, module health check, terraform metadata, provider versions, resources managed, AVM interface compliance, required variables missing, security hardening, hardcoded locations, sensitive outputs, test coverage, examples directory, terratest, tftest, documentation quality, README missing, dependency health, version constraints, open-ended constraint.'
argument-hint: '[--modules NAME] [--domains DOMAIN] [--types res|ptn|utl] [--dimension metadata|compliance|security|tests|docs|deps|all]'
---

# AVM Module Check

Runs one or all 6 analysis dimensions across one module or a filtered set of modules, and reports findings with LLM assessment.

**Supported filters (same as `./avm.sh check`):**

| Flag | Example | Description |
|---|---|---|
| `--modules NAME` | `--modules avm-res-network-virtualnetwork` | Single module (short name) |
| `--domains DOMAIN` | `--domains networking,compute` | One or more domains (comma-separated) |
| `--types TYPE` | `--types res` | Module type: `res`, `ptn`, `utl` (comma-separated) |
| `--dimension DIM` | `--dimension compliance` | Single dimension; omit for all 6 |
| `--force` | | Re-run even if results are fresh |
| `--dry-run` | | Preview what would be analysed, no writes |

**Dimension shorthand map:**

| Shorthand | Full dimension name | YAML block | What it checks |
|---|---|---|---|
| `metadata` | `terraform-metadata` | `analysis_terraform_metadata` | TF version, provider constraints, resources/module calls |
| `compliance` | `avm-interface-compliance` | `analysis_avm_interface_compliance` | Required AVM interface variables |
| `security` | `security-hardening` | `analysis_security_hardening` | Hardcoded values, validation blocks, sensitive outputs |
| `tests` | `test-coverage` | `analysis_test_coverage` | examples/, tests/, *.go / *.tftest.hcl |
| `docs` | `doc-quality` | `analysis_doc_quality` | README existence, length, required section headers |
| `deps` | `dependency-health` | `analysis_dependency_health` | Version constraint style (reads terraform-metadata) |
| `all` _(default)_ | _(all six above)_ | _(all blocks)_ | Complete quality audit |

## When to Use

- Pre-publish quality review of a single module — use `--modules NAME`
- Spot-check one concern across all networking res modules — use `--domains networking --types res --dimension compliance`
- Periodic bulk health check across a domain
- Updating stale analysis blocks after a new module release

---

## Procedure

### Step 1 — Parse input

Extract from the user message:

- **Scope** — one of:
  - `--modules NAME` — short form `avm-res-network-virtualnetwork` or full `terraform-azurerm-*` (strip prefix). Comma-separated for multiple.
  - `--domains DOMAIN[,DOMAIN]` — e.g. `networking`, `compute,containers`
  - `--types TYPE[,TYPE]` — `res`, `ptn`, `utl` (comma-separated)
  - Any combination of `--domains` + `--types`
- **Dimension** (optional): one of `metadata`, `compliance`, `security`, `tests`, `docs`, `deps`, or `all`. Default to `all`.
- **Flags**: `--force`, `--dry-run` if mentioned.

Map dimension shorthand to the full name using the table above.

If no scope is given, ask the user which module or domain/type combination to check.

**Determine run mode:**
- **Single-module mode**: `--modules` resolves to exactly one module → full LLM assessment + detailed per-dimension report.
- **Bulk mode**: `--domains`/`--types` filter, or `--modules` with multiple names → summary table only; no deep LLM assessment per module.

### Step 2 — Validate scope

**For `--modules`:** verify the module YAML exists:

```bash
find data/modules -name "{name}.yaml" | head -1
```

If not found, suggest running `./avm.sh sync`.

**For `--domains`/`--types`:** list the modules that will be checked to confirm scope:

```bash
python3 scripts/generate_config.py --domains {domains} --types {types} --list-only 2>/dev/null \
  || find data/modules -name "*.yaml" | xargs grep -l "domain: {domain}" | sed 's|.*/||;s|\.yaml||'
```

Show the user the module count before proceeding for bulk runs (>5 modules).

### Step 3 — Ensure repos are cloned

**Single module:**

```bash
ls terraform-azurerm-{name}/ 2>/dev/null | head -1 || echo "NOT_CLONED"
```

If not cloned:

```bash
./avm.sh clone --modules {name}
```

**Bulk (domain/type filter):**

```bash
./avm.sh clone --domains {domains} --types {types}
```

### Step 4 — Run the analyzer

Build the command from the parsed filters:

```bash
# Single module, all dimensions
python3 scripts/analyze_module.py --modules {name}

# Single module, specific dimension
python3 scripts/analyze_module.py --modules {name} --dimension {full-dimension-name}

# Domain/type filter, all dimensions
python3 scripts/analyze_module.py --domains {domains} --types {types}

# Domain/type filter, specific dimension
python3 scripts/analyze_module.py --domains {domains} --types {types} --dimension {full-dimension-name}
```

Append `--force` or `--dry-run` if requested.

> **Dependency note:** `deps` automatically runs `terraform-metadata` first if its block is absent or stale. When running `all`, the internal dependency order is handled automatically.

### Step 5 — Read analysis results

**Single-module mode:** open the module YAML and read the relevant `# BEGIN ANALYSIS:{dim}` … `# END ANALYSIS:{dim}` block(s). Read all 6 blocks for `all`, or only the requested block for a specific dimension.

**Bulk mode:** for each module in scope, read only the `status:` line from the relevant analysis block(s) — do not read every detail. Build a summary table.

### Step 6 — LLM assessment (single-module mode only)

For every check with `status: partial`, `status: fail`, or `status: missing`:

1. Identify the specific failing checks.
2. Add an `llm_assessment` field inside the dimension block in the YAML file with a brief qualitative explanation (1–3 sentences) and concrete remediation steps.

**Dimension-specific guidance:**

**`metadata`** — `status: partial` or `fail`:
- Check `errors` for filesystem read failures (module not cloned, missing `.tf` files).
- Note any missing `required_version` or empty provider/resource lists.

**`compliance`** — missing variables:
- Explain the variable's purpose per the AVM interface spec.
- Note if it is commonly omitted for this module type (`private_endpoints` required for all `res`; `ptn`/`utl` only need `tags` + `enable_telemetry`).
- Suggest the standard variable declaration pattern from the AVM specs.

**`security`** — per failing check:
- `hardcoded_locations`: multi-region / geo-compliance risk; suggest `variable "location" {}` or `azurerm_resource_group.this.location`.
- `validation_blocks`: heuristic — absence is a warning, not a hard failure; check `location`, `sku`, `kind` variables.
- `sensitive_outputs`: add `sensitive = true` to the output block.

**`tests`** — missing items:
- `examples_dir` missing: required for `Available`-status modules; suggest `examples/default/`.
- `test_files` missing: check module status; explain Terratest (`.go`) vs native tests (`.tftest.hcl`).

**`docs`** — partial/missing:
- `readme_exists` missing: critical gap; suggest the AVM module documentation template.
- `readme_length` partial: likely a stub — check if it is just auto-generated badges.
- `required_sections` partial: `## Requirements` is typically auto-generated by `terraform-docs`; suggest adding a `.terraform-docs.yml`.

**`deps`** — failing constraints:
- `terraform_version_upper_bound` missing: suggest `">= 1.9, < 2.0"`.
- `provider_constraint_style` fail: open-ended `>=`; AVM convention is `~>` (e.g. `~> 4.0`).

### Step 7 — Report

**Single-module, specific dimension:**

```
Module: {name} ({type})
Checked: {timestamp}

{DIMENSION} — {STATUS}

  ✓ {check_name}   {evidence}
  ⚠ {check_name}   {finding}
  ✗ {check_name}   {finding}

Assessment: {llm_assessment if present}
```

**Single-module, all dimensions:**

```
═══════════════════════════════════════════════════════════
AVM MODULE CHECK: {name} ({type})
Checked: {timestamp}
═══════════════════════════════════════════════════════════

DIMENSION       STATUS     DETAILS
─────────────── ────────── ──────────────────────────────
metadata        ✓ pass     TF >= 1.9 < 2.0 | azurerm ~> 4.0 | 15 types
compliance      ⚠ partial  6/7 — private_endpoints missing
security        ✓ pass     No hardcoded locations; validation blocks present
tests           ✓ pass     examples/ (3 items); 2 .go test files
docs            ⚠ partial  Missing ## Requirements section
deps            ✓ pass     All providers use ~> constraints

OVERALL: PARTIAL ⚠

FINDINGS
────────
compliance: private_endpoints variable is missing. Required for all AVM res modules.
  Add a variable "private_endpoints" block following the standard AVM pattern.

docs: The ## Requirements section is typically auto-generated by terraform-docs.
  Add a .terraform-docs.yml configuration to generate it.
```

**Bulk mode summary (domain/type filter):**

```
AVM CHECK — {domains} / {types} / {dimension}
Checked: {timestamp}   Modules: {N}

MODULE                                    STATUS
──────────────────────────────────────── ────────
avm-res-network-virtualnetwork           ✓ pass
avm-res-network-networksecuritygroup     ⚠ partial
avm-res-network-publicipaddress          ✓ pass
...

SUMMARY: {pass} pass / {partial} partial / {fail} fail / {unchecked} unchecked

Modules with findings:
  avm-res-network-networksecuritygroup — compliance: partial, docs: partial
```

---

## Notes

- All 6 dimensions write to the module YAML atomically — no partial writes.
- `dependency-health` reads from `terraform-metadata`; both run together when using `all` or `deps` alone.
- Analysis reads `.tf` files from the locally cloned repo — no network calls required.
- LLM assessment is only written for single-module runs; bulk runs produce a summary table only.
- After writing `llm_assessment` fields, the module YAML is a complete audit record.
