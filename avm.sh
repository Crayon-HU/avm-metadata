#!/usr/bin/env bash
# avm.sh — Unified entry point for the AVM metadata workspace
#
# Commands:
#   setup       Select domains & types → generate .config/modules.yaml
#   clone       Clone module repos listed in .config/modules.yaml
#   update      Pull latest changes in all already-cloned module repos
#   fetch       Fetch all remotes without merging (parallel)
#   status      Show repos with uncommitted changes or that are behind remote
#   branch      Multi-repo branch management (create/checkout/delete)
#   stash       Stash or pop changes across repos
#   reset       Reset repos to HEAD (--hard for working tree reset)
#   run         Run an arbitrary git/shell command in each repo
#   sync        Fetch upstream AVM CSV indexes → update data/modules/*.yaml
#   scrape      Alias for: check --dimension terraform-metadata
#   check       Run analysis dimensions on module(s) → populate analysis blocks
#
# Usage:
#   ./avm.sh setup  [--domains networking,compute] [--types res,ptn]
#   ./avm.sh clone  [--domain networking] [--type res] [--full]
#   ./avm.sh update [--domain networking] [--type res] [--parallel N]
#   ./avm.sh fetch  [--domain networking] [--type res] [--parallel N]
#   ./avm.sh status [--domain networking] [--type res]
#   ./avm.sh branch create  <name> [--domain D] [--type T]
#   ./avm.sh branch checkout <name> [--domain D] [--type T] [--fallback]
#   ./avm.sh branch delete  <name> [--domain D] [--type T] [--force]
#   ./avm.sh stash  [--domain D] [--type T]
#   ./avm.sh stash pop [--domain D] [--type T]
#   ./avm.sh reset  [--domain D] [--type T] [--hard]
#   ./avm.sh run    <cmd...> [--domain D] [--type T] [--parallel N]
#   ./avm.sh sync   [--dry-run]
#   ./avm.sh scrape [--dry-run] [--force] [--module NAME]
#   ./avm.sh check  [--module NAME] [--dimension DIM] [--dry-run] [--force]
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

  Global filters  (accepted by clone, update, fetch, status, branch, stash, reset, run, check, scrape):
    --domains <list>       Comma-separated domain slugs (e.g. networking,compute)
    --types   <list>       Comma-separated types: res, ptn, utl
    --module  <name>       Single module by name (e.g. avm-res-network-virtualnetwork)
    --dry-run              Show planned changes without executing

  Commands:

    setup        Generate .config/modules.yaml (select domains & types).

      --domains <list|all>   Comma-separated domain slugs, or 'all'
      --types   <list|all>   Comma-separated types (res,ptn,utl), or 'all'
      --include-deprecated   Include modules with status=Deprecated
      --dry-run              Show output without writing

      Examples:
        ./avm.sh setup --domains all
        ./avm.sh setup --domains networking,compute --types res

    clone        Clone module repos from .config/modules.yaml.
                 Run 'setup' first if modules.yaml does not exist.

      --full                 Full git history (default: shallow --depth 1)
      --git-name <name>      Set git user.name in cloned repos
      --git-email <email>    Set git user.email in cloned repos

      Examples:
        ./avm.sh clone
        ./avm.sh clone --domains networking --types res
        ./avm.sh clone --module avm-res-network-virtualnetwork

    update       Pull the latest changes for all already-cloned repos.

      --parallel N           Run N repos concurrently (default: 1)

      Examples:
        ./avm.sh update --parallel 10
        ./avm.sh update --domains networking --parallel 5

    fetch        Fetch all remotes without merging (fast, parallel).

      --parallel N           Concurrency (default: 20)

      Examples:
        ./avm.sh fetch --parallel 30
        ./avm.sh fetch --domains networking,compute

    status       Show repos with uncommitted changes or behind remote.

      Examples:
        ./avm.sh status
        ./avm.sh status --domains networking
        ./avm.sh status --module avm-res-network-virtualnetwork

    branch       Manage branches across matching repos.

      create  <name>         Create branch (skip if already exists)
      checkout <name>        Switch; --fallback to stay on current if absent
      delete  <name>         Delete; --force to use -D (allow unmerged)

      Examples:
        ./avm.sh branch create feature/my-fix
        ./avm.sh branch create feature/my-fix --domains networking
        ./avm.sh branch checkout feature/my-fix --fallback
        ./avm.sh branch delete feature/my-fix

    stash        Stash / pop working tree changes across repos.

      stash pop              Pop the most recent stash entry

      Examples:
        ./avm.sh stash --domains networking
        ./avm.sh stash pop

    reset        Reset repos to HEAD.

      --hard                 Hard reset (discards working tree changes)

      Examples:
        ./avm.sh reset --hard
        ./avm.sh reset --hard --domains networking

    run          Run an arbitrary command in each repo directory.

      <cmd...>               Any git or shell command
      --parallel N           Concurrency (default: 1)

      Examples:
        ./avm.sh run git log --oneline -3
        ./avm.sh run git status --domains networking

    sync         Fetch the three official AVM module index CSVs and
                 generate/update data/modules/*.yaml (one file per module).

      --dry-run              Show planned changes without writing files

      Examples:
        ./avm.sh sync
        ./avm.sh sync --dry-run

    scrape       Convenience alias for: check --dimension terraform-metadata

      --force                Re-analyze even if recently checked
      --max-age DAYS         Skip modules checked within N days (default: 7)

      Examples:
        ./avm.sh scrape --module avm-res-network-virtualnetwork
        ./avm.sh scrape --domains networking --types res
        GITHUB_TOKEN=ghp_... ./avm.sh scrape

    check        Run one or more analysis dimensions on module(s).
                 Built-in dimensions:
                   terraform-metadata       TF version + provider constraints + resources
                   avm-interface-compliance Required AVM interface variables
                   security-hardening       Hardcoded values, validation, sensitive outputs
                   test-coverage            examples/, tests/, *.go / *.tftest.hcl presence
                   doc-quality              README length and required section headers
                   dependency-health        Version constraint style

      --dimension DIM        Run only this dimension (repeat for multiple; default: all)
      --force                Ignore --max-age; always re-analyze
      --max-age DAYS         Skip dimensions checked within N days (default: 7)

      Examples:
        ./avm.sh check --module avm-res-network-virtualnetwork
        ./avm.sh check --domains networking --types res --dimension test-coverage
        ./avm.sh check --dimension avm-interface-compliance
        GITHUB_TOKEN=ghp_... ./avm.sh check

    help         Show this message.

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
  python3 "${SCRIPTS_DIR}/repos.py" clone "$@"
}

# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------
cmd_update() {
  python3 "${SCRIPTS_DIR}/repos.py" update "$@"
}

# ---------------------------------------------------------------------------
# Command: fetch
# ---------------------------------------------------------------------------
cmd_fetch() {
  python3 "${SCRIPTS_DIR}/repos.py" fetch "$@"
}

# ---------------------------------------------------------------------------
# Command: status
# ---------------------------------------------------------------------------
cmd_status() {
  python3 "${SCRIPTS_DIR}/repos.py" status "$@"
}

# ---------------------------------------------------------------------------
# Command: branch (create / checkout / delete)
# ---------------------------------------------------------------------------
cmd_branch() {
  python3 "${SCRIPTS_DIR}/repos.py" branch "$@"
}

# ---------------------------------------------------------------------------
# Command: stash / stash pop
# ---------------------------------------------------------------------------
cmd_stash() {
  python3 "${SCRIPTS_DIR}/repos.py" stash "$@"
}

# ---------------------------------------------------------------------------
# Command: reset
# ---------------------------------------------------------------------------
cmd_reset() {
  python3 "${SCRIPTS_DIR}/repos.py" reset "$@"
}

# ---------------------------------------------------------------------------
# Command: run (arbitrary command per repo)
# ---------------------------------------------------------------------------
cmd_run() {
  python3 "${SCRIPTS_DIR}/repos.py" run "$@"
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
  fetch)      cmd_fetch      "$@" ;;
  status)     cmd_status     "$@" ;;
  branch)     cmd_branch     "$@" ;;
  stash)      cmd_stash      "$@" ;;
  reset)      cmd_reset      "$@" ;;
  run)        cmd_run        "$@" ;;
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
