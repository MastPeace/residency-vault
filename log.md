# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete

## [2026-09-13] create | Wiki initialized
- Domain: Residency & Citizenship Conditions across countries (strong passport / IT-friendly / popular for RU / yacht)
- Structure created with SCHEMA.md, index.md, log.md: conditions/, entities/, concepts/, comparisons/, queries/, raw/, scripts/
- WIKI_PATH set to /home/vovka/wiki
- Phase 1 (seed) pending: build country condition pages from collected monitor data + authoritative sources

## [2026-09-14] update | Weekly monitor run — 5 country pages + alerts
- conditions/armenia.md — Added Nov 1, 2026 comprehensive reform details (work visas, labor market test abolition, business thresholds AMD 2M/1M, employer notification). Bumped updated.
- conditions/croatia.md — Added DN visa-hopping crackdown (in-country status switching prohibited without exit). Bumped updated.
- conditions/cyprus.md — Updated marriage citizenship bill: 3→6 months for spouses abroad, marriage ≥5 years (corrected from ≥3). Bumped updated.
- conditions/georgia.md — Three major updates: (1) marriage residence restructured Sep 1 2026 (temp 1yr→5yr→PR, commission, criminal liability); (2) student residence tightened (school students excluded, presence monitoring, Jan 1 2027 deadline); (3) NEW C5 Digital Nomad Visa added (adopted Apr 16, 2026). Bumped updated.
- conditions/germany.md — Added EES biometrics date (Apr 10, 2026), family reunification suspension for subsidiary protection, CDU/CSU citizenship rollback rumor. Bumped updated.
- alerts/2026-09-14.md — Delta report: 8 changed, 0 new, 2 unchanged, 13 discovered countries
- Status: Collector 87 items, Analyzer 10 items (validated OK), 12 watchlist countries with zero news

### Country pages (22 files — conditions/)
- conditions/armenia.md — confidence: high (evidence-rich; 11 snapshot items + MFA sources)
- conditions/austria.md — confidence: medium (web sources: migration.gv.at, EU Blue Card official)
- conditions/croatia.md — confidence: high (evidence-rich; 10 snapshot items)
- conditions/cyprus.md — confidence: high (evidence-rich; 13 snapshot items + analyzed)
- conditions/czechia.md — confidence: high (evidence-rich; 11 snapshot items)
- conditions/estonia.md — confidence: high (evidence-rich; 13 snapshot items)
- conditions/georgia.md — confidence: high (evidence-rich; 8 snapshot items + espero.ge)
- conditions/germany.md — confidence: high (evidence-rich; 15 snapshot items)
- conditions/greece.md — confidence: high (web sources: getgoldenvisa.com, goldenharbors.com, official tiers)
- conditions/ireland.md — confidence: medium (web sources: total.law, consiliojus.com)
- conditions/italy.md — confidence: medium (web sources: romeing.it, taxesforexpats.com)
- conditions/kazakhstan.md — confidence: medium (web sources: tengrinews.kz, astanatimes.com, timesca.com)
- conditions/malta.md — confidence: medium (web sources: workvisa.guide, ccmalta.com, imperiallegal.com)
- conditions/montenegro.md — confidence: medium (web sources: goldenvisas.com, worldcompanysetup.com)
- conditions/netherlands.md — confidence: medium (web sources: dutchreview.com, ind.nl, lawandmore.eu)
- conditions/poland.md — confidence: medium (web sources: latwy-start.pl, migrant.poznan.uw.gov.pl)
- conditions/portugal.md — confidence: high (web sources: AIMA, globalcitizensolutions.com, movingto.com)
- conditions/serbia.md — confidence: medium (web sources: mycitizensagency.com, globalcitizensolutions.com, welcometoserbia.gov.rs)
- conditions/singapore.md — confidence: medium (web sources: eh-immigration.com, one-visa.com, tip.com.sg)
- conditions/spain.md — confidence: high (web sources: exteriores.gob.es, goldenharbors.com)
- conditions/turkey.md — confidence: high (web sources: Wikipedia, astons.com, globalcitizensolutions.com)
- conditions/uae.md — confidence: high (web sources: u.ae official portal, sarmat.ae, egsh.ae)

