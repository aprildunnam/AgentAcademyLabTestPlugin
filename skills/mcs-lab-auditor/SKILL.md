---
name: mcs-lab-auditor
description: |
  Audit Microsoft Copilot Studio bootcamp labs end-to-end. Drives Playwright through every numbered step of each lab in `C:\Users\dewainr\mcs-labs\_data\lab-config.yml` → `lab_orders.event.bootcamp`, compares the live UI to the written instructions with an LLM judge, and either files a GitHub issue (one per lab with findings) or appends a clean-pass entry to a local audit log. Use this skill when the user says "audit the bootcamp", "run the lab auditor", "test the mcs-labs labs", or invokes any `/audit-*` command from this plugin.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash(gh issue list:*)
  - Bash(gh auth status:*)
  - Bash(gh repo view:*)
  - PowerShell
  - AskUserQuestion
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_click
  - mcp__plugin_playwright_playwright__browser_type
  - mcp__plugin_playwright_playwright__browser_fill_form
  - mcp__plugin_playwright_playwright__browser_select_option
  - mcp__plugin_playwright_playwright__browser_press_key
  - mcp__plugin_playwright_playwright__browser_wait_for
  - mcp__plugin_playwright_playwright__browser_evaluate
  - mcp__plugin_playwright_playwright__browser_console_messages
  - mcp__plugin_playwright_playwright__browser_network_requests
  - mcp__plugin_playwright_playwright__browser_close
---

# mcs-lab-auditor (orchestration skill)

You are auditing Microsoft Copilot Studio bootcamp labs. You run a real browser through each lab's instructions, decide whether what you see matches what the lab says, and produce either a GitHub issue (when something's wrong) or a local log entry (when everything passes).

**Read-only on the mcs-labs repo.** You never branch, commit, push, or open a pull request. The only write path is `gh issue create` and `gh issue comment`.

This file is the orchestrator. It loads the reference files below as needed:

- `references/lab-parser-spec.md` — how to convert a lab's markdown into a step tree.
- `references/playwright-cookbook.md` — portal sign-in flow, scene-boundary auth probe, tool mapping per step kind, known quirks.
- `references/workshop-redemption.md` — exchange a workshop code for a test account; DPAPI encryption flow.
- `references/llm-judge-prompts.md` — the per-step judge, the second-pass critique, the action classifier.
- `references/finding-schema.md` — finding record fields, outcome and severity definitions.
- `references/audit-log-schema.md` — `audit-history.yml` entry shape.

Read whichever you need before doing the corresponding step. Don't try to keep all of them in your head at once.

## Top-level entry points (called from command files)

| Command | What this skill does |
|---|---|
| `/audit-bootcamp [--resume <id>] [--labs csv] [--no-issue]` | Audit every bootcamp lab. |
| `/audit-lab <slug> [--no-issue] [--dry-run]` | Audit a single lab. |
| `/audit-report [<run-id>]` | Summarize `audit-history.yml`. No browser activity. |
| `/audit-account [show\|redeem\|clear]` | Manage the cached test account. |

## Run lifecycle (for `/audit-bootcamp` and `/audit-lab`)

### Phase 1 — Pre-flight (no browser yet)

1. **Resolve the plugin directory**. It is `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor`. The mcs-labs repo is `C:\Users\dewainr\mcs-labs`. Both are fixed paths on this machine.

2. **Load configs**:
   - `config/workshop.yml`
   - `config/judge-config.yml`

3. **Check `gh` auth**:
   ```
   gh auth status
   gh repo view microsoft/mcs-labs --json viewerPermission
   ```
   If either fails, halt with a clear message before doing anything else.

4. **Enumerate the lab list**:
   - Read `C:\Users\dewainr\mcs-labs\_data\lab-config.yml`.
   - Take the ordered list at `lab_orders.event.bootcamp` (key `bootcamp_lab_orders`).
   - For `/audit-bootcamp`, use the whole list (or the `--labs csv` subset, intersected).
   - For `/audit-lab`, use exactly the one slug given.
   - For each slug, confirm `_labs/<slug>.md` exists. If not, record `status: skipped, reason: lab_file_missing` and continue with the next slug — never abort the whole run because one lab is missing.

5. **Run-start account prompt** (see Phase 1.5 below). On `--dry-run`, skip this — `--dry-run` only exercises the parser and writes `steps.json` per lab.

6. **Create the run directory**:
   ```
   $run_id = (Get-Date -Format "yyyy-MM-ddTHHmmZ") + "-" + (-join ((1..4) | % { '{0:x}' -f (Get-Random -Maximum 16) }))
   $run_dir = "runtime/runs/$run_id"
   ```
   Initialize `manifest.yml` with the planned lab list, all `status: pending`, and the run start timestamp.

### Phase 1.5 — Run-start account prompt

Before any Playwright activity:

1. Check `runtime/account/account.meta.json`. If it exists, read `user_id`, `tenant_hint`, `cached_at`, `expires_at`.
2. If a cached account exists, use `AskUserQuestion`:
   - Question: `Use the cached test account?`
   - Options:
     - `[Recommended] Use cached: <user_id>` — description: `Cached <relative-time> ago. Expires <expires_at or "unknown">.`
     - `Redeem a new workshop code` — description: `Discards the cached account and prompts for a fresh workshop code.`
