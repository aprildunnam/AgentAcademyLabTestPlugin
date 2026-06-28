---
description: Export a Power Platform solution "starter pack" for a lab — ensures artifacts are in the correct solution, validates, publishes, and exports a managed/unmanaged .zip that learners can import to skip prerequisite labs.
argument-hint: "[<course>/<slug>] [--solution-name <name>] [--env-url <url>] [--export-type <managed|unmanaged|both>] [--output-dir <path>]"
---

# /export-solution

You are creating a "starter solution" export for a lab so learners can skip prerequisite
labs by importing the solution file.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab path in `<course>/<slug>` format (e.g.,
`recruit/06-create-agent-from-conversation`). This is the lab the solution is FOR —
meaning the exported solution contains everything needed to START this lab (all
artifacts from prior labs).

If omitted, present the user with a list of available interactive labs to choose from.

Flags:
- `--solution-name <name>` — The Power Platform solution's display name to use.
  If omitted, defaults to `AgentAcademy_<Course>_Lab<XX>_Starter`
  (e.g., `AgentAcademy_Recruit_Lab06_Starter`).
- `--env-url <url>` — The Copilot Studio environment URL. Falls back to
  `environment.default_url` from config.
- `--export-type <managed|unmanaged|both>` — Which solution type(s) to export.
  Default: `both`.
- `--output-dir <path>` — Where to save the exported .zip file(s) and manifest.
  Defaults to `runtime/solutions/<course>-<slug>/`.
- `--run-prereqs` — Actually run all prerequisite lab steps first to create the
  artifacts before exporting. Without this flag, assumes artifacts already exist
  in the environment and just validates + exports.
- `--include-data` — Include sample data in the export (environment variables,
  connection references with placeholder values).

## Your task

Invoke the `agent-academy-tester` skill in **solution export mode**:

### Phase 1 — Determine what the starter solution needs

1. **Identify prerequisite labs.** Look at the target lab's prerequisites section and
   the course ordering in `config/agent-academy-config.yml`. Determine which prior labs
   produce artifacts needed for the target lab.

2. **Catalog required artifacts.** For each prerequisite lab, identify what it creates:
   - Solutions (publisher, solution name)
   - Agents (Copilot Studio agents)
   - Topics (custom topics added to agents)
   - Flows (Power Automate cloud flows)
   - Tables (Dataverse tables/entities)
   - Environment variables
   - Connection references
   - Knowledge sources (SharePoint, files, etc.)
   - Adaptive cards
   - Any other Power Platform components

3. **Map artifacts to solutions.** Determine which Power Platform solution each artifact
   should belong to. If the labs use a single solution (e.g., the one created in Lab 04),
   note that. If multiple solutions exist, catalog the mapping.

### Phase 2 — Validate artifacts exist (or create them)

1. **Open the browser** and navigate to the Copilot Studio environment. Authenticate
   per Phase 2 of SKILL.md.

2. **If `--run-prereqs` is passed:** Execute all prerequisite lab steps sequentially
   (using the standard Phase 3 execution flow) to create the artifacts from scratch.
   This ensures a clean, reproducible state.

3. **If `--run-prereqs` is NOT passed:** Validate that the expected artifacts already
   exist in the environment:
   - Navigate to the Solution Explorer
   - Check that the target solution exists
   - Verify key components are present (agents, topics, flows, etc.)
   - Report any missing artifacts and ask the user how to proceed

4. **Ensure artifacts are in the correct solution:**
   - Navigate to the Solution Explorer → open the target solution
   - Check "Objects" or "Components" to see what's included
   - If artifacts are in the Default Solution but not the target solution, add them:
     - Select **Add existing** → **{component type}** → select the artifact → **Add**
   - Take a screenshot of the final solution contents for the manifest

### Phase 3 — Validate the solution

1. **Run solution checker** (if available in the environment):
   - In the Solution Explorer, select the solution → **Solution checker** → **Run**
   - Wait for results
   - Report any errors or warnings
   - Critical errors block export; warnings are noted in the manifest

2. **Verify component dependencies:**
   - Check that all dependencies are included (no missing references)
   - Ensure connection references have appropriate placeholder values
   - Verify environment variables have default values set

### Phase 4 — Publish and export

1. **Publish all customizations:**
   - In the solution, select **Publish all customizations**
   - Wait for publish to complete
   - Take a screenshot confirming success

2. **Export the solution:**
   - Select the solution → **Export solution**
   - For **unmanaged** export:
     - Select "As unmanaged" → **Export**
     - Wait for download → save as `<solution-name>_unmanaged.zip`
   - For **managed** export:
     - Select "As managed" → **Export**
     - Wait for download → save as `<solution-name>_managed.zip`
   - If `--export-type both`, do both exports

3. **Save the exported file(s)** to `<output-dir>/`.

### Phase 5 — Generate the manifest

Write `<output-dir>/manifest.md`:

```markdown
# Solution Starter Pack — {course}/{slug}

## Purpose

This solution contains all artifacts needed to START **{lab title}** without
completing the prerequisite labs. Import this solution into your environment
and you're ready to begin.

## Solution details

| Property | Value |
|---|---|
| Solution name | {solution_name} |
| Publisher | {publisher_name} |
| Version | {version} |
| Export date | {date} |
| Source environment | {env_url} |
| Export type | {managed/unmanaged/both} |

## Included artifacts

| Type | Name | From lab |
|---|---|---|
| Agent | {name} | Lab {XX} |
| Topic | {name} | Lab {XX} |
| Flow | {name} | Lab {XX} |
| ... | ... | ... |

## Prerequisites for the learner

Before importing this solution, the learner needs:
- A Power Platform developer environment
- {Security roles needed}
- {Any connections that must be configured post-import}

## Import instructions

1. In Copilot Studio, navigate to **Solutions** from the left navigation
1. Select **Import solution**
1. Select **Browse** and choose `{filename}.zip`
1. Select **Next** → review the import settings
1. Configure any connection references (if prompted)
1. Select **Import** and wait for completion
1. Verify the agent appears in your agent list

## Post-import setup

{Any steps needed after importing — e.g., "publish the agent", "configure the
SharePoint connection with your site URL", etc.}

## Validation results

{Solution checker results — errors, warnings, or "No issues found"}

## Files in this package

- `{solution_name}_unmanaged.zip` — for development/modification
- `{solution_name}_managed.zip` — for deployment (locked, no editing)
- `manifest.md` — this file
- `solution-contents.png` — screenshot of solution components
```

### Phase 6 — Present results

Display to the user:
- Solution name and contents summary
- File paths for the exported .zip(s)
- Any validation warnings
- Import instructions for learners

**Do NOT upload or PR anything.** The exports are local for the user to include
in the agent-academy repo or distribute as they see fit.

## Integration with other commands

When used with `--export-solution` flag on other commands:

- `/test-lab <slug> --export-solution` — after testing, also export the resulting state
- `/rewrite-lab <slug> --export-solution` — after rewriting, export the new-UI state
- `/create-lab <course> --export-solution` — after creating, export the end state

In these integrated modes, the solution export happens AFTER the primary command
completes successfully. If the primary command fails, no export is attempted.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for browser auth and
Playwright execution procedures.
