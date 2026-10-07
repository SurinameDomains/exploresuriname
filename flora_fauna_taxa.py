"""Flora & Fauna of Suriname: grouping rules and every fixed label in 4 languages.

Shared by the offline data script (scripts/flora_fauna_build_data.py) and the
page builder (flora_fauna_pages.py). Labels are hand-written in EN / NL / ES /
ZH (Simplified), plus FR / PT-BR in flora_fauna_frpt.py. Chinese is never machine-filled (see README_i18n.md).

A species lands in exactly one GROUP (mammals, birds, ...) and one SUBGROUP
inside it (parrots, snakes, orchids by family, ...). Rules match on the GBIF
backbone classification: kingdom, phylum, class, order, family.
"""

# ── label helper: (en, nl, es, zh) + fr/pt from flora_fauna_frpt.py ──────────
LANGS = ("en", "nl", "es", "zh", "fr", "pt")

try:
    from flora_fauna_frpt import FRPT as _FRPT
except Exception:          # table missing: French/Portuguese show English
    _FRPT = {}


def L(en, nl, es, zh, fr=None, pt=None):
    """A label in every language. French and Brazilian Portuguese come from the
    hand-written table in flora_fauna_frpt.py (keyed by the English text) unless
    given here; a label missing from it falls back to English."""
    t = _FRPT.get(en) or (None, None)
    return {"en": en, "nl": nl, "es": es, "zh": zh, "fr": fr or t[0] or en, "pt": pt or t[1] or en}


