# Changelog

All notable changes to `mcs-lab-auditor` are documented here.

This project adheres to [Semantic Versioning](https://semver.org/). The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

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

### Changed

- **`on_duplicate: "create_anyway"` is deprecated.** The plugin will never file a second open issue for the same lab. The value is now silently coerced to `"comment"` and logged as a warning to the run transcript.
- **`mcs-lab-auditor/SKILL.md` "Important rules" section rewritten.** "Issues only" becomes "two narrow write paths: issue API (always on) + screenshots-only PR-append (default on, opt out per-run)". The carve-out is documented in three places (rule list, `references/pr-append-flow.md`, and the sub-skill itself) so a future reader can't miss what is and isn't allowed.
- Default screenshot scope is `"screenshots_only"` — no markdown or other-file edits are auto-applied. A future `--append-edits-too` flag would relax this; it does not exist yet.

### Fixed

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

[Unreleased]: https://github.com/microsoft/BootcampLabTestPlugin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/microsoft/BootcampLabTestPlugin/releases/tag/v0.1.0
