# Wiki Schema — Residency & Citizenship Conditions (v3, generalized taxonomy)

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
10. **Country Snapshot** — a standard 19-row data table (see [[#country-snapshot-spec]]).
11. **Country Card** — general description + qualitative profile (see [[#country-card-spec]]).
12. **Status** — last change, last monitored, open watch items.

### Country Snapshot Spec

A fixed 19-row data table that every country page must contain. Each row carries a
**Field**, **Value**, and **Source/Confidence** annotation.

**Confidence model**:

- **Hard (official)**: value must be sourced from an authoritative reference with a
  verifiable URL (World Bank, IMF, UN, official national statistics agency, government
  source, reputable global index). Confidence = `high`. If a hard value genuinely
  cannot be confirmed, set the Value to `No reliable data` with confidence `low` —
  never fabricate, never estimate on hard fields.
- **Soft (estimate)**: value may come from market/estimated/aggregator sources
  (Numbeo, cost-of-living aggregators, salary surveys, expat forums) and must be
  tagged `[soft/estimate]` with a source URL. Confidence = `medium`. If no credible
  estimate exists, set Value to `No recent data` with confidence `low`.

**Rows** (exact labels, in order):

1. Population
2. Main religion
3. Main language
4. Main city (capital or largest)
5. On the coast? (yes/no/short note)
6. Tourism impact in season (none / low / medium / high + note on seasonal pressure)
7. GDP per capita (PPP)
8. Median net monthly salary
9. Cost of living index (relative, base note)
10. Monthly rent, 1-bedroom apartment
11. Effective personal tax rate for remote workers
12. Remote-work / self-employment residence available?
13. Years to citizenship
14. Maximum permitted absence during residence
15. Passport strength after citizenship (visa-free count)
16. Rule of Law Index
17. Freedom House score
18. Average annual sunshine hours
19. Average annual temperature

**Hard fields** (rows 1–4, 7, 15–19): Population, Main religion, Main language,
Main city, GDP per capita (PPP), Passport strength, Rule of Law Index, Freedom
House score, Sunshine hours, Average temperature. These **MUST** carry a URL to
an official/authoritative source. Value extraction error tolerance: ±0.

**Soft fields** (rows 5–6, 8–14): On the coast (requires short note — semi-hard),
Tourism impact, Median net salary, Cost of living index, 1-bed rent, Effective tax
for remote workers, Remote-work availability, Years to citizenship (official),
Maximum permitted absence. These **MAY** use market/estimated sources (Numbeo-type)
and **MUST** be tagged `[soft/estimate]` with source URL.

**Format** (source .md — data wave may write either):

*Table form* (preferred):
```
| Field | Value | Source / Confidence |
|---|---|---|
| Population | ~38,000,000 | ^[https://stat.gov.pl/en/] hard/official |
| ... | ... | ... |
```

*List form* (accepted):
```
- **Population**: ~38,000,000 ^[https://stat.gov.pl/en/] hard/official
- **Main religion**: Catholicism ^[https://www.cia.gov/the-world-factbook/] hard/official
- ...
```

Renderer must handle both forms and produce a two-column Key/Value table with
source annotation next to each value.

### Country Card Spec

Three qualitative sub-blocks every country page must include, factual and balanced
(not marketing copy), based on the country's real profile:

1. **General description** (2–4 sentences): geography, economy, society, expat relevance.
2. **Well-known strong points** (bulleted list, 3–6 items).
3. **Well-known problems** (bulleted list, 3–6 items).

Example (Switzerland): strong points = political stability, competitive tax,
mountains/quality of life; problems = very high cost of living, housing shortage,
strict citizenship process.

**Format** (source .md):

```
## Country Card

General description text here. 2–4 sentences covering geography, economy,
society, and expat relevance.

### Well-known strong points
- Factual strength 1
- Factual strength 2
- ...

### Well-known problems
- Factual problem 1
- Factual problem 2
- ...
```

Renderer must produce a styled box: the description as a paragraph, strong points
in a green-tinted list, problems in an orange-tinted list, dark-theme consistent.

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