# -*- coding: utf-8 -*-
"""s8_family.py -- trim-ratio lens: the pick (b 964, G 1.70) and its dose neighbours across the WHOLE identified family
+ the prior, mode B (fork in the loop), dists full and lp, V294 in the same batch.  Robust-direction table: for each
metric/band the min and max over members of (candidate / V294) or (candidate - V294).
Writes s8_family.json and s8_family_out.txt.  Analysis only."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
CANDS = [BASE.replace(name="b850", fb_b=850), BASE.replace(name="b964", fb_b=964), BASE.replace(name="b1134", fb_b=1134)]
PLANTS = ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "F_lo", "F_hi", "tau6", "ms_free", "nominal_kappa", "light_b")
BANDS = ("0-5", "5-10", "10-15", "15-22", "22+")
RATIO = ("hard16", "r_mid", "r_hi", "r_lo", "J_err", "cmd_rms")
DIFF = ("track_gain", "turn_hold", "straight_delivery", "i_share")


def main():
    t0 = time.time()
    S = H.sweep_drive(CANDS, plants=PLANTS, dists=("full", "lp"))
    json.dump(H.to_jsonable(S), open(os.path.join(HERE, "s8_family.json"), "w"))
    print("sweep %.0f s, %d members" % (time.time() - t0, len(PLANTS)))
    for c in CANDS:
        for dist in ("full", "lp"):
            print("\n=== %s  dist %s : [min .. max over the %d members, light_b in brackets]" % (c.name, dist, len(PLANTS)))
            for key in RATIO + DIFF:
                cells = []
                for b in BANDS:
                    vals, lb = [], None
                    for p in PLANTS:
                        r, r0 = S[(dist, c.name, p)].get(b), S[(dist, "V294", p)].get(b)
                        if r is None or r0 is None or not np.isfinite(r[key]) or not np.isfinite(r0[key]):
                            continue
                        v = r[key] / r0[key] if key in RATIO else r[key] - r0[key]
                        vals.append(v)
                        if p == "light_b":
                            lb = v
                    if not vals:
                        cells.append("        n/t        ")
                        continue
                    fmt = "%.2f" if key in RATIO else "%+.3f"
                    cells.append(("%s..%s [%s]" % (fmt % min(vals), fmt % max(vals), fmt % lb if lb is not None else "-")).ljust(19))
                print("   %-17s %s" % (key + (" x" if key in RATIO else " d"), " ".join(cells)))
            lc = [S[(dist, c.name, p)]["limit_cycle"]["dB"] - S[(dist, "V294", p)]["limit_cycle"]["dB"] for p in PLANTS]
            print("   limit-cycle dB d  %+.1f .. %+.1f" % (min(lc), max(lc)))
    print("\n(bands %s)  total %.0f s" % (BANDS, time.time() - t0))


if __name__ == "__main__":
    main()
