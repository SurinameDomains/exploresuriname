#!/usr/bin/env python3
"""
scrape_ebs.py — EBS power outages -> data/ebs_outages.json
Source: https://nvebs.com/elektriciteit/stroom-onderbrekingen

EBS site is fully JS-rendered (custom CMS, Bulma CSS).
Requires Playwright to render content. Falls back gracefully if unavailable.

GitHub Actions setup:
  pip install playwright --break-system-packages
  playwright install chromium --with-deps
"""

import json, re, sys
from datetime import datetime, timezone
from pathlib import Path

URL_ACTIVE  = "https://nvebs.com/elektriciteit/stroom-onderbrekingen"
URL_PLANNED = "https://nvebs.com/elektriciteit/stroom-onderbrekingen/gepland-onderhoud"
OUT = Path(__file__).parent.parent / "data" / "ebs_outages.json"


def clean(t):
    return re.sub(r"\s+", " ", str(t)).strip()


def parse_page(html, outage_type="active"):
    """
    Parse EBS rendered HTML for outage entries.
    EBS uses Bulma CSS — outage entries are likely in .card or .box or table elements.
    First real run: debug mode logs the raw HTML for structure analysis.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    entries = []

    # Try tables first (similar to SWM)
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < 1:
            continue
        for row in rows:
            cells = [clean(td.get_text()) for td in row.find_all(["td","th"]) if clean(td.get_text())]
            if len(cells) >= 2:
                entries.append({
                    "area":        cells[0],
                    "description": cells[1] if len(cells) > 1 else "",
                    "date":        cells[-1] if len(cells) > 2 else "",
                    "type":        outage_type,
                })

    # Fallback: try Bulma .card or .box elements
    if not entries:
        for card in soup.find_all(class_=re.compile(r"\bcard\b|\bbox\b")):
            text = clean(card.get_text())
            if len(text) > 20 and re.search(r"\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2}", text):
                # Extract date
                date_m = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", text)
                entries.append({
                    "area":        text[:80],
                    "description": text,
                    "date":        date_m.group(0) if date_m else "",
                    "type":        outage_type,
                })

    # Final fallback: scan for any paragraph with a date
    if not entries:
        for p in soup.find_all(["p", "li", "div"]):
            text = clean(p.get_text())
            if 10 < len(text) < 500 and re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", text):
                date_m = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", text)
                entries.append({
                    "area":        text[:60],
                    "description": text,
                    "date":        date_m.group(0) if date_m else "",
                    "type":        outage_type,
                })
                if len(entries) >= 10:
                    break

    return entries


def scrape_with_playwright():
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

    all_outages = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        page = browser.new_page(user_agent="Mozilla/5.0 (compatible; ExploreSuriname/1.0)")

        for url, otype in [(URL_ACTIVE, "active"), (URL_PLANNED, "planned")]:
            try:
                print(f"  Loading {url}")
                page.goto(url, timeout=30000, wait_until="networkidle")
                # Wait for main content
                try:
                    page.wait_for_selector("main, .content, .container, table", timeout=10000)
                except PlaywrightTimeout:
                    pass  # continue anyway
                html = page.content()
                entries = parse_page(html, otype)
                print(f"    Entries ({otype}): {len(entries)}")
                all_outages.extend(entries)

                # Debug: save raw HTML on first run if no entries found
                if not entries:
                    debug_path = OUT.parent / f"_ebs_debug_{otype}.html"
                    debug_path.write_text(html, encoding="utf-8")
                    print(f"    Debug HTML saved: {debug_path}")

            except Exception as e:
                print(f"    ERROR on {url}: {e}")

        browser.close()

    return all_outages


def main():
    print("Scraping EBS outages...")
    try:
        outages = scrape_with_playwright()
    except ImportError:
        print("  Playwright not installed — keeping existing data.")
        if not OUT.exists():
            OUT.parent.mkdir(parents=True, exist_ok=True)
            OUT.write_text(json.dumps({
                "outages": [],
                "last_updated": None,
                "source": URL_ACTIVE,
                "note": "Playwright not available"
            }, indent=2))
        sys.exit(0)
    except Exception as e:
        print(f"  ERROR: {e}")
        if OUT.exists():
            print("  Keeping existing data.")
        sys.exit(0)

    result = {
        "outages":      outages,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source":       URL_ACTIVE,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written {len(outages)} entries -> {OUT}")


if __name__ == "__main__":
    main()
