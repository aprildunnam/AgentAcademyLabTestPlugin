# Auto-cropped step screenshots Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `mcs-lab-builder` B4 capture loop frame each step screenshot to the key area (element-scoped crop) when that conveys the step, and keep a full-viewport shot when the whole screen is needed.

**Architecture:** This is a *skill-prose* change, not code. Two markdown skill files drive the builder's behavior: `build-session-spec.md` (the authoritative capture-loop pseudocode, ledger schema, and §screenshots rule) and `SKILL.md` (the human-facing B4 summary). We add a framing decision to the capture step (snapshot first → decide crop vs full → element-scoped or full `browser_take_screenshot`), extend the ledger `image:` record to persist the framing, and parameterize the existing `re-screenshot` override. A CHANGELOG entry records the change.

**Tech Stack:** Markdown skill definitions; Playwright MCP `browser_take_screenshot` (native `element` + `target` element-scoped capture); git on Windows (autocrlf=true, so adds may need `-c core.safecrlf=false`).

---

## File Structure

- `skills/mcs-lab-builder/references/build-session-spec.md` — authoritative source. Edits: capture-loop step 4 (reorder + framing branch), a new framing-decision subsection, the §screenshots framing note, and the ledger `image:` schema fields.
- `skills/mcs-lab-builder/SKILL.md` — the B4 summary that mirrors the spec. Edits: the CAPTURE line and the CONFIRM menu line. Must stay consistent with the spec file.
- `CHANGELOG.md` — add one entry under `## [Unreleased] → ### Added`.

No version-file bump: the repo accumulates changes under `## [Unreleased]` and bumps `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` only at release time (there are already unreleased changes on top of 0.8.0). Following that convention.

Verification note: there is **no automated test harness for skill prose** (`tests/` holds only `Test-ResolveLabInstance.ps1`). Each task's "verify" step is a `Grep`/`Read` consistency check. Final acceptance is a manual builder dry-run (Task 4) the user runs against a live browser — it cannot be run headless here.

---

## Task 1: Capture loop + framing decision in `build-session-spec.md`

**Files:**
- Modify: `skills/mcs-lab-builder/references/build-session-spec.md` (capture loop ~lines 77-79; §screenshots ~line 104; ledger `image:` ~lines 45-47)

- [ ] **Step 1: Reorder + branch the CAPTURE step (loop step 4)**

Find this block (currently lines 77-79):

```
  4. CAPTURE
     browser_take_screenshot(filename: "draft/images/<kebab>.png")          # naming rule in §screenshots
     browser_snapshot(filename: "snapshots/<step-id>-after.yml")
```

Replace it with (snapshot first — it is the source of element refs — then decide framing, then shoot):

```
  4. CAPTURE
     snap_after = browser_snapshot(filename: "snapshots/<step-id>-after.yml")
     framing    = decide_framing(intent, result, snap_after)    # crop | full  — see §framing
     if framing == crop:
        target_ref = tightest element in snap_after that encloses the action target AND a label/heading that identifies it
        browser_take_screenshot(element: <human description of target_ref>,
                                target:  target_ref,
                                filename: "draft/images/<kebab>.png")        # naming rule in §screenshots
     else:
        browser_take_screenshot(filename: "draft/images/<kebab>.png")        # full viewport
     # element-shot failure (stale/detached/zero-size ref) -> retry once as full viewport, record framing: full
```

- [ ] **Step 2: Add the §framing subsection**

Immediately BEFORE the line `## §screenshots — kebab naming rule` (currently line 104), insert:

```
## §framing — crop vs full screen (loop step 4)

`decide_framing` chooses how tightly to frame the step's screenshot. **Default to crop.**
Frame the tightest element in `snap_after` that encloses the action target together with a
label or heading that identifies it — so the crop is self-orienting, never a bare icon. Pass
that element's ref as `target` (and a human description as `element`) to
`browser_take_screenshot`; never pass `fullPage`.

Choose **full** (no `element`/`target`) instead when ANY of these hold:
- the step's meaning depends on *where* something sits in the overall layout (e.g. "the panel
  appears in the left rail");
- the learner must locate one control among many to follow the step;
- the result is a whole-page state — a freshly loaded page, a designer/canvas view;
- no single element encloses the key area without dropping context the learner needs.

Robustness: if the element-scoped shot fails (ref stale, detached, or zero-size), fall back to
a full-viewport shot automatically and record `framing: full`. A crop never blocks the loop.

```

