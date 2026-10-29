# Changelog

All notable changes to this project are documented here. Dates are UTC.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed
- **Mobile country table:** the COUNTRY header cell was pushed ~56px down onto the first row at widths up to 1240px (its sticky `top` offset survived the `position: static` override of the other header cells). The first header cell now keeps only the horizontal sticky.
- **Turkey (user feedback via bot):** property-owner short-term residence corrected (≥ $200,000 appraised value since Oct 2023, own-use only, 25% foreigner-density closed neighborhoods, income proof, 1–2 year term); added the rental/tourist short-term residence route; removed duplicate `retired_residency` row. RU translation will refresh via `translate_ru.py --stale`.

### Fixed
- **Table columns shifted by aliased wikilinks:** `[[united-states|USA]]` inside a table row was split at the pipe, adding a column (student/employment residency and country tables). Source rows now use `[[x\|label]]` (Obsidian/GitHub-safe), and the site generator's row splitter understands both `\|` and pipes inside `[[...]]`. RU `source_hash` values refreshed (formatting-only change).

### Added
- **Telegram subscribe block** under every country and program page (EN + RU): "Follow residency rule changes in Telegram" with a button to the channel, to turn search traffic into channel readers.
- **"At a glance" block on every country page (EN):** visible yes/no answers per program type (naturalisation years, digital nomad visa, investment residency, citizenship by investment, passive income, retirement), built from the Residency Programs table. Added after Search Console showed queries such as "estonia citizenship by investment" that no page answered.
- **Data-driven meta descriptions:** country pages now carry the digital nomad income threshold (30 pages) and "no citizenship by investment" (135) where the table says so; concept pages end with "Compared across N countries" instead of a mid-sentence cut; RU country descriptions include the phrase "вид на жительство". Stray `**`/`[[...]]` markup removed from RU descriptions.
- **Disclaimer coverage in Telegram:** bot profile description (EN + RU) now states "overview only, not legal, tax or immigration advice"; channel posts end with "Не юридическая консультация. Перед подачей документов сверяйтесь с официальными источниками." (generator, unpublished drafts, plus a publish-time safety net); the weekly digest posted by `post_digest.py` ends with the English disclaimer.
- **Russian version at `/ru/`** with an EN/RU switcher in the header (desktop + mobile menu), `hreflang` pairs and ru URLs in the sitemap. All 163 country pages, all 10 program pages, the glossary and the full UI are translated (about 1.4 untranslated fragments per page remain: official program names in other languages and a few long passages that failed number validation). A page whose English source changed falls back to English under a "not translated yet" banner (`noindex`, canonical to the English page) until `translate_ru.py --stale` refreshes it. Translations live in `i18n/ru/` and are produced by the new `scripts/translate_ru.py` (deepseek-v4-pro via OpenRouter; numbers/URLs/citations validated, ~$0.02 per country page). A translation is used only while its `source_hash` matches the English page (hash ignores `last_checked`/`Last monitored`), so stale text is never published; `translate_ru.py --stale` is wired into the weekly pipeline. Weekly changes stay English-only. Markdown twins exist for translated ru pages.
- "Quick answer" summary (key thresholds per program type, official source, verified date; 102 of 163 countries) in the JSON-LD `abstract` and at the top of the `.md` twin only; deliberately not rendered on the HTML page (it duplicated the programs table and crowded the header).
- `.md` twin H1 for countries is now "Country — Residency & Citizenship Conditions" (was duplicated, e.g. "Estonia — Estonia").
- AI-search (GEO) layer: `llms.txt` index and `llms-full.txt`, markdown twin of every country/concept page (`/conditions/x.md`, linked via `rel=alternate`), explicit AI-crawler rules in `robots.txt`, IndexNow ping after each deploy (`scripts/indexnow.py`).

