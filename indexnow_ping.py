"""
IndexNow ping — runs after the site is generated, before the deploy commit.

Submits ONLY the URLs whose sitemap <lastmod> changed since the previous run.

Why: IndexNow explicitly counts every submitted URL against the site's crawl
quota, and its own guidance is "submit only when content has changed; do not
resubmit unchanged URLs" (repeated resubmission is a documented cause of
HTTP 422). This build runs every ~15 minutes and the sitemap holds ~2,300 URLs,
so submitting the whole sitemap each time burned ~220k submissions/day against
a handful of genuinely changed pages.

generate.py already computes a hash-based <lastmod> (listing_lastmod_cache.json)
that only advances when page content really changes, so the sitemap itself is a
reliable change feed. We persist the last-submitted url -> lastmod map in
indexnow_state.json (committed by the workflow) and diff against it.

Zero effect on page load speed; does not touch Google at all.
"""

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SITE_HOST = "exploresuriname.com"
SITE_URL   = f"https://{SITE_HOST}"
KEY        = "34e092d0-1f92-4a82-9ecf-b442b53d80a0"
KEY_LOC    = f"{SITE_URL}/{KEY}.txt"
API_URL    = "https://api.indexnow.org/indexnow"
SITEMAP    = "sitemap.xml"
STATE      = Path("indexnow_state.json")
BATCH_SIZE = 10_000   # IndexNow hard max per request

# Safety valve: if a broken build drops most of the sitemap, do not spam the
# API with thousands of "deleted" URLs. Skip the removal notices instead.
MAX_REMOVED_FRACTION = 0.10


def load_sitemap(sitemap_path: str) -> dict[str, str]:
    """Return {url: lastmod}. lastmod may be '' if the sitemap omits it."""
    try:
        tree = ET.parse(sitemap_path)
    except (FileNotFoundError, ET.ParseError) as exc:
        print(f"[IndexNow] Could not parse {sitemap_path}: {exc}", file=sys.stderr)
        return {}
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    out: dict[str, str] = {}
    for url in tree.findall(".//sm:url", ns):
        loc = url.find("sm:loc", ns)
        if loc is None or not loc.text:
            continue
        lm = url.find("sm:lastmod", ns)
        out[loc.text.strip()] = (lm.text.strip() if lm is not None and lm.text else "")
    return out


def load_state() -> dict[str, str]:
    if not STATE.exists():
        return {}
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"[IndexNow] State unreadable ({exc}) — treating as first run.", file=sys.stderr)
        return {}


def save_state(state: dict[str, str]) -> None:
    try:
        STATE.write_text(
            json.dumps(state, ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[IndexNow] Could not write state: {exc}", file=sys.stderr)


def submit(urls: list[str]) -> bool:
    """POST urls in batches. Returns True only if every batch was accepted."""
    ok = True
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
            return False   # do not record state — retry these next run

        if status in (200, 202):
            print(f"[IndexNow] Submitted {len(batch)} URLs — HTTP {status} OK")
        elif status == 422:
            print("[IndexNow] HTTP 422: URL(s) rejected — check sitemap/key", file=sys.stderr)
            ok = False
        elif status == 429:
            print("[IndexNow] HTTP 429: rate limited — will retry next deploy", file=sys.stderr)
            ok = False
        else:
            print(f"[IndexNow] Unexpected HTTP {status}", file=sys.stderr)
            ok = False
    return ok


def main() -> None:
    current = load_sitemap(SITEMAP)
    if not current:
        print("[IndexNow] No URLs found — skipping.", file=sys.stderr)
        return
    print(f"[IndexNow] Sitemap holds {len(current)} URLs")

    previous = load_state()

    # First run: seed state without submitting. IndexNow is for changes made
    # *after* setup; the sitemap's lastmod values cover the historical backlog.
    if not previous:
        save_state(current)
        print(f"[IndexNow] First run — seeded state with {len(current)} URLs, nothing submitted.")
        return

    changed = sorted(u for u, lm in current.items() if previous.get(u) != lm)

    removed = sorted(u for u in previous if u not in current)

    # A build that drops most of the sitemap is almost certainly broken, not a
    # mass deletion. Skip the removal notices AND refuse to persist state from
    # this run — otherwise the truncated sitemap becomes the new baseline and
    # the next healthy build resubmits the whole site as "changed".
    suspicious = bool(removed) and len(removed) > len(previous) * MAX_REMOVED_FRACTION
    if suspicious:
        print(
            f"[IndexNow] {len(removed)} URLs vanished from the sitemap "
            f"(>{MAX_REMOVED_FRACTION:.0%}) — looks like a bad build, not deletions. "
            "Skipping removal notices and leaving state untouched.",
            file=sys.stderr,
        )
        removed = []

    to_submit = changed + removed
    if not to_submit:
        print("[IndexNow] Nothing changed since last run — no submission.")
        return

    print(f"[IndexNow] {len(changed)} changed, {len(removed)} removed -> submitting {len(to_submit)}")
    for u in to_submit[:10]:
        print(f"[IndexNow]   {u}")
    if len(to_submit) > 10:
        print(f"[IndexNow]   ... and {len(to_submit) - 10} more")

    if submit(to_submit):
        if suspicious:
            print("[IndexNow] Sitemap looked truncated — state deliberately not updated.")
        else:
            save_state(current)
            print("[IndexNow] State updated.")
    else:
        print("[IndexNow] Submission incomplete — state NOT updated, will retry next run.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
