---
description: Audit every lab in the mcs-labs bootcamp event end-to-end; file one GitHub issue per lab with findings, log clean labs locally.
argument-hint: "[--resume <run-id>] [--labs slug1,slug2,...] [--no-issue] [--force-issue]"
---

# /audit-bootcamp

You are starting a full bootcamp audit run.

## Arguments

Arguments passed: `$ARGUMENTS`

Parse these flags:
- `--resume <run-id>` — resume a previously interrupted run; skip labs already marked `done`/`issue_filed`/`skipped`.
- `--labs <csv>` — restrict to a comma-separated subset of slugs from the bootcamp list.
- `--no-issue` — execute the labs but never file GitHub issues (everything goes to local log only). Does NOT skip the interactive UI phase.
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those).
- `--static-only` — opt out of the interactive UI phase for this run. Static analysis (markdown, links, images, structure) still runs for every lab. The default is to run BOTH phases — `require_interactive_phase: true` in `judge-config.yml`. Use `--static-only` only when you don't have a workshop account and want a doc-only sweep; the resulting findings will not catch UI drift in the live product.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run. Default is whatever the config says (ships as `always`).

## Pre-flight context

- gh auth: !`gh auth status 2>&1 | Select-Object -First 5`
- mcs-labs repo present: !`if (Test-Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml") { "yes" } else { "MISSING — abort" }`
- bootcamp lab list source: !`Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15`
- cached account meta: !`if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw } else { "(no cached account)" }`

## Your task

Invoke the `mcs-lab-auditor` skill following its full lifecycle:

1. Pre-flight (read the configs, enumerate the lab list, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. Run-start account prompt (offer cached account or new workshop-code redemption). **This prompt is mandatory** unless `account_prompt_mode` is set to `only_if_expired`/`only_if_missing` AND the cache satisfies the chosen mode. The default ships as `always`.
3. Plan execution order (Phase 1.7): fan out static analysis across one subagent per lab and topologically sort the interactive phase against `lab_dependencies`.
4. **Interactive per-lab loop (required by default — controlled by `require_interactive_phase`)**: parse → execute steps in Playwright against the chosen account → judge each step → checkpoint per scene → file issue or log clean. Network/connection failures retry up to `network_retry_count` (default 3) with `network_retry_backoff_seconds` between attempts, then halt and ask the user via `AskUserQuestion` (retry / wait / skip lab / abort).
5. Wrap-up: close the browser, print summary, save manifest.

Read `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the full procedure and refer to the `references/` files as needed. **Do not skip the run-start account prompt and do not skip the interactive phase** — both are the user's safety net against running against the wrong tenant or shipping a doc-only audit.

If `--resume` is provided, the Phase 1.5 prompt is shown unless `account_prompt_mode` permits skipping AND the cached `expires_at` is still in the future. A resume after the cache expired always re-prompts.

If `--dry-run` is in the arguments, treat it as a per-lab dry-run for every lab (parse only, no browser activity).

If `--static-only` is in the arguments, run the static fan-out but skip Phase 2 for every lab. Record `execution.skipped_interactive: true, reason: cli_flag` in the run manifest so future readers know the audit didn't exercise the live UI.
