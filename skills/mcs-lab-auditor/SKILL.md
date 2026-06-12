---
name: mcs-lab-auditor
description: |
  Audit Microsoft Copilot Studio labs end-to-end for any event or workshop. Resolves the mcs-labs repo location dynamically (clones/updates it as needed), enumerates auditable scopes from the repo's `_events/` and `_workshops/` collections, drives Playwright through every numbered step of each lab in the chosen scope, compares the live UI to the written instructions with an LLM judge, and either files a GitHub issue (one per lab with findings) or appends a clean-pass entry to a local audit log. Use this skill when the user says "audit the bootcamp", "audit a workshop", "run the lab auditor", "test the mcs-labs labs", or invokes any `/audit-*` command from this plugin.
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
  # Claude Code browser tools (playwright@claude-plugins-official). Copilot CLI
  # exposes the same @playwright/mcp actions under its bundled `playwright`
  # server — see references/host-tools.md. Copilot ignores unknown entries.
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

**Two write paths.** (a) the active instance's lab repo `{repo}` (e.g. `microsoft/mcs-labs`) — `gh issue create | comment` for lab findings AND `gh pr create` against the lab repo for per-lab fix PRs (one per lab with findings). (b) `microsoft/BootcampLabTestPlugin` — `gh issue create | comment` for **plugin bugs** when the auditor itself is the problem (Playwright limitation, missing reference, unhandled UI pattern) AND `gh pr create` against the plugin repo for mechanical fixes. The auditor's goal is **100% lab coverage** — when a step can't be completed, the orchestrator runs the recovery patterns in `references/plugin-self-improvement.md` §2 before concluding it's stuck, then files BOTH a lab finding (if the lab is the problem) AND a plugin bug + fix PR (if the plugin is the problem). See `references/plugin-self-improvement.md` for the full procedure including the cascading-step (high-severity) classification.

This file is the orchestrator. It loads the reference files below as needed:

- `references/lab-parser-spec.md` — how to convert a lab's markdown into a step tree.
- `references/lab-resources-spec.md` — Lab Resources discovery + pre-flight scrape of per-event SharePoint config values. Used when a lab references `copilotstudiotraining.sharepoint.com/.../Lab-Assets.aspx` (or similar) for connector credentials / endpoint URLs.
- `references/plugin-self-improvement.md` — never give up on a lab without recovery attempts; when stuck file bugs and PRs against BOTH the active instance's lab repo `{repo}` (lab side) and `microsoft/BootcampLabTestPlugin` (plugin side) as appropriate; cascading-step failures are high-severity.
- `references/playwright-cookbook.md` — portal sign-in flow, scene-boundary auth probe, tool mapping per step kind, known quirks.
- `references/workshop-redemption.md` — Skillable-style workshop redemption flow.
- `references/workshop-redemption-chatbot.md` — chatbot Adaptive Card workshop redemption flow.
- `references/llm-judge-prompts.md` — the per-step judge, the second-pass critique, the action classifier.
- `references/finding-schema.md` — finding record fields, outcome and severity definitions.
- `references/audit-log-schema.md` — `audit-history.yml` entry shape.

Read whichever you need before doing the corresponding step. Don't try to keep all of them in your head at once.

## Top-level entry points (called from command files)

| Command | What this skill does |
|---|---|
| `/audit-event [--event <key>] [--resume <id>] [--labs csv] [--no-issue]` | Audit every lab in an event OR workshop. With `--event <key>` the scope is pinned; without it, Phase 1.5 Q3a picks one. Generic over every scope in the repo's `_events/` and `_workshops/` collections. |
| `/audit-bootcamp [--resume <id>] [--labs csv] [--no-issue]` | Shortcut for `/audit-event --event bootcamp`. Audits every bootcamp lab. Skips Q3 and Q3a in the interview. |
| `/audit-lab [<slug>] [--no-issue] [--dry-run]` | Audit a single lab. With `<slug>`, the slug pins scope. Without, Phase 1.5 Q4 picks one from the **full all-labs catalog** (`lab_metadata.*`), not constrained to any event. |
| `/audit-report [<run-id>]` | Summarize `audit-history.yml`. No browser activity. |
| `/audit-account [show\|redeem\|clear]` | Manage the cached test account. |

## Run lifecycle (for `/audit-bootcamp` and `/audit-lab`)

### Phase 1 — Pre-flight (no browser yet)

1. **Plugin self-version check (best-effort, runs FIRST).** Before anything else, confirm this plugin is current — auditing on a stale copy produces stale findings. Run:
   ```
   pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Test-PluginVersion.ps1"
   ```
   It compares the local `.claude-plugin/plugin.json` version to the version published on `origin/main` of `microsoft/BootcampLabTestPlugin`. Behavior:
   - `plugin up-to-date (vX.Y.Z)` → continue silently.
   - `UPDATE AVAILABLE: local vA < published vB …` (exit 10) → **surface the warning to the user** and recommend running `/plugin` to update before continuing, but do NOT hard-halt — let the user decide (they may be intentionally testing a local build).
   - `version check skipped (…)` (offline / `gh` unavailable) → note it and continue. The check is best-effort and never blocks a run.

2. **Orchestrator-is-Opus assertion (MANDATORY).** The mcs-lab-auditor orchestrator REQUIRES Opus. The plugin halts at this step if the Claude Code session model is not Opus. Detection: the system env line `You are powered by the model named Opus 4.7` (or any future `Opus X.Y`). Lower-tier orchestration silently degrades the entire audit's reliability — Sonnet and Haiku struggle with recovery patterns, dialog disambiguation, and the long-form per-lab state tracking. Sub-agents (per-UC, per-step judge, critique, static fan-out, issue-filer, fix-PR filer, PR appender) CAN run on lower-tier models — that's the Q5 model-preset question. The orchestrator itself cannot.

   On non-Opus orchestrator, halt with:
   ```
   ERROR: mcs-lab-auditor requires the orchestrator to run on Opus.
   Current session model: <detected model>
   Switch to Opus (e.g. /model in Claude Code) and re-run the /audit-* command.
   Lower-tier sub-agents are still supported — see Phase 1.5 Q5 model-preset.
   ```
   Do NOT proceed past Phase 1 step 2 on a non-Opus session.

