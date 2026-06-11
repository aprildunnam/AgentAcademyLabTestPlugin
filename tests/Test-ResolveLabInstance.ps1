#Requires -Version 7
# Framework-free tests for scripts/Resolve-LabInstance.ps1.
# Exits 0 if every assertion passes, 1 otherwise. Run:
#   pwsh -NoProfile -File tests/Test-ResolveLabInstance.ps1
$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$resolver = Join-Path $repoRoot 'scripts/Resolve-LabInstance.ps1'
$fixtures = Join-Path $PSScriptRoot 'fixtures'
$fail = 0

function New-TempUserDir { $d = Join-Path $fixtures ([System.IO.Path]::GetRandomFileName()); New-Item -ItemType Directory -Force -Path $d | Out-Null; return $d }
function Invoke-Resolver([string[]] $extra) {
    $out = & pwsh -NoProfile -File $resolver @extra 2>$null
    return @{ out = ($out -join "`n"); code = $LASTEXITCODE }
}
function Assert([bool] $cond, [string] $name) {
    if ($cond) { Write-Host "PASS  $name" -ForegroundColor Green }
    else { Write-Host "FAIL  $name" -ForegroundColor Red; $script:fail++ }
}

# 1. No user file -> shipped mcs-labs default.
$u = New-TempUserDir
$r = Invoke-Resolver @('-Mode','Json','-UserConfigDir',$u)
$j = $r.out | ConvertFrom-Json
Assert ($r.code -eq 0) 'default: exit 0'
Assert ($j.name -eq 'mcs-labs') 'default: name is mcs-labs'
Assert ($j.repo -eq 'microsoft/mcs-labs') 'default: repo'
Assert ($j.branch_prefix -eq 'dewain') 'default: branch_prefix'
Assert ($j.marker -eq '_data/lab-config.yml') 'default: marker'
Assert ($j.portal.portal_kind -eq 'chatbot') 'default: portal loaded from workshop.yml'

# 2. User file adds an instance and sets default_instance.
$u = New-TempUserDir
@'
default_instance: contoso
instances:
  contoso:
    repo: "contoso/labs-fork"
    clone_url: "https://github.com/contoso/labs-fork.git"
    branch_prefix: "alice"
    portal:
      portal_kind: "skillable"
      workshop_portal_url: "https://labs.contoso.com/redeem"
'@ | Set-Content -LiteralPath (Join-Path $u 'lab-instances.yml')
$r = Invoke-Resolver @('-Mode','Json','-UserConfigDir',$u)
$j = $r.out | ConvertFrom-Json
Assert ($j.name -eq 'contoso') 'user-default: name'
Assert ($j.repo -eq 'contoso/labs-fork') 'user-default: repo'
Assert ($j.branch_prefix -eq 'alice') 'user-default: prefix'
Assert ($j.portal.workshop_portal_url -eq 'https://labs.contoso.com/redeem') 'user-default: inline portal'

# 3. Unknown instance -> non-zero exit.
$u = New-TempUserDir
$r = Invoke-Resolver @('-Mode','Json','-Instance','nope','-UserConfigDir',$u)
Assert ($r.code -ne 0) 'unknown: non-zero exit'

# 4. User overrides ONE field of a shipped instance (field-level merge).
$u = New-TempUserDir
@'
instances:
  mcs-labs:
    branch_prefix: "zzz"
'@ | Set-Content -LiteralPath (Join-Path $u 'lab-instances.yml')
$r = Invoke-Resolver @('-Mode','Json','-Instance','mcs-labs','-UserConfigDir',$u)
$j = $r.out | ConvertFrom-Json
Assert ($j.branch_prefix -eq 'zzz') 'merge: overridden field wins'
Assert ($j.repo -eq 'microsoft/mcs-labs') 'merge: un-overridden field kept'

# 5. $env:LAB_INSTANCE selects the instance when no flag is given.
$u = New-TempUserDir
@'
instances:
  contoso:
    repo: "contoso/labs-fork"
    clone_url: "https://github.com/contoso/labs-fork.git"
    branch_prefix: "alice"
    portal: { portal_kind: "email", workshop_portal_url: "https://x" }
'@ | Set-Content -LiteralPath (Join-Path $u 'lab-instances.yml')
$env:LAB_INSTANCE = 'contoso'
$r = Invoke-Resolver @('-Mode','Json','-UserConfigDir',$u)
$env:LAB_INSTANCE = $null
$j = $r.out | ConvertFrom-Json
Assert ($j.name -eq 'contoso') 'env: LAB_INSTANCE selects instance'

if (Test-Path $fixtures) { Remove-Item -Recurse -Force $fixtures }
if ($fail -gt 0) { Write-Host "`n$fail assertion(s) failed." -ForegroundColor Red; exit 1 }
Write-Host "`nAll assertions passed." -ForegroundColor Green
exit 0
