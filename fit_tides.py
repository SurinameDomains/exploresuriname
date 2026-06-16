#!/usr/bin/env python3
"""
Self-contained derivation of the offline tide constituents baked into
tide_harmonics.py. One-time calibration; NOT imported at build time.

Source : tide-forecast.com 30-day high/low tables (datum = Mean Lower Low Water),
         16 Jun - 14 Jul 2026, for Paramaribo (Suriname R.), Nieuw Nickerie
         (Nickerie R.) and Les Hattes (Maroni/Marowijne mouth, opposite Albina).
Method : value + turning-point (zero-slope) least squares, weight 1.0.
         Constituents M2 S2 N2 K1 O1 Q1 M4 MS4 M6 - the M6 overtide was kept
         because OUT-OF-SAMPLE cross-validation (train 20d / test 9d) showed it
         lowers held-out error; K2/P1/2N2/NU2 were rejected (overfit at 30 days).
Run    : `python fit_tides.py`  -> prints validation + paste-ready TIDE_MODELS
         blocks and the nodal-factor sanity table. tide_harmonics.py adds the
         18.6-yr nodal (f,u) correction at synthesis time.
"""
import math
from datetime import datetime, timedelta, timezone

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
J2000 = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
SR = timezone(timedelta(hours=-3))
T0 = datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)   # fit-window centre

