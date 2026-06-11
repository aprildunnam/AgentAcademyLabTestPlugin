# Configurable Lab Instances — Design

**Date:** 2026-06-11
**Status:** Approved for planning
**Target version:** 0.7.0 (minor — additive feature, backward compatible)

## Problem

The plugin is wired to a single lab target — `microsoft/mcs-labs` plus the
Architecture Bootcamp training portal. The repo slug, git clone URL, local
clone path candidates, PR branch author prefix (`dewain/`), and the workshop
portal URL are all hardcoded across `config/judge-config.yml`,
`scripts/Resolve-LabRepo.ps1`, and `config/workshop.yml`.

We want a user to **fork the lab repo, stand up their own training portal, and
point this plugin at their own copy** — without editing plugin files (which the
plugin cache clobbers on every update). Multiple such targets should be
definable, with one active by default and per-run override.

## Concept: a "lab instance"

A **lab instance** is a named bundle describing one fork's target:

| Field             | Meaning                                                         | mcs-labs default                       |
|-------------------|----------------------------------------------------------------|----------------------------------------|
| `repo`            | GitHub slug where audit issues / fix-PRs / proposals are filed | `microsoft/mcs-labs`                   |
| `clone_url`       | Git URL the lab content is cloned from                         | `https://github.com/microsoft/mcs-labs.git` |
| `marker`          | Relative file that identifies a valid clone                    | `_data/lab-config.yml`                 |
| `path_candidates` | Local paths searched before cloning                            | the built-in `%USERPROFILE%` list      |
| `branch_prefix`   | PR/branch author prefix, per repo (user-selectable)            | `dewain`                               |
| `portal`          | Training-portal redemption config — either an inline `portal:` block or a `portal_file:` reference | `portal_file: workshop.yml` |

## Config layering — how a user maintains their own config

The plugin is installed into the plugin cache (`~/.claude/plugins/cache/...`).
Config edited *inside* the plugin is lost on update. Therefore user config lives
**outside** the plugin and overlays the shipped defaults.

- **Shipped (read-only, in plugin):** `config/lab-instances.yml` containing the
  built-in `mcs-labs` instance and `default_instance: mcs-labs`. Its `portal:`
  references the existing `config/workshop.yml` **in place** (no file move — this
  minimizes churn and keeps the diff small/low-risk).
- **User-owned (survives plugin updates):**
  `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml`. The plugin already uses
  `%USERPROFILE%\.mcs-lab-auditor\` for its managed clone, so this is the natural
  home. The user adds their fork's instance(s) here, with an **inline** `portal:`
  block so they manage exactly one file and never touch a plugin folder.
- **Merge:** user instances override/extend shipped ones by name; a
  `default_instance` set in the user file wins over the shipped default.

### Shipped `config/lab-instances.yml` (illustrative)

```yaml
default_instance: mcs-labs

instances:
  mcs-labs:
    repo: "microsoft/mcs-labs"
    clone_url: "https://github.com/microsoft/mcs-labs.git"
    marker: "_data/lab-config.yml"
    branch_prefix: "dewain"          # preserves current branch naming exactly
    path_candidates:
      - "%USERPROFILE%\\Projects\\mcs-labs"
      - "%USERPROFILE%\\mcs-labs"
      - "%USERPROFILE%\\source\\repos\\mcs-labs"
    portal_file: "workshop.yml"      # resolved relative to the plugin config dir
```

### Example user `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml`

```yaml
default_instance: contoso-internal

instances:
  contoso-internal:
    repo: "contoso/mcs-labs-fork"
    clone_url: "https://github.com/contoso/mcs-labs-fork.git"
    branch_prefix: "alice"
    # marker + path_candidates omitted → inherit sensible defaults
    portal:                          # inline portal block — no separate file to manage
      portal_kind: "skillable"
      workshop_portal_url: "https://labs.contoso.com/redeem"
      sso_anchor_url: "https://login.microsoftonline.com/"
      auth_probe_url: "https://copilotstudio.microsoft.com/"
      # ...remaining workshop.yml-shaped fields...