# ── groups ───────────────────────────────────────────────────────────────────
# key, realm, label, one-line intro
GROUPS = [
    ("mammals", "animals", L("Mammals", "Zoogdieren", "Mamíferos", "哺乳动物"),
     L("Monkeys, big cats, sloths, bats, manatees and every other mammal recorded in Suriname.",
       "Apen, grote katten, luiaards, vleermuizen, lamantijnen en alle andere zoogdieren die in Suriname zijn waargenomen.",
       "Monos, grandes felinos, perezosos, murciélagos, manatíes y todos los demás mamíferos registrados en Surinam.",
       "猴类、大型猫科动物、树懒、蝙蝠、海牛，以及在苏里南记录到的所有其他哺乳动物。")),
    ("birds", "animals", L("Birds", "Vogels", "Aves", "鸟类"),
     L("From the great kiskadee in every Paramaribo garden to harpy eagles and cock-of-the-rocks deep in the interior.",
       "Van de grietjebie in elke tuin in Paramaribo tot harpij-arenden en rotshanen diep in het binnenland.",
       "Desde el bienteveo de cualquier jardín de Paramaribo hasta el águila arpía y el gallito de las rocas en el interior.",
       "从帕拉马里博每个花园里的大食蝇霸鹟，到内陆深处的角雕和圭亚那动冠伞鸟。")),
    ("reptiles", "animals", L("Reptiles", "Reptielen", "Reptiles", "爬行动物"),
     L("Snakes, lizards, caimans and turtles, including the sea turtles that nest on Suriname's beaches.",
       "Slangen, hagedissen, kaaimannen en schildpadden, waaronder de zeeschildpadden die op de Surinaamse stranden nestelen.",
       "Serpientes, lagartos, caimanes y tortugas, incluidas las tortugas marinas que anidan en las playas de Surinam.",
       "蛇、蜥蜴、凯门鳄和龟类，包括在苏里南海滩上筑巢的海龟。")),
    ("amphibians", "animals", L("Amphibians", "Amfibieën", "Anfibios", "两栖动物"),
     L("Frogs, toads and caecilians, from the blue poison dart frog to the Surinam toad.",
       "Kikkers, padden en wormsalamanders, van de blauwe pijlgifkikker tot de Surinaamse pad.",
       "Ranas, sapos y cecilias, desde la rana dardo azul hasta el sapo de Surinam.",
       "青蛙、蟾蜍和蚓螈，从蓝色箭毒蛙到负子蟾。")),
    ("fish", "animals", L("Fish", "Vissen", "Peces", "鱼类"),
     L("Freshwater fish of the rivers and swamps, and the fish, sharks and rays of the Atlantic coast.",
       "Zoetwatervissen uit de rivieren en zwampen, en de vissen, haaien en roggen van de Atlantische kust.",
       "Peces de agua dulce de los ríos y pantanos, y los peces, tiburones y rayas de la costa atlántica.",
       "河流与沼泽中的淡水鱼，以及大西洋沿岸的鱼类、鲨鱼和鳐鱼。")),
    ("insects", "animals", L("Insects", "Insecten", "Insectos", "昆虫"),
     L("Butterflies, beetles, ants, dragonflies, cicadas and thousands of other insects.",
       "Vlinders, kevers, mieren, libellen, cicaden en duizenden andere insecten.",
       "Mariposas, escarabajos, hormigas, libélulas, cigarras y miles de insectos más.",
       "蝴蝶、甲虫、蚂蚁、蜻蜓、蝉以及成千上万种其他昆虫。")),
    ("arachnids", "animals", L("Spiders & scorpions", "Spinnen en schorpioenen", "Arañas y escorpiones", "蜘蛛与蝎子"),
     L("Spiders, tarantulas, scorpions, harvestmen, ticks and mites.",
       "Spinnen, vogelspinnen, schorpioenen, hooiwagens, teken en mijten.",
       "Arañas, tarántulas, escorpiones, opiliones, garrapatas y ácaros.",
       "蜘蛛、捕鸟蛛、蝎子、盲蛛、蜱和螨。")),
    ("crustaceans", "animals", L("Crabs & other crustaceans", "Krabben en andere kreeftachtigen", "Cangrejos y otros crustáceos", "蟹类及其他甲壳动物"),
     L("Crabs, shrimps, prawns and their many small relatives in rivers, mangroves and the sea.",
       "Krabben, garnalen en hun vele kleine verwanten in rivieren, mangroven en de zee.",
       "Cangrejos, camarones y sus muchos parientes pequeños en ríos, manglares y el mar.",
       "河流、红树林和海洋中的蟹、虾及其众多小型近亲。")),
    ("molluscs", "animals", L("Snails, shells & other molluscs", "Slakken, schelpen en andere weekdieren", "Caracoles, conchas y otros moluscos", "螺、贝及其他软体动物"),
     L("Land and freshwater snails, sea shells, mussels, squid and octopus.",
       "Land- en zoetwaterslakken, schelpen, mosselen, inktvissen en octopussen.",
       "Caracoles terrestres y de agua dulce, conchas marinas, mejillones, calamares y pulpos.",
       "陆地和淡水螺类、海贝、贻贝、鱿鱼和章鱼。")),
    ("other-animals", "animals", L("Other invertebrates", "Overige ongewervelden", "Otros invertebrados", "其他无脊椎动物"),
     L("Centipedes, millipedes, worms, corals, jellyfish, sponges, sea stars and more.",
       "Duizendpoten, miljoenpoten, wormen, koralen, kwallen, sponzen, zeesterren en meer.",
       "Ciempiés, milpiés, gusanos, corales, medusas, esponjas, estrellas de mar y más.",
       "蜈蚣、马陆、蠕虫、珊瑚、水母、海绵、海星等。")),
    ("flowering-plants", "plants", L("Flowering plants", "Bloemplanten", "Plantas con flor", "开花植物"),
     L("Trees, shrubs, herbs, vines, grasses and water plants, grouped by plant family.",
       "Bomen, struiken, kruiden, lianen, grassen en waterplanten, ingedeeld per plantenfamilie.",
       "Árboles, arbustos, hierbas, enredaderas, gramíneas y plantas acuáticas, agrupados por familia.",
       "乔木、灌木、草本、藤本、禾草和水生植物，按植物科分类。")),
    ("orchids", "plants", L("Orchids", "Orchideeën", "Orquídeas", "兰花"),
     L("One of the largest plant families in Suriname, most of them growing on trees in the rainforest.",
       "Een van de grootste plantenfamilies van Suriname; de meeste groeien op bomen in het regenwoud.",
       "Una de las familias de plantas más grandes de Surinam; la mayoría crece sobre los árboles de la selva.",
       "苏里南最大的植物科之一，大多附生在雨林的树上。")),
    ("palms", "plants", L("Palms", "Palmen", "Palmeras", "棕榈"),
     L("Awara, maripa, podosiri, troelie and every other palm, wild or planted.",
       "Awara, maripa, podosiri, troelie en alle andere palmen, wild of aangeplant.",
       "Awara, maripa, podosiri, troelie y todas las demás palmeras, silvestres o cultivadas.",
       "阿瓦拉棕、马里帕棕、阿萨伊棕、特罗利棕以及所有其他野生或栽培的棕榈。")),
    ("ferns", "plants", L("Ferns & clubmosses", "Varens en wolfsklauwen", "Helechos y licopodios", "蕨类与石松"),
     L("Tree ferns, climbing ferns, filmy ferns and clubmosses.",
       "Boomvarens, klimvarens, vliesvarens en wolfsklauwen.",
       "Helechos arborescentes, trepadores, himenofiláceos y licopodios.",
       "桫椤、攀援蕨、膜蕨和石松。")),
    ("mosses", "plants", L("Mosses & liverworts", "Mossen en levermossen", "Musgos y hepáticas", "苔藓与地钱"),
     L("The small green carpets on tree trunks, rocks and the forest floor.",
       "De kleine groene tapijten op boomstammen, rotsen en de bosbodem.",
       "Las pequeñas alfombras verdes sobre troncos, rocas y el suelo del bosque.",
       "覆盖在树干、岩石和林地上的小小绿色地毯。")),
    ("other-plants", "plants", L("Other plants & algae", "Overige planten en algen", "Otras plantas y algas", "其他植物与藻类"),
     L("Conifers, cycads, Gnetum vines and green and red algae.",
       "Naaldbomen, palmvarens, Gnetum-lianen en groen- en roodwieren.",
       "Coníferas, cícadas, lianas de Gnetum y algas verdes y rojas.",
       "针叶树、苏铁、买麻藤以及绿藻和红藻。")),
    ("fungi", "fungi", L("Fungi & lichens", "Paddenstoelen, schimmels en korstmossen", "Hongos y líquenes", "真菌与地衣"),
     L("Mushrooms, bracket fungi, cup fungi and lichens.",
       "Paddenstoelen, houtzwammen, bekerzwammen en korstmossen.",
       "Setas, hongos de repisa, hongos de copa y líquenes.",
       "蘑菇、多孔菌、盘菌和地衣。")),
]
GROUP_KEYS = [g[0] for g in GROUPS]
GROUP = {g[0]: {"realm": g[1], "label": g[2], "intro": g[3]} for g in GROUPS}

REALMS = {
    "animals": L("Animals", "Dieren", "Animales", "动物"),
    "plants": L("Plants", "Planten", "Plantas", "植物"),
    "fungi": L("Fungi", "Schimmels", "Hongos", "真菌"),
}

# ── subgroups ────────────────────────────────────────────────────────────────
# Each: key, label, rule. Rule keys: classes / orders / families (sets of GBIF
# names). First match wins; a group's last entry ("other") catches the rest.
SNAKE_FAMILIES = {"Aniliidae", "Anomalepididae", "Boidae", "Colubridae", "Dipsadidae", "Elapidae",
                  "Leptotyphlopidae", "Typhlopidae", "Viperidae", "Natricidae", "Pythonidae",
                  "Tropidophiidae", "Xenodontidae", "Sibynophiidae", "Lamprophiidae"}
WHALE_FAMILIES = {"Delphinidae", "Balaenopteridae", "Physeteridae", "Kogiidae", "Ziphiidae",
                  "Balaenidae", "Iniidae", "Phocoenidae", "Pontoporiidae"}