PARAMARIBO = """
06-16 01:03 L 0.32 | 06-16 06:41 H 2.49 | 06-16 13:37 L 0.11 | 06-16 19:18 H 2.29
06-17 01:52 L 0.35 | 06-17 07:31 H 2.44 | 06-17 14:26 L 0.17 | 06-17 20:07 H 2.24
06-18 02:42 L 0.40 | 06-18 08:21 H 2.37 | 06-18 15:16 L 0.25 | 06-18 20:57 H 2.18
06-19 03:34 L 0.45 | 06-19 09:12 H 2.27 | 06-19 16:07 L 0.35 | 06-19 21:48 H 2.12
06-20 04:27 L 0.52 | 06-20 10:06 H 2.16 | 06-20 16:59 L 0.46 | 06-20 22:41 H 2.06
06-21 05:23 L 0.57 | 06-21 11:02 H 2.07 | 06-21 17:52 L 0.55 | 06-21 23:35 H 2.02
06-22 06:21 L 0.61 | 06-22 12:01 H 1.99 | 06-22 18:47 L 0.62
06-23 00:30 H 2.00 | 06-23 07:20 L 0.63 | 06-23 13:00 H 1.94 | 06-23 19:43 L 0.66
06-24 01:25 H 2.00 | 06-24 08:18 L 0.62 | 06-24 13:57 H 1.92 | 06-24 20:37 L 0.68
06-25 02:18 H 2.01 | 06-25 09:12 L 0.59 | 06-25 14:52 H 1.93 | 06-25 21:29 L 0.67
06-26 03:09 H 2.05 | 06-26 10:03 L 0.55 | 06-26 15:42 H 1.95 | 06-26 22:17 L 0.65
06-27 03:56 H 2.09 | 06-27 10:50 L 0.50 | 06-27 16:29 H 1.99 | 06-27 23:02 L 0.62
06-28 04:40 H 2.14 | 06-28 11:34 L 0.45 | 06-28 17:12 H 2.02 | 06-28 23:45 L 0.58
06-29 05:22 H 2.18 | 06-29 12:15 L 0.41 | 06-29 17:53 H 2.06
06-30 00:25 L 0.55 | 06-30 06:02 H 2.22 | 06-30 12:55 L 0.37 | 06-30 18:32 H 2.09
07-01 01:05 L 0.51 | 07-01 06:41 H 2.25 | 07-01 13:34 L 0.35 | 07-01 19:11 H 2.12
07-02 01:44 L 0.48 | 07-02 07:21 H 2.27 | 07-02 14:13 L 0.34 | 07-02 19:50 H 2.14
07-03 02:24 L 0.46 | 07-03 08:01 H 2.27 | 07-03 14:52 L 0.34 | 07-03 20:29 H 2.15
07-04 03:05 L 0.45 | 07-04 08:43 H 2.26 | 07-04 15:34 L 0.36 | 07-04 21:11 H 2.16
07-05 03:50 L 0.44 | 07-05 09:28 H 2.23 | 07-05 16:17 L 0.39 | 07-05 21:56 H 2.16
07-06 04:38 L 0.45 | 07-06 10:18 H 2.19 | 07-06 17:05 L 0.44 | 07-06 22:45 H 2.15
07-07 05:31 L 0.46 | 07-07 11:12 H 2.13 | 07-07 17:58 L 0.50 | 07-07 23:39 H 2.13
07-08 06:30 L 0.48 | 07-08 12:13 H 2.07 | 07-08 18:56 L 0.55
07-09 00:39 H 2.13 | 07-09 07:35 L 0.48 | 07-09 13:19 H 2.04 | 07-09 20:00 L 0.58
07-10 01:44 H 2.15 | 07-10 08:43 L 0.44 | 07-10 14:27 H 2.03 | 07-10 21:06 L 0.58
07-11 02:49 H 2.19 | 07-11 09:50 L 0.38 | 07-11 15:34 H 2.07 | 07-11 22:10 L 0.54
07-12 03:52 H 2.26 | 07-12 10:52 L 0.31 | 07-12 16:36 H 2.14 | 07-12 23:11 L 0.47
07-13 04:51 H 2.34 | 07-13 11:49 L 0.23 | 07-13 17:31 H 2.21
07-14 00:06 L 0.40 | 07-14 05:46 H 2.41 | 07-14 12:41 L 0.17 | 07-14 18:22 H 2.27
"""
NICKERIE = """
06-16 05:41 H 2.82 | 06-16 12:16 L 0.11 | 06-16 18:18 H 2.62
06-17 00:31 L 0.35 | 06-17 06:31 H 2.78 | 06-17 13:05 L 0.17 | 06-17 19:07 H 2.58
06-18 01:21 L 0.40 | 06-18 07:21 H 2.70 | 06-18 13:55 L 0.25 | 06-18 19:57 H 2.52
06-19 02:13 L 0.45 | 06-19 08:12 H 2.60 | 06-19 14:46 L 0.35 | 06-19 20:48 H 2.46
06-20 03:06 L 0.52 | 06-20 09:06 H 2.50 | 06-20 15:38 L 0.46 | 06-20 21:41 H 2.40
06-21 04:02 L 0.57 | 06-21 10:02 H 2.40 | 06-21 16:31 L 0.55 | 06-21 22:35 H 2.36
06-22 05:00 L 0.61 | 06-22 11:01 H 2.33 | 06-22 17:26 L 0.62 | 06-22 23:30 H 2.33
06-23 05:59 L 0.63 | 06-23 12:00 H 2.28 | 06-23 18:22 L 0.66
06-24 00:25 H 2.33 | 06-24 06:57 L 0.62 | 06-24 12:57 H 2.26 | 06-24 19:16 L 0.68
06-25 01:18 H 2.35 | 06-25 07:51 L 0.59 | 06-25 13:52 H 2.26 | 06-25 20:08 L 0.67
06-26 02:09 H 2.39 | 06-26 08:42 L 0.55 | 06-26 14:42 H 2.29 | 06-26 20:56 L 0.65
06-27 02:56 H 2.43 | 06-27 09:29 L 0.50 | 06-27 15:29 H 2.32 | 06-27 21:41 L 0.62
06-28 03:40 H 2.47 | 06-28 10:13 L 0.45 | 06-28 16:12 H 2.36 | 06-28 22:24 L 0.58
06-29 04:22 H 2.52 | 06-29 10:54 L 0.41 | 06-29 16:53 H 2.40 | 06-29 23:04 L 0.55
06-30 05:02 H 2.56 | 06-30 11:34 L 0.37 | 06-30 17:32 H 2.43 | 06-30 23:44 L 0.51
07-01 05:41 H 2.58 | 07-01 12:13 L 0.35 | 07-01 18:11 H 2.46
07-02 00:23 L 0.48 | 07-02 06:21 H 2.61 | 07-02 12:52 L 0.34 | 07-02 18:50 H 2.48
07-03 01:03 L 0.46 | 07-03 07:01 H 2.61 | 07-03 13:31 L 0.34 | 07-03 19:29 H 2.49
07-04 01:44 L 0.45 | 07-04 07:43 H 2.60 | 07-04 14:13 L 0.36 | 07-04 20:11 H 2.50
07-05 02:29 L 0.44 | 07-05 08:28 H 2.57 | 07-05 14:56 L 0.39 | 07-05 20:56 H 2.49
07-06 03:17 L 0.45 | 07-06 09:18 H 2.52 | 07-06 15:44 L 0.44 | 07-06 21:45 H 2.48
07-07 04:10 L 0.46 | 07-07 10:12 H 2.46 | 07-07 16:37 L 0.50 | 07-07 22:39 H 2.47
07-08 05:09 L 0.48 | 07-08 11:13 H 2.40 | 07-08 17:35 L 0.55 | 07-08 23:39 H 2.47
07-09 06:14 L 0.48 | 07-09 12:19 H 2.37 | 07-09 18:39 L 0.58
07-10 00:44 H 2.48 | 07-10 07:22 L 0.44 | 07-10 13:27 H 2.37 | 07-10 19:45 L 0.58
07-11 01:49 H 2.53 | 07-11 08:29 L 0.38 | 07-11 14:34 H 2.41 | 07-11 20:49 L 0.54
07-12 02:52 H 2.60 | 07-12 09:31 L 0.31 | 07-12 15:36 H 2.47 | 07-12 21:50 L 0.47
07-13 03:51 H 2.68 | 07-13 10:28 L 0.23 | 07-13 16:31 H 2.54 | 07-13 22:45 L 0.40
07-14 04:46 H 2.74 | 07-14 11:20 L 0.17 | 07-14 17:22 H 2.61 | 07-14 23:36 L 0.34
"""
LESHATTES = """
06-16 00:03 L 0.64 | 06-16 05:37 H 3.05 | 06-16 12:45 L 0.26 | 06-16 18:17 H 2.61
06-17 00:53 L 0.64 | 06-17 06:26 H 2.99 | 06-17 13:33 L 0.31 | 06-17 19:07 H 2.56
06-18 01:44 L 0.67 | 06-18 07:18 H 2.87 | 06-18 14:21 L 0.41 | 06-18 20:00 H 2.50
06-19 02:34 L 0.74 | 06-19 08:11 H 2.71 | 06-19 15:10 L 0.54 | 06-19 20:56 H 2.43
06-20 03:27 L 0.83 | 06-20 09:10 H 2.54 | 06-20 15:59 L 0.69 | 06-20 21:58 H 2.38
06-21 04:23 L 0.92 | 06-21 10:16 H 2.37 | 06-21 16:50 L 0.84 | 06-21 23:03 H 2.35
06-22 05:23 L 0.99 | 06-22 11:26 H 2.25 | 06-22 17:43 L 0.96
06-23 00:05 H 2.35 | 06-23 06:29 L 1.02 | 06-23 12:33 H 2.18 | 06-23 18:42 L 1.05
06-24 01:00 H 2.38 | 06-24 07:37 L 1.01 | 06-24 13:33 H 2.17 | 06-24 19:43 L 1.10
06-25 01:50 H 2.43 | 06-25 08:40 L 0.95 | 06-25 14:25 H 2.18 | 06-25 20:41 L 1.10
06-26 02:36 H 2.48 | 06-26 09:32 L 0.87 | 06-26 15:11 H 2.22 | 06-26 21:32 L 1.07
06-27 03:17 H 2.54 | 06-27 10:16 L 0.79 | 06-27 15:53 H 2.27 | 06-27 22:16 L 1.02
06-28 03:57 H 2.60 | 06-28 10:56 L 0.72 | 06-28 16:32 H 2.31 | 06-28 22:56 L 0.97
06-29 04:35 H 2.65 | 06-29 11:33 L 0.66 | 06-29 17:09 H 2.35 | 06-29 23:34 L 0.92
06-30 05:11 H 2.68 | 06-30 12:09 L 0.62 | 06-30 17:44 H 2.37
07-01 00:11 L 0.89 | 07-01 05:46 H 2.69 | 07-01 12:45 L 0.59 | 07-01 18:19 H 2.39
07-02 00:48 L 0.87 | 07-02 06:21 H 2.69 | 07-02 13:21 L 0.60 | 07-02 18:53 H 2.40
07-03 01:26 L 0.87 | 07-03 06:56 H 2.66 | 07-03 13:57 L 0.62 | 07-03 19:29 H 2.40
07-04 02:05 L 0.88 | 07-04 07:34 H 2.60 | 07-04 14:34 L 0.67 | 07-04 20:07 H 2.40
07-05 02:47 L 0.89 | 07-05 08:15 H 2.53 | 07-05 15:13 L 0.73 | 07-05 20:50 H 2.40
07-06 03:32 L 0.91 | 07-06 09:03 H 2.43 | 07-06 15:55 L 0.81 | 07-06 21:41 H 2.40
07-07 04:23 L 0.93 | 07-07 10:01 H 2.32 | 07-07 16:42 L 0.90 | 07-07 22:40 H 2.41
07-08 05:22 L 0.93 | 07-08 11:12 H 2.24 | 07-08 17:37 L 0.97 | 07-08 23:47 H 2.45
07-09 06:30 L 0.90 | 07-09 12:29 H 2.22 | 07-09 18:42 L 1.01
07-10 00:54 H 2.54 | 07-10 07:46 L 0.81 | 07-10 13:40 H 2.26 | 07-10 19:54 L 1.00
07-11 01:57 H 2.66 | 07-11 08:58 L 0.68 | 07-11 14:42 H 2.34 | 07-11 21:05 L 0.92
07-12 02:54 H 2.80 | 07-12 10:01 L 0.52 | 07-12 15:38 H 2.44 | 07-12 22:08 L 0.81
07-13 03:48 H 2.92 | 07-13 10:55 L 0.39 | 07-13 16:29 H 2.53 | 07-13 23:03 L 0.69
07-14 04:39 H 3.00 | 07-14 11:45 L 0.29 | 07-14 17:18 H 2.61 | 07-14 23:53 L 0.60
"""
DATA = {"suriname": PARAMARIBO, "nickerie": NICKERIE, "marowijne": LESHATTES}
SP = {"M2": 28.9841042, "S2": 30.0, "N2": 28.4397295, "K1": 15.0410686,
      "O1": 13.9430356, "Q1": 13.3986609, "M4": 57.9682084, "MS4": 58.9841042,
      "M6": 86.9523127}
