# CV and Website Maintainer change history

## Unreleased: early Claude support

- Add Claude Code manifests (.claude-plugin/plugin.json and marketplace.json). Install with `/plugin marketplace add VagishHemmige/cv-and-website-maintainer`, then `/plugin install academic-records@cv-and-website-maintainer`. Checked to install all six skills and the scripts; full workflows in Claude not yet demonstrated.
- Use the display name CV and Website Maintainer where people read it. The identifier academic-records, skill folders, profile fields, handoff.json layout and ~/.codex/academic-records/ paths are unchanged.
- In Claude: AskUserQuestion for questions; the same private-state files as Codex; no scheduled reviews yet (automation_id never holds a Claude task ID); handoff by copyable block only. .claude folders are protected from publication like .codex.
- README and installation guide give the public GitHub source and a Claude Code install section. Codex manifests, the local marketplace example and the starter ZIP are unchanged.

## 0.2.0

- Mark the expanded initialization workflow with a minor-version release, including the optional private PDF and public website CV choices introduced in 0.1.81.
- Rename the display name to CV and Website Maintainer. Preserve the internal academic-records package identity, skills, existing settings and sharing.
- No additional runtime or starter changes in this version.

## 0.1.81

Initial setup records applicable private CV format and public website CV PDF choices, preserves deferrals/resumption, and reports them in status/starter receipts. Added a coordinated setup guide grounded in the 2026-10-28 owner implementation, covering source files, Word/Windows and checker dependencies, private/public outputs, PDF review and publication. Starter ZIP and routine maintenance are unchanged; PDF adaptation remains separately reviewed source work.

## 0.1.80

- Warn on valid numeric dates whose month/day components lack zero-padding, including teaching session lists. Suggestions preserve the original year/month/day precision and never rewrite records.
- Keep existing invalid-calendar/full-date errors; do not suggest invented days or alter null/present/year-only dates.
- Add six real-R tests for warning coverage, precision, invalid values, starter chronology/stable ties and an approved disposable corrective proposal. Live corrections remain separately approval-gated.


## 0.1.79

- F13: add conservative reusable audit-surface redaction for raw wrapper arguments, commands/output, connector bodies, file changes and duplicated timing commands. Unknown bodies are omitted; exact reviewed Gmail query arguments require a separate allowlist.
- Add structural and sender-filter-code checks, omission hashes and guidance for original-snapshot exports, transformed-file provenance, final archive scans, privacy limits and explicit external-sharing authorization.
- Add nine synthetic leak/duplication/schema tests. The local October 19 audit exporter was separately repaired and a redacted replacement built without changing live profile, task, route or records. Redaction is not de-identification or a public-safety certificate.


## 0.1.78

- F12: remove only the exact obsolete first-search placeholder note in the same atomic commit as successful checkpoint completion. Preserve unrelated notes, original before-history and all failed/partial-search safeguards.
- Clarify that run/cutoff evidence governs coverage and CV/site observations require current evidence. No historical output-verification backfill or immediate live checkpoint cleanup.
- Add eight checkpoint-note regression tests, including zero/nonzero success, failure, incomplete pagination and interrupted commit/recovery behavior.


## 0.1.77

- F11: clarify selected-tool PubMed access checks, scoped host approval when required, honest failed/partial coverage and unchanged successful cutoffs. Connectivity is not completed discovery; avoid repeat known-blocked calls and arbitrary probes.
- Ask for identity clues only when needed for a usable search or consequential ambiguity. Optional null fields do not restart setup; preserve deferrals and exact profile approval rather than infer saved preferences.
- Add eight guidance-contract checks. No live search, profile, task, route or record edits.


## 0.1.76

- F10: add approved_save.py to capture exact private human-response context and delegate a single YAML save to the existing proposal helper. Preserve exact approved bindings, real/unknown message times, unique evidence, validation, backups, stale-source guards and recovery status.
- Prefer packaged CLI commands and JSON inputs over routine custom Python wrappers. Reuse existing confirmation batching; consumer inspection may be reused within a run only after checking unchanged hashes, fields, dependencies and instructions. Validation is never cached.
- Add synthetic approval/failure/interruption regressions and real-R subprocess integration. No live records, profile, task or route changed; no runtime or prompt-count guarantee.


