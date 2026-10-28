# First-time initialization

This module supports a resumable private interview, read-only tool-path observations, CV text staging, structural candidate coverage and private starter staging. It does not provide automatic OCR, factual CV parsing, a repository/account installer or deployment engine. An assistant can coordinate separately approved host actions; report unsupported host actions honestly. Reuse the current site/YAML/R-officer approach initially; arbitrary CV template adaptation is deferred.

## Interview and bootstrap

Inspect existing instructions/profiles/jobs before new setup. Choose real private storage outside the public project and any Git checkout, with actual access. If it does not exist, ask for the user's storage choice/creation authorization through the host first. Do not use a public folder temporarily. Existing config.json routes to configuration, not fresh initialization. No private profile is silently backfilled or migrated.

Using an existing authorized Python:

```text
initialize.py start STATE --private-storage-confirmed --reference ACTUAL_USER_STORAGE_CHOICE
initialize.py status STATE
initialize.py answer STATE ANSWER_JSON
initialize.py probe
```

ANSWER_JSON contains one key/value plus the actual response/reference. Keys are outputs (cv/website/both), starting_point (fresh/existing_website/existing_local_project), cv_source (absolute file or null for explicitly skipped), project_path (absolute existing/new destination or explicitly deferred null), assistance (guidance/prepared_changes/approved_execution), github_account (have_account/need_help/not_needed/defer), integrations (list of zotero/email/calendar/github/editor_extensions, or []). Record an established not-needed choice without interrogating the user about irrelevant tools. Answers can be corrected with new actual response/reference; previous values remain in private history. Null means skipped/deferred, not ready. Supplementary identity, visibility, accounts, format, retention, cadence and permissions are carried into the full conditional configuration questionnaire when needed; this short bootstrap is not complete preference setup.

Additional bootstrap keys are website_cv (yes/no/defer, for website/both) and cv_format (docx/docx_pdf/defer, for private CV/both). The helper asks only applicable questions and retains saved answers on resumption. Follow [optional CV PDF initialization](cv-pdf-initialization.md) before preparing any PDF/public-CV setup. These choices do not change the Word-only starter or authorize public files.

For supplementary answers outside these bootstrap keys, use the private pending-answer procedure in preferences.md. Combine confirmed answers into one exact approved profile proposal only after the actual project exists; initialization.json is not config.json. Keep deferrals pending and preserve interview evidence after profile creation.

The helper stores initialization.json and byte-preserved prior snapshots under initialization-history with a cooperating-writer lock. It never overwrites config.json. A stale lock or interrupted staging folder requires inspection; never delete history/locks to force a retry or infer success from a partial folder. operation.json/completed.json distinguish staging start/completion. Do not claim native permissions or independent approval authentication from helper flags/references. Private state is plain local storage, not encrypted or certified clinical storage.

probe observes PATH and a bounded Windows RStudio Quarto location; found paths are not tested runtimes/accounts. Use runtime.md and the host dependency locator for actual R/yaml/officer/Quarto/editor/Git checks. Only selected output paths require relevant tools. Offer current official installation guidance; each install/account/integration/remote action needs its appropriate real authorization and host capability. Do not turn missing technical knowledge into a demand to run unexplained commands.

## Initial CV source

```text
initialize.py extract STATE SOURCE --source-screening not_flagged --private-processing-approved --reference ACTUAL_APPROVAL
```

SOURCE must match the selected source. This reads an original without copying it to the website; extracted text is private. DOCX body/table paragraph text plus header/footer text is extracted with locations. Footnotes/endnotes/comments and visual reading order remain limitations. PDF uses pypdf text extraction, flags empty-text pages and does not OCR; scanned/complex files may require a different source or manual review. TXT must be UTF-8. Text order can differ from visual order. Encrypted/empty/unsupported files stop. The 32 MiB source/64 MiB expanded DOCX limits are staging safeguards, not content validation.

Before extraction screen for possible patient identifiers and warn/pause when present, even though CVs commonly have the author's own private contact details. Clarify intended private handling and public exclusions. Screening flags are assistant assertions, not automated PHI detection. Do not put extracted contact information into candidate public records; the source header can be classified excluded/context with reason. Keep source hash and limitations in later review.