SUBGROUPS = {
    "mammals": [
        ("monkeys", L("Monkeys", "Apen", "Monos", "猴类"), {"orders": {"Primates"}}),
        ("cats-dogs-otters", L("Cats, otters & other carnivores", "Katten, otters en andere roofdieren", "Felinos, nutrias y otros carnívoros", "猫科、水獭及其他食肉动物"), {"orders": {"Carnivora"}}),
        ("sloths-anteaters-armadillos", L("Sloths, anteaters & armadillos", "Luiaards, miereneters en gordeldieren", "Perezosos, osos hormigueros y armadillos", "树懒、食蚁兽与犰狳"), {"orders": {"Pilosa", "Cingulata"}}),
        ("whales-dolphins", L("Dolphins & whales", "Dolfijnen en walvissen", "Delfines y ballenas", "海豚与鲸"), {"families": WHALE_FAMILIES, "orders": {"Cetacea"}}),
        ("hoofed-mammals", L("Deer, peccaries & tapir", "Herten, pekari's en tapir", "Venados, pecaríes y tapir", "鹿、西猯与貘"), {"orders": {"Artiodactyla", "Perissodactyla"}}),
        ("rodents", L("Rodents", "Knaagdieren", "Roedores", "啮齿动物"), {"orders": {"Rodentia", "Lagomorpha"}}),
        ("bats", L("Bats", "Vleermuizen", "Murciélagos", "蝙蝠"), {"orders": {"Chiroptera"}}),
        ("opossums", L("Opossums", "Buidelratten", "Zarigüeyas", "负鼠"), {"orders": {"Didelphimorphia"}}),
        ("other-mammals", L("Manatee & other mammals", "Lamantijn en andere zoogdieren", "Manatí y otros mamíferos", "海牛及其他哺乳动物"), {}),
    ],
    "birds": [
        ("parrots", L("Parrots & macaws", "Papegaaien en ara's", "Loros y guacamayos", "鹦鹉与金刚鹦鹉"), {"orders": {"Psittaciformes"}}),
        ("toucans-woodpeckers", L("Toucans, woodpeckers & jacamars", "Toekans, spechten en glansvogels", "Tucanes, carpinteros y jacamares", "巨嘴鸟、啄木鸟与鹟䴕"), {"orders": {"Piciformes", "Galbuliformes"}}),
        ("hummingbirds-swifts", L("Hummingbirds & swifts", "Kolibries en gierzwaluwen", "Colibríes y vencejos", "蜂鸟与雨燕"), {"orders": {"Apodiformes"}}),
        ("birds-of-prey", L("Birds of prey & vultures", "Roofvogels en gieren", "Aves rapaces y zopilotes", "猛禽与美洲鹫"), {"orders": {"Accipitriformes", "Falconiformes", "Cathartiformes"}}),
        ("owls", L("Owls", "Uilen", "Búhos y lechuzas", "鸮"), {"orders": {"Strigiformes"}}),
        ("herons-ibises", L("Herons, ibises & storks", "Reigers, ibissen en ooievaars", "Garzas, ibis y cigüeñas", "鹭、鹮与鹳"), {"orders": {"Pelecaniformes", "Ciconiiformes", "Phoenicopteriformes"}}),
        ("shorebirds-gulls", L("Shorebirds, gulls & terns", "Steltlopers, meeuwen en sterns", "Aves playeras, gaviotas y charranes", "鸻鹬、鸥与燕鸥"), {"orders": {"Charadriiformes"}}),
        ("seabirds", L("Seabirds & cormorants", "Zeevogels en aalscholvers", "Aves marinas y cormoranes", "海鸟与鸬鹚"), {"orders": {"Suliformes", "Procellariiformes", "Phaethontiformes"}}),
        ("ducks", L("Ducks & screamers", "Eenden en hoenderkoeten", "Patos y chajás", "鸭与叫鸭"), {"orders": {"Anseriformes"}}),
        ("rails-sunbittern", L("Rails, limpkin & sunbittern", "Rallen, koerlan en zonneral", "Rascones, carrao y tigana", "秧鸡、秧鹤与日鳽"), {"orders": {"Gruiformes", "Eurypygiformes"}}),
        ("guans-curassows", L("Guans, curassows & quails", "Sjakohoenders, hokko's en kwartels", "Pavas, paujiles y codornices", "冠雉、凤冠雉与鹑类"), {"orders": {"Galliformes"}}),
        ("tinamous", L("Tinamous", "Tinamoes", "Tinamúes", "䳍"), {"orders": {"Tinamiformes"}}),
        ("pigeons-doves", L("Pigeons & doves", "Duiven", "Palomas", "鸠鸽"), {"orders": {"Columbiformes"}}),
        ("cuckoos-hoatzin", L("Cuckoos, anis & hoatzin", "Koekoeken, ani's en hoatzin", "Cucos, garrapateros y hoacín", "杜鹃、犀鹃与麝雉"), {"orders": {"Cuculiformes", "Opisthocomiformes"}}),
        ("nightjars-potoos", L("Nightjars, potoos & oilbird", "Nachtzwaluwen, reuzennachtzwaluwen en vetvogel", "Chotacabras, nictibios y guácharo", "夜鹰、林鸱与油鸱"), {"orders": {"Caprimulgiformes", "Nyctibiiformes", "Steatornithiformes"}}),
        ("kingfishers-trogons", L("Kingfishers, motmots & trogons", "IJsvogels, motmots en trogons", "Martines pescadores, momotos y trogones", "翠鸟、翠鴗与咬鹃"), {"orders": {"Coraciiformes", "Trogoniformes"}}),
        ("songbirds", L("Songbirds & other perching birds", "Zangvogels en andere zangvogelachtigen", "Pájaros cantores y otros paseriformes", "鸣禽及其他雀形目鸟类"), {"orders": {"Passeriformes"}}),
        ("other-birds", L("Other birds", "Overige vogels", "Otras aves", "其他鸟类"), {}),
    ],
    "reptiles": [
        ("snakes", L("Snakes", "Slangen", "Serpientes", "蛇"), {"families": SNAKE_FAMILIES}),
        ("turtles", L("Turtles & tortoises", "Schildpadden", "Tortugas", "龟鳖"), {"classes": {"Testudines"}}),
        ("caimans", L("Caimans", "Kaaimannen", "Caimanes", "凯门鳄"), {"classes": {"Crocodylia"}}),
        ("lizards", L("Lizards & worm lizards", "Hagedissen en wormhagedissen", "Lagartos y anfisbenas", "蜥蜴与蚓蜥"), {}),
    ],
    "amphibians": [
        ("frogs-toads", L("Frogs & toads", "Kikkers en padden", "Ranas y sapos", "蛙与蟾蜍"), {"orders": {"Anura"}}),
        ("caecilians-salamanders", L("Caecilians & salamanders", "Wormsalamanders en salamanders", "Cecilias y salamandras", "蚓螈与蝾螈"), {}),
    ],
    "fish": [
        ("characins-piranhas", L("Characins, piranhas & tetras", "Zalmkarpers, piranha's en tetra's", "Carácidos, pirañas y tetras", "脂鲤、食人鱼与灯鱼"), {"orders": {"Characiformes"}}),
        ("catfish", L("Catfish", "Meervallen", "Bagres", "鲶鱼"), {"orders": {"Siluriformes"}}),
        ("cichlids", L("Cichlids", "Cichliden", "Cíclidos", "慈鲷"), {"families": {"Cichlidae"}}),
        ("knifefish", L("Knifefish & electric eel", "Mesvissen en sidderaal", "Peces cuchillo y anguila eléctrica", "电鳗与裸背鳗"), {"orders": {"Gymnotiformes"}}),
        ("killifish-livebearers", L("Killifish, livebearers & four-eyed fish", "Killivisjes, levendbarenden en vieroogvissen", "Killis, vivíparos y cuatrojos", "鳉、胎生鱼与四眼鱼"), {"orders": {"Cyprinodontiformes"}}),
        ("sharks-rays", L("Sharks & rays", "Haaien en roggen", "Tiburones y rayas", "鲨鱼与鳐鱼"), {"classes": {"Elasmobranchii", "Holocephali"}}),
        ("other-fish", L("Other fish (coast and sea)", "Overige vissen (kust en zee)", "Otros peces (costa y mar)", "其他鱼类（沿海与海洋）"), {}),
    ],
    "insects": [
        ("butterflies-moths", L("Butterflies & moths", "Vlinders en motten", "Mariposas y polillas", "蝴蝶与蛾"), {"orders": {"Lepidoptera"}}),
        ("beetles", L("Beetles", "Kevers", "Escarabajos", "甲虫"), {"orders": {"Coleoptera"}}),
        ("ants-bees-wasps", L("Ants, bees & wasps", "Mieren, bijen en wespen", "Hormigas, abejas y avispas", "蚂蚁、蜜蜂与胡蜂"), {"orders": {"Hymenoptera"}}),
        ("dragonflies", L("Dragonflies & damselflies", "Libellen en waterjuffers", "Libélulas y caballitos del diablo", "蜻蜓与豆娘"), {"orders": {"Odonata"}}),
        ("grasshoppers-crickets", L("Grasshoppers & crickets", "Sprinkhanen en krekels", "Saltamontes y grillos", "蝗虫与蟋蟀"), {"orders": {"Orthoptera"}}),
        ("true-bugs-cicadas", L("True bugs, cicadas & leafhoppers", "Wantsen, cicaden en cicadellen", "Chinches, cigarras y chicharritas", "蝽、蝉与叶蝉"), {"orders": {"Hemiptera"}}),
        ("flies-mosquitoes", L("Flies & mosquitoes", "Vliegen en muggen", "Moscas y mosquitos", "蝇与蚊"), {"orders": {"Diptera"}}),
        ("mantises-stick-insects", L("Mantises & stick insects", "Bidsprinkhanen en wandelende takken", "Mantis e insectos palo", "螳螂与竹节虫"), {"orders": {"Mantodea", "Phasmida", "Phasmatodea"}}),
        ("cockroaches-termites", L("Cockroaches & termites", "Kakkerlakken en termieten", "Cucarachas y termitas", "蟑螂与白蚁"), {"orders": {"Blattodea", "Isoptera"}}),
        ("other-insects", L("Other insects", "Overige insecten", "Otros insectos", "其他昆虫"), {}),
    ],
    "arachnids": [
        ("spiders", L("Spiders & tarantulas", "Spinnen en vogelspinnen", "Arañas y tarántulas", "蜘蛛与捕鸟蛛"), {"orders": {"Araneae"}}),
        ("scorpions", L("Scorpions", "Schorpioenen", "Escorpiones", "蝎子"), {"orders": {"Scorpiones"}}),
        ("harvestmen", L("Harvestmen", "Hooiwagens", "Opiliones", "盲蛛"), {"orders": {"Opiliones"}}),
        ("ticks-mites", L("Ticks & mites", "Teken en mijten", "Garrapatas y ácaros", "蜱与螨"), {"orders": {"Ixodida", "Trombidiformes", "Sarcoptiformes", "Mesostigmata", "Holothyrida", "Opilioacarida"}}),
        ("other-arachnids", L("Whip spiders & other arachnids", "Zweepspinnen en andere spinachtigen", "Amblipígidos y otros arácnidos", "鞭蛛及其他蛛形纲动物"), {}),
    ],
    "crustaceans": [
        ("crabs", L("Crabs", "Krabben", "Cangrejos", "蟹"), {"orders": {"Decapoda"}, "infra": "crab"}),
        ("shrimps-lobsters", L("Shrimps, prawns & lobsters", "Garnalen en kreeften", "Camarones, langostinos y langostas", "虾与龙虾"), {"orders": {"Decapoda"}}),
        ("other-crustaceans", L("Other crustaceans", "Overige kreeftachtigen", "Otros crustáceos", "其他甲壳动物"), {}),
    ],
    "molluscs": [
        ("snails-slugs", L("Snails & slugs", "Slakken", "Caracoles y babosas", "螺与蛞蝓"), {"classes": {"Gastropoda"}}),
        ("clams-mussels", L("Clams, mussels & oysters", "Schelpen, mosselen en oesters", "Almejas, mejillones y ostras", "蛤、贻贝与牡蛎"), {"classes": {"Bivalvia"}}),
        ("squid-octopus", L("Squid & octopus", "Inktvissen en octopussen", "Calamares y pulpos", "鱿鱼与章鱼"), {"classes": {"Cephalopoda"}}),
        ("other-molluscs", L("Other molluscs", "Overige weekdieren", "Otros moluscos", "其他软体动物"), {}),
    ],
    "other-animals": [
        ("centipedes-millipedes", L("Centipedes & millipedes", "Duizendpoten en miljoenpoten", "Ciempiés y milpiés", "蜈蚣与马陆"), {"classes": {"Chilopoda", "Diplopoda", "Symphyla", "Pauropoda"}}),
        ("worms", L("Worms & leeches", "Wormen en bloedzuigers", "Gusanos y sanguijuelas", "蠕虫与蛭"), {"phyla": {"Annelida", "Nematoda", "Platyhelminthes", "Nemertea", "Sipuncula", "Acanthocephala", "Nematomorpha"}}),
        ("corals-jellyfish", L("Corals, anemones & jellyfish", "Koralen, zeeanemonen en kwallen", "Corales, anémonas y medusas", "珊瑚、海葵与水母"), {"phyla": {"Cnidaria", "Ctenophora"}}),
        ("sea-stars-urchins", L("Sea stars, urchins & sea cucumbers", "Zeesterren, zee-egels en zeekomkommers", "Estrellas, erizos y pepinos de mar", "海星、海胆与海参"), {"phyla": {"Echinodermata"}}),
        ("sponges", L("Sponges", "Sponzen", "Esponjas", "海绵"), {"phyla": {"Porifera"}}),
        ("other-invertebrates", L("Other small animals", "Overige kleine dieren", "Otros animales pequeños", "其他小型动物"), {}),
    ],
    "flowering-plants": [],   # filled below: one subgroup per major family
    "orchids": [("orchids-all", L("Orchids", "Orchideeën", "Orquídeas", "兰花"), {})],
    "palms": [("palms-all", L("Palms", "Palmen", "Palmeras", "棕榈"), {})],
    "ferns": [
        ("ferns-all", L("Ferns", "Varens", "Helechos", "蕨类"), {"classes": {"Polypodiopsida"}}),
        ("clubmosses", L("Clubmosses & spikemosses", "Wolfsklauwen en moswolfsklauwen", "Licopodios y selaginelas", "石松与卷柏"), {}),
    ],
    "mosses": [
        ("mosses-all", L("Mosses", "Mossen", "Musgos", "藓类"), {"phyla": {"Bryophyta"}}),
        ("liverworts-hornworts", L("Liverworts & hornworts", "Levermossen en hauwmossen", "Hepáticas y antoceros", "苔类与角苔"), {}),
    ],
    "other-plants": [
        ("conifers-cycads", L("Conifers, cycads & Gnetum", "Naaldbomen, palmvarens en Gnetum", "Coníferas, cícadas y Gnetum", "针叶树、苏铁与买麻藤"), {"phyla": {"Tracheophyta"}}),
        ("algae", L("Green & red algae", "Groen- en roodwieren", "Algas verdes y rojas", "绿藻与红藻"), {}),
    ],
    "fungi": [
        ("mushrooms", L("Mushrooms & bracket fungi", "Paddenstoelen en houtzwammen", "Setas y hongos de repisa", "蘑菇与多孔菌"), {"classes": {"Agaricomycetes", "Tremellomycetes", "Dacrymycetes"}}),
        ("lichens", L("Lichens", "Korstmossen", "Líquenes", "地衣"), {"classes": {"Lecanoromycetes", "Arthoniomycetes", "Lichinomycetes", "Candelariomycetes"}}),
        ("other-fungi", L("Cup fungi, moulds & other fungi", "Bekerzwammen, schimmels en overige", "Hongos de copa, mohos y otros", "盘菌、霉菌及其他真菌"), {}),
    ],
}

