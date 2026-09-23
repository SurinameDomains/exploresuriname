#!/usr/bin/env python3
"""
Explore Suriname - Marketplace (classifieds) builder.

    marketplace/index.html          browse surface, server rendered then hydrated
    marketplace/<slug>/index.html   one ad, build generated, this is the SEO surface
    post-ad.html                    the posting form (sign-in only at the last step)
    my-ads.html                     the seller's own ads
    real-estate.html                redirect stub, owned by generate.py

History: shipped Sep 2026 as property-only "Real estate". Zero ads in the first
weeks, so it became a general marketplace with property as one category. The
Worker keeps accepting section=realestate for old clients; this module only
posts and reads section=market.

UX patterns copied on purpose from the big marketplaces:
  * search first, categories as a tappable rail (FB Marketplace, OLX)
  * dense 2-up photo grid on phones, price above title (Vinted, Marktplaats)
  * heart to save, recently viewed, filters live in the URL so a search can be
    shared or bookmarked and the back button works (all of them)
  * "New" badge and relative time on every card, "Free" as a category (FB)
  * floating Sell button on phones, contact bar pinned to the bottom of an ad
  * post flow: category first, photos compressed on the phone before upload,
    sign-in only at the very end, contact details remembered for next time,
    and a "share your ad on WhatsApp" step because that is where Suriname
    actually trades

WHY THE SPLIT: the site is static and rebuilds every ~15 min, so the browse grid
renders from the build AND re-hydrates from the Worker in the reader's browser.
Per-ad pages stay build generated because they are what Google indexes.

House rules: no em dashes in visible copy, no decorative emoji, no <style>
blocks emitted from the body (the CSS below goes into <head>).
JS lives in plain strings with __TOKENS__, never in f-strings, so there are no
doubled braces to get wrong.
NOTE: tailwind.config.js lists this file under `content`, and update.yml must
`git add marketplace/`, or the generated pages 404.
"""

import html as html_lib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone

MK_API = "https://esr-leaderboard.surinamedomains.workers.dev"

SECTION = "market"
SECTION_PATH = "marketplace"

# key, plural label, singular label, 24px stroke icon path.
# Must stay in step with MK_CATS.market in leaderboard-worker/worker.js.
CATS = [
    ("electronics", "Phones & electronics", "Electronics",
     "M8 2h8a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zM11 18h2"),
    ("vehicles", "Vehicles & parts", "Vehicle",
     "M3 16v-3l2.2-5.2A2 2 0 0 1 7 6.5h10a2 2 0 0 1 1.8 1.3L21 13v3zM3 16v2h3v-2M18 16v2h3v-2M7 12.5h.01M17 12.5h.01M5 11h14"),
    ("home", "Home & furniture", "Home",
     "M4 11V8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3M2 13a2 2 0 0 1 4 0v2h12v-2a2 2 0 0 1 4 0v5H2zM5 18v2M19 18v2"),
    ("fashion", "Fashion", "Fashion",
     "M8 3l4 2 4-2 5 4-3 3-2-1v12H8V9l-2 1-3-3z"),
    ("kids", "Baby & kids", "Baby & kids",
     "M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM9.5 12h.01M14.5 12h.01M10 16c1.2.8 2.8.8 4 0M12 5c0-1.6 1-2.4 2.2-2.4"),
    ("sports", "Sports & hobby", "Sports & hobby",
     "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM3.5 9h17M3.5 15h17M12 3c3.2 3.2 3.2 14.8 0 18M12 3c-3.2 3.2-3.2 14.8 0 18"),
    ("tools", "Tools & garden", "Tools & garden",
     "M14.7 6.3a4 4 0 0 0-5.4 5.1L3 17.7 6.3 21l6.3-6.3a4 4 0 0 0 5.1-5.4l-2.5 2.5-2.8-.7-.7-2.8z"),
    ("property", "Property", "Property",
     "M3 11l9-7 9 7M5 10v10h14V10M10 20v-6h4v6"),
    ("other", "Other", "Other",
     "M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8zM7.5 7.5h.01"),
]
CAT_KEYS = [c[0] for c in CATS]
CAT_LABEL = {c[0]: c[1] for c in CATS}
CAT_ONE = {c[0]: c[2] for c in CATS}
ICON_ALL = "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"
ICON_FREE = "M4 11h16v10H4zM2 7h20v4H2zM12 7v14M12 7C10 3 6 3 6 6s6 1 6 1zM12 7c2-4 6-4 6-1s-6 1-6 1"
ICON_HEART = "M12 20.5s-7.5-4.6-9.6-9.2A5.3 5.3 0 0 1 12 5.9a5.3 5.3 0 0 1 9.6 5.4c-2.1 4.6-9.6 9.2-9.6 9.2z"
ICON_CAM = "M4 8h3l2-2.5h6L17 8h3v11H4zM12 16.5a3.2 3.2 0 1 0 0-6.4 3.2 3.2 0 0 0 0 6.4z"
ICON_SHARE = "M12 3v12M7 8l5-5 5 5M5 13v7h14v-7"
ICON_PLUS = "M12 5v14M5 12h14"

CONDS = [("new", "New"), ("used", "Used"), ("parts", "For parts")]
COND_LABEL = dict(CONDS)

DISTRICTS = ["Paramaribo", "Wanica", "Commewijne", "Saramacca", "Nickerie",
             "Coronie", "Marowijne", "Para", "Brokopondo", "Sipaliwini"]

CURRENCIES = ["SRD", "USD", "EUR"]
PERIODS = [("month", "per month"), ("week", "per week"), ("day", "per day")]

PAGE = 24            # cards per "Show more"

# Ads that stopped being for sale keep their page for this long so an indexed
# URL does not turn into a 404 the week after it ranked.
DEAD_PAGE_DAYS = 90

_esc = html_lib.escape


def _svg(path, cls="w-5 h-5", sw="1.8", fill="none"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="{fill}" stroke="currentColor" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'<path d="{path}"/></svg>')


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
    """{currency: SRD per unit}. Display only, always labelled approximate."""
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
    return f"{n:,.0f}".replace(",", ".")


def _is_prop(ad):
    return ad.get("category") == "property" or ad.get("section") == "realestate"


def _is_free(ad):
    return not _is_prop(ad) and not float(ad.get("price") or 0)


def _price_main(ad):
    if _is_free(ad):
        return "Free"
    p = f'{ad.get("currency", "SRD")} {_amount(ad.get("price"))}'
    if ad.get("deal") == "rent":
        p += " " + dict(PERIODS).get(ad.get("period") or "month", "per month")
    return p


def _price_alt(ad, table):
    """One approximate line in the other two currencies, never stored."""
    cur = ad.get("currency", "SRD")
    if _is_free(ad) or cur not in table:
        return ""
    srd = float(ad.get("price") or 0) * table[cur]
    bits = [f"{o} {_amount(srd / table[o])}" for o in CURRENCIES if o != cur and o in table]
    return "about " + " or ".join(bits) if bits else ""


# ── contact ──────────────────────────────────────────────────────────────────

def _digits(p):
    return "+" + re.sub(r"\D", "", p or "")


def _wa_href(ad, page_url):
    """Prefilled WhatsApp message that already says which ad it is about."""
    digits = re.sub(r"\D", "", ad.get("phone") or "")
    msg = f'Hi, I saw your ad "{ad.get("title", "")}" on Explore Suriname. Is it still available?\n{page_url}'
    return f"https://wa.me/{digits}?text={urllib.parse.quote(msg)}"


WA_SVG = ('<svg class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
          '<path d="M17.5 14.4c-.3-.2-1.7-.9-2-1-.3-.1-.5-.1-.7.1-.2.3-.7 1-.9 1.2-.2.2-.3.2-.6.1-.3-.2-1.2-.5-2.3-1.4-.9-.8-1.4-1.7-1.6-2-.2-.3 0-.5.1-.6l.5-.5c.1-.2.2-.3.3-.5 0-.2 0-.4 0-.5 0-.2-.7-1.6-.9-2.2-.2-.5-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5 4.5.7.3 1.2.5 1.7.6.7.2 1.3.2 1.8.1.6-.1 1.7-.7 1.9-1.4.2-.7.2-1.2.2-1.4-.1-.1-.3-.2-.6-.3z"/>'
          '<path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2z"/></svg>')


def _primary_contact(ad, page_url, short=False):
    """The main button; short=True for the pinned bar on phones."""
    if ad.get("phone") and ad.get("wa"):
        return (f'<a href="{_esc(_wa_href(ad, page_url))}" target="_blank" rel="noopener nofollow" '
                'class="mk-btn mk-wa">' + WA_SVG + ('WhatsApp' if short else 'Message on WhatsApp') + '</a>')
    if ad.get("phone"):
        return (f'<a href="tel:{_esc(_digits(ad["phone"]))}" class="mk-btn mk-solid">'
                + ('Call' if short else f'Call {_esc(ad["phone"])}') + '</a>')
    if ad.get("email"):
        sub = urllib.parse.quote(f'About your ad: {ad.get("title","")}')
        return (f'<a href="mailto:{_esc(ad["email"])}?subject={sub}" class="mk-btn mk-solid">'
                'Send an email</a>')
    if ad.get("link"):
        return (f'<a href="{_esc(ad["link"])}" target="_blank" rel="noopener nofollow" '
                'class="mk-btn mk-solid">Contact the seller</a>')
    return ""


def _contact_block(ad, page_url):
    rows = [_primary_contact(ad, page_url)]
    if ad.get("phone") and ad.get("wa"):
        rows.append(f'<a href="tel:{_esc(_digits(ad["phone"]))}" class="mk-btn mk-line">'
                    f'Call {_esc(ad["phone"])}</a>')
    if ad.get("email") and (ad.get("phone")):
        sub = urllib.parse.quote(f'About your ad: {ad.get("title","")}')
        rows.append(f'<a href="mailto:{_esc(ad["email"])}?subject={sub}" class="mk-btn mk-line">'
                    'Send an email</a>')
    if ad.get("link") and (ad.get("phone") or ad.get("email")):
        rows.append(f'<a href="{_esc(ad["link"])}" target="_blank" rel="noopener nofollow" '
                    'class="mk-btn mk-line">Open the seller&#8217;s page</a>')
    return "".join(r for r in rows if r)


def _safety(ad=None):
    if ad is not None and _is_prop(ad):
        tip = ('See the property in person, meet at the address itself, and check ownership papers '
               'at the GLIS before any money changes hands. Nobody with a real listing needs a '
               'deposit to show it to you.')
    else:
        tip = ('Meet somewhere busy in daylight, check the item before you pay, and never send money '
               'in advance to someone you have not met. Phones: test the screen, camera and charging, '
               'and ask for the box or receipt.')
    return ('<div class="mk-safe"><b>Safe buying.</b> ' + tip +
            ' Explore Suriname does not handle payments or vet sellers.</div>')


# ── specs ────────────────────────────────────────────────────────────────────

def _spec_pairs(ad):
    pairs = []
    if _is_prop(ad):
        pairs.append(("Offer", "For rent" if ad.get("deal") == "rent" else "For sale"))
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
    else:
        if ad.get("cond") in COND_LABEL:
            pairs.append(("Condition", COND_LABEL[ad["cond"]]))
        if ad.get("make"):
            pairs.append(("Make", _esc(ad["make"])))
        if ad.get("model"):
            pairs.append(("Model", _esc(ad["model"])))
        if ad.get("year"):
            pairs.append(("Year", str(ad["year"])))
        if ad.get("mileage"):
            pairs.append(("Mileage", f'{_amount(ad["mileage"])} km'))
    pairs.append(("Category", CAT_LABEL.get(ad.get("category"), "Other")))
    loc = _esc(ad.get("district", ""))
    if ad.get("area"):
        loc = f'{_esc(ad["area"])}, {loc}'
    pairs.append(("Location", loc))
    return pairs


def _postal(ad):
    a = {"@type": "PostalAddress",
         "addressLocality": ad.get("area") or ad.get("district", ""),
         "addressRegion": ad.get("district", ""),
         "addressCountry": "SR"}
    if _is_prop(ad) and ad.get("show_addr") and ad.get("address"):
        a["streetAddress"] = ad["address"]
    return a


def _is_dead(ad):
    return ad.get("status") in ("sold", "expired")


def _ts(ad):
    return int(ad.get("bumped") or ad.get("created") or 0)


# ── shared styles (go into <head>) ───────────────────────────────────────────

