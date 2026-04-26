#!/usr/bin/env python3
"""
ExploreSuriname.com – Full Tourism & News Site Generator
Generates: index.html, nature.html, activities.html,
           restaurants.html, hotels.html, news.html
Run daily via GitHub Actions.
"""

import feedparser
import html as html_lib
import re, os, json
import urllib.request, urllib.parse
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────────────────────────────
SITE_URL       = "https://exploresuriname.com"
CONTACT_EMAIL  = "surinamedomains@gmail.com"
YEAR           = datetime.now().year
MAX_PER_FEED   = 10

FEEDS = [
    {"name": "De Ware Tijd",  "url": "https://www.dwtonline.com/feed/",  "color": "#2D6A4F"},
    {"name": "Starnieuws",    "url": "https://www.starnieuws.com/feed/", "color": "#B40A2D"},
    {"name": "Waterkant",     "url": "https://www.waterkant.net/feed/",  "color": "#1a56db"},
    {"name": "SurinameTimes", "url": "https://surinametimes.net/feed/",  "color": "#7e3af2"},
    {"name": "ABC Suriname",  "url": "https://www.abcsur.com/feed/",     "color": "#e3a008"},
]

# ── Static Data ────────────────────────────────────────────────────────────────

NATURE_SPOTS = [
    {
        "name": "Central Suriname Nature Reserve",
        "badge": "UNESCO World Heritage",
        "desc": "One of the world's largest intact tropical rainforests — 1.6 million pristine hectares where jaguars, tapirs and giant river otters roam free. A global treasure.",
        "tags": ["UNESCO", "Rainforest", "Wildlife"],
        "image": "https://images.unsplash.com/photo-1448375240586-882707db888b?w=800&q=80",
        "fact": "Larger than some entire countries",
        "url": "https://whc.unesco.org/en/list/1017/",
    },
    {
        "name": "Brownsberg Nature Park",
        "badge": "Best Day Trip",
        "desc": "Perched 500m above the Brokopondo Reservoir, Brownsberg rewards visitors with jaw-dropping panoramic views, swimming waterfalls and abundant wildlife just 2 hours from Paramaribo.",
        "tags": ["Hiking", "Waterfall", "Views"],
        "image": "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800&q=80",
        "fact": "Howler monkeys, toucans & jaguars",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Galibi Nature Reserve",
        "badge": "Turtle Nesting Site",
        "desc": "On Suriname's Atlantic coast, giant leatherback sea turtles — the world's largest reptile — haul ashore to nest in one of nature's most breathtaking spectacles.",
        "tags": ["Sea Turtles", "Coastal", "Wildlife"],
        "image": "https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=800&q=80",
        "fact": "Nesting season: February – July",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Peperpot Nature Park",
        "badge": "Bird Watcher's Paradise",
        "desc": "A former plantation turned bird sanctuary just minutes from the capital. Over 200 bird species recorded — the perfect introduction to Suriname's extraordinary avian diversity.",
        "tags": ["Birding", "Easy Access", "Peaceful"],
        "image": "https://images.unsplash.com/photo-1444464666168-49d633b86797?w=800&q=80",
        "fact": "700+ bird species in Suriname",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Voltzberg & Raleighvallen",
        "badge": "Remote Expedition",
        "desc": "An iconic granite dome rising above the endless jungle canopy. Accessible only by multi-day expedition — the ultimate reward for the most adventurous travellers.",
        "tags": ["Expedition", "Climbing", "Remote"],
        "image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
        "fact": "Multi-day jungle trek required",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Paramaribo Historic Inner City",
        "badge": "UNESCO World Heritage",
        "desc": "The only wooden colonial city in the Americas. Dutch colonial architecture, Hindu temples, mosques and synagogues coexist in remarkable harmony along the Suriname River.",
        "tags": ["UNESCO", "History", "Culture"],
        "image": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=800&q=80",
        "fact": "2 UNESCO sites in one country",
        "url": "https://whc.unesco.org/en/list/940/",
    },
    {
        "name": "Bigi Pan Nature Reserve",
        "badge": "Flamingo Haven",
        "desc": "One of the largest mangrove areas in the Caribbean region, home to spectacular flocks of flamingos and an extraordinary diversity of coastal birdlife. Remote and pristine.",
        "tags": ["Flamingos", "Mangroves", "Coastal Birds"],
        "image": "https://images.unsplash.com/photo-1559827260-dc66d52bef19?w=800&q=80",
        "fact": "Thousands of flamingos year-round",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Wia Wia Nature Reserve",
        "badge": "Coastal Wilderness",
        "desc": "A protected stretch of Atlantic coastline where endangered sea turtles have nested for centuries. Remote, rarely visited and utterly wild — one of Suriname's most precious places.",
        "tags": ["Sea Turtles", "Coastal", "Remote"],
        "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",
        "fact": "Leatherback & green turtles nest here",
        "url": "https://www.stinasu.sr/",
    },
    {
        "name": "Commewijne River",
        "badge": "River Dolphins & Plantations",
        "desc": "A scenic river just across from Paramaribo, famous for river dolphin sightings, historic plantation ruins and the imposing star-shaped Fort Nieuw Amsterdam.",
        "tags": ["Dolphins", "History", "Easy Access"],
        "image": "https://images.unsplash.com/photo-1536329583941-14287ec6fc4e?w=800&q=80",
        "fact": "River dolphins seen year-round",
        "url": "https://www.google.com/search?q=commewijne+river+tour+suriname",
    },
    {
        "name": "Upper Suriname River",
        "badge": "Maroon Heritage",
        "desc": "Journey upriver through dense jungle to Maroon villages of the Saramacca and Matawai peoples. Stay in traditional lodges and experience a living ancient culture.",
        "tags": ["Maroon Culture", "River", "Multi-day"],
        "image": "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?w=800&q=80",
        "fact": "Ancient Afro-Surinamese cultures",
        "url": "https://www.google.com/search?q=upper+suriname+river+tour",
    },
    {
        "name": "Tafelberg",
        "badge": "Remote Tepui",
        "desc": "A flat-topped mountain rising dramatically from the rainforest. Only reachable by expedition, Tafelberg harbours unique plant species found nowhere else on earth.",
        "tags": ["Tepui", "Expedition", "Unique Flora"],
        "image": "https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80",
        "fact": "Endemic species above the clouds",
        "url": "https://www.google.com/search?q=tafelberg+suriname+expedition",
    },
    {
        "name": "Fort Nieuw Amsterdam",
        "badge": "Colonial History",
        "desc": "An 18th-century star-shaped fort at the confluence of the Suriname and Commewijne rivers. Now an open-air museum telling the story of Suriname's colonial past.",
        "tags": ["History", "Museum", "Easy Access"],
        "image": "https://images.unsplash.com/photo-1555993539-1732b0258235?w=800&q=80",
        "fact": "18th-century Dutch fortification",
        "url": "https://www.google.com/search?q=fort+nieuw+amsterdam+suriname",
    },
    {
        "name": "Sipaliwini Savanna",
        "badge": "Far South Wilderness",
        "desc": "An isolated savanna near the Brazilian border — one of Suriname's most remote places. Home to giant anteaters, pumas and pristine black-water rivers.",
        "tags": ["Remote", "Savanna", "Wildlife"],
        "image": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",
        "fact": "Accessible only by small aircraft",
        "url": "https://www.google.com/search?q=sipaliwini+savanna+suriname",
    },
    {
        "name": "Palumeu – Trio Village",
        "badge": "Indigenous Culture",
        "desc": "Deep in the southern jungle, the Trio indigenous village of Palumeu offers a rare window into a way of life unchanged for generations. Reachable only by charter flight.",
        "tags": ["Indigenous", "Remote", "Cultural"],
        "image": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=800&q=80",
        "fact": "Accessible by charter flight only",
        "url": "https://www.mets-suriname.com/",
    },
    {
        "name": "Colakreek",
        "badge": "Local Favourite",
        "desc": "A beautiful freshwater creek just outside Paramaribo, perfect for swimming and picnicking surrounded by jungle. The go-to half-day escape for Surinamese families.",
        "tags": ["Swimming", "Easy Access", "Local Favourite"],
        "image": "https://images.unsplash.com/photo-1504700610630-ac6aba3536d3?w=800&q=80",
        "fact": "30 min from Paramaribo city centre",
        "url": "https://www.google.com/search?q=colakreek+suriname",
    },
]

