# Design decisions

This document enumerates the major architectural choices made when building `mcs-lab-auditor` and the rationale behind each. It is loosely ADR-style: each entry has a status, context, decision, consequences, and alternatives that were considered and rejected.

When proposing a change to the plugin's shape, check whether your change affects an existing decision — if so, update that decision's status (e.g., to `superseded by ADR-N`) rather than silently changing behavior.

---

## ADR-001 — Plugin scope: GitHub issues, not pull requests

**Status:** Superseded in part — see ADR-014 (screenshots carve-out) and ADR-015 (fix-PR per run). The plugin now also opens/append fix-PRs; issues remain the primary, always-on path.

**Context.** The plugin needs to surface lab problems back to the maintainers of `microsoft/mcs-labs`. The two obvious paths are (a) opening a PR with proposed edits to `_labs/<slug>.md` for each finding, or (b) filing a GitHub issue with suggested corrections in the body, leaving application to a human.

**Decision.** File **GitHub issues**. One issue per lab with findings. Suggested corrections appear in the issue body as `diff`-style blocks but are never applied as edits.

**Consequences.**
- The plugin writes to `microsoft/mcs-labs` through **three narrow paths**: the Issues API (always on); a fix-PR per audit run that applies the suggested corrections — opened on a run-unique branch, or appended to the lab's existing open fix-PR (ADR-015); and a screenshots-only commit appended to an already-open fix-PR (default on; opt out per-run with `--no-update-screenshots`, ADR-014). It never force-pushes and never opens a second *open* PR for a lab that already has one.
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
- Re-audits keep screenshots and prose edits together on the lab's open PR (when one is open) rather than splitting them across a new PR + a fresh issue.
- The "default read-only" safety property still holds for everything outside the screenshot scope.
- Each new guardrail is explicit and enumerated in `references/pr-append-flow.md` so a future contributor can't quietly broaden the carve-out without amending the docs.

**Alternatives considered.**
- **Open a separate "screenshot refresh" PR.** Rejected — produces clutter and contradicts the user's standing rule that we don't open new PRs for the same lab.
- **File screenshot drift as a separate issue.** Rejected — it's mechanical, not editorial; the value of an issue is the human discussion, which screenshot drift doesn't need.
- **Strictly opt-in append (positive flag required).** Considered initially and shipped in the first cut; revised to default-on at the user's request once the guardrails (same-author, mergeable, screenshots-only, no force-push) were confirmed sufficient to make accidental damage unlikely. The `--no-update-screenshots` opt-out preserves the read-only behavior for users who want it.

---

## ADR-015 — Fix-PR per audit run; PR dedup scoped to OPEN PRs only

**Status:** Accepted (v0.3 addition).

**Context.** ADR-014 and the original `mcs-lab-fix-pr-filer` design keyed everything to a single, fixed per-slug branch `{branch_prefix}/fix-{slug}-content-audit` and an explicit "one PR per lab, never open a new PR" rule. That rule is wrong once time passes: prior fix-PRs get **merged**. A later audit run that finds new problems must be able to open a **new** PR — reusing the same fixed branch name as a just-merged PR is fragile (leftover local/remote branches, wrong base, confusing history), and "never open a new PR" would mean new findings have nowhere to land except the issue thread.

The user's standing rule (`feedback_fresh_branch_per_pr`) is the opposite: never commit to a branch whose PR is merged/closed; always open a fresh branch + new PR. The only thing dedup should prevent is **two open PRs for the same lab at once**.

**Decision.** Make the fix-PR filer's disposition **open-PR-scoped**:

1. Find whether an *open* fix-PR for the slug exists — via the Phase 1.4 `existing-state.yml.labs[<slug>].open_pr` probe, or a direct `gh pr list --state open --search "head:<prefix>"` query (head-ref **prefix** match, so it finds the PR regardless of its run-id suffix), with a title-match fallback.
2. **If an open PR exists** and it's authored by the current `gh` user and mergeable → `gh pr checkout` it and **append** this run's commit. Never open a second open PR. If the author/mergeable guardrail fails, abort the PR step (soft failure) rather than opening a competitor.
3. **If no open PR exists** (none ever, or all prior ones merged/closed) → open a **new** PR on a **run-unique** branch `{branch_prefix}/fix-{slug}-content-audit-{run_id}`. The `{run_id}` suffix guarantees the branch can't collide with a merged PR's leftover branch, so no stale-branch rename/delete dance is needed.

