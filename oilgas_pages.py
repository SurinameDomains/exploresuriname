#!/usr/bin/env python3
"""
Explore Suriname — Oil & Gas section builder.

Seven pages, all driven by data/oilgas.json:

    oil-and-gas.html              hub / overview
    suriname-oil-blocks.html      blocks, operators, discoveries
    granmorgu.html                the GranMorgu development
    suriname-oil-timeline.html    history and roadmap to first oil
    suriname-oil-contracts.html   PSCs, fiscal terms, bid rounds
    suriname-oil-government.html  ministry, Staatsolie, the oil fund
    suriname-oil-jobs.html        jobs, local content, suppliers

generate.py calls build_oilgas_pages(ctx) and merges the returned dict into
its own `pages` map. Everything this module needs from generate.py (PAGE_HEAD
helpers, nav, footer, news cards, live Brent) arrives through `ctx`, so there
is no circular import.

House rules that apply here too: no em dashes in visible copy, no decorative
emoji, no <style> blocks emitted from the body (Tailwind utilities only).
NOTE: tailwind.config.js must list this file under `content` or the classes
used here will not be compiled.
"""

import json
import re
from pathlib import Path

_DATA_PATH = Path(__file__).parent / "data" / "oilgas.json"


def _load():
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception as e:                       # pragma: no cover
        print(f"  WARN oilgas.json unreadable: {e}")
        return {"meta": {"updated": "", "sources": []}, "keynumbers": [], "blocks": [],
                "wells": [], "players": [], "timeline": [], "glossary": []}


# ── Section pages: (file, nav key, short chip label, long label) ─────────────
SECTION_PAGES = [
    ("oil-and-gas.html",             "oilgas",       "Overview",     "Oil &amp; Gas Overview"),
    ("suriname-oil-blocks.html",     "oilblocks",    "Blocks",       "Blocks &amp; Operators"),
    ("granmorgu.html",               "granmorgu",    "GranMorgu",    "The GranMorgu Project"),
    ("suriname-oil-timeline.html",   "oiltimeline",  "Timeline",     "Timeline &amp; Roadmap"),
    ("suriname-oil-contracts.html",  "oilcontracts", "Contracts",    "Contracts &amp; Fiscal Terms"),
    ("suriname-oil-government.html", "oilgov",       "Who Governs",  "Ministry, Staatsolie &amp; the Oil Fund"),
    ("suriname-oil-jobs.html",       "oiljobs",      "Jobs",         "Jobs, Local Content &amp; Suppliers"),
]

_OIL = "#92400e"     # the amber the news page already uses for the oil tab


# ── Shared building blocks ───────────────────────────────────────────────────
def _section_nav(active):
    """Chip strip linking the seven pages of the section."""
    chips = []
    for fname, key, short, _long in SECTION_PAGES:
        if key == active:
            chips.append(
                f'<span class="shrink-0 px-4 py-2 rounded-full text-sm font-semibold text-white" '
                f'style="background:{_OIL}">{short}</span>')
        else:
            chips.append(
                f'<a href="{fname}" class="shrink-0 px-4 py-2 rounded-full text-sm font-semibold '
                f'text-gray-600 bg-white border border-gray-200 hover:border-gray-400 hover:text-gray-900 '
                f'transition">{short}</a>')
    return ('<div class="max-w-5xl mx-auto px-5 pt-8">'
            '<div class="flex gap-2 overflow-x-auto pb-1">' + "".join(chips) + '</div></div>')


def _kpi_grid(items):
    """items: list of dicts with v / l / s."""
    cells = "".join(
        '<div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">'
        f'<p class="serif text-2xl font-bold" style="color:{_OIL}">{i["v"]}</p>'
        f'<p class="text-gray-800 text-sm font-semibold mt-1 leading-snug">{i["l"]}</p>'
        f'<p class="text-gray-400 text-xs mt-2">{i["s"]}</p></div>'
        for i in items)
    return '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">' + cells + '</div>'


def _table(headers, rows, first_col_bold=True):
    """Responsive table. rows = list of lists of already-escaped HTML strings."""
    head = "".join(
        f'<th class="py-3 px-4 text-left font-semibold text-gray-900 whitespace-nowrap">{h}</th>'
        for h in headers)
    body = []
    for r in rows:
        tds = []
        for idx, cell in enumerate(r):
            cls = "py-3 px-4 align-top text-gray-700"
            if idx == 0 and first_col_bold:
                cls = "py-3 px-4 align-top font-semibold text-gray-900"
            # Mobile card label. Two-column tables need none: the first cell
            # already reads as the row heading. Long prose headers are skipped
            # too, they would shout on every card.
            lab = headers[idx] if idx < len(headers) else ""
            lab = re.sub(r"<[^>]+>", "", lab).replace('"', "").strip()
            if len(headers) < 3 or len(lab) > 22:
                lab = ""
            tds.append(f'<td class="{cls}" data-label="{lab}">{cell}</td>')
        body.append('<tr class="border-t border-gray-100">' + "".join(tds) + '</tr>')
    # esr-rtable: horizontal scroll from sm up, stacked labelled cards on phones
    # (the CSS lives in PAGE_HEAD in generate.py).
    return ('<div class="esr-rtable sm:overflow-x-auto sm:-mx-2 sm:px-2">'
            '<table class="w-full text-sm sm:min-w-[640px]">'
            '<thead class="bg-gray-50"><tr>' + head + '</tr></thead><tbody>'
            + "".join(body) + '</tbody></table></div>')


def _defs(pairs):
    """Definition rows: list of (term, description)."""
    return "".join(
        '<div class="border-t border-gray-100 py-3 first:border-t-0 first:pt-0">'
        f'<p class="font-semibold text-gray-900 text-sm">{t}</p>'
        f'<p class="text-gray-600 text-sm leading-relaxed mt-1">{d}</p></div>'
        for t, d in pairs)


def _callout(title, body, tone="mint"):
    bg, bc = ("#f0f9f4", "var(--forest2)") if tone == "mint" else ("#fdf6ec", _OIL)
    return ('<div class="rounded-2xl p-6 border-l-4 mb-8" '
            f'style="background:{bg};border-color:{bc}">'
            f'<p class="text-gray-900 font-bold mb-2">{title}</p>'
            f'<div class="text-gray-800 text-sm leading-relaxed">{body}</div></div>')


def _steps(items):
    """items: list of (heading, text)."""
    out = []
    for n, (h, t) in enumerate(items, 1):
        out.append(
            '<div class="flex gap-4 mb-5 last:mb-0">'
            '<div class="shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-white '
            f'text-sm font-bold" style="background:{_OIL}">{n}</div>'
            f'<div><p class="font-semibold text-gray-900 text-sm mb-1">{h}</p>'
            f'<p class="text-gray-700 text-sm leading-relaxed">{t}</p></div></div>')
    return "".join(out)


def _asof(meta):
    """'August 2026' from the data file's updated date, so headings never go stale."""
    from datetime import datetime as _dt
    try:
        return _dt.strptime(meta.get("updated", ""), "%Y-%m-%d").strftime("%B %Y")
    except Exception:
        return "2026"


def _sources_block(meta, extra=None):
    links = list(meta.get("sources", [])) + list(extra or [])
    items = "".join(
        f'<li class="mb-1"><a href="{s["url"]}" rel="nofollow noopener" target="_blank" '
        f'class="hover:underline" style="color:var(--forest2)">{s["label"]}</a></li>'
        for s in links)
    return ('<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 mb-6">'
            '<p class="text-xs font-semibold uppercase tracking-widest mb-2" '
            'style="color:var(--forest2)">Where this comes from</p>'
            '<h2 class="serif text-xl font-bold text-gray-900 mb-4">Sources</h2>'
            '<p class="text-gray-700 text-sm leading-relaxed mb-3">Figures on this page come from '
            'operator announcements, Staatsolie, the Surinamese government and the energy trade press. '
            'Projects move, so treat forward-looking dates as targets rather than promises.</p>'
            f'<ul class="text-sm list-disc pl-5 text-gray-700">{items}</ul>'
            f'<p class="text-gray-400 text-xs mt-4">Page data last reviewed {meta.get("updated","")}.</p>'
            '</div>')


