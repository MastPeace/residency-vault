# Wiki Schema — Residency & Citizenship Conditions (v2, generalized taxonomy)

## Domain
Cross-country living conditions for **every kind of residency program**, plus citizenship
and tax, for a broad country set. Each residency *type* is a canonical row applied
identically to every country page, so programs are comparable across countries
(e.g. Portugal D7 and Italy Elective Residence are BOTH `passive_income_residency`).

This wiki is the single source of truth that a weekly monitor updates in place.
It is NEVER re-derived from scratch.

## Conventions
- File names: lowercase, hyphens (`portugal.md`, `passive-income-residency.md`).
- Every page starts with YAML frontmatter. Use `[[wikilinks]]` (min 2 outbound).
- Bump `updated` on edit. New pages go to index.md. Every action logged in log.md.
- **Every material change MUST also update CHANGELOG.md and README.md** (if structure
  or features change). See CONTRIBUTING.md.
- Language: page content in ENGLISH; official program names kept in original language.
- **Every residency-type row MUST carry**: official program name, conditions
  (income/investment/thresholds as exact numbers), duration, path to citizenship,
  an OFFICIAL source URL (verified), and a community-verdict field.
- **Provenance**: numeric/conditional facts carry `^[url]` or `^[raw/...]`.
- **Community verdict**: cite a SPECIFIC source (Reddit thread, NomadGate, expat
  forum, Telegram channel) per verdict — not an anonymous "people say".

## Cannical Residency Type Taxonomy
Every country page uses this fixed set of row-types. Each type = one row per country
page. `category` in the taxonomy below marks the market each type serves best.

| type_slug                 | meaning                                                       | typical category   |
|---------------------------|---------------------------------------------------------------|--------------------|
| investment_residency      | residence in exchange for investment (Golden Visa, RBI)       | strong_passport    |
| passive_income_residency  | residence on passive income — PT D7, ES NLV, IT Elective...   | clear_pathway      |
| digital_nomad_visa        | remote work / nomad visa — PT D8, ES DNV, HR, ME DNV...       | it_friendly        |
| highly_skilled_employment | EU Blue Card, DE §18a/51a, NL Highly Skilled Migrant...        | it_friendly        |
| startup_entrepreneur      | startup / founder visa                                        | it_friendly        |
| employment_residency      | standard work permit / residence for employees                | clear_pathway      |
| student_residency         | student visa + residence                                      | clear_pathway      |
| family_reunification      | residence through family tie                                  | clear_pathway      |
| retired_residency         | pension / retirement residence (PT D7-retire, ES Non-Lucr.)   | clear_pathway      |
| citizenship_by_investment | DIRECT citizenship for investment (TR, UAE... rare)           | strong_passport    |

Rule: EVERY country page that has residence programs fills in a row for each type
that exists there, with the SAME row schema. If a type does not exist in a country,
write "Not available" — do not omit the row.

## Tag Taxonomy
- Type tags: use the type slugs above plus: citizenship, tax, visa
- Market tags: strong_passport, it_friendly, yacht_captain, popular_ru, clear_pathway
- Status tags: new_program, rule_change, suspension, processing_update, fee_change, deadline, rumor

## Frontmatter (per country page)
```yaml
---
title: Country — Name
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity
tags: [residence, citizenship, tax]
category: strong_passport | it_friendly | yacht_captain | popular_ru | multi
confidence: high | medium | low
sources: [raw/articles/<source>.md]
country_code: XX
---
```

## Country Page Structure (conditions/<country>.md)
Fixed sections, in order. Numbers carry provenance.

1. **Overview** — passport strength, why it matters, overall accessibility.
2. **Residency Programs** — a table of residency types that exist here, one row per
   canonical type, with columns: Type | Official program | Key conditions
   (income/investment/threshold) | Duration | Inline detail links.
3. **Per-Program Detail** — for EACH active residency type, a subsection:
   - **Official name** (native) + English
   - **Conditions**: exact income/investment/thresholds, age, degree, job offer
   - **Duration / renewal**
   - **Path to citizenship** (years counted, language, exam)
   - **Official source** (verified gov/agency URL)
   - **Community verdict**: rating (Works well / Mixed / Problematic) + cited source
4. **Citizenship** — years of residence, language, exam, timeline, dual-citizenship.
5. **Tax** — relevant regimes (flat tax, NHR, non-dom), rates, conditions.
6. **IT / Digital Nomad** — shortcut notes, if applicable.
7. **Yacht / Maritime** — if applicable (registration, captain licensing).
8. **Notes for RU citizens** — practical notes for Russian applicants.
9. **Community pulse** — aggregate: what expats actually report (backlog, rejections,
   ease), with linked sources.
10. **Status** — last change, last monitored, open watch items.

## Concept Pages (concepts/<type>.md or <program>.md)
THESE are the generalizers. Create one concept page PER CANONICAL TYPE slug:
- `concepts/investment-residency.md`, `concepts/passive-income-residency.md`,
  `concepts/digital-nomad-residency.md`, `concepts/highly-skilled-employment.md`,
  `concepts/startup-residency.md`, `concepts/employment-residency.md`,
  `concepts/student-residency.md`, `concepts/family-reunification.md`,
  `concepts/retired-residency.md`, `concepts/citizenship-by-investment.md`.
Each: definition, cross-country comparison TABLE (country | program | threshold |
duration | citizenship path | community verdict), provenance, links back to country pages.

## Page Thresholds & Size
- Create a country page for EVERY country in the configured country set.
- Create a type concept page when the type exists in 3+ countries (or is a headline
  program). A page over ~250 lines → split by section.

## Update Policy (weekly monitor)
Same as v1: match news item to country page + canonical type; if value DIFFERS →
update, bump `updated`, add Status line, log. If IDENTICAL → no change (anti-dup).
If contradictory → record both + `contradictions:` frontmatter + flag for review.

## Raw Layer
Immutable web extracts in `raw/articles/` with frontmatter (source_url, ingested, sha256).

## Weekly Alert (alerts/YYYY-MM-DD.md)
Deltas only: Changed / New / Unchanged(count) / Discovered-countries / validation status.