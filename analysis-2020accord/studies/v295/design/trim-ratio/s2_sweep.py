# -*- coding: utf-8 -*-
"""s2_sweep.py -- trim-ratio lens: closed-loop mode-B sweep (fork in the loop, recorded planner demand) of the
candidate shortlist from s1_plane, V294 in the SAME batch, dists full + lp, plants nominal / light_b / b_lo / J_hi.

Every number is reported as a DIFFERENCE / RATIO against V294 in the same batch.  Dwells are not printed.
Writes s2_sweep.json.  Analysis only."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
sys.path.insert(0, HERE)
import v295_harness as H  # noqa: E402
from s1_plane import realise  # noqa: E402

BASE = H.Cells.v294()
SHORT = [(1011, 1.5), (1011, 2.0), (1011, 2.5), (1011, 3.0), (1017, 1.0), (1014, 1.5), (1014, 2.0), (1017, 2.0),
         (1005, 2.0), (1017, 3.0)]
PLANTS = ("nominal", "light_b", "b_lo", "J_hi")
KEYS = ("track_gain", "turn_hold", "straight_delivery", "J_err", "i_share", "cmd_rms", "trim_ff", "r_lo", "r_mid", "r_hi",
        "hard16")


def main():
    cands = [realise(a, G) for a, G in SHORT]
    t0 = time.time()
    S = H.sweep_drive(cands, plants=PLANTS, dists=("full", "lp"))
    print("sweep %.0f s" % (time.time() - t0))
    json.dump(H.to_jsonable(S), open(os.path.join(HERE, "s2_sweep.json"), "w"))
    bands = ("0-5", "5-10", "10-15", "15-22", "22+")
    for dist in ("full", "lp"):
        for p in PLANTS:
            b0 = S[(dist, "V294", p)]
            print("\n=== dist %s  plant %s   V294 absolute: track %s | hold %s | hard16 %s | r_mid %s | limit %.2f Hz %+.1f dB" % (
                dist, p, [round(b0[b]["track_gain"], 3) for b in bands if b in b0],
                [round(b0[b]["turn_hold"], 3) for b in bands if b in b0],
                [round(b0[b]["hard16"], 2) for b in bands if b in b0],
                [round(b0[b]["r_mid"], 2) for b in bands if b in b0], b0["limit_cycle"]["f"], b0["limit_cycle"]["dB"]))
            print("   %-12s %-36s %-36s %-30s %-30s %-30s %s" % ("cand", "d track_gain (5 bands)", "d turn_hold", "hard16 x V294",
                                                                   "r_mid (1-3Hz) x V294", "r_hi (3-8Hz) x V294", "limit dB"))
            for c in cands:
                r = S[(dist, c.name, p)]
                dt = [r[b]["track_gain"] - b0[b]["track_gain"] for b in bands if b in r]
                dh = [r[b]["turn_hold"] - b0[b]["turn_hold"] for b in bands if b in r]
                hx = [r[b]["hard16"] / b0[b]["hard16"] if np.isfinite(b0[b]["hard16"]) else float("nan") for b in bands if b in r]
                rx = [r[b]["r_mid"] / b0[b]["r_mid"] for b in bands if b in r]
                hi = [r[b]["r_hi"] / b0[b]["r_hi"] for b in bands if b in r]
                print("   %-12s %-36s %-36s %-30s %-30s %-30s %+.1f" % (
                    c.name, " ".join("%+.3f" % v for v in dt), " ".join("%+.3f" % v if np.isfinite(v) else "  nan " for v in dh),
                    " ".join("%.2f" % v for v in hx), " ".join("%.2f" % v for v in rx), " ".join("%.2f" % v for v in hi),
                    r["limit_cycle"]["dB"] - b0["limit_cycle"]["dB"]))
    print("\ntotal %.0f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
