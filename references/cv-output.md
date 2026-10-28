# CV selection and output observations

Run the read-only helper with the discovered Python runtime:

```text
python <plugin>/scripts/cv_output.py STATE
```

It reads review.check_in from the current canonical profile. Existing cv_link values remain fixed links; the helper does not infer a pattern or search neighboring files. A remote link is returned as remote_unverified without fetching it. A local file is checked for existence and metadata. Nothing is generated, uploaded, copied, rendered or saved by this command.

For date-stamped outputs, separately propose an exact preference change adding review.check_in.cv_locator with directory (an explicitly approved absolute local directory) and filename_pattern (a filename-only .docx or .pdf pattern). For example, an approved directory plus `Example CV *.docx`. The locator takes precedence over cv_link for local selection; a malformed locator blocks resolution rather than silently falling back. The example is not a user preference. Obtain exact profile-proposal approval before adding/changing it. Keep private-CV selection separate from any public-CV authorization.

Selection inspects only matching files immediately in that directory, excludes Office temporary files, refuses redirected paths and never traverses subfolders/Archive. The most recent modification time selects a candidate; equal newest times are ambiguous and require clarification. Missing/inaccessible/changed files are not current outputs. Selection is by metadata, not semantic CV date or content correctness: the helper returns path, size, modification time and SHA256, never extracted contents. Recheck before using a link; do not use a style reference or historical baseline as the current CV.

If a latest approved source save has independently verified evidence, pass its real timestamp with `--last-save-at ISO_TIMESTAMP`. An older file gets stale_by_timestamp. A newer file gets modified_at_or_after_save_contents_unverified, not a claim it includes the edits. Without a verified save reference, freshness remains unverified. A future file timestamp is flagged as unverified. Do not infer last-save-at from a source file's modification time or claim regenerated/current merely from a hash, filename, timestamp or a user's report of generation. Record actual user-reported generation separately from metadata/content verification.

## Retain an observation for later check-ins

Save a minimal private JSON report containing the actual resolver result, observation time, evidence/method, applicable source-save reference and known limitations. For website observations record actual URL, fetch time/result and limitations; this helper does not fetch websites. Keep reports in authorized STATE, outside the public repository, with no private CV contents or raw correspondence. Merely viewing or reporting an output does not authorize publication.

Read check-in-status for the cycle revision, then record an operational event using the existing check-in-record command:

```json
{
  "event_id": "ACTUAL_UNIQUE_32_HEX_ID",
  "cycle_id": "ACTUAL_CYCLE",
  "expected_revision": 0,
  "action": "output_observed",
  "actor": "system",
  "reference": "Actual private inspection/user-report evidence reference",
  "occurred_at": "ACTUAL_OBSERVATION_TIME_WITH_TIMEZONE",
  "output_observation": {
    "kind": "cv",
    "report_path": "ABSOLUTE_REPORT_INSIDE_STATE",
    "report_sha256": "ACTUAL_SHA256_OF_SAVED_REPORT"
  }
}
```

Use the actual revision/time/IDs/hashes, not the placeholders. kind is cv or website. The helper requires a nonempty matching report inside STATE and rechecks it before commit. The event and operation intent retain the report hash. Output observations do not dispatch/close manual submissions, complete broader reviews, update preferences, authorize outputs or change source checkpoints. They may be recorded after a manual closeout without reopening it. Existing revision, idempotency, backup and interruption safeguards still apply.

check-in-status returns output_observations containing the latest observation per kind across cycles, and whether its report still matches. It also returns the event history for older observations. This is retrieval of prior evidence, not proof the live file/site is unchanged: recheck outputs before each check-in and label freshness honestly. Missing/changed/inaccessible reports stay explicit. Do not repeatedly use stale config.output_freshness prose in place of newer verified operational evidence. Preference changes still use exact profile proposals; N2's held broader-completion behavior is unchanged.
