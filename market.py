#!/usr/bin/env python3
"""
Explore Suriname - marketplace (classifieds) builder.

    real-estate.html                browse surface, server rendered then hydrated
    real-estate/<slug>/index.html   one ad, build generated, this is the SEO surface
    post-ad.html                    the posting form
    my-ads.html                     the seller's own ads

generate.py calls build_market_pages(ctx) and merges the returned dict into its
own `pages` map. Everything this module needs (PAGE_HEAD helpers, nav, footer,
the CBVS rates) arrives through `ctx`, so there is no circular import.

WHY THE SPLIT: the site is static and rebuilds every ~15 min, so a freshly
posted ad would otherwise be invisible for a quarter of an hour. The browse grid
therefore renders from the build AND re-hydrates from the Worker in the reader's
browser, so new ads and sold badges appear at once. The per-ad pages stay build
generated because they are what Google indexes.

House rules that apply here: no em dashes in visible copy, no decorative emoji,
no <style> blocks emitted from the body.
NOTE: tailwind.config.js must list this file under `content`, and update.yml
must `git add real-estate/`, or the generated pages 404.
"""

import html as html_lib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

MK_API = "https://esr-leaderboard.surinamedomains.workers.dev"

SECTION = "realestate"
SECTION_PATH = "real-estate"

CATS = [
    ("house",      "Houses"),
    ("apartment",  "Apartments"),
    ("land",       "Land and plots"),
    ("commercial", "Commercial"),
    ("room",       "Rooms and studios"),
]
CAT_ONE = {"house": "House", "apartment": "Apartment", "land": "Land",
           "commercial": "Commercial", "room": "Room or studio"}

DISTRICTS = ["Paramaribo", "Wanica", "Commewijne", "Saramacca", "Nickerie",
             "Coronie", "Marowijne", "Para", "Brokopondo", "Sipaliwini"]

CURRENCIES = ["SRD", "USD", "EUR"]
PERIODS = [("month", "per month"), ("week", "per week"), ("day", "per day")]

# Ads that stopped being for sale keep their page for this long so an indexed
# URL does not turn into a 404 the week after it ranked.
DEAD_PAGE_DAYS = 90

_esc = html_lib.escape


