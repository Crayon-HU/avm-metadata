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

  Commands:
    setup        Generate .config/modules.yaml (select domains & types).

      --domains <list|all>   Comma-separated domain names, or 'all'
      --types   <list|all>   Comma-separated types (res,ptn,utl), or 'all'
      --include-deprecated   Include modules with status=Deprecated
      --dry-run              Show output without writing

    clone        Clone module repos from .config/modules.yaml.
                 Run 'setup' first if modules.yaml does not exist.

      --domains <list>       Comma-separated domain slugs (e.g. networking,compute)
      --types   <list>       Comma-separated types (res,ptn,utl)
      --module  <name>       Filter to a single module by name
      --full                 Full git history (default: shallow --depth 1)
      --git-name <name>      Set git user.name in cloned repos
      --git-email <email>    Set git user.email in cloned repos

    update       Pull the latest changes for all already-cloned repos.

      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types (res,ptn,utl)
      --module  <name>       Filter to a single module by name
      --parallel N           Run N repos concurrently (default: 1)

    fetch        Fetch all remotes without merging (fast, parallel).

      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types
      --module  <name>       Filter to a single module by name
      --parallel N           Concurrency (default: 20)

    status       Show repos with uncommitted changes or that are behind remote.

      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types
      --module  <name>       Filter to a single module by name

    branch       Create, checkout, or delete a branch in all matching repos.

      create  <name>         Create branch (skip if already exists)
      checkout <name>        Switch to branch; --fallback to stay on current if absent
      delete  <name>         Delete branch; --force to use -D (unmerged ok)

      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types
      --module  <name>       Filter to a single module by name

    stash        Stash working tree changes across repos.
    stash pop    Pop the most recent stash entry across repos.

      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types

    reset        Reset all repos to HEAD.

      --hard                 Hard reset (discards working tree changes)
      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types

    run          Run an arbitrary command in each repo directory.

      <cmd...>               Any git or shell command
      --parallel N           Concurrency (default: 1)
      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types

    sync         Fetch the three official AVM module index CSVs and
                 generate/update data/modules/*.yaml (one file per module).

      --dry-run              Show planned changes without writing files

    scrape       Convenience alias for: check --dimension terraform-metadata

      --dry-run              Show planned changes without writing files
      --force                Re-analyze even if recently checked
      --module <name>        Analyze a single module by name
      --domains <list>       Comma-separated domain slugs
      --types   <list>       Comma-separated types (res,ptn,utl)
      --max-age DAYS         Skip modules checked within N days (default: 7)

    check        Run one or more analysis dimensions on module(s).
                 Six built-in dimensions:
                   terraform-metadata       TF version + provider constraints + resources
                   avm-interface-compliance Required AVM interface variables
                   security-hardening       Hardcoded values, validation, sensitive outputs
                   test-coverage            examples/, tests/, *.go / *.tftest.hcl presence
                   doc-quality              README length and required section headers
                   dependency-health        Version constraint style

      --module    <name>     Analyze a single module by name
      --domains   <list>     Comma-separated domain slugs
      --types     <list>     Comma-separated types (res,ptn,utl)
      --dimension DIM        Run only this dimension (repeat for multiple; default: all)
      --dry-run              Show planned changes without writing files
      --force                Ignore --max-age; always re-analyze
      --max-age   DAYS       Skip dimensions checked within N days (default: 7)

    help         Show this message.

  Examples:
    ./avm.sh setup --domains all
    ./avm.sh setup --domains networking,compute --types res
    ./avm.sh clone --domains networking --types res
    ./avm.sh clone --module avm-res-network-virtualnetwork
    ./avm.sh update --parallel 10
    ./avm.sh update --domains networking --parallel 5
    ./avm.sh fetch --parallel 30
    ./avm.sh fetch --domains networking,compute
    ./avm.sh status --domains networking
    ./avm.sh status --module avm-res-network-virtualnetwork
    ./avm.sh branch create feature/my-fix
    ./avm.sh branch create feature/my-fix --domains networking
    ./avm.sh branch checkout feature/my-fix --fallback
    ./avm.sh branch delete feature/my-fix --domains networking
    ./avm.sh stash --domains networking
    ./avm.sh stash pop
    ./avm.sh reset --hard --domains networking
    ./avm.sh run git log --oneline -3
    ./avm.sh sync --dry-run
    ./avm.sh scrape --module avm-res-network-virtualnetwork
    ./avm.sh scrape --domains networking --types res
    GITHUB_TOKEN=ghp_... ./avm.sh check --module avm-res-network-virtualnetwork
    ./avm.sh check --domains networking --types res --dimension test-coverage
    ./avm.sh check --dimension test-coverage

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
