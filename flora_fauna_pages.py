"""Flora & Fauna of Suriname (added Oct 2026): every animal, plant and fungus
recorded in Suriname, in one place.

Called from generate.py like oilgas_pages.py / business_pages.py. Pure local
build: reads data/flora_fauna/*.json (written offline by
scripts/flora_fauna_data.py, which is the only part that touches the network)
and returns {path: html} plus the static assets.

Design (see flora-fauna-spec in the project folder):
  * Own slim shell (like NParks Flora & Fauna Web): small header with section
    search and language switch, a chip bar of groups, slim footer. No site mega
    menu: it keeps ~4,000 species pages small enough for GitHub Pages and keeps
    the section focused. The wordmark links home; a menu button opens the main
    site sections.
  * Two layers: every species is on the checklist (subgroup pages + search);
    species with enough information (a real Wikipedia description plus a photo
    or a common name) also get their own profile page.
  * Languages: every visible string carries its EN/NL/ES/ZH/FR/PT value in
    data-l10n / data-l10n-group markers. build_i18n.apply_l10n() picks the right
    one per tree and strips the markers, so nothing here goes through machine
    translation and translations.json is not touched. Chinese is hand-written.
  * All internal links are relative (the NL/ES/ZH/FR/PT trees are copies of the
    English pages). Shared assets live at absolute /flora-fauna/assets/.
  * Informational, not commercial: no listing/tour promotion on these pages.
"""
import datetime as _dt
import hashlib as _hl
import html as _html
import json as _json
import posixpath as _pp
from pathlib import Path as _Path

from flora_fauna_taxa import (GROUPS, GROUP, GROUP_KEYS, REALMS, SUBGROUPS, COLLECTIONS,
                              COLLECTION_KEYS, IUCN, DISTRICTS, LOCAL_LANG, L, subgroup_label)

_ROOT = _Path(__file__).resolve().parent
_DATA = _ROOT / "data" / "flora_fauna"
SITE_URL = "https://exploresuriname.com"
BASE = "flora-fauna"
ASSETS = "/flora-fauna/assets/"
LANGS = ("en", "nl", "es", "zh", "fr", "pt")
# Languages that have species names / Wikipedia texts in the data (names table rows).
# French and Portuguese pages show these four names (there is no fr/pt name data).
NAME_LANGS = ("en", "nl", "es", "zh")
LANG_LABEL = {"en": "EN", "nl": "NL", "es": "ES", "zh": "中文", "fr": "FR", "pt": "PT"}
LANG_NAME = {"en": L("English", "Engels", "Inglés", "英语"),
             "nl": L("Dutch", "Nederlands", "Neerlandés", "荷兰语"),
             "es": L("Spanish", "Spaans", "Español", "西班牙语"),
             "zh": L("Chinese", "Chinees", "Chino", "中文")}
_LANG_ATTR = {"zh": ' lang="zh-Hans"', "fr": ' lang="fr"', "pt": ' lang="pt-BR"'}


def _la(lg):
    """lang attribute for an element in another language than its page."""
    return _LANG_ATTR.get(lg, "")


# ─────────────────────────────────────────────────────────────────────────────
# Fixed interface text (hand-written; FR/PT come from flora_fauna_frpt.py via L())
# ─────────────────────────────────────────────────────────────────────────────
U = {
    "section": L("Flora & Fauna", "Flora en fauna", "Flora y fauna", "动植物"),
    "section_long": L("Flora & Fauna of Suriname", "Flora en fauna van Suriname", "Flora y fauna de Surinam", "苏里南动植物"),
    "home": L("Home", "Home", "Inicio", "首页"),
    "search_ph": L("Search any animal or plant, in any language", "Zoek een dier of plant, in elke taal",
                   "Busca un animal o una planta, en cualquier idioma", "搜索任何动物或植物（支持多种语言）"),
    "search_btn": L("Search species", "Soorten zoeken", "Buscar especies", "搜索物种"),
    "search_hint": L("Try jaguar, kankantri, pakira or Ceiba pentandra.", "Probeer jaguar, kankantrie, pakira of Ceiba pentandra.",
                     "Prueba jaguar, kankantri, pakira o Ceiba pentandra.", "试试 jaguar、kankantri、pakira 或 Ceiba pentandra。"),
    "no_results": L("No species match your search.", "Geen soorten gevonden.", "Ninguna especie coincide con tu búsqueda.", "没有找到匹配的物种。"),
    "loading": L("Loading…", "Laden…", "Cargando…", "加载中…"),
    "close": L("Close", "Sluiten", "Cerrar", "关闭"),
    "menu": L("Menu", "Menu", "Menú", "菜单"),
    "all_groups": L("All groups", "Alle groepen", "Todos los grupos", "全部类群"),
    "hub_kicker": L("Learn", "Leren", "Aprender", "了解"),
    "hub_lead": L("Every animal, plant and fungus recorded in Suriname, with its name in English, Dutch, Spanish, Chinese, Sranan Tongo and Latin.",
                  "Elk dier, elke plant en elke schimmel die in Suriname is waargenomen, met de naam in het Engels, Nederlands, Spaans, Chinees, Sranantongo en Latijn.",
                  "Cada animal, planta y hongo registrado en Surinam, con su nombre en inglés, neerlandés, español, chino, sranan tongo y latín.",
                  "收录在苏里南有记录的每一种动物、植物和真菌，附英语、荷兰语、西班牙语、中文、苏里南汤加语和拉丁学名。"),
    "stat_species": L("species recorded", "soorten waargenomen", "especies registradas", "个有记录的物种"),
    "stat_profiles": L("species profiles", "soortprofielen", "fichas de especies", "个物种简介"),
    "stat_sranan": L("Sranan names", "Sranantongo-namen", "nombres en sranan", "个苏里南汤加语名称"),
    "browse_animals": L("Animals", "Dieren", "Animales", "动物"),
    "browse_plants": L("Plants & fungi", "Planten en schimmels", "Plantas y hongos", "植物与真菌"),
    "collections": L("Collections", "Collecties", "Colecciones", "专题"),
    "most_seen": L("Most observed in Suriname", "Het vaakst waargenomen in Suriname", "Las más observadas en Surinam", "苏里南最常见的物种"),
    "most_seen_sub": L("Ranked by observations shared on iNaturalist from Suriname.",
                       "Gerangschikt op waarnemingen uit Suriname op iNaturalist.",
                       "Según las observaciones de Surinam compartidas en iNaturalist.",
                       "按 iNaturalist 上来自苏里南的观察记录数量排序。"),
    "sranan_strip": L("Known by a Sranan name", "Met een Sranantongo-naam", "Con nombre en sranan", "有苏里南汤加语名称的物种"),
    "see_all": L("See all", "Bekijk alles", "Ver todo", "查看全部"),
    "species_n": L("species", "soorten", "especies", "个物种"),
    "profiles_n": L("profiles", "profielen", "fichas", "个简介"),
    "on_checklist": L("Also on the checklist", "Ook op de soortenlijst", "También en la lista", "名录中的其他物种"),
    "on_checklist_sub": L("Recorded in Suriname, but there is not enough reliable information yet for a full profile.",
                          "Waargenomen in Suriname, maar er is nog niet genoeg betrouwbare informatie voor een volledig profiel.",
                          "Registradas en Surinam, pero aún no hay suficiente información fiable para una ficha completa.",
                          "在苏里南有记录，但目前还没有足够可靠的资料来撰写完整简介。"),
    "filter_ph": L("Filter this list", "Filter deze lijst", "Filtrar esta lista", "筛选此列表"),
    "sort_seen": L("Most observed", "Meest waargenomen", "Más observadas", "最常见"),
    "sort_az": L("Name A–Z", "Naam A–Z", "Nombre A–Z", "名称 A–Z"),
    "sort_latin": L("Scientific name", "Wetenschappelijke naam", "Nombre científico", "学名"),
    "subgroups": L("Groups", "Groepen", "Grupos", "分类"),
    "records": L("Records", "Waarnemingen", "Registros", "记录"),
    "family": L("Family", "Familie", "Familia", "科"),
    "names": L("Names", "Namen", "Nombres", "名称"),
    "scientific": L("Scientific name", "Wetenschappelijke naam", "Nombre científico", "学名"),
    "synonyms": L("Also recorded as", "Ook geregistreerd als", "También registrado como", "也记录为"),
    "local_names": L("Local names", "Lokale namen", "Nombres locales", "本地名称"),
    "group_term": L("general name for the group", "algemene naam voor de groep", "nombre general del grupo", "该类群的统称"),
    "about": L("About", "Over", "Sobre", "简介"),
    "about_species": L("About this species", "Over deze soort", "Sobre esta especie", "物种简介"),
    "read_wiki": L("Read more on Wikipedia", "Lees verder op Wikipedia", "Seguir leyendo en Wikipedia", "在维基百科上阅读更多"),
    "wiki_lic": L("Text: Wikipedia, CC BY-SA 4.0", "Tekst: Wikipedia, CC BY-SA 4.0", "Texto: Wikipedia, CC BY-SA 4.0", "文字：维基百科，CC BY-SA 4.0"),
    "in_english": L("(in English)", "(in het Engels)", "(en inglés)", "（英文）"),
    "in_sr": L("In Suriname", "In Suriname", "En Surinam", "在苏里南"),
    "gbif_records": L("Records in Suriname", "Waarnemingen in Suriname", "Registros en Surinam", "苏里南记录数"),
    "inat_obs": L("iNaturalist observations", "Waarnemingen op iNaturalist", "Observaciones en iNaturalist", "iNaturalist 观察记录"),
    "first_record": L("First record", "Eerste waarneming", "Primer registro", "最早记录"),
    "last_record": L("Latest record", "Laatste waarneming", "Último registro", "最近记录"),
    "where": L("Where it has been recorded", "Waar de soort is waargenomen", "Dónde se ha registrado", "记录地点"),
    "where_note": L("Districts with at least one record that has coordinates. Shaded districts have records.",
                    "Districten met minstens één waarneming met coördinaten. Gekleurde districten hebben waarnemingen.",
                    "Distritos con al menos un registro con coordenadas. Los distritos coloreados tienen registros.",
                    "至少有一条带坐标记录的区。着色的区有记录。"),
    "when": L("Records by month", "Waarnemingen per maand", "Registros por mes", "每月记录"),
    "when_note": L("All years combined.", "Alle jaren samen.", "Todos los años juntos.", "所有年份合计。"),
    "status": L("Status", "Status", "Estado", "状态"),
    "iucn": L("IUCN Red List", "Rode Lijst IUCN", "Lista Roja de la UICN", "IUCN 红色名录"),
    "endemic": L("Endemic to Suriname", "Endemisch in Suriname", "Endémica de Surinam", "苏里南特有"),
    "introduced": L("Introduced by people", "Door mensen geïntroduceerd", "Introducida por el ser humano", "人为引入"),
    "threatened_sr": L("On Suriname's list of threatened fauna", "Op de Surinaamse lijst van bedreigde fauna",
                       "En la lista de fauna amenazada de Surinam", "列入苏里南受威胁动物名录"),
    "native": L("Native", "Inheems", "Nativa", "本地原生"),
    "classification": L("Classification", "Indeling", "Clasificación", "分类"),
    "kingdom": L("Kingdom", "Rijk", "Reino", "界"),
    "phylum": L("Phylum", "Stam", "Filo", "门"),
    "class": L("Class", "Klasse", "Clase", "纲"),
    "order": L("Order", "Orde", "Orden", "目"),
    "genus": L("Genus", "Geslacht", "Género", "属"),
    "related": L("Related species in Suriname", "Verwante soorten in Suriname", "Especies emparentadas en Surinam", "苏里南的近缘物种"),
    "sources": L("Sources & credits", "Bronnen en verantwoording", "Fuentes y créditos", "资料来源与署名"),
    "photo": L("Photo", "Foto", "Foto", "照片"),
    "no_photo": L("No photo yet", "Nog geen foto", "Aún sin foto", "暂无照片"),
    "dict_link": L("in our Sranan Tongo dictionary", "in ons Sranantongo-woordenboek", "en nuestro diccionario de sranan tongo", "见我们的苏里南汤加语词典"),
    "src_gbif": L("Records: GBIF.org occurrence data for Suriname", "Waarnemingen: GBIF.org-gegevens voor Suriname",
                  "Registros: datos de GBIF.org para Surinam", "记录：GBIF.org 苏里南出现数据"),
    "src_inat": L("Observations and names: iNaturalist", "Waarnemingen en namen: iNaturalist", "Observaciones y nombres: iNaturalist", "观察记录与名称：iNaturalist"),
    "src_wd": L("Names in other languages: Wikidata", "Namen in andere talen: Wikidata", "Nombres en otros idiomas: Wikidata", "其他语言名称：维基数据"),
    "src_local": L("Sranan names: Explore Suriname Sranan Tongo dictionary", "Sranantongo-namen: woordenboek van Explore Suriname",
                   "Nombres en sranan: diccionario de Explore Suriname", "苏里南汤加语名称：Explore Suriname 苏里南汤加语词典"),
    "src_nzcs": L("Suriname status: National Zoological Collection of Suriname (NZCS) checklists",
                  "Status in Suriname: soortenlijsten van de Nationale Zoölogische Collectie Suriname (NZCS)",
                  "Estado en Surinam: listas de la Colección Zoológica Nacional de Surinam (NZCS)",
                  "苏里南状态：苏里南国家动物收藏馆（NZCS）名录"),
    "correction": L("Spotted a mistake or know another local name? Tell us.", "Een fout gezien of kent u nog een lokale naam? Laat het ons weten.",
                    "¿Has visto un error o conoces otro nombre local? Avísanos.", "发现错误或知道其他本地名称？请告诉我们。"),
    "updated": L("Data updated", "Gegevens bijgewerkt", "Datos actualizados", "数据更新于"),
    "about_page": L("About this guide", "Over deze gids", "Sobre esta guía", "关于本指南"),
    "about_lead": L("How we compile the Flora & Fauna of Suriname, where the information comes from and how you can help.",
                    "Hoe we de Flora en fauna van Suriname samenstellen, waar de informatie vandaan komt en hoe u kunt helpen.",
                    "Cómo elaboramos la Flora y fauna de Surinam, de dónde viene la información y cómo puedes ayudar.",
                    "我们如何编制《苏里南动植物》、资料来自哪里，以及您可以如何帮助我们。"),
    "footer_note": L("A free guide by Explore Suriname. Names, records and photos come from open biodiversity data; every source is credited on the page where it is used.",
                     "Een gratis gids van Explore Suriname. Namen, waarnemingen en foto's komen uit open biodiversiteitsdata; elke bron staat vermeld op de pagina waar die wordt gebruikt.",
                     "Una guía gratuita de Explore Suriname. Los nombres, registros y fotos provienen de datos abiertos de biodiversidad; cada fuente se cita en la página donde se usa.",
                     "Explore Suriname 提供的免费指南。名称、记录和照片均来自开放的生物多样性数据，每个来源都在使用它的页面上注明。"),
    "skip": L("Skip to content", "Naar de inhoud", "Ir al contenido", "跳到正文"),
    "back_site": L("Explore Suriname", "Explore Suriname", "Explore Suriname", "Explore Suriname"),
    "months": [L(*m) for m in (("Jan", "jan", "ene", "1月"), ("Feb", "feb", "feb", "2月"), ("Mar", "mrt", "mar", "3月"),
                                 ("Apr", "apr", "abr", "4月"), ("May", "mei", "may", "5月"), ("Jun", "jun", "jun", "6月"),
                                 ("Jul", "jul", "jul", "7月"), ("Aug", "aug", "ago", "8月"), ("Sep", "sep", "sep", "9月"),
                                 ("Oct", "okt", "oct", "10月"), ("Nov", "nov", "nov", "11月"), ("Dec", "dec", "dic", "12月"))],
}
from flora_fauna_frpt import MONTHS_FR as _MFR, MONTHS_PT as _MPT   # noqa: E402
for _i, _m in enumerate(U["months"]):
    _m["fr"], _m["pt"] = _MFR[_i], _MPT[_i]

