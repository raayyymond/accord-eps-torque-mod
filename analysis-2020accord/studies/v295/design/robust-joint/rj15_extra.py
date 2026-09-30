# -*- coding: utf-8 -*-
"""rj15_extra.py -- lens robust-joint: (1) the Pareto point B (trim x1.5, b 850) in the nonlinear replay (nominal,
light_b, J_hi; lp + full) beside V294; (2) an ON-RECORD HF ANCHOR in the same simulator: the delivered 1 kHz lane torque
in 5-30 Hz of V294 / the pick / V282 (the flown rate servo that GROUND at 20 Hz; its cells read from its own image) under
mode A (the recorded r71b command replayed, dist full) on nominal and the 20 Hz stress members -- so the pick's HF
increase can be stated as a fraction of a flown grinding build's, same plant, same road.  (V282 in mode A is not what
V282 did on the road -- a different fork config flew with it -- it is a fixed-input comparison of the LANES.)
Writes rj15_extra.json.  ANALYSIS ONLY."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402


def main():
    out = {}
    base = RC.base()
    B = base.replace(fb_b=850, name="B_t1.5")
    A = base.replace(fb_b=1106, name="A_pick")
    for p in ("nominal", "light_b", "J_hi"):
        S = H.sweep_drive([B, A], plants=(p,), dists=("lp", "full"))
        for k, v in S.items():
            out["drive|" + "|".join(k)] = v
        for dist in ("lp", "full"):
            for c in ("B_t1.5", "A_pick"):
                a, b = S[(dist, c, p)], S[(dist, "V294", p)]
                print("  %-8s %-4s %-7s hard16 5-10 x%.2f 15-22 x%.2f | rmid 5-10 x%.2f 10-15 x%.2f 15-22 x%.2f | tg 5-10 %+.3f 15-22 %+.3f"
                      % (p, dist, c, a["5-10"]["hard16"] / b["5-10"]["hard16"], a["15-22"]["hard16"] / b["15-22"]["hard16"],
                         a["5-10"]["r_mid"] / b["5-10"]["r_mid"], a["10-15"]["r_mid"] / b["10-15"]["r_mid"],
                         a["15-22"]["r_mid"] / b["15-22"]["r_mid"], a["5-10"]["track_gain"] - b["5-10"]["track_gain"],
                         a["15-22"]["track_gain"] - b["15-22"]["track_gain"]), flush=True)
    # (2) HF anchor, mode A
    v282 = H.Cells.v282()
    fam = H.family()
    ch = H.route_chunks()
    for p in ("nominal", "mode20", "mode20_lo", "mode13"):
        try:
            R = H.simulate([base, A, B, v282], [fam[p]], ch, H.SimOpts(mode="A", dist="full"), record_1k=True)
        except H.Int32Overflow as e:
            print("  %s: Int32Overflow %s" % (p, e))
            continue
        nK = len(ch)
        for ci, nm in enumerate(("V294", "A_pick", "B_t1.5", "V282")):
            rows = [ci * nK + k for k in range(nK)]
            hf = [H.hf_content(R["T1k"][j, :R["lens"][j] * 10]) for j in rows]
            hh = {k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
            out["hfA|%s|%s" % (nm, p)] = hh
            print("  HF mode A %-10s %-7s %s" % (p, nm, "  ".join("%s %.2f" % (k, v) for k, v in hh.items())), flush=True)
    json.dump(H.to_jsonable(out), open(os.path.join(HERE, "rj15_extra.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
