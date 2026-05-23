# Changelog

All notable changes to `mcs-lab-auditor` are documented here.

This project adheres to [Semantic Versioning](https://semver.org/). The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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

### Changed

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

### Added (from PR #11, also unreleased)

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

- Default `fanout_concurrency` is `1`, preserving strict-serial legacy behavior
  for existing runs. Raise only when (a) labs genuinely don't share tenant
  state, or (b) you've provisioned one training account per slot.

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

[Unreleased]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/microsoft/BootcampLabTestPlugin/releases/tag/v0.1.0
