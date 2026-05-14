# Local audit-history schema

The audit log lives at `~/.claude/plugins/mcs-lab-auditor/runtime/audit-history.yml`. It is **never committed** to the mcs-labs repo. It is the durable record of "which labs we audited, when, with which account, and what happened" — including labs that passed clean.

## File shape

```yaml
audits:
  - <entry>
  - <entry>
  - ...
```

The file is append-only — new entries go at the end. Every run appends one entry per lab attempted (pass, fail, error, or skipped).

## Entry schema

```yaml
- run_id: 2026-05-14T1430Z-7c91
  lab_slug: core-concepts-analytics-evaluations
  lab_order: 4                    # position in bootcamp_lab_orders, 1-indexed
  bootcamp_event: bootcamp        # always "bootcamp" today; reserved for future event lists
  started_at: 2026-05-14T14:32:11Z
  finished_at: 2026-05-14T14:41:02Z
  duration_seconds: 531
  status: pass                    # pass | issue_filed | error | skipped
  reason: null                    # populated when status != pass
  steps_total: 47
  steps_executed: 47
  steps_passed: 47
  findings_summary:               # always present, zeroed on pass
    high: 0
    medium: 0
    low: 0
    cannot_verify: 0
    non_deterministic: 0
  issue_url: null                 # set when status == issue_filed
  issue_action: null              # "created" | "commented" — for de-duplication audit trail
  plugin_version: "0.1.0"
  tenant_hint: contoso-dev        # label from config/workshop.yml — never the tenant id
  account_user_id: dewain+test12@msftworkshops.com
  workshop_code_hint: "ABCD"      # first 4 chars only — never the full code
```

## Status values

| status | meaning |
|---|---|
| `pass` | All executable steps returned `pass`. No findings. No issue filed. |
| `issue_filed` | At least one finding with confidence ≥ min_to_log. Issue URL recorded in `issue_url`. |
| `error` | The run halted before reaching the end of the lab — e.g., `auth_expired`, Playwright timeout, parser failure. `reason` populated with a short tag. |
| `skipped` | The lab was in the run's planned set but not attempted — e.g., user used `--labs csv` to subset, or `--resume` skipped it because it was already done. |

## Reason tags (when status == error)

- `auth_expired` — scene-boundary probe redirected to login.
- `playwright_timeout` — repeated `_browser_wait_for` failures.
- `parser_failure` — lab markdown didn't conform to the grammar.
- `judge_unavailable` — LLM call failed repeatedly.
- `gh_unavailable` — `gh issue create` failed (auth, network, rate limit).
- `user_aborted` — Ctrl+C, user said "stop", etc.
- `unknown` — fallback; details in the run's transcript.md.

## Querying

`/audit-report` uses this file to answer:

- "When did I last audit lab X, and what was the outcome?" → filter by `lab_slug`, sort by `finished_at` desc, take 1.
- "Which labs have I never audited?" → join against `_data/lab-config.yml` bootcamp list.
- "How often does lab X produce findings?" → count `status: issue_filed` by `lab_slug` over the last N runs.
- "What's the average duration of a full bootcamp audit?" → aggregate by `run_id`, sum `duration_seconds`.

Implementation tip: parse the whole file each time (it stays small — under 1 MB even after many runs). No indexing needed.

## File hygiene

- New entries are appended; old entries are never modified or rewritten.
- If the file grows past 5 MB, the orchestrator emits a soft warning ("consider archiving older runs") but does not auto-rotate.
- The user can edit by hand to add notes (`notes: "..."` field is reserved for free-text annotations); the plugin preserves unknown fields on read.
