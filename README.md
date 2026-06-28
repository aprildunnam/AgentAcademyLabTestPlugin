# AgentAcademyLabTestPlugin

A Copilot CLI / Claude Code plugin that **tests [Copilot Studio Agent Academy](https://microsoft.github.io/agent-academy/) labs end-to-end**. It launches Microsoft Edge with your browser profile, navigates directly to your Power Platform environment, walks through every lab step using Playwright, and uses an LLM judge to verify each step against the live UI. When it finds broken or unclear instructions, it files issues on the [microsoft/agent-academy](https://github.com/microsoft/agent-academy/issues) repo.

## What it does

1. **Launches Edge** with your dedicated browser profile (pre-configured, so you're already signed in)
2. **Navigates to your Power Platform environment** — a configurable Copilot Studio environment URL
3. **Fetches the latest lab content** from the `microsoft/agent-academy` repo
4. **Walks through every step** of the selected lab using Playwright MCP
5. **Judges each step** with an LLM — compares what the lab says should happen vs what actually happens in the live UI
6. **Reports findings** — pass, broken (UI diverged), unclear, non-deterministic, transient, or cannot-verify
7. **Files GitHub issues** at [microsoft/agent-academy](https://github.com/microsoft/agent-academy/issues) when findings are confirmed (deduped — no duplicate open issues)
8. **Captures annotated screenshots** (with `--auto-fix`) — highlights broken steps with red callout boxes showing expected vs actual
9. **Opens fix PRs** (with `--auto-fix`) — applies corrected markdown and refreshed screenshots to `microsoft/agent-academy` so broken labs can be fixed quickly

## Commands

| Command | Purpose |
|---|---|
| `/test-lab [<course>/<slug>]` | Test a single lab interactively |
| `/test-course [<course>]` | Test all interactive labs in a course sequentially |
| `/reproduce-issue [<issue-number>]` | Reproduce a bug reported in a GitHub issue by re-running the relevant lab steps |
| `/rewrite-lab [<course>/<slug>]` | Rewrite a lab for a new UI experience — generates updated markdown + screenshots locally |
| `/create-lab [<course>]` | Create a brand-new lab from scratch — explores the feature live and generates complete lab markdown |
| `/export-solution [<course>/<slug>]` | Export a Power Platform starter solution so learners can skip prerequisite labs |
| `/cleanup [<course>]` | Remove lab-created artifacts from the environment so labs can be re-run clean |

### Command flags

| Flag | Applies to | Description |
|---|---|---|
| `--env-url <url>` | Both | Override the default Power Platform environment URL |
| `--no-issue` | Both | Skip GitHub issue filing — results are local only |
| `--auto-fix` | Both | Enable annotated screenshots + fix PR generation for broken findings |
| `--no-pr` | Both | Skip fix PR generation (use with `--auto-fix` to get screenshots only) |
| `--no-comment` | `/reproduce-issue` | Run reproduction but don't post results to the issue |
| `--dry-run` | `/test-lab` | Parse the lab into a step tree only, no browser |
| `--static-only` | `/test-lab` | Check markdown structure, links, and images only |
| `--stop-on-failure` | `/test-course` | Halt the run if any lab has a high-severity broken finding |
| `--output-dir <path>` | `/rewrite-lab`, `/create-lab` | Custom output directory for generated lab files |
| `--export-solution` | `/test-lab`, `/rewrite-lab`, `/create-lab` | Also export the resulting state as a Power Platform solution .zip |
| `--run-prereqs` | `/export-solution` | Run all prerequisite lab steps first to create artifacts from scratch |
| `--export-type` | `/export-solution` | Export as `managed`, `unmanaged`, or `both` (default: both) |
| `--solution-name` | `/export-solution` | Custom solution display name (default: auto-generated) |
| `--dry-run` | `/test-lab`, `/cleanup` | Preview what would happen without executing |
| `--keep-solution` | `/cleanup` | Delete contents but keep the empty solution container |
| `--force` | `/cleanup` | Skip confirmation prompt |
| `--title <title>` | `/create-lab` | The mission title for the new lab |
| `--topic <description>` | `/create-lab` | Brief description of what the lab should teach |

### Available courses

| Course | Labs | Description |
|---|---|---|
| `recruit` | 13 lessons (10 interactive) | Copilot Studio fundamentals — create agents, solutions, topics, adaptive cards, flows |
| `operative` | 11 lessons (all interactive) | Advanced — agent instructions, multi-agent, triggers, model selection, MCP, AI safety |
| `special-ops` | 5 labs | Specialized integrations — MCP servers, YAML specialist, Docusign |
| `cowork-collective` | 3 labs | Real-world agent scenarios — badge check, compliance packet, OOO handoff |

### Examples

```bash
# Test a specific lab
/test-lab recruit/04-creating-a-solution

# Test a lab against a different environment
/test-lab recruit/04-creating-a-solution --env-url https://copilotstudio.microsoft.com/environments/YOUR-ENV-ID/home

# Test with annotated screenshots + fix PR
/test-lab recruit/04-creating-a-solution --auto-fix

# Get annotated screenshots only (no PR)
/test-lab recruit/04-creating-a-solution --auto-fix --no-pr

# Test the entire Recruit course
/test-course recruit

# Test a course with auto-fix enabled
/test-course recruit --auto-fix

# Dry-run to see parsed steps without running the browser
/test-lab operative/01-get-started --dry-run

# Test without filing GitHub issues
/test-course operative --no-issue

# Reproduce a specific GitHub issue
/reproduce-issue 42

# Reproduce and auto-fix if confirmed
/reproduce-issue 42 --auto-fix

# Reproduce without posting results back to the issue
/reproduce-issue 42 --no-comment

# Rewrite a lab for a new Copilot Studio UI experience
/rewrite-lab recruit/06-create-agent-from-conversation --env-url https://copilotstudio.microsoft.com/environments/NEW-EXPERIENCE-ENV-ID/home

# Rewrite with custom output location
/rewrite-lab recruit/04-creating-a-solution --env-url https://copilotstudio.microsoft.com/environments/NEW-ENV/home --output-dir ~/Desktop/lab-rewrites/04

# Create a brand-new lab
/create-lab operative --title "Connecting a SharePoint Knowledge Source" --topic "Teach users how to add a SharePoint site as a knowledge source to their agent and test it with sample questions"

# Create a lab with a specific environment
/create-lab recruit --topic "Setting up an MCP server connection" --env-url https://copilotstudio.microsoft.com/environments/NEW-ENV/home

# Export a starter solution for a lab (so learners can skip prerequisites)
/export-solution recruit/06-create-agent-from-conversation

# Export after running all prerequisite steps from scratch
/export-solution recruit/06-create-agent-from-conversation --run-prereqs

# Test a lab and also export the resulting state as a starter solution
/test-lab recruit/06-create-agent-from-conversation --export-solution

# Clean up all Recruit course artifacts (preview first)
/cleanup recruit --dry-run

# Clean up and actually delete
/cleanup recruit

# Clean up only a specific lab's artifacts
/cleanup recruit --lab 06-create-agent-from-conversation

# Clean up but keep the solution container for re-use
/cleanup recruit --keep-solution
```

## Prerequisites

- **Copilot CLI** or **Claude Code**
- **Microsoft Edge** with a browser profile signed into your M365 tenant
- **Node.js** (for `npx @playwright/mcp`)
- **GitHub CLI (`gh`)** authenticated — needed for filing issues to `microsoft/agent-academy`

The plugin ships a `.github/mcp.json` that auto-configures Playwright MCP — no manual Playwright setup needed.

## Installation

```text
/plugin install aprildunnam/AgentAcademyLabTestPlugin
```

After installing, create your personal `.env` file:

```bash
cp .env.example .env
# Edit .env with your environment URL and Edge profile path
```

## Configuration

Environment-specific settings go in `.env` (gitignored, never committed).
Shared settings stay in the `config/` directory.

### Browser & profile (`/.github/mcp.json`)

Controls which browser and profile Playwright uses:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": [
        "-y", "@playwright/mcp@latest",
        "--browser", "msedge",
        "--user-data-dir", "~/Library/Application Support/Microsoft Edge/Profile 39"
      ]
    }
  }
}
```

| Option | Description |
|---|---|
| `--browser` | Browser engine: `msedge`, `chromium`, `firefox`, `webkit` |
| `--user-data-dir` | Path to the browser profile directory. Using a profile with an active M365 session means you skip the login step entirely. |

**Finding your Edge profile path:** On macOS, profiles live at `~/Library/Application Support/Microsoft Edge/Profile N`. Open `edge://version` in your target profile to see the exact path.

