# -*- coding: utf-8 -*-
"""s6_replay_r71b.py -- adversary `stability`, attack surface (d): the NONLINEAR byte-exact open-loop replay of the whole
r71b drive (1.02 M ticks) through MY OWN integer lane (s0 MyLane == golden model), V294 and A1017 side by side, on the
drive's own 0xE4 demand (idx, sign, taper m per frame -- the plant study's cache) and 1 kHz rate (x1k).
  * bit-exactness of my V294 march against plib's T1k_live (the march that matched the 427 tap to 3.64 counts rms);
  * fb clamp C binds, P-clamp binds (engaged), max |r26|, max |a*s| (int32), per lane;
  * the trim torque (T_live - T_null) on DRIVER-TORQUE frames (hands-on engaged: |bar| >= 400 or steeringPressed):
    does A1017 add resistance to the driver, after the firmware's own driver-torque taper?
  * a synthetic fast driver steer (0 -> 90 deg, peak 500 deg/s, ~3000 deg/s^2) at taper 254 / 178 / 76.
Not a closed loop: the wheel motion is the drive's (V294's).  It sizes the lane's reaction to the SAME motion.
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant"))
import plib as P  # noqa: E402
from s0_lane_spotcheck import MyLane, lerp  # noqa: E402

MAP_X = [0, 12, 20, 24, 32, 64, 96, 128, 160, 240]
MAP_Y = [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032]
MAPT = np.array([lerp(MAP_X, MAP_Y, i) for i in range(241)], np.int64)


def main():
    lines = []
    pr = lambda *a: (print(*a, flush=True), lines.append(" ".join(str(x) for x in a)))  # noqa: E731
    d = P.load()
    n100 = len(d["idx"])
    sp100 = (d["sgn"].astype(np.int64) * MAPT[d["idx"].astype(np.int64)])
    m100 = d["m"].astype(np.int64)
    x1k = np.clip(np.round(d["x1k"]), -12000, 12000).astype(np.int64)
    N = n100 * 10
    t0 = time.time()
    # lanes: V294 live, A1017 live, V294 null (C = 0), A1017 null is identical to V294 null (FF unchanged)
    L = MyLane(3, np.array([1011, 1017, 1011]), 567, C=np.array([1024, 1024, 0]))
    T = np.zeros((3, N), np.int32)
    R = np.zeros((2, N), np.int32)
    PB = np.zeros((2, N), bool)
    for i in range(N):
        k = i // 10
        xi = np.full(3, x1k[i])
        Pb_before = L.n_Pbind.copy()
        Ti, ri = L.tick(xi, np.full(3, sp100[k]), np.full(3, m100[k]))
        T[:, i] = Ti
        R[:, i] = ri[:2]
        PB[:, i] = (L.n_Pbind - Pb_before)[:2] > 0
    pr("replay %d ticks in %.0f s" % (N, time.time() - t0))
    sg = d["sg"]
    Tv = sg * T[0]
    mism = int(np.sum(Tv != d["T1k_live"]))
    mismn = int(np.sum(sg * T[2] != d["T1k_null"]))
    pr("bit-exactness vs plib march: V294 live %d mismatching ticks of %d ; null %d" % (mism, N, mismn))
    eng1k = np.repeat(d["eng"][:n100], 10)
    ho1k = np.repeat(d["ho"][:n100], 10)
    hon = np.repeat((d["eng"] & ~d["ho"])[:n100], 10)            # engaged, hands-on (driver torque / pressed)
    for j, nm in enumerate(("V294", "A1017")):
        pr("%-6s max|r26| %d (engaged %d) ; fb clamp binds: all %d engaged %d ; P binds engaged %d (hands-off %d) ; "
           "max|a*s| %.3e (margin %.2f)" % (nm, np.abs(R[j]).max(), np.abs(R[j][eng1k]).max(), L.n_Cbind[j],
                                           int(np.sum((np.abs(R[j]) >= 1024) & eng1k)), int(np.sum(PB[j] & eng1k)),
                                           int(np.sum(PB[j] & ho1k)), L.max_as[j], 2 ** 31 / L.max_as[j]))
    trimV = (T[0] - T[2]).astype(float)
    trimA = (T[1] - T[2]).astype(float)
    for lab, msk in (("hands-off engaged", ho1k), ("hands-on engaged (driver torque)", hon)):
        if msk.sum() == 0:
            continue
        pr("trim |T_live - T_null| on %s ticks (%d s): V294 rms %.1f p99 %.0f max %.0f | A1017 rms %.1f p99 %.0f max %.0f" % (
            lab, msk.sum() / 1000, np.sqrt(np.mean(trimV[msk] ** 2)), np.percentile(np.abs(trimV[msk]), 99), np.abs(trimV[msk]).max(),
            np.sqrt(np.mean(trimA[msk] ** 2)), np.percentile(np.abs(trimA[msk]), 99), np.abs(trimA[msk]).max()))
    # driver-torque episodes: the sign of the trim relative to the wheel acceleration and the driver's bar torque
    bar1k = np.repeat(d["bar"][:n100], 10)
    om1k = np.repeat(d["om"][:n100], 10)
    al100 = d["al"]
    al1k = np.repeat(al100[:n100], 10)
    big = hon & (np.abs(al1k) > 300)
    if big.sum():
        pr("hands-on ticks with |alpha| > 300 deg/s^2: %d ; trim opposing the driver's acceleration (sign(T) == sign(alpha) in "
           "this frame convention? mean T*alpha sign): V294 %.2f A1017 %.2f ; |trim| p95 V294 %.0f A1017 %.0f T" % (
               big.sum(), np.mean(np.sign(trimV[big]) == np.sign(al1k[big])), np.mean(np.sign(trimA[big]) == np.sign(al1k[big])),
               np.percentile(np.abs(trimV[big]), 95), np.percentile(np.abs(trimA[big]), 95)))
    # synthetic fast driver steer: raised-cosine angle ramp 0 -> 90 deg in 0.3 s, hold, back
    pr("\nsynthetic driver steer (lane only, sp 0): angle 0 -> 90 deg in 0.30 s (peak 471 deg/s, peak ~4900 deg/s^2), "
       "hold 0.7 s, back")
    t = np.arange(3000) * 1e-3
    th = np.where(t < 0.3, 45 * (1 - np.cos(np.pi * t / 0.3)), 90.0)
    th = np.where(t > 1.0, 90 - np.where(t < 1.3, 45 * (1 - np.cos(np.pi * (t - 1.0) / 0.3)), 90.0), th)
    th = np.r_[np.zeros(3), th]
    for m in (254, 178, 76):
        Lx = MyLane(2, np.array([1011, 1017]), 567)
        out = np.zeros((2, 3000))
        for i in range(3000):
            x = int(np.round(8 * (th[i + 3] - th[i]) / 3e-3))
            Ti, _ = Lx.tick(np.full(2, -x), np.zeros(2, np.int64), np.full(2, m))
            out[:, i] = Ti
        pr("  taper m %3d: peak |T| V294 %.0f A1017 %.0f ; impulse integral(|T|) dt V294 %.1f A1017 %.1f T*s ; fb clamp binds "
           "V294 %d A1017 %d" % (m, np.abs(out[0]).max(), np.abs(out[1]).max(), np.abs(out[0]).sum() * 1e-3, np.abs(out[1]).sum() * 1e-3,
                                 Lx.n_Cbind[0], Lx.n_Cbind[1]))
    open(os.path.join(HERE, "s6_replay_r71b_out.txt"), "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
