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

    Once resolved, it PINS the working tree to origin/main (unless -NoPull) so
    screenshots and step text are always compared against the latest labs -
    even if the clone was left on a stale feature branch. A dirty tree is never
    clobbered; it is surfaced loudly so the orchestrator halts (issue #41).

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
    [string] $Instance,
    [string] $RepoUrl,
    [switch] $NoPull,
    [switch] $NoClone
)

$ErrorActionPreference = 'Stop'

# Resolve the active lab instance — the source of truth for clone URL, marker,
# candidate paths, and the managed-clone directory. Falls back to mcs-labs.
$resolveInstance = Join-Path $PSScriptRoot 'Resolve-LabInstance.ps1'
$inst = $null
if (Test-Path -LiteralPath $resolveInstance) {
    try {
        $instJson = & $resolveInstance -Instance $Instance -Mode Json 2>$null
        if ($LASTEXITCODE -eq 0 -and $instJson) { $inst = ($instJson | ConvertFrom-Json) }
    } catch { $inst = $null }
}
if (-not $RepoUrl)  { $RepoUrl  = if ($inst) { $inst.clone_url } else { 'https://github.com/microsoft/mcs-labs.git' } }
$markerRel          = if ($inst) { $inst.marker } else { '_data/lab-config.yml' }
$instCandidates     = if ($inst -and $inst.path_candidates) { @($inst.path_candidates) } else { @() }
$instManagedClone   = if ($inst) { $inst.managed_clone } else { $null }
$marker = ($markerRel -replace '/', [System.IO.Path]::DirectorySeparatorChar)

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
$managedClone = if ($instManagedClone) { $instManagedClone } else { Join-Path $env:USERPROFILE '.mcs-lab-auditor\mcs-labs' }

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
$ordered += $instCandidates
# The judge-config candidates and built-in list are mcs-labs-specific; only
# search them for the default mcs-labs instance (or when instance resolution
# failed). For a custom instance, searching them risks resolving to an unrelated
# mcs-labs clone that happens to share the default marker (split-brain).
if (-not $inst -or $inst.name -eq 'mcs-labs') {
    $ordered += (Get-ConfigCandidates)
    $ordered += $builtins
}

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
# An audit MUST compare the live product against the CURRENT labs on
# origin/main — never whatever branch happens to be checked out in the
# operator's clone. The previous logic only fast-forwarded when HEAD was
# already 'main' and otherwise *skipped the pull entirely*, so a clone left on
# a stale (even merged) feature branch silently audited outdated lab text
# (issue #41). We now actively PIN the working tree to origin/main.
if (-not $NoPull -and (Get-Command git -ErrorAction SilentlyContinue)) {
    try {
        git -C $resolved fetch --quiet origin 2>&1 | Out-Null
        $originMain = (git -C $resolved rev-parse --verify --quiet origin/main 2>$null)
        $dirty = [bool] (git -C $resolved status --porcelain 2>$null)
        if (-not $originMain) {
            $status = 'pull-skipped (no origin/main)'
        }
        elseif ($dirty) {
            # Never clobber uncommitted work. Surface loudly so the orchestrator
            # halts (its Phase 1 HEAD==origin/main assertion) instead of
            # auditing the wrong content.
            $branch = (git -C $resolved rev-parse --abbrev-ref HEAD 2>$null)
            $status = "DIRTY: left on '$branch' (NOT pinned to origin/main) - commit or stash and re-run"
        }
        else {
            # Clean tree: reset local main to origin/main and check it out so the
            # operator is left on a normal main branch. If that fails (e.g. main
            # protected/diverged), detach exactly onto origin/main as a fallback.
            git -C $resolved switch -C main --track origin/main 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) {
                git -C $resolved checkout --detach origin/main 2>&1 | Out-Null
            }
            $head = (git -C $resolved rev-parse HEAD 2>$null)
            if ($head -eq $originMain) {
                $status = "pinned to origin/main @ $($originMain.Substring(0, 7))"
            } else {
                $status = 'pull-failed (HEAD != origin/main)'
            }
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
