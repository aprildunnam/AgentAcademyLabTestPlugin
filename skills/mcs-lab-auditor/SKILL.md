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

### Phase 1.5 — Run-start account prompt (MANDATORY)

Before any Playwright activity. **This prompt is required on every fresh run**
(only `--resume` with a still-valid cached `expires_at` skips it). An
implementing agent that silently reuses the cached account without asking is
violating the skill contract — the prompt is the moment the user gets to
choose "use the test account I left in DPAPI from last week" vs. "the workshop
code I just redeemed for a new event." Skipping it has caused at least one
real audit run to execute against the wrong tenant.

The behavior is governed by `judge-config.yml.execution.account_prompt_mode`:

- `always` (default): show the prompt every fresh run, even if a cached
  account exists and is unexpired. Forces the user to opt in to reuse.
- `only_if_expired`: skip the prompt only when `expires_at` is in the future;
  prompt when expired or missing.
- `only_if_missing`: prompt only when no cached account exists at all.
  Equivalent to the pre-0.2 behavior. Not recommended.

Procedure:

1. Check `runtime/account/account.meta.json`. If it exists, read `user_id`,
   `tenant_hint`, `cached_at`, `expires_at`.
2. Decide whether to prompt based on `account_prompt_mode` above. If you
   choose to skip the prompt under a non-default mode, log the decision and
   the reason ("skip_reason: expires_at_in_future") into the run manifest so
   future readers know the cached account wasn't user-confirmed for this run.
3. When prompting (the typical path), use `AskUserQuestion`:
   - Question: `Use the cached test account?`
   - Options:
     - `[Recommended] Use cached: <user_id>` — description: `Cached
       <relative-time> ago. Expires <expires_at or "unknown">.`
     - `Redeem a new workshop code` — description: `Discards the cached
       account and prompts for a fresh workshop code.`
4. If the user picks "Redeem a new..." or no cache exists, follow
   `references/workshop-redemption.md` end-to-end:
   - Prompt for the workshop code (`AskUserQuestion`, single free-text
     option labeled "Enter workshop code").
   - Open the workshop portal, fill the code, scrape the issued credentials.
   - Sign in to AAD, capture `storage-state.json`.
   - Encrypt the credential blob via DPAPI and write `credential.enc` +
     `account.meta.json`.

After Phase 1.5, the orchestrator has a valid signed-in browser context and a
usable `account_user_id`. Whichever account was chosen must be recorded in
the run manifest under `account.user_id` and `account.source: cached | redeemed`.

### Phase 1.7 — Plan execution order (fan-out vs serial)

After Phase 1.5 but before Phase 2, build the execution plan from
`judge-config.yml.lab_dependencies` and the planned lab list.

> **The static phase is not a substitute for the interactive phase.**
> Static checks can spot typos, broken links, missing images, and structural
> drift. They cannot spot UI drift in the live product — controls that have
> been renamed, dialogs that have been added, settings that have moved.
> The interactive phase is what catches the issues that actually break a
> learner mid-lab. Doing only the static phase is the audit equivalent of
> running `tsc --noEmit` and calling it tested.

The behavior is governed by
`judge-config.yml.execution.require_interactive_phase` (default `true`).
When `true`, the orchestrator MUST run Phase 2 against the signed-in
training account. The only way to skip Phase 2 is to pass the
`--static-only` CLI flag (or set the config to `false`), and either choice
is recorded in the run manifest as `execution.skipped_interactive: true,
reason: <flag|config>`.

1. **Static phase** is always fully fanned out. Spawn one background
   subagent per lab in the planned list (capped at
   `execution.static_fanout_concurrency`). Each subagent does the
   markdown-only checks: parser-spec validation, image-ref resolution,
   external-URL link-check via `WebFetch`, TOC-anchor sanity, prereq
   sanity, self-consistency between the Use Cases Covered table and the
   real scene headings. Subagents write their findings as
   `runs/<run-id>/labs/<slug>/findings-static.json`. No browser, no
   tenant state, no GitHub writes.

