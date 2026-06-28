---
description: Remove Power Platform artifacts created by Agent Academy labs so you can re-run labs from a clean state. Uses the Power Platform CLI (pac) and browser-based Solution Explorer to delete solutions, agents, topics, flows, and other components.
argument-hint: "[<course>] [--lab <slug>] [--env-url <url>] [--dry-run] [--keep-solution]"
---

# /cleanup

You are cleaning up Power Platform artifacts created by Agent Academy labs so the
environment can be returned to a clean state for re-running labs.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the course to clean up: `recruit`, `operative`,
`special-ops`, or `cowork-collective`. If omitted, ask the user which course or
specific lab(s) to clean.

Flags:
- `--lab <slug>` — Clean up only artifacts from a specific lab (e.g., `--lab 06-create-agent-from-conversation`).
  Without this, cleans up ALL labs in the specified course.
- `--env-url <url>` — The Copilot Studio environment URL to clean. Falls back to
  `environment.default_url` from config.
- `--dry-run` — List what WOULD be deleted without actually deleting anything.
  Always recommend running this first.
- `--keep-solution` — Delete the solution's contents but keep the empty solution
  container and publisher. Useful if you want to re-run labs into the same solution.
- `--force` — Skip the confirmation prompt. Without this, the user must confirm
  before any deletions occur.

## Your task

Invoke the `agent-academy-tester` skill in **cleanup mode**:

### Phase 1 — Identify artifacts to remove

1. **Determine scope.** Based on the course and optional `--lab` flag, identify which
   labs are in scope for cleanup.

2. **Catalog expected artifacts.** For each lab in scope, determine what it creates:
   - From the lab's `index.md` steps (what the lab instructs users to create)
   - From the course config in `agent-academy-config.yml`

   Common artifact types:

   | Type | Example | How created |
   |---|---|---|
   | Solution | `Contoso IT Helpdesk` | Lab 04 |
   | Publisher | `Contoso Solutions` | Lab 04 |
   | Agent | `IT Helpdesk Agent` | Lab 05/06 |
   | Topic | custom topics | Lab 07+ |
   | Cloud Flow | Power Automate flows | Lab 09+ |
   | Knowledge Source | SharePoint, files | Operative labs |
   | Environment Variable | connection strings | Various |
   | Adaptive Card | card definitions | Lab 11 |

3. **Check for dependencies.** Some artifacts are shared across labs. Map the
   dependency graph so that:
   - If cleaning Lab 06, also note that Labs 07+ depend on Lab 06's agent
   - Warn the user if they're about to delete something that later labs need

### Phase 2 — Discover actual artifacts in the environment

1. **Open the browser** and authenticate (Phase 2 from SKILL.md).

2. **Try Power Platform CLI first.** If `pac` is available, use it for faster discovery:

   ```bash
   # Authenticate to the environment
   pac auth create --environment "https://org<id>.crm.dynamics.com"

   # List solutions
   pac solution list

   # List specific components
   pac solution list-components --solution-name "<solution_unique_name>"
   ```

   If `pac` is not installed or fails, fall back to browser-based discovery (step 3).

3. **Browser-based discovery (fallback).** Navigate to Solution Explorer in Copilot Studio:
   - Open the target solution
   - Catalog all components: agents, topics, flows, tables, etc.
   - Take a screenshot of the current state for the cleanup report

4. **Match expected vs actual.** Compare what the labs should have created against
   what actually exists. Flag any unexpected artifacts (created manually, by other
   labs, or by the system).

### Phase 3 — Present cleanup plan

**Always present the plan before executing** (unless `--force` is passed):