## 0.1.75

- F9: reduce avoidable review turns with direct category answers, explicit deferral choices, reuse of supplied facts and corrections, and continuation of the eligible review queue.
- Preserve necessary clarification, pauses, one question at a time, deferred categories and exact-proposal approval. Combine a choice and approval only after displaying the exact validated named proposal; questionnaire answers alone never approve unseen changes.
- Add seven instruction-contract checks. These checks do not simulate host UI behavior or guarantee fewer clicks. No live profile, task or record changes.


## 0.1.74

- F8: prohibit improvised sender/display-name regexes and default academic-domain exclusions. Add optional exact private account-scoped address/domain rules, with explicit subdomain behavior and no active defaults.
- Add a read-only sender-filter helper with conservative header parsing, retained ambiguous senders, unique-message and overlapping rule counts, and outputs without raw sender headers. No live filters, queries, checkpoints, records or preferences changed.
- Add synthetic boundary/lookalike, account scope, malformed-header, overlap-count and read-only CLI regressions.


## 0.1.73

- F7 plugin portion: support exact user-approved destination/activity exclusions in private discovery preferences, with a read-only post-triage helper, excluded-candidate counts and explicit handling of uncertain classifications. No active default exclusions or inferred global rules from individual rejections.
- Keep recommendation, external promotion/tenure letters and journal/abstract/committee reviewing distinct. Exclusions do not change searches, erase records or alter prior rejections/deferrals. Personal profile application remains a separate exact approval step.
- Add synthetic rule-scope, count, ambiguity, malformed-input and read-only CLI tests.


## 0.1.72

- F6: compare raw-decoded source/candidate text and write proposal diffs as UTF-8 bytes, avoiding universal-newline mismatches and Windows doubled carriage returns. Preserve staged/applied YAML bytes and all historical evidence.
- Require the generated diff or a faithful labelled excerpt during exact approval. Add actual propose/apply CRLF and LF regressions, including a real-R CRLF save and verified backup check.


## 0.1.71

- F5: routine scheduler inspection first reads fresh authorized local task configuration, validating identity and available fields. Use host view for unavailable/invalid/conflicting evidence or host-only checks; retain native read-back after task creation/updates.
- Do not substitute recent cached verification, infer unexposed timezone/next-run facts or equate elapsed tool-call time with compute time. Add instruction contract checks. No scheduler/runtime implementation or live task change; prompt-speed improvement is not benchmarked.


## 0.1.70

- F4 plugin portion: add durable private staging and atomic batched history saves for routine no-change answers, with retained question/response references and displayed-source hashes. Expose saved answers through check-in-status. Refuse stale or conflicting evidence; repeated flushes do not duplicate history.
- Keep deferrals, exact record approvals and interruption-sensitive writes on their existing immediate paths. Add access-planning guidance without claiming a single approval grants later network/filesystem access. No host permission, profile or scheduler change.
- Add synthetic batching, recovery, no-write staging, stale-state and CLI tests.


## 0.1.69

- F3 plugin portion: add read-only local CV resolution from a fixed link or separately approved filename locator; report missing, ambiguous, inaccessible and changed outputs explicitly. Metadata never certifies content freshness.
- Add output_observed check-in events with private report hashes, precommit evidence checks and latest-per-kind retrieval. Observations do not alter preferences, dispatch/close submissions or complete broader reviews. Existing dated links are unchanged pending exact profile approval.
- Add synthetic resolver, freshness, race, retrieval and event-isolation tests.


## 0.1.68

- F2: add read-only checkpoint-sources to expose exact saved definitions and coverage. Block unfamiliar search definitions for a known provider/account unless an intentional new scope is acknowledged with a retained reference. Legacy unchanged scopes resume normally; no automatic checkpoint migration or new search permission.
- Add source reuse, no-write listing/refusal, query/version collision, CLI and acknowledgement-evidence regression tests.


