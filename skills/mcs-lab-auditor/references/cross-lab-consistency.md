# Cross-lab consistency check (static fan-in)

When two or more labs share a verification or setup step — the same UI, the same Dataverse table, the same connector — their step text usually drifts apart over time. One lab gets corrected after a finding, the others don't. The result is a lab where the column name reads "Address 1: State/Province" (correct) and a sibling lab where the same column reads "Address1: State or Providence" (three errors stacked: missing space, wrong separator, "Providence" instead of "Province"). The learner who completes both labs in sequence hits the inconsistency and loses confidence in the material.

The cross-lab consistency check catches that drift at static-phase fan-in time, so the next single-lab audit can ship a fix without waiting for a learner to file a bug.

## When this check runs

After the per-lab static fan-out completes in Phase 1.7 step 1 (`SKILL.md`), and before Phase 2's interactive phase begins. It is **always on** for any run whose `scope_labs` contains 2 or more slugs (i.e. an event-wide audit, or any `--labs csv` subset with 2+ entries). For a single-lab `/audit-lab <slug>` run, the check still runs but in **read-mode against the full all-labs catalog** — see "Scope" below.

The check is purely static. No browser, no tenant state, no GitHub writes. It reads each lab's parsed step tree and the `scene-fingerprints.json` sidecar emitted by the per-lab static subagent.

## Inputs

For every lab in scope, the per-lab static subagent writes:

`runs/<run-id>/labs/<slug>/scene-fingerprints.json`

```json
{
  "lab_slug": "mcs-multi-agent",
  "scenes": [
    {
      "scene_id": "usecase-3.scene-1",
      "scene_heading": "Verify the agent picks up Account columns",
      "step_count": 6,
      "shape_hash": "f8c2…",
      "shape_text": "click|Tables|type|Account|click|Address|click|State",
      "identifier_tokens": [
        "Account",
        "Address 1: State/Province",
        "Address 1: Country/Region",
        "Account Data Lookup Agent"
      ],
      "raw_excerpts": {
        "Address 1: State/Province": ["L503", "L514"],
        "Account Data Lookup Agent": ["L487"]
      }
    },
    ...
  ]
}
```

Field meanings:

- `shape_hash` — SHA-256 (first 12 chars) of `shape_text`. Used to find scenes whose **action skeleton** is identical across labs.
- `shape_text` — pipe-joined sequence of `<step_kind>|<primary_target>` for each step in the scene, lowercased and trimmed. Primary target is the first noun-phrase the parser extracted as the step's target (e.g., a Tables nav item, a column name, a button label). This is the **shape**, not the literal text — two labs that say "navigate to Tables and pick the Account row" produce the same shape even if their prose differs.
- `identifier_tokens` — the noun-phrase identifiers the parser extracted from this scene: control labels, column names, table names, agent names, schema names. Lowercased only at compare time; stored with original casing so the finding can render the verbatim form.
- `raw_excerpts` — line numbers in the lab markdown where each identifier appears, so the finding can point to a precise location.

## Algorithm

### Step 1 — Group scenes by shape

Build a map from `shape_hash` → list of `(lab_slug, scene_id)`. Drop any group with size 1 (a scene unique to one lab is not subject to cross-lab drift). For each group with size 2+, we have a **shared scene cluster**.

### Step 2 — For each shared scene cluster, diff identifier tokens

Across the cluster's labs, compute the set of identifier tokens per lab. Then compute pairwise diffs.

For each pair `(lab_A, lab_B)` in the cluster:

1. Normalize tokens for comparison: lowercase, collapse internal whitespace to single space, strip leading/trailing punctuation.
2. For each normalized token in lab_A:
   - If the same normalized token appears verbatim in lab_B, mark it as **agreed**.
   - If a near-match (≥ 0.85 string similarity via `SequenceMatcher.ratio()`) exists in lab_B with **different surface form**, mark as **drift**.
   - If no match exists in lab_B, mark as **unique** (informational; probably the labs diverge by design).

A **drift pair** is what produces a finding. Examples:

| lab_A token | lab_B token | normalized match? | classification |
|---|---|---|---|
| `Address 1: State/Province` | `Address1: State or Providence` | similarity = 0.79 (no) | drift if both labs agree elsewhere; otherwise unique |
| `Address 1: State/Province` | `Address 1: State/Province` | exact | agreed |
| `Account Data Lookup Agent` | `Account Lookup Agent` | similarity = 0.92 | drift |
| `Account` | `Accounts` | similarity = 0.94 | drift (pluralization) |

### Step 3 — Determine the canonical form

For each drift cluster (the same logical identifier appearing in 2+ surface forms across the lab set), pick a canonical form using these rules in order:

1. **Most votes wins.** If 3 labs say "Address 1: State/Province" and 1 lab says "Address1: State or Providence", canonical = "Address 1: State/Province".
2. **Tie → the form that matches the live UI.** If a `lab_resources.yml` or recent audit `findings.json` documents the form observed in the live product, use that.
3. **Tie → the more recently edited lab wins.** Read `git log --format=%cI _labs/<slug>.md` and prefer the surface form from the lab with the most recent commit touching that line. This biases toward freshness.
4. **Tie → alphabetical.** Last-resort deterministic fallback.

### Step 4 — Emit findings

For each lab whose token diverges from the canonical form, emit a finding into that lab's `findings-static.json`:

```yaml
finding_id: f-<seq>
lab_slug: <divergent-lab-slug>
run_id: <run-id>
step_id: <scene_id of the shared cluster>
scene_heading: <the scene heading where the token appears>
instruction_excerpt: <line containing the divergent token, with line number from raw_excerpts>

outcome: broken
severity: low
confidence: 0.85

expected: |
  Other labs in this event use "<canonical-form>" for this identifier.
actual: |
  This lab uses "<divergent-form>".

evidence:
  cross_lab_canonical_from: [<lab-slug>, ...]   # which labs agree on the canonical form
  cross_lab_divergent_lines: [L503, L514]       # from raw_excerpts
  observed_text_snippet: "<the divergent line verbatim>"

suggested_correction:
  original_text: "<divergent-form>"
  proposed_text: "<canonical-form>"
  rationale: |
    Matches the canonical form used in <N> sibling lab(s):
    <comma-joined list of sibling slugs>. Avoids drift between
    labs that verify the same UI surface.
  scope: phrase

flags:
  parser_warning: true
  cross_lab_drift: true
  critique_pass_survived: true     # not subject to the per-step judge critique pass
```

Severity is **always `low`** for cross-lab drift findings — a learner can still complete the lab even with the divergent text, it's just a polish issue. Confidence is `0.85` by default; lower it to `0.65` when the shape match is borderline (similarity between 0.85 and 0.90) so the issue renders with the "low confidence — please verify" marker.

### Step 5 — Output

Write a single fan-in summary file `runs/<run-id>/cross-lab-consistency.json`:

```json
{
  "scope_labs": ["agent-builder-m365", "mcs-multi-agent", ...],
  "shared_scene_clusters": <N>,
  "drift_findings_emitted": <N>,
  "clusters": [
    {
      "shape_hash": "f8c2…",
      "scene_heading": "Verify the agent picks up Account columns",
      "labs": [
        { "slug": "mcs-orchestration", "form": "Address 1: State/Province", "lines": ["L194", "L205"], "verdict": "canonical" },
        { "slug": "mcs-multi-agent",   "form": "Address1: State or Providence", "lines": ["L503", "L514"], "verdict": "drift" }
      ],
      "canonical": "Address 1: State/Province",
      "votes": { "Address 1: State/Province": 2, "Address1: State or Providence": 1 }
    },
    ...
  ]
}
```

Append the per-lab drift findings into each affected lab's `findings-static.json` so the issue-filer and fix-PR-filer pick them up exactly like any other static finding.

## Scope

### Event-wide audit

When the run's `scope_labs` is the full lab list of an event, all clusters are computed within the event. Labs outside the event are ignored.

### `--labs csv` subset

When the run's `scope_labs` is a subset, clusters are computed within the subset. A subset of size 1 falls into the single-lab case below.

### Single-lab audit (`/audit-lab <slug>`)

When `scope_labs` has only one lab, the fan-in pass needs a comparison surface. It reads `scene-fingerprints.json` from the most recent prior run for each other lab in `lab_metadata.*.id` (the full all-labs catalog), if available under `runtime/runs/*/labs/<other-slug>/scene-fingerprints.json`. Labs that have never been audited contribute nothing.

This means cross-lab drift findings for single-lab runs are **discovery-limited** — they only surface when at least one prior run audited a sibling lab. Document this clearly in the issue body so the maintainer doesn't expect coverage that isn't there:

> _Cross-lab drift findings below were computed against `<N>` previously-audited sibling lab(s): `<list>`. Labs not in that list could not contribute._

### Skip conditions

The cross-lab pass is **skipped** when:

- `--dry-run` is set (no parse output to compare).
- The run is `--static-only` AND has only 1 lab in scope (no comparison surface and no prior runs on disk).
- `judge-config.yml.consistency.cross_lab_enabled: false` (config-level opt-out, default `true`).

When skipped, the orchestrator records `consistency.cross_lab_status: skipped, reason: <reason>` in the run manifest.

## Anti-patterns

- **Do not flag intentional divergence.** When a lab is teaching a different concept that happens to reuse the same control name, the shape hash will differ (different step sequence). The shape-hash gate is the primary defense against false positives.
- **Do not flag a token whose canonical form has no clear winner.** If the vote count is tied AND no canonical-form heuristic resolves the tie, drop the finding rather than picking arbitrarily. The drift exists, but flagging it creates more confusion than it resolves until a human decides the canonical form.
- **Do not emit a `cross_lab_drift` finding without `flags.cross_lab_drift: true`.** The fix-PR filer and the issue-filer rely on that flag to route the finding to a separate "Cross-lab consistency" section in the rendered output.
- **Do not auto-apply cross-lab drift corrections via the fix-PR filer when `proposed_text` is empty.** Always emit `original_text` AND `proposed_text` together; the fix-PR filer's literal string-replacement contract requires both.

## What this check does NOT do

- It does not compare prose. Two labs explaining the same concept in different words are fine — the check only fires on identifier tokens (control labels, column names, table names, agent names, schema names).
- It does not verify against the live UI. A token that diverges across labs but where ALL surface forms match the current product is still flagged as drift between the labs themselves; pick the form that matches the product as canonical (rule 2 in step 3).
- It does not block the run. A drift finding is severity `low` — informational. The interactive phase proceeds regardless.

## See also

- `lab-parser-spec.md` — the parser writes `scene-fingerprints.json` as part of every parse.
- `finding-schema.md` — `flags.cross_lab_drift` is registered there.
- The discovery that motivated this check: the `mcs-multi-agent` UC3 vs `mcs-orchestration` UC1 column-name divergence found during the 2026-05-26 audit cycle.