# Flowering plants: one subgroup per well-known family, the rest in "other".
# (key, family, en, nl, es, zh)
PLANT_FAMILIES = [
    ("legumes", "Fabaceae", "Legumes: pea and bean family", "Vlinderbloemigen (peulvruchtenfamilie)", "Leguminosas", "豆科"),
    ("coffee-family", "Rubiaceae", "Coffee family", "Sterbladigen (koffiefamilie)", "Rubiáceas (familia del café)", "茜草科（咖啡科）"),
    ("melastomes", "Melastomataceae", "Melastomes", "Melastoma-familie", "Melastomatáceas", "野牡丹科"),
    ("grasses", "Poaceae", "Grasses & bamboos", "Grassen en bamboe", "Gramíneas y bambúes", "禾本科（禾草与竹）"),
    ("sedges", "Cyperaceae", "Sedges", "Cypergrassen", "Ciperáceas", "莎草科"),
    ("bromeliads", "Bromeliaceae", "Bromeliads & pineapple", "Bromelia's en ananas", "Bromelias y piña", "凤梨科"),
    ("aroids", "Araceae", "Aroids: philodendrons & tayer", "Aronskelken: philodendrons en tayer", "Aráceas: filodendros y malanga", "天南星科"),
    ("myrtles", "Myrtaceae", "Myrtle family: guava & Suriname cherry", "Mirtefamilie: guave en Surinaamse kers", "Mirtáceas: guayaba y pitanga", "桃金娘科"),
    ("spurges", "Euphorbiaceae", "Spurge family: cassava & rubber", "Wolfsmelkfamilie: cassave en rubber", "Euforbiáceas: yuca y caucho", "大戟科"),
    ("mallows", "Malvaceae", "Mallow family: kapok, cacao & okra", "Kaasjeskruidfamilie: kankantrie, cacao en oker", "Malváceas: ceiba, cacao y okra", "锦葵科"),
    ("custard-apples", "Annonaceae", "Custard-apple family: soursop", "Annonafamilie: zuurzak", "Anonáceas: guanábana", "番荔枝科"),
    ("laurels", "Lauraceae", "Laurel family: avocado & wana", "Laurierfamilie: avocado en wana", "Lauráceas: aguacate", "樟科"),
    ("sapotes", "Sapotaceae", "Sapote family: balata & star apple", "Sapotefamilie: bolletrie en sterappel", "Sapotáceas: balatá y caimito", "山榄科"),
    ("cocoplums", "Chrysobalanaceae", "Cocoplum family", "Kokospruimfamilie", "Crisobalanáceas", "金壳果科"),
    ("brazil-nut-family", "Lecythidaceae", "Brazil nut family: cannonball tree", "Paranotenfamilie: kanonskogelboom", "Lecitidáceas: castaña de Brasil", "玉蕊科（巴西栗科）"),
    ("peppers", "Piperaceae", "Pepper family: Piper & Peperomia", "Peperfamilie: Piper en Peperomia", "Piperáceas", "胡椒科"),
    ("daisies", "Asteraceae", "Daisy family", "Composietenfamilie", "Compuestas", "菊科"),
    ("dogbanes", "Apocynaceae", "Dogbane family", "Maagdenpalmfamilie", "Apocináceas", "夹竹桃科"),
    ("trumpet-trees", "Bignoniaceae", "Trumpet-tree family: groenhart & calabash", "Trompetboomfamilie: groenhart en kalebas", "Bignoniáceas", "紫葳科"),
    ("figs-mulberries", "Moraceae", "Fig & mulberry family", "Moerbeifamilie: vijgen en broodvrucht", "Moráceas: higueras", "桑科"),
    ("nightshades", "Solanaceae", "Nightshade family: peppers & antroewa", "Nachtschadefamilie: pepers en antroewa", "Solanáceas: ajíes y berenjenas", "茄科"),
    ("gingers-heliconias", "Zingiberales", "Gingers, heliconias & bananas", "Gemberachtigen, heliconia's en bananen", "Jengibres, heliconias y plátanos", "姜目：姜、蝎尾蕉与香蕉"),
    ("passionflowers", "Passifloraceae", "Passionflowers & markoesa", "Passiebloemen en markoesa", "Pasifloras y maracuyá", "西番莲科"),
    ("gesneriads", "Gesneriaceae", "Gesneriads", "Gesneriafamilie", "Gesneriáceas", "苦苣苔科"),
    ("acanthus-family", "Acanthaceae", "Acanthus family", "Acanthusfamilie", "Acantáceas", "爵床科"),
    ("bladderworts", "Lentibulariaceae", "Bladderworts", "Blaasjeskruiden", "Lentibulariáceas", "狸藻科"),
    ("morning-glories", "Convolvulaceae", "Morning glories & sweet potato", "Windefamilie: bataat", "Convolvuláceas: batata", "旋花科"),
    ("cucurbits", "Cucurbitaceae", "Gourd family: sopropo & pumpkin", "Komkommerfamilie: sopropo en pompoen", "Cucurbitáceas", "葫芦科"),
    ("water-lilies", "Nymphaeaceae", "Water lilies", "Waterlelies", "Nenúfares", "睡莲科"),
]
SUBGROUPS["flowering-plants"] = (
    [(k, L(en, nl, es, zh), {"orders": {fam}} if fam.endswith("ales") else {"families": {fam}})
     for k, fam, en, nl, es, zh in PLANT_FAMILIES]
    + [("other-flowering-plants", L("All other plant families", "Alle andere plantenfamilies", "Todas las demás familias", "其他所有植物科"), {})]
)

