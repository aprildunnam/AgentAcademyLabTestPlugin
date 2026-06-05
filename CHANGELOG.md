# Changelog

All notable changes to `mcs-lab-auditor` are documented here.

This project adheres to [Semantic Versioning](https://semver.org/). The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.6.0] - 2026-06-05

### Added

- **Events AND workshops are both first-class audit scopes.** The mcs-labs repo split curated scopes into two Jekyll collections — `_events/` (formal: bootcamp, the buildathons) and `_workshops/` (on-demand: Azure AI workshop, MCS in a Day, **Agent in a Day**, the Agent Academy series). The auditor now enumerates scope from these collections instead of the legacy `lab-config.yml.event_configs` table, which had drifted out of sync (it lacked the newer workshops and still listed an obsolete `mcs-in-a-day-v2`). The Phase 1.5 Q3/Q3a picker labels each option `[Event]` / `[Workshop]`, and `/audit-event --event <id>` accepts the id of either. New `scripts/Get-EventCatalog.ps1` reads each scope's front-matter `labs:` list and tags `external` scopes (e.g. Agent Academy, whose labs live in another repo) as **not auditable** so they're listed but never driven.
- **Plugin self-version check runs first (`scripts/Test-PluginVersion.ps1`).** Before any audit work, the orchestrator compares the local `plugin.json` version to the version published on `origin/main` of `microsoft/BootcampLabTestPlugin` and warns (non-blocking) when an update is available — so audits don't silently run on a stale copy. Wired into every audit/build command's pre-flight as a new Phase-1 step 1.
- **Dynamic mcs-labs repo resolution with auto-clone + always-latest (`scripts/Resolve-LabRepo.ps1`).** The repo location is resolved at run start (via `$env:MCS_LABS_REPO`, the `judge-config.yml` candidates, or a built-in list), **clones `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs` when no local copy exists**, and fast-forwards it to `origin/main` so every audit compares against current lab content.

### Changed

- **All hard-coded machine paths removed from audit mode.** The `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor` plugin path in every command pre-flight and the `~/.claude/...` SKILL.md read paths are now `$env:CLAUDE_PLUGIN_ROOT`; the `C:\Users\dewainr\mcs-labs` repo path is replaced by `Resolve-LabRepo.ps1`. This completes the follow-up noted in 0.4.0 ("Audit-side commands still carry the legacy hardcoded path"). The plugin now works on any contributor's machine with no per-machine edits.
- **Phase 1 pre-flight renumbered** (orchestrator `SKILL.md`): step 1 self-version check, step 2 Opus assertion, step 3 portable plugin + resolved repo paths, step 6 events+workshops enumeration. Q3/Q3a, the interview-outcome manifest (`scope_type: event | workshop`), and the command prose were updated to match.
- **Version → 0.6.0** across `plugin.json`, `marketplace.json`, and `judge-config.yml.plugin_version`.

### Documentation

- Updated `README.md`, `docs/architecture.md`, `docs/installation.md`, `docs/extending.md`, `docs/troubleshooting.md`, and `docs/design-decisions.md` (new ADR-022 events-vs-workshops source of truth, ADR-023 portable path resolution + self-version check) for the collection-based scope model, the new scripts, and the removal of hard-coded paths.

## [0.5.0] - 2026-06-05

### Added

- **Build mode opens a "new lab proposal" tracking issue (B3.5).** As soon as a new lab is named, `/build-lab` files a GitHub issue on `microsoft/mcs-labs` labeled **`type: new-lab`** ("Brand new lab proposal") + **`status: in-progress`** ("Someone is actively working on this") — the repo's existing label taxonomy, not new labels — so the lab is visible to the team as **In Progress** for the whole build. The issue is deduped per slug (reuses an existing open proposal rather than duplicating), reused on `--resume`, recorded in `manifest.proposal_issue`, and **closed by the final lab PR** (`Closes #<n>`, configurable). Rendered body saved to `runtime/builds/<build-id>/proposal-issue.md`.
- **`build.proposal_issue` config block** in `config/judge-config.yml`: `enabled`, `repo`, `labels`, `title_pattern`, `link_pr_with` (`Closes` | `Refs`). Documented in `skills/mcs-lab-builder/references/build-session-spec.md`.

### Changed

- **Build mode now makes two GitHub writes, both intentional:** the B3.5 proposal issue and the B7 new-lab PR. The B6 audit gate still writes nothing to GitHub (`build.audit_gate.suppress_github_writes`). `mcs-lab-builder` gains `gh issue create/view/edit/comment` permissions; `mcs-lab-new-lab-pr` links the PR to the proposal issue. Updated `commands/build-lab.md`, `skills/mcs-lab-builder/SKILL.md` (B3.5, B7, resume, rules, success), `skills/mcs-lab-new-lab-pr/SKILL.md`, `docs/architecture.md`, `docs/security.md`, `README.md`.
- **Version → 0.5.0** across `plugin.json`, `marketplace.json`, and `judge-config.yml.plugin_version`.

### Documentation

- **Documented build mode across all docs.** PR #35 shipped the `/build-lab` feature but only touched `README.md` + `CHANGELOG.md`. This pass brings the rest of the documentation current:
  - `docs/architecture.md` — new "Build mode (interactive lab authoring)" section with the B0–B7 lifecycle diagram; build-mode write boundary + workspace layout (`runtime/builds/<build-id>/`); corrected the stale "Issues, not PRs" rationale.
  - `docs/design-decisions.md` — ADR-017 (build mode + audit gate), ADR-018 (new-lab PR as a separate sub-skill), ADR-019 (event/workshop-agnostic), ADR-020 (runtime registration detection + mcs-labs path resolution). Renumbered the duplicate ADR-014 ("plugin distribution") to ADR-016 and updated it for marketplace distribution.
  - `docs/installation.md` — `/build-lab` in the command list, PR permission note, and a "Building a new lab" walkthrough.
  - `docs/extending.md` — "Customizing build mode" table; build-mode path resolution note; refreshed the "What NOT to extend" write-path boundary.
  - `docs/security.md` — build mode reuses the same account/DPAPI (no new secrets); added the new-lab PR write path and noted the gate files nothing on GitHub.
  - `docs/troubleshooting.md` — new "Build mode" failure-mode section (path resolution, registration mechanism, gate loops, slug collision, PR permission, resume).
  - `README.md` — two-mode intro, build-mode "How it works", project layout + artifacts + limitations.
  - `docs/mcs-lab-auditor-overview-and-architecture.pdf` — regenerated from `scripts/Build-OverviewPdf.py` (now covers build mode; version → v0.4.0). Note: the prior committed PDF was stale relative to its own script (it embedded custom fonts the current script no longer references), so the regenerated file is smaller and uses the script's base-14 fonts.

## [0.4.0] - 2026-06-04

### Added

- **Interactive lab-building mode** — a second mode alongside auditing. The new `/build-lab` command and `mcs-lab-builder` orchestration skill drive Playwright to the Copilot Studio Home page using the existing workshop account flow, then capture a brand-new lab step-by-step: snapshot → step intent → execute → screenshot → write instruction + tips → confirm → checkpoint. Two interaction modes, both confirming **every** step: **guided** (the user dictates each step) and **scenario** (the user describes the lab up front and the AI proposes one step at a time). The finished lab is assembled into a sibling-formatted `labs/<slug>/README.md`, re-run through the existing audit engine as a quality gate, and shipped as a PR on `microsoft/mcs-labs`.
- **`mcs-lab-builder` skill** (`skills/mcs-lab-builder/SKILL.md`) — Opus-only orchestrator with phases B0 (hard preflight: Opus assert, gh auth, mcs-labs path resolution, registration-mechanism detection) → B1 (account + interaction-mode interview, reusing the auditor's account matrix verbatim) → B2 (navigate to Copilot Studio Home) → B3 (name + slug + collision check + metadata + optional event attachment) → B4 (per-step capture loop) → B5 (ledger → README assembly) → B6 (audit gate) → B7 (PR).
- **`mcs-lab-new-lab-pr` sub-skill** (`skills/mcs-lab-new-lab-pr/SKILL.md`) — opens the new-lab PR on a run-unique branch `dewain/new-lab-{slug}-{build_id}` off fresh `origin/main`, committing the lab folder + registration entry (+ generator output in generate mode) in one commit. Distinct from `mcs-lab-fix-pr-filer` (which patches an existing lab from findings diffs); a new lab is a one-shot PR with no open-PR append path.
- **Three builder reference docs** under `skills/mcs-lab-builder/references/`: `build-session-spec.md` (workspace + ledger schema, the capture-loop pseudocode, kebab screenshot naming, the ledger→README renderer, resume semantics), `lab-authoring-template.md` (the canonical sibling-lab README skeleton + callout/image conventions), and `lab-registration-spec.md` (runtime mechanism detection, the `_data/lab-config.yml` entry shapes, order-number rule, optional event attachment).
- **`build:` config block in `config/judge-config.yml`** — `interaction_mode_default`; `audit_gate.{enabled,fail_on,max_loops,suppress_github_writes}`; `screenshot.image_name_strategy`; `registration.{mcs_labs_repo_path_candidates,root_config_relpath,data_config_relpath,generate_script_relpath,generate_args,order_gap_strategy}`. Plus `issues.new_lab_pr.{pr_branch_pattern,require_same_author}`.
- **Event/workshop-agnostic by design.** Build mode (and its audit gate) is not tied to bootcamp or any single workshop. A lab is built and tested standalone; events are read dynamically from `lab-config.yml` and attaching a built lab to any event(s) is an optional B3 choice — never hardcoded to bootcamp.

### Changed

- **The audit engine gained an internal no-GitHub-writes invocation path** used by the build audit gate (B6): the auditor's Phase-2 per-UC judge loop runs against a freshly-built lab, but findings are consumed in-loop (fed back into the build to fix) instead of routing to `mcs-lab-issue-filer` / `mcs-lab-fix-pr-filer` / `mcs-lab-pr-appender`. Gated by `build.audit_gate.suppress_github_writes`.
- **mcs-labs repo path is now resolved, not hardcoded.** Build mode tries `build.registration.mcs_labs_repo_path_candidates` in order (default `C:\Users\dewainr\Projects\mcs-labs`, then `C:\Users\dewainr\mcs-labs`) — the repo moved out of the old fixed location. (Audit-side commands still carry the legacy hardcoded path; tracked for a follow-up.)
- **`config/judge-config.yml.plugin_version`** corrected from the stale `0.1.0` to `0.4.0`.

### Notes

- The mcs-labs new-lab toolchain documented in that repo's `docs/NEW_LAB_CHECKLIST.md` (root `lab-config.yml` + `Generate-Labs.ps1`) is currently **absent** from `origin/main`; build mode detects this at B0 and falls back to writing `labs/<slug>/README.md` + `_labs/<slug>.md` + the `_data/lab-config.yml` entry directly, halting with guidance if the mechanism is ambiguous.

## [0.3.0] - 2026-06-03

### Added

- **`issues.pr_append.pr_match_head_prefix` config key** (default `dewain/fix-{slug}-content-audit`) — the head-ref **prefix** the fix-PR filer uses to find an existing open PR for a slug regardless of its run-id suffix. Documented in `docs/extending.md`.
- **ADR-015 — Fix-PR per audit run; PR dedup scoped to OPEN PRs only** in `docs/design-decisions.md`. Records the move away from a fixed per-slug branch and a "never open a new PR" rule.

- **`/audit-event` slash command** — generic event-audit entry point. Accepts `--event <key>` to pin one of the events defined in `_data/lab-config.yml.event_configs` (`bootcamp`, `agent-buildathon-1day`, `agent-buildathon-1month`, `azure-ai-workshop`, `mcs-in-a-day`, `mcs-in-a-day-v2`, and anything added later). Without `--event`, the Phase 1.5 run-start interview asks Q3a (event picker) to select interactively. Replaces the implicit "bootcamp is the only event" assumption that previously lived in Phase 1.4.
- **Phase 1.5 Q3a — Event picker.** New interactive question between Q3 (scope) and Q4 (one-lab picker). Reads `event_configs` dynamically and offers the 3 most-used events plus an "Other (type the key)" free-text escape valve. Validates typed event keys against `event_configs.*`.
- **Phase 1.5 Q4 picker now ranges over the full all-labs catalog**, not just the bootcamp event's `slugs[]`. Picker source is `lab_metadata.*.id`. Two-step grouping is by `section` (Core / Intermediate / Advanced & specialized / Other free-text), preserving the existing `AskUserQuestion` 2-step pattern. Section labels and member counts are computed at interview time from `lab_metadata`.
- **`/audit-bootcamp` clarified as a thin shortcut** for `/audit-event --event bootcamp` — Q3 and Q3a auto-skip; Q4 only fires if the user explicitly elected single-lab scope. Existing behavior preserved; no breaking change for users still on `/audit-bootcamp`.
- **Cross-lab consistency check (Phase 1.7 step 1a).** New static-phase fan-in pass that groups scenes across labs by shape hash and emits drift findings for divergent identifier tokens (e.g. `Address 1: State/Province` vs `Address1: State or Providence` in sibling labs). Findings are severity `low` and tagged `flags.cross_lab_drift: true`. Algorithm documented in `skills/mcs-lab-auditor/references/cross-lab-consistency.md`. Motivated by the live discovery between `mcs-multi-agent` UC3 and `mcs-orchestration` UC1 during the 2026-05-26 audit cycle.
- **`scene-fingerprints.json` sidecar per lab static run.** Emitted alongside `findings-static.json`. Contains scene-by-scene shape hash + identifier tokens + line numbers, feeding both same-run and cross-run cross-lab comparisons.
- **`consistency.*` config block in `config/judge-config.yml`.** New keys: `cross_lab_enabled` (default `true`), `cross_lab_similarity_threshold` (`0.85`), `cross_lab_borderline_floor`, `cross_lab_high_confidence_floor`, `cross_lab_min_cluster_size`.
- **`flags.cross_lab_drift` registered in `finding-schema.md`.** Rendered under a dedicated "Cross-lab consistency" section in issue bodies (separate from the regular "Static analysis" section).
- **`docs/mcs-lab-auditor-overview-and-architecture.pdf`** — single-document overview, architecture deep-dive, and full installation guide. Includes a comparison to generic Computer-Use Agent (CUA) approaches and why this plugin's structured pipeline produces outcomes a pure CUA cannot.

### Changed

- **Fix-PRs are now opened per audit run on a run-unique branch, and PR dedup is scoped to OPEN PRs only.** Previously `mcs-lab-fix-pr-filer` keyed everything to a fixed per-slug branch `dewain/fix-{slug}-content-audit` and the docs declared "one PR per lab, never open a new PR." That broke once a prior fix-PR was **merged** — new findings had nowhere clean to land. Now: if an **open** fix-PR for the lab exists (same-author, mergeable), the run's commit is **appended** to it; otherwise a **new** PR is opened on a run-unique branch `dewain/fix-{slug}-content-audit-{run_id}`. A merged or closed prior PR never blocks a new one. `issues.pr_append.pr_branch_pattern` default changed to include the `{run_id}` token. Affects `skills/mcs-lab-fix-pr-filer/SKILL.md`, `skills/mcs-lab-auditor/SKILL.md` (Phase 2 step 6), `config/judge-config.yml`, `README.md`, `docs/architecture.md` (sequence diagram now shows the fix-PR filer), `docs/design-decisions.md` (ADR-001 status + ADR-015), and `docs/extending.md`.
- **Phase 1.4 enumeration** now reads `event_configs` (events map) AND `lab_metadata` (all-labs catalog) instead of hardcoding `bootcamp_lab_orders`. The active event is resolved from the entry-point command and CLI flags (`/audit-bootcamp` → `bootcamp`, `/audit-event --event <key>` → `<key>`, `/audit-event` without `--event` → Q3a picker, `/audit-lab` → no driving event).
- **`manifest.yml.interview`** now records `event: <event-key|null>` alongside `scope: event|one` and `scope_labs[]`. Resume runs inherit the prior event for the relevant interview short-circuits.
- **README, `docs/architecture.md`, `docs/installation.md`, `docs/extending.md`** updated to reflect the event-aware entry points and the cross-lab consistency pass. The architecture doc has a new "Cross-lab consistency fan-in" section with a Mermaid diagram.

## [0.2.1] - 2026-05-25

### Fixed

- **Cached plugin v0.2.0 was missing `scripts/Get-PathOrFallback.ps1`** so every `/audit-*` slash command failed at preflight on Windows with `'<path>\scripts\Get-PathOrFallback.ps1' is not recognized as the name of a script file`. The script was added in commit 58bda9819cc18290bf03f01b0c399247c3a123fb (PR #22) but was not part of the published v0.2.0 cache package. Resolves microsoft/BootcampLabTestPlugin#24.
- **Version inconsistency** between `.claude-plugin/plugin.json` (`0.2.0`) and `.claude-plugin/marketplace.json` (`0.1.0`). Marketplace entry now matches the plugin entry going forward.

### Changed

- Bump to `0.2.1` for the bundling fix above.



- **`lab-parser-spec.md` §1 — Front-matter field authority table.** Documents which front-matter fields have body-table counterparts that MUST match (`duration` ↔ Lab Details `Duration` column; `difficulty` ↔ `Level` column) and which look related but describe independent axes (`journeys` is a site-nav grouping from `_data/lab-config.yml`; `Persona` is a free-text Power Platform role label — they are not the same field). Static-analysis subagents now have an explicit list of cross-field mismatches to drop instead of flagging. Resolves a false-positive class observed in the `mcs-governance` static run where a `journeys: [business-user, developer]` vs `Persona: Maker / Admin` mismatch was flagged at 0.60 confidence (correctly skipped, but should not have surfaced at all).
- The same section makes the agenda-is-authoritative rule for `duration` explicit: when front-matter `duration:` and the Lab Details `Duration` column disagree, align the front-matter to the body table, not the reverse.

### Added

- **Phase 1.5 — Run-start interview** (expanded from the old account-only prompt) in `mcs-lab-auditor/SKILL.md`. The orchestrator now walks the user through up to four `AskUserQuestion` calls before any destructive work: (Q1) account — use cached / redeem new / abort; (Q2) phase mix — both / static-only / interactive-only; (Q3) scope — all labs / one lab; (Q4) one-lab picker — two-step group→lab navigation that fits inside `AskUserQuestion`'s 2–4-option limit. Each question is skipped only when a CLI flag already provided the answer. Interview outcomes are recorded under `manifest.yml.interview`.
- New CLI flag **`--interactive-only`** on `/audit-bootcamp` and `/audit-lab`. Skips the static fan-out and assumes a prior run produced `findings-static.json` per lab. Mirrors the existing `--static-only` flag. Interview short-circuits Q2 when either flag is present.
- **`/audit-lab` slug is now optional** — when omitted, the run-start interview's Q4 lab picker decides which slug to audit. Lets the user invoke `/audit-lab` with no arguments and pick interactively.
- **Per-Use-Case subagent dispatch in Phase 2** (`mcs-lab-auditor/SKILL.md`). Replaces the prior inline per-step loop. The orchestrator now slices `steps.json` into `uc-<N>-steps.json` per use case and spawns one subagent per UC, run serially within a lab (UCs share tenant artifacts and must execute in order). The orchestrator only ever sees each subagent's return summary (status, finding counts, state-file path), keeping its conversation context bounded regardless of step count. Granularity rationale documented inline.
- **Shared MCP browser process** as the per-UC handoff mechanism. The orchestrator signs in once in Phase 1.5; the Playwright MCP server keeps the browser process alive across subagent boundaries so each UC subagent reuses the same signed-in session without re-auth or auth-state export/import.
- **`uc-<N>-state.yml`** per Use Case under `runs/<run-id>/labs/<slug>/`. Each UC subagent writes its `ctx_vars` (agent names, topic names, knowledge URLs created during that UC), `browser_left_at` (URL + last scene completed), `findings_count`, and `status: complete|error|partial`. Subsequent UCs read all prior UC state files and merge `ctx_vars` into their per-step judge `CTX_VARS` input, so the judge knows artifact names from earlier UCs when evaluating later ones.
- **Snapshot-to-disk default for per-UC subagents.** Spawn prompt instructs subagents to use `_browser_snapshot({filename: "snapshots/<step-id>-before.yml"})` instead of returning snapshots inline — single biggest context-saver for the subagent itself.
- **UC-level resume granularity.** `--resume <run-id>` now restarts an interrupted lab at the first UC missing a `uc-<N>-state.yml` file (not at the last completed scene). Completed UCs' findings are preserved; partial UCs re-run with their judge marking already-existing artifacts as `cannot_verify` rather than `broken`.
- **Phase 1.4 — Existing-state probe** in `mcs-lab-auditor/SKILL.md`. Before any Playwright work, the orchestrator now runs `gh issue list` + `gh pr list` for every planned slug and writes `runs/<run-id>/existing-state.yml`. Every per-lab disposition step consults this file, so we never re-create an issue or PR that's already open.
- **Loose-match dedup query** in `mcs-lab-issue-filer/SKILL.md` §4. In addition to the strict `lab-audit + lab:<slug>` label query, the filer now also issues a title-substring query (`{slug} in:title`) so older issues that pre-date the per-slug label still register as duplicates.
- **Finding-level fingerprint dedup** in `mcs-lab-issue-filer/SKILL.md` §6a. Every rendered finding now carries an HTML comment marker (`<!-- finding:fp:<12-char-hex> -->`). Before commenting on an existing issue, the filer extracts all fingerprints already present in the body + every prior comment and drops any new finding that matches. If everything is a duplicate, no comment is posted and the disposition is recorded as `skipped_no_new_findings`.
- **Per-slug label backfill** — when commenting, the filer now adds the `lab:<slug>` label to issues that pre-date the labeling convention, so future strict-query dedup matches without needing the loose query.
- **`mcs-lab-pr-appender` sub-skill** (new) — narrow carve-out from the "issues only" rule. **On by default.** Fires whenever (a) Phase 1.4 found an open fix-PR for the slug AND (b) the run produced refreshed screenshot files. The sub-skill checks out the PR branch, replaces matched image files in place under `labs/<slug>/images/`, commits with a `chore({slug}): refresh screenshots from audit {run_id}` message, and pushes. Screenshot files only; same-author only; mergeable PRs only; no force-push; no `Co-Authored-By: Claude` trailer. Suppress with `--no-update-screenshots` / `--no-append-to-pr` (CLI) or `issues.pr_append.enabled_by_default: false` (config).
- **`references/pr-append-flow.md`** in the orchestrator references — explains when and why the carve-out fires, with the full guardrail list and the `skipped_reason` taxonomy.
- New CLI opt-out flag **`--no-update-screenshots`** (alias `--no-append-to-pr`) on `/audit-bootcamp` and `/audit-lab`. The legacy positive flags (`--update-screenshots`, `--append-to-pr`) are still accepted as no-ops.
- New config block `issues.pr_append` in `config/judge-config.yml` (default `enabled_by_default: true` — screenshot refresh runs on every audit by default; opt out per-run with the CLI flag or globally via this config).
- New config block `existing_state` in `config/judge-config.yml`.
- New config flags: `issues.dedupe_loose_title_match`, `issues.dedupe_by_fingerprint`, `issues.on_duplicate_all_covered`, `issues.backfill_per_slug_label`.
- **Interactive-phase enforcement.** New
  `judge-config.yml.execution.require_interactive_phase` (default `true`).
  When `true`, the orchestrator MUST run Phase 2 against the signed-in
  training account — static analysis alone catches typos, broken links, and
  missing images, but it does not catch UI drift in the live product.
  Opt out per run with `--static-only` on `/audit-bootcamp` or `/audit-lab`;
  the skipped-interactive choice is recorded in the run manifest as
  `execution.skipped_interactive: true, reason: <flag|config>` so future
  readers know the audit didn't exercise the live UI.
- **Always-on run-start account prompt.** New
  `judge-config.yml.execution.account_prompt_mode` (default `always`). Other
  modes: `only_if_expired`, `only_if_missing`. The default forces Phase 1.5
  to ask "use cached vs. redeem new" every fresh run regardless of cache
  freshness — the user's safety net against running against the wrong
  tenant. `--resume` re-prompts unless the mode permits skipping AND the
  cached `expires_at` is still in the future.
- **Connection-error retry policy.** New
  `judge-config.yml.execution.network_retry_count` (default `3`),
  `network_retry_backoff_seconds` (default `[5, 10, 20]`), and
  `network_wait_seconds` (default `120`). Connection failures (DNS, ERR_*,
  repeated navigation timeouts) retry up to the cap, then halt the lab and
  prompt the user via `AskUserQuestion` with four options:
  retry now / wait-and-retry / skip this lab / abort the run. Connection
  failures are NEVER recorded as lab findings — they're environment
  issues, not lab issues.
- **`--static-only` flag** on `/audit-bootcamp` and `/audit-lab` for the
  opt-out path described above.
- **`--account-prompt <mode>` flag** on both commands to override
  `account_prompt_mode` for one run without editing config.
- **Fan-out execution for the bootcamp audit.** `judge-config.yml` now declares
  `execution.fanout_concurrency` (cap on parallel interactive UI passes per
  training account) and `execution.static_fanout_concurrency` (cap on the
  background subagent pool that does markdown/link/image-ref checks). The
  static phase always fans out fully — only the interactive phase is throttled,
  because every concurrent browser instance signs in to the same tenant and
  can collide with other concurrent labs' state.
- **`lab_dependencies` graph in `judge-config.yml`**. Defines chains of slugs
  that must execute serially because each lab's tenant artifacts (agents,
  topics, knowledge sources, variables, evaluations) are read by the next.
  The orchestrator topologically sorts the planned lab list against this
  graph; independent labs run in parallel up to `fanout_concurrency`, while
  declared chains run in order. The bootcamp's current chain is
  `core-concepts-agent-knowledge-tools` → `core-concepts-variables-agents-channels`
  → `core-concepts-analytics-evaluations`.
- **SKILL.md Phase 1.7** documents the new fan-out planning step that runs
  between the run-start account prompt and the per-lab loop.

### Changed

- **`on_duplicate: "create_anyway"` is deprecated.** The plugin will never file a second open issue for the same lab. The value is now silently coerced to `"comment"` and logged as a warning to the run transcript.
- **`mcs-lab-auditor/SKILL.md` "Important rules" section rewritten.** "Issues only" becomes "two narrow write paths: issue API (always on) + screenshots-only PR-append (default on, opt out per-run)". The carve-out is documented in three places (rule list, `references/pr-append-flow.md`, and the sub-skill itself) so a future reader can't miss what is and isn't allowed.
- Default screenshot scope is `"screenshots_only"` — no markdown or other-file edits are auto-applied. A future `--append-edits-too` flag would relax this; it does not exist yet.
- `SKILL.md` Phase 1.5 ("Run-start account prompt") is now explicitly
  marked MANDATORY with a leading note about the failure mode it prevents
  (running against the wrong tenant).
- `SKILL.md` Phase 1.7 has a new callout: "the static phase is not a
  substitute for the interactive phase." Static catches doc drift; only
  interactive catches UI drift.
- `SKILL.md` Phase 2 header now reads "interactive UI execution" with a
  one-paragraph framing of why this is the core deliverable of the audit.
- `SKILL.md` "Important rules" gained two new rules at the top:
  "Run the interactive phase by default" and "Always prompt at Phase 1.5
  unless explicitly told not to."
- `SKILL.md` "What to do when stuck" gained a new "Network / connection
  error" section with the retry-then-ask flow, distinct from the existing
  UI-side `_browser_wait_for` timeout policy.
- Default `fanout_concurrency` is `1`, preserving strict-serial legacy behavior
  for existing runs. Raise only when (a) labs genuinely don't share tenant
  state, or (b) you've provisioned one training account per slot.

### Fixed

- **Slash command preflight aborted before the interview ran.** Every `/audit-*` command had `!`...`` preflight lines using inline PowerShell `if (...) { ... } else { ... }` (some wrapped in `powershell -NoProfile -Command '...'`, some bare). When Claude Code's slash-command preprocessor routed these through bash, the literal `{` and `}` characters were re-interpreted as brace expansion even inside single quotes, producing `bash: eval: line 1: syntax error near unexpected token '{'` and halting the entire slash command before Phase 1.5 could run. Replaced every `if/else` preflight with a single `scripts/Get-PathOrFallback.ps1` helper invoked via `pwsh -NoProfile -File` — no curly braces reach the shell parser. The helper has one mode per preflight shape: `Exists`, `Raw`, `JsonField`, `SizeBytes`, `BytesLabel`, `RecentDirs`, `GrepContext`. Applies to `/audit-lab`, `/audit-bootcamp`, `/audit-account`, and `/audit-report`.
- **Duplicate-issue blind spot.** Before today, the dedup filter used `--label "lab-audit,lab:{slug}"` with comma-AND semantics; open issues missing the `lab:<slug>` label were invisible to it, so re-runs filed a second issue. The new loose-match + label-backfill flow closes the gap.
- **Comment churn on re-runs.** Re-auditing a lab no longer re-posts findings that were already present in the existing issue or its comments — fingerprint dedup drops them before the `gh issue comment` call.

## [0.1.0] — 2026-05-14

Initial scaffold. The plugin is structurally complete: every file referenced by the design plan is in place, frontmatter validates, and all 11 bootcamp slugs in `_data/lab-config.yml` resolve to existing lab markdown files. End-to-end exercise against a live workshop tenant is the immediate next step.

### Added

- `.claude-plugin/plugin.json` — plugin manifest (name, version, description, author, repository, license).
- Four slash commands:
  - `/audit-bootcamp` — full sweep of every bootcamp lab.
  - `/audit-lab <slug>` — single-lab audit.
  - `/audit-report [<run-id>]` — local summary of past runs.
  - `/audit-account [show|redeem|clear]` — workshop-account management.
- Two skills:
  - `mcs-lab-auditor` — primary orchestration skill (parse, execute, judge, checkpoint).
  - `mcs-lab-issue-filer` — sub-skill that renders findings into a GitHub issue body and files via `gh`, with label-based de-duplication.
- Six reference docs:
  - `lab-parser-spec.md` — markdown → step tree grammar.
  - `playwright-cookbook.md` — per-portal sign-in flow, scene-boundary probe, tool mapping, known quirks.
  - `workshop-redemption.md` — Skillable-style workshop-code redemption + DPAPI caching.
  - `llm-judge-prompts.md` — per-step judge, critique pass, action classifier templates.
  - `finding-schema.md` — finding record schema and severity rubric.
  - `audit-log-schema.md` — `audit-history.yml` entry shape.
- Two configuration files:
  - `config/workshop.yml` — workshop portal URL and redemption page selectors.
  - `config/judge-config.yml` — confidence thresholds, retry caps, non-deterministic lab list, dedupe behavior.
- Repo governance:
  - MIT `LICENSE` (Microsoft copyright).
  - `SECURITY.md` (Microsoft MSRC reporting flow + pointer to the plugin's security model).
  - `CODE_OF_CONDUCT.md` (Microsoft Open Source CoC).
  - `CONTRIBUTING.md` (development setup, conventions, change recipes).
- Documentation (`docs/`):
  - `architecture.md` — component overview, run lifecycle sequence diagram, finding→issue data flow.
  - `design-decisions.md` — ADR-style enumeration of the architectural choices and rationales.
  - `security.md` — DPAPI threat model, secret inventory, what's at risk versus protected.
  - `troubleshooting.md` — common failure modes by category with diagnostic steps.
  - `extending.md` — how to adapt to a different workshop portal, add a command, or point at a different lab repo.
- `runtime/` directory gitignored at the repo root — never committed.

### Design

- **Read-only on `microsoft/mcs-labs`**: the plugin never branches, commits, pushes, or opens pull requests against that repo. The only write target is the GitHub issues API.
- **One issue per lab with findings**; clean labs produce local-only `audit-history.yml` entries (zero GitHub activity when nothing is wrong).
- **Workshop-code-issued test account**, securely cached via Windows DPAPI (current-user scope), reused across every lab in a run.
- **No automatic tenant cleanup**: orphan agents created during testing are intentionally left for the user to manage out-of-band.

### Known limitations

- Windows-only (DPAPI dependency).
- Hard-coded references to `C:\Users\dewainr\mcs-labs` in several files — adjust for your environment per `docs/extending.md`.
- Single workshop-portal flow assumed (Skillable-style).
- Screenshots aren't attached inline to issues (`gh` CLI limitation); they're referenced by local path in the issue body.

[Unreleased]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.1.0...v0.2.1
[0.1.0]: https://github.com/microsoft/BootcampLabTestPlugin/releases/tag/v0.1.0
