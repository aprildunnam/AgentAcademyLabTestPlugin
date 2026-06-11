# BootcampLabTestPlugin (`mcs-lab-auditor`)

A Claude Code plugin that **audits and builds** labs in a target lab repository end-to-end, driving the live product UI with Playwright.

- **Audit mode** (`/audit-*`) drives an existing lab's steps, has an LLM judge compare observed behavior to each written instruction, and files **one GitHub issue per lab** (plus a matching fix-PR) whenever steps are broken or unclear. Clean labs produce a local-only audit-history entry — no GitHub activity when nothing's wrong.
- **Build mode** (`/build-lab`, v0.4.0+) **interactively authors a new lab**: it gets a workshop account, drives to the Copilot Studio Home page, captures the lab step-by-step (instructions + tips + screenshots, confirming every step), assembles a sibling-formatted `labs/<slug>/README.md`, re-runs it through the same audit engine as a quality gate, and opens a PR adding the lab.

Both modes are **event/workshop-agnostic**. The audit scope is enumerated from two Jekyll collections in the mcs-labs repo — `_events/<id>.md` (formal curated events: bootcamp, the buildathons) and `_workshops/<id>.md` (on-demand workshops: the Azure AI workshop, MCS-in-a-Day, Agent-in-a-Day, the Agent Academy tracks) — via `scripts/Get-EventCatalog.ps1`. **Events and workshops are both first-class audit scopes.** Single labs can still be audited individually against the full `lab_metadata` catalog, and a built lab is created standalone with optional event/workshop attachment — nothing is hardcoded to bootcamp. (The legacy `_data/lab-config.yml.event_configs` table is now only a last-resort fallback; it has drifted out of sync with the collections.)

Defaults to `microsoft/mcs-labs`; point it at your own fork + training portal via a user `lab-instances.yml` — see docs/extending.md.

**The plugin writes to the mcs-labs repo through three narrow paths.** (a) `gh issue create | comment | edit` for issues + label hygiene (always on). (b) A **fix-PR per audit run** with findings: it applies the `suggested_correction` diffs + screenshot replacements and opens a new PR on a run-unique branch `dewain/fix-<slug>-content-audit-<run-id>` — *unless* an open fix-PR for that lab already exists, in which case the run's commit is appended to that PR instead of opening a duplicate. See `skills/mcs-lab-fix-pr-filer/SKILL.md`. (c) A screenshots-only commit appended to an **already-open** fix-PR (same-author, mergeable) for the lighter re-audit case — on by default, suppressed with `--no-update-screenshots` / `--no-append-to-pr` (CLI) or `issues.pr_append.enabled_by_default: false` (config). See `skills/mcs-lab-pr-appender/SKILL.md`.

**The plugin will never create a duplicate _open_ issue or PR for a lab that already has one open.** Phase 1.4 of every audit run probes `gh issue list` + `gh pr list` per slug, and the per-lab disposition uses that result — new findings go into a fingerprint-deduped delta comment on the existing open issue, and a run's fixes are appended to the existing open PR. Dedup is scoped to **open** items only: a merged or closed prior issue/PR never blocks a new one, so each run with fresh findings gets its own PR on a fresh branch.

**Build mode adds two write paths:** (1) a **"new lab proposal" issue** opened as soon as the lab is named — labeled `type: new-lab` + `status: in-progress` so the team can see it's **In Progress** — and (2) a **new-lab PR** (`skills/mcs-lab-new-lab-pr/SKILL.md`) on a run-unique branch `dewain/new-lab-<slug>-<build-id>` off fresh `origin/main` that closes the proposal issue on merge. Build mode's audit gate itself **files nothing on GitHub** — its findings stay local and feed the authoring loop until the lab passes.

## Status

