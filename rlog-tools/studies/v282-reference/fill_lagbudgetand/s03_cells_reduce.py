"""Step 3 (cells): per route, per (band, speed bin, demand tercile, 60-s chunk) sums for in-band PHASE lags of each segment
of the chain.  One route in RAM at a time.

Cells and tercile edges are s1_goal's (s1_reduce.py / s1_analyze.py): usable(S, 2 m/s) runs >= 8 s, zero-phase order-2
butter bandpass per run (padtype even), edges trimmed 0.5/f_lo, tercile on the Hilbert envelope of the band-passed MODEL
with s1's pooled equal-group-weight edges.

Channels (all on the controlsState clock):
  x    model  = cs_des_curv * v^2  (logged plan lead = liveDelay + 0.175 s)
  xc   model re-shifted to the COMMON lead of V282 (liveDelay 0.20): xc(t) = x(t - (ld_route - 0.20))
  sp   setpoint = cs_la_des (the shaped reference the FF and P/I both use)
  act  la_act = controlsState actualLateralAccel (angle based)
  pose la_pose = livePose yaw rate * v (independent)
  ctl  x delayed by exactly 0.30 s (positive control: every cell must read 0.300)
Per pair (in -> out) the sums are S = sum(out_a * conj(in_a)) and W = sum(|in_a|^2), Wf = sum(|in_a|^2 * f_inst(in)).
lag = -angle(S) / (2 pi Wf/W).  Complex analytic signals from scipy.signal.hilbert per run.
out: _cells/<route>.npz
"""
import sys, json, gc
from pathlib import Path
import numpy as np
from scipy import signal
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V

HERE = Path(__file__).resolve().parent
OUT = HERE / "_cells"; OUT.mkdir(exist_ok=True)
FS = V.FS
BANDS = [(0.05, 0.15), (0.15, 0.30), (0.30, 0.60), (0.60, 1.20)]
VB = [(2.0, 8.0), (8.0, 15.0), (15.0, 22.0), (22.0, 99.0)]
VBN = ["2-8", "8-15", "15-22", ">22"]
EDGES = json.load(open(HERE.parent / "s1_goal" / "s1_results.json"))["tercile_edges"]
PAIRS = [("x", "sp"), ("sp", "act"), ("act", "pose"), ("x", "act"), ("x", "pose"), ("xc", "sp"), ("xc", "act"), ("xc", "pose"),
         ("x", "ctl"), ("sp", "pose")]


def bp(x, f1, f2):
    sos = signal.butter(2, [f1, f2], btype="band", fs=FS, output="sos")
    return signal.sosfiltfilt(sos, x, padtype="even")


def main(route):
    S = V.load(route)
    t, v = S["t"], S["v"]
    m = V.usable(S, 2.0)
    ld = float(np.nanmedian(S["lat_delay"][m]))
    dsh = int(round((ld - 0.20) * FS))
    ch_all = dict(x=np.nan_to_num(S["model"]), sp=np.nan_to_num(S["setpoint"]), act=np.nan_to_num(S["la_act"]),
                  pose=np.nan_to_num(S["la_pose"]))
    del S
    runs = V.runs(m, t, min_s=8.0)
    rows = {}   # key (band, vb, terc, chunk) -> vector of sums
    npair = len(PAIRS)
    for ri, (i0, i1) in enumerate(runs):
        n = i1 - i0
        seg = {k: a[i0:i1] for k, a in ch_all.items()}
        # common lead: xc(t) = x(t - dsh); the first dsh samples of the run take the model from BEFORE the run start
        j0 = i0 - dsh
        if j0 < 0:
            continue
        seg["xc"] = ch_all["x"][j0:j0 + n]
        seg["ctl"] = np.concatenate([np.full(30, seg["x"][0]), seg["x"][:-30]])
        vb = np.full(n, -1)
        for k, (a, c) in enumerate(VB):
            vb[(v[i0:i1] >= a) & (v[i0:i1] < c)] = k
        chunk = ((t[i0:i1] - t[i0]) // 60).astype(int)
        for bi, (f1, f2) in enumerate(BANDS):
            trim = int(0.5 / f1 * FS)
            if n <= 2 * trim + 50:
                continue
            A = {k: signal.hilbert(bp(y, f1, f2)) for k, y in seg.items()}
            env = np.abs(A["x"])
            finst = {k: np.r_[np.diff(np.unwrap(np.angle(A[k]))), 0.0] * FS / (2 * np.pi) for k in ("x", "xc", "sp", "act")}
            valid = np.zeros(n, bool); valid[trim:n - trim] = True
            for k in range(len(VB)):
                e1, e2 = EDGES[f"{VBN[k]}|{f1}-{f2}"]
                terc = np.digitize(env, [e1, e2])
                sel0 = valid & (vb == k)
                if sel0.sum() < 20:
                    continue
                for tc in range(3):
                    sel = sel0 & (terc == tc)
                    if not sel.any():
                        continue
                    for c in np.unique(chunk[sel]):
                        s2 = sel & (chunk == c)
                        vec = np.zeros(1 + 3 * npair, dtype=np.complex128)
                        vec[0] = s2.sum()
                        for pi, (a, b) in enumerate(PAIRS):
                            xa, ya = A[a][s2], A[b][s2]
                            w = np.abs(xa) ** 2
                            fi = np.clip(finst[a][s2], f1 * 0.5, f2 * 1.5)
                            vec[1 + 3 * pi] = np.sum(ya * np.conj(xa))
                            vec[2 + 3 * pi] = np.sum(w)
                            vec[3 + 3 * pi] = np.sum(w * fi)
                        key = (bi, k, tc, ri * 1000 + int(c))
                        rows[key] = rows.get(key, 0) + vec
            del A
    keys = np.array(list(rows.keys()), dtype=np.int64).reshape(-1, 4)
    vals = np.array(list(rows.values())) if rows else np.zeros((0, 1 + 3 * npair), complex)
    np.savez_compressed(OUT / f"{route}.npz", keys=keys, vals=vals,
                        meta=json.dumps(dict(route=route, group=V.ROUTES[route]["group"], ld=ld, dshift_samples=dsh,
                                             pairs=PAIRS, bands=BANDS, vb=VBN)))
    print(route, V.ROUTES[route]["group"], "ld", round(ld, 3), "shift", dsh, "runs", len(runs), "cells", len(rows), flush=True)
    del ch_all, rows; gc.collect()


if __name__ == "__main__":
    for r in (sys.argv[1:] or list(V.ROUTES)):
        main(r)