MK_CSS = """
.mk-rail{scroll-padding-inline:1.25rem;display:flex;gap:.5rem;overflow-x:auto;scrollbar-width:none;padding:.25rem 1.25rem .5rem;margin:0 -1.25rem;scroll-snap-type:x proximity}
.mk-rail::-webkit-scrollbar{display:none}
.mk-cat{scroll-snap-align:start;flex:0 0 auto;display:flex;flex-direction:column;align-items:center;gap:.35rem;width:5.6rem;padding:.7rem .3rem .6rem;border-radius:1rem;border:1px solid var(--line);background:var(--card);color:var(--ink);font-size:.78rem;line-height:1.15;text-align:center;transition:background .15s,border-color .15s}
.mk-cat:hover{border-color:var(--forest2)}
.mk-cat .ic{display:flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border-radius:999px;background:var(--mint);color:var(--forest)}
.mk-cat[aria-pressed=true]{background:var(--forest);border-color:var(--forest);color:#fff}
.mk-cat[aria-pressed=true] .ic{background:rgba(255,255,255,.16);color:#fff}
.mk-cat .ct{font-size:.7rem;opacity:.7}
.mk-search{display:flex;background:#fff;border:1.5px solid var(--forest);border-radius:999px;overflow:hidden;max-width:40rem;box-shadow:0 2px 10px rgba(27,67,50,.08)}
.mk-search input{flex:1;min-width:0;border:0;padding:.85rem 1.1rem;font-size:1rem;background:transparent;outline:none}
.mk-search button{background:var(--forest);color:#fff;padding:0 1.2rem;font-weight:600;display:flex;align-items:center;gap:.4rem}
.mk-grid{display:grid;gap:.9rem .75rem;grid-template-columns:repeat(2,minmax(0,1fr))}
@media(min-width:640px){.mk-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:1.25rem 1rem}}
@media(min-width:1024px){.mk-grid{grid-template-columns:repeat(4,minmax(0,1fr))}}
.mk-card{position:relative;min-width:0}
.mk-card>a{display:block;color:inherit;text-decoration:none}
.mk-ph{position:relative;aspect-ratio:1/1;border-radius:.9rem;overflow:hidden;background:var(--paper-2)}
.mk-ph img{width:100%;height:100%;object-fit:cover;transition:transform .3s}
.mk-card:hover .mk-ph img{transform:scale(1.03)}
.mk-noph{display:flex;align-items:center;justify-content:center;height:100%;font-size:.8rem;color:#656C63}
.mk-pill{position:absolute;left:.5rem;top:.5rem;padding:.15rem .55rem;border-radius:999px;font-size:.7rem;font-weight:700;color:#fff;background:var(--coral)}
.mk-pill.dark{background:#3F3F3F}.mk-pill.ok{background:var(--forest)}
.mk-cnt{position:absolute;left:.5rem;bottom:.5rem;display:flex;align-items:center;gap:.2rem;padding:.1rem .45rem;border-radius:999px;font-size:.7rem;color:#fff;background:rgba(0,0,0,.55)}
.mk-heart{position:absolute;right:.45rem;top:.45rem;width:2.2rem;height:2.2rem;border-radius:999px;display:flex;align-items:center;justify-content:center;background:rgba(255,255,255,.92);color:#233028;box-shadow:0 1px 4px rgba(0,0,0,.15)}
.mk-heart[aria-pressed=true]{color:var(--coral)}
.mk-heart[aria-pressed=true] svg{fill:currentColor}
.mk-pr{font-weight:800;font-size:1.02rem;color:var(--ink);margin-top:.45rem}
.mk-pr.free{color:var(--forest2)}
.mk-t{font-size:.9rem;line-height:1.3;color:#374151;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.mk-m{font-size:.75rem;color:#6B7280;margin-top:.15rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mk-chip{padding:.35rem .75rem;border-radius:999px;font-size:.82rem;border:1px solid var(--line);background:var(--card);color:var(--ink)}
.mk-chip[aria-pressed=true]{background:var(--forest);border-color:var(--forest);color:#fff}
.mk-tag{display:inline-flex;align-items:center;gap:.35rem;padding:.3rem .5rem .3rem .75rem;border-radius:999px;font-size:.8rem;background:var(--mint);color:var(--forest)}
.mk-in{width:100%;border:1px solid #DDD4C1;border-radius:.75rem;padding:.65rem .8rem;background:#fff;font-size:1rem}
.mk-in:focus,.mk-search input:focus-visible{outline:2px solid var(--forest2);outline-offset:1px}
.mk-lbl{display:block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:#5A625B;margin-bottom:.3rem}
.mk-btn{display:flex;align-items:center;justify-content:center;gap:.5rem;width:100%;padding:.8rem 1rem;border-radius:.8rem;font-weight:700;text-align:center;transition:opacity .15s}
.mk-btn:hover{opacity:.9}
.mk-wa{background:#25D366;color:#fff}.mk-solid{background:var(--forest);color:#fff}
.mk-line{border:1px solid var(--forest);color:var(--forest);background:#fff;margin-top:.5rem}
.mk-safe{border-radius:.9rem;padding:1rem;font-size:.85rem;line-height:1.55;background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12}
.mk-fab{position:fixed;right:1rem;bottom:calc(1rem + env(safe-area-inset-bottom));z-index:40;display:flex;align-items:center;gap:.4rem;padding:.85rem 1.25rem;border-radius:999px;background:var(--coral);color:#fff;font-weight:700;box-shadow:0 6px 18px rgba(0,0,0,.22)}
@media(min-width:768px){.mk-fab{display:none}}
.mk-bar{position:fixed;left:0;right:0;bottom:0;z-index:40;display:flex;gap:.6rem;align-items:center;padding:.6rem 1rem calc(.6rem + env(safe-area-inset-bottom));background:#fff;border-top:1px solid var(--line);box-shadow:0 -4px 14px rgba(0,0,0,.06)}
.mk-bar .mk-btn{padding:.75rem}
@media(min-width:768px){.mk-bar{display:none}}
.mk-gal{display:flex;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;border-radius:1rem;background:var(--paper-2)}
.mk-gal::-webkit-scrollbar{display:none}
.mk-gal img{flex:0 0 100%;width:100%;aspect-ratio:4/3;object-fit:contain;scroll-snap-align:center;background:#1f2a24}
.mk-row{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(10.5rem,1fr);gap:.75rem;overflow-x:auto;scrollbar-width:none;padding-bottom:.25rem}
.mk-row::-webkit-scrollbar{display:none}
@media(min-width:1024px){.mk-row{grid-auto-columns:calc((100% - 2.25rem)/4)}}
.mk-tile{display:flex;flex-direction:column;align-items:center;gap:.4rem;padding:.9rem .4rem;border-radius:1rem;border:1.5px solid var(--line);background:#fff;font-size:.82rem;font-weight:600;text-align:center;cursor:pointer}
.mk-tile .ic{color:var(--forest)}
input:checked+.mk-tile{border-color:var(--forest);background:var(--mint)}
input:focus-visible+.mk-tile{outline:2px solid var(--forest2)}
.mk-thumb{position:relative;width:5.5rem;height:5.5rem;border-radius:.7rem;overflow:hidden;background:var(--paper-2)}
.mk-thumb img{width:100%;height:100%;object-fit:cover}
.mk-thumb .x{position:absolute;right:.2rem;top:.2rem;width:1.5rem;height:1.5rem;border-radius:999px;background:rgba(0,0,0,.6);color:#fff;font-size:.9rem;line-height:1.5rem;text-align:center}
.mk-thumb .cv{position:absolute;left:0;right:0;bottom:0;font-size:.65rem;font-weight:700;text-align:center;padding:.15rem;color:#fff;background:rgba(27,67,50,.85)}
.mk-add{width:5.5rem;height:5.5rem;border-radius:.7rem;border:1.5px dashed #BDB29A;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:.2rem;font-size:.72rem;color:#5A625B;cursor:pointer}
[hidden]{display:none!important}
"""


def _head(ctx, title, desc, fname, faq=None, extra_ld=None, noindex=False, extra=""):
    head = ctx["hub_head"](title, desc, fname, faq=faq, extra_ld=extra_ld)
    if noindex:
        head = head.replace('<meta name="robots" content="max-image-preview:large">',
                            '<meta name="robots" content="noindex,follow">')
    return head.replace("</head>", f"<style>{MK_CSS}</style>{extra}\n</head>")


# ── strings the client JS needs (translated by build_i18n like any text) ─────

def _strings():
    keys = {
        "free": "Free", "per": "per", "month": "month", "week": "week", "day": "day",
        "new": "New", "used": "Used", "parts": "For parts", "nophoto": "No photo",
        "justnow": "just now", "ago_m": "min ago", "ago_h": "h ago", "yesterday": "yesterday",
        "ago_d": "days ago", "ad1": "ad", "adN": "ads", "save": "Save", "saved": "Saved",
        "forsale": "For sale", "forrent": "For rent", "sold": "Sold", "gone": "No longer listed",
        "about": "about", "or": "or", "copied": "Link copied",
    }
    for k, lbl, one, _ in CATS:
        keys["c_" + k] = lbl
    return ('<div id="mk-str" hidden>' +
            "".join(f'<span data-k="{k}">{v}</span>' for k, v in keys.items()) + "</div>")


COMMON_JS = r"""
var S=(function(){var m={};[].forEach.call(document.querySelectorAll("#mk-str [data-k]"),function(e){m[e.getAttribute("data-k")]=e.textContent});return function(k){return m[k]||k}})();
var esc=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
var amt=function(n){return Number(n||0).toLocaleString("nl-NL",{maximumFractionDigits:0})};
function isProp(a){return a.category==="property"||a.section==="realestate"}
function isFree(a){return !isProp(a)&&!Number(a.price)}
function priceMain(a){
  if(isFree(a)) return S("free");
  var p=a.currency+" "+amt(a.price);
  if(a.deal==="rent") p+=" "+S("per")+" "+S(a.period||"month");
  return p;
}
function ago(ts){
  var s=Date.now()/1000-ts; if(!ts||s<0) return "";
  if(s<120) return S("justnow");
  if(s<3600) return Math.floor(s/60)+" "+S("ago_m");
  if(s<86400) return Math.floor(s/3600)+" "+S("ago_h");
  if(s<172800) return S("yesterday");
  if(s<86400*30) return Math.floor(s/86400)+" "+S("ago_d");
  return new Date(ts*1000).toLocaleDateString("nl-NL",{day:"numeric",month:"short"});
}
function ts(a){return Number(a.bumped||a.created||0)}
var LS={get:function(k){try{return JSON.parse(localStorage.getItem(k)||"[]")}catch(e){return []}},
        set:function(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
function isSaved(s){return LS.get("esr-mk-saved").indexOf(s)>=0}
function toggleSave(s){var l=LS.get("esr-mk-saved"),i=l.indexOf(s);if(i>=0)l.splice(i,1);else l.unshift(s);LS.set("esr-mk-saved",l.slice(0,200));return i<0}
var HEART='__HEART__', CAM='__CAM__';
function card(a,base){
  var imgs=a.images||[], img=imgs[0]||"", dead=a.status==="sold"||a.status==="expired";
  var fresh=!dead&&(Date.now()/1000-Number(a.created||0))<86400;
  var pill=dead?'<span class="mk-pill dark">'+S(a.status==="sold"?"sold":"gone")+'</span>'
    :(fresh?'<span class="mk-pill">'+S("new")+'</span>'
    :(a.seller&&a.seller.verified?'<span class="mk-pill ok">&#10003;</span>':''));
  var meta=[];
  if(isProp(a)) meta.push(S(a.deal==="rent"?"forrent":"forsale"));
  else if(a.cond) meta.push(S(a.cond));
  meta.push(esc(a.area||a.district)); var t=ago(ts(a)); if(t) meta.push(t);
  var sv=isSaved(a.slug);
  return '<div class="mk-card'+(dead?' opacity-60':'')+'"><a href="'+base+esc(a.slug)+'/">'
    +'<div class="mk-ph">'+(img?'<img src="'+esc(img)+'" alt="'+esc(a.title)+'" loading="lazy" decoding="async" width="400" height="400">'
      :'<div class="mk-noph">'+S("nophoto")+'</div>')+pill
    +(imgs.length>1?'<span class="mk-cnt">'+CAM+imgs.length+'</span>':'')+'</div>'
    +'<p class="mk-pr'+(isFree(a)?' free':'')+'">'+esc(priceMain(a))+'</p>'
    +'<h3 class="mk-t" translate="no">'+esc(a.title)+'</h3>'
    +'<p class="mk-m">'+meta.join(" &middot; ")+'</p></a>'
    +'<button type="button" class="mk-heart" data-save="'+esc(a.slug)+'" aria-pressed="'+sv+'" aria-label="'+S("save")+'">'+HEART+'</button></div>';
}
document.addEventListener("click",function(e){
  var b=e.target.closest("[data-save]"); if(!b) return;
  e.preventDefault();
  var on=toggleSave(b.getAttribute("data-save"));
  document.querySelectorAll('[data-save="'+b.getAttribute("data-save")+'"]').forEach(function(x){x.setAttribute("aria-pressed",on)});
  document.dispatchEvent(new Event("mk-saved"));
});
""".replace("__HEART__", _svg(ICON_HEART, "w-5 h-5", "2")).replace(
    "__CAM__", _svg(ICON_CAM, "w-3.5 h-3.5", "2"))


