#!/usr/bin/env python3
"""
Explore Suriname: flights data + pages (20 Oct 2026).

Replaces the old 6h/12h FlightRadar24 board in generate.py.

DATA (all free, no paid API):
  1. FlightRadar24 airport schedule (unofficial JSON, the only full board for
     PBM/EAX). Answers from GitHub Actions, Cloudflare-challenges home and
     cloud IPs. Fetched adaptively: every build (~15 min) while a flight is
     within -1h..+3h of now, otherwise hourly. Two calls per airport
     (page 1 = now onwards, page -1 = recent past with actual times).
  2. FlightRadar24 per-flight list (flight/list.json): ~7 days of history per
     flight number. One flight per call, max FL_HIST_PER_BUILD per build, each
     flight once a day. Bootstraps the on-time record.
  3. Caribbean Airlines flight status (caribbean-airlines.com/get/Flight/Status):
     the airline's own NAVBLUE ops feed, with actual block/air times. Used for
     BW flights near now; airline data beats FR24.
  4. Air France-KLM Open Data Flight Status (official, free developer key):
     ONLY when env AFKL_API_KEY is set (GitHub secret). Experimental parser,
     every error is non-fatal. Used for KL flights near now.
  Not used, tested 20 Oct 2026: Copa (DataDome 401), klm.com (hangs), GOL
  (schedule only, needs a token lifted from their JS), SLM / Fly Allways /
  Gum Air (static timetables only), ADS-B feeds (adsb.fi, adsb.lol, OpenSky:
  zero receivers over Suriname), aviationstack / FlightAware / AeroDataBox free
  tiers (non-commercial or too small).

FILES:
  flights_cache.json / flights_cache_smeg.json   board cache per airport (v2)
  data/flights_live.json      what the board + flight pages re-read in the browser
  data/flight_history.json    every flight we saw (sched / est / actual), 200 days
  data/flights_meta.json      per-source health + last fetch times

Nothing here may break the build: every network call is wrapped, a failed
source keeps the last good copy, and pages render from whatever exists.
"""

import json
import os
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

SR = timezone(timedelta(hours=-3))

AIRPORTS = [
    {"icao": "SMJP", "iata": "PBM", "name": "Johan Adolf Pengel International Airport",
     "short": "Johan Adolf Pengel", "place": "Zanderij", "cache": "flights_cache.json",
     "lat": 5.4528, "lon": -55.1878},
    {"icao": "SMEG", "iata": "EAX", "name": "Eduard Alexander Gummels Airport",
     "short": "Eduard Alexander Gummels", "place": "Zorg en Hoop, Paramaribo",
     "cache": "flights_cache_smeg.json", "lat": 5.8108, "lon": -55.1908},
]
AP_BY_IATA = {a["iata"]: a for a in AIRPORTS}

HISTORY_PATH = "data/flight_history.json"
LIVE_PATH = "data/flights_live.json"
META_PATH = "data/flights_meta.json"
HISTORY_DAYS = 200
FL_HIST_PER_BUILD = 3          # FR24 flight/list calls per build
TTL_BUSY_S = 13 * 60           # a flight within -1h..+3h: refresh every build
TTL_QUIET_S = 55 * 60
TTL_ERROR_S = 25 * 60
ON_TIME_MIN = 15               # industry standard: within 15 minutes

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

# ── reference data ────────────────────────────────────────────────────────────
# Airline display names by IATA code (FR24 sometimes says "KLM Asia" etc.).
AIRLINES = {
    "KL": {"name": "KLM", "site": "https://www.klm.com/", "listing": "klm-royal-dutch-airlines",
           "phone": "+31 20 474 7746"},
    "CM": {"name": "Copa Airlines", "site": "https://www.copaair.com/", "listing": "copa-airlines",
           "phone": "+597 880-0909"},
    "PY": {"name": "Surinam Airways", "site": "https://www.flyslm.com/", "listing": "surinam-airways",
           "phone": "+597 432700"},
    "BW": {"name": "Caribbean Airlines", "site": "https://www.caribbean-airlines.com/",
           "listing": "caribbean-airlines", "phone": "+597 520034"},
    "G3": {"name": "GOL", "site": "https://www.voegol.com.br/", "phone": "+55 11 5504-4410"},
    "8W": {"name": "Fly Allways", "site": "https://flyallways.com/", "listing": "fly-allways",
           "phone": "+597 430370"},
    "M6": {"name": "Amerijet", "site": "https://www.amerijet.com/", "cargo": True},
    "W8": {"name": "Cargojet", "site": "https://www.cargojet.com/", "cargo": True},
    "5Y": {"name": "Atlas Air", "cargo": True},
    "AA": {"name": "American Airlines", "site": "https://www.aa.com/"},
    "B6": {"name": "JetBlue", "site": "https://www.jetblue.com/"},
    "TX": {"name": "Air Caraïbes", "site": "https://www.aircaraibes.com/"},
    "AF": {"name": "Air France", "site": "https://www.airfrance.com/"},
    "HV": {"name": "Transavia", "site": "https://www.transavia.com/"},
    "OR": {"name": "TUI fly", "site": "https://www.tui.nl/"},
}
# By ICAO when FR24 gives no IATA (regional / charter operators).
AIRLINES_ICAO = {
    "GUM": {"name": "Gum Air", "site": "https://gumair.sr/", "listing": "gum-air"},
    "TGY": {"name": "Trans Guyana Airways", "site": "https://transguyana.net/"},
    "BWG": {"name": "Blue Wing Airlines", "listing": "blue-wing-airlines"},
    "AJT": {"name": "Amerijet", "cargo": True},
    "CJT": {"name": "Cargojet", "cargo": True},
    "GTI": {"name": "Atlas Air", "cargo": True},
    "KLM": {"name": "KLM"}, "SLM": {"name": "Surinam Airways"}, "CMP": {"name": "Copa Airlines"},
    "BWA": {"name": "Caribbean Airlines"}, "GLO": {"name": "GOL"},
}
CARGO_WORDS = re.compile(r"cargo|freight|express|amerijet|cargojet|atlas air|fedex|ups\b|dhl", re.I)