### Power Platform environment (`.env`)

Your environment URL is resolved in this order:
1. `--env-url` flag (per-run override)
2. `AGENT_ACADEMY_ENV_URL` in your `.env` file
3. `environment.default_url` in `config/agent-academy-config.yml` (fallback)

Set it in your `.env` file:

```bash
AGENT_ACADEMY_ENV_URL=https://copilotstudio.microsoft.com/environments/YOUR-ENV-ID/home
```

Override per-run with `--env-url`:

```bash
/test-lab recruit/04-creating-a-solution --env-url https://copilotstudio.microsoft.com/environments/OTHER-ENV-ID/home
```

### GitHub issue filing (`config/judge-config.yml`)

Controls when and where issues are filed:

```yaml
issues:
  enabled: true
  repo: "microsoft/agent-academy"
  labels: ["lab-test", "automated"]
  min_confidence_to_file: 0.7
  file_on_verdicts: ["broken", "unclear"]
  on_duplicate: "comment"   # adds a comment to existing open issue instead of filing a duplicate
```

| Setting | Description |
|---|---|
| `enabled` | Set to `false` to globally disable issue filing |
| `repo` | GitHub repo where issues are filed |
| `labels` | Labels applied to every filed issue |
| `min_confidence_to_file` | Minimum LLM judge confidence (0–1) to file. Raise to reduce noise. |
| `file_on_verdicts` | Which verdicts trigger filing. Default: `broken` and `unclear` |
| `on_duplicate` | What to do when an open issue already exists: `comment` or `skip` |

