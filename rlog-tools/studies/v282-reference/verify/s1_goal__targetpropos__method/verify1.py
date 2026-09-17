"""Independent re-derivation of a few s1_goal cells cited in the target-proposal-per-cell finding.

Does NOT reuse s1_reduce.py / s1_analyze.py's reduced arrays. Loads the raw caches directly via v282cmp,
band-passes with its own filter call, aligns lag its own way (best-lag cross-correlation regression for
"gain", route lat_delay for "relative error"), and bootstraps over ROUTES (3 for V282 -- small, noted).

One route in RAM at a time is not needed here (small npz's, <10 MB each) but we still `del` between routes
to stay well inside budget.
"""
import sys, json
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import numpy as np
from scipy import signal
import v282cmp as V

FS = V.FS
rng = np.random.default_rng(0)

def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")

def cell_route(route, vmin, vmax, f1, f2):
    """Returns per-run arrays (x_bp, y_bp_bestlag, y_bp_onschedule) restricted to usable & speed band, run by run."""
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, vmin, vmax)
    ld = float(np.nanmedian(S["lat_delay"][V.usable(S, 2.0)]))
    LD = int(round(ld * FS))
    x_all = np.nan_to_num(S["model"])
    y_all = np.nan_to_num(S["la_pose"])
    del S
    xs_L, ys_L, xs_D, ys_D = [], [], [], []
    for (i0, i1) in V.runs(m, t, min_s=8.0):
        # band-pass the WHOLE contiguous run (need context outside the speed-band mask itself for filter
        # settling -- use the full active run i0:i1 already restricted to usable & speed & no clock-gap)
        n = i1 - i0
        trim = int(0.5 / f1 * FS)
        maxlag = int(0.8 * FS)
        if n <= 2 * trim + maxlag + 50:
            continue
        xb = bp(x_all[i0:i1], f1, f2)
        yb = bp(y_all[i0:i1], f1, f2)
        # best lag by cross-correlation over 0..0.8s, on this run only
        xk = xb.copy(); xk[:trim] = 0; xk[max(0, n - trim - maxlag):] = 0
        cc = signal.correlate(yb, xk, mode="full", method="fft")
        e = signal.correlate(yb * yb, (np.abs(xk) > 0).astype(float), mode="full", method="fft")
        c = cc[n - 1: n + maxlag]
        ee = np.maximum(e[n - 1: n + maxlag], 1e-9)
        Lbest = int(np.argmax(c / np.sqrt(ee)))
        val = np.zeros(n, bool); val[trim: n - trim - maxlag] = True
        idx = np.where(val)[0]
        xs_L.append(xb[idx]); ys_L.append(yb[np.minimum(idx + Lbest, n - 1)])
        xs_D.append(xb[idx]); ys_D.append(yb[np.minimum(idx + LD, n - 1)])
    if not xs_L:
        return None
    return (np.concatenate(xs_L), np.concatenate(ys_L), np.concatenate(xs_D), np.concatenate(ys_D), ld)


def gain_relerr(xL, yL, xD, yD):
    G = float(np.dot(xL, yL) / max(np.dot(xL, xL), 1e-12))
    err = np.sqrt(np.mean((yD - xD) ** 2))
    rE = float(err / np.sqrt(np.mean(xD ** 2)))
    return G, rE


def boot_routes(per_route, nb=1000):
    """per_route: list of (xL,yL,xD,yD). Bootstrap ROUTES with replacement (route-level, not chunk-level --
    coarser than s1's hierarchical route+chunk bootstrap, which is the point of an independent check)."""
    n = len(per_route)
    Gs, Es = [], []
    for _ in range(nb):
        pick = rng.integers(0, n, n)
        xL = np.concatenate([per_route[i][0] for i in pick])
        yL = np.concatenate([per_route[i][1] for i in pick])
        xD = np.concatenate([per_route[i][2] for i in pick])
        yD = np.concatenate([per_route[i][3] for i in pick])
        G, E = gain_relerr(xL, yL, xD, yD)
        Gs.append(G); Es.append(E)
    return Gs, Es


V282_ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]

CELLS = [
    (">22 (22-99)", 22.0, 99.0, 0.15, 0.30),
    (">22 (22-99)", 22.0, 99.0, 0.30, 0.60),
    ("15-22", 15.0, 22.0, 0.15, 0.30),
]

results = {}
for name, vmin, vmax, f1, f2 in CELLS:
    per_route = []
    secs = []
    for r in V282_ROUTES:
        out = cell_route(r, vmin, vmax, f1, f2)
        if out is None:
            print(f"  {r}: no usable data in this cell"); continue
        xL, yL, xD, yD, ld = out
        secs.append(len(xL) / FS)
        per_route.append((xL, yL, xD, yD))
        print(f"  {r}: {len(xL)/FS:.1f}s in-cell, ld={ld:.3f}")
    if not per_route:
        continue
    xL_all = np.concatenate([p[0] for p in per_route]); yL_all = np.concatenate([p[1] for p in per_route])
    xD_all = np.concatenate([p[2] for p in per_route]); yD_all = np.concatenate([p[3] for p in per_route])
    G_pt, E_pt = gain_relerr(xL_all, yL_all, xD_all, yD_all)
    Gs, Es = boot_routes(per_route)
    key = f"{name} {f1}-{f2}Hz"
    results[key] = dict(sec_total=float(sum(secs)), nroutes=len(per_route),
                         G_point=G_pt, G_ci=[float(np.percentile(Gs, 2.5)), float(np.percentile(Gs, 97.5))],
                         rE_point=E_pt, rE_ci=[float(np.percentile(Es, 2.5)), float(np.percentile(Es, 97.5))])
    print(key, "sec", round(sum(secs), 1), "G", round(G_pt, 3), results[key]["G_ci"],
          "rE", round(E_pt, 3), results[key]["rE_ci"])

json.dump(results, open("C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/verify/s1_goal__targetpropos__method/verify1_results.json", "w"), indent=1)
print("done")
