# Lab registration spec

How `mcs-lab-builder` (B6) and `mcs-lab-new-lab-pr` (B7) register a new lab in the mcs-labs repo. Covers runtime mechanism detection, the entry shapes, the order-number rule, optional event attachment, and screenshot promotion.

> ⚠️ **The documented toolchain has drifted.** `docs/NEW_LAB_CHECKLIST.md` describes editing a root `lab-config.yml` and running `scripts/Generate-Labs.ps1`. As of this writing **neither file exists** in the mcs-labs repo (feature branch or `origin/main`) — only the generated `_data/lab-config.yml` remains, with a now-stale "AUTO-GENERATED — DO NOT EDIT" header. So registration must be **detected at runtime**, and the realistic path is direct writes. Always re-detect; never assume.

## §1 — Mechanism detection (B0 step 5)

Within the resolved `mcs_labs_repo`:
1. Glob for a root `lab-config.yml` (config `build.registration.root_config_relpath`) and a generator (config `build.registration.generate_script_relpath`, default `scripts/Generate-Labs.ps1`).
2. Decide the mode:
   - **`generate`** — both the root config and the generator exist. Edit the root config + run the generator; commit its output.
   - **`direct`** — neither exists (current reality). Write `_data/lab-config.yml` entries and `_labs/<slug>.md` directly. This matches the existing `mcs-lab-fix-pr-filer`, which already edits `_labs/<slug>.md` in place.
   - **`ambiguous`** — exactly one exists, or the generator errors. Record it; at B6, surface via `AskUserQuestion` (run generator anyway / direct write / halt-and-let-maintainer-register).
3. Record `manifest.registration_mode`. On any unrecoverable ambiguity, prefer halting with guidance — the draft is safe under `runtime/builds/<build-id>/draft/`, so no work is lost.

## §2 — Order number

Labs join across the `_data/lab-config.yml` maps by a numeric **order** key (the key under `lab_metadata:`). Pick one in the band for the lab's `section` (from `docs/NEW_LAB_CHECKLIST.md`):

| Range | Section |
|-------|---------|
| 100–199 | core |
| 200–299 | intermediate |
| 300–399 | advanced |
| 400–499 | specialized |
| 500–599 | optional |
| 600–699 | external |

`order_gap_strategy: section_midpoint` — choose a free number midway between the two nearest existing order keys in the chosen section (e.g. existing 220 and 230 → pick 225). It must not already be a key under `lab_metadata:`. Surface the chosen number for confirmation in B3.

## §3 — `generate` mode (if the toolchain returns)

1. Add ONE entry to the root `lab-config.yml` `labs:` section:
   ```yaml
   <slug>:
     title: "<Title>"
     difficulty: "<Beginner|Intermediate|Advanced>"
     duration: <minutes>
     section: <core|intermediate|advanced|specialized|optional>
     order: <number>
     journeys: [<journey>, ...]
     events: [<event>, ...]        # ONLY if attaching; omit for standalone
   ```
2. Run the generator: `pwsh -NoProfile -File <repo>/scripts/Generate-Labs.ps1 -SkipPDFs` (args from `build.registration.generate_args`).
3. Commit the generated `_labs/<slug>.md` + `_data/lab-config.yml` alongside the root config edit.

## §4 — `direct` mode (current reality)

Replicate what the generator would have produced. In `_data/lab-config.yml`:

1. **`lab_metadata.<order>`** (keyed by the numeric order from §2):
   ```yaml
   <order>:
     difficulty: <Beginner|Intermediate|Advanced>
     duration: <minutes>
     id: <slug>
     section: <core|intermediate|advanced|specialized|optional>
     title: <Title>
   ```
2. **`lab_journeys.<slug>`**: `[<journey>, ...]`.
3. **`lab_orders.section.<section>`**: insert `<order>` in ascending position.
4. **`lab_orders.journey.<journey>`**: insert `<order>` for each journey.
5. **Event attachment (optional)** — for each event in `manifest.events`: add `<order>` to `lab_orders.event.<event>` and to the `<event>_lab_orders` map (matching that map's existing key style — numbered `n: <slug>` for `bootcamp_lab_orders`, or a flat `<order>` list for the others). **Standalone is the default; skip this when `events` is empty.**

Then write **`_labs/<slug>.md`** directly — frontmatter modeled on a sibling (`_labs/agent-builder-web.md`), followed by the assembled README body:
```yaml
---
title: "<Title>"
description: "<one-line description>"
order: <small per-section sequence number — mirror a sibling in the same section>
duration: <minutes>
difficulty: <100|200|300>          # numeric tier, not the word
section: <core_learning_path|intermediate_labs|advanced_labs|...>   # the *_learning_path/_labs form
journeys: ["<journey>", ...]
# event-order keys ONLY if attached, mirroring siblings:
# bootcamp_order: "<n>"
# mcs_in_a_day_order: "<n>"
---

---

<README body assembled in B5>
```
Map the human `section` (`core`) to the frontmatter form (`core_learning_path`) by copying a sibling in the same section. When unsure about a derived field's exact value, **read the nearest sibling in the same section and mirror it** rather than inventing.

## §5 — Lab folder + screenshot promotion (both modes)

- `labs/<slug>/README.md` — the source README from `draft/README.md`.
- `labs/<slug>/images/<file>.png` — same-name copy of every `draft/images/*.png`. The README references `images/<file>`, so no path rewrite is needed.

## §6 — Verification

After registration (B6), confirm the lab parses: the auditor's `lab-parser-spec.md` should read `_labs/<slug>.md` into a step tree with the expected use cases/scenes. If parsing fails or the Lab Details `Duration` disagrees with the registered `duration`, fix before proceeding to the gate run. In `generate` mode you can additionally run `tools/run.ps1` (Jekyll dev server) to eyeball the rendered page, but that is optional and not required for the PR.
