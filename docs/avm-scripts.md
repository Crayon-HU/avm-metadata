# AVM Script Reference

This repository uses dependency-light Bash and PowerShell scripts to build a local Azure Verified Modules workspace from committed metadata. The scripts parse simple YAML by line-oriented conventions; they do not require a YAML parser.

## Command Flow

Use the top-level wrapper for the current shell:

| Task | Bash | PowerShell |
|---|---|---|
| Show help | `./avm.sh help` | `.\avm.ps1 help` |
| Generate inventory and workspaces | `./avm.sh setup --domains all` | `.\avm.ps1 setup -Domains all` |
| Filter by domain/type | `./avm.sh setup --domains networking --types res` | `.\avm.ps1 setup -Domains networking -Types res` |
| Clone modules | `./avm.sh clone --domain networking --type res` | `.\avm.ps1 clone -Domain networking -Type res` |
| Regenerate workspaces | `./avm.sh workspaces` | `.\avm.ps1 workspaces` |
| Update cloned repos | `./avm.sh update --domain containers` | `.\avm.ps1 update -Domain containers` |

The direct scripts remain available when a wrapper is not desired:

- `scripts/generate_modules.sh` / `scripts/generate_modules.ps1`
- `scripts/generate_workspaces.sh` / `scripts/generate_workspaces.ps1`
- `scripts/clone_repos.sh` / `scripts/clone_repos.ps1`
- `scripts/update_repos.sh` / `scripts/update_repos.ps1`

## Generated Files

`setup` reads `.config/{domain}.yaml`, filters the selected domains and types, and writes `.config/modules.yaml`. It then regenerates `.config/workspaces.yaml` and `avm*.code-workspace` files.

These outputs are generated and gitignored:

- `.config/modules.yaml`
- `.config/workspaces.yaml`
- `*.code-workspace`
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

Module blocks start at `- name:`. Supported types are `res`, `ptn`, and `utl`. Comments and blank source lines are ignored during generation. `generate_modules` injects `domain:` and `workspaces:` fields into `.config/modules.yaml`; domain source files should not maintain those generated fields.

Workspace assignments are stored as bracketed comma-separated values, for example `workspaces: [networking, platform]`. Existing workspace assignments are preserved when regenerating modules, and manual additions in `.config/workspaces.yaml` are preserved when regenerating workspace files.

## Portability Notes

Bash scripts target macOS/Linux and remain compatible with Bash 3.2. PowerShell scripts target Windows PowerShell 5.1 and avoid PS 7-only syntax. Both implementations avoid external dependencies beyond Git and standard shell/runtime features.

Use `bash -n avm.sh scripts/*.sh tests/*.sh` to syntax-check Bash changes. If PowerShell is installed, run the contract test in `tests/script_contract.sh`; it performs parser checks for all `.ps1` files.
