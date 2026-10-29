#!/usr/bin/env python3
"""Morning rain heads-up for Explore Suriname (Web Push).

Run by .github/workflows/push_rain.yml at ~06:15 Suriname time. For every district that has subscribers it
asks Open-Meteo for today's hourly rain from four models (ECMWF, GFS, ICON, UKMO) and sends ONE short
message only when the models agree:

    rain hour  = an hour (07:00-20:00, not yet past) in which at least 3 of the 4 models give >= 0.5 mm
    heads-up   = at least 2 rain hours today; window = first rain hour .. last rain hour + 1

Backtest Oct 2025 - Oct 2026 (4 districts, day-ahead runs, checked against ERA5): sent on ~19% of days
(none in the Aug-Oct dry season, about half of the days in May), and on ~9 in 10 of those days it rained
in the stated window. No message on other days: silence is the default.

Subscriptions and the VAPID key come from the esr-push Worker; this job proves who it is with the GitHub
OIDC token of this workflow (no stored secret). Each subscriber gets at most one message per Suriname day.

Modes (workflow_dispatch input "mode"):
  send  normal run (schedule)
  dry   compute and print the decision per district, send nothing
  test  send a short test message to subscriptions created in the last 45 minutes, whatever the weather
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

WORKER = os.environ.get("ESR_PUSH_URL", "https://esr-push.surinamedomains.workers.dev")
SITE = "https://exploresuriname.com"
VAPID_SUB = "mailto:contact@exploresuriname.com"
SR = timezone(timedelta(hours=-3))
MODELS = ["ecmwf_ifs025", "gfs_seamless", "icon_seamless", "ukmo_seamless"]
H0, H1 = 7, 20          # daytime window considered (local hours, inclusive)
MM, AGREE, MIN_HOURS = 0.5, 3, 2
HEAVY_MM = 4.0          # an hour where >= AGREE models give this much = "heavy showers"
WIDE_H = 8              # window longer than this reads "on and off"

DISTRICTS = {  # same points as the Weather page district chips
    "Paramaribo": (5.852, -55.203), "Wanica": (5.730, -55.250), "Commewijne": (5.893, -55.087),
    "Para": (5.490, -55.226), "Saramacca": (5.793, -55.467), "Nickerie": (5.940, -56.978),
    "Coronie": (5.870, -56.300), "Marowijne": (5.491, -54.057), "Brokopondo": (4.762, -55.027),
    "Sipaliwini": (3.900, -56.000),
}

# Message text, hand-written per language. {d} district, {a}/{b} hours "14:00"
TXT = {
    "en": {"t": "Rain expected in {d}", "th": "Heavy showers expected in {d}",
           "w": "Showers likely {a}–{b}. Take an umbrella.", "wide": "Showers on and off between {a} and {b}. Take an umbrella.",
           "test_t": "Explore Suriname alerts are on", "test_b": "This is a test. You will get a heads-up around 06:30 on days rain is likely."},
    "nl": {"t": "Regen verwacht in {d}", "th": "Zware buien verwacht in {d}",
           "w": "Buien waarschijnlijk {a}–{b}. Neem een paraplu mee.", "wide": "Af en toe buien tussen {a} en {b}. Neem een paraplu mee.",
           "test_t": "Meldingen van Explore Suriname staan aan", "test_b": "Dit is een test. Op dagen met kans op regen krijg je rond 06:30 een seintje."},
    "es": {"t": "Se espera lluvia en {d}", "th": "Se esperan chubascos fuertes en {d}",
           "w": "Chubascos probables de {a} a {b}. Lleva paraguas.", "wide": "Chubascos intermitentes entre {a} y {b}. Lleva paraguas.",
           "test_t": "Las alertas de Explore Suriname están activadas", "test_b": "Esto es una prueba. Los días con probable lluvia recibirás un aviso hacia las 06:30."},
    "fr": {"t": "Pluie attendue à {d}", "th": "Fortes averses attendues à {d}",
           "w": "Averses probables de {a} à {b}. Prenez un parapluie.", "wide": "Averses intermittentes entre {a} et {b}. Prenez un parapluie.",
           "test_t": "Les alertes Explore Suriname sont activées", "test_b": "Ceci est un test. Les jours de pluie probable, vous recevrez un message vers 06:30."},
    "pt": {"t": "Chuva prevista em {d}", "th": "Pancadas fortes previstas em {d}",
           "w": "Pancadas de chuva prováveis das {a} às {b}. Leve um guarda-chuva.", "wide": "Pancadas intermitentes entre {a} e {b}. Leve um guarda-chuva.",
           "test_t": "Os alertas do Explore Suriname estão ativados", "test_b": "Isto é um teste. Nos dias com chuva provável você receberá um aviso por volta das 06:30."},
    "zh": {"t": "{d}今天有雨", "th": "{d}今天有强阵雨",
           "w": "{a}至{b}可能有阵雨，出门请带伞。", "wide": "{a}至{b}间断有阵雨，出门请带伞。",
           "test_t": "Explore Suriname 提醒已开启", "test_b": "这是一条测试消息。可能下雨的日子，我们会在 06:30 左右提醒你。"},
}


def log(*a):
    print(*a, flush=True)


def http_json(url, data=None, headers=None, timeout=60):
    h = {"User-Agent": "esr-push-rain/1.0", **(headers or {})}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if body is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def oidc_token():
    u, t = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL"), os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN")
    if not u or not t:
        sys.exit("No GitHub OIDC token: the workflow needs 'permissions: id-token: write'.")
    j = http_json(u + "&audience=esr-push", headers={"Authorization": "bearer " + t})
    print("::add-mask::" + j["value"], flush=True)
    return j["value"]


def load_subs(tok):
    subs, after, vapid = [], 0, None
    while True:
        j = http_json(WORKER + "/push/admin/list", {"after": after, "limit": 500},
                      headers={"Authorization": "Bearer " + tok})
        vapid = j["vapid"]
        subs += j["subs"]
        if j.get("next") is None:
            return subs, vapid
        after = j["next"]


def fetch_hourly(lat, lon):
    q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "hourly": "precipitation",
                                "models": ",".join(MODELS), "forecast_days": 1, "timezone": "America/Paramaribo"})
    for i in range(3):
        try:
            return http_json("https://api.open-meteo.com/v1/forecast?" + q, timeout=40)
        except Exception as e:  # noqa: BLE001
            log("  open-meteo retry", i + 1, type(e).__name__)
            time.sleep(4 * (i + 1))
    return None


def decide(data, now_hour):
    """Return None (no message) or {"a": first hour, "b": end hour, "heavy": bool, "models": n}."""
    if not data or "hourly" not in data:
        return None
    h = data["hourly"]
    times = h.get("time") or []
    series = [h.get("precipitation_" + m) for m in MODELS]
    if sum(1 for s in series if s) < AGREE:      # fewer than 3 models answered: say nothing
        return None
    rain, heavy = [], False
    for i, ts in enumerate(times):
        hr = int(ts[11:13])
        if hr < max(H0, now_hour) or hr > H1:
            continue
        vals = [s[i] for s in series if s and i < len(s) and s[i] is not None]
        if sum(1 for v in vals if v >= MM) >= AGREE:
            rain.append(hr)
        if sum(1 for v in vals if v >= HEAVY_MM) >= AGREE:
            heavy = True
    if len(rain) < MIN_HOURS:
        return None
    return {"a": rain[0], "b": min(rain[-1] + 1, 24), "heavy": heavy, "hours": len(rain)}


def message(lang, district, d):
    t = TXT.get(lang) or TXT["en"]
    a, b = f"{d['a']:02d}:00", f"{d['b']:02d}:00"
    body = (t["wide"] if d["b"] - d["a"] > WIDE_H else t["w"]).format(a=a, b=b)
    title = (t["th"] if d["heavy"] else t["t"]).format(d=district)
    return title, body


def page_url(lang):
    return SITE + ("/conditions" if lang == "en" else f"/{lang}/conditions")


def make_vapid(v):
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from py_vapid import Vapid02  # RFC 8292 header "vapid t=..., k=..." (Apple requires it)
    import base64
    d = int.from_bytes(base64.urlsafe_b64decode(v["d"] + "=" * (-len(v["d"]) % 4)), "big")
    key = ec.derive_private_key(d, ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                            serialization.NoEncryption())
    return Vapid02.from_pem(pem)


def send(sub, payload, ttl, vapid):
    """Return 'ok', 'gone' or 'fail'."""
    from pywebpush import webpush, WebPushException
    try:
        webpush({"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
                data=json.dumps(payload), vapid_private_key=vapid, vapid_claims={"sub": VAPID_SUB},
                ttl=ttl, headers={"Urgency": "normal", "Topic": "esr-rain"}, timeout=20)
        return "ok"
    except WebPushException as e:
        code = e.response.status_code if e.response is not None else 0
        return "gone" if code in (404, 410) else "fail"
    except Exception:  # noqa: BLE001
        return "fail"


def main():
    mode = (os.environ.get("MODE") or "send").strip().lower()
    now = datetime.now(SR)
    day = now.strftime("%Y-%m-%d")
    log(f"mode={mode} sr_time={now:%Y-%m-%d %H:%M}")
    tok = oidc_token()
    subs, v = load_subs(tok)
    log(f"subscriptions: {len(subs)}")
    if not subs:
        return
    vapid = make_vapid(v)
    sent, gone, failed = [], [], 0

    if mode == "test":
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
        for s in subs:
            if (s.get("created") or "") < cutoff:
                continue
            t = TXT.get(s["lang"]) or TXT["en"]
            res = send(s, {"title": t["test_t"], "body": t["test_b"], "url": page_url(s["lang"]), "tag": "esr-test"}, 3600, vapid)
            log("  test ->", s["district"], s["lang"], res)
            gone += [s["endpoint"]] if res == "gone" else []
            failed += res == "fail"
        if gone:
            http_json(WORKER + "/push/admin/report", {"day": day, "sent": [], "gone": gone},
                      headers={"Authorization": "Bearer " + tok})
        return

    by_d = {}
    for s in subs:
        if "rain" in (s.get("topics") or "").split(",") and s.get("district") in DISTRICTS:
            by_d.setdefault(s["district"], []).append(s)
    for district, group in sorted(by_d.items()):
        lat, lon = DISTRICTS[district]
        d = decide(fetch_hourly(lat, lon), now.hour)
        due = [s for s in group if s.get("last_day") != day]
        log(f"{district}: {len(group)} subscribers, {len(due)} not yet sent today -> "
            + (f"rain {d['a']:02d}:00-{d['b']:02d}:00{' heavy' if d['heavy'] else ''}" if d else "no message"))
        if not d or mode == "dry":
            continue
        ttl = max(1800, (d["a"] - now.hour) * 3600)   # never deliver after the rain has started
        for s in due:
            title, body = message(s["lang"], district, d)
            res = send(s, {"title": title, "body": body, "url": page_url(s["lang"]), "tag": "esr-rain"}, ttl, vapid)
            if res == "ok":
                sent.append(s["endpoint"])
            elif res == "gone":
                gone.append(s["endpoint"])
            else:
                failed += 1
    if sent or gone:
        http_json(WORKER + "/push/admin/report", {"day": day, "sent": sent, "gone": gone},
                  headers={"Authorization": "Bearer " + tok}, timeout=90)
    log(f"sent={len(sent)} gone={len(gone)} failed={failed}")


if __name__ == "__main__":
    main()
