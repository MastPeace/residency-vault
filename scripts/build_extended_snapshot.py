#!/usr/bin/env python3
"""Merge World Bank indicators (fetch_indicators.py JSON) + soft-field JSON(s) into
'## Extended Snapshot' on conditions/<slug>.md (inserted before '## Country Card').
Usage: build_extended_snapshot.py --ind ind.json --soft a.json [--soft b.json] [slug ...] [--dry]
Idempotent: replaces existing Extended Snapshot block. Does NOT touch `updated`; sets `extended_snapshot: <date>` in frontmatter."""
import json, re, sys, pathlib, datetime
WIKI = pathlib.Path('/home/vovka/wiki/conditions')
def fmt(n, d=1):
    return f'{n:,.{d}f}'.replace(',', ' ') if isinstance(n, float) else f'{n:,}'.replace(',', ' ')
def big(n):
    for u, s in ((1e12, 'T'), (1e9, 'B'), (1e6, 'M')):
        if abs(n) >= u: return f'${n/u:.1f}{s}'
    return f'${n:,.0f}'
# (label, key, formatter) per block; WB-sourced rows
WB = {
 'Geography & size': [('Area', 'area_km2', lambda v: fmt(float(v), 0) + ' km²'), ('Population density', 'density', lambda v: fmt(v, 0) + ' /km²'), ('Urban population', 'urban_pct', lambda v: f'{v:.0f}%')],
 'Economy': [('GDP (nominal)', 'gdp_usd', big), ('GDP growth', 'gdp_growth', lambda v: f'{v:.1f}%'), ('Inflation (CPI)', 'inflation', lambda v: f'{v:.1f}%'), ('Unemployment', 'unemployment', lambda v: f'{v:.1f}%'), ('Central govt debt', 'debt_gdp', lambda v: f'{v:.0f}% of GDP'), ('Gini index', 'gini', lambda v: f'{v:.1f}'), ('Tourism receipts', 'tourism_gdp', lambda v: f'{v:.0f}% of exports'), ('Remittances', 'remit_gdp', lambda v: f'{v:.1f}% of GDP')],
 'Technology': [('Internet users', 'internet_pct', lambda v: f'{v:.0f}% of population'), ('Fixed broadband subs', 'broadband_100', lambda v: f'{v:.1f} per 100 people'), ('High-tech exports', 'high_tech_exp', lambda v: f'{v:.1f}% of manufactured exports'), ('R&D spend', 'rd_gdp', lambda v: f'{v:.2f}% of GDP')],
 'Human development & health': [('Life expectancy', 'life_exp', lambda v: f'{v:.1f} years'), ('Hospital beds', 'hospital_beds', lambda v: f'{v:.1f} per 1000')],
 'Climate': [('Avg precipitation', 'precip_mm', lambda v: f'{v:.0f} mm/yr'), ('PM2.5 exposure', 'pm25', lambda v: f'{v:.1f} µg/m³')],
}
SOFT = {
 'Geography & size': [('Coastline', 'coastline_km'), ('Highest point', 'highest_point'), ('Type', 'country_type'), ('Time zone', 'timezone')],
 'Climate': [('Climate zone', 'koppen_zone'), ('Temp winter / summer', 'temp_winter_summer'), ('Rainy days', 'rainy_days'), ('Humidity', 'humidity'), ('Natural hazards', 'natural_hazards'), ('Verdict', 'climate_verdict'), ('Air quality', 'air_quality')],
 'Economy': [('Credit rating', 'credit_rating'), ('Currency', 'currency'), ('Top industries', 'top_industries'), ('Dependence', 'economy_dependence'), ('Economic Complexity', 'economic_complexity')],
 'Technology': [('Global Innovation Index', 'gii_rank'), ('E-Government (UN EGDI)', 'egdi'), ('Median broadband speed', 'internet_speed'), ('5G', 'mobile_5g'), ('Online payments', 'online_payments'), ('Startup ecosystem', 'startup_ecosystem')],
 'Human development & health': [('HDI', 'hdi'), ('Healthcare quality', 'health_quality'), ('Health insurance', 'health_insurance'), ('Medical note', 'medical_note')],
 'Safety': [('Global Peace Index', 'gpi_rank'), ('US travel advisory', 'travel_advisory'), ('Crime level', 'crime_level')],
 'Money & tax': [('Non-resident bank account', 'nonresident_bank'), ('Banks & Russian clients', 'russian_clients_banking'), ('FATF status', 'fatf_status'), ('CRS exchange', 'crs_participant'), ('Tax treaty with Russia', 'tax_treaty_russia'), ('Wealth / inheritance / CGT', 'wealth_inheritance_tax'), ('CFC rules', 'cfc_rules')],
 'Business': [('Company setup', 'company_setup'), ('Corporate tax', 'corporate_tax')],
 'Family & education': [('International schools', 'intl_schools'), ('Top university', 'top_university')],
 'Connectivity': [('Flights (RU / EU)', 'flights_russia_eu'), ('Visa-free for Russians', 'visa_free_russians')],
 'For Russian citizens': [('Sanctions position', 'sanctions_status'), ('Applications from RU citizens', 'accepts_russian_applicants')],
 'Policy dynamics': [('Direction (12 mo)', 'policy_trend'), ('Upcoming changes', 'upcoming_changes')],
 'Quality of life': [('World Happiness rank', 'happiness'), ('Expat friendliness', 'expat_friendliness'), ('Local language need', 'local_language_need')],
}
ORDER = ['Geography & size', 'Climate', 'Economy', 'Technology', 'Human development & health', 'Safety', 'Money & tax', 'Business', 'Family & education', 'Connectivity', 'For Russian citizens', 'Policy dynamics', 'Quality of life']
HARD_DOM = ('.gov', '.gob.', '.gouv.', '.int', 'worldbank.org', 'imf.org', 'un.org', 'undp.org', 'hdr.undp', 'wipo.int', 'fatf-gafi.org', 'oecd.org', 'visionofhumanity.org', 'worldhappiness.report', 'freedomhouse.org', 'travel.state.gov', 'henleyglobal.com', 'atlas.cid.harvard.edu', 'oec.world', 'who.int', 'speedtest.net', 'ookla.com', 'moodys.com', 'spglobal.com', 'fitchratings.com', 'topuniversities.com', 'ef.com', 'startupblink.com', 'inform-index.org', 'worldriskindex.org', 'nalog.gov.ru', 'minfin.gov.ru', 'cbr.ru', 'europa.eu', 'cbiu.gov.dm')
def flatten(d):
    """Accept {slug:{key:{..}}} or {slug:{BLOCK:{key:{..}}}}; enforce hard only for official domains."""
    out = {}
    for slug, v in d.items():
        flat = {}
        for k, x in (v or {}).items():
            if isinstance(x, dict) and 'v' not in x and k.isupper():
                flat.update({kk: xx for kk, xx in x.items()})
            else: flat[k] = x
        for k, x in flat.items():
            if isinstance(x, dict):
                src = (x.get('src') or '').lower()
                if not src.startswith('http'): x['q'] = 'unsourced'
                elif x.get('q') == 'hard' and not any(h in src for h in HARD_DOM): x['q'] = 'soft'
        out[slug] = flat
    return out
