#Requires -Version 5.1
<#
.SYNOPSIS
    Unified PowerShell entry point for the AVM metadata workspace.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptsDir = Join-Path $ScriptDir 'scripts'

$Command = if ($args.Count -gt 0) { [string]$args[0] } else { "" }
$RemainingArgs = @()
if ($args.Count -gt 1) {
    $RemainingArgs = @($args[1..($args.Count - 1)])
}

function Show-Usage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"
    Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "Usage: .\avm.ps1 <command> [--help] [options]"
    Write-Host ""
    Write-Host "Global flags (accepted by all commands unless noted):"
    Write-Host "  --domains <list|all>   Domain slugs, comma-separated, or 'all'"
    Write-Host "  --types   <list|all>   Types: res, ptn, utl, comma-separated, or 'all'"
    Write-Host "  --modules <list|all>   Module names, comma-separated, or 'all'"
    Write-Host "  --dry-run              Show planned changes without executing"
    Write-Host "  --help, -h             Show this message; or: .\avm.ps1 <cmd> --help"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup     Generate .config/modules.yaml from the data/modules/ catalog"
    Write-Host "  clone     Clone module repos listed in .config/modules.yaml"
    Write-Host "  update    Pull the latest changes in all already-cloned repos"
    Write-Host "  fetch     Fetch all remotes without merging (fast, parallel)"
    Write-Host "  status    Show repos with uncommitted changes or behind remote"
    Write-Host "  branch    Multi-repo branch management (create / checkout / delete)"
    Write-Host "  stash     Stash or pop working tree changes across repos"
    Write-Host "  reset     Reset repos to HEAD"
    Write-Host "  run       Run an arbitrary git/shell command in each repo directory"
    Write-Host "  cleanup   Remove cloned repos that are not in .config/modules.yaml"
    Write-Host "  sync      Fetch upstream AVM CSV indexes -> update data/modules/*.yaml"
    Write-Host "  scrape    Alias for: check --dimension terraform-metadata"
    Write-Host "  check     Run one or more analysis dimensions on module(s)"
    Write-Host "  report    Compliance scorecard, open issues rollup, and JSON catalog export"
    Write-Host "  activity  Git commit activity monitor across cloned repos"
    Write-Host "  index     Build per-resource-type stub inventory (data/resources/ etc.)"
    Write-Host "  providers Fetch provider changelog/issues -> write to provider stubs"
    Write-Host "  harvest   Harvest open GitHub issues from AVM module repos"
    Write-Host "  tag       Infer use-case tags -> write analysis_use_cases blocks"
    Write-Host "  site      Generate static HTML health dashboard (docs/site/index.html)"
    Write-Host "  help      Show this message"
    Write-Host ""
    Write-Host "Run '.\avm.ps1 <command> --help' for flags and examples."
    Write-Host ""
}

function Show-SetupUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  setup - Generate .config/modules.yaml from the data/modules/ catalog."
    Write-Host ""
    Write-Host "  Global filters:"
    Write-Host "    --domains <list|all>   Select domain(s); omit for interactive menu"
    Write-Host "    --types   <list|all>   Select type(s): res, ptn, utl; omit for interactive menu"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --include-deprecated   Also include modules with status=Deprecated"
    Write-Host "    --include-proposed     Also include modules with status=Proposed"
    Write-Host "    --dry-run              Show output without writing"
    Write-Host ""
    Write-Host "  Note: By default only modules with status=Available are included."
    Write-Host "        'all' selects every available domain or type."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 setup --domains all"
    Write-Host "    .\avm.ps1 setup --domains all --types all"
    Write-Host "    .\avm.ps1 setup --domains networking,compute --types res"
    Write-Host "    .\avm.ps1 setup --domains all --include-deprecated"
    Write-Host "    .\avm.ps1 setup --domains all --include-proposed"
    Write-Host "    .\avm.ps1 setup --dry-run"
    Write-Host ""
}