# ── curated collections (cross-cutting, hand-picked) ─────────────────────────
COLLECTIONS = [
    ("trees", L("Trees & timber", "Bomen en houtsoorten", "Árboles y maderas", "树木与木材"),
     L("Kankantrie, groenhart, basralocus, bolletrie and the other trees Surinamers know by name.",
       "Kankantrie, groenhart, basralocus, bolletrie en de andere bomen die Surinamers bij naam kennen.",
       "Ceiba, groenhart, basralocus, balatá y los demás árboles que los surinameses conocen por su nombre.",
       "木棉、绿心木、巴斯拉洛库斯、巴拉塔树，以及苏里南人耳熟能详的其他树木。")),
    ("fruits-crops", L("Fruits, vegetables & crops", "Fruit, groenten en gewassen", "Frutas, verduras y cultivos", "水果、蔬菜与作物"),
     L("Mango, knippa, sopropo, cassave, tayer: the plants on Surinamese plates and in market stalls.",
       "Manja, knippa, sopropo, cassave, tayer: de planten op het Surinaamse bord en op de markt.",
       "Mango, mamoncillo, cundeamor, yuca, malanga: las plantas del plato surinamés y del mercado.",
       "芒果、蜜果、苦瓜、木薯、芋头：苏里南餐桌和市场上的植物。")),
    ("sranan-names", L("Known by a Sranan name", "Met een Sranantongo-naam", "Con nombre en sranan", "有苏里南汤加语名称的物种"),
     L("Animals and plants that have their own name in Sranan Tongo, linked to our dictionary.",
       "Dieren en planten met een eigen naam in het Sranantongo, gekoppeld aan ons woordenboek.",
       "Animales y plantas con nombre propio en sranan tongo, enlazados a nuestro diccionario.",
       "在苏里南汤加语中有专属名称的动植物，并链接到我们的词典。")),
    ("endemic", L("Found only in Suriname", "Alleen in Suriname", "Solo en Surinam", "苏里南特有物种"),
     L("Species and subspecies known from Suriname and nowhere else, after the National Zoological Collection of Suriname.",
       "Soorten en ondersoorten die alleen uit Suriname bekend zijn, volgens de Nationale Zoölogische Collectie Suriname.",
       "Especies y subespecies conocidas solo de Surinam, según la Colección Zoológica Nacional de Surinam.",
       "根据苏里南国家动物收藏馆的资料，仅在苏里南有记录的物种和亚种。")),
    ("threatened", L("Threatened species", "Bedreigde soorten", "Especies amenazadas", "受威胁物种"),
     L("Species rated Vulnerable, Endangered or Critically Endangered on the IUCN Red List.",
       "Soorten die op de Rode Lijst van de IUCN als kwetsbaar, bedreigd of ernstig bedreigd staan.",
       "Especies catalogadas como vulnerables, en peligro o en peligro crítico en la Lista Roja de la UICN.",
       "在世界自然保护联盟红色名录中被列为易危、濒危或极危的物种。")),
    ("introduced", L("Introduced & invasive", "Uitheems en invasief", "Introducidas e invasoras", "外来与入侵物种"),
     L("Species brought to Suriname by people, on purpose or by accident.",
       "Soorten die door mensen naar Suriname zijn gebracht, bewust of per ongeluk.",
       "Especies traídas a Surinam por las personas, a propósito o por accidente.",
       "被人类有意或无意带入苏里南的物种。")),
]
COLLECTION_KEYS = [c[0] for c in COLLECTIONS]

