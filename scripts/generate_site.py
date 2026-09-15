#!/usr/bin/env python3
"""
Static-site generator for the Residency & Citizenship Conditions Wiki.
Converts conditions/*.md + concepts/*.md into a dark-themed Wikipedia-style HTML site.
Pure Python 3 stdlib — no external dependencies.
"""

import os
import re
import sys
import html
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from collections import OrderedDict

# ── Configuration ────────────────────────────────────────────────────────────

WIKI_DIR = Path(__file__).resolve().parent.parent  # /home/vovka/wiki
OUTPUT_DIR = WIKI_DIR / "site_output"
CONDITIONS_DIR = WIKI_DIR / "conditions"
CONCEPTS_DIR = WIKI_DIR / "concepts"
REGIONS_FILE = WIKI_DIR / "regions.yaml"
INDEX_FILE = WIKI_DIR / "index.md"
SITE_TITLE = "Residency & Citizenship Wiki"
SITE_SUBTITLE = "Cross-country living conditions for every kind of residency program"

# ── YAML Frontmatter Parser (minimal, stdlib) ────────────────────────────────

def parse_frontmatter(text):
    """Parse YAML frontmatter (--- ... ---) at start of text.
    Returns (metadata_dict, body_text). Supports simple scalars and lists."""
    if not text.startswith("---\n"):
        return {}, text
    idx = text.find("\n---\n", 4)
    if idx == -1:
        # Try closing with --- at end of line
        idx = text.find("\n---", 4)
        if idx == -1:
            return {}, text
    fm_text = text[4:idx]
    body = text[idx + 4:].lstrip("\n")
    meta = {}
    current_key = None
    current_list = None
    
    for line in fm_text.split("\n"):
        # List continuation
        if line.startswith("  - ") and current_key:
            val = line[4:].strip().strip("'\"")
            meta.setdefault(current_key, []).append(val)
            continue
        # Simple key: value
        m = re.match(r'^(\w[\w_-]*)\s*:\s*(.*)', line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                # Inline list: [a, b, c]
                items = val[1:-1].split(",")
                meta[key] = [it.strip().strip("'\"") for it in items if it.strip()]
            elif val == "":
                current_key = key
            else:
                meta[key] = val.strip("'\"")
                current_key = key if val == "" else None
    return meta, body


# ── Markdown to HTML Converter ───────────────────────────────────────────────

def md_to_html(body, page_type="entity", current_slug=""):
    """
    Convert markdown body to HTML. Handles:
    - Tables (| ... |)
    - Headings (##, ###)
    - Bold (**text**), italic (*text*)
    - Inline code (`code`)
    - Fenced code blocks
    - Links [text](url)
    - Wikilinks [[target]] and [[target|label]]
    - Unordered/ordered lists
    - Provenance footnotes ^[...]
    - Horizontal rules
    """
    lines = body.split("\n")
    out_lines = []
    i = 0
    n = len(lines)
    
    # Collect footnote definitions
    footnotes = []
    fn_counter = [0]
    
    def process_inline(text):
        """Process inline formatting within a line."""
        # Collect ^[...] footnotes first
        def replace_fn(m):
            fn_counter[0] += 1
            fn_text = m.group(1)
            footnotes.append((fn_counter[0], fn_text))
            return f'<sup class="footnote-ref"><a href="#fn{fn_counter[0]}" id="fnref{fn_counter[0]}">[{fn_counter[0]}]</a></sup>'
        text = re.sub(r'\^\[([^\]]*)\]', replace_fn, text)
        
        # Wikilinks: [[target]], [[target|label]], [[#anchor]]
        def replace_wikilink(m):
            target = m.group(1)
            label = m.group(2) if m.group(2) else target
            # Fragment-only link: [[#section-name]]
            if target.startswith("#"):
                return f'<a href="{html.escape(target)}" class="wikilink">{html.escape(label)}</a>'
            # Determine if concept or condition
            slug = target.lower().replace(" ", "-")
            # Handle fragment in target: target#anchor
            fragment = ""
            if "#" in slug:
                slug, fragment = slug.rsplit("#", 1)
                fragment = "#" + fragment
            if "/" in slug:
                href = slug + ".html"
            elif slug in CONCEPT_SLUGS:
                href = f"concepts/{slug}.html"
            else:
                href = f"conditions/{slug}.html"
            return f'<a href="/{href}{fragment}" class="wikilink">{html.escape(label)}</a>'
        text = re.sub(r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]', replace_wikilink, text)
        
        # Regular markdown links [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', text)
        
        # Inline code
        text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
        
        return text
    
    def escape_table_cell(cell):
        """Escape & < > but preserve already-escaped entities."""
        cell = cell.strip()
        # Don't double-escape
        cell = cell.replace("&amp;", "&AMP;")
        cell = cell.replace("&lt;", "&LT;")
        cell = cell.replace("&gt;", "&GT;")
        cell = html.escape(cell)
        cell = cell.replace("&AMP;", "&amp;")
        cell = cell.replace("&LT;", "&lt;")
        cell = cell.replace("&GT;", "&gt;")
        return cell
    
    in_code_block = False
    code_lines = []
    in_list = None  # 'ul' or 'ol'
    in_table = False
    table_rows = []
    
    while i < n:
        line = lines[i]
        
        # Code block fence
        if line.strip().startswith("```"):
            if in_code_block:
                out_lines.append(f'<pre><code>{"".join(code_lines)}</code></pre>')
                code_lines = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue
        
        if in_code_block:
            code_lines.append(html.escape(line) + "\n")
            i += 1
            continue
        
        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            out_lines.append("<hr>")
            i += 1
            continue
        
        # Table detection: line contains | and next line is separator
        if "|" in line and i + 1 < n:
            next_line = lines[i + 1].strip()
            if re.match(r'^\|?[\s:-]+\|[\s|:-]+\|?$', next_line):
                if not in_table:
                    # Start table: this is header
                    header_cells = [c.strip() for c in line.strip().strip("|").split("|")]
                    # Check alignment from separator
                    sep_cells = [c.strip() for c in next_line.strip().strip("|").split("|")]
                    aligns = []
                    for sc in sep_cells:
                        if sc.startswith(":") and sc.endswith(":"):
                            aligns.append("center")
                        elif sc.endswith(":"):
                            aligns.append("right")
                        else:
                            aligns.append("left")
                    
                    out_lines.append('<div class="table-wrapper"><table>')
                    out_lines.append("<thead><tr>")
                    for idx, cell in enumerate(header_cells):
                        al = f' style="text-align:{aligns[idx]}"' if idx < len(aligns) else ""
                        out_lines.append(f'<th{al}>{process_inline(escape_table_cell(cell))}</th>')
                    out_lines.append("</tr></thead><tbody>")
                    in_table = True
                    i += 2
                    continue
                else:
                    # Already in table, this line is a row
                    pass
        
        # Table row (already in table)
        if in_table and "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out_lines.append("<tr>")
            for cell in cells:
                out_lines.append(f'<td>{process_inline(escape_table_cell(cell))}</td>')
            out_lines.append("</tr>")
            i += 1
            continue
        
        # Close table if we were in one and hit non-table line
        if in_table:
            out_lines.append("</tbody></table></div>")
            in_table = False
        
        # Headings
        m = re.match(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', line)
        if m:
            level = len(m.group(1))
            text = process_inline(m.group(2))
            # Generate anchor ID from heading text
            anchor = re.sub(r'[^\w\s-]', '', m.group(2)).strip().lower()
            anchor = re.sub(r'[\s]+', '-', anchor)
            out_lines.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            i += 1
            continue
        
        # Unordered list
        m_ul = re.match(r'^(\s*)[-*+]\s+(.+)', line)
        if m_ul:
            indent = len(m_ul.group(1))
            text = process_inline(m_ul.group(2))
            if in_list != ('ul', indent):
                if in_list:
                    out_lines.append(f"</{in_list[0]}>")
                out_lines.append("<ul>")
                in_list = ('ul', indent)
            out_lines.append(f"<li>{text}</li>")
            i += 1
            continue
        
        # Ordered list
        m_ol = re.match(r'^(\s*)\d+\.\s+(.+)', line)
        if m_ol:
            indent = len(m_ol.group(1))
            text = process_inline(m_ol.group(2))
            if in_list != ('ol', indent):
                if in_list:
                    out_lines.append(f"</{in_list[0]}>")
                out_lines.append("<ol>")
                in_list = ('ol', indent)
            out_lines.append(f"<li>{text}</li>")
            i += 1
            continue
        
        # Close list if we were in one
        if in_list and line.strip() == "":
            out_lines.append(f"</{in_list[0]}>")
            in_list = None
            out_lines.append("")
            i += 1
            continue
        
        if in_list and line.strip() != "":
            # Check if this is a continuation of a list item (indented paragraph)
            out_lines.append(f"</{in_list[0]}>")
            in_list = None
            # Fall through to process line as paragraph
        elif in_list:
            out_lines.append(f"</{in_list[0]}>")
            in_list = None
        
        # Blockquote
        if line.startswith(">"):
            text = process_inline(line[1:].strip())
            out_lines.append(f"<blockquote><p>{text}</p></blockquote>")
            i += 1
            continue
        
        # Empty line
        if line.strip() == "":
            out_lines.append("")
            i += 1
            continue
        
        # Regular paragraph
        text = process_inline(line)
        out_lines.append(f"<p>{text}</p>")
        i += 1
    
    # Close any open structures
    if in_table:
        out_lines.append("</tbody></table></div>")
    if in_list:
        out_lines.append(f"</{in_list[0]}>")
    if in_code_block:
        out_lines.append(f'<pre><code>{"".join(code_lines)}</code></pre>')
    
    # Footnotes section
    if footnotes:
        out_lines.append('<div class="footnotes"><hr><ol>')
        for num, fn_text in footnotes:
            out_lines.append(f'<li id="fn{num}"><p>{fn_text} <a href="#fnref{num}" class="footnote-back">↩</a></p></li>')
        out_lines.append("</ol></div>")
    
    return "\n".join(out_lines)


# ── Region Data ──────────────────────────────────────────────────────────────

def parse_regions_yaml(filepath):
    """Simple YAML subset parser for regions.yaml."""
    regions = OrderedDict()
    with open(filepath, "r") as f:
        text = f.read()
    
    # Extract the 'regions:' block
    current_region = None
    for line in text.split("\n"):
        if line.strip().startswith("#") or line.strip() == "":
            continue
        if line.startswith("regions:"):
            continue
        m_region = re.match(r'^\s{2}(\w[\w_]*):\s*$', line)
        if m_region:
            current_region = m_region.group(1)
            regions[current_region] = []
            continue
        m_country = re.match(r'^\s{4}-\s*\{country:\s*([\w-]+).*\}', line)
        if m_country and current_region:
            regions[current_region].append(m_country.group(1))
    return regions


# Build region label lookup
REGION_LABELS = {
    "eu_western": "Western Europe",
    "eu_eastern": "Eastern Europe",
    "balkans_caucasus": "Balkans & Caucasus",
    "middle_east_gulf": "Middle East & Gulf",
    "africa_north": "North Africa",
    "africa_west": "West Africa",
    "africa_east_south": "East & South Africa",
    "latin_america": "Latin America",
    "caribbean_central": "Caribbean & Central America",
    "north_america_oceania": "North America & Oceania",
}

# ── Page Registry ────────────────────────────────────────────────────────────

# These are populated during collection
CONCEPT_SLUGS = set()
all_pages = {}  # slug -> {title, type, body, frontmatter, html_body, category, tags, ...}


def collect_pages():
    """Read all .md files from conditions/ and concepts/, parse frontmatter."""
    # Concepts first (to build CONCEPT_SLUGS)
    for md_file in sorted(CONCEPTS_DIR.glob("*.md")):
        slug = md_file.stem
        CONCEPT_SLUGS.add(slug)
        text = md_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        html_body = md_to_html(body, "concept", slug)
        all_pages[slug] = {
            "slug": slug,
            "title": frontmatter.get("title", slug.replace("-", " ").title()),
            "type": "concept",
            "category": frontmatter.get("category", ""),
            "tags": frontmatter.get("tags", []),
            "confidence": frontmatter.get("confidence", ""),
            "updated": frontmatter.get("updated", ""),
            "country_code": frontmatter.get("country_code", ""),
            "frontmatter": frontmatter,
            "body": body,
            "html_body": html_body,
            "source_file": str(md_file.relative_to(WIKI_DIR)),
        }
    
    # Country pages
    for md_file in sorted(CONDITIONS_DIR.glob("*.md")):
        slug = md_file.stem
        text = md_file.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        html_body = md_to_html(body, "entity", slug)
        all_pages[slug] = {
            "slug": slug,
            "title": frontmatter.get("title", slug.replace("-", " ").title()),
            "type": "entity",
            "category": frontmatter.get("category", ""),
            "tags": frontmatter.get("tags", []),
            "confidence": frontmatter.get("confidence", ""),
            "updated": frontmatter.get("updated", ""),
            "country_code": frontmatter.get("country_code", ""),
            "frontmatter": frontmatter,
            "body": body,
            "html_body": html_body,
            "source_file": str(md_file.relative_to(WIKI_DIR)),
        }


# ── HTML Templates ───────────────────────────────────────────────────────────

CSS = r"""
/* ── Reset & Base ──────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --bg-tertiary: #0f3460;
  --bg-card: #1e2746;
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0b8;
  --text-muted: #6c6c8a;
  --accent: #6c63ff;
  --accent-light: #8b85ff;
  --accent-dark: #4a44cc;
  --link: #7b93db;
  --link-hover: #a0b4ff;
  --border: #2a2a4a;
  --table-header-bg: #0f3460;
  --table-row-alt: #1a1f3a;
  --table-row-hover: #252a4a;
  --tag-bg: #2a2a5a;
  --tag-text: #b0b0d0;
  --success: #4caf50;
  --warning: #ff9800;
  --danger: #f44336;
  --sidebar-width: 280px;
  --header-height: 56px;
  --max-content-width: 960px;
}

html { font-size: 16px; scroll-behavior: smooth; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.65;
  min-height: 100vh;
}

a { color: var(--link); text-decoration: none; }
a:hover { color: var(--link-hover); text-decoration: underline; }
a.wikilink { color: var(--accent-light); }
a.wikilink:hover { color: #c0b8ff; }

/* ── Layout ────────────────────────────────────────────────────────────────── */
.app { display: flex; min-height: 100vh; }

/* ── Sidebar ───────────────────────────────────────────────────────────────── */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: transform 0.3s ease;
}

.sidebar-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(135deg, var(--bg-tertiary), var(--bg-secondary));
}
.sidebar-header h2 {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.3;
}
.sidebar-header .subtitle {
  font-size: 0.72rem;
  color: var(--text-muted);
  margin-top: 4px;
}

/* Search in sidebar */
.sidebar-search {
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}
.sidebar-search input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-primary);
  color: var(--text-primary);
  font-size: 0.85rem;
  outline: none;
  transition: border-color 0.2s;
}
.sidebar-search input:focus {
  border-color: var(--accent);
}
.sidebar-search input::placeholder { color: var(--text-muted); }
.no-results {
  display: none;
  padding: 8px 20px;
  color: var(--text-muted);
  font-size: 0.8rem;
  font-style: italic;
}

.sidebar-nav { flex: 1; overflow-y: auto; padding: 8px 0; }
.sidebar-nav .region-group { margin-bottom: 8px; }
.sidebar-nav .region-label {
  padding: 6px 20px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}
.sidebar-nav .nav-item { display: block; }
.sidebar-nav .nav-item a {
  display: block;
  padding: 5px 20px 5px 28px;
  font-size: 0.84rem;
  color: var(--text-secondary);
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.sidebar-nav .nav-item a:hover,
.sidebar-nav .nav-item a.active {
  color: var(--text-primary);
  background: var(--bg-tertiary);
  border-left-color: var(--accent);
  text-decoration: none;
}

/* Concept links in sidebar */
.sidebar-concepts {
  border-top: 1px solid var(--border);
  padding: 8px 0;
}
.sidebar-concepts .concept-label {
  padding: 6px 20px;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
}

.sidebar-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  font-size: 0.7rem;
  color: var(--text-muted);
}

/* ── Main Content ──────────────────────────────────────────────────────────── */
.main {
  margin-left: var(--sidebar-width);
  flex: 1;
  min-width: 0;
}

/* Top bar */
.topbar {
  height: var(--header-height);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 50;
}
.topbar .breadcrumb {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.topbar .breadcrumb a { color: var(--text-muted); }
.topbar .breadcrumb .sep { margin: 0 8px; }
.topbar .mobile-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 1.4rem;
  cursor: pointer;
  margin-right: 12px;
}

/* Content area */
.content {
  padding: 32px;
  max-width: var(--max-content-width);
}
.content h1 { font-size: 2rem; font-weight: 700; margin-bottom: 8px; color: #fff; }
.content h2 {
  font-size: 1.5rem; font-weight: 600; margin: 36px 0 12px;
  padding-bottom: 6px; border-bottom: 1px solid var(--border); color: #e8e8f0;
}
.content h3 { font-size: 1.15rem; font-weight: 600; margin: 24px 0 8px; color: #d0d0e0; }
.content h4 { font-size: 1rem; font-weight: 600; margin: 16px 0 6px; color: var(--text-secondary); }
.content p { margin: 12px 0; }
.content ul, .content ol { margin: 12px 0; padding-left: 24px; }
.content li { margin: 4px 0; }
.content blockquote {
  border-left: 4px solid var(--accent);
  padding: 8px 16px;
  margin: 16px 0;
  background: var(--bg-card);
  border-radius: 0 6px 6px 0;
  color: var(--text-secondary);
}
.content blockquote p { margin: 4px 0; }
.content code {
  background: var(--bg-tertiary);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.88em;
  font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', 'Consolas', monospace;
}
.content pre {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  border: 1px solid var(--border);
}
.content pre code { background: none; padding: 0; }
.content hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 24px 0;
}

/* Tables */
.table-wrapper {
  overflow-x: auto;
  margin: 16px 0;
  border: 1px solid var(--border);
  border-radius: 8px;
}
.content table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}
.content thead { background: var(--table-header-bg); }
.content th {
  padding: 10px 14px;
  text-align: left;
  font-weight: 600;
  color: #c0c8e0;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}
.content td {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border);
}
.content tbody tr:nth-child(even) { background: var(--table-row-alt); }
.content tbody tr:hover { background: var(--table-row-hover); }

/* Frontmatter / metadata header */
.page-meta {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px 20px;
  margin-bottom: 24px;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.page-meta .meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--text-secondary);
}
.page-meta .meta-label { color: var(--text-muted); }
.page-meta .meta-value { font-weight: 500; color: var(--text-primary); }

/* Tags */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  background: var(--tag-bg);
  color: var(--tag-text);
  margin: 2px;
}
.tag.confidence-high { background: #1b5e20; color: #a5d6a7; }
.tag.confidence-medium { background: #e65100; color: #ffcc80; }
.tag.confidence-low { background: #b71c1c; color: #ef9a9a; }
.tag.category-strong_passport { background: #1a237e; color: #9fa8da; }
.tag.category-it_friendly { background: #004d40; color: #80cbc4; }
.tag.category-yacht_captain { background: #1b5e20; color: #a5d6a7; }
.tag.category-popular_ru { background: #4a148c; color: #ce93d8; }
.tag.category-clear_pathway { background: #0d47a1; color: #90caf9; }

/* Footnotes */
.footnotes { margin-top: 32px; font-size: 0.82rem; color: var(--text-muted); }
.footnotes hr { margin-bottom: 12px; }
.footnotes ol { padding-left: 20px; }
.footnotes li { margin: 4px 0; }
.footnote-ref a { font-size: 0.75rem; text-decoration: none; }
.footnote-back { text-decoration: none; margin-left: 4px; }

/* Index page */
.index-region { margin-bottom: 24px; }
.index-region h3 {
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 10px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border);
}
.index-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}
.index-item a {
  display: block;
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.88rem;
  transition: all 0.15s;
}
.index-item a:hover {
  background: var(--bg-tertiary);
  border-color: var(--accent);
  text-decoration: none;
}
.index-item .cc { font-size: 0.7rem; color: var(--text-muted); margin-left: 6px; }

/* Concept cards */
.concept-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-top: 16px;
}
.concept-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.15s;
}
.concept-card:hover { border-color: var(--accent); }
.concept-card h4 { margin-bottom: 6px; font-size: 0.95rem; }

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
  }
  .sidebar.open {
    transform: translateX(0);
  }
  .main { margin-left: 0; }
  .topbar .mobile-menu-btn { display: block; }
  .content { padding: 16px; }
}
"""


def render_page(page):
    """Render a single page as complete HTML."""
    slug = page["slug"]
    title = page["title"]
    
    # Build metadata header HTML
    meta_parts = []
    if page.get("country_code"):
        meta_parts.append(f'<div class="meta-item"><span class="meta-label">Code:</span><span class="meta-value">{html.escape(page["country_code"])}</span></div>')
    if page.get("confidence"):
        cls = f"confidence-{page['confidence']}"
        meta_parts.append(f'<div class="meta-item"><span class="meta-label">Confidence:</span><span class="tag {cls}">{html.escape(page["confidence"].upper())}</span></div>')
    if page.get("updated"):
        meta_parts.append(f'<div class="meta-item"><span class="meta-label">Updated:</span><span class="meta-value">{html.escape(page["updated"])}</span></div>')
    if page.get("category"):
        cats = page["category"] if isinstance(page["category"], list) else [page["category"]]
        for cat in cats:
            cls_cat = f"category-{cat}" if cat in ["strong_passport", "it_friendly", "yacht_captain", "popular_ru", "clear_pathway"] else ""
            meta_parts.append(f'<span class="tag {cls_cat}">{html.escape(cat)}</span>')
    if page.get("tags"):
        for tag in page["tags"]:
            meta_parts.append(f'<span class="tag">{html.escape(tag)}</span>')
    
    meta_html = f'<div class="page-meta">{"".join(meta_parts)}</div>' if meta_parts else ""
    
    # Breadcrumb
    if page["type"] == "entity":
        breadcrumb = f'<a href="/">Home</a><span class="sep">›</span><span>{html.escape(title)}</span>'
    else:
        breadcrumb = f'<a href="/">Home</a><span class="sep">›</span><a href="/#concepts">Concepts</a><span class="sep">›</span><span>{html.escape(title)}</span>'
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(title)} — {SITE_TITLE}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌍</text></svg>">
<style>{CSS}</style>
</head>
<body>
<div class="app">
{SIDEBAR_HTML}
<div class="main">
<header class="topbar">
  <button class="mobile-menu-btn" onclick="document.querySelector('.sidebar').classList.toggle('open')" aria-label="Toggle menu">☰</button>
  <nav class="breadcrumb">{breadcrumb}</nav>
</header>
<main class="content">
<h1>{html.escape(title)}</h1>
{meta_html}
{page["html_body"]}
</main>
</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  // Highlight current page in sidebar
  var current = '{slug}';
  var links = document.querySelectorAll('.sidebar-nav a');
  links.forEach(function(a) {{
    if (a.getAttribute('data-slug') === current) a.classList.add('active');
  }});
}});
</script>
</body>
</html>"""


def render_index(regions, concept_pages):
    """Render the index/home page."""
    # Build region sections
    region_sections = []
    for region_key, countries in regions.items():
        label = REGION_LABELS.get(region_key, region_key.replace("_", " ").title())
        items_html = []
        for country_slug in countries:
            page = all_pages.get(country_slug)
            if not page:
                # Country in regions.yaml but no page yet
                items_html.append(f'<div class="index-item"><span style="color:var(--text-muted);padding:8px 12px;display:block">{country_slug.replace("-"," ").title()}</span></div>')
                continue
            title = page["title"]
            # Strip "Country — " prefix for cleaner display
            display_title = title
            if " — " in title:
                display_title = title.split(" — ", 1)[0]
            cc = page.get("country_code", "")
            cc_html = f'<span class="cc">{html.escape(cc)}</span>' if cc else ""
            items_html.append(f'<div class="index-item"><a href="/conditions/{country_slug}.html" data-slug="{country_slug}">{html.escape(display_title)}{cc_html}</a></div>')
        region_sections.append(f'<section class="index-region"><h3>{label} ({len(countries)})</h3><div class="index-grid">{"".join(items_html)}</div></section>')
    
    # Concept cards
    concept_cards = []
    for slug, page in concept_pages.items():
        # Extract first paragraph as summary
        body = page["body"]
        summary = ""
        # Try to find first paragraph after any heading
        for line in body.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("|") and not stripped.startswith("-"):
                summary = stripped[:160]
                if len(stripped) > 160:
                    summary += "…"
                break
        concept_cards.append(f'<div class="concept-card"><h4><a href="/concepts/{slug}.html">{html.escape(page["title"])}</a></h4><p style="font-size:0.82rem;color:var(--text-muted)">{html.escape(summary)}</p></div>')
    
    meta_html = f'<div class="page-meta"><div class="meta-item"><span class="meta-label">Total countries:</span><span class="meta-value">{len(all_pages) - len(concept_pages)}</span></div><div class="meta-item"><span class="meta-label">Concept pages:</span><span class="meta-value">{len(concept_pages)}</span></div><div class="meta-item"><span class="meta-label">Built:</span><span class="meta-value">{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</span></div></div>'
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{SITE_TITLE}</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌍</text></svg>">
<style>{CSS}</style>
</head>
<body>
<div class="app">
{SIDEBAR_HTML}
<div class="main">
<header class="topbar">
  <button class="mobile-menu-btn" onclick="document.querySelector('.sidebar').classList.toggle('open')" aria-label="Toggle menu">☰</button>
  <nav class="breadcrumb"><span>{SITE_TITLE}</span></nav>
</header>
<main class="content">
<h1>{SITE_TITLE}</h1>
<p style="color:var(--text-secondary);margin-bottom:8px">{SITE_SUBTITLE}</p>
{meta_html}

{"".join(region_sections)}

<h2 id="concepts">Residency Type Concepts</h2>
<div class="concept-cards">
{"".join(concept_cards)}
</div>
</main>
</div>
</div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
  document.querySelectorAll('.sidebar-nav a[data-slug]').forEach(function(a) {{
    a.classList.remove('active');
  }});
}});
</script>
</body>
</html>"""