## 0.1.67

- F1: add versioned Gmail category queries and a read-only planner; exact selected definitions identify a distinct checkpoint scope. Expanded searches require applicable authorization and an independent initial window. Require visible category/account/keyword coverage limits and retain old checkpoints.
- Add offline planner and checkpoint integration tests, including incomplete pagination and new-scope isolation. No live account, profile, scheduler or checkpoint migration. The reported abstract emails were in another account, not missed by the authorized search.


## 0.1.66

- Document local installation/distribution, prerequisites and first-session expectations; include a portable local marketplace catalog example and availability guidance. Distinguish source-verified instructions from pending fresh-account install testing; no audience, runtime or task changes.

## 0.1.65

- Add goal-specific local readiness table/JSON for selected runtimes, R packages, PDF modules and Git identity/signing, with bounded probes and official guidance. No installation, network, rendering or settings changes; preserve lightweight probe compatibility.

## 0.1.64

- N3: preserve copied interpreter metadata and ensure the POSIX fixture is executable before retargeting an alias. Keep the exact changed-binding refusal assertion; production behavior is unchanged.

## 0.1.63

- N1: exclude common R state, credential files and SSH private keys in setup/deployment checks and the new-project starter gitignore. Existing repositories remain unchanged.

## 0.1.62

- Documented user-reviewed manual reconciliation for an unconfirmed post-replacement interruption, preserving uncertain historical attribution and unchanged current bytes when accepted. Added crash-boundary regression coverage; no automatic repair or live-history migration.

## 0.1.61

- Removed redundant manual staging/backup/validation directions from the update skill. Retained helper safeguards, exact approval, consumer/resource inspection and explicit extra project requirements. Unavailable required validation leaves saving pending; no runtime behavior changed.

## 0.1.60

- Removed the personal R-directory fallback from the page-adaptation integration test. It uses explicit TEST_R_BIN or the parent of TEST_RSCRIPT, with a clear skip before staging when runtime configuration is unavailable. No production behavior changed.

## 0.1.59

- Replaced raw missing/unimportable-pypdf errors and bare existing initialization-lock errors with actionable blockers. No automatic installation, lock removal or retry; original sources and existing state are preserved.

## 0.1.58

- Named configuration versus first-time initialization explicitly in all six skill entry points. Missing preferences for existing records do not authorize new projects, repeated imports or competing profiles; inaccessible/corrupt state remains a recovery issue. No runtime or live setup changes.

## 0.1.57

- Added an optional simple starter CV filename for exact setup plans across date boundaries. Manual runs retain the dated default; existing output files remain protected. Documented matching the reviewed command and expected_files without silently changing old plans.

## 0.1.56

- Removed starter link placeholders and inaccurate missing-city Virtual labels; simplified theme wording, omitted empty CV sections/subsections and fixed grant punctuation when award numbers are absent.
- Generalized deferred-condition examples and made development-plan references optional. Preserved starter license attribution and all existing user projects.

## 0.1.55

- Clarified the publication-mode interview: recommend human preview for new users, explicitly explain agent-verified publication without a second confirmation, and preserve existing choices and authorized autonomy. No runtime behavior or settings changed.

## 0.1.54

- Added one early starter CV compatibility check for officer::run_tab, with installed-version and reviewed-upgrade guidance. Kept normal R missing-package handling; no version pin, installer or existing-project migration.

## 0.1.53

- Compared record errors independently of leading display row numbers, retaining full record context and diagnostic details. Counted occurrences to block new duplicate errors and retained strict exact comparisons before/after saving. No historical receipt or live record migration.

## 0.1.52

- Replaced the accumulated README implementation notes with a short current user guide covering all six skills, approval evidence, private setup answers, attachments, scheduled reviews and execution limits.
- Linked check-in and Zotero guidance to deferred-question handling; distinguished Zotero import/export receipts from discovery checkpoints and reminder progress.
- Added documentation checks. No runtime scripts, starter assets or live user settings changed.

