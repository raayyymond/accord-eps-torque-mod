"""Independent cross-check of the s1_goal lag finding using a DIFFERENT estimator than the phasor/Hilbert
method in s1_analyze.py: a plain masked, normalised cross-correlation peak-lag (same style as
v282cmp.event_metrics, which is validated by v282cmp._self_test to recover a known lag to <11 ms and a
known gain to <0.02). No amplitude-envelope splitting inside a run beyond selecting samples whose
band-passed |Hilbert envelope of the model| falls in the ALREADY-PUBLISHED tercile edges (read from
s1_results.json -- those edges do not depend on the phasor-lag formula being checked here, so reusing
them does not smuggle in the thing under test).

Loads ONE route at a time (RAM), accumulates masked correlation sums into per (group,vb,band,terc)
accumulators, deletes before the next route.
"""
import sys, json
from pathlib import Path
import numpy as np
from scipy import signal

sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = Path(__file__).resolve().parent
FS = V.FS
BANDS = {"0.15-0.3": (0.15, 0.30), "0.3-0.6": (0.30, 0.60)}
VB = {"8-15": (8.0, 15.0), "15-22": (15.0, 22.0), ">22": (22.0, 99.0)}
MAXLAG = int(0.8 * FS)
GROUPS_WANT = ["V282", "T64"]

edges = json.load(open(HERE.parent.parent / "s1_goal" / "s1_results.json"))["tercile_edges"]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def masked_lag(x, y, mask):
    """argmax over L in [0,MAXLAG] of sum_{t in mask} x[t] y[t+L] / sqrt(sum x[t]^2 * sum_{t in mask} y[t+L]^2).
    mask excludes the last MAXLAG samples already (caller's job)."""
    xk = x * mask
    num = signal.correlate(y, xk, mode="full", method="fft")
    n = len(x)
    num = num[n - 1: n + MAXLAG]  # num[L] = sum_t y[t+L] xk[t]
    ex = float(np.sum(x[mask] ** 2))
    ey = signal.correlate(y * y, mask.astype(float), mode="full", method="fft")[n - 1: n + MAXLAG]
    den = np.sqrt(max(ex, 1e-12) * np.maximum(ey, 1e-12))
    score = num / den
    Lbest = int(np.argmax(score))
    rho = float(score[Lbest])
    return Lbest / FS, rho


# accumulate per (group, vb, band, terc): list of (route, lag_s, rho, n_samples)
acc = {}

for route, meta in V.ROUTES.items():
    g = meta["group"]
    if g not in GROUPS_WANT:
        continue
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    x_all = np.nan_to_num(S["model"])
    p_all = np.nan_to_num(S["la_pose"])
    runs = V.runs(m, t, min_s=8.0)
    for (i0, i1) in runs:
        n = i1 - i0
        if n < MAXLAG + 400:
            continue
        for bname, (f1, f2) in BANDS.items():
            trim = int(0.5 / f1 * FS)
            if n <= 2 * trim + MAXLAG + 50:
                continue
            xb = bp(x_all[i0:i1], f1, f2)
            pb = bp(p_all[i0:i1], f1, f2)
            env = np.abs(signal.hilbert(xb))
            valid = np.zeros(n, bool)
            valid[trim: n - trim - MAXLAG] = True
            for vbname, (vlo, vhi) in VB.items():
                vsel = (v[i0:i1] >= vlo) & (v[i0:i1] < vhi) & valid
                if vsel.sum() < 200:
                    continue
                e1, e2 = edges.get(f"{vbname}|{bname}", [None, None])
                if e1 is None:
                    continue
                for tname, tsel_fn in (
                    ("lo", lambda ee=env: ee < e1),
                    ("mid", lambda ee=env: (ee >= e1) & (ee < e2)),
                    ("hi", lambda ee=env: ee >= e2),
                ):
                    sel = vsel & tsel_fn()
                    if sel.sum() < 100:
                        continue
                    lag_s, rho = masked_lag(xb, pb, sel)
                    key = (g, vbname, bname, tname)
                    acc.setdefault(key, []).append((route, lag_s, rho, int(sel.sum())))
    del S, x_all, p_all
    print("done", route, g, flush=True)

print()
print("=== independent (non-phasor) masked cross-correlation lag, per route, then pooled (sample-weighted mean) ===")
rows = {}
for key in sorted(acc):
    g, vbname, bname, tname = key
    entries = acc[key]
    tot_n = sum(e[3] for e in entries)
    pooled_lag = sum(e[1] * e[3] for e in entries) / tot_n
    pooled_rho = sum(e[2] * e[3] for e in entries) / tot_n
    rows[key] = dict(lag=pooled_lag, rho=pooled_rho, n=tot_n, nroutes=len(entries), routes=entries)
    print(f"{g:6s} {vbname:5s} {bname:9s} {tname:3s}  lag={pooled_lag:.3f}s  rho={pooled_rho:.2f}  "
          f"n={tot_n:6d} ({tot_n/FS:.0f}s, {len(entries)} routes)  per-route={[(r[0], round(r[1],3)) for r in entries]}")

json.dump({f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": {kk: vv for kk, vv in v_.items() if kk != "routes"} for k, v_ in rows.items()},
          open(HERE / "v2_results.json", "w"), indent=1)
print("\nwrote v2_results.json")
