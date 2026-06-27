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

## Top-level entry points

| Command | Purpose |
|---|---|
| `/test-lab [<course>/<slug>]` | Test a single lab interactively |
| `/test-course [<course>]` | Test all interactive labs in a course sequentially |

## Run lifecycle

### Phase 1 — Pre-flight

1. **Resolve lab content.** Clone or pull `microsoft/agent-academy` to get the latest lab
   markdown. Parse the target lab's `index.md` into a step tree.

2. **Verify Playwright MCP is available.** Confirm the `playwright` MCP server is accessible
   (it's bundled via `.github/mcp.json`).

### Phase 2 — Browser Authentication (Manual)

This is the key difference from the original plugin: **no automated credential entry**.

1. **Open browser.** Use `browser_navigate` to go to `https://copilotstudio.microsoft.com/`.
   This will trigger the M365 login flow.

2. **Prompt the user.** Tell the user:
   ```
   🔐 Please sign in to your M365 account in the browser window that just opened.
   Take your time — I'll wait up to 5 minutes for you to complete authentication.
   Let me know when you're signed in, or I'll detect it automatically.
   ```

3. **Wait for authentication.** Poll with `browser_snapshot` every 10 seconds, checking
   whether the page has left the `login.microsoftonline.com` domain and reached the
   Copilot Studio home page. Indicators of success:
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
