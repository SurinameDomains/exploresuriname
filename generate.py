#!/usr/bin/env python3
"""
ExploreSuriname.com – Full Tourism & News Site Generator
Generates:
  - index.html  : Beautiful tourism homepage (no ads)
  - news.html   : Auto-updated news aggregator (with ad slots)
Run daily via GitHub Actions.
"""

import feedparser
import html as html_lib
import re, os, json
import urllib.request, urllib.parse
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────────────────────────

SITE_URL = "https://exploresuriname.com"
YEAR     = datetime.now().year

FEEDS = [
    {"name": "De Ware Tijd",  "url": "https://www.dwtonline.com/feed/",  "color": "#2D6A4F"},
    {"name": "Starnieuws",    "url": "https://www.starnieuws.com/feed/", "color": "#B40A2D"},
    {"name": "Waterkant",     "url": "https://www.waterkant.net/feed/",  "color": "#1a56db"},
    {"name": "SurinameTimes", "url": "https://surinametimes.net/feed/",  "color": "#7e3af2"},
    {"name": "ABC Suriname",  "url": "https://www.abcsur.com/feed/",     "color": "#e3a008"},
]
MAX_PER_FEED = 10

# ── Static content ─────────────────────────────────────────────────────────────

NATURE_SPOTS = [
    {
        "name": "Central Suriname Nature Reserve",
        "badge": "UNESCO World Heritage",
        "desc": "One of the world's largest intact tropical rainforests — 1.6 million pristine hectares where time stands still. Home to jaguars, tapirs, giant river otters and thousands of plant species found nowhere else.",
        "tags": ["UNESCO", "Rainforest", "Wildlife"],
        "image": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
        "fact": "Larger than some entire countries",
    },
    {
        "name": "Brownsberg Nature Park",
        "badge": "Best Day Trip",
        "desc": "Perched 500m above the Brokopondo Reservoir, Brownsberg rewards visitors with panoramic jungle views, cascading waterfalls and abundant wildlife just 2 hours from Paramaribo.",
        "tags": ["Hiking", "Waterfall", "Views"],
        "image": "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800&q=80",
        "fact": "Howler monkeys, toucans & jaguars",
    },
    {
        "name": "Galibi Nature Reserve",
        "badge": "Turtle Nesting",
        "desc": "On Suriname's Atlantic coast, giant leatherback sea turtles — the world's largest reptile — haul ashore to nest on these remote beaches in one of nature's most extraordinary spectacles.",
        "tags": ["Sea Turtles", "Coastal", "Wildlife"],
        "image": "https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=800&q=80",
        "fact": "Nesting season: February – July",
    },
    {
        "name": "Peperpot Nature Park",
        "badge": "Bird Watcher's Paradise",
        "desc": "A former plantation turned bird sanctuary minutes from the capital. Over 200 bird species have been recorded here — the perfect introduction to Suriname's extraordinary avian diversity.",
        "tags": ["Birding", "Easy Access", "Peaceful"],
        "image": "https://images.unsplash.com/photo-1444464666168-49d633b86797?w=800&q=80",
        "fact": "700+ bird species in Suriname",
    },
    {
        "name": "Voltzberg & Raleighvallen",
        "badge": "Remote Expedition",
        "desc": "An iconic granite inselberg rising majestically above the endless jungle canopy. The Voltzberg demands a multi-day expedition, rewarding only the most adventurous with its summit views.",
        "tags": ["Expedition", "Climbing", "Remote"],
        "image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
        "fact": "Multi-day jungle trek required",
    },
    {
        "name": "Paramaribo Historic Inner City",
        "badge": "UNESCO World Heritage",
        "desc": "The only wooden colonial city in the Americas. Paramaribo's 18th-century Dutch colonial architecture — remarkably well-preserved — sits alongside Hindu temples, mosques and synagogues in harmony.",
        "tags": ["UNESCO", "History", "Culture"],
        "image": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800&q=80",
        "fact": "2 UNESCO sites in one country",
    },
]

