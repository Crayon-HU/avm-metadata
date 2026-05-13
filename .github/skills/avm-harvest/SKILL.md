---
name: avm-harvest
description: 'Harvest open GitHub issues from AVM module repos into module_issues blocks. Use when: harvest module issues, fetch upstream issues, module_issues, populate module issues, github issues for module, what issues does a module have, harvest on demand, refresh module issues.'
argument-hint: '[--modules NAME] [--domains DOMAIN] [--types res|ptn|utl] [--force] [--dry-run]'
---

# AVM Harvest Skill

Fetches open GitHub issues from each AVM module's upstream repo (`Azure/terraform-azurerm-avm-*`)
and writes a `module_issues:` block into the module YAML. This is the **automated** counterpart to
`enrichment.known_issues` (which is hand-curated).

> **Data source:** `catalog.repo_url` in each module YAML → GitHub Issues API
> **Output:** `module_issues:` block in `data/modules/{type}/{name}.yaml`
> **Rate limit:** Set `GITHUB_TOKEN` for 5 000 req/hr (60 req/hr unauthenticated)

**Default label filter:** `bug`, `enhancement`, `breaking-change`, `help wanted`, `good first issue`

| Flag | Example | Description |
|---|---|---|
| `--modules NAME` | `--modules avm-res-network-virtualnetwork` | Single module (short name) |
| `--domains DOMAIN` | `--domains networking,compute` | One or more domain slugs |
| `--types TYPE` | `--types res` | Module type: `res`, `ptn`, `utl` |
| `--labels LABEL[,…]` | `--labels bug,breaking-change` | Override label filter |
| `--max-issues N` | `--max-issues 100` | Max issues to store per module (default: 50) |
| `--since Nd` | `--since 7d` | Skip if harvested within N days (default: 1) |
| `--force` | | Re-harvest even if fresh |
| `--dry-run` | | Preview without writing |

---

## When to Use

- Before starting work on a module — check what issues exist upstream
- Periodic refresh to keep `module_issues` data current
- Before a compliance review to see the open bug/enhancement picture
- When `/avm-issues` shows 0 but you suspect there are upstream bugs

---

## Procedure

### Step 1 — Parse input

Extract from the user message:

- **Scope** — `--modules NAME`, `--domains DOMAIN`, `--types TYPE`, or no filter (all modules)
- **Flags** — `--force`, `--dry-run`, `--since Nd`, `--labels LIST`

If `--modules` is given with a single name, run in **single-module mode** (detailed summary after harvest).
Otherwise, run in **bulk mode** (count table only).

### Step 2 — Validate scope

For `--modules`, verify the module YAML exists:

```bash
find data/modules -name "{name}.yaml" | head -1
```

### Step 3 — Run the harvest

```bash
# Single module
python3 scripts/harvest_module_issues.py --modules {name}

# With force refresh
python3 scripts/harvest_module_issues.py --modules {name} --force

# Domain/type filter
python3 scripts/harvest_module_issues.py --domains {domains} --types {types}

# Dry run (always safe to show)
python3 scripts/harvest_module_issues.py --modules {name} --dry-run
```

### Step 4 — Read results (single-module mode)

After harvest completes, read the `module_issues:` block from the module YAML:

```bash
grep -A 50 "^module_issues:" data/modules/{type}/{name}.yaml
```

### Step 5 — LLM assessment (single-module mode only)

For each issue in `module_issues.issues`:

1. **`bug` or `breaking-change`** — flag as high-priority; check if a workaround exists in `enrichment.known_issues`
2. **`enhancement`** — note potential gaps in the module's feature coverage
3. **`help wanted` or `good first issue`** — note contribution opportunities

### Step 6 — Report

**Single-module:**

```
Module: {name} ({type})
Harvested: {last_harvested}

MODULE ISSUES — {open_count} open
─────────────────────────────────────────────
#{number}  [{labels}]  {title}
  {url}
  Created: {created_at}  Comments: {comments}
...

ASSESSMENT
──────────
{N} open issues: {bug_count} bug(s), {enhancement_count} enhancement(s), {breaking_count} breaking-change(s).

Priority items:
  1. #{number} — {title} [reason: bug/breaking-change + high comment count]
  2. ...

Workaround coverage: {N of M} issues have matching enrichment.known_issues entries.
```

**Bulk mode:**

```
AVM HARVEST — {domains} / {types}
─────────────────────────────────────────────
MODULE                                    ISSUES   BUGS   LAST HARVESTED
──────────────────────────────────────── ──────── ────── ────────────────
avm-res-network-virtualnetwork            7        2      2026-05-13
avm-res-network-networksecuritygroup      3        1      2026-05-13
...

Summary: {total_issues} issues across {N} modules ({bug_total} bugs, {breaking_total} breaking-changes)
```

---

## Notes

- `module_issues` is **automated pull** from GitHub; `enrichment.known_issues` is **hand-curated** — they serve different purposes and are never merged.
- The harvest script writes `module_issues:` before the `enrichment:` section on first run.
- Without `GITHUB_TOKEN`, unauthenticated requests are limited to 60/hr (≈60 modules before rate limit).
- Only issues matching the label filter are stored; default covers bugs and enhancements.
- The `/avm-issues` skill reads `enrichment.known_issues`; use this skill to surface `module_issues` data.