### LLM judge thresholds (`config/judge-config.yml`)

```yaml
confidence:
  min_to_log: 0.5              # below this, findings are dropped entirely
  low_confidence_marker_max: 0.7  # findings below this are tagged "(low confidence)"
  min_to_report: 0.6           # minimum to include in the local report

critique:
  enabled: true                # second-pass review of broken/unclear findings
  downgrade_on_failure: true   # downgrade false positives to pass
```

### Fix PR generation (`config/judge-config.yml`)

Controls the `--auto-fix` behavior:

```yaml
fix_pr:
  enabled: true
  repo: "microsoft/agent-academy"
  branch_pattern: "fix/{course}-{slug}-lab-test-{run_id}"
  labels: ["lab-test", "automated"]
  min_confidence: 0.7          # minimum confidence to include a finding in the fix PR
  fix_verdicts: ["broken"]     # only generate fixes for these verdicts
  fork_fallback: true          # if no push access, open PR from a fork

screenshots:
  output_dir: "runtime/screenshots"
  highlight_color: "#ff4444"
  annotate_on_verdicts: ["broken", "unclear"]
  min_confidence_broken: 0.7
  min_confidence_unclear: 0.8
```

| Setting | Description |
|---|---|
| `fix_pr.enabled` | Set to `false` to globally disable fix PR generation |
| `fix_pr.min_confidence` | Minimum judge confidence to include a finding in the PR |
| `fix_pr.fork_fallback` | If you don't have push access to `microsoft/agent-academy`, open the PR from a fork instead |
| `screenshots.output_dir` | Where annotated screenshots are saved locally |
| `screenshots.highlight_color` | Color of the annotation overlays (hex) |

### Course & lab catalog (`config/agent-academy-config.yml`)

The full lab catalog is defined here. Each lab has:

```yaml
courses:
  recruit:
    title: "Recruit"
    path: "docs/recruit"
    labs:
      - slug: "04-creating-a-solution"
        title: "Creating A Solution"
        interactive: true    # false = conceptual lesson, skipped during testing
```

Labs marked `interactive: false` are conceptual reading material with no hands-on steps — they're skipped automatically.

## How the LLM judge works

For each lab step, after Playwright executes the action:

1. **Captures** an accessibility snapshot + screenshot of the page state
2. **Classifies** the step instruction into an action type (click, type, navigate, verify, etc.)
3. **Compares** what the lab says should happen (expected) vs what the UI shows (observed)
4. **Renders a verdict**:

