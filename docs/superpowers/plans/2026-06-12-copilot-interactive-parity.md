# Copilot CLI Interactive Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the plugin's live-browser audit/build phase work in GitHub Copilot CLI with zero extra setup, without changing the proven Claude Code path.

**Architecture:** Ship a Copilot-only Playwright MCP server in the plugin (`.github/mcp.json`, which Claude Code does not scan), make the skills reference the browser tools by their bare `@playwright/mcp` action names with a per-host naming reference (`host-tools.md`), and add a browser-MCP preflight that falls back to `--static-only` when no browser is available. Claude keeps using its existing `playwright@claude-plugins-official` prerequisite untouched.

**Tech Stack:** Markdown skills/commands/references, JSON manifests (`.github/mcp.json`, `plugin.json`, `marketplace.json`), YAML config, GitHub Copilot CLI (`copilot` 1.0.60), `@playwright/mcp`, PowerShell, python-pptx (deck).

Full spec: `docs/superpowers/specs/2026-06-12-copilot-interactive-parity-design.md`.

---

## Decisions locked (from the spec)

1. **Claude path untouched** — keep the `mcp__plugin_playwright_playwright__*` tool names and the separately-installed `playwright@claude-plugins-official` prerequisite. Only *add* Copilot support.
2. **Ship the Copilot Playwright MCP in the plugin** at `.github/mcp.json` (Copilot reads plugin MCP from `.mcp.json` or `.github/mcp.json`; Claude does NOT scan `.github/`, so no duplicate server appears in Claude). Use `--isolated`.
3. **Hybrid tool references** — bare action names + `host-tools.md` + a browser-MCP preflight with `--static-only` fallback. No brittle env-based host detection.

---

## File structure

**Created:**
- `.github/mcp.json` — Copilot-provided `playwright` MCP server (`npx -y @playwright/mcp@latest --isolated`). ~10 lines.
- `skills/mcs-lab-auditor/references/host-tools.md` — per-host browser-tool naming + the "use what your host exposes" rule. ~40 lines.

**Modified:**
- `skills/mcs-lab-auditor/references/playwright-cookbook.md` — Tool-mapping table → bare action names + pointer to `host-tools.md`.
- `skills/mcs-lab-auditor/SKILL.md` — browser-MCP preflight + `--static-only` fallback; `allowed-tools` comment; host-agnostic note on the inline tool mentions.
- `skills/mcs-lab-builder/SKILL.md` — browser-MCP preflight + halt-with-guidance fallback; `allowed-tools` comment.
- `commands/audit-account.md` — host-agnostic pointer for the redemption browser flow.
- `README.md`, `docs/installation.md`, `docs/extending.md`, `docs/architecture.md`, `docs/troubleshooting.md`, `docs/design-decisions.md` (new ADR), `CONTRIBUTING.md` — Copilot now supports the interactive phase.
- `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `config/judge-config.yml` — version 0.8.0.

**Separate artifact (not in the repo):**
- `C:\Users\dewainr\projects\plugin-capabilities-deck\build_deck.py` + the rendered deck copied to `C:\Users\dewainr\Downloads\mcs-lab-auditor-capabilities.pptx`.

---

## Phase 1 — Ship the Copilot Playwright MCP

### Task 1: Add `.github/mcp.json`

**Files:**
- Create: `.github/mcp.json`

- [ ] **Step 1: Create `.github/mcp.json`**

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest", "--isolated"]
    }
  }
}
```

- [ ] **Step 2: Validate it is well-formed JSON**

Run:
```powershell
pwsh -NoProfile -Command "Get-Content .github/mcp.json -Raw | ConvertFrom-Json | ForEach-Object { $_.mcpServers.playwright.command + ' ' + ($_.mcpServers.playwright.args -join ' ') }"
```
Expected: `npx -y @playwright/mcp@latest --isolated`

- [ ] **Step 3: Confirm Claude Code will NOT pick this up**

Run:
```powershell
pwsh -NoProfile -Command "Test-Path .mcp.json; (Get-Content .claude-plugin/plugin.json -Raw | ConvertFrom-Json).PSObject.Properties.Name -contains 'mcpServers'"
```
Expected: `False` then `False` — there is no root `.mcp.json` and no `mcpServers` key in `plugin.json`, so Claude Code has no plugin-MCP source; the server lives only in `.github/mcp.json` (Copilot-only). (Live Copilot/Claude verification happens in Task 9.)

