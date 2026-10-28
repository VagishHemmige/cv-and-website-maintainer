# Set it up for me

This is the execution branch of initialize-academic-records, selected by assistance=approved_execution. It is not triggered by routine maintenance, a schedule, plugin installation or a preference label alone. It supports a new local destination only. Existing projects use output-execution.md and their established instructions, with backups and preservation of unrelated work.

## One concrete scope, progressive execution

First finish the needed source/visibility/identity questions and factual import review. Stage the actual proposed source files, not a hypothetical template or raw CV. Inspect permissions, dependencies, authentication, repository ownership/visibility/branch and host capabilities. A user can authorize a named group of actions together. Honor that actual scope without asking again for unchanged steps, while using host access prompts when required. Unknown factual CV claims, changed sources/destinations, unavailable credentials, unexpected files and material scope changes stop dependent actions. Keep independent authorized work moving.

Offer guidance, prepared changes, or execution. For execution, show the real destination, complete source/file hashes and readable changes, exact local commands and output paths, dependency/account actions, Git public path allowlist, intended owner/repository/branch/visibility and publication preference. Get the actual approving response/context. Record it privately as approval evidence; not merely the word approved_execution. Setup approval covers only the exact reviewed plan. It is not approval of unseen CV facts or exposure of private contacts. Never publish example identities or synthetic records as the user's facts.

Installations and new accounts/remotes are performed through available host/package/GitHub tools, after their exact proposed actions are authorized. Check current official instructions and offered plugins/extensions; never auto-install recommended components. User account registration and authentication may require their interaction. No credential/token handling in source files, commands or logs. The execution helper itself does not install software, register accounts or create a GitHub repository. After approved host actions, inspect tools and remote again. A user need not learn R/Git just because these are implementation dependencies.

## Reviewed local plan

scripts/setup_execution.py uses the same private bootstrap STATE and stores plans/approval evidence/logs under setup-plans/ID, outside the project. The reviewed source is a private staged public-source subset. Exclude raw CVs, private contacts/state, credentials and generated private CVs. The helper refuses an existing destination and any overlap of source/project/private state. It copies the exact source snapshot without overwrite, runs explicit argument arrays without shell composition, and requires named outputs. It records partial failures and never blindly reruns a used execution plan. This is a cooperating-writer/audit safeguard, not a sandbox, independent approval authentication or a multi-system transaction. Exact commands can execute code; the host must review their scope and enforce permissions.

Specification JSON keys are source (absolute reviewed source folder), project (new absolute target; parent exists), steps (list), git (null or object). Each step has name configure/generate_cv/render_website/verify_outputs, argv (absolute executable followed by exact arguments) and expected_files (nonempty list of project-relative output files). No .cmd/.bat shell wrappers: use verified executables. The agent sets up the required R library/runtime environment in the actual host and records it; no hidden package installation is performed. Generator success/output presence does not certify facts or layout.

git has executable, branch, remote (explicit HTTPS GitHub owner/repository or null), commit_roots (named public files/directories) and publication_mode (hold_for_review or after_verified_preview). Paths are enumerated into an exact file list before Git staging; no blanket git add. Private/raw/state/credential paths and private Word outputs are refused even within an approved directory. Templates/cv-styles.docx is the formatting-only exception. The new Git root, staged file set, committed tree bytes and intended remote are checked; unexpected enabled hooks cause a hold rather than being bypassed. There is no force push/reset/clean, modification of an existing repository or automatic deletion/rollback. Git environment redirects are cleared for child commands. Git identity/credentials must already be configured or separately authorized; missing identity/authentication remains a blocker.

```text
setup_execution.py plan STATE SPECIFICATION_JSON
setup_execution.py execute STATE ID --approval-evidence FILE
```

The plan returns id, sha256 and absolute project destination. Bind the actual setup approval to kind=setup, that id/hash/destination using approval-evidence.md. Evidence must be private. The helper creates a local completion receipt with commit/public_files when applicable; this says nothing was pushed or deployed.

## Publication choice and actual preview verification

