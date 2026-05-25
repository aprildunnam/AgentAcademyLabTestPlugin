# Plugin self-improvement — never give up; file bugs and PRs against BOTH repos when stuck

The auditor's target is **100% coverage of every lab**. A run that returns `cannot_verify` on a step without first exhausting recovery options is an under-performing run. The auditor must push hard to drive every step through, and when it cannot, it must produce **both** outputs for that step:

1. A **lab finding** in `microsoft/mcs-labs` (if the lab is the problem — wrong instructions, broken sequence, UI drift the lab should update) + a fix PR.
2. A **plugin bug** in `microsoft/BootcampLabTestPlugin` (if the auditor is the problem — Playwright limitation, missing reference, unhandled UI pattern, absent input source) + a fix PR when the gap is mechanical.

Most stuck steps are caused by exactly one side. Some — like a lab that references a value not surfaced anywhere the auditor knows how to read — are caused by both, and warrant findings on both repos.

The auditor MUST NOT stop a lab unless there's a **true breaking condition** (defined in §1 below). Everything else has a recovery path that should be tried before any finding is filed.

## 1. True breaking conditions — the only reasons to stop a lab

Stop a lab only when one of these holds:

| Condition | Marker | What to do |
|---|---|---|
| The lab file is structurally invalid (no front-matter, no use-case headings, parser produces zero executable steps) | `status: skipped, reason: lab_file_malformed` | File ONE issue with a `parser_warning` finding describing the malformation. Move on to the next lab. |
| The workshop account is permanently locked / suspended (AAD lockout, password-change-required, MFA blocked) | `status: error, reason: account_unavailable` | Halt the run, prompt the user to redeem a new code, then resume via `/audit-lab <slug> --resume`. |
| The DEV environment was deleted / no longer exists | `status: error, reason: environment_gone` | Halt the run, surface a clear message. Lab cannot be audited without an environment. |
| A required external service (Microsoft Learn, Power Apps maker, SharePoint) is fully unreachable AFTER the network-retry policy in `judge-config.yml.execution.network_retry_count` is exhausted | `status: paused, reason: network_unstable` | Halt the lab, prompt the user (existing flow in SKILL.md §"What to do when stuck"). |
| A required tenant artifact from a prior lab in the same chain doesn't exist and can't be recreated in-band | `status: error, reason: chain_dependency_broken` | File a lab finding describing the chain expectation; halt only the affected lab. |

Everything else is **not** a true breaking condition. Specifically, do NOT stop the lab for:

- A Playwright-side limitation (file picker won't open, slash-mention won't trigger from `.fill`, cross-origin iframe blocks `evaluate`) — try the recovery patterns in §2 first.
- A missing input value (Lab Resources URL, OAuth credentials, lab-private file path) — try recovery in §3 first.
- A UI label drift, missing dialog, new coachmark — file the lab finding and CONTINUE the lab using the corrected interpretation.
- A cross-tab navigation, an iframe redirect, a single 401 / 403 / 5xx — retry once, then continue with reduced confidence.
- An `AskUserQuestion` answer the user declines — fall back to `cannot_verify` for that step but continue the lab.

### 1.1 Cascading-step failures are HIGH severity

A **cascading-step failure** is when step N can't be completed and that incomplete state causes step N+1 to also fail because N+1 depends on the artifact/state N was supposed to produce. Example: UC2 step 5 fails to save the **Custom Knowledge Endpoint** environment variable, so UC2 step 7's *"In the solution, select + New, then More and choose Connection reference"* can't find the saved variable to reference; the whole rest of UC2 cascades.

When the orchestrator detects a cascading-step failure:

1. The step that originally failed (step N) is the **root cause**. File its finding (lab or plugin side) at `severity: high` — not the default `medium`/`low` — and call out the cascade in the finding body: *"This breaks step N+1, N+2, …, N+K because each depends on the artifact step N was supposed to produce."*
2. Each downstream step (N+1, N+2, ...) is marked `cannot_verify, reason: blocked_by_step_N_cascade`. **No separate finding per cascaded step** — the root-cause finding covers them all.
3. The audit-run summary's coverage block must distinguish:
   - `cannot_verify (cascade)` — blocked by another step's failure; not independently broken.
   - `cannot_verify (independent)` — recovery patterns exhausted on the step itself.
4. A run that contains any cascading-step failure is a **high-impact run** — the run summary in chat must lead with that fact: *"X cascading-step failures in this run — these are high-priority for follow-up."*

The orchestrator detects a cascade by tracking step **dependencies** in the parsed step tree. Indicators that step N+1 depends on step N's output (non-exhaustive):

- Step N+1 references a literal name set in step N (e.g. *"select the **CARE Prompt Guidance** child agent"* after step N created it).
- Step N+1 uses a `${var}` placeholder from the step tree's `variables_set` map.
- Step N+1's scene heading is *"Test \<thing-from-step-N\>"* / *"Verify \<thing\>"* / *"Configure the \<thing\> you just \<verb\>ed"*.
- Step N+1 begins with *"Now"*, *"Then"*, *"After"*, *"Next"*, *"With the \<thing\> selected"* and references an artifact step N introduced.

