#!/usr/bin/env python3
"""
i18n build stage for ExploreSuriname.

Runs AFTER generate.py. Reads the built English site and emits /nl/ and /es/
trees, and finalizes per-page hreflang/canonical on every tree (incl. English).

Translation comes only from the committed cache (translations.json); this stage
never calls the network, so the 15-min rebuild loop stays deterministic. Any
segment missing from the cache falls back to English, so the site never breaks.

Incremental: the NL/ES output for a page depends only on the raw English HTML,
translations.json, this file, and exploresuriname_listings.json (PROTECTED names).
i18n_build_cache.json records the md5 of each English page as generate.py emitted
it; on the next run, pages whose md5 is unchanged keep their existing /nl/ and
/es/ files instead of being re-parsed and re-translated. Any change to the three
global inputs invalidates the whole cache. English pages are ALWAYS re-finalized
(generate.py strips hreflang + the switcher every run), so the segment inventory
stays complete even on a fully cached run.

Usage:
    python3 build_i18n.py            # use cache (production / CI)
    python3 build_i18n.py --stub     # fake [nl]/[es] prefixes, no cache needed (dev)
    python3 build_i18n.py --only "index.html,restaurants.html"   # subset (dev)
    python3 build_i18n.py --jobs 1   # serial (default: one worker per CPU)
    python3 build_i18n.py --no-cache # force a full rebuild, ignore i18n_build_cache.json
"""
import json, re, sys, shutil, os, time, hashlib
from pathlib import Path
import multiprocessing
from bs4 import BeautifulSoup, NavigableString, Comment

ROOT     = Path(__file__).parent
SITE_URL = "https://exploresuriname.com"

def serialize(soup):
    """str(soup) but restore camelCase SVG attrs that lxml lowercases (viewBox)."""
    return str(soup).replace("viewbox=", "viewBox=")

# code -> (html lang attr, og:locale)
LANGS   = {"en": ("en", "en_US"), "nl": ("nl", "nl_NL"), "es": ("es", "es_ES")}
TARGETS = ["nl", "es"]                       # generated subtrees (en stays at root)

CACHE_FILE = ROOT / "translations.json"

# ── flags ────────────────────────────────────────────────────────────────────
STUB     = "--stub" in sys.argv
NO_CACHE = "--no-cache" in sys.argv
ONLY = None
JOBS = 0                                     # 0 = one worker per CPU
for i, a in enumerate(sys.argv):
    if a == "--only" and i + 1 < len(sys.argv):
        ONLY = set(sys.argv[i + 1].split(","))
    if a == "--jobs" and i + 1 < len(sys.argv):
        JOBS = max(1, int(sys.argv[i + 1]))

# ── do-not-translate dictionary (proper nouns from listings data) ─────────────
def load_protected():
    prot = set()
    try:
        data = json.load(open(ROOT / "exploresuriname_listings.json", encoding="utf-8"))
    except FileNotFoundError:
        return prot
    for b in data:
        for k in ("name", "address", "phone", "website", "email"):
            v = (b.get(k) or "").strip()
            if v:
                prot.add(v)
    return prot

PROTECTED = load_protected()

# Brand names that must never be machine-translated (news sources etc.).
# Keep in sync with BRANDS in translate_cache.py.
BRANDS_NO_TRANSLATE = {
    "Starnieuws", "De Ware Tijd", "Waterkant", "OilNow", "Offshore Energy",
    "Rigzone", "Google News", "Staatsolie",
}
PROTECTED |= BRANDS_NO_TRANSLATE

# District names are proper nouns. MT mangles the short ones — "Para" came back
# as "Par." in the NL district dropdowns on submit-business.html and
# submit-event.html. The posted <option value> was always correct, but the label
# the user reads was not.
DISTRICTS_NO_TRANSLATE = {
    "Paramaribo", "Wanica", "Commewijne", "Saramacca", "Nickerie",
    "Coronie", "Marowijne", "Para", "Brokopondo", "Sipaliwini",
}
PROTECTED |= DISTRICTS_NO_TRANSLATE

PHONE_RE = re.compile(r'^[\+\d][\d\s\-\(\)/]{5,}$')
CODE_RE  = re.compile(r'^[A-Z]{2,5}$')                 # currency/IATA codes
NUM_RE   = re.compile(r'^[\d\s.,:%–\-+/x×]+$')         # pure numeric/symbolic
URL_RE   = re.compile(r'^(https?://|www\.|@|#)')
TELLINE_RE = re.compile(r'^(?:Tel|Phone|WhatsApp)\.?:?\s*[\+\d][\d\s\-\(\)/]{5,}$', re.I)
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$')
SKIP_PARENTS = {"script", "style", "code", "kbd", "samp", "noscript", "svg"}
BRAND_RE = re.compile(r'items-baseline')      # the ExploreSuriname logo anchor

BRAND_WORDS = {"Explore", "Suriname", "ExploreSuriname"}
SERIF_RE = re.compile(r'serif')
def in_brand(node):
    # nav logo anchor
    if node.find_parent("a", class_=BRAND_RE) is not None:
        return True
    # serif wordmark parts ("Explore"/"Suriname") in nav or footer — keep brand intact.
    # (the hero is a single combined "Explore Suriname" string, so it is NOT matched)
    if str(node).strip() in BRAND_WORDS and node.find_parent(class_=SERIF_RE) is not None:
        return True
    return False

def no_translate(node):
    """
    Honour the standard HTML translate="no" attribute on any ancestor. Used by
    the marketplace: an ad page's chrome should appear in Dutch and Spanish, but
    the seller's own words must not go through MT (most are already Dutch, and
    round-tripping them produces nonsense).
    """
    return node.find_parent(attrs={"translate": "no"}) is not None


def translatable(s: str) -> bool:
    t = s.strip()
    if len(t) < 2:                 return False
    if not re.search(r'[A-Za-z]', t): return False
    if NUM_RE.match(t):            return False
    if PHONE_RE.match(t):          return False
    if TELLINE_RE.match(t):        return False   # "Tel: +597 123456"
    if EMAIL_RE.match(t):          return False
    if CODE_RE.match(t):           return False
    if URL_RE.match(t):            return False
    if t in PROTECTED:             return False
    return True