Two config keys replace the single fixed pattern: `issues.pr_append.pr_branch_pattern` (now `{branch_prefix}/fix-{slug}-content-audit-{run_id}`, the **create** name) and `issues.pr_append.pr_match_head_prefix` (`{branch_prefix}/fix-{slug}-content-audit`, the **match** prefix). The `{branch_prefix}` token is sourced from the active lab instance (`dewain` for the shipped `mcs-labs` instance) — see ADR-024.

**Consequences.**
- Each audit run with fresh findings produces its own reviewable PR; a merged PR from a prior cycle never silently swallows or blocks new fixes.
- At most one *open* fix-PR per lab at a time — re-audits of a still-open PR append rather than duplicate.
- The screenshots-only appender (ADR-014) is unchanged; it remains the lighter path for refreshing images on an already-open PR.

**Alternatives considered.**
- **Keep the fixed per-slug branch, delete the stale branch before re-creating.** Rejected — fragile around leftover branches and races; a run-unique name sidesteps the whole class of problems.
- **Always open a new PR even when one is open.** Rejected — produces competing open PRs for one lab and undoes the dedup property the user wants.
- **Leave the open PR untouched and only comment on the issue.** Rejected — splits a run's fixes away from the open PR the maintainer is already reviewing.

---

## ADR-016 — Plugin distribution (renumbered; was a duplicate ADR-014)

**Status:** Accepted (revised). Originally "user-level plugin only"; the plugin is now **also distributed as a marketplace plugin** (`mcs-lab-auditor@BootcampLabTestPlugin`).

