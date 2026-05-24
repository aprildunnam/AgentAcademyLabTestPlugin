---
description: Audit every lab in the mcs-labs bootcamp event end-to-end; file one GitHub issue per lab with findings, log clean labs locally.
argument-hint: "[--resume <run-id>] [--labs slug1,slug2,...] [--no-issue] [--force-issue]"
---

# /audit-bootcamp

You are starting a full bootcamp audit run.

## Arguments

Arguments passed: `$ARGUMENTS`

Every flag below is **optional**. Any answer the user doesn't provide via a
flag is collected interactively at run-start (see Phase 1.5 — Run-start
interview in `SKILL.md`). Running `/audit-bootcamp` with no flags is the
expected default — the orchestrator will walk the user through account,
phase mix, and scope before doing anything destructive.

Parse these flags:
- `--resume <run-id>` — resume a previously interrupted run; skip labs already marked `done`/`issue_filed`/`skipped`. Inherits the prior run's `phase_mix` and `scope_labs`, so the scope question (Q3) is not re-asked.
- `--labs <csv>` — restrict to a comma-separated subset of slugs from the bootcamp list. When provided, the interview skips the scope question (Q3) and the one-lab picker (Q4).
- `--no-issue` — execute the labs but never file GitHub issues (everything goes to local log only). Does NOT skip the interactive UI phase.
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those).
- `--static-only` — opt out of the interactive UI phase for this run. Static analysis (markdown, links, images, structure) still runs for every lab. The interview skips the phase-mix question (Q2). The default (no flag) is to ask interactively. Use `--static-only` only when you want a doc-only sweep; the resulting findings will not catch UI drift in the live product.
- `--interactive-only` — opt out of the static analysis fan-out for this run. Assumes a previous run produced `findings-static.json` for each in-scope lab and merges them at lab completion. The interview skips the phase-mix question (Q2). Useful for re-verifying a previously-audited lab after a product release.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run. Default is whatever the config says (ships as `always`). Controls only the account question (Q1); the other interview questions are governed by their own flags.

## Pre-flight context

- gh auth: !`powershell -NoProfile -Command 'gh auth status 2>&1 | Select-Object -First 5'`
- mcs-labs repo present: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml") { "yes" } else { "MISSING — abort" }'`
- bootcamp lab list source: !`powershell -NoProfile -Command 'Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15'`
- cached account meta: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw } else { "(no cached account)" }'`

## Your task

Invoke the `mcs-lab-auditor` skill following its full lifecycle:

1. Pre-flight (read the configs, enumerate the lab list, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. **Run-start interview** (Phase 1.5 in `SKILL.md`): walk the user through up to four `AskUserQuestion` calls — account, phase mix, scope, and (if scope == one lab) a two-step lab picker. Each question is skipped only when a CLI flag already provided the answer. The interview is **mandatory** for any question whose answer isn't on the command line — silent defaults have caused real audit runs to execute against the wrong tenant or to ship a doc-only audit when the user expected live coverage.
3. Plan execution order (Phase 1.7): fan out static analysis across one subagent per lab and topologically sort the interactive phase against `lab_dependencies`. Skip the static fan-out if the interview chose `phase_mix: interactive`; skip the interactive plan if `phase_mix: static`.
4. **Interactive per-lab loop (runs when `phase_mix` is `interactive` or `both`)**: parse → execute steps in Playwright against the chosen account → judge each step → checkpoint per scene → file issue or log clean. Network/connection failures retry up to `network_retry_count` (default 3) with `network_retry_backoff_seconds` between attempts, then halt and ask the user via `AskUserQuestion` (retry / wait / skip lab / abort).
5. Wrap-up: close the browser, print summary, save manifest.

Read `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the full procedure and refer to the `references/` files as needed. **Do not silently default any interview question.** If the user wants a doc-only sweep or a single-lab run, that should be their explicit choice (via flag or via the interview), not the orchestrator's silent decision.

If `--resume` is provided, the interview inherits the prior run's `phase_mix` and `scope_labs` from `manifest.yml`. The account question (Q1) is still shown unless `account_prompt_mode` permits skipping AND the cached `expires_at` is still in the future. A resume after the cache expired always re-prompts for the account.

If `--dry-run` is in the arguments, treat it as a per-lab dry-run for every lab (parse only, no browser activity). The interview still runs but the lab picker is informational only.

When `phase_mix: static` (via `--static-only` or the interview), run the static fan-out but skip Phase 2 for every lab. Record `execution.skipped_interactive: true, reason: cli_flag | interview` in the run manifest so future readers know the audit didn't exercise the live UI. The symmetric case applies for `phase_mix: interactive`.
