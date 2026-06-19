# Design: Auto-cropped step screenshots in `mcs-lab-builder`

Date: 2026-06-19
Status: Approved (brainstorming) — pending implementation plan

## Goal

When the builder captures a screenshot for a lab step, frame it to the **key area** a
learner needs to understand that step — typically the dialog, panel, card, or control
group the action produced — instead of always shooting the full viewport. When the
step's meaning genuinely needs the whole screen (layout/location context, a freshly
loaded page, a designer canvas), keep it full. The author stays in control via the
existing confirm loop.

## Scope

- **In scope:** the `mcs-lab-builder` B4 per-step capture loop only.
- **Out of scope (unchanged):**
  - The auditor's stale-screenshot refresh flow — replacements must match the framing
    of the existing screenshots already in that lab.
  - The judge's inspection screenshots (`browser_snapshot` + `browser_take_screenshot`
    captured "for the judge" per the shared playwright-cookbook).
  - Multi-region / pixel bounding-box crops and any image-processing dependency
    (PIL/ImageMagick). YAGNI.

## Mechanism

Use Playwright's **native element-scoped screenshot** — no image-processing tooling and
no pixel math:

- **Crop:** `browser_take_screenshot(element: "<description>", target: <ref>, filename: …)`
  — captures just that element.
- **Full:** `browser_take_screenshot(filename: …)` — current behavior, no `element`/`target`.

`element` (human-readable description) and `target` (the exact snapshot ref) cannot be
combined with `fullPage`; we never use `fullPage` in the builder.

## The framing decision (per step, automatic)

Default to a **crop**. After EXECUTE, pick the **tightest snapshot element that encloses
the action target *and* a label/heading that identifies it**, so the crop is
self-orienting (never a bare icon).

Choose **full screen** instead when any of these hold:

- The step's meaning depends on *where* something sits in the overall layout
  (e.g. "the panel appears in the left rail").
- The learner must locate one control among many to follow the step.
- The result is a whole-page state — a newly loaded page, a designer/canvas view.
- No single element encloses the key area without dropping needed context.

## Capture-loop changes (B4 — `build-session-spec.md` §capture-loop + `SKILL.md` B4)

Reorder step 4 so the snapshot (the source of refs) is taken first, then framing is
decided from it, then the screenshot is shot:

```
4. CAPTURE
   snap_after = browser_snapshot("snapshots/<step-id>-after.yml")
   framing    = decide_framing(intent, result, snap_after)   # crop | full  (rule above)
   if framing == crop:
        target_ref = tightest enclosing element from snap_after
        browser_take_screenshot(element: <desc>, target: target_ref,
                                filename: "draft/images/<kebab>.png")
   else:
        browser_take_screenshot(filename: "draft/images/<kebab>.png")   # full
```

**Robustness:** if the element shot fails (stale / detached / zero-size ref), fall back
to a full-viewport shot automatically and record `framing: full` with the reason. A crop
never blocks the loop.

The kebab naming rule (§screenshots) is unchanged — it is derived from the step's action
target and applies regardless of framing.

## Ledger metadata (`build-session-spec.md` step-record `image:` block)

Extend the `image:` block so resume and re-screenshot are deterministic:

```yaml
image:
  file: "create-agent-button.png"
  framing: crop                         # crop | full
  element_desc: "Create agent dialog"   # crop only — what was framed
  element_ref: "e123"                   # crop only — ref used, for redo/resume
```

`framing: full` rows omit `element_desc` / `element_ref`. Confirmed rows and their
on-disk screenshots are preserved across `--resume`, so the framing chosen for a
confirmed step survives a resume.

## CONFIRM override (B4 step 6)

The existing `re-screenshot` option becomes parameterized — no new mandatory prompt is
added to the happy path:

```
confirm | redo-step | re-screenshot (full / crop / adjust) | edit-prose | split-step | end-scene | end-lab
```

- **full** — re-shoot full viewport.
- **crop** — re-run the automatic element pick.
- **adjust** — the author names the region ("just the dialog", "include the left nav");
  the model maps it to a snapshot ref and re-shoots.

Selecting any re-screenshot variant loops back without advancing the step cursor, exactly
as today.

## Files touched

- `skills/mcs-lab-builder/references/build-session-spec.md` — §capture-loop step 4
  (reorder + framing decision), §screenshots (framing note), step-record `image:` schema.
- `skills/mcs-lab-builder/SKILL.md` — B4 CAPTURE line and the CONFIRM menu.
- `CHANGELOG.md` + plugin version bump per the repo's release convention.

## Verification

No skill-prose test harness exists (the `tests/` directory holds PowerShell unit tests
for the lab-resolver script only), so acceptance is a **manual builder dry-run**:

1. Capture a step that should crop (a modal dialog) → confirm the shot is element-scoped
   and the ledger records `framing: crop` with `element_desc` / `element_ref`.
2. Capture a step that should stay full (a freshly loaded page) → confirm `framing: full`
   and no element fields.
3. Exercise the `re-screenshot (full / crop / adjust)` override and confirm it re-shoots
   without advancing the cursor.
4. Existing PowerShell tests still pass (unaffected by this change).
