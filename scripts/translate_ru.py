#!/usr/bin/env python3
"""Russian translation pipeline for the wiki (stdlib only; model: deepseek/deepseek-v4-pro via OpenRouter).

    python3 scripts/translate_ru.py portugal spain          # country pages by slug
    python3 scripts/translate_ru.py --top                   # the launch set (TOP_COUNTRIES + all concepts + glossary)
    python3 scripts/translate_ru.py --all                   # everything not yet translated
    python3 scripts/translate_ru.py --stale                 # re-translate only pages whose English source changed
    python3 scripts/translate_ru.py --names                 # (re)build i18n/ru/names.json for all countries
    python3 scripts/translate_ru.py --status                # what is translated / stale

Output: i18n/ru/{conditions,concepts}/<slug>.md, i18n/ru/glossary.md, i18n/ru/terms.json, i18n/ru/names.json.
Each translated file carries `source_hash` (sha1 of the English file) in its frontmatter; the site generator only uses
a translation whose hash matches the current English source, so stale text is never published.

What is translated: prose lines, list items, table cells. What is NOT: headings (kept English, mapped at render time via
terms.json so anchors/parsers keep working), URLs, [[wikilinks]], ^[citations], [text](url) links, numbers (validated),
Source/Confidence and Detail columns, slug-like cells. Every unit is validated (placeholders + digits must survive);
a unit that fails twice stays English and is reported.
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
I18N = ROOT / "i18n" / "ru"
MODEL = "deepseek/deepseek-v4-pro"
TOP_COUNTRIES = ["portugal", "spain", "italy", "greece", "malta", "austria", "estonia", "czechia", "germany", "uae",
                 "georgia", "serbia", "montenegro", "turkey", "armenia", "kazakhstan", "cyprus"]
BATCH = 40

GLOSSARY = """\
residence permit / residency = ВНЖ (вид на жительство) / резидентство; permanent residence = ПМЖ; citizenship = гражданство;
naturalisation = натурализация; golden visa = золотая виза; digital nomad visa = виза цифрового кочевника;
passive income = пассивный доход; investor / investment residency = инвестиционный ВНЖ; blue card = Голубая карта ЕС (EU Blue Card);
work permit = разрешение на работу; tax resident = налоговый резидент; non-dom = non-dom (оставь как есть);
visa-free = безвизовый; passport strength = сила паспорта; processing time = срок рассмотрения; minimum wage = минимальная зарплата;
dependents = иждивенцы; spouse = супруг(а); self-employed = самозанятый / ИП (по смыслу); startup visa = стартап-виза;
residence by descent = гражданство/ВНЖ по происхождению; Schengen = Шенген; "RU citizens" = граждане РФ."""

SYSTEM = f"""You are a professional translator of immigration and tax reference material from English into Russian.
You get a JSON object {{"id": "english text", ...}}. Return ONLY a JSON object with the same ids and the Russian translations.
Rules:
- Translate faithfully. Do not add, remove, soften or reinterpret any fact. No commentary, no marketing tone.
- Tokens like ⟦3⟧ are protected placeholders (URLs, links, citations). Copy each one exactly once, in a natural position.
- Keep every number, amount, percentage, date, currency symbol and code exactly as written (€920, 1.5×, 2026, AED 2,000,000, ≥, ~).
  Do not change digits; thousands/decimal separators are normalised afterwards, so write them however is natural.
- Keep official programme names, law names, agency names and acronyms in the original language/Latin script
  (D7, NLV, IFICI, AIMA, EU Blue Card, Golden Visa, Lei Orgânica 1/2026), adding a short Russian explanation only if the English text has one.
