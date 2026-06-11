# Troubleshooting

Common failure modes you'll hit running `mcs-lab-auditor`, grouped by category, with diagnostic steps.

When you see an unexpected behavior, start by reading `runtime/runs/<latest-run-id>/labs/<slug>/transcript.md` — it's the human-readable log of everything the orchestrator did, including which judge calls were made and what they returned.

## Plugin doesn't load

**Symptom:** `/audit-bootcamp` and friends don't appear in the slash-command menu.

| Cause | Fix |
|---|---|
| Plugin directory not at `~/.claude/plugins/mcs-lab-auditor/` | Move or symlink it there. Claude Code only auto-discovers plugins in the user plugins directory. |
| Claude Code hasn't reloaded plugins since install | Restart Claude Code. There is no `/plugin reload` in current versions. |
| `plugin.json` malformed | Run `Get-Content .claude-plugin\plugin.json -Raw \| ConvertFrom-Json` — if it throws, the manifest is broken. |
| Frontmatter missing on a command file | Each `commands/*.md` must start with a `---\n…\n---` block including `description:`. Without it, the command isn't registered. |

## Plugin self-version check

**Symptom:** A run prints `UPDATE AVAILABLE: local vX < published vY — run /plugin to update …` at the very start.

This is the non-blocking self-version check (`scripts/Test-PluginVersion.ps1`, Phase 1 step 1). It compared your local `.claude-plugin/plugin.json` version to the version published on `origin/main` of `microsoft/BootcampLabTestPlugin` and found a newer one. It does **not** stop the run — but you should update (`/plugin`, or `git pull` + restart for a cloned install) so you're not auditing on stale logic. `runtime/` survives the update.

**Symptom:** The check prints `version check skipped (...)`.

Expected when it can't reach the published manifest — `gh` isn't installed/authenticated, or you're offline. The check is best-effort and silently degrades; the run continues on your local version. If you want the check to work, ensure `gh auth status` is healthy.

## Run-start account prompt

**Symptom:** Plugin reports `redemption_timeout` or fails to scrape credentials.

| Cause | Fix |
|---|---|
| `config/workshop.yml.workshop_portal_url` still set to `REPLACE_ME_ON_FIRST_RUN` | Edit it to your actual workshop event URL. |
| Workshop portal has a non-Skillable layout | See [`extending.md`](extending.md) for how to adapt the selectors and scraping logic in `references/workshop-redemption.md`. |
| Workshop code already redeemed | Get a fresh code; portal will show "Already redeemed" on submit. |
| Workshop code is for a different event than the portal URL | Match the code to the portal it was issued for. |
| MFA required on first sign-in | Run `gh notes` ... actually: workshop accounts should be MFA-exempt. If not, contact the workshop issuer. The plugin halts with `reason: mfa_required` rather than guess at TOTP flows. |
| First-login password change required | Open the account manually in a browser, change the password once, then re-run `/audit-account redeem`. The plugin halts with `reason: first_login_password_change_required` rather than auto-resetting passwords. |

**Symptom:** Plugin reports `Cached test account: <user_id>` but then sign-in fails.

```powershell
/audit-account show     # see what the plugin thinks is cached
/audit-account clear    # nuke it and start fresh
/audit-account redeem   # redeem a new code
```

**Symptom:** Decryption fails (`ConvertTo-SecureString` throws).

You've changed Windows user or moved the machine. DPAPI keys are user+machine-scoped. Run `/audit-account clear` and `/audit-account redeem`. (Migration of DPAPI blobs across machines is not supported.)

## Mid-run auth expiry

**Symptom:** Run halts with `status: error, reason: auth_expired`.

The cached account's session expired (typically 8–24 hours after sign-in). Recover:

```text
/audit-account redeem                              # fresh workshop code
/audit-bootcamp --resume <run-id>                  # continues from the last completed scene
```

The run-id is printed in the halt message and recorded in `runtime/runs/<id>/manifest.yml`.

**Symptom:** Run completes but `manifest.yml` shows several labs as `error, reason: auth_expired`.

Probably one expiry early in the run cascaded. After the first auth_expired, the orchestrator halts the *current* lab and asks you to resume — if it continued past that, you may be on an older plugin build. Verify behavior with a single `/audit-lab <slug>`.

