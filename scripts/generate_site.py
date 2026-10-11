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

# ── Relative URL Helper ───────────────────────────────────────────────────────

def relative_url(abs_path, depth, current_dir):
    """Convert absolute path to relative URL based on page depth and directory.
    abs_path: '/conditions/x.html', '/', '/search-index.json', '/#anchor'
    depth: 0 for root (index), 1 for subdirectory (conditions/ or concepts/)
    current_dir: 'conditions', 'concepts', or None (for index)
    """
    if depth == 0:
        # Index page at root: strip leading slash
        if abs_path == '/':
            return 'index.html'
        if abs_path.startswith('/#'):
            return abs_path[1:]  # '#anchor'
        return abs_path.lstrip('/')
    
    # depth == 1: in conditions/ or concepts/
    if abs_path == '/':
        return '../index.html'
    if abs_path.startswith('/#'):
        return '..' + abs_path  # '../#anchor'
    
    path = abs_path.lstrip('/')
    if current_dir and path.startswith(current_dir + '/'):
        return path.split('/', 1)[1]  # same dir, just filename
    return '../' + path



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
            # Build relative wikilink based on page type
            if page_type == "entity":
                if slug in CONCEPT_SLUGS:
                    # Cross-dir: conditions page linking to concept
                    rel_href = f"../concepts/{slug}.html"
                else:
                    # Same dir: conditions to conditions
                    rel_href = f"{slug}.html"
            elif page_type == "concept":
                if slug in CONCEPT_SLUGS:
                    # Same dir: concept to concept
                    rel_href = f"{slug}.html"
                else:
                    # Cross-dir: concept page linking to condition
                    rel_href = f"../conditions/{slug}.html"
            else:
                rel_href = f"{href}.html"
            return f'<a href="{rel_href}{fragment}" class="wikilink">{html.escape(label)}</a>'
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


# ── Country Snapshot & Country Card Extraction ────────────────────────────────

def extract_snapshot_card(text):
    """Extract Country Snapshot and Country Card sections from body text.
    Returns (clean_body, snapshot_html, card_html).
    snapshot_html and card_html are None if not found."""
    # Extract Country Card first to get its position right
    clean, card_text = extract_section(text, '## Country Card')
    card_html = render_card_html(card_text) if card_text else None

    # Extract Country Snapshot from the cleaned body
    clean, snap_text = extract_section(clean, '## Country Snapshot')
    snapshot_html = render_snapshot_html(snap_text) if snap_text else None

    return clean, snapshot_html, card_html


def extract_section(text, heading):
    """Extract a markdown section from `## heading` to the next `## ` or EOF.
    Returns (clean_text, section_text) or (text, None) if not found."""
    pattern = re.compile(r'^' + re.escape(heading) + r'\s*$', re.MULTILINE)
    m = pattern.search(text)
    if not m:
        return text, None
    start = m.start()
    # Find next ## heading (not ###, not ####)
    next_h = re.search(r'\n## ', text[m.end():])
    if next_h:
        end = m.end() + next_h.start()
    else:
        end = len(text)
    section_text = text[start:end].strip()
    # Remove from body, preserving blank lines
    clean = text[:start] + text[end:]
    return clean, section_text


def parse_snapshot_table(content):
    """Parse snapshot in 3-column markdown table form.
    Returns [(field, value, source), ...]."""
    rows = []
    lines = content.strip().split('\n')
    for line in lines:
        if not line.strip() or '---' in line:
            continue
        if '|' in line:
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) >= 2:
                field = cells[0]
                if field.lower() == 'field':
                    continue
                value = cells[1] if len(cells) > 1 else ''
                source = cells[2] if len(cells) > 2 else ''
                rows.append((field, value, source))
    return rows


def parse_snapshot_list(content):
    """Parse snapshot in markdown list form: `- **Field**: Value ^[source] confidence`.
    Returns [(field, value, source), ...]."""
    rows = []
    for line in content.split('\n'):
        line = line.strip()
        m = re.match(r'^[-*+]\s+\*\*(.+?)\*\*\s*:\s*(.+)$', line)
        if m:
            field = m.group(1).strip()
            rest = m.group(2).strip()
            fn_match = re.findall(r'\^\[([^\]]*)\]', rest)
            source = '; '.join(fn_match) if fn_match else ''
            value = re.sub(r'\^\[[^\]]*\]', '', rest).strip()
            rows.append((field, value, source))
    return rows


def render_snapshot_html(section_text):
    """Parse a Country Snapshot markdown section and return styled HTML table."""
    # Strip the heading line
    lines = section_text.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('## Country Snapshot'):
            content_start = i + 1
            break
    content = '\n'.join(lines[content_start:]).strip()
    if not content:
        return '<div class="snapshot-section"><h2 id="country-snapshot">Country Snapshot</h2><p class="snapshot-empty">No data yet.</p></div>'

    # Detect format: table or list
    if '|' in content and any('---' in l for l in content.split('\n')):
        rows = parse_snapshot_table(content)
    else:
        rows = parse_snapshot_list(content)

    if not rows:
        return '<div class="snapshot-section"><h2 id="country-snapshot">Country Snapshot</h2><p class="snapshot-empty">No data yet.</p></div>'

    def snap_inline(s):
        t = html.escape(s)
        t = re.sub(r'\[\[#([\w-]+)\]\]', lambda m: f'<a class="wikilink" href="#{m.group(1)}">{m.group(1).replace("-", " ")}</a>', t)
        t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" rel="noopener">\1</a>', t)
        t = re.sub(r'\s*[—-]?\s*\[?(hard/official)\]?', ' <span class="off">official</span>', t)
        t = re.sub(r'\s*[—-]?\s*\[?(soft/estimate)\]?', ' <span class="est">estimate</span>', t)
        return t.strip()

    html_parts = [
        '<div class="snapshot-section">',
        '<h2 id="country-snapshot">Country Snapshot</h2>',
        '<div class="table-wrapper"><table class="snapshot-table">',
        '<thead><tr><th>Field</th><th>Value</th></tr></thead>',
        '<tbody>'
    ]
    for field, value, source in rows:
        val_html = html.escape(value)
        if source:
            val_html += f'<span class="snapshot-source">{snap_inline(source)}</span>'
        html_parts.append(f'<tr><td class="snap-field">{html.escape(field)}</td><td class="snap-value">{val_html}</td></tr>')
    html_parts.append('</tbody></table></div></div>')
    return '\n'.join(html_parts)


