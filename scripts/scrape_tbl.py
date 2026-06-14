#!/usr/bin/env python3
"""
scrape_tbl.py
Scrapes TBL Cinemas day schedule -> data/tbl_cinema.json
Source: https://www.tblcinemas.com/films/dagschema

Page structure (single schedule table):
  | Vandaag          |                          |   <- day header (today)
  | 02:00 PM         | <a href="/movie/..">Title|
  | 03:00 PM         | <a ...>Title</a>         |
  | ma. 15 jun. 2026 |                          |   <- next day header -> stop
  ...

We capture only the FIRST day block (today). Showings are grouped by film,
preserving first-seen order, with each film's list of times.
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.tblcinemas.com/films/dagschema"
OUT = Path(__file__).parent.parent / "data" / "tbl_cinema.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0)"}

TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)$", re.IGNORECASE)

# Dutch day/month abbreviations -> English (for the date label when not "today")
NL_DAY = {"ma": "Mon", "di": "Tue", "wo": "Wed", "do": "Thu",
          "vr": "Fri", "za": "Sat", "zo": "Sun"}
NL_MON = {"jan": "Jan", "feb": "Feb", "mrt": "Mar", "apr": "Apr", "mei": "May",
          "jun": "Jun", "jul": "Jul", "aug": "Aug", "sep": "Sep",
          "okt": "Oct", "nov": "Nov", "dec": "Dec"}


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    for enc in ("utf-8", "latin-1", "iso-8859-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def _english_label(header):
    """ 'ma. 15 jun. 2026' -> 'Mon 15 Jun 2026'; 'Vandaag' -> 'Today'. """
    low = header.lower()
    if low.startswith("vandaag") or low == "today":
        return "Today"
    out = header
    for nl, en in NL_DAY.items():
        out = re.sub(r"\b" + nl + r"\.?", en, out, flags=re.IGNORECASE)
    for nl, en in NL_MON.items():
        out = re.sub(r"\b" + nl + r"\.?", en, out, flags=re.IGNORECASE)
    return clean(out)


def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")

    films, order = {}, []
    started = False
    date_label = "Today"

    for tr in rows:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        first = clean(cells[0].get_text())
        if not first:
            continue

        if not TIME_RE.match(first):
            # Day-header row
            if not started:
                started = True
                date_label = _english_label(first)
                continue
            else:
                break  # reached the next day -> stop (today only)

        if not started:
            continue

        # Showtime row: find the movie link
        a = tr.find("a", href=True)
        title = clean(a.get_text()) if a else clean(cells[-1].get_text())
        url = a["href"].strip() if a else ""
        if url.startswith("/"):
            url = "https://www.tblcinemas.com" + url
        if not title:
            continue

        if title not in films:
            films[title] = {"title": title, "url": url, "times": []}
            order.append(title)
        t = first.upper()
        if t not in films[title]["times"]:
            films[title]["times"].append(t)

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "date_label": date_label,
        "films": [films[t] for t in order],
        "source": URL,
    }


def main():
    print(f"Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"ERROR fetching: {e}")
        if OUT.exists():
            print("Keeping existing data.")
        sys.exit(0)

    try:
        data = parse(html)
    except Exception as e:
        print(f"ERROR parsing: {e}")
        if OUT.exists():
            print("Keeping existing data.")
        sys.exit(0)

    # Defensive: never overwrite good data with an empty result (parser drift / off-hours)
    if not data["films"]:
        print("  No films parsed for today.")
        if OUT.exists():
            print("Keeping existing data.")
            sys.exit(0)

    print(f"  Label: {data['date_label']}")
    print(f"  Films: {len(data['films'])}")
    for f in data["films"]:
        print(f"    {f['title']}  ->  {', '.join(f['times'])}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
