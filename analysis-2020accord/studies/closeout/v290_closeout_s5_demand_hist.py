# -*- coding: utf-8 -*-
"""Close-out artifact, section 5(d): the MEASURED demand-index histograms behind the Kd LERP.

`basepick`'s ADDENDUM A5 requires the close-out page to draw the delivered Kd(idx) curve with the
measured grinding-episode idx histogram underneath it, "otherwise the page shows a 25 % cut where the
car sees 12 %".  This script produces exactly that histogram, plus the two authority regimes, off the
wire, using `reqaxis`'s byte-exact `demand()` mirror and the same census episode cache
`basepick_delivered_dose.py` uses -- so the fractions below reproduce its delivered-Kd means.

Output: analysis-2020accord/_scratch/out/v290_closeout_s5_demand.json
Run:    python analysis-2020accord/studies/closeout/v290_closeout_s5_demand_hist.py
Analysis only: builds nothing, flashes nothing, sends nothing.
"""
import json
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", ".."))
REPO = os.path.abspath(os.path.join(KIT, ".."))
GRIND = os.path.join(REPO, "rlog-tools", "studies", "grind")
OUTD = os.path.join(KIT, "_scratch", "out")
sys.path.insert(0, GRIND)
sys.path.insert(0, os.path.join(KIT, "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

import kpkd_axis_r62_r63 as AX     # noqa: E402  (reqaxis's byte-exact demand mirror)
import creep20_loop_id as C20      # noqa: E402

FS = 100.0
EDGES = list(range(0, 245, 5)) + [10000]   # 5-wide bins to idx 240, then a >=240 catch-all


def main():
    C = {n: AX.cells(n) for n in AX.IMGS}
    P = pickle.load(open(AX.CENSUS_PKL, "rb"))
    ep = {}
    for e in P["episodes"]:
        ep.setdefault(e["tag"], []).append(e)

    per_route, pools = {}, {}
    for tag in ("r62_v289", "r63_v289", "r5e_v288"):
        g = C20.load(tag)
        idx, _, _ = AX.demand(np.round(g["cmd"]), g["bar"], C[AX.TAG_IMG[tag]])
        eng = g["eng"]
        v = g["vego"]
        ang = np.abs(g["ang"])
        dcmd = np.abs(np.r_[0.0, np.diff(np.round(g["cmd"]))])
        m = np.zeros(len(g["t"]), bool)
        for e in ep.get(tag, []):
            m[int(e["a"]):int(e["b"])] = True
        sel = dict(grind=eng & m,
                   step=eng & (dcmd >= 122),
                   lock=eng & (v >= 2) & (v <= 5) & (ang >= 70) & (ang <= 140),
                   cruise=eng & (v >= 22) & (ang < 5),
                   eng=eng)
        per_route[tag] = {}
        for k, mm in sel.items():
            x = idx[mm].astype(float)
            per_route[tag][k] = summarise(x)
            pools.setdefault(k, {}).setdefault("all", []).append(x)
            if tag.endswith("v289"):
                pools[k].setdefault("v289", []).append(x)

    out = {"per_route": per_route, "pool": {}, "edges": EDGES, "fs": FS}
    for k, d in pools.items():
        out["pool"][k] = {p: summarise(np.concatenate(v)) for p, v in d.items()}
    # the Kd records the page plots, and their delivered dose over the V289 grinding pool
    pool = np.concatenate(pools["grind"]["v289"])
    recs = {"base": ((0, 11, 22, 32), (128, 128, 128, 128)),
            "S'": ((0, 11, 22, 32), (112, 112, 112, 128)),
            "S": ((0, 11, 22, 32), (96, 96, 96, 128)),
            "M1": ((0, 11, 22, 32), (96, 96, 112, 128))}
    out["records"] = {}
    for name, (X, Y) in recs.items():
        xs = list(range(0, 241))
        kd = [float(np.interp(np.clip(i, X[0], X[-1]), X, Y)) for i in xs]
        out["records"][name] = dict(X=list(X), Y=list(Y), idx=xs, kd=kd,
                                    delivered_grind_v289=float(np.interp(np.clip(pool, X[0], X[-1]), X, Y).mean()))
    json.dump(out, open(os.path.join(OUTD, "v290_closeout_s5_demand.json"), "w"), indent=0, default=float)
    print("grinding pool (r62+r63): n=%d = %.1f s, frac idx>32 = %.4f, p50 = %.1f"
          % (len(pool), len(pool) / FS, float((pool > 32).mean()), float(np.median(pool))))
    for k in ("grind", "step", "lock", "cruise", "eng"):
        s = out["pool"][k]["all"]
        print("  %-7s n=%6d  p50 %6.1f  frac>32 %.3f" % (k, s["n"], s["p50"], s["frac_gt32"]))
    print("wrote", os.path.join(OUTD, "v290_closeout_s5_demand.json"))


def summarise(x):
    if len(x) == 0:
        return dict(n=0, hist=[0] * (len(EDGES) - 1), p50=None, frac_gt32=None, secs=0.0)
    h, _ = np.histogram(x, bins=EDGES)
    return dict(n=int(len(x)), secs=float(len(x) / FS), hist=[int(v) for v in h],
                frac=[float(v) / len(x) for v in h],
                p10=float(np.percentile(x, 10)), p50=float(np.median(x)), p90=float(np.percentile(x, 90)),
                frac_gt32=float((x > 32).mean()), mean=float(x.mean()))


if __name__ == "__main__":
    main()