# ── server rendered card (mirror of card() in COMMON_JS) ─────────────────────

def _card(ad, base, now, eager=False):
    imgs = ad.get("images") or []
    img = imgs[0] if imgs else ""
    dead = _is_dead(ad)
    fresh = not dead and (now - int(ad.get("created") or 0)) < 86400
    pill = ""
    if dead:
        pill = '<span class="mk-pill dark">' + ("Sold" if ad.get("status") == "sold" else "No longer listed") + "</span>"
    elif fresh:
        pill = '<span class="mk-pill">New</span>'
    elif (ad.get("seller") or {}).get("verified"):
        pill = '<span class="mk-pill ok">&#10003;</span>'
    meta = []
    if _is_prop(ad):
        meta.append("For rent" if ad.get("deal") == "rent" else "For sale")
    elif ad.get("cond") in COND_LABEL:
        meta.append(COND_LABEL[ad["cond"]])
    meta.append(_esc(ad.get("area") or ad.get("district", "")))
    ld = "eager\" fetchpriority=\"high" if eager else "lazy"
    photo = (f'<img src="{_esc(img)}" alt="{_esc(ad.get("title",""))}" loading="{ld}" decoding="async" width="400" height="400">'
             if img else '<div class="mk-noph">No photo</div>')
    cnt = (f'<span class="mk-cnt">{_svg(ICON_CAM, "w-3.5 h-3.5", "2")}{len(imgs)}</span>' if len(imgs) > 1 else "")
    return (
        f'<div class="mk-card{" opacity-60" if dead else ""}"><a href="{base}{_esc(ad["slug"])}/">'
        f'<div class="mk-ph">{photo}{pill}{cnt}</div>'
        f'<p class="mk-pr{" free" if _is_free(ad) else ""}">{_esc(_price_main(ad))}</p>'
        f'<h3 class="mk-t" translate="no">{_esc(ad.get("title",""))}</h3>'
        f'<p class="mk-m">{" &middot; ".join(meta)}</p></a>'
        f'<button type="button" class="mk-heart" data-save="{_esc(ad["slug"])}" aria-pressed="false" '
        f'aria-label="Save">{_svg(ICON_HEART, "w-5 h-5", "2")}</button></div>'
    )


# ── browse surface ───────────────────────────────────────────────────────────