def render_card_html(section_text):
    """Parse a Country Card markdown section and return styled HTML box."""
    lines = section_text.split('\n')
    content_start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith('## Country Card'):
            content_start = i + 1
            break
    lines = lines[content_start:]

    desc_lines = []
    strong_points = []
    problems = []
    section = 'desc'

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### Well-known strong points'):
            section = 'strong'
            continue
        elif stripped.startswith('### Well-known problems'):
            section = 'problems'
            continue
        elif stripped.lower().startswith('### general description'):
            section = 'desc'
            continue
        elif stripped.startswith('###'):
            section = 'other'
            continue

        if section == 'desc' and stripped:
            desc_lines.append(stripped)
        elif section == 'strong':
            m = re.match(r'^[-*+]\s+(.+)$', stripped)
            if m:
                strong_points.append(m.group(1))
        elif section == 'problems':
            m = re.match(r'^[-*+]\s+(.+)$', stripped)
            if m:
                problems.append(m.group(1))

    description = ' '.join(desc_lines).strip()

    html_parts = ['<div class="country-card">',
                  '<h2 id="country-card">Country Card</h2>']
    if description:
        html_parts.append(f'<p class="card-description">{html.escape(description)}</p>')
    if strong_points or problems:
        html_parts.append('<div class="proscons">')
        if strong_points:
            html_parts.append('<div class="pros"><h3>Strong points</h3><ul>' + ''.join(f'<li>{html.escape(sp)}</li>' for sp in strong_points) + '</ul></div>')
        if problems:
            html_parts.append('<div class="cons"><h3>Known problems</h3><ul>' + ''.join(f'<li>{html.escape(p)}</li>' for p in problems) + '</ul></div>')
        html_parts.append('</div>')
    html_parts.append('</div>')
    return '\n'.join(html_parts)


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
            "last_checked": frontmatter.get("last_checked", ""),
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
        # Extract Country Snapshot and Country Card before normal rendering
        clean_body, snapshot_html, card_html = extract_snapshot_card(body)
        html_body = md_to_html(clean_body, "entity", slug)
        all_pages[slug] = {
            "slug": slug,
            "title": frontmatter.get("title", slug.replace("-", " ").title()),
            "type": "entity",
            "category": frontmatter.get("category", ""),
            "tags": frontmatter.get("tags", []),
            "confidence": frontmatter.get("confidence", ""),
            "updated": frontmatter.get("updated", ""),
            "last_checked": frontmatter.get("last_checked", ""),
            "country_code": frontmatter.get("country_code", ""),
            "frontmatter": frontmatter,
            "body": body,
            "html_body": html_body,
            "snapshot_html": snapshot_html,
            "card_html": card_html,
            "source_file": str(md_file.relative_to(WIKI_DIR)),
        }


# ── HTML Templates ───────────────────────────────────────────────────────────


