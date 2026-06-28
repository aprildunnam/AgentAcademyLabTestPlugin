---
description: Reproduce a GitHub issue from microsoft/agent-academy by running the relevant lab steps and verifying the reported problem.
argument-hint: "[<issue-number>] [--no-comment] [--auto-fix] [--no-pr] [--env-url <url>]"
---

# /reproduce-issue

You are attempting to reproduce a bug reported in a GitHub issue on the `microsoft/agent-academy` repo.

## Arguments

Arguments passed: `$ARGUMENTS`

The first positional argument is the GitHub issue number (e.g., `42`). If omitted,
present the user with a list of recent open issues labeled `lab-test` or `bug` to
choose from.

Flags:
- `--no-comment` — run the reproduction but don't post results back to the issue.
- `--auto-fix` — if the issue is confirmed, capture annotated screenshots and open
  a fix PR (Phases 5–6 from SKILL.md).
- `--no-pr` — skip fix PR generation even when `--auto-fix` is passed.
- `--env-url <url>` — override the default Power Platform environment URL.

## Your task

Invoke the `agent-academy-tester` skill in **issue reproduction mode**:

1. **Fetch the issue.** Run `gh issue view <number> --repo microsoft/agent-academy --json title,body,labels,comments`
   to get the full issue details.

2. **Extract the lab reference.** Look for:
   - A `lab:<course>/<slug>` label (most reliable — filed by this plugin)
   - A lab path mentioned in the title or body (e.g., `recruit/04-creating-a-solution`)
   - Step numbers referenced in the issue body (e.g., "Step 5", "step 3 in section 2.1")
   If no lab can be identified, ask the user which lab this issue relates to.

3. **Extract reproduction details.** Parse the issue body for:
   - **Specific steps** that are broken (step numbers, section references)
   - **Expected behavior** described by the reporter
   - **Actual behavior** described by the reporter
   - **Environment details** (tenant, browser, date)
   - **Screenshots** attached to the issue (compare against live UI)

4. **Fetch and parse the lab.** Clone/pull `microsoft/agent-academy`, read the lab's
   `index.md`, and parse it into a step tree.

5. **Determine scope.** If the issue references specific steps:
   - Run all prerequisite steps leading up to the reported broken step(s) in quick
     mode (execute but don't deep-judge — just confirm they still work)
   - Run the reported broken step(s) with full judging and extra scrutiny
   - Run 2–3 steps after the broken step(s) to check for cascade effects

   If the issue is general ("this whole lab doesn't work"), run the full lab normally.

6. **Browser authentication.** Same as Phase 2 in SKILL.md — open browser, navigate
   to the environment URL, wait for auth if needed.

7. **Execute steps.** Walk through the scoped steps using Playwright. For each step:
   - Execute the action
   - Capture state (snapshot + screenshot)
   - Judge the result
   - **Extra comparison**: compare the live UI against any screenshots attached to
     the issue to see if the reporter's problem is still visible

8. **Determine reproduction status.** After execution, classify the result:

   | Status | Meaning |
   |---|---|
   | `reproduced` | The reported issue is confirmed — live UI matches the reporter's description |
   | `partially_reproduced` | Some aspects confirmed, others work fine or differ |
   | `not_reproduced` | All steps work as documented — cannot confirm the issue |
   | `different_issue` | Found a problem, but it's different from what was reported |
   | `environment_dependent` | Issue may be specific to the reporter's tenant/environment |

9. **Write reproduction report.** Save to `runtime/test-results/repro-<issue>-<timestamp>.md`:
   - Issue reference and original reporter's description
   - Step-by-step execution results (focused on the reported steps)
   - Screenshots at each critical step
   - Reproduction verdict with confidence
   - Environment comparison (if the reporter provided environment details)

10. **Post results to the issue** (unless `--no-comment`). Add a comment on the
    GitHub issue with the reproduction results:

    ```markdown
    ## 🔬 Automated Reproduction Attempt — {date}

    **Status: {reproduced|partially_reproduced|not_reproduced|different_issue|environment_dependent}**

    ### Environment
    - **Date:** {date}
    - **Environment:** {env_url}
    - **Browser:** Microsoft Edge (Profile: {profile_name})
    - **Plugin version:** {version}

    ### Results

    {for each tested step}
    #### Step {N}: {verdict}
    - **Expected (issue says):** {reporter_expected}
    - **Lab says:** {lab_instruction}
    - **Actual (today):** {observed}
    - **Screenshot:** (attached)
    {end for}

    ### Conclusion

    {detailed_conclusion}

    {if reproduced and auto_fix}
    🔧 A fix PR has been opened: #{pr_number}
    {end if}

    ---
    _Automated by [Agent Academy Lab Tester](https://github.com/aprildunnam/AgentAcademyLabTestPlugin)_
    ```

11. **Auto-fix (if `--auto-fix` passed and issue reproduced).** Run Phases 5–6 from
    SKILL.md to capture annotated screenshots and open a fix PR. The PR body should
    include `Fixes #<issue_number>` to auto-close the issue on merge.

Follow `$PLUGIN_ROOT/skills/agent-academy-tester/SKILL.md` for the browser auth
and step execution procedures.
