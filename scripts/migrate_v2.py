#!/usr/bin/env python3
"""Migrate a legacy (v1) country page to SCHEMA v2 using deepseek/deepseek-v4-pro via OpenRouter.
The LLM rewrites ONLY: Residency Programs table, Per-Program Detail, Community Pulse (from facts already on the page;
no new facts). All other sections (snapshot tables, country card, status, citizenship, tax...) are kept verbatim.
usage: migrate_v2.py <slug> [<slug>...]"""
import json, re, sys, urllib.request
from pathlib import Path
W = Path(__file__).resolve().parent.parent
MODEL = "deepseek/deepseek-v4-pro"
TYPES = "investment_residency passive_income_residency digital_nomad_visa highly_skilled_employment startup_entrepreneur employment_residency student_residency family_reunification retired_residency citizenship_by_investment".split()

def key():
    for l in (Path.home() / ".hermes/.env").read_text().splitlines():
        if l.startswith("OPENROUTER_API_KEY="): return l.split("=", 1)[1].strip().strip('"')
    sys.exit("no key")

PROMPT = """You convert a legacy country page into the v2 residency-vault format. Use ONLY facts present in the page below; never add new facts, numbers or URLs. Keep every fact, number and ^[url] provenance marker that belongs to residence programs. Write in English.

Produce EXACTLY three markdown blocks, in this order, with these headings and nothing else:

## Residency Programs
A table with header `| Type | Official Program | Key Conditions | Duration | Detail |` and EXACTLY these 10 rows in this order (first column is the type slug): %(types)s.
If a type is not offered or the page has no data: `| slug | Not available | — | — | — |`.
For existing programs the Detail column is `[[#slug]]` (the SAME slug as the first column, with underscores) and a matching `### slug` subsection MUST exist below.

## Per-Program Detail
For each type that exists, a `### slug` subsection (slug exactly as in the table, underscores) with bullets:
- **Official name**: ...
- **Conditions**: ... (keep ^[url] markers)
- **Duration / renewal**: ...
- **Path to citizenship**: ...
- **Official source**: URL (only one already on the page, else `see sources in frontmatter`)
- **Community verdict**: Works well / Mixed / Problematic (+short reason) -- only if the page supports it, else `Not yet assessed`.

## Community Pulse
2-4 sentences summarising only what the page says about real-world experience/friction; if nothing, write `Not yet researched.`

Do not wrap the output in code fences.

PAGE (%(slug)s):
%(page)s
"""

def call(prompt):
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({"model": MODEL, "temperature": 0.1, "max_tokens": 12000,
                         "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"Authorization": "Bearer " + key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=280) as r:
        return json.load(r)["choices"][0]["message"]["content"].strip()

def sections(body):
    parts = re.split(r"^(?=## )", body, flags=re.M)
    d = {}
    for p in parts:
        m = re.match(r"## (.+)", p)
        if m: d[m.group(1).strip().lower()] = p.rstrip() + "\n"
    return d

def migrate(slug):
    f = W / "conditions" / f"{slug}.md"
    t = f.read_text()
    m = re.match(r"(---\n.*?\n---\n)(.*)", t, re.S)
    fm, body = m.group(1), m.group(2)
    if "## Residency Programs" in body:
        print(slug, "already v2"); return
    secs = sections(body)
    out = call(PROMPT % {"types": ", ".join(TYPES), "slug": slug, "page": t})
    out = re.sub(r"^```\w*\n|\n```$", "", out.strip())
    new = sections(out)
    for need in ("residency programs", "per-program detail", "community pulse"):
        assert need in new, f"{slug}: LLM output missing {need}"
    rows = [l for l in new["residency programs"].split("\n") if l.startswith("| ") and not l.startswith("| Type") ]
    got = [r.split("|")[1].strip() for r in rows]
    assert got == TYPES, f"{slug}: rows {got}"
    order = ["overview", "residency programs", "per-program detail", "citizenship", "tax", "it / digital nomad",
             "yacht / maritime", "notes for ru citizens", "community pulse", "country snapshot", "extended snapshot",
             "country card", "status"]
    pool = {**secs, **new}
    missing = [k for k in secs if k not in order and k != "residence"]
    assert not missing, f"{slug}: unplaced sections {missing}"
    fm = re.sub(r"^title:.*$", lambda mm: mm.group(0) if "Residency" in mm.group(0) else f"title: {slug.replace('-', ' ').title()} — Residency & Citizenship Conditions", fm, count=1, flags=re.M)
    res = fm + "\n" + "\n".join(pool[k].rstrip() + "\n" for k in order if k in pool)
    f.write_text(res)
    print(slug, "migrated", len(t), "->", len(res))

if __name__ == "__main__":
    for s in sys.argv[1:]: migrate(s)
