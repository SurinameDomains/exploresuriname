# -*- coding: utf-8 -*-
"""Search vocabulary for the site search (search v2, 25 Oct 2026).

People in Suriname search by what they NEED ("aircoman paramaribo", "taart
bestellen", "nagelstudio wanica"), in Surinamese Dutch, English and some
Sranan, and often misspelled. This file is the shared vocabulary:

CONCEPTS  one row per need. `terms` are what people type (folded, lower case;
          multi-word phrases allowed). generate.py tags every listing with the
          concepts it really offers (`sub` = every listing of that type, `rx` =
          description/name pattern in EN + NL, only inside `scope`), so a
          concept search returns businesses that DO the thing, not everything
          in a broad type.
PLACES    neighbourhood / town -> district, so "kapper lelydorp" ranks Lelydorp
          (Wanica) first. Ressort -> district from en.wikipedia "Resorts of
          Suriname"; neighbourhood names from addresses on the site.
FILLER    words that never have to match ("laten", "repareren", "openingstijden").

Sources for local words: surodeals.com, surinamemarktplaats.com, socialsuriname.com,
surinamyp.com, Facebook page names, nl.wikipedia Surinaams-Nederlands, Sranan
word lists (suriname.nu, IVDNT, Wortubuku). Research notes: CLAUDE.md "Search v2".
Words marked unverified in the research are kept only when cheap and harmless.

Scope letters: E Eat & Drink, S Stay, N Nature, A Activities, H Shopping,
V Services. Guide pages match concept terms through their keyword blob.

RULES: never rename a concept id (GA4 reports use them). Labels are hand-written
in all 6 languages (no machine translation, like zh/fr/pt elsewhere).
"""
import re
import unicodedata

CONCEPTS = []

def C(i, en, nl, es, zh, fr, pt, terms, sub="", rx="", scope="VH", neg="", r="", inc="", fx=""):
    CONCEPTS.append({"fx": fx,
        "i": i, "l": {"en": en, "nl": nl, "es": es, "zh": zh, "fr": fr, "pt": pt},
        "terms": [t.strip() for t in terms.split(",") if t.strip()],
        "sub": [s for s in sub.split() if s], "rx": rx, "scope": scope, "neg": neg,
        "r": [x for x in r.split() if x], "inc": [x for x in inc.split() if x],
    })

# ── Home, building and technical trades ─────────────────────────────────────
C("airco", "Air conditioning", "Airco & koeltechniek", "Aire acondicionado", "空调", "Climatisation", "Ar-condicionado",
  "airco, aircos, airco's, aircoman, airco man, aircoboy, airco boy, airco monteur, aircomonteur, airco service, "
  "aircoservice, airco installatie, airco installeren, airco reparatie, airco repareren, airco onderhoud, airco schoonmaken, "
  "airconditioning, airconditioner, airconditioners, air conditioning, air conditioner, aircondition, aircon, ac, ac repair, "
  "ac service, hvac, koeltechniek, koeltechnicus, koeltecniek, koeltechnisch, koelservice, koelman, koelgas, split unit, "
  "inverter airco, auto airco, car ac",
  rx=r"\bairco|air[- ]?condition|koeltechn|\bhvac\b|refrigeration|koelinstallat|aircon\b", scope="VH",
  neg=r"air-?conditioned (room|suite|apartment|unit)", r="appliance-repair electrician")
C("appliance-repair", "Appliance repair", "Reparatie witgoed", "Reparación de electrodomésticos", "家电维修", "Réparation d'électroménager", "Conserto de eletrodomésticos",
  "witgoed reparatie, koelkast reparatie, koelkast repareren, wasmachine reparatie, wasmachine repareren, freezer reparatie, "
  "fridge repair, appliance repair, appliances repair, washing machine repair",
  rx=r"(repair|reparatie|repareert|herstel)\w*.{0,80}(fridge|freezer|washing machine|appliance|koelkast|wasmachine|witgoed|household)"
     r"|(fridge|freezer|washing machine|appliance|koelkast|wasmachine|witgoed).{0,40}(repair|reparatie)", scope="VH", r="airco")
C("electrician", "Electricians", "Elektriciens", "Electricistas", "电工", "Électriciens", "Eletricistas",
  "elektricien, elektriciens, electricien, electriciens, elektriciën, elektrisien, electrician, electricians, elektra, "
  "elektrische installatie, elektrische installaties, elektrisch, electrical, electrical contractor, electrical services, "
  "bedrading, wiring, elektrotechniek, elektrotechnisch, installateur, ebs keuring, huisinstallatie, stroomstoring thuis",
  rx=r"electrician|electrical (install|contract|work|engineer|service|and energy|power)|electro-?techn|elektrotechn|elektricien"
     r"|elektrische (install|werk)|technical installation|technische install|power solutions|back-?up power|generators?\b",
  scope="V", r="solar generator")
C("plumber", "Plumbers & sanitary", "Loodgieters & sanitair", "Fontaneros", "水管工", "Plombiers", "Encanadores",
  "loodgieter, loodgieters, lootgieter, loodgieder, loodgieterswerk, plumber, plumbers, plumbing, sanitair, sanitaire, "
  "sanitary, waterleiding, riolering, riool, lekkage, lek, afvoer, ontstoppen, ontstopping, verstopping, toilet, wc, "
  "douche, badkamer, bathroom, kraan, kranen, boiler, geiser",
  rx=r"plumb|loodgiet|sanit(ary|air)|bathroom (fixture|fitting|ware|suppl)|badkamer|\btoilets\b|showers? (head|cabin|fitting)", scope="VH", neg=r"waterleiding maatschappij|baby ?shower",
  r="water-pump hardware")
C("septic", "Septic tanks & drains", "Septictanks & riolering", "Fosas sépticas", "化粪池清理", "Fosses septiques", "Fossas sépticas",
  "septictank, septictanks, septic tank, septic tanks, septictank legen, septictank ledigen, beerput, vetput, vetputten, "
  "vetput legen, riool ontstoppen, ontstoppingsdienst, kolkenzuiger, zuigwagen, septic pumping, drain cleaning",
  rx=r"septic|vetput|beerput|ontstopping|drain cleaning|zuigwagen", scope="V", r="plumber cleaning")
C("water-pump", "Water pumps", "Waterpompen & hydrofoor", "Bombas de agua", "水泵", "Pompes à eau", "Bombas d'água",
  "hydrofoor, hydrofoors, hydrofor, hidrofoor, hydrafoor, waterpomp, waterpompen, pomp, pompen, drukpomp, pompu, "
  "water pump, water pumps, pressure pump, booster pump, watertank, watertanks, water tank, put boren, bron boren, well drilling",
  rx=r"\bpumps?\b|\bpomp(en)?\b|hydrofo|water ?tank|drilling", scope="VH", r="plumber")
C("carpenter", "Carpenters & woodwork", "Timmerlieden & houtwerk", "Carpinteros", "木工", "Menuisiers", "Carpinteiros",
  "timmerman, timmerlieden, timmerlui, timmerwerk, timmeren, temreman, carpenter, carpenters, carpentry, joinery, woodwork, "
  "meubelmaker, meubelmakers, meubelmakerij, houtbewerking, hout, houthandel, kasten op maat, keukens op maat, keuken op maat, "
  "maatwerk meubels, mdf, kitchen cabinets, cabinet maker",
  rx=r"carpent|timmer(man|werk|bedrijf|lieden)|joinery|woodwork|houtbewerk|meubelmak|cabinet ?mak|kitchen cabinets|maatwerk (meubel|kast|keuken)",
  scope="VH", r="furniture construction")
C("welder", "Welding & steelwork", "Lassers & staalwerk", "Soldadores", "焊接", "Soudure & métallerie", "Soldadores",
  "lasser, lassers, lassen, laswerk, laswerken, lasbedrijf, welder, welders, welding, metaalbewerking, metaal, staal, "
  "staalconstructie, staalconstructies, steel, steel construction, steelwork, hekwerk, hek, hekken, poort, poorten, gate, gates, "
  "burglar bars, tralies, traliewerk, stainless steel, rvs",
  rx=r"weld|\blas(sen|werk|bedrijf)|steel (construct|structure|work|fabricat)|staalconstr|metal ?work|metaalbewerk|fabrication"
     r"|\bgates\b|poorten|hekwerk", scope="VH", r="construction")
C("aluminium-glass", "Aluminium & glass", "Aluminium & glas", "Aluminio y vidrio", "铝材与玻璃", "Aluminium & vitrerie", "Alumínio e vidro",
  "aluminium, aluminum, aluminium ramen, ramen, raam, kozijn, kozijnen, glas, glaszetter, schuifdeur, schuifdeuren, "
  "sliding doors, sliding windows, windows, glass, louvres, jaloezieën",
  rx=r"alumin|\bglass\b|\bglas\b|sliding (window|door)|schuif(deur|raam)|kozijn", scope="VH", r="construction")
C("painter", "Painters & paint", "Schilders & verf", "Pintores", "油漆工", "Peintres en bâtiment", "Pintores",
  "schilder, schilders, schilderwerk, schilderen, verven, verf, verfwinkel, ferfi, painter, painters, painting, paint, paints, "
  "muren verven, huis schilderen, woning schilderen",
  rx=r"\bpaint(s|ing|er|ers)?\b|schilder|\bverf\b|verfwinkel|coatings?\b", scope="VH",
  neg=r"art galler|kunstgaler|paintball|paintings by|works? of art", r="construction hardware")
C("tiler", "Tiles & flooring", "Tegels & vloeren", "Azulejos y pisos", "瓷砖与地板", "Carrelage & sols", "Pisos e revestimentos",
  "tegelzetter, tegelzetters, tegelzeter, tegels, tegel, tegelwerk, betegelen, tiles, tile, tiler, tiling, vloer, vloeren, "
  "flooring, laminaat, laminate, marmer, marble, graniet, granite, wandafwerking",
  rx=r"\btil(e|es|ing|er)\b|tegel|flooring|vloer|laminat|marble|marmer|granite|graniet", scope="VH", r="hardware construction")
C("construction", "Builders & contractors", "Aannemers & bouw", "Constructoras", "建筑商", "Entrepreneurs en bâtiment", "Construtoras",
  "aannemer, aannemers, aanemer, anemer, bouwbedrijf, bouwbedrijven, bouw, bouwen, laten bouwen, nieuwbouw, renovatie, "
  "renoveren, verbouwing, verbouwen, aanbouw, metselaar, metselaars, metselwerk, ruwbouw, beton, betonwerk, fundering, "
  "sleutelklaar, contractor, contractors, builder, builders, construction, construction company, renovation, architect, "
  "architecten, architectenbureau, bouwtekening, bouwtekeningen, bouwvergunning, landmeter, landmeten, surveying, "
  "plafond, plafonds, zwembad bouwen, pool builder",
  sub="construction-trades",
  rx=r"construct|contractor|aannemer|bouwbedrijf|renovat|architect|concrete|\bbeton|survey|landmeet|design and build|design & build",
  scope="V", r="hardware", neg=r"soft drink|beverage|cleaning compan")
C("roofing", "Roofing", "Daken & zink", "Techos", "屋顶", "Toitures", "Telhados",
  "dakdekker, dakdekkers, dak, daken, dakwerk, dakwerken, dakbedekking, dakplaten, blikslager, blikslagers, zink, zinkplaat, "
  "zinkplaten, golfplaten, dakgoot, goot, goten, roof, roofs, roofing, roofer, roofing sheets, zinc sheets, gutter, gutters",
  rx=r"\broof|\bdak(en|werk|plat|bedek|goot)?\b|zink|zinc|blikslag|gutter|golfplat", scope="VH", r="construction hardware", neg=r"under one roof|onder (een|één) dak")
C("handyman", "Handymen", "Klusjesmannen", "Manitas", "杂工", "Bricoleurs", "Faz-tudo",
  "klusjesman, klusjesmannen, klusser, klussen, klusjes, klus, handyman, handymen, odd jobs, reparatie aan huis, reparaties aan huis",
  rx=r"handy ?man|klusjes|odd jobs", scope="V", r="construction electrician plumber")
C("gardening", "Gardening & yard work", "Tuinonderhoud", "Jardinería", "园艺", "Jardinage", "Jardinagem",
  "tuinman, tuinmannen, hovenier, hoveniers, tuinonderhoud, tuin, tuinen, tuinaanleg, gras, gras maaien, grasmaaien, gras kappen, "
  "gras snijden, maaien, maaiwerk, erf schoonmaken, perceel schoonmaken, wieden, wied, snoeien, bomen kappen, boom kappen, "
  "brushcutter, grasmatten, graszoden, landscaping, landscaper, gardener, gardeners, gardening, garden, lawn, lawn care, "
  "grass cutting, yard, yard work, yard cleaning, tree cutting",
  sub="nursery-garden",
  rx=r"garden(ing)? (service|maint|design|centre|center)|landscap|tuinonderh|tuinaanleg|hovenier|\blawns?\b|grass (cutting|varieties|mats)|grasmat|plant nursery|nursery (and|&) garden|kwekerij",
  scope="VH", neg=r"beer garden|garden terrace|garden seating", r="pest")
C("pest", "Pest control", "Ongediertebestrijding", "Control de plagas", "除虫", "Lutte antiparasitaire", "Controle de pragas",
  "ongedierte, ongediertebestrijding, ongedierte bestrijding, ongedierte bestrijden, bestrijding, pest control, pest, pests, "
  "pestcontrol, exterminator, termieten, termiet, termites, houtluizen, houtluis, kakkerlakken, kakkerlak, cockroaches, ratten, "
  "rat, muizen, mieren, muskieten, sprayen, fumigation, fumigatie, desinfectie",
  rx=r"\bpests?\b|pest (control|management)|ongedierte|termi(te|et)|fumigat|houtluis|exterminat", scope="VH", r="gardening")
C("cleaning", "Cleaning services", "Schoonmaak", "Limpieza", "清洁服务", "Nettoyage", "Limpeza",
  "schoonmaak, schoonmaakbedrijf, schoonmaakbedrijven, schoonmaakdienst, schoonmaken, schoonmakers, schoonmaakster, poetsen, "
  "reiniging, huisreiniging, glazenwassen, ramen wassen, deep clean, deep cleaning, cleaning, cleaning service, cleaners, cleaner, "
  "maid, housekeeping, kantoor schoonmaak, office cleaning, skoro",
  sub="cleaning-maintenance",
  rx=r"\bclean(ing|ers)\b|schoonma|reiniging|housekeeping|janitor", scope="V", r="laundry")
C("laundry", "Laundry & dry cleaning", "Wasserij & stomerij", "Lavandería", "洗衣店", "Blanchisserie & pressing", "Lavanderia",
  "wasserij, wasserijen, wasserette, stomerij, stomen, strijken, strijkservice, wassen, was, wasi, laundry, laundromat, "
  "laundry service, dry cleaning, dry cleaner, dry cleaners, wash and fold, ironing",
  rx=r"laundry|laundromat|wasserij|wasserette|dry ?clean|stomerij|ironing|\bstrijk(en|service|werk)\b", scope="V", r="cleaning tailor")
C("tailor", "Tailors & alterations", "Kleermakers & naaiateliers", "Sastres y costura", "裁缝", "Couturiers & retouches", "Alfaiates e costura",
  "kleermaker, kleermakers, kleermakerij, naaister, naaisters, naaiatelier, naaien, atelier, kleding op maat, op maat gemaakt, "
  "kleding vermaken, vermaken, nayman, tailor, tailors, seamstress, dressmaker, alterations, alteration, sewing, "
  "pangi op maat, pangi set, kimona op maat, uniformen, uniforms",
  rx=r"\btailor(s|ing)?\b(?!-?made)|kleermak|seamstress|naaister|naaiatelier|dressmak|alterations?|sewing|\bnaai|op maat gemaakte kleding|custom clothing",
  scope="VH", neg=r"tailor-?made (tour|trip|package|itinerar)|tailored (tour|trip|travel|package|itinerar)", r="clothing")
