# Playwright cookbook for Agent Academy portals

## Tool mapping

| Step kind | Primary action | Notes |
|---|---|---|
| navigate | `browser_navigate` | Only to URLs explicitly named in the step text |
| click | `browser_snapshot` → `browser_click` | Click by snapshot ref (accessibility label) |
| type | `browser_type` | Use for text input fields |
| fill form | `browser_fill_form` | When multiple inputs need filling at once |
| select | `browser_select_option` | For native `<select>` only; Power Platform combos use `browser_click` |
| keyboard | `browser_press_key` | Enter, Escape, Tab |
| wait | `browser_wait_for` | Prefer `text:` over `selector:` |
| inspect | `browser_snapshot` + `browser_take_screenshot` | Capture both for the judge |

## Execution fidelity

The test's job is to reproduce the **learner's path** click-for-click:

1. **Drive every step via the described UI affordance** — find the named button/menu/link
   by its visible text or role in the accessibility snapshot, then click it.
2. **Never skip steps by navigating directly to a URL** unless the lab step explicitly
   says to navigate to that URL.
3. If a control can't be found because the UI diverged, that IS the finding — record it.

## Portal map

| Portal | URL | Used by |
|---|---|---|
| Copilot Studio | `https://copilotstudio.microsoft.com/` | Most labs |
| Power Apps | `https://make.powerapps.com/` | Solution labs |
| M365 Copilot | `https://m365.cloud.microsoft/chat/` | Declarative agent labs |
| Power Platform Admin | `https://admin.powerplatform.microsoft.com/` | Environment setup |
| Power Automate | `https://make.powerautomate.com/` | Flow labs |

All portals federate to Entra ID — a single sign-in cascades via SSO.

## Manual authentication flow

Unlike the original plugin, this version does NOT automate sign-in:

1. `browser_navigate` to `https://copilotstudio.microsoft.com/`
2. The login page appears (redirected to `login.microsoftonline.com`)
3. **Ask the user to sign in manually** via `AskUserQuestion`
4. Poll with `browser_snapshot` every 10s to detect:
   - URL no longer contains `login.microsoftonline.com`
   - Page shows Copilot Studio home (environments list, agent builder, etc.)
5. Once authenticated, proceed with lab steps

## Environment switching

Many Agent Academy labs require being in a specific environment:

1. In Copilot Studio, the environment picker is in the left navigation
2. Look for the environment icon (typically shows current environment name)
3. If the lab says "switch to your developer environment":
   - Click the environment icon in the left nav
   - Look for the user's personal dev environment (e.g., "User's environment")
   - Select it and wait for the page to reload

## Common UI patterns in Copilot Studio

### Left navigation
- Home, Agents, Topics, Actions, Knowledge, Analytics, Solutions
- The ellipsis (...) or "Explore" icon opens additional options

### Agent creation
- "New agent" or "+ New agent" button on the Agents page
- May open a name/description modal or the agent builder directly

### Solution Explorer
- Accessed via left nav ellipsis → Explore → Solutions
- "New solution" button to create
- Publisher picker within the new-solution form

### Welcome modal (first visit)
- "Welcome to Microsoft Copilot Studio" with country picker
- Select "United States" → click "Get Started"
- Only appears once per account per browser session

## Known quirks

- **Classic vs New Experience toggle**: Some labs reference "classic" experience.
  Look for "New Experience" toggle in the upper-right corner.
- **Loading spinners**: Power Platform pages often have loading states. Use
  `browser_wait_for` with text of the expected loaded element.
- **Flyout menus**: Many menu items in Copilot Studio use flyouts that appear
  on hover or click — take a fresh snapshot after clicking to see child items.
- **Modal dialogs**: Solution publisher, agent naming, etc. use modal panes
  that slide in from the right side.

## Download handling (for solution export)

When exporting solutions, Power Platform triggers a browser download:

1. **Before clicking Export**, configure a download directory:
   - Use `browser_evaluate` to check if a download is triggered
   - The Playwright MCP server saves downloads to its default downloads path

2. **Click the Export button** and wait for the download to start.

3. **Wait for completion.** Use `browser_wait_for` to detect the download
   completion indicator in the UI (typically a toast notification or the
   Export button returning to its normal state).

4. **Locate the file.** After download, use Bash to find the `.zip` file:
   ```bash
   # Playwright MCP downloads go to the system default downloads folder
   ls -t ~/Downloads/*.zip | head -1
   ```

5. **Move to output directory:**
   ```bash
   mv ~/Downloads/SolutionName_*.zip runtime/solutions/
   ```

If the download does not trigger (some environments require a different
export flow), fall back to using `pac solution export` via CLI instead.
