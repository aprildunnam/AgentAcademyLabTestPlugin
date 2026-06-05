<#
.SYNOPSIS
    Enumerate auditable scopes from the mcs-labs _events/ and _workshops/
    collections (the current source of truth), tagged by type.

.DESCRIPTION
    The repo split curated scopes into two Jekyll collections:
      _events/<id>.md    - formal, curated event experiences (e.g. bootcamp).
      _workshops/<id>.md  - less formal, on-demand workshops (e.g. agent-in-a-day).
    Both share one front-matter schema: title, description, event_id, order,
    and a `labs:` list of `{ slug, label }`. The optional richer agenda lives in
    _data/agendas/<event_id>.yml; the front-matter `labs:` is the reliable
    lab-list source and is what this script reads.

    The legacy _data/lab-config.yml `event_configs` table has drifted out of sync
    (it lacks the academy + agent-in-a-day workshops and still lists an obsolete
    mcs-in-a-day-v2), so collections are authoritative and this is the picker
    source.

.PARAMETER RepoRoot
    The mcs-labs repo root (resolve via Resolve-LabRepo.ps1 first).

.PARAMETER Json
    Emit the catalog as JSON (for the orchestrator). Default emits a table.

.OUTPUTS
    Table: "TYPE  id  (N labs)  title"  one per scope, events first.
    JSON : [{ type, id, title, description, order, labs:[slug,...] }]
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string] $RepoRoot,
    [switch] $Json
)

$ErrorActionPreference = 'Stop'

function Read-Scope([System.IO.FileInfo] $file, [string] $type) {
    $text = Get-Content -LiteralPath $file.FullName -Raw
    # Front matter is the first --- ... --- block.
    $fm = if ($text -match '(?s)^\s*---\s*(.*?)\s*---') { $Matches[1] } else { $text }

    $title = if ($fm -match '(?m)^\s*title:\s*["'']?(.+?)["'']?\s*$') { $Matches[1].Trim() } else { $file.BaseName }
    $desc  = if ($fm -match '(?m)^\s*description:\s*["'']?(.+?)["'']?\s*$') { $Matches[1].Trim() } else { '' }
    $id    = if ($fm -match '(?m)^\s*event_id:\s*["'']?(.+?)["'']?\s*$') { $Matches[1].Trim() } else { $file.BaseName }
    $order = if ($fm -match '(?m)^\s*order:\s*(\d+)') { [int]$Matches[1] } else { 999 }

    # External scopes (e.g. Agent Academy) host their labs in another repo, so
    # they are listed for awareness but cannot be audited end-to-end here.
    $external = ($fm -match '(?m)^\s*external:\s*true\b')
    $externalUrl = if ($fm -match '(?m)^\s*external_url:\s*["'']?(.+?)["'']?\s*$') { $Matches[1].Trim() } else { '' }
    $repository  = if ($fm -match '(?m)^\s*repository:\s*["'']?(.+?)["'']?\s*$') { $Matches[1].Trim() } else { '' }

    # labs: list -> capture each "- slug: <value>".
    $labs = @()
    foreach ($m in [regex]::Matches($fm, '(?m)^\s*-\s*slug:\s*["'']?([A-Za-z0-9._-]+)["'']?')) {
        $labs += $m.Groups[1].Value
    }

    [pscustomobject]@{
        type         = $type
        id           = $id
        title        = $title
        description  = $desc
        order        = $order
        external     = [bool]$external
        external_url = $externalUrl
        repository   = $repository
        auditable    = (-not $external) -and ($labs.Count -gt 0)
        labs         = $labs
    }
}

$catalog = @()
foreach ($pair in @(@{ dir = '_events'; type = 'event' }, @{ dir = '_workshops'; type = 'workshop' })) {
    $dir = Join-Path $RepoRoot $pair.dir
    if (-not (Test-Path -LiteralPath $dir)) { continue }
    foreach ($f in Get-ChildItem -LiteralPath $dir -Filter '*.md' -File) {
        $catalog += Read-Scope $f $pair.type
    }
}

# Events first, then workshops; each group ordered by `order` then id.
$catalog = $catalog | Sort-Object @{ E = { $_.type -ne 'event' } }, order, id

if ($Json) {
    $catalog | ConvertTo-Json -Depth 5
} else {
    foreach ($c in $catalog) {
        $tag = $c.type.ToUpper().PadRight(9)
        $note = if ($c.external) { "  [external -> $($c.repository)]" } elseif ($c.labs.Count -eq 0) { "  [no labs]" } else { '' }
        Write-Output ("{0}{1}  ({2} labs)  {3}{4}" -f $tag, $c.id.PadRight(28), $c.labs.Count, $c.title, $note)
    }
}
