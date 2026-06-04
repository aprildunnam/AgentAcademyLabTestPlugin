# Lab authoring template

The canonical structure a built lab's `labs/<slug>/README.md` must match so it reads like a sibling lab. Modeled on existing labs (e.g. `labs/agent-builder-web/README.md`). B5 renders the ledger into this skeleton; the orchestrator generates the prose context sections from the scenario + ledger.

## Conventions

- **Source of truth is `labs/<slug>/README.md`** (no Jekyll frontmatter in the source README — frontmatter lives in the generated/`_labs/<slug>.md` file). Section headers carry the same emoji prefixes as siblings.
- **Callouts** use GitHub alert syntax: `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!NOTE]`. Images inside a callout are indented one level (`>   ![alt](images/x.png)`).
- **Screenshots** are referenced relative to the lab folder: `![Descriptive alt](images/<kebab>.png)`.
- **Pasteable content** (prompts, URLs, test queries) goes in a fenced code block directly under its step.
- **Horizontal rules** (`---`) separate major sections, exactly as siblings do.

## Skeleton

```markdown
# <Lab Title>

<One-sentence description of what the learner builds.>

---

## 🧭 Lab Details

| Level | Persona | Duration | Purpose |
| ----- | ------- | -------- | ------- |
| <100/200/300> | <Persona> | <N> minutes | After completing this lab, attendees will be able to <outcome>. |

---

## 📚 Table of Contents

- [Introduction](#-introduction)
- [Core Concepts Overview](#-core-concepts-overview)
- [Documentation and Additional Training Links](#-documentation-and-additional-training-links)
- [Prerequisites](#-prerequisites)
- [Summary of Targets](#-summary-of-targets)
- [Use Cases Covered](#-use-cases-covered)
- [Instructions by Use Case](#️-instructions-by-use-case)
  - [Use Case #1: <title>](#-use-case-1-<anchor>)
- [Summary of Learnings](#-summary-of-learnings)
- [Conclusions & Recommendations](#-conclusions--recommendations)

---

## 🌐 Introduction

<2–4 sentences: the real-world problem this lab addresses and what the learner will build.>

---

## 🎓 Core Concepts Overview

| Concept | Why it matters |
|---------|----------------|
| **<Concept>** | <One-line explanation.> |

---

## 📄 Documentation and Additional Training Links

* [<Title>](<url>)

---

## ✅ Prerequisites

- <Prerequisite>

---

## 🎯 Summary of Targets

By the end of the lab, <the learner / your agent> will be able to:

- <Target>

---

## 🧩 Use Cases Covered

| Step | Use Case | Value added | Effort |
|------|----------|-------------|--------|
| 1 | [<UC title>](#-use-case-1-<anchor>) | <value> | <N> min |

---

## 🛠️ Instructions by Use Case

---

## 🤖 Use Case #1: <title>

<One-line summary of the use case.>

**Summary of tasks**

In this section, you'll <tasks>.

**Scenario:** <realistic business context>

### Objective

<Clear, specific objective.>

---

### Step-by-step instructions

#### <Scene heading>

1. <Numbered step, UI labels in **bold**.>

   ```
   <optional pasteable content>
   ```

   > [!TIP]
   > <inline guidance>

   ![<alt>](images/<kebab>.png)

2. <Next step.>

---

### 🏅 Congratulations! <closing line for the use case.>

---

## 🔁 Summary of Learnings

<Reflection bullets reinforcing the key concepts.>

---

## 📌 Conclusions & Recommendations

> [!IMPORTANT]
> <Closing recommendations.>
```

## Notes for the generator

- Use exactly one `## 🤖 Use Case #N:` block per use case in the ledger; number scenes' steps with a single running counter across the whole lab (matching siblings, where step numbers don't reset per scene).
- The Use Cases Covered table's anchor must match the GitHub-generated anchor for the `## 🤖 Use Case #N: <title>` heading (lowercased, spaces→hyphens, punctuation dropped, leading emoji becomes a leading hyphen — verify against a sibling).
- Keep the Lab Details `Duration` consistent with the registration `duration` (the parser flags a mismatch).
- Generated prose should be specific to the scenario — avoid filler. Pull concept names and artifact names from the ledger's `variables_set`.
