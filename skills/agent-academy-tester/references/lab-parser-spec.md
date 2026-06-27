# Lab Parser Specification for Agent Academy

## Content source

Labs live in `microsoft/agent-academy` repo under `docs/<course>/<slug>/index.md`.

## Markdown structure

Agent Academy uses VitePress markdown. Each lab file has this structure:

```
---
(frontmatter with prev, next, difficulty, time, tags, etc.)
---
# 🚨 Mission XX: Title

<mission-meta />

## 🎯 Mission Brief
(intro paragraph)

## 🔎 Objectives
(bullet list of learning goals)

## (Conceptual sections - reading material, not interactive)

## 🧪 Lab XX: Title
### Prerequisites
(setup requirements)

### X.Y Step group heading
1. First interactive step with **bold UI elements**
   ![screenshot](./assets/image.png)
2. Second step...
   ```text
   Value to copy/paste
   ```

## ✅ Mission Complete
(congratulations text)

## 📚 Tactical Resources
(links to docs)
```

## Parsing algorithm

### Step 1: Identify interactive sections

Only content inside `## 🧪 Lab` sections (or sections starting with `###` under them)
contains interactive steps. Everything before the first `## 🧪 Lab` heading is
conceptual reading material — skip it.

### Step 2: Extract numbered steps

Within a lab section, numbered items (`1.`, `2.`, `3.`, etc.) are the interactive steps.
Each step may span multiple lines (continuation lines are indented).

### Step 3: Parse step components

Each step can contain:

- **Instruction text**: The plain text describing what to do
- **Bold elements** (`**text**`): UI elements to interact with (buttons, menus, labels)
- **Code blocks** (` ```text ... ``` `): Values to type or paste into fields
- **Images** (`![alt](./assets/file.png)`): Expected UI state for verification
- **Inline code** (`` `text` ``): Specific values, field names, or labels

### Step 4: Classify step action

Based on keywords in the instruction:

| Keywords | Action type |
|---|---|
| "navigate to", "go to", "open" + URL | navigate |
| "select", "click", "press", "choose" | click |
| "type", "enter", "paste", "copy and paste" | type |
| "from the dropdown", "select from" | select |
| "wait for", "wait until" | wait |
| "notice", "observe", "you'll see", "verify" | verify (no action, just check) |
| "toggle", "turn on/off", "enable/disable" | click (toggle control) |

### Step 5: Extract target elements

- **Click targets**: The bold text immediately following "click" / "select" / "press"
  Example: `Select **+ New solution**` → target = "+ New solution"
- **Type values**: Content in code blocks or quoted strings after "type" / "enter" / "paste"
  Example: `Copy and paste the following as the **Display name**: \`\`\`text\nContoso Solutions\n\`\`\`` → field = "Display name", value = "Contoso Solutions"
- **Navigation URLs**: URLs in the step text (not in images)

### Step 6: Build step tree

Output structure per lab:

```yaml
lab:
  course: "recruit"
  slug: "04-creating-a-solution"
  title: "Creating a Solution for Your Agent"
  sections:
    - heading: "4.1 Create a Solution publisher"
      steps:
        - index: 1
          instruction: "From the left navigation, select the ellipsis icon..."
          action: click
          target: "ellipsis icon"
          secondary_target: "Solutions"
          screenshot: "./assets/4.1_01_Solutions.png"
        - index: 2
          instruction: "The Solution Explorer will load. Select + New solution"
          action: click
          target: "+ New solution"
          screenshot: "./assets/4.1_02_NewSolution.png"
```

## Handling special cases

### Prerequisites section
- Steps in `### Prerequisites` are setup steps that must succeed before the lab
- They follow the same parsing rules as regular steps
- If a prerequisite references another lab's output, note it as a dependency

### Alert blocks
- `> [!TIP]` — helpful hint, not a step (skip)
- `> [!NOTE]` — informational, may provide alternative approaches
- `> [!WARNING]` / `> [!IMPORTANT]` — critical context that may affect step execution
- Attach alert blocks to the preceding step as metadata

### Multi-line steps
- A numbered step continues until the next numbered step or heading
- Indented content under a step number is part of that step
- Tables within steps describe field values to enter

### Non-interactive labs
- Labs where `interactive: false` in the config have no `## 🧪 Lab` section
- They are conceptual reading material — skip them entirely
