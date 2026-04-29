#!/usr/bin/env python3
"""
ExploreSuriname.com - Full Tourism & News Site Generator
Generates: index.html, nature.html, activities.html,
           restaurants.html, hotels.html, currency.html, news.html
Run daily via GitHub Actions.
"""

import feedparser
import html as html_lib
import re, os, json
import urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

SITE_URL       = "https://exploresuriname.com"
CONTACT_EMAIL  = "surinamedomains@gmail.com"
SR_TZ          = timezone(timedelta(hours=-3))   # Suriname time (UTC-3, no DST)
YEAR           = datetime.now(SR_TZ).year
MAX_PER_FEED   = 10

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
     "image": "",
     "fact": "Leatherback & green turtles nest here", "url": "https://en.wikipedia.org/wiki/Wia-Wia_Nature_Reserve"},
    {"name": "Commewijne River", "badge": "River Dolphins & Plantations",
     "desc": "A scenic river just across from Paramaribo, famous for river dolphin sightings, historic plantation ruins and Fort Nieuw Amsterdam.",
     "tags": ["Dolphins", "History", "Easy Access"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg",
     "fact": "River dolphins seen year-round", "url": "https://www.google.com/search?q=commewijne+river+tour+suriname"},
    {"name": "Upper Suriname River", "badge": "Maroon Heritage",
     "desc": "Journey upriver through dense jungle to Maroon villages of the Saramacca and Matawai peoples. Stay in traditional lodges and experience a living ancient culture.",
     "tags": ["Maroon Culture", "River", "Multi-day"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg",
     "fact": "Ancient Afro-Surinamese cultures", "url": "https://www.google.com/search?q=upper+suriname+river+tour"},
    {"name": "Tafelberg", "badge": "Remote Tepui",
     "desc": "A flat-topped mountain rising dramatically from the rainforest, harbouring unique plant species found nowhere else on earth.",
     "tags": ["Tepui", "Expedition", "Unique Flora"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Tafelberg_Suriname.jpg/1280px-Tafelberg_Suriname.jpg",
     "fact": "Endemic species above the clouds", "url": "https://www.google.com/search?q=tafelberg+suriname+expedition"},
    {"name": "Fort Nieuw Amsterdam", "badge": "Colonial History",
     "desc": "An 18th-century star-shaped fort at the confluence of the Suriname and Commewijne rivers. Now an open-air museum.",
     "tags": ["History", "Museum", "Easy Access"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Cannon_near_Fort_Nieuw_Amsterdam_in_Suriname_%2830451879073%29.jpg/1280px-Cannon_near_Fort_Nieuw_Amsterdam_in_Suriname_%2830451879073%29.jpg",
     "fact": "18th-century Dutch fortification", "url": "https://www.google.com/search?q=fort+nieuw+amsterdam+suriname"},
    {"name": "Sipaliwini Savanna", "badge": "Far South Wilderness",
     "desc": "An isolated savanna near the Brazilian border. Home to giant anteaters, pumas and pristine black-water rivers.",
     "tags": ["Remote", "Savanna", "Wildlife"],
     "image": "",
     "fact": "Accessible only by small aircraft", "url": "https://www.google.com/search?q=sipaliwini+savanna+suriname"},
    {"name": "Palumeu – Trio Village", "badge": "Indigenous Culture",
     "desc": "Deep in the southern jungle, the Trio indigenous village of Palumeu offers a rare window into a way of life unchanged for generations.",
     "tags": ["Indigenous", "Remote", "Cultural"],
     "image": "",
     "fact": "Accessible by charter flight only", "url": "https://www.mets-suriname.com/"},
    {"name": "Colakreek", "badge": "Local Favourite",
     "desc": "A beautiful freshwater creek just outside Paramaribo, perfect for swimming and picnicking surrounded by jungle.",
     "tags": ["Swimming", "Easy Access", "Local Favourite"],
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg",
     "fact": "30 min from Paramaribo city centre", "url": "https://www.google.com/search?q=colakreek+suriname"},
]

ACTIVITIES = [
    {"icon": "🌿", "name": "Jungle Trekking",
     "desc": "Multi-day guided expeditions through primary rainforest with expert Amerindian guides.",
     "url": "https://www.mets-suriname.com/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Leo_val_brownsberg.JPG/1280px-Leo_val_brownsberg.JPG"},
    {"icon": "🛶", "name": "River Canoe Tours",
     "desc": "Glide through the Amazon basin on traditional dugout canoes, spotting caimans and river dolphins.",
     "url": "https://www.google.com/search?q=river+canoe+tour+suriname",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9c/Atjoni_%2833496718666%29.jpg/1280px-Atjoni_%2833496718666%29.jpg"},
    {"icon": "🦜", "name": "Bird Watching",
     "desc": "Suriname is a birder's paradise — spot 700+ species including scarlet macaws and harpy eagles.",
     "url": "https://www.google.com/search?q=bird+watching+tour+suriname",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Ara_ararauna_Luc_Viatour.jpg/1280px-Ara_ararauna_Luc_Viatour.jpg"},
    {"icon": "🏘️", "name": "Indigenous Village Tours",
     "desc": "Visit Trio and Wayana indigenous communities in the deep interior, preserving ancient traditions.",
     "url": "https://www.mets-suriname.com/",
     "image": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=600&q=80"},
    {"icon": "🥁", "name": "Maroon Village Tours",
     "desc": "Experience the living culture of the Saramacca and Matawai Maroon peoples — music, craft and history.",
     "url": "https://www.google.com/search?q=maroon+village+tour+suriname",
     "image": "https://images.unsplash.com/photo-1504704911898-68304a7d2807?w=600&q=80"},
    {"icon": "🏙️", "name": "Paramaribo City Walk",
     "desc": "Explore the UNESCO-listed historic inner city on foot — the only wooden colonial city in the Americas.",
     "url": "https://whc.unesco.org/en/list/940/",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/Paramaribo_city_collage.png/1280px-Paramaribo_city_collage.png"},
    {"icon": "🏊️", "name": "Natural Swimming",
     "desc": "Take a dip in crystal-clear jungle rivers and natural rock pools at Colakreek and Brownsberg.",
     "url": "https://www.google.com/search?q=colakreek+brownsberg+swimming+suriname",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Suriname_Colakreek.jpg/1280px-Suriname_Colakreek.jpg"},
    {"icon": "🐢", "name": "Turtle Watching",
     "desc": "Witness giant leatherback sea turtles nesting on Suriname's Atlantic coast at Galibi or Wia Wia.",
     "url": "https://en.wikipedia.org/wiki/Galibi_Nature_Reserve",
     "image": "https://upload.wikimedia.org/wikipedia/commons/9/95/Dermochelys_coriacea_%282719177753%29.jpg"},
    {"icon": "🐬", "name": "River Dolphin Watching",
     "desc": "Spot the rare freshwater boto dolphins on a boat tour along the scenic Commewijne River.",
     "url": "https://www.google.com/search?q=dolphin+watching+commewijne+river+suriname",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e6/Sotalia_fluviatilis_boto_cinza.jpg/1280px-Sotalia_fluviatilis_boto_cinza.jpg"},
    {"icon": "🎨", "name": "Maroon Art & Craft",
     "desc": "Watch master craftsmen carve intricate Maroon woodwork and weave traditional textile art.",
     "url": "https://www.google.com/search?q=maroon+art+craft+workshop+suriname",
     "image": "https://images.unsplash.com/photo-1515186813671-4b46ca4a1cff?w=600&q=80"},
    {"icon": "🎣", "name": "Sport Fishing",
     "desc": "Fish for piranha, arapaima and peacock bass in jungle rivers and reservoirs.",
     "url": "https://www.google.com/search?q=sport+fishing+suriname",
     "image": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&q=80"},
    {"icon": "🏛️", "name": "Colonial Plantation Tours",
     "desc": "Cycle or boat through the Commewijne River district, visiting historic coffee and cacao plantations.",
     "url": "https://www.google.com/search?q=plantation+tour+commewijne+suriname",
     "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6c/Br%C3%BCckeStolkertsijver.jpeg/1280px-Br%C3%BCckeStolkertsijver.jpeg"},
    {"icon": "🍽️", "name": "Surinamese Cooking Class",
     "desc": "Learn to cook traditional Creole, Hindustani and Javanese dishes with a local Paramaribo family.",
     "url": "https://www.google.com/search?q=cooking+class+suriname+paramaribo",
     "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&q=80"},
    {"icon": "🚵🏻", "name": "ATV & 4x4 Interior Tours",
     "desc": "Explore jungle trails, gold mining areas and remote villages by ATV or 4x4.",
     "url": "https://www.google.com/search?q=atv+4x4+tour+suriname",
     "image": "https://images.unsplash.com/photo-1533130061792-64b345e4a833?w=600&q=80"},
    {"icon": "🌊", "name": "Kayaking & Paddling",
     "desc": "Paddle through mangroves, jungle rivers and lake areas on guided or self-guided kayak tours.",
     "url": "https://www.google.com/search?q=kayaking+suriname",
     "image": "https://images.unsplash.com/photo-1502933691298-84fc14542831?w=600&q=80"},
    {"icon": "🌌", "name": "Jungle Stargazing",
     "desc": "Zero light pollution deep in the interior delivers some of the world's most incredible night skies.",
     "url": "https://www.google.com/search?q=jungle+camp+overnight+suriname",
     "image": "https://images.unsplash.com/photo-1419242902214-272b3f66ee7a?w=600&q=80"},
]

# -- Business listings (hardcoded from exploresuriname_listings.json) ---------

_BIZ = {
    '9173': {"name": 'Tulip Supermarkt', "location": 'Paramaribo', "address": 'Tourtonnelaan 133-135, Paramaribo, Suriname', "phone": '+597 521060', "website": 'www.amazoneretail.com'},
    'a-la-john': {"name": 'A La John', "location": 'Paramaribo', "address": 'verlengde gemenelands weg 192, Paramaribo, Suriname', "phone": '+597 715-1821', "website": ''},
    'ac-bar-restaurant': {"name": 'AC bar & restaurant', "location": 'Paramaribo', "address": 'Anamoestraat #53', "phone": '+597 459-394', "website": ''},
    'afobaka-resort': {"name": 'Afobaka Resort', "location": 'Brokopondo', "address": 'Afobaka Resort, Brokopondo, Suriname', "phone": '868-5636', "website": ''},
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
    'huub-explorer-tours': {"name": 'Huub Explorer Tours', "location": 'Paramaribo', "address": 'Paramaribo, Suriname', "phone": '+597 826-4189', "website": ''},
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
    'plantage-frederiksdorp': {"name": 'Plantage Frederiksdorp', "location": 'Commewijne', "address": 'Frederiksdorp 1, Margrita, Suriname', "phone": '820-0359', "website": ''},
    'readytex-souvenirs-and-crafts': {"name": 'Readytex Souvenirs and Crafts', "location": 'Paramaribo', "address": 'Maagdenstraat 44, Paramaribo, Suriname', "phone": '893-3060', "website": 'www.readytexcrafts.com/'},
    'recreatie-oord-carolina-kreek': {"name": 'Recreatie Oord Carolina Kreek', "location": 'Para', "address": 'Sabakoe, Suriname', "phone": '853-2977', "website": ''},
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
    'tio-boto-eco-resort': {"name": 'Tio Boto Eco Resort', "location": 'Paramaribo', "address": 'Parrijsstraat 10', "phone": '+597 875-8790', "website": ''},
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
    "courtyard-by-marriott":          "",
    "eco-resort-miano":               "",
    "holland-lodge":                  "",
    "hotel-palacio":                  "https://irp.cdn-website.com/b0c3c22b/dms3rep/multi/Palacio-exterior-street.jpg",
    "torarica-resort":                "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/The_Torarica_-_Paramaribo%2C_Suriname.jpg/1280px-The_Torarica_-_Paramaribo%2C_Suriname.jpg",
    "royal-breeze-hotel-paramaribo":  "",
    "taman-indah-resort":             "",
    "tiny-house-tropical-appartment": "",
    "waterland-suites":               "",
    "zeelandia-suites":               "",
    "the-golden-truly-hotel":         "",
    # ── Restaurants: official website photos ─────────────────────────────────
    "zus-zo-cafe":                    "https://www.zusenzosuriname.com/wp-content/uploads/2025/12/IMG_0310-scaled.jpeg",
    "goe-thai-noodle-bar":            "https://www.goe.sr/wp-content/uploads/2020/07/home-700-inter.png",
    # Restaurants: Unsplash fallbacks
    "a-la-john":                      "",
    "ac-bar-restaurant":              "",
    "baka-foto-restaurant":           "",
    "bar-zuid":                       "",
    "bori-tori":                      "",
    "chi-min":                        "",
    "de-spot":                        "",
    "de-verdieping":                  "",
    "el-patron-latin-grill":          "",
    "elines-pizza":                   "",
    "hard-rock-cafe-suriname":        "",
    "joey-ds":                        "",
    "kasan-snacks":                   "",
    "las-tias":                       "",
    "mickis-palace-noord":            "",
    "mickis-palace-zuid":             "",
    "mingle-paramaribo":              "",
    "moments-restaurant":             "",
    "pane-e-vino":                    "",
    "pannekoek-en-poffertjes-cafe":   "",
    "passion-food-and-wines":         "https://impro.usercontent.one/appid/hostnetWsb/domain/passiefoodandwines.com/media/passiefoodandwines.com/onewebmedia/picture-120044.jpg?etag=undefined&sourceContentType=image%2Fjpeg&quality=85",
    "rogom-farm-nv":                  "",
    "souposo":                        "",
    "sushi-ya":                       "",
    "the-coffee-box":                 "",
    "zeg-ijsje":                      "",
    "julias-food":                    "",
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
    "tio-boto-eco-resort":            "",
    # ── Shopping: official photos ─────────────────────────────────────────────
    "hermitage-mall":                 "https://hermitage-mall.com/wp-content/uploads/2018/03/HermitageMall-building.jpg",
    "lilis":                          "https://cdn.shopify.com/s/files/1/0526/9137/0149/files/Bridal_2a85f0ad-2db8-4a8a-ac54-3e090625d4de.jpg",
    "suraniyat":                      "https://images.squarespace-cdn.com/content/v1/65207f08df58fe10d1fab14f/20be6ae2-e0a4-4f62-a609-dcb80ea7e0ef/IMG_0922.jpg",
    "readytex-souvenirs-and-crafts":  "https://www.readytexcrafts.com/wp-content/uploads/2021/03/sigaar.jpg",
    "kirpalani":                      "https://www.kirpalani.com/media/wysiwyg/2026/Subcatmaart2026/Electonica.webp",
    "international-mall-of-suriname": "",
    "papillon-crafts":                "",
    "woodwonders-suriname":           "",
    "switi-momenti-candles-crafts":   "",
    "talking-prints-concept-store":   "",
    "dj-liquor-store":                "",
    "from-me-to-me":                  "",
    "galaxy":                         "",
    "divergent-body-jewelry":         "",
    "unlocked-candles":               "",
    "the-uma-store":                  "",
    "the-old-attic":                  "",
    "bed-bath-more-bbm":              "",
    "sleeqe":                         "",
    "smoothieskin":                   "",
    "honeycare":                      "",
    "shlx-collection":                "",
    # ── Services: official / contextual photos ────────────────────────────────
    "timeless-barber-and-nail-shop":  "https://timelessbarbershop.sr/wp-content/uploads/2025/02/IMG_1731-768x1024.jpg",
    "seen-stories":                   "https://images.squarespace-cdn.com/content/v1/67d096a1ab6b7b756d0e779b/eb825299-fae9-4c65-9309-cbc5ca4d4bcc/Shell+docu+1.png",
    "surinam-airways":                "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg/1280px-PZ-TCN_B737_Surinam_50Years_4x6_6299_%2814223454809%29.jpg",
    "klm-royal-dutch-airlines":       "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg/1280px-KLM_Boeing_747-400_PH-BFP_at_Narita_airport_2014.jpg",
    "fly-allways":                    "https://upload.wikimedia.org/wikipedia/commons/thumb/8/81/Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg/1280px-Fly_All_Ways_Fokker_F70_at_Paramaribo_Airport.jpg",
    "rock-fitness-paramaribo":        "",
    "yoga-peetha-happiness-centre":   "",
    "carpe-diem-massagepraktijk":     "",
    "stichting-shiatsu-massage":      "",
    "royal-spa":                      "",
    "royal-wellness-lounge":          "",
    "the-beauty-bar":                 "https://beautybar.sr/wp-content/uploads/2025/08/Heading-8-e1755791215726.webp",
    "delete-beauty-lounge":           "",
    "hairstudio-32":                  "",
    "lashlift-suriname":              "",
    "lioness-beauty-effects":         "",
    "royal-rose-yoni-spa":            "",
    "thermen-hermitage-turkish-bath-beautycenter": "",
    "inksane-tattoos":                "",
    "bitdynamics":                    "https://bitdynamics.sr/wp-content/uploads/2024/08/hero-banner.webp",
    "eaglemedia":                     "",
    "ekay-media":                     "",
    "bloom-wellness-cafe":            "",
    "dli-travel-consultancy":         "",
    "fatum":                          "",
    "rich-skin":                      "",
    "pinkmoon-suriname":              "",
    "the-house-of-beauty":            "",
    "the-waxing-booth":               "",
    "the-wonderlab-su":               "",
    "honeycare":                      "",
    "mokisa-busidataa-osu-nv":        "",
    "handmade-by-farrell-nv":         "",
    "ias-wooden-and-construction-nv": "",
    "ec-operations":                  "",
    "nv-threefold-quality-system-support": "",
    "surimami-store":                 "",
    "huub-explorer-tours":            "",
    "wayfinders-exclusive-n-v":       "",
    "recreatie-oord-carolina-kreek":  "",
    "knini-paati":                    "",
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
    "river":       "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
    "nature_park": "https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=800&q=80",
    "museum":      "https://images.unsplash.com/photo-1575223970966-76ae61ee7838?w=800&q=80",
    "historical":  "https://images.unsplash.com/photo-1554232456-8727aae0cfa4?w=800&q=80",
    "mall":        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&q=80",
    "boutique":    "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=800&q=80",
    "jewelry":     "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=800&q=80",
    "candles":     "https://images.unsplash.com/photo-1603905462088-6a8dd77cddc5?w=800&q=80",
    "crafts":      "https://images.unsplash.com/photo-1561136594-7f68413baa99?w=800&q=80",
    "liquor":      "https://images.unsplash.com/photo-1586899028174-e7098604235b?w=800&q=80",
    "supermarket": "https://images.unsplash.com/photo-1534723452862-4c874986ebad?w=800&q=80",
    "skincare":    "https://images.unsplash.com/photo-1556228578-0d85b1a4d571?w=800&q=80",
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

def _make_biz(slug):
    b = _BIZ.get(slug)
    if not b: return None
    return {"slug": slug, "name": b["name"], "area": b.get("location", "Suriname"),
            "address": b.get("address", ""), "phone": b.get("phone", ""),
            "email": b.get("email", ""), "category": b.get("category", ""),
            "description": b.get("description", ""),
            "url": f"listing/{slug}/",          # internal detail page
            "external_url": _biz_url(b),        # business website / Google fallback
            "image": _biz_img(slug)}

RESTAURANTS = [b for slug in ["a-la-john","ac-bar-restaurant","baka-foto-restaurant","bar-zuid","big-tex","bori-tori","chi-min","de-gadri","de-spot","de-verdieping","el-patron-latin-grill","elines-pizza","garden-of-eden","goe-thai-noodle-bar","hard-rock-cafe-suriname","joey-ds","julias-food","kasan-snacks","las-tias","mickis-palace-noord","mickis-palace-zuid","mingle-paramaribo","moments-restaurant","pane-e-vino","pannekoek-en-poffertjes-cafe","passion-food-and-wines","rogom-farm-nv","souposo","sushi-ya","the-coffee-box","zeg-ijsje","zus-zo-cafe"] for b in [_make_biz(slug)] if b]

HOTELS = [b for slug in ["bronbella-villa-residence","courtyard-by-marriott","eco-resort-miano","eco-torarica","holland-lodge","hotel-palacio","hotel-peperpot","houttuyn-wellness-river-resort","jacana-amazon-wellness-resort","oxygen-resort","royal-brasil-hotel","royal-breeze-hotel-paramaribo","royal-torarica","taman-indah-resort","the-golden-truly-hotel","tiny-house-tropical-appartment","torarica-resort","villa-famiri","waterland-suites","zeelandia-suites"] for b in [_make_biz(slug)] if b]

SIGHTSEEING = [b for slug in ["ford-zeelandia","het-koto-museum","peperpot-nature-park","joden-savanne","plantage-frederiksdorp","museum-bakkie","cola-kreek-recreatiepark"] for b in [_make_biz(slug)] if b]

ADVENTURES_BIZ = [b for slug in ["afobaka-resort","akira-overwater-resort","huub-explorer-tours","knini-paati","kodouffi-tapawatra-resort","recreatie-oord-carolina-kreek","tio-boto-eco-resort","unlimited-suriname-tours","wayfinders-exclusive-n-v"] for b in [_make_biz(slug)] if b]

SHOPPING = [b for slug in ["9173","bed-bath-more-bbm","divergent-body-jewelry","dj-liquor-store","from-me-to-me","galaxy","h-garden","hermitage-mall","honeycare","international-mall-of-suriname","kirpalani","lilis","nv-zing-manufacturing","papillon-crafts","readytex-souvenirs-and-crafts","shlx-collection","sleeqe","smoothieskin","suraniyat","switi-momenti-candles-crafts","talking-prints-concept-store","the-old-attic","the-uma-store","unlocked-candles","woodwonders-suriname","zeepfabriek-joab"] for b in [_make_biz(slug)] if b]

SERVICES = [b for slug in ["bitdynamics","bloom-wellness-cafe","carpe-diem-massagepraktijk","delete-beauty-lounge","dli-travel-consultancy","eaglemedia","ec-operations","ekay-media","fatum","fly-allways","hairstudio-32","handmade-by-farrell-nv","ias-wooden-and-construction-nv","inksane-tattoos","klm-royal-dutch-airlines","lashlift-suriname","lioness-beauty-effects","mokisa-busidataa-osu-nv","nv-threefold-quality-system-support","pinkmoon-suriname","rich-skin","rock-fitness-paramaribo","royal-rose-yoni-spa","royal-spa","royal-wellness-lounge","seen-stories","stichting-shiatsu-massage","stukaderen-in-nederland","surimami-store","surinam-airways","the-beauty-bar","the-freelance-scout","the-house-of-beauty","the-waxing-booth","the-wonderlab-su","thermen-hermitage-turkish-bath-beautycenter","timeless-barber-and-nail-shop","yoga-peetha-happiness-centre"] for b in [_make_biz(slug)] if b]

# (legacy stubs removed — RESTAURANTS / HOTELS now come from JSON above)
# Old stub lists removed — all listings now sourced from JSON above

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
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
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

def nav_html(active="home", prefix=""):
    links = [
        (f"{prefix}index.html#nature",     "Nature"),
        (f"{prefix}index.html#activities", "Activities"),
        (f"{prefix}index.html#dining",     "Eat & Drink"),
        (f"{prefix}index.html#hotels",     "Stay"),
        (f"{prefix}shopping.html",         "Shopping"),
        (f"{prefix}services.html",         "Services"),
        (f"{prefix}currency.html",         "Currency"),
        (f"{prefix}news.html",             "News"),
    ]
    lhtml = ""
    for href, label in links:
        cls = "font-semibold" if label.lower() == active else "text-gray-700 hover:text-green-800 transition"
        color = 'style="color:var(--forest)"' if label.lower() == active else ""
        lhtml += f'<a href="{href}" class="{cls} text-sm" {color}>{label}</a>\n'
    return f"""
<nav class="fixed top-0 w-full z-50" style="background:rgba(255,255,255,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 12px rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
    <a href="{prefix}index.html" class="flex items-baseline">
      <span class="serif text-2xl font-bold" style="color:var(--forest)">Explore</span><span class="serif text-2xl font-bold" style="color:var(--coral)">Suriname</span>
    </a>
    <div class="hidden md:flex items-center gap-7">{lhtml}</div>
    <a href="{prefix}news.html" class="hidden md:inline-flex items-center gap-1 text-white text-sm font-medium px-4 py-2 rounded-full hover:opacity-90 transition" style="background:var(--forest)">&#128240; Latest News</a>
    <button onclick="document.getElementById('mm').classList.toggle('hidden')" class="md:hidden p-2 rounded-lg hover:bg-gray-100">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>
  </div>
  <div id="mm" class="hidden md:hidden border-t bg-white px-5 py-4 flex flex-col gap-3 text-sm">{lhtml}</div>
</nav>"""

def footer_html(prefix=""):
    return f"""
<footer style="background:var(--forest)" class="text-white py-16">
  <div class="max-w-6xl mx-auto px-5">
    <div class="grid grid-cols-1 md:grid-cols-4 gap-10 mb-10">
      <div>
        <p class="serif text-2xl font-bold mb-3">Explore<span style="color:var(--coral)">Suriname</span></p>
        <p class="text-white/60 text-sm leading-relaxed">Your guide to South America's most beautiful secret. Updated daily with fresh news, local insights and travel inspiration.</p>
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
          <li><a href="{prefix}news.html"        class="hover:text-white transition">Suriname News</a></li>
        </ul>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Travel Info</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li>&#127988; Capital: Paramaribo</li>
          <li>&#128172; Dutch, Sranan Tongo + 9 more</li>
          <li>&#128176; Surinamese Dollar (SRD)</li>
          <li>&#127774; Tropical, ~28&#176;C year-round</li>
          <li>&#127942; 2 UNESCO World Heritage Sites</li>
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
      <p class="text-white/40 text-xs">&copy; {YEAR} ExploreSuriname.com &mdash; Auto-updated daily &middot; Content from public sources</p>
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
    return (f'<div class="flex items-center justify-center bg-gray-50 border border-dashed '
            f'border-gray-300 rounded-xl text-gray-400 text-sm py-6 my-6">'
            f'&#128226; {html_lib.escape(label)}</div>')

def nature_card(spot):
    tags_html = "".join(
        f'<span class="text-xs px-2 py-0.5 rounded-full font-medium" style="background:var(--mint);color:var(--forest)">{t}</span>'
        for t in spot["tags"]
    )
    url = spot.get("url", "#")
    return f"""
<a href="{url}" target="_blank" rel="noopener noreferrer" class="group rounded-2xl overflow-hidden card-hover bg-white border border-gray-100 shadow-sm flex flex-col">
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
    url = act.get("url", "#")
    img = act.get("image", "")
    img_html = f'<img src="{img}" alt="{html_lib.escape(act["name"])}" loading="lazy" class="w-full h-56 object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.style.display=\'none\'">' if img else ""
    return f"""
<a href="{url}" target="_blank" rel="noopener noreferrer" class="group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover overflow-hidden flex flex-col">
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
<a href="{url}" class="group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover flex flex-col overflow-hidden">
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

def listing_page(title, subtitle, meta_desc, items, cards_html, bg_color="var(--forest)", page_file="", extra_html=""):
    page_url = f"{SITE_URL}/{page_file}"
    return f"""{PAGE_HEAD}
  <title>{title} | ExploreSuriname.com</title>
  <meta name="description" content="{html_lib.escape(meta_desc)}">
  <link rel="canonical" href="{page_url}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{page_url}">
  <meta property="og:title" content="{title} | ExploreSuriname.com">
  <meta property="og:description" content="{html_lib.escape(meta_desc)}">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title} | ExploreSuriname.com">
  <meta name="twitter:description" content="{html_lib.escape(meta_desc)}">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
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
    "@type": "WebSite",
    "name": "Explore Suriname",
    "url": "{SITE_URL}/",
    "description": "Your complete travel and lifestyle guide to Suriname — hotels, restaurants, nature, activities and live SRD exchange rates.",
    "inLanguage": "en",
    "potentialAction": {{
      "@type": "SearchAction",
      "target": {{
        "@type": "EntryPoint",
        "urlTemplate": "{SITE_URL}/restaurants.html"
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
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Climate</p><p class="font-semibold">&#127774; Tropical, ~28&#176;C</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Forest Cover</p><p class="font-semibold">&#127807; 94% Rainforest</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">UNESCO Sites</p><p class="font-semibold">&#127942; 2 World Heritage</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Bird Species</p><p class="font-semibold">&#128038; 700+ Species</p></div>
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
    <div class="text-center mt-10">{more_btn("nature.html", f"View all {len(NATURE_SPOTS)} nature spots")}</div>
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
    <div class="text-center mt-10">{more_btn("activities.html", f"View all {len(ACTIVITIES)} activities")}</div>
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
    cards = "\n".join(nature_card(s) for s in NATURE_SPOTS)
    sight_cards = "\n".join(poi_card(b) for b in SIGHTSEEING)
    extra = f"""
<div class="mt-16">
  <div class="text-center mb-10">
    <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Must-See</p>
    <h2 class="serif text-3xl font-bold text-gray-900 mb-2">Sightseeing &amp; Attractions</h2>
    <p class="text-gray-500 text-base max-w-xl mx-auto">Historic forts, museums and natural landmarks you can visit in and around Paramaribo.</p>
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{sight_cards}</div>
</div>""" if SIGHTSEEING else ""
    return listing_page("Nature & Parks", f"{len(NATURE_SPOTS)} destinations across Suriname's pristine wilderness",
        f"Explore {len(NATURE_SPOTS)} nature reserves, national parks and rainforest destinations in Suriname. From Central Suriname Nature Reserve to Brownsberg — plan your eco-adventure.",
        NATURE_SPOTS, cards, page_file="nature.html", extra_html=extra)

def build_activities_page():
    cards = "\n".join(activity_card_rich(a) for a in ACTIVITIES)
    adv_cards = "\n".join(poi_card(b) for b in ADVENTURES_BIZ)
    extra = f"""
<div class="mt-16">
  <div class="text-center mb-10">
    <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Book Your Adventure</p>
    <h2 class="serif text-3xl font-bold text-gray-900 mb-2">Tour Operators &amp; Resorts</h2>
    <p class="text-gray-500 text-base max-w-xl mx-auto">Eco-lodges, jungle camps and tour companies to make your Suriname adventure happen.</p>
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">{adv_cards}</div>
</div>""" if ADVENTURES_BIZ else ""
    return listing_page("Activities", f"{len(ACTIVITIES)} things to do in Suriname",
        f"Discover {len(ACTIVITIES)} things to do in Suriname — jungle tours, river trips, birdwatching, kayaking and more. Find tours, eco-lodges and adventure operators in Paramaribo.",
        ACTIVITIES, cards, bg_color="var(--forest2)", page_file="activities.html", extra_html=extra)

def build_restaurants_page(restaurants):
    cards = "\n".join(poi_card(r, "cuisine") for r in restaurants)
    return listing_page("Restaurants & Dining", f"{len(restaurants)} restaurants across Suriname",
        f"Browse {len(restaurants)} restaurants, cafes and bars in Paramaribo, Suriname. Indonesian, Creole, Chinese, Indian and international cuisine — find where to eat tonight.",
        restaurants, cards, bg_color="#7c3aed", page_file="restaurants.html")

def build_hotels_page(hotels):
    cards = "\n".join(poi_card(h, "category") for h in hotels)
    return listing_page("Hotels & Lodges", f"{len(hotels)} places to stay in Suriname",
        f"Browse {len(hotels)} hotels, eco-lodges and jungle retreats in Suriname. From Paramaribo city hotels to remote river resorts — find your perfect stay.",
        hotels, cards, bg_color="#c05621", page_file="hotels.html")

def build_shopping_page():
    cards = "\n".join(poi_card(b) for b in SHOPPING)
    return listing_page("Shopping", f"{len(SHOPPING)} shops, malls & boutiques in Suriname",
        f"Discover {len(SHOPPING)} shops in Suriname — malls, local boutiques, craft stores and souvenir shops in Paramaribo. Find gifts, fashion, electronics and more.",
        SHOPPING, cards, bg_color="#7c3aed", page_file="shopping.html")

def build_services_page():
    cards = "\n".join(poi_card(b) for b in SERVICES)
    return listing_page("Services", f"{len(SERVICES)} service providers in Suriname",
        f"Find {len(SERVICES)} service providers in Suriname — beauty salons, wellness centres, travel agencies, airlines, insurance and professional services in Paramaribo.",
        SERVICES, cards, bg_color="#0369a1", page_file="services.html")

def build_currency_page(cme_rates, cme_live, cme_updated, cbvs_rates, cbvs_live, cbvs_updated):
    import json as _json
    updated_now = datetime.now(SR_TZ).strftime("%d %b %Y, %H:%M SR")
    buy_json  = _json.dumps({r["currency"]: float(r["buy"])  for r in cme_rates})
    sell_json = _json.dumps({r["currency"]: float(r["sell"]) for r in cme_rates})

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
</main>
<script>{js}</script>
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
  <meta name="description" content="Latest Suriname news updated daily — De Ware Tijd, Starnieuws, Waterkant and more. Business, politics, culture and travel from Paramaribo.">
  <link rel="canonical" href="{SITE_URL}/news.html">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Explore Suriname">
  <meta property="og:url" content="{SITE_URL}/news.html">
  <meta property="og:title" content="Suriname News | Explore Suriname">
  <meta property="og:description" content="Latest Suriname news updated daily — De Ware Tijd, Starnieuws, Waterkant and more.">
  <meta property="og:image" content="{SITE_URL}/og-image.jpg">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="Suriname News | Explore Suriname">
  <meta name="twitter:description" content="Latest Suriname news updated daily — De Ware Tijd, Starnieuws, Waterkant and more.">
  <meta name="twitter:image" content="{SITE_URL}/og-image.jpg">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("news")}
<div class="pt-16"></div>
<div class="text-white text-center py-16" style="background:var(--forest)">
  <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Auto-updated daily</p>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname News</h1>
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

def _cat_back(category):
    cat = category.lower()
    for keywords, page, label in _CAT_MAP:
        if any(k in cat for k in keywords):
            return page, label
    return "services.html", "Services"


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

    name_e   = html_lib.escape(raw_name)
    desc_e   = html_lib.escape(desc[:160]) if desc else html_lib.escape(raw_name + " — listed on ExploreSuriname.com")
    back_file, back_label = _cat_back(category)

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

    website_btn = ""
    if ext_url and "google.com/search" not in ext_url:
        website_btn = (
            '<a href="' + html_lib.escape(ext_url) + '" target="_blank" rel="noopener" '
            'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
            'text-sm font-semibold text-white hover:opacity-90 transition mb-3" '
            'style="background:var(--forest)">🌐 Visit Website</a>'
        )

    directions_btn = (
        '<a href="' + html_lib.escape(maps_link) + '" target="_blank" rel="noopener" '
        'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl '
        'text-sm font-semibold border-2 hover:bg-gray-50 transition" '
        'style="border-color:var(--forest2);color:var(--forest2)">🗺️ Get Directions</a>'
    )

    desc_block = ('<p class="text-gray-700 leading-relaxed text-base mb-8">'
                  + html_lib.escape(desc) + '</p>') if desc else ""

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


# -- Main ---------------------------------------------------------------------

if __name__ == "__main__":
    print("ExploreSuriname generator starting...")

    articles                            = fetch_articles()
    cme_rates, cme_live, cme_updated    = fetch_cme_rates()
    cbvs_rates, cbvs_live, cbvs_updated = fetch_cbvs_rates()

    pages = {
        "index.html":       build_index(RESTAURANTS, HOTELS, articles[:6]),
        "nature.html":      build_nature_page(),
        "activities.html":  build_activities_page(),
        "restaurants.html": build_restaurants_page(RESTAURANTS),
        "hotels.html":      build_hotels_page(HOTELS),
        "shopping.html":    build_shopping_page(),
        "services.html":    build_services_page(),
        "currency.html":    build_currency_page(cme_rates, cme_live, cme_updated,
                                                cbvs_rates, cbvs_live, cbvs_updated),
        "news.html":        build_news(articles),
    }
    for fname, html in pages.items():
        with open(fname, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  OK  {fname}")

    os.makedirs("listing", exist_ok=True)
    count = 0
    for slug, biz in _BIZ.items():
        d = f"listing/{slug}"
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/index.html", "w", encoding="utf-8") as f:
            f.write(build_listing_page(slug, biz))
        count += 1
    print(f"  OK  {count} listing pages -> listing/*/index.html")
    print("Done.")
