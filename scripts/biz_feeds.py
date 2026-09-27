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


def update_prices():
    data = load(PRICES_PATH, {})
    try:
        page = get(RICHTPRIJZEN_PAGE).decode("utf-8", "replace")
        pdfs = []
        for u in re.findall(r'href="(https://gov\.sr/wp-content/uploads/\d{4}/\d{2}/[^"]*[Pp]ublicatielijst[^"]*\.pdf)"', page):
            if u not in pdfs:
                pdfs.append(u)
        if not pdfs:
            raise RuntimeError("no Publicatielijst PDF links on the richtprijzen page")
        newest = pdfs[0]  # the page lists the newest list first
        if data.get("pdf_url") == newest and data.get("rows"):
            data["checked"] = now_sr().isoformat(timespec="minutes")
            data["error"] = ""
            save(PRICES_PATH, data)
            print("max prices: unchanged", newest)
            return
        raw = get(newest, timeout=90)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "list.pdf"
            p.write_bytes(raw)
            txt = subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True,
                                 check=True).stdout
        parsed = parse_price_pdf_text(txt)
        if data.get("valid_from") and parsed["valid_from"] < data["valid_from"]:
            raise RuntimeError("newest PDF is older than the stored list; page order changed?")
        data = {"pdf_url": newest, "source_page": RICHTPRIJZEN_PAGE, **parsed,
                "fetched": now_sr().isoformat(timespec="minutes"),
                "checked": now_sr().isoformat(timespec="minutes"), "error": ""}
        save(PRICES_PATH, data)
        print(f"max prices: {len(parsed['rows'])} rows, {parsed['valid_from']} to {parsed['valid_to']}")
    except Exception as e:  # noqa: BLE001
        data["error"] = str(e)[:200]
        data["checked"] = now_sr().isoformat(timespec="minutes")
        save(PRICES_PATH, data)
        print("max prices: FAILED", e)


if __name__ == "__main__":
    what = set(sys.argv[1:]) or {"feeds", "prices"}
    if "feeds" in what:
        update_feeds()
    if "prices" in what:
        update_prices()
    sys.exit(0)
