---
name: avm-check-tests
description: 'Test coverage check for an AVM module. Use when: checking if a module has tests, verifying examples exist, checking for e2e tests, test files missing, tftest or terratest coverage.'
argument-hint: 'Module name (e.g. "avm-res-network-virtualnetwork") or "all"'
---

# AVM Test Coverage Check

Verifies that an AVM module has adequate test and example coverage by checking for:

1. **`examples/`** — directory at the repo root with at least one item (standard AVM convention)
2. **Test files** — `.go` (Terratest) or `.tftest.hcl` (native Terraform test) files in `tests/`

## When to Use

- Verifying a module follows AVM testing conventions
- Checking if a module has runnable examples
- Identifying gaps in test coverage before publishing

---

## Procedure

### Step 1 — Identify the module

Ask the user for the module name if not provided.

### Step 2 — Run the analyzer

```bash
python3 scripts/analyze_module.py --modules {name} --dimension test-coverage
```

Add `--force` to bypass cache.

> **Requires the repo to be cloned.** Run `./avm.sh clone --modules {name}` first if needed.

### Step 3 — Read results

Inspect the `analysis_test_coverage` block:

```
analysis_test_coverage:
  checked_at: "..."
  status: pass | partial | fail
  checks:
    examples_dir: { status: pass,    evidence: "examples/ contains 3 item(s)" }
    test_files:   { status: missing, finding: "tests/ directory not found" }
```

Check values:
- `pass` — directory/files found
- `partial` — directory exists but contains no test files
- `missing` — directory does not exist

### Step 4 — Assess and report

**LLM assessment for non-`pass` checks:**

`examples_dir` missing:
- This is required by AVM for `Available`-status modules
- Suggest creating `examples/default/` with a minimal module call

`test_files` missing or partial:
- Check module status: `Proposed` modules may not have tests yet
- For `Available` modules: missing tests is a gap
- Explain difference between Terratest (`.go`) and native tests (`.tftest.hcl`)

Report:
```
Module: avm-res-network-virtualnetwork
Test Coverage:

  ✓ examples_dir   examples/ contains 3 item(s)
  ⚠ test_files     tests/ exists but contains no .go or .tftest.hcl files

Status: partial ⚠
Assessment: The module has usage examples but no automated tests. ...
```

---

## Notes

- Only checks for file/directory presence, not quality or executability of tests
- Reads `examples/` and `tests/` from the locally cloned repo — no network calls required
