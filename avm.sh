#!/usr/bin/env bash
# avm.sh — Unified entry point for the AVM metadata workspace
#
# Commands:
#   setup       Select domains & types → generate .config/modules.yaml
#   clone       Clone module repos listed in .config/modules.yaml
#   update      Pull latest changes in all already-cloned module repos
#   sync        Fetch upstream AVM CSV indexes → update data/modules/*.yaml
#   scrape      Scrape module repos → populate scraped block in data/modules/*.yaml
#
# Usage:
#   ./avm.sh setup [--domains networking,compute] [--types res,ptn]
#   ./avm.sh setup --domains all
#   ./avm.sh clone [--domain networking] [--type res] [--full]
#   ./avm.sh update [--domain networking] [--type res]
#   ./avm.sh sync [--dry-run]
#   ./avm.sh scrape [--dry-run] [--force] [--module NAME]
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

    scrape       Scrape each module's GitHub repo and populate the scraped
                 block in data/modules/{type}/*.yaml with terraform_constraints
                 and resources_managed / modules_called.
                 Set GITHUB_TOKEN for higher rate limits (5000/hr vs 60/hr).

      --dry-run              Show planned changes without writing files
      --force                Re-scrape even if recently scraped
      --module NAME          Scrape a single module by name
      --max-age DAYS         Skip modules scraped within N days (default: 7)

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

EOF
}

# ---------------------------------------------------------------------------
# Command: setup
# ---------------------------------------------------------------------------
cmd_setup() {
  bash "${SCRIPTS_DIR}/generate_modules.sh" "$@"
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
# Command: scrape
# ---------------------------------------------------------------------------
cmd_scrape() {
  python3 "${SCRIPTS_DIR}/scrape_modules.py" "$@"
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
