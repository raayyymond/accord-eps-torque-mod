# -*- coding: utf-8 -*-
"""CLAUSE (a) -- FREQUENCY, BOTH POSITIVES.  Scored before anything is interpreted.

(a) r71's object within +/-25% of 2.34 Hz  -> [1.755, 2.925] Hz
    r73's object within +/-25% of the 4.0-6.5 Hz band -> [3.000, 8.125] Hz
    each from ITS OWN flown parameters, on ITS OWN identified plant, swept over b and the delay bracket.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g2_lib as G  # noqa: E402

FG = np.arange(0.5, 12.0005, 0.002)
DBR = [0.055, 0.065, 0.075]
BSW = [1.0e-4, 2.0e-4, 4.0e-4, 6.0e-4, 1.0e-3, 2.0e-3, 4.0e-3, 7.0e-3]   # 70x, brackets the fork's 6e-4
A_R71 = (2.34 * 0.75, 2.34 * 1.25)
A_R73 = (4.0 * 0.75, 6.5 * 1.25)


def main():
    C = G.read_controllers()
    P = G.load_plants("22+")
    out = {}

    print("=" * 126)
    print("GATE #2 -- CLAUSE (a) FREQUENCY.   ONE NEW TERM: Kj*jerk inside the relay argument, Kj = 0.22 FROM SOURCE")
    print("   latcontrol_torque.py:40   JERK_GAIN = 0.22")
    print("   latcontrol_torque.py:553  ff += friction_scale * get_friction(error_with_lsf + JERK_GAIN * friction_jerk, ...)")
    print("   latcontrol_torque.py:38   LP_FILTER_CUTOFF_HZ = 1.2   ->  lead = fric*N*0.22*s/(1+s*0.13263)")
    print(f"   r71 must land in [{A_R71[0]:.3f},{A_R71[1]:.3f}] Hz ;  r73 must land in [{A_R73[0]:.3f},{A_R73[1]:.3f}] Hz")
    print("=" * 126)

    for tag, rt in (("r71", G.R71), ("r73", G.R73)):
        pl, p = P[rt], C[rt]
        print(f"\n--- {tag}  ({G.LBL[rt]})   v={pl['v']:.1f} m/s  alpha={pl['alpha']:.3f}  c={pl['c']:.4f}  "
              f"A={pl['A']:.3f}  kp={p['kp']} LAF={p['laf']} ki={p['ki']} fric={p['fric']:.4f} "
              f"notchQ={p['notch']} rate={p['rate']} rateRC={p['rate_rc']}")
        print(f"      relay branch fric*N = {p['fric']*G.df_ramp(pl['A']):.4f}   "
              f"PID branch kp/LAF = {p['kp']/p['laf']:.4f}   "
              f"relay share = {p['fric']*G.df_ramp(pl['A'])/(p['fric']*G.df_ramp(pl['A'])+p['kp']/p['laf']):.2%}")
        print(f"   {'b':>8s} | " + "  ".join(f"{'D=' + str(int(d*1000)) + 'ms':>26s}" for d in DBR))
        print(f"   {'':>8s} | " + "  ".join(f"{'gate#1 (no jerk)':>12s}{'gate#2 (jerk)':>14s}" for _ in DBR))
        rows = []
        for b in BSW:
            line = f"   {b:8.5f} | "
            rec = {"b": b}
            for D in DBR:
                r0, f0 = G.first_crossing(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], p, pl["A"], D, b, jerk=False))
                r1, f1 = G.first_crossing(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], p, pl["A"], D, b, jerk=True))
                line += f"{f0:7.2f}Hz{r0:5.2f}{f1:9.2f}Hz{r1:5.2f}  "
                rec[f"D{int(D*1000)}"] = dict(f_g1=f0, R_g1=r0, f_g2=f1, R_g2=r1)
            rows.append(rec)
            print(line)
        out[tag] = rows

        # every crossing, at the fork's own b and the mid delay
        cr = G.crossings(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], p, pl["A"], 0.065, 6e-4, jerk=True))
        cr0 = G.crossings(FG, G.L_of(FG, pl["v"], pl["alpha"], pl["c"], p, pl["A"], 0.065, 6e-4, jerk=False))
        print(f"   ALL -180 crossings 1-8 Hz at b=6e-4, D=65 ms:")
        print(f"      gate#1: " + "  ".join(f"{f:.2f} Hz |L|={r:.2f}" for r, f in cr0))
        print(f"      gate#2: " + "  ".join(f"{f:.2f} Hz |L|={r:.2f}" for r, f in cr))

    # ---------- the verdict on (a) ----------
    print("\n" + "=" * 126)
    print("CLAUSE (a) SCORING -- first -180 crossing in 1-8 Hz (the crossing gate #1 scored; the modelling")
    print("choice is stated and held fixed).  A cell PASSES only if it lands inside the route's window.")
    print("=" * 126)
    tot = {"r71": [0, 0], "r73": [0, 0]}
    for tag, win in (("r71", A_R71), ("r73", A_R73)):
        hits = []
        for rec in out[tag]:
            for D in DBR:
                f = rec[f"D{int(D*1000)}"]["f_g2"]
                ok = np.isfinite(f) and win[0] <= f <= win[1]
                hits.append(ok)
                tot[tag][0] += ok
                tot[tag][1] += 1
        fs = [rec[f"D{int(D*1000)}"]["f_g2"] for rec in out[tag] for D in DBR]
        fs = [x for x in fs if np.isfinite(x)]
        print(f"   {tag}: window [{win[0]:.3f},{win[1]:.3f}] Hz   modelled range over the whole sweep "
              f"[{min(fs):.2f},{max(fs):.2f}] Hz   -> {tot[tag][0]}/{tot[tag][1]} cells inside")
    # the honest headline: both must be inside at the SAME (b, D)
    joint = 0
    for i, b in enumerate(BSW):
        for D in DBR:
            f71 = out["r71"][i][f"D{int(D*1000)}"]["f_g2"]
            f73 = out["r73"][i][f"D{int(D*1000)}"]["f_g2"]
            if A_R71[0] <= f71 <= A_R71[1] and A_R73[0] <= f73 <= A_R73[1]:
                joint += 1
                print(f"   JOINT PASS at b={b}, D={D*1000:.0f} ms:  r71 {f71:.2f} Hz, r73 {f73:.2f} Hz")
    print(f"\n   JOINT (both positives placed at the SAME plant damping and delay): {joint} of {len(BSW)*len(DBR)} cells")
    A_PASS = joint > 0
    print(f"\n   >>> CLAUSE (a) {'PASS' if A_PASS else 'FAIL'} <<<")
    json.dump(dict(sweep=out, joint=joint, window71=A_R71, window73=A_R73, passed=bool(A_PASS)),
              open(HERE / "out" / "g2_a_freq.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
