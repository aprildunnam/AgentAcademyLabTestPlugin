[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $Path,
    [Parameter(Mandatory)] [string] $Fallback,
    [ValidateSet('Exists', 'Raw', 'JsonField', 'SizeBytes', 'BytesLabel', 'RecentDirs', 'GrepContext')]
    [string] $Mode = 'Raw',
    [string] $JsonField,
    [string] $YesText = 'yes',
    [int] $Count = 5,
    [string] $Pattern,
    [int] $ContextAfter = 15
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Path)) {
    Write-Output $Fallback
    return
}

switch ($Mode) {
    'Exists' {
        Write-Output $YesText
    }
    'Raw' {
        Write-Output (Get-Content -LiteralPath $Path -Raw)
    }
    'JsonField' {
        if (-not $JsonField) { throw "-JsonField is required when -Mode JsonField" }
        $obj = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
        Write-Output ($obj.$JsonField)
    }
    'SizeBytes' {
        $sz = (Get-Item -LiteralPath $Path).Length
        Write-Output "yes ($sz bytes)"
    }
    'BytesLabel' {
        $sz = (Get-Item -LiteralPath $Path).Length
        Write-Output "$sz bytes"
    }
    'RecentDirs' {
        Get-ChildItem -LiteralPath $Path -Directory |
            Select-Object -Last $Count -ExpandProperty Name
    }
    'GrepContext' {
        if (-not $Pattern) { throw "-Pattern is required when -Mode GrepContext" }
        $matches = Get-Content -LiteralPath $Path |
            Select-String -Pattern $Pattern -Context 0, $ContextAfter
        foreach ($m in $matches) {
            Write-Output ("> " + $m.Line)
            foreach ($post in $m.Context.PostContext) {
                Write-Output ("    " + $post)
            }
        }
    }
}
