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
- `--export-solution` — after creating the lab, also export the resulting environment
  state as a Power Platform solution .zip starter pack.

## Your task

Invoke the `agent-academy-tester` skill in **lab creation mode**:

### Step 1 — Gather requirements

If not provided via flags, ask the user for the following information. **All of these
are needed** to produce a high-quality lab — don't skip any:

1. **Which course?** (recruit, operative, special-ops, cowork-collective)
   - `recruit` = beginner, fundamentals of Copilot Studio
   - `operative` = intermediate, advanced agent features
   - `special-ops` = advanced integrations (MCP, external services)
   - `cowork-collective` = real-world multi-agent scenarios

2. **What's the lab about?** Get a topic description. The more detail the better:
   - What feature/capability should the learner walk through?
   - What's the end result? (e.g., "an agent that answers questions from SharePoint")
   - Any specific scenarios or data to use as examples?

3. **What's the codename?** Agent Academy uses spy/mission codenames for flavor
   (e.g., "OPERATION CTRL-ALT-PACKAGE", "OPERATION KNOWLEDGE DROP"). Ask the user
   for one, or generate a fun one that fits the theme.

4. **Any prerequisites?** Does this lab build on a prior lab? Should the learner
   already have:
   - A specific solution created?
   - An existing agent to modify?
   - A data source configured?
   - Specific security roles?

5. **Estimated time?** How long should this lab take (in minutes)? Default to 30–45
   for recruit, 45–60 for operative, 60+ for special-ops.

6. **Tags and products?** What tags apply? (e.g., `copilot-studio`, `power-platform`,
   `sharepoint`, `mcp`, `adaptive-cards`)

### Step 2 — Explore the feature

1. **Open the browser** and navigate to the Copilot Studio environment.
2. **Follow standard auth** (Phase 2 from SKILL.md).
3. **Explore the feature** described in the topic. Your goal is to discover:
   - The exact click path to accomplish the task
   - Any prerequisites (existing agent, solution, data source, etc.)
   - Decision points where the user has options
   - Common pitfalls or non-obvious steps
   - What the UI looks like at each stage
4. **Capture screenshots** at every meaningful step using the two-file strategy:
   - Take a **clean screenshot** first → save as `step-<N>.png`
   - Then **annotate** by injecting a red box around the UI element the step
     references → save as `step-<N>-annotated.png`
   - Remove the overlay after capturing
   - The annotated version goes in the rendered `index.md`; the clean version is a backup
   - See `references/lab-screenshot-guide.md` for the full annotation procedure
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

Generate `<output-dir>/index.md` in the **exact** Agent Academy VitePress format.
Study this template carefully — it matches the real labs in `microsoft/agent-academy`:

```markdown
---
prev:
  text: {Previous lab title}
  link: /{course}/{prev-slug}
next:
  text: {Next lab title}
  link: /{course}/{next-slug}
short-description: {One-line description for navigation}
difficulty: {1=beginner, 2=intermediate, 3=advanced}
codename: {OPERATION CODENAME IN ALL CAPS}
time: {estimated minutes}
tags:
  - {tag1}
  - {tag2}
products:
  - copilot-studio
  - power-platform
industries:
  - it
created-date: {YYYY-MM-DD}
last-edited-date: {YYYY-MM-DD}
---
# 🚨 Mission {XX}: {Title} {#{slug-anchor}}

<mission-meta />

## 🎯 Mission Brief {#mission-brief}

{Agent Maker / Operative / Special Agent}, welcome to your next {tactical operation / mission / assignment}. In this mission, you'll learn to {what they'll accomplish}. Think of this as {fun analogy that fits the spy/mission theme}.

{Second paragraph explaining WHY this matters in the real world.}

Let's {get started / begin / dive in}!

> [!NOTE]
> {Any important context before starting — e.g., "If your Copilot Studio screen looks different..."}

## 🔎 Objectives {#objectives}

In this mission, you'll learn:

1. {Objective as a gerund phrase — "Understanding what X is and its role in Y"}
1. {Objective 2}
1. {Objective 3}
1. {Objective 4}
1. {Objective 5}

## 🕵🏻‍♀️ {Conceptual Section Title} {#slug-anchor}

{2-4 paragraphs of conceptual explanation with personality. Use emoji sparingly 🤓.
Include diagrams or tables when helpful. This section teaches the "why" before the
hands-on "how".}

   ![{Descriptive alt text}](./assets/{XX.0_01_Description}.png)

{More explanation, possibly with a bulleted list of key concepts.}

## 🧪 Lab {XX}: {Hands-on Section Title} {#lab-xx-slug}

We're now going to learn

- {What they'll do in bullet form}
- {Second thing}

Let's begin!

### Prerequisites

{Security roles, prior labs, or environment requirements}

::: warning {Warning title}
{Important prerequisite warning — e.g., "Make sure you switch to your developer environment"}
:::

1. {Prerequisite step if any setup is needed}

    ![{Alt text}](./assets/{XX.0_0N_Description}.png)

### {X.1} {Subsection Title}

1. {Instruction}. From {location}, select the **{exact UI element name}**.

    ![{Descriptive alt text}](./assets/{step-N-annotated}.png)

1. {Next instruction}. The **{pane/dialog name}** will {appear/load}. Select **{element}**

    ![{Alt text}](./assets/{step-N-annotated}.png)

1. {For copy/paste steps:} Copy and paste the following as the **{field name}**,

    ```text
    {exact value to paste}
    ```

1. {For verification steps:} You should now see {description of expected state}.

    ![{Alt text}](./assets/{step-N-annotated}.png)

    > [!TIP]
    > {Helpful observation about what just happened or what to look for}

### {X.2} {Next Subsection Title}

1. {Continue steps...}

## ✅ Mission Complete {#mission-complete}

🎉 {Congratulatory message with personality — "Agent Maker, you've successfully packed
your digital briefcase!"}

You have successfully:
- ✅ {Accomplishment 1}
- ✅ {Accomplishment 2}
- ✅ {Accomplishment 3}

### Next Steps

{Suggest what comes next — "In the next mission, you'll learn to..."}
```

