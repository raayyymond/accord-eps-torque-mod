# -*- coding: utf-8 -*-
"""rj20_hf_rate.py -- lens robust-joint: the pick adds 5-30 Hz DELIVERED torque in the sim (x1.2-1.7 under dist full).
Is that torque damping the wheel (HF wheel motion DOWN) or exciting it (UP)?  Mode B, dist full and lp, V294 vs the pick
in one batch, nominal + mode13 + mode20 + mode20_lo + light_b: the wheel-rate (the 0x18F-type x/8, 100 Hz) rms in
3-5 / 5-9 / 9-13 / 13-17 / 17-23 / 23-30 / 30-45 Hz, all chunks.  ANALYSIS ONLY."""
import os, sys, json
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rj_cands as RC
from rj_lin import H
base = RC.base(); pick = base.replace(fb_b=1106, name="pick")
fam = H.family(); ch = H.route_chunks()
B = ((3, 5), (5, 9), (9, 13), (13, 17), (17, 23), (23, 30), (30, 45))
out = {}
for dist in ("full", "lp"):
    for p in ("nominal", "light_b", "mode13", "mode20", "mode20_lo"):
        R = H.simulate([base, pick], [fam[p]], ch, H.SimOpts(mode="B", dist=dist))
        nK = len(ch)
        res = {}
        for ci, nm in enumerate(("V294", "pick")):
            acc = {b: [] for b in B}
            for k in range(nK):
                j = ci * nK + k
                r = R["rate18"][j, :R["lens"][j]]
                for lo, hi in B:
                    bb, aa = signal.butter(2, [lo / 50.0, hi / 50.0], btype="band")
                    y = signal.filtfilt(bb, aa, r - r.mean())[100:-100]
                    acc[(lo, hi)].append(y)
            res[nm] = {"%d-%d" % b: float(np.sqrt(np.mean(np.concatenate(acc[b]) ** 2))) for b in B}
        out["%s|%s" % (dist, p)] = res
        print("%-4s %-9s wheel-rate rms deg/s  V294 -> pick: %s" % (dist, p, "  ".join(
            "%s %.3f->%.3f (x%.2f)" % (k, res["V294"][k], res["pick"][k], res["pick"][k] / res["V294"][k]) for k in res["V294"])), flush=True)
json.dump(out, open(os.path.join(HERE, "rj20_hf_rate.json"), "w"), indent=1)
