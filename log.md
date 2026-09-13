# Wiki Log

> Chronological record of all wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete

## [2026-09-13] create | Wiki initialized
- Domain: Residency & Citizenship Conditions across countries (strong passport / IT-friendly / popular for RU / yacht)
- Structure created with SCHEMA.md, index.md, log.md: conditions/, entities/, concepts/, comparisons/, queries/, raw/, scripts/
- WIKI_PATH set to /home/vovka/wiki
- Phase 1 (seed) pending: build country condition pages from collected monitor data + authoritative sources

## [2026-09-13] ingest | Seed country conditions (22 countries + concepts)

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
