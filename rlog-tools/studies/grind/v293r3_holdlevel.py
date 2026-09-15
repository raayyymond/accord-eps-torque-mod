# -*- coding: utf-8 -*-
"""v293r3_holdlevel.py -- is the rev-3 hold map's LEVEL right at speed?  Per route, hands-off, 15-30 m/s:
(1) u (0.5 Hz LPF) vs map(measured angle): slope + intercept, all / left / right;
(2) still-wheel cell medians of the hold torque at |angle| 4-8 / 8-15 / 15-25 deg by band, left and right separately,
    against the map;  (3) the same with the fork's roll compensation folded into the angle (angle - roll-equivalent)."""
import os, sys
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293_ident_lib as L
import v293r3_read as R3
FS, DT = L.FS, 1.0 / L.FS
sos05 = signal.butter(2, 0.5, "lowpass", fs=FS, output="sos")
sos1 = signal.butter(2, 1.0, "lowpass", fs=FS, output="sos")
BANDS = [(8, 15, "8-15"), (15, 22, "15-22"), (22, 40, ">22")]
for tag in sys.argv[1:] or ["r72_v293r3", "r73_v293r3", "r71_v293r2", "r70_v293"]:
    g = R3.load_plus(tag); P = g["meta"]["params"]
    v, ang, u = g["v"], g["ang"], -g["op_torque"]; th = -ang; rate = R3.np.nan_to_num(g["rate_dps"])
    eng = g["eng"] & (g["cs_active"] > 0.5) & np.isfinite(u)
    w = int(0.5 * FS)
    hoff = eng & ~(np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0)
    roll = np.nan_to_num(g["roll"])
    print("\n==== %s  commit %s  roll median %+.2f deg" % (tag, str(P.get("GitCommit"))[:9], np.degrees(np.median(roll[eng]))))
    u1 = signal.sosfiltfilt(sos1, np.nan_to_num(u)); th1 = signal.sosfiltfilt(sos1, np.nan_to_num(th))
    still = hoff & (np.abs(rate) < 15)
    for lo, hi, nm in BANDS:
        m = hoff & (v >= lo) & (v < hi)
        st = L.stretches(m, int(6 * FS))
        if not st: continue
        U = np.concatenate([signal.sosfiltfilt(sos05, u[a:b]) for a, b in st])
        H = np.concatenate([signal.sosfiltfilt(sos05, R3.hold_torque(th[a:b], v[a:b])) for a, b in st])
        TH = np.concatenate([signal.sosfiltfilt(sos05, th[a:b]) for a, b in st])
        RO = np.concatenate([roll[a:b] for a, b in st])
        cf_all = np.polyfit(H, U, 1)
        L_ = TH > 3; Rr = TH < -3
        cf_l = np.polyfit(H[L_], U[L_], 1) if L_.sum() > 300 else (np.nan, np.nan)
        cf_r = np.polyfit(H[Rr], U[Rr], 1) if Rr.sum() > 300 else (np.nan, np.nan)
        # joint fit with a roll term: u = s*map + c*roll + d
        A = np.vstack([H, RO, np.ones(len(H))]).T
        cj, *_ = np.linalg.lstsq(A, U, rcond=None)
        print("  %-5s %4.0f s | u = %.2f*map %+.4f (all, n %d) | left %.2f %+.4f | right %.2f %+.4f | with roll: %.2f*map %+.3f*roll(rad) %+.4f"
              % (nm, len(U) * DT, cf_all[0], cf_all[1], len(U), cf_l[0], cf_l[1], cf_r[0], cf_r[1], cj[0], cj[1], cj[2]))
        # still-wheel cells
        row = []
        for alo, ahi in ((4, 8), (8, 15), (15, 25), (25, 45)):
            for sgn, lab in ((1, "L"), (-1, "R")):
                mm = still & (v >= lo) & (v < hi) & (sgn * th1 >= alo) & (sgn * th1 < ahi)
                if mm.sum() > 100:
                    med_u = np.median(sgn * u1[mm]); med_map = np.median(R3.hold_torque(np.abs(th1[mm]), v[mm]))
                    row.append("%d-%d%s %.3f/%.3f=%.2f(%3.0fs)" % (alo, ahi, lab, med_u, med_map, med_u / max(med_map, 1e-4), mm.sum() * DT))
        print("        still cells (u/map): " + "  ".join(row))