3. If user picks "Redeem a new..." or no cache exists, follow `references/workshop-redemption.md` end-to-end. The redemption flow:
   - Prompts the user for the workshop code (use `AskUserQuestion` with a single free-text option labeled "Enter workshop code").
   - Opens the workshop portal, fills the code, scrapes the issued credentials.
   - Signs in to AAD, captures `storage-state.json`.
   - Encrypts the credential blob via DPAPI and writes `credential.enc` + `account.meta.json`.

After Phase 1.5, the orchestrator has a valid signed-in browser context and a usable `account_user_id`.

### Phase 2 — Per-lab loop

For each lab slug in the planned list (or one slug for `/audit-lab`):

1. **Mark the lab `running`** in `manifest.yml`.
2. **Parse the lab** (`references/lab-parser-spec.md`). Write the step tree to `runs/<run-id>/labs/<slug>/steps.json`.
   - On `--dry-run`, stop here for this lab.
3. **Execute each scene** in order:
   - **Scene-boundary auth probe** (`playwright-cookbook.md#scene-boundary-auth-probe`). If expired, halt; mark lab `error, reason: auth_expired`; tell user how to resume.
   - For each step in the scene:
     - Capture `_browser_snapshot()` and store it as `snapshot_before`.
     - Dispatch via the action map in `playwright-cookbook.md#tool-mapping`. The dispatch may itself contain a `_browser_snapshot` + targeted action.
     - Capture `_browser_snapshot()` post-action as `snapshot_after`.
     - Capture `_browser_take_screenshot({ filename: "screenshots/<step-id>.png" })`.
     - Capture `_browser_console_messages` and `_browser_network_requests` for the step duration.
     - Call the per-step judge (`llm-judge-prompts.md#a-per-step-judge`). On `transient`, retry once before recording the failure.
     - If the judge produced a finding, run it through the critique pass (if enabled) and apply downgrades.
     - Append the finding (if any) to `runs/<run-id>/labs/<slug>/findings.json`.
   - Write a checkpoint to `runs/<run-id>/checkpoint.yml` at scene end.
4. **End-of-lab disposition**:
   - If `findings.json` has any finding with `confidence >= judge-config.yml.confidence.min_to_include_in_issue` AND the lab is not in `non_deterministic_lab_slugs` (or `--force-issue` was passed): invoke `mcs-lab-issue-filer` (sub-skill).
   - Otherwise: append a clean entry to `runs/<run-id>/clean-labs.yml`.
   - Either way: append the per-lab summary entry to `runtime/audit-history.yml` (`references/audit-log-schema.md`).
   - Mark lab `done` (or `issue_filed`) in `manifest.yml`.
5. **Pause** for `judge-config.yml.execution.min_seconds_between_labs` before the next lab.

### Phase 3 — Wrap-up

1. Close the browser (`mcp__plugin_playwright_playwright__browser_close`).
2. Print a summary to the user: total labs, count by status, list of filed issue URLs, run-id for future `/audit-report` lookups.
3. Write `runs/<run-id>/manifest.yml` final state.

## Resume flow (`--resume <run-id>`)

When `--resume <run-id>` is passed:

1. Read `runs/<run-id>/manifest.yml`.
2. Determine which labs are `pending`, `running` (interrupted mid-run), or `error`.
3. For `done`/`issue_filed`/`skipped` labs: keep as-is.
4. For `running`: restart that lab from the last completed scene in `checkpoint.yml`. Findings already in `findings.json` are preserved; new findings append.
5. For `pending`: run as a fresh lab.
6. Skip Phase 1.5 if the cached account is still valid (check `expires_at`). Otherwise re-prompt.

## Important rules

- **Never modify the mcs-labs repo.** Only read its `_labs/` and `_data/` directories.
- **Never commit, push, branch, or PR.** Issues only.
- **Never run `copilot-studio-cleanup` or any agent-deletion command** as part of an audit run. Tenant hygiene is the user's responsibility (see [[feedback_no_cleanup_in_test_automation]]).
- **Never log secrets.** The credential blob is DPAPI-encrypted; passwords never appear in transcripts, audit history, issue bodies, or `manifest.yml`. The first 4 chars of the workshop code may appear as `workshop_code_hint`.
- **Halt loudly on auth_expired.** Don't try to silently re-auth mid-run — that's how data loss happens.
- **Trust the critique pass.** If critique downgrades a finding to `pass` or `cannot_verify`, drop it from the issue.

## What to do when stuck

- **Parser couldn't classify a step**: emit a `parser_warning` finding (severity: low) and continue. Don't halt the whole lab.
- **Playwright timeout on `_browser_wait_for`**: capture diagnostics, mark the step `transient`, retry once. If still failing, record as a finding with `outcome: broken, severity: high, confidence: 0.6`.
- **Judge call fails**: retry once with a JSON-only reminder. If still failing, log the step as `error` in the transcript but continue with the next step — don't halt the lab over one bad judge call.
- **Issue creation fails**: write a clear error to `runs/<run-id>/labs/<slug>/transcript.md`, set `status: error, reason: gh_unavailable`, keep the rendered `issue-body.md` for the user to file manually.

## What success looks like

After a full bootcamp run:
- `runtime/audit-history.yml` has 11 new entries (one per lab).
- `runtime/runs/<run-id>/` contains parsed steps, findings, screenshots, transcripts, and rendered issue bodies for every lab.
- 0–11 GitHub issues filed (typically 1–4 in practice; many labs pass cleanly).
- The user has a one-line summary in chat: `Audited 11 labs in <duration>. 7 pass, 3 filed issues, 1 error (auth expired in <slug>, resume with /audit-bootcamp --resume <run-id>).`