ACTIVITIES = [
    {
        "icon": "🌿", "name": "Jungle Trekking",
        "desc": "Multi-day guided expeditions through primary rainforest with expert Amerindian guides.",
        "url": "https://www.mets-suriname.com/",
        "image": "https://images.unsplash.com/photo-1519904981063-b0cf448d479e?w=600&q=80",
    },
    {
        "icon": "🛶", "name": "River Canoe Tours",
        "desc": "Glide through the Amazon basin on traditional dugout canoes, spotting caimans and river dolphins.",
        "url": "https://www.google.com/search?q=river+canoe+tour+suriname",
        "image": "https://images.unsplash.com/photo-1503220317375-aaad61436b1b?w=600&q=80",
    },
    {
        "icon": "🦜", "name": "Bird Watching",
        "desc": "Suriname is a birder's paradise — spot 700+ species including scarlet macaws and harpy eagles.",
        "url": "https://surinamebirdclub.org/",
        "image": "https://images.unsplash.com/photo-1444464666168-49d633b86797?w=600&q=80",
    },
    {
        "icon": "🏘️", "name": "Indigenous Village Tours",
        "desc": "Visit Trio and Wayana indigenous communities in the deep interior, preserving ancient traditions.",
        "url": "https://www.mets-suriname.com/",
        "image": "https://images.unsplash.com/photo-1516026672322-bc52d61a55d5?w=600&q=80",
    },
    {
        "icon": "🥁", "name": "Maroon Village Tours",
        "desc": "Experience the living culture of the Saramacca and Matawai Maroon peoples — music, craft and history.",
        "url": "https://www.google.com/search?q=maroon+village+tour+suriname",
        "image": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=600&q=80",
    },
    {
        "icon": "🏙️", "name": "Paramaribo City Walk",
        "desc": "Explore the UNESCO-listed historic inner city on foot — the only wooden colonial city in the Americas.",
        "url": "https://whc.unesco.org/en/list/940/",
        "image": "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?w=600&q=80",
    },
    {
        "icon": "🏊", "name": "Natural Swimming",
        "desc": "Take a dip in crystal-clear jungle rivers and natural rock pools at Colakreek and Brownsberg.",
        "url": "https://www.google.com/search?q=colakreek+brownsberg+swimming+suriname",
        "image": "https://images.unsplash.com/photo-1504700610630-ac6aba3536d3?w=600&q=80",
    },
    {
        "icon": "🐢", "name": "Turtle Watching",
        "desc": "Witness giant leatherback sea turtles nesting on Suriname's Atlantic coast at Galibi or Wia Wia.",
        "url": "https://www.stinasu.sr/",
        "image": "https://images.unsplash.com/photo-1518020382113-a7e8fc38eac9?w=600&q=80",
    },
    {
        "icon": "🐬", "name": "River Dolphin Watching",
        "desc": "Spot the rare freshwater boto dolphins on a boat tour along the scenic Commewijne River.",
        "url": "https://www.google.com/search?q=dolphin+watching+commewijne+river+suriname",
        "image": "https://images.unsplash.com/photo-1568430462989-44163eb1752f?w=600&q=80",
    },
    {
        "icon": "🎨", "name": "Maroon Art & Craft",
        "desc": "Watch master craftsmen carve intricate Maroon woodwork and weave traditional textile art.",
        "url": "https://www.google.com/search?q=maroon+art+craft+workshop+suriname",
        "image": "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=600&q=80",
    },
    {
        "icon": "🎣", "name": "Sport Fishing",
        "desc": "Fish for piranha, arapaima and peacock bass in jungle rivers and reservoirs.",
        "url": "https://www.google.com/search?q=sport+fishing+suriname",
        "image": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=600&q=80",
    },
    {
        "icon": "🏛️", "name": "Colonial Plantation Tours",
        "desc": "Cycle or boat through the Commewijne River district, visiting historic coffee and cacao plantations.",
        "url": "https://www.google.com/search?q=plantation+tour+commewijne+suriname",
        "image": "https://images.unsplash.com/photo-1586348943529-beaae6c28db9?w=600&q=80",
    },
    {
        "icon": "🍽️", "name": "Surinamese Cooking Class",
        "desc": "Learn to cook traditional Creole, Hindustani and Javanese dishes with a local Paramaribo family.",
        "url": "https://www.google.com/search?q=cooking+class+suriname+paramaribo",
        "image": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=600&q=80",
    },
    {
        "icon": "🚵", "name": "ATV & 4x4 Interior Tours",
        "desc": "Explore jungle trails, gold mining areas and remote villages by ATV or 4x4.",
        "url": "https://www.google.com/search?q=atv+4x4+tour+suriname",
        "image": "https://images.unsplash.com/photo-1533130061792-64b345e4a833?w=600&q=80",
    },
    {
        "icon": "🌊", "name": "Kayaking & Paddling",
        "desc": "Paddle through mangroves, jungle rivers and lake areas on guided or self-guided kayak tours.",
        "url": "https://www.google.com/search?q=kayaking+suriname",
        "image": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=600&q=80",
    },
    {
        "icon": "🌌", "name": "Jungle Stargazing",
        "desc": "Zero light pollution deep in the interior delivers some of the world's most incredible night skies.",
        "url": "https://www.google.com/search?q=jungle+camp+overnight+suriname",
        "image": "https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=600&q=80",
    },
]

