---
name: mcs-lab-builder
description: |
  Interactively BUILD a new Microsoft Copilot Studio lab for the mcs-labs repo, end-to-end. Get a workshop test account, drive Playwright to the Copilot Studio Home page, then capture a lab step-by-step — writing instructions, tips, and screenshots and confirming each step with the user — assemble it into a sibling-formatted `labs/<slug>/README.md`, re-run the finished lab through the existing audit engine as a quality gate, and open a PR on the active instance's lab repo (microsoft/mcs-labs by default). Event/workshop-agnostic: a lab is built and tested standalone; event attachment is optional. Use when the user says "build a new lab", "author a lab", or invokes `/build-lab`.
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - Bash(gh issue list:*)
  - Bash(gh issue create:*)
  - Bash(gh issue view:*)
  - Bash(gh issue edit:*)
  - Bash(gh issue comment:*)
  - Bash(gh pr list:*)
  - Bash(gh auth status:*)
  - Bash(gh repo view:*)
  - Bash(gh pr create:*)
  - Bash(gh pr comment:*)
  - Bash(git*)
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

# mcs-lab-builder (orchestration skill)

You are **building a brand-new lab** for the active instance's lab repo (`{repo}`, e.g. `microsoft/mcs-labs`). You run a real browser through the lab you are authoring, capture screenshots and write the instructions as you go, confirm every step with the user, assemble a complete sibling-formatted lab, gate it through the existing audit engine, and open a PR. This is the authoring counterpart to `mcs-lab-auditor` — it reuses that skill's account flow, Playwright cookbook, judge, and finding schema, and adds an interactive authoring loop on top.

**Event/workshop-agnostic — core principle.** A lab is built and tested as a standalone lab. It is registered with `section` / `journeys` / `order` (all event-independent). Attaching it to an event (bootcamp, MCS-in-a-Day, a build-a-thon, Azure AI workshop, …) is an OPTIONAL, separate choice offered in B3 and read dynamically from `lab-config.yml`. Never hardcode bootcamp.

This file is the orchestrator. It reuses the auditor's reference docs and adds its own. Load what you need; don't keep all of them in context at once.

**Reused from `skills/mcs-lab-auditor/references/` (read these in place — do not copy):**
- `playwright-cookbook.md` — portal sign-in flow, the Welcome-to-Copilot-Studio modal handler, scene-boundary auth probe, the tool-mapping table per step kind, known quirks. Used by B2 and B4.
- `workshop-redemption.md` / `workshop-redemption-chatbot.md` — workshop-code redemption + first-login password change + DPAPI caching. Used by B1.
- `lab-parser-spec.md` — markdown → step tree (use_cases → scenes → steps + step ids). The ledger uses the same id grammar; B6 parses the built lab with it.
- `llm-judge-prompts.md` / `finding-schema.md` — the per-step judge + finding record. B6 reuses both unchanged.

**New, in `skills/mcs-lab-builder/references/`:**
- `build-session-spec.md` — the per-step capture loop, the `runtime/builds/<build-id>/` workspace + ledger schema, the ledger→README renderer, the kebab screenshot-naming rule, resume semantics.
- `lab-authoring-template.md` — the canonical new-lab README skeleton (section order, Lab Details table, Use Cases Covered table, callout + image conventions). B5 renders against this.
- `lab-registration-spec.md` — runtime detection of the mcs-labs registration mechanism, the `lab-config.yml` / `_data/lab-config.yml` entry shape, the order-number rule, optional event attachment, and the screenshot-promotion step.

**New sub-skill:** `mcs-lab-new-lab-pr` — opens the PR for the finished lab (B7). Do NOT reuse `mcs-lab-fix-pr-filer` (that skill patches an existing lab from findings diffs).

## Build lifecycle (phases B0–B7)

### B0 — Hard preflight (no browser yet)

1. **Orchestrator-is-Opus assertion (MANDATORY).** Same rule as the auditor: the build orchestrator REQUIRES Opus (long-form state tracking across a multi-step build, recovery patterns, and prose generation all degrade badly on lower tiers). Detect the session model from the env line `You are powered by the model named Opus X.Y`. On non-Opus, halt with:
   ```
   ERROR: mcs-lab-builder requires the orchestrator to run on Opus.
   Current session model: <detected model>
   Switch to Opus (/model in Claude Code) and re-run /build-lab.
   Sub-agents spawned by the B6 audit gate can still run on lower tiers (--model-preset).
   ```
   Do not proceed on a non-Opus session.