# Languages that get their own static copy of each species page, only when the
# species has an official name in that language (Dutch only, ~1,600 pages; Spanish
# and Chinese copies were dropped in Oct 2026 to save repo space). For every other
# species/language pair the English page opens with ?lang=xx and localizes labels,
# name and description in the browser.
# Hub, group, subgroup, collection and about pages are always in all 6 languages.
# Size: ~14 KB a page. Set to () to fall back to English-only species pages.
STATIC_LANGS = ("nl",)

# main-site links for the menu (relative to site root)
SITE_LINKS = [
    ("", L("Home", "Home", "Inicio", "首页")),
    ("activities.html", L("Things to Do", "Wat te doen", "Qué hacer", "玩乐")),
    ("events.html", L("Events & Festivals", "Evenementen en festivals", "Eventos y festivales", "活动与节庆")),
    ("about-suriname", L("About Suriname", "Over Suriname", "Sobre Surinam", "关于苏里南")),
    ("suriname-history.html", L("History Timeline", "Geschiedenis", "Historia", "历史时间线")),
    ("sranan-tongo-dictionary.html", L("Sranan Dictionary", "Sranantongo-woordenboek", "Diccionario de sranan", "苏里南汤加语词典")),
    ("visitor-guide.html", L("Visitor Guide", "Reisgids", "Guía del visitante", "旅行指南")),
]


# ─────────────────────────────────────────────────────────────────────────────
# Small helpers
# ─────────────────────────────────────────────────────────────────────────────
def esc(s):
    return _html.escape(str(s if s is not None else ""), quote=True)


def _lj(d):
    """data-l10n payload: only the non-English values that differ from English."""
    en = d.get("en", "")
    out = {k: v for k, v in d.items() if k != "en" and v and v != en}
    return esc(_json.dumps(out, ensure_ascii=False, separators=(",", ":")))


_KEYS = {}   # id(label dict) -> key, for labels the browser can re-localize (?lang=)


def _register():
    for k, v in U.items():
        if isinstance(v, dict):
            _KEYS[id(v)] = "u." + k
    for i, m in enumerate(U["months"]):
        _KEYS[id(m)] = f"m.{i}"
    for k in GROUP_KEYS:
        _KEYS[id(GROUP[k]["label"])] = "g." + k
        for sk, lab, _r in SUBGROUPS[k]:
            _KEYS[id(lab)] = f"s.{k}/{sk}"
    for k, lab, _i in COLLECTIONS:
        _KEYS[id(lab)] = "c." + k
    for k, lab in IUCN.items():
        _KEYS[id(lab)] = "i." + k
    for k, lab in LOCAL_LANG.items():
        _KEYS[id(lab)] = "ll." + k
    for k, lab in LANG_NAME.items():
        _KEYS[id(lab)] = "ln." + k


def _all_labels():
    """Every registered label, for the browser (window.FF_I18N.k)."""
    objs = {}
    for k, v in U.items():
        if isinstance(v, dict):
            objs["u." + k] = v
    for i, m in enumerate(U["months"]):
        objs[f"m.{i}"] = m
    for k in GROUP_KEYS:
        objs["g." + k] = GROUP[k]["label"]
        for sk, lab, _r in SUBGROUPS[k]:
            objs[f"s.{k}/{sk}"] = lab
    for k, lab, _i in COLLECTIONS:
        objs["c." + k] = lab
    for k, lab in IUCN.items():
        objs["i." + k] = lab
    for k, lab in LOCAL_LANG.items():
        objs["ll." + k] = lab
    for k, lab in LANG_NAME.items():
        objs["ln." + k] = lab
    return objs


_register()


def tx(d, tag="span", cls="", extra=""):
    """A leaf element whose text is localized by build_i18n.apply_l10n
    (and, for registered labels, by the browser on ?lang= pages)."""
    c = f' class="{cls}"' if cls else ""
    if not isinstance(d, dict):
        return f'<{tag}{c}{extra} translate="no">{esc(d)}</{tag}>'
    k = _KEYS.get(id(d))
    kk = f' data-k="{k}"' if k else ""
    return f'<{tag}{c}{extra}{kk} translate="no" data-l10n="{_lj(d)}">{esc(d.get("en", ""))}</{tag}>'


def ltxt(d, lang="en"):
    if not isinstance(d, dict):
        return str(d)
    return d.get(lang) or d.get("en") or ""


def rel(frm, to):
    """Relative link between two site directories ('' = site root).
    frm/to are like 'flora-fauna/birds/' ; to may also be a file 'x.html'."""
    base = frm.rstrip("/") or "."
    target = to.rstrip("/") or "."
    r = _pp.relpath(target, base)
    if to.endswith("/") or to == "":
        r = (r + "/") if r != "." else "./"
    return r


def cap(s):
    return (s[:1].upper() + s[1:]) if s else s


def fmt_n(n):
    """Thousands separator per language (18,548 / 18.548)."""
    en = f"{n:,}"
    if n < 1000:
        return en
    dot = en.replace(",", ".")
    sp = en.replace(",", "\u00a0")       # French: no-break space between thousands
    return f'<span translate="no" data-l10n="{_lj({"en": en, "nl": dot, "es": dot, "fr": sp, "pt": dot})}">{en}</span>'


def _sp_names(sp):
    """{lang: name} with English falling back to the scientific name."""
    n = dict(sp.get("n") or {})
    out = {}
    for lg in LANGS:
        v = n.get(lg)
        out[lg] = cap(v) if v and lg != "zh" else (v or "")
    if not out["en"]:
        out["en"] = sp["s"]
    return out


def sp_langs(sp):
    """Trees this species page exists in: English + STATIC_LANGS with an official name."""
    n = sp.get("n") or {}
    return ["en"] + [lg for lg in STATIC_LANGS if n.get(lg)]


def sp_href(sp, path):
    """href attributes for a link to a species page from `path` (relative), plus a
    data-l10n-href for the trees where that page does not exist (-> English page
    with ?lang=xx, which localizes itself)."""
    have = sp_langs(sp)
    miss = {lg: f"/{BASE}/{sp['p']}/?lang={lg}" for lg in LANGS if lg != "en" and lg not in have}
    target = f"{BASE}/{sp['p']}/"
    h = f'href="{rel(path, target)}"'
    if miss:
        h += f' data-l10n-href="{esc(_json.dumps(miss, separators=(",", ":")))}"'
    return h


def _photo(sp, size):
    img = sp.get("img")
    if not img:
        return None
    u = img["u"]
    if img.get("s") == "inat":
        return u.replace("{size}", {"s": "small", "m": "medium", "l": "large"}[size])
    return u.replace("{w}", {"s": "330", "m": "500", "l": "960"}[size])


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────
class Data:
    def __init__(self):
        raw = _json.loads((_DATA / "species.json").read_text(encoding="utf-8"))
        self.updated = raw.get("updated", "")
        self.species = raw["species"]
        try:
            self.text = _json.loads((_DATA / "text.json").read_text(encoding="utf-8"))
        except Exception:
            self.text = {}
        try:
            self.local = _json.loads((_DATA / "local_names.json").read_text(encoding="utf-8"))
        except Exception:
            self.local = {"species": {}, "groups": {}}
        self.by_slug = {s["p"]: s for s in self.species if s.get("p")}
        # old profile URL -> current slug (duplicate entries merged, see
        # scripts/flora_fauna_data.py merge_duplicates); each gets a redirect page
        self.moved = {o: n for o, n in (raw.get("moved") or {}).items()
                      if n in self.by_slug and o not in self.by_slug}
        self.by_group = {}
        self.by_sub = {}
        for s in self.species:
            self.by_group.setdefault(s["g"], []).append(s)
            self.by_sub.setdefault((s["g"], s["sg"]), []).append(s)
        for lst in list(self.by_group.values()) + list(self.by_sub.values()):
            lst.sort(key=lambda s: (-(1 if s.get("p") else 0), -(s.get("o") or 0), -(s.get("r") or 0), s["s"]))
        self.profiles = [s for s in self.species if s.get("p")]
        self.by_genus = {}
        self.by_family = {}
        for s in self.profiles:
            self.by_genus.setdefault(s["tx"][5], []).append(s)
            self.by_family.setdefault(s["tx"][4], []).append(s)

    def group_local(self, sp):
        """Names Surinamers use for a whole group this species belongs to."""
        G = self.local.get("groups", {})
        out = []
        keys = [sp["tx"][4], sp["tx"][3], sp["tx"][2]]
        if sp["sg"] == "snakes":
            keys.append("Squamata:Serpentes")
        for k in keys:
            if k and k in G:
                out += [[x["n"], x["l"], x.get("dict")] for x in G[k]]
        return out


