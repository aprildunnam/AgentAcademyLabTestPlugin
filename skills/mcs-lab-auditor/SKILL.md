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

**Two write paths.** (a) `microsoft/mcs-labs` — `gh issue create | comment` for lab findings AND `gh pr create` against the lab repo for per-lab fix PRs (one per lab with findings). (b) `microsoft/BootcampLabTestPlugin` — `gh issue create | comment` for **plugin bugs** when the auditor itself is the problem (Playwright limitation, missing reference, unhandled UI pattern) AND `gh pr create` against the plugin repo for mechanical fixes. The auditor's goal is **100% lab coverage** — when a step can't be completed, the orchestrator runs the recovery patterns in `references/plugin-self-improvement.md` §2 before concluding it's stuck, then files BOTH a lab finding (if the lab is the problem) AND a plugin bug + fix PR (if the plugin is the problem). See `references/plugin-self-improvement.md` for the full procedure including the cascading-step (high-severity) classification.

This file is the orchestrator. It loads the reference files below as needed:

- `references/lab-parser-spec.md` — how to convert a lab's markdown into a step tree.
- `references/lab-resources-spec.md` — Lab Resources discovery + pre-flight scrape of per-event SharePoint config values. Used when a lab references `copilotstudiotraining.sharepoint.com/.../Lab-Assets.aspx` (or similar) for connector credentials / endpoint URLs.
- `references/plugin-self-improvement.md` — never give up on a lab without recovery attempts; when stuck file bugs and PRs against BOTH `microsoft/mcs-labs` (lab side) and `microsoft/BootcampLabTestPlugin` (plugin side) as appropriate; cascading-step failures are high-severity.
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
| `/audit-event [--event <key>] [--resume <id>] [--labs csv] [--no-issue]` | Audit every lab in a workshop event. With `--event <key>` the event is pinned; without it, Phase 1.5 Q3a picks one. Generic over all events defined in `lab-config.yml.event_configs`. |
| `/audit-bootcamp [--resume <id>] [--labs csv] [--no-issue]` | Shortcut for `/audit-event --event bootcamp`. Audits every bootcamp lab. Skips Q3 and Q3a in the interview. |
| `/audit-lab [<slug>] [--no-issue] [--dry-run]` | Audit a single lab. With `<slug>`, the slug pins scope. Without, Phase 1.5 Q4 picks one from the **full all-labs catalog** (`lab_metadata.*`), not constrained to any event. |
| `/audit-report [<run-id>]` | Summarize `audit-history.yml`. No browser activity. |
| `/audit-account [show\|redeem\|clear]` | Manage the cached test account. |

## Run lifecycle (for `/audit-bootcamp` and `/audit-lab`)

### Phase 1 — Pre-flight (no browser yet)

1. **Orchestrator-is-Opus assertion (MANDATORY).** The mcs-lab-auditor orchestrator REQUIRES Opus. The plugin halts at this step if the Claude Code session model is not Opus. Detection: the system env line `You are powered by the model named Opus 4.7` (or any future `Opus X.Y`). Lower-tier orchestration silently degrades the entire audit's reliability — Sonnet and Haiku struggle with recovery patterns, dialog disambiguation, and the long-form per-lab state tracking. Sub-agents (per-UC, per-step judge, critique, static fan-out, issue-filer, fix-PR filer, PR appender) CAN run on lower-tier models — that's the Q5 model-preset question. The orchestrator itself cannot.

   On non-Opus orchestrator, halt with:
   ```
   ERROR: mcs-lab-auditor requires the orchestrator to run on Opus.
   Current session model: <detected model>
   Switch to Opus (e.g. /model in Claude Code) and re-run the /audit-* command.
   Lower-tier sub-agents are still supported — see Phase 1.5 Q5 model-preset.
   ```
   Do NOT proceed past Phase 1 step 1 on a non-Opus session.

2. **Resolve the plugin directory**. It is `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor`. The mcs-labs repo is `C:\Users\dewainr\mcs-labs`. Both are fixed paths on this machine.

3. **Load configs**:
   - `config/workshop.yml`
   - `config/judge-config.yml`

4. **Check `gh` auth**:
   ```
   gh auth status
   gh repo view microsoft/mcs-labs --json viewerPermission
   ```
   If either fails, halt with a clear message before doing anything else.

