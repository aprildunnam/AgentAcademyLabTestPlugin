# LLM judge prompt templates

The primary skill calls an LLM-judge after each executable step to compare the lab's written instruction to the observed browser state. This document holds the prompt templates. They are NOT loaded as system prompts — they are rendered inline by the skill into a structured Claude turn whose output is parsed as strict JSON.

## A. Per-step judge

### When invoked

After every executable step except those classified as `narrative` (which are never judged), and except `navigate` steps when `judge-config.yml.execution.skip_judge_on_pure_navigate` is true.

### Inputs to the judge

- `LAB_SLUG`, `LAB_TITLE`
- `STEP_ID`, `STEP_KIND`, `STEP_NON_DETERMINISTIC`
- `INSTRUCTION_MARKDOWN` — the verbatim raw_markdown of this step
- `SCENE_HEADING` — the h4 the step lives under
- `USE_CASE_TITLE` — the h3 use case
- `HINTS` — alert blocks attached to the step (verbatim)
- `SUB_BULLETS` — bullets nested under the step
- `EXPECTED_VISUAL_REFS` — image file references the lab includes near the step
- `CTX_VARS` — variables set by earlier steps in this lab (e.g., `{agent_name: "Sales Admin Assistant"}`)
- `SNAPSHOT_BEFORE` — accessibility-tree snapshot from `_browser_snapshot()` just before dispatching the step
- `SNAPSHOT_AFTER` — accessibility-tree snapshot taken just after the step
- `SCREENSHOT_AFTER` — image from `_browser_take_screenshot()` taken just after the step
- `CONSOLE_ERRORS` — captured from `_browser_console_messages` for the step duration
- `FAILED_NETWORK` — 4xx/5xx responses from `_browser_network_requests` for the step duration
- `PREREQUISITES` — `context.prerequisites` from the parsed lab
- `LAB_NON_DETERMINISTIC_FLAG` — whether this lab is in `non_deterministic_lab_slugs`

### Template

> **System:** You are auditing a Microsoft Copilot Studio bootcamp lab instruction against observed browser state. Output strict JSON. No prose outside the JSON object. If you are uncertain, lean toward `unclear` over `broken`, and toward lower confidence over higher. False positives are worse than false negatives — only call something `broken` when the UI clearly contradicts the instruction.
>
> **User:**
> ```
> LAB: {LAB_SLUG} — {LAB_TITLE}
> USE CASE: {USE_CASE_TITLE}
> SCENE: {SCENE_HEADING}
> STEP ID: {STEP_ID}   KIND: {STEP_KIND}   NON_DETERMINISTIC: {STEP_NON_DETERMINISTIC || LAB_NON_DETERMINISTIC_FLAG}
>
> INSTRUCTION (verbatim from the lab):
> """
> {INSTRUCTION_MARKDOWN}
> """
>
> HINTS attached to this step:
> {HINTS — each rendered as "[{kind}] {text}"}
>
> SUB-BULLETS nested under this step:
> {SUB_BULLETS — each as "- {text}"}
>
> EXPECTED VISUAL REFERENCES (lab screenshots): {EXPECTED_VISUAL_REFS}
>
> VARIABLES from earlier steps: {CTX_VARS as JSON}
>
> PREREQUISITES listed by the lab:
> {PREREQUISITES — each as "- {text}"}
>
> --- OBSERVED STATE ---
>
> ACCESSIBILITY SNAPSHOT BEFORE DISPATCH:
> {SNAPSHOT_BEFORE}
>
> ACCESSIBILITY SNAPSHOT AFTER DISPATCH:
> {SNAPSHOT_AFTER}
>
> CONSOLE ERRORS DURING STEP:
> {CONSOLE_ERRORS as bulleted list, or "(none)"}
>
> 4xx/5xx NETWORK RESPONSES DURING STEP:
> {FAILED_NETWORK as bulleted list, or "(none)"}
>
> --- RULES ---
>
> 1. `pass` when the post-state matches what the instruction said would happen. For NON_DETERMINISTIC steps, "match" means "the right kind of thing is visible" — exact wording/screenshots may differ.
> 2. `broken` when an element/label/path/URL named in the instruction doesn't exist or doesn't behave as described. Include `expected` (verbatim from the lab) and `actual` (what you see) in the output.
> 3. `unclear` when the instruction is ambiguous — multiple plausible interpretations, and there's no way to be sure which the lab author meant. Suggested correction should clarify, not guess at functionality.
> 4. `non_deterministic` ONLY when the instruction itself acknowledges variation ("may differ", "your output will look different") AND the observed state is in the correct family.
> 5. `transient` when console/network errors suggest a flake (timeout, 5xx, race). Will be retried; only the second failure is recorded.
> 6. `cannot_verify` when a prerequisite isn't met (license missing, prior lab not completed, environment not configured) and that's why the step didn't work. NOT a lab bug.
>
> Severity (only when outcome ∈ {broken, unclear}):
> - high: a user cannot complete this lab without a fix.
> - medium: the step succeeds but the lab is misleading or out of date.
> - low: cosmetic — typos, mildly outdated wording.
>
> Confidence: your self-rated reliability in this judgment, 0.0 to 1.0. If the observed state is partial (snapshot truncated, screenshot blurry), lower the confidence — don't fabricate certainty.
>
> --- OUTPUT (strict JSON) ---
>
> {
>   "outcome": "pass" | "broken" | "unclear" | "non_deterministic" | "transient" | "cannot_verify",
>   "severity": "high" | "medium" | "low" | null,    // null when outcome is pass/transient/cannot_verify
>   "confidence": <float 0..1>,
>   "expected": "<one sentence from the lab's POV>" | null,
>   "actual": "<one sentence describing what you saw>" | null,
>   "evidence_summary": "<2-3 sentence rationale tying instruction to observation>",
>   "suggested_correction": {
>     "original_text": "<verbatim substring of INSTRUCTION_MARKDOWN to replace>",
>     "proposed_text": "<replacement text>",
>     "rationale": "<1-2 sentence why>",
>     "scope": "phrase" | "step" | "scene"
>   } | null    // null when outcome is pass/transient/cannot_verify
> }
```

