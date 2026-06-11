<#
.SYNOPSIS
    Resolve the active "lab instance" — the named bundle describing which lab
    repo (+ training portal + branch prefix) the plugin operates on.

.DESCRIPTION
    Merges the plugin-shipped config/lab-instances.yml with the user-owned
    %USERPROFILE%\.mcs-lab-auditor\lab-instances.yml (user wins per field),
    selects the active instance, resolves branch_prefix and the portal, and
    emits the resolved instance as JSON (default), a one-line status, or the
    name only.

    Active-instance resolution order:
      1. -Instance <name>
      2. $env:LAB_INSTANCE
      3. merged default_instance (user file overrides shipped)
      4. shipped default ('mcs-labs')

    Requires the 'powershell-yaml' module. Install once with:
      Install-Module powershell-yaml -Scope CurrentUser -Force

.PARAMETER Instance
    Explicit instance name. Highest priority.

.PARAMETER Mode
    Json (default) | Status | Name.

.PARAMETER UserConfigDir
    Directory holding the user-owned lab-instances.yml. Defaults to
    %USERPROFILE%\.mcs-lab-auditor. (Also a test seam.)

.OUTPUTS
    Json   : the resolved instance object on stdout.
    Status : one human-readable line.
    Name   : the active instance name only.
#>
[CmdletBinding()]
param(
    [string] $Instance,
    [ValidateSet('Json', 'Status', 'Name')]
    [string] $Mode = 'Json',
    [string] $UserConfigDir = (Join-Path $env:USERPROFILE '.mcs-lab-auditor')
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue)) {
    try { Import-Module powershell-yaml -ErrorAction Stop }
    catch {
        Write-Error ("The 'powershell-yaml' module is required to resolve lab instances. " +
            "Install it once with:  Install-Module powershell-yaml -Scope CurrentUser -Force")
        exit 5
    }
}

$pluginConfigDir = Join-Path (Split-Path -Parent $PSScriptRoot) 'config'

function Read-InstanceFile([string] $path, [string] $configDir) {
    # Returns @{ default = <name|null>; instances = @{ name -> hashtable } }.
    # A relative portal_file is resolved to an absolute path against THIS
    # file's config dir, so a user instance that inherits a shipped portal_file
    # still resolves after the merge.
    if (-not (Test-Path -LiteralPath $path)) {
        return @{ default = $null; instances = @{} }
    }
    try {
        $doc = ConvertFrom-Yaml (Get-Content -LiteralPath $path -Raw)
    } catch {
        Write-Error "Failed to parse lab-instances file '$path': $($_.Exception.Message)"
        exit 6
    }
    $instances = @{}
    if ($doc.instances) {
        foreach ($name in @($doc.instances.Keys)) {
            $inst = $doc.instances[$name]
            if ($inst.portal_file -and -not [System.IO.Path]::IsPathRooted($inst.portal_file)) {
                $inst.portal_file = (Join-Path $configDir $inst.portal_file)
            }
            $instances[$name] = $inst
        }
    }
    return @{ default = $doc.default_instance; instances = $instances }
}

$shipped = Read-InstanceFile (Join-Path $pluginConfigDir 'lab-instances.yml') $pluginConfigDir
$userPath = Join-Path $UserConfigDir 'lab-instances.yml'
$user = Read-InstanceFile $userPath $UserConfigDir

# Merge: start from shipped, overlay user per field.
$merged = @{}
foreach ($name in @($shipped.instances.Keys)) { $merged[$name] = $shipped.instances[$name].Clone() }
foreach ($name in @($user.instances.Keys)) {
    if ($merged.ContainsKey($name)) {
        $u = $user.instances[$name]
        foreach ($k in @($u.Keys)) { $merged[$name][$k] = $u[$k] }
        if ($u.ContainsKey('portal'))      { $merged[$name].Remove('portal_file') }
        if ($u.ContainsKey('portal_file')) { $merged[$name].Remove('portal') }
    } else {
        $merged[$name] = $user.instances[$name]
    }
}

if ($merged.Count -eq 0) {
    Write-Error "No lab instances defined in shipped or user config."
    exit 7
}

# Select active instance.
$active = $null; $source = $null
if     ($Instance)         { $active = $Instance;          $source = 'flag' }
elseif ($env:LAB_INSTANCE) { $active = $env:LAB_INSTANCE;  $source = 'env' }
elseif ($user.default)     { $active = $user.default;      $source = 'user-default' }
elseif ($shipped.default)  { $active = $shipped.default;   $source = 'shipped-default' }

if (-not $active -or -not $merged.ContainsKey($active)) {
    $avail = (@($merged.Keys) | Sort-Object) -join ', '
    Write-Error "Unknown lab instance '$active'. Available: $avail"
    exit 8
}

$inst = $merged[$active]

$marker = if ($inst.marker) { $inst.marker } else { '_data/lab-config.yml' }
$candidates = @()
if ($inst.path_candidates) {
    $candidates = @($inst.path_candidates | ForEach-Object { [Environment]::ExpandEnvironmentVariables([string]$_) })
}

# branch_prefix: instance value -> gh login -> unresolved (consumers error later).
$prefix = $inst.branch_prefix
$prefixSource = 'config'
if (-not $prefix) {
    $prefix = $null
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        try { $login = (gh api user --jq '.login' 2>$null); if ($login) { $prefix = "$login".Trim(); $prefixSource = 'gh-user' } } catch { }
    }
    if (-not $prefix) { $prefixSource = 'unresolved' }
}

# Per-instance managed clone path (two instances never share one working tree).
$managedClone = Join-Path $UserConfigDir $active

# Resolve portal: inline block wins, else load the referenced file.
$portal = $null
if ($inst.portal) {
    $portal = $inst.portal
} elseif ($inst.portal_file) {
    if (-not (Test-Path -LiteralPath $inst.portal_file)) {
        Write-Error "Instance '$active' references portal_file '$($inst.portal_file)' which does not exist."
        exit 9
    }
    $portal = ConvertFrom-Yaml (Get-Content -LiteralPath $inst.portal_file -Raw)
}

$result = [ordered]@{
    name                 = $active
    repo                 = $inst.repo
    clone_url            = $inst.clone_url
    marker               = $marker
    branch_prefix        = $prefix
    branch_prefix_source = $prefixSource
    path_candidates      = $candidates
    managed_clone        = $managedClone
    portal               = $portal
    source               = $source
}

switch ($Mode) {
    'Name'   { Write-Output $active }
    'Status' {
        $pk = if ($portal.portal_kind) { $portal.portal_kind } else { 'n/a' }
        Write-Output ("lab-instance: $active [repo=$($inst.repo) prefix=$prefix portal=$pk] (via $source)")
    }
    'Json'   { Write-Output ($result | ConvertTo-Json -Depth 10) }
}
