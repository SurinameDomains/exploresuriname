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

import datetime
import hashlib
import json
import re
import sys
import time
import urllib.error
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
# Generated language trees. build_i18n.py rebuilds nl/ and es/ from the English
# pages immediately after this script runs, so rewriting them here is thrown
# away: two thirds of the files for nothing. An image URL can only reach a
# translated page via its English source, and rewriting an English page changes
# its hash, which makes build_i18n re-emit that page's translations.
GENERATED_TREES = {"nl", "es"}

def _english_html():
    out = []
    for p in SCRIPT_DIR.rglob("*.html"):
        rel = p.relative_to(SCRIPT_DIR)
        if rel.parts and rel.parts[0] in GENERATED_TREES:
            continue
        out.append(p)
    return out

HTML_GLOB  = _english_html()

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
    # Meta CDN URLs always return 403 from servers (auth-token protected,
    # browser-only). Skipping saves ~10 min of failed retries per run.
    # Already-cached entries are still rewritten to local paths via image_cache.json.
    "fbcdn.net",
    "cdninstagram.com",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

TIMEOUT     = 8
MAX_RETRIES = 1

# Download failures used to be forgotten between runs, so a permanently dead
# image was re-attempted on every build: 3 attempts with 2s and 4s backoff each
# time. Failures are now remembered and skipped for a week, then retried once in
# case the host came back. Conversion failures (corrupt files that can never
# become WebP) are remembered here too, under the "convert:" prefix.
FAILURES_FILE    = SCRIPT_DIR / "data" / "image_failures.json"
RETRY_AFTER_DAYS = 7