TREES = [
    "Ceiba pentandra", "Pterocarpus officinalis", "Manilkara bidentata", "Carapa guianensis",
    "Dicorynia guianensis", "Chlorocardium rodiei", "Handroanthus serratifolius", "Tabebuia serratifolia",
    "Peltogyne venosa", "Peltogyne paniculata", "Vouacapoua americana", "Brosimum guianense",
    "Goupia glabra", "Sextonia rubra", "Hura crepitans", "Cedrela odorata", "Virola surinamensis",
    "Eperua falcata", "Dipteryx odorata", "Hymenaea courbaril", "Bertholletia excelsa", "Mora excelsa",
    "Ruizterania albiflora", "Simarouba amara", "Couroupita guianensis", "Platonia insignis",
    "Symphonia globulifera", "Parkia pendula", "Samanea saman", "Delonix regia", "Terminalia catappa",
    "Avicennia germinans", "Rhizophora mangle", "Laguncularia racemosa", "Spondias mombin",
    "Mangifera indica", "Tamarindus indica", "Licania heteromorpha", "Swietenia macrophylla",
    "Swietenia mahagoni", "Ocotea rodiei", "Bagassa guianensis", "Qualea rosea", "Vochysia tomentosa",
    "Lecythis zabucajo", "Eschweilera subglandulosa", "Couratari guianensis", "Andira inermis",
    "Copaifera guianensis", "Inga edulis", "Cecropia peltata", "Cecropia obtusa", "Ficus maxima",
    "Tabebuia rosea", "Handroanthus impetiginosus", "Jacaranda copaia", "Erythrina fusca",
    "Pachira aquatica", "Crescentia cujete", "Genipa americana", "Hevea guianensis",
]
FRUITS_CROPS = [
    "Mangifera indica", "Cocos nucifera", "Musa paradisiaca", "Musa acuminata", "Manihot esculenta",
    "Xanthosoma sagittifolium", "Colocasia esculenta", "Dioscorea alata", "Dioscorea trifida", "Ipomoea batatas",
    "Oryza sativa", "Zea mays", "Saccharum officinarum", "Theobroma cacao", "Coffea arabica", "Coffea liberica",
    "Citrus sinensis", "Citrus aurantiifolia", "Citrus limon", "Citrus maxima", "Citrus reticulata", "Citrus aurantium",
    "Annona muricata", "Annona squamosa", "Annona reticulata", "Psidium guajava", "Carica papaya", "Ananas comosus",
    "Passiflora edulis", "Passiflora laurifolia", "Passiflora quadrangularis", "Averrhoa bilimbi", "Averrhoa carambola",
    "Spondias mombin", "Spondias dulcis", "Syzygium malaccense", "Syzygium cumini", "Syzygium jambos", "Eugenia uniflora",
    "Malpighia emarginata", "Melicoccus bijugatus", "Chrysophyllum cainito", "Manilkara zapota", "Pouteria caimito",
    "Persea americana", "Artocarpus altilis", "Artocarpus heterophyllus", "Tamarindus indica", "Anacardium occidentale",
    "Bertholletia excelsa", "Euterpe oleracea", "Astrocaryum vulgare", "Attalea maripa", "Oenocarpus bacaba",
    "Bactris gasipaes", "Mauritia flexuosa", "Abelmoschus esculentus", "Momordica charantia", "Solanum macrocarpon",
    "Solanum melongena", "Solanum lycopersicum", "Capsicum chinense", "Capsicum frutescens", "Capsicum annuum",
    "Cucurbita moschata", "Lagenaria siceraria", "Luffa aegyptiaca", "Citrullus lanatus", "Cucumis sativus",
    "Vigna unguiculata", "Cajanus cajan", "Phaseolus vulgaris", "Arachis hypogaea", "Sesamum indicum", "Bixa orellana",
    "Zingiber officinale", "Curcuma longa", "Cymbopogon citratus", "Ipomoea aquatica", "Amaranthus dubius",
    "Amaranthus tricolor", "Brassica juncea", "Brassica rapa", "Morinda citrifolia", "Moringa oleifera",
    "Platonia insignis", "Inga edulis", "Genipa americana", "Crescentia cujete", "Eryngium foetidum",
    "Ocimum basilicum", "Ocimum campechianum", "Allium cepa", "Allium sativum", "Allium fistulosum",
    "Coriandrum sativum", "Apium graveolens", "Petroselinum crispum", "Mentha spicata", "Piper nigrum",
    "Myristica fragrans", "Syzygium aromaticum", "Cinnamomum verum", "Vanilla planifolia", "Punica granatum",
    "Nicotiana tabacum", "Gossypium barbadense", "Ricinus communis", "Hylocereus undatus", "Selenicereus undatus",
    "Opuntia cochenillifera", "Sechium edule", "Pachyrhizus erosus", "Elaeis guineensis",
]

