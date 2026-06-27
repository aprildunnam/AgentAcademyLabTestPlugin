---
description: Test all interactive labs in an Agent Academy course sequentially.
argument-hint: "[<course>] [--skip-conceptual] [--stop-on-failure] [--no-issue]"
---

# /test-course

You are testing all interactive labs in an Agent Academy course.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the course name (e.g., `recruit`, `operative`,
`special-ops`, `cowork-collective`). If omitted, present the user with a list of
available courses to choose from.

Flags:
- `--skip-conceptual` — skip labs marked as `interactive: false` (default behavior)
- `--stop-on-failure` — halt the run if any lab has a `broken` finding with high confidence
- `--no-issue` — run all tests but skip GitHub issue filing. Results are local only.

## Your task

Invoke the `agent-academy-tester` skill for every interactive lab in the course:

1. **Course resolution**: Validate the course exists in `config/agent-academy-config.yml`.
   If no course was provided, ask the user to pick one.

2. **Enumerate labs**: List all labs in the course, filtering to `interactive: true` only
   (unless overridden).

3. **Browser authentication**: Open the browser, navigate to Copilot Studio, and ask the
   user to sign in. Wait for authentication. This happens ONCE at the start — the session
   persists across all labs in the course.

4. **Sequential execution**: For each lab in order:
   a. Fetch and parse the lab's markdown
   b. Execute all steps via Playwright
   c. Judge each step
   d. Record findings
   e. If `--stop-on-failure` and a high-severity broken finding occurs, halt and report

5. **Course report**: After all labs complete, generate a summary report showing:
   - Per-lab pass/fail status
   - Total steps tested, passed, failed
   - List of broken steps across the course
   - Write to `runtime/test-results/course-<course>-<timestamp>.md`

6. **File GitHub issues**: For each lab with `broken` or `unclear` findings (confidence
   ≥ 0.7), file an issue at `microsoft/agent-academy` (or comment on an existing open
   issue). One issue per lab, deduped by `lab:<course>/<slug>` label. Skip if `--no-issue`.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for the per-lab procedure.

## Lab dependencies

Some labs build on prior labs (e.g., "Creating a Solution" creates assets used in later labs).
Labs are run in their numbered order. If an earlier lab fails critically, later dependent labs
may also fail — note this in the report as cascading failures vs independent issues.