# ── translation cache: {source_text: {"nl": "...", "es": "..."}} ──────────────
cache = {}
if CACHE_FILE.exists():
    cache = json.load(open(CACHE_FILE, encoding="utf-8"))

# ── incremental build cache: {english page -> md5 of generate.py's output} ────
# Lives in data/ on purpose: update.yml already does `git add data/`, so the
# cache persists between CI runs without touching the workflow.
BUILD_CACHE_FILE = ROOT / "data" / "i18n_build_cache.json"

def _file_md5(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except OSError:
        return ""

def build_key() -> str:
    """Hash of everything that changes NL/ES output for an UNCHANGED English page.

    translations.json  -> the translations themselves
    build_i18n.py      -> switcher markup, hreflang, JSON-LD rules, this logic
    listings json      -> PROTECTED (business names/addresses never translated)

    If any of these moves, every page is rebuilt. That is the intended blunt
    instrument: a nav or template change also changes every English page, so the
    per-page hashes would all miss anyway.
    """
    h = hashlib.md5()
    for name in ("translations.json", "build_i18n.py", "exploresuriname_listings.json"):
        h.update(name.encode())
        h.update(_file_md5(ROOT / name).encode())
    h.update("|".join(sorted(TARGETS)).encode())
    return h.hexdigest()

def load_build_cache(key: str) -> dict:
    # --stub writes fake text into nl/es; never let that be recorded as current.
    if STUB or NO_CACHE:
        return {}
    try:
        data = json.loads(BUILD_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if data.get("key") != key:
        return {}
    return data.get("pages") or {}

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)*")
_IN_PLACE_RE = re.compile(r"(.{2,90}?) in (Paramaribo|Para|Suriname|Wanica|Nickerie|Commewijne|Lelydorp|"
                          r"Saramacca|Marowijne|Brokopondo|Coronie|Sipaliwini|Moengo|Albina)")
# ── Event dates and the short fact lines generate.py writes on event cards ────
# These change every day ("in 5 days", "Sat 3 Oct · 10pm"), so no cache key
# ever lasts. They are built from a small, fixed vocabulary, so they are
# localised by pattern instead. Anything not recognised falls back to English.
_EN_DAYS_S = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_EN_DAYS_L = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
_EN_MON_S  = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_EN_MON_L  = ["January", "February", "March", "April", "May", "June", "July", "August",
              "September", "October", "November", "December"]
_LOC = {
    "nl": {"ds": ["ma", "di", "wo", "do", "vr", "za", "zo"],
           "dl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
           "ms": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
           "ml": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus",
                  "september", "oktober", "november", "december"]},
    "es": {"ds": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
           "dl": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
           "ms": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
           "ml": ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                  "septiembre", "octubre", "noviembre", "diciembre"]},
}
_DS = "|".join(_EN_DAYS_S); _DL = "|".join(_EN_DAYS_L)
_MS = "|".join(_EN_MON_S);  _ML = "|".join(_EN_MON_L)
_TIME = r"\d{1,2}(?:[:.]\d{2})?\s?(?:[AaPp]\.?[Mm]\.?)?u?"


def _cap(t):
    return t[:1].upper() + t[1:]


def _loc_part(p, lang):
    """One ' · '-separated piece of an event date line, or None if unknown."""
    L = _LOC[lang]; es = lang == "es"
    ds = lambda d: L["ds"][_EN_DAYS_S.index(d)]
    dl = lambda d: L["dl"][_EN_DAYS_L.index(d)]
    ms = lambda m: L["ms"][_EN_MON_S.index(m)]
    ml = lambda m: L["ml"][_EN_MON_L.index(m)]
    m = re.fullmatch(rf"({_DS}) (\d{{1,2}}) ({_MS})", p)
    if m: return f"{ds(m[1])} {m[2]} {ms(m[3])}"
    m = re.fullmatch(rf"({_DS}) (\d{{1,2}}) – ({_DS}) (\d{{1,2}}) ({_MS})", p)
    if m: return f"{ds(m[1])} {m[2]} – {ds(m[3])} {m[4]} {ms(m[5])}"
    m = re.fullmatch(rf"({_DL}) (\d{{1,2}}) ({_ML}) (\d{{4}})", p)
    if m: return (f"{dl(m[1])} {m[2]} de {ml(m[3])} de {m[4]}" if es
                  else f"{dl(m[1])} {m[2]} {ml(m[3])} {m[4]}")
    m = re.fullmatch(rf"({_DS}) (\d{{1,2}}) to ({_DS}) (\d{{1,2}}) ({_ML}) (\d{{4}})", p)
    if m: return (f"{ds(m[1])} {m[2]} al {ds(m[3])} {m[4]} de {ml(m[5])} de {m[6]}" if es
                  else f"{ds(m[1])} {m[2]} t/m {ds(m[3])} {m[4]} {ml(m[5])} {m[6]}")
    m = re.fullmatch(rf"({_ML}) (\d{{4}})", p)
    if m: return _cap(f"{ml(m[1])} de {m[2]}" if es else f"{ml(m[1])} {m[2]}")
    m = re.fullmatch(rf"({_MS}) · ({_DS})", p)
    if m: return f"{ms(m[1])} · {ds(m[2])}"
    if re.fullmatch(_TIME, p):
        return p
    m = re.fullmatch(r"[Ii]n (\d+) days", p)
    if m: return ((f"en {m[1]} días" if es else f"over {m[1]} dagen") if p[0] == "i"
                  else (f"En {m[1]} días" if es else f"Over {m[1]} dagen"))
    fixed = {"today": ("vandaag", "hoy"), "tomorrow": ("morgen", "mañana"),
             "Today": ("Vandaag", "Hoy"), "Tomorrow": ("Morgen", "Mañana"),
             "happening now": ("nu bezig", "en curso"),
             "happening now, last day": ("nu bezig, laatste dag", "en curso, último día"),
             "Happening now, last day": ("Nu bezig, laatste dag", "En curso, último día"),
             "Featured": ("Uitgelicht", "Destacado"), "Daily": ("Dagelijks", "Diario")}
    if p in fixed:
        return fixed[p][1 if es else 0]
    m = re.fullmatch(rf"happening now, until ({_DS}) (\d{{1,2}}) ({_MS})", p)
    if m: return (f"en curso, hasta el {ds(m[1])} {m[2]} {ms(m[3])}" if es
                  else f"nu bezig, tot {ds(m[1])} {m[2]} {ms(m[3])}")
    m = re.fullmatch(rf"Every ((?:{_DL})|(?:{_DS})(?:–(?:{_DS}))?)(?:, next on (.+))?", p)
    if m:
        w = m[1]
        if "–" in w:
            a, b = w.split("–"); wl = f"{ds(a)}–{ds(b)}"
        elif w in _EN_DAYS_L:
            wl = dl(w)
        else:
            wl = ds(w)
        head = (f"Cada {wl}" if es else f"Elke {wl}")
        if m[2]:
            nxt = _loc_part(m[2], lang)
            if nxt is None:
                return None
            head += (f", el próximo: {nxt}" if es else f", volgende op {nxt}")
        return head
    return None