`v0.6.0` — field-tested audit mode; build mode is new. The plugin has completed multiple full audit cycles against live workshop tenants. In the May 2026 audit cycle alone, it raised **24 issues** across 11 bootcamp labs and generated **19 merged fix PRs** against `microsoft/mcs-labs`. See [Real-world impact](#real-world-impact) below. The interactive lab-building mode (`/build-lab`) shipped in v0.4.0 (proposal-issue tracking added in v0.5.0) and awaits its first full live-tenant build. v0.6.0 makes the plugin fully portable: all hard-coded machine paths are gone (the mcs-labs repo is resolved — and auto-cloned — at run start, plugin files are read via `$env:CLAUDE_PLUGIN_ROOT`), audit scope is read from the `_events/` + `_workshops/` collections, and every run begins with a non-blocking plugin self-version check.

## Real-world impact

The auditor has been exercised end-to-end against the full Architecture Bootcamp (11 labs, ~720 steps). Here's what it found and fixed:

| Category | Examples |
|---|---|
| **UI drift** | Copilot Studio renamed "Use general knowledge" to "Allow ungrounded responses"; "Create blank agent" now opens a name-required modal instead of a Details section with an Edit button; left-nav "..." menu replaced by "Explore Power Platform" flyout |
| **Screenshot refresh** | Outdated screenshots replaced across multiple labs to match current portal UI (agent builder, analytics, ALM, component collections) |
| **Clarity & wording** | Ambiguous "Select SharePoint" instruction clarified (two SharePoint surfaces exist in the dialog); analytics prerequisite rewritten to emphasize publish-first requirement |
| **Spelling & typos** | Double-space typos (`change  the Name`), "State or Providence" → "State/Province" |
| **Cross-lab consistency** | Sibling labs verifying the same Account Data Lookup Agent used different field labels — caught by the automated cross-lab drift check |
| **Missing steps** | Greeting-topic disable step missing before testing in mcs-tools; missing prereq guidance for analytics |

All findings: [microsoft/mcs-labs issues (lab-audit label)](https://github.com/microsoft/mcs-labs/issues?q=label%3Alab-audit). A full bootcamp sweep runs for roughly **$30–$60** in estimated token spend.

## Commands

| Command | Purpose |
|---|---|
| `/audit-event [--event <key>] [--resume <id>] [--labs csv] [--no-issue]` | Audit every lab in an event or workshop. With `--event <key>`, the scope is pinned; without it, the run-start interview asks. Generic over every scope in the `_events/` and `_workshops/` collections (enumerated by `scripts/Get-EventCatalog.ps1`). |
| `/audit-bootcamp [--resume <id>] [--labs csv] [--no-issue]` | Shortcut for `/audit-event --event bootcamp`. Audits every lab listed in the bootcamp `_events/bootcamp.md` `labs:` front-matter. |
| `/audit-lab [<slug>] [--no-issue] [--dry-run]` | Audit a single lab. With `<slug>`, the slug pins scope. Without, the run-start interview picks one from the **full all-labs catalog** (`lab_metadata.*`). `--dry-run` exercises only the markdown parser. |
| `/audit-report [<run-id>]` | Print a local summary of recent audit runs. |
| `/audit-account [show\|redeem\|clear]` | Manage the DPAPI-cached workshop-issued test account. |
| `/build-lab [<lab-name>] [--resume <build-id>] [--mode guided\|scenario] [--no-pr]` | **Interactively build a NEW lab** end-to-end via Playwright, capturing instructions + screenshots step-by-step, gate it through the audit engine, and open a PR on `microsoft/mcs-labs`. Event/workshop-agnostic — a lab is built standalone; event attachment is optional. |

## How it works

1. **Run-start interview.** Every `/audit-*` command first runs an interactive interview (`AskUserQuestion`): which account, which phase mix (static / interactive / both), which scope (event or single lab), which event (if scope = event), or which lab (if scope = one). Each question is skipped only when a CLI flag or entry-point command already provides the answer — silent defaults aren't allowed because they have caused real audit runs against the wrong tenant.
2. **Lab parsing.** Each lab's markdown is split into use cases (`### Use Case #N`), scenes (`####`), and numbered steps. Alert blocks (`> [!IMPORTANT]`, `> [!TIP]`, etc.) attach to the preceding step as hints. Image references attach as semantic visual hints. Non-deterministic markers (`may differ`, `may vary`) are flagged. The parser also emits a `scene-fingerprints.json` sidecar per lab feeding the cross-lab consistency pass below.
3. **Static fan-out + cross-lab consistency.** Each lab gets a background static subagent (markdown checks, link checks, image-ref resolution, prereq sanity). After all per-lab subagents return, a single fan-in pass groups scenes by shape hash across the lab set and flags identifier-token drift between sibling labs (e.g. `Address 1: State/Province` vs `Address1: State or Providence` in two labs that verify the same UI surface). Findings are severity `low` and tagged `flags.cross_lab_drift: true`.
4. **Interactive step execution.** Each step is dispatched to the Playwright MCP using an action classifier (`navigate | click | type | select | wait | inspect`). Accessibility snapshots are captured before and after each step. Labs are sliced into per-Use-Case subagents so the orchestrator's context doesn't overflow on 50-step labs.
5. **Step judging.** An LLM judge inspects the snapshots + screenshot and returns a structured JSON verdict (`pass | broken | unclear | non_deterministic | transient | cannot_verify`) with confidence and a suggested correction. An optional second-pass critique judge filters out false positives.
6. **Issue + fix-PR, or log.** If any findings clear the confidence threshold, one GitHub issue is filed per lab (or a comment added to the existing open issue), and a matching fix-PR is opened on a run-unique branch `dewain/fix-<slug>-content-audit-<run-id>` applying the `suggested_correction` diffs and any refreshed screenshots — or, if an open fix-PR for the lab already exists, the commit is appended to it instead of opening a duplicate. Otherwise, a clean entry is appended to `runtime/audit-history.yml`.

### How build mode works (`/build-lab`)

Build mode reuses the account flow, Playwright cookbook, judge, and finding schema above, and adds an authoring loop (phases B0–B7 in `skills/mcs-lab-builder/SKILL.md`):

1. **Preflight + interview.** Assert Opus, check `gh`, **resolve the mcs-labs path**, **detect the registration mechanism**, then pick the account and an interaction mode — **guided** (you dictate each step) or **scenario** (you describe the lab, the AI proposes each step). Both confirm every step.
2. **Navigate** to the Copilot Studio Home page; name the lab (slug + collision check); capture metadata and optional event attachment. **Open a "new lab proposal" issue** (`type: new-lab` + `status: in-progress`) so the lab is tracked as In Progress while you build it.
3. **Capture loop.** For each step: snapshot → step intent → execute in Playwright → screenshot → write the instruction + tips → **confirm** → checkpoint to a ledger.
4. **Assemble** the full sibling-formatted `labs/<slug>/README.md` from the ledger.
5. **Audit gate.** Register + materialize the lab and run the audit engine against it with **all GitHub writes suppressed**; any broken/unclear step loops back for a fix until the lab passes.
6. **PR.** Open a PR adding `labs/<slug>/README.md` + screenshots + the registration entry. Skipped under `--no-pr`.

See [`docs/architecture.md`](docs/architecture.md#build-mode-interactive-lab-authoring) for the full lifecycle diagram.

## Installation

The plugin works in both **Claude Code** and **GitHub Copilot CLI** (same skill-discovery model). Pick whichever runtime(s) you want and clone into the matching plugins directory.

Claude Code (primary, fully tested):

```powershell
git clone https://github.com/microsoft/BootcampLabTestPlugin "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
```

GitHub Copilot CLI (find the plugins directory via `copilot --help` or `copilot config get plugins.path`):

```powershell
git clone https://github.com/microsoft/BootcampLabTestPlugin (Join-Path $copilotPluginsPath "mcs-lab-auditor")
```

…then restart your runtime. The five `/audit-*` commands should appear.

There are **no per-machine path edits** to make: the mcs-labs repo is resolved automatically at run start (and cloned for you if no local copy exists — see below), and the plugin reads its own files via `$env:CLAUDE_PLUGIN_ROOT`. Each run also begins with a best-effort plugin self-version check that warns (non-blocking) when a newer version is published, recommending `/plugin` to update.

For the full setup — including prerequisite checks, workshop portal configuration, Copilot CLI caveats, the `MCS_LABS_REPO` override, test-account caching, and a smoke-test sequence — see [`docs/installation.md`](docs/installation.md). For a single-document overview-plus-architecture-plus-install reference, see [`docs/mcs-lab-auditor-overview-and-architecture.pdf`](docs/mcs-lab-auditor-overview-and-architecture.pdf).

## Prerequisites

- **OS**: Windows 10/11. The credential cache uses Windows DPAPI via PowerShell `ConvertFrom-SecureString`; macOS/Linux are not supported in this release.
- **Tooling**: `gh` CLI (authenticated and permitted to file issues on `microsoft/mcs-labs`), PowerShell 7+.
- **Claude Code plugins**: the global Playwright MCP plugin enabled (`playwright@claude-plugins-official`).
- **Repo clone**: a local clone of `microsoft/mcs-labs` (the plugin reads `_labs/<slug>.md`, the `_events/` + `_workshops/` collections, and `_data/lab-config.yml`). You don't need to clone it manually or edit any path: `scripts/Resolve-LabRepo.ps1` resolves the repo at run start in this order — `$env:MCS_LABS_REPO`, the `mcs_labs_repo_path_candidates` in `config/judge-config.yml`, a built-in list under `%USERPROFILE%`, and finally an **auto-clone** of `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs`. The resolved repo is then fast-forwarded to `origin/main` so audits always run against the latest lab content. This applies to **both** audit and build modes.
- **Workshop access**: an unredeemed workshop code from a Skillable-style portal. The portal URL is configured in `config/workshop.yml` on first run.

## Getting started

```text
1. /audit-account redeem                            # one-time: set up the test account
2. /audit-lab core-concepts-analytics-evaluations --dry-run   # smoke-test the parser, no browser
3. /audit-lab core-concepts-analytics-evaluations   # full single-lab run
4. /audit-bootcamp                                  # full bootcamp sweep once you trust the single-lab path
5. /audit-event --event agent-buildathon-1month     # any other event by key
6. /audit-event                                     # generic — interview picks the event
```

## Configuration

| File | Purpose |
|---|---|
| `config/workshop.yml` | Workshop portal URL + redemption page selectors. Edit on first run — the default URL is the placeholder `REPLACE_ME_ON_FIRST_RUN`. |
| `config/judge-config.yml` | Confidence thresholds, retry caps, non-deterministic lab list, scene-boundary probe URL, and the `build:` block (interaction mode, audit gate, mcs-labs path + registration). |

## Project layout

```
.claude-plugin/plugin.json                # plugin manifest
commands/                                 # slash command entry points (/audit-*, /build-lab)
skills/mcs-lab-auditor/                   # audit orchestration skill + references/
skills/mcs-lab-builder/                   # build orchestration skill + references/ (B0–B7)
skills/mcs-lab-issue-filer/               # sub-skill: findings → gh issue create
skills/mcs-lab-fix-pr-filer/              # sub-skill: apply correction diffs → new fix-PR (or append to open one)
skills/mcs-lab-pr-appender/               # sub-skill: screenshots-only commit → existing open PR
skills/mcs-lab-new-lab-pr/                # sub-skill (build mode): new lab → PR
config/                                   # workshop.yml, judge-config.yml (incl. build: block)
scripts/                                  # Resolve-LabRepo.ps1, Get-EventCatalog.ps1, Test-PluginVersion.ps1, ...
runtime/                                  # gitignored — accounts, audit log, per-run + per-build artifacts
```

The `references/` directory under each skill holds the operational rulebooks the skill loads on demand: lab-parser grammar, Playwright cookbook, workshop-redemption flow, LLM judge prompts, finding schema, audit-log schema.

## Local-only artifacts (never committed)

The `runtime/` directory is gitignored. It contains:

- `account/credential.enc` — DPAPI-encrypted credential blob.
- `account/account.meta.json` — non-secret account metadata (user_id, timestamps).
- `audit-history.yml` — rolling local log of every audit run, pass or fail.
- `runs/<run-id>/...` — per-run parsed steps, findings, screenshots, transcripts.
- `builds/<build-id>/...` — per-build (build mode) workspace: draft README, captured screenshots, step ledger, resume state, gate findings.

## Limitations

- **Windows-only**, due to DPAPI.
- **No per-machine path edits.** The mcs-labs repo path is resolved (and auto-cloned if missing) by `scripts/Resolve-LabRepo.ps1` for **both** audit and build modes; all plugin-internal paths use `$env:CLAUDE_PLUGIN_ROOT`. Override the repo location with `$env:MCS_LABS_REPO` or the `mcs_labs_repo_path_candidates` list in `config/judge-config.yml` ([details](docs/installation.md#repo-resolution-no-path-edits-needed)).
- **mcs-labs new-lab toolchain drift**: the root `lab-config.yml` + `Generate-Labs.ps1` documented in that repo's `NEW_LAB_CHECKLIST.md` are absent upstream, so build mode registers new labs by writing `_labs/<slug>.md` + the `_data/lab-config.yml` entry directly (it auto-detects and uses the generator if it returns).
- **Single workshop-portal flow** assumed (Skillable-style). Other portals require editing `references/workshop-redemption.md` and `config/workshop.yml` ([how-to](docs/extending.md#adapting-to-a-different-workshop-portal)).
- **Screenshots aren't attached to issues** — `gh issue create` doesn't support inline file uploads; screenshots stay in local run artifacts and are referenced by path in the issue body.
- **No automatic tenant cleanup**. Orphan agents created during testing accumulate; the user manages tenant hygiene separately. (Deliberate — see [ADR-004](docs/design-decisions.md#adr-004--no-environment-cleanup-as-part-of-audit-runs).)

## Documentation

| Doc | When to read |
|---|---|
| [`docs/installation.md`](docs/installation.md) | Setting up the plugin on a new machine, end to end. |
| [`docs/architecture.md`](docs/architecture.md) | Understanding how the plugin works at runtime — component diagram, run lifecycle, per-step data flow, finding→issue mapping. |
| [`docs/design-decisions.md`](docs/design-decisions.md) | The "why" behind the shape of the plugin — ADR-style enumeration of architectural choices and their alternatives. |
| [`docs/security.md`](docs/security.md) | What's encrypted, what's logged, what's at risk, what isn't. Read this before extending anything credential-handling. |
| [`docs/troubleshooting.md`](docs/troubleshooting.md) | Common failure modes during a run, grouped by category. |
| [`docs/extending.md`](docs/extending.md) | Adding commands, adapting to a different workshop portal, pointing at a different lab repo, tuning the judge, customizing build mode. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Project layout, change recipes, testing approach, conventions. |
| [`SECURITY.md`](SECURITY.md) | How to report security issues (via MSRC, **not** GitHub). |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history. |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Microsoft Open Source Code of Conduct. |
| [`LICENSE`](LICENSE) | MIT (Microsoft copyright). |
