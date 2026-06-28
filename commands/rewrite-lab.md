---
description: Rewrite an existing Agent Academy lab for a new Copilot Studio UI experience. Runs the lab steps in a new environment, documents differences, captures fresh screenshots, and generates an updated lab markdown file locally.
argument-hint: "[<course>/<slug>] [--env-url <url>] [--output-dir <path>]"
---

# /rewrite-lab

You are rewriting an existing Agent Academy lab to reflect a new Copilot Studio UI experience.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the lab path in `<course>/<slug>` format (e.g.,
`recruit/04-creating-a-solution`). If omitted, present the user with a list of
available interactive labs to choose from.

Flags:
- `--env-url <url>` — **(Required for most runs)** The Copilot Studio environment URL
  with the new experience enabled. This environment may differ from the default testing
  environment. Example:
  `https://copilotstudio.microsoft.com/environments/<new-experience-env-id>/home`
- `--output-dir <path>` — Where to save the rewritten lab and screenshots locally.
  Defaults to `runtime/rewrites/<course>-<slug>/`.
- `--export-solution` — after rewriting, also export the environment state as a
  Power Platform solution .zip starter pack for the rewritten lab.

## Your task

Invoke the `agent-academy-tester` skill in **rewrite mode**:

1. **Fetch the original lab.** Clone/pull `microsoft/agent-academy` and read the lab's
   `index.md`. Parse it into a step tree per the lab-parser-spec.

2. **Resolve environment URL.** The `--env-url` flag is the primary source. If not
   provided, fall back to `environment.default_url` from config. Since the purpose is
   testing a *new* experience, prompt the user if no URL was explicitly provided:
   ```
   ⚠️ No --env-url provided. The rewrite mode is designed for a new UI experience
   in a specific environment. Are you sure you want to use the default environment?
   ```

3. **Browser authentication.** Open the browser and navigate to the provided environment
   URL. Follow the standard Phase 2 auth flow (detect if already signed in, prompt user
   if not).

4. **Walk through each step.** For every step in the original lab:

   a. **Attempt the step as written.** Try to execute the original instruction in the
      new UI using Playwright.

   b. **Evaluate the result.** Classify into one of:

      | Status | Meaning |
      |---|---|
      | `unchanged` | Step works exactly as written — no rewrite needed |
      | `modified` | Step works but UI elements have changed (renamed, moved, restyled) |
      | `new_flow` | The workflow is fundamentally different — new steps needed |
      | `removed` | This capability no longer exists in the new UI |
      | `blocked` | Cannot complete — new UI doesn't support this action at all |

   c. **If `modified` or `new_flow`:** Figure out the correct way to accomplish the
      same goal in the new UI. Execute that path to confirm it works. Record the new
      step-by-step instructions.

   d. **If `removed` or `blocked`:** Document what's missing. Note any alternative
      approach if one exists. Flag this prominently in the evaluation.

   e. **Capture screenshots** at every step (both successful and blocked):
      - First, take a **clean screenshot** → save as `<output-dir>/assets/step-<N>.png`
      - Then, **annotate the screenshot** by injecting a red box around the UI element
        the step references (the bold text target). Use `browser_evaluate` to overlay a
        3px red border around the element, then take a second screenshot → save as
        `<output-dir>/assets/step-<N>-annotated.png`
      - Remove the overlay after capturing.
      - The annotated version is what gets referenced in the generated `index.md`.
        The clean version is a backup in case the annotation is wrong.
      - See `references/lab-screenshot-guide.md` for the annotation procedure and
        fallback behavior.

5. **Generate the evaluation file.** Write `<output-dir>/evaluation.md`:

   ```markdown
   # Lab Rewrite Evaluation — {course}/{slug}

   **Original lab:** {title}
   **Date evaluated:** {date}
   **Environment:** {env_url}
   **Plugin version:** {version}

   ## Summary

   | Metric | Count |
   |---|---|
   | Total steps | {total} |
   | Unchanged | {unchanged_count} |
   | Modified (UI changes) | {modified_count} |
   | New flow required | {new_flow_count} |
   | Removed/Not possible | {removed_count} |
   | Blocked | {blocked_count} |

   ## ⚠️ Blockers & Removed Capabilities

   {for each removed/blocked step}
   ### Step {N}: {original_instruction}
   - **Status:** {removed|blocked}
   - **Reason:** {why this doesn't work}
   - **Alternative:** {if any, or "None identified"}
   - **Impact:** {what learners lose if this step is removed}
   - **Screenshot:** ![](./assets/step-{N}-{status}.png)
   {end for}

   ## Step-by-Step Comparison

   {for each step}
   ### Step {N}
   - **Original:** {original_instruction}
   - **Status:** {unchanged|modified|new_flow|removed|blocked}
   - **New instruction:** {rewritten instruction, or "Same as original"}
   - **What changed:** {description of UI difference}
   - **Screenshot:** ![](./assets/step-{N}-{status}.png)
   {end for}
   ```

6. **Generate the rewritten lab markdown.** Write `<output-dir>/index.md`:
   - **Preserve the exact Agent Academy VitePress format** — frontmatter (prev/next,
     short-description, difficulty, codename, time, tags, products), `<mission-meta />`,
     heading anchors `{#slug}`, `::: warning` blocks, etc.
   - Start from the original lab's structure (headings, sections, mission brief, objectives)
   - Replace each step's instruction text with the new version (for `modified`/`new_flow`)
   - Keep `unchanged` steps as-is
   - For `removed`/`blocked` steps: insert a clearly-marked comment block:
     ```markdown
     <!-- ⚠️ BLOCKED: This step is not possible in the new UI experience.
          Original: "{original_instruction}"
          Reason: {reason}
          Alternative: {alternative or "None — manual review needed"} -->
     ```
   - Update all screenshot references to use the annotated captures (`step-N-annotated.png`)
   - Ensure screenshots are 4-space indented under their step
   - Use `1.` for all numbered steps (VitePress auto-numbers)
   - Keep the Agent Academy voice: "select" not "click", bold exact UI text,
     "Copy and paste the following as the **{field}**," pattern for text entry
   - Add a note at the top:
     ```markdown
     > [!NOTE]
     > This lab has been updated for the new Copilot Studio experience ({date}).
     > See `evaluation.md` for a full comparison with the original.
     ```

7. **Present results to the user.** Display:
   - Summary table (how many steps changed, blocked, etc.)
   - Path to the output directory
   - Any blockers that need manual attention
   - Remind the user: "The rewritten lab is saved locally. Review and edit as needed
     before submitting a PR."

   **Do NOT open a PR.** This is local-only output for the user to review and manually
   submit when ready.

## Output structure

```
runtime/rewrites/<course>-<slug>/
  index.md              — The rewritten lab (references -annotated screenshots)
  evaluation.md         — Full step-by-step comparison + blockers
  assets/
    step-01.png                — clean backup screenshot
    step-01-annotated.png      — annotated version (red box around target element)
    step-02.png
    step-02-annotated.png
    ...
```

The `index.md` always references `step-<N>-annotated.png`. The clean versions are
backups in case annotations need to be re-done manually.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for browser auth and
Playwright execution procedures.
