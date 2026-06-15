#!/usr/bin/env python3
"""Event radar - weekly scan for upcoming one-off events in Suriname.

Headlines only (no scraping of article bodies, no content republishing).
Candidates land in a GitHub issue for HUMAN triage: verify dates on the
organizer's official site, then add a kind "oneoff" entry to events.json.
Nothing is ever published automatically.

Sources (all RSS):
  1. Google News RSS - a broad Dutch-edition events query (most Suriname
     event news is in Dutch), plus a tight English query for the
     international / business events (SEOGS-type) reported in English.
  2. Suriname news outlet feeds (general).
  3. Outlet *entertainment category* feeds - far higher event density than
     the main feeds (Suriname Herald and GFC Nieuws expose these).

Noise control:
  - Event-keyword gate (EN + NL) on every headline.
  - SR-relevance gate on Google News results.
  - Netherlands-diaspora filter (drops the "Keti Koti in Amsterdam" results
    the Dutch edition floods in unless the item is anchored to SR geography).
  - Cross-run de-duplication via data/event_radar_seen.json, so widening the
    net does not re-surface the same headline every week, and against events
    already listed in events.json.

Runs from .github/workflows/event_radar.yml (weekly + manual dispatch).
"""
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.exit("feedparser missing - pip install feedparser")

ROOT = Path(__file__).resolve().parents[1]
SEEN_PATH = ROOT / "data" / "event_radar_seen.json"
EVENTS_PATH = ROOT / "events.json"
SEEN_TTL_DAYS = 45        # forget a surfaced headline after this many days
RECENCY_DAYS = 28         # ignore feed items older than this (when dated)
PER_QUERY = 30
PER_FEED = 25
MAX_CANDIDATES = 30

# ---- Google News queries: (query, hl, gl, ceid) ---------------------------
GNEWS_QUERIES = [
    # Dutch edition: broad event vocabulary. Most SR event news is in Dutch.
    ('(Suriname OR Paramaribo) (festival OR concert OR optreden OR voorstelling '
     'OR expositie OR tentoonstelling OR beurs OR congres OR evenement OR kermis '
     'OR editie OR gala OR braderie OR songfestival OR toernooi OR marathon OR '
     'carnaval OR parade) when:30d', "nl", "NL", "NL:nl"),
    # English edition: keep tight - only the international / business events
    # actually reported in English. The broad EN festival query is all noise.
    ('Suriname (summit OR conference OR expo OR exhibition OR "oil and gas" '
     'OR investment OR forum) when:30d', "en-US", "US", "US:en"),
]

# ---- Outlet feeds ---------------------------------------------------------
# Entertainment / culture category feeds - already event-dense.
EVENT_FEEDS = [
    "https://www.srherald.com/category/entertainment/feed/",
    "https://www.gfcnieuws.com/category/entertainment/feed/",
]
# General news feeds - SR by origin, noisier; the keyword gate does the work.
NEWS_FEEDS = [
    "https://www.waterkant.net/feed/",
    "https://www.srherald.com/feed/",
    "https://www.dbsuriname.com/feed/",
    "https://www.starnieuws.com/rss/starnieuws.rss",
    "https://www.gfcnieuws.com/feed/",
    "https://unitednews.sr/feed/",
    "https://www.dwtonline.com/feed/",
    "https://socialsuriname.com/feed/",
]

# ---- Event vocabulary (EN + NL). A headline must contain at least one. -----
KEYWORDS = (
    "festival", "festiviteit", "viering", "concert", "optreden", "voorstelling",
    "toneel", "muziektheater", "expositie", "tentoonstelling", "exhibition",
    "beurs", "braderie", "kermis", "congres", "conferentie", "conference",
    "summit", "symposium", "seminar", "workshop", "lezing", "gala", "benefiet",
    "regatta", "parade", "optocht", "carnaval", "songfestival", "dansfestival",
    "filmfestival", "premiere", "editie", "edition", "tickets", "kaarten",
    "evenement", "jazz", "soca", "kawina", "carifesta", "suripop", "vierdaagse",
)
# Keywords needing a word boundary (avoid "export"->expo, "begrotingsmarathon").
KEYWORD_RX = (re.compile(r"expo\b"), re.compile(r"\bmarathon"))

# ---- Relevance / geography ------------------------------------------------
SR_TERMS = ("suriname", "surinaams", "paramaribo", "staatsolie", "seogs",
            "nickerie", "commewijne", "wanica", "lelydorp", "marowijne",
            "albina", "moengo", "saramacca", "brokopondo", "coronie")
# Strong SR geography - enough to keep an otherwise NL-looking item.
SR_PLACES = ("paramaribo", "nickerie", "commewijne", "wanica", "lelydorp",
             "marowijne", "albina", "moengo", "saramacca", "brokopondo",
             "coronie", "in suriname", "heel suriname")
SR_OUTLETS = ("times of suriname", "starnieuws", "de ware tijd", "dagblad suriname",
              "waterkant", "suriname herald", "gfc nieuws", "gfcnieuws", "apintie",
              "dbsuriname", "dwt", "united news", "unitednews", "social suriname",
              "culturu")
# Netherlands tokens - diaspora events the NL edition floods in.
NL_TOKENS = ("amsterdam", "rotterdam", "den haag", "the hague", "utrecht",
             "eindhoven", "nijmegen", "zoetermeer", "rijswijk", "almere",
             "tilburg", "groningen", "breda", "haarlem", "arnhem", "delft",
             "nederland", "holland", "belgie", "antwerpen")