# ─────────────────────────────────────────────────────────────────────────────
# Page shell
# ─────────────────────────────────────────────────────────────────────────────
_GA = ('<script>(function(){var d=false;function l(){if(d)return;d=true;var s=document.createElement("script");'
       's.async=1;s.src="https://www.googletagmanager.com/gtag/js?id=G-6LTYHZYNSF";document.head.appendChild(s);'
       'window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments);};gtag("js",new Date());'
       'gtag("config","G-6LTYHZYNSF");}["scroll","click","touchstart","keydown"].forEach(function(e){'
       'window.addEventListener(e,l,{once:true,passive:true})});window.addEventListener("load",function(){setTimeout(l,4000)});})();</script>')


class Shell:
    def __init__(self, ctx, assets_ver):
        self.ctx = ctx
        self.v = assets_ver

    def head(self, path, title, desc, og_image=None, jsonld=None, noindex=False, langs=None):
        """path: page directory, e.g. 'flora-fauna/birds/'. title/desc: L dicts."""
        url = f"{SITE_URL}/{path}"
        t_en = esc(title["en"])
        d_en = esc(desc["en"])
        img = og_image or f"{SITE_URL}/og-image.jpg"
        ld = ""
        if jsonld:
            ld = ('<script type="application/ld+json">'
                  + _json.dumps(jsonld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
                  + '</script>')
        robots = '<meta name="robots" content="noindex,follow">' if noindex else '<meta name="robots" content="max-image-preview:large">'
        return (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title translate="no" data-l10n="{_lj(title)}">{t_en}</title>\n'
            f'<meta name="description" content="{d_en}" data-l10n-content="{_lj(desc)}">\n'
            f'{robots}\n'
            + (f'<meta name="l10n-langs" content="{",".join(langs)}">\n' if langs and len(langs) < len(LANGS) else '')
            + f'<link rel="canonical" href="{esc(url)}">\n'
            '<meta property="og:type" content="website">\n'
            '<meta property="og:site_name" content="Explore Suriname">\n'
            '<meta property="og:locale" content="en_US">\n'
            f'<meta property="og:title" content="{t_en}" data-l10n-content="{_lj(title)}">\n'
            f'<meta property="og:description" content="{d_en}" data-l10n-content="{_lj(desc)}">\n'
            f'<meta property="og:url" content="{esc(url)}">\n'
            f'<meta property="og:image" content="{esc(img)}">\n'
            '<meta name="twitter:card" content="summary_large_image">\n'
            '<meta name="twitter:site" content="@exploringsuriname">\n'
            '<link rel="icon" href="/favicon.ico" sizes="48x48 32x32 16x16">\n'
            '<link rel="icon" type="image/svg+xml" href="/favicon.svg">\n'
            '<meta name="theme-color" content="#FBF5E9">\n'
            f'<link rel="stylesheet" href="{ASSETS}ff.css?v={self.v}">\n'
            f'<script defer src="{ASSETS}ff.js?v={self.v}"></script>\n'
            f'{_GA}\n{ld}\n</head>\n'
        )

    def header(self, path, active=None, chips_bar=True, langs=None):
        """Slim section header. `active` = group/collection key for the chip bar."""
        root = rel(path, "")
        hub = rel(path, f"{BASE}/")
        # language switch: absolute, identical in every tree; the current one is
        # highlighted by CSS from <html lang>.
        have = langs or LANGS
        lang_links = "".join(
            f'<a href="{("" if lg == "en" else "/" + lg) + "/" + path if lg in have else "/" + path + "?lang=" + lg}" '
            f'class="ff-lang-{lg}"' + _la(lg) + f'>{LANG_LABEL[lg]}</a>'
            for lg in LANGS)
        chips = [f'<a href="{hub}" class="ff-chip{" on" if active == "hub" else ""}">{tx(U["all_groups"])}</a>']
        for k in GROUP_KEYS:
            chips.append(f'<a href="{rel(path, f"{BASE}/{k}/")}" class="ff-chip{" on" if active == k else ""}">'
                         f'{tx(GROUP[k]["label"])}</a>')
        for k, lab, _i in COLLECTIONS:
            chips.append(f'<a href="{rel(path, f"{BASE}/{k}/")}" class="ff-chip ff-chip-c{" on" if active == k else ""}">'
                         f'{tx(lab)}</a>')
        return (
            '<body class="ff">\n'
            f'<a class="ff-skip" href="#main">{tx(U["skip"])}</a>\n'
            '<nav class="ff-top" aria-label="Flora &amp; Fauna">'
            '<div class="ff-wrap ff-top-in">'
            f'<a href="{root}" class="ff-logo items-baseline" aria-label="Explore Suriname home">'
            '<span class="serif ff-l1">Explore</span><span class="serif ff-l2">Suriname</span></a>'
            f'<a href="{hub}" class="ff-sec">{tx(U["section"])}</a>'
            '<button type="button" class="ff-sbtn" data-ff-search aria-label="Search">'
            '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
            f'{tx(U["search_btn"], cls="ff-sbtn-t")}</button>'
            '<div class="ff-langs" data-langswitch="1">'
            '<button type="button" class="ff-lbtn" aria-label="Language" aria-expanded="false">'
            '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.6 2.6 15.4 0 18M12 3c-2.6 2.6-2.6 15.4 0 18"/></svg>'
            '<span class="ff-lcur"></span></button>'
            f'<div class="ff-lmenu">{lang_links}</div></div>'
            '<button type="button" class="ff-mbtn" aria-label="Menu" aria-expanded="false">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>'
            '<div class="ff-mmenu"></div>'
            '</div>'
            + (f'<div class="ff-chips"><div class="ff-wrap ff-chips-in">{"".join(chips)}</div></div>' if chips_bar else '')
            + '</nav>\n'
        )

    def footer(self, path, data):
        root = rel(path, "")
        about = rel(path, f"{BASE}/about/")
        contact = rel(path, "contact.html")
        dict_ = rel(path, "sranan-tongo-dictionary.html")
        return (
            '<footer class="ff-foot"><div class="ff-wrap">'
            f'<p class="ff-foot-brand"><a href="{root}" class="items-baseline"><span class="serif ff-l1">Explore</span>'
            '<span class="serif ff-l2">Suriname</span></a></p>'
            f'{tx(U["footer_note"], tag="p", cls="ff-foot-note")}'
            f'<p class="ff-foot-links"><a href="{about}">{tx(U["about_page"])}</a>'
            f'<a href="{dict_}">{tx(SITE_LINKS[5][1])}</a>'
            f'<a href="{contact}">{tx(U["correction"])}</a></p>'
            f'<p class="ff-foot-up">{tx(U["updated"])} <time datetime="{esc(data.updated)}">{esc(data.updated)}</time></p>'
            '</div></footer>\n'
            '</body>\n</html>\n'
        )


# ─────────────────────────────────────────────────────────────────────────────
# Building blocks
# ─────────────────────────────────────────────────────────────────────────────
def card(sp, path, lazy=True, listed=False):
    names = _sp_names(sp)
    src = _photo(sp, "s")
    if src:
        alt_l = {lg: names[lg] for lg in LANGS if names[lg]}
        im = (f'<img src="{esc(src)}" alt="{esc(names["en"])}" data-l10n-alt="{_lj(alt_l)}" translate="no" '
              f'loading="{"lazy" if lazy else "eager"}">')
    else:
        im = f'<span class="ff-noimg ff-g-{sp["g"]}" aria-hidden="true"></span>'
    loc = ""
    if sp.get("ln"):
        loc = f'<span class="ff-loc" translate="no">{esc(sp["ln"][0][0])}</span>'
    latin = f'<span class="ff-lat" translate="no"><i>{esc(sp["s"])}</i></span>' if names["en"] != sp["s"] else ""
    nm = {lg: names[lg] for lg in LANGS if names[lg]}
    attrs = (f' id="sp-{sp["p"]}" data-o="{sp.get("o") or 0}" data-r="{sp.get("r") or 0}"' if listed else "")
    return (f'<a class="ff-card" {sp_href(sp, path)}{attrs}>'
            f'<span class="ff-ci">{im}</span><span class="ff-cb">'
            f'{tx(nm, cls="ff-cn")}{latin}{loc}</span></a>')


def checklist_row(sp, path):
    """One compact line per checklist species: name, family, records (the count links
    to the records on GBIF). Filtering/sorting in ff.js reads the visible text."""
    names = _sp_names(sp)
    anchor = sp["s"].lower().replace(" ", "-")
    nm = {lg: names[lg] for lg in LANGS if names[lg]} if names["en"] != sp["s"] else None
    name_html = tx(nm, cls="ff-rn") if nm else ""
    loc = "".join(f'<span class="ff-loc" translate="no">{esc(x[0])}</span>' for x in sp.get("ln", [])[:2])
    return (f'<li class="ff-row" id="{esc(anchor)}" data-o="{sp.get("o") or 0}" data-r="{sp.get("r") or 0}">'
            f'<span class="ff-rlft"><i class="ff-rl" translate="no">{esc(sp["s"])}</i>{name_html}{loc}</span>'
            f'<span class="ff-rf" translate="no">{esc(sp["tx"][4] or "")}</span>'
            f'<a class="ff-rg" href="https://www.gbif.org/species/{sp["k"]}" rel="nofollow">{fmt_n(sp.get("r") or 0)}</a></li>')


def toolbar():
    return ('<div class="ff-tools">'
            f'<input type="search" class="ff-filter" placeholder="{esc(U["filter_ph"]["en"])}" '
            f'data-l10n-placeholder="{_lj(U["filter_ph"])}" translate="no" autocomplete="off">'
            '<select class="ff-sort" translate="no">'
            f'<option value="o" data-l10n="{_lj(U["sort_seen"])}">{esc(U["sort_seen"]["en"])}</option>'
            f'<option value="n" data-l10n="{_lj(U["sort_az"])}">{esc(U["sort_az"]["en"])}</option>'
            f'<option value="l" data-l10n="{_lj(U["sort_latin"])}">{esc(U["sort_latin"]["en"])}</option>'
            '</select></div>')


def crumbs(path, items):
    """items: list of (dir or None, L-label). Also returns BreadcrumbList JSON-LD."""
    out = []
    ld = []
    for i, (d, lab) in enumerate(items):
        if d is None:
            out.append(tx(lab, cls="ff-bc-cur"))
        else:
            out.append(f'<a href="{rel(path, d)}">{tx(lab)}</a>')
        ld.append({"@type": "ListItem", "position": i + 1, "name": ltxt(lab),
                   **({"item": f"{SITE_URL}/{d}"} if d is not None else {"item": f"{SITE_URL}/{path}"})})
    html = '<nav class="ff-bc" aria-label="Breadcrumb">' + '<span class="ff-bc-sep">/</span>'.join(out) + '</nav>'
    return html, {"@type": "BreadcrumbList", "itemListElement": ld}


def _webpage_ld(path, title, desc, extra=None):
    d = {"@type": "WebPage", "@id": f"{SITE_URL}/{path}#webpage", "url": f"{SITE_URL}/{path}",
         "name": title["en"], "description": desc["en"], "inLanguage": "en",
         "isPartOf": {"@type": "WebSite", "@id": f"{SITE_URL}/#website", "name": "Explore Suriname", "url": f"{SITE_URL}/"},
         "publisher": {"@type": "Organization", "name": "Explore Suriname", "url": f"{SITE_URL}/",
                       "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/og-image.jpg"}}}
    if extra:
        d.update(extra)
    return d


def _ld(*nodes):
    return {"@context": "https://schema.org", "@graph": [n for n in nodes if n]}


# ─────────────────────────────────────────────────────────────────────────────
# Pages
# ─────────────────────────────────────────────────────────────────────────────
def _group_tile(data, path, key, label, img_sp, count, profiles):
    href = rel(path, f"{BASE}/{key}/")
    src = _photo(img_sp, "m") if img_sp else None
    im = (f'<img src="{esc(src)}" alt="" loading="lazy" decoding="async" width="500" height="375">' if src
          else f'<span class="ff-noimg ff-g-{key}" aria-hidden="true"></span>')
    return (f'<a class="ff-tile" href="{href}"><span class="ff-ti">{im}</span>'
            f'<span class="ff-tb">{tx(label, cls="ff-tn")}'
            f'<span class="ff-tc"><span>{fmt_n(count)}</span> {tx(U["species_n"])}</span></span></a>')


def _best_photo(lst):
    for s in lst:
        if s.get("img") and s.get("p"):
            return s
    return None