RESTAURANTS = [
    {"name": "De Gadri",                  "cuisine": "Surinamese",         "area": "Paramaribo", "desc": "Traditional Surinamese home cooking in a charming colonial garden setting. Famous for pom, roti and moksi alesi.",                 "url": "https://www.google.com/search?q=de+gadri+restaurant+paramaribo"},
    {"name": "Restaurant Spice Quest",    "cuisine": "Indian-Surinamese",  "area": "Paramaribo", "desc": "A rich fusion of Hindustani spice with modern, elegant presentation. Outstanding curries and tandoor dishes.",                    "url": "https://www.google.com/search?q=spice+quest+restaurant+paramaribo"},
    {"name": "Zus & Zo",                  "cuisine": "Café & Bakery",      "area": "Paramaribo", "desc": "Beloved neighbourhood café with fresh pastries, open sandwiches and excellent locally-sourced coffee. Always busy.",             "url": "https://www.google.com/search?q=zus+zo+cafe+paramaribo"},
    {"name": "Warung Mini",               "cuisine": "Javanese",           "area": "Paramaribo", "desc": "Authentic Javanese-Surinamese dishes in a relaxed warung atmosphere. Try the bami, nasi and soto.",                             "url": "https://www.google.com/search?q=warung+mini+paramaribo"},
    {"name": "Bistro de Paris",           "cuisine": "French-Creole",      "area": "Waterfront", "desc": "French-influenced creole cuisine with a stunning view over the historic Paramaribo waterfront.",                                  "url": "https://www.google.com/search?q=bistro+de+paris+paramaribo"},
    {"name": "La Gondola",                "cuisine": "Italian",            "area": "Paramaribo", "desc": "Wood-fired pizzas and homemade pasta — the best Italian food in Suriname, with an excellent wine list.",                         "url": "https://www.google.com/search?q=la+gondola+restaurant+paramaribo"},
    {"name": "Restaurant Humphrey's",     "cuisine": "International",      "area": "Paramaribo", "desc": "Popular international restaurant with a diverse menu catering to all tastes. Lively atmosphere and reliable quality.",             "url": "https://www.google.com/search?q=humphreys+restaurant+paramaribo"},
    {"name": "Grand Café 1900",           "cuisine": "Café & Bar",         "area": "Paramaribo", "desc": "Historic café in a beautifully preserved colonial building. The social heart of old Paramaribo since the early 1900s.",           "url": "https://www.google.com/search?q=grand+cafe+1900+paramaribo"},
    {"name": "Sarinah Restaurant",        "cuisine": "Indonesian",         "area": "Paramaribo", "desc": "Authentic Indonesian rijsttafel served in a warm family setting — a Paramaribo institution beloved by locals.",                   "url": "https://www.google.com/search?q=sarinah+restaurant+paramaribo+suriname"},
    {"name": "ToHo Restaurant",           "cuisine": "Chinese-Surinamese", "area": "Paramaribo", "desc": "A Paramaribo classic serving Chinese-Surinamese fusion. Generous portions and great value. Cash only.",                          "url": "https://www.google.com/search?q=toho+restaurant+paramaribo"},
    {"name": "Tori Oso",                  "cuisine": "Creole",             "area": "Paramaribo", "desc": "Traditional Creole home cooking at its finest — pom, heri heri and black-eyed pea soup that taste like grandmother made it.",   "url": "https://www.google.com/search?q=tori+oso+restaurant+paramaribo"},
    {"name": "Jade Garden",               "cuisine": "Chinese",            "area": "Paramaribo", "desc": "Authentic dim sum and Cantonese specialties in a spacious, family-friendly setting popular for Sunday lunches.",                  "url": "https://www.google.com/search?q=jade+garden+paramaribo+suriname"},
    {"name": "Roti Shop Heera",           "cuisine": "Hindustani",         "area": "Paramaribo", "desc": "The best roti in Paramaribo — locals have been queuing for the flaky flatbread and rich curries for decades.",                  "url": "https://www.google.com/search?q=roti+heera+paramaribo"},
    {"name": "River Club",                "cuisine": "International & Grill", "area": "Waterfront", "desc": "Riverside dining and a vibrant bar with great views over the Suriname River. Perfect for sunset drinks.",                    "url": "https://www.google.com/search?q=river+club+paramaribo+suriname"},
    {"name": "Restaurant Palmtuin",       "cuisine": "Surinamese",         "area": "Paramaribo", "desc": "Open-air dining surrounded by palm trees — local Surinamese favourites in a relaxed tropical garden setting.",                  "url": "https://www.google.com/search?q=palmtuin+restaurant+paramaribo"},
    {"name": "Soupie's Kitchen",          "cuisine": "BBQ & Soul Food",    "area": "Paramaribo", "desc": "Suriname's best BBQ and soul food, loved by locals for weekend family gatherings. Arrive early — it sells out.",                "url": "https://www.google.com/search?q=soupies+kitchen+paramaribo"},
    {"name": "Evergreen Health Bar",      "cuisine": "Healthy & Vegan",   "area": "Paramaribo", "desc": "Fresh juices, açaí bowls and plant-based Surinamese-inspired dishes for health-conscious visitors.",                             "url": "https://www.google.com/search?q=evergreen+health+bar+paramaribo"},
    {"name": "Torarica Restaurant",       "cuisine": "Fine Dining",        "area": "Waterfront", "desc": "Elegant fine dining at Suriname's premier hotel, with panoramic river views and an extensive international wine list.",           "url": "https://www.torarica.com/"},
    {"name": "The Food Truck Park",       "cuisine": "Street Food",        "area": "Paramaribo", "desc": "Rotating food trucks serving Surinamese street food — pom, bami, bara and roti. Great for a casual, cheap and delicious meal.",  "url": "https://www.google.com/search?q=food+truck+park+paramaribo+suriname"},
    {"name": "Café de Java",              "cuisine": "Javanese Fusion",    "area": "Paramaribo", "desc": "Modern café celebrating Suriname's Javanese heritage with a contemporary twist. Great breakfast and brunch spot.",               "url": "https://www.google.com/search?q=cafe+java+paramaribo+suriname"},
]

