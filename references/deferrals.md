# Deferred questions and one-time revisits

Use structured deferrals to retain an unresolved candidate without asking the same question every review. A deferral changes private question state, not academic facts, an approved public record, review frequency, source permissions or a scheduler. Actual user choice/host access remain necessary. Do not automatically migrate older prose-only dispositions, select a new date or replace existing history.

## Record the user's chosen condition

Append an event through `proposals.py event STATE PENDING_ID EVENT_JSON`. The JSON must contain status=deferred, a nonblank deferral_reference to the actual user decision, and exactly one of:

- revisit_on: a confirmed ISO date/time with explicit timezone offset.
- revisit_trigger: an exact named condition, such as a user-confirmed project milestone.

For example, after the user actually chooses a named condition:

```json
{
  "status": "deferred",
  "revisit_trigger": "user-confirmed-project-milestone",
  "deferral_reference": "Actual user reply/chat reference confirming this condition",
  "note": "Retain existing candidate evidence and questions until the agreed condition"
}
```

For a date/time, replace revisit_trigger with a real confirmed value such as `"revisit_on":"2026-11-16T09:00:00-05:00"`. This is an example, not a default date. Do not guess a timezone or boundary for a date-only response; use the user's already confirmed interpretation or resolve the ambiguity one question at a time. Do not create a scheduled task merely because a revisit date exists.

The helper creates a new deferral_id and resets its offered marker. Facts, missing fields, questions and existing events remain preserved unless an authorized event explicitly changes them. An unchanged weekly run must not create another deferred event, move the date forward or reset its offered marker. Rescheduling/rearming requires an actual user decision with its reference, even when the condition text is unchanged.

## Read the review queue

```text
python <plugin>/scripts/proposals.py list STATE
```

The helper exposes questions_to_ask separately from the preserved original questions. Use questions_to_ask for the conversation. While a deferred date is in the future or a named trigger is absent, it is empty. The list command prints only this gated question list and revisit metadata. Readiness values are waiting_for_date, waiting_for_trigger, eligible, already_offered and not_deferred.

A date is eligible at/after its exact offset-aware instant. Named conditions require an exact match, never substring/fuzzy inference from task names, a routine cycle, web/email content or the mere arrival of a broader-review week. When the actual named condition is established, read the queue with:

```text
python <plugin>/scripts/proposals.py list STATE --trigger "EXACT_CONDITION" --trigger-reference "Actual trusted request/evidence reference"
```

For a user-requested test, pass that trigger only after a human actually requests the test. Never equate a weekly automation firing with that request. Multiple --trigger flags are supported when their actual conditions are established. The reference is an operator assertion, not authentication. Listing is read-only and does not consume a trigger, record delivery or reserve a question against another session.

Eligible means the user may be offered the retained question; status remains deferred until the user resumes/answers or makes another disposition. Recheck current records/evidence before presenting an old question. Deduplicate rediscovered candidates against prior dispositions; rediscovery or a selected broad category is not itself permission to bypass a deferral. New evidence can be retained privately without automatically asking again. A linked proposal's current stale/conflict/recovery status remains visible separately; question suppression never makes an interrupted save safe or grants approval to apply it.

## Record one actual offer

Present one focused question using the host's question capability or the established chat fallback. After the question was actually offered, save its cycle/reference:

```text
python <plugin>/scripts/proposals.py offer-revisit STATE PENDING_ID --cycle-id CYCLE_ID --offer-reference "Actual question/tool/message reference"
```

For a named trigger also supply the established --trigger and --trigger-reference. The helper refuses an unmet condition, repeated offer or terminal item. It appends a revisit_offered event tied to the current deferral_id, with timestamp, cycle and question reference. It does not send a question or prove the user saw it. Do not record an offer that was merely planned. Native question delivery and file persistence are separate host actions; avoid concurrent sessions presenting the same question from a stale read-only listing.

After a recorded offer, questions_to_ask stays empty across later cycles and repeated occurrences of the same trigger. An unanswered question is not a new weekly nudge. Do not infer an answer or automatically move its date to make it eligible again. If the user says a question disappeared or asks to resume, use that actual response to continue; do not pretend an offer proves delivery or understanding.

Offer/event writes share the private-state writer lock with other cooperating helper updates. Only one concurrent offer record can succeed. A stale offer event for an older deferral_id cannot suppress a newly rescheduled deferral; replay reports ignored_revisit_events without rewriting those events. If persistence is unavailable or interrupted, report that rather than claiming the offer/disposition was saved, and inspect existing state/conversation before any retry.

## Resume or close

The user may resume early, answer an offered question or request a later review. To return to active fact gathering, append status=needs_information with a nonblank resume_reference to that actual response/request. Preserve or explicitly update facts/missing_fields/questions as appropriate. To reach awaiting_approval, existing completeness/proposal checks still apply. Public changes still need exact proposal approval and linked approval evidence.

Rejected, superseded and applied items remain closed. A deferred event or overdue date cannot reopen them; create a new linked candidate for distinct follow-up work. A linked historically verified save closes an otherwise open item as applied, preserving historical/current-drift distinctions.

For legacy prose-only deferrals, continue honoring the user's saved intent and existing task instructions. Do not treat needs_information as permission to ignore a clearly documented deferral. Prepare a separate exact before/after private-state migration for approval; append a new structured event after approval, preserve the old note as dated history, and clarify outdated scheduling statements without rewriting historical events. No universal parser can safely invent dates/triggers from arbitrary prose. Until migration is approved, report its structured-state limitation and keep the known question suppressed procedurally.
