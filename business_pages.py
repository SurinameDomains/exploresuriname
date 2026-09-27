"""Business hub + tools for Surinamese businesses (added Sep 2026).

Called from generate.py exactly like oilgas_pages.py / market.py: it receives the
shared helpers through a ctx dict and returns {filename: html}. All pages are
root-level (xxx.html) so relative nav/footer links and build_i18n (NL/ES) work
unchanged.

Rules of the house (see business-hub-build-spec-sep2026.md in the project folder):
  * Every legal number comes from data/business_rules.json (effective-dated,
    sourced). Nothing legal is hard-coded here or in biz_engine.js.
  * All calculation lives in biz_engine.js (integer cents, unit-tested in
    tests/biz_engine.test.cjs, which runs in CI before this module).
  * All VISIBLE text is in the HTML (build_i18n.py skips <script>), so every
    sentence JS shows comes from the hidden #bzT dictionary on the page.
  * Live data (feeds, max prices) is read from data/*.json written by the
    separate biz_feeds.yml workflow; this module never touches the network.
  * Tailwind: this file is listed in tailwind.config.js 'content'.
"""
import datetime as _dt
import html as _html
import json as _json
from pathlib import Path as _Path

_ROOT = _Path(__file__).resolve().parent
_SR = _dt.timezone(_dt.timedelta(hours=-3))


def _load(name, default):
    try:
        return _json.loads((_ROOT / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def _esc(s):
    return _html.escape(str(s), quote=True)


# ─────────────────────────────────────────────────────────────────────────────
# Registry. key = nav/active key, used by generate.py for nav, search, sitemap.
# group: calc | people | docs | trade | office | live | guide
# ─────────────────────────────────────────────────────────────────────────────
BIZ_PAGES = [
    # file, key, title, short description, group, dutch search keywords
    ("business.html", "biz", "Business Tools for Suriname", "All free tools and guides for Surinamese businesses in one place.", "hub",
     "business ondernemer ondernemers bedrijf zakelijk tools rekenhulp mkb zzp"),
    ("btw-calculator.html", "biz-btw", "BTW Calculator Suriname", "Add or remove BTW at 10%, 5%, 25% or 0%, check whether you must register and estimate late-filing fines.", "calc",
     "btw berekenen btw calculator vat inclusief exclusief 10 procent omzetbelasting boete te laat"),
    ("salary-calculator.html", "biz-salary", "Salary Calculator Suriname (Gross to Net)", "Net pay, wage tax, AOV, pension, FVO and the employer's total cost, checked against official rules.", "people",
     "netto salaris berekenen bruto netto loonbelasting aov pensioen fvo werkgeverslasten loon calculator"),
    ("minimum-wage-suriname.html", "biz-minwage", "Minimum Wage & Overtime Pay Suriname", "The current minimum hourly wage, monthly equivalent and overtime pay at 150%, 200% and 300%.", "people",
     "minimumloon minimum uurloon suriname 2026 overwerk overuren 150 procent"),
    ("timesheet.html", "biz-timesheet", "Timesheet & Work Hours Calculator", "Add up work hours per week, flag the legal limits and calculate pay including overtime.", "people",
     "urenregistratie werkuren berekenen timesheet uren rooster overuren"),
    ("vacation-calculator.html", "biz-vacation", "Holiday Days & Holiday Allowance Calculator", "Statutory holiday days, the holiday allowance and the payout at termination under the Vakantiewet.", "people",
     "vakantiedagen berekenen vakantietoelage vakantiegeld vakantiewet uitbetalen"),
    ("payslip-generator.html", "biz-payslip", "Payslip Generator", "Make a clear payslip (loonstrook) as PDF for each employee, calculated with the official rules.", "people",
     "loonstrook maken salarisstrook payslip loonstrookje pdf"),
    ("income-tax-calculator.html", "biz-ib", "Income Tax Calculator for Self-Employed", "Estimate income tax and AOV on your yearly profit and how much to set aside each month.", "calc",
     "inkomstenbelasting berekenen zzp zelfstandige eenmanszaak aanslag voorlopige aangifte"),
    ("tax-deadlines.html", "biz-deadlines", "Tax Deadlines Calendar Suriname", "Every BTW, wage tax, AOV, APF and income tax deadline, with a calendar you can subscribe to.", "calc",
     "belasting deadlines termijnen aangifte btw loonbelasting wanneer betalen kalender"),
    ("working-days-calculator.html", "biz-workdays", "Working Days Calculator Suriname", "Count working days or add them to a date, skipping weekends and Surinamese public holidays.", "calc",
     "werkdagen berekenen werkdagen tellen betalingstermijn feestdagen"),
    ("pricing-calculator.html", "biz-pricing", "Price & Markup Calculator", "Turn a USD or EUR cost into an SRD shelf price with live bank rates, margin and BTW.", "trade",
     "verkoopprijs berekenen marge opslag winstmarge prijs calculator koers"),
    ("import-cost-calculator.html", "biz-import", "Import Cost Calculator Suriname", "Estimate import duty, statistics and consent fees and BTW, and the landed cost per unit.", "trade",
     "invoerrechten berekenen douane kosten import landed cost statistiekrecht consentrecht"),
    ("invoice-generator.html", "biz-invoice", "Invoice & Quote Generator (BTW-proof)", "Make invoices and quotes that contain every field the BTW law requires, as PDF, free.", "docs",
     "factuur maken offerte maken gratis factuur pdf btw factuur"),
    ("receipt-generator.html", "biz-receipt", "Receipt Maker (Kwitantie / Kassabon)", "Make a numbered receipt with the amount written in words, as PDF or for a receipt printer.", "docs",
     "kwitantie maken kassabon bon ontvangstbewijs"),
    ("payment-reminder.html", "biz-reminder", "Payment Reminder Generator", "Write a polite payment reminder and send it by WhatsApp or e-mail.", "docs",
     "betalingsherinnering herinnering factuur betalen aanmaning"),
    ("btw-register.html", "biz-register", "BTW Register & Cashbook", "Log sales and purchases and see your monthly BTW return figures.", "docs",
     "kasboek btw administratie aangifte omzet inkoop voorbelasting"),
    ("amount-in-words.html", "biz-words", "Amount in Words (Bedrag in Letters)", "Write any SRD amount out in Dutch or English words for receipts, cheques and contracts.", "docs",
     "bedrag in letters bedrag uitschrijven getal in woorden cheque"),
    ("cash-counter.html", "biz-cash", "Cash Counter & Cash-Up", "Count notes and coins, add dollars and euros, and compare with the expected amount.", "office",
     "kas tellen kasopmaak geld tellen biljetten munten dagafsluiting"),
    ("loan-calculator.html", "biz-loan", "Loan & Lease Calculator", "Monthly payment, total interest and a repayment table for a business loan or lease.", "trade",
     "lening berekenen maandlasten rente krediet lease aflossing"),
    ("break-even-calculator.html", "biz-breakeven", "Break-Even & CBM Calculator", "How many units you must sell to cover costs, and the volume of a shipment in CBM.", "trade",
     "break even berekenen kostprijs cbm kubieke meter volume"),
    ("qr-code-generator.html", "biz-qr", "QR Code Generator (Wi-Fi, Link, WhatsApp)", "Free QR codes for your website, Wi-Fi, WhatsApp, contact card or reviews. They never expire.", "office",
     "qr code maken qr code generator wifi qr whatsapp qr gratis"),
    ("barcode-generator.html", "biz-barcode", "Barcode & Price Label Maker", "Make EAN-13 or Code128 barcodes and print price labels on A4.", "office",
     "barcode maken streepjescode etiketten prijsetiket ean13"),
    ("pdf-tools.html", "biz-pdf", "PDF Tools: Merge, Split, Sign", "Merge, split, rotate, sign and stamp PDFs or turn photos into a PDF, all on your own device.", "office",
     "pdf samenvoegen pdf splitsen pdf ondertekenen foto naar pdf pdf draaien"),
    ("image-tools.html", "biz-image", "Image Resizer & Photo Tools", "Resize and compress photos, crop for social media and remove location data.", "office",
     "foto verkleinen afbeelding comprimeren foto bijsnijden locatie verwijderen"),
    ("business-card-maker.html", "biz-card", "Business Card & Email Signature Maker", "Print business cards with a QR code and make a professional e-mail signature.", "office",
     "visitekaartje maken email handtekening"),
    ("government-tenders.html", "biz-tenders", "Government Tenders & Announcements", "The latest government tenders and announcements, plus Belastingdienst notices, updated daily.", "live",
     "aanbestedingen overheid tenders bekendmakingen belastingdienst mededelingen"),
    ("max-prices-basic-goods.html", "biz-prices", "Maximum Prices of Basic Goods", "The official maximum consumer and wholesale prices of basic goods, searchable.", "live",
     "maximumprijzen basisgoederen prijzen ezoti richtprijzen publicatielijst"),
    ("start-business-suriname.html", "biz-g-start", "Starting a Business in Suriname", "The official steps to register a business: KKF, tax number, BTW, staff and licences.", "guide",
     "bedrijf starten suriname kkf inschrijven eenmanszaak nv oprichten fin nummer"),
    ("btw-guide-suriname.html", "biz-g-btw", "BTW in Suriname: A Plain Guide", "Rates, the registration threshold, invoices, deadlines and fines, with official sources.", "guide",
     "btw uitleg suriname btw regels btw registratie factuureisen"),
    ("hiring-staff-suriname.html", "biz-g-staff", "Hiring Staff in Suriname", "Wage tax, AOV, pension, FVO, minimum wage, hours and holidays for employers.", "guide",
     "personeel aannemen werkgever verplichtingen loonadministratie arbeidswet"),
    ("import-export-suriname.html", "biz-g-import", "Import & Export in Suriname", "How customs declarations work and what you pay, with official links.", "guide",
     "importeren suriname douane aangifte asycuda exporteren"),
    ("business-financing-suriname.html", "biz-g-finance", "Business Financing in Suriname", "Loans, guarantees and support programmes for Surinamese businesses.", "guide",
     "financiering lening ondernemer nob garantiefonds mkb krediet"),
    ("government-contacts-suriname.html", "biz-g-contacts", "Government Contacts for Businesses", "Addresses, phone numbers and opening hours of the Belastingdienst, customs, KKF and APF.", "guide",
     "belastingdienst adres openingstijden telefoon douane kkf contact"),
]
BIZ_KEYS = {p[1] for p in BIZ_PAGES}


def biz_url(fname):
    """Public URL path of a business page: no .html (GitHub Pages serves
    business.html at /business). Files on disk keep their .html name."""
    return fname[:-5] if fname.endswith(".html") else fname


BIZ_FILES = [p[0] for p in BIZ_PAGES]
# href="x.html", href='x.html', "/x.html", "../x.html" and SITE_URL/x.html -> clean;
# the lookbehind stops e.g. submit-business.html from matching business.html.
_CLEAN_RE = __import__("re").compile(r"(?<=[\"'/])(" + "|".join(__import__("re").escape(f[:-5]) for f in BIZ_FILES) + r")\.html(?=[\"'#?\s])")


def clean_links(html):
    return _CLEAN_RE.sub(r"\1", html)
BIZ_SEARCH = [{"n": p[2], "u": biz_url(p[0]), "c": "Guides", "a": "Suriname",
               "k": (p[2] + " " + p[3] + " " + p[5]).lower()} for p in BIZ_PAGES]
BIZ_SITEMAP = [(biz_url(p[0]), "0.8" if p[4] in ("hub", "calc", "people", "live") else "0.7",
                "daily" if p[4] in ("hub", "live") else "monthly") for p in BIZ_PAGES]


# ── Site nav (Business mega menu) ────────────────────────────────────────────
# Short labels for the nav only; page titles stay in BIZ_PAGES. A page without
# a label here falls back to its full title, so a new tool can never go missing
# from the menu. NAV_MOBILE = the short list shown in the mobile accordion.
NAV_LABELS = {
    "biz-btw": "BTW Calculator", "biz-salary": "Salary Calculator", "biz-minwage": "Minimum Wage",
    "biz-timesheet": "Timesheet", "biz-vacation": "Holiday Calculator", "biz-payslip": "Payslip Generator",
    "biz-ib": "Income Tax Calculator", "biz-deadlines": "Tax Deadlines", "biz-workdays": "Working Days",
    "biz-pricing": "Price & Markup", "biz-import": "Import Costs", "biz-invoice": "Invoice Maker",
    "biz-receipt": "Receipt Maker", "biz-reminder": "Payment Reminder", "biz-register": "BTW Register",
    "biz-words": "Amount in Words", "biz-cash": "Cash Counter", "biz-loan": "Loan Calculator",
    "biz-breakeven": "Break-Even", "biz-qr": "QR Code Generator", "biz-barcode": "Barcode Maker",
    "biz-pdf": "PDF Tools", "biz-image": "Image Tools", "biz-card": "Business Cards",
    "biz-tenders": "Government Tenders", "biz-prices": "Max Prices",
    "biz-g-start": "Start a Business", "biz-g-btw": "BTW Guide", "biz-g-staff": "Hiring Staff",
    "biz-g-import": "Import & Export", "biz-g-finance": "Business Financing",
    "biz-g-contacts": "Government Contacts",
}
NAV_MOBILE = ["biz-btw", "biz-salary", "biz-invoice", "biz-deadlines", "biz-tenders", "biz-qr", "biz-pdf"]


def nav_groups():
    """[(group label, [(url, label, key), ...]), ...] in hub order, hub page excluded.
    URLs are clean (no .html) and relative; the caller adds its prefix."""
    out = []
    for g, glabel in GROUPS:
        items = [(biz_url(p[0]), NAV_LABELS.get(p[1], p[2]), p[1]) for p in BIZ_PAGES if p[4] == g]
        if items:
            out.append((glabel, items))
    return out


def llms_section(site_url):
    lines = ["", "## Business tools (free, for Surinamese businesses)"]
    for f, _k, t, d, _g, _kw in BIZ_PAGES:
        lines.append(f"- [{t}]({site_url}/{biz_url(f)}): {d}")
    return "\n".join(lines) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# UI kit (shared CSS + JS). Namespaced .bz-* so nothing leaks into other pages.
# ─────────────────────────────────────────────────────────────────────────────
KIT_CSS = """
<style>
.bz-wrap{max-width:64rem;margin:0 auto;padding:2.2rem 1.1rem 5rem}
.bz-card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:1.35rem;margin-bottom:1.1rem}
.bz-card h2{font-family:'Newsreader',Georgia,serif;font-size:1.35rem;font-weight:700;color:var(--ink);margin:0 0 .8rem}
.bz-card h3{font-weight:700;color:var(--ink);margin:1rem 0 .4rem}
.bz-grid{display:grid;gap:1rem}
.bz-grid>*{min-width:0}
@media(min-width:760px){.bz-g2{grid-template-columns:1fr 1fr}.bz-g3{grid-template-columns:1fr 1fr 1fr}.bz-split{grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr);align-items:start}}
.bz-label{display:block;font-size:.72rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 .35rem}
.bz-in,.bz-sel,.bz-ta{width:100%;border:1.5px solid #E2D8C2;border-radius:12px;padding:.7rem .85rem;font-size:1.05rem;background:#fff;color:var(--ink);font-family:inherit}
.bz-in.bz-xl{font-size:1.6rem;font-weight:700;padding:.75rem 1rem}
.bz-in:focus,.bz-sel:focus,.bz-ta:focus{outline:none;border-color:var(--forest2);box-shadow:0 0 0 3px rgba(45,106,79,.16)}
.bz-in[aria-invalid=true]{border-color:#C2410C;background:#FFF7ED}
.bz-pre{display:flex;align-items:stretch}
.bz-pre>span{display:flex;align-items:center;padding:0 .8rem;border:1.5px solid #E2D8C2;border-right:0;border-radius:12px 0 0 12px;background:var(--paper-2);font-weight:700;color:var(--ink-soft);font-size:.9rem}
.bz-pre>.bz-in{border-radius:0 12px 12px 0}
.bz-hint{font-size:.8rem;color:var(--ink-soft);margin-top:.3rem}
.bz-seg{display:inline-flex;flex-wrap:wrap;border:1.5px solid #E2D8C2;border-radius:12px;overflow:hidden;background:#fff}
.bz-seg button{padding:.55rem .95rem;font-weight:600;font-size:.92rem;color:var(--ink-soft);border-right:1px solid #E2D8C2;background:#fff;cursor:pointer}
.bz-seg button:last-child{border-right:0}
.bz-seg button[aria-pressed=true]{background:var(--forest);color:#fff}
.bz-chips{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.55rem}
.bz-chip{border:1px solid #E2D8C2;background:#fff;border-radius:999px;padding:.3rem .8rem;font-size:.85rem;font-weight:600;color:var(--forest2);cursor:pointer}
.bz-chip:hover{border-color:var(--forest2)}
.bz-res{background:var(--forest);color:#fff;border-radius:18px;padding:1.3rem 1.35rem;margin-bottom:1.1rem}
.bz-res .bz-k{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--gold)}
.bz-res .bz-big{font-size:2.3rem;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums;margin:.2rem 0 .35rem;word-break:break-word}
.bz-res .bz-say{color:rgba(255,255,255,.85);font-size:.98rem;line-height:1.5}
.bz-tbl{width:100%;border-collapse:collapse;font-size:.95rem}
.bz-tbl td,.bz-tbl th{padding:.55rem .3rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
.bz-tbl td:not(.n),.bz-tbl th:not(.n){overflow-wrap:anywhere;hyphens:auto;-webkit-hyphens:auto}
.bz-card p,.bz-card li{overflow-wrap:break-word;hyphens:auto;-webkit-hyphens:auto}
.bz-tbl th{font-size:.72rem;letter-spacing:.07em;text-transform:uppercase;color:var(--ink-soft)}
.bz-tbl td.n,.bz-tbl th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.bz-tbl tr.bz-tot td{font-weight:700;border-top:2px solid var(--ink);border-bottom:0}
.bz-tbl tr.bz-sub td{color:var(--ink-soft);font-size:.85rem}
.bz-btn{display:inline-flex;align-items:center;gap:.4rem;background:var(--forest);color:#fff;border-radius:999px;padding:.6rem 1.15rem;font-weight:700;font-size:.92rem;cursor:pointer;border:0}
.bz-btn:hover{background:var(--forest2)}
.bz-btn2{display:inline-flex;align-items:center;gap:.4rem;background:#fff;color:var(--forest);border:1.5px solid var(--forest2);border-radius:999px;padding:.52rem 1.05rem;font-weight:700;font-size:.9rem;cursor:pointer}
.bz-btn2:hover{background:var(--mint)}
.bz-btn:disabled,.bz-btn2:disabled{opacity:.45;cursor:not-allowed}
.bz-acts{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.9rem}
.bz-note{background:#FEF6E7;border:1px solid #F3D9A4;color:#6B4A12;border-radius:12px;padding:.7rem .9rem;font-size:.88rem;line-height:1.5;margin:.6rem 0}
.bz-ok{background:var(--mint);border:1px solid #BFDDB8;color:var(--forest);border-radius:12px;padding:.7rem .9rem;font-size:.88rem;line-height:1.5;margin:.6rem 0}
.bz-warn{background:#FDECEA;border:1px solid #F5C2B8;color:#8A2A12;border-radius:12px;padding:.7rem .9rem;font-size:.88rem;line-height:1.5;margin:.6rem 0}
.bz-src{font-size:.8rem;color:var(--ink-soft);line-height:1.55}
.bz-src a{color:var(--forest2);text-decoration:underline}
.bz-src .bz-stale{color:#B45309;font-weight:700}
.bz-how summary{cursor:pointer;font-weight:700;color:var(--forest2);padding:.4rem 0}
.bz-more summary{cursor:pointer;font-weight:700;color:var(--forest2);padding:.3rem 0;margin-top:.4rem}
.bz-tip{display:inline-flex;align-items:center;justify-content:center;width:1.1rem;height:1.1rem;border-radius:999px;background:var(--paper-2);color:var(--forest2);font-size:.7rem;font-weight:800;margin-left:.3rem;cursor:help;vertical-align:middle}
.bz-tools{display:grid;gap:.75rem}
@media(min-width:640px){.bz-tools{grid-template-columns:1fr 1fr}}
@media(min-width:980px){.bz-tools{grid-template-columns:1fr 1fr 1fr}}
.bz-tool{display:block;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:1rem 1.1rem;transition:border-color .15s,transform .15s}
.bz-tool:hover{border-color:var(--forest2);transform:translateY(-1px)}
.bz-tool b{display:block;color:var(--ink);font-size:1rem;margin-bottom:.2rem}
.bz-tool span{display:block;color:var(--ink-soft);font-size:.86rem;line-height:1.45}
.bz-sec{font-family:'Newsreader',Georgia,serif;font-size:1.5rem;font-weight:700;color:var(--ink);margin:2rem 0 .8rem}
.bz-feed li{padding:.55rem 0;border-bottom:1px solid var(--line);list-style:none}
.bz-feed a{color:var(--ink);font-weight:600}
.bz-feed a:hover{color:var(--forest2);text-decoration:underline}
.bz-feed small{display:block;color:var(--ink-soft);font-size:.78rem}
.bz-tag{display:inline-block;font-size:.68rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;background:var(--mint);color:var(--forest);border-radius:6px;padding:.1rem .4rem;margin-right:.35rem;vertical-align:middle}
.bz-priv{display:flex;gap:.5rem;align-items:center;font-size:.85rem;color:var(--forest);background:var(--mint);border-radius:12px;padding:.55rem .8rem;margin-bottom:1rem}
.bz-num{font-variant-numeric:tabular-nums}
.bz-drop{border:2px dashed #CDBF9F;border-radius:16px;padding:1.6rem;text-align:center;background:#fff;cursor:pointer}
.bz-drop.bz-hot{border-color:var(--forest2);background:var(--mint)}
.bz-row{display:grid;gap:.6rem;align-items:end}
.bz-x{background:none;border:0;color:#B45309;font-weight:800;font-size:1.2rem;cursor:pointer;padding:.3rem .5rem}
.bz-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
.bz-acts>a:not(.bz-btn):not(.bz-btn2){display:inline-flex;align-items:center;gap:.35rem;background:#fff;color:var(--forest);border:1.5px solid var(--forest2);border-radius:999px;padding:.52rem 1.05rem;font-weight:700;font-size:.9rem;text-decoration:none}
.bz-acts>a[target=_blank]:not(.bz-btn):not(.bz-btn2)::after{content:"\2197";font-weight:400}
.bz-toast{position:fixed;left:50%;bottom:1.2rem;transform:translateX(-50%);background:var(--ink);color:#fff;padding:.6rem 1rem;border-radius:999px;font-size:.9rem;z-index:80;opacity:0;transition:opacity .2s;pointer-events:none}
.bz-toast.on{opacity:1}
@media print{nav,footer,.util-rail,.pg-hero,.bz-noprint,#srch-modal{display:none!important}.bz-wrap{padding:0}.bz-card,.bz-res{border:0;box-shadow:none}.bz-res{background:#fff;color:#000}.bz-res .bz-say,.bz-res .bz-k{color:#000}}
</style>
"""

# JS kit: small helpers every tool uses. Plain ES5 so old Android browsers work.
KIT_JS = r"""
<script>
(function(){
  var E = window.BizEngine;
  var L = (document.documentElement.lang || 'en').slice(0,2);
  var R = JSON.parse(document.getElementById('bzR').textContent);
  var H = JSON.parse(document.getElementById('bzH').textContent);
  function $(id){ return document.getElementById(id); }
  function T(k, v){
    var e = document.querySelector('#bzT [data-k="'+k+'"]');
    var s = e ? e.textContent : k;
    if (v) for (var x in v) s = s.split('{'+x+'}').join(v[x]);
    return s;
  }
  function money(c){ return E.fmt(c, L); }
  function fmtIn(c){ return new Intl.NumberFormat(L==='en'?'en-US':'nl-NL', {minimumFractionDigits: c%100?2:0, maximumFractionDigits:2}).format(c/100); }
  function srd(c){ return 'SRD ' + E.fmt(c, L); }
  function amt(id){ var el = $(id); if(!el) return null; var v = el.value.trim(); if(v===''){ el.removeAttribute('aria-invalid'); return null; }
    var c = E.parseAmount(v, L); if(c===null){ el.setAttribute('aria-invalid','true'); } else el.removeAttribute('aria-invalid'); return c; }
  function num(id){ var el = $(id); if(!el) return null; var v = el.value.trim(); if(v===''){ el.removeAttribute('aria-invalid'); return null; }
    var n = E.parseNum(v, L); if(n===null){ el.setAttribute('aria-invalid','true'); } else el.removeAttribute('aria-invalid'); return n; }
  function today(){ var d = new Date(Date.now() - 3*3600*1000); return d.toISOString().slice(0,10); } // Suriname date (UTC-3)
  function fmtDate(iso){ if(!iso) return ''; var p = iso.split('-'); var d = new Date(Date.UTC(+p[0], +p[1]-1, +p[2]));
    return d.toLocaleDateString(L==='en'?'en-GB':(L==='es'?'es-ES':'nl-NL'), {weekday:'short', day:'numeric', month:'long', year:'numeric', timeZone:'UTC'}); }
  function fmtDay(iso){ if(!iso) return ''; var p = iso.split('-'); var d = new Date(Date.UTC(+p[0], +p[1]-1, +p[2]));
    return d.toLocaleDateString(L==='en'?'en-GB':(L==='es'?'es-ES':'nl-NL'), {day:'numeric', month:'long', year:'numeric', timeZone:'UTC'}); }
  function seg(id, cb){ var box = $(id); if(!box) return; box.addEventListener('click', function(ev){ var b = ev.target.closest('button[data-v]'); if(!b) return;
      [].forEach.call(box.querySelectorAll('button'), function(x){ x.setAttribute('aria-pressed', x===b?'true':'false'); }); if(cb) cb(b.getAttribute('data-v')); }); }
  function segVal(id){ var b = document.querySelector('#'+id+' button[aria-pressed=true]'); return b ? b.getAttribute('data-v') : null; }
  function segSet(id, v){ [].forEach.call(document.querySelectorAll('#'+id+' button'), function(x){ x.setAttribute('aria-pressed', x.getAttribute('data-v')===v?'true':'false'); }); }
  function toast(msg){ var t = $('bzToast'); if(!t){ t = document.createElement('div'); t.id='bzToast'; t.className='bz-toast'; document.body.appendChild(t); }
    t.textContent = msg; t.classList.add('on'); clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('on'); }, 2200); }
  function copy(text){ if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(function(){ toast(T('copied')); }, function(){ fallback(); }); } else fallback();
    function fallback(){ var ta=document.createElement('textarea'); ta.value=text; document.body.appendChild(ta); ta.select(); try{ document.execCommand('copy'); toast(T('copied')); }catch(e){} document.body.removeChild(ta); } }
  function wa(text){ window.open('https://wa.me/?text=' + encodeURIComponent(text), '_blank', 'noopener'); }
  // shareable state: ?a=1&b=2 (only the listed input ids)
  // Only put inputs in the address bar after the visitor changed something, so a
  // freshly opened tool keeps its clean URL (/btw-calculator, not ?amt=...).
  var touched = false; ['input','change','click'].forEach(function(ev){ document.addEventListener(ev, function(e){ if(e.isTrusted && e.target && e.target.closest && e.target.closest('main')) touched = true; }, true); });
  function saveUrl(ids){ if(!touched) return; try{ var q = new URLSearchParams(); ids.forEach(function(id){ var el=$(id); if(!el) return;
      var v = el.type==='checkbox' ? (el.checked?'1':'') : (el.getAttribute('role')==='group' ? segVal(id) : el.value); if(v) q.set(id, v); });
      var s = q.toString(); history.replaceState(null, '', location.pathname + (s ? '?' + s : '')); }catch(e){} }
  function loadUrl(ids){ try{ var q = new URLSearchParams(location.search); ids.forEach(function(id){ if(!q.has(id)) return; var el=$(id); if(!el) return;
      if(el.type==='checkbox') el.checked = q.get(id)==='1'; else if(el.getAttribute('role')==='group') segSet(id, q.get(id)); else el.value = q.get(id); }); return q.toString() !== ''; }catch(e){ return false; } }
  function store(k, v){ try{ if(v===undefined){ var s = localStorage.getItem('bz.'+k); return s ? JSON.parse(s) : null; } localStorage.setItem('bz.'+k, JSON.stringify(v)); return true; }catch(e){ return null; } }
  function download(name, blob){ var a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name; document.body.appendChild(a); a.click(); setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 1500); }
  function loadScript(src){ return new Promise(function(res, rej){ if(document.querySelector('script[src="'+src+'"]')) return res(); var s=document.createElement('script'); s.src=src; s.onload=res; s.onerror=function(){ rej(new Error('load '+src)); }; document.head.appendChild(s); }); }
  function on(ids, ev, fn){ ids.forEach(function(id){ var el=$(id); if(el) el.addEventListener(ev, fn); }); }
  function esc(s){ return String(s===null||s===undefined?'':s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); }
  function rows(list){ return list.map(function(r){ return '<tr'+(r[2]?' class="'+r[2]+'"':'')+'><td>'+esc(r[0])+'</td><td class="n">'+r[1]+'</td></tr>'; }).join(''); }
  // Show default values in the reader's number format (1.000,50 in NL/ES, 1,000.50 in EN).
  // Runs before the page script, so values from a shared link (loadUrl) still win.
  [].forEach.call(document.querySelectorAll('input.bz-num[value]'), function(el){
    var v = el.value.trim(); if(!v) return;
    if(el.getAttribute('data-kind')==='m'){ var c = E.parseAmount(v); if(c===null) return;
      el.value = new Intl.NumberFormat(L==='en'?'en-US':'nl-NL', {minimumFractionDigits: c%100?2:0, maximumFractionDigits:2}).format(c/100); }
    else { var n = E.parseNum(v); if(n===null) return; el.value = new Intl.NumberFormat(L==='en'?'en-US':'nl-NL', {useGrouping:false, maximumFractionDigits:4}).format(n); }
  });
  // share/print buttons present on most tools
  document.addEventListener('click', function(ev){
    var b = ev.target.closest('[data-bz]'); if(!b) return;
    var a = b.getAttribute('data-bz');
    if(a==='link') copy(location.href);
    else if(a==='print') window.print();
    else if(a==='wa' && window.BZ && BZ.shareText) wa(BZ.shareText() + '\n' + location.href);
    else if(a==='copy' && window.BZ && BZ.shareText) copy(BZ.shareText());
  });
  window.BZ = {E:E, L:L, R:R, H:H, $:$, T:T, money:money, fmtIn:fmtIn, srd:srd, amt:amt, num:num, today:today, fmtDate:fmtDate, fmtDay:fmtDay, seg:seg, segVal:segVal, segSet:segSet,
    toast:toast, copy:copy, wa:wa, saveUrl:saveUrl, loadUrl:loadUrl, store:store, download:download, loadScript:loadScript, on:on, esc:esc, rows:rows, shareText:null};
})();
</script>
"""

# Strings the kit itself needs (plus each page adds its own).
KIT_T = {"copied": "Copied", "err_input": "Please check the highlighted field.",
         "srd": "SRD", "print": "Print"}


def _t_block(strings):
    items = "".join(f'<span data-k="{_esc(k)}">{_esc(v)}</span>' for k, v in strings.items())
    return f'<div id="bzT" hidden>{items}</div>'


def _field(fid, label, value="", hint="", prefix="SRD", big=False, mode="decimal", tip="", money=None):
    tipx = f'<span class="bz-tip" title="{_esc(tip)}">i</span>' if tip else ""
    cls = "bz-in bz-xl" if big else "bz-in"
    kind = "m" if (money if money is not None else prefix in ("SRD", "USD", "EUR")) else "n"
    inp = (f'<input id="{fid}" class="{cls} bz-num" inputmode="{mode}" autocomplete="off" data-kind="{kind}" '
           f'value="{_esc(value)}" aria-describedby="{fid}-h">')
    if prefix:
        inp = f'<div class="bz-pre"><span>{prefix}</span>{inp}</div>'
    h = f'<div class="bz-hint" id="{fid}-h">{hint}</div>' if hint else f'<span id="{fid}-h" hidden></span>'
    return f'<div><label class="bz-label" for="{fid}">{label}{tipx}</label>{inp}{h}</div>'


def _text(fid, label, value="", hint="", mode="text", ta=False):
    if ta:
        inp = f'<textarea id="{fid}" class="bz-ta" rows="3">{_esc(value)}</textarea>'
    else:
        inp = f'<input id="{fid}" class="bz-in" inputmode="{mode}" autocomplete="off" value="{_esc(value)}">'
    h = f'<div class="bz-hint">{hint}</div>' if hint else ""
    return f'<div><label class="bz-label" for="{fid}">{label}</label>{inp}{h}</div>'


def _select(fid, label, options, selected=None, hint=""):
    opts = "".join(f'<option value="{_esc(v)}"{" selected" if str(v) == str(selected) else ""}>{t}</option>'
                   for v, t in options)
    h = f'<div class="bz-hint">{hint}</div>' if hint else ""
    return f'<div><label class="bz-label" for="{fid}">{label}</label><select id="{fid}" class="bz-sel">{opts}</select>{h}</div>'


def _seg(fid, options, selected, label=""):
    btns = "".join(f'<button type="button" data-v="{_esc(v)}" aria-pressed="{"true" if v == selected else "false"}">{t}</button>'
                   for v, t in options)
    lab = f'<span class="bz-label">{label}</span>' if label else ""
    return f'<div>{lab}<div id="{fid}" class="bz-seg" role="group">{btns}</div></div>'


def _check(fid, label, checked=False):
    return (f'<label class="flex items-start gap-2 text-sm" style="margin:.35rem 0;cursor:pointer">'
            f'<input type="checkbox" id="{fid}"{" checked" if checked else ""} style="margin-top:.2rem;width:1.05rem;height:1.05rem">'
            f'<span>{label}</span></label>')


def _share_bar(extra=""):
    return ('<div class="bz-acts bz-noprint">'
            '<button type="button" class="bz-btn2" data-bz="wa">WhatsApp</button>'
            '<button type="button" class="bz-btn2" data-bz="copy">Copy result</button>'
            '<button type="button" class="bz-btn2" data-bz="link">Copy link</button>'
            '<button type="button" class="bz-btn2" data-bz="print">Print</button>'
            + extra + '</div>')


def _privacy():
    return ('<div class="bz-priv"><span aria-hidden="true">&#128274;</span>'
            '<span>Your files never leave your device. Everything runs in your own browser.</span></div>')


# ─────────────────────────────────────────────────────────────────────────────
# Page assembly
# ─────────────────────────────────────────────────────────────────────────────
def _rules_public(R):
    return {k: v for k, v in R.items() if not k.startswith("_")}


def _holidays_table():
    H = {"dates": {}, "names": {}, "complete": {}, "incomplete": {}}
    base = _load("data/holidays.json", {"year": 0, "public": []})
    if base.get("year"):
        H["complete"][str(base["year"])] = True
    for h in base.get("public", []):
        H["dates"][h["date"]] = 1
        H["names"][h["date"]] = h.get("name_nl", "")
    extra = _load("data/biz_holidays_extra.json", {"years": {}})
    for y, v in extra.get("years", {}).items():
        if y in H["complete"]:
            continue
        if v.get("incomplete"):
            H["incomplete"][y] = v.get("missing_note", "")
        else:
            H["complete"][y] = True
        for h in v.get("public", []):
            H["dates"][h["date"]] = 1
            H["names"][h["date"]] = h.get("name_nl", "")
    return H


def _sources_html(R, keys, today):
    """Source list for the rules a tool uses; amber when not re-verified for 180 days."""
    items = []
    seen = set()
    for k in keys:
        v = R.get(k)
        if isinstance(v, list) and v and isinstance(v[-1], dict):
            e = v[-1]
        elif isinstance(v, dict):
            e = v
        else:
            continue
        src, url, ver = e.get("source", ""), e.get("url", ""), e.get("verified", "")
        if not src or (src, url) in seen:
            continue
        seen.add((src, url))
        stale = False
        try:
            stale = (today - _dt.date.fromisoformat(ver)).days > 180
        except Exception:
            pass
        verx = (f'<span class="{"bz-stale" if stale else ""}">{_esc(ver)}</span>' if ver else "")
        link = f' <a href="{_esc(url)}" target="_blank" rel="noopener">&#8599;</a>' if url else ""
        items.append(f'<li><span translate="no">{_esc(src)}</span>{link} &middot; <span>checked</span> {verx}</li>')
    if not items:
        return ""
    return ('<div class="bz-card bz-src"><h2 style="font-size:1.05rem">Sources</h2>'
            '<ul style="padding-left:1rem;list-style:disc">' + "".join(items) + '</ul>'
            '<p style="margin-top:.6rem">These tools follow the official rules as published. They are a guide, not tax or legal advice. '
            'Rules are checked daily against the official sources; when a rule changes we update it after verifying the official text.</p></div>')


def _related(keys):
    idx = {p[1]: p for p in BIZ_PAGES}
    cards = []
    for k in keys:
        p = idx.get(k)
        if p:
            cards.append(f'<a class="bz-tool" href="{p[0]}"><b>{p[2]}</b><span>{p[3]}</span></a>')
    cards.append('<a class="bz-tool" href="business.html"><b>All business tools</b><span>Every free tool and guide for Surinamese businesses.</span></a>')
    return '<h2 class="bz-sec">Related tools</h2><div class="bz-tools">' + "".join(cards) + '</div>'


# ─────────────────────────────────────────────────────────────────────────────
# Rule values inside fixed text. Labels, hints and FAQ answers write ⟦TOKEN⟧
# instead of a number; _Ctx.page() fills every token from the CURRENT rules, so
# a rule change can never leave an old number in a sentence. A token that is
# not filled is reported as an ERROR by the build.
# ─────────────────────────────────────────────────────────────────────────────
def _last(R, k):
    v = R[k]
    return v[-1] if isinstance(v, list) else v


def _tsrd(n):
    n = float(n)
    return f"SRD {n:,.0f}" if n == int(n) else f"SRD {n:,.2f}"


def _tpct(x):
    return f"{float(x):g}%"


def _rule_tokens(R, today):
    b, pen, aov, fvo = _last(R, "btw"), _last(R, "btw_penalties"), _last(R, "aov"), _last(R, "fvo")
    wt, tf, apc, vac = _last(R, "wage_tax"), _last(R, "tax_free"), R["apf_common"], _last(R, "vacation")
    ib = _last(R, "income_tax")
    mw = [e for e in R["minimum_wage_hourly"] if e["from"] <= today.isoformat()][-1]
    fl = [_tsrd(v) for v in pen["late_filing_by_month"]]
    # wage tax bands (per month)
    widths = [w for w, _p in wt["bands_month"] if w]
    pcts = [_tpct(p) for _w, p in wt["bands_month"]]
    if widths and len(set(widths)) == 1:
        lb = f"{', '.join(pcts[:-2])} and {pcts[-2]} apply to {len(widths)} bands of {_tsrd(widths[0])} and {pcts[-1]} to the rest"
    else:
        lb = ", ".join(f"{p} on the next {_tsrd(w)}" for w, p in zip(widths, pcts)) + f" and {pcts[-1]} on the rest"
    # income tax bands (per year), cumulative
    free = ib["bands_year"][0][0] if ib["bands_year"][0][1] == 0 else 0
    parts, top = [], free
    for w, p in ib["bands_year"][1:]:
        if w:
            top += w
            parts.append(f"{_tpct(p)} up to {_tsrd(top)}")
        else:
            parts.append(f"{_tpct(p)} above")
    ibt = (f"The first {_tsrd(free)} a year is tax-free. Then " if free else "") + ", ".join(parts[:-1]) + " and " + parts[-1]
    return {
        "BTW_THR": _tsrd(b["threshold_year"]),
        "PEN_PAY": f"{_tpct(pen['late_payment_pct'])}, max {_tsrd(pen['late_payment_max'])}",
        "PEN_PAY_PCT": _tpct(pen["late_payment_pct"]), "PEN_PAY_MAX": _tsrd(pen["late_payment_max"]),
        "PEN_LIST": ", ".join(fl[:-1]) + " or " + fl[-1], "PEN_FROM": pen["from"][:4],
        "PEN_SRC": pen.get("source", "").split("(")[0].strip(),
        "AOV": _tpct(aov["pct"]), "AOV_AGE": str(aov["max_age"]),
        "FVO_EE": _tpct(fvo["employee_max_pct"]), "FVO_ER": _tpct(fvo["pct_total"] - fvo["employee_max_pct"]),
        "FORF": _tpct(wt["forfait_pct"]), "FORF_MAX": _tsrd(wt["forfait_max_month"]),
        "FORF_CAP": _tsrd(wt["forfait_max_month"] * 100 / wt["forfait_pct"]),
        "LB_FREE": _tsrd(wt["tax_free_month"]), "LB_BANDS": lb,
        "APF_MIN": _tsrd(apc["base_min_month"]), "APF_MAX": _tsrd(apc["base_max_month"]),
        "CHILD": _tsrd(tf["child_allowance_per_child_month"]), "CHILD_MAX": _tsrd(tf["child_allowance_max_month"]),
        "HOL_MAX": _tsrd(tf["holiday_allowance_max_year"]), "HOL_FROM": tf["from"][:4],
        "IB_TEXT": ibt,
        "VAC_FIRST": str(vac["first_year_days"]), "VAC_STEP": str(vac["increase_per_year"]), "VAC_MAX": str(vac["max_days"]),
        "MW_MONTH": _tsrd(round(mw["value"] * 40 * 52 / 12)), "MW_SRC": mw.get("source", ""),
    }


def _fill_tokens(html, tokens, where=""):
    import re as _re
    out = _re.sub("⟦([A-Z_]+)⟧", lambda m: tokens.get(m.group(1), m.group(0)), html)
    left = sorted(set(_re.findall("⟦([A-Z_]+)⟧", out)))
    if left:
        raise ValueError(f"unfilled rule tokens in {where}: {left}")
    return out


class _Ctx:
    def __init__(self, ctx):
        self.c = ctx
        self.R = _load("data/business_rules.json", {})
        self.H = _holidays_table()
        self.engine = (_ROOT / "biz_engine.js").read_text(encoding="utf-8")
        self.today = _dt.datetime.now(_SR).date()

    def page(self, fname, key, kicker, h1, sub, body, js="", strings=None, faq=None,
             rule_keys=(), related=(), extra_head="", vendor=(), title=None, desc=None):
        meta = {p[0]: p for p in BIZ_PAGES}[fname]
        title = title or meta[2]
        desc = desc or meta[3]
        ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": title,
              "url": f'{self.c["SITE_URL"]}/{biz_url(fname)}', "description": desc,
              "applicationCategory": "BusinessApplication", "operatingSystem": "Any",
              "inLanguage": "en", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "SRD"}} if meta[4] not in ("guide", "hub") else None
        head = self.c["hub_head"](_esc(title), _esc(desc), biz_url(fname), faq=faq, extra_ld=ld)
        head = head.replace("</head>", KIT_CSS + extra_head + "\n</head>", 1)
        hero = self.c["hub_hero"](kicker, h1, sub).replace("{NAV}", self.c["nav_html"](key))
        tstr = dict(KIT_T)
        tstr.update(strings or {})
        faq_html = self.c["hub_faq"](faq) if faq else ""
        main = ('<main class="bz-wrap">' + body + _sources_html(self.R, rule_keys, self.today)
                + (('<div style="margin-top:2rem">' + faq_html + '</div>') if faq_html else "")
                + _related(related) + '</main>')
        data = ('<script id="bzR" type="application/json">' + _json.dumps(_rules_public(self.R), ensure_ascii=False).replace("</", "<\\/") + '</script>'
                '<script id="bzH" type="application/json">' + _json.dumps(self.H, ensure_ascii=False) + '</script>')
        vend = "".join(f'<script src="{v}" defer></script>' for v in vendor)
        scripts = data + '<script>' + self.engine + '</script>' + KIT_JS + vend + (('<script>' + js + '</script>') if js else "")
        html = (head + hero + main + _t_block(tstr) + scripts + "\n" + self.c["footer_html"]() + "\n</body>\n</html>")
        return clean_links(_fill_tokens(html, _rule_tokens(self.R, self.today), fname))


# ─────────────────────────────────────────────────────────────────────────────
# BTW calculator
# ─────────────────────────────────────────────────────────────────────────────
def _btw_page(X):
    R = X.R
    b = R["btw"][-1]
    rates = [(str(r), f"{r}%") for r in sorted(b["rates"], key=lambda r: (r != b["standard"], -r))]
    months = [(str(i), m) for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July",
                                                  "August", "September", "October", "November", "December"], 1)]
    years = [(str(y), str(y)) for y in range(X.today.year - 1, X.today.year + 2)]
    lm = X.today.month - 1 or 12
    ly = X.today.year if X.today.month > 1 else X.today.year - 1
    ann = b["annex_links"]
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Add or remove BTW</h2>
    {_field("amt", "Amount", "1.000", big=True)}
    <div class="bz-chips">
      <button type="button" class="bz-chip" data-set="100">100</button>
      <button type="button" class="bz-chip" data-set="1.000">1.000</button>
      <button type="button" class="bz-chip" data-set="10.000">10.000</button>
      <button type="button" class="bz-chip" data-set="100.000">100.000</button>
    </div>
    <div class="bz-grid bz-g2" style="margin-top:1rem">
      {_seg("mode", [("excl", "Amount is excl. BTW"), ("incl", "Amount is incl. BTW")], "excl", "The amount you typed")}
      {_seg("rate", rates, str(b["standard"]), "BTW rate")}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite">
      <div class="bz-k" id="rk">Price including BTW</div>
      <div class="bz-big" id="rbig">SRD 1.100,00</div>
      <div class="bz-say" id="rsay"></div>
    </div>
    <div class="bz-card">
      <table class="bz-tbl"><tbody id="rtbl"></tbody></table>
      {_share_bar()}
    </div>
  </div>
</div>

<div class="bz-card">
  <h2>Invoice with several lines or rates</h2>
  <p class="text-sm text-gray-600 mb-3">BTW is added up per rate over the lines, the way it appears on an invoice.</p>
  <div class="bz-scroll"><table class="bz-tbl" style="min-width:560px">
    <thead><tr><th>Price per item (SRD)</th><th>Quantity</th><th>BTW rate</th><th>Price includes BTW</th><th></th></tr></thead>
    <tbody id="lines"></tbody></table></div>
  <div class="bz-acts"><button type="button" class="bz-btn2" id="addline">+ Add line</button></div>
  <table class="bz-tbl" style="margin-top:.8rem"><tbody id="ltot"></tbody></table>
</div>

<div class="bz-grid bz-g2">
  <div class="bz-card">
    <h2>Do I have to charge BTW?</h2>
    <p class="text-sm text-gray-600 mb-3">A business must register for BTW when its turnover in a calendar year is more than SRD {b["threshold_year"]:,}.</p>
    {_field("turn", "Turnover this calendar year", "")}
    <div id="turnres" class="bz-ok" hidden></div>
  </div>
  <div class="bz-card">
    <h2>Late BTW return: what is the fine?</h2>
    <p class="text-sm text-gray-600 mb-3">The return and payment are due before the 16th of the next month. Fines follow S.B. 2025 no. 140.</p>
    <div class="bz-grid bz-g2">
      {_select("pm", "Return for month", months, lm)}
      {_select("py", "Year", years, ly)}
    </div>
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      <div><label class="bz-label" for="fd">Date filed (or today)</label><input id="fd" type="date" class="bz-in"></div>
      {_field("unpaid", "BTW paid late or unpaid", "", hint="Leave empty if paid on time")}
    </div>
    <div id="penres" style="margin-top:.8rem"></div>
  </div>
</div>

<div class="bz-card">
  <h2>Which BTW rate applies?</h2>
  <table class="bz-tbl"><tbody>
    <tr><td><b>10%</b></td><td>The general rate for goods and services.</td></tr>
    <tr><td><b>5%</b></td><td>Among others water, electricity, cooking gas and domestic goods transport (full list: annex 4 of the BTW law).</td></tr>
    <tr><td><b>25%</b></td><td>Certain luxury goods, among others heavy or expensive motor vehicles, speedboats, weapons and ammunition, and fireworks (full list: annex 3 and its specification).</td></tr>
    <tr><td><b>0%</b></td><td>Exports and the goods and services in annex 1.</td></tr>
    <tr><td><b>Exempt</b></td><td>For example medical care, financial services and domestic passenger transport (annex 2). No BTW is charged and no BTW can be reclaimed.</td></tr>
  </tbody></table>
  <p class="bz-src" style="margin-top:.7rem">Official texts:
    <a href="{ann["wet"]}" target="_blank" rel="noopener">BTW law 2022</a> &middot;
    <a href="{ann["wijziging_2022"]}" target="_blank" rel="noopener">amendment Dec 2022</a> &middot;
    <a href="{ann["wijziging_2023"]}" target="_blank" rel="noopener">amendment Sep 2023</a> &middot;
    <a href="{ann["spec_bijlage3"]}" target="_blank" rel="noopener">annex 3 specification</a> &middot;
    <a href="{ann["spec_bijlage2"]}" target="_blank" rel="noopener">annex 2 specification</a> &middot;
    <a href="{ann["register"]}" target="_blank" rel="noopener">check if a business is BTW-registered</a></p>
  <p class="bz-note">We do not list exact engine-size or price limits for the 25% rate, because annex 3 was changed in 2022 and again in 2023. Check the official annex.</p>
</div>
"""
    strings = {
        "k_incl": "Price including BTW", "k_excl": "Price excluding BTW",
        "say_excl": "{a} plus {r}% BTW ({b}) makes {c} including BTW.",
        "say_incl": "{a} including {r}% BTW contains {b} BTW. Without BTW it is {c}.",
        "row_excl": "Excluding BTW", "row_btw": "BTW {r}%", "row_incl": "Including BTW",
        "turn_yes": "Above ⟦BTW_THR⟧: you must be registered for BTW and charge it.",
        "turn_no": "Not above ⟦BTW_THR⟧ this year: registration is not required. Keep an eye on it as the year goes on.",
        "pen_ok": "Filed on time (deadline {d}). No fine.",
        "pen_late": "Deadline was {d}. That is {m} month(s) late.",
        "pen_filing": "Fine for filing late", "pen_pay": "Fine for paying late (⟦PEN_PAY⟧)", "pen_total": "Total fines",
        "pen_before": "Fines under S.B. 2025 no. 140 apply to returns filed from 1 January 2026.",
        "tot_rate": "{r}% BTW over {e}",
    }
    js = r"""
(function(){ var B=BZ, E=B.E, $=B.$;
function run(){
  var a = B.amt('amt'); var r = +B.segVal('rate'); var mode = B.segVal('mode');
  if(a===null){ $('rbig').textContent='–'; $('rtbl').innerHTML=''; $('rsay').textContent=''; return; }
  var x = mode==='incl' ? E.btwFromIncl(a, r) : E.btwFromExcl(a, r);
  $('rk').textContent = B.T(mode==='incl'?'k_excl':'k_incl');
  $('rbig').textContent = B.srd(mode==='incl'? x.excl : x.incl);
  $('rsay').textContent = mode==='incl' ? B.T('say_incl',{a:B.srd(x.incl), r:r, b:B.srd(x.btw), c:B.srd(x.excl)})
                                        : B.T('say_excl',{a:B.srd(x.excl), r:r, b:B.srd(x.btw), c:B.srd(x.incl)});
  $('rtbl').innerHTML = B.rows([[B.T('row_excl'), B.srd(x.excl)],[B.T('row_btw',{r:r}), B.srd(x.btw)],[B.T('row_incl'), B.srd(x.incl),'bz-tot']]);
  B.shareText = function(){ return $('rsay').textContent; };
  B.saveUrl(['amt','mode','rate']);
}
B.loadUrl(['amt','mode','rate']);
B.seg('mode', run); B.seg('rate', run); B.on(['amt'], 'input', run);
[].forEach.call(document.querySelectorAll('[data-set]'), function(c){ c.addEventListener('click', function(){ $('amt').value=B.fmtIn(E.parseAmount(c.getAttribute('data-set'))); run(); }); });
run();
// lines
var RATES = B.R.btw[B.R.btw.length-1].rates.slice().sort(function(a,b){return b-a;});
var STD = B.R.btw[B.R.btw.length-1].standard;
function addLine(v){ var tr=document.createElement('tr');
  var opts = RATES.map(function(r){ return '<option value="'+r+'"'+(r===STD?' selected':'')+'>'+r+'%</option>'; }).join('');
  tr.innerHTML = '<td><input class="bz-in bz-num" inputmode="decimal" data-f="a" value="'+(v||'')+'"></td>'+
    '<td><input class="bz-in bz-num" inputmode="decimal" data-f="q" value="1" style="max-width:6rem"></td>'+
    '<td><select class="bz-sel" data-f="r">'+opts+'</select></td>'+
    '<td style="text-align:center"><input type="checkbox" data-f="i" style="width:1.1rem;height:1.1rem"></td>'+
    '<td><button type="button" class="bz-x" aria-label="remove">&times;</button></td>';
  $('lines').appendChild(tr); tr.querySelector('.bz-x').onclick=function(){ tr.remove(); lines(); }; }
function lines(){ var L=[]; [].forEach.call($('lines').querySelectorAll('tr'), function(tr){
    var a=E.parseAmount(tr.querySelector('[data-f=a]').value, B.L); var q=E.parseNum(tr.querySelector('[data-f=q]').value, B.L);
    if(a===null) return; L.push({amount:a, qty:(q===null?1:q), rate:+tr.querySelector('[data-f=r]').value, incl:tr.querySelector('[data-f=i]').checked}); });
  var s = E.btwLines(L); var rs=[[B.T('row_excl'), B.srd(s.excl)]];
  s.groups.forEach(function(g){ rs.push([B.T('tot_rate',{r:g.rate, e:B.srd(g.excl)}), B.srd(g.btw), 'bz-sub']); });
  rs.push([B.T('row_incl'), B.srd(s.incl), 'bz-tot']); $('ltot').innerHTML = B.rows(rs); }
$('lines').addEventListener('input', lines); $('lines').addEventListener('change', lines);
$('addline').onclick=function(){ addLine(''); };
addLine('100'); addLine(''); lines();
// threshold
var TH = B.R.btw[B.R.btw.length-1].threshold_year*100;
B.on(['turn'],'input',function(){ var t=B.amt('turn'), el=$('turnres'); if(t===null){ el.hidden=true; return; }
  el.hidden=false; el.className = t>TH ? 'bz-warn' : 'bz-ok'; el.textContent = B.T(t>TH?'turn_yes':'turn_no'); });
// penalty
$('fd').value = B.today();
function pen(){ var m=+$('pm').value, y=+$('py').value; var ny = m===12?y+1:y, nm = m===12?1:m+1;
  var due = ny+'-'+E.pad2(nm)+'-'+E.pad2(B.R.deadlines.btw.day-1); var filed = $('fd').value || B.today();
  var un = B.amt('unpaid') || 0; var out=$('penres');
  if(filed < '2026-01-01'){ out.innerHTML='<div class="bz-note">'+B.esc(B.T('pen_before'))+'</div>'; return; }
  var p = E.btwPenalty(due, filed, un, B.R);
  if(!p || p.months===0){ out.innerHTML='<div class="bz-ok">'+B.esc(B.T('pen_ok',{d:B.fmtDate(due)}))+'</div>'; return; }
  out.innerHTML = '<div class="bz-warn">'+B.esc(B.T('pen_late',{d:B.fmtDate(due), m:p.months}))+'</div><table class="bz-tbl"><tbody>'+
    B.rows([[B.T('pen_filing'), B.srd(p.filing)],[B.T('pen_pay'), B.srd(p.payment)],[B.T('pen_total'), B.srd(p.total),'bz-tot']])+'</tbody></table>'; }
B.on(['pm','py','fd'],'change',pen); B.on(['unpaid'],'input',pen); pen();
})();
"""
    faq = [
        ("What is the BTW rate in Suriname?",
         "The general rate is 10% on goods and services. There is a 5% rate (among others water, electricity, cooking gas and domestic goods transport), a 25% rate for certain luxury goods and a 0% rate for exports and annex 1."),
        ("When must a business register for BTW?",
         "When its turnover in a calendar year is more than ⟦BTW_THR⟧ (Wet BTW art. 21). Below that, registration is not required."),
        ("When is the BTW return due?",
         "Every month, before the 16th day of the following month. Payment is due on the same date (Wet BTW art. 13)."),
        ("What happens if I file late?",
         "From ⟦PEN_FROM⟧ the fine for filing late is ⟦PEN_LIST⟧, depending on how many months late the return is. Paying late costs ⟦PEN_PAY_PCT⟧ of the unpaid BTW, up to ⟦PEN_PAY_MAX⟧ (⟦PEN_SRC⟧)."),
        ("How do I calculate BTW backwards from a price including BTW?",
         "Divide the price by 1.10 for the 10% rate (1.05 for 5%, 1.25 for 25%). The difference is the BTW. The calculator does this for you when you choose 'incl. BTW'."),
    ]
    return X.page("btw-calculator.html", "biz-btw", "Business tools", "BTW Calculator",
                  "Add or remove Surinamese BTW, check whether you must register and see what a late return costs.",
                  body, js, strings, faq, rule_keys=("btw", "btw_penalties"),
                  related=("biz-invoice", "biz-register", "biz-deadlines", "biz-g-btw"))


# ─────────────────────────────────────────────────────────────────────────────
# Deadlines (Python twin of BizEngine.monthlyDeadlines; parity is verified in the
# build check below and in tests). Used for the hub strip and the .ics feed.
# ─────────────────────────────────────────────────────────────────────────────
def _is_workday(d, H):
    return d.weekday() < 5 and d.isoformat() not in H["dates"]


def _nth_workday(y, m, n, H):
    d = _dt.date(y, m, 1)
    c = 0
    while True:
        if _is_workday(d, H):
            c += 1
            if c == n:
                return d
        d += _dt.timedelta(days=1)


def _wage_tax_due(y, m, rule, H):
    """Earliest of: the nth working day (Wet LB art. 20) and the last day of the
    Belastingdienst portal window (26th - 10th). Showing the later date could make
    someone miss the portal window, so the earlier one is the deadline we show."""
    nth = _nth_workday(y, m, rule["n"], H)
    cap = _dt.date(y, m, rule["portal_last_day"]) if rule.get("portal_last_day") else None
    if nth is None:
        return cap
    return min(nth, cap) if cap else nth


def _coverage(d, H):
    y = str(d.year)
    return "complete" if y in H["complete"] else ("incomplete" if y in H["incomplete"] else "unknown")


def monthly_deadlines(year, month, R, H):
    ny, nm = (year + 1, 1) if month == 12 else (year, month + 1)
    dl = R["deadlines"]
    return {"btw": _dt.date(ny, nm, dl["btw"]["day"] - 1),
            "wage_tax": _wage_tax_due(ny, nm, dl["wage_tax"], H),
            "apf": _dt.date(ny, nm, dl["apf"]["day"]),
            "coverage": _coverage(_dt.date(ny, nm, 1), H)}


def upcoming_deadlines(R, H, start, months=13):
    """All deadlines from `start` for the next `months` months, sorted."""
    out = []
    y, m = start.year, start.month
    # obligations for the previous month fall due this month
    py, pm = (y - 1, 12) if m == 1 else (y, m - 1)
    for i in range(months):
        yy, mm = py + (pm - 1 + i) // 12, (pm - 1 + i) % 12 + 1
        d = monthly_deadlines(yy, mm, R, H)
        period = f"{yy}-{mm:02d}"
        out.append({"date": d["btw"], "kind": "btw", "period": period, "coverage": "complete"})
        out.append({"date": d["wage_tax"], "kind": "wage_tax", "period": period, "coverage": d["coverage"]})
        out.append({"date": d["apf"], "kind": "apf", "period": period, "coverage": "complete"})
    ib = R["deadlines"]["ib"]
    for yy in (start.year, start.year + 1):
        for kind, md in [("ib_prov", ib["provisional"]), ("ib_final", ib["final"])] + \
                        [("ib_inst", x) for x in ib["installments"]]:
            out.append({"date": _dt.date(yy, int(md[:2]), int(md[3:])), "kind": kind, "period": str(yy), "coverage": "complete"})
    out = [o for o in out if o["date"] >= start]
    out.sort(key=lambda o: (o["date"], o["kind"]))
    seen, res = set(), []
    for o in out:
        k = (o["date"], o["kind"])
        if k not in seen:
            seen.add(k)
            res.append(o)
    return res


_DL_LABEL = {  # calendar feed is Dutch-first (local audience), with English in the description
    "btw": ("BTW-aangifte en betaling", "BTW-aangifte en betaling over {p} / BTW return and payment for {pe}"),
    "wage_tax": ("Loonbelasting en AOV aangifte", "Aangifte en afdracht loonbelasting en AOV over {p} (portaal: 26ste t/m 10de; wet: 7e werkdag, de vroegste geldt) / Wage tax and AOV return for {pe} (portal window 26th to 10th; law: 7th working day, whichever is first)"),
    "apf": ("APF pensioenpremie", "Afdracht APF pensioenpremie over {p} / APF pension premium for {pe}"),
    "ib_prov": ("Inkomstenbelasting: voorlopige aangifte", "Voorlopige aangifte inkomstenbelasting {p} / Provisional income tax return {p}"),
    "ib_final": ("Inkomstenbelasting: definitieve aangifte", "Definitieve aangifte inkomstenbelasting over {p0} / Final income tax return for {p0}"),
    "ib_inst": ("Inkomstenbelasting: termijn voorlopige aanslag", "Betaaltermijn voorlopige aanslag inkomstenbelasting {p} / Provisional income tax instalment {p}"),
}
_NL_MONTHS = ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september",
              "oktober", "november", "december"]
_EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
              "October", "November", "December"]
_DL_TOOL = {"btw": "btw-calculator", "wage_tax": "salary-calculator", "apf": "salary-calculator",
            "ib_prov": "income-tax-calculator", "ib_final": "income-tax-calculator",
            "ib_inst": "income-tax-calculator"}


def build_ics(R, H, site_url, start):
    """RFC 5545 all-day events. Stable UIDs so calendar apps update, not duplicate."""
    def esc(t):
        return t.replace("\\", "\\\\").replace(";", "\;").replace(",", "\\,").replace("\n", "\\n")

    def fold(line):
        out, b = [], line.encode("utf-8")
        while len(b) > 73:
            cut = 73
            while (b[cut] & 0xC0) == 0x80:
                cut -= 1
            out.append(b[:cut].decode("utf-8"))
            b = b[cut:]
        out.append(b.decode("utf-8"))
        return "\r\n ".join(out)

    stamp = start.strftime("%Y%m%dT000000Z")  # per-day stamp: no git churn on every 15-min build
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ExploreSuriname//Business deadlines//EN",
         "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Suriname tax deadlines (ExploreSuriname)",
         "X-WR-TIMEZONE:America/Paramaribo", "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for o in upcoming_deadlines(R, H, start, months=14):
        short, long_ = _DL_LABEL[o["kind"]]
        p = o["period"]
        if len(p) == 7:
            per = f"{_NL_MONTHS[int(p[5:7]) - 1]} {p[:4]}"
            per_en = f"{_EN_MONTHS[int(p[5:7]) - 1]} {p[:4]}"
        else:
            per = per_en = p
        prev = str(int(p) - 1) if len(p) == 4 else p
        summary = short
        desc = long_.format(p=per, pe=per_en, p0=prev)
        if o["coverage"] != "complete":
            desc += (". Datum berekend met de feestdagen die nu bekend zijn / date based on the public holidays known today")
        desc += f". {site_url}/{_DL_TOOL[o['kind']]}"
        d = o["date"]
        L += ["BEGIN:VEVENT", f"UID:{o['kind']}-{p}-{d:%Y%m%d}@exploresuriname.com", f"DTSTAMP:{stamp}",
              f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{(d + _dt.timedelta(days=1)):%Y%m%d}",
              fold("SUMMARY:" + esc(summary)), fold("DESCRIPTION:" + esc(desc)),
              f"URL:{site_url}/tax-deadlines", "TRANSP:TRANSPARENT",
              "BEGIN:VALARM", "ACTION:DISPLAY", fold("DESCRIPTION:" + esc(summary)), "TRIGGER:-P2D", "END:VALARM",
              "END:VEVENT"]
    L.append("END:VCALENDAR")
    return "\r\n".join(L) + "\r\n"


# ─────────────────────────────────────────────────────────────────────────────
# Shared live-feed renderers (data written by scripts/biz_feeds.py)
# ─────────────────────────────────────────────────────────────────────────────
def _feed_list(items, limit, tag_tenders=False):
    if not items:
        return '<p class="text-sm text-gray-600">No items available right now.</p>'
    li = []
    for it in items[:limit]:
        tag = '<span class="bz-tag">Tender</span>' if tag_tenders and it.get("tender") else ""
        li.append(f'<li>{tag}<a href="{_esc(it["link"])}" target="_blank" rel="noopener" translate="no">{_esc(it["title"])}</a>'
                  f'<small>{_esc(it.get("date", ""))}</small></li>')
    return '<ul class="bz-feed" style="padding:0;margin:0">' + "".join(li) + '</ul>'


def _feed_status(feeds, key):
    st = (feeds.get("status") or {}).get(key) or {}
    ok = st.get("ok", "")
    txt = f'<span>Last checked</span> <span>{_esc(ok[:16].replace("T", " "))}</span>' if ok else ""
    if st.get("fails", 0) >= 3:
        txt += ' &middot; <span class="bz-stale">The source could not be reached recently; showing the last items we received.</span>'
    return f'<p class="bz-src" style="margin-top:.5rem">{txt}</p>'


GROUPS = [
    ("calc", "Tax & money"), ("people", "Staff & payroll"), ("docs", "Invoices & paperwork"),
    ("trade", "Pricing, import & finance"), ("office", "Office tools"), ("live", "Live from the government"),
    ("guide", "Guides"),
]


def _hub_page(X, feeds, prices):
    cards = ""
    for g, label in GROUPS:
        items = [p for p in BIZ_PAGES if p[4] == g]
        cards += f'<h2 class="bz-sec">{label}</h2><div class="bz-tools">' + "".join(
            f'<a class="bz-tool" href="{p[0]}"><b>{p[2]}</b><span>{p[3]}</span></a>' for p in items) + '</div>'
    dl = upcoming_deadlines(X.R, X.H, X.today, months=3)[:6]
    kinds = {"btw": "BTW return and payment", "wage_tax": "Wage tax and AOV return", "apf": "APF pension premium",
             "ib_prov": "Income tax: provisional return", "ib_final": "Income tax: final return",
             "ib_inst": "Income tax: provisional instalment"}
    dl_rows = "".join(f'<tr><td class="bz-num"><span class="bz-date" data-d="{o["date"].isoformat()}">{o["date"].isoformat()}</span></td>'
                      f'<td>{kinds[o["kind"]]}</td></tr>' for o in dl)
    mp = ""
    PV = _prices_view(prices)
    if PV["rows"] and PV["source"] == "srdcheck":
        ck = PV["checked"][:10]
        mp = (f'<p class="text-sm"><span translate="no">{len(PV["rows"])}</span> products, as published now on the ministry&#39;s price portal. '
              f'Checked on <span class="bz-date" data-d="{ck}" translate="no">{ck}</span>.</p>')
    elif PV["rows"]:
        mp = (f'<p class="text-sm">Current list: <span class="bz-date" data-d="{PV["valid_from"]}">{PV["valid_from"]}</span> &ndash; '
              f'<span class="bz-date" data-d="{PV["valid_to"]}">{PV["valid_to"]}</span>, <span translate="no">{len(PV["rows"])}</span> products.</p>')
    body = f"""
<div class="bz-card" style="background:var(--mint);border-color:#BFDDB8">
  <p style="font-size:1.05rem;line-height:1.6;color:var(--forest)">Free tools for Surinamese businesses: no account, no limits, and they work on your phone, also offline.
  Every tax and wage rule is taken from the official source and checked every day.</p>
</div>
<div class="bz-grid bz-g3" style="margin-top:1rem">
  <div class="bz-card"><h2>Next deadlines</h2><table class="bz-tbl"><tbody>{dl_rows}</tbody></table>
    <div class="bz-acts"><a class="bz-btn2" href="tax-deadlines.html">All deadlines &amp; calendar</a></div></div>
  <div class="bz-card"><h2>Government tenders</h2>{_feed_list([i for i in feeds.get("bekendmakingen", []) if i.get("tender")], 5)}
    <div class="bz-acts"><a class="bz-btn2" href="government-tenders.html">All announcements</a></div></div>
  <div class="bz-card"><h2>From the Belastingdienst</h2>{_feed_list(feeds.get("belastingdienst", []), 5)}
    <div class="bz-acts"><a class="bz-btn2" href="government-tenders.html">More notices</a></div></div>
</div>
<div class="bz-card"><h2>Maximum prices of basic goods</h2>{mp}
  <div class="bz-acts"><a class="bz-btn2" href="max-prices-basic-goods.html">Search the price list</a></div></div>
{cards}
"""
    js = r"""
(function(){ [].forEach.call(document.querySelectorAll('.bz-date'), function(e){ e.textContent = BZ.fmtDate(e.getAttribute('data-d')); }); })();
"""
    faq = [("Are these tools really free?", "Yes. No account, no limits and no adverts inside the tools. Files you open in the PDF and image tools never leave your device."),
           ("How do you keep the rules up to date?", "Every rule comes from an official source such as the Belastingdienst, the pension fund or a decree in the Staatsblad. A daily check watches those sources and flags any change, and we only update a number after verifying the official text."),
           ("Can I use the tools on my phone?", "Yes. Every tool is made for phones first, and pages you have opened once also work without internet.")]
    return X.page("business.html", "biz", "For businesses", "Business Tools for Suriname",
                  "Calculators, document makers and live government information for Surinamese businesses, free.",
                  body, js, {}, faq, rule_keys=(), related=("biz-btw", "biz-salary", "biz-invoice"))


# ─────────────────────────────────────────────────────────────────────────────
# Entry point used by generate.py
# ─────────────────────────────────────────────────────────────────────────────
ICS_PATH = "data/belasting-deadlines.ics"   # calendar feed; root-absolute links so /nl/ and /es/ work


def build_business_pages(ctx):
    import os as _os
    if _os.environ.get("BIZ_SKIP") == "1":
        # Set by update.yml when tests/biz_engine.test.cjs fails: never publish
        # numbers from an engine that failed its tests; keep the live pages.
        print("  WARN BIZ_SKIP=1: engine tests failed, business pages NOT rebuilt (previous versions kept)")
        return {}, {}
    try:
        return _build(ctx)
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR business section skipped (previous pages kept): {type(e).__name__}: {e}")
        return {}, {}


def _build(ctx):
    X = _Ctx(ctx)
    X.bank_rates = ctx.get("bank_rates") or []
    X.banks_updated = ctx.get("banks_updated") or ""
    X.cbvs_rates = ctx.get("cbvs_rates") or []
    X.cbvs_live = ctx.get("cbvs_live")
    X.cbvs_updated = ctx.get("cbvs_updated") or ""
    feeds = _load("data/biz_feeds.json", {})
    prices = _load("data/max_prices.json", {})
    builders = {
        "business.html": lambda: _hub_page(X, feeds, prices),
        "btw-calculator.html": lambda: _btw_page(X),
    }
    for name, fn in list(globals().items()):
        if name.startswith("_page_") and callable(fn):
            fname = fn.__doc__.strip().split()[0]
            builders[fname] = (lambda f=fn: f(X, feeds, prices))
    # Fail-safe: a page that throws is skipped, so the copy already on the site
    # stays live and the rest of the build carries on.
    pages = {}
    for fname, fn in builders.items():
        try:
            pages[fname] = fn()
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR business page {fname} skipped (previous version kept): {type(e).__name__}: {e}")
    files = {}
    try:
        # In data/ on purpose: update.yml already commits data/, and /data/ is served publicly.
        files[ICS_PATH] = build_ics(X.R, X.H, ctx["SITE_URL"], X.today)
    except Exception as e:  # noqa: BLE001
        print(f"  ERROR {ICS_PATH} skipped (previous version kept): {type(e).__name__}: {e}")
    missing = [p[0] for p in BIZ_PAGES if p[0] not in pages]
    if missing:
        print("  WARN business pages not built:", ", ".join(missing))
    return pages, files


# ─────────────────────────────────────────────────────────────────────────────
# Minimum wage & overtime pay
# ─────────────────────────────────────────────────────────────────────────────
def _page_minwage(X, feeds, prices):
    """minimum-wage-suriname.html"""
    R = X.R
    mw = [e for e in R["minimum_wage_hourly"] if e["from"] <= X.today.isoformat()][-1]
    prev = [e for e in R["minimum_wage_hourly"] if e["from"] < mw["from"]]
    prev_txt = (f'<p class="text-sm text-gray-600">Before that: SRD <span class="bz-num">{prev[-1]["value"]:.2f}</span> per hour '
                f'(from <span class="bz-date" data-d="{prev[-1]["from"]}">{prev[-1]["from"]}</span>).</p>') if prev else ""
    wt = R["working_time"][-1]
    body = f"""
<div class="bz-res">
  <div class="bz-k">Minimum wage per hour</div>
  <div class="bz-big">SRD <span class="bz-money" data-c="{round(mw['value']*100)}">{mw['value']:.2f}</span></div>
  <div class="bz-say">Gross, for every sector, from <span class="bz-date" data-d="{mw['from']}">{mw['from']}</span>. Employers may always pay more.</div>
</div>
{prev_txt}
<div class="bz-grid bz-g2" style="margin-top:1rem">
  <div class="bz-card">
    <h2>What is that per week and per month?</h2>
    {_field("hpw", "Hours worked per week", "40", prefix="", mode="decimal")}
    <table class="bz-tbl" style="margin-top:.8rem"><tbody id="conv"></tbody></table>
    <p class="bz-note">The law sets an hourly minimum. The monthly figure is an average (weekly pay &times; 52 &divide; 12) to help you compare.</p>
  </div>
  <div class="bz-card">
    <h2>Is a wage above the minimum?</h2>
    {_field("chk", "Wage", "")}
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_seg("per", [("h", "per hour"), ("w", "per week"), ("m", "per month")], "m", "Paid")}
      {_field("chkh", "Hours per week", "40", prefix="")}
    </div>
    <div id="chkres" style="margin-top:.7rem"></div>
  </div>
</div>
<div class="bz-card">
  <h2>Overtime pay</h2>
  <p class="text-sm text-gray-600 mb-3">Overtime needs a permit from the Labour Inspectorate. Pay is at least 150% on a normal day and 200% on a Sunday or rest day; 300% applies to public holidays where the collective agreement says so.</p>
  <div class="bz-grid bz-g3">
    {_field("otw", "Normal hourly wage", f"{mw['value']:.2f}".replace('.', ','))}
    {_field("oth", "Overtime hours this month", "10", prefix="")}
    {_select("otp", "Type of day", [("150", "Normal working day (150%)"), ("200", "Sunday or rest day (200%)"), ("300", "Public holiday, if agreed (300%)")], "150")}
  </div>
  <div class="bz-res" style="margin-top:1rem" aria-live="polite">
    <div class="bz-k">Gross overtime pay</div><div class="bz-big" id="otbig">–</div><div class="bz-say" id="otsay"></div>
  </div>
  <table class="bz-tbl"><tbody id="ottbl"></tbody></table>
  <p class="bz-src">Overtime pay is taxed with its own lower table (Wet Loonbelasting art. 17c) and 4% AOV applies. For a full payslip use the <a href="salary-calculator.html">salary calculator</a>.</p>
</div>
<div class="bz-card">
  <h2>Working hours limits</h2>
  <table class="bz-tbl"><tbody>
    <tr><td>Maximum per day</td><td class="n">{str(wt['max_day_hours']).replace('.', ',')} h</td></tr>
    <tr><td>Maximum per week</td><td class="n">{wt['max_week_hours']} h</td></tr>
    <tr><td>Overtime</td><td class="n">permit required</td></tr>
  </tbody></table>
</div>
"""
    strings = {"c_week": "Per week ({h} hours)", "c_month": "Per month (average)", "c_day": "Per 8-hour day",
               "chk_ok": "{w} per hour. That is at or above the minimum of {m}.",
               "chk_low": "{w} per hour. That is BELOW the minimum of {m}.",
               "ot_say": "{h} hours at {p}% of {w} per hour.",
               "ot_tax": "Overtime wage tax (art. 17c)", "ot_aov": "AOV ⟦AOV⟧", "ot_net": "Estimated overtime pay after tax and AOV"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var MW=E.pick(B.R.minimum_wage_hourly, B.today()); var mwc=Math.round(MW.value*100);
[].forEach.call(document.querySelectorAll('.bz-date'), function(e){ e.textContent = B.fmtDate(e.getAttribute('data-d')); });
[].forEach.call(document.querySelectorAll('.bz-money'), function(e){ e.textContent = B.money(+e.getAttribute('data-c')); });
function conv(){ var h=B.num('hpw'); if(h===null||h<=0){ $('conv').innerHTML=''; return; }
  var wk=Math.round(mwc*h), mo=Math.round(mwc*h*52/12);
  $('conv').innerHTML = B.rows([[B.T('c_day'), B.srd(mwc*8)],[B.T('c_week',{h:E.fmtNum(h,B.L)}), B.srd(wk)],[B.T('c_month'), B.srd(mo),'bz-tot']]); }
function chk(){ var w=B.amt('chk'), h=B.num('chkh'), per=B.segVal('per'), o=$('chkres'); if(w===null||!h){ o.innerHTML=''; return; }
  var hr = per==='h'? w : (per==='w'? w/h : w*12/52/h);
  var ok = Math.round(hr) >= mwc; o.innerHTML='<div class="'+(ok?'bz-ok':'bz-warn')+'">'+B.esc(B.T(ok?'chk_ok':'chk_low',{w:B.srd(Math.round(hr)), m:B.srd(mwc)}))+'</div>'; }
function ot(){ var w=B.amt('otw'), h=B.num('oth'), p=+$('otp').value; if(w===null||h===null){ $('otbig').textContent='–'; $('ottbl').innerHTML=''; return; }
  var pay=Math.round(w*h*p/100); var OT=E.pick(B.R.overtime_tax, B.today()); var tax=E.bands(pay, OT.bands_month); var aov=E.pctOf(pay, E.pick(B.R.aov,B.today()).pct);
  $('otbig').textContent=B.srd(pay); $('otsay').textContent=B.T('ot_say',{h:E.fmtNum(h,B.L), p:p, w:B.srd(w)});
  $('ottbl').innerHTML=B.rows([[B.T('ot_tax'), '− '+B.srd(tax)],[B.T('ot_aov'), '− '+B.srd(aov)],[B.T('ot_net'), B.srd(pay-tax-aov),'bz-tot']]);
  B.shareText=function(){ return $('otsay').textContent+' = '+$('otbig').textContent; }; }
B.on(['hpw'],'input',conv); B.on(['chk','chkh'],'input',chk); B.seg('per',chk); B.on(['otw','oth'],'input',ot); B.on(['otp'],'change',ot);
conv(); chk(); ot();
})();
"""
    faq = [("What is the minimum wage in Suriname?", f"SRD {mw['value']:.2f} gross per hour from {mw['from']}, for all sectors (⟦MW_SRC⟧)."),
           ("How much is the minimum wage per month?", "The law sets an hourly wage. At 40 hours a week that is on average about ⟦MW_MONTH⟧ a month (hourly wage × 40 × 52 ÷ 12)."),
           ("How much extra is overtime?", "At least 150% of the hourly wage on a normal working day and 200% on a Sunday or rest day. Overtime requires a permit from the Labour Inspectorate.")]
    return X.page("minimum-wage-suriname.html", "biz-minwage", "Staff & payroll", "Minimum Wage & Overtime Pay",
                  "The current minimum hourly wage in Suriname, what it means per month, and what overtime pays.",
                  body, js, strings, faq, rule_keys=("minimum_wage_hourly", "working_time", "overtime_tax", "aov"),
                  related=("biz-salary", "biz-timesheet", "biz-payslip", "biz-g-staff"))


# ─────────────────────────────────────────────────────────────────────────────
# Timesheet
# ─────────────────────────────────────────────────────────────────────────────
def _page_timesheet(X, feeds, prices):
    """timesheet.html"""
    mw = [e for e in X.R["minimum_wage_hourly"] if e["from"] <= X.today.isoformat()][-1]
    wt = X.R["working_time"][-1]
    days = [("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"), ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"), ("sun", "Sunday")]
    rows = "".join(
        f'<tr data-day="{k}"><td><b>{n}</b></td>'
        f'<td><input class="bz-in bz-num" data-f="s" inputmode="numeric" value="{"07:30" if k not in ("sat","sun") else ""}" style="min-width:5.5rem"></td>'
        f'<td><input class="bz-in bz-num" data-f="e" inputmode="numeric" value="{"16:00" if k not in ("sat","sun") else ""}" style="min-width:5.5rem"></td>'
        f'<td><input class="bz-in bz-num" data-f="b" inputmode="numeric" value="{"30" if k not in ("sat","sun") else ""}" style="max-width:5rem"></td>'
        f'<td class="n bz-num" data-f="h">–</td></tr>' for k, n in days)
    body = f"""
<div class="bz-card">
  <h2>Hours this week</h2>
  <p class="text-sm text-gray-600 mb-3">Type start and end times like 07:30 and 16:00, and the unpaid break in minutes. Night shifts past midnight are fine.</p>
  <div class="bz-scroll"><table class="bz-tbl" style="min-width:560px">
    <thead><tr><th>Day</th><th>Start</th><th>End</th><th>Break (min)</th><th class="n">Hours</th></tr></thead>
    <tbody id="ts">{rows}</tbody></table></div>
  <div id="tsflags"></div>
</div>
<div class="bz-grid bz-g2">
  <div class="bz-card">
    <h2>Pay for this week</h2>
    {_field("rate", "Hourly wage", f"{mw['value']:.2f}".replace('.', ','))}
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_field("normal", "Normal hours per day", "8", prefix="", hint="Hours above this on a weekday count as overtime")}
      {_select("sunpct", "Sunday hours paid at", [("200", "200% (rest day)"), ("100", "100% (normal working day)")], "200")}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Gross pay this week</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tot"></tbody></table>{_share_bar()}</div>
  </div>
</div>
"""
    strings = {"f_day": "{d}: {h} hours is more than the legal {m} hours per day.",
               "f_week": "Total {h} hours is more than the legal {m} hours per week.",
               "f_bad": "Check the times on {d} (use 07:30 style).",
               "t_normal": "Normal hours", "t_ot": "Overtime at 150%", "t_sun": "Sunday hours", "t_total": "Total gross",
               "say": "{h} hours worked this week.",
               "d_mon": "Monday", "d_tue": "Tuesday", "d_wed": "Wednesday", "d_thu": "Thursday", "d_fri": "Friday", "d_sat": "Saturday", "d_sun": "Sunday"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var WT=B.R.working_time[B.R.working_time.length-1];
function hrs(m){ return E.fmtNum(m/60, B.L, 2); }
function run(){ var total=0, normal=0, ot=0, sun=0, flags=[]; var nd=B.num('normal'); if(nd===null) nd=8;
  [].forEach.call($('ts').querySelectorAll('tr'), function(tr){ var d=tr.getAttribute('data-day');
    var s=tr.querySelector('[data-f=s]').value.trim(), e=tr.querySelector('[data-f=e]').value.trim(), b=tr.querySelector('[data-f=b]').value.trim();
    var cell=tr.querySelector('[data-f=h]'); if(!s&&!e){ cell.textContent='–'; return; }
    var m=E.shiftMinutes(s,e, b?parseInt(b,10)||0:0); if(m===null){ cell.textContent='?'; flags.push(['warn',B.T('f_bad',{d:B.T('d_'+d)})]); return; }
    cell.textContent=hrs(m); total+=m;
    if(m > WT.max_day_hours*60) flags.push(['warn',B.T('f_day',{d:B.T('d_'+d), h:hrs(m), m:E.fmtNum(WT.max_day_hours,B.L)})]);
    if(d==='sun'){ sun+=m; return; }
    var n=Math.min(m, nd*60); normal+=n; ot+=m-n; });
  if(total > WT.max_week_hours*60) flags.push(['warn',B.T('f_week',{h:hrs(total), m:WT.max_week_hours})]);
  $('tsflags').innerHTML=flags.map(function(f){ return '<div class="bz-'+f[0]+'">'+B.esc(f[1])+'</div>'; }).join('');
  var r=B.amt('rate'); var sp=+$('sunpct').value;
  if(r===null){ $('big').textContent='–'; $('tot').innerHTML=''; return; }
  var pn=Math.round(r*normal/60), po=Math.round(r*ot/60*1.5), ps=Math.round(r*sun/60*sp/100);
  $('big').textContent=B.srd(pn+po+ps); $('say').textContent=B.T('say',{h:hrs(total)});
  $('tot').innerHTML=B.rows([[B.T('t_normal')+' ('+hrs(normal)+' h)', B.srd(pn)],[B.T('t_ot')+' ('+hrs(ot)+' h)', B.srd(po)],[B.T('t_sun')+' ('+hrs(sun)+' h, '+sp+'%)', B.srd(ps)],[B.T('t_total'), B.srd(pn+po+ps),'bz-tot']]);
  B.shareText=function(){ return $('say').textContent+' '+$('big').textContent; };
  var st=[]; [].forEach.call($('ts').querySelectorAll('input'), function(i){ st.push(i.value); }); B.store('timesheet', {v:st, r:$('rate').value, n:$('normal').value});
}
var saved=B.store('timesheet'); if(saved && saved.v){ var ins=$('ts').querySelectorAll('input'); saved.v.forEach(function(v,i){ if(ins[i]) ins[i].value=v; }); if(saved.r) $('rate').value=saved.r; if(saved.n) $('normal').value=saved.n; }
$('ts').addEventListener('input', run); B.on(['rate','normal'],'input',run); B.on(['sunpct'],'change',run); run();
})();
"""
    return X.page("timesheet.html", "biz-timesheet", "Staff & payroll", "Timesheet & Work Hours",
                  "Add up the hours of the week, see where the legal limits are crossed and what the week pays.",
                  body, js, strings, None, rule_keys=("working_time", "minimum_wage_hourly"),
                  related=("biz-minwage", "biz-salary", "biz-payslip"))


# ─────────────────────────────────────────────────────────────────────────────
# Holiday days & allowance (Vakantiewet 1975)
# ─────────────────────────────────────────────────────────────────────────────
def _page_vacation(X, feeds, prices):
    """vacation-calculator.html"""
    tf = X.R["tax_free"][-1]
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>How many holiday days?</h2>
    {_seg("svc", [("full", "Full calendar years in service"), ("part", "First year, not yet complete")], "full", "Situation")}
    <div id="fullbox" style="margin-top:.8rem">{_field("years", "Completed calendar years with this employer", "1", prefix="", mode="numeric")}</div>
    <div id="partbox" style="margin-top:.8rem" hidden>{_field("months", "Full months worked in the first year", "6", prefix="", mode="numeric")}</div>
    <h2 style="margin-top:1.2rem">Holiday allowance</h2>
    {_field("month", "Monthly wage", "10.000")}
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_select("wd", "Working days per week", [("5", "5 days"), ("6", "6 days")], "5")}
      {_field("day", "Daily wage", "", hint="Filled in from the monthly wage; you can change it")}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Holiday days per year</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>{_share_bar()}</div>
  </div>
</div>
<div class="bz-card">
  <h2>Leaving the job?</h2>
  <p class="text-sm text-gray-600 mb-3">An employee who leaves (other than for an urgent reason) gets one twelfth of the year's holiday days for each full month worked that year. Unused days are paid out with the allowance (art. 12).</p>
  <div class="bz-grid bz-g2">
    {_field("mthis", "Full months worked this calendar year", "6", prefix="", mode="numeric")}
    {_field("taken", "Holiday days already taken this year", "0", prefix="", mode="decimal")}
  </div>
  <table class="bz-tbl" style="margin-top:.8rem"><tbody id="term"></tbody></table>
</div>
<div class="bz-card">
  <h2>The rules in short</h2>
  <ul style="padding-left:1.1rem;list-style:disc;line-height:1.7">
    <li>⟦VAC_FIRST⟧ working days after a full calendar year with the same employer, ⟦VAC_STEP⟧ days more for each following year, up to ⟦VAC_MAX⟧ days.</li>
    <li>In the first, incomplete year: 1 day for each full month worked.</li>
    <li>During the holiday the normal wage continues, plus a holiday allowance of half the daily wage for each holiday day.</li>
    <li>The holiday allowance is free of wage tax up to one month's wage, with a maximum of SRD {tf['holiday_allowance_max_year']:,} per year. Tax on any part above that is not calculated here.</li>
  </ul>
</div>
"""
    strings = {"say_full": "After {y} full calendar year(s) with the same employer.", "say_part": "For {m} full month(s) in the first year.",
               "r_days": "Holiday days", "r_daily": "Daily wage used", "r_allow": "Holiday allowance (½ daily wage × days)",
               "r_free": "Tax-free part of the allowance", "r_taxable": "Part above the tax-free limit",
               "t_ent": "Holiday days earned this year so far", "t_left": "Days not yet taken", "t_pay": "Payout: wage for these days", "t_allow": "Plus holiday allowance", "t_total": "Total payout",
               "days": "{n} days"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var TF=B.R.tax_free[B.R.tax_free.length-1];
var dayEdited=false;
function daily(){ var m=B.amt('month'), wd=+$('wd').value; if(m===null) return null; return Math.round(m*12/(wd*52)); }
function run(){ var mode=B.segVal('svc'); $('fullbox').hidden = mode!=='full'; $('partbox').hidden = mode==='full';
  var days = mode==='full' ? E.vacationDays(Math.max(0, Math.floor(B.num('years')||0)), B.R) : E.vacationPartial(Math.floor(B.num('months')||0), B.R);
  if(!dayEdited){ var d=daily(); $('day').value = d===null ? '' : E.fmt(d, B.L); }
  var dw=B.amt('day'); var m=B.amt('month');
  $('big').textContent=B.T('days',{n:E.fmtNum(days,B.L)});
  $('say').textContent= mode==='full' ? B.T('say_full',{y:Math.floor(B.num('years')||0)}) : B.T('say_part',{m:Math.floor(B.num('months')||0)});
  if(dw===null){ $('tbl').innerHTML=''; return; }
  var allow=E.vacationAllowance(days, dw, B.R); var cap=Math.min(m===null?allow:m, TF.holiday_allowance_max_year*100); var free=Math.min(allow, cap);
  $('tbl').innerHTML=B.rows([[B.T('r_days'), E.fmtNum(days,B.L)],[B.T('r_daily'), B.srd(dw)],[B.T('r_allow'), B.srd(allow),'bz-tot'],[B.T('r_free'), B.srd(free),'bz-sub'],[B.T('r_taxable'), B.srd(allow-free),'bz-sub']]);
  B.shareText=function(){ return $('big').textContent+'. '+B.T('r_allow')+': '+B.srd(allow); };
  // termination
  var mt=Math.floor(B.num('mthis')||0), tk=B.num('taken')||0; var ent=E.vacationOnTermination(days, mt); var left=Math.max(0, ent-tk);
  var pay=Math.round(left*dw), al=E.vacationAllowance(left, dw, B.R);
  $('term').innerHTML=B.rows([[B.T('t_ent'), E.fmtNum(ent,B.L,2)],[B.T('t_left'), E.fmtNum(left,B.L,2)],[B.T('t_pay'), B.srd(pay)],[B.T('t_allow'), B.srd(al)],[B.T('t_total'), B.srd(pay+al),'bz-tot']]);
}
$('day').addEventListener('input', function(){ dayEdited = $('day').value.trim()!==''; run(); });
B.seg('svc',run); B.on(['years','months','month','mthis','taken'],'input',run); B.on(['wd'],'change',function(){ dayEdited=false; run(); }); run();
})();
"""
    faq = [("How many holiday days does an employee get in Suriname?",
            "⟦VAC_FIRST⟧ working days after a full calendar year with the same employer, rising by ⟦VAC_STEP⟧ days each following year to a maximum of ⟦VAC_MAX⟧ (Vakantiewet 1975 art. 7)."),
           ("How much is the holiday allowance (vakantietoelage)?",
            "Half of the daily wage for each holiday day taken, on top of the normal wage (art. 10)."),
           ("Is the holiday allowance taxed?",
            "It is free of wage tax up to one month's wage, with a maximum of ⟦HOL_MAX⟧ per year (from ⟦HOL_FROM⟧).")]
    return X.page("vacation-calculator.html", "biz-vacation", "Staff & payroll", "Holiday Days & Allowance",
                  "How many holiday days an employee has, what the holiday allowance is and what is paid out when someone leaves.",
                  body, js, strings, faq, rule_keys=("vacation", "tax_free"),
                  related=("biz-salary", "biz-payslip", "biz-g-staff"))


# ─────────────────────────────────────────────────────────────────────────────
# Working days
# ─────────────────────────────────────────────────────────────────────────────
def _page_workdays(X, feeds, prices):
    """working-days-calculator.html"""
    body = f"""
<div class="bz-grid bz-g2">
  <div class="bz-card">
    <h2>Add working days to a date</h2>
    <div class="bz-grid bz-g2">
      <div><label class="bz-label" for="d0">Start date</label><input id="d0" type="date" class="bz-in"></div>
      {_field("n", "Working days to add", "30", prefix="", mode="numeric")}
    </div>
    <div class="bz-chips"><button type="button" class="bz-chip" data-n="5">5</button><button type="button" class="bz-chip" data-n="10">10</button>
      <button type="button" class="bz-chip" data-n="14">14</button><button type="button" class="bz-chip" data-n="30">30</button><button type="button" class="bz-chip" data-n="60">60</button></div>
    <div class="bz-res" style="margin-top:1rem" aria-live="polite"><div class="bz-k">Ends on</div><div class="bz-big" id="r1">–</div><div class="bz-say" id="s1"></div></div>
    <div id="w1"></div>
  </div>
  <div class="bz-card">
    <h2>Count working days between two dates</h2>
    <div class="bz-grid bz-g2">
      <div><label class="bz-label" for="a">From</label><input id="a" type="date" class="bz-in"></div>
      <div><label class="bz-label" for="b">To (included)</label><input id="b" type="date" class="bz-in"></div>
    </div>
    <div class="bz-res" style="margin-top:1rem" aria-live="polite"><div class="bz-k">Working days</div><div class="bz-big" id="r2">–</div><div class="bz-say" id="s2"></div></div>
    <div id="w2"></div>
  </div>
</div>
<div class="bz-card">
  <h2>Calendar days, for payment terms</h2>
  <div class="bz-grid bz-g3">
    <div><label class="bz-label" for="c0">Invoice date</label><input id="c0" type="date" class="bz-in"></div>
    {_field("cn", "Payment term in calendar days", "30", prefix="", mode="numeric")}
    <div><span class="bz-label">Due date</span><div class="bz-in" id="r3" style="background:var(--paper-2)">–</div></div>
  </div>
  <p class="bz-src" id="s3" style="margin-top:.5rem"></p>
</div>
<div class="bz-card"><h2>Public holidays used</h2><div id="hol" class="bz-scroll"></div>
  <p class="bz-src">Working days are Monday to Friday, except official public holidays. Holidays that fall on a Saturday or Sunday are not moved.</p></div>
"""
    strings = {"s_add": "{n} working days after {d}.", "s_count": "Of {c} calendar days, {w} are working days.",
               "w_incomplete": "Not all public holidays of this period have been announced yet. The result may still change.",
               "w_unknown": "Public holidays for this period are not known yet. Only weekends were skipped.",
               "s_due": "Falls on a {w}.", "s_due_off": "Falls on a {w}, which is not a working day; many businesses then pay on the next working day, {n}.",
               "h_date": "Date", "h_name": "Holiday",
               "h_incomplete": "{y}: not all public holidays have been officially announced yet. Holidays that follow the lunar or Hindu calendar are added when they are announced."}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$,H=B.H;
function warn(cov){ return cov==='complete' ? '' : '<div class="bz-note">'+B.esc(B.T(cov==='incomplete'?'w_incomplete':'w_unknown'))+'</div>'; }
function wd(iso){ var d=new Date(iso+'T12:00:00Z'); return d.toLocaleDateString(B.L==='en'?'en-GB':(B.L==='es'?'es-ES':'nl-NL'),{weekday:'long', timeZone:'UTC'}); }
function one(){ var d=$('d0').value, n=Math.floor(B.num('n')); if(!d||isNaN(n)||n<0){ $('r1').textContent='–'; return; }
  var r=E.addWorkingDays(d, n, H); $('r1').textContent=B.fmtDate(r.date); $('s1').textContent=B.T('s_add',{n:n, d:B.fmtDate(d)}); $('w1').innerHTML=warn(r.coverage);
  B.shareText=function(){ return $('s1').textContent+' '+$('r1').textContent; }; }
function two(){ var a=$('a').value, b=$('b').value; if(!a||!b){ $('r2').textContent='–'; return; }
  var r=E.countWorkingDays(a,b,H); var c=Math.abs(E.daysBetween(a,b))+1; $('r2').textContent=r.count; $('s2').textContent=B.T('s_count',{c:c, w:r.count}); $('w2').innerHTML=warn(r.coverage); }
function three(){ var d=$('c0').value, n=Math.floor(B.num('cn')); if(!d||isNaN(n)){ $('r3').textContent='–'; return; }
  var due=E.addDays(d,n); $('r3').textContent=B.fmtDate(due);
  if(E.isWorkingDay(due,H)) $('s3').textContent=B.T('s_due',{w:wd(due)}); else $('s3').textContent=B.T('s_due_off',{w:wd(due), n:B.fmtDate(E.addWorkingDays(due,1,H).date)}); }
var t=B.today(); $('d0').value=t; $('a').value=t; $('b').value=E.addDays(t,30); $('c0').value=t;
B.on(['d0','a','b','c0'],'change',function(){ one(); two(); three(); }); B.on(['n','cn'],'input',function(){ one(); three(); });
[].forEach.call(document.querySelectorAll('[data-n]'), function(c){ c.onclick=function(){ $('n').value=c.getAttribute('data-n'); one(); }; });
one(); two(); three();
var ks=Object.keys(H.dates).filter(function(k){ return k>=t.slice(0,4)+'-01-01'; }).sort();
$('hol').innerHTML='<table class="bz-tbl"><thead><tr><th>'+B.esc(B.T('h_date'))+'</th><th>'+B.esc(B.T('h_name'))+'</th></tr></thead><tbody>'+ks.map(function(k){ return '<tr><td>'+B.esc(B.fmtDate(k))+'</td><td translate="no">'+B.esc(H.names[k]||'')+'</td></tr>'; }).join('')+'</tbody></table>'+
  Object.keys(H.incomplete).map(function(y){ return '<div class="bz-note">'+B.esc(B.T('h_incomplete',{y:y}))+'</div>'; }).join('');
})();
"""
    return X.page("working-days-calculator.html", "biz-workdays", "Tax & money", "Working Days Calculator",
                  "Add working days to a date or count them, skipping weekends and Surinamese public holidays.",
                  body, js, strings, None, rule_keys=(), related=("biz-deadlines", "biz-invoice", "biz-reminder"))


# ─────────────────────────────────────────────────────────────────────────────
# Tax deadlines + .ics subscription
# ─────────────────────────────────────────────────────────────────────────────
def _page_deadlines(X, feeds, prices):
    """tax-deadlines.html"""
    site = X.c["SITE_URL"]
    host = site.split("://", 1)[1]
    webcal = f"webcal://{host}/{ICS_PATH}"
    gcal = "https://calendar.google.com/calendar/render?cid=" + webcal.replace(":", "%3A").replace("/", "%2F")
    body = f"""
<div class="bz-card" style="background:var(--mint);border-color:#BFDDB8">
  <h2>Get the deadlines in your phone's calendar</h2>
  <p class="text-sm" style="color:var(--forest)">Subscribe once. Your calendar then updates itself and reminds you two days before every deadline.</p>
  <div class="bz-acts">
    <a class="bz-btn" href="{webcal}">Subscribe (iPhone, Outlook, Mac)</a>
    <a class="bz-btn2" href="{gcal}" target="_blank" rel="noopener">Add to Google Calendar</a>
    <a class="bz-btn2" href="/{ICS_PATH}" download>Download .ics file</a>
  </div>
</div>
<div class="bz-card">
  <h2>Upcoming deadlines</h2>
  <div class="bz-seg" id="flt" role="group" style="margin-bottom:.8rem">
    <button type="button" data-v="all" aria-pressed="true">All</button><button type="button" data-v="btw" aria-pressed="false">BTW</button>
    <button type="button" data-v="staff" aria-pressed="false">Staff</button><button type="button" data-v="ib" aria-pressed="false">Income tax</button>
  </div>
  <div class="bz-scroll"><table class="bz-tbl"><thead><tr><th>Due date</th><th>What</th><th>Period</th><th></th></tr></thead><tbody id="dl"></tbody></table></div>
  <div id="dlw"></div>
</div>
<div class="bz-card">
  <h2>How the dates are set</h2>
  <table class="bz-tbl"><tbody>
    <tr><td><b>BTW</b></td><td>Return and payment before the 16th of the next month.</td><td class="bz-src">Wet BTW art. 13</td></tr>
    <tr><td><b>Wage tax &amp; AOV</b></td><td>The law allows until the 7th working day after the end of the month, but the Belastingdienst portal accepts the return only from the 26th up to and including the 10th. We show whichever comes first.</td><td class="bz-src">Wet Loonbelasting art. 20; Belastingdienst</td></tr>
    <tr><td><b>APF pension</b></td><td>Premium by the 15th of the next month.</td><td class="bz-src">Algemeen Pensioenfonds</td></tr>
    <tr><td><b>Income tax</b></td><td>Provisional return by 15 April; final return within four months after the year (30 April); the provisional assessment in four instalments: 15 April, 15 July, 15 October and 31 December.</td><td class="bz-src">Wet IB art. 42a, 42b, 43</td></tr>
  </tbody></table>
  <p class="bz-note">The Belastingdienst sometimes gives extra time or waives fines after a system outage. Those notices appear on our <a href="government-tenders.html" style="text-decoration:underline">announcements page</a>.</p>
</div>
"""
    strings = {"k_btw": "BTW return and payment", "k_wage_tax": "Wage tax and AOV return", "k_apf": "APF pension premium",
               "k_ib_prov": "Income tax: provisional return", "k_ib_final": "Income tax: final return",
               "k_ib_inst": "Income tax: provisional instalment", "p_final": "year {y}",
               "today": "today", "in_days": "in {n} days", "tomorrow": "tomorrow",
               "w_cov": "Dates marked * are based on the public holidays known today and may shift by a day when the remaining holidays of that year are announced.",
               "open": "Calculator"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$,H=B.H,R=B.R;
var TOOL={btw:'btw-calculator.html',wage_tax:'salary-calculator.html',apf:'salary-calculator.html',ib_prov:'income-tax-calculator.html',ib_final:'income-tax-calculator.html',ib_inst:'income-tax-calculator.html'};
var GRP={btw:'btw',wage_tax:'staff',apf:'staff',ib_prov:'ib',ib_final:'ib',ib_inst:'ib'};
function per(p){ if(p.length===4) return p; var d=new Date(Date.UTC(+p.slice(0,4), +p.slice(5,7)-1, 1)); return d.toLocaleDateString(B.L==='en'?'en-GB':(B.L==='es'?'es-ES':'nl-NL'),{month:'long',year:'numeric',timeZone:'UTC'}); }
var t=B.today(), list=[], y=+t.slice(0,4), m=+t.slice(5,7);
var py=m===1?y-1:y, pm=m===1?12:m-1;
for(var i=0;i<13;i++){ var yy=py+Math.floor((pm-1+i)/12), mm=(pm-1+i)%12+1; var d=E.monthlyDeadlines(yy,mm,R,H); var p=yy+'-'+E.pad2(mm);
  list.push({d:d.btw,k:'btw',p:p,c:'complete'}); list.push({d:d.wageTax,k:'wage_tax',p:p,c:d.wageTaxCoverage}); list.push({d:d.apf,k:'apf',p:p,c:'complete'}); }
var IB=R.deadlines.ib; [y,y+1].forEach(function(yy){ list.push({d:yy+'-'+IB.provisional,k:'ib_prov',p:String(yy),c:'complete'}); list.push({d:yy+'-'+IB.final,k:'ib_final',p:String(yy-1),c:'complete'});
  IB.installments.forEach(function(x){ list.push({d:yy+'-'+x,k:'ib_inst',p:String(yy),c:'complete'}); }); });
list=list.filter(function(o){ return o.d>=t; }).sort(function(a,b){ return a.d<b.d?-1:(a.d>b.d?1:(a.k<b.k?-1:1)); });
var seen={}; list=list.filter(function(o){ var k=o.d+o.k; if(seen[k]) return false; seen[k]=1; return true; }).slice(0,30);
function draw(){ var f=B.segVal('flt'), star=false;
  $('dl').innerHTML=list.filter(function(o){ return f==='all'||GRP[o.k]===f; }).map(function(o){ var n=E.daysBetween(t,o.d);
    var when = n===0?B.T('today'):(n===1?B.T('tomorrow'):B.T('in_days',{n:n})); var s=o.c!=='complete'?' *':''; if(s) star=true;
    return '<tr><td><b>'+B.esc(B.fmtDate(o.d))+s+'</b><br><small style="color:var(--ink-soft)">'+B.esc(when)+'</small></td><td>'+B.esc(B.T('k_'+o.k))+'</td><td>'+B.esc(o.k==='ib_final'?B.T('p_final',{y:o.p}):per(o.p))+'</td><td><a class="bz-btn2" style="padding:.3rem .7rem;font-size:.8rem" href="'+TOOL[o.k]+'">'+B.esc(B.T('open'))+'</a></td></tr>'; }).join('');
  $('dlw').innerHTML = star ? '<div class="bz-note">'+B.esc(B.T('w_cov'))+'</div>' : ''; }
B.seg('flt', draw); draw();
})();
"""
    faq = [("When is the BTW return due in Suriname?", "Every month, before the 16th of the following month, together with the payment."),
           ("When must wage tax be paid?", "The law (Wet Loonbelasting art. 20) allows until the 7th working day after the end of the month. The Belastingdienst portal, however, accepts the monthly return only from the 26th up to and including the 10th of the next month. This calendar therefore shows the earlier of the two dates."),
           ("When is the income tax return due?", "The provisional return by 15 April and the final return for the previous year by 30 April.")]
    return X.page("tax-deadlines.html", "biz-deadlines", "Tax & money", "Tax Deadlines Calendar",
                  "Every BTW, wage tax, AOV, APF and income tax deadline for the coming year, and a calendar that keeps itself up to date.",
                  body, js, strings, faq, rule_keys=("btw", "income_tax", "apf"),
                  related=("biz-btw", "biz-salary", "biz-ib", "biz-workdays"))


# ─────────────────────────────────────────────────────────────────────────────
# Pricing / markup with live bank rates
# ─────────────────────────────────────────────────────────────────────────────
def _rate_options(X):
    """Selling rates (SRD per 1 USD / EUR) from the existing bank and CBvS fetchers."""
    opts = []
    for b in X.bank_rates or []:
        try:
            opts.append({"id": b["key"], "name": b["name"], "usd": float(b["usd"][1]), "eur": float(b["eur"][1]),
                         "live": bool(b.get("live"))})
        except Exception:
            pass
    cb = {r.get("currency"): r for r in (X.cbvs_rates or [])}
    try:
        if "USD" in cb and "EUR" in cb:
            opts.append({"id": "cbvs", "name": "CBvS (weighted average)", "usd": float(cb["USD"]["sell"]),
                         "eur": float(cb["EUR"]["sell"]), "live": bool(X.cbvs_live)})
    except Exception:
        pass
    # sanity: drop anything implausible rather than show a wrong rate
    return [o for o in opts if 5 < o["usd"] < 500 and 5 < o["eur"] < 500]


def _page_pricing(X, feeds, prices):
    """pricing-calculator.html"""
    rates = _rate_options(X)
    upd = _esc(X.banks_updated or "")
    std = X.R["btw"][-1]["standard"]
    btw_opts = [(str(r), f"{r}%") for r in sorted(X.R["btw"][-1]["rates"], key=lambda r: (r != std, -r))]
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>From cost to selling price</h2>
    <div class="bz-grid bz-g2">
      {_field("cost", "Cost per item", "10", prefix="")}
      {_seg("cur", [("USD", "USD"), ("EUR", "EUR"), ("SRD", "SRD")], "USD", "Currency")}
    </div>
    <div class="bz-grid bz-g2" style="margin-top:.7rem" id="ratebox">
      {_select("src", "Exchange rate source", [(o["id"], o["name"]) for o in rates] + [("own", "My own rate")], rates[0]["id"] if rates else "own")}
      {_field("rate", "SRD per 1 unit", "", prefix="", hint="Selling rate. You can type your own.")}
    </div>
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_field("buf", "Exchange-rate buffer %", "3", prefix="", hint="Extra margin in case the rate rises before you restock")}
      {_field("extra", "Other costs per item (SRD)", "0", hint="Freight, duties, packaging")}
    </div>
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_seg("mode", [("markup", "Markup %"), ("margin", "Margin %")], "markup", "I think in")}
      {_field("pct", "Percentage", "30", prefix="")}
    </div>
    <div style="margin-top:.7rem">{_seg("btw", btw_opts + [("none", "No BTW")], str(std), "BTW on the selling price")}</div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Shelf price including BTW</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>{_share_bar()}</div>
    <div class="bz-card"><h2 style="font-size:1.05rem">If the exchange rate moves</h2><table class="bz-tbl"><tbody id="sens"></tbody></table>
      <p class="bz-src">Bank rates as published by the banks<span id="rupd"></span>.</p></div>
  </div>
</div>
<div class="bz-card">
  <h2>Compare unit prices</h2>
  <p class="text-sm text-gray-600 mb-3">Which pack is cheaper per kilo, litre or piece?</p>
  <div class="bz-scroll"><table class="bz-tbl" style="min-width:520px"><thead><tr><th>Price (SRD)</th><th>Pack size</th><th>Unit</th><th class="n">Per kg / l / piece</th></tr></thead><tbody id="up"></tbody></table></div>
</div>
<script id="bzRates" type="application/json">{_json.dumps(rates)}</script>
<span id="bzRatesUpd" hidden>{upd}</span>
"""
    strings = {"say": "Cost {c} becomes {e} excluding BTW and {i} including BTW. You earn {p} per item ({m}% margin, {k}% markup).",
               "r_cost": "Cost in SRD", "r_buf": "Cost with buffer and other costs", "r_excl": "Selling price excl. BTW",
               "r_btw": "BTW", "r_incl": "Shelf price incl. BTW", "r_profit": "Profit per item",
               "s_rate": "Rate {r}: shelf price {p}, profit {q}", "best": "cheapest",
               "margin_bad": "A margin must be below 100%."}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var RATES=JSON.parse($('bzRates').textContent);
var upd=$('bzRatesUpd').textContent; if(upd) $('rupd').textContent=' ('+upd+')';
function srcRate(){ var id=$('src').value, cur=B.segVal('cur'); for(var i=0;i<RATES.length;i++) if(RATES[i].id===id) return cur==='EUR'?RATES[i].eur:RATES[i].usd; return null; }
function fillRate(){ var r=srcRate(); if(r!==null) $('rate').value=E.fmtNum(r, B.L, 4); }
function run(){ var cur=B.segVal('cur'); $('ratebox').hidden = cur==='SRD';
  var c=B.amt('cost'), r= cur==='SRD'?1:B.num('rate'), buf=B.num('buf')||0, ex=B.amt('extra')||0, pct=B.num('pct')||0, mode=B.segVal('mode'), bt=B.segVal('btw');
  if(c===null||r===null){ $('big').textContent='–'; return; }
  if(mode==='margin' && pct>=100){ $('big').textContent='–'; $('say').textContent=B.T('margin_bad'); return; }
  var base=E.price({cost:c, rate:r, bufferPct:buf, mode:'markup', pct:0, btwPct:0});
  var costAll=base.cost+ex;
  var x=E.price({cost:costAll, rate:1, bufferPct:0, mode:mode, pct:pct, btwPct: bt==='none'?0:+bt});
  $('big').textContent=B.srd(x.incl);
  $('say').textContent=B.T('say',{c:B.srd(base.costSrd), e:B.srd(x.excl), i:B.srd(x.incl), p:B.srd(x.profit), m:E.fmtNum(x.marginPct,B.L,1), k:E.fmtNum(x.markupPct,B.L,1)});
  $('tbl').innerHTML=B.rows([[B.T('r_cost'), B.srd(base.costSrd)],[B.T('r_buf'), B.srd(costAll)],[B.T('r_excl'), B.srd(x.excl)],[B.T('r_btw'), B.srd(x.btw)],[B.T('r_incl'), B.srd(x.incl),'bz-tot'],[B.T('r_profit'), B.srd(x.profit),'bz-sub']]);
  if(cur!=='SRD'){ $('sens').innerHTML=[-5,5,10].map(function(d){ var rr=r*(1+d/100); var b2=E.price({cost:c, rate:rr, bufferPct:0, mode:'markup', pct:0, btwPct:0});
      var profit=x.excl-(b2.cost+ex); return '<tr><td>'+(d>0?'+':'')+d+'% &rarr; '+B.esc(E.fmtNum(rr,B.L,2))+'</td><td class="n">'+B.esc(B.srd(profit))+'</td></tr>'; }).join(''); } else $('sens').innerHTML='';
  B.shareText=function(){ return $('say').textContent; };
  B.saveUrl(['cost','cur','src','rate','buf','extra','mode','pct','btw']);
}
var had=B.loadUrl(['cost','cur','src','rate','buf','extra','mode','pct','btw']); if(!had || !$('rate').value) fillRate();
B.seg('cur', function(){ fillRate(); run(); }); B.seg('mode',run); B.seg('btw',run); B.on(['src'],'change',function(){ fillRate(); run(); });
B.on(['cost','rate','buf','extra','pct'],'input',run); run();
// unit prices
var UNITS=[['kg','kg',1],['g','g',0.001],['l','l',1],['ml','ml',0.001],['st','pcs',1]];
for(var i=0;i<4;i++){ var tr=document.createElement('tr'); tr.innerHTML='<td><input class="bz-in bz-num" inputmode="decimal" data-f="p"></td><td><input class="bz-in bz-num" inputmode="decimal" data-f="q"></td><td><select class="bz-sel" data-f="u">'+UNITS.map(function(u){ return '<option value="'+u[0]+'">'+u[1]+'</option>'; }).join('')+'</select></td><td class="n bz-num" data-f="r">–</td>'; $('up').appendChild(tr); }
function up(){ var best=null, rows=[].slice.call($('up').querySelectorAll('tr'));
  rows.forEach(function(tr){ var p=E.parseAmount(tr.querySelector('[data-f=p]').value), q=E.parseNum(tr.querySelector('[data-f=q]').value), u=tr.querySelector('[data-f=u]').value;
    var f=UNITS.filter(function(x){return x[0]===u;})[0][2]; tr._v=(p!==null&&q)? p/(q*f) : null; if(tr._v!==null && (best===null||tr._v<best)) best=tr._v; });
  rows.forEach(function(tr){ var c=tr.querySelector('[data-f=r]'); c.innerHTML = tr._v===null?'–':B.esc(B.srd(Math.round(tr._v)))+(tr._v===best&&rows.filter(function(r){return r._v!==null;}).length>1?' <span class="bz-tag">'+B.esc(B.T('best'))+'</span>':''); }); }
$('up').addEventListener('input',up); $('up').addEventListener('change',up);
})();
"""
    return X.page("pricing-calculator.html", "biz-pricing", "Pricing, import & finance", "Price & Markup Calculator",
                  "Work out the SRD shelf price from a dollar or euro cost with today's bank rates, your margin and BTW.",
                  body, js, strings, None, rule_keys=("btw",), related=("biz-import", "biz-btw", "biz-breakeven", "biz-prices"))


# ─────────────────────────────────────────────────────────────────────────────
# Government tenders & announcements (data/biz_feeds.json)
# ─────────────────────────────────────────────────────────────────────────────
def _page_tenders(X, feeds, prices):
    """government-tenders.html"""
    bek = feeds.get("bekendmakingen", [])
    tenders = [i for i in bek if i.get("tender")]
    body = f"""
<div class="bz-card">
  <h2>Government tenders</h2>
  <p class="text-sm text-gray-600 mb-3">Recognised from the title of each government announcement. Always read the official notice for the requirements and the closing date.</p>
  {_feed_list(tenders, 25)}
  {_feed_status(feeds, "bekendmakingen")}
</div>
<div class="bz-grid bz-g2">
  <div class="bz-card"><h2>All government announcements</h2>{_feed_list(bek, 25, tag_tenders=True)}
    <p class="bz-src" style="margin-top:.5rem">Source: <a href="https://gov.sr/bekendmaking/" target="_blank" rel="noopener">gov.sr bekendmakingen</a></p></div>
  <div class="bz-card"><h2>Belastingdienst notices</h2>{_feed_list(feeds.get("belastingdienst", []), 25)}
    {_feed_status(feeds, "belastingdienst")}
    <p class="bz-src">Source: <a href="https://belastingdienst.sr/nieuws/" target="_blank" rel="noopener">belastingdienst.sr</a>. Many notices are published as an image; open the notice to read it.</p></div>
</div>
"""
    faq = [("Where does this list come from?", "From the official announcements on gov.sr and the news of the Belastingdienst. We show the title, the date and a link to the official notice, and check for new items several times a day."),
           ("How do I take part in a government tender?", "Open the official notice. It explains how to get the tender documents, what to submit and the closing date and time.")]
    return X.page("government-tenders.html", "biz-tenders", "Live from the government", "Government Tenders & Announcements",
                  "New government tenders and announcements and the latest Belastingdienst notices, in one place.",
                  body, "", {}, faq, rule_keys=(), related=("biz-deadlines", "biz-prices", "biz-g-contacts"))


# ─────────────────────────────────────────────────────────────────────────────
# Maximum prices basic goods (data/max_prices.json)
# ─────────────────────────────────────────────────────────────────────────────
def _prices_view(prices):
    """data/max_prices.json -> what the pages show. Handles the current format
    (srdcheck + pdf, written by scripts/biz_feeds.py) and the old PDF-only one."""
    if "show" not in prices:  # old format
        return {"source": "pdf" if prices.get("rows") else "", "rows": prices.get("rows") or [],
                "valid_from": prices.get("valid_from", ""), "valid_to": prices.get("valid_to", ""),
                "pdf_url": prices.get("pdf_url", ""), "checked": prices.get("checked", ""), "changed": "", "fails": 0}
    src = prices.get("show", "")
    part = prices.get("srdcheck" if src == "srdcheck" else "pdf") or {}
    pdf = prices.get("pdf") or {}
    return {"source": src, "rows": part.get("rows") or [],
            "valid_from": pdf.get("valid_from", "") if src == "pdf" else "", "valid_to": pdf.get("valid_to", "") if src == "pdf" else "",
            "pdf_url": pdf.get("pdf_url", ""), "checked": part.get("checked", ""), "changed": part.get("changed", ""),
            "fails": int(part.get("fails", 0) or 0)}


SRDCHECK_URL = "https://ez.gov.sr/product/index"


def _page_prices(X, feeds, prices):
    """max-prices-basic-goods.html"""
    P = _prices_view(prices)
    rows = P["rows"]
    src_page = "https://gov.sr/ministeries/ministerie-van-economische-zaken-ondernemerschap-technologische-innovatie/richtprijzen-basis-en-strategische-goederen/"
    if rows:
        ck = P["checked"][:10]
        if P["source"] == "srdcheck":
            chg = (f'<br>Last change we saw: <span class="bz-date" data-d="{P["changed"]}" translate="no">{P["changed"]}</span>.' if P["changed"] else "")
            head = (f'<div class="bz-res"><div class="bz-k">Official prices, as published now</div>'
                    f'<div class="bz-big" style="font-size:1.5rem"><span translate="no">SRD Check</span></div>'
                    f'<div class="bz-say"><span translate="no">{len(rows)}</span> products, exactly as published by the Ministry of Economic Affairs (EZOTI) on its price portal. '
                    f'Checked on <span class="bz-date" data-d="{ck}" translate="no">{ck}</span>.{chg}</div></div>')
            exp_html = ('<div class="bz-note" id="expnote">The ministry&#39;s price portal could not be reached recently; these are the last prices we received.</div>'
                        if P["fails"] >= 3 else '<div id="expnote" hidden></div>')
        else:
            vf, vt = P["valid_from"], P["valid_to"]
            head = (f'<div class="bz-res"><div class="bz-k">Official list valid</div>'
                    f'<div class="bz-big" style="font-size:1.5rem"><span class="bz-date" data-d="{vf}">{vf}</span> &ndash; <span class="bz-date" data-d="{vt}">{vt}</span></div>'
                    f'<div class="bz-say"><span translate="no">{len(rows)}</span> products. Prices exactly as published by the Ministry of Economic Affairs (EZOTI).</div></div>')
            exp_html = ('<div class="bz-note" id="expnote">This list&#39;s period has ended and no newer list has been published yet. '
                        'It is the most recent official list; we check for a new one every few hours.</div>') if vt < X.today.isoformat() else '<div id="expnote" hidden></div>'
        trs = "".join(
            f'<tr data-s="{_esc((r["product"] + " " + r["importer"]).lower())}"><td translate="no"><b>{_esc(r["product"])}</b>'
            + (f'<br><small style="color:var(--ink-soft)">{_esc(r["importer"])}</small>' if r["importer"] else "")
            + f'</td><td translate="no">{_esc(r["retail_pack"])}</td><td class="n" translate="no"><b>{_esc(r["retail_price"])}</b></td>'
            f'<td translate="no">{_esc(r["wholesale_pack"])}</td><td class="n" translate="no">{_esc(r["wholesale_price"])}</td></tr>' for r in rows)
        table = (f'{_text("q", "Search product, brand or importer", "")}'
                 f'<p class="bz-src" id="cnt" style="margin:.5rem 0"></p>'
                 f'<div class="bz-scroll"><table class="bz-tbl" style="min-width:640px"><thead><tr><th>Product / importer</th><th>Retail unit</th>'
                 f'<th class="n">Max. consumer price</th><th>Wholesale unit</th><th class="n">Max. wholesale price</th></tr></thead>'
                 f'<tbody id="pt">{trs}</tbody></table></div>')
        pdf = (f'<a class="bz-btn2" href="{SRDCHECK_URL}" target="_blank" rel="noopener">SRD Check (EZOTI)</a>' if P["source"] == "srdcheck"
               else f'<a class="bz-btn2" href="{_esc(P["pdf_url"] or src_page)}" target="_blank" rel="noopener">Official PDF</a>')
    else:
        head, exp_html, table = "", "", '<div class="bz-note">The price list could not be read automatically right now. Please use the official source below.</div>'
        pdf = f'<a class="bz-btn2" href="{SRDCHECK_URL}" target="_blank" rel="noopener">SRD Check (EZOTI)</a>'
    body = f"""
{head}{exp_html}
<div class="bz-card">
  <h2>Price list</h2>
  {table}
  <div class="bz-acts">{pdf}<a class="bz-btn2" href="{src_page}" target="_blank" rel="noopener">Earlier PDF lists (gov.sr)</a></div>
  <p class="bz-src" style="margin-top:.7rem">Prices are copied word for word from the ministry; we do not recalculate them. If anything differs, the ministry&#39;s own publication is leading.
  Complaints about prices go to the Ministry of Economic Affairs via <a href="https://ez.gov.sr/" target="_blank" rel="noopener">ez.gov.sr</a>.</p>
</div>
"""
    strings = {"cnt": "{n} of {t} products shown"}
    js = r"""
(function(){ var B=BZ,$=B.$; [].forEach.call(document.querySelectorAll('.bz-date'), function(e){ e.textContent=B.fmtDate(e.getAttribute('data-d')); });
var pt=$('pt'); if(!pt) return; var rows=[].slice.call(pt.querySelectorAll('tr'));
function f(){ var q=($('q').value||'').toLowerCase().trim().split(/\s+/).filter(Boolean), n=0;
  rows.forEach(function(r){ var s=r.getAttribute('data-s'); var ok=q.every(function(w){ return s.indexOf(w)>=0; }); r.hidden=!ok; if(ok) n++; });
  $('cnt').textContent=B.T('cnt',{n:n, t:rows.length}); }
var ex=$('expnote'); if(ex && ex.hidden===false){ } $('q').addEventListener('input', f); f(); })();
"""
    faq = [("What are these maximum prices?", "The Ministry of Economic Affairs (EZOTI) publishes a list of basic goods every period with the maximum wholesale price and the maximum consumer price per brand and importer."),
           ("How often is the list updated?", "The ministry updates its prices regularly, usually every two weeks. We check the ministry's price portal SRD Check and its published lists several times a day and always show the newest official prices.")]
    return X.page("max-prices-basic-goods.html", "biz-prices", "Live from the government", "Maximum Prices of Basic Goods",
                  "The official maximum prices of basic goods in Suriname, searchable by product, brand and importer.",
                  body, js, strings, faq, rule_keys=(), related=("biz-pricing", "biz-tenders", "biz-import"))


# ─────────────────────────────────────────────────────────────────────────────
# Salary calculator (gross <-> net, employer cost)
# ─────────────────────────────────────────────────────────────────────────────
def _salary_inputs_html(X, prefix=""):
    """Shared 'more options' block for the salary calculator and the payslip maker."""
    apf = X.R["apf"][-1]
    p = prefix
    return f"""
<details class="bz-more"><summary>More options (overtime, allowances, pension, health insurance)</summary>
  <div class="bz-grid bz-g2" style="margin-top:.7rem">
    {_field(p+"ot", "Overtime pay this month (gross)", "0", hint="Taxed with the separate overtime table")}
    {_field(p+"ta", "Taxable allowances", "0", hint="For example a transport or function allowance")}
    {_field(p+"ua", "Tax-free allowances / reimbursements", "0", hint="Only what the law exempts, e.g. proven expense claims")}
    {_field(p+"ca", "Child allowance paid", "0", hint="Tax-free up to ⟦CHILD⟧ per child, max ⟦CHILD_MAX⟧")}
    {_field(p+"kids", "Number of children", "0", prefix="", mode="numeric")}
    {_field(p+"apf", "APF pension premium, total %", str(apf['pct_total']).replace('.', ','), prefix="",
            hint=f"Latest rate published by the pension fund: {str(apf['pct_total']).replace('.', ',')}% for {apf['published_for_year']}")}
    {_field(p+"apfer", "Employer's share of the pension premium %", "50", prefix="", hint="At least 50% by law")}
    {_field(p+"bzv", "Basic health insurance premium per month (BZV)", "0", hint="Your insurer's premium; employer pays at least half")}
    {_field(p+"bzver", "Employer's share of BZV %", "50", prefix="")}
  </div>
  {_check(p+"med", "Employer provides free or partly free medical care (taxed at 3% of wage, max SRD 200 a year)")}
  {_check(p+"a60", "Employee is 60 or older (no AOV premium)")}
  {_check(p+"nop", "No APF pension (e.g. not insured with the Algemeen Pensioenfonds)")}
</details>
"""


_SALARY_STRINGS = {
    "k_net": "Net pay per month", "k_gross": "Gross wage needed",
    "say_net": "Your employee receives {n}. You pay {c} in total, including your share of pension and FVO.",
    "say_gross": "For a net pay of {n} the gross wage is {g}. Total cost for the employer: {c}.",
    "r_gross": "Gross wage", "r_ot": "Overtime pay", "r_ta": "Taxable allowances", "r_ua": "Tax-free allowances", "r_ca": "Child allowance",
    "r_pens": "Pension premium APF ({p}% total, employee part)", "r_aov": "AOV premium ⟦AOV⟧", "r_tax": "Wage tax",
    "r_ottax": "Wage tax on overtime", "r_fvo": "FVO premium (⟦FVO_EE⟧)", "r_bzv": "Basic health insurance (employee part)", "r_net": "Net pay",
    "e_head": "Employer", "e_pens": "Pension premium (employer part)", "e_fvo": "FVO premium (employer part)", "e_bzv": "Basic health insurance (employer part)",
    "e_total": "Total cost for the employer",
    "h_loon": "Taxable wage (gross + taxable items − employee pension)", "h_forf": "Standard deduction ⟦FORF⟧ (max ⟦FORF_MAX⟧)",
    "h_zuiver": "Net wage for tax (zuiver loon)", "h_free": "Tax-free allowance per month", "h_taxable": "Taxed in the brackets",
    "h_med": "Medical care added to taxable wage", "h_base": "Pension base (min ⟦APF_MIN⟧, max ⟦APF_MAX⟧)",
    "n_ot": "Wage under ⟦FORF_CAP⟧ with overtime: the ⟦FORF⟧ standard deduction over overtime pay can shift a few dollars. Treat the result as an estimate.",
    "n_cap": "The pension premium is calculated over at most ⟦APF_MAX⟧ per month.",
    "n_min": "Below the minimum wage? Check the minimum wage page.",
    "n_apf": "The pension fund has not yet published a premium for this year. We use the latest published rate ({p}% for {y}); change it under More options when the new rate is known.",
}

_SALARY_JS = r"""
function bzSalaryInputs(p){ var B=BZ,$=B.$; p=p||'';
  var apf=B.num(p+'apf'), er=B.num(p+'apfer');
  return { overtime:B.amt(p+'ot')||0, taxableAllow:B.amt(p+'ta')||0, untaxedAllow:B.amt(p+'ua')||0, childAllow:B.amt(p+'ca')||0,
    children:Math.max(0,Math.floor(B.num(p+'kids')||0)), apfPct:(apf===null?null:apf), apfEmployerPct:(er===null?50:Math.max(50,Math.min(100,er))),
    bzv:B.amt(p+'bzv')||0, bzvEmployerPct:(B.num(p+'bzver')===null?50:B.num(p+'bzver')), medical:$(p+'med').checked, age60:$(p+'a60').checked, noPension:$(p+'nop').checked };
}
function bzSalaryRows(x){ var B=BZ; var r=[[B.T('r_gross'), B.srd(x.gross)]];
  if(x.overtime) r.push([B.T('r_ot'), B.srd(x.overtime)]); if(x.taxableAllow) r.push([B.T('r_ta'), B.srd(x.taxableAllow)]);
  if(x.untaxedAllow) r.push([B.T('r_ua'), B.srd(x.untaxedAllow)]); if(x.childAllow) r.push([B.T('r_ca'), B.srd(x.childAllow)]);
  if(x.pensionEmp) r.push([B.T('r_pens',{p:B.E.fmtNum(x.apfPct,B.L,2)}), '− '+B.srd(x.pensionEmp)]);
  r.push([B.T('r_aov'), '− '+B.srd(x.aov)]); r.push([B.T('r_tax'), '− '+B.srd(x.tax)]);
  if(x.overtimeTax) r.push([B.T('r_ottax'), '− '+B.srd(x.overtimeTax)]);
  r.push([B.T('r_fvo'), '− '+B.srd(x.fvoEmp)]); if(x.bzvEmp) r.push([B.T('r_bzv'), '− '+B.srd(x.bzvEmp)]);
  r.push([B.T('r_net'), B.srd(x.net), 'bz-tot']); return r; }
function bzEmployerRows(x){ var B=BZ; var r=[[B.T('r_gross'), B.srd(x.cashIn)]];
  if(x.pensionEr) r.push([B.T('e_pens'), '+ '+B.srd(x.pensionEr)]); r.push([B.T('e_fvo'), '+ '+B.srd(x.fvoEr)]);
  if(x.bzvEr) r.push([B.T('e_bzv'), '+ '+B.srd(x.bzvEr)]); r.push([B.T('e_total'), B.srd(x.employerCost), 'bz-tot']); return r; }
function bzHowRows(x){ var B=BZ, E=B.E, WT=E.pick(B.R.wage_tax, B.today()); var r=[];
  if(x.pensionBase) r.push([B.T('h_base'), B.srd(x.pensionBase)]);
  if(x.medical) r.push([B.T('h_med'), B.srd(x.medical)]);
  r.push([B.T('h_loon'), B.srd(x.loon)]); r.push([B.T('h_forf'), '− '+B.srd(x.forfait)]); r.push([B.T('h_zuiver'), B.srd(x.zuiver),'bz-tot']);
  r.push([B.T('h_free'), '− '+B.srd(WT.tax_free_month*100)]); r.push([B.T('h_taxable'), B.srd(x.taxable)]);
  var rest=x.taxable; WT.bands_month.forEach(function(b){ if(rest<=0) return; var w=b[0]===null?rest:Math.min(rest,b[0]*100); r.push([E.fmtNum(b[1],B.L)+'% × '+B.srd(w), B.srd(E.divRound(w*b[1]*100,10000)),'bz-sub']); rest-=w; });
  return r; }
function bzSalaryNotes(x){ var B=BZ, n=[];
  var apf=B.R.apf[B.R.apf.length-1]; var y=+B.today().slice(0,4);
  if(apf.published_for_year<y && !x.noPension && Math.abs(x.apfPct-apf.pct_total)<1e-9) n.push(['note', B.T('n_apf',{p:B.E.fmtNum(apf.pct_total,B.L), y:apf.published_for_year})]);
  if(x.flags.overtimeForfaitNote) n.push(['note', B.T('n_ot')]);
  if(x.flags.pensionCapped) n.push(['ok', B.T('n_cap')]);
  return n.map(function(v){ return '<div class="bz-'+v[0]+'">'+B.esc(v[1])+'</div>'; }).join(''); }
"""


def _page_salary(X, feeds, prices):
    """salary-calculator.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Monthly salary</h2>
    {_seg("dir", [("g2n", "I know the gross wage"), ("n2g", "I know the net pay I want")], "g2n")}
    <div style="margin-top:.8rem">{_field("amt", "Gross wage per month", "20.000", big=True)}</div>
    <div class="bz-chips"><button type="button" class="bz-chip" data-set="10616">Minimum wage (40 h)</button>
      <button type="button" class="bz-chip" data-set="15000">15.000</button><button type="button" class="bz-chip" data-set="25000">25.000</button>
      <button type="button" class="bz-chip" data-set="50000">50.000</button></div>
    {_salary_inputs_html(X)}
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k" id="rk">Net pay per month</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div id="notes"></div>
    <div class="bz-card"><h2 style="font-size:1.05rem">Employee</h2><table class="bz-tbl"><tbody id="emp"></tbody></table>
      <h2 style="font-size:1.05rem;margin-top:1rem">Employer</h2><table class="bz-tbl"><tbody id="er"></tbody></table>
      <details class="bz-how" style="margin-top:.8rem"><summary>How is this calculated?</summary><table class="bz-tbl"><tbody id="how"></tbody></table></details>
      {_share_bar('<a class="bz-btn2" href="payslip-generator.html">Make a payslip</a>')}
    </div>
  </div>
</div>
"""
    js = _SALARY_JS + r"""
(function(){ var B=BZ,E=B.E,$=B.$; var IDS=['dir','amt','ot','ta','ua','ca','kids','apf','apfer','bzv','bzver','med','a60','nop'];
function run(){ var dir=B.segVal('dir'); $('amt').previousElementSibling; var a=B.amt('amt'); var inp=bzSalaryInputs('');
  document.querySelector('label[for=amt]').textContent = B.T(dir==='n2g'?'lab_net':'lab_gross');
  if(a===null){ $('big').textContent='–'; $('emp').innerHTML=''; $('er').innerHTML=''; return; }
  var gross = dir==='n2g' ? E.grossForNet(a, inp, B.R, B.today()) : a;
  inp.gross=gross; var x=E.salary(inp, B.R, B.today());
  $('rk').textContent=B.T(dir==='n2g'?'k_gross':'k_net'); $('big').textContent=B.srd(dir==='n2g'?gross:x.net);
  $('say').textContent= dir==='n2g' ? B.T('say_gross',{n:B.srd(x.net), g:B.srd(gross), c:B.srd(x.employerCost)}) : B.T('say_net',{n:B.srd(x.net), c:B.srd(x.employerCost)});
  $('emp').innerHTML=B.rows(bzSalaryRows(x)); $('er').innerHTML=B.rows(bzEmployerRows(x)); $('how').innerHTML=B.rows(bzHowRows(x)); $('notes').innerHTML=bzSalaryNotes(x);
  B.shareText=function(){ return $('say').textContent; }; B.saveUrl(IDS);
}
B.loadUrl(IDS); B.seg('dir',run); B.on(IDS,'input',run); B.on(['med','a60','nop'],'change',run);
[].forEach.call(document.querySelectorAll('[data-set]'), function(c){ c.onclick=function(){ B.segSet('dir','g2n'); $('amt').value=B.fmtIn(+c.getAttribute('data-set')*100); run(); }; });
run(); })();
"""
    strings = dict(_SALARY_STRINGS)
    strings.update({"lab_gross": "Gross wage per month", "lab_net": "Net pay you want per month"})
    faq = [("How is wage tax calculated in Suriname?",
            "From the gross wage the employee's pension premium is deducted and then a standard deduction of ⟦FORF⟧ (max ⟦FORF_MAX⟧). "
            "The first ⟦LB_FREE⟧ a month is tax-free. Above that, ⟦LB_BANDS⟧."),
           ("What is AOV?", "The state old-age pension premium: ⟦AOV⟧ of the net wage for tax (zuiver loon), paid by employees under ⟦AOV_AGE⟧ and withheld with wage tax."),
           ("What does an employer pay on top of the gross wage?", "At least half of the APF pension premium, ⟦FVO_ER⟧ FVO (parental leave fund) and at least half of the basic health insurance premium."),
           ("Is this the same as tax.sr or Celery?", "We tested the same salaries in both: the wage tax, AOV, pension, FVO and net pay match to the cent. The only difference can be the pension rate the tool assumes; you can set it under More options.")]
    return X.page("salary-calculator.html", "biz-salary", "Staff & payroll", "Salary Calculator (Gross to Net)",
                  "Net pay, wage tax, AOV, pension and FVO, and what the employee really costs you. Calculated with the official rules.",
                  body, js, strings, faq,
                  rule_keys=("wage_tax", "overtime_tax", "tax_free", "aov", "apf", "apf_common", "fvo", "bzv_max_premium"),
                  related=("biz-payslip", "biz-minwage", "biz-vacation", "biz-g-staff"))


# ─────────────────────────────────────────────────────────────────────────────
# Income tax for self-employed
# ─────────────────────────────────────────────────────────────────────────────
def _page_ib(X, feeds, prices):
    """income-tax-calculator.html"""
    ib = X.R["income_tax"][-1]
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Your yearly profit</h2>
    {_field("p", "Taxable income for the year (profit after deductible costs)", "300.000", big=True)}
    {_check("a60", "I am 60 or older (no AOV premium)")}
    <p class="bz-note">This is for individuals, such as the owner of an eenmanszaak. Deductions (for example mortgage interest) and credits are not included: fill in the income after those.</p>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Set aside per month</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>
      <details class="bz-how"><summary>How is this calculated?</summary><table class="bz-tbl"><tbody id="how"></tbody></table></details>{_share_bar()}</div>
  </div>
</div>
<div class="bz-card"><h2>Dates</h2><table class="bz-tbl"><tbody id="dates"></tbody></table></div>
"""
    strings = {"say": "Income tax {t} and AOV {a} per year: {m} a month.", "r_tax": "Income tax", "r_aov": "AOV premium ⟦AOV⟧", "r_total": "Total per year",
               "r_inst": "Each of the 4 provisional instalments (income tax only)", "d_prov": "Provisional return", "d_final": "Final return for the previous year", "d_inst": "Provisional tax instalment",
               "h_band": "{p}% over {w}"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var IB=E.pick(B.R.income_tax,B.today());
function run(){ var p=B.amt('p'); if(p===null){ $('big').textContent='–'; return; } var x=E.incomeTax(p, $('a60').checked, B.R, B.today());
  $('big').textContent=B.srd(x.perMonth); $('say').textContent=B.T('say',{t:B.srd(x.tax), a:B.srd(x.aov), m:B.srd(x.perMonth)});
  $('tbl').innerHTML=B.rows([[B.T('r_tax'), B.srd(x.tax)],[B.T('r_aov'), B.srd(x.aov)],[B.T('r_total'), B.srd(x.total),'bz-tot'],[B.T('r_inst'), B.srd(x.perInstallment),'bz-sub']]);
  var rest=p, rows=[]; IB.bands_year.forEach(function(b){ if(rest<=0) return; var w=b[0]===null?rest:Math.min(rest,b[0]*100); rows.push([B.T('h_band',{p:b[1], w:B.srd(w)}), B.srd(E.divRound(w*b[1]*100,10000)),'bz-sub']); rest-=w; });
  $('how').innerHTML=B.rows(rows); B.shareText=function(){ return $('say').textContent; }; B.saveUrl(['p','a60']); }
var y=+B.today().slice(0,4), d=[]; [y,y+1].forEach(function(yy){ d.push([yy+'-'+IB.provisional_due,'d_prov']); d.push([yy+'-'+IB.final_due,'d_final']); IB.installments.forEach(function(i){ d.push([yy+'-'+i,'d_inst']); }); });
d=d.filter(function(x){ return x[0]>=B.today(); }).sort().slice(0,7);
$('dates').innerHTML=d.map(function(x){ return '<tr><td>'+B.esc(B.fmtDate(x[0]))+'</td><td>'+B.esc(B.T(x[1]))+'</td></tr>'; }).join('');
B.loadUrl(['p','a60']); B.on(['p'],'input',run); B.on(['a60'],'change',run); run(); })();
"""
    faq = [("What are the income tax rates for individuals in Suriname?", "⟦IB_TEXT⟧ (Wet Inkomstenbelasting art. 34)."),
           ("When do I file?", "The provisional return by 15 April and the final return for the previous year by 30 April. The provisional assessment is paid in four instalments: 15 April, 15 July, 15 October and 31 December.")]
    return X.page("income-tax-calculator.html", "biz-ib", "Tax & money", "Income Tax for Self-Employed",
                  "Estimate your income tax and AOV and how much to put aside every month.",
                  body, js, strings, faq, rule_keys=("income_tax", "aov"), related=("biz-deadlines", "biz-register", "biz-g-start"))


# ─────────────────────────────────────────────────────────────────────────────
# Documents: shared seller profile + PDF helpers (jsPDF, lazy-loaded)
# ─────────────────────────────────────────────────────────────────────────────
JSPDF = "/vendor/jspdf-2.5.2/jspdf.umd.min.js"

_SELLER_HTML = """
<details class="bz-more" id="sellerbox"><summary>Your business details (saved on this device)</summary>
  <div class="bz-grid bz-g2" style="margin-top:.7rem">
    %s %s %s %s %s %s %s
  </div>
  <div style="margin-top:.6rem"><label class="bz-label" for="s_logo">Logo (optional)</label><input id="s_logo" type="file" accept="image/png,image/jpeg" class="text-sm">
    <button type="button" class="bz-x" id="s_logo_x" hidden>&times;</button><div id="s_logo_prev" style="margin-top:.4rem"></div></div>
  %s
</details>
""" % (_text("s_name", "Business name"), _text("s_addr", "Address"), _text("s_kkf", "KKF number"),
       _text("s_fin", "FIN (tax number)"), _text("s_tel", "Phone / WhatsApp", mode="tel"), _text("s_mail", "E-mail", mode="email"),
       _text("s_bank", "Bank and account number", ta=True),
       _check("s_nobtw", "I am not registered for BTW (turnover up to ⟦BTW_THR⟧): no BTW on my documents"))

_DOCS_JS = r"""
var BZDOC = (function(){ var B=BZ,$=B.$;
  var F=['s_name','s_addr','s_kkf','s_fin','s_tel','s_mail','s_bank','s_nobtw'];
  function seller(){ var s={}; F.forEach(function(k){ var el=$(k); if(el) s[k]= el.type==='checkbox'?el.checked:el.value.trim(); }); s.logo=(B.store('seller')||{}).logo||''; return s; }
  function load(){ var s=B.store('seller')||{}; F.forEach(function(k){ var el=$(k); if(!el||s[k]===undefined) return; if(el.type==='checkbox') el.checked=!!s[k]; else el.value=s[k]; }); showLogo(s.logo);
    if(!s.s_name && $('sellerbox')) $('sellerbox').open=true; }
  function save(){ var s=seller(); B.store('seller', s); }
  function showLogo(d){ var p=$('s_logo_prev'); if(!p) return; p.innerHTML = d ? '<img src="'+d+'" alt="" style="max-height:60px">' : ''; if($('s_logo_x')) $('s_logo_x').hidden=!d; }
  function initLogo(onchange){ var f=$('s_logo'); if(!f) return;
    f.addEventListener('change', function(){ var file=f.files[0]; if(!file) return; var img=new Image(); var r=new FileReader();
      r.onload=function(){ img.onload=function(){ var c=document.createElement('canvas'), k=Math.min(1, 400/Math.max(img.width,img.height)); c.width=Math.round(img.width*k); c.height=Math.round(img.height*k);
        var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); x.drawImage(img,0,0,c.width,c.height);
        var d=c.toDataURL('image/jpeg',0.85); var s=B.store('seller')||{}; s.logo=d; B.store('seller',s); showLogo(d); if(onchange) onchange(); }; img.src=r.result; }; r.readAsDataURL(file); });
    $('s_logo_x').onclick=function(){ var s=B.store('seller')||{}; s.logo=''; B.store('seller',s); showLogo(''); f.value=''; if(onchange) onchange(); }; }
  function bind(onchange){ load(); F.forEach(function(k){ var el=$(k); if(el) el.addEventListener(el.type==='checkbox'?'change':'input', function(){ save(); if(onchange) onchange(); }); }); initLogo(onchange); }
  function pdfLib(){ return B.loadScript('/vendor/jspdf-2.5.2/jspdf.umd.min.js').then(function(){ return window.jspdf.jsPDF; }); }
  // plain PDF text: jsPDF standard fonts only know WinAnsi, so swap a few typographic characters
  function t(s){ return String(s===null||s===undefined?'':s).replace(/[−–—]/g,'-').replace(/[‘’]/g,"'").replace(/[“”]/g,'"').replace(/ | /g,' ').replace(/…/g,'...'); }
  function share(blob, name, text){ // phone: share the PDF itself (WhatsApp etc.); otherwise download
    try{ var file=new File([blob], name, {type:'application/pdf'}); if(navigator.canShare && navigator.canShare({files:[file]})){ return navigator.share({files:[file], text:text||''}).catch(function(){}); } }catch(e){}
    B.download(name, blob); }
  function next(kind){ var n=B.store('num_'+kind); return n ? n : null; }
  function bumpNumber(s){ var m=/^(.*?)(\d+)(\D*)$/.exec(s||''); if(!m) return s? s+'-2' : '1'; var d=String(+m[2]+1); while(d.length<m[2].length) d='0'+d; return m[1]+d+m[3]; }
  function backup(){ var o={}; try{ for(var i=0;i<localStorage.length;i++){ var k=localStorage.key(i); if(k.indexOf('bz.')===0) o[k]=localStorage.getItem(k); } }catch(e){}
    B.download('exploresuriname-backup-'+B.today()+'.json', new Blob([JSON.stringify(o)], {type:'application/json'})); }
  function restore(file, done){ var r=new FileReader(); r.onload=function(){ try{ var o=JSON.parse(r.result); Object.keys(o).forEach(function(k){ if(k.indexOf('bz.')===0) localStorage.setItem(k,o[k]); }); done(true); }catch(e){ done(false); } }; r.readAsText(file); }
  return {seller:seller, bind:bind, pdfLib:pdfLib, t:t, share:share, next:next, bumpNumber:bumpNumber, backup:backup, restore:restore};
})();
"""

_BACKUP_HTML = """
<div class="bz-card bz-noprint"><h2 style="font-size:1.05rem">Your data stays on this device</h2>
  <p class="text-sm text-gray-600">Business details, customers and numbers are stored only in this browser. Make a backup now and then, for example before you clear your browser or change phones.</p>
  <div class="bz-acts"><button type="button" class="bz-btn2" id="bk">Download backup</button>
    <label class="bz-btn2" style="cursor:pointer">Restore backup<input type="file" id="rs" accept="application/json" hidden></label></div></div>
"""
_BACKUP_JS = r"""
(function(){ var B=BZ,$=B.$; if(!$('bk')) return; $('bk').onclick=BZDOC.backup;
  $('rs').onchange=function(){ var f=$('rs').files[0]; if(!f) return; BZDOC.restore(f, function(ok){ B.toast(B.T(ok?'restored':'restore_bad')); if(ok) setTimeout(function(){ location.reload(); }, 800); }); }; })();
"""
_DOC_STRINGS = {"restored": "Backup restored", "restore_bad": "This file is not a valid backup", "pdf_fail": "The PDF could not be made. Check your connection once so the PDF tool can load, then try again."}


# ─────────────────────────────────────────────────────────────────────────────
# Invoice & quote generator
# ─────────────────────────────────────────────────────────────────────────────
def _page_invoice(X, feeds, prices):
    """invoice-generator.html"""
    rates = X.R["btw"][-1]["rates"]
    body = f"""
{_SELLER_HTML}
<div class="bz-grid bz-split" style="margin-top:1rem">
  <div>
    <div class="bz-card">
      {_seg("kind", [("inv", "Invoice"), ("quo", "Quote")], "inv", "Document")}
      <div class="bz-grid bz-g2" style="margin-top:.8rem">
        {_text("no", "Number")}
        {_select("cur", "Currency", [("SRD", "SRD"), ("USD", "USD"), ("EUR", "EUR")], "SRD")}
        <div><label class="bz-label" for="date">Date</label><input id="date" type="date" class="bz-in"></div>
        <div><label class="bz-label" for="deliv" id="delivlab">Delivery date of goods / services</label><input id="deliv" type="date" class="bz-in"></div>
        {_field("term", "Payment term (days)", "14", prefix="", mode="numeric")}
        <div id="ratebox">{_field("fx", "Exchange rate used (SRD per unit)", "", prefix="", hint="Printed on the document for foreign-currency invoices")}</div>
      </div>
    </div>
    <div class="bz-card">
      <h2>Customer</h2>
      <div class="bz-grid bz-g2">
        {_text("c_name", "Name")} {_text("c_addr", "Address")} {_text("c_fin", "Customer FIN (tax number)", hint="Required on BTW invoices to businesses")}
        {_text("c_ref", "Their reference / PO (optional)")}
      </div>
      <div class="bz-acts"><button type="button" class="bz-btn2" id="savecust">Save customer</button><select id="custs" class="bz-sel" style="max-width:16rem"><option value="">Saved customers</option></select></div>
    </div>
    <div class="bz-card">
      <h2>Lines</h2>
      <div class="bz-scroll"><table class="bz-tbl" style="min-width:600px"><thead><tr><th>Description</th><th>Qty</th><th>Unit price (excl. BTW)</th><th>BTW</th><th class="n">Amount</th><th></th></tr></thead><tbody id="lines"></tbody></table></div>
      <div class="bz-acts"><button type="button" class="bz-btn2" id="addline">+ Add line</button></div>
      {_text("notes", "Note on the document (optional)", ta=True)}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k" id="rk">Invoice total</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tot"></tbody></table>
      <div class="bz-acts bz-noprint"><button type="button" class="bz-btn" id="pdf">Download PDF</button><button type="button" class="bz-btn2" id="sharepdf">Share PDF</button>
        <button type="button" class="bz-btn2" id="new">New document</button></div></div>
    <div class="bz-card"><h2 style="font-size:1.05rem">BTW law checklist</h2><ul id="chk" style="padding:0;margin:0"></ul>
      <p class="bz-src" style="margin-top:.5rem">Wet BTW art. 28: the fields an invoice must contain. Quotes are not bound to this list.</p></div>
    <div class="bz-card"><h2 style="font-size:1.05rem">Recent documents</h2><ul id="hist" class="bz-feed" style="padding:0;margin:0"></ul></div>
  </div>
</div>
{_BACKUP_HTML}
"""
    strings = dict(_DOC_STRINGS)
    strings.update({
        "k_inv": "Invoice total", "k_quo": "Quote total", "t_inv": "INVOICE", "t_quo": "QUOTE",
        "say": "{n} lines, of which {b} BTW.", "sub": "Subtotal excl. BTW", "btw_r": "BTW {r}% over {e}", "total": "Total",
        "exempt_note": "No BTW charged: small business, turnover up to ⟦BTW_THR⟧ (Wet BTW art. 21).",
        "c_date": "Date of the invoice", "c_no": "Sequential invoice number", "c_sfin": "Your FIN (tax number)", "c_bfin": "Customer's FIN (for business customers)",
        "c_names": "Names and addresses of you and the customer", "c_desc": "Description and quantity of goods or services", "c_deliv": "Date of delivery or service",
        "c_excl": "Price per BTW rate excluding BTW", "c_rate": "BTW rate and BTW amount per rate",
        "p_from": "From", "p_to": "To", "p_no": "Number", "p_date": "Date", "p_deliv": "Delivery date", "p_due": "Due date", "p_valid": "Valid until",
        "p_desc": "Description", "p_qty": "Qty", "p_price": "Unit price", "p_btw": "BTW", "p_amt": "Amount", "p_ref": "Your reference",
        "p_kkf": "KKF", "p_fin": "FIN", "p_pay": "Payment details", "p_fx": "Exchange rate used: 1 {c} = SRD {r}",
        "p_ex": "exempt", "p_page": "Made with exploresuriname.com/invoice-generator",
        "saved_c": "Customer saved", "new_q": "Start a new document? Unsaved changes are kept in your history.", "line_def": "Description",
        "h_open": "open"})
    js = _DOCS_JS + r"""
(function(){ var B=BZ,E=B.E,$=B.$; var RATES=%RATES%; var STD=B.R.btw[B.R.btw.length-1].standard;
var cur = B.store('inv_draft');
function lineRow(l){ var tr=document.createElement('tr'); l=l||{d:'',q:'1',p:'',r:String(STD)};
  var opts=RATES.map(function(r){ return '<option value="'+r+'"'+(String(r)===String(l.r)?' selected':'')+'>'+r+'%</option>'; }).join('')+'<option value="ex"'+(l.r==='ex'?' selected':'')+'>'+B.esc(B.T('p_ex'))+'</option>';
  tr.innerHTML='<td><input class="bz-in" data-f="d" value="'+B.esc(l.d)+'"></td><td><input class="bz-in bz-num" data-f="q" inputmode="decimal" style="max-width:5rem" value="'+B.esc(l.q)+'"></td>'+
    '<td><input class="bz-in bz-num" data-f="p" inputmode="decimal" value="'+B.esc(l.p)+'"></td><td><select class="bz-sel" data-f="r">'+opts+'</select></td><td class="n bz-num" data-f="a">–</td><td><button type="button" class="bz-x">&times;</button></td>';
  tr.querySelector('.bz-x').onclick=function(){ tr.remove(); run(); }; $('lines').appendChild(tr); }
function state(){ var L=[]; [].forEach.call($('lines').querySelectorAll('tr'), function(tr){ L.push({d:tr.querySelector('[data-f=d]').value, q:tr.querySelector('[data-f=q]').value, p:tr.querySelector('[data-f=p]').value, r:tr.querySelector('[data-f=r]').value}); });
  return {kind:B.segVal('kind'), no:$('no').value, cur:$('cur').value, date:$('date').value, deliv:$('deliv').value, term:$('term').value, fx:$('fx').value,
    c_name:$('c_name').value, c_addr:$('c_addr').value, c_fin:$('c_fin').value, c_ref:$('c_ref').value, notes:$('notes').value, lines:L}; }
function apply(s){ B.segSet('kind', s.kind||'inv'); ['no','cur','date','deliv','term','fx','c_name','c_addr','c_fin','c_ref','notes'].forEach(function(k){ if(s[k]!==undefined) $(k).value=s[k]; });
  $('lines').innerHTML=''; (s.lines&&s.lines.length?s.lines:[null]).forEach(lineRow); }
function calc(s){ var nob=BZDOC.seller().s_nobtw; var lines=[], groups={}, order=[];
  s.lines.forEach(function(l){ var p=E.parseAmount(l.p), q=E.parseNum(l.q); if(p===null) return; if(q===null) q=1; var a=Math.round(p*q);
    var r = nob ? 'ex' : l.r; lines.push({d:l.d, q:q, p:p, r:r, a:a}); if(!(r in groups)){ groups[r]=0; order.push(r); } groups[r]+=a; });
  var sub=0, btw=0, g=[]; order.sort(function(a,b){ return (b==='ex'?-1:+b)-(a==='ex'?-1:+a); }).forEach(function(r){ var e=groups[r], bt= r==='ex'?0:E.pctOf(e,+r); g.push({r:r,e:e,b:bt}); sub+=e; btw+=bt; });
  return {lines:lines, groups:g, sub:sub, btw:btw, total:sub+btw, nob:nob}; }
function fmtC(c, cur){ return cur+' '+E.fmt(c, B.L); }
function run(){ var s=state(), c=calc(s), cu=s.cur; $('ratebox').hidden = cu==='SRD';
  [].forEach.call($('lines').querySelectorAll('tr'), function(tr){ var p=E.parseAmount(tr.querySelector('[data-f=p]').value), q=E.parseNum(tr.querySelector('[data-f=q]').value);
    tr.querySelector('[data-f=a]').textContent = p===null?'–':E.fmt(Math.round(p*(q===null?1:q)), B.L); tr.querySelector('[data-f=r]').disabled=!!c.nob; });
  $('rk').textContent=B.T(s.kind==='quo'?'k_quo':'k_inv'); $('big').textContent=fmtC(c.total, cu); $('say').textContent=B.T('say',{n:c.lines.length, b:fmtC(c.btw,cu)});
  var rows=[[B.T('sub'), fmtC(c.sub,cu)]]; c.groups.forEach(function(g){ if(g.r!=='ex') rows.push([B.T('btw_r',{r:g.r, e:fmtC(g.e,cu)}), fmtC(g.b,cu),'bz-sub']); });
  rows.push([B.T('total'), fmtC(c.total,cu),'bz-tot']); $('tot').innerHTML=B.rows(rows);
  var sl=BZDOC.seller(); var ck=[['c_date', !!s.date],['c_no', !!s.no.trim()],['c_sfin', !!sl.s_fin],['c_bfin', !!s.c_fin.trim()],['c_names', !!(sl.s_name&&sl.s_addr&&s.c_name.trim()&&s.c_addr.trim())],
    ['c_desc', c.lines.length>0 && c.lines.every(function(l){ return l.d.trim(); })],['c_deliv', !!s.deliv],['c_excl', c.lines.length>0],['c_rate', c.lines.length>0]];
  $('chk').innerHTML = ck.map(function(k){ return '<li style="list-style:none;padding:.25rem 0">'+(k[1]?'<b style="color:var(--forest2)">&#10003;</b> ':'<b style="color:#C2410C">&#9675;</b> ')+B.esc(B.T(k[0]))+'</li>'; }).join('');
  B.store('inv_draft', s); B.shareText=function(){ return (s.kind==='quo'?B.T('t_quo'):B.T('t_inv'))+' '+s.no+': '+fmtC(c.total,cu); };
}
function due(s){ var n=parseInt(s.term,10); return (s.date && !isNaN(n)) ? E.addDays(s.date, n) : ''; }
function makePdf(){ var s=state(), c=calc(s), sl=BZDOC.seller(), cu=s.cur, t=BZDOC.t;
  return BZDOC.pdfLib().then(function(jsPDF){ var d=new jsPDF({unit:'mm', format:'a4'}); var y=18, W=210, M=16;
    if(sl.logo){ try{ d.addImage(sl.logo,'JPEG',M,y-4,28,0); }catch(e){} }
    d.setFont('helvetica','bold'); d.setFontSize(20); d.text(t(s.kind==='quo'?B.T('t_quo'):B.T('t_inv')), W-M, y+2, {align:'right'});
    d.setFontSize(10); d.setFont('helvetica','normal');
    var meta=[[B.T('p_no'), s.no],[B.T('p_date'), s.date?B.fmtDay(s.date):'']];
    if(s.kind==='inv'){ meta.push([B.T('p_deliv'), s.deliv?B.fmtDay(s.deliv):'']); if(due(s)) meta.push([B.T('p_due'), B.fmtDay(due(s))]); }
    else if(due(s)) meta.push([B.T('p_valid'), B.fmtDay(due(s))]);
    if(s.c_ref) meta.push([B.T('p_ref'), s.c_ref]);
    var my=y+10; meta.forEach(function(m){ d.setTextColor(110); d.text(t(m[0]), W-M-75, my); d.setTextColor(20); d.text(t(m[1]), W-M, my, {align:'right'}); my+=5.5; });
    y=Math.max(y+34, my+6);
    d.setFont('helvetica','bold'); d.text(t(B.T('p_from')), M, y); d.text(t(B.T('p_to')), 110, y); d.setFont('helvetica','normal'); y+=5;
    var from=[sl.s_name, sl.s_addr, sl.s_kkf?B.T('p_kkf')+' '+sl.s_kkf:'', sl.s_fin?B.T('p_fin')+' '+sl.s_fin:'', sl.s_tel, sl.s_mail].filter(Boolean);
    var to=[s.c_name, s.c_addr, s.c_fin?B.T('p_fin')+' '+s.c_fin:''].filter(Boolean);
    var y0=y; from.forEach(function(l){ d.splitTextToSize(t(l), 85).forEach(function(x){ d.text(x, M, y); y+=5; }); }); var y1=y; y=y0;
    to.forEach(function(l){ d.splitTextToSize(t(l), 85).forEach(function(x){ d.text(x, 110, y); y+=5; }); }); y=Math.max(y, y1)+6;
    // table
    var cols=[M, 112, 128, 158, W-M]; d.setFillColor(27,67,50); d.rect(M, y-4.5, W-2*M, 7, 'F'); d.setTextColor(255); d.setFont('helvetica','bold');
    d.text(t(B.T('p_desc')), M+2, y); d.text(t(B.T('p_qty')), cols[2]-2, y, {align:'right'}); d.text(t(B.T('p_price')), cols[3]-2, y, {align:'right'});
    d.text(t(B.T('p_btw')), cols[3]+10, y, {align:'right'}); d.text(t(B.T('p_amt')), W-M-2, y, {align:'right'}); d.setTextColor(20); d.setFont('helvetica','normal'); y+=7;
    c.lines.forEach(function(l){ var desc=d.splitTextToSize(t(l.d), 92); if(y+desc.length*5>270){ d.addPage(); y=20; }
      d.text(desc, M+2, y); d.text(E.fmtNum(l.q,B.L,3), cols[2]-2, y, {align:'right'}); d.text(t(E.fmt(l.p,B.L)), cols[3]-2, y, {align:'right'});
      d.text(t(l.r==='ex'?B.T('p_ex'):l.r+'%'), cols[3]+10, y, {align:'right'}); d.text(t(E.fmt(l.a,B.L)), W-M-2, y, {align:'right'});
      y+=desc.length*5+2; d.setDrawColor(225); d.line(M, y-3.5, W-M, y-3.5); });
    y+=3; if(y>240){ d.addPage(); y=20; }
    function tl(a,b,bold){ d.setFont('helvetica', bold?'bold':'normal'); d.text(t(a), W-M-60, y, {align:'right'}); d.text(t(b), W-M-2, y, {align:'right'}); y+=6; }
    tl(B.T('sub'), fmtC(c.sub,cu)); c.groups.forEach(function(g){ if(g.r!=='ex') tl(B.T('btw_r',{r:g.r, e:fmtC(g.e,cu)}), fmtC(g.b,cu)); });
    d.setDrawColor(20); d.line(W-M-90, y-4, W-M, y-4); tl(B.T('total'), fmtC(c.total,cu), true); d.setFont('helvetica','normal');
    y+=4; var notes=[]; if(c.nob) notes.push(B.T('exempt_note')); if(cu!=='SRD' && s.fx) notes.push(B.T('p_fx',{c:cu, r:s.fx})); if(s.notes) notes.push(s.notes);
    if(sl.s_bank && s.kind==='inv'){ d.setFont('helvetica','bold'); d.text(t(B.T('p_pay')), M, y); d.setFont('helvetica','normal'); y+=5; d.splitTextToSize(t(sl.s_bank), 170).forEach(function(x){ d.text(x, M, y); y+=5; }); y+=2; }
    notes.forEach(function(n){ d.splitTextToSize(t(n), 178).forEach(function(x){ if(y>285){ d.addPage(); y=20; } d.text(x, M, y); y+=5; }); });
    d.setFontSize(7.5); d.setTextColor(150); d.text(t(B.T('p_page')), W/2, 292, {align:'center'});
    hist(s, c); return d.output('blob'); }); }
function hist(s, c){ var h=B.store('inv_hist')||[]; h=h.filter(function(x){ return !(x.no===s.no && x.kind===s.kind); }); h.unshift({no:s.no, kind:s.kind, name:s.c_name, total:fmtC(c.total,s.cur), date:s.date, s:s}); B.store('inv_hist', h.slice(0,50)); drawHist(); }
function drawHist(){ var h=B.store('inv_hist')||[]; $('hist').innerHTML = h.length ? h.slice(0,10).map(function(x,i){ return '<li><a href="#" data-i="'+i+'">'+B.esc((x.kind==='quo'?B.T('t_quo'):B.T('t_inv'))+' '+x.no+' · '+(x.name||''))+'</a><small>'+B.esc(x.total+' · '+(x.date||''))+'</small></li>'; }).join('') : '';
  [].forEach.call($('hist').querySelectorAll('a'), function(a){ a.onclick=function(ev){ ev.preventDefault(); apply(h[+a.getAttribute('data-i')].s); run(); window.scrollTo(0,0); }; }); }
function fileName(){ var s=state(); return (s.kind==='quo'?'offerte-':'factuur-')+(s.no||'document').replace(/[^\w\-]+/g,'_')+'.pdf'; }
$('pdf').onclick=function(){ makePdf().then(function(b){ B.download(fileName(), b); nextNo(); }, function(){ B.toast(B.T('pdf_fail')); }); };
$('sharepdf').onclick=function(){ makePdf().then(function(b){ BZDOC.share(b, fileName(), B.shareText()); nextNo(); }, function(){ B.toast(B.T('pdf_fail')); }); };
function nextNo(){ var s=state(); B.store('num_'+s.kind, BZDOC.bumpNumber(s.no)); }
$('new').onclick=function(){ var s=state(); var n=B.store('num_'+s.kind) || BZDOC.bumpNumber(s.no);
  apply({kind:s.kind, no:n, cur:s.cur, date:B.today(), deliv:B.today(), term:s.term, lines:[]}); ['c_name','c_addr','c_fin','c_ref','notes'].forEach(function(k){ $(k).value=''; }); run(); };
// customers
function drawCust(){ var cs=B.store('customers')||[]; $('custs').innerHTML='<option value="">'+B.esc($('custs').options[0].text)+'</option>'+cs.map(function(c,i){ return '<option value="'+i+'">'+B.esc(c.c_name)+'</option>'; }).join(''); }
$('savecust').onclick=function(){ var s=state(); if(!s.c_name.trim()) return; var cs=(B.store('customers')||[]).filter(function(c){ return c.c_name!==s.c_name; }); cs.unshift({c_name:s.c_name, c_addr:s.c_addr, c_fin:s.c_fin}); B.store('customers', cs.slice(0,200)); drawCust(); B.toast(B.T('saved_c')); };
$('custs').onchange=function(){ var cs=B.store('customers')||[]; var c=cs[+$('custs').value]; if(!c) return; ['c_name','c_addr','c_fin'].forEach(function(k){ $(k).value=c[k]||''; }); run(); };
$('addline').onclick=function(){ lineRow(null); };
BZDOC.bind(run);
if(cur) apply(cur); else apply({kind:'inv', no:(B.store('num_inv')||(new Date().getFullYear()+'-001')), cur:'SRD', date:B.today(), deliv:B.today(), term:'14', lines:[{d:B.T('line_def'), q:'1', p:'', r:String(STD)}]});
B.seg('kind', function(v){ var s=state(); if(!s.no || s.no===B.store('num_'+(v==='inv'?'quo':'inv'))) $('no').value = B.store('num_'+v) || (new Date().getFullYear()+(v==='quo'?'-Q001':'-001')); $('delivlab').parentElement.hidden = v==='quo'; run(); });
document.addEventListener('input', function(ev){ if(ev.target.closest('.bz-wrap')) run(); }); document.addEventListener('change', function(ev){ if(ev.target.closest('.bz-wrap')) run(); });
drawCust(); drawHist(); run();
})();
""".replace("%RATES%", _json.dumps(sorted(rates, reverse=True))) + _BACKUP_JS
    faq = [("What must be on an invoice in Suriname?",
            "Under Wet BTW art. 28: the date and a sequential number, the tax numbers (FIN) of the supplier and the customer, both names and addresses, "
            "the quantity and description of the goods or services, the delivery date, the price per BTW rate excluding BTW, the rate and the BTW amount, and a note when an exemption applies."),
           ("I am not registered for BTW. What do I put on my invoice?",
            "Tick 'I am not registered for BTW' in your business details. The invoice then shows no BTW and a note that you are a small business with turnover up to ⟦BTW_THR⟧."),
           ("Where are my invoices stored?",
            "Only in your own browser on this device. Nothing is sent to us. Use 'Download backup' to keep a copy.")]
    return X.page("invoice-generator.html", "biz-invoice", "Invoices & paperwork", "Invoice & Quote Generator",
                  "Make invoices and quotes with every field the BTW law asks for, as a PDF you can send by WhatsApp. Free, no account.",
                  body, js, strings, faq, rule_keys=("btw",), related=("biz-receipt", "biz-reminder", "biz-register", "biz-btw"))


# ─────────────────────────────────────────────────────────────────────────────
# Receipt: kwitantie + kassabon
# ─────────────────────────────────────────────────────────────────────────────
def _page_receipt(X, feeds, prices):
    """receipt-generator.html"""
    rates = sorted(X.R["btw"][-1]["rates"], reverse=True)
    body = f"""
{_SELLER_HTML}
<div class="bz-card" style="margin-top:1rem">
  {_seg("kind", [("kw", "Kwitantie (payment receipt)"), ("kb", "Kassabon (itemised receipt)")], "kw", "Type")}
  <div class="bz-grid bz-g3" style="margin-top:.8rem">
    {_text("no", "Number")}
    <div><label class="bz-label" for="date">Date</label><input id="date" type="date" class="bz-in"></div>
    {_select("cur", "Currency", [("SRD", "SRD"), ("USD", "USD"), ("EUR", "EUR")], "SRD")}
  </div>
</div>
<div class="bz-grid bz-split">
  <div>
    <div class="bz-card" id="kwbox">
      <h2>Kwitantie</h2>
      <div class="bz-grid bz-g2">
        {_text("from", "Received from")}
        {_field("amt", "Amount", "", prefix="", money=True)}
      </div>
      {_text("for", "For (description)", ta=True)}
      <div class="bz-grid bz-g2" style="margin-top:.6rem">
        {_select("meth", "Paid by", [("cash", "Cash"), ("bank", "Bank transfer"), ("card", "Card"), ("mobile", "Mobile payment"), ("cheque", "Cheque")], "cash")}
        {_select("wl", "Amount in words in", [("nl", "Dutch"), ("en", "English")], "nl")}
        {_text("place", "Place", "Paramaribo")}
      </div>
    </div>
    <div class="bz-card" id="kbbox" hidden>
      <h2>Kassabon</h2>
      <div class="bz-scroll"><table class="bz-tbl" style="min-width:520px"><thead><tr><th>Item</th><th>Qty</th><th>Price incl. BTW</th><th>BTW</th><th></th></tr></thead><tbody id="lines"></tbody></table></div>
      <div class="bz-acts"><button type="button" class="bz-btn2" id="addline">+ Add item</button></div>
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Total</div><div class="bz-big" id="big">–</div><div class="bz-say" id="words"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tot"></tbody></table>
      <div class="bz-grid bz-g2" style="margin-top:.8rem">{_select("fmt", "PDF format", [("a5", "A5 sheet"), ("80", "Receipt printer (80 mm)"), ("58", "Receipt printer (58 mm)")], "a5")}</div>
      <div class="bz-acts bz-noprint"><button type="button" class="bz-btn" id="pdf">Download PDF</button><button type="button" class="bz-btn2" id="sharepdf">Share PDF</button><button type="button" class="bz-btn2" id="new">Next number</button></div></div>
  </div>
</div>
{_BACKUP_HTML}
"""
    strings = dict(_DOC_STRINGS)
    strings.update({"t_kw": "RECEIPT", "p_no": "No.", "p_date": "Date", "p_from": "Received from", "p_sum": "The sum of",
                    "p_for": "For", "p_meth": "Paid by", "p_sign": "Signature", "excl": "Total excl. BTW", "btw_r": "BTW {r}%",
                    "incl": "Total incl. BTW", "p_fin": "FIN", "p_kkf": "KKF", "exempt_note": "No BTW charged: small business, turnover up to ⟦BTW_THR⟧ (Wet BTW art. 21).",
                    "m_cash": "Cash", "m_bank": "Bank transfer", "m_card": "Card", "m_mobile": "Mobile payment", "m_cheque": "Cheque", "p_ex": "exempt"})
    js = _DOCS_JS + r"""
(function(){ var B=BZ,E=B.E,$=B.$; var RATES=%RATES%; var STD=B.R.btw[B.R.btw.length-1].standard;
function lineRow(l){ var tr=document.createElement('tr'); l=l||{d:'',q:'1',p:'',r:String(STD)};
  tr.innerHTML='<td><input class="bz-in" data-f="d" value="'+B.esc(l.d)+'"></td><td><input class="bz-in bz-num" data-f="q" inputmode="decimal" style="max-width:5rem" value="'+B.esc(l.q)+'"></td><td><input class="bz-in bz-num" data-f="p" inputmode="decimal" value="'+B.esc(l.p)+'"></td>'+
    '<td><select class="bz-sel" data-f="r">'+RATES.map(function(r){ return '<option value="'+r+'"'+(String(r)===String(l.r)?' selected':'')+'>'+r+'%</option>'; }).join('')+'<option value="ex">'+B.esc(B.T('p_ex'))+'</option></select></td><td><button type="button" class="bz-x">&times;</button></td>';
  tr.querySelector('.bz-x').onclick=function(){ tr.remove(); run(); }; $('lines').appendChild(tr); }
function kb(){ var nob=BZDOC.seller().s_nobtw, L=[], g={}, order=[];
  [].forEach.call($('lines').querySelectorAll('tr'), function(tr){ var p=E.parseAmount(tr.querySelector('[data-f=p]').value), q=E.parseNum(tr.querySelector('[data-f=q]').value); if(p===null) return; if(q===null) q=1;
    var a=Math.round(p*q), r=nob?'ex':tr.querySelector('[data-f=r]').value; L.push({d:tr.querySelector('[data-f=d]').value, q:q, p:p, a:a, r:r}); if(!(r in g)){ g[r]=0; order.push(r); } g[r]+=a; });
  var incl=0, excl=0, grp=[]; order.forEach(function(r){ var i=g[r], e= r==='ex'? i : E.btwFromIncl(i,+r).excl; grp.push({r:r, i:i, e:e, b:i-e}); incl+=i; excl+=e; });
  return {lines:L, groups:grp, incl:incl, excl:excl, nob:nob}; }
function run(){ var k=B.segVal('kind'), cu=$('cur').value; $('kwbox').hidden=k!=='kw'; $('kbbox').hidden=k!=='kb';
  if(k==='kw'){ var a=B.amt('amt'); $('big').textContent= a===null?'–':cu+' '+E.fmt(a,B.L); $('words').textContent= a===null?'':E.amountInWords(a, $('wl').value, cu); $('tot').innerHTML=''; }
  else { var x=kb(); $('big').textContent=cu+' '+E.fmt(x.incl,B.L); $('words').textContent=E.amountInWords(x.incl, B.L==='en'?'en':'nl', cu);
    var rows=[[B.T('excl'), cu+' '+E.fmt(x.excl,B.L)]]; x.groups.forEach(function(g){ if(g.r!=='ex') rows.push([B.T('btw_r',{r:g.r}), cu+' '+E.fmt(g.b,B.L),'bz-sub']); }); rows.push([B.T('incl'), cu+' '+E.fmt(x.incl,B.L),'bz-tot']); $('tot').innerHTML=B.rows(rows); }
  B.store('rcpt_draft', {kind:k, no:$('no').value, cur:cu, from:$('from').value, amt:$('amt').value, 'for':$('for').value, meth:$('meth').value, wl:$('wl').value, place:$('place').value});
  B.shareText=function(){ return $('big').textContent+' – '+$('words').textContent; };
}
function pdf(){ var k=B.segVal('kind'), f=$('fmt').value, sl=BZDOC.seller(), t=BZDOC.t, cu=$('cur').value, no=$('no').value, dt=$('date').value;
  if(k==='kw' && B.amt('amt')===null) return Promise.reject(new Error('amount'));
  return BZDOC.pdfLib().then(function(jsPDF){ var d;
    if(k==='kw' && f==='a5'){ var a=B.amt('amt'); d=new jsPDF({unit:'mm', format:'a5', orientation:'landscape'}); var W=210, M=14, y=16;
        d.setFont('helvetica','bold'); d.setFontSize(18); d.text(t(B.T('t_kw')), M, y); d.setFontSize(11); d.text(t(B.T('p_no')+' '+no), W-M, y, {align:'right'});
        d.setFont('helvetica','normal'); d.setFontSize(9); y+=6; [sl.s_name, sl.s_addr, [sl.s_kkf?B.T('p_kkf')+' '+sl.s_kkf:'', sl.s_fin?B.T('p_fin')+' '+sl.s_fin:''].filter(Boolean).join('  -  ')].filter(Boolean).forEach(function(l){ d.text(t(l), M, y); y+=4.5; });
        y+=6; d.setFontSize(11);
        function row(lab, val){ d.setTextColor(110); d.text(t(lab), M, y); d.setTextColor(20); var v=d.splitTextToSize(t(val), 140); d.text(v, M+42, y); y+=Math.max(1,v.length)*6+2; }
        row(B.T('p_from'), $('from').value); d.setFont('helvetica','bold'); row(B.T('p_sum'), cu+' '+E.fmt(a,B.L)); d.setFont('helvetica','normal');
        row('', E.amountInWords(a, $('wl').value, cu)); row(B.T('p_for'), $('for').value); row(B.T('p_meth'), B.T('m_'+$('meth').value));
        y=Math.max(y, 112); d.text(t(($('place').value?$('place').value+', ':'')+(dt?B.fmtDay(dt):'')), M, y); d.line(W-M-70, y, W-M, y); d.setFontSize(8); d.text(t(B.T('p_sign')), W-M-70, y+4);
    } else { d=roll(f==='a5'?0:(f==='80'?80:58)); }
    return d.output('blob');
    function roll(w){ var x=kb(); var fmt = w ? [w, 70 + x.lines.length*10 + x.groups.length*5 + 50] : 'a5'; var dd=new jsPDF({unit:'mm', format:fmt});
      var W = w || 148, M= w?4:12, y=10, fs = w===58 ? 7.5 : 8.5; dd.setFontSize(fs+2); dd.setFont('helvetica','bold'); dd.text(t(sl.s_name||''), W/2, y, {align:'center'}); y+=5; dd.setFont('helvetica','normal'); dd.setFontSize(fs);
      [sl.s_addr, sl.s_fin?B.T('p_fin')+' '+sl.s_fin:'', sl.s_tel].filter(Boolean).forEach(function(l){ dd.splitTextToSize(t(l), W-2*M).forEach(function(z){ dd.text(z, W/2, y, {align:'center'}); y+=4; }); });
      y+=2; dd.text(t(B.T('p_no')+' '+no), M, y); dd.text(t(dt?B.fmtDay(dt):''), W-M, y, {align:'right'}); y+=3; dd.line(M, y, W-M, y); y+=4;
      if(k==='kw'){ var a=B.amt('amt'); [[B.T('p_from'), $('from').value],[B.T('p_for'), $('for').value],[B.T('p_meth'), B.T('m_'+$('meth').value)]].forEach(function(r){ dd.splitTextToSize(t(r[0]+': '+r[1]), W-2*M).forEach(function(z){ dd.text(z, M, y); y+=4; }); });
        y+=2; dd.setFont('helvetica','bold'); dd.text(t(cu+' '+E.fmt(a,B.L)), W-M, y, {align:'right'}); y+=5; dd.setFont('helvetica','normal'); dd.splitTextToSize(t(E.amountInWords(a,$('wl').value,cu)), W-2*M).forEach(function(z){ dd.text(z, M, y); y+=4; }); }
      else { x.lines.forEach(function(l){ dd.splitTextToSize(t(l.d||'-'), W-2*M).forEach(function(z){ dd.text(z, M, y); y+=4; }); dd.text(t(E.fmtNum(l.q,B.L,3)+' x '+E.fmt(l.p,B.L)+'   '+(l.r==='ex'?B.T('p_ex'):l.r+'%')), M+2, y); dd.text(t(E.fmt(l.a,B.L)), W-M, y, {align:'right'}); y+=5; });
        dd.line(M, y-2, W-M, y-2); y+=2; dd.text(t(B.T('excl')), M, y); dd.text(t(E.fmt(x.excl,B.L)), W-M, y, {align:'right'}); y+=4.5;
        x.groups.forEach(function(g){ if(g.r==='ex') return; dd.text(t(B.T('btw_r',{r:g.r})), M, y); dd.text(t(E.fmt(g.b,B.L)), W-M, y, {align:'right'}); y+=4.5; });
        dd.setFont('helvetica','bold'); dd.text(t(B.T('incl')), M, y); dd.text(t(cu+' '+E.fmt(x.incl,B.L)), W-M, y, {align:'right'}); dd.setFont('helvetica','normal'); y+=6;
        if(x.nob) dd.splitTextToSize(t(B.T('exempt_note')), W-2*M).forEach(function(z){ dd.text(z, M, y); y+=4; }); }
      return dd; }
  }); }
function fname(){ return (B.segVal('kind')==='kw'?'kwitantie-':'kassabon-')+($('no').value||'1').replace(/[^\w\-]+/g,'_')+'.pdf'; }
function bump(){ B.store('num_rcpt', BZDOC.bumpNumber($('no').value)); }
function fail(e){ B.toast(e&&e.message==='amount'?B.T('err_input'):B.T('pdf_fail')); }
$('pdf').onclick=function(){ pdf().then(function(b){ B.download(fname(), b); bump(); }, fail); };
$('sharepdf').onclick=function(){ pdf().then(function(b){ BZDOC.share(b, fname(), B.shareText()); bump(); }, fail); };
$('new').onclick=function(){ $('no').value = B.store('num_rcpt') || BZDOC.bumpNumber($('no').value); $('date').value=B.today(); ['from','amt','for'].forEach(function(k){ $(k).value=''; }); $('lines').innerHTML=''; lineRow(null); run(); };
$('addline').onclick=function(){ lineRow(null); };
BZDOC.bind(run);
var dft=B.store('rcpt_draft')||{}; $('no').value = dft.no || B.store('num_rcpt') || '1'; $('date').value=B.today();
['cur','from','amt','for','meth','wl','place'].forEach(function(k){ if(dft[k]!==undefined && dft[k]!=='') $(k).value=dft[k]; }); if(dft.kind) B.segSet('kind', dft.kind);
lineRow(null); B.seg('kind', run);
document.addEventListener('input', function(ev){ if(ev.target.closest('.bz-wrap')) run(); }); document.addEventListener('change', function(ev){ if(ev.target.closest('.bz-wrap')) run(); });
run(); })();
""".replace("%RATES%", _json.dumps(rates)) + _BACKUP_JS
    faq = [("What must a kassabon show?", "According to the Belastingdienst BTW brochure: a sequential number, your name, address and FIN, the date, the goods or services, the amounts excluding and including BTW, the BTW rate, and a note when an exemption applies."),
           ("Does the amount in words follow the official spelling?", "Yes. Dutch amounts follow the Taalunie rules (for example 'duizend tweehonderdvijftig'), with 'één' written with accents to avoid confusion.")]
    return X.page("receipt-generator.html", "biz-receipt", "Invoices & paperwork", "Receipt Maker",
                  "A numbered kwitantie with the amount in words, or an itemised kassabon with BTW, as PDF or for a receipt printer.",
                  body, js, strings, faq, rule_keys=("btw",), related=("biz-invoice", "biz-words", "biz-cash"))


# ─────────────────────────────────────────────────────────────────────────────
# Payment reminder
# ─────────────────────────────────────────────────────────────────────────────
def _page_reminder(X, feeds, prices):
    """payment-reminder.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Details</h2>
    <div class="bz-grid bz-g2">
      {_text("cust", "Customer name")} {_text("inv", "Invoice number")}
      {_field("amt", "Amount due", "")} {_select("cur", "Currency", [("SRD", "SRD"), ("USD", "USD"), ("EUR", "EUR")], "SRD")}
      <div><label class="bz-label" for="due">Due date</label><input id="due" type="date" class="bz-in"></div>
      {_text("me", "Your name / business")}
      {_text("pay", "How to pay (account number)", ta=True)}
      {_text("tel", "Customer WhatsApp number (optional)", mode="tel")}
    </div>
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_seg("tone", [("1", "Friendly"), ("2", "Firm"), ("3", "Final notice")], "1", "Tone")}
      {_seg("lang", [("nl", "Nederlands"), ("en", "English")], "nl", "Message language")}
    </div>
  </div>
  <div class="bz-card">
    <h2>Message</h2>
    <textarea id="msg" class="bz-ta" rows="12"></textarea>
    <div class="bz-acts"><button type="button" class="bz-btn" id="wa">Send by WhatsApp</button><button type="button" class="bz-btn2" id="mail">Send by e-mail</button>
      <button type="button" class="bz-btn2" id="cp">Copy</button></div>
    <p class="bz-src" style="margin-top:.6rem">You can edit the text before sending. Nothing is sent from this site; WhatsApp or your e-mail app opens with the message.</p>
  </div>
</div>
"""
    strings = {"subj_nl": "Herinnering factuur", "subj_en": "Reminder invoice"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$;
var TPL={nl:{1:'Beste {c},\n\nWij willen u vriendelijk herinneren aan factuur {i} van {a}, die op {d} betaald had moeten zijn{late}. Misschien is het aan uw aandacht ontsnapt.\n\nU kunt betalen via:\n{p}\n\nHeeft u al betaald? Dan kunt u dit bericht als niet verzonden beschouwen.\n\nMet vriendelijke groet,\n{m}',
  2:'Beste {c},\n\nOndanks onze eerdere herinnering hebben wij de betaling van factuur {i} ({a}), vervallen op {d}{late}, nog niet ontvangen.\n\nWij verzoeken u het bedrag binnen 7 dagen over te maken via:\n{p}\n\nNeem gerust contact op als er iets niet klopt.\n\nMet vriendelijke groet,\n{m}',
  3:'Beste {c},\n\nFactuur {i} ({a}) is sinds {d} vervallen{late} en is nog steeds niet betaald, ook niet na eerdere herinneringen.\n\nDit is onze laatste herinnering. Als wij de betaling niet binnen 5 dagen ontvangen, zullen wij verdere stappen moeten nemen.\n\nBetalen kan via:\n{p}\n\nMet vriendelijke groet,\n{m}'},
 en:{1:'Dear {c},\n\nThis is a friendly reminder that invoice {i} for {a} was due on {d}{late}. It may have slipped your attention.\n\nYou can pay to:\n{p}\n\nIf you have already paid, please ignore this message.\n\nKind regards,\n{m}',
  2:'Dear {c},\n\nDespite our earlier reminder we have not yet received payment of invoice {i} ({a}), due on {d}{late}.\n\nPlease transfer the amount within 7 days to:\n{p}\n\nDo contact us if anything is unclear.\n\nKind regards,\n{m}',
  3:'Dear {c},\n\nInvoice {i} ({a}) has been overdue since {d}{late} and is still unpaid, despite earlier reminders.\n\nThis is our final reminder. If we do not receive payment within 5 days, we will have to take further steps.\n\nPayment details:\n{p}\n\nKind regards,\n{m}'}};
var edited=false;
function dfmt(iso, lg){ if(!iso) return '…'; var p=iso.split('-'); return new Date(Date.UTC(+p[0],+p[1]-1,+p[2])).toLocaleDateString(lg==='en'?'en-GB':'nl-NL',{day:'numeric',month:'long',year:'numeric',timeZone:'UTC'}); }
function build(){ var lg=B.segVal('lang'), tone=B.segVal('tone'), a=B.amt('amt'), cu=$('cur').value, due=$('due').value;
  var late=''; if(due){ var n=E.daysBetween(due, B.today()); if(n>0) late = lg==='en' ? ' ('+n+' day'+(n===1?'':'s')+' ago)' : ' ('+n+' dag'+(n===1?'':'en')+' geleden)'; }
  var amount = a===null ? '…' : cu+' '+new Intl.NumberFormat(lg==='en'?'en-US':'nl-NL',{minimumFractionDigits:2, maximumFractionDigits:2}).format(a/100);
  var v={c:$('cust').value||'…', i:$('inv').value||'…', a:amount, d:dfmt(due, lg), late:late, p:$('pay').value||'…', m:$('me').value||'…'};
  var s=TPL[lg][tone]; Object.keys(v).forEach(function(k){ s=s.split('{'+k+'}').join(v[k]); }); return s; }
function run(){ if(!edited) $('msg').value=build(); B.store('reminder_me', {me:$('me').value, pay:$('pay').value}); }
$('msg').addEventListener('input', function(){ edited=true; });
['cust','inv','amt','due','me','pay','cur'].forEach(function(k){ $(k).addEventListener('input', function(){ edited=false; run(); }); $(k).addEventListener('change', function(){ edited=false; run(); }); });
B.seg('tone', function(){ edited=false; run(); }); B.seg('lang', function(){ edited=false; run(); });
var st=B.store('reminder_me')||{}; if(st.me) $('me').value=st.me; if(st.pay) $('pay').value=st.pay; if(B.L==='en') B.segSet('lang','en');
$('wa').onclick=function(){ var n=E.waNumber($('tel').value); window.open('https://wa.me/'+(n||'')+'?text='+encodeURIComponent($('msg').value), '_blank', 'noopener'); };
$('mail').onclick=function(){ location.href='mailto:?subject='+encodeURIComponent(B.T('subj_'+B.segVal('lang'))+' '+$('inv').value)+'&body='+encodeURIComponent($('msg').value); };
$('cp').onclick=function(){ B.copy($('msg').value); };
run(); })();
"""
    return X.page("payment-reminder.html", "biz-reminder", "Invoices & paperwork", "Payment Reminder",
                  "A polite, clear payment reminder in Dutch or English, ready for WhatsApp or e-mail.",
                  body, js, strings, None, rule_keys=(), related=("biz-invoice", "biz-workdays", "biz-receipt"))


# ─────────────────────────────────────────────────────────────────────────────
# Amount in words
# ─────────────────────────────────────────────────────────────────────────────
def _page_words(X, feeds, prices):
    """amount-in-words.html"""
    body = f"""
<div class="bz-card">
  <div class="bz-grid bz-g2">{_field("amt", "Amount", "1.250,50", prefix="", big=True, money=True)}{_select("cur", "Currency", [("SRD", "SRD"), ("USD", "USD"), ("EUR", "EUR")], "SRD")}</div>
</div>
<div class="bz-grid bz-g2">
  <div class="bz-card"><span class="bz-label">Nederlands</span><p id="nl" style="font-size:1.25rem;font-weight:600;min-height:2.5rem" translate="no"></p><div class="bz-acts"><button type="button" class="bz-btn2" data-c="nl">Copy</button></div></div>
  <div class="bz-card"><span class="bz-label">English</span><p id="en" style="font-size:1.25rem;font-weight:600;min-height:2.5rem" translate="no"></p><div class="bz-acts"><button type="button" class="bz-btn2" data-c="en">Copy</button></div></div>
</div>
<div class="bz-card"><h2>Spelling rules used</h2>
  <ul style="padding-left:1.1rem;list-style:disc;line-height:1.7">
    <li>Numbers up to a thousand are written as one word, for example <i translate="no">tweehonderdvijftig</i>.</li>
    <li>After <i translate="no">duizend</i> comes a space, and <i translate="no">miljoen</i> and <i translate="no">miljard</i> stand apart, for example <i translate="no">tweeduizend vijfhonderd</i>.</li>
    <li>A diaeresis where two vowels meet, for example <i translate="no">tweeëntwintig</i>.</li>
    <li>The number one is written <i translate="no">één</i> when it stands alone, to avoid confusion with the article <i translate="no">een</i>.</li>
  </ul>
  <p class="bz-src">Dutch spelling follows the Taalunie rules for numbers.</p>
</div>
"""
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$;
function run(){ var a=B.amt('amt'), cu=$('cur').value; $('nl').textContent = a===null?'':E.amountInWords(a,'nl',cu); $('en').textContent = a===null?'':E.amountInWords(a,'en',cu); B.saveUrl(['amt','cur']); }
[].forEach.call(document.querySelectorAll('[data-c]'), function(b){ b.onclick=function(){ B.copy($(b.getAttribute('data-c')).textContent); }; });
B.loadUrl(['amt','cur']); B.on(['amt'],'input',run); B.on(['cur'],'change',run); run(); })();
"""
    return X.page("amount-in-words.html", "biz-words", "Invoices & paperwork", "Amount in Words",
                  "Write any amount out in words, in Dutch and English, for receipts, cheques and contracts.",
                  body, js, {}, None, rule_keys=(), related=("biz-receipt", "biz-invoice"))


# ─────────────────────────────────────────────────────────────────────────────
# Cash counter
# ─────────────────────────────────────────────────────────────────────────────
def _page_cash(X, feeds, prices):
    """cash-counter.html"""
    cash = X.R["cash"][-1]
    rates = _rate_options(X)

    def row(d, kind):
        lab = (("SRD " + (f"{d:g}".replace(".", ","))) if d >= 1 else f"{int(round(d * 100))} cent")
        return (f'<tr><td><b class="bz-num" translate="no">{lab}</b> <small style="color:var(--ink-soft)">{kind}</small></td>'
                f'<td><input class="bz-in bz-num" data-d="{d}" inputmode="numeric" style="max-width:7rem"></td>'
                f'<td class="n bz-num" data-s="{d}">–</td></tr>')
    rows = "".join(row(d, "note") for d in cash["notes"]) + "".join(row(d, "coin") for d in cash["coins"])
    usd = str(rates[0]["usd"]).replace(".", ",") if rates else ""
    eur = str(rates[0]["eur"]).replace(".", ",") if rates else ""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Count the drawer</h2>
    <div class="bz-scroll"><table class="bz-tbl"><thead><tr><th>Note / coin</th><th>How many</th><th class="n">Value</th></tr></thead><tbody id="cnt">{rows}</tbody></table></div>
    <h3>Foreign cash (optional)</h3>
    <div class="bz-grid bz-g2">
      {_field("usd", "US dollars in the drawer", "", prefix="USD")} {_field("usdr", "Rate (SRD per USD)", usd, prefix="")}
      {_field("eur", "Euros in the drawer", "", prefix="EUR")} {_field("eurr", "Rate (SRD per EUR)", eur, prefix="")}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Cash counted</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card">
      {_field("exp", "Expected in the drawer (from your sales)", "")}
      <div style="margin-top:.6rem">{_field("float", "Change float to keep in the drawer", "")}</div>
      <table class="bz-tbl" style="margin-top:.8rem"><tbody id="tot"></tbody></table>
      <div class="bz-acts"><button type="button" class="bz-btn" id="save">Save this count</button><button type="button" class="bz-btn2" id="clear">Clear</button><button type="button" class="bz-btn2" data-bz="print">Print</button></div>
    </div>
    <div class="bz-card"><h2 style="font-size:1.05rem">Saved counts</h2><ul id="log" class="bz-feed" style="padding:0;margin:0"></ul></div>
  </div>
</div>
"""
    strings = {"t_srd": "SRD cash", "t_fx": "Foreign cash in SRD", "t_total": "Total counted", "t_exp": "Expected", "t_diff": "Difference",
               "t_bank": "To deposit (total minus change float)", "say_ok": "The drawer matches.", "say_over": "{d} more than expected.",
               "say_short": "{d} short.", "saved": "Count saved"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var ins=[].slice.call($('cnt').querySelectorAll('input'));
function run(){ var t=0; ins.forEach(function(i){ var d=+i.getAttribute('data-d'), n=parseInt(i.value,10)||0; var v=E.toCents(d)*n; t+=v; document.querySelector('[data-s="'+i.getAttribute('data-d')+'"]').textContent = n? E.fmt(v,B.L):'–'; });
  var fx=0, u=B.amt('usd'), ur=B.num('usdr'), e=B.amt('eur'), er=B.num('eurr'); if(u&&ur) fx+=Math.round(u*ur); if(e&&er) fx+=Math.round(e*er);
  var tot=t+fx; $('big').textContent=B.srd(tot); var ex=B.amt('exp'), fl=B.amt('float')||0; var rows=[[B.T('t_srd'), B.srd(t)]]; if(fx) rows.push([B.T('t_fx'), B.srd(fx)]); rows.push([B.T('t_total'), B.srd(tot),'bz-tot']);
  if(ex!==null){ var d=tot-ex; rows.push([B.T('t_exp'), B.srd(ex)]); rows.push([B.T('t_diff'), (d>0?'+ ':d<0?'− ':'')+B.srd(Math.abs(d)),'bz-tot']); $('say').textContent= d===0?B.T('say_ok'):(d>0?B.T('say_over',{d:B.srd(d)}):B.T('say_short',{d:B.srd(-d)})); } else $('say').textContent='';
  if(fl) rows.push([B.T('t_bank'), B.srd(tot-fl),'bz-sub']); $('tot').innerHTML=B.rows(rows); B.shareText=function(){ return $('big').textContent+' '+$('say').textContent; }; return tot; }
function drawLog(){ var l=B.store('cash_log')||[]; $('log').innerHTML=l.slice(0,15).map(function(x){ return '<li><b>'+B.esc(x.when)+'</b><small>'+B.esc(B.srd(x.tot)+(x.diff!==null?'  ·  '+(x.diff>0?'+':'')+E.fmt(x.diff,B.L):''))+'</small></li>'; }).join(''); }
$('save').onclick=function(){ var tot=run(), ex=B.amt('exp'); var l=B.store('cash_log')||[]; var now=new Date(Date.now()-3*3600e3).toISOString().slice(0,16).replace('T',' ');
  l.unshift({when:now, tot:tot, diff: ex===null?null:tot-ex}); B.store('cash_log', l.slice(0,60)); drawLog(); B.toast(B.T('saved')); };
$('clear').onclick=function(){ ins.forEach(function(i){ i.value=''; }); ['usd','eur','exp'].forEach(function(k){ $(k).value=''; }); run(); };
document.addEventListener('input', run); drawLog(); run(); })();
"""
    return X.page("cash-counter.html", "biz-cash", "Office tools", "Cash Counter & Cash-Up",
                  "Count the notes and coins in the till, add dollars and euros, and see at once whether the drawer matches.",
                  body, js, strings, None, rule_keys=("cash",), related=("biz-receipt", "biz-register", "biz-pricing"))


# ─────────────────────────────────────────────────────────────────────────────
# BTW register / cashbook
# ─────────────────────────────────────────────────────────────────────────────
def _page_register(X, feeds, prices):
    """btw-register.html"""
    rates = sorted(X.R["btw"][-1]["rates"], reverse=True)
    std = X.R["btw"][-1]["standard"]
    body = f"""
<div class="bz-card">
  <h2>Add a sale or purchase</h2>
  <div class="bz-grid bz-g3">
    <div><label class="bz-label" for="d">Date</label><input id="d" type="date" class="bz-in"></div>
    {_seg("type", [("sale", "Sale"), ("buy", "Purchase / cost")], "sale", "Type")}
    {_text("desc", "Description")}
    {_field("amt", "Amount", "")}
    {_seg("inc", [("incl", "incl. BTW"), ("excl", "excl. BTW")], "incl", "The amount is")}
    {_select("rate", "BTW rate", [(str(r), f"{r}%") for r in rates] + [("ex", "Exempt / no BTW")], str(std))}
  </div>
  <div class="bz-acts"><button type="button" class="bz-btn" id="add">Add</button></div>
</div>
<div class="bz-grid bz-split">
  <div class="bz-card">
    <div class="bz-grid bz-g2">{_select("mon", "Month", [], None)}<div></div></div>
    <div class="bz-scroll" style="margin-top:.7rem"><table class="bz-tbl" style="min-width:560px"><thead><tr><th>Date</th><th>Description</th><th class="n">Excl.</th><th class="n">BTW</th><th></th></tr></thead><tbody id="list"></tbody></table></div>
    <div class="bz-acts"><button type="button" class="bz-btn2" id="csv">Export month (CSV)</button><button type="button" class="bz-btn2" data-bz="print">Print</button></div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k" id="rk">BTW to pay this month</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="sum"></tbody></table>
      <p class="bz-src" style="margin-top:.6rem">These are the figures you need for the monthly BTW return: BTW charged on sales per rate, minus the BTW paid on business purchases (input tax). File and pay before the 16th of the next month.</p></div>
  </div>
</div>
{_BACKUP_HTML}
"""
    strings = dict(_DOC_STRINGS)
    strings.update({"k_pay": "BTW to pay this month", "k_back": "BTW to reclaim this month", "say": "Due before {d}.",
                    "s_sales": "Sales excl. BTW", "s_out": "BTW on sales {r}%", "s_buy": "Purchases excl. BTW", "s_in": "BTW paid on purchases (input tax)",
                    "s_net": "Balance", "s_ex": "Exempt or 0% sales", "t_sale": "Sale", "t_buy": "Purchase", "del": "Delete this line?", "exempt": "exempt",
                    "csv_h": "date,type,description,rate,excl,btw,incl"})
    js = _DOCS_JS + r"""
(function(){ var B=BZ,E=B.E,$=B.$;
function all(){ return B.store('register')||[]; }
function months(){ var m={}; all().forEach(function(x){ m[x.d.slice(0,7)]=1; }); m[B.today().slice(0,7)]=1; return Object.keys(m).sort().reverse(); }
function mname(k){ return new Date(Date.UTC(+k.slice(0,4), +k.slice(5,7)-1, 1)).toLocaleDateString(B.L==='en'?'en-GB':(B.L==='es'?'es-ES':'nl-NL'),{month:'long',year:'numeric',timeZone:'UTC'}); }
function drawMonths(){ var cur=$('mon').value; $('mon').innerHTML=months().map(function(k){ return '<option value="'+k+'">'+B.esc(mname(k))+'</option>'; }).join(''); if(cur) $('mon').value=cur; if(!$('mon').value) $('mon').selectedIndex=0; }
function draw(){ var m=$('mon').value, L=all().filter(function(x){ return x.d.slice(0,7)===m; }).sort(function(a,b){ return a.d<b.d?-1:1; });
  $('list').innerHTML=L.map(function(x){ return '<tr><td>'+B.esc(B.fmtDay(x.d))+'</td><td><span class="bz-tag">'+B.esc(B.T(x.t==='sale'?'t_sale':'t_buy'))+'</span>'+B.esc(x.desc)+'<br><small>'+(x.r==='ex'?B.esc(B.T('exempt')):x.r+'%')+'</small></td><td class="n">'+E.fmt(x.e,B.L)+'</td><td class="n">'+E.fmt(x.b,B.L)+'</td><td><button type="button" class="bz-x" data-id="'+x.id+'">&times;</button></td></tr>'; }).join('');
  [].forEach.call($('list').querySelectorAll('.bz-x'), function(b){ b.onclick=function(){ if(!confirm(B.T('del'))) return; B.store('register', all().filter(function(x){ return String(x.id)!==b.getAttribute('data-id'); })); draw(); }; });
  var out={}, sales=0, ex=0, buys=0, inp=0; L.forEach(function(x){ if(x.t==='sale'){ if(x.r==='ex'||+x.r===0){ ex+=x.e; } else { out[x.r]=(out[x.r]||0)+x.e; } sales+=x.e; } else { buys+=x.e; inp+=x.b; } });
  var rows=[[B.T('s_sales'), B.srd(sales)]], outB=0; Object.keys(out).sort(function(a,b){ return b-a; }).forEach(function(r){ var b=E.pctOf(out[r], +r); outB+=b; rows.push([B.T('s_out',{r:r})+' ('+B.srd(out[r])+')', B.srd(b),'bz-sub']); });
  if(ex) rows.push([B.T('s_ex'), B.srd(ex),'bz-sub']); rows.push([B.T('s_buy'), B.srd(buys)]); rows.push([B.T('s_in'), '− '+B.srd(inp)]);
  var net=outB-inp; rows.push([B.T('s_net'), B.srd(net),'bz-tot']); $('sum').innerHTML=B.rows(rows);
  $('rk').textContent=B.T(net>=0?'k_pay':'k_back'); $('big').textContent=B.srd(Math.abs(net));
  var y=+m.slice(0,4), mo=+m.slice(5,7); var d=E.monthlyDeadlines(y, mo, B.R, B.H).btw; $('say').textContent=B.T('say',{d:B.fmtDay(d)});
  B.shareText=function(){ return mname(m)+': '+$('rk').textContent+' '+$('big').textContent; }; }
$('add').onclick=function(){ var a=B.amt('amt'), d=$('d').value; if(a===null||!d){ B.toast(B.T('err_input')); return; }
  var r=$('rate').value, incl=B.segVal('inc')==='incl'; var e, b;
  if(r==='ex'){ e=a; b=0; } else if(incl){ var x=E.btwFromIncl(a,+r); e=x.excl; b=x.btw; } else { e=a; b=E.pctOf(a,+r); }
  var L=all(); L.push({id:Date.now(), d:d, t:B.segVal('type'), desc:$('desc').value.trim(), r:r, e:e, b:b}); B.store('register', L);
  $('amt').value=''; $('desc').value=''; drawMonths(); $('mon').value=d.slice(0,7); draw(); $('amt').focus(); };
$('csv').onclick=function(){ var m=$('mon').value; var rows=[B.T('csv_h')].concat(all().filter(function(x){ return x.d.slice(0,7)===m; }).map(function(x){
    return [x.d, x.t, '"'+String(x.desc).replace(/"/g,'""')+'"', x.r, (x.e/100).toFixed(2), (x.b/100).toFixed(2), ((x.e+x.b)/100).toFixed(2)].join(','); }));
  B.download('btw-register-'+m+'.csv', new Blob(['﻿'+rows.join('\r\n')], {type:'text/csv'})); };
$('d').value=B.today(); $('mon').addEventListener('change', draw); B.seg('type'); B.seg('inc'); drawMonths(); draw(); })();
""" + _BACKUP_JS
    faq = [("Is this an official BTW return?", "No. It collects the figures you need; you still file the return yourself through the Belastingdienst portal."),
           ("Where is my data stored?", "Only in this browser. Download a backup regularly, and keep your own invoices and receipts for 10 years as the BTW law requires.")]
    return X.page("btw-register.html", "biz-register", "Invoices & paperwork", "BTW Register & Cashbook",
                  "Keep track of sales and purchases and see each month how much BTW you pay or get back.",
                  body, js, strings, faq, rule_keys=("btw",), related=("biz-btw", "biz-invoice", "biz-deadlines"))


# ─────────────────────────────────────────────────────────────────────────────
# Payslip generator
# ─────────────────────────────────────────────────────────────────────────────
def _page_payslip(X, feeds, prices):
    """payslip-generator.html"""
    body = f"""
{_SELLER_HTML}
<div class="bz-grid bz-split" style="margin-top:1rem">
  <div>
    <div class="bz-card">
      <h2>Employee</h2>
      <div class="bz-acts" style="margin-top:0;margin-bottom:.7rem"><select id="emps" class="bz-sel" style="max-width:18rem"></select><button type="button" class="bz-btn2" id="saveemp">Save employee</button><button type="button" class="bz-btn2" id="delemp">Remove</button></div>
      <div class="bz-grid bz-g2">
        {_text("e_name", "Name")} {_text("e_no", "Staff number / ID (optional)")} {_text("e_job", "Job title (optional)")}
        <div><label class="bz-label" for="per">Pay month</label><input id="per" type="month" class="bz-in"></div>
      </div>
      <div style="margin-top:.7rem">{_field("amt", "Gross monthly wage", "", big=True)}</div>
      {_salary_inputs_html(X)}
    </div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Net pay</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div id="notes"></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="emp"></tbody></table>
      <details class="bz-how"><summary>Employer costs</summary><table class="bz-tbl"><tbody id="er"></tbody></table></details>
      <div class="bz-acts bz-noprint"><button type="button" class="bz-btn" id="pdf">Download payslip PDF</button><button type="button" class="bz-btn2" id="sharepdf">Share PDF</button>
        <button type="button" class="bz-btn2" id="all">PDF for all saved employees</button></div></div>
  </div>
</div>
{_BACKUP_HTML}
"""
    strings = dict(_DOC_STRINGS)
    strings.update(_SALARY_STRINGS)
    strings.update({"say": "{n} for {m}.", "t_slip": "PAYSLIP", "p_emp": "Employee", "p_per": "Period", "p_job": "Job", "p_no": "Staff no.",
                    "p_employer": "Employer", "p_fin": "FIN", "p_paid": "Net pay", "p_note": "Calculated with the official Surinamese rules; see exploresuriname.com/salary-calculator",
                    "p_ercost": "Employer contributions (not deducted from the employee)", "no_emps": "Save at least one employee first.", "saved_e": "Employee saved", "sel": "New employee"})
    ids = "['e_name','e_no','e_job','amt','ot','ta','ua','ca','kids','apf','apfer','bzv','bzver','med','a60','nop']"
    js = _DOCS_JS + _SALARY_JS + r"""
(function(){ var B=BZ,E=B.E,$=B.$; var IDS=%IDS%;
function iso(){ var p=$('per').value; return p ? p+'-15' : B.today(); }
function calcFor(st){ var keep={}; IDS.forEach(function(k){ var el=$(k); keep[k]= el.type==='checkbox'?el.checked:el.value; });
  if(st) IDS.forEach(function(k){ var el=$(k); if(st[k]===undefined) return; if(el.type==='checkbox') el.checked=st[k]; else el.value=st[k]; });
  var g=B.amt('amt'); var inp=bzSalaryInputs(''); inp.gross=g||0; var x=E.salary(inp, B.R, iso()); var out={x:x, name:$('e_name').value, no:$('e_no').value, job:$('e_job').value};
  if(st) IDS.forEach(function(k){ var el=$(k); if(el.type==='checkbox') el.checked=keep[k]; else el.value=keep[k]; }); return out; }
function per(){ var p=$('per').value||B.today().slice(0,7); return new Date(Date.UTC(+p.slice(0,4), +p.slice(5,7)-1, 1)).toLocaleDateString(B.L==='en'?'en-GB':(B.L==='es'?'es-ES':'nl-NL'),{month:'long',year:'numeric',timeZone:'UTC'}); }
function run(){ var g=B.amt('amt'); if(g===null){ $('big').textContent='–'; $('emp').innerHTML=''; $('er').innerHTML=''; return; }
  var r=calcFor(null), x=r.x; $('big').textContent=B.srd(x.net); $('say').textContent=B.T('say',{n:r.name||'', m:per()});
  $('emp').innerHTML=B.rows(bzSalaryRows(x)); $('er').innerHTML=B.rows(bzEmployerRows(x)); $('notes').innerHTML=bzSalaryNotes(x);
  B.shareText=function(){ return $('say').textContent+' '+$('big').textContent; }; }
function state(){ var s={}; IDS.forEach(function(k){ var el=$(k); s[k]= el.type==='checkbox'?el.checked:el.value; }); return s; }
function emps(){ return B.store('employees')||[]; }
function drawEmps(sel){ var L=emps(); $('emps').innerHTML='<option value="">'+B.esc(B.T('sel'))+'</option>'+L.map(function(e,i){ return '<option value="'+i+'">'+B.esc(e.e_name||('#'+(i+1)))+'</option>'; }).join(''); if(sel!==undefined) $('emps').value=sel; }
$('emps').onchange=function(){ var e=emps()[+$('emps').value]; IDS.forEach(function(k){ var el=$(k); if(!e){ if(el.type==='checkbox') el.checked=false; else if(k!=='apf'&&k!=='apfer'&&k!=='bzver') el.value=''; return; } if(e[k]===undefined) return; if(el.type==='checkbox') el.checked=e[k]; else el.value=e[k]; }); run(); };
$('saveemp').onclick=function(){ var s=state(); if(!s.e_name.trim()){ B.toast(B.T('err_input')); return; } var L=emps(); var i=L.findIndex(function(e){ return e.e_name===s.e_name; }); if(i>=0) L[i]=s; else { L.push(s); i=L.length-1; } B.store('employees', L); drawEmps(String(i)); B.toast(B.T('saved_e')); };
$('delemp').onclick=function(){ var i=$('emps').value; if(i==='') return; var L=emps(); L.splice(+i,1); B.store('employees', L); drawEmps(''); };
function slip(d, r, first){ var t=BZDOC.t, sl=BZDOC.seller(), x=r.x, W=210, M=16, y=18; if(!first) d.addPage();
  if(sl.logo){ try{ d.addImage(sl.logo,'JPEG',M,y-5,24,0); }catch(e){} }
  d.setFont('helvetica','bold'); d.setFontSize(18); d.text(t(B.T('t_slip')), W-M, y, {align:'right'}); d.setFontSize(10); d.setFont('helvetica','normal');
  d.text(t(per()), W-M, y+6, {align:'right'}); y+=22;
  d.setFont('helvetica','bold'); d.text(t(B.T('p_employer')), M, y); d.text(t(B.T('p_emp')), 110, y); d.setFont('helvetica','normal'); y+=5;
  var a=[sl.s_name, sl.s_addr, sl.s_fin?B.T('p_fin')+' '+sl.s_fin:''].filter(Boolean), b=[r.name, r.job?B.T('p_job')+': '+r.job:'', r.no?B.T('p_no')+' '+r.no:''].filter(Boolean);
  for(var i=0;i<Math.max(a.length,b.length);i++){ if(a[i]) d.text(t(a[i]), M, y); if(b[i]) d.text(t(b[i]), 110, y); y+=5; } y+=6;
  function line(l, v, bold){ d.setFont('helvetica', bold?'bold':'normal'); var ls=d.splitTextToSize(t(l), 125); d.text(ls, M, y); d.text(t(v), W-M, y, {align:'right'}); y+=ls.length*5+1.5; if(bold){ d.setDrawColor(30); d.line(M, y-5.5, W-M, y-5.5); } }
  bzSalaryRows(x).forEach(function(rw){ line(rw[0], rw[1], rw[2]==='bz-tot'); });
  y+=6; d.setFontSize(8.5); d.setTextColor(90); d.text(t(B.T('p_ercost')), M, y); y+=5; bzEmployerRows(x).forEach(function(rw){ line(rw[0], rw[1], false); });
  d.setFontSize(7.5); d.setTextColor(150); d.text(t(B.T('p_note')), W/2, 290, {align:'center'}); d.setTextColor(20); d.setFontSize(10); }
function pdf(list){ return BZDOC.pdfLib().then(function(jsPDF){ var d=new jsPDF({unit:'mm', format:'a4'}); list.forEach(function(r,i){ slip(d, r, i===0); }); return d.output('blob'); }); }
function fn(n){ return 'loonstrook-'+(n||'medewerker').replace(/[^\w\-]+/g,'_')+'-'+($('per').value||B.today().slice(0,7))+'.pdf'; }
$('pdf').onclick=function(){ if(B.amt('amt')===null){ B.toast(B.T('err_input')); return; } pdf([calcFor(null)]).then(function(b){ B.download(fn($('e_name').value), b); }, function(){ B.toast(B.T('pdf_fail')); }); };
$('sharepdf').onclick=function(){ if(B.amt('amt')===null){ B.toast(B.T('err_input')); return; } pdf([calcFor(null)]).then(function(b){ BZDOC.share(b, fn($('e_name').value), B.shareText()); }, function(){ B.toast(B.T('pdf_fail')); }); };
$('all').onclick=function(){ var L=emps(); if(!L.length){ B.toast(B.T('no_emps')); return; } pdf(L.map(function(e){ return calcFor(e); })).then(function(b){ B.download(fn('alle'), b); }, function(){ B.toast(B.T('pdf_fail')); }); };
$('per').value=B.today().slice(0,7); BZDOC.bind(run); drawEmps('');
document.addEventListener('input', function(ev){ if(ev.target.closest('.bz-wrap')) run(); }); document.addEventListener('change', function(ev){ if(ev.target.closest('.bz-wrap')) run(); });
run(); })();
""".replace("%IDS%", ids) + _BACKUP_JS
    faq = [("Is the payslip calculation the same as the salary calculator?", "Yes, it uses exactly the same engine and rules, which we tested against two Surinamese payroll programs."),
           ("Are my employees' details stored online?", "No. They stay in this browser only. Use the backup button to keep a copy.")]
    return X.page("payslip-generator.html", "biz-payslip", "Staff & payroll", "Payslip Generator",
                  "Make a clear payslip for each employee, calculated with the official rules, as PDF. Your data stays on your device.",
                  body, js, strings, faq,
                  rule_keys=("wage_tax", "overtime_tax", "tax_free", "aov", "apf", "apf_common", "fvo"),
                  related=("biz-salary", "biz-timesheet", "biz-vacation", "biz-deadlines"))


# ─────────────────────────────────────────────────────────────────────────────
# Import landed cost
# ─────────────────────────────────────────────────────────────────────────────
def _page_import(X, feeds, prices):
    """import-cost-calculator.html"""
    imp = X.R["import"][-1]
    rates = _rate_options(X)
    cb = [o for o in rates if o["id"] == "cbvs"]
    cbu = cb[0]["usd"] if cb else (rates[0]["usd"] if rates else "")
    cbe = cb[0]["eur"] if cb else (rates[0]["eur"] if rates else "")
    std = X.R["btw"][-1]["standard"]
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Shipment</h2>
    <div class="bz-grid bz-g2">
      {_seg("cur", [("USD", "USD"), ("EUR", "EUR")], "USD", "Invoice currency")}
      {_field("rate", "Exchange rate (SRD per unit)", str(cbu).replace(".", ","), prefix="", hint="Filled with today's CBvS selling rate. Customs uses its own rate (the douanekoers), set every two weeks: type the rate from your declaration if you have it.")}
      {_field("goods", "Value of the goods", "1.000", prefix="", money=True)}
      {_field("freight", "Freight", "150", prefix="", money=True)}
      {_field("ins", "Insurance", "10", prefix="", money=True)}
      {_field("qty", "Number of units in the shipment", "1", prefix="", mode="numeric")}
    </div>
    <h3>Duties and levies</h3>
    <div class="bz-grid bz-g2">
      {_field("duty", "Import duty %", "20", prefix="", hint="Look up the rate for your HS code in the official tariff")}
      {_field("excise", "Excise (SRD, if any)", "0")}
      {_field("stat", "Statistics fee %", str(imp["stat_pct"]).replace(".", ","), prefix="")}
      {_field("cons", "Consent fee %", str(imp["consent_pct"]).replace(".", ","), prefix="")}
      {_seg("btw", [(str(r), f"{r}%") for r in sorted(X.R["btw"][-1]["rates"], key=lambda r: (r != std, -r))], str(std), "BTW on import")}
      {_field("other", "Broker, handling, local transport (SRD)", "0")}
    </div>
    <p class="bz-src" style="margin-top:.6rem"><a href="{imp['tariff_url']}" target="_blank" rel="noopener">Official customs tariff (ASYCUDA)</a> &middot; the statistics and consent fees are the rates reported by three independent sources; the legal text is not published online, so you can change them.</p>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Landed cost per unit</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>{_share_bar('<a class="bz-btn2" id="topr" href="pricing-calculator.html">Set a selling price</a>')}</div>
    <div class="bz-note">This is an estimate. Customs decides the final amount on your declaration, using the official tariff and customs exchange rate.</div>
  </div>
</div>
<script id="bzCb" type="application/json">{_json.dumps({"USD": cbu, "EUR": cbe})}</script>
"""
    strings = {"say": "Total landed cost {t} for the shipment. Duties and taxes: {x}.", "r_cif": "CIF value in SRD (goods + freight + insurance)", "r_duty": "Import duty {p}%",
               "r_exc": "Excise", "r_stat": "Statistics fee {p}%", "r_cons": "Consent fee {p}%", "r_base": "BTW base", "r_btw": "BTW {p}%", "r_other": "Broker and handling",
               "r_total": "Total landed cost", "r_unit": "Per unit", "r_unit_ex": "Per unit excluding BTW (BTW can be reclaimed if you are registered)"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var CB=JSON.parse($('bzCb').textContent); var IDS=['cur','rate','goods','freight','ins','qty','duty','excise','stat','cons','btw','other'];
function run(){ var cur=B.segVal('cur'), r=B.num('rate'); var g=B.amt('goods')||0, f=B.amt('freight')||0, i=B.amt('ins')||0; if(r===null){ $('big').textContent='–'; return; }
  var q=Math.max(1, Math.floor(B.num('qty')||1)), du=B.num('duty')||0, st=B.num('stat')||0, co=B.num('cons')||0, bt=+B.segVal('btw');
  var x=E.importCost({cifForeign:g+f+i, rate:r, dutyPct:du, statPct:st, consentPct:co, excise:B.amt('excise')||0, btwPct:bt, other:B.amt('other')||0, qty:q});
  $('big').textContent=B.srd(x.perUnit); $('say').textContent=B.T('say',{t:B.srd(x.total), x:B.srd(x.taxes)});
  var rows=[[B.T('r_cif'), B.srd(x.cif)],[B.T('r_duty',{p:E.fmtNum(du,B.L)}), B.srd(x.duty)]]; if(x.excise) rows.push([B.T('r_exc'), B.srd(x.excise)]);
  rows.push([B.T('r_stat',{p:E.fmtNum(st,B.L)}), B.srd(x.stat)]); rows.push([B.T('r_cons',{p:E.fmtNum(co,B.L)}), B.srd(x.consent)]); rows.push([B.T('r_base'), B.srd(x.btwBase),'bz-sub']);
  rows.push([B.T('r_btw',{p:bt}), B.srd(x.btw)]); if(x.other) rows.push([B.T('r_other'), B.srd(x.other)]); rows.push([B.T('r_total'), B.srd(x.total),'bz-tot']);
  if(q>1) rows.push([B.T('r_unit'), B.srd(x.perUnit)]); rows.push([B.T('r_unit_ex'), B.srd(x.perUnitExBtw),'bz-sub']); $('tbl').innerHTML=B.rows(rows);
  $('topr').href='pricing-calculator.html?cost='+encodeURIComponent(B.fmtIn(x.perUnitExBtw))+'&cur=SRD';
  B.shareText=function(){ return $('say').textContent; }; B.saveUrl(IDS); }
var had=B.loadUrl(IDS); B.seg('cur', function(v){ $('rate').value=E.fmtNum(CB[v],B.L,4); run(); }); B.seg('btw', run); B.on(IDS,'input',run); run(); })();
"""
    faq = [("How is import BTW calculated in Suriname?", "Over the customs value plus import duty, excise and the other levies due on import, such as the statistics and consent fees (Wet BTW art. 19)."),
           ("Which exchange rate does customs use?", "The douanekoers, set every two weeks by the Central Bank from the market selling rate. It is not published in one fixed place, so the tool starts with today's CBvS rate and lets you type the customs rate from your declaration.")]
    return X.page("import-cost-calculator.html", "biz-import", "Pricing, import & finance", "Import Cost Calculator",
                  "Estimate duties, fees and BTW on a shipment and the real cost per item before you order.",
                  body, js, strings, faq, rule_keys=("import", "btw"), related=("biz-pricing", "biz-g-import", "biz-breakeven"))


# ─────────────────────────────────────────────────────────────────────────────
# Loan / lease
# ─────────────────────────────────────────────────────────────────────────────
def _page_loan(X, feeds, prices):
    """loan-calculator.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Loan</h2>
    <div class="bz-grid bz-g2">
      {_field("p", "Amount", "100.000", prefix="", big=True, money=True)}
      {_select("cur", "Currency", [("SRD", "SRD"), ("USD", "USD"), ("EUR", "EUR")], "SRD")}
      {_field("r", "Interest per year %", "12", prefix="")}
      {_field("n", "Term in months", "36", prefix="", mode="numeric")}
    </div>
    <div class="bz-chips"><button type="button" class="bz-chip" data-n="12">1 year</button><button type="button" class="bz-chip" data-n="36">3 years</button><button type="button" class="bz-chip" data-n="60">5 years</button><button type="button" class="bz-chip" data-n="120">10 years</button></div>
    <p class="bz-src" style="margin-top:.8rem">Annuity: the same payment every month. Banks may add fees or use a different method; ask your bank for the official offer. Reference: the <a href="https://www.nob.sr/" target="_blank" rel="noopener">Nationale Ontwikkelingsbank</a> publishes its rate ranges for business loans on its website.</p>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Monthly payment</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>{_share_bar()}</div>
  </div>
</div>
<div class="bz-card"><h2>Repayment table</h2><div class="bz-scroll"><table class="bz-tbl" style="min-width:520px"><thead><tr><th>Month</th><th class="n">Payment</th><th class="n">Interest</th><th class="n">Repayment</th><th class="n">Balance</th></tr></thead><tbody id="sched"></tbody></table></div></div>
"""
    strings = {"say": "{n} payments of {p}. You pay {i} interest in total.", "r_p": "Loan amount", "r_i": "Total interest", "r_t": "Total to pay back"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var IDS=['p','cur','r','n'];
function run(){ var p=B.amt('p'), r=B.num('r'), n=Math.floor(B.num('n')||0), cu=$('cur').value; if(p===null||r===null||n<=0||n>600){ $('big').textContent='–'; $('sched').innerHTML=''; return; }
  var l=E.loan(p, r, n); function m(c){ return cu+' '+E.fmt(c,B.L); }
  $('big').textContent=m(l.payment); $('say').textContent=B.T('say',{n:n, p:m(l.payment), i:m(l.totalInterest)});
  $('tbl').innerHTML=B.rows([[B.T('r_p'), m(p)],[B.T('r_i'), m(l.totalInterest)],[B.T('r_t'), m(l.totalPaid),'bz-tot']]);
  $('sched').innerHTML=l.rows.map(function(x){ return '<tr><td>'+x.n+'</td><td class="n">'+E.fmt(x.payment,B.L)+'</td><td class="n">'+E.fmt(x.interest,B.L)+'</td><td class="n">'+E.fmt(x.principal,B.L)+'</td><td class="n">'+E.fmt(x.balance,B.L)+'</td></tr>'; }).join('');
  B.shareText=function(){ return $('say').textContent; }; B.saveUrl(IDS); }
B.loadUrl(IDS); B.on(IDS,'input',run); B.on(['cur'],'change',run);
[].forEach.call(document.querySelectorAll('[data-n]'), function(c){ c.onclick=function(){ $('n').value=c.getAttribute('data-n'); run(); }; }); run(); })();
"""
    return X.page("loan-calculator.html", "biz-loan", "Pricing, import & finance", "Loan & Lease Calculator",
                  "See the monthly payment, the total interest and the full repayment table of a business loan or lease.",
                  body, js, strings, None, rule_keys=(), related=("biz-breakeven", "biz-g-finance", "biz-pricing"))


# ─────────────────────────────────────────────────────────────────────────────
# Break-even + CBM
# ─────────────────────────────────────────────────────────────────────────────
def _page_breakeven(X, feeds, prices):
    """break-even-calculator.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Break-even</h2>
    {_field("fixed", "Fixed costs per month (rent, wages, power, loan)", "50.000")}
    <div class="bz-grid bz-g2" style="margin-top:.7rem">
      {_field("price", "Selling price per item (excl. BTW)", "150")}
      {_field("var", "Variable cost per item (purchase, packaging)", "90")}
    </div>
    <div style="margin-top:.7rem">{_field("goal", "Profit you want per month (optional)", "0")}</div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Items to sell per month</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div class="bz-card"><table class="bz-tbl"><tbody id="tbl"></tbody></table>{_share_bar()}</div>
  </div>
</div>
<div class="bz-card">
  <h2>Shipment volume (CBM)</h2>
  <p class="text-sm text-gray-600 mb-3">Freight forwarders charge per cubic metre (CBM) or per cubic foot. Measure one box and count the boxes.</p>
  <div class="bz-grid bz-g3">{_field("l", "Length (cm)", "60", prefix="")}{_field("w", "Width (cm)", "40", prefix="")}{_field("h", "Height (cm)", "40", prefix="")}</div>
  <div class="bz-grid bz-g3" style="margin-top:.7rem">{_field("boxes", "Number of boxes", "10", prefix="", mode="numeric")}{_field("kg", "Weight per box (kg, optional)", "", prefix="")}{_field("rcbm", "Price per CBM (optional)", "", prefix="", money=True)}</div>
  <table class="bz-tbl" style="margin-top:.8rem"><tbody id="cbm"></tbody></table>
</div>
"""
    strings = {"say": "Every item earns {m} towards your fixed costs.", "never": "The price is not above the variable cost, so you never break even.",
               "r_m": "Contribution per item", "r_mp": "Contribution margin", "r_be": "Break-even revenue per month (excl. BTW)", "r_day": "Items per day (26 working days)",
               "c_one": "One box", "c_all": "All boxes", "c_ft": "In cubic feet", "c_kg": "Total weight", "c_vol": "Volume weight (1 CBM = 167 kg, air freight convention)", "c_cost": "Freight at your CBM price"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$;
function run(){ var f=B.amt('fixed'), p=B.amt('price'), v=B.amt('var'), g=B.amt('goal')||0; if(f===null||p===null||v===null){ $('big').textContent='–'; return; }
  var m=p-v; if(m<=0){ $('big').textContent='–'; $('say').textContent=B.T('never'); $('tbl').innerHTML=''; return; }
  var n=Math.ceil((f+g)/m); $('big').textContent=E.fmtNum(n,B.L,0); $('say').textContent=B.T('say',{m:B.srd(m)});
  $('tbl').innerHTML=B.rows([[B.T('r_m'), B.srd(m)],[B.T('r_mp'), E.fmtNum(m*100/p,B.L,1)+'%'],[B.T('r_be'), B.srd(n*p),'bz-tot'],[B.T('r_day'), E.fmtNum(Math.ceil(n/26),B.L,0),'bz-sub']]);
  B.shareText=function(){ return $('big').textContent+' – '+$('say').textContent; }; }
function cbm(){ var l=B.num('l'), w=B.num('w'), h=B.num('h'), n=Math.max(0, Math.floor(B.num('boxes')||0)), kg=B.num('kg'), rc=B.amt('rcbm'); if(!l||!w||!h){ $('cbm').innerHTML=''; return; }
  var one=l*w*h/1e6, all=one*n; var rows=[[B.T('c_one'), E.fmtNum(one,B.L,4)+' m³'],[B.T('c_all'), E.fmtNum(all,B.L,3)+' m³','bz-tot'],[B.T('c_ft'), E.fmtNum(all*35.3147,B.L,2)+' ft³']];
  if(kg) rows.push([B.T('c_kg'), E.fmtNum(kg*n,B.L,1)+' kg']); rows.push([B.T('c_vol'), E.fmtNum(all*167,B.L,1)+' kg','bz-sub']); if(rc) rows.push([B.T('c_cost'), B.srd(Math.round(rc*all))]);
  $('cbm').innerHTML=B.rows(rows); }
B.on(['fixed','price','var','goal'],'input',run); B.on(['l','w','h','boxes','kg','rcbm'],'input',cbm); run(); cbm(); })();
"""
    return X.page("break-even-calculator.html", "biz-breakeven", "Pricing, import & finance", "Break-Even & CBM Calculator",
                  "How many items you must sell to cover your costs, and how big your shipment is in cubic metres.",
                  body, js, strings, None, rule_keys=(), related=("biz-pricing", "biz-import", "biz-loan"))


# ─────────────────────────────────────────────────────────────────────────────
# QR code generator
# ─────────────────────────────────────────────────────────────────────────────
QR_LIB = "/vendor/qrcode-generator-1.4.4/qrcode.js"
BARCODE_LIB = "/vendor/jsbarcode-3.11.6/JsBarcode.all.min.js"


def _page_qr(X, feeds, prices):
    """qr-code-generator.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>What should the QR code do?</h2>
    {_seg("type", [("url", "Website"), ("wifi", "Wi-Fi"), ("wa", "WhatsApp"), ("vcard", "Contact card"), ("tel", "Phone"), ("mail", "E-mail"), ("review", "Google review"), ("geo", "Location"), ("text", "Text")], "url")}
    <div style="margin-top:1rem">
      <div data-t="url">{_text("q_url", "Website address", "https://")}</div>
      <div data-t="wifi" hidden><div class="bz-grid bz-g2">{_text("q_ssid", "Network name (SSID)")}{_text("q_pass", "Password")}
        {_select("q_auth", "Security", [("WPA", "WPA / WPA2 / WPA3"), ("WEP", "WEP"), ("nopass", "No password")], "WPA")}</div>{_check("q_hid", "Hidden network")}
        <p class="bz-src">Guests point their camera at the code and connect without typing the password.</p></div>
      <div data-t="wa" hidden><div class="bz-grid bz-g2">{_text("q_wan", "WhatsApp number", "+597 ", mode="tel")}{_text("q_wam", "Message that is already filled in (optional)")}</div></div>
      <div data-t="vcard" hidden><div class="bz-grid bz-g2">{_text("q_fn", "First name")}{_text("q_ln", "Last name")}{_text("q_org", "Company")}{_text("q_title", "Job title")}
        {_text("q_vtel", "Phone", "+597 ", mode="tel")}{_text("q_vmail", "E-mail", mode="email")}{_text("q_vurl", "Website")}{_text("q_vadr", "Address")}</div></div>
      <div data-t="tel" hidden>{_text("q_tel", "Phone number", "+597 ", mode="tel")}</div>
      <div data-t="mail" hidden><div class="bz-grid bz-g2">{_text("q_mto", "E-mail address", mode="email")}{_text("q_msub", "Subject (optional)")}</div></div>
      <div data-t="review" hidden>{_text("q_rev", "Your Google review link")}
        <p class="bz-src">In Google Business Profile choose &quot;Ask for reviews&quot; and copy the link, then paste it here.</p></div>
      <div data-t="geo" hidden><div class="bz-grid bz-g2">{_text("q_lat", "Latitude", "5.8520", mode="decimal")}{_text("q_lng", "Longitude", "-55.2038", mode="decimal")}</div>
        <p class="bz-src">In Google Maps, press and hold on your location to see these numbers.</p></div>
      <div data-t="text" hidden>{_text("q_text", "Text", ta=True)}</div>
    </div>
    <details class="bz-more"><summary>Style and card</summary>
      <div class="bz-grid bz-g2" style="margin-top:.6rem">
        <div><label class="bz-label" for="q_col">Colour</label><input id="q_col" type="color" value="#1b4332" class="bz-in" style="height:3rem;padding:.2rem"></div>
        {_select("q_ecl", "Error correction", [("M", "Normal"), ("Q", "High"), ("H", "Highest (best for printing)")], "Q")}
        {_text("q_cap", "Text under the code (for the printed card)", "Scan me")}
      </div>
    </details>
  </div>
  <div>
    <div class="bz-card" style="text-align:center">
      <div id="qrbox" style="display:inline-block;background:#fff;padding:16px;border-radius:16px;border:1px solid var(--line)"><div id="qr" style="width:240px;height:240px"></div><div id="cap" style="font-weight:700;margin-top:.4rem"></div></div>
      <p class="bz-src" id="qinfo" style="margin-top:.6rem"></p>
      <div class="bz-acts" style="justify-content:center"><button type="button" class="bz-btn" id="png">Download PNG</button><button type="button" class="bz-btn2" id="svg">Download SVG</button><button type="button" class="bz-btn2" id="prt">Print card</button></div>
    </div>
    <div class="bz-ok">This QR code contains your details directly. It never expires and does not depend on any website, also not on ours.</div>
  </div>
</div>
"""
    strings = {"empty": "Fill in the fields to create your code.", "info": "{n} characters · test it with your phone camera before printing",
               "toolong": "This is too much text for one QR code. Make it shorter.", "loadfail": "The QR tool could not load. Check your connection and reload the page."}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var svgStr='', matrix=null;
function payload(){ var t=B.segVal('type'), v=function(id){ return ($(id).value||'').trim(); };
  switch(t){
    case 'url': var u=v('q_url'); return (u && u!=='https://') ? (/^[a-z]+:/i.test(u)?u:'https://'+u) : '';
    case 'wifi': return v('q_ssid') ? E.wifiPayload(v('q_ssid'), v('q_pass'), $('q_auth').value, $('q_hid').checked) : '';
    case 'wa': var n=E.waNumber(v('q_wan')); return n.length>6 ? 'https://wa.me/'+n+(v('q_wam')?'?text='+encodeURIComponent(v('q_wam')):'') : '';
    case 'vcard': return (v('q_fn')||v('q_ln')||v('q_org')) ? E.vcardPayload({first:v('q_fn'), last:v('q_ln'), org:v('q_org'), title:v('q_title'), tel:v('q_vtel').length>5?v('q_vtel'):'', email:v('q_vmail'), url:v('q_vurl'), adr:v('q_vadr')}) : '';
    case 'tel': var p=v('q_tel').replace(/[^\d+]/g,''); return p.length>5 ? 'tel:'+p : '';
    case 'mail': return v('q_mto') ? 'mailto:'+v('q_mto')+(v('q_msub')?'?subject='+encodeURIComponent(v('q_msub')):'') : '';
    case 'review': return v('q_rev');
    case 'geo': var la=E.parseNum(v('q_lat')), lo=E.parseNum(v('q_lng')); if(la===null||lo===null) return ''; if(v('q_lng').trim().charAt(0)==='-' && lo>0) lo=-lo; if(v('q_lat').trim().charAt(0)==='-' && la>0) la=-la; return 'geo:'+la+','+lo;
    case 'text': return v('q_text');
  } return ''; }
function render(){ var t=B.segVal('type'); [].forEach.call(document.querySelectorAll('[data-t]'), function(s){ s.hidden = s.getAttribute('data-t')!==t; });
  var p=payload(); $('cap').textContent=$('q_cap').value; if(!window.qrcode){ return; }
  if(!p){ $('qr').innerHTML=''; $('qinfo').textContent=B.T('empty'); svgStr=''; return; }
  try{ qrcode.stringToBytes = qrcode.stringToBytesFuncs['UTF-8']; var q=qrcode(0, $('q_ecl').value); q.addData(p, 'Byte'); q.make();
    var n=q.getModuleCount(), col=$('q_col').value; matrix={n:n, q:q}; var d='';
    for(var r=0;r<n;r++) for(var c=0;c<n;c++) if(q.isDark(r,c)) d+='M'+c+' '+r+'h1v1h-1z';
    svgStr='<svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 '+(n+8)+' '+(n+8)+'" shape-rendering="crispEdges"><rect x="-4" y="-4" width="'+(n+8)+'" height="'+(n+8)+'" fill="#fff"/><path d="'+d+'" fill="'+col+'"/></svg>';
    $('qr').innerHTML=svgStr.replace('<svg ','<svg width="240" height="240" '); $('qinfo').textContent=B.T('info',{n:p.length});
  }catch(e){ $('qr').innerHTML=''; svgStr=''; $('qinfo').textContent=B.T('toolong'); } }
function png(size){ return new Promise(function(res){ var img=new Image(); img.onload=function(){ var c=document.createElement('canvas'); var cap=$('q_cap').value.trim(); var extra=cap?Math.round(size*0.14):0;
    c.width=size; c.height=size+extra; var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); x.imageSmoothingEnabled=false; x.drawImage(img,0,0,size,size);
    if(cap){ x.fillStyle='#111'; x.font='bold '+Math.round(size*0.06)+'px sans-serif'; x.textAlign='center'; x.fillText(cap, size/2, size+extra*0.6); } c.toBlob(res,'image/png'); };
  img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svgStr); }); }
$('png').onclick=function(){ if(!svgStr) return; png(1200).then(function(b){ B.download('qr-code.png', b); }); };
$('svg').onclick=function(){ if(!svgStr) return; B.download('qr-code.svg', new Blob([svgStr], {type:'image/svg+xml'})); };
$('prt').onclick=function(){ if(!svgStr) return; var w=window.open('', '_blank'); if(!w) return; w.document.write('<!doctype html><html><head><title>QR</title><style>body{font-family:sans-serif;text-align:center;margin:0;padding:15mm}svg{width:90mm;height:90mm}p{font-size:20pt;font-weight:bold;margin:6mm 0 0}</style></head><body>'+svgStr+'<p>'+B.esc($('q_cap').value)+'</p><script>window.onload=function(){window.print();}<\/script></body></html>'); w.document.close(); };
B.seg('type', render); document.addEventListener('input', function(ev){ if(ev.target.closest('.bz-wrap')) render(); }); document.addEventListener('change', function(ev){ if(ev.target.closest('.bz-wrap')) render(); });
B.loadScript('%QR%').then(render, function(){ $('qinfo').textContent=B.T('loadfail'); }); render(); })();
""".replace("%QR%", QR_LIB)
    faq = [("Do these QR codes expire?", "No. The information is stored in the code itself, so it works forever. Many 'free' QR sites make dynamic codes that stop working after a trial; ours are static."),
           ("How do I make a QR code for my Wi-Fi?", "Choose Wi-Fi, type the network name and password exactly as they are set on your router, and print the code. Guests scan it with the phone camera to connect."),
           ("Is my Wi-Fi password sent to your website?", "No. The code is made in your own browser; nothing is sent anywhere.")]
    return X.page("qr-code-generator.html", "biz-qr", "Office tools", "QR Code Generator",
                  "Free QR codes for your website, Wi-Fi, WhatsApp, contact card, Google reviews or location. They never expire.",
                  body, js, strings, faq, rule_keys=(), related=("biz-card", "biz-barcode", "biz-pdf"))


# ─────────────────────────────────────────────────────────────────────────────
# Barcode & price labels
# ─────────────────────────────────────────────────────────────────────────────
def _page_barcode(X, feeds, prices):
    """barcode-generator.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Barcode</h2>
    {_seg("fmt", [("EAN13", "EAN-13 (products)"), ("CODE128", "Code128 (any text)")], "EAN13", "Type")}
    <div class="bz-grid bz-g2" style="margin-top:.8rem">
      {_text("code", "Code", "871125300120", mode="numeric")}
      {_text("name", "Product name (on the label)", "Voorbeeld product")}
      {_field("price", "Price on the label (SRD)", "25")}
      {_field("copies", "How many labels", "24", prefix="", mode="numeric")}
    </div>
    <div id="msg"></div>
    <p class="bz-src" style="margin-top:.6rem">EAN-13 codes on products you sell in shops are issued by GS1. For your own shelf labels or stock you can use Code128 with your own article numbers.</p>
  </div>
  <div>
    <div class="bz-card" style="text-align:center"><svg id="bc"></svg>
      <div class="bz-acts" style="justify-content:center"><button type="button" class="bz-btn" id="png">Download PNG</button><button type="button" class="bz-btn2" id="sheet">Print label sheet (A4)</button></div></div>
  </div>
</div>
"""
    strings = {"ean_fix": "EAN-13 needs 12 digits plus a check digit. The check digit for these 12 digits is {c}: full code {f}.",
               "ean_bad": "The last digit should be {c}. This code is not a valid EAN-13.", "ean_ok": "Valid EAN-13 code.",
               "bad": "This code cannot be drawn. Check the digits.", "loadfail": "The barcode tool could not load. Check your connection and reload the page."}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$; var code='';
function draw(){ if(!window.JsBarcode) return; var f=B.segVal('fmt'), v=$('code').value.replace(/\s/g,''), m=$('msg'); code='';
  if(f==='EAN13'){ var d=v.replace(/\D/g,''); if(d.length===12){ var c=E.ean13Check(d); code=d+c; m.innerHTML='<div class="bz-ok">'+B.esc(B.T('ean_fix',{c:c, f:code}))+'</div>'; }
    else if(d.length===13){ var c2=E.ean13Check(d.slice(0,12)); if(String(c2)!==d.charAt(12)){ m.innerHTML='<div class="bz-warn">'+B.esc(B.T('ean_bad',{c:c2}))+'</div>'; $('bc').innerHTML=''; return; } code=d; m.innerHTML='<div class="bz-ok">'+B.esc(B.T('ean_ok'))+'</div>'; }
    else { m.innerHTML='<div class="bz-warn">'+B.esc(B.T('ean_fix',{c:'?', f:'…'}))+'</div>'; $('bc').innerHTML=''; return; } }
  else { code=v; m.innerHTML=''; if(!code){ $('bc').innerHTML=''; return; } }
  try{ JsBarcode('#bc', code, {format:f, width:2, height:70, fontSize:16, margin:10}); }catch(e){ m.innerHTML='<div class="bz-warn">'+B.esc(B.T('bad'))+'</div>'; code=''; } }
$('png').onclick=function(){ if(!code) return; var s=new XMLSerializer().serializeToString($('bc')); var img=new Image(); img.onload=function(){ var c=document.createElement('canvas'); c.width=img.width*3; c.height=img.height*3; var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); x.scale(3,3); x.drawImage(img,0,0); c.toBlob(function(b){ B.download('barcode-'+code+'.png', b); }); }; img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(s); };
$('sheet').onclick=function(){ if(!code) return; var n=Math.max(1, Math.min(240, Math.floor(B.num('copies')||1))); var s=new XMLSerializer().serializeToString($('bc'));
  var p=B.amt('price'); var price = p===null?'':'SRD '+E.fmt(p,B.L); var name=B.esc($('name').value);
  var cell='<div class="l"><div class="n">'+name+'</div><div class="p">'+B.esc(price)+'</div>'+s+'</div>'; var w=window.open('', '_blank'); if(!w) return;
  w.document.write('<!doctype html><html><head><title>Labels</title><style>@page{size:A4;margin:8mm}body{margin:0;font-family:sans-serif}.g{display:grid;grid-template-columns:repeat(3,1fr);gap:0}.l{height:36mm;box-sizing:border-box;border:.2mm dashed #bbb;padding:2mm;text-align:center;overflow:hidden;break-inside:avoid}.n{font-size:9pt;font-weight:bold;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.p{font-size:14pt;font-weight:bold}svg{max-width:100%;height:17mm}</style></head><body><div class="g">'+new Array(n+1).join(cell)+'</div><script>window.onload=function(){window.print();}<\/script></body></html>'); w.document.close(); };
B.seg('fmt', draw); B.on(['code','name','price','copies'],'input',draw);
B.loadScript('%BC%').then(draw, function(){ $('msg').innerHTML='<div class="bz-warn">'+B.esc(B.T('loadfail'))+'</div>'; }); })();
""".replace("%BC%", BARCODE_LIB)
    return X.page("barcode-generator.html", "biz-barcode", "Office tools", "Barcode & Price Label Maker",
                  "Make EAN-13 or Code128 barcodes and print a full A4 sheet of price labels.",
                  body, js, strings, None, rule_keys=(), related=("biz-qr", "biz-pricing", "biz-prices"))


# ─────────────────────────────────────────────────────────────────────────────
# PDF tools (pdf-lib + pdf.js, all in the browser, nothing uploaded)
# ─────────────────────────────────────────────────────────────────────────────
PDFLIB = "/vendor/pdf-lib-1.17.1/pdf-lib.min.js"
PDFJS = "/vendor/pdfjs-3.11.174/pdf.min.js"
PDFJS_WORKER = "/vendor/pdfjs-3.11.174/pdf.worker.min.js"


def _page_pdf(X, feeds, prices):
    """pdf-tools.html"""
    body = f"""
{_privacy()}
<div class="bz-card">
  <h2>What do you want to do?</h2>
  {_seg("tool", [("merge", "Combine PDFs"), ("org", "Rotate, sort or delete pages"), ("ext", "Split / pick pages"), ("img", "Photos to PDF"), ("sign", "Sign or stamp"), ("num", "Page numbers"), ("toimg", "PDF to images")], "merge")}
  <label class="bz-drop" id="drop" style="display:block;margin-top:1rem">
    <input type="file" id="file" accept="application/pdf,.pdf" multiple hidden>
    <b style="font-size:1.05rem;color:var(--forest)" id="dropt">Choose PDF files</b><br><span class="bz-src">or drag them here</span>
  </label>
  <div id="pmsg" aria-live="polite"></div>
</div>

<div data-t="merge" class="bz-card" hidden>
  <h2>Files, in order</h2>
  <ol id="mlist" style="padding-left:0;list-style:none"></ol>
  <p class="bz-src" id="mnone">No files yet. Add two or more PDFs.</p>
  <div class="bz-acts"><button type="button" class="bz-btn" id="mgo">Combine and download</button></div>
</div>

<div data-t="org" class="bz-card" hidden>
  <h2>Pages</h2>
  <p class="bz-src">Turn, move or remove pages, then download the new PDF.</p>
  <div id="ogrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:.8rem;margin-top:.8rem"></div>
  <div class="bz-acts"><button type="button" class="bz-btn" id="ogo">Download new PDF</button><button type="button" class="bz-btn2" id="orall">Turn all pages</button></div>
</div>

<div data-t="ext" class="bz-card" hidden>
  <h2>Which pages?</h2>
  {_seg("emode", [("keep", "Keep only these pages"), ("drop", "Remove these pages")], "keep")}
  <div style="margin-top:.8rem">{_text("erange", "Page numbers", "", hint="For example 1-3, 5, 8-10")}</div>
  <p class="bz-src" id="einfo"></p>
  <div class="bz-acts"><button type="button" class="bz-btn" id="ego">Download</button></div>
</div>

<div data-t="img" class="bz-card" hidden>
  <h2>Photos, in order</h2>
  <div id="ilist" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:.7rem"></div>
  <p class="bz-src" id="inone">No photos yet. Add photos of receipts, documents or products.</p>
  <div class="bz-grid bz-g2" style="margin-top:.8rem">
    {_seg("isize", [("a4", "A4"), ("letter", "Letter"), ("fit", "Same as photo")], "a4", "Page size")}
    <div style="padding-top:1.2rem">{_check("imarg", "White margin around each photo", True)}</div>
  </div>
  <div class="bz-acts"><button type="button" class="bz-btn" id="igo">Make PDF</button></div>
</div>

<div data-t="sign" class="bz-card" hidden>
  <h2>1. Make your signature or stamp</h2>
  {_seg("smode", [("draw", "Draw"), ("type", "Type your name"), ("stamp", "Text stamp")], "draw")}
  <div data-s="draw" style="margin-top:.8rem">
    <canvas id="pad" width="600" height="200" style="width:100%;max-width:600px;height:auto;aspect-ratio:3/1;border:1.5px dashed #CDBF9F;border-radius:12px;background:#fff;touch-action:none;cursor:crosshair"></canvas>
    <div class="bz-acts"><button type="button" class="bz-btn2" id="padclr">Clear</button></div>
  </div>
  <div data-s="type" hidden style="margin-top:.8rem">{_text("sname", "Your name")}</div>
  <div data-s="stamp" hidden style="margin-top:.8rem"><div class="bz-grid bz-g2">{_text("stxt", "Stamp text")}<div style="padding-top:1.2rem">{_check("sdate", "Add today's date", True)}</div></div></div>
  <div class="bz-grid bz-g2" style="margin-top:.8rem">
    {_select("scol", "Colour", [("#1a3a8f", "Blue"), ("#111111", "Black"), ("#b3261e", "Red")], "#1a3a8f")}
    <div><label class="bz-label" for="ssz">Size</label><input type="range" id="ssz" min="10" max="60" value="28" style="width:100%"></div>
  </div>
  <h2 style="margin-top:1.2rem">2. Tap on the page where it should go</h2>
  <div class="bz-grid bz-g2">{_select("spage", "Page", [("1", "1")], "1")}<div></div></div>
  <div style="margin-top:.7rem;overflow:hidden"><canvas id="spv" style="max-width:100%;border:1px solid var(--line);border-radius:8px;cursor:copy;touch-action:manipulation"></canvas></div>
  <p class="bz-src" id="sinfo"></p>
  <div class="bz-acts"><button type="button" class="bz-btn" id="sgo">Download signed PDF</button><button type="button" class="bz-btn2" id="sundo">Undo last</button></div>
</div>

<div data-t="num" class="bz-card" hidden>
  <h2>Page numbers</h2>
  <div class="bz-grid bz-g2">
    {_seg("npos", [("bc", "Bottom centre"), ("br", "Bottom right"), ("tr", "Top right")], "bc", "Position")}
    {_seg("nfmt", [("n", "1, 2, 3"), ("nt", "Page 1 of 10")], "n", "Style")}
    {_field("nstart", "Start at number", "1", prefix="", mode="numeric")}
    <div style="padding-top:1.2rem">{_check("nskip", "No number on the first page (cover)")}</div>
  </div>
  <div class="bz-acts"><button type="button" class="bz-btn" id="ngo">Add numbers and download</button></div>
</div>

<div data-t="toimg" class="bz-card" hidden>
  <h2>Pages as images</h2>
  {_seg("tfmt", [("jpg", "JPG (small)"), ("png", "PNG (sharp)")], "jpg", "Format")}
  <div class="bz-acts"><button type="button" class="bz-btn" id="tgo">Make images</button><button type="button" class="bz-btn2" id="tall" hidden>Download all</button></div>
  <div id="tgrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(140px,1fr));gap:.8rem;margin-top:.8rem"></div>
</div>
"""
    strings = {
        "pick_pdf": "Choose PDF files", "pick_one": "Choose a PDF file", "pick_img": "Choose photos",
        "loadfail": "The PDF tools could not load. Check your connection and reload the page.",
        "locked": "This PDF is protected with a password. Open it in your PDF reader, save a copy without a password, and try again.",
        "broken": "This file could not be read as a PDF.", "notpdf": "{f} is not a PDF and was skipped.", "notimg": "{f} is not a photo and was skipped.",
        "working": "Working…", "done": "Done. Your file is downloading.", "need2": "Add at least two PDFs.", "needpdf": "First choose a PDF.",
        "needimg": "First add one or more photos.", "pages": "{n} pages", "page_n": "Page {n}", "range_bad": "Check the page numbers. This PDF has {n} pages.",
        "range_ok": "The new PDF will have {k} of {n} pages.", "range_none": "That would leave no pages.", "many": "This PDF has {n} pages; only the first {m} are shown.",
        "up": "Move up", "down": "Move down", "remove": "Remove", "left": "Turn left", "right": "Turn right", "back": "Move back", "fwd": "Move forward",
        "sign_empty": "First draw, type or set your signature or stamp above.", "sign_tap": "Tap on the page to place it. {k} placed so far.",
        "sign_none": "Nothing placed yet. Tap on the page.", "stamp_def": "PAID", "pg_of": "Page {n} of {t}", "img_dl": "Download",
        "big": "Large file: this can take a while on a phone.", "sfx_merge": "combined", "sfx_org": "edited", "sfx_ext": "pages",
        "sfx_img": "photos", "sfx_sign": "signed", "sfx_num": "numbered", "sfx_page": "page",
    }
    js = r"""
(function(){ var B=BZ,$=B.$,T=B.T;
var PL='""" + PDFLIB + r"""', PJ='""" + PDFJS + r"""', PW='""" + PDFJS_WORKER + r"""';
var memo={}; function ld(src){ if(!memo[src]) memo[src]=B.loadScript(src).catch(function(e){ delete memo[src]; throw e; }); return memo[src]; }
function libs(js){ var p=ld(PL); if(js) p=p.then(function(){ return ld(PJ); }).then(function(){ pdfjsLib.GlobalWorkerOptions.workerSrc=PW; });
  return p.catch(function(e){ msg(T('loadfail'),1); throw e; }); }
function msg(t,bad){ $('pmsg').innerHTML=t?'<div class="'+(bad?'bz-warn':'bz-ok')+'">'+B.esc(t)+'</div>':''; }
function base(n){ return String(n||'document').replace(/\.[^.]+$/,'').replace(/[^\w\-]+/g,'_').slice(0,60)||'document'; }
function savePdf(bytes, suffix){ B.download(base(S.name||(M[0]&&M[0].name))+'-'+T('sfx_'+suffix).replace(/\s+/g,'-')+'.pdf', new Blob([bytes],{type:'application/pdf'})); msg(T('done')); }
function copyBuf(b){ return new Uint8Array(b.slice(0)); }
function loadPdf(buf){ return PDFLib.PDFDocument.load(copyBuf(buf)).catch(function(e){ throw new Error(/encrypt/i.test(e&&e.message)?T('locked'):T('broken')); }); }
function jsDoc(buf){ return pdfjsLib.getDocument({data:copyBuf(buf), isEvalSupported:false}).promise.catch(function(e){ throw new Error(e&&e.name==='PasswordException'?T('locked'):T('broken')); }); }
function fail(e){ msg((e&&e.message)||T('broken'),1); }
function isPdf(f){ return /pdf$/i.test(f.type)||/\.pdf$/i.test(f.name); }
var M=[], S={name:'',buf:null,n:0}, I=[], O=[], thumbs=[], tool='merge';
var ONE={org:1,ext:1,sign:1,num:1,toimg:1};

// ---------- file intake ----------
function setTool(v){ tool=v; [].forEach.call(document.querySelectorAll('[data-t]'), function(p){ p.hidden=p.getAttribute('data-t')!==v; });
  var f=$('file'); f.accept = v==='img' ? 'image/*' : 'application/pdf,.pdf'; f.multiple = (v==='merge'||v==='img');
  $('dropt').textContent = T(v==='img'?'pick_img':(v==='merge'?'pick_pdf':'pick_one')); msg('');
  if(ONE[v] && S.buf) openSingle(); }
B.seg('tool', setTool);
function take(files){ files=[].slice.call(files||[]); if(!files.length) return; msg('');
  if(tool==='merge'){ var bad=[]; Promise.all(files.map(function(f){ if(!isPdf(f)){ bad.push(f.name); return null; } return f.arrayBuffer().then(function(b){ return {name:f.name,buf:b,size:f.size}; }); }))
      .then(function(list){ list.forEach(function(x){ if(x) M.push(x); }); drawMerge(); if(bad.length) msg(T('notpdf',{f:bad.join(', ')}),1); }); return; }
  if(tool==='img'){ var badi=[]; files.forEach(function(f){ if(!/^image\//.test(f.type)){ badi.push(f.name); return; } I.push({name:f.name, url:URL.createObjectURL(f)}); }); drawImgs(); if(badi.length) msg(T('notimg',{f:badi.join(', ')}),1); return; }
  var f=files[0]; if(!isPdf(f)){ msg(T('notpdf',{f:f.name}),1); return; }
  if(f.size>60*1024*1024) msg(T('big'));
  f.arrayBuffer().then(function(b){ S={name:f.name,buf:b,n:0,doc:null}; thumbs=[]; O=[]; P=[]; pageImg=null;
    made.forEach(function(m){ URL.revokeObjectURL(m.url); }); made=[]; $('tgrid').innerHTML=''; $('tall').hidden=true; openSingle(); }); }
$('file').addEventListener('change', function(){ take(this.files); this.value=''; });
var drop=$('drop');
['dragenter','dragover'].forEach(function(ev){ drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.add('bz-hot'); }); });
['dragleave','drop'].forEach(function(ev){ drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.remove('bz-hot'); }); });
drop.addEventListener('drop', function(e){ take(e.dataTransfer.files); });

// ---------- merge ----------
function listBtns(i,n){ return '<button type="button" class="bz-btn2" data-a="up" data-i="'+i+'" aria-label="'+B.esc(T('up'))+'"'+(i===0?' disabled':'')+'>&uarr;</button>'+
  '<button type="button" class="bz-btn2" data-a="down" data-i="'+i+'" aria-label="'+B.esc(T('down'))+'"'+(i===n-1?' disabled':'')+'>&darr;</button>'+
  '<button type="button" class="bz-x" data-a="rm" data-i="'+i+'" aria-label="'+B.esc(T('remove'))+'">&times;</button>'; }
function move(arr,a,i){ if(a==='rm') arr.splice(i,1); else { var j=a==='up'?i-1:i+1; if(j<0||j>=arr.length) return; var t=arr[i]; arr[i]=arr[j]; arr[j]=t; } }
function drawMerge(){ $('mnone').hidden=M.length>0;
  $('mlist').innerHTML=M.map(function(m,i){ return '<li style="display:flex;gap:.5rem;align-items:center;padding:.45rem 0;border-bottom:1px solid var(--line)"><span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" translate="no">'+(i+1)+'. '+B.esc(m.name)+'</span><span class="bz-src">'+(m.size/1048576).toFixed(1)+' MB</span>'+listBtns(i,M.length)+'</li>'; }).join(''); }
$('mlist').addEventListener('click', function(e){ var b=e.target.closest('[data-a]'); if(!b) return; move(M,b.getAttribute('data-a'),+b.getAttribute('data-i')); drawMerge(); });
$('mgo').onclick=function(){ if(M.length<2){ msg(T('need2'),1); return; } msg(T('working'));
  libs(false).then(function(){ return PDFLib.PDFDocument.create(); }).then(function(out){
    return M.reduce(function(p,m){ return p.then(function(){ return loadPdf(m.buf); }).then(function(src){ return out.copyPages(src, src.getPageIndices()); }).then(function(pg){ pg.forEach(function(x){ out.addPage(x); }); }); }, Promise.resolve())
      .then(function(){ return out.save(); }); }).then(function(bytes){ savePdf(bytes,'merge'); }).catch(fail); };

// ---------- single-PDF tools ----------
function refresh(){ if(tool==='org') drawOrg(); if(tool==='ext') extInfo(); if(tool==='sign') renderSign(); }
function openSingle(){ if(!S.buf){ return; } if(S.doc){ refresh(); return; } var mine=S; msg(T('working'));
  libs(true).then(function(){ return jsDoc(mine.buf); }).then(function(doc){ if(mine!==S) return; S.n=doc.numPages; S.doc=doc; msg('');
    O=[]; for(var i=0;i<S.n;i++) O.push({i:i,rot:0});
    $('spage').innerHTML=''; for(var k=1;k<=S.n;k++){ var o=document.createElement('option'); o.value=k; o.textContent=k; $('spage').appendChild(o); }
    refresh(); }).catch(fail); }
function needOne(){ if(!S.buf){ msg(T('needpdf'),1); return false; } return true; }

// organize
var MAXT=300;
function thumb(i){ if(thumbs[i]) return Promise.resolve(thumbs[i]);
  var doc=S.doc; return doc.getPage(i+1).then(function(pg){ var v=pg.getViewport({scale:1}); var sc=240/Math.max(v.width,v.height); var vp=pg.getViewport({scale:sc});
    var c=document.createElement('canvas'); c.width=Math.ceil(vp.width); c.height=Math.ceil(vp.height); c.style.maxWidth='100%'; c.style.maxHeight='150px'; c.style.transition='transform .2s';
    return pg.render({canvasContext:c.getContext('2d'), viewport:vp}).promise.then(function(){ if(doc===S.doc) thumbs[i]=c; return c; }); }); }
function drawOrg(){ var g=$('ogrid'); g.innerHTML=''; if(S.n>MAXT) msg(T('many',{n:S.n,m:MAXT}));
  O.slice(0,MAXT).forEach(function(o,k){ var d=document.createElement('div'); d.style.cssText='border:1px solid var(--line);border-radius:12px;padding:.5rem;text-align:center;background:#fff';
    d.innerHTML='<div class="th" style="height:156px;display:flex;align-items:center;justify-content:center"></div><div class="bz-src" style="margin:.3rem 0">'+B.esc(T('page_n',{n:o.i+1}))+'</div>'+
      '<div style="display:flex;justify-content:center;gap:.15rem;flex-wrap:wrap">'+
      '<button type="button" class="bz-chip" data-o="l" data-k="'+k+'" aria-label="'+B.esc(T('back'))+'">&larr;</button>'+
      '<button type="button" class="bz-chip" data-o="rl" data-k="'+k+'" aria-label="'+B.esc(T('left'))+'">&#8634;</button>'+
      '<button type="button" class="bz-chip" data-o="rr" data-k="'+k+'" aria-label="'+B.esc(T('right'))+'">&#8635;</button>'+
      '<button type="button" class="bz-chip" data-o="r" data-k="'+k+'" aria-label="'+B.esc(T('fwd'))+'">&rarr;</button>'+
      '<button type="button" class="bz-x" data-o="x" data-k="'+k+'" aria-label="'+B.esc(T('remove'))+'">&times;</button></div>';
    g.appendChild(d); thumb(o.i).then(function(c){ c.style.transform='rotate('+o.rot+'deg)'; var th=d.querySelector('.th'); th.innerHTML=''; th.appendChild(c); }); }); }
$('ogrid').addEventListener('click', function(e){ var b=e.target.closest('[data-o]'); if(!b) return; var k=+b.getAttribute('data-k'), a=b.getAttribute('data-o');
  if(a==='rl') O[k].rot=(O[k].rot+270)%360; else if(a==='rr') O[k].rot=(O[k].rot+90)%360; else if(a==='x') O.splice(k,1);
  else { var j=a==='l'?k-1:k+1; if(j<0||j>=O.length) return; var t=O[k]; O[k]=O[j]; O[j]=t; } drawOrg(); });
$('orall').onclick=function(){ O.forEach(function(o){ o.rot=(o.rot+90)%360; }); drawOrg(); };
$('ogo').onclick=function(){ if(!needOne()) return; if(!O.length){ msg(T('range_none'),1); return; } msg(T('working'));
  Promise.all([loadPdf(S.buf), PDFLib.PDFDocument.create()]).then(function(r){ var src=r[0], out=r[1];
    return out.copyPages(src, O.map(function(o){ return o.i; })).then(function(pg){ pg.forEach(function(p,k){ var a=(p.getRotation().angle+O[k].rot)%360; p.setRotation(PDFLib.degrees(a)); out.addPage(p); }); return out.save(); });
  }).then(function(b){ savePdf(b,'org'); }).catch(fail); };

// extract
function parseRange(s,n){ s=String(s||'').replace(/\s+/g,''); if(!s) return null; var out=[];
  var parts=s.split(/[,;]+/); for(var i=0;i<parts.length;i++){ var p=parts[i]; if(!p) continue; var m=p.match(/^(\d+)(?:-(\d*))?$/); if(!m) return null;
    var a=+m[1], b=m[2]===undefined?a:(m[2]===''?n:+m[2]); if(a<1||b>n||a>b) return null; for(var k=a;k<=b;k++) if(out.indexOf(k-1)<0) out.push(k-1); } return out; }
function extSel(){ var r=parseRange($('erange').value,S.n); if(!r) return null; if(B.segVal('emode')==='drop'){ var keep=[]; for(var i=0;i<S.n;i++) if(r.indexOf(i)<0) keep.push(i); return keep; } return r; }
function extInfo(){ if(!S.n){ $('einfo').textContent=''; return; } if(!$('erange').value.trim()){ $('einfo').textContent=T('pages',{n:S.n}); return; }
  var k=extSel(); $('einfo').textContent = k===null ? T('range_bad',{n:S.n}) : (k.length ? T('range_ok',{k:k.length,n:S.n}) : T('range_none')); }
$('erange').addEventListener('input', extInfo); B.seg('emode', extInfo);
$('ego').onclick=function(){ if(!needOne()) return; var k=extSel(); if(k===null){ msg(T('range_bad',{n:S.n}),1); return; } if(!k.length){ msg(T('range_none'),1); return; } msg(T('working'));
  Promise.all([loadPdf(S.buf), PDFLib.PDFDocument.create()]).then(function(r){ return r[1].copyPages(r[0],k).then(function(pg){ pg.forEach(function(p){ r[1].addPage(p); }); return r[1].save(); }); })
    .then(function(b){ savePdf(b,'ext'); }).catch(fail); };

// ---------- photos to PDF ----------
function drawImgs(){ $('inone').hidden=I.length>0;
  $('ilist').innerHTML=I.map(function(m,i){ return '<div style="border:1px solid var(--line);border-radius:12px;padding:.4rem;text-align:center;background:#fff"><img src="'+m.url+'" alt="" style="height:100px;width:100%;object-fit:contain"><div style="display:flex;justify-content:center;gap:.1rem;margin-top:.3rem">'+listBtns(i,I.length).replace(/&uarr;/,'&larr;').replace(/&darr;/,'&rarr;')+'</div></div>'; }).join(''); }
$('ilist').addEventListener('click', function(e){ var b=e.target.closest('[data-a]'); if(!b) return; var i=+b.getAttribute('data-i'); if(b.getAttribute('data-a')==='rm') URL.revokeObjectURL(I[i].url); move(I,b.getAttribute('data-a'),i); drawImgs(); });
function jpegOf(url){ return new Promise(function(res,rej){ var im=new Image(); im.onload=function(){ var s=Math.min(1, 2400/Math.max(im.naturalWidth,im.naturalHeight)); var c=document.createElement('canvas');
    c.width=Math.round(im.naturalWidth*s); c.height=Math.round(im.naturalHeight*s); var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); x.drawImage(im,0,0,c.width,c.height);
    c.toBlob(function(bl){ if(!bl) return rej(new Error(T('broken'))); bl.arrayBuffer().then(function(b){ res({b:b,w:c.width,h:c.height}); }); }, 'image/jpeg', 0.85); }; im.onerror=function(){ rej(new Error(T('broken'))); }; im.src=url; }); }
$('igo').onclick=function(){ if(!I.length){ msg(T('needimg'),1); return; } msg(T('working'));
  libs(false).then(function(){ return PDFLib.PDFDocument.create(); }).then(function(out){ var size=B.segVal('isize'), mg=$('imarg').checked?28:0;
    return I.reduce(function(p,m){ return p.then(function(){ return jpegOf(m.url); }).then(function(j){ return out.embedJpg(j.b).then(function(img){
      var pw, ph; if(size==='fit'){ pw=595.28; ph=pw*j.h/j.w; if(ph>2000){ ph=2000; pw=ph*j.w/j.h; } } else { var d=size==='a4'?[595.28,841.89]:[612,792]; if(j.w>j.h){ pw=d[1]; ph=d[0]; } else { pw=d[0]; ph=d[1]; } }
      var aw=pw-2*mg, ah=ph-2*mg, sc=Math.min(aw/j.w, ah/j.h), w=j.w*sc, h=j.h*sc; var pg=out.addPage([pw,ph]); pg.drawImage(img,{x:(pw-w)/2, y:(ph-h)/2, width:w, height:h}); }); }); }, Promise.resolve())
      .then(function(){ return out.save(); }); }).then(function(b){ B.download(base(I[0].name)+'-'+T('sfx_img')+'.pdf', new Blob([b],{type:'application/pdf'})); msg(T('done')); }).catch(fail); };

// ---------- sign / stamp ----------
// Display coordinates (as the page is shown, top-left origin, PDF points) -> PDF user space,
// for any /Rotate and a crop box that does not start at 0,0.
function toUser(page, dx, dy){ var cb=page.getCropBox(), r=((page.getRotation().angle%360)+360)%360, x0=cb.x, y0=cb.y, w=cb.width, h=cb.height;
  if(r===90) return {x:x0+dy, y:y0+dx}; if(r===180) return {x:x0+w-dx, y:y0+dy}; if(r===270) return {x:x0+w-dy, y:y0+h-dx}; return {x:x0+dx, y:y0+h-dy}; }
function dispSize(page){ var cb=page.getCropBox(), r=((page.getRotation().angle%360)+360)%360; return r%180 ? {w:cb.height,h:cb.width} : {w:cb.width,h:cb.height}; }
var pad=$('pad'), px=pad.getContext('2d'), inked=false, drawing=false;
function padPos(e){ var r=pad.getBoundingClientRect(); return {x:(e.clientX-r.left)*pad.width/r.width, y:(e.clientY-r.top)*pad.height/r.height}; }
pad.addEventListener('pointerdown', function(e){ drawing=true; pad.setPointerCapture(e.pointerId); var p=padPos(e); px.beginPath(); px.moveTo(p.x,p.y); px.lineTo(p.x+0.1,p.y+0.1); px.lineWidth=3.2; px.lineCap='round'; px.lineJoin='round'; px.strokeStyle='#000'; px.stroke(); inked=true; });
pad.addEventListener('pointermove', function(e){ if(!drawing) return; var p=padPos(e); px.lineTo(p.x,p.y); px.stroke(); });
['pointerup','pointercancel'].forEach(function(ev){ pad.addEventListener(ev, function(){ drawing=false; renderSign(); }); });
$('padclr').onclick=function(){ px.clearRect(0,0,pad.width,pad.height); inked=false; renderSign(); };
B.seg('smode', function(v){ [].forEach.call(document.querySelectorAll('[data-s]'), function(p){ p.hidden=p.getAttribute('data-s')!==v; }); renderSign(); });
$('stxt').value=T('stamp_def');
['sname','stxt','scol','ssz','sdate'].forEach(function(id){ $(id).addEventListener(id==='scol'||id==='sdate'?'change':'input', renderSign); });
function trimCanvas(c){ var x=c.getContext('2d'), d=x.getImageData(0,0,c.width,c.height).data, t=c.height, l=c.width, b=-1, r=-1;
  for(var y=0;y<c.height;y++) for(var xx=0;xx<c.width;xx++) if(d[(y*c.width+xx)*4+3]>8){ if(y<t)t=y; if(y>b)b=y; if(xx<l)l=xx; if(xx>r)r=xx; }
  if(r<0) return null; var o=document.createElement('canvas'); o.width=r-l+9; o.height=b-t+9; o.getContext('2d').drawImage(c,l-4,t-4,o.width,o.height,0,0,o.width,o.height); return o; }
function stampCanvas(){ var mode=B.segVal('smode'), col=$('scol').value, c=document.createElement('canvas'), x=c.getContext('2d');
  if(mode==='draw'){ if(!inked) return null; c.width=pad.width; c.height=pad.height; x.drawImage(pad,0,0); x.globalCompositeOperation='source-in'; x.fillStyle=col; x.fillRect(0,0,c.width,c.height); return trimCanvas(c); }
  if(mode==='type'){ var n=$('sname').value.trim(); if(!n) return null; c.width=1400; c.height=260; x.font='italic 150px "Segoe Script","Brush Script MT","Lucida Handwriting",cursive'; x.fillStyle=col; x.textBaseline='middle'; x.fillText(n,20,130); return trimCanvas(c); }
  var s=$('stxt').value.trim(); if(!s) return null; var dt=$('sdate').checked?B.fmtDay(B.today()):''; c.width=1600; c.height=400; x.font='bold 110px Arial,Helvetica,sans-serif';
  var w1=x.measureText(s).width; x.font='bold 60px Arial,Helvetica,sans-serif'; var w2=dt?x.measureText(dt).width:0; var W=Math.max(w1,w2)+80, Hh=dt?250:170; c.width=Math.min(1600,Math.ceil(W)); c.height=Hh;
  x.strokeStyle=col; x.fillStyle=col; x.lineWidth=10; x.strokeRect(8,8,c.width-16,c.height-16); x.textAlign='center'; x.textBaseline='middle';
  x.font='bold 110px Arial,Helvetica,sans-serif'; x.fillText(s,c.width/2,dt?95:c.height/2); if(dt){ x.font='bold 60px Arial,Helvetica,sans-serif'; x.fillText(dt,c.width/2,190); } return c; }
var P=[], spv=$('spv'), sx=spv.getContext('2d'), pageImg=null, pageDoc=null, pageScale=1, pageDisp=null, curPage=0;
function renderSign(){ if(tool!=='sign') return; if(!S.doc){ $('sinfo').textContent=''; return; } var k=(+$('spage').value||1)-1;
  var draw=function(){ sx.clearRect(0,0,spv.width,spv.height); sx.drawImage(pageImg,0,0);
    P.forEach(function(p){ if(p.page!==k) return; sx.drawImage(p.c, p.x*pageScale, p.y*pageScale, p.w*pageScale, p.h*pageScale); });
    $('sinfo').textContent = P.length ? T('sign_tap',{k:P.length}) : (stampCanvas() ? T('sign_none') : T('sign_empty')); };
  if(pageImg && curPage===k && pageDoc===S.doc){ draw(); return; }
  var doc=S.doc; doc.getPage(k+1).then(function(pg){ var v=pg.getViewport({scale:1}); var wrap=spv.parentNode.clientWidth||600; var psc=Math.min(1.6, wrap/v.width); var vp=pg.getViewport({scale:psc});
    var c=document.createElement('canvas'); c.width=Math.floor(vp.width); c.height=Math.floor(vp.height); var disp={w:v.width,h:v.height}, sc=psc;
    return pg.render({canvasContext:c.getContext('2d'), viewport:vp}).promise.then(function(){ if(doc!==S.doc || (+$('spage').value||1)-1!==k) return; pageImg=c; curPage=k; pageDoc=doc; pageDisp=disp; pageScale=sc; spv.width=c.width; spv.height=c.height; draw(); }); }).catch(fail); }
$('spage').addEventListener('change', function(){ pageImg=null; renderSign(); });
spv.addEventListener('click', function(e){ if(!pageImg||pageDoc!==S.doc) return; var st=stampCanvas(); if(!st){ msg(T('sign_empty'),1); return; } msg('');
  var r=spv.getBoundingClientRect(), cx=(e.clientX-r.left)*spv.width/r.width/pageScale, cy=(e.clientY-r.top)*spv.height/r.height/pageScale;
  var w=pageDisp.w*(+$('ssz').value)/100, h=w*st.height/st.width; P.push({page:curPage, c:st, x:cx-w/2, y:cy-h/2, w:w, h:h, dw:pageDisp.w}); renderSign(); });
$('sundo').onclick=function(){ P.pop(); renderSign(); };
$('sgo').onclick=function(){ if(!needOne()) return; if(!P.length){ msg(T('sign_none'),1); return; } msg(T('working'));
  loadPdf(S.buf).then(function(doc){ var pages=doc.getPages();
    return P.reduce(function(pr,p){ return pr.then(function(){ return new Promise(function(res){ p.c.toBlob(function(bl){ bl.arrayBuffer().then(res); }, 'image/png'); }); })
      .then(function(b){ return doc.embedPng(b); }).then(function(img){ var pg=pages[p.page]; var d=dispSize(pg); var sx2=d.w/p.dw; // pdf.js and pdf-lib page sizes agree; guard anyway
        var a=toUser(pg, p.x*sx2, (p.y+p.h)*sx2); pg.drawImage(img,{x:a.x, y:a.y, width:p.w*sx2, height:p.h*sx2, rotate:PDFLib.degrees(pg.getRotation().angle%360)}); }); }, Promise.resolve())
      .then(function(){ return doc.save(); }); }).then(function(b){ savePdf(b,'sign'); }).catch(fail); };

// ---------- page numbers ----------
$('ngo').onclick=function(){ if(!needOne()) return; msg(T('working')); var pos=B.segVal('npos'), fmt=B.segVal('nfmt'), start=Math.max(0,Math.floor(B.num('nstart')||1)), skip=$('nskip').checked;
  Promise.all([loadPdf(S.buf)]).then(function(r){ var doc=r[0]; return doc.embedFont(PDFLib.StandardFonts.Helvetica).then(function(font){ var pages=doc.getPages(), tot=pages.length-(skip?1:0);
    pages.forEach(function(pg,i){ if(skip&&i===0) return; var n=start+i-(skip?1:0); var t=fmt==='nt'?T('pg_of',{n:n,t:start+tot-1}):String(n); var size=10, tw=font.widthOfTextAtSize(t,size), d=dispSize(pg);
      var dx = pos==='bc' ? (d.w-tw)/2 : d.w-36-tw, dy = pos==='tr' ? 30 : d.h-24; var a=toUser(pg,dx,dy);
      pg.drawText(t,{x:a.x, y:a.y, size:size, font:font, color:PDFLib.rgb(0.25,0.25,0.25), rotate:PDFLib.degrees(pg.getRotation().angle%360)}); });
    return doc.save(); }); }).then(function(b){ savePdf(b,'num'); }).catch(fail); };

// ---------- PDF to images ----------
var MAXI=60, made=[];
$('tgo').onclick=function(){ if(!needOne()) return; if(!S.doc){ msg(T('working')); return; } msg(T('working')); made.forEach(function(m){ URL.revokeObjectURL(m.url); }); made=[]; $('tgrid').innerHTML=''; var fm=B.segVal('tfmt'), n=Math.min(S.n,MAXI);
  if(S.n>MAXI) msg(T('many',{n:S.n,m:MAXI}));
  var doc=S.doc, chain=Promise.resolve(); for(var i=1;i<=n;i++)(function(i){ chain=chain.then(function(){ if(doc!==S.doc) throw 0; return doc.getPage(i); }).then(function(pg){ var v=pg.getViewport({scale:1}); var sc=Math.min(3, 1654/v.width); var vp=pg.getViewport({scale:sc});
    var c=document.createElement('canvas'); c.width=Math.floor(vp.width); c.height=Math.floor(vp.height); var x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height);
    return pg.render({canvasContext:x, viewport:vp}).promise.then(function(){ return new Promise(function(res){ c.toBlob(res, fm==='png'?'image/png':'image/jpeg', 0.9); }); }).then(function(bl){
      var name=base(S.name)+'-'+T('sfx_page')+'-'+i+'.'+fm, url=URL.createObjectURL(bl); made.push({name:name,url:url,bl:bl});
      var d=document.createElement('div'); d.style.cssText='border:1px solid var(--line);border-radius:12px;padding:.4rem;text-align:center;background:#fff';
      d.innerHTML='<img src="'+url+'" alt="" style="width:100%;height:150px;object-fit:contain"><div class="bz-src">'+B.esc(T('page_n',{n:i}))+'</div><button type="button" class="bz-btn2" data-dl="'+(made.length-1)+'">'+B.esc(T('img_dl'))+'</button>';
      $('tgrid').appendChild(d); }); }); })(i);
  chain.then(function(){ $('tall').hidden=made.length<2; if(S.n<=MAXI) msg(''); }).catch(function(e){ if(e!==0) fail(e); }); };
$('tgrid').addEventListener('click', function(e){ var b=e.target.closest('[data-dl]'); if(!b) return; var m=made[+b.getAttribute('data-dl')]; B.download(m.name, m.bl); });
$('tall').onclick=function(){ made.forEach(function(m,i){ setTimeout(function(){ B.download(m.name, m.bl); }, i*450); }); };

B.seg('npos'); B.seg('nfmt'); B.seg('isize'); B.seg('tfmt');
setTool('merge'); drawMerge(); drawImgs();
})();
"""
    faq = [("Are my files uploaded?", "No. Everything happens inside your own browser. Your PDFs and photos never leave your phone or computer, which is why this also works for contracts, payslips and ID copies."),
           ("Is a signature added here legally valid?", "It places an image of your signature on the document, the same as signing a printout and scanning it. Whether that is enough depends on the document and the other party; a qualified digital signature is something else."),
           ("Why can I not open my PDF?", "PDFs that are protected with a password cannot be edited here. Open the file in your PDF reader, save a copy without the password and try again."),
           ("Is there a limit on size or number of files?", "No fixed limit, but very large files can be slow on an older phone. On a computer, files of a few hundred pages work fine.")]
    return X.page("pdf-tools.html", "biz-pdf", "Office tools", "PDF Tools",
                  "Combine, split, turn, sign and number PDFs, turn photos into a PDF or pages into images. Your files never leave your device.",
                  body, js, strings, faq, rule_keys=(), related=("biz-image", "biz-invoice", "biz-qr"))


# ─────────────────────────────────────────────────────────────────────────────
# Image tools (canvas only; re-encoding strips EXIF incl. GPS)
# ─────────────────────────────────────────────────────────────────────────────
def _page_image(X, feeds, prices):
    """image-tools.html"""
    body = f"""
{_privacy()}
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>1. Choose photos</h2>
    <label class="bz-drop" id="drop" style="display:block">
      <input type="file" id="file" accept="image/*" multiple hidden>
      <b style="font-size:1.05rem;color:var(--forest)">Choose photos</b><br><span class="bz-src">or drag them here</span>
    </label>
    <h2 style="margin-top:1.2rem">2. Settings</h2>
    {_seg("preset", [("share", "Smaller for WhatsApp / e-mail"), ("web", "For a website"), ("upload", "Under a file size limit"), ("custom", "Custom")], "share")}
    <div class="bz-grid bz-g2" style="margin-top:.8rem">
      {_field("maxpx", "Longest side (pixels)", "1600", prefix="", mode="numeric")}
      {_field("maxkb", "Maximum file size (KB)", "", prefix="", mode="numeric", hint="Leave empty for no limit. Many online forms allow 500 or 1000 KB.")}
      {_select("crop", "Shape", [("none", "Keep the original shape"), ("1:1", "Square 1:1 (Instagram, profile photo)"), ("4:5", "Portrait 4:5 (Instagram post)"), ("9:16", "Tall 9:16 (Status, Stories)"), ("16:9", "Wide 16:9 (Facebook, YouTube)"), ("3:2", "Photo 3:2")], "none")}
      {_seg("fmt", [("jpeg", "JPG"), ("webp", "WebP"), ("png", "PNG")], "jpeg", "Format")}
      <div><label class="bz-label" for="q">Quality</label><input type="range" id="q" min="40" max="95" value="82" style="width:100%"><div class="bz-hint" id="qv"></div></div>
    </div>
    <div class="bz-ok">Location (GPS), camera and date details stored inside the photo are removed from the new copy.</div>
    <div class="bz-acts"><button type="button" class="bz-btn" id="go">Make copies</button><button type="button" class="bz-btn2" id="all" hidden>Download all</button><button type="button" class="bz-btn2" id="clr">Start over</button></div>
    <div id="msg" aria-live="polite"></div>
  </div>
  <div>
    <div class="bz-res" aria-live="polite"><div class="bz-k">Saved</div><div class="bz-big" id="big">–</div><div class="bz-say" id="say"></div></div>
    <div id="out" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.8rem"></div>
  </div>
</div>
"""
    strings = {"none": "No photos yet.", "count": "{n} photos chosen.", "working": "Working… {k} of {n}", "saved": "{a} → {b} in total ({p}% smaller).",
               "bigger": "{a} → {b} in total.", "bad": "{f} could not be opened. Photos from an iPhone (HEIC) must first be saved as JPG; in the iPhone settings choose Camera → Formats → Most Compatible.",
               "limit": "Could not get {f} under {k} KB; this is the smallest version.", "dl": "Download", "qv": "{q}%", "pngq": "PNG does not use the quality setting.",
               "sfx": "small"}
    js = r"""
(function(){ var B=BZ,$=B.$,T=B.T; var F=[], made=[];
var PRE={share:{px:1600,kb:'',q:80,fmt:'jpeg'}, web:{px:1920,kb:'',q:82,fmt:'webp'}, upload:{px:1600,kb:'500',q:85,fmt:'jpeg'}};
function msg(t,bad){ $('msg').innerHTML=t?'<div class="'+(bad?'bz-warn':'bz-ok')+'">'+B.esc(t)+'</div>':''; }
function kb(n){ return n>=1048576 ? (n/1048576).toFixed(1)+' MB' : Math.max(1,Math.round(n/1024))+' KB'; }
function qv(){ $('qv').textContent = B.segVal('fmt')==='png' ? T('pngq') : T('qv',{q:$('q').value}); }
B.seg('preset', function(v){ var p=PRE[v]; if(!p) return; $('maxpx').value=p.px; $('maxkb').value=p.kb; $('q').value=p.q; B.segSet('fmt',p.fmt); qv(); });
B.seg('fmt', function(){ qv(); }); $('q').addEventListener('input', qv);
['maxpx','maxkb','q'].forEach(function(id){ $(id).addEventListener('input', function(){ B.segSet('preset','custom'); }); }); $('crop').addEventListener('change', function(){});
function add(files){ [].forEach.call(files||[], function(f){ if(/^image\//.test(f.type)||/\.(heic|heif)$/i.test(f.name)) F.push(f); }); $('say').textContent = F.length ? T('count',{n:F.length}) : T('none'); }
$('file').addEventListener('change', function(){ add(this.files); this.value=''; });
var drop=$('drop'); ['dragenter','dragover'].forEach(function(ev){ drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.add('bz-hot'); }); });
['dragleave','drop'].forEach(function(ev){ drop.addEventListener(ev, function(e){ e.preventDefault(); drop.classList.remove('bz-hot'); }); }); drop.addEventListener('drop', function(e){ add(e.dataTransfer.files); });
function open(f){ return new Promise(function(res,rej){ var u=URL.createObjectURL(f), im=new Image(); im.onload=function(){ res({im:im,u:u}); }; im.onerror=function(){ URL.revokeObjectURL(u); rej(new Error(T('bad',{f:f.name}))); }; im.src=u; }); }
function ratio(){ var c=$('crop').value; if(c==='none') return null; var p=c.split(':'); return +p[0]/+p[1]; }
function draw(im, scale){ var r=ratio(), sw=im.naturalWidth, sh=im.naturalHeight, sx=0, sy=0;
  if(r){ if(sw/sh>r){ var nw=Math.round(sh*r); sx=Math.round((sw-nw)/2); sw=nw; } else { var nh=Math.round(sw/r); sy=Math.round((sh-nh)/2); sh=nh; } }
  var max=Math.max(16, Math.floor(B.num('maxpx')||1600)), s=Math.min(1, max/Math.max(sw,sh))*scale;
  var c=document.createElement('canvas'); c.width=Math.max(1,Math.round(sw*s)); c.height=Math.max(1,Math.round(sh*s)); var x=c.getContext('2d');
  var fm=B.segVal('fmt'); if(fm==='jpeg'){ x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); } x.imageSmoothingQuality='high'; x.drawImage(im,sx,sy,sw,sh,0,0,c.width,c.height); return c; }
function enc(c,q){ var fm=B.segVal('fmt'); return new Promise(function(res){ c.toBlob(res, 'image/'+fm, fm==='png'?undefined:q); }); }
// Try the chosen quality; when a size limit is set, lower the quality and then the size until it fits.
function one(im){ var q=(+$('q').value)/100, lim=Math.floor(B.num('maxkb')||0)*1024, scale=1, tries=0;
  function step(){ var c=draw(im,scale); return enc(c,q).then(function(bl){ tries++;
    if(!lim || bl.size<=lim || tries>=14) return {bl:bl, w:c.width, h:c.height, over: !!lim && bl.size>lim};
    if(B.segVal('fmt')!=='png' && q>0.5){ q=Math.max(0.5, q-0.08); } else { scale*=0.85; } return step(); }); }
  return step(); }
$('go').onclick=function(){ if(!F.length){ msg(T('none'),1); return; } made.forEach(function(m){ URL.revokeObjectURL(m.url); }); made=[]; $('out').innerHTML=''; msg('');
  var before=0, after=0, errs=[], n=F.length, k=0;
  F.reduce(function(p,f){ return p.then(function(){ k++; $('say').textContent=T('working',{k:k,n:n}); return open(f); }).then(function(o){ return one(o.im).then(function(r){ URL.revokeObjectURL(o.u);
      before+=f.size; after+=r.bl.size; var ext=B.segVal('fmt')==='jpeg'?'jpg':B.segVal('fmt'); var name=f.name.replace(/\.[^.]+$/,'')+'-'+T('sfx')+'.'+ext, url=URL.createObjectURL(r.bl);
      made.push({name:name,url:url,bl:r.bl}); if(r.over) errs.push(T('limit',{f:f.name,k:Math.floor(B.num('maxkb'))}));
      var d=document.createElement('div'); d.className='bz-card'; d.style.cssText='padding:.5rem;margin:0;text-align:center';
      d.innerHTML='<img src="'+url+'" alt="" style="width:100%;height:120px;object-fit:contain;background:#f4f1ea;border-radius:8px"><div class="bz-src" style="margin:.3rem 0">'+r.w+'&times;'+r.h+' &middot; '+kb(f.size)+' &rarr; <b>'+kb(r.bl.size)+'</b></div><button type="button" class="bz-btn2" data-dl="'+(made.length-1)+'">'+B.esc(T('dl'))+'</button>';
      $('out').appendChild(d); }); }).catch(function(e){ errs.push(e.message); }); }, Promise.resolve())
  .then(function(){ if(after){ var pct=Math.round((1-after/before)*100); $('big').textContent = pct>0 ? pct+'%' : '–'; $('say').textContent = pct>0 ? T('saved',{a:kb(before),b:kb(after),p:pct}) : T('bigger',{a:kb(before),b:kb(after)}); }
    $('all').hidden=made.length<2; if(errs.length) msg(errs.join(' '),1); }); };
$('out').addEventListener('click', function(e){ var b=e.target.closest('[data-dl]'); if(!b) return; var m=made[+b.getAttribute('data-dl')]; B.download(m.name, m.bl); });
$('all').onclick=function(){ made.forEach(function(m,i){ setTimeout(function(){ B.download(m.name, m.bl); }, i*450); }); };
$('clr').onclick=function(){ F=[]; made.forEach(function(m){ URL.revokeObjectURL(m.url); }); made=[]; $('out').innerHTML=''; $('big').textContent='–'; $('say').textContent=T('none'); $('all').hidden=true; msg(''); };
qv(); $('say').textContent=T('none');
})();
"""
    faq = [("Are my photos uploaded?", "No. The photos are resized inside your own browser and never leave your device."),
           ("Why remove location data?", "Photos taken with a phone often contain the exact GPS position where they were taken, for example your home or shop. The copies made here do not contain that information."),
           ("Which size should I use for WhatsApp or a website?", "For WhatsApp, e-mail and most websites a longest side of 1600 to 1920 pixels is sharp enough and keeps files small. For a form with an upload limit, choose 'Under a file size limit' and type the limit in KB.")]
    return X.page("image-tools.html", "biz-image", "Office tools", "Image Resizer & Photo Tools",
                  "Make photos smaller, fit them under an upload limit, crop them for social media and remove location data.",
                  body, js, strings, faq, rule_keys=(), related=("biz-pdf", "biz-qr", "biz-card"))


# ─────────────────────────────────────────────────────────────────────────────
# Business card + e-mail signature maker (canvas → jsPDF, QR via qrcode-generator)
# Cards are drawn on a canvas at 600 dpi so every character prints correctly
# (standard PDF fonts cannot show all accents); the same drawing is the preview.
# ─────────────────────────────────────────────────────────────────────────────
def _page_card(X, feeds, prices):
    """business-card-maker.html"""
    body = f"""
<div class="bz-grid bz-split">
  <div class="bz-card">
    <h2>Your details</h2>
    <div class="bz-grid bz-g2">
      {_text("fn", "First name")}{_text("ln", "Last name")}
      {_text("title", "Job title")}{_text("org", "Company")}
      {_text("tel", "Phone", "+597 ", mode="tel")}{_text("mail", "E-mail", mode="email")}
      {_text("web", "Website")}{_text("adr", "Address")}
    </div>
    <details class="bz-more" open><summary>Design</summary>
      <div class="bz-grid bz-g2" style="margin-top:.6rem">
        {_seg("lay", [("left", "Left"), ("center", "Centred")], "left", "Layout")}
        {_seg("qr", [("front", "QR on front"), ("back", "QR on back"), ("none", "No QR")], "front", "QR code with your contact card")}
        <div><label class="bz-label" for="col">Colour</label><input id="col" type="color" value="#1b4332" class="bz-in" style="height:3rem;padding:.2rem"></div>
        <div><label class="bz-label" for="logo">Logo (optional)</label><input id="logo" type="file" accept="image/*" class="bz-in" style="padding:.5rem"><button type="button" class="bz-btn2" id="nologo" hidden style="margin-top:.4rem">Remove logo</button></div>
      </div>
      <p class="bz-src" id="qnote" hidden>In the centred layout the QR code goes on the back.</p>
    </details>
  </div>
  <div>
    <div class="bz-card" style="text-align:center">
      <span class="bz-label">Front</span><canvas id="pf" style="width:100%;max-width:425px;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.18)"></canvas>
      <span class="bz-label" style="margin-top:1rem">Back</span><canvas id="pb" style="width:100%;max-width:425px;border-radius:6px;box-shadow:0 2px 10px rgba(0,0,0,.18)"></canvas>
      <p class="bz-src" style="margin-top:.6rem">Standard size 85 &times; 55 mm.</p>
      <div class="bz-acts" style="justify-content:center">
        <button type="button" class="bz-btn" id="a4">Print yourself: 10 per A4 (PDF)</button>
        <button type="button" class="bz-btn2" id="shop">For a print shop (PDF with 3 mm bleed)</button>
      </div>
    </div>
  </div>
</div>
<div class="bz-card">
  <h2>E-mail signature</h2>
  <div id="sig" style="border:1px solid var(--line);border-radius:12px;padding:1rem;background:#fff;overflow-x:auto"></div>
  <div class="bz-acts"><button type="button" class="bz-btn" id="sigcp">Copy signature</button><button type="button" class="bz-btn2" id="sightml">Copy HTML code</button></div>
  <p class="bz-src" style="margin-top:.6rem"><b>Gmail:</b> Settings &rarr; See all settings &rarr; Signature, then paste. <b>Outlook:</b> Settings &rarr; Mail &rarr; Compose and reply &rarr; Email signature, then paste.</p>
</div>
"""
    strings = {"loadfail": "The card tool could not load. Check your connection and reload the page.", "need": "Fill in at least your name or company.",
               "copied_sig": "Signature copied. Paste it in your e-mail settings.", "sfx_a4": "business-cards-A4", "sfx_shop": "business-card-print"}
    js = r"""
(function(){ var B=BZ,E=B.E,$=B.$,T=B.T; var IDS=['fn','ln','title','org','tel','mail','web','adr','lay','qr','col'];
var logo=null, qrLoaded=false;
var F='Helvetica, Arial, sans-serif';
function v(id){ return ($(id).value||'').trim(); }
function tel(){ var t=v('tel'); return t.replace(/[^\d]/g,'').length>4 ? t : ''; }
function name(){ return (v('fn')+' '+v('ln')).trim(); }
function webShown(){ return v('web').replace(/^https?:\/\//i,'').replace(/\/$/,''); }
function vcard(){ if(!name() && !v('org')) return ''; return E.vcardPayload({first:v('fn'), last:v('ln'), org:v('org'), title:v('title'), tel:tel(), email:v('mail'), url:v('web'), adr:v('adr')}); }
function qrPos(){ var q=B.segVal('qr'); if(q==='front' && B.segVal('lay')==='center') return 'back'; return q; }
function qrMatrix(){ var p=vcard(); if(!p || !window.qrcode) return null; try{ qrcode.stringToBytes=qrcode.stringToBytesFuncs['UTF-8']; var q=qrcode(0,'L'); q.addData(p,'Byte'); q.make(); return q; }catch(e){ return null; } }
function drawQr(x, q, X0, Y0, S){ var n=q.getModuleCount(), m=S/n; x.fillStyle='#000'; for(var r=0;r<n;r++) for(var c=0;c<n;c++) if(q.isDark(r,c)) x.fillRect(X0+c*m, Y0+r*m, m+0.02, m+0.02); }
// fit text to a width by shrinking the font; returns the font size used (mm)
function fit(x, t, bold, size, maxW){ var s=size; do { x.font=(bold?'bold ':'')+s+'px '+F; if(x.measureText(t).width<=maxW) break; s-=0.2; } while(s>1.6); return s; }
function line(x, t, bold, size, maxW, X0, Y0, color, align){ if(!t) return; fit(x,t,bold,size,maxW); x.fillStyle=color; x.textAlign=align||'left'; x.fillText(t, X0, Y0); }
function logoBox(x, X0, Y0, w, h, align){ if(!logo) return 0; var s=Math.min(w/logo.width, h/logo.height), lw=logo.width*s, lh=logo.height*s; var lx = align==='center' ? X0-lw/2 : (align==='right' ? X0-lw : X0); x.drawImage(logo, lx, Y0, lw, lh); return lh; }
// Draw one side. Units: mm (context is scaled). bleed extends colour areas past the trim edge.
function side(which, dpmm, bleed){ var W=85, H=55, c=document.createElement('canvas'); c.width=Math.round((W+2*bleed)*dpmm); c.height=Math.round((H+2*bleed)*dpmm);
  var x=c.getContext('2d'); x.scale(dpmm,dpmm); x.translate(bleed,bleed); x.fillStyle='#fff'; x.fillRect(-bleed,-bleed,W+2*bleed,H+2*bleed); x.textBaseline='alphabetic';
  var col=$('col').value, lay=B.segVal('lay'), qp=qrPos(), q=(qp==='none')?null:qrMatrix(), ink='#1f2937', soft='#4b5563';
  var contacts=[tel(), v('mail'), webShown(), v('adr')].filter(Boolean);
  if(which==='front'){
    if(lay==='left'){ x.fillStyle=col; x.fillRect(-bleed,-bleed,4+bleed,H+2*bleed);
      var qf=(q && qp==='front'), maxW = qf ? 49 : 72; if(logo) logoBox(x, 80, 5, 22, 11, 'right');
      var nameW = logo ? 44 : maxW;
      line(x, name()||v('org'), true, 5, nameW, 8, 13.5, ink); line(x, v('title'), false, 3.1, nameW, 8, 18.6, col);
      if(name()) line(x, v('org'), true, 3.2, maxW, 8, 25.5, ink);
      var y = qf ? 33 : 34; contacts.slice(0,4).forEach(function(t){ line(x, t, false, 2.75, maxW, 8, y, soft); y+=4.1; });
      if(qf){ x.fillStyle='#fff'; x.fillRect(59.5,31,20,20); drawQr(x, q, 60, 31.5, 19); }
    } else { x.fillStyle=col; x.fillRect(-bleed,-bleed,W+2*bleed,3+bleed); var y0=logo ? 6+logoBox(x, 42.5, 6, 30, 10, 'center')+5 : 14;
      line(x, name()||v('org'), true, 5, 75, 42.5, y0, ink, 'center'); line(x, v('title'), false, 3.1, 75, 42.5, y0+5, col, 'center');
      if(name()) line(x, v('org'), true, 3.2, 75, 42.5, y0+11, ink, 'center');
      var y=Math.max(y0+18, 36); var cl=contacts.slice(0,4); if(cl.length>3){ y=Math.min(y, 55-4-3*3.8); } cl.forEach(function(t){ line(x, t, false, 2.75, 75, 42.5, y, soft, 'center'); y+=3.8; }); }
  } else { x.fillStyle=col; x.fillRect(-bleed,-bleed,W+2*bleed,H+2*bleed);
    var hasQ=(q && qp==='back'); var label=v('org')||name(); x.fillStyle='#fff';
    if(hasQ){ x.fillRect(30,7.5,25,25); drawQr(x, q, 32.5, 10, 20); if(label) line(x, label, true, 4.2, 75, 42.5, 41, '#fff', 'center'); if(webShown()) line(x, webShown(), false, 2.8, 75, 42.5, 46.5, '#fff', 'center'); }
    else { if(label) line(x, label, true, 6, 75, 42.5, 29, '#fff', 'center'); if(webShown()) line(x, webShown(), false, 3, 75, 42.5, 36, '#fff', 'center'); } }
  return c; }
function preview(){ ['pf','pb'].forEach(function(id){ var s=side(id==='pf'?'front':'back', 10, 0), cv=$(id); cv.width=s.width; cv.height=s.height; cv.getContext('2d').drawImage(s,0,0); });
  $('qnote').hidden = !(B.segVal('qr')==='front' && B.segVal('lay')==='center'); sig(); B.saveUrl(IDS); }
function jspdf(){ return B.loadScript('""" + JSPDF + r"""').then(function(){ return window.jspdf.jsPDF; }); }
function ready(){ if(!name() && !v('org')){ B.toast(T('need')); return false; } return true; }
function fileBase(){ return (v('org')||name()||'card').replace(/[^\w\-]+/g,'-').slice(0,40); }
// A4: 2 columns x 5 rows, cards touching, crop marks in the margins. Page 2 = backs, in the
// mirrored position so they line up when printed double-sided (flip on long edge).
$('a4').onclick=function(){ if(!ready()) return; jspdf().then(function(J){ var d=new J({unit:'mm', format:'a4'}), X0=20, Y0=11, f=side('front',23.6,0).toDataURL('image/png'), b=side('back',23.6,0).toDataURL('image/png');
  function sheet(img, mirror){ for(var r=0;r<5;r++) for(var k=0;k<2;k++){ var xx = mirror ? 210-X0-85*(k+1) : X0+85*k; d.addImage(img,'PNG', xx, Y0+55*r, 85, 55, img===f?'F':'B'); }
    d.setDrawColor(120); d.setLineWidth(0.15); [X0, X0+85, X0+170].forEach(function(xx){ d.line(xx, 2, xx, Y0-2); d.line(xx, Y0+275+2, xx, 295); });
    for(var r2=0;r2<=5;r2++){ var yy=Y0+55*r2; d.line(2, yy, X0-2, yy); d.line(X0+170+2, yy, 208, yy); } }
  sheet(f,false); d.addPage(); sheet(b,true); d.save(fileBase()+'-'+T('sfx_a4')+'.pdf'); }).catch(function(){ B.toast(T('loadfail')); }); };
// Print shop: one card per page, 91 x 61 mm (85 x 55 + 3 mm bleed each side), front and back.
$('shop').onclick=function(){ if(!ready()) return; jspdf().then(function(J){ var d=new J({unit:'mm', format:[91,61], orientation:'landscape'});
  d.addImage(side('front',23.6,3).toDataURL('image/png'),'PNG',0,0,91,61); d.addPage([91,61],'landscape'); d.addImage(side('back',23.6,3).toDataURL('image/png'),'PNG',0,0,91,61);
  d.save(fileBase()+'-'+T('sfx_shop')+'.pdf'); }).catch(function(){ B.toast(T('loadfail')); }); };
// E-mail signature: a table with inline styles (what Gmail and Outlook keep). No images: many mail apps block embedded images.
function sigHtml(){ var col=$('col').value, e=B.esc, rows=[];
  if(name()) rows.push('<div style="font-size:15px;font-weight:bold;color:#1f2937">'+e(name())+'</div>');
  var t=[v('title'), v('org')].filter(Boolean); if(t.length) rows.push('<div style="font-size:13px;color:'+e(col)+';font-weight:bold">'+e([v('title'), v('org')].filter(Boolean).join(' · '))+'</div>');
  var c=[]; if(tel()) c.push('<a href="tel:'+e(tel().replace(/[^\d+]/g,''))+'" style="color:#374151;text-decoration:none">'+e(tel())+'</a>');
  if(v('mail')) c.push('<a href="mailto:'+e(v('mail'))+'" style="color:#374151;text-decoration:none">'+e(v('mail'))+'</a>');
  if(webShown()) c.push('<a href="'+e(/^https?:/i.test(v('web'))?v('web'):'https://'+v('web'))+'" style="color:'+e(col)+';text-decoration:none">'+e(webShown())+'</a>');
  if(c.length) rows.push('<div style="font-size:12px;color:#374151;margin-top:4px">'+c.join(' &nbsp;|&nbsp; ')+'</div>');
  if(v('adr')) rows.push('<div style="font-size:12px;color:#6b7280">'+e(v('adr'))+'</div>');
  return '<table cellpadding="0" cellspacing="0" border="0" style="font-family:Arial,Helvetica,sans-serif;border-collapse:collapse"><tr><td style="border-left:4px solid '+e(col)+';padding:2px 0 2px 10px">'+rows.join('')+'</td></tr></table>'; }
function sig(){ $('sig').innerHTML=sigHtml(); }
$('sightml').onclick=function(){ if(!ready()) return; B.copy(sigHtml()); };
$('sigcp').onclick=function(){ if(!ready()) return; var h=sigHtml();
  if(window.ClipboardItem && navigator.clipboard && navigator.clipboard.write){ navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([h],{type:'text/html'}), 'text/plain':new Blob([$('sig').innerText],{type:'text/plain'})})]).then(function(){ B.toast(T('copied_sig')); }, legacy); } else legacy();
  function legacy(){ var r=document.createRange(); r.selectNodeContents($('sig')); var s=window.getSelection(); s.removeAllRanges(); s.addRange(r); try{ document.execCommand('copy'); B.toast(T('copied_sig')); }catch(e){} s.removeAllRanges(); } };
$('logo').addEventListener('change', function(){ var f=this.files&&this.files[0]; if(!f) return; var u=URL.createObjectURL(f), im=new Image(); im.onload=function(){ logo=im; $('nologo').hidden=false; preview(); }; im.src=u; });
$('nologo').onclick=function(){ logo=null; $('logo').value=''; this.hidden=true; preview(); };
B.loadUrl(IDS); B.seg('lay', preview); B.seg('qr', preview); B.on(['fn','ln','title','org','tel','mail','web','adr','col'],'input',preview);
B.loadScript('""" + QR_LIB + r"""').then(function(){ qrLoaded=true; preview(); }).catch(function(){ preview(); }); preview();
})();
"""
    faq = [("Which paper should I use?", "For printing at home or in the office, use thick paper or card of about 250 to 300 g/m² that your printer accepts, print at 100% (not 'fit to page') and cut along the marks."),
           ("What does the QR code on the card do?", "It holds your contact card. Someone who scans it can save your name, phone, e-mail and website in their phone in one tap. It works without internet and never expires."),
           ("What is the print shop file?", "A PDF with one card per page and 3 mm of extra colour around the edge (bleed), which is what print shops usually ask for. Check with your print shop which format they want.")]
    return X.page("business-card-maker.html", "biz-card", "Office tools", "Business Card & E-mail Signature Maker",
                  "Design a business card with a QR code, print 10 on A4 or send a file to a print shop, and make a matching e-mail signature.",
                  body, js, strings, faq, rule_keys=(), related=("biz-qr", "biz-invoice", "biz-image"))


# ─────────────────────────────────────────────────────────────────────────────
# Guides. Every legal value is read from data/business_rules.json (never typed
# here) and wrapped in translate="no", so sentences stay value-free for the NL/ES
# translation and a rule change can never break a translation. Facts that could
# not be verified at an official source are left out (see business_rules.json
# "excluded_until_official"); contact details are watched by html_contains
# sentinels in data/rules_radar_config.json.
# ─────────────────────────────────────────────────────────────────────────────
def _gv(text):
    """A value inside a sentence: never translated."""
    return f'<b translate="no">{_esc(text)}</b>'


def _gsrd(n):
    """SRD amount, reformatted per language in the browser (1,000 / 1.000)."""
    return f'<b class="bz-gn" data-n="{n}" translate="no">SRD {n:,}</b>'


def _gpct(p):
    s = f"{p:g}"
    return f'<b class="bz-gp" data-p="{s}" translate="no">{s}%</b>'


def _glink(url, label):
    return f'<a href="{_esc(url)}" target="_blank" rel="noopener">{label}</a>'


def _gstep(n, title, html):
    return (f'<div class="bz-card"><h2 style="display:flex;gap:.6rem;align-items:baseline">'
            f'<span style="flex:none;display:inline-flex;align-items:center;justify-content:center;width:1.9rem;height:1.9rem;border-radius:999px;background:var(--forest);color:#fff;font-size:1rem" translate="no">{n}</span>'
            f'<span>{title}</span></h2>{html}</div>')


def _gcard(title, html):
    return f'<div class="bz-card"><h2>{title}</h2>{html}</div>'


def _gtools(keys):
    idx = {p[1]: p for p in BIZ_PAGES}
    return ('<div class="bz-acts">' + "".join(f'<a class="bz-btn2" href="{idx[k][0]}">{idx[k][2]}</a>' for k in keys if k in idx) + '</div>')


def _gcheck(R, key):
    e = R.get(key)
    e = e[-1] if isinstance(e, list) else e
    v = (e or {}).get("verified", "")
    return f'<p class="bz-src" style="margin-top:.6rem">Checked at the official source on <span class="bz-date" data-d="{v}" translate="no">{v}</span>.</p>' if v else ""


_GUIDE_JS = r"""
(function(){ var L=BZ.L, nf=new Intl.NumberFormat(L==='en'?'en-US':'nl-NL',{maximumFractionDigits:2});
[].forEach.call(document.querySelectorAll('.bz-gn'), function(e){ e.textContent='SRD '+nf.format(+e.getAttribute('data-n')); });
[].forEach.call(document.querySelectorAll('.bz-gp'), function(e){ e.textContent=nf.format(+e.getAttribute('data-p'))+'%'; });
[].forEach.call(document.querySelectorAll('.bz-date'), function(e){ var d=e.getAttribute('data-d'); if(d) e.textContent=BZ.fmtDay(d); });
})();
"""


def _mw_now(X):
    return [e for e in X.R["minimum_wage_hourly"] if e["from"] <= X.today.isoformat()][-1]


def _page_g_start(X, feeds, prices):
    """start-business-suriname.html"""
    R = X.R
    b = R["btw"][-1]
    k = R["contacts_kkf"]
    body = f"""
<div class="bz-card" style="background:var(--mint);border-color:#BFDDB8"><p style="line-height:1.65;color:var(--forest)">Registering a business in Suriname takes a few steps at different offices. This guide lists them in order, with the official links. Fees and processing times change, so check them with the office before you go.</p></div>
{_gstep(1, "Choose a legal form", '''
<table class="bz-tbl"><tbody>
<tr><td><b translate="no">Eenmanszaak</b></td><td>One owner. You are personally liable for the debts of the business.</td></tr>
<tr><td><b translate="no">VOF</b></td><td>A partnership of two or more owners, who are each personally liable.</td></tr>
<tr><td><b translate="no">NV</b></td><td>A company with shares. It is set up at a notary.</td></tr>
<tr><td><b translate="no">Stichting</b></td><td>A foundation for a non-profit goal. It is also set up at a notary.</td></tr>
</tbody></table>
<p class="bz-src" style="margin-top:.6rem">Not sure which form fits? An accountant or notary can advise you.</p>''')}
{_gstep(2, "Prepare your documents", f'''
<p>Bring a valid ID. An extract from the civil registry (<span translate="no">CBB-uittreksel</span>) can be requested online and free of charge at {_glink(R["cbb_online"]["portal"], "digitale-id.gov.sr")}; you need an account on that portal. Ask the Chamber of Commerce which documents your legal form needs.</p>
{_gcheck(R, "cbb_online")}''')}
{_gstep(3, "Register at the Chamber of Commerce (KKF)", f'''
<p>Every business is entered in the trade register of the <span translate="no">Kamer van Koophandel en Fabrieken</span> (KKF). The KKF also checks whether your trade name is still free.</p>
<table class="bz-tbl" style="margin-top:.6rem"><tbody>
<tr><td>Address</td><td translate="no">{_esc(k["address"])}</td></tr>
<tr><td>Phone</td><td translate="no">{_esc(k["phone"])}</td></tr>
<tr><td>Website</td><td>{_glink(k["web"], "kkf.sr")}</td></tr>
</tbody></table>{_gcheck(R, "contacts_kkf")}''')}
{_gstep(4, "Register with the Belastingdienst", f'''
<p>Register your business in the online portal of the Belastingdienst. You then have a tax number (<span translate="no">FIN</span>). You need it for BTW, for wage tax when you have staff, and on every invoice.</p>
<div class="bz-acts">{_glink("https://portaal.belastingdienst.sr/OPO/", "Belastingdienst online portal")}</div>''')}
{_gstep(5, "Charge BTW when your turnover is high enough", f'''
<p>A business must register for BTW when its turnover in a calendar year is more than {_gsrd(b["threshold_year"])}. From then on you charge BTW, file a return every month and pay before the 16th of the next month.</p>
{_gtools(("biz-g-btw", "biz-btw"))}''')}
{_gstep(6, "Check whether you need a business licence", f'''
<p>Some activities need a business licence (<span translate="no">bedrijfsvergunning</span>). Check this and apply on the government's permit portal.</p>
<div class="bz-acts">{_glink("https://vergunningen.gov.sr/", "vergunningen.gov.sr")}</div>''')}
{_gstep(7, "Hiring staff?", f'''<p>As an employer you withhold wage tax and AOV, and you pay pension (APF), FVO and part of the basic health insurance premium.</p>{_gtools(("biz-g-staff", "biz-salary"))}''')}
{_gstep(8, "Keep your records", f'''<p>The BTW law requires a business to keep its records for {_gv(str(b["retention_years"]))} years. Number your invoices in sequence from the start.</p>{_gtools(("biz-invoice", "biz-register", "biz-deadlines"))}''')}
"""
    faq = [("How long does it take to start a business in Suriname?", "That depends on the legal form and on the offices involved. An eenmanszaak is the simplest; an NV or stichting first goes through a notary. Ask the KKF for the current processing time."),
           ("Do I need to register for BTW straight away?", "Only when your turnover in a calendar year is above the BTW threshold in step 5. Below that you do not charge BTW."),
           ("What does registering cost?", "The KKF, the notary and some licences charge fees. We do not list amounts here because they change; ask the office before you go.")]
    return X.page("start-business-suriname.html", "biz-g-start", "Guide", "Starting a Business in Suriname",
                  "The official steps in order: legal form, Chamber of Commerce, tax number, BTW, licence and staff.",
                  body, _GUIDE_JS, {}, faq, rule_keys=("cbb_online", "contacts_kkf", "btw"), related=("biz-g-btw", "biz-g-staff", "biz-invoice"))


def _page_g_btw(X, feeds, prices):
    """btw-guide-suriname.html"""
    R = X.R
    b = R["btw"][-1]
    p = R["btw_penalties"][-1]
    ann = b["annex_links"]
    fl = p["late_filing_by_month"]
    fines = "".join(f'<tr><td>{_gv(str(i + 1))} {"month" if i == 0 else "months"}{" or more" if i == len(fl) - 1 else ""}</td><td class="n">{_gsrd(v)}</td></tr>' for i, v in enumerate(fl))
    body = f"""
{_gcard("Who must charge BTW?", f'''<p>A business must register for BTW when its turnover in a calendar year is more than {_gsrd(b["threshold_year"])}. You register in the Belastingdienst portal. To check whether a supplier is registered, use the official register.</p>
<div class="bz-acts">{_glink(ann["register"], "Official BTW register")}</div>''')}
{_gcard("The rates", f'''<table class="bz-tbl"><tbody>
<tr><td>{_gpct(10)}</td><td>The general rate for goods and services.</td></tr>
<tr><td>{_gpct(5)}</td><td>Among others water, electricity, cooking gas and domestic goods transport (annex 4 of the BTW law).</td></tr>
<tr><td>{_gpct(25)}</td><td>Certain luxury goods, among others heavy or expensive motor vehicles, speedboats, weapons and ammunition, and fireworks (annex 3 and its specification).</td></tr>
<tr><td>{_gpct(0)}</td><td>Exports and the goods and services in annex 1.</td></tr>
<tr><td><b>Exempt</b></td><td>For example medical care, financial services and domestic passenger transport (annex 2). No BTW is charged and no BTW can be reclaimed.</td></tr>
</tbody></table>
<p class="bz-src" style="margin-top:.6rem">Official texts: {_glink(ann["wet"], "BTW law 2022")} &middot; {_glink(ann["spec_bijlage2"], "specification annex 2")} &middot; {_glink(ann["spec_bijlage3"], "specification annex 3")}</p>''')}
{_gcard("What must be on an invoice?", f'''<p>Under article 28 of the BTW law an invoice contains:</p>
<ul style="padding-left:1.1rem;list-style:disc;line-height:1.7;margin-top:.4rem">
<li>the date and a sequential number;</li><li>the tax numbers (FIN) of the supplier and of the customer;</li><li>the names and addresses of both;</li>
<li>the quantity and description of the goods or services, and the delivery date;</li><li>the price excluding BTW per rate, the rate and the BTW amount;</li>
<li>a note when an exemption applies.</li></ul>
<p style="margin-top:.6rem">Send the invoice within {_gv(str(b["invoice_within_days_after_month"]))} days after the end of the month in which you delivered.</p>
{_gtools(("biz-invoice", "biz-receipt"))}''')}
{_gcard("Return and payment", f'''<p>You file a BTW return every month and pay before the 16th of the next month. On the return you deduct the BTW you paid on your purchases (input tax) from the BTW you charged.</p>
{_gtools(("biz-register", "biz-deadlines", "biz-btw"))}''')}
{_gcard("Fines for filing late", f'''<p>For returns from <span class="bz-date" data-d="{p["from"]}" translate="no">{p["from"]}</span> the fine for filing late depends on how late the return is:</p>
<table class="bz-tbl" style="margin-top:.5rem"><tbody>{fines}</tbody></table>
<p style="margin-top:.6rem">For paying late the fine is {_gpct(p["late_payment_pct"])} of the amount paid late, with a maximum of {_gsrd(p["late_payment_max"])}.</p>
<p class="bz-src" style="margin-top:.4rem">{_glink(p["url"], "S.B. 2025 no. 140")}</p>''')}
{_gcard("BTW on imports", '''<p>On imported goods BTW is charged on the customs value plus import duty, excise and the other levies due on import.</p>''' + _gtools(("biz-import", "biz-g-import")))}
{_gcard("Keep your records", f'''<p>Keep your administration for {_gv(str(b["retention_years"]))} years.</p>''')}
<div class="bz-card bz-src"><p>More explanation: the Belastingdienst {_glink(b["url"], "BTW brochure")}. The independent website {_glink("https://btw.sr/", "btw.sr")} also explains the law.</p></div>
"""
    return X.page("btw-guide-suriname.html", "biz-g-btw", "Guide", "BTW in Suriname: A Plain Guide",
                  "Who must charge BTW, the rates, invoice rules, the monthly return and the fines, with the official sources.",
                  body, _GUIDE_JS, {}, None, rule_keys=("btw", "btw_penalties"), related=("biz-btw", "biz-invoice", "biz-register"))


def _page_g_staff(X, feeds, prices):
    """hiring-staff-suriname.html"""
    R = X.R
    mw = _mw_now(X)
    wt = R["working_time"][-1]
    vac = R["vacation"][-1]
    aov = R["aov"][-1]
    apf = R["apf"][-1]
    apc = R["apf_common"]
    fvo = R["fvo"][-1]
    tf = R["tax_free"][-1]
    body = f"""
{_gcard("Register as an employer", f'''<p>A business that pays wages to employees must withhold wage tax. Register in the online portal of the Belastingdienst; an employer has one tax number (FIN) for all its employees.</p>
<div class="bz-acts">{_glink("https://portaal.belastingdienst.sr/OPO/", "Belastingdienst online portal")}{_glink("https://belastingdienst.sr/belastingen/loonbelasting/", "Belastingdienst: wage tax")}</div>''')}
{_gcard("What you pay and withhold every month", f'''<table class="bz-tbl"><tbody>
<tr><td><b>Wage tax</b></td><td>Withheld from the wage. The return is filed monthly in the portal.</td></tr>
<tr><td><b>AOV</b></td><td>{_gpct(aov["pct"])} of the taxable wage, withheld from employees under {_gv(str(aov["max_age"]))}.</td></tr>
<tr><td><b>APF pension</b></td><td>{_gpct(apf["pct_total"])} of the gross wage (rate published for {_gv(str(apf["published_for_year"]))}), on a wage between {_gsrd(apc["base_min_month"])} and {_gsrd(apc["base_max_month"])} per month. The employer pays at least {_gpct(apc["employer_min_share_pct"])}. Due on the 15th of the next month.</td></tr>
<tr><td><b>FVO</b></td><td>{_gpct(fvo["pct_total"])} of the wage for the parental-leave fund: at most {_gpct(fvo["employee_max_pct"])} from the employee, the rest from the employer.</td></tr>
<tr><td><b>Basic health insurance (BZV)</b></td><td>The employer pays at least {_gpct(R["bzv_max_premium"][-1]["employer_min_share_pct"])} of the employee's premium. The premium depends on the insurer.</td></tr>
</tbody></table>
{_gtools(("biz-salary", "biz-payslip", "biz-deadlines"))}''')}
{_gcard("Deadlines", '''<p>Wage tax and AOV: the law allows until the 7th working day after the end of the month, but the Belastingdienst portal accepts the return only from the 26th up to and including the 10th of the next month. File by the earlier date. The APF premium is due on the 15th. Once a year you also file the annual wage summary (<span translate="no">verzamelloonstaat</span>), which can be done online.</p>''' + _gtools(("biz-deadlines",)))}
{_gcard("Minimum wage", f'''<p>From <span class="bz-date" data-d="{mw["from"]}" translate="no">{mw["from"]}</span> the minimum wage is {_gv("SRD " + f'{mw["value"]:.2f}')} gross per hour, for all sectors.</p>{_gtools(("biz-minwage",))}''')}
{_gcard("Working hours and overtime", f'''<p>An employee works at most {_gv(f'{wt["max_day_hours"]:g}')} hours per day or {_gv(str(wt["max_week_hours"]))} hours per week. Overtime needs a permit from the Labour Inspectorate, usually up to 64 hours per week; the Minister of Labour can allow up to 72 hours in special cases.</p>
<p style="margin-top:.5rem">Overtime is paid at {_gpct(wt["overtime_pct_weekday"])} of the wage on a normal day and {_gpct(wt["overtime_pct_rest_day"])} on a Sunday or rest day; {_gpct(wt["overtime_pct_holiday_cao"])} on public holidays when the collective agreement says so.</p>
{_gtools(("biz-timesheet", "biz-minwage"))}''')}
{_gcard("Holidays", f'''<p>After a full year of service an employee has {_gv(str(vac["first_year_days"]))} working days of holiday, rising by {_gv(str(vac["increase_per_year"]))} days each following year up to {_gv(str(vac["max_days"]))}. For each holiday day taken, the employee also receives a holiday allowance of half a day's wage. Unused days are paid out when employment ends.</p>
<p style="margin-top:.5rem">Holiday allowance and a bonus (<span translate="no">gratificatie</span>) are each tax-free up to one month's wage, with a maximum of {_gsrd(tf["holiday_allowance_max_year"])} per year.</p>
{_gtools(("biz-vacation",))}''')}
{_gcard("Contracts and dismissal", f'''<p>Probation, notice and dismissal are regulated by law. Get advice from the Ministry of Labour or a lawyer before you end an employment contract. All labour laws can be downloaded from the government website.</p>
<div class="bz-acts">{_glink("https://gov.sr/ministeries/ministerie-van-arbeid-werkgelegenheid-en-jeugdzaken/arbeidswetgeving/", "Labour laws (gov.sr)")}</div>''')}
"""
    return X.page("hiring-staff-suriname.html", "biz-g-staff", "Guide", "Hiring Staff in Suriname",
                  "What an employer pays and withholds, the deadlines, minimum wage, working hours, overtime and holidays.",
                  body, _GUIDE_JS, {}, None,
                  rule_keys=("wage_tax", "aov", "apf", "apf_common", "fvo", "bzv_max_premium", "minimum_wage_hourly", "working_time", "vacation", "tax_free"),
                  related=("biz-salary", "biz-payslip", "biz-minwage"))


def _page_g_import(X, feeds, prices):
    """import-export-suriname.html"""
    R = X.R
    imp = R["import"][-1]
    il = R["import_licence"]
    cp = R["customs_procedure"]
    cust = [o for o in R["contacts_belastingdienst"]["offices"] if o["address"].startswith("Havenlaan")][0]
    # Time-bound notice: shown only until il["note_show_until"]; the radar reminds us on il["review_by"].
    nov = ('<div class="bz-warn" style="margin-top:.7rem">Change from 1 November 2026: the business association VSB announced in September 2026, after talks with the ministry, '
           'that the current import and licence procedures apply up to and including 31 October 2026 and that new procedures under the amended Negative List decree start on 1 November 2026. '
           'On 27 September 2026 the government had not yet published this itself. Check with the IUD before you import.</div>') if X.today.isoformat() <= il.get("note_show_until", "") else ""
    steps = ["Register and get access to the electronic declaration system.", "File the declaration.", "Upload the documents.",
             "Pay the import duties and taxes at the receiver of import duties and excise.", "The declaration is processed and approved.",
             "Follow the status of your declaration.", "The shipment is released and handled.", "Keep your records."]
    body = f"""
{_gcard("How a customs declaration works", f'''<p>Commercial goods are declared electronically. You need a tax number (FIN). The official procedure of the Belastingdienst has these steps:</p>
<ol style="padding-left:1.3rem;list-style:decimal;line-height:1.75;margin-top:.4rem">{"".join(f"<li>{s}</li>" for s in steps)}</ol>
<div class="bz-acts">{_glink(cp["url"], "Official procedure (PDF)")}{_glink("https://asycuda.belastingdienst.sr/", "ASYCUDA (customs system)")}</div>
<p class="bz-src" style="margin-top:.5rem">Many importers use a customs broker for the declaration.</p>''')}
{_gcard("What you pay", f'''<table class="bz-tbl"><tbody>
<tr><td><b>Import duty</b></td><td>A percentage of the CIF value that depends on the HS code of the product. Look it up in the official tariff.</td></tr>
<tr><td><b>Statistics fee</b></td><td>{_gpct(imp["stat_pct"])} of the CIF value.</td></tr>
<tr><td><b>Consent fee</b></td><td>{_gpct(imp["consent_pct"])} of the CIF value.</td></tr>
<tr><td><b>Excise</b></td><td>On certain goods only.</td></tr>
<tr><td><b>BTW</b></td><td>On the customs value plus import duty, excise and the other levies due on import.</td></tr>
</tbody></table>
<p class="bz-src" style="margin-top:.6rem">The statistics and consent fee rates are reported the same by several professional sources, but the legal text is not published online; your declaration shows the amounts that apply. Customs converts foreign currency with its own exchange rate, which is set every two weeks.</p>
{_gtools(("biz-import", "biz-pricing", "biz-breakeven"))}''')}
{_gcard("Import licences", f'''<p>The {_gv(il["laws"][0])} and the {_gv(il["laws"][1])} determine which goods need an import, export or transit licence. Licences are issued by the Import, Export and Foreign Exchange Control department (<span translate="no">IUD</span>) of the Ministry of Economic Affairs (EZOTI).</p>
{nov}<div class="bz-acts">{_glink(il["url"], "EZOTI: import, export and licences")}</div>{_gcheck(R, "import_licence")}''')}
{_gcard("Customs contact", f'''<table class="bz-tbl"><tbody>
<tr><td>Address</td><td translate="no">{_esc(cust["address"])}</td></tr><tr><td>Phone</td><td translate="no">{_esc(cust["phone"])}</td></tr>
<tr><td>E-mail</td><td translate="no">{_esc(cust["email"])}</td></tr></tbody></table>
<div class="bz-acts"><a class="bz-btn2" href="government-contacts-suriname.html">All government contacts</a></div>''')}
"""
    return X.page("import-export-suriname.html", "biz-g-import", "Guide", "Import & Export in Suriname",
                  "How a customs declaration works, what you pay on imports and which goods need a licence.",
                  body, _GUIDE_JS, {}, None, rule_keys=("customs_procedure", "import", "import_licence", "contacts_belastingdienst"),
                  related=("biz-import", "biz-pricing", "biz-g-contacts"))


def _page_g_finance(X, feeds, prices):
    """business-financing-suriname.html"""
    R = X.R
    n = R["financing_nob"]
    fw = R["contacts_financieringswijzer"]
    rows = "".join(f'<tr><td><b translate="no">{_esc(p["name"])}</b></td><td translate="no">{_esc(p["max"])}</td><td translate="no">{_esc(p["for"])}</td></tr>' for p in n["products"])
    body = f"""
{_gcard("Find every option in one place", f'''<p>The MKB-Financieringswijzer of the Ministry of Economic Affairs lists grants, loans, guarantees and other support for small and medium-sized businesses from public and private organisations, and its SME unit can guide you.</p>
<table class="bz-tbl" style="margin-top:.6rem"><tbody><tr><td>Address</td><td translate="no">{_esc(fw["address"])}</td></tr><tr><td>Phone</td><td translate="no">{_esc(fw["phone"])}</td></tr><tr><td>E-mail</td><td translate="no">{_esc(fw["email"])}</td></tr></tbody></table>
<div class="bz-acts">{_glink(fw["url"], "financieringswijzer.sr")}</div>{_gcheck(R, "contacts_financieringswijzer")}''')}
{_gcard("National Development Bank (NOB)", f'''<p>The NOB offers these products for businesses. Maximum amounts as published by the bank; ask the NOB for the conditions and current interest rates.</p>
<div class="bz-scroll" style="margin-top:.6rem"><table class="bz-tbl" style="min-width:520px"><thead><tr><th>Product</th><th>Maximum</th><th>For</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="bz-src" style="margin-top:.5rem">The names and descriptions are shown as the NOB publishes them, in Dutch.</p>
<table class="bz-tbl" style="margin-top:.6rem"><tbody><tr><td>Address</td><td translate="no">{_esc(n["address"])}</td></tr><tr><td>Phone</td><td translate="no">{_esc(n["phone"])}</td></tr></tbody></table>
<div class="bz-acts">{_glink(n["url"], "nob.sr")}</div>{_gcheck(R, "financing_nob")}''')}
{_gcard("Before you borrow", '''<p>Work out what the monthly payment will be and whether your sales can carry it.</p>''' + _gtools(("biz-loan", "biz-breakeven", "biz-pricing")))}
"""
    return X.page("business-financing-suriname.html", "biz-g-finance", "Guide", "Business Financing in Suriname",
                  "Loans, guarantees and support for Surinamese businesses: the government's financing map and the National Development Bank.",
                  body, _GUIDE_JS, {}, None, rule_keys=("contacts_financieringswijzer", "financing_nob"),
                  related=("biz-loan", "biz-breakeven", "biz-g-start"))


def _page_g_contacts(X, feeds, prices):
    """government-contacts-suriname.html"""
    R = X.R
    bd = R["contacts_belastingdienst"]
    apf = R["contacts_apf"]
    k = R["contacts_kkf"]
    fw = R["contacts_financieringswijzer"]
    n = R["financing_nob"]
    h = bd["hours"]

    def hrs(s):
        return s.replace("-", " – ")
    offices = "".join(f'<tr><td><span translate="no">{_esc(o["name"])}</span></td><td translate="no">{_esc(o["address"])}</td><td translate="no">{_esc(o["phone"])}'
                      + (f'<br><a href="mailto:{_esc(o["email"])}">{_esc(o["email"])}</a>' if o["email"] else "") + '</td></tr>' for o in bd["offices"])
    body = f"""
{_gcard("Belastingdienst (tax and customs)", f'''<p>Opening hours: Monday to Thursday <b translate="no">{hrs(h["mon_thu"])}</b>, Friday <b translate="no">{hrs(h["fri"])}</b>. Closed on Saturday and Sunday.</p>
<div class="bz-scroll" style="margin-top:.6rem"><table class="bz-tbl" style="min-width:560px"><thead><tr><th>Office</th><th>Address</th><th>Phone / e-mail</th></tr></thead><tbody>{offices}</tbody></table></div>
<div class="bz-acts">{_glink("https://portaal.belastingdienst.sr/OPO/", "Online portal")}{_glink(bd["url"], "All offices and border posts")}</div>{_gcheck(R, "contacts_belastingdienst")}''')}
{_gcard("Pension fund (APF)", f'''<table class="bz-tbl"><tbody><tr><td>Address</td><td translate="no">{_esc(apf["address"])}<br>{_esc(apf["address2"])}</td></tr><tr><td>Phone</td><td translate="no">{_esc(apf["phone"])}</td></tr>
<tr><td>Opening hours</td><td>Monday to Friday <b translate="no">{hrs(apf["hours"]["mon_fri"])}</b></td></tr></tbody></table>
<div class="bz-acts">{_glink(apf["url"], "pensioen.sr")}</div>{_gcheck(R, "contacts_apf")}''')}
{_gcard("Chamber of Commerce (KKF)", f'''<table class="bz-tbl"><tbody><tr><td>Address</td><td translate="no">{_esc(k["address"])}</td></tr><tr><td>Phone</td><td translate="no">{_esc(k["phone"])}</td></tr></tbody></table>
<div class="bz-acts">{_glink(k["web"], "kkf.sr")}</div>{_gcheck(R, "contacts_kkf")}''')}
{_gcard("Financing", f'''<table class="bz-tbl"><tbody>
<tr><td><span translate="no">MKB-Financieringswijzer</span></td><td translate="no">{_esc(fw["address"])}</td><td translate="no">{_esc(fw["phone"])}</td></tr>
<tr><td><span translate="no">Nationale Ontwikkelingsbank (NOB)</span></td><td translate="no">{_esc(n["address"])}</td><td translate="no">{_esc(n["phone"])}</td></tr>
</tbody></table><div class="bz-acts"><a class="bz-btn2" href="business-financing-suriname.html">Financing guide</a></div>''')}
{_gcard("Online services", f'''<table class="bz-tbl"><tbody>
<tr><td>{_glink("https://portaal.belastingdienst.sr/OPO/", "Belastingdienst portal")}</td><td>Register a business or employer, file tax returns.</td></tr>
<tr><td>{_glink(R["btw"][-1]["annex_links"]["register"], "BTW register")}</td><td>Check whether a business is registered for BTW.</td></tr>
<tr><td>{_glink("https://asycuda.belastingdienst.sr/", "ASYCUDA")}</td><td>Customs declarations and the import tariff.</td></tr>
<tr><td>{_glink(R["cbb_online"]["portal"], "digitale-id.gov.sr")}</td><td>Civil-registry extracts, free.</td></tr>
<tr><td>{_glink("https://vergunningen.gov.sr/", "vergunningen.gov.sr")}</td><td>Business licences and other permits.</td></tr>
<tr><td>{_glink(R["import_licence"]["url"], "EZOTI: import and export")}</td><td>Import, export and transit licences.</td></tr>
</tbody></table>''')}
"""
    return X.page("government-contacts-suriname.html", "biz-g-contacts", "Guide", "Government Contacts for Businesses",
                  "Addresses, phone numbers, opening hours and online services of the Belastingdienst, customs, APF, KKF and financing bodies.",
                  body, _GUIDE_JS, {}, None, rule_keys=("contacts_belastingdienst", "contacts_apf", "contacts_kkf", "contacts_financieringswijzer", "financing_nob", "cbb_online"),
                  related=("biz-deadlines", "biz-g-start", "biz-g-import"))
