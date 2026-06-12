# Copilot CLI Interactive Parity — Design

**Date:** 2026-06-12
**Status:** Approved for planning
**Target version:** 0.8.0 (minor — new capability, backward compatible)

## Problem

The plugin installs and is discovered in GitHub Copilot CLI (6 skills, v0.7.0), and
its **static** path (markdown parsing, link/image checks, cross-lab consistency,
`gh` issue/fix-PR filing, the resolver scripts) works there because Copilot
provides `CLAUDE_PLUGIN_ROOT` and runs standard shell/PowerShell.

But the **interactive (live-browser) phase** — the core of audit and build mode —
does not work in Copilot, for two reasons:

1. **No browser MCP.** Copilot has no Playwright MCP configured (only `workiq`).
2. **Claude-specific tool names.** The skills and `playwright-cookbook.md`
   reference Claude Code's namespaced Playwright tools
   (`mcp__plugin_playwright_playwright__browser_*`) in ~43 places. Copilot
   identifies MCP tools by `(serverName, toolName)` and exposes them under a
   different prefix, so those literal names never resolve there.

The underlying `@playwright/mcp` action names (`browser_navigate`, `browser_click`,
`browser_snapshot`, …) are **identical across hosts** — only the host's
namespacing prefix differs.

## Goal

The interactive browser phase works in GitHub Copilot CLI with **zero extra
setup**, **without changing the proven Claude Code path**.

## Decisions (locked during brainstorming)

1. **Leave the Claude Code Playwright path untouched.** Claude keeps using its
   existing prerequisite — the separately-installed `playwright@claude-plugins-official`
   MCP and the `mcp__plugin_playwright_playwright__*` tool names. We only *add*
   Copilot support alongside it.
2. **Ship the Copilot Playwright MCP inside the plugin (zero-config),** in a
   config location Claude Code does not read, so no second Playwright server
   appears in the Claude tool list.
3. **Host-agnostic tool references via the hybrid approach (Approach 3):** bare
   `@playwright/mcp` action names + a concise host-tools reference + a
   browser-MCP preflight with a `--static-only` fallback.

## Design

### 1. Ship a Copilot Playwright MCP (zero-config)

Add a plugin-shipped MCP manifest declaring a `playwright` server:

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

- `--isolated` gives a fresh in-memory browser profile that does not inherit the
  operator's OS account broker / cookies — satisfying the cookbook's
  identity-isolation requirement (issue #39) on both hosts.
- **Target file:** `.github/mcp.json` — Copilot loads plugin-provided MCP servers
  from `.mcp.json` or `.github/mcp.json`; Claude Code does **not** scan `.github/`
  for plugin MCP, so the Claude tool list is unaffected.
- **Implementation must verify** post-install that `copilot mcp list` shows the
  `playwright` server AND that a Claude Code session's tool list is unchanged (no
  duplicate Playwright server). If Copilot turns out not to read `.github/mcp.json`
  for plugin MCP, fall back to the filename Copilot *does* read, chosen so Claude
  Code still ignores it (preserving Decision 1).

### 2. Host-agnostic tool references (Approach 3)

**New `skills/mcs-lab-auditor/references/host-tools.md`** — the single place that
explains browser-tool naming across hosts. It contains:

- The list of `@playwright/mcp` actions the plugin uses: `browser_navigate`,
  `browser_snapshot`, `browser_click`, `browser_type`, `browser_fill_form`,
  `browser_select_option`, `browser_press_key`, `browser_wait_for`,
  `browser_take_screenshot`, `browser_console_messages`, `browser_network_requests`,
  `browser_evaluate`, `browser_close`.
- The per-host prefix:
  - **Claude Code:** `mcp__plugin_playwright_playwright__<tool>`
  - **Copilot CLI:** the bundled `playwright` MCP server's `<tool>`
- The rule: **use the browser tool your host actually exposes — check your
  available tool list; the action names are identical, only the prefix differs.**

**Edit `playwright-cookbook.md`** — change the "Tool mapping" table from the
fully-qualified Claude name to **bare action names** (`browser_navigate`, etc.)
with a one-line pointer to `host-tools.md`. The rest of the cookbook already uses
abbreviated `_browser_*` references and needs no change.

### 3. Browser-MCP preflight + fallback

At the interactive-phase boundary, the orchestrator (`mcs-lab-auditor/SKILL.md`)
and the builder (`mcs-lab-builder/SKILL.md`) add an explicit preflight:

- Confirm a browser MCP is available (the host exposes the `browser_*` tools).
- **Present →** proceed with the interactive phase.
- **Absent →** *audit mode* falls back to `--static-only` with a clear message;
  *build mode* halts with guidance. The message names how to enable the browser
  per host (Claude: enable `playwright@claude-plugins-official`; Copilot: the
  bundled MCP needs `npx`/network on first run).

This makes the no-browser case graceful in either host instead of failing on an
unresolved tool call.

### 4. `allowed-tools` frontmatter

Keep the existing Claude `mcp__plugin_playwright_playwright__*` entries in the
skill frontmatter — Claude needs them, and Copilot already tolerates unknown
`allowed-tools` entries (it installed all 6 skills with no error). Add a short
comment pointing to `host-tools.md`. No entries are removed (avoids regressing the
Claude path).

### 5. Documentation

- `README.md`, `docs/installation.md`, `docs/extending.md`: upgrade the
  "Copilot = static-only" caveat to "the interactive phase is supported in Copilot
  via the bundled Playwright MCP (zero-config)." Document `.github/mcp.json`, the
  `host-tools.md` reference, and the preflight/fallback.
- `CHANGELOG.md`: a `0.8.0` entry (Keep a Changelog).

### 6. Versioning

Bump `0.7.0 → 0.8.0` in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
and `config/judge-config.yml` (`plugin_version`).

## Error handling

- **No browser MCP** → `--static-only` fallback (§3); never a hard failure on an
  unresolved tool call.
- **`@playwright/mcp` not yet fetched on first Copilot run** → `npx -y` fetches it;
  if offline, the preflight reports it and falls back to static-only.
- **Identity bleed** → `--isolated` is mandatory in the shipped config and remains
  required for the Claude prerequisite (unchanged).

## Testing

1. **Copilot MCP load:** after `copilot plugin install mcs-lab-auditor@BootcampLabTestPlugin`,
   `copilot mcp list` shows the `playwright` server.
2. **Live browser smoke (Copilot, no portal account):** a bounded non-interactive
   `copilot -p` run that navigates to a public page and takes a snapshot — proves
   the bare tool names resolve to Copilot's `playwright` server.
3. **Claude regression:** a Claude Code session's tool list still shows the
   `playwright@claude-plugins-official` tools and **no** duplicate Playwright
   server; an existing `/audit-lab <slug> --dry-run` still works.
4. **Full portal audit** stays the existing manual A/B/C verification (requires a
   live workshop account) — out of scope for automated testing here.

## Out of scope (YAGNI)

- Unifying both hosts onto a single Playwright MCP (explicitly rejected — keeps the
  Claude path stable).
- Deterministic env-based host detection with a hardcoded per-host tool-name table
  (Approach 2 — rejected as brittle).
- Supporting browser MCPs other than `@playwright/mcp`.