NAMES = list(SP)


def parse(block):
    pts = []
    for tok in block.replace("\n", " | ").split("|"):
        tok = tok.strip()
        if not tok:
            continue
        md, hm, typ, h = tok.split()
        mo, da = map(int, md.split("-"))
        H, M = map(int, hm.split(":"))
        dt = datetime(2026, mo, da, H, M, tzinfo=SR).astimezone(timezone.utc)
        pts.append(((dt - EPOCH).total_seconds() / 3600.0, float(h), typ))
    return pts


def fit(pts, names, w=1.0):
    m = 1 + 2 * len(names)
    def bv(t):
        r = [1.0]
        for n in names:
            wn = math.radians(SP[n]); r += [math.cos(wn * t), math.sin(wn * t)]
        return r
    def bs(t):
        r = [0.0]
        for n in names:
            wn = math.radians(SP[n]); r += [-wn * math.sin(wn * t), wn * math.cos(wn * t)]
        return r
    A = [[0.0] * m for _ in range(m)]; c = [0.0] * m
    for t, h, _ in pts:
        v = bv(t)
        for i in range(m):
            for j in range(m): A[i][j] += v[i] * v[j]
            c[i] += v[i] * h
        s = bs(t); ws2 = w * w
        for i in range(m):
            for j in range(m): A[i][j] += ws2 * s[i] * s[j]
    Mx = [row[:] + [c[i]] for i, row in enumerate(A)]
    for i in range(m):
        p = max(range(i, m), key=lambda r: abs(Mx[r][i])); Mx[i], Mx[p] = Mx[p], Mx[i]
        pv = Mx[i][i]
        for j in range(i, m + 1): Mx[i][j] /= pv
        for r in range(m):
            if r == i: continue
            f = Mx[r][i]
            for j in range(i, m + 1): Mx[r][j] -= f * Mx[i][j]
    x = [Mx[i][m] for i in range(m)]
    Z0 = x[0]; con = {}; idx = 1
    for n in names:
        a, b = x[idx], x[idx + 1]; idx += 2
        con[n] = (SP[n], math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360)
    return Z0, con


