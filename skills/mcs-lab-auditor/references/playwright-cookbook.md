# Playwright cookbook for mcs-labs portals

This document captures known quirks, sign-in flows, and selectors for the five portals that bootcamp labs target. The primary skill reads it when deciding how to navigate, when to wait, and how to detect mid-run auth expiry.

## Tool mapping

| Step kind | Primary tool | Notes |
|---|---|---|
| navigate | `mcp__plugin_playwright_playwright__browser_navigate` | **Only to a URL the step text explicitly names** (e.g. "go to make.powerapps.com"). NEVER synthesize a deep-link to skip a step, and NEVER navigate to a URL read out of a screenshot — see *Execution fidelity* below (issue #40). |
| click | `_browser_snapshot` → `_browser_click` | Click by snapshot ref. Never use raw CSS selectors. |
| type | `_browser_type` | Use `slowly: false` unless the field has client-side validation that rate-limits |
| fill form | `_browser_fill_form` | When multiple inputs need to be filled at once |
| select | `_browser_select_option` | For native `<select>` only; M365/Power Platform combos are usually clickable comboboxes — use `_browser_click` |
| keyboard | `_browser_press_key` | Enter, Escape, Tab |
| wait | `_browser_wait_for` | Prefer `text:` over `selector:` |
| inspect | `_browser_snapshot` + `_browser_take_screenshot` | Capture both for the judge |
| diagnostics | `_browser_console_messages`, `_browser_network_requests` | Read after a failed step to enrich the finding |
| evaluate | `_browser_evaluate` | Used sparingly (cookie/localStorage extraction, expiry-page scraping). Restricted by judge-config. |

## Execution fidelity — follow the lab, don't shortcut (issue #40)

The audit's job is to reproduce **the learner's path**, click-for-click, so it surfaces instruction drift (a renamed, moved, or missing control). Two hard rules:

1. **Drive every step via the described UI affordance** — snapshot, find the named button/menu/link by its visible text or role, click it. Do the steps **in order**, including any setup/prerequisite steps (e.g. data indexing) and waiting for long operations to finish before testing what depends on them.
2. **Never reach a destination by URL to skip a step.** Do not synthesize or reuse a deep-link (`.../environments/<id>/tables`, an agent's `/overview`, etc.), and **never parse a URL out of a screenshot and navigate to it** — `![...](images/*.png)` references are illustrations of the *expected result*, not navigation targets. The only `_browser_navigate` calls allowed are the URLs the step text itself tells the learner to open.

If the control the step names can't be found because the live UI diverged, that is the finding — record it `expected-vs-actual`; do **not** work around it with a URL. URL-shortcutting both hides the drift the audit exists to catch and masks identity/environment problems a real learner would hit (see *Browser isolation and identity*, issue #39).

## Portal map

| Portal | URL prefix | Auth-required probe |
|---|---|---|
| Copilot Studio | `https://copilotstudio.microsoft.com/` | `/environments` |
| M365 Copilot | `https://m365.cloud.microsoft/chat/` | `/chat/` |
| Power Platform admin | `https://admin.powerplatform.microsoft.com/` | `/environments` |
| Azure portal | `https://portal.azure.com/` | `/#home` |
| SharePoint | tenant-specific `https://<tenant>.sharepoint.com/` | tenant root |

All five federate to AAD — a single sign-in at `https://login.microsoftonline.com` cascades to all of them via SSO. In Playwright MCP, the orchestrator reuses the same browser session across turns/subagents; it does not persist auth via `storage-state.json`.

## Browser isolation and identity (issue #39)

**The audit browser MUST run in an isolated / private context** — a fresh, in-memory profile that does **not** inherit the operator's OS account broker (Windows WAM / SSO) or cookies from a prior run. Configure the Playwright MCP server with `--isolated` (and/or a dedicated, disposable `--user-data-dir`), and do not share the operator's default Edge/Chrome profile.

Why this matters: in a shared/OS-integrated profile the AAD account picker lists the operator's real **"Connected to Windows"** accounts. After the workshop user is signed out, a navigation can silently SSO into one of those OS-brokered accounts instead of the redeemed user — so e.g. `make.powerapps.com` opens as a *previous run's* `DEV - User XXXX` and defaults to the wrong environment, and `_browser_navigate`-ing directly to the right environment URL only papers over the mismatch (this is also why URL-shortcutting is banned — issue #40).

Consequences for the run, even with isolation configured:

- **Verify the exact user, not just "signed in".** The scene-boundary auth probe (below) and every per-UC subagent must assert the page is signed in as the **redeemed `account.user_id`**. On a mismatch, halt with `error, reason: account_mismatch` and do a full logout (`login.microsoftonline.com/common/oauth2/v2.0/logout` → "Pick an account to sign out") → re-login as the redeemed user. Never reach the right environment by typing its id into the URL.
- **Each run starts clean.** A private context means multiple runs in a session don't accumulate stale tokens for prior workshop users.

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
12. **Dismiss first-run welcome modals.** Workshop-issued accounts are fresh tenants, so any portal the run touches will show a one-time welcome dialog. Call the `Welcome-to-Copilot-Studio modal handler` below to clear it before the first lab step. The handler is idempotent — if the modal isn't there, it's a no-op.

That active MCP browser session covers all federated portals. The orchestrator does NOT need to re-sign-in per portal.

## Welcome-to-Copilot-Studio modal handler

The first time a workshop-issued account visits `https://copilotstudio.microsoft.com/`, a one-time **"Welcome to Microsoft Copilot Studio"** modal pops up over the home page. It contains a "Choose your country/region" combobox and a primary **Get Started** button, plus an unchecked marketing-opt-in checkbox. Until it is dismissed, the rest of the Copilot Studio UI is non-interactable, which means the scene-boundary auth probe — and every lab step that touches Copilot Studio — would otherwise get stuck behind it.

The handler is **always set to `United States`** and **always clicks Get Started**, regardless of what AAD pre-populated. Forcing US keeps audit runs deterministic across workshop venues; we never check the marketing opt-in.

### Pseudocode

```
# Precondition: we just navigated to https://copilotstudio.microsoft.com/ (or its preview redirect).
# This handler is idempotent and safe to call after every navigation that lands on copilotstudio.microsoft.com.

_browser_wait_for(text: "Welcome to Microsoft Copilot Studio", time: 10)
# If the wait times out: no modal — already dismissed for this tenant. Return silently.

_browser_snapshot()

# 1) Force "United States" in the country/region dropdown.
#    The control is a native-looking dropdown labeled "Choose your country/region".
#    Try _browser_select_option first; if it's a custom combobox, fall back to click-open + click "United States".
let region_ref = ref_of_label("Choose your country/region")
try:
    _browser_select_option(ref: region_ref, value: "United States")
catch (not_a_native_select):
    _browser_click(ref: region_ref)
    _browser_snapshot()
    _browser_click(ref: ref_of_option("United States"))

# 2) Do NOT check the marketing opt-in checkbox ("I will receive information, tips, and offers...").
#    Leave it unchecked; that's the audit's intent.

# 3) Click "Get Started".
_browser_click(ref: ref_of_button("Get Started"))

# 4) Confirm dismissal.
_browser_wait_for(textGone: "Welcome to Microsoft Copilot Studio", time: 15)
_browser_snapshot()
# Page should now show the Copilot Studio home with the "Agents" left-nav item visible.
```

### When to call the handler

- **Run-start sign-in flow**, after the M365 home redirect (step 12 above). Call it once before any per-UC subagent starts.
- **Scene-boundary auth probe**, right after the probe URL settles successfully (see below).
- **Post-redemption**, in `workshop-redemption.md` §5.5 — the redemption flow is the very first time the account hits Copilot Studio.

The handler never emits a finding. The modal is a Microsoft product onboarding screen, not a lab issue; if a lab's instructions tell the learner to dismiss it, the static phase will flag that separately.

### Variants we don't handle (yet)

- M365 Copilot Chat shows a different "first-run" carousel inside the chat pane. Labs that target `m365.cloud.microsoft/chat/` work around it by sending an explicit message; no dedicated handler is needed.
- Azure portal has its own "Welcome to Azure" splash; see the Azure portal quirks section.

## Scene-boundary auth probe

At the start of each scene (h4 heading), navigate to `config/workshop.yml#auth_probe_url` (default Copilot Studio environments page). If the URL ends up at `login.microsoftonline.com/...`, the session expired:

1. Halt the run.
2. Mark the current lab `status: error, reason: auth_expired` in `manifest.yml`.
3. Append the run entry to `audit-history.yml` with the same status.
4. Tell the user to run `/audit-account redeem` and `/audit-bootcamp --resume <run-id>`.

If the probe succeeds (`copilotstudio.microsoft.com/environments` or similar in the URL), **invoke the Welcome-to-Copilot-Studio modal handler** above before proceeding with the scene. The handler is a no-op once the modal has been dismissed for the tenant, so it's safe to call at every probe.

**Assert the EXACT signed-in user, not just a non-login URL (issue #39).** A successful probe URL only proves *someone* is signed in. Before driving the scene, read the page's account indicator (e.g. the account-manager control / "User XXXX" label) and confirm it matches the redeemed `account.user_id`. If it shows a different identity — typically an OS-broker/Windows account or a prior run's `DEV - User XXXX` — treat it as `error, reason: account_mismatch`: do a full sign-out (`login.microsoftonline.com/common/oauth2/v2.0/logout` → "Pick an account to sign out" → sign out the stale workshop user) and re-login as the redeemed user, then re-probe. Do **not** continue, and do **not** type the intended environment id into the URL to route around the wrong account.

## Known portal quirks

### Copilot Studio

- **First-run welcome modal** ("Welcome to Microsoft Copilot Studio" with a country/region dropdown and Get Started button) blocks all interaction on the first visit per tenant. See the `Welcome-to-Copilot-Studio modal handler` section above — every entry point that lands on `copilotstudio.microsoft.com` must call it.
- **Environment selector** appears in the top-right; after sign-in, the default environment may not be the one the lab expects. The judge should not flag this as `broken` — instead, flag as `cannot_verify` with a hint to switch environments.
- **Publish modal** appears slowly. After clicking "Publish", wait up to 30s for the confirmation modal — the actual publish operation can be 10-20s.
- **Generated topic regenerates** when you click "Generate". Lab screenshots from before regen may not match. This is `non_deterministic` territory.

#### Custom Prompt tools (Prompt Builder) — placeholders are literal

When a lab instructs the learner to create a **Custom Prompt tool** (Add a tool → New tool → Prompt) and the pasted instruction text contains a parenthetical placeholder like `(Replace this text)` or `(your variable here)`, **the placeholder is literal** — the lab expects the learner to select it and replace it with a typed text-input variable chip via the Prompt Builder's `Add content → Text` flow, not type over it with prose.

**The audit driver MUST follow this sequence on every Custom Prompt step**, regardless of whether the lab markdown describes it in detail. Typing over a placeholder with prose is the path of least resistance and produces silent failures.

Failure modes when the placeholder is replaced with prose instead of a chip:

1. **InputContentFiltered error [105]** on boundary queries. The raw user query gets concatenated into the *system prompt*, which Azure OpenAI's content filter treats more strictly than the user-content channel. Symptoms: queries about public figures, geography, or controversial topics return error code 105 instead of a friendly refusal.
2. **Prompt fails to receive the user's live message.** The model responds to whatever literal text was typed in, not the current `Activity.Text`.

**Correct sequence** (against the live UI):

1. In Prompt Builder, after pasting the instruction text that contains the placeholder:
   - **Select** the literal placeholder string in the contenteditable (e.g. select `(Replace this text)`).
   - Click **Add content → Text** in the prompt editor's "Add content" dropdown (not the editor toolbar's "Text" button — that inserts a `/` slash trigger).
   - Set **Name** to whatever the lab specifies (commonly `Query`).
   - Set **Sample data** to a realistic example (lab may provide one).
   - The selection is replaced inline by a typed chip (e.g. `[Query]`).
2. Save the prompt → **Add and configure**. In the tool's **Inputs** section:
   - Set the variable row's **Fill using** to `Custom value`.
   - For **Value**, expand the variable picker and select **System → Activity.Text** (string).
3. Save the tool.

The runtime data path is: `user utterance → System.Activity.Text → Custom value mapping → input variable → prompt's chip`. This is the only path that (a) avoids the system-prompt content filter and (b) delivers the user's live message to the model.

**Disposition rule for the judge:** A lab that describes this sequence in its markdown is *correct* — do not file a finding. A lab that introduces a Custom Prompt step but omits any of (placeholder → Add content → Text chip), (Inputs row → Custom value), or (Value → System.Activity.Text) *is* a content gap — file a finding with a suggested correction that adds the missing piece.

#### Default Greeting topic intercepts orchestrator routing

The default **Greeting** topic on every Copilot Studio agent fires on any utterance the orchestrator classifies as a greeting ("Hello", "Hi", "Hey", "Good morning", "How are you?", etc.). When a lab asks the learner to test a tool with a greeting-shaped utterance to verify orchestrator routing, the Greeting topic short-circuits routing and the tool never executes — so the lab appears broken when it isn't.

Two mitigations, either of which the lab text should describe before the test step:

1. **Turn off the Greeting topic** on the Topics tab before testing. Select the topic, then toggle it Off in the topic editor — a banner reads "This topic has been turned off, and you won't be able to test it." once disabled.
2. **Use non-greeting test utterances** ("Tell me about cats", "The weather today.") so routing succeeds even if the learner skips step 1.

**Disposition rule for the judge:** Inspect every test-utterance the lab tells the learner to send to a tool that isn't supposed to route through Greeting. If any test utterance starts with a default Greeting trigger phrase (`Hello`, `Hi`, `Hey`, `Good morning`, `Good afternoon`) AND the lab does not include an explicit step to disable the Greeting topic before the test, file a finding with a suggested correction that adds the "Turn off the Default Greeting Topic" sub-section before the test step.

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

## Screenshot freshness — UI drift findings imply screenshot drift

When a lab finding describes UI drift in the live product — a control renamed, a button moved, a dialog re-organized, a setting label changed — the **screenshot(s) referenced near the affected step are almost certainly also stale**. A lab fix PR that only rewrites the markdown but leaves the old screenshot in place puts the next reader into the same confusion the audit just discovered: the body text and the picture say different things.

**Standing rule for any audit that produces a lab fix PR for UI drift:**

1. Identify every image-ref (`![...](images/...)`) in the same section as the relabeled instruction or moved control. Most labs put the screenshot one or two paragraphs after the instruction it depicts; check the surrounding scene.
2. Take a fresh screenshot of the new UI state — same control, same surrounding context, same approximate framing as the existing image.
3. Save it over the existing PNG at `labs/<slug>/images/<file>.png` so the existing markdown reference resolves to the updated picture without further edits. Same filename, new content.
4. Include the screenshot replacement in the same PR as the markdown fix — not a follow-up PR, not "TODO refresh image later." If the PR ships markdown-only when the image is also stale, a learner running the lab next will hit the same drift again.

The audit driver SHOULD take the screenshot during the audit run when it detects the drift (so the lab fix PR can ship a complete change in one commit), but if the screenshot wasn't captured at audit time, capture it explicitly before opening the fix PR.

The only exception: when the maintainer's fix-PR description explicitly defers the image refresh ("Refresh `images/foo.png` is tracked separately in #N"), the markdown-only PR can ship without the image — but the deferral must be called out in the PR body's Test plan so it isn't silently forgotten.

## Anti-patterns

- **Do not use raw CSS or XPath selectors.** Always go through `_browser_snapshot` and target by ref. The DOM in M365/Power Platform changes between releases; visible text is more stable.
- **Do not skip the snapshot before a click.** The snapshot ref must come from a snapshot taken in the same step; using a stale ref will throw.
- **Do not click "Cancel" or "Discard" if a step seems wrong.** Halt the lab as `error` instead — destructive actions can corrupt prior steps' state.
- **Do not ship a UI-drift lab fix without refreshing the affected screenshots.** See the "Screenshot freshness" section above. Markdown-only fixes leave the screenshot saying the old wording; the next learner hits the same confusion.