# Place names people actually use (FR24 gives airport names / odd cities).
CITY = {
    "AMS": "Amsterdam", "PTY": "Panama City", "POS": "Port of Spain", "BGI": "Barbados",
    "CUR": "Curaçao", "AUA": "Aruba", "SXM": "Sint Maarten", "BEL": "Belém",
    "GEO": "Georgetown", "OGL": "Georgetown (Ogle)", "CAY": "Cayenne", "MIA": "Miami",
    "FLL": "Fort Lauderdale", "JFK": "New York", "HAV": "Havana", "SCU": "Santiago de Cuba",
    "CMW": "Camagüey", "SDQ": "Santo Domingo", "MAO": "Manaus", "BVB": "Boa Vista",
    "GRU": "São Paulo", "MCP": "Macapá", "PBM": "Paramaribo", "EAX": "Paramaribo (Zorg en Hoop)",
    "ORG": "Paramaribo (Zorg en Hoop)", "BRU": "Brussels", "CDG": "Paris", "ORY": "Paris",
    "LIS": "Lisbon", "MAD": "Madrid", "PTP": "Guadeloupe", "FDF": "Martinique",
    "ANU": "Antigua", "SJU": "San Juan", "KTO": "Kato", "ICK": "Nieuw Nickerie",
}

# Typical drive times TO the airports (minutes, normal traffic). Rough by
# design: the page always says "about" and links Waze for the live figure.
DRIVE = {
    "PBM": [("pmb", "Paramaribo centre", 55), ("noord", "Paramaribo Noord", 60),
            ("lely", "Lelydorp", 25), ("meer", "Meerzorg / Commewijne", 65), ("here", "At the airport", 0)],
    "EAX": [("pmb", "Paramaribo centre", 15), ("lely", "Lelydorp", 30),
            ("meer", "Meerzorg / Commewijne", 25), ("here", "At the airport", 0)],
}
# Check-in times published by Johan Adolf Pengel Airport (japi-airport.com,
# "Check-In Times"): Amsterdam flights open 5h and close 2h before departure,
# all regional flights open 3h and close 2h before. Hours.
CHECKIN = {"AMS": (5, 2), "_": (3, 2)}

# ── small helpers ─────────────────────────────────────────────────────────────

def _g(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
        if d is None:
            return default
    return d


def _num(v):
    try:
        return int(v) if v not in (None, "", 0) else None
    except Exception:
        return None


def _now():
    return int(time.time())


def _sr(ts):
    return datetime.fromtimestamp(ts, SR)


def _http_json(url, data=None, headers=None, timeout=20, method=None):
    h = {"User-Agent": UA, "Accept": "application/json, text/javascript, */*",
         "Accept-Language": "en-US,en;q=0.9"}
    h.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, obj, compact=True):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        if compact:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
        else:
            json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def airline_info(ai, icao="", name=""):
    a = AIRLINES.get(ai or "") or AIRLINES_ICAO.get(icao or "") or {}
    out = dict(a)
    if not out.get("name"):
        n = (name or "").strip()
        if n.lower() in ("", "unknown", "none"):
            n = ""
        out["name"] = n
    if "cargo" not in out:
        out["cargo"] = bool(CARGO_WORDS.search(out.get("name") or ""))
    return out


def city_of(iata, fr24_city="", fr24_name=""):
    if iata in CITY:
        return CITY[iata]
    c = (fr24_city or "").strip()
    if c:
        return c
    n = (fr24_name or "").replace(" International Airport", "").replace(" Airport", "").strip()
    return n or iata or "?"


def aircraft_short(text):
    t = (text or "").strip()
    if not t:
        return ""
    m = re.match(r"^(Airbus|Boeing|Embraer|ATR|De Havilland Canada|De Havilland|Bombardier|Cessna|"
                 r"Britten-Norman|Pilatus|Beechcraft|Let|Dornier|Fokker|McDonnell Douglas)\s+"
                 r"(?:Dash\s+)?([A-Z]{0,3}-?\d+[A-Z]?)", t)
    if m:
        brand, model = m.group(1), m.group(2)
        brand = {"De Havilland Canada": "Dash", "De Havilland": "Dash"}.get(brand, brand)
        if brand in ("Boeing", "Airbus"):
            model = re.sub(r"^(\d{3})-?\d*.*$", r"\1", model) if brand == "Boeing" else re.sub(r"^(A?\d{3}).*$", r"\1", model)
            if brand == "Airbus" and not model.startswith("A"):
                model = "A" + model
        return f"{brand} {model}".strip()
    return t[:28]


def fn_norm(s):
    return re.sub(r"\s+", "", (s or "").upper())


def slug_of(fn):
    return "flight-" + re.sub(r"[^a-z0-9]", "", fn.lower())


# ── status normalisation ──────────────────────────────────────────────────────
# Normalised states: scheduled, delayed, boarding?(not available), departed,
# enroute, landed, cancelled, diverted, unknown.
_HHMM = re.compile(r"(\d{1,2}):(\d{2})")


def _hhmm_near(text, ref_ts):
    """'Estimated dep 17:39' -> epoch on the SR day closest to ref_ts."""
    m = _HHMM.search(text or "")
    if not m or not ref_ts:
        return None
    ref = _sr(ref_ts)
    best = None
    for dd in (-1, 0, 1):
        day = (ref + timedelta(days=dd)).date()
        cand = datetime(day.year, day.month, day.day, int(m.group(1)) % 24, int(m.group(2)), tzinfo=SR)
        c = int(cand.timestamp())
        if best is None or abs(c - ref_ts) < abs(best - ref_ts):
            best = c
    return best