ACTIVITIES = [
    {"icon": "🌿", "name": "Jungle Trekking",       "desc": "Multi-day guided expeditions through primary rainforest with expert local guides."},
    {"icon": "🛶", "name": "River Canoe Tours",      "desc": "Glide through the Amazon basin on traditional dugout canoes past river dolphins."},
    {"icon": "🦜", "name": "Bird Watching",          "desc": "Spot scarlet macaws, harpy eagles and 700+ species in their natural habitat."},
    {"icon": "🏘️", "name": "Village Tours",          "desc": "Visit Indigenous and Maroon communities preserving centuries-old traditions."},
    {"icon": "🏙️", "name": "Paramaribo City Walk",   "desc": "Explore the UNESCO historic inner city — the only wooden colonial city in the Americas."},
    {"icon": "🏊", "name": "Natural Swimming Holes",  "desc": "Take a dip in crystal-clear jungle rivers and natural rock pools."},
    {"icon": "🎨", "name": "Maroon Art & Craft",     "desc": "Discover world-renowned woodcarving and textile artistry of the Maroon people."},
    {"icon": "🐢", "name": "Turtle Watching",        "desc": "Witness giant leatherback sea turtles nesting on Suriname's Atlantic coast."},
]

FALLBACK_RESTAURANTS = [
    {"name": "De Gadri",              "cuisine": "Surinamese",        "area": "Paramaribo",  "desc": "Traditional Surinamese cuisine in a charming colonial garden setting."},
    {"name": "Restaurant Spice Quest","cuisine": "Indian-Surinamese", "area": "Paramaribo",  "desc": "A rich fusion of Hindustani spice with modern, elegant presentation."},
    {"name": "Zus & Zo",              "cuisine": "Café & Bakery",     "area": "Paramaribo",  "desc": "Beloved café with fresh pastries, open sandwiches and local coffee."},
    {"name": "Warung Mini",           "cuisine": "Javanese",          "area": "Paramaribo",  "desc": "Authentic Javanese-Surinamese dishes in a relaxed warung atmosphere."},
    {"name": "Bistro de Paris",       "cuisine": "French-Creole",     "area": "Waterfront",  "desc": "French-influenced creole cuisine on the historic Paramaribo waterfront."},
    {"name": "La Gondola",            "cuisine": "Italian",           "area": "Paramaribo",  "desc": "Wood-fired pizzas and homemade pasta with a tropical twist."},
]

FALLBACK_HOTELS = [
    {"name": "Torarica Hotel & Casino",  "category": "5-Star Luxury",  "area": "Paramaribo", "desc": "Suriname's premier hotel: riverside pool, casino and world-class dining."},
    {"name": "Courtyard by Marriott",    "category": "Business Hotel",  "area": "Paramaribo", "desc": "Modern international hotel perfectly placed in the heart of the capital."},
    {"name": "Eco Resort Inn",           "category": "Eco Lodge",       "area": "Paramaribo", "desc": "Sustainable resort surrounded by lush tropical gardens and birdsong."},
    {"name": "Awarradam Jungle Lodge",   "category": "Jungle Lodge",    "area": "Interior",   "desc": "Remote luxury deep in the rainforest — accessible by small plane and canoe."},
    {"name": "Danpaati River Lodge",     "category": "River Lodge",     "area": "Gran Rio",   "desc": "Traditional Maroon-style lodge on the banks of the wild Gran Rio river."},
    {"name": "Hotel Laminaire",          "category": "Boutique",        "area": "Paramaribo", "desc": "Intimate boutique hotel in a beautifully restored colonial mansion."},
]

# ── Helpers ────────────────────────────────────────────────────────────────────

def strip_tags(text):
    if not text: return ""
    return html_lib.unescape(re.sub(r"<[^>]+>", " ", text)).strip()

def get_image(entry):
    for attr in ("media_thumbnail", "media_content"):
        val = getattr(entry, attr, None)
        if val and isinstance(val, list):
            url = val[0].get("url", "")
            if url: return url
    if hasattr(entry, "enclosures"):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image"):
                return enc.get("url", "")
    raw = getattr(entry, "summary", "") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw)
    if m: return m.group(1)
    return ""

def parse_date(entry):
    for attr in ("published_parsed", "updated_parsed"):
        val = getattr(entry, attr, None)
        if val:
            try: return datetime(*val[:6], tzinfo=timezone.utc)
            except: pass
    return datetime.fromtimestamp(0, tz=timezone.utc)

