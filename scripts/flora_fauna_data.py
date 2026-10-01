"""Flora & Fauna of Suriname: offline data builder (Oct 2026).

Writes data/flora_fauna/species.json and text.json, which flora_fauna_pages.py
turns into pages. NOT part of the 15-minute site build: run it by hand (or from
a manual workflow) when you want fresh data, e.g. once a quarter:

    pip install requests opencc-python-reimplemented
    python scripts/flora_fauna_data.py            # all stages
    python scripts/flora_fauna_data.py assemble   # only rebuild the JSON from the cache

Every network answer is cached in ../.flora_fauna_cache/ (outside the repo; set FLORA_FAUNA_CACHE to move it), so a run
that is interrupted simply continues. Be polite: Wikipedia and Wikimedia Commons
rate-limit busy IP addresses; the pauses below keep well under their limits.

Sources (all free to reuse, credited on every page):
  GBIF occurrence data (species recorded in Suriname, records per district/month/year)
  Wikidata (names in EN/NL/ES/ZH, IUCN status, photo, Wikipedia links)
  iNaturalist (names, licensed photos, observations in Suriname)
  Wikipedia (intro text, CC BY-SA 4.0), Wikimedia Commons (photo licences)
  NZCS checklists (endemic / threatened / introduced) and GRIIS Suriname.
Hand-curated: data/flora_fauna/local_names.json (Sranan / Surinamese Dutch names).
"""
import datetime
import hashlib
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from flora_fauna_taxa import classify, IUCN_WD, IUCN_INAT, DISTRICTS, GROUP_KEYS, SUBGROUPS  # noqa: E402

C = Path(os.environ.get("FLORA_FAUNA_CACHE", ROOT.parent / ".flora_fauna_cache"))
OUT = ROOT / "data" / "flora_fauna"
HTTP = C / "http"
S = requests.Session()
S.headers["User-Agent"] = "ExploreSurinameBot/1.0 (https://exploresuriname.com; species directory build)"
BOR = ["HUMAN_OBSERVATION", "PRESERVED_SPECIMEN", "MACHINE_OBSERVATION", "OBSERVATION",
       "MATERIAL_SAMPLE", "OCCURRENCE", "MATERIAL_CITATION"]
SPARQL = "https://query.wikidata.org/sparql"


def get(url, params=None, data=None, pause=0.0, tries=12):
    """GET/POST with a disk cache and polite retries (honours Retry-After)."""
    key = hashlib.sha1((url + json.dumps(params, sort_keys=True) + json.dumps(data, sort_keys=True)).encode()).hexdigest()
    p = HTTP / key[:2] / key
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    for i in range(tries):
        try:
            r = (S.post(url, params=params, data=data, timeout=90, headers={"Accept": "application/sparql-results+json"})
                 if data is not None else S.get(url, params=params, timeout=90))
            if r.status_code in (429, 500, 502, 503, 504):
                ra = r.headers.get("retry-after")
                time.sleep(float(ra) + 2 if (ra and ra.isdigit()) else min(90, 2 ** i + random.random()))
                continue
            t = "null" if r.status_code == 404 else (r.raise_for_status() or r.text)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(t, encoding="utf-8")
            if pause:
                time.sleep(pause)
            return json.loads(t)
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(min(60, 2 ** i))
    raise RuntimeError("failed " + url)