def localize_event_line(key, lang):
    """'Sat 3 Oct · 10pm', 'Saturday 3 October 2026 · in 5 days · De Dolfijn',
    'Every Monday, next on Mon 28 Sep · happening now, last day · Venue'.
    At least one piece must be a date; the last piece may be a venue name,
    which is kept (or translated if the cache has it)."""
    if lang not in _LOC:
        return None
    parts = key.split(" · ")
    out, dated = [], False
    for i, p in enumerate(parts):
        l = _loc_part(p, lang)
        if l is not None:
            out.append(l)
            if l != p or re.search(r"\d", p):
                dated = dated or bool(re.search(rf"{_DS}|{_DL}|{_MS}|{_ML}|days|today|tomorrow|happening|Every|Featured", p))
            continue
        e = cache.get(p)
        if e and e.get(lang):
            out.append(e[lang]); continue
        if i == len(parts) - 1 and i > 0:      # venue / place name: keep
            out.append(p); continue
        return None
    return " · ".join(out) if dated else None


_FACT_RE = [
    (re.compile(r"Starts (.+)"),            ("Begint om {0}", "Empieza a las {0}")),
    (re.compile(r"Starting (.+)"),          ("Vanaf {0}", "Desde las {0}")),
    (re.compile(r"Start (.+)"),             ("Begin {0}", "Inicio {0}")),
    (re.compile(r"Time: (.+)"),             ("Tijd: {0}", "Hora: {0}")),
    (re.compile(r"Doors open at (.+)"),     ("Deuren open om {0}", "Puertas abiertas a las {0}")),
    (re.compile(r"Entry (.+)"),             ("Toegang {0}", "Entrada {0}")),
    (re.compile(r"Organised by (.+)"),      ("Georganiseerd door {0}", "Organizado por {0}")),
    (re.compile(r"Free to attend"),         ("Gratis toegang", "Entrada gratuita")),
]


def localize_event_facts(key, lang):
    """'Starts 12:00. Entry SRD 450.00. Organised by X.' — every sentence must be
    one generate.py writes, otherwise None (English kept)."""
    if lang not in _LOC or not key.endswith("."):
        return None
    sents = [x.strip() for x in re.split(r"(?<=\.)\s+(?=[A-Z])", key) if x.strip()]
    out = []
    for snt in sents:
        body = snt[:-1] if snt.endswith(".") else snt
        for rx, (nl, es) in _FACT_RE:
            m = rx.fullmatch(body)
            if m:
                arg = m.group(1) if m.groups() else ""
                if rx.pattern.startswith(("Starts", "Starting", "Start ", "Time", "Doors")) and not re.search(r"\d", arg):
                    m = None
                    break
                out.append((es if lang == "es" else nl).format(arg) + ".")
                break
        else:
            m = None
        if m is None:
            return None
    return " ".join(out)




