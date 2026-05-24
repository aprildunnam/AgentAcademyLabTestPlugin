# Contributing

Thanks for your interest in `mcs-lab-auditor`. This document covers how the project is laid out, how to develop and test locally, and the conventions we follow for changes.

## Code of conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## What this project is — and isn't

`mcs-lab-auditor` is a [Claude Code](https://claude.com/claude-code) plugin. There is no compiled binary, no test runner, no package manager — the entire plugin is a structured tree of markdown files (commands, skills, references) plus YAML configuration. Claude is the runtime: when you invoke `/audit-bootcamp`, Claude reads the command file, follows the skill it points at, and dispatches Playwright MCP calls per the skill's instructions.

This means **most "code" in this repo is prose**: the precision of the instructions in `SKILL.md` files and the reference docs determines correctness. Treat changes to those files with the same care you would a code change.

## Project layout

```
.claude-plugin/plugin.json                 # plugin manifest
commands/                                  # slash command entry points
  audit-bootcamp.md
  audit-lab.md
  audit-report.md
  audit-account.md
skills/
  mcs-lab-auditor/                         # primary orchestration skill
    SKILL.md
    references/
      lab-parser-spec.md                   # md → step tree grammar
      llm-judge-prompts.md                 # judge / critique / classifier templates
      playwright-cookbook.md               # portal quirks, sign-in flow
      workshop-redemption.md               # workshop-code → cached account flow
      finding-schema.md                    # finding record fields, severity rubric
      audit-log-schema.md                  # local audit-history.yml schema
  mcs-lab-issue-filer/                     # sub-skill: findings → gh issue create
    SKILL.md
config/
  workshop.yml                             # workshop portal URL + selectors
  judge-config.yml                         # confidence thresholds, retries, dedupe behavior
docs/                                      # architecture, design decisions, security, troubleshooting, extending
runtime/                                   # gitignored — accounts, audit log, per-run artifacts
```

See [docs/architecture.md](docs/architecture.md) for the component overview and run lifecycle.

## Setting up for development

1. **Clone into your Claude Code user-plugin directory:**

   ```powershell
   git clone https://github.com/microsoft/BootcampLabTestPlugin "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
   ```

   The plugin is loaded by Claude Code on session start; restart Claude Code (or reload plugins) to pick it up after changes that affect the manifest, command names, or skill names.

2. **Confirm tooling:**
   - Windows 10/11 (DPAPI dependency).
   - PowerShell 7+.
   - `gh` CLI authenticated against an account with **write** access to `microsoft/BootcampLabTestPlugin` (for contributions) and **issue-creating** access to `microsoft/mcs-labs` (for the plugin's own write target).
   - The Playwright MCP plugin enabled in Claude Code (`playwright@claude-plugins-official`).

3. **Local clone of the source labs:**
   The plugin reads `_labs/<slug>.md` and `_data/lab-config.yml` from a clone of `microsoft/mcs-labs`. The default path is `C:\Users\dewainr\mcs-labs`. Several files reference this path explicitly — see [docs/extending.md](docs/extending.md) for how to point at a different location.

## Common change recipes

### Editing a skill or reference doc

Skills and reference docs are loaded by Claude on demand each invocation. Edits take effect immediately on the next `/audit-*` invocation in a fresh Claude Code session. No build, no reload command — just edit and run.

Convention: keep `SKILL.md` files focused on the procedure (what to do, in what order); push detail (selectors, edge cases, prompts, schemas) into `references/`. The skill reads a reference only when it needs it, keeping per-invocation context lean.

### Adding a new slash command

1. Create `commands/<name>.md` with YAML frontmatter (`description`, optional `argument-hint`, optional `allowed-tools`).
2. The command body should briefly orient Claude and then point at the skill that owns the work — most of the time, that's `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/SKILL.md`.
3. Restart Claude Code to register the new slash command.

### Adapting to a non-Skillable workshop portal

See [docs/extending.md](docs/extending.md). The workshop redemption flow in `references/workshop-redemption.md` assumes a "code → form submit → credentials on confirmation page" pattern. Portals that email credentials or require additional steps need targeted edits to `references/workshop-redemption.md` and `config/workshop.yml`.

### Adjusting judge behavior

`config/judge-config.yml` exposes:
- Confidence thresholds (what gets logged vs. included in the issue vs. tagged low-confidence).
- Retry counts on `transient` outcomes.
- Per-lab "non-deterministic" flagging for labs that exercise LLM-generated UI.
- Issue de-duplication behavior (`comment` vs. `skip`; `create_anyway` is deprecated and silently coerced to `comment`). Finding-level fingerprint dedup, loose-title matching, and per-slug label backfill are also configurable here.
- Open-PR append carve-out (`issues.pr_append.*`) — default-on screenshot-only push onto an existing fix-PR's branch. Suppress per-run with `--no-update-screenshots` or globally with `enabled_by_default: false`.
- Existing-state probe behavior (`existing_state.*`) — Phase 1.4 of every run.
- Whether the second-pass critique judge is enabled.

Tune these without touching the skills.

## Testing

There is no automated test runner. The verification path is the end-to-end run sequence documented in [`docs/troubleshooting.md`](docs/troubleshooting.md) and the test plan on PR #4. At minimum, before merging changes that affect step parsing or judge behavior:

1. Run `/audit-lab <slug> --dry-run` against at least one lab and inspect `runtime/runs/<id>/labs/<slug>/steps.json` to confirm the parser tree is reasonable.
2. Run `/audit-lab <slug>` end-to-end against one of the shorter Beginner labs and inspect the resulting issue body (or clean-pass log entry) for sanity.
3. If your change affected the issue body template, render at least one finding and visually verify the resulting markdown in the GitHub preview.

## Conventions

### Commits

- Imperative mood. ("Add foo", not "Added foo".)
- First line ≤ 72 chars. Wrap the body at ~72 chars.
- Don't include Claude (or any AI tool) as a co-author — this is human-authored work that may have used tools, no different from any other tool-assisted development.
- Reference the issue or PR number when relevant.

### Branches

- Feature branches: `<short-topic>`. Avoid personal namespacing (`yourname/foo`); the repo is small and rarely has overlapping work.
- Long-lived branches are not maintained — branch off `main`, merge back, delete.

### Pull requests

- Open a PR even when you have write to `main`. The PR is the audit trail.
- Include a Summary, a What-changed section, and a Test plan with checkboxes the reviewer can verify.
- Keep PRs scoped — easier to review than a single multi-topic PR.

### Documentation changes

- When you change a skill's procedure or a reference's schema, update the corresponding entry in [docs/design-decisions.md](docs/design-decisions.md) if the change reflects a deliberate design shift.
- The README and the docs are not auto-generated — keep them in sync with code (markdown) changes.

## Filing issues against this plugin

Bug reports, feature requests, and design questions are welcome as GitHub issues on this repo. Please **do not** file security issues here — see [SECURITY.md](SECURITY.md).

The plugin files audit findings against `microsoft/mcs-labs` automatically. Those issues are about *lab content*, not the plugin itself, and they're triaged by the mcs-labs maintainers.

## Releasing

This project uses [Semantic Versioning](https://semver.org/). Version is recorded in:
- `.claude-plugin/plugin.json`
- `CHANGELOG.md`

When cutting a release, update both files in the same commit. Tag the release commit (`v0.1.0`, `v0.2.0`, etc.) and push the tag.
