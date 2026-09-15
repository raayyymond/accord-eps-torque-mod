# -*- coding: utf-8 -*-
"""v293r3_ffneed.py -- how much of the NEEDED torque did the feedforward supply, by band and frequency?  2026-09-14.
Hands-off stretches; u = total applied torque (controller frame), f_t = f/LAF = the feedforward torque.
Also: regression of u (0.5 Hz LPF) on the fork hold map evaluated at the MEASURED angle, per stretch with a free
intercept (removes crown/wind bias) -> the map's level error; and the relay reconstruction on r73."""
import os, sys
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import v293_ident_lib as L
import v293r3_read as R3
FS, DT = L.FS, 1.0 / L.FS
IB, IBN = R3.IB, R3.IBN
sos05 = signal.butter(2, 0.5, "lowpass", fs=FS, output="sos")
for tag in sys.argv[1:] or ["r72_v293r3", "r73_v293r3", "r71_v293r2", "r70_v293"]:
    g = R3.load_plus(tag); P = g["meta"]["params"]
    v, ang, u = g["v"], g["ang"], -g["op_torque"]; th = -ang
    q2 = g["eng"] & (np.abs(g["out"]) > 1e-3)
    LAF = float(np.median(-(g["p"][q2] + g["i"][q2] + g["f"][q2]) / g["out"][q2]))
    f_t, p_t, i_t = g["f"] / LAF, g["p"] / LAF, g["i"] / LAF
    eng = g["eng"] & (g["cs_active"] > 0.5) & np.isfinite(u)
    w = int(0.5 * FS)
    hoff = eng & ~(np.convolve((g["press"] > 0.5).astype(float), np.ones(2 * w + 1), mode="same") > 0)
    print("\n==== %s  commit %s  SteerFriction %s  LAF %.1f" % (tag, str(P.get("GitCommit"))[:9], P.get("SteerFriction"), LAF))
    print("  band |  <0.3 Hz: f/u slope  (p+i)/u | 0.3-1 Hz: f/u   | rms u  rms f  rms p  rms i (LPF 0.5) | map(ang) slope per stretch: median [p25 p75], n | f_t vs map(ang_des) slope")
    for (lo, hi), nm in zip(IB, IBN):
        m = hoff & (v >= lo) & (v < hi) & np.isfinite(f_t)
        st = L.stretches(m, int(6 * FS))
        if not st: continue
        U = np.concatenate([signal.sosfiltfilt(sos05, u[a:b]) for a, b in st])
        F = np.concatenate([signal.sosfiltfilt(sos05, f_t[a:b]) for a, b in st])
        PI = np.concatenate([signal.sosfiltfilt(sos05, (p_t + i_t)[a:b]) for a, b in st])
        Pp = np.concatenate([signal.sosfiltfilt(sos05, p_t[a:b]) for a, b in st])
        Ii = np.concatenate([signal.sosfiltfilt(sos05, i_t[a:b]) for a, b in st])
        sl_f = np.polyfit(U, F, 1)[0]; sl_pi = np.polyfit(U, PI, 1)[0]
        Ub = np.concatenate([R3.bp(u[a:b], 0.3, 1.0) for a, b in st]); Fb = np.concatenate([R3.bp(f_t[a:b], 0.3, 1.0) for a, b in st])
        sl_fb = np.polyfit(Ub, Fb, 1)[0]
        slopes = []
        for a, b in st:
            hm = R3.hold_torque(th[a:b], v[a:b]); uu = signal.sosfiltfilt(sos05, u[a:b]); hm = signal.sosfiltfilt(sos05, hm)
            if np.std(hm) > 0.005:
                slopes.append(np.polyfit(hm, uu, 1)[0])
        ad = R3.angle_des_from_setpoint(np.nan_to_num(g["la_des"]), np.nan_to_num(v), ang, np.nan_to_num(g["roll"]))
        hd = -R3.hold_torque(ad, v)
        HD = np.concatenate([signal.sosfiltfilt(sos05, hd[a:b]) for a, b in st])
        sl_fd = np.polyfit(HD, F, 1)[0]
        print("  %-5s | %8.2f %8.2f            | %8.2f       | %5.3f %5.3f %5.3f %5.3f | %5.2f [%4.2f %4.2f] n %2d | %5.2f"
              % (nm, sl_f, sl_pi, sl_fb, np.std(U), np.std(F), np.std(Pp), np.std(Ii),
                 np.median(slopes) if slopes else np.nan, *(np.percentile(slopes, [25, 75]) if len(slopes) > 1 else (np.nan, np.nan)), len(slopes), sl_fd))
    # relay reconstruction (SteerFriction toggle) on the residual of the S6 replay
    FR = float(P.get("SteerFriction", 0) or 0)
    if FR > 0.05:
        LOWX, LOWY = [0, 10, 20, 30], [12, 10.5, 8, 5]
        lsf = (np.interp(v, LOWX, LOWY) / np.maximum(v, 1.0)) ** 2
        KP = 0.85
        # pid_log.error IS the lsf-inflated (and notched) error -> relay argument uses it directly
        relay = FR * np.clip(g["err"] / 0.3, -1, 1)   # + 0.22*friction_jerk, ignored here
        m = eng & np.isfinite(relay)
        print("  relay 0.212 reconstructed: rms %.4f torque, |relay| >= 0.1 duty %.1f %%, sign flips %.1f /min; effective small-signal gain %.1f (LAF units) vs Kp 0.85"
              % (np.sqrt(np.mean(relay[m] ** 2)), 100 * np.mean(np.abs(relay[m]) >= 0.1), np.sum(np.diff(np.sign(relay[m])) != 0) / (m.sum() * DT / 60), FR / 0.3 * LAF))
