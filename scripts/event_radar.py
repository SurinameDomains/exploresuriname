#!/usr/bin/env python3
"""Event radar — weekly scan for upcoming one-off events in Suriname.

Reads Google News RSS headlines (no scraping, no content republishing) for
event-style keywords, then opens a GitHub issue listing candidates so a human
can verify dates on the organizer's official site and add an entry to
events.json (kind "oneoff"). Nothing is ever published automatically.

Runs from .github/workflows/event_radar.yml (weekly). Requires GITHUB_TOKEN
with issues:write and GITHUB_REPOSITORY (both provided by Actions).
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

QUERIES = [
    # English + Dutch event vocabulary, last 14 days, Suriname-scoped
    'Suriname (summit OR festival OR conference OR expo OR "trade fair") when:14d',
    'Suriname (congres OR beurs OR festival OR evenement OR jubileum) when:14d',
]
KEYWORDS = (
    "summit", "festival", "conference", "expo", "fair", "congres", "beurs",
    "evenement", "editie", "edition", "tickets", "concert", "marathon", "carifesta",
)
UA = {"User-Agent": "Mozilla/5.0 (ExploreSuriname event radar; +https://exploresuriname.com)"}


def fetch_candidates():
    seen, out = set(), []
    for q in QUERIES:
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
               + "&hl=en-US&gl=US&ceid=US:en")
        try:
            req = urllib.request.Request(url, headers=UA)
            feed = feedparser.parse(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            print("feed error:", e)
            continue
        for entry in feed.entries[:25]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            # Google News appends " - Source name"; strip it so a Surinamese
            # outlet's name does not make foreign stories match "suriname"
            low = title.rsplit(" - ", 1)[0].lower()
            if "suriname" not in low and "paramaribo" not in low:
                continue
            if not any(k in low for k in KEYWORDS):
                continue
            key = title.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append({"title": title.strip(),
                        "link": link,
                        "published": entry.get("published", "")})
    return out


def open_issue(items):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not (repo and token):
        sys.exit("GITHUB_REPOSITORY / GITHUB_TOKEN not set")
    lines = ["Possible upcoming one-off events spotted in news headlines. "
             "Verify dates on the organizer's **official site**, then add a "
             "`kind: \"oneoff\"` entry to `events.json` (it auto-expires after "
             "the end date). Close this issue when triaged.\n"]
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
        print(" -", c["title"])
    if cands and os.environ.get("GITHUB_TOKEN"):
        open_issue(cands)