def _build_browse(ctx, ads, table, now):
    live = [a for a in ads if not _is_dead(a)]
    n = len(live)
    counts = {k: sum(1 for a in live if a.get("category") == k) for k in CAT_KEYS}
    n_free = sum(1 for a in live if _is_free(a))

    def tile(key, label, icon, cnt):
        return (f'<button type="button" class="mk-cat" data-cat="{key}" aria-pressed="{"true" if key == "" else "false"}">'
                f'<span class="ic">{_svg(icon)}</span><span>{label}</span>'
                f'<span class="ct" data-ct="{key}">{cnt}</span></button>')

    rail = tile("", "All", ICON_ALL, n) + "".join(
        tile(k, lbl, ic, counts[k]) for k, lbl, _, ic in CATS if k != "other")
    rail += tile("free", "Free", ICON_FREE, n_free) + tile("other", "Other", CATS[-1][3], counts["other"])

    dist_opts = "".join(f'<option value="{d}">{d}</option>' for d in DISTRICTS)
    cards = "".join(_card(a, "", now, eager=(i < 2)) for i, a in enumerate(live[:PAGE]))

    faq = [
        ("Is it free to sell on the Explore Suriname Marketplace?",
         "Yes. Placing an ad is free. Fill in the form, sign in with Google at the end so you can edit "
         "your ad later, and it goes up. A new account's first ad gets a quick check by hand."),
        ("How do buyers contact me?",
         "Directly. A Suriname mobile number gets a WhatsApp button with a message that already names "
         "your ad. You can also give an email address or a link. We never show the email you sign in with."),
        ("How long does an ad stay online?",
         "Thirty days for items, sixty for property. Renew it with one tap from your ads page, and mark "
         "it sold the moment it goes."),
        ("Does Explore Suriname handle payments?",
         "No. You deal with the seller yourself. Meet somewhere busy, check the item before you pay, and "
         "never send money in advance to someone you have not met."),
    ]
    head = _head(ctx, "Marketplace Suriname: buy and sell new and second-hand",
                 "Buy and sell in Suriname: phones, furniture, cars, clothes, baby gear, tools and property. "
                 "Free to post, prices in SRD, USD and EUR, message sellers on WhatsApp.",
                 f"{SECTION_PATH}/", faq=faq)

    ld_list = {"@context": "https://schema.org", "@type": "ItemList",
               "itemListElement": [{"@type": "ListItem", "position": i + 1,
                                    "url": f'{ctx["SITE_URL"]}/{SECTION_PATH}/{a["slug"]}/'}
                                   for i, a in enumerate(live[:PAGE])]}
    if live:
        head = head.replace("</head>", '<script type="application/ld+json">'
                            + json.dumps(ld_list, ensure_ascii=False) + "</script>\n</head>")

    faq_html = "".join(
        f'<details class="border-b py-3" style="border-color:var(--line)"><summary class="font-semibold cursor-pointer">{q}</summary>'
        f'<p class="text-gray-600 text-sm mt-2 leading-relaxed">{a}</p></details>' for q, a in faq)

    body = r"""
<body class="bg-gray-50 overflow-x-hidden">
__NAV__
<div class="cat-hero">
  <div class="max-w-6xl mx-auto px-5 pt-8 pb-4">
    <div class="flex items-end justify-between gap-4 flex-wrap mb-4">
      <div>
        <h1 class="serif text-4xl sm:text-5xl" style="color:var(--forest);font-weight:400">Marketplace</h1>
        <p class="text-gray-600 mt-1">Buy and sell anything in Suriname. Message the seller on WhatsApp.</p>
      </div>
      <div class="hidden md:flex gap-2">
        <a href="../my-ads.html" class="px-4 py-2.5 rounded-full text-sm font-semibold border" style="border-color:var(--forest);color:var(--forest)">Your ads</a>
        <a href="../post-ad.html" class="px-5 py-2.5 rounded-full text-sm font-bold text-white flex items-center gap-1.5" style="background:var(--coral)">__PLUS__Sell something</a>
      </div>
    </div>
    <form id="mk-sf" class="mk-search" role="search" onsubmit="return false">
      <input id="f-q" type="search" enterkeyhint="search" autocomplete="off" placeholder="Search iPhone, bank, fiets, huis te huur" aria-label="Search the marketplace">
      <button type="submit" aria-label="Search">__SEARCH__<span class="hidden sm:inline">Search</span></button>
    </form>
    <div class="mk-rail mt-5" role="group" aria-label="Categories">__RAIL__</div>
  </div>
</div>

<main class="max-w-6xl mx-auto px-5 py-5 pb-24">
  <div class="flex items-center gap-2 flex-wrap mb-3">
    <p id="mk-count" class="text-sm font-semibold mr-auto w-full sm:w-auto" style="color:var(--ink)">__COUNT__</p>
    <button type="button" id="b-saved" class="mk-chip flex items-center gap-1.5" aria-pressed="false">__HEART_S__<span>Saved</span> <span id="n-saved" class="text-xs opacity-70"></span></button>
    <button type="button" id="b-filt" class="mk-chip flex items-center gap-1.5" aria-expanded="false" aria-controls="mk-filt">__FILT__Filters <span id="n-filt" class="text-xs"></span></button>
    <select id="f-sort" class="mk-chip" aria-label="Sort">
      <option value="new">Newest</option><option value="low">Lowest price</option><option value="high">Highest price</option>
    </select>
  </div>

  <div id="mk-filt" hidden class="bg-white rounded-2xl border p-4 mb-4" style="border-color:var(--line)">
    <div class="grid gap-4" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
      <label><span class="mk-lbl">District</span>
        <select id="f-d" class="mk-in"><option value="">All of Suriname</option>__DIST__</select></label>
      <div><span class="mk-lbl">Price in SRD</span>
        <div class="flex gap-2"><input id="f-min" class="mk-in" inputmode="numeric" placeholder="Min" aria-label="Minimum price in SRD"><input id="f-max" class="mk-in" inputmode="numeric" placeholder="Max" aria-label="Maximum price in SRD"></div></div>
      <div data-for="item"><span class="mk-lbl">Condition</span>
        <div class="flex gap-2 flex-wrap"><button type="button" class="mk-chip" data-f="cond" data-v="new" aria-pressed="false">New</button><button type="button" class="mk-chip" data-f="cond" data-v="used" aria-pressed="false">Used</button></div></div>
      <div data-for="property" hidden><span class="mk-lbl">Offer</span>
        <div class="flex gap-2 flex-wrap"><button type="button" class="mk-chip" data-f="deal" data-v="sale" aria-pressed="false">For sale</button><button type="button" class="mk-chip" data-f="deal" data-v="rent" aria-pressed="false">For rent</button></div></div>
      <label data-for="property" hidden><span class="mk-lbl">Bedrooms</span>
        <select id="f-beds" class="mk-in"><option value="">Any</option><option value="1">1+</option><option value="2">2+</option><option value="3">3+</option><option value="4">4+</option></select></label>
    </div>
  </div>
  <div id="mk-tags" class="flex flex-wrap gap-2 mb-4"></div>

  <section id="mk-recent" hidden class="mb-7">
    <h2 class="font-bold text-lg mb-3" style="color:var(--ink)">Recently viewed</h2>
    <div id="mk-recent-row" class="mk-row"></div>
  </section>

  <div id="mk-grid" class="mk-grid">__CARDS__</div>
  <div class="text-center mt-8"><button type="button" id="mk-more" hidden class="px-6 py-3 rounded-full font-semibold border bg-white" style="border-color:var(--forest);color:var(--forest)">Show more</button></div>

  <div id="mk-empty" hidden class="text-center py-12 px-4 bg-white rounded-2xl border" style="border-color:var(--line)">
    <div class="mx-auto mb-3 w-14 h-14 rounded-full flex items-center justify-center" style="background:var(--mint);color:var(--forest)">__TAG__</div>
    <h2 id="mk-empty-h" class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">Nothing here yet</h2>
    <p id="mk-empty-p" class="text-gray-600 max-w-md mx-auto mb-5">Try a different word or fewer filters.</p>
    <div class="flex gap-2 justify-center flex-wrap">
      <a id="mk-empty-sell" href="../post-ad.html" class="px-6 py-3 rounded-full font-bold text-white" style="background:var(--coral)">Sell something</a>
      <button type="button" id="mk-empty-clear" class="px-6 py-3 rounded-full font-semibold border" style="border-color:var(--forest);color:var(--forest)">Clear filters</button>
    </div>
  </div>

  <div class="mt-12 rounded-2xl p-6 sm:p-8 grid gap-6 sm:grid-cols-3" style="background:var(--paper-2)">
    <div><p class="font-bold mb-1" style="color:var(--forest)">1. Snap a few photos</p><p class="text-sm text-gray-600">Straight from your phone. We shrink them so the upload is quick on mobile data.</p></div>
    <div><p class="font-bold mb-1" style="color:var(--forest)">2. Set a price, or give it away</p><p class="text-sm text-gray-600">SRD, USD or EUR. Buyers see the other currencies worked out for them.</p></div>
    <div><p class="font-bold mb-1" style="color:var(--forest)">3. Buyers message you</p><p class="text-sm text-gray-600">On WhatsApp, with your ad already named. Free, no commission.</p></div>
    <div class="sm:col-span-3"><a href="../post-ad.html" class="inline-block px-6 py-3 rounded-full font-bold text-white" style="background:var(--forest)">Place a free ad</a>
      <a href="../my-ads.html" class="ml-3 text-sm font-semibold underline" style="color:var(--forest)">Manage your ads</a></div>
  </div>

  <div class="mt-8">__SAFE__</div>
  <section class="mt-10 max-w-3xl"><h2 class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">Questions</h2>__FAQ__</section>
  __STR__
</main>
<a href="../post-ad.html" class="mk-fab">__PLUS__Sell</a>
__FOOTER__
<script>
(function(){
__COMMON__
var API=__API__, RATES=__RATES__, ADS=__ADS__;
var $=function(i){return document.getElementById(i)};
var F={c:"",q:"",d:"",min:"",max:"",cond:"",deal:"",beds:"",sort:"new",saved:""}, SHOWN=__PAGE__;
var KEYS=Object.keys(F);
function readURL(){
  var p=new URLSearchParams(location.search);
  KEYS.forEach(function(k){ if(p.get(k)!=null) F[k]=p.get(k); });
}
function writeURL(){
  var p=new URLSearchParams();
  KEYS.forEach(function(k){ if(F[k]&&!(k==="sort"&&F[k]==="new")) p.set(k,F[k]); });
  var s=p.toString();
  try{ history.replaceState(null,"",location.pathname+(s?"?"+s:"")); }catch(e){}
}
function srd(a){ return Number(a.price||0)*(RATES[a.currency]||1); }
function norm(s){ return String(s||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,""); }
function live(){ return ADS.filter(function(a){return a.status==="live"}); }
function match(a,skipCat){
  if(!skipCat){
    if(F.c==="free"){ if(!isFree(a)) return false; }
    else if(F.c&&a.category!==F.c) return false;
  }
  if(F.saved&&!isSaved(a.slug)) return false;
  if(F.d&&a.district!==F.d) return false;
  if(F.min&&srd(a)<Number(F.min)) return false;
  if(F.max&&srd(a)>Number(F.max)) return false;
  if(F.cond&&a.cond!==F.cond) return false;
  if(F.c==="property"){
    if(F.deal&&a.deal!==F.deal) return false;
    if(F.beds&&Number(a.beds||0)<Number(F.beds)) return false;
  }
  if(F.q){
    var hay=norm([a.title,a.descr,a.area,a.district,a.make,a.model,S("c_"+a.category)].join(" "));
    var words=norm(F.q).split(/\s+/).filter(Boolean);
    for(var i=0;i<words.length;i++) if(hay.indexOf(words[i])<0) return false;
  }
  return true;
}
function syncControls(){
  $("f-q").value=F.q; $("f-d").value=F.d; $("f-min").value=F.min; $("f-max").value=F.max;
  $("f-sort").value=F.sort; $("f-beds").value=F.beds;
  document.querySelectorAll(".mk-cat").forEach(function(b){ b.setAttribute("aria-pressed", b.dataset.cat===F.c); });
  document.querySelectorAll("[data-f]").forEach(function(b){ b.setAttribute("aria-pressed", F[b.dataset.f]===b.dataset.v); });
  var prop=F.c==="property";
  document.querySelectorAll('[data-for="property"]').forEach(function(e){e.hidden=!prop});
  document.querySelectorAll('[data-for="item"]').forEach(function(e){e.hidden=prop});
  $("b-saved").setAttribute("aria-pressed", !!F.saved);
  var ns=LS.get("esr-mk-saved").length; $("n-saved").textContent=ns?"("+ns+")":"";
}
function tags(){
  var t=[], lbl={d:F.d, min:F.min?"SRD "+amt(F.min)+"+":"", max:F.max?"< SRD "+amt(F.max):"",
    cond:F.cond?S(F.cond):"", deal:F.deal&&F.c==="property"?S(F.deal==="rent"?"forrent":"forsale"):"",
    beds:F.beds&&F.c==="property"?F.beds+"+":"", q:F.q?'"'+F.q+'"':""};
  Object.keys(lbl).forEach(function(k){ if(lbl[k]) t.push('<span class="mk-tag">'+esc(lbl[k])+'<button type="button" data-clear="'+k+'" aria-label="Remove" class="w-5 h-5 rounded-full hover:bg-white">&times;</button></span>'); });
  var n=["d","min","max","cond","deal","beds"].filter(function(k){return lbl[k]}).length;
  $("n-filt").textContent=n?"("+n+")":"";
  if(t.length>1) t.push('<button type="button" data-clear="*" class="text-sm underline" style="color:var(--forest)">Clear all</button>');
  $("mk-tags").innerHTML=t.join("");
}
function counts(){
  var L=live().filter(function(a){return match(a,true)});
  document.querySelectorAll("[data-ct]").forEach(function(e){
    var k=e.getAttribute("data-ct");
    e.textContent=L.filter(function(a){return !k||(k==="free"?isFree(a):a.category===k)}).length;
  });
}
function recent(){
  var seen=LS.get("esr-mk-seen"), by={};
  live().forEach(function(a){by[a.slug]=a});
  var list=seen.map(function(s){return by[s]}).filter(Boolean).slice(0,8);
  var quiet=!F.c&&!F.q&&!F.saved&&!F.d&&!F.min&&!F.max&&!F.cond;
  $("mk-recent").hidden=!(quiet&&list.length);
  $("mk-recent-row").innerHTML=list.map(function(a){return card(a,"")}).join("");
}
function apply(keepShown){
  if(!keepShown) SHOWN=__PAGE__;
  var out=live().filter(function(a){return match(a,false)});
  out.sort(function(x,y){
    if(F.sort==="low") return srd(x)-srd(y);
    if(F.sort==="high") return srd(y)-srd(x);
    return ts(y)-ts(x);
  });
  $("mk-grid").innerHTML=out.slice(0,SHOWN).map(function(a){return card(a,"")}).join("");
  $("mk-more").hidden=out.length<=SHOWN;
  $("mk-count").textContent=out.length+" "+S(out.length===1?"ad1":"adN")+(F.c?" \u00B7 "+S(F.c==="free"?"free":"c_"+F.c):"");
  var empty=!out.length; $("mk-empty").hidden=!empty;
  if(empty){
    var none=!live().length, sell=$("mk-empty-sell");
    $("mk-empty-clear").hidden=none;
    if(none){
      $("mk-empty-h").textContent="The marketplace just opened";
      $("mk-empty-p").textContent="Be one of the first sellers. Early ads get seen by everyone who visits, and it is free.";
    } else if(F.saved){
      $("mk-empty-h").textContent="Nothing saved yet";
      $("mk-empty-p").textContent="Tap the heart on any ad to keep it here, on this device.";
    } else if(F.c&&F.c!=="free"&&!F.q){
      $("mk-empty-h").textContent="Be the first to sell in "+S("c_"+F.c);
      $("mk-empty-p").textContent="Nobody has listed anything here yet, so yours would be the only one people see.";
    } else {
      $("mk-empty-h").textContent="Nothing matches that yet";
      $("mk-empty-p").textContent="Try a different word or fewer filters. New ads come in every day.";
    }
    sell.href="../post-ad.html"+(F.c&&F.c!=="free"?"?c="+F.c:"");
  }
  syncControls(); tags(); counts(); recent(); writeURL();
}
document.querySelectorAll(".mk-cat").forEach(function(b){ b.addEventListener("click",function(){
  F.c=b.dataset.cat; if(F.c!=="property"){F.deal="";F.beds="";} apply();
  b.scrollIntoView({block:"nearest",inline:"center",behavior:"smooth"});
}); });
document.querySelectorAll("[data-f]").forEach(function(b){ b.addEventListener("click",function(){
  var k=b.dataset.f; F[k]=F[k]===b.dataset.v?"":b.dataset.v; apply();
}); });
var qt; $("f-q").addEventListener("input",function(){ clearTimeout(qt); qt=setTimeout(function(){F.q=$("f-q").value.trim(); apply();},200); });
$("mk-sf").addEventListener("submit",function(){ F.q=$("f-q").value.trim(); apply(); $("f-q").blur(); });
[["f-d","d"],["f-sort","sort"],["f-beds","beds"]].forEach(function(p){ $(p[0]).addEventListener("change",function(){F[p[1]]=$(p[0]).value; apply();}); });
[["f-min","min"],["f-max","max"]].forEach(function(p){ $(p[0]).addEventListener("change",function(){F[p[1]]=$(p[0]).value.replace(/\D/g,""); apply();}); });
$("b-filt").addEventListener("click",function(){ var h=$("mk-filt").hidden; $("mk-filt").hidden=!h; $("b-filt").setAttribute("aria-expanded",h); });
$("b-saved").addEventListener("click",function(){ F.saved=F.saved?"":"1"; apply(); });
$("mk-more").addEventListener("click",function(){ SHOWN+=__PAGE__; apply(true); });
$("mk-empty-clear").addEventListener("click",function(){ KEYS.forEach(function(k){F[k]=k==="sort"?"new":""}); apply(); });
$("mk-tags").addEventListener("click",function(e){
  var b=e.target.closest("[data-clear]"); if(!b) return;
  var k=b.dataset.clear;
  if(k==="*") ["q","d","min","max","cond","deal","beds"].forEach(function(x){F[x]=""}); else F[k]="";
  apply();
});
document.addEventListener("mk-saved",function(){ if(F.saved) apply(true); else syncControls(); });
readURL();
if(F.d||F.min||F.max||F.cond||F.deal||F.beds) { $("mk-filt").hidden=false; $("b-filt").setAttribute("aria-expanded","true"); }
apply();
var on=document.querySelector('.mk-cat[aria-pressed="true"]'); if(on&&F.c) on.scrollIntoView({block:"nearest",inline:"center"});
// Re-read the live feed so an ad posted since the last build is already here.
fetch(API+"/market/approved?s=__SECT__").then(function(r){return r.json()}).then(function(j){
  if(Array.isArray(j)){ ADS=j; apply(true); }
}).catch(function(){});
})();
</script>
</body>
</html>
"""
    count = f'{n} ad{"" if n == 1 else "s"}'
    rep = {
        "__NAV__": ctx["nav_html"]("marketplace", "../"),
        "__FOOTER__": ctx["footer_html"]("../"),
        "__RAIL__": rail, "__DIST__": dist_opts, "__CARDS__": cards, "__COUNT__": count,
        "__SAFE__": _safety(), "__FAQ__": faq_html, "__STR__": _strings(),
        "__PLUS__": _svg(ICON_PLUS, "w-4 h-4", "2.5"),
        "__SEARCH__": _svg("M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3", "w-5 h-5", "2.2"),
        "__HEART_S__": _svg(ICON_HEART, "w-4 h-4", "2"),
        "__FILT__": _svg("M4 6h16M7 12h10M10 18h4", "w-4 h-4", "2.2"),
        "__TAG__": _svg(CATS[-1][3], "w-7 h-7"),
        "__COMMON__": COMMON_JS,
        "__API__": json.dumps(MK_API), "__RATES__": json.dumps(table),
        "__ADS__": json.dumps(live[:600], ensure_ascii=False).replace("</", "<\\/"),
        "__PAGE__": str(PAGE), "__SECT__": SECTION,
    }
    for k, v in rep.items():
        body = body.replace(k, v)
    return head + body


# ── one ad ───────────────────────────────────────────────────────────────────

def _similar(ad, pool, n=8):
    same = [a for a in pool if a["slug"] != ad["slug"] and a.get("category") == ad.get("category")]
    rest = [a for a in pool if a["slug"] != ad["slug"] and a.get("category") != ad.get("category")]
    return (same + rest)[:n]