## Parser issues

**Symptom:** `steps.json` has steps where you expected, but `kind` is wrong (e.g., `narrative` when it should be `click`).

The action classifier (`references/lab-parser-spec.md` §4) is heuristic. If it consistently misclassifies a particular phrasing in real labs, add a pattern to the spec and re-run.

**Symptom:** `parser_warning` finding appears in the issue.

The parser detected a structural problem in the lab — most often a broken cross-reference, an orphan alert block, or a numbered list that didn't tokenize as expected. The finding includes a line number. Decide whether the lab is wrong (file the issue) or the parser is wrong (update `lab-parser-spec.md`).

**Symptom:** Lab has a step the parser missed entirely (`steps.json` count lower than the rendered lab page).

Open `_labs/<slug>.md` and find the missing step. Common causes:
- The step lives outside `## Instructions by Use Case` (the parser only treats that section as executable). If it's actually an instruction, the lab should be reorganized.
- The step is a sub-bullet rather than a numbered item — sub-bullets are merged into the parent step intentionally.
- A blank line broke list continuity. Check the markdown rendering on the live mcs-labs site to confirm whether the renderer treats it as one list or two.

## Browser / Playwright issues

**Symptom:** `_browser_wait_for` repeatedly times out on the same step.

Either the page is genuinely slow, or the wait condition is wrong. Check `transcript.md` for what text/element the wait was for. If the underlying UI changed (button renamed, page restructured), update `references/playwright-cookbook.md` with the new pattern.

**Symptom:** Click happens on the wrong element.

`_browser_click` targets by snapshot ref. The snapshot was likely stale (taken before a layout shift) or the wrong element matched the step text. Snapshots are taken just before each click; if the page is asynchronously re-rendering, add a brief wait. Document the quirk in `playwright-cookbook.md`.

**Symptom:** "Browser closed" or "Context not found" errors.

The Playwright MCP browser session died — usually because the browser was closed manually, or the MCP process restarted. The orchestrator halts the run; resume with `--resume <run-id>`. If this keeps happening, restart Claude Code (which restarts the Playwright MCP).

## Judge issues

**Symptom:** Judge consistently rates the same step `unclear` when you can clearly see it passes.