#### Resolve the active lab instance (FIRST, before any repo or portal access)

Run once at the start of every audit/build run:

```
pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT/scripts/Resolve-LabInstance.ps1" -Mode Json -Instance "<--instance value or empty>"
```

Parse the JSON and hold these values for the whole run — every sub-skill uses them:

- `{repo}`           = `.repo`           (e.g. `microsoft/mcs-labs`) — the target for ALL `gh issue` / `gh pr` / `gh repo` calls.
- `{branch_prefix}`  = `.branch_prefix`  (e.g. `dewain`) — the prefix for ALL created branches. If `.branch_prefix_source` is `unresolved`, do NOT create any branch; halt and ask the user to set `branch_prefix` in their `lab-instances.yml` or authenticate `gh`.
- `{clone_url}` / candidates are consumed by `Resolve-LabRepo.ps1 -Instance` (next step).

Then resolve the repo, passing the instance through:

```
pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT/scripts/Resolve-LabRepo.ps1" -Mode Status -Instance "<--instance value or empty>"
```

Replace the old hardcoded `gh repo view microsoft/mcs-labs …` permission check with `gh repo view {repo} …`.

#### Materialize the active portal

Write the resolved `.portal` object to `runtime/account/active-portal.yml` (create the dir if needed). All redemption flows read THIS file, never `config/workshop.yml` directly. For the default `mcs-labs` instance this file is a copy of `config/workshop.yml`, so redemption behaves identically.

