# -*- coding: utf-8 -*-
"""s1_flat_sweep.py -- p-gain lens, family (i): a FLAT Kp multiple g (all five knots = round(960 g)), plus two
diagnostics that split Kp's two roles (FF-only: Kp x g with b / g; trim-only: b x g with Kp 960).

Mode-B closed loop (the fork UNCHANGED, r1), every speed band, dist lp AND full, on nominal / light_b / b_lo / F_hi /
J_hi (the identified family's corners + the prior), all candidates + V294 in ONE batch per dist (harness rule 1).
Then the linear blocks per candidate: M_SAFE (rail, sub-rail slope, trim cap, restart, int32), M_LOOP (inner), M_HF,
and the outer loop (M_DRIVE outer) from score(quick=True).  Output: out/s1_flat_sweep.json + a printed table.
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
import v295_harness as H  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


def cands():
    base = H.Cells.v294()
    cs = []
    for g in (1.15, 1.3, 1.5, 1.75, 2.0):
        cs.append(base.replace(kp_y=(int(round(960 * g)),) * 5, name="g%.2f" % g))
    cs.append(base.replace(kp_y=(1440,) * 5, fb_b=378, name="FFonly1.5"))      # trim ~held: K_alpha ~ Kp*b
    cs.append(base.replace(fb_b=850, name="TRIMonly1.5"))                         # FF held, trim x1.5
    return base, cs


def main():
    base, cs = cands()
    plants = ("nominal", "light_b", "b_lo", "F_hi", "J_hi")
    t0 = time.time()
    S = H.sweep_drive(cs, plants=plants, dists=("lp", "full"))
    print("sweep %.0f s" % (time.time() - t0))
    json.dump(H.to_jsonable(S), open(os.path.join(OUT, "s1_flat_sweep_drive.json"), "w"), indent=1)
    names = [c.name for c in cs] + ["V294"]
    keys = ("track_gain", "turn_hold", "straight_delivery", "J_err", "i_share", "cmd_rms", "hard16", "r_mid")
    for dist in ("lp", "full"):
        for p in plants:
            print("\n=== dist %s  plant %s ===" % (dist, p))
            for b in ("0-5", "5-10", "10-15", "15-22", "22+"):
                row = []
                for nm in names:
                    x = S[(dist, nm, p)].get(b)
                    if x is None:
                        continue
                    row.append("%s:tg%.3f th%.3f sd%.2f J%.3f ish%.2f h16 %.2f" % (nm, x["track_gain"], x["turn_hold"],
                               x["straight_delivery"], x["J_err"], x["i_share"], x["hard16"]))
                print(" %-6s " % b + " | ".join(row))
            print("  limit cycle:", {nm: (round(S[(dist, nm, p)]["limit_cycle"]["f"], 2), round(S[(dist, nm, p)]["limit_cycle"]["dB"], 1))
                                     for nm in names})
    # linear blocks
    lin = {}
    for c in cs + [base]:
        q = H.score(c, plants=("nominal", "light_b", "b_lo", "F_hi", "J_hi", "tau6"), quick=True, verbose=False)
        lin[c.name] = q
        s = q["M_SAFE"]
        print("\n%s  rail +%d/%d  subrail %.4f T/wire  trimcap %d T (%.1f%%)  int32 min %.2f  restart %s" % (
            c.name, s["rail_pos"], s["rail_neg"], s["subrail_T_per_wire"], s["trim_cap_T"], s["trim_cap_pct_rail"],
            min(v["margin"] for v in s["int32"].values()), {k: v["peak"] for k, v in s["restart"].items()}))
        h = q["M_HF"]
        print("   |P/x|20Hz %.3f  stress zeta %s" % (h["P_per_x"][4], {("%s@%g" % k): round(v["zeta"], 3) for k, v in h["stress_modes"].items()}))
        worst = {}
        for (nm, v), x in q["M_LOOP"].items():
            worst.setdefault(nm, []).append((x["Ms"], x["GM_min"], x["stable"], x["L13"]))
        print("   inner Ms max / GM min / |L|1-3 max:", {k: (round(max(a[0] for a in w), 2), round(min(a[1] for a in w), 1),
                                                           round(max(a[3] for a in w), 2), all(a[2] is True for a in w)) for k, w in worst.items()})
        for (nm, v, relay), x in q["M_DRIVE"]["outer"].items():
            if relay:
                print("   outer %-8s v %4.1f  Ms %.2f@%.2f  PM %.0f  GM %.2f   |T02| %.3f" % (nm, v, x["Ms"], x["f_Ms"], x["PM_min"], x["GM_min"], x["T02"]))
    json.dump(H.to_jsonable(lin), open(os.path.join(OUT, "s1_flat_sweep_linear.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
