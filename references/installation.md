# Install CV and Website Maintainer and start your own project

## Before you start

CV and Website Maintainer (formerly Academic Records) is a plugin for an assistant with authorized local file and process access. The supported onboarding target here is a desktop Codex session with a Plugins Directory. Product labels and availability can vary by account/workspace; see the [official plugin quickstart](https://developers.openai.com/plugins/quickstart). A browser-only chat cannot directly execute R or edit folders on your computer.

You do not need to know R, YAML or Git to begin the interview. Bring an existing CV (DOCX, text-readable PDF or TXT), or identify your current website/local project. Do not upload patient-identifying material; the assistant must warn and pause when identifiers may be present.

| Goal | Tools needed for that goal |
| --- | --- |
| Install/use the local workflows | Desktop host with local execution and plugin access; a working Python runtime |
| Validate academic YAML | R with yaml |
| Generate the bundled Word CV | R with yaml, officer, RefManageR and inspected script dependencies; officer must export run_tab |
| Render the bundled website | Quarto plus the inspected R packages |
| Read/stage PDFs | pypdf in the selected Python; olefile additionally for legacy PPT validation |
| Convert PowerPoint | A separately verified local PowerPoint/LibreOffice route |
| Publish to GitHub Pages | Git and separately verified GitHub identity, remote permissions and Pages configuration |
| Manage publications in Zotero | Zotero Desktop and a working authorized companion integration; online account/sync is optional |
| Edit Quarto yourself | Your preferred editor, such as RStudio or Positron; optional for agent execution |

Start with [readiness](readiness.md); it reports actual selected versions, libraries and missing capabilities. Only selected goals block progress. See [runtime discovery](runtime.md) before declaring software absent, [Git guidance](git-setup.md) and [Zotero setup](zotero-initialization.md). Installation or upgrades require approval; the plugin bundles no R/Python/Quarto installation.

## Obtain and install a copy

The owner's account publication is private. Its link does not grant other people installation access. No public repository/download address is promised here. Obtain a complete release ZIP from the maintainer through a distribution route you can access; an update-only ZIP is insufficient.

For a local copy, the maintainer's local-marketplace ZIP contains this layout:

```
distribution-root/
  .agents/plugins/marketplace.json
  academic-records/
    plugin.json
    skills/
    scripts/
    references/
    assets/
```

1. Extract into a new durable folder outside your academic website and private profile.
2. Register that folder as a marketplace. With a compatible CLI: `codex plugin marketplace add ABSOLUTE_DISTRIBUTION_ROOT`. Ask the assistant to check installed CLI help first.
3. Restart the desktop app. In Plugins Directory, select Academic Records Local and install Academic Records.
4. Start a new chat and confirm the plugin and expected version are loaded.
5. Ask for a read-only readiness report before creating a project.

These steps follow [OpenAI's local-marketplace documentation](https://developers.openai.com/plugins/build/plugins). Registration does not itself install the plugin. No account credentials are packaged. If starting from a plain complete plugin ZIP, ask an assistant to construct the illustrated wrapper using [the catalog example](../examples/local-marketplace.json). The catalog path is relative to distribution-root, not the nested .agents/plugins folder. Preserve existing catalogs and installations; do not edit plugin caches.

## Your first session

Say: “Help me start CV and Website Maintainer from my CV. Check readiness first and ask one question at a time.”

The assistant establishes CV/site/both, existing folders/site, editing/execution preferences and private storage. It shows readiness and resolves blockers one at a time. It stages candidate records privately with source evidence, reviews omissions and public/private boundaries, and presents exact proposals. It creates files, renders, commits or publishes only within approved scope and host permissions. Setup can span several sessions; ask to resume rather than create another profile.

A working CV/site is separate from importing facts. A successful Git push is separate from a verified Pages deployment. Your records/profile and contacts are not included in someone else's package. Approve the outputs and factual mapping before calling setup complete. Existing projects retain their current instructions and layouts.

## Weekly check-ins and availability

Review tasks are optional and configured separately. Local scheduled work needs the computer on, the desktop app running and its folders accessible: [official scheduling guidance](https://learn.chatgpt.com/docs/automations). Sleep, shutdown, lost connections or expired authorization can prevent work. Automatic replay of every missed trigger is not established; inspect task/run status or ask for a review when returning.

The plugin resumes discovery from each source's last successful saved cutoff plus overlap when a later authorized search succeeds. This can recover a coverage gap; it is not proof a missed scheduled run executed. Broader reviews remain pending until actually handled. Scheduling is configured through [the existing workflow](scheduling.md); installing a ZIP creates no task.

## Updates and troubleshooting

Use the same distribution route for updates, inspect release notes and preserve your private profile/records. For a local source, update the source folder using a reviewed complete release and refresh/reinstall through the host flow; verify the loaded version in a new chat. Do not run competing private-account and local copies unintentionally. A new plugin version does not authorize changing your preferences or records.

If the plugin does not appear, check the registered root/catalog path and desktop plugin availability. If it loads but cannot save, check host folder permissions and profile allowlists. If readiness fails, report the row and selected runtime privately; never paste credentials. Optional integrations stay pending while independent work continues.

## Verification status

Documentation and marketplace format checked against official sources on 2026-10-18; installed CLI marketplace help supports add/list/upgrade/remove. The packaged catalog, source resolution and skill references are checked in disposable fixtures. A fresh-account desktop installation and newcomer end-to-end setup have not yet been demonstrated. No existing installation was replaced and no marketplace was registered by creating this guide.
