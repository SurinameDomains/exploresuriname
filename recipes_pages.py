"""Surinamese recipes section (Learn > Surinamese Recipes), added 1 Nov 2026.

Data: data/recipes.json (written once from the research dossiers; every recipe has
full text in en/nl/es/zh/fr/pt). Pages: recipes.html (hub) and recipe-<slug>.html
(one per dish; clean URLs /recipes and /recipe-<slug> via build_i18n).

All words are baked in per language with data-l10n / data-l10n-group markers that
build_i18n.apply_l10n() resolves, so nothing goes through translations.json or MT
and every shipped page carries only its own language. No JavaScript; one small
shared CSS block (asset_extract moves it to /assets). Photos: images/recipes/,
Wikimedia Commons (CC0 / CC BY / CC BY-SA / public domain), credited under the photo.

Everything this module needs from generate.py comes in through `ctx`:
PAGE_HEAD, nav_html, footer_html, SITE_URL.
"""
import html as _html
import json as _json
import os as _os

LANGS = ("en", "nl", "es", "zh", "fr", "pt")
_HERE = _os.path.dirname(_os.path.abspath(__file__))
DATA = _os.path.join(_HERE, "data", "recipes.json")


def esc(s):
    return _html.escape(str(s), quote=True)


def _lj(d):
    """JSON for a data-l10n attribute (single-quoted attribute value)."""
    return esc(_json.dumps({k: v for k, v in d.items() if k != "en" and v}, ensure_ascii=False))


def tx(d, tag="span", cls="", extra=""):
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c}{extra} translate="no" data-l10n="{_lj(d)}">{esc(d["en"])}</{tag}>'


def group_block(per_lang, tag="div", cls=""):
    """One child per language; build_i18n keeps the right one."""
    c = f' class="{cls}"' if cls else ""
    kids = "".join(
        f'<div data-l10n-lang="{lg}"{"" if lg == "en" else " hidden"}>{per_lang[lg]}</div>'
        for lg in LANGS if per_lang.get(lg))
    return f'<{tag}{c} translate="no" data-l10n-group>{kids}</{tag}>'


