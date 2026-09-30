# -*- coding: utf-8 -*-
"""s7_regress_grid.py -- p-gain lens: a small systematic grid of REGRESSIVE Kp(idx) schedules (non-increasing Kp, so the
static ratio Kp(idx)/960 always exceeds the local-slope ratio and the trim ratio always equals the static ratio -- the
property s4 found protects the outer loop on light_b), against flat multiples, all in ONE batch with V294.

Family:  X = [0, i1, (i1+i2)//2, i2, 208],  Y = 960 * [k0, k0, (k0+1)/2, 1, 1]   (k0 plateau to i1, linear-in-Kp taper
to 1.0 at i2).  k0 in {1.2, 1.3, 1.4}, i1 in {8, 20}, i2 in {60, 100, 150}.  Rejected before scoring if the surface is
not monotone or the local slope anywhere in idx 0..200 falls below 0.70 x V294's (a flat spot in the torque curve).
Scored: mode B lp + full on nominal / light_b / b_lo / J_hi (drive metrics as candidate - V294), the outer loop at the
band operating points (pg_lib.outer_local) on light_b and b_lo, the zero-command trim cap.
ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pg_lib as G  # noqa: E402
H = G.H
from s4_shape_sweep import OPS  # noqa: E402
TAG = "s7_grid"
PLANTS = ("nominal", "light_b", "b_lo", "J_hi")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")


GRID_K0 = (1.2, 1.3, 1.4)
GRID_I1 = (8, 20)
GRID_I2 = (60, 100, 150)
SLOPE_RANGE = (2, 150)     # rev 2: the rail region (idx >= 184 for a flat x1.3) is excluded -- rev 1 used 2..200 and
MIN_SLOPE = 0.60           # rejected every flat multiple for its P-clamp top (0.3 % of r71b's engaged frames)


def grid():
    b = H.Cells.v294()
    C = []
    for g in (1.1, 1.2, 1.3):
        C.append(b.replace(kp_y=(int(round(960 * g)),) * 5, name="g%.1f" % g))
    for k0 in GRID_K0:
        for i1 in GRID_I1:
            for i2 in GRID_I2:
                X = (0, i1, (i1 + i2) // 2, i2, 208)
                Y = tuple(int(round(960 * y)) for y in (k0, k0, (k0 + 1) / 2, 1.0, 1.0))
                C.append(b.replace(kp_x=X, kp_y=Y, name="R%.2f_%d_%d" % (k0, i1, i2)))
    return b, C


def main():
    base, C = grid()
    keep = []
    for c in C:
        mono, _ = G.monotone(c)
        ls = min(G.local_slope(c, i) / G.local_slope(base, i) for i in range(*SLOPE_RANGE))
        print("%-12s monotone %s  min local-slope ratio %.2f  static ratio @6/18/34/50/75/110: %s" % (
            c.name, mono, ls, " ".join("%.2f" % G.static_ratio(c, i, base) for i in (6, 18, 34, 50, 75, 110))))
        if mono and ls >= MIN_SLOPE:
            keep.append(c)
    print("scoring %d candidates" % len(keep))
    t0 = time.time()
    plants = PLANTS
    S = H.sweep_drive(keep, plants=plants, dists=("lp", "full"))
    print("sweep %.0f s" % (time.time() - t0))
    json.dump(H.to_jsonable(S), open(os.path.join(OUT, TAG + "_drive.json"), "w"), indent=1)
    fam = H.family()
    ff = np.logspace(-2, np.log10(20.0), 800)
    rows = {}
    for c in keep + [base]:
        r = dict()
        # benefit: tracking / hold deltas, lp, min over plants, per band
        for key in ("track_gain", "turn_hold", "straight_delivery"):
            for b in ("0-5", "5-10", "10-15", "15-22", "22+"):
                vals = []
                for p in plants:
                    x, y = S[("lp", c.name, p)].get(b, {}).get(key, np.nan), S[("lp", "V294", p)].get(b, {}).get(key, np.nan)
                    vals.append(x - y)
                r["%s_%s" % (key, b)] = float(np.nanmin(vals))
        # cost: hard16 and rate1-3 ratios, max over plants and dists at 5-10 / 15-22 (and 0-5 for rate)
        for key, bands in (("hard16", ("5-10", "15-22")), ("r_mid", ("0-5", "5-10", "15-22", "22+"))):
            for dist in ("lp", "full"):
                vals = []
                for p in plants:
                    for b in bands:
                        x, y = S[(dist, c.name, p)].get(b, {}).get(key, np.nan), S[(dist, "V294", p)].get(b, {}).get(key, np.nan)
                        vals.append(x / y if y else np.nan)
                r["%s_%s_max" % (key, dist)] = float(np.nanmax(vals))
        r["lc_lp_lightb_dB"] = S[("lp", c.name, "light_b")]["limit_cycle"]["dB"] - S[("lp", "V294", "light_b")]["limit_cycle"]["dB"]
        r["lc_full_max_dB"] = max(S[("full", c.name, p)]["limit_cycle"]["dB"] - S[("full", "V294", p)]["limit_cycle"]["dB"] for p in plants)
        ms = []
        for p in ("light_b", "b_lo"):
            for lab, v, io in OPS:
                pp = fam[p].at(v)
                m1 = H.margins(ff, G.outer_local(c, pp, v, ff, io))
                m0 = H.margins(ff, G.outer_local(base, pp, v, ff, io))
                ms.append((m1["Ms"] / m0["Ms"], m1["GM_min"], p, lab))
        r["outer_Ms_ratio_max"] = float(max(m[0] for m in ms))
        r["outer_Ms_ratio_where"] = [m[2] + " " + m[3] for m in ms if m[0] == max(mm[0] for mm in ms)][0]
        r["outer_GM_min"] = float(min(m[1] for m in ms))
        kp0 = int(H.lerp_table(c.kp_x, c.kp_y)[0])
        r["trim_cap_T0"] = round(c.fb_clamp * kp0 / 256 * 254 / 256 * 0.990234 * c.gain / 32768)
        rows[c.name] = r
    json.dump(rows, open(os.path.join(OUT, TAG + "_summary.json"), "w"), indent=1)
    print("\nBENEFIT = min over the 4 plants of (cand - V294), lp.   COST = max over plants (and bands) of cand/V294.")
    print("%-12s | trk 0-5  5-10 10-15 15-22  22+ | hold 5-10 10-15 15-22 22+ | str 5-10 | h16 lp  full | r13 lp  full | lc lb | outMs  GMmin  cap" % "cand")
    for nm, r in rows.items():
        print("%-12s | %+.3f %+.3f %+.3f %+.3f %+.3f | %+.3f %+.3f %+.3f %+.3f | %+.2f | %.2f %.2f | %.2f %.2f | %+.1f | %.2f %.2f %4d  (%s)" % (
            nm, r["track_gain_0-5"], r["track_gain_5-10"], r["track_gain_10-15"], r["track_gain_15-22"], r["track_gain_22+"],
            r["turn_hold_5-10"], r["turn_hold_10-15"], r["turn_hold_15-22"], r["turn_hold_22+"], r["straight_delivery_5-10"],
            r["hard16_lp_max"], r["hard16_full_max"], r["r_mid_lp_max"], r["r_mid_full_max"], r["lc_lp_lightb_dB"],
            r["outer_Ms_ratio_max"], r["outer_GM_min"], r["trim_cap_T0"], r["outer_Ms_ratio_where"]))


if __name__ == "__main__":
    main()