CSS = r"""
:root {
  --bg: #f5f2ea;
  --surface: #fffdf8;
  --sunken: #ece8dc;
  --ink: #1d1c18;
  --ink-2: #4a473f;
  --muted: #7a7567;
  --line: #ddd7c8;
  --line-strong: #bfb8a5;
  --accent: #1f5f4a;
  --accent-ink: #ffffff;
  --accent-soft: #dfeadf;
  --good: #2f6b3a;
  --warn: #9a4a12;
  --serif: "Source Serif 4", "Iowan Old Style", "Charter", "Palatino Linotype", Georgia, serif;
  --sans: "Inter Tight", "Segoe UI", "Helvetica Neue", Arial, system-ui, sans-serif;
  --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  --wrap: 1180px;
  color-scheme: light;
}
:root[data-theme="dark"] {
  --bg: #14130f;
  --surface: #1b1a15;
  --sunken: #23211b;
  --ink: #ece8dc;
  --ink-2: #c6c1b2;
  --muted: #8f8a7a;
  --line: #2f2d25;
  --line-strong: #4a473c;
  --accent: #7cc3a1;
  --accent-ink: #0f1a15;
  --accent-soft: #1f2e27;
  --good: #8cc99a;
  --warn: #e0a06a;
  color-scheme: dark;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #14130f; --surface: #1b1a15; --sunken: #23211b; --ink: #ece8dc; --ink-2: #c6c1b2;
    --muted: #8f8a7a; --line: #2f2d25; --line-strong: #4a473c; --accent: #7cc3a1;
    --accent-ink: #0f1a15; --accent-soft: #1f2e27; --good: #8cc99a; --warn: #e0a06a;
    color-scheme: dark;
  }
}
*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: 76px; -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 400 16px/1.65 var(--sans); -webkit-font-smoothing: antialiased;
}
a { color: var(--accent); text-decoration-thickness: 1px; text-underline-offset: 3px; }
a:hover { text-decoration-thickness: 2px; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 3px; }
.wrap { max-width: var(--wrap); margin: 0 auto; padding: 0 24px; }

/* ── Top bar ── */
.topbar { position: sticky; top: 0; z-index: 30; background: color-mix(in srgb, var(--bg) 92%, transparent);
  backdrop-filter: blur(6px); border-bottom: 1px solid var(--line); }
.topbar .wrap { display: flex; align-items: center; gap: 28px; height: 56px; }
.brand { font: 600 18px/1 var(--serif); color: var(--ink); text-decoration: none; letter-spacing: -.01em; white-space: nowrap; }
.brand span { color: var(--accent); }
.topnav { display: flex; gap: 20px; font-size: 14px; }
.topnav a { color: var(--ink-2); text-decoration: none; }
.topnav a:hover { color: var(--ink); text-decoration: underline; }
.topbar .spacer { flex: 1; }
.search-btn { display: flex; align-items: center; gap: 10px; min-width: 240px; height: 36px; padding: 0 10px 0 12px;
  background: var(--surface); border: 1px solid var(--line-strong); border-radius: 6px; color: var(--muted);
  font: 14px var(--sans); cursor: pointer; text-align: left; }
.search-btn:hover { border-color: var(--ink-2); }
.search-btn span:first-child { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
kbd { font: 11px var(--mono); padding: 1px 6px; border: 1px solid var(--line-strong); border-radius: 4px; color: var(--muted); background: var(--bg); }
.icon-btn { width: 36px; height: 36px; border: 1px solid var(--line-strong); background: var(--surface); color: var(--ink-2);
  border-radius: 6px; cursor: pointer; font-size: 15px; line-height: 1; }
.icon-btn:hover { color: var(--ink); border-color: var(--ink-2); }

/* ── Palette ── */
.palette { position: fixed; inset: 0; z-index: 50; display: none; background: rgba(20,19,15,.45); padding: 12vh 16px 0; }
.palette.open { display: block; }
.palette-box { max-width: 560px; margin: 0 auto; background: var(--surface); border: 1px solid var(--line-strong);
  border-radius: 10px; box-shadow: 0 24px 60px rgba(0,0,0,.28); overflow: hidden; }
.palette input { width: 100%; border: 0; border-bottom: 1px solid var(--line); padding: 16px 18px; background: transparent;
  color: var(--ink); font: 17px var(--sans); outline: none; }
.palette ul { list-style: none; margin: 0; padding: 6px; max-height: 50vh; overflow: auto; }
.palette li a { display: flex; justify-content: space-between; gap: 12px; padding: 9px 12px; border-radius: 6px;
  color: var(--ink); text-decoration: none; font-size: 15px; }
.palette li a small { color: var(--muted); font: 12px var(--mono); align-self: center; }
.palette li.sel a, .palette li a:hover { background: var(--accent-soft); }
.palette .empty { padding: 18px; color: var(--muted); font-size: 14px; }

/* ── Chips, confidence ── */
.chip { display: inline-block; padding: 1px 9px; font-size: 12px; line-height: 20px; border: 1px solid var(--line-strong);
  border-radius: 999px; color: var(--ink-2); background: transparent; white-space: nowrap; }
.conf { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink-2); }
.conf i { display: inline-flex; gap: 2px; }
.conf i b { width: 14px; height: 5px; border-radius: 1px; background: var(--line-strong); }
.conf i b.on { background: var(--accent); }

/* ── Index ── */
.hero { padding: 48px 0 32px; display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 48px; align-items: end; }
.hero h1 { font: 600 clamp(34px, 5vw, 54px)/1.04 var(--serif); letter-spacing: -.02em; margin: 0; max-width: 15ch; }
.hero p { margin: 0; color: var(--ink-2); font-size: 17px; max-width: 46ch; }
.hero .stamp { margin-top: 14px; font: 12px var(--mono); color: var(--muted); }
.latest { margin: 8px 0 36px; border-top: 2px solid var(--ink); }
.latest h2, .section-h { font: 600 12px/1 var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 16px 0 6px; }
.latest ol { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; column-gap: 40px; }
.latest li { display: grid; grid-template-columns: 74px 1fr; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 14px; line-height: 1.5; }
.latest time { font: 12px/1.9 var(--mono); color: var(--muted); }
.latest li a { font-weight: 600; color: var(--ink); text-decoration: none; }
.latest li a:hover { color: var(--accent); text-decoration: underline; }
.latest li span { color: var(--ink-2); }

.explore { position: sticky; top: 56px; z-index: 10; background: var(--bg); padding: 14px 0 12px; border-bottom: 1px solid var(--line); }
.explore-row { display: flex; flex-wrap: wrap; gap: 8px 10px; align-items: center; }
.explore input[type=search], .explore select { height: 36px; padding: 0 12px; border: 1px solid var(--line-strong); border-radius: 6px;
  background: var(--surface); color: var(--ink); font: 14px var(--sans); }
.explore input[type=search] { width: 220px; }
.fchip { height: 32px; padding: 0 12px; border-radius: 999px; border: 1px solid var(--line-strong); background: transparent;
  color: var(--ink-2); font: 13px var(--sans); cursor: pointer; }
.fchip:hover { border-color: var(--ink); color: var(--ink); }
.fchip[aria-pressed=true] { background: var(--accent); border-color: var(--accent); color: var(--accent-ink); }
.count { margin-left: auto; font: 13px var(--mono); color: var(--muted); }
.ctable { width: 100%; border-collapse: collapse; font-size: 14px; }
.ctable th { text-align: left; font: 600 12px var(--sans); letter-spacing: .06em; text-transform: uppercase; color: var(--muted);
  padding: 12px 10px 8px; border-bottom: 1px solid var(--line-strong); white-space: nowrap; }
.ctable th button { all: unset; cursor: pointer; }
.ctable th button:hover { color: var(--ink); }
.ctable th[aria-sort=ascending] button::after { content: " ↑"; }
.ctable th[aria-sort=descending] button::after { content: " ↓"; }
.ctable td { padding: 9px 10px; border-bottom: 1px solid var(--line); vertical-align: middle; }
.ctable tbody tr:hover { background: var(--accent-soft); }
.ctable td.name a { font: 600 17px/1.2 var(--serif); color: var(--ink); text-decoration: none; }
.ctable td.name a:hover { color: var(--accent); text-decoration: underline; }
.ctable td.cc, .ctable td.num, .ctable td.date { font: 13px var(--mono); color: var(--ink-2); }
.ctable td.region { color: var(--muted); font-size: 13px; }
.ctable td.fit .chip { margin: 2px 4px 2px 0; }
.ctable td.date, .ctable td.region { white-space: nowrap; }
.ctable td.num { text-align: right; } .ctable th.num { text-align: right; }
.ctable .none { color: var(--muted); }
.progs { margin: 56px 0 72px; }
.progs ul { list-style: none; margin: 0; padding: 0; border-top: 2px solid var(--ink); }
.progs li { display: grid; grid-template-columns: minmax(200px, 300px) 1fr; gap: 24px; padding: 14px 0; border-bottom: 1px solid var(--line); }
.progs li a { font: 600 18px/1.3 var(--serif); color: var(--ink); text-decoration: none; }
.progs li a:hover { color: var(--accent); text-decoration: underline; }
.progs li p { margin: 0; color: var(--ink-2); font-size: 14px; }

/* ── Article ── */
.page-grid { display: grid; grid-template-columns: minmax(0, 1fr) 210px; gap: 56px; padding: 32px 0 80px; }
.crumbs { font-size: 13px; color: var(--muted); margin-bottom: 18px; }
.crumbs a { color: var(--muted); text-decoration: none; } .crumbs a:hover { color: var(--ink); text-decoration: underline; }
.crumbs .sep { margin: 0 8px; }
.page-head h1 { font: 600 clamp(34px, 5vw, 52px)/1.05 var(--serif); letter-spacing: -.02em; margin: 0 0 14px; }
.page-head .sub { font-size: 14px; color: var(--ink-2); display: flex; flex-wrap: wrap; gap: 8px 18px; align-items: center; }
.page-head .sub .code { font: 600 13px var(--mono); padding: 1px 8px; background: var(--ink); color: var(--bg); border-radius: 3px; }
.page-head .sub .dates { font: 13px var(--mono); color: var(--muted); }
.page-head .chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 12px; }
.facts { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); margin: 28px 0 0; border-top: 2px solid var(--ink); border-bottom: 1px solid var(--line); }
.facts div { padding: 12px 16px 14px 0; }
.facts div + div { padding-left: 16px; border-left: 1px solid var(--line); }
.facts dt { font: 600 11px var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }
.facts dd { margin: 0; font: 500 17px/1.3 var(--serif); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.monitor { margin: 28px 0 0; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 18px 22px 8px; }
.monitor h2 { font: 600 12px var(--sans) !important; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 0 12px !important; padding: 0 !important; border: 0 !important; display: flex; justify-content: space-between; }
.monitor h2 time { font: 12px var(--mono); letter-spacing: 0; text-transform: none; }
.monitor dl { margin: 0; display: grid; grid-template-columns: 110px 1fr; gap: 0 18px; }
.monitor dt { font-weight: 600; font-size: 13px; color: var(--ink-2); padding: 0 0 14px; }
.monitor dd { margin: 0; padding: 0 0 14px; font-size: 15px; line-height: 1.55; }
.article { margin-top: 12px; }
.article h2 { font: 600 28px/1.2 var(--serif); letter-spacing: -.01em; margin: 56px 0 14px; padding-top: 22px; border-top: 1px solid var(--line-strong); }
.article h3 { font: 600 19px/1.3 var(--serif); margin: 32px 0 8px; }
.article h4 { font: 600 15px var(--sans); margin: 22px 0 6px; }
.article p { margin: 0 0 14px; max-width: 70ch; text-wrap: pretty; }
.article ul, .article ol { padding-left: 1.2em; margin: 0 0 16px; max-width: 70ch; }
.article li { margin: 4px 0; }
.article li::marker { color: var(--muted); }
.article blockquote { margin: 18px 0; padding: 0 0 0 18px; border-left: 2px solid var(--line-strong); color: var(--ink-2); }
.article code { font: 0.88em var(--mono); background: var(--sunken); padding: 1px 5px; border-radius: 3px; }
.article pre { background: var(--sunken); padding: 14px; border-radius: 6px; overflow: auto; }
.article pre code { background: none; padding: 0; }
.article hr { border: 0; border-top: 1px solid var(--line); margin: 28px 0; }
.article a.wikilink { text-decoration-style: dotted; }
.table-wrapper { overflow-x: auto; margin: 16px 0 24px; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--line-strong); }
.article table { width: 100%; border-collapse: collapse; font-size: 14px; line-height: 1.5; }
.article th { text-align: left; font: 600 11px var(--sans); letter-spacing: .07em; text-transform: uppercase; color: var(--muted); padding: 10px 12px 8px; border-bottom: 1px solid var(--line-strong); white-space: nowrap; }
.article td { padding: 10px 12px; border-bottom: 1px solid var(--line); vertical-align: top; }
.article tbody tr:last-child td { border-bottom: 0; }
.article tbody tr:hover { background: var(--accent-soft); }
.article td:first-child { font-family: var(--mono); font-size: 12.5px; color: var(--ink-2); white-space: nowrap; }
sup.footnote-ref { font-size: 11px; } sup.footnote-ref a { text-decoration: none; padding: 0 1px; }
.footnotes { margin-top: 48px; font-size: 13px; color: var(--ink-2); }
.footnotes ol { max-width: none; padding-left: 1.6em; }
.footnotes p { margin: 0; word-break: break-word; }
.footnotes hr { margin-bottom: 14px; }

/* snapshot + card */
.country-card .card-description { font: 400 18px/1.6 var(--serif); max-width: 62ch; color: var(--ink-2); }
.proscons { display: grid; grid-template-columns: 1fr 1fr; gap: 0 40px; margin-top: 20px; }
.proscons h3 { font: 600 12px var(--sans) !important; letter-spacing: .08em; text-transform: uppercase; margin: 0 0 6px !important; padding-bottom: 8px; border-bottom: 2px solid currentColor; }
.proscons .pros h3 { color: var(--good); } .proscons .cons h3 { color: var(--warn); }
.proscons ul { list-style: none; padding: 0; margin: 0; }
.proscons li { padding: 9px 0; border-bottom: 1px solid var(--line); font-size: 14.5px; line-height: 1.5; margin: 0; }
.snapshot-table td.snap-field { width: 34%; font: 500 13.5px var(--sans); color: var(--ink-2); white-space: normal; }
.article .snapshot-table td:first-child { font-family: var(--sans); font-size: 13.5px; }
.snapshot-source { display: block; margin-top: 2px; font-size: 12px; color: var(--muted); }
.snapshot-source a { color: var(--muted); }
.est { font: 11px var(--mono); color: var(--warn); margin-left: 6px; white-space: nowrap; }
.off { font: 11px var(--mono); color: var(--good); margin-left: 6px; white-space: nowrap; }

/* toc */
.toc { position: sticky; top: 84px; align-self: start; font-size: 13.5px; max-height: calc(100vh - 110px); overflow: auto; }
.toc h2 { font: 600 11px var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }
.toc ul { list-style: none; margin: 0; padding: 0; border-left: 1px solid var(--line); }
.toc a { display: block; padding: 4px 0 4px 14px; margin-left: -1px; border-left: 2px solid transparent; color: var(--ink-2); text-decoration: none; line-height: 1.35; }
.toc a:hover { color: var(--ink); }
.toc a.on { color: var(--ink); font-weight: 600; border-left-color: var(--accent); }
.foot { border-top: 1px solid var(--line); padding: 24px 0 48px; font-size: 13px; color: var(--muted); }
.foot .wrap { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.foot a { color: var(--muted); }

@media (max-width: 960px) {
  .hero { grid-template-columns: minmax(0, 1fr); gap: 16px; padding-top: 36px; }
  .latest ol { grid-template-columns: 1fr; }
  .page-grid { grid-template-columns: minmax(0, 1fr); }
  .toc { display: none; }
  .topnav { display: none; }
  .search-btn { min-width: 0; flex: 1; }
  .ctable .col-region, .ctable .col-passport { display: none; }
  .progs li { grid-template-columns: 1fr; gap: 4px; }
  .proscons { grid-template-columns: 1fr; gap: 24px; }
  .monitor dl { grid-template-columns: 1fr; } .monitor dt { padding-bottom: 2px; }
}
@media (max-width: 620px) {
  .wrap { padding: 0 16px; }
  .ctable .col-fit, .ctable .col-date, .ctable .col-conf { display: none; }
  .search-btn kbd { display: none; }
  .search-btn { min-width: 0; }
  .explore { position: static; }
  .explore input[type=search] { width: 100%; }
  .facts div + div { border-left: 0; padding-left: 0; }
}
@media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
@media print { .topbar, .toc, .explore, .palette { display: none; } .page-grid { display: block; } body { background: #fff; } }
"""