### Concept pages (7 files — concepts/)
- concepts/golden-visa.md — definition + 8-country table
- concepts/digital-nomad.md — definition + 9-country table
- concepts/blue-card.md — definition + 7-country EU Blue Card table
- concepts/d7-visa.md — passive income residence routes
- concepts/d8-visa.md — Portugal remote work visa
- concepts/nhr.md — special tax regimes for new residents (11-country table)
- concepts/non-lucrative-visa.md — residence without work rights

### Index and schema
- index.md — updated with all 29 pages + one-line summaries | Total pages: 32
- log.md — this entry

## [2026-09-13] update | Weekly monitor — manual live run
- Runtime: manual foreground run (cron `run` spawn is broken on this box — see note).
- Collected 81 raw items (7-day window), Stage A flagged 13 NEW countries (no pages created).
- Analyzed on deepseek-v4-pro: 1 grounded item survived 7-day window (cyprus — citizenship rule for spouses).
- Validated 1/1 OK.
- DB delta: NO change (cyprus fact already present; anti-duplicate per SCHEMA Update Policy).
- Alerts file: alerts/2026-09-13.md written, pushed to GitHub (commit e7202ab).
- Fixed scripts/auto-sync.sh: now also commits untracked/new files (was ignoring new alerts/).

## [2026-09-14] rebuild | v2 global rebuild — canonical residency-type taxonomy
- Rebuilt SCHEMA.md to v2: canonical residency-type taxonomy (investment_residency, passive_income_residency, digital_nomad_visa, highly_skilled_employment, startup_entrepreneur, employment_residency, student_residency, family_reunification, retired_residency, citizenship_by_investment).
- Expanded from 22 to 100 country pages across all regions (EU, Balkans/Caucasus, Gulf, Africa N/W/E-S, LatAm, Caribbean, North America/Oceania).
- Every country page: same canonical row structure, official gov/agency source (verified via web_search/web_extract), exact numbers with ^[url], community verdict label.
- Fixed errors from v1: montenegro now correctly has a digital nomad visa (€2,010/mo, 2+2 yrs); D7/NLV/Elective/FIP now unified under passive_income_residency.
- Replaced 7 v1 concept pages with 10 v2 residency-type generalizers (cross-country comparison tables drawn from real country data).
- index.md regenerated (100 countries by region + 10 concepts).
- Community-forum research deferred per user (verdicts labelled heuristically only).


## [2026-09-21] update | Weekly monitor — 3 country pages
- armenia.md: citizenship fee increases (50K→250K ARM, 150K→1.5M renunciation) + physical presence requirements (549d/3yr spouses, 915d/5yr general). Source: arka.am.
- cyprus.md: EC Schengen technical readiness approved Aug 2026 + mandatory medical exams for Immigration Permit A-F from Sep 1, 2026. Sources: expatsi.com, visasupdate.com.
- georgia.md: deportation + 2–5 year entry ban for unauthorized work (Sep 1, 2026). Kazakhstan MFA travel warning. Source: astanatimes.com.
- Alert written: alerts/2026-09-21.md
- Unchanged (5 items skipped): armenia digitalization, cyprus PR due diligence, cyprus spouse citizenship bill, georgia marriage route, georgia work permits.
- Discovery: china, india, malaysia flagged (no actionable items).

