# Setup entry and compatibility

First-time users can now use [initialize-academic-records](../skills/initialize-academic-records/SKILL.md) for a resumable pre-project interview, private CV text extraction/coverage ledger and prototype starter staging. See [initialization](initialization.md) for commands and limits. These staging commands do not create a real project or deploy it. The [reviewed execution branch](setup-execution.md) supports approved new-project creation, local commands, Git commits and gated push; account/repository creation and deployment configuration/verification use authorized host tools. Automatic factual CV import is not supplied. Existing maintenance must not restart initialization.

Follow [preferences](preferences.md) for profile discovery, migration and resumable storage; [questions](questions.md) for one question at a time; and the [conditional questionnaire](questionnaire.md) for complete decision coverage. Preference setup and initialization reuse the same saved answers. Prototype starter staging and reviewed new-project execution are supported through initialization.md and setup-execution.md. Automatic factual CV import and arbitrary template conversion remain unsupported; label these limits precisely instead of denying the available setup path.

## Profile and readiness
Start from profile.example.json without treating its nulls or examples as answers. Preserve unknown keys and provenance. Readiness is scoped to local maintenance, discovery, publication, attachments and scheduling. Inspect actual project instructions and consumers, required paths, approval policy and host access before using a capability. Local maintenance can proceed while optional setup is incomplete.

Supported adapter: abstracts.yml, appointments.yml, certifications.yml, education.yml, grants.yml, honors.yml, memberships.yml, mentoring.yml, projects.yml, service.yml, talks.yml, teaching.yml, training.yml. Existing media.yml is optional and separately authorized; see media.md. Presence alone is not compatibility or permission. Run proposals.py inspect DATA read-only, validate the baseline and inspect relevant consumers. Unsupported sites get a precise suggested adapter/consumer report, not empty records or guessed fields.

Use config.json only for approved preferences. Use the pending-answer procedure in preferences.md for questionnaire responses before one combined profile proposal, including when no config.json exists. For record facts after a valid profile exists, use pending/<id>.json. proposals.py remember STATE INPUT accepts kind, facts, missing_fields, questions and sources. list replays pending status; event appends answers/dispositions. Never create public placeholder activities. Required unknown dates remain pending; optional nulls can remain compatible nulls. Actual exact-proposal approval is required before apply, independent of setup choices.

Use [structured deferrals](deferrals.md) when the user postpones a question: status deferred requires one confirmed revisit date/time or exact named condition and a reference to the user's decision. Preserve the original evidence/questions, use questions_to_ask for prompting, and record a one-time offered marker rather than repeating the question every week. Existing prose-only deferrals need separately approved migration, not automatic interpretation.

Complete proposals retain staged bytes, source/bibliography hashes, validation, backups and receipts. Check status after interruptions; saved_unverified is not no-write or awaiting approval. Verification can complete an existing approved save without rewriting; it cannot approve a new one. Preserve historical receipts and distinguish current drift. See verification.md.

## Publications and sources
Record publication authority and destination preferences privately. For Zotero, preserve confirmed library/root/collection defaults and inspect current integration capabilities plus auto-export targets/timing/overwrite effects. A selected collection is an observation, not a preference. Library reads/imports/edits are different capabilities. Never reimport corrections as duplicates or assume export side effects absent. Follow zotero.md and the separate approval-gated skill.

At every review discover email/calendar integrations through supported host tools and restrict use to approved selections. Store chat scope explicitly. Failed or absent sources do not advance watermarks. Follow discovery.md and reviews.md. Keep unanswered choices pending without re-asking unchanged setup every scheduled run.

## Attachments and output handoff
For teaching/abstracts/presentations ask now/later/none unless answered. Follow attachments.md and mandatory privacy.md. Save exact project-relative PDF routes and inspect existing folders; no implicit creation, original archival or overwriting. Distinct session/version materials require compatible schema/consumers, not guessed new fields. Actual uploads require a file-capable surface.

Save rendering_preference and inspected output_commands with provenance. The preference does not authorize executing generation, code edits, Git or publication. Follow owner-handoff.md after verified saves, distinguishing source changes from pending outputs. Keep existing satisfactory layouts and structured-records-to-output flow.

## Scheduling and handoff
Follow scheduling.md: inspect existing automations before creation, bind the current installed plugin at run time, use the canonical profile and save executed version evidence. review.* is the schedule preference authority; discovery.* owns source/window configuration. Broader every-N-cycle checks need an explicit anchor and confirmation history. Schedules require separate host configuration and actual access.

A handoff route is optional and distinct from the full profile. Preserve route destination/policy during migration. Follow handoff.md; forwarding requires actual human authorization. Installation neither creates a job nor grants access.

Scheduled-maintenance setup must carry through to actual native task create/update, read-back verification and a saved profile link once specifications and authorization are complete; use scheduling.md. Initialization reuses this procedure. Maintenance setup can proceed independently of new-project setup.
