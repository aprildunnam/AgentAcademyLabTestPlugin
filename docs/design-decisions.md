# Design decisions

This document enumerates the major architectural choices made when building `mcs-lab-auditor` and the rationale behind each. It is loosely ADR-style: each entry has a status, context, decision, consequences, and alternatives that were considered and rejected.

When proposing a change to the plugin's shape, check whether your change affects an existing decision — if so, update that decision's status (e.g., to `superseded by ADR-N`) rather than silently changing behavior.

---

## ADR-001 — Plugin scope: GitHub issues, not pull requests

**Status:** Accepted.

**Context.** The plugin needs to surface lab problems back to the maintainers of `microsoft/mcs-labs`. The two obvious paths are (a) opening a PR with proposed edits to `_labs/<slug>.md` for each finding, or (b) filing a GitHub issue with suggested corrections in the body, leaving application to a human.

**Decision.** File **GitHub issues**. One issue per lab with findings. Suggested corrections appear in the issue body as `diff`-style blocks but are never applied as edits.

**Consequences.**
- The plugin writes to `microsoft/mcs-labs` through **two narrow paths only**: the Issues API (always on) and a screenshots-only commit appended to an already-open fix-PR (default on; opt out per-run with `--no-update-screenshots`). It never creates a new branch or new PR. See ADR-014 for the carve-out's design.
- CODEOWNERS, branch protection, and signed-commit policies are irrelevant to the plugin's operation.
- Maintainers triage findings and decide which corrections to apply; false positives are filtered by humans rather than amplified into bad commits.
- Re-audits comment on existing issues (de-duplication via label combo) rather than opening duplicates.

**Alternatives considered.**
- **PRs with applied edits.** Rejected. Implies the suggested correction is "the fix" and bypasses human judgment; high stakes when an LLM judge is the source of the correction. Also requires the plugin to maintain a working tree of the labs repo, which couples the two more tightly than necessary.
- **Filing the audit-log to the labs repo via a separate PR.** Rejected for clean runs (would produce a PR with no findings, contradicting the "no PR when nothing's wrong" rule). The audit log stays local-only (`runtime/audit-history.yml`).

---

## ADR-002 — Workshop-code-issued test account, DPAPI-cached

**Status:** Accepted.

**Context.** Each audit run drives the live Microsoft product UI. Using the user's personal Microsoft account would (a) intermix audit activity with their real work, (b) leak audit-generated agents/solutions into their normal tenant, and (c) require them to trust the plugin with personal credentials. Bootcamp attendees consume the labs via workshop-issued accounts — the plugin should use the same path.

**Decision.** At run start, exchange a **workshop code** at a configurable workshop portal (default: Skillable-style) for a one-time test account. Cache the issued credentials via **Windows DPAPI** (`ConvertFrom-SecureString`, user-scoped) at `runtime/account/credential.enc`. Reuse the cached account across every lab in a run.

**Consequences.**
- Audit activity is isolated from the user's normal account.
- Credentials at rest are decryptable only by the same Windows user on the same machine — no portability concern (intended).
- Workshop accounts have a finite lifetime (typically 24–48 hours); the plugin records `expires_at` and detects mid-run expiry via a scene-boundary probe.
- Windows-only. macOS/Linux support would require swapping DPAPI for a portable equivalent (Keychain on macOS, `secret-tool` on Linux), deferred until needed.

**Alternatives considered.**
- **Plaintext config file with credentials.** Rejected — secrets in disk-readable form are a non-starter regardless of how short-lived the account is.
- **Encrypt with a plugin-managed symmetric key.** Rejected — adds dependency complexity and provides no security benefit over DPAPI for this use case.
- **Re-redeem a workshop code at every run.** Rejected — wastes workshop codes (each redemption typically consumes one), and frustrates the user with a sign-in flow on every invocation.
- **Use the user's personal Microsoft account with Playwright `storageState`.** Rejected for the audit-isolation reasons above.

---

## ADR-003 — Run-start prompt to choose cached vs new account

**Status:** Accepted.

**Context.** A cached account is great when the same workshop is still active, but bootcamps run frequently and accounts expire. The plugin must let the user decide whether to reuse cached state or redeem fresh credentials, every time a run starts.