3. **Resolve the plugin directory and the mcs-labs repo (NO hard-coded paths).**
   - The plugin's own files are reached via the `${CLAUDE_PLUGIN_ROOT}` environment variable Claude Code sets for this plugin — never a hard-coded `C:\Users\...\.claude\plugins\...` path. All script invocations below use `"$env:CLAUDE_PLUGIN_ROOT\scripts\<name>.ps1"`.
   - The mcs-labs repo location is **resolved, not assumed**. Run:
     ```
     pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Path -Instance "<--instance value or empty>"
     ```
     This finds the repo (via `$env:MCS_LABS_REPO`, the `judge-config.yml.build.registration.mcs_labs_repo_path_candidates`, or a built-in candidate list), **clones `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs` if no local copy exists**, and **pins the working tree to `origin/main`** (it checks out `origin/main` even if the clone was left on a stale feature branch — a clean tree only; a dirty tree is left untouched and surfaced loudly). It prints the resolved absolute path. Capture that path as `$REPO` and use it for every subsequent read of `_labs/`, `_events/`, `_workshops/`, `_data/`. On `--dry-run` or static-only runs you may pass `-NoPull` to skip the fetch. If resolution fails (clone error, no git), halt with the script's error message.
   - **ASSERT the audited revision is `origin/main` (MANDATORY unless `-NoPull`).** A lab audit is only meaningful against the *current* instructions. After capturing `$REPO`, confirm the working tree is exactly `origin/main`:
     ```
     pwsh -NoProfile -Command "git -C '$REPO' fetch --quiet origin; if ((git -C '$REPO' rev-parse HEAD) -ne (git -C '$REPO' rev-parse origin/main)) { 'MISMATCH' } else { 'ok' }"
     ```
     If this prints `MISMATCH` (the clone is on a stale branch, behind `origin/main`, or has uncommitted changes blocking the pin), **halt** with a clear message that names the diverging-commit count and tells the user to commit/stash and re-run — do NOT proceed to parse labs against non-`origin/main` content. Record the audited commit SHA (`git -C $REPO rev-parse --short origin/main`) in `manifest.yml` so every finding is traceable to an exact instruction revision, and reference that SHA in issue/PR bodies. (Auditing a stale branch silently produces findings that are already fixed on `main` — issue #41.)

4. **Load configs**:
   - `runtime/account/active-portal.yml`
   - `config/judge-config.yml`

5. **Check `gh` auth**:
   ```
   gh auth status
   gh repo view {repo} --json viewerPermission
   ```
   If either fails, halt with a clear message before doing anything else.

6. **Enumerate the auditable scopes (events AND workshops) AND the active scope's lab list.** The source of truth is the repo's two Jekyll collections, NOT the legacy `lab-config.yml.event_configs` table (which has drifted out of sync — it is missing newer workshops like `agent-in-a-day` and the academy series and still lists an obsolete `mcs-in-a-day-v2`). Use the legacy table only as a last-resort fallback when the collections are unreadable.
   - Run:
     ```
     pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Get-EventCatalog.ps1" -RepoRoot "$REPO" -Json
     ```
     This scans `$REPO\_events\*.md` (`type: event`) and `$REPO\_workshops\*.md` (`type: workshop`) and returns, per scope: `{ type, id, title, description, order, external, external_url, repository, auditable, labs[] }`. `labs[]` is the ordered slug list from each scope's front-matter `labs:` array. When a richer `$REPO\_data\agendas\<id>.yml` exists, its `schedule[]` entries with `type: lab` override the order/labels — but the slug set is the same.
     - **Events** are formal curated experiences (bootcamp, the buildathons). **Workshops** are less formal / on-demand (azure-ai-workshop, mcs-in-a-day, agent-in-a-day, the agent-academy series).
     - `external: true` scopes (e.g. the agent-academy workshops) host their labs in another repo (`repository`), so `auditable` is false — list them for awareness in the picker but never try to drive them; if one is chosen, explain it can't be audited locally and point at its `external_url`.
   - Build the **all-labs catalog** for single-lab scope (Phase 1.5 Q4): `{slug → { title, … }}` from `lab_metadata.*` in `$REPO\_data\lab-config.yml`, with each `_labs/<slug>.md` front-matter `title:` as a fallback. (`lab_metadata` is still maintained per-lab, so it remains the single-lab picker source.)
   - Determine which scope drives the active run:
     - `/audit-bootcamp` → scope = the `bootcamp` event (pinned).
     - `/audit-event` → scope = the event/workshop named by `--event <key>` if passed; otherwise resolved by Phase 1.5 Q3a (scope picker). `--event` matches an `id` from the catalog regardless of whether it is an event or a workshop.
     - `/audit-lab <slug>` → scope is a single slug; for display, use the first catalog entry whose `labs[]` contains the slug, or `none` if the slug belongs to no scope.
   - For the active scope (whole event/workshop, `--labs csv` subset, or single slug), confirm `$REPO\_labs\<slug>.md` exists for every chosen slug. If not, record `status: skipped, reason: lab_file_missing` and continue with the next slug — never abort the whole run because one lab is missing.

7. **Run-start account prompt** (see Phase 1.5 below). On `--dry-run`, skip this — `--dry-run` only exercises the parser and writes `steps.json` per lab.

8. **Create the run directory**:
   ```
   $run_id = (Get-Date -Format "yyyy-MM-ddTHHmmZ") + "-" + (-join ((1..4) | % { '{0:x}' -f (Get-Random -Maximum 16) }))
   $run_dir = "runtime/runs/$run_id"
   ```
   Initialize `manifest.yml` with the planned lab list, all `status: pending`, and the run start timestamp.

#### Browser-MCP preflight (before any interactive step)

The interactive phase needs a Playwright MCP. Tool names differ per host — see
[`references/host-tools.md`](references/host-tools.md). Before the first browser
action:

1. Check your available tools for the Playwright `browser_*` actions (Claude:
   `mcp__plugin_playwright_playwright__*`; Copilot: the bundled `playwright`
   server). 
2. **If present** → proceed with the interactive phase, calling each action by
   its host-qualified name.
3. **If absent** → do NOT call a browser tool. Fall back to `--static-only` for
   this run and tell the user how to enable the browser for their host:
   - Claude Code: enable the `playwright@claude-plugins-official` MCP plugin.
   - Copilot CLI: the plugin bundles a `playwright` MCP (`.github/mcp.json`); it
     needs `npx` + network on first use. Run `copilot mcp list` to confirm it
     loaded.

### Phase 1.5 — Run-start interview (MANDATORY)

Before any Playwright activity, run an interactive interview to confirm the
scope of the run. The interview is a series of `AskUserQuestion` calls. Each
question is **skipped only when a CLI flag has already provided the answer**
— never silently default away a question the user hasn't answered, since
silent defaults have caused real audit runs to execute against the wrong
tenant or to ship a doc-only sweep when the user expected a live audit.

The interview questions, in order (Q1, Q2, Q2a model preset, Q3 scope, Q3a event, Q4 lab):

#### Q1. Account — which test account?

**This question is asked every run unless `account_prompt_mode` says otherwise.** The plugin never silently chooses between "cached" and "redeem new" — the user picks.

Governed by `judge-config.yml.execution.account_prompt_mode`:

- `always` (default): always ask, even if cache is valid. Forces the user to opt in.
- `only_if_expired`: skip only if cached `expires_at` is in the future.
- `only_if_missing`: skip only if no cached account exists at all. **Not recommended.**

When asking, use `AskUserQuestion`. The options shown are **conditional on cache state**:

| Cache state                                                          | Options shown                                                                                                                                                                  |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| No cache (`runtime/account/account.meta.json` missing)               | `Redeem a new workshop code` (will prompt for the code), `Abort the run`                                                                                                       |
| Cache present but `workshop_code.enc` missing (legacy cache)         | `[Recommended] Use cached: <user_id>`, `Redeem a new workshop code`, `Abort the run`                                                                                            |
| Cache present AND `workshop_code.enc` present (full cache)           | `[Recommended] Use cached: <user_id>`, `Redeem a new user from the cached workshop code` (no code prompt), `Redeem a new workshop code` (prompt for a different code), `Abort` |

Option semantics:

- **`Use cached: <user_id>`** — Reuse the existing DPAPI-cached credentials. **No workshop code prompt** — the user already exists, there is no need to redeem again. Description: `Cached <relative-time> ago. Expires <expires_at or "unknown">.`
- **`Redeem a new user from the cached workshop code`** — Only shown when `workshop_code.enc` (DPAPI-encrypted full code) is present. Decrypts the cached code, prompts for nothing, runs the redemption flow with the cached code. Description: `Issues a fresh workshop user from the same code (hint: <workshop_code_hint>...) without re-asking for it.`
- **`Redeem a new workshop code`** — Discards the cached code (if any) and prompts the user for a fresh code via `AskUserQuestion`. Description: `Prompts for a new workshop code. Use this when the cached code is exhausted or you're switching events.`
- **`Abort the run`** — Description: `Stop the run before any browser activity.`

If the user picks one of the two redemption options:

1. Read `runtime/account/active-portal.yml.portal_kind` (`chatbot | skillable | email`).
2. **Determine where the workshop code comes from**:
   - If the user picked `Redeem a new user from the cached workshop code`, decrypt `runtime/account/workshop_code.enc` via DPAPI. No `AskUserQuestion` prompt is needed.
   - Otherwise, prompt the user via `AskUserQuestion`:
     - Question: `What is the workshop code?`
     - Options: `Cancel — use cached account` (if cache exists), `Abort the run`. The user types the actual code via the auto-provided "Other" free-text path.
3. Dispatch the portal-specific redemption flow. Each flow consumes the workshop code (if required by `workshop_code_required: true`) and the deterministic config values from `runtime/account/active-portal.yml.chatbot_account_request_form` and `runtime/account/active-portal.yml.account_new_password_pattern` — **no further `AskUserQuestion` calls during redemption**:
   - `chatbot` → follow `references/workshop-redemption-chatbot.md` (Cards 1–5 + AAD sign-in + first-login password change).
   - `skillable` (or missing) → follow `references/workshop-redemption.md`.
   - `email` → submit code on the portal, detect "check your email", then use `AskUserQuestion` to collect username/password (optional tenant), then continue.
4. For all kinds, finish with the same AAD sign-in + caching path:
   - DPAPI-encrypt the **new** password (after the first-login change) into `runtime/account/credential.enc`.
   - DPAPI-encrypt the **full workshop code** into `runtime/account/workshop_code.enc` so the user can later choose `Redeem a new user from the cached workshop code` without retyping it.
   - Write `runtime/account/account.meta.json` with `user_id`, `tenant_hint`, `workshop_code_hint` (first 4 chars only), `cached_at`, `expires_at`, `run_id`, `signed_in_at`, `password_changed_on_first_login: true`.

The redemption flow is responsible for first-run portal setup too: if
`runtime/account/active-portal.yml.workshop_portal_url` is still
`REPLACE_ME_ON_FIRST_RUN`, it must prompt for `Workshop portal URL`, validate
`^https?://`, persist the URL to the active instance's source — the user's `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml` inline `portal:` when the instance came from the user file, otherwise `config/workshop.yml` — and re-materialize `runtime/account/active-portal.yml`, then continue to the
workshop-code prompt.

When skipping under a non-default `account_prompt_mode`, record the
decision in the run manifest as `account.skip_reason:
expires_at_in_future` (or similar) so future readers know the cached
account wasn't user-confirmed for this run.

#### Q2. Phase mix — static, interactive, or both?

Skip this question when ANY of:
- `--static-only` CLI flag was passed (mix = static).
- `--interactive-only` CLI flag was passed (mix = interactive).
- `judge-config.yml.execution.require_interactive_phase: false` (mix = static).

When asking, use `AskUserQuestion`:

- Question: `Which phase(s) should this run execute?`
- Options:
  - `[Recommended] Both static and interactive` — description: `Full audit.
    Static markdown checks fan out per lab, then interactive Playwright
    drives the live UI for every lab in the plan. Highest cost, most
    coverage.`
  - `Static only` — description: `Markdown parser checks, image-ref
    resolution, external link probes, prereq sanity. No browser, no
    tenant state. Fast and cheap.`
  - `Interactive only` — description: `Assumes a prior static pass
    produced findings-static.json for each lab. Drives the live UI and
    merges with the prior static findings at lab completion. Useful when
    re-verifying a previously-audited lab in a new product release.`

Record the chosen mix as `execution.phase_mix: static | interactive | both`
in the run manifest. If "static only" or "interactive only", also set
`execution.skipped_interactive: true` or `execution.skipped_static: true`
respectively, with `reason: cli_flag` or `reason: interview`.

#### Q2a. Model preset — Optimized per function, or All Opus?

Skip this question when ANY of:
- `--model-preset <key>` CLI flag was passed (`optimized` | `opus` | `custom`).
- `judge-config.yml.execution.model.preset` is set to a non-`prompt` value (i.e. the config has an explicit default, e.g. set by a previous run).
- `--resume <run-id>` was passed (preset is inherited from the prior manifest).

The orchestrator is always Opus (asserted in Phase 1 step 2). This question only chooses the model for **sub-agents** spawned by the orchestrator: per-UC subagents, the per-step LLM judge, the critique pass, static fan-out subagents, the cross-lab consistency fan-in, the lab parser subagent, and the issue-filer / fix-PR filer / PR appender sub-skills.

When asking, use `AskUserQuestion`:

- Question: `Which model preset for sub-agents?`
- Options:
  - `[Recommended] Optimized per function` — description: `Each sub-agent uses the cheapest model that handles its job well. Per-UC subagents and the LLM judge on Sonnet 4.6; static fan-out and issue/PR filers on Haiku 4.5. Approx $50 per bootcamp event run. ~85% completion rate.`
  - `All Opus` — description: `Every sub-agent and judge call runs on Opus 4.7. Maximum reliability, ~$140 per bootcamp event run, ~90% completion rate. Use when finding quality matters more than spend.`
  - `Custom (edit config)` — description: `Halt before redemption so you can edit config/judge-config.yml.execution.model.* per-function overrides, then re-run /audit-*. No subagents spawn this run.`

Record the chosen preset as `execution.model.preset: optimized | opus | custom` in the run manifest. The resolved per-function model assignments (see `judge-config.yml.execution.model`) are also frozen into the manifest so a `--resume` produces the same assignments.

On `Custom`, the orchestrator writes the current resolved assignments back to `judge-config.yml.execution.model.*` as comments (so the user can see the defaults next to their overrides), prints a one-line summary of which keys are configurable, and halts.

#### Q3. Scope — an event or a single lab?

Skip this question when ANY of:
- `--labs <csv>` CLI flag was passed (scope = csv → the driving event/workshop is the one whose `labs[]` is a superset of the csv, or `multi` if the csv crosses scopes).
- The entry point is `/audit-lab <slug>` (slug already names the scope; scope = `one` immediately).
- The entry point is `/audit-bootcamp` (scope is implicitly `event=bootcamp` and the question is skipped).
- The entry point is `/audit-event --event <key>` (scope is `event=<key>` and the question is skipped — but Q3a still runs if no `--event` was passed).
- `--resume <run-id>` was passed (scope is inherited from the prior manifest).

When asking, use `AskUserQuestion`:

- Question: `What should this run audit?`
- Options:
  - `[Recommended] A whole event or workshop (all its labs)` — description: `Audit every lab in an event or workshop in order, respecting lab_dependencies. Follow-up question picks which one.`
  - `Just one lab` — description: `Pick a single lab from the full mcs-labs catalog. Follow-up question lists choices.`

#### Q3a. Event/workshop picker (only if Q3 = "A whole event or workshop")

The picker source is the **events + workshops catalog** built in Phase 1 step 6 from the repo's `_events/` and `_workshops/` collections — NOT the legacy `event_configs` table. Each entry already carries `type` (`event` | `workshop`), `id`, `title`, `description`, `auditable`, and `labs[]`.

`AskUserQuestion` supports 2–4 options, and the catalog defines ~9 scopes (and growing). Show the most relevant 3 directly plus an `Other` escape hatch that accepts a free-text `id` validated against the catalog:

1. The most-used scope in `runtime/audit-history.yml` over the last 30 days is the first option, marked `[Recommended]`.
2. The two next-most-used (or, if no history, the highest-`labs`-count auditable scopes) fill the second and third slots.
3. `Other event/workshop (type the id)` is always option 4 — picks any remaining scope via "Other" free-text. Validate the typed id against the catalog `id`s; if invalid, re-ask Q3a with a `(invalid id: <typed>)` prefix.

**Label each option with its type** so the user can tell events from workshops, e.g. `[Event] Architecture Bootcamp (11 labs)` / `[Workshop] Agent in a Day (4 labs)`. Render title and description directly from the catalog entry — never hardcode them, so adding a scope only requires a new `_events/` or `_workshops/` file in the repo.

Example option set (regenerate dynamically — do not hardcode):

- Question: `Which event or workshop?`
- Options:
  - `[Recommended] [Event] Architecture Bootcamp (11 labs)` — description: the catalog `description` for `bootcamp`.
  - `[Workshop] Agent in a Day (4 labs)` — description: the catalog `description` for `agent-in-a-day`.
  - `[Workshop] MCS in a Day (4 labs)` — description: the catalog `description` for `mcs-in-a-day`.
  - `Other event/workshop (type the id)` — description: `Free-text entry. Any id from the catalog, e.g. agent-buildathon-1day, agent-buildathon-1month, azure-ai-workshop.`

If the chosen scope has `auditable: false` (an `external` workshop such as the agent-academy series, whose labs live in another repo), do not start an audit: explain that it is hosted at the scope's `external_url` / `repository` and cannot be driven locally, then re-ask Q3a for an auditable scope.

Once the scope is resolved, `scope_labs` is the `labs[]` slug list from its catalog entry (agenda-overridden order when `_data/agendas/<id>.yml` exists).

#### Q4. One-lab picker (only if Q3 = "Just one lab")

The picker source for a single-lab scope is **the full all-labs catalog** (`lab_metadata.*`), NOT one event/workshop's `labs[]`. The user has every lab in the mcs-labs repo to choose from — including specialized, optional, and external labs that no single event/workshop includes.

Because `AskUserQuestion` supports only 2–4 options per question and the catalog has 60+ labs, ask in two steps grouped by `lab_metadata.<id>.section`:

**Q4a — Section**. Use `AskUserQuestion`:

- Question: `Which section is the lab in?`
- Options:
  - `[Recommended] Core (essential foundations)` — description: `Build Intelligent Agents, Master Variables, Monitor Performance, etc. ~12 labs.`
  - `Intermediate (practical applications)` — description: `Setup for Success, Ask Me Anything, BYOM, MCS Governance, etc. ~10 labs.`
  - `Advanced & specialized (autonomous + dev)` — description: `Multi-Agent, Account News, Orchestration, MCP Connectors, Pipelines, etc. ~15 labs.`
  - `Other (type the slug)` — description: `Free-text entry. Use this for optional/external labs or when you already know the slug.`

Map sections from `lab_metadata.<id>.section`:
- "Core" = labs where `section: core`.
- "Intermediate" = labs where `section: intermediate`.
- "Advanced & specialized" = labs where `section ∈ {advanced, specialized, optional, external}` (consolidated to keep the question to 4 options).

**Q4b — Lab in the chosen section**. Render the section's labs as the `AskUserQuestion` options, with the lab's title (from `lab_metadata.<id>.title` or the front-matter as fallback) as the description.

When a section has more than 4 labs (most do), paginate by listing the first 3 entries plus an explicit `More labs in <section> (type the slug)` option as the 4th. The "Other" free-text response is validated against `lab_metadata.*.id` — if the typed slug isn't in the catalog, re-ask Q4a with `(invalid lab slug: <typed>)` prefix.

The 3-shown-per-section choice is intentional: most users navigate to a known section, then either see their target in the first 3 or type the slug. Re-asking with full pagination via numeric prefixes was rejected as more clicks than typing.

For "Other (type the slug)" at Q4a, skip Q4b entirely — the free-text response is the chosen slug. Validate it against `lab_metadata.*.id`; if invalid, re-ask Q4a with the validation prefix.

Read the title from `lab_metadata.<id>.title` (the source of truth in `lab-config.yml`) with the front-matter `title:` of `_labs/<slug>.md` as a fallback if `lab_metadata` is unavailable at interview time.

#### Recording the interview outcome

Append all interview answers to the run manifest before Phase 1.7 starts:

```yaml
interview:
  account_choice: cached | redeemed | aborted
  phase_mix: static | interactive | both
  model_preset: optimized | opus | custom   # Q2a; see execution.model.resolved below for per-function assignments
  scope: event | one             # "event" → audit a whole event/workshop's lab list; "one" → audit a single slug from the all-labs catalog
  scope_type: event | workshop | null  # which collection the chosen scope came from; null when scope == one
  event: <scope-id|null>         # the chosen event/workshop id; null when scope == one (single-lab runs have no driving scope)
  scope_labs: [<slug>, ...]      # the final list driving Phase 1.7 (always 1+ entries)
  skipped_questions:              # questions short-circuited by CLI flags or by the entry-point command
    - { question: "phase_mix", reason: "cli_flag: --static-only" }
    - { question: "model_preset", reason: "cli_flag: --model-preset optimized" }
    - { question: "event_picker", reason: "command: /audit-bootcamp" }

execution:
  model:
    preset: optimized | opus | custom
    resolved:                            # per-function frozen assignments for this run
      uc_subagent:        sonnet | opus | haiku
      judge:              sonnet | opus | haiku
      critique:           sonnet | opus | haiku
      static_subagent:    sonnet | opus | haiku
      cross_lab:          sonnet | opus | haiku
      lab_parser:         sonnet | opus | haiku
      issue_filer:        sonnet | opus | haiku
      fix_pr_filer:       sonnet | opus | haiku
      pr_appender:        sonnet | opus | haiku
```

After the interview, the orchestrator has:
- A valid signed-in browser context (or `phase_mix: static` so none is needed).
- A confirmed `account_user_id`.
- An explicit `phase_mix`.
- An explicit `model_preset` plus the frozen per-function `execution.model.resolved` map. **Every Agent / subagent spawn from here on MUST pass the resolved model via the tool's `model` parameter.**
- An explicit lab list for Phase 1.7's plan.

Record the account itself under `account.user_id` and `account.source:
cached | redeemed` as before.

### Phase 1.6 — Lab Resources discovery and pre-flight scrape (CONDITIONAL)

After Phase 1.5 (so the browser is signed in) but before Phase 1.7, check
whether any lab in the planned list references a per-event **Lab
Resources** SharePoint page. The full procedure is in
`references/lab-resources-spec.md`; the orchestrator-side summary:

1. For each lab in the planned list, parse `_labs/<slug>.md` for external
   URLs matching the Lab Resources pattern (see
   `lab-resources-spec.md` §1). If found, record
   `lab_metadata.lab_resources_url` in the parsed step tree.
2. If **any** lab has a Lab Resources URL, perform a single pre-flight
   scrape: navigate, capture page text via `browser_evaluate`, parse the
   label-value table per `lab-resources-spec.md` §3, and write the result
   to `runs/<run-id>/lab-resources.yml`.
3. **Skip Phase 1.6 entirely** when `--dry-run` is set OR the run is
   static-phase-only (no browser session exists in either case).
4. Take a debug screenshot at `runs/<run-id>/lab-resources.png` (local-only,
   never uploaded anywhere).
5. If the scrape fails (page 401/403/404, parser miss, network error),
   log the failure, set `lab_resources.status: unavailable` in the run
   manifest, and continue. Labs that don't depend on Lab Resources are
   unaffected; labs that do will fall back to user-prompt or
   `cannot_verify` per `lab-resources-spec.md` §6.

**Security — non-negotiable.** Lab Resources values include real credentials
(passwords, connection secrets, API keys). The orchestrator and every
downstream subagent MUST NOT include any scraped value verbatim in:
issue bodies, PR descriptions, commit messages, `audit-history.yml`,
`manifest.yml`, console output, judge prompts, transcripts. Reference
values by key only — e.g. *"the password from
lab_resources.labs.setup-for-success.servicenow.password"*, never the
literal. The cache file `runs/<run-id>/lab-resources.yml` lives in the
run directory and is excluded from any rendered finding artifact;
`runtime/` is gitignored at the repo root. See `lab-resources-spec.md` §4
for the full security contract.

After Phase 1.6, the orchestrator has the lab-resources cache available
under `runs/<run-id>/lab-resources.yml` (or knows it's `unavailable`).
Per-lab interactive subagents read from it when a step's text references
a Lab Resources value.

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
   `execution.static_fanout_concurrency`). **Pass `model:
   <execution.model.resolved.static_subagent>`** on each `Agent` tool
   call (typically `haiku` under the `optimized` preset). Each subagent
   does the markdown-only checks: parser-spec validation, image-ref
   resolution, external-URL link-check via `WebFetch`, TOC-anchor
   sanity, prereq sanity, self-consistency between the Use Cases
   Covered table and the real scene headings. Subagents write their
   findings as `runs/<run-id>/labs/<slug>/findings-static.json` AND a
   sidecar `runs/<run-id>/labs/<slug>/scene-fingerprints.json` (shape
   hash, identifier tokens, raw-excerpt line numbers — see
   `references/cross-lab-consistency.md` for the schema). No browser,
   no tenant state, no GitHub writes.

   The lab-parser pass that produces `steps.json` for each lab spawns a
   separate subagent with `model:
   <execution.model.resolved.lab_parser>` (typically `sonnet` — the
   parser benefits from a stronger model than the static checks).

1a. **Cross-lab consistency fan-in.** After every per-lab static
    subagent in step 1 has returned, run a single fan-in pass with
    `model: <execution.model.resolved.cross_lab>` (typically `sonnet`)
    that reads
    every `scene-fingerprints.json` in scope, groups scenes by shape
    hash, and emits drift findings for divergent identifier tokens (e.g.
    `Address 1: State/Province` in one lab vs `Address1: State or
    Providence` in a sibling). Full algorithm in
    `references/cross-lab-consistency.md`. Output:
    `runs/<run-id>/cross-lab-consistency.json` (summary) plus
    per-lab drift findings appended to each affected lab's
    `findings-static.json` (flags: `parser_warning: true`,
    `cross_lab_drift: true`, severity always `low`).

    For a single-lab run (`scope_labs` size 1), the fan-in reads the
    most recent prior-run `scene-fingerprints.json` for every other lab
    in `lab_metadata.*.id` (the full all-labs catalog). Labs that have
    never been audited contribute nothing — the issue body documents
    this discovery limit.

    Skip when `--dry-run` is set, OR when `--static-only` AND scope size
    1 AND no prior runs on disk, OR when
    `judge-config.yml.consistency.cross_lab_enabled: false`. Record
    `consistency.cross_lab_status` in the run manifest either way.

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

### Phase 2 — Per-lab loop (interactive UI execution via per-UC subagents)

This phase is the **core deliverable** of the audit. The orchestrator drives
a real browser through every step the lab tells the learner to perform,
using the account chosen in Phase 1.5, and compares what the live UI does
to what the lab markdown says. Skip this phase and you have a documentation
audit, not a lab audit.

#### Why per-UC subagents (and not per-lab or per-step)

The interactive phase is the most context-heavy part of the run by far —
each step generates 2 accessibility snapshots, 1 screenshot, console +
network logs, and an LLM-judge call. At ~50 steps × 11 labs the
orchestrator's conversation context would overflow long before the audit
completed.

**Granularity choice: per Use Case (the `### Use Case #N:` boundaries in
the lab markdown).** Each UC is 5–20 steps, self-contained ("create a
learning assistant" / "build a sales assistant"), and runs as a
**dedicated subagent**. The orchestrator only ever sees the UC's return
summary (counts, status, findings JSON path) — not the per-step
snapshots. Per-step granularity is too fine (subagent boot overhead
dominates and intra-UC state — "the agent I just created is in the
left-nav now" — would have to be reconstructed each time). Per-lab
granularity is too coarse (subagent itself overflows on a 50-step lab).

#### Browser handoff: shared MCP browser process

The orchestrator signs in **once** in Phase 1.5. The Playwright MCP
server keeps the browser process alive across subagent boundaries — a
per-UC subagent that calls `mcp__plugin_playwright_playwright__*` (or your host's
browser tool — see references/host-tools.md) reuses
the same browser tab the orchestrator left it in. The subagent's first
real step is typically `_browser_navigate` to the URL the UC's first
parser step expects, then a `_browser_snapshot` to confirm state.

No re-auth, no session export/import, no second sign-in. The session
cookies are tenant-side, not subagent-side.

#### Per-UC state handoff: `uc-state.yml`

UCs inside the same lab share tenant artifacts (UC#1 creates an agent
named "Copilot Teacher"; UC#3 tests that agent; the judge for UC#3 needs
to know "Copilot Teacher" was the chosen name). Each UC subagent writes
`runs/<run-id>/labs/<slug>/uc-<N>-state.yml`:

```yaml
uc_id: usecase-1
finished_at: <iso>
status: complete | error | partial
ctx_vars:             # variables the next UC's judge can use as CTX_VARS
  agent_name: "Copilot Teacher"
  topic_names: ["Welcome", "PolicyLookup"]
  knowledge_sources: ["https://learn.microsoft.com/en-us/microsoft-365-copilot/"]
  solution_name: "Travel Tools"     # any artifact name set in this UC
browser_left_at:      # for resumes
  url: "https://m365.cloud.microsoft/chat/..."
  scene_completed: "Share and test your agent"
findings_count:
  high: 0
  medium: 0
  low: 0
```

The next UC's subagent reads all prior `uc-*-state.yml` files in the lab
dir and merges their `ctx_vars` into its per-step judge `CTX_VARS` input
(see `references/llm-judge-prompts.md` §A inputs). Resumable: a failed
UC N can be retried in isolation as long as UC N-1's state file exists.

#### Per-lab orchestration steps (executed by the orchestrator)

For each lab slug in the interactive-phase execution plan (respecting
topological order from Phase 1.7):

1. **Mark the lab `running`** in `manifest.yml`.
2. **Parse the lab** (`references/lab-parser-spec.md`). Write the step
   tree to `runs/<run-id>/labs/<slug>/steps.json`.
   - On `--dry-run`, stop here for this lab. Otherwise continue.
   - If `phase_mix: static` for this run, this whole loop is skipped at
     the Phase 1.7 plan level — the orchestrator never reaches Phase 2.
3. **Slice steps.json by use case.** For each use case in
   `steps.json.use_cases[]`, write
   `runs/<run-id>/labs/<slug>/uc-<N>-steps.json` containing only that
   UC's scenes and steps. This is the subagent's input.
4. **For each use case in order (serial)**:
   - **Scene-boundary auth probe** at the start of UC N (cookbook
     §scene-boundary-auth-probe). If expired, halt; mark lab `error,
     reason: auth_expired`; tell user how to resume. Do NOT spawn the
     subagent if auth failed.
   - **Spawn a per-UC subagent** (background or foreground depending on
     orchestrator preference — see "Spawning" below for the prompt
     shape). Pass `model: <manifest.interview.execution.model.resolved.uc_subagent>`
     on the `Agent` tool call so the subagent runs on the model selected
     by Phase 1.5 Q2a (e.g. `sonnet` under `optimized`, `opus` under
     `opus`). Pass the subagent: the UC's `uc-<N>-steps.json` path, the
     paths of all prior `uc-*-state.yml` files in this lab dir, the
     run-id, the lab slug, the lab-level transcript path, the
     allowed-tools list scoped to `mcp__plugin_playwright_playwright__*` (or your host's
     browser tool — see references/host-tools.md)
     + `Read` + `Write` + the per-step judge invocation, AND the
     resolved `judge` + `critique` model values from the manifest so the
     subagent's internal per-step judge call also runs on the right
     model.
   - **Wait for the subagent to return.** Its summary tells the
     orchestrator: status (complete/error/partial), findings counts by
     severity, the UC-state file path. The orchestrator does NOT need
     the per-step snapshots — those are written to disk by the subagent
     and only the judge reads them.
   - **On error**: read the subagent's `uc-<N>-state.yml.status`. If
     `error, reason: auth_expired`, halt the whole lab. If
     `error, reason: ui_blocker`, mark the UC failed and decide whether
     to continue to UC N+1 (default: continue — a blocker in UC#1 may
     not affect UC#2's independent flow) or halt the lab (when
     `lab_dependencies` says the next UC depends on this UC's artifacts).
   - **On partial**: the subagent retried `transient` failures and
     captured findings, but couldn't finish the UC's scenes. Same
     handling as `error` based on whether downstream UCs depend on the
     unfinished state.
5. **Merge UC findings into the lab's `findings.json`.** Concatenate
   each `uc-<N>-findings.json` into the single lab-level `findings.json`
   the issue-filer reads. Merge with the static-phase
   `findings-static.json` (if `phase_mix: both` or `interactive` with a
   prior static run on disk).
6. **End-of-lab disposition** — **always file an issue AND open a fix PR** when findings exist:
   - If `findings.json` has any finding with `confidence >=
     judge-config.yml.confidence.min_to_include_in_issue` AND the lab is
     not in `non_deterministic_lab_slugs` (or `--force-issue` was
     passed):
     1. Invoke `mcs-lab-issue-filer` (sub-skill) with `model:
        <execution.model.resolved.issue_filer>` — files (or comments on)
        the GitHub issue and returns the issue number.
     2. **Then** invoke `mcs-lab-fix-pr-filer` (sub-skill) with that issue
        number and `model: <execution.model.resolved.fix_pr_filer>` —
        applies the findings' `suggested_correction` diffs to the lab
        markdown, copies any `proposed_screenshot_replacement` images
        into `labs/<slug>/images/`, and ships them as a PR. **PR dedup is
        scoped to OPEN PRs only:**
        - If an **open** fix-PR for the slug already exists (same author,
          mergeable — resolved from Phase 1.4 `existing-state.yml` or a
          head-prefix `gh pr list` query), the run's commit is **appended**
          to that PR — no duplicate is opened.
        - Otherwise (no open PR — including when prior PRs were merged or
          closed), a **new** PR is opened on a run-unique branch
          `{branch_prefix}/fix-<slug>-content-audit-<run-id>` from `main`, titled
          `<slug>: fix audit findings from #<issue-number>` with body
          `Closes #<issue-number>`. A merged/closed prior PR never blocks a
          new one — each run with fresh findings gets its own PR.
     3. If screenshots were refreshed and an open fix-PR already exists
        for the slug, invoke `mcs-lab-pr-appender` (sub-skill) with
        `model: <execution.model.resolved.pr_appender>` for the
        screenshots-only refresh path.
   - Otherwise: append a clean entry to `runs/<run-id>/clean-labs.yml`.
   - Either way: append the per-lab summary entry to
     `runtime/audit-history.yml` (`references/audit-log-schema.md`).
   - Mark lab `done`, `issue_filed`, or `issue_and_pr_filed` in
     `manifest.yml`.
   
   > **Why both an issue AND a PR?** The issue documents the *why* (audit
   > run, evidence, screenshots, links to run artifacts) so maintainers can
   > triage confidently. The PR ships the *what* (concrete markdown edits +
   > screenshot replacements) so fixes are immediately reviewable and
   > mergeable without copy/paste.
7. **Pause** for `judge-config.yml.execution.min_seconds_between_labs`
   before the next lab.

#### Spawning: what the per-UC subagent's prompt looks like

The orchestrator hands each per-UC subagent a self-contained prompt with:

- Lab slug, UC id, run id, account user_id (for context only — the
  browser is already signed in).
- Path to `uc-<N>-steps.json` (input).
- Paths to all `uc-<1..N-1>-state.yml` for prior UCs in this lab
  (read-only).
- Path where the subagent must write `uc-<N>-state.yml` and
  `uc-<N>-findings.json`.
- The dispatch table from `references/playwright-cookbook.md#tool-mapping`.
- The judge prompt template from `references/llm-judge-prompts.md#A`.
- Explicit rules:
  - **The browser is already signed in and on a URL related to the prior
    UC (or the lab's landing URL for UC#1).** Navigate as the first
    step requires; never call sign-in flow.
  - **Execute the lab by following the written steps and clicking the
    actual UI controls — NEVER navigate by URL to shortcut a step, and
    NEVER treat a URL seen in a screenshot as a navigation target
    (issue #40).** Lab screenshots (`![...](images/*.png)`) illustrate
    the *expected result*; they are not instructions. The only legitimate
    `_browser_navigate` calls are the ones the step text explicitly tells
    the learner to make (e.g. "go to make.powerapps.com"). Reaching a
    later page via a synthesized deep-link hides the very instruction
    drift the audit exists to catch (a renamed/moved/missing control), so
    if the named control can't be found, record a **finding**
    (expected-vs-actual) instead of working around it with a URL.
  - **Verify identity on every new first-party surface (issue #39).**
    Before driving Copilot Studio, Power Apps, the Power Platform admin
    center, Teams, or Outlook, confirm the page is signed in as the
    *exact redeemed workshop user* (`account.user_id`), not merely "signed
    in" — the audit browser can silently SSO into a different
    OS-broker/Windows account. If the surface shows a different user
    (e.g. Power Apps defaulting to a prior run's `DEV - User XXXX`), halt
    that UC with `error, reason: account_mismatch` and let the
    orchestrator resolve it (full logout → re-login as the redeemed user)
    rather than URL-hacking into the right environment.
  - **Save snapshots to disk by default** —
    `_browser_snapshot({filename: "snapshots/<step-id>-before.yml"})`
    instead of returning inline. The judge reads from disk. This is the
    single biggest context-saver for the subagent itself.
  - **Save screenshots to
    `runs/<run-id>/labs/<slug>/screenshots/<step-id>.png`** as before.
  - **Write `uc-<N>-state.yml` at the end** with all ctx_vars set
    during the UC.
  - **Return to the orchestrator** only: status, findings counts,
    `uc-<N>-state.yml` path. Do NOT echo back snapshots or transcripts.
  - **Connection-class failures** follow the network-retry policy and
    if exhausted, halt with `error, reason: network_unstable` so the
    orchestrator can `AskUserQuestion` the user.
### Phase 3 — Wrap-up

1. Close the browser (`mcp__plugin_playwright_playwright__browser_close` (or your host's browser tool — see references/host-tools.md)).
2. Print a summary to the user: total labs, count by status, list of filed issue URLs **and PR URLs**, run-id for future `/audit-report` lookups.
3. Write `runs/<run-id>/manifest.yml` final state.

## Resume flow (`--resume <run-id>`)

When `--resume <run-id>` is passed:

1. Read `runs/<run-id>/manifest.yml`.
2. Determine which labs are `pending`, `running` (interrupted mid-run), or `error`.
3. For `done`/`issue_filed`/`issue_and_pr_filed`/`skipped` labs: keep as-is.
4. For `running` or `error` (interrupted mid-lab): resume at the
   **UC-level**. List `runs/<run-id>/labs/<slug>/uc-*-state.yml` files;
   the first UC without a state file is where Phase 2 restarts for this
   lab. Findings already on disk (`uc-<N>-findings.json` for completed
   UCs) are preserved; new UCs append. If a UC partially completed
   (`uc-<N>-state.yml.status: partial`), the orchestrator MAY re-run
   that UC from scratch (since UC-level idempotency is best-effort —
   the tenant may already have the agent the UC was supposed to create)
   or skip ahead based on the partial state. Default behavior is to
   re-run the partial UC and let its judge mark the "create" steps
   `cannot_verify` if the artifact already exists.
5. For `pending`: run as a fresh lab.
6. Phase 1.5 interview under `--resume`: inherit `phase_mix` and
   `scope_labs` from the prior manifest (skip Q2 and Q3). Re-ask the
   account question (Q1) unless `account_prompt_mode` permits skipping
   AND the cached `expires_at` is still in the future. A resume after
   the cache expired requires fresh credentials, no exceptions. A
   resume with `account_prompt_mode: always` still re-prompts — the
   user may have meant to redeem a different account for the resumed run.

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