# ── UI words ─────────────────────────────────────────────────────────────────
U = {
    "recipes":   {"en": "Recipes", "nl": "Recepten", "es": "Recetas", "zh": "食谱", "fr": "Recettes", "pt": "Receitas"},
    "hub_h1":    {"en": "Surinamese Recipes", "nl": "Surinaamse recepten", "es": "Recetas de Surinam",
                  "zh": "苏里南食谱", "fr": "Recettes du Suriname", "pt": "Receitas do Suriname"},
    "hub_title": {"en": "Surinamese Recipes: Pom, Roti, Moksi Alesi and More",
                  "nl": "Surinaamse recepten: pom, roti, moksi alesi en meer",
                  "es": "Recetas de Surinam: pom, roti, moksi alesi y más",
                  "zh": "苏里南食谱：Pom、Roti、Moksi alesi 等",
                  "fr": "Recettes du Suriname : pom, roti, moksi alesi et plus",
                  "pt": "Receitas do Suriname: pom, roti, moksi alesi e mais"},
    "hub_desc":  {"en": "Cook Surinamese food at home: pom, roti, moksi alesi, saoto, bara, pindasoep and more. Clear recipes from Creole, Hindostani, Javanese and Chinese kitchens.",
                  "nl": "Kook Surinaams thuis: pom, roti, moksi alesi, saoto, bara, pindasoep en meer. Duidelijke recepten uit de Creoolse, Hindostaanse, Javaanse en Chinese keuken.",
                  "es": "Cocina comida de Surinam en casa: pom, roti, moksi alesi, saoto, bara, sopa de maní y más. Recetas claras de las cocinas criolla, hindostaní, javanesa y china.",
                  "zh": "在家做苏里南菜：Pom、Roti、Moksi alesi、Saoto、Bara、花生汤等。来自克里奥尔、印度斯坦、爪哇和华人厨房的清晰食谱。",
                  "fr": "Cuisinez surinamais chez vous : pom, roti, moksi alesi, saoto, bara, soupe d’arachide et plus. Des recettes claires des cuisines créole, hindoustanie, javanaise et chinoise.",
                  "pt": "Cozinhe comida do Suriname em casa: pom, roti, moksi alesi, saoto, bara, sopa de amendoim e mais. Receitas claras das cozinhas crioula, hindustâni, javanesa e chinesa."},
    "hub_intro": {"en": "Suriname cooks with the flavours of every community that made the country: Creole pom and pindasoep, Hindostani roti and bara, Javanese saoto and bami, Chinese tjauw min. These are home recipes, written step by step, the way they are cooked in Surinamese kitchens.",
                  "nl": "Suriname kookt met de smaken van alle gemeenschappen die het land hebben gemaakt: Creoolse pom en pindasoep, Hindostaanse roti en bara, Javaanse saoto en bami, Chinese tjauw min. Dit zijn huisrecepten, stap voor stap uitgeschreven, zoals ze in Surinaamse keukens worden gekookt.",
                  "es": "Surinam cocina con los sabores de todas las comunidades que formaron el país: pom y sopa de maní criollos, roti y bara hindostaníes, saoto y bami javaneses, tjauw min chino. Son recetas caseras, explicadas paso a paso, tal como se preparan en las cocinas de Surinam.",
                  "zh": "苏里南菜融合了缔造这个国家的各个族群的味道：克里奥尔的 Pom 和花生汤，印度斯坦的 Roti 和 Bara，爪哇的 Saoto 和 Bami，华人的 Tjauw min。这些都是家常食谱，按苏里南家庭厨房的做法一步步写成。",
                  "fr": "Le Suriname cuisine avec les saveurs de toutes les communautés qui ont fait le pays : pom et soupe d’arachide créoles, roti et bara hindoustanis, saoto et bami javanais, tjauw min chinois. Ce sont des recettes familiales, expliquées pas à pas, comme on les prépare dans les cuisines surinamaises.",
                  "pt": "O Suriname cozinha com os sabores de todas as comunidades que formaram o país: pom e sopa de amendoim crioulos, roti e bara hindustânis, saoto e bami javaneses, tjauw min chinês. São receitas caseiras, explicadas passo a passo, do jeito que se cozinha nas casas do Suriname."},
    "ingredients": {"en": "Ingredients", "nl": "Ingrediënten", "es": "Ingredientes", "zh": "食材", "fr": "Ingrédients", "pt": "Ingredientes"},
    "method":    {"en": "Method", "nl": "Bereiding", "es": "Preparación", "zh": "做法", "fr": "Préparation", "pt": "Modo de preparo"},
    "tips":      {"en": "Tips", "nl": "Tips", "es": "Consejos", "zh": "小贴士", "fr": "Astuces", "pt": "Dicas"},
    "about":     {"en": "About this dish", "nl": "Over dit gerecht", "es": "Sobre este plato", "zh": "关于这道菜",
                  "fr": "À propos de ce plat", "pt": "Sobre este prato"},
    "prep":      {"en": "Prep", "nl": "Voorbereiding", "es": "Preparación", "zh": "准备", "fr": "Préparation", "pt": "Preparo"},
    "cook":      {"en": "Cooking", "nl": "Kooktijd", "es": "Cocción", "zh": "烹饪", "fr": "Cuisson", "pt": "Cozimento"},
    "total":     {"en": "Total", "nl": "Totaal", "es": "Total", "zh": "总计", "fr": "Total", "pt": "Total"},
    "more":      {"en": "More Surinamese recipes", "nl": "Meer Surinaamse recepten", "es": "Más recetas de Surinam",
                  "zh": "更多苏里南食谱", "fr": "Plus de recettes du Suriname", "pt": "Mais receitas do Suriname"},
    "n_rec":     {"en": "{n} recipes", "nl": "{n} recepten", "es": "{n} recetas", "zh": "{n} 个食谱",
                  "fr": "{n} recettes", "pt": "{n} receitas"},
    "all":       {"en": "All recipes", "nl": "Alle recepten", "es": "Todas las recetas", "zh": "全部食谱",
                  "fr": "Toutes les recettes", "pt": "Todas as receitas"},
    "home":      {"en": "Home", "nl": "Home", "es": "Inicio", "zh": "首页", "fr": "Accueil", "pt": "Início"},
    "photo":     {"en": "Photo", "nl": "Foto", "es": "Foto", "zh": "图片", "fr": "Photo", "pt": "Foto"},
    "srn":       {"en": "In Sranan", "nl": "In het Sranan", "es": "En sranan", "zh": "苏里南语", "fr": "En sranan", "pt": "Em sranan"},
}
SERVES = {"en": "Serves {n}", "nl": "Voor {n} personen", "es": "Para {n} personas", "zh": "{n} 人份",
          "fr": "Pour {n} personnes", "pt": "Serve {n} pessoas"}