def hgt(Z0, con, t):
    return Z0 + sum(H * math.cos(math.radians(sp) * t - math.radians(g)) for sp, H, g in con.values())


def extremes(Z0, con, t0, t1, step=1):
    n = int((t1 - t0) * 60 / step)
    hs = [(t0 + i * step / 60.0, hgt(Z0, con, t0 + i * step / 60.0)) for i in range(n + 1)]
    out = []
    for i in range(1, len(hs) - 1):
        if hs[i][1] > hs[i - 1][1] and hs[i][1] >= hs[i + 1][1]: out.append((hs[i][0], hs[i][1], "H"))
        elif hs[i][1] < hs[i - 1][1] and hs[i][1] <= hs[i + 1][1]: out.append((hs[i][0], hs[i][1], "L"))
    return out


def err(pts, Z0, con):
    t0 = min(p[0] for p in pts) - 6; t1 = max(p[0] for p in pts) + 6
    pred = extremes(Z0, con, t0, t1); dts = []; dhs = []
    for t, h, typ in pts:
        cand = [p for p in pred if p[2] == typ]
        b = min(cand, key=lambda p: abs(p[0] - t))
        dts.append(abs(b[0] - t) * 60); dhs.append(abs(b[1] - h) * 100)
    return sum(dts) / len(dts), max(dts), math.sqrt(sum(d * d for d in dhs) / len(dhs)), max(dhs)