**Critical style rules from real Agent Academy labs:**
- Use `1.` for ALL numbered steps (VitePress auto-numbers them)
- Screenshots are indented with 4 spaces under their step
- Use `{#slug-anchor}` heading IDs on all `##` headings
- Include `<mission-meta />` component right after the H1
- Use `::: warning` blocks (not `> [!WARNING]`) for prerequisite warnings
- Use `> [!NOTE]` and `> [!TIP]` for non-critical callouts
- Tables for listing field values or properties
- Asset filenames follow the pattern: `{section}_{subsection}_{sequence}_{Description}.png`
- Copy/paste instructions use the phrasing: "Copy and paste the following as the **{field}**,"
- Navigation instructions use: "From {location}, select the **{element}**"
- Pane/dialog appearance: "The **{name}** will appear/load"

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

Match the Agent Academy voice EXACTLY. Study existing labs in `microsoft/agent-academy`
for tone. Key rules:

### Voice and tone
- **Spy/mission theme** — learners are agents on missions, not students in a class
- **Friendly and encouraging** — "Let's begin!", "Agent Maker, welcome to..."
- **Light emoji use** — 🤓 🪄 🎉 sparingly for personality, never in step instructions
- **Active voice** — "Select the **New** button" not "The New button should be selected"

### Step instruction format
- **One action per numbered step** — NEVER combine "click X and then type Y"
- **Bold the exact UI text** — `**New solution**` not "the new solution button"
- **Start with location context** — "From the left navigation, select..." or "In the **Properties** pane, enter..."
- **Describe the result** — "The **Solution Explorer** will load" after a navigation step
- **Use "select" not "click"** — Agent Academy convention
- **Use "copy and paste the following as the **{field}**," pattern** for text entry

### Screenshots
- **Every action step gets a screenshot** — show the state AFTER the action
- **Always use annotated versions** — red box around the target element
- **4-space indent** under the step they belong to
- **Descriptive alt text** — `![Solution Explorer showing new solution](./assets/...)`
- **Asset naming**: `{section}_{subsection}_{sequence}_{Description}.png`
  (e.g., `4.1_01_Solutions.png`, `4.1_02_NewSolution.png`)

### Copy/paste blocks
- Always preceded by: "Copy and paste the following as the **{field name}**,"
- Use ` ```text ` fence (not ` ```bash ` or bare ` ``` `)
- One value per code block — don't combine multiple fields

### Structural rules
- Use `1.` for ALL numbered items (VitePress auto-increments)
- Tables for listing properties, security roles, or comparisons
- `::: warning` for critical prerequisites (not `> [!WARNING]`)
- `> [!NOTE]` for contextual info, `> [!TIP]` for helpful hints
- Heading anchors on all `##` headings: `{#slug-anchor}`
- Conceptual section BEFORE the `🧪 Lab` hands-on section
- `<mission-meta />` component immediately after the H1 title

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for browser auth and
Playwright execution procedures.