def build_hub(data, shell):
    path = f"{BASE}/"
    title = L("Flora & Fauna of Suriname: Animals, Plants and their Names",
              "Flora en fauna van Suriname: dieren, planten en hun namen",
              "Flora y fauna de Surinam: animales, plantas y sus nombres",
              "苏里南动植物：动物、植物及其名称")
    desc = U["hub_lead"]
    n_all = len(data.species)
    n_prof = len(data.profiles)
    n_srn = sum(1 for s in data.species if any(x[1] == "srn" for x in s.get("ln", [])))
    _pref = ["Rupicola rupicola", "Ara macao", "Ara ararauna", "Eudocimus ruber", "Panthera onca"]
    heroes = [data_sp for n in _pref for data_sp in data.profiles if data_sp["s"] == n and data_sp.get("img")][:1] \
        or [s for s in sorted(data.profiles, key=lambda s: -(s.get("o") or 0)) if s.get("img")][:1]
    hero_img = _photo(heroes[0], "l") if heroes else None

    def tiles(realm):
        out = []
        for k in GROUP_KEYS:
            if GROUP[k]["realm"] != realm:
                continue
            lst = data.by_group.get(k, [])
            if not lst:
                continue
            out.append(_group_tile(data, path, k, GROUP[k]["label"], _best_photo(lst), len(lst),
                                   sum(1 for s in lst if s.get("p"))))
        return "".join(out)

    coll = []
    for k, lab, _intro in COLLECTIONS:
        lst = collection_members(data, k)
        if lst:
            coll.append(_group_tile(data, path, k, lab, _best_photo(lst), len(lst), 0))
    top = sorted([s for s in data.profiles if s.get("img")], key=lambda s: -(s.get("o") or 0))[:18]
    srn = sorted([s for s in data.profiles if any(x[1] == "srn" for x in s.get("ln", [])) and s.get("img")],
                 key=lambda s: -(s.get("o") or 0))[:12]
    body = (
        '<header class="ff-hero">'
        + (f'<img class="ff-hero-bg" src="{esc(hero_img)}" alt="" fetchpriority="high" decoding="async">' if hero_img else "")
        + '<div class="ff-wrap ff-hero-in">'
        f'{tx(U["hub_kicker"], tag="p", cls="ff-kick")}'
        f'{tx(U["section_long"], tag="h1", cls="ff-h1 serif")}'
        f'{tx(U["hub_lead"], tag="p", cls="ff-lead")}'
        '<button type="button" class="ff-bigsearch" data-ff-search>'
        '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
        f'{tx(U["search_ph"])}</button>'
        '<div class="ff-stats">'
        f'<div><b>{fmt_n(n_all)}</b>{tx(U["stat_species"])}</div>'
        f'<div><b>{fmt_n(n_prof)}</b>{tx(U["stat_profiles"])}</div>'
        f'<div><b>{fmt_n(n_srn)}</b>{tx(U["stat_sranan"])}</div>'
        '</div></div></header>'
        '<main id="main" class="ff-wrap ff-main">'
        f'<section class="ff-sec-b">{tx(U["browse_animals"], tag="h2", cls="ff-h2 serif")}<div class="ff-tiles">{tiles("animals")}</div></section>'
        f'<section class="ff-sec-b">{tx(U["browse_plants"], tag="h2", cls="ff-h2 serif")}<div class="ff-tiles">{tiles("plants")}{tiles("fungi")}</div></section>'
        f'<section class="ff-sec-b">{tx(U["collections"], tag="h2", cls="ff-h2 serif")}<div class="ff-tiles">{"".join(coll)}</div></section>'
        f'<section class="ff-sec-b">{tx(U["most_seen"], tag="h2", cls="ff-h2 serif")}{tx(U["most_seen_sub"], tag="p", cls="ff-sub")}'
        f'<div class="ff-grid">{"".join(card(s, path) for s in top)}</div></section>'
        f'<section class="ff-sec-b">{tx(U["sranan_strip"], tag="h2", cls="ff-h2 serif")}'
        f'<div class="ff-grid">{"".join(card(s, path) for s in srn)}</div>'
        f'<p class="ff-more"><a href="{rel(path, f"{BASE}/sranan-names/")}">{tx(U["see_all"])} &rarr;</a></p></section>'
        '</main>'
    )
    ld = _ld(_webpage_ld(path, title, desc, {"@type": "CollectionPage"}),
             {"@type": "Dataset", "name": "Flora & Fauna of Suriname (species checklist)", "description": desc["en"],
              "url": f"{SITE_URL}/{path}", "creator": {"@type": "Organization", "name": "Explore Suriname"},
              "spatialCoverage": {"@type": "Place", "name": "Suriname"},
              "isBasedOn": ["https://www.gbif.org/", "https://www.inaturalist.org/", "https://www.wikidata.org/"],
              "license": "https://creativecommons.org/licenses/by-sa/4.0/"})
    return (shell.head(path, title, desc, og_image=hero_img, jsonld=ld) + shell.header(path, "hub")
            + body + shell.footer(path, data))


def build_group(data, shell, gkey):
    path = f"{BASE}/{gkey}/"
    lab = GROUP[gkey]["label"]
    intro = GROUP[gkey]["intro"]
    title = L(f'{lab["en"]} of Suriname', f'{lab["nl"]} van Suriname', f'{lab["es"]} de Surinam', f'苏里南{lab["zh"]}',
              f'{lab["fr"]} du Suriname', f'{lab["pt"]} do Suriname')
    lst = data.by_group.get(gkey, [])
    bc, bc_ld = crumbs(path, [(f"{BASE}/", U["section"]), (None, lab)])
    subs = []
    for skey, slab, _r in SUBGROUPS[gkey]:
        sl = data.by_sub.get((gkey, skey), [])
        if not sl:
            continue
        subs.append(_group_tile(data, path, f"{gkey}/{skey}", slab, _best_photo(sl), len(sl), 0))
    one_sub = len([1 for skey, _l, _r in SUBGROUPS[gkey] if data.by_sub.get((gkey, skey))]) == 1
    top = [s for s in lst if s.get("p")][:48]
    n_prof = sum(1 for s in lst if s.get("p"))
    body = (
        '<main id="main" class="ff-wrap ff-main">' + bc
        + f'<header class="ff-ph">{tx(title, tag="h1", cls="ff-h1 serif")}{tx(intro, tag="p", cls="ff-lead")}'
        f'<p class="ff-count"><b>{fmt_n(len(lst))}</b> {tx(U["species_n"])} &middot; '
        f'<b>{fmt_n(n_prof)}</b> {tx(U["profiles_n"])}</p></header>'
    )
    if one_sub:
        body += _list_block(data, path, lst)
    else:
        body += (f'<section class="ff-sec-b">{tx(U["subgroups"], tag="h2", cls="ff-h2 serif")}<div class="ff-tiles">{"".join(subs)}</div></section>'
                 f'<section class="ff-sec-b">{tx(U["most_seen"], tag="h2", cls="ff-h2 serif")}'
                 f'<div class="ff-grid">{"".join(card(s, path) for s in top)}</div></section>')
    body += '</main>'
    ld = _ld(_webpage_ld(path, title, intro, {"@type": "CollectionPage"}), bc_ld)
    og = _photo(_best_photo(lst), "l") if _best_photo(lst) else None
    return shell.head(path, title, intro, og_image=og, jsonld=ld) + shell.header(path, gkey) + body + shell.footer(path, data)


def _list_block(data, path, lst):
    prof = [s for s in lst if s.get("p")]
    rest = [s for s in lst if not s.get("p")]
    out = toolbar()
    if prof:
        out += f'<div class="ff-grid ff-list">{"".join(card(s, path, listed=True) for s in prof)}</div>'
    if rest:
        out += (f'<section class="ff-sec-b ff-check">{tx(U["on_checklist"], tag="h2", cls="ff-h2 serif")}'
                f'{tx(U["on_checklist_sub"], tag="p", cls="ff-sub")}'
                f'<div class="ff-rhead"><span>{tx(U["scientific"])}</span><span>{tx(U["family"])}</span><span>{tx(U["records"])}</span></div>'
                f'<ul class="ff-rows ff-list">{"".join(checklist_row(s, path) for s in rest)}</ul></section>')
    out += f'<p class="ff-none" hidden>{tx(U["no_results"])}</p>'
    return out


def build_subgroup(data, shell, gkey, skey):
    path = f"{BASE}/{gkey}/{skey}/"
    glab = GROUP[gkey]["label"]
    slab = subgroup_label(gkey, skey)
    lst = data.by_sub.get((gkey, skey), [])
    title = L(f'{slab["en"]} of Suriname', f'{slab["nl"]} van Suriname', f'{slab["es"]} de Surinam', f'苏里南{slab["zh"]}',
              f'{slab["fr"]} du Suriname', f'{slab["pt"]} do Suriname')
    n_prof = sum(1 for s in lst if s.get("p"))
    desc = L(f'All {len(lst)} {slab["en"].lower()} recorded in Suriname, with names in English, Dutch, Spanish, Chinese, Sranan Tongo and Latin.',
             f'Alle {len(lst)} soorten ({slab["nl"].lower()}) die in Suriname zijn waargenomen, met namen in het Engels, Nederlands, Spaans, Chinees, Sranantongo en Latijn.',
             f'Las {len(lst)} especies ({slab["es"].lower()}) registradas en Surinam, con nombres en inglés, neerlandés, español, chino, sranan y latín.',
             f'在苏里南有记录的全部 {len(lst)} 种{slab["zh"]}，附英语、荷兰语、西班牙语、中文、苏里南汤加语和拉丁学名。',
             f'Les {len(lst)} espèces ({slab["fr"].lower()}) observées au Suriname, avec leurs noms en anglais, néerlandais, espagnol, chinois, sranan tongo et latin.',
             f'Todas as {len(lst)} espécies ({slab["pt"].lower()}) registradas no Suriname, com nomes em inglês, neerlandês, espanhol, chinês, sranan tongo e latim.')
    bc, bc_ld = crumbs(path, [(f"{BASE}/", U["section"]), (f"{BASE}/{gkey}/", glab), (None, slab)])
    body = ('<main id="main" class="ff-wrap ff-main">' + bc
            + f'<header class="ff-ph">{tx(title, tag="h1", cls="ff-h1 serif")}'
            f'<p class="ff-count"><b>{fmt_n(len(lst))}</b> {tx(U["species_n"])} &middot; '
            f'<b>{fmt_n(n_prof)}</b> {tx(U["profiles_n"])}</p></header>'
            + _list_block(data, path, lst) + '</main>')
    ld = _ld(_webpage_ld(path, title, desc, {"@type": "CollectionPage"}), bc_ld)
    og = _photo(_best_photo(lst), "l") if _best_photo(lst) else None
    return shell.head(path, title, desc, og_image=og, jsonld=ld) + shell.header(path, gkey) + body + shell.footer(path, data)


def collection_members(data, key):
    from flora_fauna_taxa import TREES, FRUITS_CROPS
    if key == "trees":
        names = set(TREES)
        return [s for s in data.species if s["s"] in names]
    if key == "fruits-crops":
        names = set(FRUITS_CROPS)
        return [s for s in data.species if s["s"] in names]
    if key == "sranan-names":
        return [s for s in data.species if s.get("ln")]
    if key == "endemic":
        return [s for s in data.species if "E" in (s.get("f") or "")]
    if key == "threatened":
        return [s for s in data.species if s.get("iu") in ("VU", "EN", "CR")]
    if key == "introduced":
        return [s for s in data.species if "I" in (s.get("f") or "")]
    return []


def build_collection(data, shell, key):
    path = f"{BASE}/{key}/"
    lab, intro = next((c[1], c[2]) for c in COLLECTIONS if c[0] == key)
    lst = sorted(collection_members(data, key),
                 key=lambda s: (-(1 if s.get("p") else 0), -(s.get("o") or 0), -(s.get("r") or 0), s["s"]))
    title = L(f'{lab["en"]} of Suriname' if key not in ("sranan-names", "endemic") else lab["en"],
              f'{lab["nl"]} van Suriname' if key not in ("sranan-names", "endemic") else lab["nl"],
              f'{lab["es"]} de Surinam' if key not in ("sranan-names", "endemic") else lab["es"],
              f'苏里南{lab["zh"]}' if key not in ("sranan-names", "endemic") else lab["zh"],
              f'{lab["fr"]} du Suriname' if key not in ("sranan-names", "endemic") else lab["fr"],
              f'{lab["pt"]} do Suriname' if key not in ("sranan-names", "endemic") else lab["pt"])
    bc, bc_ld = crumbs(path, [(f"{BASE}/", U["section"]), (None, lab)])
    n_prof = sum(1 for s in lst if s.get("p"))
    body = ('<main id="main" class="ff-wrap ff-main">' + bc
            + f'<header class="ff-ph">{tx(title, tag="h1", cls="ff-h1 serif")}{tx(intro, tag="p", cls="ff-lead")}'
            f'<p class="ff-count"><b>{fmt_n(len(lst))}</b> {tx(U["species_n"])} &middot; '
            f'<b>{fmt_n(n_prof)}</b> {tx(U["profiles_n"])}</p></header>'
            + _list_block(data, path, lst) + '</main>')
    ld = _ld(_webpage_ld(path, title, intro, {"@type": "CollectionPage"}), bc_ld)
    og = _photo(_best_photo(lst), "l") if _best_photo(lst) else None
    return shell.head(path, title, intro, og_image=og, jsonld=ld) + shell.header(path, key) + body + shell.footer(path, data)


