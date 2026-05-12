#!/usr/bin/env bash
# avm.sh — Unified entry point for the AVM metadata workspace
#
# Commands:
#   setup       Select domains & types → generate .config/modules.yaml
#   clone       Clone module repos listed in .config/modules.yaml
#   update      Pull latest changes in all already-cloned module repos
#   sync        Fetch upstream AVM CSV indexes → update data/modules/*.yaml
#   scrape      Alias for: check --dimension terraform-metadata
#   check       Run analysis dimensions on module(s) → populate analysis blocks
#
# Usage:
#   ./avm.sh setup [--domains networking,compute] [--types res,ptn]
#   ./avm.sh setup --domains all
#   ./avm.sh clone [--domain networking] [--type res] [--full]
#   ./avm.sh update [--domain networking] [--type res]
#   ./avm.sh sync [--dry-run]
#   ./avm.sh scrape [--dry-run] [--force] [--module NAME]
#   ./avm.sh check [--module NAME] [--dimension DIM] [--dry-run] [--force] [--max-age DAYS]
#   ./avm.sh help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
_header() {
  echo ""
  echo "AVM Metadata Workspace"
  echo "════════════════════════════════════════════════════════════"
}

_usage() {
  _header
  cat <<'EOF'

  Usage: ./avm.sh <command> [options]

  Commands:
    setup        Generate .config/modules.yaml (select domains & types).

      --domains <list|all>   Comma-separated domain names, or 'all'
      --types   <list|all>   Comma-separated types (res,ptn,utl), or 'all'

    clone        Clone module repos from .config/modules.yaml.
                 Run 'setup' first if modules.yaml does not exist.

      --domain <name>        Filter by a single domain
      --type   <type>        Filter by type (res|ptn|utl)
      --full                 Full git history (default: shallow --depth 1)

    update       Pull the latest changes for all already-cloned module repos.

      --domain <name>        Limit to one domain
      --type   <type>        Limit to one type (res|ptn|utl)

    sync         Fetch the three official AVM module index CSVs and
                 generate/update data/modules/*.yaml (one file per module).
                 Catalog fields are refreshed; enrichment fields are preserved.

      --dry-run              Show planned changes without writing files

    scrape       Convenience alias for: check --dimension terraform-metadata
                 Fetches each module's GitHub repo and populates the
                 analysis_terraform_metadata block in data/modules/{type}/*.yaml
                 with terraform_constraints and resources_managed / modules_called.
                 Set GITHUB_TOKEN for higher rate limits (5000/hr vs 60/hr).

      --dry-run              Show planned changes without writing files
      --force                Re-analyze even if recently checked
      --module NAME          Analyze a single module by name
      --max-age DAYS         Skip modules checked within N days (default: 7)

    check        Run one or more analysis dimensions on module(s).
                 Results are written to # BEGIN ANALYSIS:{dim} blocks in
                 data/modules/{type}/*.yaml.
                 Six built-in dimensions:
                   terraform-metadata       TF version + provider constraints + resources
                   avm-interface-compliance Required AVM interface variables
                   security-hardening       Hardcoded values, validation, sensitive outputs
                   test-coverage            examples/, tests/, *.go / *.tftest.hcl presence
                   doc-quality              README length and required section headers
                   dependency-health        Version constraint style (needs terraform-metadata)
                 Set GITHUB_TOKEN for higher rate limits (5000/hr vs 60/hr).

      --module    NAME       Analyze a single module by name
      --dimension DIM        Run only this dimension (repeat for multiple; default: all)
      --dry-run              Show planned changes without writing files
      --force                Ignore --max-age; always re-analyze
      --max-age   DAYS       Skip dimensions checked within N days (default: 7)

    help         Show this message.

  Examples:
    ./avm.sh setup --domains all
    ./avm.sh setup --domains networking,compute --types res
    ./avm.sh clone
    ./avm.sh clone --domain networking --type res
    ./avm.sh update
    ./avm.sh update --domain containers
    ./avm.sh sync
    ./avm.sh sync --dry-run
    ./avm.sh scrape
    ./avm.sh scrape --module avm-res-network-virtualnetwork
    ./avm.sh scrape --force
    GITHUB_TOKEN=ghp_... ./avm.sh scrape
    ./avm.sh check --module avm-res-network-virtualnetwork
    ./avm.sh check --module avm-res-network-virtualnetwork --dimension avm-interface-compliance
    ./avm.sh check --dimension test-coverage
    ./avm.sh check --dry-run
    GITHUB_TOKEN=ghp_... ./avm.sh check

EOF
}

# ---------------------------------------------------------------------------
# Command: setup
# ---------------------------------------------------------------------------
cmd_setup() {
  python3 "${SCRIPTS_DIR}/generate_config.py" "$@"
}

# ---------------------------------------------------------------------------
# Command: clone
# ---------------------------------------------------------------------------
cmd_clone() {
  bash "${SCRIPTS_DIR}/clone_repos.sh" "$@"
}

# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------
cmd_update() {
  bash "${SCRIPTS_DIR}/update_repos.sh" "$@"
}

# ---------------------------------------------------------------------------
# Command: sync
# ---------------------------------------------------------------------------
cmd_sync() {
  python3 "${SCRIPTS_DIR}/sync_catalog.py" "$@"
}

# ---------------------------------------------------------------------------
# Command: scrape (backward-compat alias for check --dimension terraform-metadata)
# ---------------------------------------------------------------------------
cmd_scrape() {
  python3 "${SCRIPTS_DIR}/analyze_module.py" --dimension terraform-metadata "$@"
}

# ---------------------------------------------------------------------------
# Command: check
# ---------------------------------------------------------------------------
cmd_check() {
  python3 "${SCRIPTS_DIR}/analyze_module.py" "$@"
}

# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
COMMAND="${1:-}"
[[ $# -gt 0 ]] && shift || true

case "${COMMAND}" in
  setup)      cmd_setup      "$@" ;;
  clone)      cmd_clone      "$@" ;;
  update)     cmd_update     "$@" ;;
  sync)       cmd_sync       "$@" ;;
  scrape)     cmd_scrape     "$@" ;;
  check)      cmd_check      "$@" ;;
  help|--help|-h) _usage ;;
  "")
    _usage
    exit 1
    ;;
  *)
    echo "ERROR: Unknown command '${COMMAND}'. Run './avm.sh help' for usage."
    exit 1
    ;;
esac
