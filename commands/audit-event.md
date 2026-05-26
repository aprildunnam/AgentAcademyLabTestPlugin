---
description: Audit every lab in a workshop event end-to-end (bootcamp, buildathon, MCS-in-a-Day, etc.); file one GitHub issue per lab with findings.
argument-hint: "[--event <key>] [--resume <run-id>] [--labs slug1,slug2,...] [--no-issue] [--force-issue] [--static-only] [--interactive-only] [--no-update-screenshots] [--account-prompt <mode>] [--model-preset <optimized|opus|custom>]"
---

# /audit-event

You are starting a full **event** audit run. An event is any workshop entry in `_data/lab-config.yml.event_configs` — bootcamp, buildathons, MCS-in-a-Day variants, the Azure AI workshop, and anything added in the future. This command is generic over all events.

## Arguments

Arguments passed: `$ARGUMENTS`

Every flag below is **optional**. Any answer the user doesn't provide via a flag is collected interactively at run-start (see Phase 1.5 — Run-start interview in `SKILL.md`). Running `/audit-event` with no flags is the expected default — the orchestrator will ask which event, account, and phase mix before doing anything destructive.

Parse these flags:
- `--event <key>` — pin the event up front. Valid keys come from `_data/lab-config.yml.event_configs.*` (e.g. `bootcamp`, `agent-buildathon-1day`, `agent-buildathon-1month`, `azure-ai-workshop`, `mcs-in-a-day`, `mcs-in-a-day-v2`). When provided, Phase 1.5 Q3 and Q3a are both skipped — the scope is the event's `slugs[]`.
- `--resume <run-id>` — resume a previously interrupted run; skip labs already marked `done`/`issue_filed`/`issue_and_pr_filed`/`skipped`. Inherits the prior run's `event`, `phase_mix`, and `scope_labs`, so the scope questions (Q3, Q3a) are not re-asked.
- `--labs <csv>` — restrict to a comma-separated subset of slugs from the event's `slugs[]`. Slugs not in the chosen event are dropped with a warning. When provided, the interview skips Q3 and Q3a and Q4.
- `--no-issue` — execute the labs but never file GitHub issues (everything goes to local log only). Does NOT skip the interactive UI phase.
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those).
- `--static-only` — opt out of the interactive UI phase for this run. Static analysis (markdown, links, images, structure, cross-lab consistency) still runs for every lab. The interview skips Q2 (phase mix).
- `--interactive-only` — opt out of the static analysis fan-out for this run. Assumes a previous run produced `findings-static.json` for each in-scope lab and merges them at lab completion. The interview skips Q2.
- `--no-update-screenshots` (alias `--no-append-to-pr`) — opt out of the **default-on** screenshot refresh onto any open fix-PR. Screenshot files only; same-author only; mergeable PRs only; never creates a new branch or PR.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run. Controls only Q1.
- `--model-preset <optimized|opus|custom>` — choose the sub-agent model preset without interactive Q2a. The orchestrator is always Opus (asserted in Phase 1). `optimized` is the recommended default (~$50 per bootcamp run, ~85% completion). `opus` forces every sub-agent to Opus (~$140, ~90% completion). `custom` halts the run so you can edit per-function overrides in `config/judge-config.yml.execution.model.*`.

## Pre-flight context

- gh auth: !`gh auth status 2>&1 | head -n 5`
- mcs-labs repo present: !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode Exists -Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" -Fallback "MISSING - abort"`
- events available: !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode GrepContext -Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" -Pattern "^event_configs:" -ContextAfter 30 -Fallback "MISSING - lab-config.yml not found"`
- cached account meta: !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode Raw -Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Fallback "(no cached account)"`

## Your task

Invoke the `mcs-lab-auditor` skill following its full lifecycle:

1. Pre-flight (read the configs, enumerate the all-events map from `event_configs`, build the all-labs catalog from `lab_metadata`, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. **Run-start interview** (Phase 1.5 in `SKILL.md`): walk the user through up to five `AskUserQuestion` calls — account (Q1), phase mix (Q2), scope (Q3), event picker (Q3a, only if Q3 = whole event), and (if scope == one lab) a two-step section→lab picker (Q4a/Q4b). Each question is skipped only when a CLI flag or the entry-point command already provided the answer. The interview is **mandatory** for any question whose answer isn't on the command line.
3. Plan execution order (Phase 1.7): fan out static analysis across one subagent per lab in scope, then run the cross-lab consistency fan-in (Phase 1.7 step 1a), then topologically sort the interactive phase against `lab_dependencies`.
4. **Interactive per-lab loop (runs when `phase_mix` is `interactive` or `both`)**: parse → execute per-UC subagents in Playwright against the chosen account → judge each step → checkpoint per scene → file issue + open fix PR when findings exist.
5. Wrap-up: close the browser, print summary, save manifest.

Read `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the full procedure. **Do not silently default any interview question.**

If `--resume` is provided, the interview inherits the prior run's `event`, `phase_mix`, and `scope_labs` from `manifest.yml`. The account question (Q1) is still shown unless `account_prompt_mode` permits skipping AND the cached `expires_at` is still in the future.

When `phase_mix: static` (via `--static-only` or the interview), run the static fan-out AND the cross-lab consistency pass, but skip Phase 2 for every lab. Record `execution.skipped_interactive: true, reason: cli_flag | interview` in the run manifest. The symmetric case applies for `phase_mix: interactive`.