C("shoe-repair", "Shoe repair", "Schoenmakers", "Reparación de calzado", "修鞋", "Cordonniers", "Sapateiros",
  "schoenmaker, schoenmakers, schoenreparatie, schoenen repareren, shoe repair, cobbler, cobblers",
  rx=r"cobbler|schoenmaker|shoe repair|schoenreparat", scope="VH", r="clothing")
C("phone-repair", "Phone repair", "Gsm-reparatie", "Reparación de celulares", "手机维修", "Réparation de téléphones", "Conserto de celular",
  "gsm reparatie, gsm repareren, gsm maken, gsm repair, telefoon reparatie, telefoonreparatie, telefoon repareren, telefoon maken, "
  "mobiel repareren, smartphone reparatie, iphone reparatie, samsung reparatie, scherm vervangen, nieuw scherm, kapot scherm, "
  "screen repair, screen replacement, phone repair, phone repairs, cell phone repair, fix my phone, fix phone, "
  "batterij vervangen, unlock, unlocken",
  rx=r"\b(phones?|gsm|smartphones?|iphones?|telefoons?|cell ?phones?|mobile phones?|mobiele telefoons?)\b.{0,50}(repair|reparat|fix|screen|scherm)"
     r"|(repair|reparat)\w*.{0,50}\b(phones?|gsm|smartphones?|iphones?|telefoons?)\b|screen replace", scope="VH",
  r="phones computers", neg=r"measuring|instruments")
C("phones", "Phones & accessories", "Telefoons & accessoires", "Teléfonos y accesorios", "手机与配件", "Téléphones & accessoires", "Celulares e acessórios",
  "gsm, gsms, gsm's, mobiel, mobieltje, mobiele telefoon, telefoon, telefoon kopen, telefoons, telefoonwinkel, smartphone, smartphones, iphone, "
  "iphones, samsung, phone, phones, cell phone, cellphone, mobile phone, phone shop, phone store, phone accessories, "
  "telefoonhoesje, hoesjes, phone case, oplader, charger, airpods, tablet, tablets, ipad",
  rx=r"smartphone|iphone|samsung|\bgsm|mobile (phone|device|accessor)|cell ?phone|phone (shop|store|accessor|case)|\bphones\b|telefoons\b|telefoonwinkel|tablets?\b",
  scope="H", r="phone-repair electronics telecom", fx="phone-repair")
C("computers", "Computers & laptops", "Computers & laptops", "Computadoras", "电脑", "Ordinateurs", "Computadores",
  "computer, computers, laptop, laptops, pc, pcs, pc's, desktop, notebook, macbook, printer, printers, inkt, toner, "
  "computer reparatie, laptop reparatie, pc reparatie, computer repair, laptop repair, computerwinkel, it support, "
  "windows installeren, netwerk, network",
  rx=r"\bcomputer|laptop|\bpcs?\b|desktop|printer|\btoner|\bit support|networking", scope="VH", r="it phones")
C("it", "IT & software", "IT & software", "TI y software", "IT与软件", "Informatique & logiciels", "TI e software",
  "ict, software, softwarebedrijf, software development, app, apps, app laten maken, programmeur, programmer, developer, "
  "hosting, cloud, cybersecurity, it bedrijf, it company, automatisering, systemen, erp, pos systeem, kassasysteem",
  sub="it-software", rx=r"software|\bict\b|\bit (solution|service|company|consult)|hosting|cyber|automation|automatiser",
  scope="V", r="computers web-design")
C("web-design", "Websites & marketing", "Websites & marketing", "Diseño web y marketing", "网站与营销", "Sites web & marketing", "Sites e marketing",
  "website, websites, website laten maken, webdesign, web design, webdesigner, webshop, webshop laten maken, marketing, "
  "online marketing, social media, social media marketing, seo, google ads, branding, logo, logo laten maken, reclame, "
  "reclamebureau, advertising, advertentie, graphic design, grafisch ontwerp, grafisch ontwerper, designer, content creator",
  rx=r"web ?design|website|webshop|marketing|social media|branding|\bseo\b|graphic design|grafisch|advertis|reclame|logo design",
  scope="V", r="printing it")
C("printing", "Printing & signs", "Drukwerk & reclameborden", "Imprenta y rótulos", "印刷与招牌", "Imprimerie & enseignes", "Gráfica e placas",
  "drukkerij, drukkerijen, drukwerk, printen, print, prints, printing, print shop, printshop, kopiëren, kopieën, kopie, copy, "
  "copies, copy center, flyers, flyer, posters, poster, visitekaartjes, business cards, stickers, sticker, banners, banner, "
  "borden, bord, reclamebord, reclameborden, signs, signage, lichtbak, bedrukking, bedrukken, t-shirt bedrukken, t-shirts bedrukken, "
  "t-shirt printing, zeefdruk, screen printing, borduren, embroidery, uitnodigingen, invitations, kwitantieboeken",
  rx=r"print|drukker|drukwerk|signage|\bsigns\b|copy cent|photocop|kopie|banner|sticker|screen ?print|embroider|borduur|lightbox",
  scope="VH", r="web-design")
C("mechanic", "Garages & mechanics", "Garages & monteurs", "Talleres mecánicos", "汽修", "Garages & mécaniciens", "Oficinas mecânicas",
  "garage, garages, autogarage, monteur, monteurs, automonteur, mechanic, mechanics, mekanieker, autoreparatie, auto reparatie, "
  "auto repareren, auto maken, auto repair, car repair, car service, onderhoud auto, auto onderhoud, auto service, apk, keuring, "
  "autokeuring, schadeherstel, uitdeuk, uitdeuken, uitdeukbedrijf, spuiten, spuiter, spuiterij, autospuiterij, auto spuiten, "
  "spuitinrichting, body shop, bodyshop, panel beating, uitlaat, remmen, brakes, versnellingsbak, olie verversen, oil change",
  rx=r"\bmechanics?\b|\bgarage\b(?! doors?)|auto ?repair|car repair|(repair|maintenance|servic)\w* (of|for|on) (vehicles|cars|trucks)|(vehicle|car|truck)s? (repair|servic|maintenance)|schadeherstel|spuit(erij|inrichting)|body ?shop|auto ?parts.{0,30}(repair|service)|(car|auto|vehicle) (repair|service) (shop|center|centre|workshop)|\bapk\b|autokeuring",
  scope="VH", neg=r"taxi|car rental|rent a car|autoverhuur|tracking|telematic", r="auto-parts tyres")
C("car-wash", "Car wash & detailing", "Carwash & autopoetsen", "Lavado de autos", "洗车", "Lavage auto", "Lava-jato",
  "car wash, carwash, car washes, karwash, autowas, autowasserij, auto wassen, wasstraat, detailing, car detailing, auto poetsen, "
  "poetsen, interieur reinigen, interieur reiniging, polijsten, ceramic coating, wax, wrap, car wrap",
  rx=r"car ?wash(es|ing)?\b(?! (product|shampoo|soap))|autowasserij|wasstraat|\bdetailing\b|car interior clean", scope="VH", neg=r"retailer|accessor", r="mechanic")
C("tyres", "Tyres & wheels", "Banden & velgen", "Llantas", "轮胎", "Pneus & jantes", "Pneus e rodas",
  "banden, band, bande, autobanden, bandenservice, banden service, bandenzaak, banden zaak, bandenwinkel, banden plakken, "
  "lekke band, band plakken, vulkaniseren, tyres, tyre, tires, tire, tyre shop, tire shop, tire repair, puncture, velgen, velg, "
  "rims, wheels, uitlijnen, wheel alignment, balanceren",
  rx=r"\btyres?\b|\btires?\b|\bbanden\b|bandenservice|velgen|\brims\b|wheel alignment|uitlijn", scope="HV", r="mechanic auto-parts")
C("auto-parts", "Car parts & accessories", "Auto-onderdelen", "Repuestos de auto", "汽车配件", "Pièces auto", "Autopeças",
  "onderdelen, auto onderdelen, auto-onderdelen, autoonderdelen, onderdeel, parts, auto parts, car parts, spare parts, "
  "accessoires, auto accessoires, car accessories, accu, accus, accu's, autoaccu, battery, batteries, olie, motorolie, "
  "filters, uitlaat, lampen auto, car audio, autoradio",
  sub="auto-parts", rx=r"(auto|car|spare|vehicle|truck) ?parts|auto-?onderdelen|car (accessor|audio|batter)|auto ?accessoires|\baccu", scope="HV",
  r="mechanic tyres", neg=r"veterin|livestock|agricultur")
C("cars", "Cars", "Auto's", "Autos", "汽车", "Voitures", "Carros",
  "auto, autos, auto's, car, cars, oto, wagen, wagens, voertuig, voertuigen, vehicle, vehicles, pickup, pick-up, suv, truck, trucks",
  sub="car-dealers automotive auto-parts", scope="", inc="car-dealer car-rental mechanic auto-parts tyres car-wash", fx="mechanic")
C("car-dealer", "Car dealers", "Autodealers", "Concesionarios", "汽车经销商", "Concessionnaires auto", "Concessionárias",
  "autodealer, autodealers, dealer, dealers, autohandel, autobedrijf, auto kopen, auto te koop, tweedehands auto, "
  "tweedehands auto's, occasion, occasions, nieuwe auto, car dealer, car dealers, car dealership, dealership, buy a car, "
  "used cars, used car, new cars, cars for sale, toyota, honda, nissan, suzuki, kia, hyundai, mitsubishi, isuzu, ford, "
  "chery, jeep, motor, motors, scooter, scooters, brommer, motorfiets",
  sub="car-dealers",
  rx=r"(car|auto|vehicle|motor|truck)s? ?dealer|dealership|autohandel|car sales|vehicle sales|used (cars?|vehicles?)|sells? (new |used )?(cars|vehicles)|verkoop van (auto|voertuig)",
  scope="HV", r="car-rental", fx="mechanic")
C("car-rental", "Car rental", "Autoverhuur", "Alquiler de autos", "租车", "Location de voitures", "Aluguel de carros",
  "autoverhuur, auto huren, auto verhuur, huurauto, huurauto's, huurautos, rent a car, rentacar, rent-a-car, car rental, "
  "car rentals, car hire, rental car, rent car, location voiture, location voitures, location de voiture, louer une voiture, "
  "alquiler de carro, alquiler de carros, alquiler auto, renta de autos, renta de carros, aluguel carro, aluguel de carro, alugar carro,  4x4 huren, jeep huren, pickup huren, busje huren, bus huren, vehicle rental",
  rx=r"car rental|rent[- ]a[- ]car|autoverhuur|car hire|vehicle rental|huurauto|rent(s|al)?\b.{0,30}(cars|vehicles|4x4|jeeps|suvs)|(cars|vehicles|4x4s?) for (hire|rent)",
  scope="VHA", r="taxi car-dealer")
C("taxi", "Taxis & transfers", "Taxi & vervoer", "Taxis y traslados", "出租车与接送", "Taxis & transferts", "Táxis e transfers",
  "bus, bussen, lijnbus, busdienst, nvb, minibus, ferry, veerboot, veerpont, pont, taxi, taxis, taxi's, taxibedrijf, taxicentrale, taxi bestellen, cab, chauffeur, chauffeurs, driver, airport transfer, "
  "airport taxi, vliegveld taxi, transfer, transfers, vervoer, personenvervoer, shuttle, shuttles, busvervoer, rit, ride, "
  "wagiman, ophalen vliegveld, ophalen",
  rx=r"\btaxi|airport transfer|shuttle|chauffeur|transport services?\b|personenvervoer|bus (service|transport)", scope="VA",
  r="car-rental")
C("moving", "Moving & towing", "Verhuizen & takelen", "Mudanzas y grúas", "搬家与拖车", "Déménagement & dépannage", "Mudanças e guincho",
  "verhuizen, verhuizing, verhuisbedrijf, verhuizers, verhuisdienst, movers, moving, moving company, removals, takelen, "
  "takelbedrijf, takeldienst, takelwagen, sleepdienst, slepen, towing, tow truck, wrecker, kraan, kraanverhuur, crane, "
  "vrachtvervoer, vrachtwagen, truck huren, transport",
  rx=r"\bmoving (company|service)|removals? (company|service)|verhuisbedrijf|verhuizing|towing|tow truck|takeldienst|takelbedrijf|kraanverhuur|crane (rental|hire|services)", scope="V", r="shipping", neg=r"hair|ontharing|waxing")
C("shipping", "Shipping & couriers", "Verzenden & koeriers", "Envíos y mensajería", "货运与快递", "Expédition & coursiers", "Envios e entregas",
  "verzenden, verzending, opsturen, versturen, verscheping, verschepen, shipping, ship, cargo, freight, vracht, koerier, "
  "koeriers, koeriersdienst, courier, couriers, pakket, pakketten, pakketdienst, package, packages, parcel, container, "
  "containers, douane, customs, inklaring, inklaren, expeditie, expediteur, logistics, logistiek, barrel, barrels, drum, drums, "
  "dhl, fedex, ups, post, postkantoor, surpost, luchtvracht, zeevracht, air freight, sea freight",
  sub="shipping-logistics",
  rx=r"shipping (company|agent|agency|services?|line)|cargo|freight forward|sea freight|air freight|courier|koerier|\bparcels?\b|pakketdienst|verschep|expediteur|customs (clearance|broker)|douane-?(agent|expediteur)|inklaring|barrels?\b|zeevracht|luchtvracht",
  scope="V", r="moving", neg=r"travel agen|reisbureau|holiday|vakantie|oil ?field|energy")
C("generator", "Generators", "Generatoren", "Generadores", "发电机", "Groupes électrogènes", "Geradores",
  "generator, generatoren, generators, aggregaat, aggregaten, generator verhuur, generatorverhuur, noodstroom, back-up power, "
  "backup power, stroomvoorziening",
  rx=r"generator|aggregaat|back-?up power|noodstroom|power solutions", scope="VH", r="solar electrician")
C("solar", "Solar energy", "Zonne-energie", "Energía solar", "太阳能", "Énergie solaire", "Energia solar",
  "zonnepanelen, zonnepaneel, zonne energie, zonne-energie, zonneboiler, zonneboilers, solar, solar panels, solar panel, "
  "solar energy, solar power, solar system, omvormer, omvormers, inverter, inverters, thuisbatterij",
  rx=r"\bsolar\b|zonnepane|zonne-?energie|zonneboiler|photovolta|\binverters?\b", scope="VH", r="generator electrician", neg=r"sunglass|zonnebril")
C("security", "Security & cameras", "Beveiliging & camera's", "Seguridad y cámaras", "安保与监控", "Sécurité & caméras", "Segurança e câmeras",
  "beveiliging, beveiligingsbedrijf, beveiligingsdienst, bewaking, bewakingsdienst, bewaker, bewakers, security, security company, "
  "guard, guards, security guard, alarm, alarmen, alarmsysteem, alarmsystemen, camera, cameras, camera's, cctv, "
  "beveiligingscamera, beveiligingscamera's, bewakingscamera, dvr, nvr, poortmotor, poortmotoren, gate motor, brandbeveiliging, "
  "brandblusser, brandblussers, fire extinguisher, fire safety",
  sub="security",
  rx=r"security (company|services?|guard|solution|system)|beveilig|bewaking|cctv|\bcameras?\b|alarm|fire (safety|protection|extinguish)|brandblus",
  scope="VH", r="locksmith")