def tr(text: str, lang: str) -> str:
    """Translate a text node, preserving leading/trailing whitespace."""
    key = text.strip()
    lead = text[:len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    entry = cache.get(key)
    if entry and entry.get(lang):
        return lead + entry[lang] + trail
    # Strings with a count or date in them ("Browse 185 restaurants…",
    # "109 of 109 products shown") change whenever the number does, so an exact
    # key never lasts. A cache key written with {#} for each number matches any
    # numbers; they are put back in the same order.
    nums = _NUM_RE.findall(key)
    if nums:
        tmpl = cache.get(_NUM_RE.sub("{#}", key))
        if tmpl and tmpl.get(lang) and tmpl[lang].count("{#}") == len(nums):
            out = tmpl[lang]
            for n in nums:
                out = out.replace("{#}", n, 1)
            return lead + out + trail
    if lang in _LOC:
        ev = localize_event_line(key, lang) or localize_event_facts(key, lang)
        if ev:
            return lead + ev + trail
    # "<Business> in Paramaribo" (image alt text on every listing card)
    m = _IN_PLACE_RE.fullmatch(key)
    if m and lang == "es" and not re.search(
            r"\b(?:is|are|was|a|an|the|of|and|with|for|to|serves|offers|runs|near|from)\b", m.group(1)):
        place = "Surinam" if m.group(2) == "Suriname" else m.group(2)
        return lead + m.group(1) + " en " + place + trail
    # Category cards show a listing's description cut short with "…". The full
    # description is translated (the listing page uses it), so translate that
    # and cut the translation at the same relative point.
    if key.endswith("…") and len(key) > 40:
        pre = key[:-1].rstrip()
        full = _prefix_key(pre)
        if full and cache[full].get(lang):
            t = cache[full][lang]
            cut = max(20, int(len(t) * len(pre) / max(1, len(full))))
            if cut < len(t):
                sp = t.rfind(" ", 0, cut)
                t = t[:sp if sp > 20 else cut].rstrip(" ,;:-–—") + "…"
            return lead + t + trail
    if STUB:
        return lead + f"[{lang}] " + key + trail
    return text   # English fallback


_SORTED_KEYS = None


def _prefix_key(pre: str):
    """Shortest cache key that starts with *pre* (and is longer than it)."""
    global _SORTED_KEYS
    import bisect
    if _SORTED_KEYS is None:
        _SORTED_KEYS = sorted(cache)
    i = bisect.bisect_left(_SORTED_KEYS, pre)
    best = None
    while i < len(_SORTED_KEYS) and _SORTED_KEYS[i].startswith(pre):
        k = _SORTED_KEYS[i]
        if len(k) > len(pre) and (best is None or len(k) < len(best)):
            best = k
        i += 1
    return best

# ── collect every translatable source segment (for translate_cache.py) ────────
def collect_segments(soup) -> set:
    segs = set()
    for node in soup.find_all(string=True):
        if type(node) is not NavigableString:         continue  # skip Doctype/Comment/CData
        if node.parent and node.parent.name in SKIP_PARENTS: continue
        if in_brand(node):                            continue
        if no_translate(node):                        continue
        if translatable(str(node)):
            segs.add(str(node).strip())
    # translatable attributes
    for el in soup.find_all(attrs={"alt": True}):
        if translatable(el["alt"]): segs.add(el["alt"].strip())
    for sel, attr in [("meta[name=description]", "content"),
                      ("meta[property='og:description']", "content"),
                      ("meta[property='og:title']", "content"),
                      ("meta[name='twitter:title']", "content"),
                      ("meta[name='twitter:description']", "content"),
                      ("title", None)]:
        for el in soup.select(sel):
            val = el.get_text() if attr is None else el.get(attr, "")
            if val and translatable(val): segs.add(val.strip())
    return segs

# ── localize a parsed page into `lang` (mutates soup) ─────────────────────────
_DATE_WORDS = {
    "nl": (["ma", "di", "wo", "do", "vr", "za", "zo"],
           ["januari", "februari", "maart", "april", "mei", "juni", "juli",
            "augustus", "september", "oktober", "november", "december"]),
    "es": (["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
           ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]),
}


def localize_date(iso: str, lang: str, long: bool = False) -> str:
    """"2026-09-27" -> "zo 27 september" / "dom 27 de septiembre";
    long=True -> "zondag 27 september 2026" / "domingo 27 de septiembre de 2026"."""
    import datetime as _dt
    try:
        d = _dt.date.fromisoformat(iso)
    except Exception:
        return ""
    days, months = _DATE_WORDS.get(lang, (None, None))
    if not days:
        return ""
    wd, mo = days[d.weekday()], months[d.month - 1]
    if long:
        wd = _LONG_DAYS[lang][d.weekday()]
        return (f"{wd} {d.day} de {mo} de {d.year}" if lang == "es"
                else f"{wd} {d.day} {mo} {d.year}")
    return f"{wd} {d.day} de {mo}" if lang == "es" else f"{wd} {d.day} {mo}"


_LONG_DAYS = {"nl": ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"],
              "es": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]}


def localize(soup, lang: str, rel_path: str):
    html_lang, og_locale = LANGS[lang]

    # text nodes (covers <title>; brand logo skipped)
    for node in soup.find_all(string=True):
        if type(node) is not NavigableString:         continue  # skip Doctype/Comment/CData
        if node.parent and node.parent.name in SKIP_PARENTS: continue
        if in_brand(node):                            continue
        if no_translate(node):                        continue
        s = str(node)
        if translatable(s):
            node.replace_with(tr(s, lang))

    # dates stamped by generate.py as data-srdate="YYYY-MM-DD" (utility rail)
    for el in soup.find_all(attrs={"data-srdate": True}):
        _d = localize_date(el.get("data-srdate", ""), lang)
        if _d:
            el.string = _d
    for el in soup.find_all(attrs={"data-srdate-long": True}):
        _d = localize_date(el.get("data-srdate-long", ""), lang, long=True)
        if _d:
            el.string = _d

    # alt attributes
    for el in soup.find_all(attrs={"alt": True}):
        if translatable(el["alt"]): el["alt"] = tr(el["alt"], lang)

    # head meta + title
    for sel, attr in [("meta[name=description]", "content"),
                      ("meta[property='og:description']", "content"),
                      ("meta[property='og:title']", "content"),
                      ("meta[name='twitter:title']", "content"),
                      ("meta[name='twitter:description']", "content")]:
        for el in soup.select(sel):
            v = el.get(attr, "")
            if v and translatable(v): el[attr] = tr(v, lang)
    # NB: <title> text is handled by the text-node loop above (don't double-process)

    # html lang + og:locale (+ alternates)
    if soup.html: soup.html["lang"] = html_lang
    for el in soup.select("meta[property='og:locale']"):
        el["content"] = og_locale
    inject_og_alternates(soup, lang)

    # JSON-LD: localize internal page URLs + inLanguage (schema text stays neutral)
    localize_jsonld(soup, lang)

    # canonical + og:url -> prefix the path for non-en
    prefix = "" if lang == "en" else f"/{lang}"
    canon = f"{SITE_URL}{prefix}/{url_path(rel_path)}".replace("/index.html", "/")
    # Redirect stubs must keep pointing at their target, never self-canonicalize.
    _STUBS = {"today.html": "/daily-notices.html",
              "worldcup-2026.html": "/matches.html",
              "seogs-2026.html": "/events.html",
              "nature.html": "/activities.html",
              "real-estate.html": "/business",
              # Marketplace retired Sep 28 2026 (generate._retired_stub)
              "marketplace/index.html": "/business",
              "post-ad.html": "/business",
              "my-ads.html": "/business"}
    if rel_path not in _STUBS:
        for el in soup.select("link[rel=canonical]"):
            el["href"] = canon
        for el in soup.select("meta[property='og:url']"):
            el["content"] = canon
    else:
        _t = _STUBS[rel_path]
        _tgt = f"{SITE_URL}{prefix}{_t}"
        for el in soup.select("link[rel=canonical]"):
            el["href"] = _tgt
        for el in soup.select("meta[property='og:url']"):
            el["content"] = _tgt
        if lang != "en":
            for m in soup.select('meta[http-equiv="refresh"]'):
                m["content"] = m.get("content", "").replace(_t, f"/{lang}{_t}")
            for a in soup.select(f'a[href="{_t}"]'):
                a["href"] = f"/{lang}{_t}"
    # keep translated nav labels on a single row (they run longer than English)
    if soup.head:
        _st = soup.new_tag("style"); _st.string = "nav button,nav a{white-space:nowrap}"
        soup.head.append(_st)
    inject_hreflang(soup, rel_path)
    inject_switcher(soup, lang, rel_path)
    return soup

