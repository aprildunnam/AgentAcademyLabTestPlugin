---
description: Manage the DPAPI-cached workshop-issued test account used by mcs-lab-auditor (show, redeem, clear).
argument-hint: "[show|redeem|clear]"
allowed-tools:
  - Read
  - Write
  - PowerShell
  - AskUserQuestion
  - mcp__plugin_playwright_playwright__browser_navigate
  - mcp__plugin_playwright_playwright__browser_snapshot
  - mcp__plugin_playwright_playwright__browser_take_screenshot
  - mcp__plugin_playwright_playwright__browser_click
  - mcp__plugin_playwright_playwright__browser_type
  - mcp__plugin_playwright_playwright__browser_fill_form
  - mcp__plugin_playwright_playwright__browser_press_key
  - mcp__plugin_playwright_playwright__browser_wait_for
  - mcp__plugin_playwright_playwright__browser_evaluate
  - mcp__plugin_playwright_playwright__browser_close
---

# /audit-account

You are managing the cached test account for the mcs-lab-auditor plugin.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the mode (default: `show` if no args).
- `show` — print the cached account's user_id, tenant_hint, cached_at, expires_at. No browser activity.
- `redeem` — prompt for a workshop code, redeem it, encrypt the issued credential, cache it. Replaces any existing cache.
- `clear` — delete `credential.enc`, `account.meta.json`, and `storage-state.json`.

## Pre-flight context

- cached account meta: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json") { Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -Raw } else { "(no cached account)" }'`
- credential.enc present: !`powershell -NoProfile -Command 'if (Test-Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\credential.enc") { $size = (Get-Item "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\credential.enc").Length; "yes ($size bytes)" } else { "no" }'`
- workshop portal configured: !`powershell -NoProfile -Command '(Get-Content "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\config\workshop.yml" | Select-String "workshop_portal_url").Line'`

## Your task

### Mode: show (default)

Read `runtime/account/account.meta.json`. If absent, print:
> "No test account is cached. Run `/audit-account redeem` to set one up."

Otherwise print a compact summary:
```
Cached test account: <user_id>
Tenant hint:         <tenant_hint>
Cached at:           <cached_at>  (<relative time>)
Expires at:          <expires_at or "unknown">
Workshop code hint:  <workshop_code_hint>****
```

### Mode: redeem

Follow `~/.claude/plugins/mcs-lab-auditor/skills/mcs-lab-auditor/references/workshop-redemption.md` end-to-end.

1. Check `config/workshop.yml.workshop_portal_url`. If it's still `REPLACE_ME_ON_FIRST_RUN`, prompt the user via `AskUserQuestion` for the workshop event URL, then write it back to `workshop.yml` before proceeding.

2. Prompt the user for the workshop code (`AskUserQuestion` with one option labeled "Enter workshop code" plus the user's free-text). Never echo the code back; only the first 4 chars become `workshop_code_hint`.

3. Run the Playwright redemption flow: open portal → fill code → submit → wait for credentials page → scrape username/password/tenant/expiry via `_browser_evaluate`.

4. Sign in to `https://login.microsoftonline.com/` with the captured credentials. Handle "Stay signed in?" by clicking Yes. Abort with a clear message if MFA or first-login password change is required.

5. Capture cookies + localStorage to `runtime/account/storage-state.json`.

6. Encrypt the `{username, password, tenant_id}` JSON via PowerShell DPAPI (`ConvertTo-SecureString -AsPlainText -Force | ConvertFrom-SecureString`) into `runtime/account/credential.enc`. User-scoped — never machine-scoped.

7. Write `runtime/account/account.meta.json` with `user_id`, `tenant_hint` (from workshop.yml), `workshop_code_hint` (first 4 chars), `cached_at` (ISO timestamp), `expires_at` (if scraped, else null).

8. Confirm to the user:
   > "Cached test account `<user_id>` (expires <expires_at>). Run `/audit-bootcamp` or `/audit-lab <slug>` to use it."

### Mode: clear

```powershell
Remove-Item -Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\credential.enc" -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\account.meta.json" -ErrorAction SilentlyContinue
Remove-Item -Path "C:\Users\dewainr\.claude\plugins\mcs-lab-auditor\runtime\account\storage-state.json" -ErrorAction SilentlyContinue
```

Print:
> "Cleared cached test account and storage state. Run `/audit-account redeem` to cache a new one."

## Important

- **Never print the workshop code or password in any output.** Only `user_id` and `workshop_code_hint` (first 4 chars) are safe to display.
- **Never log decrypted credentials to transcripts, run artifacts, or the audit log.** The credential blob is decrypted only at the moment of driving sign-in, used, and let go.
- If decryption fails (different Windows user, machine changed, blob corrupted), tell the user to run `/audit-account clear` and `/audit-account redeem`.