## [2026-10-05] update | Weekly full-refresh — 6 analyzed → 2 pages updated
- Collector: scope='all', 72 raw items from 34 countries, query cap reached at 120.
- Analyzer: 6 items from 3 countries (armenia ×2, cyprus ×3, georgia ×1). Validated OK.
- Changed (3):
  - armenia.md: Reform implementation date shifted Aug 1 → Nov 1, 2026 (parliament source). CBI rumor ($150K) added to citizenship section.
  - cyprus.md: Golden Visa tightening ahead of Schengen accession added (plaininvestor.com, Oct 2026).
- Unchanged (3): cyprus spousal citizenship, cyprus medical exams, georgia spousal route — all already in DB.
- Discovery: 34 countries seen, 2 not in watchlist: china, india.
- Alert written: alerts/2026-10-05.md
- Collector: scope='all' (~100-country registry), 74 raw items, 7 countries with hits, query cap reached at 120
- Analyzer: 10 items from 5 countries (armenia, croatia, cyprus, estonia, georgia). Validated OK.
- Changed (2):
  - armenia.md: H1 2026 total permits updated 8,181→10,561 (incl. permanent). Source: armenpress.am.
  - croatia.md: Aliens Act details added — A1.1 language level, 3-6mo job-search grace period, permit extended to 3yr, Blue Card to 4yr. Source: stampednomad.com.
- New (2):
  - estonia.md: e-Residency fee €165 fixed from Jan 1, 2027. Source: e-resident.gov.ee.
  - estonia.md: e-Residency record growth — 8/10 companies by recent joiners. Source: biometricupdate.com.
- Unchanged (6): armenia (×2), cyprus (×2), georgia (×2) — all already in DB.
- Discovery: 36 countries seen, 2 not in regions.yaml: china, india.
- Alert written: alerts/2026-09-28.md

## [2026-10-12] update | Weekly monitor (v5 two-tier) — 163 screened → 34 flagged → 3 analyzed → 2 pages updated
- Screening: 163 registry countries screened in 9 batches; 34 flagged needs_update (20.9%), 129 no_change stamped.
- Deep collection: 34 flagged countries → 618 raw items (102 with full-text extract); 10 watchlist countries passed to analyzer.
- Analyzer (deepseek-v4-pro): 3 items from 3 countries (armenia, greece, uae). Validated OK.
- Changed (2):
  - greece.md: Golden Visa demand shift Jan–Aug 2026 — applications −44% YoY, issued permits +10%, foreign property investment >€1B H1 2026. Source: agentnews.gr.
  - uae.md: Dubai extended 10-year Golden Visas to outstanding private-school teachers (World Teachers' Day, ~835 applications since Oct 2024 launch); added educators to Exceptional Talent conditions. Source: iranianuae.ae.
- Unchanged (1): armenia.md — Nov 1, 2026 reform (quotas, financial thresholds, online submission) already in DB from prior week; anti-duplicate, no edit.
- Discovery: 37 countries seen, 0 new (all in registry).
- Alert written: alerts/2026-10-12.md
## [2026-10-19] update | Weekly monitor — 17 countries updated
- Screened 163 countries (v5 two-tier); 50 flagged, 113 no_change stamped
- Analyzer: 24 news items across 17 countries (deepseek-v4-pro)
- Updated: argentina, australia, belgium, canada, china, ecuador, gambia, greece, japan, latvia, new-zealand, singapore, sweden, thailand, tonga, united-kingdom, vanuatu
- Types: 4 suspension, 1 new_program, 4 processing_update, 13 rule_change, 1 fee_change
- Alert: alerts/2026-10-19.md
## [2026-10-26] update | Weekly monitor — 15 countries updated
- Screened 163 countries (v5 two-tier); 41 flagged, 122 no_change stamped
- Analyzer: 24 news items across 16 countries (deepseek-v4-pro)
- Updated: albania, antigua, argentina, armenia, belarus, iceland, india, ireland, japan, kazakhstan, latvia, portugal, singapore, sweden, united-kingdom
- Types: 2 new_program, 14 rule_change, 2 processing_update, 6 rumor
- Alert: alerts/2026-10-26.md

