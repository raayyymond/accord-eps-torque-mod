# -*- coding: utf-8 -*-
"""p5c_jprofile.py -- how well does THIS drive constrain the inertia J, band by band?  A PROFILE: J fixed on a grid,
the other plant parameters (b, k, Fc, Fs/Fc) re-fitted on the FIT windows at each J (the p5b multiple-shooting estimator,
Nelder-Mead from the p5b nominal), then scored on the HELD-OUT windows.   python p5c_jprofile.py -> p5c_jprofile_out.txt,
_scratch/p5c.json

Reading: a J whose held-out score is within the noise of the best is NOT excluded by the drive.  The fit-window cost is
reported too (its minimum is the p5b estimate when the grid brackets it).
"""
import json
import math
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import optimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
J_GRID = (0.1, 0.2, 0.3, 0.5, 0.8, 1.3)
TAU = 2


def one(bi, J):
    import plib as P
    import oe_lib as O
    import v294_plant as VP
    d = P.load()
    c = VP.v294_cells()
    wins = O.windows(O.segments(d), d=d)
    wf = [w for w in wins if w["band"] == bi and w["role"] == "fit"]
    wh = [w for w in wins if w["band"] == bi and w["role"] == "held"]
    Wf, Wh = O.WindowBatch(d, wf, c), O.WindowBatch(d, wh, c)
    som = float(np.std(Wf.om[:, 1:] - Wf.om[:, 1:].mean(axis=1, keepdims=True)))
    dth = Wf.th[:, 1:] - Wf.th[:, :1]
    sth = float(np.std(dth - dth.mean(axis=1, keepdims=True)))
    nom = json.load(open(os.path.join(HERE, "_scratch", "p5b_ms.json")))["nominal"][P.BANDS[bi][0]]
    b0, k0, F0, Fs0 = nom["b"]["val"], nom["k"]["val"], nom["Fc"]["val"], nom["Fs"]["val"]

    def unpack(q):
        b, k, Fc = (math.exp(v) for v in q[:3])
        return b, k, Fc, Fc * (1.0 + 0.8 / (1.0 + math.exp(-q[3])))

    def cost(Wx, q):
        b, k, Fc, Fs = unpack(q)
        out, _ = Wx.replay(O.band_member(J, b, k, Fc, Fs, TAU))
        return Wx.cost(out, sth, som)

    r0 = min(max((Fs0 / F0 - 1) / 0.8, 1e-3), 1 - 1e-3)
    best = None
    for qs in ([math.log(b0), math.log(k0), math.log(max(F0, 1.0)), math.log(r0 / (1 - r0))],
               [math.log(3.0), math.log(k0), math.log(30.0), 0.0]):
        r = optimize.minimize(lambda q: cost(Wf, q), qs, method="Nelder-Mead", options=dict(maxfev=200, xatol=0.01, fatol=1e-5))
        if best is None or r.fun < best.fun:
            best = r
    b, k, Fc, Fs = unpack(best.x)
    mem = O.band_member(J, b, k, Fc, Fs, TAU)
    sh = Wh.scores(Wh.replay(mem)[0])
    return dict(band=bi, J=J, b=b, k=k, Fc=Fc, Fs=Fs, fit_cost=float(best.fun), held_cost=float(Wh.cost(Wh.replay(mem)[0], sth, som)),
                held=sh)


def main():
    jobs = [(bi, J) for bi in range(5) for J in J_GRID]
    with Pool(15) as pool:
        res = pool.starmap(one, jobs)
    import plib as P
    lines = []

    def pr(s=""):
        print(s, flush=True)
        lines.append(s)

    pr("J PROFILE: J fixed, b/k/Fc/Fs refitted on the fit windows (p5b estimator), scored on the held-out windows")
    for bi, (bn, lo, hi) in enumerate(P.BANDS):
        pr("")
        pr("BAND %s m/s" % bn)
        pr("  %6s | %7s %6s %6s %6s | %8s %8s | %8s %8s %8s %8s" % ("J", "b", "k", "Fc", "Fs", "fit cost", "held cst",
                                                              "om R2", "skill", "dth R2", "om rms"))
        for r in sorted([r for r in res if r["band"] == bi], key=lambda r: r["J"]):
            h = r["held"]
            pr("  %6.2f | %7.2f %6.1f %6.1f %6.1f | %8.4f %8.4f | %+8.3f %+8.3f %+8.3f %8.2f" % (
                r["J"], r["b"], r["k"], r["Fc"], r["Fs"], r["fit_cost"], r["held_cost"], h["om_R2"], h["om_skill_vs_hold"],
                h["dth_R2"], h["om_rms"]))
    json.dump(res, open(os.path.join(HERE, "_scratch", "p5c.json"), "w"), indent=1)
    open(os.path.join(HERE, "p5c_jprofile_out.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
