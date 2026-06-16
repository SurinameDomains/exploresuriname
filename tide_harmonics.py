"""
Offline harmonic tide predictor for ExploreSuriname.   (v2: +M6 overtide + nodal)

Replaces WorldTides (paid, ran out of credits). ZERO API calls at build time:
tides are deterministic astronomy, synthesised from harmonic constituents that
were fitted ONCE to published station data. No key, no quota, no live dependency.

Datum: Mean Lower Low Water (a low-water reference, matching MAS "low water at
the mouth" - NOT LAT). Heights are metres above that datum.

Provenance / accuracy (fitted to tide-forecast.com tables, 16 Jun - 14 Jul 2026,
datum MLLW; constituents M2 S2 N2 K1 O1 Q1 M4 MS4 M6 - the extra ones were chosen
by OUT-OF-SAMPLE cross-validation; value + turning-point/zero-slope least squares;
reproduction of the published 2026 tables):
  suriname   - Paramaribo (Suriname River).        Z0 1.3016 m   ~2.3 cm / 8 min
  nickerie   - Nieuw Nickerie (Nickerie River).     Z0 1.4706 m   ~2.1 cm / 7 min
  marowijne  - Les Hattes, the Maroni/Marowijne mouth (opposite Albina). Z0 1.6465 m
  commewijne - reuses suriname (shared Nieuw Amsterdam confluence).
Stored amplitudes are fit-epoch-effective; _node_factors() applies the 18.6-yr
nodal amplitude (f) and phase (u) correction so accuracy holds across years, not
just 2026. See fit_tides.py for the derivation, cross-validation and accuracy figures.
"""
import math
from datetime import datetime, timedelta, timezone

_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
_J2000 = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
_SR_TZ = timezone(timedelta(hours=-3))
_T0    = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)   # centre of the fit window

# loc_id -> {"Z0": metres above MLLW, "C": {name: (speed_deg_per_hr, H_m, g_deg)}}
# h(t) = Z0 + sum f*H * cos(speed*t_hours_from_2000Z - g + (u - u0))   (f,u: nodal)
TIDE_MODELS = {
    "suriname": {
        "Z0": 1.3016,
        "C": {
            "M2":  (28.9841042, 0.8747, 127.06),
            "S2":  (30.0,       0.1176, 314.62),
            "N2":  (28.4397295, 0.0976, 263.53),
            "K1":  (15.0410686, 0.0605, 267.00),
            "O1":  (13.9430356, 0.0527, 130.82),
            "Q1":  (13.3986609, 0.0103, 251.82),
            "M4":  (57.9682084, 0.0343, 176.12),
            "MS4": (58.9841042, 0.0120, 348.06),
            "M6":  (86.9523127, 0.0535, 191.86),
        },
    },
    "nickerie": {
        "Z0": 1.4706,
        "C": {
            "M2":  (28.9841042, 1.0649,  93.10),
            "S2":  (30.0,       0.1204, 279.14),
            "N2":  (28.4397295, 0.0974, 230.09),
            "K1":  (15.0410686, 0.0624, 248.58),
            "O1":  (13.9430356, 0.0546, 114.54),
            "Q1":  (13.3986609, 0.0102, 238.29),
            "M4":  (57.9682084, 0.0138, 110.43),
            "MS4": (58.9841042, 0.0046, 280.84),
            "M6":  (86.9523127, 0.0713,  92.11),
        },
    },
    "marowijne": {            # Maroni/Marowijne river mouth (tide-forecast Les Hattes)
        "Z0": 1.6465,
        "C": {
            "M2":  (28.9841042, 0.8356, 101.42),
            "S2":  (30.0,       0.1866, 279.09),
            "N2":  (28.4397295, 0.1472, 215.79),
            "K1":  (15.0410686, 0.1420, 260.13),
            "O1":  (13.9430356, 0.0890, 131.18),
            "Q1":  (13.3986609, 0.0224, 247.22),
            "M4":  (57.9682084, 0.0400, 113.88),
            "MS4": (58.9841042, 0.0392, 285.84),
            "M6":  (86.9523127, 0.0300,  88.35),
        },
    },
}

# Commewijne River meets the Suriname River at Nieuw Amsterdam, directly across
# from Paramaribo, so the lower-river tide is the same body of water. Reuse the
# Suriname (Paramaribo) model rather than invent a separate station.
TIDE_MODELS["commewijne"] = TIDE_MODELS["suriname"]


