#Requires -Version 5.1
<#
.SYNOPSIS
    Pull latest changes in already-cloned AVM module repositories.

.DESCRIPTION
    Reads .config/modules.yaml and runs git pull --ff-only in matching
    terraform-azurerm-avm-* directories that already exist.
#>

[CmdletBinding()]
param(
    [string]$Domain = "",
    [ValidateSet("", "res", "ptn", "utl")]
    [string]$Type = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$ConfigDir = Join-Path $WorkspaceRoot '.config'
$ModulesFile = Join-Path $ConfigDir 'modules.yaml'

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "'git' is required but not installed."
    exit 1
}

if (-not (Test-Path $ModulesFile)) {
    Write-Host "ERROR: .config/modules.yaml not found. Run '.\avm.ps1 setup' first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Pulling latest changes for cloned module repos..."
Write-Host ("-" * 60)

$pulled = 0
$skipped = 0
$failed = 0
$currentName = ""
$currentDomain = ""
$currentType = ""

foreach ($rawLine in [System.IO.File]::ReadLines($ModulesFile)) {
    $line = $rawLine.TrimEnd()
    if ($line -match '^\s*#') { continue }
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    if ($line -match '^\s*-\s+name:\s+(.+)') {
        $currentName = $Matches[1].Trim()
        $currentDomain = ""
        $currentType = ""
    }
    elseif ($line -match '^\s*domain:\s+(.+)') {
        $currentDomain = $Matches[1].Trim()
    }
    elseif ($line -match '^\s*type:\s+(.+)') {
        $currentType = $Matches[1].Trim()

        if ($Domain -ne "" -and $currentDomain -ne $Domain) { continue }
        if ($Type -ne "" -and $currentType -ne $Type) { continue }

        $repoDir = Join-Path $WorkspaceRoot $currentName
        if (-not (Test-Path (Join-Path $repoDir '.git'))) {
            Write-Host ("  SKIP  {0}  (not cloned)" -f $currentName)
            $skipped++
            continue
        }

        Write-Host ("  PULL  {0,-60}  [{1}] ({2})" -f $currentName, $currentType, $currentDomain)
        & git -C $repoDir pull --ff-only --quiet
        if ($LASTEXITCODE -eq 0) {
            $pulled++
        }
        else {
            Write-Warning "Pull failed for $currentName"
            $failed++
        }
    }
}

Write-Host ("-" * 60)
Write-Host "Done - pulled: $pulled, skipped (not cloned): $skipped, failed: $failed"
if ($failed -gt 0) { exit 1 }