C("locksmith", "Locksmiths & keys", "Slotenmakers & sleutels", "Cerrajeros", "锁匠", "Serruriers", "Chaveiros",
  "slotenmaker, slotenmakers, sloten, slot, sleutel, sleutels, sleutels bijmaken, sleutel bijmaken, sleutelservice, keyshop, "
  "locksmith, locksmiths, key, keys, key cutting, locks, buitengesloten",
  rx=r"locksmith|slotenmak|key cutting|sleutels? ?(bijmaken|service|dienst)|sleuteldienst", scope="VH", r="")

# ── Beauty and personal care ───────────────────────────────────────────────
C("hair", "Hairdressers & barbers", "Kappers & barbershops", "Peluquerías y barberías", "理发店", "Coiffeurs & barbiers", "Cabeleireiros e barbearias",
  "cabeleireiro, cabeleireiros, cabeleireira, peluqueria, peluquero, coiffeur, coiffeurs, kapper, kappers, kapsalon, kapsalons, kappersalon, kapperszaak, thuiskapper, dames kapper, dameskapper, haar, haren, "
  "haar knippen, haar laten knippen, knippen, kapsel, kapsels, haarstylist, haarstyliste, hairstylist, hairstylists, hairstyle, "
  "hairstyles, hairdresser, hairdressers, hair salon, hair salons, hair, hairstudio, hair studio, curls, krullen, natural hair, "
  "dreads, locs, relaxer, weave, weaves, wig, wigs, pruik, pruiken, haarverf, haar verven, highlights, keratine, "
  "extensions, hair extensions, blowout, föhnen",
  rx=r"\bhair|kapper|kapsalon|barber|kapsel|\bcurls?\b|\bweaves?\b|\bwigs?\b|\blocs\b|dreadlock|pruik", scope="V", neg=r"hair removal|haarverwijder|ontharing",
  r="barber braids beauty")
C("barber", "Barbers", "Barbershops", "Barberías", "男士理发", "Barbiers", "Barbearias",
  "barbier, barbiers, barber, barbers, barbershop, barbershops, barber shop, barberzaak, herenkapper, heren kapper, "
  "kapper heren, mannenkapper, fade, fades, baard, baard trimmen, beard, line up, lineup",
  rx=r"barber|herenkapper|men'?s (hair|groom|cut)|\bbeard|\bbaard", scope="V", r="hair")
C("nails", "Nail studios", "Nagelstudio's", "Salones de uñas", "美甲", "Onglerie", "Manicure e unhas",
  "nagelstudio, nagelstudios, nagelstudio's, nagel studio, nagelsalon, nagelsalons, nagelstylist, nagelstyliste, nagelstylisten, "
  "nagelstyling, nagels, nagel, nagels laten doen, nagels laten zetten, nails, nail, nailz, nail salon, nail salons, nail studio, "
  "nail tech, nail technician, nail art, manicure, manicures, pedicure, pedicures, gelnagels, gel nagels, gellak, acryl, "
  "acrylnagels, acryl nagels, acrylic nails, acrylic, biab, polygel",
  rx=r"\bnails?\b|\bnail (art|salon|studio|tech|care)|nagel|manicure|pedicure|gel ?polish|acrylic", scope="V",
  neg=r"nails? and screws|nails, screws|spijker|hammer", r="beauty lashes")
C("lashes", "Lashes & brows", "Wimpers & wenkbrauwen", "Pestañas y cejas", "睫毛与眉毛", "Cils & sourcils", "Cílios e sobrancelhas",
  "wimpers, wimper, wimperextensions, wimper extensions, wimperstyliste, wimperstylist, wimpers zetten, lashes, lash, lash studio, "
  "lash tech, lash extensions, eyelash, eyelashes, eyelash extensions, lash lift, brows, brow, wenkbrauwen, wenkbrauw, "
  "microblading, micropigmentatie, micropigmentation, pmu, permanente make-up, henna brows, threading",
  rx=r"\blash(es)?\b|eyelash|wimper|\bbrows?\b|wenkbrauw|microblad|micropigment|permanent make-?up|threading", scope="V",
  neg=r"splash", r="beauty nails makeup")
C("makeup", "Make-up", "Make-up & visagie", "Maquillaje", "化妆", "Maquillage", "Maquiagem",
  "make-up, makeup, make up, visagie, visagist, visagiste, mua, make-up artist, makeup artist, bruidsmake-up, bridal makeup, "
  "cosmetica, cosmetics",
  rx=r"make-?up|visagi|\bmua\b|cosmetic", scope="VH", r="beauty lashes")
C("braids", "Braids", "Vlechten", "Trenzas", "编发", "Tresses", "Tranças",
  "vlechten, vlechtjes, vlecht, braids, braid, braiding, braider, braidz, knotless, knotless braids, box braids, cornrows, "
  "twists, haar vlechten",
  rx=r"braid|vlecht|cornrow|twists", scope="V", r="hair")
C("spa", "Spa & massage", "Spa & massage", "Spa y masajes", "水疗与按摩", "Spa & massage", "Spa e massagem",
  "massage, massages, masseur, masseuse, massagesalon, spa, spas, dayspa, day spa, wellness, wellnesscentrum, sauna, "
  "facial, facials, gezichtsbehandeling, huidverzorging, huidtherapeut, skincare, skin care, waxing, harsen, ontharen, "
  "laser ontharing, body treatment, lichaamsbehandeling, ontspanning",
  rx=r"massage|\bspas?\b|wellness|sauna|facial|gezichtsbehandel|skin ?care|huidverzorg|waxing|harsen|ontharing", scope="V",
  r="beauty", neg=r"\bgym\b|fitness|crossfit|yoga studio|pilates studio|boxing")
C("beauty", "Beauty salons", "Schoonheidssalons", "Salones de belleza", "美容院", "Instituts de beauté", "Salões de beleza",
  "salao de beleza, salon de belleza, salon de beaute, institut de beaute, estetica, schoonheidssalon, schoonheidssalons, schoonheidsspecialiste, beauty salon, beauty salons, beautysalon, beauty, beauty studio, "
  "salon, salons, schoonheid, glow up",
  sub="beauty-wellness", scope="V", r="hair nails spa")
C("tattoo", "Tattoo & piercing", "Tattoo & piercing", "Tatuajes y piercing", "纹身与穿孔", "Tatouage & piercing", "Tatuagem e piercing",
  "tattoo, tattoos, tatoeage, tatoeages, tatoeëren, tattoo shop, tattoo studio, tattoo artist, tatoo, tattoe, tatto, "
  "piercing, piercings",
  rx=r"tattoo|tatoe|piercing", scope="V")

# ── Events, media, creative ────────────────────────────────────────────────
C("photographer", "Photographers & video", "Fotografen & video", "Fotógrafos y video", "摄影摄像", "Photographes & vidéo", "Fotógrafos e vídeo",
  "fotograaf, fotografen, fotografie, fotoshoot, foto shoot, photoshoot, photo shoot, fotos maken, foto's maken, photographer, "
  "photographers, photography, videograaf, videografen, videografie, videographer, videography, video, videos, filmen, "
  "drone, dronebeelden, trouwfotograaf, bruiloft fotograaf, wedding photographer, event photographer, fotostudio, photo studio",
  rx=r"photograph|fotogra|videogra|photo (and|&) video|foto(- en| en|&) video|video production|videoproductie|drone (footage|shots|video)",
  scope="V", r="printing web-design")
C("dj-sound", "DJs & sound systems", "DJ's & geluid", "DJ y sonido", "DJ与音响", "DJ & sonorisation", "DJ e som",
  "dj, djs, dj's, deejay, sound system, soundsystem, geluid, geluidsinstallatie, geluid en licht, licht en geluid, boxen, "
  "speakers, speaker huren, boxen huren, pa systeem, audio, audio verhuur, licht, lighting, presentator, live band, "
  "muzikanten, musicians, entertainment",
  rx=r"\bdj\b|\bdjs\b|sound (system|equipment|rental)|geluidsinstall|audio(visual| visual| equipment| rental)|\bpa (system|rental)|lighting (rental|equipment)|licht en geluid|live band",
  scope="V", neg=r"car audio|vehicles?|auto", r="party-rental")
C("party-rental", "Party & event rental", "Feest- en eventverhuur", "Alquiler para fiestas", "派对与活动租赁", "Location pour fêtes", "Aluguel para festas",
  "tenten, tent, tenten huren, tent huren, partytent, partytenten, feesttent, zinkententen, stoelen, tafels, stoelen huren, "
  "tafels huren, stoelen en tafels, tafelkleden, partyverhuur, feestverhuur, verhuurbedrijf, party rental, party rentals, "
  "event rental, tent rental, chairs, tables, chair rental, springkussen, springkussens, bounce house, bouncy castle, "
  "soft play, ijsbox, mobiele toiletten, dixi",
  rx=r"(tents?|chairs|tables)\b.{0,30}(rental|hire|verhuur|for rent)|(rental|verhuur|hire|rents?) (of )?.{0,40}(tents|chairs|tables)|soft play|bounc|springkussen|event (rental|equipment)|party (rental|equipment)|partytent|ijsbox",
  scope="VH",
  r="party-supplies catering dj-sound")
C("party-supplies", "Party supplies & decoration", "Feestartikelen & decoratie", "Artículos de fiesta", "派对用品与装饰", "Articles de fête & déco", "Artigos de festa",
  "feestartikelen, feest artikelen, party supplies, party shop, partyshop, party winkel, ballonnen, ballon, balloons, balloon, "
  "decoratie, decoraties, decor, decoration, decorations, versiering, slingers, verjaardag versiering, babyshower, baby shower, "
  "gender reveal, disposables, wegwerp, verpakking, packaging, bakbenodigdheden, baking supplies",
  rx=r"party (supplies|shop|decor|store)|balloon|ballon|feestartikel|party decoration|feestversiering|baking supplies",
  scope="VH", r="party-rental flowers")
C("party", "Parties & weddings", "Feesten & bruiloften", "Fiestas y bodas", "派对与婚礼", "Fêtes & mariages", "Festas e casamentos",
  "feest, feesten, feestje, party, parties, verjaardag, verjaardagsfeest, birthday, birthday party, kinderfeestje, kinderfeest, "
  "bruiloft, bruiloften, trouwen, trouwerij, wedding, weddings, huwelijk, jubileum, event organiseren, evenement organiseren, "
  "event planner, eventplanner, wedding planner, weddingplanner",
  inc="party-rental party-supplies catering cakes dj-sound photographer flowers", scope="")
C("catering", "Catering", "Catering", "Catering", "餐饮外送", "Traiteurs", "Bufê e catering",
  "catering, cateraar, cateraars, caterer, caterers, cateren, cateringbedrijf, eten op bestelling, bestellen eten, buffet, "
  "buffetten, private chef, personal chef, kok aan huis, chef aan huis, live cooking, live wok, bbq catering, hapjes, "
  "snacks bestellen, borrelhapjes, lunch op kantoor, maaltijden, meal prep",
  rx=r"\bcater(ing|er|ers|s)?\b|personal chef|private chef|\bbuffets?\b|kok aan huis|live (wok|cooking)|meal prep",
  scope="EV", r="cakes party")
C("flowers", "Florists & flowers", "Bloemisten & bloemen", "Floristerías", "花店", "Fleuristes", "Floriculturas",
  "bloemen, bloem, bloemist, bloemisten, bloemisterij, bloemenzaak, bloemen bezorgen, boeket, boeketten, florist, florists, "
  "flowers, flower, flower delivery, bouquet, bouquets, orchideeën, orchidee, orchids, rozen, roses, planten, plants",
  rx=r"florist|bloem(ist|en|isterij)|flowers?\b|bouquet|boeket|orchid", scope="VH",
  neg=r"butterfly|flower(ing)? (garden|trees|plants) of|bloemrijk", r="gardening gifts")

# ── Food: types, cuisines, dishes ──────────────────────────────────────────
C("cakes", "Cakes & pastries", "Taarten & gebak", "Pasteles y repostería", "蛋糕与糕点", "Gâteaux & pâtisseries", "Bolos e doces",
  "taart, taarten, taartje, taartjes, taarten bestellen, taart bestellen, verjaardagstaart, verjaardagstaarten, bruidstaart, "
  "bruidstaarten, slagroomtaart, kuku, bojo, fiadu, keksi, gebak, gebakje, gebakjes, cake, cakes, birthday cake, wedding cake, "
  "custom cake, cupcake, cupcakes, pastry, pastries, patisserie, banketbakker, banketbakkerij, koekjes, koek, cookies, cookie, "
  "brownies, cheesecake, donuts, donut, dessert, desserts, zoetigheden, sweets, lekkernijen",
  rx=r"\bcakes?\b|taart|cupcake|pastr(y|ies)|patisser|\bgebak(je|jes)?\b|\bbojo|fiadu|keksi|cookies?\b|\bkoek(jes)?\b|brownie|cheesecake|donut|doughnut|\bsweets\b|lekkernij",
  scope="EH", r="bakery")
C("bakery", "Bakeries", "Bakkerijen", "Panaderías", "面包店", "Boulangeries", "Padarias",
  "bakker, bakkers, bakkerij, bakkerijen, bakery, bakeries, baker, bakers, brood, broden, broodjes, broodje, bread, breads, "
  "bakri, bakriman, banket, croissant, croissants, zuurdesem, sourdough, bakeshop",
  sub="bakeries-sweets", rx=r"baker|bakkerij|\bbreads?\b|\bbrood|broodje|croissant|sourdough", scope="EH",
  neg=r"ice ?cream|gelato|\bijs", r="cakes")
C("roti", "Roti", "Roti", "Roti", "印度烤饼", "Roti", "Roti",
  "roti, roti's, rotis, rotishop, roti shop, rotishops, rotiwinkel, roti winkel, roti kip, roti met kip, dhal puri, dhalpuri, "
  "dalpuri, aloo roti, bara, baras, phulauri, pholourie, foelorie, phulourie",
  sub="roti-hindustani", rx=r"\broti|\bbara\b|phulauri|pholourie|dhal ?puri", scope="E", r="hindustani")
C("hindustani", "Hindustani & Indian food", "Hindostaans & Indiaas eten", "Comida hindostana e india", "印度斯坦与印度菜", "Cuisine hindoustanie & indienne", "Comida hindustani e indiana",
  "indio, indien, indiana, hindostaans, hindostaanse, hindoestaans, hindoestaanse, hindustani, indian, indiaas, indiase, indian food, curry, masala, "
  "tandoori, biryani, naan, dhal, chutney, samosa, samosas",
  sub="roti-hindustani indian", rx=r"hindustan|hindosta|hindoesta|\bindian (food|cuisine|dishes|restaurant)|indiase|\bcurry|masala|tandoor|biryani|samosa",
  scope="E", r="roti")
C("javanese", "Javanese & Indonesian food", "Javaans & Indonesisch eten", "Comida javanesa", "爪哇与印尼菜", "Cuisine javanaise", "Comida javanesa",
  "javaans, javaanse, javanese, javanese food, javaans eten, warung, warungs, waroeng, warong, bami, nasi, bami nasi, "
  "nasi goreng, bami goreng, mie goreng, saoto, soto, saoto soep, saté, sate, satay, pitjel, petjel, telo, dawet, tjendol, "
  "rijsttafel, indonesisch, indonesian, kampong, lontong, bakmi",
  sub="javanese-warung", rx=r"javan|javaans|warung|\bbami\b|\bnasi\b|saoto|\bsoto\b|\bsat[eé]\b|satay|pitjel|petjel|dawet|indonesi",
  scope="E", r="chinese")
C("chinese", "Chinese food", "Chinees eten", "Comida china", "中餐", "Cuisine chinoise", "Comida chinesa",
  "chino, chinois, chinesa, chinees, chinese, chinese food, chinees eten, chinese restaurant, chinees restaurant, chinese takeaway, afhaal chinees, "
  "snesi, snesie, dim sum, dimsum, tjauw min, tjauwmin, chow mein, chowmein, moksi meti, wonton, wontons, loempia, loempias, "
  "foe yong hai, fu yong, peking eend, peking duck, kantonees, cantonese, hot pot, hotpot, noodles, noedels",
  sub="chinese", rx=r"chines|chinees|dim ?sum|tjauw|chow ?mein|wonton|loempia|canton|kantonees|hot ?pot|szechuan|sichuan",
  scope="E", r="asian")
