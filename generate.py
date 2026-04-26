#!/usr/bin/env python3
"""
ExploreSuriname.com – Automated News Aggregator
Fetches Surinamese news RSS feeds and generates a fresh static index.html.
Run daily via GitHub Actions.
"""

import feedparser
import html as html_lib
import re
import os
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────────────────────────

SITE_NAME    = "ExploreSuriname"
SITE_TAGLINE = "Your daily window into Suriname"
SITE_URL     = "https://exploresuriname.com"

# Add / remove sources here. color = badge background in the card.
FEEDS = [
    {"name": "De Ware Tijd",  "url": "https://www.dwtonline.com/feed/",          "color": "#007B3E"},
    {"name": "Starnieuws",    "url": "https://www.starnieuws.com/feed/",         "color": "#B40A2D"},
    {"name": "Waterkant",     "url": "https://www.waterkant.net/feed/",          "color": "#1a56db"},
    {"name": "SurinameTimes", "url": "https://surinametimes.net/feed/",          "color": "#7e3af2"},
    {"name": "ABC Suriname",  "url": "https://www.abcsur.com/feed/",             "color": "#e3a008"},
]

MAX_PER_FEED = 10   # articles to pull per source

# ── Google AdSense ─────────────────────────────────────────────────────────────
# After AdSense approval, replace these with your real values and uncomment
# the <ins> blocks in build_html() below.
ADSENSE_CLIENT   = "ca-pub-XXXXXXXXXXXXXXXXX"
ADSENSE_SLOT_TOP = "1111111111"
ADSENSE_SLOT_MID = "2222222222"

# ── Helpers ────────────────────────────────────────────────────────────────────

def strip_tags(text: str) -> str:
    if not text:
        return ""
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text)).strip()

def get_image(entry) -> str:
    """Try several feed fields to extract an image URL."""
    for attr in ("media_thumbnail", "media_content"):
        val = getattr(entry, attr, None)
        if val and isinstance(val, list):
            url = val[0].get("url", "")
            if url:
                return url
    if hasattr(entry, "enclosures"):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("url", "")
    for attr in ("summary", "content"):
        raw = ""
        if attr == "summary":
            raw = getattr(entry, "summary", "") or ""
        else:
            content_list = getattr(entry, "content", [])
            if content_list:
                raw = content_list[0].get("value", "") or ""
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
        if m:
            return m.group(1)
    return ""

