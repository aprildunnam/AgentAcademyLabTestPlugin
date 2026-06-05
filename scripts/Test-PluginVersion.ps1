<#
.SYNOPSIS
    Check whether a newer mcs-lab-auditor plugin version is available before a
    run, so audits never execute on a stale local copy.

.DESCRIPTION
    Reads the local plugin version from <plugin>/.claude-plugin/plugin.json and
    compares it (semver) to the version published on origin/main of
    microsoft/BootcampLabTestPlugin (.claude-plugin/marketplace.json), fetched
    via `gh api`. Best-effort: if gh is unavailable or offline, it reports the
    check as skipped rather than blocking the run.

.PARAMETER PluginRoot
    The plugin root. Defaults to $env:CLAUDE_PLUGIN_ROOT, then this script's
    grandparent directory.

.OUTPUTS
    A one-line status string, e.g.:
      "plugin up-to-date (v0.6.0)"
      "UPDATE AVAILABLE: local v0.6.0 < published v0.7.0 - run /plugin to update mcs-lab-auditor"
      "version check skipped (gh unavailable)"
    Exit code 10 signals an update is available (callers may surface a warning).
#>
[CmdletBinding()]
param(
    [string] $PluginRoot,
    [string] $Repo = 'microsoft/BootcampLabTestPlugin'
)

$ErrorActionPreference = 'Stop'

if (-not $PluginRoot) { $PluginRoot = $env:CLAUDE_PLUGIN_ROOT }
if (-not $PluginRoot) { $PluginRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }

function Get-SemverParts([string] $v) {
    if (-not $v) { return $null }
    $clean = ($v -replace '^v', '') -split '[-+]' | Select-Object -First 1
    return @($clean -split '\.' | ForEach-Object { [int]($_ -replace '\D', '0') })
}

function Compare-Semver([string] $a, [string] $b) {
    # returns -1 if a<b, 0 if equal, 1 if a>b
    $pa = Get-SemverParts $a; $pb = Get-SemverParts $b
    for ($i = 0; $i -lt [Math]::Max($pa.Count, $pb.Count); $i++) {
        $x = if ($i -lt $pa.Count) { $pa[$i] } else { 0 }
        $y = if ($i -lt $pb.Count) { $pb[$i] } else { 0 }
        if ($x -lt $y) { return -1 }
        if ($x -gt $y) { return 1 }
    }
    return 0
}

# Local version.
$localManifest = Join-Path $PluginRoot '.claude-plugin\plugin.json'
if (-not (Test-Path -LiteralPath $localManifest)) {
    Write-Output "version check skipped (plugin.json not found under $PluginRoot)"
    return
}
$local = (Get-Content -LiteralPath $localManifest -Raw | ConvertFrom-Json).version

# Published version (best-effort via gh).
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Output "version check skipped (gh unavailable); local v$local"
    return
}
try {
    $raw = gh api -H "Accept: application/vnd.github.raw" "repos/$Repo/contents/.claude-plugin/marketplace.json" 2>$null
    if (-not $raw) { throw "empty response" }
    $published = ($raw | ConvertFrom-Json).plugins |
        Where-Object { $_.name -eq 'mcs-lab-auditor' } |
        Select-Object -First 1 -ExpandProperty version
    if (-not $published) { throw "version not found in published marketplace.json" }
} catch {
    Write-Output "version check skipped (could not reach $Repo); local v$local"
    return
}

$cmp = Compare-Semver $local $published
if ($cmp -lt 0) {
    Write-Output "UPDATE AVAILABLE: local v$local < published v$published - run /plugin to update mcs-lab-auditor before auditing"
    exit 10
} elseif ($cmp -gt 0) {
    Write-Output "plugin ahead of published (local v$local > published v$published) - dev build"
} else {
    Write-Output "plugin up-to-date (v$local)"
}
