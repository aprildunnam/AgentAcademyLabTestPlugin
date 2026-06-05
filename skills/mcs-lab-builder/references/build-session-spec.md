# Build-session spec

Operational detail for `mcs-lab-builder` phases B3–B5: the build workspace, the step ledger, the per-step capture loop, the kebab screenshot-naming rule, the ledger→README renderer, and resume semantics. The orchestrator loads this when it reaches B3.

## Workspace layout

A build uses `runtime/builds/<build-id>/`, mirroring the auditor's `runtime/runs/<run-id>/`. `runtime/` is gitignored at the plugin repo root — nothing here is committed.

```
runtime/builds/<build-id>/
  manifest.yml         # build_id, slug, mode (guided|scenario), account user_id, mcs_labs_repo,
                       #   registration_mode (generate|direct|ambiguous), lab meta
                       #   (title/difficulty/duration/section/journeys/order), events[],
                       #   proposal_issue {number,url,status,labels}, phase cursor, status
  session-state.yml    # RESUME cursor (see §resume)
  ledger.yml           # ordered list of CONFIRMED step records — the source of truth for B5
  draft/
    README.md          # assembled lab (rewritten on every B5; may be partial during B4)
    images/            # screenshots captured during B4 (kebab-named, see §screenshots)
  proposal-issue.md    # rendered B3.5 issue body (type: new-lab + status: in-progress)
  snapshots/           # <step-id>-before.yml / -after.yml (context-saver; never shipped)
  audit/
    findings.json      # B6 gate findings, consumed in-loop (NOT routed to any issue-filer)
  pr-body.md           # rendered at B7
  pr-url.txt           # B7 output
```

`build_id` is generated like the auditor's run id: `(Get-Date -Format "yyyy-MM-ddTHHmmZ") + "-" + 4 hex chars`.

## Step ledger (`ledger.yml`)

One entry per confirmed step. Field shape is chosen to map cleanly onto both the README markdown and the auditor's parser step model (`lab-parser-spec.md` id grammar), so B5 rendering and B6 parsing line up.

```yaml
- step_id: usecase-1.scene-2.step-3      # same grammar as lab-parser-spec.md
  uc_id: usecase-1
  uc_title: "Use Case #1: Build a returns-triage assistant"
  scene_heading: "Create your agent"      # the #### heading this step lives under
  ordinal: 3                              # 1-based number within the lab's running step count
  kind: click | type | navigate | wait | select | assert_visible | inspect | narrative
  instruction_md: "Select **Create** in the top-right."   # the numbered-step prose
  hints:                                  # rendered as > [!KIND] callouts under the step
    - { kind: TIP, text: "If you don't see Create, refresh with Ctrl+F5." }
  code_block: null                        # optional fenced block to paste (prompts, URLs) shown under the step
  image:
    file: "create-agent-button.png"       # lives in draft/images/, promoted to labs/<slug>/images/
    alt: "Create agent button"
  evidence:
    snapshot_after: "snapshots/usecase-1.scene-2.step-3-after.yml"
  variables_set: { agent_name: "Returns Triage" }   # artifact names later steps/prose can reference
  confirmed_at: <iso>
```

## Capture loop (B4)

Both interaction modes share this loop; they differ only at step 2 (who originates the step). **Every step is confirmed before checkpoint — never batch a scene.**

```
# preconditions: signed in, on Copilot Studio Home (B2 done); workspace exists; current_uc + current_scene chosen.
loop:
  1. SNAPSHOT
     snap_before = browser_snapshot(filename: "snapshots/<step-id>-before.yml")

  2. INTENT
     if mode == guided:
        ask (AskUserQuestion free-text): "What's the next step? Name the control to use and any key
           consideration/tip the learner needs." -> intent = user_dictation
     else:  # scenario
        proposal = propose_next_step(scenario, ledger_so_far, snap_before)   # see §propose
        ask the user to confirm/adjust the proposal BEFORE executing -> intent = confirmed_proposal

  3. EXECUTE  (playwright-cookbook §tool-mapping; snapshot refs only, never raw CSS)
     navigate / click / type / fill_form / select_option / press_key / wait_for per the intent.
     connection-class failures -> judge-config execution.network_retry_count, then pause + AskUserQuestion.
     un-completable -> recovery menu (manual-by-user / reword / split / skip-with-NOTE / abort). never silently skip.

  4. CAPTURE
     browser_take_screenshot(filename: "draft/images/<kebab>.png")          # naming rule in §screenshots
     browser_snapshot(filename: "snapshots/<step-id>-after.yml")

  5. WRITE
     instruction_md = render_step_markdown(intent, result, snap_after)       # see §render-step

  6. CONFIRM
     AskUserQuestion: confirm | redo-step | re-screenshot | edit-prose | split-step | end-scene | end-lab
       - show the rendered markdown + the screenshot path + "did the UI do what you intended?"

  7. CHECKPOINT
     on confirm:        append step record to ledger.yml; write session-state.yml (advance cursor)
     on redo/...:       loop back to the relevant sub-step WITHOUT advancing
     on end-scene:      close current scene; ask next scene heading OR end-use-case (then ask next UC title)
     on end-lab:        break to B5
```