When in doubt, ask the LLM judge to classify the dependency. If the judge says step N+1 depends on step N's completed state, treat the failure as cascading.

## 2. Recovery patterns BEFORE filing a plugin bug

Before concluding that a stuck step is the plugin's fault, the orchestrator MUST attempt the following recovery patterns, in order. Each is documented in detail in the `playwright-cookbook.md` reference; this section is the decision tree.

### 2.1 Click-then-keystroke pattern (for slash mentions, autocomplete pickers, contenteditable input)

If a step needs a mention chip inserted (e.g. UC2 of `core-concepts-variables-agents-channels` step 16, UC3 of `core-concepts-agent-knowledge-tools` Scene 4 step 4):

1. `browser_click` on the contenteditable to establish a real DOM cursor — NOT a programmatic `.focus()`.
2. `browser_press_key('/')` (or whatever trigger char) — fires a native keydown event.
3. Wait briefly for the popover.
4. `browser_click` on the desired option from the popover.

This pattern was retrofitted after PR #352 mistakenly claimed slash mentions were Playwright-blocked. They aren't.

### 2.2 Hidden-input file upload pattern (for `<input type=file>` behind a styled drop-zone)

If a step needs a file uploaded via a drop-zone that doesn't expose a native file chooser to Playwright's `browser_file_upload` modal-state detection:

1. Find the hidden `<input type=file>` via `browser_evaluate`.
2. Use Playwright's `setInputFiles` directly on that input. (Even though the MCP `browser_file_upload` tool wraps the modal-state path, the underlying Playwright frame exposes `setInputFiles`. The cookbook gives the exact incantation.)

If `setInputFiles` is genuinely not callable through the MCP layer, file a plugin bug requesting that the MCP expose the hidden-input bypass — but only after attempting the bypass via `browser_evaluate` + Playwright's frame locator.

### 2.3 Cross-origin iframe pattern (for Solutions, embedded maker surfaces)

`browser_evaluate` is cross-origin-blocked when an iframe's `src` is on a different origin than the parent page. But Playwright's `browser_snapshot` walks ARIA across frames and surfaces refs through the iframe. The recovery:

1. Don't try `iframe.contentDocument` — it will be `null` and the `evaluate` will throw.
2. Use `browser_snapshot` (which sees through the frame) to find refs.
3. Drive interactions via `browser_click` / `browser_type` with the iframe-prefixed refs Playwright returns.

This is the pattern that unblocked lab 5 UC1 Solutions (cross-origin iframe to `make.preview.powerapps.com`).

### 2.4 Re-scan-for-Lab-Resources pattern (when an unexpected per-event value is needed)

If a step's text references a value the orchestrator can't find in `runs/<run-id>/lab-resources.yml` AND Phase 1.6 ran:

1. Re-scan the lab markdown for any link whose text matches `/Lab Resources/i` or `/Lab Assets/i` — the URL may have been embedded later than the parser's first walk.
2. If found, run a one-off scrape of that URL (same procedure as Phase 1.6) and merge into the cache.

See `lab-resources-spec.md` §7 for the full mid-run recovery flow.

### 2.5 User-prompt pattern (last resort before `cannot_verify`)

If patterns 2.1–2.4 don't apply or fail, prompt the user via `AskUserQuestion` for the specific value or action needed. Phrase the question concretely — *"Paste the ServiceNow Instance URL"*, not *"What's missing?"*. The user can decline; that's fine — fall back to `cannot_verify` for that step only and continue the lab.

## 3. When the auditor concludes it's the plugin's fault

After exhausting §2's recovery patterns, if the auditor still can't drive the step, the gap is a plugin bug. File it:

1. **Don't halt the rest of the lab** — mark the affected step `cannot_verify, reason: plugin_gap_<short-slug>` and continue. Other steps / scenes / use cases that don't depend on the same gap should still execute.
2. **Aggregate within a run** — if the same gap shows up in multiple labs (e.g. file-upload hits 3 labs), file **one** plugin bug at end-of-run that lists all affected lab slugs + steps. Not three.
3. **Dedup before filing** — `gh issue list --repo microsoft/BootcampLabTestPlugin --state open --label plugin-bug` strict + loose; match against the `<!-- plugin-gap:<slug> -->` marker; comment instead of duplicating.
4. **File** with this template:

   ```markdown
   ## Plugin gap: `<short-slug>`
   <!-- plugin-gap:<short-slug> -->

   **Audit run:** `<run-id>` · **Date:** <iso>
   **Affected labs:** `<slug-1>` step <id-1>, `<slug-2>` step <id-2>, ...
   **Symptom class:** <one line>

   ### What the lab tells the learner to do

   > <verbatim quote from the affected step(s)>

   ### Recovery patterns attempted

   - §2.1 click-then-keystroke: <result>
   - §2.2 hidden-input bypass: <result>
   - §2.3 cross-origin iframe: <result>
   - §2.4 re-scan Lab Resources: <result>
   - §2.5 user prompt: <result>

   ### Why the auditor concluded the lab itself is correct

   <evidence>

   ### Proposed fix

   <concrete file-level proposal>

   ### Suggested labels

   `plugin-bug`, `<symptom-class-label>` (e.g. `playwright-limit`, `parser-gap`, `portal-map-stale`, `cross-origin-iframe`)
   ```