def _build_detail(ctx, ad, table, pool, now):
    slug = ad["slug"]
    page_url = f'{ctx["SITE_URL"]}/{SECTION_PATH}/{slug}/'
    dead = _is_dead(ad)
    imgs = ad.get("images") or []
    cat_key = ad.get("category") if ad.get("category") in CAT_LABEL else "other"
    cat = CAT_ONE.get(cat_key, "Item")
    where = ad.get("district", "")
    if ad.get("area"):
        where = f'{ad["area"]}, {where}'
    title = _esc(ad.get("title", ""))
    price = _price_main(ad)

    if _is_prop(ad):
        lead = f'{"For rent" if ad.get("deal") == "rent" else "For sale"} in {where}'
    else:
        lead = " &middot; ".join(x for x in [COND_LABEL.get(ad.get("cond"), ""), _esc(where)] if x)
    meta_desc = (f'{html_lib.unescape(ad.get("title",""))}: {price}, {html_lib.unescape(lead).replace(" · ", ", ")}. '
                 + html_lib.unescape(ad.get("descr", ""))[:180]).strip()
    meta_desc = _esc(re.sub(r"\s+", " ", meta_desc))[:300]

    cond_url = {"new": "NewCondition", "used": "UsedCondition", "parts": "DamagedCondition"}.get(ad.get("cond"))
    ld = {
        "@context": "https://schema.org", "@type": "Product",
        "name": html_lib.unescape(ad.get("title", "")), "url": page_url,
        "description": html_lib.unescape(ad.get("descr", ""))[:900] or html_lib.unescape(ad.get("title", "")),
        "category": CAT_LABEL.get(cat_key),
        "offers": {
            "@type": "Offer", "url": page_url,
            "price": ad.get("price") or 0, "priceCurrency": ad.get("currency", "SRD"),
            "availability": "https://schema.org/SoldOut" if dead else "https://schema.org/InStock",
            "areaServed": {"@type": "Place", "name": ad.get("district", "Suriname")},
            "availableAtOrFrom": {"@type": "Place", "address": _postal(ad)},
        },
    }
    if cond_url:
        ld["itemCondition"] = f"https://schema.org/{cond_url}"
        ld["offers"]["itemCondition"] = ld["itemCondition"]
    if imgs:
        ld["image"] = imgs

    og = ""
    if imgs:
        og = (f'\n  <meta property="og:image" content="{_esc(imgs[0])}">'
              f'\n  <meta name="twitter:image" content="{_esc(imgs[0])}">')
    head = _head(ctx, title, meta_desc, f"{SECTION_PATH}/{slug}/", extra_ld=ld, noindex=dead)
    if og:
        # The ad's own photo beats the site logo when the link lands in WhatsApp.
        head = re.sub(r'\n  <meta property="og:image" content="[^"]*">', "", head, count=1)
        head = re.sub(r'\n  <meta name="twitter:image" content="[^"]*">', "", head, count=1)
        head = head.replace("</head>", og + "\n</head>")

    FP, LZ = 'fetchpriority="high"', 'loading="lazy"'
    if imgs:
        gal = ('<div class="relative"><div id="mk-gal" class="mk-gal">' + "".join(
            f'<img src="{_esc(u)}" alt="{title}{" photo " + str(i + 1) if i else ""}" width="900" height="675" '
            f'{FP if i == 0 else LZ} decoding="async">'
            for i, u in enumerate(imgs)) + '</div>'
            + (f'<span id="mk-gi" class="mk-cnt" style="left:auto;right:.75rem;bottom:.75rem">1 / {len(imgs)}</span>' if len(imgs) > 1 else "")
            + "</div>")
        if len(imgs) > 1:
            gal += ('<div class="hidden md:flex gap-2 mt-3 overflow-x-auto pb-1">' + "".join(
                f'<button type="button" data-go="{i}" class="shrink-0 rounded-lg overflow-hidden border-2" '
                f'style="border-color:{"var(--forest)" if i == 0 else "transparent"}" aria-label="Photo {i + 1}">'
                f'<img src="{_esc(u)}" alt="" width="96" height="72" loading="lazy" class="w-24 h-[72px] object-cover"></button>'
                for i, u in enumerate(imgs)) + "</div>")
    else:
        gal = ('<div class="w-full rounded-2xl flex items-center justify-center" '
               'style="aspect-ratio:4/3;background:var(--paper-2);color:#656C63">No photos on this ad</div>')

    banner = ""
    if dead:
        word = "This has been sold." if ad.get("status") == "sold" else "This ad has expired."
        banner = ('<div class="rounded-xl p-4 mb-5 text-sm font-semibold" '
                  f'style="background:#EFEFEF;border:1px solid #D8D8D8;color:#3F3F3F">{word} '
                  f'<a href="../?c={cat_key}" class="underline">See similar ads</a>.</div>')

    spec_rows = ('<dl class="grid gap-x-6 text-sm" style="grid-template-columns:repeat(auto-fit,minmax(240px,1fr))">'
                 + "".join(f'<div class="flex justify-between gap-3 border-b py-2.5" style="border-color:#EDE7DA">'
                           f'<dt style="color:#5A625B">{k}</dt><dd class="font-semibold text-gray-900 text-right">{v}</dd></div>'
                           for k, v in _spec_pairs(ad)) + "</dl>")

    seller = ad.get("seller") or {}
    seller_html = ""
    if seller.get("name"):
        badge = ""
        if seller.get("verified"):
            badge = (' <span class="px-2 py-0.5 rounded-full text-xs font-semibold text-white" '
                     f'style="background:var(--forest)">{_esc(seller.get("vlabel") or "Verified seller")}</span>')
        initial = _esc(seller["name"].strip()[:1].upper() or "?")
        seller_html = (
            '<div class="flex items-center gap-3 mb-4">'
            f'<span class="w-11 h-11 rounded-full flex items-center justify-center font-bold text-white" style="background:var(--forest2)">{initial}</span>'
            f'<div><p class="text-xs" style="color:#6B7280">Seller</p><p class="font-semibold text-gray-900" translate="no">{_esc(seller["name"])}{badge}</p></div></div>')

    addr_block = ""
    if _is_prop(ad) and ad.get("show_addr") and ad.get("address"):
        q = urllib.parse.quote(f'{ad["address"]}, {ad.get("area") or ad.get("district","")}, Suriname')
        addr_block = (
            '<p class="mb-3" style="color:#5A625B"><b class="text-gray-900" translate="no">'
            + _esc(ad["address"]) + '</b> &middot; '
            f'<a href="https://www.google.com/maps/search/?api=1&amp;query={q}" target="_blank" '
            'rel="noopener" class="underline" style="color:var(--forest2)">Directions</a></p>')

    posted = datetime.fromtimestamp(ad["created"], timezone.utc).strftime("%d %B %Y") if ad.get("created") else ""
    alt = _price_alt(ad, table)
    contact = "" if dead else _contact_block(ad, page_url)
    primary = "" if dead else _primary_contact(ad, page_url, short=True)

    sim = _similar(ad, pool)
    sim_html = ""
    if sim:
        sim_html = ('<section class="mt-12"><div class="flex items-baseline justify-between mb-3">'
                    '<h2 class="font-bold text-xl" style="color:var(--ink)">More like this</h2>'
                    f'<a href="../?c={cat_key}" class="text-sm font-semibold underline" style="color:var(--forest)">See all</a></div>'
                    '<div class="mk-row">' + "".join(_card(a, "../", now) for a in sim) + "</div></section>")

    share_text = f'{html_lib.unescape(ad.get("title",""))}, {price}'
    body = r"""
<body class="bg-gray-50 overflow-x-hidden">
__NAV__
<main class="max-w-6xl mx-auto px-5 py-6 __PADB__">
  <nav aria-label="Breadcrumb" class="text-sm mb-4 truncate" style="color:#656C63">
    <a href="../../" class="hover:underline">Home</a> &rsaquo;
    <a href="../" class="hover:underline">Marketplace</a> &rsaquo;
    <a href="../?c=__CATKEY__" class="hover:underline">__CATL__</a>
  </nav>
  __BANNER__
  <div class="grid gap-8 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
    <div>
      __GAL__
      <div class="md:hidden mt-5">
        <p class="text-3xl font-extrabold __FREEC__">__PRICE__</p>
        __ALT__
      </div>
      <h1 translate="no" class="serif text-3xl mt-3 md:mt-6 mb-1" style="color:var(--forest);font-weight:400">__TITLE__</h1>
      <p class="mb-3" style="color:#5A625B">__LEAD__ &middot; <span data-ago="__TS__"></span></p>
      <div class="flex gap-2 mb-6">
        <button type="button" class="mk-chip flex items-center gap-1.5 mk-savebtn" data-save="__SLUG__" aria-pressed="false">__HEART__<span>Save</span></button>
        <button type="button" id="mk-share" class="mk-chip flex items-center gap-1.5">__SHARE__Share</button>
      </div>
      __ADDR__
      __SPECS__
      <h2 class="font-bold text-lg mt-7 mb-2" style="color:var(--ink)">Description</h2>
      <p translate="no" class="text-gray-700 leading-relaxed" style="white-space:pre-wrap">__DESCR__</p>
      <p class="text-xs mt-6" style="color:#656C63">Posted __POSTED__. Explore Suriname did not write this ad and does not inspect items.
        <button type="button" id="mk-report" class="underline" style="color:#656C63">Report this ad</button></p>
    </div>
    <aside>
      <div class="md:sticky md:top-4">
        <div class="bg-white rounded-2xl shadow-sm border border-gray-100 p-5 mb-5">
          <p class="hidden md:block text-3xl font-extrabold mb-1 __FREEC__">__PRICE__</p>
          <div class="hidden md:block">__ALT__</div>
          __SELLER__
          __CONTACT__
        </div>
        __SAFE__
      </div>
    </aside>
  </div>
  __SIMILAR__
  __STR__
</main>
__BAR__
__FOOTER__
<script>
(function(){
__COMMON__
var SLUG=__SLUGJS__, API=__API__;
document.querySelectorAll("[data-ago]").forEach(function(e){ e.textContent=ago(Number(e.getAttribute("data-ago"))); });
function paintSave(){ document.querySelectorAll("[data-save]").forEach(function(b){ b.setAttribute("aria-pressed", isSaved(b.getAttribute("data-save"))); }); }
paintSave(); document.addEventListener("mk-saved",paintSave);
// recently viewed, newest first, read by the browse page
var seen=LS.get("esr-mk-seen").filter(function(s){return s!==SLUG}); seen.unshift(SLUG); LS.set("esr-mk-seen",seen.slice(0,20));
// gallery: native swipe on phones, thumbnails on desktop
var g=document.getElementById("mk-gal"), gi=document.getElementById("mk-gi"), th=document.querySelectorAll("[data-go]");
if(g){
  var n=g.children.length;
  g.addEventListener("scroll",function(){
    var i=Math.round(g.scrollLeft/g.clientWidth);
    if(gi) gi.textContent=(i+1)+" / "+n;
    th.forEach(function(b,j){ b.style.borderColor=j===i?"var(--forest)":"transparent"; });
  },{passive:true});
  th.forEach(function(b){ b.addEventListener("click",function(){ g.scrollTo({left:g.clientWidth*Number(b.dataset.go),behavior:"smooth"}); }); });
}
var sh=document.getElementById("mk-share");
sh.addEventListener("click",function(){
  var d={title:__SHARET__, text:__SHARET__, url:location.href.split("?")[0]};
  if(navigator.share){ navigator.share(d).catch(function(){}); return; }
  try{ navigator.clipboard.writeText(d.url); sh.lastChild.textContent=S("copied"); }catch(e){}
  window.open("https://wa.me/?text="+encodeURIComponent(d.text+"\n"+d.url),"_blank","noopener");
});
var rep=document.getElementById("mk-report");
rep.addEventListener("click",function(){
  var why=prompt("What is wrong with this ad? (scam, already sold, wrong details, offensive)");
  if(why===null) return;
  fetch(API+"/market/report",{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify({slug:SLUG,reason:"other",detail:why})})
    .then(function(){rep.textContent="Reported. Thank you."})
    .catch(function(){rep.textContent="Could not send that just now."});
});
})();
</script>
</body>
</html>
"""
    bar = ""
    if primary:
        bar = (f'<div class="mk-bar"><div class="min-w-0 flex-1"><p class="font-extrabold truncate {"text-green-800" if _is_free(ad) else ""}">{_esc(price)}</p>'
               f'<p class="text-xs truncate" style="color:#6B7280" translate="no">{title}</p></div>'
               f'<div style="flex:0 0 46%">{primary}</div></div>')
    rep = {
        "__NAV__": ctx["nav_html"]("marketplace", "../../"),
        "__FOOTER__": ctx["footer_html"]("../../"),
        "__PADB__": "pb-28 md:pb-10" if bar else "pb-10",
        "__CATKEY__": cat_key, "__CATL__": CAT_LABEL[cat_key], "__BANNER__": banner, "__GAL__": gal,
        "__PRICE__": _esc(price), "__FREEC__": "text-green-800" if _is_free(ad) else "text-gray-900",
        "__ALT__": f'<p class="text-sm mb-4" style="color:#656C63">{_esc(alt)}</p>' if alt else '<div class="mb-3"></div>',
        "__TITLE__": title, "__LEAD__": lead, "__TS__": str(_ts(ad)), "__SLUG__": _esc(slug),
        "__HEART__": _svg(ICON_HEART, "w-4 h-4", "2"), "__SHARE__": _svg(ICON_SHARE, "w-4 h-4", "2"),
        "__ADDR__": addr_block, "__SPECS__": spec_rows,
        "__DESCR__": _esc(ad.get("descr", "")) or "The seller did not add a description.",
        "__POSTED__": posted, "__SELLER__": seller_html,
        "__CONTACT__": contact or '<p class="text-sm" style="color:#656C63">Contact details are no longer shown for this ad.</p>',
        "__SAFE__": _safety(ad), "__SIMILAR__": sim_html, "__STR__": _strings(), "__BAR__": bar,
        "__COMMON__": COMMON_JS, "__SLUGJS__": json.dumps(slug), "__API__": json.dumps(MK_API),
        "__SHARET__": json.dumps(share_text, ensure_ascii=False).replace("</", "<\\/"),
    }
    for k, v in rep.items():
        body = body.replace(k, v)
    return head + body


