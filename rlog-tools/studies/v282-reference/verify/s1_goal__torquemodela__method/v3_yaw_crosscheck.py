"""The finding's s1_goal pipeline uses S["la_pose"] (livePose pose_wz * v, device frame) as its ONLY
achieved-lateral-accel channel labelled 'yaw x v' -- it never computes a channel from S["la_yaw"]
(carState yaw rate * v, independent source). The task brief for this stream explicitly requires
cross-checking any V282-vs-torque conclusion against la_yaw and stating if they disagree. Do that here,
for the exact cells the finding cites, using the SAME masked cross-correlation estimator as v2 (already
shown there to reproduce the phasor-lag numbers closely) but swapped to la_yaw.
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
VB = {"15-22": (15.0, 22.0), ">22": (22.0, 99.0)}
MAXLAG = int(0.8 * FS)
GROUPS_WANT = ["V282", "T64"]
edges = json.load(open(HERE.parent.parent / "s1_goal" / "s1_results.json"))["tercile_edges"]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def masked_lag(x, y, mask):
    xk = x * mask
    num = signal.correlate(y, xk, mode="full", method="fft")
    n = len(x)
    num = num[n - 1: n + MAXLAG]
    ex = float(np.sum(x[mask] ** 2))
    ey = signal.correlate(y * y, mask.astype(float), mode="full", method="fft")[n - 1: n + MAXLAG]
    den = np.sqrt(max(ex, 1e-12) * np.maximum(ey, 1e-12))
    score = num / den
    Lbest = int(np.argmax(score))
    return Lbest / FS, float(score[Lbest])


acc = {}
frac_finite = {}
corr_yaw_pose = {}

for route, meta in V.ROUTES.items():
    g = meta["group"]
    if g not in GROUPS_WANT:
        continue
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    x_all = np.nan_to_num(S["model"])
    yaw_all = S["la_yaw"].copy()
    pose_all = S["la_pose"].copy()
    frac_finite[route] = float(np.isfinite(yaw_all[m]).mean())
    fin = np.isfinite(yaw_all) & np.isfinite(pose_all) & m
    if fin.sum() > 100:
        corr_yaw_pose[route] = float(np.corrcoef(yaw_all[fin], pose_all[fin])[0, 1])
    yaw_all = np.nan_to_num(yaw_all)
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
            yb = bp(yaw_all[i0:i1], f1, f2)
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
                    ("lo", lambda ee=env: ee < e1), ("mid", lambda ee=env: (ee >= e1) & (ee < e2)),
                    ("hi", lambda ee=env: ee >= e2),
                ):
                    sel = vsel & tsel_fn()
                    if sel.sum() < 100:
                        continue
                    lag_s, rho = masked_lag(xb, yb, sel)
                    key = (g, vbname, bname, tname)
                    acc.setdefault(key, []).append((route, lag_s, rho, int(sel.sum())))
    del S, x_all, yaw_all, pose_all
    print("done", route, g, "finite la_yaw frac", round(frac_finite[route], 3), flush=True)

print("\ncorr(la_yaw, la_pose) per route (usable mask):")
for r, c in corr_yaw_pose.items():
    print(" ", r, round(c, 4))

print("\n=== masked cross-correlation lag using la_yaw (carState) instead of la_pose (livePose) ===")
for key in sorted(acc):
    g, vbname, bname, tname = key
    entries = acc[key]
    tot_n = sum(e[3] for e in entries)
    pooled_lag = sum(e[1] * e[3] for e in entries) / tot_n
    pooled_rho = sum(e[2] * e[3] for e in entries) / tot_n
    print(f"{g:6s} {vbname:5s} {bname:9s} {tname:3s}  lag={pooled_lag:.3f}s  rho={pooled_rho:.2f}  n={tot_n:6d} ({tot_n/FS:.0f}s, {len(entries)} routes)")
