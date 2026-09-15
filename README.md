# Residency Vault

An Obsidian-compatible markdown knowledge base of residency & citizenship conditions
across ~100 countries, using a canonical residency-type taxonomy, auto-refreshed by a
weekly/monthly monitor and published as a Wikipedia-style static website.

**Live site:** [mastpeace.github.io/residency-vault](https://mastpeace.github.io/residency-vault/)

---

## 1. What It Is

- **100 country pages** covering every region: Western/Eastern Europe, Balkans & Caucasus,
  Middle East & Gulf, North/West/East & South Africa, Latin America, Caribbean & Central
  America, North America & Oceania — plus Kazakhstan.
- **10 canonical residency-type generalizer pages** (concept pages) with cross-country
  comparison tables drawn from real country data.
- Every country page carries: exact conditions and thresholds (income, investment, duration),
  path to citizenship, tax regime, official government/agency source URL (verified), and a
  community verdict with cited source.
- Fully cross-linked as an **Obsidian wiki** (wikilinks, YAML frontmatter, Dataview-compatible).
- Auto-published as a **dark-themed Wikipedia-style static website** via GitHub Pages.
- **Automated refresh**: a weekly monitor updates 22 key watchlist countries; a monthly
  monitor refreshes the full ~100-country set. Changes are collected, analyzed (on
  deepseek-v4-pro), validated, and applied as deltas to the wiki database — never
  re-derived from scratch.

---

## 2. Repository Structure

```
wiki/
├── README.md              ← this file
├── SCHEMA.md              ← v2 canonical residency-type taxonomy & conventions
├── index.md               ← structured wiki index (country pages by region + concepts)
├── log.md                 ← append-only chronological wiki action log
├── CHANGELOG.md           ← project changelog (keep-a-changelog style)
├── CONTRIBUTING.md        ← contribution & update-policy rules
├── regions.yaml           ← global country registry grouped by region
├── .gitignore
├── conditions/            ← 100 country pages (conditions/<country>.md)
├── concepts/              ← 10 residency-type generalizer pages
├── alerts/                ← weekly delta reports (alerts/YYYY-MM-DD.md)
├── raw/articles/          ← immutable web extracts (monitor snapshots)
├── scripts/
│   ├── generate_site.py   ← stdlib-only static site generator (dark Wikipedia theme)
│   └── auto-sync.sh       ← auto-commit + push to GitHub
└── .github/workflows/
    └── gh-pages.yml       ← GitHub Actions deploy to GitHub Pages
```

---

## 3. Live Website

Every push to `main` triggers a GitHub Actions workflow that rebuilds the static site
and deploys it to GitHub Pages. No manual build step required.

**URL:** [https://mastpeace.github.io/residency-vault/](https://mastpeace.github.io/residency-vault/)

The site features: dark theme, sidebar navigation by region, client-side search,
concept pages, wikilink-aware internal linking, footnotes, and responsive layout.

---

## 4. Schema & Residency Taxonomy

The wiki is governed by `SCHEMA.md` (v2), which defines a **canonical residency-type
taxonomy**. Every country page uses the same 10 row-types, making programs directly
comparable across countries:

| # | Type slug | Meaning |
|---|-----------|---------|
| 1 | `investment_residency` | Golden Visa, RBI — residence for investment |
| 2 | `passive_income_residency` | Passive-income residence (PT D7, ES NLV, IT Elective, GR FIP) |
| 3 | `digital_nomad_visa` | Remote-work / nomad visa (PT D8, ES DNV, HR, GE C5) |
| 4 | `highly_skilled_employment` | EU Blue Card, skilled-migrant permits |
| 5 | `startup_entrepreneur` | Startup / founder visa |
| 6 | `employment_residency` | Standard work-permit residence |
| 7 | `student_residency` | Student visa + residence |
| 8 | `family_reunification` | Residence through family tie |
| 9 | `retired_residency` | Pension / retirement residence |
| 10 | `citizenship_by_investment` | Direct citizenship for investment (rare) |

Each type has a corresponding concept page at `concepts/<type>.md` with a definition,
cross-country comparison table, and provenance.

Full conventions (frontmatter, page structure, provenance, community verdicts, update
policy) are in `SCHEMA.md`.

---

## 5. How the Data Is Maintained

The wiki is the **single source of truth** — it is never re-derived from scratch.
Updates arrive through a monitored pipeline (the immigration-monitor skill):

```
collect → analyze (v4-pro) → validate → update DB (deltas) → push → site rebuild
```

**Two scopes:**

| Scope | Frequency | Countries | Description |
|-------|-----------|-----------|-------------|
| Watchlist | weekly | ~22 key countries | Focused alert feed from a curated watchlist |
| Full | monthly | ~100 countries (from `regions.yaml`) | Full-DB refresh across all regions |

**Pipeline steps:**
1. **Collect** — web search for each country → raw items (7-day window).
2. **Analyze** — deepseek-v4-pro subagent deduplicates, classifies, writes structured JSON.
3. **Validate** — `validate.py` enforces schema; pipeline stops on failure.
4. **Update DB** — each validated item is matched to the correct country page + canonical
   type. If the fact is new/different → update, bump `updated`, add `Status` line, log.
   If identical → no change (anti-duplicate).
5. **Push** — `scripts/auto-sync.sh` commits and pushes to GitHub.
6. **Site rebuild** — `.github/workflows/gh-pages.yml` auto-deploys on every push.

The pipeline recipe lives at:
`~/.hermes/skills/autonomous-ai-agents/immigration-monitor/references/daily_digest.md`

---

## 6. Usage

### As an Obsidian Vault

Open `/home/vovka/wiki` as an Obsidian vault. All pages use `[[wikilinks]]` for
cross-referencing. YAML frontmatter enables Dataview queries. The graph view shows
the full knowledge graph (countries ↔ concepts ↔ regions).

### As a Static Website

Visit [mastpeace.github.io/residency-vault](https://mastpeace.github.io/residency-vault/).
Browse countries by region in the sidebar, search with the built-in client-side search,
and navigate cross-references via wikilinks converted to HTML.

---

## 7. Development & Contributing

### How the Static Site Generator Works

`scripts/generate_site.py` is a pure-Python-3-stdlib generator (no dependencies).
It reads all `conditions/*.md` and `concepts/*.md`, parses YAML frontmatter, converts
markdown to HTML (tables, wikilinks, footnotes, code blocks), and renders complete
HTML pages with a dark Wikipedia-style theme. Output lands in `site_output/` (gitignored).

### How to Add a Country

1. Create `conditions/<country>.md` following `SCHEMA.md` conventions.
2. Add the country to `regions.yaml` under the correct region.
3. Add the page to `index.md` under its region group.
4. Append a log entry to `log.md`.
5. The next push triggers auto-rebuild.

### How to Update the Schema

1. Edit `SCHEMA.md` — bump the version, update the taxonomy or conventions.
2. Apply changes to all affected country pages.
3. Regenerate concept pages if cross-country tables changed.
4. Append log + CHANGELOG entries.

### How a Change Reaches the Live Site

```
edit markdown → git commit + push → GitHub Actions → Pages deploy
```

`scripts/auto-sync.sh` handles the commit-push step (uses `GH_TOKEN` from `~/.hermes/.env`).

---

## 8. Configuration & Cron

The data-refresh pipeline is defined in the immigration-monitor skill. Two scopes are
used:

- **Weekly watchlist** (~22 countries) — collects, analyzes, validates, and applies
  deltas to the wiki DB, then pushes.
- **Monthly full refresh** (~100 countries from `regions.yaml`) — same pipeline on a
  broader scope.

The pipeline requires a Hermes environment with `cron_mode: approve` (the execute_code
step needs approval). The `GH_TOKEN` for pushing lives in `~/.hermes/.env` (never
committed to the repo).

---

## 9. Changelog Policy

Every material change to the project (schema changes, new features, bug fixes, pipeline
modifications) **must** be recorded in `CHANGELOG.md` in [keep-a-changelog](https://keepachangelog.com/)
style. Additionally, if the repository structure or features change, `README.md` should
be updated to reflect reality. See `CONTRIBUTING.md` for the full update policy.

---

## License

This project is a personal knowledge base. All country-condition data is sourced from
public official government websites and community forums; see individual pages for
provenance links.