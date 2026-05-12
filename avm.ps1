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
    Write-Host "Usage: .\avm.ps1 <command> [options]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  setup       Generate .config/modules.yaml from data/modules/ catalog."
    Write-Host "              --domains <list|all>      Comma-separated domains, or all"
    Write-Host "              --types   <list|all>      Comma-separated types: res,ptn,utl, or all"
    Write-Host "              --include-deprecated      Include modules with status=Deprecated"
    Write-Host "              --dry-run                 Show output, do not write file"
    Write-Host ""
    Write-Host "  clone       Clone module repos from .config/modules.yaml."
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --module  <name>          Filter to a single module by name"
    Write-Host "              --full                    Clone full history"
    Write-Host "              --git-name <name>         Set git user.name in cloned repos"
    Write-Host "              --git-email <email>       Set git user.email in cloned repos"
    Write-Host ""
    Write-Host "  update      Pull latest changes for already-cloned module repos."
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --module  <name>          Filter to a single module by name"
    Write-Host "              --parallel N              Run N repos concurrently (default: 1)"
    Write-Host ""
    Write-Host "  fetch       Fetch all remotes without merging (parallel)."
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --module  <name>          Filter to a single module by name"
    Write-Host "              --parallel N              Concurrency (default: 20)"
    Write-Host ""
    Write-Host "  status      Show repos with uncommitted changes or behind remote."
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --module  <name>          Filter to a single module by name"
    Write-Host ""
    Write-Host "  branch      Multi-repo branch management."
    Write-Host "              create  <name>            Create branch (skip if exists)"
    Write-Host "              checkout <name>           Switch branch (--fallback to stay if absent)"
    Write-Host "              delete  <name>            Delete branch (--force for unmerged)"
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --module  <name>          Filter to a single module by name"
    Write-Host ""
    Write-Host "  stash       Stash working tree changes across repos."
    Write-Host "  stash pop   Pop the most recent stash entry across repos."
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host ""
    Write-Host "  reset       Reset repos to HEAD."
    Write-Host "              --hard                    Hard reset (discard working tree changes)"
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host ""
    Write-Host "  run         Run an arbitrary command in each repo directory."
    Write-Host "              <cmd...>                  Any git or shell command"
    Write-Host "              --parallel N              Concurrency (default: 1)"
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host ""
    Write-Host "  sync        Fetch AVM CSV indexes → update data/modules/*.yaml."
    Write-Host "              --dry-run                 Show planned changes, no writes"
    Write-Host ""
    Write-Host "  scrape      Alias for: check --dimension terraform-metadata"
    Write-Host "              --dry-run                 Show planned changes, no writes"
    Write-Host "              --force                   Re-analyze even if recently checked"
    Write-Host "              --module <name>           Analyze a single module"
    Write-Host "              --domains <list>          Comma-separated domain slugs"
    Write-Host "              --types   <list>          Comma-separated types (res,ptn,utl)"
    Write-Host "              --max-age DAYS            Skip if checked within N days (default: 7)"
    Write-Host ""
    Write-Host "  check       Run analysis dimensions on module(s)."
    Write-Host "              --module    <name>        Analyze a single module"
    Write-Host "              --domains   <list>        Comma-separated domain slugs"
    Write-Host "              --types     <list>        Comma-separated types (res,ptn,utl)"
    Write-Host "              --dimension DIM           Run only this dimension (repeat for multi)"
    Write-Host "              --dry-run                 Show planned changes, no writes"
    Write-Host "              --force                   Ignore --max-age; always re-analyze"
    Write-Host "              --max-age   DAYS          Skip if checked within N days (default: 7)"
    Write-Host ""
    Write-Host "  help        Show this message."
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\avm.ps1 setup --domains all"
    Write-Host "  .\avm.ps1 setup --domains networking,compute --types res"
    Write-Host "  .\avm.ps1 clone --domains networking --types res"
    Write-Host "  .\avm.ps1 clone --module avm-res-network-virtualnetwork"
    Write-Host "  .\avm.ps1 update --parallel 10"
    Write-Host "  .\avm.ps1 update --domains networking --parallel 5"
    Write-Host "  .\avm.ps1 fetch --parallel 30"
    Write-Host "  .\avm.ps1 status --domains networking"
    Write-Host "  .\avm.ps1 status --module avm-res-network-virtualnetwork"
    Write-Host "  .\avm.ps1 branch create feature/my-fix"
    Write-Host "  .\avm.ps1 branch create feature/my-fix --domains networking"
    Write-Host "  .\avm.ps1 branch checkout feature/my-fix --fallback"
    Write-Host "  .\avm.ps1 stash --domains networking"
    Write-Host "  .\avm.ps1 stash pop"
    Write-Host "  .\avm.ps1 reset --hard --domains networking"
    Write-Host "  .\avm.ps1 run git log --oneline -3"
    Write-Host "  .\avm.ps1 sync"
    Write-Host "  .\avm.ps1 scrape --module avm-res-network-virtualnetwork"
    Write-Host "  .\avm.ps1 scrape --domains networking --types res"
    Write-Host "  .\avm.ps1 check --module avm-res-network-virtualnetwork"
    Write-Host "  .\avm.ps1 check --domains networking --types res --dimension test-coverage"
    Write-Host "  .\avm.ps1 check --dimension test-coverage"
    Write-Host ""
}

switch ($Command.ToLowerInvariant()) {
    'setup' {
        $pyArgs = $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'generate_config.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'clone' {
        $pyArgs = @('clone') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'update' {
        $pyArgs = @('update') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'fetch' {
        $pyArgs = @('fetch') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'status' {
        $pyArgs = @('status') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'branch' {
        $pyArgs = @('branch') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'stash' {
        $pyArgs = @('stash') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'reset' {
        $pyArgs = @('reset') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'run' {
        $pyArgs = @('run') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'repos.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'sync' {
        $pyArgs = $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'sync_catalog.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'scrape' {
        # Backward-compat alias for: check --dimension terraform-metadata
        $pyArgs = @('--dimension', 'terraform-metadata') + $RemainingArgs
        & python3 (Join-Path $ScriptsDir 'analyze_module.py') @pyArgs
        if (-not $?) { exit 1 }
    }
    'check' {
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