MAKES = {  # yield_unit -> per language
    "pieces":  {"en": "Makes {n} pieces", "nl": "{n} stuks", "es": "{n} unidades", "zh": "约 {n} 个",
                "fr": "{n} pièces", "pt": "Rende {n} unidades"},
    "bottles": {"en": "Makes {n} bottles", "nl": "{n} flessen", "es": "{n} botellas", "zh": "约 {n} 瓶",
                "fr": "{n} bouteilles", "pt": "Rende {n} garrafas"},
    "jars":    {"en": "Makes {n} jars", "nl": "{n} potten", "es": "{n} frascos", "zh": "约 {n} 罐",
                "fr": "{n} bocaux", "pt": "Rende {n} potes"},
}
MAKES_ONE = {  # yield of exactly 1
    "pieces":  {"en": "Makes 1 piece", "nl": "1 stuk", "es": "1 unidad", "zh": "约 1 个", "fr": "1 pièce", "pt": "Rende 1 unidade"},
    "bottles": {"en": "Makes 1 bottle", "nl": "1 fles", "es": "1 botella", "zh": "约 1 瓶", "fr": "1 bouteille", "pt": "Rende 1 garrafa"},
    "jars":    {"en": "Makes 1 jar", "nl": "1 pot", "es": "1 frasco", "zh": "约 1 罐", "fr": "1 bocal", "pt": "Rende 1 pote"},
}
YIELD_LD = {"": "servings", "pieces": "pieces", "bottles": "bottles", "jars": "jars"}
GROUP = {
    "creole":     {"en": "Creole", "nl": "Creools", "es": "Criolla", "zh": "克里奥尔菜", "fr": "Créole", "pt": "Crioula"},
    "hindostani": {"en": "Hindostani", "nl": "Hindostaans", "es": "Hindostaní", "zh": "印度斯坦菜", "fr": "Hindoustanie", "pt": "Hindustâni"},
    "javanese":   {"en": "Javanese", "nl": "Javaans", "es": "Javanesa", "zh": "爪哇菜", "fr": "Javanaise", "pt": "Javanesa"},
    "chinese":    {"en": "Chinese-Surinamese", "nl": "Chinees-Surinaams", "es": "Chino-surinamesa", "zh": "苏里南华人菜",
                   "fr": "Sino-surinamaise", "pt": "Sino-surinamesa"},
    "indigenous": {"en": "Indigenous", "nl": "Inheems", "es": "Indígena", "zh": "原住民菜", "fr": "Autochtone", "pt": "Indígena"},
    "maroon":     {"en": "Maroon", "nl": "Marron", "es": "Cimarrona", "zh": "马龙人菜", "fr": "Marronne", "pt": "Quilombola"},
    "jewish":     {"en": "Surinamese-Jewish", "nl": "Surinaams-Joods", "es": "Judeo-surinamesa", "zh": "苏里南犹太菜",
                   "fr": "Judéo-surinamaise", "pt": "Judaico-surinamesa"},
    "mixed":      {"en": "Surinamese", "nl": "Surinaams", "es": "Surinamesa", "zh": "苏里南菜", "fr": "Surinamaise", "pt": "Surinamesa"},
}
COURSE_ORDER = ["main", "soup", "side", "snack", "sweet", "condiment", "drink"]
COURSE = {
    "main":      {"en": "Main dishes", "nl": "Hoofdgerechten", "es": "Platos principales", "zh": "主菜", "fr": "Plats principaux", "pt": "Pratos principais"},
    "soup":      {"en": "Soups", "nl": "Soepen", "es": "Sopas", "zh": "汤", "fr": "Soupes", "pt": "Sopas"},
    "side":      {"en": "Vegetables and sides", "nl": "Groenten en bijgerechten", "es": "Verduras y acompañamientos", "zh": "蔬菜与配菜", "fr": "Légumes et accompagnements", "pt": "Legumes e acompanhamentos"},
    "snack":     {"en": "Snacks", "nl": "Hapjes en snacks", "es": "Bocadillos", "zh": "小吃", "fr": "En-cas", "pt": "Petiscos"},
    "sweet":     {"en": "Cakes and sweets", "nl": "Gebak en zoetigheden", "es": "Pasteles y dulces", "zh": "糕点甜食", "fr": "Gâteaux et douceurs", "pt": "Bolos e doces"},
    "condiment": {"en": "Sambal and pickles", "nl": "Sambal en zuur", "es": "Sambal y encurtidos", "zh": "辣酱与腌菜", "fr": "Sambal et pickles", "pt": "Sambal e conservas"},
    "drink":     {"en": "Drinks", "nl": "Drankjes", "es": "Bebidas", "zh": "饮品", "fr": "Boissons", "pt": "Bebidas"},
}
COURSE_LD = {"main": "Main course", "soup": "Soup", "side": "Side dish", "snack": "Snack",
             "sweet": "Dessert", "condiment": "Condiment", "drink": "Drink"}
