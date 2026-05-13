# Demo Script — avm-metadata @ Microsoft Budapest

**Duration:** 35–45 minutes  
**Audience:** Azure/Terraform practitioners, platform engineers  
**Format:** Live terminal + VSCode, projected screen  
**Prerequisites:** Repo cloned, Python 3.9+, 50+ module repos cloned (`terraform-azurerm-avm-*`), VSCode open

---

## Pre-demo Checklist

- [ ] `avm.code-workspace` open in VSCode
- [ ] Terminal open at repo root (`cd ~/Data/Projects/avm-metadata`)
- [ ] GitHub Copilot Chat sidebar visible
- [ ] Zoom in terminal: `Cmd/Ctrl + =` × 3 for readability
- [ ] Browser tab open: https://azure.github.io/Azure-Verified-Modules/

---

## 00 · Opening — The Problem (3 min)

**Say:**

> "If you're using Terraform on Azure today, you've probably heard of Azure Verified Modules — Microsoft's official library of opinionated, spec-compliant Terraform modules. There are 148 available modules right now, covering everything from VNets and AKS to Cosmos DB and Azure OpenAI.
>
> The problem is: they're not in one repo. Every module lives in its own GitHub repository under the Azure org. If you're a platform team managing infrastructure for multiple products, you're juggling 20, 50, maybe 100+ of these at once. How do you keep track of what's current? Which modules have good test coverage? Which ones are missing required AVM interface variables? Which are pinning outdated provider versions?
>
> That's the problem this repo solves."

**Show:** Browser → https://github.com/orgs/Azure/repositories?q=terraform-azurerm-avm (briefly — just to show the scale)

---

## 01 · Architecture Overview (5 min)

**Say:**

> "avm-metadata is a *metadata* repository. It contains no Terraform code of its own. What it does is: organize, sync, and analyse the upstream AVM modules — treating them as a fleet."

**Show:** `docs/diagrams/workflows_arch.md` rendered (Mermaid preview in VSCode or markdown preview)

**Talk through the diagram:**

> "Three layers:
> - **Blue — Operator**: `avm.sh` is the CLI entry point. You run it from your terminal.
> - **Green — Scripts**: Four Python scripts do all the real work — syncing the catalog, managing repos, running analysis.
> - **Red — Assistant**: Two Copilot skills — `/avm-sync` and `/avm-check` — give you the same capabilities from chat.
>
> Both paths go through the same scripts. There's no LLM-only path — everything is deterministic and testable."

---

## 02 · The Catalog (5 min)

**Say:**

> "The source of truth is `data/modules/`. One YAML file per module, organized by type."

**Show in terminal:**

```bash
ls data/modules/res/ | head -20
ls data/modules/ptn/ | head -10
ls data/modules/utl/
```

**Say:**

> "148 module files. Three subdirectories: `res` for resource modules, `ptn` for patterns, `utl` for utilities."

**Open one file:**

```bash
cat data/modules/res/avm-res-network-virtualnetwork.yaml
```

**Talk through the YAML sections:**

> "Each file has three sections:
> - `catalog:` — auto-generated from upstream AVM CSVs. Owner, status, registry URL, provider namespace.
> - `analysis_*:` — populated by our analysis scripts. Seven dimensions of quality data.
> - `enrichment:` — hand-maintained. Your notes, known issues, version pins. *Never* overwritten by any tool.
>
> The catalog section was last synced..." *(point to `last_synced` field)*

---

## 03 · Live: Sync the Catalog (4 min)

**Say:**

> "The catalog is kept current by pulling from the official AVM index CSVs that the AVM team publishes. Let me show a dry run."

```bash
./avm.sh sync --dry-run
```

> "This shows what would change — new modules added, status changes, owners updated — without touching any files."

```bash
./avm.sh sync
```

> "And this actually writes the updates. If a new module was published upstream since last run, it appears here. If a module was deprecated, its status updates. The enrichment sections are never touched."

**Show the manifest:**

```bash
cat data/modules/catalog-manifest.yaml
```

> "148 available modules across 17 domains."

---

## 04 · Live: Setup & Clone (5 min)

**Say:**

> "Once we have the catalog, we generate a working inventory and clone the repos we want to work with."

```bash
./avm.sh setup --domains networking --types res
```

> "This reads the catalog, filters to networking resource modules, and writes `.config/modules.yaml` — a gitignored list of repos to clone."

```bash
cat .config/modules.yaml | head -30
```

```bash
./avm.sh clone --domains networking --types res
```

> "Each repo is a separate git clone. Changes in the upstream module don't affect this metadata repo — they're independent git histories. We can also update them in parallel:"

```bash
./avm.sh update --parallel 10
```

**Show the workspace:**

```bash
code avm.code-workspace
```

> "The workspace opens all cloned repos as separate roots in VSCode. You can navigate any module's source, run `terraform validate`, make cross-module edits — all from one editor."

---

## 05 · Live: Module Analysis (8 min)

**Say:**

> "Now for the interesting part — quality analysis. The `check` command runs up to seven analysis dimensions against a module."

**Show the dimension table** (open `docs/workflows.md`, scroll to check section, or read from notes):

| Dimension | What it checks |
|---|---|
| `metadata` | TF version, provider constraints, resource types managed |
| `compliance` | AVM required interface variables present |
| `security` | Hardcoded values, validation blocks, sensitive outputs |
| `tests` | examples/ dir, test files (.go / .tftest.hcl) |
| `docs` | README exists, length, required sections |
| `deps` | Provider version constraint style (~> vs >=) |
| `provider-currency` | Module's pinned provider vs latest release; breaking-change detection |

**Run a single module check:**

```bash
./avm.sh check --modules avm-res-network-virtualnetwork
```

**Show the YAML result:**