# ── Site metadata ────────────────────────────────────────────────────────────

CAT_LABELS = OrderedDict([
    ("strong_passport", "Strong passport"),
    ("it_friendly", "IT-friendly"),
    ("clear_pathway", "Clear pathway"),
    ("popular_ru", "Popular with RU"),
    ("yacht_captain", "Yacht captain"),
])
REPO_URL = "https://github.com/MastPeace/residency-vault"

FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='6' fill='%231f5f4a'/%3E"
           "%3Cpath d='M9 24V8h8a5 5 0 0 1 0 10h-8m7 0 6 6' stroke='white' stroke-width='3' fill='none'/%3E%3C/svg%3E")


def parse_region_meta(filepath):
    """slug -> {region, categories} from regions.yaml."""
    meta = {}
    region = None
    for line in Path(filepath).read_text().split("\n"):
        m = re.match(r'^\s{2}(\w[\w_]*):\s*$', line)
        if m:
            region = m.group(1)
            continue
        m = re.match(r'^\s{4}-\s*\{country:\s*([\w-]+)(?:,\s*category:\s*\[([^\]]*)\])?', line)
        if m and region:
            cats = [c.strip() for c in (m.group(2) or "").split(",") if c.strip()]
            meta[m.group(1)] = {"region": region, "categories": cats}
    return meta