# ── shared client bits for the two signed-in pages ───────────────────────────

def _gsi_head(ctx):
    if not ctx.get("GOOGLE_CLIENT_ID"):
        return ""
    return '\n  <script src="https://accounts.google.com/gsi/client" async defer></script>'


def _auth_js(ctx):
    """
    The ID token lives in sessionStorage and the Worker verifies it on every
    call, so there is no session to expire badly: a 401 just brings the Google
    button back.
    """
    return """
var API = %s, CID = %s;
var TOK = null;
try { TOK = sessionStorage.getItem("esr-mk-idt"); } catch(e) {}
function setTok(t){ TOK=t; try{ sessionStorage.setItem("esr-mk-idt",t); }catch(e){} }
function clearTok(){ TOK=null; try{ sessionStorage.removeItem("esr-mk-idt"); }catch(e){} }
function onCred(r){ setTok(r.credential); onSignedIn(); }
function mountSignIn(el){
  function go(){
    if(!CID || !window.google || !google.accounts){ el.innerHTML='<p class="text-sm" style="color:#656C63">Sign-in is unavailable right now. Please try again shortly.</p>'; return; }
    google.accounts.id.initialize({ client_id: CID, callback: onCred });
    google.accounts.id.renderButton(el, { theme:"outline", size:"large", text:"continue_with", shape:"pill" });
  }
  if(window.google && window.google.accounts) go(); else window.addEventListener("load", go);
}
""" % (json.dumps(MK_API), json.dumps(ctx.get("GOOGLE_CLIENT_ID") or ""))


# ── post an ad ───────────────────────────────────────────────────────────────

def _build_post(ctx):
    tiles = "".join(
        f'<label><input type="radio" name="category" value="{k}" class="sr-only">'
        f'<span class="mk-tile"><span class="ic">{_svg(ic, "w-7 h-7")}</span>{lbl}</span></label>'
        for k, lbl, _, ic in CATS)
    dist_opts = "".join(f'<option value="{d}">{d}</option>' for d in DISTRICTS)
    cur_opts = "".join(f'<option value="{c}">{c}</option>' for c in CURRENCIES)
    per_opts = "".join(f'<option value="{k}">{lbl}</option>' for k, lbl in PERIODS)
    cond_chips = "".join(
        f'<label><input type="radio" name="cond" value="{k}" class="sr-only"><span class="mk-tile" style="padding:.6rem 1rem;flex-direction:row">{lbl}</span></label>'
        for k, lbl in CONDS)
    ts_key = ctx.get("TURNSTILE_SITEKEY") or ""
    ts_head = ('<script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>'
               if ts_key else "")
    ts_box = (f'<div class="cf-turnstile mt-4" data-sitekey="{ts_key}" data-theme="light"></div>' if ts_key else "")

    head = _head(ctx, "Sell something in Suriname: place a free ad",
                 "Sell your phone, furniture, car, clothes or property in Suriname. Free, takes about a "
                 "minute, and buyers message you straight on WhatsApp.",
                 "post-ad.html", extra=_gsi_head(ctx) + "\n  " + ts_head)

    body = r"""
<body class="bg-gray-50 overflow-x-hidden">
__NAV__
<div class="cat-hero">
  <div class="max-w-2xl mx-auto px-5 py-8">
    <p class="cat-crumb"><a href="marketplace/" class="hover:underline">Marketplace</a></p>
    <h1 class="serif text-4xl mb-2" style="color:var(--forest);font-weight:400">Sell something</h1>
    <p class="text-gray-600">Free. About a minute. Buyers message you on WhatsApp. <a href="my-ads.html" class="underline font-semibold" style="color:var(--forest)">Your ads</a></p>
  </div>
</div>

<main class="max-w-2xl mx-auto px-5 py-6 pb-16">
  <form id="mkform" novalidate>
    <section class="bg-white rounded-2xl border p-5 mb-4" style="border-color:var(--line)">
      <h2 class="font-bold text-lg mb-3" style="color:var(--ink)">What are you selling?</h2>
      <div class="grid grid-cols-3 gap-2">__TILES__</div>
    </section>

    <div id="rest" hidden>
    <section class="bg-white rounded-2xl border p-5 mb-4" style="border-color:var(--line)">
      <h2 class="font-bold text-lg mb-1" style="color:var(--ink)">Photos</h2>
      <p class="text-sm mb-3" style="color:#5A625B">Up to six. The first is the cover. Ads with photos get far more messages.</p>
      <div id="thumbs" class="flex flex-wrap gap-2">
        <label id="addph" class="mk-add">__CAM__<span>Add photos</span>
          <input type="file" id="f-photo" accept="image/*" multiple class="sr-only"></label>
      </div>
      <p id="ph-note" class="text-xs mt-2" style="color:#6B7280"></p>
    </section>

    <section class="bg-white rounded-2xl border p-5 mb-4" style="border-color:var(--line)">
      <h2 class="font-bold text-lg mb-3" style="color:var(--ink)">Details</h2>
      <div data-show="property" class="flex gap-2 mb-4">
        <label class="flex-1"><input type="radio" name="deal" value="sale" checked class="sr-only"><span class="mk-tile" style="padding:.65rem">For sale</span></label>
        <label class="flex-1"><input type="radio" name="deal" value="rent" class="sr-only"><span class="mk-tile" style="padding:.65rem">For rent</span></label>
      </div>
      <label class="block mb-4"><span class="mk-lbl">Title</span>
        <input name="title" id="f-title" maxlength="90" class="mk-in" placeholder="iPhone 13, 128 GB, zwart">
        <span class="flex justify-between text-xs mt-1" style="color:#6B7280"><span>Say what it is, brand and size. That is what people search for.</span><span id="t-cnt">0/90</span></span></label>
      <div class="grid gap-3 mb-2" style="grid-template-columns:minmax(0,1fr) 6rem">
        <label><span class="mk-lbl">Price</span><input name="price" id="f-price" inputmode="numeric" class="mk-in" placeholder="0"></label>
        <label><span class="mk-lbl">Currency</span><select name="currency" class="mk-in">__CUR__</select></label>
      </div>
      <label data-show="rent" class="block mb-2"><span class="mk-lbl">Rent per</span><select name="period" class="mk-in">__PER__</select></label>
      <label data-show="item" class="inline-flex items-center gap-2 text-sm mb-4"><input type="checkbox" name="free" id="f-free" value="1" class="w-4 h-4"> Give it away for free</label>
      <div data-show="item" class="mb-4"><span class="mk-lbl">Condition</span><div class="flex gap-2 flex-wrap">__COND__</div></div>
      <div data-show="vehicles" class="grid gap-3 mb-4" style="grid-template-columns:repeat(auto-fit,minmax(120px,1fr))">
        <label><span class="mk-lbl">Make</span><input name="make" maxlength="40" class="mk-in" placeholder="Toyota"></label>
        <label><span class="mk-lbl">Model</span><input name="model" maxlength="40" class="mk-in" placeholder="Hilux"></label>
        <label><span class="mk-lbl">Year</span><input name="year" inputmode="numeric" class="mk-in" placeholder="2016"></label>
        <label><span class="mk-lbl">Km</span><input name="mileage" inputmode="numeric" class="mk-in" placeholder="85000"></label>
      </div>
      <div data-show="property" class="grid gap-3 mb-3" style="grid-template-columns:repeat(auto-fit,minmax(110px,1fr))">
        <label><span class="mk-lbl">Bedrooms</span><input name="beds" inputmode="numeric" class="mk-in"></label>
        <label><span class="mk-lbl">Bathrooms</span><input name="baths" inputmode="numeric" class="mk-in"></label>
        <label><span class="mk-lbl">Built m&#178;</span><input name="built_m2" inputmode="numeric" class="mk-in"></label>
        <label><span class="mk-lbl">Plot m&#178;</span><input name="plot_m2" inputmode="numeric" class="mk-in"></label>
      </div>
      <label data-show="property" class="inline-flex items-center gap-2 text-sm mb-4"><input type="checkbox" name="furnished" value="1" class="w-4 h-4"> Furnished</label>
      <label class="block"><span class="mk-lbl">Description</span>
        <textarea name="descr" id="f-descr" rows="5" maxlength="4000" class="mk-in" placeholder="Condition, what is included, why you are selling. Links and email addresses are removed, so put those in the contact fields."></textarea></label>
    </section>

    <section class="bg-white rounded-2xl border p-5 mb-4" style="border-color:var(--line)">
      <h2 class="font-bold text-lg mb-3" style="color:var(--ink)">Where</h2>
      <div class="grid gap-3" style="grid-template-columns:repeat(auto-fit,minmax(150px,1fr))">
        <label><span class="mk-lbl">District</span><select name="district" id="f-dist" class="mk-in"><option value="">Choose one</option>__DIST__</select></label>
        <label><span class="mk-lbl">Area <span class="normal-case font-normal">optional</span></span><input name="area" maxlength="60" class="mk-in" placeholder="Kwatta"></label>
      </div>
      <div data-show="property" class="mt-3">
        <label class="block mb-2"><span class="mk-lbl">Street and number <span class="normal-case font-normal">optional</span></span>
          <input name="address" maxlength="160" class="mk-in" placeholder="Kwattaweg 123"></label>
        <label class="flex items-start gap-2 text-sm"><input type="checkbox" name="hide_addr" value="1" class="mt-1">
          <span>Do not show the exact address. Buyers see only the area until you tell them.</span></label>
      </div>
    </section>

    <section class="bg-white rounded-2xl border p-5 mb-4" style="border-color:var(--line)">
      <h2 class="font-bold text-lg mb-1" style="color:var(--ink)">How buyers reach you</h2>
      <p class="text-sm mb-3" style="color:#5A625B">At least one. A Suriname mobile number gets a WhatsApp button. We remember these for your next ad, on this device.</p>
      <label class="block mb-3"><span class="mk-lbl">WhatsApp or phone</span>
        <input name="phone" id="f-phone" inputmode="tel" autocomplete="tel" class="mk-in" placeholder="8812345">
        <span id="wa-hint" class="block text-xs mt-1" style="color:#5A625B"></span></label>
      <label class="block mb-3"><span class="mk-lbl">Email</span>
        <input name="email" id="f-email" type="email" autocomplete="email" class="mk-in" placeholder="jij@voorbeeld.com"></label>
      <label class="block"><span class="mk-lbl">Link</span>
        <input name="link" id="f-link" class="mk-in" placeholder="facebook.com/jouwpagina"></label>
      __TS__
    </section>

    <div id="gate" hidden class="bg-white rounded-2xl border p-5 mb-4 text-center" style="border-color:var(--forest)">
      <h2 class="font-bold text-lg mb-1" style="color:var(--forest)">Last step: sign in</h2>
      <p class="text-sm text-gray-600 mb-4">So you can edit the price or mark it sold later. Your email is never shown on the ad. Your ad goes up as soon as you are in.</p>
      <div id="gsi" class="flex justify-center"></div>
    </div>

    <p id="formerr" hidden class="rounded-xl p-3 mb-4 text-sm font-semibold" style="background:#FDECEA;border:1px solid #F5C2BD;color:#B3261E"></p>
    <button type="submit" id="go" class="mk-btn mk-solid text-lg" style="padding:1rem">Place my ad</button>
    <p class="text-xs text-center mt-3" style="color:#656C63">Runs 30 days (property 60). Renew, change the price or mark it sold from <a href="my-ads.html" class="underline">your ads</a>.</p>
    </div>
  </form>

  <div id="done" hidden class="bg-white rounded-2xl border p-7 text-center" style="border-color:var(--line)">
    <h2 id="done-h" class="serif text-3xl mb-2" style="color:var(--forest);font-weight:400">Your ad is up</h2>
    <p id="done-p" class="text-gray-600 mb-4"></p>
    <p id="done-strip" hidden class="text-sm rounded-xl p-3 mb-4" style="background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12"></p>
    <div id="done-share" hidden class="mb-5">
      <p class="font-semibold mb-2" style="color:var(--ink)">Sell it faster: share it on your WhatsApp status or in a group</p>
      <a id="share-wa" target="_blank" rel="noopener" class="mk-btn mk-wa">__WA__Share on WhatsApp</a>
      <button type="button" id="share-copy" class="mk-btn mk-line">Copy the link</button>
    </div>
    <div class="flex gap-2 justify-center flex-wrap">
      <a id="done-view" href="marketplace/" class="px-5 py-2.5 rounded-full font-semibold border" style="border-color:var(--forest);color:var(--forest)">View your ad</a>
      <a href="post-ad.html" class="px-5 py-2.5 rounded-full font-semibold text-white" style="background:var(--forest)">Sell something else</a>
    </div>
  </div>

  <div class="mt-8">__SAFE__</div>
</main>
__FOOTER__
<script>
(function(){
__AUTH__
var $=function(i){return document.getElementById(i)};
var form=$("mkform"), files=[], pending=false;
var BASE=location.origin;

function cat(){ var r=form.querySelector('input[name="category"]:checked'); return r?r.value:""; }
function deal(){ var r=form.querySelector('input[name="deal"]:checked'); return r?r.value:"sale"; }
function layout(){
  var c=cat(), prop=c==="property", free=$("f-free").checked&&!prop;
  $("rest").hidden=!c;
  form.querySelectorAll("[data-show]").forEach(function(e){
    var w=e.getAttribute("data-show");
    e.hidden = w==="property" ? !prop : w==="item" ? prop : w==="vehicles" ? c!=="vehicles" : w==="rent" ? !(prop&&deal()==="rent") : false;
  });
  $("f-price").disabled=free; $("f-price").placeholder=free?"Free":"0";
  if(free) $("f-price").value="";
}
form.addEventListener("change",function(e){
  if(e.target.name==="category"&&!$("rest").dataset.seen){ $("rest").dataset.seen=1; layout(); $("rest").scrollIntoView({behavior:"smooth",block:"start"}); }
  layout(); save();
});

// draft autosave: a dropped connection on mobile data should not cost the typing
var DK="esr-mk-draft2";
function save(){ try{ var d={}; new FormData(form).forEach(function(v,k){ if(typeof v==="string"&&k!=="cf-turnstile-response") d[k]=v; }); localStorage.setItem(DK,JSON.stringify(d)); }catch(e){} }
function restore(){
  try{
    var d=JSON.parse(localStorage.getItem(DK)||"{}");
    var c=JSON.parse(localStorage.getItem("esr-mk-contact")||"{}");
    ["phone","email","link"].forEach(function(k){ if(!d[k]&&c[k]) d[k]=c[k]; });
    var q=new URLSearchParams(location.search).get("c"); if(q) d.category=q;
    Object.keys(d).forEach(function(k){
      var el=form.elements[k]; if(!el) return;
      if(el.length&&el[0]&&(el[0].type==="radio")){ [].forEach.call(el,function(r){r.checked=(r.value===d[k])}); }
      else if(el.type==="checkbox") el.checked=!!d[k];
      else el.value=d[k];
    });
  }catch(e){}
  layout(); waHint(); cnt();
}
form.addEventListener("input",function(){ save(); });

function cnt(){ $("t-cnt").textContent=($("f-title").value||"").length+"/90"; }
$("f-title").addEventListener("input",cnt);
function waHint(){
  var v=($("f-phone").value||"").replace(/[^0-9+]/g,"").replace(/^\+/,"").replace(/^00/,"");
  var mob=/^597[6-8][0-9]{6}$/.test(v)||/^[6-8][0-9]{6}$/.test(v);
  $("wa-hint").textContent = !v ? "" : (mob ? "Buyers get a WhatsApp button for this number." : "Not a Suriname mobile, so buyers see a normal call link.");
}
$("f-phone").addEventListener("input",waHint);

// photos: shrink on the phone (a 4 MB camera shot becomes ~300 KB), any format
// the browser can decode (iPhone HEIC included) comes out as JPEG
async function shrink(f){
  try{
    var bmp=await createImageBitmap(f);
    var M=1600, s=Math.min(1,M/Math.max(bmp.width,bmp.height));
    if(s===1&&f.size<900000&&/^image\/(jpeg|png|webp)$/.test(f.type)) return f;
    var c=document.createElement("canvas"); c.width=Math.round(bmp.width*s); c.height=Math.round(bmp.height*s);
    c.getContext("2d").drawImage(bmp,0,0,c.width,c.height);
    var b=await new Promise(function(r){c.toBlob(r,"image/jpeg",0.82)});
    return b?new File([b],"photo.jpg",{type:"image/jpeg"}):f;
  }catch(e){ return f; }
}
function drawThumbs(){
  var box=$("thumbs"); box.querySelectorAll(".mk-thumb").forEach(function(e){e.remove()});
  files.forEach(function(f,i){
    var d=document.createElement("div"); d.className="mk-thumb";
    d.innerHTML='<img alt="" src="'+URL.createObjectURL(f)+'">'
      +'<button type="button" class="x" data-rm="'+i+'" aria-label="Remove photo">&times;</button>'
      +(i===0?'<span class="cv">Cover</span>':'<button type="button" class="cv" style="background:rgba(0,0,0,.55)" data-cover="'+i+'">Make cover</button>');
    box.insertBefore(d,$("addph"));
  });
  $("addph").hidden=files.length>=6;
  $("ph-note").textContent=files.length?files.length+" of 6":"";
}
$("f-photo").addEventListener("change",async function(e){
  var list=[].slice.call(e.target.files); e.target.value="";
  $("ph-note").textContent="Preparing photos...";
  for(var i=0;i<list.length&&files.length<6;i++) files.push(await shrink(list[i]));
  drawThumbs();
});
$("thumbs").addEventListener("click",function(e){
  var rm=e.target.closest("[data-rm]"), cv=e.target.closest("[data-cover]");
  if(rm){ files.splice(Number(rm.dataset.rm),1); drawThumbs(); }
  if(cv){ var f=files.splice(Number(cv.dataset.cover),1)[0]; files.unshift(f); drawThumbs(); }
});

function err(msg,el){
  $("formerr").textContent=msg; $("formerr").hidden=false;
  if(el){ el.focus(); el.scrollIntoView({block:"center",behavior:"smooth"}); }
}
function check(){
  $("formerr").hidden=true;
  if(!cat()) return err("Choose what you are selling.");
  if(($("f-title").value||"").trim().length<6) return err("Give it a title of at least a few words.",$("f-title"));
  var prop=cat()==="property", free=$("f-free").checked&&!prop;
  if(!free&&!Number(($("f-price").value||"").replace(/[^\d]/g,""))) return err(prop?"Add a price.":"Add a price, or tick Give it away for free.",$("f-price"));
  if(!$("f-dist").value) return err("Choose a district.",$("f-dist"));
  if(!($("f-phone").value.trim()||$("f-email").value.trim()||$("f-link").value.trim())) return err("Add at least one way for buyers to reach you.",$("f-phone"));
  return true;
}
form.addEventListener("submit",function(e){
  e.preventDefault();
  if(check()!==true) return;
  if(!TOK){ pending=true; $("gate").hidden=false; mountSignIn($("gsi")); $("gate").scrollIntoView({block:"center",behavior:"smooth"}); return; }
  send();
});
function onSignedIn(){ $("gate").hidden=true; if(pending){ pending=false; send(); } }

async function send(){
  var btn=$("go"); btn.disabled=true; btn.textContent="Placing your ad...";
  var c=cat(), prop=c==="property";
  var fd=new FormData(form);
  // only send what applies to this category
  var drop=prop?["cond","free","make","model","year","mileage"]:["deal","period","beds","baths","built_m2","plot_m2","furnished","address","hide_addr"];
  if(c!=="vehicles") drop=drop.concat(["make","model","year","mileage"]);
  if(!prop||deal()!=="rent") drop.push("period");
  drop.forEach(function(k){fd.delete(k)});
  fd.delete("photo"); files.forEach(function(f){ fd.append("photo",f); });
  fd.append("section","__SECT__"); fd.append("idt",TOK);
  try{
    var r=await fetch(API+"/market/submit",{method:"POST",body:fd});
    var j=await r.json();
    if(r.status===401){ clearTok(); btn.disabled=false; btn.textContent="Place my ad"; pending=true; $("gate").hidden=false; mountSignIn($("gsi")); return; }
    if(!j.ok){
      err(j.err||"Something went wrong. Please try again.");
      btn.disabled=false; btn.textContent="Place my ad";
      if(window.turnstile) window.turnstile.reset();
      return;
    }
    try{
      localStorage.removeItem(DK);
      localStorage.setItem("esr-mk-contact",JSON.stringify({phone:$("f-phone").value,email:$("f-email").value,link:$("f-link").value}));
    }catch(e){}
    var url=BASE+"/marketplace/"+j.slug+"/";
    form.hidden=true; $("done").hidden=false;
    $("done-h").textContent=j.live?"Your ad is up":"Thanks, we are checking it";
    $("done-p").textContent=j.live
      ? "People can see it on the Marketplace right now."
      : "A new account's first ad gets a quick look by hand, usually within a day. After that everything you post goes up straight away.";
    if(j.live){
      $("done-share").hidden=false;
      var title=($("f-title").value||"").trim();
      $("share-wa").href="https://wa.me/?text="+encodeURIComponent("Te koop: "+title+"\n"+url);
      $("share-copy").onclick=function(){ try{navigator.clipboard.writeText(url); this.textContent="Link copied";}catch(e){} };
      $("done-view").href="marketplace/"+j.slug+"/";
    } else $("done-view").hidden=true;
    if(j.stripped&&j.stripped.length){
      $("done-strip").textContent="We took a link or email address out of your description: "+j.stripped.join(", ")+". Contact details belong in the contact fields so buyers can tap them.";
      $("done-strip").hidden=false;
    }
    window.scrollTo({top:0,behavior:"smooth"});
  }catch(e){
    err("No connection. Your draft is saved, try again in a moment.");
    btn.disabled=false; btn.textContent="Place my ad";
  }
}
restore();
})();
</script>
</body>
</html>
"""
    rep = {
        "__NAV__": ctx["nav_html"]("marketplace"), "__FOOTER__": ctx["footer_html"](),
        "__TILES__": tiles, "__DIST__": dist_opts, "__CUR__": cur_opts, "__PER__": per_opts,
        "__COND__": cond_chips, "__TS__": ts_box, "__SAFE__": _safety(),
        "__CAM__": _svg(ICON_CAM, "w-6 h-6"), "__WA__": WA_SVG,
        "__AUTH__": _auth_js(ctx), "__SECT__": SECTION,
    }
    for k, v in rep.items():
        body = body.replace(k, v)
    return head + body


