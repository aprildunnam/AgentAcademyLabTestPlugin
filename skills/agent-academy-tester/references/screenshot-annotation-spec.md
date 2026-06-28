# Screenshot Annotation & Fix PR Specification

## Overview

When a lab step fails (`broken` or `unclear` with confidence ≥ 0.7), the plugin:
1. Captures an annotated screenshot highlighting the problem
2. Captures a fresh "correct" screenshot showing the current UI state
3. Generates corrected markdown for the broken step(s)
4. Opens a fix PR on `microsoft/agent-academy` with the corrections

## Phase 5 — Annotated Screenshots

### When to annotate

Annotate a screenshot when:
- Verdict is `broken` and confidence ≥ 0.7
- Verdict is `unclear` and confidence ≥ 0.8
- The finding has both `expected` and `observed` values that differ

### Annotation procedure

For each finding that meets the threshold:

1. **Capture the current UI state** with `browser_take_screenshot`. This is the
   "actual" screenshot showing what the learner would see today.

2. **Generate an annotated screenshot** using `browser_evaluate` to inject a
   temporary overlay onto the page before screenshotting:

   ```javascript
   // Inject annotation overlay via browser_evaluate
   (function() {
     // Find the element the lab step references (or the area where it should be)
     const overlay = document.createElement('div');
     overlay.id = 'lab-test-annotation';
     overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:99999;pointer-events:none;';

     // Add a callout box with the finding details
     const callout = document.createElement('div');
     callout.style.cssText = 'position:fixed;bottom:20px;right:20px;background:#ff4444;color:white;padding:16px 20px;border-radius:8px;font-family:system-ui;font-size:14px;max-width:400px;z-index:100000;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
     callout.innerHTML = `
       <div style="font-weight:bold;margin-bottom:8px;">⚠️ Lab Step ${stepIndex} — ${verdict.toUpperCase()}</div>
       <div style="margin-bottom:6px;"><strong>Expected:</strong> ${expected}</div>
       <div><strong>Actual:</strong> ${observed}</div>
     `;
     overlay.appendChild(callout);
     document.body.appendChild(overlay);
   })();
   ```

3. **Take the annotated screenshot** with `browser_take_screenshot`.

4. **Remove the overlay** with `browser_evaluate`:
   ```javascript
   document.getElementById('lab-test-annotation')?.remove();
   ```

5. **If the lab step references a specific UI element** (button, menu item, etc.):
   - Use `browser_snapshot` to find the element's bounding box from the accessibility tree
   - Draw a red rectangle around where the element IS (or where it SHOULD be)
   - Add an arrow or label showing the discrepancy

### Annotation styles

| Finding type | Annotation |
|---|---|
| **Renamed element** | Red box around the current element + callout: "Lab says: **{old}** → Now: **{new}**" |
| **Missing element** | Red dashed box where element should be + callout: "Not found: **{element}**" |
| **Wrong location** | Red box at current location + arrow from where lab says it should be |
| **Extra step needed** | Green box around the new UI element + callout: "New step needed: **{action}**" |
| **Changed flow** | Series of numbered red circles showing the new click path |

### Screenshot file naming

Annotated screenshots follow this pattern:
```
runtime/screenshots/<course>-<slug>/
  step-<N>-actual.png          # What the UI looks like now
  step-<N>-annotated.png       # Annotated with red boxes/callouts
  step-<N>-replacement.png     # Clean screenshot to replace the lab's outdated one
```

## Phase 6 — Fix PR Generation

### When to generate a fix PR

Generate a fix PR when:
- At least one finding has verdict `broken` with confidence ≥ 0.7
- The finding includes a `suggested_correction` with specific text changes
- `--no-pr` flag was NOT passed

### Fix PR procedure

1. **Clone the agent-academy repo** (or use existing clone):
   ```bash
   gh repo clone microsoft/agent-academy -- --depth 1
   ```

2. **Create a fix branch**:
   ```bash
   git checkout -b fix/<course>-<slug>-lab-test-<run_id>
   ```

3. **Apply text corrections** to `docs/<course>/<slug>/index.md`:
   - For each finding with `suggested_correction`:
     - Find the original step text in the markdown
     - Replace with the corrected text
     - Preserve formatting (indentation, bold, code blocks, etc.)

4. **Replace outdated screenshots**:
   - For each finding where the lab's screenshot no longer matches:
     - Copy `step-<N>-replacement.png` to `docs/<course>/<slug>/assets/`
     - Use the same filename as the original screenshot referenced in the markdown
     - The replacement screenshot is the CLEAN capture (no annotations)

5. **Commit and push**:
   ```bash
   git add docs/<course>/<slug>/
   git commit -m "fix(<course>/<slug>): update steps to match current UI

   Automated fix from agent-academy-tester run <run_id>.

   Findings:
   - Step <N>: <summary of change>
   - Step <M>: <summary of change>

   Co-authored-by: agent-academy-tester <noreply@github.com>"
   git push origin fix/<course>-<slug>-lab-test-<run_id>
   ```

6. **Open the PR**:
   ```bash
   gh pr create \
     --repo microsoft/agent-academy \
     --base main \
     --head fix/<course>-<slug>-lab-test-<run_id> \
     --title "fix(<course>/<slug>): update lab steps to match current UI" \
     --body "<pr_body>" \
     --label "lab-test,automated"
   ```

### Fix PR body template

```markdown
## 🔧 Automated Lab Fix — {course}/{slug}

This PR was generated by the [Agent Academy Lab Tester](https://github.com/aprildunnam/AgentAcademyLabTestPlugin)
after detecting that lab instructions have drifted from the current Copilot Studio UI.

### Findings

| Step | Verdict | Change |
|------|---------|--------|
{findings_table}

### Details

{for each finding}
#### Step {N}: {summary}

**Expected (lab says):** {expected}
**Actual (current UI):** {observed}

**Before** (annotated):
![Step {N} annotated]({course}/{slug}/assets/step-{N}-annotated.png)

**After** (replacement screenshot):
![Step {N} replacement](docs/{course}/{slug}/assets/{screenshot_filename})

> Note: Annotated screenshots are committed to the PR branch under
> `docs/{course}/{slug}/assets/` so they render inline on GitHub.
> If the screenshots are too large, they are uploaded as issue attachments
> and linked via URL instead.

**Text change:**
```diff
- {old_text}
+ {new_text}
```
{end for}

### Test metadata

- **Date:** {date}
- **Environment:** {env_id}
- **Plugin version:** {plugin_version}
- **Confidence range:** {min_confidence}–{max_confidence}

{if issue_number}
Fixes #{issue_number}
{end if}
```

### Linking issues and PRs

- If a GitHub issue was filed (or already exists) for this lab, the PR body
  includes `Fixes #<issue_number>` so the issue auto-closes on merge.
- The issue also gets a comment linking to the PR:
  ```
  🔧 Fix PR opened: #<pr_number> — addresses the findings from this test run.
  ```

## Error handling

- If the user doesn't have push access to `microsoft/agent-academy`, the PR
  is opened from a fork instead (Playwright captures the fork URL).
- If `gh pr create` fails (permissions, branch conflict), fall back to
  printing the diff and suggested changes in the local report so the user
  can apply them manually.
- Screenshots that fail to capture (element not visible, page navigated away)
  are skipped — the PR proceeds with text corrections only.
- If ALL corrections are screenshot-only (no text changes), the PR is still
  opened with just the refreshed screenshots.
