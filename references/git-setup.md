# Git and GitHub setup guidance

Use this reference during initialization when Git/GitHub setup is needed. Do not restart a working setup or require GitHub for local CV-only use.

## Guide, not a second textbook

Use [Happy Git and GitHub for the useR](https://happygitwithr.com/) by Jenny Bryan, the STAT 545 TAs and Jim Hester as the learning guide. Link to the relevant chapter and explain the next small step in the user's context; do not copy or bundle its chapters. Inspect the current chapter before giving its instructions. Check current official Git, GitHub and Posit documentation for installer details, authentication, email privacy, account/plan limits and Pages configuration; older book examples are not authority for those changing details. If browsing is unavailable, offer the links and mark current setup details unverified rather than invent commands.

Ask one question at a time through the host question UI, with a chat fallback. Reuse saved answers and inspect tools first. Explain briefly: Git keeps local change history; GitHub hosts a remote copy; RStudio can provide a Git interface. Offer guidance or approved execution according to the existing assistance choice. Users choosing execution need not complete a Git course.

## Choose only the missing steps

1. Account: [Register a GitHub account](https://happygitwithr.com/github-acct). Reuse an existing account. Let the user perform registration, sign-in and MFA in the provider UI.
2. Local tools: [Install Git](https://happygitwithr.com/install-git). Check the actual operating system, executable and version; avoid redundant installation. R/RStudio setup follows the book's installation section when needed. An extra Git client is optional; RStudio is not mandatory for agent execution.
3. Commit identity: [Introduce yourself to Git](https://happygitwithr.com/hello-git). Ask which name and email should appear on commits; explain public commit-email exposure and offer the user's actual GitHub-provided no-reply address. Inspect existing configuration, distinguish repository-local from global changes, and include any configuration change in the approved scope.
4. Authentication: use the book's connection section and current [GitHub authentication documentation](https://docs.github.com/en/authentication). Reuse a working supported method. The execution helper currently accepts HTTPS remotes; preserve existing SSH projects under their existing workflow rather than silently converting them. A connected GitHub app does not prove local command-line Git can authenticate. Never ask users to paste passwords, tokens, recovery codes or private keys into chat, profile files or commands/logs; use the supported provider/credential-manager flow.
5. Verify connection: [Connect to GitHub](https://happygitwithr.com/push-pull-github), then [Connect RStudio](https://happygitwithr.com/rstudio-git-github) if selected. Read-only probes do not establish push permission. Any test repository, commit or push must be included in actual approved scope; use synthetic public-safe content, never the raw CV.
6. Pick the project branch: [New project, GitHub first](https://happygitwithr.com/new-github-first) is a useful learning route. Existing local projects use the book's corresponding existing-project chapters after inspection. Do not clone into a destination and then run the new-project execution helper there: that helper requires an absent destination. For helper execution, create/verify an authorized empty remote and let the helper create the local project. A populated remote or existing local directory requires assessment under the existing-project workflow, never replacement or force push.
7. Publication: confirm owner, repository, visibility, branch and intended site address. Review exactly which files are public. Follow setup-execution.md approval and preview gates for commits/pushes. For GitHub Pages, consult [current Pages documentation](https://docs.github.com/en/pages); verify deployment status and the actual public site separately. Successful push is not proof of a live website.

## Save readiness and resume

Record nonsecret selections, verified executable paths/versions, identity/configuration scope, repository URL/visibility, selected authentication method (never credentials), readiness checks and the next blocker in the existing private bootstrap history/profile authority. Do not invent new required configuration fields or mark setup ready solely because the user has an account. Existing bootstrap helpers can retain answer references; they do not automatically probe or configure every item above.

A completion report distinguishes Git installed, identity configured, local Git authenticated, repository verified, first push completed, and site deployed. Report only observed stages. If permission or user interaction is missing, keep that stage pending and continue independent authorized work. This is agent guidance layered over the tested execution helper, not a tested automatic installer or account-registration service.

For this starter's personal site, continue with [personal-site deployment](personal-site-deployment.md), including branch existence before Pages configuration. Do not apply a project-site repository URL suffix.