def _fetch(path):
    """Read the Worker feed. A build must never fail because the API is down."""
    try:
        req = urllib.request.Request(MK_API + path,
                                     headers={"User-Agent": "ExploreSR-build/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"  WARN marketplace feed unreachable ({e}); building with no ads")
        return []


# ── money ────────────────────────────────────────────────────────────────────

def _rate_table(rates):
    """
    {currency: SRD per unit} from whatever generate.py hands us. Conversion is
    display only and always labelled approximate: these are indicative CBVS
    rates, not what a buyer will actually be quoted.
    """
    out = {"SRD": 1.0}
    for r in (rates or []):
        code = str(r.get("currency", "")).upper()
        if code in ("USD", "EUR"):
            try:
                out[code] = float(str(r.get("sell") or r.get("buy")).replace(",", "."))
            except (TypeError, ValueError):
                pass
    return out


def _amount(n):
    n = float(n or 0)
    return f"{n:,.0f}".replace(",", ".") if n >= 1000 else f"{n:,.0f}"


def _price_main(ad):
    p = f'{ad.get("currency", "SRD")} {_amount(ad.get("price"))}'
    if ad.get("deal") == "rent":
        per = dict(PERIODS).get(ad.get("period") or "month", "per month")
        p += f" {per}"
    return p


def _price_alt(ad, table):
    """One approximate line in the other two currencies, never stored."""
    cur = ad.get("currency", "SRD")
    if cur not in table:
        return ""
    srd = float(ad.get("price") or 0) * table[cur]
    bits = []
    for other in CURRENCIES:
        if other == cur or other not in table:
            continue
        bits.append(f"{other} {_amount(srd / table[other])}")
    return "about " + " or ".join(bits) if bits else ""


# ── contact ──────────────────────────────────────────────────────────────────

def _digits(p):
    return "+" + re.sub(r"\D", "", p or "")


def _wa_href(ad, page_url):
    """
    Prefilled WhatsApp message. The whole point of the marketplace living on the
    site rather than in a Facebook group is that the seller gets a message that
    already says which ad it is about.
    """
    digits = re.sub(r"\D", "", ad.get("phone") or "")
    msg = f'Hi, I saw your ad "{ad.get("title", "")}" on Explore Suriname. Is it still available?\n{page_url}'
    return f"https://wa.me/{digits}?text={urllib.parse.quote(msg)}"


def _contact_block(ad, page_url):
    rows = []
    if ad.get("phone") and ad.get("wa"):
        rows.append(
            f'<a href="{_esc(_wa_href(ad, page_url))}" target="_blank" rel="noopener nofollow" '
            'class="flex items-center justify-center gap-2 w-full py-3 rounded-xl font-semibold text-white '
            'transition hover:opacity-90" style="background:#25D366">'
            '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
            '<path d="M17.5 14.4c-.3-.2-1.7-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.7 1-.9 1.2-.2.2-.3.2-.6.1-.3-.2-1.2-.5-2.3-1.4-.9-.8-1.4-1.7-1.6-2-.2-.3 0-.5.1-.6l.5-.5c.1-.2.2-.3.3-.5 0-.2 0-.4 0-.5 0-.2-.7-1.6-.9-2.2-.2-.5-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5 4.5.7.3 1.2.5 1.7.6.7.2 1.3.2 1.8.1.6-.1 1.7-.7 1.9-1.4.2-.7.2-1.2.2-1.4-.1-.1-.3-.2-.6-.3z"/>'
            '<path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2z"/></svg>'
            'Message on WhatsApp</a>')
    elif ad.get("phone"):
        rows.append(
            f'<a href="tel:{_esc(_digits(ad["phone"]))}" '
            'class="block w-full text-center py-3 rounded-xl font-semibold text-white transition hover:opacity-90" '
            f'style="background:var(--forest)">Call {_esc(ad["phone"])}</a>')
    if ad.get("email"):
        sub = urllib.parse.quote(f'About your ad: {ad.get("title","")}')
        rows.append(
            f'<a href="mailto:{_esc(ad["email"])}?subject={sub}" '
            'class="block w-full text-center py-3 rounded-xl font-semibold border transition hover:bg-gray-50" '
            'style="border-color:var(--forest);color:var(--forest)">Send an email</a>')
    if ad.get("link"):
        rows.append(
            f'<a href="{_esc(ad["link"])}" target="_blank" rel="noopener nofollow" '
            'class="block w-full text-center py-3 rounded-xl font-semibold border transition hover:bg-gray-50" '
            'style="border-color:#DDD4C1;color:var(--ink)">Open the seller&#8217;s page</a>')
    return "".join(f'<div class="mb-2">{r}</div>' for r in rows)


SAFETY = (
    '<div class="rounded-xl p-4 text-sm leading-relaxed" '
    'style="background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12">'
    '<b>Before you pay anything.</b> See the property in person, meet at the address itself, '
    'and check ownership papers at the GLIS before any money changes hands. Explore Suriname '
    'does not handle payments, hold deposits or vet sellers. Nobody with a real listing needs '
    'a deposit to show it to you.</div>'
)


# ── specs ────────────────────────────────────────────────────────────────────

def _specs(ad):
    out = []
    if ad.get("beds"):
        out.append(f'{ad["beds"]} bed' + ("s" if ad["beds"] != 1 else ""))
    if ad.get("baths"):
        out.append(f'{ad["baths"]} bath' + ("s" if ad["baths"] != 1 else ""))
    if ad.get("built_m2"):
        out.append(f'{_amount(ad["built_m2"])} m&#178; built')
    if ad.get("plot_m2"):
        out.append(f'{_amount(ad["plot_m2"])} m&#178; plot')
    if ad.get("furnished"):
        out.append("furnished")
    return out


def _postal(ad):
    """
    Schema.org address. streetAddress is included only when the seller published
    it, so the structured data can never expose more than the page does.
    """
    a = {"@type": "PostalAddress",
         "addressLocality": ad.get("area") or ad.get("district", ""),
         "addressRegion": ad.get("district", ""),
         "addressCountry": "SR"}
    if ad.get("show_addr") and ad.get("address"):
        a["streetAddress"] = ad["address"]
    return a


def _is_dead(ad):
    return ad.get("status") in ("sold", "expired")


# ── cards ────────────────────────────────────────────────────────────────────

def _card(ad, table, eager=False):
    img = (ad.get("images") or [""])[0]
    loading = 'eager" fetchpriority="high' if eager else "lazy"
    href = f'/{SECTION_PATH}/{ad["slug"]}/'
    dead = _is_dead(ad)
    badge = ""
    if dead:
        badge = ('<span class="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold text-white" '
                 'style="background:#3F3F3F">' + ("Sold" if ad.get("status") == "sold" else "No longer listed") + "</span>")
    elif ad.get("seller", {}).get("verified"):
        badge = ('<span class="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold text-white" '
                 'style="background:var(--forest)">Verified seller</span>')
    photo = (f'<img src="{_esc(img)}" alt="{_esc(ad.get("title",""))}" width="400" height="260" '
             f'loading="{loading}" class="w-full h-[200px] object-cover">' if img else
             '<div class="w-full h-[200px] flex items-center justify-center text-sm" '
             'style="background:var(--paper-2);color:#656C63">No photo</div>')
    spec = " &middot; ".join(_specs(ad))
    alt = _price_alt(ad, table)
    return (
        f'<a href="{href}" class="block bg-white rounded-2xl overflow-hidden shadow-sm border '
        f'border-gray-100 hover:shadow-md transition{" opacity-70" if dead else ""}">'
        f'<div class="relative">{photo}{badge}</div>'
        '<div class="p-4">'
        f'<p class="font-bold text-lg" style="color:var(--forest)">{_esc(_price_main(ad))}</p>'
        + (f'<p class="text-xs mb-1" style="color:#656C63">{_esc(alt)}</p>' if alt else '<div class="mb-1"></div>')
        + f'<h3 translate="no" class="font-semibold text-gray-900 leading-snug mb-1">{_esc(ad.get("title",""))}</h3>'
        + (f'<p class="text-sm" style="color:#5A625B">{spec}</p>' if spec else "")
        + f'<p translate="no" class="text-sm mt-1" style="color:#656C63">{_esc(ad.get("district",""))}'
        + (f', {_esc(ad["area"])}' if ad.get("area") else "") + "</p>"
        "</div></a>"
    )


# ── browse surface ───────────────────────────────────────────────────────────

def _build_browse(ctx, ads, table):
    live = [a for a in ads if not _is_dead(a)]
    n = len(live)
    cat_chips = "".join(
        f'<button data-f="cat" data-v="{k}" class="mk-chip px-3 py-1.5 rounded-full text-sm border transition" '
        f'style="border-color:#DDD4C1;color:var(--ink);background:var(--card)">{label}</button>'
        for k, label in CATS)
    dist_opts = "".join(f'<option value="{d}">{d}</option>' for d in DISTRICTS)
    cards = "".join(_card(a, table, eager=(i == 0)) for i, a in enumerate(live[:48]))

    head = ctx["hub_head"](
        "Real estate in Suriname: houses and land for sale and rent",
        "Houses, apartments, land and commercial property for sale and to rent across Suriname. "
        "Prices in SRD, USD and EUR, contact the seller directly on WhatsApp.",
        "real-estate.html",
        faq=[
            ("Is it free to place a property ad?",
             "Yes. Sign in with Google, fill in the form and your ad goes up. The first ad from a new "
             "account is checked by hand, after that your ads appear straight away."),
            ("How long does an ad stay online?",
             "Sixty days. You can renew it with one tap from your own ads page, and mark it sold the "
             "moment it goes, so nobody wastes your time calling about a house that is gone."),
            ("Does Explore Suriname handle the money?",
             "No. You deal with the seller directly. We do not take payments, hold deposits or vet "
             "sellers, so view any property in person and check the papers at the GLIS before you pay."),
        ])

    # Sold and expired ads keep their own page so an indexed URL still resolves,
    # but they are noise in a list somebody is shopping from, so they stay out.
    ads_js  = json.dumps(live[:400], ensure_ascii=False)
    rates_js = json.dumps(table)
    MK_API_JS = json.dumps(MK_API)
    sect = SECTION_PATH
    sect_key = SECTION

    body = f"""
<body class="bg-gray-50 overflow-x-hidden">
{{NAV}}
<div class="cat-hero">
  <div class="max-w-6xl mx-auto px-5 py-10">
    <p class="cat-crumb">Marketplace</p>
    <h1 class="serif text-4xl sm:text-5xl mb-2" style="color:var(--forest);font-weight:400">Real estate in Suriname</h1>
    <p class="text-gray-600 max-w-2xl">Houses, apartments, land and commercial space, for sale and to rent.
      Placed by owners and agencies here in Suriname. You contact the seller yourself.</p>
    <p class="mt-4"><a href="/post-ad.html" class="cat-cta">Place your property ad</a></p>
  </div>
</div>

<main class="max-w-6xl mx-auto px-5 py-8">
  <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 mb-6">
    <div class="flex flex-wrap gap-2 mb-3" role="group" aria-label="For sale or for rent">
      <button data-f="deal" data-v="" class="mk-chip mk-on px-3 py-1.5 rounded-full text-sm border transition">Everything</button>
      <button data-f="deal" data-v="sale" class="mk-chip px-3 py-1.5 rounded-full text-sm border transition" style="border-color:#DDD4C1;color:var(--ink);background:var(--card)">For sale</button>
      <button data-f="deal" data-v="rent" class="mk-chip px-3 py-1.5 rounded-full text-sm border transition" style="border-color:#DDD4C1;color:var(--ink);background:var(--card)">For rent</button>
    </div>
    <div class="flex flex-wrap gap-2 mb-3" role="group" aria-label="Property type">{cat_chips}</div>
    <div class="grid gap-3" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      <label class="block"><span class="block text-xs font-semibold uppercase tracking-wide mb-1" style="color:#5A625B">District</span>
        <select id="f-district" class="w-full rounded-lg border px-3 py-2 text-sm" style="border-color:#DDD4C1"><option value="">Anywhere</option>{dist_opts}</select></label>
      <label class="block"><span class="block text-xs font-semibold uppercase tracking-wide mb-1" style="color:#5A625B">Bedrooms</span>
        <select id="f-beds" class="w-full rounded-lg border px-3 py-2 text-sm" style="border-color:#DDD4C1"><option value="">Any</option><option value="1">1 or more</option><option value="2">2 or more</option><option value="3">3 or more</option><option value="4">4 or more</option></select></label>
      <label class="block"><span class="block text-xs font-semibold uppercase tracking-wide mb-1" style="color:#5A625B">Sort by</span>
        <select id="f-sort" class="w-full rounded-lg border px-3 py-2 text-sm" style="border-color:#DDD4C1"><option value="new">Newest first</option><option value="low">Price, low to high</option><option value="high">Price, high to low</option></select></label>
      <label class="block"><span class="block text-xs font-semibold uppercase tracking-wide mb-1" style="color:#5A625B">Search</span>
        <input id="f-q" placeholder="Kwatta, appartement, perceel" class="w-full rounded-lg border px-3 py-2 text-sm" style="border-color:#DDD4C1"></label>
    </div>
  </div>

  <div id="mk-str" hidden>
    <span data-k="nophoto">No photo</span><span data-k="about">about</span>
    <span data-k="verified">Verified seller</span><span data-k="per">per</span>
    <span data-k="month">month</span><span data-k="week">week</span><span data-k="day">day</span>
    <span data-k="bed">bed</span><span data-k="beds">beds</span>
    <span data-k="bath">bath</span><span data-k="baths">baths</span>
    <span data-k="built">built</span><span data-k="plot">plot</span>
    <span data-k="furnished">furnished</span>
    <span data-k="prop1">property listed</span><span data-k="propN">properties listed</span>
  </div>
  <p id="mk-count" class="text-sm mb-4" style="color:#5A625B">{n} propert{"y" if n == 1 else "ies"} listed</p>
  <div id="mk-grid" class="grid gap-5" style="grid-template-columns:repeat(auto-fill,minmax(270px,1fr))">{cards}</div>
  <p id="mk-empty" class="hidden text-center py-12" style="color:#656C63">Nothing matches those filters yet. Try widening them.</p>

  <div class="mt-10 rounded-2xl p-6 text-center" style="background:var(--paper-2)">
    <h2 class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">Selling or renting out a property?</h2>
    <p class="text-gray-600 mb-4 max-w-xl mx-auto">Put it in front of people already looking for property in Suriname, including Surinamers abroad. Free, and it takes about a minute.</p>
    <a href="/post-ad.html" class="inline-block px-6 py-3 rounded-xl font-semibold text-white" style="background:var(--forest)">Place your ad</a>
  </div>

  <div class="mt-8">{SAFETY}</div>
</main>
{{FOOTER}}
<script>
(function(){{
  var API={MK_API_JS};
  var RATES={rates_js};
  var ADS={ads_js};
  var F={{deal:"",cat:""}};
  var $=function(i){{return document.getElementById(i)}};
  var S=(function(){{
    var m={{}};
    [].forEach.call(document.querySelectorAll("#mk-str [data-k]"),function(e){{m[e.getAttribute("data-k")]=e.textContent}});
    return function(k){{return m[k]||k}};
  }})();
  var esc=function(s){{return String(s==null?"":s).replace(/[&<>"']/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]}})}};
  var amt=function(n){{return Number(n||0).toLocaleString("nl-NL",{{maximumFractionDigits:0}})}};
  function priceMain(a){{
    var p=a.currency+" "+amt(a.price);
    if(a.deal==="rent") p+=" "+S("per")+" "+S(a.period||"month");
    return p;
  }}
  function priceAlt(a){{
    if(!RATES[a.currency]) return "";
    var srd=Number(a.price||0)*RATES[a.currency], out=[];
    ["SRD","USD","EUR"].forEach(function(c){{ if(c!==a.currency&&RATES[c]) out.push(c+" "+amt(srd/RATES[c])); }});
    return out.length?S("about")+" "+out.join(" or "):"";
  }}
  function specs(a){{
    var v=[];
    if(a.beds) v.push(a.beds+" "+S(a.beds!==1?"beds":"bed"));
    if(a.baths) v.push(a.baths+" "+S(a.baths!==1?"baths":"bath"));
    if(a.built_m2) v.push(amt(a.built_m2)+" m\\u00B2 "+S("built"));
    if(a.plot_m2) v.push(amt(a.plot_m2)+" m\\u00B2 "+S("plot"));
    if(a.furnished) v.push(S("furnished"));
    return v.join(" \\u00B7 ");
  }}
  function card(a){{
    var dead=a.status==="sold"||a.status==="expired";
    var img=(a.images&&a.images[0])||"";
    var badge=dead?'<span class="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold text-white" style="background:#3F3F3F">'+(a.status==="sold"?"Sold":"No longer listed")+'</span>'
      :(a.seller&&a.seller.verified?'<span class="absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold text-white" style="background:var(--forest)">'+S("verified")+'</span>':'');
    var photo=img?'<img src="'+esc(img)+'" alt="'+esc(a.title)+'" width="400" height="260" loading="lazy" class="w-full h-[200px] object-cover">'
      :'<div class="w-full h-[200px] flex items-center justify-center text-sm" style="background:var(--paper-2);color:#656C63">'+S("nophoto")+'</div>';
    var alt=priceAlt(a), sp=specs(a);
    return '<a href="/{sect}/'+esc(a.slug)+'/" class="block bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 hover:shadow-md transition'+(dead?' opacity-70':'')+'">'
      +'<div class="relative">'+photo+badge+'</div><div class="p-4">'
      +'<p class="font-bold text-lg" style="color:var(--forest)">'+esc(priceMain(a))+'</p>'
      +(alt?'<p class="text-xs mb-1" style="color:#656C63">'+esc(alt)+'</p>':'<div class="mb-1"></div>')
      +'<h3 translate="no" class="font-semibold text-gray-900 leading-snug mb-1">'+esc(a.title)+'</h3>'
      +(sp?'<p class="text-sm" style="color:#5A625B">'+sp+'</p>':'')
      +'<p class="text-sm mt-1" style="color:#656C63">'+esc(a.district)+(a.area?', '+esc(a.area):'')+'</p>'
      +'</div></a>';
  }}
  function srd(a){{ return Number(a.price||0)*(RATES[a.currency]||1); }}
  function apply(){{
    var q=($("f-q").value||"").toLowerCase().trim();
    var d=$("f-district").value, b=Number($("f-beds").value||0), s=$("f-sort").value;
    var out=ADS.filter(function(a){{
      if(F.deal&&a.deal!==F.deal) return false;
      if(F.cat&&a.category!==F.cat) return false;
      if(d&&a.district!==d) return false;
      if(b&&Number(a.beds||0)<b) return false;
      if(q&&((a.title||"")+" "+(a.descr||"")+" "+(a.area||"")+" "+(a.district||"")).toLowerCase().indexOf(q)<0) return false;
      return a.status==="live";
    }});
    out.sort(function(x,y){{
      if(s==="low") return srd(x)-srd(y);
      if(s==="high") return srd(y)-srd(x);
      return (y.bumped||0)-(x.bumped||0);
    }});
    $("mk-grid").innerHTML=out.map(card).join("");
    $("mk-empty").className=out.length?"hidden":"text-center py-12";
    $("mk-count").textContent=out.length+" "+S(out.length===1?"prop1":"propN");
  }}
  document.querySelectorAll(".mk-chip").forEach(function(btn){{
    btn.addEventListener("click",function(){{
      var f=btn.dataset.f;
      F[f] = F[f]===btn.dataset.v ? "" : btn.dataset.v;
      document.querySelectorAll('.mk-chip[data-f="'+f+'"]').forEach(function(o){{
        var on = (o.dataset.v||"")===(F[f]||"");
        o.classList.toggle("mk-on",on);
        o.style.background = on?"var(--forest)":"var(--card)";
        o.style.color = on?"#fff":"var(--ink)";
        o.style.borderColor = on?"var(--forest)":"#DDD4C1";
      }});
      apply();
    }});
  }});
  ["f-district","f-beds","f-sort"].forEach(function(i){{ $(i).addEventListener("change",apply) }});
  $("f-q").addEventListener("input",apply);
  // Re-read the live feed so an ad posted since the last build is already here.
  fetch(API+"/market/approved?s={sect_key}").then(function(r){{return r.json()}}).then(function(j){{
    if(Array.isArray(j)&&j.length){{ ADS=j; apply(); }}
  }}).catch(function(){{}});
}})();
</script>
</body>
</html>
"""
    return head + body.replace("{NAV}", ctx["nav_html"]("realestate")).replace("{FOOTER}", ctx["footer_html"]())


# ── one ad ───────────────────────────────────────────────────────────────────

def _build_detail(ctx, ad, table):
    slug = ad["slug"]
    page_url = f'{ctx["SITE_URL"]}/{SECTION_PATH}/{slug}/'
    dead = _is_dead(ad)
    imgs = ad.get("images") or []
    cat = CAT_ONE.get(ad.get("category"), "Property")
    deal = "for sale" if ad.get("deal") == "sale" else "for rent"
    where = ad.get("district", "")
    if ad.get("area"):
        where = f'{ad["area"]}, {where}'

    title = f'{_esc(ad.get("title",""))}'
    meta_desc = (f'{cat} {deal} in {where}. {_price_main(ad)}. '
                 + " ".join(_specs(ad)).replace("&#178;", "2"))[:300]

    ld = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": html_lib.unescape(ad.get("title", "")),
        "url": page_url,
        "description": html_lib.unescape(ad.get("descr", ""))[:900],
        "category": cat,
        "offers": {
            "@type": "Offer",
            "price": ad.get("price"),
            "priceCurrency": ad.get("currency", "SRD"),
            "availability": "https://schema.org/SoldOut" if dead else "https://schema.org/InStock",
            "areaServed": {"@type": "Place", "name": ad.get("district", "Suriname")},
            "availableAtOrFrom": {"@type": "Place", "address": _postal(ad)},
        },
    }
    if imgs:
        ld["image"] = imgs

    head = ctx["hub_head"](title, meta_desc, f"{SECTION_PATH}/{slug}/", extra_ld=ld)
    if dead:
        # The page stays up so an indexed URL does not 404, but it should stop
        # competing in search for a property nobody can buy.
        head = head.replace('<meta name="robots" content="max-image-preview:large">',
                            '<meta name="robots" content="noindex,follow">')

    gallery = ""
    if imgs:
        main = (f'<img id="mk-main" src="{_esc(imgs[0])}" alt="{title}" width="900" height="600" '
                'class="w-full rounded-2xl object-cover" style="max-height:480px" fetchpriority="high">')
        thumbs = ""
        if len(imgs) > 1:
            thumbs = ('<div class="flex gap-2 mt-3 overflow-x-auto pb-1">' + "".join(
                f'<button data-img="{_esc(u)}" class="shrink-0 rounded-lg overflow-hidden border-2" '
                f'style="border-color:{"var(--forest)" if i == 0 else "transparent"}">'
                f'<img src="{_esc(u)}" alt="" width="96" height="72" loading="lazy" '
                'class="w-24 h-[72px] object-cover"></button>' for i, u in enumerate(imgs))
                + "</div>")
        gallery = main + thumbs
    else:
        gallery = ('<div class="w-full rounded-2xl flex items-center justify-center" '
                   'style="height:260px;background:var(--paper-2);color:#656C63">No photos on this ad</div>')

    banner = ""
    if dead:
        word = "This property has been sold." if ad.get("status") == "sold" else "This ad has expired."
        banner = ('<div class="rounded-xl p-4 mb-5 text-sm font-semibold" '
                  f'style="background:#EFEFEF;border:1px solid #D8D8D8;color:#3F3F3F">{word} '
                  f'<a href="/{SECTION_PATH}.html" class="underline">See what is available now</a>.</div>')

    spec_rows = ""
    pairs = []
    if ad.get("beds"):
        pairs.append(("Bedrooms", str(ad["beds"])))
    if ad.get("baths"):
        pairs.append(("Bathrooms", str(ad["baths"])))
    if ad.get("built_m2"):
        pairs.append(("Built area", f'{_amount(ad["built_m2"])} m&#178;'))
    if ad.get("plot_m2"):
        pairs.append(("Plot size", f'{_amount(ad["plot_m2"])} m&#178;'))
    if ad.get("furnished"):
        pairs.append(("Furnished", "Yes"))
    pairs.append(("Type", cat))
    pairs.append(("District", ad.get("district", "")))
    if pairs:
        spec_rows = ('<dl class="grid gap-x-6 gap-y-2 text-sm" style="grid-template-columns:repeat(auto-fit,minmax(160px,1fr))">'
                     + "".join(f'<div class="flex justify-between border-b py-2" style="border-color:#EDE7DA">'
                               f'<dt style="color:#5A625B">{k}</dt><dd class="font-semibold text-gray-900">{v}</dd></div>'
                               for k, v in pairs) + "</dl>")

    seller = ad.get("seller") or {}
    seller_line = ""
    if seller.get("name"):
        badge = ""
        if seller.get("verified"):
            lbl = _esc(seller.get("vlabel") or "Verified seller")
            badge = (' <span class="px-2 py-0.5 rounded-full text-xs font-semibold text-white" '
                     f'style="background:var(--forest)">{lbl}</span>')
        seller_line = (f'<p class="text-sm mb-4" style="color:#5A625B">Placed by '
                       f'<b class="text-gray-900" translate="no">{_esc(seller["name"])}</b>{badge}</p>')

    alt = _price_alt(ad, table)
    contact = "" if dead else _contact_block(ad, page_url)
    posted = ""
    if ad.get("created"):
        posted = datetime.fromtimestamp(ad["created"], timezone.utc).strftime("%d %B %Y")
    addr_block = ""
    if ad.get("show_addr") and ad.get("address"):
        q = urllib.parse.quote(f'{ad["address"]}, {ad.get("area") or ad.get("district","")}, Suriname')
        addr_block = (
            '<p class="mt-1 mb-4" style="color:#5A625B"><b class="text-gray-900" translate="no">'
            + _esc(ad["address"]) + '</b> &middot; '
            f'<a href="https://www.google.com/maps/search/?api=1&amp;query={q}" target="_blank" '
            'rel="noopener" class="underline" style="color:var(--forest2)">Directions</a></p>')
    api = json.dumps(MK_API)
    slug_js = json.dumps(slug)

    body = f"""
<body class="bg-gray-50 overflow-x-hidden">
{{NAV}}
<main class="max-w-5xl mx-auto px-5 py-8">
  <nav aria-label="Breadcrumb" class="text-sm mb-4" style="color:#656C63">
    <a href="/" class="hover:underline">Home</a> &rsaquo;
    <a href="/{SECTION_PATH}.html" class="hover:underline">Real estate</a> &rsaquo;
    <span translate="no">{title}</span>
  </nav>
  {banner}
  <div class="grid gap-7" style="grid-template-columns:minmax(0,1.7fr) minmax(0,1fr)">
    <div>
      {gallery}
      <h1 translate="no" class="serif text-3xl mt-6 mb-1" style="color:var(--forest);font-weight:400">{title}</h1>
      <p class="mb-1" style="color:#5A625B">{_esc(cat)} {deal} in {_esc(where)}</p>
      {addr_block}
      {spec_rows}
      <h2 class="serif text-xl mt-7 mb-2" style="color:var(--forest);font-weight:400">About this property</h2>
      <p translate="no" class="text-gray-700 leading-relaxed" style="white-space:pre-wrap">{_esc(ad.get("descr","")) or "The seller did not add a description."}</p>
      <p class="text-xs mt-6" style="color:#656C63">Posted {posted}. Explore Suriname did not write this ad and does not inspect properties.
        <button id="mk-report" class="underline" style="color:#656C63">Report this ad</button></p>
    </div>
    <aside>
      <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-5" style="position:sticky;top:1rem">
        <p class="text-3xl font-bold mb-1" style="color:var(--forest)">{_esc(_price_main(ad))}</p>
        {f'<p class="text-sm mb-4" style="color:#656C63">{_esc(alt)}</p>' if alt else '<div class="mb-4"></div>'}
        {seller_line}
        {contact or '<p class="text-sm" style="color:#656C63">Contact details are no longer shown for this ad.</p>'}
      </div>
      {SAFETY}
    </aside>
  </div>
</main>
{{FOOTER}}
<script>
(function(){{
  var thumbs=document.querySelectorAll("[data-img]"), main=document.getElementById("mk-main");
  thumbs.forEach(function(b){{ b.addEventListener("click",function(){{
    main.src=b.dataset.img;
    thumbs.forEach(function(o){{o.style.borderColor="transparent"}});
    b.style.borderColor="var(--forest)";
  }}) }});
  var rep=document.getElementById("mk-report");
  if(rep) rep.addEventListener("click",function(){{
    var why=prompt("What is wrong with this ad? (scam, already sold, wrong details, offensive)");
    if(why===null) return;
    fetch({api}+"/market/report",{{method:"POST",headers:{{"Content-Type":"application/json"}},
      body:JSON.stringify({{slug:{slug_js},reason:"other",detail:why}})}})
      .then(function(){{rep.textContent="Reported. Thank you."}})
      .catch(function(){{rep.textContent="Could not send that just now."}});
  }});
}})();
</script>
</body>
</html>
"""
    return head + body.replace("{NAV}", ctx["nav_html"]("realestate")).replace("{FOOTER}", ctx["footer_html"]())


# ── shared client bits for the two signed-in pages ───────────────────────────

def _gsi_head(ctx):
    cid = ctx.get("GOOGLE_CLIENT_ID") or ""
    if not cid:
        return ""
    return '\n  <script src="https://accounts.google.com/gsi/client" async defer></script>'


def _auth_js(ctx):
    """
    Sign-in that stays out of the way. The ID token lives in sessionStorage and
    the Worker verifies it on every call, so there is no session to expire badly:
    if a call comes back 401 the button simply reappears.
    """
    cid = json.dumps(ctx.get("GOOGLE_CLIENT_ID") or "")
    return """
var API = %s, CID = %s;
var TOK = null;
try { TOK = sessionStorage.getItem("esr-mk-idt"); } catch(e) {}
function setTok(t){ TOK=t; try{ sessionStorage.setItem("esr-mk-idt",t); }catch(e){} }
function clearTok(){ TOK=null; try{ sessionStorage.removeItem("esr-mk-idt"); }catch(e){} }
function onCred(r){ setTok(r.credential); onSignedIn(); }
function mountSignIn(el){
  if(!CID || !window.google || !google.accounts){ el.innerHTML='<p class="text-sm" style="color:#656C63">Sign-in is unavailable right now. Please try again shortly.</p>'; return; }
  google.accounts.id.initialize({ client_id: CID, callback: onCred });
  google.accounts.id.renderButton(el, { theme:"outline", size:"large", text:"continue_with", shape:"pill" });
}
function bootAuth(){
  if(TOK) { onSignedIn(); return; }
  var el=document.getElementById("gsi");
  if(window.google && window.google.accounts) mountSignIn(el);
  else window.addEventListener("load", function(){ mountSignIn(el); });
}
""" % (json.dumps(MK_API), cid)


# ── post an ad ───────────────────────────────────────────────────────────────

def _build_post(ctx):
    cat_opts = "".join(f'<option value="{k}">{CAT_ONE[k]}</option>' for k, _ in CATS)
    dist_opts = "".join(f'<option value="{d}">{d}</option>' for d in DISTRICTS)
    cur_opts = "".join(f'<option value="{c}">{c}</option>' for c in CURRENCIES)
    per_opts = "".join(f'<option value="{k}">{lbl}</option>' for k, lbl in PERIODS)
    ts_key = ctx.get("TURNSTILE_SITEKEY") or ""
    ts_head = ('<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>'
               if ts_key else "")
    ts_box = (f'<div class="cf-turnstile mt-4" data-sitekey="{ts_key}" data-theme="light"></div>'
              if ts_key else "")

    head = ctx["hub_head"](
        "Place a property ad in Suriname",
        "Put your house, apartment, land or commercial property in front of buyers and renters in "
        "Suriname. Free, about a minute, and buyers message you directly.",
        "post-ad.html")
    head = head.replace("</head>", _gsi_head(ctx) + "\n  " + ts_head + "\n</head>")

    auth_js = _auth_js(ctx)
    sect_key = SECTION

    body = f"""
<body class="bg-gray-50 overflow-x-hidden">
{{NAV}}
<div class="pg-hero text-white py-12 text-center" style="background:var(--forest)">
  <p class="text-xs font-semibold uppercase tracking-widest mb-3" style="color:var(--coral)">Marketplace</p>
  <h1 class="serif text-4xl mb-3">Place your property ad</h1>
  <p class="text-white/65 max-w-xl mx-auto px-5">Free. Takes about a minute. Buyers message you straight on WhatsApp.</p>
</div>

<main class="max-w-2xl mx-auto px-5 py-8">

  <div id="signin" class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 text-center">
    <h2 class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">First, sign in</h2>
    <p class="text-gray-600 text-sm mb-5 max-w-md mx-auto">So you can edit your own ad later, change the price, or mark it sold. We never show your email on the ad.</p>
    <div id="gsi" class="flex justify-center"></div>
  </div>

  <form id="mkform" class="hidden">
    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5">
      <h2 class="serif text-xl mb-4" style="color:var(--forest);font-weight:400">Photos</h2>
      <p class="text-sm mb-3" style="color:#5A625B">Up to six. The first one is what people see in the list. Ads with photos get far more replies.</p>
      <input type="file" name="photo" id="f-photo" accept="image/jpeg,image/png,image/webp" multiple class="block w-full text-sm">
      <div id="prev" class="flex gap-2 flex-wrap mt-3"></div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5">
      <h2 class="serif text-xl mb-4" style="color:var(--forest);font-weight:400">The property</h2>
      <div class="flex gap-2 mb-4">
        <label class="flex-1"><input type="radio" name="deal" value="sale" checked class="sr-only mk-deal"><span class="block text-center py-2.5 rounded-xl border cursor-pointer font-semibold text-sm" style="border-color:#DDD4C1">For sale</span></label>
        <label class="flex-1"><input type="radio" name="deal" value="rent" class="sr-only mk-deal"><span class="block text-center py-2.5 rounded-xl border cursor-pointer font-semibold text-sm" style="border-color:#DDD4C1">For rent</span></label>
      </div>
      <label class="block mb-4"><span class="block text-sm font-semibold mb-1">Title</span>
        <input name="title" id="f-title" maxlength="90" required placeholder="Ruime woning met erf in Kwatta" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
      <div class="grid gap-4 mb-4" style="grid-template-columns:repeat(auto-fit,minmax(140px,1fr))">
        <label class="block"><span class="block text-sm font-semibold mb-1">Type</span>
          <select name="category" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1">{cat_opts}</select></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">District</span>
          <select name="district" required class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"><option value="">Choose one</option>{dist_opts}</select></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">Area <span class="font-normal" style="color:#656C63">optional</span></span>
          <input name="area" maxlength="60" placeholder="Kwatta" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>

      </div>
      <label class="block mb-2"><span class="block text-sm font-semibold mb-1">Street and number <span class="font-normal" style="color:#656C63">optional</span></span>
        <input name="address" maxlength="160" placeholder="Kwattaweg 123" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
      <label class="flex items-start gap-2 text-sm mb-1"><input type="checkbox" name="hide_addr" value="1" class="mt-1">
        <span>Do not show the exact address on the ad. Buyers then see only the area until you give them the address yourself. Worth ticking for an empty property.</span></label>
      <div class="grid gap-4" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))">
        <label class="block"><span class="block text-sm font-semibold mb-1">Price</span>
          <input name="price" id="f-price" inputmode="numeric" required placeholder="85000" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">Currency</span>
          <select name="currency" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1">{cur_opts}</select></label>
        <label class="block" id="wrap-period" style="display:none"><span class="block text-sm font-semibold mb-1">Rent per</span>
          <select name="period" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1">{per_opts}</select></label>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5" id="wrap-specs">
      <h2 class="serif text-xl mb-4" style="color:var(--forest);font-weight:400">Details <span class="text-sm font-sans" style="color:#656C63">all optional</span></h2>
      <div class="grid gap-4" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr))">
        <label class="block"><span class="block text-sm font-semibold mb-1">Bedrooms</span><input name="beds" inputmode="numeric" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">Bathrooms</span><input name="baths" inputmode="numeric" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">Built m&#178;</span><input name="built_m2" inputmode="numeric" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
        <label class="block"><span class="block text-sm font-semibold mb-1">Plot m&#178;</span><input name="plot_m2" inputmode="numeric" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
      </div>
      <label class="flex items-center gap-2 mt-4 text-sm"><input type="checkbox" name="furnished" value="1"> Furnished</label>
      <label class="block mt-4"><span class="block text-sm font-semibold mb-1">Description</span>
        <textarea name="descr" id="f-descr" rows="5" maxlength="4000" placeholder="What makes it worth seeing. Links and email addresses are removed, so put those in the contact fields below." class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></textarea></label>
    </div>

    <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-5">
      <h2 class="serif text-xl mb-1" style="color:var(--forest);font-weight:400">How buyers reach you</h2>
      <p class="text-sm mb-4" style="color:#5A625B">Fill in at least one. A Suriname mobile number gets a WhatsApp button automatically.</p>
      <label class="block mb-3"><span class="block text-sm font-semibold mb-1">WhatsApp or phone</span>
        <input name="phone" id="f-phone" inputmode="tel" placeholder="8812345" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1">
        <span id="wa-hint" class="block text-xs mt-1" style="color:#5A625B"></span></label>
      <label class="block mb-3"><span class="block text-sm font-semibold mb-1">Email</span>
        <input name="email" id="f-email" type="email" placeholder="jij@voorbeeld.com" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
      <label class="block"><span class="block text-sm font-semibold mb-1">Link</span>
        <input name="link" id="f-link" placeholder="facebook.com/jouwpagina" class="w-full rounded-xl border px-3 py-2.5" style="border-color:#DDD4C1"></label>
      <p id="contact-err" class="hidden text-sm mt-3 font-semibold" style="color:#B3261E">Add at least one way for buyers to reach you.</p>
      {ts_box}
    </div>

    <p id="formerr" class="hidden rounded-xl p-3 mb-4 text-sm font-semibold" style="background:#FDECEA;border:1px solid #F5C2BD;color:#B3261E"></p>
    <button type="submit" id="go" class="w-full py-3.5 rounded-xl font-semibold text-white text-lg" style="background:var(--forest)">Place my ad</button>
    <p class="text-xs text-center mt-3" style="color:#656C63">Your ad runs for 60 days. You can renew, edit the price or mark it sold any time from <a href="/my-ads.html" class="underline">your ads</a>.</p>
  </form>

  <div id="done" class="hidden bg-white rounded-2xl shadow-sm border border-gray-100 p-7 text-center">
    <h2 class="serif text-2xl mb-3" style="color:var(--forest);font-weight:400" id="done-h">Your ad is up</h2>
    <p class="text-gray-600 mb-2" id="done-p"></p>
    <p id="done-strip" class="hidden text-sm rounded-xl p-3 mb-4" style="background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12"></p>
    <a href="/my-ads.html" class="inline-block px-6 py-3 rounded-xl font-semibold text-white" style="background:var(--forest)">See your ads</a>
  </div>

  <div class="mt-8">{SAFETY}</div>
</main>
{{FOOTER}}
<script>
(function(){{
{auth_js}
var $=function(i){{return document.getElementById(i)}};
var form=$("mkform"), files=[];

function onSignedIn(){{
  $("signin").classList.add("hidden");
  form.classList.remove("hidden");
  restore();
}}

// draft autosave: a dropped connection on Suriname mobile data should not cost
// somebody the five minutes they just spent typing
var DK="esr-mk-draft";
function save(){{
  try{{
    var d={{}};
    new FormData(form).forEach(function(v,k){{ if(typeof v==="string") d[k]=v; }});
    localStorage.setItem(DK,JSON.stringify(d));
  }}catch(e){{}}
}}
function restore(){{
  try{{
    var d=JSON.parse(localStorage.getItem(DK)||"{{}}");
    Object.keys(d).forEach(function(k){{
      var el=form.elements[k];
      if(!el) return;
      if(el.length&&el[0]&&el[0].type==="radio"){{ [].forEach.call(el,function(r){{r.checked=(r.value===d[k])}}); }}
      else el.value=d[k];
    }});
    deal(); waHint();
  }}catch(e){{}}
}}
form.addEventListener("input",save);
form.addEventListener("change",save);

function deal(){{
  var rent=form.querySelector('input[name="deal"]:checked').value==="rent";
  $("wrap-period").style.display=rent?"block":"none";
  [].forEach.call(document.querySelectorAll(".mk-deal"),function(r){{
    var s=r.nextElementSibling;
    s.style.background=r.checked?"var(--forest)":"var(--card)";
    s.style.color=r.checked?"#fff":"var(--ink)";
    s.style.borderColor=r.checked?"var(--forest)":"#DDD4C1";
  }});
}}
[].forEach.call(document.querySelectorAll(".mk-deal"),function(r){{r.addEventListener("change",deal)}});

function waHint(){{
  var v=($("f-phone").value||"").replace(/[^0-9+]/g,"").replace(/^\\+/,"").replace(/^00/,"");
  var mob=/^597[6-8][0-9]{{6}}$/.test(v)||/^[6-8][0-9]{{6}}$/.test(v);
  $("wa-hint").textContent = !v ? "" : (mob ? "Buyers will get a WhatsApp button for this number." : "Not a Suriname mobile, so buyers will see a normal call link.");
}}
$("f-phone").addEventListener("input",waHint);

$("f-photo").addEventListener("change",function(e){{
  files=[].slice.call(e.target.files).slice(0,6);
  $("prev").innerHTML=files.map(function(f){{
    return '<img src="'+URL.createObjectURL(f)+'" class="w-20 h-16 object-cover rounded-lg" alt="">';
  }}).join("");
  if(e.target.files.length>6) alert("Only the first six photos will be used.");
}});

form.addEventListener("submit",async function(e){{
  e.preventDefault();
  var hasContact=$("f-phone").value.trim()||$("f-email").value.trim()||$("f-link").value.trim();
  $("contact-err").className=hasContact?"hidden":"text-sm mt-3 font-semibold";
  if(!hasContact){{ $("f-phone").focus(); return; }}
  var btn=$("go"); btn.disabled=true; btn.textContent="Placing your ad...";
  $("formerr").className="hidden";

  var fd=new FormData(form);
  fd.delete("photo");
  files.forEach(function(f){{ fd.append("photo",f); }});
  fd.append("section","{sect_key}");
  fd.append("idt",TOK);
  var ts=document.querySelector('[name="cf-turnstile-response"]');
  if(ts) fd.append("cf-turnstile-response",ts.value);

  try{{
    var r=await fetch(API+"/market/submit",{{method:"POST",body:fd}});
    var j=await r.json();
    if(r.status===401){{ clearTok(); location.reload(); return; }}
    if(!j.ok){{
      $("formerr").textContent=j.err||"Something went wrong. Please try again.";
      $("formerr").className="rounded-xl p-3 mb-4 text-sm font-semibold";
      btn.disabled=false; btn.textContent="Place my ad";
      if(window.turnstile) window.turnstile.reset();
      return;
    }}
    try{{ localStorage.removeItem(DK); }}catch(e){{}}
    form.classList.add("hidden");
    $("done").classList.remove("hidden");
    $("done-h").textContent = j.live ? "Your ad is up" : "Thanks, we are checking it";
    $("done-p").textContent = j.live
      ? "It is live now and will show on the real estate page within about fifteen minutes."
      : "First ads get a quick look by hand. Once it is approved it goes up, and everything you place after that appears straight away.";
    if(j.stripped && j.stripped.length){{
      $("done-strip").textContent="We took a link or email address out of your description: "+j.stripped.join(", ")+". Contact details belong in the contact fields so buyers can tap them.";
      $("done-strip").className="text-sm rounded-xl p-3 mb-4";
    }}
    window.scrollTo({{top:0,behavior:"smooth"}});
  }}catch(err){{
    $("formerr").textContent="No connection. Your draft is saved, try again in a moment.";
    $("formerr").className="rounded-xl p-3 mb-4 text-sm font-semibold";
    btn.disabled=false; btn.textContent="Place my ad";
  }}
}});

deal(); bootAuth();
}})();
</script>
</body>
</html>
"""
    return head + body.replace("{NAV}", ctx["nav_html"]("realestate")).replace("{FOOTER}", ctx["footer_html"]())


# ── my ads ───────────────────────────────────────────────────────────────────

def _build_myads(ctx):
    head = ctx["hub_head"](
        "Your property ads",
        "Manage the property ads you placed on Explore Suriname: change the price, mark one sold, "
        "or renew it for another sixty days.",
        "my-ads.html")
    head = head.replace('<meta name="robots" content="max-image-preview:large">',
                        '<meta name="robots" content="noindex,follow">')
    head = head.replace("</head>", _gsi_head(ctx) + "\n</head>")

    auth_js = _auth_js(ctx)
    sect_path = SECTION_PATH

    body = f"""
<body class="bg-gray-50 overflow-x-hidden">
{{NAV}}
<div class="pg-hero text-white py-12 text-center" style="background:var(--forest)">
  <p class="text-xs font-semibold uppercase tracking-widest mb-3" style="color:var(--coral)">Marketplace</p>
  <h1 class="serif text-4xl mb-3">Your ads</h1>
  <p class="text-white/65 max-w-xl mx-auto px-5">Change a price, mark something sold, or renew an ad before it runs out.</p>
</div>

<main class="max-w-3xl mx-auto px-5 py-8">
  <div id="signin" class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 text-center">
    <h2 class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">Sign in to see your ads</h2>
    <p class="text-gray-600 text-sm mb-5">Use the same Google account you placed them with.</p>
    <div id="gsi" class="flex justify-center"></div>
  </div>
  <div id="list"></div>
  <p class="text-center mt-8"><a href="/post-ad.html" class="inline-block px-6 py-3 rounded-xl font-semibold text-white" style="background:var(--forest)">Place another ad</a></p>
</main>
{{FOOTER}}
<script>
(function(){{
{auth_js}
var $=function(i){{return document.getElementById(i)}};
var esc=function(s){{return String(s==null?"":s).replace(/[&<>"']/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[c]}})}};
var amt=function(n){{return Number(n||0).toLocaleString("nl-NL",{{maximumFractionDigits:0}})}};

var LABEL={{pending:"Waiting for review",live:"Live",sold:"Sold",expired:"Expired",declined:"Not published",hidden:"Taken down"}};
var COLOR={{pending:"#7A5A12",live:"#1B4332",sold:"#3F3F3F",expired:"#3F3F3F",declined:"#B3261E",hidden:"#B3261E"}};

function daysLeft(a){{
  if(a.status!=="live"||!a.expires) return null;
  return Math.ceil((a.expires-Date.now()/1000)/86400);
}}
function row(a){{
  var d=daysLeft(a), warn="";
  if(d!==null && d<=10) warn='<p class="text-sm mt-2 rounded-lg p-2" style="background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12">'
    +(d<=0?"This runs out today.":"Runs out in "+d+" day"+(d===1?"":"s")+".")+' Still available? Renew it so it keeps showing.</p>';
  var note=a.note?'<p class="text-sm mt-2 rounded-lg p-2" style="background:#FDECEA;border:1px solid #F5C2BD;color:#B3261E">'+esc(a.note)+'</p>':'';
  var img=(a.images&&a.images[0])||"";
  var btns='';
  if(a.status==="live"){{
    btns='<button data-a="sold" data-s="'+esc(a.slug)+'" class="mk-b">Mark as sold</button>'
       +'<button data-a="renew" data-s="'+esc(a.slug)+'" class="mk-b">Renew 60 days</button>'
       +'<button data-a="price" data-s="'+esc(a.slug)+'" class="mk-b">Change price</button>'
       +(a.address?'<button data-a="addr" data-s="'+esc(a.slug)+'" data-v="'+(a.show_addr?'0':'1')+'" class="mk-b">'
          +(a.show_addr?'Hide the address':'Show the address')+'</button>':'');
  }} else if(a.status==="sold"||a.status==="expired"){{
    btns='<button data-a="relist" data-s="'+esc(a.slug)+'" class="mk-b">Put it back up</button>';
  }}
  btns+='<button data-a="del" data-s="'+esc(a.slug)+'" class="mk-b">Delete</button>';
  var link=(a.status==="live"||a.status==="sold")?'<a href="/{sect_path}/'+esc(a.slug)+'/" class="text-sm underline" style="color:var(--forest2)">View the page</a>':'';
  return '<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-4 mb-4 flex gap-4">'
    +(img?'<img src="'+esc(img)+'" class="w-24 h-20 object-cover rounded-xl shrink-0" alt="">':'')
    +'<div class="flex-1 min-w-0">'
    +'<span class="inline-block px-2 py-0.5 rounded-full text-xs font-semibold text-white mb-1" style="background:'+(COLOR[a.status]||"#3F3F3F")+'">'+(LABEL[a.status]||a.status)+'</span>'
    +'<h3 class="font-semibold text-gray-900">'+esc(a.title)+'</h3>'
    +'<p class="font-bold" style="color:var(--forest)">'+esc(a.currency+" "+amt(a.price))+(a.deal==="rent"?" per "+(a.period||"month"):"")+'</p>'
    +(a.address?'<p class="text-sm" style="color:#656C63">'+esc(a.address)
       +(a.show_addr?'':' (not shown on the ad)')+'</p>':'')
    +link+warn+note
    +'<div class="flex flex-wrap gap-2 mt-3">'+btns+'</div>'
    +'</div></div>';
}}

async function load(){{
  var r=await fetch(API+"/market/mine",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify({{idt:TOK}})}});
  if(r.status===401){{ clearTok(); $("signin").classList.remove("hidden"); $("list").innerHTML=""; bootAuth(); return; }}
  var j=await r.json();
  if(!j.ads.length){{ $("list").innerHTML='<div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-7 text-center"><p class="text-gray-600">You have not placed an ad yet.</p></div>'; return; }}
  $("list").innerHTML=j.ads.map(row).join("");
  [].forEach.call(document.querySelectorAll(".mk-b"),function(b){{
    b.className="mk-b px-3 py-1.5 rounded-lg text-sm font-semibold border";
    b.style.borderColor="#DDD4C1"; b.style.color="var(--ink)";
  }});
}}
function onSignedIn(){{ $("signin").classList.add("hidden"); load(); }}

async function act(slug,body){{
  body.idt=TOK; body.slug=slug;
  var r=await fetch(API+"/market/update",{{method:"POST",headers:{{"Content-Type":"application/json"}},body:JSON.stringify(body)}});
  var j=await r.json();
  if(!j.ok) alert(j.err||"That did not work.");
  load();
}}
document.addEventListener("click",function(e){{
  var b=e.target.closest("[data-a]"); if(!b) return;
  var s=b.dataset.s, a=b.dataset.a;
  if(a==="sold"){{ if(confirm("Mark this as sold? It stops showing in the list.")) act(s,{{act:"sold"}}); }}
  else if(a==="renew") act(s,{{act:"renew"}});
  else if(a==="relist") act(s,{{act:"relist"}});
  else if(a==="del"){{ if(confirm("Delete this ad and its photos for good?")) act(s,{{act:"delete"}}); }}
  else if(a==="price"){{
    var p=prompt("New price (numbers only):"); if(p===null) return;
    act(s,{{act:"edit",price:p}});
  }}
  else if(a==="addr") act(s,{{act:"edit",show_addr:Number(b.dataset.v)}});
}});
bootAuth();
}})();
</script>
</body>
</html>
"""
    return head + body.replace("{NAV}", ctx["nav_html"]("realestate")).replace("{FOOTER}", ctx["footer_html"]())


# ── entry point ──────────────────────────────────────────────────────────────

def build_market_pages(ctx):
    """
    Return {filename: html} for the marketplace. Detail pages use nested paths,
    so the caller must create the directories (generate.py does this for the
    business listings already).
    """
    table = _rate_table(ctx.get("cbvs_rates"))
    ads = _fetch(f"/market/approved?s={SECTION}")

    cutoff = datetime.now(timezone.utc).timestamp() - DEAD_PAGE_DAYS * 86400
    ads = [a for a in ads
           if not (_is_dead(a) and (a.get("updated") or a.get("bumped") or 0) < cutoff)]

    out = {
        f"{SECTION_PATH}.html": _build_browse(ctx, ads, table),
        "post-ad.html":         _build_post(ctx),
        "my-ads.html":          _build_myads(ctx),
    }
    for ad in ads:
        if not re.fullmatch(r"[a-z0-9-]{1,80}", ad.get("slug", "")):
            continue                      # never let a feed value shape a path
        out[f'{SECTION_PATH}/{ad["slug"]}/index.html'] = _build_detail(ctx, ad, table)

    live = sum(1 for a in ads if not _is_dead(a))
    print(f"  OK  marketplace: {live} live, {len(ads) - live} sold/expired kept for SEO")
    return out