IN_LANG = {"en": "en", "nl": "nl", "es": "es", "zh": "zh-Hans", "fr": "fr", "pt": "pt-BR"}


def _dur(m, lg):
    m = int(m or 0)
    h, mm = divmod(m, 60)
    if lg == "zh":
        return (f"{h}小时" if h else "") + (f"{mm}分钟" if mm or not h else "")
    hs = "u" if lg == "nl" else "h"
    if h and mm:
        return f"{h} {hs} {mm} min"
    return f"{h} {hs}" if h else f"{mm} min"


def _iso(m):
    m = int(m or 0)
    h, mm = divmod(m, 60)
    return "PT" + (f"{h}H" if h else "") + (f"{mm}M" if mm or not h else "")


def _yield(r, lg):
    u = r.get("yield_unit") or ""
    tpl = MAKES_ONE[u] if (u in MAKES_ONE and int(r.get("serves") or 0) == 1) else MAKES.get(u, SERVES)
    return tpl[lg].replace("{n}", str(r.get("serves") or ""))


# ── CSS (shared; asset_extract moves it to /assets because it repeats) ──────
CSS = """<style>
.rc-wrap{max-width:1040px;margin:0 auto;padding:22px 16px 72px}
.rc-crumb{font-size:13px;color:#6b7280;margin:0 0 14px}.rc-crumb a{color:inherit}
.rc-kick{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--coral,#d9663a);margin:0 0 6px}
.rc-h1{font-size:clamp(28px,5vw,42px);line-height:1.12;font-weight:700;color:#14281d;margin:0 0 8px}
.rc-srn{color:#4b5563;margin:0 0 10px;font-size:15px}
.rc-lede{font-size:17px;line-height:1.6;color:#374151;max-width:720px;margin:0 0 16px}
.rc-meta{display:flex;flex-wrap:wrap;gap:4px 20px;margin:0 0 20px;padding:0;list-style:none;font-size:14.5px;color:#1f2937}
.rc-meta b{font-weight:600;color:#6b7280;margin-right:4px}
.rc-fig{margin:0 0 26px}.rc-fig img{width:100%;height:auto;aspect-ratio:4/3;object-fit:cover;border-radius:6px;display:block;background:#eef2ee}
.rc-fig figcaption{font-size:11.5px;color:#6b7280;margin-top:6px}.rc-fig figcaption a{color:inherit}
.rc-grid{display:grid;gap:26px}
@media(min-width:860px){.rc-top{display:grid;grid-template-columns:1fr 1fr;gap:30px;align-items:start}.rc-grid{grid-template-columns:330px 1fr;gap:34px}}
.rc-box{background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:18px 20px}
.rc-h2{font-size:21px;font-weight:700;color:#14281d;margin:0 0 12px}
.rc-h3{font-size:14px;font-weight:700;color:#374151;margin:14px 0 6px}
.rc-ing{margin:0;padding-left:18px;list-style:disc}.rc-ing li{margin:0 0 7px;line-height:1.5;color:#1f2937}
.rc-steps{margin:0;padding:0;list-style:none;counter-reset:s}
.rc-steps li{position:relative;padding:0 0 16px 42px;line-height:1.65;color:#1f2937;counter-increment:s}
.rc-steps li:before{content:counter(s);position:absolute;left:0;top:0;width:28px;height:28px;border-radius:50%;background:var(--forest,#1f4d36);color:#fff;font-weight:700;font-size:13px;display:flex;align-items:center;justify-content:center}
.rc-tips{margin:0;padding-left:18px;list-style:disc}.rc-tips li{margin:0 0 8px;line-height:1.55;color:#374151}
.rc-about p{margin:0;line-height:1.65;color:#374151}
.rc-sec{margin-top:26px}
.rc-cards{display:grid;grid-template-columns:1fr;margin:0;padding:0;list-style:none;border-top:1px solid #e5e7eb}
@media(min-width:700px){.rc-cards{grid-template-columns:1fr 1fr;column-gap:32px}}
.rc-card{border-bottom:1px solid #e5e7eb}
.rc-card a{display:block;padding:12px 2px;color:inherit;text-decoration:none}
.rc-card a:hover .rc-ct{text-decoration:underline}
.rc-ct{font-weight:700;color:#14281d;font-size:16px;line-height:1.3;margin:0 0 3px}
.rc-cm{font-size:13px;color:#6b7280;margin:0}
.rc-idx{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:6px 0 8px;padding:0;list-style:none}
@media(max-width:699px){.rc-idx li:last-child:nth-child(odd){grid-column:1/-1}}
@media(min-width:700px){.rc-idx{grid-template-columns:repeat(4,1fr);gap:12px}}
.rc-idx a{display:flex;align-items:center;justify-content:space-between;gap:8px;height:100%;background:#fff;border:1px solid #e5e7eb;border-radius:6px;padding:12px 14px;color:inherit;text-decoration:none;transition:border-color .15s}
.rc-idx a:hover{border-color:var(--forest,#1f4d36)}
.rc-idx b{display:block;font-weight:700;color:#14281d;font-size:15px;line-height:1.25}
.rc-idx small{display:block;color:#6b7280;font-size:12.5px;margin-top:3px}
.rc-idx i{font-style:normal;color:var(--forest,#1f4d36);font-size:18px;line-height:1}
.rc-hsec{margin:30px 0 0;scroll-margin-top:90px}
@media print{nav,header,footer,.rc-cards,.rc-fig figcaption,.rc-crumb{display:none!important}.rc-box{border:0;padding:0}}
</style>"""