C("creole", "Creole & Surinamese food", "Creools & Surinaams eten", "Comida criolla y surinamesa", "克里奥尔与苏里南菜", "Cuisine créole & surinamaise", "Comida crioula e surinamesa",
  "comida tipica, comida surinamesa, comida local, cuisine locale, plats typiques, comida tipica surinamesa, creools, creoolse, creole, creole food, surinaams, surinaamse, surinaams eten, surinamese, surinamese food, local food, "
  "lokaal eten, lokale keuken, moksi alesi, moksi aleisi, moksi-alesi, moksie alesie, alesi, aleisi, pindasoep, heri heri, "
  "bakabana, podosiri, brafu, okersoep, peprewatra, bruine bonen, bruinebonen, kousenband, tayer, bakkeljauw, saltfish, "
  "pastei, bara, dyogo, sopropo, bravoe",
  sub="creole-surinamese",
  rx=r"creol|creool|surinamese (food|cuisine|dish|kitchen|home|classics|specialt)|surinaamse (keuken|gerecht|specialit)|moksi|\bpom\b|pindasoep|heri ?heri|bakabana|podosiri|bruine bonen|peprewatra|local (food|dish|cuisine)",
  scope="E", r="javanese hindustani")
C("pom", "Pom", "Pom", "Pom", "Pom 焗菜", "Pom", "Pom",
  "pom, broodje pom, pom broodje, pom sandwich, pomtayer, pom tayer",
  rx=r"\bpom\b", scope="E", r="creole")
C("snacks", "Snacks & fast food", "Snacks & fastfood", "Snacks y comida rápida", "小吃与快餐", "Snacks & restauration rapide", "Lanches e fast-food",
  "snack, snacks, snackbar, snackbars, snackhuis, frituur, friet, frietjes, patat, patatje, fries, french fries, kip, chicken, "
  "fried chicken, kippenpootjes, wings, chicken wings, fastfood, fast food, takeaway, take away, afhaal, afhalen, kroket, "
  "kroketten, frikandel, broodjes, sandwiches, sandwich, hotdog, hot dog, shoarma, shawarma, gyros, kebab, wraps",
  sub="fast-food", rx=r"snack|fast ?food|fried chicken|\bfries|friet|patat|takeaway|take-away|afhaal|shawarma|shoarma|\bkebab|\bwings\b",
  scope="EH", r="burger")
C("burger", "Burgers", "Burgers", "Hamburguesas", "汉堡", "Burgers", "Hambúrgueres",
  "burger, burgers, hamburger, hamburgers, cheeseburger, smash burger, smashburger",
  rx=r"burger", scope="E", r="snacks")
C("pizza", "Pizza & Italian", "Pizza & Italiaans", "Pizza e italiana", "披萨与意大利菜", "Pizza & italien", "Pizza e italiana",
  "italiano, italienne, italiana, pizza, pizzas, pizza's, pizzeria, italian, italiaans, italiaanse, pasta, lasagne, lasagna, spaghetti, risotto",
  sub="pizza-italian", rx=r"pizz|italian|italiaans|\bpasta\b|lasagn", scope="E")
C("sushi", "Sushi & Japanese", "Sushi & Japans", "Sushi y japonesa", "寿司与日料", "Sushi & japonais", "Sushi e japonesa",
  "japones, japonais, japonesa, sushi, zushi, sashimi, maki, japanese, japans, japanse, teppanyaki, ramen, poke, poke bowl, yakitori, tempura",
  sub="japanese-sushi", rx=r"sushi|zushi|sashimi|japan|teppanyaki|ramen|\bpok[eé]\b|yakitori|tempura", scope="E", r="asian")
C("asian", "Asian food", "Aziatisch eten", "Comida asiática", "亚洲菜", "Cuisine asiatique", "Comida asiática",
  "aziatisch, aziatische, asian, asian food, thai, thais, thaise, korean, koreaans, koreaanse, vietnamese, vietnamees, pho, "
  "fusion, wok, noodle bar, noodles, bubble tea, boba",
  sub="asian-other japanese-sushi chinese", rx=r"\basian|aziat|\bthai\b|thais|korea|vietnam|\bpho\b|\bwok\b|noodle|bubble tea|\bboba",
  scope="E", r="chinese sushi")
C("thai", "Thai food", "Thais eten", "Comida tailandesa", "泰国菜", "Cuisine thaïe", "Comida tailandesa",
  "thai, thais, thaise, thai food, pad thai, tom yum, green curry, groene curry",
  rx=r"\bthai\b|thais", scope="E", r="asian")
C("latin", "Latin & Mexican food", "Latijns-Amerikaans eten", "Comida latina y mexicana", "拉美与墨西哥菜", "Cuisine latino & mexicaine", "Comida latina e mexicana",
  "mexicano, mexicain, brasileno, brasileiro, bresilien, latin, latijns, latino, mexican, mexicaans, mexicaanse, tacos, taco, burrito, burritos, nachos, quesadilla, brazilian, "
  "braziliaans, braziliaanse, churrasco, rodizio, colombian, venezuelan, arepa, arepas, empanadas, peruvian, ceviche",
  sub="latin-american", rx=r"\blatin|latijns|mexic|tacos?\b|burrito|brazil|churrasc|rodizio|colombia|venezuel|arepa|empanada|peru|ceviche",
  scope="E")
C("grill", "Grill, BBQ & steak", "Grill, BBQ & steak", "Parrilla y carnes", "烧烤与牛排", "Grill, barbecue & steak", "Churrasco e grelhados",
  "bbq, barbecue, barbeque, grill, grillroom, gegrild, grilled, steak, steaks, steakhouse, ribs, spareribs, vlees, meat, "
  "kip van de grill, smokehouse, shashlik",
  sub="grill-steak", rx=r"\bbbq\b|barbe(cue|que)|\bgrill|steak|\bribs\b|spareribs|smokehouse", scope="E", r="snacks")
C("seafood", "Fish & seafood", "Vis & zeevruchten", "Pescados y mariscos", "海鲜", "Poissons & fruits de mer", "Peixes e frutos do mar",
  "mariscos, pescado, poisson, fruits de mer, frutos do mar, peixe, vis, visgerechten, gebakken vis, fish, fish dishes, seafood, zeevruchten, garnalen, shrimp, shrimps, prawns, krab, krabben, "
  "crab, kreeft, lobster, oesters, oysters, octopus, inktvis, calamari, kwi kwi, kwikwi, snoek, zalm, salmon",
  rx=r"seafood|\bfish\b|\bvis\b|zeevrucht|shrimp|garnal|prawn|\bcrab|\bkrab|lobster|kreeft|oyster|oester|octopus|calamar|kwi ?kwi",
  scope="EH", r="butcher", neg=r"fishing (gear|tackle|equipment|rod|store|shop)|hengel")
C("vegan", "Vegan & vegetarian", "Vegan & vegetarisch", "Vegano y vegetariano", "素食", "Végan & végétarien", "Vegano e vegetariano",
  "vegano, vegetariano, vegetalien, vegetarien, vegan, veganistisch, veganistische, vegetarisch, vegetarische, vegetarian, veggie, plantaardig, plant based, plant-based",
  rx=r"vegan|vegetar|veggie|plant[- ]?based|plantaardig", scope="E", r="healthy")
C("healthy", "Healthy food & juices", "Gezond eten & sappen", "Comida saludable y jugos", "健康餐与果汁", "Cuisine saine & jus", "Comida saudável e sucos",
  "gezond, gezond eten, gezonde, healthy, healthy food, salade, salades, salad, salads, smoothie, smoothies, juice bar, sapjes, "
  "verse sappen, fresh juice, bowls, poke bowl, acai, açaí, glutenvrij, gluten free, keto, suikervrij, sugar free",
  rx=r"\bhealthy|gezond|salad|smoothie|juice bar|fresh juice|verse sap|\bacai|açaí|gluten|keto", scope="E", r="vegan")
C("halal", "Halal food", "Halal eten", "Comida halal", "清真食品", "Cuisine halal", "Comida halal",
  "halal", rx=r"halal", scope="EH")
C("coffee", "Coffee & cafés", "Koffie & cafés", "Café y cafeterías", "咖啡馆", "Cafés", "Cafés",
  "koffie, koffietent, koffiebar, coffee, coffee shop, coffeeshop, coffee bar, cafe, cafés, cafes, café, espresso, cappuccino, "
  "latte, iced coffee, ijskoffie, barista, lunchroom, lunchrooms, thee, tea, tearoom",
  sub="cafes-coffee", rx=r"coffee|koffie|\bcaf[eé]s?\b|espresso|cappuccino|\blatte|barista|lunchroom|tearoom", scope="E",
  r="breakfast")
C("breakfast", "Breakfast & brunch", "Ontbijt & brunch", "Desayuno y brunch", "早餐与早午餐", "Petit-déjeuner & brunch", "Café da manhã e brunch",
  "ontbijt, ontbijten, ontbijtje, breakfast, brunch, brunchen, lunch, lunchen, pancakes, pannenkoeken, poffertjes, eggs benedict, "
  "omelet, wafels, waffles",
  rx=r"breakfast|ontbijt|brunch|\blunch|pancake|pannenkoek|waffle|wafel", scope="E", r="coffee")
C("ice-cream", "Ice cream & desserts", "IJs & desserts", "Helados y postres", "冰淇淋与甜品", "Glaces & desserts", "Sorvetes e sobremesas",
  "ijs, ijsje, ijsjes, ijssalon, ijswinkel, schepijs, softijs, schaafijs, ice cream, icecream, ice-cream, gelato, sorbet, "
  "sundae, milkshake, milkshakes, frozen yoghurt, froyo, waffles, dessert bar",
  rx=r"ice ?cream|\bijs(je|jes|salon)?\b|gelato|sorbet|sundae|frozen yo|schaafijs|desserts?\b|churro", scope="EH", r="cakes")
C("bar", "Bars & nightlife", "Bars & uitgaan", "Bares y vida nocturna", "酒吧与夜生活", "Bars & sorties", "Bares e vida noturna",
  "bar, bars, lounge, lounges, cafe bar, kroeg, kroegen, pub, pubs, borrel, borrelen, uitgaan, nightlife, nachtleven, club, "
  "clubs, nachtclub, nightclub, disco, discotheek, dansen, party, cocktails, cocktail, cocktailbar, drinks, drankjes, bier, "
  "beer, wijn, wine, wine bar, hookah, shisha, waterpijp, karaoke, rooftop, happy hour, live muziek, live music, sports bar",
  sub="bars-lounges", rx=r"(?<!snack )(?<!coffee )(?<!noodle )(?<!sushi )(?<!juice )(?<!salad )(?<!beauty )(?<!nail )(?<!lash )(?<!brow )(?<!sandwich )(?<!dessert )\bbar\b|lounge|\bpub\b|nightclub|night club|\bclub\b|cocktail|hookah|shisha|karaoke|rooftop|happy hour|nightlife",
  scope="EA", r="dj-sound")
C("restaurant", "Restaurants", "Restaurants", "Restaurantes", "餐厅", "Restaurants", "Restaurantes",
  "restaurant, restaurants, restaurnt, resto, comida, comer, onde comer, donde comer, manger, ou manger, where to eat,  restaurantje, eten, uit eten, uiteten, eetgelegenheid, eetgelegenheden, eetcafe, "
  "eetcafé, eethuis, food, dining, dinner, diner, avondeten, eat, eating, where to eat, places to eat, nyanyan, nyan",
  sub="cafes-coffee bakeries-sweets bars-lounges fast-food creole-surinamese restaurants chinese grill-steak javanese-warung "
      "asian-other pizza-italian latin-american japanese-sushi roti-hindustani indian",
  scope="E")

# ── Stay ───────────────────────────────────────────────────────────────────
C("hotel", "Hotels", "Hotels", "Hoteles", "酒店", "Hôtels", "Hotéis",
  "hospedagem, hospedagem barata, alojamiento, hebergement, hotel, hotels, hotell, hotelkamer, kamer, kamers, room, rooms, overnachten, overnachting, slapen, verblijf, verblijven, "
  "accommodatie, accommodation, accommodations, stay, sleep, place to stay, where to stay, boutique hotel, suites",
  sub="city-hotels casino-hotels resorts guesthouses eco-lodges", scope="S", inc="")
C("guesthouse", "Guesthouses & apartments", "Pensions & appartementen", "Casas de huéspedes y apartamentos", "民宿与公寓", "Maisons d'hôtes & appartements", "Pousadas e apartamentos",
  "aparthotel, apartotel, apart hotel, pousada, pousadas, hostal, posada, guesthouse, guesthouses, guest house, pension, pensions, appartement, appartementen, apartment, apartments, vakantiewoning, "
  "vakantiehuis, vakantiehuizen, holiday home, villa, villas, bungalow, bungalows, airbnb, b&b, bnb, bed and breakfast, "
  "studio, kamer huren, kamerverhuur, room for rent, long stay, kort verblijf",
  sub="guesthouses", rx=r"guest ?house|pension|apartment|appartement|villa|bungalow|holiday home|vakantie(woning|huis)|b&b|bed and breakfast",
  scope="S", r="hotel")
C("lodge", "Eco lodges & jungle stays", "Lodges & binnenland", "Ecolodges", "生态小屋", "Écolodges", "Ecolodges",
  "lodge, lodges, ecolodge, eco lodge, eco-lodge, jungle lodge, jungle, binnenland, binnenlandreis, oerwoud, regenwoud, "
  "rainforest, kamp, camp, camping, hangmat, hammock, kampeerplek, riverside, rivier, river lodge",
  sub="eco-lodges", rx=r"\blodge|eco ?resort|jungle|rainforest|regenwoud|binnenland|\bcamp\b|camping|hammock|hangmat",
  scope="SA", r="resort tours")
C("resort", "Resorts & day recreation", "Resorts & recreatieoorden", "Resorts", "度假村", "Complexes & resorts", "Resorts",
  "resort, resorts, recreatieoord, recreatieoorden, recreatie, recreatiepark, dagrecreatie, dagje uit, uitje, uitjes, "
  "zwembad, zwembaden, swimming pool, pool, pools, swimming, zwemmen, all inclusive, getaway, weekendje weg, staycation",
  sub="resorts", rx=r"\bresort|recreat|swimming pool|zwembad|\bpools?\b|day ?trip", scope="SAN", r="lodge hotel")
C("casino", "Casinos", "Casino's", "Casinos", "赌场", "Casinos", "Cassinos",
  "casino, casinos, casino's, gokken, gamble, gambling, slots, slot machines, gokkasten, bingo, poker, roulette",
  sub="casino-hotels", rx=r"casino|bingo|slot machines|gambl|poker", scope="SAVE", neg=r"pizza")
C("river", "River & waterfront", "Rivier & aan het water", "Río y frente al agua", "河畔", "Rivière & bord de l'eau", "Rio e beira-rio",
  "rivier, rivieren, river, riverside, river view, aan de rivier, aan het water, waterfront, waterkant, kreek, creek, "
  "sula, sulas, stroomversnelling, rapids, waterfall, waterval, watervallen, lake, meer, stuwmeer, brokopondo stuwmeer",
  rx=r"\briver|rivier|riverside|waterfront|kreek|\bcreek|rapids|stroomversnell|waterfall|waterval|\blake\b|stuwmeer",
  scope="SAEN", r="lodge tours")

