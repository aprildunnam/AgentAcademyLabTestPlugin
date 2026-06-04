# Security model

`mcs-lab-auditor` handles workshop-issued test account credentials and drives a logged-in browser through several Microsoft product portals. This document spells out exactly what is sensitive, where each sensitive item lives, what protects it, and what the residual risks are.

> **Build mode (`/build-lab`, v0.4.0+) introduces no new secrets.** It reuses the same workshop account + DPAPI credential cache and the same logged-in browser session described here. Its only additional at-rest artifacts are the build workspace under `runtime/builds/<build-id>/` (draft markdown, captured screenshots, accessibility snapshots) — same protections and residual risks as the `runtime/runs/` artifacts below. Its only GitHub write is the new-lab PR (the audit gate writes nothing to GitHub).

If you find a flaw in this model, **do not file a public GitHub issue** — report it via MSRC per [`SECURITY.md`](../SECURITY.md).

## Secret inventory

| Item | Where it lives | Protection | Lifetime | Notes |
|---|---|---|---|---|
| Workshop code | In memory only during `/audit-account redeem` | Never written to disk; never echoed back | Single redemption call | First 4 chars stored as `workshop_code_hint` for diagnostics |
| Username (account email) | `runtime/account/account.meta.json` (cleartext) and `credential.enc` (encrypted) | None on the meta file | Until `/audit-account clear` or cache expiry | Treated as low-sensitivity — workshop-issued, not a real user identity |
| Password | `runtime/account/credential.enc` (encrypted) | Windows DPAPI, user-scoped | Until `/audit-account clear` or cache expiry | Decrypted briefly during sign-in only |
| Tenant ID | `runtime/account/credential.enc` (encrypted) | Windows DPAPI, user-scoped | Same as password | `tenant_hint` (cleartext label) is logged, never the actual tenant ID |
| Session cookies / localStorage | Active Playwright MCP browser session (not exported to `runtime/`) | No plugin-managed at-rest encryption | Lifetime of the active MCP browser session | Equivalent to a logged-in session while active |
| Screenshots | `runtime/runs/<id>/labs/<slug>/screenshots/*.png` | Filesystem permissions only | Indefinite | May incidentally capture PII visible in the test account's tenant (test data, lab artifacts) |
| Accessibility snapshots | `runtime/runs/<id>/labs/<slug>/snapshots/*.yml` | Filesystem permissions only | Indefinite | Captured DOM text — same concerns as screenshots |
| Audit log | `runtime/audit-history.yml` | Filesystem permissions only | Indefinite | Contains `account_user_id` (workshop account email) and timestamps; no passwords, no tokens, no tenant IDs |

## DPAPI: what it does and doesn't protect against

The credential blob (`credential.enc`) is encrypted via Windows DPAPI with the `CurrentUser` scope:

```powershell
ConvertTo-SecureString -String $plaintext -AsPlainText -Force `
  | ConvertFrom-SecureString `
  | Set-Content -Path 'credential.enc'
```

### What this protects against

- **Offline attack with the file alone.** Copying `credential.enc` to another machine or another Windows account yields gibberish — DPAPI binds the ciphertext to the current Windows user's master key, which itself is protected by their login credentials.
- **Accidental commits.** If the file is uploaded somewhere (a backup, an email attachment, a misconfigured cloud sync), it remains unreadable.
- **Other local users on the same machine.** Another Windows account on this same PC cannot decrypt the file — DPAPI's user scope is enforced by the OS.

### What this does NOT protect against

- **Code running as the same Windows user.** Any process under your account can call `ConvertFrom-SecureString` on this file and get the plaintext. DPAPI is not a sandbox; it's an at-rest protection.
- **The active Playwright MCP browser session.** The plugin does not export `storage-state.json`; auth continuity comes from the live browser session. Any code running as the same user with access to that session context can potentially act as the workshop account while it remains signed in.
- **Memory inspection.** Plaintext credentials exist in memory during sign-in. A debugger or memory-inspecting process running as your user could see them. The plugin minimizes the window (decrypt → use → release) but cannot eliminate it.
- **Backup software that copies user data en clair.** DPAPI-encrypted files travel encrypted, but run artifacts (like screenshots/snapshots) travel as-is. If your machine's backup includes `runtime/`, you're trusting your backup target.

## What is logged vs. never logged

### Logged (cleartext, in `runtime/audit-history.yml`)

- `account_user_id` — the workshop account email.
- `tenant_hint` — a human-readable label like `contoso-dev`, configured in `config/workshop.yml`.
- `workshop_code_hint` — first 4 chars of the workshop code.
- Run-id, timestamps, lab slugs, statuses, finding counts, filed issue URLs.