HOTELS = [
    {"name": "Torarica Hotel & Casino",         "category": "5-Star Luxury",    "area": "Paramaribo",      "desc": "Suriname's iconic riverside luxury hotel: stunning pool, casino, spa, multiple restaurants. The best address in the country.",                                    "url": "https://www.torarica.com/"},
    {"name": "Courtyard by Marriott Paramaribo","category": "Business Hotel",   "area": "Paramaribo",      "desc": "Modern international hotel with excellent amenities and conference facilities, perfectly placed in the heart of the capital.",                                    "url": "https://www.marriott.com/en-us/hotels/pbmcy-courtyard-paramaribo/overview/"},
    {"name": "Eco Resort Inn",                  "category": "Eco Lodge",        "area": "Paramaribo",      "desc": "Sustainable resort surrounded by lush tropical gardens, bungalows, a beautiful pool and one of Paramaribo's best restaurants.",                                "url": "https://www.ecoresortinn.com/"},
    {"name": "Bergendal Eco & Cultural River Resort", "category": "Eco Resort", "area": "Suriname River",  "desc": "Stunning eco-resort with tree-house cabins, zip-lines, jungle trails and cultural programs set on the banks of the Suriname River.",                           "url": "https://www.bergendal.com/"},
    {"name": "Awarradam Jungle Lodge",          "category": "Jungle Lodge",     "area": "Deep Interior",   "desc": "Remote luxury lodge deep in the Surinamese jungle, accessible by small plane and canoe. An utterly unforgettable wilderness experience.",                       "url": "https://www.awarra.com/"},
    {"name": "Danpaati River Lodge",            "category": "River Lodge",      "area": "Upper Suriname River", "desc": "Traditional Maroon-style lodge on the wild Gran Rio river — canoe trips, village visits and jungle treks included.",                                     "url": "https://www.google.com/search?q=danpaati+river+lodge+suriname"},
    {"name": "Kabalebo Nature Resort",          "category": "Remote Lodge",     "area": "Western Interior","desc": "Ultra-remote fishing and nature lodge in Suriname's seldom-visited west. Exceptional fishing, wildlife and birding. Charter flight only.",                       "url": "https://www.google.com/search?q=kabalebo+nature+resort+suriname"},
    {"name": "Hotel Laminaire",                 "category": "Boutique Hotel",   "area": "Paramaribo",      "desc": "Intimate boutique hotel in a beautifully restored 19th-century colonial mansion in the historic heart of Paramaribo.",                                         "url": "https://www.google.com/search?q=hotel+laminaire+paramaribo"},
    {"name": "Palmentuinguesthouse",            "category": "Guesthouse",       "area": "Paramaribo",      "desc": "Charming guesthouse with lush tropical gardens, warmly recommended by travellers for its hospitality and central location.",                                    "url": "https://www.google.com/search?q=palmentuin+guesthouse+paramaribo"},
    {"name": "Hotel Golfzicht",                 "category": "Mid-Range",        "area": "Paramaribo",      "desc": "Well-located hotel with a pool overlooking the city's golf course — good value and comfortable for business or leisure stays.",                                "url": "https://www.google.com/search?q=hotel+golfzicht+paramaribo"},
    {"name": "Ambassador Hotel",                "category": "Classic Hotel",    "area": "Paramaribo",      "desc": "A Paramaribo classic with comfortable rooms, a restaurant and conference facilities. Reliable and well-established.",                                          "url": "https://www.google.com/search?q=ambassador+hotel+paramaribo+suriname"},
    {"name": "Brownsberg Cabins (STINASU)",     "category": "Park Cabins",      "area": "Brownsberg",      "desc": "Stay inside Brownsberg Nature Park in forest cabins managed by STINASU. Wake to howler monkeys and birdsong — the real thing.",                               "url": "https://www.stinasu.sr/"},
    {"name": "Foengoe Island Lodge",            "category": "Island Lodge",     "area": "Suriname River",  "desc": "A small island lodge in the Suriname River, reached by boat — perfect for birdwatching, relaxation and escaping the city.",                                    "url": "https://www.google.com/search?q=foengoe+island+lodge+suriname"},
    {"name": "Jungle Top Resort",               "category": "Nature Resort",    "area": "Interior",        "desc": "Eco-resort at the edge of the rainforest with comfortable bungalows, a pool and guided jungle activities.",                                                    "url": "https://www.google.com/search?q=jungle+top+resort+suriname"},
    {"name": "Colakreek Resort",                "category": "Nature Resort",    "area": "Near Paramaribo", "desc": "Bungalows and camping beside the famous Colakreek freshwater swimming area, just 30 minutes from the capital.",                                               "url": "https://www.google.com/search?q=colakreek+resort+suriname"},
    {"name": "Hotel Home",                      "category": "Budget Hotel",     "area": "Paramaribo",      "desc": "Central, clean and well-priced accommodation popular with budget travellers and backpackers. Friendly staff and great location.",                               "url": "https://www.google.com/search?q=hotel+home+paramaribo+suriname"},
    {"name": "Stones Boutique Hotel",           "category": "Boutique",         "area": "Paramaribo",      "desc": "Stylish boutique hotel with individually designed rooms and a beautiful rooftop terrace with city views.",                                                      "url": "https://www.google.com/search?q=stones+boutique+hotel+paramaribo"},
    {"name": "Fort Nieuw Amsterdam Hotel",      "category": "Heritage Stay",    "area": "Commewijne",      "desc": "Historic hotel adjacent to Fort Nieuw Amsterdam, offering a unique heritage stay across the river from Paramaribo.",                                             "url": "https://www.google.com/search?q=fort+nieuw+amsterdam+hotel+suriname"},
    {"name": "Zus & Zo Guesthouse",            "category": "Guesthouse",       "area": "Paramaribo",      "desc": "Relaxed guesthouse connected to the popular café of the same name. Homely rooms and excellent breakfasts included.",                                             "url": "https://www.google.com/search?q=zus+zo+guesthouse+paramaribo"},
    {"name": "Palumeu Jungle Lodge",            "category": "Indigenous Lodge", "area": "Deep South",      "desc": "Lodge near the Trio indigenous village of Palumeu, deep in the southern jungle. Accessible by charter flight only. An extraordinary experience.",              "url": "https://www.mets-suriname.com/"},
]

