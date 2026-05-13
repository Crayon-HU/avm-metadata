---
name: avm-issues
description: 'Surface open enrichment issues across AVM modules. Use when: list open issues, triage issues, module issues, known bugs, what is broken, severity, issue rollup, cross-module issues, open known_issues, issue summary, find critical issues, high severity issues.'
argument-hint: '[--domains DOMAIN] [--types res|ptn|utl] [--severity critical|high|medium|low] [--output FILE]'
---

# AVM Issues Skill

Surfaces all open `enrichment.known_issues` entries across modules, grouped by severity. Produces a triage table without modifying any files.

> **⚠️ Scope:** This skill reads `enrichment.known_issues` **only** — hand-curated entries added by operators.
> On a fresh repo with no manual enrichment it will correctly show **0 open issues**.
>
> For automated issue data, see:
> - `module_issues` (written by `avm harvest`) — open GitHub issues on AVM module repos
> - `provider_issues` and `provider_updates` (written by Phase 2/3 scripts) — Terraform provider changelog and issues

**Supported filters:**

| Flag | Example | Description |
|---|---|---|
| `--domains DOMAIN` | `--domains networking,compute` | One or more domain slugs (comma-separated) |
| `--types TYPE` | `--types res` | Module type: `res`, `ptn`, `utl` |
| `--severity LEVEL` | `--severity critical,high` | Filter by severity level(s) |
| `--output FILE` | `--output docs/issues.md` | Write to file instead of stdout |

---

## When to Use

- Starting a triage session — get a view of all open issues across the catalog
- Focused review of a single domain's open issues before a release
- Identifying which modules have critical or high-severity bugs to prioritise
- Generating an issues report for a PR or release notes

---

## Procedure

### Step 1 — Parse input

Extract from the user message:

- **Domain filter** — `--domains DOMAIN[,DOMAIN]`, e.g. `networking`, or `all`
- **Type filter** — `--types TYPE[,TYPE]`, e.g. `res`
- **Severity filter** — `--severity LEVEL[,LEVEL]`, e.g. `critical,high`
- **Output** — `--output FILE` if the user wants file output

If no filters are given, run across the full catalog.

### Step 2 — Run the report

```bash
# All modules, all severities
python3 scripts/report.py --issues

# Filtered by domain
python3 scripts/report.py --issues --domains {domains}

# Filtered by domain + type
python3 scripts/report.py --issues --domains {domains} --types {types}

# Filtered by severity
python3 scripts/report.py --issues --severity {severity}

# Write to file
python3 scripts/report.py --issues --output {file}
```

### Step 3 — Assess findings

Review the output for patterns:

- How many open issues exist per severity level?
- Which domains / module types have the most open issues?
- Are there any `critical` issues that need immediate attention?
- Are there open issues with no workaround?

For each `critical` or `high` issue, check if a workaround exists in the `workaround:` field. If the field is empty and the issue is critical, flag it.

### Step 4 — Report to user

Present the rollup table from the script output, then add an LLM assessment summary:

```
AVM Open Issue Rollup
─────────────────────
{script output}

ASSESSMENT
──────────
Total: {N} open issues across {M} modules

By severity:
  critical: {N}  high: {N}  medium: {N}  low: {N}

Hotspots (most issues):
  {domain}: {N} issues
  {module}: {N} issues

Action items:
  1. {critical/high issue with no workaround — highest priority}
  2. ...
```

If no issues are found, confirm: "No open issues found in the catalog for the specified filters."

---

## Notes

- `enrichment.known_issues` is hand-maintained — it reflects what _you_ know, not upstream issues.
- To harvest upstream issues from GitHub, use `./avm.sh harvest`.
- This skill reads `data/modules/` directly — no cloned repos required.
- Issues with `status: resolved` or `status: wontfix` are excluded from the rollup.