### Never logged

- Workshop code (full).
- Password (DPAPI-encrypted, never appears in any log, transcript, or issue body).
- Tenant ID (the real GUID).
- Bearer tokens, refresh tokens, session tokens of any kind.
- Decrypted credential JSON.

The orchestrator must take care to avoid logging request/response bodies that contain tokens. The default `_browser_network_requests` capture filters to **4xx/5xx responses only** — successful auth responses (which often carry tokens) are not captured. If you extend the plugin to capture successful responses, **filter token-bearing headers** explicitly.

## Issue body hygiene

Filed GitHub issues are public to anyone with read access to `microsoft/mcs-labs`. The issue body template:

- ✅ References screenshots by **local path**, never embedded. They stay on the user's machine.
- ✅ Quotes the lab instruction verbatim (already public content).
- ✅ Includes `tenant_hint` (configurable label, by convention not a tenant identifier).
- ❌ Should never include: passwords, tokens, internal Microsoft URLs that aren't already in the lab, screenshots embedded as base64, or anything that reveals the actual workshop tenant ID.

If `account_user_id` is sensitive in your context (e.g., the workshop account's local-part identifies the user), you can scrub it from the issue body template in `mcs-lab-issue-filer/SKILL.md` and `references/audit-log-schema.md`. By default it's only in the local log, not the issue body.

## Threat model

### In scope

- **Compromise of `credential.enc` alone**: DPAPI defeats this.
- **Compromise of an active signed-in MCP browser session**: an attacker with same-user access could act as the workshop account for as long as that session remains valid (usually a few hours). The workshop account itself has limited scope and expires within 24–48 hours.
- **Accidental disclosure via the audit log**: the log contains workshop-account identities and timestamps, no secrets.
- **Accidental disclosure via filed GitHub issues**: the issue body template excludes secrets by construction.
- **Accidental write to `microsoft/mcs-labs`** outside the enumerated narrow paths. Those paths are: the **Issues API**; the **fix-PR per audit run** (ADR-015); the **screenshots-only PR append** (ADR-014); and, in build mode, the **new-lab PR** (ADR-018). The orchestrator's "Important rules" sections and each PR sub-skill enumerate every write the plugin is allowed to make; anything beyond that is a bug, not a feature. Guardrails (`require_same_author`, `require_mergeable`, `allow_force_push: false`, run-unique branch names off fresh `origin/main`, stash/restore of unrelated working-tree changes) defend against the most common ways an automated push could damage a shared repo. **Build mode's audit gate files nothing on GitHub** (`build.audit_gate.suppress_github_writes`) — its findings stay local and feed the authoring loop.

### Out of scope

- **Compromise of the user's Windows account.** Any tool running as the user can read decrypted state. If your account is owned, secrets are gone — this is true of every plugin that handles credentials.
- **Compromise of the workshop portal itself.** If the issuer hands out a credential, anyone with that credential can use it; this plugin doesn't change that calculus.
- **Compromise of `microsoft/mcs-labs` repo permissions.** If a malicious actor has write access to the repo, they can read the issues this plugin files — but those issues contain only lab-content corrections, not credentials. The PR-append write path uses the same `gh` token the user is already signed in with; it does not escalate write access the user didn't already have.
- **Misuse of the user's `gh` token by other processes on the machine.** The PR-append sub-skill relies on `gh auth` having a token in the keyring; any process running as the same user can call `gh` directly. This is the same model as every CLI-tool-driven push and is not specific to this plugin.

## Recommendations

- **Run `/audit-account clear` after a multi-day audit cycle ends.** Cached credentials past their `expires_at` are useless to the plugin but still potentially harvestable.
- **Set tight filesystem permissions on `~/.claude/plugins/mcs-lab-auditor/runtime/`.** On a multi-user machine, ensure other accounts cannot read this directory. (DPAPI protects `credential.enc`; screenshots and other run artifacts are not encrypted.)
- **Audit `runtime/runs/<old-id>/` periodically.** Old run artifacts (screenshots, transcripts) can be deleted without affecting future runs. The audit log entries remain intact.
- **Do not check `runtime/` into any version control system.** The root `.gitignore` enforces this for this repo, but be careful if you copy the plugin elsewhere.
- **If a workshop account is compromised mid-audit, run `/audit-account clear`** and notify the workshop issuer to revoke. The plugin has no revocation power of its own.

## Reporting flaws in this model

Per [`SECURITY.md`](../SECURITY.md), report security issues via MSRC at https://msrc.microsoft.com/create-report or `secure@microsoft.com`. Do not file public GitHub issues on this repo for security concerns.
