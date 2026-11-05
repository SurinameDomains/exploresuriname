#!/usr/bin/env python3
"""
scrape_ebs.py — EBS power outages -> data/ebs_outages.json
Source: https://nvebs.com/elektriciteit/stroom-onderbrekingen

v2 (5 Nov 2026). EBS changed its notice text around 3 Nov 2026:
  old: "Gepland onderhoud: Wanica zondag 1 november 2026 tussen 08:00-17:00" + streets
  new: "GEPLAND ONDERHOUD DONDERDAG 5 NOVEMBER 2026 TUSSEN 8:30 EN 15:00 UUR" + streets,
       no district, and ONE page can hold several notices (each with its own map link).
The v1 parser only knew the old form, so the site showed "GEPLAND ONDERHOUD" with no
streets and treated it as an all-day outage.

Now:
  1. main page -> notice links (div.notice-slider-desktop > div.notice-text)
  2. each notice page -> the text column is split into blocks at every
     "Gepland onderhoud ... <date> [tussen] HH:MM (-|en|tot) HH:MM [uur]" header;
     one output entry per block (time, streets, map link, district)
  3. district: from the old header form when present, else looked up from the street
     names in OpenStreetMap (Nominatim, max 1 request/s, cached in
     data/ebs_geocache.json so each street is asked once)
A missing slider (EBS layout change) keeps the old file instead of writing an empty
list, so a broken scraper goes stale (the site then stops claiming "no outages")
rather than turning into a false all-clear.
"""

import json, re, sys, time, unicodedata, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL_MAIN = "https://nvebs.com/elektriciteit/stroom-onderbrekingen"
OUT = Path(__file__).parent.parent / "data" / "ebs_outages.json"
GEOCACHE = Path(__file__).parent.parent / "data" / "ebs_geocache.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl,en;q=0.9",
}
NOMINATIM = "https://nominatim.openstreetmap.org/search"
NOMINATIM_UA = "ExploreSuriname-outages/2.0 (+https://exploresuriname.com/contact)"
GEO_MAX_NEW = 30          # new street lookups per run (1.1 s each)
GEO_RETRY_DAYS = 30       # a street OSM did not know is asked again after this

SR_TZ = timezone(timedelta(hours=-3))
DISTRICTS = ["Paramaribo", "Wanica", "Commewijne", "Saramacca", "Para", "Marowijne",
             "Nickerie", "Coronie", "Brokopondo", "Sipaliwini"]

_MONTHS_NL = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "augustus": 8, "september": 9,
    "oktober": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mrt": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}
