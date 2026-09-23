"""PM change measured AT THE FORK'S (V293-plant) crossover frequency, across the same 1008-case grid."""
import math
import numpy as np
from rp5_outer_loop import L_outer, margins, HOLD_V_BP, HOLD_K_V, G_BP, G_V, J0
LEVEL_BP, LEVEL_V = [12.5, 17.5], [1.15, 1.45]
res = []
for v in (3, 5, 8, 12.5, 19, 26, 32):
    for world in ("light", "vlight", "ident", "free0.0009"):
        for kl in ("map", "lev"):
            for jm in (0.5, 1.0, 2.0):
                for tau in (0.015, 0.025, 0.040):
                    for fric in (0.011, 0.0):
                        k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)) * (float(np.interp(v, LEVEL_BP, LEVEL_V)) if kl == "lev" and v >= 12.5 else 1)
                        b = {"light": 6e-4, "vlight": 3e-4, "ident": 1 / float(np.interp(v, G_BP, G_V)), "free0.0009": 9e-4}[world]
                        kw = dict(J=J0 * jm, tau=tau, fric=fric)
                        p3, _, _, _ = margins(v, False, b, k, **kw)
                        if not p3: continue
                        fc = p3[0][0]
                        L3 = L_outer(np.array([fc]), v, False, b, k, **kw)[0]; L4 = L_outer(np.array([fc]), v, True, b, k, **kw)[0]
                        dph = math.degrees(np.angle(L4 / L3)); dmag = abs(L4) / abs(L3)
                        res.append((dph, dmag, v, world, kl, jm, tau, fric, fc, p3[0][1]))
res.sort()
print("largest phase LOSSES at the V293 crossover (deg), |L| ratio, case, fc, V293 PM there:")
for r in res[:10]:
    print(f"  {r[0]:+6.2f} deg  |L|x{r[1]:.3f}  v {r[2]} {r[3]} {r[4]} Jx{r[5]} tau {r[6]*1e3:.0f} fric {r[7]}  fc {r[8]:.3f} Hz  PM293 {r[9]:+.0f}")
print(f"cases with a phase loss > 10 deg at the fork's crossover: {sum(1 for r in res if r[0] < -10)} / {len(res)}; > 5 deg: {sum(1 for r in res if r[0] < -5)}")
print("largest phase GAINS:", [(round(r[0],1), r[2], r[3]) for r in res[-5:]])