# ── Helpers ─────────────────────────────────────────────────────────────────────

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

# ── Data fetching ───────────────────────────────────────────────────────────────

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

# ── Shared page parts ────────────────────────────────────────────────────────────

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

def nav_html(active="home"):
    links = [
        ("index.html#nature",     "Nature"),
        ("index.html#activities", "Activities"),
        ("index.html#dining",     "Eat & Drink"),
        ("index.html#hotels",     "Stay"),
        ("news.html",             "News"),
    ]
    lhtml = ""
    for href, label in links:
        cls = "font-semibold" if label.lower() == active else "text-gray-700 hover:text-green-800 transition"
        color = "style=\"color:var(--forest)\"" if label.lower() == active else ""
        lhtml += f'<a href="{href}" class="{cls} text-sm" {color}>{label}</a>\n'
    return f"""
<nav class="fixed top-0 w-full z-50" style="background:rgba(255,255,255,.97);backdrop-filter:blur(8px);border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 12px rgba(0,0,0,.06)">
  <div class="max-w-6xl mx-auto px-5 py-3 flex items-center justify-between">
    <a href="index.html" class="flex items-baseline">
      <span class="serif text-2xl font-bold" style="color:var(--forest)">Explore</span><span class="serif text-2xl font-bold" style="color:var(--coral)">Suriname</span>
    </a>
    <div class="hidden md:flex items-center gap-7">{lhtml}</div>
    <a href="news.html" class="hidden md:inline-flex items-center gap-1 text-white text-sm font-medium px-4 py-2 rounded-full hover:opacity-90 transition" style="background:var(--forest)">&#128240; Latest News</a>
    <button onclick="document.getElementById('mm').classList.toggle('hidden')" class="md:hidden p-2 rounded-lg hover:bg-gray-100">
      <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
    </button>
  </div>
  <div id="mm" class="hidden md:hidden border-t bg-white px-5 py-4 flex flex-col gap-3 text-sm">{lhtml}</div>
</nav>"""

