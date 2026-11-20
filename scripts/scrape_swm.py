#!/usr/bin/env python3
"""
scrape_swm.py v3 (20 Nov 2026) -> data/swm_outages.json
Source: https://swm.sr/storing-onderhoud/

swm.sr publishes one card per notice again (Nov 2026):
  div.card.swmRounded > h5 "Gepland onderhoud" | "Storing(en)"
  table.noBorderTable, 3 rows: [map-marker = areas, info = announcement, calendar = "dd/mm/yyyy - dd/mm/yyyy"]
The real time window is only in the announcement text
("op woensdag 18 november- donderdag 19 november 2026 van 20.00 uur tot 04.00 uur"),
often overnight. v3 pulls out the window(s), impact, station and bulk-water note.

Output:
  notices[]  {kind planned|outage, area, station, impact off|low|low_off|"", bulk_closed,
              bulk_alt[], start_iso, end_iso, t_from, t_to, windows[[start,end]] (SR wall clock
              "YYYY-MM-DDTHH:MM"), end_dt, text, link}
  active[] / planned[]  legacy lists (homepage rail, old page JS)
  published  False only when no notice was seen for 45 days
  last_notice_seen  SR wall clock of the last scrape that found a card
A fetch error or a page without the SWM outage section keeps the old file.
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL = "https://swm.sr/storing-onderhoud/"
OUT = Path(__file__).parent.parent / "data" / "swm_outages.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0; +https://exploresuriname.com)",
    "Accept": "text/html,application/xhtml+xml",
}
SR_TZ = timezone(timedelta(hours=-3))      # Suriname, no DST
KEEP_ENDED_H = 12                          # page shows "Ended" for a while, then the notice drops
PUBLISHED_DAYS = 45

MONTHS = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
          "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12}
BOILER = re.compile(r"adviseert verbruikers|verontschuldiging|voor het ongerief|maakt hierbij bekend|"
                    r"bovenstaande gebieden", re.I)


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(t):
    return re.sub(r"\s+", " ", str(t or "")).strip()


def paras(td):
    """Cell text split on <br>: list of non-empty lines."""
    for br in td.find_all("br"):
        br.replace_with("\n")
    return [clean(x) for x in td.get_text().split("\n") if clean(x)]


def sentences(lines):
    out = []
    for ln in lines:
        if not re.search(r"[.!?:;]$", ln):      # SWM often drops the full stop before a <br>
            ln += "."
        out += [clean(s) for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", ln) if clean(s)]
    return out


def _hm(h, m):
    h, m = int(h), int(m or 0)
    if h == 24:
        h = 0
    return f"{h:02d}:{m:02d}" if 0 <= h < 24 and 0 <= m < 60 else None


def parse_times(txt):
    """'van 20.00 uur tot 04.00 uur' / 'tussen 08:00 en 16:00' / '08.00 - 14.00 uur' -> ("20:00","04:00")."""
    t = r"(\d{1,2})(?:[.:h](\d{2}))?\s*(?:uur|u\.?)?"
    m = (re.search(r"\b(?:van|vanaf)\s+" + t + r"\s*(?:tot(?:\s+en\s+met)?|-|–)\s*" + t, txt, re.I)
         or re.search(r"\btussen\s+" + t + r"\s*(?:en|-|–|tot)\s*" + t, txt, re.I)
         or re.search(r"\b(\d{1,2})[.:](\d{2})\s*(?:uur)?\s*(?:-|–|tot)\s*(\d{1,2})[.:](\d{2})", txt, re.I))
    if not m:
        return None, None
    a, b = _hm(m.group(1), m.group(2)), _hm(m.group(3), m.group(4))
    return (a, b) if a and b else (None, None)


def parse_dates(date_cell, txt):
    """dd/mm/yyyy from the calendar row; else 'd maand [yyyy]' from the text."""
    ds = re.findall(r"(\d{1,2})/(\d{1,2})/(\d{4})", date_cell or "")
    out = []
    for d, mo, y in ds:
        try:
            out.append(datetime(int(y), int(mo), int(d)).date())
        except ValueError:
            pass
    if not out:
        yr = re.search(r"\b(20\d{2})\b", txt)
        for d, mon in re.findall(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")", txt, re.I):
            if yr:
                try:
                    out.append(datetime(int(yr.group(1)), MONTHS[mon.lower()], int(d)).date())
                except ValueError:
                    pass
    if not out:
        return None, None
    return min(out), max(out)


def windows(start, end, tf, tt):
    """SR wall-clock windows. Overnight (tt <= tf): one per night from start to end
    (a single date = into the next morning). Daytime: one per day."""
    fmt = lambda d, t: d.isoformat() + "T" + t
    if not tf:
        return [[fmt(start, "00:00"), fmt(end + timedelta(days=1), "00:00")]]
    if tt <= tf:
        nights = max(1, (end - start).days)
        return [[fmt(start + timedelta(days=i), tf), fmt(start + timedelta(days=i + 1), tt)] for i in range(nights)]
    return [[fmt(start + timedelta(days=i), tf), fmt(start + timedelta(days=i), tt)]
            for i in range((end - start).days + 1)]


def impact(txt):
    low = bool(re.search(r"lage?\s+(water)?druk|drukverlaging|vermindering van de waterdruk", txt, re.I))
    off = bool(re.search(r"onderbreking|geen water|stilgelegd|afgesloten", txt, re.I))
    return "low_off" if low and off else "low" if low else "off" if off else ""


def parse_card(card, kind):
    table = card.find("table")
    if not table:
        return None
    rows = {}
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        ic = " ".join(tds[0].find("i").get("class", [])) if tds[0].find("i") else ""
        key = "area" if "map" in ic else "date" if "calendar" in ic else "info" if "info" in ic else None
        if key is None:                       # unknown icon: fall back to row order
            key = ("area", "info", "date")[min(len(rows), 2)]
        rows.setdefault(key, tds[1])
    if "area" not in rows:
        return None
    a_lines = [s for s in sentences(paras(rows["area"])) if not BOILER.search(s)]
    i_lines = sentences(paras(rows["info"])) if "info" in rows else []
    date_cell = clean(rows["date"].get_text()) if "date" in rows else ""
    area = clean(" ".join(a_lines)).rstrip(".").strip()
    full = " ".join(i_lines)
    start, end = parse_dates(date_cell, full)
    if not start:
        return None
    tf, tt = parse_times(full)
    st = re.search(r"productie(?:station|bedrijf)\s+(?:te|in|op|aan)\s+(?:de\s+)?([A-Z][\w'’\- ]{1,40}?)(?=[,.;\n]|\s+(?:en|ter|waarbij|zal|waardoor)\b|$)", full)
    bulk_closed = bool(re.search(r"geen\s+bulkwater", full, re.I))
    alt = []
    m = re.search(r"bulkwater.*?(?:t\.w\.|te weten|namelijk|:)\s*([^.]+)", full, re.I)
    if bulk_closed and m:
        alt = [clean(x) for x in re.split(r",|\s+en\s+", m.group(1)) if clean(x)]
    text = [s for s in i_lines if not BOILER.search(s) or re.search(r"bekend dat", s, re.I)]
    w = windows(start, end, tf, tt)
    return {
        "kind": kind,
        "area": area,
        "station": clean(st.group(1)) if st else "",
        "impact": impact(full + " " + " ".join(a_lines)),
        "bulk_closed": bulk_closed,
        "bulk_alt": alt,
        "start_iso": start.isoformat(), "end_iso": end.isoformat(),
        "t_from": tf or "", "t_to": tt or "",
        "windows": w, "end_dt": w[-1][1],
        "text": " ".join(text),
        "link": URL,
    }


def parse(html, prev=None):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    now = datetime.now(SR_TZ)
    now_s = now.strftime("%Y-%m-%dT%H:%M")
    keep_s = (now - timedelta(hours=KEEP_ENDED_H)).strftime("%Y-%m-%dT%H:%M")

    page_ok = bool(soup.find(id="productie") or soup.find(id="distributie")
                   or re.search(r"storing(en)?\s*&(amp;)?\s*onderhoud", soup.get_text(" "), re.I))
    notices, cards = [], 0
    for h in soup.find_all("h5"):
        txt = clean(h.get_text())
        if not re.search(r"onderhoud|storing|onderbreking|werkzaamheden", txt, re.I):
            continue
        card = h.find_parent(lambda t: t.name == "div" and "card" in (t.get("class") or []))
        if not card:
            continue
        cards += 1
        kind = "planned" if re.search(r"gepland|onderhoud|werkzaamheden", txt, re.I) else "outage"
        try:
            n = parse_card(card, kind)
        except Exception as e:                       # one odd card never costs the others
            print(f"    [card skipped: {e}]")
            continue
        if not n:
            print(f"    [card without area/date skipped] {txt}")
            continue
        if n["end_dt"] < keep_s:
            print(f"    [ended] {n['area'][:60]} (until {n['end_dt']})")
            continue
        notices.append(n)
    notices.sort(key=lambda n: n["windows"][0][0])

    prev = prev or {}
    last_seen = now_s if cards else prev.get("last_notice_seen", "")
    if not last_seen and cards == 0 and prev.get("published") is not False and prev.get("planned"):
        last_seen = prev.get("last_updated", "")[:16]
    try:
        recent = bool(last_seen) and (now.replace(tzinfo=None) - datetime.fromisoformat(last_seen[:16])).days < PUBLISHED_DAYS
    except ValueError:
        recent = False
    leg = lambda n: {"area": n["area"], "description": n["text"],
                     "start": n["start_iso"], "end": n["end_iso"], "date": n["start_iso"]}
    return {
        "notices": notices,
        "active": [leg(n) for n in notices if n["kind"] == "outage"],
        "planned": [leg(n) for n in notices if n["kind"] == "planned"],
        "published": bool(cards) or recent,
        "last_notice_seen": last_seen,
        "cards_on_page": cards,
        "page_ok": page_ok,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
        "v": 3,
    }


def main():
    print(f"Fetching {URL}")
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"ERROR: {e}\nKeeping existing data.")
        sys.exit(0)
    data = parse(html, prev)
    if not data["page_ok"] and not data["cards_on_page"]:
        print("ERROR: page has no SWM outage section (layout change or error page). Keeping existing data.")
        sys.exit(0)
    print(f"  Cards on page: {data['cards_on_page']}, current notices: {len(data['notices'])}")
    for n in data["notices"]:
        print(f"    - [{n['kind']}] {n['windows'][0][0]} -> {n['end_dt']} {n['station'] or '-'} | {n['area'][:70]}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
