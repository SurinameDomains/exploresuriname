#!/usr/bin/env python3
"""
scrape_ebs.py — EBS power outages -> data/ebs_outages.json
Source: https://nvebs.com/elektriciteit/stroom-onderbrekingen

EBS renders outage titles in div.notice-text inside div.notice-slider-desktop
in the static HTML — no Playwright required.

Each notice-text div contains:
  - Title text: "GEPLAND ONDERHOUD DINSDAG 26 MEI 2026"
  - Link to detail page: https://nvebs.com/nieuws/1500/...
"""

import json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

URL_MAIN = "https://nvebs.com/elektriciteit/stroom-onderbrekingen"
OUT = Path(__file__).parent.parent / "data" / "ebs_outages.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl,en;q=0.9",
}

# Suriname is UTC-3 (no DST)
SR_TZ = timezone(timedelta(hours=-3))

_MONTHS_NL = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5,
    "juni": 6, "juli": 7, "augustus": 8, "september": 9,
    "oktober": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mrt": 3, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "nov": 11, "dec": 12,
}


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def parse_dutch_date(text):
    """Parse 'DINSDAG 26 MEI 2026' or '26 MEI 2026' -> date object."""
    # Full form: WEEKDAY DD MONTH YYYY
    m = re.search(r"(\d{1,2})\s+([A-Z][A-Z]+)\s+(\d{4})", text, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        mon = _MONTHS_NL.get(m.group(2).lower())
        year = int(m.group(3))
        if mon:
            try:
                return datetime(year, mon, day).date()
            except Exception:
                pass
    return None


def fmt_date_nl(text):
    """Return a human-readable date string from a Dutch outage title."""
    m = re.search(r"(\d{1,2})\s+([A-Z][A-Z]+)\s+(\d{4})", text, re.IGNORECASE)
    if m:
        return f"{m.group(1)} {m.group(2).capitalize()} {m.group(3)}"
    return text


def fetch_html(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def fetch_detail(url):
    """Try to fetch area/description from a detail page. Returns dict or None."""
    try:
        from bs4 import BeautifulSoup
        html = fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        for s in soup(["script", "style"]): s.decompose()
        # Look for content divs
        for cls in ["content", "article-body", "post-content", "entry-content", "page-content"]:
            el = soup.find(class_=cls)
            if el:
                txt = clean(el.get_text())
                if len(txt) > 30:
                    return txt[:300]
        # Try article/main tags
        for tag in ["article", "main"]:
            el = soup.find(tag)
            if el:
                txt = clean(el.get_text())
                if len(txt) > 30:
                    return txt[:300]
    except Exception:
        pass
    return None


def parse_main_page(html):
    """Extract planned outage entries from notice-slider-desktop."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    today = datetime.now(SR_TZ).date()

    # Find the desktop slider (avoid mobile duplicates)
    slider = soup.find("div", class_="notice-slider-desktop")
    if not slider:
        # Fallback: find all notice-text divs
        slider = soup

    entries = []
    seen_dates = set()

    for div in slider.find_all("div", class_="notice-text"):
        title = clean(div.get_text(" ").replace("Lees meer", "").strip())
        link_tag = div.find("a")
        link = link_tag["href"] if link_tag and link_tag.get("href") else ""

        # Parse date from title
        outage_date = parse_dutch_date(title)
        if not outage_date:
            continue

        # Skip outages in the past
        if outage_date < today:
            print(f"    [skipped past] {title}")
            continue

        # Deduplicate by date (same date can appear multiple times)
        date_key = str(outage_date)
        if date_key in seen_dates:
            # Accumulate links for same date
            for e in entries:
                if e["date_iso"] == date_key and link not in e.get("links", []):
                    e.setdefault("links", []).append(link)
            continue
        seen_dates.add(date_key)

        entries.append({
            "title":       title,
            "date":        fmt_date_nl(title),
            "date_iso":    date_key,
            "type":        "planned",
            "links":       [link] if link else [],
        })
        print(f"    [planned] {title}")

    return entries


def main():
    print(f"Fetching {URL_MAIN} ...")
    try:
        html = fetch_html(URL_MAIN)
    except Exception as e:
        print(f"ERROR fetching main page: {e}")
        if OUT.exists():
            print("  Keeping existing data.")
        sys.exit(0)

    try:
        outages = parse_main_page(html)
    except Exception as e:
        print(f"ERROR parsing page: {e}")
        outages = []

    # Optionally enrich first entry with detail page text
    for entry in outages[:3]:
        if entry.get("links"):
            detail_url = entry["links"][0]
            if not detail_url.startswith("http"):
                detail_url = "https://nvebs.com" + detail_url
            detail = fetch_detail(detail_url)
            if detail and len(detail) > 50:
                entry["description"] = detail

    result = {
        "outages":      outages,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source":       URL_MAIN,
        "note":         "Planned outage notices from EBS (Energie Bedrijven Suriname).",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written {len(outages)} outage(s) -> {OUT}")


if __name__ == "__main__":
    main()
