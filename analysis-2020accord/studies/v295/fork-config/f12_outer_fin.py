# -*- coding: utf-8 -*-
"""f12: G1-G3 (outer-loop linear margins with the relay slope, the light_b 17-27 m/s comparison, the describing-function
relay sweep) for the finalists, printed per member x speed; plus the static loop-gain bookkeeping by speed
(P, relay, Ki_eff in torque per m/s^2 of error) against r1."""
import sys, json
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/fork-config")
import numpy as np
import fc_lib as F
import f2_outer as O
H = F.H

spec = json.load(open("out/fin_spec.json"))
FIN = [F.Fork(**d) for d in spec["forks"]]
K295, K294 = O.K_table(O.c295), O.K_table(O.c294)
r294, _ = O.screen(K294, F.R1)
r295, _ = O.screen(K295, F.R1)
ref_gm = {k: min(r294[k][1], r295[k][1]) for k in r295}
ref_lb = {v: (r294[("light_b", v)][0], r294[("light_b", v)][1]) for v in O.SPEEDS}
out = {}
for fk in [F.R1] + FIN:
    res, fails = O.screen(K295, fk, ref_gm, ref_lb)
    out[fk.name] = dict(fails=fails, res={"|".join(map(str, k)): v for k, v in res.items()})
    print("\n%s  %s   G1-G3: %s" % (fk.name, fk.short(), "PASS" if not fails else "FAIL " + "; ".join(fails[:6])))
    for m in O.MEMBERS:
        print("   %-8s " % m + " ".join("%4.1f:%4.2f/%5.1f/%3.0f" % (v, *res[(m, v)][:3]) for v in O.SPEEDS))
    print("   per m/s^2 of error, torque units:  " + "  ".join(
        "v%.0f P %.3f rl %.3f Ki %.3f" % (v, F.p_gain_torque(fk, v), F.relay_slope_torque(fk, v),
                                          float(fk.ki_at(v)) * (1 + F.lsf_of(v) / fk.kp) / fk.laf) for v in (3.1, 5, 8, 12, 17, 27)))
    # DF: the smallest relay multiplier that destabilises, per member, worst over speeds (inf = none up to x8)
    worst = []
    for m in O.MEMBERS:
        for v in O.SPEEDS:
            for mult in (2.0, 3.0, 4.0, 6.0, 8.0):
                Ms_, GM_, PM_, _ = O.mg(O.L_of(K295[(m, v)], fk, v, mult))
                if not (GM_ > 1.0 and PM_ > 0.0):
                    worst.append((mult, m, v))
                    break
    print("   DF: first destabilising relay multiple (x the flown slope):",
          sorted(worst)[:4] if worst else "none up to x8 at any member/speed")
json.dump(out, open("out/f12_outer_fin.json", "w"), indent=1)
