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
    Write-Host "  sync      Fetch upstream AVM CSV indexes -> update data/modules/*.yaml"
    Write-Host "  scrape    Alias for: check --dimension terraform-metadata"
    Write-Host "  check     Run one or more analysis dimensions on module(s)"
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
    Write-Host "    --include-deprecated   Include modules with status=Deprecated"
    Write-Host "    --dry-run              Show output without writing"
    Write-Host ""
    Write-Host "  Note: 'all' selects every available domain or type."
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 setup --domains all"
    Write-Host "    .\avm.ps1 setup --domains all --types all"
    Write-Host "    .\avm.ps1 setup --domains networking,compute --types res"
    Write-Host "    .\avm.ps1 setup --domains all --include-deprecated"
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
    Write-Host "    --full                 Clone full git history (default: shallow)"
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
    Write-Host "    checkout <name>        Switch; --fallback to stay on current if absent"
    Write-Host "    delete  <name>         Delete; --force to use -D (allow unmerged)"
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

function Show-SyncUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  sync - Fetch upstream AVM CSV indexes -> update data/modules/*.yaml."
    Write-Host ""
    Write-Host "  Note: sync always refreshes the full catalog; filter flags do not apply."
    Write-Host ""
    Write-Host "  Command flags:"
    Write-Host "    --dry-run              Show planned changes without writing files"
    Write-Host ""
    Write-Host "  Examples:"
    Write-Host "    .\avm.ps1 sync"
    Write-Host "    .\avm.ps1 sync --dry-run"
    Write-Host ""
}

function Show-ScrapeUsage {
    Write-Host ""
    Write-Host "AVM Metadata Workspace"; Write-Host ("=" * 60)
    Write-Host ""
    Write-Host "  scrape - Alias for: check --dimension terraform-metadata"
    Write-Host "            Scrapes TF version, provider constraints, and managed resources."
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
    Write-Host "    .\avm.ps1 check --dimension avm-interface-compliance"
    Write-Host "    .\avm.ps1 check --force"
    Write-Host ""
}

function Test-HelpFlag([string[]]$ArgList) {
    return $ArgList -contains '--help' -or $ArgList -contains '-h'
}

switch ($Command.ToLowerInvariant()) {
    'setup' {
        if (Test-HelpFlag $RemainingArgs) { Show-SetupUsage; exit 0 }
        $pyArgs = $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'generate_config.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'clone' {
        if (Test-HelpFlag $RemainingArgs) { Show-CloneUsage; exit 0 }
        $pyArgs = @('clone') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'update' {
        if (Test-HelpFlag $RemainingArgs) { Show-UpdateUsage; exit 0 }
        $pyArgs = @('update') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'fetch' {
        if (Test-HelpFlag $RemainingArgs) { Show-FetchUsage; exit 0 }
        $pyArgs = @('fetch') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'status' {
        if (Test-HelpFlag $RemainingArgs) { Show-StatusUsage; exit 0 }
        $pyArgs = @('status') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'branch' {
        if (Test-HelpFlag $RemainingArgs) { Show-BranchUsage; exit 0 }
        $pyArgs = @('branch') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'stash' {
        if (Test-HelpFlag $RemainingArgs) { Show-StashUsage; exit 0 }
        $pyArgs = @('stash') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'reset' {
        if (Test-HelpFlag $RemainingArgs) { Show-ResetUsage; exit 0 }
        $pyArgs = @('reset') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'run' {
        # Only intercept --help when it is the very first argument so that
        # '.\avm.ps1 run git --help' still passes --help to git, not AVM.
        if ($RemainingArgs.Count -gt 0 -and ($RemainingArgs[0] -eq '--help' -or $RemainingArgs[0] -eq '-h')) {
            Show-RunUsage; exit 0
        }
        $pyArgs = @('run') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'sync' {
        if (Test-HelpFlag $RemainingArgs) { Show-SyncUsage; exit 0 }
        $pyArgs = $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'sync_catalog.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'scrape' {
        if (Test-HelpFlag $RemainingArgs) { Show-ScrapeUsage; exit 0 }
        # Backward-compat alias for: check --dimension terraform-metadata
        $pyArgs = @('--dimension', 'terraform-metadata') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'analyze_module.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'check' {
        if (Test-HelpFlag $RemainingArgs) { Show-CheckUsage; exit 0 }
        $pyArgs = $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'analyze_module.py') @pyArgs
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
