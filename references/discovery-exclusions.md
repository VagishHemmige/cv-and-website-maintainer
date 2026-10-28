# User-approved discovery exclusions

Read discovery.exclusions from the canonical private profile on each run before presenting candidates. Missing/null/empty means no configured exclusions; never invent a rule from packaged examples, another user, an assistant paraphrase or one rejected candidate. A specific pending rejection remains closed independently of these rules. Each new/changed rule requires an exact profile proposal and actual approval. An answer about desired scope is retained pending that approval, not applied silently.

Rules use this generic shape:

```json
{
  "id": "user-chosen-stable-rule-id",
  "destination": "service.yml",
  "activity_types": ["user_confirmed_activity_type"],
  "reason": "Actual user wording describing the exclusion",
  "confirmation_reference": "Actual human scope-decision reference; exact profile approval is retained in its proposal receipt"
}
```

These are schema placeholders, not default choices. Match destination and activity_types exactly; do not broaden a service rule into a blanket exclusion of publications, awards or all correspondence. Activity IDs are explicit lower-case identifiers. For letter decisions distinguish recommendation_letter, external_promotion_review_letter and external_tenure_review_letter; do not assume a choice about one covers the others. Journal reviewing, abstract reviewing and committee reviewing are distinct activities, not synonyms for letter review. Keep all personal selections in private preferences; the reusable package provides no active exclusion defaults.

## Evidence-based classification, then filtering

Collect minimal authorized discovery summaries, deduplicate by source IDs and prior dispositions, then establish each candidate's activity type from actual evidence. Do not filter remote searches by these rules or remove unread results before understanding their activity; this helper operates after triage and does not grant search permission, change queries or advance checkpoints. Existing permitted source coverage still needs its own complete searches/pagination and saved report.

A candidate has id, destination and optionally activity_classification with exactly type, certainty (supported or uncertain) and reference (actual classification evidence). Existing candidate fields such as new/existing/changed classification are separate; do not replace them. The assistant is responsible for truth of the supplied classification; the helper does not infer types from subjects, senders, domains or keywords and cannot authenticate the evidence. Classify a promotion/tenure evaluation letter separately from a letter of recommendation or an editorial manuscript review. If unclear, retain the item privately as needs_classification; consult accessible authorized evidence and, only if necessary, ask one focused question without reopening settled rule scope or existing rejections/deferrals.

After saving the minimal candidate JSON list inside authorized STATE, run with the discovered Python runtime:

```text
python <plugin>/scripts/discovery_exclusions.py STATE PRIVATE_CANDIDATES_JSON
```

The helper only reads. It returns eligible, excluded (IDs and matched rule IDs only), needs_classification, per-rule counts and unique category counts. Unknown/uncertain types under a relevant rule remain pending, not silently excluded or treated as eligible record proposals. Supported nonmatching activities remain eligible for normal factual/identity/approval review. Unsupported rules, malformed inputs or duplicate candidate IDs stop filtering for review instead of quietly dropping evidence. No configured rule means the candidate list passes through unchanged. Multiple matching rules can count the same excluded candidate; disclose overlaps rather than summing them as unique messages. Counts describe deduplicated candidates, not all messages searched.

Save the filter result with the private discovery report and report excluded-candidate counts and applicable rule scope in the check-in, without unnecessary names/raw correspondence. A retained exclusion never deletes existing records, changes an old rejection, dismisses an unrelated finding or authorizes an update. Prior pending dispositions and questions_to_ask still apply before any re-prompt. Discovery only proposes candidates; eligible output is not approval to save anything.
