# Lab markdown → executable step tree

This document defines the grammar the primary skill uses to convert an mcs-labs `_labs/<slug>.md` file into a structured step tree (`steps.json`).

## Output shape

```json
{
  "lab_slug": "core-concepts-analytics-evaluations",
  "lab_title": "Monitor Performance and Evaluate Agent Quality",
  "front_matter": { "...": "..." },
  "context": {
    "why_this_matters": "...",
    "introduction": "...",
    "core_concepts": [{ "name": "...", "description": "..." }],
    "prerequisites": ["...", "..."],
    "summary_of_targets": ["...", "..."]
  },
  "use_cases": [
    {
      "id": "usecase-1",
      "title": "Use Case #1: Monitor Agent Performance with Analytics",
      "objective": "...",
      "scenes": [
        {
          "id": "usecase-1.scene-1",
          "heading": "Navigate to Analytics",
          "non_deterministic": false,
          "steps": [
            {
              "id": "usecase-1.scene-1.step-1",
              "ordinal": 1,
              "raw_markdown": "Go to Copilot Studio and select **Agents** on the left navigation. Open your Copilot Studio Assistant agent and select **Analytics** in the top navigation bar.",
              "kind": "navigate",
              "kind_confidence": 0.91,
              "hints": [],
              "sub_bullets": [],
              "expected_visual_refs": [],
              "non_deterministic": false,
              "variables_set": {},
              "variables_used": []
            }
          ]
        }
      ]
    }
  ],
  "executable_step_count": 47
}
```

## Parsing rules

### 1. Front-matter

Strip everything between the first `---` line and the next `---` line at the start of the file. Parse as YAML into `front_matter`. Skip a second `---` line if present immediately after (some labs have a doubled front-matter separator).

### 2. Section identification

Walk h2 (`## …`) headings. Map them to context buckets:

| Heading | Context bucket |
|---|---|
| `Why This Matters` | `context.why_this_matters` |
| `Introduction` | `context.introduction` |
| `Core Concepts Overview` | `context.core_concepts` (parse the table) |
| `Documentation and Additional Training Links` | discarded (not relevant to step execution) |
| `Prerequisites` | `context.prerequisites` (each bullet → one entry) |
| `Summary of Targets` | `context.summary_of_targets` (each bullet → one entry) |
| `Use Cases Covered` | discarded (duplicated by the use-case headings under "Instructions by Use Case") |
| `Instructions by Use Case` | the **executable** content — parse per §3 |

Anything outside these is ignored.

### 3. Use cases → scenes → steps

Inside `## Instructions by Use Case`, the tree is:

```
### Use Case #N: <title>           ← h3 = use case
   (intro paragraph)
   **Scenario:** …                  ← optional flavor text, attached as context
   ### Objective                    ← h3 sub-section — body becomes use_case.objective
   ### Step-by-step instructions    ← h3 marker; content below is executable scenes
      #### <Scene heading>          ← h4 = scene (resumable boundary)
         1. <step text>             ← numbered list = candidate executable step
         1. <step text>
            - sub-bullet            ← merged into parent step.sub_bullets
            > [!TIP] …              ← alert attached to step.hints
         1. <step text>
      #### <Next Scene>
         ...
```

Note: **all numbered items use `1.`** — markdown renders them sequentially. Compute `ordinal` by counting position in the parent scene's numbered-list run, not by reading the numeric value.

### 4. Step kind classification

For each step, run a heuristic classifier against `raw_markdown`. Patterns are evaluated in order; the first match wins.

| Kind | Match pattern (case-insensitive unless noted) | Notes |
|---|---|---|
| `navigate` | starts with `go to`, `navigate to`, `open`, `browse to`, contains a full URL on its own | First step of any scene is often this |
| `click` | contains `click`, `select` (when followed by a `**bold**` token), `choose`, `press` |
| `type` | contains `type`, `enter`, `paste`, `name the … as`, `fill in` |
| `select` | contains `select` + a dropdown/option phrase (`from the dropdown`, `option`) | falls through to `click` if ambiguous |
| `wait` | `wait for`, `wait until`, `you should see` (when no action verb) |
| `assert_visible` | `verify that`, `confirm that`, `you will see`, `the page shows` |
| `inspect` | `review`, `notice`, `observe`, `examine` (no action verb) |
| `narrative` | step contains no actionable verb and reads as commentary |

If the classifier's confidence is < 0.7, escalate to a fast LLM call passing the step text + parent scene heading. The LLM returns one of the same kinds.

### 5. Alert block attachment

Alert blocks like `> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]` are attached to the **immediately preceding step** as `hints[]`. They can have leading whitespace (when nested inside a numbered list, e.g. `    > [!TIP]`). Strip the leading `>` and any indent; preserve the alert kind as `hints[N].kind` and the body text as `hints[N].text`.