def classify(direction, sched, est, act, generic, text, live=False, diverted=None, now=None):
    """Return (state, delay_minutes_or_None). direction 'A' or 'D'."""
    now = now or _now()
    g = (generic or "").lower()
    t = (text or "").lower()
    if g in ("canceled", "cancelled") or t.startswith("cancel"):
        return "cancelled", None
    if diverted or g == "diverted" or t.startswith("diverted"):
        return "diverted", None
    ref = act or est
    delay = int(round((ref - sched) / 60)) if (ref and sched) else None
    if direction == "A":
        if act or g == "landed" or t.startswith("landed"):
            return "landed", delay
        if live:
            return ("delayed" if (delay or 0) >= ON_TIME_MIN else "enroute"), delay
    else:
        if act or g == "departed" or t.startswith("departed"):
            return "departed", delay
    if delay is not None and delay >= ON_TIME_MIN:
        return "delayed", delay
    if g == "delayed" or t.startswith("delayed"):
        return "delayed", delay
    if sched and sched < now - 3 * 3600 and not (est or act):
        return "unknown", None
    return "scheduled", delay


# ── FR24 parsing ──────────────────────────────────────────────────────────────

def parse_fr24(item, our_iata, now=None):
    """One FR24 FlightListItem (dict with identification/status/...) -> record
    relative to OUR airport, or None when it doesn't touch our airport."""
    fl = item.get("flight", item) if isinstance(item, dict) else None
    if not isinstance(fl, dict):
        return None
    ori = _g(fl, "airport", "origin") or {}
    dst = _g(fl, "airport", "destination") or {}
    oi = _g(ori, "code", "iata") or ""
    di = _g(dst, "code", "iata") or ""
    if di == our_iata:
        direction, other = "A", ori
    elif oi == our_iata:
        direction, other = "D", dst
    elif not di and oi and oi != our_iata:
        direction, other = "A", ori        # airport board: our side is omitted
    elif not oi and di and di != our_iata:
        direction, other = "D", dst
    else:
        return None
    fn = fn_norm(_g(fl, "identification", "number", "default") or _g(fl, "identification", "callsign") or "")
    if not fn:
        return None
    t = fl.get("time") or {}
    key_t = "arrival" if direction == "A" else "departure"
    sched = _num(_g(t, "scheduled", key_t))
    if not sched:
        return None
    sd = _num(_g(t, "scheduled", "departure"))
    sa = _num(_g(t, "scheduled", "arrival"))
    real = _num(_g(t, "real", key_t))
    est = _num(_g(t, "estimated", key_t))
    if direction == "A" and not est:
        est = _num(_g(t, "other", "eta"))
    st = fl.get("status") or {}
    text = st.get("text") or ""
    generic = _g(st, "generic", "status", "text") or ""
    ev = _num(_g(st, "generic", "eventTime", "utc"))
    tl = text.lower()
    if not real and (tl.startswith("landed") or tl.startswith("departed") or generic in ("landed", "departed")):
        real = ev or _hhmm_near(text, sched)
    if not est and not real and (tl.startswith("estimated") or tl.startswith("delayed")):
        est = ev or _hhmm_near(text, sched)
    diverted = _g(st, "generic", "status", "diverted") or _g(fl, "airport", "real", "code", "iata")
    live = bool(st.get("live"))
    state, delay = classify(direction, sched, est, real, generic, text, live, diverted, now)
    al = fl.get("airline") or {}
    ai = _g(al, "code", "iata") or ""
    aicao = _g(al, "code", "icao") or ""
    if not ai and not aicao:
        m = re.match(r"^([A-Z0-9]{2})\d", fn)
        ai = m.group(1) if m else ""
    info = airline_info(ai, aicao, al.get("name") or "")
    ac = _g(fl, "aircraft", "model", "text") or ""
    rec = {
        "fn": fn, "al": info.get("name") or "", "ai": ai or aicao, "d": direction, "ap": our_iata,
        "oi": _g(other, "code", "iata") or "", "on": city_of(_g(other, "code", "iata") or "",
                                                          _g(other, "position", "region", "city") or "",
                                                          other.get("name") or ""),
        "occ": _g(other, "position", "country", "name") or "",
        "oz": _num(_g(other, "timezone", "offset")) if _g(other, "timezone", "offset") not in (None, "") else None,
        "s": sched, "sd": sd, "sa": sa, "e": est, "a": real, "st": state, "dl": delay,
        "ac": aircraft_short(ac), "acc": _g(fl, "aircraft", "model", "code") or "",
        "rg": _g(fl, "aircraft", "registration") or "", "cg": 1 if info.get("cargo") else 0,
        "tx": text[:40], "src": "fr24",
    }
    if diverted:
        rec["dv"] = diverted
    rec["known"] = bool(info.get("name"))
    return rec


def rec_key(r):
    return _sr(r["s"]).strftime("%Y-%m-%d") + "|" + r["fn"] + "|" + r["d"] + "|" + r["ap"]


