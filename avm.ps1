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
    Write-Host "  setup       Generate .config/modules.yaml."
    Write-Host "              -Domains <list|all>  Comma-separated domains, or all"
    Write-Host "              -Types   <list|all>  Comma-separated types: res,ptn,utl, or all"
    Write-Host ""
    Write-Host "  clone       Clone module repos from .config/modules.yaml."
    Write-Host "              -Domain <name>        Filter by a single domain"
    Write-Host "              -Type   <type>        Filter by res, ptn, or utl"
    Write-Host "              -Full                 Clone full history"
    Write-Host ""
    Write-Host "  update      Pull latest changes for already-cloned module repos."
    Write-Host "              -Domain <name>        Filter by a single domain"
    Write-Host "              -Type   <type>        Filter by res, ptn, or utl"
    Write-Host ""
    Write-Host "  help        Show this message."
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\avm.ps1 setup -Domains all"
    Write-Host "  .\avm.ps1 setup -Domains networking,compute -Types res"
    Write-Host "  .\avm.ps1 clone -Domain networking -Type res"
    Write-Host "  .\avm.ps1 update -Domain containers"
    Write-Host ""
}

function Convert-Arguments {
    param(
        [string[]]$Arguments = @(),
        [string[]]$ValueNames = @(),
        [string[]]$SwitchNames = @()
    )

    $valueLookup = @{}
    foreach ($name in $ValueNames) {
        $valueLookup[$name.ToLowerInvariant()] = $name
    }

    $switchLookup = @{}
    foreach ($name in $SwitchNames) {
        $switchLookup[$name.ToLowerInvariant()] = $name
    }

    $bound = @{}
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        $token = [string]$Arguments[$i]
        if ($token -in @('-h', '--help', '-?', 'help')) {
            Show-Usage
            exit 0
        }
        if (-not $token.StartsWith('-')) {
            Write-Host "ERROR: Unexpected positional argument '$token'." -ForegroundColor Red
            Show-Usage
            exit 1
        }

        $rawName = $token -replace '^-+', ''
        $inlineValue = $null
        if ($rawName -match '^([^=]+)=(.*)$') {
            $rawName = $Matches[1]
            $inlineValue = $Matches[2]
        }

        $lookupName = $rawName.ToLowerInvariant()
        if ($switchLookup.ContainsKey($lookupName)) {
            if ($null -ne $inlineValue -and $inlineValue -ne "") {
                Write-Host "ERROR: -$rawName does not accept a value." -ForegroundColor Red
                exit 1
            }
            $bound[$switchLookup[$lookupName]] = $true
        }
        elseif ($valueLookup.ContainsKey($lookupName)) {
            if ($null -eq $inlineValue) {
                $i++
                if ($i -ge $Arguments.Count -or ([string]$Arguments[$i]).StartsWith('-')) {
                    Write-Host "ERROR: -$rawName requires a value." -ForegroundColor Red
                    exit 1
                }
                $inlineValue = [string]$Arguments[$i]
            }
            $bound[$valueLookup[$lookupName]] = $inlineValue
        }
        else {
            Write-Host "ERROR: Unknown option '-$rawName'." -ForegroundColor Red
            Show-Usage
            exit 1
        }
    }

    return $bound
}

function Invoke-WorkspaceScript {
    param(
        [string]$Path,
        [hashtable]$Parameters = @{}
    )

    if (-not (Test-Path $Path)) {
        Write-Host "ERROR: script not found: $Path" -ForegroundColor Red
        exit 1
    }

    & $Path @Parameters
    if (-not $?) { exit 1 }
}

switch ($Command.ToLowerInvariant()) {
    'setup' {
        $params = Convert-Arguments $RemainingArgs @('Domains', 'Types') @()
        Invoke-WorkspaceScript (Join-Path $ScriptsDir 'generate_modules.ps1') $params
    }
    'clone' {
        $params = Convert-Arguments $RemainingArgs @('Domain', 'Type', 'GitName', 'GitEmail') @('Full')
        Invoke-WorkspaceScript (Join-Path $ScriptsDir 'clone_repos.ps1') $params
    }
    'update' {
        $params = Convert-Arguments $RemainingArgs @('Domain', 'Type') @()
        Invoke-WorkspaceScript (Join-Path $ScriptsDir 'update_repos.ps1') $params
    }
    { $_ -in @('help', '--help', '-h', '-?') } {
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
