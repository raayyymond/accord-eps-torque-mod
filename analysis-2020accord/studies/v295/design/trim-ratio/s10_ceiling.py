# -*- coding: utf-8 -*-
"""s10_ceiling.py -- trim-ratio lens: the PHYSICS CEILING of "alpha tracks the command" through this loop, and the curve
data for the close-out page (before/after, same axes).

(1) inner |L(f)| of V294 at 0.3 / 0.5 / 1 / 2 / 3 Hz per member and speed, and the HF gain multiple G_req that would give
    |L| = 3 there (|L| is linear in Kp*b at a fixed pole: G_req = 3/|L_V294|), for the 2.03 Hz pole and a 4.9 Hz pole.
    |L| >= 3 is where the acceleration error falls below ~25 % -- a loose definition of "tracks".
(2) the spring corner f_s = sqrt(k / K_alpha) / 2 pi below which the spring k*theta out-pulls the trim's inertia K_alpha*alpha,
    for V294, the pick and the rigorous cal-only maximum (b = b_max at margin 1).
(3) curve dump (JSON) for plotting: trim T/omega (magnitude, damping and inertia parts) 0.1-30 Hz, |T/x| 1-40 Hz,
    closed-form |alpha/cmd| 0.2-8 Hz on nominal and light_b at 8 / 17 m/s, the delivered surface T(idx) (identical by
    construction), for V293 (off), V294 and the pick.
Writes s10_ceiling_out.txt and s10_curves.json.  Analysis only."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
PICK = BASE.replace(name="V295tr_b964", fb_b=964)
V293 = BASE.replace(name="V293 (trim off)", fb_clamp=0)
FAM = H.family()


def main():
    f = np.array([0.3, 0.5, 1.0, 2.0, 3.0])
    print("(1) V294 inner |L| and the HF-gain multiple G_req for |L| = 3 (2.03 Hz pole | 4.9 Hz pole, same HF gain as V294)")
    hi = BASE.replace(fb_a=993)          # 4.9 Hz pole, b 567: HF gain equal to V294 (s1_plane: HFx 0.99)
    for nm in ("nominal", "b_lo", "J_hi", "light_b"):
        for v in (3.1, 8.0, 12.0, 17.0, 26.9):
            p = FAM[nm].at(v)
            L = np.abs(H.loop_frf(BASE, p, f))
            Lh = np.abs(H.loop_frf(hi, p, f))
            print("   %-8s v %4.1f  |L| %s   G_req %s   | 4.9 Hz pole: G_req %s" % (
                nm, v, " ".join("%.2f" % x for x in L), " ".join("%5.1f" % (3 / x) for x in L),
                " ".join("%5.1f" % (3 / x) for x in Lh)))
    print("\n(2) spring corner f_s = sqrt(k/K_alpha)/2pi (Hz) per speed knot, nominal k [6.5, 20.2, 24.3, 79.7, 55.8] T/deg")
    kk = FAM["nominal"].k
    bmax = int(BASE.b_max)
    for c in (BASE, PICK, BASE.replace(name="b_max (margin 1)", fb_b=bmax)):
        t0 = H.trim_T_per_omega(c, np.array([0.05]))[0]
        Ka = t0.imag / (2 * np.pi * 0.05)
        print("   %-18s b %4d  K_alpha %.3f T/(deg/s^2)  f_s %s Hz  (the trim is an ACCELERATION term only between f_s and the"
              " 2.03 Hz pole)" % (c.name, c.fb_b, Ka, " ".join("%.2f" % (math.sqrt(k / Ka) / (2 * math.pi)) for k in kk)))
    # (3) curves
    fr = np.logspace(-1, np.log10(30.0), 200)
    out = dict(f_trim=fr.tolist(), f_x=np.logspace(0, np.log10(40), 120).tolist(), trim={}, Tx={}, alpha={}, surface={})
    fa = np.logspace(np.log10(0.2), np.log10(8.0), 120)
    out["f_alpha"] = fa.tolist()
    for c in (V293, BASE, PICK):
        Tw = H.trim_T_per_omega(c, fr) if c.fb_clamp else np.zeros(len(fr), complex)
        out["trim"][c.name] = dict(mag=np.abs(Tw).tolist(), damping=Tw.real.tolist(),
                                   inertia=(Tw.imag / (2 * np.pi * fr)).tolist(),
                                   phase=np.degrees(np.angle(Tw)).tolist())
        out["Tx"][c.name] = np.abs(H.lane_ctf(c, np.array(out["f_x"]))).tolist() if c.fb_clamp else [0.0] * len(out["f_x"])
        for nm in ("nominal", "light_b"):
            for v in (8.0, 17.0):
                A = H.alpha_per_cmd(c, FAM[nm].at(v), fa)
                out["alpha"]["%s|%s|%.0f" % (c.name, nm, v)] = dict(mag=np.abs(A).tolist(), phase=np.degrees(np.angle(A)).tolist())
        out["surface"][c.name] = [int(t) for t in H.surface(c, range(0, 241, 4))]
    out["surface_idx"] = list(range(0, 241, 4))
    out["V282_P_per_x_20Hz"] = 44.90
    json.dump(out, open(os.path.join(HERE, "s10_curves.json"), "w"))
    s = out["surface"]
    print("\n(3) delivered surface T(idx) identical V293 / V294 / pick: %s ; curves -> s10_curves.json" % (
        s[V293.name] == s[BASE.name] == s[PICK.name]))
    for nm_f in (1.0, 2.0, 2.5, 3.0):
        i = int(np.argmin(abs(fr - nm_f)))
        print("   trim at %.1f Hz: V294 damping %.2f inertia %.3f | pick damping %.2f inertia %.3f" % (
            nm_f, out["trim"][BASE.name]["damping"][i], out["trim"][BASE.name]["inertia"][i],
            out["trim"][PICK.name]["damping"][i], out["trim"][PICK.name]["inertia"][i]))


if __name__ == "__main__":
    main()
