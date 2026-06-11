---
name: mcs-lab-pr-appender
description: |
  Append screenshot updates from a lab audit run onto an EXISTING open fix-PR branch in the active instance's lab repo (microsoft/mcs-labs by default). Replaces matched image files in place, makes one commit, pushes, and comments on the PR. Never creates a new branch and never opens a new PR. Invoked by mcs-lab-auditor by default whenever (a) the orchestrator's existing-state probe found an open PR for the slug AND (b) the lab produced new screenshot artifacts. Suppressed by --no-update-screenshots / --no-append-to-pr (CLI) or `issues.pr_append.enabled_by_default: false` (config). Should NOT be invoked directly by the user.
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(gh pr view:*)
  - Bash(gh pr checkout:*)
  - Bash(gh pr comment:*)
  - Bash(gh api:*)
  - Bash(git status:*)
  - Bash(git add:*)
  - Bash(git commit:*)
  - Bash(git push:*)
  - Bash(git stash:*)
  - Bash(git restore:*)
  - Bash(git checkout:*)
  - Bash(git rev-parse:*)
  - Bash(git log:*)
  - Bash(git diff:*)
---

# mcs-lab-pr-appender (sub-skill)

Append refreshed screenshot files from one audit run to one existing open fix-PR's branch on the active instance's repo (`{repo}`). One PR, one commit, one push. Image files only.

This sub-skill exists because the user's standing rule is: **never re-create an open PR**. When the auditor produces new screenshots and an open fix-PR for the same lab is already in flight, the natural place for those updates is that PR — not a brand-new branch and not a brand-new PR.

## Inputs (provided by the orchestrator)

- `slug` — the lab slug (e.g., `mcs-orchestration`).
- `run_id` — the audit run id (e.g., `2026-05-23T1130Z-a1b2`).
- `existing_pr` — the `open_pr` block from `runs/<run-id>/existing-state.yml`:
  ```yaml
  number: 328
  url: https://github.com/{repo}/pull/328
  branch: {branch_prefix}/fix-mcs-orchestration-content-audit
  author: Dewain27
  mergeable: true
  files: [_labs/mcs-orchestration.md, _data/lab-config.yml]
  ```
- `screenshots_dir` — absolute path to `runs/<run-id>/labs/<slug>/screenshots/` containing `.png` files named to match the target lab.
- `repo_path` — absolute path to the local mcs-labs working tree (e.g., `C:\Users\dewainr\mcs-labs`).

## Outputs

- One new commit pushed to `existing_pr.branch`.
- One new comment on `existing_pr` summarizing the changed files.
- An update to `runs/<run-id>/manifest.yml.labs[<slug>].pr_append_result`:
  ```yaml
  pr_append_result:
    pr_number: 328
    branch: {branch_prefix}/fix-mcs-orchestration-content-audit
    commit_sha: <40-char>
    commit_url: https://github.com/{repo}/commit/<sha>
    files_changed: [labs/mcs-orchestration/images/foo.png, ...]
    skipped_reason: null
  ```

If the sub-skill skips for any guardrail reason (see §3), `commit_sha` is `null` and `skipped_reason` is populated.

## Procedure

### 1. Pre-flight guardrails (ANY failure → skip with logged reason)

Run all of these. If any returns a "skip" verdict, stop and write the result to `manifest.yml`.

1. **PR open and mergeable**:
   ```
   gh pr view <number> --repo {repo} --json state,mergeable,mergeStateStatus,headRefName,author
   ```
   - `state` must be `OPEN`. Otherwise skip with `reason: pr_not_open`.
   - `mergeable` must be `MERGEABLE`. `CONFLICTING` → skip with `reason: pr_has_conflicts`. `UNKNOWN` is allowed but logged.
   - `headRefName` must equal `existing_pr.branch` (sanity check against drift). Otherwise skip with `reason: branch_mismatch`.

2. **Author match**:
   - The current `gh` user (`gh api user --jq .login`) must equal `author.login`. Otherwise skip with `reason: not_pr_author` — never push to another contributor's branch.

3. **Branch is not protected**:
   - The branch name must not be `main`, `master`, `develop`, or `release/*`. Otherwise skip with `reason: protected_branch`.

4. **No uncommitted changes in `repo_path`**:
   ```
   git -C <repo_path> status --porcelain
   ```
   Must be empty. If not, stash with `git stash push -u -m "mcs-lab-pr-appender <run_id> <slug>"` and remember to restore at the end (§5). If the stash itself fails, skip with `reason: dirty_worktree`.