2. **Interactive phase** (REQUIRED by default — see the callout above)
   topologically sorts the planned labs against `lab_dependencies`. Each
   entry under `lab_dependencies` defines a `chain` (ordered list of slugs
   that must run serially because each lab's tenant artifacts are read by
   the next). Independent labs run in parallel — but only up to
   `execution.fanout_concurrency` browser sessions per training account,
   since concurrent UI activity in the same tenant can collide (e.g. two
   labs both renaming the same default agent).

   The default `fanout_concurrency: 1` preserves the legacy strict-serial
   behavior. Raising it requires either (a) a workshop event whose labs
   genuinely don't share tenant state, or (b) provisioning one training
   account per concurrent slot.

3. The orchestrator merges static and interactive findings for each lab
   into a single `findings.json` at the end of the lab's interactive
   pass. The static `findings-static.json` is also retained for
   debugging.

### Phase 2 — Per-lab loop (interactive UI execution)

This phase is the **core deliverable** of the audit. The orchestrator drives
a real browser through every step the lab tells the learner to perform,
using the account chosen in Phase 1.5, and compares what the live UI does
to what the lab markdown says. Skip this phase and you have a documentation
audit, not a lab audit.

For each lab slug in the interactive-phase execution plan
(respecting topological order from Phase 1.7):

1. **Mark the lab `running`** in `manifest.yml`.
2. **Parse the lab** (`references/lab-parser-spec.md`). Write the step tree to `runs/<run-id>/labs/<slug>/steps.json`.
   - On `--dry-run` or `--static-only`, stop here for this lab. Otherwise continue to step 3.
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
4. **End-of-lab disposition** — **always file an issue AND open a fix PR** when findings exist:
   - If `findings.json` has any finding with `confidence >= judge-config.yml.confidence.min_to_include_in_issue` AND the lab is not in `non_deterministic_lab_slugs` (or `--force-issue` was passed):
     1. Invoke `mcs-lab-issue-filer` (sub-skill) — files (or comments on) the GitHub issue and returns the issue number.
     2. **Then** invoke `mcs-lab-fix-pr-filer` (sub-skill) with the issue number — applies the findings' `suggested_correction` diffs to the lab markdown, copies any `proposed_screenshot_replacement` images into `labs/<slug>/images/`, commits on branch `dewain/fix-<slug>-content-audit` (creating the branch from `main` if it does not exist), pushes, and opens a PR titled `<slug>: fix audit findings from #<issue-number>` with body `Closes #<issue-number>`.
     3. If an open PR already exists on the matching branch, the PR filer appends commits to it rather than opening a duplicate.
   - Otherwise: append a clean entry to `runs/<run-id>/clean-labs.yml` (no issue, no PR).
   - In all cases: append the per-lab summary entry to `runtime/audit-history.yml` (`references/audit-log-schema.md`).
   - Mark lab `done`, `issue_filed`, or `issue_and_pr_filed` in `manifest.yml`.

   > **Why both an issue AND a PR?** The issue documents the *why* (audit run, evidence, screenshots, links to the run directory) so maintainers can triage and decide whether each finding is real. The PR ships the *what* (concrete markdown edits + screenshot replacements) so the fix is ready to review and merge with no copy-paste burden. This combined flow replaces the prior issues-only policy (2026-05 onward).
5. **Pause** for `judge-config.yml.execution.min_seconds_between_labs` before the next lab.

### Phase 3 — Wrap-up

1. Close the browser (`mcp__plugin_playwright_playwright__browser_close`).
2. Print a summary to the user: total labs, count by status, list of filed issue URLs **and PR URLs**, run-id for future `/audit-report` lookups.
3. Write `runs/<run-id>/manifest.yml` final state.

## Resume flow (`--resume <run-id>`)

When `--resume <run-id>` is passed:

1. Read `runs/<run-id>/manifest.yml`.
2. Determine which labs are `pending`, `running` (interrupted mid-run), or `error`.
3. For `done`/`issue_filed`/`issue_and_pr_filed`/`skipped` labs: keep as-is.
4. For `running`: restart that lab from the last completed scene in `checkpoint.yml`. Findings already in `findings.json` are preserved; new findings append.
5. For `pending`: run as a fresh lab.
6. Phase 1.5 prompt under `--resume`: re-prompt unless the cached
   `expires_at` is in the future AND `account_prompt_mode` is not `always`.
   A resume after the cache expired requires fresh credentials, no
   exceptions. A resume with `account_prompt_mode: always` still re-prompts —
   the user may have meant to redeem a different account for the resumed run.

