# Roadmap

Working plan for Residency Radar / Residency Vault. Order = priority inside each stage. Update when something ships (and add it to CHANGELOG.md).

## Positioning
Overview-level, source-cited, continuously monitored reference for residency and citizenship conditions in 163 countries. Information only, never legal advice. English first; a Russian version (`/ru/`) is rolled out page by page via `scripts/translate_ru.py`.

## Stage 0 — Foundations (done / in progress)
- [x] 163 country pages + 10 program pages in one schema (v2)
- [x] Weekly monitor (screen -> deep analysis -> wiki update -> publish)
- [x] Site integrity audit (0 broken links/anchors)
- [x] "Overview information only, not advice" notice on every page + footer
- [x] Technical SEO: canonical, Open Graph, sitemap.xml, robots.txt
- [ ] Extended Snapshot for all 163 countries (cron `extended-snapshot-batch`, ~1 day)
- [x] Disclaimer in the Telegram bot (all answers, /start, /subscribe, Stars invoices, bot profile description EN+RU, channel posts and digest)

## Stage 1 — Be findable (traffic is currently ~0)
- [x] Site verified in Google Search Console and Bing Webmaster Tools (verification files in `static/`); sitemap submission = owner action
- [x] Custom domain residencyradar.org connected to GitHub Pages (Oct 2026)
- [ ] Check indexing after 1-2 weeks (`site:residencyradar.org`)
- [x] SEO pass on country/program pages (data-driven titles/descriptions, JSON-LD, internal links, social card); FAQ markup skipped (Google shows it only for gov/health sites)
- [ ] Backlinks / distribution: Telegram channel @residencyradar, relevant communities, Reddit/HN-style launch post, lists of "digital nomad visa" resources
- [x] Public weekly changes section `/changes/` (one page per week with changes, auto-built from the weekly alert)

- [ ] **Telegram channel content** — dark-brand image cards (`immigration-bot/make_card.py`), queue of country posts, daily draft at 07:00 UTC via cron `channel-daily-post` (approval mode); next series: program types, weekly "Radar" post

## Stage 2 — Content depth (the differentiators)
- [ ] **Community channels per country** — Telegram/forums/Facebook groups/Reddit for expats in each country, with a short note per channel. New section on the country page.
- [ ] **Blogs, experts and helpers per country** — independent bloggers, practitioners, lawyers/agencies, with a clear "listed, not endorsed" rule and criteria for inclusion.
- [ ] **Reviews / community verdicts** — the Community Pulse block exists but is thin: 45 countries have no section, others are one paragraph. Rework: collect real reports (forums, groups), cite each, summarise per program (backlog, rejections, ease). Redo the per-program "Community verdict" the same way.
- [ ] Human spot-check of facts (sample N pages per month, key numbers: income thresholds, durations, fees) and a visible "last verified by a human" flag where done

## Stage 3 — Product
- [ ] **Country-fit quiz in the Telegram bot** — inputs: passport, income, goal (work / remote / invest / retire / study), family, timeline -> top 3-5 countries with thresholds, links to pages, disclaimer. Uses `data/facts.json` and the program tables.
- [ ] Bot: per-user watchlist of countries and alerts on changes (weekly digest filtered by "my countries")
- [ ] Web version of the quiz (reuse the same logic) once the site has traffic

## Stage 4 — Monetization (after traffic exists)
Ordered by speed. Ranges are rough assumptions, not market data.
1. Referral / partner links on high-intent pages (lawyers and relocation agencies, insurance, banking, tax-residency tools). Always disclosed; partners never change the content or ranking.
2. Paid subscription: weekly changes for chosen countries, early alerts (bot Stars today at 199; test email/Telegram tiers, about $5-15/mo)
3. Lead generation from the quiz results to vetted professionals
4. B2B: data feed / API / CSV for lawyers, agencies and relocation companies (needs accuracy commitments, so only after human verification is in place)

- **Open dataset (parked idea)** — publish country x program-type matrix + `facts.json` as CSV/JSON on `/data/`, GitHub, Hugging Face/Kaggle for backlinks and AI-citation signals. Audit 2026-10-12: matrix 163x10 complete; numeric fields partial (gv_min 55, remote_tax 106, DN min income 31 of 48 programs; no years-to-citizenship, mixed currencies/periods). Option A: ship as-is with a "numeric fields partial" note; option B: first extract years-to-citizenship and normalise currency. Revisit once Search Console shows indexing/links.

## Risks to keep in view
- **Legal:** information only; no individual advice, no promises of outcomes; disclose partnerships; check local rules for lead generation.
- **Quality:** one wrong threshold costs more reputation than many right facts gain. Every number carries a source and a check date; add human verification before any paid/B2B offer.
- **Distribution:** the product works, the audience does not exist yet. Stage 1 gates everything below it.

## Later / ideas
- **Special residency conditions per country** — a catch-all for residence programs that do not fit the 10 canonical types (SCHEMA taxonomy): ancestry/heritage and repatriation routes, regimes for nationals of specific countries (treaty/quota), humanitarian and temporary-protection statuses, special professional or regional schemes. Plan: add an "Other / special programs" section to the country page schema (free-form rows: program, who qualifies, conditions, source), collect it during the monitor pass, and promote a type to a canonical class once it shows up in many countries.

- **Russian version, next steps** — weekly changes feed (`/changes/`) is English-only; Yandex Webmaster verification; `translate_ru.py --stale` runs in the weekly pipeline so translations never lag the English pages.
