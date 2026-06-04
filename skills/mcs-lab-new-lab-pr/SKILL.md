---
name: mcs-lab-new-lab-pr
description: |
  Open a PR on microsoft/mcs-labs that adds a NEW lab built by mcs-lab-builder. Stages the assembled `labs/<slug>/README.md` + screenshots, applies the registration entry (root `lab-config.yml` + generator, or direct `_data/lab-config.yml` + `_labs/<slug>.md` writes — per the detected mechanism), commits everything in one commit on a run-unique branch off `origin/main`, and opens the PR. Invoked by mcs-lab-builder at B7 — NOT directly by the user. Do not use this for audit fixes (that is mcs-lab-fix-pr-filer, which patches an existing lab).
allowed-tools:
  - Read
  - Glob
  - Grep
  - Write
  - Edit
  - PowerShell
  - Bash(git*)
  - Bash(gh pr create:*)
  - Bash(gh pr list:*)
  - Bash(gh pr comment:*)
---

# mcs-lab-new-lab-pr (sub-skill)

Open the PR for a freshly-built lab. You are called by `mcs-lab-builder` at B7 with: `build_id`, `mcs_labs_repo` (resolved absolute path), `slug`, `registration_mode` (`generate` | `direct`), the lab metadata + `order` + `journeys`, the optional `events` list, and the build workspace path `runtime/builds/<build-id>/`. The audit gate has already passed (or the user accepted a draft PR with residual findings listed by the orchestrator).

**Why a separate skill from `mcs-lab-fix-pr-filer`.** That filer's contract is: patch an existing `_labs/<slug>.md` from `suggested_correction` diffs and replace images, with OPEN-PR-dedup keyed to a lab's audit history. A new lab has no existing markdown to patch and no findings diffs — it adds a whole folder, a registration entry, and (in generate mode) generated output. Keeping this separate preserves both skills' contracts.

## Flow

1. **Prepare the working tree.**
   ```
   cd <mcs_labs_repo>
   git fetch origin main
   ```
   Stash any unrelated in-flight changes with a labeled stash and restore them at the end — never clobber the user's uncommitted work. Record whether a stash was created.

2. **Create the branch (run-unique, off fresh main).**
   ```
   branch = build.issues.new_lab_pr.pr_branch_pattern   # default "dewain/new-lab-{slug}-{build_id}"
   git checkout -b "<branch>" origin/main
   ```
   The `{build_id}` suffix makes the branch unique — re-running build for the same slug yields a fresh build_id and a fresh branch, so a merged/closed prior PR never collides. (No open-PR append path: a new lab is one-shot.)

3. **Stage the lab content.**
   - Copy `runtime/builds/<build_id>/draft/README.md` → `<mcs_labs_repo>/labs/<slug>/README.md`.
   - Copy `runtime/builds/<build_id>/draft/images/*` → `<mcs_labs_repo>/labs/<slug>/images/` (create the dir; same-name copy — the README references `images/<file>`).
   - These may already be staged by the B6 gate; copying is idempotent.

4. **Apply registration** (per `skills/mcs-lab-builder/references/lab-registration-spec.md`):
   - **generate mode:** add the one entry to the root `lab-config.yml` (`title`, `difficulty`, `duration`, `section`, `order`, `journeys`, and `events: [...]` only if `events` is non-empty), then run the generator (`pwsh -NoProfile -File <mcs_labs_repo>/scripts/Generate-Labs.ps1 -SkipPDFs` or the path from config). Commit the generated `_labs/<slug>.md` + `_data/lab-config.yml` too.
   - **direct mode (current reality):** add the lab entry directly to `_data/lab-config.yml` (matching the existing `lab_metadata` / `lab_journeys` / `lab_orders` shape), and write `_labs/<slug>.md` directly — Jekyll frontmatter (`layout: lab`, `title`, `order`, `duration`, `difficulty`, `section`, `journeys`, `description`, plus any `bootcamp_order`/event keys only if attached) followed by the README body. If `events` is non-empty, add the slug to each event's `lab_order` in `_data/lab-config.yml`.

5. **Sanity check.**
   ```
   git status --porcelain
   git diff --stat
   ```
   If nothing changed, abort with `pr_action: skipped_no_changes` and restore the stash. (Should not happen for a real build.)

6. **Commit (one commit, no AI attribution).**
   ```
   git add labs/<slug>/ _labs/<slug>.md _data/lab-config.yml lab-config.yml   # whichever exist
   git commit -m "<slug>: add new lab"
   ```
   Commit body (plain, no `Co-Authored-By` / no AI mention): one line on what the lab teaches (from Summary of Targets), the use-case list, and `Built and verified end-to-end by mcs-lab-builder (build <build_id>).` Author = current `gh`/`git` user.

7. **Push and open the PR.**
   ```
   git push -u origin <branch>
   gh pr create --repo microsoft/mcs-labs --base main --head <branch> \
     --title "<slug>: add new lab" \
     --body-file "runtime/builds/<build_id>/pr-body.md"
   ```
   Render `pr-body.md` first: what the lab teaches, the UC list, the lab metadata (section/difficulty/duration/journeys, events if any), a "How it was verified" line (`Built interactively and passed the mcs-lab-builder audit gate, build <build_id>`), and — if the user accepted residual findings — a "Findings deferred to review" list. Use `gh pr create --draft` when residual findings exist.

8. **Restore + record.**
   - `git switch -` then `git stash pop` if a stash was created.
   - Write `runtime/builds/<build_id>/pr-url.txt` and return `{ pr_url, pr_action: created | created_draft | skipped_no_changes }` to the orchestrator.

## Rules

- **Branch off fresh `origin/main`**, never the user's current branch (the mcs-labs clone is often on a feature branch).
- **One commit, no AI attribution** (no `Co-Authored-By: Claude`, no "Generated with…") — user preference.
- **Never force-push.** Never touch other labs' files.
- **Restore stashed work** even on early abort.
- **Generated output is committed** in generate mode so the PR builds the site without a maintainer re-running generation.
