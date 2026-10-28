# Private preference and discovery state

Use [confirmation batching](confirmation-batching.md) for routine no-change responses only. scripts/confirmations.py stages outside the public project and flushes to separate private no-change-confirmations.json history under the same shared lock/backup/commit safeguards. check-in-status exposes its revision and saved answers. These answers neither change preferences nor complete a review, and host access remains separate.

For operational CV/site evidence, see [CV selection and output observations](cv-output.md). check-in-record supports output_observed with a hash-linked private report; check-in-status returns the latest observation per kind across cycles. Observations leave manual/broader completion and preferences unchanged. Recheck live outputs before claiming freshness.

On a successful checkpoint completion, the same atomic commit removes only the exact legacy placeholder note "No successful discovery searches recorded; first-search look-back remains pending." It preserves unrelated notes and keys, and the before-history retains the original bytes. Begin, failure, partial or rejected completion paths do not remove the note. This is not a cleanup command or authority to rewrite historical files: installing/updating the plugin does not modify an existing checkpoint. Read cutoff/run evidence rather than treating explanatory prose as coverage authority.

New profile-apply calls also require a private [approval evidence file](approval-evidence.md). The actual response/context is bound to the preference proposal ID, after_sha256 and STATE/config.json, copied into the operation folder before replacement and hash-linked from intent/receipt. The existing approval-reference remains a navigation aid, not a substitute for evidence. Recovery checks the retained copy; older completed receipts remain unchanged with missing evidence honestly labelled. Routine checkpoint and check-in event operations retain their actual source/coverage/event assertions and do not require a newly invented human preference approval on each run.

Use `scripts/private_state.py` with the discovered Python runtime. It uses only the standard library. These commands write private state only: no YAML, attachments, bibliography, scheduler, route, rendering or Git mutations. Installation never executes them. Actual host access and behavioral authorization are separate. Approval and coverage flags assert prior human authorization/observed connector behavior; they do not authenticate a user or prove that every remote page was searched.

STATE is an existing, explicitly authorized absolute private directory outside the configured project. An existing valid `config.json` is required except for a reviewed first creation. The project directory must already exist. Do not silently initialize over missing, inaccessible or corrupt state. The helper preserves unknown profile/checkpoint keys. It rejects duplicate JSON keys, non-finite numbers, traversal and redirected paths. It does not encrypt files, set operating-system access controls, synchronize computers or serve as a full schema validator/initializer.

## Preferences

Questionnaire responses are first retained privately under the pending-answer procedure in [preferences](preferences.md); they are not applied to config.json one at a time. Combine confirmed answers into one reviewed merge patch at a checkpoint. Before first creation, the actual project directory must exist; until then retain interview state rather than bypassing profile-propose with an ad-hoc config write.

Prepare a private JSON merge patch, for example:

```json
{"discovery": {"initial_window_days": 365}}
```

Objects merge recursively, preserving unspecified keys. Explicit null is a value, not deletion. Lists are replaced as a whole; review them carefully. Replacing an object with a scalar/null can remove its children and is therefore visible in the full proposal. Do not use a preference update to expand filesystem, source, scheduler or public-record authority without the user's actual corresponding authorization.

Prepare provenance separately:

```json
{"source": "User response in the maintenance chat", "recorded_at": "2026-10-17T12:00:00+00:00", "reason": "Initial look-back answer"}
```

Run:

```text
python <plugin>/scripts/private_state.py profile-propose STATE PATCH_JSON PROVENANCE_JSON
```

Show the exact returned before/after, diff, provenance and proposal ID. Hold the live update for actual approval of that proposal, following the user's approval requirements. Then:

```text
python <plugin>/scripts/private_state.py profile-apply STATE ID --approval ID --approval-reference "Private reference to the actual approving response" --approval-evidence FILE
```

The flag/reference are operator assertions, not authentication. Keep the actual response privately; never manufacture it. Apply refuses a changed profile, tampered candidate or repeated application. A unique byte-verified original backup, candidate, intent and completion receipt are stored in `state-history/OPERATION_ID/`. No task or handoff route is changed by updating config.json; reconcile those separately with the appropriate authorization and native host tools.

