# Preference-aware output follow-through

After a verified approved source save, or an explicit generation request, resolve the actual affected consumers and the user's saved assistance settings. This is a separate output workflow; the YAML/attachment helpers themselves do not render, commit or publish. A scheduled discovery report has no record-change approval and cannot apply candidates to trigger outputs.

## Stage preferences and authorization
Treat website rendering, private CV generation, output verification, Git commit and push/publication as separate stages. Resolve output_execution.STAGE.mode when configured; otherwise interpret existing assistance and rendering_preference conservatively. Supported modes: owner_managed/instructions_only; agent_with_per_run_approval; agent_with_standing_authorization. Unknown or contradictory values require one relevant clarification, not automatic execution.
Preference is desired assistance, not permission. Agent execution additionally requires a dated explicit human authorization covering that stage, repository/project, allowed paths/commands, overwrite/backups policy and, for Git, intended branch/remote/files. Check actual host tools, filesystem access, dependencies and credentials each run. Plugin installation, an approved record diff, a successful render or a frequency setting does not authorize another stage. Existing project instructions may constrain scope.
Honor an already explicit matching standing authorization without re-asking, but stop for changed scope, credentials failure, unexpected files or an approval checkpoint. A per-run mode prepares concrete reviewable work before requesting its approval. Settings may be changed by request; keep history and apply the same choices in tasks configured by setup.

## Execution and verification
- Website: inspect actual Quarto configuration/commands and output/cache paths before running. Need authorized writes to build locations as well as source reads. Preserve unrelated changes; never edit R/Quarto code to force a build through without separate code authorization.
- Private CV: inspect the existing generator, private inputs and output target without copying private contacts into public files/logs. Protect prior and same-day outputs under the approved backup/version policy before overwriting. Generator success is not factual/layout verification.
- Verification: check command exits/logs, expected changed entries, links and appropriate rendered/visual outputs. Report gaps. Unknown freshness remains unknown. Verify affected consumers rather than assume every record feeds both CV and website.
- Git commit: review current branch/remote/status and complete diff; stage only explicitly intended paths. Exclude private CV/contact data, private state and unrelated work. An unexpected staged file or source modification stops automatic progression. No blanket git add, force push, reset, clean or deletion.
- Push/publication: require the corresponding explicit authorization, correct remote/branch and credentials. After successful push, inspect deployment status and published output where tools permit. Commit success is not push success; push success is not verified deployment.
On any failure, report actual partial state and preserve backups/logs privately. No blind reruns, rollback or automatic permission expansion. Refresh verified output links only after actual generation and checks; do not imply publication from a local render.

## Scheduled tasks
Every created maintenance task must load this same profile and apply the same stage preferences. Discovery is read-only for academic records; optional output execution can follow only an already verified/approved save or an explicitly authorized generation trigger and all stage-specific gates. A routine reminder alone is not such a trigger.
If preferences are owner_managed, provide the established handoff and accurately labelled current output links. If permissions/tools are absent, leave that stage pending and explain what is missing; do not silently downgrade or change the user's settings.

## Public CV
Private CV generation and public CV preparation/publication are distinct. Do not upload, export, commit or publish a private-contact CV merely because generic rendering/push assistance is enabled. A public version needs separately approved content/visibility, export destination and publication authorization. A deferred public-CV decision remains deferred until requested.
