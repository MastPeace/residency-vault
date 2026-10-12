#!/usr/bin/env python3
"""Rewrite shorthand numbers as digits in wiki pages (idempotent).

  €250K -> €250,000   USD 1.5M -> USD 1,500,000   €250K–500K -> €250,000–500,000
  five years -> 5 years, ten-year -> 10-year

Only currency-prefixed amounts are touched (a bare '47M' is a population, not money).
Usage: normalize_numbers.py [--dry-run]
"""
import re, sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CUR = r'(?:US)?[€$£¥]|\b(?:[A-Z]{3}|BD)\b'
AMT = re.compile(r'(?P<cur>%s)(?P<sp>\s?)(?P<a>\d[\d,]*(?:\.\d+)?)\s?(?P<ak>[KkMm])\b'
                 r'(?:(?P<sep>\s?[–-]\s?)(?P<b>\d[\d,]*(?:\.\d+)?)\s?(?P<bk>[KkMm])\b)?' % CUR)
RANGE = re.compile(r'(?P<cur>%s)(?P<sp>\s?)(?P<a>\d{1,3})(?P<sep>\s?[–-]\s?)(?P<b>\d[\d,]*(?:\.\d+)?)\s?(?P<k>[KkMm])\b' % CUR)
WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
WORD_RE = re.compile(r'\b(%s)([- ])(years?|months?|days?)\b' % "|".join(w for w in WORDS if w != "zero"), re.I)


def expand(num, k):
    v = Decimal(num.replace(",", "")) * (1000 if k.lower() == "k" else 1_000_000)
    return f"{int(v):,}"


def amt_sub(m):
    out = f'{m["cur"]}{m["sp"]}{expand(m["a"], m["ak"])}'
    if m["b"]:
        out += f'{m["sep"]}{expand(m["b"], m["bk"])}'
    return out


def range_sub(m):
    return f'{m["cur"]}{m["sp"]}{expand(m["a"], m["k"])}{m["sep"]}{expand(m["b"], m["k"])}'


def convert(text):
    out, in_fm = [], False
    for i, line in enumerate(text.split("\n")):
        if i == 0 and line.strip() == "---":
            in_fm = True
            out.append(line); continue
        if in_fm:
            if line.strip() == "---":
                in_fm = False
            out.append(line); continue
        if "http" in line:  # leave lines carrying URLs untouched
            parts = re.split(r'(\S*https?://\S*)', line)
            parts = [p if p.startswith(("http",)) or "http" in p else RANGE.sub(range_sub, AMT.sub(amt_sub, p)) for p in parts]
            line = "".join(parts)
        else:
            line = RANGE.sub(range_sub, AMT.sub(amt_sub, line))
        line = WORD_RE.sub(lambda m: WORDS[m[1].lower()] + m[2] + m[3], line)
        out.append(line)
    return "\n".join(out)


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    changed = 0
    for f in sorted(list((ROOT / "conditions").glob("*.md")) + list((ROOT / "concepts").glob("*.md"))):
        t = f.read_text(encoding="utf-8")
        n = convert(t)
        if n != t:
            changed += 1
            if not dry:
                f.write_text(n, encoding="utf-8")
    print(f"{'would change' if dry else 'changed'} {changed} files")
