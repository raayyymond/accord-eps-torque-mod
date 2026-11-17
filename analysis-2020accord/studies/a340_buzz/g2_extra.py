# -*- coding: utf-8 -*-
"""g2_extra.py -- (E1) where the REV 4 angle loop fails on the EXPLICIT plant (mechanical J_m, b_mech, k + explicit lane):
the minimum mechanical viscous damping that passes, by J_m and speed;  (E2) two-mass stress (a lightly damped 16.5 / 22 /
25 Hz mode) for REV 3 / REV 4 / MID;  (E3) lane damping part by config (sign check of the 'lagged inertia' reading);
(E4) wheel-rate PSD 4-48 Hz, engaged not pressed: A340 stock fw vs A160 V300 vs A340 REV 3.   ANALYSIS ONLY.  Seconds."""
import math
import os
import sys
import time
import numpy as np
from scipy import signal

t00 = time.time()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import g2_score as S   # noqa: E402   (runs its tables once on import; ~10 s)  -- reuse its functions
G, HF, FH = S.G, S.HF, S.FH
print("\n\n================ g2_extra ================")

# ---------------------------------------------------------------- E1
print("(E1) explicit plant, lane delay 2 ms: smallest b_mech multiplier (of the family nominal b at that speed) at which the angle loop")
print("     passes PM>=45, GM>=6, T5-30<=+3 (and the local loop is stable).  '-' = fails even at x1.0; value in () = b in T/(deg/s)")
BM = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0)
print("| v | k x | J_m | " + " | ".join(list(S.CFG)[:3]) + " |")
print("|---|---|---|---|---|---|")
for v in (3.0, 5.0, 8.0, 12.5):
    c = G.ctl_v299(v)
    Fr = G.F_r24(FH, v, G.r24_gain_stock(v) - 2.0, S.SIG_R, S.HTBH)
    pn = HF.plant_at("nominal", v)
    for kk in (1.0, 2.4):
        for Jm in (0.012, 0.02, 0.035, 0.07, 0.15, 0.3):
            cells = []
            for name in list(S.CFG)[:3]:
                rows, K2 = S.CFG[name]
                Fl = S.F_da(FH, v, rows, K2, 2)
                got = None; worst = None
                for bm in BM:
                    Pm = HF.Plant(J=Jm, b=pn.b * bm, k=pn.k * kk).frf(FH)
                    lg, lf = S.local_gm(-Pm * Fl, FH)
                    r = S.metrics(c, Pm / (1 - Pm * (Fl + Fr)), FH)
                    ok = lg > 0 and not S.gate(r) and not r["encircle"]
                    if bm == 0.0:
                        worst = (lg, r["pm"], r["gm_db"], r["T530_db"], r["fTpk"])
                    if ok and got is None:
                        got = bm
                cells.append(("x%.1f (%.1f)" % (got, pn.b * got) if got is not None else "-") +
                             " ; at b=0: loc %.1f dB, PM %.0f GM %.1f T %+.1f @%.0f Hz" % worst)
            print("| %g | %.1f | %.3f | " % (v, kk, Jm) + " | ".join(cells) + " |")

