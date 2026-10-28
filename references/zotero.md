# Zotero capability and review protocol

## Available local route

This workflow delegates actual operations to the available Zotero companion skill/tools. The plugin adds review instructions, not a bundled Zotero server or independent access. Resolve installed instructions/helper dynamically. Do not package another plugin's code, a user's profile path, credentials or a fake app binding.

With the current companion: status --json and probe --json inspect readiness; search QUERY --json and collection/item reads establish existing records; selected-target --json inspects destination. The local API under /api is read-only. Connector import-bibtex/import-ris can add records to the selected library/collection. The supported writes are additions, not edits of existing metadata. A future editing-capable route must be separately configured and verified before use; the existence of web API documentation is not evidence of credentials or permission.

The selected-target output can include extensive unrelated tags: retain/show only library and collection identity, editability and relevant target IDs. A currently selected collection is an observation, not a preference. If the profile says no collection, select/verify the library root before import. Store destination defaults outside the plugin.

## Duplicate and outcome checks

DOI normalization removes DOI URL/prefix and case differences. A PMID must match its exact identifier. Title matching normalizes punctuation/spacing for candidate detection but cannot alone settle a different edition/version/erratum. Author identity, container, year and source evidence resolve uncertain matches. Search all relevant target-library results; do not infer absence from a limited page or an export that may be incomplete.

For an import, compare baseline library keys/versions or duplicate-check results with the post-import item(s). Keep a private receipt with proposal ID, payload hash, user approval reference, import session, resulting item key and verification status. Connector success alone is not proof of correct collection membership or inclusion in an auto-export. Never retry an uncertain import until a library read settles whether it already happened.

## Capability checks before claiming success

- No approval: never call a write/import command.
- Duplicate exists: return existing item, no import.
- Missing required facts: save pending questions, no import.
- Destination changed after approval: stop and obtain a new reviewed proposal.
- Correction requested through local read-only API: save field-by-field correction proposal; do not PUT/PATCH or reimport.
- Import success but verification/export inclusion unknown: report those checks as incomplete.
- Import timeout: reconcile before retry.
- Automatic export side effects unresolved: clarify or postpone any write that could exceed authorized scope.
- Scheduled run: discover/report only, never import.

Do not test this workflow by creating dummy items in a real library. Use mocked/non-writing checks, then perform the first genuine import only for a user-approved real proposal. Disclose whether live writes have actually been tested.

## First-time library and export setup

Use [zotero-initialization.md](zotero-initialization.md) when Desktop, library contents, integration or export setup is missing. Local Desktop use does not require an online account; online sync is a separate choice. Current companion export-bibtex accepts --item-key or the local library and has no collection-selection flag: a selected collection is not an export filter. Verify an appropriate scoped native/integration export rather than silently exporting a mixed library or claiming the root-only helper reads any arbitrary group library. No raw CV or private fields/attachments belong in the public bibliography.

## Separate import and bibliography delivery outcomes
After each approved addition, report separately: (1) item verified in the approved Zotero destination, (2) expected item present in the configured bibliography with correct metadata and a stable citation key, and (3) requested CV/site outputs regenerated and checked, or pending/owner-managed. The third outcome never follows from the first two alone.

For an automatic export, use the saved verified source/target/timing and inspect the actual expected file and item identity, not merely file existence or modification time. Check parsing, relevant identifiers/title/authors and citation-key continuity. A file may be unchanged because the item was already included; unchanged bytes alone neither prove failure nor new delivery. A collection export must actually include the imported item. Use bounded rechecks consistent with observed timing; if paused, delayed, errored or outside the export scope, report Zotero saved / bibliography pending with the reason and next authorized step. Never reimport the paper, hand-edit the generated bibliography, silently reconfigure exports or force a refresh as a workaround. A manual refresh/export requires matching destination-write authorization.

Keep import receipt and export-verification evidence/status separately in the existing private continuity records. Missing output access means verification unavailable, not import failure. Resolve setup via zotero-initialization.md, reusing saved answers and current evidence.


## Private continuity and deferred questions
Use [structured deferrals](deferrals.md) for postponed questions and preserve their revisit conditions. Repeated discovery alone does not reopen a settled candidate. Use the [private-state helper](private-state.md) for approved preference changes, source-search checkpoints and reminder progress under their respective rules. Those operations do not import into Zotero or verify bibliography export; keep library import/export evidence separate and never advance successful search coverage from an import receipt alone.
