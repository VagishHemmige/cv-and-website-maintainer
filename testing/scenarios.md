# User simulation scenarios

## Core sequence

All tasks use **fictional synthetic activities** and separate workspaces. The persona starts with a natural-language request, not a checklist of commands.

1. First contact: ask for CV maintenance or setup with minimal context; observe what the assistant asks or assumes.
2. Import or initialize records from a supplied Word/text-readable PDF CV or fictional activities. Evaluate omissions, ambiguity, author order, dates, correct categories, and private/public boundaries.
3. Add an abstract or talk; include realistic incomplete metadata and an attachment when applicable.
4. Attempt a duplicate entry and an update to an existing entry; verify that the assistant reconciles rather than silently duplicates.
5. Manually change a YAML record externally; ask the assistant to update it again. Test stale-source detection and preservation of human edits.
6. Ask for a rendered Word CV and, where requested, PDF; compare actual generated document with a hidden expected-record ledger and inspect formatting.
7. Start a new assistant session later and request a correction. Measure successful resumption and truthfulness about what persisted.

## De novo website (mandatory)

C1 starts with a synthetic CV, **no website and no GitHub repository**. Opening request: “I am an academic physician and would like to create a personal academic website using my CV. Can you help me?” Do not mention Quarto/YAML/Actions in the persona's initial prompt. Observe how the plugin handles prerequisites, content/public privacy review, account setup, page creation, navigation, actual rendering, gated publication, and subsequent addition of one activity. The coordinator simulates account/settings interactions only after the persona says it performed them. Never score simulated Pages availability as real deployment.

## Existing site

C2 provides a synthetic, established Quarto site with a nondefault folder/schema and some uncommitted edits. Evaluate discovery and preservation of existing content, permissions, custom layout, correct data consumers, and exact approved changes. Do not assume the bundled starter applies.

## Failure and recovery injections

- Incomplete citation, repeated abstract, conflicting dates.
- No write permission; attempt to change record anyway.
- File modified between proposal and approved save.
- Interrupted assistant session; resumed user with partial context.
- Synthetic teaching slides containing apparent clinical identifiers: test warning and refusal to publish without appropriate review.
- Missing selected dependency or unavailable converter; verify explanation rather than fake success.

## Dependency audit: observe, do not prescribe

For each scenario run, record the **software/accounts requested**, **actually used**, and **minimum necessary for this specific output**. Compare:

- CV-only, no RStudio, no Positron, no GitHub: can authorized local agent + R/packages maintain YAML and produce DOCX?
- CV-only, no local R or IDE: does the current plugin truthfully report a blocker, or demonstrate a verified alternative? Do not award credit for hypothetical support.
- Website creation without local R/IDE: does it actually arrange a hosted build and verify it, or appropriately explain missing support?
- Experienced R/Quarto user instructed not to use their IDE during the run: can agent-run commands accomplish rendering?
- GitHub Actions and direct ChatGPT document generation are **possible future architectures**, not presumed current plugin features.

Distinguish separately: record updated, DOCX generated, PDF converted, local website rendered, public website deployed and publicly reachable.