NL_OUTLETS = ("rtv utrecht", "ad.nl", "pzc", "hbvl", "into nijmegen",
              "rijswijks dagblad", "zoetermeer actief", "doorbraak", "nh nieuws",
              "at5", "omroep", "indebuurt", "dichtbij")

# Common words that are not distinctive enough to flag an events.json duplicate.
STOP = {"festival", "weekend", "easter", "christmas", "independence", "indigenous",
        "maroons", "chinese", "javanese", "emancipation", "national", "suriname",
        "surinaamse", "paramaribo", "festiviteit", "viering", "feest"}

UA = {"User-Agent": "Mozilla/5.0 (ExploreSuriname event radar; +https://exploresuriname.com)"}


def _grab(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        return feedparser.parse(urllib.request.urlopen(req, timeout=30).read()).entries
    except Exception as e:
        print("feed error:", url[:70], "->", e)
        return []


def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _key(title, link):
    """Stable de-dup key: normalized URL (host+path), else normalized title."""
    if link:
        p = urllib.parse.urlsplit(link)
        return (p.netloc + p.path).rstrip("/").lower()
    return _norm(title)


def _recent(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return True  # undated -> let it through
    age = (dt.datetime.now(dt.timezone.utc)
           - dt.datetime(*t[:6], tzinfo=dt.timezone.utc)).days
    return age <= RECENCY_DAYS


def _is_nl_diaspora(low, src_low):
    nl = any(t in low for t in NL_TOKENS) or any(o in src_low for o in NL_OUTLETS)
    if not nl:
        return False
    # Keep only if anchored to real SR geography (not just "Surinaams").
    return not any(p in low for p in SR_PLACES)


def _existing_signatures():
    """Distinctive token-sets from events.json names, to suppress re-surfacing
    events already on the site (e.g. SEOGS, Avond Vierdaagse)."""
    sigs = []
    try:
        data = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return sigs
    for ev in data.get("events", []):
        toks = {w for w in re.findall(r"[a-z]{4,}", _norm(ev.get("name", "")))
                if w not in STOP}
        if toks:
            sigs.append(toks)
    return sigs


def _matches_existing(low, sigs):
    toks = set(re.findall(r"[a-z]{4,}", low))
    # Conservative: only suppress on 2+ shared distinctive tokens.
    return any(len(sig & toks) >= 2 for sig in sigs)


def load_seen():
    try:
        raw = json.loads(SEEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cutoff = (dt.date.today() - dt.timedelta(days=SEEN_TTL_DAYS)).isoformat()
    return {k: v for k, v in raw.items() if v >= cutoff}


def save_seen(seen_state, surfaced_keys):
    today = dt.date.today().isoformat()
    for k in surfaced_keys:
        seen_state.setdefault(k, today)
    SEEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_PATH.write_text(
        json.dumps(seen_state, indent=0, sort_keys=True, ensure_ascii=False),
        encoding="utf-8")


def fetch_candidates():
    seen_state = load_seen()
    sigs = _existing_signatures()
    out, keys, surfaced = [], set(), []

    def consider(title, link, published, *, gnews):
        if gnews:
            base, _, source = title.rpartition(" - ")
            if not base:
                base, source = title, ""
        else:
            base, source = title, ""        # outlet titles have no " - source"
        low, src_low = base.lower(), source.lower()
        if not (any(k in low for k in KEYWORDS)
                or any(rx.search(low) for rx in KEYWORD_RX)):
            return
        if gnews and not (any(t in low for t in SR_TERMS)
                          or any(s in src_low for s in SR_OUTLETS)):
            return
        if _is_nl_diaspora(low, src_low):
            return
        if _matches_existing(low, sigs):
            return
        k = _key(base, link)
        if k in keys:
            return
        keys.add(k)
        if k in seen_state:                  # surfaced in an earlier run
            return
        surfaced.append(k)
        out.append({"title": title.strip(), "link": link,
                    "published": published, "source": source})

    for q, hl, gl, ceid in GNEWS_QUERIES:
        url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
               + f"&hl={hl}&gl={gl}&ceid={ceid}")
        for e in _grab(url)[:PER_QUERY]:
            if _recent(e):
                consider(e.get("title", ""), e.get("link", ""),
                         e.get("published", ""), gnews=True)

    for feed in EVENT_FEEDS + NEWS_FEEDS:
        for e in _grab(feed)[:PER_FEED]:
            if _recent(e):
                consider(e.get("title", ""), e.get("link", ""),
                         e.get("published", ""), gnews=False)

    return out[:MAX_CANDIDATES], seen_state, surfaced


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
        src = f" `{it['source']}`" if it.get("source") else ""
        lines.append(f"- [ ] [{it['title']}]({it['link']}){src} - {it['published']}")
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
    cands, seen_state, surfaced = fetch_candidates()
    print(f"{len(cands)} new candidate(s)")
    for c in cands:
        print("  -", c["title"][:110], "  [", c.get("source") or "feed", "]")
    save_seen(seen_state, surfaced)          # remember what we surfaced
    if cands and os.environ.get("GITHUB_TOKEN"):
        open_issue(cands)
    elif not cands:
        print("nothing new - no issue opened")
