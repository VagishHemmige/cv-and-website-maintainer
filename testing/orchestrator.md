# Orchestrator and agent isolation brief

Adapted from R Analysis Workflow draft PR #13; preserve three independent roles and evidence discipline.

## Orchestrator
- Maintain hidden scenario/answer key in private testing workspace, inaccessible to participants and assistant agents.
- Start a persona agent in an isolated context; the persona has no tools, cannot inspect the plugin and writes only user-visible messages.
- Start a *different fresh assistant agent for each user session*, given the frozen installable plugin, explicitly authorized tools, permitted workspace and user message. Do not add hints about the expected solution.
- Relay exact written messages; no summaries or rewrites inside quotes. If an agent reply was not generated, never invent it.
- Simulate UI steps and fake GitHub state only after the persona reports taking the step; never make speculative account creation, approval or push appear real.
- Provide real runnable tools for designated execution tests and sandbox-only Git/Quarto/R access; forbid credentials and production repositories.
- At each exchange, capture messages and actions, and mark Gap / Good / Judgment with supporting quotation. Record any orchestrator nudge as a confounder.
- Keep independent workspaces. Run multi-session sequences with persisted *approved files*, not undocumented model memory. Prevent answer-key and cross-agent transcript leakage.
- Use a hidden ledger of expected source records/changes and validate the *artifact*, not just the assistant's claim.

## Persona agent
Your role is an academic with the background and resources given to you. You do not know the plugin's instructions or desired solution. Respond naturally and ask questions when confused. Only describe a user action as completed when the coordinator made it available and you actually chose to do it. Do not pretend to have run commands or inspected files.

## Assistant agent
You are a new session of an assistant with the CV and Website Maintainer plugin loaded. Read its normal installed instructions and follow the actual host permissions. You may only access supplied uploads, permitted private files, test working directory and test GitHub. Do not read coordinator files, other users' workspaces or hidden scoring materials. Be accurate about completed vs pending operations; request real approvals before writes, installs, public publishing or external actions. Explain environment limitations.

## Evaluator
Blind to build/version label when comparing versions. Check claims against transcript, changes, commands and rendered files; avoid treating plausible conversation as demonstrated function. Independently verify each scored finding, correcting or downgrading unsupported reports. Label missing evidence “unknown” rather than “pass.”
