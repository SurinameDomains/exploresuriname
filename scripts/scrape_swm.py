#!/usr/bin/env python3
"""
scrape_swm.py — SWM water outages -> data/swm_outages.json
Source: https://swm.sr/storing-onderhoud/

DOM structure: h5 heading + table both live inside a div.card.swmRounded.border-0
Table has 3 rows per outage: [area row, description row, date row]
Each row: 2 <td> — first is icon placeholder, second is content.
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://swm.sr/storing-onderhoud/"
OUT = Path(__file__).parent.parent / "data" / "swm_outages.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ExploreSuriname/1.0; +https://exploresuriname.com)",
    "Accept": "text/html,application/xhtml+xml",
}


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def _fmt_date(s):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").strftime("%-d %b %Y")
    except Exception:
        return s.strip()


def parse_table(table):
    """3 rows per outage: [area, description, date]. Second <td> is content."""
    cells = []
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        content = clean(tds[1].get_text()) if len(tds) >= 2 else (clean(tds[0].get_text()) if tds else "")
        if content:
            cells.append(content)

    entries = []
    for i in range(0, len(cells), 3):
        chunk = cells[i:i+3]
        if len(chunk) < 2:
            continue
        area = chunk[0]
        desc = chunk[1] if len(chunk) > 1 else ""
        date_str = chunk[2] if len(chunk) > 2 else ""
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", date_str)
        start = _fmt_date(dates[0]) if dates else date_str
        end   = _fmt_date(dates[1]) if len(dates) > 1 else start
        entries.append({"area": area, "description": desc, "start": start, "end": end})
    return entries


def find_card_for_heading(heading):
    """Walk up from h5 to find the .card container that holds both the heading and its table."""
    node = heading
    for _ in range(10):
        node = node.parent
        if not node or node.name in ("html", "body"):
            break
        classes = node.get("class", [])
        if "card" in classes and "swmRounded" in classes:
            return node
    return None


def parse(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    result = {
        "active":  [],
        "planned": [],
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
    }

    for h in soup.find_all("h5"):
        txt = clean(h.get_text())
        if not re.search(r"gepland onderhoud|^storingen$", txt, re.IGNORECASE):
            continue
        is_planned = bool(re.search(r"gepland", txt, re.IGNORECASE))

        card = find_card_for_heading(h)
        if not card:
            continue

        table = card.find("table")
        if not table:
            continue

        for e in parse_table(table):
            if is_planned:
                result["planned"].append({
                    "area":        e["area"],
                    "description": e["description"],
                    "start":       e["start"],
                    "end":         e["end"],
                    "date":        e["start"],
                })
            else:
                result["active"].append({
                    "area":        e["area"],
                    "description": e["description"],
                    "date":        e["start"],
                })

    return result


def main():
    print(f"Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"ERROR: {e}")
        if OUT.exists():
            print("Keeping existing data.")
        sys.exit(0)

    data = parse(html)
    print(f"  Active outages: {len(data['active'])}")
    for o in data["active"]:
        print(f"    - {o['area']} ({o['date']})")
    print(f"  Planned:        {len(data['planned'])}")
    for o in data["planned"]:
        print(f"    - {o['area']} ({o['start']} → {o['end']})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written: {OUT}")


if __name__ == "__main__":
    main()