def _related(active):
    """Cards linking to the other pages in the section."""
    cards = []
    for fname, key, _short, long in SECTION_PAGES:
        if key == active:
            continue
        cards.append(
            f'<a href="{fname}" class="block bg-white rounded-2xl border border-gray-100 shadow-sm '
            'p-5 hover:shadow-md transition">'
            f'<p class="font-bold text-gray-900 text-sm mb-1">{long}</p>'
            '<p class="text-xs" style="color:var(--forest2)">Read more</p></a>')
    return ('<h2 class="serif text-2xl font-bold text-gray-900 mb-5 mt-2">More in this section</h2>'
            '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">'
            + "".join(cards) + '</div>')


def _page(ctx, key, title, desc, fname, kicker, h1, sub, body, faq=None,
          extra_ld=None, tail=""):
    """Assemble one section page using generate.py's hub helpers."""
    head = ctx["hub_head"](title, desc, fname, faq=faq, extra_ld=extra_ld)
    hero = ctx["hub_hero"](kicker, h1, sub).replace("{NAV}", ctx["nav_html"](key))
    inner = body
    if faq:
        inner += ctx["hub_faq"](faq)
    inner += _related(key)
    main = ('<main class="max-w-5xl mx-auto px-5 py-10 pb-24">' + inner + '</main>')
    return (head + hero + _section_nav(key) + main + tail + "\n"
            + ctx["footer_html"]() + "\n</body>\n</html>")


# ═══════════════════════════════════════════════════════════════════════════
# 1. HUB
# ═══════════════════════════════════════════════════════════════════════════
def _build_hub(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]
    meta  = D["meta"]

    faq = [
        ("Has Suriname started producing offshore oil?",
         "Not yet. Suriname produces around 17,000 barrels a day from onshore fields in Saramacca "
         "district, which it has done since 1982. The first offshore production, from the GranMorgu "
         "development in Block 58, is targeted for 2028."),
        ("How much oil does Suriname have?",
         "The GranMorgu development alone holds more than 750 million barrels, and TotalEnergies has "
         "said better seismic could push that toward 800 million. Across Block 52, PETRONAS reports "
         "discoveries exceeding one billion barrels of oil equivalent, much of it gas. Total national "
         "resources are still unknown because roughly half the basin has yet to be drilled."),
        ("Who owns Suriname&#8217;s oil?",
         "The state does. Companies operate under production sharing contracts: they fund and run the "
         "work, recover their costs from part of the production, and split the rest with the state. "
         "Staatsolie manages the acreage on behalf of Suriname and can take up to a 20% share in any "
         "development."),
        ("Will oil make Suriname rich?",
         "It will make the state considerably richer. The IMF projects GDP growth of roughly 55% in the "
         "first full year of production, and Staatsolie has pointed to government oil revenue in the "
         "range of US$1.5 to 2 billion a year at peak. Whether that translates into broad prosperity "
         "depends on the Savings and Stabilisation Fund, spending discipline and local content, all of "
         "which the IMF has flagged as unfinished work."),
        ("Will petrol get cheaper in Suriname?",
         "There is no automatic link. Crude from GranMorgu is sold on the world market at Brent-linked "
         "prices, and Suriname's pump prices depend on refining, import costs, the exchange rate and "
         "government levies. Producing countries routinely pay world prices at the pump."),
        ("Is any of this open to Surinamese businesses?",
         "Yes, mostly through the supply chain: logistics, catering, marine services, fabrication, "
         "waste handling, security, accommodation and professional services. Registration runs through "
         "the Suriname Supplier Registration Portal. There is still no local content law, only policy, "
         "which is the sector's most-argued gap."),
    ]

    body = _callout(
        "The 60-second version",
        "<p class='mb-2'>Suriname sits on the same geology that made Guyana an oil producer. Between 2020 "
        "and 2022 a run of discoveries offshore proved it. In October 2024 TotalEnergies, APA and "
        "Staatsolie committed about US$10.5 billion to build GranMorgu, a floating production vessel "
        "150 km offshore that will handle 220,000 barrels a day.</p>"
        "<p>Nothing offshore is producing yet. The FPSO is under construction in Asia, subsea equipment "
        "is arriving in Paramaribo, and first oil is targeted for 2028. Everything else on this page is "
        "about what that means, who controls it and what is still unresolved.</p>", tone="oil")

    body += ('<h2 class="serif text-2xl font-bold text-gray-900 mb-5">Suriname oil and gas by the numbers</h2>'
             + _kpi_grid(D["keynumbers"]))

    # Live strip: Brent + countdown
    brent = ctx.get("brent_price")
    brent_upd = ctx.get("brent_updated") or ""
    if brent:
        brent_html = (f'<p class="serif text-3xl font-bold" style="color:{_OIL}">US$ {brent:,.2f}</p>'
                      f'<p class="text-gray-500 text-xs mt-1">per barrel &middot; updated {brent_upd}</p>')
    else:
        brent_html = ('<p class="serif text-3xl font-bold text-gray-300">Unavailable</p>'
                      '<p class="text-gray-500 text-xs mt-1">price feed did not respond on this build</p>')

    body += (
        '<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">'
        '<div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">'
        '<p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Live benchmark</p>'
        '<h3 class="font-bold text-gray-900 mb-3">Brent crude</h3>'
        + brent_html +
        '<p class="text-gray-500 text-xs mt-3 leading-relaxed">Suriname&#8217;s offshore output will be priced '
        'against Brent, so this number drives how much the state eventually collects. Full rates, including '
        'gold and the SRD, are on our ' + ilink("currency.html", "Market Rates page") + '.</p></div>'
        '<div class="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">'
        '<p class="text-xs font-semibold uppercase tracking-widest mb-2" style="color:var(--forest2)">Countdown</p>'
        '<h3 class="font-bold text-gray-900 mb-3">To the start of 2028</h3>'
        f'<p class="serif text-3xl font-bold" style="color:{_OIL}" id="oil-countdown">&mdash;</p>'
        '<p class="text-gray-500 text-xs mt-3 leading-relaxed">First oil is targeted for 2028, without a '
        'published date. This counts down to 1 January 2028, the start of the target year, and will move '
        'if the schedule does.</p></div></div>')

    body += card("At a glance", "The whole picture in one table",
        _table(["", f"Where things stand as of {_asof(meta)}"], [
            ["Producing today", "Onshore only. Around 17,000 barrels a day of heavy Saramacca Crude from "
             "Tambaredjo, Tambaredjo North-West and Calcutta, refined at Tout Lui Faut."],
            ["First offshore oil", "Targeted 2028, from GranMorgu in Block 58."],
            ["Flagship project", "GranMorgu. Two fields, Sapakara South and Krabdagu, 150 km offshore, "
             "developed with subsea wells feeding one FPSO rated at 220,000 barrels a day."],
            ["Who runs it", "TotalEnergies operates with 40%. APA Corporation holds 40%, Staatsolie 20%."],
            ["The gas story", "PETRONAS declared the Sloanea field in Block 52 commercial in late 2025. "
             "A floating LNG development is the leading concept, FID targeted in the second half of 2026, "
             "first gas around 2030."],
            ["Who governs it", "Ministry of Oil, Gas and Environment for policy, Staatsolie for the "
             "acreage and contracts, the National Environment Authority for permits."],
            ["Where the money goes", "Royalty, profit oil, 36% income tax and Staatsolie dividends, "
             "channelled into the Savings and Stabilisation Fund from 2026."],
            ["The open questions", "No local content law yet, an oil fund without a board or investment "
             "framework, and an economy the IMF says is not yet ready for the inflow."],
        ]))

    body += card("What is actually happening", "Construction, not drilling headlines",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The exploration phase that produced the headlines is largely over for Block 58. What is happening '
        'now is heavy industrial construction spread across three continents. The FPSO hull entered dry '
        'dock in China in April 2026 for topsides integration. Subsea trees are being assembled and '
        'tested in Malaysia. The first subsea equipment, part of the acoustic positioning system used to '
        'place hardware precisely on the seabed, landed at the Dr. Jules Sedney Terminal in Paramaribo at '
        'the end of March 2026.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'Development drilling, up to 32 producer and injector wells, is scheduled to start in late 2026 or '
        'early 2027. That is the phase Surinamers will actually see: supply boats, helicopters, a bigger '
        'expat presence and a lot more procurement. The '
        + ilink("granmorgu.html", "GranMorgu project page") + ' tracks it in detail.</p>')

    body += card("Where the oil is", "Blocks, operators and the half that is still unknown",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Suriname&#8217;s offshore is divided into numbered blocks running from the shallow coastal shelf '
        'out to ultra-deep water. Block 58 has the oil under development. Block 52 has the gas. Blocks 53, '
        '64 and 65 are where the next discoveries would most plausibly come from, and the shallow blocks '
        '5 to 10 are the newer, cheaper frontier being tested by Chevron and partners.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'About half the basin now has modern 3D seismic, and in November 2025 Staatsolie opened roughly '
        '60% of offshore acreage, more than 70,000 km2, to nomination at any time under its Open Door '
        'Offering. Full block-by-block detail is on the '
        + ilink("suriname-oil-blocks.html", "blocks and operators page") + '.</p>')

    body += card("What it means at home", "Revenue, jobs and the part nobody has finished",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The fiscal side is genuinely large for a country of roughly 600,000 people. A 6.25% royalty, a '
        '36% income tax fixed for the life of each contract, a share of profit oil and Staatsolie&#8217;s '
        '20% stake give the state something in the order of 60 to 70% of project value after costs. '
        'Staatsolie has pointed to US$1.5 to 2 billion a year at peak.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The jobs picture is more modest than most people expect. Offshore oil is capital-intensive, not '
        'labour-intensive, and the largest contracts are technical and international. The realistic '
        'Surinamese opportunity is in the supply chain and in the trades: welding, marine crew, logistics, '
        'catering, inspection, waste handling. See '
        + ilink("suriname-oil-jobs.html", "jobs and local content") + '.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'The unfinished part is institutional. As of 2026 there is still no local content law, only policy. '
        'The Savings and Stabilisation Fund exists on paper and is meant to receive all mineral revenue '
        'from 2026, but the IMF noted it has no board, no operating procedures and no investment '
        'framework. That gap, not the geology, is what decides whether this goes well.</p>')

    body += card("The other side", "Risks worth stating plainly",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Three risks come up consistently. First, environmental: the Guyana-Suriname basin has strong '
        'currents, and researchers have warned that a significant spill could reach mangroves, '
        'small-scale fisheries and neighbouring coastlines. Suriname&#8217;s coast is largely undeveloped '
        'and its mangrove belt is its own flood defence.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Second, economic concentration. A country that already depends on gold and bauxite history adding '
        'oil has to manage an exchange rate and a spending cycle that resource booms tend to distort. The '
        'IMF has used the phrase resource curse in its Suriname commentary and tied the outcome to '
        'completing the fiscal framework before the money arrives.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'Third, timing. First oil in 2028 is a target under a fixed-price global supply chain. FPSO '
        'projects slip. So do gas FIDs. Treat every forward date on this site as an operator target.</p>')

    # Live news
    oil_articles = ctx.get("oil_articles") or []
    if oil_articles:
        cards_html = "\n".join(ctx["news_card_html"](a, eager=False) for a in oil_articles[:9])
        news_block = ('<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-4">'
                      + cards_html + '</div>'
                      '<a href="news.html#oil" class="inline-block px-5 py-2.5 rounded-full text-sm '
                      f'font-semibold text-white" style="background:{_OIL}">All oil &amp; gas headlines</a>')
    else:
        news_block = ('<p class="text-gray-500 text-sm">The feed did not return articles on this build. '
                      'The full archive is on the ' + ilink("news.html", "news page") + '.</p>')
    body += ('<h2 class="serif text-2xl font-bold text-gray-900 mb-5 mt-2">Latest oil and gas news</h2>'
             + news_block + '<div class="mb-8"></div>')

    body += _sources_block(meta)

    tail = ("""
<script>
(function(){
  var el = document.getElementById('oil-countdown');
  if (!el) return;
  var target = new Date('2028-01-01T00:00:00-03:00').getTime();
  function tick(){
    var d = target - Date.now();
    if (d <= 0) { el.textContent = '2028'; return; }
    var days = Math.floor(d / 86400000);
    var hrs  = Math.floor(d % 86400000 / 3600000);
    el.textContent = days.toLocaleString('en-US') + ' days, ' + hrs + ' h';
  }
  tick(); setInterval(tick, 60000);
})();
</script>""")

    return _page(
        ctx, "oilgas",
        "Suriname Oil and Gas: Blocks, GranMorgu, Contracts and First Oil",
        "Everything about Suriname&#8217;s oil and gas sector in one place: the GranMorgu project, "
        "offshore blocks and operators, production sharing contracts and fiscal terms, the Ministry of "
        "Oil, Gas and Environment, jobs and local content, and the road to first oil in 2028.",
        "oil-and-gas.html",
        "The industry reshaping Suriname",
        "Suriname Oil &amp; Gas",
        "No offshore barrel has been produced yet. Here is exactly where the sector stands, who controls "
        "it, and what happens between now and first oil.",
        body, faq=faq, tail=tail)


