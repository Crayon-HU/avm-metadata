#Requires -Version 5.1
<#
.SYNOPSIS
    Merge selected domain YAML files into .config/modules.yaml.

.DESCRIPTION
    Reads .config/{domain}.yaml files, filters by domain and module type,
    and writes .config/modules.yaml.

.PARAMETER Domains
    Comma-separated domain slugs to include, or "all". If omitted, an
    interactive menu is shown.

.PARAMETER Types
    Comma-separated module types to include: res, ptn, utl, or "all".
    If omitted, an interactive menu is shown.

.EXAMPLE
    .\scripts\generate_modules.ps1 -Domains networking,compute -Types res,ptn
    .\scripts\generate_modules.ps1 -Domains all -Types all
#>

[CmdletBinding()]
param(
    [string]$Domains = "",
    [string]$Types = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = Split-Path -Parent $ScriptDir
$ConfigDir = Join-Path $WorkspaceRoot '.config'
$OutputFile = Join-Path $ConfigDir 'modules.yaml'

function Add-LinesFromModule {
    param(
        [System.Collections.Generic.List[string]]$Buffer,
        [string]$ModuleType,
        [string]$ModuleName,
        [System.Collections.Generic.List[string]]$SelectedTypes,
        [string]$Slug,
        [System.Collections.Generic.List[string]]$OutputLines
    )

    if ([string]::IsNullOrWhiteSpace($ModuleName) -or $Buffer.Count -eq 0) {
        return $false
    }
    if (-not ($SelectedTypes -contains $ModuleType)) {
        return $false
    }

    foreach ($item in $Buffer) {
        [void]$OutputLines.Add($item)
    }
    [void]$OutputLines.Add("")
    return $true
}

$DomainFiles = @(Get-ChildItem -Path $ConfigDir -Filter '*.yaml' |
    Where-Object { $_.Name -ne 'modules.yaml' -and $_.Name -ne 'workspaces.yaml' } |
    Sort-Object Name)

if ($DomainFiles.Count -eq 0) {
    Write-Error "No domain YAML files found in $ConfigDir"
    exit 1
}

$DomainSlugs = @($DomainFiles | ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_.Name) })
$SelectedSlugs = [System.Collections.Generic.List[string]]::new()

if ($Domains -ne "") {
    if ($Domains.Trim().ToLowerInvariant() -eq 'all') {
        foreach ($slug in $DomainSlugs) { [void]$SelectedSlugs.Add($slug) }
    }
    else {
        foreach ($requestedDomain in ($Domains -split ',')) {
            $requestedDomain = $requestedDomain.Trim()
            if ([string]::IsNullOrWhiteSpace($requestedDomain)) {
                Write-Error "Empty domain value in -Domains"
                exit 1
            }
            if ($DomainSlugs -contains $requestedDomain) {
                [void]$SelectedSlugs.Add($requestedDomain)
            }
            else {
                Write-Error "Unknown domain '$requestedDomain'"
                exit 1
            }
        }
    }
}
else {
    Write-Host ""
    Write-Host "AVM Module Generator"
    Write-Host ("=" * 60)
    Write-Host "Available domains:"
    Write-Host ""
    for ($i = 0; $i -lt $DomainSlugs.Count; $i++) {
        Write-Host ("  {0,2})  {1}" -f ($i + 1), $DomainSlugs[$i])
    }
    Write-Host ""
    Write-Host "Enter domain numbers separated by spaces, or type 'all'."
    $userInput = Read-Host "Selection"

    if ($userInput.Trim().ToLowerInvariant() -eq 'all') {
        foreach ($slug in $DomainSlugs) { [void]$SelectedSlugs.Add($slug) }
    }
    else {
        foreach ($token in ($userInput -split '\s+')) {
            if ([string]::IsNullOrWhiteSpace($token)) { continue }
            $number = 0
            if ([int]::TryParse($token, [ref]$number) -and $number -ge 1 -and $number -le $DomainSlugs.Count) {
                [void]$SelectedSlugs.Add($DomainSlugs[$number - 1])
            }
            else {
                Write-Warning "Invalid selection '$token' - skipping"
            }
        }
    }
}

if ($SelectedSlugs.Count -eq 0) {
    Write-Host "No domains selected. Nothing to do."
    exit 0
}

$AllTypes = @('res', 'ptn', 'utl')
$SelectedTypes = [System.Collections.Generic.List[string]]::new()