# ── Things to do ───────────────────────────────────────────────────────────
C("tours", "Tours & excursions", "Tours & excursies", "Tours y excursiones", "旅游与短途游", "Excursions & visites", "Passeios e excursões",
  "pirogue, excursion en pirogue, canoa, passeio de barco, paseo en bote, kanotocht, boot, boten, boat, boats, boottochten, tour, tours, touroperator, tour operator, excursie, excursies, uitstap, uitstapje, uitstapjes, trip, trips, dagtrip, "
  "dagtocht, rondleiding, rondreis, guide, gids, reisgids, binnenlandtour, jungletour, jungle tour, boottocht, boat tour, "
  "boat trip, river cruise, dolfijnen, dolphins, dolphin tour, kaaimannen, caimans, birdwatching, vogels kijken, "
  "plantagetour, plantation tour, fietstour, bike tour, kanoën, kayak, kayaking, kano, korjaal, avontuur, adventure",
  sub="tours-expeditions",
  rx=r"\btours?\b|excursion|excursie|expedition|boat (trip|tour)|river cruise|dolphin|dolfijn|birdwatch|kayak|canoe|kano|korjaal",
  scope="AV", neg=r"travel agency|reisbureau", r="lodge river")
C("things-to-do", "Things to do", "Wat te doen", "Qué hacer", "玩乐", "Que faire", "O que fazer",
  "things to do, what to do, wat te doen, wat is er te doen, bezienswaardigheden, bezienswaardigheid, sightseeing, attractions, "
  "attraction, uitstapjes, dagje uit, que hacer, cosas para hacer, cosas que hacer, que ver, lugares turisticos, que faire, "
  "a voir, choses a faire, activites, o que fazer, pontos turisticos, passeios, atracoes, must see, highlights",
  scope="", inc="tours museum nature-park river resort")
C("venue", "Event venues & halls", "Feestzalen & locaties", "Salones de eventos", "活动场地", "Salles de réception", "Salões de festa",
  "feestzaal, feestzalen, zaal, zalen, zaalverhuur, zaal huren, partyzaal, partylocatie, trouwlocatie, evenementenlocatie, "
  "vergaderzaal, vergaderruimte, conferentieruimte, event hall, event venue, venue, venues, banquet hall, ballroom, "
  "conference room, conference hall, meeting room, wedding venue",
  rx=r"event (hall|venue|space|location|centre|center|park)|events? venue|banquet|ballroom|conference (room|hall|facilit|centre|center)|meeting (room|facilit)|feestzaal|zaalverhuur|vergaderzaal|wedding venue|events? and (weddings|conferences)|theat(re|er) (for hire|rental)",
  scope="SVEA", r="party-rental catering")
C("museum", "Museums & heritage", "Musea & erfgoed", "Museos y patrimonio", "博物馆与古迹", "Musées & patrimoine", "Museus e patrimônio",
  "museum, musea, museums, erfgoed, heritage, history, geschiedenis, historisch, historic, fort, monument, monumenten, "
  "plantage, plantages, plantation, plantations, galerie, gallery, art gallery, kunst, art, kunstgalerie, synagoge, "
  "moskee, mosque, kathedraal, cathedral, kerk, church, tempel, temple, mandir",
  sub="museums-heritage",
  rx=r"museum|musea|heritage|erfgoed|histor|\bfort\b|monument|plantation|plantage|galler|galerie|synago|mosque|moskee|cathedral|kathedra|\btemple|mandir",
  scope="ANH", r="tours")
C("nature-park", "Nature parks & reserves", "Natuurparken & reservaten", "Parques naturales", "自然公园与保护区", "Parcs naturels & réserves", "Parques naturais",
  "natuur, natuurpark, natuurparken, natuurreservaat, reservaat, nature, nature park, nature reserve, national park, park, "
  "parken, wildlife, dieren, animals, apen, monkeys, vlinders, butterflies, wandelen, hiking, hike, wandelroute, trail, trails, "
  "berg, mountain, savanne, savanna",
  sub="nature-parks",
  rx=r"nature (park|reserve)|natuur(park|reservaat)|national park|wildlife|reserve\b|hiking|wandel|\btrails?\b|butterfl|vlinder",
  scope="ANS", r="tours lodge")
C("kids", "Kids & family", "Kinderen & familie", "Niños y familia", "亲子", "Enfants & famille", "Crianças e família",
  "kinderen, kids, kind, children, child, family, familie, gezin, speeltuin, speeltuinen, playground, play area, speelhal, "
  "arcade, kinderfeestje, kinderfeest, binnenspeeltuin, indoor playground, waterpark, water park, waterglijbaan, zoo, dierentuin, "
  "baby, babies, peuters, toddlers, family day out",
  rx=r"\bkids?\b|children|family (entertainment|fun|friendly|day)|kinderen|speeltuin|playground|play area|arcade|water ?park|\bzoo\b|dierentuin|toddler|soft play",
  scope="AENV", r="daycare toys")
C("cinema", "Cinemas & theatre", "Bioscoop & theater", "Cines y teatro", "电影院与剧院", "Cinémas & théâtre", "Cinemas e teatro",
  "bioscoop, bioscopen, cinema, cinemas, film, films, movie, movies, theater, theatre, toneel, voorstelling, voorstellingen, "
  "concert, concerten, comedy, stand-up",
  rx=r"cinema|bioscoop|movie|theat(er|re)|toneel|concert|comedy", scope="ANV", r="bar")
C("sports", "Sports & activities", "Sport & activiteiten", "Deportes", "运动", "Sports & activités", "Esportes",
  "sport, sporten, sports, voetbal, football, soccer, padel, tennis, golf, basketbal, basketball, volleybal, "
  "paintball, karten, karting, go kart, bowling, schieten, schietbaan, shooting range, "
  "vissen, sportvissen, fishing, sport fishing, hengelsport, duiken, diving, surfen, waterski, jetski, boxing, boksen",
  rx=r"\bsports?\b|football|soccer|padel|tennis|\bgolf\b|basketbal|volleybal|swimming lessons|zwemles|paintball|karting|bowling|shooting|fishing|vissen|diving|duiken|jet ?ski|boxing|boksen",
  scope="AVN", r="gym", neg=r"broadcast|television|tv station|radio|omroep|sports bar|sportsbar")

# ── Shopping ───────────────────────────────────────────────────────────────
C("supermarket", "Supermarkets & groceries", "Supermarkten & boodschappen", "Supermercados", "超市", "Supermarchés", "Supermercados",
  "supermarkt, supermarkten, supermarket, supermarkets, supermarkert, super, minimarkt, minimarket, toko, "
  "chinese winkel, chinees winkel, snesi winkel, snesi wenkri, wenkri, winkri, boodschappen, boodschappen doen, groceries, "
  "grocery, grocery store, food store, levensmiddelen, kruidenier, kruidenierswaren, provisions",
  sub="supermarkets", rx=r"supermar|grocer|minimar|boodschappen|levensmiddel|kruidenier", scope="H", r="market")
C("market", "Markets & fresh produce", "Markten & groente en fruit", "Mercados", "市场与农产品", "Marchés & primeurs", "Mercados e hortifrúti",
  "markt, markten, market, markets, centrale markt, versmarkt, groente, groenten, fruit, groente en fruit, fruitwinkel, "
  "vegetables, produce, fresh produce, boerenmarkt, farmers market, bazaar, kruiden, specerijen, spices, rijst, rice",
  sub="", rx=r"\|.*(\bmarkt\b|(fresh|central|farmers'?|fruit|vegetable|fish|night|food) market|groentemarkt|bazaar|market hall|markthal)",
  scope="H", r="supermarket")
C("butcher", "Butchers, meat & fish", "Slagers, vlees & vis", "Carnicerías y pescaderías", "肉铺与鱼店", "Boucheries & poissonneries", "Açougues e peixarias",
  "slager, slagers, slagerij, slagerijen, vlees, meat, butcher, butchers, butchery, kip, kippen, chicken, kippenvlees, "
  "rundvlees, beef, varkensvlees, pork, lamsvlees, lamb, geitenvlees, goat, gehakt, worst, vis, visboer, viswinkel, fish shop, "
  "fish market, vismarkt, garnalen, shrimp, eieren, eggs, pluimvee, poultry, kwikwi",
  sub="butchers-meat", rx=r"butcher|slager|\bmeat\b|\bvlees|fish (shop|market|store)|vismarkt|viswinkel", scope="H",
  r="seafood supermarket", neg=r"fishing (gear|tackle|equipment|rod|store|shop)|hengel")
C("liquor", "Drinks & liquor", "Drank & slijterij", "Bebidas y licores", "酒水", "Boissons & spiritueux", "Bebidas e bebidas alcoólicas",
  "drank, dranken, drankjes, slijterij, slijterijen, liquor, liquor store, wine shop, wijn, wijnen, wine, wines, bier, beer, "
  "rum, whisky, whiskey, vodka, alcohol, borgoe, parbo bier, frisdrank, soft drinks, juice, sap, sappen, water, ijs blokjes, "
  "ijsblokjes, cube ice, ice cubes",
  sub="drinks-liquor", rx=r"liquor|slijter|\bwines?\b|\bwijn|\bbeer\b|\bbier\b|\brum\b|whisk|vodka|spirits|beverage", scope="H",
  r="supermarket bar")
C("hardware", "Hardware & building materials", "Bouwmaterialen & ijzerwaren", "Ferreterías y materiales", "五金与建材", "Quincaillerie & matériaux", "Material de construção",
  "bouwmaterialen, bouwmateriaal, bouwmarkt, bouwmarkten, bouwcenter, ijzerwaren, ijzerhandel, gereedschap, gereedschappen, "
  "tools, power tools, hardware, hardware store, building materials, building supplies, cement, zand, sand, opvulzand, "
  "grind, blokken, bouwblokken, hout, timber, triplex, plywood, spijkers, nails and screws, schroeven, screws, pvc, pijpen, "
  "pipes, elektra materiaal, kabels, cables, verf, paint, sanitair, tegels, tiles, zinkplaten, golfplaten",
  sub="building-materials", rx=r"\bhardware (store|shop|stores|products|and)|building material|bouwmateria|bouwmarkt|ijzerwar|\btools\b|gereedschap|\bcement\b|\bsand\b|\bzand\b|timber|plywood",
  scope="H", r="construction", neg=r"computer hardware|hardwood|veterin|livestock")
C("furniture", "Furniture & home", "Meubels & wonen", "Muebles y hogar", "家具与家居", "Meubles & maison", "Móveis e casa",
  "meubels, meubel, meubelzaak, meubelwinkel, woninginrichting, interieur, wonen, furniture, home furniture, sofa, "
  "zitbank, bed, bedden, matras, matrassen, mattress, kast, kasten, klerenkast, tafel, stoelen, eettafel, keuken, "
  "keukens, kitchen, gordijnen, curtains, rotan, rattan, decoratie, home decor, woonaccessoires",
  sub="home-furniture", rx=r"furnitur|meubel|\bsofas?\b|mattress|matras|\bbeds?\b(?! and breakfast)|curtain|gordijn|home decor|kitchen (cabinets|furniture|design)|keukens\b",
  scope="HV", r="carpenter electronics", fx="carpenter")
C("electronics", "Electronics & appliances", "Elektronica & witgoed", "Electrónica y electrodomésticos", "电子产品与家电", "Électronique & électroménager", "Eletrônicos e eletrodomésticos",
  "elektronica, electronica, electronics, witgoed, apparaten, huishoudelijke apparaten, appliances, home appliances, koelkast, "
  "koelkasten, fridge, fridges, vriezer, freezer, wasmachine, wasmachines, washing machine, droger, fornuis, stove, oven, "
  "magnetron, microwave, tv, tv's, televisie, television, televisions, smart tv, blender, ventilator, ventilatoren, fan, fans, "
  "speaker, speakers, playstation, ps5, xbox, gaming, camera kopen",
  sub="electronics", rx=r"electronic|elektronica|appliance|witgoed|fridge|koelkast|freezer|vriezer|washing machine|wasmachine|\btvs?\b|televis|microwave|magnetron|gaming",
  scope="H", r="phones computers airco", fx="appliance-repair")
C("clothing", "Clothing & fashion", "Kleding & mode", "Ropa y moda", "服装与时尚", "Vêtements & mode", "Roupas e moda",
  "kleding, kleren, kledingwinkel, kledingzaak, mode, fashion, clothing, clothes, boutique, boutiques, boetiek, jurk, jurken, "
  "dress, dresses, tshirt, t-shirts, broek, broeken, jeans, sneakers, schoenen, shoes, slippers, tassen, tas, bags, handbags, "
  "lingerie, ondergoed, badmode, swimwear, kinderkleding, kids clothing, herenkleding, dameskleding, pangi, pangi's, kotomisi, "
  "kimona, sari, saree, traditionele kleding, thrift, tweedehands kleding, uniform",
  sub="fashion-clothing", rx=r"cloth(ing|es)\b|fashion|boutique|kleding|kleren|dresses|jurk|apparel|\bshoes\b|schoenen|sneaker|handbag|tassen|lingerie|swimwear|\bpangi|kotomisi|saree|\bsari\b",
  scope="H", r="tailor jewelry", fx="tailor")
C("jewelry", "Jewellery & gold", "Juweliers & goud", "Joyerías", "珠宝与黄金", "Bijouteries & or", "Joalherias e ouro",
  "juwelier, juweliers, juwelen, sieraden, sieraad, goud, gouden, goudsmid, goudsmeden, goud kopen, goud verkopen, zilver, "
  "zilversmid, gold, gold shop, jewelry, jewellery, jeweler, jeweller, jewelers, rings, ring, ringen, trouwringen, "
  "kettingen, ketting, necklace, armband, armbanden, bracelet, oorbellen, earrings, horloge, horloges, watch, watches",
  rx=r"jewel|juwel|sieraden|goudsmid|zilversmid|\bgold(smith)?\b|\bgoud\b|watches|horloge|\brings\b|necklace|bracelet|earring",
  scope="H", neg=r"golden|gold (coast|card|member)", r="clothing gifts")
C("optician", "Opticians & glasses", "Opticiens & brillen", "Ópticas", "眼镜店", "Opticiens", "Óticas",
  "opticien, opticiens, optiek, optieken, optician, opticians, optical, bril, brillen, glasses, eyeglasses, zonnebril, "
  "zonnebrillen, sunglasses, lenzen, contactlenzen, contact lenses, oogmeting, eye test, oogarts, eye doctor, brilleman",
  rx=r"optician|opticien|optiek|optical (shop|store|centre|center)|eyewear|eyeglasses|\bglasses\b|\bbril(len)?\b|contact lens|lenzen|oogmeting|eye (test|exam)",
  scope="HV", neg=r"wine glasses|glasses of|jewel|sieraden", r="doctor")
C("pharmacy", "Pharmacies & drugstores", "Apotheken & drogisterijen", "Farmacias y droguerías", "药店", "Pharmacies & drogueries", "Farmácias e drogarias",
  "apotheek, apotheken, apoteek, apotheke, apotheker, apteiki, apteki, apteyk, drogist, drogisterij, drogisterijen, pharmacy, "
  "pharmacies, chemist, drugstore, drug store, medicijnen, medicijn, medicine, medicines, dresi, recept, prescription, "
  "dienstdoende apotheek, apotheek dienst, wachtdienst apotheek, vitaminen, vitamins",
  rx=r"pharmac|apothe|drogist|drugstore|drug store|chemist", scope="HV", neg=r"resellers only|wederverkopers|wholesaler of", r="doctor")
C("cosmetics", "Cosmetics & beauty products", "Cosmetica & verzorging", "Cosméticos", "化妆品", "Cosmétiques", "Cosméticos",
  "cosmetica, cosmetics, parfum, parfums, perfume, perfumes, verzorgingsproducten, huidverzorging producten, skincare products, "
  "body lotion, bodylotion, lotion, haarproducten, hair products, beauty products, beauty supply, beauty shop, nagellak, "
  "nail polish, lippenstift, lipstick",
  sub="health-beauty", rx=r"cosmet|perfum|parfum|skincare products|beauty (products|supply|shop|store)|hair products|lotion",
  scope="H", r="pharmacy makeup")
