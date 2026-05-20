"""
IndexNow ping — runs after generate.py in GitHub Actions.
Reads sitemap.xml, submits all URLs to IndexNow (Bing/Yandex).
Zero effect on page load speed; does not touch Google at all.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

SITE_HOST = "exploresuriname.com"
SITE_URL   = f"https://{SITE_HOST}"
KEY        = "34e092d0-1f92-4a82-9ecf-b442b53d80a0"
KEY_LOC    = f"{SITE_URL}/{KEY}.txt"
API_URL    = "https://api.indexnow.org/indexnow"
SITEMAP    = "sitemap.xml"
BATCH_SIZE = 10_000  # IndexNow max per request


def load_urls(sitemap_path: str) -> list[str]:
    try:
        tree = ET.parse(sitemap_path)
    except (FileNotFoundError, ET.ParseError) as exc:
        print(f"[IndexNow] Could not parse {sitemap_path}: {exc}", file=sys.stderr)
        return []
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    return [loc.text.strip() for loc in tree.findall(".//sm:loc", ns) if loc.text]


def ping(urls: list[str]) -> None:
    if not urls:
        print("[IndexNow] No URLs found — skipping.", file=sys.stderr)
        return

    # Submit in batches (we have ~700 URLs, well under 10k, but future-proof)
    for i in range(0, len(urls), BATCH_SIZE):
        batch = urls[i : i + BATCH_SIZE]
        payload = json.dumps(
            {
                "host": SITE_HOST,
                "key": KEY,
                "keyLocation": KEY_LOC,
                "urlList": batch,
            }
        ).encode("utf-8")

        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
        except urllib.error.HTTPError as exc:
            status = exc.code
        except urllib.error.URLError as exc:
            print(f"[IndexNow] Network error: {exc.reason}", file=sys.stderr)
            sys.exit(0)  # Non-fatal — don't break the deploy

        if status in (200, 202):
            print(f"[IndexNow] Submitted {len(batch)} URLs — HTTP {status} OK")
        elif status == 422:
            print(f"[IndexNow] HTTP 422: one or more URLs invalid — check sitemap", file=sys.stderr)
        elif status == 429:
            print(f"[IndexNow] HTTP 429: rate limited — will retry next deploy", file=sys.stderr)
        else:
            print(f"[IndexNow] Unexpected HTTP {status}", file=sys.stderr)


if __name__ == "__main__":
    urls = load_urls(SITEMAP)
    print(f"[IndexNow] Found {len(urls)} URLs in sitemap")
    ping(urls)
