---
description: Audit a single mcs-labs bootcamp lab end-to-end; file one GitHub issue with findings if any, or log a clean pass locally.
argument-hint: "<lab-slug> [--no-issue] [--force-issue] [--dry-run]"
---

# /audit-lab

You are auditing a single bootcamp lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab slug (e.g. `core-concepts-analytics-evaluations`). Flags:
- `--dry-run` — parse the lab into `steps.json` only. No browser activity, no issue, no audit-history entry.
- `--no-issue` — execute the lab but never file a GitHub issue.
- `--force-issue` — file an issue even if the lab is in `non_deterministic_lab_slugs`.

## Pre-flight context

- bootcamp lab slugs: !`Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15`
- cached account: !`if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { (Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw | ConvertFrom-Json).user_id } else { "(none)" }`

## Your task

Invoke the `mcs-lab-auditor` skill for the single given slug:

1. Validate the slug exists in `_data/lab-config.yml` `lab_orders.event.bootcamp` AND `_labs/<slug>.md` exists. Abort with a clear message if either is missing.
2. Pre-flight (configs, `gh` auth).
3. Run-start account prompt — **unless `--dry-run` is set**, in which case skip Phase 1.5 entirely.
4. Single-lab loop: parse → execute → judge → file-or-log.
5. Print summary: status, issue URL (if any), run-id.

Follow `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the procedure. The single-lab path is the same as the full-bootcamp path, just with a list of one.
