# -*- coding: utf-8 -*-
"""c3r2_intlane_straight.py -- straight-line (theta = 0) integer lane with the identified friction, with and without the fork
outer integral (tau_o 1 s): does the two-integrator + Coulomb loop hunt?  A 60 ms 120 T pulse at 7 s.  -> intlane_straight_out.txt"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
import c3r2_intlane as IL
out = []
for mem, v, fr in (("nominal", 11.75, (1.0, 1.0)), ("nominal", 20.0, (1.0, 1.0)), ("b_hi", 11.75, (1.155, 1.0)),
                   ("J1.0", 11.75, (1.0, 1.0)), ("nominal", 8.0, (1.0, 1.0))):
    for tau in (None, 1.0):
        th, T, I, th_op, frz = IL.simulate(M.C3R2P, mem, v, 0.0, fr, 0, dur=40.0, fric=True, tau_o=tau)
        f, z, amax, alast = IL.ring_metrics(th, 7.1, 40.0)
        out.append(f"P {mem:8s} @{v:5.2f} tau_o {tau}: fric 1 straight ; ring {f:.2f} Hz ; p-p 10-15 s {np.ptp(th[10000:15000]):.2f} / "
                   f"30-40 s {np.ptp(th[30000:40000]):.2f} deg ; |mean| 30-40 s {abs(th[30000:40000].mean()):.2f} deg")
        print(out[-1], flush=True)
(M.OUT / "intlane_straight_out.txt").write_text("\n".join(out), encoding="utf-8")
