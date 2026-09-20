# -*- coding: utf-8 -*-
"""c2a: diagnostic -- find the frame alignment between the reconstructed stage input and the logged output.
If the reconstruction is right the best shift is 0 frames.  usage: python c2a_align.py <route>"""
import os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "studies", "v282-reference"))
import v282cmp as V  # noqa: E402
from c2_stage import CFG, reconstruct, onepole, DT, MAX_LAT_JERK_UP  # noqa: E402


def main():
    r = sys.argv[1]
    cfg = CFG[r]
    S = V.load(r)
    R = reconstruct(S, cfg)
    m = V.usable(S)
    keep = np.zeros(len(m), bool)
    for a, b in V.runs(m, S["t"], min_s=3.0):
        keep[a + 200:b] = True
    m = m & keep
    jl = R["jerk_log"]
    rc = 1.0 / (2.0 * np.pi, )[0] / cfg["fc"]
    print("route %s  group %s  fc %.1f  n %d   usable frames %d" % (r, cfg["g"], cfg["fc"], int(np.median(R["n"])), m.sum()))
    print("  shift  rms(F_j(raw shifted) - jerk_log)/rms(jerk_log)   corr")
    best = None
    for s in range(-8, 9):
        raw_s = np.roll(R["raw"], s)
        y = np.clip(onepole(raw_s, rc, reset_mask=~S["active"]), -MAX_LAT_JERK_UP, MAX_LAT_JERK_UP)
        e = y[m] - jl[m]
        v = np.sqrt(np.mean(e ** 2)) / (np.sqrt(np.mean(jl[m] ** 2)) + 1e-12)
        c = float(np.corrcoef(y[m], jl[m])[0, 1])
        print("   %+3d    %8.4f                              %7.5f" % (s, v, c))
        if best is None or v < best[1]:
            best = (s, v)
    print("  best shift %+d  (positive = the logged jerk is AHEAD of my reconstruction)" % best[0])

    # and the same for the whole setpoint
    print()
    print("  shift  rms(sp_rec shifted - sp_log)/rms(sp_log)")
    for s in range(-6, 7):
        e = np.roll(R["sp_rec"], s)[m] - R["sp_log"][m]
        print("   %+3d    %8.5f" % (s, np.sqrt(np.mean(e ** 2)) / np.sqrt(np.mean(R["sp_log"][m] ** 2))))

    # is `expected` really u(t-n)?  scan n directly against a direct reconstruction of sp_pre from the log
    print()
    print("  n scan: rms( (expected_n + jerk_log*ld) - sp_pre_implied )   where sp_pre_implied is the logged")
    print("          setpoint itself on a route with NO ref filter (rf=%.2f)" % cfg["rf"])
    v2 = np.maximum(np.nan_to_num(S["v"]) ** 2, 1e-9)
    curv = np.nan_to_num(S["model"]) / v2
    ld = np.nan_to_num(S["lat_delay"], nan=0.2)
    for n in range(int(np.median(R["n"])) - 4, int(np.median(R["n"])) + 5):
        idx = np.maximum(np.arange(len(curv)) - n, 0)
        exp = curv[idx] * v2
        sp = exp + jl * ld
        e = sp[m] - R["sp_log"][m]
        print("   n=%2d   %8.5f" % (n, np.sqrt(np.mean(e ** 2)) / np.sqrt(np.mean(R["sp_log"][m] ** 2))))


if __name__ == "__main__":
    main()
