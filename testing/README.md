# Blind testing: CV and Website Maintainer

Status: **proposed protocol, not yet executed**.

This protocol adapts the independent-agent user simulation in [R Analysis Workflow draft PR #13](https://github.com/VagishHemmige/r-analysis-workflow/pull/13), especially its testing README, assistant brief, world, scenarios and scorecards. This is distinct from existing automated tests under `tests/`.

## Repository boundary

Keep `testing/` **outside the installable plugin**. The intended eventual layout is `plugin/` for installable skills/scripts/references/assets/manifests, and root `testing/` for coordinator briefs, persona prompts, synthetic fixtures, hidden answer keys and run reports. **Do not move the existing plugin in this PR.** Plan a separate, validated migration of paths, packaging, marketplace manifests, imports and documentation. Never bundle hidden scoring material into participant-agent/plugin context.

## Two independent evaluations

**A. Blind plugin review:** Independent reviewers inspect a frozen plugin version from their assigned professional perspective. An evaluator verifies each claimed problem against files and documentation, withdrawing unsupported findings.

**B. Blind user simulation:** An orchestrator stages a realistic environment, a persistent persona agent writes only the human user's messages, and a fresh assistant agent in each session uses the actual frozen plugin. The orchestrator relays messages verbatim and never coaches either side. The evaluator separately assesses outputs and evidence.

A role-play transcript alone does not establish that dependencies installed, files compiled or GitHub Pages deployed. Use an isolated executable sandbox wherever possible. Record simulated versus executed outcomes explicitly.

## Starting and finishing a run

1. Freeze the exact plugin commit and installation/package layout. Confirm what the assistant can actually load.
2. Record the starting environment and permitted capabilities (R/Rscript, libraries, Python, Quarto, document/PDF converter, editor, Git, GitHub account/permissions, execution/file scopes). Do not preinstall tools merely because they might be useful.
3. Give the persona only its background, circumstances, synthetic files and a natural goal; **never** give it the plugin, scoring rubric or hidden outcomes.
4. Give each new assistant session the frozen plugin, only that session's workspace/uploads, authorized user-facing environment, and the persona's message. No prior chat memory unless the test explicitly supplies it.
5. Relay verbatim until the user finishes, gives up, or reaches the predefined session cap. The orchestrator may perform simulated user-only UI/account actions *only when the persona says it performed them*; mark simulation clearly.
6. Capture both sides of every exchange, commands, actual files and diffs, approvals, status receipts and verification evidence.
7. After each reply, record a **Gap**, **Good**, or **Judgment** with an exact supporting exchange. No mid-round plugin fixes; log any accidental prompt nudges.
8. Score against withheld answer keys. Verify each alleged failure independently; record false positives and unknowns. Aggregate results by persona, goal and environment.
9. File issues for confirmed problems after the baseline run and rerun the affected scenarios on the corrected version.

Never use actual patients, real private CVs, authentication secrets or production repositories in fixtures. See [personas](personas.md), [scenarios](scenarios.md), [orchestrator](orchestrator.md), and [scorecard](scorecard.md).

## Evidence labels

- **Executed/verified:** inspected real files, commands, document output, or accessible page.
- **Executed/unverified:** action executed but output not independently inspected.
- **Simulated:** represented in fake GitHub, user UI action or role-play only.
- **Blocked:** precondition unavailable or access denied.
- **Not tested:** action not attempted.

A YAML save is not CV compilation; CV compilation is not PDF conversion; site rendering is not public deployment.