5. **Record** in the run manifest under `plugin_bugs_filed: [{slug, url, affected_labs}, ...]`.

## 4. Plugin fix PR — required for every mechanical bug

A bug is "mechanical" if the fix is confined to files under `skills/`, `references/`, `docs/`, or `config/` of `microsoft/BootcampLabTestPlugin`, doesn't change the CLI surface, and is a documentation, heuristic, or reference-content addition. **For every mechanical plugin bug filed, the auditor MUST also open a fix PR.** Filing the bug without a PR for a mechanical gap is an incomplete deliverable.

Procedure:

1. **Branch off `origin/main`**: `dewain/fix-plugin-<short-slug>` matching the bug slug.
2. **Apply the proposed fix.** Keep the diff minimal — one logical change per PR.
3. **Commit** with `<short-slug>: <one-line>` + `Closes #N` in the body. NEVER include a Claude co-author trailer.
4. **`gh pr create`** against `microsoft/BootcampLabTestPlugin:main` with body that:
   - Opens with `Closes #N`.
   - Summarizes the gap in 2–3 sentences.
   - Lists files changed + why.
   - Includes a test plan: *"Re-run /audit-lab `<slug>` and verify the previously-stuck step now completes."*
5. Record the PR URL in `plugin_bugs_filed[<entry>].fix_pr_url`.

Non-mechanical gaps (deep Playwright work, MCP server changes, new judge prompts, anything in `commands/`) — file the bug, document the gap, do NOT open a PR. Wait for a human.

## 5. Security — never log secrets in plugin bugs or fix PRs

The same rules that apply to lab findings apply here:

- Bug bodies, PR descriptions, and commit messages must NEVER contain workshop credentials, scraped Lab Resources values, AAD tokens, OAuth `client_secret`s, or any other secret material — even when the secret is the *cause* of the gap. Reference values by key only.
- Screenshots attached as evidence must NEVER capture password fields, OAuth consent screens with secrets in URL params, or test-pane chat history that echoes a credential.
- Stack traces / console messages with embedded credentials must be redacted before inclusion.

## 6. End-of-run summary — show both counts

Every audit run's chat summary must show both the lab-side and plugin-side counts:

```
Audited N labs in <duration>.

mcs-labs:
  X new issues / Y existing-issue comments / Z fix PRs.

BootcampLabTestPlugin:
  P new plugin bugs / Q existing-bug comments / R fix PRs.

Coverage:
  K of N steps verified-passed.
  L of N steps verified-failed-with-finding (lab side).
  M of N steps verified-failed-with-finding (plugin side).
  J of N steps cannot_verify (recovery patterns exhausted, user declined to provide value).

If J > 0, list the J steps so a follow-up audit can target them specifically.
```

A run where `J > 0` is incomplete coverage. The follow-up should target each `cannot_verify` step individually.

## 7. What this looks like in practice — three scenarios

### Scenario A: lab UI drift, plugin handles it correctly

Step says "click the **+ New** button". Live UI shows "**New**" (no leading "+"). Auditor:

- Files lab finding on mcs-labs (`gh issue create --repo microsoft/mcs-labs ...`).
- Opens lab fix PR on mcs-labs (`gh pr create --repo microsoft/mcs-labs ...`).
- Continues the lab using the corrected button label.
- No plugin bug.

### Scenario B: lab is correct, plugin can't drive it

Step says "upload the licensing PDF via the file dialog". Live UI has a styled drop-zone with a hidden `<input type=file>`. Auditor:

- Tries §2.2 hidden-input bypass — succeeds OR fails.
- If succeeds: lab finding (if there's one), continue.
- If fails: marks step `cannot_verify, reason: plugin_gap_browser_file_upload_hidden_input`. Continues lab. At end-of-run, files plugin bug on `microsoft/BootcampLabTestPlugin` + fix PR adding a `playwright-cookbook.md` recipe.

### Scenario C: both sides have bugs

Step says "use the Custom Knowledge Endpoint URL from the Lab Resources". The lab is correct, but the orchestrator parsed the lab markdown before §1 of `lab-resources-spec.md` was added — so `lab_metadata.lab_resources_url` is unset, Phase 1.6 didn't run, and the step has no value to use. Auditor:

- Tries §2.4 re-scan-for-Lab-Resources — finds the URL, scrapes, continues the step. No plugin bug needed here because the recovery pattern worked.
- (Hypothetically, if §2.4 hadn't been spec'd yet: file plugin bug + fix PR adding §2.4.)
- Also notes during the audit: the lab text says "In **Name**, enter `Custom Knowledge Endpoint`" but the field is actually labeled **Display name**. Files lab finding + fix PR on mcs-labs side too.