For a genuinely missing profile, an authorized initial patch containing the known absolute project_root can be proposed with `--create`. The private directory must already be authorized and exist; initial installation is exclusive and does not overwrite an existing profile. First creation uses a fully written/fsynced temporary JSON and an exclusive installation (Windows rename, which refuses an existing destination; a hard link on other systems). A filesystem that cannot provide that operation fails rather than falling back to a racy overwrite. A setup with no known project boundary remains pending until that boundary is established. This is a state-file creation helper, not a CV importer or project initializer.

## Discovery runs

Before preparing each recurring search, list its saved source definitions read-only:

```text
python <plugin>/scripts/private_state.py checkpoint-sources STATE
```

The result includes every exact saved definition (source, declared subqueries and coverage fields) plus source_key and active_run_ids. Reuse the appropriate definition.source and definition.subqueries verbatim; do not reword query descriptions from memory. The listing creates no lock, checkpoint, directory or history. It is private source-selection evidence, not permission to search every listed account. Missing or malformed state is not repaired by listing.

For Gmail catalogue searches, use the deterministic planner described in [email coverage](email-discovery.md). Exact query text, selected category IDs and catalogue version determine the source identity; dates/tokens do not. Legacy free-text definitions remain usable unchanged. The helper cannot prove that remote queries match a definition: retain the exact executed queries and actual coverage in each report.

checkpoint-begin refuses an unfamiliar key when the same provider/account already has another definition, including a query-only wording change with the same scope_version. Inspect checkpoint-sources and distinguish accidental rewording from an intentional scope change before searching. If intentional and authorized, use:

```text
python <plugin>/scripts/private_state.py checkpoint-begin STATE REQUEST_JSON --source-approved --acknowledge-new-scope --scope-change-reference "Private reference to actual reviewed scope decision/authorization"
```

Acknowledgement and reference are operator assertions, not authentication or new permission. Obtain any required human approval for expanded sources/categories/history first. The run and operation intent retain the assertion, reference and related source keys. Existing-source resumes need no new acknowledgement. An intentional new source still gets its own initial window; the flags never copy an old cutoff, bypass active-run/subquery guards, change preferences or rewrite old source evidence. A different provider/account remains subject to its own actual authorization.

Resolve actual provider/account/calendar/library/project and query scope before searching. Reuse the same canonical source definition for identical scopes; do not put secrets or raw correspondence in it. The query describes stable filters, not each run's dates or pagination tokens. A changed identity/query/scope version gets a different SHA256 source key. Changing declared subqueries under an existing key is refused; use a reviewed new scope version so new subqueries do not inherit coverage they never searched. A hash is an identifier, not anonymization; the private document also stores its source definition.

Create a private request file before the first connector call:

```json
{
  "source": {
    "provider": "example-provider",
    "identity": "explicitly-approved-account-or-project",
    "scope_version": "v1",
    "query": "stable approved academic-discovery scope"
  },
  "cycle_id": "routine-review-cycle-identifier",
  "end": "2026-10-17T12:00:00+00:00",
  "timezone_interpretation": "Inclusive UTC bounds; record provider date-only conversion here",
  "subqueries": ["abstracts", "presentations"]
}
```

Use the actual fixed upper cutoff at that run, never this example date. Enumerate all intended subqueries before searching. The helper rejects a future or timezone-free cutoff and refuses a second active run for the same source. With no successful checkpoint, it requires the confirmed `discovery.initial_window_days`; if unknown, ask one question and save its approved answer before dependent discovery. After an unsuccessful first search, it retains the earliest intended initial start on retry, rather than losing coverage as the next run date moves forward. Otherwise it calculates start = last successful cutoff minus the confirmed overlap_days. A materially revised search/window scope needs reviewed source-scope reconciliation or a distinct scope version; do not silently share old coverage with a newly restricted scope. Unsupported window policies require an adapter. It never advances successful coverage at begin:

```text
python <plugin>/scripts/private_state.py checkpoint-begin STATE REQUEST_JSON --source-approved
```

Use the returned run ID, source key and exact inclusive window_start/window_end for the connector calls. Source approval is scoped to that account/query; a flag cannot grant access. The helper records cycle, source definition, initial bounds, prior successful cutoff, profile hash, timezone interpretation and expected subqueries. It uses `discovery.checkpoint_path` when configured, otherwise `STATE/reviews/discovery-checkpoints.json`. This version requires that path inside STATE; a different configured location requires a reviewed migration/adapter, never silent relocation. Existing schema_version=1 empty-source documents are supported without discarding notes; unsupported/ambiguous legacy layouts require reconciliation.

After complete coverage, save a nonempty private report even for zero results. Save result/candidate summaries with source IDs and evidence references when there are results; keep raw correspondence and unnecessary identifying information out. Prepare completion JSON using the exact bounds returned by begin:

```json
{
  "window_start": "EXACT_RETURNED_WINDOW_START",
  "window_end": "EXACT_RETURNED_WINDOW_END",
  "results_durably_saved": true,
  "result_count": 0,
  "report_path": "ABSOLUTE_PRIVATE_REPORT_PATH",
  "result_paths": [],
  "pagination": [
    {"query_id": "abstracts", "pages": 1, "exhausted": true},
    {"query_id": "presentations", "pages": 1, "exhausted": true}
  ]
}
```

Use actual page counts and exhaustion observations. Every declared subquery must occur exactly once and have at least one inspected response/page, including an empty first response. Nonzero results require durable result_paths. Reports/results must be nonempty files inside STATE, not the profile/checkpoint file. Their hashes are captured and checked again before the checkpoint commit. The helper validates these structural assertions and durable files, not the truth of connector coverage or report content. Never assert exhausted/complete for truncated, failed, rate-limited or inaccessible results.

```text
python <plugin>/scripts/private_state.py checkpoint-complete STATE RUN_ID COMPLETION_JSON
```

For new runs, completion requires the semantic search-scope fingerprint to match at completion and immediately before commit, the prior successful cutoff to be unchanged, all fixed bounds/subqueries covered and saved evidence to remain unchanged. The fingerprint includes the entire profile except review.last_broader_completed_at and review.check_in.last_cycle_id, manual_submission_state and output_freshness. It retains identity, source permissions (including review.approved_sources), paths, unknown settings and other preference guards rather than hashing discovery alone. Key order/JSON whitespace do not change it. Legacy runs without scope_hash_version retain their original full-byte check; no silent conversion. Do not disable this check to continue after scope changes. A successful zero-result report may advance exactly to the fixed cutoff, never completion time. Runs and source coverage share one atomic checkpoint document, preserving previous runs and bounds. Other source keys may complete independently.

For unsuccessful/partial work, use a private minimal failure JSON, for example `{"outcome":"partial","reason":"Second subquery could not be fully paginated"}`, then:

```text
python <plugin>/scripts/private_state.py checkpoint-fail STATE RUN_ID FAILURE_JSON
```

Supported outcomes are failed, partial, unauthorized, unavailable, rate_limited, interrupted and save_failed. This closes the attempt and retains the prior successful cutoff. Changed source permission can be recorded as failure without claiming new successful coverage. A missing/changed report or write failure also cannot authorize advancing the cutoff. If failure persistence itself fails, report that and preserve the active run/evidence for recovery. Do not start duplicate searches or assume an exception means no bytes were written.

## Concurrency and interrupted saves

All mutating commands share an exclusive `.private-state-writer.lock`. Cooperating helper processes cannot write concurrently; each update also checks the expected file hash immediately before atomic replacement. This is not an operating-system compare-and-swap against unrelated editors. Do not edit these files concurrently by hand; a tiny external-editor race remains between the final check and replacement. Temporary sibling files are flushed/fsynced, initial creation is exclusive, and existing JSON uses atomic replacement with read-back. These mechanisms do not promise survival of arbitrary hardware/power failures on every filesystem.