function Show-CloneUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  clone - Clone module repos listed in .config/modules.yaml."
    Write-Host "           Run 'setup' first if .config/modules.yaml does not exist."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules (all accept 'all' or a list)"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --full                 Clone full git history (default: shallow --depth 1)"
    Write-Host "    --git-name <name>      Set git user.name in each cloned repo"
    Write-Host "    --git-email <email>    Set git user.email in each cloned repo"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 clone"
    Write-Host "    .\avm.ps1 clone --domains networking --types res"
    Write-Host "    .\avm.ps1 clone --modules avm-res-network-virtualnetwork"
    Write-Host "    .\avm.ps1 clone --modules avm-res-network-virtualnetwork,avm-res-network-subnet"
    Write-Host "    .\avm.ps1 clone --domains networking --full"
    Write-Host ""
}

function Show-UpdateUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  update - Pull the latest changes in all already-cloned repos."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --parallel N           Run N repos concurrently (default: 1)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 update"
    Write-Host "    .\avm.ps1 update --parallel 10"
    Write-Host "    .\avm.ps1 update --domains networking --parallel 5"
    Write-Host "    .\avm.ps1 update --modules avm-res-network-virtualnetwork"
    Write-Host ""
}

function Show-FetchUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  fetch - Fetch all remotes without merging (fast, parallel)."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --parallel N           Concurrency (default: 20)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 fetch"
    Write-Host "    .\avm.ps1 fetch --parallel 30"
    Write-Host "    .\avm.ps1 fetch --domains networking,compute"
    Write-Host ""
}

function Show-StatusUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  status - Show repos with uncommitted changes or behind remote."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 status"
    Write-Host "    .\avm.ps1 status --domains networking"
    Write-Host "    .\avm.ps1 status --modules avm-res-network-virtualnetwork"
    Write-Host ""
}

function Show-BranchUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  branch - Manage branches across matching repos."
    Write-Host ""
    Write-Host "  Sub-operations:"
    Write-Host "    create  <name>         Create branch (skip if already exists)"
    Write-Host "    checkout <name>        Switch to branch; --fallback to stay on current if absent"
    Write-Host "    delete  <name>         Delete branch; --force to use -D (allow unmerged)"
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 branch create feature/my-fix"
    Write-Host "    .\avm.ps1 branch create feature/my-fix --domains networking"
    Write-Host "    .\avm.ps1 branch checkout feature/my-fix --fallback"
    Write-Host "    .\avm.ps1 branch checkout feature/my-fix --domains compute --fallback"
    Write-Host "    .\avm.ps1 branch delete feature/my-fix"
    Write-Host "    .\avm.ps1 branch delete feature/my-fix --force"
    Write-Host ""
}

function Show-StashUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  stash - Stash or pop working tree changes across repos."
    Write-Host ""
    Write-Host "  Sub-operations:"
    Write-Host "    stash         Stash current changes"
    Write-Host "    stash pop     Pop the most recent stash entry"
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 stash"
    Write-Host "    .\avm.ps1 stash --domains networking"
    Write-Host "    .\avm.ps1 stash pop"
    Write-Host "    .\avm.ps1 stash pop --domains networking"
    Write-Host ""
}

function Show-ResetUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  reset - Reset repos to HEAD."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --hard                 Hard reset (discards all working tree changes)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 reset --hard"
    Write-Host "    .\avm.ps1 reset --hard --domains networking"
    Write-Host "    .\avm.ps1 reset --hard --modules avm-res-network-virtualnetwork"
    Write-Host ""
}

function Show-RunUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  run - Run an arbitrary git or shell command in each repo directory."
    Write-Host ""
    Write-Host "  Usage: .\avm.ps1 run [--domains D] [--types T] [--modules M] [--parallel N] <cmd...>"
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host "  Note: pass --help BEFORE the run command (e.g. '.\avm.ps1 run --help')."
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --parallel N           Concurrency (default: 1)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 run git log --oneline -3"
    Write-Host "    .\avm.ps1 run git status --domains networking"
    Write-Host "    .\avm.ps1 run git fetch --parallel 10"
    Write-Host "    .\avm.ps1 run terraform fmt --types res"
    Write-Host ""
}