# ── my ads ───────────────────────────────────────────────────────────────────

def _build_myads(ctx):
    head = _head(ctx, "Your ads", "Manage the ads you placed on the Explore Suriname Marketplace: "
                 "change the price, mark one sold, or renew it.", "my-ads.html", noindex=True,
                 extra=_gsi_head(ctx))
    body = r"""
<body class="bg-gray-50 overflow-x-hidden">
__NAV__
<div class="cat-hero">
  <div class="max-w-3xl mx-auto px-5 py-8">
    <p class="cat-crumb"><a href="marketplace/" class="hover:underline">Marketplace</a></p>
    <h1 class="serif text-4xl mb-2" style="color:var(--forest);font-weight:400">Your ads</h1>
    <p class="text-gray-600">Change a price, mark something sold, or renew an ad before it runs out.</p>
  </div>
</div>
<main class="max-w-3xl mx-auto px-5 py-6 pb-16">
  <div id="signin" class="bg-white rounded-2xl border p-7 text-center" style="border-color:var(--line)">
    <h2 class="serif text-2xl mb-2" style="color:var(--forest);font-weight:400">Sign in to see your ads</h2>
    <p class="text-gray-600 text-sm mb-5">Use the same Google account you placed them with.</p>
    <div id="gsi" class="flex justify-center"></div>
  </div>
  <div id="list"></div>
  <p class="text-center mt-8"><a href="post-ad.html" class="inline-block px-6 py-3 rounded-full font-bold text-white" style="background:var(--coral)">Sell something</a></p>
</main>
__FOOTER__
<script>
(function(){
__AUTH__
var $=function(i){return document.getElementById(i)};
var esc=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
var amt=function(n){return Number(n||0).toLocaleString("nl-NL",{maximumFractionDigits:0})};
var LABEL={pending:"Waiting for review",live:"Live",sold:"Sold",expired:"Expired",declined:"Not published",hidden:"Taken down"};
var COLOR={pending:"#7A5A12",live:"#1B4332",sold:"#3F3F3F",expired:"#3F3F3F",declined:"#B3261E",hidden:"#B3261E"};
function prop(a){return a.category==="property"||a.section==="realestate"}
function price(a){ if(!prop(a)&&!Number(a.price)) return "Free"; return a.currency+" "+amt(a.price)+(a.deal==="rent"?" per "+(a.period||"month"):""); }
function daysLeft(a){ if(a.status!=="live"||!a.expires) return null; return Math.ceil((a.expires-Date.now()/1000)/86400); }
function path(a){ return (a.section==="realestate"?"real-estate/":"marketplace/")+a.slug+"/"; }
function row(a){
  var d=daysLeft(a), warn="";
  if(d!==null&&d<=7) warn='<p class="text-sm mt-2 rounded-lg p-2" style="background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12">'
    +(d<=0?"This runs out today.":"Runs out in "+d+" day"+(d===1?"":"s")+".")+' Still available? Renew it so it keeps showing.</p>';
  var note=a.note?'<p class="text-sm mt-2 rounded-lg p-2" style="background:#FDECEA;border:1px solid #F5C2BD;color:#B3261E">'+esc(a.note)+'</p>':'';
  var img=(a.images&&a.images[0])||"", b='';
  if(a.status==="live"){
    b='<button data-a="sold" data-s="'+esc(a.slug)+'" class="mk-b">Mark as sold</button>'
     +'<button data-a="renew" data-s="'+esc(a.slug)+'" class="mk-b">Renew</button>'
     +'<button data-a="price" data-s="'+esc(a.slug)+'" class="mk-b">Change price</button>'
     +'<a class="mk-b" target="_blank" rel="noopener" href="https://wa.me/?text='+encodeURIComponent("Te koop: "+a.title+"\n"+location.origin+"/"+path(a))+'">Share on WhatsApp</a>'
     +(a.address&&prop(a)?'<button data-a="addr" data-s="'+esc(a.slug)+'" data-v="'+(a.show_addr?'0':'1')+'" class="mk-b">'+(a.show_addr?'Hide the address':'Show the address')+'</button>':'');
  } else if(a.status==="sold"||a.status==="expired"){
    b='<button data-a="relist" data-s="'+esc(a.slug)+'" class="mk-b">Put it back up</button>';
  }
  b+='<button data-a="del" data-s="'+esc(a.slug)+'" class="mk-b">Delete</button>';
  var link=(a.status==="live"||a.status==="sold")?'<a href="'+path(a)+'" class="text-sm underline" style="color:var(--forest2)">View the ad</a>':'';
  return '<div class="bg-white rounded-2xl border p-4 mb-3 flex gap-4" style="border-color:var(--line)">'
    +(img?'<img src="'+esc(img)+'" class="w-24 h-24 object-cover rounded-xl shrink-0" alt="">':'')
    +'<div class="flex-1 min-w-0">'
    +'<span class="inline-block px-2 py-0.5 rounded-full text-xs font-semibold text-white mb-1" style="background:'+(COLOR[a.status]||"#3F3F3F")+'">'+(LABEL[a.status]||a.status)+'</span>'
    +'<h3 class="font-semibold text-gray-900">'+esc(a.title)+'</h3>'
    +'<p class="font-bold" style="color:var(--forest)">'+esc(price(a))+'</p>'
    +link+warn+note+'<div class="flex flex-wrap gap-2 mt-3">'+b+'</div></div></div>';
}
async function load(){
  var r=await fetch(API+"/market/mine",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({idt:TOK})});
  if(r.status===401){ clearTok(); $("signin").hidden=false; $("list").innerHTML=""; mountSignIn($("gsi")); return; }
  var j=await r.json();
  if(!j.ads.length){ $("list").innerHTML='<div class="bg-white rounded-2xl border p-7 text-center" style="border-color:var(--line)"><p class="text-gray-600">You have not placed an ad yet.</p></div>'; return; }
  $("list").innerHTML=j.ads.map(row).join("");
  document.querySelectorAll(".mk-b").forEach(function(b){
    b.className="mk-b px-3 py-1.5 rounded-lg text-sm font-semibold border"; b.style.borderColor="#DDD4C1"; b.style.color="var(--ink)";
  });
}
function onSignedIn(){ $("signin").hidden=true; load(); }
async function act(slug,body){
  body.idt=TOK; body.slug=slug;
  var r=await fetch(API+"/market/update",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  var j=await r.json(); if(!j.ok) alert(j.err||"That did not work.");
  load();
}
document.addEventListener("click",function(e){
  var b=e.target.closest("button[data-a]"); if(!b) return;
  var s=b.dataset.s, a=b.dataset.a;
  if(a==="sold"){ if(confirm("Mark this as sold? It stops showing in the list.")) act(s,{act:"sold"}); }
  else if(a==="renew") act(s,{act:"renew"});
  else if(a==="relist") act(s,{act:"relist"});
  else if(a==="del"){ if(confirm("Delete this ad and its photos for good?")) act(s,{act:"delete"}); }
  else if(a==="price"){ var p=prompt("New price (numbers only, 0 for free):"); if(p===null) return; act(s,{act:"edit",price:p}); }
  else if(a==="addr") act(s,{act:"edit",show_addr:Number(b.dataset.v)});
});
if(TOK) onSignedIn(); else mountSignIn($("gsi"));
})();
</script>
</body>
</html>
"""
    rep = {"__NAV__": ctx["nav_html"]("marketplace"), "__FOOTER__": ctx["footer_html"](),
           "__AUTH__": _auth_js(ctx)}
    for k, v in rep.items():
        body = body.replace(k, v)
    return head + body


