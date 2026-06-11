---
description: Audit a single mcs-labs bootcamp lab end-to-end; file one GitHub issue with findings if any, or log a clean pass locally.
argument-hint: "[<lab-slug>] [--no-issue] [--force-issue] [--dry-run] [--static-only] [--interactive-only] [--account-prompt <mode>] [--model-preset <optimized|opus|custom>]"
---

# /audit-lab

You are auditing a single bootcamp lab.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab slug (e.g. `core-concepts-analytics-evaluations`). The slug is **optional** — when omitted, the orchestrator runs the lab picker (Phase 1.5 Q4 in `SKILL.md`) against the **full all-labs catalog** (`lab_metadata.*`), not constrained to any one event. Flags:
- `--dry-run` — parse the lab into `steps.json` only. No browser activity, no issue, no audit-history entry.
- `--no-issue` — execute the lab (interactive UI phase still runs) but never file a GitHub issue.
- `--force-issue` — file an issue even if the lab is in `non_deterministic_lab_slugs`.
- `--static-only` — skip the interactive UI phase; do static checks only. The interview skips the phase-mix question (Q2). Default (no flag) is to ask interactively.
- `--interactive-only` — skip the static fan-out; assumes a prior run produced `findings-static.json`. The interview skips the phase-mix question (Q2).
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this run.
- `--model-preset <optimized|opus|custom>` — choose the sub-agent model preset without interactive Q2a. Orchestrator is always Opus.
- `--instance <name>` — which lab instance to operate on (repo + clone URL +
  training portal + branch prefix). Resolved by `scripts/Resolve-LabInstance.ps1`.
  Order: this flag → `$env:LAB_INSTANCE` → your `lab-instances.yml`
  `default_instance` → the shipped `mcs-labs`. Run
  `pwsh -File scripts/Resolve-LabInstance.ps1 -Mode Status` to see the active one.

## Pre-flight context

- plugin version: !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Test-PluginVersion.ps1"`
- mcs-labs repo (resolved + updated): !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Status`
- all-labs catalog (id → title): !`pwsh -NoProfile -Command '$r = & "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Path -NoPull; & "$env:CLAUDE_PLUGIN_ROOT\scripts\Get-PathOrFallback.ps1" -Mode GrepContext -Path "$r\_data\lab-config.yml" -Pattern "^lab_metadata:" -ContextAfter 20 -Fallback "MISSING - lab-config.yml not found"'`
- cached account: !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Get-PathOrFallback.ps1" -Mode JsonField -Path "$env:CLAUDE_PLUGIN_ROOT\runtime\account\account.meta.json" -JsonField user_id -Fallback "(none)"`
- active lab instance: !`pwsh -NoProfile -File "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabInstance.ps1" -Mode Status`

## Your task

Invoke the `mcs-lab-auditor` skill for the given (or interactively-picked) slug:

1. **Slug resolution**: If a slug was passed positionally, validate it exists in `_data/lab-config.yml.lab_metadata.*.id` (the full all-labs catalog) AND `_labs/<slug>.md` exists. Abort with a clear message if either is missing. If no slug was passed, defer to the Phase 1.5 Q4 lab picker, which uses the full all-labs catalog as its picker source (not constrained to any event).
2. Pre-flight (configs, `gh` auth).
3. **Run-start interview** (Phase 1.5 in `SKILL.md`): asks the account question (Q1, governed by `account_prompt_mode`) and the phase-mix question (Q2, unless `--static-only`/`--interactive-only` was passed). The scope question (Q3) is auto-answered (scope = single lab from arg 1, or Q4 picker if no arg). Mandatory unless a CLI flag short-circuits a specific question. Even on `--static-only` the account prompt may run if you want the static pass recorded against a known account; it's safe to skip otherwise. If Q1 goes through redemption (or no cache exists) and `workshop_portal_url` is still `REPLACE_ME_ON_FIRST_RUN`, the redemption flow must auto-prompt for `Workshop portal URL`, validate URL format, persist it to the active instance's source (the user's `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml` inline `portal:`, otherwise `config/workshop.yml`), re-materialize `runtime/account/active-portal.yml`, and then continue.
4. Single-lab loop: parse → **execute steps in Playwright against the chosen account** (when `phase_mix` includes interactive) → judge → file-or-log. Connection-class failures during execution follow the network-retry policy in `judge-config.yml.execution.network_retry_count` (default 3) before halting and asking the user.
5. Print summary: status, issue URL (if any), run-id, and which phase(s) actually ran.

Follow `$env:CLAUDE_PLUGIN_ROOT/skills/mcs-lab-auditor/SKILL.md` for the procedure. The single-lab path is the same as the full-event path, just with `scope: one`, `event: null`, and a scope_labs list of length 1. Cross-lab consistency findings still surface in single-lab runs — the fan-in compares this lab's fingerprints against the most recent prior-run fingerprints for every sibling lab in the catalog. Labs that have never been audited contribute nothing.
