#!/usr/bin/env python3
"""
i18n build stage for ExploreSuriname.

Runs AFTER generate.py. Reads the built English site and emits /nl/ and /es/
trees, and finalizes per-page hreflang/canonical on every tree (incl. English).

Translation comes only from the committed cache (translations.json); this stage
never calls the network, so the 15-min rebuild loop stays deterministic. Any
segment missing from the cache falls back to English, so the site never breaks.

Usage:
    python3 build_i18n.py            # use cache (production / CI)
    python3 build_i18n.py --stub     # fake [nl]/[es] prefixes, no cache needed (dev)
    python3 build_i18n.py --only "index.html,restaurants.html"   # subset (dev)
"""
import json, re, sys, shutil
from pathlib import Path
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
STUB = "--stub" in sys.argv
ONLY = None
for i, a in enumerate(sys.argv):
    if a == "--only" and i + 1 < len(sys.argv):
        ONLY = set(sys.argv[i + 1].split(","))

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

PHONE_RE = re.compile(r'^[\+\d][\d\s\-\(\)/]{5,}$')
CODE_RE  = re.compile(r'^[A-Z]{2,5}$')                 # currency/IATA codes
NUM_RE   = re.compile(r'^[\d\s.,:%–\-+/x×]+$')         # pure numeric/symbolic
URL_RE   = re.compile(r'^(https?://|www\.|@|#)')
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

def translatable(s: str) -> bool:
    t = s.strip()
    if len(t) < 2:                 return False
    if not re.search(r'[A-Za-z]', t): return False
    if NUM_RE.match(t):            return False
    if PHONE_RE.match(t):          return False
    if CODE_RE.match(t):           return False
    if URL_RE.match(t):            return False
    if t in PROTECTED:             return False
    return True

# ── translation cache: {source_text: {"nl": "...", "es": "..."}} ──────────────
cache = {}
if CACHE_FILE.exists():
    cache = json.load(open(CACHE_FILE, encoding="utf-8"))

