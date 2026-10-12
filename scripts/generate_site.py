#!/usr/bin/env python3
"""
Static-site generator for the Residency & Citizenship Conditions Wiki.
Converts conditions/*.md + concepts/*.md into a dark-themed Wikipedia-style HTML site.
Pure Python 3 stdlib — no external dependencies.
"""

import os
import re
import urllib.parse
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


def fmt_source(s):
    """Source/confidence cell -> compact `domain-link badge`. Understands `[text](url)`, `^[url]`, bare urls,
    `[[#anchor]]` wikilinks and hard/official | soft/estimate | unsourced markers."""
    s = s or ''
    m = re.search(r'\[([^\]]+)\]\((https?://[^)\s]+)\)', s)
    label = url = None
    if m: label, url = m.group(1), m.group(2)
    else:
        m = re.search(r'(https?://[^\s\]\)]+)', s)
        if m: url = m.group(1)
    link = ''
    if url:
        host = re.sub(r'^www\.', '', re.sub(r'^https?://', '', url).split('/')[0])
        if not label or label.lower() in ('source', 'link'): label = host
        link = f'<a href="{html.escape(url)}" rel="noopener" title="{html.escape(url)}">{html.escape(label)}</a>'
    else:
        w = re.search(r'\[\[#([\w-]+)\]\]', s)
        if w: link = f'<a class="wikilink" href="#{w.group(1)}">{html.escape(w.group(1).replace("-", " "))}</a>'
    low = s.lower()
    if 'hard/official' in low: badge = '<span class="off" title="official source">&#10003;</span>'
    elif 'unsourced' in low: badge = '<span class="est unsrc" title="no verifiable source">?</span>'
    elif 'soft/estimate' in low: badge = '<span class="est" title="estimate or secondary source \u2014 may be outdated">~</span>'
    else: badge = ''
    return (link + ' ' + badge).strip()


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
        '<div class="snapshot-section ext-block-wrap">',
        '<h2 id="country-snapshot">Country Snapshot</h2>',
        '<div class="table-wrapper"><table class="snapshot-table ext-table">',
        '<thead><tr><th>Field</th><th>Value</th><th class="ext-src">Source</th></tr></thead>',
        '<tbody>'
    ]
    for field, value, source in rows:
        html_parts.append(f'<tr><td class="snap-field">{html.escape(field)}</td><td class="snap-value">{html.escape(value)}</td><td class="ext-src">{fmt_source(source)}</td></tr>')
    html_parts.append('</tbody></table></div></div>')
    return '\n'.join(html_parts)


def render_extended_html(section_text):
    """Extended Snapshot -> collapsible per-block cards (Block | Field | Value | Source table in markdown)."""
    m = re.search(r'Coverage:\s*(\d+)/(\d+)', section_text)
    cov = f'{m.group(1)}/{m.group(2)} fields' if m else ''
    blocks = {}
    for line in section_text.split('\n'):
        if not line.startswith('| ') or line.startswith('| Block') or line.startswith('|---'):
            continue
        cells = [c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
        if len(cells) < 4:
            continue
        blocks.setdefault(cells[0], []).append(cells[1:4])
    if not blocks:
        return None
    src = fmt_source
    parts = ['<div class="snapshot-section ext-snapshot">',
             '<h2 id="extended-snapshot">Extended Snapshot</h2>',
             f'<p class="ext-cov">{html.escape(cov)} &middot; &#10003; official &nbsp; ~ estimate or secondary source, may be outdated &nbsp; ? unverified &middot; fields without reliable data are hidden</p>']
    for i, (blk, rows) in enumerate(blocks.items()):
        have = sum(1 for r in rows if r[1] != 'No reliable data')
        if have == 0:
            continue
        parts.append(f'<details class="ext-block"{" open" if i == 0 else ""}><summary>{html.escape(blk)} <span class="ext-n">{have}/{len(rows)}</span></summary>')
        parts.append('<div class="table-wrapper"><table class="snapshot-table"><tbody>')
        for field, value, source in rows:
            if value == 'No reliable data':
                continue
            vh = html.escape(value)
            sh = src(source) if (source and source != '\u2014') else ''
            parts.append(f'<tr><td class="snap-field">{html.escape(field)}</td><td class="snap-value">{vh}</td><td class="ext-src">{sh}</td></tr>')
        parts.append('</tbody></table></div></details>')
    parts.append('</div>')
    return '\n'.join(parts)


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

REGION_LABELS.update({"asia": "Asia", "africa_central": "Central Africa"})
# regions.yaml groups were created per research wave; fold them into the display regions above.
# Keyed by country slug; only countries whose yaml group has no display label need an entry.
REGION_FOLD = {
    "eu_western": "andorra liechtenstein monaco san-marino",
    "eu_eastern": "belarus moldova ukraine",
    "africa_west": "benin burkina-faso gambia guinea liberia mauritania sierra-leone togo cabo-verde",
    "africa_central": "cameroon central-african-republic congo democratic-republic-of-congo equatorial-guinea gabon sao-tome",
    "africa_east_south": "angola mozambique zambia zimbabwe malawi lesotho madagascar djibouti comoros eswatini",
    "caribbean_central": "british-virgin-islands cayman-islands cuba dominica haiti st-lucia st-vincent trinidad-and-tobago turks-and-caicos",
    "asia": "china hong-kong india indonesia malaysia myanmar philippines sri-lanka taiwan thailand",
    "north_america_oceania": "fiji marshall-islands papua-new-guinea samoa solomon-islands tonga vanuatu",
    "latin_america": "guyana suriname venezuela",
    "middle_east_gulf": "lebanon",
}
FOLD_OF = {slug: reg for reg, slugs in REGION_FOLD.items() for slug in slugs.split()}

# ── Page Registry ────────────────────────────────────────────────────────────

# These are populated during collection
CONCEPT_SLUGS = set()
all_pages = {}  # slug -> {title, type, body, frontmatter, html_body, category, tags, ...}


def collect_pages():
    """Read all .md files from conditions/ and concepts/, parse frontmatter."""
    # Concepts first (to build CONCEPT_SLUGS) -- pre-register all so concept->concept links resolve
    CONCEPT_SLUGS.update(f.stem for f in CONCEPTS_DIR.glob("*.md"))
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
        body_noext, ext_text = extract_section(body, '## Extended Snapshot')
        extended_html = render_extended_html(ext_text) if ext_text else None
        clean_body, snapshot_html, card_html = extract_snapshot_card(body_noext)
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
            "extended_html": extended_html,
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
.brand .bn { color: inherit; display: block; }
.brand .bt { display: flex; flex-direction: column; gap: 3px; color: inherit; }
.brand .bs { font: 500 10.5px/1 var(--sans); color: var(--muted); letter-spacing: .02em; }
@media (max-width: 720px) { .brand .bs { display: none; } }
.brand { display: inline-flex; align-items: center; gap: 10px; }
.brand .logo { border-radius: 50%; box-shadow: 0 0 0 1.5px #c9953a; }
.brand .logo-dark { display: none; }
:root[data-theme="dark"] .brand .logo-light { display: none; }
:root[data-theme="dark"] .brand .logo-dark { display: inline-block; }
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) .brand .logo-light { display: none; }
  :root:not([data-theme="light"]) .brand .logo-dark { display: inline-block; }
}
.topnav { display: flex; gap: 20px; font-size: 14px; }
.topnav a { color: var(--ink-2); text-decoration: none; }
.topnav a:hover { color: var(--ink); text-decoration: underline; }
.topbar .spacer { flex: 1; }
.search-btn { display: flex; align-items: center; gap: 10px; min-width: 240px; height: 36px; padding: 0 10px 0 12px;
  background: var(--surface); border: 1px solid var(--line-strong); border-radius: 6px; color: var(--muted);
  font: 14px var(--sans); cursor: pointer; text-align: left; }
.search-btn .si { display: none; }
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

