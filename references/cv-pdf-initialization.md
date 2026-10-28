# Optional CV PDF and website availability during initialization

Ask one question at a time and reuse saved answers. For a website or both goals,
ask `website_cv`: yes / no / defer. For a private CV or both goals, separately ask
`cv_format`: docx / docx_pdf / defer. A private PDF does not imply a public CV;
a website-only user can request a public PDF without requesting a private CV.
Explain that website availability makes the approved public CV downloadable.
Save actual answers/references in initialization.json, then carry them into the
existing full-profile preference procedure; do not create a competing config.
Missing answers on resumed bootstraps stay pending. Deferral is not consent.
When output goals change, retain historical answers but use only applicable
choices; confirm a changed preference before replacing it.

The bundled starter remains Word-only. The helper reports choices in status and
new starter receipts; it does not implement a PDF adapter, change the ZIP or
grant execution/publication permission. Do not describe selecting yes, successful
staging or questionnaire completion as a configured PDF pipeline. For selected
PDF/public output, prepare and inspect the coordinated adaptation below in the
private staged project_source_root before presenting the exact setup plan.
If unavailable, report the adaptation as pending and continue independent setup.
Existing functioning projects retain their source and maintenance workflow;
this initialization feature does not migrate them or expand routine write scope.

## Source pattern and coordinated proposal

The inspected implementation is [Add CV to website, 2026-10-28](https://github.com/VagishHemmige/VagishHemmige.github.io/commit/4f2aedd668ba7044c4277614b2164321e93d4c06).
Inspect the actual selected project's current source before adapting it; this
commit is a reference, not a command to copy the owner's project. Its R/cv.R
builds both private and public DOCX/PDF versions unconditionally and uses Windows
PowerShell and installed Word COM for conversion. A new user's selected branches
must be respected. Do not replace a newer starter generator with that whole
script: retain its generic site.yml identity, section logic, filename pinning,
output collision safeguards and publication authority.

Show the exact affected files, output paths, dependencies, commands and public
Git allowlist in one reviewed setup plan:

| Selection | Coordinated source and output work |
| --- | --- |
| Word only, no public CV | Keep baseline Word generation; no PDF converter, CV page, PDF resource or CV navigation entry is needed. |
| Private Word and PDF | Adapt staged R/cv.R and a reviewed converter for the selected host. Both outputs stay under ignored cv/. No public page or resource is implied. |
| Public website CV PDF | Adapt staged R/cv.R to generate a public version with the approved header exclusions, plus conversion and a PDF privacy check such as R/check-cv-pdf.R. Keep intermediate DOCX private. Choose a stable generic files/CV.pdf path (or the user's reviewed equivalent), add cv.qmd, the exact resource and CV navbar entry in _quarto.yml, and the embed styling in styles.scss when embedding is selected. Include the PDF's rendered destination for the actual output-dir in verification and the public Git plan. |
| Deferred or unanswered | Leave the feature pending; do not add a working-looking page with a missing PDF, silently enable conversion or assume publication approval. |

Choose every filename with the user; do not copy Hemmige filenames, contact
details or the fixed “Last updated October 2026” line. Generate an accurate update
label or define its maintenance responsibility in the setup handoff. Preserve
the root-page render restriction, existing navigation/resources and styling.
An embed needs a download fallback and a usable phone layout; a download-only
page is a valid explicit choice. Do not create duplicate activity records for
the public CV; both versions consume the same approved YAML/Zotero authority.

## Dependencies, privacy and validation

The reference converter requires Windows, PowerShell and installed/licensed
Microsoft Word; officer alone cannot perform that export. It uses pdftools for
the actual-PDF text check. Inspect the chosen host and selected R library. Run
the readiness report with the relevant cv/site goals and `--package pdftools`
alongside the actual consumer package list when that checker is selected.
The readiness `pdf` goal checks Python PDF reading, not Word conversion. Record
Word/export readiness separately as pending until actual authorized conversion
succeeds. Never launch Word, install packages or invoke project scripts merely
to answer the preference question. On other hosts or without Word, offer a
separately reviewed supported converter or defer PDF; do not promise this
Windows COM implementation works unchanged.

Agree exactly which header/contact fields belong in each output. Keep private
inputs, full-header PDFs and intermediate DOCX files ignored and outside public
commit roots. Generate a public document from approved fields rather than
converting the private full-header document and calling it public. Match known
excluded address/email strings against text extracted from the actual PDF,
and inspect all pages, links and document properties for other private details.
Exact-string checks can miss wrapped/transformed text, phone numbers or other
identifiers: a passing check is not complete de-identification or public-use
approval. Fail/hold on unresolved privacy findings; preserve operation evidence
and handle existing outputs through the reviewed collision/backup policy, not
the reference script's unconditional deletion/overwrite behavior.

Before executing, pin exact private DOCX/PDF, intermediate and stable public PDF
paths in the source/command and expected_files. Retain starter filename pinning;
the PDF adaptation must bind its corresponding names too. Inspect the actual
generated PDF, freshness, selected inclusions/exclusions, readable layout and
page count. Then render only under the approved setup scope, verify the CV page,
download/embed and copied PDF in the actual output directory, and check the
public commit contains only approved public material. Publication follows the
existing setup-execution/personal-site approval mode and live deployment checks.
Report generation, privacy review, site render and deployment separately.
Routine YAML maintenance requires no new PDF action or standing permission.
