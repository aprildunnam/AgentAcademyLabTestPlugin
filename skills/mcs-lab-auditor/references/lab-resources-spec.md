# Lab Resources discovery and pre-flight scrape

Some mcs-labs reference a per-event **Lab Resources** SharePoint page that hosts the configuration values labs need (URLs, connector credentials, instance hostnames, etc.). The page is workshop-event-specific — different events publish different values, but the page structure stays stable.

This document describes how the orchestrator discovers and pre-flight-scrapes that page so steps that say *"use the values found in the Lab Resources"* can execute end-to-end instead of being skipped.

Labs that historically depended on Lab Resources values (non-exhaustive):

- `mcs-alm` UC2 — Custom Knowledge Endpoint, ServiceNow connection (Auth Type / Username / Password / Instance)
- `core-concepts-analytics-evaluations` UC2 — `EvaluationAlwaysFail.csv` (referenced via `<a href="EvaluationAlwaysFail.csv">` and downloaded from the same SharePoint site)
- `agent-builder-sharepoint` — SharePoint Site URL
- `mcs-governance` — SharePoint Knowledge URL
- `mbr-prep-sharepoint-agent` — SharePoint URL
- `ask-me-anything` — SharePoint Knowledge URL, classic-data Power Fx formula
- `guildhall-custom-mcp` — Pre-deployed Guild MCP server endpoint
- `expense-claims-with-approvals` — Site Address, File Identifier, Receipt location

If you discover a new lab depending on Lab Resources during a run, add it to this list.

## 1. Detection during lab parsing

While walking the markdown (per `lab-parser-spec.md`), record any external link whose URL matches one of these patterns as a **lab-resources reference**:

- `copilotstudiotraining.sharepoint.com/sites/Workshop/SitePages/Lab-Assets.aspx` (current Bootcamp event)
- `*.sharepoint.com/sites/*/SitePages/Lab*Assets.aspx` (generalized — Lab Assets, Lab-Assets, Lab Resources, etc.)
- Any link whose **link text** matches `/Lab Resources/i` or `/Lab Assets/i`

Store the first matched URL in the parsed step tree under `lab_metadata.lab_resources_url`. If the same URL appears multiple times in one lab, dedup — store once.

## 2. Pre-flight scrape (Phase 1.6 of SKILL.md)

If any lab in the planned list has `lab_metadata.lab_resources_url` set, the orchestrator MUST visit it once during Phase 1.6 and cache the values to disk. Skip Phase 1.6 only when:

- `--dry-run` is set (no browser activity allowed), OR
- The run is static-phase-only.

### Procedure

1. **Navigate** to the URL in the already-signed-in browser context (storage state from Phase 1.5 must work, since both the URL and the workshop account belong to the same tenant). Wait for the page title to read `Lab Resources` (or equivalent).

2. **Scrape the configuration table** by walking the visible DOM via `browser_evaluate`:

   ```js
   () => {
     const main = document.querySelector('main') || document.body;
     const text = (main.innerText || '');
     // The page renders configuration as label-value pairs separated by tabs/newlines.
     // Parse known keys; capture both the labeled lab section and the raw key.
     const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
     // ... orchestrator-side parser; see Section 3 below.
   }
   ```

3. **Write** `runs/<run-id>/lab-resources.yml` with the parsed key-value pairs. This file is **NEVER** logged elsewhere — see Security below.

4. **Take a screenshot** at `runs/<run-id>/lab-resources.png` (full page) for debugging if the parser misses a value. The screenshot is local-only and never uploaded.

5. **Continue** to Phase 1.7. Per-lab interactive steps that need a Lab Resources value read it from `runs/<run-id>/lab-resources.yml` at runtime.

### If Phase 1.6 fails

- **Page not found / 401 / 403**: the workshop account may not have access to this event's Lab Resources page, or the URL changed. Log the failure to the run transcript, set `lab_resources.status: unavailable`, and CONTINUE. Steps that depend on Lab Resources values will fall back to either user-prompt or skip-with-finding behavior.
- **Page found but no parseable table**: same fallback — log + continue.
- **Network failure**: follow the orchestrator's existing network-retry policy.

The orchestrator MUST NOT halt a whole run because Lab Resources scrape failed. Labs that don't depend on Lab Resources still need to run.

## 3. Parsing the configuration table

