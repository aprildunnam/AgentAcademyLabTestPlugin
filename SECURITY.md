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

This plugin handles workshop-issued test account credentials. The security model is documented in detail in [`docs/security.md`](docs/security.md), including:

- What is encrypted (passwords, tenant identifiers) versus stored as cleartext (user IDs, timestamps).
- The Windows DPAPI scope (current-user) and what that guarantees.
- The boundaries of the audit log (what's logged, what's never logged).
- Known limitations (browser cookies, screenshots that may capture PII, transcript hygiene).

If you discover a flaw in this plugin's credential handling, please report it through MSRC (above) rather than filing a public issue against this repo.
