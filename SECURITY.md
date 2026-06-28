# Security

## Reporting security issues

**Do not report security vulnerabilities through public GitHub issues.**

Instead, please report them to the Microsoft Security Response Center (MSRC) at [https://msrc.microsoft.com/create-report](https://msrc.microsoft.com/create-report). If you prefer to submit without logging in, send email to [secure@microsoft.com](mailto:secure@microsoft.com). If possible, encrypt your message with our PGP key; please download it from the [Microsoft Security Response Center PGP Key page](https://aka.ms/opensource/security/pgpkey).

You should receive a response within 24 hours. If for some reason you do not, please follow up via email to ensure we received your original message. Additional information can be found at [microsoft.com/msrc](https://www.microsoft.com/msrc).

Please include the requested information listed below (as much as you can provide) to help us better understand the nature and scope of the possible issue:

- Type of issue (e.g. credential leak, prompt injection, command injection, unsafe deserialization, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit the issue

This information will help us triage your report more quickly.

If you are reporting for a bug bounty, more complete reports can contribute to a higher bounty award. Please visit our [Microsoft Bug Bounty Program](https://aka.ms/opensource/security/bounty) page for more details.

## Preferred languages

We prefer all communications to be in English.

## Policy

Microsoft follows the principle of [Coordinated Vulnerability Disclosure](https://aka.ms/opensource/security/cvd).

## Plugin-specific security model

This plugin does NOT handle or store any credentials. Authentication is performed
manually by the user in their browser — the plugin never sees, caches, or logs
passwords, tokens, or secrets.

**What the plugin DOES access:**
- Your browser profile (via Playwright MCP) — to reuse an existing M365 session
- Copilot Studio UI elements — via accessibility snapshots and screenshots
- GitHub CLI (`gh`) — for issue filing and PR creation, using your existing `gh` auth
- Power Platform CLI (`pac`) — optional, for solution management

**What the plugin DOES NOT do:**
- Store or cache any credentials (passwords, tokens, API keys)
- Automate the sign-in process (you always sign in manually)
- Log sensitive data in reports (screenshots may capture UI state — review before sharing)

**Screenshots and reports** are saved to `runtime/` (gitignored) and may contain
UI state from your environment. Review them before sharing or committing.

If you discover a security issue in this plugin, please report it through MSRC (above)
rather than filing a public issue against this repo.
