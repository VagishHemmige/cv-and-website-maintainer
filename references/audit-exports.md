# Private run-audit exports

Only prepare an audit bundle when requested. Use the original snapshots for the
audited run; do not substitute current preferences or records into historical
evidence. Work on a separately authorized private export copy, preserving the
original ZIP and source files. Include visible conversation and selected
operational evidence only, never hidden reasoning, analysis messages, reasoning
summaries, system/developer prompts or raw session logs. Do not send the bundle
to another service/person/chat without explicit authorization.

Omitting raw email results is not enough. Inspect all duplicated surfaces:
wrapper arguments, nested command strings, command output, connector arguments
and results, file-change diffs, timing JSON/CSV, copied scripts and archived
members. Unrelated sender names or filters must not pass through executable
code. Use scripts/audit_redaction.py's conservative field omission on export
copies. It preserves event IDs, timing/status/count metadata and omission hashes,
not raw executable bodies. Unknown event bodies are omitted by default.

Restore only an explicitly reviewed query through the helper's exact-event
argument allowlist. Read the actual query and compare its source scope/window
first; do not mark all connector arguments reviewed automatically. Raw mail
payloads stay omitted. The review is an operator assertion, not independent
authentication. Preserve reviewed academic proposal, backup, validation and
scoped report snapshots separately, with an explicit selection and privacy
review; never assume copying an entire working directory is safe.

Scan the final copied tree and archive, not just the main tool-call file.
Validate redacted field schemas, detect residual sender-filter code and known
credential/MIME markers, and inspect binary/nested archives or disclose them as
unreviewed. Report findings without quoting private literals. Test nested and
duplicated leaks with synthetic sender tokens; do not turn real private senders
into test fixtures. Preserve unchanged snapshot hashes and record original and
new export hashes for every transformed artifact. Redacted bytes cannot still
be represented as exact originals in the integrity index.

Give the reviewer the selection/redaction policy, omitted-field counts, evidence
limits and archive checksum. Omission hashes prove only a binding to canonical
field bytes, not what those bytes meant or that approval occurred. Redaction
prevents independent inspection of the omitted execution bodies; retain the
selected durable evidence and be explicit about that loss. Review a changed
bundle as a new export, not a repair of original receipts.

This is not de-identification, a formal security review or a guarantee that all
personal information was removed. An intentionally private academic audit may
still contain the owner's identity, paths, preferences, academic collaborators
and approvals. Do not call it public-safe. A replacement does not retract an
earlier ZIP or erase a copy already shared. Preserve originals unless deletion
is separately requested and authorized.
