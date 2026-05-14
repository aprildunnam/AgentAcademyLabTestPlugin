# BootcampLabTestPlugin (`mcs-lab-auditor`)

A Claude Code plugin that audits every lab in the [`microsoft/mcs-labs`](https://github.com/microsoft/mcs-labs) **bootcamp event** end-to-end. It drives the live product UI with Playwright, has an LLM judge compare observed behavior to each written instruction, and files **one GitHub issue per lab** against `microsoft/mcs-labs` whenever steps are broken or unclear. Clean labs produce a local-only entry in an audit-history log — no GitHub activity at all when nothing's wrong.

**The plugin is read-only on the mcs-labs repo.** It never branches, commits, pushes, or opens pull requests. The only write target is the GitHub issues API.

## Status

`v0.1.0` — initial scaffold. Slash commands, skills, schemas, and configuration are in place. End-to-end exercise against a live workshop tenant is the next step (see "Getting started").

## Commands

| Command | Purpose |
|---|---|
| `/audit-bootcamp [--resume <id>] [--labs csv] [--no-issue]` | Audit every lab listed in `_data/lab-config.yml` → `lab_orders.event.bootcamp`. |
| `/audit-lab <slug> [--no-issue] [--dry-run]` | Audit a single lab. `--dry-run` exercises only the markdown parser. |
| `/audit-report [<run-id>]` | Print a local summary of recent audit runs. |
| `/audit-account [show\|redeem\|clear]` | Manage the DPAPI-cached workshop-issued test account. |

## How it works

1. **Run-start account prompt.** Each `/audit-*` command first checks for a cached test account (`runtime/account/account.meta.json`). If found, prompts to reuse it (showing the cached `user_id`) or redeem a fresh workshop code via the workshop portal. Issued credentials are encrypted with Windows DPAPI (current-user scope) at `runtime/account/credential.enc`.
2. **Lab parsing.** Each lab's markdown is split into use cases (`### Use Case #N`), scenes (`####`), and numbered steps. Alert blocks (`> [!IMPORTANT]`, `> [!TIP]`, etc.) attach to the preceding step as hints. Image references attach as semantic visual hints. Non-deterministic markers (`may differ`, `may vary`) are flagged.
3. **Step execution.** Each step is dispatched to the Playwright MCP using an action classifier (`navigate | click | type | select | wait | inspect`). Accessibility snapshots are captured before and after each step.
4. **Step judging.** An LLM judge inspects the snapshots + screenshot and returns a structured JSON verdict (`pass | broken | unclear | non_deterministic | transient | cannot_verify`) with confidence and a suggested correction. An optional second-pass critique judge filters out false positives.
5. **Issue or log.** If any findings clear the confidence threshold, one GitHub issue is filed per lab (or a comment added to an existing open issue for the same lab via label-based de-duplication). Otherwise, a clean entry is appended to `runtime/audit-history.yml`.

## Installation

Quick path:

```powershell
git clone https://github.com/microsoft/BootcampLabTestPlugin "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
```

…then restart Claude Code. The four `/audit-*` commands should appear.

For the full setup including prerequisite checks, workshop portal configuration, hard-coded path adjustments (if your `mcs-labs` clone isn't at `C:\Users\dewainr\mcs-labs`), test-account caching, and a smoke-test sequence: see [`docs/installation.md`](docs/installation.md).

## Prerequisites

- **OS**: Windows 10/11. The credential cache uses Windows DPAPI via PowerShell `ConvertFrom-SecureString`; macOS/Linux are not supported in this release.
- **Tooling**: `gh` CLI (authenticated and permitted to file issues on `microsoft/mcs-labs`), PowerShell 7+.
- **Claude Code plugins**: the global Playwright MCP plugin enabled (`playwright@claude-plugins-official`).
- **Repo clone**: a local clone of `microsoft/mcs-labs` (the plugin reads `_labs/<slug>.md` and `_data/lab-config.yml`). The default path it looks at is `C:\Users\dewainr\mcs-labs` — adjust the path references in `skills/mcs-lab-auditor/SKILL.md` and the command files if your clone lives elsewhere.
- **Workshop access**: an unredeemed workshop code from a Skillable-style portal. The portal URL is configured in `config/workshop.yml` on first run.

## Getting started

```text
1. /audit-account redeem                            # one-time: set up the test account
2. /audit-lab core-concepts-analytics-evaluations --dry-run   # smoke-test the parser, no browser
3. /audit-lab core-concepts-analytics-evaluations   # full single-lab run
4. /audit-bootcamp                                  # full bootcamp sweep once you trust the single-lab path
```

## Configuration

| File | Purpose |
|---|---|
| `config/workshop.yml` | Workshop portal URL + redemption page selectors. Edit on first run — the default URL is the placeholder `REPLACE_ME_ON_FIRST_RUN`. |
| `config/judge-config.yml` | Confidence thresholds, retry caps, non-deterministic lab list, scene-boundary probe URL. |

## Project layout

```
.claude-plugin/plugin.json                # plugin manifest
commands/                                 # slash command entry points
skills/mcs-lab-auditor/                   # primary orchestration skill + references/
skills/mcs-lab-issue-filer/               # sub-skill: findings → gh issue create
config/                                   # workshop.yml, judge-config.yml
runtime/                                  # gitignored — accounts, audit log, per-run artifacts
```

The `references/` directory under each skill holds the operational rulebooks the skill loads on demand: lab-parser grammar, Playwright cookbook, workshop-redemption flow, LLM judge prompts, finding schema, audit-log schema.

## Local-only artifacts (never committed)

The `runtime/` directory is gitignored. It contains:

- `account/credential.enc` — DPAPI-encrypted credential blob.
- `account/account.meta.json` — non-secret account metadata (user_id, timestamps).
- `account/storage-state.json` — post-SSO cookies + localStorage.
- `audit-history.yml` — rolling local log of every audit run, pass or fail.
- `runs/<run-id>/...` — per-run parsed steps, findings, screenshots, transcripts.

## Limitations

- **Windows-only**, due to DPAPI.
- **Hard-coded paths** to `C:\Users\dewainr\mcs-labs` in several places — adjust for your clone location ([instructions](docs/installation.md#step-5b--adjust-hard-coded-paths-only-if-your-clone-is-not-at-cusersdewainrmcs-labs)).
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
| [`docs/extending.md`](docs/extending.md) | Adding commands, adapting to a different workshop portal, pointing at a different lab repo, tuning the judge. |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Project layout, change recipes, testing approach, conventions. |
| [`SECURITY.md`](SECURITY.md) | How to report security issues (via MSRC, **not** GitHub). |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history. |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Microsoft Open Source Code of Conduct. |
| [`LICENSE`](LICENSE) | MIT (Microsoft copyright). |
