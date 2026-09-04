# -*- coding: utf-8 -*-
"""studies/osc-highangle/oversteer_v283_levers.py -- sizing the NON-INTEGRATOR replacements for Ki 50.

The question: Ki 50 fixed the r35 stall/deadband class (section 3 of oversteer_v283.py: stalled runs 7 -> 0/1/0,
idx 40-80 rate/reference 23 % -> 72-95 %).  If the integrator has to go, what else buys that?

Kp is the obvious candidate, but V281 rev 3 flattened Kp to 248 exactly to kill the 7 Hz limit cycle.  So the
question is WHERE IN DEMAND INDEX the 7 Hz ring lives.  If it lives at high idx and the stall lives at idx 40-112,
Kp can be un-flattened over the stall band alone.  This measures both, on the routes that carry each build:
  A  the 7 Hz ring by demand-index bin, r34 (stock Kp LERP 248..696) vs r35 (flat 248) vs V283 -- tap 6-8.5 Hz
     ripple / level, P-rail duty, and the 0x18F rate's own 6-8.5 Hz amplitude, in hands-light engaged frames
  B  the stall statistic by the same bins, so the two can be read on one axis
  C  what a partial un-flattening would deliver: the chain's T at the r35 stall frames under each Kp candidate

Run: python oversteer_v283_levers.py
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import oversteer_v283 as O  # noqa: E402

V, ST = O.V, O.ST
FS, CPD = O.FS, O.CPD
LINES = []


def pr(s=""):
    print(s, flush=True)
    LINES.append(s)


def bamp(x, lo=6.0, hi=8.5):
    if len(x) < 64:
        return np.nan
    return ST.band_amp(np.asarray(x, float), lo, hi)


IDX = ((1, 20), (20, 40), (40, 68), (68, 112), (112, 136), (136, 200), (200, 241))
KP_CANDS = (
    ("flat 248 (V281r3/V283, FLOWN r35/r36-38)", np.full(5, 248.0)),
    ("stock LERP 248,512,645,696,696 (FLOWN r32/r33/r34)", O.KP_STOCK[1]),
    ("flat 341 (V281 rev 2, BUILT, SUPERSEDED, NEVER FLOWN)", np.full(5, 341.0)),
    ("PARTIAL: 248,512,512,248,248 (un-flatten idx 40-136 only)", np.array([248, 512, 512, 248, 248], float)),
    ("PARTIAL: 248,450,450,248,248", np.array([248, 450, 450, 248, 248], float)),
)


def main():
    routes = {t: V.Route(t) for t in O.ROUTES}
    pr("=" * 165)
    pr("A/B -- THE 7 Hz RING AND THE STALL, BOTH BY DEMAND-INDEX BIN (engaged, hands-light |tq_raw| < 512)")
    pr("  ring   = tap 6-8.5 Hz ripple / |T| level, and the 0x18F rate's own 6-8.5 Hz amplitude (deg/s), over 1.28 s windows")
    pr("  P-rail = duty of |P_raw| >= 15360 in the chain run with THAT ROUTE'S OWN Kp table and Ki")
    pr("  stall  = duty of (|rate| < 0.5 * the map's reference) at |angle| > 10, the class Ki 50 was cut to fix")
    pr("=" * 165)
    for tag in O.ROUTES:
        r = routes[tag]
        R = O.sim(r, kp=O.KP_OF[tag], ki=O.KI_OF[tag])
        ref = R["ref_deg"][r.i100]
        Prail = np.abs(R["P_raw"][r.i100]) >= V.P_CLAMP
        e = r.eng & (np.abs(r.tq_raw) < 512)
        pr("  %s (%s)" % (tag, V.ROUTE_BUILD[tag]))
        for lo, hi in IDX:
            m = e & (r.idx >= lo) & (r.idx < hi)
            if m.sum() < 200:
                pr("     idx %3d-%3d: %5.1f s -- too few" % (lo, hi, m.sum() / FS))
                continue
            wins = [(a, a + 128) for a in range(0, len(m) - 128, 64) if m[a:a + 128].mean() > 0.95]
            rip = np.nan
            ra = np.nan
            if wins:
                rr = [bamp(r.T_meas[a:b]) / max(np.median(np.abs(r.T_meas[a:b])), 1) for a, b in wins]
                ra_ = [bamp(r.wire[a:b]) / CPD for a, b in wins]
                rip = float(np.median(rr))
                ra = float(np.median(ra_))
            mv = m & (ref > 3)
            stall = float(np.mean(np.abs(r.wire[mv]) / CPD < 0.5 * ref[mv])) if mv.sum() > 100 else np.nan
            pr("     idx %3d-%3d: %6.1f s | tap |T| p50 %5.0f | ring rip/L %5s (n win %3d) | rate 6-8.5 Hz %5s deg/s | P-rail %.3f | rate/ref p50 %4s | STALL duty %5s"
               % (lo, hi, m.sum() / FS, np.median(np.abs(r.T_meas[m])),
                  "%.2f" % rip if np.isfinite(rip) else "  --", len(wins),
                  "%.1f" % ra if np.isfinite(ra) else "  --", np.mean(Prail[m]),
                  "%.2f" % np.median(np.abs(r.wire[mv]) / CPD / np.maximum(ref[mv], 1)) if mv.sum() > 100 else "  --",
                  "%.3f" % stall if np.isfinite(stall) else "  --"))
    pr()
    pr("=" * 165)
    pr("C -- WHAT EACH Kp CANDIDATE WOULD HAVE DELIVERED ON r35's OWN STALL FRAMES (open loop on the measured rate; Ki 0 in every candidate)")
    pr("  frames: r35, engaged, |angle| >= 30, idx 40-112, hands-light -- the seven stalls' own cell.  The r35 tap there reads |T| p50 847.")
    pr("  V283 (Ki 50) delivered |T| p50 516-855 in the same cell WITH the wheel moving at 72-95 %% of reference (r35: 23 %%).")
    pr("=" * 165)
    r = routes["r35"]
    m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx < 112) & (np.abs(r.tq_raw) < 400)
    pr("  r35 cell: %.1f s, tap |T| p50 %.0f, wheel %.1f deg/s vs reference %.1f" %
       (m.sum() / FS, np.median(np.abs(r.T_meas[m])), np.median(np.abs(r.wire[m])) / CPD,
        np.median(O.sim(r, kp=O.KP_FLAT, ki=0)["ref_deg"][r.i100][m])))
    for name, Y in KP_CANDS:
        R = O.sim(r, kp=(O.KP_FLAT[0], Y), ki=0)
        T = np.abs(R["T"][r.i100][m])
        pr("     %-58s chain |T| p50 %5.0f (x%.2f vs flat 248) | P-rail duty %.3f" %
           (name, np.median(T), np.median(T) / max(np.median(np.abs(O.sim(r, kp=O.KP_FLAT, ki=0)["T"][r.i100][m])), 1),
            float(np.mean(np.abs(R["P_raw"][r.i100][m]) >= V.P_CLAMP))))
    with open(os.path.join(HERE, "_scratch", "oversteer_v283_levers.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()
