# -*- coding: utf-8 -*-
"""rj16_hf_modes.py -- lens robust-joint: where does the trim's opposing torque turn ANTI-damping (phase of T/omega past
-90 deg), and does the pick de-damp a hypothetical lightly damped mode ANYWHERE in 8-60 Hz?  Extra stress members beyond
the harness's 13/20 Hz: two-mass modes at 8..60 Hz (zeta 0.05 and 0.02, wheel share r2 0.2 and 0.5), closed-loop exact
1 kHz poles (H.stress_damping), V294 vs the pick vs open (C = 0) vs V282 (the flown grinder).  ANALYSIS ONLY."""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rj_cands as RC
from rj_lin import H

base = RC.base(); pick = base.replace(fb_b=1106, name="pick"); v282 = H.Cells.v282()
f = np.array([2, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60.0])
for nm, c in (("V294", base), ("pick", pick), ("V282", v282)):
    Tw = H.trim_T_per_omega(c, f)
    print("%-5s T/omega (T per deg/s): " % nm + "  ".join("%g Hz %.2f@%+.0f" % (ff, abs(t), np.degrees(np.angle(t))) for ff, t in zip(f, Tw)))
fam = H.family()
nom = fam["nominal"]
worst = 1e9
for f2 in (8, 10, 13, 16, 20, 25, 30, 35, 40, 50, 60):
    for z2, r2 in ((0.05, 0.2), (0.02, 0.5)):
        mem = nom.with_mode20(f2=float(f2), zeta2=z2, r2=r2)
        line = []
        for v in (5.0, 12.0, 25.0):
            p = mem.at(v)
            band = (0.6 * f2, 1.6 * f2)
            (fo, zo), _ = H.stress_damping(base.replace(fb_clamp=0), p, band)
            (fb, zb), _ = H.stress_damping(base, p, band)
            (fp, zp), rp = H.stress_damping(pick, p, band)
            (f8, z8), r8 = H.stress_damping(v282, p, band)
            worst = min(worst, zp / min(zb, zo))
            line.append("v%-4g open %.3f V294 %.3f pick %.3f (x%.2f) V282 %.3f%s" % (v, zo, zb, zp, zp / min(zb, zo), z8, " UNSTABLE" if r8 >= 1 else ""))
        print("mode %2d Hz z %.2f r2 %.1f: %s" % (f2, z2, r2, " | ".join(line)))
print("worst pick zeta / min(V294, open) over 8-60 Hz modes: %.3f" % worst)