### Output handling

- Parse strict JSON; on parse failure, retry the call once with a stronger "JSON ONLY" reminder. If still failing, log `transient` and continue.
- Reject the response if `outcome ∈ {broken, unclear}` but `suggested_correction` is null — retry once.
- Reject if `original_text` is not a substring of `INSTRUCTION_MARKDOWN` (case-sensitive). The judge gets one retry to fix this; on second failure, downgrade to `unclear` with severity `low`.

## B. Critique judge (second pass)

Enabled by `judge-config.yml.critique.enabled`. Runs on every finding the per-step judge produced (excluding `transient` and `cannot_verify`).

### Inputs

The full per-step judge output PLUS the original per-step inputs.

### Template

> **System:** You are critiquing a previous judge's verdict on a lab instruction. Your job is to argue for the OPPOSITE verdict — find every reason the previous judge might have been wrong. If after honest critique the original verdict still stands, say so. If the critique reveals the original was over-eager, say what the correct verdict should be.
>
> **User:**
> ```
> ORIGINAL VERDICT:
> {previous judge's full JSON output}
>
> ORIGINAL INPUTS:
> {same inputs as the per-step judge}
>
> --- CRITIQUE TASK ---
>
> 1. Could the observed state actually be a correct interpretation of the lab instruction? Consider phrasings the original judge may have ignored.
> 2. Could this be `non_deterministic` instead of `broken` or `unclear`? Consider LLM-generated UI, varying tenant configuration, A/B tests.
> 3. Could a missing prerequisite explain the observed mismatch (making this `cannot_verify`, not a lab bug)?
> 4. Is the suggested_correction actually better than the original text, or just different?
>
> --- OUTPUT (strict JSON) ---
>
> {
>   "survives": true | false,
>   "revised_outcome": same enum as per-step judge,
>   "revised_severity": same enum,
>   "revised_confidence": <float 0..1>,
>   "critique_summary": "<2-3 sentences explaining what you found>"
> }
> ```

### Output handling

- If `survives == true`: keep the original finding; set `flags.critique_pass_survived = true`.
- If `survives == false` and `revised_outcome ∈ {pass, transient, cannot_verify}`: drop the finding entirely, log it locally with `flags.critique_pass_survived = false`.
- If `survives == false` and the critique downgraded severity but kept the outcome: use the revised severity and confidence, set `flags.critique_pass_survived = false`.

## C. Action classifier (fallback)

Used by the parser when the heuristic classifier (`lab-parser-spec.md` §4) returns confidence < 0.7. Lightweight prompt; cheap model OK.

### Template

> **System:** Classify a single lab instruction into one of: `navigate`, `click`, `type`, `select`, `wait`, `assert_visible`, `inspect`, `narrative`. Output strict JSON.
>
> **User:**
> ```
> STEP: """{INSTRUCTION_MARKDOWN}"""
> SCENE: {SCENE_HEADING}
>
> Definitions:
> - navigate: open a URL or move to a different page/section.
> - click: press a button, link, menu item.
> - type: enter text into a field.
> - select: choose from a dropdown or list.
> - wait: explicitly wait for something to appear.
> - assert_visible: confirm a thing is on screen, no other action.
> - inspect: read or observe content with no action ("review the metric").
> - narrative: commentary or context with no testable action.
>
> Output:
> {"kind": "<one of the above>", "confidence": <float 0..1>}
> ```

## Cost budgeting

The plan estimates ~50-80 steps × 11 labs × (per-step judge + screenshot capture) ≈ 600-900 Claude judge calls per full bootcamp run, plus ~100-200 critique calls (since not every step produces a finding, and critique only runs on findings). Use the project's main Claude model for the per-step judge; cheaper model (Haiku) is fine for the action classifier (template C). The critique judge should use the same model as the per-step judge for symmetry.
