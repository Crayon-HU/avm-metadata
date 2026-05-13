# Repository Guidelines

## Project Structure & Module Organization

This repository is metadata for Azure Verified Modules (AVM); it does not contain Terraform module source code. Domain inventories live in `.config/{domain}.yaml` and are the source of truth. `docs/avm-modules.md` documents the catalog. Automation lives in `avm.sh` and `scripts/`.

Generated files include `.config/modules.yaml`, `.config/workspaces.yaml`, and `*.code-workspace`; regenerate them instead of hand-maintaining them. Directories named `terraform-azurerm-avm-*` are cloned upstream repositories with their own Git histories. Do not edit or commit those directories through this repo.

## Build, Test, and Development Commands

- `./avm.sh help`: show supported commands and options.
- `./avm.sh setup --domains all`: generate inventory and workspace files for all domains.
- `./avm.sh setup --domains networking,compute --types res`: generate a focused inventory.
- `./avm.sh clone --domain networking --type res`: clone selected module repos from the generated inventory.
- `./avm.sh workspaces`: regenerate `.code-workspace` files from the current generated workspace config.
- `./avm.sh update`: run `git pull --ff-only` in already-cloned module repos.
- `bash -n avm.sh scripts/*.sh`: syntax-check Bash scripts before committing script changes.

PowerShell equivalents exist for module generation and cloning: `scripts/generate_modules.ps1` and `scripts/clone_repos.ps1`.

## Coding Style & Naming Conventions

Shell scripts use Bash with `set -euo pipefail`, uppercase constants, local lowercase variables, and helper functions such as `_usage`. Keep scripts dependency-light; current Bash automation relies on Git and standard POSIX tools. Preserve LF endings for `.sh`, YAML, and JSON; `.ps1` files use CRLF per `.gitattributes`.

Domain files are named by lowercase domain slug, for example `.config/networking.yaml`. Module entries should use full GitHub repo names such as `terraform-azurerm-avm-res-network-virtualnetwork` and type values `res`, `ptn`, or `utl`.

## Testing Guidelines

There is no formal test framework. Validate changes with syntax checks for edited scripts and a non-interactive generation command, for example `./avm.sh setup --domains networking --types res`. Confirm generated files look correct, but do not commit gitignored outputs unless repository policy changes.

## Commit & Pull Request Guidelines

The current history is minimal (`Initial commit`), so use clear, imperative commit subjects such as `Add networking module metadata` or `Update workspace generation script`. Pull requests should describe the changed domains or scripts, list validation commands run, and note any generated files intentionally left uncommitted. Link related issues when available.

## Agent-Specific Instructions

Prefer editing `.config/{domain}.yaml`, `docs/avm-modules.md`, and scripts in this repo. Treat cloned `terraform-azurerm-avm-*` directories as external dependencies. Never add secrets, credentials, or local machine paths to committed metadata.