- [ ] **Step 4: Commit**

```powershell
git add .github/mcp.json
git commit -m "Ship Copilot-only Playwright MCP server for the interactive phase"
```

---

## Phase 2 — Host-agnostic tool references

### Task 2: Create `host-tools.md`

**Files:**
- Create: `skills/mcs-lab-auditor/references/host-tools.md`

- [ ] **Step 1: Create the reference**

```markdown
# Browser tools across hosts (Claude Code & Copilot CLI)

The interactive phase drives a real browser through a **Playwright MCP server**.
The plugin runs in two hosts that namespace MCP tools differently — but the
underlying `@playwright/mcp` **action names are identical**; only the prefix
differs.

## The rule

**Use the browser tool your host actually exposes.** Look at your available tool
list and call the `browser_*` action by whatever fully-qualified name your host
gives it. Do not hard-code one host's prefix.

## Per-host naming

| Host | Browser MCP source | Tool name shape |
|---|---|---|
| **Claude Code** | the `playwright@claude-plugins-official` plugin (prerequisite) | `mcp__plugin_playwright_playwright__<action>` |
| **GitHub Copilot CLI** | the `playwright` server bundled in this plugin (`.github/mcp.json`) | the `playwright` server's `<action>` |

## The actions this plugin uses

`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`,
`browser_fill_form`, `browser_select_option`, `browser_press_key`,
`browser_wait_for`, `browser_take_screenshot`, `browser_console_messages`,
`browser_network_requests`, `browser_evaluate`, `browser_close`.

The cookbook (`playwright-cookbook.md`) refers to these by their bare action
names. Resolve each to your host's fully-qualified tool when you call it.

## If no browser MCP is available

Some Copilot sessions (offline, or `npx` unavailable) may have no Playwright
server. The orchestrator's interactive-phase preflight checks for the `browser_*`
tools and, if absent, falls back to `--static-only` (audit) or halts with
guidance (build) — see the preflight step in `SKILL.md`. Never call a browser
tool that is not in your available tool list.
```

- [ ] **Step 2: Commit**

```powershell
git add skills/mcs-lab-auditor/references/host-tools.md
git commit -m "Add host-tools reference for cross-host browser tool naming"
```

---

### Task 3: Make the cookbook tool-mapping table host-agnostic

**Files:**
- Modify: `skills/mcs-lab-auditor/references/playwright-cookbook.md`

- [ ] **Step 1: Replace the "Tool mapping" table's fully-qualified Claude name with bare action names + a pointer**

