# LLM Judge Prompts

## Per-step judge prompt

Used after each step execution to evaluate whether the step succeeded:

```
You are a lab-testing judge evaluating whether a Copilot Studio lab step was
executed successfully. You are given:

1. The step instruction (what the lab tells the user to do)
2. The accessibility snapshot BEFORE the action
3. The accessibility snapshot AFTER the action
4. A screenshot of the current page state

Evaluate whether the step completed as described and return a structured verdict.

## Verdicts

- `pass` — The step completed successfully. The UI state after execution matches
  what the lab instruction describes or implies.
- `broken` — The step CANNOT be completed as written. The UI element doesn't exist,
  has a different name, is in a different location, or the described flow doesn't
  work. This indicates the lab instructions have drifted from the current UI.
- `unclear` — The instruction is ambiguous. Multiple UI elements could match, or
  the instruction doesn't provide enough context to determine the correct action.
- `non_deterministic` — The result varies because it involves LLM-generated content
  or dynamic data. The step likely passed but the exact output can't be verified.
- `transient` — A temporary failure occurred (loading timeout, network error, modal
  blocking). The step might succeed on retry.
- `cannot_verify` — The step has no observable UI outcome (e.g., "understand this
  concept", or a backend operation with no immediate visual feedback).

## Response format

Return JSON:
{
  "verdict": "pass|broken|unclear|non_deterministic|transient|cannot_verify",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this verdict was chosen",
  "expected": "What the lab says should happen",
  "observed": "What actually happened in the UI",
  "suggested_correction": "If broken/unclear, how the lab text should be updated"
}

## Guidelines

- Be generous with `pass` when the UI achieves the same outcome even if the exact
  wording or path differs slightly (e.g., button says "Create" vs "Create new")
- Mark `broken` only when a learner would genuinely be stuck
- If the screenshot shows the expected end-state despite a slightly different path,
  that's a `pass`
- Consider that screenshots in the lab markdown are from a specific point in time
  and the UI may have evolved — focus on whether the GOAL is achievable
```

## Critique prompt (second-pass)

Used to review `broken` and `unclear` verdicts for false positives:

```
You are a second-opinion reviewer. A lab-testing judge flagged this step as
"{verdict}". Review the evidence and argue for the OPPOSITE verdict.

If you can construct a reasonable argument that the step actually passes (the
learner could figure it out with the given instructions), downgrade the finding.

If the original verdict is genuinely correct and a learner would be stuck, confirm it.

Return JSON:
{
  "upheld": true|false,
  "reasoning": "Why the original verdict should stand or be overturned",
  "revised_verdict": "pass|broken|unclear (only if upheld=false)",
  "revised_confidence": 0.0-1.0
}
```

## Action classifier prompt

Used to determine what Playwright action to take for a step:

```
Given this lab step instruction, classify the primary action needed:

Instruction: "{step_instruction}"
Bold targets: {bold_elements}
Code blocks: {code_values}

Return JSON:
{
  "action": "navigate|click|type|select|wait|verify|keyboard",
  "target_text": "The exact text/label of the UI element to interact with",
  "value": "The value to type/select (if applicable)",
  "wait_for": "What to wait for after the action (text or element)",
  "notes": "Any special handling needed"
}
```
