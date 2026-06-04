# Extending the plugin

This document covers the most common ways to extend `mcs-lab-auditor`: adapting to a workshop portal that isn't Skillable-shaped, adding a new slash command, swapping the lab source repo, and adjusting the judge.

For each extension, the rule of thumb: **change the reference doc first, then the skill, then the config.** Reference docs are the operational rulebooks; skills are the procedures that read them; configs are the knobs that tune them.

## Adapting to a different workshop portal

The redemption flow is selected by `config/workshop.yml.portal_kind`:

- `chatbot` → `references/workshop-redemption-chatbot.md`
- `skillable` → `references/workshop-redemption.md`
- `email` → manual credential collection after "check your email" confirmation

The default bootcamp configuration is `portal_kind: chatbot` at `https://aka.ms/MCSWorkshopAgent/`.

### Portal emails credentials instead of displaying them

1. Keep `portal_kind: email` in `config/workshop.yml`.
2. After code submit, detect the email-confirmation message and prompt manually:
   ```
   3. Detect the "code accepted, check your email" confirmation.
   4. Use AskUserQuestion to prompt the user for the username, password, and (optionally) tenant from the received email.
   ```
3. Continue with the standard sign-in and credential-cache steps (shared MCP session, DPAPI encryption, metadata write).

### Portal uses multi-step redemption (e.g., select event, then enter code)

Set `portal_kind: chatbot` and adapt `references/workshop-redemption-chatbot.md` for your card sequence.

### Portal requires login to access the redemption form

Document the pre-redemption login flow in the portal-kind-specific reference doc. The Playwright sequence is the same as the AAD sign-in flow — `_browser_type` username, `_browser_type` password, click submit — just against the workshop portal's identity provider instead of AAD.

## Adding a new slash command

To add `/audit-foo`:

1. Create `commands/audit-foo.md`:
   ```markdown
   ---
   description: One-line description of what this command does.
   argument-hint: "[--flag] [<positional>]"
   ---

   # /audit-foo

   Brief framing of what the user wants when they run this.

   ## Arguments
   Arguments passed: `$ARGUMENTS`

   (Parse expected flags here.)

   ## Pre-flight context
   - Useful state: !`Get-Content … `

   ## Your task
   (One paragraph or numbered list pointing at the relevant skill and what to do with the arguments.)
   ```

2. Either point at an existing skill (`skills/mcs-lab-auditor/SKILL.md`) or add a new sub-skill (`skills/audit-foo-thing/SKILL.md`).

3. Restart Claude Code so the new command is registered.

4. Update `README.md` and `CHANGELOG.md` with the new command.

## Pointing at a different lab repo

> **Build mode already resolves the path.** `/build-lab` (v0.4.0+) does **not** use the hardcoded path below — it resolves the mcs-labs repo from `config/judge-config.yml.build.registration.mcs_labs_repo_path_candidates` (first existing wins; default `…\Projects\mcs-labs` then `…\mcs-labs`). The hardcoded path described here still applies to the **audit** commands; aligning them on the same candidate-resolution is a tracked follow-up (ADR-020). To point build mode at a different clone, add it as the first entry in that candidates list.

For the audit commands, the plugin reads from `C:\Users\dewainr\mcs-labs` by default. Adapting:

### Quick (per-machine) override

Several files reference the hard-coded path. Bulk-replace `C:\Users\dewainr\mcs-labs` with your clone path in:
- `commands/audit-bootcamp.md`
- `commands/audit-lab.md`
- `commands/audit-account.md`
- `skills/mcs-lab-auditor/SKILL.md` (look for the "Resolve the plugin directory" section)

### Proper config-driven path (recommended for a v0.2)

1. Add to `config/judge-config.yml`:
   ```yaml
   labs:
     repo_path: "C:\\Users\\dewainr\\mcs-labs"
     lab_config_relative: "_data/lab-config.yml"
     labs_dir_relative: "_labs"
   ```
2. Update `SKILL.md` Phase 1 to read these values rather than hard-coding paths.
3. Update the pre-flight `!` interpolations in the command files to use `$env:USERPROFILE` or read from config.

This change is bounded (one config key, four file edits) but touches enough places that it's worth doing as a single PR rather than ad-hoc per machine. Open an issue if you want to tackle it.