If an alert appears before the first step of a scene, attach it to `scene.scene_hints[]` instead.

### 6. Sub-bullets

A `-` bullet (or `*` bullet) indented under a numbered step is merged into the parent step's `sub_bullets[]`. Sub-bullets describe what to look at or expected sub-outcomes — they are NEVER dispatched as separate clicks. They become judge context.

### 7. Image references

Markdown image refs `![alt](images/foo.png)` attach to the most recent step (or scene if before any step) as `expected_visual_refs[]`. The plugin does NOT pixel-diff against these — they are semantic hints describing what the UI should roughly look like. Track them so the judge can reference them ("the screenshot in the lab shows a button labeled X in the top-right; do you see that?").

### 8. Non-determinism flagging

Mark `non_deterministic: true` on a step (or whole scene if every step in it matches) when ANY of:

- Regex against `raw_markdown`: `/may differ|may vary|will be different|might look different|your .* (might|may) look|the exact (output|wording|response) (will|may)/i`
- The scene heading contains `Agent Builder`, `Researcher`, `Multi[- ]?Agent`, `Generated answer`, or `Generative answer`.
- The lab's slug is in `config/judge-config.yml.non_deterministic_lab_slugs[]` (in which case ALL scenes are non-deterministic by default).

The judge prompt for non-deterministic steps uses a softer rubric — it asks "is the right *kind* of thing visible?" rather than "does the UI match exactly?".

### 9. Variable extraction

Some steps name an artifact the user will create that later steps refer to. Detect:

- `name the (agent|topic|knowledge source|tool|environment|solution) **<value>**` → `ctx.vars.<role> = <value>`
- `with name **<value>**`, `called **<value>**`, `as **<value>**`
- Quoted strings after the verb `name`, `call`, `title`, `label`

Later steps that reference `your <value>` or the literal value should record `variables_used: ["<role>"]`. This is best-effort; if the judge sees an unexpected name in the UI it can still pass if the meaning matches.

### 10. Step IDs

Stable, hierarchical, deterministic: `{usecase-id}.{scene-id}.step-{ordinal}`. Scene IDs are `scene-N` where N is the scene's position within the use case. Stable across runs of the parser as long as the lab content doesn't change.

### 11. Lab Resources link detection

Some labs reference a per-event SharePoint **Lab Resources** page that hosts configuration values (URLs, connector credentials, instance hostnames) the lab assumes the user can read at run time. Detect those references and surface them as lab-level metadata — they are NOT executable steps but the orchestrator's Phase 1.6 needs to know they exist.

During the link walk, capture the first URL matching any of:

- `copilotstudiotraining.sharepoint.com/sites/Workshop/SitePages/Lab-Assets.aspx`
- `*.sharepoint.com/sites/*/SitePages/Lab*Assets.aspx`
- Any link whose **link text** matches `/Lab Resources/i` or `/Lab Assets/i`

Store on the parsed lab as:

```json
{
  "lab_slug": "mcs-alm",
  "lab_metadata": {
    "lab_resources_url": "https://copilotstudiotraining.sharepoint.com/sites/Workshop/SitePages/Lab-Assets.aspx"
  },
  ...
}
```

When unset (most labs), the orchestrator skips Phase 1.6. When set, Phase 1.6 (see `references/lab-resources-spec.md`) navigates there once and caches the parsed values to `runs/<run-id>/lab-resources.yml` for per-lab subagents to read.

## Important edge cases

- **Doubled `---` markers** (line 13–15 of `core-concepts-analytics-evaluations.md`): a single front-matter block followed by a `---` horizontal rule. Tolerate by only consuming the first front-matter block.
- **Inline `### Objective` and `### Step-by-step instructions`** are h3 children of the use-case h3, not separate use cases. Distinguish by content — use-case h3s match `^Use Case #\d+:`.
- **Anonymous scenes**: a use case's `### Step-by-step instructions` may have numbered steps directly under it with no `####` heading at all. In that case, create one synthetic scene `scene-1` with `heading: "(top-level steps)"`.
- **Numbered list resets**: blank lines and headings reset numbered-list state. Some labs put commentary paragraphs between numbered items expecting the renderer to continue numbering — handle by treating any `^\s*\d+\.` after a blank line as continuing the previous list IF no heading intervened.
- **Lone code blocks** (no surrounding numbered step): attach to the immediately preceding step's `code_blocks[]`. If none, attach to the scene.

## Validation

After parsing, run these sanity checks:

- Every executable step has a non-empty `raw_markdown`.
- `executable_step_count` matches the sum of step counts across all scenes.
- No two steps share an `id`.
- Every alert is attached either to a step or a scene.
- Every `variables_used` entry references a variable set earlier in the same lab (warn if not — likely a lab-typo finding).

Failed validation → emit a `parser_warning` finding (severity: low) and continue with best-effort execution.
