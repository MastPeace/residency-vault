# Roadmap

Working plan for Residency Radar / Residency Vault. Order = priority inside each stage. Update when something ships (and add it to CHANGELOG.md).

## Positioning
Overview-level, source-cited, continuously monitored reference for residency and citizenship conditions in 163 countries. Information only, never legal advice. English first; a Russian version is deferred until the English product has an audience.

## Stage 0 — Foundations (done / in progress)
- [x] 163 country pages + 10 program pages in one schema (v2)
- [x] Weekly monitor (screen -> deep analysis -> wiki update -> publish)
- [x] Site integrity audit (0 broken links/anchors)
- [x] "Overview information only, not advice" notice on every page + footer
- [x] Technical SEO: canonical, Open Graph, sitemap.xml, robots.txt
- [ ] Extended Snapshot for all 163 countries (cron `extended-snapshot-batch`, ~1 day)
- [x] Disclaimer in the Telegram bot (all answers, /start, /subscribe, Stars invoices); channel digest posts and bot profile description still to cover

## Stage 1 — Be findable (traffic is currently ~0)
- [ ] Register the site in Google Search Console and Bing Webmaster Tools, submit `sitemap.xml` (owner action: needs the Google account)
- [x] Custom domain residencyradar.org connected to GitHub Pages (Oct 2026)
- [ ] Check indexing after 1-2 weeks (`site:residencyradar.org`)
- [ ] SEO pass on country/program pages: titles and descriptions per target query ("Portugal D7 visa requirements 2026"), structured data (FAQ/Article), internal links between countries and programs
- [ ] Backlinks / distribution: Telegram channel @migrate_easy, relevant communities, Reddit/HN-style launch post, lists of "digital nomad visa" resources
- [ ] Public "Changes this week" page (shows freshness, gives search engines something new weekly)

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

## Risks to keep in view
- **Legal:** information only; no individual advice, no promises of outcomes; disclose partnerships; check local rules for lead generation.
- **Quality:** one wrong threshold costs more reputation than many right facts gain. Every number carries a source and a check date; add human verification before any paid/B2B offer.
- **Distribution:** the product works, the audience does not exist yet. Stage 1 gates everything below it.

## Later / ideas
- **Special residency conditions per country** — a catch-all for residence programs that do not fit the 10 canonical types (SCHEMA taxonomy): ancestry/heritage and repatriation routes, regimes for nationals of specific countries (treaty/quota), humanitarian and temporary-protection statuses, special professional or regional schemes. Plan: add an "Other / special programs" section to the country page schema (free-form rows: program, who qualifies, conditions, source), collect it during the monitor pass, and promote a type to a canonical class once it shows up in many countries.

## Parked
- Russian-language version (revisit when the English site has steady traffic)