```bash
grep -A 30 "BEGIN ANALYSIS:avm-interface-compliance" \
  data/modules/res/avm-res-network-virtualnetwork.yaml
```

> "See the `partial` status? It's missing `private_endpoints` and `managed_identities`. That's a compliance gap — those are required AVM interface variables for all `res` modules."

**Run across a domain:**

```bash
./avm.sh check --domains networking --types res --dimension avm-interface-compliance
```

> "This runs compliance checks across all 26 networking res modules. Results get written back into each module's YAML."

**Show summary pattern:**

```bash
grep -l "status: partial\|status: fail" data/modules/res/*.yaml | wc -l
```

> "That gives us instant visibility across the whole domain."

---

## 06 · Copilot Skills — /avm-check (8 min)

**Say:**

> "All of that was the operator path — great for automation, CI, or scripting. But when you're in the middle of a code review or trying to understand a specific module before using it, you want a conversational interface."

**Switch to Copilot Chat in VSCode**

**Type:**

```
/avm-check --modules avm-res-network-virtualnetwork
```

**Say:**

> "The `/avm-check` skill is a Copilot skill — it calls the same analysis scripts under the hood, reads the YAML output, and gives you a structured LLM assessment. It explains *why* something is partial or failing, not just what the status code is."

*(Wait for response — point to the formatted report)*

> "Single-module mode gives you a full per-dimension breakdown with qualitative assessment and remediation suggestions. If I run it across a domain, I get a summary table instead."

**Type:**

```
/avm-check --domains containers --dimension tests
```

*(Wait for response)*

> "It identified that test coverage is the weakest dimension across the containers domain. Every single module shows as partial or fail. That's actionable — now I know where to focus contribution effort."

**Show the skill file** (optional, if time allows):

```bash
cat .github/skills/avm-check/SKILL.md | head -50
```

> "Skills are just markdown files — a structured prompt that Copilot follows as a procedure. Deterministic work goes to the scripts; exception handling and reporting stays in the LLM. Easy to audit, easy to extend."

---

## 07 · Copilot Skills — /avm-sync (3 min)

**Type in Copilot Chat:**

```
/avm-sync
```

> "The `/avm-sync` skill wraps the catalog sync. It handles edge cases the script can't — like asking whether to include Proposed-status modules, confirming scope before writing changes, and summarising what was added or removed."

*(Show form or response)*

---

## 08 · Extensibility (3 min)

**Say:**

> "The architecture is deliberately additive. Adding a new analysis dimension takes three steps:
> 1. Add a new `# BEGIN ANALYSIS:{dim}` block pattern to `analyze_module.py`
> 2. Add the dimension shorthand to the `/avm-check` skill's dimension table
> 3. Add a row to `docs/workflows.md`
>
> No changes to `avm.sh` needed. The operator and assistant paths both pick it up automatically."

**Point to `docs/ideas.md`:**

```bash
cat docs/ideas.md | head -30
```

> "We already have ideas for a provider currency dimension — detecting when a module's pinned provider is behind and whether any of the intervening releases contain breaking changes for the specific resources that module manages. All the data is there in `analysis_terraform_metadata.resources_managed`."

---

## 09 · Wrap-up (2 min)

**Say:**

> "To summarise:
> - **148 AVM modules**, organized into a single metadata workspace
> - **Automatic catalog sync** from upstream AVM CSVs
> - **Seven-dimension quality analysis** written back to per-module YAML files
> - **Five Copilot skills** — `/avm-sync`, `/avm-check`, `/avm-issues`, `/avm-index`, `/avm-harvest` — that wrap everything with conversational interface and LLM assessment
> - **Fully extensible** — new dimensions, new skills, same architecture
>
> The repo is at [github.com/Crayon-HU/avm-metadata](https://github.com/Crayon-HU/avm-metadata). Questions?"

---

## Timing Guide

| Section | Duration | Cumulative |
|---|---|---|
| 00 · Opening — The Problem | 3 min | 3 min |
| 01 · Architecture Overview | 5 min | 8 min |
| 02 · The Catalog | 5 min | 13 min |
| 03 · Live: Sync | 4 min | 17 min |
| 04 · Live: Setup & Clone | 5 min | 22 min |
| 05 · Live: Module Analysis | 8 min | 30 min |
| 06 · Copilot: /avm-check | 8 min | 38 min |
| 07 · Copilot: /avm-sync | 3 min | 41 min |
| 08 · Extensibility | 3 min | 44 min |
| 09 · Wrap-up | 2 min | 46 min |

> **30-minute cut:** Skip sections 04 (Setup & Clone) and 07 (/avm-sync). Go directly from catalog sync (03) to analysis (05). Cuts ~8 minutes.  
> **45-minute version:** Include everything above; leave 3–5 min buffer for audience questions mid-demo.

---

## Fallback Commands (if live demo breaks)

```bash
# Show catalog without syncing
cat data/modules/catalog-manifest.yaml

# Show analysis already written (no script run needed)
grep -A 20 "BEGIN ANALYSIS:avm-interface-compliance" \
  data/modules/res/avm-res-network-virtualnetwork.yaml

# Show analysis summary across all modules
grep "status:" data/modules/res/*.yaml | grep -v "catalog\|Available\|Proposed" | \
  sort | uniq -c | sort -rn

# List cloned repos
find . -maxdepth 1 -type d -name "terraform-azurerm-avm-*" | wc -l
```

---

## Key Numbers to Remember

| Fact | Value |
|---|---|
| Available AVM modules | 148 |
| Cloned in this workspace | 54 |
| Domains | 17 |
| Analysis dimensions | 7 |
| Copilot skills | 5 (`/avm-sync`, `/avm-check`, `/avm-issues`, `/avm-index`, `/avm-harvest`) |
| Python scripts | 11 |