| Verdict | Meaning |
|---|---|
| `pass` | Step completed as described |
| `broken` | Step cannot be completed as written — UI has diverged from instructions |
| `unclear` | Instruction is ambiguous, multiple interpretations possible |
| `non_deterministic` | Result varies (LLM-generated content) — noted but not a bug |
| `transient` | Temporary failure (loading timeout, etc.) — retryable |
| `cannot_verify` | Step has no observable UI outcome to check |

5. **Critique pass** (for `broken`/`unclear`): A second LLM review argues for the opposite verdict to catch false positives
6. **Files or reports** all confirmed findings with confidence scores and suggested corrections

### Annotated screenshots & fix PRs (Phase 5–6)

When `--auto-fix` is enabled and broken findings exist:

1. **Captures an annotated screenshot** for each broken step — injects a red callout overlay showing the step number, expected text, and actual text, then takes a screenshot
2. **Captures a clean replacement screenshot** of the current UI to replace the outdated lab screenshot
3. **Generates corrected markdown** for each broken step with updated instructions
4. **Opens a fix PR** on `microsoft/agent-academy` with:
   - Updated `index.md` with corrected step text
   - Refreshed screenshots replacing outdated ones
   - Before/after comparison in the PR body with annotated screenshots
   - `Fixes #<issue>` linking to the filed issue (auto-closes on merge)

### Issue reproduction (`/reproduce-issue`)

When you have a bug report filed against a lab, `/reproduce-issue` automates the verification:

1. **Fetches the issue** from `microsoft/agent-academy` and extracts the lab reference + reported broken steps
2. **Runs in targeted mode** — executes prerequisite steps quickly, then runs the reported broken steps with full scrutiny, plus a few steps after to check for cascading failures
3. **Compares live UI** against both the lab instructions AND any screenshots the reporter attached
4. **Classifies the result**: `reproduced`, `partially_reproduced`, `not_reproduced`, `different_issue`, or `environment_dependent`
5. **Posts results** back to the issue as a structured comment with screenshots and a reproduction verdict
6. **Optionally opens a fix PR** (with `--auto-fix`) if the issue is confirmed

This is useful for triaging incoming bug reports — run `/reproduce-issue 42` and let the plugin confirm whether the problem is real, environment-specific, or already fixed.

### Lab rewrite for new UI (`/rewrite-lab`)

When a new Copilot Studio experience rolls out, `/rewrite-lab` helps you migrate existing labs:

1. **Runs the original lab steps** in the new environment (you provide the `--env-url` with the new experience enabled)
2. **Classifies each step**: `unchanged` (works as-is), `modified` (UI renamed/moved), `new_flow` (fundamentally different), `removed` (no longer possible), or `blocked` (not supported)
3. **Discovers the new path** for modified/new-flow steps by figuring out how to accomplish the same goal in the new UI
4. **Captures fresh screenshots** at every step
5. **Generates two files locally** (no PR, no issue — purely for your review):
   - `evaluation.md` — full comparison table with blockers section highlighting anything that's **not possible** in the new UI
   - `index.md` — the complete rewritten lab markdown ready to copy into agent-academy

Output goes to `runtime/rewrites/<course>-<slug>/` (or `--output-dir`). You review, edit, and submit a PR manually when ready.

**Key: blockers are flagged prominently.** If something from the old lab can't be done in the new UI, the evaluation file calls it out with the reason, potential alternatives, and impact on the learning objective.

### Creating new labs from scratch (`/create-lab`)

When you need a net-new lab (not a rewrite of an existing one):

1. **Tell it the course and topic** — e.g., `/create-lab operative --topic "teach users how to connect an MCP server"`
2. **It explores the feature live** in your Copilot Studio environment — discovers the full click path, decision points, and pitfalls
3. **Captures annotated screenshots** (red box around target element) at every step, plus clean backups
4. **Writes a complete lab** in the exact Agent Academy VitePress format — matching the style of existing labs perfectly
5. **Self-validates** by running through its own instructions to confirm they work
6. **Generates an evaluation file** with stats, validation results, and suggested placement in the course

Output is local only (`runtime/new-labs/<course>-<slug>/`). You review the generated `index.md`, edit to taste, and manually add it to the agent-academy repo when ready.

**What input does it need?**