def tr(text: str, lang: str) -> str:
    """Translate a text node, preserving leading/trailing whitespace."""
    key = text.strip()
    lead = text[:len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    entry = cache.get(key)
    if entry and entry.get(lang):
        return lead + entry[lang] + trail
    if STUB:
        return lead + f"[{lang}] " + key + trail
    return text   # English fallback

# ── collect every translatable source segment (for translate_cache.py) ────────
def collect_segments(soup) -> set:
    segs = set()
    for node in soup.find_all(string=True):
        if type(node) is not NavigableString:         continue  # skip Doctype/Comment/CData
        if node.parent and node.parent.name in SKIP_PARENTS: continue
        if in_brand(node):                            continue
        if translatable(str(node)):
            segs.add(str(node).strip())
    # translatable attributes
    for el in soup.find_all(attrs={"alt": True}):
        if translatable(el["alt"]): segs.add(el["alt"].strip())
    for sel, attr in [("meta[name=description]", "content"),
                      ("meta[property='og:description']", "content"),
                      ("meta[property='og:title']", "content"),
                      ("title", None)]:
        for el in soup.select(sel):
            val = el.get_text() if attr is None else el.get(attr, "")
            if val and translatable(val): segs.add(val.strip())
    return segs

# ── localize a parsed page into `lang` (mutates soup) ─────────────────────────
def localize(soup, lang: str, rel_path: str):
    html_lang, og_locale = LANGS[lang]

    # text nodes (covers <title>; brand logo skipped)
    for node in soup.find_all(string=True):
        if type(node) is not NavigableString:         continue  # skip Doctype/Comment/CData
        if node.parent and node.parent.name in SKIP_PARENTS: continue
        if in_brand(node):                            continue
        s = str(node)
        if translatable(s):
            node.replace_with(tr(s, lang))

    # alt attributes
    for el in soup.find_all(attrs={"alt": True}):
        if translatable(el["alt"]): el["alt"] = tr(el["alt"], lang)

    # head meta + title
    for sel, attr in [("meta[name=description]", "content"),
                      ("meta[property='og:description']", "content"),
                      ("meta[property='og:title']", "content")]:
        for el in soup.select(sel):
            v = el.get(attr, "")
            if v and translatable(v): el[attr] = tr(v, lang)
    # NB: <title> text is handled by the text-node loop above (don't double-process)

    # html lang + og:locale
    if soup.html: soup.html["lang"] = html_lang
    for el in soup.select("meta[property='og:locale']"):
        el["content"] = og_locale

    # canonical + og:url -> prefix the path for non-en
    prefix = "" if lang == "en" else f"/{lang}"
    canon = f"{SITE_URL}{prefix}/{rel_path}".replace("/index.html", "/")
    for el in soup.select("link[rel=canonical]"):
        el["href"] = canon
    for el in soup.select("meta[property='og:url']"):
        el["content"] = canon

    # language-aware redirect for the today.html stub
    if rel_path == "today.html" and lang != "en":
        for m in soup.select('meta[http-equiv="refresh"]'):
            m["content"] = m.get("content","").replace("/daily-notices.html", f"/{lang}/daily-notices.html")
        for a in soup.select('a[href="/daily-notices.html"]'):
            a["href"] = f"/{lang}/daily-notices.html"
    # keep translated nav labels on a single row (they run longer than English)
    if soup.head:
        _st = soup.new_tag("style"); _st.string = "nav button,nav a{white-space:nowrap}"
        soup.head.append(_st)
    inject_hreflang(soup, rel_path)
    inject_switcher(soup, lang, rel_path)
    return soup

# ── per-page hreflang/x-default (identical set on every tree) ─────────────────
def inject_hreflang(soup, rel_path: str):
    head = soup.head
    if not head: return
    for el in head.select("link[rel='alternate'][hreflang]"):
        el.decompose()
    def url_for(code):
        pre = "" if code == "en" else f"/{code}"
        return f"{SITE_URL}{pre}/{rel_path}".replace("/index.html", "/")
    for code in ["en", "nl", "es"]:
        tag = soup.new_tag("link", rel="alternate", hreflang=code, href=url_for(code))
        head.append(tag)
    xd = soup.new_tag("link", rel="alternate", hreflang="x-default", href=url_for("en"))
    head.append(xd)

# ── language switcher injected into nav ───────────────────────────────────────
SWITCH_LABEL = {"en": "EN", "nl": "NL", "es": "ES"}
def inject_switcher(soup, lang: str, rel_path: str):
    nav = soup.find("nav")
    if not nav: return
    if nav.find(attrs={"data-langswitch": True}): return

    def href(code):
        pre = "" if code == "en" else f"/{code}"
        return (f"{pre}/{rel_path}".replace("/index.html", "/")) or "/"

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

    # --- desktop: far-right of the search box, hidden on mobile ---
    holder = soup.find(attrs={"class": re.compile(r"flex items-center gap-2 flex-shrink-0")})
    if holder is not None:
        wrap = soup.new_tag("div"); wrap["data-langswitch"] = "1"
        wrap["class"] = "hidden md:flex items-center"
        wrap["style"] = "gap:7px;margin-left:10px;flex-shrink:0;font-size:12px;font-weight:600"
        wrap.append(globe("#9ca3af"))
        links(wrap, "var(--forest)", "#9ca3af")
        sb = holder.find("button", onclick=re.compile("openSearch")) or holder.find("button")
        (sb.insert_after if sb is not None else holder.append)(wrap)

    # --- mobile: row at the top of the hamburger menu (keeps the hamburger intact) ---
    mm = soup.find(id="mm")
    if mm is not None:
        m = soup.new_tag("div"); m["data-langswitch-mobile"] = "1"
        m["style"] = ("display:flex;align-items:center;gap:16px;padding:10px 2px 12px;"
                      "margin-bottom:4px;border-bottom:1px solid #eee;font-size:15px;font-weight:600")
        m.append(globe("#6b7280"))
        links(m, "var(--forest)", "#6b7280")
        mm.insert(0, m)

# ── walk the English tree ─────────────────────────────────────────────────────
def english_pages():
    for p in ROOT.glob("*.html"):
        yield p, p.name
    for p in (ROOT / "listing").glob("*/index.html"):
        yield p, f"listing/{p.parent.name}/index.html"

def main():
    pages = list(english_pages())
    if ONLY:
        pages = [(p, rel) for (p, rel) in pages if p.name in ONLY or rel in ONLY]
    print(f"i18n: {len(pages)} source pages | stub={STUB} | cache={len(cache)} keys")

    all_segments = set()
    for src, rel in pages:
        html = src.read_text(encoding="utf-8")

        # finalize English in place (hreflang + switcher only, no translation)
        en_soup = BeautifulSoup(html, "lxml")
        all_segments |= collect_segments(en_soup)
        inject_hreflang(en_soup, rel)
        inject_switcher(en_soup, "en", rel)
        src.write_text(serialize(en_soup), encoding="utf-8")

        # emit translated trees
        for lang in TARGETS:
            soup = BeautifulSoup(html, "lxml")
            localize(soup, lang, rel)
            out = ROOT / lang / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(serialize(soup), encoding="utf-8")

    # per-language search index (names/areas identical; category labels translated)
    si = ROOT / "search-index.json"
    if si.exists():
        data = json.load(open(si, encoding="utf-8"))
        for lang in TARGETS:
            out = ROOT / lang / "search-index.json"
            loc = [{**e, "c": tr(e.get("c", ""), lang)} for e in data]
            out.write_text(json.dumps(loc, ensure_ascii=False, separators=(",", ":")),
                           encoding="utf-8")

    localize_sitemap()

    # dump the segment inventory for translate_cache.py to consume
    (ROOT / "i18n_segments.json").write_text(
        json.dumps(sorted(all_segments), ensure_ascii=False, indent=0),
        encoding="utf-8")
    print(f"i18n: collected {len(all_segments)} unique segments -> i18n_segments.json")
    print("i18n: done")


# ── multilingual sitemap (adds nl/es URLs + xhtml:link alternates) ────────────
def localize_sitemap():
    sm = ROOT / "sitemap.xml"
    if not sm.exists() or sm.stat().st_size == 0:
        return
    import re as _re
    txt = sm.read_text(encoding="utf-8")
    locs = _re.findall(r"<loc>(.*?)</loc>", txt)
    def path_of(u): return u[len(SITE_URL):] or "/"
    def alt_links(path):
        out = []
        for code in ["en", "nl", "es"]:
            pre = "" if code == "en" else f"/{code}"
            out.append(f'    <xhtml:link rel="alternate" hreflang="{code}" href="{SITE_URL}{pre}{path}"/>')
        out.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{SITE_URL}{path}"/>')
        return "\n".join(out)
    blocks = []
    for u in locs:
        path = path_of(u)
        for code in ["en", "nl", "es"]:
            pre = "" if code == "en" else f"/{code}"
            blocks.append(
                f"  <url>\n    <loc>{SITE_URL}{pre}{path}</loc>\n"
                f"{alt_links(path)}\n  </url>"
            )
    out = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           + "\n".join(blocks) + "\n</urlset>\n")
    sm.write_text(out, encoding="utf-8")
    print(f"i18n: sitemap localized -> {len(locs)} pages x 3 languages")


if __name__ == "__main__":
    main()
