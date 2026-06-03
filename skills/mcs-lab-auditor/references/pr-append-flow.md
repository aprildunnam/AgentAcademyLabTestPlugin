# PR-append flow (narrow carve-out from "issues only")

This document explains *when* and *why* the orchestrator deviates from its default "read-only on the mcs-labs repo" stance to push a single **screenshots-only** commit onto an existing open fix-PR. The *how* lives in `skills/mcs-lab-pr-appender/SKILL.md`.

> **Note.** This is the lighter of two PR paths. The primary one is `skills/mcs-lab-fix-pr-filer/SKILL.md`, which applies the run's `suggested_correction` markdown diffs + screenshot replacements and either opens a **new** fix-PR on a run-unique branch or appends to the lab's existing **open** fix-PR (ADR-015). The appender below is the screenshots-only complement for the re-audit case where there's nothing to change but the images.

## Why this exists

The mcs-lab-auditor's original design said "never branch, never commit, never push, never PR — issues only." That rule prevents a class of accidents (audit silently editing source code).

But it created a different problem: when re-auditing a lab, the auditor would propose screenshot updates that had to be applied by hand or filed as yet another issue. If a fix-PR for the same lab was already open (the common case), the user wanted those screenshot updates to land *on that PR*, not split across a stale PR + a new issue + a follow-up commit they'd have to make themselves.

So the rule changed to: **default-on append for screenshots to existing fix-PRs, plus opt-out controls for users who want pure read-only behavior**. The carve-out is intentionally narrow — image files only, existing PRs only, same-author only — so the original safety property (no surprise edits to source) holds for everything else.

## Activation

The PR-append path fires when **all** of the following are true:

1. The run was NOT started with `--no-update-screenshots` (or `--no-append-to-pr`).
2. `judge-config.yml.issues.pr_append.enabled_by_default` is `true` (the shipped default).
3. Phase 1.4's `existing-state.yml` shows `labs[<slug>].open_pr` is non-null.
4. The lab's `runs/<run-id>/labs/<slug>/screenshots/` directory contains `.png` files whose basenames match existing files under `labs/<slug>/images/` in the mcs-labs working tree.

If any of those is false, the screenshot files stay local and are referenced (by path) in the issue body. No automated push happens.

The legacy `--update-screenshots` / `--append-to-pr` flags are still accepted but are now no-ops (the behavior they used to enable is the default).

## Guardrails (enforced in `mcs-lab-pr-appender/SKILL.md` §1)

- PR must be **open** and **mergeable** (no conflicts).
- PR author must be the **current `gh` user** — never push to someone else's branch.
- Branch must not be `main`/`master`/`develop`/`release/*`.
- Working tree must be clean (or stashable).
- Screenshots must map to **already-existing** files in the repo. Adding a brand-new image is a content decision and is out of scope.
- No `Co-Authored-By: Claude` trailer (per the user's standing rule on commit metadata).
- No force-push. Ever.

## Failure mode summary

Every reason to refuse pushing maps to a single string in `manifest.yml.labs[<slug>].pr_append_result.skipped_reason`:

| Reason                            | Meaning                                                                |
| --------------------------------- | ---------------------------------------------------------------------- |
| `pr_not_open`                     | The PR closed between Phase 1.4 and the append step.                   |
| `pr_has_conflicts`                | `mergeable: CONFLICTING`. Manual rebase needed before append can run.  |
| `branch_mismatch`                 | `gh pr view` reports a different `headRefName` than `existing_state`.  |
| `not_pr_author`                   | Current `gh` user doesn't match the PR author.                         |
| `protected_branch`                | Branch is on the protected list.                                       |
| `dirty_worktree`                  | Local tree had uncommitted changes that couldn't be stashed.           |
| `no_mapped_screenshots`           | None of the new `.png` files matched an existing repo image.           |
| `no_visual_diff`                  | Files were byte-identical to what's already in the repo.               |
| `no_existing_pr`                  | The sub-skill was invoked but the orchestrator passed `open_pr: null`. |
| `checkout_failed_branch_mismatch` | `gh pr checkout` succeeded but `git rev-parse` reports a wrong branch. |
| `push_network_error`              | `git push` failed after one retry.                                     |
| `rebase_conflict`                 | Remote moved during the run and the local rebase didn't apply cleanly. |

Skips are logged but do not fail the audit — the rest of the lab's disposition (issue comment, audit-history entry) still happens.

## Future extensions (not yet implemented)

- `--append-edits-too`: extend `mcs-lab-pr-appender/SKILL.md` §2 to also apply prose edits from `suggested_correction.proposed_text` to `_labs/<slug>.md`. Same guardrails; explicit opt-in.
- `--append-new-images`: relax the "must already exist" rule. Useful for net-new lab content, but requires a stronger naming convention to avoid accidental clutter.

Until those land, the sub-skill remains a screenshot-replacement pipe and nothing more.
