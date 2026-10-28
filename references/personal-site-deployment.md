# Personal-site deployment: USERNAME.github.io

Use for the supported new personal website, not organization/project sites or custom domains. Consult current official [GitHub site creation](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site), [publishing-source settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) and [Quarto Pages guidance](https://quarto.org/docs/publishing/github-pages.html). Ask one question at a time; reuse answers and actual approved setup scope. This document is guidance; available host tools and access govern execution.

## Discover and propose
Identify the authenticated personal account through available GitHub tools/provider UI. A configured Git author name is not proof of account identity. Derive lowercase username.github.io, HTTPS remote and root site URL; verify ownership. Inspect both repository and local destination before creation. If either exists, preserve it, inspect instructions/changes/remote/Pages/custom domain, and use the existing-project workflow. Never replace it, change visibility, remove CNAME or force push automatically.

For a fresh user, propose owner/repository, visibility, branch, new local folder, public file list, rendering, push and Pages settings together. Explain public repository source exposure and public website exposure independently; never promise a private repository makes a site private. Check current plan availability before selecting private-repository Pages. No paid plan is assumed or purchased. Make any account, repository creation, setting changes or installations concrete and authorized. Account authentication may need user interaction. Reuse approved unchanged steps without repeated prompts.

scripts/personal_site.py plan USERNAME BRANCH [--repository-exists] [--local-exists] derives a nonmutating plan. Existing flags yield inspect_existing, never permission to proceed. Its output is not account/ownership verification.

## Prepare public source
In the reviewed staged source, preserve unrelated YAML keys and set:
```yaml
project:
  type: website
  output-dir: docs
website:
  site-url: https://username.github.io/
```
Substitute the verified username, with no repository-name suffix. Coordinate site.yml identity/title/footer and navigation. Do not copy private CV/contact/bootstrap files into public source. Inspect the complete generated docs tree too: ignore rules alone do not prevent Quarto copying sensitive files. Follow existing attachment screening, exact record approval and public-CV separation.

Ensure the final docs/.nojekyll exists (empty is valid) after rendering and before public file hashing/commit. Stage an explicit creation step in the approved plan if rendering does not preserve/create it. The execution helper requires nonempty expected_files: list docs/index.html there and verify .nojekyll existence separately, not as a nonempty output. Inspect links/resources and exclude source/instructions/private material from rendered output. Do not introduce quarto publish, gh-pages or an Actions render workflow alongside this selected docs-on-branch approach.

## Execute in the right order
1. Create and verify the authorized empty remote via available GitHub tools or guided UI. For the new-project helper, do not initialize that remote with README/license/.gitignore: remote history would conflict with its new local commit. If it is populated, stop and assess an existing-project path; never force overwrite.
2. Follow setup-execution.md for approved new local creation, R/Quarto execution, actual output/privacy/factual/visual/link review and public-only commit. Review metadata and generated assets before publishing. Missing private-file coverage stops publication.
3. Push within the chosen publication approval mode. A successful push only establishes the remote branch; it is not deployment verification.
4. After the branch and docs/index.html exist remotely, configure Settings > Pages > Build and deployment > Source: Deploy from a branch > approved branch > /docs > Save. Use a supported authorized GitHub API/integration if available, otherwise guide the user through UI and verify the saved result. Missing settings permissions remain pending. Keep HTTPS enabled when available; custom domains are deferred.
5. Inspect the actual Pages deployment/workflow for the intended commit. Branch publishing can still appear as a GitHub Actions deployment. Do not replace this with an automatic Quarto build workflow. Failure, pending or unknown stays non-live; retain diagnostics privately. Check current GitHub guidance if an automated-token push does not trigger a build; do not blindly retry/force push.
6. Open https://username.github.io/ and verify the intended version, navigation, images, CSS, attachments, downloads and relevant cross-links (including case-sensitive paths). Check required resources on the actual site, not just HTTP 200 or an older cached home page. Deployment success alone is insufficient. Report pending stages and actionable failure rather than claiming live.

## Verification and durable preferences
scripts/personal_site.py check PLAN_JSON OBSERVATIONS_JSON validates operator-provided observations; it makes no network calls, privacy detection or independent deployment checks. It requires exact URL/configuration/source, correct repo identity/branch, observed public file list with no private paths, deployment status=success, deployed_commit matching intended_commit, and root/assets review. True observations must come from real inspection; never fill them just to pass. An empty .nojekyll is allowed. It reports blockers and deployment_verified false until all checks pass.

Save the account/repository/site URL, branch, source folder /docs, method branch-docs, visibility, observed Pages settings, verification reference/time, relevant commit and pending stages in the same authorized private bootstrap/profile authority. Do not add unsupported required keys to config.json; retain a private setup note referenced by bootstrap answer history until the profile schema supports these details. Never save credentials. During later maintenance, read these choices and preserve the established manual/agent execution preference. YAML changes alone do not deploy: render, inspect, commit and push updated docs when authorized.

Tests cover derived addresses, existing-project holds, configuration/source mismatch, private paths and failed/stale deployment observations. They do not create a GitHub repository, configure real Pages or certify a live deployment.