Explain the choice before asking for setup approval, using one focused question. For new users, recommend **Show me the preview before publishing** (hold_for_review). The alternative is **Publish after the assistant verifies the preview** (after_verified_preview): explicitly say, “This lets the assistant push the approved public files without asking you again after its verification; you may not see the preview before publication.” A push to a configured live site may make the content public. Never describe this alternative as requiring a later human preview approval.

Reuse an existing confirmed choice without asking again. If the user is undecided, leave publication pending; the recommendation is not a saved setting or authorization. Record the selected mode only through the reviewed preference/setup-plan process. Choosing general execution assistance does not choose autonomous publication. Keep both modes available, honor an explicit preference for autonomy, and preserve any requirement the user has set to inspect outputs personally. No existing mode is changed by this guidance.

**hold_for_review**: after generating and inspecting outputs, show the actual preview, file set and publication destination. Use publication-request to obtain the exact commit/remote/branch/public-file digest for a fresh actual approval. Kind=publication binds its ID/SHA256 and the private publication-request.json destination; that document contains the remote/branch, not a local deployment target. Then publish with that evidence. Preserve the request and evidence privately.

**after_verified_preview**: user explicitly authorizes pushing the exact configured public project after successful agent preview/verification within the setup plan. It permits proceeding without a second human confirmation when all conditions match. It does not waive actual factual/privacy/visual/link/repository review or any explicit user requirement to inspect the preview. If those cannot be performed, keep publication pending instead of inventing success. The original setup evidence is rechecked before push.

In either mode, create a private verification JSON containing plan_id, commit, public_files (exact map from the local completion receipt), reference (where actual review evidence is retained), and true factual_review/privacy_review/visual_review/link_review/repository_identity_and_visibility_verified. These are agent review assertions and navigation aids, not automated clinical screening, independent security checks or proof of visual inspection. The assistant must actually inspect and retain evidence of the outputs and remote owner/visibility through available tools. A false/missing check holds publication. Native host tools are still required for authentication and GitHub/deployment inspection.

```text
setup_execution.py publication-request STATE ID
setup_execution.py publish STATE ID VERIFICATION_JSON [--approval-evidence FILE]
```

Before push the helper rechecks HEAD, current branch, origin and allowed public file hashes. It records push-started before the network call; a failure/interruption requires inspecting local/remote state, never a blind retry. Push success is reported as push_command_succeeded with deployment_verified=false. Inspect actual GitHub deployment/check status and the public site separately before claiming it is live. Remote creation, credentials and actual GitHub Pages deployment are host/integration work, not supplied by git push alone.

Private CV generation and public-CV publication remain separate choices. Keep private CVs/contact inputs outside the committed public set even when setup is fully agent-executed. Stage/inspect the public version separately when authorized. No automatic recovery history certification, rollback or permission expansion follows a partial stage.

## Verification boundary

Tests exercise actual disposable local project creation, commands, Git commits, approval gates and public-file checks. Push calls are mocked; no test creates a real GitHub repository, uses the owner's identity/credentials or verifies a real deployment. Existing starter empty/synthetic R/Quarto rendering evidence remains applicable, with visual Word review/template provenance still pending. Do not represent local/mock tests as a completed live autonomous setup trial.

For USERNAME.github.io, follow [personal-site deployment](personal-site-deployment.md): first push the verified docs tree to establish the branch, then configure Pages from that branch and /docs, then inspect deployment and the live site. Repository creation and Pages settings are authorized host work; this helper does not perform them. Preserve an existing site's configuration rather than replacing it.

When source comes from initialize.py stage-starter, begin with its returned project_source_root and review/adapt the actual public-source subset there. The legacy folder and metadata_folder identify private operation metadata, not a project source. Keep operation.json/completed.json and other private state outside both the reviewed source and destination. Do not derive the project root from the wrapper path or pass the wrapper as source.

## Shared public-file exclusions
Setup and personal-site deployment checks use scripts/public_paths.py. Both refuse agent instructions (AGENTS.md, case-insensitive), .codex/private/state folders, private config/credentials, unsafe paths and Word files other than the exact templates/cv-styles.docx formatting reference. Paths use portable forward slashes. Inspect source before creating the destination and scan generated commit roots before git init/stage/commit; do not rely on a later deployment check to catch a private file. These are conservative new-project defaults, not authorization to delete files or change existing repositories or an owner-approved public instructions policy.

