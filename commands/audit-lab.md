---
description: Audit a single mcs-labs bootcamp lab end-to-end; comment on existing open issue or file a new one (never duplicates); refresh screenshots on existing open fix-PR by default.
argument-hint: "<lab-slug> [--no-issue] [--force-issue] [--dry-run] [--no-update-screenshots]"
---

# /audit-lab

You are auditing a single bootcamp lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab slug (e.g. `core-concepts-analytics-evaluations`). Flags:
- `--dry-run` — parse the lab into `steps.json` only. No browser activity, no issue, no audit-history entry.
- `--no-issue` — execute the lab but never file or comment on a GitHub issue.
- `--force-issue` — file an issue even if the lab is in `non_deterministic_lab_slugs`. Does NOT bypass open-issue dedup — an existing open issue for this lab is always commented on, never duplicated.
- `--no-update-screenshots` (alias `--no-append-to-pr`) — opt out of the **default-on** screenshot refresh. By default, if the lab has an open fix-PR AND the run produced refreshed screenshot files, the plugin pushes one commit replacing those screenshots onto the PR branch. Screenshot files only; same-author only; mergeable PRs only; never creates a new branch or PR. The legacy `--update-screenshots` / `--append-to-pr` flags are still accepted as no-ops for backwards compatibility.

## Dedup guarantee (always on)

This command will **never create a second open GitHub issue for a lab that already has one open**, and it will **never open a new PR**. Phase 1.4 of the orchestrator probes for existing open issues + PRs for the slug before doing anything else; the disposition step uses that result. Findings already covered by the existing issue (matched by per-finding fingerprint) are dropped before commenting.

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
