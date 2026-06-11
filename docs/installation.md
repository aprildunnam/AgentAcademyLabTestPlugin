# Installation

Step-by-step setup for `mcs-lab-auditor`. If you hit problems, jump to [Troubleshooting](#troubleshooting) at the bottom of this page or see [`troubleshooting.md`](troubleshooting.md) for failure modes after install.

## Prerequisites

| Requirement | Why | How to check |
|---|---|---|
| **Windows 10 or 11** | DPAPI credential caching is Windows-only | `winver` |
| **PowerShell 7+** | Used by the workshop-redemption flow and `audit-account` | `pwsh -v` (or `$PSVersionTable.PSVersion` inside PowerShell) |
| **Git** | To clone this plugin and `microsoft/mcs-labs` | `git --version` |
| **GitHub CLI (`gh`)** authenticated with an account that can file issues on `microsoft/mcs-labs` (and **open PRs**, for fix-PRs and build mode) | The plugin's GitHub write path. `READ` is insufficient. | `gh auth status` and `gh repo view microsoft/mcs-labs --json viewerPermission` |
| **Claude Code** (Desktop, CLI, or IDE) | Hosts the plugin | Run Claude Code; check version in About/help |
| **Playwright MCP plugin enabled in Claude Code** | Drives the browser | In Claude Code: confirm `mcp__plugin_playwright_playwright__*` tools are listed in a `/tools` or equivalent command, or that `playwright@claude-plugins-official` appears in `~/.claude/settings.json` under enabled plugins |
| **A local clone of `microsoft/mcs-labs`** *(optional — auto-cloned if missing)* | The plugin reads lab markdown, the `_events/` + `_workshops/` collections, and `_data/lab-config.yml` from it | Not required up front: `scripts/Resolve-LabRepo.ps1` resolves an existing clone or clones one into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs` at run start. See [Repo resolution](#repo-resolution-no-path-edits-needed). |
| **An unredeemed workshop code** | One per audit run, used during `/audit-account redeem` | Obtained from your workshop organizer; expires after one redemption |

- **PowerShell module `powershell-yaml`** (only needed if you define custom lab
  instances; the resolver errors with this exact command if it is missing):

  ```powershell
  Install-Module powershell-yaml -Scope CurrentUser -Force
  ```

> Heads-up: workshop accounts typically expire within 24–48 hours. Don't redeem the code days before you intend to start an audit run.

## Step 1 — Install `gh` and authenticate

If you don't already have `gh`:

```powershell
winget install --id GitHub.cli -e
```

Authenticate:

```powershell
gh auth login
```

Pick **GitHub.com**, **HTTPS**, **Login with a web browser**, and follow the prompts. Once done:

```powershell
gh auth status                              # confirm logged in
gh repo view microsoft/mcs-labs --json viewerPermission
```

The `viewerPermission` should be `TRIAGE`, `WRITE`, `MAINTAIN`, or `ADMIN`. `READ` is insufficient to file issues — request triage access from the `microsoft/mcs-labs` maintainers if needed.

## Step 2 — Clone the labs repo (optional)

**You can skip this step.** At run start the plugin resolves the mcs-labs repo automatically and, if no local clone is found, clones `microsoft/mcs-labs` into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs` and fast-forwards it to `origin/main` — there are no hard-coded paths to adjust. See [Repo resolution](#repo-resolution-no-path-edits-needed) for the full resolution order and the `MCS_LABS_REPO` override.

If you'd rather clone it yourself (e.g. you already have a working tree you edit), put it anywhere on a built-in candidate path — `%USERPROFILE%\Projects\mcs-labs` is tried first:

```powershell
git clone https://github.com/microsoft/mcs-labs.git "$env:USERPROFILE\Projects\mcs-labs"
```

Verify the lab config is readable:

```powershell
Test-Path "$env:USERPROFILE\Projects\mcs-labs\_data\lab-config.yml"   # should print True
```

## Step 3 — Install the plugin

The plugin is a directory of markdown commands, skills, references, and YAML config — no compiled artifacts. Both **Claude Code** and **GitHub Copilot CLI** auto-discover plugins from their respective user-plugins directories; install via `git clone` into the right place.

### Option A — Claude Code (primary, fully tested)

Clone into the Claude Code user-plugins directory:

```powershell
git clone https://github.com/microsoft/BootcampLabTestPlugin "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
```

Confirm the install layout:

```powershell
Get-ChildItem "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor" | Select-Object Name
# expected: .claude-plugin, .gitignore, CHANGELOG.md, CODE_OF_CONDUCT.md,
#           CONTRIBUTING.md, LICENSE, README.md, SECURITY.md, commands,
#           config, docs, runtime, scripts, skills
```

### Option B — GitHub Copilot CLI

The plugin uses the same skill-discovery model as Claude Code (one `Skill`/`skill` tool, plugins auto-discovered from a known directory), so the install pattern is the same — clone into the Copilot CLI plugins directory. The exact directory depends on your Copilot CLI version and platform; find it with `copilot --help` (look for the *plugins* or *extensions* section) or by checking `copilot config get plugins.path` if your version supports it. Then:

```powershell
# Example - confirm $copilotPluginsPath against `copilot --help` output first
git clone https://github.com/microsoft/BootcampLabTestPlugin (Join-Path $copilotPluginsPath "mcs-lab-auditor")
```

Caveats for Copilot CLI:

- The plugin no longer hard-codes any machine paths: it reads its own files via `$env:CLAUDE_PLUGIN_ROOT` and resolves the mcs-labs repo via `scripts/Resolve-LabRepo.ps1`. If your Copilot CLI host doesn't set `CLAUDE_PLUGIN_ROOT`, export it to the plugin's install directory before launching, and (optionally) set `MCS_LABS_REPO` to point at your labs clone. See [`docs/extending.md`](extending.md#pointing-at-a-different-lab-repo).
- Workshop-portal redemption uses Playwright via the Claude Code Playwright MCP plugin. If your Copilot CLI session doesn't have an MCP server providing equivalent `mcp__plugin_playwright_playwright__*` tools, the interactive phase won't run — use `--static-only` for doc-audit sweeps and fall back to Claude Code when you need the interactive phase.
- DPAPI credential storage is Windows-only regardless of which runtime invokes the skill.

### Both at once

Symlink or hardlink the second directory at the first so the plugin lives in one place but both runtimes see it:

```powershell
# Run as elevated PowerShell if creating a directory symlink
New-Item -ItemType SymbolicLink `
  -Path (Join-Path $copilotPluginsPath "mcs-lab-auditor") `
  -Target "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
```

## Step 4 — Restart your runtime

Plugins are discovered at session start. Close Claude Code (or end your Copilot CLI session) completely and reopen. After it's back up, type `/` in the prompt and look for:

- `/audit-event` (generic — picks the workshop event interactively)
- `/audit-bootcamp` (shortcut for `/audit-event --event bootcamp`)
- `/audit-lab` (single lab — with or without a slug)
- `/audit-report`
- `/audit-account`
- `/build-lab` (interactively build a **new** lab and open a PR — v0.4.0+)

If those don't appear, see [Troubleshooting](#troubleshooting).

## Step 5 — Configure the workshop portal

Open `config/workshop.yml`:

```powershell
notepad "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor\config\workshop.yml"
```

Replace the placeholder:

```yaml
workshop_portal_url: "REPLACE_ME_ON_FIRST_RUN"
```

…with your actual workshop event URL (you'll get this from whoever distributed your workshop code).

Optionally, set a tenant label that will appear in audit logs:

```yaml
tenant_hint: "your-workshop-label-here"
```

If your workshop portal isn't Skillable-style (i.e. doesn't display credentials on a confirmation page), also adjust `redemption_selectors` — see [`extending.md`](extending.md#adapting-to-a-different-workshop-portal).

### Repo resolution (no path edits needed)

> **There is nothing to edit here.** As of v0.6.0 the plugin has **no hard-coded machine paths** — the old "Step 5b: adjust hard-coded paths" procedure is obsolete and has been removed. Both audit and build modes resolve the mcs-labs repo at run start via `scripts/Resolve-LabRepo.ps1`, and all plugin-internal reads use `$env:CLAUDE_PLUGIN_ROOT`.

The resolver tries these in order and uses the first that contains `_data/lab-config.yml`:

1. **`$env:MCS_LABS_REPO`** — set this if you want to force a specific clone:
   ```powershell
   [Environment]::SetEnvironmentVariable("MCS_LABS_REPO", "D:\src\mcs-labs", "User")
   # then restart Claude Code so the session picks it up
   ```
2. **`mcs_labs_repo_path_candidates`** in `config/judge-config.yml` — add your clone path (use doubled backslashes) to have it preferred over the built-ins.
3. **Built-in candidates** under `%USERPROFILE%`: `Projects\mcs-labs`, `mcs-labs`, `source\repos\mcs-labs`, `.mcs-lab-auditor\mcs-labs`.
4. **Auto-clone** — if none of the above exist, `microsoft/mcs-labs` is cloned into `%USERPROFILE%\.mcs-lab-auditor\mcs-labs`.

Once resolved, the repo is fast-forwarded to `origin/main` (unless it's checked out on a non-`main` branch), so audits always run against the latest lab content. To verify resolution at any time:

```powershell
pwsh "$env:CLAUDE_PLUGIN_ROOT\scripts\Resolve-LabRepo.ps1" -Mode Status
# e.g. "mcs-labs: C:\Users\you\Projects\mcs-labs [pulled]"
```

## Step 6 — Cache a test account

Get a fresh workshop code from your workshop organizer, then in Claude Code:

```text
/audit-account redeem
```

The plugin will:
1. Open the workshop portal in Playwright.
2. Prompt you for the code.
3. Submit and scrape the issued credentials.
4. Sign in to `login.microsoftonline.com` to capture session cookies.
5. Encrypt the credential blob via Windows DPAPI and write `runtime/account/credential.enc`.

If everything worked, you'll see:

```
Cached test account: <user_id> (expires <expires_at>).
```

Verify:

```text
/audit-account show
```

## Step 7 — Smoke-test the parser

The cheapest verification — no browser activity, no auth, just exercises the markdown parser:

```text
/audit-lab core-concepts-analytics-evaluations --dry-run
```

You should see a confirmation that `steps.json` was written. Open it:

```powershell
notepad "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor\runtime\runs\<run-id>\labs\core-concepts-analytics-evaluations\steps.json"
```

The use-case → scene → step tree should match the lab's outline (open `_labs/core-concepts-analytics-evaluations.md` to compare).

## Step 8 — Full single-lab run

Once `--dry-run` looks right:

```text
/audit-lab core-concepts-analytics-evaluations
```

This drives the browser through the entire lab. Expect 5–10 minutes. The plugin will either:

- Append a clean-pass entry to `runtime/audit-history.yml` and print a success summary; or
- File a single GitHub issue against `microsoft/mcs-labs` (one issue total for all findings in this lab), with the URL printed in the summary.

## Step 9 — Full event sweep (when ready)

Once one single-lab run looks correct end-to-end, you can audit a whole event or workshop. The Architecture Bootcamp is the default — but any scope in the `_events/` or `_workshops/` collections works (events and workshops are both first-class):

```text
/audit-bootcamp                              # shortcut: event = bootcamp
/audit-event --event agent-buildathon-1month # any other event by key
/audit-event                                 # generic — interview picks the event
```

Expect 3–8 hours for the bootcamp's 11 labs (other events vary by lab count). The plugin checkpoints at every scene boundary; if it dies mid-run, you can resume:

```text
/audit-bootcamp --resume <run-id>
/audit-event --resume <run-id>     # if the run was a non-bootcamp event
```

(The `<run-id>` is printed at the start of each run and recorded in `runtime/runs/<run-id>/manifest.yml`. Resume inherits the prior run's `event`, `phase_mix`, and `scope_labs`.)

---

## Building a new lab (`/build-lab`, v0.4.0+)

Build mode authors a brand-new lab end-to-end and opens a PR adding it to `microsoft/mcs-labs`. It reuses the same cached workshop account, so Steps 6 (cache a test account) and the `gh` PR permission above are the only prerequisites.

```text
/build-lab "Build a Returns Triage Agent"          # full build → audit gate → PR
/build-lab "Build a Returns Triage Agent" --no-pr  # author + gate only; leaves the draft, no PR
/build-lab --resume <build-id>                      # resume an interrupted build
```

What happens:

1. **Account + mode** — pick the cached account (or redeem) and choose **guided** (you dictate each step) or **scenario** (you describe the lab, the AI proposes each step). Both confirm every step.
2. **Navigate** to the Copilot Studio Home page, then name the lab. A **"new lab proposal" issue** is opened on `microsoft/mcs-labs` (labeled `type: new-lab` + `status: in-progress`) so the team can see the lab is In Progress; the final PR closes it.
3. **Capture loop** — for each step: the action runs in the browser, a screenshot is taken, the instruction prose + tips are written, and you confirm before moving on.
4. **Audit gate** — the finished lab is re-run through the audit engine; any broken/unclear steps loop back for a fix. No GitHub issue/PR is filed by the gate.
5. **PR** — once the gate passes, a PR adds `labs/<slug>/README.md` + screenshots + the registration entry.

Build mode is **event/workshop-agnostic** — the new lab is standalone by default; attaching it to an event or workshop (bootcamp, etc.) is an optional prompt, with the available scopes read from the `_events/` + `_workshops/` collections. It **resolves the mcs-labs repo path automatically** with the same `scripts/Resolve-LabRepo.ps1` resolver audit mode uses (env override → config candidates → built-ins → auto-clone), so no path edits are ever needed. Build artifacts live under `runtime/builds/<build-id>/` (gitignored); the mcs-labs working tree is touched only when the PR is created.

> Heads-up: the mcs-labs new-lab toolchain documented in that repo's `docs/NEW_LAB_CHECKLIST.md` (root `lab-config.yml` + `Generate-Labs.ps1`) is currently absent upstream; build mode detects this and writes `labs/<slug>/README.md` + `_labs/<slug>.md` + the `_data/lab-config.yml` entry directly. See [`extending.md`](extending.md#customizing-build-mode-build-lab).

---

## Updating to a newer version

Inside the plugin directory:

```powershell
cd "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
git pull
```

Then restart Claude Code so the latest skills, commands, and references are loaded. `runtime/` is gitignored, so your cached account and audit history survive the update.

Every `/audit-*` and `/build-lab` run begins with a best-effort **self-version check** (`scripts/Test-PluginVersion.ps1`): it compares your local `.claude-plugin/plugin.json` version to the version published on `origin/main` of `microsoft/BootcampLabTestPlugin` (via `gh api`) and, if a newer version is available, prints a non-blocking warning recommending `/plugin` to update. The check is skipped silently when `gh` is unavailable or you're offline — it never blocks a run.

---

## Uninstalling

```powershell
Remove-Item -Recurse -Force "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor"
```

This removes the plugin and **all local state**, including the cached account credentials and audit history. If you only want to clear the credentials but keep the install:

```text
/audit-account clear
```

Restart Claude Code to drop the plugin from the slash-command registry.

---

## Troubleshooting

### `/audit-*` commands don't appear after install

- Did you fully restart Claude Code? Plugins are discovered at session start.
- Is the plugin directory at exactly `~/.claude/plugins/mcs-lab-auditor/`? Use `Get-ChildItem "$env:USERPROFILE\.claude\plugins\"` to confirm.
- Run `Get-Content "$env:USERPROFILE\.claude\plugins\mcs-lab-auditor\.claude-plugin\plugin.json" -Raw | ConvertFrom-Json` — if it throws, the manifest is broken.

### `gh repo view microsoft/mcs-labs` returns 404 or 403

- Your `gh` is logged in as an account without access to the (potentially private) repo. Run `gh auth login` with the right account.
- If the repo is public and your account is fine, check `gh auth status` for SAML SSO authorization — some org-managed accounts require `gh auth refresh -h github.com -s read:org` to surface team permissions.

### Workshop redemption times out

- Verify `config/workshop.yml.workshop_portal_url` is set (not the `REPLACE_ME_ON_FIRST_RUN` placeholder).
- Open the portal URL in your normal browser and visually confirm it has a code-entry form. If the layout differs from a Skillable-style flow, see [`extending.md`](extending.md#adapting-to-a-different-workshop-portal).

### Sign-in fails with "first login password change required"

The workshop-issued account needs to be initialized once interactively. Open `https://login.microsoftonline.com/` in your normal browser, sign in with the issued credentials, complete the password-change prompt, then run `/audit-account clear` followed by `/audit-account redeem` with a fresh code. (You can't reuse the same code — request a new one from your workshop organizer.)

### DPAPI decryption fails on the next run

DPAPI keys are bound to (Windows user, machine). If you signed in as a different user or moved the machine, `credential.enc` becomes unreadable. Run `/audit-account clear` and `/audit-account redeem`.

### Plugin reads stale config after editing

Most config and reference doc changes are read at invocation time — they take effect on the next `/audit-*` call. The few things that require a Claude Code restart:

- New command files (`commands/*.md`)
- Renamed commands or skills
- Changes to `.claude-plugin/plugin.json`

For the rest, just re-run.

### Where to look for more

- Runtime failures during an audit run: [`troubleshooting.md`](troubleshooting.md).
- Security questions about credential storage: [`security.md`](security.md).
- Extending or customizing the plugin: [`extending.md`](extending.md).