def _load_failures():
    try:
        return json.loads(FAILURES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_failures(failures):
    FAILURES_FILE.parent.mkdir(parents=True, exist_ok=True)
    FAILURES_FILE.write_text(json.dumps(failures, indent=1, sort_keys=True),
                             encoding="utf-8")

def _recently_failed(failures, key):
    rec = failures.get(key)
    if not rec:
        return False
    try:
        last = datetime.datetime.fromisoformat(rec["last"])
    except Exception:
        return False
    age = datetime.datetime.now(datetime.timezone.utc) - last
    return age.days < RETRY_AFTER_DAYS

def _note_failure(failures, key, error):
    rec = failures.get(key) or {}
    rec["last"]  = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    rec["count"] = int(rec.get("count", 0)) + 1
    rec["error"] = str(error)[:120]
    failures[key] = rec

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


# src="URL" / src='URL' / url(URL) / url('URL') / url("URL")
_EXT_REF_RE = re.compile(
    r"""(src=["']|url\(["']?)(https?://[^"'()\s>]+)""")

def _rewrite_html(html_contents, cache, dry_run):
    """Replace cached external URLs with local paths in all HTML files.

    One regex pass per file. The old version looped over every cache entry for
    every file, so cost grew with cache size (789 entries x 3216 files).
    html_contents is updated in place so callers never have to re-read the site.
    """
    def _repl(m):
        local = cache.get(m.group(2))
        if not local:
            return m.group(0)
        # Always use an absolute path so it resolves correctly from
        # any subdirectory depth (e.g. /listing/slug/index.html).
        return m.group(1) + "/" + local.lstrip("/")

    rewrites = 0
    for html_path, content in html_contents.items():
        new_content = _EXT_REF_RE.sub(_repl, content)
        if new_content != content:
            rewrites += 1
            html_contents[html_path] = new_content
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
            # A 403/404 is a verdict, not a hiccup. Sleeping and asking the same
            # server the same question twice more just burns build minutes.
            fatal = (isinstance(exc, urllib.error.HTTPError)
                     and 400 <= exc.code < 500 and exc.code != 429)
            if attempt <= MAX_RETRIES and not fatal:
                time.sleep(2 ** attempt)
            else:
                print("  FAILED (%s): %s" % (type(exc).__name__, url[:80]))
                return exc

    if needs_convert:
        ok = _convert_to_webp(raw_dest, dest)
        if ok:
            raw_dest.unlink(missing_ok=True)
        else:
            raw_dest.rename(dest.with_suffix(src_ext))
            return "WebP conversion failed"
    return True


# ---------------------------------------------------------------------------
# Migration pass
# ---------------------------------------------------------------------------

def _migrate_existing(cache, dry_run, failures):
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
        # A file that failed to decode last week will fail again today. Two of
        # these were being retried, and logged, on every single build.
        if _recently_failed(failures, "convert:" + p.name):
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
            print("  migrate FAILED: %s (keeping original, skipping for %d days)"
                  % (p.name, RETRY_AFTER_DAYS))
            _note_failure(failures, "convert:" + p.name, "WebP conversion failed")

    if converted and not dry_run:
        print("Migration: saved %d KB total across %d images" % (saved_kb, converted))

    return converted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CARD_VARIANT_WIDTH = 480
WIDTHS_FILE = SCRIPT_DIR / "image_widths.json"

def _build_card_variants():
    """Create missing -480 card thumbnails and refresh image_widths.json.
    Idempotent; skips hero-*/home-* art and existing variants."""
    if not _PILLOW_OK:
        return
    widths, made = {}, 0
    for p in sorted(IMAGES_DIR.glob("*.webp")):
        if p.name.startswith(("hero-", "home-")) or p.stem.endswith(("-m", "-480")):
            continue
        try:
            img = _PILImage.open(p)
        except Exception:
            continue
        w, h = img.size
        widths[p.name] = w
        out = p.with_name(p.stem + "-480.webp")
        if w > 560 and not out.exists():
            img.resize((CARD_VARIANT_WIDTH, round(h * CARD_VARIANT_WIDTH / w)),
                       _PILImage.LANCZOS).save(out, "webp", quality=78, method=4)
            made += 1
    WIDTHS_FILE.write_text(json.dumps(widths, separators=(",", ":")), encoding="utf-8")
    if made:
        print("\nCard variants: created %d new -480 thumbnails" % made)


OG_DIR = IMAGES_DIR / "og"
OG_MANIFEST = SCRIPT_DIR / "data" / "og_twins.json"
OG_MIN_WIDTH = 400      # link-preview crawlers drop anything smaller
OG_MAX_WIDTH = 1200


def _build_og_jpegs():
    """Write a JPEG twin of every cached image into images/og/.

    WhatsApp, Signal and several Android link-preview crawlers do not decode
    WebP, so a shared listing link showed a preview card with no thumbnail even
    though the page had a perfectly good og:image. generate.py points og:image
    at images/og/<name>.jpg for any source at least OG_MIN_WIDTH wide and falls
    back to the site card below that.

    Skipping used to compare mtimes, which cannot work on CI: actions/checkout
    writes every file in the same instant, so the comparison was decided by git
    index order rather than by content. ~93 twins were re-encoded on every run
    and committed again as changed binaries. The skip is now a content hash of
    the source, recorded in data/og_twins.json.

    The og/ subdirectory matters. _migrate_existing() converts every JPEG
    sitting directly in images/ to WebP and deletes the original, so twins kept
    beside their sources would be eaten on the next run. Both that scan and the
    card-variant scan are non-recursive, so a subdirectory is safe.
    """
    if not _PILLOW_OK:
        return
    OG_DIR.mkdir(exist_ok=True)
    try:
        seen = json.loads(OG_MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        seen = {}
    made, skipped = 0, 0
    fresh = {}
    for p in sorted(IMAGES_DIR.glob("*.webp")):
        if p.stem.endswith(("-480", "-m")):
            continue
        out = OG_DIR / (p.stem + ".jpg")
        try:
            digest = hashlib.md5(p.read_bytes()).hexdigest()
            fresh[p.name] = digest
            if out.exists() and seen.get(p.name) == digest:
                skipped += 1
                continue
            img = _PILImage.open(p)
            if img.size[0] < OG_MIN_WIDTH:
                if out.exists():
                    out.unlink()      # source shrank below the useful threshold
                continue
            img = img.convert("RGB")
            if img.size[0] > OG_MAX_WIDTH:
                w, h = img.size
                img = img.resize((OG_MAX_WIDTH, round(h * OG_MAX_WIDTH / w)), _PILImage.LANCZOS)
            img.save(out, "JPEG", quality=82, optimize=True, progressive=True)
            made += 1
        except Exception as e:
            fresh.pop(p.name, None)
            print("  og twin failed for %s: %s" % (p.name, e))
    OG_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    OG_MANIFEST.write_text(json.dumps(fresh, separators=(",", ":"), sort_keys=True),
                           encoding="utf-8")
    print("\nShare previews: %d JPEG twin(s) written to images/og/, %d unchanged"
          % (made, skipped))


def main(dry_run=False):
    t_start = time.time()
    _laps = []
    def lap(name):
        _laps.append((name, time.time() - lap.t)); lap.t = time.time()
    lap.t = time.time()

    IMAGES_DIR.mkdir(exist_ok=True)
    failures = _load_failures()

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
        n_migrated = _migrate_existing(cache, dry_run, failures)
        if n_migrated:
            print("Migration: converted %d image(s) to WebP\n" % n_migrated)
            if not dry_run:
                _save_cache(cache)
        else:
            print("Migration: nothing to convert (all already WebP or non-convertible)\n")
    lap("migration")

    # Collect all unique external image URLs from generated HTML
    all_urls = set()
    html_contents = {}
    for html_path in sorted(HTML_GLOB):
        content = html_path.read_text(encoding="utf-8")
        html_contents[html_path] = content
        all_urls.update(_extract_img_srcs(content))

    print("Found %d unique external image URLs across %d HTML files "
          "(nl/ and es/ excluded; build_i18n.py regenerates them)\n" % (
        len(all_urls), len(HTML_GLOB)))
    lap("read html")

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
        # _rewrite_html updates html_contents in place, so the whole site no
        # longer has to be read off disk a second time here.
    lap("rewrite")

    # Phase 2 (slow): download missing images
    missing_all = sorted(u for u in all_urls if u not in cache)
    missing = [u for u in missing_all if not _recently_failed(failures, u)]
    deferred = len(missing_all) - len(missing)
    print("Phase 2: %d image(s) still need downloading"
          "%s" % (len(missing),
                  " (%d known-dead skipped, retried after %d days)"
                  % (deferred, RETRY_AFTER_DAYS) if deferred else ""))

    newly_downloaded = 0
    for url in missing:
        filename = _local_filename(url)
        dest = IMAGES_DIR / filename
        label = (url[:72] + "...") if len(url) > 75 else url
        print("  downloading : %s" % label)
        if dry_run:
            continue
        result = _download(url, dest)
        if result is True:
            size_kb = dest.stat().st_size // 1024
            print("    saved %d KB -> images/%s" % (size_kb, filename))
            cache[url] = "images/" + filename
            failures.pop(url, None)
            newly_downloaded += 1
            _save_cache(cache)
        else:
            _note_failure(failures, url, result)

    if newly_downloaded:
        rewrites_2 = _rewrite_html(html_contents, cache, dry_run)
        if rewrites_2:
            print("\nPhase 2: rewrote %d HTML file(s) with new images" % rewrites_2)
    lap("download")

    if not dry_run:
        _save_cache(cache)
        print("\nCache saved -> image_cache.json (%d total entries)" % len(cache))

    if not dry_run:
        _save_failures(failures)
        _build_card_variants()
        lap("card variants")
        _build_og_jpegs()
        lap("share previews")

    total_cached = len([u for u in all_urls if u in cache])
    print("\nDone. %d/%d URLs cached, %d new images downloaded." % (
        total_cached, len(all_urls), newly_downloaded))
    print("Timing: %s | total %.1fs" % (
        ", ".join("%s %.1fs" % (n, d) for n, d in _laps if d >= 0.05),
        time.time() - t_start))


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    main(dry_run=dry_run)
