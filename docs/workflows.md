# Workflows

This document describes how **operator** workflows (`avm.sh` / `avm.ps1`) and **assistant** workflows (GitHub Copilot skills) share the same underlying `scripts/` automation layer, and how to extend the repo with new commands.

---

## 1. Architecture Overview

The repo uses a layered architecture where `scripts/` is the single shared automation layer. Both operator and assistant entry points call into it directly — there is no separate "LLM-only" path.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Entry Points                                │
│                                                                 │
│   avm.sh / avm.ps1          .github/skills/{name}/SKILL.md     │
│   (Operator — CLI/terminal)  (Assistant — Copilot chat)         │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
                 ▼                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    scripts/   (shared layer)                    │
│                                                                 │
│   sync_catalog.py          Python  ← catalog/data ops          │
│   analyze_module.py        Python  ← catalog/data ops          │
│   generate_modules.sh/.ps1 Bash/PS ← git-adjacent ops          │
│   clone_repos.sh/.ps1      Bash/PS ← git ops                   │
│   update_repos.sh/.ps1     Bash/PS ← git ops                   │
└─────────────────────────────────────────────────────────────────┘
```

**Key principle:** `avm.sh`/`avm.ps1` and skills are symmetric — both are thin wrappers over the same `scripts/` layer. If you add a new command, you add it to all three entry points.

---

## 2. Copilot Ecosystem Hierarchy

The GitHub Copilot CLI supports several types of persistent artifacts. Understanding the differences helps you choose the right one:

| Artifact | Location | Scope | How to invoke |
|---|---|---|---|
| **Instructions** | `.github/copilot-instructions.md` | Always active — loaded into every conversation | Automatic |
| **Skills** | `.github/skills/{name}/SKILL.md` | Task-specific — invoked on demand | `/skill-name` in chat |
| **Agents** | `.github/agents/{name}.md` or hosted | Autonomous multi-step workers — suited for long-running tasks (e.g., Copilot coding agent on a PR) | Explicit launch |
| **Prompts** | Inline chat | Ad-hoc — not persisted; for one-off questions | Natural language |

### When to use each

- **Instructions** — repo conventions, do-not-do rules, always-on context. Keep this focused and accurate; it loads every time.
- **Skills** — any task you run repeatedly from chat (e.g., "sync the AVM catalog", "scrape a module"). A skill calls the relevant script and then handles any LLM-level exception the script can't (ambiguous domain, user prompt needed).
- **Agents** — tasks spanning many files or requiring autonomous judgment (e.g., triage an entire module's enrichment fields). Use when a skill would need too many follow-up turns.
- **Prompts** — exploration, one-off questions. Do not create a skill for something you will only do once.

### How skills in this repo work

A skill in this repo follows a simple two-part structure:

1. **Call the script** — invoke the relevant Python or Bash script via the `bash` tool. The script does the deterministic work.
2. **Handle exceptions** — interpret output, ask the user about anything ambiguous, report results.

This keeps scripts testable in isolation and skills readable.

---

## 3. Operator Workflows

Operators run commands from a terminal using the top-level wrapper for their shell.

### Command reference

| Command | Bash | PowerShell | Script |
|---|---|---|---|
| Generate modules.yaml | `./avm.sh setup --domains all` | `.\avm.ps1 setup -Domains all` | `scripts/generate_modules.sh/.ps1` |
| Filter by domain/type | `./avm.sh setup --domains networking --types res` | `.\avm.ps1 setup -Domains networking -Types res` | `scripts/generate_modules.sh/.ps1` |
| Clone repos | `./avm.sh clone` | `.\avm.ps1 clone` | `scripts/clone_repos.sh/.ps1` |
| Clone filtered | `./avm.sh clone --domain networking --type res` | `.\avm.ps1 clone -Domain networking -Type res` | `scripts/clone_repos.sh/.ps1` |
| Update cloned repos | `./avm.sh update` | `.\avm.ps1 update` | `scripts/update_repos.sh/.ps1` |
| Sync AVM catalog | `./avm.sh sync` | `.\avm.ps1 sync` | `scripts/sync_catalog.py` |
| Sync (dry run) | `./avm.sh sync --dry-run` | `.\avm.ps1 sync --dry-run` | `scripts/sync_catalog.py` |
| Scrape TF metadata (alias) | `./avm.sh scrape` | `.\avm.ps1 scrape` | `scripts/analyze_module.py --dimension terraform-metadata` |
| Scrape one module | `./avm.sh scrape --module NAME` | `.\avm.ps1 scrape --module NAME` | `scripts/analyze_module.py` |
| Run all analysis | `./avm.sh check --module NAME` | `.\avm.ps1 check --module NAME` | `scripts/analyze_module.py` |
| Run one dimension | `./avm.sh check --dimension DIM` | `.\avm.ps1 check --dimension DIM` | `scripts/analyze_module.py` |
| Dry-run analysis | `./avm.sh check --dry-run` | `.\avm.ps1 check --dry-run` | `scripts/analyze_module.py` |

### Typical operator session

```bash
# First time setup — pick your domains
./avm.sh setup --domains networking,compute --types res,ptn

