# Blinded participant profiles

Record **R, GitHub, ChatGPT conversational proficiency and desktop-agent/plugin proficiency separately**; do not infer these from academic rank. Recruitment targets below are hypotheses to test, not skill assessments. Levels: none, beginner, intermediate, advanced.

| ID and identity | R | GitHub | ChatGPT | Goal |
| --- | --- | --- | --- | --- |
| A1 senior physician | None | None | Beginner | Update a local existing CV |
| A2 academic with extensive Word CV | None | None | Advanced | Import and organize existing CV |
| B1 resident/fellow | Beginner | None | Beginner | Create an academic CV from supplied activities |
| B2 research-active faculty | Intermediate | Beginner | Advanced | Add publications, abstracts, presentations and teaching |
| C1 new website owner | None | None | Intermediate | Start an academic website **de novo**, with CV as source |
| C2 established website owner/analyst | Advanced | Advanced | Intermediate | Maintain existing website and CV without restructuring |

For each persona the coordinator privately specifies: starting CV/site, available accounts/software, working platform, willingness to install tools, privacy/permission preferences, accessible files, technical vocabulary and a small realistic goal. The persona should know its situation, *not* the intended path through the plugin. Its agent **must not read** plugin source, this protocol's scorecard, or answer keys.

Keep each persona persistent across sessions (people remember), but instantiate a **fresh assistant agent per session** (new chats do not inherently remember). Do not supply a backfilled assistant summary unless available through the explicitly simulated product context. When the persona must perform account or UI actions, have it decide what it would actually do; the coordinator updates fake environment state only following that choice.

Cross two goals with different competence combinations in follow-up runs to distinguish task complexity from user background.