### Fixed
- Mobile header: Telegram and theme buttons no longer shrink on narrow phones (<=360 px); the brand shrinks/ellipsizes instead, logo hidden below 340 px.
- Mobile header: the search box collapsed into an "S." square; below 960 px it is now a magnifier icon button (tap opens the search palette).
- Confidence label in the page header reads "High confidence" (was "High") instead of an unlabeled bar.
- `extended_batch.py`: a successful snapshot resets the attempt counter (otherwise a country would be skipped for good after 3 refreshes in total). Cron gate `ext_pending.sh` includes the UTC hour while work is pending, so the batch no longer stalls after a tick skipped by the Monday monitor window.
- Kazakhstan and Singapore migrated from v1 to SCHEMA v2 (Residency Programs table, Per-Program Detail, Community Pulse) with `scripts/migrate_v2.py` (deepseek-v4-pro, facts from the page only; other sections kept verbatim). Singapore title fixed.
- 12 country pages: Detail/snapshot anchors that pointed to non-existent headings repaired; footnote back-links without a reference are dropped. Site now has 0 broken internal links/anchors and 0 broken wikilinks.
- Concept pages got `category` and `last_checked` in frontmatter.
- Site integrity audit: ~650 dead in-page links (`[[#employment-residency]]` vs `employment_residency` ids) now resolve to the matching heading; unresolved anchors render as plain text; concept-to-concept links no longer point to `conditions/`; `[[usa]]` -> `[[united-states]]`; README counts 100 -> 163.

### Added
- Mobile menu: below 960 px a burger button opens Countries / Programs / Changes / Glossary and the theme switch (the header theme button is hidden on mobile).
- `404.html` (noindex, links to the main sections).
- `/changes/`: weekly changes section built from `alerts/YYYY-MM-DD.md` (Changed + New items; only weeks with changes), one page per week plus an archive, "Changes" menu item, "Change history" block on country pages, link from the home page, sitemap entries. The monitor recipe documents the item format the parser expects.
- SEO pass: data-driven page titles and unique meta descriptions for country and program pages (routes offered, years to citizenship, remote-worker tax), keyword-bearing H1 suffix, JSON-LD (Article, BreadcrumbList, WebSite, Organization), robots meta, social card (`assets/og-card.png`), "More countries in <region>" and "program types" internal-link blocks, sitemap `lastmod` from the page's content-change date.
- `static/` directory: files copied verbatim to the site root (Google Search Console verification file).
- Custom domain `residencyradar.org` (GitHub Pages, Namecheap DNS); canonical/OG/sitemap/robots and README now use it.
- Country flags (vendored PNGs in `assets/flags/`, ~650 KB) next to the country code on every country page and in the countries table.
- Overview/"not advice" notice at the bottom of every country and program page and of the home page, expanded footer and README disclaimer.
- Technical SEO: canonical + Open Graph tags on all pages, `sitemap.xml`, `robots.txt` (site was not discoverable before).
- `ROADMAP.md`: staged plan (findability, community channels, experts/helpers, reviews, quiz bot, monetization).
- Country table: Programs column with icons per offered residency route (closed routes left out) plus program filter buttons; Cost index (Numbeo, NYC=100) and Rent $/mo (approximate USD) columns.
- `data/facts.json`: structured facts per country (investment-residency minimum, remote-work visa + income threshold, remote tax range), extracted by `scripts/extract_facts.py` (deepseek-v4-pro) with a verbatim evidence quote each; facts whose quote is not found on the page are dropped. 55 investment minimums, 152 remote-visa and 106 tax values for 163 countries.
- Country table: "More columns" toggle with Investment from / Remote visa / Remote tax (hover shows the source quote).
- `scripts/normalize_numbers.py`: amounts and durations written as digits (`€250K` -> `€250,000`, `five years` -> `5 years`) across 99 pages; rule added to SCHEMA.md.
- Site: separate `countries.html`, `programs.html` and `glossary.html` pages (glossary is edited in `glossary.md`); the home page is now a landing page with the latest monitoring changes.