def footer_html():
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
          <li><a href="nature.html"      class="hover:text-white transition">Nature &amp; Parks</a></li>
          <li><a href="activities.html"  class="hover:text-white transition">Activities</a></li>
          <li><a href="restaurants.html" class="hover:text-white transition">Eat &amp; Drink</a></li>
          <li><a href="hotels.html"      class="hover:text-white transition">Hotels &amp; Lodges</a></li>
          <li><a href="news.html"        class="hover:text-white transition">Suriname News</a></li>
        </ul>
      </div>
      <div>
        <p class="text-white/45 text-xs uppercase tracking-widest font-semibold mb-4">Travel Info</p>
        <ul class="space-y-2 text-sm text-white/70">
          <li>&#127988; Capital: Paramaribo</li>
          <li>&#128172; Dutch, Sranan Tongo + 9 more</li>
          <li>&#128176; Surinamese Dollar (SRD)</li>
          <li>&#127774; Tropical, ~28°C year-round</li>
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
    <div class="border-t border-white/10 pt-8 text-center text-white/40 text-xs">
      &copy; {YEAR} ExploreSuriname.com &mdash; Auto-updated daily &middot; Content from public sources
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

# ── Card renderers ──────────────────────────────────────────────────────────────

def nature_card(spot, preview=False):
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
    img_html = ""
    if img:
        img_html = f'<img src="{img}" alt="{html_lib.escape(act["name"])}" loading="lazy" class="w-full h-40 object-cover group-hover:scale-105 transition-transform duration-500" onerror="this.style.display=\'none\'">'
    return f"""
<a href="{url}" target="_blank" rel="noopener noreferrer" class="group bg-white rounded-2xl border border-gray-100 shadow-sm card-hover overflow-hidden flex flex-col">
  <div class="relative h-40 overflow-hidden bg-green-900">
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
    url      = item.get("url", "#")
    badge    = item.get(badge_key) or item.get("cuisine") or item.get("category", "")
    desc     = item.get("desc") or item.get("description") or ""
    area     = item.get("area", "Suriname")
    bg, fg   = ("var(--mint)", "var(--forest2)") if badge_key == "cuisine" else ("#fff3e8", "#c05621")
    return f"""
<a href="{url}" target="_blank" rel="noopener noreferrer" class="group bg-white rounded-2xl border border-gray-100 shadow-sm p-5 card-hover flex flex-col gap-2">
  <div class="flex items-start justify-between gap-2">
    <h4 class="font-bold text-gray-900 text-base leading-tight group-hover:text-green-800 transition">{html_lib.escape(item['name'])}</h4>
    {f'<span class="text-xs font-medium px-2 py-0.5 rounded-full shrink-0" style="background:{bg};color:{fg}">{html_lib.escape(badge)}</span>' if badge else ''}
  </div>
  <p class="text-gray-500 text-sm leading-relaxed flex-1">{html_lib.escape(desc)}</p>
  <div class="flex items-center justify-between mt-1">
    <p class="text-gray-400 text-xs">&#128205; {html_lib.escape(area)}, Suriname</p>
    <span class="text-xs font-semibold" style="color:var(--forest2)">Visit &rarr;</span>
  </div>
</a>"""

# ── Sub-page builder ────────────────────────────────────────────────────────────

def listing_page(title, subtitle, meta_desc, items, cards_html, bg_color="var(--forest)", page_file=""):
    return f"""{PAGE_HEAD}
  <title>{title} &mdash; ExploreSuriname.com</title>
  <meta name="description" content="{html_lib.escape(meta_desc)}">
  <link rel="canonical" href="{SITE_URL}/{page_file}">
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
</main>
{footer_html()}
</body>
</html>"""

# ── Index page ──────────────────────────────────────────────────────────────────

def build_index(restaurants, hotels, news_preview):
    # Show 6 on homepage, link to sub-pages for all
    nature_cards    = "\n".join(nature_card(s)         for s in NATURE_SPOTS[:6])
    activity_cards  = "\n".join(activity_card_icon(a)  for a in ACTIVITIES[:8])
    rest_cards      = "\n".join(poi_card(r, "cuisine") for r in restaurants[:6])
    hotel_cards     = "\n".join(poi_card(h, "category") for h in hotels[:6])
    news_cards      = "\n".join(news_card_html(a, large=(i == 0)) for i, a in enumerate(news_preview))

    more_btn = lambda href, label: f'<a href="{href}" class="inline-flex items-center gap-1 px-6 py-3 rounded-full text-sm font-semibold border-2 transition hover:opacity-80" style="border-color:var(--forest2);color:var(--forest2)">{label} &rarr;</a>'

    return f"""{PAGE_HEAD}
  <title>Explore Suriname &mdash; Discover South America&apos;s Best-Kept Secret</title>
  <meta name="description" content="Your guide to Suriname — pristine rainforests, vibrant culture, incredible wildlife. Discover nature, activities, restaurants and hotels.">
  <meta property="og:title" content="Explore Suriname — The Amazon's Best-Kept Secret">
  <meta property="og:url" content="{SITE_URL}/">
  <link rel="canonical" href="{SITE_URL}/">