The accessibility snapshot may be incomplete (some elements aren't surfaced in the a11y tree). Inspect `runtime/runs/<id>/labs/<slug>/snapshots/<step-id>.yml`. If the relevant element isn't in the snapshot, the judge can't see it — switch the step's `kind` to `inspect` (asks the judge to look at the screenshot more than the snapshot) by adjusting the action classifier or annotating the lab.

**Symptom:** Judge produces a verdict but `suggested_correction.original_text` doesn't match the lab markdown.

The judge fabricated a substring. The orchestrator should retry once with a stronger reminder; if it persists, downgrade to `unclear` with severity `low`. If you see this often, the prompt in `references/llm-judge-prompts.md` may need a stronger "must be exact substring" constraint.

**Symptom:** Judge calls fail (`gh` works, browser works, but no findings are produced).

Check `transcript.md` for the judge invocation. If the model is failing repeatedly, the orchestrator logs `transient` for those steps but continues. After enough transients, consider lowering `judge-config.yml.execution.max_steps_per_lab` to bail out earlier, or switching models in the judge config.

## Issue filing issues

**Symptom:** `gh issue create` returns 403.

```bash
gh auth status                                                # confirm logged-in account
gh repo view microsoft/mcs-labs --json viewerPermission       # confirm permission
```

If your account doesn't have permission to file issues on `microsoft/mcs-labs`, ask for triage access or use a different `gh` identity (`gh auth login --user <other>`).

**Symptom:** New issue opened even though an existing one should have matched.

The v0.2 dedup is a **union of two queries**: strict (`--label "lab-audit" --label "lab:<slug>"`) and loose (`--label "lab-audit" --search "<slug> in:title"`). A new issue would only be created if both queries return zero results. Check:

1. Does the existing issue have the `lab-audit` label? Without it, neither query matches. Add the label and re-run.
2. Does the existing issue's title contain the slug? If not, the loose query also misses; either edit the title to include the slug or add a `lab:<slug>` label.
3. Was `issues.dedupe_loose_title_match` set to `false` in `judge-config.yml`? If so, only the strict query runs — set it back to `true`.

The filer also auto-backfills the `lab:<slug>` label on every commented issue, so over time the loose query becomes redundant.

**Symptom:** Re-audit comment repeats findings the existing issue already covers.

Finding-fingerprint dedup may be off. Check `judge-config.yml.issues.dedupe_by_fingerprint`. When enabled (default), each rendered finding carries an HTML marker `<!-- finding:fp:<hex> -->` and re-runs drop findings whose fingerprint already appears in the issue body or any prior comment. If you intentionally want full re-renders, set `dedupe_by_fingerprint: false`.

**Symptom:** PR-append push failed or got skipped.

The `mcs-lab-pr-appender` sub-skill records a `skipped_reason` in `manifest.yml.labs[<slug>].pr_append_result`. The full taxonomy is in `skills/mcs-lab-auditor/references/pr-append-flow.md` — common ones:

- `not_pr_author` — your `gh` identity doesn't match the PR author. Sign in as the author or skip the append (`--no-update-screenshots`).
- `pr_has_conflicts` — the open PR has merge conflicts. Resolve manually, then re-run.
- `no_mapped_screenshots` — none of the new `.png` files matched an existing image path in `labs/<slug>/images/`. The appender only replaces existing files; adding net-new images is not in scope.
- `no_visual_diff` — files were byte-identical. Nothing to commit.

**Symptom:** Issue body looks malformed (broken markdown, missing sections).

The rendered body is at `runtime/runs/<id>/labs/<slug>/issue-body.md`. Open it locally — if it's broken there, the issue-filer's template has a bug. If it's fine there but broken on GitHub, GitHub-flavored markdown is rejecting something (rare).

## Audit log issues

**Symptom:** `/audit-report` shows nothing or "No runs recorded."

Either `runtime/audit-history.yml` doesn't exist (no runs yet) or it's empty. Verify with `Get-Content runtime\audit-history.yml -TotalCount 5`. If a run completed without writing to the log, the orchestrator skipped the append step — file a bug.

**Symptom:** `audit-history.yml` shows duplicate entries for the same `(run_id, lab_slug)`.

Probably a `--resume` after a partially-written entry. The plugin should append-only, but if it doesn't, you can hand-edit to dedupe — the file is plain YAML.

**Symptom:** Log grows past 5 MB and `/audit-report` becomes sluggish.

The plugin emits a soft warning at 5 MB. Archive old entries manually: move them to a dated file like `runtime/audit-history-2026Q1.yml.bak` and trim the live file. Don't auto-rotate from the plugin — too much risk of losing the wrong entries.

## Build mode (`/build-lab`) issues

**Symptom:** Build (or audit) halts at repo resolution with "mcs-labs repo not found."

Both modes resolve the repo via `scripts/Resolve-LabRepo.ps1`, which normally **auto-clones** `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs` when no local copy is found — so a hard failure here means the clone itself couldn't happen. Check, in order:

- **`git` not on PATH** — the resolver can't clone without it (`git --version`). Install Git, then re-run.
- **No network / `gh`-less offline run** — the clone step needs to reach `github.com`. If you're offline, point the resolver at an existing local clone via `$env:MCS_LABS_REPO` or `mcs_labs_repo_path_candidates`, and pass `-NoPull` semantics will apply (a stale local copy is preferred over a hard failure).
- **`-NoClone` / read-only context** — if cloning is disabled, you must supply a path. Set `$env:MCS_LABS_REPO` to your clone or add it to `mcs_labs_repo_path_candidates` in `config/judge-config.yml`.

To see what the resolver picks (and why):

```powershell
pwsh "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Status
# e.g. "mcs-labs: C:\Users\you\Projects\mcs-labs [pulled]"  or  "[cloned]"
```

**Symptom:** Build halts at B6 with a registration-mechanism message ("could not find the editable root `lab-config.yml`" / "generator not found").

The mcs-labs new-lab toolchain documented in `NEW_LAB_CHECKLIST.md` (root `lab-config.yml` + `scripts/Generate-Labs.ps1`) is absent upstream. Expected — build mode falls back to **direct writes** of `labs/<slug>/README.md` + `_labs/<slug>.md` + the `_data/lab-config.yml` entry. If it halted instead of falling back, the detection found a partial/ambiguous toolchain (e.g. a root config but no generator); resolve which mechanism is real, or register manually. The draft is safe under `runtime/builds/<build-id>/draft/`.

**Symptom:** The audit gate never passes — it keeps looping back to the capture loop.

A step the gate judges `broken`/`unclear` above threshold blocks the gate. Either fix the step when prompted (re-record / re-screenshot / re-word) or, if it's a false positive, the gate stops after `build.audit_gate.max_loops` (default 5) and offers to open a **draft** PR listing the residual findings. To inspect them, read `runtime/builds/<build-id>/audit/findings.json`. Tune `build.audit_gate.fail_on` / thresholds if the judge is too strict for this lab.

**Symptom:** Slug collision — "a lab with this name already exists."

B3 found the derived `<slug>` already in `_data/lab-config.yml` (an `id:`) or as a `labs/<slug>/` folder. Build mode never overwrites an existing lab — pick a different name. (To *fix* an existing lab, use the audit flow, not `/build-lab`.)

**Symptom:** PR step fails with 403 / permission denied.

Build mode opens a PR (not just an issue), so `gh` needs PR-create permission on `microsoft/mcs-labs`. Check `gh repo view microsoft/mcs-labs --json viewerPermission` (`WRITE`+). Use `--no-pr` to author + gate without opening a PR.

**Symptom:** The "new lab proposal" issue wasn't created (or a duplicate appeared).

Build mode opens a `type: new-lab` + `status: in-progress` issue at B3.5. If it was skipped, check: (a) `gh` has issue-create permission on `microsoft/mcs-labs` (`gh repo view … --json viewerPermission`); (b) `judge-config.yml.build.proposal_issue.enabled` is `true`; (c) the labels in `build.proposal_issue.labels` exist on the repo (it warns and files with the labels that do rather than failing). A *duplicate* means dedup missed an existing open proposal — it matches by `type: new-lab` label + slug-in-title, so a prior proposal with a different title won't be found; close the extra one. On `--resume`, the issue from `manifest.proposal_issue` is reused, never reopened.

**Symptom:** A build was interrupted; how do I continue?

`/build-lab --resume <build-id>`. It re-runs preflight + the account prompt, returns to where the browser left off, and resumes at the first unconfirmed step. Confirmed steps in `runtime/builds/<build-id>/ledger.yml` (and their screenshots) are preserved. The `<build-id>` is printed at build start and stored in `runtime/builds/<build-id>/manifest.yml`.

## Filesystem issues

**Symptom:** `Cannot remove the item ... because it is in use`.

Some long-running process (often a shell or editor) has the path open. Close it, retry. As a last resort, restart Claude Code.

**Symptom:** Plugin can't write to `runtime/account/` (permission denied).

Filesystem permissions changed. Run `icacls "%USERPROFILE%\.claude\plugins\mcs-lab-auditor\runtime"` to inspect. The default user-profile permissions are sufficient; if you've explicitly tightened them, restore inheritance.

## Lab instance resolution

### "The 'powershell-yaml' module is required to resolve lab instances"
Run `Install-Module powershell-yaml -Scope CurrentUser -Force`, then retry.

### "Unknown lab instance '<name>'"
The `--instance` / `$env:LAB_INSTANCE` name does not match any instance in the
shipped registry or your `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml`. Run
`pwsh -File scripts/Resolve-LabInstance.ps1 -Mode Status` and check the spelling.

## When all else fails

1. Read `runtime/runs/<run-id>/labs/<slug>/transcript.md` end-to-end.
2. Compare what the orchestrator did vs. what `references/playwright-cookbook.md` and `references/lab-parser-spec.md` say it should do.
3. If the plugin's behavior contradicts its own docs, that's a real bug — file an issue on this repo (not on `microsoft/mcs-labs`).
4. If the UI has changed under us (renamed button, redesigned page), update `references/playwright-cookbook.md` and re-run.