# ── per-page hreflang/x-default (identical set on every tree) ─────────────────
# Clean URLs: pages listed here are published without ".html" (GitHub Pages
# serves x.html at /x). Read from the business registry; if that import fails,
# fall back to the old behaviour (with .html) rather than breaking the build.
try:
    from business_pages import BIZ_FILES as _CLEAN_FILES
    _CLEAN_FILES = set(_CLEAN_FILES)
except Exception:
    _CLEAN_FILES = set()
# Non-business pages that are also published without ".html" (keep in sync with
# the hrefs/canonical in generate.py).
_CLEAN_FILES |= {"about-suriname.html"}


def url_path(rel_path: str) -> str:
    """Public path for a file path (index.html -> '', clean pages lose .html)."""
    if rel_path in _CLEAN_FILES:
        return rel_path[:-5]
    return rel_path


def inject_hreflang(soup, rel_path: str):
    head = soup.head
    if not head: return
    for el in head.select("link[rel='alternate'][hreflang]"):
        el.decompose()
    def url_for(code):
        pre = "" if code == "en" else f"/{code}"
        return f"{SITE_URL}{pre}/{url_path(rel_path)}".replace("/index.html", "/")
    for code in ["en", "nl", "es"]:
        tag = soup.new_tag("link", rel="alternate", hreflang=code, href=url_for(code))
        head.append(tag)
    xd = soup.new_tag("link", rel="alternate", hreflang="x-default", href=url_for("en"))
    head.append(xd)

# ── og:locale:alternate (signal the other available locales) ──────────────────
def inject_og_alternates(soup, lang: str):
    head = soup.head
    if not head: return
    for el in head.select("meta[property='og:locale:alternate']"):
        el.decompose()
    anchor = soup.select_one("meta[property='og:locale']")
    for code, (_h, oglc) in LANGS.items():
        if code == lang: continue
        tag = soup.new_tag("meta"); tag["property"] = "og:locale:alternate"; tag["content"] = oglc
        (anchor.insert_after if anchor is not None else head.append)(tag)

# ── JSON-LD localization: prefix internal page URLs, set inLanguage ────────────
_LD_ASSET_RE = re.compile(r'\.(?:jpg|jpeg|png|webp|gif|svg|ico|css|js|xml|json|mp4|pdf|woff2?|ttf)(?:$|\?)', re.I)
def localize_jsonld(soup, lang: str):
    if lang == "en": return
    base = SITE_URL + "/"
    prefix = f"{SITE_URL}/{lang}/"
    def loc_url(u):
        if not isinstance(u, str) or not u.startswith(base):
            return u
        rest = u[len(base):]                 # path (+ optional ?query/#frag)
        path = rest.split("?", 1)[0].split("#", 1)[0]
        if _LD_ASSET_RE.search(path):        # leave images/assets at root (no lang variant)
            return u
        if rest.startswith(f"{lang}/"):      # already localized
            return u
        return prefix + rest
    def walk(o):
        if isinstance(o, dict):
            return {k: (lang if k == "inLanguage"
                        else loc_url(v) if isinstance(v, str)
                        else walk(v))
                    for k, v in o.items()}
        if isinstance(o, list):
            return [walk(i) for i in o]
        if isinstance(o, str):
            return loc_url(o)
        return o
    def _loc_text(node):
        # Localize rich-result text (breadcrumb labels, FAQ Q&A) via the existing
        # translation cache. Proper/business names are not cached, so tr() returns
        # them unchanged (English fallback). Keeps schema in sync with the already
        # translated visible content -> localized SERP rich results.
        if isinstance(node, list):
            for _n in node: _loc_text(_n)
            return
        if not isinstance(node, dict): return
        _t = node.get("@type")
        if _t == "BreadcrumbList":
            for _it in (node.get("itemListElement") or []):
                if isinstance(_it, dict) and isinstance(_it.get("name"), str):
                    _it["name"] = tr(_it["name"], lang)
        elif _t == "FAQPage":
            for _q in (node.get("mainEntity") or []):
                if isinstance(_q, dict):
                    if isinstance(_q.get("name"), str):
                        _q["name"] = tr(_q["name"], lang)
                    _a = _q.get("acceptedAnswer")
                    if isinstance(_a, dict) and isinstance(_a.get("text"), str):
                        _a["text"] = tr(_a["text"], lang)
        if isinstance(node.get("@graph"), list):
            for _n in node["@graph"]: _loc_text(_n)
    for sc in soup.select("script[type='application/ld+json']"):
        raw = sc.string
        if not raw: continue
        try:
            data = json.loads(raw)
        except Exception:
            continue                          # malformed → leave English, never break
        data = walk(data)
        _loc_text(data)
        sc.string = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

