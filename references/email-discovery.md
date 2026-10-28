# Email search coverage

Use the packaged [query catalogue](email-queries.json) for Gmail. Its groups and quoted phrases use [Google's documented search operators](https://support.google.com/mail/answer/7190?hl=en). This is a keyword recall aid, not proof of exhaustive coverage. It searches terms in subject/body, rather than requiring them in subjects. Queries intentionally overlap; deduplicate by provider message/thread IDs and authoritative records. Inspect the relevant evidence before making a candidate. Mentoring/project terms never establish a relationship, and an invitation, acceptance, nomination or renewal reminder never proves completed activity or current status.

## Select and prepare

Read saved account and source/category selections and applicable deferrals first. Package contents never grant permission to another account, category, attachment or calendar. If category scope is unclear, resolve it once before searching; do not expand it to the whole catalogue implicitly. A deferred check-in category does not itself revoke existing discovery permission, but must not generate renewed questions contrary to its revisit condition.

Run the read-only planner with the discovered Python runtime and only authorized category IDs:

```text
python <plugin>/scripts/email_queries.py --identity APPROVED_ACCOUNT --categories abstracts talks teaching
```

It prints source, subqueries, exact stable query strings, unselected categories and a coverage limitation. It neither searches mail nor writes state. Save that definition in the authorized private run evidence. Pass its source and subqueries unchanged into the existing checkpoint-begin request along with the real cycle ID, fixed upper cutoff and connector timezone interpretation. The generated source identity includes the catalogue version, selected categories and exact query text; category order does not change it. A connector's query grammar must actually support Gmail syntax. For another provider, prepare a reviewed equivalent with its own provider/scope identity and exact strings; do not submit Gmail strings and claim equivalent coverage.

## Changed scope and prior runs

First run `python <plugin>/scripts/private_state.py checkpoint-sources STATE` to inspect exact saved definitions. Reuse the appropriate saved definition verbatim when the scope is unchanged. An unfamiliar definition for an existing provider/account is blocked by checkpoint-begin until an intentional, authorized change is explicitly acknowledged with --acknowledge-new-scope and --scope-change-reference. See [private-state scope acknowledgements](private-state.md#discovery-runs). Neither flag grants permission or migrates old coverage.

Compare the definition with existing checkpoint sources before beginning. A new catalogue, selected category set, query customization or account is a new scope. Do not relabel an earlier narrow search as covering it or copy an older cutoff. Report the change and obtain any required human authorization for expanded scope/historical re-coverage. Hold that new search until authorized; retain the old evidence and checkpoints. The new scope uses the saved initial look-back, not the narrow scope's overlap. Do not change profile preferences or live checkpoints merely to adopt this catalogue. Previously stored scopes remain readable.

Meeting names can support additional searches only when relevant and authorized. Declare their exact queries and new scope before searching; never silently append undeclared searches under a catalogue identity. Do not add sender/domain exclusions or ignore academic domains without an approved exclusion. Record exclusion scope and counts without unrelated sender names or raw mail.

## Execute and complete

Follow [optional approved sender filters](sender-exclusions.md). Never improvise sender regexes or hide returned messages from the triage display without exact account-scoped approved rules. No academic-domain defaults apply. The read-only helper retains ambiguous senders and returns rule/message counts without raw sender literals; report exclusions separately from search and inspection coverage.

Begin the checkpoint before connector calls. Add the returned fixed window to each query using the connector's documented time semantics. Save both the stable query and exact executed query with bounds privately. Inspect every response and exhaust pagination for every declared subquery, including zero-result responses. Deduplicate overlapping results. Unsupported syntax, truncation, rate limits, inaccessible results or an unfinished query mean partial/failed coverage: use checkpoint-fail and retain the previous successful cutoff. Save minimal report/results before checkpoint-complete. The existing helper checks all declared query IDs and pagination assertions, but cannot verify a remote search or semantic recall.

## Report to the user

Before presenting email-derived candidates, follow [approved candidate exclusions](discovery-exclusions.md) using actual activity evidence. Report excluded-candidate counts separately from message/search counts. Candidate rules never authorize dropping unread mail, adding sender/domain filters or broadening source access.

The check-in must name the selected account, date window, categories actually searched, categories unselected/not authorized, failures and important keyword limitations. Say, for example, "Completed the declared keyword searches in the selected account; this is not a search of all mail or other accounts." A zero-result category means no matching candidate in those searches, not no activity. Save catalogue version, exact queries, exclusion counts, actual pages/results and source key in the private report; do not leave these solely in transient tool logs. Do not claim an older run missed an email merely because a record exists; its email may be in another account or never have existed.
