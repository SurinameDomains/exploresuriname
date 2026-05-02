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
CONTACT_EMAIL  = "surinamedomains@gmail.com"
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

# Load rich descriptions from exploresuriname_listings.json (keyed by slug)
_JSON_DESCS: dict = {}
_jd_path = Path(__file__).parent / "exploresuriname_listings.json"
if _jd_path.exists():
    try:
        for _e in json.loads(_jd_path.read_text(encoding="utf-8")):
            if _e.get("slug") and _e.get("description", "").strip():
                _JSON_DESCS[_e["slug"]] = _e["description"].strip()
        print(f"  Loaded {len(_JSON_DESCS)} rich descriptions from exploresuriname_listings.json")
    except Exception as _err:
        print(f"  Warning: could not load listing descriptions — {_err}")

FEEDS = [
    {"name": "De Ware Tijd", "url": "https://www.dwtonline.com/feed/",              "color": "#2D6A4F"},
    {"name": "Starnieuws",   "url": "https://www.starnieuws.com/rss/starnieuws.rss","color": "#B40A2D"},
    {"name": "Waterkant",    "url": "https://www.waterkant.net/feed/",               "color": "#1a56db"},
]

NATURE_SPOTS = [
    {"name": "Central Suriname Nature Reserve", "badge": "UNESCO World Heritage",
     "desc": "One of the world's largest intact tropical rainforests — 1.6 million pristine hectares where jaguars, tapirs and giant river otters roam free. A global treasure.",
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
     "desc": "An iconic granite dome rising above the endless jungle canopy. Accessible only by multi-day expedition — the ultimate reward for the most adventurous travellers.",
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
     "desc": "Suriname is a birder's paradise — spot 700+ species including scarlet macaws and harpy eagles.",
     "url": "https://surinameholidays.nl/en/birdwatching/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Ara_ararauna_Luc_Viatour.jpg/1280px-Ara_ararauna_Luc_Viatour.jpg"},
    {"icon": "🏘️", "name": "Indigenous Village Tours",
     "desc": "Visit Trio and Wayana indigenous communities in the deep interior, preserving ancient traditions.",
     "url": "https://www.mets-suriname.com/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/5/5c/Wayana%2C_muziek_en_dans%2C_1.PNG"},
    {"icon": "🥁", "name": "Maroon Village Tours",
     "desc": "Experience the living culture of the Saramacca and Matawai Maroon peoples — music, craft and history.",
     "url": "https://allsurinametours.com/en/visit-to-maroon-village-santigron/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/f/f3/Santigron_pleng%2C_African_Culture_in_Suriname.jpg"},
    {"icon": "🏙️", "name": "Paramaribo City Walk",
     "desc": "Explore the UNESCO-listed historic inner city on foot — the only wooden colonial city in the Americas.",
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

# -- Business listings (hardcoded from exploresuriname_listings.json) ---------

_BIZ = {
    '9173': {"name": 'Tulip Supermarkt', "location": 'Paramaribo', "address": 'Tourtonnelaan 133-135, Paramaribo, Suriname', "phone": '+597 521060', "website": 'www.amazoneretail.com'},
    'a-la-john': {"name": 'A La John', "location": 'Paramaribo', "address": 'verlengde gemenelands weg 192, Paramaribo, Suriname', "phone": '+597 715-1821', "website": ''},
    'ac-bar-restaurant': {"name": 'AC bar & restaurant', "location": 'Paramaribo', "address": 'Anamoestraat #53', "phone": '+597 459-394', "website": ''},
    'afobaka-resort': {"name": 'Afobaka Resort', "location": 'Brokopondo', "address": 'Afobaka Resort, Brokopondo, Suriname', "phone": '+597 868-5636', "website": 'afobakaresort.com'},
    'akira-overwater-resort': {"name": 'Akira Overwater Resort', "location": 'Nickerie', "address": 'Wagenwegstraat 24, Paramaribo, Suriname', "phone": '410-700', "website": 'www.akiraoverwaterresort.com/'},
    'baka-foto-restaurant': {"name": 'Baka Foto Restaurant', "location": 'Paramaribo', "address": 'Abraham Crijnssenweg No 1, Paramaribo, Suriname', "phone": '471-819', "website": 'baka-foto.business.site/'},
    'bar-zuid': {"name": 'Bar Zuid', "location": 'Paramaribo', "address": 'Van sommolsdijckstraat 17, Paramaribo, Suriname', "phone": '+597 422-928', "website": ''},
    'bed-bath-more-bbm': {"name": 'Bed Bath & More (BB&M)', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo, Suriname', "phone": '+597 820-7225', "website": 'bbm.sr'},
    'bitdynamics': {"name": 'Bit Dynamics N.V.', "location": 'Paramaribo', "address": 'Heliconstraat #34', "phone": '+597 890-9030', "website": 'bitdynamics.sr'},
    'bloom-wellness-cafe': {"name": 'Bloom Wellness Café', "location": 'Paramaribo', "address": 'Verlengde Gemenelandsweg 163, Paramaribo, Suriname', "phone": '826-5050', "website": ''},
    'bori-tori': {"name": 'Bori Tori', "location": 'Paramaribo', "address": 'Zonnebloemstraat 44, Paramaribo, Suriname', "phone": '+597 439-173', "website": ''},
    'bronbella-villa-residence': {"name": 'Bronbella Villa Residence', "location": 'Paramaribo', "address": 'Menckenbergstraat 45, Paramaribo, Suriname', "phone": '+31 (0) 637501731', "website": 'bronbellavillaresidence.com'},
    'carpe-diem-massagepraktijk': {"name": 'Carpe Diem Massagepraktijk', "location": 'Paramaribo', "address": 'Khadiweg 132', "phone": '+597 895-5187', "website": ''},
    'chi-min': {"name": 'Chi Min', "location": 'Paramaribo', "address": 'Cornelis Jongbawstraat 83, Paramaribo, Suriname', "phone": '+597 412-155', "website": 'www.chimin-restaurant.com'},
    'cola-kreek-recreatiepark': {"name": 'Cola Kreek Recreatiepark', "location": 'Para', "address": 'Colakreek, Zanderij', "phone": '472-621', "website": 'mets.sr/nl/tour/colakreek-recreation-park/'},
    'courtyard-by-marriott': {"name": 'Courtyard by Marriott', "location": 'Paramaribo', "address": 'Anton Dragtenweg 50-54, Paramaribo, Suriname', "phone": '456-000', "website": 'www.marriott.com/en-us/hotels/pbmcy-courtyard-paramaribo/overview/'},
    'de-spot': {"name": 'De Spot', "location": 'Paramaribo', "address": 'Slangenhoutstraat 77, Paramaribo, Suriname', "phone": '+597 850-7376', "website": ''},
    'de-verdieping': {"name": 'De Verdieping', "location": 'Paramaribo', "address": 'Kleine Waterstraat 1', "phone": '+597 840-8613', "website": ''},
    'delete-beauty-lounge': {"name": 'Delete Beauty Lounge', "location": 'Paramaribo', "address": 'Frederikastraat 48A, Paramaribo, Suriname', "phone": '874-6610', "website": 'www.fresha.com/a/delete-paramaribo-afobakalaan-xfdcx98c/booking'},
    'divergent-body-jewelry': {"name": 'Divergent Body Jewelry', "location": 'Paramaribo', "address": 'Parijsstraat 10', "phone": '+597 895-6839', "website": ''},
    'dj-liquor-store': {"name": 'DJ Liquor Store', "location": 'Paramaribo', "address": 'Prins Hendrikstraat 44', "phone": '+597 472-226', "website": ''},
    'dli-travel-consultancy': {"name": 'D-Li Travel & Consultancy', "location": 'Paramaribo', "address": 'Bonistraat 117, Paramaribo', "phone": '+597 850-8710', "website": ''},
    'eaglemedia': {"name": 'EagleMedia', "location": 'Wanica', "address": 'Lashkarweg 85', "phone": '+597 886-4108', "website": ''},
    'ec-operations': {"name": 'EC Operations', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 899-0105', "website": 'ecoperations.godaddysites.com/'},
    'eco-resort-miano': {"name": 'Eco-Resort Miano', "location": 'Para', "address": 'Louis Stugerweg 134', "phone": '+597 875-0593', "website": ''},
    'eco-torarica': {"name": 'Eco Torarica', "location": 'Paramaribo', "address": 'Cornelis Jongbawstraat 16, Paramaribo, Suriname', "phone": '425-522', "website": 'ecotorarica.com/en'},
    'ekay-media': {"name": 'Ekay Media', "location": 'Wanica', "address": 'Soedhoestraat', "phone": '+597 855-9589', "website": ''},
    'el-patron-latin-grill': {"name": 'El Patron Latin Grill', "location": 'Paramaribo', "address": 'Flustraat 25A', "phone": '495-151', "website": ''},
    'elines-pizza': {"name": "Eline's Pizza", "location": 'Paramaribo', "address": 'Birambiestraat 40', "phone": '+597 892-9595', "website": ''},
    'fatum': {"name": 'FATUM Schadeverzekering N.V.', "location": 'Paramaribo', "address": 'Noorderkerkstraat 5-7', "phone": '471-541', "website": ''},
    'fly-allways': {"name": 'Fly AllWays', "location": 'Paramaribo', "address": 'Hoek Coesewijnestraat / Parastraat, Paramaribo, Suriname', "phone": '455645', "website": ''},
    'ford-zeelandia': {"name": 'Fort Zeelandia', "location": 'Paramaribo', "address": 'Abraham Crijnssenweg 1, Paramaribo, Suriname', "phone": '+597 425-871', "website": 'www.surinaamsmuseum.net/'},
    'from-me-to-me': {"name": 'From Me, To Me', "location": 'Paramaribo', "address": 'Toscastraat #3', "phone": '+597 869-5727', "website": ''},
    'galaxy': {"name": 'Galaxy', "location": 'Paramaribo', "address": 'Lala Rookhweg Hermitage Mall, Paramaribo', "phone": '+597 473-580', "website": ''},
    'garden-of-eden': {"name": 'Garden of Eden', "location": 'Paramaribo', "address": 'Virolastraat 61, Paramaribo, Suriname', "phone": '+597 499-448', "website": 'www.gardenofeden.sr'},
    'goe-thai-noodle-bar': {"name": 'GoE Thai Noodle Bar', "location": 'Paramaribo', "address": 'Virolastraat 61, Paramaribo, Suriname', "phone": '714-1214', "website": 'www.goe.sr'},
    'h-garden': {"name": 'H Garden', "location": 'Wanica', "address": 'Leiding 9 #135', "phone": '+597 857-0880', "website": ''},
    'hairstudio-32': {"name": 'Hairstudio 32', "location": 'Paramaribo', "address": 'Bluewingstraat 13', "phone": '+597 880-8794', "website": ''},
    'handmade-by-farrell-nv': {"name": 'Handmade by Farrell N.V.', "location": 'Wanica', "address": 'Ds. Martin Luther Kingweg #532', "phone": '+597 840-8840', "website": ''},
    'hard-rock-cafe-suriname': {"name": 'Hard Rock Cafe Suriname', "location": 'Paramaribo', "address": 'International Mall of Suriname, Paramaribo, Suriname', "phone": '+597 811-0035', "website": ''},
    'hermitage-mall': {"name": 'Hermitage Mall', "location": 'Paramaribo', "address": 'Lala Rookhweg, Paramaribo, Suriname', "phone": '463-295', "website": 'hermitage-mall.com'},
    'het-koto-museum': {"name": 'Het Koto Museum', "location": 'Paramaribo', "address": 'Prinsessestraat 43, Paramaribo, Suriname', "phone": '+597 894-5261', "website": ''},
    'holland-lodge': {"name": 'Holland Lodge', "location": 'Paramaribo', "address": 'Mahonylaan 25, Paramaribo, Suriname', "phone": '+597 520-663', "website": 'hollandlodgeparamaribo.com/'},
    'honeycare': {"name": 'Honeycare', "location": 'Paramaribo', "address": 'Verlengde Gemenelandsweg 119, Paramaribo, Suriname', "phone": '+597 893-9391', "website": ''},
    'hotel-palacio': {"name": 'Hotel Palacio', "location": 'Paramaribo', "address": 'Heerenstraat 9, Paramaribo, Suriname', "phone": '+597 420-064', "website": 'www.hotelpalacio.net/'},
    'hotel-peperpot': {"name": 'Hotel Peperpot', "location": 'Commewijne', "address": 'Plantage Peperpot 1, Nieuw-Meerzorg, Commewijne, Suriname', "phone": '+31 202-152-003', "website": 'www.hotelpeperpot.nl/'},
    'houttuyn-wellness-river-resort': {"name": 'Houttuyn Wellness River Resort', "location": 'Paramaribo', "address": 'Zijstraat Watermuntweg, Paramaribo, Suriname', "phone": '825-2888', "website": 'www.houttuyn.com/'},
    'huub-explorer-tours': {"name": 'Huub Explorer Tours', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 826-4189', "website": 'www.facebook.com/Huubexplorertours/'},
    'ias-wooden-and-construction-nv': {"name": 'IAS Wooden and Construction N.V.', "location": 'Wanica', "address": 'Houttuin, Wanica', "phone": '+597 890-3179', "website": ''},
    'inksane-tattoos': {"name": 'Inksane Tattoos', "location": 'Paramaribo', "address": 'Sohawanweg 30, Nieuw Charlesburg', "phone": '+597 891-3614', "website": ''},
    'international-mall-of-suriname': {"name": 'International Mall of Suriname', "location": 'Paramaribo', "address": 'Ringweg-Zuid 245, Paramaribo, Suriname', "phone": '+597 445-555', "website": ''},
    'jacana-amazon-wellness-resort': {"name": 'Jacana Amazon Wellness Resort', "location": 'Paramaribo', "address": 'Commewijnestraat 35, Zorg en Hoop, Suriname', "phone": '531-000', "website": 'jacanaresort.com/'},
    'joden-savanne': {"name": 'Joden Savanne', "location": 'Para', "address": 'Joden Savanne, Para, Suriname', "phone": '+597 479-272', "website": 'www.jodensavanne.org/'},
    'joey-ds': {"name": "Joey D's", "location": 'Paramaribo', "address": 'Claudiastraat 13, Paramaribo, Suriname', "phone": '+597 878-4878', "website": ''},
    'julias-food': {"name": "Julia's Food", "location": 'Paramaribo', "address": 'verl gemenelandsweg 125', "phone": '847-0189', "website": ''},
    'kasan-snacks': {"name": 'Kasan Snacks', "location": 'Wanica', "address": 'Schotelweg 95', "phone": '+597 857-0950', "website": ''},
    'kirpalani': {"name": 'Kirpalani', "location": 'Paramaribo', "address": 'Maagden-, Dominee- en J.A.Pengelstraat, Paramaribo, Suriname', "phone": '+597 471-400', "website": 'www.kirpalani.com/en/'},
    'klm-royal-dutch-airlines': {"name": 'KLM Royal Dutch Airlines', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+31 20 474 7746', "website": 'www.klm.com/'},
    'knini-paati': {"name": 'Knini Paati', "location": 'Sipaliwini', "address": 'Boven Suriname', "phone": '+597 885-9355', "website": 'www.knini-paati.com/'},
    'kodouffi-tapawatra-resort': {"name": 'Kodouffi Tapawatra Resort', "location": 'Sipaliwini', "address": 'Djoemoe, Sipaliwini, Suriname', "phone": '+597 862-7899', "website": 'tapawatra.nl/'},
    'las-tias': {"name": 'Las Tias', "location": 'Paramaribo', "address": 'Johannesmungrastraat 75, Paramaribo, Suriname', "phone": '434-162', "website": ''},
    'lashlift-suriname': {"name": 'Lashlift Suriname', "location": 'Paramaribo', "address": 'Trefbalstraat', "phone": '+597 859-0353', "website": ''},
    'lilis': {"name": "Lili's", "location": 'Paramaribo', "address": 'Kuldipsinghstraat 21', "phone": '875-7991', "website": 'shoplilis.com'},
    'lioness-beauty-effects': {"name": 'Lioness Beauty Effects', "location": 'Paramaribo', "address": 'Ramlakhanstraat 58', "phone": '864-9076', "website": 'www.fresha.com/nl/a/lioness-beauty-effects-studio-more-paramaribo-zodiacstraat-b4a26fug/booking'},
    'mickis-palace-noord': {"name": "Micki's Palace Noord", "location": 'Paramaribo', "address": 'Hecubastraat 57', "phone": '+597 892-7537', "website": ''},
    'mickis-palace-zuid': {"name": "Micki's Palace Zuid", "location": 'Paramaribo', "address": 'Bindastraat 69, Paramaribo, Suriname', "phone": '+597 857-8181', "website": ''},
    'mingle-paramaribo': {"name": 'Mingle Paramaribo', "location": 'Paramaribo', "address": 'Ringweg-Zuid 245, Paramaribo, Suriname', "phone": '+597 858-9988', "website": 'www.mingleparamaribo.com/'},
    'mokisa-busidataa-osu-nv': {"name": 'Mokisa Busidataa Osu N.V.', "location": 'Paramaribo', "address": 'Dr. Sophie Redmondstraat 231', "phone": '+597 491-900', "website": ''},
    'moments-restaurant': {"name": "Moment's Restaurant", "location": 'Paramaribo', "address": 'Bombaystraat 21a', "phone": '492-917', "website": ''},
    'museum-bakkie': {"name": 'Museum Bakkie', "location": 'Commewijne', "address": 'Plantage Bakkie #6, Reijnsdorp, Suriname', "phone": '+597 865-4130', "website": 'museumbakkie.com/'},
    'nv-threefold-quality-system-support': {"name": 'N.V. Threefold Quality System Support', "location": 'Paramaribo', "address": 'Taspalmstraat 14', "phone": '+597 539-660', "website": ''},
    'nv-zing-manufacturing': {"name": 'N.V. ZING Manufacturing', "location": 'Paramaribo', "address": 'Aquariusstraat 96-98', "phone": '+597 864-9098', "website": ''},
    'oxygen-resort': {"name": 'Oxygen Resort', "location": 'Paramaribo', "address": 'Bombaystraat 21, Paramaribo, Suriname', "phone": '+597 441-819', "website": 'oxygen-resort.com/'},
    'pane-e-vino': {"name": 'Pane E Vino', "location": 'Paramaribo', "address": 'Van Sommelsdijckstraat 19, Paramaribo, Suriname', "phone": '+597 520-423', "website": ''},
    'pannekoek-en-poffertjes-cafe': {"name": 'Pannekoek en Poffertjes Cafe', "location": 'Paramaribo', "address": 'Van Sommelsdijckstraat 11, Paramaribo, Suriname', "phone": '+597 422-914', "website": ''},
    'papillon-crafts': {"name": 'Papillon Crafts', "location": 'Paramaribo', "address": 'Sangrafoestraat 6', "phone": '+597 885-1848', "website": ''},
    'passion-food-and-wines': {"name": 'Passion Food and Wines', "location": 'Paramaribo', "address": 'Kolonistenweg 39, Paramaribo, Suriname', "phone": '840-8613', "website": 'passiefoodandwines.com/passie-food/'},
    'peperpot-nature-park': {"name": 'Peperpot Nature Park', "location": 'Commewijne', "address": 'Hadji Iding Soemitaweg 32, Nieuw Meerzorg, Commewijne, Suriname', "phone": '+597 354-547', "website": 'peperpotnaturepark.com/'},
    'pinkmoon-suriname': {"name": 'Pinkmoon Suriname', "location": 'Paramaribo', "address": 'Johannes Mungrastraat', "phone": '891-3465', "website": ''},
    'plantage-frederiksdorp': {"name": 'Plantage Frederiksdorp', "location": 'Commewijne', "address": 'Frederiksdorp 1, Margrita, Suriname', "phone": '+597 820-0378', "website": 'www.frederiksdorp.com'},
    'readytex-souvenirs-and-crafts': {"name": 'Readytex Souvenirs and Crafts', "location": 'Paramaribo', "address": 'Maagdenstraat 44, Paramaribo, Suriname', "phone": '893-3060', "website": 'www.readytexcrafts.com/'},
    'recreatie-oord-carolina-kreek': {"name": 'Recreatie Oord Carolina Kreek', "location": 'Para', "address": 'Sabakoe, Suriname', "phone": '+597 853-2977', "website": 'www.carolinakreek.com'},
    'rich-skin': {"name": 'Rich Skin', "location": 'Paramaribo', "address": 'Jainarain Sohansinghlaan 43', "phone": '+597 722-1170', "website": ''},
    'rock-fitness-paramaribo': {"name": 'Rock Fitness Paramaribo', "location": 'Paramaribo', "address": 'Ringwegnoord 36, Paramaribo', "phone": '+597 828-0080', "website": ''},
    'rogom-farm-nv': {"name": 'Rogom Farm N.V.', "location": 'Wanica', "address": 'Ds. Martin Luther Kingweg #532', "phone": '+597 888-0105', "website": ''},
    'royal-brasil-hotel': {"name": 'Royal Brasil Hotel', "location": 'Paramaribo', "address": 'William Kemble straat #7, Paramaribo', "phone": '+597 855-5585', "website": 'royalbrasilhotel.com'},
    'royal-breeze-hotel-paramaribo': {"name": 'Royal Breeze Hotel Paramaribo', "location": 'Paramaribo', "address": 'Waterkant 78, Paramaribo, Suriname', "phone": '421-640', "website": ''},
    'royal-rose-yoni-spa': {"name": 'Royal Rose Yoni Spa', "location": 'Paramaribo', "address": 'Blaw Kepankistraat 22, Paramaribo', "phone": '871-1564', "website": 'www.fresha.com/a/royal-rose-yoni-spa-paramaribo-blaw-kepankistraat-22-t8sftqpc'},
    'royal-spa': {"name": 'Royal Spa', "location": 'Paramaribo', "address": 'Toevluchtweg 49, Paramaribo, Suriname', "phone": '+597 892-9621', "website": ''},
    'royal-torarica': {"name": 'Royal Torarica', "location": 'Paramaribo', "address": 'Kleine Waterstraat 10, Paramaribo, Suriname', "phone": '+597 473-500', "website": 'royaltorarica.com/en'},
    'royal-wellness-lounge': {"name": 'Royal Wellness Lounge', "location": 'Paramaribo', "address": 'Commissaris Weythingweg 565A, Paramaribo, Suriname', "phone": '754-7357', "website": ''},
    'seen-stories': {"name": 'Seen Stories', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 821-5175', "website": 'www.seen-stories.com/'},
    'shlx-collection': {"name": 'SHLX Collection', "location": 'Paramaribo', "address": 'Verlengde Gemenlandsweg 164, Paramaribo, Suriname', "phone": '870-2464', "website": 'www.shlx.shop/'},
    'sleeqe': {"name": 'Sleeqe', "location": 'Wanica', "address": 'Kwattaweg 670A', "phone": '+597 869-7141', "website": ''},
    'smoothieskin': {"name": 'SmoothieSkin', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '875-2677', "website": ''},
    'souposo': {"name": 'Souposo', "location": 'Paramaribo', "address": 'Costerstraat 20a, Paramaribo, Suriname', "phone": '+597 420-351', "website": ''},
    'stichting-shiatsu-massage': {"name": 'Stichting Shiatsu Massage', "location": 'Paramaribo', "address": 'Dr. Sophie Redmondstraat 167', "phone": '+597 871-9661', "website": ''},
    'stukaderen-in-nederland': {"name": 'Stukaderen in Nederland', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": 'stukaderenin.nl'},
    'suraniyat': {"name": 'Suraniyat', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 817-3928', "website": 'www.suraniyat.com'},
    'surimami-store': {"name": 'Surimami Store', "location": 'Paramaribo', "address": 'Kleine Waterstraat 1', "phone": '+31 647-750-700', "website": ''},
    'surinam-airways': {"name": 'Surinam Airways', "location": 'Paramaribo', "address": 'Mr. Jagernath Lachmonstraat, Paramaribo, Suriname', "phone": '+597 465-700', "website": 'www.flyslm.com/'},
    'sushi-ya': {"name": 'Sushi-Ya', "location": 'Paramaribo', "address": 'Van Sommelsdijckstraat 21, Paramaribo, Suriname', "phone": '+597 475-450', "website": ''},
    'switi-momenti-candles-crafts': {"name": 'Switi Momenti Candles & Crafts', "location": 'Paramaribo', "address": 'Grote Combeweg / Van Roseveltkade', "phone": '877-3401', "website": ''},
    'talking-prints-concept-store': {"name": 'Talking Prints Concept Store', "location": 'Paramaribo', "address": 'Kleine Waterstraat 1', "phone": '840-8966', "website": 'talkingprints.org'},
    'taman-indah-resort': {"name": 'Taman Indah Resort', "location": 'Commewijne', "address": 'Djojosoepartoweg 140, Tamanredjo', "phone": '+597 356-685', "website": ''},
    'the-beauty-bar': {"name": 'The Beauty Bar', "location": 'Paramaribo', "address": 'Tourtonnelaan 181, Paramaribo, Suriname', "phone": '+597 854-9280', "website": 'beautybar.sr/'},
    'the-coffee-box': {"name": 'The Coffee Box', "location": 'Paramaribo', "address": 'Wilhelminastraat 66-68', "phone": '498-949', "website": ''},
    'the-freelance-scout': {"name": 'The Freelance Scout', "location": 'Paramaribo', "address": 'Ormosiastraat 2A', "phone": '+597 824-2012', "website": ''},
    'the-golden-truly-hotel': {"name": 'The Golden Truly Hotel', "location": 'Paramaribo', "address": 'Jozef Israelstraat, Paramaribo, Suriname', "phone": '+597 454-249', "website": ''},
    'the-house-of-beauty': {"name": 'The House of Beauty', "location": 'Paramaribo', "address": 'Kashmirstraat 164', "phone": '+597 843-3213', "website": ''},
    'the-old-attic': {"name": 'The Old Attic', "location": 'Paramaribo', "address": 'Paterweidmann straat 25', "phone": '846-8841', "website": ''},
    'the-uma-store': {"name": 'The Uma Store', "location": 'Paramaribo', "address": 'Kleine Waterstraat 1, Paramaribo, Suriname', "phone": '+597 861-0540', "website": ''},
    'the-waxing-booth': {"name": 'The Waxing Booth and More by SG', "location": 'Wanica', "address": 'Ramanandproject 2#1, Garnizoenspad', "phone": '+597 815-9594', "website": ''},
    'the-wonderlab-su': {"name": 'The WonderLab Su', "location": 'Paramaribo', "address": 'Louis Goveastraat', "phone": '+597 854-5169', "website": ''},
    'thermen-hermitage-turkish-bath-beautycenter': {"name": 'Thermen Hermitage Turkish Bath & Beautycenter', "location": 'Paramaribo', "address": 'Previenlaan 78, Uitvlugt, Paramaribo, Suriname', "phone": '439-800', "website": ''},
    'timeless-barber-and-nail-shop': {"name": 'Timeless Barber and Nail Shop', "location": 'Paramaribo', "address": 'Jan Besar Sarno Rebostraat #10, Paramaribo, Suriname', "phone": '710-5162', "website": 'timelessbarbershop.sr'},
    'tiny-house-tropical-appartment': {"name": 'Tiny House Tropical Appartment', "location": 'Wanica', "address": 'Grijskwarts straat 10, Domburg', "phone": '+597 769-9407', "website": ''},
    'tio-boto-eco-resort': {"name": 'Tio Boto Eco Resort', "location": 'Sipaliwini', "address": 'Parrijsstraat 10, Paramaribo', "phone": '+597 875-8790', "website": 'www.tioboto.com'},
    'torarica-resort': {"name": 'Torarica Resort', "location": 'Paramaribo', "address": 'Mr. L.J. Rietbergplein 1, Paramaribo, Suriname', "phone": '471-500', "website": 'toraricaresort.com/en'},
    'unlimited-suriname-tours': {"name": 'Unlimited Suriname Tours', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 879-5436', "website": 'www.unlimitedsuriname.com'},
    'unlocked-candles': {"name": 'Unlocked Candles', "location": 'Paramaribo', "address": 'Hk. Hendrik & Orlandostraat #2', "phone": '+597 873-2131', "website": ''},
    'villa-famiri': {"name": 'Villa Famiri', "location": 'Paramaribo', "address": 'Dr. Axwijkstraat 76, Paramaribo', "phone": '450-230', "website": 'www.villafamiri.com/'},
    'waterland-suites': {"name": 'Waterland Suites', "location": 'Paramaribo', "address": 'Waterlandstraat 17, Paramaribo, Suriname', "phone": '+597 530-151', "website": ''},
    'wayfinders-exclusive-n-v': {"name": 'Wayfinders Exclusive N.V.', "location": 'Paramaribo', "address": 'Calcutta straat 82', "phone": '+597 766-4837', "website": ''},
    'woodwonders-suriname': {"name": 'Woodwonders Suriname', "location": 'Commewijne', "address": 'Weg Naar Peperpot 26', "phone": '+597 866-7104', "website": ''},
    'yoga-peetha-happiness-centre': {"name": 'Yoga Peetha Happiness Centre', "location": 'Paramaribo', "address": 'Picassostraat 113', "phone": '+597 855-9779', "website": ''},
    'zeelandia-suites': {"name": 'Zeelandia Suites', "location": 'Paramaribo', "address": 'Kleine Waterstraat 1', "phone": '+597 840-8613', "website": ''},
    'zeepfabriek-joab': {"name": 'Zeepfabriek JOAB', "location": 'Paramaribo', "address": 'Van Roosevelt kade Prasara 1', "phone": '+597 879-7165', "website": ''},
    'zeg-ijsje': {"name": 'Zeg Ijsje', "location": 'Paramaribo', "address": 'Marygoldstraat', "phone": '+597 867-0993', "website": ''},
    'zus-zo-cafe': {"name": 'Zus & Zo Cafe', "location": 'Paramaribo', "address": 'Grote Combeweg 13a, Paramaribo, Suriname', "phone": '+597 520-904', "website": 'www.zusenzosuriname.com/'},
    'de-gadri': {"name": 'De Gadri', "location": 'Paramaribo', "address": 'Zeelandiaweg 1, Paramaribo, Suriname', "phone": '+597 420-688', "website": ''},
    'big-tex': {"name": 'Big Tex', "location": 'Paramaribo', "address": 'Anamoestraat 81, Paramaribo, Suriname', "phone": '+597 815-7161', "website": ''},
    '101-real-estate': {"name": '101 Real Estate', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    '4r-gym': {"name": '4r Gym', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'aaras-cafe': {"name": 'Aaras Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'abrix-cleaning-services': {"name": 'Abrix Cleaning Services', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'access-suriname-travel': {"name": 'Access Suriname Travel', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ace-restaurant-lounge': {"name": 'Ace Restaurant Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'alegria': {"name": 'Alegria', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'alis-drugstore': {"name": 'Alis Drugstore', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'alliance-francaise': {"name": 'Alliance Francaise', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'amada-shopping': {"name": 'Amada Shopping', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'anaula-nature-resort': {"name": 'Anaula Nature Resort', "location": 'Sipaliwini', "address": 'Boven Suriname River', "phone": '', "website": ''},
    'anton-de-kom-universiteit-van-suriname': {"name": 'Anton De Kom Universiteit Van Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-joemmanbaks': {"name": 'Apotheek Joemmanbaks', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-karis': {"name": 'Apotheek Karis', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-mac-donald-north': {"name": 'Apotheek Mac Donald North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-mac-donald-south': {"name": 'Apotheek Mac Donald South', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-rafeka': {"name": 'Apotheek Rafeka', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-sibilo': {"name": 'Apotheek Sibilo', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-soma': {"name": 'Apotheek Soma', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'apotheek-soma-ringweg': {"name": 'Apotheek Soma Ringweg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'arthur-alex-hoogendoorn-atheneum': {"name": 'Arthur Alex Hoogendoorn Atheneum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ashley-furniture-homestore': {"name": 'Ashley Furniture HomeStore', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'assuria-hermitage-high-rise': {"name": 'Assuria Hermitage High Rise', "location": 'Paramaribo', "address": 'Lala Rookhweg, Paramaribo', "phone": '', "website": 'www.assuria.sr'},
    'assuria-insurance-walk-in-city': {"name": 'Assuria Walk-in City', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": ''},
    'assuria-insurance-walk-in-commewijne': {"name": 'Assuria Walk-in Commewijne', "location": 'Commewijne', "address": 'Commewijne, Suriname', "phone": '', "website": ''},
    'assuria-insurance-walk-in-lelydorp': {"name": 'Assuria Walk-in Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'assuria-insurance-walk-in-nickerie': {"name": 'Assuria Walk-in Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'assuria-insurance-walk-in-noord': {"name": 'Assuria Walk-in Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'atlantis-hotel-casino': {"name": 'Atlantis Hotel Casino', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'augis-travel': {"name": 'Augis Travel', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'auto-style-franchepanestraat': {"name": 'Auto Style Franchepanestraat', "location": 'Paramaribo', "address": 'Franchepanestraat, Paramaribo', "phone": '', "website": ''},
    'auto-style-johannes-mungrastraat': {"name": 'Auto Style Johannes Mungrastraat', "location": 'Paramaribo', "address": 'Johannes Mungrastraat, Paramaribo', "phone": '', "website": ''},
    'auto-style-kwatta': {"name": 'Auto Style Kwatta', "location": 'Paramaribo', "address": 'Kwatta, Paramaribo', "phone": '', "website": ''},
    'auto-style-tweede-rijweg': {"name": 'Auto Style Tweede Rijweg', "location": 'Paramaribo', "address": 'Tweede Rijweg, Paramaribo', "phone": '', "website": ''},
    'auto-style-verlengde-gemenelandsweg': {"name": 'Auto Style Verlengde Gemenelandsweg', "location": 'Paramaribo', "address": 'Verlengde Gemenelandsweg, Paramaribo', "phone": '', "website": ''},
    'ayo-river-lounge': {"name": 'Ayo River Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ayur-mi-beauty-wellness': {"name": 'Ayur Mi Beauty Wellness', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'balance-studio': {"name": 'Balance Studio', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'balletschool-marlene': {"name": 'Balletschool Marlene', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bar-qle': {"name": 'Bar Qle', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bella-italia': {"name": 'Bella Italia', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'best-mart': {"name": 'Best Mart', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'beyrouth-bazaar': {"name": 'Beyrouth Bazaar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bingo-pizza-coppename': {"name": 'Bingo Pizza Coppename', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bingo-pizza-kwatta': {"name": 'Bingo Pizza Kwatta', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bistro-brwni': {"name": 'Bistro Brwni', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bistro-don-julio': {"name": 'Bistro Don Julio', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bistro-lequatorze': {"name": 'Bistro Lequatorze', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'blissful-massage-aromatherapy': {"name": 'Blissful Massage Aromatherapy', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'blossom-beauty-bar': {"name": 'Blossom Beauty Bar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'blue-grand-cafe': {"name": 'Blue Grand Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bmw-suriname': {"name": 'BMW Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'body-enhancement-gym': {"name": 'Body Enhancement Gym', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'boekhandel-vaco': {"name": 'Boekhandel Vaco', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'boss-burgers': {"name": 'Boss Burgers', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brahma-centrum': {"name": 'Brahma Centrum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brahma-noord': {"name": 'Brahma Noord', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brahma-zuid': {"name": 'Brahma Zuid', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'bright-cleaning': {"name": 'Bright Cleaning', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brilleman': {"name": 'Brilleman', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brotherhood-security': {"name": 'Brotherhood Security', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'brow-bliss-lounge': {"name": 'Brow Bliss Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'building-depot': {"name": 'Building Depot', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'burger-king-centrum': {"name": 'Burger King Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": ''},
    'burger-king-latour': {"name": 'Burger King Latour', "location": 'Paramaribo', "address": 'Latour, Paramaribo', "phone": '', "website": ''},
    'buro-workspaces': {"name": 'Buro Workspaces', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'byd-suriname': {"name": 'BYD Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'camex-suriname': {"name": 'Camex Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'car-rental-city': {"name": 'Car Rental City', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'carline-kwatta': {"name": 'Carline Kwatta', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'carline-waaldijkstraat': {"name": 'Carline Waaldijkstraat', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'carvision-paramaribo': {"name": 'Carvision Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chees-jewelry-watches': {"name": 'Chees Jewelry Watches', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chique-eyewear-fashion': {"name": 'Chique Eyewear Fashion', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-centrum': {"name": 'CHM Centrum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-commewijne': {"name": 'CHM Commewijne', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-kernkampweg': {"name": 'CHM Kernkampweg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-nickerie': {"name": 'CHM Nickerie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-wanica': {"name": 'CHM Wanica', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-wilhelminastraat': {"name": 'CHM Wilhelminastraat', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chm-wilhelminastraat-2': {"name": 'CHM Wilhelminastraat 2', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'chois-supermarkt': {"name": 'Chois Supermarkt', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'chois-supermarkt-lelydorp': {"name": 'Chois Supermarkt Lelydorp', "location": 'Wanica', "address": 'Lelydorp', "phone": '', "website": ''},
    'chois-supermarkt-north': {"name": 'Chois Supermarkt Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'chuck-e-cheese': {"name": 'Chuck E Cheese', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cinnagirl': {"name": 'Cinnagirl', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ciranos': {"name": 'Ciranos', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'clarissa-vaseur-writing-wellness-services-claw': {"name": 'Clarissa Vaseur Writing Wellness Services Claw', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'clean-it': {"name": 'Clean It', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'clevia-park': {"name": 'Clevia Park', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'club-oase': {"name": 'Club Oase', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'coffee-mama': {"name": 'Coffee Mama', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'combe-bazaar': {"name": 'Combe Bazaar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'combe-markt': {"name": 'Combe Markt', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'computer-hardware-services': {"name": 'Computer Hardware Services', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'computronics-north': {"name": 'Computronics Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'computronics-south': {"name": 'Computronics Zuid', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'conservatorium-suriname': {"name": 'Conservatorium Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cookie-closet': {"name": 'Cookie Closet', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'courtyard-marriott': {"name": 'Courtyard Marriott', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cpr-pilates-curves': {"name": 'Cpr Pilates Curves', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'creative-q': {"name": 'Creative Q', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'crocs-ims': {"name": 'Crocs IMS', "location": 'Paramaribo', "address": 'International Mall of Suriname', "phone": '', "website": ''},
    'cupcake-fantasy': {"name": 'Cupcake Fantasy', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'curl-babes': {"name": 'Curl Babes', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cute-as-a-button': {"name": 'Cute As a Button', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cy-coffee': {"name": 'Cy Coffee', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'cynsational-glam': {"name": 'Cynsational Glam', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'd-mighty-view-lounge': {"name": 'D Mighty View Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-drogisterij-coppename': {"name": 'DA Drogisterij Coppename', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-drogisterij-hermitage': {"name": 'DA Drogisterij Hermitage', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-drogisterij-ims-mall': {"name": 'DA Drogisterij IMS Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-drogisterij-lelydorp': {"name": 'DA Drogisterij Lelydorp', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-drogisterij-wilhelmina': {"name": 'DA Drogisterij Wilhelmina', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'da-select-en-service-apotheek': {"name": 'DA Select En Service Apotheek', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'danpaati-river-lodge': {"name": 'Danpaati River Lodge', "location": 'Sipaliwini', "address": 'Boven Suriname River', "phone": '', "website": 'www.danpaati.com'},
    'dansclub-danzson': {"name": 'Dansclub Danzson', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dcars-rental': {"name": 'Dcars Rental', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'de-cederboom-school': {"name": 'De Cederboom School', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'de-keurslager-interfarm': {"name": 'De Keurslager Interfarm', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'de-nederlandse-basisschool-het-kleurenorkest': {"name": 'De Nederlandse Basisschool Het Kleurenorkest', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'de-spetter': {"name": 'De Spetter', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'de-surinaamsche-bank-hermitage-mall': {"name": 'DSB Hermitage Mall', "location": 'Paramaribo', "address": 'Lala Rookhweg, Paramaribo', "phone": '', "website": 'www.dsb.sr'},
    'de-surinaamsche-bank-hoofdkantoor': {"name": 'DSB Hoofdkantoor', "location": 'Paramaribo', "address": 'Henck Arronstraat 45, Paramaribo', "phone": '', "website": ''},
    'de-surinaamsche-bank-lelydorp': {"name": 'DSB Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'de-surinaamsche-bank-ma-retraite': {"name": 'DSB Ma Retraite', "location": 'Paramaribo', "address": 'Ma Retraite, Paramaribo', "phone": '', "website": ''},
    'de-surinaamsche-bank-ma-retraite-2': {"name": 'DSB Ma Retraite (2)', "location": 'Paramaribo', "address": 'Ma Retraite, Paramaribo', "phone": '', "website": ''},
    'de-surinaamsche-bank-nickerie': {"name": 'DSB Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'de-surinaamsche-bank-nickerie-2': {"name": 'DSB Nickerie (2)', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'de-surinaamsche-bank-nieuwe-haven': {"name": 'DSB Nieuwe Haven', "location": 'Paramaribo', "address": 'Nieuwe Haven, Paramaribo', "phone": '', "website": ''},
    'de-vrije-school': {"name": 'De Vrije School', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'deto-handelmaatschappij': {"name": 'Deto Handelmaatschappij', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'dhl-express-service-point': {"name": 'DHL Express Service Point', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dierenarts-resopawiro': {"name": 'Dierenarts Resopawiro', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dierenartspraktijk-l-m-bansse-issa': {"name": 'Dierenartspraktijk L M Bansse Issa', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dierenpoli-lobo': {"name": 'Dierenpoli Lobo', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'digicel-albina': {"name": 'Digicel Albina', "location": 'Marowijne', "address": 'Albina, Marowijne', "phone": '', "website": 'www.digicel.sr'},
    'digicel-business-center': {"name": 'Digicel Business Center', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'digicel-extacy': {"name": 'Digicel Extacy', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'digicel-hermitage': {"name": 'Digicel Hermitage', "location": 'Paramaribo', "address": 'Lala Rookhweg, Paramaribo', "phone": '', "website": ''},
    'digicel-latour': {"name": 'Digicel Latour', "location": 'Paramaribo', "address": 'Latour, Paramaribo', "phone": '', "website": ''},
    'digicel-lelydorp': {"name": 'Digicel Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'digicel-nickerie': {"name": 'Digicel Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'digicel-wilhelminastraat': {"name": 'Digicel Wilhelminastraat', "location": 'Paramaribo', "address": 'Wilhelminastraat, Paramaribo', "phone": '', "website": ''},
    'digital-world-hermitage-mall': {"name": 'Digital World Hermitage Mall', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo', "phone": '', "website": ''},
    'digital-world-ims': {"name": 'Digital World IMS', "location": 'Paramaribo', "address": 'International Mall of Suriname', "phone": '', "website": ''},
    'digital-world-maretraite-mall': {"name": 'Digital World Ma Retraite Mall', "location": 'Paramaribo', "address": 'Ma Retraite, Paramaribo', "phone": '', "website": ''},
    'digital-world-maretraite-mall-2': {"name": 'Digital World Ma Retraite Mall (2)', "location": 'Paramaribo', "address": 'Ma Retraite, Paramaribo', "phone": '', "website": ''},
    'djinipi-copy-center': {"name": 'Djinipi Copy Center', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'djo-cleaning-service': {"name": 'Djo Cleaning Service', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dlish': {"name": 'Dlish', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dojo-couture-centrum': {"name": 'Dojo Couture Centrum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dojo-couture-hermitage-mall': {"name": 'Dojo Couture Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dojo-couture-ims': {"name": 'Dojo Couture IMS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dolce-bella-cafe': {"name": 'Dolce Bella Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dor-property-management-services-n-v': {"name": 'Dor Property Management Services N V', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dream-clean-suriname': {"name": 'Dream Clean Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'dresscode': {"name": 'Dresscode', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'eethuis-liv': {"name": 'Eethuis Liv', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'energiebedrijven-suriname-ebs': {"name": 'Energiebedrijven Suriname EBS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'etembe-rainforest-restaurant': {"name": 'Etembe Rainforest Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'eterno': {"name": 'Eterno', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ettores-pizza-kitchen': {"name": 'Ettores Pizza Kitchen', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'eucon': {"name": 'Eucon', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'everything-sr': {"name": 'Everything SR', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'faraya-medical-center': {"name": 'Faraya Medical Center', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'farma-vida': {"name": 'Farma Vida', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'fatum-schadeverzekering-commewijne': {"name": 'FATUM Commewijne', "location": 'Commewijne', "address": 'Commewijne, Suriname', "phone": '', "website": ''},
    'fatum-schadeverzekering-hoofdkantoor': {"name": 'FATUM Hoofdkantoor', "location": 'Paramaribo', "address": 'Noorderkerkstraat 5-7, Paramaribo', "phone": '', "website": ''},
    'fatum-schadeverzekering-kwatta': {"name": 'FATUM Kwatta', "location": 'Paramaribo', "address": 'Kwatta, Paramaribo', "phone": '', "website": ''},
    'fatum-schadeverzekering-nickerie': {"name": 'FATUM Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'fhr-lim-a-po-institute-for-higher-education': {"name": 'FHR Lim a Po Institute For Higher Education', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'finabank-centrum': {"name": 'Finabank Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": 'www.finabank.sr'},
    'finabank-nickerie': {"name": 'Finabank Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'finabank-noord': {"name": 'Finabank Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'finabank-wanica': {"name": 'Finabank Wanica', "location": 'Wanica', "address": 'Wanica, Suriname', "phone": '', "website": ''},
    'finabank-zuid': {"name": 'Finabank Zuid', "location": 'Paramaribo', "address": 'Zuid, Paramaribo', "phone": '', "website": ''},
    'first-aid-plus': {"name": 'First Aid Plus', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'fish-finder-fishing-and-outdoors': {"name": 'Fish Finder Fishing & Outdoors', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'fit-factory': {"name": 'Fit Factory', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'flavor-restaurant': {"name": 'Flavor Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'flex-luxuries': {"name": 'Flex Luxuries', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'flex-phones': {"name": 'Flex Phones', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'fluxo-pilates': {"name": 'Fluxo Pilates', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'folo-nature-tours': {"name": 'Folo Nature Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'footcandy-hermitage-mall': {"name": 'Footcandy Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'free-city-walk-paramaribo': {"name": 'Free City Walk Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'free-flow': {"name": 'Free Flow', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'from-kay-with-love': {"name": 'From Kay With Love', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'frygri': {"name": 'Frygri', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'furniture-city-kwatta': {"name": 'Furniture City Kwatta', "location": 'Paramaribo', "address": 'Kwatta, Paramaribo', "phone": '', "website": ''},
    'furniture-city-north': {"name": 'Furniture City Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'gaby-april-beauty-clinic': {"name": 'Gaby April Beauty Clinic', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'galaxyliving': {"name": 'Galaxyliving', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'gao-ming-trading-north': {"name": 'Gao Ming Trading North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'gao-ming-trading-south': {"name": 'Gao Ming Trading South', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'garage-d-a-ashruf': {"name": 'Garage D a Ashruf', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'georgies-bar-chill': {"name": 'Georgies Bar Chill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'glam-curves': {"name": 'Glam Curves', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'glambox': {"name": 'Glambox', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'goldenwings': {"name": 'Goldenwings', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'golderom-healthy-organic-store': {"name": 'Golderom Healthy Organic Store', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'golf-club-paramaribo': {"name": 'Golf Club Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'gossip-nails-xx': {"name": 'Gossip Nails Xx', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'great-wall-motor-suriname': {"name": 'Great Wall Motor Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'greenheart-boutique-hotel': {"name": 'Greenheart Boutique Hotel', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'grounded-botanical-studio': {"name": 'Grounded Botanical Studio', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'guesthouse-albergoalberga': {"name": 'Guesthouse Albergo Alberga', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'guesthouse-albina': {"name": 'Guesthouse Albina', "location": 'Marowijne', "address": 'Albina, Marowijne', "phone": '', "website": ''},
    'h-t': {"name": 'H&T', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'habco-delight': {"name": 'Habco Delight', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'habco-delight-north': {"name": 'Habco Delight North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hakrinbank': {"name": 'Hakrinbank Hoofdkantoor', "location": 'Paramaribo', "address": 'Dr. Sophie Redmondstraat, Paramaribo', "phone": '', "website": 'www.hakrinbank.com'},
    'hakrinbank-flora': {"name": 'Hakrinbank Flora', "location": 'Paramaribo', "address": 'Flora, Paramaribo', "phone": '', "website": ''},
    'hakrinbank-latour': {"name": 'Hakrinbank Latour', "location": 'Paramaribo', "address": 'Latour, Paramaribo', "phone": '', "website": ''},
    'hakrinbank-nickerie': {"name": 'Hakrinbank Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'hakrinbank-nieuwe-haven': {"name": 'Hakrinbank Nieuwe Haven', "location": 'Paramaribo', "address": 'Nieuwe Haven, Paramaribo', "phone": '', "website": ''},
    'hakrinbank-tamanredjo': {"name": 'Hakrinbank Tamanredjo', "location": 'Commewijne', "address": 'Tamanredjo, Commewijne', "phone": '', "website": ''},
    'hakrinbank-tourtonne': {"name": 'Hakrinbank Tourtonne', "location": 'Paramaribo', "address": 'Tourtonnelaan, Paramaribo', "phone": '', "website": ''},
    'han-palace': {"name": 'Han Palace', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'happy-flower-services': {"name": 'Happy Flower Services', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'harry-tjin': {"name": 'Harry Tjin', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hertz-suriname-car-rental': {"name": 'Hertz Suriname Car Rental', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hes-ds': {"name": 'HES DS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hes-ds-2': {"name": 'HES DS 2', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hes-ds-3': {"name": 'HES DS 3', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'holiday-home-decor': {"name": 'Holiday Home Decor', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hollandia-bakkerij-north': {"name": 'Hollandia Bakkerij Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'hollandia-bakkerij-south': {"name": 'Hollandia Bakkerij Zuid', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'holy-moly': {"name": 'Holy Moly', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'honeycare-north': {"name": 'Honeycare North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'honeycare-south': {"name": 'Honeycare South', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hotel-north-resort': {"name": 'Hotel North Resort', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'house-of-pureness': {"name": 'House Of Pureness', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hsds-lifestyle-noord': {"name": 'Hsds Lifestyle Noord', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'hsds-lifestyle-wanica': {"name": 'Hsds Lifestyle Wanica', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'iamchede': {"name": 'Iamchede', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'infinity-holding': {"name": 'Infinity Holding', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'instyle-optics': {"name": 'Instyle Optics', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'international-academy-of-suriname': {"name": 'International Academy Of Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'intervast': {"name": 'Intervast', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'invictus-brazilian-jiu-jitsu': {"name": 'Invictus Brazilian Jiu Jitsu', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'itrendzz': {"name": 'Itrendzz', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jack-tours-travel-service': {"name": 'Jack Tours & Travel Service', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'jadore-cafe-grill': {"name": 'Jadore Cafe Grill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jage-caffe': {"name": 'Jage Caffe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jage-caffe-2': {"name": 'Jage Caffe 2', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jamilas-dry-cleaning-north': {"name": 'Jamilas Dry Cleaning North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jamilas-dry-cleaning-south': {"name": 'Jamilas Dry Cleaning South', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'janelles-shoes-and-bags': {"name": 'Janelles Shoes & Bags', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'jenny-tours': {"name": 'Jenny Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'jjs-place-zuid': {"name": 'Jjs Place Zuid', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'joosje-roti-shop': {"name": 'Joosje Roti Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'just-curlss': {"name": 'Just Curlss', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kabalebo-nature-resort': {"name": 'Kabalebo Nature Resort', "location": 'Sipaliwini', "address": 'Kabalebo, Suriname', "phone": '', "website": 'www.kabalebo.com'},
    'kaizen': {"name": 'Kaizen', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kaki-supermarkt': {"name": 'Kaki Supermarkt', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'karans-indian-food': {"name": 'Karans Indian Food', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kasimex-indira-ghandiweg': {"name": 'Kasimex Indira Ghandiweg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kasimex-makro': {"name": 'Kasimex Makro', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'keller-williams-suriname': {"name": 'Keller Williams Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kempes-co': {"name": 'Kempes Co.', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ket-mien': {"name": 'Ket Mien', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kfc-ims': {"name": 'KFC IMS', "location": 'Paramaribo', "address": 'International Mall of Suriname, Paramaribo', "phone": '', "website": ''},
    'kfc-kwatta': {"name": 'KFC Kwatta', "location": 'Paramaribo', "address": 'Kwatta, Paramaribo', "phone": '', "website": ''},
    'kfc-lallarookh': {"name": 'KFC Lallarookh', "location": 'Paramaribo', "address": 'Lallarookh, Paramaribo', "phone": '', "website": ''},
    'kfc-latour': {"name": 'KFC Latour', "location": 'Paramaribo', "address": 'Latour, Paramaribo', "phone": '', "website": ''},
    'kfc-lelydorp': {"name": 'KFC Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'kfc-waterkant': {"name": 'KFC Waterkant', "location": 'Paramaribo', "address": 'Waterkant, Paramaribo', "phone": '', "website": ''},
    'kfc-wilhelminastraat': {"name": 'KFC Wilhelminastraat', "location": 'Paramaribo', "address": 'Wilhelminastraat, Paramaribo', "phone": '', "website": ''},
    'kimboto': {"name": 'Kimboto Lodge', "location": 'Sipaliwini', "address": 'Brokopondo, Suriname', "phone": '', "website": ''},
    'kirpalani-domineestraat': {"name": 'Kirpalani Domineestraat', "location": 'Paramaribo', "address": 'Domineestraat, Paramaribo', "phone": '', "website": ''},
    'kirpalani-maagdenstraat': {"name": 'Kirpalani Maagdenstraat', "location": 'Paramaribo', "address": 'Maagdenstraat, Paramaribo', "phone": '', "website": ''},
    'kirpalani-super-store': {"name": 'Kirpalani Super Store', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'kong-nam-snack': {"name": 'Kong Nam Snack', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'krioro': {"name": 'Krioro', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'krioro-north': {"name": 'Krioro North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kushiyaki-the-next-episode': {"name": 'Kushiyaki The Next Episode', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kwan-tai-restaurant': {"name": 'Kwan Tai Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kwan-tai-restaurant-2': {"name": 'Kwan Tai Restaurant 2', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'kyu-pho-grill': {"name": 'Kyu Pho Grill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ladybug-nursery-and-garden-center': {"name": 'Ladybug Nursery & Garden Center', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'lamour-restaurant': {"name": 'Lamour Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'le-den': {"name": 'Le Den', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'lees-korean-grill': {"name": 'Lees Korean Grill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'leiding-1-restaurant': {"name": 'Leiding 1 Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'lins-super-market': {"name": 'Lin\'s Super Market', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'lobby': {"name": 'Lobby', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'lucky-store': {"name": 'Lucky Store', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'lucky-twins-restaurant': {"name": 'Lucky Twins Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'luxe-escape-lotus-spa-wellness-beautysalon': {"name": 'Luxe Escape Lotus Spa Wellness Beautysalon', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'maharaja-palace': {"name": 'Maharaja Palace', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mandy-butka': {"name": 'Mandy Butka', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'marchand-notariaat': {"name": 'Marchand Notariaat', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'marina-resort-waterland': {"name": 'Marina Resort Waterland', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'matcha-loft': {"name": 'Matcha Loft', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'max-n-co': {"name": 'Max N Co.', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'maze': {"name": 'Maze', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mcdonalds-centrum': {"name": 'McDonald\'s Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": ''},
    'mcdonalds-hermitage-mall': {"name": 'McDonald\'s Hermitage Mall', "location": 'Paramaribo', "address": 'Lala Rookhweg, Paramaribo', "phone": '', "website": ''},
    'messias-tours': {"name": 'Messias Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'mezze-suriname': {"name": 'Mezze Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mighty-racks': {"name": 'Mighty Racks', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mimi-market': {"name": 'Mimi Market', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'mingle-sushi': {"name": 'Mingle Sushi', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mini-nail-shop': {"name": 'Mini Nail Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'miniso-gompertstraat': {"name": 'Miniso Gompertstraat', "location": 'Paramaribo', "address": 'Gompertstraat, Paramaribo', "phone": '', "website": ''},
    'miniso-hermitage-mall': {"name": 'Miniso Hermitage Mall', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo', "phone": '', "website": ''},
    'mirage-casino': {"name": 'Mirage Casino', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'miss-doll-fit': {"name": 'Miss Doll Fit', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mn-international-centrum': {"name": 'MN International Centrum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mn-international-kwatta': {"name": 'MN International Kwatta', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'moka-coffeebar': {"name": 'Moka Coffeebar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mokisa-wellness': {"name": 'Mokisa Wellness', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mon-plaisir-nursery': {"name": 'Mon Plaisir Nursery', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'mondowa-tours': {"name": 'Mondowa Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'morevans-outlet': {"name": 'Morevans Outlet', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'multi-travel': {"name": 'Multi Travel', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'muntjes-take-out-juniors-place': {"name": 'Muntjes Take Out Juniors Place', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'murphys-irish-pub': {"name": 'Murphys Irish Pub', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'naskip': {"name": 'Naskip Henck Arronstraat', "location": 'Paramaribo', "address": 'Henck Arronstraat 46b, Paramaribo', "phone": '+597 475-419', "website": 'naskip.com'},
    'naskip-2': {"name": 'Naskip Latourweg', "location": 'Paramaribo', "address": 'Latourweg 10, Paramaribo', "phone": '+597 481-555', "website": 'naskip.com'},
    'naskip-3': {"name": 'Naskip Gemenelandsweg', "location": 'Paramaribo', "address": 'Verlengde Gemenelandsweg, Paramaribo', "phone": '', "website": 'naskip.com'},
    'naskip-4': {"name": 'Naskip Kwatta', "location": 'Paramaribo', "address": 'Hoek Kwattaweg & Van Idsingastraat, Paramaribo', "phone": '', "website": 'naskip.com'},
    'naskip-5': {"name": 'Naskip Indira Ghandiweg', "location": 'Paramaribo', "address": 'Hoek Indira Ghandiweg & Schotelweg, Paramaribo', "phone": '', "website": 'naskip.com'},
    'nassy-brouwer-college': {"name": 'Nassy Brouwer College', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'nassy-brouwer-school': {"name": 'Nassy Brouwer School', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'new-choice-lalla-rookhweg': {"name": 'New Choice Lalla Rookhweg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'new-choice-nickerie': {"name": 'New Choice Nickerie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'new-choice-ringweg': {"name": 'New Choice Ringweg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'new-suriname-dream-cafe': {"name": 'New Suriname Dream Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'no-span-eco-tours': {"name": 'No Span Eco Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'norrii-zushii': {"name": 'Norrii Zushii', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'north-fitness-gym': {"name": 'North Fitness Gym', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'notariaat-mannes': {"name": 'Notariaat Mannes', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'notariaat-van-dijk': {"name": 'Notariaat Van Dijk', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'nr-1-spot': {"name": 'Nr 1 Spot', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'numa-cafe': {"name": 'Numa Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'oasis-restaurant': {"name": 'Oasis Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ochama-amazing': {"name": 'Ochama Amazing', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'ochama-hermitage-mall': {"name": 'Ochama Hermitage Mall', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo', "phone": '', "website": ''},
    'office-world-hermitage-mall': {"name": 'Office World Hermitage Mall', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo', "phone": '', "website": ''},
    'office-world-lelydorp': {"name": 'Office World Lelydorp', "location": 'Wanica', "address": 'Lelydorp', "phone": '', "website": ''},
    'ogi-teppanyaki-sushi-bar': {"name": 'Ogi Teppanyaki Sushi Bar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'okido-tours-travel': {"name": 'Okido Tours & Travel', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'okopipi-tropical-grill': {"name": 'Okopipi Tropical Grill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'olive-multi-cuisine-restaurant': {"name": 'Olive Multi Cuisine Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ondernemershuis': {"name": 'Ondernemershuis', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'one-stop-apotheek-drugstore': {"name": 'One Stop Apotheek Drugstore', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-all-vision': {"name": 'Optiek All Vision', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-all-vision-albina': {"name": 'Optiek All Vision Albina', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-all-vision-lelydorp': {"name": 'Optiek All Vision Lelydorp', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-all-vision-nickerie': {"name": 'Optiek All Vision Nickerie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-marisa': {"name": 'Optiek Marisa', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon': {"name": 'Optiek Ninon', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon-hermitage-mall': {"name": 'Optiek Ninon Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon-ims': {"name": 'Optiek Ninon IMS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon-lelydorp': {"name": 'Optiek Ninon Lelydorp', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon-meerzorg': {"name": 'Optiek Ninon Meerzorg', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'optiek-ninon-nickerie': {"name": 'Optiek Ninon Nickerie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'orchid': {"name": 'Orchid', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'organic-skincare': {"name": 'Organic Skincare', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'outdoor-living': {"name": 'Outdoor Living', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'overbridge-river-resort': {"name": 'Overbridge River Resort', "location": 'Para', "address": 'Para, Suriname', "phone": '', "website": ''},
    'overdoughsed-suriname': {"name": 'Overdoughsed Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'padel-x-suriname': {"name": 'Padel X Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'padre-nostro-italian-restaurant': {"name": 'Padre Nostro Italian Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'pandie': {"name": 'Pandie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'paramaribo-princess-casino': {"name": 'Paramaribo Princess Casino', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'paramaribo-zoo': {"name": 'Paramaribo Zoo', "location": 'Paramaribo', "address": 'Paramaribo Zoological Garden, Paramaribo', "phone": '', "website": ''},
    'percy-massage-therapy': {"name": 'Percy Massage Therapy', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'petisco-restaurant': {"name": 'Petisco Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'petit-bouchon': {"name": 'Petit Bouchon', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'pineapple-tours': {"name": 'Pineapple Tours', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'pitbull-fitness': {"name": 'Pitbull Fitness', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'pizza-hut-leysweg': {"name": 'Pizza Hut Leysweg', "location": 'Paramaribo', "address": 'Leysweg, Paramaribo', "phone": '', "website": ''},
    'pizza-hut-south': {"name": 'Pizza Hut South', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'pizza-hut-wilhelminastraat': {"name": 'Pizza Hut Wilhelminastraat', "location": 'Paramaribo', "address": 'Wilhelminastraat, Paramaribo', "phone": '', "website": ''},
    'pizza-mafia': {"name": 'Pizza Mafia', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'popeyes-centrum': {"name": 'Popeyes Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": ''},
    'popeyes-lelydorp': {"name": 'Popeyes Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'popeyes-tbl': {"name": 'Popeyes TBL', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'popeyes-wilhelminastraat': {"name": 'Popeyes Wilhelminastraat', "location": 'Paramaribo', "address": 'Wilhelminastraat, Paramaribo', "phone": '', "website": ''},
    'professional-private-security': {"name": 'Professional Private Security', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'protrade-international': {"name": 'Protrade International', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'qsi-international-school-of-suriname': {"name": 'QSI International School Of Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'r-k-bisdom-paramaribo': {"name": 'R K Bisdom Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'radisson-hotel': {"name": 'Radisson Hotel Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": 'www.radissonhotels.com'},
    'raja-ji': {"name": 'Raja Ji', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ramada-paramaribo-princess': {"name": 'Ramada Paramaribo Princess', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'randoe-meubelen': {"name": 'Randoe Meubelen', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    're-max-suriname': {"name": 'Re Max Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'readytex-art-gallery': {"name": 'Readytex Art Gallery', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'real-one-fitness-gym': {"name": 'Real One Fitness Gym', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'red-century-party-shop-commewijne': {"name": 'Red Century Party Shop Commewijne', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'red-century-party-shop-kwatta': {"name": 'Red Century Party Shop Kwatta', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'red-century-party-shop-lelydorp': {"name": 'Red Century Party Shop Lelydorp', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'red-century-party-shop-north': {"name": 'Red Century Party Shop North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'red-century-party-shop-zorg-en-hoop': {"name": 'Red Century Party Shop Zorg En Hoop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'remy-vastgoed': {"name": 'Remy Vastgoed', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'republic-bank-head-office': {"name": 'Republic Bank Head Office', "location": 'Paramaribo', "address": 'Henck Arronstraat, Paramaribo', "phone": '', "website": 'www.republicbanktt.com'},
    'republic-bank-jozef-israelstraat': {"name": 'Republic Bank Jozef Israelstraat', "location": 'Paramaribo', "address": 'Jozef Israelstraat, Paramaribo', "phone": '', "website": ''},
    'republic-bank-kernkampweg': {"name": 'Republic Bank Kernkampweg', "location": 'Paramaribo', "address": 'Kernkampweg, Paramaribo', "phone": '', "website": ''},
    'republic-bank-nickerie': {"name": 'Republic Bank Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'republic-bank-vant-hogerhuysstraat': {"name": 'Republic Bank Van\'t Hogerhuysstraat', "location": 'Paramaribo', "address": 'Van\'t Hogerhuysstraat, Paramaribo', "phone": '', "website": ''},
    'republic-bank-zorg-en-hoop': {"name": 'Republic Bank Zorg en Hoop', "location": 'Paramaribo', "address": 'Zorg en Hoop, Paramaribo', "phone": '', "website": ''},
    'residence-inn-nickerie': {"name": 'Residence Inn Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'residence-inn-paramaribo': {"name": 'Residence Inn Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'resourceful-real-estate-construction': {"name": 'Resourceful Real Estate Construction', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'restaurant-lhermitage': {"name": 'Restaurant Lhermitage', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'restaurant-sarinah': {"name": 'Restaurant Sarinah', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'restoran-bibit': {"name": 'Restoran Bibit', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ricos-a-gladiator-foodtruck': {"name": 'Ricos a Gladiator Foodtruck', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'rif-cleaning-service': {"name": 'Rif Cleaning Service', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ring-ring-imports': {"name": 'Ring Ring Imports', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'ritas-roti-shop': {"name": 'Ritas Roti Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'rolines-de-waag': {"name": 'Rolines De Waag', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'roopram-roti-shop': {"name": 'Roopram Roti Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ross-rental-cars': {"name": 'Ross Rental Cars', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'rossignol-2go-kwattaweg': {"name": 'Rossignol 2GO Kwattaweg', "location": 'Paramaribo', "address": 'Kwattaweg, Paramaribo', "phone": '', "website": ''},
    'rossignol-2go-thurkowstraat': {"name": 'Rossignol 2GO Thurkowstraat', "location": 'Paramaribo', "address": 'Thurkowstraat, Paramaribo', "phone": '', "website": ''},
    'rossignol-coppename': {"name": 'Rossignol Coppename', "location": 'Paramaribo', "address": 'Coppename, Paramaribo', "phone": '', "website": ''},
    'rossignol-geyersvlijt': {"name": 'Rossignol Geyersvlijt', "location": 'Paramaribo', "address": 'Geyersvlijt, Paramaribo', "phone": '', "website": ''},
    'rossignol-linda': {"name": 'Rossignol Linda', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'rossignol-waaldijkstraat': {"name": 'Rossignol Waaldijkstraat', "location": 'Paramaribo', "address": 'Waaldijkstraat, Paramaribo', "phone": '', "website": ''},
    'royal-tours-suriname-guyana': {"name": 'Royal Tours Suriname Guyana', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'safety-first-quality-always': {"name": 'Safety First Quality Always', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sakura': {"name": 'Sakura', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'samba-cafe': {"name": 'Samba Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sanousch-books': {"name": 'Sanousch Books', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'saras-brunch-cafe': {"name": 'Saras Brunch Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sash-fashion-hermitage-mall': {"name": 'Sash Fashion Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'satyam-holidays': {"name": 'Satyam Holidays', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'savage-den': {"name": 'Savage Den', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'savannah-casino-hotel': {"name": 'Savannah Casino Hotel', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'scene-beauty-salon': {"name": 'Scene Beauty Salon', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'secas': {"name": 'Secas', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sendang-redjo': {"name": 'Sendang Redjo', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'shimmery-beauty-lounge': {"name": 'Shimmery Beauty Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'shoebizz-ims': {"name": 'Shoebizz IMS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sizzler-midnight-grill': {"name": 'Sizzler Midnight Grill', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sizzlers-signature': {"name": 'Sizzlers Signature', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'slagerij-abbas': {"name": 'Slagerij Abbas', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'slagerij-asruf': {"name": 'Slagerij Asruf', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'slagerij-stolk': {"name": 'Slagerij Stolk', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sleepstore-suriname': {"name": 'Sleepstore Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'smart-connexxionz': {"name": 'Smart Connexxionz', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'soengngie-mega-store': {"name": 'Soengngie Mega Store', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'soengngie-oriental-market': {"name": 'Soengngie Oriental Market', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'south-america-hot-pot': {"name": 'South America Hot Pot', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'southern-commercial-bank': {"name": 'Southern Commercial Bank N.V.', "location": 'Paramaribo', "address": 'Henck Arronstraat, Paramaribo', "phone": '+597 471-100', "website": 'www.scombank.sr'},
    'spice-quest': {"name": 'Spice Quest', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'squeaky-clean': {"name": 'Squeaky Clean', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'squeezy-hot-pot-restaurant': {"name": 'Squeezy Hot Pot Restaurant', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sranan-fowru': {"name": 'Sranan Fowru', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-boni': {"name": 'Sranan Fowru Boni', "location": 'Paramaribo', "address": 'Boni, Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-combe': {"name": 'Sranan Fowru Combe', "location": 'Paramaribo', "address": 'Combe, Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-flu': {"name": 'Sranan Fowru Flu', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-leiding': {"name": 'Sranan Fowru Leiding', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-lelydorp': {"name": 'Sranan Fowru Lelydorp', "location": 'Wanica', "address": 'Lelydorp', "phone": '', "website": ''},
    'sranan-fowru-meursweg': {"name": 'Sranan Fowru Meursweg', "location": 'Paramaribo', "address": 'Meursweg, Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-tabiki-fowru': {"name": 'Sranan Fowru Tabiki Fowru', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-tourtonne': {"name": 'Sranan Fowru Tourtonne', "location": 'Paramaribo', "address": 'Tourtonnelaan, Paramaribo', "phone": '', "website": ''},
    'sranan-fowru-zinnia': {"name": 'Sranan Fowru Zinnia', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'steps-domineestraat': {"name": 'Steps Domineestraat', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'steps-hermitage-mall': {"name": 'Steps Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'steps-noord': {"name": 'Steps Noord', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'steps-wanica': {"name": 'Steps Wanica', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sthephany-skincare': {"name": 'Sthephany Skincare', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'stichting-surinaams-museum': {"name": 'Stichting Surinaams Museum', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'store4u': {"name": 'Store4u', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'subway': {"name": 'Subway', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'subway-2': {"name": 'Subway (2)', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'subway-3': {"name": 'Subway (3)', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'sugar': {"name": 'Sugar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sun-ice': {"name": 'Sun Ice', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'supply-solutions-limited-suriname': {"name": 'Supply Solutions Limited Suriname', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'suran-adventures-tours-travel': {"name": 'Suran Adventures Tours & Travel', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'surgoed-makelaardij': {"name": 'Surgoed Makelaardij', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'surinaamsche-waterleiding-maatschappij': {"name": 'Surinaamsche Waterleiding Maatschappij', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'suriname-princess-casino': {"name": 'Suriname Princess Casino', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sweet-tooth-pastries': {"name": 'Sweet Tooth Pastries', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sweetheart-hermitage-mall': {"name": 'Sweetheart Hermitage Mall', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sweetheart-ims': {"name": 'Sweetheart IMS', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'sweetie-coffee': {"name": 'Sweetie Coffee', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'talula': {"name": 'Talula', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tapauku-terras': {"name": 'Tapauku Terras', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tastelicious': {"name": 'Tastelicious', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tasty-fresh-food-coffee-bar': {"name": 'Tasty Fresh Food Coffee Bar', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tbl-cinemas': {"name": 'TBL Cinemas', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'teasee': {"name": 'Teasee', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'telesur-centrum': {"name": 'Telesur Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": 'www.telesur.sr'},
    'telesur-latour': {"name": 'Telesur Latour', "location": 'Paramaribo', "address": 'Latour, Paramaribo', "phone": '', "website": ''},
    'telesur-lelydorp': {"name": 'Telesur Lelydorp', "location": 'Wanica', "address": 'Lelydorp, Wanica', "phone": '', "website": ''},
    'telesur-nickerie': {"name": 'Telesur Nickerie', "location": 'Nickerie', "address": 'Nickerie, Suriname', "phone": '', "website": ''},
    'telesur-noord': {"name": 'Telesur Noord', "location": 'Paramaribo', "address": 'Noord, Paramaribo', "phone": '', "website": ''},
    'telesur-zonnebloemstraat': {"name": 'Telesur Zonnebloemstraat', "location": 'Paramaribo', "address": 'Zonnebloemstraat, Paramaribo', "phone": '', "website": ''},
    'the-aerial-yoga-studio': {"name": 'The Aerial Yoga Studio', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-bakery-house': {"name": 'The Bakery House', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-basement-barbershop': {"name": 'The Basement Barbershop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-beauty-bar-north': {"name": 'The Beauty Bar North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-beauty-bar-south': {"name": 'The Beauty Bar South', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-coffee-box-north': {"name": 'The Coffee Box North', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-coffee-hobbyist': {"name": 'The Coffee Hobbyist', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-girl-house': {"name": 'The Girl House', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-laundry-spot': {"name": 'The Laundry Spot', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-maillard-cafe': {"name": 'The Maillard Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-nail-house': {"name": 'The Nail House', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-old-garage': {"name": 'The Old Garage', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-perfume-spot': {"name": 'The Perfume Spot', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-rose-manor': {"name": 'The Rose Manor', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-solution-property-management': {"name": 'The Solution Property Management', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-sweetest-thing': {"name": 'The Sweetest Thing', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'the-warehouse-shop': {"name": 'The Warehouse Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'theater-thalia': {"name": 'Theater Thalia', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'three-little-beans': {"name": 'Three Little Beans', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tianyou-aquafun': {"name": 'Tianyou Aquafun', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tipsy-bar-lounge': {"name": 'Tipsy Bar Lounge', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tirzahs-patisserie': {"name": 'Tirzahs Patisserie', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tomahawk-outdoor-adventures': {"name": 'Tomahawk Outdoor Adventures', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'tomahawk-outdoor-adventures-hermitage-mall': {"name": 'Tomahawk Outdoor Adventures Hermitage', "location": 'Paramaribo', "address": 'Hermitage Mall, Paramaribo', "phone": '', "website": ''},
    'tomahawk-outdoor-adventures-ims': {"name": 'Tomahawk Outdoor Adventures IMS', "location": 'Paramaribo', "address": 'IMS, Paramaribo', "phone": '', "website": ''},
    'tomahawk-outdoor-adventures-lelydorp': {"name": 'Tomahawk Outdoor Adventures Lelydorp', "location": 'Wanica', "address": 'Lelydorp', "phone": '', "website": ''},
    'topslager-stolk': {"name": 'Topslager Stolk', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'topsport': {"name": 'Topsport', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tori-oso': {"name": 'Tori Oso', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'touch-of-heaven-wellness': {"name": 'Touch Of Heaven Wellness', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tout-tout-petit': {"name": 'Tout Tout Petit', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'toys-n-more': {"name": 'Toys N More', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tranquil-at-mamba-republiek': {"name": 'Tranquil At Mamba Republiek', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tranquil-massage': {"name": 'Tranquil Massage', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tropicana-hotel-casino-suriname': {"name": 'Tropicana Hotel Casino', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'tsw-group': {"name": 'Tsw Group', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'tucan-resort-and-spa': {"name": 'Tucan Resort and Spa', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'tulip-supermarket': {"name": 'Tulip Supermarket', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'twins-pizza-burgers': {"name": 'Twins Pizza Burgers', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'typing-nomad-nv': {"name": 'Typing Nomad N.V.', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'u-s-bakery': {"name": 'U S Bakery', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'uitkijk-riverlounge-cafe': {"name": 'Uitkijk Riverlounge Cafe', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'vcm-slagerij-centrum': {"name": 'VCM Slagerij Centrum', "location": 'Paramaribo', "address": 'Centrum, Paramaribo', "phone": '', "website": ''},
    'vcm-slagerij-johannes-mungrastraat': {"name": 'VCM Slagerij Johannes Mungrastraat', "location": 'Paramaribo', "address": 'Johannes Mungrastraat, Paramaribo', "phone": '', "website": ''},
    'vcm-slagerij-verl-gemenelandsweg': {"name": 'VCM Slagerij Verlengde Gemenelandsweg', "location": 'Paramaribo', "address": 'Verlengde Gemenelandsweg, Paramaribo', "phone": '', "website": ''},
    'vifa-trading': {"name": 'Vifa Trading', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'villa-zapakara': {"name": 'Villa Zapakara', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'villas-paramaribo': {"name": 'Villas Paramaribo', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'vincent-supermarket': {"name": 'Vincent Supermarket', "location": 'Paramaribo', "address": 'Paramaribo', "phone": '', "website": ''},
    'viva-mexico': {"name": 'Viva Mexico', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'waldos-worldwide-travel-service': {"name": 'Waldos Worldwide Travel Service', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'warung-resa-centrum': {"name": 'Warung Resa Centrum', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'warung-soepy-ann': {"name": 'Warung Soepy Ann', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'welink-real-estate': {"name": 'Welink Real Estate', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'wing-hung-cake-shop': {"name": 'Wing Hung Cake Shop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'wollys': {"name": 'Wollys', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'wollys-2': {"name": 'Wollys 2', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'wollys-3': {"name": 'Wollys 3', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'wow-plus': {"name": 'Wow Plus', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'x-avenue': {"name": 'X Avenue', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'ying-hao-beautyshop': {"name": 'Ying Hao Beautyshop', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'yogh-hospitality': {"name": 'Yogh Hospitality', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'yokohama-trading': {"name": 'Yokohama Trading', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'young-engineers': {"name": 'Young Engineers', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
    'zenobia-bottling-company': {"name": 'Zenobia Bottling Company', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '', "website": ''},
}

def _biz_url(b):
    import re as _re
    w = b.get('website', '')
    if w and _re.match(r'^(https?://|www\.)[^\s@+]{4,}\.[a-z]{2,}', w, _re.I):
        return ('https://' + w) if not w.startswith('http') else w
    return f"https://www.google.com/search?q={urllib.parse.quote(b['name'] + ' Suriname')}"

_IMGS = {
    # ── Hotels: official website photos ─────────────────────────────────────
    "villa-famiri":                   "https://www.villafamiri.com/wp-content/uploads/2023/04/FF6E67AF-3FEA-4518-A212-432AC27DB0C3_1_201_a-1-605x465.jpeg",
    "hotel-peperpot":                 "https://hotelpeperpot.nl/wp-content/uploads/2024/02/66e837d5-13a7-4712-8766-fc69fcc52b4c-scaled.jpg",
    "bronbella-villa-residence":      "https://bronbellavillaresidence.com/wp-content/uploads/2024/08/Bronbella_website-7-1024x683.jpg",
    "eco-torarica":                   "https://ecotorarica.com/uploads/images/page/original/whatsapp-image-2026-03-22-at-10-05-24.jpeg",
    "royal-torarica":                 "https://royaltorarica.com/uploads/images/page/original/orchid(1).jpg",
    "houttuyn-wellness-river-resort": "https://www.houttuyn.com/wp-content/uploads/2020/08/Nature.jpg",
    "jacana-amazon-wellness-resort":  "https://jacanaresort.com/wp-content/uploads/2023/05/Slide-1.jpg",
    "oxygen-resort":                  "https://oxygen-resort.com/wp-content/uploads/2022/07/slide-1.jpg",
    "royal-brasil-hotel":             "https://royalbrasilhotel.com/wp-content/uploads/2022/07/building-side-1.jpg",
    # Hotels: Unsplash fallbacks for those without accessible official photos
    "courtyard-by-marriott":          "https://cache.marriott.com/content/dam/marriott-renditions/PBMCY/pbmcy-pool-0043-hor-wide.jpg",
    "eco-resort-miano":               "https://mianoecoresort.wordpress.com/wp-content/uploads/2025/09/05bab-1755531893645.jpg",
    "holland-lodge":                  "https://www.hollandlodge.nl/wp-content/uploads/2020/07/Holland-1.jpg",
    "hotel-palacio":                  "https://irp.cdn-website.com/b0c3c22b/dms3rep/multi/Palacio-exterior-street.jpg",
    "torarica-resort":                "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/The_Torarica_-_Paramaribo%2C_Suriname.jpg/1280px-The_Torarica_-_Paramaribo%2C_Suriname.jpg",
    "royal-breeze-hotel-paramaribo": "https://royalbreezeparamaribo.com/wp-content/uploads/2022/12/Royal-breeze-HOR-logo.png",
    "taman-indah-resort": "https://tamanindah.com/wp-content/uploads/2026/04/6307398004_8088be063f_o_4000x2200-1024x563.jpg",
    "tiny-house-tropical-appartment": "",
    "waterland-suites":               "https://waterlandsuites.com/wp-content/uploads/2021/08/20210729_171148-1.jpg",
    "zeelandia-suites":               "https://www.zeelandiasuites.sr/wp-content/uploads/2018/07/balcony-view.png",
    "the-golden-truly-hotel": "",
    # ── Restaurants: official website photos ─────────────────────────────────
    "zus-zo-cafe":                    "https://www.zusenzosuriname.com/wp-content/uploads/2025/12/IMG_0310-scaled.jpeg",
    "goe-thai-noodle-bar":            "https://www.goe.sr/wp-content/uploads/2020/07/home-700-inter.png",
    # Restaurants: Unsplash fallbacks
    "a-la-john": "",
    "ac-bar-restaurant": "",
    "baka-foto-restaurant": "",
    "bar-zuid": "",
    "bori-tori": "",
    "chi-min": "",
    "de-spot":                        "https://de-spot.com/media/frontpage/frontpage.jpg",
    "de-verdieping": "",
    "el-patron-latin-grill":          "https://elpatronlatingrill.com/wp-content/uploads/2024/09/EPLG-1-scaled.jpg",
    "elines-pizza": "",
    "hard-rock-cafe-suriname":        "https://ims.sr/wp-content/uploads/2023/07/food-hard-rock.jpg",
    "joey-ds": "",
    "kasan-snacks": "",
    "las-tias": "",
    "mickis-palace-noord": "",
    "mickis-palace-zuid": "",
    "mingle-paramaribo": "https://ims.sr/wp-content/uploads/2025/02/Logo-Mingle-Cocktail-Lounge_gold-1024x1024.png",
    "moments-restaurant": "",
    "pane-e-vino": "",
    "pannekoek-en-poffertjes-cafe": "",
    "passion-food-and-wines":         "https://impro.usercontent.one/appid/hostnetWsb/domain/passiefoodandwines.com/media/passiefoodandwines.com/onewebmedia/picture-120044.jpg?etag=undefined&sourceContentType=image%2Fjpeg&quality=85",
    "rogom-farm-nv": "",
    "souposo": "",
    "sushi-ya": "",
    "the-coffee-box": "",
    "zeg-ijsje": "",
    "julias-food": "",
    # ── Sightseeing: official / Wikimedia ────────────────────────────────────
    "ford-zeelandia":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Fort_Zeelandia.jpg/1280px-Fort_Zeelandia.jpg",
    "joden-savanne":                  "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cd/Jodensavanne.jpg/1280px-Jodensavanne.jpg",
    "cola-kreek-recreatiepark":       "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg",
    "peperpot-nature-park":           "https://images.squarespace-cdn.com/content/v1/5d52bcc2f6730e0001fe9d75/1649371470790-ED2SMLZ2QP4VLM1WUFJ3/Peperpot+Drone8.jpg",
    "het-koto-museum":                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Koto_Museum%2C_5.jpg/1280px-Koto_Museum%2C_5.jpg",
    "plantage-frederiksdorp":         "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg",
    "museum-bakkie":                  "https://museumbakkie.com/wp-content/uploads/2022/02/museum-bakkie-sluis.jpg",
    # ── Adventures / tour operators ──────────────────────────────────────────
    "unlimited-suriname-tours":       "https://unlimitedsuriname.com/wp-content/uploads/2025/04/d3621001-7e23-426f-9ff7-d5256c918cfd.jpg",
    "afobaka-resort":                 "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Brokopondo_Meer_Viewpiont_%284%29.jpg/1280px-Brokopondo_Meer_Viewpiont_%284%29.jpg",
    "akira-overwater-resort":         "https://www.akiraoverwaterresort.com/wp-content/uploads/2019/01/drone-foto-Akira-resort.jpg",
    "tio-boto-eco-resort":            "https://www.tioboto.com/wp-content/uploads/2019/02/TBE25-1840x1200.jpg",
    # ── Shopping: official photos ─────────────────────────────────────────────
    "hermitage-mall":                 "https://hermitage-mall.com/wp-content/uploads/2018/03/HermitageMall-building.jpg",
    "lilis":                          "https://cdn.shopify.com/s/files/1/0526/9137/0149/files/Bridal_2a85f0ad-2db8-4a8a-ac54-3e090625d4de.jpg",
    "suraniyat":                      "https://images.squarespace-cdn.com/content/v1/65207f08df58fe10d1fab14f/20be6ae2-e0a4-4f62-a609-dcb80ea7e0ef/IMG_0922.jpg",
    "readytex-souvenirs-and-crafts":  "https://www.readytexcrafts.com/wp-content/uploads/2021/03/sigaar.jpg",
    "kirpalani":                      "https://www.kirpalani.com/media/wysiwyg/2026/Subcatmaart2026/Electonica.webp",
    "international-mall-of-suriname": "https://ims.sr/wp-content/uploads/2025/08/IMG_7285.jpg",
    "papillon-crafts": "",
    "woodwonders-suriname": "",
    "switi-momenti-candles-crafts": "https://ims.sr/wp-content/uploads/2025/04/switi-momenti-1024x634.jpg",
    "talking-prints-concept-store": "https://cdn.shopify.com/s/files/1/0114/3016/6587/files/Talkingprints_NewLogo_Final-01_b4c93b19-4415-42a8-8458-e58ede2cb7d4.jpg",
    "dj-liquor-store": "",
    "from-me-to-me": "",
    "galaxy": "https://ims.sr/wp-content/uploads/2023/07/Galaxy-logo-zwart-1024x837.png",
    "divergent-body-jewelry": "",
    "unlocked-candles": "",
    "the-uma-store": "",
    "the-old-attic": "",
    "bed-bath-more-bbm": "https://ims.sr/wp-content/uploads/2024/01/BBM-LOGO-2-1024x724.png",
    "sleeqe": "",
    "smoothieskin": "",
    "honeycare": "https://www.honeycaresu.com/wp-content/uploads/2024/02/HC_Cat_Thumb2.jpg",
    "shlx-collection": "https://shlx.shop/wp-content/uploads/2022/01/maillogo.png",
    # ── Services: official / contextual photos ────────────────────────────────
    "timeless-barber-and-nail-shop":  "https://timelessbarbershop.sr/wp-content/uploads/2025/02/IMG_1731-768x1024.jpg",
    "seen-stories":                   "https://images.squarespace-cdn.com/content/v1/67d096a1ab6b7b756d0e779b/eb825299-fae9-4c65-9309-cbc5ca4d4bcc/Shell+docu+1.png",
    "surinam-airways":                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg/1280px-PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg",
    "klm-royal-dutch-airlines":       "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg/1280px-KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg",
    "fly-allways":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg/1280px-Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg",
    "rock-fitness-paramaribo": "",
    "yoga-peetha-happiness-centre": "",
    "carpe-diem-massagepraktijk": "",
    "stichting-shiatsu-massage": "",
    "royal-spa": "",
    "royal-wellness-lounge": "",
    "the-beauty-bar":                 "https://beautybar.sr/wp-content/uploads/2025/08/Heading-8-e1755791215726.webp",
    "delete-beauty-lounge": "",
    "hairstudio-32": "",
    "lashlift-suriname": "",
    "lioness-beauty-effects": "",
    "royal-rose-yoni-spa": "",
    "thermen-hermitage-turkish-bath-beautycenter": "",
    "inksane-tattoos": "",
    "bitdynamics":                    "https://bitdynamics.sr/wp-content/uploads/2024/08/hero-banner.webp",
    "eaglemedia": "",
    "ekay-media": "",
    "bloom-wellness-cafe": "",
    "dli-travel-consultancy": "",
    "fatum": "",
    "rich-skin":                      "https://richskinsu.com/wp-content/uploads/2025/03/Asset-2_5.png",
    "pinkmoon-suriname": "",
    "the-house-of-beauty": "",
    "the-waxing-booth": "",
    "the-wonderlab-su": "",
    "honeycare":                      "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=800&q=80",
    "mokisa-busidataa-osu-nv": "",
    "handmade-by-farrell-nv": "",
    "ias-wooden-and-construction-nv": "",
    "ec-operations": "",
    "nv-threefold-quality-system-support": "",
    "surimami-store": "",
    "huub-explorer-tours": "",
    "wayfinders-exclusive-n-v": "",
    "recreatie-oord-carolina-kreek": "",
    "knini-paati":                    "https://www.knini-paati.com/wp-content/uploads/eco-vakantie-suriname.jpg",
    "101-real-estate": "",
    "4r-gym": "",
    "aaras-cafe": "",
    "abrix-cleaning-services": "",
    "access-suriname-travel": "",
    "ace-restaurant-lounge": "",
    "alegria": "",
    "alis-drugstore": "",
    "alliance-francaise": "",
    "amada-shopping": "",
    "anaula-nature-resort": "https://upload.wikimedia.org/wikipedia/commons/3/35/Anaula_Nature_Resort_%2814406614971%29.jpg",
    "anton-de-kom-universiteit-van-suriname": "https://www.uvs.edu/wp-content/uploads/2017/12/STM_2770.jpg",
    "apotheek-joemmanbaks": "",
    "apotheek-karis": "",
    "apotheek-mac-donald-north": "",
    "apotheek-mac-donald-south": "",
    "apotheek-rafeka": "",
    "apotheek-sibilo": "",
    "apotheek-soma": "",
    "apotheek-soma-ringweg": "",
    "arthur-alex-hoogendoorn-atheneum": "",
    "ashley-furniture-homestore": "https://www.ashleyfurniture.com/_appnext/immutable/assets/ogimage.DgfO7h4b.webp",
    "assuria-hermitage-high-rise": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "assuria-insurance-walk-in-city": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "assuria-insurance-walk-in-commewijne": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "assuria-insurance-walk-in-lelydorp": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "assuria-insurance-walk-in-nickerie": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "assuria-insurance-walk-in-noord": "https://www.assuria.sr/assets/globals/highrise.jpg",
    "atlantis-hotel-casino": "https://ak-d.tripcdn.com/images/220k12000000tb7oy527E_R_960_660_R5_D.jpg",
    "augis-travel": "",
    "auto-style-franchepanestraat": "https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png",
    "auto-style-johannes-mungrastraat": "https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png",
    "auto-style-kwatta": "https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png",
    "auto-style-tweede-rijweg": "https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png",
    "auto-style-verlengde-gemenelandsweg": "https://autostylenv.com/wp-content/uploads/2023/03/services_center_image_autostylenv.png",
    "ayo-river-lounge": "",
    "ayur-mi-beauty-wellness": "",
    "balance-studio": "",
    "balletschool-marlene": "",
    "bar-qle": "",
    "bella-italia": "",
    "best-mart": "",
    "beyrouth-bazaar": "",
    "bingo-pizza-coppename": "https://www.bingopizza.sr/wp-content/uploads/2024/04/Americana-2022_06_18-19_57_12-UTC-600x600.jpg",
    "bingo-pizza-kwatta": "https://www.bingopizza.sr/wp-content/uploads/2024/04/Americana-2022_06_18-19_57_12-UTC-600x600.jpg",
    "bistro-brwni": "",
    "bistro-don-julio": "",
    "bistro-lequatorze": "",
    "blissful-massage-aromatherapy": "",
    "blossom-beauty-bar": "",
    "blue-grand-cafe": "",
    "bmw-suriname": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/BMW_dealership_Ann_Street%2C_Brisbane.JPG/1280px-BMW_dealership_Ann_Street%2C_Brisbane.JPG",
    "body-enhancement-gym": "",
    "boekhandel-vaco": "",
    "boss-burgers": "",
    "brahma-centrum": "",
    "brahma-noord": "",
    "brahma-zuid": "",
    "bright-cleaning": "",
    "brilleman": "",
    "brotherhood-security": "",
    "brow-bliss-lounge": "",
    "building-depot": "",
    "burger-king-centrum": "https://upload.wikimedia.org/wikipedia/commons/7/76/Burger_king_Suriname_voorin.jpg",
    "burger-king-latour":  "https://upload.wikimedia.org/wikipedia/commons/7/76/Burger_king_Suriname_voorin.jpg",
    "buro-workspaces": "",
    "byd-suriname": "",
    "camex-suriname": "",
    "car-rental-city": "",
    "carline-kwatta": "",
    "carline-waaldijkstraat": "",
    "carvision-paramaribo": "",
    "chees-jewelry-watches": "",
    "chique-eyewear-fashion": "",
    "chm-centrum": "",
    "chm-commewijne": "",
    "chm-kernkampweg": "",
    "chm-nickerie": "",
    "chm-wanica": "",
    "chm-wilhelminastraat": "",
    "chm-wilhelminastraat-2": "",
    "chois-supermarkt": "",
    "chois-supermarkt-lelydorp": "",
    "chois-supermarkt-north": "",
    "chuck-e-cheese": "https://upload.wikimedia.org/wikipedia/commons/2/2d/Chuck_E_Cheese%27s_Pizza_%28crop%29.jpg",
    "cinnagirl": "",
    "ciranos": "",
    "clarissa-vaseur-writing-wellness-services-claw": "",
    "clean-it": "",
    "clevia-park": "https://cleviapark.sr/wp-content/uploads/2024/01/Hengelen-en-bootje-varen-bij-Clevia-Park.jpg",
    "club-oase": "https://www.cluboase.sr/wp-content/uploads/2023/02/OASE-web.jpg",
    "coffee-mama": "",
    "combe-bazaar": "",
    "combe-markt": "",
    "computer-hardware-services": "",
    "computronics-north": "https://computronics.sr/skin/frontend/base/default/images/logo-new01.jpg",
    "computronics-south": "https://computronics.sr/skin/frontend/base/default/images/logo-new01.jpg",
    "conservatorium-suriname": "",
    "cookie-closet": "",
    "courtyard-marriott": "https://upload.wikimedia.org/wikipedia/commons/3/34/Courtyard_by_Marriott_logo.svg",
    "cpr-pilates-curves": "",
    "creative-q": "",
    "crocs-ims": "https://ims.sr/wp-content/uploads/2023/08/Crocs.png",
    "cupcake-fantasy": "",
    "curl-babes": "",
    "cute-as-a-button": "https://ims.sr/wp-content/uploads/2023/09/Cute-as-a-button-logo-nieuw-design.png",
    "cy-coffee": "",
    "cynsational-glam": "",
    "d-mighty-view-lounge": "",
    "da-drogisterij-coppename": "https://ims.sr/wp-content/uploads/2024/01/DA_logo.png",
    "da-drogisterij-hermitage": "https://ims.sr/wp-content/uploads/2024/01/DA_logo.png",
    "da-drogisterij-ims-mall": "https://ims.sr/wp-content/uploads/2024/01/DA_logo.png",
    "da-drogisterij-lelydorp": "https://ims.sr/wp-content/uploads/2024/01/DA_logo.png",
    "da-drogisterij-wilhelmina": "https://ims.sr/wp-content/uploads/2024/01/DA_logo.png",
    "da-select-en-service-apotheek": "",
    "danpaati-river-lodge": "https://www.orangesuriname.com/wp-content/uploads/2023/12/Danpaati-orange-suriname-lodge-view-1.png",
    "dansclub-danzson": "",
    "dcars-rental": "",
    "de-cederboom-school": "",
    "de-keurslager-interfarm": "",
    "de-nederlandse-basisschool-het-kleurenorkest": "",
    "de-spetter": "",
    "de-surinaamsche-bank-hermitage-mall": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-hoofdkantoor": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-lelydorp": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-ma-retraite": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-ma-retraite-2": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-nickerie": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-nickerie-2": "https://www.dsb.sr/assets/og-dsb.png",
    "de-surinaamsche-bank-nieuwe-haven": "https://www.dsb.sr/assets/og-dsb.png",
    "de-vrije-school": "",
    "deto-handelmaatschappij": "",
    "dhl-express-service-point": "",
    "dierenarts-resopawiro": "",
    "dierenartspraktijk-l-m-bansse-issa": "",
    "dierenpoli-lobo": "",
    "digicel-albina": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-business-center": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-extacy": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-hermitage": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-latour": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-lelydorp": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-nickerie": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digicel-wilhelminastraat": "https://upload.wikimedia.org/wikipedia/commons/4/49/Digicel_logo.svg",
    "digital-world-hermitage-mall": "https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315",
    "digital-world-ims": "https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315",
    "digital-world-maretraite-mall": "https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315",
    "digital-world-maretraite-mall-2": "https://cmsdigitalworld.b-cdn.net/assets/a0b4f195-fab0-4eca-a0f3-bd980e1c3fe4/OG%20Image.png?cache=20240315",
    "djinipi-copy-center": "",
    "djo-cleaning-service": "",
    "dlish": "",
    "dojo-couture-centrum": "https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg",
    "dojo-couture-hermitage-mall": "https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg",
    "dojo-couture-ims": "https://ims.sr/wp-content/uploads/2024/01/DOJO.jpg",
    "dolce-bella-cafe": "",
    "dor-property-management-services-n-v": "",
    "dream-clean-suriname": "",
    "dresscode": "",
    "eethuis-liv": "",
    "energiebedrijven-suriname-ebs": "",
    "etembe-rainforest-restaurant": "",
    "eterno": "",
    "ettores-pizza-kitchen": "",
    "eucon": "",
    "everything-sr": "",
    "faraya-medical-center": "",
    "farma-vida": "",
    "fatum-schadeverzekering-commewijne": "",
    "fatum-schadeverzekering-hoofdkantoor": "",
    "fatum-schadeverzekering-kwatta": "",
    "fatum-schadeverzekering-nickerie": "",
    "fhr-lim-a-po-institute-for-higher-education": "",
    "finabank-centrum": "https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg",
    "finabank-nickerie": "https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg",
    "finabank-noord": "https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg",
    "finabank-wanica": "https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg",
    "finabank-zuid": "https://www.finabanknv.com/media/199735/finabank_1920x450_website_banner.jpg",
    "first-aid-plus": "",
    "fish-finder-fishing-and-outdoors": "",
    "fit-factory": "",
    "flavor-restaurant": "",
    "flex-luxuries": "",
    "flex-phones": "",
    "fluxo-pilates": "",
    "folo-nature-tours": "",
    "footcandy-hermitage-mall": "",
    "free-city-walk-paramaribo": "",
    "free-flow": "",
    "from-kay-with-love": "",
    "frygri": "",
    "furniture-city-kwatta": "",
    "furniture-city-north": "",
    "gaby-april-beauty-clinic": "",
    "galaxyliving": "",
    "gao-ming-trading-north": "",
    "gao-ming-trading-south": "",
    "garage-d-a-ashruf": "",
    "georgies-bar-chill": "",
    "glam-curves": "",
    "glambox": "",
    "goldenwings": "",
    "golderom-healthy-organic-store": "",
    "golf-club-paramaribo": "",
    "gossip-nails-xx": "",
    "great-wall-motor-suriname": "",
    "greenheart-boutique-hotel": "https://www.greenheartboutiquehotel.com/images/logo-green.png",
    "grounded-botanical-studio": "https://ims.sr/wp-content/uploads/2025/04/Grounded.jpg",
    "guesthouse-albergoalberga": "https://guesthousealberga.com/wp-content/uploads/2024/03/cropped-302162370_459943272818604_7623356389716890021_n.png",
    "guesthouse-albina": "https://guesthousealbina.com/wp-content/uploads/2024/05/Guesthouse-Albina-Logo-dunne-ronde-kader-Transparant.png",
    "h-t": "",
    "habco-delight": "",
    "habco-delight-north": "",
    "hakrinbank": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-flora": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-latour": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-nickerie": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-nieuwe-haven": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-tamanredjo": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "hakrinbank-tourtonne": "https://www.hakrinbank.com/app/uploads/2026/01/banner-1.png",
    "han-palace": "",
    "happy-flower-services": "",
    "harry-tjin": "",
    "hertz-suriname-car-rental": "",
    "hes-ds": "",
    "hes-ds-2": "",
    "hes-ds-3": "",
    "holiday-home-decor": "",
    "hollandia-bakkerij-north": "",
    "hollandia-bakkerij-south": "",
    "holy-moly": "",
    "honeycare-north": "https://www.honeycaresu.com/wp-content/uploads/2024/02/HC_Cat_Thumb2.jpg",
    "honeycare-south": "https://www.honeycaresu.com/wp-content/uploads/2024/02/HC_Cat_Thumb2.jpg",
    "hotel-north-resort": "",
    "house-of-pureness": "",
    "hsds-lifestyle-noord": "",
    "hsds-lifestyle-wanica": "",
    "iamchede": "",
    "infinity-holding": "",
    "instyle-optics": "",
    "international-academy-of-suriname": "",
    "intervast": "",
    "invictus-brazilian-jiu-jitsu": "",
    "itrendzz": "",
    "jack-tours-travel-service": "",
    "jadore-cafe-grill": "",
    "jage-caffe": "https://ims.sr/wp-content/uploads/2025/02/jage-2.png",
    "jage-caffe-2": "https://ims.sr/wp-content/uploads/2025/02/jage-2.png",
    "jamilas-dry-cleaning-north": "",
    "jamilas-dry-cleaning-south": "",
    "janelles-shoes-and-bags": "",
    "jenny-tours": "",
    "jjs-place-zuid": "",
    "joosje-roti-shop": "",
    "just-curlss": "",
    "kabalebo-nature-resort": "https://kabalebo.com/wp-content/uploads/2025/04/home-header.jpg",
    "kaizen": "",
    "kaki-supermarkt": "",
    "karans-indian-food": "",
    "kasimex-indira-ghandiweg": "",
    "kasimex-makro": "",
    "keller-williams-suriname": "",
    "kempes-co": "",
    "ket-mien": "",
    "kfc-ims":             "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-kwatta":          "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-lallarookh":      "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-latour":          "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-lelydorp":        "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-waterkant":       "https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kfc-wilhelminastraat":"https://www.surinamyp.com/img/sr/e/1683205990-93-kfc.png",
    "kimboto": "",
    "kirpalani-domineestraat": "https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp",
    "kirpalani-maagdenstraat": "https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp",
    "kirpalani-super-store": "https://www.kirpalani.com/media/bluebird/widget/widget/image/h/i/highlights.webp",
    "kong-nam-snack": "",
    "krioro": "",
    "krioro-north": "",
    "kushiyaki-the-next-episode": "",
    "kwan-tai-restaurant": "",
    "kwan-tai-restaurant-2": "",
    "kyu-pho-grill": "",
    "ladybug-nursery-and-garden-center": "",
    "lamour-restaurant": "",
    "le-den": "",
    "lees-korean-grill": "",
    "leiding-1-restaurant": "",
    "lins-super-market": "",
    "lobby": "",
    "lucky-store": "",
    "lucky-twins-restaurant": "",
    "luxe-escape-lotus-spa-wellness-beautysalon": "",
    "maharaja-palace": "",
    "mandy-butka": "",
    "marchand-notariaat": "",
    "marina-resort-waterland": "https://surinameholidays.nl/wp-content/uploads/2016/05/IMG_3067-Edit.jpg",
    "matcha-loft": "",
    "max-n-co": "",
    "maze": "",
    "mcdonalds-centrum": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/McDonald%27s_logo_Targ%C3%B3wek.JPG/1280px-McDonald%27s_logo_Targ%C3%B3wek.JPG",
    "mcdonalds-hermitage-mall": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fe/McDonald%27s_logo_Targ%C3%B3wek.JPG/1280px-McDonald%27s_logo_Targ%C3%B3wek.JPG",
    "messias-tours": "",
    "mezze-suriname": "",
    "mighty-racks": "",
    "mimi-market": "",
    "mingle-sushi": "http://mingleparamaribo.com/wp-content/uploads/2022/06/Logo-Mingle-Cocktail-Lounge_gold.png",
    "mini-nail-shop": "",
    "miniso-gompertstraat": "https://www.miniso.com/Uploads/img/20230511/6459c5046dd82.jpg",
    "miniso-hermitage-mall": "https://www.miniso.com/Uploads/img/20230511/6459c5046dd82.jpg",
    "mirage-casino": "",
    "miss-doll-fit": "",
    "mn-international-centrum": "",
    "mn-international-kwatta": "",
    "moka-coffeebar": "",
    "mokisa-wellness": "",
    "mon-plaisir-nursery": "",
    "mondowa-tours": "",
    "morevans-outlet": "",
    "multi-travel": "",
    "muntjes-take-out-juniors-place": "",
    "murphys-irish-pub": "https://ims.sr/wp-content/uploads/2023/07/murphys.png",
    "naskip":   "https://upload.wikimedia.org/wikipedia/commons/2/25/Suriname_-_Paramaribo_-_Henck_Arronstraat_46_20221004_Naskip.jpg",
    "naskip-2": "https://upload.wikimedia.org/wikipedia/commons/2/25/Suriname_-_Paramaribo_-_Henck_Arronstraat_46_20221004_Naskip.jpg",
    "naskip-3": "https://upload.wikimedia.org/wikipedia/commons/2/25/Suriname_-_Paramaribo_-_Henck_Arronstraat_46_20221004_Naskip.jpg",
    "naskip-4": "https://upload.wikimedia.org/wikipedia/commons/2/25/Suriname_-_Paramaribo_-_Henck_Arronstraat_46_20221004_Naskip.jpg",
    "naskip-5": "https://upload.wikimedia.org/wikipedia/commons/2/25/Suriname_-_Paramaribo_-_Henck_Arronstraat_46_20221004_Naskip.jpg",
    "nassy-brouwer-college": "",
    "nassy-brouwer-school": "",
    "new-choice-lalla-rookhweg": "",
    "new-choice-nickerie": "",
    "new-choice-ringweg": "",
    "new-suriname-dream-cafe": "",
    "no-span-eco-tours": "",
    "norrii-zushii": "",
    "north-fitness-gym": "",
    "notariaat-mannes": "",
    "notariaat-van-dijk": "",
    "nr-1-spot": "",
    "numa-cafe": "",
    "oasis-restaurant": "",
    "ochama-amazing": "",
    "ochama-hermitage-mall": "",
    "office-world-hermitage-mall": "",
    "office-world-lelydorp": "",
    "ogi-teppanyaki-sushi-bar": "",
    "okido-tours-travel": "",
    "okopipi-tropical-grill": "",
    "olive-multi-cuisine-restaurant": "",
    "ondernemershuis": "",
    "one-stop-apotheek-drugstore": "",
    "optiek-all-vision": "https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg",
    "optiek-all-vision-albina": "https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg",
    "optiek-all-vision-lelydorp": "https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg",
    "optiek-all-vision-nickerie": "https://allvision.sr/wp-content/uploads/2024/02/Banner-homepage-All-Vision.jpg",
    "optiek-marisa": "",
    "optiek-ninon": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "optiek-ninon-hermitage-mall": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "optiek-ninon-ims": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "optiek-ninon-lelydorp": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "optiek-ninon-meerzorg": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "optiek-ninon-nickerie": "https://ims.sr/wp-content/uploads/2023/09/logo-optiek-Ninon-969x1024.jpg",
    "orchid": "",
    "organic-skincare": "",
    "outdoor-living": "",
    "overbridge-river-resort": "https://overbridge.sr/wp-content/uploads/2019/02/overbridge-river-resort-type_sm.png",
    "overdoughsed-suriname": "",
    "padel-x-suriname": "https://upload.wikimedia.org/wikipedia/commons/f/ff/Platform_26_padel_tennis_courts_behind_Railway_Street%2C_Chatham.jpg",
    "padre-nostro-italian-restaurant": "",
    "pandie": "",
    "paramaribo-princess-casino": "",
    "paramaribo-zoo": "http://paramaribozoo.sr/wp-content/uploads/2024/12/slider-paramaribo-zoo-2.jpg",
    "percy-massage-therapy": "",
    "petisco-restaurant": "",
    "petit-bouchon": "",
    "pineapple-tours": "",
    "pitbull-fitness": "",
    "pizza-hut-leysweg":          "https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png",
    "pizza-hut-south":            "https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png",
    "pizza-hut-wilhelminastraat": "https://www.pizzahut.sr/wp-content/uploads/2024/05/show_01.png",
    "pizza-mafia": "",
    "popeyes-centrum":        "https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg",
    "popeyes-lelydorp":       "https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg",
    "popeyes-tbl":            "https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg",
    "popeyes-wilhelminastraat":"https://www.surinamyp.com/img/sr/e/1683207102-18-popeyes.jpg",
    "professional-private-security": "",
    "protrade-international": "",
    "qsi-international-school-of-suriname": "",
    "r-k-bisdom-paramaribo": "",
    "radisson-hotel": "https://ak-d.tripcdn.com/images/0226b12000rtqz8o4F02F_Z_1280_853_R50_Q90.jpg",
    "raja-ji": "",
    "ramada-paramaribo-princess": "https://www.ramadaparamaribo.com/wp-content/uploads/2026/02/pizza-cover.jpeg",
    "randoe-meubelen": "",
    "re-max-suriname": "https://static-images.remax.com/assets/web/global/v2/homepage/global-hero.jpg",
    "readytex-art-gallery": "https://www.readytexartgallery.com/wp-content/uploads/2026/02/rag_expo-3-26_1920x870.jpg",
    "real-one-fitness-gym": "",
    "red-century-party-shop-commewijne": "https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371",
    "red-century-party-shop-kwatta": "https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371",
    "red-century-party-shop-lelydorp": "https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371",
    "red-century-party-shop-north": "https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371",
    "red-century-party-shop-zorg-en-hoop": "https://media.evendo.com/locations-resized/ShoppingImages/1920x466/358c883a-ac82-4dad-a02d-20fa6c734371",
    "remy-vastgoed": "",
    "republic-bank-head-office": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "republic-bank-jozef-israelstraat": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "republic-bank-kernkampweg": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "republic-bank-nickerie": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "republic-bank-vant-hogerhuysstraat": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "republic-bank-zorg-en-hoop": "https://upload.wikimedia.org/wikipedia/commons/1/1d/Republic_Bank_logo.svg",
    "residence-inn-nickerie": "https://residenceinn.sr/wp-content/uploads/2024/06/web-logo-ResInn.png",
    "residence-inn-paramaribo": "https://residenceinn.sr/wp-content/uploads/2024/06/web-logo-ResInn.png",
    "resourceful-real-estate-construction": "",
    "restaurant-lhermitage": "",
    "restaurant-sarinah": "",
    "restoran-bibit": "",
    "ricos-a-gladiator-foodtruck": "",
    "rif-cleaning-service": "",
    "ring-ring-imports": "",
    "ritas-roti-shop": "",
    "rolines-de-waag": "",
    "roopram-roti-shop": "",
    "ross-rental-cars": "",
    "rossignol-2go-kwattaweg": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "rossignol-2go-thurkowstraat": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "rossignol-coppename": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "rossignol-geyersvlijt": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "rossignol-linda": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "rossignol-waaldijkstraat": "http://rossignolslagerij.com/cdn/shop/files/Rossignol-Logo_No-Name_1200x1200.png?v=1621953656",
    "royal-tours-suriname-guyana": "",
    "safety-first-quality-always": "",
    "sakura": "",
    "samba-cafe": "",
    "sanousch-books": "",
    "saras-brunch-cafe": "",
    "sash-fashion-hermitage-mall": "",
    "satyam-holidays": "",
    "savage-den": "",
    "savannah-casino-hotel": "https://cdn.worldota.net/t/640x400/content/e7/27/e72767fe01b309ca7a9a45352ac1e9041ddd91a2.jpeg",
    "scene-beauty-salon": "",
    "secas": "",
    "sendang-redjo": "",
    "shimmery-beauty-lounge": "",
    "shoebizz-ims": "https://ims.sr/wp-content/uploads/2023/09/shoebizz_office.jpg",
    "sizzler-midnight-grill": "",
    "sizzlers-signature": "",
    "slagerij-abbas": "",
    "slagerij-asruf": "",
    "slagerij-stolk": "",
    "sleepstore-suriname": "",
    "smart-connexxionz": "",
    "soengngie-mega-store": "",
    "soengngie-oriental-market": "",
    "south-america-hot-pot": "",
    "southern-commercial-bank": "https://scombank.sr/wp-content/uploads/2025/08/sparen-1.png",
    "spice-quest": "",
    "squeaky-clean": "",
    "squeezy-hot-pot-restaurant": "",
    "sranan-fowru": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-boni": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-combe": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-flu": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-leiding": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-lelydorp": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-meursweg": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-tabiki-fowru": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-tourtonne": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "sranan-fowru-zinnia": "https://srananfowru.sr/wp-content/uploads/2025/07/klaargemaakte-kip.webp",
    "steps-domineestraat": "https://steps-shop.weblocher.com/img2/about_bg.jpg",
    "steps-hermitage-mall": "https://steps-shop.weblocher.com/img2/about_bg.jpg",
    "steps-noord": "https://steps-shop.weblocher.com/img2/about_bg.jpg",
    "steps-wanica": "https://steps-shop.weblocher.com/img2/about_bg.jpg",
    "sthephany-skincare": "",
    "stichting-surinaams-museum": "http://www.surinaamsmuseum.net/wp-content/uploads/2015/08/SurinaamsMuseum-for-web.png",
    "store4u": "",
    "subway": "https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg",
    "subway-2": "https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg",
    "subway-3": "https://upload.wikimedia.org/wikipedia/commons/c/c3/Subway-restaurant.jpg",
    "sugar": "",
    "sun-ice": "",
    "supply-solutions-limited-suriname": "",
    "suran-adventures-tours-travel": "https://suranadventures.com/uploads/0000/1/2023/07/14/untitled-2.png",
    "surgoed-makelaardij": "",
    "surinaamsche-waterleiding-maatschappij": "",
    "suriname-princess-casino": "",
    "sweet-tooth-pastries": "",
    "sweetheart-hermitage-mall": "https://ims.sr/wp-content/uploads/2024/01/Sweetheart-_1-1024x573.png",
    "sweetheart-ims": "https://ims.sr/wp-content/uploads/2024/01/Sweetheart-_1-1024x573.png",
    "sweetie-coffee": "",
    "talula": "",
    "tapauku-terras": "",
    "tastelicious": "",
    "tasty-fresh-food-coffee-bar": "",
    "tbl-cinemas": "https://www.tblcinemas.com/storage/backdrops/2TWIlmhE06ghspeQLEX1VmnEBiE.jpg",
    "teasee": "",
    "telesur-centrum": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "telesur-latour": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "telesur-lelydorp": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "telesur-nickerie": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "telesur-noord": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "telesur-zonnebloemstraat": "https://www.telesur.sr/wp-content/uploads/2025/11/Telesur-Plus-1200-x-1200_17NOV2025-1.jpg",
    "the-aerial-yoga-studio": "",
    "the-bakery-house": "",
    "the-basement-barbershop": "",
    "the-beauty-bar-north": "",
    "the-beauty-bar-south": "",
    "the-coffee-box-north": "",
    "the-coffee-hobbyist": "",
    "the-girl-house": "",
    "the-laundry-spot": "",
    "the-maillard-cafe": "",
    "the-nail-house": "",
    "the-old-garage": "",
    "the-perfume-spot": "",
    "the-rose-manor": "",
    "the-solution-property-management": "",
    "the-sweetest-thing": "",
    "the-warehouse-shop": "",
    "theater-thalia": "",
    "three-little-beans": "",
    "tianyou-aquafun": "",
    "tipsy-bar-lounge": "",
    "tirzahs-patisserie": "",
    "tomahawk-outdoor-adventures": "https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png",
    "tomahawk-outdoor-adventures-hermitage-mall": "https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png",
    "tomahawk-outdoor-adventures-ims": "https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png",
    "tomahawk-outdoor-adventures-lelydorp": "https://tomahawk.sr/wp-content/uploads/2024/02/tomahawk-logo.png",
    "topslager-stolk": "",
    "topsport": "",
    "tori-oso": "",
    "touch-of-heaven-wellness": "",
    "tout-tout-petit": "",
    "toys-n-more": "",
    "tranquil-at-mamba-republiek": "",
    "tranquil-massage": "",
    "tropicana-hotel-casino-suriname": "https://ak-d.tripcdn.com/images/200i0a0000004jxq769BE_R_960_660_R5_D.jpg",
    "tsw-group": "",
    "tucan-resort-and-spa": "https://tucanresidence.com/wp-content/uploads/duoble-room-scaled.jpg",
    "tulip-supermarket": "",
    "twins-pizza-burgers": "",
    "typing-nomad-nv": "",
    "u-s-bakery": "",
    "uitkijk-riverlounge-cafe": "",
    "vcm-slagerij-centrum": "https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png",
    "vcm-slagerij-johannes-mungrastraat": "https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png",
    "vcm-slagerij-verl-gemenelandsweg": "https://winkel.vcm.sr/wp-content/uploads/2019/09/VCM-slagerij-1000x-PNG.png",
    "vifa-trading": "",
    "villa-zapakara": "",
    "villas-paramaribo": "https://villasparamaribo.com/wp-content/uploads/2025/01/b3d31ef4-1c33-4e72-8a26-1dbab5dcb6b7.jpg",
    "vincent-supermarket": "",
    "viva-mexico": "",
    "waldos-worldwide-travel-service": "",
    "warung-resa-centrum": "",
    "warung-soepy-ann": "",
    "welink-real-estate": "",
    "wing-hung-cake-shop": "",
    "wollys": "http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg",
    "wollys-2": "http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg",
    "wollys-3": "http://wollys.com/wp-content/uploads/2014/12/Double-Wolly-Shoarmacc.jpg",
    "wow-plus": "",
    "x-avenue": "",
    "ying-hao-beautyshop": "",
    "yogh-hospitality": "",
    "yokohama-trading": "",
    "young-engineers": "",
    "zenobia-bottling-company": "",
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
    if any(x in s for x in ['bar-qle','tipsy','georgies','uitkijk','d-mighty',
            'riverloun','murphys','de-spot','de-verdieping','lobby','alegria',
            'salon','bar-zu','lounge','mr-bar','bar-nord']):
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
            'paramaribo-zoo','invictus','fish-finder','outdoor-living']):
        return 'entertainment'
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
            'dojo-couture','sash-fashion','steps-','morevans','janelles',
            'crocs-','chm-','miniso','ochama','itrendzz','flex-luxuries',
            'everything-sr','x-avenue','store4u','lucky-store']):
        return 'fashion-clothing'
    if any(x in s for x in ['digital-world','computronics','flex-phones','computer-hardware',
            'ring-ring','vifa-trading','yokohama-trading']):
        return 'electronics'
    if any(x in s for x in ['furniture','ashley-furniture','randoe-meubelen',
            'building-depot','sleepstore','holiday-home','randoe','outdoor-living',
            'galaxyliving']):
        return 'home-furniture'
    if any(x in s for x in ['optiek','instyle-optic','chees-jewelry','chique-eyewear']):
        return 'optical-jewelry'
    if any(x in s for x in ['slagerij','topslager','vcm-slager','keurslager',
            'hollandia-bakkerij','da-drogist','alis-drugstore','rossignol',
            'office-world']):
        return 'food-specialty'
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
    if any(x in s for x in ['sugar','sweetheart-ims','from-kay-with-love','holy-moly']):
        return 'bakeries-sweets'
    if any(x in s for x in ['max-n-co','mighty-racks','eterno','cute-as-a-button',
            'new-choice','surimami-store','toys-n-more','wow-plus',
            'mn-international','pandie']):
        return 'fashion-clothing'
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
    # ── Restaurant catch-ups (slugs not matched above) ─────────────────────
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
    # Foursquare cache fills gaps: phone / address / website / coordinates
    fsq = _FSQ.get(slug, {})
    _fdet = _FSQ_DETAILS.get(slug, {})
    # Priority for contact fields: curated _BIZ > OSM (applied later in build_listing_page) > Foursquare
    return {"slug": slug, "name": b["name"], "area": b.get("location", "Suriname"),
            "address":  b.get("address") or fsq.get("address") or "",
            "phone":    b.get("phone")   or fsq.get("phone")   or "",
            "email":    b.get("email", ""),
            "website":  b.get("website") or fsq.get("website") or "",
            "category": b.get("category", ""),
            "description": b.get("description", ""),
            "url": f"listing/{slug}/",          # internal detail page
            "external_url": _biz_url(b),        # business website / Google fallback
            "image": _biz_img(slug) or _fdet.get("photo_url", ""),   # FSQ photo fallback for thumbnails
            "subcat": _subcat(slug)}

RESTAURANTS = [b for slug in ["a-la-john","ac-bar-restaurant","baka-foto-restaurant","bar-zuid","big-tex","bori-tori","chi-min","de-gadri","de-spot","de-verdieping","el-patron-latin-grill","elines-pizza","garden-of-eden","goe-thai-noodle-bar","hard-rock-cafe-suriname","joey-ds","julias-food","kasan-snacks","las-tias","mickis-palace-noord","mickis-palace-zuid","mingle-paramaribo","moments-restaurant","pane-e-vino","pannekoek-en-poffertjes-cafe","passion-food-and-wines","rogom-farm-nv","souposo","sushi-ya","the-coffee-box","zeg-ijsje","zus-zo-cafe","aaras-cafe","ace-restaurant-lounge","ayo-river-lounge","bar-qle","bingo-pizza-coppename","bingo-pizza-kwatta","bistro-brwni","bistro-don-julio","bistro-lequatorze","blossom-beauty-bar","blue-grand-cafe","brow-bliss-lounge","burger-king-centrum","burger-king-latour","coffee-mama","cy-coffee","d-mighty-view-lounge","dolce-bella-cafe","etembe-rainforest-restaurant","ettores-pizza-kitchen","flavor-restaurant","georgies-bar-chill","habco-delight","habco-delight-north","jadore-cafe-grill","joosje-roti-shop","kfc-ims","kfc-kwatta","kfc-lallarookh","kfc-latour","kfc-lelydorp","kfc-waterkant","kfc-wilhelminastraat","kong-nam-snack","kwan-tai-restaurant","kwan-tai-restaurant-2","kyu-pho-grill","lamour-restaurant","lees-korean-grill","leiding-1-restaurant","lucky-twins-restaurant","mcdonalds-centrum","mcdonalds-hermitage-mall","mingle-sushi","moka-coffeebar","naskip","naskip-2","naskip-3","naskip-4","naskip-5","new-suriname-dream-cafe","numa-cafe","oasis-restaurant","ogi-teppanyaki-sushi-bar","okopipi-tropical-grill","olive-multi-cuisine-restaurant","padre-nostro-italian-restaurant","petisco-restaurant","pizza-hut-leysweg","pizza-hut-south","pizza-hut-wilhelminastraat","pizza-mafia","popeyes-centrum","popeyes-lelydorp","popeyes-tbl","popeyes-wilhelminastraat","restaurant-lhermitage","restaurant-sarinah","ritas-roti-shop","roopram-roti-shop","samba-cafe","saras-brunch-cafe","shimmery-beauty-lounge","sizzler-midnight-grill","squeezy-hot-pot-restaurant","sranan-fowru","sranan-fowru-boni","sranan-fowru-combe","sranan-fowru-flu","sranan-fowru-leiding","sranan-fowru-lelydorp","sranan-fowru-meursweg","sranan-fowru-tabiki-fowru","sranan-fowru-tourtonne","sranan-fowru-zinnia","subway","subway-2","subway-3","sweetie-coffee","tasty-fresh-food-coffee-bar","the-bakery-house","the-beauty-bar-north","the-beauty-bar-south","the-coffee-box-north","the-coffee-hobbyist","the-maillard-cafe","tipsy-bar-lounge","tirzahs-patisserie","twins-pizza-burgers","u-s-bakery","uitkijk-riverlounge-cafe"] for b in [_make_biz(slug)] if b]

HOTELS = [b for slug in ["bronbella-villa-residence","courtyard-by-marriott","eco-resort-miano","eco-torarica","holland-lodge","hotel-palacio","hotel-peperpot","houttuyn-wellness-river-resort","jacana-amazon-wellness-resort","oxygen-resort","royal-brasil-hotel","royal-breeze-hotel-paramaribo","royal-torarica","taman-indah-resort","the-golden-truly-hotel","tiny-house-tropical-appartment","torarica-resort","villa-famiri","waterland-suites","zeelandia-suites","anaula-nature-resort","atlantis-hotel-casino","danpaati-river-lodge","greenheart-boutique-hotel","guesthouse-albergoalberga","guesthouse-albina","hotel-north-resort","kabalebo-nature-resort","kimboto","marina-resort-waterland","overbridge-river-resort","radisson-hotel","ramada-paramaribo-princess","residence-inn-nickerie","residence-inn-paramaribo","savannah-casino-hotel","tropicana-hotel-casino-suriname","tucan-resort-and-spa","villa-zapakara","villas-paramaribo"] for b in [_make_biz(slug)] if b]

SIGHTSEEING = [b for slug in ["ford-zeelandia","het-koto-museum","peperpot-nature-park","joden-savanne","plantage-frederiksdorp","museum-bakkie","cola-kreek-recreatiepark","conservatorium-suriname","golf-club-paramaribo","paramaribo-zoo","readytex-art-gallery","stichting-surinaams-museum","tbl-cinemas","theater-thalia"] for b in [_make_biz(slug)] if b]

ADVENTURES_BIZ = [b for slug in ["afobaka-resort","akira-overwater-resort","huub-explorer-tours","knini-paati","kodouffi-tapawatra-resort","recreatie-oord-carolina-kreek","tio-boto-eco-resort","unlimited-suriname-tours","wayfinders-exclusive-n-v","clevia-park","folo-nature-tours","free-city-walk-paramaribo","jack-tours-travel-service","jenny-tours","messias-tours","mondowa-tours","no-span-eco-tours","okido-tours-travel","outdoor-living","pineapple-tours","royal-tours-suriname-guyana","suran-adventures-tours-travel","tomahawk-outdoor-adventures","tomahawk-outdoor-adventures-hermitage-mall","tomahawk-outdoor-adventures-ims","tomahawk-outdoor-adventures-lelydorp"] for b in [_make_biz(slug)] if b]

SHOPPING = [b for slug in ["9173","bed-bath-more-bbm","divergent-body-jewelry","dj-liquor-store","from-me-to-me","galaxy","h-garden","hermitage-mall","honeycare","international-mall-of-suriname","kirpalani","lilis","nv-zing-manufacturing","papillon-crafts","readytex-souvenirs-and-crafts","shlx-collection","sleeqe","smoothieskin","suraniyat","switi-momenti-candles-crafts","talking-prints-concept-store","the-old-attic","the-uma-store","unlocked-candles","woodwonders-suriname","zeepfabriek-joab","amada-shopping","ashley-furniture-homestore","auto-style-franchepanestraat","auto-style-johannes-mungrastraat","auto-style-kwatta","auto-style-tweede-rijweg","auto-style-verlengde-gemenelandsweg","beyrouth-bazaar","boekhandel-vaco","building-depot","chees-jewelry-watches","chm-centrum","chm-commewijne","chm-kernkampweg","chm-nickerie","chm-wanica","chm-wilhelminastraat","chm-wilhelminastraat-2","chois-supermarkt","chois-supermarkt-lelydorp","chois-supermarkt-north","combe-bazaar","combe-markt","computer-hardware-services","computronics-north","computronics-south","crocs-ims","da-drogisterij-coppename","da-drogisterij-hermitage","da-drogisterij-ims-mall","da-drogisterij-lelydorp","da-drogisterij-wilhelmina","de-keurslager-interfarm","deto-handelmaatschappij","digital-world-hermitage-mall","digital-world-ims","digital-world-maretraite-mall","digital-world-maretraite-mall-2","dojo-couture-hermitage-mall","flex-phones","footcandy-hermitage-mall","furniture-city-kwatta","furniture-city-north","gao-ming-trading-north","gao-ming-trading-south","golderom-healthy-organic-store","hollandia-bakkerij-north","hollandia-bakkerij-south","kaki-supermarkt","kirpalani-domineestraat","kirpalani-maagdenstraat","kirpalani-super-store","lins-super-market","lucky-store","mimi-market","miniso-gompertstraat","miniso-hermitage-mall","ochama-amazing","ochama-hermitage-mall","office-world-hermitage-mall","office-world-lelydorp","optiek-all-vision","optiek-all-vision-albina","optiek-all-vision-lelydorp","optiek-all-vision-nickerie","optiek-marisa","optiek-ninon","optiek-ninon-hermitage-mall","optiek-ninon-ims","optiek-ninon-lelydorp","optiek-ninon-meerzorg","optiek-ninon-nickerie","randoe-meubelen","ring-ring-imports","rossignol-2go-kwattaweg","rossignol-2go-thurkowstraat","rossignol-coppename","rossignol-geyersvlijt","rossignol-linda","rossignol-waaldijkstraat","sanousch-books","sash-fashion-hermitage-mall","slagerij-abbas","slagerij-asruf","slagerij-stolk","soengngie-mega-store","soengngie-oriental-market","steps-hermitage-mall","sweetheart-hermitage-mall","topslager-stolk","tulip-supermarket","vcm-slagerij-centrum","vcm-slagerij-johannes-mungrastraat","vcm-slagerij-verl-gemenelandsweg","vifa-trading","vincent-supermarket","yokohama-trading"] for b in [_make_biz(slug)] if b]

SERVICES = [b for slug in ["bitdynamics","bloom-wellness-cafe","carpe-diem-massagepraktijk","delete-beauty-lounge","dli-travel-consultancy","eaglemedia","ec-operations","ekay-media","fatum","fly-allways","hairstudio-32","handmade-by-farrell-nv","ias-wooden-and-construction-nv","inksane-tattoos","klm-royal-dutch-airlines","lashlift-suriname","lioness-beauty-effects","mokisa-busidataa-osu-nv","nv-threefold-quality-system-support","pinkmoon-suriname","rich-skin","rock-fitness-paramaribo","royal-rose-yoni-spa","royal-spa","royal-wellness-lounge","seen-stories","stichting-shiatsu-massage","stukaderen-in-nederland","surimami-store","surinam-airways","the-beauty-bar","the-freelance-scout","the-house-of-beauty","the-waxing-booth","the-wonderlab-su","thermen-hermitage-turkish-bath-beautycenter","timeless-barber-and-nail-shop","yoga-peetha-happiness-centre","101-real-estate","4r-gym","abrix-cleaning-services","access-suriname-travel","alegria","alis-drugstore","alliance-francaise","anton-de-kom-universiteit-van-suriname","apotheek-joemmanbaks","apotheek-karis","apotheek-mac-donald-north","apotheek-mac-donald-south","apotheek-rafeka","apotheek-sibilo","apotheek-soma","apotheek-soma-ringweg","arthur-alex-hoogendoorn-atheneum","assuria-hermitage-high-rise","assuria-insurance-walk-in-city","assuria-insurance-walk-in-commewijne","assuria-insurance-walk-in-lelydorp","assuria-insurance-walk-in-nickerie","assuria-insurance-walk-in-noord","augis-travel","ayur-mi-beauty-wellness","balance-studio","balletschool-marlene","bella-italia","best-mart","blissful-massage-aromatherapy","bmw-suriname","body-enhancement-gym","boss-burgers","brahma-centrum","brahma-noord","brahma-zuid","bright-cleaning","brilleman","brotherhood-security","buro-workspaces","byd-suriname","camex-suriname","car-rental-city","carline-kwatta","carline-waaldijkstraat","carvision-paramaribo","chique-eyewear-fashion","chuck-e-cheese","cinnagirl","ciranos","clarissa-vaseur-writing-wellness-services-claw","clean-it","club-oase","cookie-closet","cpr-pilates-curves","creative-q","cupcake-fantasy","curl-babes","cute-as-a-button","cynsational-glam","da-select-en-service-apotheek","dansclub-danzson","dcars-rental","de-cederboom-school","de-nederlandse-basisschool-het-kleurenorkest","de-spetter","de-surinaamsche-bank-hermitage-mall","de-surinaamsche-bank-hoofdkantoor","de-surinaamsche-bank-lelydorp","de-surinaamsche-bank-ma-retraite","de-surinaamsche-bank-ma-retraite-2","de-surinaamsche-bank-nickerie","de-surinaamsche-bank-nickerie-2","de-surinaamsche-bank-nieuwe-haven","de-vrije-school","dhl-express-service-point","dierenarts-resopawiro","dierenartspraktijk-l-m-bansse-issa","dierenpoli-lobo","digicel-albina","digicel-business-center","digicel-extacy","digicel-hermitage","digicel-latour","digicel-lelydorp","digicel-nickerie","digicel-wilhelminastraat","djinipi-copy-center","djo-cleaning-service","dlish","dojo-couture-centrum","dojo-couture-ims","dor-property-management-services-n-v","dream-clean-suriname","dresscode","eethuis-liv","energiebedrijven-suriname-ebs","eterno","eucon","everything-sr","faraya-medical-center","farma-vida","fatum-schadeverzekering-commewijne","fatum-schadeverzekering-hoofdkantoor","fatum-schadeverzekering-kwatta","fatum-schadeverzekering-nickerie","fhr-lim-a-po-institute-for-higher-education","finabank-centrum","finabank-nickerie","finabank-noord","finabank-wanica","finabank-zuid","first-aid-plus","fish-finder-fishing-and-outdoors","fit-factory","flex-luxuries","fluxo-pilates","free-flow","from-kay-with-love","frygri","gaby-april-beauty-clinic","galaxyliving","garage-d-a-ashruf","glam-curves","glambox","goldenwings","gossip-nails-xx","great-wall-motor-suriname","grounded-botanical-studio","h-t","hakrinbank","hakrinbank-flora","hakrinbank-latour","hakrinbank-nickerie","hakrinbank-nieuwe-haven","hakrinbank-tamanredjo","hakrinbank-tourtonne","han-palace","happy-flower-services","harry-tjin","hertz-suriname-car-rental","hes-ds","hes-ds-2","hes-ds-3","holiday-home-decor","holy-moly","honeycare-north","honeycare-south","house-of-pureness","hsds-lifestyle-noord","hsds-lifestyle-wanica","iamchede","infinity-holding","instyle-optics","international-academy-of-suriname","intervast","invictus-brazilian-jiu-jitsu","itrendzz","jage-caffe","jage-caffe-2","jamilas-dry-cleaning-north","jamilas-dry-cleaning-south","janelles-shoes-and-bags","jjs-place-zuid","just-curlss","kaizen","karans-indian-food","kasimex-indira-ghandiweg","kasimex-makro","keller-williams-suriname","kempes-co","ket-mien","krioro","krioro-north","kushiyaki-the-next-episode","ladybug-nursery-and-garden-center","le-den","lobby","luxe-escape-lotus-spa-wellness-beautysalon","maharaja-palace","mandy-butka","marchand-notariaat","matcha-loft","max-n-co","maze","mezze-suriname","mighty-racks","mini-nail-shop","mirage-casino","miss-doll-fit","mn-international-centrum","mn-international-kwatta","mokisa-wellness","mon-plaisir-nursery","morevans-outlet","multi-travel","muntjes-take-out-juniors-place","murphys-irish-pub","nassy-brouwer-college","nassy-brouwer-school","new-choice-lalla-rookhweg","new-choice-nickerie","new-choice-ringweg","norrii-zushii","north-fitness-gym","notariaat-mannes","notariaat-van-dijk","nr-1-spot","ondernemershuis","one-stop-apotheek-drugstore","orchid","organic-skincare","overdoughsed-suriname","padel-x-suriname","pandie","paramaribo-princess-casino","percy-massage-therapy","petit-bouchon","pitbull-fitness","professional-private-security","protrade-international","qsi-international-school-of-suriname","raja-ji","re-max-suriname","real-one-fitness-gym","red-century-party-shop-commewijne","red-century-party-shop-kwatta","red-century-party-shop-lelydorp","red-century-party-shop-north","red-century-party-shop-zorg-en-hoop","remy-vastgoed","republic-bank-head-office","republic-bank-jozef-israelstraat","republic-bank-kernkampweg","republic-bank-nickerie","republic-bank-vant-hogerhuysstraat","republic-bank-zorg-en-hoop","resourceful-real-estate-construction","restoran-bibit","ricos-a-gladiator-foodtruck","rif-cleaning-service","rolines-de-waag","ross-rental-cars","safety-first-quality-always","sakura","satyam-holidays","savage-den","scene-beauty-salon","secas","sendang-redjo","shoebizz-ims","sizzlers-signature","sleepstore-suriname","smart-connexxionz","south-america-hot-pot","southern-commercial-bank","spice-quest","squeaky-clean","steps-domineestraat","steps-noord","steps-wanica","sthephany-skincare","store4u","sugar","sun-ice","supply-solutions-limited-suriname","surgoed-makelaardij","surinaamsche-waterleiding-maatschappij","suriname-princess-casino","sweet-tooth-pastries","sweetheart-ims","talula","tapauku-terras","tastelicious","teasee","telesur-centrum","telesur-latour","telesur-lelydorp","telesur-nickerie","telesur-noord","telesur-zonnebloemstraat","the-aerial-yoga-studio","the-basement-barbershop","the-girl-house","the-laundry-spot","the-nail-house","the-old-garage","the-perfume-spot","the-rose-manor","the-solution-property-management","the-sweetest-thing","the-warehouse-shop","three-little-beans","tianyou-aquafun","topsport","tori-oso","touch-of-heaven-wellness","tout-tout-petit","toys-n-more","tranquil-at-mamba-republiek","tranquil-massage","tsw-group","typing-nomad-nv","viva-mexico","waldos-worldwide-travel-service","warung-resa-centrum","warung-soepy-ann","welink-real-estate","wing-hung-cake-shop","wollys","wollys-2","wollys-3","wow-plus","x-avenue","ying-hao-beautyshop","yogh-hospitality","young-engineers","zenobia-bottling-company"] for b in [_make_biz(slug)] if b]

# Sort every category list alphabetically by display name
_alpha = lambda lst: sorted(lst, key=lambda b: b["name"].lower())
RESTAURANTS   = _alpha(RESTAURANTS)
HOTELS        = _alpha(HOTELS)
SIGHTSEEING   = _alpha(SIGHTSEEING)
ADVENTURES_BIZ= _alpha(ADVENTURES_BIZ)
SHOPPING      = _alpha(SHOPPING)
SERVICES      = _alpha(SERVICES)

# ── Global search index (embedded in every page for client-side search) ──────
import json as _json
_SEARCH_INDEX = _json.dumps([
    *[{"n": b["name"], "u": b["url"], "c": "Eat & Drink",  "a": b.get("area","")} for b in RESTAURANTS],
    *[{"n": b["name"], "u": b["url"], "c": "Stay",         "a": b.get("area","")} for b in HOTELS],
    *[{"n": b["name"], "u": b["url"], "c": "Nature",       "a": b.get("area","")} for b in SIGHTSEEING],
    *[{"n": b["name"], "u": b["url"], "c": "Activities",   "a": b.get("area","")} for b in ADVENTURES_BIZ],
    *[{"n": b["name"], "u": b["url"], "c": "Shopping",     "a": b.get("area","")} for b in SHOPPING],
    *[{"n": b["name"], "u": b["url"], "c": "Services",     "a": b.get("area","")} for b in SERVICES],
], ensure_ascii=False, separators=(',', ':'))

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
    m = re.search(r'<img[^>]+src=["\'](^["\']+)["\']>', raw)
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
  <link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <link rel="apple-touch-icon" href="/favicon.svg">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/tailwind.css">
  <style>
    :root { --forest:#1B4332; --forest2:#2D6A4F; --leaf:#52B788; --mint:#D8F3DC; --coral:#E76F51; }
    body   { font-family: 'Inter', system-ui, sans-serif; }
    .serif { font-family: 'Playfair Display', Georgia, serif; }
    .hero-bg { background-size:cover; background-position:center; }
    @media (min-width:768px) { .hero-bg { background-attachment:fixed; } }
    .card-hover { transition: transform .2s, box-shadow .2s; }
    .card-hover:hover { transform:translateY(-4px); box-shadow:0 12px 32px rgba(0,0,0,.12); }
    a { text-decoration: none; }
  </style>"""

# ── WorldTides: tide data for Paramaribo ────────────────────────────────────
_TIDES_CACHE_FILE = "tides_cache.json"
_TIDES_LAT        = 5.852
_TIDES_LON        = -55.203

def fetch_worldtides():
    """
    Fetch tide extremes for Paramaribo from WorldTides API v3.
    Caches results to tides_cache.json for 24 h to stay within the free
    100-requests/month limit.  Requires WORLDTIDES_KEY env var.
    Returns (extremes_list, is_live, updated_str).
    """
    import os as _os
    key = _os.environ.get("WORLDTIDES_KEY", "").strip()
    if not key:
        print("  WorldTides: no WORLDTIDES_KEY set — skipping tides")
        return [], False, "No API key configured"

    # Check 24-h cache first
    now_ts = datetime.now(timezone.utc).timestamp()
    try:
        with open(_TIDES_CACHE_FILE) as _f:
            cache = json.load(_f)
        if now_ts - cache.get("fetched", 0) < 86400:
            print(f"  WorldTides: using cached data ({_TIDES_CACHE_FILE})")
            return cache["extremes"], True, cache["updated"]
    except Exception:
        pass

    try:
        url = (
            f"https://www.worldtides.info/api/v3?extremes"
            f"&lat={_TIDES_LAT}&lon={_TIDES_LON}&days=3&key={key}"
        )
        with urllib.request.urlopen(url, timeout=20) as _r:
            data = json.loads(_r.read().decode("utf-8"))

        if data.get("status", 0) != 200:
            raise ValueError(f"WorldTides error: {data}")

        extremes = data.get("Extremes", [])
        ts_str   = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")

        cache = {"fetched": now_ts, "extremes": extremes, "updated": ts_str}
        with open(_TIDES_CACHE_FILE, "w") as _f:
            json.dump(cache, _f)
        print(f"  WorldTides: fetched {len(extremes)} extremes")
        return extremes, True, ts_str

    except Exception as e:
        print(f"  WorldTides error: {e}")
        try:
            with open(_TIDES_CACHE_FILE) as _f:
                cache = json.load(_f)
            return cache["extremes"], False, cache["updated"] + " (cached)"
        except Exception:
            return [], False, "Data unavailable"


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
    "SMZO": "Paramaribo / Zorg en Hoop (ORJ)",
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


def fetch_opensky_flights():
    """
    Fetch recent arrivals and departures at SMJP (Johan Adolf Pengel, PBM)
    from OpenSky Network.  Completely free, no API key required.
    Returns (arrivals, departures, updated_str).
    """
    now_ts = int(datetime.now(timezone.utc).timestamp())
    begin  = now_ts - 48 * 3600   # past 48 h for a good sample
    end    = now_ts
    results = {}

    for direction in ("arrival", "departure"):
        try:
            url = (
                f"https://opensky-network.org/api/flights/{direction}"
                f"?airport={_OPENSKY_ICAO}&begin={begin}&end={end}"
            )
            req = urllib.request.Request(
                url, headers={"User-Agent": "ExploreSuriname/1.0"})
            with urllib.request.urlopen(req, timeout=20) as _r:
                rows = json.loads(_r.read().decode("utf-8")) or []

            flights = [_decode_flight(row, direction) for row in rows]
            # Most recent first for arrivals; most recent first for departures too
            flights.sort(key=lambda x: x["ts"], reverse=True)

            # Deduplicate and filter out SMJP↔SMJP
            seen, clean = set(), []
            for f in flights:
                if f["flight"] not in seen and f["icao"] not in ("SMJP", "", "???"):
                    seen.add(f["flight"])
                    clean.append(f)
            results[direction] = clean[:15]
            print(f"  OpenSky {direction}s: {len(clean)} flights")
        except Exception as e:
            print(f"  OpenSky {direction} error: {e}")
            results[direction] = []

    updated = datetime.now(SR_TZ).strftime("%d %b %Y %H:%M SR")
    return results.get("arrival", []), results.get("departure", []), updated


def nav_html(active="home", prefix=""):
    links = [
        (f"{prefix}nature.html",       "Nature"),
        (f"{prefix}activities.html",   "Activities"),
        (f"{prefix}restaurants.html",  "Eat & Drink"),
        (f"{prefix}hotels.html",       "Stay"),
        (f"{prefix}shopping.html",     "Shopping"),
        (f"{prefix}services.html",     "Services"),
        (f"{prefix}currency.html",     "Currency"),
        (f"{prefix}flights.html",      "Flights"),
        (f"{prefix}conditions.html",   "Forecast"),
        (f"{prefix}news.html",         "News"),
    ]
    lhtml = ""
    for href, label in links:
        cls = "font-semibold" if label.lower() == active else "text-gray-700 hover:text-green-800 transition"
        color = 'style="color:var(--forest)"' if label.lower() == active else ""
        lhtml += f'<a href="{href}" class="{cls} text-sm" {color}>{label}</a>\n'
    cat_colors = {"Eat & Drink":"#7c3aed","Stay":"#c05621","Nature":"var(--forest)",
                   "Activities":"var(--forest2)","Shopping":"#0369a1","Services":"#0369a1","Sightseeing":"var(--forest)"}
    return f"""
<nav class="fixed top-0 w-full z-50" style="background:rgba(255,255,255,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 12px rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
    <a href="{prefix}index.html" class="flex items-baseline">
      <span class="serif text-2xl font-bold" style="color:var(--forest)">Explore</span><span class="serif text-2xl font-bold" style="color:var(--coral)">Suriname</span>
    </a>
    <div class="hidden md:flex items-center gap-5">{lhtml}</div>
    <div class="flex items-center gap-2">
      <button onclick="openSearch()" title="Search listings (press /)" class="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 text-gray-400 text-sm hover:border-gray-400 hover:text-gray-600 transition bg-gray-50" style="min-width:120px">
        <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path stroke-linecap="round" d="m21 21-4.35-4.35"/></svg>
        <span class="hidden sm:inline">Search…</span>
        <span class="ml-auto hidden sm:inline text-xs bg-gray-200 text-gray-500 rounded px-1.5 py-0.5 font-mono">/</span>
      </button>
    </div>
    <button onclick="document.getElementById('mm').classList.toggle('hidden')" class="md:hidden p-2 rounded-lg hover:bg-gray-100">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>
  </div>
  <div id="mm" class="hidden md:hidden border-t bg-white px-5 py-4 flex flex-col gap-3 text-sm">{lhtml}</div>
</nav>

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
const _SI = {_SEARCH_INDEX};
const _CAT_C = {_json.dumps(cat_colors)};
let _sel = -1;
function openSearch() {{
  document.getElementById('search-modal').style.display = 'block';
  setTimeout(() => document.getElementById('search-input').focus(), 50);
}}
function closeSearch() {{
  document.getElementById('search-modal').style.display = 'none';
  document.getElementById('search-input').value = '';
  document.getElementById('search-results').innerHTML = '<p id="search-hint" style="text-align:center;color:#9ca3af;font-size:.85rem;padding:32px 0">Start typing to search {len(_SEARCH_INDEX.split('"n"')) - 1} listings…</p>';
  _sel = -1;
}}
function runSearch(q) {{
  const box = document.getElementById('search-results');
  q = q.trim();
  if (!q) {{ closeSearch(); openSearch(); return; }}
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
<footer style="background:var(--forest)" class="text-white py-16">
  <div class="max-w-6xl mx-auto px-5">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 mb-10">
      <div>
        <p class="serif text-2xl font-bold mb-3">Explore<span style="color:var(--coral)">Suriname</span></p>
        <p class="text-white/60 text-sm leading-relaxed">Your guide to Suriname — restaurants, hotels, nature, activities and local news.</p>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Explore</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li><a href="{prefix}nature.html"      class="hover:text-white transition">Nature &amp; Parks</a></li>
          <li><a href="{prefix}activities.html"  class="hover:text-white transition">Activities</a></li>
          <li><a href="{prefix}restaurants.html" class="hover:text-white transition">Eat &amp; Drink</a></li>
          <li><a href="{prefix}hotels.html"      class="hover:text-white transition">Hotels &amp; Lodges</a></li>
          <li><a href="{prefix}shopping.html"    class="hover:text-white transition">Shopping</a></li>
          <li><a href="{prefix}services.html"    class="hover:text-white transition">Services</a></li>
          <li><a href="{prefix}currency.html"    class="hover:text-white transition">Currency Rates</a></li>
          <li><a href="{prefix}flights.html"     class="hover:text-white transition">Flights (PBM)</a></li>
          <li><a href="{prefix}conditions.html"  class="hover:text-white transition">Weather &amp; Tides</a></li>
          <li><a href="{prefix}news.html"        class="hover:text-white transition">Suriname News</a></li>
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
          <li><a href="mailto:{CONTACT_EMAIL}" class="hover:text-white transition">&#9993; {CONTACT_EMAIL}</a></li>
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
      <p class="text-white/40 text-xs">&copy; {YEAR} ExploreSuriname.com</p>
    </div>
  </div>
</footer>"""

def news_card_html(a, large=False):
    img = ""
    if a["image"]:
        h = "h-52" if large else "h-36"
        img = f'<img src="{a["image"]}" alt="" loading="lazy" class="w-full {h} object-cover" onerror="this.style.display=\'none\'">'
    badge = f'<span class="text-white text-xs font-medium px-2 py-0.5 rounded-full" style="background:{a["color"]}">{html_lib.escape(a["source"])}</span>'
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
    # Placeholder for ad unit — no visible text shown to users or crawlers
    return '<div class="my-6" aria-hidden="true"></div>'

def nature_card(spot):
    tags_html = "".join(
        f'<span class="text-xs px-2 py-0.5 rounded-full font-medium" style="background:var(--mint);color:var(--forest)">{t}</span>'
        for t in spot["tags"]
    )
    internal_url = f"listing/{_nature_slug(spot['name'])}/"    
    return f"""
<a href="{internal_url}" data-sub="{spot.get('subcat','nature-parks')}" class="listing-card group rounded-2xl overflow-hidden card-hover bg-white border border-gray-100 shadow-sm flex flex-col">
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
    <div class="flex flex-wrap gap-1 items-center justify-between">
      <div class="flex flex-wrap gap-1">{tags_html}</div>
      <span class="text-xs font-medium" style="color:var(--forest2)">Learn more &rarr;</span>
    </div>
  </div>
</a>"""

def activity_card_rich(act):
    slug = _act_slug(act["name"])
    internal_url = f"listing/{slug}/"
    img = act.get("image", "")
    img_html = f'<img src="{img}" alt="{html_lib.escape(act["name"])}" loading="lazy" class="w-full h-56 object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.style.display=\'none\'">' if img else ""
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

def poi_card(item, badge_key="cuisine"):
    url   = item.get("url", "#")
    badge = item.get(badge_key) or item.get("cuisine") or item.get("category", "")
    area  = item.get("area", "Suriname")
    img   = item.get("image", "")
    phone = item.get("phone", "")
    bg, fg = ("var(--mint)", "var(--forest2)") if badge_key == "cuisine" else ("#fff3e8", "#c05621")
    badge_html = f'<span class="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style="background:{bg};color:{fg}">{html_lib.escape(badge)}</span>' if badge else ""
    img_html = (f'<div class="w-full h-56 overflow-hidden rounded-t-2xl -mx-0 -mt-0">'
                f'<img src="{img}" alt="{html_lib.escape(item["name"])}" loading="lazy" '
                f'class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" '
                f'onerror="this.parentElement.style.background=\'#2D6A4F\';this.style.display=\'none\'">'
                f'</div>') if img else ""
    phone_html = f'<span class="text-gray-400 text-xs">&#128222; {html_lib.escape(phone)}</span>' if phone else ""
    return f"""
<a href="{url}" data-sub="{item.get('subcat','other')}" class="listing-card group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover flex flex-col overflow-hidden">
  {img_html}
  <div class="p-4 flex flex-col gap-2 flex-1">
    <div class="flex items-start justify-between gap-2">
      <h4 class="font-bold text-gray-900 text-base leading-tight group-hover:text-green-800 transition">{html_lib.escape(item['name'])}</h4>
      {badge_html}
    </div>
    <div class="flex items-center justify-between mt-auto pt-2">
      <p class="text-gray-400 text-xs">&#128205; {html_lib.escape(area)}</p>
      {phone_html}
      <span class="text-xs font-semibold" style="color:var(--forest2)">Visit &rarr;</span>
    </div>
  </div>
</a>"""


def _filter_bar_html(items, cat_key):
    """Sticky filter chip bar with live count badges and JS filtering."""
    from collections import Counter
    sub_counts = Counter(b.get("subcat","other") for b in items)
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

    bar_id = f"chipbar-{cat_key}"
    return f"""
<div class="sticky top-16 z-40 py-3 mb-8" style="background:rgba(249,250,251,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="relative flex items-center gap-1">
      <button id="{bar_id}-prev" onclick="chipScroll('{bar_id}',-1)" class="chip-arrow" aria-label="scroll left">&#8249;</button>
      <div id="{bar_id}" class="flex gap-2 overflow-x-auto pb-1" style="scrollbar-width:none;-ms-overflow-style:none;scroll-behavior:smooth">
        {"".join(chips)}
      </div>
      <button id="{bar_id}-next" onclick="chipScroll('{bar_id}',1)" class="chip-arrow" aria-label="scroll right">&#8250;</button>
    </div>
  </div>
</div>
<style>
.filter-chip {{
  display:inline-flex;align-items:center;gap:5px;padding:6px 14px;border-radius:999px;
  border:1.5px solid #e5e7eb;background:#fff;font-size:.8rem;font-weight:600;
  color:#374151;cursor:pointer;white-space:nowrap;transition:all .15s;flex-shrink:0;
}}
.filter-chip:hover {{ border-color:var(--forest);color:var(--forest); }}
.filter-chip.chip-active {{ background:var(--forest);border-color:var(--forest);color:#fff; }}
.chip-count {{ opacity:.65;font-weight:500;font-size:.75rem; }}
.filter-chip.chip-active .chip-count {{ opacity:.8; }}
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
function chipScroll(id, dir) {{
  var el = document.getElementById(id);
  if (el) el.scrollBy({{left: dir * 200, behavior: 'smooth'}});
}}
</script>
<script>
function filterSub(btn, key) {{
  document.querySelectorAll('.filter-chip').forEach(b => b.classList.remove('chip-active'));
  btn.classList.add('chip-active');
  document.querySelectorAll('.listing-card').forEach(card => {{
    if (key === 'all' || card.dataset.sub === key) {{
      card.classList.remove('hidden');
    }} else {{
      card.classList.add('hidden');
    }}
  }});
  // Update grid count label
  const visible = document.querySelectorAll('.listing-card:not(.hidden)').length;
  const lbl = document.getElementById('result-count');
  if (lbl) lbl.textContent = visible + ' results';
}}
</script>"""

def listing_page(title, subtitle, meta_desc, items, cards_html, bg_color="var(--forest)", page_file="", extra_html="", filter_bar="", og_image=None):
    page_url = f"{SITE_URL}/{page_file}"
    _og_img = og_image or f"{SITE_URL}/og-image.jpg"
    return f"""{PAGE_HEAD}
  <title>{title} | ExploreSuriname.com</title>
  <meta name="description" content="{html_lib.escape(meta_desc)}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{page_url}">
  <meta property="og:title" content="{title} | ExploreSuriname.com">
  <meta property="og:description" content="{html_lib.escape(meta_desc)}">
  <meta property="og:image" content="{{_og_img}}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} | ExploreSuriname.com">
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
</head>
<body class="bg-gray-50">
{nav_html()}
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

def build_index(restaurants, hotels, news_preview):
    nature_cards   = "\n".join(nature_card(s)          for s in NATURE_SPOTS[:6])
    activity_cards = "\n".join(activity_card_rich(a)   for a in ACTIVITIES[:6])
    rest_cards     = "\n".join(poi_card(r, "cuisine")  for r in RESTAURANTS[:6])
    hotel_cards    = "\n".join(poi_card(h, "category") for h in HOTELS[:6])
    news_cards     = "\n".join(news_card_html(a, large=(i==0)) for i,a in enumerate(news_preview))
    more_btn = lambda href, label: f'<a href="{href}" class="inline-flex items-center gap-1 px-6 py-3 rounded-full text-sm font-semibold border-2 transition hover:opacity-80" style="border-color:var(--forest2);color:var(--forest2)">{label} &rarr;</a>'
    return f"""{PAGE_HEAD}
  <title>Explore Suriname | South America's Hidden Gem</title>
  <meta name="description" content="Plan your Suriname trip: rainforest lodges, Paramaribo restaurants, local tours, shopping and live SRD exchange rates. Your complete guide to South America's most unspoiled destination.">
  <link rel="canonical" href="{SITE_URL}/">
  <link rel="preload" as="image" href="https://images.unsplash.com/photo-1448375240586-882707db888b?w=1920&q=80">
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
      "url": "{SITE_URL}/favicon.svg",
      "width": 64,
      "height": 64
    }},
    "description": "Your complete travel and lifestyle guide to Suriname — hotels, restaurants, nature, activities and live SRD exchange rates.",
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
    "description": "Your complete travel and lifestyle guide to Suriname — hotels, restaurants, nature, activities and live SRD exchange rates.",
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
</head>
<body class="bg-white overflow-x-hidden">
{nav_html("home")}
<section class="relative min-h-screen flex items-center justify-center hero-bg"
  style="background-image:url('https://images.unsplash.com/photo-1448375240586-882707db888b?w=1920&q=80')">
  <div class="absolute inset-0" style="background:linear-gradient(to bottom,rgba(0,0,0,.15) 0%,rgba(0,0,0,.55) 60%,rgba(0,0,0,.82) 100%)"></div>
  <div class="relative z-10 text-center text-white px-5 max-w-4xl mx-auto" style="padding-top:5rem">
    <p class="text-xs font-semibold tracking-widest uppercase mb-6" style="color:var(--coral)">South America&apos;s Hidden Gem</p>
    <h1 class="serif font-black leading-tight mb-6" style="font-size:clamp(2.5rem,8vw,5.5rem)">The Amazon&apos;s<br>Best-Kept Secret</h1>
    <p class="text-xl font-light leading-relaxed mb-10 max-w-2xl mx-auto text-white/90">94% pristine rainforest. Unmatched biodiversity. Two UNESCO World Heritage Sites. Welcome to Suriname.</p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <a href="#nature" class="px-8 py-4 rounded-full font-semibold text-lg text-white hover:opacity-90 transition shadow-lg" style="background:var(--forest)">Start Exploring &#8595;</a>
      <a href="news.html" class="px-8 py-4 rounded-full font-semibold text-lg text-white border-2 hover:bg-white/10 transition" style="border-color:rgba(255,255,255,.6)">Latest News</a>
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
<section id="nature" class="py-24 bg-gray-50">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Pristine Wilderness</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Nature Like Nowhere Else</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname protects more of its original forest than any other country on earth.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{nature_cards}</div>
    <div class="text-center mt-10">{more_btn("nature.html", f"View all {len(NATURE_SPOTS) + len(SIGHTSEEING)} nature spots")}</div>
  </div>
</section>
<section id="activities" class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Adventures Await</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Things to Do</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">From deep jungle expeditions to cultural immersion.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{activity_cards}</div>
    <div class="text-center mt-10">{more_btn("activities.html", f"View all {len(ACTIVITIES) + len(ADVENTURES_BIZ)} activities")}</div>
  </div>
</section>
<section id="dining" class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Eat &amp; Drink</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Where to Eat</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname&apos;s cuisine is as diverse as its people — Creole, Hindustani, Javanese, Chinese and Maroon flavors.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{rest_cards}</div>
    <div class="text-center mt-10">{more_btn("restaurants.html", f"View all {len(RESTAURANTS)} restaurants")}</div>
  </div>
</section>
<section id="hotels" class="py-24" style="background:var(--mint)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Where to Stay</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Hotels &amp; Lodges</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">From 5-star riverside hotels to remote jungle lodges only reachable by canoe.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{hotel_cards}</div>
    <div class="text-center mt-10">{more_btn("hotels.html", f"View all {len(HOTELS)} hotels &amp; lodges")}</div>
  </div>
</section>
<section class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="flex items-end justify-between mb-10 flex-wrap gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest uppercase mb-2" style="color:var(--forest2)">Stay Informed</p>
        <h2 class="serif text-4xl font-bold text-gray-900">Latest from Suriname</h2>
      </div>
      <a href="news.html" class="hidden sm:inline-flex px-6 py-3 rounded-full text-white text-sm font-semibold hover:opacity-90 transition" style="background:var(--forest)">All News &rarr;</a>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">{news_cards}</div>
    <div class="text-center mt-8 sm:hidden">
      <a href="news.html" class="inline-flex px-6 py-3 rounded-full text-white text-sm font-semibold" style="background:var(--forest)">All Suriname News &rarr;</a>
    </div>
  </div>
</section>
{footer_html()}
</body>
</html>"""

def build_nature_page():
    nature_cards = "\n".join(nature_card(s) for s in NATURE_SPOTS)
    sight_cards  = "\n".join(poi_card(b) for b in SIGHTSEEING)
    all_cards    = nature_cards + "\n" + sight_cards
    # build filter bar from combined list (nature spots default to "nature-parks" subcat)
    combined_items = [{"subcat": s.get("subcat", "nature-parks")} for s in NATURE_SPOTS] + list(SIGHTSEEING)
    filter_bar_s = _filter_bar_html(combined_items, "sightseeing")
    total = len(NATURE_SPOTS) + len(SIGHTSEEING)
    return listing_page("Nature & Parks", f"{total} destinations across Suriname's pristine wilderness",
        f"Explore {total} nature reserves, national parks and rainforest destinations in Suriname. From Central Suriname Nature Reserve to Brownsberg — plan your eco-adventure.",
        NATURE_SPOTS, all_cards, page_file="nature.html", extra_html="", filter_bar=filter_bar_s, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG")

def build_activities_page():
    # Merge ACTIVITIES and ADVENTURES_BIZ sorted alphabetically by name
    tagged = (
        [(a["name"].lower(), "activity", a) for a in ACTIVITIES] +
        [(b["name"].lower(), "biz",      b) for b in ADVENTURES_BIZ]
    )
    tagged.sort(key=lambda x: x[0])
    all_cards = "\n".join(
        activity_card_rich(item) if kind == "activity" else poi_card(item)
        for _, kind, item in tagged
    )
    combined_items = [{"subcat": a.get("subcat", "tours-expeditions")} for a in ACTIVITIES] + list(ADVENTURES_BIZ)
    filter_bar_a = _filter_bar_html(combined_items, "adventure")
    total = len(ACTIVITIES) + len(ADVENTURES_BIZ)
    return listing_page("Activities", f"{total} things to do in Suriname",
        f"Discover {total} things to do in Suriname — jungle tours, river trips, birdwatching, kayaking and more. Find tours, eco-lodges and adventure operators in Paramaribo.",
        ACTIVITIES, all_cards, bg_color="var(--forest2)", page_file="activities.html", extra_html="", filter_bar=filter_bar_a, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg")

def build_restaurants_page(restaurants):
    cards = "\n".join(poi_card(r, "cuisine") for r in restaurants)
    fb    = _filter_bar_html(restaurants, "restaurant")
    return listing_page("Eat & Drink", f"{len(restaurants)} places to eat & drink in Suriname",
        f"Browse {len(restaurants)} restaurants, cafes, bars and fast food in Suriname. Find local Surinamese food, Asian cuisine, coffee shops and more.",
        restaurants, cards, bg_color="#7c3aed", page_file="restaurants.html", filter_bar=fb, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/9/94/2016_0624_Tjauw_min_moksie_meti_speciaal.jpg/1280px-2016_0624_Tjauw_min_moksie_meti_speciaal.jpg")

def build_hotels_page(hotels):
    cards = "\n".join(poi_card(h, "category") for h in hotels)
    fb    = _filter_bar_html(hotels, "hotel")
    return listing_page("Hotels & Lodges", f"{len(hotels)} places to stay in Suriname",
        f"Browse {len(hotels)} hotels, eco-lodges and jungle retreats in Suriname. From Paramaribo city hotels to remote river resorts — find your perfect stay.",
        hotels, cards, bg_color="#c05621", page_file="hotels.html", filter_bar=fb, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/0/07/Bigi_Pan_Nature_Reserve_%282719369111%29.jpg/1280px-Bigi_Pan_Nature_Reserve_%282719369111%29.jpg")

def build_shopping_page():
    cards = "\n".join(poi_card(b) for b in SHOPPING)
    fb    = _filter_bar_html(SHOPPING, "shopping")
    return listing_page("Shopping", f"{len(SHOPPING)} shops & stores in Suriname",
        f"Discover {len(SHOPPING)} shops in Suriname — supermarkets, malls, fashion, electronics, furniture, butchers and specialty stores in Paramaribo.",
        SHOPPING, cards, bg_color="#7c3aed", page_file="shopping.html", filter_bar=fb, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png")

def build_services_page():
    cards = "\n".join(poi_card(b) for b in SERVICES)
    fb    = _filter_bar_html(SERVICES, "service")
    return listing_page("Services", f"{len(SERVICES)} service providers in Suriname",
        f"Find {len(SERVICES)} service providers in Suriname — banks, beauty, health, fitness, education, telecom, real estate and more.",
        SERVICES, cards, bg_color="#0369a1", page_file="services.html", filter_bar=fb, og_image="https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png")

def build_currency_page(cme_rates, cme_live, cme_updated, cbvs_rates, cbvs_live, cbvs_updated):
    import json as _json
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")
    buy_json  = _json.dumps({r["currency"]: float(r["buy"])  for r in cme_rates})
    sell_json = _json.dumps({r["currency"]: float(r["sell"]) for r in cme_rates})

    # USD→SRD rate baked in for gold price SRD equivalent
    usd_buy_srd = next((float(r["buy"]) for r in cme_rates if r["currency"] == "USD"), 37.5)

    def badge(is_live):
        if is_live:
            return '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">&#9679; Live</span>'
        return '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">&#9675; Estimated</span>'

    cbvs_rows = ""
    for r in cbvs_rates:
        cbvs_rows += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 font-semibold text-gray-900 whitespace-nowrap">{r["flag"]} {r["currency"]}</td>'
            f'<td class="py-3 px-4 text-gray-500 text-sm">{html_lib.escape(r["name"])}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold text-gray-800">{r["buy"]}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold text-gray-800">{r["sell"]}</td>'
            '</tr>'
        )

    cme_rows = ""
    for r in cme_rates:
        cme_rows += (
            '<tr class="border-b border-gray-100 hover:bg-gray-50">'
            f'<td class="py-3 px-4 font-semibold text-gray-900 whitespace-nowrap">{r["flag"]} {r["currency"]}</td>'
            f'<td class="py-3 px-4 text-gray-500 text-sm">{html_lib.escape(r["name"])}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold" style="color:var(--forest2)">{r["buy"]}</td>'
            f'<td class="py-3 px-4 text-right font-mono font-bold" style="color:var(--coral)">{r["sell"]}</td>'
            '</tr>'
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
  <title>SRD Exchange Rates | Explore Suriname</title>
  <meta name="description" content="Live Surinamese Dollar (SRD) exchange rates updated 3x daily — USD, EUR, GBP and more from CBVS and CME. Includes a free currency converter.">
  <link rel="canonical" href="{SITE_URL}/currency.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/currency.html">
  <meta property="og:title" content="SRD Exchange Rates | Explore Suriname">
  <meta property="og:description" content="Live Surinamese Dollar (SRD) exchange rates updated 3x daily — USD, EUR, GBP and more from CBVS and CME.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="SRD Exchange Rates | Explore Suriname">
  <meta name="twitter:description" content="Live Surinamese Dollar (SRD) exchange rates updated 3x daily — USD, EUR, GBP and more from CBVS and CME.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("currency")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Currency Exchange</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">Surinamese Dollar (SRD) rates &mdash; updated 3&times; daily on business days</p>
  <p class="text-white/35 text-xs mt-3">&#128336; Page built: {updated_now}</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">
  <div class="rounded-2xl border border-amber-200 p-6 mb-8" style="background:#fffbeb">
    <p class="text-amber-900 text-sm leading-relaxed">
      <strong class="text-amber-800">&#128161; What&apos;s the difference?</strong>
      <strong>CBVS</strong> is the Central Bank of Suriname&apos;s official reference rate used for banking.
      <strong>CME</strong> (Cambio Money Exchange) shows cash rates at local exchange offices &mdash; what you actually get when exchanging banknotes.
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
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
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
      <div class="overflow-x-auto">
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
    </div>
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
      <div class="px-6 py-5 border-b border-gray-100">
        <div class="flex items-start justify-between gap-2">
          <div>
            <p class="font-bold text-gray-900 text-base">CME Cash Rates {badge(cme_live)}</p>
            <p class="text-gray-400 text-xs mt-0.5">Cambio Money Exchange &mdash; local market rate</p>
          </div>
          <a href="https://www.cme.sr" target="_blank" rel="noopener noreferrer"
             class="text-xs font-semibold shrink-0 hover:underline" style="color:var(--forest2)">cme.sr &#8599;</a>
        </div>
        <p class="text-gray-400 text-xs mt-2">&#128336; {html_lib.escape(cme_updated)}</p>
      </div>
      <div class="overflow-x-auto">
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
    </div>
  </div>
  <p class="text-center text-gray-400 text-xs mt-8 max-w-2xl mx-auto leading-relaxed px-4">
    Rates are for informational purposes only. Always confirm the current rate before transacting. Page auto-updates daily.
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
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
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
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">24h Change</p>
        <p id="gold-chg" class="text-xl font-bold font-mono text-gray-500">—</p>
      </div>
    </div>
    <p class="text-gray-400 text-xs mt-4">Suriname is one of the world&apos;s leading gold producers per capita. SRD equivalent uses today&apos;s CME USD buy rate ({usd_buy_srd:.2f}). Price refreshes on each page load.</p>
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
      var prev  = d.prev_close_price || price;
      var chg   = price - prev;
      var chgPct = prev ? (chg / prev * 100) : 0;
      document.getElementById('gold-usd').textContent  = '$' + price.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
      document.getElementById('gold-srd').textContent  = (price * USD_SRD).toLocaleString('en-US',{{minimumFractionDigits:0,maximumFractionDigits:0}}) + ' SRD';
      document.getElementById('gold-usdg').textContent = '$' + (price / 31.1035).toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
      var chgEl = document.getElementById('gold-chg');
      var sign  = chg >= 0 ? '+' : '';
      chgEl.textContent = sign + chg.toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}}) + ' (' + sign + chgPct.toFixed(2) + '%)';
      chgEl.style.color = chg >= 0 ? 'var(--forest2)' : 'var(--coral)';
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

def build_news(articles):
    updated   = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")
    total     = len(articles)
    feat_html = "\n".join(news_card_html(a, large=True) for a in articles[:3])
    rest_html = "\n".join(news_card_html(a) for a in articles[3:30])
    return f"""{PAGE_HEAD}
  <title>Suriname News | Explore Suriname</title>
  <meta name="description" content="Suriname news from De Ware Tijd, Starnieuws, Waterkant and more. Business, politics, culture and travel from Paramaribo.">
  <link rel="canonical" href="{SITE_URL}/news.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/news.html">
  <meta property="og:title" content="Suriname News | Explore Suriname">
  <meta property="og:description" content="Suriname news from De Ware Tijd, Starnieuws, Waterkant and more.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname News | Explore Suriname">
  <meta name="twitter:description" content="Suriname news from De Ware Tijd, Starnieuws, Waterkant and more.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("news")}
<div class="pt-16"></div>
<div class="text-white text-center py-16" style="background:var(--forest)">
  <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Suriname News</p>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Latest from Suriname</h1>
  <p class="text-white/55 text-sm">{updated} &middot; {total} stories from {len(FEEDS)} sources</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-20">
  {ad_slot("Top Banner Ad — Replace with Google AdSense code")}
  <h2 class="text-xs font-bold uppercase tracking-widest mb-5" style="color:var(--forest2)">Top Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">{feat_html}</div>
  {ad_slot("Mid-Page Ad — Replace with Google AdSense code")}
  <h2 class="text-xs font-bold uppercase tracking-widest mb-5 mt-6 text-gray-500">All Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{rest_html}</div>
</main>
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

def build_listing_page(slug, b):
    raw_name = b.get("name", slug)
    desc     = b.get("description", "")
    address  = b.get("address", "")
    phone    = b.get("phone", "")
    email    = b.get("email", "")
    category = b.get("category", "")
    location = b.get("location", "Paramaribo")
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
    # Pull rich description from JSON cache if not stored in _BIZ
    if not desc:
        desc = _JSON_DESCS.get(slug, "")
    if desc:
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
    og_img     = img if img else SITE_URL + "/og-image.jpg"

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

    head = (
        PAGE_HEAD +
        "\n  <title>" + name_e + " | ExploreSuriname.com</title>"
        "\n  <meta name=\"description\" content=\"" + desc_e + "\">"
        "\n  <link rel=\"canonical\" href=\"" + page_url + "\">"
        "\n  <meta property=\"og:type\" content=\"business.business\">"
        "\n  <meta property=\"og:site_name\" content=\"Explore Suriname\">"
        "\n  <meta property=\"og:url\" content=\"" + page_url + "\">"
        "\n  <meta property=\"og:title\" content=\"" + name_e + " | ExploreSuriname.com\">"
        "\n  <meta property=\"og:description\" content=\"" + desc_e + "\">"
        "\n  <meta property=\"og:image\" content=\"" + og_img + "\">"
        "\n  <meta name=\"twitter:card\" content=\"summary_large_image\">"
        "\n  <meta name=\"twitter:title\" content=\"" + name_e + " | ExploreSuriname.com\">"
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

    return head + hero + main + "\n" + footer_html(prefix="../../") + "\n</body>\n</html>"


def build_activity_listing_page(act, slug):
    """Generate an individual detail page for an ACTIVITIES entry."""
    name    = act.get("name", slug)
    desc    = act.get("desc", "")
    img     = act.get("image", "")
    ext_url = act.get("url", "")
    icon    = act.get("icon", "\U0001f33f")

    name_e     = html_lib.escape(name)
    desc_e     = html_lib.escape(desc[:160]) if desc else html_lib.escape(name + " — ExploreSuriname.com")
    page_url   = SITE_URL + "/listing/" + slug + "/"
    maps_q     = urllib.parse.quote(name + ", Suriname")
    maps_embed = "https://maps.google.com/maps?q=" + maps_q + "&output=embed&hl=en"
    maps_link  = "https://www.google.com/maps/search/?api=1&query=" + maps_q
    og_img     = img if img else SITE_URL + "/og-image.jpg"

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
        "description": desc[:300] if desc else name + " — activity in Suriname.",
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
    desc_e     = html_lib.escape(desc[:160]) if desc else html_lib.escape(name + " — ExploreSuriname.com")
    page_url   = SITE_URL + "/listing/" + slug + "/"
    maps_q     = urllib.parse.quote(name + ", Suriname")
    maps_embed = "https://maps.google.com/maps?q=" + maps_q + "&output=embed&hl=en"
    maps_link  = "https://www.google.com/maps/search/?api=1&query=" + maps_q
    og_img     = img if img else SITE_URL + "/og-image.jpg"


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
        "description": desc if desc else name + " — nature attraction in Suriname.",
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
        + '\n  <title>' + name_e + ' | ExploreSuriname.com</title>\n  <meta name="description" content="'
        + desc_e
        + '">\n  <link rel="canonical" href="' + page_url
        + '">\n  <meta property="og:type" content="website">\n  <meta property="og:site_name" content="Explore Suriname">\n  <meta property="og:url" content="'
        + page_url
        + '">\n  <meta property="og:title" content="' + name_e
        + ' | ExploreSuriname.com">\n  <meta property="og:description" content="'
        + desc_e
        + '">\n  <meta property="og:image" content="' + og_img
        + '">\n  <meta name="twitter:card" content="summary_large_image">\n  <meta name="twitter:title" content="'
        + name_e + ' | ExploreSuriname.com">\n  <meta name="twitter:image" content="'
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

def build_sitemap(biz_slugs, act_slugs, nat_slugs):
    """Generate sitemap.xml covering all pages and listing URLs."""
    today = datetime.now(SR_TZ).strftime("%Y-%m-%d")

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
        ("news.html",       "0.7", "daily"),
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

    for slug in biz_slugs:
        loc = SITE_URL + "/listing/" + slug + "/"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.7</priority>\n"
            f"  </url>"
        )

    for slug in act_slugs + nat_slugs:
        loc = SITE_URL + "/listing/" + slug + "/"
        urls.append(
            f"  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>monthly</changefreq>\n"
            f"    <priority>0.6</priority>\n"
            f"  </url>"
        )

    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(urls)
            + "\n\n</urlset>\n")


def build_robots():
    """Return robots.txt content."""
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"


# ── Conditions page (weather + tides + sunrise/sunset) ──────────────────────

def build_conditions_page(tides_extremes, tides_live, tides_updated):
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")

    if tides_extremes:
        from collections import defaultdict
        by_day = defaultdict(list)
        for ex in tides_extremes:
            dt  = datetime.fromtimestamp(ex["dt"], tz=SR_TZ)
            day = dt.strftime("%A, %d %b")
            by_day[day].append({
                "type":   ex["type"],
                "time":   dt.strftime("%H:%M SR"),
                "height": f"{ex['height']:.2f} m",
                "icon":   "\U0001f53c" if ex["type"] == "High" else "\U0001f53d",
            })

        tide_rows = ""
        for day, events in list(by_day.items())[:3]:
            for ev in events:
                tide_rows += (
                    '<tr class="border-b border-gray-100">'
                    f'<td class="py-3 px-4 text-gray-500 text-sm">{day}</td>'
                    f'<td class="py-3 px-4 font-semibold">{ev["icon"]} {ev["type"]} Tide</td>'
                    f'<td class="py-3 px-4 font-mono font-bold">{ev["time"]}</td>'
                    f'<td class="py-3 px-4 text-right font-mono text-gray-700">{ev["height"]}</td>'
                    '</tr>'
                )

        tide_badge = ('<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">&#9679; Live</span>'
                      if tides_live else
                      '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">&#9675; Cached</span>')

        tides_html = f"""
<div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
  <div class="px-6 py-5 border-b border-gray-100">
    <div class="flex items-center justify-between">
      <div>
        <p class="font-bold text-gray-900 text-base">&#127754; Tides &mdash; Paramaribo {tide_badge}</p>
        <p class="text-gray-400 text-xs mt-0.5">Suriname River mouth &mdash; predictions from WorldTides</p>
      </div>
    </div>
    <p class="text-gray-400 text-xs mt-2">&#128336; {html_lib.escape(tides_updated)}</p>
  </div>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead><tr class="bg-gray-50 text-left">
        <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Date</th>
        <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Tide</th>
        <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Time (SR)</th>
        <th class="py-3 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Height</th>
      </tr></thead>
      <tbody>{tide_rows}</tbody>
    </table>
  </div>
</div>"""
    else:
        tides_html = """
<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 text-center">
  <p class="text-5xl mb-4">&#127754;</p>
  <h3 class="font-bold text-gray-900 mb-2">Tide Predictions</h3>
  <p class="text-gray-500 text-sm max-w-md mx-auto">Tide data requires a <a href="https://www.worldtides.info" target="_blank" class="underline" style="color:var(--forest2)">WorldTides API key</a>. Set the <code class="bg-gray-100 px-1 rounded">WORLDTIDES_KEY</code> GitHub Actions secret to enable tidal forecasts for fishermen and sailors.</p>
</div>"""

    return f"""{PAGE_HEAD}
  <title>Weather &amp; Forecast | Explore Suriname</title>
  <meta name="description" content="Live weather, tides and sunrise/sunset for Suriname. Essential for fishermen, sailors and outdoor enthusiasts in Paramaribo.">
  <link rel="canonical" href="{SITE_URL}/conditions.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/conditions.html">
  <meta property="og:title" content="Weather &amp; Forecast | Explore Suriname">
  <meta property="og:description" content="Live weather, tides and sunrise/sunset for Suriname.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Weather &amp; Forecast | Explore Suriname">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("forecast")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Today in Suriname</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">Live weather, sunrise &amp; sunset, and tidal forecasts for Paramaribo</p>
  <p class="text-white/35 text-xs mt-3">&#128336; Page built: {updated_now}</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">

  <!-- Weather -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-8 mb-6">
    <div class="flex items-start justify-between mb-6">
      <div>
        <h2 class="serif text-2xl font-bold text-gray-900">&#127777;&#65039; Weather &mdash; Paramaribo</h2>
        <p class="text-gray-400 text-sm mt-1">Live via <a href="https://open-meteo.com" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">Open-Meteo</a> &mdash; free, no API key required</p>
      </div>
      <span id="wx-badge" class="text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 shrink-0 ml-4">Loading&hellip;</span>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
      <div class="rounded-xl p-4" style="background:var(--mint)">
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
        <p class="text-xs text-gray-400 mt-1">Relative humidity</p>
      </div>
      <div class="rounded-xl p-4 bg-gray-50">
        <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Wind</p>
        <p id="wx-wind" class="text-3xl font-bold font-mono text-gray-900">&mdash;</p>
        <p id="wx-wdir" class="text-xs text-gray-400 mt-1">&mdash;</p>
      </div>
    </div>
    <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-widest mb-4">7-Day Forecast</h3>
    <div id="wx-forecast" class="grid grid-cols-7 gap-2"></div>
    <p class="text-gray-400 text-xs text-center mt-4">Data from Open-Meteo &mdash; free, open-source weather API. Refreshes on every page load.</p>
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
    <p class="text-gray-400 text-xs text-center mt-4">Data from <a href="https://sunrise-sunset.org" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">sunrise-sunset.org</a> &mdash; Paramaribo (5.85&deg;N, 55.20&deg;W)</p>
  </div>

  <!-- Fishermen's Corner: Tides -->
  <div class="mb-6">
    <div class="flex items-center gap-3 mb-4">
      <h2 class="serif text-2xl font-bold text-gray-900">&#9973;&#65039; Fishermen&apos;s Corner</h2>
      <span class="text-xs font-semibold px-2 py-0.5 rounded-full text-white" style="background:var(--forest2)">For mariners &amp; fishers</span>
    </div>
    {tides_html}
    <p class="text-gray-400 text-xs mt-3">Tide heights are relative to lowest astronomical tide (LAT). Suriname&apos;s coastal tidal range is approximately 2&ndash;3 m. Always verify with local authorities before heading out.</p>
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

(function(){{
  var url = 'https://api.open-meteo.com/v1/forecast?latitude=5.852&longitude=-55.203'
    + '&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m'
    + '&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max'
    + '&wind_speed_unit=kmh&timezone=America%2FParamaribo&forecast_days=7';
  fetch(url).then(function(r){{return r.json();}}).then(function(d){{
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
    var badge = document.getElementById('wx-badge');
    badge.innerHTML = '&#9679; Live';
    badge.className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800 shrink-0 ml-4';
    var fc = d.daily, fbox = document.getElementById('wx-forecast');
    fbox.innerHTML = '';
    for(var i=0;i<7;i++){{
      var dt = new Date(fc.time[i]);
      var dn = i===0?'Today':DAYS[dt.getDay()];
      var w  = WMO[fc.weather_code[i]]||['&#127777;',''];
      var rn = fc.precipitation_probability_max[i]||0;
      fbox.innerHTML += '<div class="flex flex-col items-center text-center rounded-xl p-2" style="background:#f8fafc">'
        + '<p class="text-xs font-semibold text-gray-500">'+dn+'</p>'
        + '<p class="text-2xl my-1">'+w[0]+'</p>'
        + '<p class="text-xs font-bold text-gray-900">'+Math.round(fc.temperature_2m_max[i])+'°</p>'
        + '<p class="text-xs text-gray-400">'+Math.round(fc.temperature_2m_min[i])+'°</p>'
        + (rn>20?'<p class="text-xs text-blue-500 mt-0.5">&#128167;'+rn+'%</p>':'')
        + '</div>';
    }}
  }}).catch(function(){{
    document.getElementById('wx-badge').textContent = 'Unavailable';
    document.getElementById('wx-badge').className = 'text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-500 shrink-0 ml-4';
  }});
}})();

(function(){{
  fetch('https://api.sunrise-sunset.org/json?lat=5.852&lng=-55.203&formatted=0')
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
}})();
</script>
{footer_html()}
</body>
</html>"""


# ── Flights page (OpenSky — arrivals/departures at PBM) ─────────────────────

def build_flights_page(arrivals, departures, updated):
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")

    def flight_rows(flights, direction):
        if not flights:
            col = "From" if direction == "arrival" else "To"
            return (f'<tr><td colspan="4" class="py-8 text-center text-gray-400 text-sm">'
                    f'No recent {direction}s found in OpenSky data</td></tr>')
        rows = ""
        for f in flights:
            rows += (
                '<tr class="border-b border-gray-100 hover:bg-gray-50">'
                f'<td class="py-3 px-4 font-mono font-bold text-gray-900 whitespace-nowrap">{html_lib.escape(f["flight"])}</td>'
                f'<td class="py-3 px-4 text-gray-700 text-sm">{html_lib.escape(f["airline"])}</td>'
                f'<td class="py-3 px-4 text-gray-600 text-sm">{html_lib.escape(f["airport"])}</td>'
                f'<td class="py-3 px-4 text-right font-mono text-gray-700 text-sm whitespace-nowrap">{html_lib.escape(f["time"])}</td>'
                '</tr>'
            )
        return rows

    arr_rows = flight_rows(arrivals,  "arrival")
    dep_rows = flight_rows(departures, "departure")

    def count_badge(n):
        return (f'<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full '
                f'bg-green-100 text-green-800">{n} flights</span>') if n else ""

    return f"""{PAGE_HEAD}
  <title>Flights &mdash; Paramaribo (PBM) | Explore Suriname</title>
  <meta name="description" content="Recent arrivals and departures at Johan Adolf Pengel International Airport (PBM), Paramaribo, Suriname. Updated every 30 minutes.">
  <link rel="canonical" href="{SITE_URL}/flights.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/flights.html">
  <meta property="og:title" content="Flights &mdash; Paramaribo Airport | Explore Suriname">
  <meta property="og:description" content="Recent arrivals and departures at Johan Adolf Pengel International Airport (PBM).">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Flights &mdash; Paramaribo Airport | Explore Suriname">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("flights")}
<div class="pt-16"></div>
<div class="text-white py-16 text-center" style="background:var(--forest)">
  <a href="index.html" class="inline-flex items-center gap-1 text-white/60 text-sm hover:text-white mb-8 transition">&#8592; Back to Home</a>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">&#9992;&#65039; Flights</h1>
  <p class="text-white/60 text-lg max-w-xl mx-auto px-4">Johan Adolf Pengel International Airport &mdash; Paramaribo (PBM / SMJP)</p>
  <p class="text-white/35 text-xs mt-3">&#128336; Updated: {html_lib.escape(updated)}</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-24">

  <div class="rounded-2xl border border-blue-100 p-5 mb-8" style="background:#eff6ff">
    <p class="text-blue-900 text-sm leading-relaxed">
      <strong class="text-blue-800">&#9992;&#65039; About this data:</strong>
      Flight data is sourced from <a href="https://opensky-network.org" target="_blank" rel="noopener" class="underline">OpenSky Network</a>, a community-driven open aviation database (CC BY 4.0).
      Times are actual transponder signals converted to Suriname time (SR, UTC&minus;3). Data covers the last 48 hours and refreshes every 30 minutes with the site rebuild.
      For real-time tracking, visit <a href="https://www.flightradar24.com/5.85,-55.20/10" target="_blank" rel="noopener" class="underline">Flightradar24</a>.
    </p>
  </div>

  <!-- Arrivals -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
    <div class="px-6 py-5 border-b border-gray-100">
      <p class="font-bold text-gray-900 text-base">&#9650; Arrivals &mdash; Paramaribo (PBM) {count_badge(len(arrivals))}</p>
      <p class="text-gray-400 text-xs mt-0.5">Flights that landed at Johan Adolf Pengel in the past 48 hours</p>
    </div>
    <div class="overflow-x-auto">
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
  </div>

  <!-- Departures -->
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mb-6">
    <div class="px-6 py-5 border-b border-gray-100">
      <p class="font-bold text-gray-900 text-base">&#9660; Departures &mdash; Paramaribo (PBM) {count_badge(len(departures))}</p>
      <p class="text-gray-400 text-xs mt-0.5">Flights that departed Johan Adolf Pengel in the past 48 hours</p>
    </div>
    <div class="overflow-x-auto">
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
  </div>

  <p class="text-center text-gray-400 text-xs mt-4 max-w-2xl mx-auto leading-relaxed px-4">
    Data from <a href="https://opensky-network.org" target="_blank" rel="noopener" class="hover:underline" style="color:var(--forest2)">OpenSky Network</a> under CC BY 4.0.
    Data may be 30&ndash;90 min delayed. Not suitable for operational flight planning.
  </p>

</main>
{footer_html()}
</body>
</html>"""


# ── Main entry point ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("ExploreSuriname generator starting...")

    articles = fetch_articles()
    cme_rates,  cme_live,  cme_updated  = fetch_cme_rates()
    cbvs_rates, cbvs_live, cbvs_updated = fetch_cbvs_rates()
    tides_extremes, tides_live, tides_updated = fetch_worldtides()
    arrivals, departures, flights_updated     = fetch_opensky_flights()

    pages = {
        "index.html":       build_index(RESTAURANTS, HOTELS, articles),
        "nature.html":      build_nature_page(),
        "activities.html":  build_activities_page(),
        "restaurants.html": build_restaurants_page(RESTAURANTS),
        "hotels.html":      build_hotels_page(HOTELS),
        "shopping.html":    build_shopping_page(),
        "services.html":    build_services_page(),
        "currency.html":    build_currency_page(cme_rates, cme_live, cme_updated,
                                                cbvs_rates, cbvs_live, cbvs_updated),
        "conditions.html":  build_conditions_page(tides_extremes, tides_live, tides_updated),
        "flights.html":     build_flights_page(arrivals, departures, flights_updated),
        "news.html":        build_news(articles),
    }

    for fname, html in pages.items():
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  OK  {fname}")

    os.makedirs("listing", exist_ok=True)
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

    print("Done.")