- [ ] **Step 3: Add a framing note to §screenshots**

In the §screenshots section, after the line `- Apply the rule at capture time so the ledger's \`image.file\` and the on-disk file always agree.` (currently line 109), add a new bullet:

```
- The kebab naming rule is independent of framing (§framing): a cropped shot and a full shot are named the same way, from the step's action target.
```

- [ ] **Step 4: Extend the ledger `image:` schema**

Find the ledger `image:` block (currently lines 45-47):

```yaml
  image:
    file: "create-agent-button.png"       # lives in draft/images/, promoted to labs/<slug>/images/
    alt: "Create agent button"
```

Replace it with:

```yaml
  image:
    file: "create-agent-button.png"       # lives in draft/images/, promoted to labs/<slug>/images/
    alt: "Create agent button"
    framing: crop                          # crop | full  (see §framing) — how the shot was framed
    element_desc: "Create agent dialog"    # crop only: the element passed as browser_take_screenshot `element`
    element_ref: "e123"                    # crop only: the snap_after ref used as `target`, for redo/resume
```

- [ ] **Step 5: Verify the edits are consistent**

Run (Grep, output_mode content):
- Pattern `decide_framing` in `skills/mcs-lab-builder/references/build-session-spec.md` → expect 2 hits (capture loop + §framing reference).
- Pattern `## §framing` in the same file → expect 1 hit.
- Pattern `framing: crop` in the same file → expect 1 hit (the ledger example).
- Pattern `fullPage` in the same file → expect 0 hits.

Confirm the capture block now calls `browser_snapshot` before `browser_take_screenshot`.

- [ ] **Step 6: Commit**

```bash
git -c core.safecrlf=false add skills/mcs-lab-builder/references/build-session-spec.md
git commit -m "feat(builder): element-scoped step screenshots with full-screen fallback

Add a framing decision to the B4 capture loop (snapshot first, then crop to
the tightest self-orienting element or keep full viewport), a §framing rule,
and framing/element fields on the ledger image record.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Mirror the change in `SKILL.md` (B4 summary)

**Files:**
- Modify: `skills/mcs-lab-builder/SKILL.md` (CAPTURE line ~183; CONFIRM line ~186)

- [ ] **Step 1: Update the CAPTURE line**

Find (currently line 183):

```
  4. CAPTURE    browser_take_screenshot -> draft/images/<kebab>.png ; snapshot -> snapshots/<step-id>-after.yml
```

Replace with (snapshot first; crop vs full per §framing):

```
  4. CAPTURE    snapshot -> snapshots/<step-id>-after.yml ; then per build-session-spec §framing,
                crop to the tightest self-orienting element (browser_take_screenshot element+target)
                or shoot full viewport -> draft/images/<kebab>.png ; record framing in the ledger image record
```

- [ ] **Step 2: Update the CONFIRM menu line**

Find (currently line 186):

```
  6. CONFIRM    AskUserQuestion: confirm | redo-step | re-screenshot | edit-prose | split-step | end-scene | end-lab
```

Replace with:

```
  6. CONFIRM    AskUserQuestion: confirm | redo-step | re-screenshot (full / crop / adjust) | edit-prose | split-step | end-scene | end-lab
                  - re-screenshot full:   re-shoot full viewport
                  - re-screenshot crop:   re-run the automatic element pick (§framing)
                  - re-screenshot adjust: user names the region; map it to a snap_after ref and re-shoot
