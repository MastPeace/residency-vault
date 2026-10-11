#!/usr/bin/env python3
"""Extended Snapshot batch driver (cron-safe, self-terminating).
  extended_batch.py prepare [N=6]   -> picks next N countries (missing snapshot first, then stalest >90d),
                                       runs World Bank fetch, creates workdir; prints JSON {workdir, slugs, names, soft_out} or {"done": true}
  extended_batch.py finalize <workdir> -> builds blocks from ind.json + soft.json, validates, commits ONLY touched
                                       condition pages (git commit --only) and pushes. Prints JSON report.
Attempt counter (state file) skips a country after 3 failed attempts."""
import json, re, sys, os, subprocess, datetime, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_extended_snapshot as B, fetch_indicators as F
WIKI = pathlib.Path('/home/vovka/wiki'); COND = WIKI / 'conditions'
SCR = pathlib.Path('/home/vovka/.hermes/cache/scratch'); STATE = SCR / 'ext_attempts.json'
TOTAL = sum(len(v) for v in B.WB.values()) + sum(len(v) for v in B.SOFT.values())
STALE_DAYS = 90; MAX_ATTEMPTS = 3; MIN_FILLED = 20
def registry():
    t = (WIKI / 'regions.yaml').read_text(); return re.findall(r'country:\s*([a-z0-9-]+)', t)
def snap_date(slug):
    m = re.search(r'^extended_snapshot:\s*(\d{4}-\d{2}-\d{2})', (COND / f'{slug}.md').read_text(), re.M)
    return datetime.date.fromisoformat(m.group(1)) if m else None
def name_of(slug):
    m = re.search(r'^title:\s*"?(.+?)\s+[—-]\s+Residency', (COND / f'{slug}.md').read_text(), re.M)
    n = m.group(1) if m else slug
    return n.replace('-', ' ').title() if n.islower() else n
def link_ok(url, cache={}):
    """False only when the page definitely does not exist (404/410/DNS). 403/Cloudflare/timeouts count as alive."""
    import urllib.request, urllib.error
    if url in cache: return cache[url]
    ok = True
    for method in ('HEAD', 'GET'):
        try:
            urllib.request.urlopen(urllib.request.Request(url, method=method, headers={'User-Agent': 'Mozilla/5.0'}), timeout=12); ok = True; break
        except urllib.error.HTTPError as e:
            if e.code in (404, 410): ok = False; 
            else: ok = True
            if method == 'GET' or e.code not in (404, 405, 403, 501): break
        except urllib.error.URLError as e:
            ok = 'Name or service' not in str(e.reason) and 'not known' not in str(e.reason); break
        except Exception: ok = True; break
    cache[url] = ok; return ok
def verify_links(soft):
    from concurrent.futures import ThreadPoolExecutor
    urls = {x['src'] for v in soft.values() for x in v.values() if isinstance(x, dict) and str(x.get('src', '')).startswith('http')}
    with ThreadPoolExecutor(8) as ex: res = dict(zip(urls, ex.map(link_ok, urls)))
    dead = 0
    for v in soft.values():
        for x in v.values():
            if isinstance(x, dict) and x.get('src') in res and not res[x['src']]: x['dead_src'] = x['src']; x['src'] = None; x['q'] = 'unsourced'; dead += 1
    return dead