def display_name(title):
    return re.split(r"\s[—–-]\s", title, maxsplit=1)[0]


def cats_of(page, region_meta):
    cats = region_meta.get(page["slug"], {}).get("categories") or []
    if not cats:
        c = page.get("category") or []
        cats = c if isinstance(c, list) else [c]
    return [c for c in cats if c in CAT_LABELS]


def fm_scalar(page, key):
    v = page.get("frontmatter", {}).get(key, "")
    return v if isinstance(v, str) else ""


def snapshot_value(page, field_prefix):
    m = re.search(r'\|\s*' + re.escape(field_prefix) + r'[^|]*\|\s*([^|]*?)\s*\|', page["body"])
    return m.group(1).strip() if m else ""


def strip_md(s):
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', s)
    s = re.sub(r'\^\[[^\]]*\]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def years_to_citizenship(page):
    v = snapshot_value(page, "Years to citizenship")
    if not v:
        return None, ""
    low = v.lower()
    if low.startswith(("no ", "none", "not ")) or "no pathway" in low[:30]:
        return None, "no path"
    m = re.search(r'(\d+)(?:\s*[–-]\s*\d+)?\+?\s*(?:years?|yrs?|continuous|lawful|of)', v) or re.search(r'~?(\d+)', v)
    if not m:
        return None, ""
    return int(m.group(1)), f"{m.group(1)}{'+' if '+' in v[:m.end()+1] else ''} yr"


def passport_count(page):
    v = snapshot_value(page, "Passport strength")
    m = re.search(r'~?\b(\d{2,3})\b', v)
    if m and 20 <= int(m.group(1)) <= 200:
        return int(m.group(1))
    return None


def conf_html(level):
    n = {"low": 1, "medium": 2, "high": 3}.get((level or "").lower())
    if not n:
        return '<span class="none">—</span>'
    bars = "".join(f'<b class="{"on" if i < n else ""}"></b>' for i in range(3))
    return f'<span class="conf" title="Confidence: {level}"><i>{bars}</i>{level.capitalize()}</span>'


def first_sentences(text, limit=190):
    text = strip_md(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    p = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:p + 1] if p > 80 else cut.rsplit(" ", 1)[0] + "…")


def parse_status(page):
    """Return dict of Status section bullets {label: text}."""
    m = re.search(r'^## Status\s*\n(.*?)(?=^## |\Z)', page["body"], re.M | re.S)
    out = OrderedDict()
    if not m:
        return out
    for line in m.group(1).split("\n"):
        mm = re.match(r'^[-*]\s+(?:\*\*)?([^:*]+?)(?:\*\*)?\s*:\s*(?:\*\*)?\s*(.+)$', line.strip())
        if mm:
            key = mm.group(1).strip()
            if "change" in key.lower() and "recent" not in key.lower():
                key = "Recent changes"
            elif key.lower() == "watch":
                key = "Watch items"
            out[key] = mm.group(2).strip()
    return out


