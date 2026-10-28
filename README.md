# CV and Website Maintainer

Previously displayed as Academic Records. The internal package name remains academic-records so existing skills and configurations continue to resolve.

Maintain academic records with an assistant: add activities, review possible updates, and prepare a CV or website using approved local tools.

## Before you start

Use a desktop Codex session with authorized local execution and plugin access. The account publication is private; a private link or downloaded ZIP alone does not install it for someone else. See the [installation and first-session guide](references/installation.md) for the local marketplace route, goal-specific prerequisites, updates and current testing limits. No public download location is established yet.

**In Claude (early support):** use Claude Code on the computer that holds your records, with access to this repository: `/plugin install academic-records --marketplace VagishHemmige/cv-and-website-maintainer`. Claude in a browser cannot reach local records or tools. Scheduled reviews and handing an update to another chat are not yet set up for Claude. So far Claude has been checked to load the plugin and its references, not to run full workflows.

## Start here

Say “Add this teaching session and these slides,” “Check for possible updates,” or “Help me start from my CV.” The assistant checks access, reuses saved answers, asks one question at a time, and shows each exact record change for approval. You do not need to edit YAML or run helper commands yourself.

| What you need | Workflow |
| --- | --- |
| Start from a CV, existing website or fresh project | [initialize-academic-records](skills/initialize-academic-records/SKILL.md) |
| Set preferences, resume setup or configure reviews | [configure-academic-records](skills/configure-academic-records/SKILL.md) |
| Add or correct activities and attachments | [update-academic-records](skills/update-academic-records/SKILL.md) |
| Find possible publications and other updates | [discover-academic-updates](skills/discover-academic-updates/SKILL.md) |
| Add approved references through an available Zotero integration | [update-zotero-records](skills/update-zotero-records/SKILL.md) |
| Continue in the configured local records chat | [handoff-academic-update](skills/handoff-academic-update/SKILL.md) |

Before creating a new project, the assistant can show a [readiness report](references/readiness.md): selected tool/package versions, blockers and next steps. This checks local capabilities without installing software, rendering or changing settings. Remote authentication and deployment remain separate.

## Setup and regular reviews

Preferences and interview history stay in authorized private storage outside the public project. Setup saves answers as pending, then presents one combined profile proposal for approval. Existing setup is reused. [Initialization](references/initialization.md) includes private CV text/candidate staging and a supported Quarto/Word-CV starter. Scanned or complex CVs require additional review; factual import and arbitrary template conversion are not automatic.

With your authorization and available host tools, the assistant can guide installation/account setup, run reviewed local R/Quarto commands, create a checked public Git commit, and push under your chosen approval/verification gate. Existing projects retain their own instructions. A successful push does not prove deployment. See [setup execution](references/setup-execution.md) and [personal-site deployment](references/personal-site-deployment.md).

Configured reviews search only approved sources, present candidates, link the existing CV/site with honest freshness labels, and invite updates through linked record categories. You can reply Nothing to add. Broader checks and remembered deferrals avoid repeating settled questions. Frequencies are configurable. [Scheduling](references/scheduling.md) uses the host's task capability and verifies the actual task; installation alone creates no task or connection.

## Saving records and attachments

Record, PDF and preference saves require exact [approval evidence](references/approval-evidence.md). Helpers check stale sources, retain backups/receipts and verify saved bytes. Approval evidence provides an audit trail; it is not authentication. After interruptions, inspect status before retrying. See [verification](references/verification.md).

Teaching, abstracts and presentations offer attachments now, later or none. PowerPoint conversion is local and requires initial screening and private-copy approval. Format checks precede conversion; final visual/privacy review and public-use approval precede PDF placement. Possible patient identifiers require an explicit warning and a pause before further copying or linking. Conversion does not de-identify content. The PDF helper needs pypdf; legacy PPT checks also need olefile. See [attachments](references/attachments.md) and [privacy](references/privacy.md).

Zotero remains the configured publication authority when selected. Approved imports require a separate available integration, duplicate/destination checks and post-import verification. Bibliography exports and regenerated CV/site outputs are separate outcomes. See [Zotero setup and export](references/zotero-initialization.md).

Saving YAML does not automatically regenerate the CV, render the website or publish it. The assistant reports what was saved and what remains; those stages follow your permissions and separately authorized assistance preferences.

## Requirements and limits

The host must provide authorized file access and tools. Installation grants no filesystem, email, calendar, chat-history or Zotero access. Forwarding to another chat requires explicit human authorization. The existing adapter checks its supported YAML layout; unsupported schemas need a reviewed plan. The read-only validator requires R and yaml; output generation needs the project's inspected R packages and Quarto where applicable. No storage server, connector server or scheduler service is bundled.

## Development

Regression tests live across [tests/](tests/). Run `python -B -m unittest discover -s tests -v` from the plugin folder. Real integrations require TEST_RSCRIPT, TEST_R_LIBRARY, TEST_QUARTO and TEST_GIT as applicable; TEST_TMP_ROOT selects authorized private scratch storage. Report skips and actual integration coverage. Tests use disposable synthetic data; remote push and Office conversion tests are mocked, and live Zotero/PubMed end-to-end behavior needs separate verification.

See [runtime discovery](references/runtime.md), [private-state commands](references/private-state.md), and [change history](CHANGELOG.md) for technical details.

Initial setup also records optional private Word/PDF and public website CV choices. See [CV PDF initialization](references/cv-pdf-initialization.md) for the coordinated source adaptation and dependencies. The bundled starter remains Word-only; preferences do not generate or publish PDFs.
