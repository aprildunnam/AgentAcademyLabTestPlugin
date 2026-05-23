---
description: Audit a single mcs-labs bootcamp lab end-to-end; file one GitHub issue with findings if any, or log a clean pass locally.
argument-hint: "<lab-slug> [--no-issue] [--force-issue] [--dry-run] [--static-only] [--account-prompt <mode>]"
---

# /audit-lab

You are auditing a single bootcamp lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab slug (e.g. `core-concepts-analytics-evaluations`). Flags:
- `--dry-run` — parse the lab into `steps.json` only. No browser activity, no issue, no audit-history entry.
- `--no-issue` — execute the lab (interactive UI phase still runs) but never file a GitHub issue.
- `--force-issue` — file an issue even if the lab is in `non_deterministic_lab_slugs`.
- `--static-only` — skip the interactive UI phase; do static checks only. Default is to run both phases — `require_interactive_phase: true` in `judge-config.yml`.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run.

## Pre-flight context

- bootcamp lab slugs: !`Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15`
- cached account: !`if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { (Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw | ConvertFrom-Json).user_id } else { "(none)" }`

## Your task

Invoke the `mcs-lab-auditor` skill for the single given slug:

1. Validate the slug exists in `_data/lab-config.yml` `lab_orders.event.bootcamp` AND `_labs/<slug>.md` exists. Abort with a clear message if either is missing.
2. Pre-flight (configs, `gh` auth).
3. **Run-start account prompt** — mandatory per `judge-config.yml.execution.account_prompt_mode` (ships as `always`). Skip only when `--dry-run` is set OR the mode + cache state allow it (see SKILL.md Phase 1.5). Even on `--static-only` the prompt still runs if you want the static phase recorded against a known account, but it is safe to skip if you don't.
4. Single-lab loop: parse → **execute steps in Playwright against the chosen account** → judge → file-or-log. The interactive execution is required by default — pass `--static-only` only when you intend a doc-only sweep. Connection-class failures during execution follow the network-retry policy in `judge-config.yml.execution.network_retry_count` (default 3) before halting and asking the user.
5. Print summary: status, issue URL (if any), run-id, and whether the interactive phase ran.

Follow `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the procedure. The single-lab path is the same as the full-bootcamp path, just with a list of one.