# ── species profile ─────────────────────────────────────────────────────────
def _districts_svg(sp):
    d = sp.get("d") or {}
    if not d:
        return ""
    lst = "".join(
        f'<li><span translate="no"' + (' data-l10n="{&quot;zh&quot;:&quot;帕拉马里博&quot;}"' if n == "Paramaribo" else "")
        + f'>{esc(n)}</span><b>{fmt_n(c)}</b></li>'
        for n, c in sorted(d.items(), key=lambda x: -x[1]))
    on = ",".join(n for n in d)
    return f'<div class="ff-map" data-d="{esc(on)}"><ul class="ff-dl">{lst}</ul></div>'


def _months(sp):
    m = sp.get("m")
    if not m or sum(m) < 12:
        return ""
    return f'<div class="ff-months" data-m="{",".join(map(str, m))}"></div>'


def _summary(sp, names):
    """Short factual intro (all 6 languages) for a profile without a Wikipedia
    text: rank, records, years, districts and IUCN status, from species.json."""
    sci = esc(sp["s"])
    fam, gen = sp["tx"][4], sp["tx"][5]
    r, o, y = sp.get("r") or 0, sp.get("o") or 0, sp.get("y")
    top = [n for n, _c in sorted((sp.get("d") or {}).items(), key=lambda x: -x[1])][:3]
    iu = sp.get("iu") if sp.get("iu") in IUCN else None

    def num(n, lg):
        t = f"{n:,}"
        if lg == "fr":
            return t.replace(",", "\u00a0")
        return t.replace(",", ".") if lg in ("nl", "es", "pt") else t

    def lst(items, lg):
        items = [("帕拉马里博" if (lg == "zh" and x == "Paramaribo") else x) for x in items]
        if lg == "zh":
            return "、".join(items[:-1]) + "和" + items[-1] if len(items) > 1 else items[0]
        conj = {"en": "and", "nl": "en", "es": "y", "fr": "et", "pt": "e"}[lg]
        return ", ".join(items[:-1]) + f" {conj} " + items[-1] if len(items) > 1 else items[0]

    out = {}
    for lg in LANGS:
        nm = esc(cap(names[lg] or names["en"]))
        lead = f"{nm} (<i>{sci}</i>)" if names["en"] != sp["s"] or names[lg] else f"<i>{sci}</i>"
        if lg == "zh":
            lead = f"{nm}（<i>{sci}</i>）" if names["en"] != sp["s"] or names[lg] else f"<i>{sci}</i>"
        rank = esc(fam or gen)
        p = []
        if lg == "en":
            if names["en"] != sp["s"]:
                lead = "The " + lead
            p.append(f"{lead} is a species of the {'family' if fam else 'genus'} <i>{rank}</i>." if rank else f"{lead} is a species.")
            if r:
                t = "once" if r == 1 else f"{num(r, lg)} times"
                yr = (f", in {y[0]}" if y[0] == y[1] else f", between {y[0]} and {y[1]}") if y else ""
                p.append(f"It has been recorded in Suriname {t} (GBIF){yr}.")
            if o:
                p.append(f"iNaturalist users have shared {num(o, lg)} observation{'s' if o != 1 else ''} from Suriname.")
            if top:
                p.append(f"Records come mainly from {lst(top, lg)}." if len(top) > 1 else f"Records come from {lst(top, lg)}.")
            if iu:
                p.append(f"Its global IUCN Red List status is {IUCN[iu]['en']}.")
        elif lg == "nl":
            p.append(f"{lead} is een soort uit {'de familie' if fam else 'het geslacht'} <i>{rank}</i>." if rank else f"{lead} is een soort.")
            if r:
                t = "één keer" if r == 1 else f"{num(r, lg)} keer"
                yr = (f", in {y[0]}" if y[0] == y[1] else f", tussen {y[0]} en {y[1]}") if y else ""
                p.append(f"In Suriname is de soort {t} geregistreerd (GBIF){yr}.")
            if o:
                p.append(f"iNaturalist-gebruikers deelden {num(o, lg)} waarneming{'en' if o != 1 else ''} uit Suriname.")
            if top:
                p.append(f"De meeste gegevens komen uit {lst(top, lg)}." if len(top) > 1 else f"De gegevens komen uit {lst(top, lg)}.")
            if iu:
                p.append(f"De wereldwijde status op de Rode Lijst van de IUCN is: {IUCN[iu]['nl'].lower()}.")
        elif lg == "es":
            p.append(f"{lead} es una especie de la {'familia' if fam else 'género'} <i>{rank}</i>.".replace("de la género", "del género") if rank else f"{lead} es una especie.")
            if r:
                t = "una vez" if r == 1 else f"{num(r, lg)} veces"
                yr = (f", en {y[0]}" if y[0] == y[1] else f", entre {y[0]} y {y[1]}") if y else ""
                p.append(f"En Surinam se ha registrado {t} (GBIF){yr}.")
            if o:
                p.append(f"Los usuarios de iNaturalist han compartido {num(o, lg)} observaci{'ones' if o != 1 else 'ón'} de Surinam.")
            if top:
                p.append(f"La mayoría de los registros proceden de {lst(top, lg)}." if len(top) > 1 else f"Los registros proceden de {lst(top, lg)}.")
            if iu:
                p.append(f"Su categoría mundial en la Lista Roja de la UICN es: {IUCN[iu]['es'].lower()}.")
        elif lg == "fr":
            p.append(f"{lead} est une espèce de la {'famille' if fam else 'genre'} <i>{rank}</i>.".replace("de la genre", "du genre") if rank else f"{lead} est une espèce.")
            if r:
                t = "une fois" if r == 1 else f"{num(r, lg)}\u00a0fois"
                yr = (f", en {y[0]}" if y[0] == y[1] else f", entre {y[0]} et {y[1]}") if y else ""
                p.append(f"Elle a été signalée au Suriname {t} (GBIF){yr}.")
            if o:
                p.append(f"Les utilisateurs d'iNaturalist ont partagé {num(o, lg)} observation{'s' if o != 1 else ''} faite{'s' if o != 1 else ''} au Suriname.")
            if top:
                p.append(f"La plupart des données proviennent de {lst(top, lg)}." if len(top) > 1 else f"Les données proviennent de {lst(top, lg)}.")
            if iu:
                p.append(f"Son statut mondial sur la Liste rouge de l'UICN\u00a0: {IUCN[iu]['fr'].lower()}.")
        elif lg == "pt":
            p.append(f"{lead} é uma espécie da {'família' if fam else 'gênero'} <i>{rank}</i>.".replace("da gênero", "do gênero") if rank else f"{lead} é uma espécie.")
            if r:
                t = "uma vez" if r == 1 else f"{num(r, lg)} vezes"
                yr = (f", em {y[0]}" if y[0] == y[1] else f", entre {y[0]} e {y[1]}") if y else ""
                p.append(f"Foi registrada no Suriname {t} (GBIF){yr}.")
            if o:
                p.append(f"Usuários do iNaturalist compartilharam {num(o, lg)} observaç{'ões' if o != 1 else 'ão'} feita{'s' if o != 1 else ''} no Suriname.")
            if top:
                p.append(f"A maioria dos registros vem de {lst(top, lg)}." if len(top) > 1 else f"Os registros vêm de {lst(top, lg)}.")
            if iu:
                p.append(f"Sua categoria global na Lista Vermelha da IUCN é: {IUCN[iu]['pt'].lower()}.")
        else:
            p.append(f"{lead}是{'' if not rank else f'<i>{rank}</i>' + ('科' if fam else '属')}的一个物种。")
            if r:
                yr = (f"，记录于{y[0]}年" if y[0] == y[1] else f"，时间为{y[0]}年至{y[1]}年") if y else ""
                p.append(f"在苏里南共有{num(r, lg)}条记录（GBIF）{yr}。")
            if o:
                p.append(f"iNaturalist用户分享了{num(o, lg)}条来自苏里南的观察记录。")
            if top:
                p.append(f"记录{'主要' if len(top) > 1 else ''}来自{lst(top, lg)}。")
            if iu:
                p.append(f"其全球IUCN红色名录等级为：{IUCN[iu]['zh']}。")
        out[lg] = (" " if lg != "zh" else "").join(p)
    return out