### §render-step — `render_step_markdown`
Produce exactly one numbered list item:
- The instruction sentence(s) in imperative voice, UI labels **bold** (`**Create**`), matching sibling-lab tone.
- Any `code_block` as a fenced block directly under the step (prompts/URLs the learner pastes).
- Each `hints[]` entry as a GitHub callout: `> [!TIP]` / `> [!IMPORTANT]` / `> [!WARNING]` / `> [!NOTE]`, with the image (if any) embedded inside the callout when it illustrates the hint, else one paragraph below the step as `![alt](images/<file>)`.

### §propose — `propose_next_step` (scenario mode)
From the scenario captured in B3, the ledger so far, and `snap_before`, infer the single most likely next action a learner would take to advance the scenario, grounded in the controls actually visible in `snap_before`. Propose ONE step only (control + intent + a candidate tip). Present it for confirmation before executing — the user can accept, adjust, or replace it. Never chain multiple steps without confirmation.

## §screenshots — kebab naming rule

At capture time (loop step 4), derive the filename from the step's primary action target:
- lowercase; non-alphanumerics → single hyphens; trim leading/trailing hyphens.
- On collision with an existing `draft/images/*` name, append `-2`, `-3`, … .
- Apply the rule at capture time so the ledger's `image.file` and the on-disk file always agree.

Examples: "Create agent button" → `create-agent-button.png`; a second shot of the same surface → `create-agent-button-2.png`.

Promotion to the repo (B6/B7) is a same-name copy `draft/images/*` → `labs/<slug>/images/`; because the README already references `images/<file>`, no rewrite is needed.

## Ledger → README renderer (B5)

Walk `ledger.yml` grouped by `uc_id` → `scene_heading` → `ordinal` and emit the Instructions-by-Use-Case body; then prepend the context sections from `lab-authoring-template.md`. Structure (sibling order):

1. `# <Title>` + one-line description.
2. `## 🧭 Lab Details` table (Level / Persona / Duration / Purpose) from B3 metadata.
3. `## 📚 Table of Contents` (anchors to the sections + each `### Use Case #N`).
4. `## 🌐 Introduction`, `## 🎓 Core Concepts Overview` (table), `## 📄 Documentation and Additional Training Links`, `## ✅ Prerequisites`, `## 🎯 Summary of Targets` — generated from the scenario + ledger artifacts.
5. `## 🧩 Use Cases Covered` table — auto-built from the UC list (Step # / Use Case (anchor) / Value added / Effort).
6. `## 🛠️ Instructions by Use Case` → per UC: `## 🤖 Use Case #N: <title>`, a short summary, `**Scenario:**`, `### Objective`, then `### Step-by-step instructions` containing the `#### <scene_heading>` blocks with their numbered steps (rendered per §render-step).
7. `## 🔁 Summary of Learnings`, `## 📌 Conclusions & Recommendations` — generated.

After rendering, show the README to the user for a read-through and accept edits before B6.

## §resume — `session-state.yml`

```yaml
phase_cursor: B4
current_uc: usecase-2
current_scene: "Add a knowledge source"
last_confirmed_step_id: usecase-2.scene-1.step-7
browser_left_at:
  url: "https://copilotstudio.microsoft.com/environments/.../agents/..."
  scene: "Add a knowledge source"
pending_decision: null     # set if a step was mid-confirmation when interrupted
```

`--resume <build-id>` re-runs B0 + B1-account + B2 (idempotent Welcome handler, navigate to `browser_left_at.url`), then resumes B4 at `last_confirmed_step_id + 1` in `current_uc`/`current_scene`. Confirmed `ledger.yml` steps and their on-disk screenshots are preserved.

## `build:` config defaults (used if `judge-config.yml.build` is absent)

```yaml
build:
  interaction_mode_default: prompt        # prompt | guided | scenario
  proposal_issue:
    enabled: true
    repo: "microsoft/mcs-labs"
    labels: ["type: new-lab", "status: in-progress"]   # existing repo labels (do not invent)
    title_pattern: "New lab proposal: {title} ({slug})"
    link_pr_with: "Closes"                 # Closes | Refs — how the B7 PR references the issue
  audit_gate:
    enabled: true
    fail_on: [broken, unclear]
    max_loops: 5
    suppress_github_writes: true
  screenshot:
    image_name_strategy: kebab_from_target
  registration:
    mcs_labs_repo_path_candidates:
      - "C:\\Users\\dewainr\\Projects\\mcs-labs"
      - "C:\\Users\\dewainr\\mcs-labs"
    root_config_relpath: "lab-config.yml"
    data_config_relpath: "_data/lab-config.yml"
    generate_script_relpath: "scripts/Generate-Labs.ps1"
    generate_args: ["-SkipPDFs"]
    order_gap_strategy: section_midpoint
  issues:
    new_lab_pr:
      pr_branch_pattern: "dewain/new-lab-{slug}-{build_id}"
      require_same_author: true
```