def save(name, obj):
    (C / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def load(name, default=None):
    try:
        return json.loads((C / name).read_text(encoding="utf-8"))
    except Exception:
        return default


# ── 1. species recorded in Suriname (GBIF) ───────────────────────────────────
def stage_species():
    counts = {}
    for kk in (1, 6, 5):   # Animalia, Plantae, Fungi
        r = get("https://api.gbif.org/v1/occurrence/search",
                dict(country="SR", kingdomKey=kk, limit=0, facet="speciesKey", facetLimit=100000,
                     basisOfRecord=BOR, occurrenceStatus="PRESENT"))
        for c in r["facets"][0]["counts"]:
            counts[c["name"]] = c["count"]
    out = {}
    for i, k in enumerate(counts):
        d = get(f"https://api.gbif.org/v1/species/{k}")
        if d:
            out[k] = {f: d.get(f) for f in ("key", "canonicalName", "scientificName", "authorship", "kingdom", "phylum",
                                            "class", "order", "family", "genus", "rank", "taxonomicStatus", "vernacularName")}
            out[k]["n"] = counts[k]
        if i % 2000 == 0:
            print("  gbif species", i, len(counts), flush=True)
    save("gbif_species.json", out)


# ── 2. Wikidata: names, photo, IUCN, Wikipedia links (by GBIF id, then by name) ─
Q_BY_GBIF = """SELECT ?gbif ?item ?img ?iucn ?inat ?en ?nl ?es ?zh WHERE {
 VALUES ?gbif { %s } ?item wdt:P846 ?gbif .
 OPTIONAL { ?item wdt:P18 ?img } OPTIONAL { ?item wdt:P141 ?iucn } OPTIONAL { ?item wdt:P3151 ?inat }
 OPTIONAL { ?en schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> }
 OPTIONAL { ?nl schema:about ?item ; schema:isPartOf <https://nl.wikipedia.org/> }
 OPTIONAL { ?es schema:about ?item ; schema:isPartOf <https://es.wikipedia.org/> }
 OPTIONAL { ?zh schema:about ?item ; schema:isPartOf <https://zh.wikipedia.org/> } }"""
Q_BY_NAME = Q_BY_GBIF.replace("?gbif ?item", "?name ?item").replace(
    "VALUES ?gbif { %s } ?item wdt:P846 ?gbif .", "VALUES ?name { %s } ?item wdt:P225 ?name .")
Q_NAMES = """SELECT ?item ?l ?lang WHERE { VALUES ?item { %s } { ?item rdfs:label ?l } UNION { ?item wdt:P1843 ?l }
 BIND(LANG(?l) AS ?lang) FILTER(LANG(?l) IN ("en","nl","es","zh","zh-hans","zh-cn","zh-hant","zh-tw","zh-hk")) }"""


def _wd_rows(rows, keyf, out):
    for x in rows:
        k = keyf(x)
        e = out.setdefault(k, {"item": x["item"]["value"].rsplit("/", 1)[1], "img": [], "iucn": [], "wiki": {}})
        if "img" in x and x["img"]["value"] not in e["img"]:
            e["img"].append(x["img"]["value"])
        if "iucn" in x and x["iucn"]["value"].rsplit("/", 1)[1] not in e["iucn"]:
            e["iucn"].append(x["iucn"]["value"].rsplit("/", 1)[1])
        if "inat" in x:
            e["inat"] = x["inat"]["value"]
        for L in ("en", "nl", "es", "zh"):
            if L in x:
                e["wiki"][L] = x[L]["value"]


def stage_wikidata():
    gb = load("gbif_species.json")
    keys = [k for k, v in gb.items() if v and v.get("rank") == "SPECIES"]
    out = {}
    for i in range(0, len(keys), 250):
        r = get(SPARQL, {"format": "json"}, data={"query": Q_BY_GBIF % " ".join(f'"{k}"' for k in keys[i:i + 250])})
        _wd_rows(r["results"]["bindings"], lambda x: x["gbif"]["value"], out)
    miss = {v["canonicalName"]: k for k, v in gb.items()
            if v and v.get("rank") == "SPECIES" and v.get("canonicalName") and k not in out}
    names = list(miss)
    for i in range(0, len(names), 200):
        r = get(SPARQL, {"format": "json"}, data={"query": Q_BY_NAME % " ".join(json.dumps(n) for n in names[i:i + 200])})
        _wd_rows(r["results"]["bindings"], lambda x: miss[x["name"]["value"]], out)
    items = {v["item"]: g for g, v in out.items()}
    il = list(items)
    for i in range(0, len(il), 300):
        r = get(SPARQL, {"format": "json"}, data={"query": Q_NAMES % " ".join("wd:" + q for q in il[i:i + 300])})
        for x in r["results"]["bindings"]:
            g = items[x["item"]["value"].rsplit("/", 1)[1]]
            lst = out[g].setdefault("names", {}).setdefault(x["lang"]["value"], [])
            if x["l"]["value"] not in lst:
                lst.append(x["l"]["value"])
    save("wd.json", out)
    print("  wikidata", len(out))


# ── 3. iNaturalist: observations in Suriname + names and licensed photos ─────
def stage_inat():
    res = {}
    for loc in ("en", "nl", "es", "zh-CN"):
        page = 1
        while True:
            r = get("https://api.inaturalist.org/v1/observations/species_counts",
                    dict(place_id=7827, verifiable="true", per_page=500, page=page, locale=loc), pause=1.0)
            for x in r["results"]:
                t = x["taxon"]
                res.setdefault(t["id"], {"id": t["id"], "name": t["name"], "obs": x["count"]})
            if page * 500 >= r["total_results"]:
                break
            page += 1
    save("inat_sr.json", res)
    wd = load("wd.json")
    ids = sorted({int(v["inat"]) for v in wd.values() if v.get("inat", "").isdigit()} | {int(k) for k in res})
    out = load("inat_taxa.json", {}) or {}
    todo = [i for i in ids if str(i) not in out]
    for loc in ("en", "nl", "es", "zh-CN"):
        for i in range(0, len(todo), 30):
            r = get("https://api.inaturalist.org/v1/taxa/" + ",".join(map(str, todo[i:i + 30])), dict(locale=loc), pause=1.0)
            for t in (r or {}).get("results", []):
                e = out.setdefault(str(t["id"]), {"id": t["id"], "name": t["name"], "rank": t.get("rank"), "names": {}})
                if t.get("preferred_common_name"):
                    e["names"][loc] = t["preferred_common_name"]
                if loc == "en":
                    e["photos"] = [{"id": p["photo"]["id"], "lic": p["photo"].get("license_code"),
                                    "attr": p["photo"].get("attribution"), "url": p["photo"].get("url")}
                                   for p in t.get("taxon_photos", [])]
                    e["cs"] = [{"s": c.get("status"), "a": c.get("authority"), "iucn": c.get("iucn"),
                                "place": (c.get("place") or {}).get("name")} for c in t.get("conservation_statuses", [])]
    save("inat_taxa.json", out)
    print("  inaturalist", len(out))


# ── 4. Suriname checklists (NZCS, GRIIS) ─────────────────────────────────────
CHECKLISTS = {"endemic": "c7bcf931-2494-4206-91b0-bbd00700cae2", "endangered": "c3413793-cd8e-4f74-b0b7-e1f0c155102c",
              "introduced": "d1756e5c-0667-4b48-bdbb-3d59abf2bcab", "griis": "e98cc325-bc7a-4489-a841-15b734ab2514"}


def stage_checklists():
    out = {}
    for k, ds in CHECKLISTS.items():
        off, rows = 0, []
        while True:
            r = get("https://api.gbif.org/v1/species", dict(datasetKey=ds, limit=1000, offset=off))
            rows += r["results"]
            if r["endOfRecords"]:
                break
            off += 1000
        out[k] = [{"name": x.get("canonicalName") or x.get("scientificName"), "nub": x.get("nubKey"), "rank": x.get("rank")} for x in rows]
    save("checklists.json", out)


# ── 5. GBIF: records per district, month and year (profile candidates) ───────
def stage_facets():
    wd = load("wd.json")
    cand = [g for g, v in wd.items() if v["wiki"] and (v["img"] or v.get("inat"))]
    res = load("facets.json", {}) or {}
    for i, k in enumerate(cand):
        if k in res:
            continue
        r = get("https://api.gbif.org/v1/occurrence/search",
                dict(country="SR", speciesKey=k, limit=0, facet=["gadmLevel1Gid", "month", "year"], facetLimit=400,
                     basisOfRecord=BOR, occurrenceStatus="PRESENT"))
        res[k] = {fc["field"]: {x["name"]: x["count"] for x in fc["counts"]} for fc in (r or {}).get("facets", [])}
        if i % 1000 == 0:
            print("  facets", i, len(cand), flush=True)
            save("facets.json", res)
    save("facets.json", res)


# ── 6. Wikipedia intros (EN/NL/ES/ZH) ────────────────────────────────────────
def stage_wiki():
    wd = load("wd.json")
    out = load("wiki.json", {}) or {}
    for L in ("en", "es", "zh", "nl"):
        res = out.setdefault(L, {})
        titles = sorted({urllib.parse.unquote(v["wiki"][L].rsplit("/wiki/", 1)[1]).replace("_", " ")
                         for v in wd.values() if L in v["wiki"]} - set(res))
        for i in range(0, len(titles), 20):
            b = titles[i:i + 20]
            r = get(f"https://{L}.wikipedia.org/w/api.php",
                    dict(action="query", prop="extracts", exintro=1, explaintext=1, exlimit=20, titles="|".join(b),
                         format="json", formatversion=2, redirects=1), pause=2.0)
            q = r.get("query", {})
            m = {t: t for t in b}
            for n in q.get("normalized", []):
                m[n["to"]] = n["from"]
            rd = {x["to"]: x["from"] for x in q.get("redirects", [])}
            for pg in q.get("pages", []):
                if pg.get("missing"):
                    continue
                t = pg["title"]
                o = m.get(rd.get(t, t), rd.get(t, t))
                res[o] = {"t": t, "x": pg.get("extract", "")}
        save("wiki.json", out)
        print("  wikipedia", L, len(res))


# ── 7. Wikimedia Commons: licence + author + thumbnail of Wikidata photos ────
COMMONS_OK = re.compile(r"^(CC BY(-SA)? [\d.]+( \w+)?|CC0|Public domain|No restrictions|Copyrighted free use)$")


def stage_commons():
    wd = load("wd.json")
    out = load("commons.json", {}) or {}
    raw = load("commons_raw.json", {}) or {}
    files = sorted({urllib.parse.unquote(f.rsplit("/", 1)[1]) for v in wd.values() for f in v["img"][:2]} - set(raw))
    for i in range(0, len(files), 40):
        b = files[i:i + 40]
        r = get("https://commons.wikimedia.org/w/api.php",
                dict(action="query", prop="imageinfo", iiprop="url|extmetadata|mime", iiurlwidth=500,
                     titles="|".join("File:" + f for f in b), format="json", formatversion=2), pause=2.0)
        q = r.get("query", {})
        norm = {n["to"]: n["from"] for n in q.get("normalized", [])}
        for pg in q.get("pages", []):
            t = norm.get(pg["title"], pg["title"])
            name = t[5:] if t.startswith("File:") else t
            ii = (pg.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata", {})

            def g(k):
                return re.sub("<[^>]+>", "", __import__("html").unescape((em.get(k) or {}).get("value", ""))).strip()
            raw[name] = {"thumb": ii.get("thumburl", ""), "mime": ii.get("mime", ""), "lic": g("LicenseShortName"),
                         "lu": g("LicenseUrl"), "by": g("Artist")[:80]}
        for f in b:
            raw.setdefault(f, {})
    for n, v in raw.items():
        u = (v.get("thumb") or "").split("?")[0]
        if v.get("mime") in ("image/jpeg", "image/png") and COMMONS_OK.match(v.get("lic", "")) and "/500px-" in u:
            out[n] = {"thumb": u.replace("/500px-", "/{w}px-"), "lic": v["lic"], "lu": v.get("lu", ""),
                      "by": v.get("by") or "Unknown author"}
    save("commons_raw.json", raw)
    save("commons.json", out)
    print("  commons", len(out))


# ── 8. assemble data/flora_fauna/species.json + text.json ────────────────────
def stage_assemble():
    import opencc
    T2S = opencc.OpenCC("t2s")
    gb = json.load(open(C / 'gbif_species.json'))
    wd = json.load(open(C / 'wd.json'))
    inat_sr = json.load(open(C / 'inat_sr.json'))
    inat = {int(k): v for k, v in json.load(open(C / 'inat_taxa.json')).items()}
    try:
        wiki = json.load(open(C / 'wiki.json'))
    except Exception:
        wiki = {}
    try:
        facets = json.load(open(C / 'facets.json'))
    except Exception:
        facets = {}
    try:
        commons = json.load(open(C / 'commons.json'))
    except Exception:
        commons = {}
    checklists = json.load(open(C / 'checklists.json'))
    local = json.load(open(OUT / 'local_names.json'))

    inat_by_name = {}
    for v in inat.values():
        inat_by_name.setdefault(v['name'], v)
    sr_obs = {}
    for v in inat_sr.values():
        sr_obs[v['name']] = v['obs']


    def species_part(n):
        p = (n or '').split()
        return ' '.join(p[:2]) if len(p) >= 2 else n


    endemic = {species_part(x['name']) for x in checklists['endemic']}
    endemic_nub = {x['nub'] for x in checklists['endemic'] if x['rank'] == 'SPECIES'}
    thr = {species_part(x['name']) for x in checklists['endangered']}
    intro = {species_part(x['name']) for x in checklists['introduced']} | {species_part(x['name']) for x in checklists['griis']}

    LATIN_RE = re.compile(r'^[A-Z][a-z]+ [a-z\-]+$')


    def has_cjk(s):
        return any('一' <= c <= '鿿' for c in s)


    def clean_name(v, sci, lang, corro=None):
        if not v:
            return None
        v = v.strip()
        if v.lower() == sci.lower():
            return None
        g = sci.split()[0]
        if lang != 'zh' and (LATIN_RE.match(v) and v.split()[0] == g):
            return None
        if v.lower() == g.lower() and not any(x.lower() == v.lower() for x in (corro or [])):
            return None
        if lang == 'zh':
            v = T2S.convert(v)
            if not has_cjk(v):
                return None
        if len(v) > 60:
            return None
        return v


    def pick_names(sci, w, it, gbif_vern, is_bird=False, lead_names=None):
        lead_names = lead_names or {}
        wn = (w or {}).get('names', {})
        out = {}
        en_i = (it or {}).get('names', {}).get('en')
        # English
        out['en'] = clean_name(en_i, sci, 'en') or next((clean_name(x, sci, 'en') for x in wn.get('en', []) if clean_name(x, sci, 'en')), None) \
            or clean_name(gbif_vern, sci, 'en')
        for lg, il in (('nl', 'nl'), ('es', 'es')):
            cand = (it or {}).get('names', {}).get(il)
            wl = [x for x in (clean_name(y, sci, lg) for y in wn.get(lg, [])) if x]
            v = clean_name(cand, sci, lg, wn.get(lg, []))
            if v and en_i and v.lower() == en_i.lower() and not any(x.lower() == v.lower() for x in wl):
                v = None   # iNat fell back to the English name
            # Spanish: iNat often carries a regional name (Otorongo for the jaguar);
            # the Wikidata label is the general one. Birds keep iNat's standard list.
            lead = lead_names.get(lg)
            if lg == 'es' and not is_bird and lead:
                out[lg] = lead
            else:
                out[lg] = v or lead or (wl[0] if wl else None)
        zc = []
        for k in ('zh-hans', 'zh-cn', 'zh', 'zh-hant', 'zh-tw', 'zh-hk'):
            zc += wn.get(k, [])
        zi = (it or {}).get('names', {}).get('zh-CN')
        zh = clean_name(zi, sci, 'zh') if zi and has_cjk(zi) else None
        if not zh:
            zh = next((clean_name(x, sci, 'zh') for x in zc if clean_name(x, sci, 'zh')), None)
        out['zh'] = zh
        return {k: v for k, v in out.items() if v}


    OK_LIC = {'cc0': ('CC0', 'https://creativecommons.org/publicdomain/zero/1.0/'),
              'cc-by': ('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
              'cc-by-sa': ('CC BY-SA 4.0', 'https://creativecommons.org/licenses/by-sa/4.0/'),
              'pd': ('Public domain', 'https://creativecommons.org/publicdomain/mark/1.0/')}


    def inat_photo(it):
        for p in (it or {}).get('photos', []) or []:
            lic = (p.get('lic') or '').lower()
            if lic in OK_LIC and p.get('url'):
                u = p['url']
                u = re.sub(r'/(square|small|medium|large|original|thumb)\.(jpe?g|png|gif)', r'/{size}.\2', u, flags=re.I)
                if '{size}' not in u:
                    continue
                attr = (p.get('attr') or '').replace('\n', ' ').strip()
                by = re.sub(r'^\(c\)\s*', '', attr).split(',')[0].strip()
                if by.lower().startswith('no rights reserved') or not by:
                    m_up = re.search(r'uploaded by ([^,()]+)', attr)
                    by = m_up.group(1).strip() if m_up else 'iNaturalist user'
                short, lu = OK_LIC[lic]
                credit = f"{by}, {short}, via iNaturalist" if lic != 'pd' else f"{by}, public domain, via iNaturalist"
                return {'s': 'inat', 'u': u, 'c': credit, 'by': by, 'l': short, 'lu': lu,
                        'p': f"https://www.inaturalist.org/photos/{p['id']}"}
        return None


    def commons_photo(w):
        for f in (w or {}).get('img', []):
            name = f.rsplit('/', 1)[1]
            name = __import__('urllib.parse').parse.unquote(name)
            meta = commons.get(name)
            if not meta or not meta.get('thumb'):
                continue
            return {'s': 'commons', 'u': meta['thumb'], 'c': f"{meta['by']}, {meta['lic']}, via Wikimedia Commons",
                    'by': meta['by'], 'l': meta['lic'], 'lu': meta.get('lu', ''),
                    'p': 'https://commons.wikimedia.org/wiki/File:' + name.replace(' ', '_')}
        return None


    def wiki_text(w):
        out = {}
        for lg in ('en', 'nl', 'es', 'zh'):
            url = (w or {}).get('wiki', {}).get(lg)
            if not url:
                continue
            t = __import__('urllib.parse').parse.unquote(url.rsplit('/wiki/', 1)[1]).replace('_', ' ')
            e = wiki.get(lg, {}).get(t)
            if not e or not e.get('x'):
                continue
            x = e['x'].strip()
            if lg == 'zh':
                x = T2S.convert(x)
            x = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', x).replace('\u2009', ' ')
            x = re.sub(r'\[(?:cita requerida|citation needed|bron\?|來源請求|来源请求|需要引用)\]', '', x)
            x = re.sub(r' {2,}', ' ', x)
            x = re.sub(r'\n{2,}', '\n', x)
            x = re.sub(r'\s*\(\s*\)', '', x)          # empty brackets left by stripped templates
            x = re.sub(r'\(\s*[;,]\s*', '(', x)
            # trim to ~1100 chars at a sentence boundary
            if len(x) > 1100:
                cut = x[:1100]
                m = max(cut.rfind('. '), cut.rfind('。'), cut.rfind('.\n'))
                x = cut[:m + 1] if m > 300 else cut.rsplit(' ', 1)[0] + '…'
            out[lg] = {'t': e['t'], 'x': x}
        return out


    def slugify(s):
        s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
        s = re.sub(r"[’']", '', s.lower())
        return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


    RESERVED = set(GROUP_KEYS) | {'about', 'assets', 'trees', 'fruits-crops', 'sranan-names', 'endemic', 'threatened', 'introduced'}

    loc_species = {k: [[x['n'], x['l'], x.get('dict')] for x in v] for k, v in local['species'].items() if v}

    rows = []
    texts = {}
    for k, g in gb.items():
        if not g or g.get('rank') != 'SPECIES' or not g.get('canonicalName'):
            continue
        sci = g['canonicalName']
        t = {x: g.get(x) for x in ('kingdom', 'phylum', 'class', 'order', 'family', 'genus')}
        grp, sub = classify(t)
        if not grp:
            continue
        w = wd.get(k) or wd.get(str(k))
        it = None
        if w and w.get('inat', '').isdigit():
            it = inat.get(int(w['inat']))
        if not it:
            it = inat_by_name.get(sci)
        tx_ = wiki_text(w)
        leads = {}
        for lg, art in (('es', r'(?:El|La|Los|Las)'), ('nl', r'(?:De|Het)')):
            x = (tx_.get(lg) or {}).get('x', '')
            m = re.match(art + r' ([a-záéíóúñüë][a-záéíóúñüë\- ]{2,45}?)\s*[,(\u200b]', x)
            bad = {'es', 'is', 'een', 'una', 'un', 'de', 'del', 'van', 'het', 'la', 'el'}
            if (m and len(m.group(1).split()) <= 5 and m.group(1).split()[0].lower() != sci.split()[0].lower()
                    and m.group(1).split()[-1] not in bad and not (set(m.group(1).split()) & {'es', 'is', 'een', 'una'})):
                leads[lg] = re.split(r' (?:o|u|of|y|en) ', m.group(1).strip())[0]
        names = pick_names(sci, w, it, g.get('vernacularName'), grp == 'birds', leads)
        iu = None
        for q in (w or {}).get('iucn', []):
            if q in IUCN_WD:
                iu = IUCN_WD[q]
        if not iu and it:
            for c in it.get('cs', []):
                if (c.get('a') or '').startswith('IUCN') and not c.get('place') and c.get('iucn') in IUCN_INAT:
                    iu = IUCN_INAT[c['iucn']]
        flags = ''
        if sci in endemic or int(k) in endemic_nub:
            flags += 'E'
        if sci in thr:
            flags += 'T'
        if sci in intro:
            flags += 'I'
        img = inat_photo(it) or commons_photo(w)
        obs = sr_obs.get(sci) or sr_obs.get((it or {}).get('name'), 0)
        r = {'k': int(k), 's': sci, 'a': g.get('authorship') or '', 'tx': [t[x] or '' for x in ('kingdom', 'phylum', 'class', 'order', 'family', 'genus')],
             'g': grp, 'sg': sub, 'n': names, 'r': g.get('n') or 0, 'o': obs}
        if sci in loc_species:
            r['ln'] = loc_species[sci]
        if iu:
            r['iu'] = iu
        if flags:
            r['f'] = flags
        if img:
            r['img'] = img
        if w:
            r['wd'] = w['item']
        if it:
            r['in'] = it['id']
        fc = facets.get(k) or facets.get(str(k)) or {}
        if fc:
            d = {DISTRICTS[gid]: n for gid, n in fc.get('GADM_LEVEL_1_GID', {}).items() if gid in DISTRICTS}
            if d:
                r['d'] = d
            m = fc.get('MONTH', {})
            if m:
                r['m'] = [m.get(str(i), 0) for i in range(1, 13)]
            ys = sorted(int(y) for y in fc.get('YEAR', {}) if y.isdigit())
            if ys:
                r['y'] = [ys[0], ys[-1]]
        # profile rule: a real description + (photo or a common name)
        best_len = max([len(v['x']) for v in tx_.values()] or [0])
        if best_len >= 260 and (img or names.get('en')):
            r['_cand'] = True
            texts[sci] = tx_
        rows.append(r)

    # slugs for profiles: English name when unique, else scientific name
    from collections import Counter
    cands = [r for r in rows if r.pop('_cand', False)]
    c = Counter(slugify(r['n'].get('en', '')) for r in cands if r['n'].get('en'))
    used = set()
    for r in sorted(cands, key=lambda r: (-(r['o'] or 0), -(r['r'] or 0))):
        en = r['n'].get('en')
        s = slugify(en) if en and c[slugify(en)] == 1 else ''
        if not s or s in RESERVED or s in used or len(s) < 3:
            s = slugify(r['s'])
        if s in used or s in RESERVED:
            s = slugify(r['s']) + '-' + str(r['k'])
        used.add(s)
        r['p'] = s
    text_out = {r['p']: texts[r['s']] for r in cands}
    rows.sort(key=lambda r: (GROUP_KEYS.index(r['g']), -(r['o'] or 0), -(r['r'] or 0), r['s']))
    today = datetime.date.today().isoformat()
    json.dump({'updated': today, 'species': rows}, open(OUT / 'species.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    json.dump(text_out, open(OUT / 'text.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('species', len(rows), 'profiles', len(cands), 'with img', sum(1 for r in rows if r.get('img')),
          'profile imgs', sum(1 for r in cands if r.get('img')))
    print(Counter(r['g'] for r in rows))
    print(Counter(r['g'] for r in cands))


STAGES = {"species": stage_species, "wikidata": stage_wikidata, "inat": stage_inat, "checklists": stage_checklists,
          "facets": stage_facets, "wiki": stage_wiki, "commons": stage_commons, "assemble": stage_assemble}

if __name__ == "__main__":
    HTTP.mkdir(parents=True, exist_ok=True)
    todo = sys.argv[1:] or list(STAGES)
    for s in todo:
        print("stage", s, flush=True)
        STAGES[s]()
