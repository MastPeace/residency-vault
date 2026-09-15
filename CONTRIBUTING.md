# Contributing

This is a personal knowledge base, but the conventions below keep it consistent
and maintainable.

## Update Policy

Every material change to the project **must** also update:

1. **`CHANGELOG.md`** — append an entry in [keep-a-changelog](https://keepachangelog.com/)
   format under the appropriate date heading. If there is no heading for today, add one
   as `## [YYYY-MM-DD] — short summary`. Keep `[Unreleased]` at the top.

2. **`README.md`** — if the repository structure, features, or documented workflows
   change, reflect the new reality in the README. Out-of-date documentation is worse
   than no documentation.

3. **`log.md`** — append an entry for every wiki page touched (already required by
   `SCHEMA.md` conventions).

## Schema Compliance

All content changes must follow `SCHEMA.md` conventions:
- File naming: lowercase, hyphens.
- YAML frontmatter with required fields.
- `[[wikilinks]]` for internal links (minimum 2 outbound per page).
- Bump `updated` on every edit.
- Provenance on numeric/conditional facts (`^[url]`).

## Commit Messages

Keep commit messages descriptive. The auto-sync script uses a generic dated message;
when committing manually, use conventional style:
- `feat: <description>` for new features
- `fix: <description>` for bug fixes
- `docs: <description>` for documentation changes
- `update: <description>` for content updates

## Testing the Static Site

```bash
cd /home/vovka/wiki
python3 scripts/generate_site.py
# Output in site_output/ — open index.html in a browser to verify
```