---
description: Audit a single mcs-labs bootcamp lab end-to-end; file one GitHub issue with findings if any, or log a clean pass locally.
argument-hint: "[<lab-slug>] [--no-issue] [--force-issue] [--dry-run] [--static-only] [--interactive-only] [--account-prompt <mode>]"
---

# /audit-lab

You are auditing a single bootcamp lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab slug (e.g. `core-concepts-analytics-evaluations`). The slug is **optional** — when omitted, the orchestrator runs the lab picker (Phase 1.5 Q4 in `SKILL.md`) so the user can choose interactively. Flags:
- `--dry-run` — parse the lab into `steps.json` only. No browser activity, no issue, no audit-history entry.
- `--no-issue` — execute the lab (interactive UI phase still runs) but never file a GitHub issue.
- `--force-issue` — file an issue even if the lab is in `non_deterministic_lab_slugs`.
- `--static-only` — skip the interactive UI phase; do static checks only. The interview skips the phase-mix question (Q2). Default (no flag) is to ask interactively.
- `--interactive-only` — skip the static fan-out; assumes a prior run produced `findings-static.json`. The interview skips the phase-mix question (Q2).
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run.

## Pre-flight context

- bootcamp lab slugs: !`powershell -NoProfile -Command 'Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15'`
- cached account: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { (Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw | ConvertFrom-Json).user_id } else { "(none)" }'`

## Your task

Invoke the `mcs-lab-auditor` skill for the given (or interactively-picked) slug:

1. **Slug resolution**: If a slug was passed positionally, validate it exists in `_data/lab-config.yml` `lab_orders.event.bootcamp` AND `_labs/<slug>.md` exists. Abort with a clear message if either is missing. If no slug was passed, defer to the Phase 1.5 Q4 lab picker.
2. Pre-flight (configs, `gh` auth).
3. **Run-start interview** (Phase 1.5 in `SKILL.md`): asks the account question (Q1, governed by `account_prompt_mode`) and the phase-mix question (Q2, unless `--static-only`/`--interactive-only` was passed). The scope question (Q3) is auto-answered (scope = single lab from arg 1, or Q4 picker if no arg). Mandatory unless a CLI flag short-circuits a specific question. Even on `--static-only` the account prompt may run if you want the static pass recorded against a known account; it's safe to skip otherwise.
4. Single-lab loop: parse → **execute steps in Playwright against the chosen account** (when `phase_mix` includes interactive) → judge → file-or-log. Connection-class failures during execution follow the network-retry policy in `judge-config.yml.execution.network_retry_count` (default 3) before halting and asking the user.
5. Print summary: status, issue URL (if any), run-id, and which phase(s) actually ran.

Follow `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the procedure. The single-lab path is the same as the full-bootcamp path, just with a list of one and the scope question short-circuited.
