# -*- coding: utf-8 -*-
"""S6 -- the PHASE COST of the inner-rate-loop suppressor, per band, from the band-averaged measured G.

The suppressor multiplies the plant the OUTER loop sees by  q(f) = (1 - g0*F*G)/(1 - g1*F*G).
Its magnitude is the attenuation; its ARGUMENT is the phase it adds at the outer loop's crossover.
Also: the inner loop's own return ratio |g1*F*G| and the margin |1 - g1*F*G| per band, which is the
GATE-2 question (magnitude AND phase, in every loop the signal is in).

usage: python s6_phasecost.py > out/S6-PHASECOST.txt
"""
import json
import numpy as np
import suplib as S

D = json.load(open(S.OUT / "s3_plant.json"))
BANDS = [tuple(b) for b in D["bands"]]
print("q(f) = (1-g0 F G)/(1-g1 F G) from the BAND-AVERAGED measured G (magnitude per bin, phase by")
print("unit-phasor mean).  |q| < 1 = attenuation; arg q = the phase the suppressor ADDS.")
print("g1 = 0.003 with the 12/v taper REMOVED (the strongest dose in the class).\n")
for g1t, taper in ((0.003, True), (0.003, False), (0.002, False)):
    print("=" * 130)
    print(f"  AccordRateLoopGain {g1t}{'' if taper else ', taper removed (code change)'}")
    print("=" * 130)
    print(f"  {'route':10s} {'bin':6s} {'v':>5s} {'g0e':>8s} {'g1e':>8s} " +
          "".join(f"{f'{a}-{b}':>16s}" for a, b in BANDS))
    print(f"  {'':10s} {'':6s} {'':5s} {'':8s} {'':8s} " + "".join(f"{'|q|  argq |gFG|':>16s}" for _ in BANDS))
    for rk, row in D["res"].items():
        for tag, b in row["bins"].items():
            g0e, v = b["g0e"], b["v"]
            g1e = S.rate_loop_gain(v, g1t) if taper else g1t
            cells = []
            for f1, f2 in BANDS:
                k = f"{f1}-{f2}"
                if k not in b["bands"]:
                    cells.append(" " * 16); continue
                mg, ph = b["bands"][k]["G"]
                G = mg * np.exp(1j * np.radians(ph))
                F = S.fof_H(0.5 * (f1 + f2), S.RATE_LOOP_RC)
                q = (1 - g0e * F * G) / (1 - g1e * F * G)
                cells.append(f"{abs(q):6.2f}{np.degrees(np.angle(q)):6.0f}{abs(g1e*F*G):5.1f}")
            print(f"  {rk[:10]:10s} {tag:6s} {v:5.1f} {g0e:8.5f} {g1e:8.5f} " + "".join(cells))
    print()
