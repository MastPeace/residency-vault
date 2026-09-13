# Wiki Schema — Residency & Citizenship Conditions

## Domain
Living conditions for residency / citizenship / tax programs across countries, with
focus on strong passports, IT-worker-friendly routes, and routes popular with Russian
citizens. The wiki is the single source of truth that a weekly monitor updates in
place; it is NEVER re-derived from scratch.

## Conventions
- File names: lowercase, hyphens, no spaces (e.g. `portugal.md`, `golden-visa.md`)
- Every wiki page starts with YAML frontmatter (see below)
- Use `[[wikilinks]]` to link between pages (minimum 2 outbound links per page)
- When updating a page, always bump `updated`
- Every new page must be added to `index.md` under the correct section
- Every action must be appended to `log.md`
- Provenance: pages that synthesize 3+ sources append `^[raw/articles/<file>]` at the
  end of paragraphs whose claims come from that source. Single-source pages rely on
  `sources:` frontmatter.
- Language: wiki content is written in ENGLISH (analysis summaries may keep official
  program names in original language). In the weekly monitor, deltas are reported
  against these English pages.

## Frontmatter (condition / country pages)
```yaml
---
title: Country — (e.g. Portugal)
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity
tags: [from taxonomy below]
category: [strong_passport | it_friendly | yacht_captain | popular_ru | clear_pathway | multi]
confidence: high | medium | low
sources: [raw/articles/<source>.md]
country_code: PT
---
```

## Tag Taxonomy
- Program type: residence, citizenship, golden-visa, digital-nomad, work-visa, tax
- Category (market): strong_passport, it_friendly, yacht_captain, popular_ru, clear_pathway
- Status: new_program, rule_change, suspension, processing_update, fee_change, deadline, rumor
- Meta: comparison, timeline, controversy

Rule: every tag on a page must appear in this taxonomy. Add new tags HERE first, then use them.

## Page Thresholds
- Create a country page when it is in the watchlist OR has 2+ distinct sources
- Create a concept page when a program (e.g. Golden Visa, D7, NHR) appears across 2+ countries
- DON'T create pages for passing mentions
- Split pages over ~200 lines into sub-topics with cross-links
- Archive superseded pages to `_archive/`

## Country Page Structure (`conditions/<country>.md`)
Each country page has fixed sections. Empty sections are shown as "Not available / no data".

1. **Overview** — passport strength, why it matters (one paragraph)
2. **Residence** — routes to a residence permit: names, income thresholds, timelines, fees
3. **Citizenship** — years of residence required, language/exam requirements, timeline to passport
4. **Tax** — relevant regimes (flat tax, NHR, non-habitual), rates, conditions
5. **IT / Digital Nomad** — if applicable: visa type, income bar, tax treatment
6. **Yacht / Maritime** — if applicable: registration, licensing recognition (captain)
7. **Sommary for RU citizens** — practical notes relevant to Russian applicants
8. **Status** — current "snapshot" line: what changed last, last monitored date, open watch items

Every fact in sections 2-7 carries an inline source reference `^[raw/...]` when it is
numeric or program-specific, and a `confidence` in the frontmatter.

## Concept Pages (`concepts/<program>.md`)
One page per program, e.g. golden-visa, d7-visa, nhr, non-lucrative-visa, blue-card.
Structure: definition, current-state, per-country table (where available), open questions, sources.

## Update Policy (how the weekly monitor edits the wiki)
When new watched news arrives:
1. Match it to an existing country page + section. If the fact differs from what the page
   says: update the value, bump `updated`, append a log entry, and (if the change is
   material) add a delta note in the page's **Status** section.
2. If the news introduces a new condition not in the page: add it, set `confidence`
   based on source strength, mark `new_program`/`rule_change` as appropriate.
3. If the news is identical to what the page already states: make NO change — this is the
   anti-duplicate behavior that keeps the weekly digest fresh.
4. If genuinely contradictory to existing content: record BOTH claims with dates and
   sources, set frontmatter `contradictions: [page]`.
5. Log every change (add/update/contradiction) in log.md.

## Raw / Layer 1
`raw/articles/` holds immutable web extracts. Each gets frontmatter:
```yaml
---
source_url: https://...
ingested: YYYY-MM-DD
sha256: <hex of body>
---
```
Do not edit files under raw/. Corrections go into the wiki pages.

## Delivered Weekly Artifact (`alerts/YYYY-MM-DD.md`)
The monitor's only delivery: a delta report. Format:
```markdown
# Residency Weekly — YYYY-MM-DD
Variance vs database snapshot as of <last-monitored-date>.

## Changed
- Portugal citizenship: 10 → 7 years (updated 2026-09-13) ^[raw/...]

## New
- <new condition added to database>

## Unchanged (silently skipped)
N items matched existing knowledge and did NOT change the database.
```