function Show-CleanupUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  cleanup - Remove cloned repos that are NOT in .config/modules.yaml."
    Write-Host "             Scope filters (--domains/--types/--modules) are ignored; the"
    Write-Host "             comparison is always against the full modules.yaml."
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --force                Remove even repos with uncommitted changes,"
    Write-Host "                           stash entries, or unpushed commits"
    Write-Host "    --dry-run              Show what would be removed without deleting"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 cleanup"
    Write-Host "    .\avm.ps1 cleanup --dry-run"
    Write-Host "    .\avm.ps1 cleanup --force"
    Write-Host ""
}

function Show-SyncUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  sync - Fetch the three official AVM module index CSVs and"
    Write-Host "          generate/update data/modules/*.yaml (one file per module)."
    Write-Host ""
    Write-Host "  Note: sync always refreshes the full catalog; filter flags do not apply."
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --include-deprecated   Also sync modules with status=Deprecated"
    Write-Host "    --include-proposed     Also sync modules with status=Proposed"
    Write-Host "    --force                Re-write all module files even if content is unchanged"
    Write-Host "    --dry-run              Show planned changes without writing files"
    Write-Host ""
    Write-Host "  Note: By default only modules with status=Available are synced."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 sync"
    Write-Host "    .\avm.ps1 sync --dry-run"
    Write-Host "    .\avm.ps1 sync --force"
    Write-Host "    .\avm.ps1 sync --include-proposed"
    Write-Host ""
}

function Show-ScrapeUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  scrape - Convenience alias for: check --dimension terraform-metadata"
    Write-Host "            Scrapes TF version, provider constraints, and managed resources"
    Write-Host "            from each cloned module repo into data/modules/*.yaml."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --force                Re-analyze even if recently checked"
    Write-Host "    --max-age DAYS         Skip modules checked within N days (default: 7)"
    Write-Host "    --dry-run              Show planned changes without writing files"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 scrape"
    Write-Host "    .\avm.ps1 scrape --modules avm-res-network-virtualnetwork"
    Write-Host "    .\avm.ps1 scrape --domains networking --types res"
    Write-Host ""
}

function Show-CheckUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  check - Run one or more analysis dimensions on module(s)."
    Write-Host ""
    Write-Host "  Built-in dimensions:"
    Write-Host "    terraform-metadata       TF version + provider constraints + resources"
    Write-Host "    avm-interface-compliance Required AVM interface variables"
    Write-Host "    security-hardening       Hardcoded values, validation, sensitive outputs"
    Write-Host "    test-coverage            examples/, tests/, *.go / *.tftest.hcl presence"
    Write-Host "    doc-quality              README length and required section headers"
    Write-Host "    dependency-health        Version constraint style"
    Write-Host "    provider-currency        Provider release findings + open issues (shorthand: currency)"
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --dimension DIM        Run only this dimension (repeat for multiple; default: all)"
    Write-Host "    --force                Ignore --max-age; always re-analyze"
    Write-Host "    --max-age DAYS         Skip dimensions checked within N days (default: 7)"
    Write-Host "    --dry-run              Show planned changes without writing files"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 check"
    Write-Host "    .\avm.ps1 check --modules avm-res-network-virtualnetwork"
    Write-Host "    .\avm.ps1 check --domains networking --types res --dimension test-coverage"
    Write-Host "    .\avm.ps1 check --dimension provider-currency"
    Write-Host "    .\avm.ps1 check --dimension avm-interface-compliance"
    Write-Host "    .\avm.ps1 check --force"
    Write-Host ""
}