C("books-office", "Books & office supplies", "Boeken & kantoorartikelen", "Libros y papelería", "书籍与办公用品", "Livres & fournitures", "Livros e papelaria",
  "boeken, boek, boekhandel, boekwinkel, books, book, bookstore, bookshop, kantoorartikelen, kantoorbenodigdheden, "
  "office supplies, stationery, schoolspullen, schoolboeken, school supplies, pennen, schriften, papier, paper",
  sub="books-office", rx=r"\bbooks?\b|boek(en|handel|winkel)|stationery|office supplies|kantoorartikel|school supplies|schoolboek",
  scope="H", r="printing")
C("gifts", "Gifts & souvenirs", "Cadeaus & souvenirs", "Regalos y recuerdos", "礼品与纪念品", "Cadeaux & souvenirs", "Presentes e lembranças",
  "cadeau, cadeaus, cadeautje, cadeautjes, kado, kados, cadeauwinkel, geschenk, geschenken, gift, gifts, gift shop, giftshop, "
  "gift box, giftbox, giftset, giftsets, souvenir, souvenirs, souvenirwinkel, handwerk, handgemaakt, handmade, crafts, "
  "ambacht, ambachten, houtsnijwerk, woodcarving, kunstnijverheid, marron kunst, tembe, speelgoed, toys",
  sub="toys-gifts crafts-souvenirs", rx=r"\bgifts?\b|cadeau|souvenir|handmade|handgemaakt|\bcrafts?\b|handwerk|woodcarv|houtsnij|\btoys?\b|speelgoed|tembe",
  scope="H", r="flowers jewelry")
C("toys", "Toys & baby", "Speelgoed & baby", "Juguetes y bebés", "玩具与母婴", "Jouets & bébé", "Brinquedos e bebê",
  "speelgoed, speelgoedwinkel, toys, toy store, toy shop, baby, babyspullen, babywinkel, baby shop, babykleding, kinderwagen, "
  "stroller, luiers, diapers, lego, poppen, dolls",
  rx=r"\btoys?\b|speelgoed|\bbaby\b|babies|stroller|kinderwagen|diaper|luier", scope="H", r="gifts kids")
C("mall", "Malls & shopping centres", "Winkelcentra", "Centros comerciales", "购物中心", "Centres commerciaux", "Shoppings",
  "mall, malls, winkelcentrum, winkelcentra, shopping centre, shopping center, shoppingcenter, shopping mall, shopping, "
  "winkelen, shoppen, warenhuis, department store",
  sub="malls-markets", rx=r"\|.*(shopping (centre|center|mall)|winkelcentrum|department store|warenhuis|\bmall (with|featuring|houses|has|offers))", scope="H", r="clothing")
C("wholesale", "Wholesale & import", "Groothandel & import", "Mayoristas e importación", "批发与进口", "Grossistes & import", "Atacado e importação",
  "groothandel, groothandels, wholesale, wholesaler, wholesalers, import, importeur, importeurs, importer, export, exporteur, "
  "handelmaatschappij, trading, trading company, distributeur, distributor, distributors, bulk, in bulk, grootverpakking",
  sub="wholesale-import", rx=r"wholesal|groothandel|importer|import (and|&) (export|distribut)|distributor|trading company|handelmaatschappij", scope="HV")
C("sports-goods", "Sports & outdoor gear", "Sport- & outdoorwinkels", "Artículos deportivos", "体育与户外用品", "Articles de sport", "Artigos esportivos",
  "sportwinkel, sportwinkels, sportartikelen, sport kleding, sportkleding, sports store, sports shop, sporting goods, "
  "outdoor, outdoor winkel, visgerei, hengels, fishing gear, fishing tackle, kampeerspullen, camping gear, fietsen, fiets, "
  "fietsenwinkel, bicycles, bicycle, bike shop, fitness apparatuur, fitness equipment",
  sub="sports-outdoors", rx=r"sport(s|ing)? (store|shop|goods|gear|equipment|wear)|sportswear|sportkleding|athletic wear|activewear|outdoor (gear|store)|fishing (gear|tackle|equipment)|bicycl|fietsen",
  scope="H", r="sports")
C("pets", "Pets, animal feed & farm", "Dieren, voer & landbouw", "Mascotas y agro", "宠物与农资", "Animaux & agriculture", "Pets e agropecuária",
  "dierenwinkel, dierenspeciaalzaak, huisdieren, huisdier, pets, pet shop, pet store, dierenvoer, hondenvoer, kattenvoer, "
  "pet food, dog food, cat food, voer, veevoer, kippenvoer, animal feed, livestock, vee, pluimvee, landbouw, agro, agri, "
  "boer, boeren, farm, farming, farmers, zaden, seeds, kunstmest, fertilizer, landbouwshop",
  sub="vet-livestock agriculture", rx=r"\bpets?\b(?! bottles)|pet (food|shop|store|supplies)|huisdier|dierenvoer|hondenvoer|veevoer|animal (feed|food)|livestock|pluimvee|kunstmest|fertili[sz]er|landbouw(shop|benodigd)",
  scope="HV", r="vet gardening")
C("gas-cylinders", "Cooking gas", "Kookgas & gasflessen", "Gas de cocina", "煤气罐", "Gaz de cuisine", "Gás de cozinha",
  "kookgas, gas, gasfles, gasflessen, gascilinder, gascilinders, gas cilinder, cilinder, gas hervullen, gas bijvullen, "
  "gas bestellen, gas cylinder, gas cylinders, cooking gas, lpg, propane, propaan, 28 lbs",
  rx=r"cooking gas|kookgas|gas ?cylind|gascilind|\blpg\b|propan", scope="HV", r="hardware")
C("water-delivery", "Drinking water & ice", "Drinkwater & ijs", "Agua potable y hielo", "饮用水与冰块", "Eau potable & glace", "Água potável e gelo",
  "drinkwater, drink water, water bezorgen, water bestellen, waterflessen, flessenwater, bronwater, gallon, gallons, "
  "waterkoeler, water cooler, bottled water, drinking water, water delivery, watra, ijsblokjes, ijs blokjes, cube ice, "
  "ice cubes, ice delivery, blokijs",
  rx=r"drinking water|drinkwater|bottled water|bottling|bronwater|spring water|water (delivery|cooler)|ice cubes|cube ice|ijsblok",
  scope="HV", r="liquor")

# ── Money, legal, business services ─────────────────────────────────────────
C("bank", "Banks", "Banken", "Bancos", "银行", "Banques", "Bancos",
  "bank, banken, banking, bankrekening, rekening openen, bank account, account, lening, leningen, loan, loans, krediet, "
  "credit, hypotheek, hypotheken, mortgage, sparen, spaarrekening, savings, pinpas, debitcard, creditcard, credit card, "
  "internet bankieren, mobile banking, mobiel bankieren, volkscredietbank",
  sub="banking", rx=r"^[^|]*\b(bank|kredietbank|credit union)\b", scope="V",
  neg=r"river ?bank|riverbank|oever", r="atm exchange")
C("atm", "ATMs", "Geldautomaten", "Cajeros automáticos", "取款机", "Distributeurs de billets", "Caixas eletrônicos",
  "atm, atms, geldautomaat, geldautomaten, pinautomaat, pinautomaten, pinnen, geld pinnen, geld opnemen, cash, contant, "
  "cash machine, withdraw, withdraw money, pinpas werkt niet",
  rx=r"\batms?\b|geldautomaat|pinautomaat|cash machine", scope="V", r="bank", sub="banking")
C("exchange", "Money exchange (cambio)", "Wisselkantoren (cambio)", "Casas de cambio", "货币兑换", "Bureaux de change", "Casas de câmbio",
  "cambio, cambios, wisselkantoor, wisselkantoren, geld wisselen, wisselen, valuta, valuta wisselen, wisselkoers, wisselkoersen, "
  "koers, koersen, dollar koers, euro koers, money exchange, currency exchange, exchange office, exchange rate, exchange rates, "
  "rates, srd, dollar, dollars, euro, euros, usd, eur",
  rx=r"cambio|wisselkantoor|money exchange|currency exchange|exchange (office|house|bureau)|bureau de change", scope="VH",
  r="bank money-transfer")
C("money-transfer", "Money transfer", "Geld overmaken", "Envío de dinero", "汇款", "Transfert d'argent", "Envio de dinheiro",
  "geld overmaken, geld sturen, geld versturen, geld ontvangen, overmaken, geldovermaking, geldovermakingskantoor, "
  "geldtransactiekantoor, money transfer, money transfers, moneytransfer, money wiring, send money, remittance, remittances, "
  "western union, moneygram, ria, wereldwijd geld sturen",
  rx=r"money (transfer|wir|remit)|remittan|western union|moneygram|geldovermak|geldtransact|send money", scope="V",
  r="bank exchange")
C("insurance", "Insurance", "Verzekeringen", "Seguros", "保险", "Assurances", "Seguros",
  "verzekering, verzekeringen, verzekeraar, verzekeraars, verzekeren, autoverzekering, auto verzekering, zorgverzekering, "
  "ziektekostenverzekering, levensverzekering, uitvaartverzekering, brandverzekering, reisverzekering, insurance, insurer, "
  "insurers, car insurance, health insurance, life insurance, travel insurance, assurantie, assurantiën, polis",
  sub="insurance", rx=r"insur|verzeker|assurant", scope="V", r="funeral bank")
C("notary", "Notaries", "Notarissen", "Notarios", "公证处", "Notaires", "Cartórios e notários",
  "notaris, notarissen, notariaat, notariaten, notarieel, notarsi, notary, notaries, notary public, akte, aktes, transport akte, "
  "testament, huwelijkse voorwaarden, oprichting nv, nv oprichten, hypotheekakte",
  rx=r"notar", scope="V", r="lawyer")
C("lawyer", "Lawyers & legal", "Advocaten & juristen", "Abogados", "律师", "Avocats", "Advogados",
  "advocaat, advocaten, advocatenkantoor, jurist, juristen, juridisch, juridisch advies, rechtsbijstand, lawyer, lawyers, "
  "attorney, attorneys, law firm, legal, legal advice, rechtszaak, scheiding, divorce, incasso, debt collection, deurwaarder",
  rx=r"lawyer|advoca|attorney|law ?firm|juridisch advies|rechtsbijstand|incasso|deurwaarder",
  scope="V", r="notary", neg=r"real estate agency")
C("accountant", "Accountants & tax", "Accountants & belasting", "Contadores e impuestos", "会计与税务", "Comptables & fiscalité", "Contadores e impostos",
  "accountant, accountants, accountancy, accountantskantoor, boekhouder, boekhouders, boekhouding, administratie, "
  "administratiekantoor, administratiekantoren, belasting, belastingen, belastingaangifte, aangifte, belastingadviseur, "
  "btw, vat, tax, taxes, tax advisor, bookkeeping, bookkeeper, payroll, salarisadministratie, audit, accounting, jaarrekening",
  sub="accounting-tax", rx=r"accountan|bookkeep|boekhoud|administratiekantoor|\btax\b|belasting|payroll|salarisadmin|audit",
  scope="V", r="consulting")
C("consulting", "Consulting & recruitment", "Advies & uitzendbureaus", "Consultoría y empleo", "咨询与招聘", "Conseil & recrutement", "Consultoria e recrutamento",
  "consultancy, consultant, consultants, consulting, advies, adviesbureau, adviseur, management advies, hr, human resources, "
  "recruitment, recruiter, uitzendbureau, uitzendbureaus, werving, personeel, vacatures, vacature, jobs, job, werk, banen, "
  "baan, werk zoeken, outsourcing, callcenter, call center, coaching, coach",
  sub="consulting-hr", rx=r"consultan|consulting|adviesbureau|recruit|uitzendbureau|staffing|human resources|outsourc|call ?cent|coaching",
  scope="V", r="accountant", neg=r"\bgym\b|fitness|dance|dans|bjj|jiu|\bschool\b|martial")
C("real-estate", "Real estate", "Makelaars & vastgoed", "Inmobiliarias", "房地产", "Immobilier", "Imobiliárias",
  "oso hur, hur oso, makelaar, makelaars, makelaardij, makelaarskantoor, vastgoed, onroerend goed, huis kopen, huis huren, huis te koop, "
  "huis te huur, huizen, woning, woningen, woning huren, appartement huren, perceel, percelen, grond, grond kopen, "
  "grond te koop, kavel, te koop, tekoop, te huur, tehuur, real estate, realtor, real estate agent, property, properties, "
  "house for sale, house for rent, land for sale, rental property, rent a house, projectontwikkelaar",
  sub="real-estate", rx=r"real estate|makelaar|vastgoed|property (management|sales|rental|developer|for)|properties for|onroerend|perce(el|len)|\bland for sale", scope="V", neg=r"insur|verzeker",
  r="construction")
C("telecom", "Internet & telecom", "Internet & telecom", "Internet y telecomunicaciones", "网络与电信", "Internet & télécoms", "Internet e telecom",
  "internet, internetprovider, internet provider, wifi, wi-fi, glasvezel, fiber, fibre, fiber internet, adsl, telecom, "
  "telecommunicatie, telefoonmaatschappij, simkaart, sim kaart, sim card, sim, prepaid, beltegoed, opwaarderen, top up, "
  "topup, data bundel, databundel, digicel, telesur, mobiel internet, mobile data, kabel tv, cable tv",
  sub="telecom-utilities", rx=r"internet|telecom|\bfib(er|re)\b|glasvezel|\bsim\b|prepaid|mobile network|\bwifi\b|cable tv", scope="V",
  r="phones")
C("utilities", "Water & electricity", "Water & stroom", "Agua y electricidad", "水电", "Eau & électricité", "Água e energia",
  "ebs, stroom, elektriciteit, electricity, power, stroomstoring, power outage, swm, waterleiding maatschappij, water, "
  "waterstoring, water outage, nutsbedrijf, utilities, utility, energiebedrijf",
  rx=r"\bebs\b|\bswm\b|waterleiding maatschappij|electricity (supply|company|provider|distribut)|energy company of suriname|nutsbedrijf",
  scope="V", r="telecom")
C("travel-agency", "Travel agencies & tickets", "Reisbureaus & tickets", "Agencias de viajes", "旅行社与机票", "Agences de voyages", "Agências de viagem",
  "reisbureau, reisbureaus, reizen, reis, vakantie, vakanties, ticket, tickets, vliegticket, vliegtickets, ticket kopen, "
  "travel agency, travel agent, travel, flight tickets, plane tickets, airline tickets, pakketreis, package holiday, "
  "visum, visa, visa aanvraag",
  sub="travel-agencies", rx=r"travel agen|reisbureau|\btickets?\b|holiday packages|vakantiereis|visa (service|applic)", scope="V",
  r="airline tours")
C("airline", "Airlines", "Luchtvaartmaatschappijen", "Aerolíneas", "航空公司", "Compagnies aériennes", "Companhias aéreas",
  "airline, airlines, luchtvaartmaatschappij, vliegmaatschappij, vliegmaatschappijen, luchtvaart, aviation, vlucht, vluchten, "
  "flight, flights, vliegen, vliegtuig, plane, slm, klm, copa, gol, caribbean airlines, surinam airways, fly allways, gum air, "
  "blue wing, binnenlandse vlucht, charter, chartervlucht, vliegveld, airport, zorg en hoop vliegveld",
  sub="airlines-aviation", rx=r"airline|aviation|luchtvaart|\bflights?\b|charter|airways|\bair\b (services|charter)", scope="V",
  r="travel-agency")