**Decision.** At the top of every `/audit-bootcamp` and `/audit-lab` invocation, if a cached account exists, **prompt the user**: show the cached `user_id` and offer `[y] use cached / [n] redeem a new workshop code`. If no cache exists, go straight to the redemption flow.

**Consequences.**
- One extra prompt per run, but the prompt is informative (shows cached identity) and zero-friction when the user wants the default ("yes, use cached").
- `--resume <run-id>` skips the prompt when the cached account is still valid (within `expires_at`), matching the "resume what was running" intent.
- Encourages the user to think about which account they're testing against before kicking off a multi-hour audit run.

**Alternatives considered.**
- **Always use cached if present, fail loudly on expiry.** Rejected — silent reuse of yesterday's account is surprising when the user expected to test with a fresh one.
- **Always re-redeem.** Rejected for the same reason as ADR-002 alt #3.

---

## ADR-004 — No environment cleanup as part of audit runs

**Status:** Accepted.

**Context.** Running 11 bootcamp labs in sequence against the same tenant creates orphan agents, solutions, and knowledge sources. There is an existing MCP server (`copilot-studio-cleanup`) that can purge these. The plugin could invoke it between labs or at the end of a run.

**Decision.** **No automatic cleanup.** The plugin never invokes `copilot-studio-cleanup` or any agent-deletion command. Orphan management is the user's responsibility outside this plugin.