# ── Sidebar Generation ───────────────────────────────────────────────────────

SIDEBAR_HTML = ""  # Set during build

def build_sidebar(regions, concept_pages):
    """Generate the shared sidebar HTML."""
    nav_items = []
    for region_key, countries in regions.items():
        label = REGION_LABELS.get(region_key, region_key.replace("_", " ").title())
        items = []
        for country_slug in countries:
            page = all_pages.get(country_slug)
            if not page:
                continue
            title = page["title"]
            if " — " in title:
                title = title.split(" — ", 1)[0]
            items.append(f'<div class="nav-item"><a href="/conditions/{country_slug}.html" data-slug="{country_slug}">{html.escape(title)}</a></div>')
        nav_items.append(f'<div class="region-group"><div class="region-label">{label}</div>{"".join(items)}</div>')
    
    concept_items = []
    for slug, page in concept_pages.items():
        concept_items.append(f'<div class="nav-item"><a href="/concepts/{slug}.html" data-slug="{slug}">{html.escape(page["title"])}</a></div>')
    
    return f"""
<aside class="sidebar">
  <div class="sidebar-header">
    <h2><a href="/" style="color:inherit;text-decoration:none">{SITE_TITLE}</a></h2>
    <div class="subtitle">{SITE_SUBTITLE}</div>
  </div>
  <div class="sidebar-search">
    <input type="text" id="sidebar-search-input" placeholder="Search countries…" autocomplete="off">
    <div class="no-results" id="no-results">No results found</div>
  </div>
  <nav class="sidebar-nav">
    {"".join(nav_items)}
  </nav>
  <div class="sidebar-concepts">
    <div class="concept-label">Concepts</div>
    {"".join(concept_items)}
  </div>
  <div class="sidebar-footer">
    Built {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} · {len(all_pages)} pages
  </div>
</aside>
<script>{SEARCH_JS}</script>"""


