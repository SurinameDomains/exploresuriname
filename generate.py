#!/usr/bin/env python3
"""
ExploreSuriname.com - Full Tourism & News Site Generator
Generates: index.html, nature.html, activities.html,
           restaurants.html, hotels.html, currency.html, news.html,
           sitemap.xml, robots.txt
Run daily via GitHub Actions.
"""

import feedparser
import html as html_lib
import re, os, json
from pathlib import Path
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

SITE_URL       = "https://exploresuriname.com"
CONTACT_EMAIL  = "contact@exploresuriname.com"
SR_TZ          = timezone(timedelta(hours=-3))   # Suriname time (UTC-3, no DST)
YEAR           = datetime.now(SR_TZ).year
MAX_PER_FEED   = 10

# Load OSM enrichment cache (produced by enrich_from_osm.py, committed periodically)
# Keys: slug → {opening_hours, phone, address, cuisine, price_range, ...}
# Format: slug-keyed dict (new) OR legacy list-of-dicts (old) — both handled below
_ENRICHMENTS: dict = {}
_enrich_path = Path(__file__).parent / "listing_enrichments.json"
if _enrich_path.exists():
    try:
        _raw = json.loads(_enrich_path.read_text(encoding="utf-8"))
        if isinstance(_raw, dict):
            _ENRICHMENTS = _raw                          # new slug-keyed format
        else:
            for _e in _raw:                              # legacy list format
                if _e.get("found"):
                    _ENRICHMENTS[_e["slug"]] = _e
        print(f"  Loaded {len(_ENRICHMENTS)} OSM enrichments from listing_enrichments.json")
    except Exception as _err:
        print(f"  Warning: could not load listing_enrichments.json — {_err}")

# Load Foursquare enrichment cache (produced by scripts/fetch_foursquare.py, committed manually)
# Keys: slug → {name, address, phone, website, lat, lng, score, matched, ...}
_FSQ: dict = {}
_fsq_path = Path(__file__).parent / "foursquare_cache.json"
if _fsq_path.exists():
    try:
        _fsq_raw = json.loads(_fsq_path.read_text(encoding="utf-8"))
        _FSQ = {k: v for k, v in _fsq_raw.items() if v.get("matched")}
        print(f"  Loaded {len(_FSQ)} Foursquare matches from foursquare_cache.json")
    except Exception as _err:
        print(f"  Warning: could not load foursquare_cache.json — {_err}")

# Load Foursquare details cache (produced by scripts/fetch_foursquare_details.py, committed manually)
# Keys: slug → {hours_display, photo_url, phone, website}
# Priority in generate.py: Google Places (future) > OSM > Foursquare
_FSQ_DETAILS: dict = {}
_fsq_det_path = Path(__file__).parent / "foursquare_details_cache.json"
if _fsq_det_path.exists():
    try:
        _FSQ_DETAILS = json.loads(_fsq_det_path.read_text(encoding="utf-8"))
        _det_hours = sum(1 for v in _FSQ_DETAILS.values() if v.get("hours_display"))
        _det_photo = sum(1 for v in _FSQ_DETAILS.values() if v.get("photo_url"))
        print(f"  Loaded {len(_FSQ_DETAILS)} FSQ details ({_det_hours} hours, {_det_photo} photos)")
    except Exception as _err:
        print(f"  Warning: could not load foursquare_details_cache.json — {_err}")

# Single source of truth: load all listing data from exploresuriname_listings.json
_jd_path = Path(__file__).parent / "exploresuriname_listings.json"
_BIZ: dict = {}          # slug → full entry dict (name, location, address, phone, website, description …)
_JSON_DESCS: dict = {}   # slug → description  (kept for build_listing_page fallback reference)
if _jd_path.exists():
    try:
        for _e in json.loads(_jd_path.read_text(encoding="utf-8")):
            _slug = _e.get("slug")
            if not _slug: continue
            _BIZ[_slug] = _e
            if _e.get("description", "").strip():
                _JSON_DESCS[_slug] = _e["description"].strip()
        print(f"  Loaded {len(_BIZ)} listings from exploresuriname_listings.json")
    except Exception as _err:
        print(f"  Warning: could not load listing data — {_err}")

FEEDS = [
    {"name": "De Ware Tijd", "url": "https://www.dwtonline.com/feed/",              "color": "#2D6A4F"},
    {"name": "Starnieuws",   "url": "https://www.starnieuws.com/rss/starnieuws.rss","color": "#B40A2D"},
    {"name": "Waterkant",    "url": "https://www.waterkant.net/feed/",               "color": "#1a56db"},
]

# Oil & gas feeds — broad feeds (filter=True) are restricted to Suriname-relevant articles
# OilNow blocks direct RSS (403); routed via Google News proxy instead.
# Offshore Energy: use the Suriname tag feed (already filtered, no kw check needed).
OIL_FEEDS = [
    {"name": "OilNow",         "url": "https://news.google.com/rss/search?q=site:oilnow.gy+Suriname&hl=en&gl=US&ceid=US:en",                                                                                                       "color": "#92400e", "filter": False},
    {"name": "Offshore Energy", "url": "https://www.offshore-energy.biz/tag/suriname/feed/",                                                                                                                                         "color": "#1e40af", "filter": False},
    {"name": "Rigzone",        "url": "https://www.rigzone.com/news/rss/rigzone_news.aspx",                                                                                                                                          "color": "#374151", "filter": True},
    {"name": "Google News",    "url": "https://news.google.com/rss/search?q=Staatsolie+OR+%22Block+58%22+OR+%22Block+52%22+OR+%22GranMorgu%22+OR+%22Sapakara%22+OR+%22Krabdagu%22+OR+%22TotalEnergies+Suriname%22+OR+%22APA+Suriname%22+OR+%22PETRONAS+Suriname%22+OR+%22offshore+Suriname%22+OR+%22Suriname+oil%22+OR+%22Suriname+gas%22+OR+%22Suriname+energy%22&hl=en&gl=US&ceid=US:en", "color": "#be185d", "filter": False},
]

_OIL_KEYWORDS = {
    "suriname", "staatsolie", "block 58", "block 52", "granmorgu", "sapakara", "krabdagu",
    "totalenergies suriname", "apa suriname", "apache suriname", "petronas suriname",
    "offshore suriname", "suriname oil", "suriname gas", "suriname energy",
}

# Finance feeds — Suriname economy, banking, investment, IMF/debt coverage
# Three targeted Google News queries; fetch_finance_articles() deduplicates across them.
FINANCE_FEEDS = [
    # Broad economy & investment coverage — APA, TotalEnergies economics, trade, SRD
    {"name": "Economy & Investment",      "url": "https://news.google.com/rss/search?q=%22Suriname%22+%28economy+OR+investment+OR+finance+OR+%22economic+growth%22+OR+%22trade%22+OR+%22SRD%22%29&hl=en&gl=US&ceid=US:en",                                                                                                                                                                               "color": "#0f766e"},
    # IMF programmes, sovereign debt, fiscal policy — tighter query to avoid diplomatic noise
    {"name": "IMF & Macro",              "url": "https://news.google.com/rss/search?q=%22Suriname%22+%28%22IMF%22+OR+%22debt+restructuring%22+OR+%22fiscal+deficit%22+OR+%22World+Bank%22+OR+%22IDB+Invest%22+OR+%22sovereign+debt%22+OR+%22Surinamese+dollar%22%29&hl=en&gl=US&ceid=US:en",                                                                                                             "color": "#7c3aed"},
    # Banking & financial sector — full institution names to avoid DSB golf-tournament noise
    {"name": "Banking & Financial Sector", "url": "https://news.google.com/rss/search?q=%22Suriname%22+%28%22Centrale+Bank%22+OR+%22De+Surinaamsche+Bank%22+OR+%22Hakrinbank%22+OR+%22Finabank%22+OR+%22Republic+Bank+Suriname%22+OR+%22SRD%22+OR+%22Surinamese+dollar%22+OR+%22exchange+rate+Suriname%22+OR+%22financial+sector+Suriname%22+OR+%22credit+rating+Suriname%22%29&hl=en&gl=US&ceid=US:en", "color": "#b45309"},
]

NATURE_SPOTS = [
    {"name": "Central Suriname Nature Reserve", "badge": "UNESCO World Heritage",
     "desc": "One of the world's largest intact tropical rainforests. Over 1.6 million hectares of pristine rainforest where jaguars, tapirs and giant river otters roam free.",
     "tags": ["UNESCO", "Rainforest", "Wildlife"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e8/Amazon_jungle_from_above.jpg/1280px-Amazon_jungle_from_above.jpg",
     "fact": "Larger than some entire countries", "url": "https://whc.unesco.org/en/list/1017/"},
    {"name": "Brownsberg Nature Park", "badge": "Best Day Trip",
     "desc": "Perched 500m above the Brokopondo Reservoir, Brownsberg rewards visitors with jaw-dropping views, swimming waterfalls and abundant wildlife just 2 hours from Paramaribo.",
     "tags": ["Hiking", "Waterfall", "Views"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG",
     "fact": "Howler monkeys, toucans & jaguars", "url": "https://en.wikipedia.org/wiki/Brownsberg_Nature_Park"},
    {"name": "Galibi Nature Reserve", "badge": "Turtle Nesting Site",
     "desc": "On Suriname's Atlantic coast, giant leatherback sea turtles haul ashore to nest in one of nature's most breathtaking spectacles.",
     "tags": ["Sea Turtles", "Coastal", "Wildlife"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/9/95/Dermochelys_coriacea_%282719177753%29.jpg",
     "fact": "Nesting season: February – July", "url": "https://en.wikipedia.org/wiki/Galibi_Nature_Reserve"},
    {"name": "Peperpot Nature Park", "badge": "Bird Watcher's Paradise",
     "desc": "A former plantation turned bird sanctuary just minutes from the capital. Over 200 bird species recorded.",
     "tags": ["Birding", "Easy Access", "Peaceful"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/0/03/Peperpot_%2814159966508%29.jpg",
     "fact": "700+ bird species in Suriname", "url": "https://en.wikipedia.org/wiki/Peperpot_Nature_Park"},
    {"name": "Voltzberg & Raleighvallen", "badge": "Remote Expedition",
     "desc": "An iconic granite dome rising above the endless jungle canopy. Accessible only by multi-day expedition. The ultimate reward for the most adventurous travellers.",
     "tags": ["Expedition", "Climbing", "Remote"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0a/Voltzberg_Mountain_top.jpg/1280px-Voltzberg_Mountain_top.jpg",
     "fact": "Multi-day jungle trek required", "url": "https://en.wikipedia.org/wiki/Voltzberg"},
    {"name": "Paramaribo Historic Inner City", "badge": "UNESCO World Heritage",
     "desc": "The only wooden colonial city in the Americas. Dutch colonial architecture, Hindu temples, mosques and synagogues coexist in remarkable harmony along the Suriname River.",
     "tags": ["UNESCO", "History", "Culture"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png",
     "fact": "2 UNESCO sites in one country", "url": "https://whc.unesco.org/en/list/940/"},
    {"name": "Bigi Pan Nature Reserve", "badge": "Flamingo Haven",
     "desc": "One of the largest mangrove areas in the Caribbean region, home to spectacular flamingo flocks and extraordinary coastal birdlife.",
     "tags": ["Flamingos", "Mangroves", "Coastal Birds"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/A_flock_of_flamingo%27s_in_Bigi_Pan_%2831095600672%29.jpg/1280px-A_flock_of_flamingo%27s_in_Bigi_Pan_%2831095600672%29.jpg",
     "fact": "Thousands of flamingos year-round", "url": "https://en.wikipedia.org/wiki/Bigi_Pan_Nature_Reserve"},
    {"name": "Wia Wia Nature Reserve", "badge": "Coastal Wilderness",
     "desc": "A protected stretch of Atlantic coastline where endangered sea turtles have nested for centuries. Remote, rarely visited and utterly wild.",
     "tags": ["Sea Turtles", "Coastal", "Remote"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/9/95/Dermochelys_coriacea_%282719177753%29.jpg",
     "fact": "Leatherback & green turtles nest here", "url": "https://en.wikipedia.org/wiki/Wia-Wia_Nature_Reserve"},
    {"name": "Commewijne River", "badge": "River Dolphins & Plantations",
     "desc": "A scenic river just across from Paramaribo, famous for river dolphin sightings, historic plantation ruins and Fort Nieuw Amsterdam.",
     "tags": ["Dolphins", "History", "Easy Access"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg",
     "fact": "River dolphins seen year-round", "url": "https://www.impressivesuriname.com/to_book/commewijne-dolphin-plantation-boat-tour/"},
    {"name": "Upper Suriname River", "badge": "Maroon Heritage",
     "desc": "Journey upriver through dense jungle to Maroon villages of the Saramacca and Matawai peoples. Stay in traditional lodges and experience a living ancient culture.",
     "tags": ["Maroon Culture", "River", "Multi-day"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg",
     "fact": "Ancient Afro-Surinamese cultures", "url": "https://www.knini-paati.com/en/"},
    {"name": "Tafelberg", "badge": "Remote Tepui",
     "desc": "A flat-topped mountain rising dramatically from the rainforest, harbouring unique plant species found nowhere else on earth.",
     "tags": ["Tepui", "Expedition", "Unique Flora"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Tafelberg_Suriname.jpg/1280px-Tafelberg_Suriname.jpg",
     "fact": "Endemic species above the clouds", "url": "https://unlocknature.tours/expeditions/table-mountain/"},
    {"name": "Fort Nieuw Amsterdam", "badge": "Colonial History",
     "desc": "An 18th-century star-shaped fort at the confluence of the Suriname and Commewijne rivers. Now an open-air museum.",
     "tags": ["History", "Museum", "Easy Access"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Cannon_near_Fort_Nieuw_Amsterdam_in_Suriname_%2830451879073%29.jpg/1280px-Cannon_near_Fort_Nieuw_Amsterdam_in_Suriname_%2830451879073%29.jpg",
     "fact": "18th-century Dutch fortification", "url": "https://en.wikipedia.org/wiki/Fort_Nieuw-Amsterdam"},
    {"name": "Sipaliwini Savanna", "badge": "Far South Wilderness",
     "desc": "An isolated savanna near the Brazilian border. Home to giant anteaters, pumas and pristine black-water rivers.",
     "tags": ["Remote", "Savanna", "Wildlife"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/9/9b/Along_the_river_%2817979749230%29.jpg",
     "fact": "Accessible only by small aircraft", "url": "https://www.discoversurinametours.com/english/Tours/expedities/sipaliwini.html"},
    {"name": "Palumeu – Trio Village", "badge": "Indigenous Culture",
     "desc": "Deep in the southern jungle, the Trio indigenous village of Palumeu offers a rare window into a way of life unchanged for generations.",
     "tags": ["Indigenous", "Remote", "Cultural"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/6/61/Primary_school_Paloemeu_Suriname_%2817981257229%29.jpg",
     "fact": "Accessible by charter flight only", "url": "https://www.mets-suriname.com/"},
    {"name": "Colakreek", "badge": "Local Favourite",
     "desc": "A beautiful freshwater creek just outside Paramaribo, perfect for swimming and picnicking surrounded by jungle.",
     "tags": ["Swimming", "Easy Access", "Local Favourite"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg",
     "fact": "30 min from Paramaribo city centre", "url": "https://mets.sr/nl/tour/colakreek-recreation-park/"},
]

ACTIVITIES = [
    {"icon": "🌿", "name": "Jungle Trekking",
     "desc": "Multi-day guided expeditions through primary rainforest with expert Amerindian guides.",
     "url": "https://www.mets-suriname.com/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG"},
    {"icon": "🛶", "name": "River Canoe Tours",
     "desc": "Glide through the Amazon basin on traditional dugout canoes, spotting caimans and river dolphins.",
     "url": "https://allsurinametours.com/en/reservoir-canoe-tour/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg"},
    {"icon": "🦜", "name": "Bird Watching",
     "desc": "Suriname is a birder's paradise. Spot 700+ species including scarlet macaws and harpy eagles.",
     "url": "https://surinameholidays.nl/en/birdwatching/",
     "image": "images/Birding-in-Suriname.webp"},
    {"icon": "🏘️", "name": "Indigenous Village Tours",
     "desc": "Visit Trio and Wayana indigenous communities in the deep interior, preserving ancient traditions.",
     "url": "https://www.mets-suriname.com/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Wayana%2C_muziek_en_dans%2C_1.PNG"},
    {"icon": "🥁", "name": "Maroon Village Tours",
     "desc": "Experience the living culture of the Saramacca and Matawai Maroon peoples: music, craft and history.",
     "url": "https://allsurinametours.com/en/visit-to-maroon-village-santigron/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Santigron_pleng%2C_African_Culture_in_Suriname.jpg"},
    {"icon": "🏙️", "name": "Paramaribo City Walk",
     "desc": "Explore the UNESCO-listed historic inner city on foot. The only wooden colonial city in the Americas.",
     "url": "https://whc.unesco.org/en/list/940/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png"},
    {"icon": "🏊️", "name": "Natural Swimming",
     "desc": "Take a dip in crystal-clear jungle rivers and natural rock pools at Colakreek and Brownsberg.",
     "url": "https://mets.sr/nl/tour/colakreek-recreation-park/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg"},
    {"icon": "🐢", "name": "Turtle Watching",
     "desc": "Witness giant leatherback sea turtles nesting on Suriname's Atlantic coast at Galibi or Wia Wia.",
     "url": "https://en.wikipedia.org/wiki/Galibi_Nature_Reserve",
     "image": "https://upload.wikimedia.org/wikipedia/commons/9/95/Dermochelys_coriacea_%282719177753%29.jpg"},
    {"icon": "🐬", "name": "River Dolphin Watching",
     "desc": "Spot the rare freshwater boto dolphins on a boat tour along the scenic Commewijne River.",
     "url": "https://www.impressivesuriname.com/to_book/commewijne-dolphin-plantation-boat-tour/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Sotalia_fluviatilis_boto_cinza.jpg/1280px-Sotalia_fluviatilis_boto_cinza.jpg"},
    {"icon": "🎨", "name": "Maroon Art & Craft",
     "desc": "Watch master craftsmen carve intricate Maroon woodwork and weave traditional textile art.",
     "url": "https://www.knini-paati.com/en/excursions-suriname/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/a/a8/Wayana%2C_Culturele_voorwerpen.png"},
    {"icon": "🎣", "name": "Sport Fishing",
     "desc": "Fish for piranha, arapaima and peacock bass in jungle rivers and reservoirs.",
     "url": "https://www.orangesuriname.com/en/boat-trips-fishing-tours/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/Arapaima_gigas.jpg/1280px-Arapaima_gigas.jpg"},
    {"icon": "🏛️", "name": "Colonial Plantation Tours",
     "desc": "Cycle or boat through the Commewijne River district, visiting historic coffee and cacao plantations.",
     "url": "https://www.trips-suriname.com/tours/commewijne-plantation-tour/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg"},
    {"icon": "🍽️", "name": "Surinamese Cooking Class",
     "desc": "Learn to cook traditional Creole, Hindustani and Javanese dishes with a local Paramaribo family.",
     "url": "https://www.orangesuriname.com/en/tours/surinamese-cooking-workshop/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/2016_0624_Tjauw_min_moksie_meti_speciaal.jpg/1280px-2016_0624_Tjauw_min_moksie_meti_speciaal.jpg"},
    {"icon": "🚵🏻", "name": "ATV & 4x4 Interior Tours",
     "desc": "Explore jungle trails, gold mining areas and remote villages by ATV or 4x4.",
     "url": "https://bluebirdtourstravel.com/en/products/atv-kabelbaan-avontuur",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG"},
    {"icon": "🌊", "name": "Kayaking & Paddling",
     "desc": "Paddle through mangroves, jungle rivers and lake areas on guided or self-guided kayak tours.",
     "url": "https://www.surinamekayakadventures.com/?lang=en",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Canoe_%28korjaal%29_on_Fungu_Island_jungle_%282719255807%29.jpg/1280px-Canoe_%28korjaal%29_on_Fungu_Island_jungle_%282719255807%29.jpg"},
    {"icon": "🌌", "name": "Jungle Stargazing",
     "desc": "Zero light pollution deep in the interior delivers some of the world's most incredible night skies.",
     "url": "https://unlocknature.tours/tours/multiple-day/",
     "image": ""},
]


def _biz_url(b):
    import re as _re
    w = b.get('website', '')
    if w and _re.match(r'^(https?://|www\.)[^\s@+]{4,}\.[a-z]{2,}', w, _re.I):
        return ('https://' + w) if not w.startswith('http') else w
    return f"https://www.google.com/search?q={urllib.parse.quote(b['name'] + ' Suriname')}"

_IMGS = {
    '4r-gym': 'https://img.youtube.com/vi/_dndYccJtn8/hqdefault.jpg',
    'aaras-cafe': 'https://socialsuriname.com/wp-content/uploads/2025/05/Aaras-Cafe-v1.webp',
    'access-suriname-travel': 'https://www.surinametravel.com/img/logo.png',
    'ace-restaurant-lounge': 'https://aceparamaribo.com/assets/images/logo-removebg-preview.png',
    'activity-atv-4x4-interior-tours': 'https://mets.sr/wp-content/uploads/2017/01/Website_Slider_26_3_2019_AW.jpg',
    'activity-bird-watching': 'https://kabalebo.com/wp-content/uploads/2025/04/kolebri-1024x680.jpg',
    'activity-colonial-plantation-tours': 'https://upload.wikimedia.org/wikipedia/commons/f/f5/Overzicht_van_district_Commewijne_-_Unknown_-_20418727_-_RCE.jpg',
    'activity-indigenous-village-tours': 'https://mets.sr/wp-content/uploads/2017/01/Website_Slider_GR_8_11_2018.jpg',
    'activity-jungle-stargazing': 'https://kabalebo.com/wp-content/uploads/2025/04/mountain4.jpg',
    'activity-jungle-trekking': 'https://kabalebo.com/wp-content/uploads/2025/04/Hiking-Thumb.jpg',
    'activity-kayaking-paddling': 'https://kabalebo.com/wp-content/uploads/2025/04/kayaking-2-1024x686.jpg',
    'activity-maroon-art-craft': 'https://mets.sr/wp-content/uploads/2017/01/Picture-265.jpg',
    'activity-maroon-village-tours': 'https://kabalebo.com/wp-content/uploads/2025/04/boat-tours-1024x683.jpg',
    'activity-natural-swimming': 'https://mets.sr/wp-content/uploads/2017/01/Website_Slider_2_4_2019_KA.jpg',
    'activity-paramaribo-city-walk': 'https://mets.sr/wp-content/uploads/2017/01/Website_Slider_26_3_2019_PA.jpg',
    'afobaka-resort': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Brokopondo_Meer_Viewpiont_%284%29.jpg/1280px-Brokopondo_Meer_Viewpiont_%284%29.jpg',
    'akira-overwater-resort': 'https://www.akiraoverwaterresort.com/wp-content/uploads/2019/01/drone-foto-Akira-resort.jpg',
    'alis-drugstore': 'https://socialsuriname.com/wp-content/uploads/2025/04/Alis-Drugstore.webp',
    'alliance-francaise': 'https://afsuriname.org/wp-content/uploads/2023/09/Cursus-768x512.jpg',
    'amada-shopping': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/6a3e0bdf-e4ec-42d2-9b03-3966d72e5ae7',
    'anaula-nature-resort': 'https://upload.wikimedia.org/wikipedia/commons/3/35/Anaula_Nature_Resort_%2814406614971%29.jpg',
    'anton-de-kom-universiteit-van-suriname': 'https://www.uvs.edu/wp-content/uploads/2017/12/STM_2770.jpg',
    'ashley-furniture-homestore': 'https://www.ashleyfurniture.com/_appnext/immutable/assets/ogimage.DgfO7h4b.webp',
    'assuria-hermitage-high-rise': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'assuria-insurance-walk-in-city': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'assuria-insurance-walk-in-commewijne': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'assuria-insurance-walk-in-lelydorp': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'assuria-insurance-walk-in-nickerie': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'assuria-insurance-walk-in-noord': 'https://www.assuria.sr/assets/globals/highrise.jpg',
    'atlantis-hotel-casino': 'https://ak-d.tripcdn.com/images/220k12000000tb7oy527E_R_960_660_R5_D.jpg',
    'augis-travel': 'https://www.surinamyp.com/img/sr/c/_1684146589-39-augi-s-travel-buro.jpg',
    'auto-style-franchepanestraat': 'https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png',
    'auto-style-johannes-mungrastraat': 'https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png',
    'auto-style-kwatta': 'https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png',
    'auto-style-tweede-rijweg': 'https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png',
    'auto-style-verlengde-gemenelandsweg': 'https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png',
    'ayo-river-lounge': 'https://21271a4b52.clvaw-cdnwnd.com/ac36ef76463495ef5fb3166ec1e36f1f/200000014-e8a82e8a86/700/arl_MG_4835.jpeg?ph=21271a4b52',
    'baka-foto-restaurant': 'https://exploresuriname.com/images/bakafoto.webp',
    'bed-bath-more-bbm': 'https://ims.sr/wp-content/uploads/2024/01/BBM-LOGO-2-1024x724.png',
    'best-mart': 'https://socialsuriname.com/wp-content/uploads/2024/06/Best-Mart-v1.webp',
    'beyrouth-bazaar': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/6bb1563b-3e2a-4ab4-9b80-21058899d91a',
    'bingo-pizza-coppename': 'https://www.bingopizza.sr/wp-content/uploads/2024/04/LogoTransparent.png',
    'bingo-pizza-kwatta': 'https://www.bingopizza.sr/wp-content/uploads/2024/04/LogoTransparent.png',
    'bistro-don-julio': 'https://socialsuriname.com/wp-content/uploads/2025/05/Bistro-Don-Julio-v1.webp',
    'bistro-lequatorze': 'https://socialsuriname.com/wp-content/uploads/2025/05/Bistro-LeQuatorze-v3.webp',
    'bitdynamics': 'https://bitdynamics.sr/wp-content/uploads/2024/08/hero-banner.webp',
    'blue-grand-cafe': 'https://media.evendo.com/locations-resized/RestaurantImages/1920x466/279d3513-01e0-4a6f-a566-2aa86fcb9cd3',
    'bmw-suriname': 'https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/BMW_dealership_Ann_Street%2C_Brisbane.JPG/1280px-BMW_dealership_Ann_Street%2C_Brisbane.JPG',
    'body-enhancement-gym': 'https://socialsuriname.com/wp-content/uploads/2024/06/body-enhancement-gym-01-cf3p.webp',
    'boekhandel-vaco': 'https://socialsuriname.com/wp-content/uploads/2025/04/Boekhandel-VACO.webp',
    'boss-burgers': 'https://socialsuriname.com/wp-content/uploads/2024/06/boss-burgers-01.webp',
    'brahma-centrum': 'https://www.surinamyp.com/img/sr/n/1683285743-51-brahma-n-v.jpg',
    'brahma-noord': 'https://www.surinamyp.com/img/sr/n/1683285743-51-brahma-n-v.jpg',
    'brahma-zuid': 'https://www.surinamyp.com/img/sr/n/1683285743-51-brahma-n-v.jpg',
    'bronbella-villa-residence': 'https://bronbellavillaresidence.com/wp-content/uploads/2024/08/Bronbella_website-7-1024x683.jpg',
    'building-depot': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/b347d2d1-574a-4c21-8c75-afa6e4aedda9',
    'burger-king-centrum': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzbCjvHfbGdFlhB6LJQjbLq-GipEldY9BP1w&s',
    'burger-king-latour': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSzbCjvHfbGdFlhB6LJQjbLq-GipEldY9BP1w&s',
    'carline-kwatta': 'https://www.carline.sr/wp-content/uploads/2022/01/chase.jpg',
    'carline-waaldijkstraat': 'https://www.carline.sr/wp-content/uploads/2022/01/chase.jpg',
    'carvision-paramaribo': 'https://carvision.io/wp-content/uploads/2024/03/carvision3.jpg',
    'chees-jewelry-watches': 'https://www.surinamyp.com/img/sr/a/_1684146815-27-chee-s-jewelry-watches.png',
    'chois-supermarkt': 'https://www.surinamyp.com/img/sr/l/1683286152-83-choi-s-supermarkt.png',
    'chois-supermarkt-lelydorp': 'https://www.surinamyp.com/img/sr/l/1683286152-83-choi-s-supermarkt.png',
    'chois-supermarkt-north': 'https://www.surinamyp.com/img/sr/l/1683286152-83-choi-s-supermarkt.png',
    'chuck-e-cheese': 'https://upload.wikimedia.org/wikipedia/commons/2/2d/Chuck_E_Cheese%27s_Pizza_%28crop%29.jpg',
    'cinnagirl': 'https://socialsuriname.com/wp-content/uploads/2025/01/Cinnagirl.webp',
    'ciranos': 'https://socialsuriname.com/wp-content/uploads/2025/05/Ciranos-Restaurant-v2.webp',
    'clevia-park': 'https://cleviapark.sr/wp-content/uploads/2024/01/Hengelen-en-bootje-varen-bij-Clevia-Park.jpg',
    'club-oase': 'https://www.cluboase.sr/wp-content/uploads/2023/02/OASE-web.jpg',
    'coffee-mama': 'https://cdn.shopify.com/s/files/1/0818/3732/6683/files/logo_coffee_mama_small_001_png.png',
    'cola-kreek-recreatiepark': 'https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg',
    'combe-bazaar': 'https://www.surinamyp.com/img/sr/x/1683280412-80-combe-markt.jpg',
    'combe-markt': 'https://www.surinamyp.com/img/sr/x/1683280412-80-combe-markt.jpg',
    'computer-hardware-services': 'https://www.surinamyp.com/img/sr/g/1683543164-96-computer-hardware-services-n-v-chs.png',
    'computronics-north': 'https://computronics.sr/skin/frontend/base/default/images/logo-new01.jpg',
    'computronics-south': 'https://computronics.sr/skin/frontend/base/default/images/logo-new01.jpg',
    'conservatorium-suriname': 'https://conservatoriumsuriname.com/wp-content/uploads/2024/01/conservatorium_logo.webp',
    'courtyard-by-marriott': 'https://cache.marriott.com/content/dam/marriott-renditions/PBMCY/pbmcy-pool-0043-hor-wide.jpg',
    'crocs-ims': 'https://ims.sr/wp-content/uploads/2023/08/Crocs.png',
    'cute-as-a-button': 'https://ims.sr/wp-content/uploads/2023/09/Cute-as-a-button-logo-nieuw-design.png',
    'd-mighty-view-lounge': 'https://travelbubu.com/images/spots/d-mighty.jpg',
    'da-drogisterij-coppename': 'https://ims.sr/wp-content/uploads/2024/01/DA_logo.png',
    'da-drogisterij-hermitage': 'https://ims.sr/wp-content/uploads/2024/01/DA_logo.png',
    'da-drogisterij-ims-mall': 'https://ims.sr/wp-content/uploads/2024/01/DA_logo.png',
    'da-drogisterij-lelydorp': 'https://ims.sr/wp-content/uploads/2024/01/DA_logo.png',
    'da-drogisterij-wilhelmina': 'https://ims.sr/wp-content/uploads/2024/01/DA_logo.png',
    'danpaati-river-lodge': 'https://www.orangesuriname.com/wp-content/uploads/2023/12/Danpaati-orange-suriname-lodge-view-1.png',
    'dcars-rental': 'https://www.dcarsrental.com/app/web/upload/medium/dcars-straat-in-paramaribo-2966-1775905846.png',
    'de-gadri': 'https://exploresuriname.com/images/gadri.webp',
    'de-keurslager-interfarm': 'https://www.interfarmnv.com/img2/interfarm_logo.png',
    'de-spot': 'https://de-spot.com/media/frontpage/frontpage.jpg',
    'de-surinaamsche-bank-hermitage-mall': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-hoofdkantoor': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-lelydorp': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-ma-retraite': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-ma-retraite-2': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-nickerie': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-nickerie-2': 'https://www.dsb.sr/assets/og-dsb.png',
    'de-surinaamsche-bank-nieuwe-haven': 'https://www.dsb.sr/assets/og-dsb.png',
    'deto-handelmaatschappij': 'https://socialsuriname.com/wp-content/uploads/2024/06/deto-v1.webp',
    'digicel-albina': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-business-center': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-extacy': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-hermitage': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-latour': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-lelydorp': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-nickerie': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digicel-wilhelminastraat': 'https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg',
    'digital-world-hermitage-mall': 'https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315',
    'digital-world-ims': 'https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315',
    'digital-world-maretraite-mall': 'https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315',
    'digital-world-maretraite-mall-2': 'https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315',
    'dojo-couture-centrum': 'https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg',
    'dojo-couture-hermitage-mall': 'https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg',
    'dojo-couture-ims': 'https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg',
    'dolce-bella-cafe': 'https://socialsuriname.com/wp-content/uploads/2025/06/Dolce-Bella-Cafe-v1.webp',
    'dresscode': 'https://www.waterkant.net/wp-content/2018/08/i-love-su-suriname.jpg',
    'eco-resort-miano': 'https://mianoecoresort.wordpress.com/wp-content/uploads/2025/09/05bab-1755531893645.jpg',
    'eco-torarica': 'https://ecotorarica.com/uploads/images/page/original/whatsapp-image-2026-03-22-at-10-05-24.jpeg',
    'eethuis-liv': 'https://socialsuriname.com/wp-content/uploads/2025/11/Eethuis-Liv-v1.webp',
    'el-patron-latin-grill': 'https://elpatronlatingrill.com/wp-content/uploads/2024/09/EPLG-1-scaled.jpg',
    'energiebedrijven-suriname-ebs': 'https://img.youtube.com/vi/jmMIdsBlXDw/hqdefault.jpg',
    'etembe-rainforest-restaurant': 'https://media.evendo.com/locations-resized/RestaurantImages/1920x466/fc5d6a30-bcd7-4eb1-b9d2-b880b803d5a3',
    'ettores-pizza-kitchen': 'https://cache.marriott.com/content/dam/marriott-renditions/PBMCY/pbmcy-restaurant-2683-sq.jpg',
    'everything-sr': 'https://socialsuriname.com/wp-content/uploads/2025/06/Everything.sr-v2.webp',
    'fatum-schadeverzekering-commewijne': 'https://info-suriname.com/wp-content/uploads/2017/09/logo-Fatum.png',
    'fatum-schadeverzekering-hoofdkantoor': 'https://info-suriname.com/wp-content/uploads/2017/09/logo-Fatum.png',
    'fatum-schadeverzekering-kwatta': 'https://info-suriname.com/wp-content/uploads/2017/09/logo-Fatum.png',
    'fatum-schadeverzekering-nickerie': 'https://info-suriname.com/wp-content/uploads/2017/09/logo-Fatum.png',
    'finabank-centrum': 'https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg',
    'finabank-nickerie': 'https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg',
    'finabank-noord': 'https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg',
    'finabank-wanica': 'https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg',
    'finabank-zuid': 'https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg',
    'fish-finder-fishing-and-outdoors': 'https://img.youtube.com/vi/S6w4_vktD4g/hqdefault.jpg',
    'flavor-restaurant': 'https://cache.marriott.com/content/dam/marriott-renditions/PBMCY/pbmcy-restaurant-2683-sq.jpg',
    'flex-luxuries': 'https://socialsuriname.com/wp-content/uploads/2024/06/flex-luxuries-01-02c9.webp',
    'flex-phones': 'https://www.surinamyp.com/img/sr/e/1683543969-41-flex-phones.jpg',
    'fly-allways': 'https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg/1280px-Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg',
    'folo-nature-tours': 'https://socialsuriname.com/wp-content/uploads/2024/06/Folo-Nature-Tours.webp',
    'footcandy-hermitage-mall': 'https://mallsbycountry.com/images/stores/hermitage-mall/foot-candy-logo.png',
    'ford-zeelandia': 'https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Fort_Zeelandia.jpg/1280px-Fort_Zeelandia.jpg',
    'frygri': 'https://socialsuriname.com/wp-content/uploads/2025/03/FryGri.webp',
    'furniture-city-kwatta': 'https://images.squarespace-cdn.com/content/v1/641dd0ce8e44087636ccf334/214f42ae-b8f9-4e96-94be-aa5c8d8652a5/FurnitureCityLogo%27s+solo.png?format=1500w',
    'furniture-city-north': 'https://images.squarespace-cdn.com/content/v1/641dd0ce8e44087636ccf334/214f42ae-b8f9-4e96-94be-aa5c8d8652a5/FurnitureCityLogo%27s+solo.png?format=1500w',
    'gaby-april-beauty-clinic': 'https://socialsuriname.com/wp-content/uploads/2025/11/Gaby-April-Beauty-Clinic-v1.webp',
    'galaxy': 'https://ims.sr/wp-content/uploads/2023/07/Galaxy-logo-zwart-1024x837.png',
    'galaxyliving': 'https://galaxy.sr/wp-content/uploads/2019/10/Galaxy-zwart.png',
    'gao-ming-trading-north': 'https://www.surinamyp.com/img/sr/z/_1683566205-19-gao-ming-trading.jpg',
    'gao-ming-trading-south': 'https://www.surinamyp.com/img/sr/z/_1683566205-19-gao-ming-trading.jpg',
    'garage-d-a-ashruf': 'https://garageashruf.com/wp-content/uploads/2023/05/GarageDaAshruf-OGImage-1200x360Concept_1.jpg',
    'georgies-bar-chill': 'https://socialsuriname.com/wp-content/uploads/2024/06/Georgies-Bar-Chill.webp',
    'goe-thai-noodle-bar': 'https://www.goe.sr/wp-content/uploads/2020/07/home-700-inter.png',
    'golf-club-paramaribo': 'https://golfclubparamaribo.com/wp-content/uploads/2025/05/488417682_1416452269681580_8011502248948940642_n.jpg',
    'greenheart-boutique-hotel': 'https://www.greenheartboutiquehotel.com/images/logo-green.png',
    'grounded-botanical-studio': 'https://ims.sr/wp-content/uploads/2025/04/Grounded.jpg',
    'guesthouse-albergoalberga': 'https://guesthousealberga.com/wp-content/uploads/2024/03/cropped-302162370_459943272818604_7623356389716890021_n.png',
    'guesthouse-albina': 'https://guesthousealbina.com/wp-content/uploads/2024/05/Guesthouse-Albina-Logo-dunne-ronde-kader-Transparant.png',
    'hakrinbank': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-flora': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-latour': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-nickerie': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-nieuwe-haven': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-tamanredjo': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hakrinbank-tourtonne': 'https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png',
    'hard-rock-cafe-suriname': 'https://ims.sr/wp-content/uploads/2023/07/food-hard-rock.jpg',
    'hermitage-mall': 'https://hermitage-mall.com/wp-content/uploads/2018/03/HermitageMall-building.jpg',
    'het-koto-museum': 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Koto_Museum%2C_5.jpg/1280px-Koto_Museum%2C_5.jpg',
    'holiday-home-decor': 'https://socialsuriname.com/wp-content/uploads/2025/07/Holiday-Home-Decor-v2.webp',
    'holland-lodge': 'https://www.hollandlodge.nl/wp-content/uploads/2020/07/Holland-1.jpg',
    'hollandia-bakkerij-north': 'https://www.surinamyp.com/img/sr/h/1683203767-37-hollandia-bakkerij-n-v.jpg',
    'hollandia-bakkerij-south': 'https://www.surinamyp.com/img/sr/h/1683203767-37-hollandia-bakkerij-n-v.jpg',
    'holy-moly': 'https://socialsuriname.com/wp-content/uploads/2025/03/Holy-Moly-v3.webp',
    'honeycare': 'https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=800&q=80',
    'honeycare-north': 'https://www.honeycaresu.com/wp-content/uploads/2024/02/HC_Cat_Thumb2.jpg',
    'honeycare-south': 'https://www.honeycaresu.com/wp-content/uploads/2024/02/HC_Cat_Thumb2.jpg',
    'hotel-north-resort': 'https://content.r9cdn.net/rimg/himg/43/10/4a/expediav2-444817-ec9020-313005.jpg?width=1200&height=630&crop=false',
    'hotel-palacio': 'https://irp.cdn-website.com/b0c3c22b/dms3rep/multi/Palacio-exterior-street.jpg',
    'hotel-peperpot': 'https://hotelpeperpot.nl/wp-content/uploads/2024/02/66e837d5-13a7-4712-8766-fc69fcc52b4c-scaled.jpg',
    'houttuyn-wellness-river-resort': 'https://www.houttuyn.com/wp-content/uploads/2020/08/Nature.jpg',
    'iamchede': 'https://socialsuriname.com/wp-content/uploads/2025/10/Iamchede-v1.webp',
    'instyle-optics': 'https://www.instyle.sr/wp-content/uploads/2024/03/instyle-logo-200px.png',
    'international-mall-of-suriname': 'https://ims.sr/wp-content/uploads/2024/01/IMS-Right-scaled.jpg',
    'intervast': 'https://www.intervast.nl/components/com_realestatemanager/photos/70381D52-4211-16F0-DE9C-470BB8CACC2D_dji_0462_1400_600_1_.JPG',
    'invictus-brazilian-jiu-jitsu': 'https://img.youtube.com/vi/gY6GsJUjX7Q/hqdefault.jpg',
    'itrendzz': 'https://socialsuriname.com/wp-content/uploads/2024/06/iTrendzZ-v1.webp',
    'jacana-amazon-wellness-resort': 'https://jacanaresort.com/wp-content/uploads/2023/05/Slide-1.jpg',
    'jack-tours-travel-service': 'https://www.surinamyp.com/img/sr/n/1683280999-29-jack-tours-travel-service.jpg',
    'jadore-cafe-grill': 'https://socialsuriname.com/wp-content/uploads/2024/12/Jadore-Cafe-Grill.webp',
    'jage-caffe': 'https://ims.sr/wp-content/uploads/2025/02/jage-2.png',
    'jage-caffe-2': 'https://ims.sr/wp-content/uploads/2025/02/jage-2.png',
    'janelles-shoes-and-bags': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/7580db81-eb04-4445-80e2-0789b03625f5',
    'jenny-tours': 'https://suriname-tour.com/wp-content/uploads/benodigdheden-inreizen-suriname-1.png',
    'joden-savanne': 'https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Jodensavanne.jpg/1280px-Jodensavanne.jpg',
    'joosje-roti-shop': 'https://www.surinamyp.com/img/sr/z/1683543876-37-joosje-roti-shop.jpg',
    'kabalebo-nature-resort': 'https://kabalebo.com/wp-content/uploads/2025/04/home-header.jpg',
    'karans-indian-food': 'https://socialsuriname.com/wp-content/uploads/2024/06/Karans-Indian-Food-v1.webp',
    'kasco-customs-solutions': 'https://kascocustomssolutions.com/wp-content/uploads/2026/03/35584898-foreman-control-loading-containers-box-from-cargo-freight-ship-for-import-export-container-warehouse-worker.jpg',
    'kasimex-indira-ghandiweg': 'https://www.surinamyp.com/img/sr/f/1683567410-28-kasimex-n-v-superstore.png',
    'kasimex-makro': 'https://www.surinamyp.com/img/sr/f/1683567410-28-kasimex-n-v-superstore.png',
    'keller-williams-suriname': 'https://kwsuriname.com/storage/app/uploads/public/638/65b/0ba/63865b0ba9f36584922562.jpg',
    'ket-mien': 'https://socialsuriname.com/wp-content/uploads/2025/05/Ket-Mien-Co-v1.webp',
    'kfc-ims': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-kwatta': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-lallarookh': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-latour': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-lelydorp': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-waterkant': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kfc-wilhelminastraat': 'https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png',
    'kimboto': 'https://i0.wp.com/sairahtujeehut.com/wp-content/uploads/2022/02/kimboto-cover-website.png?fit=1200%2C676&ssl=1',
    'kirpalani': 'https://www.surinamyp.com/img/sr/e/1683222276-81-kirpalani-s-nv-warenhuis.jpg',
    'kirpalani-domineestraat': 'https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp',
    'kirpalani-maagdenstraat': 'https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp',
    'kirpalani-super-store': 'https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp',
    'klm-royal-dutch-airlines': 'https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg/1280px-KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg',
    'knini-paati': 'https://www.knini-paati.com/wp-content/uploads/eco-vakantie-suriname.jpg',
    'krioro': 'https://socialsuriname.com/wp-content/uploads/2024/06/Krioro-Noord-v1.webp',
    'kushiyaki-the-next-episode': 'https://socialsuriname.com/wp-content/uploads/2024/06/House-of-Kushiyaki.webp',
    'kwan-tai-restaurant': 'https://socialsuriname.com/wp-content/uploads/2024/06/Kwan-Tai-v1.webp',
    'kwan-tai-restaurant-2': 'https://socialsuriname.com/wp-content/uploads/2024/06/Kwan-Tai-v1.webp',
    'kyu-pho-grill': 'https://socialsuriname.com/wp-content/uploads/2025/10/KYU-Pho-and-Grill-v2.webp',
    'le-den': 'https://socialsuriname.com/wp-content/uploads/2025/11/Le-Den-v1.webp',
    'lees-korean-grill': 'https://www.surinamyp.com/img/sr/h/1683547092-91-lee-s-korean-restaurant.jpg',
    'lilis': 'https://cdn.shopify.com/s/files/1/0526/9137/0149/files/Bridal_2a85f0ad-2db8-4a8a-ac54-3e090625d4de.jpg',
    'lobby': 'https://socialsuriname.com/wp-content/uploads/2024/06/Lobby-v1.webp',
    'lucky-store': 'https://socialsuriname.com/wp-content/uploads/2024/06/Lucky-Store.webp',
    'lucky-twins-restaurant': 'https://www.surinamyp.com/img/sr/f/1683204464-18-lucky-twins-restaurant.jpg',
    'maharaja-palace': 'https://socialsuriname.com/wp-content/uploads/2024/06/Maharaja-Palace.webp',
    'marina-resort-waterland': 'https://surinameholidays.nl/wp-content/uploads/2016/05/IMG_3067-Edit.jpg',
    'maze': 'https://socialsuriname.com/wp-content/uploads/2024/06/Maze-v1.webp',
    'mcdonalds-centrum': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/McDonald%27s_logo_Targ%C3%B3wek.JPG/1280px-McDonald%27s_logo_Targ%C3%B3wek.JPG',
    'mcdonalds-hermitage-mall': 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/McDonald%27s_logo_Targ%C3%B3wek.JPG/1280px-McDonald%27s_logo_Targ%C3%B3wek.JPG',
    'mimi-market': 'https://socialsuriname.com/wp-content/uploads/2024/06/Mimi-Market-v1.webp',
    'mingle-paramaribo': 'https://ims.sr/wp-content/uploads/2025/02/Logo-Mingle-Cocktail-Lounge_gold-1024x1024.png',
    'mingle-sushi': 'http://mingleparamaribo.com/wp-content/uploads/2022/06/Logo-Mingle-Cocktail-Lounge_gold.png',
    'miniso-gompertstraat': 'https://www.miniso.com/Uploads/img/20230511/6459c5046dd82.jpg',
    'miniso-hermitage-mall': 'https://www.miniso.com/Uploads/img/20230511/6459c5046dd82.jpg',
    'miss-doll-fit': 'https://socialsuriname.com/wp-content/uploads/2024/06/Miss-Doll-Fit.webp',
    'moka-coffeebar': 'https://socialsuriname.com/wp-content/uploads/2026/04/Moka-Coffee-Bar-v1-01-ti04.webp',
    'mondowa-tours': 'https://img.youtube.com/vi/wvFWCxPvzYA/hqdefault.jpg',
    'morevans-outlet': 'https://img.youtube.com/vi/SEAFaXpvjmE/hqdefault.jpg',
    'multi-travel': 'https://www.surinamyp.com/img/sr/g/_1684246192-86-multi-travel.jpg',
    'murphys-irish-pub': 'https://ims.sr/wp-content/uploads/2023/07/murphys.png',
    'museum-bakkie': 'https://museumbakkie.com/wp-content/uploads/2022/02/museum-bakkie-sluis.jpg',
    'naskip': 'https://www.naskip.com/wp-content/uploads/2025/02/logo.jpg',
    'naskip-2': 'https://www.naskip.com/wp-content/uploads/2025/02/logo.jpg',
    'naskip-3': 'https://www.naskip.com/wp-content/uploads/2025/02/logo.jpg',
    'naskip-4': 'https://www.naskip.com/wp-content/uploads/2025/02/logo.jpg',
    'naskip-5': 'https://www.naskip.com/wp-content/uploads/2025/02/logo.jpg',
    'norrii-zushii': 'https://socialsuriname.com/wp-content/uploads/2024/06/Norrii-Zushii-v1.webp',
    'north-fitness-gym': 'https://socialsuriname.com/wp-content/uploads/2024/06/north-fitness-gym-01-ha0t.webp',
    'nr-1-spot': 'https://socialsuriname.com/wp-content/uploads/2026/01/Nr.-1-Spot-v1.webp',
    'oasis-restaurant': 'https://socialsuriname.com/wp-content/uploads/2025/11/Oasis-Restaurant-v1.webp',
    'ochama-amazing': 'https://mallsbycountry.com/images/stores/hermitage-mall/ochama-logo.jpg',
    'ochama-hermitage-mall': 'https://mallsbycountry.com/images/stores/hermitage-mall/ochama-logo.jpg',
    'office-world-hermitage-mall': 'https://www.surinamyp.com/img/sr/h/1683221352-13-office-world.jpg',
    'office-world-lelydorp': 'https://www.surinamyp.com/img/sr/h/1683221352-13-office-world.jpg',
    'ogi-teppanyaki-sushi-bar': 'https://www.ramadaparamaribo.com/wp-content/uploads/2024/06/best-seller-food-crop-1.jpg',
    'okido-tours-travel': 'https://okidotravel.com/wp-content/uploads/2022/08/NEW-logo-web.png',
    'okopipi-tropical-grill': 'https://okopipitropicalgrill.com/wp-content/uploads/2024/09/OKOPIPI-1.png',
    'olive-multi-cuisine-restaurant': 'https://socialsuriname.com/wp-content/uploads/2024/06/Olive-Multi-Cuisine-Restaurant-v1.webp',
    'optiek-all-vision': 'https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg',
    'optiek-all-vision-albina': 'https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg',
    'optiek-all-vision-lelydorp': 'https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg',
    'optiek-all-vision-nickerie': 'https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg',
    'optiek-marisa': 'https://www.surinamyp.com/img/sr/z/1683283789-85-optiek-marisa.jpg',
    'optiek-ninon': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'optiek-ninon-hermitage-mall': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'optiek-ninon-ims': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'optiek-ninon-lelydorp': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'optiek-ninon-meerzorg': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'optiek-ninon-nickerie': 'https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg',
    'outdoor-living': 'https://socialsuriname.com/wp-content/uploads/2024/06/Outdoor-Living.webp',
    'overbridge-river-resort': 'https://overbridge.sr/wp-content/uploads/2019/02/overbridge-river-resort-type_sm.png',
    'oxygen-resort': 'https://oxygen-resort.com/wp-content/uploads/2022/07/slide-1.jpg',
    'padel-x-suriname': 'https://upload.wikimedia.org/wikipedia/commons/f/ff/Platform_26_padel_tennis_courts_behind_Railway_Street%2C_Chatham.jpg',
    'padre-nostro-italian-restaurant': 'https://padrenostro16.com/wp-content/uploads/2023/12/cropped-Small-Logo-Padre-Nostro-150x92.png',
    'pandie': 'https://www.ilovepandie.com/wp-content/uploads/2022/05/Untitled-design-19-1-e1652362466132.png',
    'paramaribo-zoo': 'http://paramaribozoo.sr/wp-content/uploads/2024/12/slider-paramaribo-zoo-2.jpg',
    'passion-food-and-wines': 'https://impro.usercontent.one/appid/hostnetWsb/domain/passiefoodandwines.com/media/passiefoodandwines.com/onewebmedia/picture-120044.jpg?etag=undefined&sourceContentType=image%2Fjpeg&quality=85',
    'peperpot-nature-park': 'https://images.squarespace-cdn.com/content/v1/5d52bcc2f6730e0001fe9d75/1649371470790-ED2SMLZ2QP4VLM1WUFJ3/Peperpot+Drone8.jpg',
    'petit-bouchon': 'https://socialsuriname.com/wp-content/uploads/2025/07/Petit-Bouchon.webp',
    'pineapple-tours': 'https://pineappletourssu.nl/onewebmedia/IMG-20241109-WA0001.jpg',
    'pizza-hut-leysweg': 'https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png',
    'pizza-hut-south': 'https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png',
    'pizza-hut-wilhelminastraat': 'https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png',
    'pizza-mafia': 'https://socialsuriname.com/wp-content/uploads/2024/06/pizza-mafia.webp',
    'plantage-frederiksdorp': 'https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg',
    'popeyes-centrum': 'https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg',
    'popeyes-lelydorp': 'https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg',
    'popeyes-tbl': 'https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg',
    'popeyes-wilhelminastraat': 'https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg',
    'radisson-hotel': 'https://ak-d.tripcdn.com/images/0226b12000rtqz8o4F02F_Z_1280_853_R50_Q90.jpg',
    'ramada-paramaribo-princess': 'https://www.ramadaparamaribo.com/wp-content/uploads/2026/02/pizza-cover.jpeg',
    're-max-suriname': 'https://static-images.remax.com/assets/web/global/v2/homepage/global-hero.jpg',
    'readytex-art-gallery': 'https://www.readytexartgallery.com/wp-content/uploads/2026/02/rag_expo-3-26_1920x870.jpg',
    'readytex-souvenirs-and-crafts': 'https://www.readytexcrafts.com/wp-content/uploads/2021/03/sigaar.jpg',
    'real-one-fitness-gym': 'https://socialsuriname.com/wp-content/uploads/2025/08/REAL-ONE-Fitness-GYM.webp',
    'red-century-party-shop-commewijne': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371',
    'red-century-party-shop-kwatta': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371',
    'red-century-party-shop-lelydorp': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371',
    'red-century-party-shop-north': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371',
    'red-century-party-shop-zorg-en-hoop': 'https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371',
    'remy-vastgoed': 'https://www.remyvastgoed.com/storage/2023/04/RV-vierkant-1.png',
    'republic-bank-head-office': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'republic-bank-jozef-israelstraat': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'republic-bank-kernkampweg': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'republic-bank-nickerie': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'republic-bank-vant-hogerhuysstraat': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'republic-bank-zorg-en-hoop': 'https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg',
    'residence-inn-nickerie': 'https://residenceinn.sr/wp-content/uploads/2024/06/web-logo-ResInn.png',
    'residence-inn-paramaribo': 'https://residenceinn.sr/wp-content/uploads/2024/06/web-logo-ResInn.png',
    'restaurant-lhermitage': 'https://www.hermitage.sr/wp-content/uploads/2021/03/Hermitage-Fine-Dining-menukaart-1-1300x352-1.png',
    'restaurant-sarinah': 'https://socialsuriname.com/wp-content/uploads/2024/06/Sarinah-Indisch-Restaurant.webp',
    'restoran-bibit': 'https://socialsuriname.com/wp-content/uploads/2024/06/Restoran-Bibit-1.webp',
    'rich-skin': 'https://richskinsu.com/wp-content/uploads/2025/03/Asset-2_5.png',
    'ricos-a-gladiator-foodtruck': 'https://socialsuriname.com/wp-content/uploads/2025/04/Ricos-v3.webp',
    'rolines-de-waag': 'https://socialsuriname.com/wp-content/uploads/2024/06/Rolines-De-Waag-V1.webp',
    'roopram-roti-shop': 'https://www.surinamyp.com/img/sr/a/1683283161-65-roopram-rotie-shop.jpg',
    'rossignol-2go-kwattaweg': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'rossignol-2go-thurkowstraat': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'rossignol-coppename': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'rossignol-geyersvlijt': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'rossignol-linda': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'rossignol-waaldijkstraat': 'http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656',
    'royal-brasil-hotel': 'https://royalbrasilhotel.com/wp-content/uploads/2022/07/building-side-1.jpg',
    'royal-breeze-hotel-paramaribo': 'https://royalbreezeparamaribo.com/wp-content/uploads/2022/12/Royal-breeze-HOR-logo.png',
    'royal-torarica': 'https://royaltorarica.com/uploads/images/page/original/orchid(1).jpg',
    'royal-tours-suriname-guyana': 'https://img.youtube.com/vi/JbRKcloOTZA/hqdefault.jpg',
    'sakura': 'https://socialsuriname.com/wp-content/uploads/2024/06/SAKURA-v3.webp',
    'samba-cafe': 'https://socialsuriname.com/wp-content/uploads/2025/04/Samba-Cafe-v1.webp',
    'sanousch-books': 'https://www.surinamyp.com/img/sr/c/_1684307098-60-sanoush-books.jpg',
    'saras-brunch-cafe': 'https://socialsuriname.com/wp-content/uploads/2024/06/Saras-Brunch-Cafe.webp',
    'sash-fashion-hermitage-mall': 'https://mallsbycountry.com/images/stores/hermitage-mall/sash-fashion-logo.png',
    'satyam-holidays': 'https://www.surinamyp.com/img/sr/l/_1683208455-48-satyam-holidays.png',
    'savage-den': 'https://savageden.sr/wp-content/uploads/2025/11/PHOTO-2025-11-03-10-30-58-1024x1024.jpg',
    'savannah-casino-hotel': 'https://cdn.worldota.net/t/640x400/content/e7/27/e72767fe01b309ca7a9a45352ac1e9041ddd91a2.jpeg',
    'seen-stories': 'https://images.squarespace-cdn.com/content/v1/67d096a1ab6b7b756d0e779b/eb825299-fae9-4c65-9309-cbc5ca4d4bcc/Shell+docu+1.png',
    'sendang-redjo': 'https://socialsuriname.com/wp-content/uploads/2025/10/Sendang-Redjo-v6.webp',
    'shlx-collection': 'https://shlx.shop/wp-content/uploads/2022/01/maillogo.png',
    'shoebizz-ims': 'https://ims.sr/wp-content/uploads/2023/09/shoebizz_office.jpg',
    'slagerij-stolk': 'https://socialsuriname.com/wp-content/uploads/2024/06/Slagerij-Stolk.webp',
    'sleepstore-suriname': 'https://sleepstore.sr/wp-content/uploads/2025/02/SleepStore-logo-black.png',
    'smart-connexxionz': 'https://assets.smartconnexxionz.com/website/home/logos/logo-round.png',
    'soengngie-mega-store': 'https://www.soengco.com/adimages/logo.png',
    'soengngie-oriental-market': 'https://www.soengco.com/adimages/logo.png',
    'southern-commercial-bank': 'https://scombank.sr/wp-content/uploads/2024/02/4-kaarten.png',
    'spice-quest': 'https://socialsuriname.com/wp-content/uploads/2024/06/Spice-Quest.webp',
    'squeezy-hot-pot-restaurant': 'https://socialsuriname.com/wp-content/uploads/2024/06/Squeezy-Hot-Pot-Restaurant.webp',
    'sranan-fowru': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-boni': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-combe': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-flu': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-leiding': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-lelydorp': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-meursweg': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-tabiki-fowru': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-tourtonne': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'sranan-fowru-zinnia': 'https://srananfowru.sr/wp-content/uploads/2025/06/SF_Hele-Kip.png',
    'steps-domineestraat': 'https://steps-shop.weblocher.com/img2/about_bg.jpg',
    'steps-hermitage-mall': 'https://steps-shop.weblocher.com/img2/about_bg.jpg',
    'steps-noord': 'https://steps-shop.weblocher.com/img2/about_bg.jpg',
    'steps-wanica': 'https://steps-shop.weblocher.com/img2/about_bg.jpg',
    'stichting-surinaams-museum': 'http://www.surinaamsmuseum.net/wp-content/uploads/2015/08/SurinaamsMuseum-for-web.png',
    'store4u': 'https://cdn.shopify.com/s/files/1/0279/8354/4372/files/9399472_orig_76349385-5be0-462b-b95e-db9bc2cfa0f9.png?v=1594058546',
    'subway': 'https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg',
    'subway-2': 'https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg',
    'subway-3': 'https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg',
    'sugar': 'https://socialsuriname.com/wp-content/uploads/2025/03/Sugar-v1.webp',
    'suran-adventures-tours-travel': 'https://suranadventures.com/uploads/0000/1/2023/07/14/untitled-2.png',
    'suraniyat': 'https://images.squarespace-cdn.com/content/v1/65207f08df58fe10d1fab14f/20be6ae2-e0a4-4f62-a609-dcb80ea7e0ef/IMG_0922.jpg',
    'surgoed-makelaardij': 'https://www.surgoed.com/wp-content/uploads/2023/06/Surgoed-Makelaardij-NV-Paramaribo-Suriname-Homepage-Image.jpg',
    'surinaamsche-waterleiding-maatschappij': 'https://swm.sr/wp-content/uploads/2023/04/swm-logo.png',
    'surinam-airways': 'https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg/1280px-PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg',
    'sweetheart-hermitage-mall': 'https://ims.sr/wp-content/uploads/2024/01/Sweetheart-_1-1024x573.png',
    'sweetheart-ims': 'https://ims.sr/wp-content/uploads/2024/01/Sweetheart-_1-1024x573.png',
    'sweetie-coffee': 'https://socialsuriname.com/wp-content/uploads/2024/06/Sweetie-Coffee.webp',
    'switi-momenti-candles-crafts': 'https://ims.sr/wp-content/uploads/2025/04/switi-momenti-1024x634.jpg',
    'talking-prints-concept-store': 'https://cdn.shopify.com/s/files/1/0114/3016/6587/files/Talkingprints_NewLogo_Final-01_b4c93b19-4415-42a8-8458-e58ede2cb7d4.jpg',
    'taman-indah-resort': 'https://tamanindah.com/wp-content/uploads/2026/04/6307398004_8088be063f_o_4000x2200-1024x563.jpg',
    'tasty-fresh-food-coffee-bar': 'https://www.kirpalani.com/media/wysiwyg/Tasty/cafe_2.webp',
    'tbl-cinemas': 'https://www.tblcinemas.com/storage/backdrops/2TWIlmhE06ghspeQLEX1VmnEBiE.jpg',
    'teasee': 'https://socialsuriname.com/wp-content/uploads/2025/01/Teasee.webp',
    'telesur-centrum': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'telesur-latour': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'telesur-lelydorp': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'telesur-nickerie': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'telesur-noord': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'telesur-zonnebloemstraat': 'https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg',
    'the-beauty-bar': 'https://beautybar.sr/wp-content/uploads/2025/08/Heading-8-e1755791215726.webp',
    'the-beauty-bar-north': 'https://beautybar.sr/wp-content/uploads/2022/02/cropped-cropped-TheBeautyBar-logo_small_transparent-150x150-1.png',
    'the-beauty-bar-south': 'https://beautybar.sr/wp-content/uploads/2022/02/cropped-cropped-TheBeautyBar-logo_small_transparent-150x150-1.png',
    'the-coffee-box-north': 'https://cdn.prod.website-files.com/66fedd5a9fea532b66621c84/6725132133a6b0240068256a_Logo%20(cinderella).png',
    'the-maillard-cafe': 'https://socialsuriname.com/wp-content/uploads/2025/04/The-maillard-cafe-v1.webp',
    'the-rose-manor': 'https://socialsuriname.com/wp-content/uploads/2025/03/The-Rose-Manor.webp',
    'theater-thalia': 'https://theaterthalia.com/wp-content/uploads/2023/04/thalia-theater-suriname.jpg',
    'tianyou-aquafun': 'https://img.youtube.com/vi/cWIBzH1WVvQ/hqdefault.jpg',
    'timeless-barber-and-nail-shop': 'https://timelessbarbershop.sr/wp-content/uploads/2025/02/IMG_1731-768x1024.jpg',
    'tio-boto-eco-resort': 'https://www.tioboto.com/wp-content/uploads/2019/02/TBE25-1840x1200.jpg',
    'tipsy-bar-lounge': 'https://media.evendo.com/locations-resized/BarImages/1920x466/207591e3-ee80-416f-ae25-3a640f19674c',
    'tirzahs-patisserie': 'https://unitednews.sr/wp-content/uploads/2016/10/pattiesr.jpg',
    'tomahawk-outdoor-adventures': 'https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png',
    'tomahawk-outdoor-adventures-hermitage-mall': 'https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png',
    'tomahawk-outdoor-adventures-ims': 'https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png',
    'tomahawk-outdoor-adventures-lelydorp': 'https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png',
    'topslager-stolk': 'https://www.surinamyp.com/img/sr/d/_1683544328-83-stolk-slagerij-n-v-de-topslager.jpg',
    'topsport': 'https://socialsuriname.com/wp-content/uploads/2024/06/Topsport.webp',
    'torarica-resort': 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/The_Torarica_-_Paramaribo%2C_Suriname.jpg/1280px-The_Torarica_-_Paramaribo%2C_Suriname.jpg',
    'tropicana-hotel-casino-suriname': 'https://ak-d.tripcdn.com/images/200i0a0000004jxq769BE_R_960_660_R5_D.jpg',
    'tucan-resort-and-spa': 'https://tucanresidence.com/wp-content/uploads/duoble-room-scaled.jpg',
    'tulip-supermarket': 'https://www.surinamyp.com/img/sr/l/1683208614-24-tulip.jpg',
    'twins-pizza-burgers': 'https://socialsuriname.com/wp-content/uploads/2025/05/Twins-Pizza-Burgers-v1.webp',
    'uitkijk-riverlounge-cafe': 'https://socialsuriname.com/wp-content/uploads/2026/01/Uitkijk-RiverLounge-and-Cafe-v1.webp',
    'unlimited-suriname-tours': 'https://unlimitedsuriname.com/wp-content/uploads/2025/04/d3621001-7e23-426f-9ff7-d5256c918cfd.jpg',
    'vcm-slagerij-centrum': 'https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png',
    'vcm-slagerij-johannes-mungrastraat': 'https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png',
    'vcm-slagerij-verl-gemenelandsweg': 'https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png',
    'vifa-trading': 'https://socialsuriname.com/wp-content/uploads/2024/06/Vifa-Trading-v1.webp',
    'villa-famiri': 'https://www.villafamiri.com/wp-content/uploads/2023/04/FF6E67AF-3FEA-4518-A212-432AC27DB0C3_1_201_a-1-605x465.jpeg',
    'villa-zapakara': 'https://socialsuriname.com/wp-content/uploads/2024/06/Stichting-Villa-Zapakara.webp',
    'villas-paramaribo': 'https://villasparamaribo.com/wp-content/uploads/2025/01/b3d31ef4-1c33-4e72-8a26-1dbab5dcb6b7.jpg',
    'vincent-supermarket': 'https://socialsuriname.com/wp-content/uploads/2024/06/Vincent-Supermarket-v1.webp',
    'viva-mexico': 'https://socialsuriname.com/wp-content/uploads/2025/10/Viva-Mexico-v1.webp',
    'waldos-worldwide-travel-service': 'https://www.surinamyp.com/img/sr/e/_1683198923-21-waldo-s-world-wide-travel-service.jpg',
    'warung-resa-centrum': 'https://socialsuriname.com/wp-content/uploads/2024/06/Warung-Resa-v1.webp',
    'waterland-suites': 'https://waterlandsuites.com/wp-content/uploads/2021/08/20210729_171148-1.jpg',
    'welink-real-estate': 'https://welink.sr/wp-content/uploads/2024/11/1-1-850x550.jpeg',
    'wollys': 'http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg',
    'wollys-2': 'http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg',
    'wollys-3': 'http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg',
    'yokohama-trading': 'https://socialsuriname.com/wp-content/uploads/2024/06/Yokohama-Trading-NV-v1.webp',
    'zeelandia-suites': 'https://www.zeelandiasuites.sr/wp-content/uploads/2018/07/balcony-view.png',
    'zus-zo-cafe': 'https://www.zusenzosuriname.com/wp-content/uploads/2025/12/IMG_0310-scaled.jpeg',
    # Manually added
    'gateway-fire-nv':      'https://gatewayfirenv.com/wp-content/uploads/2025/06/a5-removebg-preview.png',
    'triple-security-unit': 'https://exploresuriname.com/images/triplesecurityunit.webp',
    'hurricane-steel':        'https://exploresuriname.com/images/Hurricanesteel.webp',
    'hurricane-steel-ringweg':'https://exploresuriname.com/images/Hurricanesteel.webp',
    'a-la-john': 'https://socialsuriname.com/wp-content/uploads/2024/06/A-La-John-v1.webp',
    'ac-bar-restaurant': 'https://socialsuriname.com/wp-content/uploads/2025/06/AC-Bar-Restaurant-v1.webp',
    'alegria': 'https://socialsuriname.com/wp-content/uploads/2025/06/Alegria-v3.webp',
    'apotheek-rafeka': 'https://socialsuriname.com/wp-content/uploads/2024/06/Apotheek-Rafeka-v1.webp',
    'balletschool-marlene': 'https://socialsuriname.com/wp-content/uploads/2025/10/Marlenes-Ballet-Company-viert-39-jaar-danskunst-in-Suriname.webp',
    'bar-zuid': 'https://socialsuriname.com/wp-content/uploads/2024/06/Bar-Zuid-v1.webp',
    'big-tex': 'https://socialsuriname.com/wp-content/uploads/2024/06/Big-Tex-BBQ.webp',
    'bori-tori': 'https://socialsuriname.com/wp-content/uploads/2024/06/Bori-Tori-v1.webp',
    'bright-cleaning': 'https://socialsuriname.com/wp-content/uploads/2024/06/Bright-Cleaning-scaled.webp',
    'byd-suriname': 'https://socialsuriname.com/wp-content/uploads/2024/08/BYD-Suriname-v1.webp',
    'car-rental-city': 'https://socialsuriname.com/wp-content/uploads/2024/06/car-rental-city-01-r623.webp',
    'carpe-diem-massagepraktijk': 'https://socialsuriname.com/wp-content/uploads/2025/03/Carpe-Diem-Massagepraktijk.webp',
    'chi-min': 'https://socialsuriname.com/wp-content/uploads/2024/06/chi-min-restaurant.webp',
    'de-verdieping': 'https://socialsuriname.com/wp-content/uploads/2024/06/De-Verdieping-v1.webp',
    'delete-beauty-lounge': 'https://socialsuriname.com/wp-content/uploads/2024/06/Delete-Beauty-Lounge-v2.webp',
    'dierenpoli-lobo': 'https://socialsuriname.com/wp-content/uploads/2026/04/dierenpoli-lobo-01-enfl.webp',
    'divergent-body-jewelry': 'https://socialsuriname.com/wp-content/uploads/2025/04/Divergent-Body-Jewelry.webp',
    'dj-liquor-store': 'https://socialsuriname.com/wp-content/uploads/2024/11/DJ-Liquor-Store.webp',
    'ec-operations': 'https://socialsuriname.com/wp-content/uploads/2025/05/EC-Operations.webp',
    'ekay-media': 'https://socialsuriname.com/wp-content/uploads/2024/11/Ekay-Media.webp',
    'elines-pizza': 'https://socialsuriname.com/wp-content/uploads/2024/06/Elines-Pizza-mini-pizzas.webp',
    'eucon': 'https://socialsuriname.com/wp-content/uploads/2024/06/EUCON.webp',
    'farma-vida': 'https://socialsuriname.com/wp-content/uploads/2025/10/Farma-Vida-v1.webp',
    'fatum': 'https://socialsuriname.com/wp-content/uploads/2025/06/Fatum-v1.webp',
    'from-me-to-me': 'https://socialsuriname.com/wp-content/uploads/2024/11/From-Me-To-Me-1.webp',
    'h-garden': 'https://socialsuriname.com/wp-content/uploads/2025/05/H-Garden-v2.webp',
    'hairstudio-32': 'https://socialsuriname.com/wp-content/uploads/2024/06/Hair-studio-32-1.webp',
    'hes-ds': 'https://socialsuriname.com/wp-content/uploads/2024/06/HES-Ds-scaled.webp',
    'huub-explorer-tours': 'https://socialsuriname.com/wp-content/uploads/2024/06/Huub-Explorer-Tours.webp',
    'ineffable': 'https://socialsuriname.com/wp-content/uploads/2024/06/Ineffable.webp',
    'inksane-tattoos': 'https://socialsuriname.com/wp-content/uploads/2024/08/Inksane-Tattoo.webp',
    'joey-ds': 'https://socialsuriname.com/wp-content/uploads/2024/06/Joey-Ds-v2.webp',
    'julias-food': 'https://socialsuriname.com/wp-content/uploads/2024/06/Julias-Food.webp',
    'kasan-snacks': 'https://socialsuriname.com/wp-content/uploads/2025/04/Kasan-Snacks.webp',
    'kempes-co': 'https://socialsuriname.com/wp-content/uploads/2024/06/Kempes-and-co-v1.webp',
    'mickis-palace-noord': 'https://socialsuriname.com/wp-content/uploads/2025/01/Mickis-Palace-Zuid.webp',
    'mickis-palace-zuid': 'https://socialsuriname.com/wp-content/uploads/2025/01/Mickis-Palace-Zuid.webp',
    'mokisa-wellness': 'https://socialsuriname.com/wp-content/uploads/2025/03/De-Harmonie-van-Traditionele-Marron-Geneeskunst-en-Moderne-Gezondheidszorg-scaled.webp',
    'moments-restaurant': 'https://socialsuriname.com/wp-content/uploads/2025/05/Moments-Restaurant-v1.webp',
    'mon-plaisir-nursery': 'https://socialsuriname.com/wp-content/uploads/2024/06/Mon-Plaisir-Nursery-v1.webp',
    'overdoughsed-suriname': 'https://socialsuriname.com/wp-content/uploads/2024/06/Overdoughsed.webp',
    'pane-e-vino': 'https://socialsuriname.com/wp-content/uploads/2024/06/Pane-E-Vino-v2.webp',
    'papillon-crafts': 'https://socialsuriname.com/wp-content/uploads/2024/10/Papillon-Crafts-v1.webp',
    'protrade-international': 'https://socialsuriname.com/wp-content/uploads/2024/06/Protrade-International-NV.webp',
    'recreatie-oord-carolina-kreek': 'https://socialsuriname.com/wp-content/uploads/2025/01/Carolinakreek.webp',
    'resourceful-real-estate-construction': 'https://socialsuriname.com/wp-content/uploads/2025/05/Resourceful-Real-Estate-Construction.webp',
    'rif-cleaning-service': 'https://socialsuriname.com/wp-content/uploads/2024/06/Rifgroup-nv-v1.webp',
    'ross-rental-cars': 'https://socialsuriname.com/wp-content/uploads/2024/06/Ross-Rental-Cars-v1.webp',
    'royal-spa': 'https://socialsuriname.com/wp-content/uploads/2024/06/Royal-spa.webp',
    'royal-wellness-lounge': 'https://socialsuriname.com/wp-content/uploads/2024/06/Royal-Wellness-Lounge-v1.webp',
    'sleeqe': 'https://socialsuriname.com/wp-content/uploads/2025/01/Sleeqe.webp',
    'smoothieskin': 'https://socialsuriname.com/wp-content/uploads/2024/10/SmoothieSkin-v1.webp',
    'souposo': 'https://socialsuriname.com/wp-content/uploads/2024/06/Souposo-v2.webp',
    'squeaky-clean': 'https://socialsuriname.com/wp-content/uploads/2024/12/Squeaky-Clean-N.V.webp',
    'stukaderen-in-nederland': 'https://socialsuriname.com/wp-content/uploads/2024/10/Stukaderen-in-Nederland.webp',
    'sushi-ya': 'https://socialsuriname.com/wp-content/uploads/2024/06/Sushi-Ya-v3.webp',
    'the-coffee-box': 'https://socialsuriname.com/wp-content/uploads/2024/06/The-Coffee-Box-Giftcards.webp',
    'the-old-attic': 'https://socialsuriname.com/wp-content/uploads/2025/05/The-Old-Attic-v1.webp',
    'the-uma-store': 'https://socialsuriname.com/wp-content/uploads/2024/06/The-Uma-Store.webp',
    'the-waxing-booth': 'https://socialsuriname.com/wp-content/uploads/2024/11/The-Waxing-Booth-and-More-by-SG.webp',
    'touch-of-heaven-wellness': 'https://socialsuriname.com/wp-content/uploads/2024/06/Touch-of-Heaven-Wellness-v1.webp',
    'tranquil-at-mamba-republiek': 'https://socialsuriname.com/wp-content/uploads/2025/08/Tranquil-at-Mamba-Republiek-v1.webp',
    'tsw-group': 'https://socialsuriname.com/wp-content/uploads/2025/07/TSW-Group-of-Companies-v1.webp',
    'unlocked-candles': 'https://socialsuriname.com/wp-content/uploads/2025/04/Unlocked-Candles-v2.webp',
    'yoga-peetha-happiness-centre': 'https://socialsuriname.com/wp-content/uploads/2024/06/Yoga-Peetha-Happiness-Centre.webp',
    'yogh-hospitality': 'https://socialsuriname.com/wp-content/uploads/2024/06/YOGH-Hospitality-1.webp',
    'zeepfabriek-joab': 'https://socialsuriname.com/wp-content/uploads/2024/06/JOAB-Global-NV-v1.webp',
    'zeg-ijsje': 'https://socialsuriname.com/wp-content/uploads/2025/04/Zeg-Ijsje-scaled.webp',
    'zenobia-bottling-company': 'https://socialsuriname.com/wp-content/uploads/2024/06/Zenobia-Bottling-Company.webp',
}



_F = {
    "hotel_lux":   "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&q=80",
    "hotel_eco":   "https://images.unsplash.com/photo-1596178065887-1198b6148b2b?w=800&q=80",
    "hotel_bou":   "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800&q=80",
    "hotel_gen":   "https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800&q=80",
    "restaurant":  "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80",
    "cafe":        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&q=80",
    "bar":         "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",
    "pizza":       "https://images.unsplash.com/photo-1513104890138-7c749659a591?w=800&q=80",
    "sushi":       "https://images.unsplash.com/photo-1617196034183-421b4040ed20?w=800&q=80",
    "food":        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800&q=80",
    "jungle":      "https://images.unsplash.com/photo-1564038406-d99ca4d96b8a?w=800&q=80",
    "river":       "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",    "museum":      "https://images.unsplash.com/photo-1575223970966-76ae61ee7838?w=800&q=80",
    "historical":  "https://images.unsplash.com/photo-1554232456-8727aae0cfa4?w=800&q=80",
    "mall":        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&q=80",
    "boutique":    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=80",
    "jewelry":     "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800&q=80",
    "candles":     "https://images.unsplash.com/photo-1603905462088-6a8dd77cddc5?w=800&q=80",
    "crafts":      "https://images.unsplash.com/photo-1561136594-7f68413baa99?w=800&q=80",
    "liquor":      "https://images.unsplash.com/photo-1586899028174-e7098604235b?w=800&q=80",    "skincare":    "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=800&q=80",
    "spa":         "https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800&q=80",
    "hair":        "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=800&q=80",
    "barber":      "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=800&q=80",
    "fitness":     "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=800&q=80",
    "tattoo":      "https://images.unsplash.com/photo-1607346705504-2558edcbb9d9?w=800&q=80",
    "yoga":        "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=800&q=80",
    "beauty":      "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=800&q=80",
    "airline":     "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80",
    "tech":        "https://images.unsplash.com/photo-1461749280684-dccba630e2f6?w=800&q=80",
    "media":       "https://images.unsplash.com/photo-1526961718745-8b79e5dc7e14?w=800&q=80",
    "travel":      "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80",
    "finance":     "https://images.unsplash.com/photo-1554224155-6726b3ff858f?w=800&q=80",
    "massage":     "https://images.unsplash.com/photo-1600334129128-685c5582fd35?w=800&q=80",
    "wellness":    "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=800&q=80",
    "services":    "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=800&q=80",
    "construction":"https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=800&q=80",
}

def _biz_img(slug):
    return _IMGS.get(slug, "")

# ── Subcategory assignment ────────────────────────────────────────────────────
def _subcat(slug, main_cat=""):
    s = slug.lower()
    # Eat & Drink
    if any(x in s for x in ['kfc','burger-king','mcdonalds','popeyes','pizza-hut','subway',
            'sranan-fowru','naskip','habco','boss-burgers','twins-pizza','wollys',
            'ricos','cinnagirl','goldenwings','dlish','lucky-twins','murphys',
            'frygri','kriegslist','chuck-e','monster']):
        return 'fast-food'
    if any(x in s for x in ['coffee','cafe','moka','matcha','teasee','maillard',
            'three-little-beans','coffee-hobbyist','cy-coffee','coffee-mama',
            'numa-cafe','sweetie-coffee','tasty-fresh','aaras','cy-coffee',
            'jage-caffe','dolce','blue-grand','new-suriname-dream','samba']):
        return 'cafes-coffee'
    # Beauty/wellness with 'lounge' or 'salon' in name must come BEFORE bars-lounges check
    if any(x in s for x in ['beauty-lounge','wellness-lounge','brow-bliss','shimmery',
            'scene-beauty','delete-beauty','royal-wellness','luxe-escape']):
        return 'beauty-wellness'
    if any(x in s for x in ['bar-qle','tipsy','georgies','uitkijk','d-mighty',
            'riverloun','murphys','de-spot','de-verdieping','lobby','alegria',
            'bar-zu','mr-bar','bar-nord','ace-restaurant-lounge','ayo-river-lounge']):
        return 'bars-lounges'
    if any(x in s for x in ['sushi','korean','japanese','teppanyaki','kwan-tai',
            'kong-nam','kyu-pho','norrii','ogi-','mingle-sushi','south-america-hot',
            'squeezy-hot','lees-korean','chi-min','han-palace','sakura',
            'ket-mien','kushiyaki','olive']):
        return 'asian-fusion'
    if any(x in s for x in ['roti','warung','baka-foto','joosje','ritas','sendang',
            'roopram','oasis','eethuis','kasan','la-s','restoran-bibit',
            'tori-oso','okopipi','petisco','leiding-1','rolines','de-waag',
            'restaurant-sarinah','sranan']):
        return 'local-caribbean'
    if any(x in s for x in ['bakery','patisserie','tirzahs','overdough','wing-hung',
            'u-s-bakery','bakery-house','the-sweetest','sweet-tooth','cookie-closet',
            'cup-cake','cupcake','croissant','zeg-ijsje','pannekoek',
            'tirzah','tout-tout','the-girl-house']):
        return 'bakeries-sweets'
    if any(x in s for x in ['pizza','pasta','italian','padre','bella-italia','ettores',
            'pane-e-vino','pizza-mafia','bingo-pizza','sizzler']):
        return 'pizza-italian'
    # Hotels
    if any(x in s for x in ['eco','nature-resort','river-lodge','jungle','kabalebo',
            'danpaati','anaula','knini','kimboto','tioboto','tapawatra',
            'afobaka','akira','overbridge','kodouffi']):
        return 'eco-lodges'
    if any(x in s for x in ['casino','tropicana','atlantis','savannah-casino',
            'paramaribo-princess','mirage','suriname-princess']):
        return 'casino-hotels'
    if any(x in s for x in ['guesthouse','villa-','villas-','appartment','apartment',
            'tiny-house','waterland','bronbella','residence-inn','zeelandia-suite',
            'royal-breeze','yogh']):
        return 'guesthouses'
    # Activities
    if any(x in s for x in ['tour','tours','travel-service','folo','mondowa','pineapple',
            'tomahawk','no-span','jack-tour','jenny-tour','messias','royal-tours',
            'suran','okido','wayfinder','huub','unlimited-suriname','free-city-walk',
            'access-suriname','satyam','multi-travel','augis','waldos','jack-tours']):
        return 'tours-expeditions'
    if any(x in s for x in ['museum','heritage','historic','fort-zeeland','joden',
            'plantage','koto-museum','stichting-surinaams','readytex-art',
            'conservatorium','alliance-francaise','museum-bakkie','ford-zeeland']):
        return 'museums-heritage'
    if any(x in s for x in ['zoo','cinema','theater','thalia','tbl-cinema','tianyou',
            'golf-club','clevia','oase','padel','dansclub','balance-studio',
            'paramaribo-zoo','invictus','outdoor-living']):
        return 'entertainment'
    if 'fish-finder' in s:
        return 'other'
    if any(x in s for x in ['peperpot','brownsberg','nature-park','colakreek',
            'carolina-kreek','recreatie-oord','afobaka','bigi-pan','galibi']):
        return 'nature-parks'
    # Shopping
    if any(x in s for x in ['supermarkt','supermarket','chois','kaki','lins-super',
            'vincent-super','tulip-super','mimi-market','gao-ming','best-mart','kasimex',
            'vincent-supermarket','lins-super-market']):
        return 'supermarkets'
    if any(x in s for x in ['mall','combe-markt','combe-bazaar','beyrouth-bazaar',
            'soengngie-mega','hermitage-mall','ims-mall','amada-shopping',
            'boekhandel','sanousch']):
        return 'malls-markets'
    if any(x in s for x in ['fashion','shoe','footcandy','shoebizz','dresscode',
            'dojo-couture','sash-fashion','steps-','janelles',
            'crocs-','chm-','miniso','ochama','itrendzz','flex-luxuries',
            'everything-sr','x-avenue','lucky-store']):
        return 'fashion-clothing'
    if any(x in s for x in ['digital-world','computronics','flex-phones','computer-hardware',
            'ring-ring','vifa-trading','yokohama-trading']):
        return 'electronics'
    if any(x in s for x in ['furniture','ashley-furniture','randoe-meubelen',
            'building-depot','sleepstore','holiday-home','randoe','outdoor-living',
            'morevans','galaxyliving']):
        return 'home-furniture'
    if any(x in s for x in ['optiek','instyle-optic','chees-jewelry','chique-eyewear']):
        return 'optical-jewelry'
    if any(x in s for x in ['slagerij','topslager','vcm-slager','keurslager',
            'hollandia-bakkerij','rossignol',
            'office-world']):
        return 'food-specialty'
    # da-drogist and alis-drugstore: drugstores → health-beauty chip in Shopping
    if any(x in s for x in ['da-drogist', 'alis-drugstore', 'one-stop-apotheek']):
        return 'health-beauty'
    # Services subcategories
    if any(x in s for x in ['bank','hakrinbank','republic-bank','finabank',
            'surinaamsche-bank','scombank','southern-commercial']):
        return 'banking'
    if any(x in s for x in ['assuria','fatum-schade','insurance','verzekering']):
        return 'insurance'
    if any(x in s for x in ['apotheek','drugstore','pharmacie','farma','medical',
            'dierenarts','dierenpoli','faraya','first-aid','health','clinic',
            'da-select','one-stop-apotheek','alis-drugstore']):
        return 'health-pharmacy'
    if any(x in s for x in ['telesur','digicel','telecom','smart-connexxionz',
            'digital-world','energiebedrijven','ebs','swm','ebs-','zenobia']):
        return 'telecom-utilities'
    if any(x in s for x in ['school','universiteit','university','college','atheneum',
            'lyceum','academy','institute','conservatorium','fhr-lim','ias-wooden',
            'nassy-brouwer','de-vrije-school','arthur-alex','qsi-international',
            'lim-a-po','international-academy','young-engineers','balletschool']):
        return 'education'
    if any(x in s for x in ['gym','fitness','yoga','pilates','sport','wellness',
            '4r-gym','north-fitness','pitbull-fitness','rock-fitness','fit-factory',
            'real-one-fitness','body-enhancement','cpr-pilates','topsport',
            'the-aerial','invictus','kaizen','fluxo','glam-curves','miss-doll-fit']):
        return 'fitness-wellness'
    if any(x in s for x in ['beauty','salon','hair','nail','barber','wax','lash','brow',
            'spa','massage','tattoo','piercing','skincare','rich-skin','the-beauty-bar',
            'bloom-wellness','carpe-diem','stichting-shiatsu','royal-spa','royal-rose',
            'delete-beauty','hairstudio','lashlift','lioness','timeless-barber',
            'thermen','inksane','gaby-april','scene-beauty','touch-of-heaven',
            'percy-massage','tranquil','luxe-escape','shimmery','blissful',
            'brow-bliss','sthephany','house-of-pureness','curl-babes','just-curlss',
            'organic-skincare','ying-hao','cynsational','iamchede','glambox',
            'gossip-nails','glam-curves','ayur-mi','mokisa-wellness','mini-nail',
            'the-nail-house','the-basement-barber','hsds-lifestyle','clarissa-vaseur',
            'pinkmoon','smoothieskin','honeycare']):
        return 'beauty-wellness'
    if any(x in s for x in ['real-estate','vastgoed','makelaardij','property','remy',
            'welink','101-real-estate','keller-williams','re-max','surgoed',
            'dor-property','resourceful','intervast']):
        return 'real-estate'
    if any(x in s for x in ['cleaning','laundry','bright-cleaning','abrix-cleaning',
            'rif-cleaning','djo-cleaning','jamilas-dry','the-laundry','squeaky',
            'dream-clean','clean-it']):
        return 'cleaning-maintenance'
    if any(x in s for x in ['security','brotherhood-security','professional-private',
            'safety-first']):
        return 'security'
    if any(x in s for x in ['travel','airline','car-rental','hertz','dcars','ross-rental',
            'fly-allways','surinam-airways','klm','digicel','augis','multi-travel',
            'waldos','jack-tours','jenny-tour','access-suriname','satyam',
            'okido-tours','royal-tours','dli-travel']):
        return 'travel-transport'
    if any(x in s for x in ['media','tech','digital','eaglemedia','ekay-media','bitdynamics',
            'seen-stories','computer','typing-nomad','djinipi','creativing',
            'eucon','tsw','printing','creative-q']):
        return 'tech-media'
    if any(x in s for x in ['notariaat','notary','law','legal','marchand','mannes',
            'van-dijk','accountant']):
        return 'legal-professional'
    if any(x in s for x in ['car','auto','bmw','byd','great-wall','garage','carvision',
            'hertz','dcars','ross-rental','car-rental']):
        return 'automotive'
    # -- Additional categorisations (reduces 'other' bucket) --
    if any(x in s for x in ['muntjes-take-out','tastelicious']):
        return 'fast-food'
    if any(x in s for x in ['brahma-centrum','brahma-noord','brahma-zuid']):
        return 'health-pharmacy'
    if any(x in s for x in ['jjs-place','nr-1-spot','tapauku-terras','petit-bouchon','le-den','talula','h-t']):
        return 'bars-lounges'
    if any(x in s for x in ['karans-indian','maharaja-palace','raja-ji','spice-quest','mezze-suriname']):
        return 'asian-fusion'
    if 'viva-mexico' in s:
        return 'local-caribbean'
    if any(x in s for x in ['mandy-butka','the-rose-manor','ciranos','orchid','maze',
            'the-perfume-spot','handmade-by-farrell']):
        return 'beauty-wellness'
    if any(x in s for x in ['free-flow','savage-den']):
        return 'fitness-wellness'
    if any(x in s for x in ['sugar','from-kay-with-love','holy-moly']):
        return 'bakeries-sweets'
    if 'sweetheart-ims' in s or 'sweetheart-hermitage' in s:
        return 'food-specialty'
    if any(x in s for x in ['max-n-co','eterno','cute-as-a-button',
            'new-choice','surimami-store','wow-plus',
            'mn-international','pandie']):
        return 'fashion-clothing'
    if 'toys-n-more' in s:
        return 'other'
    if 'krioro' in s:
        return 'fast-food'
    if any(x in s for x in ['waterleiding','sun-ice']):
        return 'telecom-utilities'
    if any(x in s for x in ['ec-operations','infinity-holding','threefold','protrade',
            'supply-solutions','freelance-scout','ondernemershuis','camex',
            'kempes-co','mokisa-busidataa','stukaderen','secas','harry-tjin']):
        return 'legal-professional'
    if 'dhl-express' in s:
        return 'travel-transport'
    if s == 'fatum':
        return 'insurance'
    if any(x in s for x in ['red-century','happy-flower']):
        return 'events-party'
    if 'de-spetter' in s:
        return 'entertainment'
    if any(x in s for x in ['nursery','ladybug','mon-plaisir','grounded-botanical']):
        return 'nursery-garden'
    if any(x in s for x in ['hes-ds','warehouse-shop']):
        return 'home-furniture'
    if 'brilleman' in s:
        return 'optical-jewelry'
    if 'wonderlab' in s:
        return 'education'
    # ── Restaurant catch-ups ────────────────────────────────────────────────
    if any(x in s for x in ['goe-thai','etembe']):
        return 'asian-fusion'
    if any(x in s for x in ['ac-bar','mingle-paramaribo','passion-food','bistro-brwni',
            'bistro-don-julio','bistro-lequatorze','lamour']):
        return 'bars-lounges'
    if any(x in s for x in ['a-la-john','big-tex','bori-tori','de-gadri','el-patron',
            'garden-of-eden','joey-ds','julias-food','las-tias','mickis-palace',
            'moments-restaurant','rogom-farm','souposo','flavor-restaurant',
            'restaurant-lhermitage']):
        return 'local-caribbean'
    # ── Beauty/lounge name conflicts — must come after bars-lounges block ───
    if any(x in s for x in ['beauty-lounge','wellness-lounge','brow-bliss','shimmery',
            'scene-beauty','delete-beauty','royal-wellness','luxe-escape']):
        return 'beauty-wellness'
    # ── Hotels: standard/boutique catch-all ────────────────────────────────
    if any(x in s for x in ['royal-torarica','royal-brasil','courtyard','radisson',
            'torarica-resort','holland-lodge','hotel-north',
            'the-golden-truly','oxygen-resort','taman-indah','greenheart-boutique',
            'tucan-resort']):
        return 'city-hotels'
    if any(x in s for x in ['hotel-palacio']):
        return 'guesthouses'
    if any(x in s for x in ['hotel-peperpot','houttuyn','jacana-amazon']):
        return 'eco-lodges'
    # ── Shopping: catch-ups ─────────────────────────────────────────────────
    if any(x in s for x in ['kirpalani','soengngie-mega','soengngie-oriental',
            'deto-handel','amada-shopping']):
        return 'malls-markets'
    if any(x in s for x in ['shlx','sleeqe','from-me-to-me','the-uma-store',
            'lilis','nv-zing']):
        return 'fashion-clothing'
    if any(x in s for x in ['divergent-body','bed-bath','galaxy']):
        return 'home-furniture'
    if any(x in s for x in ['papillon-crafts','readytex-souvenir','switi-momenti',
            'talking-prints','woodwonders','zeepfabriek','unlocked-candles',
            'the-old-attic','h-garden']):
        return 'crafts-souvenirs'
    if any(x in s for x in ['dj-liquor','golderom-healthy']):
        return 'food-specialty'
    # ── Services: remaining catch-ups ──────────────────────────────────────
    if any(x in s for x in ['4x4-rental','ross-rental','car-rental-city']):
        return 'travel-transport'
    if any(x in s for x in ['kasco-custom','kasco-customs']):
        return 'tech-media'
    if any(x in s for x in ['suraniyat']):
        return 'crafts-souvenirs'
    if 'smoothieskin' in s or 'honeycare' in s:
        return 'beauty-wellness'
    if 'r-k-bisdom' in s:
        return 'museums-heritage'
    # ── Nature/sightseeing: slug uses hyphens ──────────────────────────────
    if 'cola-kreek' in s:
        return 'nature-parks'
    if '9173' in s:
        return 'supermarkets'
    # Manually added slugs
    if 'gateway-fire' in s:
        return 'security'
    if 'dans-dip' in s:
        return 'automotive'
    if 'hurricane-steel' in s:
        return 'home-furniture'
    return 'other'

# Subcategory display config: cat → [ (key, label, emoji) ]
SUBCATS = {
    "restaurant": [
        ("all",           "All",              "🍽️"),
        ("fast-food",     "Fast Food",         "🍔"),
        ("cafes-coffee",  "Cafés & Coffee",    "☕"),
        ("bars-lounges",  "Bars & Lounges",    "🍹"),
        ("asian-fusion",  "Asian & Fusion",    "🥢"),
        ("local-caribbean","Local & Caribbean","🌿"),
        ("pizza-italian", "Pizza & Italian",   "🍕"),
        ("bakeries-sweets","Bakeries & Sweets","🍰"),
        ("restaurants",   "Restaurants",       "🍴"),
    ],
    "hotel": [
        ("all",          "All",               "🏨"),
        ("city-hotels",  "City Hotels",       "🏙️"),
        ("resorts",      "Resorts",            "🏊"),
        ("casino-hotels","Casino Hotels",     "🎰"),
        ("eco-lodges",   "Eco & River Lodges","🌿"),
        ("guesthouses",  "Guesthouses & Villas","🏡"),
    ],
    "adventure": [
        ("all",             "All",             "🌍"),
        ("tours-expeditions","Tours & Expeditions","🧭"),
        ("eco-lodges",      "Eco & River Lodges","🌿"),
        ("nature-parks",    "Nature & Parks",  "🦜"),
        ("museums-heritage","Museums & Heritage","🏛️"),
        ("entertainment",   "Entertainment",   "🎭"),
    ],
    "sightseeing": [
        ("all",             "All",             "🗺️"),
        ("museums-heritage","Museums & Heritage","🏛️"),
        ("nature-parks",    "Nature & Parks",  "🌿"),
        ("entertainment",   "Entertainment",   "🎭"),
        ("tours-expeditions","Tours",          "🧭"),
        ("other",           "Other",           "🔧"),
    ],
    "shopping": [
        ("all",           "All",              "🛍️"),
        ("malls-markets", "Malls & Markets",  "🏬"),
        ("supermarkets",  "Supermarkets",     "🛒"),
        ("fashion-clothing","Fashion & Shoes","👗"),
        ("electronics",   "Electronics",      "📱"),
        ("home-furniture","Home & Furniture", "🛋️"),
        ("food-specialty","Food & Specialty", "🥩"),
        ("optical-jewelry","Optical & Jewelry","👓"),
        ("crafts-souvenirs","Crafts & Souvenirs","🎨"),
        ("events-party",  "Events & Parties", "🎉"),
        ("nursery-garden","Nursery & Garden",  "🌱"),
        ("health-beauty", "Health & Beauty",    "🧴"),
    ],
    "service": [
        ("all",               "All",              "⚡"),
        ("beauty-wellness",   "Beauty & Wellness","💄"),
        ("fitness-wellness",  "Fitness",          "💪"),
        ("health-pharmacy",   "Health & Pharmacy","💊"),
        ("banking",           "Banking",          "🏦"),
        ("insurance",         "Insurance",        "🛡️"),
        ("telecom-utilities", "Telecom & Utilities","📡"),
        ("travel-transport",  "Travel & Transport","✈️"),
        ("real-estate",       "Real Estate",      "🏠"),
        ("education",         "Education",        "🎓"),
        ("tech-media",        "Tech & Media",     "💻"),
        ("cleaning-maintenance","Cleaning",       "🧹"),
        ("automotive",        "Automotive",       "🚗"),
        ("legal-professional","Legal & Professional","⚖️"),
        ("events-party",      "Events & Parties", "🎉"),
        ("nursery-garden",    "Nursery & Garden",  "🌱"),
        ("other",             "Other",             "🔧"),
    ],
}


def _make_biz(slug):
    b = _BIZ.get(slug)
    if not b: return None
    # Foursquare cache fills gaps for any fields still missing
    fsq = _FSQ.get(slug, {})
    _fdet = _FSQ_DETAILS.get(slug, {})
    # Priority: JSON (already has curated _BIZ data merged in) > Foursquare
    return {"slug": slug, "name": b["name"], "area": b.get("location", "Suriname"),
            "address":     b.get("address")     or fsq.get("address") or "",
            "phone":       b.get("phone")       or fsq.get("phone")   or "",
            "email":       b.get("email", ""),
            "website":     b.get("website")     or fsq.get("website") or "",
            "category":    b.get("category", ""),
            "description": b.get("description", ""),
            "url": f"listing/{slug}/",
            "external_url": _biz_url(b),
            "image": _biz_img(slug) or _fdet.get("photo_url", ""),
            "subcat": _subcat(slug)}

RESTAURANTS = [b for slug in ["a-la-john","aaras-cafe","ac-bar-restaurant","ace-restaurant-lounge","ayo-river-lounge","baka-foto-restaurant","bar-qle","bar-zuid","bella-italia","big-tex","bingo-pizza-coppename","bingo-pizza-kwatta","bistro-brwni","bistro-don-julio","bistro-lequatorze","bloom-wellness-cafe","blue-grand-cafe","bori-tori","boss-burgers","burger-king-centrum","burger-king-latour","chi-min","chuck-e-cheese","cinnagirl","coffee-mama","cookie-closet","cupcake-fantasy","cy-coffee","d-mighty-view-lounge","de-gadri","de-spot","de-verdieping","dlish","dolce-bella-cafe","eethuis-liv","el-patron-latin-grill","elines-pizza","etembe-rainforest-restaurant","ettores-pizza-kitchen","flavor-restaurant","from-kay-with-love","frygri","garden-of-eden","georgies-bar-chill","goe-thai-noodle-bar","goldenwings","habco-delight","habco-delight-north","han-palace","hard-rock-cafe-suriname","holy-moly","jadore-cafe-grill","jage-caffe","jage-caffe-2","joey-ds","joosje-roti-shop","julias-food","karans-indian-food","kfc-ims","kfc-kwatta","kfc-lallarookh","kfc-latour","kfc-lelydorp","kfc-waterkant","kfc-wilhelminastraat","kong-nam-snack","krioro","krioro-north","kushiyaki-the-next-episode","kwan-tai-restaurant","kwan-tai-restaurant-2","kyu-pho-grill","lamour-restaurant","las-tias","lees-korean-grill","leiding-1-restaurant","lucky-twins-restaurant","maharaja-palace","matcha-loft","mcdonalds-centrum","mcdonalds-hermitage-mall","mezze-suriname","mickis-palace-noord","mickis-palace-zuid","mighty-racks","mingle-paramaribo","mingle-sushi","moka-coffeebar","moments-restaurant","muntjes-take-out-juniors-place","murphys-irish-pub","naskip","naskip-2","naskip-3","naskip-4","naskip-5","new-suriname-dream-cafe","norrii-zushii","nr-1-spot","numa-cafe","oasis-restaurant","ogi-teppanyaki-sushi-bar","okopipi-tropical-grill","olive-multi-cuisine-restaurant","overdoughsed-suriname","padre-nostro-italian-restaurant","pane-e-vino","pannekoek-en-poffertjes-cafe","passion-food-and-wines","petisco-restaurant","petit-bouchon","pizza-hut-leysweg","pizza-hut-south","pizza-hut-wilhelminastraat","pizza-mafia","popeyes-centrum","popeyes-lelydorp","popeyes-tbl","popeyes-wilhelminastraat","raja-ji","restaurant-lhermitage","restaurant-sarinah","restoran-bibit","ricos-a-gladiator-foodtruck","ritas-roti-shop","rogom-farm-nv","rolines-de-waag","roopram-roti-shop","sakura","samba-cafe","saras-brunch-cafe","sizzler-midnight-grill","sizzlers-signature","souposo","south-america-hot-pot","spice-quest","squeezy-hot-pot-restaurant","subway","subway-2","subway-3","sugar","sushi-ya","sweet-tooth-pastries","sweetie-coffee","talula","tapauku-terras","tastelicious","tasty-fresh-food-coffee-bar","teasee","the-bakery-house","the-coffee-box","the-coffee-box-north","the-coffee-hobbyist","the-girl-house","the-maillard-cafe","the-old-garage","the-sweetest-thing","three-little-beans","tipsy-bar-lounge","tirzahs-patisserie","tori-oso","tout-tout-petit","twins-pizza-burgers","u-s-bakery","uitkijk-riverlounge-cafe","viva-mexico","warung-resa-centrum","warung-soepy-ann","wollys","wollys-2","wollys-3","zeg-ijsje","zus-zo-cafe"] for b in [_make_biz(slug)] if b]

HOTELS = [b for slug in ["bronbella-villa-residence","courtyard-by-marriott","eco-resort-miano","eco-torarica","holland-lodge","hotel-palacio","hotel-peperpot","houttuyn-wellness-river-resort","jacana-amazon-wellness-resort","oxygen-resort","royal-brasil-hotel","royal-breeze-hotel-paramaribo","royal-torarica","taman-indah-resort","the-golden-truly-hotel","tiny-house-tropical-appartment","torarica-resort","villa-famiri","waterland-suites","zeelandia-suites","anaula-nature-resort","atlantis-hotel-casino","danpaati-river-lodge","greenheart-boutique-hotel","guesthouse-albergoalberga","guesthouse-albina","hotel-north-resort","kabalebo-nature-resort","kimboto","marina-resort-waterland","overbridge-river-resort","radisson-hotel","ramada-paramaribo-princess","residence-inn-nickerie","residence-inn-paramaribo","savannah-casino-hotel","tropicana-hotel-casino-suriname","tucan-resort-and-spa","villa-zapakara","villas-paramaribo"] for b in [_make_biz(slug)] if b]

SIGHTSEEING = [b for slug in ["cola-kreek-recreatiepark","conservatorium-suriname","ford-zeelandia","golf-club-paramaribo","het-koto-museum","joden-savanne","museum-bakkie","paramaribo-zoo","peperpot-nature-park","plantage-frederiksdorp","r-k-bisdom-paramaribo","readytex-art-gallery","stichting-surinaams-museum","tbl-cinemas","theater-thalia"] for b in [_make_biz(slug)] if b]

ADVENTURES_BIZ = [b for slug in ["afobaka-resort","akira-overwater-resort","clevia-park","folo-nature-tours","free-city-walk-paramaribo","huub-explorer-tours","jack-tours-travel-service","jenny-tours","knini-paati","kodouffi-tapawatra-resort","messias-tours","mondowa-tours","no-span-eco-tours","okido-tours-travel","outdoor-living","pineapple-tours","recreatie-oord-carolina-kreek","royal-tours-suriname-guyana","sendang-redjo","suran-adventures-tours-travel","tio-boto-eco-resort","tomahawk-outdoor-adventures","tomahawk-outdoor-adventures-hermitage-mall","tomahawk-outdoor-adventures-ims","tomahawk-outdoor-adventures-lelydorp","unlimited-suriname-tours","wayfinders-exclusive-n-v"] for b in [_make_biz(slug)] if b]

SHOPPING = [b for slug in ["9173","amada-shopping","ashley-furniture-homestore","auto-style-franchepanestraat","auto-style-johannes-mungrastraat","auto-style-kwatta","auto-style-tweede-rijweg","auto-style-verlengde-gemenelandsweg","bed-bath-more-bbm","best-mart","beyrouth-bazaar","boekhandel-kasco","boekhandel-vaco","building-depot","chees-jewelry-watches","chm-centrum","chm-commewijne","chm-kernkampweg","chm-nickerie","chm-wanica","chm-wilhelminastraat","chm-wilhelminastraat-2","chois-supermarkt","chois-supermarkt-lelydorp","chois-supermarkt-north","combe-bazaar","combe-markt","computer-hardware-services","computronics-north","computronics-south","crocs-ims","da-drogisterij-coppename","da-drogisterij-hermitage","da-drogisterij-ims-mall","da-drogisterij-lelydorp","da-drogisterij-wilhelmina","de-keurslager-interfarm","deto-handelmaatschappij","digital-world-hermitage-mall","digital-world-ims","digital-world-maretraite-mall","digital-world-maretraite-mall-2","divergent-body-jewelry","dj-liquor-store","dojo-couture-hermitage-mall","fish-finder-fishing-and-outdoors","flex-phones","footcandy-hermitage-mall","from-me-to-me","furniture-city-kwatta","furniture-city-north","galaxy","gao-ming-trading-north","gao-ming-trading-south","golderom-healthy-organic-store","h-garden","hermitage-mall","holiday-home-decor","hollandia-bakkerij-north","hollandia-bakkerij-south","honeycare","hurricane-steel","hurricane-steel-ringweg","international-mall-of-suriname","janelles-shoes-and-bags","kaki-supermarkt","kirpalani","kirpalani-domineestraat","kirpalani-maagdenstraat","kirpalani-super-store","ladybug-nursery-and-garden-center","lilis","lins-super-market","lucky-store","mimi-market","miniso-gompertstraat","miniso-hermitage-mall","mon-plaisir-nursery","morevans-outlet","nv-zing-manufacturing","ochama-amazing","ochama-hermitage-mall","office-world-hermitage-mall","office-world-lelydorp","optiek-all-vision","optiek-all-vision-albina","optiek-all-vision-lelydorp","optiek-all-vision-nickerie","optiek-marisa","optiek-ninon","optiek-ninon-hermitage-mall","optiek-ninon-ims","optiek-ninon-lelydorp","optiek-ninon-meerzorg","optiek-ninon-nickerie","papillon-crafts","randoe-meubelen","readytex-souvenirs-and-crafts","red-century-party-shop-commewijne","red-century-party-shop-kwatta","red-century-party-shop-lelydorp","red-century-party-shop-north","red-century-party-shop-zorg-en-hoop","ring-ring-imports","rossignol-2go-kwattaweg","rossignol-2go-thurkowstraat","rossignol-coppename","rossignol-geyersvlijt","rossignol-linda","rossignol-waaldijkstraat","sanousch-books","sash-fashion-hermitage-mall","shlx-collection","shoebizz-ims","slagerij-abbas","slagerij-asruf","slagerij-stolk","sleepstore-suriname","sleeqe","smoothieskin","soengngie-mega-store","soengngie-oriental-market","sranan-fowru","sranan-fowru-boni","sranan-fowru-combe","sranan-fowru-flu","sranan-fowru-leiding","sranan-fowru-lelydorp","sranan-fowru-meursweg","sranan-fowru-tabiki-fowru","sranan-fowru-tourtonne","sranan-fowru-zinnia","steps-hermitage-mall","store4u","suraniyat","sweetheart-hermitage-mall","sweetheart-ims","switi-momenti-candles-crafts","talking-prints-concept-store","the-old-attic","the-perfume-spot","the-uma-store","the-warehouse-shop","topslager-stolk","toys-n-more","tulip-supermarket","unlocked-candles","vcm-slagerij-centrum","vcm-slagerij-johannes-mungrastraat","vcm-slagerij-verl-gemenelandsweg","vifa-trading","vincent-supermarket","woodwonders-suriname","yokohama-trading","zeepfabriek-joab","ket-mien","kasan-snacks","wing-hung-cake-shop","dojo-couture-centrum","dojo-couture-ims","steps-domineestraat","steps-noord","steps-wanica","honeycare-north","honeycare-south"] for b in [_make_biz(slug)] if b]

SERVICES = [b for slug in ["101-real-estate","4r-gym","4x4-rental","abrix-cleaning-services","access-suriname-travel","alegria","alis-drugstore","alliance-francaise","anton-de-kom-universiteit-van-suriname","apotheek-joemmanbaks","apotheek-karis","apotheek-mac-donald-north","apotheek-mac-donald-south","apotheek-rafeka","apotheek-sibilo","apotheek-soma","apotheek-soma-ringweg","arthur-alex-hoogendoorn-atheneum","assuria-hermitage-high-rise","assuria-insurance-walk-in-city","assuria-insurance-walk-in-commewijne","assuria-insurance-walk-in-lelydorp","assuria-insurance-walk-in-nickerie","assuria-insurance-walk-in-noord","augis-travel","ayur-mi-beauty-wellness","balance-studio","balletschool-marlene","bitdynamics","blissful-massage-aromatherapy","blossom-beauty-bar","bmw-suriname","body-enhancement-gym","brahma-centrum","brahma-noord","brahma-zuid","bright-cleaning","brilleman","brotherhood-security","brow-bliss-lounge","buro-workspaces","byd-suriname","camex-suriname","car-rental-city","carline-kwatta","carline-waaldijkstraat","carpe-diem-massagepraktijk","carvision-paramaribo","chique-eyewear-fashion","ciranos","clarissa-vaseur-writing-wellness-services-claw","clean-it","club-oase","cpr-pilates-curves","creative-q","curl-babes","cute-as-a-button","cynsational-glam","da-select-en-service-apotheek","dans-dip-and-detail","dansclub-danzson","dcars-rental","de-cederboom-school","de-nederlandse-basisschool-het-kleurenorkest","de-spetter","de-surinaamsche-bank-hermitage-mall","de-surinaamsche-bank-hoofdkantoor","de-surinaamsche-bank-lelydorp","de-surinaamsche-bank-ma-retraite","de-surinaamsche-bank-ma-retraite-2","de-surinaamsche-bank-nickerie","de-surinaamsche-bank-nickerie-2","de-surinaamsche-bank-nieuwe-haven","de-vrije-school","delete-beauty-lounge","dhl-express-service-point","dierenarts-resopawiro","dierenartspraktijk-l-m-bansse-issa","dierenpoli-lobo","digicel-albina","digicel-business-center","digicel-extacy","digicel-hermitage","digicel-latour","digicel-lelydorp","digicel-nickerie","digicel-wilhelminastraat","djinipi-copy-center","djo-cleaning-service","dli-travel-consultancy","dor-property-management-services-n-v","dream-clean-suriname","dresscode","eaglemedia","ec-operations","ekay-media","energiebedrijven-suriname-ebs","eterno","eucon","everything-sr","faraya-medical-center","farma-vida","fatum","fatum-schadeverzekering-commewijne","fatum-schadeverzekering-hoofdkantoor","fatum-schadeverzekering-kwatta","fatum-schadeverzekering-nickerie","fhr-lim-a-po-institute-for-higher-education","finabank-centrum","finabank-nickerie","finabank-noord","finabank-wanica","finabank-zuid","first-aid-plus","fit-factory","flex-luxuries","fluxo-pilates","fly-allways","free-flow","gaby-april-beauty-clinic","galaxyliving","garage-d-a-ashruf","gateway-fire-nv","glam-curves","glambox","gossip-nails-xx","great-wall-motor-suriname","grounded-botanical-studio","h-t","hairstudio-32","hakrinbank","hakrinbank-flora","hakrinbank-latour","hakrinbank-nickerie","hakrinbank-nieuwe-haven","hakrinbank-tamanredjo","hakrinbank-tourtonne","handmade-by-farrell-nv","happy-flower-services","harry-tjin","hertz-suriname-car-rental","hes-ds","hes-ds-2","hes-ds-3","house-of-pureness","hsds-lifestyle-noord","hsds-lifestyle-wanica","iamchede","ias-wooden-and-construction-nv","infinity-holding","inksane-tattoos","instyle-optics","international-academy-of-suriname","intervast","invictus-brazilian-jiu-jitsu","itrendzz","jamilas-dry-cleaning-north","jamilas-dry-cleaning-south","jjs-place-zuid","just-curlss","kaizen","kasco-customs-solutions","kasimex-indira-ghandiweg","kasimex-makro","keller-williams-suriname","kempes-co","klm-royal-dutch-airlines","lashlift-suriname","le-den","lioness-beauty-effects","lobby","luxe-escape-lotus-spa-wellness-beautysalon","mandy-butka","marchand-notariaat","max-n-co","maze","mini-nail-shop","mirage-casino","miss-doll-fit","mn-international-centrum","mn-international-kwatta","mokisa-busidataa-osu-nv","mokisa-wellness","multi-travel","nassy-brouwer-college","nassy-brouwer-school","new-choice-lalla-rookhweg","new-choice-nickerie","new-choice-ringweg","north-fitness-gym","notariaat-mannes","notariaat-van-dijk","nv-threefold-quality-system-support","ondernemershuis","one-stop-apotheek-drugstore","orchid","organic-skincare","padel-x-suriname","pandie","paramaribo-princess-casino","percy-massage-therapy","pinkmoon-suriname","pitbull-fitness","professional-private-security","protrade-international","qsi-international-school-of-suriname","re-max-suriname","real-one-fitness-gym","remy-vastgoed","republic-bank-head-office","republic-bank-jozef-israelstraat","republic-bank-kernkampweg","republic-bank-nickerie","republic-bank-vant-hogerhuysstraat","republic-bank-zorg-en-hoop","resourceful-real-estate-construction","rich-skin","rif-cleaning-service","rock-fitness-paramaribo","ross-rental-cars","royal-rose-yoni-spa","royal-spa","royal-wellness-lounge","safety-first-quality-always","satyam-holidays","savage-den","scene-beauty-salon","secas","seen-stories","shimmery-beauty-lounge","smart-connexxionz","southern-commercial-bank","squeaky-clean","sthephany-skincare","stichting-shiatsu-massage","stukaderen-in-nederland","sun-ice","supply-solutions-limited-suriname","surgoed-makelaardij","surimami-store","surinaamsche-waterleiding-maatschappij","surinam-airways","suriname-princess-casino","telesur-centrum","telesur-latour","telesur-lelydorp","telesur-nickerie","telesur-noord","telesur-zonnebloemstraat","the-aerial-yoga-studio","the-basement-barbershop","the-beauty-bar","the-beauty-bar-north","the-beauty-bar-south","the-freelance-scout","the-house-of-beauty","the-laundry-spot","the-nail-house","the-rose-manor","the-solution-property-management","the-waxing-booth","the-wonderlab-su","thermen-hermitage-turkish-bath-beautycenter","tianyou-aquafun","timeless-barber-and-nail-shop","topsport","touch-of-heaven-wellness","tranquil-at-mamba-republiek","tranquil-massage","triple-security-unit","tsw-group","typing-nomad-nv","waldos-worldwide-travel-service","welink-real-estate","wow-plus","x-avenue","ying-hao-beautyshop","yoga-peetha-happiness-centre","yogh-hospitality","young-engineers","zenobia-bottling-company"] for b in [_make_biz(slug)] if b]

# Sort every category list alphabetically by display name
_alpha = lambda lst: sorted(lst, key=lambda b: b["name"].lower())
RESTAURANTS   = _alpha(RESTAURANTS)
HOTELS        = _alpha(HOTELS)
SIGHTSEEING   = _alpha(SIGHTSEEING)
ADVENTURES_BIZ= _alpha(ADVENTURES_BIZ)
SHOPPING      = _alpha(SHOPPING)
SERVICES      = _alpha(SERVICES)

# ── Global search index — written to search-index.json, loaded lazily ────────
import json as _json
_SEARCH_INDEX = _json.dumps([
    *[{"n": b["name"], "u": b["url"], "c": "Eat & Drink",  "a": b.get("area","")} for b in RESTAURANTS],
    *[{"n": b["name"], "u": b["url"], "c": "Stay",         "a": b.get("area","")} for b in HOTELS],
    *[{"n": b["name"], "u": b["url"], "c": "Nature",       "a": b.get("area","")} for b in SIGHTSEEING],
    *[{"n": b["name"], "u": b["url"], "c": "Activities",   "a": b.get("area","")} for b in ADVENTURES_BIZ],
    *[{"n": b["name"], "u": b["url"], "c": "Shopping",     "a": b.get("area","")} for b in SHOPPING],
    *[{"n": b["name"], "u": b["url"], "c": "Services",     "a": b.get("area","")} for b in SERVICES],
], ensure_ascii=False, separators=(',', ':'))

# Write the search index to a standalone cacheable file
with open("search-index.json", "w", encoding="utf-8") as _si_f:
    _si_f.write(_SEARCH_INDEX)

CME_FALLBACK = [
    # CME.sr only publishes SRD, USD, and EUR — no other currencies
    {"currency": "USD", "name": "US Dollar", "buy": "37.50", "sell": "37.65", "flag": "🇺🇸"},
    {"currency": "EUR", "name": "Euro",      "buy": "43.00", "sell": "44.00", "flag": "🇪🇺"},
]

CBVS_FALLBACK = [
    # Giraal (transfer) rates from CBVS weighted-average table.
    # Updated from cbvs.sr front page (24 Apr 2026, 15:00 SR time).
    {"currency": "USD", "name": "US Dollar",           "buy": "37.365", "sell": "37.679", "flag": "🇺🇸"},
    {"currency": "EUR", "name": "Euro",                "buy": "43.345", "sell": "44.151", "flag": "🇪🇺"},
    {"currency": "GBP", "name": "British Pound",       "buy": "50.415", "sell": "51.403", "flag": "🇬🇧"},
    {"currency": "XCG", "name": "Curaçao Guilder",     "buy": "20.530", "sell": "20.933", "flag": "🇨🇼"},
    {"currency": "AWG", "name": "Aruban Florin",       "buy": "20.758", "sell": "21.165", "flag": "🇦🇼"},
    {"currency": "BRL", "name": "Brazilian Real",      "buy": "7.472",  "sell": "7.619",  "flag": "🇧🇷"},
    {"currency": "TTD", "name": "T&T Dollar",          "buy": "5.496",  "sell": "5.603",  "flag": "🇹🇹"},
    {"currency": "BBD", "name": "Barbados Dollar",     "buy": "18.419", "sell": "18.780", "flag": "🇧🇧"},
    {"currency": "XCD", "name": "E. Caribbean Dollar", "buy": "13.839", "sell": "14.110", "flag": "🏝️"},
    {"currency": "GYD", "name": "Guyana Dollar",       "buy": "0.17755","sell": "0.18103","flag": "🇬🇾"},  # CBVS quotes per 100 GYD; stored per unit
    {"currency": "CNY", "name": "Chinese Yuan",        "buy": "5.466",  "sell": "5.573",  "flag": "🇨🇳"},
]

# -- Helpers ------------------------------------------------------------------

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
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']>', raw)
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
                "url":      tags.get("website", f"https://www.google.com/search?q={urllib.parse.quote(name + ' suriname')}"),
            })
            if len(pois) >= limit: break
        return pois
    except Exception as e:
        print(f"  Overpass error: {e}")
        return []

def merge_with_fallbacks(live, fallbacks, target=20):
    used = {r["name"].lower() for r in live}
    for fb in fallbacks:
        if len(live) >= target: break
        if fb["name"].lower() not in used:
            live.append(fb)
    return live

_OBIT_KEYWORDS = {
    "rouwberichten", "rouwadvertentie", "rouwkaart", "rouwbericht",
    "overlijden", "in memoriam", "obituar",
}

def _is_obituary(entry, title_lower):
    """Return True if the entry is an obituary / death notice."""
    if any(kw in title_lower for kw in _OBIT_KEYWORDS):
        return True
    # Check feedparser category tags (term field)
    for tag in getattr(entry, "tags", []):
        term = getattr(tag, "term", "").lower()
        if any(kw in term for kw in _OBIT_KEYWORDS):
            return True
    return False

def fetch_articles():
    articles = []
    for src in FEEDS:
        try:
            feed  = feedparser.parse(src["url"])
            count = 0
            for entry in feed.entries[:MAX_PER_FEED]:
                title   = strip_tags(getattr(entry, "title", "")).strip()
                # Skip obituaries/death notices (De Ware Tijd posts many)
                if _is_obituary(entry, title.lower()):
                    continue
                link    = getattr(entry, "link", "#")
                summary = strip_tags(getattr(entry, "summary", ""))
                if len(summary) > 200: summary = summary[:197] + "..."
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

def fetch_oil_articles():
    """Fetch Oil & Gas articles relevant to Suriname.
    Broad feeds (filter=True) are restricted to articles mentioning Suriname keywords.
    """
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    articles = []
    for src_feed in OIL_FEEDS:
        try:
            feed  = feedparser.parse(src_feed["url"], agent=_UA)
            if getattr(feed, "status", 200) in (403, 401):
                print(f"  SKIP {src_feed['name']} (oil): HTTP {feed.status} — feed blocks server requests")
                continue
            count = 0
            for entry in feed.entries[:30]:
                title   = strip_tags(getattr(entry, "title", "")).strip()
                summary = strip_tags(getattr(entry, "summary", ""))
                # Filter broad feeds to Suriname-relevant articles only
                if src_feed.get("filter"):
                    combined = (title + " " + summary).lower()
                    if not any(kw in combined for kw in _OIL_KEYWORDS):
                        continue
                if len(summary) > 200: summary = summary[:197] + "..."
                link = getattr(entry, "link", "#")
                pub  = parse_date(entry)
                articles.append({
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                    "image":   get_image(entry),
                    "date":    pub,
                    "ago":     time_ago(pub),
                    "source":  src_feed["name"],
                    "color":   src_feed["color"],
                })
                count += 1
            print(f"  OK  {src_feed['name']} (oil): {count}")
        except Exception as e:
            print(f"  ERR {src_feed['name']} (oil): {e}")
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

def fetch_finance_articles():
    """Fetch Suriname finance & economy articles from Google News RSS feeds."""
    _UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    articles = []
    seen = set()
    for src_feed in FINANCE_FEEDS:
        try:
            feed  = feedparser.parse(src_feed["url"], agent=_UA)
            count = 0
            for entry in feed.entries[:20]:
                title   = strip_tags(getattr(entry, "title", "")).strip()
                summary = strip_tags(getattr(entry, "summary", ""))
                link    = getattr(entry, "link", "#")
                # deduplicate by normalised title
                key = title.lower()[:60]
                if key in seen:
                    continue
                seen.add(key)
                if len(summary) > 200: summary = summary[:197] + "..."
                pub = parse_date(entry)
                articles.append({
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                    "image":   get_image(entry),
                    "date":    pub,
                    "ago":     time_ago(pub),
                    "source":  src_feed["name"],
                    "color":   src_feed["color"],
                })
                count += 1
            print(f"  OK  {src_feed['name']} (finance): {count}")
        except Exception as e:
            print(f"  ERR {src_feed['name']} (finance): {e}")
    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles

def fetch_cme_rates():
    """
    CME.sr rates via their internal JSON API.
    The homepage renders rates via JS (all values are 0.00 in static HTML),
    so HTML scraping never works. The JS calls POST /Home/GetTodaysExchangeRates/
    which returns a JSON list with cash buy/sell for USD and EUR only.
    BusinessDate param is hardcoded in their JS and ignored server-side.
    """
    try:
        req = urllib.request.Request(
            "https://www.cme.sr/Home/GetTodaysExchangeRates/?BusinessDate=2016-07-25",
            data=b"",
            headers={
                "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Content-Type": "application/json; charset=utf-8",
                "Accept":       "application/json, text/javascript, */*; q=0.01",
                "Referer":      "https://www.cme.sr/",
                "X-Requested-With": "XMLHttpRequest",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            payload = json.loads(r.read().decode("utf-8"))

        if not payload or not isinstance(payload, list):
            raise ValueError(f"Unexpected response: {str(payload)[:200]}")
        v = payload[0]

        rates = [
            {"currency": "USD", "name": "US Dollar", "flag": "🇺🇸",
             "buy":  f"{float(v['BuyUsdExchangeRate']):.2f}",
             "sell": f"{float(v['SaleUsdExchangeRate']):.2f}"},
            {"currency": "EUR", "name": "Euro",      "flag": "🇪🇺",
             "buy":  f"{float(v['BuyEuroExchangeRate']):.2f}",
             "sell": f"{float(v['SaleEuroExchangeRate']):.2f}"},
        ]
        ts = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")
        print(f"  CME: rates live via API ({ts})")
        return rates, True, f"CME: {ts}"

    except Exception as e:
        print(f"  CME API error: {e}")
        return CME_FALLBACK, False, "Estimated rates (API unavailable)"


def fetch_brent_price():
    """
    Brent Crude front-month futures (BZ=F) via Yahoo Finance chart API.
    Server-side fetch — no CORS issues. Returns (price_usd, updated_str).
    """
    try:
        req = urllib.request.Request(
            "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8"))
        price = d["chart"]["result"][0]["meta"]["regularMarketPrice"]
        ts = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")
        print(f"  Brent Crude: ${price:.2f}/bbl ({ts})")
        return round(price, 2), ts
    except Exception as e:
        print(f"  Brent fetch error: {e}")
        return None, None

def fetch_cbvs_rates():
    """
    Scrape the Gewogen Gemiddelde Wisselkoersen from cbvs.sr.
    The page contains multiple tables; we target only <table class="exchange-table">
    which holds the correct market rates. A plain unstyled <table> higher on the page
    contains fixed intervention/ceiling rates (~14 SRD/USD) — we must skip that.
    CBVS uses Dutch decimal notation: 37,365 = 37.365.
    GYD is quoted per 100 units; we divide by 100 to store per-unit.
    """
    fb_map = {r["currency"]: r for r in CBVS_FALLBACK}
    SKIP = {"THE", "FOR", "AND", "SRD", "VAR", "CSS", "DIV", "IMG", "NAV", "GEM", "PER"}

    for url in ["https://www.cbvs.sr/", "https://www.cbvs.sr/statistieken/financiele-markten-statistieken/dagelijkse-publicaties"]:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
                "Accept-Language": "nl,en;q=0.9",
            })
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read().decode("utf-8", errors="replace")

            # Extract only the Gewogen Gemiddelde exchange-table block — skip all other tables
            tbl_m = re.search(r'<table[^>]+class="exchange-table"[^>]*>(.*?)</table>', raw, re.DOTALL | re.IGNORECASE)
            if not tbl_m:
                print(f"  CBVS {url}: exchange-table not found in page")
                continue
            tbl_html = tbl_m.group(1)

            # Pull the CBVS publication timestamp from the header (e.g. "24 april - 15:00u")
            ts_m = re.search(r'(\d{1,2}\s+\w+\s*-\s*\d{1,2}:\d{2}u)', tbl_html)
            cbvs_ts = ts_m.group(1).strip() if ts_m else datetime.now(SR_TZ).strftime("%d %b %Y")

            rates = []
            seen  = set()
            for row in re.findall(r'<tr[^>]*>(.*?)</tr>', tbl_html, re.DOTALL | re.IGNORECASE):
                text = html_lib.unescape(re.sub(r'<[^>]+>', ' ', row)).strip()
                is_per_100 = bool(re.search(r'GYD\s*PER\s*100', text, re.IGNORECASE))
                # Dutch decimal: 37,365 → 37.365  (3 decimal digits after comma)
                text_norm = re.sub(r'(\d),(\d{3})\b', r'\1.\2', text)
                cm = re.search(r'\b([A-Z]{3})\b', text_norm)
                if not cm:
                    continue
                code = cm.group(1)
                if code in SKIP or code in seen:
                    continue
                nums = [n for n in re.findall(r'\b(\d{1,3}\.\d{2,4})\b', text_norm) if 0.01 < float(n) < 10000]
                if len(nums) >= 2:
                    buy_val, sell_val = nums[0], nums[1]  # Giraal Aankoop / Giraal Verkoop
                    if is_per_100:
                        buy_val  = f"{float(buy_val)  / 100:.5f}"
                        sell_val = f"{float(sell_val) / 100:.5f}"
                        code = "GYD"
                    fb = fb_map.get(code, {})
                    rates.append({"currency": code, "name": fb.get("name", code),
                                   "buy": buy_val, "sell": sell_val, "flag": fb.get("flag", "\U0001f4b1")})
                    seen.add(code)

            if len(rates) >= 2:
                print(f"  CBVS: {len(rates)} rates live from {url} ({cbvs_ts})")
                return rates, True, f"CBVS: {cbvs_ts}"

        except Exception as e:
            print(f"  CBVS {url}: {e}")

    print("  CBVS: all URLs failed, using fallback")
    return CBVS_FALLBACK, False, "Estimated rates (live fetch unavailable)"

# -- Shared HTML parts --------------------------------------------------------

PAGE_HEAD = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="content-language" content="en">
  <link rel="icon" href="/favicon.ico" sizes="48x48 32x32 16x16">
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/icons/icon-192.png">
  <meta name="twitter:site" content="@exploringsuriname">
  <meta property="og:locale" content="en_US">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" as="style" onload="this.onload=null;this.rel='stylesheet'"
        href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap">
  <noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap"></noscript>
  <link rel="stylesheet" href="/tailwind.css">
  <link rel="manifest" href="/manifest.webmanifest">
  <meta name="theme-color" content="#1B4332">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="ExploreSR">
  <style>
    :root { --forest:#1B4332; --forest2:#2D6A4F; --leaf:#52B788; --mint:#D8F3DC; --coral:#E76F51; }
    body   { font-family: 'Inter', system-ui, sans-serif; }
    .serif { font-family: 'Playfair Display', Georgia, serif; }
    .hero-bg { background-size:cover; background-position:center; }
    .card-hover { transition: transform .2s, box-shadow .2s; }
    .card-hover:hover { transform:translateY(-4px); box-shadow:0 12px 32px rgba(0,0,0,.12); }
    a { text-decoration: none; }
  </style>
  <script>if("serviceWorker"in navigator)window.addEventListener("load",()=>navigator.serviceWorker.register("/sw.js").catch(()=>{}));</script>
  <!-- Google tag (gtag.js) -->
  <script>window.addEventListener("load",function(){var s=document.createElement("script");s.async=1;s.src="https://www.googletagmanager.com/gtag/js?id=G-6LTYHZYNSF";document.head.appendChild(s);window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag("js",new Date());gtag("config","G-6LTYHZYNSF");});</script>"""

# ── WorldTides: tide data for Paramaribo ────────────────────────────────────
# ── WorldTides: district river tide locations ─────────────────────────────────
# API budget (100 free requests/month):
#   Suriname River  24h cache → 30/month
#   4 other rivers  72h cache → 10/month each = 40/month
#   Total: 70/month  ✓ within 100 free limit

TIDES_LOCATIONS = [
    {"id": "suriname",   "label": "Suriname River",   "district": "Paramaribo",
     "lat": 5.852, "lon": -55.203, "cache": "tides_cache.json",             "cache_h": 24},
    {"id": "commewijne", "label": "Commewijne River", "district": "Commewijne",
     "lat": 5.893, "lon": -55.087, "cache": "tides_cache_commewijne.json",  "cache_h": 72},
    {"id": "nickerie",   "label": "Nickerie River",   "district": "Nickerie",
     "lat": 5.944, "lon": -57.003, "cache": "tides_cache_nickerie.json",    "cache_h": 72},
    {"id": "marowijne",  "label": "Marowijne River",  "district": "Marowijne",
     "lat": 5.502, "lon": -54.056, "cache": "tides_cache_marowijne.json",   "cache_h": 72},
]


def _fetch_tides_for_location(loc, key):
    """
    Fetch 3-day tide extremes for a single TIDES_LOCATIONS entry.
    Returns (extremes, is_live, updated_str).
    """
    import time as _time
    now_ts = datetime.now(timezone.utc).timestamp()
    cache_file = loc["cache"]
    cache_secs = loc["cache_h"] * 3600

    try:
        with open(cache_file) as _f:
            cache = json.load(_f)
        if now_ts - cache.get("fetched", 0) < cache_secs:
            print(f"  WorldTides [{loc['id']}]: using cached data")
            return cache["extremes"], True, cache["updated"]
    except Exception:
        pass

    try:
        url = (
            f"https://www.worldtides.info/api/v3?extremes"
            f"&lat={loc['lat']}&lon={loc['lon']}&days=3&key={key}"
        )
        with urllib.request.urlopen(url, timeout=20) as _r:
            data = json.loads(_r.read().decode("utf-8"))

        if data.get("status", 0) != 200:
            raise ValueError(f"WorldTides [{loc['id']}] error: {data}")

        extremes = data.get("extremes", data.get("Extremes", []))
        ts_str   = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")

        cache_obj = {"fetched": now_ts, "extremes": extremes, "updated": ts_str}
        with open(cache_file, "w") as _f:
            json.dump(cache_obj, _f)
        print(f"  WorldTides [{loc['id']}]: fetched {len(extremes)} extremes")
        return extremes, True, ts_str

    except Exception as e:
        print(f"  WorldTides [{loc['id']}] error: {e}")
        try:
            with open(cache_file) as _f:
                cache = json.load(_f)
            return cache["extremes"], False, cache["updated"] + " (cached)"
        except Exception:
            return [], False, "Data unavailable"


def fetch_worldtides():
    """
    Fetch tide extremes for all district river locations.
    Returns a dict keyed by location id: {id: (extremes, is_live, updated_str)}.
    Paramaribo (main) result also returned separately for backward compat.
    """
    import os as _os
    import time as _time
    key = _os.environ.get("WORLDTIDES_KEY", "").strip()
    if not key:
        print("  WorldTides: no WORLDTIDES_KEY set — skipping tides")
        fallback = "No API key configured"
        results = {loc["id"]: ([], False, fallback) for loc in TIDES_LOCATIONS}
        return results

    results = {}
    for i, loc in enumerate(TIDES_LOCATIONS):
        if i > 0:
            _time.sleep(2)   # avoid rate limit between requests
        results[loc["id"]] = _fetch_tides_for_location(loc, key)
    return results


# ── OpenSky: arrivals and departures at Johan Adolf Pengel (SMJP / PBM) ─────
_OPENSKY_ICAO = "SMJP"

_AIRLINE_ICAO = {
    "KLM": "KLM Royal Dutch Airlines",
    "SLM": "Surinam Airways",
    "TUI": "TUI fly",
    "TBB": "TUI fly Netherlands",
    "HV":  "Transavia",
    "TOF": "Transavia",
    "CMP": "Copa Airlines",
    "BEL": "Brussels Airlines",
    "IBE": "Iberia",
    "DLH": "Lufthansa",
    "AFR": "Air France",
    "DAL": "Delta Air Lines",
    "AAL": "American Airlines",
    "UAL": "United Airlines",
    "GLO": "Gol Transportes",
    "TAM": "LATAM Airlines",
    "LA":  "LATAM Airlines",
    "AZU": "Azul Brazilian Airlines",
    "BWA": "Caribbean Airlines",
    "CAW": "Caribbean Airlines",
    "BW":  "Caribbean Airlines",
    "LIA": "LIAT",
    "SVD": "St. Vincent Grenadines Air",
}

_AIRPORT_NAMES = {
    "EHAM": "Amsterdam (AMS)",
    "EHRD": "Rotterdam (RTM)",
    "TNCC": "Curaçao (CUR)",
    "TNCM": "St. Maarten (SXM)",
    "TNCA": "Aruba (AUA)",
    "MPTO": "Panama City (PTY)",
    "SBGL": "Rio de Janeiro (GIG)",
    "SBGR": "São Paulo (GRU)",
    "SBEG": "Manaus (MAO)",
    "SBMQ": "Macapá (MCP)",
    "SBBV": "Boa Vista (BVB)",
    "MDSD": "Santo Domingo (SDQ)",
    "TGPY": "Grenada (GND)",
    "TBPB": "Barbados (BGI)",
    "TTPP": "Port of Spain (POS)",
    "MKJP": "Kingston (KIN)",
    "SYEL": "Kaieteur (KAI)",
    "SYGT": "Georgetown (GEO)",
    "SYGO": "Georgetown (OGL)",
    "SMJP": "Paramaribo (PBM)",
    "LEMD": "Madrid (MAD)",
    "LFPG": "Paris CDG (CDG)",
    "EGLL": "London (LHR)",
    "EDDF": "Frankfurt (FRA)",
    "LIRF": "Rome (FCO)",
    "LEBL": "Barcelona (BCN)",
    "FNLU": "Luanda (LAD)",
    "HAAB": "Addis Ababa (ADD)",
}


def _decode_flight(row, direction):
    """Parse an OpenSky flights API row into a display dict."""
    import re as _re
    callsign = (row.get("callsign") or "").strip()
    m = _re.match(r'^([A-Z]{2,3})(\d+)$', callsign)
    if m:
        prefix, number = m.group(1), m.group(2)
    else:
        prefix = callsign[:3].upper() if callsign else "???"
        number = callsign[3:] if len(callsign) > 3 else ""

    airline   = _AIRLINE_ICAO.get(prefix, prefix)
    flight_no = f"{prefix}{number}" if number else callsign or "???"

    if direction == "arrival":
        ap_icao = row.get("estDepartureAirport") or "???"
        ts      = row.get("lastSeen") or row.get("firstSeen") or 0
    else:
        ap_icao = row.get("estArrivalAirport") or "???"
        ts      = row.get("firstSeen") or row.get("lastSeen") or 0

    ap_name = _AIRPORT_NAMES.get(ap_icao, ap_icao)

    time_str = (datetime.fromtimestamp(ts, tz=SR_TZ).strftime("%d %b %H:%M SR")
                if ts else "—")

    return {
        "flight":  flight_no,
        "airline": airline,
        "airport": ap_name,
        "icao":    ap_icao,
        "time":    time_str,
        "ts":      ts,
    }


# ── AeroDataBox flight fetching ───────────────────────────────────────────────
# API budget (600 free calls/month via RapidAPI):
#   SMJP  6 h cache → 2 calls/fetch × 4 fetches/day × 30 = 240/month
#   SMGM 12 h cache → 2 calls/fetch × 2 fetches/day × 30 = 120/month
#   Total: 480/month  ✓ comfortably within 600 free limit

_AIRPORTS_FLIGHT = [
    {"icao": "SMJP", "iata": "PBM", "label": "Johan Adolf Pengel (PBM)",
     "short": "PBM",  "cache": "flights_cache.json",      "cache_h": 6},
    {"icao": "SMEG", "iata": "EAX", "label": "Eduard Alexander Gummels (EAX)",
     "short": "EAX",   "cache": "flights_cache_smeg.json",  "cache_h": 12},
]

def _fr24_parse_flight(entry, direction):
    """Parse one FR24 schedule entry into a display dict."""
    fl = entry.get("flight", entry)

    flight_no = (fl.get("identification") or {}).get("number", {}).get("default") or "—"
    airline   = ((fl.get("airline") or {}).get("name") or "Unknown")

    ap_key  = "origin" if direction == "arrival" else "destination"
    ap      = ((fl.get("airport") or {}).get(ap_key) or {})
    ap_name = ap.get("name") or ((ap.get("code") or {}).get("iata")) or "Unknown"
    ap_iata = (ap.get("code") or {}).get("iata", "")

    # Prefer real > estimated > scheduled time
    times    = (fl.get("time") or {})
    time_key = "arrival" if direction == "arrival" else "departure"
    ts = (times.get("real")      or {}).get(time_key) \
      or (times.get("estimated") or {}).get(time_key) \
      or (times.get("scheduled") or {}).get(time_key)

    time_sr = ""
    if ts:
        try:
            from datetime import datetime as _dt
            time_sr = _dt.fromtimestamp(ts, tz=SR_TZ).strftime("%d %b %H:%M")
        except Exception:
            pass

    status = (fl.get("status") or {}).get("text", "")

    return {
        "flight":  flight_no,
        "airline": airline,
        "airport": ap_name,
        "iata":    ap_iata,
        "time":    time_sr,
        "status":  status,
    }


def _fetch_flights_fr24(icao, cache_file, cache_hours):
    """
    Fetch today's arrivals & departures for *icao* from FlightRadar24.
    No API key required. Same cache interface as before.
    """
    import time as _time
    now_ts = datetime.now(timezone.utc).timestamp()

    # Cache: full TTL if API was reached (even 0 flights), 1h retry on error
    try:
        with open(cache_file) as _f:
            cache = json.load(_f)
        age      = now_ts - cache.get("fetched", 0)
        has_data = bool(cache.get("arrivals") or cache.get("departures"))
        api_ok   = cache.get("api_success", False)
        ttl      = cache_hours * 3600 if (has_data or api_ok) else 3600
        if age < ttl:
            print(f"  FR24 [{icao}]: using cached data")
            return cache["arrivals"], cache["departures"], cache["updated"]
    except Exception:
        pass

    _headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "application/json, text/javascript, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer":         "https://www.flightradar24.com/",
    }

    url = (
        f"https://api.flightradar24.com/common/v1/airport.json"
        f"?code={icao}&plugin[]=schedule&limit=100&page=1"
    )

    arrivals, departures = [], []
    api_success = False

    try:
        req = urllib.request.Request(url, headers=_headers)
        with urllib.request.urlopen(req, timeout=20) as _r:
            data = json.loads(_r.read().decode("utf-8"))

        sched = (
            data.get("result", {})
                .get("response", {})
                .get("airport", {})
                .get("pluginData", {})
                .get("schedule", {})
        )

        for entry in sched.get("arrivals", {}).get("data", []):
            parsed = _fr24_parse_flight(entry, "arrival")
            if parsed["time"]:
                arrivals.append(parsed)

        for entry in sched.get("departures", {}).get("data", []):
            parsed = _fr24_parse_flight(entry, "departure")
            if parsed["time"]:
                departures.append(parsed)

        arrivals.sort(key=lambda x: x["time"])
        departures.sort(key=lambda x: x["time"])
        api_success = True
        print(f"  FR24 [{icao}]: {len(arrivals)} arr, {len(departures)} dep")

    except Exception as e:
        print(f"  FR24 [{icao}] error: {e}")

    updated = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")
    try:
        with open(cache_file, "w") as _f:
            json.dump({
                "fetched":     now_ts,
                "arrivals":    arrivals,
                "departures":  departures,
                "updated":     updated,
                "api_success": api_success,
            }, _f)
    except Exception:
        pass

    return arrivals, departures, updated


def fetch_aerodatabox_flights():
    """
    Fetch flights for all tracked airports via FlightRadar24.
    Returns dict keyed by ICAO: {icao: (arrivals, departures, updated)}.
    No API key required — replaces AeroDataBox.
    """
    import time as _time
    results = {}
    for i, ap in enumerate(_AIRPORTS_FLIGHT):
        if i > 0:
            _time.sleep(2)
        results[ap["icao"]] = _fetch_flights_fr24(
            ap["icao"], ap["cache"], ap["cache_h"]
        )
    return results


def nav_html(active="home", prefix=""):
    # ── Group / active-state helpers ────────────────────────────────────────
    _TODO  = {"nature", "activities", "shopping"}
    _EAT   = {"restaurants", "hotels"}
    _ESS   = {"currency", "flights", "forecast", "visitor", "roads"}

    def _is_active(key):
        return active == key

    def _group_active(keys):
        return active in keys

    def _link_cls(key):
        if _is_active(key):
            return 'class="block px-4 py-2.5 text-sm font-semibold rounded-lg" style="color:var(--forest);background:var(--mint)"'
        return 'class="block px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 hover:text-green-800 rounded-lg transition"'

    def _top_btn_style(group_keys):
        if _group_active(group_keys):
            return 'class="dd-trigger flex items-center gap-1 text-sm font-semibold transition py-1" style="color:var(--forest)"'
        return 'class="dd-trigger flex items-center gap-1 text-sm text-gray-700 hover:text-green-800 transition py-1"'

    def _top_single_style(key):
        if _is_active(key):
            return 'class="text-sm font-semibold py-1" style="color:var(--forest)"'
        return 'class="text-sm text-gray-700 hover:text-green-800 transition py-1"'

    _chevron = '<svg class="dd-chevron w-3.5 h-3.5 transition-transform duration-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>'

    # ── Desktop dropdowns ───────────────────────────────────────────────────
    def _desktop_dd(dd_id, label, items_html, group_keys):
        dot = ' <span class="inline-block w-1.5 h-1.5 rounded-full mb-0.5" style="background:var(--forest)"></span>' if _group_active(group_keys) else ''
        return (
            f'<div class="relative" id="{dd_id}" onmouseenter="openDd(\'{dd_id}\')" onmouseleave="closeDd(\'{dd_id}\')">'
            f'<button onclick="toggleDd(\'{dd_id}\')" {_top_btn_style(group_keys)}>'
            f'{label}{dot}{_chevron}</button>'
            f'<div id="{dd_id}-menu" class="dd-menu hidden absolute top-full left-1/2 -translate-x-1/2 mt-1 bg-white rounded-2xl shadow-xl border border-gray-100 py-2 min-w-[190px] z-50">'
            f'{items_html}'
            f'</div></div>'
        )

    # Things to Do
    todo_items = (
        f'<a href="{prefix}nature.html"      {_link_cls("nature")}     >Nature</a>'
        f'<a href="{prefix}activities.html"  {_link_cls("activities")} >Activities</a>'
        f'<a href="{prefix}shopping.html"    {_link_cls("shopping")}   >Shopping</a>'
    )
    # Eat & Stay
    eat_items = (
        f'<a href="{prefix}restaurants.html" {_link_cls("restaurants")}>Where to Eat</a>'
        f'<a href="{prefix}hotels.html"      {_link_cls("hotels")}     >Where to Stay</a>'
    )
    # Essentials
    ess_items = (
        f'<a href="{prefix}currency.html"    {_link_cls("currency")}   >Market Rates</a>'
        f'<a href="{prefix}flights.html"     {_link_cls("flights")}    >Flights</a>'
        f'<a href="{prefix}conditions.html"  {_link_cls("forecast")}   >Weather &amp; Tides</a>'
        f'<a href="{prefix}visitor-guide.html" {_link_cls("visitor")}  >Visitor Guide</a>'
        f'<a href="{prefix}on-the-road.html" {_link_cls("roads")}      >On the Road</a>'
    )

    desktop_nav = (
        _desktop_dd("dd-todo", "Things to Do",   todo_items, _TODO) +
        _desktop_dd("dd-eat",  "Eat &amp; Stay", eat_items,  _EAT)  +
        f'<a href="{prefix}services.html" {_top_single_style("services")}>Local Services</a>' +
        _desktop_dd("dd-ess",  "Essentials",     ess_items,  _ESS)  +
        f'<a href="{prefix}news.html" {_top_single_style("news")}>News</a>'
    )

    # ── Mobile accordion ────────────────────────────────────────────────────
    def _mob_link(href, label, key):
        if _is_active(key):
            return f'<a href="{href}" class="flex items-center gap-2 py-2.5 px-3 text-sm font-semibold rounded-lg" style="color:var(--forest);background:var(--mint)">{label}</a>'
        return f'<a href="{href}" class="flex items-center gap-2 py-2.5 px-3 text-sm text-gray-600 hover:text-green-800 rounded-lg">{label}</a>'

    def _mob_group(mg_id, label, items_html, group_keys):
        open_cls  = "" if _group_active(group_keys) else " hidden"
        hdr_style = 'style="color:var(--forest)"' if _group_active(group_keys) else ""
        return (
            f'<div class="mob-group">'
            f'<button onclick="toggleMobGroup(\'{mg_id}\')" '
            f'class="mob-group-btn flex items-center justify-between w-full py-3 px-1 text-sm font-semibold text-gray-800 border-b border-gray-100" {hdr_style}>'
            f'<span>{label}</span>'
            f'<svg class="mob-chevron w-4 h-4 transition-transform duration-200{" rotate-180" if _group_active(group_keys) else ""}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>'
            f'</button>'
            f'<div id="{mg_id}" class="mob-group-body pl-2 pb-1{open_cls}">{items_html}</div>'
            f'</div>'
        )

    mob_todo_items = (
        _mob_link(f"{prefix}nature.html",      "Nature",       "nature")     +
        _mob_link(f"{prefix}activities.html",  "Activities",   "activities") +
        _mob_link(f"{prefix}shopping.html",    "Shopping",     "shopping")
    )
    mob_eat_items = (
        _mob_link(f"{prefix}restaurants.html", "Where to Eat",  "restaurants") +
        _mob_link(f"{prefix}hotels.html",      "Where to Stay", "hotels")
    )
    mob_ess_items = (
        _mob_link(f"{prefix}currency.html",   "Market Rates", "currency") +
        _mob_link(f"{prefix}flights.html",    "Flights",              "flights")  +
        _mob_link(f"{prefix}conditions.html", "Weather & Tides",      "forecast") +
        _mob_link(f"{prefix}visitor-guide.html", "Visitor Guide",     "visitor") +
        _mob_link(f"{prefix}on-the-road.html", "On the Road",         "roads")
    )

    _svc_col  = 'style="color:var(--forest)"' if _is_active("services") else ""
    _news_col = 'style="color:var(--forest)"' if _is_active("news")     else ""
    _svc_link  = f'<a href="{prefix}services.html" class="flex items-center justify-between py-3 px-1 text-sm font-semibold text-gray-800 border-b border-gray-100" {_svc_col}>Local Services</a>'
    _news_link = f'<a href="{prefix}news.html" class="flex items-center py-3 px-1 text-sm font-semibold text-gray-800" {_news_col}>News</a>'

    # Used by the search modal JS
    cat_colors = {"Eat & Drink":"#7c3aed","Stay":"#c05621","Nature":"var(--forest)",
                  "Activities":"var(--forest2)","Shopping":"#0369a1","Services":"#0369a1","Sightseeing":"var(--forest)"}

    mobile_menu = (
        _mob_group("mg-todo", "Things to Do",   mob_todo_items, _TODO) +
        _mob_group("mg-eat",  "Eat & Stay",     mob_eat_items,  _EAT)  +
        _svc_link +
        _mob_group("mg-ess",  "Essentials",     mob_ess_items,  _ESS)  +
        _news_link
    )

    return f"""
<style>
.dd-menu {{ transform-origin: top center; }}
.dd-menu.open {{ display:block!important; animation: ddFadeIn .15s ease; }}
@keyframes ddFadeIn {{ from{{opacity:0;transform:translateY(-6px)}} to{{opacity:1;transform:translateY(0)}} }}
</style>
<nav class="fixed top-0 w-full z-50" style="background:rgba(255,255,255,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 12px rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between gap-4">
    <a href="{prefix}index.html" class="flex items-baseline flex-shrink-0">
      <span class="serif text-2xl font-bold" style="color:var(--forest)">Explore</span><span class="serif text-2xl font-bold" style="color:var(--coral)">Suriname</span>
    </a>
    <div class="hidden md:flex items-center gap-6">{desktop_nav}</div>
    <div class="flex items-center gap-2 flex-shrink-0">
      <button onclick="openSearch()" title="Search listings (press /)" class="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 text-gray-400 text-sm hover:border-gray-400 hover:text-gray-600 transition bg-gray-50 sm:min-w-[120px]">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path stroke-linecap="round" d="m21 21-4.35-4.35"/></svg>
        <span class="hidden sm:inline">Search…</span>
        <span class="ml-auto hidden sm:inline text-xs bg-gray-200 text-gray-500 rounded px-1.5 py-0.5 font-mono">/</span>
      </button>
      <button id="hamburger" onclick="toggleMobileMenu()" class="md:hidden p-2 rounded-lg hover:bg-gray-100 transition" aria-label="Menu">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
      </button>
    </div>
  </div>
  <div id="mm" class="hidden md:hidden border-t bg-white px-4 py-2 pb-3 flex flex-col gap-0 max-h-[75vh] overflow-y-auto">
    {mobile_menu}
  </div>
</nav>
<script>
/* ── Dropdown (desktop) ─────────────────────────────────────────────────── */
var _openDd = null;
var _ddTimer = null;
function openDd(id) {{
  if (_ddTimer) {{ clearTimeout(_ddTimer); _ddTimer = null; }}
  if (_openDd && _openDd !== id) closeDd(_openDd);
  var menu = document.getElementById(id + '-menu');
  var chev = document.getElementById(id) ? document.getElementById(id).querySelector('.dd-chevron') : null;
  if (menu) menu.classList.remove('hidden');
  if (chev) chev.style.transform = 'rotate(180deg)';
  _openDd = id;
}}
function closeDd(id) {{
  _ddTimer = setTimeout(function() {{
    var menu = document.getElementById(id + '-menu');
    var chev = document.getElementById(id) ? document.getElementById(id).querySelector('.dd-chevron') : null;
    if (menu) menu.classList.add('hidden');
    if (chev) chev.style.transform = '';
    if (_openDd === id) _openDd = null;
    _ddTimer = null;
  }}, 80);
}}
function toggleDd(id) {{
  var menu = document.getElementById(id + '-menu');
  var btn  = document.getElementById(id);
  var chev = btn ? btn.querySelector('.dd-chevron') : null;
  if (_openDd && _openDd !== id) {{
    var prev = document.getElementById(_openDd + '-menu');
    var prevBtn = document.getElementById(_openDd);
    if (prev)    prev.classList.add('hidden');
    if (prevBtn) {{ var c = prevBtn.querySelector('.dd-chevron'); if(c) c.style.transform=''; }}
    _openDd = null;
  }}
  if (!menu) return;
  var isOpen = !menu.classList.contains('hidden');
  if (isOpen) {{
    menu.classList.add('hidden');
    if (chev) chev.style.transform = '';
    _openDd = null;
  }} else {{
    menu.classList.remove('hidden');
    if (chev) chev.style.transform = 'rotate(180deg)';
    _openDd = id;
  }}
}}
document.addEventListener('click', function(e) {{
  if (_openDd && !document.getElementById(_openDd).contains(e.target)) {{
    var menu = document.getElementById(_openDd + '-menu');
    var btn  = document.getElementById(_openDd);
    if (menu) menu.classList.add('hidden');
    if (btn)  {{ var c = btn.querySelector('.dd-chevron'); if(c) c.style.transform=''; }}
    _openDd = null;
  }}
}});
/* ── Mobile accordion ───────────────────────────────────────────────────── */
function toggleMobileMenu() {{
  var mm = document.getElementById('mm');
  mm.classList.toggle('hidden');
}}
function toggleMobGroup(id) {{
  var body = document.getElementById(id);
  var btn  = body ? body.previousElementSibling : null;
  var chev = btn  ? btn.querySelector('.mob-chevron') : null;
  if (!body) return;
  var isOpen = !body.classList.contains('hidden');
  body.classList.toggle('hidden', isOpen);
  if (chev) chev.style.transform = isOpen ? '' : 'rotate(180deg)';
}}
</script>
<!-- ── Global Search Modal ───────────────────────────────────────────── -->
<div id="search-modal" onclick="if(event.target===this)closeSearch()"
  style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.45);backdrop-filter:blur(4px);padding:80px 16px 16px">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 25px 60px rgba(0,0,0,.25);overflow:hidden">
    <div style="display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid #f0f0f0">
      <svg style="width:18px;height:18px;color:#9ca3af;flex-shrink:0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path stroke-linecap="round" d="m21 21-4.35-4.35"/></svg>
      <input id="search-input" type="text" placeholder="Search all listings…"
        oninput="runSearch(this.value)" onkeydown="searchKey(event)"
        style="flex:1;border:none;outline:none;font-size:1rem;color:#111;background:transparent"
        autocomplete="off" spellcheck="false">
      <button onclick="closeSearch()" style="color:#9ca3af;font-size:1.3rem;line-height:1;background:none;border:none;cursor:pointer">&#x2715;</button>
    </div>
    <div id="search-results" style="max-height:420px;overflow-y:auto;padding:8px 0">
      <p id="search-hint" style="text-align:center;color:#9ca3af;font-size:.85rem;padding:32px 0">Start typing to search {len(_SEARCH_INDEX.split('"n"')) - 1} listings…</p>
    </div>
  </div>
</div>
<style>
#search-results a {{
  display:flex;align-items:center;gap:10px;padding:10px 18px;text-decoration:none;color:#111;transition:background .1s;
}}
#search-results a:hover, #search-results a.sr-active {{ background:#f5f5f5; }}
.sr-badge {{
  font-size:.7rem;font-weight:600;padding:2px 8px;border-radius:999px;color:#fff;flex-shrink:0;
}}
.sr-name {{ font-size:.9rem;font-weight:600;flex:1;min-width:0; }}
.sr-area {{ font-size:.78rem;color:#9ca3af;white-space:nowrap; }}
mark {{ background:#fef08a;border-radius:2px;padding:0 1px; }}
</style>
<script>
const _CAT_C = {_json.dumps(cat_colors)};
let _SI = null;
let _SI_loading = false;
let _sel = -1;

function _loadSI(cb) {{
  if (_SI) {{ cb(); return; }}
  if (_SI_loading) {{ setTimeout(() => _loadSI(cb), 50); return; }}
  _SI_loading = true;
  const depth = window.location.pathname.split('/').length > 3 ? '../../' : '';
  fetch(depth + 'search-index.json')
    .then(r => r.json())
    .then(data => {{ _SI = data; cb(); }})
    .catch(() => {{ _SI = []; cb(); }});
}}
function openSearch() {{
  document.getElementById('search-modal').style.display = 'block';
  setTimeout(() => document.getElementById('search-input').focus(), 50);
  _loadSI(() => {{}});
}}
function closeSearch() {{
  document.getElementById('search-modal').style.display = 'none';
  document.getElementById('search-input').value = '';
  document.getElementById('search-results').innerHTML = '<p id="search-hint" style="text-align:center;color:#9ca3af;font-size:.85rem;padding:32px 0">Start typing to search listings…</p>';
  _sel = -1;
}}
function runSearch(q) {{
  const box = document.getElementById('search-results');
  q = q.trim();
  if (!q) {{ closeSearch(); openSearch(); return; }}
  if (!_SI) {{
    _loadSI(() => runSearch(q));
    box.innerHTML = '<p style="text-align:center;color:#9ca3af;font-size:.85rem;padding:32px 0">Loading…</p>';
    return;
  }}
  const ql = q.toLowerCase();
  const hits = _SI.filter(x => x.n.toLowerCase().includes(ql)).slice(0, 10);
  if (!hits.length) {{ box.innerHTML = '<p style="text-align:center;color:#9ca3af;font-size:.85rem;padding:32px 0">No results for "' + q + '"</p>'; return; }}
  const depth = window.location.pathname.split('/').length > 3 ? '../../' : '';
  box.innerHTML = hits.map((h, i) => {{
    const hi = h.n.replace(new RegExp('(' + q.replace(/[.*+?^${{}}()|[\]\\\\]/g,'\\\\$&') + ')', 'gi'), '<mark>$1</mark>');
    const col = _CAT_C[h.c] || '#6b7280';
    return '<a href="' + depth + h.u + '" class="' + (i===0?'sr-active':'') + '">'
      + '<span class="sr-badge" style="background:' + col + '">' + h.c + '</span>'
      + '<span class="sr-name">' + hi + '</span>'
      + (h.a ? '<span class="sr-area">' + h.a + '</span>' : '')
      + '</a>';
  }}).join('');
  _sel = 0;
}}
function searchKey(e) {{
  const items = document.querySelectorAll('#search-results a');
  if (e.key === 'Escape') {{ closeSearch(); return; }}
  if (e.key === 'ArrowDown') {{ e.preventDefault(); _sel = Math.min(_sel+1, items.length-1); }}
  else if (e.key === 'ArrowUp') {{ e.preventDefault(); _sel = Math.max(_sel-1, 0); }}
  else if (e.key === 'Enter') {{ if(items[_sel]) window.location = items[_sel].href; return; }}
  else return;
  items.forEach((el,i) => el.classList.toggle('sr-active', i===_sel));
  if(items[_sel]) items[_sel].scrollIntoView({{block:'nearest'}});
}}
document.addEventListener('keydown', e => {{
  if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {{
    e.preventDefault(); openSearch();
  }}
}});
</script>"""

def footer_html(prefix=""):
    return f"""
<footer style="background:var(--forest)" class="text-white py-10">
  <div class="max-w-6xl mx-auto px-5">
    <div class="grid grid-cols-2 md:grid-cols-5 gap-8 mb-6">
      <div class="col-span-2 md:col-span-1">
        <p class="serif text-2xl font-bold mb-3">Explore<span style="color:var(--coral)">Suriname</span></p>
        <p class="text-white/60 text-sm leading-relaxed">Your guide to Suriname: places to eat, stay, explore, shop and stay informed with local, Oil &amp; Gas and Finance news.</p>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Explore</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li><a href="{prefix}nature.html"      class="hover:text-white transition">Nature &amp; Parks</a></li>
          <li><a href="{prefix}activities.html"  class="hover:text-white transition">Activities</a></li>
          <li><a href="{prefix}shopping.html"    class="hover:text-white transition">Shopping</a></li>
          <li><a href="{prefix}restaurants.html" class="hover:text-white transition">Where to Eat</a></li>
          <li><a href="{prefix}hotels.html"      class="hover:text-white transition">Where to Stay</a></li>
          <li><a href="{prefix}services.html"    class="hover:text-white transition">Local Services</a></li>
        </ul>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Essentials</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li><a href="{prefix}currency.html"      class="hover:text-white transition">Market Rates</a></li>
          <li><a href="{prefix}flights.html"       class="hover:text-white transition">Flights</a></li>
          <li><a href="{prefix}conditions.html"    class="hover:text-white transition">Weather &amp; Tides</a></li>
          <li><a href="{prefix}visitor-guide.html" class="hover:text-white transition">Visitor Guide</a></li>
          <li><a href="{prefix}on-the-road.html"   class="hover:text-white transition">On the Road</a></li>
          <li><a href="{prefix}news.html"          class="hover:text-white transition">News</a></li>
        </ul>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Travel Info</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li>Capital: Paramaribo</li>
          <li>Languages: Dutch, Sranan Tongo + 9 more</li>
          <li>Currency: Surinamese Dollar (SRD)</li>
          <li>Climate: Tropical, ~28&#176;C year-round</li>
          <li>2 UNESCO World Heritage Sites</li>
        </ul>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Contact</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li><a href="{prefix}contact.html" class="hover:text-white transition">Contact Us</a></li>
          <li><a href="{prefix}about.html" class="hover:text-white transition">About This Site</a></li>
          <li class="text-white/40 text-xs mt-3">For partnerships, listings<br>or general enquiries.</li>
        </ul>
      </div>
    </div>
    <div class="border-t border-white/10 pt-8 flex flex-col items-center gap-4">
      <div class="flex gap-3">
        <a href="https://www.facebook.com/exploringsuriname/" target="_blank" rel="noopener"
           class="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold text-white transition"
           style="background:#1877F2;">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22 12c0-5.522-4.477-10-10-10S2 6.478 2 12c0 4.991 3.657 9.128 8.438 9.878v-6.987H7.898V12h2.54V9.797c0-2.506 1.492-3.89 3.777-3.89 1.094 0 2.238.195 2.238.195v2.46h-1.26c-1.243 0-1.63.771-1.63 1.562V12h2.773l-.443 2.891h-2.33v6.987C18.343 21.128 22 16.991 22 12z"/></svg>
          Facebook
        </a>
        <a href="https://www.instagram.com/exploringsuriname/" target="_blank" rel="noopener"
           class="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold text-white transition"
           style="background:linear-gradient(45deg,#f09433,#e6683c,#dc2743,#cc2366,#bc1888);">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 1.366.062 2.633.336 3.608 1.311.975.975 1.249 2.242 1.311 3.608.058 1.266.07 1.646.07 4.85s-.012 3.584-.07 4.85c-.062 1.366-.336 2.633-1.311 3.608-.975.975-2.242 1.249-3.608 1.311-1.266.058-1.646.07-4.85.07s-3.584-.012-4.85-.07c-1.366-.062-2.633-.336-3.608-1.311-.975-.975-1.249-2.242-1.311-3.608C2.175 15.584 2.163 15.204 2.163 12s.012-3.584.07-4.85c.062-1.366.336-2.633 1.311-3.608.975-.975 2.242-1.249 3.608-1.311C8.416 2.175 8.796 2.163 12 2.163zm0-2.163C8.741 0 8.333.014 7.053.072 5.775.13 4.602.402 3.635 1.368 2.668 2.335 2.396 3.508 2.338 4.786 2.28 6.066 2.266 6.474 2.266 12s.014 5.934.072 7.214c.058 1.278.33 2.451 1.297 3.418.967.967 2.14 1.239 3.418 1.297C8.333 23.986 8.741 24 12 24s3.667-.014 4.947-.072c1.278-.058 2.451-.33 3.418-1.297.967-.967 1.239-2.14 1.297-3.418.058-1.28.072-1.688.072-7.213s-.014-5.934-.072-7.214c-.058-1.278-.33-2.451-1.297-3.418C19.398.402 18.225.13 16.947.072 15.667.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 1 0 0 12.324 6.162 6.162 0 0 0 0-12.324zm0 10.162a4 4 0 1 1 0-8 4 4 0 0 1 0 8zm6.406-11.845a1.44 1.44 0 1 0 0 2.881 1.44 1.44 0 0 0 0-2.881z"/></svg>
          Instagram
        </a>
      </div>
      <p class="text-white/40 text-xs">&copy; {YEAR} ExploreSuriname.com &nbsp;&middot;&nbsp; <a href="{prefix}privacy.html" class="hover:text-white/70 transition">Privacy Policy</a></p>
    </div>
  </div>
</footer>"""

def news_card_html(a, large=False, eager=False):
    img = ""
    if a["image"]:
        h = "h-52" if large else "h-36"
        _loading = 'eager" fetchpriority="high' if eager else "lazy"
        _h_px = "208" if large else "144"
        img = f'<img src="{a["image"]}" alt="" loading="{_loading}" width="400" height="{_h_px}" class="w-full {h} object-cover" onerror="this.style.display=\'none\'">'
    badge = f'<span class="text-white text-xs font-medium px-2 py-0.5 rounded-full" style="background:{a["color"]}">{html_lib.escape(a["source"])}</span>'
    tc = "text-base font-bold" if large else "text-sm font-semibold"
    return (f'<a href="{a["link"]}" target="_blank" rel="noopener noreferrer" '
            f'data-source="{html_lib.escape(a["source"])}" '
            f'class="group flex flex-col bg-white rounded-2xl overflow-hidden card-hover border border-gray-100">'
            f'{img}'
            f'<div class="p-5 flex flex-col gap-2 flex-1">'
            f'<div class="flex items-center gap-2 flex-wrap">{badge}'
            f'<span class="text-gray-400 text-xs">{a["ago"]}</span></div>'
            f'<h3 class="{tc} text-gray-900 group-hover:text-green-800 leading-snug">{html_lib.escape(a["title"])}</h3>'
            f'<p class="text-gray-500 text-xs leading-relaxed flex-1">{html_lib.escape(a["summary"])}</p>'
            f'</div></a>')

def ad_slot(label):
    # Placeholder for ad unit — no visible text shown to users or crawlers
    return '<div class="my-6" aria-hidden="true"></div>'

def nature_card(spot, eager=False):
    tags_html = "".join(
        f'<span class="text-xs px-2 py-0.5 rounded-full font-medium" style="background:var(--mint);color:var(--forest)">{t}</span>'
        for t in spot["tags"]
    )
    internal_url = f"listing/{_nature_slug(spot['name'])}/"
    _loading = 'eager" fetchpriority="high' if eager else "lazy"
    return f"""
<a href="{internal_url}" data-sub="{spot.get('subcat','nature-parks')}" class="listing-card group rounded-2xl overflow-hidden card-hover bg-white border border-gray-100 shadow-sm flex flex-col">
  <div class="relative h-56 overflow-hidden">
    <img src="{spot['image']}" alt="{html_lib.escape(spot['name'])}" loading="{_loading}"
         width="400" height="224"
         class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
         onerror="this.parentElement.style.background='#2D6A4F'">
    <div class="absolute inset-0 bg-gradient-to-t from-black/75 via-black/10 to-transparent"></div>
    <div class="absolute bottom-4 left-4 right-4">
      <h3 class="serif text-white font-bold text-lg leading-tight">{html_lib.escape(spot['name'])}</h3>
      <p class="text-white/75 text-xs mt-1">&#10024; {html_lib.escape(spot['fact'])}</p>
    </div>
  </div>
  <div class="p-5 flex flex-col gap-3 flex-1">
    <p class="text-gray-600 text-sm leading-relaxed flex-1">{html_lib.escape(spot['desc'])}</p>
    <div class="flex flex-wrap gap-1 items-center justify-between">
      <div class="flex flex-wrap gap-1">{tags_html}</div>
      <span class="text-xs font-medium" style="color:var(--forest2)">Learn more &rarr;</span>
    </div>
  </div>
</a>"""

def activity_card_rich(act, eager=False):
    slug = _act_slug(act["name"])
    internal_url = f"listing/{slug}/"
    img = act.get("image", "")
    _loading = 'eager" fetchpriority="high' if eager else "lazy"
    img_html = f'<img src="{img}" alt="{html_lib.escape(act["name"])}" loading="{_loading}" width="400" height="224" class="w-full h-56 object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.style.display=\'none\'">' if img else ""
    return f"""
<a href="{internal_url}" data-sub="{act.get('subcat','tours-expeditions')}" class="listing-card group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover overflow-hidden flex flex-col">
  <div class="relative h-56 overflow-hidden bg-green-900">
    {img_html}
    <div class="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
    <span class="absolute top-4 left-4 text-2xl">{act['icon']}</span>
  </div>
  <div class="p-5 flex flex-col gap-2 flex-1">
    <h3 class="font-bold text-gray-900 text-base group-hover:text-green-800 transition">{html_lib.escape(act['name'])}</h3>
    <p class="text-gray-500 text-sm leading-relaxed flex-1">{html_lib.escape(act['desc'])}</p>
    <span class="text-xs font-semibold mt-1" style="color:var(--forest2)">Find out more &rarr;</span>
  </div>
</a>"""

def activity_card_icon(act):
    url = act.get("url", "#")
    return f"""
<a href="{url}" target="_blank" rel="noopener noreferrer"
   class="flex flex-col items-center text-center p-6 rounded-2xl transition"
   style="background:rgba(255,255,255,0.08)"
   onmouseover="this.style.background='rgba(255,255,255,0.18)'"
   onmouseout="this.style.background='rgba(255,255,255,0.08)'">
  <span class="text-4xl mb-3">{act['icon']}</span>
  <h4 class="serif text-white font-bold text-base mb-2">{html_lib.escape(act['name'])}</h4>
  <p class="text-white/65 text-sm leading-relaxed">{html_lib.escape(act['desc'])}</p>
</a>"""

def poi_card(item, badge_key="cuisine", eager=False):
    url   = item.get("url", "#")
    badge = item.get(badge_key) or item.get("cuisine") or item.get("category", "")
    area  = item.get("area", "Suriname")
    img   = item.get("image", "")
    phone = item.get("phone", "")
    bg, fg = ("var(--mint)", "var(--forest2)") if badge_key == "cuisine" else ("#fff3e8", "#c05621")
    badge_html = f'<span class="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style="background:{bg};color:{fg}">{html_lib.escape(badge)}</span>' if badge else ""
    _loading = 'eager" fetchpriority="high' if eager else "lazy"
    img_html = (f'<div class="w-full h-56 overflow-hidden rounded-t-2xl -mx-0 -mt-0">'
                f'<img src="{img}" alt="{html_lib.escape(item["name"])}" loading="{_loading}" '
                f'width="400" height="224" '
                f'class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" '
                f'onerror="this.parentElement.style.background=\'#2D6A4F\';this.style.display=\'none\'">'
                f'</div>') if img else ""
    phone_html = f'<span class="text-gray-400 text-xs">&#128222; {html_lib.escape(phone)}</span>' if phone else ""
    district   = item.get("area", item.get("location", "Paramaribo"))
    return f"""
<a href="{url}" data-sub="{item.get('subcat','other')}" data-district="{html_lib.escape(district)}" class="listing-card group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover flex flex-col overflow-hidden">
  {img_html}
  <div class="p-4 flex flex-col gap-2 flex-1">
    <div>
      <h3 class="font-bold text-gray-900 text-base leading-tight group-hover:text-green-800 transition">{html_lib.escape(item['name'])}</h3>
    </div>
    <div class="flex items-center justify-between mt-auto pt-2">
      <p class="text-gray-400 text-xs">&#128205; {html_lib.escape(area)}</p>
      {phone_html}
      <span class="text-xs font-semibold" style="color:var(--forest2)">Visit &rarr;</span>
    </div>
  </div>
</a>"""


def _filter_bar_html(items, cat_key):
    """Sticky filter chip bar with subcat + district filtering."""
    from collections import Counter
    sub_counts  = Counter(b.get("subcat","other")     for b in items)
    dist_counts = Counter(b.get("area", b.get("location","Paramaribo")) for b in items)

    chips_cfg  = SUBCATS.get(cat_key, [("all","All","🔍")])

    chips = []
    for key, label, emoji in chips_cfg:
        if key == "all":
            count = len(items)
        else:
            count = sub_counts.get(key, 0)
        if count == 0 and key != "all":
            continue
        active = ' chip-active' if key == "all" else ''
        chips.append(
            f'''<button onclick="filterSub(this,\'{key}\')" class="filter-chip{active}">'''
            f'''{label} <span class="chip-count">{count}</span></button>'''
        )

    # District chips — only show districts that have at least one item
    _DIST_ORDER = ["Paramaribo","Wanica","Commewijne","Para","Nickerie",
                   "Marowijne","Brokopondo","Saramacca","Coronie","Sipaliwini"]
    dist_chips = [f'<button onclick="filterDistrict(this,\'all\')" class="dist-chip dist-chip-active">All districts <span class="chip-count">{len(items)}</span></button>']
    for d in _DIST_ORDER:
        cnt = dist_counts.get(d, 0)
        if cnt > 0:
            dist_chips.append(
                f'<button onclick="filterDistrict(this,\'{d}\')" class="dist-chip">'
                f'{d} <span class="chip-count">{cnt}</span></button>'
            )
    # Any districts not in order list
    for d, cnt in sorted(dist_counts.items()):
        if d not in _DIST_ORDER and cnt > 0:
            dist_chips.append(
                f'<button onclick="filterDistrict(this,\'{d}\')" class="dist-chip">'
                f'{d} <span class="chip-count">{cnt}</span></button>'
            )

    bar_id = f"chipbar-{cat_key}"
    return f"""
<div class="sticky top-16 z-40 pb-2 mb-6" style="background:rgba(249,250,251,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5">
    <!-- Subcat chips -->
    <div class="relative flex items-center gap-1 pt-3">
      <button id="{bar_id}-prev" onclick="chipScroll('{bar_id}',-1)" class="chip-arrow" aria-label="scroll left">&#8249;</button>
      <div id="{bar_id}" class="flex gap-2 overflow-x-auto pb-1" style="scrollbar-width:none;-ms-overflow-style:none;scroll-behavior:smooth">
        {"".join(chips)}
      </div>
      <button id="{bar_id}-next" onclick="chipScroll('{bar_id}',1)" class="chip-arrow" aria-label="scroll right">&#8250;</button>
    </div>
    <!-- District chips -->
    <div class="flex gap-1.5 overflow-x-auto pt-2 pb-1" style="scrollbar-width:none">
      <span class="text-xs font-semibold text-gray-400 self-center shrink-0 mr-1">&#128205; District:</span>
      {"".join(dist_chips)}
    </div>
  </div>
</div>
<style>
.filter-chip {{
  display:inline-flex;align-items:center;gap:5px;padding:10px 16px;border-radius:999px;
  border:1.5px solid #e5e7eb;background:#fff;font-size:.8rem;font-weight:600;
  color:#374151;cursor:pointer;white-space:nowrap;transition:all .15s;flex-shrink:0;
  touch-action:manipulation;
}}
.filter-chip:hover {{ border-color:var(--forest);color:var(--forest); }}
.filter-chip.chip-active {{ background:var(--forest);border-color:var(--forest);color:#fff; }}
.dist-chip {{
  display:inline-flex;align-items:center;gap:4px;padding:5px 12px;border-radius:999px;
  border:1.5px solid #e5e7eb;background:#fff;font-size:.72rem;font-weight:600;
  color:#6b7280;cursor:pointer;white-space:nowrap;transition:all .15s;flex-shrink:0;
}}
.dist-chip:hover {{ border-color:var(--forest2);color:var(--forest2); }}
.dist-chip.dist-chip-active {{ background:var(--forest2);border-color:var(--forest2);color:#fff; }}
.chip-count {{ opacity:.65;font-weight:500;font-size:.75rem; }}
.filter-chip.chip-active .chip-count, .dist-chip.dist-chip-active .chip-count {{ opacity:.8; }}
.chip-arrow {{
  flex-shrink:0;width:28px;height:28px;border-radius:50%;border:1.5px solid #e5e7eb;
  background:#fff;font-size:1.1rem;line-height:1;cursor:pointer;display:flex;
  align-items:center;justify-content:center;color:#6b7280;transition:all .15s;
}}
.chip-arrow:hover {{ border-color:var(--forest);color:var(--forest); }}
.listing-card {{ transition:opacity .2s, transform .2s; }}
.listing-card.hidden {{ display:none; }}
</style>
<script>
var _activeSub  = 'all';
var _activeDist = 'all';

function _applyFilters() {{
  document.querySelectorAll('.listing-card').forEach(function(card) {{
    var subOk  = _activeSub  === 'all' || card.dataset.sub      === _activeSub;
    var distOk = _activeDist === 'all' || card.dataset.district === _activeDist;
    card.classList.toggle('hidden', !(subOk && distOk));
  }});
  var visible = document.querySelectorAll('.listing-card:not(.hidden)').length;
  var lbl = document.getElementById('result-count');
  if (lbl) lbl.textContent = visible + ' results';

  /* ── Update district chip counts dynamically ── */
  var distCounts = {{}};
  var totalVisible = 0;
  document.querySelectorAll('.listing-card').forEach(function(card) {{
    var subOk = _activeSub === 'all' || card.dataset.sub === _activeSub;
    if (!subOk) return;
    var d = card.dataset.district || 'Paramaribo';
    distCounts[d] = (distCounts[d] || 0) + 1;
    totalVisible++;
  }});
  document.querySelectorAll('.dist-chip').forEach(function(btn) {{
    var dist = btn.getAttribute('onclick').match(/'([^']+)'\s*\)/);
    if (!dist) return;
    dist = dist[1];
    var countEl = btn.querySelector('.chip-count');
    if (dist === 'all') {{
      if (countEl) countEl.textContent = totalVisible;
    }} else {{
      var c = distCounts[dist] || 0;
      if (countEl) countEl.textContent = c;
      btn.style.display = c > 0 ? '' : 'none';
      /* if active district now has 0 results, reset to all */
      if (c === 0 && _activeDist === dist) {{
        _activeDist = 'all';
        document.querySelectorAll('.dist-chip').forEach(function(b) {{ b.classList.remove('dist-chip-active'); }});
        var allBtn = document.querySelector('.dist-chip');
        if (allBtn) allBtn.classList.add('dist-chip-active');
      }}
    }}
  }});
}}

function chipScroll(id, dir) {{
  var el = document.getElementById(id);
  if (el) el.scrollBy({{left: dir * 200, behavior: 'smooth'}});
}}

function filterSub(btn, key) {{
  _activeSub = key;
  document.querySelectorAll('.filter-chip').forEach(function(b) {{ b.classList.remove('chip-active'); }});
  btn.classList.add('chip-active');
  _applyFilters();
}}

function filterDistrict(btn, dist) {{
  _activeDist = dist;
  document.querySelectorAll('.dist-chip').forEach(function(b) {{ b.classList.remove('dist-chip-active'); }});
  btn.classList.add('dist-chip-active');
  _applyFilters();
}}
</script>"""

def listing_page(title, subtitle, meta_desc, items, cards_html, bg_color="var(--forest)", page_file="", extra_html="", filter_bar="", og_image=None, lcp_image=None, seo_title=None):
    _page_active = page_file.replace(".html", "") if page_file else "home"
    page_url = f"{SITE_URL}/{page_file}"
    _og_img = og_image or f"{SITE_URL}/og-image.jpg"
    _seo_title = seo_title or title
    _lcp_preload = f'  <link rel="preload" as="image" href="{lcp_image}" fetchpriority="high">\n' if lcp_image else ""
    return f"""{PAGE_HEAD}
  <title>{_seo_title} | ExploreSuriname.com</title>
  <meta name="description" content="{html_lib.escape(meta_desc)}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{page_url}">
  <meta property="og:title" content="{_seo_title} | ExploreSuriname.com">
  <meta property="og:description" content="{html_lib.escape(meta_desc)}">
  <meta property="og:image" content="{{_og_img}}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{_seo_title} | ExploreSuriname.com">
  <meta name="twitter:description" content="{html_lib.escape(meta_desc)}">
  <meta name="twitter:image" content="{{_og_img}}">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"ItemList","name":"{title}","url":"{page_url}","numberOfItems":{len(items)},"itemListElement":[{",".join(
    '{"@type":"ListItem","position":' + str(i+1) + ',"name":' + __import__("json").dumps(it.get("name","")) + ',"url":"' + SITE_URL + "/" + it.get("url","") + '"}' for i,it in enumerate(items[:20])
  )}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"{title}","item":"{page_url}"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"{_seo_title} | ExploreSuriname.com","url":"{page_url}","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
{_lcp_preload}</head>
<body class="bg-gray-50">
{nav_html(_page_active)}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:{bg_color}">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">{title}</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">{subtitle}</p>
</div>
<main class="max-w-6xl mx-auto px-5 py-12 pb-24">
  {filter_bar}
  <div id="result-count" class="text-sm text-gray-400 mb-4 font-medium">{len(items)} results</div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
    {cards_html}
  </div>
  {extra_html}
</main>
{footer_html()}
</body>
</html>"""

# -- Page builders ------------------------------------------------------------

_FEATURED_HOTELS      = ["royal-torarica","courtyard-by-marriott","eco-torarica","torarica-resort","hotel-peperpot","radisson-hotel"]
_FEATURED_RESTAURANTS = ["de-gadri","baka-foto-restaurant","goe-thai-noodle-bar","passion-food-and-wines","el-patron-latin-grill","zus-zo-cafe"]
_FEATURED_SHOPPING    = ["international-mall-of-suriname","hermitage-mall","readytex-souvenirs-and-crafts","kirpalani","galaxy","digital-world-maretraite-mall"]

def _pick_featured(lst, slugs):
    """Return items from lst ordered by the given slug list, skipping missing slugs."""
    lut = {b["slug"]: b for b in lst}
    return [lut[s] for s in slugs if s in lut]

def build_index(restaurants, hotels):
    nature_cards   = "\n".join(nature_card(s, eager=(i==0))         for i,s in enumerate(NATURE_SPOTS[:6]))
    activity_cards = "\n".join(activity_card_rich(a, eager=(i==0)) for i,a in enumerate(ACTIVITIES[:6]))
    rest_cards     = "\n".join(poi_card(r, "cuisine",  eager=(i==0)) for i,r in enumerate(_pick_featured(RESTAURANTS, _FEATURED_RESTAURANTS)))
    hotel_cards    = "\n".join(poi_card(h, "category", eager=(i==0)) for i,h in enumerate(_pick_featured(HOTELS,      _FEATURED_HOTELS)))
    shop_cards     = "\n".join(poi_card(s, eager=(i==0))             for i,s in enumerate(_pick_featured(SHOPPING,    _FEATURED_SHOPPING)))
    more_btn = lambda href, label: f'<a href="{href}" class="inline-flex items-center gap-1 px-6 py-3 rounded-full text-sm font-semibold border-2 transition hover:opacity-80" style="border-color:var(--forest2);color:var(--forest2)">{label} &rarr;</a>'
    return f"""{PAGE_HEAD}
  <title>Explore Suriname | South America's Hidden Gem</title>
  <meta name="description" content="Plan your Suriname trip: rainforest lodges, Paramaribo restaurants, local tours, shopping and live SRD exchange rates. Guide to South America's hidden gem.">
  <link rel="canonical" href="{SITE_URL}/">
  <link rel="preload" as="image" href="/images/hero-home.webp" fetchpriority="high">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/">
  <meta property="og:title" content="Explore Suriname | South America's Hidden Gem">
  <meta property="og:description" content="Rainforest lodges, Paramaribo restaurants, local tours, shopping and live SRD exchange rates. Your complete guide to Suriname.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Explore Suriname | South America's Hidden Gem">
  <meta name="twitter:description" content="Rainforest lodges, Paramaribo restaurants, local tours, shopping and live SRD exchange rates. Your complete guide to Suriname.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Explore Suriname",
    "alternateName": "ExploreSuriname.com",
    "url": "{SITE_URL}/",
    "logo": {{
      "@type": "ImageObject",
      "url": "{SITE_URL}/og-image.jpg",
      "width": 1200,
      "height": 630
    }},
    "description": "Your complete travel and lifestyle guide to Suriname: hotels, restaurants, nature, activities and live SRD exchange rates.",
    "areaServed": {{
      "@type": "Country",
      "name": "Suriname",
      "sameAs": "https://en.wikipedia.org/wiki/Suriname"
    }},
    "knowsAbout": ["Suriname", "Paramaribo", "Travel", "Restaurants", "Hotels", "Tourism"]
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": "Explore Suriname",
    "alternateName": "ExploreSuriname.com",
    "url": "{SITE_URL}/",
    "description": "Your complete travel and lifestyle guide to Suriname: hotels, restaurants, nature, activities and live SRD exchange rates.",
    "inLanguage": "en",
    "about": {{
      "@type": "Place",
      "name": "Suriname",
      "sameAs": "https://en.wikipedia.org/wiki/Suriname"
    }},
    "potentialAction": {{
      "@type": "SearchAction",
      "target": {{
        "@type": "EntryPoint",
        "urlTemplate": "{SITE_URL}/?s={{search_term_string}}"
      }},
      "query-input": "required name=search_term_string"
    }}
  }}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"Explore Suriname | South America's Hidden Gem","url":"{SITE_URL}/","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
</head>
<body class="bg-white overflow-x-hidden">
{nav_html("home")}
<section class="relative min-h-screen flex items-center justify-center hero-bg"
  style="background-image:url('/images/hero-home.webp')">
  <div class="absolute inset-0" style="background:linear-gradient(to bottom,rgba(0,0,0,.15) 0%,rgba(0,0,0,.55) 60%,rgba(0,0,0,.82) 100%)"></div>
  <div class="relative z-10 text-center text-white px-5 max-w-4xl mx-auto" style="padding-top:5rem;padding-bottom:6rem">
    <p class="text-xs font-semibold tracking-widest uppercase mb-6" style="color:var(--coral)">South America&apos;s Hidden Gem</p>
    <h1 class="serif font-black leading-tight mb-6" style="font-size:clamp(2.5rem,8vw,5.5rem)">The Amazon&#8217;s<br>Best-Kept Secret</h1>
    <p class="text-xl font-light leading-relaxed mb-10 max-w-2xl mx-auto text-white/90">94% pristine rainforest. Unmatched biodiversity. Two UNESCO World Heritage Sites. Welcome to Suriname.</p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <a href="#nature" class="px-8 py-4 rounded-full font-semibold text-lg text-white hover:opacity-90 transition shadow-lg" style="background:var(--forest)">Start Exploring</a>
      <a href="#travel-tools" class="px-8 py-4 rounded-full font-semibold text-lg text-white border-2 hover:bg-white/10 transition" style="border-color:rgba(255,255,255,.6)">Travel Tools</a>
    </div>
  </div>
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-white/50 text-xs">
    <span>Scroll to explore</span>
    <svg class="w-4 h-4 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="2"><path d="M19 9l-7 7-7-7"/></svg>
  </div>
</section>
<section style="background:var(--forest)" class="text-white py-7">
  <div class="max-w-5xl mx-auto px-5 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Climate</p><p class="font-semibold">Tropical, ~28&#176;C</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Forest Cover</p><p class="font-semibold">94% Rainforest</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">UNESCO Sites</p><p class="font-semibold">2 World Heritage Sites</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Bird Species</p><p class="font-semibold">700+ Species</p></div>
  </div>
</section>
<section class="py-10 bg-white border-b border-gray-100">
  <div class="max-w-2xl mx-auto px-5 text-center">
    <p class="text-gray-500 text-base leading-relaxed">This isn&apos;t just a directory. It&apos;s a living record of the people and places moving Suriname forward. We find the details so you can find the experience.</p>
  </div>
</section>
<section id="nature" class="py-12 md:py-24 bg-gray-50">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10 md:mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Natural Wonders</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Suriname&apos;s Wild Side</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname protects more of its original forest than any other country on earth.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{nature_cards}</div>
    <div class="text-center mt-10">{more_btn("nature.html", f"View all {len(NATURE_SPOTS) + len(SIGHTSEEING)} nature spots")}</div>
  </div>
</section>
<section id="activities" class="py-12 md:py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10 md:mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Out &amp; About</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Things to Do</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Jungle treks, river tours, city walks, turtle watching and more.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{activity_cards}</div>
    <div class="text-center mt-10">{more_btn("activities.html", f"View all {len(ACTIVITIES) + len(ADVENTURES_BIZ)} activities")}</div>
  </div>
</section>
<section id="dining" class="py-12 md:py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10 md:mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Eat &amp; Drink</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Where to Eat</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname&apos;s cuisine is as diverse as its people — Creole, Hindustani, Javanese, Chinese and Maroon flavors.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{rest_cards}</div>
    <div class="text-center mt-10">{more_btn("restaurants.html", f"View all {len(RESTAURANTS)} restaurants")}</div>
  </div>
</section>
<section id="hotels" class="py-12 md:py-24" style="background:var(--mint)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10 md:mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Where to Stay</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Hotels &amp; Lodges</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">From 5-star riverside hotels to remote jungle lodges only reachable by canoe.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{hotel_cards}</div>
    <div class="text-center mt-10">{more_btn("hotels.html", f"View all {len(HOTELS)} hotels &amp; lodges")}</div>
  </div>
</section>
<section id="shopping" class="py-12 md:py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10 md:mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Retail &amp; Souvenirs</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Shopping</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Malls, craft markets and local boutiques &mdash; from handmade souvenirs to everyday essentials.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{shop_cards}</div>
    <div class="text-center mt-10">{more_btn("shopping.html", f"View all {len(SHOPPING)} shops")}</div>
  </div>
</section>
<section id="travel-tools" class="py-12 md:py-20 bg-gray-50">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-10">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Plan Your Visit</p>
      <h2 class="serif text-3xl sm:text-4xl font-bold text-gray-900 mb-3">Travel Tools</h2>
      <p class="text-gray-500 text-base max-w-xl mx-auto">Exchange rates, flights, weather, road conditions, tides and Suriname news in one place.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      <a href="currency.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><circle cx="12" cy="12" r="9"/><path d="M14.5 9a3.5 2 0 1 0 0 6 3.5 2 0 1 0 0-6"/><path d="M12 7v2M12 15v2"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">Market Rates</p>
          <p class="text-gray-500 text-sm leading-relaxed">SRD exchange rates from CME and CBVS, plus live gold spot price in USD and SRD.</p>
        </div>
      </a>
      <a href="flights.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">Flights</p>
          <p class="text-gray-500 text-sm leading-relaxed">Arrivals and departures at Johan Adolf Pengel (PBM) and Eduard Alexander Gummels (EAX).</p>
        </div>
      </a>
      <a href="conditions.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/><circle cx="12" cy="12" r="4"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">Weather &amp; Tides</p>
          <p class="text-gray-500 text-sm leading-relaxed">7-day district forecasts, river tidal predictions and daily sunrise &amp; sunset times.</p>
        </div>
      </a>
      <a href="news.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><path d="M4 22h16a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v16a2 2 0 0 1-2 2zm0 0a2 2 0 0 1-2-2v-9c0-1.1.9-2 2-2h2"/><path d="M18 14h-8M15 18h-5M10 6h8v4h-8z"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">Suriname News</p>
          <p class="text-gray-500 text-sm leading-relaxed">Local news in Dutch, Oil &amp; Gas updates (Staatsolie, Block 58, offshore) and English-language Finance &amp; Economy coverage.</p>
        </div>
      </a>
      <a href="visitor-guide.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">Visitor Guide</p>
          <p class="text-gray-500 text-sm leading-relaxed">Visas, customs, SIM cards, ATMs, taxi apps and mobile payments for first-time visitors.</p>
        </div>
      </a>
      <a href="on-the-road.html" class="group flex flex-col gap-5 p-7 rounded-2xl bg-white border border-gray-100 hover:border-gray-300 hover:shadow-sm transition">
        <div class="flex items-start justify-between">
          <div class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0" style="background:var(--mint)">
            <svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="color:var(--forest2)"><path d="M3 17l2-8h14l2 8"/><path d="M3 17h18"/><circle cx="7.5" cy="17" r="1.5"/><circle cx="16.5" cy="17" r="1.5"/><path d="M10 9v4M14 9v4"/></svg>
          </div>
          <svg class="w-4 h-4 text-gray-300 group-hover:text-gray-400 transition mt-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7"/></svg>
        </div>
        <div>
          <p class="font-semibold text-gray-900 mb-1">On the Road</p>
          <p class="text-gray-500 text-sm leading-relaxed">Live traffic via Waze, road rules, rainy season advisories, emergency numbers and what to do after an accident.</p>
        </div>
      </a>
    </div>
  </div>
</section>
{footer_html()}
</body>
</html>"""

def build_nature_page():
    nature_cards = "\n".join(nature_card(s, eager=(i==0)) for i,s in enumerate(NATURE_SPOTS))
    sight_cards  = "\n".join(poi_card(b) for b in SIGHTSEEING)
    all_cards    = nature_cards + "\n" + sight_cards
    # build filter bar from combined list (nature spots default to "nature-parks" subcat)
    combined_items = [{"subcat": s.get("subcat", "nature-parks")} for s in NATURE_SPOTS] + list(SIGHTSEEING)
    filter_bar_s = _filter_bar_html(combined_items, "sightseeing")
    total = len(NATURE_SPOTS) + len(SIGHTSEEING)
    return listing_page("Nature & Parks", f"{total} destinations across Suriname's pristine wilderness",
        f"Explore {total} nature reserves, national parks and rainforest destinations in Suriname. From Central Suriname Reserve to Brownsberg. Plan your eco-adventure.",
        NATURE_SPOTS, all_cards, page_file="nature.html", extra_html="", filter_bar=filter_bar_s,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG",
        lcp_image=NATURE_SPOTS[0]["image"] if NATURE_SPOTS else None, seo_title="Nature Parks & Wildlife Reserves in Suriname")

def build_activities_page():
    # Merge ACTIVITIES and ADVENTURES_BIZ sorted alphabetically by name
    tagged = (
        [(a["name"].lower(), "activity", a) for a in ACTIVITIES] +
        [(b["name"].lower(), "biz",      b) for b in ADVENTURES_BIZ]
    )
    tagged.sort(key=lambda x: x[0])
    all_cards = "\n".join(
        (activity_card_rich(item, eager=(i==0)) if kind == "activity" else poi_card(item, eager=(i==0)))
        for i, (_, kind, item) in enumerate(tagged)
    )
    _first_img = next((item.get("image","") for _,_,item in tagged if item.get("image")), None)
    combined_items = [{"subcat": a.get("subcat", "tours-expeditions")} for a in ACTIVITIES] + list(ADVENTURES_BIZ)
    filter_bar_a = _filter_bar_html(combined_items, "adventure")
    total = len(ACTIVITIES) + len(ADVENTURES_BIZ)
    return listing_page("Activities", f"{total} things to do in Suriname",
        f"Discover {total} things to do in Suriname: jungle tours, river trips, birdwatching, kayaking and more. Find tours and adventure operators in Paramaribo.",
        ACTIVITIES, all_cards, bg_color="var(--forest2)", page_file="activities.html", extra_html="", filter_bar=filter_bar_a,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg",
        lcp_image=_first_img, seo_title="Things to Do in Suriname: Tours and Treks")

def build_restaurants_page(restaurants):
    cards = "\n".join(poi_card(r, "cuisine", eager=(i==0)) for i,r in enumerate(restaurants))
    fb    = _filter_bar_html(restaurants, "restaurant")
    _lcp  = restaurants[0].get("image") if restaurants else None
    return listing_page("Eat & Drink", f"{len(restaurants)} places to eat & drink in Suriname",
        f"Browse {len(restaurants)} restaurants, cafes, bars and fast food in Suriname. Find local Surinamese food, Asian cuisine, coffee shops and more.",
        restaurants, cards, bg_color="#7c3aed", page_file="restaurants.html", filter_bar=fb,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/2016_0624_Tjauw_min_moksie_meti_speciaal.jpg/1280px-2016_0624_Tjauw_min_moksie_meti_speciaal.jpg",
        lcp_image=_lcp, seo_title="Restaurants in Paramaribo, Suriname")

def build_hotels_page(hotels):
    cards = "\n".join(poi_card(h, "category", eager=(i==0)) for i,h in enumerate(hotels))
    fb    = _filter_bar_html(hotels, "hotel")
    _lcp  = hotels[0].get("image") if hotels else None
    return listing_page("Hotels & Lodges", f"{len(hotels)} places to stay in Suriname",
        f"Browse {len(hotels)} hotels, eco-lodges and jungle retreats in Suriname. From Paramaribo city hotels to remote river resorts. Find your perfect stay.",
        hotels, cards, bg_color="#c05621", page_file="hotels.html", filter_bar=fb,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Bigi_Pan_Nature_Reserve_%282719369111%29.jpg/1280px-Bigi_Pan_Nature_Reserve_%282719369111%29.jpg",
        lcp_image=_lcp, seo_title="Hotels in Suriname: City and Jungle Lodges")

def build_shopping_page():
    cards = "\n".join(poi_card(b, eager=(i==0)) for i,b in enumerate(SHOPPING))
    fb    = _filter_bar_html(SHOPPING, "shopping")
    _lcp  = SHOPPING[0].get("image") if SHOPPING else None
    return listing_page("Shopping", f"{len(SHOPPING)} shops & stores in Suriname",
        f"Discover {len(SHOPPING)} shops in Suriname: supermarkets, malls, fashion, electronics, furniture, butchers and specialty stores in Paramaribo.",
        SHOPPING, cards, bg_color="#7c3aed", page_file="shopping.html", filter_bar=fb,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png",
        lcp_image=_lcp, seo_title="Shopping in Paramaribo, Suriname")

def build_services_page():
    cards = "\n".join(poi_card(b, eager=(i==0)) for i,b in enumerate(SERVICES))
    fb    = _filter_bar_html(SERVICES, "service")
    _lcp  = SERVICES[0].get("image") if SERVICES else None
    return listing_page("Services", f"{len(SERVICES)} service providers in Suriname",
        f"Find {len(SERVICES)} service providers in Suriname: banks, beauty, health, fitness, education, telecom, real estate and more.",
        SERVICES, cards, bg_color="#0369a1", page_file="services.html", filter_bar=fb,
        og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png",
        lcp_image=_lcp, seo_title="Local Services in Paramaribo, Suriname")

def build_currency_page(cme_rates, cme_live, cme_updated, cbvs_rates, cbvs_live, cbvs_updated, brent_price=None, brent_updated=None):
    import json as _json
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")
    buy_json  = _json.dumps({r["currency"]: float(r["buy"])  for r in cme_rates})
    sell_json = _json.dumps({r["currency"]: float(r["sell"]) for r in cme_rates})

    # USD→SRD rate baked in for gold price SRD equivalent
    usd_buy_srd = next((float(r["buy"]) for r in cme_rates if r["currency"] == "USD"), 37.5)

    # Brent crude baked values
    if brent_price is not None:
        brent_usd_str = f"${brent_price:,.2f}"
        brent_srd_str = f"{brent_price * usd_buy_srd:,.0f} SRD"
        brent_grid_html = f'''<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">USD / barrel</p>
        <p class="text-2xl font-bold font-mono text-gray-900">{brent_usd_str}</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">SRD / barrel</p>
        <p class="text-2xl font-bold font-mono text-gray-900">{brent_srd_str}</p>
      </div>
    </div>'''
        oil_badge_html = f'<span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800 shrink-0">&#9679; {brent_updated}</span>'
    else:
        brent_grid_html = '<p class="text-gray-400 text-sm">Price unavailable &mdash; will update on next rebuild.</p>'
        oil_badge_html = '<span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0">Unavailable</span>'

    def badge(is_live):
        if is_live:
            return '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">&#9679; Live</span>'
        return '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">&#9675; Estimated</span>'

    cbvs_rows = ""
    cbvs_cards = ""
    for r in cbvs_rates:
        cbvs_rows += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 font-semibold text-gray-900 whitespace-nowrap">{r["flag"]} {r["currency"]}</td>'
            f'<td class="py-3 px-4 text-gray-500 text-sm">{html_lib.escape(r["name"])}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold text-gray-800">{r["buy"]}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold text-gray-800">{r["sell"]}</td>'
            '</tr>'
        )
        cbvs_cards += (
            '<div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0 px-4">'
            '<div>'
            f'<p class="font-semibold text-gray-900 text-sm">{r["flag"]} {r["currency"]}</p>'
            f'<p class="text-gray-500 text-xs mt-0.5">{html_lib.escape(r["name"])}</p>'
            '</div>'
            '<div class="text-right">'
            f'<p class="font-mono font-bold text-gray-800 text-sm">{r["buy"]} <span class="text-gray-300">/</span> {r["sell"]}</p>'
            '<p class="text-gray-400 text-xs mt-0.5">buy / sell</p>'
            '</div>'
            '</div>'
        )

    cme_rows = ""
    cme_cards = ""
    for r in cme_rates:
        cme_rows += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 font-semibold text-gray-900 whitespace-nowrap">{r["flag"]} {r["currency"]}</td>'
            f'<td class="py-3 px-4 text-gray-500 text-sm">{html_lib.escape(r["name"])}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold" style="color:var(--forest2)">{r["buy"]}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold" style="color:var(--coral)">{r["sell"]}</td>'
            '</tr>'
        )
        cme_cards += (
            '<div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0 px-4">'
            '<div>'
            f'<p class="font-semibold text-gray-900 text-sm">{r["flag"]} {r["currency"]}</p>'
            f'<p class="text-gray-500 text-xs mt-0.5">{html_lib.escape(r["name"])}</p>'
            '</div>'
            '<div class="text-right">'
            f'<p class="font-mono font-bold text-sm"><span style="color:var(--forest2)">{r["buy"]}</span>'
            f'<span class="text-gray-300 mx-1">/</span>'
            f'<span style="color:var(--coral)">{r["sell"]}</span></p>'
            '<p class="text-gray-400 text-xs mt-0.5">buy / sell</p>'
            '</div>'
            '</div>'
        )

    from_opts = ""
    for r in cme_rates:
        sel = " selected" if r["currency"] == "USD" else ""
        from_opts += f'<option value="{r["currency"]}"{sel}>{r["flag"]} {r["currency"]} – {html_lib.escape(r["name"])}</option>\n'
    from_opts += '<option value="SRD">\U0001f1f8\U0001f1f7 SRD – Surinamese Dollar</option>'

    to_opts = '<option value="SRD" selected>\U0001f1f8\U0001f1f7 SRD – Surinamese Dollar</option>\n'
    for r in cme_rates:
        to_opts += f'<option value="{r["currency"]}">{r["flag"]} {r["currency"]} – {html_lib.escape(r["name"])}</option>\n'

    js = f"""const BUY  = {buy_json};
const SELL = {sell_json};
function toSRD(a,c){{return BUY[c]!=null?a*BUY[c]:null;}}
function fromSRD(a,c){{return SELL[c]!=null?a/SELL[c]:null;}}
function doConvert(){{
  var amt=parseFloat(document.getElementById('cv-amt').value);
  var from=document.getElementById('cv-from').value;
  var to=document.getElementById('cv-to').value;
  var rEl=document.getElementById('cv-result');
  var nEl=document.getElementById('cv-note');
  if(isNaN(amt)||amt<0){{rEl.textContent='—';nEl.textContent='Enter a valid amount';return;}}
  var result,note;
  if(from===to){{result=amt;note='Same currency';}}
  else if(from==='SRD'){{result=fromSRD(amt,to);note=SELL[to]?'CME: 1 '+to+' costs '+SELL[to]+' SRD':'Rate unavailable';}}
  else if(to==='SRD'){{result=toSRD(amt,from);note=BUY[from]?'CME: 1 '+from+' = '+BUY[from]+' SRD':'Rate unavailable';}}
  else{{var srd=toSRD(amt,from);result=srd!=null?fromSRD(srd,to):null;var cross=(BUY[from]&&SELL[to])?(BUY[from]/SELL[to]).toFixed(4):'?';note='Via SRD: 1 '+from+' ≈ '+cross+' '+to;}}
  if(result==null){{rEl.textContent='N/A';nEl.textContent='Rate not available';}}
  else{{rEl.textContent=result.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}})+' '+to;nEl.textContent=note;}}
}}
doConvert();"""

    return f"""{PAGE_HEAD}
  <title>SRD to USD Today | Surinamese Dollar Exchange Rates | Explore Suriname</title>
  <meta name="description" content="Live Surinamese Dollar (SRD) exchange rates. CBVS official rates updated 3× daily, CME cash rates updated continuously. Free currency converter.">
  <link rel="canonical" href="{SITE_URL}/currency.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/currency.html">
  <meta property="og:title" content="SRD to USD Today | Surinamese Dollar Exchange Rates | Explore Suriname">
  <meta property="og:description" content="Live Surinamese Dollar (SRD) exchange rates. CBVS official rates updated 3× daily, CME cash rates updated continuously.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="SRD to USD Today | Surinamese Dollar Exchange Rates | Explore Suriname">
  <meta name="twitter:description" content="Live Surinamese Dollar (SRD) exchange rates. CBVS official rates updated 3× daily, CME cash rates updated continuously.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"SRD to USD Today | Surinamese Dollar Exchange Rates","url":"{SITE_URL}/currency.html","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"SRD Exchange Rates","item":"{SITE_URL}/currency.html"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Dataset","name":"Surinamese Dollar (SRD) Exchange Rates","description":"Live SRD exchange rates from CBVS (Central Bank of Suriname) and CME (Central Money Exchange), updated multiple times daily on business days.","url":"{SITE_URL}/currency.html","creator":{{"@type":"Organization","name":"Explore Suriname","url":"{SITE_URL}"}},"spatialCoverage":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"variableMeasured":[{{"@type":"PropertyValue","name":"SRD/USD exchange rate"}},{{"@type":"PropertyValue","name":"SRD/EUR exchange rate"}},{{"@type":"PropertyValue","name":"SRD/GBP exchange rate"}},{{"@type":"PropertyValue","name":"SRD/BRL exchange rate"}}],"isAccessibleForFree":true,"dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}"}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {{"@type":"Question","name":"What currency is used in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"The official currency of Suriname is the Surinamese Dollar (SRD). Most everyday transactions, including markets, local restaurants and minibuses, require SRD. Some hotels and larger shops also accept USD or EUR, but you will receive change in SRD."}}}},
    {{"@type":"Question","name":"Can I use US dollars or euros in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"USD and EUR are accepted at hotels, some restaurants, and larger shops in Paramaribo. However, for local markets, street food, and public transport you will need Surinamese Dollars (SRD). It is advisable to exchange money upon arrival."}}}},
    {{"@type":"Question","name":"Where can I exchange money in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Money can be exchanged at licensed cambios (exchange offices) throughout Paramaribo, at major banks such as Hakrinbank and DSB Bank, and at the Johan Adolf Pengel International Airport. Cambios typically offer competitive rates. ATMs dispensing SRD are widely available in Paramaribo."}}}},
    {{"@type":"Question","name":"What is the official SRD exchange rate?","acceptedAnswer":{{"@type":"Answer","text":"The official exchange rate is set by the Central Bank of Suriname (CBVS) and published on business days. Cash market rates (CME) may differ slightly. Check the live rates on this page for the most current CBVS and cash market exchange rates."}}}},
    {{"@type":"Question","name":"Can I pay by credit or debit card in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Credit and debit cards are accepted at larger hotels, supermarkets and some restaurants in Paramaribo. Visa and Mastercard are the most widely accepted. For markets, street food, minibuses and smaller shops you will need cash in SRD. It is advisable to carry local cash at all times."}}}},
    {{"@type":"Question","name":"What is the SRD to EUR exchange rate today?","acceptedAnswer":{{"@type":"Answer","text":"The current SRD to EUR exchange rate is shown in real time on this page using CBVS official rates and CME cash market rates. The CBVS rate is the central bank reference; the CME rate reflects what you will receive at cash exchange offices in Paramaribo."}}}},
    {{"@type":"Question","name":"Is tipping customary in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Tipping is not mandatory in Suriname but is appreciated for good service. A tip of 5 to 10 percent is common at restaurants that do not include a service charge. Taxi drivers do not typically expect a tip, but rounding up the fare is a common courtesy."}}}}
  ]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("currency")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">SRD Exchange Rates</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">SRD exchange rates &mdash; CBVS 3&times; daily &bull; CME continuous &bull; live gold spot price</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">
  <div class="rounded-2xl border border-amber-200 p-6 mb-8" style="background:#fffbeb">
    <p class="text-amber-900 text-sm leading-relaxed">
      <strong class="text-amber-800">&#128161; What&apos;s the difference?</strong>
      <strong>CBVS</strong> is the Central Bank of Suriname&apos;s official reference rate used for banking.
      <strong>CME</strong> (Central Money Exchange) shows cash rates at local exchange offices &mdash; what you actually get when exchanging banknotes.
      &ldquo;We Buy&rdquo; is what they pay when you sell foreign currency; &ldquo;We Sell&rdquo; is what you pay to buy foreign currency.
    </p>
  </div>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-10">
    <h2 class="serif text-2xl font-bold text-gray-900 mb-1">Currency Converter</h2>
    <p class="text-gray-400 text-sm mb-7">Using CME cash rates &mdash; typical exchange-office rates</p>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 items-end">
      <div>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">Amount</label>
        <input id="cv-amt" type="number" value="100" min="0" step="any"
               class="w-full border border-gray-200 rounded-xl px-4 py-3 text-xl font-mono font-bold text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-200"
               oninput="doConvert()">
      </div>
      <div>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">From</label>
        <select id="cv-from" onchange="doConvert()"
                class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-200 bg-white">
          {from_opts}
        </select>
      </div>
      <div>
        <label class="block text-xs font-semibold text-gray-500 uppercase tracking-widest mb-2">To</label>
        <select id="cv-to" onchange="doConvert()"
                class="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-200 bg-white">
          {to_opts}
        </select>
      </div>
    </div>
    <div class="mt-6 p-5 rounded-xl text-center" style="background:var(--mint)">
      <p id="cv-result" class="text-3xl font-bold text-gray-900 font-mono">&#8212;</p>
      <p id="cv-note"   class="text-xs mt-1" style="color:var(--forest2)">Enter an amount above</p>
    </div>
    <p class="text-gray-400 text-xs text-center mt-3">Rates are indicative only &mdash; confirm with your exchange office before transacting</p>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden order-2 lg:order-1">
      <div class="px-6 py-5 border-b border-gray-100">
        <div class="flex items-start justify-between gap-2">
          <div>
            <p class="font-bold text-gray-900 text-base">CBVS Official Rates {badge(cbvs_live)}</p>
            <p class="text-gray-400 text-xs mt-0.5">Central Bank of Suriname &mdash; reference rate</p>
          </div>
          <a href="https://www.cbvs.sr" target="_blank" rel="noopener noreferrer"
             class="text-xs font-semibold shrink-0 hover:underline" style="color:var(--forest2)">cbvs.sr &#8599;</a>
        </div>
        <p class="text-gray-400 text-xs mt-2">&#128336; {html_lib.escape(cbvs_updated)}</p>
      </div>
      <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="bg-gray-50 text-left">
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Code</th>
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Currency</th>
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Buy SRD</th>
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Sell SRD</th>
          </tr></thead>
          <tbody>{cbvs_rows}</tbody>
        </table>
      </div>
      <div class="sm:hidden py-1">{cbvs_cards}</div>
    </div>
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden order-1 lg:order-2">
      <div class="px-6 py-5 border-b border-gray-100">
        <div class="flex items-start justify-between gap-2">
          <div>
            <p class="font-bold text-gray-900 text-base">CME Cash Rates {badge(cme_live)}</p>
            <p class="text-gray-400 text-xs mt-0.5">Central Money Exchange &mdash; local market rate</p>
          </div>
          <a href="https://www.cme.sr" target="_blank" rel="noopener noreferrer"
             class="text-xs font-semibold shrink-0 hover:underline" style="color:var(--forest2)">cme.sr &#8599;</a>
        </div>
        <p class="text-gray-400 text-xs mt-2">&#128336; {html_lib.escape(cme_updated)}</p>
      </div>
      <div class="hidden sm:block overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="bg-gray-50 text-left">
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Code</th>
            <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Currency</th>
            <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wide text-right" style="color:var(--forest2)">We Buy</th>
            <th class="py-3 px-4 text-xs font-semibold uppercase tracking-wide text-right" style="color:var(--coral)">We Sell</th>
          </tr></thead>
          <tbody>{cme_rows}</tbody>
        </table>
      </div>
      <div class="sm:hidden py-1">{cme_cards}</div>
    </div>
  </div>
  <p class="text-center text-gray-400 text-xs mt-8 max-w-2xl mx-auto leading-relaxed px-4">
    Rates are for informational purposes only. Always confirm the current rate before transacting. Page updates daily.
  </p>

  <!-- Gold price ─────────────────────────────────────────────────────────── -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mt-8">
    <div class="flex items-start justify-between mb-5">
      <div>
        <h2 class="serif text-2xl font-bold text-gray-900">&#129351; Gold Price</h2>
        <p class="text-gray-400 text-sm mt-1">XAU — spot price, live from markets &mdash; via <a href="https://gold-api.com" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">gold-api.com</a></p>
      </div>
      <span id="gold-badge" class="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0">Loading…</span>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">USD / troy oz</p>
        <p id="gold-usd" class="text-2xl font-bold font-mono text-gray-900">—</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">SRD / troy oz</p>
        <p id="gold-srd" class="text-2xl font-bold font-mono text-gray-900">—</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">USD / gram</p>
        <p id="gold-usdg" class="text-xl font-bold font-mono text-gray-900">—</p>
      </div>
    </div>
    <p class="text-gray-400 text-xs mt-4">Suriname is one of the world&apos;s leading gold producers per capita. SRD equivalent uses today&apos;s CME USD buy rate ({usd_buy_srd:.2f}). Price updates on each page load.</p>
  </div>
  <!-- Oil price ──────────────────────────────────────────────────────────── -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mt-6">
    <div class="flex items-start justify-between mb-5">
      <div>
        <h2 class="serif text-2xl font-bold text-gray-900">&#128739;&#xFE0E; Brent Crude Oil</h2>
        <p class="text-gray-400 text-sm mt-1">Brent Crude &mdash; updated hourly</p>
      </div>
      {oil_badge_html}
    </div>
    {brent_grid_html}
    <p class="text-gray-400 text-xs mt-4">Brent Crude is the global benchmark used for most international oil contracts. Suriname&#8217;s offshore production (Block 58) is priced against this index. SRD equivalent uses today&#8217;s CME USD buy rate ({usd_buy_srd:.2f}). Fetched fresh on each site rebuild.</p>
  </div>


</main>
<script>{js}
/* ── Gold price (gold-api.com, free, no key) ── */
(function(){{
  var USD_SRD = {usd_buy_srd};
  fetch('https://api.gold-api.com/price/XAU')
    .then(function(r){{return r.json();}})
    .then(function(d){{
      var price = d.price;
      document.getElementById('gold-usd').textContent  = '$' + price.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
      document.getElementById('gold-srd').textContent  = (price * USD_SRD).toLocaleString('en-US',{{minimumFractionDigits:0,maximumFractionDigits:0}}) + ' SRD';
      document.getElementById('gold-usdg').textContent = '$' + (price / 31.1035).toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
      var badge = document.getElementById('gold-badge');
      badge.textContent = '● Live';
      badge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800 shrink-0';
    }})
    .catch(function(){{
      var badge = document.getElementById('gold-badge');
      badge.textContent = 'Unavailable';
      badge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-500 shrink-0';
    }});
}})();


</script>
{footer_html()}
</body>
</html>"""

def build_news(articles, oil_articles, finance_articles):
    updated   = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")

    # ── Local news section ──────────────────────────────────────────────────
    local_cards_html = "\n".join(news_card_html(a, eager=(idx==0)) for idx, a in enumerate(articles[:30]))
    local_filter_html = (
        '<button onclick="filterSection(\'local\',\'all\')" id="lf-all" '
        'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
        'style="background:var(--forest);border-color:var(--forest);color:#fff">All</button>\n'
    )
    for _feed in FEEDS:
        _fn  = _feed["name"]
        _fid = _fn.replace(" ", "_")
        local_filter_html += (
            f'<button onclick="filterSection(\'local\',\'{html_lib.escape(_fn)}\')" id="lf-{_fid}" '
            f'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
            f'style="border-color:#e5e7eb;color:#374151;background:#fff">'
            f'{html_lib.escape(_fn)}</button>\n'
        )

    # ── Oil & Gas section ───────────────────────────────────────────────────
    oil_cards_html = "\n".join(news_card_html(a, eager=False) for a in oil_articles[:30]) if oil_articles else (
        '<div class="col-span-full text-center py-16 text-gray-400">'
        '<p class="text-4xl mb-3">⛽</p>'
        '<p class="text-sm">No Oil &amp; Gas articles available right now. Check back soon.</p>'
        '</div>'
    )
    oil_filter_html = (
        '<button onclick="filterSection(\'oil\',\'all\')" id="of-all" '
        'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
        'style="background:#92400e;border-color:#92400e;color:#fff">All</button>\n'
    )
    for _feed in OIL_FEEDS:
        _fn  = _feed["name"]
        _fid = _fn.replace(" ", "_")
        oil_filter_html += (
            f'<button onclick="filterSection(\'oil\',\'{html_lib.escape(_fn)}\')" id="of-{_fid}" '
            f'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
            f'style="border-color:#e5e7eb;color:#374151;background:#fff">'
            f'{html_lib.escape(_fn)}</button>\n'
        )

    local_count   = len(articles)
    oil_count     = len(oil_articles)

    # ── Finance section ────────────────────────────────────────────────────
    finance_cards_html = "\n".join(news_card_html(a, eager=False) for a in finance_articles[:30]) if finance_articles else (
        '<div class="col-span-full text-center py-16 text-gray-400">'
        '<p class="text-4xl mb-3">&#x1F4CA;</p>'
        '<p class="text-sm">No finance articles available right now. Check back soon.</p>'
        '</div>'
    )
    finance_filter_html = (
        '<button onclick="filterSection(\'finance\',\'all\')" id="ff-all" '
        'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
        'style="background:#0f766e;border-color:#0f766e;color:#fff">All</button>\n'
    )
    for _feed in FINANCE_FEEDS:
        _fn  = _feed["name"]
        _fid = _fn.replace(" ", "_")
        finance_filter_html += (
            f'<button onclick="filterSection(\'finance\',\'{html_lib.escape(_fn)}\')" id="ff-{_fid}" '
            f'class="sec-filt text-xs font-semibold px-3 py-1.5 rounded-full border transition" '
            f'style="border-color:#e5e7eb;color:#374151;background:#fff">'
            f'{html_lib.escape(_fn)}</button>\n'
        )
    finance_count = len(finance_articles)

    return f"""{PAGE_HEAD}
  <title>Suriname News | Local, Oil &amp; Gas and Finance | Explore Suriname</title>
  <meta name="description" content="Suriname local news, oil &amp; gas updates and finance in one place: De Ware Tijd, Starnieuws, Waterkant, Staatsolie, Block 58, IMF and more.">
  <link rel="canonical" href="{SITE_URL}/news.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/news.html">
  <meta property="og:title" content="Suriname News | Local, Oil &amp; Gas and Finance | Explore Suriname">
  <meta property="og:description" content="Suriname local news, oil &amp; gas and finance updates from De Ware Tijd, Starnieuws, Waterkant, OilNow, IMF and more.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname News | Local, Oil &amp; Gas and Finance | Explore Suriname">
  <meta name="twitter:description" content="Suriname local news, oil &amp; gas and finance updates in one place.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"CollectionPage","name":"Suriname News | Local, Oil & Gas and Finance","url":"{SITE_URL}/news.html","description":"Suriname local news, oil & gas and finance updates from De Ware Tijd, Starnieuws, Waterkant, OilNow, IMF and more.","isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}},"dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}"}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"News","item":"{SITE_URL}/news.html"}}]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("news")}
<div class="pt-16"></div>

<!-- ── Hero ─────────────────────────────────────────────────────────────── -->
<div class="text-white text-center py-14" style="background:var(--forest)">
  <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Suriname News</p>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-2">Stay Informed</h1>
</div>

<!-- ── Tab switcher ──────────────────────────────────────────────────────── -->
<div class="sticky top-16 z-40 bg-white border-b border-gray-100 shadow-sm">
  <div class="max-w-5xl mx-auto px-5">
    <div class="flex gap-1 py-2" role="tablist">
      <button id="tab-local" role="tab" aria-selected="true" aria-controls="section-local"
        onclick="switchTab('local')"
        class="tab-btn flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
        style="background:var(--forest);color:#fff">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 12h6m-6-4h2"/></svg>
        <span>Local News</span>
        <span class="hidden sm:inline text-xs font-normal opacity-70">({local_count} stories)</span>
      </button>
      <button id="tab-oil" role="tab" aria-selected="false" aria-controls="section-oil"
        onclick="switchTab('oil')"
        class="tab-btn flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
        style="background:#f3f4f6;color:#374151">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
        <span>Oil &amp; Gas</span>
        <span class="hidden sm:inline text-xs font-normal opacity-70">({oil_count} stories)</span>
      </button>
      <button id="tab-finance" role="tab" aria-selected="false" aria-controls="section-finance"
        onclick="switchTab('finance')"
        class="tab-btn flex-1 sm:flex-none flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold transition-all"
        style="background:#f3f4f6;color:#374151">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
        <span>Finance</span>
        <span class="hidden sm:inline text-xs font-normal opacity-70">({finance_count} stories)</span>
      </button>
    </div>
  </div>
</div>

<main class="max-w-5xl mx-auto px-5 py-8 pb-20">
  {ad_slot("Top Banner Ad — Replace with Google AdSense code")}

  <!-- ── Local News ─────────────────────────────────────────────────────── -->
  <div id="section-local" role="tabpanel" aria-labelledby="tab-local">
    <div class="rounded-2xl border border-amber-100 px-5 py-3 mb-5" style="background:#fffbeb">
      <p class="text-amber-800 text-sm leading-relaxed">
        <strong>Note:</strong> Articles are published in Dutch, the national language of Suriname. Readers outside Suriname may wish to use browser translation.
      </p>
    </div>
    <div class="flex gap-2 flex-wrap mb-6" id="local-filters">
      {local_filter_html}
    </div>
    <div id="local-feed" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{local_cards_html}</div>
  </div>

  <!-- ── Oil & Gas ──────────────────────────────────────────────────────── -->
  <div id="section-oil" role="tabpanel" aria-labelledby="tab-oil" style="display:none">
    <div class="rounded-2xl border border-blue-100 px-5 py-3 mb-5" style="background:#eff6ff">
      <p class="text-blue-800 text-sm leading-relaxed">
        <strong>Suriname Oil &amp; Gas:</strong> Covering Staatsolie, Block 58 (TotalEnergies), Block 52 (APA / PETRONAS), GranMorgu, Sapakara and Krabdagu developments.
      </p>
    </div>
    <div class="flex gap-2 flex-wrap mb-6" id="oil-filters">
      {oil_filter_html}
    </div>
    <div id="oil-feed" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{oil_cards_html}</div>
  </div>

  <!-- ── Finance ────────────────────────────────────────────────────────── -->
  <div id="section-finance" role="tabpanel" aria-labelledby="tab-finance" style="display:none">
    <div class="rounded-2xl border px-5 py-3 mb-5" style="background:#f0fdfa;border-color:#99f6e4">
      <p class="text-sm leading-relaxed" style="color:#134e4a">
        <strong>Suriname Finance &amp; Economy:</strong> Investment, banking, IMF programmes, fiscal policy, GDP and economic developments.
      </p>
    </div>
    <div class="flex gap-2 flex-wrap mb-6" id="finance-filters">
      {finance_filter_html}
    </div>
    <div id="finance-feed" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{finance_cards_html}</div>
  </div>
</main>

<script>
/* ── Tab switching ──────────────────────────────────────────────────────── */
function switchTab(tab) {{
  var tabs     = ['local','oil','finance'];
  var colors   = {{'local':'var(--forest)','oil':'#92400e','finance':'#0f766e'}};
  tabs.forEach(function(t) {{
    var btn = document.getElementById('tab-' + t);
    var sec = document.getElementById('section-' + t);
    var active = (t === tab);
    btn.style.background = active ? colors[t] : '#f3f4f6';
    btn.style.color      = active ? '#fff' : '#374151';
    btn.setAttribute('aria-selected', active ? 'true' : 'false');
    sec.style.display    = active ? '' : 'none';
  }});
}}

/* ── Source filter ──────────────────────────────────────────────────────── */
function filterSection(section, source) {{
  var feedMap   = {{'local':'local-feed','oil':'oil-feed','finance':'finance-feed'}};
  var filterMap = {{'local':'local-filters','oil':'oil-filters','finance':'finance-filters'}};
  var colorMap  = {{'local':'var(--forest)','oil':'#92400e','finance':'#0f766e'}};
  var prefMap   = {{'local':'lf-','oil':'of-','finance':'ff-'}};
  var feedId    = feedMap[section]   || 'local-feed';
  var filterId  = filterMap[section] || 'local-filters';
  var activeColor = colorMap[section] || 'var(--forest)';
  var allBtnId  = prefMap[section] + 'all';

  document.querySelectorAll('#' + filterId + ' .sec-filt').forEach(function(b) {{
    b.style.background   = '#fff';
    b.style.borderColor  = '#e5e7eb';
    b.style.color        = '#374151';
  }});

  var activeId  = source === 'all'
    ? allBtnId
    : prefMap[section] + source.replace(/ /g, '_');
  var activeBtn = document.getElementById(activeId);
  if (activeBtn) {{
    activeBtn.style.background  = activeColor;
    activeBtn.style.borderColor = activeColor;
    activeBtn.style.color       = '#fff';
  }}

  document.querySelectorAll('#' + feedId + ' > a').forEach(function(card) {{
    card.style.display = (source === 'all' || card.dataset.source === source) ? '' : 'none';
  }});
}}

/* ── Hash routing (optional deep-link) ─────────────────────────────────── */
(function() {{
  var h = window.location.hash;
  if (h === '#oil') switchTab('oil');
  else if (h === '#finance') switchTab('finance');
}})();
</script>
{footer_html()}
</body>
</html>"""


# -- Listing detail pages -----------------------------------------------------

_CAT_MAP = [
    (["food","restaurant","dining","bar","cafe","coffee","snack","grill","pizza",
      "sushi","noodle","pannekoek","ijsje"],
     "restaurants.html", "Restaurants &amp; Dining"),
    (["hotel","lodge","resort","accommodation","villa","suite","apartment",
      "tiny house","waterland"],
     "hotels.html", "Hotels &amp; Lodges"),
    (["shopping","souvenir","retail","store","mall","boutique","craft","candle",
      "jewelry","jewellery","print","skin","beauty","hair","wax","nail","tattoo",
      "barber","spa","wellness","massage","yoga","fitness"],
     "shopping.html", "Shopping"),
    (["tour","adventure","nature","park","travel","airline","airways","klm","fly"],
     "activities.html", "Activities"),
]

def _act_slug(name):
    """Convert an activity name to a URL-safe slug, prefixed with 'activity-'."""
    return "activity-" + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _nature_slug(name):
    """Convert a nature spot name to a URL-safe slug, prefixed with 'nature-'."""
    return "nature-" + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


def _cat_back(category):
    cat = category.lower()
    for keywords, page, label in _CAT_MAP:
        if any(k in cat for k in keywords):
            return page, label
    return "services.html", "Services"



# Slug → (schema_type, back_page, back_label) for JSON-LD & breadcrumbs
def _slug_schema_info(slug):
    """Return (ld_type, category_page, category_label) for a business slug."""
    rest_slugs  = {b["slug"] for b in RESTAURANTS}
    hotel_slugs = {b["slug"] for b in HOTELS}
    shop_slugs  = {b["slug"] for b in SHOPPING}
    sight_slugs = {b["slug"] for b in SIGHTSEEING}
    adv_slugs   = {b["slug"] for b in ADVENTURES_BIZ}
    svc_slugs   = {b["slug"] for b in SERVICES}
    if slug in rest_slugs:
        return "FoodEstablishment",  "restaurants.html", "Eat &amp; Drink"
    if slug in hotel_slugs:
        return "LodgingBusiness",    "hotels.html",      "Hotels &amp; Lodges"
    if slug in shop_slugs:
        return "Store",              "shopping.html",    "Shopping"
    if slug in sight_slugs or slug in adv_slugs:
        return "TouristAttraction",  "activities.html",  "Adventures &amp; Sightseeing"
    if slug in svc_slugs:
        return "LocalBusiness",      "services.html",    "Services"
    return "LocalBusiness", "index.html", "Home"


# Subcategory → (refined schema.org @type, servesCuisine or None)
# More specific types unlock Google rich result eligibility
_SUBCAT_SCHEMA = {
    "fast-food":            ("FastFoodRestaurant",        "Fast Food"),
    "cafes-coffee":         ("CafeOrCoffeeShop",          None),
    "bars-lounges":         ("BarOrPub",                  None),
    "asian-fusion":         ("Restaurant",                "Asian, International"),
    "local-caribbean":      ("Restaurant",                "Surinamese, Caribbean"),
    "bakeries-sweets":      ("Bakery",                    None),
    "pizza-italian":        ("Restaurant",                "Italian, Pizza"),
    "eco-lodges":           ("LodgingBusiness",           None),
    "casino-hotels":        ("Hotel",                     None),
    "guesthouses":          ("BedAndBreakfast",           None),
    "tours-expeditions":    ("TravelAgency",              None),
    "museums-heritage":     ("Museum",                    None),
    "entertainment":        ("EntertainmentBusiness",     None),
    "nature-parks":         ("Park",                      None),
    "supermarkets":         ("GroceryStore",              None),
    "malls-markets":        ("ShoppingCenter",            None),
    "fashion-clothing":     ("ClothingStore",             None),
    "electronics":          ("ElectronicsStore",          None),
    "home-furniture":       ("FurnitureStore",            None),
    "optical-jewelry":      ("JewelryStore",              None),
    "food-specialty":       ("Store",                     None),
    "banking":              ("BankOrCreditUnion",         None),
    "insurance":            ("InsuranceAgency",           None),
    "health-pharmacy":      ("Pharmacy",                  None),
    "telecom-utilities":    ("LocalBusiness",             None),
    "education":            ("EducationalOrganization",   None),
    "fitness-wellness":     ("SportsActivityLocation",    None),
    "beauty-wellness":      ("BeautySalon",               None),
    "real-estate":          ("RealEstateAgent",           None),
    "cleaning-maintenance": ("LocalBusiness",             None),
    "security":             ("LocalBusiness",             None),
    "travel-transport":     ("TravelAgency",              None),
    "tech-media":           ("LocalBusiness",             None),
    "legal-professional":   ("LegalService",              None),
    "automotive":           ("AutoRepair",                None),
    "events-party":         ("EventVenue",                None),
    "nursery-garden":       ("Store",                     None),
    "other":                ("LocalBusiness",             None),
}

def _related_listings_html(current_slug, sub, prefix="../../"):
    """Return an HTML strip of up to 4 related listings using the same
    pre-built category lists (and image paths) that poi_card uses."""
    import html as _hl

    # Source from the same lists poi_card uses — images already resolved by _make_biz
    # Reference globals at call-time so the lists are fully built
    _src = (
        list(globals().get("RESTAURANTS", []))
        + list(globals().get("HOTELS", []))
        + list(globals().get("SHOPPING", []))
        + list(globals().get("SERVICES", []))
        + list(globals().get("SIGHTSEEING", []))
        + list(globals().get("ADVENTURES_BIZ", []))
    )

    candidates = [
        item for item in _src
        if item.get("slug") != current_slug and item.get("subcat") == sub and item.get("image")
    ]
    candidates.sort(key=lambda x: x.get("name", "").lower())
    picks = candidates[:4]
    if not picks:
        return ""

    cards_html = ""
    for item in picks:
        bname = item.get("name", "")
        bloc  = item.get("area", "Paramaribo")
        bimg  = item.get("image", "")
        burl  = prefix + item.get("url", "listing/" + item.get("slug","") + "/")
        thumb = (
            f'<div class="w-full h-32 rounded-xl overflow-hidden mb-3 bg-gray-100">'
            f'<img src="{bimg}" alt="{_hl.escape(bname)}" loading="lazy" '
            f'class="w-full h-full object-cover">'
            f'</div>'
        )
        cards_html += (
            f'<a href="{burl}" class="block bg-white rounded-2xl border border-gray-100 '
            f'hover:border-gray-300 hover:shadow-sm transition p-4">'
            + thumb +
            f'<h3 class="text-sm font-semibold text-gray-900 leading-snug mb-1">{_hl.escape(bname)}</h3>'
            f'<p class="text-xs text-gray-400">{_hl.escape(bloc)}</p>'
            f'</a>'
        )

    return (
        '\n<section class="max-w-5xl mx-auto px-5 pb-16">'
        '\n  <h2 class="text-lg font-bold text-gray-900 mb-5">More like this</h2>'
        '\n  <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">'
        + cards_html +
        '\n  </div>'
        '\n</section>'
    )


def build_listing_page(slug, b):
    raw_name = b.get("name", slug)
    desc     = b.get("description", "")
    address  = b.get("address", "")
    phone    = b.get("phone", "")
    email    = b.get("email", "")
    category = b.get("category", "")
    location = b.get("area", b.get("location", "Paramaribo"))
    img      = _IMGS.get(slug, "")
    ext_url  = _biz_url(b)

    # Merge enrichment data — priority: Google Places (future slot) > OSM > Foursquare
    _osm  = _ENRICHMENTS.get(slug, {})
    _fdet = _FSQ_DETAILS.get(slug, {})
    # Phone / address / website: OSM fills gaps first, then Foursquare
    if not phone   and _osm.get("phone"):   phone   = _osm["phone"]
    if not phone   and _fdet.get("phone"):  phone   = _fdet["phone"]
    if not address and _osm.get("address"): address = _osm["address"]
    if not ext_url and _osm.get("website"): ext_url = _osm["website"]
    if not ext_url and _fdet.get("website") and "google.com" not in _fdet.get("website", ""):
        ext_url = _fdet["website"]
    # Hours: OSM > Foursquare (both use human-readable strings)
    hours     = _osm.get("opening_hours") or _fdet.get("hours_display") or ""
    osm_price = _osm.get("price_range", "")
    # Photo: FSQ fills missing thumbnails (already in img via _make_biz, but img is re-fetched
    # from _IMGS here for the detail page hero — apply the same fallback)
    if not img and _fdet.get("photo_url"):
        img = _fdet["photo_url"]

    name_e   = html_lib.escape(raw_name)
    # Description already in b via _make_biz; _JSON_DESCS as belt-and-braces fallback
    if not desc:
        desc = _JSON_DESCS.get(slug, "")
    # Build meta description: prefer structured data (address/hours/phone) over raw marketing copy.
    # Searchers looking up a specific business want to know WHERE it is and WHETHER it's open —
    # not a marketing blurb. Structured snippets also improve CTR from GSC position 8-12.
    _struct_parts = []
    if address:
        # Skip generic city-only addresses (e.g. "Paramaribo, Suriname") — not useful in a snippet
        _addr_clean = address.strip().lower().rstrip(", suriname").rstrip(",").strip()
        _loc_clean  = (location or "paramaribo").strip().lower()
        if _addr_clean and _addr_clean != _loc_clean:
            _struct_parts.append(address)
    if hours:
        _h = (hours.replace("Mo","Mon").replace("Tu","Tue").replace("We","Wed")
                   .replace("Th","Thu").replace("Fr","Fri").replace("Sa","Sat")
                   .replace("Su","Sun").replace(";", " ·"))
        _struct_parts.append(_h[:65])
    if phone:
        _struct_parts.append(phone)
    if _struct_parts:
        _loc_for_desc = location or "Paramaribo"
        desc_e = html_lib.escape(
            f"{raw_name} in {_loc_for_desc}, Suriname. " + " · ".join(_struct_parts)
        )[:160]
    elif desc:
        desc_e = html_lib.escape(desc[:155]) + ("…" if len(desc) > 155 else "")
    else:
        loc_part = location or "Paramaribo"
        sub = _subcat(slug)
        _SUBCAT_LABELS = {
            # Eat & Drink
            "fast-food":           "fast food restaurant",
            "cafes-coffee":        "café & coffee shop",
            "bars-lounges":        "bar & lounge",
            "asian-fusion":        "Asian restaurant",
            "local-caribbean":     "local Surinamese restaurant",
            "bakeries-sweets":     "bakery & pastry shop",
            "pizza-italian":       "pizza & Italian restaurant",
            # Hotels
            "eco-lodges":          "eco lodge & nature resort",
            "casino-hotels":       "casino hotel",
            "guesthouses":         "guesthouse & villa",
            # Activities
            "tours-expeditions":   "tour & expedition operator",
            "museums-heritage":    "museum & heritage site",
            "entertainment":       "entertainment venue",
            "nature-parks":        "nature park & wildlife reserve",
            # Shopping
            "supermarkets":        "supermarket",
            "malls-markets":       "shopping mall & market",
            "fashion-clothing":    "fashion & clothing store",
            "electronics":         "electronics & tech store",
            "home-furniture":      "home & furniture store",
            "optical-jewelry":     "optician & jewellery",
            "food-specialty":      "specialty food & pharmacy",
            # Services — must match _subcat() return values exactly
            "banking":             "bank & financial services",
            "insurance":           "insurance company",
            "fitness-wellness":    "fitness & wellness center",
            "beauty-wellness":     "beauty salon & wellness",
            "health-pharmacy":     "pharmacy & health services",
            "telecom-utilities":   "telecom & utility provider",
            "real-estate":         "real estate agency",
            "education":           "school & educational institution",
            "travel-transport":    "travel & transport services",
            "tech-media":          "tech & media company",
            "cleaning-maintenance":"cleaning & maintenance services",
            "automotive":          "automotive & car services",
            "legal-professional":  "legal & professional services",
            "events-party":        "events & party services",
            "nursery-garden":      "nursery & garden center",
            "security":            "security services",
        }
        biz_type = _SUBCAT_LABELS.get(sub, "business")
        desc_e = html_lib.escape(
            f"{raw_name} — {biz_type} in {loc_part}, Suriname. "
            f"View location, contact info & more on ExploreSuriname.com."
        )[:160]
    # Use slug-based lookup (reliable) instead of category-text matching (error-prone)
    _ld_type_tmp, back_file, back_label = _slug_schema_info(slug)

    page_url   = SITE_URL + "/listing/" + slug + "/"
    maps_q     = urllib.parse.quote(raw_name + ", " + (address or location + ", Suriname"))
    maps_embed = "https://maps.google.com/maps?q=" + maps_q + "&output=embed&hl=en"
    maps_link  = "https://www.google.com/maps/search/?api=1&query=" + maps_q
    og_img     = (SITE_URL + "/" + img) if img and not img.startswith("http") else (img or SITE_URL + "/og-image.jpg")

    hero_style = ("background:url(" + html_lib.escape(img) + ") center/cover no-repeat"
                  if img else "background:var(--forest)")
    overlay    = ('<div class="absolute inset-0" style="background:linear-gradient('
                  'to top,rgba(0,0,0,.75) 0%,rgba(0,0,0,.3) 60%,transparent 100%)"></div>'
                  if img else "")

    def row(icon, content):
        return (
            '<div class="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">'
            '<span class="text-xl shrink-0 mt-0.5">' + icon + '</span>'
            '<span class="text-gray-700 text-sm leading-relaxed">' + content + '</span>'
            '</div>'
        )

    rows = ""
    if address:
        rows += row("📍", html_lib.escape(address))
    if phone:
        rows += row("📞", '<a href="tel:' + html_lib.escape(phone) + '" class="hover:underline" '
                    'style="color:var(--forest2)">' + html_lib.escape(phone) + '</a>')
    if email:
        rows += row("✉️", '<a href="mailto:' + html_lib.escape(email) + '" class="hover:underline" '
                    'style="color:var(--forest2)">' + html_lib.escape(email) + '</a>')
    if category:
        rows += row("🏷️", html_lib.escape(category))
    if hours:
        # Format hours for display: "Mo-Fr 09:00-17:00; Sa 10:00-14:00" → lines
        hours_display = html_lib.escape(hours).replace("; ", "<br>")
        rows += row("🕐", hours_display)
    if osm_price:
        rows += row("💰", html_lib.escape(osm_price))

    if ext_url and "google.com/search" not in ext_url:
        website_btn = (
            '<a href="' + html_lib.escape(ext_url) + '" target="_blank" rel="noopener" '
            'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
            'text-sm font-semibold text-white hover:opacity-90 transition mb-3" '
            'style="background:var(--forest)">🌐 Visit Website</a>'
        )
    else:
        # No website — link to the Google Maps listing as a useful fallback
        website_btn = (
            '<a href="' + html_lib.escape(maps_link) + '" target="_blank" rel="noopener" '
            'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
            'text-sm font-semibold text-white hover:opacity-90 transition mb-3" '
            'style="background:var(--forest)">📍 View on Google Maps</a>'
        )

    directions_btn = (
        '<a href="' + html_lib.escape(maps_link) + '" target="_blank" rel="noopener" '
        'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
        'text-sm font-semibold border-2 hover:bg-gray-50 transition mb-3" '
        'style="border-color:var(--forest2);color:var(--forest2)">🗺️ Get Directions</a>'
    )

    desc_block = ('<p class="text-gray-700 leading-relaxed text-base mb-8">'
                  + html_lib.escape(desc) + '</p>') if desc else ""

    # JSON-LD LocalBusiness/subtype schema
    import json as _json
    ld_type, cat_page, cat_label = _slug_schema_info(slug)

    # Refine @type and cuisine using subcategory — unlocks more Google rich result types
    _sub = _subcat(slug)
    _sub_schema = _SUBCAT_SCHEMA.get(_sub)
    if _sub_schema:
        ld_type, _cuisine = _sub_schema
    else:
        _cuisine = None

    # Build PostalAddress — include addressLocality so Google can surface the business location
    _loc = location or "Paramaribo"
    if address:
        _postal = {
            "@type": "PostalAddress",
            "streetAddress": address,
            "addressLocality": _loc,
            "addressCountry": "SR",
        }
    else:
        _postal = {
            "@type": "PostalAddress",
            "addressLocality": _loc,
            "addressCountry": "SR",
        }

    ld_obj = {"@context": "https://schema.org", "@type": ld_type, "name": raw_name, "url": page_url}
    if desc:      ld_obj["description"] = desc[:300]
    ld_obj["address"] = _postal
    if phone:     ld_obj["telephone"] = phone
    if email:     ld_obj["email"] = email
    if og_img != SITE_URL + "/og-image.jpg": ld_obj["image"] = og_img
    if ext_url and "google.com/search" not in ext_url: ld_obj["sameAs"] = ext_url
    # OSM enrichment → structured data Google can parse for rich results
    if hours:
        # schema.org openingHours accepts OSM-style strings directly
        ld_obj["openingHours"] = [s.strip() for s in hours.split(";") if s.strip()]
    if osm_price:
        ld_obj["priceRange"] = osm_price
    if _cuisine:
        ld_obj["servesCuisine"] = _cuisine
    ld_obj["currenciesAccepted"] = "SRD"

    # JSON-LD names must be plain text — unescape HTML entities from category labels
    _cat_label_plain = cat_label.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
    breadcrumb_obj = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",             "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": _cat_label_plain,   "item": SITE_URL + "/" + cat_page},
            {"@type": "ListItem", "position": 3, "name": raw_name,           "item": page_url},
        ]
    }

    ld_script = (
        "\n  <script type=\"application/ld+json\">\n  " + _json.dumps(ld_obj, ensure_ascii=False) + "\n  </script>"
        + "\n  <script type=\"application/ld+json\">\n  " + _json.dumps(breadcrumb_obj, ensure_ascii=False) + "\n  </script>"
    )

    # SEO-optimised <title>: "Name — Type in Location, Suriname | ExploreSuriname"
    _SEO_TYPE_LABEL = {
        "fast-food": "Fast Food Restaurant", "cafes-coffee": "Café",
        "bars-lounges": "Bar & Lounge", "asian-fusion": "Asian Restaurant",
        "local-caribbean": "Surinamese Restaurant", "bakeries-sweets": "Bakery",
        "pizza-italian": "Italian Restaurant", "eco-lodges": "Eco Lodge",
        "casino-hotels": "Casino Hotel", "guesthouses": "Guesthouse",
        "city-hotels": "Hotel", "tours-expeditions": "Tour Operator",
        "museums-heritage": "Museum", "entertainment": "Entertainment Venue",
        "nature-parks": "Nature Park", "supermarkets": "Supermarket",
        "malls-markets": "Shopping Mall", "fashion-clothing": "Fashion Store",
        "electronics": "Electronics Store", "home-furniture": "Furniture Store",
        "optical-jewelry": "Jewellery & Optician", "food-specialty": "Specialty Store",
        "banking": "Bank", "insurance": "Insurance", "fitness-wellness": "Gym & Wellness",
        "beauty-wellness": "Beauty Salon", "health-pharmacy": "Pharmacy",
        "telecom-utilities": "Telecom Provider", "real-estate": "Real Estate",
        "education": "School", "travel-transport": "Travel Agency",
        "tech-media": "Tech & Media", "cleaning-maintenance": "Cleaning Services",
        "automotive": "Auto Services", "legal-professional": "Professional Services",
        "events-party": "Events & Party", "nursery-garden": "Garden Centre",
        "security": "Security Services",
    }
    _seo_biz_type = _SEO_TYPE_LABEL.get(_sub, "")
    if _seo_biz_type:
        _seo_loc = (_loc + ", Suriname") if _loc.lower() not in ("suriname", "") else "Suriname"
        seo_page_title = name_e + html_lib.escape(", " + _seo_biz_type + " in " + _seo_loc)
    else:
        _seo_loc = (_loc + ", Suriname") if _loc.lower() not in ("suriname", "") else "Suriname"
        seo_page_title = name_e + html_lib.escape(" in " + _seo_loc)

    head = (
        PAGE_HEAD +
        "\n  <title>" + seo_page_title + " | ExploreSuriname</title>"
        "\n  <meta name=\"description\" content=\"" + desc_e + "\">"
        "\n  <link rel=\"canonical\" href=\"" + page_url + "\">"
        "\n  <meta property=\"og:type\" content=\"website\">"
        "\n  <meta property=\"og:site_name\" content=\"Explore Suriname\">"
        "\n  <meta property=\"og:url\" content=\"" + page_url + "\">"
        "\n  <meta property=\"og:title\" content=\"" + seo_page_title + " | ExploreSuriname\">"
        "\n  <meta property=\"og:description\" content=\"" + desc_e + "\">"
        "\n  <meta property=\"og:image\" content=\"" + og_img + "\">"
        "\n  <meta name=\"twitter:card\" content=\"summary_large_image\">"
        "\n  <meta name=\"twitter:title\" content=\"" + seo_page_title + " | ExploreSuriname\">"
        "\n  <meta name=\"twitter:description\" content=\"" + desc_e + "\">"
        "\n  <meta name=\"twitter:image\" content=\"" + og_img + "\">"
        + ld_script +
        "\n</head>"
    )

    hero = (
        '\n<body class="bg-gray-50 overflow-x-hidden">\n' +
        nav_html(prefix="../../") +
        '\n<div class="relative w-full pt-16" style="min-height:320px">'
        '\n  <div class="absolute inset-0" style="' + hero_style + '"></div>'
        '\n  ' + overlay +
        '\n  <div class="relative max-w-5xl mx-auto px-5 flex flex-col justify-end"'
        '\n       style="min-height:320px;padding-top:5rem;padding-bottom:3rem">'
        '\n    <a href="../../' + back_file + '"'
        '\n       class="inline-flex items-center gap-1 text-white/70 text-sm hover:text-white mb-5 transition w-fit">'
        '\n      &#8592; ' + back_label +
        '\n    </a>'
        '\n    <span class="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-3 w-fit"'
        '\n          style="background:var(--coral);color:#fff">' + html_lib.escape(category) + '</span>'
        '\n    <h1 class="serif text-4xl sm:text-5xl font-bold text-white mb-2">' + name_e + '</h1>'
        '\n    <p class="text-white/70 text-sm">&#128205; ' + html_lib.escape(location) + ', Suriname</p>'
        '\n  </div>'
        '\n</div>'
    )

    main = (
        '\n<main class="max-w-5xl mx-auto px-5 py-12 pb-24">'
        '\n  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">'

        '\n    <div class="lg:col-span-2">'
        '\n      ' + desc_block +
        '\n      <h2 class="text-lg font-bold text-gray-900 mb-4">Location</h2>'
        '\n      <div class="rounded-2xl overflow-hidden border border-gray-200 shadow-sm mb-3" style="height:380px">'
        '\n        <iframe src="' + maps_embed + '" width="100%" height="100%"'
        '\n          style="border:0" allowfullscreen="" loading="lazy"'
        '\n          referrerpolicy="no-referrer-when-downgrade"></iframe>'
        '\n      </div>'
        '\n      <p class="text-gray-400 text-xs text-center mb-8">'
        '\n        Map data &copy; Google &mdash; click the map to see hours, reviews &amp; street view.'
        '\n      </p>'
        '\n    </div>'

        '\n    <div class="lg:col-span-1">'
        '\n      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sticky top-24">'
        '\n        <h2 class="text-base font-bold text-gray-900 mb-4">Contact &amp; Info</h2>'
        '\n        ' + rows +
        '\n        <div class="mt-6">'
        '\n          ' + website_btn +
        '\n          ' + directions_btn +
        '\n        </div>'
        '\n      </div>'
        '\n    </div>'

        '\n  </div>'
        '\n</main>'
    )

    related_html = _related_listings_html(slug, _sub, prefix="../../")
    return head + hero + main + related_html + "\n" + footer_html(prefix="../../") + "\n</body>\n</html>"


def build_activity_listing_page(act, slug):
    """Generate an individual detail page for an ACTIVITIES entry."""
    name    = act.get("name", slug)
    desc    = act.get("desc", "")
    img     = act.get("image", "")
    ext_url = act.get("url", "")
    icon    = act.get("icon", "\U0001f33f")

    name_e     = html_lib.escape(name)
    desc_e     = html_lib.escape(desc[:160]) if desc else html_lib.escape(name + " on ExploreSuriname.com")
    page_url   = SITE_URL + "/listing/" + slug + "/"
    maps_q     = urllib.parse.quote(name + ", Suriname")
    maps_embed = "https://maps.google.com/maps?q=" + maps_q + "&output=embed&hl=en"
    maps_link  = "https://www.google.com/maps/search/?api=1&query=" + maps_q
    og_img     = (SITE_URL + "/" + img) if img and not img.startswith("http") else (img or SITE_URL + "/og-image.jpg")

    hero_style = ("background:url(" + html_lib.escape(img) + ") center/cover no-repeat"
                  if img else "background:var(--forest)")
    overlay    = ('<div class="absolute inset-0" style="background:linear-gradient('
                  'to top,rgba(0,0,0,.75) 0%,rgba(0,0,0,.3) 60%,transparent 100%)"></div>'
                  if img else "")

    website_btn = ""
    if ext_url:
        website_btn = (
            '<a href="' + html_lib.escape(ext_url) + '" target="_blank" rel="noopener" '
            'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
            'text-sm font-semibold text-white hover:opacity-90 transition mb-3" '
            'style="background:var(--forest)">\U0001f310 Find Operators &amp; Tours</a>'
        )

    directions_btn = (
        '<a href="' + html_lib.escape(maps_link) + '" target="_blank" rel="noopener" '
        'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
        'text-sm font-semibold border-2 hover:bg-gray-50 transition" '
        'style="border-color:var(--forest2);color:var(--forest2)">\U0001f5fa️ View on Map</a>'
    )

    desc_block = ('<p class="text-gray-700 leading-relaxed text-base mb-8">'
                  + html_lib.escape(desc) + '</p>') if desc else ""

    import json as _json
    act_ld = {
        "@context": "https://schema.org", "@type": "TouristAttraction",
        "name": name, "url": page_url,
        "description": desc[:300] if desc else name + ". Activity in Suriname.",
        "touristType": "Adventure travellers",
        "geo": {"@type": "GeoCoordinates", "addressCountry": "SR"},
    }
    if og_img != SITE_URL + "/og-image.jpg": act_ld["image"] = og_img
    if ext_url: act_ld["sameAs"] = ext_url

    act_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",       "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Activities", "item": SITE_URL + "/activities.html"},
            {"@type": "ListItem", "position": 3, "name": name,         "item": page_url},
        ]
    }
    act_ld_scripts = (
        "\n  <script type=\"application/ld+json\">\n  " + _json.dumps(act_ld, ensure_ascii=False) + "\n  </script>"
        + "\n  <script type=\"application/ld+json\">\n  " + _json.dumps(act_breadcrumb, ensure_ascii=False) + "\n  </script>"
    )

    head = (
        PAGE_HEAD +
        "\n  <title>" + name_e + " in Suriname | ExploreSuriname.com</title>"
        "\n  <meta name=\"description\" content=\"" + desc_e + "\">"
        "\n  <link rel=\"canonical\" href=\"" + page_url + "\">"
        "\n  <meta property=\"og:type\" content=\"website\">"
        "\n  <meta property=\"og:site_name\" content=\"Explore Suriname\">"
        "\n  <meta property=\"og:url\" content=\"" + page_url + "\">"
        "\n  <meta property=\"og:title\" content=\"" + name_e + " in Suriname | ExploreSuriname.com\">"
        "\n  <meta property=\"og:description\" content=\"" + desc_e + "\">"
        "\n  <meta property=\"og:image\" content=\"" + og_img + "\">"
        "\n  <meta name=\"twitter:card\" content=\"summary_large_image\">"
        "\n  <meta name=\"twitter:title\" content=\"" + name_e + " | ExploreSuriname.com\">"
        "\n  <meta name=\"twitter:description\" content=\"" + desc_e + "\">"
        "\n  <meta name=\"twitter:image\" content=\"" + og_img + "\">"
        + act_ld_scripts +
        "\n</head>"
    )

    hero = (
        '\n<body class="bg-gray-50 overflow-x-hidden">\n' +
        nav_html(prefix="../../") +
        '\n<div class="relative w-full pt-16" style="min-height:320px">'
        '\n  <div class="absolute inset-0" style="' + hero_style + '"></div>'
        '\n  ' + overlay +
        '\n  <div class="relative max-w-5xl mx-auto px-5 flex flex-col justify-end"'
        '\n       style="min-height:320px;padding-top:5rem;padding-bottom:3rem">'
        '\n    <a href="../../activities.html"'
        '\n       class="inline-flex items-center gap-1 text-white/70 text-sm hover:text-white mb-5 transition w-fit">'
        '\n      &#8592; Activities'
        '\n    </a>'
        '\n    <span class="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-3 w-fit"'
        '\n          style="background:var(--coral);color:#fff">' + icon + ' Activity</span>'
        '\n    <h1 class="serif text-4xl sm:text-5xl font-bold text-white mb-2">' + name_e + '</h1>'
        '\n    <p class="text-white/70 text-sm">&#127757; Suriname</p>'
        '\n  </div>'
        '\n</div>'
    )

    main = (
        '\n<main class="max-w-5xl mx-auto px-5 py-12 pb-24">'
        '\n  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">'
        '\n    <div class="lg:col-span-2">'
        '\n      ' + desc_block +
        '\n      <h2 class="text-lg font-bold text-gray-900 mb-4">Location</h2>'
        '\n      <div class="rounded-2xl overflow-hidden border border-gray-200 shadow-sm mb-3" style="height:380px">'
        '\n        <iframe src="' + maps_embed + '" width="100%" height="100%"'
        '\n          style="border:0" allowfullscreen="" loading="lazy"'
        '\n          referrerpolicy="no-referrer-when-downgrade"></iframe>'
        '\n      </div>'
        '\n      <p class="text-gray-400 text-xs text-center mb-8">'
        '\n        Map data &copy; Google &mdash; click the map to see locations, reviews &amp; directions.'
        '\n      </p>'
        '\n    </div>'
        '\n    <div class="lg:col-span-1">'
        '\n      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sticky top-24">'
        '\n        <h2 class="text-base font-bold text-gray-900 mb-4">Plan Your Trip</h2>'
        '\n        <div class="mt-2">'
        '\n          ' + website_btn +
        '\n          ' + directions_btn +
        '\n        </div>'
        '\n      </div>'
        '\n    </div>'
        '\n  </div>'
        '\n</main>'
    )

    return head + hero + main + "\n" + footer_html(prefix="../../") + "\n</body>\n</html>"


def build_nature_listing_page(spot, slug):
    """Generate an individual detail page for a NATURE_SPOTS entry."""
    name    = spot.get("name", slug)
    desc    = spot.get("desc", "")
    img     = spot.get("image", "")
    ext_url = spot.get("url", "")
    badge   = spot.get("badge", "Nature")
    fact    = spot.get("fact", "")
    tags    = spot.get("tags", [])

    name_e     = html_lib.escape(name)
    desc_e     = html_lib.escape(desc[:160]) if desc else html_lib.escape(name + " on ExploreSuriname.com")
    page_url   = SITE_URL + "/listing/" + slug + "/"
    maps_q     = urllib.parse.quote(name + ", Suriname")
    maps_embed = "https://maps.google.com/maps?q=" + maps_q + "&output=embed&hl=en"
    maps_link  = "https://www.google.com/maps/search/?api=1&query=" + maps_q
    og_img     = (SITE_URL + "/" + img) if img and not img.startswith("http") else (img or SITE_URL + "/og-image.jpg")


    hero_style = ("background:url(" + html_lib.escape(img) + ") center/cover no-repeat"
                  if img else "background:var(--forest)")
    overlay    = ('<div class="absolute inset-0" style="background:linear-gradient('
                  'to top,rgba(0,0,0,.75) 0%,rgba(0,0,0,.3) 60%,transparent 100%)"></div>'
                  if img else "")

    tags_html  = "".join(
        '<span class="inline-block text-xs px-3 py-1 rounded-full font-medium mr-1 mb-1"'
        ' style="background:var(--mint);color:var(--forest)">' + html_lib.escape(t) + '</span>'
        for t in tags
    )
    fact_block = (
        '<div class="flex items-start gap-3 p-4 rounded-xl mb-6"'
        ' style="background:var(--mint)"><span class="text-2xl shrink-0">✨</span>'
        '<p class="text-sm font-medium" style="color:var(--forest)">'
        + html_lib.escape(fact) + '</p></div>'
    ) if fact else ""

    website_btn = (
        '<a href="' + html_lib.escape(ext_url) + '"'
        ' target="_blank" rel="noopener"'
        ' class="flex items-center justify-center gap-2 w-full py-3 rounded-xl'
        ' text-sm font-semibold text-white hover:opacity-90 transition mb-3"'
        ' style="background:var(--forest)">\U0001f310 Learn More</a>'
    ) if ext_url else ""

    directions_btn = (
        '<a href="' + maps_link + '"'
        ' target="_blank" rel="noopener"'
        ' class="flex items-center justify-center gap-2 w-full py-3 rounded-xl'
        ' text-sm font-semibold border-2 hover:bg-gray-50 transition"'
        ' style="border-color:var(--forest2);color:var(--forest2)">\U0001f5fa️ Get Directions</a>'
    )

    desc_block   = ('<p class="text-gray-700 leading-relaxed text-base mb-8">'
                    + html_lib.escape(desc) + '</p>') if desc else ""
    tags_section = ('<div class="flex flex-wrap gap-1 mb-8">' + tags_html + '</div>') if tags_html else ""

    import json as _json
    nat_ld = {
        "@context":    "https://schema.org",
        "@type":       "TouristAttraction",
        "name":        name,
        "url":         page_url,
        "description": desc if desc else name + ". Nature attraction in Suriname.",
        "geo":         {"@type": "GeoCoordinates", "addressCountry": "SR"},
    }
    if tags:
        nat_ld["keywords"] = ", ".join(tags)
    if fact:
        nat_ld["additionalProperty"] = {"@type": "PropertyValue", "name": "Fact", "value": fact}
    if og_img != SITE_URL + "/og-image.jpg":
        nat_ld["image"] = og_img
    if ext_url:
        nat_ld["sameAs"] = ext_url

    nat_breadcrumb = {
        "@context": "https://schema.org",
        "@type":    "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home",           "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "Nature & Parks", "item": SITE_URL + "/nature.html"},
            {"@type": "ListItem", "position": 3, "name": name,             "item": page_url},
        ]
    }

    nat_ld_scripts = (
        '\n  <script type="application/ld+json">\n  '
        + _json.dumps(nat_ld, ensure_ascii=False)
        + '\n  </script>'
        + '\n  <script type="application/ld+json">\n  '
        + _json.dumps(nat_breadcrumb, ensure_ascii=False)
        + '\n  </script>'
    )

    head = (
        PAGE_HEAD
        + '\n  <title>' + name_e + ', Nature Park in Suriname | ExploreSuriname</title>\n  <meta name="description" content="'
        + desc_e
        + '">\n  <link rel="canonical" href="' + page_url
        + '">\n  <meta property="og:type" content="website">\n  <meta property="og:site_name" content="Explore Suriname">\n  <meta property="og:url" content="'
        + page_url
        + '">\n  <meta property="og:title" content="' + name_e + ' â Nature Park in Suriname | ExploreSuriname">\n  <meta property="og:description" content="'
        + desc_e
        + '">\n  <meta property="og:image" content="' + og_img
        + '">\n  <meta name="twitter:card" content="summary_large_image">\n  <meta name="twitter:title" content="'
        + name_e + ' â Nature Park in Suriname | ExploreSuriname">\n  <meta name="twitter:description" content="'
        + desc_e + '">\n  <meta name="twitter:image" content="'
        + og_img + '">'
        + nat_ld_scripts
        + '\n</head>'
    )

    hero = (
        '\n<body class="bg-gray-50 overflow-x-hidden">\n'
        + nav_html(prefix="../../")
        + '\n<div class="relative w-full pt-16" style="min-height:320px">\n  <div class="absolute inset-0" style="'
        + hero_style + '"></div>\n  '
        + overlay
        + '\n  <div class="relative max-w-5xl mx-auto px-5 flex flex-col justify-end"\n       style="min-height:320px;padding-top:5rem;padding-bottom:3rem">\n    <a href="../../nature.html"\n       class="inline-flex items-center gap-1 text-white/70 text-sm hover:text-white mb-5 transition w-fit">\n      &#8592; Nature &amp; Parks\n    </a>\n    <span class="inline-block text-xs font-semibold px-3 py-1 rounded-full mb-3 w-fit"\n          style="background:var(--coral);color:#fff">'
        + html_lib.escape(badge)
        + '</span>\n    <h1 class="serif text-4xl sm:text-5xl font-bold text-white mb-2">'
        + name_e
        + '</h1>\n    <p class="text-white/70 text-sm">&#127757; Suriname</p>\n  </div>\n</div>'
    )

    main = (
        '\n<main class="max-w-5xl mx-auto px-5 py-12 pb-24">\n  <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">\n    <div class="lg:col-span-2">\n      '
        + desc_block
        + '\n      ' + fact_block
        + '\n      ' + tags_section
        + '\n      <h2 class="text-lg font-bold text-gray-900 mb-4">Location</h2>\n      <div class="rounded-2xl overflow-hidden border border-gray-200 shadow-sm mb-3" style="height:380px">\n        <iframe src="'
        + maps_embed
        + '" width="100%" height="100%"\n          style="border:0" allowfullscreen="" loading="lazy"\n          referrerpolicy="no-referrer-when-downgrade"></iframe>\n      </div>\n      <p class="text-gray-400 text-xs text-center mb-8">\n        Map data &copy; Google &mdash; click the map to see locations, reviews &amp; directions.\n      </p>\n    </div>\n    <div class="lg:col-span-1">\n      <div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 sticky top-24">\n        <h2 class="text-base font-bold text-gray-900 mb-4">Plan Your Visit</h2>\n        <div class="mt-2">\n          '
        + website_btn
        + '\n          ' + directions_btn
        + '\n        </div>\n      </div>\n    </div>\n  </div>\n</main>'
    )

    return head + hero + main + "\n" + footer_html(prefix="../../") + "\n</body>\n</html>"


# ── Sitemap ──────────────────────────────────────────────────────────────────


def build_visitor_guide_page():
    """Suriname Visitor Guide — static page covering visas, customs, SIM cards, money, transport and apps."""
    return f"""{PAGE_HEAD}
  <title>Suriname Travel Guide | Visa, SIM Cards &amp; Money | Explore Suriname</title>
  <meta name="description" content="Everything a first-time visitor needs for Suriname: visa requirements, customs, SIM cards, ATMs, taxi apps, food delivery and mobile payments.">
  <link rel="canonical" href="{SITE_URL}/visitor-guide.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/visitor-guide.html">
  <meta property="og:title" content="Suriname Travel Guide | Visa, SIM Cards &amp; Money | Explore Suriname">
  <meta property="og:description" content="Visa requirements, customs, SIM cards, best ATMs, taxi apps and tips for getting around Suriname. The practical stuff, in one place.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname Travel Guide | Visa, SIM Cards &amp; Money | Explore Suriname">
  <meta name="twitter:description" content="Visa requirements, customs, SIM cards, best ATMs, taxi apps and tips for getting around Suriname.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"Suriname Travel Guide | Visa, SIM Cards, ATMs & Getting Around","url":"{SITE_URL}/visitor-guide.html","description":"Practical guide for first-time visitors to Suriname: visa and entry requirements, customs declaration, SIM cards, ATMs, tipping, taxi apps, food delivery and mobile payments.","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[{{"@type":"Question","name":"Do I need a visa to visit Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Most nationalities need a tourist visa or tourist card for Suriname, arranged through the VFS Global portal before departure. Some nationalities may be exempt. Check the official Suriname immigration requirements for your passport."}}}},{{"@type":"Question","name":"What currency is used in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"The Surinamese Dollar (SRD) is the official currency. USD and EUR are accepted at some hotels and shops, but SRD is needed for most local transactions. ATMs dispensing SRD are widely available in Paramaribo."}}}},{{"@type":"Question","name":"Which SIM card should I buy in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Telesur and Digicel are the two main mobile operators. Telesur has broader 4G coverage across the country. Both sell prepaid SIM cards at the airport and shops in Paramaribo."}}}},{{"@type":"Question","name":"What taxi apps work in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Suriname has local ride-hailing apps. Kura and TaxiSR are the most widely used in Paramaribo. Traditional metered taxis are also available."}}}},{{"@type":"Question","name":"What is the best way to get money in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"ATMs are the most convenient way to get SRD. Hakrinbank and DSB Bank ATMs are reliable and widely available in Paramaribo. Inform your bank before travelling to avoid card blocks."}}}},{{"@type":"Question","name":"Do I need vaccinations to visit Suriname?","acceptedAnswer":{{"@type":"Answer","text":"A yellow fever vaccination certificate is required if you are arriving from a yellow fever risk country. Hepatitis A and B, typhoid and routine vaccines are generally recommended. Malaria prophylaxis is advised if you plan to travel into the interior rainforest. Consult a travel health clinic well before departure."}}}},{{"@type":"Question","name":"Is Suriname safe for tourists?","acceptedAnswer":{{"@type":"Answer","text":"Paramaribo is generally safe for tourists who take standard precautions. Petty theft can occur in busy areas. Avoid displaying valuables in public, use registered taxis or ride-hailing apps, and stay aware of your surroundings at night. The interior rainforest is best explored with a licensed guide."}}}},{{"@type":"Question","name":"What is the tipping culture in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Tipping is not mandatory but is welcomed for good service. At restaurants a tip of 5 to 10 percent is appropriate if no service charge is included. Taxi drivers do not generally expect a tip, though rounding up the fare is a common courtesy. Tour guides often appreciate a gratuity at the end of a tour."}}}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"Suriname Travel Guide","item":"{SITE_URL}/visitor-guide.html"}}]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("visitor")}
<div class="pt-16"></div>
<div class="text-white py-14 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname Travel Guide</h1>
  <p class="text-white/65 text-lg max-w-xl mx-auto px-5">Visas, customs, SIM cards, money and getting around. The practical stuff, in one place.</p>
</div>

<main class="max-w-5xl mx-auto px-5 py-12 pb-24">

  <!-- VISA + CUSTOMS side by side -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Before You Board</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Arrival &amp; Visa</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-5">
        Check the entry requirements for your passport before you book. Most nationalities need a
        tourist visa or tourist card arranged through the VFS Global portal in advance, though
        some go through their nearest Surinamese embassy. Either way, sort it before departure.
      </p>
      <a href="https://www.vfsglobal.com" target="_blank" rel="noopener"
         class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-90 transition mb-5"
         style="background:var(--forest2)">
        VFS Global Portal &#8599;
      </a>
      <div class="rounded-xl p-4 border-l-4" style="background:#fff8f0;border-color:var(--coral)">
        <p class="text-sm font-semibold text-gray-800 mb-1">Yellow Fever Certificate</p>
        <p class="text-sm text-gray-600 leading-relaxed">
          Arriving from sub-Saharan Africa or parts of South America? A valid vaccination
          certificate is checked at the border. Get vaccinated at least 10 days before departure.
          No certificate, no entry.
        </p>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">At the Border</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Customs Declaration</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-5">
        Every visitor fills out a customs and immigration declaration form from the ICF before
        clearing the border. It covers what you are bringing into the country. Cash over
        US&#8239;$10,000 must be declared. The form is handed out on the plane or available
        at the airport, and you can also fill it in through the ICF portal before you travel.
      </p>
      <a href="https://www.icf.sr" target="_blank" rel="noopener"
         class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-90 transition"
         style="background:var(--forest2)">
        ICF Suriname &#8599;
      </a>
    </div>
  </div>

  <!-- MARITIME -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">
    <div class="md:flex md:items-start md:gap-8">
      <div class="md:flex-1">
        <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Maritime Entry</p>
        <h2 class="serif text-xl font-bold text-gray-900 mb-4">Arriving by Boat or Yacht</h2>
        <p class="text-gray-700 text-sm leading-relaxed">
          Before entering Surinamese territorial waters, file a Notice of Arrival with the Maritime
          Authority of Suriname (MAS). This covers private yachts, charter boats and any
          non-commercial vessel. File through the MAS portal and keep a printed copy of the
          confirmation on board for inspection.
        </p>
      </div>
      <div class="mt-5 md:mt-7 md:shrink-0">
        <a href="https://www.mas.sr" target="_blank" rel="noopener"
           class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold text-white hover:opacity-90 transition"
           style="background:var(--forest2)">
          MAS Portal &#8599;
        </a>
      </div>
    </div>
  </div>

  <!-- SIM + MONEY -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Connectivity</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Getting a SIM Card</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-5">
        Two carriers operate in Suriname: <strong>Telesur</strong> and <strong>Digicel</strong>.
        Both have counters in the arrivals hall at Johan Adolf Pengel airport. Bring your passport,
        as registration is mandatory. Coverage is solid across Paramaribo and the coastal belt;
        the interior is a different story on either network.
      </p>
      <div class="flex flex-col gap-2">
        <a href="https://www.telesur.sr" target="_blank" rel="noopener"
           class="flex items-center justify-between px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 hover:border-gray-400 transition">
          Telesur <span style="color:var(--forest2)">&#8599;</span>
        </a>
        <div class="flex items-center justify-between px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-500">
          Digicel Suriname <span class="text-xs font-normal text-gray-400">available in-store</span>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Money</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Cash &amp; ATMs</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-4">
        The currency is the <strong>Surinamese Dollar (SRD)</strong>. For ATM withdrawals,
        <strong>DSB Bank</strong> and <strong>Republic Bank</strong> are the most reliable
        with international Visa and Mastercard. For card payments at shops and restaurants,
        <strong>Southern Commercial Bank (SCom Bank)</strong> leads card acceptance across
        Paramaribo. Outside the city centre, most smaller vendors still work in cash.
      </p>
      <div class="rounded-xl p-4 text-sm" style="background:var(--mint)">
        <span class="font-semibold" style="color:var(--forest)">Tipping:</span>
        <span class="text-gray-700"> 10% is standard at restaurants. Some places add a service charge automatically, so check your bill before adding more.</span>
      </div>
    </div>
  </div>

  <!-- TRANSPORT -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">
    <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Getting Around</p>
    <h2 class="serif text-xl font-bold text-gray-900 mb-4">Taxis &amp; Transport</h2>
    <div class="md:grid md:grid-cols-2 md:gap-8">
      <div>
        <p class="text-gray-700 text-sm leading-relaxed mb-4">
          Johan Adolf Pengel airport is about 45&nbsp;km south of Paramaribo, a 45 to 60 minute
          ride depending on traffic. Taxis at the airport do not use meters, so agree on a price
          before you get in. Suriname drives on the <strong>left</strong>.
        </p>
        <p class="text-gray-700 text-sm leading-relaxed">
          The main ride app in Paramaribo is <strong>1690 Tourtonne</strong>. Prices are shown
          upfront before you confirm, which takes the guesswork out of getting around. Download
          it before you land.
        </p>
      </div>
      <div class="mt-5 md:mt-0">
        <div class="rounded-xl p-5 border border-gray-200 h-full flex flex-col justify-between">
          <div>
            <p class="font-bold text-gray-900 text-sm mb-1">1690 Tourtonne</p>
            <p class="text-gray-500 text-xs mb-4">Taxi app for Paramaribo</p>
          </div>
          <div class="flex gap-2 flex-wrap">
            <a href="https://play.google.com/store/apps/details?id=com.tourtonnestaxi&hl=en" target="_blank" rel="noopener"
               class="text-xs px-3 py-2 rounded-lg border border-gray-200 text-gray-700 hover:border-gray-400 transition font-medium">
              Google Play &#8599;
            </a>
            <a href="https://apps.apple.com/sr/app/tourtonne-taxi-1690/id6760743422" target="_blank" rel="noopener"
               class="text-xs px-3 py-2 rounded-lg border border-gray-200 text-gray-700 hover:border-gray-400 transition font-medium">
              App Store &#8599;
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- FOOD + UNI5PAY -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Food Delivery</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Ride Eats</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-5">
        Ride Eats is the main delivery app in Paramaribo. The selection covers local Surinamese,
        Chinese, Indian and fast food, with decent coverage across the city. Download it
        on your first day.
      </p>
      <div class="flex flex-col gap-2">
        <a href="https://play.google.com/store/apps/details?id=com.resvevo.rideeats" target="_blank" rel="noopener"
           class="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 hover:border-gray-400 transition">
          <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3.18 23.76a2 2 0 0 0 2.08-.15l12.9-7.45-3.32-3.32-11.66 10.92zM.36 1.38A2 2 0 0 0 0 2.5v19a2 2 0 0 0 .36 1.12L.48 23.7l10.66-10.66v-.25L.48 2.13l-.12 1.25zM20.52 10.38l-3.56-2.05-3.73 3.73 3.73 3.73 3.59-2.07a2.03 2.03 0 0 0 0-3.34zM3.18.24L14.84 7.7l-3.32 3.32L.48.38 3.18.24z"/></svg>
          Google Play &#8599;
        </a>
        <a href="https://apps.apple.com/sr/app/ride-eats/id1530050503" target="_blank" rel="noopener"
           class="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 hover:border-gray-400 transition">
          <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
          App Store &#8599;
        </a>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Mobile Payments</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Uni5Pay</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-5">
        Uni5Pay is Suriname's mobile wallet, accepted at a growing number of shops, restaurants
        and vendors across Paramaribo. If you are staying more than a few days, it is worth
        setting up. Registration is quick and you can top up directly in the app.
      </p>
      <div class="flex flex-col gap-2">
        <a href="https://play.google.com/store/apps/details?id=com.unionpay.scomapp" target="_blank" rel="noopener"
           class="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 hover:border-gray-400 transition">
          <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M3.18 23.76a2 2 0 0 0 2.08-.15l12.9-7.45-3.32-3.32-11.66 10.92zM.36 1.38A2 2 0 0 0 0 2.5v19a2 2 0 0 0 .36 1.12L.48 23.7l10.66-10.66v-.25L.48 2.13l-.12 1.25zM20.52 10.38l-3.56-2.05-3.73 3.73 3.73 3.73 3.59-2.07a2.03 2.03 0 0 0 0-3.34zM3.18.24L14.84 7.7l-3.32 3.32L.48.38 3.18.24z"/></svg>
          Google Play &#8599;
        </a>
        <a href="https://apps.apple.com/de/app/uni5pay/id1464144473" target="_blank" rel="noopener"
           class="flex items-center gap-3 px-4 py-3 rounded-xl border border-gray-200 text-sm font-semibold text-gray-800 hover:border-gray-400 transition">
          <svg class="w-4 h-4 shrink-0" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
          App Store &#8599;
        </a>
      </div>
    </div>
  </div>

  <!-- GOOD TO KNOW -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
    <h2 class="serif text-xl font-bold text-gray-900 mb-6">Good to Know</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
      <div class="pl-4 border-l-2" style="border-color:var(--leaf)">
        <p class="font-semibold text-gray-900 text-sm mb-1">Language</p>
        <p class="text-gray-600 text-sm leading-relaxed">Dutch is the official language. Sranan Tongo is the everyday street tongue. English is widely understood in hotels, restaurants and tourist areas across Paramaribo.</p>
      </div>
      <div class="pl-4 border-l-2" style="border-color:var(--leaf)">
        <p class="font-semibold text-gray-900 text-sm mb-1">Power &amp; Plugs</p>
        <p class="text-gray-600 text-sm leading-relaxed">127V / 60Hz, Type A sockets (US-style flat-pin). Some hotels also have 220V outlets. A universal adapter will cover all cases.</p>
      </div>
      <div class="pl-4 border-l-2" style="border-color:var(--leaf)">
        <p class="font-semibold text-gray-900 text-sm mb-1">Drinking Water</p>
        <p class="text-gray-600 text-sm leading-relaxed">Stick to bottled water throughout your stay. Tap water quality varies by area and most locals do the same. Bottles are cheap and available everywhere.</p>
      </div>
      <div class="pl-4 border-l-2" style="border-color:var(--leaf)">
        <p class="font-semibold text-gray-900 text-sm mb-1">Emergency Numbers</p>
        <p class="text-gray-600 text-sm leading-relaxed">Police: <strong class="text-gray-800">115</strong>&ensp;&middot;&ensp;Ambulance: <strong class="text-gray-800">113</strong>&ensp;&middot;&ensp;Fire: <strong class="text-gray-800">110</strong>. Save them before you need them.</p>
      </div>
    </div>
  </div>

</main>
{footer_html()}
</body>
</html>"""

def build_about_page():
    """Static About page — establishes site identity for Google AdSense review."""
    return f"""{PAGE_HEAD}
  <title>About | Explore Suriname</title>
  <meta name="description" content="Explore Suriname is an independent travel and lifestyle guide to Suriname, covering restaurants, hotels, nature, activities, currency rates and local news.">
  <link rel="canonical" href="{SITE_URL}/about.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/about.html">
  <meta property="og:title" content="About | Explore Suriname">
  <meta property="og:description" content="Explore Suriname is an independent travel and lifestyle guide to Suriname.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@exploringsuriname">
  <meta name="twitter:title" content="About | Explore Suriname">
  <meta name="twitter:description" content="Explore Suriname is an independent travel and lifestyle guide to Suriname, covering restaurants, hotels, nature, activities, currency rates and local news.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"AboutPage","name":"About Explore Suriname","url":"{SITE_URL}/about.html","description":"Explore Suriname is an independent travel and lifestyle guide to Suriname.","isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"About","item":"{SITE_URL}/about.html"}}]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("about")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">About Explore Suriname</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">South America&rsquo;s best-kept secret, uncovered</p>
</div>
<main class="max-w-3xl mx-auto px-5 py-12 pb-24">

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-6">
    <h2 class="serif text-2xl font-bold text-gray-900 mb-4">What is Explore Suriname?</h2>
    <p class="text-gray-700 leading-relaxed mb-4">
      Explore Suriname is an independent online guide to everything Suriname has to offer — restaurants,
      hotels and guesthouses, nature reserves, activities, shopping, local services, live currency rates,
      flight schedules, weather forecasts and daily news.
    </p>
    <p class="text-gray-700 leading-relaxed mb-4">
      Suriname is one of the most biodiverse and culturally rich countries in South America, yet it remains
      largely undiscovered by international travellers. Our goal is to change that by providing accurate,
      up-to-date information for visitors and locals alike.
    </p>
    <p class="text-gray-700 leading-relaxed">
      The directory currently covers more than 700 businesses and attractions across Paramaribo and beyond,
      and is updated continuously. If you have a listing to add or a correction to suggest, please
      <a href="contact.html" style="color:var(--forest2)">get in touch</a>.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-6">
    <h2 class="serif text-2xl font-bold text-gray-900 mb-4">What we cover</h2>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm text-gray-700">
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Restaurants &amp; Bars</strong> &mdash; Surinamese, Indonesian, Chinese, Indian, and international cuisine across Paramaribo</span>
      </div>
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Hotels &amp; Lodges</strong> &mdash; from city hotels to rainforest eco-lodges and overwater bungalows</span>
      </div>
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Nature &amp; Activities</strong> &mdash; jungle treks, river tours, wildlife reserves and UNESCO sites</span>
      </div>
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Shopping &amp; Services</strong> &mdash; local retailers, markets and professional services in Paramaribo</span>
      </div>
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Market Rates</strong> &mdash; SRD exchange rates updated three times daily from CBVS and CME</span>
      </div>
      <div class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Flights, Weather &amp; News</strong> &mdash; real-time data to help you plan your stay in Suriname</span>
      </div>
    </div>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-2xl font-bold text-gray-900 mb-4">Contact</h2>
    <p class="text-gray-700 leading-relaxed">
      For listing requests, corrections, partnerships or general questions, reach out via our
      <a href="contact.html" class="font-semibold" style="color:var(--forest2)">contact page</a>
      or email us directly at
      <a href="mailto:{CONTACT_EMAIL}" style="color:var(--forest2)">{CONTACT_EMAIL}</a>.
    </p>
  </div>

</main>
{footer_html()}
</body>
</html>"""


def build_contact_page():
    """Contact page — shows a mailto button instead of a bare email address."""
    return f"""{PAGE_HEAD}
  <title>Contact | Explore Suriname</title>
  <meta name="description" content="Contact Explore Suriname for listing requests, business partnerships, corrections or general enquiries about Suriname travel.">
  <link rel="canonical" href="{SITE_URL}/contact.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/contact.html">
  <meta property="og:title" content="Contact | Explore Suriname">
  <meta property="og:description" content="Get in touch with Explore Suriname for listing requests, corrections or partnerships.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@exploringsuriname">
  <meta name="twitter:title" content="Contact | Explore Suriname">
  <meta name="twitter:description" content="Get in touch with Explore Suriname for listing requests, corrections or partnerships.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"ContactPage","name":"Contact Explore Suriname","url":"{SITE_URL}/contact.html","description":"Contact Explore Suriname for listing requests, corrections or partnerships.","isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"Contact","item":"{SITE_URL}/contact.html"}}]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("contact")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Contact Us</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">We&rsquo;d love to hear from you</p>
</div>
<main class="max-w-2xl mx-auto px-5 py-12 pb-24">

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-6">
    <h2 class="serif text-xl font-bold text-gray-900 mb-2">Get in touch</h2>
    <p class="text-gray-600 text-sm leading-relaxed mb-6">
      Use the button below to send us an email. We respond to all enquiries within a few business days.
    </p>
    <a href="mailto:{CONTACT_EMAIL}?subject=Enquiry%20via%20ExploreSuriname.com"
       class="inline-flex items-center gap-3 px-6 py-3 rounded-xl text-white font-semibold text-sm transition hover:opacity-90"
       style="background:var(--forest)">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
      </svg>
      Send us an email
    </a>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-4">What we can help with</h2>
    <ul class="space-y-3 text-sm text-gray-700">
      <li class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Listing requests</strong> &mdash; add a new business, hotel, restaurant or attraction to the directory</span>
      </li>
      <li class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Corrections</strong> &mdash; update an address, phone number, opening hours or description</span>
      </li>
      <li class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>Partnerships</strong> &mdash; advertising, sponsored listings or content collaborations</span>
      </li>
      <li class="flex items-start gap-3">
        <span class="mt-0.5 text-green-700 font-bold shrink-0">&#10003;</span>
        <span><strong>General questions</strong> &mdash; anything about Suriname travel, the site or our data</span>
      </li>
    </ul>
  </div>

</main>
{footer_html()}
</body>
</html>"""


def build_privacy_page():
    """Privacy Policy page — required for Google AdSense compliance.
    Discloses cookie use, third-party advertising, and how to opt out."""
    policy_date = "1 May 2025"
    return f"""{PAGE_HEAD}
  <title>Privacy Policy | Explore Suriname</title>
  <meta name="description" content="Privacy Policy for ExploreSuriname.com. Learn how we use cookies, what data we collect, and how Google advertising works on this site.">
  <link rel="canonical" href="{SITE_URL}/privacy.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/privacy.html">
  <meta property="og:title" content="Privacy Policy | Explore Suriname">
  <meta property="og:description" content="How ExploreSuriname.com uses cookies and handles your data.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="robots" content="noindex, follow">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("privacy")}
<div class="pt-16"></div>
<div class="text-white py-12 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-3xl sm:text-4xl font-bold mb-2">Privacy Policy</h1>
  <p class="text-white/60 text-sm">Last updated: {policy_date}</p>
</div>
<main class="max-w-3xl mx-auto px-5 py-12 pb-24 space-y-6">

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">1. Who we are</h2>
    <p class="text-gray-700 text-sm leading-relaxed">
      This Privacy Policy applies to <strong>ExploreSuriname.com</strong> (&ldquo;the Site&rdquo;), an
      independent travel and lifestyle guide to Suriname. For questions about this policy, contact us at
      <a href="mailto:{CONTACT_EMAIL}" style="color:var(--forest2)">{CONTACT_EMAIL}</a>.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">2. Information we collect</h2>
    <p class="text-gray-700 text-sm leading-relaxed mb-3">
      We do not require registration and do not collect your name, email address or any personally
      identifiable information unless you contact us directly. When you visit the Site, standard web
      server logs may record your IP address, browser type, referring page, and pages visited. This
      information is used only for site administration and is never sold or shared with third parties
      except as described below.
    </p>
    <p class="text-gray-700 text-sm leading-relaxed">
      If you send us an email, we retain your message and email address only to respond to your
      enquiry and for no other purpose.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">3. Cookies</h2>
    <p class="text-gray-700 text-sm leading-relaxed mb-4">
      Cookies are small text files stored on your device by your browser. We use cookies for the
      following purposes:
    </p>
    <div class="space-y-4 text-sm text-gray-700">
      <div>
        <p class="font-semibold text-gray-900 mb-1">Functional cookies</p>
        <p class="leading-relaxed">Used to remember your preferences (such as filter or sort selections) during your visit. These cookies are session-based and expire when you close your browser.</p>
      </div>
      <div>
        <p class="font-semibold text-gray-900 mb-1">Analytics cookies</p>
        <p class="leading-relaxed">We may use analytics tools to understand how visitors use the Site in aggregate. No individual user profiles are built.</p>
      </div>
      <div>
        <p class="font-semibold text-gray-900 mb-1">Advertising cookies (Google AdSense)</p>
        <p class="leading-relaxed">
          This Site uses <strong>Google AdSense</strong>, a third-party advertising service provided by Google LLC.
          Google AdSense places cookies on your device to serve personalised advertisements based on your browsing
          history across websites. Google&rsquo;s advertising cookies include the <strong>DoubleClick cookie</strong>
          and similar technologies that allow Google and its partners to serve ads based on your interests.
        </p>
        <p class="leading-relaxed mt-2">
          You may opt out of personalised advertising by visiting
          <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener" style="color:var(--forest2)">Google Ads Settings</a>
          or <a href="https://www.aboutads.info" target="_blank" rel="noopener" style="color:var(--forest2)">www.aboutads.info</a>.
          You can also opt out of Google Analytics by installing the
          <a href="https://tools.google.com/dlpage/gaoptout" target="_blank" rel="noopener" style="color:var(--forest2)">Google Analytics opt-out browser add-on</a>.
        </p>
      </div>
    </div>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">4. Third-party advertising</h2>
    <p class="text-gray-700 text-sm leading-relaxed mb-3">
      We use <strong>Google AdSense</strong> to display advertisements on this Site. Google AdSense is
      operated by Google LLC, 1600 Amphitheatre Parkway, Mountain View, CA 94043, USA.
    </p>
    <p class="text-gray-700 text-sm leading-relaxed mb-3">
      Third-party vendors, including Google, use cookies to serve ads based on a user&rsquo;s prior
      visits to this website or other websites. Google&rsquo;s use of advertising cookies enables
      it and its partners to serve ads based on your visit to this Site and/or other sites on the internet.
    </p>
    <p class="text-gray-700 text-sm leading-relaxed">
      We have no access to or control over the cookies used by Google or other third-party advertisers.
      For more information on how Google uses data when you visit sites that use Google services,
      see <a href="https://policies.google.com/technologies/partner-sites" target="_blank" rel="noopener" style="color:var(--forest2)">Google&rsquo;s privacy policy</a>.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">5. External links</h2>
    <p class="text-gray-700 text-sm leading-relaxed">
      The Site contains links to external websites and sources (news outlets, business websites, map
      services, etc.). We are not responsible for the privacy practices or content of those sites.
      We encourage you to read the privacy policies of any external sites you visit.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">6. Data retention &amp; security</h2>
    <p class="text-gray-700 text-sm leading-relaxed">
      We retain email correspondence for as long as necessary to resolve your enquiry. Server log
      files are retained for a maximum of 90 days. We take reasonable steps to protect information
      but cannot guarantee the security of data transmitted over the internet.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">7. Your rights</h2>
    <p class="text-gray-700 text-sm leading-relaxed mb-3">
      You may request access to, correction of, or deletion of any personal data we hold about you
      by contacting us at <a href="mailto:{CONTACT_EMAIL}" style="color:var(--forest2)">{CONTACT_EMAIL}</a>.
    </p>
    <p class="text-gray-700 text-sm leading-relaxed">
      To manage or disable cookies, adjust your browser settings. Note that disabling cookies may
      affect the functionality of this Site and other websites.
    </p>
  </div>

  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">8. Changes to this policy</h2>
    <p class="text-gray-700 text-sm leading-relaxed">
      We may update this Privacy Policy from time to time. Changes will be posted on this page
      with an updated &ldquo;Last updated&rdquo; date. Continued use of the Site after any changes
      constitutes acceptance of the updated policy.
    </p>
  </div>

</main>
{footer_html()}
</body>
</html>"""


def build_sitemap(biz_slugs, act_slugs, nat_slugs):
    """Generate sitemap.xml covering all pages and listing URLs."""
    today = datetime.now(SR_TZ).strftime("%Y-%m-%d")

    # ── Per-listing lastmod tracking (hash-based) ────────────────────────────
    # Persist a slug→date map so lastmod only advances when content changes.
    import hashlib as _hl
    _lastmod_path = Path("listing_lastmod_cache.json")
    try:
        _lastmod_cache = json.loads(_lastmod_path.read_text(encoding="utf-8")) if _lastmod_path.exists() else {}
    except Exception:
        _lastmod_cache = {}

    def _listing_lastmod(slug):
        """Return lastmod date for a listing — only updates when HTML changes."""
        html_path = Path("listing") / slug / "index.html"
        if not html_path.exists():
            return today
        try:
            h = _hl.md5(html_path.read_bytes()).hexdigest()
        except Exception:
            return today
        if _lastmod_cache.get(slug, {}).get("hash") == h:
            return _lastmod_cache[slug]["date"]
        _lastmod_cache[slug] = {"hash": h, "date": today}
        return today

    def _flush_lastmod():
        try:
            _lastmod_path.write_text(
                json.dumps(_lastmod_cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    static_pages = [
        ("",                "1.0", "daily"),
        ("restaurants.html","0.9", "weekly"),
        ("hotels.html",     "0.9", "weekly"),
        ("activities.html", "0.9", "weekly"),
        ("nature.html",     "0.9", "weekly"),
        ("shopping.html",   "0.8", "weekly"),
        ("services.html",   "0.8", "weekly"),
        ("currency.html",   "0.9", "daily"),
        ("flights.html",    "0.8", "daily"),
        ("conditions.html", "0.8", "daily"),
        ("visitor-guide.html","0.8", "monthly"),
        ("on-the-road.html", "0.7", "monthly"),
        ("news.html",       "0.7", "daily"),
        ("about.html",      "0.5", "yearly"),
        ("contact.html",    "0.5", "yearly"),
        ("privacy.html",    "0.3", "yearly"),
    ]

    urls = []
    for path_seg, priority, freq in static_pages:
        loc = SITE_URL + "/" + path_seg
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{freq}</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    _act_nat_set = set(act_slugs) | set(nat_slugs)
    for slug in biz_slugs:
        if slug in _act_nat_set:
            continue  # already included in act/nat loop below — prevents duplicates
        loc = SITE_URL + "/listing/" + slug + "/"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{_listing_lastmod(slug)}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.7</priority>\n"
            f"  </url>"
        )

    for slug in act_slugs + nat_slugs:
        loc = SITE_URL + "/listing/" + slug + "/"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{_listing_lastmod(slug)}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.6</priority>\n"
            f"  </url>"
        )

    _flush_lastmod()
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls)
            + "\n\n</urlset>\n")


def build_robots():
    """Return robots.txt content."""
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"


def build_manifest():
    """Return manifest.webmanifest content for PWA."""
    import json as _j
    manifest = {
        "name": "Explore Suriname",
        "short_name": "ExploreSR",
        "description": "Travel & lifestyle guide to Suriname: hotels, restaurants, nature and live SRD rates.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1B4332",
        "lang": "en",
        "scope": "/",
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            {"src": "/favicon.svg",        "sizes": "any",     "type": "image/svg+xml", "purpose": "any"},
        ],
        "categories": ["travel", "lifestyle", "food"],
        "screenshots": [
            {"src": "/og-image.jpg", "sizes": "1200x630", "type": "image/jpeg", "form_factor": "wide", "label": "Explore Suriname home page"}
        ],
        "shortcuts": [
            {"name": "Restaurants",   "url": "/restaurants.html", "description": "Paramaribo restaurants & dining", "icons": [{"src": "/favicon.svg", "sizes": "any"}]},
            {"name": "Exchange Rates","url": "/currency.html",     "description": "Live SRD exchange rates",         "icons": [{"src": "/favicon.svg", "sizes": "any"}]},
            {"name": "Nature & Parks","url": "/nature.html",       "description": "Suriname nature spots",           "icons": [{"src": "/favicon.svg", "sizes": "any"}]},
            {"name": "Flights",       "url": "/flights.html",      "description": "PBM arrivals & departures",       "icons": [{"src": "/favicon.svg", "sizes": "any"}]},
        ],
    }
    return _j.dumps(manifest, indent=2, ensure_ascii=False)


def build_sw():
    """Return sw.js service worker content."""
    return r"""// ExploreSuriname Service Worker
const CACHE = 'exploresr-v2';
const PRECACHE = ['/', '/tailwind.css', '/favicon.ico', '/favicon.svg', '/offline.html'];
const LIVE_PAGES = new Set(['/currency.html', '/flights.html', '/conditions.html', '/news.html']);

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(PRECACHE)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const sameOrigin = u.origin === location.origin;
  const isFont = u.hostname === 'fonts.googleapis.com' || u.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !isFont) return;

  // Network-first for live-data pages (currency, flights, tides, news)
  if (sameOrigin && LIVE_PAGES.has(u.pathname)) {
    e.respondWith(
      fetch(e.request)
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => caches.match(e.request).then(r => r || caches.match('/offline.html')))
    );
    return;
  }

  // Cache-first for static assets (CSS, JS, images, fonts, icons)
  if (u.pathname.match(/\.(css|js|svg|webp|png|jpg|ico|woff2?)$/) || isFont) {
    e.respondWith(
      caches.match(e.request).then(cached => {
        const network = fetch(e.request).then(r => {
          caches.open(CACHE).then(c => c.put(e.request, r.clone()));
          return r;
        });
        return cached || network;
      })
    );
    return;
  }

  // Stale-while-revalidate for HTML pages
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request)
        .then(r => { caches.open(CACHE).then(c => c.put(e.request, r.clone())); return r; })
        .catch(() => cached || caches.match('/offline.html'));
      return cached || network;
    })
  );
});
"""


def build_offline():
    """Return a simple offline fallback page."""
    return f"""{PAGE_HEAD}
  <title>You're Offline | Explore Suriname</title>
  <meta name="description" content="You appear to be offline. Please check your connection and try again.">
  <meta property="og:title" content="Offline | Explore Suriname">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html()}
<div class="pt-16"></div>
<div class="text-white py-20 text-center" style="background:var(--forest)">
  <p class="text-6xl mb-4">🌿</p>
  <h1 class="serif text-4xl font-bold mb-3">You're offline</h1>
  <p class="text-white/70 text-lg max-w-sm mx-auto px-5">Check your connection and try again — or explore pages you've already visited.</p>
  <button onclick="location.reload()"
    class="mt-8 inline-block px-8 py-3 rounded-full font-semibold text-white border-2 border-white/50 hover:bg-white/10 transition">
    Try again
  </button>
</div>
{footer_html()}
</body></html>"""


def _generate_pwa_icons():
    """Generate 192×192 and 512×512 PNG icons via Wand (ImageMagick SVG renderer).
    Falls back to a Pillow super-sampled version if Wand is unavailable.
    Skips regeneration if icons already exist (preserves manually committed icons)."""
    import os as _os
    _os.makedirs("icons", exist_ok=True)

    if _os.path.exists("icons/icon-192.png") and _os.path.exists("icons/icon-512.png"):
        print("  SKIP  icons — using committed versions")
        return

    _ICON_SVG = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" ry="96" fill="#1B4332"/>
  <rect x="112" y="112" width="88"  height="288" rx="8" fill="#E76F51"/>
  <rect x="112" y="112" width="280" height="76"  rx="8" fill="#E76F51"/>
  <rect x="112" y="218" width="232" height="76"  rx="8" fill="#E76F51"/>
  <rect x="112" y="324" width="280" height="76"  rx="8" fill="#E76F51"/>
</svg>"""

    try:
        from wand.image import Image as _WandImage
        from wand.color import Color as _Color
        for size in (192, 512):
            with _WandImage(blob=_ICON_SVG, format='svg', width=size, height=size) as img:
                img.background_color = _Color('white')
                img.format = 'png'
                img.save(filename=f"icons/icon-{size}.png")
            print(f"  OK  icons/icon-{size}.png (Wand)")
        return
    except ImportError:
        pass

    # Pillow super-sampled fallback
    try:
        from PIL import Image as _Image, ImageDraw as _ImageDraw
    except ImportError:
        print("  SKIP  icons — Pillow not available")
        return

    def _make_pillow_icon(size):
        SCALE = 4
        S = size * SCALE
        img  = _Image.new("RGB", (S, S), (255, 255, 255))
        draw = _ImageDraw.Draw(img)
        r    = S // 8
        draw.rounded_rectangle([0, 0, S-1, S-1], radius=r, fill=(27, 67, 50))
        pad   = round(S * 0.219)
        sw    = round(S * 0.172)
        bh    = round(S * 0.148)
        gap   = round((S - 2*pad - 3*bh) / 2)
        coral = (231, 111, 81)
        draw.rectangle([pad, pad, pad+sw, S-pad], fill=coral)
        draw.rectangle([pad, pad, S-pad, pad+bh], fill=coral)
        mid_y = pad + bh + gap
        draw.rectangle([pad, mid_y, S-pad-round(S*0.094), mid_y+bh], fill=coral)
        bot_y = S - pad - bh
        draw.rectangle([pad, bot_y, S-pad, S-pad], fill=coral)
        return img.resize((size, size), _Image.LANCZOS)

    for size in (192, 512):
        _make_pillow_icon(size).save(f"icons/icon-{size}.png", "PNG")
        print(f"  OK  icons/icon-{size}.png (Pillow fallback)")


def build_conditions_page(tides_data):
    """
    tides_data: dict keyed by TIDES_LOCATIONS id → (extremes, is_live, updated_str)
    """
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")

    def _tide_panel(loc, extremes, is_live, updated):
        """Build HTML for one tide location panel."""
        if not extremes:
            return f"""
<div id="tpanel-{loc['id']}" class="tide-panel hidden">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
    <p class="text-4xl mb-3">&#127754;</p>
    <p class="text-gray-500 text-sm">No tide data available for {html_lib.escape(loc['label'])}.</p>
  </div>
</div>"""

        from collections import defaultdict
        by_day = defaultdict(list)
        for ex in extremes:
            dt  = datetime.fromtimestamp(ex["dt"], tz=SR_TZ)
            day = dt.strftime("%A, %d %b")
            by_day[day].append({
                "type":   ex["type"],
                "time":   dt.strftime("%H:%M SR"),
                "height": f"{ex['height']:.2f} m",
                "icon":   "\U0001f53c" if ex["type"] == "High" else "\U0001f53d",
            })

        rows = ""
        tide_cards = ""
        for day, events in list(by_day.items())[:3]:
            for ev in events:
                rows += (
                    '<tr class="border-b border-gray-100">'
                    f'<td class="py-3 px-4 text-gray-500 text-sm">{day}</td>'
                    f'<td class="py-3 px-4 font-semibold">{ev["icon"]} {ev["type"]} Tide</td>'
                    f'<td class="py-3 px-4 font-mono font-bold">{ev["time"]}</td>'
                    f'<td class="py-3 px-4 text-right font-mono text-gray-700">{ev["height"]}</td>'
                    '</tr>'
                )
                tide_cards += (
                    '<div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0 px-4">'
                    '<div>'
                    f'<p class="font-semibold text-gray-900 text-sm">{ev["icon"]} {ev["type"]} Tide</p>'
                    f'<p class="text-gray-500 text-xs mt-0.5">{day}</p>'
                    '</div>'
                    '<div class="text-right">'
                    f'<p class="font-mono font-bold text-gray-900 text-sm">{ev["time"]}</p>'
                    f'<p class="font-mono text-gray-500 text-xs mt-0.5">{ev["height"]}</p>'
                    '</div>'
                    '</div>'
                )

        badge = ('<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">&#9679; Live</span>'
                 if is_live else
                 '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">&#9675; Cached</span>')
        cache_note = f"Refreshes every {loc['cache_h']}h"

        return f"""
<div id="tpanel-{loc['id']}" class="tide-panel hidden">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="px-6 py-5 border-b border-gray-100">
      <p class="font-bold text-gray-900 text-base">&#127754; {html_lib.escape(loc['label'])} &mdash; {html_lib.escape(loc['district'])} {badge}</p>
      <p class="text-gray-400 text-xs mt-1">&#128336; Updated: {html_lib.escape(updated)} &bull; {cache_note}</p>
    </div>
    <div class="hidden sm:block overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="bg-gray-50 text-left">
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Date</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Tide</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Time (SR)</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Height</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
    <div class="sm:hidden py-1">{tide_cards}</div>
  </div>
</div>"""

    # Build tide panels + tab buttons
    tide_tabs_html   = ""
    tide_panels_html = ""
    has_any_tides    = False

    for idx, loc in enumerate(TIDES_LOCATIONS):
        extremes, is_live, updated = tides_data.get(loc["id"], ([], False, "No data"))
        if extremes:
            has_any_tides = True
        active_cls   = "tide-tab border-b-2 font-bold text-gray-900 px-4 py-3 text-sm whitespace-nowrap" if idx == 0 else "tide-tab text-gray-500 hover:text-gray-700 px-4 py-3 text-sm whitespace-nowrap"
        active_style = 'style="border-color:var(--forest2)"' if idx == 0 else ""
        tide_tabs_html += (
            f'<button onclick="showTide(\'{loc["id"]}\')" id="ttab-{loc["id"]}" '
            f'class="{active_cls} transition" {active_style}>'
            f'{html_lib.escape(loc["label"])}</button>\n'
        )
        panel = _tide_panel(loc, extremes, is_live, updated)
        # First panel not hidden
        if idx == 0:
            panel = panel.replace(' class="tide-panel hidden"', ' class="tide-panel"')
        tide_panels_html += panel

    if not has_any_tides:
        tides_section = """
<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
  <p class="text-5xl mb-4">&#127754;</p>
  <h3 class="font-bold text-gray-900 mb-2">Tide Predictions</h3>
  <p class="text-gray-500 text-sm max-w-md mx-auto">Set the <code class="bg-gray-100 px-1 rounded">WORLDTIDES_KEY</code> GitHub Actions secret to enable tidal forecasts.</p>
</div>"""
    else:
        tides_section = f"""
<div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-4">
  <div class="flex overflow-x-auto border-b border-gray-100" style="scrollbar-width:none">
    {tide_tabs_html}
  </div>
</div>
{tide_panels_html}"""

    # District weather coords for JS (open-meteo, free/unlimited)
    wx_districts = [
        {"label": "Paramaribo",  "lat": 5.852,  "lon": -55.203},
        {"label": "Wanica",      "lat": 5.730,  "lon": -55.250},
        {"label": "Nickerie",    "lat": 5.940,  "lon": -56.978},
        {"label": "Commewijne",  "lat": 5.893,  "lon": -55.087},
        {"label": "Marowijne",   "lat": 5.491,  "lon": -54.057},
        {"label": "Brokopondo",  "lat": 4.762,  "lon": -55.027},
        {"label": "Para",        "lat": 5.490,  "lon": -55.226},
        {"label": "Saramacca",   "lat": 5.793,  "lon": -55.467},
    ]
    import json as _json
    wx_districts_js = _json.dumps(wx_districts)

    return f"""{PAGE_HEAD}
  <title>Suriname Weather &amp; River Tides | Live Forecast | Explore Suriname</title>
  <meta name="description" content="Tidal predictions for Suriname's rivers, 7-day weather forecasts by district, sunrise/sunset times and UV index. Updated continuously.">
  <link rel="canonical" href="{SITE_URL}/conditions.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/conditions.html">
  <meta property="og:title" content="Suriname Weather &amp; River Tides | Live Forecast | Explore Suriname">
  <meta property="og:description" content="Tidal predictions for Suriname's rivers, 7-day district forecasts and sunrise/sunset times. Updated continuously.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname Weather &amp; River Tides | Live Forecast | Explore Suriname">
  <meta name="twitter:description" content="Tidal predictions for Suriname's rivers, 7-day district forecasts and sunrise/sunset times. Updated continuously.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"Suriname Weather & River Tides | Live Forecast","url":"{SITE_URL}/conditions.html","description":"Tidal predictions for the Suriname, Commewijne, Nickerie and Marowijne rivers, plus 7-day weather forecasts by district. Updated continuously.","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {{"@type":"Question","name":"What is the best time to visit Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Suriname has two dry seasons: the short dry season from February to April, and the long dry season from August to November. These are generally the best periods to visit, with less rainfall and easier travel conditions in the interior. August to October is considered the peak season for nature and rainforest tours."}}}},
    {{"@type":"Question","name":"Does Suriname have a rainy season?","acceptedAnswer":{{"@type":"Answer","text":"Yes, Suriname has two rainy seasons: the long rainy season from mid-April to mid-August, and the short rainy season from mid-November to mid-February. During these periods rainfall is frequent, though it typically comes in short, intense showers rather than all-day rain."}}}},
    {{"@type":"Question","name":"How hot is it in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Suriname has a tropical climate with temperatures ranging from 26°C to 32°C (79°F to 90°F) year-round. Humidity is high throughout the year. Paramaribo on the coast is slightly cooler than the interior rainforest."}}}},
    {{"@type":"Question","name":"What is the weather like in Paramaribo?","acceptedAnswer":{{"@type":"Answer","text":"Paramaribo has a tropical climate with hot, humid conditions year-round. Average temperatures stay between 26°C and 31°C. The city receives rainfall across all months, with heavier periods during the two rainy seasons. Sea breezes from the Atlantic can provide some relief in coastal areas."}}}},
    {{"@type":"Question","name":"How high is the UV index in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Suriname sits near the equator and UV levels are consistently very high, often reaching UV index 11 or above during midday. Sun protection is strongly recommended year-round. Wear high-SPF sunscreen, a hat and protective clothing, especially during outdoor activities between 10:00 and 16:00."}}}},
    {{"@type":"Question","name":"What are the tides like in Suriname's rivers?","acceptedAnswer":{{"@type":"Answer","text":"The Suriname, Commewijne, Nickerie and Marowijne rivers all experience semi-diurnal tides (two high tides and two low tides per day) driven by Atlantic tidal patterns. Tidal range varies by location and season. The tide forecasts on this page are updated daily for all four rivers."}}}},
    {{"@type":"Question","name":"Does Suriname get hurricanes?","acceptedAnswer":{{"@type":"Answer","text":"Suriname lies south of the main Atlantic hurricane belt and is rarely affected by direct hurricane strikes. Tropical disturbances can occasionally bring heavy rainfall, but major hurricane impacts are uncommon. Suriname does experience frequent short but intense rain showers, particularly during the two rainy seasons."}}}}
  ]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"Weather & Tides","item":"{SITE_URL}/conditions.html"}}]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("forecast")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname Weather &amp; River Tides</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">Live weather by district &bull; tidal forecasts for 4 rivers &bull; sunrise &amp; sunset</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">

  <!-- Weather — district selector -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 sm:p-8 mb-6">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h2 class="serif text-2xl font-bold text-gray-900">&#127777;&#65039; Weather</h2>
        <p class="text-gray-400 text-sm mt-1">Live via <a href="https://open-meteo.com" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">Open-Meteo</a></p>
      </div>
      <span id="wx-badge" class="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0 ml-4">Loading&hellip;</span>
    </div>
    <!-- District selector -->
    <div class="flex gap-2 flex-wrap mb-5">
      <p class="text-xs font-semibold text-gray-500 self-center mr-1">District:</p>
      <div id="wx-district-tabs" class="flex gap-1 flex-wrap"></div>
    </div>
    <!-- Current conditions: 5 tiles -->
    <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-5">
      <div class="col-span-2 sm:col-span-1 rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Temperature</p>
        <p id="wx-temp" class="text-3xl font-bold font-mono text-gray-900">&mdash;</p>
        <p id="wx-feels" class="text-xs text-gray-400 mt-1">Feels like &mdash;</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Condition</p>
        <p id="wx-icon" class="text-3xl mb-1">&#127780;</p>
        <p id="wx-desc" class="text-xs text-gray-600 font-medium">&mdash;</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Humidity</p>
        <p id="wx-hum" class="text-3xl font-bold font-mono text-gray-900">&mdash;</p>
        <p class="text-xs text-gray-400 mt-1">Relative</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Wind</p>
        <p id="wx-wind" class="text-3xl font-bold font-mono text-gray-900">&mdash;</p>
        <p id="wx-wdir" class="text-xs text-gray-400 mt-1">&mdash;</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">UV Index</p>
        <p id="wx-uv" class="text-3xl font-bold font-mono text-gray-900">&mdash;</p>
        <p id="wx-uv-label" class="text-xs mt-1 font-semibold">&mdash;</p>
      </div>
    </div>
    <!-- Rain next 2 hours (minutely_15) -->
    <div class="rounded-xl p-4 mb-5" style="background:#eff6ff">
      <div class="flex items-center justify-between mb-2">
        <p class="text-xs font-semibold text-gray-600 uppercase tracking-wide">&#127783; Rain next 2 hours</p>
        <p id="wx-rain-summary" class="text-xs font-semibold text-blue-600">&mdash;</p>
      </div>
      <div class="flex items-end gap-px h-10" id="wx-rain-bars"></div>
      <div class="flex gap-px mt-1.5" id="wx-rain-times"></div>
    </div>
    <!-- 24-hour strip -->
    <div class="mb-5">
      <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">Next 24 hours</h3>
      <div class="overflow-x-auto -mx-2 px-2 pb-1" style="scrollbar-width:none">
        <div id="wx-hourly" class="flex gap-1.5"></div>
      </div>
    </div>
    <!-- 7-day forecast (clickable) -->
    <div>
      <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">7-day &mdash; <span class="normal-case font-normal text-gray-400">tap a day for detail</span></h3>
      <div class="overflow-x-auto -mx-2 px-2 pb-1" style="scrollbar-width:none">
        <div id="wx-forecast" class="flex gap-2 sm:grid sm:grid-cols-7"></div>
      </div>
      <div id="wx-day-detail" class="hidden mt-3 rounded-xl overflow-hidden" style="border:1px solid #bfdbfe">
        <div class="px-4 py-2.5 flex items-center justify-between" style="background:#eff6ff">
          <p id="wx-day-detail-title" class="text-xs font-semibold text-gray-700 uppercase tracking-wide">&mdash;</p>
          <button onclick="document.getElementById('wx-day-detail').classList.add('hidden')" class="text-gray-400 hover:text-gray-600 text-xl leading-none font-light">&times;</button>
        </div>
        <div class="overflow-x-auto px-3 py-3 bg-white" style="scrollbar-width:none">
          <div id="wx-day-detail-hours" class="flex gap-1.5"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Sunrise & Sunset -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-6">
    <h2 class="serif text-2xl font-bold text-gray-900 mb-6">&#9728;&#65039; Sunrise &amp; Sunset</h2>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="rounded-xl p-5 text-center" style="background:#fff8e1">
        <p class="text-4xl mb-2">&#127749;</p>
        <p class="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Sunrise</p>
        <p id="ss-rise" class="text-2xl font-bold font-mono text-gray-900">&mdash;</p>
        <p class="text-xs text-gray-400 mt-1">Suriname time</p>
      </div>
      <div class="rounded-xl p-5 text-center" style="background:var(--mint)">
        <p class="text-4xl mb-2">&#9203;</p>
        <p class="text-xs font-semibold uppercase tracking-wide mb-1" style="color:var(--forest2)">Day Length</p>
        <p id="ss-len" class="text-2xl font-bold font-mono text-gray-900">&mdash;</p>
        <p class="text-xs text-gray-400 mt-1">Hours of daylight</p>
      </div>
      <div class="rounded-xl p-5 text-center" style="background:#e8f4fd">
        <p class="text-4xl mb-2">&#127751;</p>
        <p class="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1">Sunset</p>
        <p id="ss-set" class="text-2xl font-bold font-mono text-gray-900">&mdash;</p>
        <p class="text-xs text-gray-400 mt-1">Suriname time</p>
      </div>
    </div>
    <p class="text-gray-400 text-xs text-center mt-4">Data from <a href="https://sunrise-sunset.org" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">sunrise-sunset.org</a>. Updates with selected district.</p>
  </div>

  <!-- Fishermen's Corner: Tides by river -->
  <div class="mb-6">
    <div class="flex items-center gap-3 mb-4">
      <h2 class="serif text-2xl font-bold text-gray-900">&#9973;&#65039; Fishermen&apos;s Corner</h2>
      <span class="text-xs font-semibold px-2 py-0.5 rounded-full text-white" style="background:var(--forest2)">For mariners &amp; fishers</span>
    </div>
    {tides_section}
    <p class="text-gray-400 text-xs mt-3">Tide heights are relative to lowest astronomical tide (LAT). Always verify with local authorities before heading out.</p>
  </div>

</main>

<script>
var WMO = {{
  0:['&#9728;&#65039;','Clear sky'], 1:['&#127780;','Mainly clear'], 2:['&#9925;','Partly cloudy'],
  3:['&#9729;','Overcast'], 45:['&#127787;','Fog'], 48:['&#127787;','Freezing fog'],
  51:['&#127782;','Light drizzle'], 53:['&#127782;','Drizzle'], 55:['&#127783;','Heavy drizzle'],
  61:['&#127783;','Light rain'], 63:['&#127783;','Rain'], 65:['&#127783;','Heavy rain'],
  80:['&#127782;','Showers'], 81:['&#127783;','Heavy showers'], 82:['&#9928;','Violent showers'],
  95:['&#9928;','Thunderstorm'], 96:['&#9928;','Storm + hail'], 99:['&#9928;','Heavy storm']
}};
var DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
var MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
var WX_DISTRICTS = {wx_districts_js};
var _curDistrict = 0;
var _wxHourly = null;

function uvLabel(v) {{
  if (v <= 2) return ['Low','#16a34a'];
  if (v <= 5) return ['Moderate','#ca8a04'];
  if (v <= 7) return ['High','#ea580c'];
  if (v <= 10) return ['Very High','#dc2626'];
  return ['Extreme','#7c3aed'];
}}

// Build district tabs
(function(){{
  var container = document.getElementById('wx-district-tabs');
  WX_DISTRICTS.forEach(function(d, i) {{
    var btn = document.createElement('button');
    btn.textContent = d.label;
    btn.dataset.idx = i;
    btn.className = 'wx-dtab text-xs font-semibold px-3 py-1.5 rounded-full border transition';
    if (i === 0) {{
      btn.style.background = 'var(--forest)'; btn.style.borderColor = 'var(--forest)'; btn.style.color = '#fff';
    }} else {{
      btn.style.borderColor = '#e5e7eb'; btn.style.color = '#374151'; btn.style.background = '#fff';
    }}
    btn.onclick = function() {{
      _curDistrict = i;
      document.querySelectorAll('.wx-dtab').forEach(function(b) {{
        b.style.background = '#fff'; b.style.borderColor = '#e5e7eb'; b.style.color = '#374151';
      }});
      btn.style.background = 'var(--forest)'; btn.style.borderColor = 'var(--forest)'; btn.style.color = '#fff';
      document.getElementById('wx-day-detail').classList.add('hidden');
      loadWeather(d.lat, d.lon);
      loadSunrise(d.lat, d.lon);
    }};
    container.appendChild(btn);
  }});
}})();

function loadWeather(lat, lon) {{
  document.getElementById('wx-badge').innerHTML = 'Loading&hellip;';
  document.getElementById('wx-badge').className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0 ml-4';
  var url = 'https://api.open-meteo.com/v1/forecast?latitude=' + lat + '&longitude=' + lon
    + '&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m,uv_index'
    + '&minutely_15=precipitation,weather_code'
    + '&hourly=temperature_2m,weather_code,precipitation_probability,precipitation,wind_speed_10m'
    + '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
    + '&wind_speed_unit=kmh&timezone=America%2FParamaribo&forecast_days=7';
  fetch(url).then(function(r){{return r.json();}}).then(function(d){{

    // --- Current conditions ---
    var c = d.current;
    var wmo = WMO[c.weather_code] || ['&#127777;','Unknown'];
    document.getElementById('wx-temp').textContent  = Math.round(c.temperature_2m) + '°C';
    document.getElementById('wx-feels').textContent = 'Feels like ' + Math.round(c.apparent_temperature) + '°C';
    document.getElementById('wx-icon').innerHTML    = wmo[0];
    document.getElementById('wx-desc').textContent  = wmo[1];
    document.getElementById('wx-hum').textContent   = c.relative_humidity_2m + '%';
    document.getElementById('wx-wind').textContent  = Math.round(c.wind_speed_10m) + ' km/h';
    var dirs = ['N','NE','E','SE','S','SW','W','NW'];
    var deg  = c.wind_direction_10m;
    document.getElementById('wx-wdir').textContent  = dirs[Math.round(deg/45)%8] + ' · ' + Math.round(deg) + '°';
    var uvVal  = Math.round(c.uv_index || 0);
    var uvInfo = uvLabel(uvVal);
    document.getElementById('wx-uv').textContent       = uvVal;
    document.getElementById('wx-uv').style.color       = uvInfo[1];
    document.getElementById('wx-uv-label').textContent = uvInfo[0];
    document.getElementById('wx-uv-label').style.color = uvInfo[1];
    var badge = document.getElementById('wx-badge');
    badge.innerHTML = '&#9679; Live';
    badge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800 shrink-0 ml-4';

    // --- Rain next 2 hours (minutely_15) ---
    var m15 = d.minutely_15;
    if (m15 && m15.time && m15.precipitation) {{
      var now = new Date();
      var bars = document.getElementById('wx-rain-bars');
      var timesEl = document.getElementById('wx-rain-times');
      bars.innerHTML = ''; timesEl.innerHTML = '';
      var startIdx = 0;
      for (var k = 0; k < m15.time.length; k++) {{
        if (new Date(m15.time[k]) >= now) {{ startIdx = k; break; }}
      }}
      var slots = Math.min(8, m15.time.length - startIdx);
      var maxP = 0;
      for (var k = startIdx; k < startIdx + slots; k++) {{ maxP = Math.max(maxP, m15.precipitation[k] || 0); }}
      var anyRain = false, firstRainTime = null;
      for (var k = startIdx; k < startIdx + slots; k++) {{
        var p  = m15.precipitation[k] || 0;
        var t  = new Date(m15.time[k]);
        var hh = ('0'+t.getHours()).slice(-2);
        var mm = ('0'+t.getMinutes()).slice(-2);
        var h  = maxP > 0 ? Math.max(4, Math.round((p / maxP) * 38)) : 4;
        var col = p < 0.05 ? '#bfdbfe' : p < 0.3 ? '#60a5fa' : p < 1.5 ? '#2563eb' : '#1e3a8a';
        bars.innerHTML += '<div style="flex:1;height:' + h + 'px;background:' + col + ';border-radius:3px 3px 0 0;min-width:0" title="' + p.toFixed(1) + 'mm"></div>';
        var showLabel = (k === startIdx || (k - startIdx) % 2 === 0);
        timesEl.innerHTML += '<div style="flex:1;text-align:center;font-size:9px;color:#9ca3af;min-width:0">' + (showLabel ? hh+':'+mm : '') + '</div>';
        if (p >= 0.05 && !anyRain) {{ anyRain = true; firstRainTime = hh + ':' + mm; }}
      }}
      var sumEl = document.getElementById('wx-rain-summary');
      if (!anyRain) {{
        sumEl.textContent = 'Dry for now ✔'; sumEl.style.color = '#16a34a';
      }} else {{
        var t0 = new Date(m15.time[startIdx]);
        var isNow = (new Date(m15.time[startIdx]).getTime() === new Date(m15.time[startIdx]).getTime()) && p >= 0.05;
        var firstSlotRaining = (m15.precipitation[startIdx] || 0) >= 0.05;
        sumEl.textContent = firstSlotRaining ? 'Raining now' : ('Rain ~' + firstRainTime);
        sumEl.style.color = '#2563eb';
      }}
    }}

    // --- 24-hour strip ---
    var hr = d.hourly;
    _wxHourly = hr;
    if (hr && hr.time) {{
      var nowMs = Date.now();
      var strip = document.getElementById('wx-hourly');
      strip.innerHTML = '';
      var count = 0;
      for (var i = 0; i < hr.time.length && count < 24; i++) {{
        var t = new Date(hr.time[i]);
        if (t.getTime() < nowMs - 1800000) continue;
        var w  = WMO[hr.weather_code[i]] || ['&#127777;',''];
        var rp = hr.precipitation_probability[i] || 0;
        var isNow = count === 0;
        var bg = isNow ? 'var(--forest)' : '#f8fafc';
        var tc = isNow ? '#fff' : '#111827';
        var sc = isNow ? 'rgba(255,255,255,0.65)' : '#9ca3af';
        var rc = isNow ? '#93c5fd' : '#3b82f6';
        var hh = ('0'+t.getHours()).slice(-2) + ':00';
        strip.innerHTML += '<div class="flex flex-col items-center text-center rounded-xl p-2 shrink-0" style="background:' + bg + ';min-width:54px">'
          + '<p style="font-size:10px;font-weight:600;color:' + sc + '">' + (isNow ? 'Now' : hh) + '</p>'
          + '<p style="font-size:20px;margin:3px 0">' + w[0] + '</p>'
          + '<p style="font-size:11px;font-weight:700;color:' + tc + '">' + Math.round(hr.temperature_2m[i]) + '°</p>'
          + (rp > 15 ? '<p style="font-size:9px;color:' + rc + ';margin-top:2px">&#128167;' + rp + '%</p>' : '<p style="font-size:9px;margin-top:2px;color:transparent">.</p>')
          + '</div>';
        count++;
      }}
    }}

    // --- 7-day forecast ---
    var fc = d.daily, fbox = document.getElementById('wx-forecast');
    fbox.innerHTML = '';
    for (var i = 0; i < 7; i++) {{
      var dt = new Date(fc.time[i] + 'T12:00:00');
      var dn = i === 0 ? 'Today' : DAYS[dt.getDay()];
      var w  = WMO[fc.weather_code[i]] || ['&#127777;',''];
      var rn = fc.precipitation_probability_max[i] || 0;
      var card = document.createElement('div');
      card.className = 'wx-day-card flex flex-col items-center text-center rounded-xl p-2 shrink-0 cursor-pointer transition-all';
      card.style.cssText = 'background:#f8fafc;min-width:68px;border:2px solid transparent';
      card.dataset.dayIdx = i;
      card.innerHTML = '<p style="font-size:10px;font-weight:600;color:#6b7280">' + dn + '</p>'
        + '<p style="font-size:22px;margin:4px 0">' + w[0] + '</p>'
        + '<p style="font-size:12px;font-weight:700;color:#111827">' + Math.round(fc.temperature_2m_max[i]) + '°</p>'
        + '<p style="font-size:10px;color:#9ca3af">' + Math.round(fc.temperature_2m_min[i]) + '°</p>'
        + (rn > 15 ? '<p style="font-size:9px;color:#3b82f6;margin-top:2px">&#128167;' + rn + '%</p>' : '<p style="font-size:9px;margin-top:2px;color:transparent">.</p>');
      card.onclick = (function(idx, el) {{
        return function() {{
          document.querySelectorAll('.wx-day-card').forEach(function(c) {{
            c.style.background = '#f8fafc'; c.style.borderColor = 'transparent';
          }});
          el.style.background = '#eff6ff'; el.style.borderColor = '#3b82f6';
          showDayDetail(idx);
        }};
      }})(i, card);
      fbox.appendChild(card);
    }}

  }}).catch(function() {{
    document.getElementById('wx-badge').textContent = 'Unavailable';
    document.getElementById('wx-badge').className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-500 shrink-0 ml-4';
  }});
}}

function showDayDetail(dayIdx) {{
  var detail  = document.getElementById('wx-day-detail');
  var title   = document.getElementById('wx-day-detail-title');
  var hourBox = document.getElementById('wx-day-detail-hours');
  if (!_wxHourly) {{ detail.classList.add('hidden'); return; }}
  var hr = _wxHourly;
  var dayDate = new Date(hr.time[dayIdx * 24] + (hr.time[dayIdx * 24].length === 16 ? ':00' : ''));
  title.textContent = (dayIdx === 0 ? 'Today' : DAYS[new Date(hr.time[dayIdx*24]).getDay()]) + ', ' + new Date(hr.time[dayIdx*24]).getDate() + ' ' + MONTHS[new Date(hr.time[dayIdx*24]).getMonth()];
  hourBox.innerHTML = '';
  var startH = dayIdx * 24;
  for (var i = startH; i < startH + 24 && i < hr.time.length; i++) {{
    var t  = new Date(hr.time[i]);
    var w  = WMO[hr.weather_code[i]] || ['&#127777;',''];
    var rp = hr.precipitation_probability[i] || 0;
    var p  = hr.precipitation[i] || 0;
    var hh = ('0'+t.getHours()).slice(-2) + ':00';
    var rainBit = p >= 0.1
      ? '<p style="font-size:9px;color:#2563eb;margin-top:2px;font-weight:600">' + p.toFixed(1) + 'mm</p>'
      : rp > 20
        ? '<p style="font-size:9px;color:#60a5fa;margin-top:2px">&#128167;' + rp + '%</p>'
        : '<p style="font-size:9px;margin-top:2px;color:transparent">.</p>';
    hourBox.innerHTML += '<div class="flex flex-col items-center text-center rounded-xl p-2 shrink-0" style="background:#f8fafc;border:1px solid #e5e7eb;min-width:54px">'
      + '<p style="font-size:10px;font-weight:600;color:#6b7280">' + hh + '</p>'
      + '<p style="font-size:20px;margin:3px 0">' + w[0] + '</p>'
      + '<p style="font-size:11px;font-weight:700;color:#111827">' + Math.round(hr.temperature_2m[i]) + '°</p>'
      + rainBit
      + '</div>';
  }}
  detail.classList.remove('hidden');
  setTimeout(function() {{ detail.scrollIntoView({{behavior:'smooth',block:'nearest'}}); }}, 50);
}}

// Initial load — Paramaribo
loadWeather(WX_DISTRICTS[0].lat, WX_DISTRICTS[0].lon);

function loadSunrise(lat, lon) {{
  fetch('https://api.sunrise-sunset.org/json?lat=' + lat + '&lng=' + lon + '&formatted=0')
    .then(function(r){{return r.json();}})
    .then(function(d){{
      var res = d.results;
      function toSR(iso){{
        var dt = new Date(iso);
        var sr = new Date(dt.getTime() - 3*3600000);
        return ('0'+sr.getUTCHours()).slice(-2)+':'+('0'+sr.getUTCMinutes()).slice(-2);
      }}
      document.getElementById('ss-rise').textContent = toSR(res.sunrise);
      document.getElementById('ss-set').textContent  = toSR(res.sunset);
      var s = res.day_length;
      document.getElementById('ss-len').textContent  = Math.floor(s/3600)+'h '+Math.floor((s%3600)/60)+'m';
    }})
    .catch(function(){{
      ['ss-rise','ss-set','ss-len'].forEach(function(id){{document.getElementById(id).textContent='Unavailable';}});
    }});
}}
loadSunrise(WX_DISTRICTS[0].lat, WX_DISTRICTS[0].lon);

// Tide tab switching
function showTide(id) {{
  document.querySelectorAll('.tide-panel').forEach(function(p){{p.classList.add('hidden');}});
  document.querySelectorAll('.tide-tab').forEach(function(t){{
    t.classList.remove('border-b-2','font-bold','text-gray-900');
    t.classList.add('text-gray-500');
    t.removeAttribute('style');
  }});
  var panel = document.getElementById('tpanel-' + id);
  var tab   = document.getElementById('ttab-'   + id);
  if (panel) panel.classList.remove('hidden');
  if (tab) {{
    tab.classList.add('border-b-2','font-bold','text-gray-900');
    tab.classList.remove('text-gray-500');
    tab.style.borderColor = 'var(--forest2)';
  }}
}}
</script>
{footer_html()}
</body>
</html>"""


# ── Flights page (OpenSky — arrivals/departures at PBM) ─────────────────────


# ── Flights page — multi-airport with tabs ───────────────────────────────────

def build_flights_page(flights_data):
    """
    flights_data: dict returned by fetch_aerodatabox_flights() — now via FR24
      { icao: (arrivals, departures, updated_str), ... }
    """
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")

    def flight_rows(flights, direction):
        if not flights:
            return (f'<tr><td colspan="4" class="py-8 text-center text-gray-400 text-sm">'
                    f'No scheduled {direction}s found for today. '
                    f'This airport may have limited or no commercial service.</td></tr>')
        rows = ""
        for fl in flights:
            rows += (
                '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                f'<td class="py-3 px-4 font-mono font-bold text-gray-900 whitespace-nowrap">{html_lib.escape(fl["flight"])}</td>'
                f'<td class="py-3 px-4 text-gray-700 text-sm">{html_lib.escape(fl["airline"])}</td>'
                f'<td class="py-3 px-4 text-gray-600 text-sm">{html_lib.escape(fl["airport"])}</td>'
                f'<td class="py-3 px-4 text-right font-mono text-gray-700 text-sm whitespace-nowrap">{html_lib.escape(fl["time"])}</td>'
                '</tr>'
            )
        return rows

    def flight_cards(flights, direction):
        if not flights:
            return (f'<div class="py-6 text-center text-gray-400 text-sm px-4">'
                    f'No scheduled {direction}s found for today.</div>')
        cards = ""
        for fl in flights:
            cards += (
                '<div class="flex items-center justify-between py-3 border-b border-gray-100 last:border-0 px-4">'
                '<div class="flex-1 min-w-0 pr-3">'
                f'<div class="flex items-center gap-2">'
                f'<span class="font-mono font-bold text-gray-900 text-sm">{html_lib.escape(fl["flight"])}</span>'
                f'<span class="text-gray-500 text-xs truncate">{html_lib.escape(fl["airline"])}</span>'
                f'</div>'
                f'<p class="text-gray-500 text-xs mt-0.5 truncate">{html_lib.escape(fl["airport"])}</p>'
                '</div>'
                f'<span class="font-mono text-gray-800 text-sm font-semibold shrink-0">{html_lib.escape(fl["time"])}</span>'
                '</div>'
            )
        return cards

    def count_badge(n):
        return (f'<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full '
                f'bg-green-100 text-green-800">{n} flights</span>') if n else ""

    # Build per-airport panel HTML
    panels_html = ""
    tab_buttons_html = ""
    for idx, ap in enumerate(_AIRPORTS_FLIGHT):
        icao = ap["icao"]
        arrivals, departures, updated = flights_data.get(icao, ([], [], updated_now))
        arr_rows  = flight_rows(arrivals,   "arrival")
        dep_rows  = flight_rows(departures, "departure")
        arr_cards = flight_cards(arrivals,   "arrival")
        dep_cards = flight_cards(departures, "departure")
        active_tab   = "border-b-2 font-bold text-gray-900" if idx == 0 else "text-gray-500 hover:text-gray-700"
        active_style = 'style="border-color:var(--forest)"' if idx == 0 else ""
        panel_hidden = "" if idx == 0 else " hidden"
        cache_note   = f"Refreshes every {ap['cache_h']}h"
        tab_buttons_html += (
            f'<button onclick="showAirport(\'{icao}\')" id="tab-{icao}" '
            f'class="airport-tab px-4 py-3 text-sm {active_tab} whitespace-nowrap transition" '
            f'{active_style}>{ap["label"]}</button>\n'
        )
        panels_html += f"""
<div id="panel-{icao}" class="airport-panel{panel_hidden}">
  <p class="text-gray-400 text-xs mb-4">&#128336; Updated: {html_lib.escape(updated)} &bull; {cache_note}</p>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
    <div class="px-6 py-5 border-b border-gray-100">
      <p class="font-bold text-gray-900 text-base">&#9650; Arrivals &mdash; {html_lib.escape(ap["label"])} {count_badge(len(arrivals))}</p>
      <p class="text-gray-400 text-xs mt-0.5">Scheduled arrivals today</p>
    </div>
    <div class="hidden sm:block overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="bg-gray-50 text-left">
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Flight</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Airline</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">From</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Time (SR)</th>
        </tr></thead>
        <tbody>{arr_rows}</tbody>
      </table>
    </div>
    <div class="sm:hidden py-1">{arr_cards}</div>
  </div>
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
    <div class="px-6 py-5 border-b border-gray-100">
      <p class="font-bold text-gray-900 text-base">&#9660; Departures &mdash; {html_lib.escape(ap["label"])} {count_badge(len(departures))}</p>
      <p class="text-gray-400 text-xs mt-0.5">Scheduled departures today</p>
    </div>
    <div class="hidden sm:block overflow-x-auto">
      <table class="w-full text-sm">
        <thead><tr class="bg-gray-50 text-left">
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Flight</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Airline</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">To</th>
          <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Time (SR)</th>
        </tr></thead>
        <tbody>{dep_rows}</tbody>
      </table>
    </div>
    <div class="sm:hidden py-1">{dep_cards}</div>
  </div>
</div>"""

    return f"""{PAGE_HEAD}
  <title>Suriname Flights Today | PBM Arrivals &amp; Departures | Explore Suriname</title>
  <meta name="description" content="Live arrivals and departures at Johan Adolf Pengel (PBM) and Eduard Alexander Gummels (EAX). KLM, Copa Airlines, Caribbean Airlines and Surinam Airways.">
  <link rel="canonical" href="{SITE_URL}/flights.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/flights.html">
  <meta property="og:title" content="Suriname Flights Today | PBM Arrivals &amp; Departures | Explore Suriname">
  <meta property="og:description" content="Live arrivals and departures at Johan Adolf Pengel (PBM) and Eduard Alexander Gummels (EAX). KLM, Copa Airlines, Caribbean Airlines and Surinam Airways.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname Flights Today | PBM Arrivals &amp; Departures | Explore Suriname">
  <meta name="twitter:description" content="Live arrivals and departures at Johan Adolf Pengel (PBM) and Eduard Alexander Gummels (EAX). KLM, Copa Airlines, Caribbean Airlines and Surinam Airways.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"Suriname Flights Today | PBM Arrivals & Departures","url":"{SITE_URL}/flights.html","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}},"description":"Today's arrivals and departures at Suriname airports including Johan Adolf Pengel (PBM) and Eduard Alexander Gummels (EAX)."}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {{"@type":"Question","name":"Which airlines fly to Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Airlines serving Suriname include KLM (Amsterdam), Copa Airlines (Panama City), Caribbean Airlines (Trinidad), and Surinam Airways on regional routes. KLM operates direct flights from Amsterdam to Johan Adolf Pengel International Airport (PBM), making it the primary route for European travelers."}}}},
    {{"@type":"Question","name":"What is the main airport in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Johan Adolf Pengel International Airport (IATA: PBM), also known as Zanderij Airport, is Suriname\'s main international airport. It is located approximately 45 km south of Paramaribo. Eduard Alexander Gummels Airport (EAX) in Paramaribo handles some domestic and regional flights."}}}},
    {{"@type":"Question","name":"How long is a flight from Amsterdam to Suriname?","acceptedAnswer":{{"@type":"Answer","text":"A direct flight from Amsterdam Schiphol (AMS) to Johan Adolf Pengel International Airport (PBM) takes approximately 9 to 10 hours. KLM operates this route several times per week."}}}},
    {{"@type":"Question","name":"Do I need a visa to fly to Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Most nationalities require a tourist visa or tourist card to enter Suriname. These are arranged through the VFS Global portal before departure. Some Caribbean and South American nationalities may be exempt. Always check the latest Suriname immigration requirements for your passport before booking flights."}}}},
    {{"@type":"Question","name":"How far is Johan Adolf Pengel Airport from Paramaribo?","acceptedAnswer":{{"@type":"Answer","text":"Johan Adolf Pengel International Airport (PBM) is located approximately 45 km south of Paramaribo city centre. The drive typically takes 40 to 60 minutes depending on traffic conditions."}}}},
    {{"@type":"Question","name":"How do I get from Suriname airport to Paramaribo?","acceptedAnswer":{{"@type":"Answer","text":"The most common options are licensed airport taxis with a fixed fare agreed before boarding, or private transfer services booked in advance. Ride-hailing apps do not currently operate at Johan Adolf Pengel Airport. The journey to central Paramaribo takes approximately 45 to 60 minutes."}}}},
    {{"@type":"Question","name":"Does KLM fly direct to Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Yes. KLM operates direct flights between Amsterdam Schiphol (AMS) and Johan Adolf Pengel International Airport (PBM) several times per week. The flight takes approximately 9 to 10 hours. KLM is the primary airline connecting Europe to Suriname."}}}}
  ]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"Flights","item":"{SITE_URL}/flights.html"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Airport","name":"Johan Adolf Pengel International Airport","iataCode":"PBM","icaoCode":"SMJP","address":{{"@type":"PostalAddress","addressCountry":"SR","addressRegion":"Wanica","addressLocality":"Zanderij"}},"geo":{{"@type":"GeoCoordinates","latitude":5.4528,"longitude":-55.1878}},"url":"https://www.japi-airport.com"}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"Airport","name":"Eduard Alexander Gummels Airport","iataCode":"ORG","icaoCode":"SMCO","address":{{"@type":"PostalAddress","addressCountry":"SR","addressLocality":"Paramaribo"}},"geo":{{"@type":"GeoCoordinates","latitude":5.8108,"longitude":-55.1908}}}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("flights")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname Flights Today</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">Arrivals &amp; departures &mdash; Johan Adolf Pengel (PBM) &bull; Eduard Alexander Gummels (EAX)</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
    <div class="flex overflow-x-auto border-b border-gray-100" style="scrollbar-width:none">
      {tab_buttons_html}
    </div>
  </div>
  {panels_html}
  <!-- Flight Resources -->
  <div class="mt-8 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="px-5 py-4 border-b border-gray-100">
      <p class="text-xs font-bold text-gray-500 uppercase tracking-wide">Flight Resources</p>
    </div>
    <div class="p-5">
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
        <div>
          <p class="font-bold text-gray-900 text-sm mb-1">Johan Adolf Pengel &mdash; PBM</p>
          <p class="text-gray-500 text-sm leading-relaxed">International airport, 45&nbsp;km south of Paramaribo. Served by KLM (Amsterdam), Copa Airlines (Panama City), Caribbean Airlines (Trinidad) and Surinam Airways.</p>
        </div>
        <div>
          <p class="font-bold text-gray-900 text-sm mb-1">Eduard Alexander Gummels &mdash; EAX</p>
          <p class="text-gray-500 text-sm leading-relaxed">City airport handling domestic flights and charter routes to Nickerie, Moengo and interior airstrips.</p>
        </div>
      </div>
      <div class="flex flex-wrap items-center gap-3">
        <a href="https://www.flightradar24.com/5.85,-55.20/10" target="_blank" rel="noopener"
           class="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold border border-gray-200 text-gray-700 bg-white transition hover:bg-gray-50">
          Real-time Flight Tracking &rarr;
        </a>
      </div>
      <p class="text-gray-400 text-xs mt-4 leading-relaxed">Data from FlightRadar24. Scheduled times only &mdash; not for operational use. PBM updates every 6h; EAX every 12h.</p>
    </div>
  </div>
</main>
<script>
function showAirport(icao) {{
  document.querySelectorAll('.airport-panel').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('.airport-tab').forEach(t => {{
    t.classList.remove('border-b-2','font-bold','text-gray-900');
    t.classList.add('text-gray-500');
    t.removeAttribute('style');
  }});
  var panel = document.getElementById('panel-' + icao);
  var tab   = document.getElementById('tab-'   + icao);
  if (panel) panel.classList.remove('hidden');
  if (tab) {{
    tab.classList.add('border-b-2','font-bold','text-gray-900');
    tab.classList.remove('text-gray-500');
    tab.style.borderColor = 'var(--forest)';
  }}
}}
</script>
{footer_html()}
</body>
</html>"""


# ── Interactive map page (Google Maps JS API) ────────────────────────────────

# District centroid coordinates (lat, lng)
_DISTRICT_COORDS = {
    "Paramaribo":  (5.852, -55.203),
    "Wanica":      (5.751, -55.255),
    "Commewijne":  (5.730, -54.997),
    "Para":        (5.530, -55.182),
    "Nickerie":    (5.940, -56.978),
    "Marowijne":   (5.490, -54.060),
    "Brokopondo":  (4.762, -55.023),
    "Saramacca":   (5.750, -55.670),
    "Coronie":     (5.820, -56.330),
    "Sipaliwini":  (3.916, -56.196),
}

_CAT_COLORS = {
    "restaurant": "#7c3aed",
    "hotel":      "#c05621",
    "shopping":   "#0369a1",
    "service":    "#374151",
    "activity":   "#166534",
    "nature":     "#15803d",
    "other":      "#6b7280",
}



def build_roads_page():
    """On the Road: embedded Waze Live Map + road info panels for Suriname."""
    return f"""{PAGE_HEAD}
  <title>Suriname Traffic &amp; Road Guide | Live Waze Map | Explore Suriname</title>
  <meta name="description" content="Live Suriname traffic and road conditions. Speed limits, emergency numbers, driving rules, rainy season road advisory and what to do after an accident.">
  <link rel="canonical" href="{SITE_URL}/on-the-road.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/on-the-road.html">
  <meta property="og:title" content="Suriname Traffic &amp; Road Guide | Live Waze Map | Explore Suriname">
  <meta property="og:description" content="Live Suriname traffic and road conditions. Speed limits, emergency numbers, driving rules, rainy season advisory and a live Waze map.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname Traffic &amp; Road Guide | Live Waze Map | Explore Suriname">
  <meta name="twitter:description" content="Live Suriname traffic and road conditions. Speed limits, emergency numbers, driving rules, rainy season advisory and a live Waze map.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"WebPage","name":"Suriname Traffic & Road Guide | Live Waze Map","url":"{SITE_URL}/on-the-road.html","description":"Live traffic and road conditions in Suriname. Emergency numbers, road rules, speed limits, rainy season advisory and what to do after an accident.","dateModified":"{datetime.now(SR_TZ).strftime('%Y-%m-%d')}","about":{{"@type":"Place","name":"Suriname","addressCountry":"SR"}},"isPartOf":{{"@type":"WebSite","name":"Explore Suriname","url":"{SITE_URL}/"}}}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[{{"@type":"ListItem","position":1,"name":"Home","item":"{SITE_URL}/"}},{{"@type":"ListItem","position":2,"name":"On the Road","item":"{SITE_URL}/on-the-road.html"}}]}}
  </script>
  <script type="application/ld+json">
  {{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
    {{"@type":"Question","name":"What side of the road do you drive on in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"In Suriname, traffic drives on the left side of the road."}}}},
    {{"@type":"Question","name":"What are the speed limits in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Speed limits in Suriname are 40 km/h in urban areas, 80 km/h on rural roads and 100 km/h on motorways."}}}},
    {{"@type":"Question","name":"What is the blood alcohol limit for drivers in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"The legal blood alcohol limit for drivers in Suriname is 0.05%."}}}},
    {{"@type":"Question","name":"Do I need an International Driving Permit to drive in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Yes. Foreign visitors need an International Driving Permit (IDP) alongside their valid national licence. If you arrive without one, you can apply for a local driving permit at the Bureau Nieuwe Haven in Paramaribo."}}}},
    {{"@type":"Question","name":"What are the emergency numbers in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"In Suriname, call 115 for the police, 113 for the ambulance and 110 for the fire department."}}}},
    {{"@type":"Question","name":"What should I do after a car accident in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Stay at the scene and call 115 if anyone is injured. Fill in the SURVAM Aanrijdingsformulier (collision form) together with the other driver. Photograph the damage and the other driver's driving licence and insurance certificate, then notify your insurer as soon as possible."}}}},
    {{"@type":"Question","name":"When must I call the police after an accident in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Call the police on 115 if someone is seriously injured, a serious traffic violation was involved such as running a red light or driving under the influence, the other driver disputes the facts, the other driver left the scene without providing their details, or the damage is due to theft or vandalism."}}}},
    {{"@type":"Question","name":"What can I report on Waze in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Waze lets drivers report accidents, police checks, road closures, hazards and traffic jams in real time. Every report improves the live map for other drivers in Suriname."}}}},
    {{"@type":"Question","name":"Are there toll roads in Suriname?","acceptedAnswer":{{"@type":"Answer","text":"Suriname does not have a toll road system. Roads are generally free to use. Some ferry crossings, such as across the Suriname River between Paramaribo and the Commewijne district, charge a small fee."}}}},
    {{"@type":"Question","name":"What should I know about driving to Suriname's interior?","acceptedAnswer":{{"@type":"Answer","text":"The road from Paramaribo to the interior transitions from paved highway to unpaved dirt tracks. A high-clearance vehicle or 4WD is strongly recommended beyond Atjoni. Road conditions deteriorate significantly during the rainy season. Inform someone of your route and estimated return time before venturing into the interior, and carry sufficient fuel, water and emergency supplies."}}}}
  ]}}
  </script>
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("roads")}
<div class="pt-16"></div>

<div class="text-white py-10 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-6 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname Road Conditions</h1>
  <p class="text-white/65 text-lg max-w-xl mx-auto px-5">Waze drivers across Suriname report accidents, closures and hazards as they happen. Check before you go.</p>
</div>

<!-- MAP -->
<div style="height:calc(100vh - 220px);min-height:560px;max-height:900px">
  <iframe
    src="https://embed.waze.com/iframe?zoom=13&lat=5.8520&lon=-55.2038&ct=livemap&pin=0"
    title="Waze Live Map, Suriname road conditions"
    width="100%"
    height="100%"
    style="border:0;display:block;width:100%;height:100%"
    allowfullscreen
  ></iframe>
</div>

<main class="max-w-5xl mx-auto px-5 py-12 pb-24">

  <!-- RAINY SEASON ADVISORY (JS-driven) -->
  <div id="season-banner" class="hidden rounded-2xl p-5 mb-8 border-l-4" style="background:#fff8f0;border-color:var(--coral)">
    <p class="text-sm font-semibold text-gray-800 mb-1" id="season-title"></p>
    <p class="text-sm text-gray-600 leading-relaxed" id="season-body"></p>
  </div>
  <script>
  (function(){{
    var m = new Date().getMonth(); // 0=Jan
    var banner = document.getElementById('season-banner');
    var title  = document.getElementById('season-title');
    var body   = document.getElementById('season-body');
    // Short rainy: Dec(11), Jan(0)
    // Long rainy:  Apr(3)–Aug(7), peak May–Jun
    if(m === 11 || m === 0){{
      title.textContent = 'Short Rainy Season: December to January';
      body.textContent  = 'Expect daily showers and reduced visibility. Allow extra travel time and watch for standing water on low-lying roads.';
      banner.classList.remove('hidden');
    }} else if(m >= 3 && m <= 7){{
      var peak = (m === 4 || m === 5) ? ' May and June are the wettest months.' : '';
      title.textContent = 'Long Rainy Season: April to August';
      body.textContent  = 'Heavy and prolonged rainfall is common during this period.' + peak + ' Expect reduced visibility, slippery roads and possible delays.';
      banner.classList.remove('hidden');
    }}
    // Dry seasons: Feb-Mar(1-2) and Aug-Nov(8-10) - no banner shown
  }})();
  </script>

  <!-- REPORT ON WAZE -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">
    <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Community Traffic</p>
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">Report on Waze</h2>
    <p class="text-gray-700 text-sm leading-relaxed mb-5">
      The Waze map is powered by drivers reporting what they see. Accidents, police checks, road
      closures, hazards and traffic jams. Every report improves the map for everyone in Suriname.
      Open Waze, tap the report button and pick what you see.
    </p>
    <div class="flex flex-wrap gap-3 mb-5">
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold text-white" style="background:var(--coral)">Accident</span>
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold text-white" style="background:var(--forest2)">Road Closed</span>
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold text-white" style="background:var(--forest2)">Hazard</span>
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold text-white" style="background:var(--forest2)">Police</span>
      <span class="px-3 py-1.5 rounded-full text-xs font-semibold text-white" style="background:var(--forest2)">Traffic Jam</span>
    </div>
    <a href="https://waze.com/ul?ll=5.8520,-55.2038&zoom=13"
       target="_blank" rel="noopener"
       class="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-semibold text-white hover:opacity-90 transition"
       style="background:#05c8f7;color:#1a1a1a">
      Open Waze &amp; Report &#8599;
    </a>
  </div>

  <!-- EMERGENCY NUMBERS -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">
    <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Emergency</p>
    <h2 class="serif text-xl font-bold text-gray-900 mb-4">Emergency Numbers</h2>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <a href="tel:115" class="flex flex-col items-center justify-center rounded-xl p-5 text-center hover:opacity-90 transition" style="background:var(--forest)">
        <span class="text-3xl font-bold text-white mb-1">115</span>
        <span class="text-white/75 text-sm font-semibold">Police</span>
      </a>
      <a href="tel:113" class="flex flex-col items-center justify-center rounded-xl p-5 text-center hover:opacity-90 transition" style="background:var(--coral)">
        <span class="text-3xl font-bold text-white mb-1">113</span>
        <span class="text-white/75 text-sm font-semibold">Ambulance</span>
      </a>
      <a href="tel:110" class="flex flex-col items-center justify-center rounded-xl p-5 text-center hover:opacity-90 transition" style="background:#b45309">
        <span class="text-3xl font-bold text-white mb-1">110</span>
        <span class="text-white/75 text-sm font-semibold">Fire Department</span>
      </a>
    </div>

  </div>

  <!-- ROAD RULES + FOREIGN LICENCE side by side -->
  <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Know Before You Drive</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Road Rules</h2>
      <table class="w-full text-sm">
        <tbody class="divide-y divide-gray-100">
          <tr><td class="py-2.5 text-gray-500 pr-4 w-1/2">Traffic side</td><td class="py-2.5 font-semibold text-gray-800">Left-hand traffic</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Urban speed limit</td><td class="py-2.5 font-semibold text-gray-800">40 km/h</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Rural roads</td><td class="py-2.5 font-semibold text-gray-800">80 km/h</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Motorways</td><td class="py-2.5 font-semibold text-gray-800">100 km/h</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Blood alcohol limit</td><td class="py-2.5 font-semibold text-gray-800">0.05%</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Seatbelts</td><td class="py-2.5 font-semibold text-gray-800">Mandatory</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Child seats</td><td class="py-2.5 font-semibold text-gray-800">Required by law</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Mobile phone use</td><td class="py-2.5 font-semibold text-gray-800">Hands-free only</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Motorcycle helmets</td><td class="py-2.5 font-semibold text-gray-800">Mandatory</td></tr>
          <tr><td class="py-2.5 text-gray-500 pr-4">Minimum driving age</td><td class="py-2.5 font-semibold text-gray-800">18 years</td></tr>
        </tbody>
      </table>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7">
      <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Visitors</p>
      <h2 class="serif text-xl font-bold text-gray-900 mb-4">Foreign Driving Licence</h2>
      <p class="text-gray-700 text-sm leading-relaxed mb-4">
        To drive in Suriname on a foreign licence, you need an
        <strong>International Driving Permit (IDP)</strong> alongside your valid national licence.
        Get the IDP from your home country's motoring association before you travel.
      </p>
      <p class="text-gray-700 text-sm leading-relaxed mb-4">
        If you arrive without one, you can apply for a local driving permit at the
        <strong>Bureau Nieuwe Haven</strong> in Paramaribo using your foreign licence.
        Permits are issued for up to one year and can be renewed.
      </p>
      <div class="rounded-xl p-4 border-l-4" style="background:#f0fdf4;border-color:var(--forest2)">
        <p class="text-sm text-gray-700 leading-relaxed">
          Car rental companies require drivers to be <strong>at least 21 years old</strong>
          and to have held their licence for at least one year.
        </p>
      </div>
    </div>

  </div>

  <!-- AFTER AN ACCIDENT -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">
    <p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">If It Happens</p>
    <h2 class="serif text-xl font-bold text-gray-900 mb-3">After an Accident</h2>
    <p class="text-gray-600 text-sm leading-relaxed mb-5">
      In Suriname, the standard procedure after a collision is to complete the
      <strong>SURVAM Aanrijdingsformulier</strong> (collision form) together with the other driver
      at the scene. Keep a copy in your vehicle. Your insurer needs it to process a claim.
    </p>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-bold uppercase tracking-wide mb-2" style="color:var(--forest)">1. Stay at the scene</p>
        <p class="text-sm text-gray-700 leading-relaxed">Do not leave. Move the vehicle to the roadside only if it is safe and the vehicle can be driven.</p>
      </div>
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-bold uppercase tracking-wide mb-2" style="color:var(--forest)">2. Check for injuries</p>
        <p class="text-sm text-gray-700 leading-relaxed">If anyone is injured, call <strong>115</strong> (police) immediately. They will dispatch an ambulance when needed.</p>
      </div>
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-bold uppercase tracking-wide mb-2" style="color:var(--forest)">3. Complete the collision form</p>
        <p class="text-sm text-gray-700 leading-relaxed">Fill in the SURVAM Aanrijdingsformulier together with the other driver. Note the cause, sketch the road position, record the damage, and both parties sign both sides.</p>
      </div>
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-bold uppercase tracking-wide mb-2" style="color:var(--forest)">4. Document everything</p>
        <p class="text-sm text-gray-700 leading-relaxed">Photograph the damage, the road situation, and the other driver's <strong>driving licence and insurance certificate</strong>. Get witness names and phone numbers.</p>
      </div>
      <div class="rounded-xl p-4" style="background:var(--mint)">
        <p class="text-xs font-bold uppercase tracking-wide mb-2" style="color:var(--forest)">5. Report to your insurer</p>
        <p class="text-sm text-gray-700 leading-relaxed">Notify your insurance company as soon as possible with the completed form and your photos.</p>
      </div>
    </div>
    <div class="rounded-xl p-5 border-l-4" style="background:#fff8f0;border-color:var(--coral)">
      <p class="text-sm font-semibold text-gray-800 mb-2">When to call the police (115)</p>
      <ul class="text-sm text-gray-700 space-y-1">
        <li>Someone is seriously injured</li>
        <li>A serious traffic violation was involved: running a red light, driving under the influence</li>
        <li>The other driver disputes the facts or the situation escalates</li>
        <li>The other driver left the scene without leaving their details (hit and run)</li>
        <li>The damage is due to theft, break-in or vandalism</li>
      </ul>
    </div>
  </div>

</main>

{footer_html()}
</body>
</html>"""


def build_map_page(gmaps_key=""):
    """Removed — map page disabled."""
    return ""



if __name__ == "__main__":
    print("ExploreSuriname generator starting...")

    articles     = fetch_articles()
    oil_articles     = fetch_oil_articles()
    finance_articles = fetch_finance_articles()
    cme_rates,  cme_live,  cme_updated  = fetch_cme_rates()
    cbvs_rates, cbvs_live, cbvs_updated = fetch_cbvs_rates()
    brent_price, brent_updated          = fetch_brent_price()
    tides_data    = fetch_worldtides()
    flights_data  = fetch_aerodatabox_flights()

    pages = {
        "index.html":       build_index(RESTAURANTS, HOTELS),
        "nature.html":      build_nature_page(),
        "activities.html":  build_activities_page(),
        "restaurants.html": build_restaurants_page(RESTAURANTS),
        "hotels.html":      build_hotels_page(HOTELS),
        "shopping.html":    build_shopping_page(),
        "services.html":    build_services_page(),
        "currency.html":    build_currency_page(cme_rates, cme_live, cme_updated,
                                                cbvs_rates, cbvs_live, cbvs_updated,
                                                brent_price, brent_updated),
        "conditions.html":  build_conditions_page(tides_data),
        "flights.html":     build_flights_page(flights_data),
        "news.html":        build_news(articles, oil_articles, finance_articles),
        "about.html":       build_about_page(),
        "contact.html":     build_contact_page(),
        "privacy.html":     build_privacy_page(),
        "visitor-guide.html": build_visitor_guide_page(),
        "on-the-road.html":   build_roads_page(),
    }

    for fname, html in pages.items():
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  OK  {fname}")

    import os as _os
    _os.makedirs("listing", exist_ok=True)
    count = 0

    for slug in _BIZ:
        b = _make_biz(slug)
        if not b:
            continue
        html    = build_listing_page(slug, b)
        out_dir = Path("listing") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        count += 1

    nat_slugs = []
    for spot in NATURE_SPOTS:
        slug    = _nature_slug(spot["name"])
        nat_slugs.append(slug)
        html    = build_nature_listing_page(spot, slug)
        out_dir = Path("listing") / slug
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        count += 1

    print(f"  OK  {count} listing pages")

    act_slugs = [b["slug"] for b in ADVENTURES_BIZ + SIGHTSEEING]

    with open("sitemap.xml", "w", encoding="utf-8") as f:
        f.write(build_sitemap(list(_BIZ.keys()), act_slugs, nat_slugs))

    with open("robots.txt", "w", encoding="utf-8") as f:
        f.write(build_robots())

    # PWA files
    with open("manifest.webmanifest", "w", encoding="utf-8") as f:
        f.write(build_manifest())
    print("  OK  manifest.webmanifest")
    with open("sw.js", "w", encoding="utf-8") as f:
        f.write(build_sw())
    print("  OK  sw.js")
    with open("offline.html", "w", encoding="utf-8") as f:
        f.write(build_offline())
    print("  OK  offline.html")
    _generate_pwa_icons()

    print("Done.")