An operation writes immutable before/after/intent evidence before replacing the target, followed by a completion receipt. On an interrupted save, inspect the operation ID printed in the error or the latest intents in state-history:

```text
python <plugin>/scripts/private_state.py status STATE OPERATION_ID
```

Statuses are committed_verified, committed_unverified, not_committed, changed_after_commit and conflict. Status only reads. A post-replacement interruption may have already committed the preferences or coverage cutoff even if no receipt was written; never describe that as an unchanged state or advance it again. Recover matching committed bytes with:

```text
python <plugin>/scripts/private_state.py verify STATE OPERATION_ID
```

Verify checks immutable candidate/backup hashes and saved evidence, writes only the missing receipt and does not rewrite the profile/checkpoints. Changed state or evidence requires reconciliation; no automatic rollback. Later edits preserve historical receipts. A killed process can leave its lock: inspect the process/operation and obtain appropriate authorization before stale-lock removal. No timeout silently steals or clears a lock. If helper execution or persistence is unavailable, report the state save as pending; do not claim its safeguards by silently using an ad-hoc writer.

## Routine check-in progress
Preferences stay in config.json. Operational cycle history lives at the fixed STATE/reviews/check-in-state.json, outside the project, using the same writer lock, immutable intent/backup and atomic-commit/status/verify procedure as checkpoints. Host/private-storage authorization is still required. No preferences, permissions, records, schedules, routes or candidate dispositions are changed.

Read before dispatch or responding:

    python <plugin>/scripts/private_state.py check-in-status STATE

An absent file returns empty progress without writing. Null/absent legacy cycle/completion fields need no config edit. Nonnull review.check_in.last_cycle_id or manual_submission_state, or review.last_broader_completed_at, without a progress file returns migration_required and blocks recording: preserve the values and show an exact reviewed migration before writes. Do not clear them or invent completion. Existing output_freshness is dated observation only, not past check-in evidence; keep current freshness evidence in private reports referenced by events.

Prepare a private event JSON containing event_id (32 lowercase hex UUID), cycle_id (stable confirmed cycle), expected_revision (0 for new cycle), action, actor (user/system), reference (actual private message/report evidence), occurred_at (actual nonfuture ISO timestamp with timezone). Then:

    python <plugin>/scripts/private_state.py check-in-record STATE EVENT_JSON

Actions: dispatched (once per cycle, after actual delivery), selected (actual user response, with unique nonempty categories list), closed (actual user Nothing to add), ignored (observed unanswered cycle, not rejection/closure), broader_due and broader_completed. Only selected accepts categories. selected/closed require actor=user. Timestamp must not predate the cycle's last event. References/actor are operator assertions, not authenticated evidence: never fabricate a reply or completion. Broader completion requires a prior due marker and actual completed sweep evidence. Derive due status from saved cadence/anchor and carry an unanswered due cycle forward, rather than minting another independent pending sweep each week.

expected_revision must match current cycle revision; each event advances it. Identical event-ID replay is idempotent; altered payload under that ID is refused. Closed submissions cannot be reopened implicitly; another cycle is separate. Ignored cycles can receive a later genuine response. No event resolves candidates, changes preferences or marks a search successful. No repeated dispatch/extra same-cycle nudge. File opening is not a category response.

After interruption inspect the printed operation ID with status. If committed_unverified, use receipt-only verify before retry. Replay only the same exact known event after inspecting state; never invent a new ID to bypass conflicts. Inspect host history if message delivery is uncertain: this helper is not a transactional sender and cannot itself guarantee exactly-once delivery.

A scheduled worker may checkpoint-fail its own inspected interrupted run under existing source/private-state authorization after verifying no worker is still searching. Preserve the prior successful cutoff and evidence. Never close a live/unknown worker or unrelated run, steal a writer lock, rewrite scope or claim success. After a changed-scope completion refusal, record honest failure on that run and reconcile scope before a fresh search. If persistence fails, leave it pending and report the blocker.