# ── language switcher injected into nav ───────────────────────────────────────
SWITCH_LABEL = {"en": "EN", "nl": "NL", "es": "ES"}
def inject_switcher(soup, lang: str, rel_path: str):
    nav = soup.find("nav")
    if not nav: return
    if nav.find(attrs={"data-langswitch": True}): return

    def href(code):
        pre = "" if code == "en" else f"/{code}"
        return (f"{pre}/{url_path(rel_path)}".replace("/index.html", "/")) or "/"

    def globe(stroke):
        svg = soup.new_tag("svg", attrs={"width":"15","height":"15","viewBox":"0 0 24 24",
                                         "fill":"none","stroke":stroke,"stroke-width":"2",
                                         "style":"flex-shrink:0"})
        svg.append(soup.new_tag("circle", attrs={"cx":"12","cy":"12","r":"9"}))
        for d in ("M3 12h18", "M12 3c2.6 2.6 2.6 15.4 0 18", "M12 3c-2.6 2.6-2.6 15.4 0 18"):
            svg.append(soup.new_tag("path", attrs={"d": d}))
        return svg

    def links(into, active_col, idle_col):
        for code in ["en", "nl", "es"]:
            a = soup.new_tag("a", href=href(code)); a.string = SWITCH_LABEL[code]
            a["style"] = (f"color:{active_col};text-decoration:underline" if code == lang
                          else f"color:{idle_col};text-decoration:none")
            into.append(a)

    # --- desktop: globe dropdown to the right of the search box, hidden on mobile ---
    holder = soup.find(attrs={"class": re.compile(r"flex items-center gap-2 flex-shrink-0")})
    if holder is not None:
        wrap = soup.new_tag("div"); wrap["data-langswitch"] = "1"
        wrap["class"] = "hidden lg:flex"
        wrap["style"] = "position:relative;align-items:center;margin-left:8px;flex-shrink:0"

        btn = soup.new_tag("button", attrs={
            "type":"button","aria-label":"Language","aria-expanded":"false",
            "onclick":("var m=this.nextElementSibling,o=m.style.display==='block';"
                       "document.querySelectorAll('[data-langmenu]').forEach(function(x){x.style.display='none';});"
                       "m.style.display=o?'none':'block';"
                       "this.setAttribute('aria-expanded',(!o).toString());"
                       "event.stopPropagation();"),
            "style":("display:flex;align-items:center;gap:5px;background:none;border:0;cursor:pointer;"
                     "font-size:12px;font-weight:600;color:#6b7280;padding:4px 7px;border-radius:8px")})
        btn.append(globe("#6b7280"))
        cur = soup.new_tag("span"); cur.string = SWITCH_LABEL[lang]; btn.append(cur)
        chev = soup.new_tag("svg", attrs={"width":"11","height":"11","viewBox":"0 0 24 24",
                                          "fill":"none","stroke":"currentColor","stroke-width":"2.5",
                                          "style":"flex-shrink:0;opacity:.7"})
        chev.append(soup.new_tag("path", attrs={"d":"M6 9l6 6 6-6","stroke-linecap":"round","stroke-linejoin":"round"}))
        btn.append(chev)
        wrap.append(btn)

        menu = soup.new_tag("div"); menu["data-langmenu"] = "1"
        menu["style"] = ("display:none;position:absolute;right:0;top:100%;margin-top:6px;background:#fff;"
                         "border:1px solid #eee;border-radius:10px;box-shadow:0 8px 24px rgba(20,42,30,.12);"
                         "padding:5px;min-width:112px;z-index:60")
        for code in ["en", "nl", "es"]:
            a = soup.new_tag("a", href=href(code)); a.string = SWITCH_LABEL[code]
            active = (code == lang)
            a["style"] = ("display:block;padding:7px 12px;border-radius:7px;font-size:13px;font-weight:600;"
                          "text-decoration:none;" + ("color:var(--forest);background:#eef4ee"
                          if active else "color:#374151"))
            menu.append(a)
        wrap.append(menu)

        sb = holder.find("button", onclick=re.compile("openSearch")) or holder.find("button")
        (sb.insert_after if sb is not None else holder.append)(wrap)

        # one outside-click handler closes any open language menu
        body = soup.body or soup
        if not soup.find(id="langswitch-js"):
            js = soup.new_tag("script", id="langswitch-js")
            js.string = ("document.addEventListener('click',function(){"
                         "document.querySelectorAll('[data-langmenu]').forEach(function(x){"
                         "x.style.display='none';var b=x.previousElementSibling;"
                         "if(b)b.setAttribute('aria-expanded','false');});});")
            body.append(js)

    # --- mobile: row at the top of the hamburger menu (keeps the hamburger intact) ---
    mm = soup.find(id="mm")
    if mm is not None:
        m = soup.new_tag("div"); m["data-langswitch-mobile"] = "1"
        m["style"] = ("display:flex;align-items:center;gap:16px;padding:10px 2px 12px;"
                      "margin-bottom:4px;border-bottom:1px solid #eee;font-size:15px;font-weight:600")
        m.append(globe("#6b7280"))
        links(m, "var(--forest)", "#6b7280")
        _ib = soup.new_tag("button", attrs={"id":"pwa-nav","type":"button","onclick":"pwaInstall()","aria-label":"Install app","style":"display:none;margin-left:auto;align-items:center;gap:6px;background:var(--forest);color:#fff;border:0;border-radius:999px;padding:7px 14px;font-size:13px;font-weight:700;cursor:pointer;flex-shrink:0"})
        _isvg = soup.new_tag("svg", attrs={"width":"15","height":"15","viewBox":"0 0 24 24","fill":"none","stroke":"currentColor","stroke-width":"2","style":"flex-shrink:0"})
        _isvg.append(soup.new_tag("path", attrs={"stroke-linecap":"round","stroke-linejoin":"round","d":"M12 4v10m0 0l-4-4m4 4l4-4M5 20h14"}))
        _ib.append(_isvg)
        _ilbl = soup.new_tag("span"); _ilbl.string = "Install"
        _ib.append(_ilbl)
        m.append(_ib)
        mm.insert(0, m)

# ── per-build volatile markup (kept OUT of the page hash, spliced back in) ────
# generate.py stamps three things on (nearly) every page that change between
# builds without changing anything translatable in the page body:
#   * the utility rail above the nav: live °C, USD rate, outage count, date
#   * JSON-LD "dateModified" (today's date)
#   * the tailwind.css?v=<hash> cache-buster
# Hashing them made every page miss the incremental cache on every 15-min run
# (e.g. "1656 pages translated, 18 reused"). They are now stripped before
# hashing; on a hit the cached NL/ES file gets the fresh values spliced in. If
# the counts don't line up for any reason, the page is fully rebuilt instead,
# so this can only ever fall back to the old behaviour, never serve stale text.
_RAIL_RE   = re.compile(r'<div class="util-rail">.*?</div></div></div>', re.S)
_LDDATE_RE = re.compile(r'("dateModified":\s?")(\d{4}-\d{2}-\d{2})(")')
_TWV_RE    = re.compile(r'(tailwind\.css\?v=)([0-9A-Za-z]+)')

