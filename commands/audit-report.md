---
description: Print a local summary of recent mcs-lab-auditor runs from runtime/audit-history.yml. No browser activity.
argument-hint: "[<run-id>]"
---

# /audit-report

You are summarizing past audit runs for the user. No browser activity, no issue filing, no judge calls.

## Arguments

Arguments passed: `$ARGUMENTS`

If a positional argument is provided, treat it as a `<run-id>` and show only that run. Otherwise show a rolling summary of recent runs.

## Pre-flight context

- audit history present: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\audit-history.yml") { (Get-Item "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\audit-history.yml").Length.ToString() + " bytes" } else { "MISSING — no runs yet" }'`
- runs directory contents: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\runs") { Get-ChildItem "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\runs" -Directory | Select-Object -Last 5 -ExpandProperty Name } else { "(no runs)" }'`

## Your task

1. Read `~/.claude/plugins/mcs-lab-auditor/runtime/audit-history.yml`. If missing, tell the user no runs have been recorded yet and suggest `/audit-bootcamp` or `/audit-lab <slug>`.

2. If a `<run-id>` argument was given:
   - Filter to entries where `run_id == <given>`.
   - Print a per-lab table: `slug | status | duration | findings (H/M/L) | issue_url`.
   - Print run-level totals at the bottom: total labs, count by status, total duration.

3. Otherwise (no argument):
   - Group entries by `run_id`, sort by latest `finished_at` descending.
   - Print the most recent 5 runs, one block per run.
   - For each run, show: run-id, started_at, account_user_id, labs total, status breakdown (pass / issue_filed / error / skipped), list of issue URLs filed.
   - At the very end, list any labs from `_data/lab-config.yml` `lab_orders.event.bootcamp` that have NEVER been audited.

Output format: terse, monospace-friendly. Use unicode box-drawing only if the user's terminal supports it — otherwise plain ASCII tables.

If the user passes both a `<run-id>` AND additional flags, error with usage info instead of guessing.