## Through 0.1.51: retained implementation notes

The following notes were moved from the previous README. They summarize development through 0.1.51, not a complete release-by-release ledger or current operational instructions. Exact release attribution is not reconstructed. Follow the current skills and linked references for behavior and safeguards. Obsolete approval/test/workflow descriptions have been corrected during the move.


Deferred questions now have confirmed date/time or exact named conditions, a gated question queue and one-time revisit-offer history. Unanswered offers stay suppressed across later review cycles until the user resumes/reschedules; closed items remain closed. Legacy prose dispositions are not automatically migrated. See references/deferrals.md.

New YAML, PDF and preference saves require private approval evidence bound to the exact item/hash/destination. The actual response/context and known-or-unavailable message time are retained beside receipts with hash checks; older receipts stay unchanged and report missing evidence honestly. This is an audit trail, not independent authentication. See references/approval-evidence.md.

Staged attachment saves now compare only versioned attachment-relevant settings (resolved project, approval policy and attachments configuration). Unrelated check-in/setup changes no longer require another private copy or PDF review. Current destination, integrity and privacy/public-use checks remain required; legacy manifests keep conservative compatibility checks. See references/attachments.md.

Private-state updates now have a standard-library helper: reviewed preference proposals, serialized writes, verified backups and recovery receipts; source-specific discovery begin/complete/fail commands require fixed bounds, complete pagination assertions and durable reports before advancing coverage. It does not authenticate approval or prove remote search completeness. Installing this release changes no live profile, task or checkpoint. See references/private-state.md for commands, compatibility and concurrency limits.

Historical saves remain verified when records subsequently change: status reports changed_after_save and current differences without claiming the later edit was approved. Completed, rejected and superseded pending items stay closed; follow-up work uses a new linked candidate. Status/list preserve existing records and history.

Bibliography auto-exports are revalidated against the exact approved YAML rather than automatically invalidating every proposal. Changed validation warnings require renewed review; completion receipts identify the bibliography generation validated. See references/verification.md. No bibliography is written by this workflow.

Every concrete record change requires explicit approval before saving. First-use setup reuses established decisions. Keep incomplete candidates and follow-up questions in authorized private state. The Python proposal helper stages and validates changes, detects stale sources, requires exact approval evidence, backs up the target and verifies the write. The assistant must obtain actual human approval; the helper is not authentication or a security boundary.

Private skills-based plugin for local academic website YAML maintenance and discovery reports. It does not include a storage server or scheduler and does not grant filesystem, mail or chat-history access. Invocation requires host-provided authorized tools. A phone session works only if its execution environment can access the configured local project.

Workflows include initialization, configuration, record updates, discovery, Zotero updates and handoff. The optional Zotero workflow uses a separately available Zotero companion integration; it does not bundle a server or grant access. With the current local connector it can import approved new references. Metadata corrections remain proposals unless a verified editing-capable integration is available. Destination, duplicate checks, approval, post-import verification and export side effects are reviewed separately. The bundled read-only R validator requires R and the yaml package already available in the user's environment. Consumer inspection is still required; validator success is not a render/layout guarantee.

Examples: “I received a new teaching award”; “Add this abstract using this official program”; “Check PubMed, connected email and online media for possible updates; report candidates before saving.”

Identity, paths, source selection, review choices and scheduling are questionnaire answers stored in a separate private profile. No user's settings are bundled. Discovery scheduling is configured separately. No scheduled task, external connection or live record change is created by installing this package. Source access failures must be reported.

First-use compatibility is checked before proposals; the adapter requires the existing 13-file layout. Unsupported sites receive a suggested change report rather than empty files. After a save, the assistant gives a project-specific output handoff; rendering and publishing require the user's existing workflow/authorization.