</head>
<body class="bg-white overflow-x-hidden">
{nav_html("home")}

<!-- HERO -->
<section class="relative min-h-screen flex items-center justify-center hero-bg"
  style="background-image:url('https://images.unsplash.com/photo-1448375240586-882707db888b?w=1920&q=80')">
  <div class="absolute inset-0" style="background:linear-gradient(to bottom,rgba(0,0,0,.15) 0%,rgba(0,0,0,.55) 60%,rgba(0,0,0,.82) 100%)"></div>
  <div class="relative z-10 text-center text-white px-5 max-w-4xl mx-auto" style="padding-top:5rem">
    <p class="text-xs font-semibold tracking-widest uppercase mb-6" style="color:var(--coral)">South America&apos;s Hidden Gem</p>
    <h1 class="serif font-black leading-tight mb-6" style="font-size:clamp(2.5rem,8vw,5.5rem)">
      The Amazon&apos;s<br>Best-Kept Secret
    </h1>
    <p class="text-xl font-light leading-relaxed mb-10 max-w-2xl mx-auto text-white/90">
      94% pristine rainforest. Unmatched biodiversity. Two UNESCO World Heritage Sites. Welcome to Suriname.
    </p>
    <div class="flex flex-col sm:flex-row gap-4 justify-center">
      <a href="#nature" class="px-8 py-4 rounded-full font-semibold text-lg text-white hover:opacity-90 transition shadow-lg" style="background:var(--forest)">Start Exploring &#8595;</a>
      <a href="news.html" class="px-8 py-4 rounded-full font-semibold text-lg text-white border-2 hover:bg-white/10 transition" style="border-color:rgba(255,255,255,.6)">Latest News</a>
    </div>
  </div>
  <div class="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-white/50 text-xs">
    <span>Scroll to explore</span>
    <svg class="w-4 h-4 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
  </div>
</section>

<!-- FACTS BAR -->
<section style="background:var(--forest)" class="text-white py-7">
  <div class="max-w-5xl mx-auto px-5 grid grid-cols-2 sm:grid-cols-4 gap-6 text-center">
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Climate</p><p class="font-semibold">&#127774; Tropical, ~28°C</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Forest Cover</p><p class="font-semibold">&#127807; 94% Rainforest</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">UNESCO Sites</p><p class="font-semibold">&#127942; 2 World Heritage</p></div>
    <div><p class="text-white/45 text-xs uppercase tracking-widest mb-1">Bird Species</p><p class="font-semibold">&#128038; 700+ Species</p></div>
  </div>
</section>

<!-- NATURE -->
<section id="nature" class="py-24 bg-gray-50">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Pristine Wilderness</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Nature Like Nowhere Else</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname protects more of its original forest than any other country on earth. Here, wilderness still reigns.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {nature_cards}
    </div>
    <div class="text-center mt-10">{more_btn("nature.html", f"View all {len(NATURE_SPOTS)} nature spots")}</div>
  </div>
</section>

<!-- ACTIVITIES -->
<section id="activities" class="py-24" style="background:var(--forest)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Adventures Await</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-white mb-4">Things to Do</h2>
      <p class="text-white/60 text-lg max-w-2xl mx-auto leading-relaxed">From deep jungle expeditions to cultural immersion — experiences you can&apos;t find anywhere else on earth.</p>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      {activity_cards}
    </div>
    <div class="text-center mt-10">
      <a href="activities.html" class="inline-flex items-center gap-1 px-6 py-3 rounded-full text-sm font-semibold border-2 border-white/40 text-white hover:bg-white/10 transition">View all {len(ACTIVITIES)} activities &rarr;</a>
    </div>
  </div>
</section>

<!-- RESTAURANTS -->
<section id="dining" class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Eat &amp; Drink</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Where to Eat</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">Suriname&apos;s cuisine is as diverse as its people — Creole, Hindustani, Javanese, Chinese and Maroon flavors all on one plate.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {rest_cards}
    </div>
    <div class="text-center mt-10">{more_btn("restaurants.html", f"View all {len(RESTAURANTS)} restaurants")}</div>
  </div>
</section>

<!-- HOTELS -->
<section id="hotels" class="py-24" style="background:var(--mint)">
  <div class="max-w-6xl mx-auto px-5">
    <div class="text-center mb-16">
      <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--forest2)">Where to Stay</p>
      <h2 class="serif text-4xl sm:text-5xl font-bold text-gray-900 mb-4">Hotels &amp; Lodges</h2>
      <p class="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">From 5-star riverside hotels in Paramaribo to remote jungle lodges only reachable by canoe — every traveller finds their place.</p>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
      {hotel_cards}
    </div>
    <div class="text-center mt-10">{more_btn("hotels.html", f"View all {len(HOTELS)} hotels &amp; lodges")}</div>
  </div>
</section>

<!-- NEWS PREVIEW -->
<section class="py-24 bg-white">
  <div class="max-w-6xl mx-auto px-5">
    <div class="flex items-end justify-between mb-10 flex-wrap gap-4">
      <div>
        <p class="text-xs font-semibold tracking-widest uppercase mb-2" style="color:var(--forest2)">Stay Informed</p>
        <h2 class="serif text-4xl font-bold text-gray-900">Latest from Suriname</h2>
      </div>
      <a href="news.html" class="hidden sm:inline-flex px-6 py-3 rounded-full text-white text-sm font-semibold hover:opacity-90 transition" style="background:var(--forest)">All News &rarr;</a>
    </div>
    <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
      {news_cards}
    </div>
    <div class="text-center mt-8 sm:hidden">
      <a href="news.html" class="inline-flex px-6 py-3 rounded-full text-white text-sm font-semibold" style="background:var(--forest)">All Suriname News &rarr;</a>
    </div>
  </div>