if ($Types -ne "") {
    if ($Types.Trim().ToLowerInvariant() -eq 'all') {
        foreach ($typeName in $AllTypes) { [void]$SelectedTypes.Add($typeName) }
    }
    else {
        foreach ($requestedType in ($Types -split ',')) {
            $requestedType = $requestedType.Trim()
            if ([string]::IsNullOrWhiteSpace($requestedType)) {
                Write-Error "Empty type value in -Types"
                exit 1
            }
            if ($AllTypes -contains $requestedType) {
                [void]$SelectedTypes.Add($requestedType)
            }
            else {
                Write-Error "Unknown type '$requestedType' - valid: res, ptn, utl"
                exit 1
            }
        }
    }
}
else {
    Write-Host ""
    Write-Host "Module types:"
    Write-Host ""
    for ($i = 0; $i -lt $AllTypes.Count; $i++) {
        Write-Host ("  {0,2})  {1}" -f ($i + 1), $AllTypes[$i])
    }
    Write-Host ""
    Write-Host "Enter type numbers separated by spaces, or press Enter / type 'all'."
    $typeInput = Read-Host "Type selection [all]"

    if ([string]::IsNullOrWhiteSpace($typeInput) -or $typeInput.Trim().ToLowerInvariant() -eq 'all') {
        foreach ($typeName in $AllTypes) { [void]$SelectedTypes.Add($typeName) }
    }
    else {
        foreach ($token in ($typeInput -split '\s+')) {
            if ([string]::IsNullOrWhiteSpace($token)) { continue }
            $number = 0
            if ([int]::TryParse($token, [ref]$number) -and $number -ge 1 -and $number -le $AllTypes.Count) {
                [void]$SelectedTypes.Add($AllTypes[$number - 1])
            }
            else {
                Write-Warning "Invalid type selection '$token' - skipping"
            }
        }
    }
}

if ($SelectedTypes.Count -eq 0) {
    Write-Host "No types selected. Nothing to do."
    exit 0
}

Write-Host ""
Write-Host "Selected domains: $($SelectedSlugs -join ', ')"
Write-Host "Selected types:   $($SelectedTypes -join ', ')"

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$lines = [System.Collections.Generic.List[string]]::new()
[void]$lines.Add("# AUTO-GENERATED - do not edit manually.")
[void]$lines.Add("# Re-run scripts/generate_modules.ps1 to update.")
[void]$lines.Add("# Generated: $timestamp")
[void]$lines.Add("# Domains:   $($SelectedSlugs -join ', ')")
[void]$lines.Add("# Types:     $($SelectedTypes -join ', ')")
[void]$lines.Add("#")
[void]$lines.Add("# Source files: .config/{domain}.yaml")
[void]$lines.Add("")
[void]$lines.Add("modules:")

$total = 0

foreach ($slug in $SelectedSlugs) {
    $domainFile = Join-Path $ConfigDir "$slug.yaml"
    if (-not (Test-Path $domainFile)) {
        Write-Warning "Domain file not found: $domainFile - skipping"
        continue
    }

    $inModule = $false
    $moduleCount = 0
    $moduleBuffer = [System.Collections.Generic.List[string]]::new()
    $moduleType = ""
    $moduleName = ""

    foreach ($rawLine in [System.IO.File]::ReadLines($domainFile)) {
        $line = $rawLine.TrimEnd()

        if ($line -match '^\s*#') { continue }

        if ($line -match '^(\s*)-\s+name:\s+(.+)') {
            if ($inModule) {
                if (Add-LinesFromModule $moduleBuffer $moduleType $moduleName $SelectedTypes $PreviousWorkspaces $slug $lines) {
                    $moduleCount++
                }
            }

            $inModule = $true
            $moduleBuffer = [System.Collections.Generic.List[string]]::new()
            $moduleType = ""
            $moduleName = $Matches[2].Trim()
            $indent = $Matches[1]
            [void]$moduleBuffer.Add($line)
            [void]$moduleBuffer.Add("${indent}  domain: $slug")
            continue
        }

        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        if ($inModule) {
            if ($line -match '^\s*type:\s+(.+)') {
                $moduleType = $Matches[1].Trim()
            }
            [void]$moduleBuffer.Add($line)
        }
    }

    if ($inModule) {
        if (Add-LinesFromModule $moduleBuffer $moduleType $moduleName $SelectedTypes $slug $lines) {
            $moduleCount++
        }
    }

    if ($moduleCount -gt 0) {
        [void]$lines.Add("  # (end of domain: $slug)")
        [void]$lines.Add("")
    }

    $total += $moduleCount
    Write-Host "  OK  $slug  ($moduleCount modules)"
}

$content = $lines -join "`n"
[System.IO.File]::WriteAllText($OutputFile, $content + "`n", [System.Text.UTF8Encoding]::new($false))

Write-Host ("-" * 60)
Write-Host "Done - $total modules written to $OutputFile"

Write-Host ""
Write-Host "Next step:"
Write-Host "  .\avm.ps1 clone"
Write-Host "  .\avm.ps1 clone -Domain networking"