5. **Enumerate the lab catalog AND the active event's lab list**:
   - Read `C:\Users\dewainr\mcs-labs\_data\lab-config.yml`.
   - From `event_configs`, build a map `{event_key → { title, description, config_key, slugs[] }}` for every event defined in the file. `slugs[]` is the ordered list read from the matching `<config_key>` top-level entry (e.g. `bootcamp_lab_orders`, `agent_buildathon_1month_lab_orders`, `mcs_in_a_day_v2_lab_orders`, etc.). Skip the `legacy_lab_orders` table.
   - From `lab_metadata`, build the **all-labs catalog**: `{slug → { id, title, section, difficulty, duration }}`. This is the picker source for single-lab scope (Phase 1.5 Q4) and the comparison surface for single-lab cross-lab consistency runs.
   - Determine which event drives the active run:
     - `/audit-bootcamp` → event = `bootcamp` (pinned).
     - `/audit-event` → event = the value of `--event <key>` if passed; otherwise resolved by Phase 1.5 Q3a (event picker).
     - `/audit-lab <slug>` → event is informational only (the run audits a single slug regardless); use the first event whose `slugs[]` contains the slug for display purposes, or `none` if the slug is event-less.
   - For the active scope (whole event, `--labs csv` subset, or single slug), confirm `_labs/<slug>.md` exists for every chosen slug. If not, record `status: skipped, reason: lab_file_missing` and continue with the next slug — never abort the whole run because one lab is missing.

6. **Run-start account prompt** (see Phase 1.5 below). On `--dry-run`, skip this — `--dry-run` only exercises the parser and writes `steps.json` per lab.

7. **Create the run directory**:
   ```
   $run_id = (Get-Date -Format "yyyy-MM-ddTHHmmZ") + "-" + (-join ((1..4) | % { '{0:x}' -f (Get-Random -Maximum 16) }))
   $run_dir = "runtime/runs/$run_id"
   ```
   Initialize `manifest.yml` with the planned lab list, all `status: pending`, and the run start timestamp.

### Phase 1.5 — Run-start interview (MANDATORY)

Before any Playwright activity, run an interactive interview to confirm the
scope of the run. The interview is a series of `AskUserQuestion` calls. Each
question is **skipped only when a CLI flag has already provided the answer**
— never silently default away a question the user hasn't answered, since
silent defaults have caused real audit runs to execute against the wrong
tenant or to ship a doc-only sweep when the user expected a live audit.

The interview questions, in order (Q1, Q2, Q2a model preset, Q3 scope, Q3a event, Q4 lab):

#### Q1. Account — which test account?

Governed by `judge-config.yml.execution.account_prompt_mode`:

- `always` (default): always ask, even if cache is valid.
- `only_if_expired`: skip only if cached `expires_at` is in the future.
- `only_if_missing`: skip only if no cached account exists at all.

When asking, use `AskUserQuestion`:

- Question: `Use the cached test account?`
- Options:
  - `[Recommended] Use cached: <user_id>` — description: `Cached
    <relative-time> ago. Expires <expires_at or "unknown">.` (Show only if
    a cache exists.)
  - `Redeem a new workshop code` — description: `Discards the cached
    account and prompts for a fresh workshop code.`
  - `Abort` — description: `Stop the run before any browser activity.`

If the user picks "Redeem a new..." or no cache exists:

1. Read `config/workshop.yml.portal_kind` (`chatbot | skillable | email`).
2. Dispatch redemption flow:
   - `chatbot` → follow `references/workshop-redemption-chatbot.md`.
   - `skillable` (or missing) → follow `references/workshop-redemption.md`.
   - `email` → submit code on the portal, detect "check your email", then use
     `AskUserQuestion` to collect username/password (optional tenant), then continue.
3. For all kinds, finish with the same AAD sign-in + caching path:
   keep the MCP browser session authenticated, DPAPI-encrypt
   `credential.enc`, and write `account.meta.json`.

The redemption flow is responsible for first-run portal setup too: if
`config/workshop.yml.workshop_portal_url` is still
`REPLACE_ME_ON_FIRST_RUN`, it must prompt for `Workshop portal URL`, validate
`^https?://`, persist the URL to `config/workshop.yml`, then continue to the
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

