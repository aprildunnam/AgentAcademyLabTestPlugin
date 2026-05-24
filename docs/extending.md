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

By default the plugin reads from `C:\Users\dewainr\mcs-labs`. Adapting:

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

### Pointing at a different bootcamp event list

The plugin reads `_data/lab-config.yml` → `lab_orders.event.bootcamp`. If you want to audit a different event (e.g., `lab_orders.event.mcs-in-a-day`):

1. Add a `--event` flag to `audit-bootcamp.md` and `audit-lab.md`.
2. In `SKILL.md` Phase 1.4 (enumerate the lab list), read `lab_orders.event.<event>` instead of hardcoding `bootcamp`.
3. Update `audit-history.yml` to record `bootcamp_event: <event>` rather than always `bootcamp`.

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
| Change the PR branch pattern the probe matches against | Set `issues.pr_append.pr_branch_pattern` (default `dewain/fix-{slug}-content-audit`). |
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

## What NOT to extend

Some boundaries are deliberate and shouldn't be crossed without re-opening the relevant ADR (`docs/design-decisions.md`):

- **Don't add an "apply suggested correction as a PR" mode.** ADR-001 explicitly chose issues over PRs.
- **Don't add automatic tenant cleanup.** ADR-004 explicitly excluded this.
- **Don't commit `runtime/` contents.** The `.gitignore` enforces it; don't relax it.
- **Don't hard-code lab slugs.** ADR-005 — always read from `_data/lab-config.yml`.

If a real need pushes against one of these, write a new ADR superseding the old one and have a conversation before merging.