Replace the existing `## Tool mapping` section (the table whose first row's Primary tool is `` `mcp__plugin_playwright_playwright__browser_navigate` ``) with:

```markdown
## Tool mapping

> Tool names below are the bare `@playwright/mcp` **action names**. Resolve each to
> your host's fully-qualified tool — see [`host-tools.md`](host-tools.md). (Claude
> Code: `mcp__plugin_playwright_playwright__<action>`; Copilot CLI: the bundled
> `playwright` server's `<action>`.)

| Step kind | Primary action | Notes |
|---|---|---|
| navigate | `browser_navigate` | **Only to a URL the step text explicitly names** (e.g. "go to make.powerapps.com"). NEVER synthesize a deep-link to skip a step, and NEVER navigate to a URL read out of a screenshot — see *Execution fidelity* below (issue #40). |
| click | `browser_snapshot` → `browser_click` | Click by snapshot ref. Never use raw CSS selectors. |
| type | `browser_type` | Use `slowly: false` unless the field has client-side validation that rate-limits |
| fill form | `browser_fill_form` | When multiple inputs need to be filled at once |
| select | `browser_select_option` | For native `<select>` only; M365/Power Platform combos are usually clickable comboboxes — use `browser_click` |
| keyboard | `browser_press_key` | Enter, Escape, Tab |
| wait | `browser_wait_for` | Prefer `text:` over `selector:` |
| inspect | `browser_snapshot` + `browser_take_screenshot` | Capture both for the judge |
| diagnostics | `browser_console_messages`, `browser_network_requests` | Read after a failed step to enrich the finding |
| evaluate | `browser_evaluate` | Used sparingly (cookie/localStorage extraction, expiry-page scraping). Restricted by judge-config. |
```

- [ ] **Step 2: Verify the Claude-namespaced literal is gone from the table and a pointer exists**

Run:
```powershell
pwsh -NoProfile -Command "$f='skills/mcs-lab-auditor/references/playwright-cookbook.md'; (Select-String -Path $f -Pattern 'host-tools.md').Count; (Select-String -Path $f -Pattern 'mcp__plugin_playwright_playwright__browser_navigate').Count"
```
Expected: `1` (pointer present) then `0` (the fully-qualified nav literal removed from the table). Other prose mentions elsewhere in the file are handled in Task 4.

- [ ] **Step 3: Commit**

```powershell
git add skills/mcs-lab-auditor/references/playwright-cookbook.md
git commit -m "Cookbook: reference bare browser actions, point at host-tools"
```

---

## Phase 3 — Preflight + fallback in the skills

### Task 4: Orchestrator preflight + fallback (`mcs-lab-auditor/SKILL.md`)

**Files:**
- Modify: `skills/mcs-lab-auditor/SKILL.md`

- [ ] **Step 1: Read the interactive-phase boundary**

Open `skills/mcs-lab-auditor/SKILL.md` and locate the pre-flight / sign-in region (the step that establishes the signed-in Playwright browser session, near the "keep signed-in MCP browser session active" text) and the `allowed-tools` block (lines ~16–28).

- [ ] **Step 2: Add a browser-MCP preflight block immediately before the first browser navigation / sign-in**

Insert this markdown at the interactive-phase boundary (before any `browser_*` call / sign-in):

```markdown
#### Browser-MCP preflight (before any interactive step)

The interactive phase needs a Playwright MCP. Tool names differ per host — see
[`references/host-tools.md`](references/host-tools.md). Before the first browser
action:

1. Check your available tools for the Playwright `browser_*` actions (Claude:
   `mcp__plugin_playwright_playwright__*`; Copilot: the bundled `playwright`
   server). 
2. **If present** → proceed with the interactive phase, calling each action by
   its host-qualified name.
3. **If absent** → do NOT call a browser tool. Fall back to `--static-only` for
   this run and tell the user how to enable the browser for their host:
   - Claude Code: enable the `playwright@claude-plugins-official` MCP plugin.
   - Copilot CLI: the plugin bundles a `playwright` MCP (`.github/mcp.json`); it
     needs `npx` + network on first use. Run `copilot mcp list` to confirm it
     loaded.
```

- [ ] **Step 3: Annotate the `allowed-tools` Playwright block with a host note**

Directly above the first `- mcp__plugin_playwright_playwright__browser_navigate`
line (line ~16), add a YAML comment:

```yaml
  # Claude Code browser tools (playwright@claude-plugins-official). Copilot CLI
  # exposes the same @playwright/mcp actions under its bundled `playwright`
  # server — see references/host-tools.md. Copilot ignores unknown entries.
```

- [ ] **Step 4: Make the inline prose tool mentions host-agnostic**

For each inline mention of the Claude-namespaced tool in prose (around lines ~543,
~609, ~729 — e.g. "calls `mcp__plugin_playwright_playwright__*`",
"`mcp__plugin_playwright_playwright__browser_close`"), append "` (or your host's
browser tool — see references/host-tools.md)`" on first occurrence in each
section. Keep the Claude literal (it is correct for Claude); just add the pointer.

- [ ] **Step 5: Verify**

Run:
```powershell
pwsh -NoProfile -Command "$f='skills/mcs-lab-auditor/SKILL.md'; 'preflight: '+((Select-String -Path $f -Pattern 'Browser-MCP preflight').Count); 'host-tools refs: '+((Select-String -Path $f -Pattern 'host-tools.md').Count); 'static-only fallback: '+((Select-String -Path $f -Pattern 'static-only').Count)"
```
Expected: `preflight: 1`, `host-tools refs: 3` or more, `static-only fallback: 1` or more.

- [ ] **Step 6: Commit**

```powershell
git add skills/mcs-lab-auditor/SKILL.md
git commit -m "Orchestrator: browser-MCP preflight + host-agnostic tool refs"
```

---

### Task 5: Builder preflight + fallback (`mcs-lab-builder/SKILL.md`)

**Files:**
- Modify: `skills/mcs-lab-builder/SKILL.md`

- [ ] **Step 1: Locate the builder's first browser use (B2 navigate-home) and its `allowed-tools` block**

Open `skills/mcs-lab-builder/SKILL.md`; find the B2 "navigate to Copilot Studio Home" step and the `allowed-tools` Playwright entries.

- [ ] **Step 2: Insert the same preflight, with a build-mode fallback**

Immediately before B2's first browser action, insert:

```markdown
#### Browser-MCP preflight (build mode needs the live product)