**Consequences.**
- The plugin's behavior is more predictable — it only does the audit, nothing else.
- Two responsibilities (test execution, tenant hygiene) stay separately controllable.
- Users running many audits may accumulate orphans; they can run cleanup separately as they choose.
- Removes a category of accidental destructive action (the plugin can't delete things the user wanted to keep).

**Alternatives considered.**
- **Opt-in `--cleanup-between-labs` flag.** Rejected by user direction. Even opt-in coupling muddies the boundary.

---

## ADR-005 — Lab list enumerated from `lab-config.yml`, never hard-coded

**Status:** Accepted.

**Context.** The bootcamp lab list lives in `microsoft/mcs-labs/_data/lab-config.yml` under `lab_orders.event.bootcamp`. The list can change as bootcamp content evolves.

**Decision.** Read the slug list from `_data/lab-config.yml` at runtime every time. Never hard-code slugs in the plugin code or config.

**Consequences.**
- The plugin automatically picks up changes to the bootcamp roster — no plugin update needed when labs are added/reordered.
- One source of truth.
- If a slug is listed but the corresponding `_labs/<slug>.md` is missing, the plugin records `status: skipped, reason: lab_file_missing` and continues with the rest — never aborts the whole run because of one missing lab.

**Alternatives considered.**
- **Hard-code the 11 current slugs in `judge-config.yml`.** Rejected — drift inevitable.
- **Maintain a separate manifest in this plugin's repo.** Rejected — two sources of truth.

---

## ADR-006 — Structured step parsing with stable IDs

**Status:** Accepted.

**Context.** Each lab is ~30–80 numbered steps. The judge needs to compare each step's intent to observed UI behavior. There are two extremes: (a) feed the entire lab markdown to the LLM every step, asking "what step are we on and did it succeed?", or (b) parse the lab into a structured step tree first and dispatch one step at a time.

**Decision.** **Parse first, then dispatch.** Each lab is converted into a `steps.json` tree (use cases → scenes → steps) with stable IDs like `usecase-2.scene-3.step-4`. The judge sees one step at a time with explicit context (parent scene, attached hints, sub-bullets).

**Consequences.**
- Bounded cost per step (one judge call with bounded input size).
- Step IDs are stable across runs — re-audits can identify "the same step" reliably, enabling de-duplication and longitudinal tracking.
- Adds a parser-correctness concern: if the parser splits a lab wrong, the judge sees skewed inputs. Mitigated by parser validation rules and a `parser_warning` finding type.
- Action classifier (`navigate | click | type | ...`) lets the orchestrator dispatch to the right Playwright tool without LLM cost on routine steps.

**Alternatives considered.**
- **LLM-driven step extraction at runtime.** Rejected — non-deterministic step boundaries break ID stability, and re-parsing 80 steps every run wastes tokens.
- **Pure regex/heuristic parsing with no LLM fallback.** Rejected — some steps require LLM judgment to classify; pure heuristics produce too many `narrative` misclassifications.

---

## ADR-007 — Scenes as the resumability boundary

**Status:** Accepted.

**Context.** Audit runs are long (hours for a full bootcamp sweep). Failures happen: auth expires, network drops, a portal hangs. The plugin must support resuming mid-run.

**Decision.** Checkpoint at every **scene boundary** (`####` heading in the lab markdown), not at every step. On resume, restart from the last completed scene.

**Consequences.**
- Worst-case lost work: one scene (typically 3–10 steps).
- Scenes start with a known navigation state — re-running them from scratch is safe.
- Individual clicks are not idempotent (clicking "Publish" twice creates two publishes); restarting at the step level would corrupt prior state.
- Findings from completed scenes are preserved across resumes.

**Alternatives considered.**
- **Step-level checkpointing.** Rejected — see "clicks not idempotent" above.
- **Lab-level checkpointing only.** Rejected — losing a whole lab's work on a mid-lab failure is too expensive for a 60-minute lab.

---

## ADR-008 — LLM judge per step + optional critique pass

**Status:** Accepted.

**Context.** The judgment "did this step do what the lab said?" is fundamentally semantic and requires comparing intent to observation. Pure-DOM-equality checks fail on dynamic UIs (every Copilot Studio session has different IDs). An LLM judge is the only viable approach.

**Decision.** Call an **LLM judge** after every executable step, passing verbatim instruction + accessibility snapshots before/after + screenshot + diagnostics. The judge returns strict JSON (`outcome`, `severity`, `confidence`, `suggested_correction`). An optional **critique pass** runs after the per-step judge on every non-pass finding, arguing for the opposite verdict to filter false positives.

**Consequences.**
- Cost: ~50–80 judge calls per lab × 11 labs ≈ 600–900 calls per full bootcamp run, plus ~10% for critique. The judge model uses the project's main Claude model; the action classifier uses a cheaper model.
- The judge is the failure mode most likely to produce false positives. The critique pass + confidence thresholds + the "lean toward `unclear` over `broken`" rubric in the prompt are all defenses against this.
- LLM unreliability is bounded: a transient judge failure causes one missed step, not a run-killing error.

**Alternatives considered.**
- **Strict DOM equality with the lab's expected screenshots.** Rejected — fragile, fails on every UI release.
- **Single-pass judge with no critique.** Rejected for non-deterministic and ambiguous cases — too many false positives.
- **Two-judge ensemble (two judges, take majority).** Rejected — doubles cost for marginal gain over critique pass.

---

## ADR-009 — Confidence-based filtering with low-confidence marker

**Status:** Accepted.

**Context.** The judge self-rates confidence (0.0–1.0). Different confidence levels need different treatments — high confidence wants the issue, low confidence wants a heads-up to the maintainer, very low confidence wants to be discarded entirely.

**Decision.** Three thresholds in `judge-config.yml`:
- `< 0.5` (default): logged locally, never sent to GitHub.
- `0.5 – 0.7`: included in the issue body but visually marked `(low confidence — please verify)`.
- `≥ 0.7`: included in the issue body as-is.

**Consequences.**
- Maintainers triaging issues see clear signal about which findings to trust vs. which to verify carefully.
- The lowest-confidence noise never reaches GitHub.
- Thresholds are configurable, so different teams can tune the noise/coverage trade-off without touching skills.

**Alternatives considered.**
- **Binary include/exclude at a single threshold.** Rejected — throws away the "almost certainly real, but worth a sanity check" middle band.
- **Don't surface confidence at all.** Rejected — the maintainer needs the signal.

---

## ADR-010 — Non-deterministic labs default to log-only

**Status:** Accepted.

**Context.** Some labs (`agent-builder-m365`, `mcs-multi-agent`) render LLM-generated UI that varies on every run. The judge will hallucinate `broken` findings for these unless given a different rubric.

**Decision.** Labs listed in `judge-config.yml.non_deterministic_lab_slugs` default to `--no-issue` mode (findings logged but not filed). The judge prompt uses a "shape-match" rubric (the right *kind* of thing is visible, not exact wording/screenshot match). Override per-run with `--force-issue` once the maintainer has tuned the rubric and trusts the output.

**Consequences.**
- Cautious default: less noise on the issues backlog, at the cost of finding fewer issues in those labs initially.
- The rubric difference lives in the judge prompt; no special handling in the orchestrator.
- The list is configuration, not code — new non-deterministic labs can be added without a plugin release.

**Alternatives considered.**
- **Skip those labs entirely.** Rejected — even non-deterministic labs can have hard-broken steps (e.g., a button rename); we want to find those.
- **Always file issues regardless.** Rejected for the false-positive reason above.

---

## ADR-011 — Single SSO state across all portals

**Status:** Accepted.

**Context.** The bootcamp labs target five Microsoft portals (Copilot Studio, M365 Copilot, Power Platform admin, Azure portal, SharePoint). The original design proposed per-portal auth-state capture after manual login per portal.

**Decision.** Sign in to **`login.microsoftonline.com`** once at run start and keep that Playwright MCP browser session alive across orchestrator/subagent boundaries. The shared authenticated session covers all five portals via AAD SSO federation.

**Consequences.**
- One sign-in flow instead of five.
- Matches how Microsoft accounts actually work in practice (AAD cascade).
- If a portal has a tenant-specific oddity that breaks the cascade, fall back to a portal-specific sign-in inside the relevant scene — exception, not rule.

**Alternatives considered.**
- **Per-portal auth-state export/import.** Rejected — over-engineered, and Playwright MCP does not expose `context.storageState()`.

---

## ADR-012 — Local-only audit log; never committed

**Status:** Accepted.

**Context.** The user wants a record of every audit run for tracking purposes. The log could live in the plugin's local `runtime/` directory, in the `mcs-labs` repo (as a committed YAML file), or in a separate "audit-logs" repo.

**Decision.** **Local-only.** The audit log lives at `runtime/audit-history.yml` inside this plugin's directory. It is appended to on every run and never leaves the local machine. `/audit-report` is the read interface.

**Consequences.**
- A fully-clean audit run produces **zero GitHub activity**.
- The user can grep, edit, or annotate the log freely without worrying about commits.
- No central visibility — each user has their own log. If team-wide visibility is needed later, a separate publish step could export selected entries; deferred.

**Alternatives considered.**
- **Commit to `microsoft/mcs-labs` as `_data/lab-audit-log.yml`.** Rejected — would require either committing for every run (noisy) or batching (cumbersome), and contradicts "no PR when nothing's wrong" if committed via PR.
- **Separate audit-logs repo.** Rejected — premature; one-user use case for now.

---

## ADR-013 — Issue de-duplication via label matching, loose-title fallback, and finding-fingerprint dedup

**Status:** Accepted (revised — see ADR-014 for the v0.2 hardening).

**Context.** Audit runs are recurring. If lab X stays broken across three audit runs, we should not open three identical issues, and re-runs should not re-post findings that the existing issue already covers.

**Decision.** Before any disposition decision, Phase 1.4 of the orchestrator queries `gh issue list` + `gh pr list` per slug and writes `runs/<run-id>/existing-state.yml`. The issue filer consults that file. Dedup runs as a **two-query union** to cover history:

1. Strict: `--label "lab-audit" --label "lab:<slug>"`.
2. Loose: `--label "lab-audit" --search "<slug> in:title"`.

If either returns a match, the filer **comments** on the most recent open issue with a fingerprint-deduped delta. Every rendered finding carries an HTML marker `<!-- finding:fp:<12-char-hex> -->`; on re-runs, fingerprints already present in the body or any prior comment are dropped. If every new finding is a duplicate, no comment is posted (`issue_action: skipped_no_new_findings`).

The historical `on_duplicate: "create_anyway"` config value is **deprecated** and silently coerced to `"comment"` — filing a second open issue is never an option.

**Consequences.**
- An issue per lab becomes a longitudinal thread, not a heap.
- Comments are deltas, not full re-renders — maintainers see only what's new since the last update.
- Closing the issue when fixed signals to the plugin that future findings should open a new issue.
- Issues filed before the per-slug label convention existed are still recognized via the loose-match query, and their `lab:<slug>` label is backfilled on the next comment.

**Alternatives considered.**
- **Issue de-duplication by title hash.** Rejected — title changes when finding counts shift; matching by stable label combo + slug-in-title is more robust.
- **Always open new issues.** Rejected for the obvious reason.
- **Full body re-render on every comment.** Rejected after observing duplicate-comment churn in early runs; fingerprint dedup keeps the thread readable.

---

## ADR-014 — Narrow open-PR append carve-out (screenshots only)

**Status:** Accepted (v0.2 addition).

**Context.** The original "issues only, no commits, no PRs" stance in ADR-001 was a deliberate safety property. But in practice, when a fix-PR for a lab is already open and a re-audit produces refreshed screenshots, the natural place for those screenshots is *that PR* — not a new branch, not a new PR, not yet another issue thread. Splitting screenshot updates across a stale PR + a fresh issue creates more work for the maintainer, not less.

**Decision.** Add a narrow, **default-on** carve-out: whenever Phase 1.4 found an open fix-PR for the lab AND the run produced screenshot files that map (by basename) to images already present under `labs/<slug>/images/`, invoke the new `mcs-lab-pr-appender` sub-skill. Users can suppress the carve-out per-run with `--no-update-screenshots` / `--no-append-to-pr`, or globally by setting `judge-config.yml.issues.pr_append.enabled_by_default: false`. The legacy positive flags (`--update-screenshots`, `--append-to-pr`) are still accepted as no-ops for backwards compatibility. The sub-skill:

- Verifies the PR is open, mergeable, authored by the current `gh` user, and not on a protected branch.
- Checks out the PR branch, replaces matched image files in place, commits with `chore({slug}): refresh screenshots from audit {run_id}`, pushes.
- Comments on the PR with a summary of the changed files.
- Restores the user's prior working state.

No new branches. No new PRs. No edits to markdown or any non-image file. No `Co-Authored-By: Claude` trailer. No force-push.

**Consequences.**
- Re-audits keep screenshots and prose edits together on one PR per lab.
- The "default read-only" safety property still holds for everything outside the screenshot scope.
- Each new guardrail is explicit and enumerated in `references/pr-append-flow.md` so a future contributor can't quietly broaden the carve-out without amending the docs.

**Alternatives considered.**
- **Open a separate "screenshot refresh" PR.** Rejected — produces clutter and contradicts the user's standing rule that we don't open new PRs for the same lab.
- **File screenshot drift as a separate issue.** Rejected — it's mechanical, not editorial; the value of an issue is the human discussion, which screenshot drift doesn't need.
- **Strictly opt-in append (positive flag required).** Considered initially and shipped in the first cut; revised to default-on at the user's request once the guardrails (same-author, mergeable, screenshots-only, no force-push) were confirmed sufficient to make accidental damage unlikely. The `--no-update-screenshots` opt-out preserves the read-only behavior for users who want it.

---

## ADR-014 — Plugin lives at user-level, not as marketplace plugin

**Status:** Accepted.

**Context.** Claude Code plugins can live in a marketplace (auto-installed, versioned, shared) or at the user level (one user's machine). Marketplace plugins are great for distribution but require additional manifest/release machinery.

**Decision.** **User-level plugin** at `~/.claude/plugins/mcs-lab-auditor/`, tracked by this Git repo. Users clone the repo into their plugins directory.

**Consequences.**
- Simpler distribution: `git clone` + restart Claude Code.
- Updates: `git pull`.
- No marketplace policy compliance work needed.
- Could be elevated to a marketplace plugin later if/when sharing broadens beyond this team.

**Alternatives considered.**
- **Publish to a marketplace.** Deferred until there's demand and the plugin's Windows-only-ness is resolved.

---

## Cross-references

- [`architecture.md`](architecture.md) — how these decisions compose at runtime.
- [`security.md`](security.md) — the security model (related to ADR-002).
- [`troubleshooting.md`](troubleshooting.md) — operational consequences of these decisions.
- [`extending.md`](extending.md) — how to extend without violating these decisions.
