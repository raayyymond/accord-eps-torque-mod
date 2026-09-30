# -*- coding: utf-8 -*-
"""rj12_sens.py -- lens robust-joint: SENSITIVITY of the pick (and the g-runner-up) to every plant uncertainty the brief
names, in the nonlinear byte-exact closed loop (mode B, V294 in the same batch):
  J x0.5 (J_lo 0.1) / x2.5 (J_hi 0.5, in rj6) / x4 (J_hi2 0.8) ; b corners (b_lo in rj6, b_hi) ; Fc x0.5 (F_lo) / x2 (F_hi in
  rj6) ; delay x1.5 (tau9) ; the kappa map (nominal_kappa) ; the two-mass STRESS members mode13 / mode20 / mode20_lo.
For the stress members the delivered 1 kHz torque is recorded and its 5-9 / 9-13 / 13-17 / 17-23 / 23-30 Hz content is
compared with V294's (lp and full) -- the 'no grinding' guard in the only members that carry an HF mode (BELIEF members).
Writes rj12_sens.json.  ANALYSIS ONLY."""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rj_cands as RC  # noqa: E402
from rj_lin import H  # noqa: E402

EXTRA = ("J_lo", "J_hi2", "b_hi", "F_lo", "tau9", "nominal_kappa", "mode13", "mode20", "mode20_lo")


def main():
    F1 = RC.make(g=1.0, t=1.95, name="F1", allow_opcode=False)
    F3 = RC.make(g=1.2, t=1.95, name="F3", allow_opcode=False)
    base = RC.base()
    fam = H.family()
    ch = H.route_chunks()
    res = {}
    t0 = time.time()
    for p in EXTRA:
        S = H.sweep_drive([F1, F3], plants=(p,), dists=("lp", "full"))
        for k, v in S.items():
            res["drive|" + "|".join(k)] = v
        print("  %s done %.0f s" % (p, time.time() - t0), flush=True)
    # delivered HF torque on the stress members (1 kHz record), both dists
    for dist in ("lp", "full"):
        for p in ("mode13", "mode20", "mode20_lo"):
            R = H.simulate([base, F1, F3], [fam[p]], ch, H.SimOpts(mode="B", dist=dist), record_1k=True)
            nK = len(ch)
            for ci, nm in enumerate(("V294", "F1", "F3")):
                rows = [ci * nK + k for k in range(nK)]
                hf = [H.hf_content(R["T1k"][j, :R["lens"][j] * 10]) for j in rows]
                res["hf|%s|%s|%s" % (dist, nm, p)] = {k: float(np.sqrt(np.mean([h[k] ** 2 for h in hf]))) for k in hf[0]}
            print("  HF %s %s done %.0f s" % (dist, p, time.time() - t0), flush=True)
    json.dump(H.to_jsonable(res), open(os.path.join(HERE, "rj12_sens.json"), "w"), indent=1)
    # summary
    print("\nSENSITIVITY (ratio / difference vs V294, same batch):")
    for p in EXTRA:
        for dist in ("lp", "full"):
            for c in ("F1", "F3"):
                a = res["drive|%s|%s|%s" % (dist, c, p)]
                b = res["drive|%s|V294|%s" % (dist, p)]
                def r(bd, k):
                    try:
                        return a[bd][k] / b[bd][k]
                    except Exception:
                        return float("nan")
                def dd(bd, k):
                    try:
                        return a[bd][k] - b[bd][k]
                    except Exception:
                        return float("nan")
                print("  %-13s %-4s %-3s hard16 5-10 x%.2f 15-22 x%.2f | rmid 5-10 x%.2f 10-15 x%.2f 15-22 x%.2f | tg 0-5 %+.3f 5-10 %+.3f 15-22 %+.3f 22+ %+.3f | th 15-22 %+.3f"
                      % (p, dist, c, r("5-10", "hard16"), r("15-22", "hard16"), r("5-10", "r_mid"), r("10-15", "r_mid"),
                         r("15-22", "r_mid"), dd("0-5", "track_gain"), dd("5-10", "track_gain"), dd("15-22", "track_gain"),
                         dd("22+", "track_gain"), dd("15-22", "turn_hold")))
    print("\nDELIVERED TORQUE rms (T counts) by HF band, stress members, mode B:")
    for dist in ("lp", "full"):
        for p in ("mode13", "mode20", "mode20_lo"):
            for nm in ("V294", "F1", "F3"):
                h = res["hf|%s|%s|%s" % (dist, nm, p)]
                print("  %-4s %-10s %-4s %s" % (dist, p, nm, "  ".join("%s %.3f" % (k, v) for k, v in h.items())))


if __name__ == "__main__":
    main()