def build_species(data, shell, sp):
    slug = sp["p"]
    path = f"{BASE}/{slug}/"
    names = _sp_names(sp)
    g, sg = sp["g"], sp["sg"]
    glab = GROUP[g]["label"]
    slab = subgroup_label(g, sg)
    sci = sp["s"]
    loc_species = sp.get("ln", [])
    loc_group = data.group_local(sp)
    # title / description
    def _t(lg):
        n = names[lg] or names["en"]
        return f"{n} ({sci})" if n != sci else sci
    title = {lg: _t(lg) for lg in LANGS}
    srn = [x[0] for x in loc_species if x[1] == "srn"]
    srn_txt = {"en": f" Sranan: {', '.join(srn)}." if srn else "", "nl": f" Sranantongo: {', '.join(srn)}." if srn else "",
               "es": f" Sranan: {', '.join(srn)}." if srn else "", "zh": f" 苏里南汤加语：{'、'.join(srn)}。" if srn else "",
               "fr": f" Sranan\u00a0: {', '.join(srn)}." if srn else "", "pt": f" Sranan: {', '.join(srn)}." if srn else ""}
    desc = {
        "en": f"{names['en']} ({sci}) in Suriname: names in English, Dutch, Spanish, Chinese and Sranan, where it has been recorded, photos and facts.{srn_txt['en']}",
        "nl": f"{names['nl'] or names['en']} ({sci}) in Suriname: namen in het Nederlands, Engels, Spaans, Chinees en Sranantongo, waar de soort is waargenomen, foto's en feiten.{srn_txt['nl']}",
        "es": f"{names['es'] or names['en']} ({sci}) en Surinam: nombres en español, inglés, neerlandés, chino y sranan, dónde se ha registrado, fotos y datos.{srn_txt['es']}",
        "zh": f"苏里南的{names['zh'] or names['en']}（{sci}）：中文、英语、荷兰语、西班牙语和苏里南汤加语名称、记录地点、照片与资料。{srn_txt['zh']}",
        "fr": f"{names['en']} ({sci}) au Suriname\u00a0: noms en anglais, néerlandais, espagnol, chinois et sranan, lieux d'observation, photos et faits.{srn_txt['fr']}",
        "pt": f"{names['en']} ({sci}) no Suriname: nomes em inglês, neerlandês, espanhol, chinês e sranan, onde foi registrada, fotos e fatos.{srn_txt['pt']}",
    }
    bc, bc_ld = crumbs(path, [(f"{BASE}/", U["section"]), (f"{BASE}/{g}/", glab),
                              (f"{BASE}/{g}/{sg}/", slab), (None, {lg: names[lg] or names["en"] for lg in LANGS})])
    # photo
    img = sp.get("img")
    if img:
        alt_l = {lg: names[lg] for lg in LANGS if names[lg]}
        credit = esc(img.get("c", ""))
        photo = (f'<figure class="ff-photo"><img src="{esc(_photo(sp, "m"))}" '
                 f'srcset="{esc(_photo(sp, "m"))} 500w, {esc(_photo(sp, "l"))} 1000w" sizes="(min-width: 900px) 560px, 100vw" '
                 f'alt="{esc(names["en"])}" data-l10n-alt="{_lj(alt_l)}" translate="no" fetchpriority="high" decoding="async">'
                 # blurred copy fills the frame so the whole photo shows (contain), never cropped
                 f'<img class="ff-photo-bg" src="{esc(_photo(sp, "s"))}" alt="" aria-hidden="true" decoding="async">'
                 f'<figcaption translate="no"><a href="{esc(img.get("p", "#"))}" rel="nofollow noopener" target="_blank">{credit}</a></figcaption></figure>')
    else:
        photo = f'<div class="ff-photo ff-photo-none"><span class="ff-noimg ff-g-{g}"></span>{tx(U["no_photo"], cls="ff-nop")}</div>'
    # badges
    badges = []
    iu = sp.get("iu")
    if iu and iu in IUCN:
        badges.append(f'<span class="ff-badge ff-iu-{iu}"><b>{iu}</b> {tx(IUCN[iu])}</span>')
    fl = sp.get("f") or ""
    if "E" in fl:
        badges.append(f'<span class="ff-badge ff-b-end">{tx(U["endemic"])}</span>')
    if "I" in fl:
        badges.append(f'<span class="ff-badge ff-b-int">{tx(U["introduced"])}</span>')
    if "T" in fl:
        badges.append(f'<span class="ff-badge ff-b-thr">{tx(U["threatened_sr"])}</span>')
    # local name chips
    chips = []
    dict_page = rel(path, "sranan-tongo-dictionary.html")
    for n, lg, dk in loc_species:
        lab = LOCAL_LANG.get(lg, L(lg, lg, lg, lg))
        inner = f'<b translate="no">{esc(n)}</b> {tx(lab, cls="ff-lln")}'
        if dk:
            chips.append(f'<a class="ff-lchip" href="{dict_page}?q={esc(_json.dumps(dk)[1:-1])}">{inner}</a>')
        else:
            chips.append(f'<span class="ff-lchip">{inner}</span>')
    # names table
    rows = []
    for lg in NAME_LANGS:
        v = names[lg] if (lg != "en" or names["en"] != sci) else ""
        rows.append(f'<tr><th>{tx(LANG_NAME[lg])}</th><td translate="no" data-lang="{lg}"' + _la(lg)
                    + f'>{esc(v) if v else "&mdash;"}</td></tr>')
    for n, lg, dk in loc_species:
        lab = LOCAL_LANG.get(lg, L(lg, lg, lg, lg))
        val = f'<a href="{dict_page}?q={esc(_json.dumps(dk)[1:-1])}">{esc(n)}</a>' if dk else esc(n)
        rows.append(f'<tr><th>{tx(lab)}</th><td translate="no">{val}</td></tr>')
    for n, lg, dk in loc_group:
        if any(n == x[0] for x in loc_species):
            continue
        lab = LOCAL_LANG.get(lg, L(lg, lg, lg, lg))
        val = f'<a href="{dict_page}?q={esc(_json.dumps(dk)[1:-1])}">{esc(n)}</a>' if dk else esc(n)
        rows.append(f'<tr><th>{tx(lab)}</th><td><span translate="no">{val}</span> <small>({tx(U["group_term"])})</small></td></tr>')
    auth = f' <span class="ff-auth" translate="no">{esc(sp.get("a") or "")}</span>' if sp.get("a") else ""
    rows.append(f'<tr><th>{tx(U["scientific"])}</th><td translate="no"><i>{esc(sci)}</i>{auth}</td></tr>')
    if sp.get("syn"):
        rows.append(f'<tr><th>{tx(U["synonyms"])}</th><td translate="no">'
                    + ", ".join(f"<i>{esc(x)}</i>" for x in sp["syn"]) + '</td></tr>')
    names_tbl = f'<table class="ff-names">{"".join(rows)}</table>'
    # about (Wikipedia, per language)
    txt = data.text.get(slug, {})
    about = ""
    if txt:
        blocks = []
        for lg in LANGS:
            w = txt.get(lg)
            if not w:
                continue
            paras = "".join(f"<p>{esc(p)}</p>" for p in w["x"].split("\n") if p.strip())
            wurl = f"https://{lg}.wikipedia.org/wiki/{esc(w['t'].replace(' ', '_'))}"
            blocks.append(
                f'<div data-l10n-lang="{lg}"' + (" hidden" if lg != "en" else "") + _la(lg) + '>'
                + paras
                + f'<p class="ff-wsrc"><a href="{wurl}" rel="noopener" target="_blank">{esc(U["read_wiki"][lg])}</a>'
                f' &middot; {esc(U["wiki_lic"][lg])}</p></div>')
        if "en" not in txt:
            # no English text: the first available language is the fallback
            first = next(lg for lg in LANGS if lg in txt)
            blocks = [b.replace(f'data-l10n-lang="{first}" hidden', 'data-l10n-lang="en"', 1) if f'data-l10n-lang="{first}"' in b else b for b in blocks]
        # languages without a static copy of this page: the text waits in a <template>
        # that ff.js swaps in when the English page is opened with ?lang=xx
        have = sp_langs(sp)
        tpls = "".join(
            f'<template data-wlang="{lg}" translate="no">'
            + "".join(f"<p>{esc(p_)}</p>" for p_ in txt[lg]["x"].split("\n") if p_.strip())
            + f'<p class="ff-wsrc"><a href="https://{lg}.wikipedia.org/wiki/{esc(txt[lg]["t"].replace(" ", "_"))}" rel="noopener" '
            f'target="_blank">{esc(U["read_wiki"][lg])}</a> &middot; {esc(U["wiki_lic"][lg])}</p></template>'
            for lg in LANGS if lg != "en" and lg not in have and lg in txt and "en" in txt)
        about = (f'<section class="ff-card-s ff-o1">{tx(U["about_species"], tag="h2", cls="ff-h2 serif")}'
                 f'<div class="ff-wtext" translate="no" data-l10n-group>{"".join(blocks)}</div>{tpls}</section>')
    if not txt:
        # no Wikipedia text: a short factual intro built from the data
        sm = _summary(sp, names)
        have = sp_langs(sp)
        blocks = "".join(f'<div data-l10n-lang="{lg}"' + (" hidden" if lg != "en" else "") + _la(lg)
                         + f'><p>{sm[lg]}</p></div>' for lg in LANGS)
        tpls = "".join(f'<template data-wlang="{lg}" translate="no"><p>{sm[lg]}</p></template>'
                       for lg in LANGS if lg != "en" and lg not in have)
        about = (f'<section class="ff-card-s ff-o1">{tx(U["about_species"], tag="h2", cls="ff-h2 serif")}'
                 f'<div class="ff-wtext" translate="no" data-l10n-group>{blocks}</div>{tpls}</section>')
    # in Suriname
    facts = []
    if sp.get("r"):
        facts.append(f'<div class="ff-fact"><b>{fmt_n(sp["r"])}</b>{tx(U["gbif_records"])}</div>')
    if sp.get("o"):
        facts.append(f'<div class="ff-fact"><b>{fmt_n(sp["o"])}</b>{tx(U["inat_obs"])}</div>')
    y = sp.get("y")
    if y:
        facts.append(f'<div class="ff-fact"><b>{y[0]}</b>{tx(U["first_record"])}</div>')
        if y[1] != y[0]:
            facts.append(f'<div class="ff-fact"><b>{y[1]}</b>{tx(U["last_record"])}</div>')
    where = _districts_svg(sp)
    when = _months(sp)
    insr = (f'<section class="ff-card-s ff-o2">{tx(U["in_sr"], tag="h2", cls="ff-h2 serif")}'
            f'<div class="ff-facts">{"".join(facts)}</div>'
            + (f'<h3 class="ff-h3">{tx(U["where"])}</h3>{where}{tx(U["where_note"], tag="p", cls="ff-note")}' if where else "")
            + (f'<h3 class="ff-h3">{tx(U["when"])}</h3>{when}{tx(U["when_note"], tag="p", cls="ff-note")}' if when else "")
            + '</section>')
    # classification
    ranks = [("kingdom", 0), ("phylum", 1), ("class", 2), ("order", 3), ("family", 4), ("genus", 5)]
    cls_rows = "".join(f'<tr><th>{tx(U[r])}</th><td translate="no">{esc(sp["tx"][i])}</td></tr>'
                       for r, i in ranks if sp["tx"][i])
    classification = (f'<section class="ff-card-s ff-o3">{tx(U["classification"], tag="h2", cls="ff-h2 serif")}'
                      f'<table class="ff-names">{cls_rows}</table></section>')
    # related
    rel_list = [s for s in data.by_genus.get(sp["tx"][5], []) if s is not sp]
    if len(rel_list) < 4:
        rel_list += [s for s in data.by_family.get(sp["tx"][4], []) if s is not sp and s not in rel_list]
    rel_list = sorted(rel_list, key=lambda s: -(s.get("o") or 0))[:4]
    related = (f'<section class="ff-sec-b">{tx(U["related"], tag="h2", cls="ff-h2 serif")}'
               f'<div class="ff-grid">{"".join(card(s, path) for s in rel_list)}</div></section>') if rel_list else ""
    # sources
    src = [f'<li><a href="https://www.gbif.org/occurrence/search?country=SR&amp;taxon_key={sp["k"]}" rel="noopener nofollow" target="_blank">{tx(U["src_gbif"])}</a></li>']
    if sp.get("in"):
        src.append(f'<li><a href="https://www.inaturalist.org/taxa/{sp["in"]}" rel="noopener nofollow" target="_blank">{tx(U["src_inat"])}</a></li>')
    if sp.get("wd"):
        src.append(f'<li><a href="https://www.wikidata.org/wiki/{sp["wd"]}" rel="noopener nofollow" target="_blank">{tx(U["src_wd"])}</a></li>')
    if loc_species or loc_group:
        src.append(f'<li><a href="{dict_page}">{tx(U["src_local"])}</a></li>')
    if fl:
        src.append(f'<li><a href="https://www.gbif.org/publisher/search?q=NZCS" rel="noopener nofollow" target="_blank">{tx(U["src_nzcs"])}</a></li>')
    if img:
        src.append(f'<li>{tx(U["photo"])}: <a href="{esc(img.get("p", "#"))}" rel="noopener nofollow" target="_blank" translate="no">{esc(img.get("c", ""))}</a></li>')
    sources = (f'<section class="ff-card-s ff-srcs ff-o4">{tx(U["sources"], tag="h2", cls="ff-h2 serif")}<ul>{"".join(src)}</ul>'
               f'<p class="ff-note"><a href="{rel(path, "contact.html")}">{tx(U["correction"])}</a></p></section>')
    # hero
    h1 = tx({lg: names[lg] for lg in LANGS if names[lg]}, tag="h1", cls="ff-h1 serif")
    latin_line = f'<p class="ff-latin" translate="no"><i>{esc(sci)}</i>{auth}</p>' if names["en"] != sci else ""
    hero = (f'<div class="ff-sp-hero">{photo}<div class="ff-sp-head">'
            f'<p class="ff-kick"><a href="{rel(path, f"{BASE}/{g}/{sg}/")}">{tx(slab)}</a></p>'
            f'{h1}{latin_line}'
            + (f'<div class="ff-lchips">{"".join(chips)}</div>' if chips else "")
            + (f'<div class="ff-badges">{"".join(badges)}</div>' if badges else "")
            + f'{tx(U["names"], tag="h2", cls="ff-h3")}{names_tbl}</div></div>')
    body = ('<main id="main" class="ff-wrap ff-main ff-sp">' + bc + hero
            + '<div class="ff-sp-cols"><div class="ff-col">' + about + classification + '</div>'
            + '<div class="ff-col">' + insr + sources + '</div></div>' + related + '</main>')
    # JSON-LD
    alt_names = sorted({v for lg, v in names.items() if v and v != sci} | {x[0] for x in loc_species})
    # JSON-LD (kept compact: ~4,000 pages x several trees)
    taxon = {"@type": "Taxon", "@id": f"{SITE_URL}/{path}#taxon", "name": sci, "taxonRank": "species",
             "alternateName": alt_names, "parentTaxon": {"@type": "Taxon", "name": sp["tx"][5], "taxonRank": "genus"},
             "sameAs": [u for u in (f"https://www.gbif.org/species/{sp['k']}",
                                    f"https://www.wikidata.org/wiki/{sp['wd']}" if sp.get("wd") else None,
                                    f"https://www.inaturalist.org/taxa/{sp['in']}" if sp.get("in") else None) if u]}
    if img:
        taxon["image"] = {"@type": "ImageObject", "contentUrl": _photo(sp, "l"), "creditText": img.get("c", ""),
                          "license": img.get("lu", ""), "acquireLicensePage": img.get("p", "")}
    page = {"@type": "WebPage", "@id": f"{SITE_URL}/{path}", "name": title["en"], "about": {"@id": taxon["@id"]}}
    ld = _ld(page, taxon, bc_ld)
    og = _photo(sp, "l") if img else None
    langs = sp_langs(sp)
    return (shell.head(path, title, desc, og_image=og, jsonld=ld, langs=langs)
            + shell.header(path, g, chips_bar=False, langs=langs) + body + shell.footer(path, data))


