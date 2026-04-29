#!/usr/bin/env python3
"""
enrich_from_osm.py — Fetch business enrichment data from OpenStreetMap (Overpass API).
Saves results to listing_enrichments.json for use by generate.py.

Run via GitHub Actions weekly (enrich.yml), or manually:
    python enrich_from_osm.py

No API key, no credit card, no account needed. Completely free.
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

# Suriname bounding box: south, west, north, east
SR_BBOX = "1.8,-58.1,6.0,-53.9"

CACHE_FILE = "listing_enrichments.json"

# Rate-limit: pause between requests to be polite to OSM servers
SLEEP_SECONDS = 1.5


def query_osm(name: str) -> dict:
    """
    Query Overpass API for a business by name within Suriname.
    Returns the OSM tags dict of the best match, or {} if not found.
    """
    # Escape special regex chars in the name
    esc = name.replace('"', '').replace("'", "\\'").replace("(", "\\(").replace(")", "\\)")
    query = f"""
[out:json][timeout:20];
(
  node["name"~"{esc}",i]({SR_BBOX});
  way["name"~"{esc}",i]({SR_BBOX});
  relation["name"~"{esc}",i]({SR_BBOX});
);
out tags 10;
"""
    try:
        url  = "https://overpass-api.de/api/interpreter"
        data = urllib.parse.urlencode({"data": query}).encode()
        req  = urllib.request.Request(
            url, data=data,
            headers={"User-Agent": "ExploreSuriname/1.0 (surinamedomains@gmail.com)"}
        )
        with urllib.request.urlopen(req, timeout=25) as r:
            result = json.loads(r.read().decode())

        elements = result.get("elements", [])
        if not elements:
            return {}

        # Prefer exact name match (case-insensitive)
        name_lower = name.lower()
        for el in elements:
            tags = el.get("tags", {})
            if tags.get("name", "").lower() == name_lower:
                return tags

        # Fall back to first result
        return elements[0].get("tags", {})

    except Exception as e:
        print(f"    OSM error for '{name}': {e}")
        return {}


def extract_enrichment(slug: str, name: str, tags: dict) -> dict:
    """
    Pull useful fields from an OSM tags dict.
    Returns a dict ready to be stored in listing_enrichments.json.
    """
    result = {"slug": slug, "found": bool(tags), "osm_name": tags.get("name", "")}

    # Opening hours — OSM format e.g. "Mo-Fr 09:00-17:00; Sa 10:00-14:00"
    oh = tags.get("opening_hours", "").strip()
    if oh:
        result["opening_hours"] = oh

    # Phone
    phone = (
        tags.get("phone")
        or tags.get("contact:phone")
        or tags.get("contact:mobile")
        or ""
    ).strip()
    if phone:
        result["phone"] = phone

    # Website
    website = (tags.get("website") or tags.get("contact:website") or "").strip()
    if website:
        result["website"] = website

    # Address from OSM addr:* tags
    parts = []
    for k in ("addr:housenumber", "addr:street", "addr:city"):
        v = tags.get(k, "").strip()
        if v:
            parts.append(v)
    if parts:
        result["address"] = ", ".join(parts)

    # Cuisine (for restaurants)
    cuisine = tags.get("cuisine", "").strip()
    if cuisine:
        result["cuisine"] = cuisine.replace(";", " · ").title()

    # Price level (0=free, 1=$, 2=$$, 3=$$$, 4=$$$$)
    fee = tags.get("fee", "")
    stars = {"1": "$", "2": "$$", "3": "$$$", "4": "$$$$"}.get(
        tags.get("stars", ""), ""
    )
    if stars:
        result["price_range"] = stars

    return result


if __name__ == "__main__":
    # Import the listings from generate.py (same folder)
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import generate as gen

    slugs = [s for s in gen._BIZ if gen._make_biz(s)]
    total = len(slugs)
    print(f"ExploreSuriname OSM enrichment — {total} listings\n")

    # Load existing cache so we can merge/update
    existing_cache: dict[str, dict] = {}
    cache_path = Path(__file__).parent / CACHE_FILE
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            for entry in json.load(f):
                existing_cache[entry["slug"]] = entry

    results = []
    found_count = 0

    for i, slug in enumerate(slugs, 1):
        biz   = gen._make_biz(slug)
        name  = biz["name"]
        print(f"  [{i:3}/{total}] {name:<40}", end=" ", flush=True)

        tags       = query_osm(name)
        enrichment = extract_enrichment(slug, name, tags)
        results.append(enrichment)

        if enrichment["found"]:
            found_count += 1
            fields = [k for k in ("opening_hours", "phone", "address", "cuisine", "price_range")
                      if k in enrichment]
            print(f"✓  ({', '.join(fields) if fields else 'name only'})")
        else:
            print("–  not in OSM")

        time.sleep(SLEEP_SECONDS)

    # Save results
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {found_count}/{len(results)} listings matched in OSM.")
    print(f"Saved to {CACHE_FILE}")
