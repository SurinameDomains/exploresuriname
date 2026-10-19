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
State format v2 (19 Oct 2026): {"v": 2, "urls": {...}, "missing_since": {...}};
the old flat {url: lastmod} file is still read.

Zero effect on page load speed; does not touch Google at all.
"""

import json
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SITE_HOST = "exploresuriname.com"
SITE_URL   = f"https://{SITE_HOST}"
KEY        = "34e092d0-1f92-4a82-9ecf-b442b53d80a0"
KEY_LOC    = f"{SITE_URL}/{KEY}.txt"
API_URL    = "https://api.indexnow.org/indexnow"
SITEMAP    = "sitemap.xml"
STATE      = Path("indexnow_state.json")
BATCH_SIZE = 10_000   # IndexNow hard max per request

# Safety valves (rewritten 19 Oct 2026).
# Old rule: if >10% of the URLs vanished, skip removal notices AND freeze the
# state. A legitimate big removal (7 Oct 2026: es/zh species copies dropped,
# 18 Oct: .html -> clean URLs) tripped it, the state never advanced again and
# EVERY build resubmitted the whole sitemap (~19k URLs x ~95 builds/day =
# ~1.8M submissions/day, visible in Bing Webmaster Tools > IndexNow).
# New rules:
#  - The baseline for URLs that ARE in the sitemap always advances after a
#    successful submission, so an unchanged URL is never resubmitted.
#  - A URL that disappears is remembered (missing_since) and only reported as
#    removed once it has stayed out of the sitemap for REMOVAL_GRACE_H hours.
#    A single bad/truncated build is repaired 15 minutes later, long before.
#    No size-ratio valve any more: a stuck ratio check is exactly what froze
#    the state; the grace window covers a truncated sitemap on its own.
REMOVAL_GRACE_H = 24


def load_sitemap(sitemap_path: str) -> dict[str, str]:
    """Return {url: lastmod}. lastmod may be '' if the sitemap omits it.
    Since 19 Oct 2026 sitemap.xml is a sitemap index whose parts live in
    sitemaps/*.xml on disk; those are read from the local build output."""
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    try:
        tree = ET.parse(sitemap_path)
    except (FileNotFoundError, ET.ParseError) as exc:
        print(f"[IndexNow] Could not parse {sitemap_path}: {exc}", file=sys.stderr)
        return {}
    root = tree.getroot()
    out: dict[str, str] = {}
    if root.tag.endswith("sitemapindex"):
        for sm in root.findall("sm:sitemap", ns):
            loc = sm.find("sm:loc", ns)
            if loc is None or not loc.text or not loc.text.strip().startswith(SITE_URL + "/"):
                continue
            part = loc.text.strip()[len(SITE_URL) + 1:]
            got = load_sitemap(part)
            if not got:
                # an unreadable part would look like thousands of removed URLs
                print(f"[IndexNow] Sitemap part {part} unreadable or empty — skipping this run.",
                      file=sys.stderr)
                return {}
            out.update(got)
        return out
    for url in tree.findall(".//sm:url", ns):
        loc = url.find("sm:loc", ns)
        if loc is None or not loc.text:
            continue
        lm = url.find("sm:lastmod", ns)
        out[loc.text.strip()] = (lm.text.strip() if lm is not None and lm.text else "")
    return out


def load_state() -> tuple[dict[str, str], dict[str, str]]:
    """Return (urls {url: lastmod}, missing_since {url: ISO time}).
    Reads both the v2 format and the old flat {url: lastmod} file."""
    if not STATE.exists():
        return {}, {}
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[IndexNow] State unreadable ({exc}) — treating as first run.", file=sys.stderr)
        return {}, {}
    if not isinstance(data, dict):
        return {}, {}
    if data.get("v") == 2 and isinstance(data.get("urls"), dict):
        ms = data.get("missing_since")
        return data["urls"], (ms if isinstance(ms, dict) else {})
    return data, {}     # old flat format


def save_state(urls: dict[str, str], missing_since: dict[str, str]) -> None:
    try:
        STATE.write_text(
            json.dumps({"v": 2, "urls": urls, "missing_since": missing_since},
                       ensure_ascii=False, indent=0, sort_keys=True),
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


def main(now: datetime | None = None) -> None:
    now = now or datetime.now(timezone.utc)
    current = load_sitemap(SITEMAP)
    if not current:
        print("[IndexNow] No URLs found — skipping.", file=sys.stderr)
        return
    print(f"[IndexNow] Sitemap holds {len(current)} URLs")

    previous, missing_since = load_state()

    # First run: seed state without submitting. IndexNow is for changes made
    # *after* setup; the sitemap's lastmod values cover the historical backlog.
    if not previous:
        save_state(dict(current), {})
        print(f"[IndexNow] First run — seeded state with {len(current)} URLs, nothing submitted.")
        return

    changed = sorted(u for u, lm in current.items() if previous.get(u) != lm)

    # URLs missing from this sitemap: start (or keep) their clock.
    new_missing = {}
    for u in set(previous) | set(missing_since):
        if u in current:
            continue                      # back in the sitemap: forget the clock
        new_missing[u] = missing_since.get(u) or now.isoformat(timespec="seconds")

    def _age_h(ts: str) -> float:
        try:
            return (now - datetime.fromisoformat(ts)).total_seconds() / 3600
        except Exception:
            return 0.0

    removed = sorted(u for u, ts in new_missing.items() if _age_h(ts) >= REMOVAL_GRACE_H)
    waiting = len(new_missing) - len(removed)
    if waiting:
        print(f"[IndexNow] {waiting} URLs missing for < {REMOVAL_GRACE_H} h — "
              "not reported yet (could be a bad build).")

    # Next state: every URL in the sitemap with its lastmod; URLs still inside
    # the grace window keep their old entry so a quick return is not "changed".
    next_urls = dict(current)
    for u in new_missing:
        if u not in removed and u in previous:
            next_urls[u] = previous[u]
    next_missing = {u: ts for u, ts in new_missing.items() if u not in removed}

    to_submit = changed + removed
    if not to_submit:
        if next_missing != missing_since or next_urls != previous:
            save_state(next_urls, next_missing)
        print("[IndexNow] Nothing changed since last run — no submission.")
        return

    print(f"[IndexNow] {len(changed)} changed, {len(removed)} removed -> submitting {len(to_submit)}")
    for u in to_submit[:10]:
        print(f"[IndexNow]   {u}")
    if len(to_submit) > 10:
        print(f"[IndexNow]   ... and {len(to_submit) - 10} more")

    if submit(to_submit):
        save_state(next_urls, next_missing)
        print("[IndexNow] State updated.")
    else:
        print("[IndexNow] Submission incomplete — state NOT updated, will retry next run.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