# Clone selected modules (shallow by default)
./avm.sh clone

# Refresh the catalog from upstream AVM CSVs
./avm.sh sync

# Scrape Terraform metadata from each module repo (alias for check --dimension terraform-metadata)
./avm.sh scrape

# Run full analysis on a specific module (all 6 dimensions)
./avm.sh check --module avm-res-network-virtualnetwork

# Run a single dimension across all modules
./avm.sh check --dimension avm-interface-compliance

# After a few weeks — pull latest changes in cloned repos
./avm.sh update
```

---

## 4. Assistant Workflows

Assistant workflows run inside GitHub Copilot CLI chat sessions. A skill is invoked with `/skill-name` and the Copilot agent executes the procedure step by step using its available tools (including `bash`).

### Anatomy of a skill

```markdown
---
name: avm-sync
description: 'Trigger phrases that tell Copilot when to offer this skill'
argument-hint: 'Optional argument the user can pass'
---

# Skill Title

Brief description of what the skill does.

## Procedure

### Step 1 — Run the script
(Call the relevant script and capture its output)

### Step 2 — Handle exceptions
(Anything the script cannot decide automatically: ambiguous domains,
 user confirmation, etc.)

### Step 3 — Report
(Summarise what changed)
```

### Current skills

| Skill | Invocation | Script called | What it does |
|---|---|---|---|
| `avm-sync` | `/avm-sync [domain]` | `scripts/sync_catalog.py` | Sync AVM module catalog from upstream CSVs |
| `avm-check-metadata` | `/avm-check-metadata [module]` | `scripts/analyze_module.py --dimension terraform-metadata` | Scrape TF metadata from module repo |
| `avm-check-compliance` | `/avm-check-compliance [module]` | `scripts/analyze_module.py --dimension avm-interface-compliance` | Check AVM interface variable requirements |
| `avm-check-security` | `/avm-check-security [module]` | `scripts/analyze_module.py --dimension security-hardening` | Scan for security anti-patterns |
| `avm-check-tests` | `/avm-check-tests [module]` | `scripts/analyze_module.py --dimension test-coverage` | Check examples/ and tests/ presence |
| `avm-check-docs` | `/avm-check-docs [module]` | `scripts/analyze_module.py --dimension doc-quality` | Check README quality |
| `avm-check-deps` | `/avm-check-deps [module]` | `scripts/analyze_module.py --dimension dependency-health` | Check version constraint style |
| `avm-audit` | `/avm-audit [module]` | `scripts/analyze_module.py` (all dims) | Full quality audit across all dimensions |

---

## 5. Development Guidelines

### Adding a new command

Follow this checklist whenever you add a new `avm.sh` command (e.g., `validate`):

- [ ] **Write the script** in `scripts/` following the language policy below
- [ ] **Add `cmd_{name}()`** function to `avm.sh` that delegates to the script
- [ ] **Add dispatch case** `{name}) cmd_{name} "$@" ;;` in `avm.sh`
- [ ] **Add usage text** to the `_usage()` function in `avm.sh`
- [ ] **Add matching block** to `avm.ps1` (usage + dispatch)
- [ ] **Create a skill** at `.github/skills/avm-{name}/SKILL.md`
- [ ] **Update this file** (`docs/workflows.md`) — add a row to the command table and skills table
- [ ] **Update `.github/copilot-instructions.md`** entry point section
- [ ] **Run syntax check**: `bash -n avm.sh scripts/*.sh`

### Language policy

| Script category | Language | Rationale |
|---|---|---|
| Catalog / data ops | **Python 3** | Native stdlib for HTTP, JSON, CSV, YAML-adjacent work; no external deps unless unavoidable |
| Git operations | **Bash + PowerShell pair** | Thin subprocess wrappers; dual implementation keeps cross-platform parity without a git library |

New data-manipulation scripts → Python only (no `.sh` equivalent needed).  
New git-wrapping scripts → Bash + PowerShell pair (both must be kept in sync).

### Script authoring rules

**Python:**
- Use only stdlib unless there is a strong reason (document it in the script header)
- Atomic writes: write to a temp file, then `os.replace()` — never partial writes
- Encode UTF-8 explicitly; AVM CSVs carry a BOM — use `open(..., encoding="utf-8-sig")`
- Accept `--dry-run` for any script that modifies files

**Bash:**
- Always start with `set -euo pipefail`
- Run `bash -n scripts/your-script.sh` before committing
- Target Bash 3.2 (macOS default) — avoid associative arrays and `mapfile`

**PowerShell:**
- Declare `#Requires -Version 5.1` at the top
- Set `$ErrorActionPreference = 'Stop'`
- Avoid PowerShell 7-only syntax — the scripts must run on Windows PowerShell 5.1

### Skill authoring rules

- **`description`** frontmatter — write trigger phrases, not a formal description. These are what the Copilot model matches against user messages.
- **Step 1** of every skill procedure: call the relevant script. Do not replicate script logic in the skill.
- **Remaining steps**: interpret output, handle ambiguity, report to the user.
- Keep skills focused — one skill per command. Resist the urge to combine sync + scrape into one skill.

### Validation

```bash
# Syntax-check all Bash scripts before committing
bash -n avm.sh scripts/*.sh

# Dry-run the Python catalog scripts
python3 scripts/sync_catalog.py --dry-run
python3 scripts/analyze_module.py --dry-run --module avm-res-network-virtualnetwork
```

---

## 6. Analysis Workflows

The `check` command and the `avm-audit` skill give both operators and assistants access to
multi-dimensional quality analysis. All results are stored in isolated, tool-owned YAML blocks
that can be read by both humans and Copilot agents.

### YAML block format

Each dimension writes one marker-delimited block. All blocks live between `# END CATALOG` and
the hand-maintained `enrichment:` section:

```yaml
# BEGIN CATALOG
catalog: ...
# END CATALOG

# BEGIN ANALYSIS:terraform-metadata       ← analyze_module.py (./avm.sh scrape alias)
analysis_terraform_metadata:
  checked_at: "2026-05-12T20:00:00Z"
  status: pass
  errors: []
  terraform_constraints:
    required_version: ">= 1.9, < 2.0"
    required_providers:
      azurerm: { source: "hashicorp/azurerm", version_constraint: "~> 4.0" }
  resources_managed:
    azurerm: ["azurerm_virtual_network", "azurerm_subnet"]
# END ANALYSIS:terraform-metadata

# BEGIN ANALYSIS:avm-interface-compliance  ← analyze_module.py / avm-check-compliance skill
analysis_avm_interface_compliance:
  checked_at: "2026-05-12T20:00:00Z"
  status: partial
  checks:
    lock:              { status: pass,    evidence: "variables.tf:47" }
    private_endpoints: { status: missing, finding: "No variable found" }
    ...
  llm_assessment: "6/7 AVM interfaces present. private_endpoints missing."  ← added by skill
# END ANALYSIS:avm-interface-compliance

enrichment:   ← hand-maintained, never overwritten
  ...
```

**Block ownership rules:**
- Each tool only rewrites its own `# BEGIN ANALYSIS:{dim}` / `# END ANALYSIS:{dim}` block.
- All other blocks are read, preserved, and written back unchanged.
- The `enrichment:` section has no markers and is never touched by any tool.

### The 6 built-in dimensions

| Dimension | Key | API calls | Depends on |
|---|---|---|---|
| `terraform-metadata` | `analysis_terraform_metadata` | GitHub Contents (list + fetch .tf files) | — |
| `avm-interface-compliance` | `analysis_avm_interface_compliance` | Same .tf files (cached) | — |
| `security-hardening` | `analysis_security_hardening` | Same .tf files (cached) | — |
| `test-coverage` | `analysis_test_coverage` | GitHub Contents (examples/, tests/) | — |
| `doc-quality` | `analysis_doc_quality` | raw.githubusercontent.com (README.md) | — |
| `dependency-health` | `analysis_dependency_health` | **None** (reads in-memory metadata) | `terraform-metadata` |

All dimensions share a per-module fetch cache — fetching `.tf` files once serves all three
dimensions that need them.

### Running analysis

**All dimensions on one module:**
```bash
./avm.sh check --module avm-res-network-virtualnetwork
GITHUB_TOKEN=ghp_... ./avm.sh check --module avm-res-network-virtualnetwork
```

**One dimension across all modules:**
```bash
./avm.sh check --dimension test-coverage
./avm.sh check --dimension test-coverage --max-age 30
```

**Scrape alias (terraform-metadata only):**
```bash
./avm.sh scrape --module avm-res-network-virtualnetwork
./avm.sh scrape --force
```

**Skip recently checked (default 7 days):**
```bash
./avm.sh check --dimension doc-quality --max-age 30   # skip if checked within 30 days
./avm.sh check --force                                # ignore age; always re-run
```

### Mixed deterministic + LLM output

The Python script produces **deterministic, structured results** — each check is
`pass | fail | missing | partial | unchecked` with an `evidence` or `finding` string.

Skills then add **qualitative LLM assessment** for borderline (`partial`) findings by writing
an `llm_assessment:` field into the block. This keeps the deterministic checks auditable and
the LLM's judgment clearly separated.

The `avm-audit` skill runs all 6 dimensions in one pass, then populates `llm_assessment` for
every `partial` or `fail` result and reports a consolidated summary table.

### Extensibility — adding a new dimension

To add a dimension `foo-bar`:

1. **Script** (`scripts/analyze_module.py`):
   - Implement `check_foo_bar(ctx: ModuleContext) -> dict`
   - Add `"foo-bar": ("analysis_foo_bar", check_foo_bar)` to the `DIMENSIONS` registry

2. **Schema** (all 3 `schemas/avm-module-{res,ptn,utl}.schema.json`):
   - Add `"analysis_foo_bar": { "$ref": "#/$defs/analysis_dimension" }` as an optional property

3. **Skill** (`.github/skills/avm-check-foo-bar/SKILL.md`):
   - Follow the pattern of existing dimension skills (Step 1: run script, Step 2: LLM on partials)

4. **Docs** (`docs/workflows.md`):
   - Add a row to the dimensions table above
   - Add a row to the skills table in Section 4
   - Add a row to the operator command table in Section 3