def stable_hash(html: str) -> str:
    """md5 of the English page with the per-build volatile markup removed."""
    t = _RAIL_RE.sub("", html)
    t = _LDDATE_RE.sub(r"\1\3", t)
    t = _TWV_RE.sub(r"\1", t)
    return hashlib.md5(t.encode("utf-8")).hexdigest()

def _localize_rail(frag: str, lang: str) -> str:
    """The rail through the same text/date rules localize() applies to a page."""
    soup = BeautifulSoup(frag, "lxml")
    rail = soup.find("div", class_="util-rail")
    if rail is None:
        return None
    for node in rail.find_all(string=True):
        if type(node) is not NavigableString:         continue
        if node.parent and node.parent.name in SKIP_PARENTS: continue
        if in_brand(node):                            continue
        if no_translate(node):                        continue
        s = str(node)
        if translatable(s):
            node.replace_with(tr(s, lang))
    for el in rail.find_all(attrs={"data-srdate": True}):
        _d = localize_date(el.get("data-srdate", ""), lang)
        if _d:
            el.string = _d
    for el in rail.find_all(attrs={"data-srdate-long": True}):
        _d = localize_date(el.get("data-srdate-long", ""), lang, long=True)
        if _d:
            el.string = _d
    return serialize(rail)

def refresh_volatile(cached: str, en_html: str, lang: str):
    """Cached NL/ES page with this build's rail/dates/CSS version, or None."""
    en_rails = _RAIL_RE.findall(en_html)
    if len(_RAIL_RE.findall(cached)) != len(en_rails):
        return None
    loc = [_localize_rail(r, lang) for r in en_rails]
    if any(x is None for x in loc):
        return None
    it = iter(loc)
    out = _RAIL_RE.sub(lambda m: next(it), cached)

    en_dates = [m.group(2) for m in _LDDATE_RE.finditer(en_html)]
    if len(_LDDATE_RE.findall(out)) != len(en_dates):
        return None
    it = iter(en_dates)
    out = _LDDATE_RE.sub(lambda m: m.group(1) + next(it) + m.group(3), out)

    en_v = {m.group(2) for m in _TWV_RE.finditer(en_html)}
    if len(en_v) > 1:
        return None
    if en_v:
        if not _TWV_RE.search(out):
            return None
        v = en_v.pop()
        out = _TWV_RE.sub(lambda m: m.group(1) + v, out)
    elif _TWV_RE.search(out):
        return None
    return out

# ── walk the English tree ─────────────────────────────────────────────────────
# Pages whose text is mostly a live feed (headlines, fixtures, flights, rates).
LIVE_FEED_PAGES = {"news.html", "matches.html", "flights.html", "currency.html",
                   "conditions.html", "daily-notices.html", "atms.html"}


def english_pages():
    for p in ROOT.glob("*.html"):
        yield p, p.name
    for p in (ROOT / "listing").glob("*/index.html"):
        yield p, f"listing/{p.parent.name}/index.html"
    # Marketplace browse page + ads. The seller's own text carries
    # translate="no", so only the page furniture is localised.
    if (ROOT / "marketplace" / "index.html").exists():
        yield ROOT / "marketplace" / "index.html", "marketplace/index.html"
    for p in (ROOT / "marketplace").glob("*/index.html"):
        yield p, f"marketplace/{p.parent.name}/index.html"

def process_page(job):
    """One English page: always re-finalize EN, emit nl/es only when stale.

    Runs in a worker process. Everything it touches (the translation cache,
    PROTECTED) is read-only and inherited by fork, so there is nothing to pickle
    beyond the small job tuple and the returned segment list.
    """
    src_str, rel, old_hash = job
    src = Path(src_str)

    raw = src.read_bytes()
    # match Path.read_text()'s universal newlines so output is byte-for-byte
    # identical to the pre-incremental version on CRLF checkouts too
    html = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    new_hash = stable_hash(html)

    # finalize English in place (hreflang + switcher only, no translation).
    # never skipped: generate.py rewrites this file from scratch every run.
    en_soup = BeautifulSoup(html, "lxml")
    segs = collect_segments(en_soup)
    inject_hreflang(en_soup, rel)
    inject_og_alternates(en_soup, "en")
    inject_switcher(en_soup, "en", rel)
    src.write_text(serialize(en_soup), encoding="utf-8")

    reuse = (old_hash is not None and old_hash == new_hash
             and all((ROOT / lang / rel).exists() for lang in TARGETS))

    if reuse:
        # same page body; only rail/dates/CSS version moved -> splice, don't re-render
        fresh = {}
        for lang in TARGETS:
            out = ROOT / lang / rel
            upd = refresh_volatile(out.read_text(encoding="utf-8"), html, lang)
            if upd is None:
                reuse = False
                break
            fresh[out] = upd
        if reuse:
            for out, upd in fresh.items():
                out.write_text(upd, encoding="utf-8")

    if not reuse:
        for lang in TARGETS:
            soup = BeautifulSoup(html, "lxml")
            localize(soup, lang, rel)
            out = ROOT / lang / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(serialize(soup), encoding="utf-8")

    return rel, new_hash, sorted(segs), reuse