.explore { background: var(--bg); padding: 14px 0 12px; border-bottom: 1px solid var(--line); }
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
.qa-h span { font-weight: 400; text-transform: none; letter-spacing: 0; margin-left: 8px; }
.qa ul { margin: 0; padding: 0; list-style: none; }
.qa li { font: 400 15.5px/1.5 var(--serif); padding: 3px 0; }
.qa li b { font: 600 11px var(--sans); letter-spacing: .05em; text-transform: uppercase; color: var(--ink-2); margin-right: 8px; }
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
.est.unsrc { color: var(--bad, #c0392b); }
.ext-cov { font: 12px var(--mono); color: var(--muted); margin: -6px 0 12px; }
.ext-block { border: 1px solid var(--line); border-radius: 10px; margin: 10px 0; background: var(--paper, transparent); }
.ext-block > summary { cursor: pointer; padding: 12px 16px; font: 600 14px var(--sans); color: var(--ink); list-style: none; display: flex; justify-content: space-between; }
.ext-block > summary::-webkit-details-marker { display: none; }
.ext-block > summary::after { content: "+"; color: var(--muted); font-weight: 400; margin-left: 12px; }
.ext-block[open] > summary::after { content: "\2212"; }
.ext-block[open] > summary { border-bottom: 1px solid var(--line); }
.ext-n { font: 11px var(--mono); color: var(--muted); margin-left: auto; }
.ext-block .table-wrapper { margin: 0; }
.ext-none { color: var(--muted); font-style: italic; font-size: 13px; }
.ext-block .snapshot-table td.snap-field, .ext-table td.snap-field { width: 28%; }
.ext-table td.ext-src, .ext-table th.ext-src { width: 1%; white-space: nowrap; text-align: right; font: 12px var(--mono); color: var(--muted); padding-left: 16px; }
.ext-table td.ext-src a { color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--line); }
.ext-block .snapshot-table td.ext-src { width: 1%; white-space: nowrap; text-align: right; font: 12px var(--mono); color: var(--muted); padding-left: 16px; }
.ext-block .snapshot-table td.ext-src a { color: var(--muted); text-decoration: none; border-bottom: 1px dotted var(--line); }
.ext-block .snapshot-table td.ext-src a:hover { color: var(--ink); }
.ext-src .off, .ext-src .est { margin-left: 4px; font-size: 12px; }
@media (max-width: 640px) { .ext-block .snapshot-table td.ext-src { display: block; width: auto; text-align: left; padding: 0 0 10px; } .ext-block .snapshot-table td.snap-field { width: auto; } }

/* toc */
.toc { position: sticky; top: 84px; align-self: start; font-size: 13.5px; max-height: calc(100vh - 110px); overflow: auto; }
.toc h2 { font: 600 11px var(--sans); letter-spacing: .08em; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }
.toc ul { list-style: none; margin: 0; padding: 0; border-left: 1px solid var(--line); }
.toc a { display: block; padding: 4px 0 4px 14px; margin-left: -1px; border-left: 2px solid transparent; color: var(--ink-2); text-decoration: none; line-height: 1.35; }
.toc a:hover { color: var(--ink); }
.toc a.on { color: var(--ink); font-weight: 600; border-left-color: var(--accent); }
.flag { width: 20px; height: auto; max-height: 14px; object-fit: cover; border-radius: 2px; vertical-align: -2px; margin-right: 8px; box-shadow: 0 0 0 1px rgba(0,0,0,.12); }
.flag-lg { width: 28px; max-height: 20px; margin-right: 0; vertical-align: middle; }
.chg-lead { color: var(--muted); max-width: 62ch; }
.chg-weeks { list-style: none; padding: 0; margin: 20px 0 0; max-width: none; }
.chg-weeks li { display: flex; flex-direction: column; gap: 2px; padding: 14px 0; border-top: 1px solid var(--line); }
.chg-weeks span { color: var(--muted); font-size: 14px; }
.chg-list { list-style: none; padding: 0; margin: 20px 0; max-width: none; }
.chg-item { padding: 16px 0; border-top: 1px solid var(--line); }
.chg-item p { margin: 6px 0 0; }
.chg-h { font-size: 16px; }
.chg-h .flag { margin-right: 8px; }
.chg-imp { font: 600 11px var(--sans); text-transform: uppercase; letter-spacing: .06em; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--line); color: var(--muted); margin-left: 6px; }
.chg-high { color: #a33; border-color: #a33; }
.chg-src { font-size: 13px; margin-left: 4px; }
.chg-more { margin: 14px 0 0; font-size: 14px; }
.hist-list { list-style: none; padding: 0; margin: 0 0 8px; max-width: none; }
.hist-list li { margin: 4px 0; font-size: 14px; }
.hist-list time { font-family: var(--mono); font-size: 12px; color: var(--muted); margin-right: 8px; }
.h1-sub { font-size: 0.38em; font-weight: 400; color: var(--muted); letter-spacing: 0; white-space: nowrap; }
.related { margin: 40px 0 8px; }
.related .rel-h { font-size: 15px; margin: 0 0 10px; }
.related-list { list-style: none; padding: 0; margin: 0 0 18px; display: flex; flex-wrap: wrap; gap: 8px 10px; }
.related-list li { margin: 0; }
.related-list a { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid var(--line); border-radius: 999px; font-size: 13px; text-decoration: none; color: var(--ink); }
.related-list a:hover { border-color: var(--accent, #1f5b45); }
.related-list .flag { margin-right: 6px; }
.notice { margin: 16px 0; padding: 10px 14px; border: 1px solid var(--line); border-left: 3px solid var(--accent, #c9a227); border-radius: 6px; font-size: 13px; line-height: 1.5; color: var(--muted); }
.notice b { color: var(--ink-2, inherit); }
.foot { border-top: 1px solid var(--line); padding: 24px 0 48px; font-size: 13px; color: var(--muted); }
.foot .wrap { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.foot a { color: var(--muted); }
.ctable th a.gl { display: none; }
.ctable td.reg-cell { font: 12px var(--mono); color: var(--ink-2); white-space: nowrap; }
.ctable td.tags-cell { font: 12px var(--mono); color: var(--accent); white-space: nowrap; }
.ctable td.tags-cell span { margin-right: 6px; }
.ctable td.progs-cell { white-space: nowrap; font-size: 14px; letter-spacing: 0; }
.ctable thead th { position: sticky; top: 56px; z-index: 6; background: var(--bg); box-shadow: 0 1px 0 var(--line-strong); }
.ctable thead th:first-child { z-index: 8; }
.tscroll { overflow: visible; }
@media (max-width: 1240px) { .tscroll { overflow-x: auto; } .ctable thead th { position: static; } }
.ctable th:first-child, .ctable td:first-child { position: sticky; left: 0; z-index: 2; background: var(--bg); box-shadow: 1px 0 0 var(--line); }
.ctable tbody tr:hover td:first-child { background: var(--accent-soft); }
.ctable th, .ctable td { padding-left: 6px; padding-right: 6px; }
.ctable td.name { min-width: 110px; max-width: 170px; }
.ctable td.progs-cell .pi { cursor: default; }
.ctable td.col-rv, .ctable td.col-gv, .ctable td.col-cost { white-space: nowrap; font-size: 13px; }
.ctable th { position: relative; white-space: nowrap; vertical-align: middle; line-height: 1.2; font-size: 11px; letter-spacing: .02em; padding-top: 12px; padding-bottom: 12px; }
.ctable th button { text-align: left; }
.tip { position: relative; display: inline-block; }
.tip .gl { all: unset; cursor: pointer; color: var(--accent); font-weight: 700; font-size: 12px; padding: 0 0 0 2px; line-height: 1; }
.tip-box { display: none; position: absolute; top: 100%; left: -8px; z-index: 40; width: 250px; padding: 10px 12px; text-align: left;
  background: var(--surface); color: var(--ink-2); border: 1px solid var(--line-strong); border-radius: 8px; box-shadow: 0 10px 28px rgba(0,0,0,.18);
  font: 400 13px/1.45 var(--sans); letter-spacing: 0; text-transform: none; white-space: normal; }
.tip-r .tip-box { left: auto; right: -8px; }
.tip:hover .tip-box, .tip.open .tip-box, .tip:focus-within .tip-box { display: block; }
.tip-box a { color: var(--accent); white-space: nowrap; }
@media (max-width: 1180px) { .ctable .col-region { display: none; } }
@media (max-width: 960px) { .ctable .col-cost, .ctable .col-conf { display: none; } }
@media (max-width: 720px) { .ctable td.tags-cell, .ctable th:nth-child(3) { display: none; } }
@media (max-width: 720px) { .ctable .col-gv, .ctable .col-rv { display: none; } }
.tnote { margin: 14px 0 0; font-size: 13px; color: var(--muted); }
.ctable th a.gl { color: var(--accent); text-decoration: none; font-weight: 700; margin-left: 2px; }
.cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin: 8px 0 36px; }
.cards .card { display: flex; flex-direction: column; gap: 6px; padding: 18px 20px; border: 1px solid var(--line-strong); border-radius: 10px;
  background: var(--surface); text-decoration: none; color: var(--ink); }
.cards .card:hover { border-color: var(--accent); }
.cards .card b { font: 600 20px/1.2 var(--serif); }
.cards .card span { color: var(--ink-2); font-size: 14px; }
@media (max-width: 760px) {
  .cards { gap: 8px; margin: 0 0 28px; }
  .cards .card { padding: 12px 6px; text-align: center; align-items: center; justify-content: center; }
  .cards .card b { font-size: 16px; }
  .cards .card span { display: none; }
}
.tg-btn { display: inline-flex; align-items: center; gap: 7px; height: 36px; padding: 0 13px; border-radius: 6px; background: var(--accent);
  color: var(--accent-ink); font: 600 13px var(--sans); text-decoration: none; white-space: nowrap; }
.tg-btn:hover { filter: brightness(1.1); text-decoration: none; }
.topbar .wrap { gap: 12px; }
.topbar .brand { margin-right: 16px; }
.foot-r { display: inline-flex; align-items: center; gap: 14px; }
.foot-ic { display: inline-flex; color: var(--muted); }
.foot-ic:hover { color: var(--ink); }

.search-btn, .tg-btn, .icon-btn { flex-shrink: 0; }
.burger, .mnav { display: none; }
.mnav a, .mnav-theme { display: block; width: 100%; box-sizing: border-box; padding: 14px 4px; font: 500 17px var(--sans); color: var(--ink); text-decoration: none; text-align: left; background: none; border: 0; border-top: 1px solid var(--line); cursor: pointer; }
.mnav a:first-child { border-top: 0; }
.mnav-theme { color: var(--muted); }
@media (max-width: 960px) {
  .burger { display: inline-flex; align-items: center; justify-content: center; }
  #theme-btn { display: none; }
  .mnav { position: absolute; top: 100%; left: 0; right: 0; padding: 4px 16px 8px; background: var(--bg); border-bottom: 1px solid var(--line); box-shadow: 0 10px 24px rgba(0,0,0,.08); }
  .mnav.open { display: block; }
}
.brand { min-width: 0; }
.brand .bt { min-width: 0; overflow: hidden; }
.brand .bn { overflow: hidden; text-overflow: ellipsis; }
@media (max-width: 400px) {
  .topbar .wrap { gap: 8px; }
  .brand { gap: 8px; font-size: 16px; }
  .brand .logo { width: 30px; height: 30px; }
}
@media (max-width: 340px) { .brand .logo { display: none !important; } }
@media (max-width: 960px) {
  .hero { grid-template-columns: minmax(0, 1fr); gap: 16px; padding-top: 36px; }
  .latest ol { grid-template-columns: 1fr; }
  .page-grid { grid-template-columns: minmax(0, 1fr); }
  .toc { display: none; }
  .topnav { display: none; }
  .tg-btn span { display: none; } .tg-btn { width: 36px; padding: 0; justify-content: center; }
  .search-btn { min-width: 0; width: 36px; padding: 0; justify-content: center; gap: 0; flex: none; }
  .search-btn .si { display: block; }
  .search-btn span, .search-btn kbd { display: none; }
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
SITE_URL = "https://residencyradar.org/"
HOME_TITLE = "Residency & Citizenship Conditions for 163 Countries | Residency Radar"
HOME_DESC = ("Source-cited residency and citizenship requirements for 163 countries: golden visas, digital nomad, work and "
             "passive-income routes, years to citizenship, tax. Updated weekly.")
NOTICE_HTML = ('<aside class="notice" role="note"><b>Overview information only.</b> This page is a general summary compiled '
    'from public sources with the help of automated tools. It is <b>not legal, tax or immigration advice</b> and may be '
    'incomplete or out of date. Rules, thresholds and fees change often and are applied case by case. Always verify with the '
    'official sources cited on the page and consult a licensed professional before you apply or make a decision.</aside>')
TG_URL = "https://t.me/migrate_easy"


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
    for slug, m in meta.items():
        if m["region"] not in REGION_LABELS and slug in FOLD_OF:
            m["region"] = FOLD_OF[slug]
    return meta


FACTS_FILE = WIKI_DIR / "data" / "facts.json"
FACTS = json.loads(FACTS_FILE.read_text(encoding="utf-8")) if FACTS_FILE.exists() else {}
CUR_SYM = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CNY": "¥"}
# Approximate EUR per unit, used ONLY to sort the investment column; the page always shows the original currency.
EUR_RATE = {"EUR": 1, "USD": .92, "GBP": 1.17, "AED": .25, "CAD": .67, "AUD": .6, "NZD": .55, "CHF": 1.05,
            "SGD": .69, "HKD": .12, "JPY": .006, "CNY": .13, "THB": .027, "MYR": .2, "TRY": .022, "BHD": 2.45, "KWD": 3}


def money(cur, amount):
    sym = CUR_SYM.get(cur)
    n = f"{int(amount):,}"
    return f"{sym}{n}" if sym else f"{cur} {n}"


# Approximate USD per unit (2026 ballpark). Used to show every amount in dollars; the original is kept in the tooltip.
USD_RATE = {"USD": 1, "EUR": 1.09, "GBP": 1.27, "AED": .272, "CAD": .72, "AUD": .65, "NZD": .6, "CHF": 1.13,
            "SGD": .75, "HKD": .128, "JPY": .0067, "CNY": .14, "THB": .029, "MYR": .22, "TRY": .025, "BD": 2.65, "BHD": 2.65,
            "KWD": 3.25, "OMR": 2.6, "QAR": .275, "SAR": .267, "ARS": .0007, "AZN": .59, "BRL": .18, "COP": .00025,
            "F$": .44, "FJD": .44, "KYD": 1.2, "PEN": .27, "ZAR": .055, "KRW": .00072, "TWD": .031}


def usd(cur, amount):
    """(label, usd_value) for an amount; exact when already USD, otherwise ≈ with 2 significant digits."""
    r = USD_RATE.get(cur)
    if r is None:
        return money(cur, amount), None
    v = amount * r
    if cur == "USD":
        return f"${int(amount):,}", v
    mag = 10 ** (len(str(int(v))) - 2) if v >= 100 else 1
    return f"≈${int(round(v / mag) * mag):,}", v


def fact_gv(slug):
    f = (FACTS.get(slug) or {}).get("gv_min")
    if not f:
        return "", None, ""
    label, v = usd(f["currency"], f["amount"])
    orig = money(f["currency"], f["amount"])
    tip = f"{f.get('note', '')}: {f['evidence']}" + (f" (original: {orig})" if f["currency"] != "USD" else "")
    return label, v, tip


def fact_remote(slug):
    f = (FACTS.get(slug) or {}).get("remote_visa")
    if not f:
        return "", None, ""
    if not f["available"]:
        return "No", 0, f["evidence"]
    inc, mon = "", 1
    if f.get("min_income") and f.get("currency"):
        per = {"month": "/mo", "year": "/yr"}.get(f.get("period"), "")
        label, v = usd(f["currency"], f["min_income"])
        inc = f" · {label}{per}"
        if v is not None:
            mon = v / 12 if f.get("period") == "year" else v
    return f"Yes{inc}", mon, f["evidence"]


def fact_tax(slug):
    f = (FACTS.get(slug) or {}).get("remote_tax")
    if not f:
        return "", None, ""
    lo, hi = f["low_pct"], f["high_pct"]
    fmt = lambda x: f"{x:g}"
    return (f"{fmt(lo)}%" if lo == hi else f"{fmt(lo)}–{fmt(hi)}%"), lo, f["evidence"]


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


def flag_img(code, base, cls="flag"):
    c = (code or "").strip().lower()
    if not c or not (WIKI_DIR / "assets" / "flags" / f"{c}.png").exists():
        return ""
    return f'<img class="{cls}" src="{base}assets/flags/{c}.png" alt="" width="24" height="16" loading="lazy">'


def conf_html(level, compact=False):
    n = {"low": 1, "medium": 2, "high": 3}.get((level or "").lower())
    if not n:
        return '<span class="none">—</span>'
    bars = "".join(f'<b class="{"on" if i < n else ""}"></b>' for i in range(3))
    return f'<span class="conf" title="Confidence: {level}"><i>{bars}</i>{'' if compact else level.capitalize() + ' confidence'}</span>'


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
  var tb = document.getElementById('theme-btn'), tbm = document.getElementById('theme-btn-m');
  function isDark() { var t = root.dataset.theme; return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; }
  function sync() { tb.textContent = isDark() ? '☀' : '☾'; tb.setAttribute('aria-label', isDark() ? 'Switch to light theme' : 'Switch to dark theme'); if (tbm) tbm.textContent = isDark() ? 'Light theme' : 'Dark theme'; }
  function flip() {
    var n = isDark() ? 'light' : 'dark'; root.dataset.theme = n;
    try { localStorage.setItem('rv-theme', n); } catch (e) {} sync();
  }
  tb.addEventListener('click', flip); if (tbm) tbm.addEventListener('click', flip); sync();
  var mb = document.getElementById('menu-btn'), mn = document.getElementById('mnav');
  function menu(open) { mn.classList.toggle('open', open); mb.setAttribute('aria-expanded', open ? 'true' : 'false'); }
  mb.addEventListener('click', function (e) { e.stopPropagation(); menu(!mn.classList.contains('open')); });
  document.addEventListener('click', function (e) { if (!mn.contains(e.target)) menu(false); });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu(false); });

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
  var chips = [].slice.call(document.querySelectorAll('.fchip[data-cat]')), pchips = [].slice.call(document.querySelectorAll('.fchip[data-prog]')), cnt = document.getElementById('f-count');
  function apply() {
    var s = q.value.trim().toLowerCase(), on = chips.filter(function (c) { return c.getAttribute('aria-pressed') === 'true'; }).map(function (c) { return c.dataset.cat; });
    var pon = pchips.filter(function (c) { return c.getAttribute('aria-pressed') === 'true'; }).map(function (c) { return c.dataset.prog; });
    var n = 0;
    rows.forEach(function (r) {
      var cats = r.dataset.cats.split(' '), pr = r.dataset.progs.split(' ');
      var ok = (!s || r.dataset.name.indexOf(s) > -1 || r.dataset.code === s) &&
        (!reg.value || r.dataset.region === reg.value) && (!conf.value || r.dataset.conf === conf.value) &&
        on.every(function (c) { return cats.indexOf(c) > -1; }) &&
        pon.every(function (c) { return pr.indexOf(c) > -1; });
      r.hidden = !ok; if (ok) n++;
    });
    cnt.textContent = n + ' of ' + rows.length + ' countries';
  }
  chips.concat(pchips).forEach(function (c) { c.addEventListener('click', function () {
    c.setAttribute('aria-pressed', c.getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); apply(); }); });
  [q, reg, conf].forEach(function (el) { el.addEventListener('input', apply); });

  document.addEventListener('click', function (e) {
    var b = e.target.closest ? e.target.closest('.tip .gl') : null;
    [].forEach.call(document.querySelectorAll('.tip.open'), function (t) { if (!b || t !== b.parentNode) t.classList.remove('open'); });
    if (b) { b.parentNode.classList.toggle('open'); e.stopPropagation(); }
  });
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


def shell(title, body, base, extra_js="", desc="", ld=""):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc or SITE_SUBTITLE)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
{ld}
<link rel="icon" type="image/svg+xml" href="{base}assets/favicon.svg">
<link rel="icon" type="image/png" sizes="32x32" href="{base}assets/favicon-32.png">
<link rel="alternate icon" href="{base}assets/favicon.ico">
<link rel="apple-touch-icon" href="{base}assets/apple-touch-icon.png">
{THEME_BOOT}
<style>{CSS}</style>
</head>
<body data-base="{base}">
<header class="topbar"><div class="wrap">
  <a class="brand" href="{base}index.html"><img class="logo logo-light" src="{base}assets/logo-light.png" width="34" height="34" alt=""><img class="logo logo-dark" src="{base}assets/logo-dark.png" width="34" height="34" alt=""><span class="bt"><span class="bn">Residency<span>Radar</span></span><small class="bs">powered by Residency Vault</small></span></a>
  <nav class="topnav"><a href="{base}countries.html">Countries</a><a href="{base}programs.html">Programs</a><a href="{base}changes/index.html">Changes</a><a href="{base}glossary.html">Glossary</a></nav>
  <span class="spacer"></span>
  <button class="search-btn" id="search-btn" type="button" aria-label="Search countries and programs"><svg class="si" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><span>Search countries and programs</span><kbd>/</kbd></button>
  <a class="tg-btn" href="{TG_URL}" rel="noopener" title="News channel on Telegram"><svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M21.9 4.3 18.6 19.6c-.2 1-.9 1.3-1.7.8l-4.7-3.5-2.3 2.2c-.3.3-.5.5-1 .5l.3-4.8 8.7-7.9c.4-.3-.1-.5-.6-.2L6.5 13.4l-4.6-1.4c-1-.3-1-1 .2-1.5L20 3.5c.8-.3 1.6.2 1.9.8z"/></svg><span>News channel</span></a>
  <button class="icon-btn" id="theme-btn" type="button" aria-label="Toggle theme">☾</button>
  <button class="icon-btn burger" id="menu-btn" type="button" aria-label="Menu" aria-expanded="false" aria-controls="mnav"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div>
<nav class="mnav" id="mnav" aria-label="Menu"><a href="{base}countries.html">Countries</a><a href="{base}programs.html">Programs</a><a href="{base}changes/index.html">Changes</a><a href="{base}glossary.html">Glossary</a><button type="button" class="mnav-theme" id="theme-btn-m">Dark theme</button></nav>
</header>
<div class="palette" id="palette" role="dialog" aria-label="Search"><div class="palette-box">
  <input type="text" placeholder="Country, code or program…" autocomplete="off" aria-label="Search"><ul></ul>
</div></div>
{body}
<footer class="foot"><div class="wrap"><span>Residency Radar · powered by the Residency Vault knowledge base. Overview information only — not legal, tax or immigration advice. Conditions change; verify with the official sources cited on each page.</span><span class="foot-r">Built {now}<a class="foot-ic" href="{TG_URL}" rel="noopener" aria-label="Telegram channel" title="Telegram channel"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M21.9 4.3 18.6 19.6c-.2 1-.9 1.3-1.7.8l-4.7-3.5-2.3 2.2c-.3.3-.5.5-1 .5l.3-4.8 8.7-7.9c.4-.3-.1-.5-.6-.2L6.5 13.4l-4.6-1.4c-1-.3-1-1 .2-1.5L20 3.5c.8-.3 1.6.2 1.9.8z"/></svg></a><a class="foot-ic" href="{REPO_URL}" aria-label="Source on GitHub" title="Source on GitHub"><svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.22 1.88.87 2.34.66.07-.52.28-.87.5-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg></a></span></div></footer>
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
    ("Monthly rent", "1-bed rent / month"),
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


QA_ROWS = [("passive_income_residency", "Passive income / no work"), ("digital_nomad_visa", "Remote workers"),
           ("investment_residency", "Investment"), ("highly_skilled_employment", "Skilled workers"),
           ("startup_entrepreneur", "Founders"), ("retired_residency", "Retirees"),
           ("citizenship_by_investment", "Citizenship by investment")]
QA_MAX = 5
QA_MIN = 3   # minimum program rows for the block to appear


def _qa_cell(c):
    c = strip_md(re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), c))
    return c.strip()


def _qa_sources(page):
    """type-key -> first official URL from '### <type>' sections of '## Per-Program Detail'."""
    m = re.search(r"^## Per-Program Detail\s*\n(.*?)(?=^## )", page["body"], re.S | re.M)
    out = {}
    if not m:
        return out
    for blk in re.split(r"^### ", m.group(1), flags=re.M)[1:]:
        head, _, rest = blk.partition("\n")
        key = re.sub(r"[^a-z]+", "_", head.strip().lower()).strip("_")
        sm = re.search(r"\*\*Official source\*\*:\s*(.*)", rest)
        um = re.search(r"https?://[^\s)\]>,;]+", sm.group(1)) if sm else None
        if um:
            out[key] = um.group(0).rstrip(".")
    return out


def quick_answer_items(page):
    """Rows derived from the '## Residency Programs' table: [(label, program, conditions, duration)].
    Skips 'Not available' rows. Only text already on the page is used."""
    m = re.search(r"^## Residency Programs\s*\n(.*?)(?=^## )", page["body"], re.S | re.M)
    if not m:
        return []
    found = {}
    srcs = _qa_sources(page)
    for ln in m.group(1).splitlines():
        if not ln.startswith("|") or ln.startswith("|--") or ln.startswith("| Type"):
            continue
        ln = re.sub(r"\[\[([^\]|]+)\|[^\]]+\]\]", r"\1", ln)  # drop the pipe inside [[a|b]] before splitting cells
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        key = re.sub(r"[^a-z]+", "_", _qa_cell(cells[0]).lower()).strip("_")
        prog, cond, dur = _qa_cell(cells[1]), _qa_cell(cells[2]), _qa_cell(cells[3])
        if prog.lower().startswith("not available"):
            continue
        if cond in ("", "—") and not re.search(r"closed|terminated|suspended", prog, re.I):
            continue
        if re.search(r"\bsee \w+ above\b|does not grant (?:residen|permanent)", cond, re.I):
            continue
        found.setdefault(key, (prog, cond if cond != "—" else "", dur if dur not in ("—", "N/A") else "", srcs.get(key, "")))
    out, seen = [], set()
    for key, label in QA_ROWS:
        if key in found:
            sig = (found[key][0].lower(), found[key][1].lower())
            if sig in seen or found[key][0].lower() in {x[0] for x in seen}:
                continue  # same program listed under two types (e.g. Stamp 0 as passive income and retirement)
            seen.add(sig)
            out.append((label,) + found[key])
        if len(out) >= QA_MAX:
            break
    return out


def quick_answer_citizenship(page):
    y, lab = years_to_citizenship(page)
    if y:
        return f"{y} years of legal residence"
    return "No standard naturalisation path" if lab == "no path" else ""


def quick_answer_data(page):
    if page["type"] != "entity":
        return None
    rows = quick_answer_items(page)
    if len(rows) < QA_MIN:
        return None
    return {"rows": rows, "citizenship": quick_answer_citizenship(page),
            "checked": page.get("last_checked") or page.get("updated") or ""}


def _qa_line(label, prog, cond, dur, src=""):
    t = f"{prog}" + (f": {cond}" if cond else "")
    t = clip_words(t, 190)
    return t + (f" ({dur})" if dur and len(t) < 160 else "")


def quick_answer_text(page):
    """Plain-text list, used for the markdown twin and JSON-LD."""
    d = quick_answer_data(page)
    if not d:
        return ""
    lines = [f"- {l}: {_qa_line(l, p, c, du)}" + (f" [source: {src}]" if src else "") for l, p, c, du, src in d["rows"]]
    if d["citizenship"]:
        lines.append(f"- Citizenship by naturalisation: {d['citizenship']}")
    return "\n".join(lines)




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


def fix_inpage_anchors(doc):
    """Resolve in-page #anchors written as [[#employment-residency]] against real heading ids
    (ids use underscores / carry a title suffix; table-of-detail links use hyphens)."""
    ids = re.findall(r'\bid="([^"]+)"', doc)
    idset = set(ids)
    norm = lambda x: re.sub(r'[^a-z0-9]', '', x.lower())
    def fix(m):
        a = m.group(1)
        if a in idset:
            return m.group(0)
        n = norm(a)
        cand = [i for i in ids if norm(i) == n] or [i for i in ids if not i.startswith("fn") and norm(i).startswith(n)]
        return f'href="#{cand[0]}"' if cand else m.group(0)
    doc = re.sub(r'href="#([^"]+)"', fix, doc)
    # unresolved non-footnote anchors -> plain text instead of a dead link
    doc = re.sub(r'<a (?:class="wikilink" )?href="#([^"]+)"(?: class="footnote-back")?>([^<]*)</a>',
                 lambda m: m.group(0) if m.group(1) in idset else m.group(2), doc)
    return doc



SEO_SHORT = {
    "investment-residency": "investment", "citizenship-by-investment": "citizenship by investment",
    "passive-income-residency": "passive income", "retired-residency": "retirement",
    "digital-nomad-visa": "digital nomad", "employment-residency": "work permit",
    "highly-skilled-employment": "highly skilled", "startup-entrepreneur": "startup / business",
    "student-residency": "student", "family-reunification": "family",
}
SEO_LASTMOD = {}      # relative url -> ISO date, filled while rendering, read by seo_pass()


def clip_words(text, limit):
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:-– ")
    return cut + "…"


def seo_year(page):
    d = page.get("last_checked") or page.get("updated") or ""
    return d[:4] if re.match(r"\d{4}", d) else str(datetime.now(timezone.utc).year)


def seo_country(page, name):
    year = seo_year(page)
    title = f"{name} Residency & Citizenship Requirements {year}"
    if len(title) + 18 <= 62:
        title += " | Residency Radar"
    progs = [SEO_SHORT[x] for x in programs_of(page) if x in SEO_SHORT]
    ys = strip_md(snapshot_value(page, "Years to citizenship"))
    ys = re.split(r"[;(\[]", ys)[0].strip(" .—-")
    cit = f"citizenship after {ys}" if ys and len(ys) <= 24 and re.match(r"^~?\d", ys) and "year" in ys.lower() else ""
    tax = strip_md(snapshot_value(page, "Effective personal tax"))
    tax = re.split(r",\s*or\s|;|\sor\s|\(|\[", tax)[0].strip(" .—-")
    tx = f"remote-worker tax {tax}" if tax and len(tax) <= 22 and re.search(r"\d", tax) else ""
    checked = page.get("last_checked") or page.get("updated") or ""
    best = ""
    for n in (4, 3, 2, 1):
        for use_cit, use_tax in ((True, True), (True, False), (False, True), (False, False)):
            bits = ([f"routes: {', '.join(progs[:n])}"] if progs else []) + ([cit] if use_cit and cit else []) + ([tx] if use_tax and tx else [])
            cand = f"{name} residency — " + "; ".join(bits) + f". Sources cited, checked {checked}." if bits else ""
            if cand and len(cand) <= 158:
                best = cand
                break
        if best:
            break
    if not best:
        best = first_sentences(page["body"].split("\n## Residency")[0].replace("## Overview", ""), 155)
    return title, clip_words(best, 158)


def seo_concept(page, name):
    base = re.split(r"\s[—–-]\s", name, maxsplit=1)[0].strip()
    title = f"{base}: Requirements Compared Across Countries"
    if len(title) <= 52:
        title += " | Residency Radar"
    body = re.sub(r"^## .*$", "", page["body"], flags=re.M)
    first = strip_md(re.sub(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1).replace("-", " "), body.strip().split("\n\n")[0]))
    desc = clip_words(f"{first}", 158)
    return title, desc


