"""
Douanekoers (customs exchange rate) for the Market Rates page.

LEGAL BASIS
  Art. 17 lid 1 Wet Tarief van Invoerrechten 1996 (S.B. 1995 no. 111; art. 17
  unchanged by S.B. 2004 no. 79): foreign-currency values are converted "naar de
  door de Centrale Bank vastgestelde verkoopkoers, zoals die van kracht is op de
  tweede werkdag in de periode van twee weken waarin de dag van de aangifte valt."
  Lid 2 lets the Minister pick another moment after a parity change (rare; not
  reflected in the CBvS list, hence the "source: CBvS" wording on the page).

SOURCE (the only one we use)
  CBvS "Uitgebreid wisselkoersenoverzicht - verkoopkoersen SRD van kracht m.i.v."
    {BASE}/{YYYY}/UWKOVZ-{DDMMYYYY}.pdf    (Dutch)
    {BASE}/{YYYY}/UWKOVZ-{DDMMYYYY}E.pdf   (English; sometimes the ONLY one, e.g. 26-08-2025)
  There is no working index page on cbvs.sr, so we probe by date. A missing
  file answers 302 -> HTML error page, so we never follow redirects and only
  accept a body that starts with %PDF.

CYCLE
  Verified Jan 2024 - Sep 2026 (72 lists): periods start on Mondays on a fixed
  14-day grid (ANCHOR). The list appears on the 2nd working day: Tuesday, or
  Wednesday when the Monday or Tuesday is a holiday. We do NOT rely on that
  maths to pick the data: the newest valid PDF dated <= today wins, and the
  date printed inside the PDF must equal the file-name date. The grid is only
  used to (a) avoid probing when the cached list is current and (b) display
  the period / next expected date. A list on an unexpected day is logged as
  a DRIFT warning (CBvS changed schedule -> update ANCHOR).

FAIL-SAFE
  Any fetch/parse/validation problem keeps the last good list from
  data/douanekoers.json. The page never shows an unvalidated number.
"""
import datetime as dt
import json
import re
import urllib.request
from pathlib import Path

BASE = "https://www.cbvs.sr/images/content/publicaties/Douanekoersen"
_HERE = Path(__file__).resolve().parent
CACHE_PATH = _HERE / "data" / "douanekoers.json"
HOLIDAY_FILES = (_HERE / "data" / "holidays.json", _HERE / "data" / "biz_holidays_extra.json")

ANCHOR = dt.date(2026, 9, 21)   # a Monday that starts a customs-rate period
PERIOD = 14
MAX_BACK_DAYS = 16              # full scan window when the cache is empty/old
MAX_PROBES = 24                 # hard cap on HTTP requests per build
TIME_BUDGET_S = 60              # hard cap on time spent probing per build
HISTORY_KEEP = 30               # ~14 months of USD/EUR history
MAX_DEV_VS_CBVS = 0.10          # USD may differ at most 10% from today's CBvS giraal sell
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

NAMES = {
    "USD": "US Dollar", "EUR": "Euro", "GBP": "British Pound", "XCG": "Caribbean Guilder",
    "CHF": "Swiss Franc", "AWG": "Aruban Florin", "SEK": "Swedish Krona", "DKK": "Danish Krone",
    "NOK": "Norwegian Krone", "CAD": "Canadian Dollar", "AUD": "Australian Dollar",
    "JPY": "Japanese Yen", "HKD": "Hong Kong Dollar", "BBD": "Barbados Dollar",
    "BSD": "Bahamian Dollar", "BZD": "Belize Dollar", "XCD": "East Caribbean Dollar",
    "TTD": "Trinidad & Tobago Dollar", "GYD": "Guyana Dollar", "INR": "Indian Rupee",
    "BRL": "Brazilian Real", "CNY": "Chinese Yuan", "ANG": "Antillean Guilder",
}