_WD = r"(?:maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)"
# One notice header. The time is optional (a header without one still splits blocks).
# "\d*" after the minutes swallows EBS typos such as "12:000".
HDR = re.compile(
    r"gepland\s+onderhoud\s*:?\s*(?P<pre>[^\n\d]{0,40}?)\s*(?:" + _WD + r"\s+)?"
    r"(?P<d>\d{1,2})\s+(?P<m>[a-z]+)\s+(?P<y>\d{4})"
    r"(?:[ \t]*(?:(?:tussen|van)\s+)+(?P<h1>\d{1,2})[:.](?P<m1>\d{2})\d*\s*(?:u(?:ur)?\.?)?"
    r"\s*(?:-|–|en|tot)\s*(?P<h2>\d{1,2})[:.](?P<m2>\d{2})\d*\s*(?:u(?:ur)?\b\.?)?)?",
    re.IGNORECASE)


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_dutch_date(text):
    """Date object from text like 'DINSDAG 26 MEI 2026'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        mon = _MONTHS_NL.get(m.group(2).lower())
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1))).date()
            except Exception:
                pass
    return None


def fmt_date_nl(text):
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        return f"{m.group(1)} {m.group(2).capitalize()} {m.group(3)}"
    return text


def _hm(h, m):
    h, m = int(h), int(m)
    if 0 <= h <= 24 and 0 <= m < 60:
        return f"{h:02d}:{m:02d}"
    return None


def split_blocks(text):
    """Split a notice text into [{district?, date_iso, time?, area}] blocks.

    The page headline repeated at the top (a header followed directly by another
    header, no streets and no time) is dropped."""
    text = (text or "").replace("\r", "")
    hs = list(HDR.finditer(text))
    out = []
    for i, h in enumerate(hs):
        seg = text[h.end(): hs[i + 1].start() if i + 1 < len(hs) else len(text)]
        seg = re.sub(r"kaart(\s+openen)?\s*:?", " ", seg, flags=re.IGNORECASE)
        seg = clean(seg).strip(" .,:;")
        has_time = bool(h.group("h1"))
        if not seg and not has_time:
            continue
        mon = _MONTHS_NL.get(h.group("m").lower())
        try:
            d = datetime(int(h.group("y")), mon, int(h.group("d"))).date() if mon else None
        except Exception:
            d = None
        b = {"date_iso": str(d) if d else "", "area": seg}
        if has_time:
            t1, t2 = _hm(h.group("h1"), h.group("m1")), _hm(h.group("h2"), h.group("m2"))
            if t1 and t2:
                b["time"] = f"{t1} – {t2}"
        pre = clean(h.group("pre") or "").strip(" :,").title()
        if pre in DISTRICTS:
            b["district"] = pre
        out.append(b)
    return out


# ---------------------------------------------------------------- streets
_SUFFIX = re.compile(r"[\s,]*(?:\ben\s+)?alle\s+zijwegen.*$", re.IGNORECASE)


def streets_of(area):
    """(main streets, boundary streets) named in an EBS street list."""
    core = _SUFFIX.sub("", area or "").strip(" .,")
    mains, cross = [], []
    for part in re.split(r"\s*[,;]\s*", core):
        part = clean(part).strip(" .")
        if not part:
            continue
        m = re.match(r"^(?:(?:gedeelte|geheel|gedeeltelijk|deel)\s+(?:van\s+(?:de\s+)?)?)?(?P<s>.+?)"
                     r"(?:\s+tussen\s+(?P<a>.+?)(?:\s+en\s+(?P<b>.+))?)?$", part, re.IGNORECASE)
        if not m:
            continue
        s = m.group("s").strip()
        if 2 < len(s) < 60 and s not in mains:
            mains.append(s)
        for x in (m.group("a"), m.group("b")):
            x = (x or "").strip()
            if 2 < len(x) < 60 and x not in cross and x not in mains:
                cross.append(x)
    return mains, cross


def _key(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _load_cache():
    try:
        c = json.loads(GEOCACHE.read_text(encoding="utf-8"))
        return c if isinstance(c, dict) else {}
    except Exception:
        return {}


def geocode(street, cache, budget):
    """[{district, lat, lon}] for a street name; [] when OSM has none. Cached."""
    k = _key(street)
    if not k:
        return []
    hit = cache.get(k)
    if isinstance(hit, dict):
        age = datetime.now(timezone.utc).timestamp() - hit.get("t", 0)
        if hit.get("r") or age < GEO_RETRY_DAYS * 86400:
            return hit.get("r") or []
    if budget[0] <= 0:
        return []
    budget[0] -= 1
    q = urllib.parse.urlencode({"q": f"{street}, Suriname", "countrycodes": "sr", "format": "jsonv2",
                                "addressdetails": 1, "limit": 5})
    res = []
    try:
        time.sleep(1.1)
        req = urllib.request.Request(f"{NOMINATIM}?{q}", headers={"User-Agent": NOMINATIM_UA, "Accept-Language": "nl"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        for x in data:
            if (x.get("category") or x.get("class")) != "highway":
                continue
            st = (x.get("address") or {}).get("state", "")
            st = next((d for d in DISTRICTS if d.lower() == st.lower()), "")
            if st:
                res.append({"district": st, "lat": round(float(x["lat"]), 5), "lon": round(float(x["lon"]), 5)})
    except Exception as e:
        print(f"    [geocode error] {street}: {e}")
        return []          # not cached: asked again next run
    cache[k] = {"r": res, "t": int(datetime.now(timezone.utc).timestamp())}
    return res


def district_for(mains, cache, budget):
    """Most likely district for a list of streets, plus one map point per street.

    Each street votes once for every district it exists in; a name that exists in
    two districts is settled by the other streets of the same notice."""
    votes, found = Counter(), []
    for s in mains[:6]:
        r = geocode(s, cache, budget)
        if r:
            found.append(r)
            for d in {x["district"] for x in r}:
                votes[d] += 1
    if not votes:
        return "", []
    top = votes.most_common(2)
    if len(top) > 1 and top[0][1] == top[1][1]:
        return "", []      # a tie is a guess: show no district rather than a wrong one
    best, pts = top[0][0], []
    for r in found:
        p = next((x for x in r if x["district"] == best), None)
        if p:
            pts.append([p["lat"], p["lon"]])
    return best, pts


# ---------------------------------------------------------------- pages
def fetch_detail_full(url):
    """(meta description, column text with newlines, [map links]) from a notice page."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(fetch_html(url), "html.parser")
        meta = (soup.find("meta", {"name": "description"}) or soup.find("meta", {"property": "og:description"}))
        desc = meta["content"] if meta and meta.get("content") else None
        texts, maps = [], []
        for col in soup.select("section.section div.column.is-half"):
            t = col.get_text("\n")
            if len(clean(t)) <= 40:
                continue
            for a in col.find_all("a", href=True):
                if "gisenterprise" in a["href"] or "kaart" in a.get_text(" ").lower():
                    maps.append(a["href"].strip())
            texts.append(t)
        return desc, "\n".join(texts), maps
    except Exception as e:
        print(f"    [detail fetch error] {e}")
    return None, "", []


