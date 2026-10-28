# Optional approved sender filters

No sender/domain filters are active by default. Never invent regexes or personal/academic-domain exclusions to shorten a triage display. A filter on the displayed result list can hide evidence just as a provider query can. Keep every returned message available for normal triage unless a current, explicitly approved private rule covers it. Academic domains and institutions are not default exclusions. Existing candidate/activity exclusions are separate and do not authorize sender filtering.

If a user wants a sender rule, propose its exact account, bare address or DNS domain, subdomain behavior, reason and human scope reference in discovery.sender_exclusions through the normal exact profile-proposal approval workflow. Installation, an unrelated rejection or this document grants no rule. Missing/null/empty means no configured filters. Do not expand a rule to other accounts. The generic rule shape is:

```json
{
  "id": "stable-user-rule-id",
  "account": "explicitly-approved-account-identity",
  "kind": "domain",
  "value": "example.test",
  "include_subdomains": false,
  "reason": "Actual user-selected scope",
  "confirmation_reference": "Actual human scope decision reference; exact profile approval retained in its receipt"
}
```

The example is not an active preference. kind is address or domain. Domain matching normalizes DNS case/IDNA and uses exact boundaries; subdomains require explicit include_subdomains=true. Address rules require a bare mailbox, preserve local-part case and aliases, normalize its domain and require include_subdomains=false. Never match display-name substrings. Regexes, wildcards, address groups, multi-address From fields, malformed/unsupported/ambiguous headers and control characters cannot silently exclude messages; retain affected IDs for inspection. The parser supports conservative ASCII dot-atom local parts; unsupported quoted/international local parts remain for review. Sender parsing is not factual evidence that an academic activity occurred.

## Read-only filtering and reporting

After retrieving and deduplicating authorized results, retain minimal private metadata using only id and from for each message. Do not put message bodies, personal-domain regex literals or unrelated sender names into exported reports/tool arguments. Use a private input file inside authorized STATE and run:

```text
python <plugin>/scripts/sender_exclusions.py STATE PRIVATE_MESSAGES_JSON --account ACTUAL_AUTHORIZED_ACCOUNT
```

The helper reads the current canonical profile and only the rules for that account. It neither searches nor modifies email, preferences, records, candidate dispositions or checkpoints. Returned retained_ids include ambiguous senders, with sender_review_ids as a subset for inspection. excluded entries contain message IDs and matched rule IDs only. Save the aggregate counts and rule IDs in the private coverage report and disclose how many unique returned messages were excluded. Per-rule counts can overlap; never sum them as unique-message coverage. Filter outputs omit raw sender headers. Preserve needed private source evidence under existing retention permissions; do not retain unrelated correspondence merely for debugging.

Filtering does not prove the provider searched everything or allow skipping pagination. Record actual returned/deduplicated counts, excluded counts, retained/inspected coverage and limitations separately; do not report an excluded message as examined relevant evidence. If no rules exist, inspect results normally rather than recreating a filter in code. If configuration is malformed, report filtering pending and do not invent replacement rules. Unknown sender parsing retains the message; use normal privacy/source triage rather than dropping it. Existing checkpoints stay as historical evidence; a new historical search or changed provider-query scope needs its applicable approval and independent coverage handling.