## Coverage ledger and proposed records

```text
initialize.py ledger STATE EXTRACTED_JSON LEDGER_JSON
```

Ledger shape:

```json
{
  "source_sha256": "hash from extracted.json",
  "coverage": [{"source_id":"S00001","disposition":"candidate","candidate_ids":["entry-1"],"reason":"Maps the source activity; dates still need review"}],
  "candidates": [{"id":"entry-1","source_ids":["S00001"],"target":"honors.yml","record":{"title":"Source wording"}}]
}
```

Every extracted segment must appear once; candidates and source coverage must link reciprocally. Other dispositions are context/excluded/unresolved with reasons. Titles/headings and contact lines are not activities. One line may contain several entries; one entry may span multiple lines. The assistant must inspect splits/merges and original layout, identify missing text, preserve roles/dates/author order and ask ambiguities one at a time. A structurally complete ledger is not an entry-complete or factually approved CV. No candidate is imported by this command, and incomplete record dictionaries are deliberately permitted for staged review. Existing records/publications must be checked for matches, conflicts and duplicates before proposals. Never reconstruct a relationship from incidental names.

## Starter and transition

```text
initialize.py stage-starter STATE --reference ACTUAL_STAGING_REQUEST
```

assets/starter.zip contains the 41-file empty-record starter, including LICENSE, public site.yml, root-page Quarto configuration, R source, templates/cv-styles.docx and private-header example. No personal records, original CV/contact files or images are included. A copyright attribution in LICENSE is intentionally retained. Reference formatting has been separated from source content/metadata; general template provenance and visual Word approval are not established solely by XML sanitization. The starter's CV and nine-page site were tested with empty and synthetic records; screenshots/visual Word certification and a first public deployment are not implied.

New staging receipts also report cv_output_choices. Status recomputes them from current answers; older receipts remain historical. Recheck choices and privately prepare the coordinated PDF/page/config/style adaptation when requested; an unchanged staged ZIP is not PDF implementation.

Private staging creates no project, repository, profile, account or schedule. Inspect the actual chosen destination, existing Git/remote state and ownership before a concrete creation plan. Preserve existing source and uncommitted changes. Obtain approval for the named new folder/files and identity settings, then use authorized host file operations; never silently merge over an existing site. Set site.yml and the website title/footer coherently. Create approved record proposals only after the supported consumer/runtime/profile boundary is real. Empty YAML is [], never invented placeholder activities. Keep a verified backup and actual approval evidence for live imports. Zotero exports, private CVs and public material have distinct authority.

After establishment, configure-academic-records owns full preferences and maintenance schedule setup. It must inspect the same authority and reuse answers rather than starting a second questionnaire. Verify output commands and actual saved/generated/published state separately. The initial look-back, source accounts, chat scopes and weekly/broader review choices are asked when relevant, not assumed during CV extraction. Source failures do not count as zero results or successful coverage. No independent automatic stage transition or deployment is supplied in this version.

## Approved execution branch

Users selecting approved_execution can now use [setup-execution.md](setup-execution.md) for concrete new-project execution plans, actual approval evidence, local creation/R-or-Quarto commands, checked public Git commits and gated push. The initialization staging commands above remain non-executing. Host installation, account/remote creation and deployment verification are separate authorized tool work. This branch preserves each user’s established project and output-assistance choices; routine maintenance must not restart initialization.

For the supported personal-site target USERNAME.github.io, use [personal-site deployment](personal-site-deployment.md). The local planner/checker scripts/personal_site.py creates no repositories or settings and does not replace actual host verification.

## Adapt website sections

Use [page adaptation](page-adaptation.md) for requested additions or hidden sections. The bundled [YAML-driven example](../examples/yaml-records.qmd) is an adaptation pattern, not a required grants page or a new schema. Website display choices are distinct from records/CV maintenance choices.

### Staged source versus operation metadata

