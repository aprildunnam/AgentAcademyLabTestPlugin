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