</section>

{footer_html()}
</body>
</html>"""

# ── Sub-pages ───────────────────────────────────────────────────────────────────

def build_nature_page():
    cards = "\n".join(nature_card(s) for s in NATURE_SPOTS)
    return listing_page(
        "Nature & Parks", f"{len(NATURE_SPOTS)} destinations across Suriname's pristine wilderness",
        "Discover all of Suriname's nature reserves, national parks and natural wonders.",
        NATURE_SPOTS, cards, page_file="nature.html"
    )

def build_activities_page():
    cards = "\n".join(activity_card_rich(a) for a in ACTIVITIES)
    return listing_page(
        "Activities", f"{len(ACTIVITIES)} things to do in Suriname",
        "Find the best activities and adventures in Suriname — from jungle trekking to river canoe tours.",
        ACTIVITIES, cards, bg_color="var(--forest2)", page_file="activities.html"
    )

def build_restaurants_page(restaurants):
    cards = "\n".join(poi_card(r, "cuisine") for r in restaurants)
    return listing_page(
        "Restaurants & Dining", f"{len(restaurants)} restaurants across Suriname",
        "Find the best restaurants, cafés and dining experiences in Paramaribo and beyond.",
        restaurants, cards, bg_color="#7c3aed", page_file="restaurants.html"
    )

def build_hotels_page(hotels):
    cards = "\n".join(poi_card(h, "category") for h in hotels)
    return listing_page(
        "Hotels & Lodges", f"{len(hotels)} places to stay in Suriname",
        "Find the best hotels, eco-lodges and jungle retreats across Suriname.",
        hotels, cards, bg_color="#c05621", page_file="hotels.html"
    )

# ── News page ───────────────────────────────────────────────────────────────────

def build_news(articles):
    updated   = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    total     = len(articles)
    feat_html = "\n".join(news_card_html(a, large=True) for a in articles[:3])
    rest_html = "\n".join(news_card_html(a) for a in articles[3:30])
    return f"""{PAGE_HEAD}
  <title>Suriname News &mdash; ExploreSuriname.com</title>
  <meta name="description" content="Daily Suriname news from De Ware Tijd, Starnieuws, Waterkant and more.">
  <link rel="canonical" href="{SITE_URL}/news.html">
</head>
<body class="bg-gray-50 overflow-x-hidden">
{nav_html("news")}
<div class="pt-16"></div>
<div class="text-white text-center py-16" style="background:var(--forest)">
  <p class="text-xs font-semibold tracking-widest uppercase mb-3" style="color:var(--leaf)">Auto-updated daily</p>
  <h1 class="serif text-4xl sm:text-5xl font-bold mb-3">Suriname News</h1>
  <p class="text-white/55 text-sm">&#128336; {updated} &middot; {total} stories from {len(FEEDS)} sources</p>
</div>
<main class="max-w-5xl mx-auto px-5 py-10 pb-20">
  {ad_slot("Top Banner Ad — Replace with Google AdSense code")}
  <h2 class="text-xs font-bold uppercase tracking-widest mb-5" style="color:var(--forest2)">&#128293; Top Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">{feat_html}</div>
  {ad_slot("Mid-Page Ad — Replace with Google AdSense code")}
  <h2 class="text-xs font-bold uppercase tracking-widest mb-5 mt-6 text-gray-500">&#128240; All Stories</h2>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">{rest_html}</div>
</main>
{footer_html()}
</body>
</html>"""

# ── Main ─────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  ExploreSuriname.com — Site Generator")
    print("=" * 55)

    print("\n[1/5] Fetching news articles...")
    articles = fetch_articles()
    print(f"      {len(articles)} articles total")

    print("\n[2/5] Fetching restaurants (Overpass API)...")
    REST_Q = """[out:json][timeout:20];
area["name"="Paramaribo"]["admin_level"="8"]->.a;
(node["amenity"="restaurant"](area.a); way["amenity"="restaurant"](area.a););
out center 20;"""
    restaurants = merge_with_fallbacks(fetch_overpass(REST_Q, 20), RESTAURANTS)
    print(f"      {len(restaurants)} restaurants")

    print("\n[3/5] Fetching hotels (Overpass API)...")
    HOTEL_Q = """[out:json][timeout:20];
area["name"="Suriname"]["admin_level"="2"]->.a;
(node["tourism"~"hotel|guest_house|hostel|motel"](area.a);
 way["tourism"~"hotel|guest_house|hostel|motel"](area.a););
out center 20;"""
    hotels = merge_with_fallbacks(fetch_overpass(HOTEL_Q, 20), HOTELS)
    print(f"      {len(hotels)} hotels")

    print("\n[4/5] Generating all pages...")
    pages = {
        "index.html":       build_index(restaurants, hotels, articles[:3]),
        "nature.html":      build_nature_page(),
        "activities.html":  build_activities_page(),
        "restaurants.html": build_restaurants_page(restaurants),
        "hotels.html":      build_hotels_page(hotels),
        "news.html":        build_news(articles),
    }
    for filename, content in pages.items():
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"      {filename} — done")

    print("\n[5/5] All done! 6 pages generated.")