def weekly_window():
    """Monday 02:30-06:00 UTC = weekly monitor run; do not touch condition pages then."""
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.weekday() == 0 and (2, 30) <= (now.hour, now.minute) < (6, 0)
def prepare(n):
    if weekly_window(): return {'done': True, 'reason': 'weekly monitor window (Mon 02:30-06:00 UTC), retry next tick'}
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = datetime.date.today(); cand = []
    for s in registry():
        if not (COND / f'{s}.md').exists() or st.get(s, 0) >= MAX_ATTEMPTS: continue
        d = snap_date(s)
        if d is None: cand.append(((0, 0), s))
        elif (today - d).days > STALE_DAYS: cand.append(((1, -(today - d).days), s))
    cand.sort(); slugs = [s for _, s in cand[:n]]
    if not slugs: return {'done': True}
    for s in slugs: st[s] = st.get(s, 0) + 1
    STATE.write_text(json.dumps(st))
    wd = SCR / f'ext_{datetime.datetime.now(datetime.timezone.utc):%Y%m%d_%H%M%S}'; wd.mkdir(parents=True)
    ind = F.main(slugs); (wd / 'ind.json').write_text(json.dumps(ind, ensure_ascii=False))
    (wd / 'slugs.json').write_text(json.dumps(slugs))
    return {'workdir': str(wd), 'slugs': slugs, 'names': {s: name_of(s) for s in slugs}, 'soft_out': str(wd / 'soft.json'), 'remaining_after': len(cand) - len(slugs)}
def finalize(wd):
    wd = pathlib.Path(wd); slugs = json.loads((wd / 'slugs.json').read_text())
    ind = json.loads((wd / 'ind.json').read_text())
    try: soft = B.flatten(json.loads((wd / 'soft.json').read_text()))
    except Exception as e: return {'error': f'soft.json unreadable: {e}', 'ok': [], 'failed': slugs}
    dead = verify_links(soft)
    ok, failed, files = [], [], []
    for s in slugs:
        sf = {k: v for k, v in (soft.get(s) or {}).items() if v and v.get('v')}
        if len(sf) < MIN_FILLED: failed.append((s, f'only {len(sf)} soft fields')); continue
        p = COND / f'{s}.md'; before = p.read_text()
        try:
            f, t = B.apply(s, ind.get(s), soft.get(s))
            txt = p.read_text(); blk = re.search(r'## Extended Snapshot\n(.*?)\n## Country Card', txt, re.S).group(1)
            rows = [l for l in blk.splitlines() if l.startswith('| ') and not l.startswith('| Block')]
            assert len(rows) == t == TOTAL and txt.startswith('---\n') and txt.count('\n---\n') >= 1 and txt.count('## Country Card') == 1
            ok.append((s, f'{f}/{t}')); files.append(f'conditions/{s}.md')
        except Exception as e:
            p.write_text(before); failed.append((s, str(e)[:80]))
    rep = {'ok': ok, 'failed': failed, 'dead_links_demoted': dead, 'pushed': False}
    if files:
        env = dict(os.environ); envf = pathlib.Path.home() / '.hermes/.env'
        tok = None
        for l in envf.read_text().splitlines():
            if l.startswith('GH_TOKEN='): tok = l.split('=', 1)[1].strip().strip('"\'')
        r = subprocess.run(['git', '-C', str(WIKI), 'commit', '-q', '-m', f'Extended Snapshot: {len(ok)} countries ({", ".join(s for s,_ in ok)})', '--only', '--'] + files, capture_output=True, text=True)
        if r.returncode: rep['git_error'] = r.stderr[-200:]
        elif tok:
            pr = subprocess.run(['git', '-C', str(WIKI), 'push', '-q', f'https://MastPeace:{tok}@github.com/MastPeace/residency-vault.git', 'HEAD:main'], capture_output=True, text=True)
            rep['pushed'] = pr.returncode == 0
            if pr.returncode: rep['git_error'] = pr.stderr.replace(tok, '***')[-200:]
    return rep
def pending():
    st = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = datetime.date.today(); n = 0
    for s in registry():
        if not (COND / f'{s}.md').exists() or st.get(s, 0) >= MAX_ATTEMPTS: continue
        d = snap_date(s)
        if d is None or (today - d).days > STALE_DAYS: n += 1
    return n
if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'pending': print(f'pending={pending()}')
    if c == 'prepare': print(json.dumps(prepare(int(sys.argv[2]) if len(sys.argv) > 2 else 6), ensure_ascii=False))
    elif c == 'finalize': print(json.dumps(finalize(sys.argv[2]), ensure_ascii=False))
