# Lab Screenshot Annotation Guide

## Purpose

Every screenshot in a generated lab (from `/rewrite-lab` or `/create-lab`) should have
an **annotated version** that highlights the UI element the step is referencing. This
helps learners immediately see where to look and what to click.

## Two-file strategy

For every screenshot captured during lab generation, produce TWO files:

```
assets/
  step-03.png              ← clean screenshot (backup, not used in markdown)
  step-03-annotated.png    ← annotated version (used in the rendered markdown)
```

The `index.md` always references the `-annotated` version. The clean version exists
as a backup in case the annotation is wrong or needs to be re-done.

## When to annotate

Annotate screenshots when the step instruction references a specific UI element:

| Step instruction pattern | Annotation |
|---|---|
| "Click **{button}**" | Red box around the button |
| "Select **{menu item}**" | Red box around the menu item |
| "Navigate to **{tab/section}**" | Red box around the tab or nav item |
| "Type/Enter/Paste in the **{field}**" | Red box around the input field |
| "Toggle **{switch}**" | Red box around the toggle |
| "Expand **{section}**" | Red box around the expandable header |
| "You should see **{element}**" (verification) | Red box around what to look for |
| General "observe the page" | No annotation needed — clean screenshot is fine |

## Annotation procedure

After capturing each step's screenshot:

1. **Identify the target element.** From the step instruction, determine which UI
   element is being referenced (the bold text is usually the target).

2. **Find the element's position.** Use `browser_snapshot` to get the accessibility
   tree and identify the element. Note its role and name.

3. **Inject the annotation overlay.** Use `browser_evaluate` to draw a red rectangle
   around the target element:

   ```javascript
   (function() {
     // Find the target element by accessible name/role or text content
     const target = document.querySelector('[aria-label="{element_name}"]')
       || [...document.querySelectorAll('button, a, input, [role="tab"], [role="menuitem"]')]
           .find(el => el.textContent.trim().includes('{element_text}'));

     if (!target) return 'NOT_FOUND';

     const rect = target.getBoundingClientRect();

     const overlay = document.createElement('div');
     overlay.id = 'lab-screenshot-annotation';
     overlay.style.cssText = `
       position: fixed;
       top: ${rect.top - 4}px;
       left: ${rect.left - 4}px;
       width: ${rect.width + 8}px;
       height: ${rect.height + 8}px;
       border: 3px solid #ff0000;
       border-radius: 4px;
       z-index: 99999;
       pointer-events: none;
       box-shadow: 0 0 0 2px rgba(255, 0, 0, 0.3);
     `;
     document.body.appendChild(overlay);
     return 'OK';
   })();
   ```

4. **Take the annotated screenshot.** Use `browser_take_screenshot` and save as
   `step-<N>-annotated.png`.

5. **Remove the overlay.** Use `browser_evaluate`:
   ```javascript
   document.getElementById('lab-screenshot-annotation')?.remove();
   ```

6. **If the element can't be found** (selector fails), fall back to using the clean
   screenshot for both files. Note this in the evaluation so the user knows which
   screenshots may need manual annotation.

## Annotation styles

### Primary: Red box (most common)
- 3px solid red border (`#ff0000`)
- 4px padding around the element
- Slight border-radius (4px)
- Subtle red shadow for visibility on busy backgrounds

### For multiple elements in one step
If a step references multiple elements (rare — should be split into multiple steps),
annotate only the PRIMARY action target. Example: "Click **Save** in the **Properties**
panel" → annotate the Save button, not the panel.

### For dropdown/menu items not yet visible
If the target is inside a dropdown that hasn't been opened yet, take TWO annotated
screenshots:
1. First: annotate the dropdown trigger (e.g., the "..." menu button)
2. Second: after opening, annotate the menu item inside

## What the markdown looks like

In the generated `index.md`:

```markdown
1. Click the **New agent** button in the top toolbar.

   ![Click New agent button](./assets/step-01-annotated.png)
```

The `-annotated` version is always what's referenced. The clean `step-01.png` sits
in the same `assets/` folder as a backup.

## Fallback behavior

- If `browser_evaluate` fails to find the element → use clean screenshot, log a warning
- If the page has scrolled and the element is off-screen → scroll to element first,
  then annotate
- If the element is inside an iframe → attempt to access the iframe's document,
  fall back to clean screenshot if blocked by CORS