### Adding or auditing a different workshop event

As of v0.3.0, event scope is **first-class**. Every workshop entry in `_data/lab-config.yml.event_configs` (bootcamp, buildathons, MCS-in-a-Day variants, the Azure AI workshop, anything added in the future) is a valid `/audit-event --event <key>` target. No plugin edits needed when a new event is added on the mcs-labs side — `event_configs` is read dynamically at run start.

What still needs editing if a brand-new event has a structural quirk:

1. **Different lab-dependency chains** — add a chain to `config/judge-config.yml.lab_dependencies` if the new event's labs share tenant state in a non-bootcamp pattern.
2. **Custom workshop portal** — if the new event uses a different portal kind (Skillable vs chatbot vs email), set `config/workshop.yml.portal_kind` accordingly and follow `references/workshop-redemption*.md`.
3. **Custom event grouping in the Q3a picker** — the picker's top 3 options come from the most-used events in `runtime/audit-history.yml`; you can also hand-curate the recommended option by editing the option labels in `SKILL.md` Phase 1.5 Q3a.

Auditing a brand-new event with no plugin changes:

```text
/audit-event --event <new-event-key>
```

The skill enumerates `event_configs.<new-event-key>.config_key` to get the slug list and proceeds.

## Adding a new finding outcome

The current outcomes are `pass | broken | unclear | non_deterministic | transient | cannot_verify`. To add e.g. `accessibility_violation`:

1. Update `references/finding-schema.md` to add the new outcome to the schema and the rubric.
2. Update `references/llm-judge-prompts.md` §A to teach the judge about the new outcome (when to use it, what evidence to cite).
3. Update `references/audit-log-schema.md` to allow the new value in `status`.
4. Update `mcs-lab-issue-filer/SKILL.md` to decide whether the new outcome should be included in the issue body or kept local-only.

This is a coordinated change across four files — design carefully and exercise end-to-end before merging.

## Tuning judge behavior without code changes

Most behavior changes can be made via `config/judge-config.yml` alone:

| Want to | Edit |
|---|---|
| Reduce false positives | Raise `confidence.min_to_include_in_issue` from 0.5 → 0.6 |
| Surface more findings even at low confidence | Lower the same threshold to 0.3, and lower `low_confidence_marker_max` to 0.4 |
| Skip GitHub issues entirely for now | Always pass `--no-issue` (or temporarily set `issues.on_duplicate: skip` *and* mark every lab non-deterministic — there's no global "disable issues" flag yet, but `--no-issue` per invocation is the same effect) |
| Cap a runaway lab | Lower `execution.max_steps_per_lab` |
| Disable critique pass | Set `critique.enabled: false` (saves ~10% cost, accepts higher false-positive rate) |
| Add a lab to the non-deterministic list | Append to `non_deterministic_lab_slugs` |
| Change the dedupe behavior | Set `issues.on_duplicate` to `comment` (default) or `skip`. `create_anyway` is deprecated and silently coerced to `comment`. |
| Disable fingerprint dedup (post every finding on every run) | Set `issues.dedupe_by_fingerprint: false`. Not recommended — produces duplicate-comment churn. |
| Disable loose-title dedup query | Set `issues.dedupe_loose_title_match: false`. Only safe once every open audit issue has the `lab:<slug>` label. |
| Disable per-slug label backfill | Set `issues.backfill_per_slug_label: false`. |
| Disable open-PR screenshot append by default | Set `issues.pr_append.enabled_by_default: false`. On by default; this flips the plugin to pure read-only behavior unless the per-run flag explicitly re-enables it. |
| Change the branch name newly-opened fix-PRs are created on | Set `issues.pr_append.pr_branch_pattern` (default `dewain/fix-{slug}-content-audit-{run_id}`). Keep the `{run_id}` token so each new PR's branch is unique and can't collide with a merged PR's leftover branch. |
| Change the head-ref prefix used to find an existing open PR to append to | Set `issues.pr_append.pr_match_head_prefix` (default `dewain/fix-{slug}-content-audit`). Must remain a prefix of `pr_branch_pattern`. |
| Disable the Phase 1.4 existing-state probe | Set `existing_state.check_open_issues: false` and `existing_state.check_open_prs: false`. The filer will fall back to its inline dedup queries. Not recommended — costs extra `gh` calls per lab. |

No code changes needed — config tweaks take effect on the next invocation.

## Adding screenshot uploading to issues

Currently the plugin references screenshots by local path. A future enhancement: upload screenshots somewhere and embed image links in the issue body.

Two approaches:

**Sidecar release asset.** Create a draft release on this plugin's repo, upload screenshots as assets, embed by URL. Stable URLs, but each audit run pollutes the releases list.

**Gist.** Create a Gist per finding with the screenshot embedded, reference the Gist's raw URL. Cleaner namespace, but Gists are user-scoped (every issue link associated with whichever account `gh` is authed as).

Either way, the change lives in `mcs-lab-issue-filer/SKILL.md`:
1. Before rendering the issue body, upload screenshots → get URLs.
2. Replace the local path references in the body with markdown image embeds.
3. Add an opt-in flag (`--upload-screenshots`) because this is the kind of thing you might not always want.

## Supporting macOS or Linux

The DPAPI dependency is the blocker. Plan:

1. Abstract the credential cache into a helper (`references/credential-cache.md`) with three implementations:
   - Windows: PowerShell + DPAPI (current).
   - macOS: `security` CLI + Keychain.
   - Linux: `secret-tool` + libsecret (Gnome Keyring / KWallet).
2. Detect platform at run-start and pick the right implementation.
3. The credential cache interface is small: `store(cred_json)`, `read() -> cred_json`, `clear()`. Each implementation maps onto its native primitive.

This is a v0.3+ effort. Track via a GitHub issue if it's a real need.

## Customizing build mode (`/build-lab`)

Build mode authors a new lab end-to-end; the pieces you'll most likely adjust:

| Want to | Edit |
|---|---|
| Change the default interaction mode | `judge-config.yml.build.interaction_mode_default` (`prompt` / `guided` / `scenario`). Per-run override: `--mode`. |
| Change what fails the audit gate, or how many fix loops it allows | `judge-config.yml.build.audit_gate.fail_on` (default `[broken, unclear]`) and `audit_gate.max_loops`. |
| Point build mode at a different mcs-labs clone | Prepend your path to `judge-config.yml.build.registration.mcs_labs_repo_path_candidates`. |
| Change the new-lab PR branch name | `judge-config.yml.issues.new_lab_pr.pr_branch_pattern` (default `dewain/new-lab-{slug}-{build_id}`). |
| Change the new-lab README format | Edit `skills/mcs-lab-builder/references/lab-authoring-template.md` — the canonical skeleton B5 renders against. |
| Change how a lab is registered (config maps, `_labs` frontmatter) | Edit `skills/mcs-lab-builder/references/lab-registration-spec.md`. It documents both the `generate` and `direct` mechanisms; B0 detects which applies. |
| Change the capture loop, ledger schema, or screenshot naming | Edit `skills/mcs-lab-builder/references/build-session-spec.md`. |

**If the mcs-labs new-lab toolchain returns** (a root `lab-config.yml` + `scripts/Generate-Labs.ps1`), no code change is needed — B0 detects it and switches from direct-write to the generate flow automatically (`lab-registration-spec.md` §1). Confirm `build.registration.generate_script_relpath` matches the script's actual path.

## What NOT to extend

Some boundaries are deliberate and shouldn't be crossed without re-opening the relevant ADR (`docs/design-decisions.md`):

- **Keep every write path narrow and explicit.** The plugin's writes to `microsoft/mcs-labs` are exactly: the Issues API (ADR-001), the fix-PR per audit run (ADR-015), the screenshots-only PR append (ADR-014), and the build-mode new-lab PR (ADR-018). Don't add a path that mutates the repo outside these — and don't broaden the audit fix-PR into auto-applying corrections without review.
- **Don't add automatic tenant cleanup.** ADR-004 explicitly excluded this.
- **Don't commit `runtime/` contents.** The `.gitignore` enforces it; don't relax it. This includes `runtime/builds/` (build-mode workspaces).
- **Don't hard-code lab slugs or assume the bootcamp event.** ADR-005 / ADR-019 — always read from `_data/lab-config.yml`; both audit and build are event/workshop-agnostic.

If a real need pushes against one of these, write a new ADR superseding the old one and have a conversation before merging.
