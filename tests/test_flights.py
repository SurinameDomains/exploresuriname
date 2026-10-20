"""Offline tests for flights.py (no network).
Run: python -m pytest tests/test_flights.py   or   python tests/test_flights.py"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import flights as F  # noqa: E402

NOW = 1792500000  # 20 Oct 2026 ~09:20 SR


def _ap(iata, city, off=-14400):
    return {"name": city + " Airport", "code": {"iata": iata, "icao": "X" + iata},
            "position": {"country": {"name": "X"}, "region": {"city": city}}, "timezone": {"offset": off}}


def _item(fn, al_iata, al_name, origin, dest, sd, sa, text="Scheduled", generic="scheduled", real=None, est=None):
    return {"flight": {
        "identification": {"number": {"default": fn}},
        "status": {"live": False, "text": text,
                   "generic": {"status": {"text": generic, "diverted": None}, "eventTime": {"utc": None}}},
        "aircraft": {"model": {"code": "B772", "text": "Boeing 777-206(ER)"}, "registration": "PH-BQD"},
        "airline": ({"name": al_name, "code": {"iata": al_iata, "icao": "XXX"}} if al_name else None),
        "airport": {"origin": origin, "destination": dest, "real": None},
        "time": {"scheduled": {"departure": sd, "arrival": sa},
                 "real": real or {"departure": None, "arrival": None},
                 "estimated": est or {"departure": None, "arrival": None}, "other": {"eta": None}}}}


def test_arrival_delay_and_names():
    it = _item("KL713", "KL", "KLM Asia", _ap("AMS", "Amsterdam", 7200), None, NOW - 9 * 3600, NOW + 3600,
               text="Estimated 14:45", generic="estimated",
               est={"departure": None, "arrival": NOW + 3600 + 90 * 60})
    r = F.parse_fr24(it, "PBM", NOW)
    assert r["d"] == "A" and r["al"] == "KLM" and r["on"] == "Amsterdam" and r["oz"] == 7200
    assert r["st"] == "delayed" and r["dl"] == 90 and r["ac"] == "Boeing 777"


def test_landed_uses_real_time():
    it = _item("CM318", "CM", "Copa Airlines", _ap("PTY", "Panama City", -18000), None, NOW - 4 * 3600, NOW - 600,
               text="Landed 09:15", generic="landed", real={"departure": None, "arrival": NOW - 300})
    r = F.parse_fr24(it, "PBM", NOW)
    assert r["st"] == "landed" and r["a"] == NOW - 300 and r["dl"] == 5


def test_codeshare_merge():
    a = F.parse_fr24(_item("GUM42", "", "Gum Air", _ap("OGL", "Georgetown"), None, NOW, NOW + 3600), "EAX", NOW)
    b = F.parse_fr24(_item("W12492", "", None, _ap("OGL", "Georgetown"), None, NOW, NOW + 3600), "EAX", NOW)
    out = F.merge_board([b, a])
    assert len(out) == 1 and out[0]["fn"] == "GUM42" and out[0]["cs"] == ["W12492"]


def test_cancelled_and_cargo():
    it = _item("M6820", "M6", "Amerijet International", None, _ap("MIA", "Miami"), NOW + 3600, NOW + 5 * 3600,
               text="Canceled", generic="canceled")
    r = F.parse_fr24(it, "PBM", NOW)
    assert r["d"] == "D" and r["st"] == "cancelled" and r["cg"] == 1


def test_history_and_stats():
    hist = {"f": {}}
    recs = []
    for i in range(1, 11):
        s = NOW - i * 86400
        recs.append({"fn": "KL714", "al": "KLM", "ai": "KL", "d": "D", "ap": "PBM", "oi": "AMS", "on": "Amsterdam",
                     "s": s, "sd": s, "sa": s + 9 * 3600, "a": s + (0 if i % 2 else 30 * 60), "st": "departed",
                     "dl": 0 if i % 2 else 30, "cg": 0})
    F.history_update(hist, recs, NOW)
    g = F.group_history(hist)[("KL714", "D", "PBM")]
    st = F.flight_stats(g, NOW)
    assert st["n"] == 10 and st["ontime"] == 50 and st["avg"] == 15
    pat = F.schedule_pattern(g, NOW)
    assert pat["per_week"] == 7 and pat["dur"] == 9 * 3600


AFKL_SAMPLE = {"operationalFlights": [{
    "flightNumber": 714, "airline": {"code": "KL"}, "flightStatusPublic": "ARRIVED",
    "flightLegs": [{"legStatusPublic": "ARRIVED",
                    "departureInformation": {"airport": {"code": "PBM"}, "times": {
                        "scheduled": "2026-10-19T17:30:00.000-03:00", "actual": "2026-10-19T17:31:00.000-03:00",
                        "actualTakeOffTime": "2026-10-19T17:40:00.000-03:00"}},
                    "arrivalInformation": {"airport": {"code": "AMS"}, "times": {"scheduled": "2026-10-20T07:15:00.000+02:00"}},
                    "aircraft": {"registration": "PHBQM", "typeName": "BOEING 777-200/200 ER"},
                    "irregularity": {"cancelled": "N", "delayInformation": [{"delayReasonPublicShort": "Restrictions from Air Traffic Control"}]},
                    "otherFlightLegStatuses": {"acceptanceStatus": "Finalised", "boardingStatus": "Closed"}}]}]}


def test_afkl_parse_and_apply():
    legs = F.parse_afkl(AFKL_SAMPLE, "PBM")
    assert len(legs) == 1
    o = legs[0]
    assert o["fn"] == "KL714" and o["d"] == "D" and o["rg"] == "PH-BQM" and o["brd"] == "Closed"
    assert o["why"] == "Restrictions from Air Traffic Control"
    s = o["s"]
    board = {"PBM": [{"fn": "KL714", "d": "D", "ap": "PBM", "s": s + 600, "st": "scheduled"}]}
    F.afkl_apply(board, {"legs": {"x": o}}, s + 6 * 3600)
    r = board["PBM"][0]
    assert r["s"] == s and r["st"] == "departed" and r["dl"] == 10 and r["src"] == "airline"


def test_afkl_budget_cap():
    afkl = {"day": "2026-10-20", "n": F.AFKL_DAY_CAP}
    calls = F.afkl_refresh(afkl, {"PBM": []}, {"f": {}}, 1792500000, "dummy-key", log=lambda *a: None)
    assert calls == 0


if __name__ == "__main__":
    for k, v in list(globals().items()):
        if k.startswith("test_"):
            v()
            print("ok", k)
