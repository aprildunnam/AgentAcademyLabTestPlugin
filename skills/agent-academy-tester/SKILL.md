---
name: agent-academy-tester
description: |
  Test Agent Academy labs (https://microsoft.github.io/agent-academy/) end-to-end via Playwright.
  Opens a browser for manual M365 authentication, then walks through each lab's numbered steps
  in Copilot Studio and related portals, comparing the live UI to the written instructions with
  an LLM judge. Use this skill when the user says "test the agent academy labs", "run the recruit
  course", "test a lab", or invokes any /test-* command from this plugin.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash(gh:*)
  - Bash(gh issue create:*)
  - Bash(gh issue list:*)
  - Bash(gh issue comment:*)
  - Bash(gh issue view:*)
  - Bash(gh repo clone:*)
  - Bash(gh pr create:*)
  - Bash(git:*)
  - AskUserQuestion
  # Playwright MCP tools
  - mcp__playwright__browser_navigate
  - mcp__playwright__browser_snapshot
  - mcp__playwright__browser_take_screenshot
  - mcp__playwright__browser_click
  - mcp__playwright__browser_type
  - mcp__playwright__browser_fill_form
  - mcp__playwright__browser_select_option
  - mcp__playwright__browser_press_key
  - mcp__playwright__browser_wait_for
  - mcp__playwright__browser_evaluate
  - mcp__playwright__browser_console_messages
  - mcp__playwright__browser_network_requests
  - mcp__playwright__browser_close
---

# agent-academy-tester (orchestration skill)

You are testing Microsoft Copilot Studio Agent Academy labs end-to-end. You open a real browser,
let the user authenticate into their M365 account, then walk through each lab's instructions
step-by-step, comparing what you see in the live UI to what the lab says should happen.

This file is the orchestrator. It loads reference files as needed:

- `references/lab-parser-spec.md` — how to parse Agent Academy VitePress markdown into a step tree
- `references/playwright-cookbook.md` — portal navigation, tool mapping, known quirks
- `references/llm-judge-prompts.md` — per-step judge and critique prompts
- `references/finding-schema.md` — finding record structure and outcome definitions
- `references/screenshot-annotation-spec.md` — annotated screenshot generation and fix PR procedure
- `references/lab-screenshot-guide.md` — how to annotate screenshots in generated labs (red boxes around target elements)

## Top-level entry points

| Command | Purpose |
|---|---|
| `/test-lab [<course>/<slug>]` | Test a single lab interactively |
| `/test-course [<course>]` | Test all interactive labs in a course sequentially |
| `/reproduce-issue [<issue-number>]` | Reproduce a reported GitHub issue by re-running the relevant lab steps |
| `/rewrite-lab [<course>/<slug>]` | Rewrite a lab for a new UI experience — documents changes and generates updated markdown locally |
| `/create-lab [<course>]` | Create a brand-new lab from scratch — explores the feature live and generates complete lab markdown |
| `/export-solution [<course>/<slug>]` | Export a Power Platform starter solution .zip so learners can skip prerequisite labs |

## Run lifecycle

### Phase 1 — Pre-flight

1. **Resolve lab content.** Clone or pull `microsoft/agent-academy` to get the latest lab
   markdown. Parse the target lab's `index.md` into a step tree.

2. **Verify Playwright MCP is available.** Confirm the `playwright` MCP server is accessible
   (it's bundled via `.github/mcp.json`).

### Phase 2 — Browser Authentication (Manual)

This is the key difference from the original plugin: **no automated credential entry**.

1. **Resolve environment URL.** Check for `--env-url` flag first. If not provided, read
   `environment.default_url` from `config/agent-academy-config.yml`. This gives a
   full Copilot Studio URL with the target Power Platform environment embedded, e.g.
   `https://copilotstudio.microsoft.com/environments/<env-id>/home`.

2. **Open browser.** Use `browser_navigate` to go to the resolved environment URL.
   This will either land directly in the correct environment (if the Edge profile has
   an active session) or trigger the M365 login flow.

3. **Check if already authenticated.** Take a `browser_snapshot`. If the page shows
   the Copilot Studio home (agent list, environment name, etc.) — auth is already
   handled by the Edge profile. Skip to step 6.

4. **Prompt the user (if login page appeared).** Tell the user:
   ```
   🔐 Please sign in to your M365 account in the browser window that just opened.
   Take your time — I'll wait up to 5 minutes for you to complete authentication.
   Let me know when you're signed in, or I'll detect it automatically.
   ```

5. **Wait for authentication.** Poll with `browser_snapshot` every 10 seconds, checking
   whether the page has left the `login.microsoftonline.com` domain and reached the
   Copilot Studio environment. Indicators of success:
   - URL contains `copilotstudio.microsoft.com/environments`
   - Page contains environment picker or agent list
   - No login form visible

4. **Handle first-run modals.** If the "Welcome to Microsoft Copilot Studio" modal appears
   (country picker + "Get Started" button), dismiss it by selecting "United States" and
   clicking "Get Started".

5. **Confirm auth.** Take a snapshot and screenshot to confirm the authenticated state.
   Record which user is signed in for the test report.

### Phase 3 — Lab Execution

For each step in the parsed step tree:

1. **Read the step instruction.** The instruction tells the user what to do (click X,
   navigate to Y, type Z, etc.).

2. **Classify the action.** Map the instruction to a Playwright action:
   - `navigate` → `browser_navigate` (only for explicit URLs in the step)
   - `click` → `browser_snapshot` → find element → `browser_click`
   - `type` / `copy-paste` → `browser_type` or `browser_fill_form`
   - `select` → `browser_select_option` or `browser_click` (for custom dropdowns)
   - `wait` → `browser_wait_for`
   - `verify` → `browser_snapshot` + `browser_take_screenshot`

3. **Execute the action.** Perform it in the live browser.

4. **Capture state.** Take a `browser_snapshot` (accessibility tree) and
   `browser_take_screenshot` after each step.

5. **Judge the result.** Compare what the lab says should happen (expected) vs what
   actually happened (observed). Use the LLM judge prompt from
   `references/llm-judge-prompts.md`. Possible verdicts:
   - `pass` — step completed as described
   - `broken` — step cannot be completed as written (UI diverged)
   - `unclear` — instruction is ambiguous, multiple interpretations exist
   - `non_deterministic` — result varies (LLM-generated content)
   - `transient` — temporary failure, retryable
   - `cannot_verify` — step has no observable UI outcome to check

6. **Record the finding.** Store the verdict, confidence, screenshots, and any
   suggested correction.

### Phase 4 — Report & Issue Filing

After all steps are executed:

1. **Summarize results.** Count pass/broken/unclear/etc. per lab.
2. **Write local report.** Generate a markdown report with:
   - Lab title, course, date tested
   - Step-by-step results with screenshots for failures
   - Overall pass/fail status
   - Suggested corrections for broken steps
3. **File GitHub issue (if findings exist).** When the lab has at least one `broken`
   or `unclear` finding with confidence ≥ 0.7:
   a. **Deduplicate**: Check `gh issue list --repo microsoft/agent-academy --label lab-test`
      for an existing open issue for this lab (match by `lab:<course>/<slug>` label).
   b. **If no open issue exists**: File a new issue with:
      - Title: `[Lab Test] <course>/<slug>: <1-line summary of findings>`
      - Labels: `lab-test`, `automated`, `lab:<course>/<slug>`
      - Body: structured report with step-by-step findings, expected vs observed,
        suggested corrections, screenshot references, and test metadata
      - Command: `gh issue create --repo microsoft/agent-academy --title "..." --body "..." --label lab-test,automated,"lab:<course>/<slug>"`
   c. **If an open issue already exists**: Add a comment with the new findings
      (fingerprint-deduped — skip findings already reported in the issue body or
      prior comments).
      - Command: `gh issue comment <number> --repo microsoft/agent-academy --body "..."`
   d. If `--no-issue` flag was passed, skip issue filing and only write the local report.
4. **Present to user.** Display the summary, local report path, and issue URL (if filed).

### Phase 5 — Annotated Screenshots

For each finding with verdict `broken` (confidence ≥ 0.7) or `unclear` (confidence ≥ 0.8):

1. **Capture the actual UI state.** Take a clean `browser_take_screenshot` showing what the
   learner would see today. Save as `step-<N>-actual.png`.

2. **Generate an annotated screenshot.** Use `browser_evaluate` to inject a temporary
   overlay onto the page with:
   - A **red callout box** in the corner showing: step number, verdict, expected vs observed
   - A **red rectangle** around the UI element that's wrong (renamed, missing, moved)
   - For renamed elements: label showing `"Lab says: {old} → Now: {new}"`
   - For missing elements: red dashed box where the element should be

3. **Take the annotated screenshot** with `browser_take_screenshot`. Save as
   `step-<N>-annotated.png`.

4. **Remove the overlay** with `browser_evaluate` to restore the clean page state.

5. **Capture a replacement screenshot.** If the lab's screenshot for this step is outdated,
   take a clean screenshot of the current UI in the same viewport/state as the lab's
   original. Save as `step-<N>-replacement.png`. This becomes the new screenshot in the
   fix PR.

See `references/screenshot-annotation-spec.md` for full annotation styles and file naming.

### Phase 6 — Fix PR Generation

When at least one finding has verdict `broken` (confidence ≥ 0.7) with a
`suggested_correction`, and `--no-pr` was NOT passed:

1. **Clone `microsoft/agent-academy`** (shallow, depth 1).

2. **Create a fix branch**: `fix/<course>-<slug>-lab-test-<run_id>`.

3. **Apply text corrections** to `docs/<course>/<slug>/index.md`:
   - For each finding with `suggested_correction`, find the original step text
     and replace it with the corrected version.
   - Preserve markdown formatting (indentation, bold, code blocks).

4. **Replace outdated screenshots**: Copy each `step-<N>-replacement.png` into
   `docs/<course>/<slug>/assets/`, using the same filename as the original
   screenshot referenced in the lab markdown.

5. **Commit and push** with a descriptive message listing each corrected step.

6. **Open a PR** via `gh pr create --repo microsoft/agent-academy` with:
   - Title: `fix(<course>/<slug>): update lab steps to match current UI`
   - Body: structured report with before/after for each finding, annotated
     screenshots, diff of text changes, and `Fixes #<issue>` if an issue exists
   - Labels: `lab-test`, `automated`

7. **Link the issue**: If a GitHub issue was filed (or already open) for this lab,
   add a comment on the issue linking to the new PR.

See `references/screenshot-annotation-spec.md` for the full PR body template and
error handling (fork fallback, permission errors, etc.).

### Phase 7 — Issue Reproduction (for `/reproduce-issue`)

When invoked via `/reproduce-issue <number>`, the lifecycle changes:

1. **Fetch the issue.** Use `gh issue view <number> --repo microsoft/agent-academy`
   to retrieve the title, body, labels, and comments.

2. **Extract the lab and step references.**
   - Look for a `lab:<course>/<slug>` label (auto-filed issues always have one)
   - Parse the body for lab paths (`recruit/06-...`) and step numbers (`Step 5`)
   - If ambiguous, ask the user which lab the issue relates to

3. **Determine scope.** Two modes:
   - **Targeted**: issue references specific steps → run prerequisites in quick mode
     (execute without deep judging), then run the reported steps with full scrutiny,
     plus 2–3 subsequent steps for cascade effects
   - **Full**: issue is general → run the entire lab normally via Phase 3

4. **Execute with extra comparison.** During step judging, also compare the live UI
   against any screenshots the reporter attached to the issue. This catches cases
   where the lab text is correct but the UI has changed since the reporter filed.

5. **Classify the reproduction result:**

   | Status | Meaning |
   |---|---|
   | `reproduced` | Confirmed — live UI matches what the reporter described |
   | `partially_reproduced` | Some findings confirmed, others differ or work fine |
   | `not_reproduced` | All tested steps work as documented — issue may be resolved |
   | `different_issue` | Found a problem, but it's not the one reported |
   | `environment_dependent` | Issue may be specific to reporter's tenant/config |

6. **Write a reproduction report.** Save to
   `runtime/test-results/repro-<issue>-<timestamp>.md` with the reproduction
   status, step-by-step results, screenshots, and environment comparison.

7. **Post results to the issue** (unless `--no-comment`). Add a structured comment
   with the reproduction verdict, per-step results, and screenshots. See the
   comment template in `commands/reproduce-issue.md`.

8. **Auto-fix (optional).** If `--auto-fix` was passed and the issue was reproduced,
   proceed to Phases 5–6 to capture annotated screenshots and open a fix PR with
   `Fixes #<issue_number>` in the body.

### Phase 8 — Lab Rewrite (for `/rewrite-lab`)

When invoked via `/rewrite-lab`, the goal is to document UI differences and produce
a locally-stored rewritten lab. **No PRs are opened.** Output is for the user to
review, edit, and manually submit.

1. **Resolve environment URL.** The `--env-url` flag takes precedence. If not provided,
   warn the user that rewrite mode is designed for a specific new-experience environment
   and confirm they want to use the default.

2. **Walk through each original step.** For every step in the parsed step tree:
   a. Attempt the step as originally written in the new environment
   b. Classify the result: `unchanged`, `modified`, `new_flow`, `removed`, or `blocked`
   c. If the step doesn't work as written, discover the correct new path and execute it
   d. Capture TWO screenshots at every step:
      - Clean screenshot → `step-<N>.png` (backup)
      - Annotated screenshot with red box around the target element → `step-<N>-annotated.png`
      - The annotated version is what gets referenced in the generated `index.md`
      - See `references/lab-screenshot-guide.md` for the annotation procedure

3. **Handle blocked/removed steps carefully.** When a step is not possible:
   - Document WHY it's not possible (element removed? feature deprecated? behind a flag?)
   - Check if there's an alternative way to achieve the same learning objective
   - Flag it prominently — these need human review before publishing

4. **Generate two output files:**
   - `evaluation.md` — full step-by-step comparison, blockers section at top, summary stats
   - `index.md` — the rewritten lab markdown with updated instructions and screenshots

5. **All output is local.** Save to `runtime/rewrites/<course>-<slug>/`. No issue filing,
   no PR creation. The user reviews the output and decides what to do with it.

See `commands/rewrite-lab.md` for the full evaluation table structure and output format.

### Phase 9 — Lab Creation (for `/create-lab`)

When invoked via `/create-lab`, the plugin creates a net-new lab from scratch:

1. **Gather requirements.** Determine the course, topic, title, prerequisites, and
   difficulty level. Ask the user for anything not provided via flags.

2. **Explore the feature live.** Open the browser, authenticate, and walk through the
   feature described by the user. The goal is to discover the full click path, decision
   points, and potential pitfalls. At every meaningful step, capture TWO screenshots:
   - Clean version → `step-<N>.png` (backup)
   - Annotated version with red box around the target element → `step-<N>-annotated.png`
   - See `references/lab-screenshot-guide.md` for the annotation procedure

3. **Plan the lab structure.** Based on exploration:
   - Determine the next available mission number in the target course
   - Group steps into logical sections (2–5 sections)
   - Define 3–5 learning objectives
   - Identify prerequisites

4. **Write the lab markdown.** Generate a complete `index.md` in the Agent Academy
   VitePress format with:
   - Mission brief, objectives, prerequisites
   - Numbered steps with bold UI elements, screenshots, code blocks, and tips
   - One action per step — never combine multiple actions
   - Mission Complete summary with accomplishments and next steps

5. **Self-validate.** Run through the generated lab instructions in the same browser
   session to confirm every step works. Fix any issues found.

6. **Generate evaluation.** Write an `evaluation.md` with stats, validation results,
   and suggested placement (slug, path, mission number, dependencies).

7. **All output is local.** Save to `runtime/new-labs/<course>-<slug>/`. No PR, no issue.
   The user reviews and submits manually.

See `commands/create-lab.md` for the full VitePress template and writing style guidelines.

### Phase 10 — Solution Export (for `/export-solution` or `--export-solution`)

Produces a Power Platform solution .zip "starter pack" so learners can skip
prerequisite labs by importing the solution.

1. **Identify prerequisites.** Determine which prior labs produce artifacts needed
   for the target lab (agents, topics, flows, tables, etc.).

2. **Validate or create artifacts.** Either validate that artifacts already exist in
   the environment, or run prerequisite steps (with `--run-prereqs`) to create them.

3. **Ensure artifacts are in the correct solution.** Navigate to Solution Explorer,
   verify components are in the target solution. Add any missing components via
   "Add existing" → select → "Add".

4. **Run solution validation.** Use Solution Checker if available. Block export on
   critical errors; note warnings in the manifest.

5. **Publish and export.** Publish all customizations, then export as unmanaged,
   managed, or both. Save .zip files to the output directory.

6. **Generate manifest.** Write `manifest.md` with solution details, component list,
   import instructions, and post-import setup steps.

This phase can run standalone (via `/export-solution`) or as a final step of other
commands when `--export-solution` is passed.

See `commands/export-solution.md` for full details.

## Lab parsing rules

Agent Academy labs use VitePress markdown with this structure:

```markdown
# 🚨 Mission XX: Title

## 🎯 Mission Brief
(intro text)

## 🔎 Objectives
(learning goals)

## 🧪 Lab XX: Section Title
### Prerequisites
(required setup)

### X.Y Step Group Title
1. Step instruction with **bold UI elements** to click
   ![screenshot](./assets/image.png)
2. Next step...
   ```text
   Copy this text
   ```

## ✅ Mission Complete
```

Key parsing rules:
- **Interactive steps** are numbered items (`1.`, `2.`, etc.) under `### X.Y` headings
  that are inside a `## 🧪 Lab` section
- **Bold text** in steps usually indicates UI elements to interact with
- **Code blocks** marked with ` ```text ` are values to copy/paste into fields
- **Images** (`![...](./assets/...)`) show expected UI state — use for verification
- **Alert blocks** (`> [!TIP]`, `> [!NOTE]`, `> [!WARNING]`) are hints, not steps
- **Non-interactive sections** (before `## 🧪 Lab`) are conceptual — skip them
- Steps that say "select", "click", "navigate to" are interactive actions
- Steps that say "notice", "observe", "you'll see" are verification steps

## Auth session management

- The browser session persists across all steps within a lab run
- At each major section boundary, probe `https://copilotstudio.microsoft.com/` to verify
  auth hasn't expired
- If auth expires mid-run, prompt the user to re-authenticate (same manual flow)
- Never store or cache credentials — the user always authenticates manually

## Error handling

- If a step fails and the UI element can't be found, take a screenshot, record
  the finding as `broken`, and attempt the next step (unless it depends on this one)
- If the browser disconnects, prompt the user to check their connection
- If the auth probe fails, pause and ask the user to re-authenticate
- For steps marked with `> [!NOTE]` alternatives, try the primary path first,
  then the alternative if it fails