Build mode authors a lab by driving the real product, so a Playwright MCP is
required — tool names differ per host (see
[`../mcs-lab-auditor/references/host-tools.md`](../mcs-lab-auditor/references/host-tools.md)).
Before B2:

1. Check your available tools for the Playwright `browser_*` actions.
2. **If present** → proceed, calling each by its host-qualified name.
3. **If absent** → **halt** with a clear message (build mode cannot run
   static-only). Tell the user to enable the browser MCP for their host — Claude:
   `playwright@claude-plugins-official`; Copilot: the bundled `playwright` server
   (`copilot mcp list` to confirm; needs `npx` + network on first use).
```

- [ ] **Step 3: Annotate the builder `allowed-tools` Playwright block**

Add the same YAML comment as Task 4 Step 3 above the builder's first
`mcp__plugin_playwright_playwright__*` `allowed-tools` entry.

- [ ] **Step 4: Verify**

Run:
```powershell
pwsh -NoProfile -Command "$f='skills/mcs-lab-builder/SKILL.md'; 'preflight: '+((Select-String -Path $f -Pattern 'Browser-MCP preflight').Count); 'host-tools refs: '+((Select-String -Path $f -Pattern 'host-tools.md').Count)"
```
Expected: `preflight: 1`, `host-tools refs: 1` or more.

- [ ] **Step 5: Commit**

```powershell
git add skills/mcs-lab-builder/SKILL.md
git commit -m "Builder: browser-MCP preflight + host-tools pointer"
```

---

### Task 6: Redemption browser flow (`commands/audit-account.md`)

**Files:**
- Modify: `commands/audit-account.md`

- [ ] **Step 1: Add a host-tools pointer where redemption drives the browser**

In `commands/audit-account.md`, find the redemption section that uses the
Playwright browser (the `mcp__plugin_playwright_playwright__*` references). Add a
single sentence near the first such reference:

```markdown
> Account redemption drives the browser too. Browser tool names differ per host —
> use the Playwright `browser_*` action your host exposes (see
> `skills/mcs-lab-auditor/references/host-tools.md`).
```

Keep the existing Claude-namespaced references (correct for Claude); just add the
pointer. Do not remove anything.

- [ ] **Step 2: Verify**

Run:
```powershell
pwsh -NoProfile -Command "(Select-String -Path commands/audit-account.md -Pattern 'host-tools.md').Count"
```
Expected: `1` or more.

- [ ] **Step 3: Commit**

```powershell
git add commands/audit-account.md
git commit -m "audit-account: host-agnostic browser tool pointer for redemption"
```

---

## Phase 4 — Documentation (across the board)

### Task 7: Update all docs for Copilot interactive support

**Files:**
- Modify: `README.md`, `docs/installation.md`, `docs/extending.md`, `docs/architecture.md`, `docs/troubleshooting.md`, `docs/design-decisions.md`, `CONTRIBUTING.md`

Apply this canonical fact set consistently: *Copilot CLI now supports the
interactive (live-browser) phase via a plugin-bundled Playwright MCP
(`.github/mcp.json`, `npx -y @playwright/mcp@latest --isolated`); browser tool
names are host-specific and documented in
`skills/mcs-lab-auditor/references/host-tools.md`; an interactive-phase preflight
falls back to `--static-only` (audit) or halts (build) when no browser MCP is
present; the Claude Code path is unchanged (still uses
`playwright@claude-plugins-official`). Version 0.8.0.*

- [ ] **Step 1: `README.md`** — In the Copilot/installation and Limitations areas, change any "Copilot = static-only / interactive is Claude-only" wording to: the interactive phase runs in Copilot via the bundled Playwright MCP (zero-config); browser tool names resolve per host via `host-tools.md`. Note the `npx`/network-on-first-use caveat and the static-only fallback.

- [ ] **Step 2: `docs/installation.md`** — In the "Option B — GitHub Copilot CLI" / caveats section, replace the "interactive phase won't run — use `--static-only`" caveat with: install via `copilot plugin install mcs-lab-auditor@BootcampLabTestPlugin`; the bundled `playwright` MCP enables the interactive phase (`copilot mcp list` to confirm; first use runs `npx`). Keep the DPAPI-Windows note.

- [ ] **Step 3: `docs/extending.md`** — In "Adapting to a different workshop portal" / any Copilot mention, add that browser tool naming is host-specific and centralized in `host-tools.md`, and that adding a different browser MCP means updating `.github/mcp.json` (Copilot) and/or the Claude prerequisite.

- [ ] **Step 4: `docs/architecture.md`** — Add a short note in the components/resolver area: the interactive phase uses a Playwright MCP whose tool names are host-specific (`host-tools.md`); Copilot's server ships in `.github/mcp.json`; a preflight gates the interactive phase with a static-only fallback.

- [ ] **Step 5: `docs/troubleshooting.md`** — Add an entry: **"Interactive phase doesn't run in Copilot CLI"** → run `copilot mcp list` to confirm the `playwright` server loaded; it needs `npx` + network on first use; if unavailable the run falls back to `--static-only`. Add **"Browser tool not found / wrong tool name"** → see `host-tools.md`; use the `browser_*` tool your host exposes.

- [ ] **Step 6: `docs/design-decisions.md`** — Add a new ADR (next number after the current highest — verify; expected **ADR-025**) titled "Copilot CLI interactive parity via a bundled Playwright MCP." Match the existing ADR format (Status / Context / Decision / Alternatives / Consequences). Capture: the two-host tool-naming problem; the decision (Copilot-only `.github/mcp.json` + bare action names + `host-tools.md` + preflight/fallback; Claude untouched); alternatives rejected (unify both hosts onto one MCP; env-based host detection with a hardcoded map); consequences (`npx`/network on first Copilot use; `--isolated` required; static-only fallback). Cross-reference the lab-instances ADR if one references repo/runtime resolution.

- [ ] **Step 7: `CONTRIBUTING.md`** — In the project layout / dev-setup, mention `.github/mcp.json` (Copilot Playwright MCP) and `host-tools.md`; note that browser tool references must stay host-agnostic (bare action names).

- [ ] **Step 8: Verify the static-only-only caveat is gone from user docs**

Run:
```powershell
pwsh -NoProfile -Command "Get-ChildItem README.md,docs/installation.md,docs/extending.md -ErrorAction SilentlyContinue | Select-String -Pattern \"won't run|Claude Code when you need the interactive\" | ForEach-Object { $_.Filename + ':' + $_.LineNumber }"
```
Expected: no lines that still say the interactive phase can't run in Copilot (only the graceful static-only *fallback* wording remains).

- [ ] **Step 9: Commit**

```powershell
git add README.md docs/ CONTRIBUTING.md
git commit -m "Docs: Copilot CLI now supports the interactive phase (bundled Playwright MCP)"
```

---

## Phase 5 — Version bump

### Task 8: Bump to 0.8.0 + CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `config/judge-config.yml`

- [ ] **Step 1: Add a `## [0.8.0]` CHANGELOG entry**

