<#
.SYNOPSIS
    Resolve the local mcs-labs repository, cloning it if missing and pulling
    the latest main so the audit always runs against current lab content.

.DESCRIPTION
    The mcs-labs repo location is NOT hard-coded. This script finds it in a
    portable way so the plugin works on any contributor's machine:

      1. Explicit override: -RepoRoot, then $env:MCS_LABS_REPO.
      2. Caller-supplied -Candidate paths (e.g. from
         judge-config.yml.build.registration.mcs_labs_repo_path_candidates).
      3. A built-in candidate list under the user profile.
      4. If none contain _data/lab-config.yml, clone microsoft/mcs-labs into the
         managed cache ($env:USERPROFILE\.mcs-lab-auditor\mcs-labs).

    Once resolved, it fast-forwards the repo to origin/main (unless -NoPull),
    so screenshots and step text are always compared against the latest labs.

.PARAMETER Mode
    Path   - emit ONLY the resolved absolute repo root (default; for capture).
    Status - emit a human-readable one-line summary for command pre-flight.

.PARAMETER RepoRoot
    Explicit repo root. Skips all discovery when it contains _data/lab-config.yml.

.PARAMETER Candidate
    Zero or more candidate repo roots tried (in order) before the built-ins.

.PARAMETER NoPull
    Skip the git fetch/fast-forward. Use for offline runs.

.PARAMETER NoClone
    Do not clone when the repo is missing; fail instead. Use in CI / read-only.

.OUTPUTS
    The resolved repo root (Mode Path) or a status string (Mode Status).
    Exits non-zero with a message on the error stream if the repo cannot be
    resolved and cloning is disabled or fails.
#>
[CmdletBinding()]
param(
    [ValidateSet('Path', 'Status')]
    [string] $Mode = 'Path',
    [string] $RepoRoot,
    [string[]] $Candidate = @(),
    [string] $RepoUrl = 'https://github.com/microsoft/mcs-labs.git',
    [switch] $NoPull,
    [switch] $NoClone
)

$ErrorActionPreference = 'Stop'
$marker = Join-Path '_data' 'lab-config.yml'

function Test-LabRepo([string] $root) {
    return $root -and (Test-Path -LiteralPath (Join-Path $root $marker))
}

# 1+2+3. Build the ordered candidate list: explicit > env > caller > built-ins.
$builtins = @(
    (Join-Path $env:USERPROFILE 'Projects\mcs-labs'),
    (Join-Path $env:USERPROFILE 'mcs-labs'),
    (Join-Path $env:USERPROFILE 'source\repos\mcs-labs'),
    (Join-Path $env:USERPROFILE '.mcs-lab-auditor\mcs-labs')
)
$managedClone = Join-Path $env:USERPROFILE '.mcs-lab-auditor\mcs-labs'

# Candidates recorded in config/judge-config.yml (kept in sync with docs).
function Get-ConfigCandidates {
    $cfg = Join-Path (Split-Path -Parent $PSScriptRoot) 'config\judge-config.yml'
    if (-not (Test-Path -LiteralPath $cfg)) { return @() }
    $lines = Get-Content -LiteralPath $cfg
    $out = @(); $inBlock = $false
    foreach ($line in $lines) {
        if ($line -match '^\s*mcs_labs_repo_path_candidates:\s*$') { $inBlock = $true; continue }
        if ($inBlock) {
            if ($line -match '^\s*-\s*["'']?(.+?)["'']?\s*$') { $out += ($Matches[1] -replace '\\\\', '\') }
            elseif ($line -match '^\s*\S') { break }   # dedented → end of the list
        }
    }
    return $out
}

$ordered = @()
if ($RepoRoot)         { $ordered += $RepoRoot }
if ($env:MCS_LABS_REPO){ $ordered += $env:MCS_LABS_REPO }
$ordered += $Candidate
$ordered += (Get-ConfigCandidates)
$ordered += $builtins

$resolved = $null
$status = ''
foreach ($c in $ordered) {
    if (Test-LabRepo $c) { $resolved = (Resolve-Path -LiteralPath $c).Path; break }
}

# 4. Clone if nothing resolved.
if (-not $resolved) {
    if ($NoClone) {
        Write-Error "mcs-labs repo not found in any candidate path and -NoClone was set. Tried: $($ordered -join '; ')"
        exit 2
    }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Error "mcs-labs repo not found and git is not installed; cannot clone $RepoUrl."
        exit 3
    }
    $parent = Split-Path -Parent $managedClone
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Write-Information "Cloning $RepoUrl into $managedClone ..." -InformationAction Continue
    git clone --depth 1 $RepoUrl $managedClone 2>&1 | Write-Information -InformationAction Continue
    if ($LASTEXITCODE -ne 0 -or -not (Test-LabRepo $managedClone)) {
        Write-Error "git clone of $RepoUrl failed."
        exit 4
    }
    $resolved = (Resolve-Path -LiteralPath $managedClone).Path
    $status = 'cloned'
}

# Always pull latest unless suppressed (best-effort; a stale local copy is
# better than a hard failure mid-run).
if (-not $NoPull -and (Get-Command git -ErrorAction SilentlyContinue)) {
    try {
        git -C $resolved fetch --quiet origin 2>&1 | Out-Null
        $branch = (git -C $resolved rev-parse --abbrev-ref HEAD 2>$null)
        if ($branch -eq 'main') {
            git -C $resolved merge --ff-only origin/main 2>&1 | Out-Null
            if ($LASTEXITCODE -eq 0) { if (-not $status) { $status = 'pulled' } }
            else { $status = 'pull-skipped (not fast-forwardable)' }
        } else {
            $status = "pull-skipped (on '$branch', not main)"
        }
    } catch {
        $status = 'pull-failed (using local copy)'
    }
} elseif (-not $status) {
    $status = 'found (pull skipped)'
}

if ($Mode -eq 'Status') {
    Write-Output ("mcs-labs: $resolved [$status]")
} else {
    Write-Output $resolved
}
