# Optional media records

`media.yml` is an optional extension to the existing 13-file adapter. Never create it automatically or add it to an existing profile allowlist implicitly. Its initial migration requires an exact approved proposal and coordinated `media.qmd` integration by the site owner. The routine proposal helper updates an existing media file only. Older 13-file sites remain supported. Preserve the profile adapter identity; optional media capability does not authorize unrelated migrations.

Top-level sequence, one mapping per media item:
- `id`: unique stable lowercase anchor, starting with a letter; retain it when titles change.
- `section`: writing, printed_news, video_news or podcast. The page controls section headings/order; records retain order within a section.
- `title`: source title; required scalar text.
- `outlet`, `date`, `description`, `url`: scalar text or null. Dates retain established year/month/day precision; never infer publication dates from URL paths. URLs must be HTTPS. At least a URL or embed is required.
- `embed`: null or a mapping containing only `provider` and `src`. Supported providers are youtube, apple_podcasts and libsyn. Use only their recognized HTTPS embed hosts/paths, not arbitrary HTML or scripts.

Match existing URLs, provider/source and titles before adding records. Related written coverage, video segments and podcasts can remain separate entries; do not assume they are duplicates. Coverage by a colleague is not necessarily the user's own appearance. Preserve source wording and unknown metadata. Searchable titles, outlet and description must render outside embeds. Keep layout and iframe attributes in the consumer, not YAML.

Discovery may propose media candidates for this destination only after the private profile selects media.yml and explicitly approves it. Report possible coverage when no destination is configured; do not silently write to media.qmd or create new schemas. Every concrete record diff still needs approval. No rendering, publishing, bibliography or CV scope is added. `validate.R` checks media when present; no CV consumer is expected unless separately implemented.
