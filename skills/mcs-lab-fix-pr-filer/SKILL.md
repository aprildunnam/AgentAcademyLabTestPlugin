---
name: mcs-lab-fix-pr-filer
description: |
  After mcs-lab-issue-filer has filed (or commented on) the audit issue for a lab, apply the findings' suggested_correction diffs to the lab markdown, copy any proposed_screenshot_replacement images into labs/<slug>/images/, commit on branch `dewain/fix-<slug>-content-audit`, push, and open a PR titled `<slug>: fix audit findings from #<issue-number>` with body "Closes #<issue-number>". Should NOT be invoked directly by the user — the orchestrator calls it after mcs-lab-issue-filer returns the issue number.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(git status:*)
  - Bash(git checkout:*)
  - Bash(git branch:*)
  - Bash(git fetch:*)
  - Bash(git pull:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push:*)
  - Bash(git log:*)
  - Bash(git diff:*)
  - Bash(gh pr list:*)
  - Bash(gh pr view:*)
  - Bash(gh pr create:*)
  - Bash(gh pr edit:*)
  - Bash(cp:*)
---

# mcs-lab-fix-pr-filer (sub-skill)

Apply the audit's suggested corrections to the actual lab files in `microsoft/mcs-labs`, commit them on a per-slug fix branch, and open (or update) the PR that closes the audit issue.

## Inputs (assumed present from the orchestrator)

- `runs/<run-id>/labs/<slug>/findings.json` — same file the issue-filer read.
- `runs/<run-id>/labs/<slug>/screenshots/proposed/` — proposed replacement images keyed to `findings[*].proposed_screenshot_replacement_for` paths.
- `<plugin>/config/judge-config.yml` — for branch naming convention (`issues.pr_append.pr_branch_pattern`, default `dewain/fix-{slug}-content-audit`).
- `C:\Users\dewainr\mcs-labs\` — clone of microsoft/mcs-labs.
- `issue_number` — returned by `mcs-lab-issue-filer`. Required.
- `lab_slug`, `run_id` — passed through.

## Outputs

- New or updated branch `dewain/fix-<slug>-content-audit` on `microsoft/mcs-labs`.
- New or updated PR titled `<slug>: fix audit findings from #<issue-number>` with body containing `Closes #<issue-number>`.
- `runs/<run-id>/labs/<slug>/pr-url.txt` — convenience file for the orchestrator's summary.
- Updated `manifest.yml.labs[<slug>]`: `status: issue_and_pr_filed`, `pr_url`, `pr_action: created | appended | skipped_no_changes`.

## Procedure

### 1. Prepare the working tree

```bash
cd C:\Users\dewainr\mcs-labs
git fetch origin main
```

If there are uncommitted changes in the working tree, stash them with a clear label and restore the user's prior `HEAD`. (Never clobber unrelated in-flight work.)

### 2. Resolve the branch

Branch name: `dewain/fix-<slug>-content-audit` (from `judge-config.yml.issues.pr_append.pr_branch_pattern`).

- If an open PR already exists on that branch (`gh pr list --head <branch> --state open`):
  - Verify it's authored by the current `gh` user (`pr_append.require_same_author`) and mergeable (`pr_append.require_mergeable`).
  - If guardrails pass, `git checkout <branch>` and `git pull --ff-only origin <branch>`. Set `pr_action: appended`.
  - If guardrails fail, abort the PR step (the orchestrator records this as a soft failure: issue was filed but PR could not be appended; the user is told to inspect the branch).
- If no open PR exists:
  - If the branch exists locally or remotely but is stale (e.g. behind a merged prior PR), rename it out of the way (`git branch -m <branch> <branch>-rev<N>`) or delete it after confirming no open PR depends on it.
  - Create a fresh branch from main: `git checkout -b <branch> origin/main`. Set `pr_action: created`.

### 3. Apply markdown corrections

For each finding in `findings.json` where `outcome ∈ {broken, unclear}` AND `suggested_correction` is non-null:

1. Read the lab file `_labs/<slug>.md`.
2. Apply a literal string replacement:
   - `old_string = suggested_correction.original_text`
   - `new_string = suggested_correction.proposed_text`
3. If the `old_string` is no longer present (the lab has changed since the audit), record `{finding_id, applied: false, reason: original_text_not_found}` in `runs/<run-id>/labs/<slug>/pr-apply-log.json` and continue with the next finding.
4. If the replacement would match in multiple places, prefer the location with the line number closest to `finding.evidence.line_number` if recorded; otherwise apply once at the first match and warn.

Some corrections span multiple lines or require reordering content (new UC, scene swap, etc.). Findings whose `suggested_correction.scope == "scene"` should NOT be auto-applied — leave them for human review and record `{finding_id, applied: false, reason: scope_scene_requires_manual}`.

### 4. Apply screenshot replacements / additions

For each finding with non-null `proposed_screenshot_replacement`:

1. Resolve source path: `runs/<run-id>/labs/<slug>/screenshots/proposed/<proposed_screenshot_replacement>` (the audit subagents save replacements here).
2. Resolve destination:
   - If `proposed_screenshot_replacement_for` is non-null (replacing an existing image): destination is `labs/<slug>/<proposed_screenshot_replacement_for>` (e.g. `labs/<slug>/images/foo.png`).
   - If null (adding a new image): destination is `labs/<slug>/images/<proposed_screenshot_replacement>` and ensure the lab markdown is updated to reference it (the markdown reference should be in the same finding's `suggested_correction.proposed_text` if the parser caught it).
3. `cp <source> <destination>`.

Track `screenshots_replaced` count for the commit message.

### 5. Sanity check

```bash
git diff --stat
```

If the working tree has NO changes after steps 3 and 4 (every correction failed to apply, every screenshot was already current), set `pr_action: skipped_no_changes` and abort the PR step. Record the reason in `pr-apply-log.json`.

### 6. Commit

```bash
git add _labs/<slug>.md labs/<slug>/images/
git commit -m "$(cat <<EOF
<slug>: fix audit findings from #<issue-number>

Auto-applied by mcs-lab-fix-pr-filer from audit run <run-id>.

Markdown corrections: <N applied> of <N total> findings.
Screenshot updates: <N replaced> + <N added>.

See issue #<issue-number> for full audit details and per-finding evidence.

Closes #<issue-number>
EOF
)"
```

Commit author: use the current `gh auth status` user (e.g. `dewainr@microsoft.com` / `Dewain Robinson`) via `git -c user.email=... -c user.name=...`. Never sign with a Claude / bot identity unless explicitly configured.

### 7. Push

```bash
git push -u origin <branch>
```

If push fails because the remote branch already exists and is ahead (concurrent run), `git pull --rebase origin <branch>` then re-push.

### 8. Open or update the PR

If `pr_action: created`:

```bash
gh pr create \
  --repo microsoft/mcs-labs \
  --base main \
  --head <branch> \
  --title "<slug>: fix audit findings from #<issue-number>" \
  --body-file <pr-body.md>
```

PR body template (`runs/<run-id>/labs/<slug>/pr-body.md`):

```markdown
Closes #<issue-number>.

Implements the corrections from the mcs-lab-auditor run on `<slug>` (run id `<run-id>`).

## What changed

<for each applied finding: a 1-2 line bullet describing the fix>

## How it was verified

Every change was driven by the audit run's Playwright execution on a fresh workshop-issued tenant account. Per-finding evidence (screenshots, accessibility snapshots, console + network logs) is stored locally under `~/.claude/plugins/mcs-lab-auditor/runtime/runs/<run-id>/labs/<slug>/`.

<if any findings were NOT auto-applied:>
## Findings deferred to human review

<for each unapplied finding: a bullet with the reason from pr-apply-log.json>
```

If `pr_action: appended`:
- Just push (already done in step 7). Then `gh pr comment <pr-number> --body "Appended fixes from audit run <run-id>: <N> markdown corrections, <N> screenshot updates."`.

Capture the resulting PR URL.

### 9. Record the outcome

Update `runs/<run-id>/manifest.yml`:

```yaml
labs:
  <slug>:
    status: issue_and_pr_filed
    issue_url: <from issue-filer>
    issue_action: created | commented
    pr_url: <captured above>
    pr_action: created | appended | skipped_no_changes
    finished_at: <iso-timestamp>
```

Append to `runtime/audit-history.yml`:

```yaml
- run_id: <run-id>
  lab_slug: <slug>
  status: issue_and_pr_filed
  issue_url: <...>
  pr_url: <...>
  findings_applied: <N>
  findings_deferred: <N>
```

Write `runs/<run-id>/labs/<slug>/pr-url.txt` containing just the PR URL for the orchestrator's end-of-run summary.

## Important rules

- **Never force-push.** `pr_append.allow_force_push` is `false` and remains so.
- **Never modify a closed/merged PR's branch.** Always check open-PR state before pushing. See [[feedback_no_push_to_merged_pr]].
- **Respect same-author guardrail.** If the current `gh` user does not match the PR author on an existing open PR, abort the append step and leave the issue-filer's record as the only output for this lab.
- **Restore the user's working tree.** If you stashed changes at the start, `git stash pop` (or leave the stash with a clear label and tell the user how to recover) — never silently lose work.
- **Defer scene-scope corrections.** Anything bigger than a phrase- or step-scope replacement should land in the PR body's "Findings deferred to human review" section, not in the commit. Large rewrites (e.g., adding a whole new use case) should be handled by the orchestrator at audit time, not auto-applied here.

## What to do when stuck

- **`original_text` not found in markdown**: lab has drifted since the audit. Record in `pr-apply-log.json` and continue.
- **`proposed_screenshot_replacement` source missing**: subagent didn't save the file. Skip the image update and record in pr-apply-log. The PR still ships the markdown corrections; the screenshot finding remains in the issue for human attention.
- **Branch is up-to-date with main and no changes apply**: still no-op — set `pr_action: skipped_no_changes` and don't push an empty commit.
- **`gh pr create` fails**: leave the branch pushed (the commits are valuable), record the error in `pr-apply-log.json`, and tell the user the manual PR-create command they can run.