```

- [ ] **Step 3: Verify consistency between the two files**

Run (Grep, output_mode content):
- Pattern `re-screenshot \(full / crop / adjust\)` across `skills/mcs-lab-builder/` → expect hits in BOTH `SKILL.md` and (already added) — confirm `SKILL.md` matches the spec's intent.
- Pattern `§framing` in `skills/mcs-lab-builder/SKILL.md` → expect 1 hit.
- Read lines 183-190 of `SKILL.md` and confirm CAPTURE does snapshot before screenshot, matching `build-session-spec.md` step 4.

- [ ] **Step 4: Commit**

```bash
git -c core.safecrlf=false add skills/mcs-lab-builder/SKILL.md
git commit -m "docs(builder): mirror framing + re-screenshot override in B4 summary

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: CHANGELOG entry

**Files:**
- Modify: `CHANGELOG.md` (`## [Unreleased]` section, top of file ~line 7)

- [ ] **Step 1: Add an `### Added` entry under `## [Unreleased]`**

The `## [Unreleased]` section currently opens with `### Fixed`. Insert a new `### Added` block directly under the `## [Unreleased]` heading and ABOVE the existing `### Fixed` (Keep a Changelog orders Added before Fixed):

```markdown
### Added

- **`mcs-lab-builder` now crops step screenshots to the key area.** The B4 capture loop takes the after-snapshot first, then decides framing (`build-session-spec.md` §framing): it element-scopes `browser_take_screenshot` to the tightest self-orienting element when that conveys the step, and keeps a full-viewport shot when the whole screen is needed (layout/location context, a freshly loaded page, a designer canvas). The ledger `image:` record gains `framing` / `element_desc` / `element_ref`, and the CONFIRM step's `re-screenshot` option gains `full / crop / adjust` framing controls so the author can override any call. Auditor refresh and judge inspection shots are unchanged.
```

- [ ] **Step 2: Verify**

Run (Grep): pattern `### Added` in `CHANGELOG.md` → confirm the new block sits under `## [Unreleased]` and above `### Fixed` (Read the top ~20 lines to confirm ordering).

- [ ] **Step 3: Commit**

```bash
git -c core.safecrlf=false add CHANGELOG.md
git commit -m "docs: changelog entry for builder screenshot cropping

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Manual acceptance dry-run (user-run)

**Files:** none — this is a live verification, not an edit. It requires a browser + workshop account, so it is run by the user via `/build-lab`, not headless here.

- [ ] **Step 1: Crop case**

Start a builder session (`/build-lab`, guided mode). Drive a step that opens a **modal dialog**. Confirm:
- the saved `draft/images/<kebab>.png` is tightly framed on the dialog (not the full window);
- the ledger row records `framing: crop` with `element_desc` and `element_ref`.

- [ ] **Step 2: Full case**

Drive a step whose result is a **freshly loaded page**. Confirm the shot is full viewport and the ledger row records `framing: full` with no `element_desc`/`element_ref`.

- [ ] **Step 3: Override**

On any step, pick `re-screenshot → adjust`, name a different region, and confirm it re-shoots that region without advancing the step cursor. Repeat with `full` and `crop`.

- [ ] **Step 4: Regression**

Run `scripts/Test-ResolveLabInstance.ps1` (or the repo's test entrypoint) and confirm the existing PowerShell tests still pass — this change does not touch them.

---

## Self-Review

- **Spec coverage:** mechanism (element-scoped) → Task 1 Step 1; framing rule → Task 1 Step 2; capture reorder → Task 1 Step 1 + Task 2 Step 1; ledger metadata → Task 1 Step 4; CONFIRM override → Task 2 Step 2; builder-only scope → no auditor/cookbook files touched; verification → Task 4. All spec sections mapped.
- **Placeholder scan:** every edit step shows exact old→new text; no TBD/TODO. The one symbolic placeholder `<human description of target_ref>` / `target_ref` is intentional pseudocode in the skill prose (the model fills it at runtime from the snapshot), matching the file's existing pseudocode style (`<kebab>`, `<step-id>`).
- **Naming consistency:** `framing` / `element_desc` / `element_ref` / `decide_framing` / `§framing` used identically across Tasks 1–3.
- **Convention note:** version files deliberately not bumped (repo accumulates under `## [Unreleased]`); recorded in File Structure.