# ---------------------------------------------------------------- E2
print("\n(E2) two-mass stress on the explicit plant (J_total 0.07 and 0.15 mechanical, rim share r2, mode f2, zeta2 0.03), b,k nominal:")
print("     cells: PM / GM dB / T5-30 dB (f) / Ms")
print("| v | J_tot | f2 | r2 | " + " | ".join(list(S.CFG)[:3]) + " |")
print("|---|---|---|---|---|---|---|")
worstE2 = {n: (-99, None) for n in list(S.CFG)[:3]}
for v in (3.0, 8.0, 12.5, 19.0, 26.0):
    c = G.ctl_v299(v)
    Fr = G.F_r24(FH, v, G.r24_gain_stock(v) - 2.0, S.SIG_R, S.HTBH)
    pn = HF.plant_at("nominal", v)
    for Jt in (0.07, 0.15):
        for f2 in (16.5, 22.0, 25.0):
            for r2 in (0.3, 0.6):
                Pm = HF.Plant(J=Jt, b=pn.b, k=pn.k, f2=f2, zeta2=0.03, r2=r2).frf(FH)
                cells = []
                for name in list(S.CFG)[:3]:
                    rows, K2 = S.CFG[name]
                    Fl = S.F_da(FH, v, rows, K2, 2)
                    lg, lf = S.local_gm(-Pm * Fl, FH)
                    r = S.metrics(c, Pm / (1 - Pm * (Fl + Fr)), FH)
                    cells.append(("LOCAL UNSTABLE (%.1f dB @%.0f Hz)" % (lg, lf)) if lg <= 0 else "%.0f / %.1f / %+.1f (%.0f) / %.2f %s" % (
                        r["pm"], r["gm_db"], r["T530_db"], r["fTpk"], r["Ms"], S.gate(r)))
                    if lg > 0 and r["T530_db"] > worstE2[name][0]:
                        worstE2[name] = (r["T530_db"], (v, Jt, f2, r2, r["gm_db"], r["pm"]))
                if v in (3.0, 19.0):
                    print("| %g | %.2f | %.1f | %.1f | " % (v, Jt, f2, r2) + " | ".join(cells) + " |")
print("     worst T5-30 over the E2 grid (5 speeds x 2 J x 3 f2 x 2 r2): " + "; ".join("%s %+.1f dB at %s" % (n, w[0], w[1]) for n, w in worstE2.items()))

# ---------------------------------------------------------------- E3
print("\n(E3) lane damping part -Re(F/jw), T per deg/s (>0 = opposes motion), no lane delay / 2 ms lane delay, v = 5.6 m/s (20 km/h):")
for name, (rows, K2) in S.CFG.items():
    s = []
    for f in (2.0, 5.0, 10.0, 15.0, 20.0, 30.0, 50.0, 80.0, 120.0):
        fa = np.array([f])
        s.append("%g Hz %+.2f/%+.2f" % (f, G.damping_part(S.F_da(fa, 5.56, rows, K2, 0), fa)[0], G.damping_part(S.F_da(fa, 5.56, rows, K2, 2), fa)[0]))
    print("   %-16s %s" % (name, "  ".join(s)))

# ---------------------------------------------------------------- E4
print("\n(E4) 0x14A wheel-rate PSD, engaged & not pressed, 10-20 m/s (A160 also 1-6 m/s): sqrt(PSD x 2 Hz) = rms in each 2 Hz bin, deg/s")
bins = np.arange(4, 50, 2)
print("      bin lo Hz:      " + " ".join("%5d" % b for b in bins[:-1]))
for name, fn, lo, hi in (("A340 stock fw", "g2_cache_a340_stock.npz", 10, 20), ("A160 V300", "g2_cache_a160_v300.npz", 10, 20),
                         ("A160 V300 creep", "g2_cache_a160_v300.npz", 1, 6), ("A340 REV3", "g2_cache_a340_mod.npz", 10, 20),
                         ("A340 REV3 creep", "g2_cache_a340_mod.npz", 1, 6)):
    z = np.load(os.path.join(HERE, fn))
    ok = (z["req"] > 0.5) & (z["pressed"] < 0.5) & (z["v"] >= lo) & (z["v"] < hi)
    idx = np.flatnonzero(ok)
    runs = [r for r in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(r) >= 256]
    P = 0; n = 0
    for r in runs:
        f, p = signal.welch(signal.detrend(z["rate"][r]), 100, nperseg=256)
        P = P + p * len(r); n += len(r)
    P = P / max(n, 1)
    df = f[1] - f[0]
    print("      %-15s " % name + " ".join("%5.2f" % math.sqrt(P[(f >= b) & (f < b + 2)].sum() * df) for b in bins[:-1]) + "   (%.0f s)" % (n / 100))
print("\nwall %.1f s" % (time.time() - t00))
