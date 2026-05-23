---
description: Audit every lab in the mcs-labs bootcamp event end-to-end; comment on existing open issue or file a new one (never duplicates); refresh screenshots on existing open fix-PRs by default.
argument-hint: "[--resume <run-id>] [--labs slug1,slug2,...] [--no-issue] [--force-issue] [--no-update-screenshots]"
---

# /audit-bootcamp

You are starting a full bootcamp audit run.

## Arguments

Arguments passed: `$ARGUMENTS`

Parse these flags:
- `--resume <run-id>` — resume a previously interrupted run; skip labs already marked `done`/`issue_filed`/`skipped`.
- `--labs <csv>` — restrict to a comma-separated subset of slugs from the bootcamp list.
- `--no-issue` — execute the labs but never file or comment on GitHub issues (everything goes to local log only).
- `--force-issue` — file issues even for labs in `non_deterministic_lab_slugs` (default skips those). Does NOT bypass open-issue dedup — even with this flag, existing open issues are still commented on, never duplicated.
- `--no-update-screenshots` (alias `--no-append-to-pr`) — opt out of the **default-on** screenshot refresh. By default, when a lab has an open fix-PR (per Phase 1.4 probe) AND the run produced refreshed screenshot files, the plugin pushes one commit replacing those screenshots onto the PR branch. Screenshot files only; same-author only; mergeable PRs only; never creates a new branch or PR. The legacy `--update-screenshots` / `--append-to-pr` flags are still accepted as no-ops for backwards compatibility.

## Dedup guarantee (always on)

This command will **never create a second open GitHub issue for a lab that already has one open**, and it will **never open a new PR**. Phase 1.4 of the orchestrator probes `gh issue list` and `gh pr list` per slug and writes the result to `runs/<run-id>/existing-state.yml`; every per-lab disposition step consults it. Findings that already appear in the existing issue (matched by per-finding fingerprint) are dropped before commenting — if every finding is a duplicate, no comment is posted.

## Pre-flight context

- gh auth: !`gh auth status 2>&1 | Select-Object -First 5`
- mcs-labs repo present: !`if (Test-Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml") { "yes" } else { "MISSING — abort" }`
- bootcamp lab list source: !`Get-Content "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" | Select-String -Pattern "bootcamp_lab_orders" -Context 0,15`
- cached account meta: !`if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw } else { "(no cached account)" }`

## Your task

Invoke the `mcs-lab-auditor` skill following its full lifecycle:

1. Pre-flight (read the configs, enumerate the lab list, check `gh` auth and `microsoft/mcs-labs` viewer permission).
2. **Phase 1.4 — Probe existing GitHub state** (`gh issue list` + `gh pr list` per slug) and write `runs/<run-id>/existing-state.yml`. Mandatory.
3. Run-start account prompt (offer cached account or new workshop-code redemption).
4. Per-lab loop: parse → execute steps in Playwright → judge each step → checkpoint per scene → **disposition** (comment on existing open issue OR file new issue if none exists; **by default**, also append refreshed screenshots to the lab's existing open fix-PR if one is found, unless `--no-update-screenshots` was passed).
5. Wrap-up: close the browser, print summary, save manifest.

Read `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md` for the full procedure and refer to the `references/` files as needed. Do not skip the run-start account prompt — the user expects it.

If `--resume` is provided, do NOT prompt for a new account if the cached one is still valid (check `expires_at`).

If `--dry-run` is in the arguments, treat it as a per-lab dry-run for every lab (parse only, no browser activity).