Add above the most recent released section (date `2026-06-12`), Keep a Changelog format:
- `### Added` — Copilot CLI interactive-phase support: bundled Playwright MCP (`.github/mcp.json`); `host-tools.md` cross-host browser-tool reference; interactive-phase browser-MCP preflight with `--static-only` (audit) / halt (build) fallback.
- `### Changed` — `playwright-cookbook.md` tool-mapping table now uses bare `@playwright/mcp` action names; skill `allowed-tools` annotated; docs updated; Claude Code path unchanged.
- Move any `## [Unreleased] > Documentation` items as appropriate and add the `[0.8.0]` compare link at the bottom.

- [ ] **Step 2: Bump the three version locations**

Replace `"version": "0.7.0"` → `"version": "0.8.0"` in `.claude-plugin/plugin.json` (line 3) and `.claude-plugin/marketplace.json` (line 13); replace `plugin_version: "0.7.0"` → `plugin_version: "0.8.0"` in `config/judge-config.yml` (line ~277).

- [ ] **Step 3: Verify version consistency**

Run:
```powershell
pwsh -NoProfile -Command "(Select-String -Path .claude-plugin/plugin.json,.claude-plugin/marketplace.json,config/judge-config.yml -Pattern '0\.8\.0' | Measure-Object).Count"
```
Expected: `3`

- [ ] **Step 4: Commit**

```powershell
git add CHANGELOG.md .claude-plugin/plugin.json .claude-plugin/marketplace.json config/judge-config.yml
git commit -m "Release 0.8.0: Copilot CLI interactive parity"
```

---

## Phase 6 — Verification

