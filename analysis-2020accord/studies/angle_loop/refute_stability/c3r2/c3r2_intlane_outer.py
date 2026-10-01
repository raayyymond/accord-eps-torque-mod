# -*- coding: utf-8 -*-
"""c3r2_intlane_outer.py -- the integer lane with the fork outer-integral stand-in (tau_o 1.0 s, 100 Hz, 60 ms round trip)
at the curve operating points the exact model flags; frictionless and with the identified friction.  -> intlane_outer_out.txt"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import c3r2_model as M
import c3r2_intlane as IL
CASES = [
    (M.C3R2P, "b_hi", 11.75, 2.5, (1.155, 1.0), 10, 1.0, "P b_hi (tier A) tau_o 1: exact ring 0.33 Hz z 0.092"),
    (M.C3R2P, "b_hi", 11.75, 2.5, (1.155, 1.0), 10, None, "P b_hi same point, NO fork (control)"),
    (M.C3R2P, "nominal", 11.75, 2.5, (0.83, 1.0), 0, 1.0, "P nominal tau_o 1: exact ring 0.37 Hz z 0.17"),
    (M.C3R2P, "J1.0", 11.75, 2.5, (1.155, 1.0), 0, 1.0, "P J1.0 tau_o 1: exact ring 0.44 Hz z 0.16"),
    (M.C3R2P, "b_lo*ms_free", 11.9, 2.5, (0.83, 1.0), 10, 1.0, "P b_lo*ms_free tau_o 1: exact rho 1.0036"),
    (M.C3R2P, "ms_free", 11.9, 2.5, (0.83, 1.0), 10, 1.0, "P ms_free (tier A) tau_o 1: exact rho 1.0010"),
    (M.C3R2P, "b_lo*ms_free", 11.9, 2.5, (0.83, 1.0), 10, 2.0, "P b_lo*ms_free tau_o 2: exact rho 1.0013"),
]
out = []
for des, mem, v, a, fr, e, tau, lab in CASES:
    for fric in (False, True):
        th, T, I, th_op, frz = IL.simulate(des, mem, v, a, fr, e, dur=45.0, fric=fric, tau_o=tau)
        f, z, amax, alast = IL.ring_metrics(th, 7.1, 45.0)
        w1 = th[10000:15000]; w2 = th[25000:30000]; w3 = th[40000:45000]
        out.append(f"{lab:52s} fric {int(fric)}: th_op {th_op:5.1f} ; ring {f:.2f} Hz zeta~{z:+.3f} ; p-p 10-15 s {np.ptp(w1):.2f} / "
                   f"25-30 s {np.ptp(w2):.2f} / 40-45 s {np.ptp(w3):.2f} deg ; I end {I[-1]:.0f} S ; freeze duty {frz:.2f}")
        print(out[-1], flush=True)
(M.OUT / "intlane_outer_out.txt").write_text("\n".join(out), encoding="utf-8")
