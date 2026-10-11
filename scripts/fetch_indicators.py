#!/usr/bin/env python3
"""Fetch static country indicators from World Bank API (stdlib only, no LLM).
Usage: fetch_indicators.py portugal georgia ...  -> JSON to stdout / --out file
Uses country_code from wiki/conditions/<slug>.md frontmatter (ISO2)."""
import json, re, sys, urllib.request, pathlib
from concurrent.futures import ThreadPoolExecutor
WIKI = pathlib.Path('/home/vovka/wiki/conditions')
IND = {
 'area_km2': ('AG.SRF.TOTL.K2', 'Land+water area, km²'),
 'density': ('EN.POP.DNST', 'Population density, per km²'),
 'urban_pct': ('SP.URB.TOTL.IN.ZS', 'Urban population, %'),
 'gdp_usd': ('NY.GDP.MKTP.CD', 'GDP nominal, US$'),
 'gdp_growth': ('NY.GDP.MKTP.KD.ZG', 'GDP growth, % y/y'),
 'inflation': ('FP.CPI.TOTL.ZG', 'Inflation CPI, % y/y'),
 'unemployment': ('SL.UEM.TOTL.ZS', 'Unemployment, %'),
 'debt_gdp': ('GC.DOD.TOTL.GD.ZS', 'Central govt debt, % GDP'),
 'gini': ('SI.POV.GINI', 'Gini index'),
 'internet_pct': ('IT.NET.USER.ZS', 'Internet users, % pop'),
 'broadband_100': ('IT.NET.BBND.P2', 'Fixed broadband subs per 100'),
 'life_exp': ('SP.DYN.LE00.IN', 'Life expectancy, years'),
 'precip_mm': ('AG.LND.PRCP.MM', 'Avg precipitation, mm/yr'),
 'pm25': ('EN.ATM.PM25.MC.M3', 'PM2.5 mean exposure, µg/m³'),
 'tourism_gdp': ('ST.INT.RCPT.XP.ZS', 'Tourism receipts, % of exports'),
 'remit_gdp': ('BX.TRF.PWKR.DT.GD.ZS', 'Remittances, % GDP'),
 'hospital_beds': ('SH.MED.BEDS.ZS', 'Hospital beds per 1000'),
 'uhc_index': ('SH.UHC.SRVS.CV.XD', 'UHC service coverage index'),
 'high_tech_exp': ('TX.VAL.TECH.MF.ZS', 'High-tech exports, % of manuf. exports'),
 'rd_gdp': ('GB.XPD.RSDV.GD.ZS', 'R&D spend, % GDP'),
}
def get(iso, code):
    url=f'https://api.worldbank.org/v2/country/{iso}/indicator/{code}?format=json&mrnev=1'
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}), timeout=12) as r: d=json.load(r)
        rec=d[1][0] if len(d)>1 and d[1] else None
        if rec and rec['value'] is not None:
            return {'value':rec['value'],'year':rec['date'],'url':f'https://data.worldbank.org/indicator/{code}?locations={iso}'}
    except Exception as e: return {'error':str(e)[:80]}
    return None
def iso_of(slug):
    m=re.search(r'^country_code:\s*"?([A-Za-z]{2})"?', (WIKI/f'{slug}.md').read_text(), re.M)
    return m.group(1).upper() if m else None
def main(slugs):
    out={}
    for s in slugs:
        iso=iso_of(s); out[s]={'iso':iso,'data':{}}
        if not iso: continue
        with ThreadPoolExecutor(4) as ex:
            res=dict(zip(IND, ex.map(lambda kv: get(iso,kv[0]), [(c,) for c,_ in IND.values()])))
        out[s]['data']=res
    return out
if __name__=='__main__':
    a=sys.argv[1:]; outp=None
    if '--out' in a: i=a.index('--out'); outp=a[i+1]; a=a[:i]+a[i+2:]
    r=main(a); s=json.dumps(r,ensure_ascii=False,indent=1)
    (open(outp,'w').write(s) if outp else print(s))