The orchestrator is always Opus (asserted in Phase 1 step 1). This question only chooses the model for **sub-agents** spawned by the orchestrator: per-UC subagents, the per-step LLM judge, the critique pass, static fan-out subagents, the cross-lab consistency fan-in, the lab parser subagent, and the issue-filer / fix-PR filer / PR appender sub-skills.

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
- `--labs <csv>` CLI flag was passed (scope = csv → event is the one whose `slugs[]` is a superset of the csv, or `multi` if the csv crosses events).
- The entry point is `/audit-lab <slug>` (slug already names the scope; scope = `one` immediately).
- The entry point is `/audit-bootcamp` (scope is implicitly `event=bootcamp` and the question is skipped).
- The entry point is `/audit-event --event <key>` (scope is `event=<key>` and the question is skipped — but Q3a still runs if no `--event` was passed).
- `--resume <run-id>` was passed (scope is inherited from the prior manifest).

When asking, use `AskUserQuestion`:

- Question: `What should this run audit?`
- Options:
  - `[Recommended] A whole event (all its labs)` — description: `Audit every lab in a workshop event in order, respecting lab_dependencies. Follow-up question picks which event.`
  - `Just one lab` — description: `Pick a single lab from the full mcs-labs catalog. Follow-up question lists choices.`

#### Q3a. Event picker (only if Q3 = "A whole event")

`AskUserQuestion` supports 2–4 options, and the mcs-labs catalog defines 6 events (and growing). Show the most commonly-audited 3 events directly plus an `Other` escape hatch that accepts a free-text event key validated against `event_configs.*`.

Read the option set dynamically from `event_configs` at interview time. The first three options below are the typical defaults; if `event_configs` differs (e.g. an event was added or removed), regenerate the list using these rules:

1. The most-used event in `runtime/audit-history.yml` over the last 30 days is the first option, marked `[Recommended]`.
2. The two next-most-used events fill the second and third slots.
3. `Other event (type the key)` is always option 4 — picks any of the remaining events via "Other" free-text. Validate the typed key against the keys of `event_configs`; if invalid, re-ask Q3a with a `(invalid event key: <typed>)` prefix on the question.

For the typical case as of this writing:

- Question: `Which event?`
- Options:
  - `[Recommended] Architecture Bootcamp (11 labs)` — description: `bootcamp — Intensive hands-on bootcamp covering progressive AI assistants, core concepts, governance, tools, multi-agent architectures, and autonomous agents.`
  - `Agent Build-A-Thon, 1 month (8 labs)` — description: `agent-buildathon-1month — Comprehensive month-long agent development program covering declarative agents, autonomous AI, and enterprise deployment patterns.`
  - `MCS in a Day V2 (4 labs)` — description: `mcs-in-a-day-v2 — Updated full-day workshop covering progressive AI assistants and core Copilot Studio concepts.`
  - `Other event (type the key)` — description: `Free-text entry. Valid keys: bootcamp, agent-buildathon-1day, agent-buildathon-1month, azure-ai-workshop, mcs-in-a-day, mcs-in-a-day-v2.`

Render each title and description directly from `event_configs.<key>.title` and `event_configs.<key>.description` — never hardcode them in the option labels, so adding a new event only requires a `lab-config.yml` edit.

Once the event is resolved, `scope_labs` is the `slugs[]` from `event_configs.<event>.config_key`.

#### Q4. One-lab picker (only if Q3 = "Just one lab")

The picker source for a single-lab scope is **the full all-labs catalog** (`lab_metadata.*`), NOT one event's `slugs[]`. The user has every lab in the mcs-labs repo to choose from — including specialized, optional, and external labs that no single event includes.

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
  scope: event | one             # "event" → audit the chosen event's lab list; "one" → audit a single slug from the all-labs catalog
  event: <event-key|null>        # null when scope == one (single-lab runs have no driving event)
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
per-UC subagent that calls `mcp__plugin_playwright_playwright__*` reuses
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
     allowed-tools list scoped to `mcp__plugin_playwright_playwright__*`
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
        into `labs/<slug>/images/`, commits on branch
        `dewain/fix-<slug>-content-audit` (creating the branch from `main`
        if needed), pushes, and opens a PR titled
        `<slug>: fix audit findings from #<issue-number>` with body
        `Closes #<issue-number>`.
     3. If an open PR already exists on that branch, append commits to it
        rather than opening a duplicate.
     4. If screenshots were refreshed and an open fix-PR already exists
        for the slug, invoke `mcs-lab-pr-appender` (sub-skill) with
        `model: <execution.model.resolved.pr_appender>`.
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

1. Close the browser (`mcp__plugin_playwright_playwright__browser_close`).
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