def build_about(data, shell):
    path = f"{BASE}/about/"
    title = L("About the Flora & Fauna of Suriname guide", "Over de gids Flora en fauna van Suriname",
              "Sobre la guía Flora y fauna de Surinam", "关于《苏里南动植物》指南")
    desc = U["about_lead"]
    bc, bc_ld = crumbs(path, [(f"{BASE}/", U["section"]), (None, U["about_page"])])
    n_all, n_prof = len(data.species), len(data.profiles)
    n_all_d, n_prof_d = f"{n_all:,}".replace(",", "."), f"{n_prof:,}".replace(",", ".")
    n_all_fr, n_prof_fr = f"{n_all:,}".replace(",", "\u00a0"), f"{n_prof:,}".replace(",", "\u00a0")
    paras = {
        "en": [
            f"This guide lists every species of animal, plant and fungus with at least one record from Suriname in the Global Biodiversity Information Facility (GBIF): {n_all:,} species at the last update, from museum specimens collected since the 1700s to photos shared last week.",
            f"{n_prof:,} species have a full profile. A profile needs a real description (a Wikipedia article in at least one of our four languages, not a one-line stub) and a photo or a common name. Every other species is on the checklist of its group, with a link to its records, so nothing that has been found in Suriname is left out.",
            "Names come from iNaturalist and Wikidata, which collect the official common names used in each language. Many tropical species simply have no name in Dutch, Spanish or Chinese yet; then we show the English or scientific name rather than inventing one.",
            "Sranan Tongo and Surinamese Dutch names are added by hand, one by one, and only when a source clearly ties the name to the species. They link to our Sranan Tongo dictionary. Some local names cover a whole group (popokai is any parrot); those are labelled as a general name.",
            "Status in Suriname comes from the checklists of the National Zoological Collection of Suriname (NZCS) and the Global Register of Introduced and Invasive Species. World status is the IUCN Red List category.",
            "Photos are only used when the photographer allows reuse (CC0, CC BY or CC BY-SA, or public domain), and every photo is credited with its licence. Descriptions are the opening paragraphs of Wikipedia, shown in your language when available and credited under CC BY-SA 4.0.",
            "Records are not proof of abundance: a species with ten thousand bird-watching records is not necessarily more common than a beetle with one museum specimen. Records with wrong identifications also exist; if you spot one, or know a local name we are missing, please tell us.",
        ],
        "nl": [
            f"Deze gids bevat elke dier-, planten- en schimmelsoort met ten minste één waarneming uit Suriname in de Global Biodiversity Information Facility (GBIF): {n_all_d} soorten bij de laatste update, van museumexemplaren uit de 18e eeuw tot foto's van vorige week.",
            f"{n_prof_d} soorten hebben een volledig profiel. Daarvoor is een echte beschrijving nodig (een Wikipedia-artikel in minstens een van onze vier talen, geen artikel van één regel) en een foto of een gangbare naam. Alle andere soorten staan op de soortenlijst van hun groep, met een link naar de waarnemingen. Zo ontbreekt niets wat in Suriname is gevonden.",
            "Namen komen van iNaturalist en Wikidata, die de officiële namen per taal verzamelen. Veel tropische soorten hebben nog geen Nederlandse, Spaanse of Chinese naam; dan tonen we de Engelse of wetenschappelijke naam in plaats van er zelf een te verzinnen.",
            "Sranantongo- en Surinaams-Nederlandse namen voegen we met de hand toe, één voor één, en alleen als een bron de naam duidelijk aan de soort koppelt. Ze linken naar ons Sranantongo-woordenboek. Sommige lokale namen gelden voor een hele groep (popokai is elke papegaai); die staan vermeld als algemene naam.",
            "De status in Suriname komt uit de soortenlijsten van de Nationale Zoölogische Collectie Suriname (NZCS) en het Global Register of Introduced and Invasive Species. De wereldstatus is de categorie op de Rode Lijst van de IUCN.",
            "We gebruiken alleen foto's die de fotograaf vrijgeeft voor hergebruik (CC0, CC BY, CC BY-SA of publiek domein), en bij elke foto staan de maker en de licentie. De beschrijvingen zijn de eerste alinea's van Wikipedia, in uw taal waar mogelijk, onder CC BY-SA 4.0.",
            "Waarnemingen zeggen niets over hoe algemeen een soort is: een vogel met tienduizend waarnemingen is niet per se algemener dan een kever met één museumexemplaar. Er bestaan ook waarnemingen met een verkeerde determinatie. Ziet u er een, of kent u een lokale naam die ontbreekt? Laat het ons weten.",
        ],
        "es": [
            f"Esta guía reúne cada especie de animal, planta y hongo con al menos un registro de Surinam en el Global Biodiversity Information Facility (GBIF): {n_all_d} especies en la última actualización, desde ejemplares de museo del siglo XVIII hasta fotos compartidas la semana pasada.",
            f"{n_prof_d} especies tienen una ficha completa. Para ello hace falta una descripción real (un artículo de Wikipedia en al menos uno de nuestros cuatro idiomas, no un esbozo de una línea) y una foto o un nombre común. Las demás especies figuran en la lista de su grupo, con un enlace a sus registros, para que no falte nada de lo encontrado en Surinam.",
            "Los nombres provienen de iNaturalist y Wikidata, que recopilan los nombres comunes oficiales de cada idioma. Muchas especies tropicales aún no tienen nombre en neerlandés, español o chino; en ese caso mostramos el nombre inglés o científico en lugar de inventar uno.",
            "Los nombres en sranan tongo y en neerlandés de Surinam se añaden a mano, uno a uno, y solo cuando una fuente vincula claramente el nombre con la especie. Enlazan a nuestro diccionario de sranan tongo. Algunos nombres locales abarcan un grupo entero (popokai es cualquier loro); se indican como nombre general.",
            "El estado en Surinam procede de las listas de la Colección Zoológica Nacional de Surinam (NZCS) y del Global Register of Introduced and Invasive Species. El estado mundial es la categoría de la Lista Roja de la UICN.",
            "Solo usamos fotos cuyo autor permite reutilizarlas (CC0, CC BY, CC BY-SA o dominio público), y cada foto lleva su autor y licencia. Las descripciones son los primeros párrafos de Wikipedia, en tu idioma cuando existen, bajo CC BY-SA 4.0.",
            "Los registros no indican abundancia: una especie con diez mil registros de observadores de aves no es necesariamente más común que un escarabajo con un solo ejemplar de museo. También hay registros mal identificados; si ves uno, o conoces un nombre local que falta, avísanos.",
        ],
        "zh": [
            f"本指南收录了在全球生物多样性信息机构（GBIF）中至少有一条苏里南记录的所有动物、植物和真菌物种：截至最近一次更新共 {n_all:,} 种，既有十八世纪以来采集的博物馆标本，也有上周刚分享的照片。",
            f"其中 {n_prof:,} 种有完整简介。完整简介需要一段真正的描述（至少在我们四种语言之一中有维基百科条目，而不是一行字的小作品），以及一张照片或一个通用名称。其余物种都列在所属类群的名录中，并附有记录链接，因此在苏里南发现过的物种一个也不会遗漏。",
            "名称来自 iNaturalist 和维基数据，它们收集了各语言的正式通用名称。许多热带物种在荷兰语、西班牙语或中文中还没有名称；这种情况下我们显示英文名或学名，而不会自行编造。",
            "苏里南汤加语和苏里南荷兰语名称由我们逐一手工添加，并且只在资料来源明确将名称与物种对应时才收录。这些名称链接到我们的苏里南汤加语词典。有些本地名称指的是整个类群（popokai 指任何鹦鹉），我们会标注为统称。",
            "苏里南境内的状态来自苏里南国家动物收藏馆（NZCS）的名录以及《全球引入与入侵物种登记册》。全球状态采用 IUCN 红色名录的等级。",
            "我们只使用作者允许再利用的照片（CC0、CC BY、CC BY-SA 或公有领域），每张照片都注明作者和许可协议。物种描述取自维基百科的开头段落，有您所用语言的版本时优先显示，按 CC BY-SA 4.0 署名。",
            "记录数量并不代表物种的多寡：一种有一万条观鸟记录的鸟，不一定比只有一件博物馆标本的甲虫更常见。记录中也可能存在鉴定错误；如果您发现错误，或知道我们遗漏的本地名称，请告诉我们。",
        ],
        "fr": [
            f"Ce guide recense toutes les espèces d'animaux, de plantes et de champignons ayant au moins une donnée au Suriname dans le Global Biodiversity Information Facility (GBIF)\u00a0: {n_all_fr} espèces lors de la dernière mise à jour, des spécimens de musée collectés depuis le XVIIIe siècle aux photos partagées la semaine dernière.",
            f"{n_prof_fr} espèces ont une fiche complète. Une fiche exige une vraie description (un article Wikipédia dans au moins une de nos quatre langues sources\u00a0: anglais, néerlandais, espagnol ou chinois, et non une ébauche d'une ligne) ainsi qu'une photo ou un nom commun. Toutes les autres espèces figurent sur la liste de leur groupe, avec un lien vers leurs données\u00a0: rien de ce qui a été trouvé au Suriname n'est laissé de côté.",
            "Les noms proviennent d'iNaturalist et de Wikidata, qui rassemblent les noms communs officiels de chaque langue. Ces sources ne fournissent pas encore de noms français\u00a0; nous affichons donc le nom anglais ou scientifique plutôt que d'en inventer un. Beaucoup d'espèces tropicales n'ont d'ailleurs pas encore de nom en néerlandais, en espagnol ou en chinois.",
            "Les noms en sranan tongo et en néerlandais du Suriname sont ajoutés à la main, un par un, et seulement lorsqu'une source rattache clairement le nom à l'espèce. Ils renvoient à notre dictionnaire de sranan tongo. Certains noms locaux désignent tout un groupe (popokai désigne n'importe quel perroquet)\u00a0; ils sont signalés comme nom générique.",
            "Le statut au Suriname provient des listes de la Collection zoologique nationale du Suriname (NZCS) et du Global Register of Introduced and Invasive Species. Le statut mondial correspond à la catégorie de la Liste rouge de l'UICN.",
            "Nous n'utilisons que des photos dont l'auteur autorise la réutilisation (CC0, CC BY, CC BY-SA ou domaine public), et chaque photo est créditée avec sa licence. Les descriptions sont les premiers paragraphes de Wikipédia, affichés dans votre langue lorsqu'ils existent, sous licence CC BY-SA 4.0.",
            "Les données ne disent rien de l'abondance\u00a0: une espèce comptant dix mille observations d'ornithologues n'est pas forcément plus commune qu'un coléoptère connu par un seul spécimen de musée. Il existe aussi des données mal identifiées. Si vous en repérez une, ou connaissez un nom local qui manque, dites-le-nous.",
        ],
        "pt": [
            f"Este guia reúne todas as espécies de animais, plantas e fungos com pelo menos um registro do Suriname no Global Biodiversity Information Facility (GBIF): {n_all_d} espécies na última atualização, de exemplares de museu coletados desde o século XVIII a fotos compartilhadas na semana passada.",
            f"{n_prof_d} espécies têm uma ficha completa. Para isso é preciso uma descrição de verdade (um artigo da Wikipédia em pelo menos um dos nossos quatro idiomas de origem: inglês, neerlandês, espanhol ou chinês, e não um esboço de uma linha) e uma foto ou um nome popular. Todas as outras espécies aparecem na lista do seu grupo, com link para os registros, para que nada do que já foi encontrado no Suriname fique de fora.",
            "Os nomes vêm do iNaturalist e do Wikidata, que reúnem os nomes populares oficiais de cada idioma. Essas fontes ainda não trazem nomes em português; por isso mostramos o nome em inglês ou o nome científico em vez de inventar um. Muitas espécies tropicais também ainda não têm nome em neerlandês, espanhol ou chinês.",
            "Os nomes em sranan tongo e em neerlandês do Suriname são acrescentados à mão, um a um, e só quando uma fonte liga claramente o nome à espécie. Eles têm link para o nosso dicionário de sranan tongo. Alguns nomes locais valem para um grupo inteiro (popokai é qualquer papagaio); esses aparecem como nome genérico.",
            "A situação no Suriname vem das listas da Coleção Zoológica Nacional do Suriname (NZCS) e do Global Register of Introduced and Invasive Species. A situação global é a categoria da Lista Vermelha da IUCN.",
            "Só usamos fotos cujo autor permite a reutilização (CC0, CC BY, CC BY-SA ou domínio público), e cada foto traz o crédito e a licença. As descrições são os primeiros parágrafos da Wikipédia, no seu idioma quando existem, sob a licença CC BY-SA 4.0.",
            "Os registros não indicam abundância: uma espécie com dez mil registros de observadores de aves não é necessariamente mais comum que um besouro conhecido por um único exemplar de museu. Também há registros com identificação errada. Se você encontrar um, ou conhecer um nome local que esteja faltando, avise a gente.",
        ],
    }
    blocks = "".join(
        f'<div data-l10n-lang="{lg}"' + (" hidden" if lg != "en" else "") + _la(lg) + '>'
        + "".join(f"<p>{esc(p)}</p>" for p in paras[lg]) + '</div>' for lg in LANGS)
    srcs = [
        ("https://www.gbif.org/country/SR/summary", "GBIF: Suriname"),
        ("https://www.inaturalist.org/places/suriname", "iNaturalist: Suriname"),
        ("https://www.wikidata.org/", "Wikidata"),
        ("https://www.wikipedia.org/", "Wikipedia"),
        ("https://commons.wikimedia.org/", "Wikimedia Commons"),
        ("https://www.gbif.org/dataset/c7bcf931-2494-4206-91b0-bbd00700cae2", "NZCS Endemic Fauna Suriname"),
        ("https://www.gbif.org/dataset/c3413793-cd8e-4f74-b0b7-e1f0c155102c", "NZCS Endangered Fauna Suriname"),
        ("https://www.gbif.org/dataset/d1756e5c-0667-4b48-bdbb-3d59abf2bcab", "NZCS Introduced Fauna Suriname"),
        ("https://www.gbif.org/dataset/e98cc325-bc7a-4489-a841-15b734ab2514", "GRIIS Checklist: Suriname"),
        ("https://www.iucnredlist.org/", "IUCN Red List"),
        ("https://www.geoboundaries.org/", "geoBoundaries (district map, OpenStreetMap contributors, ODbL)"),
        ("https://www.naturalearthdata.com/", "Natural Earth (Tigri and Lawa-Litani areas on the district map, public domain)"),
    ]
    src_html = "".join(f'<li><a href="{u}" rel="noopener" target="_blank" translate="no">{esc(t)}</a></li>' for u, t in srcs)
    body = ('<main id="main" class="ff-wrap ff-main ff-narrow">' + bc
            + f'<header class="ff-ph">{tx(title, tag="h1", cls="ff-h1 serif")}{tx(desc, tag="p", cls="ff-lead")}</header>'
            f'<section class="ff-card-s ff-prose" translate="no" data-l10n-group>{blocks}</section>'
            f'<section class="ff-card-s ff-srcs">{tx(U["sources"], tag="h2", cls="ff-h2 serif")}<ul>{src_html}</ul>'
            f'<p class="ff-note"><a href="{rel(path, "contact.html")}">{tx(U["correction"])}</a></p></section></main>')
    ld = _ld(_webpage_ld(path, title, desc, {"@type": "AboutPage"}), bc_ld)
    return shell.head(path, title, desc, jsonld=ld) + shell.header(path, None) + body + shell.footer(path, data)