# ── dates ────────────────────────────────────────────────────────────────────
def period_start(d):
    """Monday that starts the 14-day customs period containing d."""
    return ANCHOR + dt.timedelta(days=PERIOD * ((d - ANCHOR).days // PERIOD))


def load_holidays():
    out = set()
    for p in HOLIDAY_FILES:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        blocks = [data] + list((data.get("years") or {}).values())
        for b in blocks:
            for h in (b.get("public") or []):
                try:
                    out.add(dt.date.fromisoformat(h["date"]))
                except Exception:
                    pass
    return out


def second_working_day(start, holidays):
    n, d = 0, start
    while True:
        if d.weekday() < 5 and d not in holidays:
            n += 1
            if n == 2:
                return d
        d += dt.timedelta(days=1)


def pdf_url(d, english=False):
    return f"{BASE}/{d.year}/UWKOVZ-{d:%d%m%Y}{'E' if english else ''}.pdf"


# ── fetch + parse ────────────────────────────────────────────────────────────
class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def fetch_pdf(url, timeout=10):
    """PDF bytes, or None for anything that is not a real PDF (302s, HTML error pages)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
        with _OPENER.open(req, timeout=timeout) as r:
            if r.status != 200:
                return None
            body = r.read(2_000_000)
    except Exception:
        return None
    return body if body[:5] == b"%PDF-" else None


def pdf_text(data):
    try:
        import io
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(data)).pages)
    except ImportError:
        import subprocess
        r = subprocess.run(["pdftotext", "-layout", "-", "-"], input=data,
                           capture_output=True, timeout=30, check=True)
        return r.stdout.decode("utf-8", "replace")


_ROW = re.compile(r'^\s*(?P<name>\S.*?)\s*\(\s*PER\s+(?P<code>[A-Z]{3})\s+(?P<unit>[\d.,]+)\s*\)'
                  r'\s*(?:SRD|")?\s*(?P<val>\d[\d.,]*)\s*$')
_NL_DATE = re.compile(r'M\.\s*I\.\s*V\.?\s*:?\s*(\d{2})-(\d{2})-(\d{4})')
_EN_DATE = re.compile(r'VALID\s+STARTING\s*:?\s*(\d{2})/(\d{2})/(\d{4})')


def _num(s, lang):
    s = s.strip()
    s = s.replace(".", "").replace(",", ".") if lang == "nl" else s.replace(",", "")
    return float(s)


def parse(text):
    """{'valid_from': date, 'lang': 'nl'|'en', 'rates': [{code,name,unit,rate}]}; raises ValueError."""
    m = _NL_DATE.search(text)
    lang = "nl"
    if not m:
        m = _EN_DATE.search(text)
        lang = "en"
    if not m:
        raise ValueError("no validity date found")
    dd, mm, yy = (int(x) for x in m.groups())
    valid_from = dt.date(yy, mm, dd)
    rates, seen = [], set()
    for line in text.splitlines():
        r = _ROW.match(line)
        if not r:
            continue
        code = r["code"]
        if code in seen:
            continue
        unit = int(re.sub(r"[.,]", "", r["unit"]))
        rates.append({"code": code, "name": NAMES.get(code, r["name"].strip().title()),
                      "unit": unit, "rate": round(_num(r["val"], lang), 4)})
        seen.add(code)
    return {"valid_from": valid_from, "lang": lang, "rates": rates}


def validate(parsed, expected_date, ref_usd=None):
    """List of problems (empty = OK)."""
    errs = []
    if parsed["valid_from"] != expected_date:
        errs.append(f"date inside PDF {parsed['valid_from']} != file date {expected_date}")
    by = {r["code"]: r for r in parsed["rates"]}
    if len(by) < 10:
        errs.append(f"only {len(by)} currencies parsed")
    usd, eur = by.get("USD"), by.get("EUR")
    if not usd or not eur:
        errs.append("USD or EUR missing")
        return errs
    if usd["unit"] != 1 or eur["unit"] != 1:
        errs.append("USD/EUR unit is not 1")
    if not (5 < usd["rate"] < 500):
        errs.append(f"USD {usd['rate']} outside sane range")
    if not (0.8 < eur["rate"] / usd["rate"] < 1.6):
        errs.append(f"EUR/USD ratio {eur['rate'] / usd['rate']:.3f} implausible")
    if any(r["rate"] <= 0 for r in parsed["rates"]):
        errs.append("non-positive rate")
    if ref_usd and abs(usd["rate"] / ref_usd - 1) > MAX_DEV_VS_CBVS:
        errs.append(f"USD {usd['rate']} deviates >{MAX_DEV_VS_CBVS:.0%} from CBvS giraal sell {ref_usd}")
    return errs


# ── cache ────────────────────────────────────────────────────────────────────
def load_cache(path=CACHE_PATH):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache, path=CACHE_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _entry(parsed, url):
    return {"valid_from": parsed["valid_from"].isoformat(), "lang": parsed["lang"], "url": url,
            "fetched_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).strftime("%Y-%m-%d %H:%M"),
            "rates": parsed["rates"]}


def _usd_eur(entry):
    by = {r["code"]: r["rate"] for r in entry["rates"]}
    return {"valid_from": entry["valid_from"], "USD": by.get("USD"), "EUR": by.get("EUR")}


# ── main entry point ─────────────────────────────────────────────────────────
def update(today=None, ref_usd=None, cache_path=CACHE_PATH, fetch=fetch_pdf, log=print):
    """Refresh the cache if a newer list should exist; return render state (dict) or None."""
    today = today or dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date()
    cache = load_cache(cache_path)
    cur = cache.get("current")
    cur_date = dt.date.fromisoformat(cur["valid_from"]) if cur else None

    if cur_date is None or cur_date < period_start(today):
        p_today = period_start(today)
        if cur_date and cur_date >= p_today - dt.timedelta(days=PERIOD):
            lo = p_today                      # normal case: only look inside the new period
        else:                                 # empty or older cache: wide scan
            lo = max(cur_date + dt.timedelta(days=1) if cur_date else today - dt.timedelta(days=MAX_BACK_DAYS),
                     today - dt.timedelta(days=MAX_BACK_DAYS))
        cands = [today - dt.timedelta(days=i) for i in range((today - lo).days + 1)]
        cands = [d for d in cands if d.weekday() < 5]
        import time as _time
        t0 = _time.monotonic()
        probes, found = 0, None
        for d in cands:
            if _time.monotonic() - t0 > TIME_BUDGET_S:
                log(f"  Douanekoers: time budget hit after {probes} probes")
                break
            for english in (False, True):
                if probes >= MAX_PROBES:
                    break
                url = pdf_url(d, english)
                probes += 1
                data = fetch(url)
                if not data:
                    continue
                try:
                    parsed = parse(pdf_text(data))
                except Exception as e:
                    log(f"  Douanekoers: parse failed for {url}: {e}")
                    continue
                errs = validate(parsed, d, ref_usd)
                if errs:
                    log(f"  Douanekoers: REJECTED {url}: {'; '.join(errs)}")
                    continue
                found = _entry(parsed, url)
                break
            if found:
                break
        if found:
            if cur:
                hist = [h for h in cache.get("history", []) if h["valid_from"] != cur["valid_from"]]
                hist.append(_usd_eur(cur))
                cache["history"] = hist[-HISTORY_KEEP:]
                cache["previous"] = cur
            cache["current"] = found
            save_cache(cache, cache_path)
            cur, cur_date = found, dt.date.fromisoformat(found["valid_from"])
            log(f"  Douanekoers: NEW list m.i.v. {cur_date} ({probes} probes) {found['url']}")
        else:
            log(f"  Douanekoers: no newer list yet ({probes} probes); keeping "
                f"{cur_date or 'nothing'}")
    else:
        log(f"  Douanekoers: cached list m.i.v. {cur_date} is current (no fetch)")

    if not cur:
        return None

    hol = load_holidays()
    p0 = period_start(cur_date)
    exp = second_working_day(p0, hol)
    if cur_date != exp:
        log(f"  Douanekoers: NOTE list dated {cur_date:%a %d-%m-%Y}, grid expected {exp:%a %d-%m-%Y}. "
            f"Fine if a holiday is missing from data/holidays.json; if it repeats without holidays, "
            f"CBvS changed its cycle: update ANCHOR in douane.py.")
    next_start = p0 + dt.timedelta(days=PERIOD)
    return {
        "current": cur,
        "previous": cache.get("previous"),
        "period_start": p0,
        "period_end": next_start - dt.timedelta(days=1),
        "next_period_start": next_start,
        "next_expected": second_working_day(next_start, hol),
        "pending": today >= next_start,                      # new period started, list not out yet
        "stale": today >= next_start + dt.timedelta(days=PERIOD),  # a whole cycle missed
        "today": today,
    }


# ── converter helper ─────────────────────────────────────────────────────────
def per_unit_map(state):
    """{code: SRD per 1 unit} for the currency converter; {} when unavailable/stale."""
    if not state or state.get("stale"):
        return {}
    return {r["code"]: round(r["rate"] / r["unit"], 6) for r in state["current"]["rates"]}


# ── HTML ─────────────────────────────────────────────────────────────────────
def _fmt(v):
    return f"{v:,.2f}"


def _ds(d):
    """Date for the page; build_i18n rewrites data-srdate-long into NL/ES."""
    return f'<span data-srdate-long="{d.isoformat()}">{_d(d)}</span>'


def _d(d):
    return f"{d:%a} {d.day} {d:%b %Y}"


def render_section(state, esc):
    """Card HTML for currency.html. esc = html.escape."""
    head = '''
  <section id="douanekoers" class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden mt-8">
    <div class="px-6 py-5 border-b border-gray-100">
      <div class="flex items-start justify-between gap-2">
        <div>
          <h2 class="font-bold text-gray-900 text-base">Douanekoers (Customs Exchange Rate) {badge}</h2>
          <p class="text-gray-400 text-xs mt-0.5">Official rate for converting import values to SRD for customs duties</p>
        </div>
        <a href="{src}" target="_blank" rel="noopener noreferrer"
           class="text-xs font-semibold shrink-0 hover:underline" style="color:var(--forest2)">CBvS PDF &#8599;</a>
      </div>
      {meta}
    </div>'''
    legal = ('<p class="text-gray-400 text-xs px-6 py-4 border-t border-gray-100 leading-relaxed">'
             'Source: Centrale Bank van Suriname, &#8220;Uitgebreid wisselkoersenoverzicht&#8221; (selling rates, '
             'drafts, cheques and transfers). Legal basis: art. 17 Wet Tarief van Invoerrechten 1996: a declaration '
             'uses the CBvS selling rate in force on the second working day of the two-week period in which it is filed. '
             'The Minister of Finance may set a different moment after a parity change. '
             'Informational only; the rate in the customs system (ASYCUDA) is decisive.</p>')

    if not state or state.get("stale"):
        return (head.format(badge='<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">Unavailable</span>',
                            src="https://www.cbvs.sr/", meta="")
                + '<p class="text-gray-500 text-sm px-6 py-5">The current customs rate list could not be retrieved. '
                  'Please check the Central Bank of Suriname&#8217;s website.</p>' + legal + '</section>')

    cur, prev = state["current"], state.get("previous") or {}
    by = {r["code"]: r for r in cur["rates"]}
    pby = {r["code"]: r for r in prev.get("rates", [])}
    vf = dt.date.fromisoformat(cur["valid_from"])

    if state["pending"]:
        badge = '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">&#9675; New list due</span>'
        notice = ('<div class="mx-6 mt-5 rounded-xl border border-amber-200 p-4 text-amber-900 text-sm leading-relaxed" style="background:#fffbeb">'
                  f'<strong><span>New period started</span> {_ds(state["next_period_start"])}.</strong> '
                  f'<span>CBvS publishes its list on the second working day. Expected:</span> {_ds(state["next_expected"])}. '
                  f'<span>By law that list applies to the whole period, including declarations filed before it appears. Shown below: the list for</span> '
                  f'{_ds(state["period_start"])} &#8211; {_ds(state["period_end"])}.</div>')
    else:
        badge = '<span class="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-green-100 text-green-800">&#9679; Current</span>'
        notice = ""
    meta = (f'<p class="text-gray-500 text-xs mt-2"><span>In force from</span> <strong>{_ds(vf)}</strong> &#183; '
            f'<span>Applies to declarations filed</span> {_ds(state["period_start"])} &#8211; {_ds(state["period_end"])} &#183; '
            f'<span>Next list expected</span> {_ds(state["next_expected"])}</p>')

    tiles = ""
    for code in ("USD", "EUR"):
        r = by[code]
        chg = ""
        if code in pby:
            diff = r["rate"] - pby[code]["rate"]
            if abs(diff) >= 0.005:
                up = diff > 0
                chg = (f'<p class="text-xs font-semibold mt-1" style="color:{"var(--coral)" if up else "var(--forest2)"}">'
                       f'{"&#9650;" if up else "&#9660;"} {abs(diff):.2f} vs previous list ({_fmt(pby[code]["rate"])})</p>')
            else:
                chg = '<p class="text-xs text-gray-400 mt-1">Unchanged vs previous list</p>'
        tiles += (f'<div class="rounded-xl p-4" style="background:var(--mint)">'
                  f'<p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">1 {code}</p>'
                  f'<p class="text-2xl font-bold font-mono text-gray-900">SRD {_fmt(r["rate"])}</p>{chg}</div>')

    rows = ""
    for r in cur["rates"]:
        unit = f'{r["unit"]:,}'
        rows += ('<tr class="border-b border-gray-100 last:border-0">'
                 f'<td class="py-2 px-4 font-semibold text-gray-900 whitespace-nowrap">{esc(r["code"])}</td>'
                 f'<td class="py-2 px-4 text-gray-500 text-sm">{esc(r["name"])}</td>'
                 f'<td class="py-2 px-4 text-right text-gray-500 text-sm whitespace-nowrap">per {unit}</td>'
                 f'<td class="py-2 px-4 text-right font-mono font-bold text-gray-800 whitespace-nowrap">{_fmt(r["rate"])}</td></tr>')

    return (head.format(badge=badge, src=esc(cur["url"]), meta=meta) + notice
            + f'<div class="grid grid-cols-1 sm:grid-cols-2 gap-4 px-6 py-5">{tiles}</div>'
            + '<details class="border-t border-gray-100"><summary class="px-6 py-4 text-sm font-semibold cursor-pointer" '
              f'style="color:var(--forest2)">All {len(cur["rates"])} currencies</summary>'
            + '<div class="overflow-x-auto pb-2"><table class="w-full text-sm"><thead><tr class="bg-gray-50 text-left">'
              '<th class="py-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Code</th>'
              '<th class="py-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide">Currency</th>'
              '<th class="py-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">Unit</th>'
              '<th class="py-2 px-4 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">SRD</th>'
              f'</tr></thead><tbody>{rows}</tbody></table></div></details>'
            + legal + '\n  </section>')