def parse_main_page(html):
    """Notice links from the slider. None when the slider is gone (layout change)."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    today = datetime.now(SR_TZ).date()
    slider = soup.find("div", class_="notice-slider-desktop")
    if not slider:
        return None
    entries, seen = [], set()
    for div in slider.find_all("div", class_="notice-text"):
        title = clean(div.get_text(" ").replace("Lees meer", "").strip())
        a = div.find("a")
        link = a["href"] if a and a.get("href") else ""
        if link and not link.startswith("http"):
            link = "https://nvebs.com" + link
        if link in seen:
            continue
        seen.add(link)
        d = parse_dutch_date(title)
        if not d:
            continue
        if d < today:
            print(f"    [skipped past] {title}")
            continue
        entries.append({"title": title, "date": fmt_date_nl(title), "date_iso": str(d), "type": "planned", "link": link})
        print(f"    [found] {title}")
    return entries


def expand(entry, desc, text, maps, cache, budget):
    """One notice page -> one or more outage entries."""
    blocks = split_blocks(text) or split_blocks(desc or "")
    if not blocks:
        e = dict(entry)
        body = clean(re.sub(r"kaart(\s+openen)?\s*:?", " ", text or "", flags=re.IGNORECASE))
        if body:
            e["body"] = body
        if maps:
            e["map"] = maps[0]
        return [e]
    out = []
    for i, b in enumerate(blocks):
        e = dict(entry)
        if b.get("date_iso"):
            e["date_iso"] = b["date_iso"]
        if b.get("time"):
            e["time"] = b["time"]
        if b.get("area"):
            e["area"] = b["area"]
        mains, cross = streets_of(b.get("area", ""))
        if mains:
            e["streets"] = mains
        if cross:
            e["cross"] = cross
        dist = b.get("district", "")
        gd, pts = district_for(mains, cache, budget) if mains else ("", [])
        e["district"] = dist or gd
        e["district_src"] = "ebs" if dist else ("osm" if gd else "")
        if pts:
            e["pts"] = pts
        if len(maps) == len(blocks):
            e["map"] = maps[i]
        elif maps:
            e["map"] = maps[0]
        if len(blocks) > 1:
            e["part"] = [i + 1, len(blocks)]
        out.append(e)
    return out


def main():
    print(f"Fetching {URL_MAIN} ...")
    try:
        html = fetch_html(URL_MAIN)
    except Exception as e:
        print(f"ERROR: {e}  (keeping existing data)")
        sys.exit(0)
    try:
        notices = parse_main_page(html)
    except Exception as e:
        print(f"ERROR parsing: {e}")
        notices = None
    if notices is None:
        print("WARNING: notice slider not found (EBS layout change?); keeping existing data so it goes stale.")
        sys.exit(0)

    cache, budget = _load_cache(), [GEO_MAX_NEW]
    outages = []
    for n in notices:
        if not n.get("link"):
            outages.append(n)
            continue
        print(f"  Fetching detail: {n['link']}")
        desc, text, maps = fetch_detail_full(n["link"])
        for e in expand(n, desc, text, maps, cache, budget):
            print(f"    -> {e.get('date_iso')} {e.get('time', '?')} {e.get('district') or '-'}: "
                  f"{(e.get('area') or e.get('body') or '')[:70]}")
            outages.append(e)

    today = str(datetime.now(SR_TZ).date())
    outages = [o for o in outages if not o.get("date_iso") or o["date_iso"] >= today]
    outages.sort(key=lambda o: (o.get("date_iso", ""), o.get("time", "")))
    result = {"outages": outages, "last_updated": datetime.now(timezone.utc).isoformat(), "source": URL_MAIN, "v": 2}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        GEOCACHE.write_text(json.dumps(cache, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    except Exception as e:
        print(f"  [geocache write error] {e}")
    print(f"  Written {len(outages)} outage(s) -> {OUT}")


if __name__ == "__main__":
    main()