# ── IUCN Red List categories (Wikidata item -> code) ─────────────────────────
IUCN_WD = {"Q211005": "LC", "Q719675": "NT", "Q278113": "VU", "Q96377276": "EN", "Q11394": "EN", "Q219127": "CR",
           "Q239509": "EW", "Q237350": "EX", "Q3245245": "DD"}
IUCN_INAT = {0: "NE", 5: "DD", 10: "LC", 20: "NT", 30: "VU", 40: "EN", 50: "CR", 60: "EW", 70: "EX"}
IUCN = {
    "LC": L("Least Concern", "Niet bedreigd", "Preocupación menor", "无危"),
    "NT": L("Near Threatened", "Gevoelig", "Casi amenazada", "近危"),
    "VU": L("Vulnerable", "Kwetsbaar", "Vulnerable", "易危"),
    "EN": L("Endangered", "Bedreigd", "En peligro", "濒危"),
    "CR": L("Critically Endangered", "Ernstig bedreigd", "En peligro crítico", "极危"),
    "EW": L("Extinct in the Wild", "Uitgestorven in het wild", "Extinta en estado silvestre", "野外灭绝"),
    "EX": L("Extinct", "Uitgestorven", "Extinta", "灭绝"),
    "DD": L("Data Deficient", "Onvoldoende gegevens", "Datos insuficientes", "数据缺乏"),
}

