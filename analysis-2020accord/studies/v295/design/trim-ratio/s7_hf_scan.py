# -*- coding: utf-8 -*-
"""s7_hf_scan.py -- trim-ratio lens: pre-registered F5-HF clause ("no band of mode-A simulated delivered HF torque rises
by more than x1.5") on a dose ladder at the 2.03 Hz pole, plus two pole variants; V294 in the SAME batch (mode A,
dist full, every default member).  Also mode B dist lp (no replayed HF disturbance: the fork staircase + the 1.93-count
sensor noise only) as a second view of the same clause.
Writes s7_hf_scan_out.txt.  Analysis only."""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))
import v295_harness as H  # noqa: E402

BASE = H.Cells.v294()
CANDS = [BASE.replace(name="V294")] + [BASE.replace(name="b%d" % b, fb_b=b) for b in (737, 850, 907, 964, 1021, 1077, 1134)] + \
        [BASE.replace(name="a1017_b567", fb_a=1017), BASE.replace(name="a1014_b850", fb_a=1014, fb_b=850),
         BASE.replace(name="a1005_b1134", fb_a=1005, fb_b=1134)]
PLANTS = ("nominal", "light_b", "J_lo", "tau6")


def run(mode, dist):
    fam = H.family()
    mem = [fam[p] for p in PLANTS]
    ch = H.route_chunks()
    R = H.simulate(CANDS, mem, ch, H.SimOpts(mode=mode, dist=dist), record_1k=True)
    nM, nK = len(mem), len(ch)
    out = {}
    for ci, c in enumerate(CANDS):
        for mi, p in enumerate(PLANTS):
            rows = [ci * nM * nK + mi * nK + k for k in range(nK)]
            hf = [H.hf_content(R["T1k"][j, :R["lens"][j] * 10]) for j in rows]
            out[(c.name, p)] = {k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
    return out


def main():
    t0 = time.time()
    for mode, dist in (("A", "full"), ("B", "lp")):
        o = run(mode, dist)
        print("\n=== mode %s dist %s: delivered-torque rms per band, candidate / V294 (max over bands; FAIL if > 1.5)" % (mode, dist))
        for p in PLANTS:
            b0 = o[("V294", p)]
            print("  %-8s V294 abs %s" % (p, {k: round(v, 2) for k, v in b0.items()}))
            for c in CANDS[1:]:
                r = o[(c.name, p)]
                ratios = [r[k] / b0[k] for k in b0]
                print("     %-12s G %.2f  %s   max x%.2f %s" % (c.name, c.kp_y[0] * c.fb_b / (960 * 567.0),
                                                           " ".join("%.2f" % v for v in ratios), max(ratios),
                                                           "FAIL" if max(ratios) > 1.5 else "pass"))
        print("  (%.0f s)" % (time.time() - t0))


if __name__ == "__main__":
    main()