| Input | Required? | How to provide |
|---|---|---|
| Course | Yes | First argument: `recruit`, `operative`, `special-ops`, `cowork-collective` |
| Topic | Yes | `--topic "..."` flag, or it will ask you |
| Title | Recommended | `--title "..."` flag, or it will generate one |
| Codename | Optional | It will ask (e.g., "OPERATION KNOWLEDGE DROP") or generate one |
| Prerequisites | Asked | It will ask what prior labs or artifacts are needed |
| Time estimate | Asked | How many minutes (defaults: 30–45 recruit, 45–60 operative) |
| Environment URL | Optional | `--env-url` flag or uses your default |

The more detail you give in `--topic`, the better. Compare:
- ❌ Vague: `--topic "SharePoint"`
- ✅ Good: `--topic "teach users how to add a SharePoint site as a knowledge source to their agent, configure the indexing, and test it by asking questions about the SharePoint content"`

**Style matching:** The generated markdown uses the exact Agent Academy conventions — `<mission-meta />`, VitePress frontmatter (prev/next, difficulty, codename, tags), heading anchors, `::: warning` blocks, "select" instead of "click", bold exact UI text, `1.` for all steps, tables for field properties, and the spy/mission narrative voice.

### Modular lab solutions (`/export-solution`)

Labs in Agent Academy build on each other — Lab 06 needs artifacts from Labs 04 and 05. The `/export-solution` command creates **starter packs** so learners can jump to any lab:

1. **Identifies what the target lab needs** — catalogs all artifacts from prerequisite labs (agents, topics, flows, tables, etc.)
2. **Validates artifacts exist** in the environment (or runs prereqs with `--run-prereqs` to create them from scratch)
3. **Ensures everything is in the correct solution** — adds missing components via "Add existing"
4. **Runs solution validation** — blocks export on critical errors
5. **Publishes and exports** as managed .zip, unmanaged .zip, or both
6. **Generates a manifest** with import instructions and post-import setup steps

The result is a `.zip` file that a learner can import into their environment to instantly have all prerequisites ready.

**Use with other commands:** Add `--export-solution` to `/test-lab`, `/rewrite-lab`, or `/create-lab` to also produce the starter solution after the primary task completes.

Output goes to `runtime/solutions/<course>-<slug>/` with the .zip(s) and a `manifest.md`.

### Environment cleanup (`/cleanup`)

When you want to re-run labs from scratch, `/cleanup` removes all lab-created artifacts:

1. **Catalogs what each lab created** — agents, topics, flows, solutions, publishers, etc.
2. **Discovers what actually exists** in the environment (via Power Platform CLI `pac` or browser)
3. **Shows you a cleanup plan** — you must confirm before anything is deleted
4. **Deletes in dependency order** — inside-out (topics → agents → solution → publisher)
5. **Verifies clean state** — confirms everything is gone

**Safety features:**
- `--dry-run` shows the plan without deleting anything (always run this first!)
- Never deletes system artifacts, Default Solution, or non-lab items
- Warns about cross-lab dependencies (e.g., "deleting Lab 06's agent will break Labs 07-13")
- Requires explicit confirmation (or `--force` to skip)

**Power Platform CLI integration:** If `pac` is installed (`dotnet tool install --global Microsoft.PowerApps.CLI.Tool`), cleanup is faster and more reliable. Falls back to browser-based deletion via Playwright if `pac` isn't available.

## Architecture

```
.claude-plugin/plugin.json          — Plugin identity & version
.github/mcp.json                    — Playwright MCP config (browser, profile)
config/
  agent-academy-config.yml          — Course catalog, environment URL, auth settings
  judge-config.yml                  — LLM judge thresholds, issue filing config
commands/
  test-lab.md                       — /test-lab command definition
  test-course.md                    — /test-course command definition
  reproduce-issue.md                — /reproduce-issue command definition
  rewrite-lab.md                    — /rewrite-lab command definition
  create-lab.md                     — /create-lab command definition
  export-solution.md                — /export-solution command definition
  cleanup.md                        — /cleanup command definition
skills/
  agent-academy-tester/
    SKILL.md                        — Main orchestration skill (auth → parse → execute → judge → report)
    references/
      lab-parser-spec.md            — VitePress markdown → step tree parsing rules
      playwright-cookbook.md         — Portal navigation patterns, Edge/M365 quirks
      llm-judge-prompts.md          — Judge, critique, and action classifier prompts
      finding-schema.md             — Test result structure and severity definitions
      screenshot-annotation-spec.md — Annotated screenshot and fix PR specification
```

## License

MIT
