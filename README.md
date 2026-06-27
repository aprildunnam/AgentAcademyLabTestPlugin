# AgentAcademyLabTestPlugin

A Copilot CLI / Claude Code plugin that **tests Agent Academy labs end-to-end** by driving a real browser through each lab's instructions via Playwright MCP.

**Source content:** [microsoft.github.io/agent-academy](https://microsoft.github.io/agent-academy/) (repo: `microsoft/agent-academy`)

## How it works

1. **Opens a browser** and navigates to Copilot Studio
2. **You sign in** to your M365 account manually (no automated credentials, no workshop codes)
3. **Walks through every step** of the selected lab using Playwright
4. **Judges each step** — compares what the lab says should happen vs what actually happens in the live UI
5. **Reports findings** — which steps pass, which are broken (UI diverged from instructions), which are unclear

## Commands

| Command | Purpose |
|---|---|
| `/test-lab [<course>/<slug>]` | Test a single lab interactively |
| `/test-course [<course>]` | Test all interactive labs in a course sequentially |

### Available courses

| Course | Labs | Description |
|---|---|---|
| `recruit` | 13 lessons (10 interactive) | Copilot Studio fundamentals — building your first agent |
| `operative` | 11 lessons (all interactive) | Advanced agent building — instructions, multi-agent, triggers, MCP |
| `special-ops` | 5 labs | Specialized integrations — MCP servers, YAML, Docusign |
| `cowork-collective` | 3 labs | Real-world agent scenarios — badge check, compliance, OOO |

### Examples

```bash
# Test a specific lab
/test-lab recruit/04-creating-a-solution

# Test the entire Recruit course
/test-course recruit

# Dry-run to see parsed steps without running the browser
/test-lab operative/01-get-started --dry-run
```

## Key differences from the original mcs-labs auditor

| Feature | Original (mcs-labs) | This version (Agent Academy) |
|---|---|---|
| Content source | `microsoft/mcs-labs` (Jekyll) | `microsoft/agent-academy` (VitePress) |
| Authentication | Automated workshop code redemption + DPAPI-cached credentials | Manual M365 sign-in in browser |
| Environment setup | Workshop portal chatbot flow | You use your own M365 tenant |
| Output | GitHub issues + fix PRs on mcs-labs | Local test reports (markdown) |
| Dependencies | PowerShell scripts, Windows-specific DPAPI | Cross-platform (Playwright MCP only) |

## Prerequisites

- **Copilot CLI** or **Claude Code** with Playwright MCP enabled
- **M365 account** with access to Copilot Studio (any tenant with appropriate licenses)
- **Node.js** (for `npx @playwright/mcp`)

The plugin ships a `.github/mcp.json` that auto-configures Playwright MCP — no manual setup needed.

## Installation

The plugin works in both **Claude Code** and **GitHub Copilot CLI**.

```text
# Install from the repository
/plugin install aprildunnam/AgentAcademyLabTestPlugin
```

## Architecture

```
.claude-plugin/plugin.json     — Plugin identity
.github/mcp.json               — Playwright MCP server config
config/
  agent-academy-config.yml     — Course catalog + auth config
  judge-config.yml             — LLM judge thresholds + model config
commands/
  test-lab.md                  — /test-lab command
  test-course.md               — /test-course command
skills/
  agent-academy-tester/
    SKILL.md                   — Main orchestration skill
    references/
      lab-parser-spec.md       — How to parse VitePress markdown into steps
      playwright-cookbook.md    — Portal navigation + Playwright patterns
      llm-judge-prompts.md     — Judge, critique, and classifier prompts
      finding-schema.md        — Test result structure
```

## How the LLM judge works

For each lab step, after execution:

1. **Captures** an accessibility snapshot + screenshot of the page state
2. **Compares** what the lab instruction says should happen vs what actually happened
3. **Renders a verdict**: `pass`, `broken`, `unclear`, `non_deterministic`, `transient`, or `cannot_verify`
4. **For broken/unclear steps**: a second-pass critique reviews the finding to reduce false positives
5. **Reports** all findings with confidence scores and suggested corrections

## License

MIT
