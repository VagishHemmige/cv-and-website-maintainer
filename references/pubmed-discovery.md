# PubMed access and identity

## Check the actual search path

Before the first PubMed call in a run, inspect the selected available tool,
current host network restrictions and any applicable authorized access. Reuse a
working authorized connector or browser tool when it covers the required query,
window and pagination. Do not switch tools to evade an access denial. A source
selection permits the intended search scope; it does not grant host network
access. Conversely, network access does not authorize a new source or scope.

If the selected command requires network access known to be restricted, use the
host's normal approval/escalation flow for that specific call before attempting
it. Do not deliberately repeat a known blocked command first. Where the host
does not expose advance network approval, use its documented access flow and
report the limitation rather than invent a permission tool or blanket grant.
Do not edit host security settings, request unrestricted network access, probe
arbitrary sites or install dependencies as a preflight.

An unanticipated DNS, proxy or connection failure may be sandbox-related.
Follow the actual host's escalation requirements for that failure; do not label
it an empty PubMed result or proof of an NCBI outage. If an authorized retry also
fails, report the observed error and incomplete coverage rather than loop.
Respect provider error/rate-limit responses and actual available access.
Continue independently permitted local checks and other authorized sources.

Access checks, permission approval and successful connectivity are not a
completed discovery search. Keep fixed bounds and the exact saved query scope,
cover every intended page/subquery, and durably save results before checkpoint
completion. Denied, unavailable, failed or partial searches leave the previous
successful cutoff unchanged. Never broaden a query or change its source key to
bypass a blocker; intentional query changes follow scope reconciliation.

## Ask only for identity clues that matter

Read the saved full name and confirmed search_names, identifiers, affiliations
and topics, plus applicable prior confirmations and deferrals. A null optional
field alone does not require a question or restart the setup questionnaire.
Use the available confirmed identity to construct the authorized search.
Do not invent variants, ORCID, affiliations or topic restrictions to fill blanks.

Compare source PMID/DOI, normalized title and actual author/context evidence
with authoritative publication records. A reliable match to an existing item
can resolve duplicate triage without collecting every optional identity field.
Matching a DOI establishes the matching work, not that every author or a
same-surname candidate is the user. Never accept surname-only identity matches.
Do not use an affiliation or topic as an unapproved hard filter that could hide
older or interdisciplinary work.

Ask one focused question only when missing identity evidence prevents a usable
author search or leaves a consequential candidate match uncertain. Explain the
specific uncertainty and request the smallest useful clue; keep that candidate
pending and continue independent work. Honor saved deferrals and suppress
repeated unanswered identity questions across cycles. Do not repeatedly demand
all missing identity fields.

A factual answer can inform the candidate under review. Persisting it as a new
profile preference requires the existing exact profile-proposal approval
workflow; do not silently populate identity fields from publications, email or
the current conversation. A changed saved query still needs its own scope and
checkpoint reconciliation. Discovery proposes candidates only; it neither
imports to Zotero nor edits the bibliography.
