---
description: Shortcut for `/audit-event --event bootcamp`. Audits every lab in the Architecture Bootcamp event end-to-end.
argument-hint: "[--resume <run-id>] [--labs slug1,slug2,...] [--no-issue] [--force-issue] [--model-preset <optimized|opus|custom>]"
---

# /audit-bootcamp

You are starting a full bootcamp audit run. This is a thin shortcut for `/audit-event --event bootcamp` — the event is pinned to `bootcamp` and Phase 1.5 Q3 (scope) and Q3a (event picker) are both skipped. For any other event, use `/audit-event` directly.

## Arguments

Arguments passed: `$ARGUMENTS`

Every flag below is **optional**. Any answer the user doesn't provide via a
flag is collected interactively at run-start (see Phase 1.5 — Run-start
interview in `SKILL.md`). Running `/audit-bootcamp` with no flags is the
expected default for the bootcamp event — the orchestrator will walk the user
through account and phase mix before doing anything destructive. Scope is
pinned to the bootcamp event so the scope and event-picker questions don't
fire.

Parse these flags:
- `--resume <run-id>` — resume a previously interrupted run; skip labs already marked `done`/`issue_filed`/`skipped`. Inherits the prior run's `phase_mix` and `scope_labs`, so the scope question (Q3) is not re-asked.
- `--labs <csv>` — restrict to a comma-separated subset of slugs from the bootcamp list. When provided, the interview skips the scope question (Q3) and the one-lab picker (Q4).
- `--no-issue` — execute the labs but never file GitHub issues (everything goes to local log only). Does NOT skip the interactive UI phase.
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those).
- `--static-only` — opt out of the interactive UI phase for this run. Static analysis (markdown, links, images, structure) still runs for every lab. The interview skips the phase-mix question (Q2). The default (no flag) is to ask interactively. Use `--static-only` only when you want a doc-only sweep; the resulting findings will not catch UI drift in the live product.
- `--interactive-only` — opt out of the static analysis fan-out for this run. Assumes a previous run produced `findings-static.json` for each in-scope lab and merges them at lab completion. The interview skips the phase-mix question (Q2). Useful for re-verifying a previously-audited lab after a product release.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run. Default is whatever the config says (ships as `always`). Controls only the account question (Q1); the other interview questions are governed by their own flags.
- `--model-preset <optimized|opus|custom>` — choose the sub-agent model preset without interactive Q2a. Orchestrator is always Opus.

## Pre-flight context

- gh auth: !`gh auth status 2>&1 | head -n 5`
- plugin version: !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Test-PluginVersion.ps1"`
- mcs-labs repo (resolved + updated): !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Status`
- bootcamp lab list: !`pwsh -NoProfile -Command '$r = & "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Path -NoPull; (& "$env:CLAUDE_PLUGIN_ROOT\scripts\Get-EventCatalog.ps1" -RepoRoot $r -Json | ConvertFrom-Json | Where-Object id -eq "bootcamp").labs'`
- cached account meta: !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Get-PathOrFallback.ps1" -Mode Raw -Path "$env:CLAUDE_PLUGIN_ROOT\runtime\account\account.meta.json" -Fallback "(no cached account)"`

## Your task

Set `event = bootcamp` and invoke the `mcs-lab-auditor` skill following its full lifecycle, exactly as `/audit-event --event bootcamp` would:

1. Pre-flight (self-version check, resolve+update the mcs-labs repo, read the configs, build the events+workshops catalog from the `_events/`/`_workshops/` collections, pin the active scope to the `bootcamp` event, take its lab list from the `bootcamp` entry's `labs[]`, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. **Run-start interview** (Phase 1.5 in `SKILL.md`): walk the user through up to four `AskUserQuestion` calls — account (Q1), phase mix (Q2), and (if Q3-skip wasn't already triggered by the bootcamp pin) Q3/Q4. **Q3 and Q3a are auto-skipped** for this command because `event=bootcamp` is pinned. Q4 only fires if `--labs` is missing and the user explicitly asks for a single lab via Q3 — which this command skips, so Q4 also doesn't fire. Each remaining question is skipped only when a CLI flag already provided the answer. If Q1 chooses redemption (or no cached account exists), the redemption flow auto-prompts for `Workshop portal URL` when `workshop_portal_url` is still `REPLACE_ME_ON_FIRST_RUN`, validates it as a URL, persists it to `config/workshop.yml`, then continues.
3. Plan execution order (Phase 1.7): fan out static analysis across one subagent per lab, run the cross-lab consistency fan-in pass (Phase 1.7 step 1a), then topologically sort the interactive phase against `lab_dependencies`. Skip the static fan-out if the interview chose `phase_mix: interactive`; skip the interactive plan if `phase_mix: static`.
4. **Interactive per-lab loop (runs when `phase_mix` is `interactive` or `both`)**: parse → execute steps in Playwright against the chosen account → judge each step → checkpoint per scene → file issue or log clean. Network/connection failures retry up to `network_retry_count` (default 3) with `network_retry_backoff_seconds` between attempts, then halt and ask the user via `AskUserQuestion` (retry / wait / skip lab / abort).
5. Wrap-up: close the browser, print summary, save manifest.

Read `$env:CLAUDE_PLUGIN_ROOT/skills/mcs-lab-auditor/SKILL.md` for the full procedure and refer to the `references/` files as needed. **Do not silently default any interview question.** If the user wants a doc-only sweep or a single-lab run, that should be their explicit choice (via flag or via the interview), not the orchestrator's silent decision.

If `--resume` is provided, the interview inherits the prior run's `event`, `phase_mix`, and `scope_labs` from `manifest.yml`. The account question (Q1) is still shown unless `account_prompt_mode` permits skipping AND the cached `expires_at` is still in the future. A resume after the cache expired always re-prompts for the account. A resume of a run whose `event` is anything other than `bootcamp` should be invoked via `/audit-event --resume <id>` instead — this command refuses to resume a non-bootcamp run.

If `--dry-run` is in the arguments, treat it as a per-lab dry-run for every lab (parse only, no browser activity). The interview still runs but the lab picker is informational only.

When `phase_mix: static` (via `--static-only` or the interview), run the static fan-out but skip Phase 2 for every lab. Record `execution.skipped_interactive: true, reason: cli_flag | interview` in the run manifest so future readers know the audit didn't exercise the live UI. The symmetric case applies for `phase_mix: interactive`.
