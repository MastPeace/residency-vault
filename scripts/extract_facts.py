#!/usr/bin/env python3
"""Extract structured numeric facts from country pages into data/facts.json.

Facts (per country slug):
  gv_min      headline minimum amount of the investment-residency route (amount, currency, note)
  remote_visa remote-work / digital-nomad residence (available yes/no, min income, period)
  remote_tax  effective personal tax range for remote workers (low_pct, high_pct)
Every fact carries an `evidence` quote that must literally occur in the page text and contain the
extracted number(s); facts failing that check are dropped (value = null). Idempotent: only pages
whose relevant text changed since the last run are re-extracted (use --all to force).

Model: deepseek/deepseek-v4-pro through OpenRouter (key from ~/.hermes/.env).
Usage: extract_facts.py [--all] [--only slug,slug]
"""
import hashlib, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "facts.json"
MODEL = "deepseek/deepseek-v4-pro"

PROMPT = """You extract structured facts from a country page of a residency/citizenship database.
Use ONLY the text provided. If a fact is not stated, return null for it. Never guess or convert currencies.

Return one JSON object:
{
 "gv_min": null | {"amount": <number, digits only>, "currency": "<ISO code as in the text, e.g. EUR, USD, AED>", "note": "<=8 words, e.g. 'real estate' or 'conversion tier'", "evidence": "<exact quote from the text containing the amount>"},
 "remote_visa": null | {"available": true|false, "min_income": <number or null>, "currency": "<ISO or null>", "period": "month"|"year"|null, "evidence": "<exact quote>"},
 "remote_tax": null | {"low_pct": <number>, "high_pct": <number>, "evidence": "<exact quote>"}
}
Rules:
- gv_min: the CHEAPEST qualifying amount of the investment-residency route (Golden Visa / investor residence permit): property, fund, business or deposit. Not fees, not citizenship-by-investment, not net-worth requirements. Null if the route is closed, absent or has no stated amount. Amount as a plain number (250000).
- remote_visa: a digital-nomad / remote-work / freelancer residence permit. available=false only if the text says there is none. min_income is the headline income requirement.
- remote_tax: the effective personal income tax range for a remote worker (low and high %; if a single flat rate, low=high). Null if not stated.
- evidence must be copied verbatim from the text."""


def load_key():
    for ln in (Path.home() / ".hermes" / ".env").read_text().splitlines():
        if ln.startswith("OPENROUTER_API_KEY="):
            return ln.split("=", 1)[1].strip().strip('"')
    sys.exit("OPENROUTER_API_KEY not found")


def relevant_text(text):
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.S)
    parts = []
    for head in ("Residency Programs", "Tax"):
        m = re.search(r"^## %s\s*\n(.*?)(?=^## |\Z)" % head, body, re.S | re.M)
        if m:
            parts.append(f"## {head}\n{m.group(1).strip()}")
    snap = [l for l in body.split("\n") if re.search(r"Remote-work|Effective personal tax", l)]
    if snap:
        parts.append("## Snapshot rows\n" + "\n".join(snap))
    return "\n\n".join(parts)[:9000]


def norm(s):
    return re.sub(r"\s+", " ", s.replace("\u00a0", " ")).strip().lower()


def num_in(evidence, n):
    digits = {f"{int(n):,}", str(int(n)), f"{n:g}"}
    ev = evidence.replace(" ", "")
    return any(d in ev for d in digits)


def validate(facts, src):
    s = norm(src)
    out = {}
    for key, v in (facts or {}).items():
        if not isinstance(v, dict):
            out[key] = None
            continue
        ev = v.get("evidence") or ""
        ok = bool(ev) and norm(ev) in s
        if ok and key == "gv_min":
            ok = isinstance(v.get("amount"), (int, float)) and num_in(ev, v["amount"])
        if ok and key == "remote_visa" and v.get("min_income") is not None:
            ok = num_in(ev, v["min_income"])
        if ok and key == "remote_tax":
            ok = all(isinstance(v.get(k), (int, float)) and num_in(ev, v[k]) for k in ("low_pct", "high_pct"))
        out[key] = v if ok else None
    for k in ("gv_min", "remote_visa", "remote_tax"):
        out.setdefault(k, None)
    return out


def call(key, text):
    body = json.dumps({"model": MODEL, "temperature": 0, "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": PROMPT}, {"role": "user", "content": text}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                msg = json.loads(r.read())["choices"][0]["message"]["content"]
            return json.loads(re.sub(r"^```(?:json)?|```$", "", msg.strip(), flags=re.M).strip())
        except Exception as e:
            err = e
            time.sleep(3 * (attempt + 1))
    raise err


def main():
    force = "--all" in sys.argv
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    key = load_key()
    db = json.loads(OUT.read_text()) if OUT.exists() else {}
    todo = []
    for f in sorted((ROOT / "conditions").glob("*.md")):
        slug = f.stem
        if only and slug not in only:
            continue
        rel = relevant_text(f.read_text(encoding="utf-8"))
        h = hashlib.sha256(rel.encode()).hexdigest()[:16]
        if force or only or db.get(slug, {}).get("hash") != h:
            todo.append((slug, rel, h))
    print(f"{len(todo)} pages to extract")

    def work(item):
        slug, rel, h = item
        try:
            facts = validate(call(key, rel), rel)
            return slug, {"hash": h, "extracted": time.strftime("%Y-%m-%d"), **facts}, None
        except Exception as e:
            return slug, None, str(e)[:120]

    errs = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        for slug, rec, err in ex.map(work, todo):
            if rec:
                db[slug] = rec
            else:
                errs += 1
                print("ERR", slug, err)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(dict(sorted(db.items())), ensure_ascii=False, indent=1))
    print(f"done: {len(db)} in db, {errs} errors")


if __name__ == "__main__":
    main()