### Task 9: Install in Copilot, smoke-test the browser, regress Claude

**Files:** none (verification only)

- [ ] **Step 1: Reinstall the plugin in Copilot from the branch/latest and confirm the MCP loads**

> Note: the marketplace install pulls `origin/main`. To test the branch before merge, either use `copilot plugin install microsoft/BootcampLabTestPlugin` after pushing the branch as a PR/temp ref, or test post-merge. For local validation, `--plugin-dir` can load the working tree.

Run (post-merge or via `--plugin-dir`):
```powershell
copilot plugin marketplace update BootcampLabTestPlugin
copilot plugin update mcs-lab-auditor@BootcampLabTestPlugin
copilot mcp list
```
Expected: `copilot mcp list` includes a `playwright` server (from the plugin).

- [ ] **Step 2: Bounded live browser smoke in Copilot (no portal account)**

Run:
```powershell
copilot -p "Using the Playwright browser tools, navigate to https://example.com, take a snapshot, and tell me the page's main heading text. Do nothing else." --allow-all-tools -s
```
Expected: Copilot uses the bundled `playwright` server's `browser_navigate` + `browser_snapshot` and reports "Example Domain". This proves the bare action names resolve in Copilot.

- [ ] **Step 3: Claude Code regression**

In a Claude Code session, confirm the tool list still shows `mcp__plugin_playwright_playwright__*` and that there is **no** second Playwright server, and run an existing dry-run:
```
/audit-lab core-concepts-analytics-evaluations --dry-run
```
Expected: parses to `steps.json` as before; no change in Playwright tooling.

- [ ] **Step 4: Repo grep sweep**

Run:
```powershell
pwsh -NoProfile -Command "Get-ChildItem -Recurse -File skills,commands -Include *.md | Select-String -Pattern 'mcp__plugin_playwright_playwright__' | Where-Object { $_.Line -notmatch 'host-tools|allowed|or your host' } | ForEach-Object { $_.Filename + ':' + $_.LineNumber } | Select-Object -First 20"
```
Expected: remaining matches are only the `allowed-tools` entries and annotated prose — every cookbook/instruction tool reference is either bare or points at `host-tools.md`.

- [ ] **Step 5: Record results** (no commit unless a fix was needed)

---

## Phase 7 — Update the capabilities deck

### Task 10: Reflect Copilot interactive parity + 0.8.0 in the PowerPoint

**Files:**
- Modify: `C:\Users\dewainr\projects\plugin-capabilities-deck\build_deck.py`
- Output: re-render and copy to `C:\Users\dewainr\Downloads\mcs-lab-auditor-capabilities.pptx`

- [ ] **Step 1: Update the "Portable & self-maintaining" slide (slide 08)**

In `build_deck.py`, the GitHub Copilot CLI host box currently reads
"static-only when no browser MCP". Change it to reflect interactive parity, e.g.
"bundled Playwright MCP → interactive too" and adjust the chips/footer to mention
the host-aware browser tools + static-only *fallback*. Update the title-slide
version token `v0.7.0` → `v0.8.0`.

- [ ] **Step 2: Rebuild and re-render**

Run:
```powershell
Set-Location "C:\Users\dewainr\projects\plugin-capabilities-deck"
python build_deck.py
# render via PowerPoint COM (as before) and visually confirm the changed slide
```

- [ ] **Step 3: Copy the updated deck to Downloads**

```powershell
Copy-Item "C:\Users\dewainr\projects\plugin-capabilities-deck\mcs-lab-auditor-capabilities.pptx" "C:\Users\dewainr\Downloads\mcs-lab-auditor-capabilities.pptx" -Force
```

- [ ] **Step 4: Visually verify** the changed slide(s) render cleanly (no overflow), as in the original deck build.

---

## Notes for the implementer

- **Do not remove** any `mcp__plugin_playwright_playwright__*` reference — Claude needs them. Only add host-agnostic pointers / annotations.
- The bundled MCP file MUST be `.github/mcp.json` (Copilot reads it; Claude ignores `.github/`). If Task 9 shows Copilot didn't load it, the fallback is the other plugin-MCP filename Copilot reads — but re-verify Claude still ignores it before committing.
- `--isolated` is mandatory in the shipped config (issue #39 identity isolation).
- Commit after every task; never squash phases.
- The deck (Phase 7) is a separate artifact in Downloads — the user explicitly asked for it to be updated; do it after the repo work.