- Keep country and city names in standard Russian form. Keep Markdown markup (**bold**, _italic_) around the same words.
- Use these term choices consistently:
{GLOSSARY}
- Style: neutral, precise, concise Russian (reference handbook), same sentence structure as the source where possible.
- If a text is only a name, code or number, return it unchanged."""

TERMS_SYSTEM = f"""Translate short English headings, field names and labels of an immigration reference site into Russian.
Input: JSON object {{"id": "English label"}}. Output: ONLY a JSON object with the same ids and concise Russian labels
(title case like the source, no trailing punctuation). Keep acronyms (IT, UAE, RU, PR, FH, HDI, GDP) and names as is.
Term choices:
{GLOSSARY}"""

# deterministic seeds so the key headings are always identical across pages
TERMS_SEED = {
    "Overview": "Обзор", "Residency Programs": "Программы ВНЖ", "Per-Program Detail": "Подробно по программам",
    "Citizenship": "Гражданство", "Tax": "Налоги", "IT / Digital Nomad": "IT и цифровые кочевники",
    "Yacht / Maritime": "Яхтинг и морская сфера", "Notes for RU Citizens": "Заметки для граждан РФ",
    "Community Pulse": "Мнение сообщества", "Country Snapshot": "Страна в цифрах", "Extended Snapshot": "Расширенные данные",
    "Country Card": "Карточка страны", "Status": "Мониторинг", "General description": "Общее описание",
    "Well-known strong points": "Сильные стороны", "Well-known problems": "Известные проблемы",
    "Type": "Тип", "Official Program": "Официальная программа", "Key Conditions": "Ключевые условия", "Duration": "Срок",
    "Detail": "Подробнее", "Field": "Поле", "Value": "Значение", "Block": "Блок", "Source / Confidence": "Источник",
    "Source": "Источник",
    "investment_residency": "Инвестиционный ВНЖ", "citizenship_by_investment": "Гражданство за инвестиции",
    "passive_income_residency": "ВНЖ по пассивному доходу", "retired_residency": "ВНЖ для пенсионеров",
    "digital_nomad_visa": "Виза цифрового кочевника", "employment_residency": "ВНЖ по трудоустройству",
    "highly_skilled_employment": "Высококвалифицированные специалисты", "startup_entrepreneur": "Стартап и предпринимательство",
    "student_residency": "ВНЖ для студентов", "family_reunification": "Воссоединение семьи",
    "Official name": "Официальное название", "Conditions": "Условия", "Duration / renewal": "Срок и продление",
    "Path to citizenship": "Путь к гражданству", "Official source": "Официальный источник",
    "Community verdict": "Оценка сообщества", "Last monitored": "Последняя проверка", "Recent changes": "Недавние изменения",
    "Watch items": "На что смотреть", "Watch": "На что смотреть",
}

PROTECT = [
    re.compile(r"\^\[[^\]]*\]"),                       # ^[citation]
    re.compile(r"\[\[[^\]]*\]\]"),                     # [[wikilink]]
    re.compile(r"\[[^\]]*\]\(https?://[^)\s]+\)"),     # [text](url)
    re.compile(r"https?://[^\s)\]»⟧]+"),               # bare url
    re.compile(r"`[^`]+`"),                            # inline code
    re.compile(r"\b(?:hard/official|soft/estimate|unsourced|No reliable data)\b"),  # parsed markers
]
SKIP_COLS = re.compile(r"^(source.*|confidence|detail|type|slug|code)$", re.I)
SLUGLIKE = re.compile(r"^[\w\-\[\]#|/\s]*$")
LETTERS4 = re.compile(r"[A-Za-z]{2,}")


sys.path.insert(0, str(Path(__file__).resolve().parent))
from i18n_ru import source_hash as sha  # noqa: E402  (shared with generate_site.py)


def load_key():
    k = os.environ.get("OPENROUTER_API_KEY")
    if k:
        return k
    for line in open(os.path.expanduser("~/.hermes/.env"), encoding="utf-8"):
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip("\"'")
    sys.exit("OPENROUTER_API_KEY not found")


KEY = None
TERMS_LOCK = threading.Lock()
USAGE = {"cost": 0.0, "prompt": 0, "completion": 0}


def llm(system, payload, max_tokens=8000, retries=3):
    global KEY
    KEY = KEY or load_key()
    body = json.dumps({"model": MODEL, "temperature": 0.2, "max_tokens": max_tokens, "reasoning": {"enabled": False},
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]}).encode()
    last = None
    for a in range(retries):
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=240))
            u = r.get("usage") or {}
            USAGE["cost"] += u.get("cost", 0) or 0
            USAGE["prompt"] += u.get("prompt_tokens", 0)
            USAGE["completion"] += u.get("completion_tokens", 0)
            txt = (r["choices"][0]["message"]["content"] or "").strip()
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt)
            return json.loads(txt)
        except Exception as e:  # network / bad json -> retry
            last = e
            time.sleep(2 + 3 * a)
    raise RuntimeError(f"LLM failed: {last}")


# ── protection / validation ─────────────────────────────────────────────────

def protect(text):
    toks = []

    def sub(m):
        toks.append(m.group(0))
        return f"⟦{len(toks)}⟧"
    for rx in PROTECT:
        text = rx.sub(sub, text)
    return text, toks


def restore(text, toks):
    return re.sub(r"⟦(\d+)⟧", lambda m: toks[int(m.group(1)) - 1] if 0 < int(m.group(1)) <= len(toks) else m.group(0), text)


NUM = re.compile(r"\d{1,3}(?:[,\u00a0 ]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?")


def num_keys(tok):
    """Possible canonical values of a number token ('1,459' may be 1459 or 1.459, '1 424,50' is 1424.50)."""
    t = re.sub(r"[\u00a0 ]", "", tok)
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):
        keys = [t.replace(",", "")]
        if re.fullmatch(r"\d{1,3},\d{3}", t):          # ambiguous: thousands or a 3-digit decimal
            keys.append(t.replace(",", "."))
        return keys
    if re.fullmatch(r"\d+,\d+", t):
        return [t.replace(",", ".")]
    return [t]


def check(src, dst, ntok):
    """Validate a translated unit; return it with numbers rewritten exactly as in the source, or None if invalid."""
    found = re.findall(r"⟦(\d+)⟧", dst)
    if sorted(map(int, found)) != list(range(1, ntok + 1)):
        return None
    src_nums = NUM.findall(re.sub(r"⟦\d+⟧", "", src))
    parts = re.split(r"(⟦\d+⟧)", dst)           # never touch placeholders
    pool = {}
    for n in src_nums:
        pool.setdefault(num_keys(n)[0], []).append(n)
        for extra in num_keys(n)[1:]:               # source token itself ambiguous: also reachable by alt key
            pool.setdefault(extra, [])
    repl, left = {}, sum(len(v) for v in pool.values())

    def fix(m):
        nonlocal left
        for k in num_keys(m.group(0)):
            if pool.get(k):
                left -= 1
                return pool[k].pop(0)
        repl["bad"] = True
        return m.group(0)
    dst = "".join(p if p.startswith("⟦") else NUM.sub(fix, p) for p in parts)
    if repl or left:
        return None
    letters = re.findall(r"[A-Za-z]", src)
    if len(letters) > 25:  # real prose must come back translated (names/acronyms may stay Latin)
        cyr = len(re.findall(r"[А-Яа-яЁё]", dst))
        if cyr < 3 or (len(letters) > 80 and cyr < 0.35 * len(letters)):
            return None
    return dst


def worth_translating(text):
    t, _ = protect(text)
    t = re.sub(r"⟦\d+⟧", "", t)
    return bool(LETTERS4.search(t))


# ── markdown segmentation ───────────────────────────────────────────────────

def split_cells(line):
    return [c for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def extract_units(lines):
    """Return list of (line_idx, cell_idx_or_None, kind, text). kind: prose | term."""
    units = []
    in_code = False
    section = ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            i += 1
            continue
        if in_code or not s or s == "---":
            i += 1
            continue
        if s.startswith("#"):
            hm = re.match(r"^(#+)\s+(.*)$", s)
            if hm:
                if len(hm.group(1)) == 2:
                    section = hm.group(2).strip()
                units.append((i, None, "heading", hm.group(2).strip()))
            i += 1
            continue
        if s.startswith("|"):
            j = i
            while j < len(lines) and lines[j].strip().startswith("|"):
                j += 1
            header = [c.strip() for c in split_cells(lines[i])]
            skip = {k for k, h in enumerate(header) if SKIP_COLS.match(h)}
            term_cols = {k for k, h in enumerate(header) if h in ("Field", "Block")}
            if len(header) >= 4 and header[0] == "Block":
                term_cols = {0, 1}
            for r in range(i + 2, j):  # skip header + separator
                if re.match(r"^\|[\s:|-]+\|?\s*$", lines[r].strip()):
                    continue
                cells = split_cells(lines[r])
                for k, c in enumerate(cells):
                    c = c.strip()
                    if k in skip or not c or not worth_translating(c):
                        continue
                    if k == 0 and header[0].lower() in ("type",):
                        continue
                    if SLUGLIKE.match(c) and re.match(r"^[\w\-\[\]#|/]+$", c) and "_" in c:
                        continue
                    units.append((r, k, "term" if k in term_cols else "prose", c))
            i = j
            continue
        # list item / paragraph / blockquote / footnote
        m = re.match(r"^(\s*(?:[-*+]|\d+\.)\s+)(?:\*\*([^*]+?)\*\*\s*:|\*\*([^*]+?):\*\*)\s*(.*)$", ln)
        if m:
            label = (m.group(2) or m.group(3)).strip()
            if section != "Status" and worth_translating(label):
                units.append((i, "label", "term", label))
            rest = m.group(4)
            if rest and worth_translating(rest):
                units.append((i, "rest", "prose", rest))
        elif worth_translating(s):
            units.append((i, None, "prose", s))
        i += 1
    return units


# ── translation of units ────────────────────────────────────────────────────

def translate_terms(terms, cache):
    todo = [t for t in dict.fromkeys(terms) if t not in cache]
    for k in range(0, len(todo), 80):
        chunk = todo[k:k + 80]
        res = llm(TERMS_SYSTEM, {str(n + 1): t for n, t in enumerate(chunk)})
        for n, t in enumerate(chunk):
            v = res.get(str(n + 1))
            if isinstance(v, str) and v.strip():
                cache[t] = v.strip()


def translate_prose(texts):
    """texts: list[str] -> list[str|None] (None = failed validation, keep English)."""
    prot = [protect(t) for t in texts]
    out: list = [None] * len(texts)

    def run(idx_list):
        payload = {str(i): prot[i][0] for i in idx_list}
        try:
            res = llm(SYSTEM, payload)
        except Exception as e:
            print("   batch error:", e, file=sys.stderr)
            return
        for i in idx_list:
            v = res.get(str(i))
            fixed = check(prot[i][0], v, len(prot[i][1])) if isinstance(v, str) else None
            if fixed is not None:
                out[i] = restore(fixed, prot[i][1])

    batches = [list(range(k, min(k + BATCH, len(texts)))) for k in range(0, len(texts), BATCH)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(run, batches))
    for attempt in range(2):  # retry failures in small batches
        bad = [i for i, v in enumerate(out) if v is None]
        if not bad:
            break
        for k in range(0, len(bad), 8):
            run(bad[k:k + 8])
    # last resort for long units: translate sentence by sentence (shorter text validates more often)
    for i in [i for i, v in enumerate(out) if v is None and len(texts[i]) > 140]:
        sents = [x for x in re.split(r"(?<=[.;!?])\s+(?=[A-Z⟦*\[(\d])", texts[i]) if x.strip()]
        if len(sents) < 2:
            continue
        sub = translate_prose_flat(sents)
        if all(v is not None for v in sub):
            out[i] = " ".join(sub)
    return out


def translate_prose_flat(texts):
    """Single-level version of translate_prose (no sentence fallback) used by the fallback itself."""
    prot = [protect(t) for t in texts]
    out: list = [None] * len(texts)
    for k in range(0, len(texts), 8):
        idx = list(range(k, min(k + 8, len(texts))))
        for _ in range(2):
            todo = [i for i in idx if out[i] is None]
            if not todo:
                break
            try:
                res = llm(SYSTEM, {str(i): prot[i][0] for i in todo})
            except Exception:
                continue
            for i in todo:
                v = res.get(str(i))
                fixed = check(prot[i][0], v, len(prot[i][1])) if isinstance(v, str) else None
                if fixed is not None:
                    out[i] = restore(fixed, prot[i][1])
    return out


def load_json(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def save_json(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def translate_file(src_path, dst_path, kind, names):
    text = src_path.read_text(encoding="utf-8")
    h = sha(text)
    fm_end = text.find("\n---\n", 4) if text.startswith("---\n") else -1
    fm, body = (text[:fm_end + 5], text[fm_end + 5:]) if fm_end != -1 else ("", text)
    lines = body.split("\n")
    units = extract_units(lines)
    terms_path = I18N / "terms.json"
    need = [u[3] for u in units if u[2] in ("term", "heading")]
    with TERMS_LOCK:
        terms = load_json(terms_path, {})
        for k, v in TERMS_SEED.items():
            terms.setdefault(k, v)
        translate_terms(need, terms)
        save_json(terms_path, terms)

    prose = [u for u in units if u[2] == "prose"]
    tr = translate_prose([u[3] for u in prose])
    failed = sum(1 for v in tr if v is None)
    for (ln, col, k, txt), v in zip(prose, tr):
        if v is None:
            print(f"   kept English: {txt[:110]!r}", file=sys.stderr)

    # apply
    for (ln, col, k, txt), v in zip(prose, tr):
        if v is None:
            continue
        lines[ln] = apply(lines[ln], col, txt, v)
    for ln, col, k, txt in units:
        if k == "term" and txt in terms:
            lines[ln] = apply(lines[ln], col, txt, terms[txt])
    new_body = "\n".join(lines)

    # frontmatter: translate title, stamp hash
    title_m = re.search(r"^title:\s*(.*)$", fm, re.M)
    slug = src_path.stem
    if kind == "entity":
        ru_title = f"{names.get(slug, slug)} — Условия ВНЖ и гражданства"
    else:
        base = re.split(r"\s[—–-]\s", title_m.group(1).strip("'\""), maxsplit=1)[0] if title_m else slug
        with TERMS_LOCK:
            terms = load_json(terms_path, {})
            translate_terms([base], terms)
            save_json(terms_path, terms)
        ru_title = f"{terms.get(base, base)} — Сравнение по странам"
    if not fm:
        fm = f"---\ntitle: glossary\n---\n"
    if fm:
        fm = re.sub(r"^title:.*$", lambda m: f"title: {ru_title}", fm, count=1, flags=re.M)
        fm = fm.replace("\n---\n", f"\nsource_hash: {h}\nlang: ru\n---\n", 1) if fm.count("\n---\n") else fm
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(fm + new_body, encoding="utf-8")
    return len(units), len(prose), failed


def apply(line, col, old, new):
    if col is None:
        return line.replace(old, new, 1)
    if col in ("label", "rest"):
        return line.replace(old, new, 1)
    cells = re.split(r"(?<!\\)\|", line)
    # cells[0] is '' before the first pipe
    k = col + 1
    cells[k] = cells[k].replace(old, new, 1)
    return "|".join(cells)


def build_names(slugs_filter=None):
    names = load_json(I18N / "names.json", {})
    en = {}
    for f in sorted((ROOT / "conditions").glob("*.md")):
        t = f.read_text(encoding="utf-8")
        m = re.search(r"^title:\s*(.*)$", t, re.M)
        en[f.stem] = re.split(r"\s[—–-]\s", m.group(1).strip("'\""), maxsplit=1)[0] if m else f.stem
    todo = {s: n for s, n in en.items() if s not in names}
    sys_p = ("Translate English country/territory names into standard Russian short names (as used in Russian media, "
             "e.g. 'UAE' -> 'ОАЭ', 'Czechia' -> 'Чехия', 'Eswatini' -> 'Эсватини'). Input JSON {slug: English name}. "
             "Output ONLY JSON {slug: Russian name}.")
    items = list(todo.items())
    for k in range(0, len(items), 60):
        res = llm(sys_p, dict(items[k:k + 60]))
        for s, v in res.items():
            if isinstance(v, str) and v.strip():
                names[s] = v.strip()
    save_json(I18N / "names.json", names)
    return names


def status():
    rows = []
    for sub in ("conditions", "concepts"):
        for f in sorted((ROOT / sub).glob("*.md")):
            d = I18N / sub / f.name
            if d.exists():
                m = re.search(r"^source_hash:\s*(\w+)", d.read_text(encoding="utf-8"), re.M)
                rows.append((sub, f.stem, "ok" if m and m.group(1) == sha(f.read_text(encoding="utf-8")) else "STALE"))
    return rows


def main(argv):
    names = build_names()
    if "--names" in argv:
        print(f"names: {len(names)}")
        return
    if "--status" in argv:
        rows = status()
        print(f"{len(rows)} translated, {sum(r[2] == 'STALE' for r in rows)} stale")
        for r in rows:
            if r[2] != "ok":
                print(" ", r)
        return
    jobs = []  # (src, dst, kind)
    slugs = [a for a in argv if not a.startswith("--")]
    if "--top" in argv:
        slugs += TOP_COUNTRIES
        slugs += [f.stem for f in (ROOT / "concepts").glob("*.md")]
        jobs.append((ROOT / "glossary.md", I18N / "glossary.md", "concept"))
    if "--all" in argv:   # every country/concept without a fresh translation yet
        done = {(r[0], r[1]) for r in status() if r[2] == "ok"}
        for sub in ("conditions", "concepts"):
            slugs += [f.stem for f in sorted((ROOT / sub).glob("*.md")) if (sub, f.stem) not in done]
    if "--glossary" in argv:
        jobs.append((ROOT / "glossary.md", I18N / "glossary.md", "concept"))
    if "--stale" in argv:
        slugs += [r[1] for r in status() if r[2] == "STALE"]
    for s in dict.fromkeys(slugs):
        for sub, kind in (("conditions", "entity"), ("concepts", "concept")):
            p = ROOT / sub / f"{s}.md"
            if p.exists():
                jobs.append((p, I18N / sub / f"{s}.md", kind))
    if "--stale" in argv and (I18N / "glossary.md").exists():
        gl = (I18N / "glossary.md").read_text(encoding="utf-8")
        if f"source_hash: {sha((ROOT / 'glossary.md').read_text(encoding='utf-8'))}" not in gl:
            jobs.append((ROOT / "glossary.md", I18N / "glossary.md", "concept"))
    def one(job):
        src, dst, kind = job
        t = time.time()
        try:
            n, p, f = translate_file(src, dst, kind, names)
        except Exception as e:
            print(f"{src.relative_to(ROOT)}: FAILED {e}", flush=True)
            return
        print(f"{src.relative_to(ROOT)}: {n} units ({p} prose), {f} kept English, {time.time() - t:.0f}s, running cost ${USAGE['cost']:.3f}", flush=True)
    with ThreadPoolExecutor(max_workers=3) as ex:   # 3 files at a time, each file batches 4 requests
        list(ex.map(one, jobs))
    print(f"tokens in/out: {USAGE['prompt']}/{USAGE['completion']}, cost ${USAGE['cost']:.3f}")


if __name__ == "__main__":
    main(sys.argv[1:])