5. **Screenshots exist and map to repo files**:
   - Enumerate `*.png` in `screenshots_dir`.
   - For each, compute the target path: `<repo_path>/labs/<slug>/images/<basename>.png`.
   - Skip files whose target does **not** already exist in the repo — this sub-skill replaces existing screenshots only; it never adds new ones (adding a new image is a content decision that belongs in a normal PR, not an automated append).
   - If zero files map to existing repo paths, skip with `reason: no_mapped_screenshots`.

### 2. Checkout, replace, commit, push

```
git -C <repo_path> fetch origin
gh pr checkout <number> --repo {repo}   # checks out existing_pr.branch
```

After checkout, verify the current branch matches `existing_pr.branch`:
```
git -C <repo_path> rev-parse --abbrev-ref HEAD
```
If not, skip with `reason: checkout_failed_branch_mismatch`.

For each mapped screenshot:
- Copy `screenshots_dir/<name>.png` over `repo_path/labs/<slug>/images/<name>.png`.

Then:
```
git -C <repo_path> add labs/<slug>/images/
git -C <repo_path> diff --cached --stat
```
If `--cached --stat` is empty (the new files were byte-identical to the existing ones), skip with `reason: no_visual_diff` — don't make an empty commit.

Commit with the **no-coauthor** rule (per [[feedback_no_claude_coauthor]]):
```
git -C <repo_path> commit -m "chore(<slug>): refresh screenshots from audit <run_id>"
```
No `Co-Authored-By` trailer. No mention of Claude. The PR-append sub-skill MUST NOT add either.

Push:
```
git -C <repo_path> push origin <existing_pr.branch>
```

Capture the new HEAD SHA:
```
git -C <repo_path> rev-parse HEAD
```

### 3. Comment on the PR

```
gh pr comment <number> --repo {repo} --body-file <comment-body>
```

Where `<comment-body>` contains:
```markdown
> Screenshot refresh from audit run `<run_id>` — commit <short-sha>.

Files updated:
- `labs/<slug>/images/<name1>.png`
- `labs/<slug>/images/<name2>.png`
...

These replace the prior screenshots in place. No markdown was edited by the automated appender.
```

### 4. Update manifest

Write `runs/<run-id>/manifest.yml.labs[<slug>].pr_append_result` with the structure shown under "Outputs" above. Set `skipped_reason: null` on success.

### 5. Restore the worktree if we stashed

If §1 step 4 stashed changes, restore them with `git stash pop` after switching back off the PR branch. If `git stash pop` fails (conflict), leave the stash in place and write a clear warning to the run transcript so the user can recover.

Always end on the user's prior branch:
```
git -C <repo_path> checkout -
```

## Anti-patterns

- **Never create a new branch.** The whole point of this sub-skill is to append to existing PRs.
- **Never open a new PR.** If `existing_pr.number` is null, the orchestrator should not have invoked us — and if it did, skip with `reason: no_existing_pr`.
- **Never push to a non-PR branch.** Validate that `gh pr view --json headRefName` matches the branch you're on before pushing.
- **Never add new image files** that don't already exist in the repo. Replacement only — additions are a content decision.
- **Never edit `_labs/<slug>.md` or any non-image file.** That's outside the screenshot-only carve-out.
- **Never amend an existing commit on the PR.** Always make a new commit so the PR history is clear (also avoids forced-update on a shared branch).
- **Never add a Claude co-author trailer.** Per [[feedback_no_claude_coauthor]], commits authored by this sub-skill must read as standard `chore(...)` commits from the user's git identity.
- **Never force-push.** `git push` without `--force` (or `--force-with-lease`).

## Failure handling

- `git push` rejected (someone else pushed in the meantime): pull with `--rebase` (no merge commits), re-push. If the rebase fails, skip with `reason: rebase_conflict` and leave the local branch untouched.
- `gh pr comment` fails: still record the commit SHA in `manifest.yml` and write the comment body to `runs/<run-id>/labs/<slug>/pr-append-comment.md` for manual posting. The push is what matters; the comment is convenience.
- Network failure mid-push: retry once after 15s. Then skip with `reason: push_network_error`.

## Why this is a separate sub-skill (and not part of the orchestrator)

- **Surface area**. The orchestrator runs hundreds of Playwright + LLM-judge steps; this sub-skill makes a handful of `gh`/`git` calls. Keeping them separate keeps the orchestrator's "what could possibly go wrong" surface limited to the audit itself.
- **Guardrails in one place**. Every reason to refuse pushing (wrong author, conflicts, protected branch, etc.) lives in §1 of this file, not scattered across the orchestrator.
- **Reusability**. A future flag like `--append-edits-too` would extend §2 with prose edits, but the same guardrails apply unchanged.