# ── not built yet: the 404 fallback ─────────────────────────────────────────
#
# An ad goes live in D1 the moment it is approved, and the browse grid re-reads
# the feed, so its card shows at once. Its own page only exists after the next
# build (~15 min). GitHub Pages answers that gap with 404.html, so generate.py
# injects these two strings into 404.html: if the missing path is an ad that is
# already live in the feed, show it with working contact buttons and reload by
# itself once the page exists. Plain strings: the JS braces stay single.

PENDING_AD_CSS = (
    "body.mk-p{display:block;background:#F4EEE2;color:#1F2A24;text-align:left}"
    ".mk-w{max-width:40rem;margin:0 auto;padding:1.5rem 1rem 3rem}"
    ".mk-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:1.25rem}"
    ".mk-top a{color:#1B4332;text-decoration:none;font-weight:700}"
    ".mk-c{background:#fff;border:1px solid #E7DFCF;border-radius:1rem;overflow:hidden}"
    ".mk-c img{width:100%;height:300px;object-fit:cover;display:block}"
    ".mk-b{padding:1.25rem}"
    ".mk-n{background:#FFF6E6;border:1px solid #E8CF9A;color:#7A5A12;border-radius:.75rem;padding:.8rem 1rem;font-size:.92rem;line-height:1.5;margin-bottom:1rem}"
    ".mk-pr{font-size:1.8rem;font-weight:800;color:#1F2A24;margin:.2rem 0}"
    ".mk-s{color:#5A625B;margin:.15rem 0}"
    ".mk-d{white-space:pre-wrap;color:#374151;line-height:1.6;margin-top:1rem}"
    ".mk-k{display:block;text-align:center;padding:.8rem;border-radius:.75rem;font-weight:700;text-decoration:none;margin-top:.5rem}"
    ".mk-wa{background:#25D366;color:#fff}.mk-ph{background:#1B4332;color:#fff}"
    ".mk-o{border:1px solid #1B4332;color:#1B4332}"
    ".mk-sf{font-size:.85rem;color:#656C63;margin-top:1rem;line-height:1.5}"
)

PENDING_AD_JS = r"""<script>
(function(){
  var m=location.pathname.match(/^\/(?:(nl|es)\/)?marketplace\/([a-z0-9-]{1,80})\/?(?:index\.html)?$/);
  if(!m) return;
  var slug=m[2];
  var more=document.querySelector(".w a.b.o");
  if(more){ more.href="/marketplace/"; more.textContent="Browse the Marketplace"; }
  var esc=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
  var amt=function(n){return Number(n||0).toLocaleString("nl-NL",{maximumFractionDigits:0})};
  var CAT=__CATS__;
  fetch("__API__/market/approved?s=market",{cache:"no-store"}).then(function(r){return r.json()}).then(function(j){
    var a=(Array.isArray(j)?j:[]).filter(function(x){return x.slug===slug})[0];
    if(!a||a.status!=="live") return;
    document.title=a.title+" | Explore Suriname";
    var prop=a.category==="property";
    var price=(!prop&&!Number(a.price))?"Free":a.currency+" "+amt(a.price)+(a.deal==="rent"?" per "+(a.period||"month"):"");
    var url=location.origin+"/marketplace/"+slug+"/";
    var k="", d=String(a.phone||"").replace(/\D/g,"");
    if(a.phone&&a.wa){
      var msg='Hi, I saw your ad "'+a.title+'" on Explore Suriname. Is it still available?\n'+url;
      k+='<a class="mk-k mk-wa" target="_blank" rel="noopener nofollow" href="https://wa.me/'+d+'?text='+encodeURIComponent(msg)+'">Message on WhatsApp</a>';
    } else if(a.phone){
      k+='<a class="mk-k mk-ph" href="tel:+'+d+'">Call '+esc(a.phone)+'</a>';
    }
    if(a.email) k+='<a class="mk-k mk-o" href="mailto:'+esc(a.email)+'?subject='+encodeURIComponent("About your ad: "+a.title)+'">Send an email</a>';
    if(a.link) k+='<a class="mk-k mk-o" target="_blank" rel="noopener nofollow" href="'+esc(a.link)+'">Open the seller&#8217;s page</a>';
    var img=(a.images&&a.images[0])||"";
    document.body.className="mk-p";
    document.body.innerHTML='<div class="mk-w">'
      +'<div class="mk-top"><a href="/">Explore Suriname</a><a href="/marketplace/">Marketplace</a></div>'
      +'<div class="mk-n" role="status"><b>Just published.</b> The full page for this ad is being built and goes live within about 15 minutes. This page switches over by itself.</div>'
      +'<div class="mk-c">'+(img?'<img src="'+esc(img)+'" alt="'+esc(a.title)+'">':'')
      +'<div class="mk-b"><p class="mk-pr">'+esc(price)+'</p>'
      +'<h1 translate="no" style="font-size:1.4rem;margin:0 0 .25rem;color:#1B4332">'+esc(a.title)+'</h1>'
      +'<p class="mk-s">'+esc(CAT[a.category]||"Other")+' &middot; '+esc(a.district)+(a.area?', '+esc(a.area):'')+'</p>'
      +(a.seller&&a.seller.name?'<p class="mk-s">Seller: <b>'+esc(a.seller.name)+'</b></p>':'')
      +(a.descr?'<p class="mk-d" translate="no">'+esc(a.descr)+'</p>':'')
      +k
      +'<p class="mk-sf"><b>Safe buying.</b> Meet somewhere busy, check it before you pay, and never send money in advance. Explore Suriname does not handle payments or vet sellers.</p>'
      +'</div></div></div>';
    var tries=0, t=setInterval(function(){
      if(++tries>53){ clearInterval(t); return; }
      fetch(location.pathname+"?cb="+Date.now(),{method:"HEAD",cache:"no-store"}).then(function(r){
        if(r.ok){ clearInterval(t); location.reload(); }
      }).catch(function(){});
    },45000);
  }).catch(function(){});
})();
</script>""".replace("__API__", MK_API).replace("__CATS__", json.dumps(CAT_LABEL))


# ── entry point ──────────────────────────────────────────────────────────────

def build_market_pages(ctx):
    """
    Return {filename: html}. Browse and ad pages use nested paths
    (marketplace/index.html, marketplace/<slug>/index.html); generate.py
    creates the directories.
    """
    table = _rate_table(ctx.get("cbvs_rates"))
    ads = ctx["_ads"] if "_ads" in ctx else _fetch(f"/market/approved?s={SECTION}")
    now = int(datetime.now(timezone.utc).timestamp())

    cutoff = now - DEAD_PAGE_DAYS * 86400
    ads = [a for a in ads
           if re.fullmatch(r"[a-z0-9-]{1,80}", a.get("slug", ""))      # never let a feed value shape a path
           and not (_is_dead(a) and (a.get("updated") or a.get("bumped") or 0) < cutoff)]
    ads.sort(key=_ts, reverse=True)
    pool = [a for a in ads if not _is_dead(a)]

    out = {
        f"{SECTION_PATH}/index.html": _build_browse(ctx, ads, table, now),
        "post-ad.html":               _build_post(ctx),
        "my-ads.html":                _build_myads(ctx),
    }
    for ad in ads:
        out[f'{SECTION_PATH}/{ad["slug"]}/index.html'] = _build_detail(ctx, ad, table, pool, now)

    print(f"  OK  marketplace: {len(pool)} live, {len(ads) - len(pool)} sold/expired kept for SEO")
    return out