Helper recovery: `status STATE PROPOSAL_ID` compares target hashes and receipts; `list STATE` also replays pending events. Interrupted saves can be saved_unverified, failed_before_write or conflict. Inspect write_attribution as well: matching bytes may remain unconfirmed, and a contradictory recovery history is a conflict. Inspect status, backup and the failure cause before recovery. A failed_before_write proposal cannot be reapplied: preserve its attempts/backups, resolve the cause, create a fresh proposal from current sources and obtain new exact approval even for an identical diff; never reuse the old approval. `verify STATE ID RSCRIPT` can finish verification of already-saved approved bytes and record completion without rewriting records; it cannot approve or apply an unapplied proposal. There is no automatic rollback. This helper does not lock out unrelated editors; avoid concurrent edits during an approved save.

Teaching, abstracts and presentations prompt for PDF/PowerPoint now, later or none. A separate resource-folder allowlist permits reviewed PDFs without changing the YAML schema. The helper detects local Windows PowerPoint, including Store installations, and exports PDF with macros disabled; local LibreOffice is supported when PowerPoint is unavailable. Request a PDF when neither converter is usable. Deferred uploads match the existing record. Possible patient identifiers trigger an immediate explicit warning and pause saving/linking. Privacy screening is not HIPAA certification; unresolved files remain outside public folders. The attachment helper requires pypdf (and olefile for legacy .ppt format checks), validates PowerPoint package/stream structure before conversion, preserves private staged inputs and refuses existing destinations. It does not edit YAML; PDF placement and approved YAML apply are separate recoverable steps. See references/attachments.md and references/privacy.md.

Runtime discovery follows references/runtime.md: host dependency locators, saved executable/library paths, Windows Store PowerPoint registration and private scratch folders. Permission, package and execution-policy errors must be diagnosed before declaring a capability unavailable.

Optional handoff-academic-update prepares requests when the current chat cannot access records. It can forward to an explicitly configured local chat with actual human authorization when messaging tools exist, otherwise supplies a manual handoff. Local routing configuration stays outside the package; it does not initialize a project, grant permissions or guarantee attachment transfer. See references/handoff.md.


Optional media.yml support adds stable anchors, source-preserving article/video/podcast metadata and allowlisted embeds. Existing 13-file sites remain supported. Initial media migration and consumer integration are separately approved; the routine helper updates existing files only. Profiles do not gain new permissions automatically. See references/media.md.

Save verification now rechecks the complete approved source snapshot after validation, including optional media, the target and bibliography, before issuing a receipt. Recovery also requires current file authorization. Status separates historical receipt existence from current snapshot consistency and reports changed files; legitimate later updates do not erase history. See references/verification.md. Synthetic regression tests are bundled across tests/test_*.py, with optional real R/yaml and R/Quarto/Git integration.

Questions use the host's structured question capability when available, one question at a time, with chat fallback. Setup settings are resolved progressively and previous confirmations are reused. See references/questions.md.

Private preferences now use documented project-specific locators and resumable guided setup, including the configure-academic-records skill. Missing profiles trigger one-question-at-a-time initialization; inaccessible storage never silently falls back to public files. Routine and broader review instructions include source discovery, relationship candidates, status checklists and remembered dispositions. Frequencies are user choices. These are skills-based host workflows; no scheduler, importer or new connector is bundled. See references/preferences.md and references/reviews.md.

Setup now includes a conditional questionnaire distinguishing user choices, inspectable facts and deferred initializer features. It requires legacy profile/job reconciliation, preserves dated decisions and the canonical development-plan pointer, and records readiness per capability. Scheduling instructions resolve the current installed plugin at each run and record version evidence; a stale known package is reported rather than silently used. Profile v3 makes review settings canonical for cadence/notifications/job identity while discovery settings own sources/windows; legacy mirrors are migration-only. Prototype starter delivery and reviewed setup execution are included. Automatic factual CV import, arbitrary template conversion, an unattended package updater and a storage/scheduler service are not bundled. See references/questionnaire.md, references/preferences.md and references/scheduling.md.

Scheduled-review setup now includes actual native host task creation/update, read-back verification and task-ID persistence after the user confirms the necessary specifications. It reuses existing jobs and supports later frequency changes. Initialization uses this same procedure; missing host scheduler access leaves setup explicitly pending rather than claiming a schedule exists.

