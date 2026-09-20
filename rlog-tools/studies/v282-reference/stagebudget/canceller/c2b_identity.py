# -*- coding: utf-8 -*-
"""c2b: the EXACT identity test.  On a route with no ref filter,
      setpoint_log == expected + jerk_log * lat_delay       (verbatim from latcontrol_torque.py)
so    expected == setpoint_log - jerk_log * lat_delay   is DIRECTLY OBSERVABLE, with no filter model at all.
Divide by v^2 and it must equal desiredCurvature delayed by exactly `delay_frames`.
This pins `delay_frames` and the whole stage's arithmetic from the log alone.

usage: python c2b_identity.py <route>"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402
from c2_stage import CFG, onepole, DT, MAX_LAT_JERK_UP, LAT_SMOOTH  # noqa: E402


def main():
    r = sys.argv[1]
    cfg = CFG[r]
    S = V.load(r)
    v2 = np.maximum(np.nan_to_num(S["v"]) ** 2, 1e-9)
    curv = np.nan_to_num(S["model"]) / v2
    ld = np.nan_to_num(S["lat_delay"], nan=0.2) + LAT_SMOOTH
    jl = np.nan_to_num(S["jerk_des"])
    sp = np.nan_to_num(S["setpoint"])
    m = V.usable(S)
    keep = np.zeros(len(m), bool)
    for a, b in V.runs(m, S["t"], min_s=5.0):
        keep[a + 300:b] = True
    m = m & keep
    print("route %s  group %s  RF=%.2f  n_nominal=%d  usable %d frames" %
          (r, cfg["g"], cfg["rf"], int(np.median(ld / DT)), m.sum()))
    if cfg["rf"] > 0:
        print("  (ref filter ON: the identity holds on sp_PRE, which is not logged -- this route is informative")
        print("   only through the jerk leg below)")
    exp_obs = (sp - jl * ld) / v2            # == desiredCurvature delayed by delay_frames, if rf == 0
    print()
    print("  A. `expected` recovered from the identity, matched against desiredCurvature at each shift n.")
    print("     Residual normalised by the RMS of (curv - curv_delayed): 0 means an exact hit.")
    sc = None
    for n in range(0, 60):
        idx = np.maximum(np.arange(len(curv)) - n, 0)
        d = exp_obs[m] - curv[idx][m]
        scale = np.sqrt(np.mean((curv[m] - curv[np.maximum(np.arange(len(curv)) - 20, 0)][m]) ** 2))
        val = np.sqrt(np.mean(d ** 2)) / max(scale, 1e-12)
        if sc is None or val < sc[1]:
            sc = (n, val)
        if 0 <= n <= 59 and (n % 1 == 0) and n >= max(0, int(np.median(ld / DT)) - 8) and n <= int(np.median(ld / DT)) + 8:
            print("       n=%2d   %9.5f" % (n, val))
    print("     best n = %d (residual %.5f);  nominal int(lat_delay/dt) = %d" % (sc[0], sc[1], int(np.median(ld / DT))))

    print()
    print("  B. the F_j leg with NO reconstruction of `expected`: input (u - expected_obs), output")
    print("     (sp - expected_obs) = jerk*ld.  Both from the log.  Scan (shift, rc) jointly.")
    uu = np.nan_to_num(S["model"])
    x = (uu - exp_obs * v2) / np.maximum(ld, DT)
    x = np.clip(x, -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
    y = jl
    rc0 = 1.0 / (2.0 * np.pi * cfg["fc"])
    print("     rc0 = %.5f s (fc %.1f Hz).  rel-rms of F_j(x shifted) - y :" % (rc0, cfg["fc"]))
    hdr = "        rc\\shift " + "".join("  %+3d  " % s for s in range(-2, 7))
    print(hdr)
    for mult in (0.6, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5):
        rc = rc0 * mult
        row = "       %6.4f   " % rc
        for s in range(-2, 7):
            xs = np.roll(x, s)
            yy = np.clip(onepole(xs, rc, reset_mask=~S["active"]), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
            e = yy[m] - y[m]
            row += "%6.3f " % (np.sqrt(np.mean(e ** 2)) / (np.sqrt(np.mean(y[m] ** 2)) + 1e-12))
        print(row + "   (fc=%.2f Hz)" % (1.0 / (2 * np.pi * rc)))


if __name__ == "__main__":
    main()
