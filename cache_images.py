"""
cache_images.py - Image caching for ExploreSuriname

Downloads all external image src= URLs from generated HTML pages into
the local images/ folder and rewrites the HTML to use local paths.

Usage:
    python cache_images.py             # download + rewrite HTML
    python cache_images.py --dry-run   # show what would happen, no writes

The cache map lives in image_cache.json:
    { "https://example.com/photo.jpg": "images/a1b2c3d4.jpg", ... }

Run order in update.yml:
    1. python generate.py        (produces HTML with external URLs)
    2. python cache_images.py    (downloads new images, rewrites HTML)
    3. git add ... images/ image_cache.json

Two-phase design:
    Phase 1 (fast): register already-downloaded files, rewrite HTML now
                    so the site benefits immediately from what is cached.
    Phase 2 (slow): download images not yet on disk, rewrite again.
    A mid-run timeout still leaves a partially-rewritten site rather
    than leaving all HTML unchanged.
"""

import hashlib
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "images"
CACHE_FILE = SCRIPT_DIR / "image_cache.json"
HTML_GLOB  = list(SCRIPT_DIR.rglob("*.html"))

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

SKIP_PATTERNS = [
    "cdn.tailwindcss.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "favicon",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; ExploreSurinameBot/1.0; "
        "+https://exploresuriname.com)"
    )
}

TIMEOUT     = 15
MAX_RETRIES = 2

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_image_url(url):
    if not url.startswith("http"):
        return False
    for skip in SKIP_PATTERNS:
        if skip in url:
            return False
    path = url.split("?")[0].lower()
    return any(path.endswith(ext) for ext in IMG_EXTS)


def _local_filename(url):
    stem = hashlib.md5(url.encode()).hexdigest()
    path = url.split("?")[0].lower()
    ext = ""
    for candidate in IMG_EXTS:
        if path.endswith(candidate):
            ext = candidate
            break
    return stem + ext


def _save_cache(cache):
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, sort_keys=True),
        encoding="utf-8"
    )


def _extract_img_srcs(html):
    # src="..." attributes
    raw = re.findall(r"""src=['"]([^'"]+)['"]""", html)
    # CSS background-image: url('...') or url("...") or url(...)
    raw += re.findall(r"""url\(['"]?([^'"\)]+)['"]?\)""", html)
    return [u for u in raw if _is_image_url(u)]


def _rewrite_html(html_contents, cache, dry_run):
    """Replace cached external URLs with local paths in all HTML files."""
    rewrites = 0
    for html_path, content in html_contents.items():
        new_content = content
        for url, local_path in cache.items():
            if url in new_content:
                # Rewrite src= attributes
                new_content = new_content.replace(
                    'src="%s"' % url, 'src="%s"' % local_path
                ).replace(
                    "src='%s'" % url, "src='%s'" % local_path
                )
                # Rewrite CSS url() values (all three quote styles)
                new_content = new_content.replace(
                    "url('%s')" % url, "url('%s')" % local_path
                ).replace(
                    'url("%s")' % url, 'url("%s")' % local_path
                ).replace(
                    "url(%s)" % url, "url(%s)" % local_path
                )
        if new_content != content:
            rewrites += 1
            if not dry_run:
                html_path.write_text(new_content, encoding="utf-8")
                print("  rewritten   : %s" % html_path.name)
    return rewrites


def _download(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(1, MAX_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
            dest.write_bytes(data)
            return True
        except Exception as exc:
            if attempt <= MAX_RETRIES:
                time.sleep(2 ** attempt)
            else:
                print("  FAILED (%s): %s" % (type(exc).__name__, url[:80]))
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run=False):
    IMAGES_DIR.mkdir(exist_ok=True)

    # Load existing cache
    if CACHE_FILE.exists():
        raw = CACHE_FILE.read_text(encoding="utf-8").strip()
        cache = json.loads(raw) if raw else {}
    else:
        cache = {}

    print("ExploreSuriname image cache -- %d entries already cached" % len(cache))
    if dry_run:
        print("(dry-run mode -- no files will be written)\n")

    # Collect all unique external image URLs from generated HTML
    all_urls = set()
    html_contents = {}
    for html_path in sorted(HTML_GLOB):
        content = html_path.read_text(encoding="utf-8")
        html_contents[html_path] = content
        all_urls.update(_extract_img_srcs(content))

    print("Found %d unique external image URLs across %d HTML files\n" % (
        len(all_urls), len(HTML_GLOB)))

    # ------------------------------------------------------------------
    # Phase 1 (fast): register already-downloaded files, rewrite HTML
    # ------------------------------------------------------------------
    registered = 0
    for url in sorted(all_urls):
        if url in cache:
            continue
        filename = _local_filename(url)
        if (IMAGES_DIR / filename).exists():
            cache[url] = "images/" + filename
            registered += 1

    if registered:
        print("Phase 1: registered %d already-downloaded files" % registered)
        if not dry_run:
            _save_cache(cache)

    rewrites_1 = _rewrite_html(html_contents, cache, dry_run)
    if rewrites_1:
        print("Phase 1: rewrote %d HTML file(s) with cached paths\n" % rewrites_1)
        html_contents = {p: p.read_text(encoding="utf-8") for p in sorted(HTML_GLOB)}

    # ------------------------------------------------------------------
    # Phase 2 (slow): download missing images
    # ------------------------------------------------------------------
    missing = sorted(u for u in all_urls if u not in cache)
    print("Phase 2: %d image(s) still need downloading" % len(missing))

    newly_downloaded = 0
    for url in missing:
        filename = _local_filename(url)
        dest = IMAGES_DIR / filename
        label = (url[:72] + "...") if len(url) > 75 else url
        print("  downloading : %s" % label)
        if dry_run:
            continue
        if _download(url, dest):
            size_kb = dest.stat().st_size // 1024
            print("    saved %d KB -> images/%s" % (size_kb, filename))
            cache[url] = "images/" + filename
            newly_downloaded += 1
            _save_cache(cache)

    # Rewrite HTML again for any newly downloaded images
    if newly_downloaded:
        rewrites_2 = _rewrite_html(html_contents, cache, dry_run)
        if rewrites_2:
            print("\nPhase 2: rewrote %d HTML file(s) with new images" % rewrites_2)

    if not dry_run:
        _save_cache(cache)
        print("\nCache saved -> image_cache.json (%d total entries)" % len(cache))

    total_cached = len([u for u in all_urls if u in cache])
    print("\nDone. %d/%d URLs cached, %d new images downloaded." % (
        total_cached, len(all_urls), newly_downloaded))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