# Surinamese districts (GBIF GADM ids -> names). Names stay as they are in
# every language; only Paramaribo has a fixed Chinese form (glossary).
DISTRICTS = {"SUR.1_1": "Brokopondo", "SUR.2_1": "Commewijne", "SUR.3_1": "Coronie",
             "SUR.4_1": "Marowijne", "SUR.5_1": "Nickerie", "SUR.6_1": "Para",
             "SUR.7_1": "Paramaribo", "SUR.8_1": "Saramacca", "SUR.9_1": "Sipaliwini",
             "SUR.10_1": "Wanica"}

LOCAL_LANG = {
    "srn": L("Sranan Tongo", "Sranantongo", "Sranan tongo", "苏里南汤加语"),
    "nl-SR": L("Surinamese Dutch", "Surinaams-Nederlands", "Neerlandés de Surinam", "苏里南荷兰语"),
}


def match_rule(rule, t):
    """t: dict with kingdom/phylum/class/order/family. Empty rule = catch-all."""
    if not rule:
        return True
    if "classes" in rule and t.get("class") in rule["classes"]:
        return True
    if "orders" in rule and t.get("order") in rule["orders"]:
        if rule.get("infra") == "crab":
            return t.get("crab", False)
        return True
    if "families" in rule and t.get("family") in rule["families"]:
        return True
    if "phyla" in rule and t.get("phylum") in rule["phyla"]:
        return True
    return False


# Decapod families that are crabs (true crabs, hermit crabs, mud lobsters excluded)
CRAB_FAMILIES = {"Grapsidae", "Sesarmidae", "Ocypodidae", "Portunidae", "Gecarcinidae", "Trichodactylidae",
                 "Panopeidae", "Menippidae", "Xanthidae", "Pseudothelphusidae", "Calappidae", "Leucosiidae",
                 "Majidae", "Epialtidae", "Inachidae", "Mithracidae", "Pinnotheridae", "Ucididae", "Varunidae",
                 "Plagusiidae", "Diogenidae", "Paguridae", "Porcellanidae", "Dromiidae", "Raninidae",
                 "Aethridae", "Hepatidae", "Parthenopidae", "Goneplacidae", "Pilumnidae", "Eriphiidae",
                 "Glyptograpsidae", "Coenobitidae", "Albuneidae", "Hippidae", "Dorippidae", "Ethusidae",
                 "Homolidae", "Cancridae", "Carpiliidae", "Pseudorhombilidae", "Euryplacidae", "Mictyridae",
                 "Dotillidae", "Macrophthalmidae", "Gecarcinucidae", "Potamidae", "Geryonidae", "Pinnotheridae"}

REPTILE_CLASSES = {"Squamata", "Testudines", "Crocodylia", "Reptilia", "Sphenodontia"}
NONFISH_CHORDATES = {"Mammalia", "Aves", "Amphibia", "Ascidiacea", "Thaliacea", "Appendicularia",
                     "Leptocardii"} | REPTILE_CLASSES
CRUSTACEAN_CLASSES = {"Malacostraca", "Copepoda", "Ostracoda", "Branchiopoda", "Thecostraca",
                      "Hexanauplia", "Maxillopoda", "Ichthyostraca", "Cephalocarida", "Remipedia",
                      "Branchiura", "Mystacocarida"}
BRYO_PHYLA = {"Bryophyta", "Marchantiophyta", "Anthocerotophyta"}
FERN_CLASSES = {"Polypodiopsida", "Lycopodiopsida"}


def classify(t):
    """Return (group, subgroup) for a GBIF classification dict, or (None, None)."""
    k, ph, cl = t.get("kingdom"), t.get("phylum"), t.get("class")
    g = None
    if k == "Animalia":
        if ph == "Chordata":
            if cl == "Mammalia":
                g = "mammals"
            elif cl == "Aves":
                g = "birds"
            elif cl in REPTILE_CLASSES:
                g = "reptiles"
            elif cl == "Amphibia":
                g = "amphibians"
            elif cl in NONFISH_CHORDATES:
                g = "other-animals"
            else:
                g = "fish"
        elif ph == "Arthropoda":
            if cl == "Insecta":
                g = "insects"
            elif cl == "Arachnida":
                g = "arachnids"
            elif cl in CRUSTACEAN_CLASSES:
                g = "crustaceans"
            else:
                g = "other-animals"
        elif ph == "Mollusca":
            g = "molluscs"
        else:
            g = "other-animals"
    elif k == "Plantae":
        if t.get("family") == "Orchidaceae":
            g = "orchids"
        elif t.get("family") == "Arecaceae":
            g = "palms"
        elif cl in ("Magnoliopsida", "Liliopsida"):
            g = "flowering-plants"
        elif cl in FERN_CLASSES:
            g = "ferns"
        elif ph in BRYO_PHYLA:
            g = "mosses"
        else:
            g = "other-plants"
    elif k == "Fungi":
        g = "fungi"
    if g is None:
        return None, None
    tt = dict(t)
    tt["crab"] = t.get("family") in CRAB_FAMILIES
    for key, _lab, rule in SUBGROUPS[g]:
        if match_rule(rule, tt):
            return g, key
    return g, SUBGROUPS[g][-1][0]


def subgroup_label(group, sub):
    for k, lab, _r in SUBGROUPS[group]:
        if k == sub:
            return lab
    return GROUP[group]["label"]