def node_factors(dt):
    D = (dt - J2000).total_seconds() / 86400.0
    N = math.radians((125.0445 - 0.0529539222 * D) % 360.0)
    cN, c2N, c3N = math.cos(N), math.cos(2 * N), math.cos(3 * N)
    sN, s2N, s3N = math.sin(N), math.sin(2 * N), math.sin(3 * N)
    fM2 = 1.0004 - 0.0373 * cN + 0.0002 * c2N
    fK1 = 1.0060 + 0.1150 * cN - 0.0088 * c2N + 0.0006 * c3N
    fO1 = 1.0089 + 0.1871 * cN - 0.0147 * c2N + 0.0014 * c3N
    return {"M2": fM2, "K1": fK1, "O1": fO1}, math.degrees(N) % 360


if __name__ == "__main__":
    # out-of-sample check: does M6 help on held-out days? (train < 6 Jul, test >= 6 Jul)
    CUT = (datetime(2026, 7, 6, tzinfo=SR).astimezone(timezone.utc) - EPOCH).total_seconds() / 3600.0
    base = ["M2", "S2", "N2", "K1", "O1", "Q1", "M4", "MS4"]
    print("out-of-sample held-out height RMS (cm):  base8  vs  base8+M6")
    for st, block in DATA.items():
        pts = parse(block); tr = [p for p in pts if p[0] < CUT]; te = [p for p in pts if p[0] >= CUT]
        z0, c0 = fit(tr, base); z1, c1 = fit(tr, base + ["M6"])
        print(f"  {st:10s}  {err(te, z0, c0)[2]:5.1f}      {err(te, z1, c1)[2]:5.1f}")

    print("\nFINAL fit (M2 S2 N2 K1 O1 Q1 M4 MS4 M6) + reproduction of published 2026 tables:")
    models = {}
    for st, block in DATA.items():
        Z0, con = fit(parse(block), NAMES); models[st] = (Z0, con)
        tm, tx, hr, hx = err(parse(block), Z0, con)
        print(f"  {st:10s} Z0={Z0:.4f}  time {tm:4.1f}/{tx:4.1f} min   height {hr:.1f}/{hx:.1f} cm")

    f0, N0 = node_factors(T0)
    print(f"\nnodal anchor t0={T0:%Y-%m-%d}  N={N0:.1f}deg  fM2={f0['M2']:.3f} fK1={f0['K1']:.3f} fO1={f0['O1']:.3f}")

    print("\npaste-ready TIDE_MODELS blocks:")
    for st in ["suriname", "nickerie", "marowijne"]:
        Z0, con = models[st]
        print(f'    "{st}": {{\n        "Z0": {Z0:.4f},\n        "C": {{')
        for n in NAMES:
            sp, H, g = con[n]
            print(f'            "{n}":{" " * (4 - len(n))}({sp}, {H:.4f}, {g:.2f}),')
        print('        },\n    },')
