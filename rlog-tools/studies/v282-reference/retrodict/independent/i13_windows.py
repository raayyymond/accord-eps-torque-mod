# -*- coding: utf-8 -*-
"""i13 -- per-WINDOW operating points, then the controller x plant cross table over them.

Why per window.  The notch centre, the low-speed factor, the rate-loop taper, k(v) and the
angle->measurement map g all move with speed, and each route's engaged >=15 m/s population spans
17-28 m/s.  Evaluating a route at its MEDIAN speed both smears the notch (which in reality tracks the
instantaneous speed) and hides the speed where a controller is worst.  So each 10.24 s window is its
own operating point (v, g), the loop is evaluated there, and a route's "plant" is its set of windows.

Step 1 dumps (v, g) per window per route (g = the window's own regression of the logged la_act on the
logged angle -- measured, not modelled).
Step 2 evaluates L for every controller on every route's windows and reports, per cell, the fraction
of windows predicted unstable and the median / 90th-percentile |L| at the first -180 crossing.

ANALYSIS ONLY.  python i13_windows.py dump <route> [...]   |   python i13_windows.py table
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import signal

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(HERE))
import v282cmp as V   # noqa: E402
import i9_loop as M   # noqa: E402

FS = 100.0
NPS, HOP = 1024, 512
VMIN = 15.0
F = np.linspace(0.3, 8.0, 15401)


def dump(route):
    S = V.load(route)
    m = (S["active"] & ~S["pressed"] & ~S["sat"] & (S["v"] >= VMIN)
         & np.isfinite(S["sa"]) & np.isfinite(S["la_act"]) & np.isfinite(S["out"]))
    rows = []
    sa = np.nan_to_num(S["sa"] - S["aoff"])
    la = np.nan_to_num(S["la_act"])
    for a, b in V.runs(m, S["t"], min_s=NPS / FS):
        for s in range(a, b - NPS + 1, HOP):
            e = s + NPS
            vv = S["v"][s:e]
            if not np.isfinite(vv).all():
                continue
            x = signal.detrend(sa[s:e])
            y = signal.detrend(la[s:e])
            if np.dot(x, x) < 1e-6:
                continue
            g = -float(np.dot(x, y) / np.dot(x, x))
            r2 = 1.0 - float(np.sum((y + g * x) ** 2) / max(np.sum(y ** 2), 1e-12))
            if not (0.005 < g < 0.5) or r2 < 0.5:
                continue
            rows.append(dict(t=float(S["t"][s]), v=float(np.median(vv)),
                             vlo=float(vv.min()), vhi=float(vv.max()), g=g, r2=r2))
    del S, sa, la
    return rows


def eval_cell(ctrl, pts, tau=0.060, kmul=1.0, bmul=1.0, ndf=1.0):
    Lx, fx, unst = [], [], 0
    for p in pts:
        L, _, _ = M.L_of(F, ctrl, p["v"], p["g"], tau=tau, kmul=kmul, bmul=bmul, ndf=ndf)
        cx = M.crossing(F, L)
        if cx is None:
            Lx.append(0.0); fx.append(np.nan)
            continue
        Lx.append(cx[1]); fx.append(cx[0])
        if cx[1] >= 1.0:
            unst += 1
    Lx = np.array(Lx)
    return dict(n=len(pts), frac_unstable=float(unst / max(len(pts), 1)),
                L_med=float(np.median(Lx)), L_p90=float(np.percentile(Lx, 90)),
                L_max=float(Lx.max()) if len(Lx) else np.nan,
                f_med=float(np.nanmedian(fx)) if len(fx) else np.nan, Lx=Lx.tolist())


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        store = {}
        p = HERE / "out_i13_points.json"
        if p.exists():
            store = json.load(open(p))
        for r in sys.argv[2:]:
            rows = dump(r)
            store[r] = rows
            v = np.array([x["v"] for x in rows]); g = np.array([x["g"] for x in rows])
            print(f"{r}  {len(rows):4d} windows  v {np.median(v):5.1f} [{v.min():.1f}-{v.max():.1f}]  "
                  f"g {np.median(g):.5f} [{g.min():.5f}-{g.max():.5f}]  "
                  f"medR2 {np.median([x['r2'] for x in rows]):.3f}")
        json.dump(store, open(p, "w"))
        sys.exit(0)

    pts = json.load(open(HERE / "out_i13_points.json"))
    tags = [t for t, c in M.CTRL.items() if c["route"] in pts and len(pts[c["route"]]) >= 8]
    print(f"controllers/plants: {tags}")
    for tau in (0.055, 0.060, 0.075):
        print(f"\n{'='*118}\nFRACTION OF WINDOWS PREDICTED UNSTABLE   tau {tau*1000:.0f} ms, k x1.0, b x1.0, relay DF 1.0")
        print("   ctrl \\ plant " + "".join(f"{t:>9s}" for t in tags) + "   outcome")
        res = {}
        for t in tags:
            row = []
            for p in tags:
                r = eval_cell(M.CTRL[t], pts[M.CTRL[p]["route"]], tau=tau)
                res[f"{t}|{p}"] = r
                row.append(r["frac_unstable"])
            print(f"   {t:12s}" + "".join(f"{x:9.2f}" for x in row) + f"   {M.OUTCOME[t]}")
        print(f"\n   MEDIAN |L| at the first -180 crossing   tau {tau*1000:.0f} ms")
        print("   ctrl \\ plant " + "".join(f"{t:>9s}" for t in tags))
        for t in tags:
            print(f"   {t:12s}" + "".join(f"{res[f'{t}|{p}']['L_med']:9.3f}" for p in tags))
        if abs(tau - 0.060) < 1e-9:
            json.dump({k: {kk: vv for kk, vv in v.items() if kk != "Lx"} for k, v in res.items()},
                      open(HERE / "out_i13_table.json", "w"), indent=1)
            json.dump({k: v["Lx"] for k, v in res.items()}, open(HERE / "out_i13_Lx.json", "w"))
        print(f"\n   RANK per plant (riskiest first, by median |L| at the crossing)  tau {tau*1000:.0f} ms")
        for p in tags:
            vals = sorted(((t, res[f"{t}|{p}"]["L_med"]) for t in tags), key=lambda z: -z[1])
            print(f"   plant {p:6s}: " + "  ".join(f"{t}={x:.2f}" for t, x in vals))
