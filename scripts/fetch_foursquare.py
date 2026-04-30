#!/usr/bin/env python3
"""
fetch_foursquare.py
===================
One-time enrichment script: pulls business data from Foursquare Places API
and caches it in website/foursquare_cache.json.

Usage (run locally — do NOT commit API key to git):
    set FSQ_KEY=your_service_api_key_here   (Windows CMD)
    python scripts/fetch_foursquare.py

    # or inline:
    FSQ_KEY=your_key python scripts/fetch_foursquare.py

The cache file is committed to the repo so GitHub Actions never needs the key.
Re-run this script periodically (e.g. quarterly) to refresh the data.
"""

import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY       = os.environ.get("FSQ_KEY", "").strip()
# Foursquare migrated from api.foursquare.com/v3 → places-api.foursquare.com
# Auth is now:  Authorization: Bearer <SERVICE_KEY>
# Versioning:   X-Places-Api-Version: YYYY-MM-DD header required
BASE_URL      = "https://places-api.foursquare.com/places/search"
API_VERSION   = "2025-06-17"
SURINAME_LL   = "5.8520,-55.2038"   # Paramaribo city centre
SEARCH_RADIUS = 80_000              # 80 km covers all populated areas
FIELDS        = "name,location,tel,website,fsq_place_id"
MIN_SCORE     = 0.50                # confidence threshold for a "match"
DELAY_S       = 0.25               # seconds between requests (stay well under 1k/day)

ROOT       = Path(__file__).resolve().parent.parent  # = repo root (website/)
GEN_PY     = ROOT / "generate.py"
CACHE_FILE = ROOT / "foursquare_cache.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def fsq_search(name: str) -> dict:
    """Search Foursquare for `name` near Paramaribo. Returns raw API response."""
    params = urllib.parse.urlencode({
        "query":  name,
        "ll":     SURINAME_LL,
        "radius": str(SEARCH_RADIUS),
        "limit":  "3",
        "fields": FIELDS,
    })
    req = urllib.request.Request(
        f"{BASE_URL}?{params}",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-Places-Api-Version": API_VERSION,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        return {"_error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as e:
        return {"_error": str(e)}


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def best_match(query: str, places: list) -> tuple[dict | None, float]:
    """Return (best_place, score) from a list of Foursquare results."""
    best, score = None, 0.0
    for p in places:
        s = similarity(query, p.get("name", ""))
        if s > score:
            best, score = p, s
    return best, score


def extract_biz(gen_py: Path) -> dict[str, str]:
    """
    Parse _BIZ from generate.py and return {slug: name}.
    Uses the stored "name" field for accurate search queries.
    """
    code = gen_py.read_text(encoding="utf-8")

    # Find the _BIZ block
    m = re.search(r"^_BIZ\s*=\s*\{", code, re.MULTILINE)
    if not m:
        raise ValueError("Could not find _BIZ = { in generate.py")

    start = m.end()
    # Walk forward matching braces to find the end of the dict
    depth, i = 1, start
    while i < len(code) and depth:
        if code[i] == "{":
            depth += 1
        elif code[i] == "}":
            depth -= 1
        i += 1
    biz_block = code[start:i]

    # Extract  'slug': {"name": 'Business Name', ...}
    result = {}
    for m in re.finditer(r"'([a-z0-9][a-z0-9\-]+)':\s*\{[^}]*\"name\":\s*'([^']+)'", biz_block):
        result[m.group(1)] = m.group(2)
    return result


def load_cache() -> dict:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  💾  Saved {len(cache)} entries → {CACHE_FILE.relative_to(ROOT)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print("❌  FSQ_KEY environment variable is not set.")
        print("    Run:  set FSQ_KEY=your_service_api_key   (Windows CMD)")
        print("    Then: python scripts/fetch_foursquare.py")
        sys.exit(1)

    # Quick auth check before burning through slugs
    print("🔑  Testing API key …")
    test = fsq_search("KFC")
    if "_error" in test:
        print(f"❌  Auth failed: {test['_error']}")
        print("    Check that the Service API Key is correct and the project")
        print("    has the Places API enabled in the Foursquare developer portal.")
        sys.exit(1)
    print(f"✅  Auth OK — {len(test.get('results', []))} results for test query")

    # Load existing data
    biz        = extract_biz(GEN_PY)
    cache      = load_cache()
    already    = set(cache.keys())
    todo       = [(slug, name) for slug, name in biz.items() if slug not in already]

    print(f"\n📋  Total listings : {len(biz)}")
    print(f"    Already cached : {len(already)}")
    print(f"    To fetch       : {len(todo)}")
    if not todo:
        print("    Nothing to do — cache is up to date.")
        return

    hits = misses = errors = 0

    for idx, (slug, name) in enumerate(todo, 1):
        resp = fsq_search(name)

        if "_error" in resp:
            print(f"  [{idx:>3}/{len(todo)}] ERR   {slug!r:45} {resp['_error']}")
            cache[slug] = {"matched": False, "error": resp["_error"]}
            errors += 1
        else:
            places = resp.get("results", [])
            place, score = best_match(name, places)

            if place is None:
                print(f"  [{idx:>3}/{len(todo)}] MISS  {name!r}")
                cache[slug] = {"matched": False}
                misses += 1
            else:
                loc  = place.get("location", {})
                matched = score >= MIN_SCORE
                entry = {
                    "matched":  matched,
                    "score":    round(score, 3),
                    "fsq_id":   place.get("fsq_place_id"),
                    "name":     place.get("name"),
                    "address":  loc.get("formatted_address") or loc.get("address"),
                    "city":     loc.get("locality") or loc.get("city"),
                    "country":  loc.get("country"),
                    "phone":    place.get("tel"),
                    "website":  place.get("website"),
                }
                cache[slug] = entry
                tag = "HIT " if matched else "WEAK"
                print(f"  [{idx:>3}/{len(todo)}] {tag}  {name!r:42} → {entry['name']!r} ({score:.2f})")
                if matched:
                    hits += 1
                else:
                    misses += 1

        # Checkpoint every 50 requests
        if idx % 50 == 0:
            save_cache(cache)

        time.sleep(DELAY_S)

    save_cache(cache)
    total = hits + misses + errors
    print(f"\n{'─'*60}")
    print(f"Done:  {hits} hits / {misses} misses / {errors} errors  ({total} fetched)")
    match_rate = hits / total * 100 if total else 0
    print(f"Match rate: {match_rate:.0f}%")
    print(f"Cache: {len(cache)} total entries")


if __name__ == "__main__":
    main()