def merge_board(recs):
    """Codeshares + multi-leg duplicates -> one row each.
    1) same direction, other airport and scheduled time (5 min) = codeshare:
       keep the entry with a known airline, the others become 'cs'.
    2) same flight number + direction on the same SR day with different other
       airports = multi-leg (FR24 lists each itinerary): keep the leg that
       touches us (latest departure for arrivals, earliest arrival for
       departures), the rest become 'via'."""
    groups = {}
    for r in recs:
        k = (r["d"], r["oi"], r["s"] // 300)
        groups.setdefault(k, []).append(r)
    out = []
    for g in groups.values():
        g.sort(key=lambda r: (not r.get("known"), not r.get("rg"), r["fn"]))
        p = dict(g[0])
        cs = []
        for x in g[1:]:
            # two different aircraft at the same minute are two real flights, not a codeshare
            if x.get("rg") and p.get("rg") and x["rg"] != p["rg"]:
                out.append(dict(x))
            elif x["fn"] != p["fn"]:
                cs.append(x["fn"])
        if cs:
            p["cs"] = sorted(set(cs))
        out.append(p)
    by_fn = {}
    for r in out:
        by_fn.setdefault((r["fn"], r["d"], _sr(r["s"]).date()), []).append(r)
    final = []
    for (fn, d, _day), g in by_fn.items():
        if len(g) == 1:
            final.append(g[0])
            continue
        if d == "A":
            g.sort(key=lambda r: -(r.get("sd") or 0))
            p = dict(g[0])
            p["via"] = [x["on"] for x in sorted(g[1:], key=lambda r: r.get("sd") or 0)]
            p["vfirst"] = 1      # via airports come BEFORE p["on"]
        else:
            g.sort(key=lambda r: (r.get("sa") or 0))
            p = dict(g[0])
            p["via"] = [x["on"] for x in g[1:]]
        final.append(p)
    final.sort(key=lambda r: r["s"])
    for r in final:
        r.pop("known", None)
    return final


# ── FR24 fetching ─────────────────────────────────────────────────────────────

def _fr24_airport(icao, page):
    url = ("https://api.flightradar24.com/common/v1/airport.json"
           f"?code={icao}&plugin[]=schedule&limit=100&page={page}")
    return _http_json(url, headers={"Referer": "https://www.flightradar24.com/"})


def fetch_board(ap, cache, now=None, log=print):
    """Returns (records, ok, fetched_ts). Uses cache when fresh."""
    now = now or _now()
    recs = cache.get("flights") if cache.get("v") == 2 else None
    fetched = cache.get("fetched", 0) or 0
    if recs is not None:
        busy = any(-3600 <= ((r.get("a") or r.get("e") or r["s"]) - now) <= 3 * 3600 for r in recs)
        ttl = TTL_BUSY_S if busy else TTL_QUIET_S
        if not cache.get("ok", True):
            ttl = TTL_ERROR_S
        if now - (cache.get("tried") or fetched) < ttl:
            log(f"  flights [{ap['iata']}]: cache ({int((now - fetched) / 60)} min old)")
            return recs, bool(cache.get("ok")), fetched
    raw, ok = [], False
    for page in (1, -1):
        try:
            data = _fr24_airport(ap["icao"], page)
            sched = _g(data, "result", "response", "airport", "pluginData", "schedule") or {}
            for side in ("arrivals", "departures"):
                for e in (_g(sched, side, "data") or []):
                    raw.append(e)
            if page == 1:
                ok = True
        except Exception as e:
            log(f"  flights [{ap['iata']}] FR24 page {page} error: {e}")
            if page == 1:
                break
        time.sleep(1.2)
    if not ok:
        cache["ok"] = False
        cache["tried"] = now
        return (recs or []), False, fetched
    parsed = []
    for e in raw:
        r = parse_fr24(e, ap["iata"], now)
        if r:
            parsed.append(r)
    # de-duplicate the overlap between page 1 and -1
    seen, uniq = set(), []
    for r in parsed:
        k = (r["fn"], r["d"], r["s"], r["oi"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    board = merge_board(uniq)
    # keep a small raw sample so the cache shows what FR24 sends (diagnostics)
    cache.clear()
    cache.update({"v": 2, "fetched": now, "tried": now, "ok": True, "flights": board,
                  "updated": _sr(now).strftime("%d %b %Y %H:%M SR"),
                  "sample": raw[:2]})
    log(f"  flights [{ap['iata']}]: FR24 {len(raw)} raw -> {len(board)} rows")
    return board, True, now


def fetch_fr24_flight_list(fn):
    url = ("https://api.flightradar24.com/common/v1/flight/list.json"
           f"?query={urllib.parse.quote(fn)}&fetchBy=flight&page=1&limit=40")
    data = _http_json(url, headers={"Referer": "https://www.flightradar24.com/"})
    return _g(data, "result", "response", "data") or []


# ── Caribbean Airlines (airline ops feed) ─────────────────────────────────────

def _parse_iso_utc(s):
    try:
        return int(datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        return None


def fetch_bw(rec, log=print):
    """Overlay Caribbean Airlines' own data on a BW record (in place).
    Departure date in the request = local date at the ORIGIN airport."""
    num = re.sub(r"^BW", "", rec["fn"])
    if not num.isdigit():
        return False
    sd = rec.get("sd") or rec["s"]
    off = -10800 if rec["d"] == "D" else (rec.get("oz") if rec.get("oz") is not None else -14400)
    dept = datetime.fromtimestamp(sd + off, timezone.utc).strftime("%Y%m%d")
    data = _http_json("https://www.caribbean-airlines.com/get/Flight/Status",
                      data={"to": "", "from": "", "dept_date": dept, "flight_number": num}, timeout=25)
    res = _g(data, "data", "result") or []
    legs = [x for grp in res if isinstance(grp, list) for x in grp] if isinstance(res, list) else []
    me = rec["ap"]
    for leg in legs:
        if rec["d"] == "A" and leg.get("arr_code") != me:
            continue
        if rec["d"] == "D" and leg.get("dept_code") != me:
            continue
        mv = leg.get("mvt_times") or {}
        if rec["d"] == "A":
            sched = _parse_iso_utc(leg.get("sta_utc") or "")
            act = _parse_iso_utc(mv.get("actual_touch_down") or "") or _parse_iso_utc(mv.get("actual_block_on") or "")
            est = _parse_iso_utc(mv.get("estimated_touch_down") or "") or _parse_iso_utc(mv.get("estimated_block_on") or "")
        else:
            sched = _parse_iso_utc(leg.get("std_utc") or "")
            act = _parse_iso_utc(mv.get("actual_take_off") or "") or _parse_iso_utc(mv.get("actual_block_off") or "")
            est = None
        fs = (leg.get("flight_status") or "").lower()
        if sched:
            rec["s"] = sched
        if act:
            rec["a"] = act
        if est and not act:
            rec["e"] = est
        generic = "canceled" if fs.startswith("cancel") else ""
        live = fs == "airborne"
        if fs == "completed" and not act:
            rec["a"] = rec.get("e") or rec["s"]
        rec["st"], rec["dl"] = classify(rec["d"], rec["s"], rec.get("e"), rec.get("a"), generic, "", live)
        if leg.get("aircraft_type") and not rec.get("acc"):
            rec["acc"] = leg["aircraft_type"]
        if leg.get("tailnumber") and not rec.get("rg"):
            rec["rg"] = leg["tailnumber"]
        rec["src"] = "airline"
        return True
    return False


# ── Air France-KLM Open Data (official, free key in env AFKL_API_KEY) ────────
# Verified 20 Oct 2026 with the live key: ONE call with origin=PBM (or
# destination=PBM) returns every flight in the AF-KLM network data at PBM in the
# time range, KLM *and* Copa included, several days at once, with gate and
# runway times, delay reasons, check-in/boarding state and the aircraft.
# Quota on the free key: 100 calls/day, 1/s. Budget below: one direction per
# call, every AFKL_ACTIVE_S while a covered flight is within -1h..+3h, else
# every AFKL_QUIET_S, hard cap AFKL_DAY_CAP per UTC day (both workflows share it).
AFKL_PATH = "data/flights_afkl.json"
AFKL_ACTIVE_S = 20 * 60
AFKL_QUIET_S = 3 * 3600
AFKL_ERROR_S = 2 * 3600
AFKL_DAY_CAP = 80
AFKL_AIRLINES = {"KL", "CM", "AF", "DL", "KQ", "VS"}   # who can appear; refined from responses


def _afkl_time(times, *names):
    for n in names:
        v = times.get(n) if isinstance(times, dict) else None
        if isinstance(v, dict):
            v = v.get("value")
        if isinstance(v, str) and len(v) >= 16:
            try:
                return int(datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp())
            except Exception:
                continue
    return None


def _reg_fmt(r):
    r = (r or "").strip().upper()
    if "-" in r or len(r) < 4:
        return r
    if r[:2] in ("PH", "HP", "PZ", "9Y", "8R", "PR", "PP", "PT", "PS", "HK", "YV", "TG", "HI", "VP", "F-", "EI"):
        return r[:2] + "-" + r[2:]
    if r[0] in ("N",):
        return r
    return r


def parse_afkl(data, our_iata):
    """AF-KLM flightstatus response -> list of overlay dicts for legs at our airport."""
    out = []
    for of in (data.get("operationalFlights") or []):
        al = _g(of, "airline", "code") or ""
        try:
            fn = al + str(int(of.get("flightNumber")))
        except Exception:
            continue
        for leg in (of.get("flightLegs") or []):
            dep = leg.get("departureInformation") or {}
            arr = leg.get("arrivalInformation") or {}
            if _g(arr, "airport", "code") == our_iata:
                d, side, other = "A", arr, dep
            elif _g(dep, "airport", "code") == our_iata:
                d, side, other = "D", dep, arr
            else:
                continue
            t = side.get("times") or {}
            sched = _afkl_time(t, "scheduled")
            if not sched:
                continue
            if d == "A":
                act = _afkl_time(t, "actualTouchDownTime", "actual")
                est = _afkl_time(t, "estimated", "latestPublished")
            else:
                act = _afkl_time(t, "actualTakeOffTime", "actual")
                est = _afkl_time(t, "latestPublished", "estimated")
            ot = other.get("times") or {}
            status = (leg.get("legStatusPublic") or leg.get("publishedStatus") or of.get("flightStatusPublic") or "").upper()
            irr = leg.get("irregularity") or {}
            why = ""
            for di in (irr.get("delayInformation") or []):
                why = di.get("delayReasonPublicShort") or why
            if not why:
                lst = irr.get("delayReasonPublicLangTransl") or []
                why = lst[0] if lst else ""
            ac = leg.get("aircraft") or {}
            gate = _g(dep, "places", "gateNumber")
            o = {"fn": fn, "d": d, "ap": our_iata, "s": sched, "a": act, "e": est if (est and not act) else None,
                 "ast": "CANCELLED" if str(irr.get("cancelled", "")).upper() == "Y" else status,
                 "oi": _g(other, "airport", "code") or "",
                 "sd": sched if d == "D" else _afkl_time(ot, "scheduled"),
                 "sa": sched if d == "A" else _afkl_time(ot, "scheduled"),
                 "ac": aircraft_short((ac.get("typeName") or "").title().replace("Er", "ER")) if ac.get("typeName") else "",
                 "rg": _reg_fmt(ac.get("registration")),
                 "why": why[:90], "src": "airline"}
            if d == "D":
                ols = leg.get("otherFlightLegStatuses") or {}
                o["brd"] = ols.get("boardingStatus") or ""
                o["chk"] = ols.get("acceptanceStatus") or ""
                if gate:
                    o["gate"] = gate[0] if isinstance(gate, list) else str(gate)
            out.append(o)
    return out


def _afkl_state(o, now=None):
    """(st, dl) for an overlay, from the airline's status word + times."""
    st = o.get("ast") or ""
    generic = {"CANCELLED": "canceled", "DIVERTED": "diverted", "ARRIVED": "landed", "DELAYED": "delayed"}.get(st, "")
    if o["d"] == "D" and st in ("DEPARTED", "IN_FLIGHT", "ARRIVED"):
        generic = "departed"
    live = o["d"] == "A" and st in ("IN_FLIGHT", "DEPARTED")
    return classify(o["d"], o["s"], o.get("e"), o.get("a"), generic, "", live, None, now)


def afkl_apply(boards, afkl, now):
    """Overlay stored AF-KLM legs on board records (every build, also between calls)."""
    legs = list((afkl.get("legs") or {}).values())
    n = 0
    for iata, recs in boards.items():
        for r in recs:
            cand = [o for o in legs if o["fn"] == r["fn"] and o["d"] == r["d"] and o["ap"] == iata
                    and abs(o["s"] - r["s"]) <= 3 * 3600]
            if not cand:
                continue
            o = min(cand, key=lambda x: abs(x["s"] - r["s"]))
            fr24_act = r.get("a") if not o.get("a") else None   # FR24 saw it land/leave after our last AF-KLM call
            r["s"] = o["s"]
            for k in ("a", "e"):
                if o.get(k):
                    r[k] = o[k]
                elif k == "e" and o.get("a"):
                    r.pop("e", None)
            for k in ("ac", "rg", "gate", "why", "brd", "chk"):
                if o.get(k):
                    r[k] = o[k]
            if o.get("sd"):
                r["sd"] = o["sd"]
            if o.get("sa"):
                r["sa"] = o["sa"]
            if fr24_act and o.get("ast") != "CANCELLED":
                r["a"] = fr24_act
                r.pop("e", None)
                r["st"], r["dl"] = classify(r["d"], r["s"], None, fr24_act, "", "", False, None, now)
            else:
                r["st"], r["dl"] = _afkl_state(o, now)
            if r["st"] == "delayed" and not o.get("e") and r.get("e"):
                r["dl"] = int(round((r["e"] - r["s"]) / 60))
            r["src"] = "airline"
            n += 1
    return n


def afkl_due(afkl, boards, now, direction):
    """Seconds-based decision: call AF-KLM for this direction now?"""
    last = (afkl.get("last") or {}).get(direction) or 0
    if (afkl.get("err_until") or 0) > now:
        return False
    covered = set(afkl.get("airlines") or []) or AFKL_AIRLINES
    active = any(r["d"] == direction and r["fn"][:2] in covered
                 and -3600 <= ((r.get("a") or r.get("e") or r["s"]) - now) <= 3 * 3600
                 for r in boards.get("PBM", []))
    return now - last >= (AFKL_ACTIVE_S if active else AFKL_QUIET_S) - 60


def fetch_afkl_airport(key, direction, now, iata="PBM"):
    q = urllib.parse.urlencode({
        "startRange": datetime.fromtimestamp(now - 30 * 3600, timezone.utc).strftime("%Y-%m-%dT%H:00:00Z"),
        "endRange": datetime.fromtimestamp(now + 30 * 3600, timezone.utc).strftime("%Y-%m-%dT%H:00:00Z"),
        ("origin" if direction == "D" else "destination"): iata,
        "pageSize": 100,
    })
    return _http_json("https://api.airfranceklm.com/opendata/flightstatus?" + q,
                      headers={"API-Key": key, "Accept": "application/hal+json"}, timeout=25)


def afkl_refresh(afkl, boards, hist, now, key, log=print):
    """Call AF-KLM within the daily budget; store legs; feed history. Returns calls made."""
    day = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
    if afkl.get("day") != day:
        afkl["day"], afkl["n"] = day, 0
    calls = 0
    for direction in ("A", "D"):
        if afkl.get("n", 0) >= AFKL_DAY_CAP or not afkl_due(afkl, boards, now, direction):
            continue
        afkl["n"] = afkl.get("n", 0) + 1
        afkl.setdefault("last", {})[direction] = now
        calls += 1
        try:
            data = fetch_afkl_airport(key, direction, now)
        except Exception as e:
            msg = str(e)
            log(f"  flights AF-KLM {direction}: {msg[:120]}")
            afkl["err"] = msg[:160]
            if "403" in msg or "429" in msg or "401" in msg:
                afkl["err_until"] = now + AFKL_ERROR_S
            continue
        legs = parse_afkl(data, "PBM")
        store = afkl.setdefault("legs", {})
        for o in legs:
            store[f'{o["fn"]}|{o["d"]}|{o["s"]}'] = o
        afkl["airlines"] = sorted(set(afkl.get("airlines") or []) | {o["fn"][:2] for o in legs})
        afkl["ok_at"] = now
        afkl.pop("err", None)
        log(f"  flights AF-KLM {direction}: {len(legs)} legs ({afkl['n']}/{AFKL_DAY_CAP} today)")
        time.sleep(1.2)
    # forget legs older than 3 days
    afkl["legs"] = {k: v for k, v in (afkl.get("legs") or {}).items() if v["s"] > now - 3 * 86400}
    # past legs that are no longer on the board: correct their history entries
    f = hist.setdefault("f", {})
    upd = []
    for o in afkl["legs"].values():
        k = _sr(o["s"]).strftime("%Y-%m-%d") + "|" + o["fn"] + "|" + o["d"] + "|" + o["ap"]
        base = f.get(k)
        if not base or not o.get("a") and o.get("ast") != "CANCELLED":
            continue
        rr = dict(base)
        rr.update({x: o[x] for x in ("s", "a", "ac", "rg", "why", "sd", "sa") if o.get(x)})
        rr["st"], rr["dl"] = _afkl_state(o, now)
        rr["src"] = "airline"
        upd.append(rr)
    if upd:
        history_update(hist, upd, now)
    return calls


# ── history + stats ───────────────────────────────────────────────────────────
_HKEEP = ("fn", "al", "ai", "d", "ap", "oi", "on", "occ", "oz", "s", "sd", "sa", "e", "a", "st", "dl", "ac", "rg", "cg", "cs", "via", "vfirst", "src", "why")


def history_update(hist, recs, now=None):
    """Merge records into history. Actual times win; airline data beats FR24."""
    now = now or _now()
    f = hist.setdefault("f", {})
    changed = 0
    for r in recs:
        if not r.get("s"):
            continue
        k = rec_key(r)
        new = {x: r[x] for x in _HKEEP if r.get(x) is not None and r.get(x) != "" and r.get(x) != []}
        old = f.get(k)
        if old:
            if old.get("src") == "airline" and r.get("src") != "airline" and old.get("a"):
                continue
            if old.get("a") and not new.get("a"):
                for x in ("a", "st", "dl"):
                    new[x] = old.get(x)
                if old.get("e") and not new.get("e"):
                    new["e"] = old["e"]
            for x in ("ac", "rg", "cs", "via", "occ"):
                if not new.get(x) and old.get(x):
                    new[x] = old[x]
        if new != old:
            f[k] = new
            changed += 1
    cut = now - HISTORY_DAYS * 86400
    for k in [k for k, v in f.items() if (v.get("s") or 0) < cut]:
        del f[k]
        changed += 1
    return changed


def flight_stats(hist_list, now=None, days=30):
    """hist_list: history records for one (fn, d, ap). Past flights only."""
    now = now or _now()
    since = now - days * 86400
    past = [r for r in hist_list if since <= r["s"] <= now - 1800]
    flown = [r for r in past if r.get("st") in ("landed", "departed") and r.get("dl") is not None]
    canc = [r for r in past if r.get("st") == "cancelled"]
    n = len(flown)
    out = {"n": n, "cancelled": len(canc), "days": days}
    if n:
        dls = sorted(r["dl"] for r in flown)
        out["ontime"] = round(100 * sum(1 for x in dls if x <= ON_TIME_MIN) / n)
        out["avg"] = round(sum(max(x, 0) for x in dls) / n)
        out["median"] = dls[n // 2]
        out["worst"] = dls[-1]
    return out


def schedule_pattern(hist_list, now=None, weeks=4):
    """Weekdays + typical local time + aircraft from the last N weeks (incl. upcoming)."""
    now = now or _now()
    lo, hi = now - weeks * 7 * 86400, now + 3 * 86400
    rows = [r for r in hist_list if lo <= r["s"] <= hi and r.get("st") != "cancelled"]
    if not rows:
        return {}
    wd = sorted({_sr(r["s"]).weekday() for r in rows})
    times = {}
    for r in rows:
        t = _sr(r["s"]).strftime("%H:%M")
        times[t] = times.get(t, 0) + 1
    typical = max(times.items(), key=lambda kv: kv[1])[0]
    acs = {}
    for r in rows:
        if r.get("ac"):
            acs[r["ac"]] = acs.get(r["ac"], 0) + 1
    dur = [((r.get("sa") or 0) - (r.get("sd") or 0)) for r in rows if r.get("sa") and r.get("sd")]
    dur = sorted(x for x in dur if 600 < x < 20 * 3600)
    past = [r for r in rows if r["s"] <= now]
    span_days = (now - min(r["s"] for r in past)) / 86400 if past else 0
    per_week = (min(round(len(past) * 7 / span_days), 7) if span_days >= 6.5 else None)
    return {"wd": wd, "time": typical, "ac": (max(acs.items(), key=lambda kv: kv[1])[0] if acs else ""),
            "dur": (dur[len(dur) // 2] if dur else None), "per_week": per_week, "seen": len(rows),
            "since": min(r["s"] for r in rows)}


def group_history(hist):
    g = {}
    for v in (hist.get("f") or {}).values():
        g.setdefault((v["fn"], v["d"], v["ap"]), []).append(v)
    for L in g.values():
        L.sort(key=lambda r: r["s"])
    return g


# ── orchestration ─────────────────────────────────────────────────────────────

def collect(log=print, now=None, network=True):
    """Run every source, update history, write flights_live.json.
    Returns a dict the page builders use:
      {"boards": {iata: [rec...]}, "ok": {iata: bool}, "fetched": {iata: ts},
       "hist": history dict, "groups": group_history(...), "now": ts, "meta": {...}}"""
    now = now or _now()
    meta = _load(META_PATH, {})
    meta.setdefault("sources", {})
    hist = _load(HISTORY_PATH, {"v": 1, "f": {}})
    if not isinstance(hist.get("f"), dict):
        hist = {"v": 1, "f": {}}
    boards, oks, fetched = {}, {}, {}
    caches = {}
    for ap in AIRPORTS:
        cache = _load(ap["cache"], {})
        caches[ap["iata"]] = cache
        try:
            if network:
                recs, ok, ft = fetch_board(ap, cache, now, log)
            else:
                recs = cache.get("flights") or [] if cache.get("v") == 2 else []
                ok, ft = bool(cache.get("ok")), cache.get("fetched") or 0
        except Exception as e:                       # never fatal
            log(f"  !! flights [{ap['iata']}] board failed: {e}")
            recs, ok, ft = (cache.get("flights") or []) if cache.get("v") == 2 else [], False, cache.get("fetched") or 0
        boards[ap["iata"]], oks[ap["iata"]], fetched[ap["iata"]] = recs, ok, ft
        meta["sources"]["fr24_" + ap["iata"]] = {"ok": ok, "fetched": ft}

    afkl = _load(AFKL_PATH, {})
    # airline overlays for flights near now (-6h..+12h)
    if network:
        afkl_key = os.environ.get("AFKL_API_KEY", "").strip()
        bw_n = 0
        for iata, recs in boards.items():
            for r in recs:
                dt = (r.get("e") or r["s"]) - now
                if not (-6 * 3600 <= dt <= 12 * 3600):
                    continue
                if r["fn"].startswith("BW") and bw_n < 4:
                    bw_n += 1
                    try:
                        if fetch_bw(r, log):
                            meta["sources"]["bw"] = {"ok": True, "fetched": now}
                    except Exception as e:
                        meta["sources"]["bw"] = {"ok": False, "fetched": now, "err": str(e)[:120]}
                        log(f"  flights BW {r['fn']}: {e}")
                    time.sleep(0.8)
        if afkl_key:
            try:
                afkl_refresh(afkl, boards, hist, now, afkl_key, log)
            except Exception as e:                   # never fatal
                log(f"  !! flights AF-KLM: {e}")
            meta["sources"]["afkl"] = {"ok": not afkl.get("err"), "fetched": afkl.get("ok_at"),
                                       "calls_today": afkl.get("n", 0), "err": afkl.get("err", "")}
    afkl_apply(boards, afkl, now)
    if network:
        # persist overlays into the board caches too
        for ap in AIRPORTS:
            c = caches[ap["iata"]]
            if c.get("v") == 2:
                c["flights"] = boards[ap["iata"]]
                try:
                    _save(ap["cache"], c)
                except Exception as e:
                    log(f"  !! flights cache write {ap['cache']}: {e}")

    history_update(hist, [r for L in boards.values() for r in L], now)
    meta.pop("afkl_last", None)

    # per-flight FR24 history (bootstrap / gaps), few per build, each once a day
    if network:
        last = meta.setdefault("fl_hist", {})
        todo = []
        for iata, recs in boards.items():
            for r in recs:
                if r.get("cg"):
                    continue
                k = r["fn"]
                if now - (last.get(k) or 0) > 20 * 3600 and k not in todo:
                    todo.append(k)
        todo.sort(key=lambda k: last.get(k) or 0)
        for k in todo[:FL_HIST_PER_BUILD]:
            try:
                items = fetch_fr24_flight_list(k)
                got = []
                for it in items:
                    for ap in AIRPORTS:
                        rr = parse_fr24({"flight": it}, ap["iata"], now)
                        if rr and rr["fn"] == k:
                            got.append(rr)
                history_update(hist, got, now)
                last[k] = now
                meta["sources"]["fr24_hist"] = {"ok": True, "fetched": now}
                log(f"  flights history {k}: {len(got)} legs")
            except Exception as e:
                last[k] = now - 14 * 3600        # retry in ~6 h
                meta["sources"]["fr24_hist"] = {"ok": False, "fetched": now, "err": str(e)[:120]}
                log(f"  flights history {k}: {e}")
            time.sleep(1.5)

    try:
        _save(HISTORY_PATH, hist)
        if afkl:
            _save(AFKL_PATH, afkl)
        _save(META_PATH, meta, compact=False)
    except Exception as e:
        log(f"  !! flights history write: {e}")

    groups = group_history(hist)
    out = {"boards": boards, "ok": oks, "fetched": fetched, "hist": hist, "groups": groups,
           "now": now, "meta": meta}
    try:
        write_live(out)
    except Exception as e:
        log(f"  !! flights_live.json: {e}")
    return out


_LIVE_KEYS = ("fn", "al", "ai", "d", "ap", "oi", "on", "oz", "s", "sd", "sa", "e", "a", "st", "dl", "ac", "rg", "cg", "cs", "via", "vfirst", "dv", "gate", "src", "why", "brd", "chk")


def live_rows(boards, now, back_h=12, ahead_h=48):
    rows = []
    for iata, recs in boards.items():
        for r in recs:
            t = r.get("a") or r.get("e") or r["s"]
            if now - back_h * 3600 <= t <= now + ahead_h * 3600 or now - back_h * 3600 <= r["s"] <= now + ahead_h * 3600:
                x = {k: r[k] for k in _LIVE_KEYS if r.get(k) not in (None, "", [])}
                x["k"] = rec_key(r)
                x["sl"] = slug_of(r["fn"])
                rows.append(x)
    rows.sort(key=lambda r: r["s"])
    return rows


def write_live(c):
    now = c["now"]
    out = {"built": now, "tz": "America/Paramaribo",
           "airports": {a["iata"]: {"ok": c["ok"].get(a["iata"], False),
                                    "as_of": c["fetched"].get(a["iata"]) or None} for a in AIRPORTS},
           "stale_after_min": 75,
           "pages": sorted(PAGE_SLUGS),
           "flights": live_rows(c["boards"], now)}
    _save(LIVE_PATH, out)


# Filled by build_pages(): slugs that got a flight page this build.
PAGE_SLUGS = set()


# ── legacy shape for the homepage tile (generate.write_home_live / _flights) ──

def legacy_lists(c, iata="PBM"):
    """[(arrivals, departures, updated)] in the old shape: time '%d %b %H:%M',
    English status words the homepage already understands."""
    now = c["now"]
    words = {"landed": "Landed", "departed": "Departed", "cancelled": "Cancelled", "diverted": "Diverted",
             "delayed": "Delayed", "enroute": "En route", "scheduled": "Scheduled", "unknown": "Scheduled"}
    arr, dep = [], []
    for r in c["boards"].get(iata, []):
        if r.get("cg"):
            continue
        t = r.get("a") or r.get("e") or r["s"]
        if t < now - 6 * 3600:
            continue
        row = {"flight": r["fn"], "airline": r.get("al") or "", "airport": r.get("on") or "",
               "iata": r.get("oi") or "", "time": _sr(t).strftime("%d %b %H:%M"),
               "status": words.get(r.get("st"), "Scheduled"), "ts": t, "st": r.get("st")}
        (arr if r["d"] == "A" else dep).append(row)
    arr.sort(key=lambda x: x["ts"])
    dep.sort(key=lambda x: x["ts"])
    ft = c["fetched"].get(iata) or now
    return arr, dep, _sr(ft).strftime("%d %b %Y %H:%M SR")
