# After-save handoff for the site owner

First report the actual save outcome. A helper error is not evidence that nothing changed. For saved_unverified, conflict or changed_after_save, explain the current files, verification failure and backup, and propose recovery before any further edits or regeneration. For saved_unverified, `verify STATE ID RSCRIPT` (with --r-library if needed) checks the existing approved bytes, original backup, unchanged other records/bibliography and validation, then records verified completion privately without rewriting YAML. It requires an approved apply attempt with confirmed target-write evidence; matching bytes alone cannot establish that this proposal saved them. Legacy uncertain attempts require manual reconciliation, and contradictory recovery history is flagged without rewriting receipts. It cannot approve an unapplied proposal. Conflicts or failed verification require a new reviewable recovery plan. Do not roll back automatically.

For a verified save, explain in plain language:
1. Which source record/file changed and what checks passed.
2. Which outputs depend on it: website pages, Word CV, both, or neither. Determine this from the actual consumer map/source.
3. Which outputs have not yet been regenerated. A source-save is not a deployed-site or CV update.
4. The user's established next actions, based on rendering_preference and verified output_commands in their private profile. For manual_rstudio, describe the project-specific RStudio actions; for terminal_instructions give the exact verified command and working directory. Only offer agent execution under separate existing authorization. Do not change the user's preference or permissions here.
5. What the owner should inspect in regenerated outputs and their known commit/publication process. If publication steps are unknown, say so and ask when relevant; do not invent a deployment command or execute Git without the separate authorization described in output-execution.md.

Routine supported record updates require no R/Quarto code edits after setup. An incompatible requested feature gets a separate suggested source/schema change report and remains pending, not an instruction to patch code after every update. Word CV generation and website rendering may use different commands. File existence/source inspection verifies a command's configuration, not successful execution; report whether it was actually tested.

Do not hard-code a particular person's project path or output commands here. Save those answers and observed commands in their private profile. Do not run a render, generate a CV, commit or publish merely because this handoff lists next steps.

For attachments, separately report PDF placement and YAML-link outcomes. Verify project-root-relative paths exist and hashes match, and distinguish privacy screening from institutional clearance. A saved but unlinked file is not a completed record update; keep it pending without automatic deletion or rollback. Converted PDFs need page/render checks before approval. Do not publish unresolved patient identifiers.


Media updates affect the website through its verified media.qmd consumer; they do not imply a CV entry or authorize a render. Report whether the consumer migration is applied or still owner-pending.

Read [verification semantics](verification.md) when reporting save/recovery results. Inspect historical_save_verified, current_snapshot_matches and changed_files separately; an older snapshot may differ because of later legitimate changes. Recovery completion requires current file allowlisting. A final-validation mismatch with already-saved target bytes is not an untouched record; report its actual status and preserve the backup.

For a user who explicitly authorizes agent output execution, follow [preference-aware output follow-through](output-execution.md) as a separate stage after the verified save. Reuse per-stage settings in interactive and scheduled workflows; do not infer grants from a desired assistance mode. Owner-managed preferences retain the manual handoff. Private and public CV permissions remain separate.