def inline_md(text):
    """Escape and render links / bold in a short markdown fragment."""
    t = html.escape(text)
    t = re.sub(r'\^\[[^\]]*\]', '', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', r'<a href="\2" rel="noopener">\1</a>', t)
    t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
    return t


# ── Page shell ───────────────────────────────────────────────────────────────

THEME_BOOT = ("<script>try{var t=localStorage.getItem('rv-theme');"
              "if(t)document.documentElement.dataset.theme=t}catch(e){}</script>")

SHELL_JS = r"""
(function () {
  var root = document.documentElement;
  var tb = document.getElementById('theme-btn');
  function isDark() { var t = root.dataset.theme; return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; }
  function sync() { tb.textContent = isDark() ? '☀' : '☾'; tb.setAttribute('aria-label', isDark() ? 'Switch to light theme' : 'Switch to dark theme'); }
  tb.addEventListener('click', function () {
    var n = isDark() ? 'light' : 'dark'; root.dataset.theme = n;
    try { localStorage.setItem('rv-theme', n); } catch (e) {} sync();
  }); sync();

  var pal = document.getElementById('palette'), inp = pal.querySelector('input'), list = pal.querySelector('ul');
  var idx = null, sel = 0, shown = [], base = document.body.dataset.base || '';
  function load(cb) {
    if (idx) return cb();
    fetch(base + 'search-index.json').then(function (r) { return r.json(); }).then(function (d) { idx = d; cb(); });
  }
  function render() {
    var q = inp.value.trim().toLowerCase();
    shown = idx.filter(function (e) {
      return !q || e.title.toLowerCase().indexOf(q) > -1 || (e.country_code || '').toLowerCase() === q || e.slug.indexOf(q) > -1;
    }).sort(function (a, b) {
      var as = a.title.toLowerCase().indexOf(q) === 0 ? 0 : 1, bs = b.title.toLowerCase().indexOf(q) === 0 ? 0 : 1;
      return as - bs || (a.type === b.type ? a.title.localeCompare(b.title) : (a.type === 'entity' ? -1 : 1));
    }).slice(0, 40);
    sel = 0;
    list.innerHTML = shown.length ? shown.map(function (e, i) {
      return '<li class="' + (i === 0 ? 'sel' : '') + '"><a href="' + base + e.url + '">' + e.title.replace(/</g, '&lt;') +
        '<small>' + (e.type === 'entity' ? (e.country_code || 'country') : 'program') + '</small></a></li>';
    }).join('') : '<li class="empty">No matches</li>';
  }
  function mark() { [].forEach.call(list.children, function (li, i) { li.classList.toggle('sel', i === sel); });
    var s = list.children[sel]; if (s && s.scrollIntoView) s.scrollIntoView({ block: 'nearest' }); }
  function open() { pal.classList.add('open'); inp.value = ''; load(function () { render(); inp.focus(); }); }
  function close() { pal.classList.remove('open'); }
  document.getElementById('search-btn').addEventListener('click', open);
  pal.addEventListener('mousedown', function (e) { if (e.target === pal) close(); });
  inp.addEventListener('input', render);
  inp.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, shown.length - 1); mark(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); mark(); e.preventDefault(); }
    else if (e.key === 'Enter' && shown[sel]) { location.href = base + shown[sel].url; }
  });
  document.addEventListener('keydown', function (e) {
    var typing = /INPUT|SELECT|TEXTAREA/.test((document.activeElement || {}).tagName || '');
    if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && !typing)) { e.preventDefault(); open(); }
    else if (e.key === 'Escape') close();
  });

  var toc = document.querySelectorAll('.toc a');
  if (toc.length && 'IntersectionObserver' in window) {
    var map = {}; [].forEach.call(toc, function (a) { map[a.getAttribute('href').slice(1)] = a; });
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (en) { if (en.isIntersecting) {
        [].forEach.call(toc, function (a) { a.classList.remove('on'); });
        var a = map[en.target.id]; if (a) a.classList.add('on');
      } });
    }, { rootMargin: '-80px 0px -70% 0px' });
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) io.observe(el); });
  }
})();
"""

INDEX_JS = r"""
(function () {
  var rows = [].slice.call(document.querySelectorAll('#ctable tbody tr'));
  var q = document.getElementById('f-q'), reg = document.getElementById('f-region'), conf = document.getElementById('f-conf');
  var chips = [].slice.call(document.querySelectorAll('.fchip')), cnt = document.getElementById('f-count');
  function apply() {
    var s = q.value.trim().toLowerCase(), on = chips.filter(function (c) { return c.getAttribute('aria-pressed') === 'true'; }).map(function (c) { return c.dataset.cat; });
    var n = 0;
    rows.forEach(function (r) {
      var cats = r.dataset.cats.split(' ');
      var ok = (!s || r.dataset.name.indexOf(s) > -1 || r.dataset.code === s) &&
        (!reg.value || r.dataset.region === reg.value) && (!conf.value || r.dataset.conf === conf.value) &&
        on.every(function (c) { return cats.indexOf(c) > -1; });
      r.hidden = !ok; if (ok) n++;
    });
    cnt.textContent = n + ' of ' + rows.length + ' countries';
  }
  chips.forEach(function (c) { c.addEventListener('click', function () {
    c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); apply(); }); });
  [q, reg, conf].forEach(function (el) { el.addEventListener('input', apply); });

  var ths = document.querySelectorAll('#ctable th[data-sort]'), tb = document.querySelector('#ctable tbody');
  [].forEach.call(ths, function (th) {
    th.querySelector('button').addEventListener('click', function () {
      var k = th.dataset.sort, dir = th.getAttribute('aria-sort') === 'ascending' ? -1 : 1, num = th.dataset.type === 'num';
      [].forEach.call(ths, function (t) { t.removeAttribute('aria-sort'); });
      th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
      rows.sort(function (a, b) {
        var x = a.dataset[k], y = b.dataset[k];
        if (num) { x = x === '' ? null : +x; y = y === '' ? null : +y;
          if (x === null && y === null) return 0; if (x === null) return 1; if (y === null) return -1; return (x - y) * dir; }
        return x.localeCompare(y) * dir;
      });
      rows.forEach(function (r) { tb.appendChild(r); });
    });
  });
  apply();
})();
"""


def shell(title, body, base, extra_js="", desc=""):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc or SITE_SUBTITLE)}">
<link rel="icon" href="{FAVICON}">
{THEME_BOOT}
<style>{CSS}</style>
</head>
<body data-base="{base}">
<header class="topbar"><div class="wrap">
  <a class="brand" href="{base}index.html">Residency<span>Vault</span></a>
  <nav class="topnav"><a href="{base}index.html#countries">Countries</a><a href="{base}index.html#programs">Programs</a><a href="{REPO_URL}">GitHub</a></nav>
  <span class="spacer"></span>
  <button class="search-btn" id="search-btn" type="button"><span>Search countries and programs</span><kbd>/</kbd></button>
  <button class="icon-btn" id="theme-btn" type="button" aria-label="Toggle theme">☾</button>
</div></header>
<div class="palette" id="palette" role="dialog" aria-label="Search"><div class="palette-box">
  <input type="text" placeholder="Country, code or program…" autocomplete="off" aria-label="Search"><ul></ul>