### Fixed
- Site: 63 countries had an empty Region (registry groups without a display label); they are now folded into display regions (added Asia, Central Africa).

### Changed
- Telegram channel link is now https://t.me/residencyradar (was `migrate_easy`): header button, footer icon and JSON-LD `sameAs`.
- Country table: single-line, smaller column headers with the `*` attached to the title; tag `#passport` shortened to `#pass`.
- Branding: site header now shows the Residency Radar logo (round, light and dark variants that follow the theme) and the name "ResidencyRadar"; new favicon set (SVG, PNG 16/32/48, ICO, Apple touch icon) built from `assets/`; the header carries the subtitle "powered by Residency Vault" (hidden on narrow screens) and the footer repeats it. Repository name and site URL are unchanged.
- Country table: header stays visible while scrolling; column titles shortened (Citizen yrs, Visa-free, Cost idx, Invest min, Nomad visa, Tax %, Trust); filter bar no longer sticky.
- Country table: investment minimums and remote-visa income thresholds are shown in US dollars (`≈` when converted at approximate rates); the original amount stays in the tooltip.
- Country table: region and fit tags moved to their own compact columns (region codes like `EU-W`, tags like `#passport #path`; hover for full names; codes listed in the glossary).
- Country table shows all columns at once (the "More columns" toggle is gone); region and fit tags moved under the country name; `*` next to column titles opens a popover with a short definition and a glossary link instead of jumping to the glossary.
- Site: country table drops the country-code and "Checked" columns; Passport, To citizenship, Fit and Confidence headers carry a `*` link to the glossary, with a footnote under the table.
- Site: top nav keeps only in-site links (Countries, Programs); Telegram is a highlighted 'News channel' button next to search; GitHub and Telegram are icon links in the footer.
- Site: country header fact `1-bed rent` relabelled `1-bed rent / month` (the underlying field was already monthly).
- Site: link to the Telegram channel (https://t.me/migrate_easy) in the top nav and the footer.
- Extended Snapshot: FATF status now comes from one central facts file (`references/facts/fatf.json`, as of 2026-06-19) instead of per-page worker output; CRS participation and the tax treaty with Russia show `No reliable data` until their facts files are verified. Worker source links are now checked for existence (23 of 478 pilot links were dead and are demoted to `unsourced`).
- Site: Extended Snapshot renders as collapsible per-block cards.

### Changed
- **Site redesign** (`scripts/generate_site.py`): light "paper" theme with dark toggle (system preference respected), serif headings + sans/mono data, single green accent. Replaces the 163-link sidebar with a top bar and a `/` or Ctrl/Cmd+K search palette.
- Home page is now a sortable, filterable country table (fit categories, region, confidence; columns: years to citizenship, passport, confidence, last checked) plus program comparisons.
- Country pages: key-facts strip, Monitoring panel (recent changes / watch items) moved to the top, sticky "On this page" TOC, strengths/problems side by side, snapshot sources rendered as links with official/estimate markers.

### Fixed
- Country Card "General description" was silently dropped; Country Snapshot table printed its header row as data; titles with ` - ` separator (e.g. Malawi) now get clean display names.

### Added
- **Extended Snapshot (pilot, 10 countries)**: 55 extra fields in 12 blocks (geography, climate, economy, technology, HDI, safety, money & tax, business, education, connectivity, sanctions/visa, quality of life); practice-dependent fields (banks, acceptance of Russians, flights, policy mood) deliberately excluded on portugal, georgia, uae, serbia, thailand, malta, dominica, kazakhstan, estonia, fiji. New `scripts/fetch_indicators.py` (World Bank API, stdlib) and `scripts/build_extended_snapshot.py`; SCHEMA v4 spec.

### Fixed
- 81 broken `[[wikilinks]]` on 50 country pages now point to the real concept pages (`digital-nomad-visa`, `student-residency`, `family-reunification`, `retired-residency`, `investment-residency`, `highly-skilled-employment`); links to non-existent pages became plain text.
- `SCHEMA.md` concept page names aligned with the files in `concepts/`.
- `central-african-republic`: malformed "Notes for RU citizens" heading.
- Monitoring pipeline: country detection missed 13 countries and matched substrings (e.g. "oman" in "Romanian"); screening now covers the whole registry in batches with a hard coverage check; deep collection is batched.

## [2026-10-11] — Registry extended to 163 countries (waves 1+2)

### Added
- **63 new countries** added to `regions.yaml`: Asia (china, hong-kong, taiwan, india,
  indonesia, thailand, malaysia, philippines, sri-lanka, myanmar), Europe micro/tax
  (andorra, monaco, liechtenstein, san-marino, ukraine, moldova, belarus), CBI Caribbean
  (dominica, st-lucia, st-vincent, vanuatu, trinidad-and-tobago, cayman-islands,
  british-virgin-islands, turks-and-caicos, cuba, haiti), Africa (comoros, cabo-verde,
  sao-tome, gabon, eswatini + angola, cameroon, mozambique, zambia, zimbabwe, madagascar,
  benin, togo, sierra-leone, liberia, guinea, burkina-faso, mauritania, djibouti, gambia,
  lesotho, malawi, congo, democratic-republic-of-congo, equatorial-guinea,
  central-african-republic), South America (venezuela, guyana, suriname), Oceania
  (fiji, samoa, tonga, papua-new-guinea, solomon-islands, marshall-islands), Middle East
  (lebanon). Registry is now 163 countries.
- Collector `GLOBAL_COUNTRY_ALLOWLIST` extended with the new countries (detection
  aliases + capitals) so screening/deep collection can detect them.
- Country pages for the new countries (being generated; fulfilled per SCHEMA).

## [2026-10-11] — Freshness signals + restored corrupted pages

### Added
- **`last_checked`** frontmatter field: date of the last monitor pass that actually
  queried the country (set by `stamp_last_checked.py` on every weekly run, even when
  nothing changed). Site now renders both **Updated** (content change) and **Checked**
  (last monitor pass) on country pages.
- `covered_<stamp>.json` written by the collector (list of countries actually queried),
  feeding the stamp step in the weekly pipeline (`daily_digest.md` Step 5).
- **kazakhstan** added to `regions.yaml` (balkans_caucasus) — was missing from the
  registry despite having a wiki page and keyword configs.

### Fixed
- **Japan, Singapore, South Korea, Vietnam** pages were corrupted by the 2026-09-16
  SCHEMA v3 bulk commit (template artifact `{{existing['content']}}` replaced the full
  content). Restored full content from git history + kept Snapshot/Card; fix noted in
  each page's Status section.
- Backfilled `Last monitored` / `last_checked: 2026-10-05` for the 20 countries actually
  covered by weekly runs (the ~80 remaining countries have no keyword configs yet and
  are honestly left un-stamped until the monitor covers them).

### Notes
- Weekly runs currently query only ~20 of 100 countries (120-query cap + 21 countries
  with keyword configs). Pages for uncovered countries keep their seed dates — this is
  now visible as a missing `Checked` date rather than a misleading old `Updated`.

## [2026-09-16] — Country Snapshot + Country Card (data) for all 100 countries

### Added
- **Country Snapshot** (19-row table) + **Country Card** (general description / well-known
  strong points / well-known problems) added to all 100 `conditions/*.md` pages.
- Hard fields (population, main religion/language/city, GDP/capita PPP, passport strength,
  Rule of Law Index, Freedom House score, sunshine hours, avg temperature) sourced from
  World Bank / IMF / CIA Factbook / official index / climate sources with URLs.
- Soft fields (median net salary, cost-of-living index, 1-bed rent, effective tax for
  remote workers) tagged `[soft/estimate]` (Numbeo-type market estimates).
- Residency rows (years to citizenship, max permitted absence, remote-work residence
  availability) made consistent with each page's own residency sections.

### Notes
- Filled over several parallel waves; a few runs hit a transient API-credit ceiling (HTTP 402)
  and were re-dispatched in smaller batches — final coverage verified at 100/100.

## [2026-09-15] — v3: Country Snapshot + Country Card schema

### Added
- **SCHEMA v3**: two new required country-page sections:
  - `## Country Snapshot` — 19-row quantitative table (population, main religion/language/city, coastline, tourism impact, GDP/capita PPP, median net salary, cost-of-living, 1-bed rent, effective tax for remote workers, remote-work residence availability, years to citizenship, max permitted absence, passport strength, Rule of Law Index, Freedom House score, sunshine hours, average temperature). Hard fields MUST be official-sourced (World Bank / IMF / stat agency / official gov); soft fields (salary, cost-of-living, rent, effective tax) MAY use market estimates (Numbeo-type) tagged `[soft/estimate]` with source.
  - `## Country Card` — general description + well-known strong points + well-known problems (factual, balanced).
- `scripts/generate_site.py`: renders Country Snapshot as a Key/Value table with source annotations and Country Card as a styled strong-points (green) / problems (orange) box; dark theme.

### Pending
- Per-country data (Snapshot + Card) to be added to all 100 `conditions/*.md` (data-gathering wave in progress).

## [2026-09-15] — static website + GitHub Pages

### Added
- `scripts/generate_site.py` — pure-Python-stdlib static site generator with dark
  Wikipedia-style theme, sidebar navigation by region, client-side search, wikilink
  resolution, and responsive layout.
- `.github/workflows/gh-pages.yml` — GitHub Actions workflow that builds the static
  site and deploys to GitHub Pages on every push to `main`.
- `README.md` — full project README replacing the 2-line stub.
- `CHANGELOG.md` — this file.
- `CONTRIBUTING.md` — contribution and update-policy rules.

### Changed
- Repository made public; GitHub Pages enabled.

### Fixed
- Relative-link bug in static site (subpath 404s) — site is now fully navigable on
  GitHub Pages.

## [2026-09-14] — v2 global rebuild

### Added
- Expanded from 22 to 100 country pages covering all regions: Western Europe,
  Eastern Europe, Balkans & Caucasus, Middle East & Gulf, North/West/East & South
  Africa, Latin America, Caribbean & Central America, North America & Oceania.
- 10 residency-type concept pages replacing 7 v1 concept pages: `investment-residency`,
  `passive-income-residency`, `digital-nomad-visa`, `highly-skilled-employment`,
  `startup-entrepreneur`, `employment-residency`, `student-residency`,
  `family-reunification`, `retired-residency`, `citizenship-by-investment`.
- Each country page now has a canonical residency-type structure (SCHEMA v2) with
  verified official source URLs, exact thresholds, and community verdict labels.

### Changed
- **SCHEMA.md v2**: canonical residency-type taxonomy (10 types) replacing v1's
  ad-hoc program-based tags. Every country page now uses the same row structure
  for direct cross-country comparison.
- Portugal D7, Spain NLV, Italy Elective Residence, Greece FIP unified under
  `passive_income_residency`.
- `index.md` regenerated with region-grouped structure.

### Fixed
- Montenegro: added its digital nomad visa (previously missing).
- `scripts/auto-sync.sh`: now commits untracked/new files (was ignoring new `alerts/`).

## [2026-09-13] — initial build

### Added
- Seeded 22-country watchlist wiki with `conditions/` and 7 concept pages.
- Weekly monitor pipeline wired: collect → analyze → validate → update DB → push.
- GitHub repository initialized with `auto-sync.sh`, `SCHEMA.md`, `index.md`,
  `log.md`, `regions.yaml`.
- `GH_TOKEN` integration in `~/.hermes/.env` for authenticated pushes.