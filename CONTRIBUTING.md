# Contributing

Thanks for your interest in `agent-academy-tester`. This document covers how the project is laid out, how to develop and test locally, and the conventions we follow for changes.

## Code of conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## What this project is — and isn't

`agent-academy-tester` is a [Copilot CLI](https://githubnext.com/projects/copilot-cli) / [Claude Code](https://claude.com/claude-code) plugin. There is no compiled binary, no test runner, no package manager — the entire plugin is a structured tree of markdown files (commands, skills, references) plus YAML configuration. The AI runtime reads the command file, follows the skill it points at, and dispatches Playwright MCP calls per the skill's instructions.

This means **most "code" in this repo is prose**: the precision of the instructions in `SKILL.md` files and the reference docs determines correctness. Treat changes to those files with the same care you would a code change.

## Project layout

```
.claude-plugin/plugin.json                 # plugin manifest
.github/
  mcp.json                                 # Playwright MCP server config (Edge + profile)
commands/                                  # slash command entry points
  test-lab.md                              # /test-lab — single lab testing
  test-course.md                           # /test-course — course-wide testing
  reproduce-issue.md                       # /reproduce-issue — issue reproduction
skills/
  agent-academy-tester/                    # primary orchestration skill
    SKILL.md                               # lifecycle: auth → parse → execute → judge → report → fix
    references/
      lab-parser-spec.md                   # VitePress md → step tree grammar
      llm-judge-prompts.md                 # judge / critique / classifier templates
      playwright-cookbook.md                # portal navigation, Edge/M365 quirks
      finding-schema.md                    # finding record fields, severity, reproduction status
      screenshot-annotation-spec.md        # annotated screenshots + fix PR procedure
config/
  agent-academy-config.yml                 # course catalog, environment URL, auth settings
  judge-config.yml                         # confidence thresholds, retries, issue filing, fix PR, screenshots
runtime/                                   # gitignored — test results, screenshots, per-run artifacts
```

## Setting up for development

1. **Clone the repo:**

   ```bash
   git clone https://github.com/aprildunnam/AgentAcademyLabTestPlugin
   ```

2. **Install as a plugin** (from the cloned path):

   ```text
   /plugin install /path/to/AgentAcademyLabTestPlugin
   ```

   The plugin is loaded on session start; restart your session to pick up changes
   that affect the manifest, command names, or skill names.

3. **Confirm tooling:**
   - **Node.js** — for `npx @playwright/mcp`
   - **Microsoft Edge** with a browser profile signed into your M365 tenant
   - **GitHub CLI (`gh`)** authenticated — needed for issue filing and fix PRs
   - The Playwright MCP server is auto-configured via `.github/mcp.json` — no manual setup needed

4. **Configure your environment:**
   - Edit `.github/mcp.json` to set your Edge profile path (see `edge://version` in your target profile)
   - Edit `config/agent-academy-config.yml` to set your Power Platform environment URL

## Common change recipes

### Editing a skill or reference doc

Skills and reference docs are loaded on demand each invocation. Edits take effect
immediately on the next `/test-*` invocation in a fresh session. No build, no reload
command — just edit and run.

Convention: keep `SKILL.md` focused on the procedure (what to do, in what order);
push detail (selectors, edge cases, prompts, schemas) into `references/`. The skill
reads a reference only when it needs it, keeping per-invocation context lean.

### Adding a new slash command

1. Create `commands/<name>.md` with YAML frontmatter (`description`, optional `argument-hint`).
2. The command body should briefly orient the AI and then point at the skill that owns
   the work: `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md`.
3. Restart your session to register the new command.

### Adjusting judge behavior

`config/judge-config.yml` exposes:
- Confidence thresholds (what gets logged vs. included in the issue vs. tagged low-confidence)
- Retry counts on `transient` outcomes
- Issue de-duplication behavior (`comment` vs. `skip`)
- Fix PR generation settings (branch pattern, labels, fork fallback)
- Screenshot annotation settings (colors, which verdicts trigger annotation)
- Reproduction settings (cascade steps, quick-mode critique bypass)
- Whether the second-pass critique judge is enabled

Tune these without touching the skills.

## Testing

There is no automated test runner. The verification path is end-to-end:

1. Run `/test-lab <course>/<slug> --dry-run` to confirm the parser tree is reasonable.
2. Run `/test-lab <course>/<slug>` end-to-end against a short lab and inspect the
   resulting report in `runtime/test-results/`.
3. If your change affected the issue body template, file an issue and visually verify
   the resulting markdown in the GitHub preview.
4. For reproduction mode, test with `/reproduce-issue <number>` against a known issue.

## Conventions

### Browser and Playwright tools

When referencing browser or Playwright tools in skills, references, or cookbooks, use
bare `@playwright/mcp` action names (e.g., `browser_navigate`, `browser_click`). The
`.github/mcp.json` file handles the MCP server configuration for both Claude Code and
Copilot CLI.

### Commits

- Imperative mood. ("Add foo", not "Added foo".)
- First line ≤ 72 chars. Wrap the body at ~72 chars.
- Reference the issue or PR number when relevant.

### Branches

- Feature branches: `<short-topic>`.
- Long-lived branches are not maintained — branch off `main`, merge back, delete.

### Pull requests

- Open a PR even when you have write to `main`. The PR is the audit trail.
- Include a Summary, a What-changed section, and a Test plan.
- Keep PRs scoped — easier to review than a single multi-topic PR.

## Filing issues against this plugin

Bug reports, feature requests, and design questions are welcome as GitHub issues on this repo.

The plugin files lab content issues against `microsoft/agent-academy` automatically.
Those issues are about *lab content*, not the plugin itself.

## Releasing

This project uses [Semantic Versioning](https://semver.org/). Version is recorded in:
- `.claude-plugin/plugin.json`
- `config/judge-config.yml`

When cutting a release, update both files in the same commit and tag appropriately.
