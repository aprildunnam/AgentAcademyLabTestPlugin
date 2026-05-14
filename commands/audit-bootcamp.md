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
- `--no-issue` — execute the labs but never file GitHub issues (everything goes to local log only).
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those).

## Pre-flight context

- gh auth: !`gh auth status 2>&1 | Select-Object -First 5`
- mcs-labs repo present: !`if (Test-Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml") { "yes" } else { "MISSING — abort" }`
- bootcamp lab list source: !`Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15`
- cached account meta: !`if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw } else { "(no cached account)" }`

## Your task

Invoke the `mcs-lab-auditor` skill following its full lifecycle:

1. Pre-flight (read the configs, enumerate the lab list, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. Run-start account prompt (offer cached account or new workshop-code redemption).
3. Per-lab loop: parse → execute steps in Playwright → judge each step → checkpoint per scene → file issue or log clean.
4. Wrap-up: close the browser, print summary, save manifest.

Read `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the full procedure and refer to the `references/` files as needed. Do not skip the run-start account prompt — the user expects it.

If `--resume` is provided, do NOT prompt for a new account if the cached one is still valid (check `expires_at`).

If `--dry-run` is in the arguments, treat it as a per-lab dry-run for every lab (parse only, no browser activity).
