#!/usr/bin/env python3
"""Business hub feeds: collected OUTSIDE the main site build.

Runs from .github/workflows/biz_feeds.yml (every few hours). It writes small
JSON files in data/ that generate.py only READS, so the ~15-minute site update
job never waits on these websites.

  data/biz_feeds.json   Belastingdienst notices + gov.sr announcements (tenders)
  data/max_prices.json  EZOTI "Publicatielijst basis goederen" (max prices)

Accuracy rules
  * Titles, dates and links are copied verbatim. Nothing is summarised.
  * Max-price rows keep the ORIGINAL text of every field. Prices are never
    recalculated or reformatted.
  * A max-price list is only accepted when its validity period is found and at
    least 90% of the price lines parse. Otherwise the previous good list stays
    and the error is recorded (the page then shows the official PDF link only).
  * On any network error the previous data is kept; the script never deletes
    good data and always exits 0 so it cannot break the workflow.
"""
import datetime as dt
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FEEDS_PATH = ROOT / "data" / "biz_feeds.json"
PRICES_PATH = ROOT / "data" / "max_prices.json"
UA = {"User-Agent": "Mozilla/5.0 (ExploreSuriname business feeds; +https://exploresuriname.com)"}

BELASTINGDIENST_RSS = "https://belastingdienst.sr/feed/"
GOV_BEKENDMAKING_RSS = "https://gov.sr/feed/?post_type=bekendmaking"
RICHTPRIJZEN_PAGE = ("https://gov.sr/ministeries/ministerie-van-economische-zaken-ondernemerschap-"
                     "technologische-innovatie/richtprijzen-basis-en-strategische-goederen/")

TENDER_RE = re.compile(r"aanbesteding|procurement|request for (bids|quotation|proposal)|\bRFB\b|\bRFQ\b|"
                       r"\bRFP\b|inschrijving|het leveren van|levering van|offerte|expression of interest|"
                       r"bids?\b|tender", re.I)
KEEP_DAYS = 60
MAX_ITEMS = 40

NL_MONTHS = {"januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6, "juli": 7,
             "augustus": 8, "september": 9, "oktober": 10, "november": 11, "december": 12,
             "jan": 1, "feb": 2, "febr": 2, "mrt": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
             "sep": 9, "sept": 9, "okt": 10, "nov": 11, "dec": 12}


def now_sr():
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=-3)))


