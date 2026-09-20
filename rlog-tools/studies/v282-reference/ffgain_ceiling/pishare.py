# -*- coding: utf-8 -*-
"""Adversarial hole check: my totals hold P and I at their logged values.  How much of the command at
the railed frames IS P and I?  If P dominates, the open-loop total is a weak upper bound; if the
feedforward dominates, it is nearly exact.  ANALYSIS ONLY."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import ffrecon as F, v282cmp as C
from sweep import route_frames, FS
from validate import load
routes = [(rk, c) for rk, c in F.ROUTECFG.items() if c["ff_live"] and (C.CACHE / f"{rk}.npz").exists()]
print(f"{'route':6s} {'band':>6s} {'n rail':>7s} | {'mean |f|/LAF':>13s} {'|p|/LAF':>9s} {'|i|/LAF':>9s} "
      f"| {'f share':>8s} {'p share':>8s} {'i share':>8s} | {'sign(move)==sign(u)':>20s}")
for rk, cfg in routes:
    S = load(rk); D = route_frames(rk, cfg); laf = cfg["laf"]
    for lo, hi, bn in ((2.0, 8.0, "2-8"),):
        bm = D["mask"] & (D["v"] >= lo) & (D["v"] < hi)
        rail = bm & (np.abs(D["u0"]) >= 1.0)
        if rail.sum() < 3:
            print(f"{cfg['tag']:6s} {bn:>6s} {int(rail.sum()):7d} |   (too few)")
            continue
        f_, p_, i_ = S["f"][rail] / laf, S["p"][rail] / laf, S["i"][rail] / laf
        u = D["u0"][rail]
        sg = float(np.mean(np.sign(D["mv0"][rail] * -1.0) == np.sign(u)))
        print(f"{cfg['tag']:6s} {bn:>6s} {int(rail.sum()):7d} | {np.abs(f_).mean():13.3f} "
              f"{np.abs(p_).mean():9.3f} {np.abs(i_).mean():9.3f} | "
              f"{np.mean(f_*np.sign(u)):8.3f} {np.mean(p_*np.sign(u)):8.3f} {np.mean(i_*np.sign(u)):8.3f} "
              f"| {100*sg:19.0f}%")
    del D, S