# ── Education, health, community ───────────────────────────────────────────
C("school", "Schools", "Scholen", "Escuelas", "学校", "Écoles", "Escolas",
  "school, scholen, basisschool, middelbare school, international school, internationale school, privéschool, privé school, "
  "private school, schools, universiteit, university, hogeschool, college, academie, academy, onderwijs, education, mbo, hbo, "
  "lyceum, vwo, havo, mulo",
  sub="schools", rx=r"\|.*(\bschools?\b|universit|college|onderwijs|education|lyceum|\bmulo|\bmbo\b|\bhbo\b)", scope="V",
  neg=r"(driving|dance|ballet|dans|swim|zwem|cooking|language|beauty|nail)( |-)?school|\bgym\b|fitness|jiu|bjj|martial|hospital|ziekenhuis", r="courses tutoring")
C("courses", "Courses & training", "Cursussen & opleidingen", "Cursos y formación", "课程与培训", "Cours & formations", "Cursos e treinamentos",
  "cursus, cursussen, opleiding, opleidingen, training, trainingen, workshop, workshops, les, lessen, lessons, course, courses, "
  "certificaat, certificate, diploma, taalcursus, language course, engels leren, spaans leren, nederlands leren, chinees leren, "
  "computercursus, kookcursus, cooking class, cooking classes, beauty school, nagelcursus, nail course, barber course",
  sub="training-courses", rx=r"\bcourses?\b|cursus|opleiding|training institut|vocational|certificat|diploma", scope="V", neg=r"\bgym\b|fitness|ballet|dans",
  r="tutoring school")
C("tutoring", "Tutoring & homework help", "Bijles & huiswerkbegeleiding", "Clases particulares", "家教与课业辅导", "Soutien scolaire", "Aulas particulares",
  "bijles, bijlessen, bijles aan huis, bijlesdocent, huiswerkbegeleiding, huiswerk, huiswerkklas, privéles, privelessen, "
  "privé les, examentraining, examen training, tutor, tutors, tutoring, homework, homework help, private lessons, "
  "rekenles, wiskunde bijles, taalles",
  rx=r"tutor|bijles|huiswerk|homework|examentraining", scope="V", r="courses school")
C("driving-school", "Driving schools", "Rijscholen", "Autoescuelas", "驾校", "Auto-écoles", "Autoescolas",
  "rijschool, rijscholen, rijles, rijlessen, rijopleiding, rijbewijs, rijbewijs halen, theorieles, theorie examen, "
  "rijexamen, driving school, driving lessons, driving license, drivers license, driver's license",
  rx=r"driving (school|lesson|instruct)|rijschool|rijles|rijopleiding|rijbewijs|theorieles", scope="V")
C("daycare", "Daycare & creche", "Kinderopvang & crèches", "Guarderías", "托儿所", "Crèches & garderies", "Creches",
  "kinderopvang, kinderdagverblijf, kinderdagverblijven, creche, crèche, creches, crèches, opvang, naschoolse opvang, bso, "
  "peuterschool, peuterspeelzaal, peuters, oppas, oppassen, babysitter, babysit, nanny, daycare, day care, nursery, preschool, "
  "pre-school, kleuterschool, montessori",
  rx=r"daycare|day care|kinderopvang|kinderdagverblijf|cr[eè]che|peuter|nursery school|preschool|pre-school|kleuterschool|montessori|babysit|after.?school",
  scope="V", r="school kids", neg=r"rentals?\b|verhuur")
C("dance-music", "Dance & music lessons", "Dans- & muziekles", "Clases de baile y música", "舞蹈与音乐课", "Cours de danse & musique", "Aulas de dança e música",
  "dansschool, dansscholen, dansles, danslessen, dansen, dance, dance school, dance classes, dance lessons, ballet, balletschool, "
  "salsa, bachata, kizomba, zouk, afro dance, bollywood, muziekles, muziekschool, muziek, music lessons, music school, "
  "pianoles, piano, gitaarles, gitaar, guitar, zangles, zingen, singing, drums les, conservatorium",
  sub="arts-dance-music", rx=r"\bdanc|\bdans|ballet|salsa|bachata|kizomba|\bmusic|\bmuziek|piano|guitar|gitaar|singing|zangles|conservator",
  scope="VA", r="courses")
C("swimming", "Swimming lessons & pools", "Zwemles & zwembaden", "Clases de natación", "游泳课与泳池", "Natation", "Natação",
  "zwemles, zwemlessen, zwemschool, zwemscholen, zwemmen leren, leren zwemmen, zwemdiploma, zwembad, zwembaden, swimming lessons, "
  "swim lessons, swim school, learn to swim, swimming pool, public pool, natacion, natacao, piscine, piscina",
  rx=r"zwem(les|school|lessen|bad|diploma)|swim(ming)? (lessons?|school|classes|pool)|public (swimming )?pool|aquafit", scope="VAN", r="sports kids")
C("gym", "Gyms & fitness", "Sportscholen & fitness", "Gimnasios", "健身房", "Salles de sport", "Academias",
  "gym, gyms, sportschool, sportscholen, fitness, fitnesscentrum, fitness center, fitness centre, workout, trainen, "
  "krachttraining, crossfit, bootcamp, personal trainer, personal training, pt, spinning, zumba, aerobics, sporten",
  sub="fitness-wellness", rx=r"\bgym|fitness|sportschool|crossfit|bootcamp|personal train|workout|zumba|spinning|aerobic",
  scope="V", r="yoga martial-arts")
C("yoga", "Yoga & pilates", "Yoga & pilates", "Yoga y pilates", "瑜伽与普拉提", "Yoga & pilates", "Yoga e pilates",
  "yoga, yogales, yogalessen, yoga studio, pilates, pilatesles, meditatie, meditation, mindfulness, stretching",
  rx=r"\byoga|pilates|meditat|mindful", scope="V", r="gym spa")
C("martial-arts", "Martial arts & boxing", "Vechtsport & boksen", "Artes marciales y boxeo", "武术与拳击", "Arts martiaux & boxe", "Artes marciais e boxe",
  "vechtsport, vechtsporten, martial arts, boksen, boxing, kickboksen, kickboxing, mma, karate, judo, taekwondo, "
  "jiu jitsu, jiujitsu, bjj, muay thai, zelfverdediging, self defense, self-defence",
  rx=r"martial|boxing|boksen|kickbox|\bmma\b|karate|judo|taekwondo|jiu|muay|self[- ]defen", scope="V", r="gym")
C("doctor", "Doctors & clinics", "Huisartsen & klinieken", "Médicos y clínicas", "医生与诊所", "Médecins & cliniques", "Médicos e clínicas",
  "dokter, dokters, huisarts, huisartsen, huisartsenpraktijk, arts, artsen, specialist, specialisten, kliniek, klinieken, "
  "poli, polikliniek, medisch centrum, medical center, medical centre, doctor, doctors, gp, general practitioner, clinic, "
  "clinics, datra, gynaecoloog, gynecologist, kinderarts, pediatrician, dermatoloog, dermatologist, cardioloog, psycholoog, "
  "psychologist, therapeut, therapist, keuring, medische keuring, check up, checkup",
  sub="hospitals-clinics", rx=r"\bdoctors?\b|huisarts|general practi|medical (cent|practice|clinic)|medisch centrum|polikliniek|gyna?ecolog|pediatric|kinderarts|dermatolog|psycholog|cardiolog|\bclinic\b",
  scope="V", neg=r"beauty|aesthetic|esthetic|wellness|dental|dierenarts|veterin|animal|pets?\b|laser", r="hospital pharmacy")
C("hospital", "Hospitals & emergency", "Ziekenhuizen & spoed", "Hospitales y urgencias", "医院与急诊", "Hôpitaux & urgences", "Hospitais e emergência",
  "ziekenhuis, ziekenhuizen, hospitaal, hospital, hospitals, spoed, spoedeisende hulp, seh, eerste hulp, emergency, "
  "emergency room, ambulance, ambulances, azp, academisch ziekenhuis, diakonessenhuis, lands hospitaal, 's lands hospitaal",
  sub="hospitals-clinics", rx=r"\bhospital\b|\bhospitals\b|ziekenhuis|emergency (room|care|department|medical)|spoedeisende|eerste hulp post|ambulance", scope="V", r="doctor")
C("dentist", "Dentists", "Tandartsen", "Dentistas", "牙医", "Dentistes", "Dentistas",
  "tandarts, tandartsen, tandartspraktijk, tandart, tandarts praktijk, tanden, tand, kies, kiezen, dentist, dentists, dental, "
  "dental clinic, orthodontist, orthodontie, beugel, braces, tandtechnicus, tandtechniek, mondhygiënist, mondhygiene, "
  "dental hygiene, teeth whitening, tanden bleken",
  rx=r"dentist|dental|tandarts|tandtechn|orthodont|teeth|mondhygi", scope="V", neg=r"dental lab|tandtechni|insur|verzeker", r="doctor")
C("physio", "Physiotherapy", "Fysiotherapie", "Fisioterapia", "理疗", "Kinésithérapie", "Fisioterapia",
  "fysio, fysiotherapie, fysiotherapeut, fysiotherapeuten, physio, physiotherapy, physiotherapist, physical therapy, "
  "chiropractor, chiropractie, revalidatie, rehabilitation, sportmassage, sports massage, manuele therapie",
  rx=r"physio|fysio|chiropract|physical therap|revalidatiecentrum|rehabilitation (centre|center|clinic)", scope="V", r="doctor spa")
C("lab", "Medical labs", "Laboratoria", "Laboratorios", "医学检验", "Laboratoires", "Laboratórios",
  "lab, labs, laboratorium, laboratoria, laboratory, bloed prikken, bloedonderzoek, bloedtest, blood test, bloedafname, "
  "test, testen, covid test, pcr, röntgen, rontgen, x-ray, xray, echo, ultrasound, mri, ct scan, radiologie, radiology",
  rx=r"medical lab|laborator(y|ium) (for|services|testing)|medisch laboratorium|bloedonderzoek|blood test|bloedafname|x-?ray|r[oö]ntgen|radiolog|ultrasound|\bmri\b", scope="V",
  r="doctor hospital", neg=r"dental lab|tandtechn|mineral|assay|mining|measuring")
C("vet", "Vets", "Dierenartsen", "Veterinarios", "兽医", "Vétérinaires", "Veterinários",
  "dierenarts, dierenartsen, dierenkliniek, dierenpoli, dierenartspraktijk, dierendokter, vet, vets, veterinarian, "
  "veterinary, animal clinic, animal hospital, pet clinic, hond, honden, dog, dogs, kat, katten, cat, cats, castreren, "
  "steriliseren, vaccinatie hond, inenten",
  sub="veterinary", rx=r"veterin|dierenarts|dierenkliniek|dierenpoli|animal (clinic|hospital)|pet clinic", scope="VH",
  r="pets")
C("funeral", "Funeral services", "Uitvaartverzorging", "Servicios funerarios", "殡葬服务", "Pompes funèbres", "Serviços funerários",
  "uitvaart, uitvaarten, uitvaartverzorging, uitvaartcentrum, uitvaartonderneming, begrafenis, begrafenisonderneming, "
  "crematie, cremeren, funeral, funerals, funeral home, funeral services, undertaker, rouwcentrum, doodskist, kist, "
  "uitvaartverzekering, dede oso",
  rx=r"funeral|uitvaart|begrafenis|crematie|cremat|undertaker|rouwcentrum", scope="V", r="insurance")
C("church", "Churches & places of worship", "Kerken & gebedshuizen", "Iglesias y templos", "教堂与宗教场所", "Églises & lieux de culte", "Igrejas e templos",
  "kerk, kerken, church, churches, moskee, moskeeën, mosque, mosques, mandir, mandirs, tempel, tempels, temple, temples, "
  "synagoge, synagogue, kathedraal, cathedral, gebedshuis, worship, mass",
  rx=r"\bchurch\b|\bkerk\b|kerken|mosque|moskee|mandir|\btemple\b|tempel|synago|cathedral|kathedra|worship|diocese|bisdom", scope="NAV", r="museum")

# ── Industry ────────────────────────────────────────────────────────────────
C("oil-gas", "Oil & gas", "Olie & gas", "Petróleo y gas", "石油天然气", "Pétrole & gaz", "Petróleo e gás",
  "olie, olie en gas, oil, oil and gas, oil & gas, gas, petroleum, offshore, onshore, staatsolie, olieindustrie, oliesector, "
  "energy, energie, fpso, drilling, boren, oilfield, oil field services",
  sub="oil-gas", rx=r"\boil\b|petroleum|offshore|oilfield|staatsolie|\bfpso|drilling", scope="V", r="manufacturing")
C("mining", "Mining", "Mijnbouw", "Minería", "矿业", "Mines", "Mineração",
  "mijnbouw, mijnen, mining, mine, mines, goudwinning, goud mijn, gold mining, bauxiet, bauxite, steengroeve, quarry",
  sub="mining", rx=r"mining|mijnbouw|\bmines?\b|bauxi|quarry|steengroeve", scope="V")
C("manufacturing", "Manufacturing & industry", "Productie & industrie", "Fabricación e industria", "制造业", "Industrie & fabrication", "Indústria",
  "fabriek, fabrieken, productie, producent, producenten, manufacturer, manufacturers, manufacturing, factory, factories, "
  "industrie, industrieel, industrial, machines, machinery, equipment, apparatuur, verpakking, packaging",
  sub="manufacturing", rx=r"\|.*(manufactur|\bfactory\b|fabriek|producer of|industrial|machinery)", scope="V")
C("media", "Media, TV & radio", "Media, tv & radio", "Medios, TV y radio", "媒体", "Médias, TV & radio", "Mídia, TV e rádio",
  "media, tv, televisie, televisiezender, radio, radiostation, zender, omroep, krant, kranten, newspaper, magazine, "
  "nieuws, journalist, adverteren, advertising space, podcast",
  sub="media-broadcast", rx=r"\bmedia\b|television|televisie|\bradio\b|broadcast|omroep|newspaper|krant|magazine", scope="V",
  r="web-design", neg=r"technology and media company|technologie- en mediabedrijf")
C("government", "Government & public services", "Overheid & publieke diensten", "Gobierno y servicios públicos", "政府与公共服务", "Administrations", "Governo e serviços públicos",
  "overheid, ministerie, ministeries, ministry, government, gemeente, districtscommissariaat, dc, bevolkingsregister, cbb, "
  "uittreksel, paspoort, passport, id kaart, id-kaart, vergunning, vergunningen, permit, permits, kkf, kamer van koophandel, "
  "chamber of commerce, ambassade, ambassades, embassy, embassies, consulaat, consulate, politie, police",
  rx=r"\bministry of|ministerie van|government (agency|department|office|institution|body)|overheidsinstantie|embassy|ambassade|consula|chamber of commerce|kamer van koophandel|\bpolice\b|politie|\bstate (agency|institute)",
  scope="V", neg=r"government clients|clients (in|from) (the )?government|overheidsklanten|serving government")

# ── Site tools (no listings; guide pages match through their keyword blob) ──
C("safety", "Safety", "Veiligheid", "Seguridad", "安全", "Sécurité", "Segurança",
  "safe, safety, is it safe, veilig, veiligheid, onveilig, unsafe, crime, criminaliteit, dangerous, gevaarlijk, beroving, "
  "robbery, theft, diefstal, scams, oplichting, seguro, seguridad, securite, segurança",
  scope="")
C("visa", "Visas & entry", "Visum & inreizen", "Visados y entrada", "签证与入境", "Visas & entrée", "Vistos e entrada",
  "visa, visum, visa suriname, tourist card, toeristenkaart, toerist kaart, e-visa, evisa, entry fee, entree fee, inreizen, "
  "inreisregels, entry requirements, passport, paspoort, douane regels, customs rules, visado, tarjeta de turista, visto",
  scope="")
