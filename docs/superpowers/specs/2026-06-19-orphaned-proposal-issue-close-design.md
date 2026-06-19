# Close orphaned new-lab proposal issues when their PR is closed unmerged

**Date:** 2026-06-19
**Status:** Approved (brainstorming → implementation)
**Scope:** `microsoft/BootcampLabTestPlugin` — build-mode proposal-issue lifecycle only.

## Problem

Build mode (`/build-lab`) makes two GitHub writes for a new lab (or a new use
case authored into a lab): at **B3.5** it opens a tracking **proposal issue**
(`type: new-lab` + `status: in-progress`), and at **B7** it opens the **new-lab
PR**, linking the two with GitHub's `Closes #<n>` keyword
(`config/judge-config.yml` → `build.proposal_issue.link_pr_with: "Closes"`).

GitHub honors `Closes #<n>` **only when the PR is merged.** When the PR is
*closed without merging* — an abandoned build, a superseded run, or a human
closing it in the GitHub UI — nothing closes the issue. It remains **open** and
labeled `status: in-progress` indefinitely, falsely signaling that a lab is
still being authored. These are the "orphaned issues" the user observed.

The plugin is a Claude Code instruction-skill bundle with no long-running
listener, so it cannot react at PR-close time. Reconciliation therefore happens
on the **next plugin run** that touches the same slug (accepted trade-off).

## Goal

After this change, a proposal issue whose linked PR was closed-without-merge is
**closed (not reused)** the next time build mode runs for that slug, and any PR
the plugin itself closes/supersedes has its linked proposal issue closed in the
same step rather than left to the merge-only `Closes` keyword.

## Non-goals

- **Audit-issue ↔ fix-PR pair is explicitly untouched.** A `lab-audit` findings
  issue represents problems in a lab; a closed-unmerged *fix-PR* means the
  proposed fix was rejected/superseded, **not** that the finding is invalid.
  Auto-closing the findings issue there would hide still-valid problems. This
  asymmetry is intentional. (`skills/mcs-lab-fix-pr-filer` is not modified.)
- No GitHub Actions workflow in the target lab repo (`mcs-labs`). Keeping the
  fix self-contained in this plugin preserves portability across lab instances
  and the "build mode makes exactly two GitHub writes" property.
- No real-time / event-driven close. Reconciliation is run-time only.

## Definition: an "orphaned" proposal issue

For a given slug, the open proposal issue (`type: new-lab`) is **orphaned** when
its linked PR — the PR that references it via `Closes #<n>` / the issue's
timeline cross-reference — is in state `CLOSED` with `merged == false`, and no
*open* PR for the slug currently exists.

## Changes

All changes are in `microsoft/BootcampLabTestPlugin`.

### 1. Reconcile at build B3.5 dedup — `skills/mcs-lab-builder/SKILL.md`

Today step 2 ("Dedup") finds an open `type: new-lab` proposal for the slug and
**reuses** it. New behavior, gated on
`build.proposal_issue.close_orphaned_on_pr_close` (default `true`):

1. After finding a candidate open proposal issue, resolve its linked PR. Prefer
   the `Closes #<n>` reference in the open PR set; otherwise inspect the issue's
   timeline / cross-referenced PRs (`gh issue view <n> --json ...` +
   `gh pr list`/`gh pr view`).
2. If the linked PR is `CLOSED` and `merged == false` (and no open PR exists for
   the slug), the proposal is **orphaned**:
   - `gh issue close <n>` with `build.proposal_issue.orphan_close_comment`
     (default: `Linked PR #<pr> was closed without merging; closing this stale
     In-Progress proposal. A fresh proposal will be opened for the new build.`).
   - Do **not** reuse it. Fall through to step 3 (create a fresh proposal).
3. If the linked PR is still `OPEN`, or `merged == true`, or no PR is linked yet
   → behave exactly as today (reuse the open proposal).

`--resume` is unaffected: it still reuses `manifest.proposal_issue` and never
re-probes (an in-progress build's own PR is not orphaned).

### 2. Close inline when the plugin drops its own PR — `skills/mcs-lab-new-lab-pr/SKILL.md`

Add an explicit rule: `Closes #<n>` resolves the proposal **only on merge.**
Whenever this skill closes or supersedes a PR it opened (without merging), it
**must** `gh issue close <proposal_issue.number>` in the same step, with a
comment pointing at the closed PR. Never rely on `Closes` for a non-merge close.

### 3. Config + documentation — `config/judge-config.yml`

Under `build.proposal_issue`, add:

```yaml
    # `Closes #<n>` only fires when the B7 PR is MERGED. If a proposal's PR is
    # closed WITHOUT merging, the issue would otherwise stay open forever as an
    # orphan. When true, the next build run for the slug closes that orphaned
    # proposal (with the comment below) instead of reusing it. See
    # docs/design-decisions.md and skills/mcs-lab-builder/SKILL.md B3.5.
    close_orphaned_on_pr_close: true
    orphan_close_comment: "Linked PR #{pr} was closed without merging; closing this stale In-Progress proposal. A fresh proposal will be opened for the new build."
```

### 4. Changelog + design note

- `CHANGELOG.md`: new `v0.8.1` entry describing the orphaned-proposal close.
- `docs/design-decisions.md`: short entry recording the merge-only semantics of
  `Closes`, the run-time-reconciliation choice, and the audit-issue asymmetry.

## Verification

No automated test harness drives `gh` in this repo, so verification is by
inspection of the edited instructions plus a manual scenario walk-through:

1. Confirm B3.5 dedup branches on linked-PR state and only closes on
   `CLOSED && !merged && no open PR`.
2. Confirm the reuse path is preserved for open / merged / no-PR cases.
3. Confirm `--resume` still bypasses the probe.
4. Confirm config defaults keep zero-config behavior sensible (feature on by
   default; comment templated with `{pr}`).
5. Confirm the audit fix-PR flow is unchanged (no edits under
   `skills/mcs-lab-fix-pr-filer/`).