</div></div>
{body}
<footer class="foot"><div class="wrap"><span>Not legal advice. Conditions change — check the sources cited on each page.</span><span>Built {now} · <a href="{REPO_URL}">source</a></span></div></footer>
<script>{SHELL_JS}</script>
{extra_js}
</body>
</html>"""


# ── Page renderers ───────────────────────────────────────────────────────────

FACT_FIELDS = [
    ("Years to citizenship", "Years to citizenship"),
    ("Passport strength", "Passport"),
    ("Remote-work", "Remote-work visa"),
    ("Effective personal tax", "Tax, remote workers"),
    ("Monthly rent", "1-bed rent"),
    ("Main language", "Language"),
]


def build_facts(page):
    items = []
    for prefix, label in FACT_FIELDS:
        v = strip_md(snapshot_value(page, prefix))
        v = re.sub(r'\s*—?\s*\[?(hard/official|soft/estimate)\]?\s*$', '', v).strip()
        v = re.sub(r'\s*See\s+\[\[[^\]]*\]\].*$', '', v).strip()
        if prefix == "Passport strength":
            m = re.search(r'~?(\d{2,3})\s+(?:visa-free\s+)?(?:destinations|countries)?', v)
            v = f"{m.group(1)} visa-free" if m else v
        elif prefix.startswith("Effective personal tax"):
            v = re.split(r',\s*or\s|;|\sor\s', v)[0].strip()
        if v and v != "—" and len(items) < 5:
            items.append(f'<div><dt>{label}</dt><dd>{html.escape(v)}</dd></div>')
    return f'<dl class="facts">{"".join(items)}</dl>' if len(items) >= 3 else ""


def build_monitor(page):
    st = parse_status(page)
    if not st:
        return ""
    checked = st.get("Last monitored", "")
    rows = []
    for key, label in (("Recent changes", "Recent changes"), ("Watch items", "Watching")):
        if st.get(key):
            rows.append(f'<dt>{label}</dt><dd>{inline_md(st[key])}</dd>')
    if not rows:
        return ""
    stamp = f'<time>checked {html.escape(checked)}</time>' if checked else ""
    return f'<section class="monitor"><h2>Monitoring{stamp}</h2><dl>{"".join(rows)}</dl></section>'


def build_toc(body_html):
    items = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body_html)
    items = [(i, re.sub(r'<[^>]+>', '', t)) for i, t in items if i != "status"]
    if len(items) < 3:
        return ""
    lis = "".join(f'<li><a href="#{i}">{t}</a></li>' for i, t in items)
    return f'<aside class="toc"><h2>On this page</h2><ul>{lis}</ul></aside>'


def render_page(page, region_meta, region_labels):
    title = page["title"]
    name = display_name(title) if page["type"] == "entity" else title
    is_entity = page["type"] == "entity"
    cats = cats_of(page, region_meta) if is_entity else []

    body = page["html_body"]
    # status moves to the monitoring panel at the top
    monitor_html = build_monitor(page) if is_entity else ""
    if monitor_html:
        body = re.sub(r'<h2 id="status">.*?(?=<h2 |<div class="footnotes">|\Z)', '', body, flags=re.S)
    extra = (page.get("card_html") or "") + "\n" + (page.get("snapshot_html") or "")
    if extra.strip():
        marker = '<div class="footnotes">'
        body = body.replace(marker, extra + marker, 1) if marker in body else body + extra

    sub = []
    if page.get("country_code"):
        sub.append(f'<span class="code">{html.escape(page["country_code"])}</span>')
    reg = region_meta.get(page["slug"], {}).get("region")
    if reg:
        sub.append(f'<span>{html.escape(region_labels.get(reg, reg))}</span>')
    if page.get("confidence"):
        sub.append(conf_html(page["confidence"]))
    dates = []
    if page.get("updated"):
        dates.append(f'updated {html.escape(page["updated"])}')
    if page.get("last_checked"):
        dates.append(f'checked {html.escape(page["last_checked"])}')
    if dates:
        sub.append(f'<span class="dates">{" · ".join(dates)}</span>')
    chips = "".join(f'<span class="chip">{CAT_LABELS[c]}</span>' for c in cats)

    crumbs = '<a href="../index.html">Home</a><span class="sep">/</span>'
    crumbs += (f'<a href="../index.html#countries">Countries</a>' if is_entity
               else '<a href="../index.html#programs">Programs</a>')
    crumbs += f'<span class="sep">/</span><span>{html.escape(name)}</span>'

    head = f"""<div class="crumbs">{crumbs}</div>
<div class="page-head"><h1>{html.escape(name)}</h1>
<div class="sub">{"".join(sub)}</div>{f'<div class="chips">{chips}</div>' if chips else ''}</div>
{build_facts(page) if is_entity else ''}
{monitor_html}"""

    main = f"""<div class="wrap"><div class="page-grid">
