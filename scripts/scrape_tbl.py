#!/usr/bin/env python3
"""
scrape_tbl.py
Scrapes TBL Cinemas day schedule -> data/tbl_cinema.json
Source: https://www.tblcinemas.com/films/dagschema

Captures the FIRST day block (today) as a CHRONOLOGICAL list of showings,
one entry per showtime: {time, title, url}. Keeping it chronological (rather
than grouping by film) means no late show is ever hidden mid-list.
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://www.tblcinemas.com/films/dagschema"
OUT = Path(__file__).parent.parent / "data" / "tbl_cinema.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0)"}

TIME_RE = re.compile(r"^\d{1,2}:\d{2}\s*(?:AM|PM)$", re.IGNORECASE)

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

    showings, seen = [], set()
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
                break  # next day -> stop (today only)

        if not started:
            continue

        a = tr.find("a", href=True)
        title = clean(a.get_text()) if a else clean(cells[-1].get_text())
        url = a["href"].strip() if a else ""
        if url.startswith("/"):
            url = "https://www.tblcinemas.com" + url
        if not title:
            continue

        t = first.upper()
        key = (t, title)
        if key in seen:        # guard against accidental duplicate rows
            continue
        seen.add(key)
        showings.append({"time": t, "title": title, "url": url})

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "date_label": date_label,
        "showings": showings,
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

    if not data["showings"]:
        print("  No showings parsed for today.")
        if OUT.exists():
            print("Keeping existing data.")
            sys.exit(0)

    print(f"  Label: {data['date_label']}")
    print(f"  Showings: {len(data['showings'])}")
    for s in data["showings"]:
        print(f"    {s['time']}  {s['title']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
