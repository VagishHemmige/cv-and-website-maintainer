# Routine save without custom wrapper scripts

Use existing packaged CLI commands for supported operations. Write small private
JSON inputs with normal file tools; do not generate a Python script merely to
assemble approval evidence, call apply, record a confirmation or print status.
Release-building and genuinely unsupported adaptation work are separate tasks.
No performance or permission-prompt count is guaranteed.

## One approved YAML proposal

After showing the exact diff, named proposal and validation and receiving actual
human approval, write CONTEXT.json inside authorized private STATE. Use exactly
the approval-evidence schema fields except recorded_at:
schema_version, decision, response, channel, message_reference,
proposal_reference, approved_at, timestamp_source, approvals. Preserve the actual
response and references. Each approvals entry must explicitly contain the
approved kind, ID, SHA256 and destination from the displayed proposal. Do not
derive approval from the latest bytes, a vague yes, or installation.

If message time is unavailable, approved_at is null and timestamp_source is
message_time_unavailable. The command supplies only the real capture time:

```text
python -B <plugin>/scripts/approved_save.py STATE ID CONTEXT.json RSCRIPT --r-library LIBRARY
```

Omit --r-library when unnecessary. JSON is data, not executable code; do not put
reply text into shell interpolation. The command checks private paths and exact
evidence binding, exclusively saves a unique private evidence file, then invokes
the existing proposals.py apply command. All its validation, allowlist,
stale-source, staged-byte, backup and recovery checks still run. No validator
result is cached. The helper's argument/evidence is an operator assertion, not
independent authentication of a human response.

Output has an approval_captured event (never a save-success claim), followed by
the helper return code and current proposal status. Quotes are not printed.
A captured approval alone is not a saved record. On failure/interruption preserve
the context, captured evidence, attempts and backups; run proposals.py status
STATE ID. Never automatically retry, repair receipts, roll back or resolve a
pending candidate. saved_unverified is a saved-but-unverified outcome. Pending
events remain separate so a failed save cannot mark a candidate applied.

This convenience command covers one YAML proposal. Profile and PDF saves retain
their existing CLI workflows and separate permission/privacy requirements; use
their documented evidence schema directly, without ad-hoc live-write scripts.
It neither changes profiles nor performs rendering, publishing or Zotero writes.

## Confirmations and consumer inspection

For no-change answers use confirmations.py stage and flush as documented in
[confirmation batching](confirmation-batching.md). Do not add a competing
check-in-confirm history store. Changes, deferrals, approvals and review closeout
remain separate.

Inspect relevant website/CV consumers once per run for the actual changed fields.
Keep a run-local note identifying each inspected path, its SHA256, the fields
examined and the resulting compatibility assessment. Before reuse, hash those
same files and check the proposed fields/dependencies and current instructions.
Reuse the assessment only while hashes and relevant scope are unchanged. A new
field, dependency, changed/missing consumer or changed instruction requires
inspection again. An uninspected file's hash alone is not a consumer review.
Do not reuse a cache across runs as proof of current compatibility.

This avoids rereading unchanged consumer text; it does not skip source hashes,
record validation, cross-reference/resource checks, project-required safeguards,
or exact proposal review. The proposal helper still validates each save.
