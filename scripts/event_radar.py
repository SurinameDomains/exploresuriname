#!/usr/bin/env python3
"""Event radar — weekly scan for upcoming one-off events in Suriname.

Two sources, headlines only (no scraping, no content republishing):
  1. Google News RSS, English + Dutch editions, Suriname-scoped queries.
  2. Direct RSS feeds of Surinamese outlets (Waterkant, Suriname Herald,
     DBSuriname, Starnieuws) — these cover local event announcements that
     Google's English edition misses.

Headlines matching event vocabulary land in a GitHub issue for HUMAN triage:
verify dates on the organizer's official site, then add a kind "oneoff" entry
to events.json. Nothing is ever published automatically. Some noise (foreign
stories syndicated by local outlets) is expected and intentional; ticking a
checkbox is cheaper than a missed event.

Runs from .github/workflows/event_radar.yml (weekly + manual dispatch).
"""
import json
import os
import sys
import urllib.parse
import urllib.request

try:
    import feedparser
except ImportError:
    sys.exit("feedparser missing — pip install feedparser")

GNEWS_QUERIES = [
    # (query, hl, gl, ceid)
    ('Suriname (summit OR festival OR conference OR expo OR fair OR concert) when:14d',
     "en-US", "US", "US:en"),
    ('Suriname (congres OR beurs OR festival OR evenement OR kermis OR concert OR editie) when:14d',
     "nl", "NL", "NL:nl"),
]
OUTLET_FEEDS = [
    "https://www.waterkant.net/feed/",
    "https://www.srherald.com/feed/",
    "https://www.dbsuriname.com/feed/",
    "https://www.starnieuws.com/rss/starnieuws.rss",
]
# Event vocabulary, EN + NL. A headline must contain at least one.
KEYWORDS = (
    "summit", "festival", "conference", "conferentie", "expo", "fair", "beurs",
    "congres", "evenement", "kermis", "editie", "edition", "tickets", "concert",
    "marathon", "carifesta", "seogs", "vierdaagse", "jazz", "tentoonstelling",
    "viering", "festiviteit", "optocht", "parade",
)
# Suriname relevance for Google News results (outlet feeds are SR by origin)
SR_TERMS = ("suriname", "surinaams", "paramaribo", "staatsolie", "seogs",
            "nickerie", "commewijne", "lelydorp")
SR_OUTLETS = ("times of suriname", "starnieuws", "de ware tijd", "dagblad suriname",
              "waterkant", "suriname herald", "gfc nieuws", "apintie", "dbsuriname",
              "culturu", "united news")
UA = {"User-Agent": "Mozilla/5.0 (ExploreSuriname event radar; +https://exploresuriname.com)"}


def _grab(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        return feedparser.parse(urllib.request.urlopen(req, timeout=30).read()).entries
    except Exception as e:
        print("feed error:", url[:60], "->", e)
        return []


def fetch_candidates():
    seen, out = set(), []

    def consider(title, link, published, sr_known):
        base, _, source = title.rpartition(" - ")
        if not base:
            base, source = title, ""
        low = base.lower()
        if not any(k in low for k in KEYWORDS):
            return
        if not (sr_known
                or any(t in low for t in SR_TERMS)
                or any(s in source.lower() for s in SR_OUTLETS)):
            return
        key = low.strip()
        if key in seen:
            return
        seen.add(key)
        out.append({"title": title.strip(), "link": link, "published": published})

    for q, hl, gl, ceid in GNEWS_QUERIES:
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
               + f"&hl={hl}&gl={gl}&ceid={ceid}")
        for e in _grab(url)[:25]:
            consider(e.get("title", ""), e.get("link", ""), e.get("published", ""),
                     sr_known=False)

    for feed_url in OUTLET_FEEDS:
        for e in _grab(feed_url)[:20]:
            consider(e.get("title", ""), e.get("link", ""), e.get("published", ""),
                     sr_known=True)

    return out[:15]


def open_issue(items):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not (repo and token):
        sys.exit("GITHUB_REPOSITORY / GITHUB_TOKEN not set")
    lines = ["Possible upcoming one-off events spotted in news headlines. "
             "Verify dates on the organizer's **official site**, then add a "
             "`kind: \"oneoff\"` entry to `events.json` (it auto-expires after "
             "the end date). Foreign stories syndicated by local outlets are "
             "expected noise; just tick and ignore. Close when triaged.\n"]
    for it in items:
        lines.append(f"- [ ] [{it['title']}]({it['link']}) — {it['published']}")
    body = "\n".join(lines)
    data = json.dumps({"title": f"Event radar: {len(items)} candidate(s)",
                       "body": body, "labels": ["event-radar"]}).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues", data=data,
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/vnd.github+json",
                 "User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r:
        print("issue created:", json.load(r).get("html_url"))


if __name__ == "__main__":
    cands = fetch_candidates()
    print(f"{len(cands)} candidate(s)")
    for c in cands:
        print(" -", c["title"][:110])
    if cands and os.environ.get("GITHUB_TOKEN"):
        open_issue(cands)