## Git preflight before any project creation
For Git-enabled setup, plan and execute both check effective author/committer identity with user.useConfigOnly=true, so guessed host identities do not pass. Configuration and environment overrides are read using the existing private bootstrap directory outside the project; Git context redirects are cleared. Missing/unusable identity, probe failure or unreadable commit-signing configuration stops before destination creation, copying, rendering, or the execute started marker. Resolve settings with user-authorized Git guidance; never silently set a name/email or disable signing. A preflight failure before started leaves the exact unchanged plan available after the blocker is resolved.

Enabled commit.gpgsign stays pending: this helper has no verified noninteractive signing route, does not invoke keys or prove signing by configuration alone, and does not bypass it. Offer separately reviewed signing/manual Git setup or an explicitly authorized configuration change. Unsigned/unset signing may proceed under the existing approval gates. These early checks do not guarantee future credentials, hooks, target-specific conditional configuration or command success; later failures still preserve partial files and logs without automatic retry/cleanup. Git-free setup is independent of Git identity. No existing repository/configuration is modified by preflight.


## Executable aliases and protected paths
Setup handles installed executable links separately from data paths. At planning, absolute executable paths (including symlinked R, Python, Quarto and Git installations) are resolved to regular files; .cmd/.bat wrappers, missing/cyclic links and non-executable POSIX files are refused. The returned proposal and stored plan show the requested path, resolved path, SHA-256, file mode and owner identifier where the OS supplies one. Review the actual resolved installation before approving; resolution does not prove publisher trust. Commands run the resolved path, not the alias. Caller specifications are not mutated.

Execution rechecks these bindings before Git preflight/project creation and before each child command; publication rechecks too. Changed alias targets, bytes, ownership or mode require a fresh exact plan/approval, never rebinding an old approval. Older plans with commands but no executable bindings need a fresh plan; no historical plan is rewritten. This is a cooperating-process safeguard, not an OS sandbox or elimination of filesystem races, and does not pin shared libraries, script arguments or the full runtime environment.

Protected source, destination, private-state, approval and output paths retain strict no-redirection checks. For platform aliases such as macOS /tmp, select the actual direct authorized directory, rather than relaxing private-state boundaries. Executable alias support does not authorize redirected records or arbitrary state locations. No Git configuration, tool installation, existing project or scheduler changes are made by this update.


## Pin the starter CV output name in the reviewed command
When preparing a generate_cv step for the bundled starter, choose an exact simple .docx filename before approval. Set options(academic_records.cv_filename="approved-CV.docx") in the same R command before source("R/cv.R", encoding="UTF-8"), and name cv/approved-CV.docx in expected_files. Use the user's actual reviewed filename, not this example by default. The filename option accepts only a simple basename and always writes inside cv/; paths, drive prefixes, empty names and other extensions are rejected. The existing output-file refusal still applies.

This pins the name even when execution occurs on another day. Do not use a date guessed at execution, wildcard matching, a success marker or a copied second file as a substitute for the exact expected CV. Without the option, manual generation keeps the existing dated filename. Existing projects/scripts and already approved plans are not changed: an older plan that needs a pinned filename requires reviewed source/command changes and fresh exact approval. The assistant prepares the command; setup_execution.py checks exact command/source/output evidence but does not synthesize the filename or parse arbitrary R code to infer it. This option changes no profile, scheduler or publication scope.

## Optional CV PDF and public CV setup

Before preparing an initial setup plan, follow [CV PDF initialization](cv-pdf-initialization.md). Reuse saved format/website choices, inspect and adapt the staged source as one coordinated file set, pin every output and preserve private/public boundaries. The bundled starter remains Word-only; neither a preference nor a staging receipt supplies a converter. Keep pending adaptation, actual conversion and public-use/deployment approval distinct. Existing routine maintenance scope is unchanged.