def _node_factors(dt):
    """Schureman/Pugh nodal amplitude (f) and phase (u, deg) from the lunar node N.
    Keeps the model accurate across the 18.6-yr nodal cycle, not just the fit year."""
    D = (dt - _J2000).total_seconds() / 86400.0
    N = math.radians((125.0445 - 0.0529539222 * D) % 360.0)
    cN, c2N, c3N = math.cos(N), math.cos(2 * N), math.cos(3 * N)
    sN, s2N, s3N = math.sin(N), math.sin(2 * N), math.sin(3 * N)
    fM2 = 1.0004 - 0.0373 * cN + 0.0002 * c2N
    uM2 = -2.14 * sN
    fK1 = 1.0060 + 0.1150 * cN - 0.0088 * c2N + 0.0006 * c3N
    uK1 = -8.86 * sN + 0.68 * s2N - 0.07 * s3N
    fO1 = 1.0089 + 0.1871 * cN - 0.0147 * c2N + 0.0014 * c3N
    uO1 = 10.80 * sN - 1.34 * s2N + 0.19 * s3N
    return {
        "M2": (fM2, uM2), "N2": (fM2, uM2), "S2": (1.0, 0.0),
        "K1": (fK1, uK1), "O1": (fO1, uO1), "Q1": (fO1, uO1),
        "M4": (fM2 ** 2, 2 * uM2), "MS4": (fM2, uM2), "M6": (fM2 ** 3, 3 * uM2),
    }


_F0 = _node_factors(_T0)   # reference nodal state at the fit-window centre


def _adjust(model, dt):
    """Nodal-correct a model for date dt (relative to fit epoch _T0).
    Returns (Z0, [(speed, amp, phase_deg), ...]) for synthesis."""
    fac = _node_factors(dt)
    cons = []
    for name, (sp, H, g) in model["C"].items():
        f, u = fac.get(name, (1.0, 0.0))
        f0, u0 = _F0.get(name, (1.0, 0.0))
        cons.append((sp, H * f / f0, (g - (u - u0)) % 360.0))
    return model["Z0"], cons


def _height(Z0, cons, dt):
    t = (dt - _EPOCH).total_seconds() / 3600.0
    h = Z0
    for sp, H, g in cons:
        h += H * math.cos(math.radians(sp) * t - math.radians(g))
    return h


def _extremes(model, start_utc, days=4, step_min=1):
    # nodal factors are ~constant over a 4-day window, so resolve them once at the start
    Z0, cons = _adjust(model, start_utc)
    n = int(days * 1440 / step_min)
    ts = [start_utc + timedelta(minutes=step_min * i) for i in range(n + 2)]
    hs = [_height(Z0, cons, t) for t in ts]
    out = []
    for i in range(1, len(hs) - 1):
        if hs[i] > hs[i - 1] and hs[i] >= hs[i + 1]:
            out.append({"dt": int(ts[i].timestamp()), "height": hs[i], "type": "High"})
        elif hs[i] < hs[i - 1] and hs[i] <= hs[i + 1]:
            out.append({"dt": int(ts[i].timestamp()), "height": hs[i], "type": "Low"})
    return out


def fetch_tides(locations):
    """Drop-in replacement for fetch_worldtides().

    locations: the TIDES_LOCATIONS list (needs each loc["id"]).
    Returns {loc_id: (extremes, is_live, updated_str)} - identical shape to the
    old WorldTides path, so build_conditions_page() needs no changes.
    """
    now = datetime.now(timezone.utc)
    updated = now.astimezone(_SR_TZ).strftime("%d %b %Y %H:%M SR")
    res = {}
    for loc in locations:
        m = TIDE_MODELS.get(loc["id"])
        if not m:
            res[loc["id"]] = ([], False, "No data")          # graceful: panel shows "no data"
            continue
        res[loc["id"]] = (_extremes(m, now, days=4), True, updated)
    return res


if __name__ == "__main__":
    locs = [{"id": "suriname"}, {"id": "commewijne"}, {"id": "nickerie"}, {"id": "marowijne"}]
    for lid, (ex, live, upd) in fetch_tides(locs).items():
        print(f"\n{lid}  (live={live}, updated={upd}, n={len(ex)})")
        for e in ex[:6]:
            t = datetime.fromtimestamp(e["dt"], tz=_SR_TZ)
            print(f"  {t:%a %d %b %H:%M SR}  {e['type']:4}  {e['height']:.2f} m")
