#!/usr/bin/env python3
"""
scrape_ebs.py — EBS power outages -> data/ebs_outages.json
Source: https://nvebs.com/elektriciteit/stroom-onderbrekingen

Strategy:
  1. Fetch main outages page → parse div.notice-slider-desktop for upcoming entries
     (each has a title like "GEPLAND ONDERHOUD DINSDAG 26 MEI 2026" and a detail link)
  2. For each detail link, fetch the page and extract the meta description —
     it's server-rendered and contains: district, date, time window, streets affected.
     Example: "Gepland onderhoud: Paramaribo maandag 25 mei 2026 tussen 08:30-14:30
               GEDEELTE RINGWEG ZUID TUSSEN NIEUWE CHARLESBURGWEG EN LEO HEINEMANNSTRAAT"
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL_MAIN = "https://nvebs.com/elektriciteit/stroom-onderbrekingen"
OUT = Path(__file__).parent.parent / "data" / "ebs_outages.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl,en;q=0.9",
}

SR_TZ = timezone(timedelta(hours=-3))

_MONTHS_NL = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "augustus": 8, "september": 9,
    "oktober": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mrt": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_dutch_date(text):
    """Extract date object from text like 'DINSDAG 26 MEI 2026'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        day, year = int(m.group(1)), int(m.group(3))
        mon = _MONTHS_NL.get(m.group(2).lower())
        if mon:
            try:
                return datetime(year, mon, day).date()
            except Exception:
                pass
    return None


def fmt_date_nl(text):
    """Return 'Dinsdag 26 Mei 2026' from a Dutch outage title."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", text)
    if m:
        return f"{m.group(1)} {m.group(2).capitalize()} {m.group(3)}"
    return text


def parse_meta_description(desc):
    """
    Parse EBS meta description into structured fields.
    Format: "Gepland onderhoud: [District] [Day] [Date] tussen [HH:MM]-[HH:MM] [Streets]"
    Returns dict with keys: district, time, area
    """
    if not desc:
        return {}
    # Remove the "Gepland onderhoud:" prefix
    desc = re.sub(r"^Gepland\s+onderhoud\s*:\s*", "", desc, flags=re.IGNORECASE).strip()

    result = {}

    # Extract time window "tussen HH:MM-HH:MM" or "HH:MM-HH:MM"
    time_m = re.search(r"tussen\s+(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", desc, re.IGNORECASE)
    if time_m:
        result["time"] = f"{time_m.group(1)} – {time_m.group(2)}"
        # Streets = everything after the time (may be truncated)
        area_part = desc[time_m.end():].strip().rstrip(",. ")
        if area_part:
            # Title-case for readability
            result["area"] = area_part
    else:
        time_m2 = re.search(r"(\d{1,2}:\d{2})\s*[-–]\s*(\d{1,2}:\d{2})", desc)
        if time_m2:
            result["time"] = f"{time_m2.group(1)} – {time_m2.group(2)}"

    # District = first word(s) before the date (up to next date-like token)
    # Strip date tokens
    without_date = re.sub(r"\b(maandag|dinsdag|woensdag|donderdag|vrijdag|zaterdag|zondag)\b", "", desc, flags=re.IGNORECASE)
    without_date = re.sub(r"\d{1,2}\s+[a-z]+\s+\d{4}", "", without_date, flags=re.IGNORECASE)
    without_date = re.sub(r"tussen.*", "", without_date, flags=re.IGNORECASE).strip().rstrip(",. ")
    if without_date and len(without_date) < 40:
        result["district"] = without_date.strip()

    return result


def fetch_detail(url):
    """Fetch a detail page and extract meta description + parsed fields."""
    try:
        from bs4 import BeautifulSoup
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        meta = (soup.find("meta", {"name": "description"}) or
                soup.find("meta", {"property": "og:description"}))
        if meta and meta.get("content"):
            return meta["content"]
    except Exception as e:
        print(f"    [detail fetch error] {e}")
    return None


def parse_main_page(html):
    """Extract outage entries from notice-slider-desktop."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    today = datetime.now(SR_TZ).date()

    slider = soup.find("div", class_="notice-slider-desktop")
    if not slider:
        slider = soup

    entries = []
    seen_links = set()

    for div in slider.find_all("div", class_="notice-text"):
        title = clean(div.get_text(" ").replace("Lees meer", "").strip())
        link_tag = div.find("a")
        link = link_tag["href"] if link_tag and link_tag.get("href") else ""
        if not link.startswith("http"):
            link = "https://nvebs.com" + link if link else ""

        # Skip duplicates by link
        if link in seen_links:
            continue
        seen_links.add(link)

        outage_date = parse_dutch_date(title)
        if not outage_date:
            continue
        if outage_date < today:
            print(f"    [skipped past] {title}")
            continue

        entries.append({
            "title":    title,
            "date":     fmt_date_nl(title),
            "date_iso": str(outage_date),
            "type":     "planned",
            "link":     link,
        })
        print(f"    [found] {title}")

    return entries


def main():
    print(f"Fetching {URL_MAIN} ...")
    try:
        html = fetch_html(URL_MAIN)
    except Exception as e:
        print(f"ERROR: {e}")
        if OUT.exists():
            print("  Keeping existing data.")
        sys.exit(0)

    try:
        outages = parse_main_page(html)
    except Exception as e:
        print(f"ERROR parsing: {e}")
        outages = []

    # Enrich each entry with detail from meta description
    for entry in outages:
        if entry.get("link"):
            print(f"  Fetching detail: {entry['link']}")
            meta_desc = fetch_detail(entry["link"])
            if meta_desc:
                parsed = parse_meta_description(meta_desc)
                entry["meta_description"] = meta_desc
                if parsed.get("district"):
                    entry["district"] = parsed["district"]
                if parsed.get("time"):
                    entry["time"] = parsed["time"]
                if parsed.get("area"):
                    entry["area"] = parsed["area"]

    result = {
        "outages":      outages,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source":       URL_MAIN,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written {len(outages)} outage(s) -> {OUT}")


if __name__ == "__main__":
    main()
