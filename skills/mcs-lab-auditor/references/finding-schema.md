# Finding record schema

Each item in a lab's `findings.json` follows this shape. Findings are emitted by the per-step judge (and by parser warnings — see `lab-parser-spec.md` §Validation).

## Schema

```yaml
finding_id: f-{0-padded 4-digit sequence within the run}        # e.g., f-0007
lab_slug: <string>
run_id: <string>
step_id: <string>                # parser step id, e.g. "usecase-2.scene-3.step-4"
scene_heading: <string>
instruction_excerpt: <string>    # verbatim raw_markdown of the step, or a relevant slice

outcome: <enum>                  # see Outcomes table below
severity: <enum>                 # high | medium | low
confidence: <float 0..1>         # judge's self-rated confidence in the outcome

expected: <string>               # one-sentence description of what the lab said would happen
actual: <string>                 # one-sentence description of what the browser actually showed

evidence:
  screenshot: <relative path>    # screenshots/{step-id}.png
  snapshot_after: <relative path>
  console_errors: [<string>]     # captured from _browser_console_messages
  failed_network: [<string>]     # captured from _browser_network_requests (filtered to 4xx/5xx)
  observed_text_snippet: <string?>   # any visible text the judge thinks is relevant

suggested_correction:
  original_text: <string>        # exact substring from the lab's raw_markdown
  proposed_text: <string>        # what the judge thinks the lab SHOULD say
  rationale: <string>            # 1-2 sentence explanation
  scope: <enum>                  # "phrase" | "step" | "scene"

flags:
  non_deterministic: <bool>
  parser_warning: <bool>         # true for findings emitted by the parser, not the judge
  cross_lab_drift: <bool>        # true for findings emitted by the cross-lab consistency fan-in (see cross-lab-consistency.md)
  critique_pass_survived: <bool> # set after critique judge pass; if false, finding is downgraded
```

Additional evidence fields exist for cross-lab drift findings:

```yaml
evidence:
  cross_lab_canonical_from: [<lab-slug>, ...]   # which sibling labs agree on the canonical form
  cross_lab_divergent_lines: [L<n>, L<n>, ...]   # line numbers in the divergent lab where the token appears
```

## Outcomes

| outcome | meaning | severity bias | issue inclusion |
|---|---|---|---|
| `pass` | UI matches the lab instruction within the kind's tolerance. Never produces a finding record. | n/a | n/a |
| `broken` | The element/label/path/URL in the lab doesn't exist or doesn't behave as described. | high or medium depending on user impact | included |
| `unclear` | Multiple plausible interpretations; lab is ambiguous about which element/click/value. | medium or low | included |
| `non_deterministic` | Step explicitly says output varies; observed result is in the right shape but differs. | low — typically just logged | excluded by default; included with `--force-issue` |
| `transient` | Network blip, missing wait, race condition. Retried before being recorded. Finding only emitted if retry also failed. | medium | excluded (treated as auth/network, not lab content) |
| `cannot_verify` | User's tenant lacks a license, the previous lab's setup wasn't done, or some other precondition prevented the step from running. | n/a (informational) | excluded — logged locally only |

## Severity rubric

- **`high`**: the step is a blocker — a user following the lab cannot complete this lab without a fix. Examples: button label renamed; navigation path no longer exists; required permission name changed; screenshot reference shows nonexistent UI.
- **`medium`**: the step works but the lab is misleading or out of date. Examples: feature moved to a new menu; recommended option renamed; description of expected behavior doesn't match what actually happens (but the click still succeeds).
- **`low`**: cosmetic — typos, outdated screenshots that still convey the right idea, minor wording. Examples: "analyticss" → "analytics"; "click the cog" → "click the gear" (both work).

Confidence and severity are independent: a low-confidence finding can still be high-severity if the judge is unsure but suspects a blocker. The `(low confidence — please verify)` marker in the issue body always reflects confidence, never severity.

## Suggested-correction scope

- `phrase`: replace a single phrase or word inside one numbered step (the most common).
- `step`: replace the entire `raw_markdown` of one step.
- `scene`: the whole scene needs rewriting (rare — usually only when the underlying UI has been redesigned).

## When NOT to emit a finding

The judge MUST NOT emit a finding when:

- The step is marked `narrative` and the judge has nothing to verify.
- The previous step's `cannot_verify` outcome means this step couldn't be reached (chain `cannot_verify`).
- The user's tenant explicitly lacks a license called out in `context.prerequisites` and the step requires that license.
- The lab's `non_deterministic` flag is set AND the observed UI is in the correct family (e.g., "an agent was created" — even if its generated description differs from the lab's screenshot).

## Parser-emitted findings

Parser warnings (validation failures, lab typos detected at parse time) use:

- `outcome: broken` for typos and broken cross-references.
- `severity: low` always.
- `flags.parser_warning: true`.
- `evidence` populated with line numbers (`line_number: 175`) instead of screenshots.

These still go into the per-lab issue, but are visually separated in the issue body under a "Static analysis" heading.

## Cross-lab drift findings

Cross-lab drift findings are emitted by the static-fan-in pass described in `cross-lab-consistency.md`. They use:

- `outcome: broken`
- `severity: low` always — divergent text is a polish issue, not a blocker.
- `confidence: 0.85` by default, `0.65` when the underlying shape match is borderline (similarity 0.85–0.90).
- `flags.parser_warning: true` AND `flags.cross_lab_drift: true`.
- `evidence.cross_lab_canonical_from` + `evidence.cross_lab_divergent_lines` populated; no screenshot.

Issue bodies render cross-lab drift findings under a dedicated "Cross-lab consistency" section, separate from the regular "Static analysis" section, so maintainers can see at a glance whether the issue is a per-lab drift fix or a true UI-versus-lab mismatch.
