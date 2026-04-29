#!/usr/bin/env python3
"""
enrich_from_osm.py — Fetch business enrichment data from OpenStreetMap (Overpass API).
Saves results to listing_enrichments.json for use by generate.py.

Uses a SINGLE batch query for all of Suriname instead of one query per listing,
avoiding rate limits from GitHub Actions IP addresses.

No API key, no credit card, no account needed. Completely free.
"""

import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

SR_BBOX    = "1.8,-58.1,6.0,-53.9"
CACHE_FILE = "listing_enrichments.json"

# Try multiple Overpass endpoints in case one is down or rate-limiting
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]


def fetch_all_suriname_pois() -> list[dict]:
    """
    Single batch query: fetch every named amenity/shop/tourism/office node & way
    in Suriname in one request. Returns list of tag dicts.
    """
    query = f"""
[out:json][timeout:120];
(
  node["name"]["amenity"]({SR_BBOX});
  node["name"]["shop"]({SR_BBOX});
  node["name"]["tourism"]({SR_BBOX});
  node["name"]["leisure"]({SR_BBOX});
  node["name"]["office"]({SR_BBOX});
  way["name"]["amenity"]({SR_BBOX});
  way["name"]["shop"]({SR_BBOX});
  way["name"]["tourism"]({SR_BBOX});
);
out tags;
"""
    data = urllib.parse.urlencode({"data": query}).encode()

    for endpoint in ENDPOINTS:
        print(f"  Trying {endpoint} ...")
        try:
            req = urllib.request.Request(
                endpoint, data=data,
                headers={"User-Agent": "ExploreSuriname/1.0 (surinamedomains@gmail.com)"}
            )
            with urllib.request.urlopen(req, timeout=130) as r:
                result = json.loads(r.read().decode())
            elements = result.get("elements", [])
            print(f"  Got {len(elements)} OSM elements from {endpoint}")
            return [el.get("tags", {}) for el in elements if el.get("tags")]
        except Exception as e:
            print(f"  Failed ({e}), trying next endpoint...")
            time.sleep(3)

    print("  All endpoints failed — no OSM data available this run.")
    return []


def best_match(name: str, all_tags: list[dict]) -> dict:
    """Find the best-matching OSM entry for a given business name."""
    name_lower = name.lower().strip()

    # 1. Exact match
    for tags in all_tags:
        if tags.get("name", "").lower().strip() == name_lower:
            return tags

    # 2. OSM name contains our name (e.g. "Hard Rock Cafe Suriname" ↔ "Hard Rock Cafe")
    for tags in all_tags:
        osm = tags.get("name", "").lower()
        if name_lower in osm or osm in name_lower:
            return tags

    return {}


def extract_enrichment(slug: str, tags: dict) -> dict:
    result = {"slug": slug, "found": bool(tags), "osm_name": tags.get("name", "")}

    oh = tags.get("opening_hours", "").strip()
    if oh:
        result["opening_hours"] = oh

    phone = (
        tags.get("phone") or tags.get("contact:phone") or tags.get("contact:mobile") or ""
    ).strip()
    if phone:
        result["phone"] = phone

    website = (tags.get("website") or tags.get("contact:website") or "").strip()
    if website:
        result["website"] = website

    parts = [tags.get(k, "").strip() for k in ("addr:housenumber", "addr:street", "addr:city") if tags.get(k)]
    if parts:
        result["address"] = ", ".join(parts)

    cuisine = tags.get("cuisine", "").strip()
    if cuisine:
        result["cuisine"] = cuisine.replace(";", " · ").title()

    stars = {"1": "$", "2": "$$", "3": "$$$", "4": "$$$$"}.get(tags.get("stars", ""), "")
    if stars:
        result["price_range"] = stars

    return result


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import generate as gen

    slugs = [s for s in gen._BIZ if gen._make_biz(s)]
    print(f"ExploreSuriname OSM enrichment — {len(slugs)} listings\n")

    # Step 1: one batch request for all of Suriname
    all_tags = fetch_all_suriname_pois()

    if not all_tags:
        print("No OSM data retrieved — keeping existing cache unchanged.")
        sys.exit(0)

    # Step 2: match each listing locally
    results = []
    found_count = 0

    for slug in slugs:
        biz  = gen._make_biz(slug)
        name = biz["name"]
        tags = best_match(name, all_tags)
        enrichment = extract_enrichment(slug, tags)
        results.append(enrichment)

        if enrichment["found"]:
            found_count += 1
            fields = [k for k in ("opening_hours", "phone", "address", "cuisine") if k in enrichment]
            print(f"  ✓  {name:<45} ({', '.join(fields) if fields else 'name only'})")

    cache_path = Path(__file__).parent / CACHE_FILE
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone: {found_count}/{len(results)} listings matched.")
    print(f"Saved to {CACHE_FILE}")