# ── Search JSON index generation ─────────────────────────────────────────────

def generate_search_index():
    """Generate a search-index.json for client-side filtering."""
    index = []
    for slug, page in all_pages.items():
        if page["type"] == "entity":
            title = page["title"]
            if " — " in title:
                display = title.split(" — ", 1)[0]
            else:
                display = title
            index.append({
                "slug": slug,
                "title": display,
                "full_title": title,
                "country_code": page.get("country_code", ""),
                "type": "entity",
                "url": f"/conditions/{slug}.html",
            })
        else:
            index.append({
                "slug": slug,
                "title": page["title"],
                "full_title": page["title"],
                "country_code": "",
                "type": "concept",
                "url": f"/concepts/{slug}.html",
            })
    return json.dumps(index, ensure_ascii=False, sort_keys=True)


SEARCH_JS = r"""
(function() {
  var input = document.getElementById('sidebar-search-input');
  var noResults = document.getElementById('no-results');
  if (!input) return;
  
  var index = [];
  var xhr = new XMLHttpRequest();
  xhr.open('GET', '/search-index.json', true);
  xhr.onload = function() {
    if (xhr.status === 200) {
      index = JSON.parse(xhr.responseText);
    }
  };
  xhr.send();
  
  input.addEventListener('input', function() {
    var q = input.value.toLowerCase().trim();
    var items = document.querySelectorAll('.sidebar-nav .nav-item, .sidebar-concepts .nav-item');
    var regionGroups = document.querySelectorAll('.sidebar-nav .region-group');
    var regionLabels = document.querySelectorAll('.sidebar-nav .region-label');
    var conceptLabel = document.querySelector('.concept-label');
    var visible = 0;
    
    regionGroups.forEach(function(g) { g.style.display = 'none'; });
    regionLabels.forEach(function(l) { l.style.display = 'none'; });
    
    items.forEach(function(item) {
      var a = item.querySelector('a');
      if (!a) return;
      var text = a.textContent.toLowerCase();
      
      // Also search by country code from the index
      var slug = a.getAttribute('data-slug') || '';
      var cc = '';
      for (var i = 0; i < index.length; i++) {
        if (index[i].slug === slug) { cc = index[i].country_code.toLowerCase(); break; }
      }
      
      if (!q || text.indexOf(q) !== -1 || cc.indexOf(q) !== -1) {
        item.style.display = '';
        visible++;
        // Show parent region group
        var group = item.closest('.region-group');
        if (group) {
          group.style.display = '';
          // Show the label in this group
          var label = group.querySelector('.region-label');
          if (label) label.style.display = '';
        }
      } else {
        item.style.display = 'none';
      }
    });
    
    // Show concept label if any concept is visible
    if (conceptLabel) {
      var conceptVisible = false;
      document.querySelectorAll('.sidebar-concepts .nav-item').forEach(function(item) {
        if (item.style.display !== 'none') conceptVisible = true;
      });
      conceptLabel.style.display = conceptVisible || !q ? '' : 'none';
    }
    
    noResults.style.display = (visible === 0 && q) ? 'block' : 'none';
  });
})();
"""


