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
│   scrape_modules.py        Python  ← catalog/data ops          │
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
| Sync AVM catalog | `./avm.sh sync` | — | `scripts/sync_catalog.py` |
| Sync (dry run) | `./avm.sh sync --dry-run` | — | `scripts/sync_catalog.py` |
| Scrape module repos | `./avm.sh scrape` | — | `scripts/scrape_modules.py` |
| Scrape one module | `./avm.sh scrape --module avm-res-network-virtualnetwork` | — | `scripts/scrape_modules.py` |

### Typical operator session

```bash
# First time setup — pick your domains
./avm.sh setup --domains networking,compute --types res,ptn

# Clone selected modules (shallow by default)
./avm.sh clone

# Refresh the catalog from upstream AVM CSVs
./avm.sh sync

# Scrape Terraform metadata from each module repo
./avm.sh scrape

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

| Skill | Invocation | Script called |
|---|---|---|
| `avm-sync` | `/avm-sync [domain]` | `scripts/sync_catalog.py` |

### Planned skills (follow the dev guidelines to add)

| Skill | Script |
|---|---|
| `avm-scrape` | `scripts/scrape_modules.py` |
| `avm-clone` | `scripts/clone_repos.sh` |

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
python3 scripts/scrape_modules.py --dry-run --module avm-res-network-virtualnetwork
```
