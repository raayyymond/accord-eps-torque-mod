# -*- coding: utf-8 -*-
r"""e2_data_hold.py -- does the ANGLE-REFERENCED I BOUND (ARB) cap a torque the car actually needs?  On r71b (V294,
torque mode: in a STEADY hands-off hold the lane torque IS the hold load at that wheel angle -- spring + road crown +
crosswind + friction residue), read the CAN-427 tap (gp-0x6b38; frame = (sign<<9) | (|T|>>3), polarity +sign(cmd),
v293_flight_read.tap_quantise) at steady holds (|rate| < 2 deg/s for >= 0.5 s, hands not pressed, lateral engaged)
and compare |T| with the bound 0.160 * ((|angle_counts| << sh) + B) T for the ARB parameters.  ANALYSIS ONLY.
The I is not the whole hold (P carries Kp_eff x error); counting |T| against the I's bound is CONSERVATIVE (it
over-counts the I's need)."""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
KIT = HERE.parents[4]
d = np.load(KIT / "analysis-2020accord" / "_scratch" / "cache" / "tau" / "r71b_v294_ident.npz")
TPS = 0.160


def main():
    f = ((d["b0"].astype(int) << 8) | d["b1"].astype(int)) & 0x3FF
    T = np.where(f >> 9, -1, 1) * ((f & 0x1FF) << 3)
    tt = d["t1ab"]
    cmd = np.interp(tt, d["te4"], d["cmd"])
    L = [f"tap polarity check: sign(T) == sign(cmd) on {np.mean(np.sign(T[np.abs(T) > 40]) == np.sign(cmd[np.abs(T) > 40])):.3f} "
         f"of |T| > 40 frames (expected +sign(cmd))"]
    t, v, sa, sr, sp = d["t_cst"], d["vego"], d["sa_deg"], d["sr_deg"], d["spress"]
    lat = np.interp(t, d["t_cc"], d["lat_active"]) > 0.5
    k = 50
    still = np.convolve((np.abs(sr) < 2.0).astype(float), np.ones(k) / k, "same") > 0.999
    m = lat & (sp < 0.5) & still
    Ti = np.interp(t, tt, T)
    out = {}
    for lo, hi in ((3, 8), (8, 15), (15, 22), (22, 40)):
        mm = m & (v >= lo) & (v < hi)
        th_c = np.abs(sa[mm]) * 10.0
        aT = np.abs(Ti[mm])
        row = [f"steady holds {lo:2d}-{hi:2d} m/s n {int(mm.sum()):6d} (|angle| p50 {np.percentile(np.abs(sa[mm]), 50):.1f} "
               f"p95 {np.percentile(np.abs(sa[mm]), 95):.1f}): |T| p50 {np.percentile(aT, 50):.0f} p95 "
               f"{np.percentile(aT, 95):.0f} p99 {np.percentile(aT, 99):.0f} max {aT.max():.0f} T"]
        for sh, B in ((6, 1250), (6, 625), (5, 1250)):
            bound = TPS * (th_c * (1 << sh) + B)
            ex = aT > bound
            row.append(f"   ARB sh {sh} B {B}: frames with |T| > bound {ex.mean():.4f}; worst excess "
                       f"{(aT - bound).max():+.0f} T")
            out[f"{lo}-{hi}:{sh}:{B}"] = float(ex.mean())
        L += row
    txt = "\n".join(L)
    print(txt)
    (HERE / "e2_data_hold_out.txt").write_text(txt + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
