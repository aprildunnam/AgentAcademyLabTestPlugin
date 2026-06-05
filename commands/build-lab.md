---
description: Interactively build a NEW mcs-labs lab end-to-end via Playwright, audit-gate it, and open a PR. Event/workshop-agnostic.
argument-hint: "[<lab-name>] [--resume <build-id>] [--mode guided|scenario] [--no-pr] [--account-prompt <mode>] [--model-preset <optimized|opus|custom>]"
---

# /build-lab

You are **building a new lab** for the mcs-labs repository — not auditing an existing one. You drive a real browser through the lab you are authoring, capture screenshots and write the instructions as you go, confirm every step with the user, then re-run the finished lab through the existing audit engine as a quality gate before opening a PR.

This mode is **event/workshop-agnostic**: the lab is built and tested as a standalone lab. Attaching it to an event (bootcamp, MCS-in-a-Day, a build-a-thon, etc.) is an optional, separate choice — never assumed.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is an **optional** free-text lab name (e.g. `"Build a Returns Triage Agent"`); it is slugified to a kebab `<slug>`. When omitted, B3 asks for the name. Flags:
- `--resume <build-id>` — resume an interrupted build from `runtime/builds/<build-id>/session-state.yml`. Inherits mode, slug, and lab metadata from the prior `manifest.yml`; restarts at the first unconfirmed step.
- `--mode <guided|scenario>` — skip the B1 interaction-mode question. `guided` = you dictate each step; `scenario` = you give a scenario up front and the AI proposes one step at a time. Both confirm every step.
- `--no-pr` — run B0–B6 (build + audit gate) but stop before B7. Leaves the assembled draft + screenshots under `runtime/builds/<build-id>/draft/` and prints the registration steps. The mcs-labs working tree is never modified.
- `--account-prompt <always|only_if_expired|only_if_missing>` — override `judge-config.yml.execution.account_prompt_mode` for this build.
- `--model-preset <optimized|opus|custom>` — choose the sub-agent model preset (used by the B6 audit gate) without the interactive prompt. Orchestrator is always Opus.

## Pre-flight context

- cached account: !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode JsonField -Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -JsonField user_id -Fallback "(none)"`
- mcs-labs repo (Projects): !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode Exists -Path "C:\Users\dewainr\Projects\mcs-labs\_data\lab-config.yml" -Fallback "MISSING"`
- mcs-labs repo (home): !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode Exists -Path "C:\Users\dewainr\mcs-labs\_data\lab-config.yml" -Fallback "MISSING"`
- existing lab ids (collision check, Projects): !`pwsh -NoProfile -File "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\scripts\Get-PathOrFallback.ps1" -Mode GrepContext -Path "C:\Users\dewainr\Projects\mcs-labs\_data\lab-config.yml" -Pattern "id:" -ContextAfter 0 -Fallback "MISSING - resolve mcs-labs path in B0"`

## Your task

Invoke the `mcs-lab-builder` skill and follow `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-builder/SKILL.md`. The skill defines the full build lifecycle (phases B0–B7):

1. **B0 preflight** — assert Opus orchestrator; check `gh` auth + repo perm; **resolve the mcs-labs repo path** (the candidates above — never assume `C:\Users\dewainr\mcs-labs`, the repo moved to `…\Projects\mcs-labs`); **detect the registration mechanism** (root `lab-config.yml` + `Generate-Labs.ps1` vs. direct writes — see `references/lab-registration-spec.md`); load configs.
2. **B1 interview** — account question (cached / redeem / abort — same matrix as the auditor's Q1) + interaction mode (`guided` / `scenario`), unless a CLI flag answered them.
3. **B2 navigate-home** — sign in with the chosen account and reach the Copilot Studio Home page (Welcome modal dismissed).
4. **B3 name + scaffold** — ask the lab name (or use arg 1), slugify, collision-check, seed the build workspace, capture lab metadata, and optionally offer attaching to ANY event/workshop (read dynamically from `lab-config.yml` — never hardcode bootcamp).
4.5. **B3.5 file the proposal issue** — open a tracking issue on `microsoft/mcs-labs` labeled `type: new-lab` + `status: in-progress` so the new lab is visible as an **In Progress** proposal while you build it (deduped per slug; reused on `--resume`). The final PR closes it.
5. **B4 capture loop** — the per-step authoring loop: snapshot → step intent (you dictate, or AI proposes) → execute in Playwright → screenshot → write the instruction + tips → confirm → checkpoint. Repeat per scene/use-case until the lab is complete.
6. **B5 prose assembly** — render the full `labs/<slug>/README.md` from the step ledger, matching sibling-lab format.
7. **B6 audit gate** — register + materialize the lab, then run the existing audit engine against it with **all GitHub writes suppressed**; feed any `broken`/`unclear` findings back into B4 until a clean pass. Skipped only if the mcs-labs registration toolchain is unavailable (then halt with guidance).
8. **B7 generate + PR** — open a PR on `microsoft/mcs-labs` via `mcs-lab-new-lab-pr`. Skipped under `--no-pr`.

Never modify the mcs-labs working tree before B6/B7. Never log the workshop password. Resume cleanly via `--resume <build-id>`.
