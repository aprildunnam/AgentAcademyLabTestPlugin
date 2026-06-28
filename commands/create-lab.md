---
description: Create a brand-new Agent Academy lab from scratch by exploring a feature in Copilot Studio, documenting the steps, and generating a complete lab markdown file in the Agent Academy format.
argument-hint: "[<course>] [--title <title>] [--topic <description>] [--env-url <url>] [--output-dir <path>]"
---

# /create-lab

You are creating a brand-new Agent Academy lab from scratch.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the course where this lab belongs: `recruit`, `operative`,
`special-ops`, or `cowork-collective`. If omitted, ask the user.

Flags:
- `--title <title>` — The lab/mission title (e.g., "Building a Knowledge Agent").
  If omitted, ask the user.
- `--topic <description>` — A brief description of what the lab should teach. Can be
  a sentence or a few bullet points. If omitted, ask the user.
- `--env-url <url>` — The Copilot Studio environment URL to use while exploring and
  documenting the feature. Falls back to `environment.default_url` from config.
- `--output-dir <path>` — Where to save the generated lab. Defaults to
  `runtime/new-labs/<course>-<slug>/`.

## Your task

Invoke the `agent-academy-tester` skill in **lab creation mode**:

### Step 1 — Gather requirements

If not provided via flags, ask the user:
1. **Which course?** (recruit, operative, special-ops, cowork-collective)
2. **What's the lab about?** Get a topic description — can be high-level like
   "teach users how to connect a SharePoint knowledge source to their agent" or
   detailed with specific steps they want covered.
3. **Any prerequisites?** Does this lab build on a prior lab? Should the learner
   already have a solution, agent, or other artifact created?
4. **Difficulty level?** Beginner (recruit-level), intermediate (operative), or
   advanced (special-ops)?

### Step 2 — Explore the feature

1. **Open the browser** and navigate to the Copilot Studio environment.
2. **Follow standard auth** (Phase 2 from SKILL.md).
3. **Explore the feature** described in the topic. Your goal is to discover:
   - The exact click path to accomplish the task
   - Any prerequisites (existing agent, solution, data source, etc.)
   - Decision points where the user has options
   - Common pitfalls or non-obvious steps
   - What the UI looks like at each stage
4. **Capture screenshots** at every meaningful step. Save to `<output-dir>/assets/`.
5. **Take notes** on:
   - Button labels, menu items, dialog titles (exactly as shown)
   - Any fields that need specific values
   - Confirmation messages or success indicators
   - Time-sensitive steps (things that take a moment to process)

### Step 3 — Determine lab structure

Based on your exploration, plan the lab structure:

1. **Assign a mission number.** Look at existing labs in the target course to find
   the next available number (e.g., if the last is `13-...`, this is `14-...`).

2. **Define sections.** Group steps into logical sections (typically 2–5 sections):
   - Each section gets a `## 🧪 Lab XX: Section Title` heading
   - Each section has numbered subsections (`### X.Y Subsection Title`)

3. **Define objectives.** What will the learner be able to do after completing this lab?
   (typically 3–5 bullet points)

4. **Identify prerequisites.** What must exist before starting? (prior labs, assets, etc.)

### Step 4 — Write the lab markdown

Generate `<output-dir>/index.md` in the exact Agent Academy VitePress format:

```markdown
---
title: "🚨 Mission XX: {Title}"
description: "{One-line description}"
---

# 🚨 Mission XX: {Title}

## 🎯 Mission Brief

{2-3 paragraph introduction explaining what the learner will accomplish and why
it matters. Written in a friendly, encouraging tone. Reference the Agent Academy
narrative voice — learners are "recruits" in the recruit course, "operatives" in
the operative course, etc.}

## 🔎 Objectives

By the end of this mission, you will:
- {Objective 1}
- {Objective 2}
- {Objective 3}

## 🧪 Lab XX: {Section Title}

### Prerequisites

{List anything needed before starting. Reference prior labs by number if applicable.}

> [!NOTE]
> {Any helpful context or tips before starting}

### X.1 {First Subsection Title}

1. {Step instruction with **bold UI elements** to interact with}

   ![{alt text}](./assets/{screenshot-filename}.png)

2. {Next step...}

   ```text
   {Any text the user needs to copy/paste}
   ```

3. {Step with a verification point}

   > [!TIP]
   > {Helpful tip about what to look for}

### X.2 {Second Subsection Title}

1. {Continue with steps...}

## ✅ Mission Complete

🎉 {Congratulatory message summarizing what was accomplished.}

You have successfully:
- {Accomplishment 1}
- {Accomplishment 2}
- {Accomplishment 3}

### Next Steps

{Suggest what to explore next or which lab to do after this one.}
```

### Step 5 — Validate the lab

After writing the lab, **run through it yourself** in the same browser session:

1. Reset to a clean starting state (if possible — navigate back to home)
2. Follow the lab instructions exactly as written
3. At each step, verify:
   - The UI element referenced actually exists and is named correctly
   - The screenshot matches what the learner would see
   - The instruction is unambiguous — only one interpretation possible
   - No steps are missing between actions
4. Note any issues found during validation and fix them in the markdown

### Step 6 — Generate supporting files

Write `<output-dir>/evaluation.md`:

```markdown
# New Lab Evaluation — {course}/{slug}

**Title:** {title}
**Course:** {course}
**Date created:** {date}
**Environment:** {env_url}

## Summary

| Metric | Value |
|---|---|
| Total sections | {count} |
| Total steps | {count} |
| Screenshots captured | {count} |
| Prerequisites | {list} |
| Estimated completion time | {minutes} min |

## Validation Results

| Step | Status | Notes |
|---|---|---|
{for each step: step number, pass/issue, any notes}

## Suggested placement

- **Course:** {course}
- **Mission number:** {XX}
- **Slug:** {slug}
- **Path:** `docs/{course}/{slug}/index.md`
- **Depends on:** {list of prerequisite labs, if any}
- **Leads into:** {suggested next lab, if applicable}
```

### Step 7 — Present results

Display to the user:
- Lab title and summary
- Number of steps and sections
- Path to output files
- Any validation issues found
- Suggested slug and file path for when they're ready to add it to agent-academy

Remind the user:
```
📝 The new lab is saved locally at: {output_dir}
Review index.md, edit as needed, then copy to docs/{course}/{slug}/ in the
agent-academy repo when ready to submit a PR.
```

**Do NOT open a PR or file an issue.** This is local-only output.

## Writing style guidelines

When writing lab instructions, match the Agent Academy voice:

- **Friendly and encouraging** — learners are on a mission, not reading a manual
- **Precise about UI elements** — always bold the exact button/menu text: **Create agent**
- **One action per step** — don't combine "click X and then type Y" into one step
- **Show, don't just tell** — include a screenshot after every meaningful action
- **Anticipate confusion** — use `> [!TIP]` blocks for non-obvious things
- **Use code blocks** for anything the user needs to type or paste verbatim
- **Keep steps scannable** — short sentences, active voice, start with a verb

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for browser auth and
Playwright execution procedures.
