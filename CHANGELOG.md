# Changelog

All notable changes to this project are documented here. Dates are UTC.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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