def _load():
    with open(DATA, encoding="utf-8") as f:
        return _json.load(f)["recipes"]


def _img(r, size="", lazy=True):
    p = r.get("photo")
    if not p:
        return ""
    alt = p["alt"]
    src = f"/images/recipes/{r['slug']}{size}.webp"
    extra = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high" decoding="async"'
    srcset = (f' srcset="/images/recipes/{r["slug"]}-480.webp 480w, /images/recipes/{r["slug"]}.webp 900w"'
              f' sizes="(min-width:860px) 500px, 100vw"') if not size else ""
    return (f'<img src="{src}"{srcset} width="{900 if not size else 480}" height="{675 if not size else 360}" '
            f'alt="{esc(alt["en"])}" data-l10n-alt="{_lj(alt)}" translate="no"{extra}>')


def _credit(r):
    p = r.get("photo")
    if not p:
        return ""
    return (f'<figcaption>{tx(U["photo"])}: <a href="{esc(p["page"])}" rel="nofollow noopener" target="_blank">'
            f'{esc(p["artist"] or "Wikimedia Commons")}</a>, {esc(p["lic"])}, Wikimedia Commons</figcaption>')


def _card(r):
    t = {lg: r["text"][lg]["title"].split(":")[0].split("：")[0].strip() for lg in LANGS}
    total = int(r.get("prep_min") or 0) + int(r.get("cook_min") or 0)
    meta = {lg: f'{GROUP[r["group"]][lg]} · {_dur(total, lg)}' for lg in LANGS}
    return (f'<li class="rc-card"><a href="recipe-{r["slug"]}.html">'
            f'{tx(t, "p", "rc-ct")}{tx(meta, "p", "rc-cm")}</a></li>')