<main class="main"><article>{head}<div class="article">{body}</div></article></main>
{build_toc(body)}
</div></div>"""
    return shell(f"{name} — {SITE_TITLE}", main, "../", desc=first_sentences(page["body"].split("\n## Residency")[0].replace("## Overview", ""), 160))


def render_index(region_meta, region_labels, concept_pages):
    countries = [p for p in all_pages.values() if p["type"] == "entity"]
    rows = []
    for p in sorted(countries, key=lambda p: display_name(p["title"])):
        name = display_name(p["title"])
        cats = cats_of(p, region_meta)
        reg = region_meta.get(p["slug"], {}).get("region", "")
        yrs, ylabel = years_to_citizenship(p)
        pp = passport_count(p)
        conf = (p.get("confidence") or "").lower()
        upd = p.get("last_checked") or p.get("updated") or ""
        fit = "".join(f'<span class="chip">{CAT_LABELS[c]}</span>' for c in cats)
        rows.append(
            f'<tr data-name="{html.escape(name.lower())}" data-code="{html.escape((p.get("country_code") or "").lower())}" '
            f'data-cats="{" ".join(cats)}" data-region="{reg}" data-conf="{conf}" '
            f'data-years="{yrs if yrs is not None else ""}" data-passport="{pp if pp else ""}" '
            f'data-confn="{ {"low":1,"medium":2,"high":3}.get(conf,"") }" data-date="{html.escape(upd)}">'
            f'<td class="name"><a href="conditions/{p["slug"]}.html">{html.escape(name)}</a></td>'
            f'<td class="cc">{html.escape(p.get("country_code") or "")}</td>'
            f'<td class="region col-region">{html.escape(region_labels.get(reg, ""))}</td>'
            f'<td class="fit col-fit">{fit}</td>'
            f'<td class="num">{ylabel if ylabel else "<span class=none>—</span>"}</td>'
            f'<td class="num col-passport">{pp if pp else "<span class=none>—</span>"}</td>'
            f'<td class="col-conf">{conf_html(conf)}</td>'
            f'<td class="date col-date">{html.escape(upd)}</td></tr>')

    def th(label, key, typ="text", cls=""):
        return f'<th data-sort="{key}" data-type="{typ}" class="{cls}"><button type="button">{label}</button></th>'

    used_regions = [r for r in region_labels if any(m["region"] == r for m in region_meta.values())]
    region_opts = "".join(f'<option value="{r}">{region_labels[r]}</option>' for r in used_regions)
    used_cats = [c for c in CAT_LABELS if any(c in cats_of(p, region_meta) for p in countries)]
    chip_btns = "".join(f'<button class="fchip" type="button" data-cat="{c}" aria-pressed="false">{CAT_LABELS[c]}</button>' for c in used_cats)

    # Latest monitoring: pages that carry a monitored date + real recent-changes text
    latest = []
    for p in countries:
        st = parse_status(p)
        rc = st.get("Recent changes", "")
        d = st.get("Last monitored", "")
        if rc and d and not rc.lower().startswith(("none", "no ", "n/a", "—")):
            latest.append((d, display_name(p["title"]), p["slug"], rc))
    latest.sort(key=lambda x: (x[0], x[1]), reverse=True)
    latest_html = ""
    if latest:
        lis = "".join(
            f'<li><time>{html.escape(d[5:] if len(d) >= 10 else d)}</time><div><a href="conditions/{s}.html">{html.escape(n)}</a> '
            f'<span>{html.escape(first_sentences(rc, 170))}</span></div></li>' for d, n, s, rc in latest[:8])
        latest_html = f'<section class="latest"><h2>Latest from monitoring</h2><ol>{lis}</ol></section>'

    progs = []
    for slug, p in concept_pages.items():
        summary = ""
        for line in p["body"].split("\n"):
            s = line.strip()
            if s and not s.startswith(("#", "|", "-", ">", "*")):
                summary = first_sentences(s, 200)
                break
        t = re.sub(r"\s+—\s+Cross-Country Comparison$", "", p["title"])
        progs.append(f'<li><a href="concepts/{slug}.html">{html.escape(t)}</a><p>{html.escape(summary)}</p></li>')

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    body = f"""<div class="wrap">
<section class="hero">
  <div><h1>Residency &amp; citizenship conditions</h1></div>
  <div><p>Residency and citizenship conditions for {len(countries)} countries: programs, thresholds, tax, years to a passport. Pages are monitored for changes and cite their sources.</p>
  <div class="stamp">{len(countries)} countries · {len(concept_pages)} program comparisons · built {now}</div></div>
</section>
<section id="countries">
<div class="explore"><div class="explore-row">
  <input id="f-q" type="search" placeholder="Filter by name or code" aria-label="Filter countries">
  <select id="f-region" aria-label="Region"><option value="">All regions</option>{region_opts}</select>
  <select id="f-conf" aria-label="Confidence"><option value="">Any confidence</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
  <span class="count" id="f-count"></span></div>
  <div class="explore-row" style="margin-top:10px">{chip_btns}</div></div>
<table class="ctable" id="ctable"><thead><tr>
 {th("Country", "name")}{th("Code", "code")}{th("Region", "region", cls="col-region")}<th class="col-fit">Fit</th>
 {th("To citizenship", "years", "num", "num")}{th("Passport", "passport", "num", "num col-passport")}{th("Confidence", "confn", "num", "col-conf")}{th("Checked", "date", cls="col-date")}
</tr></thead><tbody>{"".join(rows)}</tbody></table>
</section>
<section class="progs" id="programs"><h2 class="section-h">Program comparisons</h2><ul>{"".join(progs)}</ul></section>
</div>"""
    return shell(SITE_TITLE, body, "", extra_js=f"<script>{INDEX_JS}</script>")


def generate_search_index():
    index = []
    for slug, page in all_pages.items():
        if page["type"] == "entity":
            index.append({"slug": slug, "title": display_name(page["title"]), "country_code": page.get("country_code", ""),
                          "type": "entity", "url": f"conditions/{slug}.html"})
        else:
            index.append({"slug": slug, "title": re.sub(r"\s+—\s+Cross-Country Comparison$", "", page["title"]),
                          "country_code": "", "type": "concept", "url": f"concepts/{slug}.html"})
    return json.dumps(index, ensure_ascii=False, sort_keys=True)


# ── Main Build ───────────────────────────────────────────────────────────────

def build():
    print(f"Building static site: {SITE_TITLE}")
    collect_pages()
    region_meta = parse_region_meta(REGIONS_FILE)
    concept_pages = OrderedDict(sorted(((s, p) for s, p in all_pages.items() if p["type"] == "concept"), key=lambda x: x[0]))
    n_ent = sum(1 for p in all_pages.values() if p["type"] == "entity")
    print(f"   {n_ent} countries, {len(concept_pages)} concepts; region meta for {len(region_meta)}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    (OUTPUT_DIR / "conditions").mkdir(parents=True)
    (OUTPUT_DIR / "concepts").mkdir()
    count = 0
    for slug, page in all_pages.items():
        sub = "conditions" if page["type"] == "entity" else "concepts"
        (OUTPUT_DIR / sub / f"{slug}.html").write_text(render_page(page, region_meta, REGION_LABELS), encoding="utf-8")
        count += 1
    (OUTPUT_DIR / "index.html").write_text(render_index(region_meta, REGION_LABELS, concept_pages), encoding="utf-8")
    (OUTPUT_DIR / "search-index.json").write_text(generate_search_index(), encoding="utf-8")
    (OUTPUT_DIR / ".nojekyll").write_text("")
    print(f"Build complete: {count + 2} files written to {OUTPUT_DIR}")
    return count + 2


if __name__ == "__main__":
    build()