def main():
    t0 = time.time()
    pages = list(english_pages())
    if ONLY:
        pages = [(p, rel) for (p, rel) in pages if p.name in ONLY or rel in ONLY]

    key   = build_key()
    known = load_build_cache(key)
    jobs  = [(str(p), rel, known.get(rel)) for (p, rel) in pages]

    # Only fork is safe here: a spawned worker re-imports this module with a
    # different sys.argv, which would drop --stub/--only and reload the
    # translation cache per process. Windows/macOS therefore run serial.
    try:
        ctx = multiprocessing.get_context("fork")
    except ValueError:
        ctx = None
    workers = JOBS or min(len(jobs), os.cpu_count() or 1) or 1
    if ctx is None and workers > 1:
        workers = 1
        print("i18n: no fork() on this platform, running serial")
    print(f"i18n: {len(jobs)} source pages | stub={STUB} | cache={len(cache)} keys "
          f"| reusable={len(known)} | workers={workers}")

    all_segments = set()
    stable_segments = set()   # seen on at least one page that is not a live feed
    hashes = {}
    reused = 0

    def absorb(result):
        nonlocal reused
        rel, h, segs, was_reused = result
        hashes[rel] = h
        all_segments.update(segs)
        if rel not in LIVE_FEED_PAGES:
            stable_segments.update(segs)
        if was_reused:
            reused += 1

    if workers > 1 and len(jobs) > 1:
        with ctx.Pool(workers) as pool:
            for result in pool.imap_unordered(process_page, jobs, chunksize=4):
                absorb(result)
    else:
        for job in jobs:
            absorb(process_page(job))

    print(f"i18n: {len(jobs) - reused} pages translated, {reused} reused from cache")

    # per-language search index (names/areas identical; category labels translated)
    si = ROOT / "search-index.json"
    if si.exists():
        data = json.load(open(si, encoding="utf-8"))
        for lang in TARGETS:
            out = ROOT / lang / "search-index.json"
            loc = [{**e, "c": tr(e.get("c", ""), lang)} for e in data]
            out.write_text(json.dumps(loc, ensure_ascii=False, separators=(",", ":")),
                           encoding="utf-8")

    # A --only run has seen a subset of the site, so anything derived from the
    # FULL page set would be written truncated. Skip those writes instead of
    # clobbering them (this used to require backing up 3 files by hand).
    if ONLY:
        print("i18n: --only run; sitemap, i18n_segments.json and the build cache left untouched")
    else:
        localize_sitemap()

        # dump the segment inventory for translate_cache.py to consume.
        # complete even on a fully cached run: every English page is still parsed.
        # Stable text first: translate_cache.py works through this list in order
        # with a --limit, so headlines and fixtures that are gone tomorrow no
        # longer use up the budget ahead of listings and page text.
        _ordered = sorted(stable_segments) + sorted(all_segments - stable_segments)
        (ROOT / "i18n_segments.json").write_text(
            json.dumps(_ordered, ensure_ascii=False, indent=0),
            encoding="utf-8")
        print(f"i18n: collected {len(all_segments)} unique segments -> i18n_segments.json")

        if not STUB:
            BUILD_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            BUILD_CACHE_FILE.write_text(
                json.dumps({"key": key, "pages": hashes}, separators=(",", ":"),
                           sort_keys=True),
                encoding="utf-8")

    print(f"i18n: done in {time.time() - t0:.1f}s")
    _stage_new_dirs()


def _stage_new_dirs():
    """
    update.yml only `git add`s the folders it names, and workflow files cannot
    be edited from here. This is the last build step that writes pages before
    the commit step, so new top-level folders get staged here instead. The
    commit step's `git diff --staged` then picks them up. CI only.
    """
    if not os.environ.get("GITHUB_ACTIONS"):
        return
    import subprocess
    for d in ("marketplace",):
        if (ROOT / d).is_dir():
            r = subprocess.run(["git", "add", "-A", d], cwd=ROOT, capture_output=True, text=True)
            print(f"i18n: staged {d}/ ({'ok' if r.returncode == 0 else r.stderr.strip()})")


# ── multilingual sitemap (adds nl/es URLs + xhtml:link alternates) ────────────
def localize_sitemap():
    sm = ROOT / "sitemap.xml"
    if not sm.exists() or sm.stat().st_size == 0:
        return
    import re as _re
    txt = sm.read_text(encoding="utf-8")
    # Parse each <url> block so the English lastmod/changefreq/priority survive
    # into the localized sitemap. generate.py computes a hash-based lastmod
    # (only advances when content changes); without this it was being dropped.
    # The nl/es variants inherit the same values as their English source.
    url_blocks = _re.findall(r"<url>(.*?)</url>", txt, _re.S)
    def _tag(block, name):
        m = _re.search(rf"<{name}>(.*?)</{name}>", block, _re.S)
        return m.group(1).strip() if m else None
    def path_of(u): return u[len(SITE_URL):] or "/"
    def alt_links(path):
        out = []
        for code in ["en", "nl", "es"]:
            pre = "" if code == "en" else f"/{code}"
            out.append(f'    <xhtml:link rel="alternate" hreflang="{code}" href="{SITE_URL}{pre}{path}"/>')
        out.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}{path}"/>')
        return "\n".join(out)
    blocks = []
    pages = 0
    for blk in url_blocks:
        loc = _tag(blk, "loc")
        if not loc:
            continue
        path = path_of(loc)
        # Idempotency guard: if this function runs twice without generate.py
        # rewriting sitemap.xml in between, the file already contains /nl/ and
        # /es/ URLs. Re-prefixing them produced /nl/nl/… entries (a 20k-URL
        # sitemap full of 404s). Only English paths are localized.
        if re.match(r"^/(nl|es)(/|$)", path):
            continue
        pages += 1
        meta = ""
        for _t in ("lastmod", "changefreq", "priority"):
            _v = _tag(blk, _t)
            if _v:
                meta += f"    <{_t}>{_v}</{_t}>\n"
        for code in ["en", "nl", "es"]:
            pre = "" if code == "en" else f"/{code}"
            blocks.append(
                f"  <url>\n    <loc>{SITE_URL}{pre}{path}</loc>\n"
                f"{meta}{alt_links(path)}\n  </url>"
            )
    out = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(blocks) + "\n</urlset>\n")
    sm.write_text(out, encoding="utf-8")
    print(f"i18n: sitemap localized -> {pages} pages x 3 languages (lastmod preserved)")


if __name__ == "__main__":
    main()