Check-ins and configured review tasks now share the review-message workflow: search-derived suggestions, CV/site links with truthful freshness, linked record-category checklist, assistant-guided submissions and a Nothing to add closeout. Users can choose regular submission reminders even with no findings. No repeated nudge within an ignored cycle; YAML viewing remains available at any time. Native checklists/file side panels are host-dependent; no custom UI is bundled. See references/check-in.md.

Incremental discovery uses a separate successful-coverage checkpoint for each source/account/scope, a saved overlap and deduplication. Failed or partial searches retain their old cutoff; setup/dispatch never invents successful search history. Initial look-back is asked at first search when needed and reused thereafter. Configured tasks use the same rule; see references/discovery.md.

Output follow-through now reads separate saved website/private-CV/verification/commit/push assistance preferences in interactive maintenance and configured tasks. Execution requires explicit stage-specific authorization plus actual host access; a preference alone is not a grant. Owner-managed settings retain the existing handoff. Public CV preparation/publication is separate and can remain deferred. The bundled starter includes its R/Word generator; existing projects use their inspected tools. There is no background Git automation service; approved execution uses the available host tools. See references/output-execution.md.


PowerPoint preparation now requires an initial not-flagged source-screen assertion and actual explicit private-copy approval before the helper creates any attachment folder/copy or probes converters. Conversion precedes final visual/privacy review; manifests remain pending review. Declared flagged inputs are refused, and preparation failures identify retained staging with minimal phase/category receipts. Public save approval/privacy assertions remain separate. No automated PHI detection or compliant storage is claimed. See references/attachments.md and references/privacy.md.

Validation permits corrections to records when baseline data errors exist: proposals explicitly list resolved and remaining errors, block new/changed errors and all parser/structure failures, and preserve the exact reviewed error set during save/recovery. A verified approved change does not mean the entire dataset is error-free. See references/verification.md.

Recovery attribution now preserves known failed-before-write outcomes even when another proposal later saves identical bytes. New receipt-only recovery requires that same attempt’s durable confirmed-target-write marker as well as its approval, backup, scope and validation evidence. Matching bytes alone cannot establish attribution. Legacy interrupted attempts without confirmed-write evidence require manual reconciliation; contradictory older recovery receipts are flagged without rewriting history. See references/verification.md.

“Set it up for me” is an initialization option with a concrete reviewed scope. The new-project execution helper can copy approved staged files, run exact local R/Quarto commands, create a checked public Git commit and push after the chosen verification/approval gate. It does not install tools, register accounts or create a GitHub repository itself; the agent uses available authorized host tools for those actions. Existing manual setups are preserved. Local Git execution is tested; remote push is mocked in tests, and a real deployment still requires verification. See references/setup-execution.md.

First-time Zotero setup now distinguishes Desktop, integration, empty/existing library and optional account/sync. The assistant can reconcile CV/PubMed candidates privately, reuse reviewed imports and verify scoped citation-key/export/consumer setup. The publication readiness helper stages operator observations only; it does not install, search, import or export. Mocked connection cases and synthetic BibTeX/R output checks are not a live Zotero/PubMed end-to-end trial. See references/zotero-initialization.md.

### Zotero export continuity
Initialization reuses an existing verified bibliography export or guides an approved Better BibTeX automatic-export setup; native/manual export remains available. Saved scope, destination, timing and citation-key observations prevent repeating setup each week. After an approved addition, Zotero insertion, bibliography inclusion and regenerated CV/site outputs are checked and reported separately. Delayed or failed export never triggers a duplicate import. See [export setup](references/zotero-initialization.md#reuse-or-guide-export-configuration).


### Weekly check-in progress
Routine reminder/closeout and broader-review progress uses a separate private state helper, leaving preferences unchanged. Bookkeeping does not invalidate a concurrent search; source/permission changes still block completion. See [runtime progress](references/private-state.md#routine-check-in-progress).
