#!/usr/bin/env python3
"""
fetch_foursquare_details.py
============================
Second-pass enrichment: fetches opening hours + photos for every listing
that already has an fsq_id in foursquare_cache.json.

Reads  : website/foursquare_cache.json          (existing – slug → {fsq_id, ...})
Writes : website/foursquare_details_cache.json  (new     – slug → {hours_display, photo_url, phone, website})

Usage (run locally — never commit your key):
    set FSQ_KEY=your_service_api_key   (Windows CMD)
    python scripts/fetch_foursquare_details.py

Free tier: 1 000 calls/day.  ~493 matched places = done in one run.
Script is resume-safe: already-fetched slugs are skipped on re-run.
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

API_KEY     = os.environ.get("FSQ_KEY", "").strip()
API_VERSION = "2025-06-17"
BASE_URL    = "https://places-api.foursquare.com/places"
FIELDS      = "hours,photos,tel,website"
DELAY_S     = 0.30          # stay comfortably under 1 000 / day
PHOTO_SIZE  = "800x600"     # WxH inserted into Foursquare CDN URL

ROOT      = Path(__file__).resolve().parent.parent   # website/
CACHE_IN  = ROOT / "foursquare_cache.json"
CACHE_OUT = ROOT / "foursquare_details_cache.json"

# ── Helpers ───────────────────────────────────────────────────────────────────

def fsq_get(fsq_id: str) -> dict:
    """GET /places/{fsq_id}?fields=hours,photos,tel,website"""
    url = f"{BASE_URL}/{fsq_id}?fields={FIELDS}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-Places-Api-Version": API_VERSION,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="ignore")
        return {"_error": f"HTTP {e.code}: {body[:200]}"}
    except Exception as exc:
        return {"_error": str(exc)}


def parse_hours(hours_obj: dict) -> str:
    """
    Convert Foursquare hours object → OSM-compatible display string.
    Prefers the human-readable 'display' list; falls back to building
    from the 'regular' slots.
    """
    if not hours_obj:
        return ""
    display = hours_obj.get("display", [])
    if display:
        return "; ".join(display)
    # Build from structured slots
    DAY = {1: "Mo", 2: "Tu", 3: "We", 4: "Th", 5: "Fr", 6: "Sa", 7: "Su"}
    parts = []
    for slot in hours_obj.get("regular", []):
        d  = DAY.get(slot.get("day", 0), "?")
        o  = slot.get("open",  "")[:4]   # "0900"
        cl = slot.get("close", "")[:4]
        if o and cl:
            parts.append(f"{d} {o[:2]}:{o[2:]}-{cl[:2]}:{cl[2:]}")
    return "; ".join(parts)


def best_photo_url(photos: list) -> str:
    """
    Return CDN URL of the widest available photo.
    Foursquare URL pattern: {prefix}{WxH}{suffix}
    e.g. https://fastly.4sqi.net/img/general/800x600/xxx.jpg
    """
    if not photos:
        return ""
    # Prefer landscape (widest)
    photos_sorted = sorted(photos, key=lambda p: p.get("width", 0), reverse=True)
    p = photos_sorted[0]
    prefix = p.get("prefix", "")
    suffix = p.get("suffix", "")
    if prefix and suffix:
        return f"{prefix}{PHOTO_SIZE}{suffix}"
    return ""


def save(cache: dict) -> None:
    CACHE_OUT.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not API_KEY:
        print("❌  FSQ_KEY environment variable is not set.")
        print("    set FSQ_KEY=your_service_api_key   (Windows CMD)")
        sys.exit(1)

    base_cache = json.loads(CACHE_IN.read_text(encoding="utf-8"))
    matched    = {
        slug: v for slug, v in base_cache.items()
        if v.get("matched") and v.get("fsq_id")
    }
    print(f"ExploreSuriname — Foursquare details enrichment")
    print(f"  {len(matched)} matched listings with fsq_id\n")

    # Resume-safe: load whatever was already fetched
    out_cache: dict = {}
    if CACHE_OUT.exists():
        out_cache = json.loads(CACHE_OUT.read_text(encoding="utf-8"))
        print(f"  Resuming — {len(out_cache)} already cached, skipping those\n")

    todo = [(slug, v["fsq_id"]) for slug, v in matched.items() if slug not in out_cache]
    print(f"  {len(todo)} to fetch (est. {len(todo) * DELAY_S / 60:.1f} min at {DELAY_S}s delay)\n")

    if not todo:
        print("  Nothing to do — all matched listings already have details.")
        return

    ok = skipped = errors = 0

    for idx, (slug, fsq_id) in enumerate(todo, 1):
        resp = fsq_get(fsq_id)

        if "_error" in resp:
            print(f"  [{idx:>3}/{len(todo)}] ERR  {slug:<45} {resp['_error']}")
            out_cache[slug] = {}   # mark attempted so re-run skips
            errors += 1
        else:
            hours_str = parse_hours(resp.get("hours") or {})
            photo_url = best_photo_url(resp.get("photos") or [])
            phone     = (resp.get("tel") or "").strip()
            website   = (resp.get("website") or "").strip()

            entry: dict = {}
            if hours_str: entry["hours_display"] = hours_str
            if photo_url: entry["photo_url"]     = photo_url
            if phone:     entry["phone"]          = phone
            if website:   entry["website"]        = website

            out_cache[slug] = entry
            fields = list(entry.keys())

            if fields:
                print(f"  [{idx:>3}/{len(todo)}] ✓  {slug:<45} {', '.join(fields)}")
                ok += 1
            else:
                print(f"  [{idx:>3}/{len(todo)}] ·  {slug:<45} (no data returned)")
                skipped += 1

        # Checkpoint every 50 requests
        if idx % 50 == 0:
            save(out_cache)
            print(f"  💾  checkpoint — {idx} processed so far")

        time.sleep(DELAY_S)

    save(out_cache)

    with_hours = sum(1 for v in out_cache.values() if v.get("hours_display"))
    with_photo = sum(1 for v in out_cache.values() if v.get("photo_url"))
    print(f"\n{'─' * 60}")
    print(f"Done: {ok} enriched / {skipped} no-data / {errors} errors")
    print(f"Total cache: {len(out_cache)} entries")
    print(f"  📅  with hours : {with_hours}")
    print(f"  📸  with photo : {with_photo}")
    print(f"Saved → {CACHE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
