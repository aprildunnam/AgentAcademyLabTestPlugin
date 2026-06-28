# Finding Schema

A finding is a single test result for one lab step.

## Fields

```yaml
finding:
  id: "unique-finding-id"
  lab:
    course: "recruit"
    slug: "04-creating-a-solution"
    title: "Creating a Solution"
  section: "4.1 Create a Solution publisher"
  step_index: 3
  step_instruction: "Select + New publisher"

  # Verdict from the LLM judge
  verdict: "pass|broken|unclear|non_deterministic|transient|cannot_verify"
  confidence: 0.85

  # Details
  expected: "A '+ New publisher' button should be visible in the New solution pane"
  observed: "The button is labeled 'New publisher' without the + prefix"
  reasoning: "Button text has changed but functionality is the same"

  # Correction (only for broken/unclear)
  suggested_correction: "Update step text from '+ New publisher' to 'New publisher'"

  # Evidence
  screenshot_before: "path/to/before.png"
  screenshot_after: "path/to/after.png"
  snapshot_before: "(accessibility tree excerpt)"
  snapshot_after: "(accessibility tree excerpt)"

  # Annotated screenshots (Phase 5 — populated when verdict triggers annotation)
  screenshot_actual: "runtime/screenshots/<course>-<slug>/step-<N>-actual.png"
  screenshot_annotated: "runtime/screenshots/<course>-<slug>/step-<N>-annotated.png"
  screenshot_replacement: "runtime/screenshots/<course>-<slug>/step-<N>-replacement.png"

  # Fix PR data (Phase 6 — populated when a fix PR is generated)
  fix_pr:
    original_markdown: "(the original step text from the lab)"
    corrected_markdown: "(the corrected step text)"
    original_screenshot_path: "docs/<course>/<slug>/assets/<filename>.png"
    replacement_screenshot_path: "docs/<course>/<slug>/assets/<filename>.png"

  # Metadata
  timestamp: "2026-06-27T17:00:00Z"
  critique_upheld: true|false|null
```

## Verdict definitions

| Verdict | Meaning | Action |
|---|---|---|
| `pass` | Step works as described | No action needed |
| `broken` | Step cannot be completed as written | Lab needs updating |
| `unclear` | Instruction is ambiguous | Lab needs clarification |
| `non_deterministic` | Output varies (LLM content) | Note only, not a bug |
| `transient` | Temporary failure | Retry or note environment issue |
| `cannot_verify` | No observable outcome | Skip verification |

## Severity (derived from verdict + confidence)

- **high**: `broken` with confidence ≥ 0.8
- **medium**: `broken` with confidence 0.6–0.8, or `unclear` with confidence ≥ 0.8
- **low**: everything else that's not a `pass`

## Reproduction status (for `/reproduce-issue`)

When running in reproduction mode, the overall result for the issue is classified as:

| Status | Meaning |
|---|---|
| `reproduced` | Confirmed — live UI matches what the reporter described |
| `partially_reproduced` | Some findings confirmed, others differ or work fine |
| `not_reproduced` | All tested steps work as documented — issue may be resolved |
| `different_issue` | Found a problem, but it's different from what was reported |
| `environment_dependent` | Issue may be specific to reporter's tenant/config |

Each finding in reproduction mode also includes:

```yaml
  # Reproduction context (only in /reproduce-issue mode)
  reproduction:
    issue_number: 42
    reporter_expected: "Button labeled 'Create agent' should appear"
    reporter_observed: "Button is missing from the toolbar"
    matches_report: true|false  # does the live UI match what the reporter described?
    scope: "targeted|full"      # was this a targeted step or full lab run?
```