The current Bootcamp Lab Resources page (verified 2026-05-25) renders the configuration as a flat list of label-value pairs grouped by lab name. Sample fragment:

```
Setup for success
Environment variable: Custom Knowledge Endpoint
https://c22e64a4eda3ec278e9fb7e60ccab7.02.environment.api.powerplatform.com/...

ServiceNow: Authentication Type
Basic Authentication

ServiceNow: Username
CopilotStudioServiceAccount

ServiceNow: Password
<a password literal>

ServiceNow: Instance
https://dev341799.service-now.com/
```

Heuristic parser:

1. Walk `main.innerText` line-by-line.
2. A line that matches `/^[A-Z][^:]+:\s*[A-Z]/` (e.g. `"Setup for success"`) is treated as a **lab section header**.
3. A line ending in `:` (e.g. `"ServiceNow: Username"`) is a **key**.
4. The next non-empty line is the **value**.
5. Group into:

```yaml
labs:
  setup-for-success:
    custom_knowledge_endpoint: <url>
    servicenow:
      auth_type: Basic Authentication
      username: CopilotStudioServiceAccount
      password: <PASSWORD-redacted-in-this-document-only>
      instance: https://dev341799.service-now.com/
```

The orchestrator slugifies the section header for lookup, then exposes the parsed values to the per-lab interactive subagent as a `lab_resources` parameter.

## 4. Security — never log values

The Lab Resources page **contains real credentials**. The orchestrator MUST observe these rules:

- **NEVER include any Lab Resources value verbatim in**:
  - GitHub issue bodies or comments
  - PR descriptions or commit messages
  - `audit-history.yml` entries
  - `manifest.yml`
  - Console output, transcripts, or judge prompts
- The cache file `runs/<run-id>/lab-resources.yml` lives in the run directory but is **not part of the rendered finding artifacts**. The top-level `.gitignore` already excludes `runtime/` (where the run directory lives) from any accidental commit.
- The screenshot at `runs/<run-id>/lab-resources.png` likewise stays local.
- Findings that reference a value should describe it by **key only**: `"the value of lab_resources.labs.setup-for-success.servicenow.password"` — never the literal value.
- When using a value in a Playwright type/fill, the orchestrator MUST NOT echo it in any subsequent log line. `browser_type` and `browser_fill_form` accept text without logging by default; this is the path to use.
- If a step's correctness check would require comparing the live UI's value to the Lab Resources value, do the comparison in-memory only — never persist the value into the comparison's serialized output. The finding should say *"value matches Lab Resources"* / *"value does not match Lab Resources"*, not include either side.

## 5. When the lab doesn't reference Lab Resources

If no lab in the planned list has a `lab_metadata.lab_resources_url`, Phase 1.6 is skipped entirely — no browser navigation, no cache file. The vast majority of labs do not depend on Lab Resources.

## 6. Failure to satisfy a Lab Resources dependency at step time

If an interactive step needs a Lab Resources key but Phase 1.6 didn't run, or the key wasn't found in the scrape:

1. The orchestrator MAY prompt the user via `AskUserQuestion` to paste the value inline (single-question, with a free-text "Other" option). If provided, the value is cached in `runs/<run-id>/lab-resources.yml` for the rest of the run.

2. If the user declines, mark the step `cannot_verify, reason: lab_resources_missing` and continue. This becomes an audit-coverage gap noted in the run summary.

Never silently substitute a placeholder value (`"REPLACE_ME"`, an empty string, etc.) — that produces a misleading "the step ran" outcome when the step actually didn't.

## 7. Audit-time discovery — when a new lab needs Lab Resources values mid-run

If during interactive execution the orchestrator hits a step whose text references *"Lab Resources"* / *"Lab Assets"* for a lab that didn't have a `lab_metadata.lab_resources_url` detected during parsing (or whose Phase 1.6 scrape ran before the Lab Resources URL was reachable), the orchestrator should:

1. Pause the lab.
2. Locate the URL by re-scanning the lab markdown for any link whose text matches the patterns in §1.
3. If found, run a one-off scrape (single navigate + parse, same procedure as Phase 1.6) and merge the parsed values into the existing `lab-resources.yml`.
4. If not found, prompt the user via `AskUserQuestion` for the URL.

This recovery path ensures a single missed-during-parse Lab Resources reference doesn't force the entire lab into `cannot_verify`.
