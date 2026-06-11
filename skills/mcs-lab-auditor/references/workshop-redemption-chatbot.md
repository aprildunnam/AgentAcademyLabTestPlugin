> Portal values come from `runtime/account/active-portal.yml`, which the
> orchestrator materializes at run start from the active lab instance's portal
> (the `mcs-labs` instance's portal is `config/workshop.yml`).

# Workshop-code → test-account redemption (chatbot portal)

This document describes the Copilot Studio chatbot redemption flow used by the MCS Workshop Agent (`https://aka.ms/MCSWorkshopAgent/`, which redirects to `https://microsoft.github.io/mcs-labs/`).

> **A workshop code is required unless you're reusing a cached user account.**
> The chatbot's "Workshop Pass Code" Adaptive Card is the **first** step: submit the code to gate the rest of the flow. After that, the chatbot transitions to an "Agent Training Assistant" greeting where you click the **"Get a User Account"** suggested-action button to continue with consent → form → credentials. Both steps are needed. Submitting the code alone does not issue credentials; clicking "Get a User Account" without first submitting the code will not work either.

> **The plugin must NOT prompt the user for anything except the workshop code.** The four dropdowns and the Job title input on the account-request form are all pre-populated from `runtime/account/active-portal.yml.chatbot_account_request_form`. The new password is generated from `runtime/account/active-portal.yml.account_new_password_pattern`. The only user input collected during redemption is the workshop code itself (via `AskUserQuestion`), and only when there is no valid cached account to reuse.

## Inputs

All inputs to this flow come from `runtime/account/active-portal.yml`. The plugin issues **at most one** `AskUserQuestion` call during redemption — the workshop code prompt — and even that is skipped when one of these is true:

- The user picked `Use cached: <user_id>` in Phase 1.5 Q1 (no redemption happens; we just sign in with the existing cached credentials).
- The user picked `Redeem a new user from the cached workshop code` in Phase 1.5 Q1 — the code comes from DPAPI-decrypting `runtime/account/workshop_code.enc` instead of asking the user.

If the user picked `Redeem a new workshop code` (or there is no cache and no `workshop_code.enc`), the workshop code prompt fires once.

- `workshop_portal_url` — chatbot URL.
- `workshop_code_required` — boolean. Default `true` — the workshop code is required unless using a cached user account. Set to `false` only if your event's chatbot genuinely does not gate on a code.
- `chatbot_account_request_form` — pre-populates the five form fields:
  - `organization_type` (e.g. `Microsoft`)
  - `industry` (e.g. `Technology (software & services)`)
  - `company_size` (e.g. `10,001+`)
  - `country` (e.g. `United States`)
  - `job_title` (e.g. `Software Engineer`)
- `account_new_password_pattern` — template for the AAD first-login password change, e.g. `Bootcamp-Audit-{year}!Q9`. The `{year}` token is substituted with the current calendar year.

## Outputs scraped from the chatbot

These come from the chatbot's success card — the plugin parses them, no user involvement:

- **Username** (`user_id`) — e.g. `user.<id>@copilotstudiotraining.onmicrosoft.com`.
- **Password** — temporary password, used once for sign-in then immediately replaced by the password from `account_new_password_pattern`.
- **Full name** — e.g. `User <ID>`.

## Persisted outputs

- `runtime/account/credential.enc` — DPAPI-encrypted **new** password (after the first-login change), NOT the temp password.
- `runtime/account/workshop_code.enc` — DPAPI-encrypted **full** workshop code. Required so the user can later choose `Redeem a new user from the cached workshop code` in Phase 1.5 Q1 without retyping the code. DPAPI keys are bound to the current Windows user, so this file is only readable by the same operator on the same machine — never echoed to console output, audit-history, issue bodies, or any other surface.
- `runtime/account/account.meta.json` — non-secret metadata: `user_id`, `tenant_hint`, `cached_at`, `expires_at`, `run_id`, `signed_in_at`, `password_changed_on_first_login: true`, and `workshop_code_hint` (the first 4 chars of the workshop code — never more — for human-readable identification of which event the cache came from).

## Outputs

- `runtime/account/credential.enc` — DPAPI-encrypted password blob.
- `runtime/account/account.meta.json` — non-secret metadata: `user_id`, `tenant_hint`, `cached_at`, `expires_at`, `run_id`, `signed_in_at`, `password_changed_on_first_login`. The `workshop_code_hint` field is now optional (omit if no code was used).

## Flow (current, verified 2026-05-26)

### Card 0 — Open the portal

```text
_browser_navigate(url: <workshop_portal_url>)
_browser_wait_for(time: 3)
```

The aka.ms link redirects to `https://microsoft.github.io/mcs-labs/`. The Lab Assistant chat dialog usually auto-opens. If it doesn't, click the `Request account` button (in the page header) or the `Open Lab Assistant chat` floating button.

### Card 1 — Submit the workshop code

The chat opens with a "Workshop Pass Code" Adaptive Card. **This is the first required step.** The workshop code comes from one of two sources depending on which Phase 1.5 Q1 option the user picked:

1. **`Redeem a new user from the cached workshop code`** — Decrypt `runtime/account/workshop_code.enc` via DPAPI; no `AskUserQuestion` needed.
2. **`Redeem a new workshop code`** (or no cache) — Prompt the user via `AskUserQuestion`. The user types the code via the auto-provided "Other" free-text path.

```text
# Resolve the workshop code
if ($interview.account_choice == 'redeem_with_cached_code') {
  $workshopCode = DPAPI_decrypt('runtime/account/workshop_code.enc')
} else {
  $workshopCode = AskUserQuestion(
    question: "What is the workshop code?",
    options: ["Cancel — use cached account", "Abort the run"]
  ).other_text
}

_browser_wait_for(text: "Workshop Pass Code", time: 30)
_browser_evaluate(function: (code) => {
  const inputs = [...document.querySelectorAll('input[type="text"]')].filter(i => i.offsetWidth > 0);
  if (!inputs.length) return 'no input';
  const target = inputs[0];
  target.focus();
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  setter.call(target, code);
  target.dispatchEvent(new Event('input', { bubbles: true }));
  target.dispatchEvent(new Event('change', { bubbles: true }));
  return 'filled';
}, $workshopCode)
_browser_evaluate(function: () => {
  for (const b of document.querySelectorAll('button')) {
    if ((b.innerText || '').trim() === 'Submit') { b.click(); return 'clicked'; }
  }
})
```

After submitting, the chat usually transitions to an "Agent Training Assistant" greeting card. This is normal — credentials are NOT issued at this step; the code gates the rest of the flow but does not itself produce the user. Continue to Card 2.

Save the first 4 chars of the workshop code to `account.meta.json.workshop_code_hint` so audits can correlate runs back to the same event without echoing the secret.

DPAPI-encrypt the full workshop code to `runtime/account/workshop_code.enc` at the end of the redemption flow (after credentials are successfully scraped) so a future Phase 1.5 Q1 can offer `Redeem a new user from the cached workshop code`. Skip this write if the code came from the cached file in the first place — the existing file is already valid.

### Card 2 — Click "Get a User Account"

Wait for the **Agent Training Assistant** card to be visible. It has three quick-reply buttons (`Product`, `Pricing`, `How-To`) plus a **"Get a User Account"** suggested-action button. Click "Get a User Account" to continue.

```text
_browser_wait_for(text: "Agent Training Assistant", time: 30)

# Scope the click to a button with exact name match — there are also nav
# buttons "Request account" / "Request an account" on the page header
# that look similar but do not trigger the redemption flow.
_browser_evaluate(function: () => {
  for (const b of document.querySelectorAll('button, [role="button"], a[role="button"]')) {
    if ((b.innerText || '').trim() === 'Get a User Account') { b.click(); return 'clicked'; }
  }
  return 'not found';
})
```

**Anti-pattern**: clicking the page-header `Request account` or `Request an account` buttons does NOT start the redemption flow — those just open the chat (which may already be open). The right surface is the `Get a User Account` button inside the chat's suggested-action card.

**Anti-pattern**: skipping Card 1 (the workshop code submission) and clicking `Get a User Account` directly may still let the chat respond, but the credential issuance will silently fail downstream because the code-gate hasn't been satisfied. Always submit the code first.

### Card 3 — Consent

Wait for the terms-of-use Adaptive Card (text contains `temporary access`, `data rules`, `shared tenant`, etc.). Check the `I confirm I've read and agree to these terms` checkbox, then click **`Consent and create account`**.

```text
_browser_wait_for(text: "I confirm")
# Check the checkbox (it's a real <input type="checkbox"> inside the card)
_browser_evaluate(function: () => {
  for (const c of document.querySelectorAll('input[type="checkbox"]')) {
    const lbl = (c.getAttribute('aria-label') || c.parentElement?.innerText || '').toLowerCase();
    if (/confirm|agree|read/.test(lbl) && c.offsetWidth > 0) { c.click(); return 'checked'; }
  }
})
# Then click the "Consent and create account" button
_browser_evaluate(function: () => {
  for (const b of document.querySelectorAll('button')) {
    if ((b.innerText || '').trim() === 'Consent and create account') { b.click(); return 'clicked'; }
  }
})
```

If the user prefers to abort, clicking **`I don't consent`** ends the flow. Record `redemption.status: aborted, reason: consent_declined`.

### Card 4 — Training user account request form

Wait for the form card (text contains `Training user account request`). It has four required dropdowns plus one required text input. **Every value comes from `runtime/account/active-portal.yml.chatbot_account_request_form`** — the plugin does not ask the user:

| Form field        | Config key                                            | Default                            |
| ----------------- | ----------------------------------------------------- | ---------------------------------- |
| Organization type | `chatbot_account_request_form.organization_type`      | `Microsoft`                        |
| Industry          | `chatbot_account_request_form.industry`               | `Technology (software & services)` |
| Company size      | `chatbot_account_request_form.company_size`           | `10,001+`                          |
| Country           | `chatbot_account_request_form.country`                | `United States`                    |
| Job title         | `chatbot_account_request_form.job_title`              | `Software Engineer`                |

These selections are metadata for workshop telemetry and **do not affect the issued user's permissions, region, or tenant**. Override individual values per event by editing the config; do **not** hard-code them in the redemption code.

```text
# Read the five form values from config — single source of truth.
$form = (Get-Content $workshopYml | ConvertFrom-Yaml).chatbot_account_request_form
$orgType   = $form.organization_type
$industry  = $form.industry
$companySize = $form.company_size
$country   = $form.country
$jobTitle  = $form.job_title

# Fill the four <select> dropdowns and the one text input, then submit.
_browser_evaluate(function: ([orgType, industry, companySize, country, jobTitle]) => {
  const targets = [orgType, industry, companySize, country];
  const selects = [...document.querySelectorAll('select')].filter(s => s.offsetWidth > 0);
  selects.forEach((s, i) => {
    const opt = [...s.options].find(o => o.text.trim() === targets[i]);
    if (opt) { s.value = opt.value; s.dispatchEvent(new Event('change', { bubbles: true })); }
  });
  // Fill the Job title input (the only remaining text input on the latest card)
  const feed = document.querySelector('[role="feed"]');
  const last = feed.querySelectorAll('article')[feed.querySelectorAll('article').length - 1];
  const inputs = [...last.querySelectorAll('input[type="text"]')].filter(i => i.offsetWidth > 0);
  for (const i of inputs) {
    if ((i.value || '') === '') {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
      setter.call(i, jobTitle);
      i.dispatchEvent(new Event('input', { bubbles: true }));
      i.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
}, [orgType, industry, companySize, country, jobTitle])

# Submit (the LAST Submit button on the page — there may be a leftover
# Submit button from the earlier Workshop Pass Code card if it was visible).
_browser_evaluate(function: () => {
  const feed = document.querySelector('[role="feed"]');
  const last = feed.querySelectorAll('article')[feed.querySelectorAll('article').length - 1];
  const btns = [...last.querySelectorAll('button')].filter(b => (b.innerText || '').trim() === 'Submit');
  if (btns.length > 0) btns[btns.length - 1].click();
})
```

**Pre-flight validation**: before clicking Submit, re-read every input's `value` via `_browser_evaluate` and confirm each matches the configured target string. If a dropdown silently rejected the value (the option text changed on the server side), the form will fail submission with no useful error — better to detect the mismatch early and surface it as a clear `redemption.status: error, reason: form_field_mismatch` than to let the chatbot eat the request.

### Card 5 — "Hang tight..." then credentials

The bot first posts `Hang tight, I'm setting up your account right now…`. Within ~60 seconds, a success card appears with:

```text
✅ Success! Your account has been created.
Here are your login details:
Full name: User <ID>
Username: user.<id>@copilotstudiotraining.onmicrosoft.com
Password: <issued temp password>
```

**Wait up to 90 seconds** for the success card to land — provisioning is the slowest step.

```text
_browser_wait_for(text: "Your account has been created", time: 90)
# Scrape credentials from the LATEST article in the chat feed.
_browser_evaluate(function: () => {
  const feed = document.querySelector('[role="feed"]');
  const arts = feed.querySelectorAll('article');
  for (let i = arts.length - 1; i >= 0; i--) {
    const t = (arts[i].innerText || '').replace(/\s+/g, ' ');
    if (/Your account has been created/i.test(t)) {
      const username = t.match(/Username:\s*([^\s]+@[^\s]+)/i)?.[1];
      const password = t.match(/Password:\s*(\S[^\n]*?)(?=\s+🔐|\s+Please store|$)/i)?.[1]?.trim();
      const fullName = t.match(/Full name:\s*([^\n]+?)(?=\s+Username)/i)?.[1]?.trim();
      return { username, password, fullName };
    }
  }
  return null;
})
```

If `username` or `password` is missing from the result, abort with `redemption.status: error, reason: credentials_not_scraped` and surface the raw card text in the run transcript for human triage. **Do NOT echo the password to console output, audit-history, or any persisted file other than the DPAPI-encrypted `credential.enc`.**

### Card 6 — Optional rating prompt

A follow-up card asks `Optional: rate your answer`. **Ignore it.** Credentials were already issued on Card 5; the rating is best-effort feedback. Do not block on it.

## Continue with the standard sign-in + cache flow

After scraping the credentials:

1. **Sign out the old session first.** The browser context may still be authenticated as the prior user. Navigate to `https://login.microsoftonline.com/common/oauth2/logout`, wait 5 seconds.
2. **Navigate to login.** `https://login.microsoftonline.com/`.
3. **Account picker.** If a "Pick an account" page appears, click `Use another account` (not the cached entry).
4. **Email**: fill the scraped username, click Next.
5. **Password**: fill the scraped temp password, click Sign in.
6. **First-login password change.** The IdP requires changing the temp password on first login. Fill `currentpasswd` with the scraped temp password, `newpasswd` + `confirmnewpasswd` with a strong generated password (the plugin uses the pattern `Bootcamp-Audit-<year>!Q<digit>` as a deterministic default; override via `runtime/account/active-portal.yml.account_new_password_pattern` if you need different policy).
7. **Verify sign-in landed.** Wait for the M365 landing page (`m365.cloud.microsoft/chat` or similar). The page title typically contains `M365 Copilot`.
8. **DPAPI-encrypt the NEW password** (not the temp password) to `runtime/account/credential.enc`. Write `runtime/account/account.meta.json` with:
   - `user_id` — the scraped Username
   - `tenant_hint` — from `runtime/account/active-portal.yml.tenant_hint` or the workshop name
   - `cached_at` — now
   - `expires_at` — now + 14 days (per the consent card's "ends 14 days after the training")
   - `run_id` — the current run-id
   - `signed_in_at` — now
   - `password_changed_on_first_login: true`
   - `workshop_code_hint` — OMIT for the current chatbot flow (no code was used)

## Variant — single-card credential issuance

A subset of events (typically small / private workshops) have a chatbot variant where submitting the workshop code on Card 1 issues credentials **directly** — no Training Assistant greeting, no "Get a User Account" button, no consent form, no profile form. If your event uses this variant, the plugin auto-detects it: after Card 1's Submit, wait up to 90s for either:

- `Your account has been created` (single-card variant — jump straight to Card 5's scrape logic), OR
- `Agent Training Assistant` (the standard flow described above — continue with Card 2).

Whichever shows first is the live flow for this run.

```text
# Race the two possible follow-up texts.
$result = await Promise.race([
  page.getByText("Your account has been created").waitFor({ timeout: 90000 }).then(() => 'single_card'),
  page.getByText("Agent Training Assistant").waitFor({ timeout: 90000 }).then(() => 'standard'),
])
if ($result === 'single_card') { jumpTo Card 5 } else { continue Card 2 }
```

## Anti-patterns

- **Never** skip the Workshop Pass Code card. The code is required (the user must provide it via `AskUserQuestion`) unless a valid cached account is being reused. Skipping the card and clicking `Get a User Account` directly will not produce credentials.
- **Never** click the page-header `Request account` button as if it were the redeem trigger — it just opens the chat (which auto-opens on page load anyway).
- **Never** prompt the user for the form values (organization type, industry, company size, country, job title). Those come from `runtime/account/active-portal.yml.chatbot_account_request_form`; surfacing them as `AskUserQuestion` choices is wasted UX.
- **Never** log the scraped password to console output, `audit-history.yml`, `manifest.yml`, issue bodies, PR descriptions, or any file other than DPAPI-encrypted `credential.enc`. The success card text MAY be retained in `runs/<run-id>/redemption-transcript.md` ONLY if that file is excluded from any subsequent issue/PR rendering.
- **Never** log the workshop code itself anywhere except the first 4 chars in `account.meta.json.workshop_code_hint`. The code is a per-event secret.
- **Never** assume the rating-prompt card means credentials weren't issued. Credentials land on the success card BEFORE the rating prompt; they're independent.
- **Never** reuse the temp password as the new password during the AAD first-login change. The IdP rejects "same as current" — generate a fresh password from `account_new_password_pattern`.

## What to do when stuck

| Symptom                                                                                                                  | Likely cause                                                                                                       | Fix                                                                                                                                                          |
| ------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| After Submit on the Workshop Pass Code card the bot shows the Training Assistant greeting; no credentials yet.            | Expected — the code-submit gates the flow but doesn't issue. Continue with Card 2 ("Get a User Account").          | No fix needed. Click the `Get a User Account` suggested-action button on the Training Assistant card to continue.                                            |
| Workshop code is rejected ("invalid code" or no transition).                                                              | Code typo, expired event, or already-used single-use code.                                                          | Re-prompt the user via `AskUserQuestion`. If still rejected, abort with `reason: invalid_workshop_code` and ask the user for a fresh code from the organizer.|
| `Get a User Account` button isn't visible after 30 seconds.                                                              | The chat hasn't finished initializing, OR the code wasn't successfully submitted on Card 1.                          | Verify Card 1 was submitted (check chat history for the "Bot said: 1 attachment" entry referencing the Training Assistant). If not, retry Card 1.            |
| Form submit doesn't transition to `Hang tight…`.                                                                        | One of the four dropdowns or the Job title text input is empty / silently rejected.                                | Use the pre-flight validation noted in Card 4 — re-read each input's value after fill, compare to the configured target, abort with `form_field_mismatch` on a mismatch instead of guessing. |
| Password change page rejects the new password.                                                                          | The new password doesn't meet the tenant policy (length, complexity).                                              | Use a longer password with mixed case + digit + symbol. Default `Bootcamp-Audit-<year>!Q<digit>` (22 chars) satisfies typical AAD password policy.            |
| Sign-in lands back at the password prompt instead of M365.                                                              | The new password was set but the temporary password was reused as the new password.                                | The temp password and new password MUST differ. Regenerate the new password and retry.                                                                       |