function Show-ReportUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  report - Read-only catalog reports: compliance scores, open issues, JSON export."
    Write-Host ""
    Write-Host "  Subcommands:"
    Write-Host "    --scores              Weighted compliance scorecard, ranked by overall score."
    Write-Host "    --issues              Cross-module open issue rollup, grouped by severity."
    Write-Host "    --json                Export the full catalog to data/catalog.json (or --output FILE)."
    Write-Host "    --provider-findings   Provider currency triage: modules with critical/high release findings."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types"
    Write-Host ""
    Write-Host "  --scores flags:"
    Write-Host "    --min-score N         Only show modules with score < N (0-100)"
    Write-Host ""
    Write-Host "  --issues flags:"
    Write-Host "    --severity LEVEL[,.]  Filter by severity: critical, high, medium, low"
    Write-Host ""
    Write-Host "  --provider-findings flags:"
    Write-Host "    --severity LEVEL[,.]  Filter by severity (default: critical,high)"
    Write-Host ""
    Write-Host "  Common flags:"
    Write-Host "    --output FILE         Write output to FILE instead of stdout"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 report --scores"
    Write-Host "    .\avm.ps1 report --scores --domains networking --min-score 80"
    Write-Host "    .\avm.ps1 report --issues"
    Write-Host "    .\avm.ps1 report --issues --severity critical,high"
    Write-Host "    .\avm.ps1 report --provider-findings"
    Write-Host "    .\avm.ps1 report --provider-findings --severity critical"
    Write-Host "    .\avm.ps1 report --json"
    Write-Host "    .\avm.ps1 report --json --output docs/catalog.json"
    Write-Host ""
}

function Show-ActivityUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  activity - Git commit activity monitor across cloned module repos."
    Write-Host "              Ranks modules by recent commit count; flags stagnant repos."
    Write-Host ""
    Write-Host "  Options:"
    Write-Host "    --since PERIOD         Look-back window (default: 30d). Examples: 7d, 90d, 1y."
    Write-Host "    --top N                Show only the top N most active modules (0 = all)."
    Write-Host "    --stagnant-only        Only show modules with 0 commits."
    Write-Host "    --no-stagnant          Exclude modules with 0 commits."
    Write-Host "    --domains DOMAINS      Comma-separated domain slugs."
    Write-Host "    --types TYPES          Comma-separated module types: res, ptn, utl."
    Write-Host "    --output FILE          Write output to FILE instead of stdout."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 activity"
    Write-Host "    .\avm.ps1 activity --since 7d --no-stagnant"
    Write-Host "    .\avm.ps1 activity --stagnant-only"
    Write-Host "    .\avm.ps1 activity --domains networking --top 10"
    Write-Host ""
}

function Show-IndexUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  index - Build a per-resource-type stub inventory from all analysis data."
    Write-Host "           Collects all 5 symbol types (resources, datasources, functions,"
    Write-Host "           ephemeral, actions) from analysis_terraform_metadata blocks and"
    Write-Host "           creates stub YAML files at:"
    Write-Host "             data/resources/    azurerm_virtual_network.yaml"
    Write-Host "             data/datasources/  azurerm_subnet.yaml"
    Write-Host "             data/functions/    ..."
    Write-Host "             data/ephemerals/   ..."
    Write-Host "             data/actions/      ..."
    Write-Host "           Stubs are created once and NEVER overwritten by this command."
    Write-Host "           Use 'providers' to populate provider_updates.findings."
    Write-Host ""
    Write-Host "  Options:"
    Write-Host "    --dry-run              Preview without writing files."
    Write-Host "    --force                Overwrite existing stubs (resets provider data)."
    Write-Host "    --domains DOMAINS      Comma-separated domain slugs."
    Write-Host "    --types TYPES          Comma-separated module types: res, ptn, utl."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 index"
    Write-Host "    .\avm.ps1 index --dry-run"
    Write-Host "    .\avm.ps1 index --force"
    Write-Host "    .\avm.ps1 index --domains networking --types res"
    Write-Host ""
}

function Show-SiteUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  site - Generate static HTML health dashboard."
    Write-Host "          Produces a single self-contained HTML file (inline CSS, no CDN)."
    Write-Host "          Panels: stats, domain x dimension heatmap, owner map, per-domain tables."
    Write-Host ""
    Write-Host "  Options:"
    Write-Host "    --output FILE          Output path (default: docs/site/index.html)."
    Write-Host "    --domains DOMAINS      Comma-separated domain slugs."
    Write-Host "    --types TYPES          Comma-separated module types: res, ptn, utl."
    Write-Host "    --open                 Open the output in the default browser after generation."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 site"
    Write-Host "    .\avm.ps1 site --domains networking,compute"
    Write-Host "    .\avm.ps1 site --output /tmp/avm-health.html --open"
    Write-Host ""
}

