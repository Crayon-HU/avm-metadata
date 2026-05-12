# AVM Script Reference

This repository uses a layered script architecture. Python scripts handle catalog and data operations; Bash and PowerShell scripts handle git operations. All scripts are called by both the operator entry points (`avm.sh` / `avm.ps1`) and by Copilot skills.

## Command Flow

Use the top-level wrapper for the current shell:

| Task | Bash | PowerShell | Script |
|---|---|---|---|
| Show help | `./avm.sh help` | `.\avm.ps1 help` | — |
| Generate inventory | `./avm.sh setup --domains all` | `.\avm.ps1 setup -Domains all` | `scripts/generate_modules.sh/.ps1` |
| Filter by domain/type | `./avm.sh setup --domains networking --types res` | `.\avm.ps1 setup -Domains networking -Types res` | `scripts/generate_modules.sh/.ps1` |
| Clone modules | `./avm.sh clone --domain networking --type res` | `.\avm.ps1 clone -Domain networking -Type res` | `scripts/clone_repos.sh/.ps1` |
| Update cloned repos | `./avm.sh update --domain containers` | `.\avm.ps1 update -Domain containers` | `scripts/update_repos.sh/.ps1` |
| Sync AVM catalog | `./avm.sh sync` | — | `scripts/sync_catalog.py` |
| Sync (dry run) | `./avm.sh sync --dry-run` | — | `scripts/sync_catalog.py` |
| Scrape module repos | `./avm.sh scrape` | — | `scripts/scrape_modules.py` |
| Scrape one module | `./avm.sh scrape --module NAME` | — | `scripts/scrape_modules.py` |

The direct scripts remain available when the wrapper is not desired:

- `scripts/generate_modules.sh` / `scripts/generate_modules.ps1`
- `scripts/clone_repos.sh` / `scripts/clone_repos.ps1`
- `scripts/update_repos.sh` / `scripts/update_repos.ps1`
- `scripts/sync_catalog.py`
- `scripts/scrape_modules.py`

Copilot skills call the Python scripts directly (same layer as `avm.sh`). See `docs/workflows.md` for the full architecture.

## Generated Files

`setup` reads `.config/{domain}.yaml`, filters the selected domains and types, and writes `.config/modules.yaml`.

These outputs are generated and gitignored:

- `.config/modules.yaml`
- `terraform-azurerm-avm-*/` cloned module repositories

Regenerate these files instead of editing them by hand. Commit changes to `.config/{domain}.yaml`, scripts, and documentation.

## Parsing Assumptions

Domain files must use the existing simple shape:

```yaml
modules:
  - name: terraform-azurerm-avm-res-network-virtualnetwork
    type: res
    url: https://github.com/Azure/terraform-azurerm-avm-res-network-virtualnetwork.git
    branch: main
    description: Virtual Network
```

Module blocks start at `- name:`. Supported types are `res`, `ptn`, and `utl`. Comments and blank source lines are ignored during generation. `generate_modules` injects a `domain:` field into `.config/modules.yaml`; domain source files should not maintain that generated field.

## Portability Notes

Bash scripts target macOS/Linux and remain compatible with Bash 3.2. PowerShell scripts target Windows PowerShell 5.1 and avoid PS 7-only syntax. Both implementations avoid external dependencies beyond Git and standard shell/runtime features.

Use `bash -n avm.sh scripts/*.sh tests/*.sh` to syntax-check Bash changes. If PowerShell is installed, run the contract test in `tests/script_contract.sh`; it performs parser checks for all `.ps1` files.