C("vaccination", "Vaccinations", "Vaccinaties", "Vacunas", "疫苗接种", "Vaccinations", "Vacinas",
  "vaccinatie, vaccinaties, vaccineren, inenting, inentingen, inenten, prik, vaccination, vaccinations, vaccine, vaccines, "
  "travel clinic, reisvaccinatie, gele koorts, yellow fever, vacuna, vacunas, vacina, vacinas",
  rx=r"vaccin|inenting|immunis|immuniz|yellow fever|gele koorts", scope="V", neg=r"veterin|dierenarts|animal|pets?\b", r="doctor")
C("events", "Events & festivals", "Evenementen & festivals", "Eventos y festivales", "活动与节庆", "Événements & festivals", "Eventos e festivais",
  "events, event, evenementen, evenement, festival, festivals, agenda, uitagenda, wat te doen, what's on, whats on, "
  "this weekend, dit weekend, deze week, concerten, feestdagen, holidays, public holidays, owru yari, oud en nieuw, "
  "keti koti, holi, phagwa, divali, diwali, kerst, christmas, carnaval, carnival, suripop, parbo night",
  scope="")
C("weather", "Weather & tides", "Weer & getijden", "Clima y mareas", "天气与潮汐", "Météo & marées", "Clima e marés",
  "weer, weerbericht, weersverwachting, weather, weather forecast, forecast, regen, rain, regent het, onweer, storm, "
  "temperatuur, temperature, hitte, heat, uv, getij, getijden, tij, eb, vloed, tide, tides, hoogwater",
  scope="")
C("outages", "Power & water outages", "Stroom- & waterstoringen", "Cortes de luz y agua", "停电停水", "Coupures d'eau & d'électricité", "Falta de luz e água",
  "stroomstoring, stroomstoringen, stroom uitval, stroomuitval, black out, blackout, geen stroom, waterstoring, waterstoringen, "
  "geen water, power outage, power cut, power outages, water outage, onderbreking, onderbrekingen, afsluiting, ebs storing",
  scope="", r="utilities")

assert len({c["i"] for c in CONCEPTS}) == len(CONCEPTS), "duplicate concept id"

# ── Places ─────────────────────────────────────────────────────────────────
# term -> district. A district name maps to itself. Paramaribo neighbourhoods
# map to Paramaribo; ressorten / towns elsewhere to their district.
_PLACES = {
 "Paramaribo": "paramaribo, parbo, pbo, binnenstad, centrum, center, centre, downtown, waterkant, "
               "noord, paramaribo noord, zuid, paramaribo zuid, west, paramaribo west, oost, blauwgrond, rainville, munder, "
               "munderbuiten, beekhuizen, weg naar zee, welgelegen, tammenga, flora, latour, pontbuiten, livorno, "
               "uitvlugt, zorg en hoop, frimangron, kasabaholo, combe, abrabroki, maretraite, ma retraite, mon plaisir, "
               "morgenstond, elisabethshof, geyersvlijt, leonsberg, cultuurtuin, molenpad, ephraimszegen, hannaslust, "
               "half flora, poelepantje, tourtonne, charlesburg, sunny point, van dijk, land van dijk, sophia's lust, "
               "ringweg, hermitage, wanica weg, kwattaweg, coppename, jarikaba weg, nieuw weergevonden, wilhelminastraat, "
               "dijkveld, morgenstond, zinnia, sophialaan, garnizoenspad, verlengde gemenelandsweg, gemenelandsweg, "
               "lallarookh, lalla rookh, lalla rookhweg, leysweg, tourtonnelaan, kernkampweg, hk weg, indira gandhiweg",
 "Wanica": "wanica, kwatta, lelydorp, saramacca polder, koewarasan, de nieuwe grond, nieuwe grond, houttuin, domburg, "
           "santigron, mattonshoop, leiding, leidingen, santo boma, tout lui faut, welgedacht, welgedacht a, welgedacht b, "
           "welgedacht c, boxel, uitkijk wanica, la vigilantia, pad van wanica, indira gandhiweg wanica, commissaris weytingweg",
 "Commewijne": "commewijne, meerzorg, laarwijk, peperpot, tamanredjo, nieuw amsterdam, alkmaar, marienburg, mariënburg, "
               "tamansari, wonoredjo, johan margaretha, margaretha, bakkie, frederiksdorp, spieringshoek",
 "Para": "para, onverwacht, bernharddorp, zanderij, hollandse kamp, paranam, powakka, redi doti, matta, republiek, "
         "onverdacht, bersaba, jodensavanne, carolina, bigi poika, colakreek, cola kreek",
 "Saramacca": "saramacca, groningen, calcutta, tijgerkreek, kampong baroe, wayamboweg, jarikaba, uitkijk",
 "Nickerie": "nickerie, nieuw nickerie, wageningen, groot henar, henar",
 "Coronie": "coronie, totness, friendship, johanna maria",
 "Marowijne": "marowijne, moengo, albina, galibi, wanhatti, patamacca, moengo tapoe",
 "Brokopondo": "brokopondo, brownsweg, klaaskreek, afobaka, marshallkreek, kwakoegron, sarakreek, brownsberg",
 "Sipaliwini": "sipaliwini, binnenland, atjoni, pokigron, botopasi, apoera, washabo, kwamalasamutu, tapanahony, "
               "boven suriname, boven saramacca, coeroeni, kabalebo, palumeu, raleighvallen, kasikasima, stoelmanseiland, "
               "drietabbetje, nieuw aurora, gunsi, laduani, awarradam",
}
PLACES = {}
for _d, _terms in _PLACES.items():
    for _t in _terms.split(","):
        _t = _t.strip()
        if _t and _t not in PLACES:
            PLACES[_t] = _d
DISTRICTS = sorted(_PLACES)

# Words that never have to match: intent verbs, politeness, generic nouns.
FILLER = """
can could done do does get got have has someone somebody anyone where there which who iets ergens graag even
en of and or with without y e et ou o el la los las le les un une una uno des du au aux da do dos das em no na
onde donde ou que qui quoi quel quelle what which near pres cerca perto barato barata baratos pas cher bon marche
economico economique bellen call calling bel boeken book booking reserveren reservering reserve reservation
afspraak appointment maken bestellen online whatsapp
snel quickly fast asap legen ledigen leeghalen tipica tipico typique typiques laten doen maken maakt gemaakt repareren gerepareerd fixen fix fixed bestellen bestel kopen koop kopen verkoop zoeken zoek
zoekt nodig wil willen moet kan kun kunnen iemand die dat mijn mij me je jij u uw ons onze een de het van voor met naar
aan bij in op om te tot uit waar wat welke wie hoe hier daar er is zijn ook nog al goed goede beste best top goedkoop
goedkope cheap affordable budget betaalbaar near nearby dichtbij buurt omgeving close around open nu vandaag today now
openingstijden openingstijd opening hours hour tijden adres address telefoonnummer nummer number contact
contactgegevens prijs prijzen price prices kosten tarief tarieven menu menukaart website site info informatie review
reviews suriname sr srname surinam surinamese the a an of and for to with from at on my your our you me i im i'm we
need want looking find get show give some any something please pls aub alsjeblieft service services diensten dienst
bedrijf bedrijven company companies firm zaak zaken winkel shop store place places plek plekken spot thuis aan huis
home house located locatie location
""".split()
# Words in FILLER that ARE concepts when they stand alone are resolved in JS:
# a concept/place term always wins over filler (e.g. "winkel" alone).
FILLER = sorted(set(FILLER))

# Repair intent: "telefoon laten repareren" -> phone repair, "auto kapot" ->
# garage. A concept with fx= is swapped for its repair counterpart.
REPAIR_WORDS = """repareren reparatie reparaties repareert gerepareerd repair repairs repairing fix fixen fixed
herstellen herstel hersteld kapot stuk broken maken""".split()

# Generic heads for decompounding: "nagelstudio" = "nagel" + "studio",
# "aircomonteur" = "airco" + "monteur", "taartenbakker" = "taarten" + "bakker".
HEADS = """studio studios salon salons zaak zaken winkel winkels shop shops store bedrijf bedrijven service services
centrum center centre huis man mannen specialist specialiste stylist styliste stylisten monteur monteurs reparatie
reparaties maker makers bakker bakkerij handel kantoor atelier boetiek boutique lounge bar point plaza depot markt
verhuur dienst diensten man boy expert""".split()


def fold(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s.lower()


def norm_term(s):
    return " ".join(t for t in re.split(r"[^a-z0-9]+", fold(s)) if t)


# Spanish / French / Portuguese visitors search in their own language: the
# hand-written labels double as search terms (whole label + longer words and
# their singular). Connectors and words that clash with a place are skipped.
_LABEL_SKIP = set("""para pour avec sans como comme dans sobre entre servicios services servicos tienda tiendas
magasin magasins lojas comida cuisine produits productos produtos articulos artigos articles locales""".split())
_CJK = re.compile(r"[\u3400-\u9fff]+")


def _label_terms(c):
    out = []
    for lang in ("es", "fr", "pt"):
        lab = c["l"].get(lang) or ""
        whole = norm_term(lab)
        if whole and " " in whole:
            out.append(whole)
        for w in whole.split():
            if len(w) < 5 or w in _LABEL_SKIP or w in PLACES:
                continue
            out.append(w)
            if w.endswith("es") and len(w) > 6:
                out.append(w[:-2])
            if w.endswith("s") and len(w) > 5:
                out.append(w[:-1])
    return out


def _zh_terms(c):
    lab = c["l"].get("zh") or ""
    parts = [lab] + re.split(r"[与和、及/]", lab)
    return [x for x in dict.fromkeys(p.strip() for p in parts) if len(x) >= 2 and _CJK.fullmatch(x)]


def vocab_json():
    """Compact vocabulary for the browser: concepts (id, labels, terms, related,
    includes), places (term -> district), filler and decompounding heads."""
    cs = []
    for c in CONCEPTS:
        terms = []
        for t in c["terms"] + _label_terms(c):
            n = norm_term(t)
            if n and n not in terms:
                terms.append(n)
        terms += [z for z in _zh_terms(c) if z not in terms]
        row = {"i": c["i"], "l": c["l"], "t": terms}
        if c["r"]:
            row["r"] = c["r"]
        if c["inc"]:
            row["x"] = c["inc"]
        if c["fx"]:
            row["fx"] = c["fx"]
        cs.append(row)
    places = {"帕拉马里博": "Paramaribo"}
    for t, d in PLACES.items():
        n = norm_term(t)
        if n:
            places.setdefault(n, d)
    return {"v": 1, "c": cs, "p": places, "f": [norm_term(w) for w in FILLER if norm_term(w)] + ["苏里南"],
            "rw": sorted({norm_term(w) for w in REPAIR_WORDS}),
            "h": sorted({norm_term(h) for h in HEADS})}


_RX = None

def _compiled():
    global _RX
    if _RX is None:
        _RX = [(c, re.compile(c["rx"], re.I) if c["rx"] else None, re.compile(c["neg"], re.I) if c["neg"] else None,
                set(c["sub"]), set(c["scope"])) for c in CONCEPTS]
    return _RX

_STREET = re.compile(r"\b[\w'.-]*(weg|straat|laan|kade|plein|dreef|singel|gracht|pad)\b", re.I)
_SCOPE = {"Eat & Drink": "E", "Stay": "S", "Nature": "N", "Activities": "A", "Shopping": "H", "Services": "V"}


def tags_for(b, cat, nl_desc=""):
    """Concept ids a listing really offers. `b` is a listing dict (name, subcat,
    description), `cat` its section ("Eat & Drink" ...), nl_desc the Dutch
    description from translations.json."""
    letter = _SCOPE.get(cat, "")
    sub = b.get("subcat") or ""
    # "name | description" so a pattern can be limited to the name with ^[^|]*
    # or to the description with \|.* ; street names are blanked first
    # ("Sir Winston Churchillweg" is not a church, "Steenbakkerijstraat" no bakery)
    desc = " ".join([b.get("description") or b.get("desc") or "", nl_desc or ""])
    desc = _STREET.sub(" ", desc)
    txt = ((b.get("name") or "") + " | " + desc).lower()
    out = []
    for c, rx, neg, subs, scope in _compiled():
        hit = False
        if sub and sub in subs and (not scope or letter in scope):
            hit = True
        elif rx is not None and letter and letter in scope and rx.search(txt):
            # a negative pattern anywhere cancels the description match
            # (type membership via `sub` still applies)
            hit = neg is None or not neg.search(txt)
        if hit:
            out.append(c["i"])
    return out


# ── Index enrichment (called from generate.py right before search-index.json is written) ──
_KW_STOP = set("""
a an and are as at be been being but by can for from had has have her his in into is it its of on or our that the their
them there these they this those to was were what when where which who will with you your also just more most very well
well-known known located offering serving serves offers features featuring style styled plus per each while both over
under near around de het een en van in op om te met voor is zijn ook aan bij als dat die dit door naar niet uit worden
wordt heeft hebben zich onder over tussen waar wat wie hun ligt gelegen biedt bieden maar zoals veel meer zeer wel weer
nog dan af ten der des dus geen hier daar deze dien suriname surinamese surinaamse paramaribo company business bedrijf
based located gevestigd since sinds offers aanbod services diensten various verschillende range wide breed including
waaronder aanbiedt aanbieden verkoopt verkopen levert leveren opgericht branch branches filiaal vestiging selling sells
sold founded products product producten supplies supplier leverancier professional professionele one een tot international
internationale local lokale central centrale quality kwaliteit offering providing provides provide provided biedt
service store shop winkel kantoor company bedrijven its zijn haar hun customers klanten clients people mensen also
year years jaar jaren new nieuwe well both all alle other andere""".split())


def _toks(txt, have, cap):
    out = []
    for t in re.findall(r"[a-z0-9à-ÿ]{3,}", (txt or "").lower()):
        if t in _KW_STOP or t in have or t.isdigit():
            continue
        have.add(t)
        out.append(t)
        if len(out) >= cap:
            break
    return out


def _addr(b):
    a = (b.get("address") or "").strip()
    a = re.sub(r",?\s*(Suriname|Paramaribo,\s*Suriname)\s*$", "", a, flags=re.I).strip(" ,")
    if not a or a.lower() in ("paramaribo", (b.get("area") or "").lower()):
        return ""
    return a[:90]


def enrich_index(entries, sources, nl_of):
    """entries: the _SI_LIST dicts. sources: url -> (listing dict, section).
    nl_of: english description -> dutch description ('' when unknown).
    Listings get "t" (concept ids), "s" (address, when it says more than the
    district) and a keyword blob with English AND Dutch description words.
    Other entries (guides, Flora & Fauna, flights) are left as they are."""
    n_tag = 0
    # words the browser always reads as a concept or as filler never match
    # free text, so a listing's keyword blob does not need to carry them
    dead = {t for c in CONCEPTS for t in (norm_term(x) for x in c["terms"]) if t and " " not in t}
    dead |= {norm_term(w) for w in FILLER}
    for e in entries:
        src = sources.get(e.get("u"))
        if not src:
            continue
        b, cat = src
        desc = b.get("description") or b.get("desc") or ""
        nl = nl_of(desc) or ""
        tags = tags_for(b, cat, nl)
        if tags:
            e["t"] = tags
            n_tag += 1
        ad = _addr(b)
        if ad:
            e["s"] = ad
        have = set(dead)
        head = " ".join(x for x in [b.get("name", ""), (b.get("subcat") or "").replace("-", " ")] if x).lower()
        for t in re.findall(r"[a-z0-9à-ÿ]{3,}", head):
            have.add(t)
        extra = " ".join(b.get("tags") or []) + " " + (b.get("badge") or "")
        words = _toks(desc + " " + extra, have, 40) + _toks(nl, have, 30)
        e["k"] = " ".join([head] + words)
    return n_tag
