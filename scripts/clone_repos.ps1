#Requires -Version 5.1
<#
.SYNOPSIS
    Clone AVM module repositories listed in .config/modules.yaml

.DESCRIPTION
    Reads the generated .config/modules.yaml (run scripts/generate_modules.ps1 first).
    Clones each repo into the workspace root. Existing directories are skipped.

.PARAMETER Domain
    Filter by domain slug (e.g. networking, compute). Default: all domains.

.PARAMETER Type
    Filter by module type: res, ptn, or utl. Default: all types.

.PARAMETER Full
    Clone full history. Default: shallow clone (--depth 1).

.PARAMETER GitName
    Set git user.name locally in each cloned repo.

.PARAMETER GitEmail
    Set git user.email locally in each cloned repo.

.EXAMPLE
    .\scripts\clone_repos.ps1
    .\scripts\clone_repos.ps1 -Domain networking
    .\scripts\clone_repos.ps1 -Type ptn
    .\scripts\clone_repos.ps1 -Domain networking -Type res -Full

.REQUIREMENTS
    git (no other dependencies)
#>

[CmdletBinding()]
param(
    [string]$Domain   = "",
    [ValidateSet("", "res", "ptn", "utl")]
    [string]$Type     = "",
    [switch]$Full,
    [string]$GitName  = "",
    [string]$GitEmail = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
$ScriptDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$ConfigDir     = Join-Path $WorkspaceRoot '.config'
$ModulesFile   = Join-Path $ConfigDir 'modules.yaml'

# ---------------------------------------------------------------------------
# Dependency checks
# ---------------------------------------------------------------------------
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "'git' is required but not installed."
    exit 1
}

if (-not (Test-Path $ModulesFile)) {
    Write-Host "ERROR: .config/modules.yaml not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Generate it first by running:"
    Write-Host "  .\scripts\generate_modules.ps1"
    exit 1
}

# ---------------------------------------------------------------------------
# Parse modules.yaml
# ---------------------------------------------------------------------------
$Names    = [System.Collections.Generic.List[string]]::new()
$Types    = [System.Collections.Generic.List[string]]::new()
$Domains  = [System.Collections.Generic.List[string]]::new()
$Urls     = [System.Collections.Generic.List[string]]::new()
$Branches = [System.Collections.Generic.List[string]]::new()

$_name = $null; $_type = $null; $_domain = $null; $_url = $null; $_branch = 'main'

function Emit-Module {
    if (-not $_name -or -not $_url) { return }

    # Apply filters
    if ($Domain -ne "" -and $_domain -ne $Domain) { return }
    if ($Type   -ne "" -and $_type   -ne $Type)   { return }

    $Names.Add($_name)
    $Types.Add($(if ($_type) { $_type } else { "" }))
    $Domains.Add($(if ($_domain) { $_domain } else { "" }))
    $Urls.Add($_url)
    $Branches.Add($_branch)
}

foreach ($rawLine in [System.IO.File]::ReadLines($ModulesFile)) {
    $line = $rawLine.TrimEnd()
    if ($line -match '^\s*#')              { continue }
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    if ($line -match '^\s*-\s+name:\s+(.+)') {
        Emit-Module
        $_name = $Matches[1].Trim(); $_type = $null; $_domain = $null
        $_url = $null; $_branch = 'main'
    }
    elseif ($line -match '^\s+type:\s+(.+)')   { $_type   = $Matches[1].Trim() }
    elseif ($line -match '^\s+domain:\s+(.+)') { $_domain = $Matches[1].Trim() }
    elseif ($line -match '^\s+url:\s+(.+)')    { $_url    = $Matches[1].Trim() }
    elseif ($line -match '^\s+branch:\s+(.+)') { $_branch = $Matches[1].Trim() }
}
Emit-Module  # flush last entry

# ---------------------------------------------------------------------------
# Print effective filters
# ---------------------------------------------------------------------------
$moduleCount = $Names.Count

if ($moduleCount -eq 0) {
    Write-Host "No modules match the specified filters. Nothing to clone."
    if ($Domain -ne "") { Write-Host "  -Domain $Domain" }
    if ($Type   -ne "") { Write-Host "  -Type $Type" }
    exit 0
}

$cloneMode = if ($Full) { "full history" } else { "shallow (--depth 1)" }

Write-Host "AVM clone — $moduleCount modules"
Write-Host "Workspace root: $WorkspaceRoot"
if ($Domain -ne "") { Write-Host "Domain filter:  $Domain" }
if ($Type   -ne "") { Write-Host "Type filter:    $Type" }
Write-Host "Clone mode:     $cloneMode"
Write-Host ("-" * 60)

# ---------------------------------------------------------------------------
# Clone repos
# ---------------------------------------------------------------------------
$cloned  = 0
$skipped = 0
$failed  = 0

for ($i = 0; $i -lt $Names.Count; $i++) {
    $name     = $Names[$i]
    $url      = $Urls[$i]
    $branch   = $Branches[$i]
    $typeLabel = "[{0}]" -f $Types[$i]
    $domLabel  = "({0})" -f $Domains[$i]
    $target   = Join-Path $WorkspaceRoot $name

    if (Test-Path (Join-Path $target '.git')) {
        Write-Host "- SKIP   $name  $typeLabel $domLabel"
        $skipped++

        if ($GitName  -ne "") { git -C $target config user.name  $GitName  2>$null }
        if ($GitEmail -ne "") { git -C $target config user.email $GitEmail 2>$null }
    }
    else {
        Write-Host "CLONE  $name  $typeLabel $domLabel"
        $cloneArgs = @('clone', '--branch', $branch)
        if (-not $Full) { $cloneArgs += '--depth', '1' }
        $cloneArgs += $url, $target

        & git @cloneArgs
        if ($LASTEXITCODE -eq 0) {
            if ($GitName  -ne "") { git -C $target config user.name  $GitName }
            if ($GitEmail -ne "") { git -C $target config user.email $GitEmail }
            $cloned++
        }
        else {
            Write-Warning "Clone failed for ${name}"
            $failed++
        }
    }
}

Write-Host ("-" * 60)
Write-Host "Done — cloned: $cloned, skipped: $skipped, failed: $failed"
if ($failed -gt 0) { exit 1 }
