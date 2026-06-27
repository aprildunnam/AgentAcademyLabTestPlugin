---
description: Test a single Agent Academy lab end-to-end by walking through its steps in a live browser.
argument-hint: "[<course>/<slug>] [--dry-run] [--static-only]"
---

# /test-lab

You are testing a single Agent Academy lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab path in `<course>/<slug>` format (e.g.,
`recruit/04-creating-a-solution`). If omitted, present the user with a list of
available interactive labs to choose from.

Flags:
- `--dry-run` — parse the lab into a step tree only. No browser activity.
- `--static-only` — check markdown structure, links, and images only. No browser.

## Your task

Invoke the `agent-academy-tester` skill for the given lab:

1. **Lab resolution**: If a path was provided, validate it exists in the config's course
   catalog AND `docs/<course>/<slug>/index.md` exists in the agent-academy repo. If no
   path was provided, show the user a picker of all interactive labs grouped by course.

2. **Fetch lab content**: Clone or pull `microsoft/agent-academy` to get the latest
   markdown. Read the lab's `index.md`.

3. **Parse the lab**: Convert the markdown into a step tree per the lab-parser-spec.
   If `--dry-run`, output the step tree and stop.

4. **Browser authentication**: Open the browser and navigate to Copilot Studio. Ask the
   user to sign in to their M365 account. Wait for authentication to complete (detect
   the Copilot Studio home page). No automated credential entry — the user handles auth.

5. **Execute steps**: Walk through each step in the parsed step tree using Playwright.
   For each step: classify the action → execute → capture state → judge the result.

6. **Report**: Summarize results — how many steps passed, failed, were unclear, etc.
   Write a detailed report to `runtime/test-results/<course>-<slug>-<timestamp>.md`.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for the full procedure.