def seo_ld(kind, url, name, desc, page=None, crumbs=()):
    org = {"@type": "Organization", "name": "Residency Radar", "url": SITE_URL,
           "logo": SITE_URL + "assets/logo-dark.png", "sameAs": [TG_URL, REPO_URL]}
    graph = []
    if kind == "home":
        graph += [org, {"@type": "WebSite", "name": "Residency Radar", "url": SITE_URL, "description": desc,
                        "publisher": {"@type": "Organization", "name": "Residency Radar"}}]
    else:
        item = {"@type": "Article" if page else "WebPage", "headline": name, "name": name, "description": desc,
                "url": url, "mainEntityOfPage": url, "inLanguage": "en", "publisher": {"@type": "Organization", "name": "Residency Radar", "url": SITE_URL}}
        if page:
            if page.get("created"): item["datePublished"] = page["created"]
            dm = page.get("updated") or page.get("last_checked")
            if dm: item["dateModified"] = dm
            item["author"] = {"@type": "Organization", "name": "Residency Radar", "url": SITE_URL}
            item["image"] = SITE_URL + "assets/og-card.png"
            qa = quick_answer_text(page)
            if qa: item["abstract"] = re.sub(r"^- ", "", qa, flags=re.M).replace("\n", " ")
        graph.append(item)
        if crumbs:
            graph.append({"@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE_URL + u} for i, (n, u) in enumerate(crumbs)]})
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def related_html(page, region_meta, region_labels, is_entity):
    items = []
    if is_entity:
        reg = region_meta.get(page["slug"], {}).get("region")
        peers = [p for sl, p in all_pages.items() if p["type"] == "entity" and sl != page["slug"]
                 and region_meta.get(sl, {}).get("region") == reg]
        peers.sort(key=lambda p: display_name(p["title"]))
        heading = f"More countries in {region_labels.get(reg, 'this region')}"
        items = [(f'{sl}.html', display_name(p["title"]), p.get("country_code")) for p in peers[:10] for sl in [p["slug"]]]
        progs = [(f'../concepts/{x}.html', PROG_ICONS[x][1]) for x in programs_of(page)]
        extra = ("<h2 class=\"rel-h\">Program types offered here</h2><ul class=\"related-list\">"
                 + "".join(f'<li><a href="{u}">{html.escape(n)} compared</a></li>' for u, n in progs) + "</ul>") if progs else ""
    else:
        heading = "Other residency program types"
        items = [(f'{sl}.html', p["title"].split(" — ")[0], None) for sl, p in all_pages.items() if p["type"] != "entity" and sl != page["slug"]]
        extra = ""
    if not items and not extra:
        return ""
    lis = "".join(f'<li><a href="{u}">{flag_img(cc, "../")}{html.escape(n)}</a></li>' for u, n, cc in items)
    return (f'<section class="related"><h2 class="rel-h">{html.escape(heading)}</h2><ul class="related-list">{lis}</ul>{extra}</section>') if items else f'<section class="related">{extra}</section>'


# ── Weekly changes (built from alerts/YYYY-MM-DD.md; only weeks that have changes are published) ──

ALERTS_DIR = WIKI_DIR / "alerts"
CHANGE_WEEKS = []          # [{date, items:[{country, slug, headline, text, impact, url}]}] newest first
CHANGES_BY_SLUG = {}       # slug -> [(date, headline)]


def _section(text, name):
    m = re.search(r"^## " + name + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    return m.group(1) if m else ""


def _clean_item_text(t):
    t = re.sub(r"\^\[[^\]]*\]", "", t)
    t = re.sub(r"\s*Source:.*$", "", t.strip())
    t = re.sub(r"\*\*|__", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip(" .:;")
    t = re.sub(r"^\(([^)]*)\):\s*(.*)$", lambda m: m.group(2) + f" ({m.group(1)})", t)
    return (t[:1].upper() + t[1:] + ".") if t else ""


def _src_of(raw):
    """(url, host) from a raw item text: ^[url], markdown link, bare url, or 'Source: domain'."""
    m = re.search(r"\^\[(https?://[^\]\s]+)\]", raw) or re.search(r"\]\((https?://[^)\s]+)\)", raw) or re.search(r"(https?://[^\s\])]+)", raw)
    if m:
        return m.group(1).rstrip(".,)"), ""
    m = re.search(r"Source:\s*([\w\-]+(?:\.[\w\-]+)+)", raw)
    return "", (m.group(1) if m else "")


def _headline_of(txt):
    if ": " in txt[:90]:
        h = txt.split(": ", 1)[0]
        r = txt.split(": ", 1)[1]
        return h, r[:1].upper() + r[1:]
    clause = re.split(r"\s\(|;|\.\s", txt, maxsplit=1)[0]
    return clip_words(clause, 80).rstrip(".…"), txt


def _country_slug(name):
    key = re.sub(r"[^a-z0-9]", "", name.lower())
    for sl, pg in all_pages.items():
        if pg["type"] == "entity" and (re.sub(r"[^a-z0-9]", "", display_name(pg["title"]).lower()) == key or re.sub(r"[^a-z0-9]", "", sl) == key):
            return sl
    return ""


def _mk_item(country, headline, text, impact="", url="", host=""):
    return {"country": country, "slug": _country_slug(country), "headline": headline.strip(" .:"), "text": text.strip(), "impact": impact, "url": url, "host": host}


def parse_alert_items(block):
    items = []
    # style B: numbered "1. **Country** — text"
    for m in re.finditer(r"^\d+\.\s+\*\*(.+?)\*\*\s+[—-]\s+(.*)$", block, re.M):
        country, body = m.group(1), m.group(2)
        url, host = _src_of(body)
        txt = _clean_item_text(body)
        head, rest = _headline_of(txt)
        items.append(_mk_item(country, head, rest, url=url, host=host))
    if items:
        return items
    # style A: "### Country[ — headline]" blocks with bullets
    for blk in re.split(r"^### ", block, flags=re.M)[1:]:
        title, _, rest = blk.partition("\n")
        country, _, headline = re.split(r"\s+[—-]\s+", title.strip(), 1) + [""] if False else (title.strip(), "", "")
        parts = re.split(r"\s+[—-]\s+", title.strip(), maxsplit=1)
        country = parts[0].strip(); headline = parts[1].strip() if len(parts) > 1 else ""
        bullets = re.findall(r"^- \*\*(.+?)\*\*:?\s*(.*)$", rest, re.M)
        labels = {b[0].strip().lower(): b[1].strip() for b in bullets}
        if "what" in labels:
            url, host = _src_of("Source: " + labels.get("source", "")) if False else _src_of(labels.get("source", "") or "")
            items.append(_mk_item(country, headline or "Update", _clean_item_text(labels["what"]), impact=labels.get("impact", "").split(" ")[0].strip(" —-,.:").lower(), url=url, host=host))
        else:
            for lab, val in bullets:
                if lab.strip().lower() in ("categories", "db", "source", "impact", "urgency"):
                    continue
                imp = re.search(r"Impact:\s*(\w+)", rest[rest.find(lab):rest.find(lab) + 600])
                u_, h_ = _src_of(val)
                items.append(_mk_item(country, lab, _clean_item_text(val), impact=imp.group(1).lower() if imp else "", url=u_, host=h_))
    return items


def load_changes():
    CHANGE_WEEKS.clear(); CHANGES_BY_SLUG.clear()
    if not ALERTS_DIR.is_dir():
        return
    for f in sorted(ALERTS_DIR.glob("20??-??-??.md"), reverse=True):
        t = f.read_text(encoding="utf-8")
        items = parse_alert_items(_section(t, "Changed")) + parse_alert_items(_section(t, "New"))
        if not items:
            m = re.search(r"^## Changed \((\d+)\)", t, re.M)
            if m and int(m.group(1)) > 0:
                print(f"   WARNING: {f.name} reports {m.group(1)} changes but none could be parsed (unknown format)")
            continue
        CHANGE_WEEKS.append({"date": f.stem, "items": items})
        for it in items:
            if it["slug"]:
                CHANGES_BY_SLUG.setdefault(it["slug"], []).append((f.stem, it["headline"]))


def _fmt_date(d):
    return datetime.strptime(d, "%Y-%m-%d").strftime("%-d %b %Y")


def _item_html(it):
    flag = ""
    pg = all_pages.get(it["slug"]) if it["slug"] else None
    if pg:
        flag = flag_img(pg.get("country_code"), "../")
    name = (f'<a href="../conditions/{it["slug"]}.html">{html.escape(it["country"])}</a>' if it["slug"] else html.escape(it["country"]))
    imp = f' <span class="chg-imp chg-{html.escape(it["impact"])}">{html.escape(it["impact"])} impact</span>' if it["impact"] in ("high", "medium", "low") else ""
    src = ""
    if it["url"]:
        host = re.sub(r"^www\.", "", re.sub(r"^https?://", "", it["url"]).split("/")[0])
        src = f' <a class="chg-src" href="{html.escape(it["url"])}" rel="noopener nofollow">Source: {html.escape(host)}</a>'
    if not src and it.get("host"):
        src = f' <span class="chg-src">Source: {html.escape(it["host"])}</span>'
    return (f'<li class="chg-item"><div class="chg-h">{flag}<b>{name}</b> — {html.escape(it["headline"])}{imp}</div>'
            f'<p>{html.escape(it["text"])}{src}</p></li>')


def render_changes_pages():
    """Returns {relative_filename: html}."""
    out = {}
    if not CHANGE_WEEKS:
        return out
    n = len(CHANGE_WEEKS)
    for w in CHANGE_WEEKS:
        d, items = w["date"], w["items"]
        countries = []
        for it in items:
            if it["country"] not in countries:
                countries.append(it["country"])
        title = f"Residency & Citizenship Changes, Week of {_fmt_date(d)}"
        lead = "; ".join(f'{it["country"]}: {it["headline"]}' for it in items[:3])
        desc = clip_words(f"{len(items)} verified change{'s' if len(items) != 1 else ''} in {', '.join(countries[:4])}. {lead}.", 158)
        body = (f'<div class="crumbs"><a href="../index.html">Home</a><span class="sep">/</span><a href="index.html">Changes</a><span class="sep">/</span><span>{_fmt_date(d)}</span></div>'
                f'<div class="page-head"><h1>Changes, week of {_fmt_date(d)}</h1>'
                f'<div class="sub"><span>{len(items)} update{"s" if len(items) != 1 else ""}</span><span>{len(countries)} countr{"ies" if len(countries) != 1 else "y"}</span></div></div>'
                f'<ul class="chg-list">{"".join(_item_html(it) for it in items)}</ul>'
                f'<p class="chg-more"><a href="index.html">← All weekly changes</a></p>{NOTICE_HTML}')
        main = f'<div class="wrap"><main class="main"><article>{body}</article></main></div>'
        url = f"{SITE_URL}changes/{d}.html"
        SEO_LASTMOD[f"changes/{d}.html"] = d
        ld = seo_ld("page", url, title, desc, crumbs=[("Home", ""), ("Changes", "changes/index.html"), (title, f"changes/{d}.html")])
        out[f"{d}.html"] = shell(f"{title} | Residency Radar" if len(title) < 46 else title, main, "../", desc=desc, ld=ld)
    rows = "".join(
        f'<li><a href="{w["date"]}.html"><b>Week of {_fmt_date(w["date"])}</b></a><span>{len(w["items"])} update{"s" if len(w["items"]) != 1 else ""}: '
        f'{html.escape(", ".join(dict.fromkeys(i["country"] for i in w["items"])))}</span></li>' for w in CHANGE_WEEKS)
    idx_title = "Residency & Citizenship Law Changes by Week | Residency Radar"
    idx_desc = "Weekly log of verified changes to residency and citizenship rules: golden visas, digital nomad visas, fees, thresholds and citizenship requirements."
    body = (f'<div class="crumbs"><a href="../index.html">Home</a><span class="sep">/</span><span>Changes</span></div>'
            f'<div class="page-head"><h1>Weekly changes</h1><div class="sub"><span>{n} week{"s" if n != 1 else ""} with changes</span></div></div>'
            f'<p class="chg-lead">What changed in residency and citizenship rules, week by week. Only changes that passed review are listed, each linked to the country page and its source.</p>'
            f'<ol class="chg-weeks">{rows}</ol>{NOTICE_HTML}')
    main = f'<div class="wrap"><main class="main"><article>{body}</article></main></div>'
    SEO_LASTMOD["changes/index.html"] = CHANGE_WEEKS[0]["date"]
    out["index.html"] = shell(idx_title, main, "../", desc=idx_desc, ld=seo_ld("page", SITE_URL + "changes/index.html", idx_title, idx_desc, crumbs=[("Home", ""), ("Changes", "changes/index.html")]))
    return out


def history_html(page):
    rows = CHANGES_BY_SLUG.get(page["slug"]) if page["type"] == "entity" else None
    if not rows:
        return ""
    lis = "".join(f'<li><a href="../changes/{d}.html"><time>{_fmt_date(d)}</time> {html.escape(h)}</a></li>' for d, h in rows[:8])
    return f'<section class="related"><h2 class="rel-h">Change history</h2><ul class="hist-list">{lis}</ul><p class="chg-more"><a href="../changes/index.html">All weekly changes →</a></p></section>'


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
    extra = (page.get("card_html") or "") + "\n" + (page.get("snapshot_html") or "") + "\n" + (page.get("extended_html") or "")
    if extra.strip():
        marker = '<div class="footnotes">'
        body = body.replace(marker, extra + marker, 1) if marker in body else body + extra

    sub = []
    if page.get("country_code"):
        sub.append(flag_img(page["country_code"], "../", "flag flag-lg") + f'<span class="code">{html.escape(page["country_code"])}</span>')
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
    crumbs += (f'<a href="../countries.html">Countries</a>' if is_entity
               else '<a href="../programs.html">Programs</a>')
    crumbs += f'<span class="sep">/</span><span>{html.escape(name)}</span>'

    head = f"""<div class="crumbs">{crumbs}</div>
<div class="page-head"><h1>{html.escape(name)}{'<span class="h1-sub"> residency &amp; citizenship</span>' if is_entity else ''}</h1>
<div class="sub">{"".join(sub)}</div>{f'<div class="chips">{chips}</div>' if chips else ''}</div>
{build_facts(page) if is_entity else ''}
{monitor_html}"""

    main = f"""<div class="wrap"><div class="page-grid">
<main class="main"><article>{head}<div class="article">{body}</div>{history_html(page)}{related_html(page, region_meta, region_labels, is_entity)}{NOTICE_HTML}</article></main>
{build_toc(body)}
</div></div>"""
    main = fix_inpage_anchors(main)
    sub_dir = "conditions" if is_entity else "concepts"
    seo_title, seo_desc = seo_country(page, name) if is_entity else seo_concept(page, name)
    url = f"{SITE_URL}{sub_dir}/{page['slug']}.html"
    SEO_LASTMOD[f"{sub_dir}/{page['slug']}.html"] = (page.get("updated") or page.get("last_checked") or "")[:10]
    crumbs = [("Home", ""), ("Countries" if is_entity else "Programs", "countries.html" if is_entity else "programs.html"),
              (name.split(" — ")[0], f"{sub_dir}/{page['slug']}.html")]
    ld = seo_ld("page", url, seo_title.replace(" | Residency Radar", ""), seo_desc, page=page, crumbs=crumbs)
    return shell(seo_title, main, "../", desc=seo_desc, ld=ld)


REGION_ABBR = {
    "eu_western": "EU-W", "eu_eastern": "EU-E", "balkans_caucasus": "BALK", "middle_east_gulf": "ME",
    "africa_north": "AF-N", "africa_west": "AF-W", "africa_central": "AF-C", "africa_east_south": "AF-ES",
    "latin_america": "LATAM", "caribbean_central": "CARIB", "north_america_oceania": "NA-OC", "asia": "ASIA",
}
CAT_TAGS = {"strong_passport": "#pass", "it_friendly": "#it", "clear_pathway": "#path",
            "popular_ru": "#ru", "yacht_captain": "#yacht"}

PROG_ICONS = OrderedDict([
    ("investment-residency", ("💰", "Investment residency")),
    ("citizenship-by-investment", ("🛂", "Citizenship by investment")),
    ("passive-income-residency", ("🏦", "Passive income")),
    ("retired-residency", ("🌴", "Retired")),
    ("digital-nomad-visa", ("💻", "Digital nomad")),
    ("employment-residency", ("💼", "Employment")),
    ("highly-skilled-employment", ("🧠", "Highly skilled")),
    ("startup-entrepreneur", ("🚀", "Startup / entrepreneur")),
    ("student-residency", ("🎓", "Student")),
    ("family-reunification", ("👨‍👩‍👧", "Family")),
])
_NA = re.compile(r"not available|not yet operational|\bclosed\b|\bsuspended\b|^\s*(?:n/?a|—|-)\s*$", re.I)


def programs_of(page):
    """Program types the country actually offers, from its Residency Programs table."""
    m = re.search(r"^## Residency Programs\s*\n(.*?)(?=^## |\Z)", page["body"], re.S | re.M)
    found = []
    for line in (m.group(1).split("\n") if m else []):
        if not line.startswith("|") or re.match(r"^\|[\s:|-]+\|?\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0].startswith("[[") and "]]" not in cells[0] and len(cells) > 1:
            cells = [cells[0] + "|" + cells[1]] + cells[2:]      # wikilink split by the pipe
        if len(cells) < 3:
            continue
        slug = re.sub(r"[\[\]]", "", cells[0]).split("|")[0].strip().lower().replace("_", "-")
        if slug not in PROG_ICONS or slug in found:
            continue
        if _NA.search(cells[1]) or _NA.search(cells[2]) or (len(cells) > 3 and _NA.search(cells[3])):
            continue
        found.append(slug)
    return found


_CUR_CODE = {"€": "EUR", "$": "USD", "US$": "USD", "£": "GBP"}
_MONEY = re.compile(r"((?:US)?[€$£]|\b[A-Z]{3}\b)\s?(\d[\d,]*)(?:\s?[–-]\s?(?:(?:US)?[€$£]|\b[A-Z]{3}\b)?\s?(\d[\d,]*))?")


def rent_usd(page):
    """(usd_mid, label, source_text) from the Monthly rent snapshot row; approximate rates."""
    v = strip_md(snapshot_value(page, "Monthly rent"))
    if not v or re.match(r"(no |n/a|—)", v, re.I):
        return None, "", ""
    m = _MONEY.search(v)
    if not m:
        return None, "", ""
    cur = _CUR_CODE.get(m.group(1), m.group(1))
    if cur not in EUR_RATE:
        return None, "", ""
    k = EUR_RATE[cur] / EUR_RATE["USD"]
    lo = float(m.group(2).replace(",", "")) * k
    hi = float(m.group(3).replace(",", "")) * k if m.group(3) else None
    r10 = lambda x: int(round(x / 10.0) * 10) if x >= 100 else int(round(x))
    label = f"${r10(lo):,}–{r10(hi):,}" if hi and r10(hi) != r10(lo) else f"${r10(lo):,}"
    return (lo + hi) / 2 if hi else lo, label, v


def cost_index(page):
    v = strip_md(snapshot_value(page, "Cost of living index"))
    if not v or re.match(r"(no |n/a|—)", v, re.I):
        return None, ""
    m = re.search(r"(\d+(?:\.\d+)?)(?:\s?[–-]\s?(\d+(?:\.\d+)?))?", v)
    if not m:
        return None, ""
    x = float(m.group(1))
    if m.group(2):
        x = (x + float(m.group(2))) / 2
    return (x, f"{x:.0f}") if 1 <= x <= 250 else (None, "")


TIPS = {
    "region": ("Region code; hover for the full name. All codes are listed in the glossary.", "region-codes"),
    "tags": ("Editorial tags: #pass strong passport, #it IT-friendly, #path clear pathway, #ru popular with RU, #yacht yacht captain.", "fit-tags"),
    "progs": ("Residency routes the country offers (closed or unavailable routes are left out). Hover an icon for its name; use the program buttons above to filter.", "program-types"),
    "years": ("Years of legal residence before you can apply for citizenship on the standard route ('no path' = none).", "country-list-columns"),
    "passport": ("Passport strength: number of visa-free destinations of the passport you would hold after naturalisation.", "country-list-columns"),
    "cost": ("Numbeo cost-of-living index with New York City = 100. Lower means cheaper.", "country-list-columns"),
    "rent": ("Typical monthly rent of a 1-bedroom apartment, shown in USD at approximate exchange rates (mostly city centre).", "country-list-columns"),
    "gv": ("Cheapest qualifying amount of the investment-residency route, in the currency the page states. Empty: route closed or no amount stated.", "country-list-columns"),
    "rv": ("Digital-nomad / remote-work residence. Yes shows the headline income requirement in USD.", "country-list-columns"),
    "tax": ("Effective personal income tax range for a remote worker, in percent. Indicative only.", "country-list-columns"),
    "conf": ("Trust level: how well the page is backed by sources (3 bars = high, 2 = medium, 1 = low).", "confidence"),
}


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
        reg_t = (f'<span title="{html.escape(region_labels.get(reg, ""), quote=True)}">{REGION_ABBR.get(reg, "")}</span>'
                 if REGION_ABBR.get(reg) else "")
        tags_t = " ".join(f'<span title="{CAT_LABELS[c]}">{CAT_TAGS[c]}</span>' for c in cats)
        progs_found = programs_of(p)
        icons = "".join(f'<span class="pi" title="{PROG_ICONS[x][1]}" aria-label="{PROG_ICONS[x][1]}">{PROG_ICONS[x][0]}</span>' for x in progs_found)
        gv_t, gv_n, gv_h = fact_gv(p["slug"])
        rv_t, rv_n, rv_h = fact_remote(p["slug"])
        tx_t, tx_n, tx_h = fact_tax(p["slug"])
        ci_n, ci_t = cost_index(p)
        rn_n, rn_t, rn_h = rent_usd(p)
        dash = '<span class="none">—</span>'
        ttl = lambda x: html.escape(x, quote=True)
        rows.append(
            f'<tr data-name="{html.escape(name.lower())}" data-code="{html.escape((p.get("country_code") or "").lower())}" '
            f'data-cats="{" ".join(cats)}" data-progs="{" ".join(progs_found)}" data-region="{reg}" data-conf="{conf}" '
            f'data-years="{yrs if yrs is not None else ""}" data-passport="{pp if pp else ""}" '
            f'data-confn="{ {"low":1,"medium":2,"high":3}.get(conf,"") }" '
            f'data-cost="{"" if ci_n is None else round(ci_n)}" data-rent="{"" if rn_n is None else round(rn_n)}" '
            f'data-gv="{round(gv_n) if gv_n else ""}" data-rv="{"" if rv_n is None else round(rv_n)}" data-tax="{"" if tx_n is None else tx_n}">'
            f'<td class="name">{flag_img(p.get("country_code"), "")}<a href="conditions/{p["slug"]}.html">{html.escape(name)}</a></td>'
            f'<td class="reg-cell">{reg_t or dash}</td>'
            f'<td class="tags-cell">{tags_t or dash}</td>'
            f'<td class="progs-cell">{icons or dash}</td>'
            f'<td class="num">{ylabel if ylabel else dash}</td>'
            f'<td class="num">{pp if pp else dash}</td>'
            f'<td class="num col-cost">{ci_t or dash}</td>'
            f'<td class="num col-cost" title="{ttl(rn_h)}">{html.escape(rn_t) or dash}</td>'
            f'<td class="num col-gv" title="{ttl(gv_h)}">{html.escape(gv_t) or dash}</td>'
            f'<td class="col-rv" title="{ttl(rv_h)}">{html.escape(rv_t) or dash}</td>'
            f'<td class="num col-cost" title="{ttl(tx_h)}">{html.escape(tx_t) or dash}</td>'
            f'<td class="col-conf">{conf_html(conf, True)}</td></tr>')

    def th(label, key, typ="text", cls="", tip=""):
        star = ""
        if tip:
            text, anchor = TIPS[tip]
            side = " tip-r" if "col-r" in cls else ""
            star = (f'<span class="tip{side}"><button class="gl" type="button" aria-label="What is {label}?">*</button>'
                    f'<span class="tip-box" role="tooltip">{text} <a href="glossary.html#{anchor}">Glossary →</a></span></span>')
        btn = f'<button type="button">{label}</button>' if key else label
        sort = f' data-sort="{key}" data-type="{typ}"' if key else ""
        return f'<th{sort} class="{cls}">{btn}{star}</th>'

    used_regions = [r for r in region_labels if any(m["region"] == r for m in region_meta.values())]
    region_opts = "".join(f'<option value="{r}">{region_labels[r]}</option>' for r in used_regions)
    used_cats = [c for c in CAT_LABELS if any(c in cats_of(p, region_meta) for p in countries)]
    chip_btns = "".join(f'<button class="fchip" type="button" data-cat="{c}" aria-pressed="false">{CAT_LABELS[c]}</button>' for c in used_cats)

    header_row = (th("Country", "name") + th("Region", "region", tip="region") + th("Tags", "", tip="tags")
                  + th("Programs", "", cls="", tip="progs")
                  + th("Citizen yrs", "years", "num", "num", tip="years")
                  + th("Visa-free", "passport", "num", "num", tip="passport")
                  + th("Cost idx", "cost", "num", "num col-cost", tip="cost")
                  + th("Rent $/mo", "rent", "num", "num col-cost", tip="rent")
                  + th("Invest min", "gv", "num", "num col-gv col-r", tip="gv")
                  + th("Nomad visa", "rv", "num", "col-rv col-r", tip="rv")
                  + th("Tax %", "tax", "num", "num col-cost col-r", tip="tax")
                  + th("Trust", "confn", "num", "col-conf col-r", tip="conf"))
    prog_chips = "".join(
        f'<button class="fchip" type="button" data-prog="{k}" aria-pressed="false" title="{n}">{e} {n}</button>'
        for k, (e, n) in PROG_ICONS.items())

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
        latest_html = f'<section class="latest"><h2>Latest from monitoring</h2><ol>{lis}</ol>{'<p class="chg-more"><a href="changes/index.html">All weekly changes →</a></p>' if CHANGE_WEEKS else ''}</section>'

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
    n_c, n_p = len(countries), len(concept_pages)
    explore = f"""<div class="explore"><div class="explore-row">
  <input id="f-q" type="search" placeholder="Filter by name or code" aria-label="Filter countries">
  <select id="f-region" aria-label="Region"><option value="">All regions</option>{region_opts}</select>
  <select id="f-conf" aria-label="Trust level"><option value="">Any trust level</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select>
  <span class="count" id="f-count"></span></div>
  <div class="explore-row" style="margin-top:10px">{chip_btns}</div>
  <div class="explore-row" style="margin-top:8px">{prog_chips}</div></div>"""
    table = f"""<table class="ctable" id="ctable"><thead><tr>
{header_row}
</tr></thead><tbody>{"".join(rows)}</tbody></table>
<p class="tnote">* Passport = number of visa-free destinations of the passport you would get after naturalisation. Hover a value to see the source quote; click a * to see what a column means, or open the <a href="glossary.html">glossary</a>.</p>"""
    countries_body = f"""<style>.wrap{{max-width:1400px}}</style><div class="wrap">
<section class="hero"><div><h1>Countries</h1></div><div><p>{n_c} countries: filter by region or fit, sort by years to citizenship or passport strength.</p></div></section>
<section id="countries">{explore}<div class="tscroll">{table}</div></section>
</div>"""
    programs_body = f"""<div class="wrap">
<section class="hero"><div><h1>Programs</h1></div><div><p>{n_p} residency and citizenship program types, each compared across countries.</p></div></section>
<section class="progs" id="programs"><ul>{"".join(progs)}</ul></section>
</div>"""
    cards = (f'<a class="card" href="countries.html"><b>Countries</b><span>{n_c} countries with conditions, sources and monitoring.</span></a>'
             f'<a class="card" href="programs.html"><b>Programs</b><span>{n_p} program types compared across countries.</span></a>'
             f'<a class="card" href="glossary.html"><b>Glossary</b><span>What the columns, labels and abbreviations mean.</span></a>')
    index_body = f"""<div class="wrap">
<section class="hero">
  <div><h1>Residency &amp; citizenship conditions</h1></div>
  <div><p>Residency and citizenship conditions for {n_c} countries: programs, thresholds, tax, years to a passport. Pages are monitored for changes and cite their sources.</p>
  <div class="stamp">{n_c} countries · {n_p} program comparisons · built {now}</div></div>
</section>
<section class="cards">{cards}</section>
{latest_html}
{NOTICE_HTML}
</div>"""
    return {
        "index.html": shell(HOME_TITLE, index_body, "", desc=HOME_DESC, ld=seo_ld("home", SITE_URL, HOME_TITLE, HOME_DESC)),
        "countries.html": shell("Residency & Citizenship by Country: Compare 163 Countries | Residency Radar", countries_body, "", extra_js=f"<script>{INDEX_JS}</script>", desc="Compare residency and citizenship conditions in 163 countries: programs, years to citizenship, passport strength, cost of living and tax for remote workers.", ld=seo_ld("page", SITE_URL + "countries.html", "Residency & Citizenship by Country", "Compare residency and citizenship conditions in 163 countries.", crumbs=[("Home", ""), ("Countries", "countries.html")])),
        "programs.html": shell("Residency Programs Compared: Golden Visa, Digital Nomad, Retirement & More | Residency Radar", programs_body, "", desc="Ten residency and citizenship program types (investment, digital nomad, passive income, work, student, family and more), each compared across countries.", ld=seo_ld("page", SITE_URL + "programs.html", "Residency Programs Compared", "Ten residency and citizenship program types compared across countries.", crumbs=[("Home", ""), ("Programs", "programs.html")])),
    }


def render_glossary():
    text = (WIKI_DIR / "glossary.md").read_text(encoding="utf-8")
    body = md_to_html(text, "concept", "glossary")
    crumbs = '<a href="index.html">Home</a><span class="sep">/</span><span>Glossary</span>'
    main = f"""<div class="wrap"><div class="page-grid">
<main class="main"><article><div class="crumbs">{crumbs}</div>
<div class="page-head"><h1>Glossary</h1></div><div class="article">{body}</div></article></main>
{build_toc(body)}
</div></div>"""
    return shell(f"Glossary — {SITE_TITLE}", main, "", desc="What the columns, labels, confidence levels and abbreviations on Residency Radar mean: how to read country pages, program types and data sources.")


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
    load_changes()
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
    for fname, doc in render_index(region_meta, REGION_LABELS, concept_pages).items():
        (OUTPUT_DIR / fname).write_text(doc, encoding="utf-8")
        count += 1
    (OUTPUT_DIR / "glossary.html").write_text(render_glossary(), encoding="utf-8")
    count += 1
    nf = (f'<div class="wrap"><main class="main"><article style="padding:48px 0 40px"><div class="page-head"><h1>Page not found</h1></div>'
          f'<p class="chg-lead">This page does not exist or has moved. Try search (top right) or start from one of these:</p>'
          f'<ul class="related-list"><li><a href="{SITE_URL}countries.html">All countries</a></li><li><a href="{SITE_URL}programs.html">Program types</a></li>'
          f'<li><a href="{SITE_URL}changes/index.html">Weekly changes</a></li><li><a href="{SITE_URL}index.html">Home</a></li></ul></article></main></div>')
    (OUTPUT_DIR / "404.html").write_text(shell("Page not found | Residency Radar", nf, SITE_URL, desc="Page not found.").replace('content="index,follow,max-image-preview:large,max-snippet:-1"', 'content="noindex"'), encoding="utf-8")
    count += 1
    changes = render_changes_pages()
    if changes:
        (OUTPUT_DIR / "changes").mkdir()
        for fn, doc in changes.items():
            (OUTPUT_DIR / "changes" / fn).write_text(doc, encoding="utf-8")
            count += 1
    (OUTPUT_DIR / "search-index.json").write_text(generate_search_index(), encoding="utf-8")
    (OUTPUT_DIR / ".nojekyll").write_text("")
    if (WIKI_DIR / "assets").is_dir():
        shutil.copytree(WIKI_DIR / "assets", OUTPUT_DIR / "assets")
    print(f"Build complete: {count + 1} files written to {OUTPUT_DIR}")
    return count + 1


def seo_pass():
    """Add canonical + Open Graph tags to every page; write sitemap.xml and robots.txt."""
    urls = []
    for f in sorted(OUTPUT_DIR.rglob("*.html")):
        rel = f.relative_to(OUTPUT_DIR).as_posix()
        if rel == "404.html":
            continue
        url = SITE_URL + ("" if rel == "index.html" else rel)
        doc = f.read_text(encoding="utf-8")
        t = re.search(r"<title>(.*?)</title>", doc, re.S)
        d = re.search(r'<meta name="description" content="(.*?)">', doc, re.S)
        tags = f'<link rel="canonical" href="{url}">\n<meta property="og:type" content="website">\n<meta property="og:site_name" content="Residency Radar">\n'
        if t: tags += f'<meta property="og:title" content="{t.group(1)}">\n'
        if d: tags += f'<meta property="og:description" content="{d.group(1)}">\n'
        tags += f'<meta property="og:url" content="{url}">\n<meta property="og:image" content="{SITE_URL}assets/og-card.png">\n<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n<meta name="twitter:card" content="summary_large_image">\n'
        md_alt = _md_alt_href(rel)
        if md_alt: tags += f'<link rel="alternate" type="text/markdown" href="{SITE_URL}{md_alt}">\n'
        if "rel=\"canonical\"" not in doc:
            f.write_text(doc.replace("</head>", tags + "</head>", 1), encoding="utf-8")
        urls.append(url)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    def lm(u):
        rel = u[len(SITE_URL):] or "index.html"
        d = SEO_LASTMOD.get(rel, "")
        return d if re.match(r"\d{4}-\d\d-\d\d$", d) else today
    body = "\n".join(f"  <url><loc>{u}</loc><lastmod>{lm(u)}</lastmod></url>" for u in urls)
    (OUTPUT_DIR / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{body}\n</urlset>\n', encoding="utf-8")
    ai = "\n".join(f"User-agent: {b}\nAllow: /\n" for b in AI_BOTS)
    (OUTPUT_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\n{ai}\nSitemap: {SITE_URL}sitemap.xml\n", encoding="utf-8")
    geo_pass()
    return len(urls)


AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot", "Claude-User",
           "PerplexityBot", "Perplexity-User", "Google-Extended", "Applebot-Extended", "Bingbot", "YandexBot", "CCBot"]


def _md_alt_href(rel):
    """Markdown twin of a rendered page (conditions/x.html -> conditions/x.md), or '' if none."""
    m = re.match(r"(conditions|concepts)/([^/]+)\.html$", rel)
    return f"{m.group(1)}/{m.group(2)}.md" if m and m.group(2) in all_pages else ""


def _md_clean(page):
    """Page as plain markdown: title header + freshness line + body (frontmatter dropped, sources kept)."""
    name = page["title"]
    if page["type"] == "entity":
        name = f"{display_name(name)} — Residency & Citizenship Conditions"
    fm = page.get("frontmatter", {})
    lines = [f"# {name}", ""]
    meta = [f"Source: {SITE_URL}{'conditions' if page['type'] == 'entity' else 'concepts'}/{page['slug']}.html"]
    if page.get("last_checked"): meta.append(f"Last checked: {page['last_checked']}")
    if page.get("updated"): meta.append(f"Last updated: {page['updated']}")
    lines += ["> " + " | ".join(meta), ""]
    qa = quick_answer_text(page)
    if qa:
        lines += ["## Quick answer", "", qa, ""]
    srcs = fm.get("sources") or []
    body = page["body"].strip() + "\n"
    if isinstance(srcs, list) and srcs:
        body += "\n## Official and primary sources\n" + "\n".join(f"- {u}" for u in srcs) + "\n"
    return "\n".join(lines) + "\n" + body


def geo_pass():
    """AI-search layer: markdown twins of every page, llms.txt (index), llms-full.txt (everything)."""
    countries = sorted((p for p in all_pages.values() if p["type"] == "entity"), key=lambda p: p["title"])
    concepts = sorted((p for p in all_pages.values() if p["type"] != "entity"), key=lambda p: p["title"])
    full = []
    for p in countries + concepts:
        sub = "conditions" if p["type"] == "entity" else "concepts"
        md = _md_clean(p)
        (OUTPUT_DIR / sub).mkdir(exist_ok=True)
        (OUTPUT_DIR / sub / f"{p['slug']}.md").write_text(md, encoding="utf-8")
        full.append(md)
    def line(p):
        sub = "conditions" if p["type"] == "entity" else "concepts"
        lc = p.get("last_checked") or p.get("updated") or ""
        return f"- [{display_name(p['title']) if p['type'] == 'entity' else p['title'].split(' — ')[0]}]({SITE_URL}{sub}/{p['slug']}.md)" + (f": checked {lc}" if lc else "")
    idx = ["# Residency Radar", "",
           "> Continuously monitored knowledge base of residency, citizenship and visa conditions for "
           f"{len(countries)} countries, with official sources and a weekly change digest. Each page states the date it was last verified.",
           "",
           "Facts are drawn from official government sources (linked at the bottom of every page). "
           "Check the 'Last checked' date before relying on a figure; rules change often.", "",
           "## Countries", *map(line, countries), "",
           "## Residency program types (cross-country comparisons)", *map(line, concepts), "",
           "## Optional",
           f"- [Full content of all pages in one file]({SITE_URL}llms-full.txt)",
           f"- [Weekly changes]({SITE_URL}changes/index.html)",
           f"- [Sitemap]({SITE_URL}sitemap.xml)", ""]
    (OUTPUT_DIR / "llms.txt").write_text("\n".join(idx), encoding="utf-8")
    (OUTPUT_DIR / "llms-full.txt").write_text("\n\n---\n\n".join(full), encoding="utf-8")


if __name__ == "__main__":
    build()
    print(f"SEO: canonical/OG on {seo_pass()} pages, sitemap.xml + robots.txt")
    # verbatim root files (search-engine verification etc.), copied AFTER seo_pass so their content stays untouched
    static = WIKI_DIR / "static"
    if static.is_dir():
        for f in static.iterdir():
            if f.is_file():
                shutil.copy(f, OUTPUT_DIR / f.name)