```
🧹 Cleanup Plan — {course} {lab if specified}

Environment: {env_url}
Mode: {dry-run | live}

The following artifacts will be DELETED:

┌─────────────────────────────────────────────────────┐
│ Type          │ Name                    │ From Lab   │
├─────────────────────────────────────────────────────┤
│ Agent         │ IT Helpdesk Agent       │ Lab 06     │
│ Topic         │ Greeting                │ Lab 07     │
│ Topic         │ IT Support              │ Lab 08     │
│ Cloud Flow    │ Ticket Creation         │ Lab 09     │
│ Solution      │ Contoso IT Helpdesk     │ Lab 04     │
│ Publisher     │ Contoso Solutions       │ Lab 04     │
└─────────────────────────────────────────────────────┘

⚠️  Warnings:
- Deleting "IT Helpdesk Agent" will break Labs 07-13 (they depend on this agent)
- Solution "Contoso IT Helpdesk" contains 12 components

Proceed with deletion? (The user must confirm)
```

If `--dry-run`, show the plan and stop — do NOT delete anything.

### Phase 4 — Execute cleanup

After user confirmation, delete artifacts in the correct order (dependencies first,
containers last):

**Deletion order (inside-out):**
1. Knowledge sources (remove from agent)
2. Topics (remove from agent, then delete)
3. Cloud flows (deactivate, then delete)
4. Adaptive cards
5. Environment variables
6. Agents (delete the agent itself)
7. Tables (only if created by the lab — NEVER delete system tables)
8. Solution components (remove from solution if `--keep-solution`)
9. Solution (delete the solution container)
10. Publisher (delete only if no other solutions use it)

**Using Power Platform CLI (preferred):**

```bash
# Delete a solution and all its components
pac solution delete --solution-name "<unique_name>"

# Or remove specific components first
pac solution remove-component --solution-name "<name>" --component-id "<guid>" --component-type "<type_code>"
```

**Using browser (fallback):**
- Navigate to the component → select **Delete** or **Remove**
- For agents: Copilot Studio → select agent → **...** → **Delete**
- For solutions: Solution Explorer → select solution → **Delete**
- For flows: Power Automate → select flow → **Delete**

**Safety rules:**
- NEVER delete the Default Solution
- NEVER delete system publishers (Microsoft, Common Data Service Default Publisher)
- NEVER delete Dataverse system tables (Account, Contact, etc.)
- NEVER delete artifacts not created by Agent Academy labs
- If an artifact can't be deleted (permission error, dependency), log it and continue

### Phase 5 — Generate cleanup report

Write `runtime/cleanup/<course>-<timestamp>.md`:

```markdown
# Cleanup Report — {course}

**Date:** {date}
**Environment:** {env_url}
**Scope:** {course} {lab if specified}
**Mode:** {dry-run | live}

## Summary

| Action | Count |
|---|---|
| Deleted | {count} |
| Skipped (dependency) | {count} |
| Failed | {count} |
| Not found | {count} |

## Deleted artifacts

| Type | Name | Status |
|---|---|---|
| Agent | IT Helpdesk Agent | ✅ Deleted |
| Topic | Greeting | ✅ Deleted |
| Solution | Contoso IT Helpdesk | ✅ Deleted |

## Skipped

{any artifacts that were skipped and why}

## Errors

{any failures with error messages}

## Environment state

The following Agent Academy artifacts remain in the environment:
{list of anything still present — from other courses, etc.}
```

### Phase 6 — Confirm clean state

After deletion, verify the environment is clean:
1. Refresh Solution Explorer — confirm the solution is gone
2. Check the agent list — confirm the agent is gone
3. Take a final screenshot of the clean state

Display to the user:
- Summary of what was deleted
- Any failures or skipped items
- Confirmation that the environment is ready for a fresh run

## Power Platform CLI setup

The `pac` CLI enables faster, more reliable cleanup. If it's not installed:

```bash
# Install via dotnet
dotnet tool install --global Microsoft.PowerApps.CLI.Tool

# Or via npm
npm install -g pac
```

If `pac` is not available, all operations fall back to browser-based cleanup via
Playwright — slower but always works.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for browser auth and
Playwright execution procedures.