def parse_date(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.fromtimestamp(0, tz=timezone.utc)

def time_ago(dt: datetime) -> str:
    secs = int((datetime.now(timezone.utc) - dt).total_seconds())
    if secs < 60:     return "just now"
    if secs < 3600:   return f"{secs // 60}m ago"
    if secs < 86400:  return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"

# ── Fetch ──────────────────────────────────────────────────────────────────────

def fetch_all() -> list:
    articles = []
    for src in FEEDS:
        try:
            feed = feedparser.parse(src["url"])
            count = 0
            for entry in feed.entries[:MAX_PER_FEED]:
                title   = strip_tags(getattr(entry, "title", "")).strip()
                link    = getattr(entry, "link", "#")
                summary = strip_tags(getattr(entry, "summary", ""))
                if len(summary) > 200:
                    summary = summary[:197] + "…"
                pub = parse_date(entry)
                articles.append({
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                    "image":   get_image(entry),
                    "date":    pub,
                    "ago":     time_ago(pub),
                    "source":  src["name"],
                    "color":   src["color"],
                })
                count += 1
            print(f"  OK  {src['name']}: {count} articles")
        except Exception as exc:
            print(f"  ERR {src['name']}: {exc}")
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

# ── Render helpers ─────────────────────────────────────────────────────────────

def card_html(a: dict, large: bool = False) -> str:
    img_tag = ""
    if a["image"]:
        h = "h-48" if large else "h-36"
        img_tag = (
            f'<img src="{a["image"]}" alt="" '
            f'class="w-full {h} object-cover" loading="lazy" '
            f'onerror="this.style.display=\'none\'">'
        )
    badge = (
        f'<span class="inline-block text-white text-xs font-semibold px-2 py-0.5 rounded-full" '
        f'style="background:{a["color"]}">{a["source"]}</span>'
    )
    title_cls = "text-base font-bold" if large else "text-sm font-semibold"
    return (
        f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer"\n'
        f'   class="group flex flex-col bg-white rounded-xl border border-gray-100 '
        f'shadow-sm hover:shadow-md transition-shadow overflow-hidden">\n'
        f'  {img_tag}\n'
        f'  <div class="p-4 flex flex-col gap-1 flex-1">\n'
        f'    <div class="flex items-center gap-2 flex-wrap">{badge}'
        f'<span class="text-gray-400 text-xs">{a["ago"]}</span></div>\n'
        f'    <h3 class="{title_cls} text-gray-900 group-hover:text-green-700 leading-snug">'
        f'{html_lib.escape(a["title"])}</h3>\n'
        f'    <p class="text-gray-500 text-xs leading-relaxed">'
        f'{html_lib.escape(a["summary"])}</p>\n'
        f'  </div>\n'
        f'</a>'
    )

def ad_placeholder(label: str) -> str:
    return (
        f'<div class="flex items-center justify-center bg-gray-50 border border-dashed '
        f'border-gray-300 rounded-xl text-gray-400 text-sm py-6 my-4">'
        f'&#128226; {label}</div>'
    )

# ── Build HTML ─────────────────────────────────────────────────────────────────

def build_html(articles: list) -> str:
    year    = datetime.now().year
    updated = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    total   = len(articles)
    sources = len(FEEDS)

    featured  = articles[:3]
    rest      = articles[3:28]

    feat_cards = "\n".join(card_html(a, large=True) for a in featured)
    rest_cards = "\n".join(card_html(a) for a in rest)

    top_ad = ad_placeholder("Top Banner Ad &mdash; Replace with Google AdSense code")
    mid_ad = ad_placeholder("Mid-Page Ad &mdash; Replace with Google AdSense code")

    # Uncomment below and remove ad_placeholder lines above once AdSense is approved:
    # top_ad = f"""<ins class="adsbygoogle" style="display:block"
    #   data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_TOP}"
    #   data-ad-format="auto" data-full-width-responsive="true"></ins>
    #   <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>"""
    # mid_ad = f"""<ins class="adsbygoogle" style="display:block"
    #   data-ad-client="{ADSENSE_CLIENT}" data-ad-slot="{ADSENSE_SLOT_MID}"
    #   data-ad-format="auto" data-full-width-responsive="true"></ins>
    #   <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Explore Suriname &ndash; Latest News</title>
  <meta name="description" content="Daily Suriname news aggregated from De Ware Tijd, Starnieuws, Waterkant and more. Updated automatically every day.">
  <meta property="og:title" content="Explore Suriname &ndash; Latest News">
  <meta property="og:description" content="Your daily window into Suriname.">
  <meta property="og:url" content="{SITE_URL}">
  <meta property="og:type" content="website">
  <link rel="canonical" href="{SITE_URL}/">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background: #f1f5f9; }}
    .flag-bar {{ height: 6px; background: linear-gradient(90deg, #007B3E 33.3%, #ECC81A 33.3%, #ECC81A 66.6%, #B40A2D 66.6%); }}
  </style>
</head>
<body>

<div class="flag-bar"></div>

<!-- HEADER -->
<header class="bg-white shadow-sm sticky top-0 z-10">
  <div class="max-w-5xl mx-auto px-4 py-3 flex justify-between items-center">
    <div>
      <a href="/" class="no-underline">
        <span class="text-2xl font-extrabold text-green-700">Explore</span><span class="text-2xl font-extrabold text-red-700">Suriname</span><span class="text-2xl font-extrabold text-gray-700">.com</span>
      </a>
      <p class="text-xs text-gray-400 mt-0.5 hidden sm:block">{SITE_TAGLINE}</p>
    </div>
    <div class="text-right text-xs text-gray-400 leading-relaxed">
      <div>&#128336; {updated}</div>
      <div>{total} stories &middot; {sources} sources</div>
    </div>
  </div>
</header>

<!-- TOP AD -->
<div class="max-w-5xl mx-auto px-4 mt-4">
  {top_ad}
</div>

<!-- MAIN CONTENT -->
<main class="max-w-5xl mx-auto px-4 pb-16">

  <h2 class="text-xs font-bold uppercase tracking-widest text-green-700 mb-3 mt-2">
    &#128293; Top Stories
  </h2>
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
    {feat_cards}
  </div>

  {mid_ad}

  <h2 class="text-xs font-bold uppercase tracking-widest text-red-700 mb-3 mt-6">
    &#128240; Latest News
  </h2>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
    {rest_cards}
  </div>

</main>

<!-- FOOTER -->
<footer class="bg-white border-t border-gray-200 py-8 text-center text-xs text-gray-400">
  <p class="font-semibold text-gray-500 mb-1">ExploreSuriname.com</p>
  <p>Auto-updated daily from public Surinamese news sources.</p>
  <p class="mt-1">De Ware Tijd &middot; Starnieuws &middot; Waterkant &middot; SurinameTimes &middot; ABC Suriname</p>
  <p class="mt-3">&copy; {year} ExploreSuriname.com</p>
</footer>

</body>
</html>"""

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Fetching Suriname news...")
    articles = fetch_all()
    print(f"Total: {len(articles)} articles")
    page = build_html(articles)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print("Generated index.html successfully.")