# ═══════════════════════════════════════════════════════════════════════════
# 2. BLOCKS, OPERATORS, DISCOVERIES
# ═══════════════════════════════════════════════════════════════════════════
def _build_blocks(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("How many offshore blocks does Suriname have?",
         "Suriname&#8217;s offshore is divided into dozens of numbered blocks stretching from the shallow "
         "coastal shelf out past 3,000 metres of water. Only a minority are under contract. In November "
         "2025 Staatsolie put roughly 60% of the offshore area, over 70,000 km2, back on offer through "
         "its Open Door Offering."),
        ("Which block has the oil?",
         "Block 58, operated by TotalEnergies. The Sapakara South and Krabdagu fields inside it are the "
         "basis of the GranMorgu development, holding more than 750 million barrels."),
        ("Which block has the gas?",
         "Block 52, operated by PETRONAS. The Sloanea field was declared commercial in late 2025, and "
         "cumulative discoveries in the block exceed one billion barrels of oil equivalent."),
        ("Is ExxonMobil in Suriname?",
         "ExxonMobil has held interests in Suriname acreage, including a past position in Block 52, but "
         "it is not the operator of any of the blocks now heading toward development. The operators "
         "driving activity in 2026 are TotalEnergies, PETRONAS, APA Corporation, Chevron and Shell."),
        ("How deep is the water?",
         "It varies enormously. The shallow offshore blocks sit in tens of metres. Block 58 and Block 52 "
         "are deepwater, roughly 100 to 1,000 metres and beyond, and the acreage on offer runs into "
         "ultra-deep water past 3,000 metres."),
    ]

    blocks = D["blocks"]
    rows = [[b["block"],
             b["water"],
             b["operator"],
             b["partners"],
             f'<span class="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-gray-100 '
             f'text-gray-700 whitespace-nowrap">{b["status"]}</span>']
            for b in blocks]

    body = _callout(
        "How to read this page",
        "A block is a numbered area of seabed that the state licenses out. One company is the operator, "
        "meaning it runs the work; the others simply pay their share and take their share. Staatsolie can "
        "take up to 20% of any development once it is proven. Nothing on this page is producing yet.",
        tone="oil")

    body += card("The map in table form", "Every contracted block, who runs it and what stage it is at",
                 _table(["Block", "Water", "Operator", "Partners", "Stage"], rows))

    body += card("Block detail", "What is in each one",
        "".join(
            '<div class="border-t border-gray-100 py-4 first:border-t-0 first:pt-0">'
            f'<p class="font-bold text-gray-900 text-sm">{b["block"]}'
            f'<span class="font-normal text-gray-400"> &middot; {b["water"]}</span></p>'
            f'<p class="text-gray-700 text-sm leading-relaxed mt-1">{b["note"]}</p></div>'
            for b in blocks))

    wells = D["wells"]
    wrows = [[w["name"], w["block"], w["year"], w["operator"], w["result"]] for w in wells]
    body += card("The discovery record", "The wells that built the story",
        '<p class="text-gray-700 text-sm leading-relaxed mb-4">'
        'Suriname was drilled unsuccessfully for decades. What changed was the Guyana side of the basin '
        'proving the play in 2015, which redirected seismic interpretation and led straight to Maka '
        'Central in 2020. Success rates since have been mixed, which is normal for a frontier basin.</p>'
        + _table(["Well", "Block", "Year", "Operator", "Result"], wrows))

    players = D["players"]
    body += card("Who is here", "Operators, partners and the companies building the hardware",
        "".join(
            '<div class="border-t border-gray-100 py-4 first:border-t-0 first:pt-0">'
            f'<p class="font-bold text-gray-900 text-sm">{p["n"]}'
            f'<span class="font-normal text-gray-400"> &middot; {p["c"]}</span></p>'
            f'<p class="text-xs font-semibold mb-1" style="color:{_OIL}">{p["r"]}</p>'
            f'<p class="text-gray-700 text-sm leading-relaxed">{p["d"]}</p>'
            f'<a href="{p["u"]}" rel="nofollow noopener" target="_blank" '
            'class="text-xs font-semibold hover:underline" style="color:var(--forest2)">Company site</a></div>'
            for p in players))

    body += card("What is still on offer", "The Open Door Offering",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Historically Suriname licensed acreage through timed bid rounds: the Shallow Offshore round of '
        '2020-2021, the Demerara round of 2022-2023, and a second shallow offshore round after that. In '
        'November 2025 Staatsolie switched approach and launched an Open Door Offering covering roughly '
        '60% of the offshore area, more than 70,000 km2, from shallow water to ultra-deep.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Under an open door, companies nominate the blocks they want, propose their own work programme and '
        'can choose between a full production sharing contract, a joint study or a technical evaluation '
        'agreement. Staatsolie took the offering on the road, including a Houston roadshow in May 2026. '
        'A separate near-shore seismic survey announced in 2026 covers the waters between the Guyanese and '
        'French Guianese borders.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'The mechanics of what a bidder actually signs are on the '
        + ilink("suriname-oil-contracts.html", "contracts and fiscal terms page") + '.</p>')

    body += _sources_block(D["meta"])

    return _page(
        ctx, "oilblocks",
        "Suriname Offshore Blocks and Operators: Block 58, Block 52 and the Rest",
        "Block-by-block guide to oil and gas offshore Suriname: operators, partners, water depths, "
        "discovery wells and what is still open for licensing under the Open Door Offering.",
        "suriname-oil-blocks.html",
        "Who holds what, and where",
        "Blocks &amp; Operators",
        "Suriname&#8217;s offshore is a grid of numbered blocks. Here is who runs each one, what they have "
        "found and which acreage is still open.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# 3. GRANMORGU
# ═══════════════════════════════════════════════════════════════════════════
def _build_granmorgu(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("What does GranMorgu mean?",
         "It is Sranan Tongo, and it works two ways. Read as words it means new dawn, which is how "
         "TotalEnergies and the government present the project. It is also the local name for the "
         "goliath grouper, a heavy fish of Suriname&#8217;s coastal waters that carries associations of "
         "strength and long life. Our "
         "<a href='sranan-tongo-dictionary.html' style='color:var(--forest2)' class='font-semibold'>"
         "Sranan Tongo dictionary</a> has more of the language."),
        ("When will GranMorgu produce first oil?",
         "The target is 2028. As of mid-2026 the project is in construction: the FPSO hull is in dry dock "
         "in China, subsea trees are being built in Malaysia and development drilling is scheduled to "
         "start in late 2026 or the first quarter of 2027."),
        ("How much oil will GranMorgu produce?",
         "The FPSO is designed for 220,000 barrels a day, with gas processing capacity of 500 million "
         "cubic feet a day. The development holds more than 750 million barrels of oil, and "
         "TotalEnergies has said improved seismic could take that toward 800 million."),
        ("Who owns GranMorgu?",
         "TotalEnergies operates with 40%, APA Corporation holds 40% and Staatsolie holds 20% after "
         "exercising its back-in right. Staatsolie&#8217;s share cost about US$2.4 billion, funded with a "
         "US$516 million bond and a US$1.6 billion syndicated loan from 18 institutions."),
        ("Will there be flaring?",
         "The design targets minimal routine flaring. Associated gas is reinjected rather than burned, and "
         "the FPSO uses an all-electric drive, which is the main reason TotalEnergies presents GranMorgu "
         "as a lower-emission development."),
        ("Where exactly is it?",
         "About 150 kilometres off the Suriname coast in Block 58, developing the Sapakara South and "
         "Krabdagu fields. Nothing is visible from shore."),
    ]

    body = _callout(
        "What GranMorgu is",
        "One floating vessel, permanently moored 150 km offshore, connected by pipelines to wells drilled "
        "into the seabed below. Oil arrives at the vessel, is separated from gas and water, is stored in "
        "the hull, and is offloaded to tankers every few days. There is no platform, no pipeline to shore "
        "and no refinery attached. That is the entire project in one paragraph.",
        tone="oil")

    body += card("The numbers", "GranMorgu specification",
        _table(["", ""], [
            ["Fields", "Sapakara South and Krabdagu, Block 58"],
            ["Distance offshore", "About 150 km"],
            ["Investment at FID", "About US$10.5 billion, sanctioned October 2024"],
            ["Resource", "More than 750 million barrels; TotalEnergies has cited up to 800 million with better seismic"],
            ["FPSO capacity", "220,000 barrels of oil a day"],
            ["Gas processing", "500 million cubic feet a day, reinjected rather than flared"],
            ["Topside weight", "About 50,000 tonnes"],
            ["Wells planned", "Up to 32, producers and water or gas injectors"],
            ["Ownership", "TotalEnergies 40% (operator), APA Corporation 40%, Staatsolie 20%"],
            ["Staatsolie&#8217;s cost", "About US$2.4 billion, financed with a US$516 million bond and a US$1.6 billion syndicated loan"],
            ["First oil target", "2028"],
        ], first_col_bold=True))

    body += card("How it works", "From seabed to tanker in five steps",
        _steps([
            ("Drill and complete the wells",
             "A drillship sinks wells into the reservoir roughly two kilometres below the seabed and "
             "installs a subsea tree, a valve stack, on top of each one. Up to 32 wells are planned, "
             "including injectors that push water or gas back down to keep reservoir pressure up."),
            ("Connect them",
             "Flowlines, risers and umbilicals link the trees back to the vessel. Saipem holds the subsea "
             "contract, worth around US$1.9 billion. Placing this hardware accurately is why an acoustic "
             "positioning system was shipped to Paramaribo before anything else."),
            ("Separate on board",
             "What arrives at the FPSO is a mixture of oil, gas, water and sand. The topsides, about "
             "50,000 tonnes of processing equipment, split it. Water is treated, gas is reinjected, oil "
             "is stabilised."),
            ("Store in the hull",
             "The vessel is its own tank farm. Crude accumulates in the hull until a shuttle tanker comes "
             "alongside."),
            ("Offload and sell",
             "Tankers take the crude to refineries abroad and it is priced against Brent. This is the "
             "point at which Suriname earns royalty and profit oil."),
        ]))

    body += card("Who builds what", "The contractor map",
        _table(["Scope", "Company", "Detail"], [
            ["FPSO", "SBM Offshore with Technip Energies",
             "Fast4Ward-style hull, all-electric drive. Hull entered dry dock at the COSCO yard in China in April 2026 for topsides integration."],
            ["Subsea installation", "Saipem", "Approximately US$1.9 billion scope covering flowlines, risers and installation."],
            ["Subsea production systems", "TechnipFMC",
             "Christmas trees and related hardware, assembled and system-integration tested in Malaysia."],
            ["Drilling", "Contracted by TotalEnergies",
             "TotalEnergies has signalled a more integrated well-construction contracting model for Suriname."],
            ["Workforce pipeline", "STS joint venture",
             "SBM Offshore, Technip Energies and Suriname run a 19-month graduate programme; the first Surinamese cohort trained in Kuala Lumpur."],
        ]))

    tl_rows = [
        ["January 2026", "TotalEnergies Suriname puts the development above 750 million barrels and says better seismic could reach 800 million."],
        ["February 2026", "TotalEnergies signals a more integrated contracting model for the Suriname wells."],
        ["March 2026", "Rystad Energy details the 50,000-tonne topside and 500 mmcf/d gas processing. Subsea trees 1 to 4 complete, 5 to 7 in assembly."],
        ["Late March 2026", "First subsea equipment lands in Suriname: components of the long baseline acoustic positioning system arrive at the Dr. Jules Sedney Terminal, Paramaribo."],
        ["April 2026", "The FPSO hull enters dry dock in China ahead of topsides integration."],
        ["May 2026", "TechnipFMC and TotalEnergies complete stack-up and system integration testing of a production tree in Malaysia. Six Surinamese graduates on the STS programme meet SBM Offshore leadership in Kuala Lumpur."],
        ["Late 2026 to Q1 2027", "Development drilling scheduled to begin. Offshore installation activity ramps up."],
        ["2027", "FPSO sail-away, mooring, hook-up and commissioning offshore Suriname."],
        ["2028", "Target for first oil and ramp-up toward 220,000 barrels a day."],
    ]
    body += card("Progress log", "What has actually happened, and what is next",
        _table(["When", "Milestone"], tl_rows))

    body += card("What could go wrong", "The honest version",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'FPSO projects are among the most schedule-sensitive things in heavy industry. A yard delay in '
        'China, a problem during hook-up, or slower-than-planned development drilling all push first oil '
        'to the right. Historically, deepwater projects of this size slip more often than they arrive '
        'early.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'There is also reservoir risk. Sapakara South and Krabdagu are well appraised, but production '
        'behaviour is only truly known once the field is flowing, and the ramp to plateau can be slower '
        'than the design rate suggests.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'And there is spill risk. GranMorgu sits in a basin with strong currents, upstream of mangrove '
        'coastline and small-scale fisheries. The National Oil Spill Response Plan is being updated and '
        'the 2026 ministry budget allocates funds for offshore risk analysis, which is an acknowledgement '
        'that the capability is not fully in place yet. More on the institutional side is on the '
        + ilink("suriname-oil-government.html", "who governs it page") + '.</p>')

    body += _sources_block(D["meta"], extra=[
        {"label": "TotalEnergies: FID press release for GranMorgu",
         "url": "https://totalenergies.com/news/press-releases/suriname-totalenergies-announces-final-investment-decision-granmorgu"},
    ])

    return _page(
        ctx, "granmorgu",
        "GranMorgu: Suriname&#8217;s First Offshore Oil Project Explained",
        "The GranMorgu development in Block 58: the FPSO, the 220,000 barrel a day design, who owns it, "
        "who builds it, the construction progress so far and the road to first oil in 2028.",
        "granmorgu.html",
        "Block 58, 150 km offshore",
        "The GranMorgu Project",
        "US$10.5 billion, one floating production vessel, up to 32 wells and a 2028 target. Here is how "
        "it is being built.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# 4. TIMELINE & ROADMAP
# ═══════════════════════════════════════════════════════════════════════════
def _build_timeline(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("When did Suriname find oil?",
         "Oil was first found in 1928 in Nickerie district, and again in 1965 in Saramacca, where a crew "
         "drilling for drinking water hit heavy oil in a school yard. Commercial onshore production "
         "started at Tambaredjo on 25 November 1982. The offshore story began in 2020, when Apache and "
         "Total hit oil at Maka Central-1 in Block 58."),
        ("When is first oil in Suriname?",
         "2028 is the target for GranMorgu, the first offshore development. There is no published date "
         "within that year. Onshore production has been running continuously since 1982."),
        ("When will Suriname produce gas?",
         "Around 2030, if PETRONAS sanctions the Sloanea development in Block 52. A final investment "
         "decision was targeted for the second half of 2026, with floating LNG the leading concept."),
        ("What happens after first oil?",
         "GranMorgu ramps toward 220,000 barrels a day, and the IMF projects Suriname&#8217;s crude output "
         "peaking around 73 million barrels in 2030 and 2031. Beyond that depends on new final investment "
         "decisions and on tiebacks to the existing vessel."),
    ]

    tl = D["timeline"]
    dots = {"past": "#9ca3af", "now": _OIL, "future": "var(--forest2)"}
    items = []
    for ev in tl:
        colour = dots.get(ev.get("k", "past"), "#9ca3af")
        badge = ""
        if ev.get("k") == "now":
            badge = ('<span class="ml-2 inline-block px-2 py-0.5 rounded-full text-xs font-semibold '
                     f'text-white align-middle" style="background:{_OIL}">now</span>')
        items.append(
            '<div class="relative pl-8 pb-7 border-l-2 border-gray-200 last:border-l-0 last:pb-0">'
            f'<span class="absolute left-0 top-1 -translate-x-1/2 w-3 h-3 rounded-full" '
            f'style="background:{colour}"></span>'
            f'<p class="text-xs font-bold uppercase tracking-widest mb-1" style="color:{_OIL}">{ev["y"]}</p>'
            f'<p class="font-bold text-gray-900 text-sm mb-1">{ev["t"]}{badge}</p>'
            f'<p class="text-gray-700 text-sm leading-relaxed">{ev["d"]}</p></div>')

    body = _callout(
        "A hundred years in one column",
        "Suriname has had oil under it the whole time. Nickerie in 1928, a schoolyard in Saramacca in "
        "1965, then decades of small onshore production. What changed in 2015 was the Guyana side of the "
        "same basin proving the deepwater play, which redirected the seismic interpretation that led "
        "directly to the 2020 discoveries. Everything since has been engineering and paperwork.",
        tone="oil")

    body += card("The full timeline", "From Nickerie 1928 to first gas",
                 '<div class="pt-2">' + "".join(items) + '</div>')

    body += card("What has to happen before 2028", "The critical path",
        _steps([
            ("Finish the FPSO",
             "Topsides integration in China, then commissioning. This is the long pole: the vessel has to "
             "be complete enough to sail before anything else matters."),
            ("Drill the wells",
             "Up to 32 development wells starting late 2026 or early 2027. Each one takes weeks, and the "
             "campaign runs in parallel with vessel construction."),
            ("Install subsea infrastructure",
             "Trees, flowlines, risers and umbilicals placed and tested on the seabed. Saipem's scope."),
            ("Sail, moor and hook up",
             "The vessel transits from Asia, is moored on location and is connected to the subsea system."),
            ("Commission and start up",
             "Systems are proven, wells are opened, and production ramps. First oil is the moment stabilised "
             "crude reaches the storage tanks."),
        ]))

    body += card("What could move the dates", "Slip risk, plainly stated",
        _table(["Risk", "Effect"], [
            ["Yard or commissioning delay", "The single most common cause of FPSO slippage. Pushes first oil directly."],
            ["Development drilling pace", "Fewer wells ready at start-up means a slower ramp rather than a later start."],
            ["Sloanea FID timing", "If the Block 52 gas decision slips past 2026, first gas moves out from around 2030."],
            ["Oil price", "A sustained fall changes appetite for the next final investment decision, not GranMorgu itself, which is already sanctioned."],
            ["Institutional readiness", "Does not delay production, but the IMF has argued it determines whether the revenue is handled well."],
        ]))

    body += card("After first oil", "What the forecasts assume",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The IMF projects roughly 55% GDP growth in the first full year of production and sees crude '
        'output peaking near 73 million barrels in 2030 and 2031 before declining. Staatsolie has pointed '
        'to government oil revenue of US$1.5 to 2 billion a year at peak, with something in the order of '
        'US$7 billion across the first five production years.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'Those numbers assume one project. Extending the plateau depends on tiebacks and on new '
        'sanctions from the blocks covered on the '
        + ilink("suriname-oil-blocks.html", "blocks page") + '. Where the money is supposed to land is on '
        'the ' + ilink("suriname-oil-government.html", "institutions page") + '.</p>')

    body += _sources_block(D["meta"])

    return _page(
        ctx, "oiltimeline",
        "Suriname Oil Timeline: From 1928 to First Oil in 2028",
        "The full timeline of oil and gas in Suriname: the 1928 Nickerie find, Staatsolie&#8217;s founding in 1980, "
        "onshore production from 1982, the 2020 offshore discoveries, the 2024 GranMorgu FID and the "
        "roadmap to first oil in 2028 and first gas around 2030.",
        "suriname-oil-timeline.html",
        "From 1928 to first oil",
        "Timeline &amp; Roadmap",
        "A hundred years from the first oil find in Nickerie to the first offshore barrel, and the "
        "critical path between now and 2028.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CONTRACTS, LICENSING, FISCAL TERMS
# ═══════════════════════════════════════════════════════════════════════════
def _build_contracts(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("Does Suriname sell its oil to foreign companies?",
         "No. It licenses the right to produce it under a production sharing contract. The state keeps "
         "ownership of the resource, the company funds and carries the risk, and production is split "
         "between them after costs."),
        ("What royalty does Suriname charge?",
         "6.25% of gross production, taken before anything else. On top of that sits cost recovery, a "
         "profit oil split and a 36% income tax fixed for the life of the contract."),
        ("What is Suriname&#8217;s government take?",
         "Staatsolie puts it at 60 to 70% of project value after costs, depending on the oil price. That "
         "counts royalty, profit oil and income tax, and does not include the value of Staatsolie&#8217;s "
         "own equity stake."),
        ("How does Suriname&#8217;s deal compare to Guyana&#8217;s?",
         "Suriname&#8217;s terms are generally regarded as tougher for the contractor than Guyana&#8217;s "
         "2016 Stabroek agreement, mainly because Guyana&#8217;s carried a 2% royalty and no separate "
         "corporate income tax on the contractors. Suriname charges 6.25% royalty plus 36% income tax and "
         "takes an equity stake through Staatsolie."),
        ("How does a company get a block in Suriname?",
         "Since November 2025, through the Open Door Offering: a company nominates the acreage it wants "
         "at any time, proposes a work programme and negotiates with Staatsolie. Before that, acreage was "
         "awarded in timed bid rounds."),
        ("Are Suriname&#8217;s petroleum contracts public?",
         "Model contract terms and headline fiscal parameters are published by Staatsolie, but individual "
         "signed contracts are not routinely published in full. Contract transparency is one of the "
         "governance points raised by observers as the sector scales up."),
    ]

    body = _callout(
        "The one thing to understand",
        "Suriname does not sell its oil. It signs a production sharing contract, keeps ownership of the "
        "resource, and lets a company spend its own money to find and produce it in exchange for a defined "
        "share. If the company finds nothing, Suriname has lost nothing but time.",
        tone="oil")

    body += card("The waterfall", "How one barrel gets divided",
        _steps([
            ("Royalty comes off the top",
             "6.25% of gross production goes to the state before any costs are recovered. This is the "
             "portion Suriname earns even on a marginal project."),
            ("The company recovers its costs",
             "Between 75 and 80% of what is left is available as cost oil, used to pay back exploration, "
             "development and production spending. In the early years this is where most of the barrel goes."),
            ("The rest is profit oil, and it is shared",
             "Whatever remains after royalty and cost oil is split between the contractor and Staatsolie "
             "on a negotiated scale."),
            ("The company pays income tax",
             "36%, fixed for the term of the contract so the fiscal terms cannot be changed under the "
             "contractor mid-project."),
            ("Staatsolie can take equity",
             "Up to 20% of a development, paid for by carrying 20% of costs from that point forward. It "
             "did exactly this on GranMorgu, at a cost of about US$2.4 billion."),
        ]))

    body += card("Fiscal terms", "The headline numbers",
        _table(["Term", "Suriname", "Note"], [
            ["Royalty", "6.25% of gross production", "Paid regardless of profitability."],
            ["Cost oil ceiling", "75 to 80% after royalty", "The share available to repay costs each period."],
            ["Profit oil", "Negotiated split of the remainder", "Between contractor and Staatsolie."],
            ["Income tax", "36%, fixed for the contract term", "Stability is part of what attracts bidders."],
            ["State participation", "Staatsolie up to 20%", "A back-in right exercised after a discovery is proven."],
            ["Overall government take", "About 60 to 70% after costs", "Varies with the oil price."],
            ["Contract type", "Production sharing contract", "The state retains ownership of the resource."],
            ["Typical term", "Up to 30 years", "The shallow offshore blocks 6 and 8 were signed on 30-year PSCs."],
        ]))

    body += card("Licensing history", "How the acreage was handed out",
        _table(["Round", "When", "Result"], [
            ["Shallow Offshore Bid Round", "2020 to 2021",
             "Blocks 5, 6, 7 and 8 awarded. Chevron took 5 and 7; TotalEnergies and QatarEnergy took 6 and 8. Staatsolie holds interests through Paradise Oil Company."],
            ["Demerara Bid Round", "November 2022 to May 2023",
             "Blocks 63, 64 and 65. PETRONAS on 63; TotalEnergies, QatarEnergy and PETRONAS on 64; Shell&#8217;s BG International with QatarEnergy on 65."],
            ["Shallow Offshore Round 2", "Following the Demerara round",
             "Eleven further shallow-water blocks offered; blocks 9 and 10 went to PETRONAS and Chevron."],
            ["Open Door Offering", "From November 2025",
             "Roughly 60% of offshore acreage, over 70,000 km2, open to nomination at any time. Promoted internationally including a Houston roadshow in May 2026."],
        ]))

    body += card("How to actually bid", "The process, in order",
        _steps([
            ("Look at the data",
             "Staatsolie licenses seismic and well data for the basin. About half of it now has modern 3D "
             "coverage, and a near-shore survey covering the waters between the Guyanese and French "
             "Guianese borders was announced in 2026."),
            ("Nominate the acreage",
             "Under the Open Door Offering a company proposes the blocks it wants rather than waiting for "
             "a round to open."),
            ("Choose the instrument",
             "A full production sharing contract, a joint study agreement, or a technical evaluation "
             "agreement if the company wants to look before committing."),
            ("Propose a work programme",
             "Commitments are typically expressed as seismic and a minimum number of wells within a "
             "defined exploration period."),
            ("Negotiate and sign with Staatsolie",
             "Staatsolie negotiates on behalf of the state, with the profit oil split as the main "
             "commercial variable. Royalty and income tax are fixed."),
        ]))

    body += card("The legal stack", "Which law does what",
        _defs([
            ("Petroleum Act 1990",
             "The backbone. It gives Staatsolie the exclusive right to explore for and produce "
             "hydrocarbons in Suriname, and to contract that right out to others. It also carries the tax "
             "provisions applied to petroleum operations."),
            ("Production Sharing Contracts",
             "The operational rulebook for each block, including cost recovery, profit oil, work "
             "commitments, decommissioning and the preference given to local suppliers and workers."),
            ("Environmental Framework Act (Milieu Raamwet)",
             "Establishes the National Environment Authority (NMA) and the permitting regime that "
             "offshore operations sit under."),
            ("Savings and Stabilisation Fund law",
             "Directs mineral revenue into a sovereign fund. From 2026 all mineral revenue is meant to be "
             "deposited there and managed independently."),
            ("Local content: policy, not yet law",
             "Preference for local suppliers and workers is written into the petroleum law and the PSCs, "
             "but Suriname has no dedicated local content act. A national local content programme began "
             "in 2026 and legislation has been promised. See "
             "<a href='suriname-oil-jobs.html' class='font-semibold' style='color:var(--forest2)'>jobs and "
             "local content</a>."),
        ]))

    body += _sources_block(D["meta"], extra=[
        {"label": "Staatsolie: bidding and fiscal terms",
         "url": "https://www.staatsolie.com/en/shi/"},
    ])

    return _page(
        ctx, "oilcontracts",
        "Suriname Petroleum Contracts and Fiscal Terms: PSCs, Royalty and Bid Rounds",
        "How Suriname licenses its oil and gas: production sharing contracts, the 6.25% royalty, cost oil "
        "and profit oil, the 36% income tax, Staatsolie&#8217;s 20% back-in right, past bid rounds and the "
        "Open Door Offering.",
        "suriname-oil-contracts.html",
        "How one barrel gets divided",
        "Contracts &amp; Fiscal Terms",
        "Royalty, cost oil, profit oil, income tax and a state back-in right. How one Surinamese barrel "
        "actually gets divided.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# 6. INSTITUTIONS, POLICY, THE OIL FUND
# ═══════════════════════════════════════════════════════════════════════════
def _build_government(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("Does Suriname have a Ministry of Oil and Gas?",
         "Yes. The Ministry of Oil, Gas and Environment (Ministerie van Olie, Gas en Milieu, OGM) was "
         "created in 2025 and is led by Patrick Brunings, a petroleum engineer who spent more than 25 "
         "years at Staatsolie. It sits at Swalbergstraat 7 in Paramaribo and also carries the "
         "environment and spatial planning portfolios previously held by the ROM ministry."),
        ("Who regulates oil in Suriname?",
         "Responsibility is split. The Ministry of Oil, Gas and Environment sets policy and legislation. "
         "Staatsolie manages the acreage, negotiates contracts and holds state equity. The National "
         "Environment Authority handles environmental permitting. The Ministry of Finance and Planning "
         "and the Savings and Stabilisation Fund handle the revenue."),
        ("What is the Savings and Stabilisation Fund?",
         "Suriname&#8217;s sovereign wealth fund, the Spaar- en Stabilisatiefonds Suriname. From 2026 all "
         "mineral revenue is meant to be deposited into it and managed independently, to smooth price "
         "swings and save for future generations. The IMF noted in early 2026 that the fund still lacked "
         "a board, operating procedures and an investment framework."),
        ("Is Staatsolie both regulator and player?",
         "Effectively yes, and it is the structural question people raise. Staatsolie markets the "
         "acreage, negotiates the contracts and takes an equity stake in the projects it licensed. The "
         "creation of a separate oil and gas ministry in 2025 was partly a move toward splitting policy "
         "from commercial operations."),
        ("What has the IMF said about Suriname and oil?",
         "In its 2025 Article IV consultation, concluded in February 2026, the IMF described 2026 and "
         "2027 as a transition period in which Suriname must finish regulations and strengthen "
         "institutions before production starts, warned about the risk of a resource curse without "
         "urgent policy measures, and called for meaningful fiscal adjustment in 2026."),
    ]

    body = _callout(
        "Four institutions decide how this goes",
        "A ministry that writes the policy, a state company that signs the contracts and owns 20% of the "
        "flagship project, an environment authority that issues the permits, and a sovereign fund that is "
        "supposed to hold the money. Three of the four are functioning. The fourth is the one the IMF "
        "keeps writing about.",
        tone="oil")

    body += card("Who does what", "The division of responsibility",
        _table(["Body", "Role", "Status in 2026"], [
            ["Ministry of Oil, Gas and Environment (OGM)",
             "Policy, legislation, national oil and gas policy plan, oil spill preparedness, environment and spatial planning",
             "Created 2025. Minister Patrick Brunings. 2026 budget includes SRD 3.393 billion for investment in Staatsolie, plus allocations for local content policy and for updating the National Oil Spill Response Plan."],
            ["Staatsolie Maatschappij Suriname N.V.",
             "Resource manager, licensing counterparty, state equity holder, onshore producer and refiner",
             "Founded 1980, wholly state owned. Managing Director Annand Jagesar. Holds 20% of GranMorgu."],
            ["National Environment Authority (NMA)",
             "Environmental permitting and enforcement under the Environmental Framework Act",
             "Operational, and still building capacity for offshore-scale oversight."],
            ["Savings and Stabilisation Fund (SSFS)",
             "Receives and invests mineral revenue; smooths price swings; saves for future generations",
             "Legally established. As of early 2026 the IMF reported no board, no operating procedures and no investment framework."],
            ["Ministry of Finance and Planning",
             "Budget, fiscal framework, debt",
             "Under IMF pressure for fiscal adjustment ahead of the revenue inflow."],
            ["Ministry of Natural Resources",
             "Mining, water and energy outside the petroleum portfolio",
             "Still exists separately; oil and gas policy moved to OGM in 2025."],
        ]))

    body += card("The ministry", "Ministerie van Olie, Gas en Milieu",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Suriname did not have a dedicated oil ministry until 2025. Petroleum policy sat with Natural '
        'Resources, and in practice a great deal of it sat with Staatsolie. The new government created '
        'OGM and appointed Patrick Brunings, who had been Exploration and Subsurface Manager in '
        'Staatsolie&#8217;s offshore directorate and holds a master&#8217;s degree in petroleum '
        'engineering.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The ministry also absorbed the environment and spatial planning portfolios, which is why its news '
        'output runs from offshore licensing to biodiversity monitoring and marine litter in the same '
        'month. Its stated 2026 workplan includes a National Oil and Gas Policy Plan, modernisation of '
        'petroleum legislation, a local content policy, and updating the National Oil Spill Response '
        'Plan.</p>'
        + _defs([
            ("Address", "Swalbergstraat 7, Paramaribo"),
            ("Minister", "Patrick Brunings, nominated by the NPS"),
            ("Portfolios", "Oil, gas, environment, spatial planning"),
            ("Public information",
             "<a href='https://gov.sr/ministeries/ministerie-van-olie-gas-en-milieu/' rel='nofollow noopener' "
             "target='_blank' class='font-semibold' style='color:var(--forest2)'>gov.sr ministry page</a>, "
             "including tenders (aanbestedingen), announcements (bekendmakingen) and vacancies"),
        ]))

    body += card("Staatsolie", "The company that is also the system",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Staatsolie was founded on 13 December 1980 and is entirely state owned. Under the Petroleum Act '
        '1990 it holds the exclusive right to explore for and produce hydrocarbons in Suriname, and it '
        'contracts that right out to international companies. It is simultaneously an operating business: '
        'onshore fields, the Tout Lui Faut refinery, power generation and a gold royalty stream.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Recent scale: Staatsolie anticipated total revenue of about US$802 million for 2025 with pre-tax '
        'profit near US$418 million, and contributions to the treasury of roughly US$387 million through '
        'taxes, dividends and royalties. It raised more than US$2 billion in 2025 to fund its GranMorgu '
        'share, through a US$516 million bond and a US$1.6 billion syndicated loan from 18 lenders.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'The structural criticism is straightforward: the entity that markets the acreage and negotiates '
        'the contracts is also a commercial partner in the resulting projects. Splitting policy out into a '
        'separate ministry in 2025 was a partial answer. Contract publication and an independent regulator '
        'are the reforms most often proposed next.</p>')

    body += card("The oil fund", "Where the money is supposed to go",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The Spaar- en Stabilisatiefonds Suriname exists to do two jobs: absorb the swings when oil prices '
        'move, and save part of a finite resource for people who are not born yet. From 2026 all mineral '
        'revenue is supposed to be deposited directly into it and managed independently of the annual '
        'budget.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'That is the design. The IMF&#8217;s 2025 Article IV consultation, concluded in February 2026, '
        'reported that the fund had no board, no operating procedures and no investment framework, and '
        'that implementation was held back by institutional weakness, poor coordination and a shortage of '
        'skilled staff. It framed 2026 and 2027 as a transition window in which the rules have to be '
        'finished before the money arrives.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'This is the single most consequential unresolved item in the sector. The oil will be produced '
        'whether or not the fund works. What the fund decides is who benefits and for how long.</p>')

    body += card("The environmental side", "Permits, spills and the coastline",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Offshore operations are permitted under the Environmental Framework Act through the National '
        'Environment Authority. The ministry&#8217;s 2026 budget carries a specific allocation for '
        'disaster preparedness and oil incident risk management, including updating the National Oil Spill '
        'Response Plan and running risk analyses for offshore activity.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'The concern researchers raise is geographic. Currents in the Guyana-Suriname basin are strong and '
        'run westward, so a significant spill would not stay put: modelling work has flagged risk to '
        'mangroves, small-scale fisheries and the coasts of French Guiana, Guyana and Caribbean states. '
        'Suriname&#8217;s mangrove belt is also its flood defence, which raises the stakes beyond '
        'biodiversity.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'On the emissions side, GranMorgu is designed with gas reinjection and an all-electric FPSO to '
        'minimise routine flaring, which is genuinely better than the regional norm. It does not change '
        'the spill exposure, which is a response-capability question rather than a design question.</p>')

    body += _sources_block(D["meta"], extra=[
        {"label": "IMF Country Report: Suriname 2025 Article IV",
         "url": "https://www.imf.org/en/publications/cr/issues/2026/02/11/suriname-2025-article-iv-consultation-press-release-staff-report-and-statement-by-the-573924"},
    ])

    return _page(
        ctx, "oilgov",
        "Who Governs Suriname&#8217;s Oil: Ministry, Staatsolie and the Oil Fund",
        "The institutions behind Suriname&#8217;s oil and gas sector: the Ministry of Oil, Gas and "
        "Environment, Staatsolie, the National Environment Authority and the Savings and Stabilisation "
        "Fund, plus what the IMF says still needs finishing before 2028.",
        "suriname-oil-government.html",
        "Policy, licensing and the oil fund",
        "Who Governs the Oil",
        "Four institutions decide whether Suriname&#8217;s oil money is handled well. Here is what each "
        "one does and where the gaps are.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# 7. JOBS, LOCAL CONTENT, SUPPLIERS
# ═══════════════════════════════════════════════════════════════════════════
def _build_jobs(ctx, D):
    ilink = ctx["ilink"]
    card  = ctx["hub_card"]

    faq = [
        ("How do I get a job in Suriname&#8217;s oil industry?",
         "There are three realistic routes: apply directly to Staatsolie through its careers portal, get "
         "certified for offshore work through a recognised training provider such as the T-BOSIET course "
         "at the Kersten training facility, or join a contractor already serving the sector. Technical "
         "trades, marine crew and safety-certified staff are in far higher demand than general "
         "applicants."),
        ("How many jobs will offshore oil create in Suriname?",
         "Fewer than most people expect. Offshore production is capital-intensive, not labour-intensive: "
         "an FPSO producing 220,000 barrels a day runs with a crew in the low hundreds, most of them "
         "specialists. The larger and more durable opportunity is onshore, in logistics, fabrication, "
         "catering, marine services, inspection, waste handling and professional services."),
        ("How does my company become a supplier to the oil industry?",
         "Register in the Suriname Supplier Registration Portal (SSRP), which international operators use "
         "to find local vendors, and register in SAP Ariba to supply Staatsolie directly. Expect to be "
         "asked about safety management, insurance, financial standing and quality certification long "
         "before anyone discusses price."),
        ("Does Suriname have a local content law?",
         "No. As of 2026 preference for local suppliers and workers is written into the petroleum law and "
         "into production sharing contracts, and a national local content programme started in 2026, but "
         "there is no dedicated local content act with mandatory targets and enforcement. This is the "
         "sector&#8217;s most-argued gap, particularly compared with Guyana."),
        ("What is the NATIN Oil and Gas programme?",
         "A technical education track at the Natuur Technisch Instituut Suriname, created with Staatsolie, "
         "the Ministry of Education and international operators. The first cohort ran from October 2022 to "
         "October 2024, and a second from February 2024 to mid-2025."),
        ("Do I need English to work in the sector?",
         "Yes, in practice. Operations, safety documentation and contractor communication run in English "
         "even though Dutch is the official language. It is one of the cheapest things a candidate can fix."),
    ]

    body = _callout(
        "Set expectations first",
        "Oil is not a jobs programme. A vessel producing 220,000 barrels a day runs with a crew in the low "
        "hundreds, and most of those roles need years of certified offshore experience. What Suriname "
        "actually gets is procurement: several years of construction, drilling and logistics spending that "
        "flows through Surinamese companies if those companies are registered, certified and insured. "
        "That is where the realistic opportunity sits.",
        tone="oil")

    body += card("Where the work actually is", "Realistic categories for Surinamese firms and workers",
        _table(["Area", "What it involves", "Who it suits"], [
            ["Marine and logistics", "Supply boats, crew transfer, port handling, customs clearance, warehousing",
             "Established logistics and shipping firms with the capital for compliance"],
            ["Fabrication and workshops", "Steel work, welding, pipe spooling, maintenance of equipment onshore",
             "Engineering workshops willing to certify to international standards"],
            ["Catering and camp services", "Feeding offshore and onshore crews, housekeeping, laundry",
             "Food service businesses that can pass an operator safety audit"],
            ["Inspection, testing, calibration", "Non-destructive testing, lifting equipment inspection, metering",
             "Technicians with international certification; a chronic shortage"],
            ["Waste management", "Drilling waste, oily water, hazardous waste handling and disposal",
             "Specialist firms; permits are the barrier, not equipment"],
            ["Security and facilities", "Base security, facility management, transport", "Existing service firms"],
            ["Professional services", "Legal, accounting, tax, HR, translation, environmental studies",
             "Firms that build genuine sector expertise rather than generalists"],
            ["Accommodation and travel", "Long-stay housing, hotels, chartered transport",
             "Paramaribo hospitality; see our " +
             "<a href='hotels.html' class='font-semibold' style='color:var(--forest2)'>hotels page</a>"],
        ]))

    body += card("For companies", "How to become a supplier",
        _steps([
            ("Register in the SSRP",
             "The Suriname Supplier Registration Portal, running since 2019, is the database international "
             "operators search when they need a local vendor. If you are not in it, you are invisible."),
            ("Register in SAP Ariba for Staatsolie",
             "Staatsolie runs its own procurement through Ariba. It is a separate registration from the SSRP."),
            ("Get your safety house in order",
             "An HSE management system, incident records, insurance and evidence of competent staff. This "
             "is what disqualifies most local bidders, well before price is discussed."),
            ("Certify what you can",
             "ISO quality and safety certification, trade certifications for staff, and equipment "
             "inspection records. Certification is the entry ticket to tier-one contracts."),
            ("Partner rather than bid alone",
             "Most successful local entries into a new oil province come through joint ventures with "
             "experienced international service firms, who bring the track record while the local partner "
             "brings presence, labour and permits."),
        ]))

    body += card("For individuals", "Training and entry routes",
        _table(["Route", "What it is", "Where"], [
            ["NATIN Oil &amp; Gas programme",
             "Technical secondary education track built with Staatsolie, the education ministry and "
             "international operators. First cohort 2022 to 2024, second 2024 to 2025.",
             "Natuur Technisch Instituut Suriname"],
            ["T-BOSIET offshore safety",
             "Tropical Basic Offshore Safety Induction and Emergency Training. The baseline certificate "
             "for anyone going offshore, including helicopter escape training.",
             "Kersten training facility, Paramaribo"],
            ["STS graduate programme",
             "A 19-month programme run by the SBM Offshore, Technip Energies and Suriname joint venture, "
             "preparing graduates for FPSO roles. Cohorts have trained in Kuala Lumpur.",
             "STS joint venture"],
            ["Staatsolie careers",
             "Direct recruitment into the state company, from engineering to finance. The portal supports "
             "job alerts.",
             "staatsolie.com careers"],
            ["Vocational partnership",
             "Government, Staatsolie and TotalEnergies announced joint work on vocational education in "
             "June 2026, aimed at trades feeding the sector.",
             "Announced 2026"],
        ]))

    body += card("The local content gap", "Policy without a law",
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'Preference for Surinamese suppliers and workers is written into the petroleum law and into every '
        'production sharing contract, and Staatsolie runs a Local Content Development programme with '
        'supplier development and workforce projects attached. The government has framed 2026 as the start '
        'of a national local content programme, with the ambition that Surinamese firms and workers hold '
        'materially bigger roles by 2029, and its 2026 budget carries a line for developing the policy.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed mb-3">'
        'What does not exist is a local content act: binding percentage targets, a dedicated enforcement '
        'office and penalties. The policy framework calls for both, and neither has been legislated. '
        'Suriname reaches first oil without the instrument Guyana used, which is the criticism most often '
        'made by local business organisations.</p>'
        '<p class="text-gray-700 text-sm leading-relaxed">'
        'Practically, that means a Surinamese company cannot rely on a quota. It has to be genuinely '
        'competitive on safety, certification and delivery, and it has to be registered before the tender '
        'appears rather than after.</p>')

    body += card("Where to look", "Useful links",
        _defs([
            ("Staatsolie local content",
             "<a href='https://www.staatsolie.com/en/local-content/' rel='nofollow noopener' target='_blank' "
             "class='font-semibold' style='color:var(--forest2)'>staatsolie.com/en/local-content</a>, "
             "including supplier registration and workforce development"),
            ("Staatsolie careers",
             "<a href='https://www.staatsolie.com/en/career/' rel='nofollow noopener' target='_blank' "
             "class='font-semibold' style='color:var(--forest2)'>staatsolie.com/en/career</a>"),
            ("Ministry vacancies and tenders",
             "<a href='https://gov.sr/ministeries/ministerie-van-olie-gas-en-milieu/aanbestedingen/' "
             "rel='nofollow noopener' target='_blank' class='font-semibold' style='color:var(--forest2)'>"
             "OGM aanbestedingen</a> and the ministry vacancies page on gov.sr"),
            ("SEOGS",
             "The Suriname Energy, Oil and Gas Summit, hosted by Staatsolie in Paramaribo, is where most "
             "supplier contact actually happens. The 2026 edition ran 23 to 26 June. Dates for the next "
             "edition appear on our <a href='events.html' class='font-semibold' "
             "style='color:var(--forest2)'>events page</a> when confirmed."),
        ]))

    body += _sources_block(D["meta"], extra=[
        {"label": "Staatsolie: local content and supplier registration",
         "url": "https://www.staatsolie.com/en/local-content/"},
    ])

    return _page(
        ctx, "oiljobs",
        "Suriname Oil and Gas Jobs, Local Content and Supplier Registration",
        "How Surinamese workers and companies get into the oil and gas sector: supplier registration "
        "through the SSRP and SAP Ariba, offshore safety training, the NATIN oil and gas programme, and "
        "where local content policy actually stands in 2026.",
        "suriname-oil-jobs.html",
        "Work, contracts and training",
        "Jobs &amp; Local Content",
        "What the sector actually buys, how to register as a supplier, where to get certified, and why "
        "there is still no local content law.",
        body, faq=faq)


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════
def build_oilgas_pages(ctx):
    """Return {filename: html} for the whole Oil & Gas section."""
    D = _load()
    return {
        "oil-and-gas.html":             _build_hub(ctx, D),
        "suriname-oil-blocks.html":     _build_blocks(ctx, D),
        "granmorgu.html":               _build_granmorgu(ctx, D),
        "suriname-oil-timeline.html":   _build_timeline(ctx, D),
        "suriname-oil-contracts.html":  _build_contracts(ctx, D),
        "suriname-oil-government.html": _build_government(ctx, D),
        "suriname-oil-jobs.html":       _build_jobs(ctx, D),
    }