```

## Active-instance resolution

Resolution order (first match wins):

1. `--instance <name>` command flag
2. `$env:LAB_INSTANCE`
3. merged `default_instance` (user file overrides shipped)
4. shipped default — `mcs-labs`

An unknown instance name lists the available instances and exits non-zero.

## New component: `scripts/Resolve-LabInstance.ps1`

The single source of truth for "which lab am I working on right now." It:

1. Loads shipped `config/lab-instances.yml`.
2. Loads `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml` if present.
3. Deep-merges the two (user wins per instance/field; user `default_instance` wins).
4. Selects the active instance per the resolution order above.
5. Resolves `branch_prefix`: instance value → else `gh api user --jq .login` →
   else hard error (so no branch op ever runs with an unknown prefix).
6. Resolves the portal: inline `portal:` block, else `portal_file` loaded
   relative to the file that declared it.
7. Emits the fully resolved instance as **JSON** on stdout.

`-Mode Status` emits a one-line human summary for command pre-flight (mirrors
`Resolve-LabRepo.ps1`'s existing convention).

Every script and skill that needs `repo` / `clone_url` / `branch_prefix` /
`portal` calls this resolver instead of reading hardcoded literals.

## Changes to existing components

### `scripts/Resolve-LabRepo.ps1`
- Gains `-Instance <name>`. Sources `clone_url`, `marker`, and `path_candidates`
  from the resolved instance instead of its hardcoded
  `https://github.com/microsoft/mcs-labs.git` and built-in list.
- `$env:MCS_LABS_REPO` remains the top-priority **path** override (unchanged).
- Managed clone path becomes `%USERPROFILE%\.mcs-lab-auditor\<instance-name>`
  (was `…\mcs-labs`) so two instances never share one working tree. The
  `mcs-labs` instance keeps the historical `…\mcs-labs` path for back-compat.
- The origin/main pin logic is unchanged.

### `config/judge-config.yml`
- `issues.repo` and `build.proposal_issue.repo`: sourced from the active
  instance. The literal `microsoft/mcs-labs` is retained only as the mcs-labs
  default's value, not as the universal target.
- Branch patterns: `dewain/...` → `{branch_prefix}/...` tokens, substituted from
  the resolved instance (`pr_append.pr_branch_pattern`,
  `pr_append.pr_match_head_prefix`, `new_lab_pr.pr_branch_pattern`).
- `build.registration.mcs_labs_repo_path_candidates` continues to work and feeds
  the mcs-labs instance's `path_candidates`.

### Skills
- `mcs-lab-auditor` (orchestrator): resolves the instance **once** at run start
  via `Resolve-LabInstance.ps1` and threads `repo` + `branch_prefix` + `portal`
  to every sub-skill it dispatches.
- `mcs-lab-issue-filer`, `mcs-lab-fix-pr-filer`, `mcs-lab-new-lab-pr`,
  `mcs-lab-pr-appender`, `mcs-lab-builder`: consume the passed-in `repo` and
  `branch_prefix` rather than the config literal; hardcoded "microsoft/mcs-labs"
  prose is replaced with "the active instance's repo."

### Commands
- `audit-lab`, `audit-event`, `audit-bootcamp`, `build-lab`: document the
  `--instance <name>` flag and the resolution order.

## Error handling

- Malformed user YAML → **hard error**. Never silently fall back, or the run
  could audit / file against the wrong repo.
- `portal_file` referenced but missing → error.
- `branch_prefix` unresolvable (no instance value and `gh` not authenticated) →
  error **before** any branch is created.
- Unknown `--instance` / `$env:LAB_INSTANCE` → error listing available instances.

## Testing

Pester-style invocation tests for `Resolve-LabInstance.ps1` against a temp
`$env:USERPROFILE`:

1. No user file → returns the `mcs-labs` default.
2. User file adds an instance and sets `default_instance` → that instance is
   returned.
3. `-Instance <unknown>` → non-zero exit, lists available instances.
4. User file overrides a single field of a shipped instance → merge produces the
   overridden value while keeping un-overridden fields.
5. Inline `portal:` block and `portal_file` reference both load correctly.

Regression: confirm the `mcs-labs` default resolution is byte-for-byte unchanged
(repo slug, clone URL, marker, candidate list, branch prefix) so existing runs
behave identically with zero user config.

## Docs & versioning

- Update `docs/installation.md`, `docs/extending.md`, `docs/architecture.md`,
  `docs/troubleshooting.md`, and `README.md`: the lab-instance concept, the fork
  workflow, and a sample user `lab-instances.yml`.
- `CHANGELOG.md`: Keep a Changelog entry under a new `0.7.0` heading.
- Bump `plugin_version` (`judge-config.yml`), `.claude-plugin/plugin.json`, and
  sync `.claude-plugin/marketplace.json` to `0.7.0`.

## Out of scope (YAGNI)

- A CLI to scaffold/validate a user config file (manual file authoring is enough
  for the fork use case).
- Per-instance model presets or judge thresholds (those stay global in
  `judge-config.yml`).
- Relocating the user config dir via env var (fixed at
  `%USERPROFILE%\.mcs-lab-auditor\`).