## Important rules

- **Run the interactive phase by default.** Static analysis alone is not a
  complete audit. Skip Phase 2 only when the user has explicitly passed
  `--static-only` or set `execution.require_interactive_phase: false`. Either
  case must be recorded in the run manifest.
- **Always prompt at Phase 1.5 unless explicitly told not to.** Default
  `account_prompt_mode: always` means every fresh run asks "use cached vs.
  redeem new", regardless of how recently the cache was written. This is
  the user's safety net against running against the wrong tenant.
- **Never modify the mcs-labs repo.** Only read its `_labs/` and `_data/` directories.
- **Never commit, push, branch, or PR.** Issues only.
- **Never run `copilot-studio-cleanup` or any agent-deletion command** as part of an audit run. Tenant hygiene is the user's responsibility (see [[feedback_no_cleanup_in_test_automation]]).
- **Never log secrets.** The credential blob is DPAPI-encrypted; passwords never appear in transcripts, audit history, issue bodies, or `manifest.yml`. The first 4 chars of the workshop code may appear as `workshop_code_hint`.
- **Halt loudly on auth_expired.** Don't try to silently re-auth mid-run — that's how data loss happens.
- **Trust the critique pass.** If critique downgrades a finding to `pass` or `cannot_verify`, drop it from the issue.

## What to do when stuck

- **Parser couldn't classify a step**: emit a `parser_warning` finding (severity: low) and continue. Don't halt the whole lab.
- **Playwright timeout on `_browser_wait_for`** (UI took too long but the page is reachable): capture diagnostics, mark the step `transient`, retry once. If still failing, record as a finding with `outcome: broken, severity: high, confidence: 0.6`. This is a UI-side problem, not a connection problem — keep going.
- **Network / connection error** (DNS failure, `net::ERR_*`, navigation timeout to a page that should resolve quickly, repeated `net::ERR_INTERNET_DISCONNECTED`, or any failed-network entry that recurs across consecutive steps): treat as a **connection class** failure, distinct from a UI timeout. The retry policy is:
  1. Retry the failing operation up to `execution.network_retry_count` times (default `3`), pausing `execution.network_retry_backoff_seconds` between attempts (default `5`, `10`, `20` — exponential).
  2. If all retries fail, **halt the lab** (mark `status: paused, reason: network_unstable`) and prompt the user via `AskUserQuestion`:
     - Question: `Network looks unstable — what should we do?`
     - Options:
       - `[Recommended] Retry now — connection is back` — description: `Re-attempts the failing step and continues the lab from where we paused.`
       - `Wait <N> seconds and retry` — description: `Sleeps for execution.network_wait_seconds (default 120) before retrying. Use this if the outage is ongoing.`
       - `Skip this lab` — description: `Marks the lab status: error, reason: network_unstable and continues with the next lab in the plan.`
       - `Abort the run` — description: `Halts the entire run. Resume later with /audit-bootcamp --resume <run-id> when the connection is stable.`
  3. Do NOT silently keep retrying past the cap, and do NOT record a connection-class failure as a lab finding — it's an environment issue, not a lab issue. Lab findings are reserved for things the lab author can fix.
  4. Record every connection-class pause in `runs/<run-id>/transcript.md` with the timestamp, retry count, and the user's chosen response.
- **Judge call fails**: retry once with a JSON-only reminder. If still failing, log the step as `error` in the transcript but continue with the next step — don't halt the lab over one bad judge call.
- **Issue creation fails**: write a clear error to `runs/<run-id>/labs/<slug>/transcript.md`, set `status: error, reason: gh_unavailable`, keep the rendered `issue-body.md` for the user to file manually.

## What success looks like

After a full bootcamp run:
- `runtime/audit-history.yml` has 11 new entries (one per lab).
- `runtime/runs/<run-id>/` contains parsed steps, findings, screenshots, transcripts, and rendered issue bodies for every lab.
- 0–11 GitHub issues filed (typically 1–4 in practice; many labs pass cleanly).
- The user has a one-line summary in chat: `Audited 11 labs in <duration>. 7 pass, 3 filed issues, 1 error (auth expired in <slug>, resume with /audit-bootcamp --resume <run-id>).`
