# -*- coding: utf-8 -*-
"""c3r2_retw.py -- Re(T/w) 5-25 Hz (T counts per deg/s at the motor; > 0 damps) worst over 1..35 m/s, vs V294/V295, at
kappa 1 / 0.866 (physical) / 0.83 / 1.155 and hold ages 1-10 / 0-9 / 11-20; and |L(20 Hz)| / |L_V295(20 Hz)| on every
gated member, speed and frame (the goal's '20 Hz gain <= V295').  -> retw_out.txt"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M  # noqa: E402

f = np.array([5, 7, 10, 13, 15, 17, 20, 25.0])
V = [x / 4 for x in range(4, 141)]
out = ["Re(T/w) worst (min) over v 1..35 m/s, T counts per deg/s; > 0 damps.  ratio = C3 / V295 where both < 0"]
KAPS = ((1.0, "k1"), (1 / 1.155, "k.866"), (0.83, "k.83"), (1.155, "k1.155"))
for e, en in ((0, "ages 1-10"), (-1, "ages 0-9"), (10, "ages 11-20")):
    for kap, kn in KAPS:
        K = M.Kout(f, 2)
        Cth, Cw, _ = M.controller(M.V295D, 20.0, f, e, kap)
        rv = (K * (Cth / (2j * np.pi * f) + Cw)).real
        out.append(f"-- {en} {kn}: V295 " + " ".join(f"{x:+.2f}" for x in rv))
        for des in (M.C3R2P, M.C3R2F):
            R = np.array([(K * (Cth_ / (2j * np.pi * f) + Cw_)).real
                          for Cth_, Cw_, _ in (M.controller(des, v, f, e, kap) for v in V)])
            w = R.min(axis=0)
            rat = np.where((w < 0) & (rv < 0), w / rv, np.nan)
            out.append(f"   {des.name:10s} " + " ".join(f"{x:+.2f}" for x in w) + "   ratio " +
                       " ".join("  -  " if np.isnan(x) else f"{x:.2f}x" for x in rat))
out.append("Hz:            " + " ".join(f"{x:5.0f}" for x in f))

# L20 ratio over the gated set (theta = 0 plants; L20 does not depend on the spring at 20 Hz to first order)
out.append("")
out.append("|L(20)| / |L_V295(20)| (same plant, same kappa, same e): max over gated members, v 1..35, frames, e 0/-1/10")
FR = (("nom", 1.0, 1.0), ("FA.83", 0.83, 1.0), ("FA1.155", 1.155, 1.0), ("FB.83", 0.83, 1 / 1.155),
      ("FB1.155", 1.155, 1 / 1.155), ("FAc", 1 / 1.155, 1.0))
f20 = np.array([20.0])
for des in (M.C3R2P, M.C3R2F):
    worst = (0, None)
    for mem in M.SINGLE + M.COMBINED + M.MSF2:
        for v in V[::2]:
            pl, ea = M.member(mem, v)
            for fn, kap, jb in FR:
                ch = M.plant_frf(pl, f20, jb)
                for e in (-1, 0, 10):
                    L, _ = M.loop_L(des, pl, v, f=f20, e=e + ea, kappa=kap, jb=jb, chans=ch)
                    LV, _ = M.loop_L(M.V295D, pl, v, f=f20, e=e + ea, kappa=kap, jb=jb, chans=ch)
                    r = abs(L[0]) / abs(LV[0])
                    if r > worst[0]:
                        worst = (r, (mem, v, fn, e))
    out.append(f"   {des.name}: max L20/L20_V295 = {worst[0]:.3f} at {worst[1]}")
txt = "\n".join(out)
(M.OUT / "retw_out.txt").write_text(txt, encoding="utf-8")
print(txt)