def time_ago(dt):
    secs = int((datetime.now(timezone.utc) - dt).total_seconds())
    if secs < 60:    return "just now"
    if secs < 3600:  return f"{secs//60}m ago"
    if secs < 86400: return f"{secs//3600}h ago"
    return f"{secs//86400}d ago"

# ── Data fetching ──────────────────────────────────────────────────────────────

def fetch_overpass(query, limit=12):
    try:
        url  = "https://overpass-api.de/api/interpreter"
        data = urllib.parse.urlencode({"data": query}).encode()
        req  = urllib.request.Request(url, data=data, headers={"User-Agent": "ExploreSuriname/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            result = json.loads(r.read().decode())
        pois = []
        for el in result.get("elements", []):
            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("name:en", "")
            if not name or len(name) < 2: continue
            pois.append({
                "name":     name,
                "cuisine":  tags.get("cuisine", "").replace(";", " · ").title(),
                "category": tags.get("tourism", tags.get("amenity", "")).replace("_", " ").title(),
                "area":     tags.get("addr:city", tags.get("addr:suburb", "Paramaribo")),
                "desc":     tags.get("description", ""),
                "website":  tags.get("website", ""),
            })
            if len(pois) >= limit: break
        return pois
    except Exception as e:
        print(f"  Overpass error: {e}")
        return []

def merge_with_fallbacks(live, fallbacks, target=6):
    used = {r["name"].lower() for r in live}
    for fb in fallbacks:
        if len(live) >= target: break
        if fb["name"].lower() not in used:
            live.append(fb)
    return live[:target]

def fetch_articles():
    articles = []
    for src in FEEDS:
        try:
            feed  = feedparser.parse(src["url"])
            count = 0
            for entry in feed.entries[:MAX_PER_FEED]:
                title   = strip_tags(getattr(entry, "title", "")).strip()
                link    = getattr(entry, "link", "#")
                summary = strip_tags(getattr(entry, "summary", ""))
                if len(summary) > 200: summary = summary[:197] + "…"
                pub = parse_date(entry)
                articles.append({
                    "title": title, "link": link, "summary": summary,
                    "image": get_image(entry), "date": pub, "ago": time_ago(pub),
                    "source": src["name"], "color": src["color"],
                })
                count += 1
            print(f"  OK  {src['name']}: {count}")
        except Exception as e:
            print(f"  ERR {src['name']}: {e}")
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

# ── Shared HTML parts ──────────────────────────────────────────────────────────

PAGE_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    :root {
      --forest:   #1B4332;
      --forest2:  #2D6A4F;
      --leaf:     #52B788;
      --mint:     #D8F3DC;
      --coral:    #E76F51;
      --sand:     #FEFAE0;
    }
    body   { font-family: 'Inter', system-ui, sans-serif; }
    .serif { font-family: 'Playfair Display', Georgia, serif; }
    .hero-bg { background-size: cover; background-position: center; }
    @media (min-width: 768px) { .hero-bg { background-attachment: fixed; } }
    .card-hover { transition: transform .2s, box-shadow .2s; }
    .card-hover:hover { transform: translateY(-4px); box-shadow: 0 12px 32px rgba(0,0,0,.12); }
  </style>"""

def nav_html(active="home"):
    links = [
        ("index.html#nature",      "Nature"),
        ("index.html#activities",  "Activities"),
        ("index.html#dining",      "Eat & Drink"),
        ("index.html#hotels",      "Stay"),
        ("news.html",              "News"),
    ]
    link_html = ""
    for href, label in links:
        cls = "text-green-700 font-semibold" if label.lower() == active else "text-gray-700 hover:text-green-700"
        link_html += f'<a href="{href}" class="{cls} transition text-sm">{label}</a>\n'

    return f"""
<nav id="navbar" class="fixed top-0 w-full z-50 transition-all duration-300" style="background:rgba(255,255,255,0.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 12px rgba(0,0,0,.07)">
  <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
    <a href="index.html" class="flex items-baseline gap-0.5 no-underline">
      <span class="serif text-2xl font-bold" style="color:var(--forest)">Explore</span><span class="serif text-2xl font-bold" style="color:var(--coral)">Suriname</span>
    </a>
    <div class="hidden md:flex items-center gap-7">
      {link_html}
    </div>
    <a href="news.html" class="hidden md:inline-flex items-center gap-1 text-white text-sm font-medium px-4 py-2 rounded-full transition hover:opacity-90" style="background:var(--forest)">
      &#128240; Latest News
    </a>
    <!-- Mobile menu button -->
    <button onclick="document.getElementById('mobile-menu').classList.toggle('hidden')" class="md:hidden p-2 rounded-lg hover:bg-gray-100">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>
  </div>
  <!-- Mobile menu -->
  <div id="mobile-menu" class="hidden md:hidden border-t border-gray-100 bg-white px-5 py-4 flex flex-col gap-3 text-sm">
    {link_html}
  </div>
</nav>"""

def footer_html():
    return f"""
<footer style="background:var(--forest)" class="text-white py-16 mt-0">
  <div class="max-w-6xl mx-auto px-5">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-12 mb-10">
      <div>
        <p class="serif text-2xl font-bold mb-3">Explore<span style="color:var(--coral)">Suriname</span></p>
        <p class="text-white/60 text-sm leading-relaxed">Your guide to South America's most beautiful secret. Updated daily with fresh news, local insights and travel inspiration.</p>
      </div>
      <div>
        <p class="text-white/50 text-xs uppercase tracking-widest font-semibold mb-4">Explore</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li><a href="index.html#nature"      class="hover:text-white transition">Nature &amp; Parks</a></li>
          <li><a href="index.html#activities"  class="hover:text-white transition">Activities</a></li>
          <li><a href="index.html#dining"      class="hover:text-white transition">Eat &amp; Drink</a></li>
          <li><a href="index.html#hotels"      class="hover:text-white transition">Hotels &amp; Lodges</a></li>
          <li><a href="news.html"              class="hover:text-white transition">Suriname News</a></li>
        </ul>
      </div>
      <div>
        <p class="text-white/50 text-xs uppercase tracking-widest font-semibold mb-4">Travel Info</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li>&#127988; Capital: Paramaribo</li>
          <li>&#128172; Dutch, Sranan Tongo + 9 more</li>
          <li>&#128176; Surinamese Dollar (SRD)</li>
          <li>&#127774; Tropical, ~28°C year-round</li>
          <li>&#127942; 2 UNESCO World Heritage Sites</li>
        </ul>
      </div>
    </div>
    <div class="border-t border-white/10 pt-8 text-center text-white/40 text-xs">
      &copy; {YEAR} ExploreSuriname.com &mdash; Auto-updated daily &middot; Content from public sources
    </div>
  </div>
</footer>"""

def news_card_html(a, large=False):
    img = ""
    if a["image"]:
        h = "h-52" if large else "h-36"
        img = (f'<img src="{a["image"]}" alt="" loading="lazy" '
               f'class="w-full {h} object-cover" onerror="this.style.display=\'none\'">')
    badge = (f'<span class="text-white text-xs font-medium px-2 py-0.5 rounded-full" '
             f'style="background:{a["color"]}">{html_lib.escape(a["source"])}</span>')
    tc = "text-base font-bold" if large else "text-sm font-semibold"
    return (f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
            f'class="group flex flex-col bg-white rounded-2xl overflow-hidden card-hover border border-gray-100">'
            f'{img}'
            f'<div class="p-5 flex flex-col gap-2 flex-1">'
            f'<div class="flex items-center gap-2 flex-wrap">{badge}'
            f'<span class="text-gray-400 text-xs">{a["ago"]}</span></div>'
            f'<h3 class="{tc} text-gray-900 group-hover:text-green-800 leading-snug">{html_lib.escape(a["title"])}</h3>'
            f'<p class="text-gray-500 text-xs leading-relaxed flex-1">{html_lib.escape(a["summary"])}</p>'
            f'</div></a>')

def ad_slot(label):
    return (f'<div class="flex items-center justify-center bg-gray-50 border border-dashed '
            f'border-gray-300 rounded-xl text-gray-400 text-sm py-6 my-6">'
            f'&#128226; {html_lib.escape(label)}</div>')

# ── Index page ─────────────────────────────────────────────────────────────────

def build_index(restaurants, hotels, news_preview):
    # Nature cards
    nature_cards = ""
    for spot in NATURE_SPOTS:
        tags_html = "".join(
            f'<span class="text-xs px-2 py-0.5 rounded-full font-medium" style="background:var(--mint);color:var(--forest)">{t}</span>'
            for t in spot["tags"]
        )
        nature_cards += f"""
<div class="group rounded-2xl overflow-hidden card-hover bg-white border border-gray-100 shadow-sm flex flex-col">
  <div class="relative h-56 overflow-hidden">
    <img src="{spot['image']}" alt="{html_lib.escape(spot['name'])}" loading="lazy"
         class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
         onerror="this.parentElement.style.background='#2D6A4F'">
    <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/10 to-transparent"></div>
    <span class="absolute top-4 left-4 text-white text-xs font-semibold px-3 py-1 rounded-full" style="background:var(--coral)">{html_lib.escape(spot['badge'])}</span>
    <div class="absolute bottom-4 left-4 right-4">
      <h3 class="serif text-white font-bold text-lg leading-tight">{html_lib.escape(spot['name'])}</h3>
      <p class="text-white/75 text-xs mt-1">&#10024; {html_lib.escape(spot['fact'])}</p>
    </div>
  </div>
  <div class="p-5 flex flex-col gap-3 flex-1">
    <p class="text-gray-600 text-sm leading-relaxed flex-1">{html_lib.escape(spot['desc'])}</p>
    <div class="flex flex-wrap gap-1">{tags_html}</div>
  </div>
</div>"""

    # Activity cards
    activity_cards = ""
    for act in ACTIVITIES:
        activity_cards += f"""
<div class="flex flex-col items-center text-center p-6 rounded-2xl transition cursor-default" style="background:rgba(255,255,255,0.08)" onmouseover="this.style.background='rgba(255,255,255,0.15)'" onmouseout="this.style.background='rgba(255,255,255,0.08)'">
  <span class="text-4xl mb-3">{act['icon']}</span>
  <h4 class="serif text-white font-bold text-base mb-2">{html_lib.escape(act['name'])}</h4>
  <p class="text-white/65 text-sm leading-relaxed">{html_lib.escape(act['desc'])}</p>
</div>"""

    # Restaurant cards
    restaurant_cards = ""
    for r in restaurants:
        cuisine = r.get("cuisine") or r.get("category", "Restaurant")
        desc    = r.get("desc") or r.get("description") or "A great dining experience in Paramaribo."
        area    = r.get("area", "Paramaribo")
        restaurant_cards += f"""
<div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 card-hover flex flex-col gap-2">
  <div class="flex items-start justify-between gap-2">
    <h4 class="font-bold text-gray-900 text-base leading-tight">{html_lib.escape(r['name'])}</h4>
    <span class="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style="background:var(--mint);color:var(--forest)">{html_lib.escape(cuisine) if cuisine else 'Restaurant'}</span>
  </div>
  <p class="text-gray-500 text-sm leading-relaxed flex-1">{html_lib.escape(desc)}</p>
  <p class="text-gray-400 text-xs">&#128205; {html_lib.escape(area)}, Suriname</p>
</div>"""

    # Hotel cards
    hotel_cards = ""
    for h in hotels:
        category = h.get("category", "Hotel")
        desc     = h.get("desc") or h.get("description") or "Comfortable accommodation in Suriname."
        area     = h.get("area", "Suriname")
        hotel_cards += f"""
<div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 card-hover flex flex-col gap-2">
  <div class="flex items-start justify-between gap-2">
    <h4 class="font-bold text-gray-900 text-base leading-tight">{html_lib.escape(h['name'])}</h4>
    <span class="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style="background:#fff3e8;color:#c05621">{html_lib.escape(category)}</span>
  </div>
  <p class="text-gray-500 text-sm leading-relaxed flex-1">{html_lib.escape(desc)}</p>
  <p class="text-gray-400 text-xs">&#128205; {html_lib.escape(area)}, Suriname</p>
</div>"""

    # News preview cards
    news_cards = "\n".join(news_card_html(a, large=(i == 0)) for i, a in enumerate(news_preview))

    return f"""{PAGE_HEAD}
  <title>Explore Suriname &mdash; Discover South America&apos;s Best-Kept Secret</title>
  <meta name="description" content="Your guide to Suriname — pristine rainforests, vibrant culture, incredible wildlife. Discover nature, activities, restaurants and hotels.">
  <meta property="og:title" content="Explore Suriname — The Amazon's Best-Kept Secret">
  <meta property="og:url" content="{SITE_URL}/">
  <link rel="canonical" href="{SITE_URL}/">
</head>
<body class="bg-white overflow-x-hidden">

{nav_html("home")}

<!-- ═══ HERO ═══════════════════════════════════════════════════════════════ -->
<section class="relative min-h-screen flex items-center justify-center hero-bg"
  style="background-image:url('https://images.unsplash.com/photo-1448375240586-882707db888b?w=1920&q=80')">
  <div class="absolute inset-0" style="background:linear-gradient(to bottom, rgba(0,0,0,.15) 0%, rgba(0,0,0,.55) 60%, rgba(0,0,0,.82) 100%)"></div>
  <div class="relative z-10 text-center text-white px-5 max-w-4xl mx-auto" style="padding-top:5rem">
    <p class="text-xs font-semibold tracking-widest uppercase mb-6" style="color:var(--coral)">South America&apos;s Hidden Gem</p>
    <h1 class="serif font-black leading-tight mb-6" style="font-size:clamp(2.5rem,8vw,5.5rem)">
      The Amazon&apos;s<br>Best-Kept Secret
    </h1>
    <p class="text-xl font-light leading-relaxed mb-10 max-w-2xl mx-auto text-white/90">
      94% pristine rainforest. Unmatched biodiversity. Two UNESCO World Heritage Sites.<br class="hidden sm:block"> Welcome to Suriname.
    </p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <a href="#nature" class="px-8 py-4 rounded-full font-semibold text-lg text-white transition hover:opacity-90 shadow-lg" style="background:var(--forest)">
        Start Exploring &#8595;
      </a>
      <a href="news.html" class="px-8 py-4 rounded-full font-semibold text-lg text-white border-2 transition hover:bg-white/10" style="border-color:rgba(255,255,255,.6)">
        Latest News
      </a>
    </div>
  </div>
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-white/50 text-xs">
    <span>Scroll to explore</span>
    <svg class="w-4 h-4 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
    </svg>
  </div>
</section>

<!-- ═══ QUICK FACTS BAR ═══════════════════════════════════════════════════ -->
<section style="background:var(--forest)" class="text-white py-7">
  <div class="max-w-5xl mx-auto px-5 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Climate</p><p class="font-semibold">&#127774; Tropical, ~28°C</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Forest Cover</p><p class="font-semibold">&#127807; 94% Rainforest</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">UNESCO Sites</p><p class="font-semibold">&#127942; 2 World Heritage</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Bird Species</p><p class="font-semibold">&#128038; 700+ Species</p></div>
  </div>
</section>

<!-- ═══ NATURE ════════════════════════════════════════════════════════════ -->
<section id="nature" class="py-24 bg-gray-50">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Pristine Wilderness</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Nature Like Nowhere Else</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
        Suriname protects more of its original forest than any other country on earth. Here, wilderness still reigns.
      </p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {nature_cards}
    </div>
  </div>
</section>

<!-- ═══ ACTIVITIES ════════════════════════════════════════════════════════ -->
<section id="activities" class="py-24" style="background:var(--forest)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Adventures Await</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-white mb-4">Things to Do</h2>
      <p class="text-white/60 text-lg max-w-2xl mx-auto leading-relaxed">
        From deep jungle expeditions to cultural immersion — Suriname offers experiences you can&apos;t find anywhere else on earth.
      </p>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {activity_cards}
    </div>
  </div>
</section>

<!-- ═══ RESTAURANTS ═══════════════════════════════════════════════════════ -->
<section id="dining" class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Eat &amp; Drink</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Where to Eat</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
        Suriname&apos;s cuisine is as diverse as its people — a unique blend of Creole, Hindustani, Javanese, Chinese and Maroon flavors all on one plate.
      </p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {restaurant_cards}
    </div>
  </div>
</section>

<!-- ═══ HOTELS ════════════════════════════════════════════════════════════ -->
<section id="hotels" class="py-24" style="background:var(--mint)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Where to Stay</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Hotels &amp; Lodges</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
        From 5-star riverside hotels in Paramaribo to remote jungle lodges only reachable by canoe &mdash; every traveller finds their place in Suriname.
      </p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {hotel_cards}
    </div>
  </div>
</section>

<!-- ═══ NEWS PREVIEW ══════════════════════════════════════════════════════ -->
<section class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="flex items-end justify-between mb-10 flex-wrap gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest uppercase mb-2" style="color:var(--forest2)">Stay Informed</p>
        <h2 class="serif text-4xl font-bold text-gray-900">Latest from Suriname</h2>
      </div>
      <a href="news.html" class="hidden sm:inline-flex items-center gap-1 px-6 py-3 rounded-full text-white text-sm font-semibold transition hover:opacity-90" style="background:var(--forest)">
        All News &rarr;
      </a>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
      {news_cards}
    </div>
    <div class="text-center mt-8 sm:hidden">
      <a href="news.html" class="inline-flex items-center gap-1 px-6 py-3 rounded-full text-white text-sm font-semibold" style="background:var(--forest)">All Suriname News &rarr;</a>
    </div>
  </div>
</section>

{footer_html()}

</body>
</html>"""

# ── News page ──────────────────────────────────────────────────────────────────

def build_news(articles):
    updated  = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    total    = len(articles)
    featured = articles[:3]
    rest     = articles[3:30]
    feat_html = "\n".join(news_card_html(a, large=True) for a in featured)
    rest_html = "\n".join(news_card_html(a) for a in rest)

    return f"""{PAGE_HEAD}
  <title>Suriname News &mdash; ExploreSuriname.com</title>
  <meta name="description" content="Daily Suriname news from De Ware Tijd, Starnieuws, Waterkant and more. Auto-updated every day.">
  <link rel="canonical" href="{SITE_URL}/news.html">
</head>
<body class="bg-gray-50 overflow-x-hidden">

{nav_html("news")}

<div class="pt-16"></div>

<!-- NEWS HEADER -->
<div class="text-white text-center py-16" style="background:var(--forest)">
  <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Auto-updated daily</p>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname News</h1>
  <p class="text-white/55 text-sm">&#128336; {updated} &middot; {total} stories from {len(FEEDS)} sources</p>
</div>

<main class="max-w-5xl mx-auto px-5 py-10 pb-20">

  {ad_slot("Top Banner Ad — Replace with Google AdSense code")}

  <h2 class="text-xs font-bold uppercase tracking-widest mb-5" style="color:var(--forest2)">&#128293; Top Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">
    {feat_html}
  </div>

  {ad_slot("Mid-Page Ad — Replace with Google AdSense code")}

  <h2 class="text-xs font-bold uppercase tracking-widest mb-5 mt-6 text-gray-500">&#128240; All Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
    {rest_html}
  </div>

</main>

{footer_html()}

</body>
</html>"""

# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("ExploreSuriname.com — Site Generator")
    print("=" * 50)

    print("\n[1/4] Fetching news articles...")
    articles = fetch_articles()
    print(f"      Total: {len(articles)} articles")

    print("\n[2/4] Fetching restaurants (Overpass)...")
    RESTAURANT_Q = """
[out:json][timeout:20];
area["name"="Paramaribo"]["admin_level"="8"]->.a;
(node["amenity"="restaurant"](area.a);
 way["amenity"="restaurant"](area.a););
out center 12;
"""
    restaurants = fetch_overpass(RESTAURANT_Q, limit=12)
    restaurants = merge_with_fallbacks(restaurants, FALLBACK_RESTAURANTS, target=6)
    print(f"      Total: {len(restaurants)} restaurants")

    print("\n[3/4] Fetching hotels (Overpass)...")
    HOTEL_Q = """
[out:json][timeout:20];
area["name"="Suriname"]["admin_level"="2"]->.a;
(node["tourism"~"hotel|guest_house|hostel|motel"](area.a);
 way["tourism"~"hotel|guest_house|hostel|motel"](area.a););
out center 12;
"""
    hotels = fetch_overpass(HOTEL_Q, limit=12)
    hotels = merge_with_fallbacks(hotels, FALLBACK_HOTELS, target=6)
    print(f"      Total: {len(hotels)} hotels")

    print("\n[4/4] Building HTML pages...")
    news_preview = articles[:3]

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(build_index(restaurants, hotels, news_preview))
    print("      index.html — done")

    with open("news.html", "w", encoding="utf-8") as f:
        f.write(build_news(articles))
    print("      news.html  — done")

    print("\nAll done! Both pages generated successfully.")