2. **Resolve the plugin directory and the mcs-labs repo path.** The plugin dir is `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor`. The mcs-labs repo path is **NOT fixed** — the repo moved out of `C:\Users\dewainr\mcs-labs`. Resolve it by trying, in order, the candidates in `judge-config.yml.build.registration.mcs_labs_repo_path_candidates` (default: `C:\Users\dewainr\Projects\mcs-labs`, then `C:\Users\dewainr\mcs-labs`). The first whose `_data/lab-config.yml` exists wins. If none exist, halt: `ERROR: could not locate the mcs-labs repo. Set build.registration.mcs_labs_repo_path_candidates in config/judge-config.yml.` Record the resolved path as `manifest.mcs_labs_repo`.

3. **Load configs:** `runtime/account/active-portal.yml`, `config/judge-config.yml` (including the new `build:` block). If the `build:` block is absent, use the documented defaults from `references/build-session-spec.md`.

4. **Check `gh` auth + repo permission** (needed for B7; verify early so a long build doesn't end at a permission wall):
   ```
   gh auth status
   gh repo view {repo} --json viewerPermission
   ```
   Halt on failure unless `--no-pr` is set (then warn and continue — the build still produces a draft).

5. **Detect the registration mechanism** (per `references/lab-registration-spec.md` §1). Glob the resolved mcs-labs repo for a root `lab-config.yml` and a `Generate-Labs.ps1` generator.
   - **Both present** → "generate" mode: B6/B7 edit the root `lab-config.yml` and run the generator.
   - **Absent (current reality)** → "direct-write" mode: B6/B7 write `labs/<slug>/README.md` + `_labs/<slug>.md` + the `_data/lab-config.yml` entry directly (the pattern `mcs-lab-fix-pr-filer` already uses for `_labs/`).
   - **Ambiguous** (e.g. a root config but no generator) → record it and, at B6, surface the ambiguity via `AskUserQuestion` rather than guessing.
   Record the detected mode as `manifest.registration_mode`.

6. **Create the build workspace** (`references/build-session-spec.md` §workspace). Generate a build id the same way the auditor generates run ids:
   ```
   $build_id = (Get-Date -Format "yyyy-MM-ddTHHmmZ") + "-" + (-join ((1..4) | % { '{0:x}' -f (Get-Random -Maximum 16) }))
   ```
   Initialize `runtime/builds/<build-id>/manifest.yml` (status `building`, phase cursor `B0`). Under `--resume <build-id>`, skip creation and load the existing workspace instead (see Resume below).

### B1 — Account + interaction-mode interview (MANDATORY)

Two `AskUserQuestion` calls, each skipped only when a CLI flag already answered it.

**Q-Account — which test account?** Use the auditor's Phase 1.5 Q1 **verbatim**: the same cache-state-conditional option matrix (use cached `<user_id>` / redeem a new user from the cached code / redeem a new workshop code / abort), governed by `judge-config.yml.execution.account_prompt_mode` (override via `--account-prompt`). On any redemption path, follow `references/workshop-redemption.md` or `…-chatbot.md` per `runtime/account/active-portal.yml.portal_kind`, including first-login password change and DPAPI caching of the new password + workshop code + `account.meta.json`. Reuse it exactly — do not re-implement account handling here.

**Q-Mode — how do you want to build?** Skip if `--mode` was passed. `AskUserQuestion`:
- Question: `How do you want to drive the build?`
- Options:
  - `[Recommended] Guided — I'll dictate each step` — description: `You tell me the next step and any key consideration/tip. I execute it in the browser, capture a screenshot, write the instruction, and confirm with you before moving on.`
  - `Scenario — I'll describe it, you attempt it` — description: `You give me the scenario and details up front. I propose ONE step at a time, you confirm before I execute, and I capture/write it the same way. Same per-step confirmation as guided.`

Record `manifest.mode: guided | scenario`.

### B2 — Navigate to the Copilot Studio Home page

Using the chosen account (browser signed in by B1's redemption flow, or sign in now with cached credentials per `playwright-cookbook.md` §sign-in flow):
1. Navigate to `runtime/account/active-portal.yml.auth_probe_url` (default `https://copilotstudio.microsoft.com/`).
2. Run the **Welcome-to-Copilot-Studio modal handler** from `playwright-cookbook.md` (idempotent — forces United States region, declines marketing, clicks Get Started).
3. `_browser_snapshot` to confirm the Copilot Studio Home / Agents left-nav is visible. If you instead land on `login.microsoftonline.com`, the cached session is dead → run the redemption/sign-in path or halt with the auditor's `auth_expired` guidance.

The browser session established here is reused across the whole build (and by B6's gate subagents — same shared-MCP-browser handoff the auditor relies on).

### B3 — Name + scaffold

1. **Lab name → slug.** Use arg 1 if provided, else `AskUserQuestion` (free-text "Other") for the lab name. Slugify: lowercase, non-alphanumerics → single hyphens, trim. Show the derived `<slug>` and confirm.
2. **Collision check.** Reject if `<slug>` already appears as an `id:` in `_data/lab-config.yml` OR `labs/<slug>/` exists on disk. On collision, re-ask for a different name. **Never overwrite an existing lab** — that is the audit/fix path, not the build path.
3. **Capture lab metadata** for registration (`AskUserQuestion`, with sensible suggested options): `title` (full human title), `difficulty` (Beginner/Intermediate/Advanced), `duration` (minutes), `section` (core/intermediate/advanced/specialized/optional), `journeys` (quick-start/business-user/developer/autonomous-ai — multi-select). Pick `order` per the gap rule in `references/lab-registration-spec.md` and surface it for confirmation.
4. **Optional event attachment (event-agnostic).** Ask whether to attach the lab to any event(s)/workshop(s). Read the available events dynamically from `_data/lab-config.yml` event configs — present them as options plus "None (standalone lab)" as the default-recommended first option and an "Other (type the key)" escape. Record the chosen events (possibly empty) as `manifest.events`. **Do not** default to bootcamp or any specific event.
5. **Seed the workspace.** Create `runtime/builds/<build-id>/draft/README.md` from `references/lab-authoring-template.md` with the captured metadata filled into the Lab Details table and title. Create `draft/images/`. Write the metadata into `manifest.yml`.

### B3.5 — File the new-lab proposal issue (MANDATORY when PR target is reachable)

As soon as the lab is named and scaffolded, open a tracking issue on the active instance's repo (`{repo}`) so the new lab is visible to the team as an **In Progress** proposal for the whole duration of the build. Governed by `judge-config.yml.build.proposal_issue` (defaults in `references/build-session-spec.md`).

1. **Skip / defer conditions.** Skip only if `build.proposal_issue.enabled: false`, or if `gh` is unauthenticated / lacks issue-create permission on the repo (then warn and continue — the build still produces a draft; record `proposal_issue.status: skipped`). On `--resume`, **reuse** the issue recorded in `manifest.proposal_issue` — never open a second one.
2. **Dedup.** Before creating, query for an existing open proposal for this slug:
   ```
   gh issue list --repo {repo} --state open \
     --label "type: new-lab" --search "<slug> in:title" \
     --json number,title,url --limit 5
   ```
   If a match exists, reuse it (record it in the manifest) instead of opening a duplicate.
3. **Create the issue** with the repo's existing taxonomy labels (do not invent new ones):
   ```
   gh issue create --repo {repo} \
     --title "<build.proposal_issue.title_pattern>"   # default: "New lab proposal: {title} ({slug})"
     --label "type: new-lab" \
     --label "status: in-progress" \
     --body-file "runtime/builds/<build-id>/proposal-issue.md"
   ```
   Render `proposal-issue.md` first: the lab title + slug, a one-line summary of what it teaches (from the B3 metadata / scenario), the captured metadata (section / difficulty / duration / journeys, and any optional event attachment), the interaction mode, the build-id, and a line stating **Status: In Progress — being authored interactively by `mcs-lab-builder`.** Include a stable marker comment `<!-- mcs-lab-builder:proposal slug=<slug> -->` so re-runs and the PR step can find it.
4. **Record** the result in `manifest.yml` under `proposal_issue: { number, url, status: open, labels: [...] }`. Print the issue URL to the user.

The labels come from `build.proposal_issue.labels` (default `["type: new-lab", "status: in-progress"]`). These match the labels defined on `{repo}` (the mcs-labs taxonomy by default) (`type: new-lab` = "Brand new lab proposal"; `status: in-progress` = "Someone is actively working on this"). If a configured label does not exist on the repo, file with the labels that do and warn about the missing one rather than failing the build.

> **This is the one GitHub write build mode makes before B7, and it is intentional.** It is separate from the B6 audit gate, which still writes nothing to GitHub (`build.audit_gate.suppress_github_writes`). The proposal issue tracks the *lab*, not findings.

### B4 — Per-step interactive capture loop

This is the core authoring loop. It runs per scene, scenes grouped under use cases, until the user ends the lab. Both modes confirm **every** step before checkpoint. The precise loop, the ledger schema, and the `render_step_markdown` / `propose_next_step` procedures live in `references/build-session-spec.md` §capture-loop. Summary:

```
loop:
  1. SNAPSHOT   browser_snapshot -> snapshots/<step-id>-before.yml
  2. INTENT     guided:   user dictates the next step + any key consideration/tip
                scenario: AI proposes ONE step from the scenario + snap_before; user confirms BEFORE execute
  3. EXECUTE    drive Playwright per playwright-cookbook §tool-mapping (snapshot refs only, never raw CSS).
                connection-class failures follow judge-config execution.network_retry_count before pausing.
                un-completable step -> recovery menu (see below); never silently skip.
  4. CAPTURE    browser_take_screenshot -> draft/images/<kebab>.png ; snapshot -> snapshots/<step-id>-after.yml
  5. WRITE      render the numbered instruction markdown + > [!TIP]/[!IMPORTANT]/[!WARNING] callouts
                + the ![alt](images/<kebab>.png) reference (kebab rule in build-session-spec §screenshots)
  6. CONFIRM    AskUserQuestion: confirm | redo-step | re-screenshot | edit-prose | split-step | end-scene | end-lab
  7. CHECKPOINT on confirm: append the step record to ledger.yml + flush session-state.yml (advance cursor).
                on redo/re-screenshot/edit/split: loop back without advancing.
                on end-scene: close scene, ask next scene heading or end-use-case.
                on end-lab: break to B5.
```

**Scene/UC boundaries.** Ask the user for a use-case title at the start of each use case and a scene heading (`####`) at the start of each scene, matching the lab structure. At each new scene/UC boundary, run the `playwright-cookbook.md` scene-boundary auth probe; on expiry, flush `session-state.yml` and halt with resume guidance (no silent re-auth).

**Un-completable step recovery** (`AskUserQuestion`): (a) you perform the action manually in the shared browser, then I screenshot the result and continue; (b) reword/split the step; (c) skip with a `> [!NOTE]` placeholder flagged for human follow-up; (d) abort to resume later via `--resume`. Never drop a step silently.

### B5 — Prose + doc assembly

Render the full `draft/README.md` from `ledger.yml` using `references/lab-authoring-template.md` and the renderer in `build-session-spec.md` §renderer:
- Walk the ledger grouped by use case → scene → ordinal. Each ledger step → one numbered list item under its `#### <scene_heading>`, with `hints[]` as `> [!KIND]` callouts and `image` as `![alt](images/<file>)`.
- Prepend the context sections in sibling order: title + one-liner → Lab Details table → Table of Contents → Introduction → Core Concepts Overview → Documentation links → Prerequisites → Summary of Targets → Use Cases Covered (table auto-built from the UC list) → Instructions by Use Case → Summary of Learnings → Conclusions & Recommendations.
- Generate the prose context sections (Why/Introduction/Core Concepts/Targets/Learnings/Conclusions) from the scenario + ledger so the lab reads like a sibling. Surface the assembled README to the user for a read-through; accept edits before the gate.

### B6 — End-to-end audit gate (reuse the engine, suppress all GitHub writes)

The lab must be a real `_labs/<slug>.md` for the auditor's parser to consume. Per `references/lab-registration-spec.md`:
1. **Stage** `draft/README.md` → `labs/<slug>/README.md` and promote `draft/images/*` → `labs/<slug>/images/` (same-name copy; the README already references `images/<file>`).
2. **Register** the lab via the detected mechanism (B0 step 5): generate mode → edit root `lab-config.yml` + run `Generate-Labs.ps1`; direct-write mode → write the `_data/lab-config.yml` entry and materialize `_labs/<slug>.md` directly (frontmatter + body). If `manifest.registration_mode` is ambiguous or the toolchain is unavailable, `AskUserQuestion` how to proceed or halt with guidance (the draft is safe under `runtime/builds/<build-id>/`).
3. **Run the audit engine against `<slug>` with ALL GitHub writes suppressed.** Drive the auditor's Phase-2 per-UC judge loop (spawn per-UC subagents with the resolved `--model-preset`; the browser is already signed in from B2). Write findings to `runtime/builds/<build-id>/audit/findings.json`. Honor `judge-config.yml.build.audit_gate.suppress_github_writes: true` — **never** invoke `mcs-lab-issue-filer`, `mcs-lab-fix-pr-filer`, or `mcs-lab-pr-appender` in this phase.
4. **Consume findings in-loop.** For every finding whose `outcome` ∈ `build.audit_gate.fail_on` (default `[broken, unclear]`) at confidence ≥ `confidence.min_to_include_in_issue`, surface it to the user as a fix task and loop back into B4 for that `step_id` (re-record / re-screenshot / re-word). `cannot_verify` and below-threshold findings are informational only. Re-run the gate after fixes. The gate **passes** when zero above-threshold `broken`/`unclear` findings remain. Cap iterations at `build.audit_gate.max_loops` (default 5); if exhausted, `AskUserQuestion`: keep iterating, open a **draft** PR listing the unresolved findings, or abort.

### B7 — Generate + PR

Skipped entirely under `--no-pr` (print the registration steps + draft location instead; the proposal issue stays open as **In Progress** for a human to pick up). Otherwise invoke the **`mcs-lab-new-lab-pr`** sub-skill with: `build-id`, resolved `mcs_labs_repo`, `slug`, the staged files, the registration mode, the optional `events`, and the **`proposal_issue.number`** from `manifest.yml`. It branches off fresh `origin/main`, commits the new-lab files + registration changes (+ generator output if generate mode) in one commit, and opens the PR (`<slug>: add new lab`). When a proposal issue exists, the PR body links it per `build.proposal_issue.link_pr_with` (default `Closes`, so merging the lab auto-closes the proposal). Record `pr_url` in `manifest.yml`.

### Wrap-up
1. Close the browser (`mcp__plugin_playwright_playwright__browser_close`).
2. Print a summary: slug, build-id, gate result (loops run, residual findings), PR URL (or "draft saved, --no-pr").
3. Write final `manifest.yml` (status `pr_filed` | `draft_only` | `aborted`).

## Resume flow (`--resume <build-id>`)

1. Load `runtime/builds/<build-id>/{manifest.yml, session-state.yml, ledger.yml}`. Inherit `mode`, `slug`, metadata, `events`, `registration_mode`, `mcs_labs_repo`, and `proposal_issue` (the existing In-Progress issue is reused — B3.5 never opens a second one on resume).
2. Re-run B0 preflight (Opus assert, path + mechanism re-detect, configs) and B1 **account** question (re-prompt unless `account_prompt_mode` permits skipping AND cache is unexpired — a build after cache expiry needs fresh credentials).
3. B2 navigate-home, re-running the idempotent Welcome handler, returning to `session-state.yml.browser_left_at.url`.
4. Resume B4 at `session-state.yml.last_confirmed_step_id + 1` in the recorded `current_uc` / `current_scene`. Confirmed steps in `ledger.yml` (and their on-disk screenshots) are preserved.

## Important rules

- **Event/workshop-agnostic.** Never assume bootcamp. Read events from `lab-config.yml`; standalone is the default.
- **Resolve the mcs-labs path; never hardcode `C:\Users\dewainr\mcs-labs`.** The repo moved to `…\Projects\mcs-labs`. Use the B0 resolution.
- **Touch the mcs-labs working tree only in B6/B7.** All B0–B5 artifacts live under `runtime/builds/` (gitignored). Under `--no-pr` or any halt, the mcs-labs tree is not modified.
- **Build mode makes exactly two GitHub writes: the B3.5 proposal issue and the B7 new-lab PR.** Nothing else. The B6 audit gate files nothing on GitHub — its findings feed the build loop, not `mcs-lab-issue-filer`.
- **Never overwrite an existing lab.** Collision → new name.
- **Never log the workshop password.** DPAPI handling is inherited from the auditor; only `workshop_code_hint` (first 4 chars) may appear.
- **Halt loudly on auth_expired.** No silent re-auth mid-build; the ledger is the durable record, so flush and resume.
- **No `Co-Authored-By: Claude` / AI attribution** in commits or PRs (user preference).
- **Confirm every step.** Both modes checkpoint per step. Never batch-author a scene without per-step confirmation.

## What success looks like

- `runtime/builds/<build-id>/` holds `manifest.yml`, `ledger.yml`, `draft/README.md`, `draft/images/*`, `proposal-issue.md`, and `audit/findings.json`.
- A **proposal issue** is open on the active instance's repo (`{repo}`) labeled `type: new-lab` + `status: in-progress`, opened at B3.5 and recorded in `manifest.proposal_issue`.
- The built lab passed the audit gate with zero above-threshold `broken`/`unclear` findings (or the user accepted a draft PR with residuals listed).
- A PR on the active instance's repo (`{repo}`) adds `labs/<slug>/README.md` + `images/` + the registration entry (+ `_labs/<slug>.md` and `_data/lab-config.yml`), branch `{branch_prefix}/new-lab-<slug>-<build-id>`, linking the proposal issue (`Closes #<n>`), with no AI attribution.
- One-line chat summary: `Built <slug> in <duration>. Proposal issue #<n> (In Progress). Gate passed after <N> fix loop(s). PR: <url>.`
