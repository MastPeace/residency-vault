#!/usr/bin/env python3
"""Ping IndexNow (Bing, Yandex, Seznam, Naver) with every URL from the built sitemap.
Run after deploy. The key file lives in static/<key>.txt and is public by design."""
import json, re, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "residencyradar.org"
KEY = "b1475a61a78e73366c6593194ca59211"

urls = re.findall(r"<loc>(.*?)</loc>", (ROOT / "site_output" / "sitemap.xml").read_text(encoding="utf-8"))
payload = json.dumps({"host": HOST, "key": KEY, "keyLocation": f"https://{HOST}/{KEY}.txt", "urlList": urls}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", data=payload,
                             headers={"Content-Type": "application/json; charset=utf-8"})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print(f"IndexNow: {len(urls)} urls, HTTP {r.status}")
except Exception as e:  # never fail the deploy over a ping
    print(f"IndexNow ping failed: {e}", file=sys.stderr)