stage-starter returns project_source_root, the nested starter directory containing _quarto.yml and R/cv.R. Inspect and adapt that directory's public-source subset for setup-execution source, then obtain exact setup approval. It is a private staged source, not the user's actual project or blanket public-use approval. metadata_folder contains operation.json and completed.json; keep it private and never copy the operation wrapper into the project. The legacy folder field remains an alias of metadata_folder for compatibility. status exposes these fields inside the saved operation result so resumed setup can locate the same source. Older completion receipts lack these fields: inspect their recorded folder/starter layout and verify the expected files, without rewriting historical receipts or assuming the wrapper is a project root. Missing layout remains an interrupted staging operation for inspection, not a successful stage.

### Initial import coverage by requested output

Before initial import approval, show a readable table for each candidate: activity, destination, expected Word-CV inclusion, expected website inclusion, evidence and any omission requiring a decision. Inspect actual R/page consumers and applicable display filters, visibility choices, dates and field completeness. A file being read somewhere is not proof that this particular record will appear. Use CV only / Website only / Both / Neither / Pending for the user's selected outputs. For a CV-only user, website is not requested rather than an omission. If goals are unknown, keep overall coverage Pending.

Optionally add private candidate metadata (outside record):
```json
"output_coverage": {
  "cv": {"status":"unsupported","reason":"Current Word generator has no teaching section","reference":"Reviewed staged R/cv.R consumer list"},
  "website": {"status":"included","reason":"Teaching page renders this session","reference":"Reviewed teaching.qmd and fixture preview"}
}
```
Each supplied assessment has status included/excluded/unsupported/pending, nonblank reason and reference. included means expected inclusion based on actual inspection, not proof of output generation or visual review. Do not hard-code a consumer map from the bundled template into another user's project. Missing assessments stay Pending. The ledger command stages output-coverage.json privately beside ledger.json and returns its path; its checks validate operator assertions only. Candidate output_coverage is import-review metadata, never part of the record dictionary/public YAML. Old ledgers without it still stage successfully, with Pending coverage; historical ledgers/receipts are not rewritten.

Explain omissions in the source CV when both/CV output was requested. Obtain a conscious acceptance, defer the affected item, or propose a separate template/page change. Exact record approval alone must not be described as accepting an undisclosed output omission. Never silently invent a new Word section, discard records, duplicate data into a page, or certify overall output completeness from structural ledger coverage. Save the actual user's decision with the import review/approval history; this report does not itself grant acceptance or authorize any write. After authorized generation, inspect the expected entries in the actual outputs and report discrepancies separately. Teaching may currently be website-only in the bundled starter: confirm current consumers rather than promising it appears in the Word CV.

## First-time publication-library setup

For publications, [zotero-initialization.md](zotero-initialization.md) connects CV/PubMed candidate reconciliation, Desktop/integration readiness, optional account/sync, reviewed imports and scoped bibliography export into the initial setup. Source searches and account/export actions require their actual scopes; an empty starter bibliography is not completed publication reconciliation. scripts/publication_setup.py can stage a private readiness report in existing bootstrap state; it observes no live systems and performs no imports, searches, export or configuration changes.

## Starter talk placement
The starter Word CV groups talks.yml records by their explicit category: invited (Invited Presentations), conference (Conference Presentations), grand_rounds (Grand Rounds), teaching (Teaching Presentations). Only populated groups receive headings. Each group retains the existing date ordering and entry formatting. Missing or unsupported categories require clarification; do not infer them from titles/venues or label all talks invited/extramural. teaching.yml sessions remain a separate website-only consumer. Existing owner generators are not automatically migrated.

For reviewed bundled-starter CV execution, follow setup-execution.md to pin academic_records.cv_filename in the exact R command and match expected_files before approval. A later execution date must not silently change the approved output name. Existing/manual project behavior remains unchanged.

## Dependency and writer-lock blockers
A missing or unimportable pypdf installation stops PDF extraction with runtime/library checks and a DOCX/TXT alternative. No package is installed automatically; a source-format change still requires selecting/approving that source. An existing initialization writer lock may belong to an active worker or an interrupted operation. Its age alone does not prove it is stale. Preserve the lock and history, inspect actual operation/process status and agree reviewed recovery before any cleanup or retry. The helper neither steals nor automatically removes a pre-existing lock. Permission errors remain host-access issues, not proof of missing packages.