function Show-ProvidersUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  providers - Fetch Terraform provider changelog and/or open GitHub Issues,"
    Write-Host "               and write findings into per-resource-type stubs."
    Write-Host ""
    Write-Host "  Two modes -- use --mode to control what is fetched:"
    Write-Host "    changes (default)  GitHub Releases -> provider_updates.findings"
    Write-Host "    issues             Open GitHub Issues -> provider_issues.items"
    Write-Host "    all                Both in a single pass"
    Write-Host ""
    Write-Host "  Requires GITHUB_TOKEN for best results (5 000 req/hr vs 60 unauthenticated)."
    Write-Host ""
    Write-Host "  Options:"
    Write-Host "    --provider LIST        Comma-separated provider names (default: azurerm,azapi)."
    Write-Host "                           Supported: azurerm, azapi, azuread"
    Write-Host "    --mode MODE            changes | issues | all (default: changes)"
    Write-Host "    --since VERSION        Only include releases >= this version (e.g., 4.0.0)."
    Write-Host "    --max-releases N       Maximum releases per provider (default: 100)."
    Write-Host "    --max-issues N         Maximum open issues per provider (default: 1000)."
    Write-Host "    --dry-run              Preview without modifying files."
    Write-Host "    --force                Re-fetch even if last_checked is within 24 h."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 providers"
    Write-Host "    .\avm.ps1 providers --mode issues"
    Write-Host "    .\avm.ps1 providers --mode all"
    Write-Host "    .\avm.ps1 providers --since 4.0.0"
    Write-Host "    .\avm.ps1 providers --provider azurerm --max-releases 10"
    Write-Host "    .\avm.ps1 providers --mode issues --max-issues 500"
    Write-Host "    .\avm.ps1 providers --dry-run"
    Write-Host "    .\avm.ps1 providers --force"
    Write-Host ""
}

function Show-HarvestUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  harvest - Harvest open GitHub issues from AVM module repos."
    Write-Host ""
    Write-Host "  Fetches open issues from each module's upstream GitHub repository"
    Write-Host "  (catalog.repo_url) and writes a module_issues: block into the module YAML."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Flags:"
    Write-Host "    --labels  LABEL[,.]    Issue label filter (default: bug,enhancement,"
    Write-Host "                           breaking-change,help wanted,good first issue)"
    Write-Host "    --max-issues N         Maximum issues to store per module (default: 50)"
    Write-Host "    --since Nd             Skip modules harvested within N days (default: 1)"
    Write-Host "    --force                Re-harvest even if last_harvested is fresh"
    Write-Host "    --dry-run              Preview without writing"
    Write-Host ""
    Write-Host "  Environment:"
    Write-Host "    GITHUB_TOKEN           GitHub personal access token (5 000 req/hr with token)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 harvest"
    Write-Host "    .\avm.ps1 harvest --domains networking --types res"
    Write-Host "    .\avm.ps1 harvest --modules avm-res-network-virtualnetwork"
    Write-Host "    .\avm.ps1 harvest --since 7d"
    Write-Host "    .\avm.ps1 harvest --force --dry-run"
    Write-Host ""
}

function Show-TagUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  tag - Infer functional use-case tags for AVM modules."
    Write-Host ""
    Write-Host "  Uses a three-tier signal model to classify modules:"
    Write-Host "    1. catalog.domain              -> base functional tags"
    Write-Host "    2. provider_namespace/resource_type -> resource-specific tags (res modules)"
    Write-Host "    3. resources_managed list      -> extra tags (helpers ignored)"
    Write-Host ""
    Write-Host "  Writes a # BEGIN ANALYSIS:use-cases block into each module YAML."
    Write-Host "  Does NOT modify enrichment.use_cases unless --promote is given."
    Write-Host ""
    Write-Host "  Global filters: --domains, --types, --modules"
    Write-Host ""
    Write-Host "  Flags:"
    Write-Host "    --force                Re-tag even if analysis_use_cases block already exists"
    Write-Host "    --dry-run              Preview inferred tags without writing"
    Write-Host "    --promote              Also seed enrichment.use_cases when it is currently []"
    Write-Host "    --tags-file PATH       Custom tag lookup YAML (default: data/use_case_tags.yaml)"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 tag"
    Write-Host "    .\avm.ps1 tag --domains networking --types res"
    Write-Host "    .\avm.ps1 tag --modules avm-res-network-virtualnetwork"
    Write-Host "    .\avm.ps1 tag --dry-run"
    Write-Host "    .\avm.ps1 tag --force"
    Write-Host "    .\avm.ps1 tag --promote"
    Write-Host ""
}

