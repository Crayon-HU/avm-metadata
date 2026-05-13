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
#   report      Compliance scorecard, open issues rollup, and JSON catalog export
#   activity    Git commit activity monitor across cloned repos
#   index       Build per-resource-type stub inventory (data/resources/ etc.)
#   providers   Fetch provider changelog/issues → write provider_updates/provider_issues to stubs
#   site        Generate static HTML health dashboard
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

  Usage: ./avm.sh <command> [--help] [options]

  Global flags (accepted by all commands unless noted):
    --domains <list|all>   Domain slugs, comma-separated, or 'all'
    --types   <list|all>   Types: res, ptn, utl, comma-separated, or 'all'
    --modules <list|all>   Module names, comma-separated, or 'all'
    --dry-run              Show planned changes without executing
    --help, -h             Show this message; or: ./avm.sh <cmd> --help

  Commands:
    setup     Generate .config/modules.yaml from the data/modules/ catalog
    clone     Clone module repos listed in .config/modules.yaml
    update    Pull the latest changes in all already-cloned repos
    fetch     Fetch all remotes without merging (fast, parallel)
    status    Show repos with uncommitted changes or behind remote
    branch    Multi-repo branch management (create / checkout / delete)
    stash     Stash or pop working tree changes across repos
    reset     Reset repos to HEAD
    run       Run an arbitrary git/shell command in each repo directory
    cleanup   Remove cloned repos that are not in .config/modules.yaml
    sync      Fetch upstream AVM CSV indexes → update data/modules/*.yaml
    scrape    Alias for: check --dimension terraform-metadata
    check     Run one or more analysis dimensions on module(s)
    report    Compliance scorecard, open issues rollup, and JSON catalog export
    activity  Git commit activity monitor across cloned repos
    index     Build per-resource-type stub inventory (data/resources/ etc.)
    providers Fetch provider changelog/issues → write to provider_updates/provider_issues stubs
    harvest   Harvest open GitHub issues from AVM module repos → write module_issues blocks
    tag       Infer use-case tags → write analysis_use_cases blocks in module YAMLs
    site      Generate static HTML health dashboard (docs/site/index.html)
    help      Show this message

  Run './avm.sh <command> --help' for flags and examples.

EOF
}

_usage_setup() {
  _header
  cat <<'EOF'

  setup — Generate .config/modules.yaml from the data/modules/ catalog.

  Global filters:
    --domains <list|all>   Select domain(s); omit for interactive menu
    --types   <list|all>   Select type(s): res, ptn, utl; omit for interactive menu

  Command flags:
    --include-deprecated   Also include modules with status=Deprecated
    --include-proposed     Also include modules with status=Proposed
    --dry-run              Show output without writing

  Note: By default only modules with status=Available are included.
        'all' selects every available domain or type. Omitting --domains or
        --types triggers an interactive selection menu.

  Examples:
    ./avm.sh setup --domains all
    ./avm.sh setup --domains all --types all
    ./avm.sh setup --domains networking,compute --types res
    ./avm.sh setup --domains all --include-deprecated
    ./avm.sh setup --domains all --include-proposed
    ./avm.sh setup --dry-run

EOF
}

_usage_clone() {
  _header
  cat <<'EOF'

  clone — Clone module repos listed in .config/modules.yaml.
           Run 'setup' first if .config/modules.yaml does not exist.

  Global filters: --domains, --types, --modules (all accept 'all' or a comma-separated list)

  Command flags:
    --full                 Clone full git history (default: shallow --depth 1)
    --git-name <name>      Set git user.name in each cloned repo
    --git-email <email>    Set git user.email in each cloned repo

  Examples:
    ./avm.sh clone
    ./avm.sh clone --domains networking --types res
    ./avm.sh clone --modules avm-res-network-virtualnetwork
    ./avm.sh clone --modules avm-res-network-virtualnetwork,avm-res-network-subnet
    ./avm.sh clone --domains networking --full

EOF
}

_usage_update() {
  _header
  cat <<'EOF'

  update — Pull the latest changes in all already-cloned repos.

  Global filters: --domains, --types, --modules

  Command flags:
    --parallel N           Run N repos concurrently (default: 1)

  Examples:
    ./avm.sh update
    ./avm.sh update --parallel 10
    ./avm.sh update --domains networking --parallel 5
    ./avm.sh update --modules avm-res-network-virtualnetwork

EOF
}

_usage_fetch() {
  _header
  cat <<'EOF'

  fetch — Fetch all remotes without merging (fast, parallel).

  Global filters: --domains, --types, --modules

  Command flags:
    --parallel N           Concurrency (default: 20)

  Examples:
    ./avm.sh fetch
    ./avm.sh fetch --parallel 30
    ./avm.sh fetch --domains networking,compute

EOF
}

_usage_status() {
  _header
  cat <<'EOF'

  status — Show repos with uncommitted changes or behind remote.

  Global filters: --domains, --types, --modules

  Examples:
    ./avm.sh status
    ./avm.sh status --domains networking
    ./avm.sh status --modules avm-res-network-virtualnetwork

EOF
}

_usage_branch() {
  _header
  cat <<'EOF'

  branch — Manage branches across matching repos.

  Sub-operations:
    create  <name>         Create branch (skip if already exists)
    checkout <name>        Switch to branch; --fallback to stay on current if absent
    delete  <name>         Delete branch; --force to use -D (allow unmerged)

  Global filters: --domains, --types, --modules

  Examples:
    ./avm.sh branch create feature/my-fix
    ./avm.sh branch create feature/my-fix --domains networking
    ./avm.sh branch checkout feature/my-fix --fallback
    ./avm.sh branch checkout feature/my-fix --domains compute --fallback
    ./avm.sh branch delete feature/my-fix
    ./avm.sh branch delete feature/my-fix --force

EOF
}

_usage_stash() {
  _header
  cat <<'EOF'

  stash — Stash or pop working tree changes across repos.

  Sub-operations:
    stash         Stash current changes
    stash pop     Pop the most recent stash entry

  Global filters: --domains, --types, --modules

  Examples:
    ./avm.sh stash
    ./avm.sh stash --domains networking
    ./avm.sh stash pop
    ./avm.sh stash pop --domains networking

EOF
}

_usage_reset() {
  _header
  cat <<'EOF'

  reset — Reset repos to HEAD.

  Global filters: --domains, --types, --modules

  Command flags:
    --hard                 Hard reset (discards all working tree changes)

  Examples:
    ./avm.sh reset --hard
    ./avm.sh reset --hard --domains networking
    ./avm.sh reset --hard --modules avm-res-network-virtualnetwork

EOF
}

_usage_run() {
  _header
  cat <<'EOF'

  run — Run an arbitrary git or shell command in each repo directory.

  Usage: ./avm.sh run [--domains D] [--types T] [--modules M] [--parallel N] <cmd...>

  Global filters: --domains, --types, --modules
  Note: pass --help BEFORE the run command (e.g. './avm.sh run --help', not './avm.sh run git --help').

  Command flags:
    --parallel N           Concurrency (default: 1)

  Examples:
    ./avm.sh run git log --oneline -3
    ./avm.sh run git status --domains networking
    ./avm.sh run git fetch --parallel 10
    ./avm.sh run terraform fmt --types res

EOF
}

_usage_cleanup() {
  _header
  cat <<'EOF'

  cleanup — Remove cloned repos that are NOT in .config/modules.yaml.
             Scope filters (--domains/--types/--modules) are ignored; the
             comparison is always against the full modules.yaml.

  Command flags:
    --force                Remove even repos with uncommitted changes, stash
                           entries, or unpushed commits
    --dry-run              Show what would be removed without deleting

  Examples:
    ./avm.sh cleanup
    ./avm.sh cleanup --dry-run
    ./avm.sh cleanup --force

EOF
}

_usage_sync() {
  _header
  cat <<'EOF'

  sync — Fetch the three official AVM module index CSVs and
          generate/update data/modules/*.yaml (one file per module).

  Note: sync always refreshes the full catalog; filter flags do not apply.

  Command flags:
    --include-deprecated   Also sync modules with status=Deprecated
    --include-proposed     Also sync modules with status=Proposed
    --force                Re-write all module files even if catalog content is unchanged
    --dry-run              Show planned changes without writing files

  Note: By default only modules with status=Available are synced.

  Examples:
    ./avm.sh sync
    ./avm.sh sync --dry-run
    ./avm.sh sync --force
    ./avm.sh sync --include-proposed

EOF
}

_usage_scrape() {
  _header
  cat <<'EOF'

  scrape — Convenience alias for: check --dimension terraform-metadata
            Scrapes TF version, provider constraints, and managed resources
            from each cloned module repo into data/modules/*.yaml.

  Global filters: --domains, --types, --modules

  Command flags:
    --force                Re-analyze even if recently checked
    --max-age DAYS         Skip modules checked within N days (default: 7)
    --dry-run              Show planned changes without writing files

  Examples:
    ./avm.sh scrape
    ./avm.sh scrape --modules avm-res-network-virtualnetwork
    ./avm.sh scrape --domains networking --types res
    GITHUB_TOKEN=ghp_... ./avm.sh scrape

EOF
}

_usage_check() {
  _header
  cat <<'EOF'

  check — Run one or more analysis dimensions on module(s).

  Built-in dimensions:
    terraform-metadata       TF version + provider constraints + resources
    avm-interface-compliance Required AVM interface variables
    security-hardening       Hardcoded values, validation, sensitive outputs
    test-coverage            examples/, tests/, *.go / *.tftest.hcl presence
    doc-quality              README length and required section headers
    dependency-health        Version constraint style
    provider-currency        Provider release findings + open issues (shorthand: currency)

  Global filters: --domains, --types, --modules

  Command flags:
    --dimension DIM        Run only this dimension (repeat for multiple; default: all)
    --force                Ignore --max-age; always re-analyze
    --max-age DAYS         Skip dimensions checked within N days (default: 7)
    --dry-run              Show planned changes without writing files

  Examples:
    ./avm.sh check
    ./avm.sh check --modules avm-res-network-virtualnetwork
    ./avm.sh check --domains networking --types res --dimension test-coverage
    ./avm.sh check --dimension provider-currency
    ./avm.sh check --dimension avm-interface-compliance
    ./avm.sh check --force
    GITHUB_TOKEN=ghp_... ./avm.sh check

EOF
}

# ---------------------------------------------------------------------------
# Command: setup
# ---------------------------------------------------------------------------
cmd_setup() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_setup; return 0; }; done
  python3 "${SCRIPTS_DIR}/generate_config.py" "$@"
}

# ---------------------------------------------------------------------------
# Command: clone
# ---------------------------------------------------------------------------
cmd_clone() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_clone; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" clone "$@"
}

# ---------------------------------------------------------------------------
# Command: update
# ---------------------------------------------------------------------------
cmd_update() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_update; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" update "$@"
}

# ---------------------------------------------------------------------------
# Command: fetch
# ---------------------------------------------------------------------------
cmd_fetch() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_fetch; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" fetch "$@"
}

# ---------------------------------------------------------------------------
# Command: status
# ---------------------------------------------------------------------------
cmd_status() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_status; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" status "$@"
}

# ---------------------------------------------------------------------------
# Command: branch (create / checkout / delete)
# ---------------------------------------------------------------------------
cmd_branch() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_branch; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" branch "$@"
}

# ---------------------------------------------------------------------------
# Command: stash / stash pop
# ---------------------------------------------------------------------------
cmd_stash() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_stash; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" stash "$@"
}

# ---------------------------------------------------------------------------
# Command: reset
# ---------------------------------------------------------------------------
cmd_reset() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_reset; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" reset "$@"
}

# ---------------------------------------------------------------------------
# Command: run (arbitrary command per repo)
# Note: only intercept --help when it is the very first argument so that
#       './avm.sh run git --help' still passes --help to git, not AVM.
# ---------------------------------------------------------------------------
cmd_run() {
  [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]] && { _usage_run; return 0; }
  python3 "${SCRIPTS_DIR}/manage_repos.py" run "$@"
}

# ---------------------------------------------------------------------------
# Command: cleanup
# ---------------------------------------------------------------------------
cmd_cleanup() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_cleanup; return 0; }; done
  python3 "${SCRIPTS_DIR}/manage_repos.py" cleanup "$@"
}

# ---------------------------------------------------------------------------
# Command: sync
# ---------------------------------------------------------------------------
cmd_sync() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_sync; return 0; }; done
  python3 "${SCRIPTS_DIR}/sync_catalog.py" "$@"
}

# ---------------------------------------------------------------------------
# Command: scrape (backward-compat alias for check --dimension terraform-metadata)
# ---------------------------------------------------------------------------
cmd_scrape() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_scrape; return 0; }; done
  python3 "${SCRIPTS_DIR}/analyze_module.py" --dimension terraform-metadata "$@"
}

# ---------------------------------------------------------------------------
# Command: check
# ---------------------------------------------------------------------------
cmd_check() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_check; return 0; }; done
  python3 "${SCRIPTS_DIR}/analyze_module.py" "$@"
}

# ---------------------------------------------------------------------------
# Command: report
# ---------------------------------------------------------------------------
_usage_report() {
  _header
  cat <<'EOF'

  report — Read-only catalog reports: compliance scores, open issues, JSON export.

  Subcommands:
    --scores              Weighted compliance scorecard, ranked by overall score.
    --issues              Cross-module open issue rollup, grouped by severity.
    --json                Export the full catalog to data/catalog.json (or --output FILE).
    --provider-findings   Provider currency triage: modules with critical/high release findings.

  Global filters: --domains, --types

  --scores flags:
    --min-score N    Only show modules with score < N (0–100)

  --issues flags:
    --severity LEVEL[,…]  Filter by severity: critical, high, medium, low

  --provider-findings flags:
    --severity LEVEL[,…]  Filter by severity (default: critical,high)

  Common flags:
    --output FILE    Write output to FILE instead of stdout

  Examples:
    ./avm.sh report --scores
    ./avm.sh report --scores --domains networking --min-score 80
    ./avm.sh report --issues
    ./avm.sh report --issues --severity critical,high
    ./avm.sh report --provider-findings
    ./avm.sh report --provider-findings --severity critical
    ./avm.sh report --json
    ./avm.sh report --json --output docs/catalog.json

EOF
}

cmd_report() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_report; return 0; }; done
  python3 "${SCRIPTS_DIR}/report.py" "$@"
}

_usage_activity() {
  _header
  cat <<'EOF'

  activity — Git commit activity monitor across cloned module repos.
             Ranks modules by recent commit count; flags stagnant repos.

  Usage:
    ./avm.sh activity [options]

  Options:
    --since PERIOD       Look-back window (default: 30d). Examples: 7d, 90d, 1y.
    --top N              Show only the top N most active modules (0 = all).
    --stagnant-only      Only show modules with 0 commits.
    --no-stagnant        Exclude modules with 0 commits.
    --domains DOMAINS    Comma-separated domain slugs.
    --types TYPES        Comma-separated module types: res, ptn, utl.
    --output FILE        Write output to FILE instead of stdout.

  Examples:
    ./avm.sh activity
    ./avm.sh activity --since 7d --no-stagnant
    ./avm.sh activity --stagnant-only
    ./avm.sh activity --domains networking --top 10

EOF
}

cmd_activity() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_activity; return 0; }; done
  python3 "${SCRIPTS_DIR}/activity.py" "$@"
}

_usage_index() {
  _header
  cat <<'EOF'

  index — Build a per-resource-type stub inventory from all analysis data.
          Collects all 5 symbol types (resources, datasources, functions,
          ephemeral, actions) from analysis_terraform_metadata blocks and
          creates stub YAML files at:
            data/resources/    azurerm_virtual_network.yaml
            data/datasources/  azurerm_subnet.yaml
            data/functions/    ...
            data/ephemerals/   ...
            data/actions/      ...
          Stubs are created once and NEVER overwritten by this command.
          Use 'providers' to populate provider_updates.findings.
          Use Phase 3 to populate provider_issues.items.

  Usage:
    ./avm.sh index [options]

  Options:
    --dry-run             Preview without writing files.
    --force               Overwrite existing stubs (use with care — resets
                          provider_updates and provider_issues to empty).
    --domains DOMAINS     Comma-separated domain slugs.
    --types TYPES         Comma-separated module types: res, ptn, utl.

  Examples:
    ./avm.sh index
    ./avm.sh index --dry-run
    ./avm.sh index --force
    ./avm.sh index --domains networking --types res

EOF
}

cmd_index() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_index; return 0; }; done
  python3 "${SCRIPTS_DIR}/build_resource_index.py" "$@"
}

_usage_site() {
  _header
  cat <<'EOF'
         Produces a single self-contained HTML file (inline CSS, no CDN).
         Per-domain tables with colour-coded scores, dimension badges,
         staleness indicators, and version pin status.

  Usage:
    ./avm.sh site [options]

  Options:
    --output FILE         Output path (default: docs/site/index.html).
    --domains DOMAINS     Comma-separated domain slugs.
    --types TYPES         Comma-separated module types: res, ptn, utl.
    --open                Open the output in the default browser after generation.

  Examples:
    ./avm.sh site
    ./avm.sh site --domains networking,compute
    ./avm.sh site --output /tmp/avm-health.html --open

EOF
}

cmd_site() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_site; return 0; }; done
  python3 "${SCRIPTS_DIR}/generate_site.py" "$@"
}

_usage_providers() {
  _header
  cat <<'EOF'

  providers — Fetch Terraform provider changelog and/or open GitHub Issues,
              and write findings into per-resource-type stubs at:
                data/resources/    azurerm_virtual_network.yaml
                data/datasources/  azurerm_subnet.yaml
                ...

              Two modes — use --mode to control what is fetched:
                changes (default)  GitHub Releases → provider_updates.findings
                issues             Open GitHub Issues → provider_issues.items
                all                Both in a single pass

              Stubs are updated in-place; all sections not targeted by the
              current mode are preserved unchanged.

              Requires GITHUB_TOKEN for best results (5 000 req/hr vs 60 unauthenticated).

  Usage:
    ./avm.sh providers [options]

  Options:
    --provider LIST       Comma-separated provider names (default: azurerm,azapi).
                          Supported: azurerm, azapi, azuread
    --mode MODE           changes | issues | all (default: changes)
    --since VERSION       Only include releases >= this version (e.g., 4.0.0).
                          Applies to changes mode only.
    --max-releases N      Maximum releases per provider (default: 100).
    --max-issues N        Maximum open issues per provider (default: 1000).
    --dry-run             Preview without modifying files.
    --force               Re-fetch even if last_checked is within 24 h.

  Examples:
    ./avm.sh providers                                    # changelog only (default)
    ./avm.sh providers --mode issues                      # open issues only
    ./avm.sh providers --mode all                         # changelog + issues
    ./avm.sh providers --since 4.0.0                      # changelog from version 4.0.0
    ./avm.sh providers --provider azurerm --max-releases 10
    ./avm.sh providers --mode issues --max-issues 500
    ./avm.sh providers --dry-run
    ./avm.sh providers --force

EOF
}

cmd_providers() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_providers; return 0; }; done
  python3 "${SCRIPTS_DIR}/fetch_provider_changes.py" "$@"
}

_usage_harvest() {
  _header
  cat <<'EOHELP'

  harvest — Harvest open GitHub issues from AVM module repos.

  Fetches open issues from each module's upstream GitHub repository
  (catalog.repo_url) and writes a module_issues: block into the module YAML.

  Global filters: --domains, --types, --modules

  Flags:
    --labels  LABEL[,…]   Issue label filter; keep issues with ANY of these labels
                          (default: bug,enhancement,breaking-change,help wanted,good first issue)
    --max-issues N        Maximum issues to store per module (default: 50)
    --since Nd            Skip modules harvested within N days (default: 1)
    --force               Re-harvest even if last_harvested is fresh
    --dry-run             Preview without writing

  Environment:
    GITHUB_TOKEN          GitHub personal access token (5 000 req/hr with token;
                          60 req/hr without)

  Examples:
    ./avm.sh harvest
    ./avm.sh harvest --domains networking --types res
    ./avm.sh harvest --modules avm-res-network-virtualnetwork
    ./avm.sh harvest --since 7d
    ./avm.sh harvest --force --dry-run

EOHELP
}

cmd_harvest() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_harvest; return 0; }; done
  python3 "${SCRIPTS_DIR}/harvest_module_issues.py" "$@"
}

# ---------------------------------------------------------------------------
# tag — Infer use-case tags
# ---------------------------------------------------------------------------
_usage_tag() {
  _header
  cat <<'EOHELP'

  tag — Infer functional use-case tags for AVM modules.

  Uses a three-tier signal model to classify modules:
    1. catalog.domain             → base functional tags
    2. provider_namespace/resource_type → resource-specific tags (res modules)
    3. resources_managed list     → extra tags (helpers ignored)

  Writes a # BEGIN ANALYSIS:use-cases block into each module YAML.
  Does NOT modify enrichment.use_cases unless --promote is given.

  Global filters: --domains, --types, --modules

  Flags:
    --force             Re-tag even if analysis_use_cases block already exists
    --dry-run           Preview inferred tags without writing
    --promote           Also seed enrichment.use_cases when it is currently []
    --tags-file PATH    Custom tag lookup YAML (default: data/use_case_tags.yaml)

  Examples:
    ./avm.sh tag                                      # tag all untagged modules
    ./avm.sh tag --domains networking --types res     # filtered
    ./avm.sh tag --modules avm-res-network-virtualnetwork
    ./avm.sh tag --dry-run                            # preview all inferred tags
    ./avm.sh tag --force                              # re-classify all modules
    ./avm.sh tag --promote                            # also seed enrichment.use_cases

EOHELP
}

cmd_tag() {
  for a in "$@"; do [[ "$a" == "--help" || "$a" == "-h" ]] && { _usage_tag; return 0; }; done
  python3 "${SCRIPTS_DIR}/tag_use_cases.py" "$@"
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
  cleanup)    cmd_cleanup    "$@" ;;
  sync)       cmd_sync       "$@" ;;
  scrape)     cmd_scrape     "$@" ;;
  check)      cmd_check      "$@" ;;
  report)     cmd_report     "$@" ;;
  activity)   cmd_activity   "$@" ;;
  index)      cmd_index      "$@" ;;
  site)       cmd_site       "$@" ;;
  providers)  cmd_providers  "$@" ;;
  harvest)    cmd_harvest    "$@" ;;
  tag)        cmd_tag        "$@" ;;
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