def esc(s): return str(s).replace('|', '\\|').replace('\n', ' ').strip()
def render(slug, ind, soft):
    rows = []; filled = total = 0
    for blk in ORDER:
        for label, key, f in WB.get(blk, []):
            total += 1; x = (ind or {}).get('data', {}).get(key)
            if x and 'value' in x:
                filled += 1; rows.append((blk, label, f(x['value']) + f" ({x['year']})", f"[World Bank]({x['url']}) — hard/official"))
            else: rows.append((blk, label, 'No reliable data', '—'))
        for label, key in SOFT.get(blk, []):
            total += 1; x = (soft or {}).get(key)
            if isinstance(x, dict) and x.get('v'):
                filled += 1; src = x.get('src'); q = {'hard': 'hard/official', 'unsourced': 'unsourced/unverified'}.get(x.get('q'), 'soft/estimate')
                rows.append((blk, label, esc(x['v']), (f'[source]({src}) — {q}' if src else q)))
            else: rows.append((blk, label, 'No reliable data', '—'))
    out = ['## Extended Snapshot', '', f'_Coverage: {filled}/{total} fields. Static indicators refreshed quarterly; policy/Russia fields refreshed by the weekly monitor._', '', '| Block | Field | Value | Source / Confidence |', '|---|---|---|---|']
    for b, l, v, s in rows: out.append(f'| {b} | {l} | {v} | {s} |')
    return '\n'.join(out) + '\n', filled, total
def apply(slug, ind, soft, dry=False):
    p = WIKI / f'{slug}.md'; t = p.read_text()
    block, filled, total = render(slug, ind, soft)
    t = re.sub(r'## Extended Snapshot\n.*?(?=\n## )', '', t, flags=re.S)
    if '\n## Country Card' not in t: raise SystemExit(f'{slug}: no Country Card anchor')
    t = t.replace('\n## Country Card', '\n' + block + '\n## Country Card', 1)
    today = datetime.date.today().isoformat()
    if re.search(r'^extended_snapshot:', t, re.M): t = re.sub(r'^extended_snapshot:.*$', f'extended_snapshot: {today}', t, count=1, flags=re.M)
    else: t = re.sub(r'^(last_checked:.*|updated:.*)$', lambda m: m.group(0) + f'\nextended_snapshot: {today}', t, count=1, flags=re.M)
    if not dry: p.write_text(t)
    return filled, total
if __name__ == '__main__':
    a = sys.argv[1:]; ind = {}; soft = {}; dry = '--dry' in a; slugs = []
    i = 0
    while i < len(a):
        if a[i] == '--ind': ind = json.load(open(a[i+1])); i += 2
        elif a[i] == '--soft': soft.update(flatten(json.load(open(a[i+1])))); i += 2
        elif a[i] == '--dry': i += 1
        else: slugs.append(a[i]); i += 1
    for s in slugs or list(ind):
        f, t = apply(s, ind.get(s), soft.get(s), dry); print(f'{s}: {f}/{t}')
