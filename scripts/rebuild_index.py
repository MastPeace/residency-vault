#!/usr/bin/env python3
"""
Rebuild /home/vovka/wiki/index.md from regions.yaml + country page Overviews.
Deterministic (no LLM): section per region group, one `- [[slug]] — <first line
of Overview>` entry per country. Concept pages section is preserved as-is.

Usage: python3 rebuild_index.py [--dry-run]
Run after adding countries/pages, before committing.
"""
import re, sys, yaml
from pathlib import Path

WIKI = Path("/home/vovka/wiki")
REGIONS = WIKI / "regions.yaml"
CONDITIONS = WIKI / "conditions"
INDEX = WIKI / "index.md"

REGION_TITLES = {
    "eu_western": "EU Western", "eu_eastern": "EU Eastern",
    "balkans_caucasus": "Balkans Caucasus", "middle_east_gulf": "Middle East Gulf",
    "middle_east_extra": "Middle East Extra", "africa_north": "Africa North",
    "africa_west": "Africa West", "africa_east_south": "Africa East South",
    "africa_cbi": "Africa CBI", "africa_extra": "Africa Extra",
    "latin_america": "Latin America", "caribbean_central": "Caribbean Central",
    "cbi_caribbean": "CBI Caribbean", "north_america_oceania": "North America Oceania",
    "asia_extra": "Asia Extra", "europe_micro": "Europe Micro",
    "south_america_extra": "South America Extra", "oceania_extra": "Oceania Extra",
}


def overview_line(slug):
    p = CONDITIONS / f"{slug}.md"
    if not p.exists():
        return ""
    text = p.read_text(errors="ignore")
    m = re.search(r"^## Overview\n\n?(.+?)(?=\n\n|\n## )", text, re.S)
    if not m:
        return ""
    line = " ".join(m.group(1).split())
    return line[:160]


def main():
    dry = "--dry-run" in sys.argv
    data = yaml.safe_load(REGIONS.read_text())
    regions = data["regions"]

    # preserve the concept pages section (everything after its heading)
    old = INDEX.read_text() if INDEX.exists() else ""
    concepts = ""
    cm = re.search(r"(^## Concept Pages.*)\Z", old, re.S)
    if cm:
        concepts = cm.group(1)

    out = ["# Wiki Index — Residency & Citizenship Conditions",
           "",
           "> Content catalog. Every wiki page listed under its type with a one-line summary.",
           "> Read this first to find relevant pages for any query.",
           f"> Rebuilt 2026-10-11 | Schema: SCHEMA.md (canonical residency-type taxonomy).",
           ""]

    total = 0
    for rl, entries in regions.items():
        title = REGION_TITLES.get(rl, rl.replace("_", " ").title())
        if not entries:
            continue
        out.append(f"## {title} ({len(entries)})\n")
        for e in entries:
            slug = e["country"]
            line = f"- [[{slug}]] — {overview_line(slug)}"
            out.append(line)
            total += 1
        out.append("")

    out.append(f"## Other\n")
    out.append("")
    if concepts:
        out.append(concepts)

    text = "\n".join(out).rstrip() + "\n"
    print(f"countries indexed: {total}")
    if dry:
        print("DRY RUN — not written")
        return
    INDEX.write_text(text)
    print(f"written: {INDEX} ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()