**Context.** Claude Code plugins can live in a marketplace (auto-installed, versioned, shared) or at the user level (one user's machine). Marketplace plugins are great for distribution but require additional manifest/release machinery. (This entry was originally numbered ADR-014, colliding with the screenshots carve-out ADR; renumbered to ADR-016 for uniqueness.)

**Decision.** Ship via the **`BootcampLabTestPlugin` marketplace** with a `.claude-plugin/marketplace.json`; the plugin is installed into the versioned cache (`~/.claude/plugins/cache/BootcampLabTestPlugin/mcs-lab-auditor/<version>`). A direct **git clone into `~/.claude/plugins/mcs-lab-auditor/`** remains supported as the development/edit path (and is what `installation.md` documents). `.claude-plugin/plugin.json` and `marketplace.json` carry the version in lockstep.

**Consequences.**
- Updating an installed copy is a marketplace refresh (or `git pull` + re-sync of the cache for the clone path); `runtime/` is gitignored so cached account and history survive.
- Two install shapes coexist: marketplace cache (distribution) and direct clone (development). Keep their versions aligned.

**Alternatives considered.**
- **User-level clone only (the original decision).** Superseded — a marketplace makes versioned distribution and updates cleaner now that the plugin is shared beyond a single machine.

---

## ADR-017 — Interactive lab-building mode with an audit gate

**Status:** Accepted (v0.4.0 addition).

**Context.** The plugin could only *audit* existing labs. Authoring a new lab was still a manual, error-prone process: click through Copilot Studio, screenshot each step, hand-write the markdown, and hope it matches the live UI. The plugin already has all the pieces needed to do this well — a workshop account flow, a driven browser, an LLM judge that compares written instructions to live UI, and the lab markdown format.

**Decision.** Add a second mode (`/build-lab` → `mcs-lab-builder`) that authors a new lab interactively, then **re-runs the finished lab through the existing audit engine as a quality gate** before opening a PR. The gate runs the auditor's per-UC judge loop but **suppresses all GitHub writes** (`build.audit_gate.suppress_github_writes`) — findings are consumed *in-loop* (each above-threshold `broken`/`unclear` finding loops back into the capture loop for a fix) instead of being filed as issues/PRs. The gate passes only when zero above-threshold findings remain (capped at `build.audit_gate.max_loops`).

**Consequences.**
- A built lab is verified against the live UI by the same judge that audits existing labs — the lab can't ship with steps that don't actually work.
- The audit engine gains a non-GitHub invocation path; the judge/finding machinery stays disposition-agnostic (only the disposition step differs between modes).
- Build mode confirms **every** step with the user (both interaction modes), trading speed for authoring accuracy.

**Alternatives considered.**
- **Author the markdown without re-driving the UI.** Rejected — defeats the plugin's core value (catching written-vs-live drift) at the moment it matters most.
- **Reuse the issue/PR filers to record gate findings.** Rejected — gate findings are an authoring feedback loop, not a maintainer-facing report; filing them would create noise and a chicken-and-egg PR.

---

## ADR-018 — New-lab PR as a separate sub-skill, not an extension of the fix-PR filer

**Status:** Accepted (v0.4.0 addition).

**Context.** Build mode ends by opening a PR that adds a whole new lab. The plugin already has `mcs-lab-fix-pr-filer`, which opens/append PRs for audit *fixes*.

**Decision.** Add a dedicated `mcs-lab-new-lab-pr` sub-skill rather than overloading the fix-PR filer. A new lab is a one-shot PR (folder + registration entry + generated/`_labs` output) on a run-unique branch `{branch_prefix}/new-lab-{slug}-{build_id}` off fresh `origin/main`; it has no `suggested_correction` diffs and no open-PR-append/dedup semantics.

**Consequences.**
- Each filer keeps a crisp contract: fix-filer patches an existing lab from findings diffs with OPEN-PR dedup; new-lab filer adds a lab with no dedup (re-builds get a fresh `build_id` → fresh branch).
- Branches off fresh `origin/main` (the mcs-labs clone is often on a feature branch), stashes/restores unrelated work, and never adds AI attribution.

**Alternatives considered.**
- **Extend `mcs-lab-fix-pr-filer` with a "new lab" branch.** Rejected — muddies its findings-diff + open-PR-dedup model with an unrelated code path.

---

## ADR-019 — Build and audit are event/workshop-agnostic

**Status:** Accepted (v0.4.0 addition; generalizes ADR-005).

**Context.** Despite the repo name "BootcampLabTestPlugin" and `/audit-bootcamp`, neither auditing nor building should be limited to the bootcamp event. A lab exists independently of any event; events are an optional grouping.

**Decision.** Build mode (and its audit gate) operate on a lab **standalone**. A built lab is registered with `section` / `journeys` / `order` (all event-independent); attaching it to one or more events/workshops is an optional B3 choice, and the available events are read dynamically from `_data/lab-config.yml` — never hardcoded to bootcamp. Audit mode already supports any event (`/audit-event --event <key>`) and any single lab (`/audit-lab <slug>`).

**Consequences.**
- New events on the mcs-labs side need no plugin change.
- The default for a built lab is "no event attachment" (standalone), keeping the diff minimal and leaving event wiring to maintainers unless explicitly requested.

**Alternatives considered.**
- **Default new labs into the bootcamp order.** Rejected — bakes in a bootcamp-centric assumption the user explicitly rejected.

---

## ADR-020 — Runtime registration-mechanism detection + mcs-labs path resolution

**Status:** Accepted (v0.4.0 addition).

**Context.** `mcs-labs/docs/NEW_LAB_CHECKLIST.md` documents registering a lab by editing a root `lab-config.yml` and running `scripts/Generate-Labs.ps1`. As of v0.4.0 **neither file exists** in the mcs-labs repo (feature branch or `origin/main`) — only the generated `_data/lab-config.yml` remains, with a stale "DO NOT EDIT" header. Separately, the repo moved out of the old hardcoded `C:\Users\dewainr\mcs-labs` to `…\Projects\mcs-labs`.

**Decision.** Build mode **detects the registration mechanism at runtime** (B0): if a root `lab-config.yml` + generator exist, use the generate flow; otherwise fall back to **direct writes** of `labs/<slug>/README.md` + `_labs/<slug>.md` + the `_data/lab-config.yml` entry (the same direct-`_labs` editing the fix-PR filer already does). Genuinely ambiguous cases halt and ask rather than guess. The mcs-labs repo path is **resolved** from `build.registration.mcs_labs_repo_path_candidates` (first existing wins), not hardcoded.

**Consequences.**
- The plugin survives the upstream toolchain drift instead of failing mid-PR.
- The draft is always preserved under `runtime/builds/<build-id>/`, so a halt loses no work.
- Audit-side commands still carry the legacy hardcoded path; aligning them on the same resolution is tracked as a follow-up.

**Alternatives considered.**
- **Assume the documented generator exists.** Rejected — it doesn't; that would fail every build at registration.
- **Always write `_data/lab-config.yml` directly without detection.** Rejected — if the generator returns upstream, hand-editing generated output would be wrong; detection keeps both paths correct.

---

## ADR-021 — Build mode opens an "In Progress" proposal issue up front

**Status:** Accepted (v0.5.0 addition).

**Context.** A new lab takes a while to author interactively, and the team needs visibility that a lab is being built before its PR appears — to avoid two people building the same lab, and to track proposals through a lifecycle.

**Decision.** At B3.5 (right after the lab is named), build mode opens a tracking issue on `microsoft/mcs-labs` labeled **`type: new-lab`** + **`status: in-progress`** — the repo's *existing* label taxonomy, not new labels. The issue is deduped per slug (reuses an existing open proposal rather than duplicating), reused on `--resume`, recorded in `manifest.proposal_issue`, and **closed by the B7 lab PR** (`Closes #<n>`, configurable to `Refs`). Governed by `build.proposal_issue`.

**Consequences.**
- A new lab is visible as *In Progress* for the entire build, not just when the PR lands.
- Build mode now makes **two** intentional GitHub writes (proposal issue + PR); the audit gate still writes nothing (`build.audit_gate.suppress_github_writes`).
- Reuses the repo's label vocabulary, so proposals sit alongside existing `type:`/`status:` triage automation with no new labels to create.
- Under `--no-pr` or an aborted build, the proposal issue remains open as *In Progress* for a human to pick up or close.

**Alternatives considered.**
- **Open the issue only at PR time (B7).** Rejected — defeats the "visible while in progress" goal; the issue and PR would appear together.
- **Invent a dedicated `new lab proposal` / `In Progress` label.** Rejected — the repo already has `type: new-lab` ("Brand new lab proposal") and `status: in-progress`; reusing them avoids label sprawl and fits existing triage.
- **Track via a GitHub Projects board status field.** Deferred — requires a project ID + GraphQL and `read:project`/`project` scopes; labels are portable and need no extra auth. Could be layered on later via config.

---

## ADR-022 — Events vs workshops: collections are the source of truth

**Status:** Accepted (v0.6.0 addition; generalizes ADR-005 / ADR-019).

**Context.** The mcs-labs repo split its curated scopes into two Jekyll collections: `_events/<id>.md` for formal, curated event experiences (bootcamp, agent-buildathon-1day, agent-buildathon-1month) and `_workshops/<id>.md` for on-demand workshops (azure-ai-workshop, mcs-in-a-day, agent-in-a-day, the Agent Academy recruit/operative/commander tracks). Both share one front-matter schema — `title`, `description`, `event_id`, `order`, and a `labs:` list of `{ slug, label }` — with an optional richer agenda at `_data/agendas/<id>.yml`. Meanwhile the plugin's original scope source, the legacy `_data/lab-config.yml.event_configs` table, **drifted out of sync**: it lacks agent-in-a-day and the academy workshops and still lists an obsolete `mcs-in-a-day-v2`. Continuing to read `event_configs` would silently miss real scopes and offer dead ones.

**Decision.** Enumerate the scope catalog from the **`_events/` + `_workshops/` collections** via a new `scripts/Get-EventCatalog.ps1`. For each scope it emits `type` (event|workshop), `id`, `title`, `description`, `order`, `external`, `external_url`, `repository`, `auditable`, and the `labs[]` slug list — events first, then workshops, each ordered by `order` then `id`. **Events and workshops are both first-class audit scopes.** Scopes flagged `external: true` (the Agent Academy tracks, whose labs live in `microsoft/agent-academy`) are **listed for awareness but `auditable: false`** — never driven end-to-end. The legacy `event_configs` table is demoted to a **last-resort fallback only**. The single-lab picker still reads `lab_metadata.*` from `lab-config.yml` — that part is unchanged.

**Consequences.**
- New events/workshops added on the mcs-labs side (a `_events/` or `_workshops/` file with a `labs:` list) appear in the plugin with no code change.
- The picker reflects the real, current scope set instead of the drifted legacy table; obsolete entries (mcs-in-a-day-v2) disappear and missing ones (agent-in-a-day, the academy tracks) appear.
- External scopes are visible but can't be falsely "audited" — the catalog marks them non-auditable rather than failing mid-run when their labs aren't in this repo.
- Two source surfaces now matter: the collections (scope catalog) and `lab_metadata` (all-labs single-lab catalog). The legacy `event_configs` table remains only as a defensive fallback for repos that predate the collections.

**Alternatives considered.**
- **Keep reading `event_configs`.** Rejected — it has demonstrably drifted; the collections are now the repo's source of truth.
- **Merge the two collections into one "scopes" surface in the plugin.** Rejected — the event/workshop distinction is meaningful to users and is carried as a `type` tag rather than flattened away.
- **Drop `event_configs` support entirely.** Deferred — keeping it as a last-resort fallback costs nothing and protects against an older mcs-labs checkout that lacks the collections.

---

## ADR-023 — Portable paths: dynamic repo resolution + plugin self-version check

**Status:** Accepted (v0.6.0 addition; supersedes the audit-side hardcoded path in ADR-020). Extended by ADR-024, which makes the labs-repo target itself configurable per named instance.

**Context.** The plugin shipped with hard-coded machine paths — `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor` for plugin files, `~/.claude/plugins/mcs-lab-auditor/...` SKILL read-paths, and `C:\Users\dewainr\mcs-labs` for the labs repo (audit mode hard-coded it; build mode had only a partial candidate list). On any other contributor's machine these broke, requiring manual per-machine path edits. There was also **no update awareness**: a run could execute on a stale local copy without the user knowing a newer version existed.

**Decision.** Three changes make the plugin portable and update-aware:

1. **Plugin files via `$env:CLAUDE_PLUGIN_ROOT`.** Every `C:\Users\dewainr\.claude\plugins\mcs-lab-auditor` and every `~/.claude/plugins/mcs-lab-auditor/...` SKILL read-path is replaced with `$env:CLAUDE_PLUGIN_ROOT`. No machine-specific plugin path remains.
2. **mcs-labs repo via `scripts/Resolve-LabRepo.ps1`.** Resolution order: `$env:MCS_LABS_REPO` → `judge-config.yml.build.registration.mcs_labs_repo_path_candidates` → built-in candidates under `%USERPROFILE%` → if none found, **clone** `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs`; then **fast-forward to `origin/main`** so audits always run against the latest lab content. This applies to **both** audit and build modes (previously only build mode had partial candidate resolution; audit mode hard-coded the path).
3. **Self-version check via `scripts/Test-PluginVersion.ps1`.** As Phase 1 step 1 (and a pre-flight line in every command), it compares local `.claude-plugin/plugin.json` against the version published on `origin/main` of `microsoft/BootcampLabTestPlugin` (`.claude-plugin/marketplace.json`) using `gh api`. Best-effort and **non-blocking**: it warns when an update is available, recommends `/plugin` to update, and is skipped silently when `gh` is unavailable or offline.

**Consequences.**
- The plugin works on any contributor's machine with **no per-machine path edits**; the obsolete "Step 5b: adjust hard-coded paths" install step is gone.
- Audits always run against current lab content (auto-clone + fast-forward), and against a known-current plugin version (or a visible warning if not).
- A new dependency on `git` at the labs-repo-resolution boundary (for the auto-clone + fast-forward) — degraded gracefully: a stale local copy is preferred over a hard failure when the network or `git` is unavailable.
- The version check is one more `gh` call per run, but cheap and silently skipped when `gh` can't reach the published manifest.

**Alternatives considered.**
- **Keep per-machine path edits documented in installation.** Rejected — every new contributor hit the same setup friction, and the edits drifted from the docs.
- **Require a manual clone of mcs-labs before first run.** Rejected — auto-clone removes a setup step and guarantees the repo is present and current; users who want a specific clone still override via `MCS_LABS_REPO` or the candidates list.
- **Block the run when an update is available.** Rejected — a hard block on a best-effort network check would strand offline users; a non-blocking warning preserves the run while still nudging the update.

---

## ADR-024 — Configurable lab instances (user-overlay registry)

**Status:** Accepted (v0.7.0 addition; extends ADR-023's labs-repo resolution).

**Context.** Before v0.7.0 the lab target was effectively hardcoded to `microsoft/mcs-labs` and the bootcamp training portal. The repo slug, git clone URL, local path candidates, PR/branch author prefix (`dewain/`), and the workshop portal URL were scattered across `config/judge-config.yml`, `scripts/Resolve-LabRepo.ps1`, and `config/workshop.yml`. A user wanting to audit a fork of `mcs-labs` with their own training portal had no sanctioned path: they had to edit plugin files directly, and those edits were clobbered every time the plugin updated from the marketplace cache.

**Decision.** Introduce named **lab instances**. A lab instance bundles the following fields into a single named entry: `repo` (owner/name slug), `clone_url`, `marker` (the file whose presence confirms a valid checkout; default `_data/lab-config.yml`), `path_candidates` (ordered list of local paths to try before auto-cloning), `branch_prefix` (for fix-PRs and new-lab branches), and a training `portal` (either an inline block or a `portal_file` path). The resolution lifecycle is:

1. **Shipped registry** — `config/lab-instances.yml` is bundled with the plugin and defines the built-in `mcs-labs` instance. The key `default_instance: mcs-labs` makes it the active instance when nothing else is specified.
2. **User-owned overlay** — `%USERPROFILE%\.mcs-lab-auditor\lab-instances.yml` is loaded on top of the shipped registry; user-supplied fields win per field. This file lives outside the plugin cache directory and therefore **survives plugin updates**.
3. **Instance selection** — active instance is resolved in priority order: `--instance <name>` flag → `$env:LAB_INSTANCE` environment variable → `default_instance` key → shipped `mcs-labs` fallback.
4. **`scripts/Resolve-LabInstance.ps1`** is the single source of truth for the merge, selection, and field resolution. It resolves `branch_prefix` (instance value → `gh api user` login → left unresolved) and the portal (inline block or loaded from `portal_file`), then emits JSON consumed by every downstream caller.

Downstream integration: `Resolve-LabRepo.ps1` sources clone URL, marker, path candidates, and the per-instance managed-clone path (`%USERPROFILE%\.mcs-lab-auditor\<instance-name>`) from `Resolve-LabInstance.ps1`'s output; `judge-config.yml`, the skills, and the commands use `{repo}` and `{branch_prefix}` tokens; and at run start the active portal is materialized to `runtime/account/active-portal.yml` (for the default `mcs-labs` instance this equals `config/workshop.yml` verbatim, so no behavioral change).

**Consequences.**
- Custom instances require the `powershell-yaml` module for YAML merging. The default `mcs-labs` path continues to work without it via graceful fallback in `Resolve-LabRepo.ps1` (it re-uses its pre-v0.7.0 resolution logic when no user overlay is present).
- Each instance gets an isolated managed clone under `%USERPROFILE%\.mcs-lab-auditor\<instance-name>` so a custom fork's clone never collides with the built-in mcs-labs clone.
- Fully backward compatible — a user with zero overlay config targets `microsoft/mcs-labs` exactly as before; no migration step is required.
- The mcs-labs-specific built-in candidate paths (enumerated in `config/lab-instances.yml`) are only searched when the active instance is `mcs-labs`, preventing a custom instance from accidentally resolving to an unrelated mcs-labs checkout.
- See `docs/examples/lab-instances.sample.yml` for an annotated user overlay example, and `docs/extending.md#targeting-your-own-lab-fork` for the end-to-end walkthrough.

**Alternatives considered.**
- **Edit a single global config in place.** Rejected — the plugin cache (`~/.claude/plugins/cache/BootcampLabTestPlugin/mcs-lab-auditor/<version>`) is overwritten on every marketplace update; any in-place edit would be silently lost.
- **One environment variable per configurable field.** Rejected — unwieldy to set for multi-field customization, and provides no support for defining and switching between multiple named instances.
- **JSON instead of YAML for the user overlay.** Rejected — JSON does not support comments, which are important for a hand-maintained configuration file where explaining each field's purpose inline is practical and expected.
- **Minimal "repo-only" parameterization keeping a single global portal.** Rejected — a fork of `mcs-labs` must be able to point at its own training portal; sharing the portal config from the built-in instance would cause a custom fork to redeem workshop codes against the wrong portal and receive credentials for the wrong tenant.

---

## Cross-references

- [`architecture.md`](architecture.md) — how these decisions compose at runtime.
- [`security.md`](security.md) — the security model (related to ADR-002).
- [`troubleshooting.md`](troubleshooting.md) — operational consequences of these decisions.
- [`extending.md`](extending.md) — how to extend without violating these decisions.