# ─────────────────────────────────────────────────────────────────────────────
# Assets + registry
# ─────────────────────────────────────────────────────────────────────────────
def _search_index(data):
    """One compact list for the section search, all languages at once:
    [slug-or-anchor-path, latin, en, nl, es, zh, local names, group]"""
    rows = []
    for s in data.species:
        n = s.get("n") or {}
        if s.get("p"):
            target = s["p"] + "/"
        else:
            target = f'{s["g"]}/{s["sg"]}/#' + s["s"].lower().replace(" ", "-")
        rows.append([target, s["s"], n.get("en") or "", n.get("nl") or "", n.get("es") or "", n.get("zh") or "",
                     " ".join(x[0] for x in s.get("ln", [])), s["g"], 1 if s.get("p") else 0, s.get("o") or 0,
                     "".join(lg for lg in STATIC_LANGS if s.get("p") and lg in sp_langs(s)),
                     " ".join(s.get("syn", []))])
    return _json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def _districts_file():
    try:
        d = _json.loads((_DATA / "districts_svg.json").read_text(encoding="utf-8"))
    except Exception:
        return ""
    paths = "".join(f'<path id="d-{esc(n)}" d="{v["d"]}"/>' for n, v in d["districts"].items())
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 330 336">'
            f'<!-- {esc(d.get("source", ""))} --><defs>{paths}</defs></svg>')


def asset_files():
    css = (_ROOT / "flora_fauna_assets" / "ff.css").read_text(encoding="utf-8")
    js = (_ROOT / "flora_fauna_assets" / "ff.js").read_text(encoding="utf-8")
    # interface text the script needs, in every language (the script picks <html lang>)
    i18n = {"k": _all_labels(), "static": list(STATIC_LANGS),
            "site": [[p_, lab] for p_, lab in SITE_LINKS]}
    js = "window.FF_I18N=" + _json.dumps(i18n, ensure_ascii=False, separators=(",", ":")) + ";\n" + js
    return css, js


def all_page_paths(data=None):
    data = data or Data()
    paths = [f"{BASE}/", f"{BASE}/about/"]
    for k in GROUP_KEYS:
        if data.by_group.get(k):
            paths.append(f"{BASE}/{k}/")
            for sk, _l, _r in SUBGROUPS[k]:
                if data.by_sub.get((k, sk)):
                    paths.append(f"{BASE}/{k}/{sk}/")
    for k in COLLECTION_KEYS:
        if collection_members(data, k):
            paths.append(f"{BASE}/{k}/")
    for s in data.profiles:
        paths.append(f"{BASE}/{s['p']}/")
    return paths


def sitemap_entries():
    """(path, priority, changefreq) for generate.build_sitemap."""
    try:
        data = Data()
    except Exception:
        return []
    out = []
    for p in all_page_paths(data):
        depth = p.count("/")
        pr = "0.8" if p == f"{BASE}/" else ("0.7" if depth == 2 else "0.6")
        out.append((p, pr, "monthly"))
    return out


def site_search_entries(top_n=400):
    """Entries for the site-wide search-index.json: hub, groups, collections and
    the most-observed species (the section search covers everything)."""
    try:
        data = Data()
    except Exception:
        return []
    out = [{"n": "Flora & Fauna of Suriname", "u": f"{BASE}/", "c": "Guides", "a": "Suriname",
            "k": "flora fauna animals plants wildlife species nature dieren planten natuur dierenrijk vogels bomen"}]
    for k in GROUP_KEYS:
        if data.by_group.get(k):
            lab = GROUP[k]["label"]
            out.append({"n": f'{lab["en"]} of Suriname', "u": f"{BASE}/{k}/", "c": "Guides", "a": "Suriname",
                        "k": " ".join(lab.values()).lower() + " flora fauna"})
    for k, lab, _i in COLLECTIONS:
        if collection_members(data, k):
            out.append({"n": lab["en"], "u": f"{BASE}/{k}/", "c": "Guides", "a": "Suriname",
                        "k": " ".join(lab.values()).lower() + " flora fauna"})
    top = sorted(data.profiles, key=lambda s: (-(1 if s.get("ln") else 0), -(s.get("o") or 0), -(s.get("r") or 0)))[:top_n]
    for s in top:
        n = s.get("n") or {}
        name = cap(n.get("en") or s["s"])
        kw = " ".join([s["s"]] + [v for v in n.values() if v] + [x[0] for x in s.get("ln", [])]).lower()
        # "ffu": where the NL/ES/ZH search indexes point (build_i18n swaps it in): the
        # card on the subgroup page, which exists in every language tree.
        out.append({"n": name, "u": f"{BASE}/{s['p']}/", "ffu": f"{BASE}/{s['g']}/{s['sg']}/#sp-{s['p']}",
                    "c": "Nature", "a": "Suriname", "k": kw})
    return out


RESERVED_DIRS = set(GROUP_KEYS) | {"about", "assets"} | set(COLLECTION_KEYS)


def redirect_page(path, sp):
    """A species page that moved (two entries for one species were merged).
    English only (build_i18n removes old copies in the other trees), not in the
    sitemap or search, noindex + canonical to the new URL. Keeps ?lang= and #."""
    url = f"/{path}"
    name = esc(cap((sp.get("n") or {}).get("en") or sp["s"]))
    return ('<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="UTF-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title translate="no">{name} | Flora &amp; Fauna of Suriname</title>\n'
            '<meta name="robots" content="noindex,follow">\n'
            '<meta name="l10n-langs" content="en">\n'
            f'<link rel="canonical" href="{SITE_URL}{url}">\n'
            f'<meta http-equiv="refresh" content="0; url={url}">\n'
            f'<script>location.replace({_json.dumps(url)}+location.search+location.hash)</script>\n'
            '</head>\n<body>\n'
            f'<p><a href="{url}">{name}</a></p>\n'
            '</body>\n</html>\n')


# ── incremental build markers (Oct 2026) ─────────────────────────────────────
# ~4,000 section pages are identical from one 15-minute build to the next, yet
# generate.py rewrote them all and build_i18n.py re-parsed every one (most of its
# ~100 s). Now:
#   generate.py   stamps each page with <meta name="ff-src" content="<md5>"> and
#                 does not rewrite a page whose finished copy on disk carries
#                 <meta name="ff-built" content="<same md5>">;
#   build_i18n.py renames ff-src to ff-built when it finishes a page, and skips a
#                 finished page when its build cache says nothing else changed.
#                 If it cannot vouch for a finished page (translations or the
#                 script changed, cache missing, a language copy gone), it puts
#                 the fresh source back (ff_restore_sources) and builds it as usual.
import re as _re
_FF_MARK_RE = _re.compile(r'<meta\s+(?:content="([0-9a-f]{32})"\s+name="ff-(src|built)"'
                          r'|name="ff-(src|built)"\s+content="([0-9a-f]{32})")\s*/?>')


def ff_mark(html):
    """(html with the ff-src marker, md5) — the md5 is of the page without it."""
    h = _hl.md5(html.encode("utf-8")).hexdigest()
    if "<head>\n" not in html:
        return html, None
    return html.replace("<head>\n", f'<head>\n<meta name="ff-src" content="{h}">\n', 1), h


def ff_marker(text):
    """("src"|"built", md5) from the start of a page, or None."""
    m = _FF_MARK_RE.search(text[:8192])
    if not m:
        return None
    return (m.group(2) or m.group(3)), (m.group(1) or m.group(4))


def build_flora_fauna_pages(ctx=None):
    """Returns ({path: html}, {path: text}) — HTML pages and verbatim asset files."""
    data = Data()
    css, js = asset_files()
    search = _search_index(data)
    svg = _districts_file()
    ver = _hl.md5((css + js + search[:2000] + str(len(search))).encode("utf-8")).hexdigest()[:10]
    shell = Shell(ctx or {}, ver)
    pages = {}
    pages[f"{BASE}/index.html"] = build_hub(data, shell)
    pages[f"{BASE}/about/index.html"] = build_about(data, shell)
    for k in GROUP_KEYS:
        if not data.by_group.get(k):
            continue
        pages[f"{BASE}/{k}/index.html"] = build_group(data, shell, k)
        for sk, _l, _r in SUBGROUPS[k]:
            if data.by_sub.get((k, sk)):
                pages[f"{BASE}/{k}/{sk}/index.html"] = build_subgroup(data, shell, k, sk)
    for k in COLLECTION_KEYS:
        if collection_members(data, k):
            pages[f"{BASE}/{k}/index.html"] = build_collection(data, shell, k)
    for s in data.profiles:
        pages[f"{BASE}/{s['p']}/index.html"] = build_species(data, shell, s)
    for old, new in data.moved.items():
        if old in RESERVED_DIRS:
            continue
        pages[f"{BASE}/{old}/index.html"] = redirect_page(f"{BASE}/{new}/", data.by_slug[new])
    files = {
        f"{BASE}/assets/ff.css": css,
        f"{BASE}/assets/ff.js": js,
        f"{BASE}/assets/search.json": search,
        f"{BASE}/assets/districts.svg": svg,
    }
    return pages, files
