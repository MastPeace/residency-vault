"""Russian UI strings for the static site generator (scripts/generate_site.py).

Everything the generator hard-codes in English goes through T(); pages' own text comes from i18n/ru/*.md
(see translate_ru.py). A string missing here falls back to English and is listed in the build log.
"""
import hashlib
import json
import re
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent.parent / "i18n" / "ru"

UI = {
    # navigation / shell
    "Home": "Главная", "Countries": "Страны", "Programs": "Программы", "Changes": "Изменения", "Glossary": "Глоссарий",
    "Search countries and programs": "Поиск по странам и программам",
    "Country, code or program…": "Страна, код или программа…", "Search": "Поиск",
    "News channel": "Канал с новостями", "News channel on Telegram": "Новостной канал в Telegram",
    "Toggle theme": "Сменить тему", "Menu": "Меню", "Light theme": "Светлая тема", "Dark theme": "Тёмная тема",
    "Switch to light theme": "Включить светлую тему", "Switch to dark theme": "Включить тёмную тему",
    "No matches": "Ничего не найдено", "country": "страна", "program": "программа",
    "Language": "Язык", "visa-free": "безвиз.",
    "footer": "Residency Radar · на базе базы знаний Residency Vault. Только обзорная информация — не юридическая, налоговая и не иммиграционная консультация. Условия меняются: сверяйтесь с официальными источниками, указанными на каждой странице.",
    "notice": ('<aside class="notice" role="note"><b>Только обзорная информация.</b> Эта страница — общая сводка, составленная '
               'по открытым источникам с помощью автоматизированных инструментов. Это <b>не юридическая, налоговая и не иммиграционная консультация</b>; '
               'сведения могут быть неполными или устаревшими. Правила, пороги и сборы часто меняются и применяются в каждом случае по-своему. '
               'Перед подачей документов или принятием решения проверьте информацию по официальным источникам, указанным на странице, '
               'и проконсультируйтесь с лицензированным специалистом.</aside>'),
    "untranslated": ('<aside class="notice" role="note"><b>Страница пока не переведена.</b> Показана английская версия — '
                     'русский перевод появится позже.</aside>'),
    # page head
    "residency & citizenship": "ВНЖ и гражданство", "updated": "обновлено", "checked": "проверено",
    "Strong passport": "Сильный паспорт", "IT-friendly": "Для IT", "Clear pathway": "Понятный путь",
    "Popular with RU": "Популярно у граждан РФ", "Yacht captain": "Яхтенный капитан",
    "High confidence": "Высокая достоверность", "Medium confidence": "Средняя достоверность", "Low confidence": "Низкая достоверность",
    "Confidence": "Достоверность", "High": "Высокая", "Medium": "Средняя", "Low": "Низкая",
    "On this page": "На странице", "Monitoring": "Мониторинг", "Recent changes": "Недавние изменения", "Watching": "Под наблюдением",
    "Change history": "История изменений", "All weekly changes →": "Все недельные изменения →",
    "Program types offered here": "Программы, доступные в стране", "compared": "— сравнение",
    "More countries in": "Ещё страны региона:", "this region": "этого региона", "Other residency program types": "Другие типы программ ВНЖ",
    # facts
    "Years to citizenship": "Лет до гражданства", "Passport": "Паспорт", "Remote-work visa": "Виза для удалёнки",
    "Tax, remote workers": "Налог, удалёнка", "1-bed rent / month": "Аренда 1-комн. / мес.", "Language": "Язык",
    # snapshot / card / extended
    "Country Snapshot": "Страна в цифрах", "Extended Snapshot": "Расширенные данные", "Country Card": "Карточка страны",
    "No data yet.": "Данных пока нет.", "Field": "Поле", "Value": "Значение", "Source": "Источник",
    "Strong points": "Сильные стороны", "Known problems": "Известные проблемы",
    "official": "офиц.", "estimate": "оценка",
    "official source": "официальный источник", "no verifiable source": "нет проверяемого источника",
    "estimate or secondary source — may be outdated": "оценка или вторичный источник — может быть устаревшим",
    "fields": "полей",
    "ext_legend": "✓ официальные данные &nbsp; ~ оценка или вторичный источник, может быть устаревшим &nbsp; ? не подтверждено · поля без надёжных данных скрыты",
    # regions / programs
    "Western Europe": "Западная Европа", "Eastern Europe": "Восточная Европа", "Balkans & Caucasus": "Балканы и Кавказ",
    "Middle East & Gulf": "Ближний Восток и Персидский залив", "North Africa": "Северная Африка", "West Africa": "Западная Африка",
    "East & South Africa": "Восточная и Южная Африка", "Latin America": "Латинская Америка",
    "Caribbean & Central America": "Карибы и Центральная Америка", "North America & Oceania": "Северная Америка и Океания",
    "Asia": "Азия", "Central Africa": "Центральная Африка",
    "Investment residency": "Инвестиционный ВНЖ", "Citizenship by investment": "Гражданство за инвестиции",
    "Passive income": "Пассивный доход", "Retired": "Пенсионеры", "Digital nomad": "Цифровой кочевник", "Employment": "Работа",
    "Highly skilled": "Квалифицированные специалисты", "Startup / entrepreneur": "Стартап / предприниматель",
    "Student": "Студенты", "Family": "Семья",
    # country list
    "Residency & Citizenship by Country: Compare 163 Countries | Residency Radar": "ВНЖ и гражданство по странам: сравнение 163 стран | Residency Radar",
    "Compare residency and citizenship conditions in 163 countries: programs, years to citizenship, passport strength, cost of living and tax for remote workers.":
        "Сравнение условий ВНЖ и гражданства в 163 странах: программы, срок до гражданства, сила паспорта, стоимость жизни и налоги для удалёнщиков.",
    "Residency Programs Compared: Golden Visa, Digital Nomad, Retirement & More | Residency Radar": "Программы ВНЖ: золотая виза, цифровой кочевник, пенсионный ВНЖ и другие | Residency Radar",
    "Ten residency and citizenship program types (investment, digital nomad, passive income, work, student, family and more), each compared across countries.":
        "Десять типов программ ВНЖ и гражданства (инвестиции, цифровой кочевник, пассивный доход, работа, учёба, семья и другие), каждый — в сравнении по странам.",
    "Filter by name or code": "Фильтр по названию или коду", "Filter countries": "Фильтр стран", "Region": "Регион",
    "All regions": "Все регионы", "Trust level": "Уровень доверия", "Any trust level": "Любой уровень доверия",
    "Country": "Страна", "Tags": "Метки", "Citizen yrs": "Лет до гражд.", "Visa-free": "Безвиз", "Cost idx": "Индекс цен",
    "Rent $/mo": "Аренда $/мес", "Invest min": "Мин. инвестиция", "Nomad visa": "Виза кочевника", "Tax %": "Налог %", "Trust": "Доверие",
    "What is": "Что такое", "Glossary →": "Глоссарий →",
    "countries_hero": "{n} стран: фильтруйте по региону или профилю, сортируйте по сроку до гражданства или силе паспорта.",
    "programs_hero": "{n} типов программ ВНЖ и гражданства, каждый — в сравнении по странам.",
    "tnote": '* Паспорт = число безвизовых направлений у паспорта, который вы получите после натурализации. Наведите на значение, чтобы увидеть цитату из источника; нажмите *, чтобы узнать, что значит колонка, или откройте <a href="glossary.html">глоссарий</a>.',
    "of_countries": "из", "countries_word": "стран",
    "Latest from monitoring": "Свежее из мониторинга",
    "Residency & citizenship conditions": "Условия ВНЖ и гражданства",
    "home_hero": "Условия ВНЖ и гражданства в {n} странах: программы, пороги, налоги, срок до паспорта. Страницы отслеживаются на изменения и ссылаются на источники.",
    "stamp": "{n} стран · {p} сравнений программ · собрано {now}",
    "card_countries": "{n} стран: условия, источники и мониторинг.", "card_programs": "{p} типов программ в сравнении по странам.",
    "card_glossary": "Что означают колонки, метки и аббревиатуры.",
    "HOME_TITLE": "Условия ВНЖ и гражданства в 163 странах | Residency Radar",
    "HOME_DESC": "Требования к ВНЖ и гражданству со ссылками на источники: золотые визы, цифровые кочевники, работа, пассивный доход, налоги. Обновляется еженедельно.",
    "Glossary — Residency & Citizenship Wiki": "Глоссарий — Residency Radar",
    "glossary_desc": "Что означают колонки, метки, уровни достоверности и аббревиатуры на Residency Radar: как читать страницы стран и типов программ и источники данных.",
    "Page not found": "Страница не найдена",
    "nf_lead": "Такой страницы нет или она переехала. Воспользуйтесь поиском (справа вверху) или начните отсюда:",
    "All countries": "Все страны", "Program types": "Типы программ", "Weekly changes": "Недельные изменения",
    "Page not found | Residency Radar": "Страница не найдена | Residency Radar",
    "Changes (English)": "Изменения (на английском)",
    # tooltips (TIPS)
    "tip_region": "Код региона; наведите для полного названия. Все коды — в глоссарии.",
    "tip_tags": "Редакционные метки: #pass сильный паспорт, #it для IT, #path понятный путь, #ru популярно у граждан РФ, #yacht яхтенный капитан.",
    "tip_progs": "Маршруты ВНЖ, которые есть в стране (закрытые и недоступные не показаны). Наведите на значок, чтобы увидеть название; кнопки выше фильтруют по программам.",
    "tip_years": "Лет легального проживания до подачи на гражданство по стандартному маршруту («нет пути» = маршрута нет).",
    "tip_passport": "Сила паспорта: число безвизовых направлений у паспорта, который вы получите после натурализации.",
    "tip_cost": "Индекс стоимости жизни Numbeo, Нью-Йорк = 100. Чем меньше, тем дешевле.",
    "tip_rent": "Типичная аренда 1-комнатной квартиры в месяц в долларах США по приблизительному курсу (чаще центр города).",
    "tip_gv": "Минимальная сумма инвестиционного маршрута ВНЖ в валюте, указанной на странице. Пусто: маршрут закрыт или сумма не указана.",
    "tip_rv": "ВНЖ для цифровых кочевников / удалённой работы. «Да» показывает основное требование к доходу в долларах США.",
    "tip_tax": "Эффективный диапазон подоходного налога для удалённого работника, в процентах. Только ориентир.",
    "tip_conf": "Уровень доверия: насколько страница подтверждена источниками (3 полоски = высокий, 2 = средний, 1 = низкий).",
    # seo
    "seo_country_title": "{name}: ВНЖ и гражданство, условия {year}",
    "seo_concept_title": "{base}: сравнение условий по странам",
    "Residency Radar": "Residency Radar",
}

LANG_SWITCH = {"en": "EN", "ru": "RU"}
CONCEPT_TITLE_SUFFIX_RU = " — Сравнение по странам"


def load_terms():
    p = I18N_DIR / "terms.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_names():
    p = I18N_DIR / "names.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def source_hash(text):
    """Hash of what a translation depends on: the English body + title, ignoring volatile metadata
    (frontmatter dates, 'Last monitored' stamp) that the weekly monitor rewrites on every page."""
    m = re.match(r"---\n.*?\n---\n", text, re.S)
    title = re.search(r"^title:\s*(.*)$", m.group(0), re.M).group(1) if m and re.search(r"^title:", m.group(0), re.M) else ""
    body = text[m.end():] if m else text
    body = re.sub(r"^\s*[-*]\s+\*\*Last monitored\*\*.*$", "", body, flags=re.M)
    return hashlib.sha1((title + "\n" + body.strip()).encode("utf-8")).hexdigest()
