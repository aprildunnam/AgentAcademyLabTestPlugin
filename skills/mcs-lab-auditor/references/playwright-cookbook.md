# Playwright cookbook for mcs-labs portals

This document captures known quirks, sign-in flows, and selectors for the five portals that bootcamp labs target. The primary skill reads it when deciding how to navigate, when to wait, and how to detect mid-run auth expiry.

## Tool mapping

| Step kind | Primary tool | Notes |
|---|---|---|
| navigate | `mcp__plugin_playwright_playwright__browser_navigate` | URL from step text or scene hint |
| click | `_browser_snapshot` → `_browser_click` | Click by snapshot ref. Never use raw CSS selectors. |
| type | `_browser_type` | Use `slowly: false` unless the field has client-side validation that rate-limits |
| fill form | `_browser_fill_form` | When multiple inputs need to be filled at once |
| select | `_browser_select_option` | For native `<select>` only; M365/Power Platform combos are usually clickable comboboxes — use `_browser_click` |
| keyboard | `_browser_press_key` | Enter, Escape, Tab |
| wait | `_browser_wait_for` | Prefer `text:` over `selector:` |
| inspect | `_browser_snapshot` + `_browser_take_screenshot` | Capture both for the judge |
| diagnostics | `_browser_console_messages`, `_browser_network_requests` | Read after a failed step to enrich the finding |
| evaluate | `_browser_evaluate` | Used sparingly (cookie/localStorage extraction, expiry-page scraping). Restricted by judge-config. |

## Portal map

| Portal | URL prefix | Auth-required probe |
|---|---|---|
| Copilot Studio | `https://copilotstudio.microsoft.com/` | `/environments` |
| M365 Copilot | `https://m365.cloud.microsoft/chat/` | `/chat/` |
| Power Platform admin | `https://admin.powerplatform.microsoft.com/` | `/environments` |
| Azure portal | `https://portal.azure.com/` | `/#home` |
| SharePoint | tenant-specific `https://<tenant>.sharepoint.com/` | tenant root |

All five federate to AAD — a single sign-in at `https://login.microsoftonline.com` cascades to all of them via SSO. In Playwright MCP, the orchestrator reuses the same browser session across turns/subagents; it does not persist auth via `storage-state.json`.

## Sign-in flow (run-start)

After decrypting the cached credential blob:

1. `_browser_navigate` to `https://login.microsoftonline.com/`.
2. `_browser_snapshot` to find the username input (label "Email, phone, or Skype" or "Sign in").
3. `_browser_type` the username.
4. Click `Next` (button text).
5. Wait for the password field (label "Password").
6. `_browser_type` the password.
7. Click `Sign in`.
8. **First-login password change**: if the URL navigates to `…/password/Change` or a "Update your password" page appears, abort the run with status `error, reason: first_login_password_change_required` — the workshop-issued account needs to be initialized once interactively before the plugin can use it.
9. **"Stay signed in?" prompt**: click `Yes`. This is required to ensure cookies persist long enough for the run.
10. **MFA prompt**: if challenged, abort with `error, reason: mfa_required` — workshop accounts should be exempt; if they're not, the workshop org didn't configure them correctly.
11. Wait for redirect to either the M365 home page or `office.com`. Confirm the signed-in landing page is reached and keep the current MCP browser session open for downstream portal steps.

That active MCP browser session covers all federated portals. The orchestrator does NOT need to re-sign-in per portal.

## Scene-boundary auth probe

At the start of each scene (h4 heading), navigate to `config/workshop.yml#auth_probe_url` (default Copilot Studio environments page). If the URL ends up at `login.microsoftonline.com/...`, the session expired:

1. Halt the run.
2. Mark the current lab `status: error, reason: auth_expired` in `manifest.yml`.
3. Append the run entry to `audit-history.yml` with the same status.
4. Tell the user to run `/audit-account redeem` and `/audit-bootcamp --resume <run-id>`.

If the probe succeeds (`copilotstudio.microsoft.com/environments` or similar in the URL), proceed with the scene.

## Known portal quirks

### Copilot Studio

- **Environment selector** appears in the top-right; after sign-in, the default environment may not be the one the lab expects. The judge should not flag this as `broken` — instead, flag as `cannot_verify` with a hint to switch environments.
- **Publish modal** appears slowly. After clicking "Publish", wait up to 30s for the confirmation modal — the actual publish operation can be 10-20s.
- **Generated topic regenerates** when you click "Generate". Lab screenshots from before regen may not match. This is `non_deterministic` territory.

### M365 Copilot / Agent Builder

- Agent Builder generates a different first-message and configuration on every "Generate" click. Steps that say "your agent should look similar to this" are `non_deterministic` by definition.
- The Agent Builder pane is an iframe inside `m365.cloud.microsoft/chat/`. `_browser_snapshot` may need a brief wait after navigation for the iframe to load.

### Power Platform admin

- Most pages are server-rendered and stable. Solution explorer and environment variables panels are the main lab targets.

### Azure portal

- First navigation to the Azure portal after sign-in shows a "Welcome to Azure" splash for new accounts. Dismiss with the close button if present.
- Resource creation forms have lots of asynchronous validation. Always `_browser_wait_for` the "Validation passed" text before clicking "Review + create".

### SharePoint

- Tenant-specific URL — the lab must supply it via a step. Workshop accounts get tenant-scoped SharePoint at `<workshopId>.sharepoint.com`.
- "Create site" wizard has a multi-step flow with selector text that varies by tenant template. Lean on visible-text targeting (`Communication site` button), not CSS.

## Anti-patterns

- **Do not use raw CSS or XPath selectors.** Always go through `_browser_snapshot` and target by ref. The DOM in M365/Power Platform changes between releases; visible text is more stable.
- **Do not skip the snapshot before a click.** The snapshot ref must come from a snapshot taken in the same step; using a stale ref will throw.
- **Do not click "Cancel" or "Discard" if a step seems wrong.** Halt the lab as `error` instead — destructive actions can corrupt prior steps' state.
