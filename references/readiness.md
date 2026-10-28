# Before setup: local readiness

Use scripts/readiness.py after the user selects records, CV, website, PDF processing and/or Git publication. Show its table before the concrete setup plan and ask one next question about a blocker. Ready means the named local probe passed, not that setup, rendering, credentials or deployment will succeed.

The assistant resolves saved runtime paths from the authorized profile or bootstrap answers, or host-provided runtime discovery (runtime.md), and passes explicit paths. This helper never reads/writes profile configuration itself. An explicit invalid path stays blocked rather than silently selecting another installation. Its fallback checks PATH and the known Windows RStudio-bundled Quarto path; a missing candidate is not proof software is absent everywhere.

Example (replace placeholders with actual authorized absolute executable/library paths):
```
python -B scripts/readiness.py --goal cv --goal site --goal pdf --goal git --rscript ABSOLUTE_RSCRIPT --r-library SELECTED_R_LIBRARY --quarto ABSOLUTE_QUARTO --git ABSOLUTE_GIT
```
Use the actual Python executable to launch the helper; --python can select a different interpreter for its module probe. --format json includes checked paths and guidance links; the default table is user-facing. Keep machine paths/library observations private.

- records requires yaml; CV/site defaults use the inspected starter package inventory. For an existing project's different consumers, inspect those consumers and pass repeated --package NAME values. CV always checks yaml, officer and RefManageR; records always checks yaml. Do not claim these defaults cover arbitrary R code or optional features.
- R runs with --vanilla, uses the selected library (plus R's normal fallback libraries) and reports actual library paths. Installed namespace load and version are checked; officer additionally must export run_tab. No arbitrary numerical minimum. Trusted installed package initialization can run when namespaces load; project startup files and project scripts are not sourced. No packages are installed.
- pdf checks actual pypdf import/version in selected isolated Python; --legacy-ppt additionally checks olefile. Converter/export readiness is separate under attachments.md/runtime.md, not implied by module readiness.
- Quarto is checked only for selected website generation. Git is checked only for selected Git work. Git identity/signing reuses the setup preflight without printing name/email. Enabled signing remains a manual-workflow blocker; no keys invoked or signing disabled.
- Editor is optional. Zotero and connectors remain not checked until relevant authorized integration checks. A missing unrelated capability must not block useful work.
- All subprocess probes have a timeout. Failure, access denial, malformed response and timeout remain blocked/unresolved, not proof the tool is absent. Raw subprocess output/errors and credential values are not printed.
- No network command is implemented here. The table leaves remote access/Pages not checked. If the user separately requests a scoped remote check, use authorized tools; successful public ls-remote demonstrates readable reachability, not identity, write access or Pages deployment.
- No project creation, rendering, package installation, Git writes, profile edits or automatic next action. The existing setup helper rechecks its own prerequisites at execution; readiness is a dated observation, never approval.

Official next-step guidance (checked 2026-10-18): [R/CRAN](https://cran.r-project.org/), [Quarto](https://quarto.org/docs/get-started/), [Git/GitHub setup](https://docs.github.com/en/get-started/git-basics/set-up-git), [pypdf installation](https://pypdf.readthedocs.io/en/stable/user/installation.html). Follow current platform-specific instructions only after installation is authorized. R package remediation uses the selected R library and current package documentation; do not invent installer commands.

initialize.py probe is preserved for compatibility as a lightweight path observation. This report supplements it. A blank/slim setup plan is not an end-to-end readiness result.

For optional CV PDF generation or a public website CV during initial setup, follow [CV PDF initialization](cv-pdf-initialization.md). The reference Word COM converter needs Windows/PowerShell/Word plus pdftools for its PDF check. Add the inspected checker package to the selected R package list; record converter readiness separately. The pdf goal above checks Python reading modules and does not establish DOCX-to-PDF export.
