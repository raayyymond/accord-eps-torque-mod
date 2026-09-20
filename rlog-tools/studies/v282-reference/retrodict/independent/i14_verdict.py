# -*- coding: utf-8 -*-
"""i14 -- the three pre-registered gate clauses, the relay counterfactual, and the term ablation.

(a) RANK        r71's controller riskiest on >= 2 of 3 non-r71 plants
(b) SEPARATION  r71 vs r72 must not overlap in a route-cluster bootstrap
(c) NO FALSE ALARM  rev 6.4's controller must not rank riskier than r71's on any plant

plus:
  * r71 WITH vs WITHOUT the relay, per window -- the counterfactual the whole repair rests on
  * predicted crossing frequency vs the MEASURED 2.30 Hz limit cycle
  * a term ablation on r73, which is where the model breaks

ANALYSIS ONLY.  python i14_verdict.py
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import i9_loop as M       # noqa: E402
import i13_windows as W   # noqa: E402

RNG = np.random.default_rng(20260920)
NB = 4000


def boot_ci(Lx, nb=NB, q=(2.5, 97.5)):
    Lx = np.asarray(Lx, float)
    if len(Lx) < 3:
        return (np.nan, np.nan)
    idx = RNG.integers(0, len(Lx), size=(nb, len(Lx)))
    med = np.median(Lx[idx], axis=1)
    return (float(np.percentile(med, q[0])), float(np.percentile(med, q[1])))


if __name__ == "__main__":
    pts = json.load(open(HERE / "out_i13_points.json"))
    tags = [t for t, c in M.CTRL.items() if c["route"] in pts and len(pts[c["route"]]) >= 8]
    P = {t: pts[M.CTRL[t]["route"]] for t in tags}

    print("=" * 100)
    print("COUNTERFACTUAL -- r71's controller with and without the SteerFriction relay, per window")
    print(f"   {'plant':7s} {'n':>4s} {'WITH relay: med|L|':>20s} {'f_x':>7s} {'%unst':>6s} "
          f"{'NO relay: med|L|':>18s} {'f_x':>7s} {'%unst':>6s}  ratio")
    for p in tags:
        a = W.eval_cell(M.CTRL["r71"], P[p])
        b = W.eval_cell(dict(M.CTRL["r71"], relay_live=False), P[p])
        print(f"   {p:7s} {a['n']:4d} {a['L_med']:20.3f} {a['f_med']:7.3f} {100*a['frac_unstable']:6.0f} "
              f"{b['L_med']:18.3f} {b['f_med']:7.3f} {100*b['frac_unstable']:6.0f}  "
              f"{a['L_med']/max(b['L_med'],1e-9):5.3f}")

    print("\n" + "=" * 100)
    print("PREDICTED CROSSING FREQUENCY vs the MEASURED 2.298 Hz limit cycle (r71 on r71's windows)")
    for tau in (0.055, 0.060, 0.075):
        fx = []
        for q in P["r71"]:
            L, _, _ = M.L_of(W.F, M.CTRL["r71"], q["v"], q["g"], tau=tau)
            cx = M.crossing(W.F, L)
            if cx:
                fx.append(cx[0])
        fx = np.array(fx)
        # the limit cycle happened at v 16.4-22.1, so also restrict to those windows
        sel = [i for i, q in enumerate(P["r71"]) if 16.0 <= q["v"] <= 22.5]
        print(f"   tau {tau*1000:3.0f} ms: all windows f_x med {np.median(fx):.3f} "
              f"[{np.percentile(fx,10):.3f}-{np.percentile(fx,90):.3f}] Hz   "
              f"| the LC's own speed band (16-22.5 m/s, n {len(sel)}) med "
              f"{np.median([fx[i] for i in sel if i < len(fx)]):.3f} Hz   "
              f"error vs 2.298 Hz {100*(np.median([fx[i] for i in sel if i < len(fx)])/2.298-1):+.1f} %")

    print("\n" + "=" * 100)
    print("GATE (a) RANK -- r71's controller must be RISKIEST on >=2 of the non-r71 plants")
    res = {}
    for t in tags:
        for p in tags:
            res[f"{t}|{p}"] = W.eval_cell(M.CTRL[t], P[p])
    nonr71 = [p for p in tags if p != "r71"]
    wins = 0
    for p in nonr71:
        order = sorted(((t, res[f"{t}|{p}"]["L_med"]) for t in tags), key=lambda z: -z[1])
        top = order[0][0]
        wins += (top == "r71")
        print(f"   plant {p:6s}: riskiest = {top:5s} ({order[0][1]:.3f});  r71 = "
              f"{dict(order)['r71']:.3f} (rank {[t for t,_ in order].index('r71')+1})")
    print(f"   => r71 riskiest on {wins} of {len(nonr71)} non-r71 plants   "
          f"{'PASS' if wins >= 2 else 'FAIL'}")

    print("\n" + "=" * 100)
    print("GATE (b) SEPARATION -- r71 vs r72, route-cluster bootstrap of the median |L|")
    for p in tags:
        a, b = res[f"r71|{p}"], res[f"r72|{p}"]
        ca = boot_ci(json.load(open(HERE / "out_i13_Lx.json"))[f"r71|{p}"])
        cb = boot_ci(json.load(open(HERE / "out_i13_Lx.json"))[f"r72|{p}"])
        ov = not (ca[0] > cb[1] or cb[0] > ca[1])
        print(f"   plant {p:6s}: r71 {a['L_med']:.3f} CI [{ca[0]:.3f}, {ca[1]:.3f}]   "
              f"r72 {b['L_med']:.3f} CI [{cb[0]:.3f}, {cb[1]:.3f}]   "
              f"{'OVERLAP' if ov else 'separated'}")

    print("\n" + "=" * 100)
    print("GATE (c) NO FALSE ALARM -- rev 6.4 (T64a/T64b/T64B) must NOT outrank r71 on any plant")
    bad = 0
    for p in tags:
        r71 = res[f"r71|{p}"]["L_med"]
        for t in ("T64a", "T64b", "T64B"):
            if res[f"{t}|{p}"]["L_med"] > r71:
                bad += 1
                print(f"   FALSE ALARM: plant {p} -- {t} {res[f'{t}|{p}']['L_med']:.3f} > r71 {r71:.3f}")
    print(f"   => {bad} violations   {'PASS' if bad == 0 else 'FAIL'}")

    print("\n" + "=" * 100)
    print("ABLATION on r73 -- which flown term, removed, changes the (wrong) verdict?")
    base = W.eval_cell(M.CTRL["r73"], P["r73"])
    print(f"   as flown                : med|L| {base['L_med']:6.3f} at {base['f_med']:.3f} Hz, "
          f"{100*base['frac_unstable']:.0f} % unstable")
    for name, kw in (("relay off", dict(use_relay=False)), ("notch off", dict(use_notch=False)),
                     ("rate loop off", dict(use_rate=False))):
        c = dict(M.CTRL["r73"])
        r = W.eval_cell(c, P["r73"], **{}) if not kw else None
        Lx, fx, un = [], [], 0
        for q in P["r73"]:
            L, _, _ = M.L_of(W.F, c, q["v"], q["g"], **kw)
            cx = M.crossing(W.F, L)
            if cx is None:
                Lx.append(0.0); continue
            Lx.append(cx[1]); fx.append(cx[0]); un += cx[1] >= 1
        print(f"   {name:24s}: med|L| {np.median(Lx):6.3f} at "
              f"{np.median(fx) if fx else float('nan'):.3f} Hz, {100*un/len(P['r73']):.0f} % unstable")
    for km in (1.3, 1.8, 2.5):
        Lx, un = [], 0
        for q in P["r73"]:
            L, _, _ = M.L_of(W.F, M.CTRL["r73"], q["v"], q["g"], kmul=km)
            cx = M.crossing(W.F, L)
            Lx.append(0.0 if cx is None else cx[1]); un += (cx is not None and cx[1] >= 1)
        print(f"   plant stiffness x{km:<4.1f}      : med|L| {np.median(Lx):6.3f}, "
              f"{100*un/len(P['r73']):.0f} % unstable")
