"""
cache_images.py - Image caching for ExploreSuriname

Downloads all external image src= URLs from generated HTML pages into
the local images/ folder and rewrites the HTML to use local paths.

All JPG/PNG images in the images/ folder are converted to WebP at max
900px wide using Pillow -- whether they were downloaded by this script
or manually uploaded to the repo. This cuts typical file sizes from
500 KB-3 MB down to 40-150 KB.

Usage:
    python cache_images.py             # download + rewrite HTML
    python cache_images.py --dry-run   # show what would happen, no writes

The cache map lives in image_cache.json:
    { "https://example.com/photo.jpg": "images/a1b2c3d4.webp", ... }

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

try:
    from PIL import Image as _PILImage
    _PILLOW_OK = True
except ImportError:
    _PILImage = None
    _PILLOW_OK = False
    print("WARNING: Pillow not installed -- images will be saved without WebP conversion.")
    print("         Run: pip install Pillow")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
IMAGES_DIR = SCRIPT_DIR / "images"
CACHE_FILE = SCRIPT_DIR / "image_cache.json"
HTML_GLOB  = list(SCRIPT_DIR.rglob("*.html"))

IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

# These formats get converted to WebP on download.
# SVG, GIF, and already-WebP files are left as-is.
CONVERT_TO_WEBP = {".jpg", ".jpeg", ".png"}

# Max width (px) for WebP output. Cards are ~400px wide on mobile at 2x
# DPR, so 900px covers retina mobile and most desktop card grids.
WEBP_MAX_WIDTH = 900
WEBP_QUALITY   = 82

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
    # Store as .webp for formats we can convert
    if ext in CONVERT_TO_WEBP and _PILLOW_OK:
        ext = ".webp"
    return stem + ext


def _convert_to_webp(src_path, dest_path):
    """Convert src_path (jpg/png) to dest_path (.webp) at WEBP_MAX_WIDTH.
    Returns True on success, False on failure.
    """
    if not _PILLOW_OK:
        return False
    try:
        img = _PILImage.open(src_path)
        w, h = img.size
        if w > WEBP_MAX_WIDTH:
            h = int(h * WEBP_MAX_WIDTH / w)
            w = WEBP_MAX_WIDTH
            img = img.resize((w, h), _PILImage.LANCZOS)
        if img.mode == "P":
            img = img.convert("RGBA")
        if img.mode == "RGBA":
            img.save(dest_path, "webp", quality=WEBP_QUALITY, method=4)
        else:
            img = img.convert("RGB")
            img.save(dest_path, "webp", quality=WEBP_QUALITY, method=4)
        return True
    except Exception as exc:
        print("  WebP convert FAILED (%s): %s" % (type(exc).__name__, src_path.name))
        return False


def _save_cache(cache):
    CACHE_FILE.write_text(
        json.dumps(cache, indent=2, sort_keys=True),
        encoding="utf-8"
    )


def _extract_img_srcs(html):
    raw = re.findall(r"""src=['"]([^'"]+)['"]""", html)
    raw += re.findall(r"""url\(['"]?([^'"\)]+)['"]?\)""", html)
    return [u for u in raw if _is_image_url(u)]


def _rewrite_html(html_contents, cache, dry_run):
    """Replace cached external URLs with local paths in all HTML files."""
    rewrites = 0
    for html_path, content in html_contents.items():
        new_content = content
        for url, local_path in cache.items():
            if url in new_content:
                new_content = new_content.replace(
                    'src="%s"' % url, 'src="%s"' % local_path
                ).replace(
                    "src='%s'" % url, "src='%s'" % local_path
                )
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


def _rewrite_html_local_paths(old_local, new_local, dry_run):
    """Rewrite a local image path (e.g. images/foo.png -> images/foo.webp)
    across all HTML files. Used for manually uploaded images not in the cache.
    Returns number of files rewritten.
    """
    rewrites = 0
    for html_path in sorted(HTML_GLOB):
        content = html_path.read_text(encoding="utf-8")
        new_content = content.replace(
            'src="%s"' % old_local, 'src="%s"' % new_local
        ).replace(
            "src='%s'" % old_local, "src='%s'" % new_local
        ).replace(
            'url("%s")' % old_local, 'url("%s")' % new_local
        ).replace(
            "url('%s')" % old_local, "url('%s')" % new_local
        ).replace(
            "url(%s)" % old_local, "url(%s)" % new_local
        )
        if new_content != content:
            rewrites += 1
            if not dry_run:
                html_path.write_text(new_content, encoding="utf-8")
                print("  rewritten   : %s" % html_path.name)
    return rewrites


def _download(url, dest):
    """Download url to dest, converting to WebP via Pillow if applicable."""
    req = urllib.request.Request(url, headers=HEADERS)

    src_ext = ""
    src_path_lower = url.split("?")[0].lower()
    for candidate in CONVERT_TO_WEBP:
        if src_path_lower.endswith(candidate):
            src_ext = candidate
            break

    needs_convert = dest.suffix == ".webp" and src_ext in CONVERT_TO_WEBP and _PILLOW_OK
    raw_dest = dest.with_suffix(src_ext) if needs_convert else dest

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()
            raw_dest.write_bytes(data)
            break
        except Exception as exc:
            if attempt <= MAX_RETRIES:
                time.sleep(2 ** attempt)
            else:
                print("  FAILED (%s): %s" % (type(exc).__name__, url[:80]))
                return False

    if needs_convert:
        ok = _convert_to_webp(raw_dest, dest)
        raw_dest.unlink(missing_ok=True)
        if not ok:
            raw_dest.rename(dest.with_suffix(src_ext))
            return False
    return True


# ---------------------------------------------------------------------------
# Migration pass
# ---------------------------------------------------------------------------

def _migrate_existing(cache, dry_run):
    """Convert ALL JPG/PNG files in images/ to WebP -- whether they arrived
    via the cache script or were manually uploaded to the repo.

    Strategy:
      1. Scan images/ for any .jpg/.png file.
      2. Convert each to .webp, delete the original.
      3. Update any matching cache entry (url -> local path).
      4. Rewrite HTML references for files not in the cache (manual uploads).

    Returns the number of files converted.
    """
    if not _PILLOW_OK:
        return 0

    # Build reverse map: local filename stem -> cache url (for cache updates)
    stem_to_url = {}
    for url, local_path in cache.items():
        stem_to_url[Path(local_path).stem] = url

    converted = 0
    saved_kb = 0

    for p in sorted(IMAGES_DIR.glob("*")):
        if p.suffix.lower() not in CONVERT_TO_WEBP:
            continue

        webp_path = p.with_suffix(".webp")
        if webp_path.exists():
            # Already converted; just make sure cache + HTML are up to date
            old_local = "images/" + p.name
            new_local = "images/" + webp_path.name
            url = stem_to_url.get(p.stem)
            if url and cache.get(url) != new_local:
                if not dry_run:
                    cache[url] = new_local
                    _rewrite_html_local_paths(old_local, new_local, dry_run)
            continue

        orig_size = p.stat().st_size

        if dry_run:
            in_cache = p.stem in stem_to_url
            tag = "cached" if in_cache else "manual upload"
            print("  [dry-run] would convert %s (%d KB) [%s]" % (
                p.name, orig_size // 1024, tag))
            converted += 1
            continue

        ok = _convert_to_webp(p, webp_path)
        if ok:
            new_size = webp_path.stat().st_size
            saving = orig_size - new_size
            saved_kb += saving // 1024

            old_local = "images/" + p.name
            new_local = "images/" + webp_path.name

            # Update cache entry if this file came from the cache script
            url = stem_to_url.get(p.stem)
            if url:
                cache[url] = new_local
                tag = "cached"
            else:
                # Manually uploaded -- rewrite HTML local path references
                n = _rewrite_html_local_paths(old_local, new_local, dry_run)
                tag = "manual upload%s" % (", rewrote %d HTML file(s)" % n if n else "")

            print("  migrated %s -> %s  (%d KB -> %d KB, saved %d KB) [%s]" % (
                p.name, webp_path.name, orig_size // 1024, new_size // 1024,
                saving // 1024, tag))
            try:
                p.unlink()
            except OSError:
                pass  # best-effort; GitHub Actions has full write access
            converted += 1
        else:
            print("  migrate FAILED: %s (keeping original)" % p.name)

    if converted and not dry_run:
        print("Migration: saved %d KB total across %d images" % (saved_kb, converted))

    return converted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run=False):
    IMAGES_DIR.mkdir(exist_ok=True)

    if CACHE_FILE.exists():
        raw = CACHE_FILE.read_text(encoding="utf-8").strip()
        cache = json.loads(raw) if raw else {}
    else:
        cache = {}

    print("ExploreSuriname image cache -- %d entries already cached" % len(cache))
    if dry_run:
        print("(dry-run mode -- no files will be written)\n")

    # Migration pass: convert ALL jpg/png in images/ to WebP
    if _PILLOW_OK:
        print("Migration pass: converting all JPG/PNG in images/ to WebP...")
        n_migrated = _migrate_existing(cache, dry_run)
        if n_migrated:
            print("Migration: converted %d image(s) to WebP\n" % n_migrated)
            if not dry_run:
                _save_cache(cache)
        else:
            print("Migration: nothing to convert (all already WebP or non-convertible)\n")

    # Collect all unique external image URLs from generated HTML
    all_urls = set()
    html_contents = {}
    for html_path in sorted(HTML_GLOB):
        content = html_path.read_text(encoding="utf-8")
        html_contents[html_path] = content
        all_urls.update(_extract_img_srcs(content))

    print("Found %d unique external image URLs across %d HTML files\n" % (
        len(all_urls), len(HTML_GLOB)))

    # Phase 1 (fast): register already-downloaded files
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

    # Phase 2 (slow): download missing images
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