# ── Main Build ───────────────────────────────────────────────────────────────

def build():
    """Main build function."""
    global SIDEBAR_HTML, CONCEPT_SLUGS, all_pages
    
    print(f"🔨 Building static site: {SITE_TITLE}")
    print(f"   Source: {WIKI_DIR}")
    print(f"   Output: {OUTPUT_DIR}")
    
    # Collect pages
    collect_pages()
    print(f"   Collected {len(all_pages)} pages ({len([p for p in all_pages.values() if p['type']=='entity'])} countries, {len([p for p in all_pages.values() if p['type']=='concept'])} concepts)")
    
    # Parse regions
    regions = parse_regions_yaml(REGIONS_FILE)
    total_countries_in_regions = sum(len(v) for v in regions.values())
    print(f"   Regions: {len(regions)} groups, {total_countries_in_regions} countries listed")
    
    # Get concept pages sorted
    concept_pages = OrderedDict(
        sorted(
            [(s, p) for s, p in all_pages.items() if p["type"] == "concept"],
            key=lambda x: x[0]
        )
    )
    
    # Build sidebar
    SIDEBAR_HTML = build_sidebar(regions, concept_pages)
    
    # Clean output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "conditions").mkdir(exist_ok=True)
    (OUTPUT_DIR / "concepts").mkdir(exist_ok=True)
    
    # Generate country pages
    file_count = 0
    for slug, page in all_pages.items():
        if page["type"] != "entity":
            continue
        html_content = render_page(page)
        out_path = OUTPUT_DIR / "conditions" / f"{slug}.html"
        out_path.write_text(html_content, encoding="utf-8")
        file_count += 1
    print(f"   Generated {file_count} country pages")
    
    # Generate concept pages
    concept_file_count = 0
    for slug, page in concept_pages.items():
        html_content = render_page(page)
        out_path = OUTPUT_DIR / "concepts" / f"{slug}.html"
        out_path.write_text(html_content, encoding="utf-8")
        file_count += 1
        concept_file_count += 1
    print(f"   Generated {concept_file_count} concept pages")
    
    # Generate index
    index_html = render_index(regions, concept_pages)
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    file_count += 1
    print(f"   Generated index page")
    
    # Generate search index
    search_json = generate_search_index()
    (OUTPUT_DIR / "search-index.json").write_text(search_json, encoding="utf-8")
    file_count += 1
    print(f"   Generated search index")
    
    # Generate client-side search JS (inline in each page, but separate for future)
    # Already embedded in SIDEBAR_HTML via each page's template
    
    # Copy .nojekyll for GitHub Pages
    (OUTPUT_DIR / ".nojekyll").write_text("")
    
    print(f"\n✅ Build complete: {file_count} files written to {OUTPUT_DIR}")
    return file_count


if __name__ == "__main__":
    count = build()
    sys.exit(0)