def get(url, timeout=40, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 - keep going, report below
            last = e
            time.sleep(4 * (i + 1))
    raise RuntimeError(f"{url}: {last}")


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def parse_rss(raw):
    """Minimal RSS 2.0 reader (no extra dependency). Returns [{title, link, date}]."""
    root = ET.fromstring(raw)
    out = []
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        pub = (it.findtext("pubDate") or "").strip()
        iso = ""
        try:
            iso = dt.datetime.strptime(pub[:25].strip(), "%a, %d %b %Y %H:%M:%S").date().isoformat()
        except Exception:
            pass
        if title and link.startswith("https://"):
            out.append({"title": title, "link": link, "date": iso})
    return out


def merge(old, new, key="link"):
    seen, res = set(), []
    for it in new + old:
        if it[key] in seen:
            continue
        seen.add(it[key])
        res.append(it)
    cutoff = (now_sr().date() - dt.timedelta(days=KEEP_DAYS)).isoformat()
    res = [r for r in res if not r.get("date") or r["date"] >= cutoff]
    res.sort(key=lambda r: r.get("date", ""), reverse=True)
    return res[:MAX_ITEMS]


def update_feeds():
    data = load(FEEDS_PATH, {"belastingdienst": [], "bekendmakingen": [], "status": {}})
    status = data.setdefault("status", {})
    for key, url in (("belastingdienst", BELASTINGDIENST_RSS), ("bekendmakingen", GOV_BEKENDMAKING_RSS)):
        st = status.setdefault(key, {"source": url})
        try:
            items = parse_rss(get(url))
            if not items:
                raise RuntimeError("feed parsed but contained no items")
            if key == "bekendmakingen":
                for it in items:
                    it["tender"] = bool(TENDER_RE.search(it["title"]))
            data[key] = merge(data.get(key, []), items)
            st.update(ok=now_sr().isoformat(timespec="minutes"), fails=0, error="")
            print(f"{key}: {len(items)} items")
        except Exception as e:  # noqa: BLE001
            st["fails"] = int(st.get("fails", 0)) + 1
            st["error"] = str(e)[:200]
            print(f"{key}: FAILED ({e}); keeping {len(data.get(key, []))} previous items")
    data["updated"] = now_sr().isoformat(timespec="minutes")
    save(FEEDS_PATH, data)


# ── EZOTI max prices ─────────────────────────────────────────────────────────
ROW_RE = re.compile(
    r"^(?P<desc>.+?)\s+(?P<wpack>per\s.+?)\s+SRD\s+(?P<wprice>[\d.,]+\.\d{2})\s+"
    r"(?P<rpack>per\s.+?)\s+SRD\s+(?P<rprice>[\d.,]+\.\d{2})\s*$")
VALID_RE = re.compile(r"Geldigheidsduur:\s*(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})\s*[-–]\s*(\d{1,2})\s+([A-Za-z]+)\.?\s+(\d{4})", re.I)


def _date(d, m, y):
    mm = NL_MONTHS.get(m.lower())
    if not mm:
        raise ValueError(f"unknown month {m}")
    return dt.date(int(y), mm, int(d)).isoformat()


def parse_price_pdf_text(txt):
    m = VALID_RE.search(txt)
    if not m:
        raise ValueError("validity period (Geldigheidsduur) not found")
    start, end = _date(*m.group(1, 2, 3)), _date(*m.group(4, 5, 6))
    rows, candidates = [], 0
    for line in txt.splitlines():
        if line.count("SRD") < 2:
            continue
        candidates += 1
        r = ROW_RE.match(line.strip())
        if not r:
            continue
        desc = r.group("desc").strip()
        parts = re.split(r"\s{2,}", desc)
        product, importer = (parts[0], " ".join(parts[1:])) if len(parts) >= 2 else (desc, "")
        rows.append({"product": product, "importer": importer,
                     "wholesale_pack": re.sub(r"\s+", " ", r.group("wpack")),
                     "wholesale_price": "SRD " + r.group("wprice"),
                     "retail_pack": re.sub(r"\s+", " ", r.group("rpack")),
                     "retail_price": "SRD " + r.group("rprice")})
    if candidates < 20:
        raise ValueError(f"only {candidates} price lines found")
    if len(rows) < 0.9 * candidates:
        raise ValueError(f"parsed {len(rows)} of {candidates} price lines (<90%)")
    return {"valid_from": start, "valid_to": end, "rows": rows, "price_lines": candidates}


SRDCHECK_URL = "https://ez.gov.sr/product/index"
SRDCHECK_HEAD = ["#", "Bestaand product", "Importeur", "Groothandel Verpakking", "Groothandel Prijs",
                 "Kleinhandel Verpakking", "Kleinhandel Prijs"]
PRICE_TXT_RE = re.compile(r"^SRD\s?\d{1,3}(?:[.,]\d{3})*[.,]\d{2}$")


def _cell(h):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def parse_srdcheck(page):
    """Parse the ministry's SRD Check product table. Strict: the header must match,
    the number of rows must equal the count the page itself states, and every
    price must look like a price. Values are kept exactly as published."""
    heads = [_cell(h) for h in re.findall(r"(?s)<th[^>]*>(.*?)</th>", page)]
    if heads[:7] != SRDCHECK_HEAD:
        raise ValueError(f"SRD Check table layout changed: {heads[:7]}")
    m = re.search(r"(\d+)\s+producten", _cell(page))
    if not m:
        raise ValueError("SRD Check product count not found")
    stated = int(m.group(1))
    rows = []
    for tr in re.findall(r"(?s)<tr[^>]*>(.*?)</tr>", page):
        tds = [_cell(td) for td in re.findall(r"(?s)<td[^>]*>(.*?)</td>", tr)]
        if len(tds) != 7:
            continue
        _n, product, importer, wpack, wprice, rpack, rprice = tds
        if not (PRICE_TXT_RE.match(wprice) and PRICE_TXT_RE.match(rprice)) or not product:
            raise ValueError(f"unexpected price text in row {tds}")
        rows.append({"product": product, "importer": importer, "wholesale_pack": wpack,
                     "wholesale_price": wprice, "retail_pack": rpack, "retail_price": rprice})
    if len(rows) != stated or stated < 20:
        raise ValueError(f"SRD Check: {len(rows)} rows parsed, page states {stated}")
    return rows


def update_prices():
    """Two official sources of the same EZOTI list:
      1. SRD Check (ez.gov.sr/product/index): the ministry's live price portal.
         No validity period is shown, so we record when WE first saw a change.
      2. The fortnightly PDF on gov.sr (has a validity period, but gov.sr stopped
         posting new PDFs after the 5-18 Sep 2026 list).
    The page shows SRD Check, unless a newer PDF appears whose period covers today
    and started after the last change we saw on SRD Check. Previous good data is
    kept on any failure."""
    data = load(PRICES_PATH, {})
    now = now_sr().isoformat(timespec="minutes")
    today = now[:10]
    srd = data.get("srdcheck") or {}
    pdf = data.get("pdf") or ({k: data[k] for k in ("pdf_url", "valid_from", "valid_to", "rows", "price_lines", "fetched")
                               if k in data} if data.get("pdf_url") else {})
    # 1. SRD Check
    try:
        rows = parse_srdcheck(get(SRDCHECK_URL).decode("utf-8", "replace"))
        if rows != srd.get("rows"):
            # first observation: we do not know when the ministry changed it
            srd["changed"] = today if srd.get("rows") else ""
            srd["rows"] = rows
        srd.update(url=SRDCHECK_URL, checked=now, error="", fails=0)
        print(f"max prices (SRD Check): {len(rows)} rows")
    except Exception as e:  # noqa: BLE001
        srd.update(checked=now, error=str(e)[:200], fails=int(srd.get("fails", 0)) + 1)
        print("max prices (SRD Check): FAILED", e)
    # 2. gov.sr PDF
    try:
        page = get(RICHTPRIJZEN_PAGE).decode("utf-8", "replace")
        pdfs = []
        for u in re.findall(r'href="(https://gov\.sr/wp-content/uploads/\d{4}/\d{2}/[^"]*[Pp]ublicatielijst[^"]*\.pdf)"', page):
            if u not in pdfs:
                pdfs.append(u)
        if not pdfs:
            raise RuntimeError("no Publicatielijst PDF links on the richtprijzen page")
        newest = pdfs[0]  # the page lists the newest list first
        if pdf.get("pdf_url") != newest or not pdf.get("rows"):
            raw = get(newest, timeout=90)
            with tempfile.TemporaryDirectory() as td:
                pp = Path(td) / "list.pdf"
                pp.write_bytes(raw)
                txt = subprocess.run(["pdftotext", "-layout", str(pp), "-"], capture_output=True, text=True,
                                     check=True).stdout
            parsed = parse_price_pdf_text(txt)
            if pdf.get("valid_from") and parsed["valid_from"] < pdf["valid_from"]:
                raise RuntimeError("newest PDF is older than the stored list; page order changed?")
            pdf = {"pdf_url": newest, **parsed, "fetched": now}
            print(f"max prices (PDF): {len(parsed['rows'])} rows, {parsed['valid_from']} to {parsed['valid_to']}")
        pdf.update(checked=now, error="")
    except Exception as e:  # noqa: BLE001
        pdf.update(checked=now, error=str(e)[:200])
        print("max prices (PDF): FAILED", e)
    # 3. choose what the page shows
    pdf_current = bool(pdf.get("rows")) and pdf.get("valid_from", "") <= today <= pdf.get("valid_to", "")
    pdf_newer = pdf_current and pdf.get("valid_from", "") > (srd.get("changed") or "")
    # A failed SRD Check run keeps its last good rows (never falls back to an older PDF).
    if pdf_newer:
        show = "pdf"
    elif srd.get("rows"):
        show = "srdcheck"
    elif pdf.get("rows"):
        show = "pdf"
    else:
        show = data.get("show", "")
    save(PRICES_PATH, {"show": show, "srdcheck": srd, "pdf": pdf, "source_page": RICHTPRIJZEN_PAGE, "checked": now})
    print("max prices: showing", show or "nothing")


if __name__ == "__main__":
    what = set(sys.argv[1:]) or {"feeds", "prices"}
    if "feeds" in what:
        update_feeds()
    if "prices" in what:
        update_prices()
    sys.exit(0)