def _recipe_ld(r, lg, site):
    t = r["text"][lg]
    ld = {
        "@context": "https://schema.org", "@type": "Recipe",
        "name": t["title"], "description": t["summary"],
        "url": f"{site}/recipe-{r['slug']}",
        "inLanguage": IN_LANG[lg],
        "author": {"@type": "Organization", "name": "Explore Suriname", "url": site + "/"},
        "recipeCuisine": "Surinamese",
        "recipeCategory": COURSE_LD.get(r["course"], "Main course"),
        "recipeYield": f'{r.get("serves")} {YIELD_LD.get(r.get("yield_unit") or "", "servings")}'.replace("1 jars", "1 jar").replace("1 bottles", "1 bottle").replace("1 pieces", "1 piece") if int(r.get("serves") or 0) == 1 else f'{r.get("serves")} {YIELD_LD.get(r.get("yield_unit") or "", "servings")}',
        "recipeIngredient": [i for g in t["ingredients"] for i in g["items"]],
        "recipeInstructions": [{"@type": "HowToStep", "text": s} for s in t["steps"]],
        "keywords": ", ".join([r["slug"].replace("-", " "), "Suriname"] + list(r.get("tags") or [])),
    }
    if r.get("prep_min"):
        ld["prepTime"] = _iso(r["prep_min"])
    if r.get("cook_min"):
        ld["cookTime"] = _iso(r["cook_min"])
    ld["totalTime"] = _iso(int(r.get("prep_min") or 0) + int(r.get("cook_min") or 0))
    if r.get("photo"):
        ld["image"] = [f"{site}/images/recipes/{r['slug']}.webp"]
    return ('<script type="application/ld+json">'
            + _json.dumps(ld, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>")


def _head(ctx, fname, title, desc, og_img):
    site = ctx["SITE_URL"]
    url = f"{site}/{fname.replace('.html', '')}"
    def _brand(d):
        return {lg: (v + " | Explore Suriname" if len(v) <= 48 else v) for lg, v in d.items()}
    tb = _brand(title)
    return (ctx["PAGE_HEAD"]
            + f'\n  <title translate="no" data-l10n="{_lj(tb)}">{esc(tb["en"])}</title>'
            + f'\n  <meta name="description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <link rel="canonical" href="{url}">'
            + '\n  <meta property="og:type" content="article">'
            + '\n  <meta property="og:site_name" content="Explore Suriname">'
            + f'\n  <meta property="og:url" content="{url}">'
            + f'\n  <meta property="og:title" content="{esc(tb["en"])}" data-l10n-content="{_lj(tb)}">'
            + f'\n  <meta property="og:description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <meta property="og:image" content="{og_img}">'
            + '\n  <meta name="twitter:card" content="summary_large_image">'
            + f'\n  <meta name="twitter:title" content="{esc(tb["en"])}" data-l10n-content="{_lj(tb)}">'
            + f'\n  <meta name="twitter:description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <meta name="twitter:image" content="{og_img}">'
            + "\n</head>")


def _shell(ctx, head, body):
    return (head + '\n<body class="bg-gray-50 overflow-x-hidden">\n' + ctx["nav_html"]("recipes") + CSS
            + '<main class="rc-wrap">' + body + '</main>\n' + ctx["footer_html"]() + "\n</body>\n</html>")


def _crumb(extra=""):
    return (f'<p class="rc-crumb"><a href="./">{tx(U["home"])}</a> &#8250; '
            f'<a href="recipes.html">{tx(U["recipes"])}</a>{extra}</p>')


def _recipe_body(r, lg):
    t = r["text"][lg]
    ing = ""
    for g in t["ingredients"]:
        if g.get("group"):
            ing += f'<h3 class="rc-h3">{esc(g["group"])}</h3>'
        ing += '<ul class="rc-ing">' + "".join(f"<li>{esc(i)}</li>" for i in g["items"]) + "</ul>"
    steps = '<ol class="rc-steps">' + "".join(f"<li>{esc(s)}</li>" for s in t["steps"]) + "</ol>"
    tips = ""
    if t.get("tips"):
        tips = (f'<section class="rc-sec rc-box"><h2 class="rc-h2">{esc(U["tips"][lg])}</h2>'
                '<ul class="rc-tips">' + "".join(f"<li>{esc(x)}</li>" for x in t["tips"]) + "</ul></section>")
    about = ""
    if t.get("about"):
        about = (f'<section class="rc-sec rc-box rc-about"><h2 class="rc-h2">{esc(U["about"][lg])}</h2>'
                 f'<p>{esc(t["about"])}</p></section>')
    return (f'<div class="rc-grid"><section class="rc-box"><h2 class="rc-h2">{esc(U["ingredients"][lg])}</h2>{ing}</section>'
            f'<div><section class="rc-box"><h2 class="rc-h2">{esc(U["method"][lg])}</h2>{steps}</section>{tips}{about}</div></div>')


def _related(r, allr, n=4):
    same = [x for x in allr if x["slug"] != r["slug"] and x["group"] == r["group"]]
    other = [x for x in allr if x["slug"] != r["slug"] and x["group"] != r["group"] and x["course"] == r["course"]]
    pick = (same + other)[:n]
    if len(pick) < n:
        pick += [x for x in allr if x["slug"] != r["slug"] and x not in pick][: n - len(pick)]
    return pick


def build_recipe_page(ctx, r, allr):
    site = ctx["SITE_URL"]
    title = {lg: r["text"][lg]["title"] for lg in LANGS}
    desc = {lg: r["text"][lg]["summary"] for lg in LANGS}
    og = f"{site}/images/recipes/{r['slug']}.webp" if r.get("photo") else f"{site}/og-image.jpg"
    head = _head(ctx, f"recipe-{r['slug']}.html", title, desc, og)
    kick = {lg: f'{GROUP[r["group"]][lg]} · {COURSE[r["course"]][lg]}' for lg in LANGS}
    srn = ""
    if r.get("srn"):
        srn = f'<p class="rc-srn">{tx(U["srn"])}: <strong translate="no">{esc(r["srn"])}</strong></p>'
    total = int(r.get("prep_min") or 0) + int(r.get("cook_min") or 0)
    meta = []
    meta.append("<li>" + tx({lg: _yield(r, lg) for lg in LANGS}) + "</li>")
    if r.get("prep_min"):
        meta.append(f'<li><b>{tx(U["prep"])}</b>{tx({lg: _dur(r["prep_min"], lg) for lg in LANGS})}</li>')
    if r.get("cook_min"):
        meta.append(f'<li><b>{tx(U["cook"])}</b>{tx({lg: _dur(r["cook_min"], lg) for lg in LANGS})}</li>')
    meta.append(f'<li><b>{tx(U["total"])}</b>{tx({lg: _dur(total, lg) for lg in LANGS})}</li>')
    intro = {lg: f'<p class="rc-lede">{esc(r["text"][lg]["intro"])}</p>' for lg in LANGS}
    head_txt = (f'<p class="rc-kick">{tx(kick)}</p>{tx(title, "h1", "rc-h1 serif")}{srn}'
                + group_block(intro) + '<ul class="rc-meta">' + "".join(meta) + "</ul>")
    fig = ""
    if r.get("photo"):
        fig = f'<figure class="rc-fig">{_img(r, "", lazy=False)}{_credit(r)}</figure>'
    top = (f'<div class="rc-top"><div>{head_txt}</div><div>{fig}</div></div>' if fig
           else f'<div>{head_txt}</div>')
    body_l = {lg: _recipe_body(r, lg) + _recipe_ld(r, lg, site) for lg in LANGS}
    rel = ('<section class="rc-sec"><h2 class="rc-h2">' + tx(U["more"]) + '</h2><ul class="rc-cards">'
           + "".join(_card(x) for x in _related(r, allr)) + '</ul>'
           + f'<p style="margin-top:14px"><a href="recipes.html" style="color:var(--forest,#1f4d36);font-weight:600">'
           + tx(U["all"]) + ' &#8250;</a></p></section>')
    body = _crumb() + top + group_block(body_l) + rel
    return _shell(ctx, head, body)


def build_hub(ctx, allr):
    site = ctx["SITE_URL"]
    head = _head(ctx, "recipes.html", U["hub_title"], U["hub_desc"], f"{site}/og-image.jpg")
    by = {c: sorted([r for r in allr if r["course"] == c], key=lambda r: r["text"]["nl"]["title"].lower())
          for c in COURSE_ORDER}
    chips = '<ul class="rc-idx">' + "".join(
        f'<li><a href="#{c}"><span>{tx(COURSE[c], "b")}'
        f'{tx({lg: U["n_rec"][lg].replace("{n}", str(len(by[c]))) for lg in LANGS}, "small")}</span>'
        f'<i aria-hidden="true">&#8250;</i></a></li>' for c in COURSE_ORDER if by[c]) + "</ul>"
    secs = "".join(
        f'<section class="rc-hsec" id="{c}"><h2 class="rc-h2">{tx(COURSE[c])}</h2>'
        f'<ul class="rc-cards">{"".join(_card(r) for r in by[c])}</ul></section>'
        for c in COURSE_ORDER if by[c])
    items = [{"@type": "ListItem", "position": i + 1, "url": f"{site}/recipe-{r['slug']}"}
             for i, r in enumerate([r for c in COURSE_ORDER for r in by[c]])]
    ld = ('<script type="application/ld+json">' + _json.dumps(
        {"@context": "https://schema.org", "@type": "ItemList", "name": "Surinamese Recipes",
         "itemListElement": items}, ensure_ascii=False, separators=(",", ":")) + "</script>")
    body = (f'<p class="rc-crumb"><a href="./">{tx(U["home"])}</a> &#8250; {tx(U["recipes"])}</p>'
            f'{tx(U["hub_h1"], "h1", "rc-h1 serif")}'
            + group_block({lg: f'<p class="rc-lede">{esc(U["hub_intro"][lg])}</p>' for lg in LANGS})
            + chips + secs + ld)
    return _shell(ctx, head, body)


def build_recipes_pages(ctx):
    allr = _load()
    pages = {"recipes.html": build_hub(ctx, allr)}
    for r in allr:
        pages[f"recipe-{r['slug']}.html"] = build_recipe_page(ctx, r, allr)
    return pages


def recipe_index():
    """(slug, English title) for sitemap / search / llms.txt."""
    try:
        return [(r["slug"], r["text"]["en"]["title"], r["text"]["en"]["summary"]) for r in _load()]
    except Exception:
        return []