function Test-HelpFlag([string[]]$ArgList) {
    return $ArgList -contains '--help' -or $ArgList -contains '-h'
}

switch ($Command.ToLowerInvariant()) {
    'setup' {
        if (Test-HelpFlag $RemainingArgs) { Show-SetupUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'generate_config.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'clone' {
        if (Test-HelpFlag $RemainingArgs) { Show-CloneUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('clone') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'update' {
        if (Test-HelpFlag $RemainingArgs) { Show-UpdateUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('update') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'fetch' {
        if (Test-HelpFlag $RemainingArgs) { Show-FetchUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('fetch') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'status' {
        if (Test-HelpFlag $RemainingArgs) { Show-StatusUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('status') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'branch' {
        if (Test-HelpFlag $RemainingArgs) { Show-BranchUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('branch') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'stash' {
        if (Test-HelpFlag $RemainingArgs) { Show-StashUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('stash') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'reset' {
        if (Test-HelpFlag $RemainingArgs) { Show-ResetUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('reset') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'run' {
        # Only intercept --help when it is the very first argument so that
        # '.\avm.ps1 run git --help' still passes --help to git, not AVM.
        if ($RemainingArgs.Count -gt 0 -and ($RemainingArgs[0] -eq '--help' -or $RemainingArgs[0] -eq '-h')) {
            Show-RunUsage; exit 0
        }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('run') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'cleanup' {
        if (Test-HelpFlag $RemainingArgs) { Show-CleanupUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'manage_repos.py') @(@('cleanup') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'sync' {
        if (Test-HelpFlag $RemainingArgs) { Show-SyncUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'sync_catalog.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'scrape' {
        if (Test-HelpFlag $RemainingArgs) { Show-ScrapeUsage; exit 0 }
        # Backward-compat alias for: check --dimension terraform-metadata
        & python3 (Join-Path $ScriptsDir 'analyze_module.py') @(@('--dimension', 'terraform-metadata') + $RemainingArgs)
        if (-not $?) { exit 1 }
    }
    'check' {
        if (Test-HelpFlag $RemainingArgs) { Show-CheckUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'analyze_module.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'report' {
        if (Test-HelpFlag $RemainingArgs) { Show-ReportUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'report.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'activity' {
        if (Test-HelpFlag $RemainingArgs) { Show-ActivityUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'activity.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'index' {
        if (Test-HelpFlag $RemainingArgs) { Show-IndexUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'build_resource_index.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'site' {
        if (Test-HelpFlag $RemainingArgs) { Show-SiteUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'generate_site.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'providers' {
        if (Test-HelpFlag $RemainingArgs) { Show-ProvidersUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'fetch_provider_changes.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'harvest' {
        if (Test-HelpFlag $RemainingArgs) { Show-HarvestUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'harvest_module_issues.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    'tag' {
        if (Test-HelpFlag $RemainingArgs) { Show-TagUsage; exit 0 }
        & python3 (Join-Path $ScriptsDir 'tag_use_cases.py') @RemainingArgs
        if (-not $?) { exit 1 }
    }
    { $_ -in @('help', '--help', '-h') } {
        Show-Usage
    }
    '' {
        Show-Usage
        exit 1
    }
    default {
        Write-Host "ERROR: Unknown command '$Command'. Run '.\avm.ps1 help' for usage." -ForegroundColor Red
        exit 1
    }
}
