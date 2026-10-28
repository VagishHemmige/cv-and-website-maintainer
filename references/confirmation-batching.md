# Batch routine no-change confirmations

This workflow reduces separate private-history save commands. It does not change questions, exact record approvals, host permissions or broader-review completion. It does not guarantee a particular number of permission prompts.

## Prepare access and stage each answer

At run start inspect the actual writable roots, canonical private profile, installed plugin/runtime and known source/network needs. Identify an explicitly authorized private run directory that is writable in this session and outside the public project and plugin. Use the host's real access/escalation workflow when needed. A successful probe or prior command approval is not a standing permission grant. Do not preflight through arbitrary network destinations, modify host settings or invent a blanket approval. Use available approved grants only within their actual scope. If no private writable staging location exists, request needed access or report that persistence is pending; never stage private answers in public data or silently create a competing profile.

Before showing a category's current list, retain hashes of the actual source files used to construct it. After an actual user no-change response, prepare a minimal private answer JSON:

```json
{
  "id": "ACTUAL_UNIQUE_32_HEX_ID",
  "cycle_id": "ACTUAL_CYCLE",
  "category": "ACTUAL_CATEGORY_SHOWN",
  "outcome": "no_changes",
  "response": "Actual brief user reply",
  "reference": "Actual question/list and response reference",
  "source_hashes": {"ABSOLUTE_DISPLAYED_SOURCE_PATH": "ACTUAL_SHA256_AT_DISPLAY"}
}
```

Hashes bind source bytes, not proof of the exact rendered list or authenticity of the human response. Preserve the actual prompt/response reference; never manufacture a confirmation or turn silence, assistant conclusions, email, an invitation or a deferral into no_changes. Files must be in the configured project. New facts, approvals, deferrals, profile answers and sensitive raw correspondence do not belong in this batching path.

Run with the discovered Python runtime:

```text
python <plugin>/scripts/confirmations.py stage STATE PRIVATE_RUN_DIRECTORY ANSWER_JSON
```

The private directory must already exist and be authorized. The helper checks current source hashes, stores an exclusive hash/context-bound envelope and verifies it. Same-ID identical retries preserve the original capture; conflicting evidence is refused. Staging does not write the canonical profile/history. No source record is edited. Save each response here immediately so an interrupted conversation can resume without asking again; report it as staged, not already saved to canonical history.

## Flush at a natural break

At category-review breaks, closeout, or before a requested pause, read check-in-status.no_change_confirmations.state.revision and flush the intended cycle once:

```text
python <plugin>/scripts/confirmations.py flush STATE PRIVATE_RUN_DIRECTORY --cycle ACTUAL_CYCLE --expected-revision ACTUAL_REVISION
```

The batch writes STATE/reviews/no-change-confirmations.json in one atomic helper commit, with the existing shared lock, immutable before/after/intent/receipt and verified backup. The canonical document retains each complete staged answer/envelope. Its own revision is separate from the interactive cycle revision. All new selected answers must pass before any commit; changed sources, profile scope, revision, staging or malformed history block the batch for inspection. Do not silently refresh hashes to make old answers pass. Reinspect the displayed list and reconcile whether the user's answer still applies. Unrelated cycles remain staged. Staging files are retained; repeated flushes do not duplicate saved IDs or rewrite history, even if records have changed since their historical save.

Use actual host permissions for the flush. Do not replace exact record approval with the batch or change scheduler/route/configuration. The canonical confirmation document is visible through check-in-status, so later runs can reuse dated answers without treating them as permanent guarantees. It does not close manual submissions, resolve unrelated findings, advance source cutoffs, complete or defer broader reviews, or authorize outputs. Deferrals/rejections, approved record saves, important preference answers and other interruption-sensitive decisions keep their immediate existing safeguarded writes.

If flushing fails, keep staged answers and report canonical persistence pending. An interruption may have committed bytes: inspect the operation ID with private_state.py status and, when supported, receipt-only verify before considering another flush. Never erase locks/history, roll back, fabricate historical success or discard staging to hide a failure. Staged answers are plaintext private data; existing retention preferences/permissions govern them, and this helper performs no automatic cleanup.
