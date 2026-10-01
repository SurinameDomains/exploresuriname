"""Shared CSS/JS files (Oct 2026): keep the published site well under the
GitHub Pages 1 GB limit.

Every generated page used to carry the same ~55 KB of inline <style>/<script>
blocks (fonts, the main stylesheet, the menu and search scripts, ...), copied
again into the NL/ES/ZH trees. This step moves every block that is repeated
on many pages into one shared file under /assets/ and puts a reference in its
place:

    <style>X</style>   ->  <link rel="stylesheet" href="/assets/s-<hash>.css">
    <script>X</script> ->  <script src="/assets/j-<hash>.js"></script>

Why this cannot change what a page does:
  * Only bare <style> and <script> tags are touched (no attributes), so JSON-LD,
    modules, async/defer scripts and anything with an id stay inline.
  * The file holds the block's exact bytes and the reference sits exactly where
    the block was. A plain <script src> runs in the same order, at the same
    point, as the inline script it replaces; a stylesheet <link> applies in the
    same cascade position as the <style> it replaces.
  * The shared blocks hold no relative url() references (checked at build
    time; a block that does is left inline).
  * File names are content hashes, so a changed block gets a new name: no
    stale cache, and the service worker's cache-first rule for .css/.js is
    exactly right for them.
  * offline.html and 404.html keep everything inline (they must work alone).

Runs at the start of build_i18n.py (after generate.py and cache_images.py, so
the English pages are final), before the language trees are copied from them.
Old files stay for KEEP_DAYS after their last use, so a page that is still
open in someone's browser can finish loading.
"""
import datetime as _dt
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets"
MANIFEST = OUT / "manifest.json"
BLOCK_RE = re.compile(r"<(style|script)>(.*?)</\1>", re.S)
NAME_RE = re.compile(r"^[sj]-[0-9a-f]{12}\.(css|js)$")
REL_URL_RE = re.compile(r"""url\(\s*["']?(?!data:|https?:|/|#)[^)"'\s]""")
MIN_PAGES = 10      # a block must repeat on at least this many pages
MIN_BYTES = 300     # ...and be at least this big, or it stays inline
KEEP_DAYS = 30
SKIP = {"offline.html", "404.html"}


def _name(kind, body):
    h = hashlib.md5(body.encode("utf-8")).hexdigest()[:12]
    return f"s-{h}.css" if kind == "style" else f"j-{h}.js"


def run(pages, today=None):
    """pages: iterable of (Path, rel) English pages. Returns a short report."""
    today = today or _dt.date.today().isoformat()
    texts = {}
    counts = Counter()
    for p, rel in pages:
        if rel in SKIP or Path(rel).name in SKIP:
            continue
        try:
            h = p.read_text(encoding="utf-8")
        except Exception:
            continue
        texts[p] = h
        for m in BLOCK_RE.finditer(h):
            counts[(m.group(1), m.group(2))] += 1

    shared = {}
    for (kind, body), c in counts.items():
        if c < MIN_PAGES or len(body.encode("utf-8")) < MIN_BYTES:
            continue
        if kind == "style" and REL_URL_RE.search(body):
            continue   # a relative url() would resolve against /assets/, not the page
        if "</" + kind in body.lower():
            continue   # never happens in valid HTML; refuse rather than guess
        shared[(kind, body)] = _name(kind, body)

    if not shared:
        return "assets: nothing to share"

    # 1) write the files first: a page must never point at a file that is not there
    OUT.mkdir(exist_ok=True)
    for (kind, body), name in shared.items():
        f = OUT / name
        if not f.exists() or f.read_text(encoding="utf-8") != body:
            with open(f, "w", encoding="utf-8", newline="") as fh:
                fh.write(body)

    # 2) point the pages at them
    def repl(m):
        name = shared.get((m.group(1), m.group(2)))
        if not name:
            return m.group(0)
        if m.group(1) == "style":
            return f'<link rel="stylesheet" href="/assets/{name}">'
        return f'<script src="/assets/{name}"></script>'

    changed = 0
    saved = 0
    for p, h in texts.items():
        new = BLOCK_RE.sub(repl, h)
        if new != h:
            p.write_text(new, encoding="utf-8")
            changed += 1
            saved += len(h.encode("utf-8")) - len(new.encode("utf-8"))

    # 3) housekeeping: remember when each file was last used, drop long-unused ones
    try:
        seen = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception:
        seen = {}
    for name in shared.values():
        seen[name] = today
    cutoff = (_dt.date.fromisoformat(today) - _dt.timedelta(days=KEEP_DAYS)).isoformat()
    removed = 0
    for f in OUT.iterdir():
        if not NAME_RE.match(f.name) or f.name in shared.values():
            continue
        last = seen.get(f.name)
        if last is None:
            seen[f.name] = today        # unknown file: start its clock now
        elif last < cutoff:
            f.unlink()
            seen.pop(f.name, None)
            removed += 1
    seen = {k: v for k, v in seen.items() if (OUT / k).exists()}
    new_manifest = json.dumps(seen, indent=1, sort_keys=True) + "\n"
    if not MANIFEST.exists() or MANIFEST.read_text(encoding="utf-8") != new_manifest:
        MANIFEST.write_text(new_manifest, encoding="utf-8")

    return (f"assets: {len(shared)} shared files, {changed} pages updated, "
            f"{saved / 1e6:.1f} MB less HTML in the English tree, {removed} old files removed")
