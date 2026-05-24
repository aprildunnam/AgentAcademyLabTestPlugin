# Workshop-code → test-account redemption

This document describes the Playwright flow the `/audit-account redeem` command runs to exchange a workshop code for a usable test account, and how the result is encrypted and cached on disk.

The default flow assumes a Skillable-style "enter code → get credentials on confirmation page" portal. Other portals (e.g., ones that email credentials) require editing this file and `config/workshop.yml` accordingly.

## Inputs

- `config/workshop.yml.workshop_portal_url` — the redemption portal URL.
- `config/workshop.yml.redemption_selectors` — accessibility hints for the form and confirmation page.
- The workshop code, prompted from the user via the chat (never logged or echoed back beyond the first 4 chars).

## Flow

### 1. Open the redemption page

```
_browser_navigate(url: <workshop_portal_url>)
_browser_snapshot()
```

If the URL is the placeholder `REPLACE_ME_ON_FIRST_RUN`, abort with a clear message:
> "Edit `~/.claude/plugins/mcs-lab-auditor/config/workshop.yml` and set `workshop_portal_url` to your workshop event's redemption URL."

### 2. Enter the code

From the snapshot, find the input whose accessibility label matches `redemption_selectors.code_input_label` (default "Workshop code"). If multiple match, take the first visible one.

```
_browser_type(ref: <code-input-ref>, text: <workshop-code>, slowly: false)
```

Then submit. The submit control is either a button matching `redemption_selectors.submit_button_text` or the Enter key on the code input.

```
_browser_click(ref: <submit-button-ref>)
   # or
_browser_press_key(key: "Enter")
```

### 3. Wait for the credentials page

```
_browser_wait_for(text: <redemption_selectors.credentials_panel_heading>)   # default "Your account"
_browser_snapshot()
```

Timeout 60 seconds. If the wait times out:

- Check the page for an error message ("Invalid code", "Expired code", "Code already used"). Extract via `_browser_evaluate` reading `document.body.innerText`. Abort with that message in `reason`.
- If no error is visible, abort with `reason: redemption_timeout` and instruct the user to inspect the page manually.

### 4. Scrape the issued credentials

```
_browser_evaluate(function: `() => {
  const labels = [
    "${redemption_selectors.username_label}",
    "${redemption_selectors.password_label}",
    "${redemption_selectors.tenant_label}",
    "${redemption_selectors.expiry_label}"
  ];
  const result = {};
  for (const label of labels) {
    // Find a node whose text contains the label, then read the adjacent value.
    // Most workshop portals render label + value as siblings inside a definition list or table.
    const xpath = \`//*[normalize-space(text())="\${label}" or normalize-space(text())="\${label}:"]\`;
    const node = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
    if (!node) continue;
    // Look for the value in the next sibling, child, or parent's next sibling.
    const candidates = [
      node.nextElementSibling,
      node.parentElement?.nextElementSibling?.firstElementChild,
      node.parentElement?.querySelector('[class*="value"], [data-testid*="value"]'),
    ].filter(Boolean);
    result[label.toLowerCase()] = candidates[0]?.innerText?.trim() ?? null;
  }
  return result;
}`)
```

The result is a JSON object like:
```json
{
  "username": "user12@workshop.contoso.com",
  "password": "Pa$$word!2026",
  "tenant": "workshop.contoso.com",
  "expires": "2026-05-16 18:00 UTC"
}
```

If `username` or `password` is missing, abort with `reason: credentials_not_scraped` and prompt the user to update the selectors in `config/workshop.yml`.

### 5. Sign in to AAD with the captured credentials

Follow the sign-in flow documented in `playwright-cookbook.md#sign-in-flow-run-start`. The point of this step is to (a) prove the credentials work, (b) handle any first-login password change requirement, and (c) capture cookie + localStorage state to `runtime/account/storage-state.json`.

If the sign-in succeeds, the storage state is now valid for all federated portals.

### 5.5. Dismiss the Copilot Studio first-run welcome modal

Workshop-issued accounts are always fresh tenants, so the first navigation to `https://copilotstudio.microsoft.com/` after sign-in shows the **"Welcome to Microsoft Copilot Studio"** modal with a country/region dropdown and a Get Started button. Until it is dismissed, the scene-boundary auth probe and every lab step that touches Copilot Studio will be blocked behind it.

Invoke the `Welcome-to-Copilot-Studio modal handler` documented in `playwright-cookbook.md` — it forces the dropdown to `United States` and clicks Get Started. The handler is idempotent (no-op if the modal isn't present), so it's safe to call once here even when the run will later call it again at the first scene boundary.

### 6. Encrypt and cache

Persist the credential blob via Windows DPAPI (user-scoped):

```powershell
$plain = @{
  username = $username
  password = $password
  tenant_id = $tenant
} | ConvertTo-Json -Compress

$secure = ConvertTo-SecureString -String $plain -AsPlainText -Force
$encrypted = $secure | ConvertFrom-SecureString
Set-Content -Path 'runtime\account\credential.enc' -Value $encrypted -Encoding UTF8
```

Write the metadata file (cleartext, but contains no secrets):

```powershell
@{
  user_id = $username
  tenant_hint = $tenant_hint_from_config
  workshop_code_hint = $code.Substring(0, [Math]::Min(4, $code.Length))
  cached_at = (Get-Date -Format 'o')
  expires_at = $parsed_expiry_iso   # or $null if not on the page
} | ConvertTo-Json | Set-Content -Path 'runtime\account\account.meta.json' -Encoding UTF8
```

Confirm to the user:

> "Cached test account `<user_id>` (expires `<expires_at>`). Subsequent `/audit-*` commands will reuse this account unless you run `/audit-account clear` or pick `[n]` at the run-start prompt."

## Decryption (when starting an audit)

```powershell
$encrypted = Get-Content 'runtime\account\credential.enc' -Raw
$secure = $encrypted | ConvertTo-SecureString    # fails if the current Windows user differs
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
  $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  $cred = $plain | ConvertFrom-Json
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
# $cred.username, $cred.password are now in memory just long enough to drive sign-in
```

After driving sign-in, clear `$plain`, `$cred`, and any intermediate variables.

## Clearing the cache

`/audit-account clear` removes all three files:

```powershell
Remove-Item -Path 'runtime\account\credential.enc' -ErrorAction SilentlyContinue
Remove-Item -Path 'runtime\account\account.meta.json' -ErrorAction SilentlyContinue
Remove-Item -Path 'runtime\account\storage-state.json' -ErrorAction SilentlyContinue
```

Then prints "Cleared cached test account. Run `/audit-account redeem` to set up a new one."

## Adapting to a different workshop portal

If your event uses a portal that differs from the Skillable-style flow:

1. Update `workshop_portal_url` in `config/workshop.yml`.
2. Adjust `redemption_selectors.*` to match the new portal's labels.
3. If the new portal emails credentials instead of displaying them, replace §3–§4 above with a manual prompt: have the orchestrator print "Check your email; paste the issued username and password" and `AskUserQuestion` for each. Continue from §5.
4. Document the new flow inline here so future runs work without re-deriving.
